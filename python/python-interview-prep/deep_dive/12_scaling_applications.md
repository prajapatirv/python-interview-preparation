# Deep Dive 12 — Scaling Applications & Handling Challenges

> Runnable companion: [`08_scaling_production_resilience/`](../08_scaling_production_resilience/) —
> retry+backoff, circuit breaker, rate limiter, health checks, graceful shutdown.
> Related deep dives: [Framework development](11_python_framework_development.md) ·
> [Caching](17_caching.md) · [Production stability](19_production_stability_monitoring.md) ·
> [Concurrency](07_concurrency.md)

## What interviewers are actually probing

This is a **systems thinking** round. The question is rarely "how do you scale?" — it's "traffic went
up 20×; what broke and in what order?" They want to hear that you've **watched** a service fall over
and know the sequence: connection pool exhaustion first, then unindexed queries, then a downstream
timeout cascading.

The senior signal is **naming the bottleneck before the solution**, and knowing that "add more pods"
often makes things *worse* (because each pod opens its own connection pool).

---

## Must-know points

- **Horizontal for the app tier, vertical for the database** — until read replicas or sharding.
- **Statelessness is the precondition** for horizontal scaling. Externalise sessions, files, locks.
- **The first thing that breaks at scale is usually database connections**, not CPU.
- **Retry with exponential backoff and jitter**; jitter is not optional.
- **Circuit breakers** prevent a slow downstream from consuming all your workers.
- **Backpressure** (bounded queues) and **load shedding** (drop low-priority work) keep a system
  degraded-but-alive instead of collapsed.

---

## Interview questions and full answers

### Q1. Horizontal vs vertical scaling — which do you prefer for Python services?

| | Vertical (scale up) | Horizontal (scale out) |
|---|---|---|
| **Approach** | Bigger machine — more CPU/RAM | More instances behind a load balancer |
| **Limit** | Hardware ceiling | Effectively unlimited |
| **Cost curve** | **Exponential** at the high end | Roughly **linear** |
| **Downtime** | Usually requires a restart | Rolling deploy, zero downtime |
| **Fault tolerance** | Single point of failure | Survives instance loss |
| **Complexity** | Simple | Services must be **stateless** |

**For Python app tiers, horizontal — and there's a Python-specific reason.** The GIL means a single
process can't use multiple cores for Python bytecode, so a 64-core machine does nothing for one
Python process. You need multiple **processes** regardless — and once you're running multiple
processes, running them on multiple machines is barely any extra work and buys you fault tolerance
and zero-downtime deploys.

**The database is the exception.** Stateful, hard to shard, and consistency matters. The usual
progression:

1. **Vertical** — more RAM (bigger buffer cache) and faster disks. Cheapest fix, and surprisingly
   far-reaching.
2. **Read replicas** — send read traffic elsewhere. Most workloads are read-heavy. Accept replication
   lag; route read-after-write to the primary.
3. **Connection pooling** (PgBouncer) — see Q4/Q5.
4. **Caching** — see [Deep Dive 17](17_caching.md). Often removes the need for everything below.
5. **Partitioning** — split large tables by time or tenant.
6. **Sharding** — last resort. Cross-shard joins and transactions become your problem.

**The sentence that lands well:** "Design stateless from day one — externalise sessions to Redis,
files to S3, scheduled locks to Redis or DynamoDB. That costs almost nothing early and it's the
difference between scaling being a config change and being a rewrite."

---

### Q2. How do you make a Python service stateless?

Every piece of in-process state is a reason two requests from the same user must hit the same
instance. Remove them all.

```python
# WRONG — state in process memory. Breaks the moment you run 2 instances.
_sessions = {}                   # user hits pod B, session is on pod A -> logged out
_upload_cache = {}               # file written to pod A's disk, read request goes to pod B
_rate_limits = {}                # each pod enforces its own limit -> N× the intended rate
_scheduler_ran_today = False     # every pod runs the "daily" job

# CORRECT — externalise everything
import redis.asyncio as aioredis, json

redis = aioredis.from_url("redis://redis-cluster:6379")

async def set_session(token, data, ttl_secs=1800):
    await redis.setex(f"sess:{token}", ttl_secs, json.dumps(data))

async def get_session(token):
    raw = await redis.get(f"sess:{token}")
    return json.loads(raw) if raw else None
```

