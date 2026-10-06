# Deep Dive 28 — Observability in a Distributed System

> Runnable companion: [`13_system_design_scenarios/02_observability_pillars.py`](../13_system_design_scenarios/02_observability_pillars.py)
> Related deep dives: [19 — Production stability, alerting & monitoring](19_production_stability_monitoring.md) ·
> [27 — Zero-downtime changes](27_zero_downtime_production_changes.md) ·
> [29 — Capacity scaling](29_capacity_scaling_tps.md) ·
> [15 — Kafka failure handling](15_kafka_failure_handling.md) ·
> [22 — Variable scope (`ContextVar`)](22_variable_scope_namespaces.md)

## What interviewers are actually probing

The question is usually *"how does observability work in a distributed system, and what are its key
components?"* — and the answer "metrics, logs and traces" earns about a third of the marks. What they
want to know is whether you've actually used them at 3am.

Four specific things separate a real answer from a recited one:

1. **Monitoring vs observability.** Monitoring tells you *that* something is wrong, against questions
   you wrote in advance. Observability lets you ask *why*, including questions you didn't anticipate.
2. **Why you need all three pillars** — because each answers a question the others cannot, and because
   **cardinality** forces the split: a user ID cannot go in a metric label, so it has to live in logs
   and spans.
3. **The glue.** Three pillars without a propagated correlation/trace ID are three disconnected
   datasets. The glue is the part people forget, and it's the part that makes an incident debuggable.
4. **SLI → SLO → error budget, and alerting on burn rate and symptoms.** This is what turns telemetry
   into decisions instead of dashboards nobody looks at.

---

## Must-know points

- **METRICS** — cheap, aggregated numbers over time. *"Is it broken, and how badly?"* Counter / gauge /
  histogram / summary. **Latency always goes in a histogram**, never an average. Labels must be
  **low cardinality**.
- **LOGS** — one **structured** event per interesting thing. *"What happened to THIS request?"*
  High-cardinality fields live here. Expensive at volume → sample routine INFO, **never** sample errors.
- **TRACES** — a tree of spans per request across services. *"WHERE did the time go?"* The only pillar
  that shows the call graph.
- **THE GLUE** — a correlation ID minted at the edge (or adopted from the inbound header) and
  propagated everywhere, plus W3C `traceparent` on every outbound call and Kafka message header.
  In Python: `contextvars.ContextVar`, **not** a global and **not** `threading.local()`.
- **Cardinality rule**: `endpoint`, `status`, `region` are fine as labels. `user_id`, `order_id`,
  `correlation_id` are **never** labels — each distinct value is a new time series.
- **RED** for services (Rate, Errors, Duration); **USE** for resources (Utilization, Saturation,
  Errors). The **four golden signals**: latency, traffic, errors, saturation.
- **Saturation is the leading indicator** — queue depth and pool waits predict the outage; latency
  reports it.
- **SLI** = the measurement, **SLO** = the target, **error budget** = `1 − SLO`. Alert on **burn rate**
  (14.4× over 1h → page; ~1.5× over 6h → ticket).
- **Alert on symptoms, not causes.** Error rate and latency page someone; CPU at 85% does not.
- **Tail-based sampling** beats head-based: decide after the trace completes, keep 100% of errors and
  slow traces, 1% of the boring ones.
- **OpenTelemetry** is the vendor-neutral standard: one SDK, one collector, any backend.

---

## Interview questions and full answers

### Q1. What's the difference between monitoring and observability?

**Monitoring** is checking known signals against known thresholds. You decide in advance what to watch
— CPU, error rate, a specific query's latency — and you get alerted when it crosses a line. It answers
questions you already thought of.

**Observability** is the property that lets you answer **new** questions from the data you already
emit, without shipping code. The canonical test: *"can you explain why requests from Android users in
ap-south-1 with a particular feature flag are slow, without adding new instrumentation?"* If you must
deploy to find out, you have monitoring.

