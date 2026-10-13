# Production troubleshooting, incident response and RCA

> **Runnable:** [`01_incident_triage_runbook.java`](../examples/18_production_troubleshooting/01_incident_triage_runbook.java)
> **Crib sheet:** [`topics/16-production-troubleshooting-rca.md`](../topics/16-production-troubleshooting-rca.md) · **Guide:** Q87, Q90–Q96
> **Symptom drills:** [23 Production scenarios](23_production_scenarios.md) (20 one-symptom questions with runnable proofs)

## What interviewers are actually probing

This is where "hands-on" is verified. They give a symptom and watch your **method**: do you stabilise first, scope the blast radius, form and test hypotheses with evidence
(metrics → traces → logs), and communicate. Naming the tools (`jstack`, `jcmd`, Splunk, Grafana, `kubectl`) matters less than the order of your questions.

## Must-know points

- **Mitigate before you investigate** (rollback, flag off, scale, shed load); customers first, curiosity second.
- **Scope** the problem: which endpoint/version/pod/region/tenant, since when, what changed.
- Use the **golden signals** (latency, traffic, errors, saturation) and compare with a baseline.
- Resource signals point to a class of cause: pool saturated → slow query/leak; GC high → memory; CPU high → hot loop; threads blocked → downstream.
- Consumer lag is a symptom; duplicates are normal under at-least-once; "the DLT is growing" is a symptom of a persistent bug.
- An RCA documents **timeline, root cause, contributing factors, detection gaps, and corrective + preventive actions** — blameless.

## Interview questions and full answers

### Q1. A Spring Boot API is slow. How do you troubleshoot it?

1. **Quantify**: p50/p95/p99, since when, which endpoints, error rate, traffic change; is it all requests or a segment (tenant, payload size, region)?
2. **Recent change?** deploy, config, dependency, data volume, certificate, traffic pattern.
3. **Where is time spent?** a trace of a slow request (span breakdown); otherwise per-layer metrics: Tomcat busy threads, **Hikari pending/acquire time**, outbound HTTP latency, Kafka send latency, GC pauses.
4. **Hypothesis by signal** (example 18 rule table): pool saturated with low CPU → slow query/long transaction/leak; CPU high → thread dumps/flame graph; GC high → heap; threads blocked in a client call → downstream timeouts; latency only after deploy → cold JIT/cache or a new N+1.
5. **Prove it**: slow-query log/`EXPLAIN`, `pg_stat_activity`, 3 thread dumps, heap histogram.
6. **Fix and verify** with metrics, then add the missing alert/test.

### Q2. Kafka consumer lag keeps growing. What do you do?

Compare production vs consumption rate and look at lag **per partition**. One partition behind → key skew/hot partition or one stuck poison record; all partitions → consumers too slow or too few; sawtooth with spikes → rebalances (check `max.poll.interval.ms`, GC, pod restarts).
Check handler latency and downstream health (DB/partner), error/retry/DLT counts, and consumer count vs partitions. Fix the cause (batching, async I/O, query, key distribution), scale consumers up to the partition count, and only add partitions after thinking about key remapping.
If lag is old data you can't process in time, decide business-wise: catch-up in parallel with a separate group, skip/reset (`--reset-offsets`) with sign-off, or compact.

### Q3. An event was processed twice. How do you prevent duplicate business effects?

Assume at-least-once. Make the effect idempotent: unique constraint on a business or event id (UPSERT/`INSERT … ON CONFLICT DO NOTHING`), a processed-events table updated in the **same transaction** as the effect, or naturally idempotent state transitions (`status = PAID` only from `PENDING`). Use idempotency keys on outbound calls to partners.
Then find *why* it was redelivered (rebalance before commit, crash, retry, producer retry without idempotence) and fix that too, but never rely on its absence.

### Q4. A downstream service is unavailable. How should your service behave?

Fail fast and visibly: timeout, circuit breaker open, **fallback** appropriate to the business (cached/default data, queue the work, degrade a feature) or a clear 503 with `Retry-After`; never block all threads waiting. Protect the dependency from retry storms (backoff + jitter, budgets).
Make the degraded mode observable (metric/log) and test it with failure injection. Decide per dependency: critical (fail closed — payment auth) vs non-critical (fail open — recommendations).

### Q5. High CPU on a Java service — walk through your steps.

`top -H -p <pid>` → hottest thread ids → convert to hex → match `nid` in `jcmd <pid> Thread.print` (take 3 dumps). If GC threads dominate it's a memory problem. Else find the frame: regex backtracking, JSON/XML (de)serialisation of big payloads, tight retry loops, logging at DEBUG, cache stampede, hash-collision DoS. Confirm with async-profiler/JFR flame graph; change; compare CPU before/after at equal load.

### Q6. Memory keeps growing until OOM / OOMKilled. What do you do?