**The checklist of state to externalise:**

| In-process state | Externalise to |
|---|---|
| Sessions / login state | Redis, or a **stateless JWT** (no server state at all) |
| Uploaded files, generated reports | S3 / object storage |
| Cache | Redis (keep a small in-process L1 for hot keys — see [Caching](17_caching.md)) |
| Rate-limit counters | Redis with atomic `INCR` + TTL |
| Scheduled-job "already ran" flags | A distributed lock (Redis `SET NX`, DynamoDB conditional write) |
| WebSocket connection registry | Redis pub/sub for cross-instance fan-out |
| Background task queues | Celery/SQS/Kafka, not `BackgroundTasks` |
| In-memory feature-flag cache | Fine, **if** it has a short TTL and refreshes |

**The trade-off to name, because it shows depth:** a stateless JWT means no session lookup at all
(fast, infinitely scalable) but you **cannot revoke it** before expiry. Server-side sessions cost a
Redis round-trip but allow instant revocation. Choose by whether immediate logout matters — for a
banking app it does; for a content site it usually doesn't.

**Sticky sessions are a smell.** They "work" until a pod is rescheduled, and they break autoscaling
and rolling deploys. Treat them as a temporary bridge, never a design.

---

### Q3. How do you scale a FastAPI service with Gunicorn + Uvicorn?

```python
# gunicorn.conf.py
workers = 4                          # see the sizing discussion below
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 30                         # kill a worker stuck longer than this
graceful_timeout = 30                # time to drain in-flight requests on shutdown
keepalive = 5
max_requests = 1000                  # recycle workers — bounds any memory leak
max_requests_jitter = 100            # de-synchronise restarts
accesslog = "-"                      # stdout, for container log collection
```

```bash
gunicorn -c gunicorn.conf.py app.main:app
```

**Worker sizing — the nuance people get wrong:**

- **Async workloads: roughly `#cores`.** Each Uvicorn worker has **its own event loop**, and one
  event loop already handles thousands of concurrent I/O-bound requests. More workers than cores
  doesn't increase I/O concurrency; it just adds context switching and multiplies your connection
  pools.
- **Mostly-sync endpoints (`def` handlers): `2–4 × cores`**, since each request occupies a thread
  that spends most of its time blocked.
- **In Kubernetes, consider 1 worker per pod** and scale with replicas. Resource requests/limits
  become meaningful, the HPA works on real signals, and one crashed worker doesn't take three others
  with it.

**`max_requests` with jitter** is the detail worth explaining: recycling workers bounds slow memory
leaks (common with C extensions), and the **jitter prevents all four workers restarting at the same
instant**, which would drop capacity to zero for a moment — a self-inflicted thundering herd.

**Scaling beyond one machine:**

```yaml
# Kubernetes HPA on CPU and a custom metric
minReplicas: 2                        # never 1 — no redundancy
maxReplicas: 20
metrics:
  - type: Resource
    resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
  - type: External                    # scale on what actually matters
    external:
      metric: { name: kafka_consumer_lag }
      target: { type: AverageValue, averageValue: "1000" }
```

**Key point about the CPU metric:** for an **I/O-bound** async service, CPU is a *poor* scaling
signal — the service can be saturated on downstream latency at 20% CPU. Scale on **requests per
second**, **p99 latency**, or **queue depth / consumer lag** instead. Naming that limitation is the
senior answer.

---

### Q4. What are the common bottlenecks when scaling to 20× traffic?

**In the order they actually bite:**

**1. Database connections — almost always first.**
Each pod opens its own pool. 10 pods × 4 workers × 20 connections = **800 connections**, against a
PostgreSQL `max_connections` of 100. New connections are refused, and the errors look like
application bugs. *Fix:* **PgBouncer** in transaction-pooling mode in front of the DB, smaller
per-worker pools, and async drivers that need fewer connections for the same throughput.