The practical difference is **cardinality and context**. Monitoring aggregates — `p99 = 2.4s` — and
aggregation is lossy by design. Observability keeps enough per-event detail (which user, which SKU,
which cache key, which upstream, which pod) to slice after the fact, which is exactly what
high-cardinality fields in logs and spans are for.

The honest framing: **you need both.** Monitoring gives you the page; observability gives you the
answer. The three pillars plus the glue are how you get the second one, and the SLO framework is how
you get the first.

---

### Q2. What are the three pillars, and why do you need all three?

Because **each answers a question the others structurally cannot**:

| Pillar | Answers | Cost shape | Cardinality |
|---|---|---|---|
| **Metrics** | "Is it broken? How badly? What's the trend?" | fixed per time series, independent of traffic | **must be low** |
| **Logs** | "What exactly happened to this one request?" | scales with **volume** — the expensive one | unlimited |
| **Traces** | "Where did the 2 seconds go, across 6 services?" | scales with volume; mitigated by sampling | unlimited |

The companion file runs one deliberately slow request through all three and prints each view. The
punchline:

```
METRICS say THAT it's slow  :  p99 = 898ms   (no idea which request, or why)
LOGS say WHICH request      :  correlation_id=req-a7a046, plus a db.slow_query warning
TRACES say WHERE the time went:
    POST /orders              898.4ms  100%  ########################################
      redis.get                 2.4ms    0.3% #
      postgres.query          846.1ms   94.2% #####################################  <-- here
      http.client inventory     43.6ms    4.9% #
      postgres.query             4.3ms    0.5% #
```

**The cardinality constraint is what forces the split**, and this is the most useful thing to say.
A Prometheus-style metric creates one time series per unique label combination:

```python
metrics.inc("http_requests_total", route="/orders", status="200")       # ~50 series. Fine.
metrics.inc("http_requests_total", order_id=order_id)                   # one series PER ORDER.
                                                                        # 1M orders = 1M series = OOM.
```

So high-cardinality identifiers *have* to go somewhere else — which is logs and span attributes. You
don't use three pillars because it's fashionable; you use three because one of them physically cannot
hold the data you need to answer "which customer?".

**An honest footnote:** the "three pillars" framing is being superseded by **wide structured events**
(the Honeycomb model) — one richly-attributed event per unit of work, from which metrics and traces
are derived. Mentioning that shows you're current. It doesn't change the practical advice, because
OpenTelemetry's span-with-attributes *is* a wide event.

---

### Q3. Metrics: what are the four types, and what are the rules?

```python
counter   = "monotonically increasing total"   # requests, errors, messages, bytes
gauge     = "a value that goes up and down"    # queue depth, in-flight requests, pool size
histogram = "bucketed observations"            # LATENCY. Percentiles computed server-side
summary   = "client-computed quantiles"        # cheaper, but CANNOT be aggregated across instances
```

**The rules, each with the mistake it prevents:**

**1. You never read a counter; you read its rate.** `http_requests_total` is a meaningless number
(it resets on restart). `rate(http_requests_total[5m])` is traffic. Counters are monotonic *so that*
the rate survives scrapes being missed.

**2. Latency goes in a histogram, never a gauge, never an average.** An average hides everything:
if 99% of requests take 50ms and 1% take 10s, the average is 150ms and looks fine, while 1 in 100
customers is timing out. Set your buckets to straddle your SLO threshold — if the SLO is 300ms, you
need a bucket boundary at 300ms, or you cannot measure compliance.

**3. Summaries cannot be aggregated.** A client-computed p99 from each of 20 pods cannot be combined
into a fleet p99 — averaging percentiles is meaningless. Histograms can, because the buckets add. This
is why Prometheus-style monitoring prefers histograms despite the extra storage.

**4. Labels must be low cardinality.** Series count is the product of all label cardinalities, so
`route` (50) × `status` (6) × `method` (4) = 1,200 series — fine. Add `user_id` and you multiply by
your user count. **The symptom of getting this wrong is your monitoring system falling over during an
incident**, which is the worst possible time.

