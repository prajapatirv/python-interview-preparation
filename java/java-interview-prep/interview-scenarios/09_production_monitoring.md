---
id: production-monitoring
title: Production support, monitoring and incident handling
stack: java
skill: production
---
Interview feedback focus: **production issues, monitoring and incident handling** — the questions
MNC rounds (Infosys production support, EPAM managerial, product-company senior rounds) ask. Each entry
mirrors `deep_dive/25_production_monitoring_qa.md`: short answer first, then the detail.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] A service is at near 100% CPU with normal traffic and pods fail health checks. How do you find the cause?
tags: high-cpu, thread-dump, top, jstack, flame-graph, troubleshooting

**The live scenario**
The order service is pinned at 100% CPU on every pod. Traffic is the same as yesterday, and Kubernetes is restarting pods because the health endpoint times out.

**What the interviewer is really checking**
That you go from the process to the thread to the line of code with evidence, instead of restarting or adding pods.

**How I answer it**
1. **Stabilise without losing evidence:** keep one affected pod out of rotation if I can, or capture dumps before any restart.
2. **Find the hot thread:** `top -H -p <pid>` gives per-thread CPU; convert the busiest thread id to hex.
3. **Match it in a thread dump:** take three `jstack` dumps about ten seconds apart and look for that `nid=0x…` in the same place each time.
4. **Confirm with a profile:** a JFR recording or async-profiler flame graph turns "this method appears" into "this method is 40% of CPU".
5. **Read the cause:** a hot loop, regex backtracking, serialisation of huge payloads, logging in a hot path, or GC threads.
6. **Fix and verify:** change the code, then re-run the load and compare CPU and p95.

**Trade-offs and what can go wrong**
Heap dumps pause the JVM, so I prefer JFR or async-profiler in production. One dump is one frame; I always take several. CPU limits can cause throttling that looks like slowness at modest usage.

**How I'd monitor it**
Alert on sustained CPU above a threshold together with p95 latency, track CFS throttling in containers, and keep a JFR continuous recording ready.

**Follow-ups to expect**
- *Threads are mostly BLOCKED, not RUNNABLE* -> then it is lock contention, not computation; look at the monitor owner.
- *Only one pod is hot* -> compare nodes, noisy neighbours, bad instance, or CPU throttling.

**60-second answer**
Normal traffic with high CPU means each request is doing more work or something is spinning. I use `top -H` to find the hottest thread, convert its id to hex and match it in a few thread dumps, then confirm with a JFR or async-profiler flame graph. The cause is usually a hot loop, regex backtracking, serialisation, logging or GC, and I fix it and re-test under load.

### Q2 [mid] A Java 17 service crashes with heap exhaustion every three to four days. Restarting fixes it. What do you do?
tags: memory-leak, heap-dump, mat, gc-logs, soak-test, troubleshooting

**The live scenario**
The payments service runs fine after a restart, then its memory climbs for days and it dies with `OutOfMemoryError: Java heap space`.

**What the interviewer is really checking**
That you can tell a leak from normal growth and know the heap-dump workflow and the usual retention paths.

**How I answer it**
1. **Confirm it is retention:** heap *after* full GC trends upward over days; a healthy heap sawtooths with a flat floor.
2. **Make the failure observable:** `-XX:+HeapDumpOnOutOfMemoryError` and GC logging so the next crash leaves a dump.
3. **Capture two heap dumps** hours apart with `jcmd <pid> GC.heap_dump`.
4. **Analyse in Eclipse MAT:** leak suspects, dominator tree, then "path to GC roots" for the biggest retainer.
5. **Typical culprits:**
   - an unbounded static map or cache;
   - `ThreadLocal` values never removed in pooled threads;
   - listeners never deregistered;
   - an unbounded queue in front of a slow consumer.
6. **Fix and prove:** bound it (Caffeine max size and TTL), then run a soak test and confirm a flat floor.

**Trade-offs and what can go wrong**
Heap dumps are large and pause the JVM. Heap is not the only memory: Metaspace, thread stacks and direct buffers need native-memory checks.

**How I'd monitor it**
Alert on heap-after-GC slope rather than raw usage, and keep a soak test in the release checklist.

**Follow-ups to expect**
- *Heap dump vs thread dump?* -> heap dump is what objects exist and who holds them; thread dump is what each thread is doing now.
- *What if Metaspace fills?* -> look for classloader leaks or runtime class generation before raising the cap.

**60-second answer**
That pattern is a leak: heap-after-GC rises until it hits the limit. I confirm with GC logs, take two heap dumps, and use MAT to find the growing object graph and its GC-root path. It is usually an unbounded cache or collection, a ThreadLocal or a listener. I bound or remove it and verify with a soak test showing a flat floor.