**2. Unindexed queries.**
At 1× traffic a 200 ms sequential scan is invisible. At 20× it's a full table scan running 20× as
often, and the database's buffer cache thrashes. *Fix:* `EXPLAIN (ANALYZE, BUFFERS)` on your slowest
queries, add the indexes, check `pg_stat_statements` for total time rather than per-call time — the
worst query is often a fast one called a million times.

**3. Synchronous blocking calls.**
One slow external API holds a worker/thread for its full timeout. Ten such calls exhaust the pool and
**every** endpoint starts timing out, including `/health`. *Fix:* async HTTP (`httpx`), aggressive
**timeouts on every network call** (a missing timeout is an unbounded outage), and **circuit
breakers**.

**4. No caching.**
The same expensive query runs for every request. *Fix:* Redis cache-aside, CDN for static and
cacheable responses. See [Caching](17_caching.md).

**5. Heavy serialisation.**
Large Pydantic models validated and serialised on every response burn real CPU. *Fix:* projections
and partial responses (`fields=` query param), `response_model_exclude`, streaming for large
payloads, and `orjson` as the JSON encoder.

**6. Kafka consumer lag.**
Producers scale with the API; consumers don't automatically. Lag grows until the retention window is
breached and you **lose data**. *Fix:* more partitions **and** more consumer instances (partitions
cap parallelism), batch processing, and lag-based autoscaling. See
[Kafka pipelines](14_kafka_pipelines_delivery_semantics.md).

**7. N+1 queries.** One query for a list, then one per item. 20 rows becomes 21 queries; 2,000 rows
becomes 2,001. *Fix:* `selectinload`/`joinedload` in SQLAlchemy, `select_related`/`prefetch_related`
in Django.

**8. Logging.** Synchronous logging to disk or a network endpoint becomes a bottleneck at high RPS.
*Fix:* log to stdout and let the collector handle shipping; sample debug logs; never log inside a
tight loop.

**The meta-answer, and the one that scores:** "I wouldn't guess — I'd look at p99 latency broken down
by endpoint, the DB connection-pool wait time, and a flame graph from `py-spy`. The bottleneck is
almost never where people assume." See
[Production stability](19_production_stability_monitoring.md).

---

### Q5. How do you implement database connection pooling?

Connections are **expensive** — a PostgreSQL connection costs a backend process and ~5–10 MB. Opening
one per request is both slow (TCP + TLS + auth, ~10–50 ms) and a hard scaling ceiling.

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Created ONCE at startup and shared. Never per request.
engine = create_async_engine(
    settings.db_url,
    pool_size=10,          # persistent connections kept open per worker process
    max_overflow=20,       # extra burst connections, closed when idle
    pool_timeout=30,       # wait this long for a free connection before raising
    pool_recycle=1800,     # recycle after 30 min — beats server/firewall idle timeouts
    pool_pre_ping=True,    # cheap SELECT 1 before handing out — survives DB restarts
    echo=settings.environment == "dev",
)

AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session       # auto-closed, auto-rolled-back on exception
```

**Sizing is the actual question**, and the formula is:

```
total connections = pods × workers_per_pod × (pool_size + max_overflow)
```

With 10 pods × 4 workers × (10 + 20) = **1,200 connections** against `max_connections = 100`. That is
the #1 scaling failure, and it's why "just add more pods" makes things worse.

**The fixes, in order:**

1. **PgBouncer** in **transaction** pooling mode. Thousands of client connections multiplex onto a
   few dozen server connections. *Caveat to mention:* transaction mode breaks session-level features
   — prepared statements (use `prepared_statement_cache_size=0` with asyncpg), `SET` session
   variables, advisory locks, and `LISTEN/NOTIFY`.
2. **Smaller pools.** With async drivers a pool of 5 often serves more throughput than a sync pool
   of 20, because connections aren't idle while the app thinks.
3. **Fewer workers per pod**, more pods.

**The two settings people omit:**

- **`pool_pre_ping=True`** — without it, after a DB failover or restart your pool hands out dead
  connections and every request fails until they're recycled.
- **`pool_recycle`** — cloud load balancers and firewalls silently drop idle TCP connections
  (AWS RDS Proxy at ~30 min, many NATs sooner). Recycling below that threshold avoids the
  "connection reset by peer" mystery.

---

### Q6. Explain auto-scaling in Kubernetes / ECS for a Python service.

**HPA (Horizontal Pod Autoscaler)** adds/removes pods based on metrics:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  scaleTargetRef: { name: order-service }
  minReplicas: 2
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
    - type: External
      external:
        metric: { name: kafka_consumer_lag }
        target: { type: AverageValue, averageValue: "1000" }
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0        # scale up fast
      policies: [{ type: Percent, value: 100, periodSeconds: 30 }]
    scaleDown:
      stabilizationWindowSeconds: 300      # scale down slowly — avoid flapping
      policies: [{ type: Percent, value: 10, periodSeconds: 60 }]
```

