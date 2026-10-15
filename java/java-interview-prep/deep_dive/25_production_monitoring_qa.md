# Production, monitoring and performance Q&A: short answer, technical detail, deep dive

> **Related:** [24 Performance tuning answers](24_performance_tuning_answers.md) (API/CPU/memory/tools/Kafka) ·
> [18 Production troubleshooting](18_production_troubleshooting.md) · [23 Production scenarios](23_production_scenarios.md) ·
> [14 Observability and Splunk](14_observability_splunk.md) · [12 Kafka](12_kafka.md)

## How to use this chapter (the three-tier format)

Every question has the same three layers, so you can stop at the depth the interviewer wants:

| Tier | Length | Use it when |
|---|---|---|
| **Short answer** | 3-5 sentences, speakable in 30-45 s | the first reply to any question |
| **Technical detail** | tables, commands, settings, numbers | the interviewer says "how exactly?" |
| **Deep dive** | mechanism, worked example, pitfalls, follow-ups | the interviewer probes, or it is a design/RCA round |

**Where these questions come from.** Company-specific lists are thin: no reliable public question list
exists for Google, Nagarro or Persistent. The patterns below come from Infosys Java production-support
job postings (L2/L3 incident ownership, RCA, thread/heap dumps, SQL plans, alert tuning, Splunk and
AppDynamics), EPAM candidate reports (managerial round on production issues you solved), and common
senior-Java scenario banks (memory leak, high CPU, slow API, exhausted connections). Treat it as the
*shape* of these rounds, not a leaked list.

## Cheat sheet

| # | Question | One-line answer |
|---|---|---|
| 1 | Service at ~100% CPU with normal traffic | `top -H` -> hex thread id -> thread dump / flame graph |
| 2 | Heap exhausted every 3-4 days | heap-after-GC rising = retention; two heap dumps, MAT, GC roots |
| 3 | DB connections exhausted | slow queries or leaks hold connections; fix the hold time, not the pool |
| 4 | Kafka lag stuck although consumers look healthy | per-partition lag; poison message, blocked thread or rebalance loop |
| 5 | Liveness vs readiness | restart vs route traffic; never tie liveness to the DB |
| 6 | Which Actuator endpoints in production | expose health/info/prometheus only, on an internal port, secured |
| 7 | High-cardinality metrics and percentiles | bounded tags; histograms aggregate, client percentiles do not |
| 8 | Tracing one request across services | correlation/trace id in every log line and header |
| 9 | Handling a P1 incident and RCA | mitigate, communicate, preserve evidence, RCA, corrective + preventive |
| 10 | What do you alert on and how do you cut noise | user-visible symptoms and SLO burn; resource metrics are diagnostic |
| 11 | "Tell me about a production issue you solved" | STAR with numbers: symptom, evidence, cause, fix, prevention |
| 12 | What do you check after a deployment | golden signals vs baseline, errors, lag, canary, rollback trigger |
| 13 | Tools and techniques to measure performance | metrics = what, tracing = where, profiling = why, load test = did it work |

---

### Q1. A service is at near 100% CPU with normal traffic and pods fail health checks. How do you find the cause?

**Short answer.** Normal traffic with high CPU means each request is doing more work, or something is
spinning. I find the hottest thread with `top -H`, convert its id to hex and match it in a thread dump,
then confirm with a flame graph from JFR or async-profiler. Common causes are a hot loop, regex
backtracking, serialisation, excessive logging or GC, and the fix follows the evidence.

**Technical detail.**

```text
top -H -p <pid>                 # per-thread CPU; note the busiest TID
printf '%x\n' <tid>             # convert to hex
jstack <pid> > dump.txt         # or: jcmd <pid> Thread.print
grep -A 25 'nid=0x<hex>' dump.txt
```

