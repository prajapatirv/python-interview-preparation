# Deep Dive 19 — Production Stability, Alerting & Monitoring

> Runnable companions: [`08_scaling_production_resilience/04_health_checks_graceful_shutdown.py`](../08_scaling_production_resilience/04_health_checks_graceful_shutdown.py) ·
> [`05_metrics_alerting_simulation.py`](../08_scaling_production_resilience/05_metrics_alerting_simulation.py)
> Related deep dives: [Scaling](12_scaling_applications.md) ·
> [Framework development](11_python_framework_development.md) · [Error handling](08_error_handling.md) ·
> [Kafka failure handling](15_kafka_failure_handling.md)

## What interviewers are actually probing

Whether you've **operated** software, not just written it. The tells are specific: do you know the
difference between an SLI, an SLO and an SLA; do you understand **error budgets** as a decision-making
tool rather than a metric; do you alert on **symptoms** (users are affected) rather than **causes**
(CPU is high); and can you describe **graceful shutdown** in enough detail to show you've dealt with
dropped requests during a deploy.

The best single answer in this whole section is about **cardinality** — it's a real production
incident that a lot of engineers have caused and few can explain in advance.

---

## Must-know points

- **SLI** = what you measure. **SLO** = your target. **SLA** = the contract with a penalty.
- **Error budget** = `1 − SLO`. It's a **deployment risk budget**, not just a number.
- **Alert on symptoms, not causes.** Page on "users are getting errors", not "CPU > 80%".
- **The three pillars**: metrics (aggregate, cheap), logs (detail, expensive), traces (causality
  across services). Plus **correlation IDs** to join them.
- **Structured JSON logs** to stdout. Never unstructured text in production.
- **Graceful shutdown**: SIGTERM → stop accepting → drain → flush → exit, and the orchestrator's
  grace period must exceed it.

---

## Interview questions and full answers

### Q1. What are SLI, SLO and SLA?

| Term | Definition | Example |
|---|---|---|
| **SLI** (Indicator) | The **metric you measure** | % of requests served in < 200 ms |
| **SLO** (Objective) | Your **internal target** for that SLI | 99.5% of requests < 200 ms over 30 days |
| **SLA** (Agreement) | A **contract** with a financial penalty | "99.5% uptime or a 10% credit" |
| **Error budget** | `1 − SLO` — how much failure is permitted | 0.5% ≈ **3.6 hours/month** |

**Choosing good SLIs** is the part worth elaborating. A good SLI measures **what the user
experiences**:

- **Availability**: `successful_requests / total_requests` — not "is the process running".
- **Latency**: the proportion of requests **under a threshold**, not the average. Averages hide
  everything; a service with a 50 ms average can have a 30 s p99.
- **Quality**: for a data pipeline, freshness (how far behind is the read model?) and correctness.

**Set the SLO below the SLA**, always. If you promise 99.5%, target 99.9% internally. The gap is your
safety margin — you find out you're degrading before a customer invokes the contract.

**The error budget is the genuinely useful idea**, and it's what interviewers want to hear:

> "The error budget converts reliability from an argument into arithmetic. With a 99.5% SLO you have
> 3.6 hours of failure a month. If you've spent it, **feature deploys freeze** and the team works on
> reliability until the budget recovers. If you have budget left, you can ship aggressively. It
> aligns the incentives of the people who want velocity and the people who want stability, because
> now they're both looking at the same number instead of arguing about risk tolerance."

**Don't set the SLO to 100%.** It's unachievable, infinitely expensive, and it removes the error
budget entirely — which means every incident is a crisis and there's no framework for deciding what's
acceptable. The point of an SLO is to define *how unreliable you're allowed to be*.

---

### Q2. How do you instrument a FastAPI service with Prometheus metrics?