Differentiate Java **heap OOM** (`OutOfMemoryError`, heap dump) from **container OOMKill** (exit 137, no Java error): the latter means heap + metaspace + thread stacks + direct buffers exceeded the cgroup limit → lower `MaxRAMPercentage`, cap threads/direct memory, check native memory with NMT.
Heap leak: GC log trend, histogram diff over time, dump → MAT dominator tree → path to GC roots → typical culprits (unbounded cache/map, listener, `ThreadLocal`, unclosed client, large `Page` loads).

### Q7. After a deploy, error rate increased. What now?

Roll back or disable the flag **first** if the correlation is clear (SLO burn), preserve evidence (logs, a heap/thread dump from a bad pod), then diff: version-tagged error signatures in Splunk (`stats count by version`), config/dependency diffs, schema changes, feature flags, traffic shape.
If errors exist in the old version too, it's the environment/dependency, not the deploy (example 14/01 section 8). Add a canary gate so the next one is caught at 5% traffic.

### Q8. Database connection pool exhausted — causes and fixes?

Causes: slow queries/long transactions holding connections, a leak (connection not returned: missing `close`, a transaction around a remote call), pool too small for concurrency or too **large** for the DB, `REQUIRES_NEW` nesting needing two connections, burst traffic.
Evidence: `hikaricp.connections.pending` > 0 with `active == max`, thread dumps showing threads in `HikariPool.getConnection`. Fix: shorten transactions (never hold one across HTTP/Kafka calls), tune the query/index, `leakDetectionThreshold`, right-size the pool from the DB's capacity, add timeouts, back-pressure upstream.

### Q9. How do you troubleshoot a Kafka rebalance storm?

Look at consumer logs for `Revoking`/`Attempt to heartbeat failed`/`max.poll.interval.ms` messages and the rebalance rate metric. Common causes: processing in the poll thread exceeding `max.poll.interval.ms`, GC pauses longer than the session timeout, pods crash-looping or autoscaler thrash, a rolling deploy restarting consumers faster than they stabilise.
Fix: reduce `max.poll.records`, move slow work off the poll thread safely, cooperative-sticky + static membership, slower rolling update (`maxUnavailable: 1`, readiness gating), fix the crash.

### Q10. How do you write an RCA / how do you explain a difficult incident in an interview?

Structure (STAR + engineering): **Situation/impact** (who was affected, how long, how many) → **Detection** (how found, how fast, what was missed) → **Mitigation** (what stopped the bleeding) → **Root cause** (the mechanism, not "human error") → **Contributing factors** (missing alert, no timeout, no canary) → **Corrective/preventive actions** with owners → **What I personally did and learned**.
Be specific with numbers (error rate, minutes, lag) and honest about what you'd do differently.

### Q11. What is a good runbook / on-call practice?

A runbook per alert: *what it means, how to verify, dashboards, first three diagnostic commands, mitigations, escalation, known causes*. Alerts must be actionable and tied to SLOs; on-call is supported by a blameless post-incident review, tracked action items, game days, and automation of repeated manual steps.

### Q12. What Kubernetes-level checks do you do first?

`kubectl get pods` (restarts, `CrashLoopBackOff`, `OOMKilled`), `kubectl describe pod` (events, probe failures, last state reason), `kubectl logs --previous`, resource requests/limits vs usage (CPU throttling), HPA status, node pressure, recent rollout (`kubectl rollout history/undo`), service endpoints readiness, and network policies/DNS if a call starts failing.

## A worked example

Run [`01_incident_triage_runbook.java`](../examples/18_production_troubleshooting/01_incident_triage_runbook.java). It encodes five incidents as signal snapshots and prints the ranked hypotheses
with the next action. Add your own rule (disk full, expired certificate, DNS) and a scenario for it; deciding which signal distinguishes the new cause from the others *is* the interview skill.

## Hands-on drills

1. Cause a connection-pool exhaustion in a local app (sleep inside a transaction) and diagnose it from a thread dump only.
2. Induce a consumer rebalance storm (long `Thread.sleep` in the handler) and read the logs to name the config at fault.
3. Practise narrating a past incident in the 7-part structure above in under 3 minutes.
4. Write a one-page runbook for "Kafka consumer lag > threshold for 10 minutes".
5. Reproduce a heap leak with a static map and find it in MAT.

## The 60-second spoken answer

"I mitigate first, then scope with metrics: what changed, which endpoints or versions, and the golden signals against a baseline. Resource signals tell me the class of
cause: a saturated DB pool with low CPU means slow queries or long transactions, high GC means memory, blocked threads mean a slow dependency.
I confirm with traces, thread dumps or a heap dump, fix, and verify on the metrics. Afterwards I write a blameless RCA with the timeline, root cause,
the detection gap and preventive actions such as a canary gate or a missing timeout."