| Finding | Meaning | Next step |
|---|---|---|
| Hot thread is app code in a loop | busy-loop, bad algorithm, unbounded retry | read the stack, fix the loop |
| Hot threads are "GC Thread" / VM threads | GC pressure | GC log, allocation rate, heap dump |
| Many threads RUNNABLE in the same method | hot path (regex, JSON, crypto) | flame graph to confirm |
| CPU high only in one pod | noisy neighbour, throttling, bad instance | compare pods, check CFS throttling |
| JIT compiler threads busy | warm-up after start | expected; check if it persists |

**Deep dive.** One thread dump is a single frame; take **three, about 10 seconds apart**, and look for
the same thread in the same place. A flame graph from async-profiler (`-e cpu`) or a JFR recording
turns "this method appears" into "this method is 38% of CPU". Typical culprits in Spring services:
a catastrophic regex on user input, `String.format` or logging of large payloads in a hot path,
JSON serialisation of huge entity graphs, a retry loop with no backoff, an infinite loop on malformed
input, or `HashMap` misuse under concurrency. Health checks fail because the pod is starved: request
threads cannot get CPU to answer `/actuator/health`. In Kubernetes also check CPU limits, since
throttling makes a pod look slow at modest utilisation.

*Worked example.* 2 cores pinned, traffic flat. `top -H` shows one thread at 99%; its stack is in
`Pattern$Loop.match` from a validation method. A flame graph shows 61% of CPU in that regex. A crafted
input made it backtrack exponentially. Fix: simplify the pattern, bound input length, add a timeout.
CPU falls to 25%.

*Follow-ups.* **CPU is high but threads are mostly BLOCKED?** Then CPU is not the issue; look at lock
contention. **Is it safe to profile in production?** JFR and async-profiler are low overhead; heap
dumps pause the JVM, so use them deliberately.

---

### Q2. A Java 17 service crashes with heap exhaustion every 3-4 days; restart fixes it temporarily. What do you do?

**Short answer.** That pattern is a memory leak: objects are retained and heap-after-GC creeps up until
it hits the limit. I confirm with GC logs and heap metrics, capture heap dumps at two points, and use
Eclipse MAT to find which object graph grows and the GC-root path that holds it. Then I fix the
retention, usually an unbounded cache or collection, a `ThreadLocal`, or a listener, and verify with a
soak test.

**Technical detail.**

| Step | Tool or setting |
|---|---|
| Always-on safety net | `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps` |
| Confirm the trend | heap-after-GC (live set) over days; `-Xlog:gc*` |
| Capture on demand | `jcmd <pid> GC.heap_dump /dumps/h1.hprof` (live objects only) |
| Analyse | Eclipse MAT: leak suspects, dominator tree, path to GC roots |
| Compare | two dumps hours apart; which class count and retained size grew |
| Prove the fix | soak test with a flat heap-after-GC floor |

**Deep dive.** Distinguish **leak** from **normal growth**: a healthy heap sawtooths, and the floor
after full GC stays flat. A leak's floor rises steadily. Typical retention paths: a static
`Map`/`List` that only grows, an in-process cache with no `maximumSize`/TTL, `ThreadLocal` values
never `remove()`d in a pooled thread, listeners or callbacks never deregistered, an unbounded queue
in front of a slow consumer, sessions, and (for Metaspace) classloader leaks from repeated
redeploys or dynamic proxies. Also check non-heap: `OutOfMemoryError: Metaspace`, "unable to create
native thread" (too many threads), and direct buffers, which a heap dump will not show.

*Worked example.* Heap floor grows about 40 MB/hour. MAT leak suspects: a `ConcurrentHashMap` holding
1.4 GB. Path to GC root: `static RequestCache.INSTANCE -> map -> CustomerResponse[]`. The "performance
cache" never evicted. Fix: Caffeine with `maximumSize=50_000`, `expireAfterWrite=10m`, and cache a
small DTO. Soak test 24 h: floor flat at 600 MB, no restarts.