### Q3 [mid] Database connections are exhausted. What could be wrong?
tags: connection-pool, hikari, database, transactions, pg-stat-activity

**The live scenario**
Users get 500s with "Connection is not available, request timed out after 30000 ms". Traffic is normal.

**What the interviewer is really checking**
That you reason from "connections in use = rate x hold time" and do not just raise the pool size.

**How I answer it**
1. **Look at the pool:** Hikari `active` at max and `pending` above zero confirms saturation.
2. **Look at the database:** `pg_stat_activity` or `SHOW PROCESSLIST` shows what those connections are doing.
3. **Classify:**
   - slow queries holding connections;
   - "idle in transaction" from a transaction held open during an HTTP call;
   - a leak (connection never closed);
   - too many pods x pool size over `max_connections`.
4. **Fix the hold time:** index or rewrite the query, shorten transactions, move remote calls out of them, fix leaks (`leak-detection-threshold` shows the borrowing stack).
5. **Only then size the pool,** within what the database can run concurrently; small pools are usually right.

**Trade-offs and what can go wrong**
A bigger pool moves the queue into the database and can take it down. PgBouncer helps connection count, not slow queries.

**How I'd monitor it**
Alert on Hikari pending connections and acquire time, and on slow queries and idle-in-transaction sessions.

**60-second answer**
The pool is empty because connections are held too long or never returned. I check Hikari active and pending, then the database session list to see what they are doing: slow queries, transactions open across an external call, or leaks. I fix the hold time and leaks first; raising the pool usually just moves the overload to the database.

### Q4 [senior] Kafka consumer lag keeps growing although the consumers and heartbeats look healthy. What next?
tags: kafka, consumer-lag, poison-message, rebalance, dlq, troubleshooting

**The live scenario**
The lag dashboard for the orders topic climbs steadily; producers are fine and the consumer pods are up.

**What the interviewer is really checking**
That you read lag per partition and recognise the three distinct causes: stuck, slow, or rebalancing.

**How I answer it**
1. **Per partition, not the total:** `kafka-consumer-groups.sh --describe --group <g>`. Offset stalled while log-end moves means stuck; both moving with a widening gap means too slow.
2. **One partition stuck:** a poison message retried forever, a blocked thread, or a hot key.
3. **All partitions growing:** processing time per record is the limit; check downstream (DB, API) latency and `poll-idle-ratio`.
4. **Saw-tooth:** rebalances; check `max.poll.interval.ms` breaches, deploys, autoscaler flapping.
5. **Fix at that layer:** bounded retries plus a dead-letter topic; batch the downstream writes; cooperative sticky assignor and static membership; add partitions and consumers only if throughput really needs it.

**Trade-offs and what can go wrong**
Parallelism is capped by partition count and adding partitions changes key routing. Skipping a poison message needs a DLQ so it is not lost.

**How I'd monitor it**
Alert on time lag and its growth rate per partition, rebalance rate per hour, and DLQ rate.

**60-second answer**
I look at lag per partition. One stuck partition means a poison message, a blocked thread or a hot key; uniform growth means per-record processing is too slow; a saw-tooth means rebalances. I fix that layer: DLQ with bounded retries, batched writes, cooperative rebalancing, or more partitions and consumers, and I alert on time lag and rebalance rate.

### Q5 [mid] What is the difference between liveness and readiness, and how do you design health checks?
tags: actuator, kubernetes, liveness, readiness, health-checks

**The live scenario**
A brief database blip makes every pod restart at once and a small hiccup becomes a full outage.

**What the interviewer is really checking**
That you know liveness means "restart me" and readiness means "send me traffic", and what each should depend on.

**How I answer it**
1. **Liveness:** cheap, process-only; never depend on the database or downstream services.
2. **Readiness:** warm-up finished, critical dependencies reachable, not shutting down.
3. **Startup probe** for slow boots so liveness does not kill a pod mid-start.
4. **Graceful shutdown:** flip readiness to false, drain in-flight requests, then stop.
5. **Custom indicators** have timeouts and caching because health endpoints are polled constantly.

**Trade-offs and what can go wrong**
Too strict readiness removes every pod at once during a dependency blip; too loose sends traffic to cold pods.

**How I'd monitor it**
Track restart counts, readiness flaps and time-to-ready per deployment.

**60-second answer**
Liveness decides whether to restart the container and must be cheap and independent of the database. Readiness decides whether to route traffic and can include warm-up and critical dependencies. I add a startup probe for slow starts and drain gracefully on shutdown, so a dependency blip never restarts every pod.

