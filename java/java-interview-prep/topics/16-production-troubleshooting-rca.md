---
id: 16-troubleshooting-rca
title: Production Troubleshooting & Root Cause Analysis (RCA)
focus: Incident method, JVM/DB/Kafka/K8s failure patterns, writing RCAs (rated 8/10 - tell real stories)
deep_dive: 18
examples: 18_production_troubleshooting
---
Use the **STAR + metrics** form for stories: Situation, Task, Action (what you checked, in order), Result (time to detect/mitigate/resolve, what you prevented next time).

### Q1 [basic] What is your general approach when production is down?
1. Confirm impact and scope (who, since when, which region/feature). 2. Declare the incident and assign roles. 3. **Mitigate first** (rollback, scale, feature flag off, failover) - stop the bleeding before the root cause hunt. 4. Gather evidence (dashboards, logs, traces, recent changes). 5. Communicate regularly. 6. After recovery: RCA, action items, follow-up.

### Q2 [basic] What is an RCA and what does a good one contain?
A blameless written analysis: summary and impact, timeline (UTC), detection (how we found out and how long it took), root cause and contributing factors, what went well/badly, mitigation, **corrective actions with owners and dates** (prevent, detect faster, recover faster). Use "5 Whys" but stop at systemic causes, not "human error".

### Q3 [intermediate] What is the difference between an incident, a problem and a change?
Incident = service disruption (restore ASAP). Problem = the underlying cause of one or more incidents (fix permanently). Change = any modification; most outages are triggered by a recent change - always ask "what changed?" first (deploy, config, data volume, certificate, dependency).

### Q4 [intermediate] Service is slow - what is your checklist?
Trace which hop is slow (APM/trace) -> check saturation: CPU, memory/GC, thread pools, DB/HTTP connection pools, queue depth -> check dependencies (DB slow queries/locks, downstream latency) -> check traffic (spike, bot, retry storm) -> check recent deploys -> reproduce with a profile (JFR/flame graph). Mitigate with scale-out, cache, shed load, or rollback.

### Q5 [intermediate] OutOfMemoryError - how do you handle each type?
- `Java heap space`: heap dump -> MAT -> find the retainer (cache/list/session); fix leak or size.
- `Metaspace`: classloader leak / dynamic proxies / many redeploys.
- `unable to create native thread`: too many threads or low OS/container limit; reduce pools, check `ulimit`, use virtual threads wisely.
- `Direct buffer memory`: Netty/NIO buffers not released.
- Container OOMKilled (exit 137): non-heap memory plus heap exceed the limit.
Enable `-XX:+HeapDumpOnOutOfMemoryError` and `ExitOnOutOfMemoryError`.

### Q6 [intermediate] Thread dump says all threads are WAITING/BLOCKED. What now?
Take several dumps and compare. Group by stack: many threads waiting on the same lock = contention (find the owner thread); all waiting on a socket read = slow downstream without a timeout; all waiting for a connection pool = pool exhausted by slow queries or leaked connections (missing close/long transactions). Add timeouts and fix the slow resource.

### Q7 [intermediate] Connection pool exhausted (HikariCP "Connection is not available").
Check `hikaricp.connections.active/pending`, long-running transactions or a connection held during a remote call, slow queries, leaked connections (`leakDetectionThreshold`), pool smaller than concurrency, DB max connections reached across pods. Fix the cause (shorten transactions, add timeouts) before enlarging the pool.

### Q8 [intermediate] Kafka consumer lag increases after a deploy.
Look for rebalance loops (`max.poll.interval.ms` exceeded), a new slow code path, a poison message retrying, fewer consumers than before (crash loop, readiness), DB slowness in the sink, or partition skew. Fix and, if needed, scale consumers (up to partitions) and replay safely.