**5. Percentiles from histograms are approximate**, because they're interpolated within buckets. Say
so if asked — claiming an exact p99 from a histogram is a tell.

**What to actually instrument**, in priority order: the RED signals per endpoint; every outbound
dependency's latency and error rate; queue depth and consumer lag; pool utilization *and saturation*;
and the business metric that proves the system is doing its job (orders per minute). That last one is
the most valuable alert you'll ever have, because it catches failures that are invisible in
infrastructure metrics — a deploy that silently stops processing a message type keeps every
infrastructure graph green.

---

### Q4. Logs: what makes a log line useful?

**Structure.** One JSON object per event, not a sentence:

```python
# BAD — needs a regex to query, and breaks the day someone rephrases the message
log.info(f"Order {oid} failed for user {uid} after {ms}ms")

# GOOD — a queryable record: `event="order.failed" AND duration_ms > 1000` works in any backend
log.info("order.failed", order_id=oid, user_id=uid, duration_ms=ms, reason="timeout")
```

**Always included, automatically** (via a logging filter or a `structlog` processor, never by hand at
each call site): timestamp, level, service name, version, pod/host, **correlation ID**, **trace ID and
span ID**. The last two are what let you jump from a log line to the trace and back.

**Never included:** passwords, tokens, card numbers, full request bodies with PII, authorization
headers. Redaction belongs in the logging pipeline, not in the discipline of individual developers —
one forgotten `log.debug(request.json())` is a compliance incident. Test the redactor.

**Levels, with the actual decision rule — "who needs to act?":**

| Level | Meaning | Action |
|---|---|---|
| ERROR | we failed and a human should know | alertable; must carry a traceback |
| WARN | we recovered, but something is wrong | trend-worthy; alert on the *rate* |
| INFO | a business event happened | the audit trail; sampleable |
| DEBUG | developer detail | off in production, or on for a sampled % |

**`logger.exception()` inside an `except` block**, not `logger.error(str(e))` — the first captures the
traceback automatically, the second throws away the only thing that would have told you where it
happened.

**Sampling, and the rule that makes it safe:**

```python
if level == "INFO" and random.random() > sample_rate:
    return            # drop it
# WARN and ERROR are NEVER sampled
```

At 600 TPS, 5 INFO lines per request is 260 million lines a day — real money. So you sample the boring
ones. Two refinements worth naming:

- **Never sample a request that errored.** Once a request is failing, you want *all* of its lines.
  That means the sampling decision has to be per-request (sticky), not per-line.
- **The cost of over-sampling is a p99 spike with no explanation.** You'll have the metric showing it
  and no log line for any affected request. That's the trade-off to state out loud.

---

### Q5. Traces: how do they actually work across a network?

A **span** is one unit of work with a start, duration, status and attributes. A **trace** is the tree
of spans sharing a `trace_id`, linked by `parent_span_id`. The tree is built by propagating a header.

**The W3C `traceparent` header** is the standard:

```
traceparent: 00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01
             ^^ ^-------- trace id (32 hex) ------^ ^-- span id --^ ^^ flags (01 = sampled)
```

Every outbound call injects it; every inbound handler extracts it and makes it the parent of its own
root span:

```python
# HTTP
headers["traceparent"] = current_span.traceparent()

# Kafka — the SAME idea, in a message header. This is the one people forget.
producer.produce(topic, value=payload,
                 headers=[("traceparent", current_span.traceparent().encode())])
```

**Drop that header on one hop and the trace splits into two unconnected halves** — which is the single
most common reason a distributed trace "looks broken". Async boundaries are where it happens: a
message queue, a background task, a thread pool. HTTP is usually handled by auto-instrumentation;
Kafka and Celery usually need you to do it deliberately.

**Span attributes are where high-cardinality data belongs** — exactly what must stay out of metric
labels:

```python
span.set_attributes({"order.id": order_id, "db.statement": sql,
                     "cache.hit": False, "user.tier": "premium"})
```