### Q6 [mid] Which Actuator endpoints do you expose in production, and how do you secure them?
tags: actuator, security, prometheus, endpoints, management-port

**The live scenario**
A security review finds `/actuator/env` and `/actuator/heapdump` reachable from the internet.

**What the interviewer is really checking**
That you treat Actuator as an attack surface and expose the minimum.

**How I answer it**
1. **Expose only what is needed:** `health`, `info` and `prometheus` (and `metrics` if useful).
2. **Keep off the public surface:** `env`, `configprops`, `heapdump`, `threaddump`, writable `loggers`, and never `shutdown`.
3. **Separate management port** reachable only from the internal network, plus Spring Security or a network policy.
4. **`show-details=when-authorized`** for health.
5. **Use `loggers` deliberately:** raise one package to DEBUG, reproduce, revert.

**Trade-offs and what can go wrong**
Endpoints are collected but not exposed by default, which is why `/actuator/prometheus` is a 404 until included. A heap dump can contain secrets and personal data.

**How I'd monitor it**
Audit exposed endpoints in CI and alert on unexpected access to management paths.

**60-second answer**
I expose health, info and prometheus only, on a separate internal management port behind Spring Security. Env, heapdump, threaddump and writable loggers stay off the public surface and shutdown is never exposed. I use the loggers endpoint temporarily for targeted DEBUG and revert afterwards.

### Q7 [senior] How do you avoid high-cardinality metrics, and how do you get correct percentiles across instances?
tags: micrometer, prometheus, cardinality, histograms, percentiles

**The live scenario**
Prometheus runs out of memory after someone tagged a latency metric with the user id.

**What the interviewer is really checking**
That you understand series cardinality and why client-side percentiles cannot be averaged.

**How I answer it**
1. **Bounded tags only:** route template, method, status class — never user id, order id, raw URL or exception message.
2. **Identifiers go in logs and traces,** not metric labels.
3. **Publish histogram buckets** with SLO boundaries and compute `histogram_quantile` in PromQL.
4. **Do not average per-pod p99s;** merged histograms are correct, averages are not.
5. **Counters:** use `rate()` or `increase()` because they reset on restart.

**Trade-offs and what can go wrong**
Histograms cost more series per metric; choose buckets around the SLO instead of dozens of defaults.

**How I'd monitor it**
Watch Prometheus series count and scrape duration, and review new metrics for unbounded labels.

**60-second answer**
Each unique tag combination is a new time series, so I only tag with bounded values like route template and status, and keep ids in logs. For percentiles I publish histogram buckets and use `histogram_quantile`, because per-instance percentiles cannot be aggregated.

### Q8 [mid] How do you trace one request across microservices and in the logs?
tags: tracing, correlation-id, mdc, opentelemetry, splunk

**The live scenario**
A customer says "my order failed at 14:03" and the request touched five services and a Kafka topic.

**What the interviewer is really checking**
That you can follow one request end to end with ids, not by guessing timestamps.

**How I answer it**
1. **Create a trace id at the edge** and propagate it with the W3C `traceparent` header.
2. **Put ids in every log line** through MDC (`traceId`, `spanId`, business `orderId`).
3. **Carry it across async hops** in Kafka headers.
4. **Use the trace backend** (Jaeger, Zipkin, APM) for the span waterfall: where the time went.
5. **Use Splunk or ELK** filtered by that id for why: exceptions and timeouts in each service.
6. **Never log sensitive data** — tokens, card numbers, personal data.

**Trade-offs and what can go wrong**
Full tracing is expensive; sample, with tail-based sampling to keep slow and errored traces.

**How I'd monitor it**
Check trace coverage across services and the share of log lines carrying a trace id.

**60-second answer**
A trace id is created at the edge, propagated in headers and Kafka message headers, and written into every log line through MDC. The trace backend shows where the time went, and a search in Splunk by that id shows the logs of every service for the why.

### Q9 [senior] How do you handle a P1 production incident and do the root-cause analysis?
tags: incident-management, rca, p1, on-call, postmortem

**The live scenario**
Checkout is failing for 30% of users and you are the on-call owner.

**What the interviewer is really checking**
Calm, structured ownership: mitigate first, communicate, then analyse and prevent recurrence.

**How I answer it**
1. **Triage:** confirm via monitoring, severity, blast radius.
2. **Mitigate first:** roll back the last change, flip a feature flag, scale out, fail over or shed load.
3. **Communicate:** one incident channel, a named owner, updates every 15–30 minutes.
4. **Preserve evidence** before restarting: dumps, logs, dashboards.
5. **Diagnose** with a change timeline and golden signals against baseline, then trace and tools.
6. **RCA:** trigger vs root cause vs contributing factors, blameless, with a timeline.
7. **Corrective and preventive actions** with owners and dates: alert, test, runbook, guardrail.

