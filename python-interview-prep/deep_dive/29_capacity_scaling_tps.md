# Deep Dive 29 — Scaling from 100 TPS to 600 TPS

> Runnable companion: [`13_system_design_scenarios/03_capacity_scaling_tps.py`](../13_system_design_scenarios/03_capacity_scaling_tps.py)
> Related deep dives: [12 — Scaling applications](12_scaling_applications.md) ·
> [17 — Caching](17_caching.md) · [18 — Queue architectures](18_queue_architectures.md) ·
> [28 — Observability](28_observability_distributed_systems.md) ·
> [27 — Zero-downtime changes](27_zero_downtime_production_changes.md) ·
> [07 — Concurrency](07_concurrency.md)

## What interviewers are actually probing

*"Traffic is going from 100 TPS to 600 TPS. How do you scale the system?"*

The wrong answer is "add more pods and a cache". It isn't wrong because those are bad ideas — it's
wrong because it's a **guess**, and capacity planning is arithmetic. What they're checking:

1. **Do you measure before you act?** The first move is finding out what one request *costs*. 6× traffic
   is only frightening if you don't know where it lands.
2. **Can you do the arithmetic?** Little's Law gives you concurrency; that gives you worker count, pool
   sizes and partition counts. Senior candidates produce numbers; others produce adjectives.
3. **Do you remove work before buying capacity?** Halving latency halves the fleet you must provision.
   Fixing an N+1 is free and makes the system *faster*; adding 6× the pods is expensive and only makes
   it *survive*.
4. **Do you know the bottleneck is rarely yours?** It's the single write primary, a third-party rate
   limit, or a shared lock. Scaling the app tier in front of those makes things worse.
5. **Do you know overload must degrade, not collapse?** And that ~70% utilization is the planning
   ceiling, because queueing delay goes as `1/(1−ρ)`.

---

## Must-know points

- **Little's Law: `concurrency = arrival rate × latency`.** 600 TPS × 200ms = 120 requests in flight.
  **Halving latency halves the concurrency you must provision** — latency reduction and capacity are
  the same lever.
- **Never plan past ~70% utilization.** M/M/1 response time multiplies by `1/(1−ρ)`: 80% → 5×, 90% →
  10×, 95% → 20×. "CPU is only at 90%" means your p99 is already 10× your service time.
- **Amdahl's Law caps you.** 10% of the request serialised (one lock, one leader, one sequence) means 50
  workers buy 8.5×, not 50×. Find the serial component first.
- **Remove work before adding capacity**, in payoff order: fix N+1 queries → cache hot reads → batch
  writes → move anything the user doesn't wait for onto a queue.
- **Cache maths: `backend load = TPS × (1 − hit_ratio)`.** 0→80% hit removes 480 of 600 TPS; 95→99%
  removes only 24. Most of the win arrives early.
- **Size pools with Little's Law too**: 600 TPS × 8ms of DB time = ~5 concurrent queries → a pool of
  ~7–12. Then check `pods × pool_size` against `max_connections`.
- **Kafka partitions cap consumer parallelism.** Provision 2–3× the target so you can scale out without
  repartitioning (which breaks per-key ordering).
- **Overload must shed, not queue.** A bounded queue + 429 with `Retry-After` keeps p99 bounded; an
  unbounded queue just relocates the outage.
- **Autoscale on p95 latency or queue depth**, not CPU — CPU is a lagging indicator for an I/O-bound
  service.
- **Load-test to 2× the target.** "It was fine at 540 TPS" is not evidence that 600 is safe.

---

## Interview questions and full answers

### Q1. Where do you start?

**By refusing to answer until you have numbers.** Specifically four:

1. **Current latency distribution** — p50, p95, p99, per endpoint. Not the average.
2. **The per-request cost breakdown** — from a trace or a profile: how many milliseconds in app CPU, in
   each DB query, in each outbound call. And **how many calls** of each per request.
3. **The current utilization** of every tier — pods, DB CPU and connections, cache, queue depth.
4. **The shape of the traffic** — is 600 TPS the average or the peak? What's the peak-to-average ratio?
   Is it spiky (a flash sale) or a steady ramp? You provision for the **peak**, and a 3× peak-to-mean
   ratio means 600 average is really 1800.

That last one is the question most candidates never ask, and it changes the answer by a factor of three.