That's what makes a trace query like *"show me traces where `cache.hit=false` AND `user.tier=premium`
AND duration > 1s"* possible — an ad-hoc question you never pre-aggregated. Follow the OpenTelemetry
semantic conventions for the attribute names (`http.request.method`, `db.system`, `messaging.destination.name`)
so your backend's built-in dashboards work without configuration.

**Sampling: head-based vs tail-based.**

- **Head-based** decides at the root ("sample 1%") and propagates the decision. Cheap and simple, but
  it's a coin flip — the slow request you care about is probably not sampled.
- **Tail-based** buffers the whole trace in a collector, then decides: keep 100% of traces that
  errored or exceeded a latency threshold, plus 1% of normal ones. Far more useful; costs memory in the
  collector and adds a small delay. **This is the right default**, and knowing the distinction is a
  strong signal.

**What traces are bad at:** they show you *one* request. They won't tell you "p99 regressed 20% since
Tuesday" — that's metrics. And they're poor at CPU-level attribution: if a span takes 2 seconds with
no child spans, the trace says "it was slow here" and nothing more. That's what continuous profiling
is for, and it's reasonable to call it a fourth pillar.

---

### Q6. What is the glue, and why does it matter most?

**A correlation ID, minted at the ingress edge or adopted from the inbound header, propagated through
every hop, and stamped on every log line and span.** Without it the three pillars are three datasets
you cannot join, and an incident becomes guesswork.

In Python the right tool is `contextvars.ContextVar`:

```python
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")

@app.middleware("http")
async def correlation_middleware(request, call_next):
    incoming = request.headers.get("X-Correlation-ID")
    token = correlation_id.set(incoming or f"req-{uuid.uuid4().hex[:12]}")
    try:
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id.get()   # give it BACK to the caller
        return response
    finally:
        correlation_id.reset(token)        # ALWAYS reset, or it leaks to the next request
```

**Why `ContextVar` and not the alternatives** — this is a real technical point, not a detail:

- A **module-level global** is shared by every concurrent request in the process. Guaranteed wrong.
- **`threading.local()`** is right for a thread-per-request server and *wrong for asyncio*, because
  thousands of tasks share one thread and would therefore share one value.
- **`ContextVar`** is isolated per asyncio task **and** per thread, and the value propagates into tasks
  you create. It's the only correct answer for a modern Python service.

**Two rules that make it work in practice:**

1. **Adopt the inbound ID, don't overwrite it.** That's what lets you follow one customer's request
   across six services. Overwriting at each hop gives you six unrelated IDs.
2. **Return it in the response header and show it in error bodies.** A customer quoting
   `correlation_id=req-a7a046` to support turns a 40-minute investigation into a single query. And it's
   why a 500 response should contain a correlation ID and **never** a stack trace.

For **async work the ID must travel with the payload**, not with the thread: put it in the Kafka
message header, the Celery task kwargs, the SQS message attribute. Otherwise the trace stops at the
queue — which is exactly where your latency usually is.

---

### Q7. What goes on a dashboard? (RED and USE)

**RED — for request-driven services.** Three graphs per service, in this order:

| | What | Query shape |
|---|---|---|
| **R**ate | requests/sec | `rate(http_requests_total[5m])` |
| **E**rrors | failures/sec, and as a % of rate | `rate(http_requests_total{status=~"5.."}[5m])` |
| **D**uration | the latency **distribution**: p50, p95, p99 | `histogram_quantile(0.99, ...)` |

**USE — for resources** (CPU, memory, disk, connection pools, thread pools, queues):

| | What | Why |
|---|---|---|
| **U**tilization | % of time the resource was busy | the obvious one |
| **S**aturation | how much work is **queued** waiting for it | **the leading indicator** |
| **E**rrors | error events for that resource | often the first hard signal |

**Saturation is the one people forget and the one that predicts the outage.** A connection pool at
100% utilization with 0 waiters is *fine* — it's fully used. At 100% with 50 waiters you are already
failing; the latency graph just hasn't caught up. The same applies to Kafka consumer lag, thread-pool
queue depth, and the run queue. Utilization tells you how busy; saturation tells you how late.