**Trade-offs and what can go wrong**
Rolling back loses the new feature but buys time. "Human error" is not a root cause; the missing guardrail is.

**How I'd monitor it**
Track MTTD, MTTR, recurrence and action-item completion.

**60-second answer**
I stabilise first — roll back or mitigate — while communicating on a fixed cadence and preserving evidence. Then I do a blameless RCA with a timeline, separating trigger, root cause and contributing factors, and close with corrective and preventive actions that have owners, such as an alert, a test or a runbook.

### Q10 [senior] What do you alert on, and how do you reduce alert noise?
tags: alerting, slo, burn-rate, monitoring, on-call

**The live scenario**
The on-call engineer gets 60 pages a week and most need no action.

**What the interviewer is really checking**
That you alert on user-visible symptoms and SLOs, and treat noise as a defect.

**How I answer it**
1. **Page on symptoms:** error rate, latency percentiles against an SLO, saturation that predicts an outage.
2. **Ticket, don't page,** for slow-burn issues: disk filling in days, certificates expiring.
3. **Resource metrics** like CPU and heap are dashboards and diagnostics.
4. **Burn-rate alerts** with a fast and a slow window catch both outages and slow degradation.
5. **Every page is actionable** with a runbook link; review monthly and delete or retune anything that fired without action.
6. **Deduplicate and route** by severity and ownership.

**Trade-offs and what can go wrong**
Tight thresholds create noise; loose ones miss incidents. Alerting on causes (CPU) instead of symptoms misses real outages.

**How I'd monitor it**
Track pages per week, percentage actionable, and time to acknowledge.

**60-second answer**
I page on symptoms users feel: errors, latency against the SLO and predictive saturation, and keep CPU and heap as diagnostics. I use burn-rate alerts, link a runbook to every page, and review monthly to delete anything that fires without action.

### Q11 [mid] "Tell me about a production issue you solved." How do you structure the answer?
tags: behavioural, star, incident, storytelling, managerial-round

**The live scenario**
In the managerial round the interviewer says: "Walk me through a production issue you handled."

**What the interviewer is really checking**
Ownership, an evidence-led method, a quantified result, and what you changed afterwards.

**How I answer it**
1. **Situation:** the service, the scale and the impact, with numbers.
2. **Task:** your specific responsibility, such as on-call owner.
3. **Action:** the evidence you gathered — traces, plan, dumps — and why you chose each step.
4. **Result:** before and after numbers and the time to recover.
5. **Prevention:** the alert, test or checklist you added.
6. **Prepare three stories:** performance, a memory or concurrency bug, and a messaging issue.

**Trade-offs and what can go wrong**
Vague "we fixed it" answers, blaming people, or no numbers. Be ready for "what would you do differently".

**How I'd monitor it**
Rehearse aloud and time each story to under two minutes.

**60-second answer**
I use STAR with numbers. For example: order API p95 rose from 200 ms to 1 second after a release; I was on-call owner; a trace showed one 780 ms SQL span and the plan showed a sequential scan; I rolled back in 25 minutes, added the index, and p95 returned to 190 ms; afterwards I added query-plan review to the release checklist and an alert on pool pending.

### Q12 [mid] What do you check after a production deployment?
tags: deployment, canary, rollback, post-release, golden-signals

**The live scenario**
A release just went out at 09:10 and you are asked "is it healthy?".

**What the interviewer is really checking**
That you verify with data against a baseline, and that rollback conditions were agreed beforehand.

**How I answer it**
1. **Pods and probes:** ready, no restart loops.
2. **Golden signals against the pre-release baseline:** p50/p95/p99, errors, throughput, CPU, heap, GC.
3. **Dependencies:** DB pool pending, slow queries, downstream latency, circuit breakers.
4. **Messaging:** consumer lag, rebalances, DLQ rate.
5. **Business metrics:** orders placed, payment success rate.
6. **Logs by version tag:** new exception types.
7. **Rollback trigger** agreed in advance, for example p95 above 300 ms or errors above 1% for five minutes.

**Trade-offs and what can go wrong**
Backward-incompatible schema changes make rollback unsafe; use expand-migrate-contract.

**How I'd monitor it**
Tag metrics and logs with the release version and compare canary vs stable side by side.

**60-second answer**
I compare golden signals with the baseline: latency percentiles, errors, throughput and saturation, plus dependency health and Kafka lag, tagged by release version. I release by canary with a pre-agreed rollback condition and watch closely for the first hour and the first traffic peak.