**Choosing the metric — the important part:**

- **CPU** is the default and is **wrong for I/O-bound async services**. An asyncio service saturated
  on downstream latency may sit at 15% CPU while queueing badly. You'd never scale.
- **Requests per second per pod** is better for APIs.
- **p99 latency** is closest to user experience but is noisy and can lag.
- **Queue depth / Kafka consumer lag** is the best signal for workers — it directly measures "are we
  falling behind?" Exposed via KEDA or the Prometheus Adapter.

**Operational details that separate experience from theory:**

1. **`minReplicas: 2` minimum.** One pod means no redundancy during a rolling deploy or a node
   failure.
2. **Asymmetric behaviour: scale up fast, down slow.** Scaling down aggressively causes **flapping** —
   scale down, load concentrates, scale up, repeat — and each cycle costs cold starts.
3. **Readiness probes gate traffic.** A new pod must not receive requests until the pool is warm and
   dependencies are reachable, or you'll see a latency spike on every scale-up.
4. **Scaling has a floor set by your dependencies.** Twenty pods against a database that saturates at
   eight is worse than eight — you've added connection contention, not capacity. **Autoscaling the
   app tier can overwhelm the data tier**; that's the trap.
5. **Warm-up cost matters.** If startup takes 40 s (loading an ML model), HPA reacts too late. Use
   `startupProbe`, over-provision, or **predictive/scheduled scaling** for known traffic patterns.
6. **Cluster Autoscaler** must add *nodes* for HPA to place pods on — otherwise pods sit Pending.

---

### Q7. How do you implement retry with exponential backoff?