```python
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import FastAPI, Response, Request
import time

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency",
    ["method", "endpoint"],
    buckets=[.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10],
)
IN_PROGRESS = Gauge("http_requests_in_progress", "Requests in flight")

app = FastAPI()

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    IN_PROGRESS.inc()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception:
        status = 500
        raise
    finally:
        IN_PROGRESS.dec()
        duration = time.perf_counter() - start
        # CRITICAL: the route TEMPLATE, not the raw path
        route = request.scope.get("route")
        endpoint = route.path if route else "unmatched"
        REQUEST_COUNT.labels(request.method, endpoint, status).inc()
        REQUEST_LATENCY.labels(request.method, endpoint).observe(duration)

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

**The metric types:**

| Type | Use | Examples |
|---|---|---|
| **Counter** | Monotonically increasing | requests, errors, bytes, messages |
| **Gauge** | Goes up and down | in-flight requests, queue depth, pool size |
| **Histogram** | Distribution, bucketed **server-side** | latency, payload size |
| **Summary** | Quantiles computed **client-side** | rarely — see below |

**Prefer Histogram to Summary.** A Summary computes quantiles per instance, and **quantiles cannot be
averaged across instances** — you simply cannot derive a fleet-wide p99 from ten per-instance p99s.
A Histogram exports bucket counts, which *are* additive, so `histogram_quantile()` gives a correct
aggregate. This trips people up constantly.

**Now the most important operational point in this whole deep dive — cardinality.**

Every unique **combination** of label values creates a **separate time series**. Using an unbounded
value as a label is how you take down your monitoring system:

```python
# CATASTROPHIC — one time series per order ID
REQUEST_COUNT.labels(method, f"/orders/{order_id}", status).inc()
# 1,000,000 orders = 1,000,000 time series = Prometheus OOM

# CORRECT — the route template: ONE series for all orders
REQUEST_COUNT.labels(method, "/orders/{id}", status).inc()
```

**Never use as a label:** user ID, order ID, email, session ID, full URL path, raw error message,
timestamp. **Safe labels:** route template, HTTP method, status code, environment, service name,
error *class*.

**The rule of thumb: keep total series per metric in the low thousands.** If you need per-user
detail, that's what **logs and traces** are for — metrics are for aggregates.

**In practice**, use `prometheus-fastapi-instrumentator`, which handles the route templating and the
standard metrics for you. But be able to explain the cardinality trap, because that's the question.

---

### Q3. How do you set up structured logging for production?

**JSON to stdout. Always.** Unstructured text requires fragile regex parsing in your log aggregator;
JSON is parsed natively by CloudWatch Logs Insights, Elasticsearch, Datadog, Loki and everything else.

```python
import logging, sys, contextvars
from pythonjsonlogger import jsonlogger

trace_id_var = contextvars.ContextVar("trace_id", default="-")

class ContextFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        log_record["service"]     = "order-service"
        log_record["environment"] = settings.environment
        log_record["version"]     = settings.app_version
        log_record["trace_id"]    = trace_id_var.get()      # automatic on EVERY line

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(ContextFormatter("%(timestamp)s %(level)s %(name)s %(message)s"))
logging.root.setLevel(logging.INFO)
logging.root.addHandler(handler)

logger = logging.getLogger("order")
logger.info("Order placed", extra={"order_id": order.id, "user_id": user.id,
                                   "total": order.total})