*Follow-ups.* **Heap dump vs thread dump?** Heap dump = what objects exist and who retains them;
thread dump = what each thread is doing now. **Can a thread pool leak?** Yes: unbounded queue growth,
threads never shut down, and `ThreadLocal` values pinned to pool threads. **What if Metaspace fills?**
Look for classloader leaks and runtime class generation; cap with `-XX:MaxMetaspaceSize` only after
finding the cause.

---

### Q3. Database connections are exhausted. What could be wrong?

**Short answer.** The pool is empty because connections are held too long or never returned. I look at
Hikari active/pending metrics and the database's own session list to see what the connections are
doing: slow queries, long transactions, a connection leak, or an external call made inside a
transaction. The fix is to shorten the hold time and fix leaks; raising the pool size usually just
moves the overload to the database.

**Technical detail.**

| Evidence | Where | Points to |
|---|---|---|
| `hikaricp.connections.active` = max, `pending` > 0 | Micrometer | pool saturation |
| `Connection is not available, request timed out after 30000ms` | app log | callers waiting for a connection |
| Sessions "idle in transaction" | `pg_stat_activity` / `SHOW PROCESSLIST` | transaction held open, often during an HTTP call |
| Long-running statements | slow-query log, `pg_stat_activity` | slow query holding a connection |
| Active stays high with no traffic | leak detection log | connection never closed |

```text
spring.datasource.hikari.leak-detection-threshold=20000   # logs the stack that borrowed it
spring.datasource.hikari.maximum-pool-size=20
spring.datasource.hikari.connection-timeout=2000
```

**Deep dive.** Little's Law: connections in use = query rate x time held. If a query goes from 20 ms to
2 s, the same traffic needs 100x connections, so the pool empties without any traffic increase. Typical
causes: a missing index or plan change; N+1 loops; `@Transactional` spanning a remote HTTP call
(connection held while waiting on a third party); `open-in-view` keeping a connection through view
rendering; manual JDBC without `try-with-resources`; and too many pods x pool size exceeding the DB
`max_connections`. Mitigation order: find and fix the slow or long holder, shorten transactions, add a
read replica or cache, and only then raise the pool, within what the DB can actually run concurrently.
A small pool (10-20 per instance) is usually right.

*Worked example.* 5 -> 20 pods and Postgres refuses connections: 20 pods x 50 = 1,000 > `max_connections`
100. Fix: pool 10 per pod (200 total) with PgBouncer in transaction mode, plus a fix for one
200 ms query that was holding connections.

---

### Q4. Kafka consumer lag keeps growing although consumers and heartbeats look healthy. What next?

**Short answer.** I look at lag per partition, not the total. One stuck partition means a poison message,
a blocked thread or a hot key; uniform lag means consumers are simply too slow; a saw-tooth means
rebalances. Then I check processing time per record and downstream latency, and fix at that layer:
batch the writes, add a retry/DLQ path, tune poll settings, or add partitions and consumers.

**Technical detail.**

```text
kafka-consumer-groups.sh --bootstrap-server <b> --describe --group <g>
# CURRENT-OFFSET stalled while LOG-END-OFFSET moves => stuck
# both moving but the gap widens                    => too slow
```

| Pattern | Likely cause | Check |
|---|---|---|
| One partition stuck | poison message retried forever, hot key | consumer error log, DLQ config, key distribution |
| All partitions growing | per-record processing slow | downstream (DB/API) latency, `poll-idle-ratio` |
| Saw-tooth | rebalances | `rebalance-rate-per-hour`, `max.poll.interval.ms` breaches |
| Lag with GC logs showing long pauses | consumer JVM pauses | GC log, Full GC |
| Lag with stable consumption | throttling by quotas | `fetch-throttle-time` |