Google's **four golden signals** — latency, traffic, errors, saturation — are the same idea phrased for
services. Whichever framing you use, the dashboard rules are:

- **Top-left is the SLI**, the number that represents the customer experience. Everything else is
  diagnosis.
- **One screen per service**, no scrolling. A dashboard with 40 panels is read by nobody.
- **Dependencies get a row each** (latency + error rate per upstream), because "are we broken or are
  they?" is the first question during an incident.
- **Deploy and flag-flip markers overlaid on the time axis**, because most incidents are caused by a
  change and the correlation should be visible without asking anyone.

---

### Q8. Explain SLI, SLO and error budget — and how you alert on them.

```
SLI  — the measurement:  "fraction of /checkout requests served in <300ms with a non-5xx status"
SLO  — the target:       "99.9% over a rolling 28 days"
ERROR BUDGET — 1 − SLO = 0.1% = about 40 minutes of failure per 28 days
```

**The error budget is the useful part**, and the reason is organisational rather than technical: it's a
**shared currency between product and engineering**. Budget remaining → ship faster, take risks, run
experiments. Budget spent → deploys freeze and the next sprint is reliability work. Nobody has to argue
about whether the system "feels" reliable.

**Alert on burn rate, not on the raw SLI.** Burn rate = how many times faster than "allowed" you're
consuming budget:

| Burn rate | Budget exhausted in | Action |
|---|---|---|
| 14.4× over 1 hour | ~2 days | **PAGE** |
| 6× over 6 hours | ~5 days | **PAGE** |
| 3× over 1 day | ~9 days | ticket |
| 1× | exactly at window end | ticket / watch |

Those multipliers are the standard Google SRE multi-window alerts. Why **multi-window**: a short window
catches a sudden severe outage quickly; a long window catches a slow bleed that a short window would
dismiss as noise. Requiring both a short-window *and* a long-window breach before paging is what
removes false pages from brief blips.

**And alert on SYMPTOMS, not causes.** This is the single most important alerting rule:

```
PAGE on:    customer-facing error rate, p99 latency against the SLO, queue age / consumer lag,
            a business metric flatlining (orders per minute → 0)
DON'T PAGE on: CPU at 85%, memory at 70%, disk at 70%, a single slow query,
               one pod restarting, a transient spike in a dependency
```

Causes are **debugging material**, not alerts. CPU at 90% with latency fine is not a problem; CPU at
30% with latency broken is. Cause-based alerts are how teams end up with 200 alerts nobody reads — and
then miss the real one. The test for any alert: **"if this fires at 3am, is there something a human must
do right now?"** If not, it's a dashboard panel or a ticket, not a page.

**Three more things worth having ready:**

- **Pick the SLI from the customer's perspective.** "Checkout completes" is an SLI. "The orders service
  returns 200" is not — the customer doesn't care which service answered.
- **Don't promise five nines.** Each nine multiplies cost. 99.9% is 40 minutes a month; 99.99% is 4
  minutes, which rules out most human-in-the-loop recovery and therefore demands automation.
- **Measure the SLI where the customer is** (at the load balancer or in the client), not inside the
  service. A service that's up but unreachable scores 100% on its own metrics.

---

### Q9. How do you actually instrument a Python service?

**OpenTelemetry**, with the collector pattern. One SDK, one wire protocol, swap backends without
touching code:

```python
# auto-instrumentation gets you HTTP, DB and client spans with zero code changes
# $ opentelemetry-instrument --traces_exporter otlp --service_name orders-api uvicorn app.main:app

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

@app.post("/orders")
async def create_order(order: OrderIn):
    with tracer.start_as_current_span("validate_order") as span:   # a MANUAL span for YOUR logic
        span.set_attribute("order.item_count", len(order.items))
        validate(order)
    return await service.create(order)
```

The architecture to describe:

```
  app (OTel SDK)  --OTLP-->  OTel Collector (a sidecar or a daemonset)
                                 |-- tail sampling, redaction, batching, enrichment
                                 |--> traces  -> Jaeger / Tempo / Datadog / X-Ray
                                 |--> metrics -> Prometheus / Mimir
                                 `--> logs    -> Loki / ELK / CloudWatch
```

**Why the collector matters** (and why "we send straight to the vendor" is the weaker answer): it's
where tail-based sampling happens (the app can't decide — it doesn't know the trace's outcome yet),
where PII redaction is centralised, and where you change vendors by editing one config instead of
redeploying forty services.

**The practical setup checklist:**

1. Auto-instrumentation first — HTTP, DB, Kafka, Redis spans for free.
2. Manual spans only around *your* business logic, named after the operation.
3. `structlog` (or a logging filter) injecting `correlation_id`, `trace_id` and `span_id` into every
   line automatically.
4. Prometheus client for metrics the SDK doesn't give you — queue depth, business counters.
5. Tail sampling in the collector: 100% of errors and slow traces, 1–5% of the rest.
6. One dashboard per service (RED), one per critical resource (USE), and SLO burn-rate alerts.
7. **Then test it**: run a game day, break something deliberately, and time how long it takes someone
   who didn't break it to find the cause. That number is your observability metric.

**And know the overhead**, because it's a fair follow-up: OTel adds roughly 1–5% CPU with batching
enabled, and a few hundred microseconds per span. Metrics are nearly free. Logs are usually the biggest
line on the bill, which is why sampling is a cost decision, not a technical one.

---

## A worked example

**"p99 on checkout went from 200ms to 2.4s. Find it."** The pillars in sequence:

```
1. METRICS — the alert, and the shape of the problem (30 seconds)
     histogram_quantile(0.99, http_request_duration{route="/checkout"}) = 2.4s
     p50 unchanged at 180ms  -> it is a TAIL problem, not an across-the-board slowdown.
     Error rate flat         -> requests succeed, slowly. Not an outage; a latency regression.
     By label: region="ap-south-1" only. Other regions normal.
     -> Hypothesis space narrowed before anyone opened a log.

2. TRACES — where the time goes (2 minutes)
     Query: traces WHERE route=/checkout AND duration > 2s AND region=ap-south-1
     Tail-based sampling kept 100% of these, so they exist. Waterfall:
        POST /checkout                2380ms 100%
          redis.get customer             2ms
          postgres.query SELECT…      2210ms  93%   <-- here
            . db.statement = SELECT * FROM orders WHERE customer_id = $1
            . db.rows = 48213                        <-- and HERE is the actual reason
          http.client payment           140ms

3. LOGS — which requests, and the detail (1 minute)
     event="db.slow_query" AND duration_ms>1000 AND region="ap-south-1"
     -> all from 3 customer_ids, each with ~50k orders. One of them is a load-test account
        created yesterday.
     Correlation IDs in hand for 3 specific affected requests.

4. THE DIFF — why now (1 minute)
     Deploy markers: a release 14 hours ago removed a LIMIT clause from the order-history query
     during a refactor. Fine for customers with 20 orders; 48,000 rows for the big ones.

   Total: ~5 minutes from page to root cause, because the pillars joined up.