```

**`ContextVar`, not `threading.local`.** `ContextVar` follows the **asyncio task**, so in an async
service each concurrent request keeps its own trace ID. `threading.local` would leak between
coroutines sharing a thread — a subtle bug producing logs attributed to the wrong request.

**The practices that matter:**

1. **Log to stdout**, not to files. In containers, the runtime collects stdout. Writing files means
   log rotation, disk-full risk, and logs lost when the pod dies.
2. **A correlation/trace ID on every line**, propagated across services via a header. Without it,
   debugging a request that touched four services means manual timestamp correlation.
3. **Lazy `%s` formatting, not f-strings**: `logger.info("order %s", order_id)`. With an f-string the
   string is built even when the level would discard it, and aggregators lose the ability to group by
   message template.
4. **Never log secrets or PII** — tokens, passwords, card numbers, full request bodies. Add a
   redacting filter; logs are copied to more places than you think, with weaker access controls.
5. **Use levels honestly.** `ERROR` = a human should look. `WARNING` = unusual but handled.
   `INFO` = business events. `DEBUG` = off in production. If everything is ERROR, nothing is.
6. **Sample high-volume logs.** At 10,000 RPS, one log line per request is 864M lines a day. Sample
   successes, keep all errors.

**Logs vs metrics — the cost distinction:** metrics are cheap and aggregate (millions of requests →
one number); logs are expensive and detailed. Use metrics to **detect**, logs to **diagnose**. Don't
build dashboards by counting log lines when a counter would do.

---

### Q4. How do you implement distributed tracing?

A trace follows **one request across every service**, showing where the time actually went. It's the
only tool that answers "which of these six services made this request slow?"

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel:4317")))
trace.set_tracer_provider(provider)

FastAPIInstrumentor.instrument_app(app)           # auto-trace every HTTP request
SQLAlchemyInstrumentor().instrument(engine=engine)  # auto-trace every SQL query
HTTPXClientInstrumentor().instrument()             # auto-trace outbound calls + propagate headers

# Manual span for a business operation
tracer = trace.get_tracer("order-service")

with tracer.start_as_current_span("apply_coupon") as span:
    span.set_attribute("coupon.code", coupon_code)
    discount = apply_coupon(order, coupon_code)
    span.set_attribute("discount.amount", discount)
```

**The concepts:**

- **Trace** — the whole request journey, identified by a `trace_id`.
- **Span** — one unit of work (an HTTP handler, a DB query, an external call), with a `span_id`, a
  parent, a start/end time and attributes.
- **Context propagation** — the `traceparent` header (W3C Trace Context) carries the trace across
  service boundaries. The auto-instrumentation injects and extracts it for you.

**Why it beats logs for latency problems:** a trace shows a **waterfall**. You see immediately that
of a 4-second request, 3.8 seconds was one downstream call — or 200 individual 20 ms queries,
revealing an N+1 that no log line would have made obvious.

**Sampling is mandatory at scale.** Tracing every request at 10,000 RPS is unaffordable. The options:

- **Head-based** (simple): decide at the start, e.g. 1% of requests. Cheap, but you'll miss the rare
  slow ones — which are exactly the ones you wanted.
- **Tail-based** (better): buffer the spans and decide *after* seeing the outcome — **keep 100% of
  errors and slow requests, 1% of the fast successes**. Requires a collector that supports it
  (OpenTelemetry Collector does).