**Deep dive.** Throughput ceiling per partition = 1 / processing time per record: 5 s per record is
0.2 msg/s per partition. Parallelism is capped by partition count, so consumers beyond partitions idle.
A poison message (cannot deserialise or always throws) blocks a partition if the listener retries
forever; use bounded retries with backoff and a dead-letter topic, and a deserialisation error handler.
Rebalances pause the whole group; reduce them with cooperative sticky assignor, static membership
(`group.instance.id`), a `max.poll.records` that fits inside `max.poll.interval.ms`, and avoiding
autoscaler flapping. Commit offsets after processing (at-least-once) and make handlers idempotent.
Alert on **time lag** and growth rate, not a raw message count. Lag can also threaten data loss if
retention expires before consumption.

*Worked example.* Lag grows on 1 of 12 partitions. Its consumer logs a `JsonParseException` loop for
offset 482,113: a poison record retried endlessly. Fix: skip to DLQ after 3 attempts with backoff;
the partition drains in minutes. Alert added on per-partition lag and DLQ rate.

---

### Q5. What is the difference between liveness and readiness, and how do you design health checks?

**Short answer.** Liveness answers "should the orchestrator restart me?" and readiness answers "should I
receive traffic now?". Liveness must be cheap and depend only on the process itself; readiness can
include dependencies and warm-up. If liveness depends on the database, a DB blip restarts every pod
at once and turns a partial outage into a full one.

**Technical detail.**

| | Liveness | Readiness |
|---|---|---|
| Question | is the process wedged? | can it serve requests now? |
| Failure action | restart the container | remove from load balancer |
| Should check | thread pool alive, no deadlock | warm-up done, critical dependencies, not shutting down |
| Should not check | DB, downstream | nothing slow or flaky |

```text
management.endpoint.health.probes.enabled=true
management.endpoint.health.group.readiness.include=readinessState,db
# /actuator/health/liveness   /actuator/health/readiness
```

**Deep dive.** Add a **startup probe** for slow starts (90 s boot) so liveness does not kill the pod
mid-start. Custom health indicators need timeouts and caching because health endpoints are polled
often and a slow remote check can cascade. On shutdown, flip readiness to false first, then drain
in-flight requests (`server.shutdown=graceful`), so rolling deploys do not drop requests.

---

### Q6. Which Actuator endpoints do you expose in production, and how do you secure them?

**Short answer.** Only what operations needs: `health`, `info`, and `prometheus` (and `metrics` if
useful). I keep `env`, `heapdump`, `threaddump` and writable `loggers` off the public surface, move
management to a separate internal port, and put it behind Spring Security or network policy.

**Technical detail.**

```text
management.endpoints.web.exposure.include=health,info,prometheus
management.server.port=9090                     # internal only
management.endpoint.health.show-details=when-authorized
```

| Endpoint | Risk | Policy |
|---|---|---|
| `env`, `configprops` | leaks secrets/config | off, or sanitised and authenticated |
| `heapdump` | full memory including secrets | off by default; enable only temporarily |
| `threaddump` | internal structure | authenticated |
| `loggers` (POST) | changing log levels | authenticated; useful for temporary DEBUG |
| `shutdown` | stops the app | never exposed |

**Deep dive.** Endpoints are collected but not exposed by default, which is why `/actuator/prometheus`
returns 404 until included. Useful production move: raise one package to DEBUG via `loggers`, reproduce,
revert. Never leave it raised.

---

### Q7. How do you avoid high-cardinality metrics, and how do you get correct percentiles?

**Short answer.** Every unique tag-value combination creates a new time series, so tags must be
bounded: route template, method, status, not user id or raw URL. For percentiles I publish histogram
buckets and compute `histogram_quantile` in Prometheus, because client-side percentiles cannot be
aggregated across instances.

**Technical detail.**

| Do | Don't |
|---|---|
| tag with `/orders/{id}`, status class, method | tag with user id, order id, raw path, exception message |
| `percentiles-histogram` + SLO buckets | rely on per-instance `p99` gauges, then average them |
| `rate()` / `increase()` on counters | read raw counters (they reset on restart) |
| `sum by (application)` across pods | trust a single pod as the truth |

