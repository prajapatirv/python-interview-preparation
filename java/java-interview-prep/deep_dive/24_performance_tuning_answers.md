# Performance tuning answers: API response time, CPU and memory efficiency, measurement tools, Kafka at scale

> **Related:** [05 JVM, GC and performance](05_jvm_gc_performance.md) (the mechanics) ·
> [14 Observability and Splunk](14_observability_splunk.md) · [18 Production troubleshooting](18_production_troubleshooting.md) ·
> [12 Kafka](12_kafka.md) · scenario banks
> [06 API performance tuning](../interview-scenarios/06_api_performance_tuning.md),
> [07 CPU and memory efficiency](../interview-scenarios/07_cpu_memory_efficiency.md),
> [08 Performance measurement tools](../interview-scenarios/08_performance_measurement_tools.md).
> No runnable files of its own: this chapter is the **long-form spoken-answer layer** over those banks.

## What interviewers are actually probing

Real feedback on a senior Java/Spring Boot round flagged four weak areas: API response time and
throughput, CPU and memory efficiency, performance-measurement tools, and Kafka tuning at scale. The
question is never "which Spring property do you set". It is whether you work **evidence-first**:

> **I don't tune configuration based on assumptions. I measure first, identify the bottleneck, make a
> targeted change, load-test it, and validate the improvement using latency, throughput and
> resource-utilisation metrics.**

Say that sentence early. Every answer below is an expansion of it.

## Must-know points

1. **Baseline before change.** p50 / p95 / p99, throughput (RPS/TPS), error rate, CPU, memory, GC pause.
   Without a baseline "it got faster" cannot be proved.
2. **Four golden signals:** latency, traffic, errors, saturation.
3. **One bottleneck at a time.** App CPU, JVM/GC, thread pool, DB query, connection pool, network call,
   downstream service. Fix the biggest, re-measure, repeat.
4. **Response time and throughput are different levers.** Response time = shorten the critical path.
   Throughput = remove saturation and add parallelism or async capacity.