See [Error handling Q12](08_error_handling.md#q12-design-a-retry-strategy-for-transient-failures) for
the full design discussion. The async version:

```python
import asyncio, random, logging
from typing import Callable

logger = logging.getLogger(__name__)

async def retry_async(
    fn: Callable, *args,
    max_attempts: int = 4,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    deadline: float = 120.0,
    exceptions: tuple = (Exception,),
    **kwargs,
):
    started = asyncio.get_running_loop().time()
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn(*args, **kwargs)
        except exceptions as e:
            elapsed = asyncio.get_running_loop().time() - started
            if attempt == max_attempts or elapsed > deadline:
                logger.error("all %d attempts failed after %.1fs", attempt, elapsed)
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            delay = random.uniform(0, delay)          # FULL JITTER
            logger.warning("attempt %d failed: %s — retrying in %.1fs", attempt, e, delay)
            await asyncio.sleep(delay)                # never time.sleep in async code
```

**Why jitter is mandatory, stated concretely:** a downstream goes down for 30 seconds. A thousand
clients all fail at t=0. Without jitter, all thousand retry at t=1, all fail; all retry at t=2, all
fail; all retry at t=4... The recovering service is hit by a **synchronised wall of 1,000 requests**
at exactly the moment it's most fragile, and it falls over again. With full jitter those retries
spread uniformly across the window and the service recovers.

The AWS Architecture Blog's three variants, worth naming:

| Strategy | Formula |
|---|---|
| No jitter | `min(cap, base * 2**n)` |
| **Full jitter** | `random(0, min(cap, base * 2**n))` — best for herd avoidance |
| Equal jitter | `d/2 + random(0, d/2)` where `d = min(cap, base * 2**n)` |
| Decorrelated | `min(cap, random(base, prev * 3))` |

**Retries must be paired with:** a **total deadline** (the caller's SLA doesn't care about your retry
budget), **idempotency** (or a retry after a partial success double-charges), and a **circuit
breaker** (retrying into a fully-down service just multiplies load).

Use **`tenacity`** in production; be able to write the above from memory in an interview.

---

### Q8. What is the strangler fig pattern for zero-downtime migration?

Replace an old system **incrementally** by routing a growing share of traffic to the new one, until
the old is unused and can be retired. Named after the fig that grows around a host tree and
eventually replaces it.

```python
import random

def route_request(request, feature_flags):
    rollout_pct = feature_flags.get("new_order_service_pct", 0)
    # Hash on a stable key so a given user is CONSISTENTLY routed — not random per request
    bucket = hash(request.user_id) % 100
    if bucket < rollout_pct:
        return forward_to("new-order-service", request)
    return forward_to("legacy-order-service", request)
```

**The consistent-hashing detail matters.** `random.random()` per request means the same user hits
both implementations alternately — if they have different bugs or different cache state, you get
inconsistent behaviour that's almost impossible to debug. Hash on user ID (or tenant, or account) so
each user's experience is stable.

**The process:**

1. **Put a facade in front** — API gateway, proxy, or a routing layer — so clients address one
   endpoint.
2. **Build the new service behind the same contract.**
3. **Shadow / dark launch**: send a *copy* of production traffic to the new service, discard its
   response, and **compare outputs**. This finds behavioural differences with zero customer risk —
   the single most valuable step, and the one most often skipped.
4. **Ramp**: 1% → 5% → 20% → 50% → 100%, watching error rate, p99, and business KPIs at each step.
5. **Keep the old path warm** so rollback is instant.
6. **Retire** the old service once traffic is zero *and* you've waited a full business cycle
   (month-end jobs, quarterly reports).

**Why it beats a big-bang rewrite:** risk is proportional to the traffic share, rollback is a config
change rather than a deploy, and you learn about the differences under real load instead of
discovering them at cutover.

**The hard part to acknowledge:** **shared state**. If both systems write to the same database you
need compatible schemas and migration discipline; if they have separate stores you need dual-writes
or CDC, plus a reconciliation job. Say this — it's where these migrations actually fail.

---

### Q9. How do you scale a Kafka consumer group?

**The fundamental constraint: maximum parallelism within a consumer group equals the number of
partitions.** Consumers beyond that sit idle.

```python
consumer = Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": "order-processor",                          # ALL instances share this
    "partition.assignment.strategy": "cooperative-sticky",  # incremental rebalance
    "max.poll.interval.ms": 300000,                         # max processing time per poll
    "max.poll.records": 500,
    "enable.auto.commit": False,
})
```

**Scaling levers, in order:**

1. **Add consumer instances** with the same `group.id`, up to the partition count. Kafka rebalances
   automatically. With 6 partitions and 3 consumers → 2 partitions each.
2. **Add partitions** if you've hit the cap. **But:** adding partitions **changes the key→partition
   mapping** (`hash(key) % partitions`), so existing keys move and **per-key ordering is broken
   across the change**. Over-provision partitions up front — it's much cheaper than repartitioning.
3. **Batch processing** — `consume(num_messages=500)` and do one bulk DB write instead of 500
   individual ones. Often a 10–50× throughput win, and usually the *first* thing to try.
4. **Parallelise within a consumer** — hand messages to a thread/process pool. But **route by key to
   a fixed worker** if you need per-key ordering, and only commit **contiguous** completed offsets.
5. **Optimise the processing itself.** If each message triggers an N+1 query, more consumers just
   means more load on a database that's already the bottleneck.

**Operational points:**

- **Monitor consumer lag** — it's *the* Kafka metric. Growing lag means you can't keep up; if it
  exceeds the retention window, **you lose data permanently**.
- **`cooperative-sticky`** avoids stop-the-world rebalances (see
  [Kafka core](13_kafka_core.md#q11-what-is-a-rebalance-and-how-do-you-reduce-its-impact)).
- **`max.poll.interval.ms`** must exceed your worst-case batch processing time, or the consumer is
  evicted mid-batch and you get a rebalance storm — which makes the lag worse, which makes processing
  slower. A classic death spiral.
- **Autoscale on lag**, not CPU, using KEDA.

---

### Q10. What is load shedding and backpressure?

Two complementary defences against overload.

**Backpressure** — signal *upstream* to slow down. A bounded queue does this naturally: when it's
full, `put()` blocks, so the producer cannot outrun the consumer.

**Load shedding** — deliberately **drop** low-priority work when overloaded, rather than letting
latency rise for everyone. Return `503` with `Retry-After`.

```python
import asyncio

queue = asyncio.Queue(maxsize=500)          # BOUNDED — this is the backpressure

async def producer():
    async for event in event_stream():
        try:
            queue.put_nowait(event)         # non-blocking attempt
        except asyncio.QueueFull:
            if event.priority == "high":
                await queue.put(event)      # BLOCK for important work -> backpressure
            else:
                metrics.increment("events_shed")   # DROP low-priority -> load shedding
```

**The principle to articulate:** an **unbounded queue is not a buffer, it's a memory leak with a
scheduling problem**. When a consumer is permanently slower than its producer, an unbounded queue
grows until the process is OOM-killed — and you lose *everything* in it, including the work you'd
already accepted. A bounded queue forces the decision (block or drop) while you can still make it
gracefully.

**Where each mechanism lives:**

| Layer | Backpressure | Load shedding |
|---|---|---|
| HTTP API | Bounded worker pool; reject when saturated | 429/503 with `Retry-After` |
| asyncio | `asyncio.Queue(maxsize=N)` | `put_nowait` + catch `QueueFull` |
| Kafka producer | `max.block.ms` — blocks when the local buffer is full | Drop low-priority topics |
| Kafka consumer | `pause()` partitions when downstream is slow | Skip to DLQ after N failures |
| TCP | Flow control (built in) | — |

**Load shedding needs a priority signal** — which is a *product* decision, not a technical one. Shed
analytics events before payment events; shed anonymous traffic before authenticated; shed retries
before first attempts (signalled by an `X-Retry-Count` header). Deciding *what* to drop is the hard
part and worth saying so.

**Adaptive shedding** is the advanced answer: track your own p99 latency or queue wait time and shed
proportionally as it crosses a threshold, rather than using a fixed limit that's wrong at every
traffic level. Netflix's concurrency-limits and Google's adaptive LIFO are the references.

---

## How the pieces fit together

The resilience patterns are complementary, and interviewers like hearing the distinction:

| Pattern | Protects | From |
|---|---|---|
| **Rate limiting** | *Your* service | Too many callers |
| **Circuit breaker** | *A downstream* | *Your* retries hammering it while it's sick |
| **Retry + backoff** | *Your* request | Transient blips |
| **Bulkhead** | The *rest* of your service | One slow dependency eating every worker |
| **Timeout** | *Your* resources | An unbounded wait |
| **Backpressure** | *Memory* | A producer outrunning a consumer |
| **Load shedding** | *Everyone else's latency* | Overload |

**The bulkhead** is the one people forget: separate connection pools / thread pools per downstream,
so a slow payment API can't consume every worker and take your inventory endpoint down with it.

```python
# Bulkhead: independent semaphores per downstream
payment_sem  = asyncio.Semaphore(10)
inventory_sem = asyncio.Semaphore(20)

async def call_payment(x):
    async with payment_sem:               # at most 10 in flight; can't starve inventory
        return await httpx_client.post(...)
```

**And the most under-rated one: set a timeout on every single network call.** A call with no timeout
is an unbounded outage waiting for a network partition. Most HTTP clients default to *no* timeout.

---

## Worked example — the 20× traffic post-mortem

A narrative answer to "walk me through what happened", which is how this is often asked.

> Traffic went from 500 to 10,000 RPS over a marketing launch.
>
> **T+0** — p99 latency climbed from 80 ms to 4 s. CPU was at 30%, so it wasn't compute.
>
> **T+2 min** — errors appeared: `TimeoutError: QueuePool limit of size 10 overflow 20 reached`. The
> HPA had scaled from 4 to 18 pods; each pod × 4 workers × 30 connections meant we were asking
> PostgreSQL for 2,160 connections against `max_connections=200`. **Autoscaling the app tier had
> overwhelmed the data tier.**
>
> **Immediate mitigation** — capped `maxReplicas` at 8 and cut `pool_size` to 5. Latency recovered
> to 600 ms. Still bad, but serving.
>
> **T+20 min** — `pg_stat_statements` showed one endpoint doing an N+1: one query for the order list,
> then one per line item. At 500 RPS that was invisible; at 10,000 it was 200,000 queries/sec.
>
> **Fixes, in order of deployment:**
> 1. `selectinload` on the relationship — 201 queries became 2.
> 2. **PgBouncer** in transaction mode — 2,000 client connections onto 40 server connections.
> 3. **Redis cache-aside** on the product catalogue (15-minute TTL) — 60% of reads stopped hitting
>    the DB at all.
> 4. Changed the HPA to scale on **RPS per pod**, not CPU, since CPU was never the signal.
> 5. Added a **circuit breaker** on the payment API after it started timing out under the new load
>    and consumed our workers.
>
> **The lesson**: the bottleneck was never the Python service. Scaling *it* made things worse.

That structure — symptom → measurement → root cause → ordered fixes → lesson — is what this question
is really asking for.

---

## Hands-on drills

1. Run a service with an in-memory session dict under `gunicorn -w 4`, log in, and refresh until you
   hit a different worker and get logged out. Move sessions to Redis and confirm it stops.
2. Set `pool_size=2, max_overflow=0` and fire 50 concurrent requests. Read the `QueuePool limit`
   error. Compute `pods × workers × pool_size` for your real deployment.
3. Write a retry loop without jitter, simulate 200 clients failing simultaneously, and print the
   retry timestamps. Add full jitter and print again. Compare the distributions.
4. Build an unbounded `asyncio.Queue` with a producer 10× faster than the consumer. Watch RSS grow
   until OOM. Add `maxsize` and observe the producer being throttled instead.
5. Create a Kafka topic with 3 partitions and start 5 consumers in one group. Confirm 2 are idle.
   Add partitions and watch the assignment change.
6. Time `OFFSET 0` vs `OFFSET 500000` on a million-row table. Then add a circuit breaker around a
   downstream you kill mid-test, and measure the latency difference with and without it.
7. Deploy with `minReplicas: 1` and do a rolling update while sending traffic. Count the failed
   requests. Set it to 2 and repeat.

---

## The 60-second spoken answer

> "Horizontal for the app tier — the GIL means one process can't use many cores anyway, so I'm
> running multiple processes regardless, and spreading them across machines buys fault tolerance and
> zero-downtime deploys. The precondition is statelessness: sessions in Redis or a JWT, files in S3,
> rate-limit counters and scheduler locks in Redis. When traffic multiplies, the first thing that
> breaks is almost never CPU — it's database connections, because every pod opens its own pool, so
> pods × workers × pool_size blows past `max_connections`. That's the trap: autoscaling the app tier
> overwhelms the data tier. The fixes are PgBouncer, smaller pools with async drivers, and caching.
> Then it's unindexed queries and N+1s, which are invisible at 1× and fatal at 20×. I'd scale on RPS
> or queue depth rather than CPU, because an I/O-bound async service can be saturated at 15% CPU. For
> resilience I pair retries — transient errors only, exponential backoff with full jitter, a total
> deadline, and idempotent operations — with a circuit breaker per downstream so their outage doesn't
> become mine, bulkheads so one slow dependency can't eat every worker, a timeout on every network
> call, and bounded queues for backpressure. An unbounded queue is a memory leak with a scheduling
> problem. And for migrations I use the strangler fig with consistent hashing on user ID, shadowing
> the new service first so I compare outputs before any customer sees it."