```text
management.metrics.distribution.percentiles-histogram.http.server.requests=true
management.metrics.distribution.slo.http.server.requests=100ms,300ms,1s
```

**Deep dive.** Cardinality is the usual way Prometheus runs out of memory. Keep identifiers in logs and
traces, not metric labels. Averaging pod-level p99s is mathematically wrong; merged histograms are
correct. Business metrics: inject `MeterRegistry` and create `Counter`/`Timer` (for example
`orders.placed`), or `@Timed` with a `TimedAspect`.

---

### Q8. How do you trace one request across microservices and in logs?

**Short answer.** A trace id (and a correlation id for business flows) is created at the edge, propagated
in headers to every service and Kafka message, and written into every log line through MDC. With
OpenTelemetry or Micrometer Tracing I get spans per hop, and in Splunk I filter by that one id to see
the whole journey.

**Technical detail.**

| Piece | Role |
|---|---|
| W3C `traceparent` header | propagates trace id and span id over HTTP |
| MDC (`traceId`, `spanId`, `correlationId`) | puts ids in every log line |
| Kafka headers | carries the id across async hops |
| Trace backend (Jaeger/Zipkin/APM) | span waterfall, slow-span search |
| Log search (Splunk/ELK) | `traceId=...` shows every service's log |

**Deep dive.** Log business identifiers (order id) alongside the technical ids, never sensitive data
(card numbers, tokens, PII). Use sampling to control cost; tail-based sampling keeps slow and errored
traces. The answer to "where did the 1.2 s go" is the span waterfall; the answer to "why" is the log
lines with the same id.

---

### Q9. How do you handle a P1 production incident and do the RCA?

**Short answer.** Stabilise first: assess impact, roll back or mitigate, communicate on a fixed cadence,
and preserve evidence. Only then do the root-cause analysis with a timeline, using metrics, traces,
logs and dumps, and close with corrective and preventive actions so the incident does not recur.

**Technical detail.**

| Phase | Actions |
|---|---|
| Detect and triage | confirm via monitoring, severity, blast radius, who is affected |
| Mitigate | rollback, feature flag off, scale out, failover, shed load |
| Communicate | single incident channel, status updates every 15-30 min, owner named |
| Preserve evidence | thread dump, heap dump or JFR, logs, metrics screenshots before restart |
| Diagnose | timeline of changes, golden signals vs baseline, trace, then tool drill-down |
| Fix | targeted change, tested, canary release |
| RCA | five whys, timeline, root cause (not "human error"), what detection failed |
| Prevent | action items with owners and dates: alert, test, runbook, guardrail |

**Deep dive.** A good RCA separates **trigger** (the deploy), **root cause** (missing index plus no
query-plan review), and **contributing factors** (no alert on pool pending, no canary). Corrective
actions fix this instance; preventive actions fix the class (CI plan check, alert, runbook). Blameless
tone. Measure MTTD, MTTR and recurrence.

---

### Q10. What do you alert on, and how do you reduce alert noise?

**Short answer.** I alert on symptoms users feel: error rate, latency percentiles against an SLO, and
saturation that predicts an outage. Resource metrics like CPU stay on dashboards as diagnostics. To
cut noise I use SLO burn-rate alerts, sensible durations, deduplication and runbook links, and I
review alerts that fired without action.

**Technical detail.**

| Alert (page) | Alert (ticket) | Dashboard only |
|---|---|---|
| p95/p99 above SLO for 5+ min | disk filling in 3 days | CPU, heap, thread count |
| 5xx rate above threshold | cert expiring in 14 days | GC details |
| consumer time lag above target | rising slow-query count | per-pod detail |
| error-budget burn rate high | DLQ growing slowly | cache hit ratio |