**Use OpenTelemetry**, not a vendor SDK. It's the CNCF standard, it's vendor-neutral, and switching
from Jaeger to Datadog to Honeycomb becomes a collector config change rather than a code rewrite.
(Jaeger's own exporter is deprecated in favour of OTLP.)

**Tie the three pillars together**: put the `trace_id` in your **logs** (Q3) and as an **exemplar** on
your metrics. Then a latency spike on a dashboard links to the traces that caused it, which link to
the logs for that exact request. That correlation is the whole point of observability as a practice.

---

### Q5. What are the key alerting rules for a Python API?

| Alert | Condition | Severity | Action |
|---|---|---|---|
| **High error rate** | 5xx rate > 1% for 2 min | **P1** | Page on-call |
| **High latency** | p99 > 2 s for 5 min | P2 | Slack |
| **Low throughput** | RPS < 10% of baseline | **P1** | Page — likely a total outage |
| **Kafka consumer lag** | > 10,000 msgs for 10 min | P2 | Slack + autoscale |
| **DLQ non-empty** | depth > 0 | P2 | Slack + ticket |
| **Error budget burn** | Burning 10× the sustainable rate | **P1** | Page |
| **Certificate expiry** | < 14 days | P3 | Ticket |
| **Disk usage** | > 85% | P2 | Investigate |
| **Health check failing** | Readiness failing on > 50% of pods | **P1** | Page |
| **Pod restarts** | CrashLoopBackOff | **P1** | Page |

**The principle that matters more than the table: alert on SYMPTOMS, not CAUSES.**

- ❌ "CPU > 80%" — so what? If users are being served fine, this is noise at 3 a.m.
- ✅ "5xx rate > 1%" — users are being harmed. That's worth waking someone for.

High CPU is worth a **dashboard**, not a page. Page only when a human must act **now**.

**The most important refinement: multi-window, multi-burn-rate alerts.** A flat "error rate > 1%"
either fires constantly on brief blips or misses a slow persistent burn. The SRE-standard approach
alerts on how fast you're **consuming the error budget**:

```
# Fast burn: 14.4x budget rate over 1h AND 5m -> P1 page
#   (at this rate the entire 30-day budget is gone in ~2 days)
(
  rate(http_requests_total{status=~"5.."}[1h]) / rate(http_requests_total[1h]) > 14.4 * 0.005
  and
  rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 14.4 * 0.005
)

# Slow burn: 3x over 6h AND 30m -> P2 ticket
```

**The two windows are what suppress false positives:** the long window confirms it's sustained; the
short window confirms it's *still happening* right now, so the alert resolves promptly once fixed.

**Alert fatigue is the real failure mode.** Every alert that fires without requiring action trains
people to ignore alerts. The tests to apply to any proposed alert:

1. Is a human needed **right now**? If not, it's a ticket or a dashboard.
2. Is it **actionable**? If there's no runbook step, it's noise.
3. Does it reflect **user impact**? If not, deprioritise it.

A good practice to mention: **every page must have a runbook link in the alert payload**.

---

### Q6. How do you implement graceful shutdown?

When Kubernetes terminates a pod it sends **SIGTERM**, waits `terminationGracePeriodSeconds`
(default 30), then **SIGKILL**s. Without graceful handling, every in-flight request is dropped and
every buffered Kafka message is lost — **on every single deploy**.

```python
import signal, asyncio, logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

log = logging.getLogger(__name__)
shutdown_event = asyncio.Event()

def handle_shutdown(*_):
    log.info("shutdown signal received")
    shutdown_event.set()

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    await db_pool.connect()
    app.state.ready = True
    log.info("service ready")

    yield

    # --- shutdown ---
    app.state.ready = False          # 1. readiness now fails -> LB stops sending traffic
    log.info("draining...")
    await asyncio.sleep(5)           # 2. let the LB notice (see below)
    log.info("finishing in-flight requests...")
    await asyncio.sleep(5)           # 3. let current requests complete
    kafka_producer.flush(timeout=30) # 4. NEVER lose buffered messages
    await db_pool.disconnect()       # 5. close pools cleanly
    log.info("shutdown complete")

app = FastAPI(lifespan=lifespan)

@app.get("/health/ready")
async def ready():
    if not app.state.ready:
        return JSONResponse({"status": "draining"}, status_code=503)
    return {"status": "ready"}
```

**The sequence, and why each step is there:**

1. **Fail readiness first.** This is the step people omit, and it's the most important one.
2. **Sleep before draining.** Kubernetes removes the pod from the Service endpoints **asynchronously**
   — the kube-proxy/iptables update and the load balancer's own propagation take a few seconds. If
   you stop accepting immediately on SIGTERM, requests **already in flight from the LB** get
   connection-refused. That's why you keep serving for a few seconds *after* failing readiness. This
   is the classic "we get 502s on every deploy" bug.
3. **Finish in-flight requests.** Uvicorn/Gunicorn handle this with `graceful_timeout`.
4. **Flush the Kafka producer.** `produce()` buffers locally; without `flush()` every buffered
   message is lost. See
   [Kafka Q8](14_kafka_pipelines_delivery_semantics.md#q8-how-do-producer-delivery-reports-work-in-confluent-kafka-python).
5. **Close pools** so the database isn't left with orphaned connections.

**`terminationGracePeriodSeconds` must exceed the total**, or SIGKILL cuts you off mid-drain:

```yaml
spec:
  terminationGracePeriodSeconds: 60      # > 5 + 5 + 30 flush
  containers:
    - lifecycle:
        preStop:
          exec: { command: ["sleep", "5"] }   # belt-and-braces LB propagation delay
```

**For a Kafka consumer** the equivalent is: stop the poll loop, **commit offsets synchronously**, and
call `consumer.close()` so the group rebalances immediately rather than waiting out
`session.timeout.ms` — which would add ~45 s of lag to every deploy.

---

### Q7. How do you handle database migrations safely in production?

**Never run migrations in the application startup path.** With 10 pods rolling out, ten processes race
to run the same migration. Even with Alembic's locking you get failed startups, and a failed migration
in a startup hook means a CrashLoopBackOff instead of a clear error.

```
# WRONG:  CMD alembic upgrade head && uvicorn app.main:app
# RIGHT:  a separate Kubernetes Job (or an init container), run BEFORE the rollout
```

**The safe-migration checklist** — the substance of the answer:

1. **Add a column as nullable first.** `ADD COLUMN x NOT NULL DEFAULT 'y'` rewrites the whole table
   and holds an exclusive lock on older PostgreSQL. Do it in three steps: add nullable → backfill in
   batches → add the NOT NULL constraint.
2. **Never drop a column in the same deploy as the code that stops using it.** The old code is still
   running during a rolling deploy and will `SELECT` a column that no longer exists. Deploy the code
   first, drop the column next release.
3. **`CREATE INDEX CONCURRENTLY`** — a plain `CREATE INDEX` takes an exclusive lock and blocks all
   writes for the duration. On a large table that's an outage.
4. **Rename via expand/contract**: add the new column → dual-write both → backfill → switch reads →
   stop writing the old → drop it. Four deploys, zero downtime.
5. **Backfill in batches with sleeps.** `UPDATE orders SET region='UNKNOWN'` on 100M rows takes a
   long lock and bloats the WAL. Loop in batches of 10,000 with a pause.
6. **Always have a tested `downgrade()`.** An untested rollback is not a rollback.
7. **Set a `lock_timeout`** so a migration that can't get its lock fails fast instead of queueing
   behind a long query and blocking every subsequent one.

```python
def upgrade():
    op.execute("SET lock_timeout = '5s'")
    op.add_column("orders", sa.Column("region", sa.String(10), nullable=True))   # 1. nullable
    op.execute("UPDATE orders SET region = 'UNKNOWN' WHERE region IS NULL")      # 2. backfill
    op.alter_column("orders", "region", nullable=False)                          # 3. constrain
    op.create_index("ix_orders_region", "orders", ["region"],
                    postgresql_concurrently=True)                                # 4. no lock
```

**The governing principle: every migration must be compatible with both the old and new application
code**, because during a rolling deploy both are running simultaneously. That single sentence is the
best answer to this question.

---

### Q8. What is a canary deployment and how do you monitor it?

Route a **small percentage of traffic** (5–10%) to the new version, watch the metrics, and roll back
automatically if thresholds are breached.

```yaml
# Argo Rollouts
strategy:
  canary:
    steps:
      - setWeight: 5
      - pause: { duration: 5m }
      - analysis: { templates: [{ templateName: error-rate }] }
      - setWeight: 25
      - pause: { duration: 10m }
      - setWeight: 50
      - pause: { duration: 10m }
      - setWeight: 100
---
# AnalysisTemplate
successCondition: result[0] < 0.01        # error rate under 1%
failureCondition: result[0] >= 0.05       # abort above 5%
query: |
  sum(rate(http_requests_total{status=~"5..",version="{{args.version}}"}[2m]))
  / sum(rate(http_requests_total{version="{{args.version}}"}[2m]))
```

**What to monitor, in priority order:**

1. **Error rate** — the obvious one.
2. **p99 latency** — a canary can be functionally correct and 3× slower.
3. **Business KPIs** — orders per minute, checkout conversion, revenue. **This is the one people
   forget**, and it catches the worst bugs: a canary with a 0% error rate and perfect latency that
   silently fails to create orders because a boolean got inverted. No infrastructure metric detects
   that; the orders-per-minute counter does immediately.

```python
ORDER_FAILURES = Counter("orders_failed_total", "Orders that failed", ["reason"])
ORDER_REVENUE  = Counter("orders_revenue_total_cents", "Revenue in cents")
ORDERS_CREATED = Counter("orders_created_total", "Orders successfully created")
```

**Label metrics by version** so you can compare canary against baseline directly, rather than
eyeballing a dashboard for a step change.

**Deployment strategies compared:**

| Strategy | How | Rollback | Cost |
|---|---|---|---|
| **Rolling** | Replace pods gradually | Roll forward/back — slow | Low |
| **Blue/green** | Two full environments, switch all at once | **Instant** (flip back) | **2× infra** |
| **Canary** | Gradual % shift with analysis | Fast, automated | Low |
| **Feature flag** | Deploy dark, enable per user | **Instant, no deploy** | Low |

**Canary + feature flags is the strongest combination**: deploy the code to 100% with the feature
**off**, then enable it for 1% of users. Now the deployment risk and the feature risk are separated,
and disabling is a config change rather than a rollback.

---

### Q9. How do you implement feature flags for safe releases?

```python
from functools import lru_cache
import boto3, json, hashlib, time

ssm = boto3.client("ssm")
_cache = {"flags": None, "at": 0}

def get_flags(ttl=60) -> dict:
    if _cache["flags"] is None or time.time() - _cache["at"] > ttl:
        raw = ssm.get_parameter(Name="/app/feature-flags")["Parameter"]["Value"]
        _cache.update(flags=json.loads(raw), at=time.time())
    return _cache["flags"]

def is_enabled(flag: str, user_id: str | None = None) -> bool:
    cfg = get_flags().get(flag, {"enabled": False})       # default OFF — fail safe
    if not cfg.get("enabled"):
        return False
    if user_id and user_id in cfg.get("allowlist", []):
        return True
    if (pct := cfg.get("rollout_pct")) is not None:
        # Stable hash: the SAME user always gets the SAME answer
        bucket = int(hashlib.md5(f"{flag}:{user_id}".encode()).hexdigest(), 16) % 100
        return bucket < pct
    return True

if is_enabled("new-checkout-flow", user_id=user.id):
    return await new_checkout(order)
return await legacy_checkout(order)
```

**The details that matter:**

1. **Stable hashing, not `random()`.** A random decision per request means the same user alternates
   between implementations — inconsistent behaviour that's nearly impossible to debug, and a broken
   experience if the two paths have different state. Hash on `(flag, user_id)` so each user is
   consistently bucketed, and including the flag name means a user isn't in the same bucket for
   every flag.
2. **A TTL cache.** Hitting SSM per request adds latency and cost; caching forever means a flag flip
   never takes effect. 30–60 s is the usual compromise.
3. **Default to OFF.** If the flag store is unreachable, fall back to the safe path.
4. **An allowlist** for internal testing before any percentage rollout.
5. **Flags are technical debt.** Every flag doubles the code paths to test. **Remove them once the
   rollout is complete** — set an expiry date and track it. A codebase with 200 stale flags has
   2^200 theoretical configurations and nobody knows which are tested.

**A kill switch** is the highest-value flag type: wrap a risky integration so you can disable it
instantly, without a deploy, when a downstream starts failing.

---

## The three pillars, and what each is for

| | **Metrics** | **Logs** | **Traces** |
|---|---|---|---|
| **Answers** | "Is something wrong?" | "What exactly happened?" | "Where did the time go?" |
| **Granularity** | Aggregate | Per event | Per request, across services |
| **Cost** | Very low | High | Medium (with sampling) |
| **Retention** | Months–years | Days–weeks | Days |
| **Cardinality** | **Must be low** | Unlimited | Unlimited |
| **Use to** | **Detect** and alert | **Diagnose** | **Localise** |

**The workflow to describe:** a **metric** alert fires ("5xx rate > 1%"). A **dashboard** narrows it
to one endpoint and one version. A **trace** shows the time is in one downstream call. **Logs** for
that trace ID show the exact exception and the input that caused it.

**The correlation ID is what makes it one workflow instead of three tools.** Put the `trace_id` in
every log line and as an exemplar on your histograms, and you can navigate from a graph to a
traceback in two clicks.

---

## Worked example — a production-readiness checklist

The answer to "how do you know a service is ready for production?" — a concrete list beats a vague
philosophy.

**Observability**
- [ ] `/metrics` endpoint with RED metrics (Rate, Errors, Duration), labelled by **route template**
- [ ] Structured JSON logs to stdout with a trace ID on every line
- [ ] OpenTelemetry tracing with tail-based sampling
- [ ] Business metrics (orders created, revenue), not only technical ones
- [ ] Dashboards for SLIs, and alerts on SLO burn rate

**Resilience**
- [ ] `/health/live` (checks nothing external) and `/health/ready` (checks dependencies, with timeouts)
- [ ] `startupProbe` if startup is slow
- [ ] **Timeouts on every network call** — no exceptions
- [ ] Retries with exponential backoff **and jitter**, transient errors only
- [ ] A circuit breaker per downstream
- [ ] Graceful shutdown: fail readiness → sleep → drain → flush → exit
- [ ] `terminationGracePeriodSeconds` > total shutdown time

**Scaling**
- [ ] Stateless — sessions, files, locks all externalised
- [ ] `minReplicas >= 2`
- [ ] HPA on a **meaningful** metric (RPS, lag), not just CPU
- [ ] Connection pool sized so `pods × workers × pool` < the DB's `max_connections`
- [ ] Resource requests **and** limits set

**Operations**
- [ ] Migrations as a separate Job, backward-compatible with the running code
- [ ] Config from env/secrets, validated at startup, **fails fast** when missing
- [ ] Canary or feature-flagged rollout with automated analysis
- [ ] A runbook linked from every alert
- [ ] Rollback tested, not assumed

---

## Hands-on drills

1. Add a Prometheus middleware labelling by `request.url.path`. Hit `/orders/{random_uuid}` 10,000
   times and count the series in `/metrics`. Fix it with the route template and re-count.
2. Use a `Summary` for latency across 3 instances and try to compute a fleet-wide p99. Then use a
   `Histogram` with `histogram_quantile()` and explain why one works.
3. Set `terminationGracePeriodSeconds: 5` with a 10-second drain. Deploy under load and count the
   failed requests. Raise it and re-run.
4. Remove the `await asyncio.sleep(5)` between failing readiness and draining. Deploy under load and
   observe the 502s from the load balancer.
5. Run a Kafka producer without `flush()` in the shutdown path. Kill the pod mid-produce and count
   the messages that never arrived.
6. Set up a flat "error rate > 1%" alert and feed it a 30-second blip. Then implement the
   multi-window multi-burn-rate version and feed it the same blip plus a slow persistent burn.
7. Implement feature flags with `random()` instead of a stable hash. Refresh the page repeatedly and
   watch the implementation flip.
8. Run `ALTER TABLE ADD COLUMN x NOT NULL DEFAULT 'y'` on a 10M-row table while sending writes.
   Measure the lock duration. Do it in three steps instead.

---

## The 60-second spoken answer

> "I start from SLIs and SLOs — availability as successful over total requests, and latency as the
> proportion under a threshold rather than an average, because averages hide the p99. The SLO is set
> below whatever the SLA promises, and the gap gives an error budget, which I treat as a deployment
> risk budget: budget left means ship freely, budget spent means freeze features and work on
> reliability. For instrumentation it's RED metrics in Prometheus — rate, errors, duration — and the
> thing I'm careful about is cardinality: labelling by raw path instead of route template creates a
> time series per order ID and will OOM your Prometheus, so user IDs and order IDs go in logs and
> traces, never in labels. Logs are structured JSON to stdout with a trace ID injected via a
> ContextVar, so it follows the asyncio task rather than the thread. Tracing is OpenTelemetry with
> tail-based sampling so I keep all the errors and slow requests. I alert on symptoms rather than
> causes — 5xx rate and latency, not CPU — using multi-window burn-rate alerts so a brief blip
> doesn't page anyone, and every page has a runbook. On graceful shutdown, the step people miss is
> failing readiness *first* and then continuing to serve for a few seconds, because the load balancer
> removes you asynchronously — skip that and you get 502s on every deploy. Then drain in-flight
> requests, flush the Kafka producer, close pools, and make sure the grace period exceeds all of it.
> And migrations run as a separate Job, always backward-compatible with the currently-running code,
> because during a rolling deploy both versions are live at once."