```

**What made that fast, item by item:**

- **The metric had a `region` label** (low cardinality — correct) which eliminated 80% of the search
  space in one click.
- **Tail-based sampling kept the slow traces.** Head-based 1% sampling would very likely have kept
  none of them, and the investigation would have started with "we can't reproduce it".
- **`db.rows` was a span attribute** — high cardinality, which is exactly why it belongs on a span and
  not in a metric label. It's the single datum that explains the whole incident.
- **The correlation ID** connected the metric spike to specific logs to specific customers.
- **Deploy markers on the dashboard** answered "why now?" without asking anyone.

**And the follow-up actions**, because an interviewer will ask: restore the `LIMIT`; add a
`db.rows`-based alert (any query returning >10k rows is a bug waiting to happen); add a slow-query log
threshold; and add a test with a fixture customer holding 50k orders, because the bug was invisible at
small data volumes.

---

## Hands-on drills

1. Run the companion and read the same slow request three ways. Then add `order_id` as a **metric
   label**, run the 40-request loop, and count the distinct series. That's a cardinality explosion in
   miniature.
2. Remove the `traceparent` attribute from the outbound call and describe what the downstream
   service's trace looks like to an on-call engineer.
3. Set the log `sample_rate` to 0.001 and re-run the slow scenario. You now have a p99 spike and no log
   line explaining it. That's the cost/blindness trade-off, live.
4. Compute the error budget in minutes for 99%, 99.9%, 99.95% and 99.99% over 28 days. Decide which you
   would promise for a checkout API, and what automation each one forces.
5. Implement multi-window burn-rate alerting: page only when both a 1h window exceeds 14.4× **and** a
   5m window also breaches. Then simulate a 2-minute blip and confirm it doesn't page.
6. Write a `ContextVar`-based correlation middleware for FastAPI, then deliberately forget the
   `reset(token)` and show the ID leaking into the next request on the same task.
7. Add a Kafka producer that injects `traceparent` into a message header and a consumer that extracts it
   as its parent span. Prove the trace spans the queue.
8. Set histogram buckets that do **not** straddle your SLO threshold, then try to compute SLO
   compliance. Observe that you can't.
9. For a service you own, list every alert and sort them into symptom-based and cause-based. Delete or
   downgrade the cause-based ones. Count how many are left.
10. Run a game day: break something, and time how long it takes a colleague to find the cause using
    only telemetry. That number is the only honest measure of your observability.

---

## The 60-second spoken answer

> "Monitoring tells me *that* something is wrong against questions I wrote in advance; observability
> lets me ask *why*, including questions I didn't anticipate. It stands on three pillars plus the glue
> that joins them.
>
> Metrics are cheap aggregated numbers — counters, gauges and histograms — and they tell me that
> something is broken and how badly. Latency always goes in a histogram, never an average, because an
> average hides a bad tail, and labels stay low-cardinality: route and status are fine, user ID or
> order ID would create a time series per value and take the monitoring system down. Logs are one
> structured JSON event per interesting thing, and they tell me what happened to a *specific* request —
> that's where high-cardinality fields live. I sample routine INFO lines for cost but never errors, and
> the sampling decision is per-request so a failing request keeps all of its lines. Traces are a tree
> of spans per request and they tell me *where* the time went — the only pillar that shows the call
> graph. They propagate with the W3C `traceparent` header on HTTP calls and in Kafka message headers;
> miss one hop and the trace splits in two, which is the usual reason a trace looks broken. I prefer
> tail-based sampling in a collector, so I keep 100% of traces that errored or were slow rather than a
> blind 1%.
>
> The glue is a correlation ID generated at the edge — or adopted from the inbound header, never
> overwritten — held in a `ContextVar` because that's isolated per asyncio task as well as per thread,
> and stamped on every log line and span, with the token reset in a `finally` so it doesn't leak into
> the next request. I return it in the response header, so a 500 gives the customer an ID instead of a
> stack trace.
>
> On top sits the contract: an SLI I measure from the customer's perspective, an SLO I promise, and an
> error budget of 1 minus the SLO — which is a shared currency: budget left means ship faster, budget
> spent means the next sprint is reliability. I alert on multi-window burn rate against that budget —
> 14.4× over an hour pages, 1.5× over six hours opens a ticket — and I alert on symptoms the customer
> feels, never on causes like CPU, because cause-based alerts are how you end up with 200 alerts nobody
> reads. Dashboards follow RED for services and USE for resources, with deploy markers on the time
> axis, and saturation is the signal I watch hardest because queue depth and pool waits predict the
> outage while latency only reports it.
>
> Implementation-wise it's OpenTelemetry with a collector — auto-instrumentation for HTTP and DB,
> manual spans around business logic, tail sampling and PII redaction in the collector, and structlog
> injecting trace IDs into every line. And then I'd test it with a game day, because the only honest
> measure of observability is how long it takes someone who didn't break it to find the cause."