**Deep dive.** A burn-rate alert (fast burn over short window plus slow burn over a long window)
catches both outages and slow degradation with few false pages. Every page should be actionable,
link a runbook, and be reviewed monthly: delete or retune anything that fires without action.

---

### Q11. "Tell me about a production issue you solved." How do you structure it?

**Short answer.** Use STAR with numbers: the situation and impact, how you investigated with evidence,
the root cause, the fix, and the prevention. Keep your own contribution explicit and quantify
before and after.

**Technical detail.**

| Part | Content | Example |
|---|---|---|
| Situation | service, impact, scale | order API p95 200 ms -> 1 s at 500 TPS after a release |
| Task | your responsibility | on-call owner for the incident |
| Action | evidence-led steps | traces showed one 780 ms SQL span; plan showed a seq scan |
| Result | numbers | rolled back in 25 min; index added; p95 190 ms |
| Prevention | what changed afterwards | query-plan review in release checklist, pool-pending alert |

**Deep dive.** Prepare two or three stories in advance, covering performance, a memory or concurrency
bug, and a messaging issue (Kafka). Be ready for "what would you do differently" (earlier alert,
canary, load test) and "what was your specific role". Do not blame individuals; focus on the system
gap you closed.

---

### Q12. What do you check after a production deployment?

**Short answer.** I compare golden signals with the pre-release baseline: latency percentiles, error
rate, throughput, saturation, plus dependency health and Kafka lag. I release by canary with a
pre-agreed rollback condition and keep a closer watch for the first hour and the first traffic peak.

**Technical detail.**

| Check | How |
|---|---|
| Health and readiness | pods ready, no restart loops, readiness gating traffic |
| Golden signals | p50/p95/p99, 5xx, TPS, CPU, heap, GC vs baseline dashboard |
| Dependencies | DB pool pending, slow queries, downstream latency, circuit breakers |
| Messaging | consumer lag, rebalances, DLQ rate |
| Business metrics | orders placed, payment success rate |
| Logs | new exception types, error rate by version tag |
| Rollback trigger | for example p95 above 300 ms or errors above 1% for 5 min |

**Deep dive.** Tag metrics and logs with the release version so old and new can be compared side by
side during a canary. Keep database migrations backward compatible (expand, migrate, contract) so
rollback of the app is safe. A smoke test and a synthetic transaction cover critical paths before
the canary widens.

---

### Q13. What tools and techniques do you use to measure application performance?

**Short answer.** I measure at four levels and always start from a baseline of p50/p95/p99 latency,
throughput, error rate and resource use. Metrics (Actuator, Micrometer, Prometheus, Grafana) tell me
*what* is slow, distributed tracing (OpenTelemetry, Jaeger, Zipkin) tells me *where*, profiling (JFR,
async-profiler, thread and heap dumps, GC logs) tells me *why*, and load testing (k6, JMeter, Gatling)
tells me *whether the fix works*. I never tune on assumption: measure, find the bottleneck, change one
thing, re-run the same workload and compare before and after.

**Technical detail.**

| Level | Tool | Answers |
|---|---|---|
| Metrics | Actuator + Micrometer -> Prometheus -> Grafana | latency percentiles, TPS, errors, JVM heap/GC/threads, pools |
| Tracing | OpenTelemetry, Jaeger, Zipkin, APM | which downstream hop owns the time |
| CPU / allocation | JFR + Mission Control, async-profiler | hot methods, allocation, lock contention |
| Stuck / slow | `jstack` thread dumps (3 dumps, 10 s apart) | BLOCKED/WAITING pile-ups, pool exhaustion |
| Memory | heap dump + Eclipse MAT | retained size, leak suspects, unbounded caches |
| GC | GC logs (`-Xlog:gc*`) | pause time, frequency, allocation rate |
| Database | slow-query log, `EXPLAIN`, pool metrics | missing index, N+1, lock waits |
| Kafka | lag, records/sec, poll and commit latency, rebalances | consumers cannot keep up |
| Logs | Splunk | correlate errors with a time window and trace id |
| Load | k6, JMeter, Gatling | capacity and the knee of the latency curve |