### Q9 [intermediate] Intermittent 502/503/504 behind a load balancer.
Mismatched idle timeouts (LB timeout shorter/longer than the app's keep-alive), pods terminating without graceful drain, failing readiness, upstream timeouts, connection resets from NAT/firewall idle expiry, or overload. Align timeouts (client < LB < server), add preStop sleep, retries on idempotent calls.

### Q10 [intermediate] Database CPU 100% - what do you do?
Find top SQL (AWR/`v$sql`/`pg_stat_statements`), check recent plan changes, missing index, a runaway report, lock waits, connection storm. Mitigate: kill/limit the offending session, add index online, scale reads to a replica, enable caching, throttle the caller. Then fix the query and add a slow-query alert.

### Q11 [advanced] Deadlock between two transactions in the database.
The DB picks a victim (`ORA-00060` / `deadlock detected`). Read the deadlock trace to get both statements, then fix ordering (always lock tables/rows in the same order), shorten transactions, index foreign keys, and retry the victim transaction safely.

### Q12 [advanced] Memory keeps growing slowly for days then the pod restarts.
Classic leak: compare heap dumps taken hours apart (histogram diff), check static maps/caches without eviction, unclosed streams, listeners, `ThreadLocal`, large metrics label sets (cardinality), Hibernate session caches in long loops, Netty direct memory. Add a size-bounded cache with metrics and an alert on heap-after-GC trend.

### Q13 [advanced] Duplicate records/events in production.
Root causes: at-least-once delivery without idempotent writes, retries on non-idempotent calls, rebalance reprocessing, double-submit from UI, dual writes. Fix with idempotency keys/unique constraints, outbox pattern, and a one-time cleanup script with a dry-run and backups.

### Q14 [advanced] Data inconsistency between two services.
Find the first divergence in the event/timeline, check lost events (consumer offset commit before processing, DLT ignored), out-of-order events (use version/sequence), failed compensations. Add reconciliation jobs and alerts for drift; repair with replay from the log.

### Q15 [advanced] An expired certificate / secret rotation caused an outage - how do you prevent it?
Monitor certificate expiry (alert at 30/14/7 days), automate renewal (cert-manager/ACM), support dual-valid keys during rotation, test rotation in staging, store secrets centrally, and make apps reload credentials without restart. (Relates to the API key rotation work.)

### Q16 [advanced] How do you debug something that only fails in production?
Add targeted structured logging and trace attributes behind a dynamic log level (Actuator loggers), capture the failing payload safely (masked), compare config/env/data volume with staging, use feature flags/canary to test the fix, replay traffic (shadowing), and write a regression test as soon as you reproduce.

### Q17 [intermediate] How do you reduce Mean Time To Detect and Mean Time To Recover?
Detect: SLO-based alerts, synthetic checks, good dashboards, deploy markers. Recover: one-click rollback, feature flags, runbooks, tested failover, on-call rota with clear escalation, game days/chaos drills, immutable infra.

### Q18 [design] Design a blameless post-incident process for a team of 20.
Severity definitions, incident commander + comms roles, timeline document started during the incident, a post-incident review within 3-5 working days, RCA template, action items tracked in the backlog with owners and due dates, monthly review of repeat causes, sharing learnings in a searchable archive.

### Q19 [design] Design a runbook for "orders API p95 latency > 2 s".
Impact check -> dashboard links -> decision tree (recent deploy? rollback; DB slow? top SQL, kill/limit; downstream slow? circuit breaker/fallback; CPU/GC? scale/heap analysis; traffic spike? rate limit/scale) -> commands (kubectl, jcmd) -> escalation contacts -> verification steps and when to close.

### Q20 [intermediate] Tell me about a production issue you solved (template).
Pick one real story: **Situation** (system, impact, scale) -> **Detection** (alert/customer) -> **Investigation** (3-4 concrete steps and tools) -> **Root cause** (precise) -> **Fix and prevention** (code + alert + test + process) -> **Result** (numbers: downtime minutes, errors avoided). Fill with an actual case from Cvent/CBOS/Sambasafety work.

### Q21 [intermediate] What is a good logging practice during incidents?
Correlation ids in every line, one log per event at the right level, include identifiers (orderId, partition/offset), avoid logging inside tight loops, don't swallow exceptions (log with cause once), and keep a switch to raise log level temporarily without redeploying.

### Q22 [advanced] Explain graceful degradation versus failing fast.
Degrade: serve cached/partial data or disable non-critical features (recommendations) so the core path (checkout) keeps working. Fail fast: when a dependency is down and no useful fallback exists, return a quick clear error instead of holding resources. Decide per feature and document it.

### Q23 [design] Design a game-day / chaos exercise to prove a service survives a dependency outage.
Pick a hypothesis ('orders still accepted when the payment provider is down for 10 minutes'), define the steady-state metrics, inject the fault in a staging or limited-blast-radius prod slice (latency, errors, pod kill, DNS), and watch circuit breakers, timeouts, queue depth and alerts. Have an abort condition and a rollback owner. Record findings as tickets with owners. Failure modes: running it without a hypothesis, or without observability so you learn nothing.