Then build the per-request profile — this *is* the capacity plan:

| component | ms × calls | = ms | max capacity | at 600 TPS | status |
|---|---|---|---|---|---|
| app CPU | 25 × 1 | 25 | 400 TPS | 600 | **BOTTLENECK** |
| auth cache (redis) | 2 × 1 | 2 | 100,000 | 600 | ok |
| db: SELECT order | 8 × 1 | 8 | 1,200 | 600 | ok (50%) |
| db: SELECT items | 6 × **5** | 30 | 1,200 | **3,000** | **BOTTLENECK (N+1)** |
| db: INSERT event | 12 × 1 | 12 | 400 | 600 | **BOTTLENECK (write primary)** |
| payment gateway | 85 × 1 | 85 | **150 (hard)** | 600 | **BOTTLENECK (third party)** |
| email send | 120 × 1 | 120 | 50 | 600 | **BOTTLENECK (shouldn't be here)** |
| **total** | | **282ms** | | | |

Five bottlenecks, and they need five *different* answers. That table is worth drawing on the whiteboard
before saying anything else, because it makes every subsequent decision obvious.

---

### Q2. What is Little's Law and why is it the whole answer?

```
L = λ × W        concurrency = arrival rate × time in system

600 TPS × 282ms = 169 requests in flight at any instant
600 TPS × 120ms =  72 requests in flight
600 TPS ×  50ms =  30 requests in flight
```

**Read it twice. The second reading is the insight: halving latency halves the concurrency you must
provision.** Making a request faster is arithmetically identical to buying servers — except it also
makes customers happier and costs nothing to run.

From concurrency you derive everything:

```python
def workers_needed(tps, latency_s, target_utilization=0.7, per_worker_concurrency=1):
    return math.ceil((tps * latency_s) / (target_utilization * per_worker_concurrency))
```

Two parameters carry all the nuance:

**`target_utilization=0.7`** — never size for 100% (Q3).

**`per_worker_concurrency`** — this is where the sync/async decision shows up as a number:

| Model | Concurrency per worker | Workers for 600 TPS × 120ms |
|---|---|---|
| sync WSGI (gunicorn sync) | 1 | **103** |
| sync + threads (gthread, 8 threads) | ~8 | 13 |
| **asyncio (I/O-bound)** | 50–200 | **3** |

For an I/O-bound service — which almost every web service is, since most of the 120ms is *waiting* —
that's the entire business case for asyncio in one row. The caveat to state: asyncio only helps if the
work is genuinely I/O-bound. One CPU-heavy or blocking call in the event loop stalls every concurrent
request on that worker, which is worse than the sync model. See [07 — Concurrency](07_concurrency.md).

The same equation also sizes **pools** (Q6) and tells you the **in-flight memory**: 169 concurrent
requests × a 2MB working set is 338MB you must have, or you OOM before you saturate CPU.

---

### Q3. Why not plan for 100% utilization?

Because **queueing delay goes to infinity as utilization approaches 1.** From M/M/1, response time
multiplies by `1/(1−ρ)`:

| Utilization ρ | Response time multiplier |
|---|---|
| 50% | 2× |
| 70% | 3.3× |
| 80% | 5× |
| 90% | **10×** |
| 95% | 20× |
| 99% | 100× |

**This is the number to quote when someone says "CPU is only at 85%, we're fine."** At 85% your p99 is
already ~7× your service time, and the next 5% of traffic doubles it again. The curve is not linear;
it's a cliff, and you are standing near the edge.

The companion file simulates it with a 12-worker pool at 20ms service time (capacity 600 TPS):

| offered | util | completed | p50 | p99 | max queue |
|---|---|---|---|---|---|
| 300 | 50% | 9,000 | 20ms | 30ms | 7 |
| 480 | 80% | 14,399 | 21ms | 37ms | 21 |
| 540 | 90% | 16,187 | 23ms | 50ms | 28 |
| 570 | 95% | 17,099 | 28ms | 66ms | 34 |
| **600** | **100%** | 17,936 | **81ms** | **207ms** | **130** |
| **660** | **110%** | 17,987 | **1,353ms** | **2,600ms** | **1,813** |

**Read the last two rows.** Throughput stops improving (it can't exceed capacity) while latency and
queue depth run away. That is what "the site is down" looks like in metrics — not zero throughput, but
unbounded latency. And note that 540 TPS looked completely healthy. **"It was fine at 540" is not
evidence that 600 is safe**, which is why you load-test to 2× the target.

The 30% headroom you keep is not waste. It absorbs: a traffic spike, a GC pause, losing one AZ (which
instantly raises utilization on the rest by 50% in a 3-AZ setup), a slow dependency stretching your
service time, and the deploy that temporarily removes a batch of instances.

---

### Q4. Where is the bottleneck, really?

**Almost never the app tier**, because that's the one tier that's stateless and trivially horizontal.
From the Q1 table, the five bottlenecks and their five *different* answers:

| Bottleneck | Why it's hard | The actual fix |
|---|---|---|
| **app CPU** | it isn't hard | more pods — the easy one |
| **N+1 query** (5 queries/request) | it's a code bug, not a capacity problem | one JOIN or an `IN` query. Removes 2,400 of the 3,000 required TPS |
| **single write primary** | writes can't be replicated away | batch inserts, move writes off the request path, eventually shard |
| **third-party at 150 TPS** | **not yours to scale** | queue + backpressure, negotiate the limit, cache what's cacheable |
| **email at 120ms** | it shouldn't be in the request path at all | publish an event; a worker sends it |

**Two of those cannot be solved by scaling your own code, and naming that is the senior move.** The
payment gateway's 150 TPS cap is a commercial conversation plus a queue on your side; the write primary
needs an architectural change, not a config change.

**And Amdahl's Law sets the ceiling.** If a fraction *s* of the request is serialised — one shared lock,
one single-threaded leader, one global sequence number, one `SELECT FOR UPDATE` on a counter row — then:

| serial fraction | 2 workers | 6 | 12 | 50 | ceiling |
|---|---|---|---|---|---|
| 0% | 2.0× | 6.0× | 12.0× | 50.0× | unbounded |
| 5% | 1.9× | 4.8× | 7.7× | 14.5× | 20× |
| **10%** | 1.8× | 4.0× | 5.7× | **8.5×** | **10×** |
| 25% | 1.6× | 2.7× | 3.2× | 3.8× | 4× |

**With 10% of the request behind one shared lock, 50 pods buy you 8.5×, not 50×.** So the first question
when someone says "we'll just add instances" is *"what's the serial component?"* Common culprits: a
`SELECT … FOR UPDATE` on a shared row, an auto-increment sequence, a distributed lock held for the whole
request, a single-partition Kafka topic, and a leader-only write path.

---

### Q5. What do you do before buying capacity?

**Remove work.** Four changes, in payoff order, on the Q1 profile:

| # | Change | Latency | Load removed |
|---|---|---|---|
| 1 | **Fix the N+1** — 5 queries → 1 JOIN | −24ms | −2,400 DB TPS |
| 2 | **Cache the hot read** — 90% hit ratio | −7.2ms | DB read load ÷ 10 |
| 3 | **Offload the email** to a queue | **−120ms** of *user-facing* latency | the whole email tier leaves the request path |
| 4 | **Batch the writes** — 10 inserts per transaction | −10.8ms | write TPS ÷ 10 |

**282ms → 120ms (2.4×).** By Little's Law that alone cuts required concurrency from 169 to 72 — it
absorbs a large slice of the 6× increase for roughly a week of engineering and **zero** extra
infrastructure. And unlike adding pods, it makes the system *faster* rather than merely survivable.

Note what remains at 120ms: 85ms of it is the payment gateway. Someone else's latency. The only lever
there is to stop waiting for it synchronously — which is an architectural change (accept the order,
charge asynchronously, notify on completion), with real product consequences. Say that; it's the kind of
trade-off they're probing for.

**The cache arithmetic**, which is why caching is nearly always the cheapest first move:

| hit ratio | backend sees | avg latency (2ms cache / 20ms backend) |
|---|---|---|
| 0% | 600 TPS | 20.0ms |
| 50% | 300 TPS | 11.0ms |
| 80% | 120 TPS | 5.6ms |
| 90% | 60 TPS | 3.8ms |
| 95% | 30 TPS | 2.9ms |
| 99% | 6 TPS | 2.2ms |

**Note the shape: 0→80% removes 480 TPS; 95→99% removes 24.** Most of the win arrives early, so chasing
the last few percent of hit ratio is usually wasted effort — while the first 80% is often a day's work.

The things to say about the cache beyond the arithmetic: pick a TTL from how stale the data may be, not
from a round number; protect against **stampedes** (when a hot key expires, N requests all miss
simultaneously); and remember an in-process cache is per-pod, so 4 pods hold 4 copies with 4 different
answers. See [17 — Caching](17_caching.md),
[`07_caching_queues/02_cache_stampede_lock.py`](../07_caching_queues/02_cache_stampede_lock.py) and
[26 — LRU design](26_coding_design_problems.md).

**And the offload is the highest-leverage change of the four**, because it's the only one that removes
a whole tier from the critical path. The rule: **if the user doesn't need to see it before the response,
it doesn't belong in the request.** Emails, webhooks, analytics events, search-index updates, PDF
generation, cache warming. The cost is eventual consistency and a worker fleet to operate — see
[18 — Queue architectures](18_queue_architectures.md).

---

### Q6. How do you size pools, replicas and partitions?

**All three come from Little's Law.** This is the part that shows you've actually done it.

**Connection pool per pod:**

```
600 TPS × 8ms of DB time = 4.8 concurrent queries → pool of 7 with 30% headroom
```

Two failure modes, and the second is the one that takes production down:

- **Too small** → requests queue *waiting for a connection*. That wait is invisible in database metrics
  and looks exactly like "the database is slow" while the database sits idle. The giveaway is
  **saturation** on the pool (waiters > 0) with low DB CPU.
- **Too big** → `pods × pool_size` exceeds `max_connections`. A db.r6g.large tops out around 1,000, and
  each connection costs memory on the server. **With 40 pods × 20 connections you're at 800, and the
  deploy that adds 5 pods takes the database down.** This is a genuinely common outage: the app tier
  autoscales and kills the database.

So: compute the pool from Little's Law, multiply by max pod count, compare with `max_connections`, and
put **pgbouncer or RDS Proxy** in front when that product gets uncomfortable — mandatory for Lambda or
anything serverless, where concurrency is unbounded by design.

**Read replicas:**

```
600 TPS of reads × (1 − 0.9 cache hit) = 60 TPS → one replica is more than enough
```

The replica exists for **failover and analytics**, not for this load. And the thing to raise unprompted
is **replication lag**: reading your own write from a replica returns stale data, so a POST followed by
a GET can 404. The fixes are read-your-writes routing (send a session's reads to the primary for N
seconds after a write), or a monotonic-read token. Don't add replicas without deciding this.

**Kafka partitions:**

```
600 TPS ÷ 100 TPS per consumer = 6 partitions minimum → provision 18 (2-3×)
```

Partition count is the **parallelism ceiling** of a consumer group: you can never have more
usefully-consuming instances than partitions. Over-provision because **increasing partitions later
breaks per-key ordering** (the hash mapping changes, so a key moves partitions and can be processed out
of order relative to its history) and is operationally painful. But not wildly: each partition costs file
handles, memory, and rebalance time. See [13 — Kafka core](13_kafka_core.md).

**Autoscaling:** on **p95 latency or queue depth**, not CPU. For an I/O-bound service CPU is a lagging
indicator — you'll be timing out at 40% CPU because you're waiting on a dependency. And set
`min_replicas ≥ 3` across 3 AZs, because scaling *up* takes minutes (image pull, warm-up) and traffic
spikes take seconds.

---

### Q7. How do you stop overload from becoming an outage?

Capacity planning is never exact, so the system must **degrade** rather than collapse. Four mechanisms,
and all four are in [`08_scaling_production_resilience/`](../08_scaling_production_resilience/):

**1. Timeouts everywhere, each shorter than the caller's.** Without a timeout, "slow" and "broken" are
the same thing and your workers are all parked on a dead dependency. A request budget decomposed down
the stack: 2s at the edge → 1s for the payment call → 200ms per DB query. A timeout longer than the
caller's is useless — the caller has already given up.

**2. A circuit breaker on every external dependency.** After N consecutive failures, stop calling for a
cool-off window and fail fast. This both protects you (workers aren't parked) and protects *them* (you
stop hammering something that's struggling).

**3. Rate limiting per API key.** Protects everyone else from one abusive caller, and makes the capacity
you planned for actually attributable. Token bucket for bursts, sliding window for fairness. Remember
that an in-process limiter is per-pod — 4 pods × "100/min" is 400/min, so a shared limiter needs Redis.

**4. A bounded queue with load shedding.** This is the one people miss:

| offered | completed | rejected | p99 | max queue |
|---|---|---|---|---|
| 600 | 17,833 | 128 | 102ms | 50 |
| 900 | 17,971 | 8,984 | 108ms | 50 |
| 1,200 | 18,036 | 17,915 | 111ms | 50 |

**Throughput stays at capacity and p99 stays bounded at ~110ms regardless of how much load is offered.**
Compare that with the unbounded case in Q3, where 110% load gave a 2,600ms p99 and a queue of 1,813.

The principle: **an unbounded queue doesn't add capacity, it just relocates the failure** — and makes it
worse, because by the time a request is served the client has already timed out, so you did the work for
nothing. A fast 429 with `Retry-After` for 20% of traffic is a strictly better outcome than a slow
failure for 100%. Shed the *cheapest* requests first if you can prioritise (health checks and paying
customers before bulk API users).

**And the related trick: drop work the client no longer wants.** Check a deadline before starting
expensive work — if the request has been queued longer than the client's timeout, discard it rather than
spending capacity on a response nobody will read.

---

### Q8. How do you prove it?

**Load-test to 2× the target, and watch saturation — not throughput.**

1. **Baseline first.** Test the current system at 100 TPS to validate the harness. If your test
   disagrees with production at known load, the test is wrong.
2. **Ramp, don't step.** 100 → 200 → 400 → 600 → 900 → 1,200, holding each for long enough to reach
   steady state (several minutes — a short burst is absorbed by queues and buffers and tells you
   nothing).
3. **Find the knee**, the utilization at which p99 starts climbing non-linearly. That's your real
   capacity, and it will be below the theoretical number.
4. **Watch the leading indicators**, not the throughput graph: queue depth, connection-pool waiters,
   replication lag, Kafka consumer lag, GC pauses, thread-pool queue. Throughput flattening is the
   *last* thing to happen (Q3); saturation moves first.
5. **Use realistic data.** A test with 10 customers each holding 20 orders will not find the query that
   returns 48,000 rows for your biggest customer. Production data distributions matter more than
   production volume.
6. **Test the failure modes too**: kill one AZ mid-test (utilization on the rest jumps 50%), make a
   dependency slow rather than dead (slow is harder than dead), and fill a queue to confirm shedding
   works.
7. **Soak test.** An hour at 600 TPS finds the leak, the unbounded cache and the file-descriptor
   exhaustion that a 5-minute test never will.

Tools: `locust` (Python, scriptable, good for realistic sequences), `k6` (JS, excellent output),
`vegeta`/`hey` (simple constant-rate HTTP). The key property for capacity work is **open-model
load generation** (fire at a fixed rate regardless of response time) rather than closed-model (N virtual
users waiting for each response) — a closed model self-throttles when the system slows and will hide
exactly the cliff you're looking for.

---

### Q9. What does it cost?

Have this conversation before someone else does:

| Approach | Pods | Monthly | Latency |
|---|---|---|---|
| **Brute force**: 6× the fleet at 282ms, sync workers | 242 | ~$16,900 | unchanged, 282ms |
| **After tuning**: 120ms, asyncio, cache + queue | 3 | ~$210 + ~$200 infra | **120ms** |

Those numbers are from the companion's model, so treat them as illustrative — but the *ratio* is real
and it's the point: **scaling well is an order of magnitude cheaper than scaling hard, and the
engineering that gets you there also makes the product faster.** That framing is what gets remembered in
a system-design round, and it's the version of the answer that works on a non-engineering stakeholder
too.

The honest caveats to attach: the engineering time isn't free (call it 2–3 weeks), a cache and a queue
are **new operational surface** (two more things to monitor, two more failure modes, eventual
consistency to explain to product), and asyncio is a real change in how the team writes code — one
blocking call in the event loop undoes it.

---

### Q10. When does the architecture have to change, not just the config?

Worth volunteering, because it shows you know the limits of the approach above. Set `TARGET_TPS = 6000`
in the companion and the bottlenecks that remain are the ones caching and batching cannot fix:

- **The single write primary.** Batching buys you 10×, and then you're out of road. Next steps, in order
  of increasing pain: move writes to an append-only log and project them (CQRS); **shard** by tenant or
  customer ID; or move the write-heavy entity to a store designed for it (DynamoDB, Cassandra).
- **The third-party cap.** At 6000 TPS a 150 TPS gateway means the synchronous charge is impossible.
  The architecture must become asynchronous: accept, queue, charge, notify.
- **Anything global.** One sequence, one lock, one leader, one single-partition topic. These must become
  per-shard or be eliminated.
- **The blast radius.** At 6000 TPS a bad deploy affects 6000 requests/second. That's when **cell-based
  architecture** earns its cost: N independent cells, customers hashed to one, so a failure affects 1/N
  of users. See [27 — Zero-downtime changes](27_zero_downtime_production_changes.md).

**The iteration is the actual job**: fix the bottleneck, re-measure, find the next one. There is always a
next one — the skill is knowing when the current one is worth fixing and when it's time to change shape.

---

## A worked example

**The plan you'd present, as a document, for 100 → 600 TPS in one quarter:**

```
WEEK 1 — MEASURE (no changes)
  - Trace 100 real requests; build the per-component cost table (Q1).
  - Establish the peak-to-mean ratio from 30 days of traffic. [Found: 2.4x, so provision for 1440]
  - Baseline load test at 100 TPS to validate the harness.
  DELIVERABLE: the bottleneck table, and a stated target of 1440 TPS peak, not 600.

WEEKS 2-3 — REMOVE WORK (no new infrastructure)
  - Fix the N+1 on order items: 5 queries -> 1 JOIN.       [-24ms, -2400 DB TPS]
  - Cache the customer/pricing lookup in Redis, 60s TTL,
    with stampede protection.                              [-7ms, DB reads /10]
  - Move the confirmation email and the analytics event to
    Kafka with an idempotent consumer.                     [-120ms user-facing]
  - Batch the order_events inserts, 10 per transaction.    [-11ms, write TPS /10]
  DELIVERABLE: p95 282ms -> 120ms, verified in production behind a flag at 5% then 100%.
  (This step alone takes the required concurrency from 169 to 72.)

WEEK 4 — SIZE AND SCALE
  - Switch the app tier to asyncio workers (I/O-bound):
    Little's Law at 1440 TPS x 120ms = 173 concurrent -> 5 pods at 50/worker, min 3 across AZs.
  - DB pool: 1440 x 8ms = 12 concurrent -> pool of 16/pod. 10 pods max x 16 = 160 connections,
    vs max_connections 1000. Fine. Documented so the next autoscale change rechecks it.
  - Kafka: 1440/100 = 15 partitions minimum -> provision 36.
  - HPA on p95 latency, not CPU. min 3, max 10.

WEEK 5 — PROTECT
  - Timeout budget: 2s edge / 1s payment / 200ms per query.
  - Circuit breaker on the payment gateway and the pricing service.
  - Rate limit per API key in Redis (shared, not per-pod).
  - Bounded queue + 429 with Retry-After; shed bulk API traffic before checkout traffic.

WEEK 6 — PROVE
  - Ramp test to 2880 TPS (2x the 1440 peak). Find the knee.
  - Failure tests: kill one AZ mid-test; make the payment gateway slow (not dead); fill the queue.
  - 1-hour soak at 1440 TPS to catch leaks.
  - Dashboards: RED per service, USE per resource, SLO burn-rate alerts (see deep dive 28).
  DELIVERABLE: a documented tested capacity number, and the three saturation signals to watch.

STILL OPEN, FLAGGED TO PRODUCT (not an engineering decision)
  - The payment gateway's 150 TPS cap: at 1440 TPS the synchronous charge is impossible.
    Either negotiate the limit, or make charging asynchronous -- which changes the customer
    experience (order accepted, then confirmed) and is therefore a product decision.
```

**Why this is the right shape for an answer:** it measures before acting; the peak-to-mean ratio changes
the target in week 1 (600 → 1440) which is the kind of thing that sinks a plan if found in week 6; the
biggest win comes from *removing work* with no new infrastructure; every number is derived rather than
guessed; the connection-count check is written down so the next autoscaling change rechecks it; and the
one thing engineering **can't** decide is escalated rather than quietly assumed.

---

## Hands-on drills

1. Run the companion. Then set `TARGET_TPS = 6000` and identify which bottleneck can no longer be fixed
   by caching or batching. That's where the architecture has to change.
2. In `simulate()`, set `workers=12` and `service_time_ms=40` (capacity 300 TPS) and offer 600. Watch
   `max_queue` grow without bound. That's an unbounded queue hiding an outage.
3. Add `queue_limit=50` to the same run. Compare completed, rejected and p99. Write the one sentence
   you'd use to justify returning 429s to a product manager.
4. Compute `workers_needed` for 600 TPS × 120ms with `per_worker_concurrency` of 1, 8 and 50. That
   spread is the business case for asyncio — and then say what would make it a lie.
5. Print `utilization_latency_multiplier` from 0.5 to 0.99 in 0.01 steps and find where it crosses 10×.
   Memorise that number; it's your autoscaling trigger.
6. For a service you know, compute `max_pods × pool_size` and compare it with the database's
   `max_connections`. If you can't find both numbers in under five minutes, that's the finding.
7. Work out the Kafka partition count for 2,000 TPS at 150 TPS per consumer, then explain what breaks if
   you increase it from 14 to 28 next year.
8. Take your own service's trace and build the Q1 table. Find the component with the least headroom.
   That's your bottleneck, and it's probably not the one you assumed.
9. Run a locust test with an open model (constant arrival rate) and then with a closed model (fixed
   virtual users). Explain why the closed model hides the cliff.

---

## The 60-second spoken answer

> "First I'd refuse to answer until I had numbers — current p50 and p99, the per-request cost in CPU and
> DB time from a trace, and the peak-to-mean ratio, because 600 average with a 2.4× peak is really 1,440
> and that changes everything. 6× traffic is only frightening if you don't know where it lands.
>
> Then the arithmetic. Little's Law: concurrency equals arrival rate times latency. At 600 TPS and 282ms
> that's 169 requests in flight; at 120ms it's 72. So my first move is always to cut per-request work
> rather than buy 6× the fleet — fix the N+1 so five queries become one JOIN, cache the hot reads, batch
> the writes, and move anything the user doesn't wait for, like emails and analytics, onto a queue with
> an idempotent consumer. On a typical profile that's a 2.4× latency cut for about two weeks of work and
> zero extra infrastructure, and it makes the product faster rather than merely survivable.
>
> Then I scale what's left, horizontally, because the app tier is stateless — and for an I/O-bound
> service asyncio changes the worker count from a hundred to a handful, as long as nothing blocks the
> event loop. I size pools with Little's Law too: 600 TPS times 8ms of DB time is about 5 concurrent
> queries, so a pool of 7 to 12 per pod — and then I multiply by max pod count and check it against
> `max_connections`, because the classic way to take a database down is to autoscale the app tier.
> Kafka partitions get provisioned at 2–3× the target, since increasing them later breaks per-key
> ordering. And I autoscale on p95 latency or queue depth, not CPU, because CPU is a lagging indicator
> when you're waiting on I/O.
>
> The bottleneck usually isn't mine to scale. A third-party gateway capped at 150 TPS is a commercial
> conversation plus queueing and backpressure on my side, and a single write primary needs batching now
> and sharding eventually. And Amdahl's Law sets the ceiling: with 10% of the request behind one shared
> lock, 50 pods buy 8.5×, not 50× — so 'what's the serial component?' comes before 'add instances'.
>
> I never plan past about 70% utilization, because queueing delay goes as 1/(1−ρ): at 90% busy the p99
> is already 10× the service time, and the next 5% doubles it. And I protect the system so overload
> degrades instead of collapsing — timeout budgets down the stack, circuit breakers on every external
> call, rate limits per key in Redis rather than per pod, and a *bounded* queue that sheds with 429 and
> Retry-After. An unbounded queue doesn't add capacity, it just relocates the failure and makes it
> worse, because by the time you serve the request the client has gone.
>
> Then I prove it: ramp to 2× the peak, not to the target, with realistic data distributions and an open
> load model, watching saturation signals — queue depth, pool waiters, replication lag — because
> throughput flattening is the last thing to happen. Plus a one-hour soak for leaks and an AZ kill
> mid-test. And I'd bring the cost comparison, because tuning first turned a 242-pod answer into a
> 3-pod answer and improved latency at the same time."