5. **Never just "increase the pool".** Bigger pools move the queue to the database and add context
   switching. Size from measured workload (Little's Law: concurrency = throughput x latency).
6. **Validate with the same load-test scenario**, then roll out in a controlled way and watch production.

## Interview questions and full answers

---

### Q1. How do you tune a backend API for response time and throughput?

**Short answer.** I baseline p50/p95/p99, throughput, errors and utilisation, then use metrics, traces
and profiling to find the one bottleneck. For response time I shorten the critical path (fewer sync
calls, better queries, caching, smaller payloads, timeouts); for throughput I remove saturation (pools,
DB capacity, batching, async, Kafka partitions). I validate with the same load test and release
gradually.

**Technical detail.**

| Goal | Levers | Evidence first |
|---|---|---|
| Response time | parallel calls, query/index fix, caching, payload size, timeouts | trace span breakdown, slow-query log |
| Throughput | pool sizing, batching, async via Kafka, horizontal scale | saturation: pool pending, CPU, DB load |
| Safety | circuit breaker, bulkhead, bounded queues | error and retry rates |
| Proof | same load test, before/after table | p50/p95/p99, TPS, errors, CPU, GC |

#### Deep dive: the framing I open with

Response time and throughput are related but are **not the same problem**, and tuning one can hurt the
other. Response time is *how long one request takes*. Throughput is *how many requests per second the
system completes*. Little's Law ties them: **in-flight requests = throughput x latency**. If latency
doubles at the same traffic, twice as many requests are in flight, which means twice the threads,
connections and memory. That is why a slow dependency tends to take a whole service down.

So I never start by changing a setting. I run a loop: **baseline -> locate -> fix one thing -> re-test
-> compare -> release**.

#### Step 1. Establish the baseline

I capture, for the endpoint in question, under a realistic load profile:

| Signal | Why |
|---|---|
| p50, p95, p99 latency | p50 is the typical user; p99 is what a tail of users actually feel. Averages hide the tail |
| Throughput (RPS/TPS) | the capacity I am trying to raise |
| Error rate (4xx/5xx, timeouts) | a fast API that fails is not fast |
| CPU, heap, GC pause | JVM saturation |
| Thread-pool and connection-pool usage | the usual hidden queue |
| DB latency, downstream latency, Kafka lag | where time really goes |

Example baseline I would write down: *800 TPS, p95 650 ms, p99 1.2 s, CPU 85%, GC pause 150 ms,
errors 1.2%*. The target is stated up front too: *1,200 TPS, p95 under 300 ms, errors under 0.5%*.

#### Step 2. Find the bottleneck, do not guess

Use three instruments in this order:

1. **Metrics** (Actuator/Micrometer, Prometheus, Grafana) say *that* something is wrong and which
   resource looks saturated: CPU, heap, pool wait, DB time.
2. **Distributed tracing** (OpenTelemetry, Jaeger/Zipkin/APM) says *where* the time goes inside one
   request: gateway 20 ms, service 80 ms, PostgreSQL 250 ms, payment API 600 ms.
3. **Profiling** (JFR, async-profiler, thread dump) says *why* inside the JVM: which method burns CPU,
   which lock is contended, which thread is blocked.

The bottleneck is almost always one of: application CPU, GC, thread pool, DB query, connection pool,
network call, or a downstream service. A useful rule: **the bottleneck is the first resource that is
saturated as load rises**. Tuning anything else produces no gain.

#### Step 3. Reduce response time (shorten the critical path)

Work through the trace from the largest span down.

- **Remove or parallelise synchronous calls.** If an endpoint calls three independent services in
  sequence (100 + 150 + 200 ms = 450 ms), call them in parallel with `CompletableFuture` on a
  dedicated, bounded executor: latency becomes the slowest call (about 200 ms). Move anything the
  client does not need *in the response* (audit, email, analytics) off the request path.
- **Fix the database path.** Usually the biggest win. Look for N+1 queries (one query per row; fix with
  fetch join, `@EntityGraph` or a batch fetch), missing or wrong indexes (check `EXPLAIN`), selecting
  whole entities when a DTO projection of three columns will do, unpaginated lists, and long
  transactions that hold a connection while calling another service.
- **Cache what is read-heavy and slow-changing.** Caffeine in-process for very hot, small data; Redis
  when several instances must share it. Set a TTL, a maximum size, and think about invalidation and
  cache stampede (many requests recomputing the same expired key; fix with single-flight or jittered
  TTL).
- **Reduce payload size.** Pagination, field selection, DTOs instead of entity graphs, gzip, avoiding
  double serialisation. Large JSON is CPU on both sides plus network time.
- **Tune pools from data.** Hikari pool size from measured concurrent queries, not "100 to be safe".
  A common healthy pool is small (10-20 per instance); the database has a finite number of useful
  concurrent queries, and pods x pool size must stay under its `max_connections`.
- **Timeouts and controlled concurrency.** Connect and read timeouts on every outbound call, a circuit
  breaker and bulkhead around each dependency, bounded queues. This does not make the happy path
  faster, but it stops one slow dependency from turning p95 into an outage.

Minimal config that matters:

```text
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.connection-timeout=2000
resilience4j.timelimiter.instances.payment.timeout-duration=800ms
```

#### Step 4. Raise throughput (remove saturation, add parallelism)

Throughput stops growing when some resource saturates, so I ask *which one*:

- **CPU saturated** -> profile; cheaper work per request, or scale horizontally.
- **Threads all busy or blocked** -> thread dump; are they waiting on DB, a downstream call or a lock?
  Fix the wait rather than add threads. Java 21 virtual threads help blocking IO, but watch pinning in
  `synchronized` blocks.
- **Connection pool exhausted** -> requests queue for a connection; shorten transactions, fix slow
  queries, add a read replica, or raise the pool only if the DB has headroom.
- **Database at capacity** -> indexes, batching writes (`saveAll` with `batch_size`, JDBC batching),
  read replicas, caching, sharding as the last resort.
- **Synchronous work that could be async** -> accept, return `202`, publish to Kafka via the outbox
  pattern and process in consumers. The API's throughput is now bounded by cheap enqueueing, not slow
  processing.
- **Horizontal scaling** -> stateless instances behind a load balancer with HPA; first make sure the
  shared resource (DB, cache) can take it, otherwise you only move the queue.

**If Kafka is involved:** parallelism is capped by **partition count**, so consumers beyond partitions
sit idle; watch **consumer lag** (latest offset minus committed offset) to see whether consumers keep
up; tune producer `linger.ms` and `batch.size` for batching and compression; check that per-message
processing time (DB write, external call) is the real limit; and batch DB writes in the consumer.

#### Step 5. Validate and release

Re-run the **same** load-test scenario (k6, JMeter or Gatling, using an open arrival-rate model so
slow responses do not hide themselves) and compare the same metrics against the baseline:

| Metric | Before | After |
|---|---|---|
| TPS | 800 | 1,200 |
| p95 | 650 ms | 280 ms |
| p99 | 1.2 s | 500 ms |
| CPU | 85% | 65% |
| GC pause | 150 ms | 50 ms |
| Error rate | 1.2% | 0.2% |

Then a controlled rollout (canary or blue-green), with dashboards and alerts on p95/p99, errors and
saturation, and a rollback criterion agreed before the release.

#### Worked scenario

*"`GET /orders/{id}` p95 is 900 ms at 600 TPS."* Trace shows 650 ms in a query and 150 ms in a
pricing-service call. Plan: add the missing composite index and a projection for the query (650 ms ->
40 ms), cache pricing data for 60 s with Caffeine (150 ms -> about 2 ms on hit), set a 300 ms timeout
with a fallback. Re-test: p95 900 -> 120 ms, same TPS, CPU unchanged. The gain came from two measured
spans, not from touching Tomcat threads.

#### Trade-offs and what can go wrong

- Caching: stale data, invalidation bugs, stampede, memory growth.
- Extra index: slower writes, more storage.
- Async: eventual consistency, duplicate delivery, so consumers must be idempotent.
- Bigger pools: more DB contention, not more throughput.
- Retries without backoff and jitter: amplify an outage (retry storm).

#### Follow-ups with answers

- **Average is 200 ms but p99 is 3 s. Where do you look?** The tail: traces of the slowest requests,
  GC pauses, pool wait time, a single slow shard or downstream, retries, cold caches. Percentiles per
  endpoint and per instance, not the average.
- **Would more threads help?** Only if threads are the saturated resource and CPU and DB have
  headroom. Otherwise it adds context switching and DB contention. Show the pool metric or thread
  dump that proves it.
- **How do you know the DB is the bottleneck, not the app?** Trace span durations, Hikari
  `pending` and `usage` metrics, slow-query log, and `EXPLAIN` on the suspect query.
- **How do you go from 100 to 1,000 RPS?** Measure the knee with a stress test, find the first
  saturating resource, fix it, repeat; scale out only once the shared resources can absorb it.

**The 60-second answer:** Baseline p50/p95/p99, throughput, errors and utilisation. Use metrics, then
tracing, then profiling to find the single bottleneck. For latency, shorten the critical path: fewer
sync calls, better queries, caching, smaller payloads, right-sized pools, timeouts. For throughput,
remove saturation: pools, DB capacity, batching, async, and for Kafka partitions, lag and batching.
Validate with the identical load test and release gradually.

---

### Q2. How do you use CPU and memory efficiently in a Java application?

**Short answer.** I measure CPU, heap, allocation rate and GC first to see whether the problem is
computation, GC, contention or retention. For CPU I profile with JFR or async-profiler and use thread
dumps; for memory I use GC logs and heap dumps. I remove unnecessary computation, allocation and
retention, bound caches and queues, stream large data, size pools from workload, and validate with load
and soak tests.

**Technical detail.**

| Symptom | Tool | Typical fix |
|---|---|---|
| High CPU | flame graph, JFR | optimise hot method, cheaper serialisation/logging |
| BLOCKED threads | thread dump | shrink critical section, concurrent structures |
| Rising heap floor | heap dump + MAT | bound the cache/collection, remove retention path |
| Frequent young GC | GC log, allocation profile | cut churn on hot paths |
| Big input OOM | heap dump | paginate, stream, bounded queue |
| `OOMKilled` | NMT, container metrics | `MaxRAMPercentage`, cap threads and direct memory |

#### Deep dive: the framing I open with

Efficiency is not "use less". It is **do less unnecessary work (CPU) and hold less unnecessary data
(memory)**, and prove it under load. CPU and memory are linked: **allocation drives GC, and GC
consumes CPU**, so a high allocation rate shows up as CPU and latency, not just as memory.

> CPU efficiency = minimise unnecessary computation and contention.
> Memory efficiency = minimise unnecessary allocation and retention.
> Both must be measured and validated under realistic load.

#### Step 1. Measure first, and split the problem

I look at process CPU, heap used after GC, GC pause and frequency, allocation rate, thread count and
states, and then classify what I see:

| Observation | Probable meaning |
|---|---|
| CPU high, threads RUNNABLE | real computation: a hot method |
| CPU low, latency high, threads BLOCKED/WAITING | contention or waiting on IO, not a CPU problem |
| CPU high with lots of GC | allocation churn |
| Heap after full GC keeps climbing | retention: a leak or unbounded structure |
| Heap fine, container `OOMKilled` | native memory (threads, metaspace, direct buffers) over the limit |

#### Step 2. CPU efficiency

**Find the hot spot, with evidence.**

- **JFR** (Java Flight Recorder) is low-overhead and safe in production. Start a recording during load
  and open it in Java Mission Control for CPU, allocation, locks, GC and IO.
- **async-profiler** produces CPU, allocation, lock and wall-clock **flame graphs**. The widest frame
  at the top is where time goes.
- **Thread dumps** (`jstack` or `jcmd Thread.print`), taken a few times 10 s apart, show whether
  threads are running or stuck, and on which lock.

A typical CPU profile reads: JSON serialisation 35%, business logic 25%, GC 20%, lock contention 10%,
other 10%. Now the work is targeted: fix serialisation first.

**Typical causes and fixes**

- Excess serialisation or mapping: smaller DTOs, reuse the `ObjectMapper`, avoid converting twice.
- Expensive logging: string concatenation and debug logging in a hot path; use parameterised logging,
  guard or lower the level, and avoid logging whole payloads.
- Regex recompiled per call, repeated reflection, repeated `String.format`: precompile or cache.
- Poor algorithms or data structures: `List.contains` in a loop (O(n^2)) instead of a `Set`.
- Redundant work: repeated identical DB or remote calls in one request; cache within the request.
- **Lock contention:** shrink the critical section, use concurrent collections, stripe or avoid
  shared mutable state.
- **Too much concurrency:** more runnable threads than cores causes context switching. For CPU-bound
  work use about the core count; for IO-bound work size from `cores x (1 + wait/compute)` and then
  measure rather than trust the formula.

#### Step 3. Memory efficiency

**Observe.** Heap used after GC (the "live set"), allocation rate (MB/s), GC frequency and pause.
Enable GC logging (`-Xlog:gc*`). Heap that returns to a stable baseline after GC is healthy even if
the peak looks large; a rising floor is a leak.

**Reduce allocation (churn on hot paths)**

- Avoid boxing in loops (`long` not `Long`, primitive streams), and string concatenation in loops
  (`StringBuilder`).
- Do not copy large collections or arrays needlessly; pre-size collections when the size is known.
- Reuse expensive, thread-safe objects (`ObjectMapper`, `HttpClient`, `DateTimeFormatter`).
- Prefer streaming over materialising intermediate lists.

**Reduce retention (the leak and bloat sources)**

- **Unbounded caches and maps.** Use Caffeine with `maximumSize` and a TTL, not a bare `HashMap`.
- **Unbounded queues** (`LinkedBlockingQueue` with no capacity, `Executors.newFixedThreadPool`'s
  hidden queue). Bound them and choose a rejection policy.
- **`ThreadLocal` not removed** in pooled threads, listeners never deregistered, static collections
  that only grow, sessions kept forever.
- **Large payloads in memory.** Loading a million rows or a 50 GB file into a list.

**Process big data in bounded memory**

- Database: pagination or keyset paging, `fetchSize`/cursor, stream and process in chunks, commit in
  batches.
- Files: read line by line or in chunks, never `readAllBytes` on large input.
- Pipelines: a **bounded queue** between producer and consumer gives back-pressure, so memory is flat
  regardless of input size.

**Investigate a suspected leak**

1. Confirm: heap after full GC trends upward over hours (a soak test).
2. Take heap dumps (`jcmd <pid> GC.heap_dump`) at two points, or one near the limit.
3. Open in **Eclipse MAT**: dominator tree, then "path to GC roots" for the biggest retainer.
4. The answer is a *retention path*, such as `static Map -> entries -> Session -> byte[]`. Remove or
   bound it.

**Containers.** The JVM must fit the pod: use `-XX:MaxRAMPercentage` (for example 70-75) rather than a
fixed `-Xmx` that ignores the limit, remember metaspace, thread stacks and direct buffers sit
*outside* heap, and know that CPU limits cause **CFS throttling**, which looks like random latency
spikes even at modest CPU usage.

```text
-XX:MaxRAMPercentage=70
-Xlog:gc*:file=gc.log
```

#### Step 4. Pools sized from workload

Thread pool and connection pool sizes are an efficiency decision. Too many threads waste memory (each
has a stack) and CPU (context switching); too few starve throughput. Size from measured concurrency
(Little's Law) and the downstream limit, then confirm with a load test. Do not "just increase it".

#### Step 5. Choose the collector last

G1 is a sensible default for most services; generational ZGC suits very large heaps or strict pause
goals; Parallel favours batch throughput. But **fix allocation and retention first**. Tuning GC flags
on top of wasteful code only hides the problem.

#### Step 6. Validate

Run a load test, and a **soak test** (hours) for leaks, and compare before and after on the same
scenario: p95/p99, throughput, CPU, heap-after-GC, GC pause and allocation rate.

#### Worked scenario

*"A service's heap climbs until the pod is OOMKilled every 6 hours."* Heap-after-GC rises steadily, so
it is retention. A heap dump in MAT shows a `ConcurrentHashMap` holding 1.4 GB of per-customer response
objects, populated by a "performance cache" with no eviction. Fix: replace it with Caffeine
(`maximumSize=50_000`, `expireAfterWrite=10m`) and cache a compact DTO, not the full response. Soak
test: heap after GC flat at about 600 MB, no restarts, GC pause 40 ms, and CPU down 12% because GC
work fell.

#### Trade-offs and what can go wrong

- Object reuse and pooling add complexity and thread-safety risk; do it only where the profile
  justifies it.
- Smaller caches mean more misses and more DB load; size by hit-ratio measurement.
- Streaming and chunking trade simplicity for bounded memory.
- Premature micro-optimisation: profile first, JIT already handles a lot.

#### Follow-ups with answers

- **CPU is 100% but throughput is flat. Why?** Likely contention, GC, or spinning/busy threads rather
  than useful work. Flame graph plus thread dump separate the cases.
- **Difference between a heap `OutOfMemoryError` and `OOMKilled`?** The first is the JVM running out
  of heap or metaspace and throwing; the second is the container exceeding its memory limit with
  heap *plus* native memory, killed by the kernel with no Java stack trace.
- **How many threads should the pool have?** CPU-bound: about cores. IO-bound: more, derived from
  wait/compute ratio, then measured; consider virtual threads on Java 21.
- **Do you tune GC?** Only after the logs show GC is the problem, and after reducing allocation.

**The 60-second answer:** Measure CPU, heap, allocation rate and GC and classify the problem. For CPU,
profile with JFR and async-profiler, use thread dumps for contention, and remove unnecessary
computation, logging and over-concurrency. For memory, watch heap-after-GC and allocation rate, use
heap dumps and MAT for retention, bound caches and queues, and stream or paginate big data. Size pools
from workload, pick the collector last, and validate with load and soak tests.

---

### Q3. Which tools and techniques do you use to measure application performance?

**Short answer.** I measure at four levels: application metrics (Actuator, Micrometer, Prometheus,
Grafana), distributed traces (OpenTelemetry), JVM profiling (JFR, async-profiler, thread and heap
dumps), and infrastructure metrics (DB, Kafka, pools), with Splunk for log correlation. I baseline
first, locate with traces, explain with the profiler, and validate with load, stress, spike and soak
tests.

**Technical detail.**

| Question | Tool |
|---|---|
| Is it healthy over time? | Micrometer -> Prometheus -> Grafana |
| Where did the time go? | tracing: OpenTelemetry, Jaeger/Zipkin/APM |
| What happened around then? | Splunk logs by trace id |
| What is the JVM doing? | JFR + JMC, async-profiler |
| Contention or leak? | thread dump, heap dump + MAT, GC logs |
| What breaks under load? | k6 / JMeter / Gatling (load, stress, spike, soak) |

#### Deep dive: the framing I open with

Performance work is **observability + profiling + load testing + bottleneck analysis**. No single
tool is enough, so I measure at four levels:

```text
1. Business / application metrics   what users and the business experience
2. Distributed traces               where time goes across services
3. JVM profiling                    why the JVM behaves as it does
4. Infrastructure metrics           DB, network, Kafka, pools, containers
```

and the guiding principle is: **do not optimise on assumptions; baseline, find the bottleneck,
change, re-measure.**

#### What exactly to measure

| Group | Metrics |
|---|---|
| Latency | p50, p95, p99 per endpoint |
| Traffic | RPS/TPS |
| Errors | error %, timeouts, rejected requests |
| Saturation | CPU, heap, threads, pool usage, queue depth |
| JVM | GC pause and frequency, allocation rate, thread count |
| Dependencies | DB query time, pool wait, downstream latency, Kafka lag |

These map onto the **four golden signals**: latency, traffic, errors, saturation. A line such as
*p95 800 ms, 2,000 TPS, errors 2%, CPU 95%* instantly says "under resource pressure".

#### The toolset, layer by layer

**1. Spring Boot Actuator + Micrometer (application metrics).** Actuator exposes `/actuator/health`
and `/actuator/metrics`; Micrometer is the metrics abstraction that publishes them to a backend.
Meters worth knowing: `http.server.requests` (latency histogram per URI/status), `jvm.memory.used`,
`jvm.gc.pause`, `jvm.threads.live`, `process.cpu.usage`, `hikaricp.connections.active/pending`. Add
**business metrics** too (`payment.success.count`, `payment.failure.count`, `order.processing.time`),
because technical metrics alone do not tell you whether the business is healthy.

**2. Prometheus + Grafana.** Prometheus scrapes and stores time series and drives alert rules; Grafana
builds the dashboards. A good API dashboard shows RPS, p50/p95/p99, error %, CPU, heap, GC, DB-pool
use, and Kafka lag side by side, so correlation is visible.

**3. Distributed tracing (OpenTelemetry, Jaeger, Zipkin, or a commercial APM).** Metrics say *latency
rose*; traces say *where the 1.2 seconds went*:

```text
POST /orders  1.0 s
  order-service       80 ms
  PostgreSQL         250 ms
  payment API        600 ms   <- the bottleneck
  Kafka publish       20 ms
  serialisation       30 ms
```

Know the concept (spans, context propagation, trace id, sampling) more than any vendor.

**4. Logs (Splunk).** Logs explain the *why* around an event: exception, DB timeout, external timeout,
Kafka error, deployment. Correlate by trace id. Use SPL for `perc95/perc99` by endpoint and release,
but do not use logs as the only performance source.

**5. JFR + Java Mission Control (JVM profiling).** JFR records CPU, allocation, GC, threads, locks,
IO and exceptions with low overhead, so it is acceptable in production. JMC analyses the recording.
Start one with `jcmd <pid> JFR.start duration=60s filename=rec.jfr`.

**6. async-profiler.** Sampling profiler for CPU, allocation, locks and wall-clock time, producing
flame graphs. Use it to answer "which method?" with evidence instead of guessing.

**7. Thread dump (`jstack`, `jcmd Thread.print`).** A snapshot of thread states. 200 threads with 150
BLOCKED points to a lock or resource problem, not lack of CPU. Take several dumps a few seconds apart.

**8. Heap dump + Eclipse MAT.** For retention and leaks: dominator tree, path to GC roots.

**9. GC logs (`-Xlog:gc*`) and `jstat`.** Frequency, pause time, young vs old, heap occupancy,
allocation rate. Answers "is GC my problem?" before any flag is touched.

**10. JMH.** For micro-benchmarks of a specific code path. Naive timing loops lie because of JIT
warm-up and dead-code elimination.

**11. Load-testing tools (k6, JMeter, Gatling).** Reproduce traffic under control. Model arrival rate
(open model) so slow responses do not reduce offered load; otherwise you suffer **coordinated
omission** and the numbers look better than reality.

**12. Database tools.** Slow-query log, `EXPLAIN (ANALYZE)`, `pg_stat_statements`, Hibernate
statistics, Hikari metrics (active, pending, timeouts), lock waits.

**13. Kafka metrics.** Producer throughput, latency and errors; consumer throughput, **lag**,
rebalances; partition distribution; broker CPU and disk; under-replicated partitions. Lag =
latest offset - committed offset; rising lag means consumers are slower than producers.

#### Types of performance test

| Test | Shape | Answers |
|---|---|---|
| Load | expected traffic, say 1,000 TPS | does it meet the SLO at normal load? |
| Stress | ramp until it breaks | where is the knee and how does it fail? |
| Spike | 500 -> 3,000 TPS suddenly | does it absorb and recover? |
| Soak | steady load for 4-8 hours | leaks (memory, threads, connections), slow degradation |

Example capacity result: 500 TPS p95 120 ms; 1,000 TPS 280 ms; 1,500 TPS 650 ms; 2,000 TPS 1.8 s.
The system saturates between 1,000 and 1,500 TPS. That curve *is* the capacity answer.

#### Putting it into a troubleshooting workflow

```text
Performance problem
   -> establish baseline / what changed (traffic, data, release)
   -> check golden signals
   -> distributed trace: which span is slow?
   -> bottleneck: DB | downstream | Kafka | app CPU | GC | threads
   -> profile: JFR / async-profiler / thread dump / heap dump
   -> targeted fix
   -> load test, compare to baseline
   -> controlled rollout, production monitoring
```

#### Worked scenario

*"The API ran at 500 TPS yesterday with p95 200 ms. Today p95 is 1 second. Investigate."*

1. **Scope and change:** did traffic, data volume or a release change? Compare to yesterday's
   dashboards. Say a deployment went out at 09:10 and the spike starts at 09:12.
2. **Golden signals:** TPS flat, errors up slightly, CPU 40%, heap normal, Hikari pending connections
   climbing. That points away from CPU and toward the database or pool.
3. **Trace:** the slow span is one SQL call, 800 ms, previously 30 ms.
4. **Logs:** Splunk shows the new release added a query with no index, and a JPA lazy-loading loop.
5. **Fix:** add the index, replace the loop with a fetch join. Re-run the load test at 500 TPS:
   p95 back to 190 ms, pending connections zero. Canary release, watch p95 and errors for a day.

#### Trade-offs and cautions

- Profiling and dumps have overhead and a heap dump pauses the JVM: use JFR and sampling profilers in
  production, dumps deliberately.
- High-cardinality metric labels (user id, full URL) can crash Prometheus.
- Tracing needs sampling to control cost; tail-based sampling keeps the slow ones.
- Load tests are only as good as their data and traffic shape; test with production-like volume.

#### Follow-ups with answers

- **Metrics vs logs vs traces?** Metrics: aggregated numbers, cheap, for alerting and trends. Logs:
  detailed events, for the why. Traces: one request across services, for where.
- **RED vs USE?** RED (rate, errors, duration) for services and requests; USE (utilisation,
  saturation, errors) for resources such as CPU, pools, disks.
- **What alerts would you set?** SLO-based: p95/p99 above the target, error rate, saturation, and
  burn-rate alerts on the error budget, rather than raw CPU thresholds.
- **How do you profile in production safely?** JFR or async-profiler with sampling, short windows,
  during real load, with the team informed; avoid heavyweight agents.

**The 60-second answer:** I measure at four levels: application metrics through Actuator and
Micrometer into Prometheus and Grafana, distributed traces with OpenTelemetry, JVM profiling with JFR
and async-profiler plus thread and heap dumps, and infrastructure metrics for DB, Kafka and pools,
with Splunk for log correlation. I baseline first, locate the bottleneck from the trace, explain it
with the profiler, validate with load, stress, spike and soak tests, and release gradually.

---

### Q4. How do you measure Kafka performance? What do you watch on producers, consumers and brokers?

**Short answer.** I watch three stages. Producer: send rate, request latency, errors and retries,
batch size and buffer pressure. Broker: bytes in/out, IO and network thread idle percent,
under-replicated partitions, disk and CPU, balance. Consumer: lag per partition and its trend, consume
rate, poll interval and rebalances. The pattern of lag (all partitions, one, or saw-tooth) tells me
which stage is the limit.

**Technical detail.**

| Stage | Key metrics | Bad sign |
|---|---|---|
| Producer | `record-send-rate`, `request-latency-avg`, `record-retry-rate`, `batch-size-avg` | retries up, tiny batches |
| Broker | `UnderReplicatedPartitions`, `RequestHandlerAvgIdlePercent`, bytes in/out | under-replicated > 0, idle < 30% |
| Consumer | `records-lag-max`, `records-consumed-rate`, `rebalance-rate-per-hour` | lag growing, frequent rebalances |

#### Deep dive: the framing I open with

Kafka is a pipeline: **producer -> broker (network, disk, replication) -> consumer**. A problem anywhere
shows up as the same symptom, rising end-to-end latency or lag, so I measure all three stages and
look for the first one that is saturated.

```text
Producer ----> Broker (network threads -> request queue -> IO threads -> disk -> replicas) ----> Consumer
 send rate,     bytes in/out, request latency,                                        consume rate,
 latency,       ISR health, disk, CPU, controller                                     lag, rebalances,
 errors, batch                                                                         poll interval
```

The one number that summarises health is **consumer lag**, but it is a *symptom*; the cause is found
in the other metrics below.

#### Producer metrics

| Metric (client JMX / Micrometer) | What it tells me | Bad sign |
|---|---|---|
| `record-send-rate`, `byte-rate` | producer throughput | below the arrival rate: backpressure |
| `request-latency-avg/max` | broker round-trip per request | rising: broker or network slow, or `acks=all` waiting on replicas |
| `record-error-rate`, `record-retry-rate` | failed or retried sends | retries rising: broker unavailable, ISR shrink, timeouts |
| `batch-size-avg`, `records-per-request-avg` | batching effectiveness | tiny batches: `linger.ms` is 0, so many small requests |
| `compression-rate-avg` | bytes saved | near 1.0: data does not compress or compression off |
| `buffer-available-bytes`, `bufferpool-wait-time` | `buffer.memory` pressure | near 0 or waits: producer blocks in `send()` |
| `produce-throttle-time` | broker quotas | non-zero: you are being throttled |

#### Consumer metrics

| Metric | What it tells me | Bad sign |
|---|---|---|
| `records-lag-max`, per-partition `records-lag` | backlog | growing, or uneven across partitions (hot key / slow instance) |
| `records-consumed-rate`, `bytes-consumed-rate` | consumer throughput | below the produce rate |
| `fetch-latency-avg`, `fetch-size-avg` | fetch efficiency | many tiny fetches: `fetch.min.bytes` too low |
| `commit-latency-avg` | offset commit cost | high: sync commit per record |
| `rebalance-rate-per-hour`, `rebalance-latency-avg` | group stability | frequent rebalances: lag spikes each time |
| `time-between-poll-max`, `last-poll-seconds-ago` | processing time per batch | approaching `max.poll.interval.ms`: about to be kicked out |
| `poll-idle-ratio-avg` | idle vs busy consumer | near 0: consumer is the bottleneck; near 1: it is waiting for data |

**Consumer lag** per partition = log end offset - committed offset. Read it with
`kafka-consumer-groups.sh --describe --group <g>`, or in Grafana via Micrometer's
`kafka.consumer.*` meters, Burrow or kafka-lag-exporter. Two things matter: the **trend** (growing
vs stable) and the **distribution** (all partitions, or one?). Lag in messages should be converted
into **time lag** (lag / consume rate) because "50,000 messages" means little but "8 minutes behind"
is an SLO statement.

#### Broker and cluster metrics

| Metric | Meaning | Bad sign |
|---|---|---|
| `UnderReplicatedPartitions` | followers behind the leader | > 0 sustained: broker down, slow disk or network |
| `OfflinePartitionsCount`, `ActiveControllerCount` | availability | offline > 0; controller count != 1 |
| `IsrShrinksPerSec` / `IsrExpandsPerSec` | replica flapping | frequent shrinks: instability |
| `BytesInPerSec`, `BytesOutPerSec` per broker | load and balance | one broker far above the rest |
| `RequestHandlerAvgIdlePercent` | IO thread headroom | below about 0.3: IO threads saturated |
| `NetworkProcessorAvgIdlePercent` | network thread headroom | below about 0.3: network threads saturated |
| `RequestQueueSize`, request total time | queuing | queue growing, latency broken down into queue/local/remote/response |
| Disk usage, disk IO wait, `LogFlush` time | storage | disk filling before retention frees it; slow flush |
| CPU, network bandwidth, page-cache hit | host resources | NIC near line rate; reads missing page cache |
| Partition and leader distribution | balance | one broker leads a disproportionate number of partitions |

#### Reading the symptoms (the useful part)

| What I see | Likely cause | Next check |
|---|---|---|
| Lag growing on **all** partitions | consumers too slow overall, or input surge | processing time per record, downstream (DB) latency, `poll-idle-ratio` |
| Lag on **one** partition | hot key, skewed partitioner, one slow instance | key distribution, bytes-in per partition, that consumer's GC and CPU |
| Lag spikes in a regular saw-tooth | rebalances | `rebalance-rate-per-hour`, deploys, `max.poll.interval.ms` breaches |
| Producer latency up, retries up | ISR shrink, broker or disk issue | `UnderReplicatedPartitions`, broker disk, network |
| `bufferpool-wait` high | producer outpacing broker or `buffer.memory` too small | broker request latency, batching and compression |
| Under-replicated partitions after a restart | follower catching up | wait and watch; check `num.replica.fetchers`, throttle |
| Broker CPU high, IO threads idle low | compression, TLS, too many partitions or small requests | request mix, batching, partition count per broker |

#### Worked scenario

*"Orders are processed 15 minutes late at peak."* Dashboard: lag grows linearly on all 12 partitions
during peak, consume rate is 4,000 msg/s against 6,500 msg/s produced, `poll-idle-ratio` is about 0.05
(consumers are busy, not waiting), and `time-between-poll-max` is 40 s. The consumer trace shows 4 ms
per message in a single-row DB insert. So the consumer is the bottleneck, not Kafka. Fix: batch the
inserts (`saveAll` with JDBC batching) and raise `max.poll.records` modestly. Consume rate reaches
11,000 msg/s and lag drains in 6 minutes; the broker was never the limit.

#### Follow-ups with answers

- **Lag is zero. Are we fine?** Not necessarily: check end-to-end latency (produce timestamp to
  processed time), error and DLQ rates, and that the consumer is actually committing.
- **How do you alert on lag?** On *time lag* or sustained growth, not a fixed count, and alert
  separately on rebalance rate and under-replicated partitions.
- **Why can lag be high while consumers are idle?** Fewer partitions than the work needs (cannot
  parallelise), a stuck rebalance, or a poll loop blocked on a downstream call.

**The 60-second answer:** I watch three stages. Producer: send rate, request latency, errors and
retries, batch size, buffer pressure. Broker: bytes in/out, IO and network thread idle percent,
under-replicated partitions, ISR shrinks, disk and CPU, partition balance. Consumer: lag per partition
and its trend, consume rate, poll interval, and rebalances. I turn lag into time lag, and use the
pattern (all partitions, one partition, saw-tooth) to find whether the producer, broker or consumer
is the limit.

---

### Q5. Tuning Kafka configuration for handling large scale of traffic

**Short answer.** I size partitions from throughput and consumer parallelism with replication 3 and
`min.insync.replicas=2`. On the producer I batch with `linger.ms`, `batch.size` and compression, with
idempotence and `acks=all`. On the consumer I size `max.poll.records` to processing time, use
cooperative rebalancing, commit after processing and batch downstream writes. Then I load-test with
realistic data and validate throughput, p99 and lag.

**Technical detail.**

| Layer | Settings |
|---|---|
| Topic | partitions >= max(T/producer-per-partition, T/consumer-per-partition); RF=3; `min.insync.replicas=2` |
| Producer | `linger.ms` 5-20, `batch.size` 64-256 KB, `compression.type=lz4/zstd`, `acks=all`, idempotence |
| Consumer | `max.poll.records`, `max.poll.interval.ms`, `fetch.min.bytes`, cooperative sticky, `group.instance.id` |
| Broker | `num.network.threads`, `num.io.threads`, page cache, disks, balanced leaders |

#### Deep dive: the framing I open with

Tuning Kafka is a **three-way trade-off between throughput, latency and durability**, and every knob
moves one of them. So I start from requirements (messages/s, message size, latency target, whether
loss or duplication is acceptable, ordering needs), tune against measured bottlenecks, and test with a
realistic load.

#### Step 1. Topic and partition design (the biggest lever)

Partitions are the unit of parallelism: **consumer parallelism in a group is capped by partition
count**, and ordering is guaranteed only within a partition.

Sizing rule of thumb: `partitions >= max(target throughput / per-partition producer throughput,
target throughput / per-partition consumer throughput)`, then add headroom for growth. Example: 200 MB/s
target, a partition handles about 10 MB/s produce and 5 MB/s consume (because processing is slow) ->
40 partitions, so 40 consumers can run in parallel.

Cautions:

- You cannot reduce partitions, and **adding partitions changes `hash(key) % count`**, breaking
  per-key ordering for existing keys. Plan ahead; for ordered data create a new topic and migrate.
- More partitions cost more file handles, memory, replication traffic, leader-election time and
  end-to-end latency. Do not create thousands per broker without need.
- A bad key causes a hot partition. Choose a high-cardinality key, or add a salt where ordering is
  not needed for the whole key.
- Replication factor 3 and `min.insync.replicas=2` for important data, with rack awareness.

#### Step 2. Producer tuning

| Setting | Purpose | Typical direction at scale |
|---|---|---|
| `linger.ms` | wait to fill batches | 5-20 ms: more batching, much higher throughput, small added latency |
| `batch.size` | max batch bytes per partition | 64-256 KB (default 16 KB is small) |
| `compression.type` | less network and disk | `lz4` (fast) or `zstd` (better ratio); batches compress better when larger |
| `buffer.memory` | producer buffer | raise if `bufferpool-wait` shows blocking |
| `acks` | durability | `all` for important data; `1` trades durability for latency |
| `enable.idempotence` | no duplicates on retry | `true` (with `acks=all`) |
| `max.in.flight.requests.per.connection` | pipelining | up to 5 with idempotence, ordering preserved |
| `delivery.timeout.ms`, `request.timeout.ms`, `retries` | failure behaviour | bound total send time; do not retry forever |

Also: send asynchronously with a callback, not one blocking `get()` per record; reuse one producer per
JVM; and avoid huge messages (move large blobs to object storage and send a reference).

#### Step 3. Consumer tuning

| Setting | Purpose | Notes |
|---|---|---|
| `fetch.min.bytes`, `fetch.max.wait.ms` | fetch batching | raise `fetch.min.bytes` to cut tiny fetches, at some latency cost |
| `max.partition.fetch.bytes`, `fetch.max.bytes` | bytes per fetch | must exceed the largest message |
| `max.poll.records` | records per poll | size so processing fits well inside the poll interval |
| `max.poll.interval.ms` | max time between polls | exceeded -> consumer is removed -> rebalance |
| `session.timeout.ms`, `heartbeat.interval.ms` | failure detection | heartbeat about a third of session timeout |
| `enable.auto.commit` | commit control | `false`; commit after successful processing |
| `partition.assignment.strategy` | rebalance behaviour | `CooperativeStickyAssignor` to avoid stop-the-world rebalances |
| `group.instance.id` | static membership | restarts do not trigger a rebalance within the session timeout |

Application-level tuning matters more than client settings: **batch the downstream write** (one
batched DB insert rather than per record), keep the poll loop short, and in Spring Kafka set
`concurrency` up to the partition count, use batch listeners where it fits, and acknowledge
explicitly. Handle failures with a retry topic and a dead-letter topic with backoff so one poison
message does not block a partition. Make processing **idempotent**, since delivery is at-least-once.

#### Step 4. Broker tuning and capacity

| Area | What I check or set |
|---|---|
| Threads | `num.network.threads`, `num.io.threads` sized to the idle-percent metrics; `num.replica.fetchers` for replication |
| Durability | `min.insync.replicas=2`, `unclean.leader.election.enable=false` |
| Retention and segments | `retention.ms/bytes`, segment size, so disk never fills; log compaction only where it fits |
| Storage | fast disks (SSD/NVMe), separate log dirs, leave RAM for the **page cache** (Kafka relies on it) |
| Network | NIC bandwidth vs replication x fan-out traffic; TLS adds CPU |
| Balance | even partition and leader distribution; rebalance with Cruise Control or reassignment tooling |
| Quotas | producer/consumer quotas to protect the cluster from one noisy client |

Capacity check: ingest x replication factor for disk and inter-broker network, plus consumer
fan-out for outbound network. If 100 MB/s in with RF=3 and 3 consumer groups, outbound is about
300 MB/s from leaders plus 200 MB/s replication.

#### Step 5. Rebalance and scaling behaviour

- Frequent rebalances destroy throughput. Causes: `max.poll.interval.ms` exceeded, short session
  timeout, deploy churn, autoscaling flapping. Cures: cooperative sticky assignor, static membership,
  right-sized `max.poll.records`, slower scale-down.
- Scaling consumers helps **only up to the partition count**. Beyond that, extra instances idle.
- Scale the DB or downstream with the consumers, otherwise lag moves into the sink.

#### Step 6. Validate

Run a load test with realistic message size and key distribution, using the same dashboards from Q4.
Compare produce throughput, p99 produce latency, consume rate, max lag and time to drain after a
spike, and broker CPU/disk/network, before and after each change. Change one thing at a time.

#### Worked scenario

*"Black-Friday traffic is 10x. Design Kafka for it."* Peak: 50,000 msg/s at 1 KB (about 50 MB/s).
Plan: 48 partitions (headroom over the 40 computed); RF=3, `min.insync.replicas=2`; producer
`acks=all`, idempotence on, `linger.ms=10`, `batch.size=128KB`, `compression=lz4`; consumers 48
instances, `CooperativeStickyAssignor`, `max.poll.records=500`, batched DB writes, DLQ for poison
messages. Load test: 55,000 msg/s sustained, produce p99 35 ms, max lag under 5 s, and drains a
10-minute spike in about 4 minutes. Monitoring: time lag SLO, rebalance rate, under-replicated
partitions, broker idle percent.

#### Trade-offs

- Larger `linger.ms` and batch size: higher throughput, higher per-message latency.
- `acks=all` and replication: safer, slower than `acks=1`.
- More partitions: more parallelism, more overhead, harder ordering.
- Compression: saves network and disk, costs CPU.
- Bigger `max.poll.records`: fewer polls, but risk of exceeding `max.poll.interval.ms`.

#### Follow-ups with answers

- **Exactly-once?** Idempotent producer plus transactions with `read_committed` consumers gives
  exactly-once *within Kafka*; to a database you still need an idempotent write or the outbox/
  transactional pattern.
- **Ordering with many partitions?** Key by the entity that needs ordering; accept order only per
  key; one in-flight request per partition without idempotence, up to 5 with it.
- **Consumers are at the partition limit and still slow?** Optimise per-message work (batching,
  async IO, caching), or hand off to a worker pool while committing offsets only after completion,
  or repartition to a new topic with more partitions.
- **Message too large?** Raise `max.message.bytes`, `max.partition.fetch.bytes` and
  `replica.fetch.max.bytes` consistently, but prefer claim-check (store the blob elsewhere).

**The 60-second answer:** I design partitions from throughput and consumer parallelism, with
replication 3 and `min.insync.replicas=2`. On the producer I batch with `linger.ms`, `batch.size` and
compression, with idempotence and `acks=all`. On the consumer I size `max.poll.records` to the
processing time, use cooperative rebalancing and static membership, commit after processing, batch
downstream writes and make handling idempotent. On the brokers I watch thread idle percent, disk,
network and balance. Then I load-test with realistic data and validate throughput, p99 and lag.

---

### Q6. Your API handled 500 TPS yesterday, but today p95 went from 200 ms to 1 second. How do you investigate?

**Short answer.** Mitigate first if users are hurting (roll back or scale), preserving evidence. Then
establish what changed (traffic, release, data, dependency), compare golden signals with yesterday,
find the slow span with a trace, and drill in with the right tool: slow-query log for DB, JFR for CPU,
GC logs and heap dump for memory, thread dumps for contention. Confirm the cause, make one fix,
reproduce the load, compare with baseline and release by canary.

**Technical detail.**

| Pattern | Reading | Tool |
|---|---|---|
| p50 and p95 up | shared slow resource | trace, DB/pool metrics |
| Only p99 up | subset slow, GC or one instance | per-instance percentiles, GC log |
| Low CPU, high latency | waiting | thread dump, Hikari pending, downstream |
| High CPU | computing more per request | flame graph |
| Step at a deploy time | code or config change | diff, canary compare, rollback |

#### Deep dive: the framing I open with

This is a **regression with a known-good yesterday**, which is the easiest kind of performance problem
because I can compare. The question is "what is *different*": traffic, data, code, configuration,
infrastructure or a dependency. I do not start by tuning; I start by narrowing.

#### Step 0. Stabilise first if users are hurting

If it is a live incident, the first move is mitigation, not diagnosis: roll back the latest release
if the timing matches, scale out if the cause is plain saturation, or shed load and disable a
non-critical feature. Keep evidence (dashboards, a thread dump, a JFR recording) before restarting
anything, because a restart destroys the state you need.

#### Step 1. Establish what changed

| Question | Where I look |
|---|---|
| When exactly did it start? | latency graph; mark the first bad minute |
| Did traffic change (volume, mix, a new client, a retry storm)? | RPS per endpoint and per client |
| Did we deploy or change config or a feature flag? | release and config history around that minute |
| Did data change (table growth, a big tenant, a batch job)? | row counts, job schedule |
| Did a dependency change (DB, cache, downstream, Kafka)? | their dashboards and status |
| Did infrastructure change (node, autoscaling, network, certificate)? | cluster events, pod restarts |

A sharp step at a deploy time points to code or config. A slow climb over days points to data growth
or a leak. A recurring pattern (every hour) points to a scheduled job, cache expiry or GC.

#### Step 2. Compare against the baseline using the golden signals

I put yesterday and today side by side for the affected endpoint: p50, p95, p99, throughput, error
rate, CPU, heap and GC pause, thread count, thread-pool queue, Hikari active/pending, downstream
latency, and Kafka lag if relevant. The *shape* is diagnostic:

| Pattern | Reading |
|---|---|
| p50 and p95 both up | every request is slower: a shared resource or a common slow call |
| p50 flat, p95/p99 up | a subset is slow: one tenant, one query path, GC pauses, a cold cache, one instance |
| Throughput flat, latency up, CPU low | waiting, not computing: DB, pool, lock, downstream |
| Throughput flat, latency up, CPU high | computing more per request: code, serialisation, GC |
| Errors rising with latency | timeouts and retries are amplifying it |
| One pod much worse than others | node issue, noisy neighbour, bad instance, CPU throttling |

#### Step 3. Trace to find the slow span

Distributed tracing breaks the 1 second into its parts:

```text
GET /orders/{id}  1,000 ms      (yesterday: 200 ms)
  service logic        30 ms
  DB query            780 ms    <- was 40 ms
  pricing API         150 ms
  serialisation        40 ms
```

Now I know where to dig. Compare a slow trace with a baseline trace of the same endpoint.

#### Step 4. Drill into the bottleneck family

**If the time is in the database.** Check the slow-query log and `EXPLAIN (ANALYZE)` of that query:
a changed plan (a sequential scan after statistics or data growth), a missing index, lock waits, an
N+1 introduced by a code change, or a long transaction. On the app side check Hikari `pending` and
`active`: if requests queue for a connection, the cause is slow queries holding connections, and raising
the pool without fixing the query makes the DB worse.

**If the time is in a downstream service.** Check that service's latency, your timeout and retry
settings, and whether a circuit breaker is open. A retry policy without backoff can double the load on
an already slow dependency.

**If CPU is high.** Record JFR or an async-profiler flame graph under load and read the widest frames:
serialisation, regex, logging, a new loop, or GC. Compare with a profile from a healthy time if one
exists.

**If memory or GC is abnormal.** Look at heap-after-GC, allocation rate and pause times in the GC log.
Rising floor means retention: take a heap dump and analyse in MAT. High allocation rate with frequent
young GC means churn from a new code path.

**If threads are the issue.** Take two or three thread dumps a few seconds apart. Many BLOCKED threads
on one monitor is lock contention; many WAITING in a pool's `take()` is idle; many RUNNABLE in socket
read is waiting on IO; a full pool with a growing queue is saturation.

**If Kafka is involved.** Check consumer lag and whether lag is cause or effect, rebalance frequency,
and whether a synchronous produce with `acks=all` is on the request path with an ISR problem behind it.

**If only some instances are slow.** Check CPU throttling in containers (CFS), node pressure, and
instance-specific GC.

#### Step 5. Confirm the cause before changing anything

State the hypothesis as a testable claim and prove it: "the new query in release 4.12 has no index, so
at 500 TPS it holds 780 ms of connection time." Evidence: the trace span, the plan, the pool metric,
and the deploy time all agree. If only one signal supports it, keep looking.

#### Step 6. Make one targeted fix

Examples matched to causes: add or correct an index or rewrite the query; replace the lazy-loading loop
with a fetch join; add a timeout, backoff and circuit breaker around the slow dependency; cache a
repeated lookup; cut payload or remove double serialisation; bound a runaway cache; reduce lock scope.
Increase pool capacity only when the database has measured headroom.

#### Step 7. Verify, release carefully, prevent recurrence

- **Reproduce** the workload (500 TPS, same data volume and mix) with k6, JMeter or Gatling and
  compare p50/p95/p99, throughput, error rate, CPU, memory and GC with the baseline.
- **Release** by canary or blue-green with a rollback condition (for example p95 above 300 ms for 5
  minutes), and watch the same dashboards.
- **Prevent:** add a performance check in CI or pre-release for hot endpoints, an SLO and burn-rate
  alert on p95, a slow-query alert, and a post-incident note on the cause.

#### Worked scenario

*Release 4.12 went out at 09:10; p95 rose at 09:12.* TPS unchanged at 500, errors 0.3%, CPU 38%, heap
normal. Hikari `pending` jumped from 0 to 25. Trace: a single SQL span at 780 ms. The slow-query log
shows `SELECT ... WHERE customer_ref = ?` doing a sequential scan on a 40-million-row table; release
4.12 added the filter without an index. Mitigation: roll back to 4.11 at 09:35, p95 back to 210 ms.
Fix: add an index on `customer_ref` (built concurrently), re-deploy. Load test at 500 TPS: p95 190 ms,
pending connections 0, CPU 40%. Canary at 10% for 30 minutes, then full rollout. Follow-up: query-plan
review added to the release checklist.

#### What I do not do

- Restart pods first and lose the evidence.
- Increase the thread pool, heap or connection pool "to see if it helps".
- Look at CPU only.
- Change several things at once, so the cause stays unknown.
- Declare victory without the before/after table.

#### Follow-ups with answers

- **Nothing was deployed and traffic is the same. Now what?** Data growth, a dependency, a scheduled
  job, certificate or DNS change, a noisy neighbour, or a cache that expired or was evicted. Check
  dependency dashboards and infrastructure events and compare table sizes and plans.
- **p95 is bad but you cannot reproduce it.** Use production traces and percentiles per instance,
  per tenant and per endpoint; add targeted tracing or a short JFR recording during the window.
- **How long do you spend before mitigating?** If a recent release correlates, roll back first
  (minutes), then investigate with calm and evidence.
- **How do you tell a regression from a capacity limit?** A regression changes latency at the same
  load; a capacity limit shows the same code getting slower as load rises. The load-test knee curve
  separates them.

**The 60-second answer:** I first mitigate if users are affected, preserving evidence. I establish what
changed (traffic, release, data, dependency, infrastructure) and compare golden signals with
yesterday's baseline, reading the shape of the change. I use a distributed trace to find the slow
span, then drill in with the right tool: slow-query log and plans for the DB, dependency metrics for
downstream, JFR or async-profiler for CPU, GC logs and a heap dump for memory, thread dumps for
contention. I confirm the cause with several signals, make one targeted fix, reproduce the load,
compare to baseline, and release through a canary with monitoring.

---

## Common mistakes interviewers listen for

- Naming a Spring property or a GC flag before naming a measurement.
- Quoting averages instead of percentiles.
- "Increase the thread pool / heap" as the first move.
- Treating CPU as the only resource; forgetting pools, DB, downstream and Kafka lag.
- Claiming an improvement with no before/after numbers.
- Tuning GC blindly instead of reducing allocation first.
- Load testing with a closed model and trusting the flattering numbers.

## Hands-on drills

1. Expose `/actuator/metrics` on a Spring Boot app and read `http.server.requests` percentiles during
   a 5-minute k6 run.
2. Record JFR during load (`jcmd <pid> JFR.start duration=60s filename=rec.jfr`) and find the top CPU
   and top allocating methods in JMC.
3. Take two thread dumps 10 s apart and classify threads RUNNABLE / BLOCKED / WAITING.
4. Reproduce a leak with an unbounded static map, find it with a heap dump in MAT, then fix with a
   bounded Caffeine cache and confirm with a soak run.
5. Write a before/after table for one change and state which signal moved and why.

## The 60-second spoken answer (all three questions)

"I treat performance as measure, locate, fix, validate. I baseline p50/p95/p99, throughput, errors and
resource use. Metrics tell me something is wrong, traces tell me where, JFR or async-profiler tell me
why, and thread and heap dumps cover contention and leaks. For response time I shorten the critical
path; for throughput I remove saturation; for CPU and memory I cut unnecessary computation,
allocation and retention. Then I make one targeted change, repeat the same load test, compare against
the baseline and release gradually. I don't tune on assumptions."