Baseline to write down before changing anything:

```text
TPS 1,000 | p50 100 ms | p95 250 ms | p99 500 ms | errors 0.2% | CPU 65% | heap 60% | GC pause 20 ms
```

| Test type | Purpose | Example |
|---|---|---|
| Load | expected normal / peak | 1,000 -> 2,000 TPS |
| Stress | find the breaking point | ramp until degradation |
| Spike | sudden surge | 1,000 -> 5,000 TPS |
| Soak | leaks and slow degradation | 1,500 TPS for 8 h |
| Capacity | maximum sustainable throughput | highest TPS inside the SLO |

**Deep dive.** *Triage with the four golden signals* (latency, traffic, errors, saturation). When
latency rises, ask in order: did traffic rise, did errors rise, is something saturated (CPU, heap, GC,
thread pool, DB pool), is a dependency slow (DB, Kafka lag, external API)? Then use the tool for that
branch: tracing for a slow hop, JFR for CPU, dumps for stuck threads, MAT for memory.

*Worked example.* An API takes 1 s. The trace shows controller 10 ms, service 30 ms, DB query 900 ms,
serialisation 60 ms. Profiling the Java code would be wasted effort; the fix is the query, its index or
its plan. After the change, repeat the same load test and confirm p95/p99, TPS, CPU and GC improved.

*Reading a load test.* Latency is flat until the system nears capacity and then rises sharply. For
example 500 TPS = p95 150 ms, 1,000 = 250 ms, 1,500 = 450 ms, 2,000 = 2 s: the knee is near 1,500, so
plan capacity below it with headroom.

*Pitfalls.* Averages hide tail latency (use percentiles from histograms, see Q7). Load generators on a
laptop or with unrealistic data prove little. Coordinated omission makes closed-loop tools under-report
latency; prefer open-model arrival rates (k6 `constant-arrival-rate`). Profiling overhead differs:
JFR is low-overhead and safe in production, heap dumps pause the JVM.

*Likely follow-ups.* "p95 vs average?" tail latency is what users feel. "How do you prove the fix?"
same workload, before/after comparison. "Kafka consumer slow?" lag = log-end offset - committed
offset; compare produce rate with consume rate, then check processing time per record.

**60-second answer.** "I baseline p50/p95/p99, throughput, errors and utilisation first. Actuator and
Micrometer feed Prometheus and Grafana, and OpenTelemetry traces show which hop is slow. For JVM
issues I use JFR, async-profiler, thread and heap dumps and GC logs. I check DB and Kafka metrics,
especially consumer lag, then validate with k6, JMeter or Gatling. After a targeted fix I rerun the
same load and compare before and after. Metrics say what, tracing where, profiling why, load testing
whether it worked."

---

## Hands-on drills

1. Run a busy loop in a sample app; find it with `top -H`, hex id and `jstack`.
2. Add an unbounded static map; capture two heap dumps and find it in MAT.
3. Set Hikari `maximumPoolSize=3`, add a `sleep` in a transaction, and watch `pending` rise.
4. Produce a malformed record; observe the stuck partition, then add a DLQ.
5. Expose only `health,info,prometheus` on a separate port and confirm `/actuator/env` is gone.
6. Write one STAR story with before/after numbers, out loud, in under two minutes.

## Sources used to shape the question list

- Infosys Java production-support job postings (incident ownership, RCA, thread/heap dumps, SQL plans, alert tuning, Splunk/AppDynamics).
- EPAM candidate interview reports (managerial round on production issues; Spring Boot and microservices rounds).
- Public senior-Java scenario banks (memory leak, high CPU, slow API, exhausted connections) and
  Kafka consumer-lag troubleshooting guides.
