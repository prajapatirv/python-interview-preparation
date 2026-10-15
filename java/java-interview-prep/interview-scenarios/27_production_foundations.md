---
id: foundations-production
title: Production incidents & troubleshooting: from the basics (drafted)
stack: java
skill: production
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is your general approach when production is down?
tags: incident-response, production-support, rollback, rca, splunk, observability, basics

**Start here: the concepts**
- **Production (prod):** the live system real customers use. Mistakes here cost money and trust, so we act carefully and quickly.
- **Incident:** any unplanned event that harms users or the business, such as an outage or heavy slowness. Calling it an "incident" starts a structured process instead of everyone guessing.
- **Impact and scope:** impact is how badly users are hurt. Scope is who is hit (all users or some), since when, in which region, and in which feature. They decide how urgent the response is.
- **Incident roles:** typically an incident commander who coordinates, engineers who investigate, and a communicator who updates stakeholders. Roles exist so people don't duplicate work or all dive into debugging while nobody informs the business.
- **Mitigation:** an action that stops user pain quickly, even if it doesn't explain the cause. Examples:
  - **Rollback:** go back to the previous working version.
  - **Scale:** add servers or instances.
  - **Feature flag off:** a switch that disables a new feature without redeploying.
  - **Failover:** move traffic to a healthy backup region or instance.
- **Root cause:** the real underlying reason for the failure, found *after* users are safe.
- **Evidence:** dashboards (metrics over time), logs (for example in Splunk), traces (a request's path across services), and the list of recent changes.
- **RCA (root cause analysis):** a written review after recovery covering what happened, why, and how to prevent it. **Blameless** means we blame the process, not a person.

**The live scenario**
Friday 6:00 pm, a new version of the checkout service is deployed. At 6:10 the error rate jumps from 0.2% to 40%, and about 3,000 orders per minute are failing. An alert pages the on-call engineer. They confirm on the dashboard that all regions are affected and that it started right after the deploy. They declare an incident and name a commander and a communicator. The team rolls back at 6:22 and errors are normal by 6:25. Only then do they search Splunk for the exact exception. The cause was a bad database setting in the new release. Total pain was about 25 minutes. Hunting for the bug first could have meant an hour or more.

**What the interviewer is really checking**
Whether you stay calm and follow a clear order: restore service first, investigate second, communicate throughout, and learn afterwards. Fresher answers that jump straight to "read the code and find the bug" are a red flag.

**How I answer it**
1. **Confirm impact and scope** (who, since when, which region or feature). *Reason:* it tells you how urgent this is and where to look.
2. **Declare the incident and assign roles.** *Reason:* shared ownership and one coordinator prevent chaos.
3. **Mitigate first** (rollback, scale, flag off, failover). *Reason:* every minute costs users and money, and a known-good state is faster to reach than a diagnosis.
4. **Gather evidence** from dashboards, logs, traces and recent changes (deploys, config edits). *Reason:* most outages follow a change. Before restarting a sick server, I capture a thread dump (`jstack <pid>` or `jcmd <pid> Thread.print`), because a restart erases that evidence.
5. **Communicate regularly,** starting at step 1 and not only at the end. *Reason:* stakeholders stay calm when they get short, timed updates (what we know, what we're doing, next update time).
6. **After recovery, run a blameless RCA** with a timeline, root cause, action items with owners, and follow-up until they are done. *Reason:* otherwise the same incident returns.

Example Splunk search: `index=prod service=checkout level=ERROR | timechart count`

**Trade-offs and what can go wrong**
- Rolling back is not always safe. If the release changed the database schema, going back may break things, so check this before you roll back.
- Restarting hides evidence, so capture thread dumps or heap dumps first if it's safe.
- Changing many things at once makes it unclear what fixed the problem. Change one thing at a time and log it.
- Silence or guessing in updates damages trust.
- Skipping the RCA once things are "working again" is the most common mistake.

**How I'd monitor it**
- Error rate, latency and traffic dashboards, plus alerts that page on-call.
- Spring Boot Actuator health endpoints, and JVM and GC metrics.
- Splunk searches around the incident window and deploy time.
- A timeline recording each action and who took it.
- After the fix, watch the same metrics until stable.

**Follow-ups to expect**
- *Why mitigate before finding the root cause?* -> Users are hurting now. A rollback restores service in minutes, and the investigation can continue safely afterwards.
- *What if rollback isn't possible?* -> Turn off the feature flag, scale out, fail over, or ship a small hotfix, depending on the cause.
- *What does blameless mean?* -> We look for the gaps in process, testing or tooling that allowed the failure, and we don't punish individuals, so people report problems honestly.

**60-second answer**
When production is down, I first confirm the impact and scope: who is affected, since when, and which region or feature. Then I declare an incident and assign roles so one person coordinates and another communicates. My priority is to mitigate first, using a rollback, scaling, turning a feature flag off, or failing over, to stop the damage before hunting for the cause. Then I gather evidence from dashboards, Splunk logs, traces and recent changes, and I take a thread dump before restarting anything. I keep stakeholders updated throughout. After recovery, I lead a blameless RCA with a timeline, root cause and action items with owners, and I follow up until they are done.

### Q2 [fresher] What is an RCA and what does a good one contain?
tags: rca, incident-management, postmortem, blameless, 5-whys, production-support, basics

**Start here: the concepts**
- **Incident:** an unplanned event where a production system is broken or degraded and users are affected, for example checkout failing.
- **RCA (Root Cause Analysis):** a written document produced after an incident that explains what happened, why it happened, and what we will change so it does not happen again. It exists so the team learns from the failure instead of just forgetting it.
- **Blameless:** the review looks for gaps in the system (missing tests, missing alerts, unclear process), not for a person to punish. If people fear blame, they hide facts, and then the RCA is wrong.
- **Impact:** who and what was affected, and for how long, such as failed orders, lost revenue or affected users.
- **Timeline (UTC):** a minute-by-minute list of events. UTC is used so people in different time zones read the same clock.
- **Detection:** how we first learned about the problem (an alert, a customer complaint) and how long that took.
- **Mitigation:** the action that stopped the damage (rollback, restart, scaling up). It is different from the fix, which removes the underlying cause.
- **Root cause and contributing factors:** the root cause is the main reason it happened. Contributing factors are other conditions that let it happen or made it worse.
- **5 Whys:** asking "why?" repeatedly, usually about five times, to move from a symptom to a deeper cause.
- **Corrective actions:** concrete follow-up tasks, each with an owner and a due date.

**The live scenario**
On Tuesday at 14:05 UTC, a deploy of the Orders service added a new database query with no index. By 14:10, p99 latency (the time within which 99% of requests finish) rose from 300 ms to 12 s, and about 35% of checkouts failed. We had no latency alert. Support tickets told us at 14:23, so detection took 18 minutes. We rolled back at 14:45, which was the mitigation. About 8,000 orders failed (illustrative numbers). The RCA found three causes: the index was missing, the staging database was too small to show the slowness, and there was no latency alert.

**What the interviewer is really checking**
Whether you understand that an RCA is about learning and improving the system, not blaming someone. They also want to see that you know its parts, especially that actions need owners and dates.

**How I answer it**
1. **Summary and impact.** State in a few lines what broke, for whom, and for how long. Readers, including managers, need the size of the problem first.
2. **Timeline in UTC.** List events in order: deploy, first error, alert or complaint, mitigation, recovery. This prevents arguments from memory and shows where time was lost.
3. **Detection.** Record how we found out and how long it took. Slow detection is a problem you can fix on its own, usually with better alerts.
4. **Root cause and contributing factors.** Use 5 Whys: why were checkouts failing? Because queries were slow. Why? No index. Why was it deployed? Review and tests did not catch it. Why? Staging data is tiny. Stop at systemic causes such as "no load test with realistic data", not "human error". "A developer made a mistake" gives you nothing to fix, whereas a missing safety net does.
5. **What went well and what went badly.** Note what helped (fast rollback) and what hurt (no alert). Both teach something.
6. **Mitigation.** Describe what stopped the impact and how quickly.
7. **Corrective actions with owners and dates.** Cover three kinds: prevent it (index review, realistic test data), detect it faster (p99 latency alert), recover faster (one-click rollback). An action with no owner or date usually never happens.

**Trade-offs and what can go wrong**
- Blame language ("Bob forgot") makes people hide facts.
- Stopping at the first "why" produces shallow fixes.
- Real incidents rarely have one cause, so list contributing factors too.
- An overlong action list never gets done, so prioritise.
- Writing the RCA while still firefighting leads to mistakes. Wait until service is stable, but do it within days while memory is fresh.
- An RCA that is filed and forgotten is wasted effort.

**How I'd monitor it**
- Track whether action items are closed by their due dates.
- Track MTTD (mean time to detect) and MTTR (mean time to recover) across incidents; they should fall over time.
- Check that new alerts exist and fire in a test.
- Watch for the same incident repeating, which means the RCA failed.
- For evidence in the timeline, use Splunk searches for error counts per minute and Spring Boot Actuator or APM latency graphs.

**Follow-ups to expect**
- *Why blameless?* -> People who fear punishment hide details. Blameless reviews get honest facts and find fixable system gaps.
- *What is the difference between mitigation and root-cause fix?* -> Mitigation stops the pain quickly (rollback). The fix removes the underlying cause (add the index, add the test).
- *When do you stop asking "why"?* -> When you reach something the organisation can change, such as a process, tool or missing check, rather than an individual's mistake.

**60-second answer**
An RCA is a blameless written review done after an incident to learn what happened and prevent a repeat. It starts with a summary and the impact, then a UTC timeline, and how we detected the problem and how long that took. Next comes the root cause and contributing factors, found with 5 Whys, stopping at systemic causes rather than "human error". It also notes what went well and badly, and what mitigation stopped the damage. Most importantly, it lists corrective actions with owners and dates to prevent the issue, detect it faster and recover faster. Without owners and dates, the learning never turns into change.

### Q3 [mid] What is the difference between an incident, a problem and a change?
tags: incident-management, problem-management, change-management, itil, rca, production-support, basics

**Start here: the concepts**
- **Incident:** an unplanned interruption or slowdown of a service, such as checkout returning errors. The goal is to restore service quickly, even if you don't yet know why it broke. It exists so users stop suffering before anyone debates causes.
- **Problem:** the underlying cause of one or more incidents, for example "the connection pool is too small". The goal is a permanent fix so the incident doesn't come back. It is separate from the incident because finding a root cause takes calm, careful time that you don't have mid-outage.
- **Change:** any modification to the system: a code deploy, a config edit, a schema migration, an infrastructure update. Changes exist because software must evolve, but each one is a risk, so teams track and review them.
- **Mitigation / workaround:** a fast action that stops the pain without fixing the cause (rollback, restart, scale out, feature flag off).
- **RCA (root cause analysis):** the structured investigation, usually blameless, that finds why an incident really happened. It is the main work of problem management.
- **"What changed?":** the first diagnostic question. Systems that were stable until a given minute usually changed at that minute.

**The live scenario**
At 10:05 a team deploys v2.4 of a payment API that handles about 800 requests per second. By 10:12 the error rate climbs from 0.1% to 35% and customers can't check out. The on-call engineer opens an **incident**, asks "what changed?", and sees the 10:05 deploy. They roll back at 10:20, and errors drop to normal by 10:25. The incident is over, but the cause is unknown. The next day the team opens a **problem** record. Splunk logs show "connection pool exhausted", and a config file in v2.4 had set the pool size to 5 instead of 50. The permanent fix is a config validation check in the pipeline. That is a new **change**, and it goes through review.

**What the interviewer is really checking**
Whether you separate "stop the bleeding" from "find and fix the cause", and whether you instinctively look at recent changes first instead of guessing.

**How I answer it**
1. **Define the incident as restoring service.** Speed matters because every minute costs users and money. Rollback, scaling or a feature flag is fine even without knowing the cause.
2. **Define the problem as the root cause.** If you only restore service, the same failure returns. A problem record tracks the investigation, the fix and an owner, and it can cover several incidents with the same cause.
3. **Define the change as any modification.** This includes deploys, config, infrastructure and schema changes. A change can cause an incident, and a fix for a problem is itself a change, so it needs the same review.
4. **Ask "what changed?" first.** Many outages follow a recent change, so checking the deploy log, config history and feature flags is the cheapest and fastest lead.
5. **Widen "change" beyond deploys.** Also check data volume growth, certificate expiry, dependency behaviour and traffic patterns. Nobody "deployed" these, but the system's environment changed.
6. **Link all three.** Change → incident → problem → new change. Writing this chain in the postmortem timeline is how you show ownership.

**Trade-offs and what can go wrong**
- Rolling back fast hides the cause. If nobody opens a problem record, the same bug ships again.
- "Most outages come from changes" is a heuristic, not a law. Hardware failure, a traffic spike or an expired certificate can happen with no deploy, so don't stop investigating after a change looks innocent.
- Mixing up the terms causes bad process: people try to find the root cause during the outage and prolong it, or they close tickets without fixing anything.
- Not every incident needs a problem record. Do it for major or recurring ones.
- A rollback or hotfix is itself a change and carries risk, so do it in a controlled way.

**How I'd monitor it**
- Put deploy and config-change markers on dashboards so you can see if an error spike lines up with a change.
- Alert on error rate and latency (for example, Actuator metrics in APM) so detection happens within minutes.
- In Splunk, correlate errors with versions: `index=app level=ERROR | timechart count by app_version`
- Track MTTR (mean time to restore) for incidents, and recurrence rate and open action items for problems.

**Follow-ups to expect**
- *Does every incident need a problem record?* -> No. Raise one for major, repeated or unexplained incidents. Minor one-offs with a known cause may not need it.
- *What is a workaround or "known error"?* -> A documented way to reduce impact while the permanent fix is pending, such as "restart the pod when the queue stalls".
- *Is a rollback a change?* -> Yes. It is usually an emergency change with lighter approval but still logged, so the timeline stays accurate.

**60-second answer**
An incident is an unplanned service disruption, and my job is to restore service as fast as possible, using rollback, scaling or a feature flag if needed. A problem is the underlying root cause of one or more incidents, and I fix it permanently after service is back, through a blameless RCA. A change is any modification, such as a deploy, config edit or schema update. Many outages follow a recent change, so my first question is always "what changed?" I also check non-deploy changes like data growth, expired certificates and dependency behaviour. Afterwards I link the chain: the change caused the incident, the problem record finds the root cause, and the permanent fix goes out as a new, reviewed change.

### Q4 [mid] Service is slow - what is your checklist?
tags: production-incidents, latency, troubleshooting, observability, jvm, thread-pools, basics

**Start here: the concepts**
- **Latency**: how long one request takes. "Slow" means latency is higher than normal, so first confirm it with numbers (p95/p99, not just the average).
- **Hop**: one step in a request's path, such as gateway -> service -> database -> downstream API. Total time is the sum of the hops, so one slow hop slows everything.
- **APM / distributed trace**: a tool that records how long each hop took for a sample request. It shows where the time went, so you don't guess.
- **Saturation**: a resource is so busy that new work has to wait. Waiting is what users feel as slowness.
- **GC (garbage collection)**: the JVM pauses or competes with your code to free unused memory. Long or frequent GC makes requests stall.
- **Thread pool**: a fixed set of worker threads. If all are busy or blocked, new requests queue up.
- **Connection pool**: a limited set of reusable connections to a database or HTTP service. If all are taken, callers wait for one.
- **Queue depth**: how many items are waiting. A growing queue means work arrives faster than it is processed.
- **Retry storm**: clients retry failed or slow calls, adding more load to an already struggling service.
- **Load shedding**: deliberately rejecting some requests (for example with HTTP 429/503) so the rest stay fast.
- **Profile / flame graph / JFR**: JFR (Java Flight Recorder) is a low-overhead recorder built into the JVM. A flame graph shows which methods use the most time.

**The live scenario**
At 10:05 on a Monday, the orders API goes from p95 200 ms to 4 s. Traffic is about 2,000 requests/s, and checkout conversion is dropping. A deploy went out at 10:00. The on-call engineer opens the trace. The service itself is fast, but the call to the inventory database takes 3.5 s. The DB connection pool is exhausted, and the cause is a new query without an index. The team rolls back, latency recovers in minutes, and the index is added before the next release.

**What the interviewer is really checking**
Whether you work in a calm, ordered way: find the slow hop with evidence, protect users first, and only then dig for the root cause. They also want to see that you don't just "add servers".

**How I answer it**
1. **Confirm and scope it.** Look at p95/p99, which endpoints, and since when. This tells you whether it is one endpoint or everything, and gives you a start time to compare against.
2. **Trace which hop is slow.** Use APM or traces. This stops guesswork and points you at the right component.
3. **Check recent deploys and config changes.** Compare the start time with the release log. It is the cheapest check and often the cause. If it matches, roll back first and investigate afterwards.
4. **Check saturation.** Look at CPU, memory and GC logs, thread pools, DB/HTTP connection pools and queue depth. A pool at 100% with waiting callers explains slowness even when the CPU is idle. If threads look stuck, take thread dumps:
   `jcmd <pid> Thread.print` (take 3 dumps, 10 s apart). Threads in the same place across dumps show where they are blocked.
5. **Check dependencies.** Look for slow DB queries and locks, and for downstream latency. Your service is only as fast as what it waits on.
6. **Check traffic.** Look for a spike, bots or a retry storm. If load is abnormal, the fix is rate limiting or shedding, not code.
7. **Mitigate while you diagnose.** Options are rollback, scale-out, caching hot reads, or load shedding. Pick the one that matches the cause: scaling out does not help if the shared database is the bottleneck, and can make it worse.
8. **Reproduce with a profile.** Record JFR on the affected instance and read the flame graph to find the hot code. Then fix, hold a blameless RCA (focus on the system, not on blaming a person), and add prevention.

**Trade-offs and what can go wrong**
- Scaling out hides a bad query and increases pressure on the database.
- Caching adds stale-data risk and invalidation complexity.
- Load shedding means some users get errors, which is a deliberate trade for protecting everyone else.
- Rollback may undo a needed fix, so check what else was in the release.
- Don't change many things at once, or you won't know what worked.
- Profiling and heap dumps add overhead, so use JFR rather than heavy tools on a struggling instance.
- Watching only average latency hides the slow tail.

**How I'd monitor it**
- p50/p95/p99 latency, error rate and throughput per endpoint, with alerts on p95.
- Spring Boot Actuator/Micrometer metrics: thread pool usage, HikariCP active/pending connections, JVM GC pause time.
- GC logs for long or frequent pauses.
- Splunk: search for errors, timeouts and slow-query logs from the incident window, and compare against the deploy time.
- Slow query log and lock waits on the database.

**Follow-ups to expect**
- *CPU is low but requests are slow. Why?* -> Threads are waiting, not working: an exhausted connection pool, a slow downstream, or lock contention. Thread dumps show where.
- *Why not just scale out?* -> It only helps if the bottleneck is per-instance. If it is a shared DB or a bad query, more instances add load and make it worse.
- *How do you tell a GC problem?* -> GC logs show long or frequent pauses, and heap usage climbs and stays high after collections.

**60-second answer**
First I confirm the slowness with p95/p99 numbers and find when it started. Then I open the trace to see which hop is slow, and I check whether a deploy happened at that time. If it did, I roll back first and investigate afterwards. Next I check saturation: CPU, GC, thread pools, connection pools and queue depth. I also check dependencies like slow DB queries or a slow downstream, and the traffic for spikes, bots or retry storms. While diagnosing I mitigate with rollback, caching, load shedding or scaling out, but only scale out if the bottleneck is per-instance. Finally I profile with JFR to find the code, fix it, and write a blameless RCA with prevention steps.

### Q5 [mid] Thread dump says all threads are WAITING/BLOCKED. What now?
tags: thread-dump, jstack, thread-states, lock-contention, connection-pool, timeouts, basics

**Start here: the concepts**
- **Thread dump:** a snapshot of every thread in the JVM and the line of code it is running or stuck on. Take it with `jstack` or `jcmd`. It shows where threads are stuck right now.
- **RUNNABLE:** the thread is running, or could run. A thread blocked reading a network socket usually still shows as RUNNABLE, because the JVM hands the wait to the operating system.
- **BLOCKED:** the thread is waiting to enter a `synchronized` block that another thread holds.
- **WAITING / TIMED_WAITING:** the thread is parked until something happens (`wait`, `park`, `join`, `sleep`). TIMED_WAITING has a time limit, WAITING does not. Idle pool threads waiting for work show up here too, and that is normal.
- **Lock contention:** many threads want the same lock and only one gets it at a time.
- **Deadlock:** thread A holds lock 1 and wants lock 2, while thread B holds lock 2 and wants lock 1. Neither can ever continue.
- **Connection pool:** a fixed set of reusable database connections (for example HikariCP). If all are in use, new requests wait for one to be returned.
- **Timeout:** a maximum time to wait. Without one, a slow dependency can hold a thread forever.

**The live scenario**
An order service handles about 800 requests per second. At 10:05 latency climbs and by 10:08 the health checks fail. CPU is only 5%, so the service is not busy but stuck. Every request thread (200 in the Tomcat pool) is parked. The team takes dumps, and 190 threads sit in `HikariPool.getConnection`. The ones holding the connections are waiting on a slow payment-history query, and a new report job started at 10:04. The pool is exhausted and nothing moves.

**What the interviewer is really checking**
Whether you stay calm and follow a method: capture evidence, compare it over time, group threads by what they are waiting for, and find the *holder* of the resource, not just the waiters. Also whether you mitigate first.

**How I answer it**
1. **Mitigate, but capture evidence first.** Take the instance out of the load balancer, grab dumps, then restart or roll back. A restart destroys the evidence, and the stuck instance cannot serve traffic anyway.
2. **Take 3 dumps about 10 seconds apart.** One dump is a photo, three show whether threads are truly stuck or just passing through. Threads in the same place in all three are the real problem.
   `jcmd <pid> Thread.print -l`
   (`-l` also shows `java.util.concurrent` locks.)
3. **Check for a deadlock.** The dump ends with "Found one Java-level deadlock" if there is one. Then fix the lock ordering.
4. **Group threads by identical stack trace.** The biggest group is your answer. Ignore healthy idle threads, such as pool workers waiting for tasks.
5. **Match the group to a cause:**
   - Many threads "waiting to lock <0x…>": lock contention. Find the thread that has "locked <0x…>" with the same address. That is the owner. See what it is doing, probably slow I/O inside a `synchronized` block.
   - Many threads in a socket read (`SocketInputStream.read`, usually RUNNABLE): a slow downstream with no read timeout.
   - Many threads in the connection pool's `getConnection`: the pool is exhausted, by slow queries, long transactions, or leaked connections (a missing `close()`).
6. **Fix the root cause.** Add connect and read timeouts, close connections with try-with-resources, shorten transactions, tune or kill the slow query, and shrink the lock scope.
7. **Write a blameless RCA** with a timeline, and add prevention (timeouts by default, alerts, load tests).

**Trade-offs and what can go wrong**
- Making the pool bigger hides the problem and can overload the database.
- Timeouts that are too short cause false failures and retry storms. Too long, and threads still pile up.
- Taking dumps briefly pauses the JVM, so avoid taking them in a tight loop.
- Reading one dump alone can mislead you, so compare several.
- A restart without dumps means you will see it again with no answer.

**How I'd monitor it**
- Actuator/Micrometer: `hikaricp.connections.active`, `hikaricp.connections.pending`, `hikaricp.connections.acquire`, and `jvm.threads.states`.
- Splunk: search for "Connection is not available, request timed out" and for timeout exceptions, and chart the count per minute.
- APM: downstream call latency and error rates.
- Alerts: pending connections above 0 for more than 1 minute, and the blocked-thread count.

**Follow-ups to expect**
- *How do you tell a leaked connection from a slow query?* -> A leak keeps the connection checked out with no query running. Hikari's `leakDetectionThreshold` logs the stack trace of whoever borrowed it. A slow query shows up in the database's active-session view.
- *Why is a thread reading a socket not shown as WAITING?* -> The JVM reports a native socket read as RUNNABLE, so look for `socketRead` frames, not the state.
- *How do you find the lock owner for a `ReentrantLock`?* -> Use `jstack -l` or `jcmd Thread.print -l`. The "Locked ownable synchronizers" section lists who holds it.

**60-second answer**
First I protect users: remove the stuck instance from the load balancer, take three thread dumps about 10 seconds apart with jcmd, then restart or roll back. Some waiting is normal, so I look for threads stuck in the same place across all dumps. I check for a deadlock, then group threads by stack trace. Many threads on one lock mean contention, and I find the thread that owns that lock. Many threads in a socket read mean a slow downstream with no timeout. Many threads in the pool's getConnection mean the pool is exhausted by slow queries or leaked connections. I fix the cause with timeouts, closing connections, shorter transactions and smaller lock scope, then write a blameless RCA and add alerts on pool pending count and blocked threads.

### Q6 [mid] Connection pool exhausted (HikariCP "Connection is not available").
tags: hikaricp, connection-pool, spring-boot, jdbc, incident-response, database, basics

**Start here: the concepts**
- **Connection pool:** Opening a database connection is slow, so the app opens a few at startup and lends them out. A request borrows one, uses it, and returns it. HikariCP is the default pool in Spring Boot.
- **Pool exhaustion:** All connections are borrowed and a new request has to wait. If it waits longer than `connectionTimeout` (30 seconds by default), HikariCP throws "Connection is not available, request timed out after 30000ms".
- **Active vs pending:** Active means connections currently lent out. Pending means threads waiting for one. Active at the maximum with pending above zero means the pool is saturated.
- **Transaction holding a connection:** A transaction keeps its connection until it commits or rolls back. If the code calls a slow remote service inside the transaction, the connection sits idle but unavailable.
- **Connection leak:** Code borrows a connection and never returns it. `leakDetectionThreshold` makes Hikari log a warning with a stack trace when a connection stays out too long. It only reports the leak; it does not close the connection.
- **Database max connections:** The database accepts only a fixed number of connections in total. Every pod has its own pool, so the total is pods × pool size.

**The live scenario**
At 10:15 an orders service (6 pods, pool size 10 each, so 60 connections; database limit 100) went from 200 ms to 30 s latency, with 40% HTTP 500s. Traffic was a normal 150 requests/s. A release that morning added a payment-API call inside a `@Transactional` method. The payment API slowed to 8 s, so every request held a connection for 8 s. 60 connections ÷ 8 s ≈ 7 requests/s of capacity against 150 requests/s of demand. The pool drained in seconds. The database itself was nearly idle.

**What the interviewer is really checking**
Whether you treat this as a symptom with several possible causes rather than "increase the pool size", and whether you stabilise first, then find the cause with evidence.

**How I answer it**
1. **Mitigate first.** Roll back the release, switch off the feature flag, or restart the worst pods. This restores service while you investigate. Do not raise the pool size as a first reaction, because it can overload the database.
2. **Confirm saturation.** Check `hikaricp.connections.active`, `hikaricp.connections.pending` and `hikaricp.connections.timeout` in Actuator or Grafana. This tells you whether the pool is really the bottleneck.
3. **Take a thread dump** (`jcmd <pid> Thread.print` or `jstack`). Many threads waiting in `HikariPool.getConnection` confirm the queue. Then look at the threads *holding* connections: are they in a socket read (a remote call) or in a JDBC query?
4. **Find why connections are held too long.** Check the likely causes in order:
   - a connection held during a remote call;
   - long-running transactions or slow queries (check the database's active-session view);
   - leaked connections, using the leak detector;
   - a pool smaller than real concurrency;
   - database max connections reached across all pods.
5. **Fix the cause, then size the pool.** Move remote calls outside the transaction, shorten transactions, and add timeouts (query, transaction and HTTP client). Enlarging the pool only hides the problem. When you do size it, keep pods × `maximumPoolSize` below the database limit, with headroom for admin and other services.

```
spring.datasource.hikari.leak-detection-threshold=20000   # ms, logs a stack trace
```

**Trade-offs and what can go wrong**
- A bigger pool delays the failure and can push the database into overload, which makes every query slower.
- Autoscaling pods adds more pools, so it can hit the database connection limit.
- A very low leak threshold produces false alarms on legitimately slow queries.
- Spring Boot's open-in-view setting (`spring.jpa.open-in-view`, on by default) can keep a connection for the entire web request.
- Timeouts that are too aggressive turn slowness into errors, so choose them from observed latencies.

**How I'd monitor it**
- Metrics: `hikaricp.connections.active`, `.pending`, `.timeout`, `.acquire` (wait time) and `.usage` (hold time). Alert when pending stays above 0 for a minute or two.
- Splunk: search for "Connection is not available" and "Apparent connection leak detected", count by pod and time, and compare with the deploy time.
- Database: sessions per application, longest-running transactions, and total connections against the limit.
- Release dashboards that show p95 latency next to the pool metrics.

**Follow-ups to expect**
- *Why not just increase `maximumPoolSize`?* -> If connections are held too long, more of them only move the failure and can overload the database. Fix hold time first, then size the pool using the database's capacity.
- *How do you find a leak?* -> Set `leakDetectionThreshold`. The logged stack trace shows where the connection was borrowed. Usually a connection was not closed, or a transaction never finished.
- *How does pod count affect the pool?* -> Total connections = pods × pool size. Autoscaling must stay under the database's max connections.

**60-second answer**
"First I stabilise: roll back the last change or restart the bad pods, because a full pool means users are waiting. Then I check HikariCP's active and pending metrics to confirm the pool is saturated. A thread dump shows what the threads holding connections are doing. Usually a transaction is held open during a remote call, a query is slow, or a connection leaked, which I confirm with `leakDetectionThreshold`. I fix that cause by moving remote calls out of transactions and adding timeouts. Only then do I size the pool, keeping pods × pool size under the database's max connections. Afterwards I run a blameless RCA and add alerts on pending connections."

### Q7 [mid] Kafka consumer lag increases after a deploy.
tags: kafka, consumer-lag, rebalance, incident-response, rollback, observability, basics

**Start here: the concepts**
- **Topic and partition:** A topic is a named stream of messages. It is split into partitions, and each partition is an ordered log. Partitions let many consumers read in parallel.
- **Consumer group:** Consumers with the same group id share a topic. Kafka gives each partition to exactly one consumer in the group, so the number of partitions is the ceiling on useful parallelism.
- **Offset and lag:** An offset is a message's position in a partition. The consumer commits the offset it has processed. Lag is the latest offset minus the committed offset, meaning how far behind the consumer is.
- **Rebalance:** Kafka redistributes partitions when consumers join, leave or are considered dead. Consumption pauses or slows during a rebalance (less so with cooperative rebalancing).
- **`max.poll.interval.ms`:** The maximum time allowed between two `poll()` calls. If processing a batch takes longer, Kafka assumes the consumer is stuck, removes it and triggers a rebalance. The batch is then redelivered, which can cause a rebalance loop.
- **Poison message:** A message that always fails processing, for example bad data. If it is retried forever, it blocks its partition.
- **Partition skew:** Some partitions get far more traffic than others, often because of a hot message key. One consumer is overloaded while the others sit idle.
- **Sink:** The system the consumer writes to, such as a database.

**The live scenario**
At 14:00 we deploy order-service v2, which consumes `orders` (12 partitions, 6 pods). Normal lag is under 1,000. By 14:10 lag is 400,000 and growing, and order confirmations are delayed by minutes. Customers are complaining and support is raising tickets.

**What the interviewer is really checking**
Whether you stop the impact first and then diagnose methodically from evidence, rather than guessing. Also whether you know the common causes of lag after a deploy.

**How I answer it**
1. **Confirm and communicate.** Check that lag really started at the deploy time. Post a status update with the impact and an owner. A short lag blip during a rolling deploy is normal, but sustained growth is not.
2. **Mitigate first.** Roll back, or turn off the new code path with a feature flag. Rollback is the fastest safe fix. Diagnosis can happen after customers are protected.
3. **Check consumer count and health.** Look for crash loops (failing liveness probes, out-of-memory kills) or a stalled rollout. Fewer consumers means each carries more partitions. A failing readiness probe can also block a rolling deploy from finishing.
4. **Look for rebalance loops.** Search logs for repeated rebalances and commit failures. If a batch takes longer than `max.poll.interval.ms`, the consumer is kicked out and the same batch comes back. Fix this by lowering `max.poll.records` or speeding up processing. Raise the interval only as a stopgap.
5. **Look for a slow new code path.** Take thread dumps (`jstack` or `jcmd Thread.print`) from a consumer. If threads wait on a remote call or database, the bottleneck is downstream.
6. **Check the sink.** Database slowness from locks, a missing index or an exhausted connection pool shows up as lag. Scaling consumers would then make the database worse.
7. **Check for a poison message.** If one partition's lag grows while the others are fine, and the same error repeats in the logs, a bad record is being retried. Send it to a dead-letter topic after N attempts and move on.
8. **Check for skew.** Describe the group and compare per-partition lag.
```
kafka-consumer-groups.sh --describe --group orders-group
```
9. **Scale only if the bottleneck is the consumer.** More consumers help only up to the partition count, so a 13th consumer on 12 partitions sits idle. Increasing partitions changes key-to-partition mapping, which affects ordering.
10. **Recover and replay safely.** Once fixed, the consumers drain the backlog. If messages were skipped or mishandled, replay them by resetting offsets with the group stopped. Consumers must be idempotent, because replay produces duplicates.
11. **Blameless RCA.** Write a timeline and the root cause. Prevention: load-test with production-like batch sizes, canary deploys, and a lag alert tied to the deploy.

**Trade-offs and what can go wrong**
- Rollback loses the new feature, but it is cheap and fast.
- Raising `max.poll.interval.ms` hides slow processing and delays failure detection.
- Skipping a poison message risks data loss, so route it to a dead-letter topic instead of dropping it.
- Resetting offsets while consumers run does not work and risks duplicates.
- Scaling beyond the partition count or against a slow database wastes money and can worsen the outage.

**How I'd monitor it**
- Per-partition and group lag, using a lag exporter or `records-lag-max`.
- Rebalance rate and consumer count over time.
- Splunk searches for rebalance messages, `CommitFailedException` and repeated identical errors, filtered by deploy version.
- Processing time per batch, database latency and connection pool use in Actuator or APM.
- Pod restarts and the GC log, to spot memory pressure.
- Alert on lag growing for N minutes, not just on its absolute size.

**Follow-ups to expect**
- *Why did lag rise even though the code looked fine?* -> Fewer consumers, a slower dependency, or a rebalance loop can each cause it. Compare before and after the deploy for consumer count, batch time and the sink's latency.
- *Can I just add consumers?* -> Only up to the partition count, and only if the consumer is the bottleneck. It does not fix a poison message or a slow database.
- *How do you avoid duplicates on replay?* -> Make processing idempotent, for example with a unique key or upsert in the sink.

**60-second answer**
When lag rises after a deploy, I first confirm the timing and roll back or flip a feature flag to stop the impact, while keeping stakeholders updated. Then I diagnose with evidence. I check whether consumers are crash-looping, whether `max.poll.interval.ms` is being exceeded and causing rebalance loops, and whether a poison message is stuck on one partition. I also check whether new code or a slow database is the bottleneck, using thread dumps, Splunk and per-partition lag, and I look for skew. I scale consumers only if they are the bottleneck, and never beyond the partition count. After the fix I let the backlog drain or replay safely with idempotent consumers. Then I run a blameless RCA and add canary deploys and lag alerts to prevent a repeat.

### Q8 [mid] Intermittent 502/503/504 behind a load balancer.
tags: load-balancer, 502-503-504, timeouts, keep-alive, graceful-shutdown, kubernetes, basics

**Start here: the concepts**
- **Load balancer (LB):** a server that receives client requests and forwards each to one of several healthy app instances, so no single instance is overloaded and one can fail without a full outage.
- **502 / 503 / 504:** the LB's own error codes. 502 Bad Gateway means the app gave a broken response or reset the connection. 503 Service Unavailable means no healthy instance was available, or the service was overloaded. 504 Gateway Timeout means the app did not answer in time.
- **Keep-alive (idle timeout):** opening a TCP connection is expensive, so the LB keeps connections open and reuses them. Each side closes a connection after it has been idle for a set time.
- **Stale connection:** a connection one side has closed but the other still thinks is open. Sending a request on it fails with a reset, which shows up as a 502.
- **Readiness probe:** a check (for example in Kubernetes) that tells the LB whether an instance can take traffic right now.
- **Graceful drain:** when an instance shuts down, it first stops receiving new requests and finishes in-flight ones, then exits.
- **preStop hook:** a Kubernetes step that runs before the app gets the stop signal. A short sleep there gives the LB time to remove the pod.
- **NAT/firewall idle expiry:** network devices between LB and app forget idle connections after some minutes. The next packet is then dropped or reset.
- **Idempotent call:** one that is safe to repeat, such as GET or PUT. A retried POST can create duplicates.

**The live scenario**
An orders API runs 8 pods at about 1,200 requests/second. Users see roughly 0.3% failures, mostly 502s, scattered with no pattern. Dashboards show CPU at 40% and normal latency. Spikes of 503s appear at every deploy. The LB idle timeout is 60s and Tomcat's keep-alive is 30s. About once a minute the app closes a connection that the LB still thinks is open, and the LB's next request on it is reset.

**What the interviewer is really checking**
Whether you can map each status code to a cause, work out which layer produced it from evidence rather than guessing, and know the timeout ordering rules.

**How I answer it**
1. **Stabilise first.** If it started after a deploy, roll back. If it is overload, scale out. Tell stakeholders the impact and that mitigation is under way. Reason: restore users before you investigate.
2. **Identify which layer returned the error.** Compare LB access logs (the LB's status and upstream status) with app logs in Splunk. If the app never saw the request, the problem is between LB and app. Reason: this splits "app is slow" from "connection problem".
3. **Read the code.** 502 usually means a reset or stale connection, or a pod killed mid-request. 503 means no healthy targets (failing readiness, or a pod not yet ready or already gone). 504 means the app or a downstream call was slower than the LB timeout.
4. **Fix the keep-alive mismatch.** The app's idle timeout must be longer than the LB's, so the LB closes first and never reuses a connection the app already closed. In the scenario, set Tomcat's keep-alive above 60s.
5. **Fix the request timeouts.** Each outer layer should wait slightly longer than the one inside it (client > LB > app > downstream call). Then the innermost layer fails cleanly with a real error instead of an outer layer giving up and returning a generic 504. The stored answer's "client < LB < server" is only right for the idle timeouts above, not for request timeouts.
6. **Make shutdown graceful.** Remove the pod from the LB first (preStop sleep of a few seconds), then drain in-flight requests, then exit. Set `terminationGracePeriodSeconds` larger than the sleep plus drain time. Reason: the LB takes a few seconds to learn a pod is leaving.
```yaml
server.shutdown: graceful   # Spring Boot 2.3+
spring.lifecycle.timeout-per-shutdown-phase: 20s
```
7. **Check readiness and NAT/firewall expiry.** Readiness should reflect real ability to serve. For idle-expiry resets, use TCP keep-alive probes or an idle timeout shorter than the device's.
8. **Add retries only for idempotent calls**, with a limit and backoff. Then run a blameless RCA with a timeline and action items.

**Trade-offs and what can go wrong**
- Retries on non-idempotent calls cause duplicates, and unbounded retries amplify an overload (a retry storm).
- Longer app keep-alive holds more idle connections and uses more memory.
- A long preStop sleep slows deploys.
- Raising timeouts to hide 504s only hides slow code.
- Fixing one layer while another still disagrees leaves the problem half-fixed.

**How I'd monitor it**
- LB metrics: 5xx counts split by LB-generated vs target-generated, target response time, healthy host count.
- Splunk: search LB logs for status 502/503/504 grouped by pod and time, then correlate with deploy and restart events.
- Actuator health and readiness endpoints, plus pod restart counts.
- Alert on the 5xx rate and on healthy targets below a threshold.

**Follow-ups to expect**
- *Why do 502s often appear at low traffic?* -> Connections sit idle longer, so they are more likely to hit the idle timeout and become stale.
- *Why do 503s appear during deploys?* -> Traffic still goes to pods that are shutting down or not yet ready. Fix with readiness, a preStop sleep and graceful shutdown.
- *Is retrying a 504 safe?* -> Only for idempotent calls, because the first request may still be running on the server.

**60-second answer**
First I mitigate: roll back a bad deploy or scale out, and tell stakeholders. Then I find which layer produced the error by comparing LB logs with app logs in Splunk. 502 usually means a reset connection, 503 means no healthy target, and 504 means a timeout. The most common cause is mismatched idle timeouts: the app's keep-alive must be longer than the LB's, so the LB closes first. I also make request timeouts shrink as you go inward, and I make shutdown graceful with a preStop sleep, draining, and honest readiness checks. I add bounded retries only for idempotent calls. I finish with a blameless RCA and alerts on 5xx rate and healthy target count.

### Q9 [mid] Database CPU 100% - what do you do?
tags: database, cpu, incident-response, slow-queries, execution-plan, connection-pool, troubleshooting, basics

**Start here: the concepts**
- **Database CPU**: the processor time the database server spends parsing SQL, scanning rows, sorting, joining and handling connections. At 100%, every query queues for CPU, so everything gets slow.
- **Top SQL**: a ranking of statements by total time or CPU used. The DB keeps these statistics so you can see which few queries cause most of the load. Oracle exposes them through `v$sql` and AWR (Automatic Workload Repository, hourly performance snapshots, which needs a Diagnostics Pack licence). PostgreSQL uses the `pg_stat_statements` extension, which must be enabled first.
- **Execution plan**: the DB's chosen recipe for running a query (which index to use, how to join). A **plan change** happens when the DB picks a different recipe, for example after statistics refresh or a data-volume shift, and the new one can be far slower.
- **Index**: a sorted lookup structure. Without one, the DB does a **full table scan**, reading every row, which burns CPU.
- **Lock wait**: a session paused because another holds a lock on the same row. Waiting uses little CPU, so lock waits usually explain slowness, not 100% CPU. Check them, but don't expect them to be the cause.
- **Connection storm**: a sudden flood of new connections (a restart, a retry loop, a pool misconfigured). Each connection costs CPU and memory.
- **Read replica**: a read-only copy of the database that can serve SELECTs.

**The live scenario**
At 10:05 on a Monday, an order service's p95 latency jumps from 150 ms to 8 s, and the primary DB shows 100% CPU. Alerts fire and checkout errors climb to 12%. Top SQL shows one query, a finance "all orders this quarter" report, started at 10:00 and accounts for about 70% of CPU. It scans a 200-million-row table because the filter column has no index. The team throttles the report, checkout recovers within minutes, and the index is added later in a quiet window.

**What the interviewer is really checking**
Whether you stabilise first, then find the cause with evidence instead of guessing, and whether you know that each quick fix (kill, index, replica) has its own risk.

**How I answer it**
1. **Confirm and size the impact.** Check that the CPU is the database process, not another process on the host, and see which services are failing. Post a first update to stakeholders. This keeps everyone aligned and avoids duplicate work.
2. **Look at what is running now.** Query top SQL (`v$sql`/AWR, or `pg_stat_statements`) and the active-session list, sorted by CPU or total time. Usually one or two statements dominate, so you aim at those instead of tuning blindly.
3. **Check the usual suspects:** a recent plan change, a missing index, a runaway report, lock waits, a connection storm. Ask "what changed?" (a deploy, a stats job, a new batch). Most incidents follow a change.
4. **Mitigate before the perfect fix.** Pick the least risky option:
   - Throttle the caller or pause the report, which is fast and reversible.
   - Kill or limit the offending session. Warning: killing a session that has been writing forces a rollback, which can take a long time and use more resources, so prefer killing read-only queries.
   - Move read traffic to a replica, which works only for reads.
   - Turn on caching for hot, repeated reads.
   - Add an index online, but only if the DB has headroom, because index builds use CPU and I/O and can make things worse mid-incident.
5. **If it's a connection storm,** cap the pool size, stop retry loops and fix the cause. More connections rarely help a CPU-bound database.
6. **Fix the root cause after recovery:** rewrite the query, add the right index, pin or restore the good plan, refresh statistics, or move the report to a replica or off-hours.
7. **Blameless RCA and prevention.** Write a timeline, find the process gap (for example, no review of reports hitting the primary), and add a slow-query alert and a statement timeout.

**Trade-offs and what can go wrong**
- Killing sessions can leave a long rollback and lose users' work.
- Replicas lag, so recent writes may not be visible, and the report may show stale data.
- Caching can serve stale data.
- A new index slows writes and takes storage, and one index can change other queries' plans.
- Throttling protects the DB but degrades the feature, so tell the business.
- Common mistake: restarting the DB, which clears caches and usually makes things worse.

**How I'd monitor it**
DB CPU, active sessions, and top SQL by CPU. Slow-query count, lock waits and connection count. On the app side, HikariCP pool metrics through Actuator (active and pending connections) and p95 latency. In Splunk, search for slow-query and timeout errors by service and time. Alert on sustained CPU above a threshold (for example, 80% for 5 minutes) and on sudden jumps in connection count.

**Follow-ups to expect**
- *How do you tell a plan change from a missing index?* -> Compare the current plan with the earlier one for the same query (Oracle AWR history, or `EXPLAIN` in PostgreSQL). A plan change shows a different plan, while a missing index shows a full scan that was always there but is now hit by more data or traffic.
- *Why not just scale up the server?* -> It buys time but hides a bad query. A 10x inefficient query will exhaust the bigger server too, so find the cause.
- *How do you stop this recurring?* -> A statement timeout, a slow-query alert, query review before release, and keeping heavy reports off the primary.

**60-second answer**
First I confirm that the database itself is at 100% CPU and see who is affected, and I tell stakeholders. Then I look at top SQL, using AWR or `v$sql` on Oracle or `pg_stat_statements` on PostgreSQL, to find the few queries using the CPU. I check for a recent plan change, a missing index, a runaway report, lock waits, or a connection storm. To mitigate, I throttle the caller or pause the report, kill the session if it is safe, send reads to a replica, or add caching. I add an index online only if the database has headroom. After recovery I fix the query or index, write a blameless RCA, and add a slow-query alert and a statement timeout.

### Q10 [senior] Deadlock between two transactions in the database.
tags: deadlock, database, transactions, locking, incident-response, retry, basics

**Start here: the concepts**
- **Transaction:** a group of database statements that succeed or fail together. It exists so money is never taken from one account without being added to another.
- **Lock:** a "reserved" sign the database puts on a row or table while a transaction changes it. Other transactions that want the same row must wait. Locks exist so two people never overwrite each other's work.
- **Deadlock:** Transaction A holds row 1 and waits for row 2. Transaction B holds row 2 and waits for row 1. Neither can ever continue, because each waits for the other.
- **Deadlock detector and victim:** the database notices the cycle and aborts one transaction, the "victim", so the other can proceed. Oracle reports `ORA-00060`, PostgreSQL reports `deadlock detected` (SQLSTATE `40P01`), SQL Server uses error 1205, and MySQL InnoDB uses error 1213.
- **Deadlock trace:** the database's record of the cycle, with the sessions and SQL statements involved. Oracle writes it to a trace file and the alert log, and PostgreSQL writes it to the server log.
- **Foreign key (FK):** a column that points to a row in another table. If the FK column has no index, the database may scan or lock far more than the row you meant, which widens lock footprints.
- **Idempotent:** safe to run twice with the same end result. This matters when retrying.

**The live scenario**
At 10:05 on a sale day, an order service handling about 400 requests/second starts returning HTTP 500 on roughly 3% of checkouts, about 12 failures per second. Latency is normal and CPU is low. A Splunk search for `ORA-00060` shows a spike. Two code paths update the `inventory` and `orders` tables in opposite order. Under light load they rarely collided, but at peak they collide constantly.

**What the interviewer is really checking**
Whether you understand that a deadlock is a lock-ordering problem rather than a "database bug". They also want to see a disciplined sequence: stabilise, read the evidence, fix the root cause, and make the application resilient.

**How I answer it**
1. **Confirm it is a deadlock, not slow blocking.** The database picks a victim and returns an error immediately. Blocking just makes callers wait. The fixes differ, so I check the error code first.
2. **Mitigate first.** Deadlocks resolve themselves, so the damage is failed requests. I add a safe retry, or turn off the newly released feature or batch job if a deploy triggered it. This stops customer impact while I investigate.
3. **Read the deadlock trace.** It shows both statements, the rows they locked and the order. I map each statement to a code path. In Oracle, note that `ORA-00060` rolls back only the failing statement, not the whole transaction, so the application must roll back explicitly.
4. **Fix the lock order.** Every code path must touch tables and rows in the same order, for example always `inventory` before `orders`, and rows sorted by primary key. Then a cycle cannot form, because everyone queues in the same line.
```sql
SELECT * FROM inventory WHERE id IN (7, 3, 9) ORDER BY id FOR UPDATE
```
5. **Shorten transactions.** Locks are held until commit, so do slow work such as HTTP calls, file I/O and heavy computation outside the transaction. A shorter window means fewer collisions.
6. **Index foreign keys.** Without an index the database does more work and may lock more than needed, which enlarges the collision window.
7. **Retry the victim safely.** Retry the whole transaction, not one statement, with a small limit (say 3 attempts), backoff and random jitter. Only retry if the operation is idempotent, or the retry can't double-charge or double-ship.
8. **Blameless RCA.** Write a timeline, the root cause (inconsistent lock order), and actions: a code-review rule, a concurrency test and an alert.

**Trade-offs and what can go wrong**
- Retries hide the problem and add load. Unlimited retries without jitter can cause a retry storm, so fix the ordering as well.
- Ordering locks may need a refactor across services, and the order is hard to enforce across teams.
- Stricter isolation levels or more explicit locking can reduce throughput.
- Lock timeouts are not a fix: they only turn a deadlock into a slow failure.
- Retrying a non-idempotent operation (payment, email) causes duplicates.

**How I'd monitor it**
- Splunk: `index=app ("ORA-00060" OR "deadlock detected") | timechart span=1m count by service`.
- Database views and logs: the Oracle alert log and trace files, or the PostgreSQL log and `pg_stat_database.deadlocks`.
- Application metrics: retry count, retry exhaustion and transaction duration.
- Alert on a deadlock rate above a baseline. Test concurrency before release.

**Follow-ups to expect**
- *How is a deadlock different from a long-running lock wait?* -> A wait ends when the holder commits. A deadlock is a cycle that never ends unless the database kills one transaction.
- *Can you eliminate deadlocks completely?* -> Not guaranteed, but consistent lock ordering and short transactions make them rare, so keep a safe retry as a backstop.
- *What if the cycle involves two different services?* -> Look at the trace for the SQL involved, align ordering through a shared convention, or serialise the work with a queue or a single-owner pattern.

**60-second answer**
A deadlock happens when two transactions each hold a lock the other needs, so neither can proceed. The database detects the cycle and aborts one victim, giving `ORA-00060` in Oracle or `deadlock detected` in PostgreSQL. In an incident I first reduce customer impact with a safe, limited retry, or by rolling back a recent change. Then I read the deadlock trace to see both statements and find the code paths. The real fix is to lock tables and rows in the same order everywhere, keep transactions short, and index foreign keys. I retry the whole transaction with backoff and only if it is idempotent. Finally I run a blameless RCA and add alerts on deadlock counts.

### Q11 [senior] Memory keeps growing slowly for days then the pod restarts.
tags: java, memory-leak, heap-dump, garbage-collection, kubernetes, incident-response, basics

**Start here: the concepts**
- **Heap**: the memory area where Java objects live. The garbage collector (GC) frees objects that nothing references any more.
- **Memory leak (in Java)**: objects that are no longer needed but are still referenced, so GC cannot free them. Memory rises slowly until the process dies.
- **Heap after GC**: heap usage measured right after a full collection. It shows what is truly retained. Raw heap usage rises and falls like a sawtooth, so it hides leaks. A leak shows up as this floor creeping upward.
- **Heap dump**: a snapshot of every object on the heap, taken with `jcmd <pid> GC.heap_dump`. A **class histogram** (`jcmd <pid> GC.class_histogram`) is a lighter version that lists object counts per class. Comparing two snapshots hours apart shows which classes keep growing.
- **Off-heap (native/direct) memory**: memory outside the heap, such as Netty direct buffers, thread stacks and Metaspace. Heap dumps do not show it, but the container limit counts it.
- **OOMKilled**: Kubernetes kills a container that exceeds its memory limit (exit code 137). This differs from a Java `OutOfMemoryError`, which the JVM throws itself.
- **Cardinality**: the number of distinct label combinations on a metric. Each combination is stored in memory, so a label such as `userId` explodes it.
- **ThreadLocal**: a per-thread variable. In a thread pool the threads never die, so values that are never removed stay forever.

**The live scenario**
An order service runs 6 pods with a 2 GB limit. Every 4–5 days, pods restart one after another, with a few failed requests each time. Heap-after-GC was 600 MB on Monday and 1.4 GB by Friday. Nobody noticed because the dashboards showed only the sawtooth. The cause was a static `HashMap` caching customer pricing with no eviction, plus a metric tagged with `orderId`.

**What the interviewer is really checking**
Whether you work from evidence (snapshots, trends) instead of guessing. Also whether you know the leak may be off-heap, and whether you stabilise production before you dig.

**How I answer it**
1. **Confirm what is dying.** Check whether the pod got `OOMKilled` or the app logged `OutOfMemoryError`. This tells you whether the heap or the whole container is the problem.
2. **Mitigate first.** Raise the limit slightly, restart pods on a schedule or by rolling them, and take a pod out of traffic for investigation. This buys time without hiding the bug.
3. **Capture evidence before the pod dies.** Set `-XX:+HeapDumpOnOutOfMemoryError` with a dump path on a persistent volume. Also take a histogram or dump early and again hours later. A dump pauses the JVM, so do it on a pod removed from the load balancer.
4. **Diff the snapshots.** Find the class whose count only grows, then use the dominator tree in a tool such as Eclipse MAT to see what holds it.
5. **Check the usual suspects:**
   - static maps or caches with no eviction
   - unclosed streams or connections
   - listeners or callbacks registered but never removed
   - `ThreadLocal` values never cleared
   - high-cardinality metric labels
   - Hibernate session caches in long loops (the first-level cache grows with every loaded entity, so flush/clear or use a short session)
6. **If the heap looks flat, suspect off-heap.** Netty direct memory is a common cause. Enable Native Memory Tracking (`-XX:NativeMemoryTracking=summary`, then `jcmd <pid> VM.native_memory`) and check Netty's buffer metrics.
7. **Fix and prevent.** Replace the unbounded map with a size-bounded cache (for example Caffeine, with a max size and expiry) and expose its metrics. Alert on the heap-after-GC trend.
8. **Blameless RCA.** Write the timeline, root cause, why monitoring missed it, and the follow-up actions with owners. Keep stakeholders informed during the incident.

**Trade-offs and what can go wrong**
- A bigger heap only delays the crash and makes dumps and GC pauses larger.
- Dumping a live production pod can freeze it, and dumps may contain customer data, so protect them.
- A bounded cache may lower the hit rate and raise database load, so size it from real data.
- Scheduled restarts hide the leak. Treat them as a temporary measure only.
- Setting the heap equal to the container limit leaves no room for off-heap memory, which guarantees OOMKilled.

**How I'd monitor it**
- Heap-after-GC from Micrometer/Actuator (`jvm.memory.used`, GC metrics). Alert when the 24-hour trend rises.
- Container memory against the limit, and restart counts.
- GC logs (`-Xlog:gc`) showing full GCs that reclaim less each time.
- Cache size and eviction metrics.
- Metric series counts.
- Splunk search for `OutOfMemoryError` or `OOMKilled` events.

**Follow-ups to expect**
- *Heap is flat but the pod is OOMKilled. Why?* -> Off-heap growth: direct buffers, thread stacks, Metaspace. Use NMT and leave headroom between `-Xmx` and the container limit.
- *Why compare two dumps instead of one?* -> One dump shows what is big. Two show what is growing, and growth is the leak.
- *How do you stop this recurring?* -> Bounded caches, a cardinality review in code review, a heap-after-GC trend alert, and a soak test before release.

**60-second answer**
First I check whether the pod was OOMKilled or hit a Java OutOfMemoryError, then I stabilise things by rolling restarts or a temporary limit increase. Next I capture class histograms or heap dumps hours apart from a pod taken out of traffic and diff them to find the class that only grows. I check the usual suspects: unbounded static caches, unclosed resources, listeners, ThreadLocals, high-cardinality metric labels and Hibernate sessions in long loops. If the heap is flat, I look at off-heap memory such as Netty direct buffers using Native Memory Tracking. The fix is usually a bounded cache with metrics, and I add an alert on the heap-after-GC trend. Then I run a blameless RCA so the gap in monitoring is closed.

### Q12 [senior] Duplicate records/events in production.
tags: duplicates, idempotency, kafka, outbox-pattern, at-least-once, incident-response, basics

**Start here: the concepts**
- **Duplicate record/event:** the same business fact (one order, one payment) stored or processed more than once.
- **At-least-once delivery:** the messaging system promises a message is never lost, but it may arrive more than once. It resends when unsure whether you got it. This is the Kafka default for consumers.
- **Idempotent operation:** doing it twice has the same effect as doing it once. "Set status = PAID" is idempotent. "Add 100 to balance" is not.
- **Idempotency key:** a unique ID for one business action (for example an order ID or a client-generated request UUID). Storing it lets you recognise and skip a repeat.
- **Unique constraint:** a database rule that rejects a second row with the same key. It is the last line of defence because it holds even when application code has a bug or two threads race.
- **Retry:** automatically repeating a call after a timeout. The first call may have succeeded and only the reply was lost.
- **Rebalance:** when Kafka reassigns partitions among consumers in a group. If a consumer processed messages but had not yet committed its offset (its "read up to here" bookmark), the next owner restarts from the last committed offset and reprocesses them.
- **Dual write:** writing to two systems (database and Kafka) in one code path with no shared transaction. One can succeed while the other fails, and the retry then creates duplicates.
- **Outbox pattern:** write the business row and an "event to send" row in the same database transaction. A separate publisher reads the outbox table and sends to Kafka. This removes the dual write, but the publisher can still resend, so it is at-least-once too.

**The live scenario**
A payments team gets a call from finance: about 1,800 customers (roughly 0.4% of the day's 450,000 orders) were charged or invoiced twice since a 2 pm deploy. Support tickets are climbing. Logs show the order consumer log "Rebalance, revoking partitions" several times an hour because a new slow downstream call pushed processing past `max.poll.interval.ms`. Every rebalance replayed uncommitted messages, and the insert had no uniqueness check.

**What the interviewer is really checking**
Whether you stop the bleeding before theorising, find the actual duplicate source with evidence, and fix it by design (idempotency) instead of "dedupe harder in code". Also whether you clean data safely and lead communication.

**How I answer it**
1. **Detect and size it.** Run a query grouping by business key with `HAVING count(*) > 1`. This gives the number of affected records and the start time, which tells me which change caused it. Reason: scope drives severity and communication.
2. **Mitigate first.** Roll back the deploy or disable the feature flag, or pause the consumer or the retry job. Stop downstream side effects such as emails and payment captures. Reason: duplicates keep growing while you investigate.
3. **Find the source with evidence.** Check each cause:
   - Consumer logs and rebalance events, plus offset commit gaps (rebalance reprocessing).
   - Retry logs and HTTP timeouts followed by repeated calls (retries on non-idempotent calls).
   - Two identical requests milliseconds apart from one user session (UI double-submit).
   - Rows with no matching event, or the reverse (dual write failure).
   Compare timestamps and message offsets or request IDs of the duplicate pair. Identical payload and same offset means replay. Different offsets means the producer sent twice.
4. **Fix at the root.** Make writes idempotent:
   - Add an idempotency key and a unique constraint.
   - Make the consumer insert-or-ignore (upsert) on that key.
   - Send the key with API calls so retries are safe.
   - Disable the UI button after the first click, and also enforce it on the server.
   - Replace the dual write with the outbox pattern.
   ```sql
   ALTER TABLE orders ADD CONSTRAINT uq_order_key UNIQUE (idempotency_key);
   ```
   Reason: delivery guarantees cannot be perfect, so the receiver must tolerate repeats.
5. **Clean up the data once.** Write a script that first runs in dry-run mode and only reports what it would delete or merge. Take a backup first. Keep the oldest or correct row, and have finance review the list. Handle money side effects separately (refunds). Reason: a careless delete turns an incident into data loss.
6. **Blameless RCA and prevention.** Write the timeline, the root cause, and why tests and alerts missed it. Add duplicate-detection checks and a replay test with forced rebalances.
7. **Communicate throughout.** Give support and business a named owner, regular updates, and the affected-customer count.

**Trade-offs and what can go wrong**
- A unique constraint turns silent duplicates into errors. Handle the violation as "already processed", not as a failure that retries forever.
- Idempotency tables need cleanup, and the key must be defined carefully. Too broad a key drops legitimate orders. Too narrow still lets duplicates in.
- The Kafka idempotent producer only stops duplicates from producer retries. Kafka transactions give exactly-once only within Kafka. A database write still needs its own idempotency.
- The outbox adds latency and a publisher to operate.
- Deleting duplicates blindly may remove rows that other tables already reference.

**How I'd monitor it**
- A scheduled duplicate-count query on business keys, with an alert when it is above zero.
- Splunk searches for rebalance messages, unique-constraint violations (expected, but watch the rate), and retry counts by request ID.
- Kafka consumer lag, rebalance frequency and commit failures.
- Outbox backlog size and age.

**Follow-ups to expect**
- *Does Kafka exactly-once solve this?* -> Only for Kafka-to-Kafka processing with transactions. Writes to an external database still need idempotency.
- *How do you reduce rebalance replays?* -> Tune `max.poll.interval.ms` and `max.poll.records`, move slow work off the poll loop, and commit offsets only after processing. Cooperative rebalancing also helps.
- *Why not check "exists?" then insert?* -> Two threads can both see "not found" and both insert. Only a unique constraint is atomic.

**60-second answer**
First I'd size the problem with a group-by query and stop the growth by rolling back or pausing the consumer or retry job. Then I'd find the source from evidence: rebalance logs, retry traces, offsets and request IDs of the duplicate pairs. Usual causes are at-least-once delivery, retries on non-idempotent calls, rebalance reprocessing, UI double-submit and dual writes. The permanent fix is idempotent writes, meaning an idempotency key backed by a unique constraint, plus the outbox pattern instead of writing to the database and Kafka separately. I'd clean existing data with a script that has a dry-run mode, taken after a backup and reviewed by the business. Finally I'd run a blameless RCA and add duplicate-count alerts and rebalance tests, and keep stakeholders updated throughout.

### Q13 [senior] Data inconsistency between two services.
tags: data-consistency, kafka, event-driven, incident-response, idempotency, reconciliation, basics

**Start here: the concepts**
- **Data inconsistency:** two services hold copies of the same fact (e.g. order status) and disagree. It happens because each service has its own database, and no single transaction covers both.
- **Event / event log:** a record that "something happened", stored in an ordered, append-only log such as a Kafka topic. Because the log is kept, you can read it again later.
- **Offset and offset commit:** the offset is a consumer's bookmark in the log. Committing it tells Kafka "I'm done up to here". If you commit before the work is finished and then crash, that message is never processed again. It is silently lost.
- **Dead-letter topic (DLT):** where messages that keep failing are parked so they don't block the queue. If nobody watches it, parked messages are effectively lost.
- **Out-of-order events:** with retries, multiple partitions or multiple producers, "cancelled" can arrive before "created". Applying them in arrival order leaves the wrong final state.
- **Version / sequence number:** a counter on each entity's events. The consumer ignores any event older than what it has already applied.
- **Compensation (saga):** an "undo" step (e.g. refund) when a later step of a multi-service workflow fails. If the undo itself fails, the services stay split.
- **Reconciliation job:** a scheduled comparison of both services' data that reports or fixes differences ("drift").
- **Idempotent:** processing the same message twice gives the same result as once. This makes replay safe.

**The live scenario**
Friday 16:00: support reports 340 customers charged for orders that Order Service shows as "CANCELLED". About 0.2% of the roughly 170k orders that day are affected. Payment Service says PAID and Order Service says CANCELLED. Finance is worried about refunds and chargebacks.

**What the interviewer is really checking**
Whether you contain the damage first, then find the exact first point where the two services diverged using evidence, and whether you fix the cause, not just the rows, and add detection so drift is caught early next time.

**How I answer it**
1. **Contain and communicate.** Pause the process creating more bad data (feature flag, stop the faulty consumer, or roll back the last release). Open an incident channel, name an owner, and give stakeholders a timeline and an update cadence. Stopping the bleeding comes before explaining it.
2. **Decide the source of truth.** For payments, the payment provider's record usually wins. Without this, you can't tell which side is "wrong".
3. **Pick one affected entity and find the first divergence.** Follow its ID through the event log and both services' logs, in time order, to the first step where they disagree. A search such as `index=prod orderId=123 | sort _time` in Splunk gives the timeline. Starting from one case is faster than comparing everything.
4. **Check the usual causes, in order:**
   - **Lost events:** was the offset committed before processing finished? Was the message sitting unread in the DLT?
   - **Out-of-order events:** did an older event overwrite a newer one? The fix is a version/sequence check on write.
   - **Failed compensations:** did a refund or undo step fail with no retry or alert?
5. **Fix the cause.** Commit offsets after successful processing, make handlers idempotent, alert on DLT depth, and add version checks. If the root cause is writing to the database and publishing an event as two separate steps, use the outbox pattern (write the event in the same database transaction, publish it afterwards).
6. **Repair the data.** Replay the affected events from the log through the now-idempotent consumer, or apply a reviewed correction script. Check that the log's retention still covers the incident window.
7. **Prevent recurrence.** Run a blameless RCA (focus on what the system allowed, not who erred), and add a nightly reconciliation job with an alert when drift crosses a threshold.

**Trade-offs and what can go wrong**
- Replay without idempotency creates duplicate charges or refunds.
- Kafka retention may have already deleted the events you need. Then you must rebuild from the databases or the payment provider.
- Committing after processing gives at-least-once delivery, so duplicates become possible. That is why idempotency is required.
- Reconciliation adds load and only detects problems after the fact. Auto-fixing can hide a real bug, so report first.
- Blaming one team in the RCA stops people sharing facts.

**How I'd monitor it**
- Consumer lag per group, and DLT message count with an alert above zero.
- A reconciliation drift metric (mismatched records per night) with a threshold alert.
- Splunk searches for handler errors, "stale version ignored" logs and failed compensation messages.
- Actuator and APM error rates on the consumers.
- The count of unresolved cases after the repair.

**Follow-ups to expect**
- *How do you stop old events overwriting new ones?* -> Store a version per entity and apply an event only if its version is higher. Ordering by the entity key within one partition also helps.
- *Why not a distributed transaction (2PC) across both services?* -> It couples availability and scales poorly. Prefer the outbox pattern, idempotent consumers and sagas with compensation, plus reconciliation as a safety net.
- *How do you replay safely?* -> Use idempotent handlers, replay in a controlled batch, test on a copy first, and watch for duplicates.

**60-second answer**
First I'd contain it: pause the faulty consumer or roll back the release, open an incident channel and keep stakeholders updated. Then I'd agree which service is the source of truth. I'd take one affected order and follow it through the event log and Splunk to find the first point where the services diverged. The usual causes are lost events, such as an offset committed before processing or a dead-letter topic nobody watched, out-of-order events, and failed compensations. I'd fix the cause with commit-after-processing, idempotent handlers, version checks and the outbox pattern. Then I'd repair the data by replaying from the log, checking retention first. Afterwards I'd run a blameless RCA and add a reconciliation job with drift and DLT alerts.

### Q14 [senior] An expired certificate / secret rotation caused an outage - how do you prevent it?
tags: certificates, tls, secret-rotation, cert-manager, incident-prevention, monitoring, basics

**Start here: the concepts**
- **TLS certificate:** a file that proves a server's identity and enables encrypted connections. It has a built-in expiry date, so clients refuse to connect once it passes. This limits the damage if a certificate is stolen.
- **Secret:** any credential an app needs, such as an API key, database password or token. Secrets are rotated (replaced) regularly to limit damage if one leaks.
- **Rotation:** swapping an old certificate or secret for a new one. An outage happens when the swap is forgotten, or when the two sides don't switch at the same moment.
- **Dual-valid keys:** for a window of time, both the old and the new credential are accepted. Clients and servers can then move over at different times without failing.
- **cert-manager / ACM:** tools that request and renew certificates automatically. cert-manager does this inside Kubernetes. ACM is AWS Certificate Manager. It renews certificates it issued for AWS services, but a certificate you imported yourself is not auto-renewed.
- **Central secret store:** one managed place (for example Vault or a cloud secrets manager) that holds secrets, controls access and gives you one place to rotate them. Without it, secrets sit scattered in config files and nobody knows where they all are.
- **Reload without restart:** the app re-reads a new certificate or secret while running, so rotation needs no redeploy.

**The live scenario**
At 02:10 on a Saturday, the payment gateway's TLS certificate expired. Within minutes, 100% of checkout calls (about 800 requests/second) failed with handshake errors, and the error rate alert fired. The renewal was a manual task owned by an engineer who had left. The fix took 90 minutes: issue a new certificate, install it, and restart the pods. The same quarter, an API key rotation broke a partner integration because the old key was cancelled before the partner switched.

**What the interviewer is really checking**
Whether you treat expiry as a predictable, preventable event and design for it. A senior answer combines automation, early warning, safe rollout and ownership, not just "set a calendar reminder".

**How I answer it**
1. **Inventory everything that expires.** List the certificates (public, internal, client, intermediate CAs), API keys and passwords, with an owner for each. You cannot protect what you haven't listed, and forgotten internal certificates are the usual culprits.
2. **Store secrets centrally.** Put them in one secret store with access control and audit logs. Rotation then happens in one place instead of across many config files.
3. **Automate renewal.** Use cert-manager or ACM so no human has to remember. Humans forget, and renewal runs on a schedule. Check what the tool really covers, such as imported ACM certificates.
4. **Alert on expiry anyway, at 30/14/7 days.** Automation can fail silently, for example when a DNS validation breaks. Several alerts at decreasing distances give time to react, and the 7-day alert should page someone. Check the certificate the server actually serves, not just the inventory:
   `openssl s_client -connect host:443 | openssl x509 -noout -enddate`
5. **Support dual-valid keys during rotation.** Accept old and new credentials together. Roll out the new one to all clients, confirm the old one is unused, then retire it. This avoids the partner-key outage above.
6. **Make apps reload without restart.** Renewal is useless if the running JVM keeps the old certificate in memory. Use reloadable keystores or a refreshed secret source, so rotation is a non-event.
7. **Rehearse in staging.** Do a real rotation, including an early expiry, to find hardcoded secrets or apps that cache them. Better to find these on a Tuesday than at 02:10 on a Saturday.
8. **Run a blameless review after any miss.** Fix the process gap (no owner, no alert), not the person.

**Trade-offs and what can go wrong**
- Automation adds a dependency. If the renewal tool breaks, you need the alerts from step 4 as a backstop.
- Dual-valid keys widen the attack window, so set a firm end date for the old credential.
- Short certificate lifetimes improve security but make any broken automation visible sooner.
- Common misses: intermediate CA expiry, truststores on clients, certificates pinned in mobile apps, and alerts sent to a mailbox nobody reads.

**How I'd monitor it**
- A dashboard of days-to-expiry for all certificates, probed from outside (a synthetic check against the live endpoint).
- Alerts at 30/14/7 days, with the 7-day one paging the owner.
- Splunk searches for `SSLHandshakeException`, `certificate expired` and `401` spikes after a rotation.
- Renewal job failure alerts from cert-manager or ACM.

**Follow-ups to expect**
- *Why not just rely on auto-renewal?* -> It can fail silently, and a running app may not pick up the new certificate, so you still need expiry alerts and reload support.
- *How do you rotate an API key shared with a partner without downtime?* -> Issue the new key, accept both, let the partner switch, watch the old key's usage drop to zero, then revoke it.
- *What would you do if a certificate expires right now?* -> Mitigate first: issue or install a new certificate and reload or restart, then communicate status, then do the review.

**60-second answer**
Certificate expiry is predictable, so it should never cause an outage. I first inventory every certificate and secret with an owner, and keep secrets in a central store. I automate renewal with cert-manager or ACM, but still alert at 30, 14 and 7 days, because automation can fail silently. During rotation I accept both old and new credentials for a while, so clients move over safely, then I retire the old one. I make applications reload certificates without a restart, and I rehearse rotation in staging. After any miss I run a blameless review and fix the process gap.

### Q15 [senior] How do you debug something that only fails in production?
tags: production-debugging, observability, actuator, structured-logging, feature-flags, canary, basics

**Start here: the concepts**
- **Works in staging, fails in production:** Production differs from staging in data, traffic, config, dependencies and timing. The bug usually lives in one of those differences, not in the code alone.
- **Structured logging:** Each log line is key-value data (JSON) such as `orderId`, `customerTier`, `traceId`. Tools like Splunk can filter and count on those fields, instead of someone grepping free text.
- **Trace attributes / trace ID:** A trace ID is one ID that follows a request across all services. Attributes are extra tags on it, such as region or feature flag state. Together they show where one failing request went.
- **Dynamic log level (Actuator loggers):** Spring Boot Actuator has a `loggers` endpoint that changes a logger's level (e.g. to DEBUG) on a running app, with no restart. A restart would often hide the bug and lose in-memory state.
- **Masking:** Replacing sensitive values (card numbers, emails, tokens) with `****` before logging, so debugging does not create a data breach.
- **Feature flag:** A runtime switch that turns code on or off without deploying.
- **Canary:** Sending a small share of traffic (say 5%) to the new version first, so a bad fix harms few users.
- **Traffic replay / shadowing:** Copying real requests to a test copy of the service. Its responses are discarded, so real users are unaffected.
- **Regression test:** An automated test that fails on the bug and passes after the fix, so the bug cannot return unnoticed.

**The live scenario**
At 10:05, about 2% of 4,000 requests/min to the checkout service return HTTP 500. That is roughly 80 failed orders a minute. Staging is clean. The errors cluster on customers with very large carts, and staging test carts hold at most 10 items. We cannot attach a debugger to production, because a breakpoint would freeze live traffic.

**What the interviewer is really checking**
Whether you work methodically and safely: stop the damage first, gather evidence without making things worse, and protect customer data. Guessing, or redeploying code to "see what happens", is the weak answer.

**How I answer it**
1. **Mitigate first.** Roll back the last release, turn off a feature flag, or scale out. Users come before curiosity. Then keep a copy of the evidence, because a rollback can erase the symptom.
2. **Read what already exists.** Check Splunk for the error, e.g. `index=prod service=checkout level=ERROR | stats count by exception, host`. Look at APM traces and dashboards. Find *when* it started and what changed (deploy, config, data).
3. **Compare production with staging.** Check config values, environment variables, library versions, data volume and shape, and dependency behaviour. Here the difference was cart size. Most "only in prod" bugs are found at this step.
4. **Add targeted visibility.** Raise the log level for *one* package at runtime through Actuator, and add structured fields and trace attributes (`cartSize`, `traceId`):
   `POST /actuator/loggers/com.shop.checkout  {"configuredLevel":"DEBUG"}`
   Keep it narrow, on a single instance if possible, and set it back afterwards. Secure the endpoint.
5. **Capture the failing payload safely.** Log only failing requests, with sensitive fields masked, and keep it only as long as needed. This gives you real input to reproduce with.
6. **Reproduce.** Try the captured input in a lower environment, or replay or shadow real traffic against a test copy. Replay only against copies with side effects disabled (no real emails or payments). As soon as it reproduces, write the regression test.
7. **Ship the fix gradually.** Put it behind a feature flag and canary it to a small share of traffic. Watch the error rate, then ramp up.
8. **Close out.** Hold a blameless RCA, with a timeline, root cause and action items such as "add large-cart test data to staging". Update stakeholders throughout.

**Trade-offs and what can go wrong**
- DEBUG logging on a busy service can flood disks and Splunk licence and slow the app. Keep it scoped and time-boxed.
- Logging raw payloads can leak personal data, so mask and restrict access.
- Exposing Actuator without authentication is a security hole.
- Replay can trigger real side effects (double charges) if not isolated.
- A restart "to fix it" destroys evidence. Capture thread dumps (`jcmd <pid> Thread.print`), heap histograms (`jcmd <pid> GC.class_histogram`) and GC logs *before* restarting if you suspect a hang or memory problem.

**How I'd monitor it**
- Error rate and latency (p95/p99) per version during the canary.
- Splunk searches by `traceId` and error type, plus alerts on error spikes.
- Log volume, to catch runaway DEBUG.
- Whether the regression test runs in CI.

**Follow-ups to expect**
- *Why not attach a remote debugger?* -> A breakpoint pauses threads and hurts live users. It also exposes a debug port. Use logs, traces and dumps instead.
- *What if it's intermittent and you can't reproduce it?* -> Add trace attributes, find what the failing requests share, and use replay or a canary with extra logging until a pattern appears.
- *How do you avoid leaking data while debugging?* -> Mask at the logging layer, log only failures, limit retention and access, and follow the data policy.

**60-second answer**
First I stop the damage with a rollback, a feature flag or scaling, and I keep the evidence. Then I read what already exists: Splunk logs, traces and metrics, to learn when it started and what changed. I compare production with staging on config, data volume and dependencies, since the cause is usually a difference there. If I need more detail, I raise the log level for one package through Actuator, add structured fields and trace attributes, and capture failing payloads with sensitive data masked. I reproduce the bug, possibly by replaying traffic against an isolated copy, and I write a regression test straight away. I ship the fix behind a flag with a canary, watch the error rate, and finish with a blameless RCA and prevention actions.

### Q16 [mid] How do you reduce Mean Time To Detect and Mean Time To Recover?
tags: mttd, mttr, incident-response, slo, observability, rollback, on-call, basics

**Start here: the concepts**
- **MTTD (Mean Time To Detect):** the average time from when a problem starts to when your team knows about it. Customers hurt during that gap.
- **MTTR (Mean Time To Recover):** the average time from detection until users are back to normal. "R" is sometimes read as Repair, Respond or Resolve, so say which one you mean. Recovery means *restoring service*, not finding the root cause.
- **SLI / SLO:** an SLI is a measurement of user experience, such as "percentage of checkout requests that succeed". An SLO is the target, such as 99.9% over 30 days. Alerting on the SLO means paging people only when users are actually affected.
- **Error budget and burn rate:** the budget is the failure the SLO allows (0.1%). Burn rate is how fast you are spending it. A fast burn pages someone immediately; a slow burn creates a ticket.
- **Synthetic check:** a script that acts like a user (for example, log in and add to cart) every minute. It catches outages even when no real traffic is arriving.
- **Dashboard and deploy marker:** a dashboard shows key graphs together. A deploy marker is a vertical line on the graph showing when a release happened, so "it broke right after the deploy" is obvious.
- **Rollback / feature flag:** a rollback redeploys the previous version. A feature flag is a runtime switch that turns a new feature off without redeploying.
- **Runbook:** a step-by-step page for a known alert. It lets a tired engineer at 3 a.m. act without guessing.
- **Failover:** switching to a standby (replica database, second region) when the primary fails.
- **On-call rota and escalation:** a schedule of who is responsible now, and who gets called next if they do not respond.
- **Game day / chaos drill:** a planned practice where you break something on purpose (kill a node, fail a dependency) to test people and procedures.
- **Immutable infrastructure:** servers or containers are never patched by hand. You replace them with a new, versioned image, so what runs is always known and repeatable.

**The live scenario**
Checkout handles about 2,000 requests/second. A release at 14:00 leaks database connections. By 14:10 about 5% of checkouts fail. Nobody is paged because the only alert is "CPU above 90%". Support tickets arrive at 14:25, so MTTD is 25 minutes. The team then argues in chat about the cause, and the rollback finishes at 15:10, so recovery takes 45 minutes. After the RCA they add an error-rate SLO burn-rate alert, a deploy marker, a one-command rollback and a runbook. The next bad release pages on-call within 3 minutes, and rollback completes in 5.

**What the interviewer is really checking**
That you treat detection and recovery as separate problems, that you mitigate before you diagnose, and that you build the habits and tooling in advance instead of improvising during an incident.

**How I answer it**
1. **Alert on user impact (SLO burn rate), not just machine metrics.** CPU can be high with no harm, or normal while users fail. Symptom-based alerts fire on what customers feel.
2. **Add synthetic checks.** They find outages in quiet hours and in flows with little traffic.
3. **Build dashboards with deploy markers.** Most incidents follow a change, so showing releases on the graphs shortens triage.
4. **Make errors searchable.** Log the app version in every event so one query exposes the culprit: `index=prod service=checkout level=ERROR | timechart span=1m count by app_version`
5. **Mitigate first, diagnose second.** Roll back, flip the feature flag, scale out or fail over to restore service. Then take thread dumps (jstack/jcmd), heap histograms and GC logs to find the cause. Fast mitigation is the biggest MTTR lever.
6. **Make rollback one click and safe.** Use immutable, versioned artifacts. Keep database migrations backward compatible, or the old version cannot run against the new schema.
7. **Write runbooks and test failover.** An untested failover is only a hope.
8. **Set clear on-call and escalation.** Define who is the incident commander, how long before escalating, and who updates stakeholders. Unclear ownership wastes more minutes than technical work does.
9. **Practise with game days and chaos drills, then run blameless RCAs.** Turn each incident into a new alert, runbook or automation.

**Trade-offs and what can go wrong**
- Too many alerts cause alert fatigue, and people start ignoring pages. Page only on user impact and send everything else to tickets.
- Rollback fails if a migration or data change is not reversible. Use expand-then-contract migrations.
- Feature flags left in the code add complexity, so remove them once a feature is stable.
- Chaos drills in production without guardrails can cause real outages. Start in staging, then limit the blast radius.
- Averages hide bad cases, so also track percentiles (p90) of detect and recover times.

**How I'd monitor it**
Record timestamps for every incident: start, detected, mitigated, resolved. Track MTTD and MTTR per quarter. Also track the share of incidents found by alerts rather than by customers, the number of pages per shift, rollback duration, and runbook coverage for alerts. Use Actuator health and metrics endpoints, APM and Splunk alerts as the signal sources.

**Follow-ups to expect**
- *Why not alert on CPU and memory?* -> They are causes, not user impact. Use them for diagnosis and capacity, and page on SLO burn.
- *Rollback or fix forward?* -> Roll back by default because it is predictable. Fix forward only when rollback is unsafe, such as after an irreversible data change.
- *What is the difference between MTTR and RCA?* -> MTTR measures how fast service is restored. The RCA happens afterwards, blamelessly, to stop recurrence.

**60-second answer**
I treat detection and recovery separately. For detection, I alert on user impact using SLO burn rates, add synthetic checks, and build dashboards with deploy markers so I can see which release caused the change. For recovery, I mitigate first, with one-click rollback, feature flags, or a tested failover, and diagnose afterwards with thread dumps, GC logs and Splunk. Runbooks and a clear on-call and escalation path remove the guesswork, and immutable infrastructure makes rollbacks reliable. I keep this sharp with game days and blameless RCAs that turn every incident into a new alert or automation. I measure progress by tracking MTTD and MTTR per incident.

### Q17 [architect] Design a blameless post-incident process for a team of 20.
tags: incident-management, blameless-postmortem, rca, on-call, severity, observability, basics

**Start here: the concepts**
- **Incident:** an unplanned event that hurts users or the business, such as an outage, data errors or severe slowness.
- **Blameless:** the review asks "what in our system, tooling or process allowed this?" and not "who made the mistake?". People hide facts when they fear punishment, and hidden facts mean the real cause is never found.
- **Severity (SEV) levels:** agreed labels such as SEV1 (full outage or data loss), SEV2 (major feature degraded) and SEV3 (minor). They decide who is paged, how fast we respond and how often we update stakeholders.
- **Incident commander (IC):** one person who coordinates the response and makes decisions. The IC does not debug. Without one, ten engineers debug the same thing and nobody decides.
- **Comms lead:** the person who updates stakeholders and customers, so engineers can keep working.
- **Scribe and timeline:** a running log of "time, what we saw, what we did". Memory is unreliable after a stressful night, so we record it live.
- **Post-incident review (PIR):** a meeting after the incident to learn from it.
- **RCA (root cause analysis):** finding why it happened. Real incidents usually have several contributing factors, not one root cause.
- **Action item:** a concrete follow-up task with an owner and due date.

**The live scenario**
At 02:10 a bad config change took our payments API from 40 ms to timeouts. About 30% of 5,000 requests per minute failed for 47 minutes. Nobody owned the response. Five people joined the call, two rolled back different things, and the VP got no update for 30 minutes. The next week, the engineer who deployed the change was quietly blamed. Three months later a similar config change caused another outage, because nothing had been fixed except "be more careful".

**What the interviewer is really checking**
Whether you can build a repeatable system that turns incidents into lasting fixes, with clear roles and a culture where people report honestly, and one that scales beyond heroics.

**How I answer it**
1. **Define severity levels first.** Each level has clear criteria, response times and a paging rule. Reason: people argue less during an outage, and small issues don't wake the whole team.
2. **Assign roles for every SEV1 and SEV2:** an incident commander, a comms lead, and a scribe or ops lead. Rotate the roles among the 20 people, with training and shadowing. Reason: roles remove confusion, and rotation avoids dependence on a few heroes.
3. **Mitigate first, diagnose second.** Roll back, scale out or flip a feature flag before hunting for causes. Reason: user impact ends sooner, and evidence such as thread dumps, heap dumps and Splunk logs can be captured as we go.
4. **Start the timeline document during the incident,** not afterwards. Reason: timestamps are accurate and the review has facts to work from.
5. **Hold the PIR within 3-5 working days.** That is early enough for fresh memory and late enough for people to rest. Reason: waiting longer loses detail and momentum.
6. **Use an RCA template:** impact, timeline, detection, contributing factors (the "five whys" is one technique), what went well, what went badly, and where we got lucky. Frame everything around systems ("the pipeline allowed an unvalidated config") and never "X broke it". Reason: this keeps the review blameless and finds several causes.
7. **Track action items in the normal backlog,** each with one owner and a due date, and mark which ones prevent recurrence and which only improve detection. Reason: items in a separate document get forgotten.
8. **Hold a monthly review of repeat causes** with engineering leads. Reason: patterns across incidents, such as config changes or missing alerts, point to systemic investment.
9. **Publish every review in a searchable archive** with tags for service, cause and severity. Reason: new joiners and future on-call engineers can find past fixes.

**Trade-offs and what can go wrong**
- Too much process for small incidents causes fatigue. Do full reviews only for SEV1 and SEV2, and keep a short form for SEV3.
- "Blameless" does not mean "no accountability". Owners still deliver action items, but nobody is punished for honest mistakes.
- Typical failures are reviews that end in "human error" with no system fix, action items nobody finishes, and leadership using review content for performance ratings.
- A single root cause is often a simplification. Look for the contributing factors.

**How I'd monitor it**
- Process metrics: MTTD (mean time to detect), MTTR (mean time to recover), incident count by severity, and repeat-incident rate.
- Percentage of PIRs held within 5 working days, and action-item completion rate and age of overdue items.
- Whether detection came from alerts or from customers. The latter means our monitoring has a gap.
- Evidence tools used during incidents: Splunk searches, Actuator health endpoints, GC logs, jstack/jcmd output. Link them in the timeline.

**Follow-ups to expect**
- *How do you keep it blameless when someone clearly erred?* -> Ask why the system let one person's error cause an outage, and add guardrails such as validation, review or canary deploys.
- *How do you make sure action items get done?* -> Put them in the sprint backlog with an owner and due date, and review overdue ones monthly.
- *How do you decide the severity?* -> Use predefined criteria, mainly user impact and data risk. Anyone may raise it, and the IC can downgrade it later.

**60-second answer**
I'd start with clear severity levels, so everyone knows when to escalate. In a serious incident we assign an incident commander, a comms lead and a scribe, and we mitigate first, with a rollback or feature flag, before diagnosing. The timeline is written during the incident. Within three to five working days we run a blameless review with an RCA template that lists contributing factors and focuses on systems, not people. Action items go into the normal backlog with an owner and due date. Once a month we review repeat causes to find systemic problems, and every review goes into a searchable archive. I'd track MTTD, MTTR, repeat incidents and action-item completion to show the process works.

### Q18 [architect] Design a runbook for "orders API p95 latency > 2 s".
tags: incident-response, runbook, latency, observability, kubernetes, jcmd, splunk, basics

**Start here: the concepts**
- **p95 latency:** 95% of requests finish faster than this number, and 5% are slower. "p95 > 2 s" means at least 1 in 20 users waits over 2 seconds. Averages hide this, so we alert on percentiles.
- **Runbook:** a short written procedure that an on-call engineer follows at 3 a.m. It exists so that diagnosis does not depend on who happens to be awake.
- **Mitigate vs. fix:** mitigation stops the user pain quickly (rollback, scale out, switch something off). The fix removes the root cause and usually comes later.
- **Decision tree:** an ordered list of questions, each pointing to an action. It stops people guessing.
- **Circuit breaker:** a wrapper around a downstream call. After too many failures or timeouts it stops calling for a while and returns a fallback (cached or default data). This keeps one slow dependency from tying up all your threads.
- **Rate limiting:** rejecting or delaying excess requests to protect the service.
- **Thread dump / heap histogram / GC log:** a thread dump (`jcmd <pid> Thread.print`) shows what every thread is doing now. A heap histogram (`jcmd <pid> GC.class_histogram`) counts objects by class. A GC log shows how long garbage-collection pauses take.

**The live scenario**
At 10:02 an alert fires: orders API p95 has been above 2 s for 5 minutes (normally 300 ms) at about 1,200 requests/s. Checkout conversion is dropping. A release went out at 09:55. The on-call engineer opens the runbook, sees the error rate is flat but latency is rising, finds the deploy marker on the dashboard, and rolls back. Latency recovers in 3 minutes. The RCA later finds that the new release added a query without an index.

**What the interviewer is really checking**
Whether you can turn firefighting into a repeatable, ordered process. That means impact first, cheap and reversible actions before deep analysis, and a clear definition of "done".

**How I answer it**
1. **Trigger and impact check.** The alert should fire only if the condition holds for a window (for example 5 minutes), so it does not flap. Then ask who is affected: which endpoints, which regions, what share of traffic, and whether errors are rising too. This sets severity and decides whether to open an incident channel and notify stakeholders.
2. **Dashboard links.** Put direct links in the runbook: latency by endpoint, traffic, error rate, CPU, GC pauses, DB metrics, downstream call timings, and deploy markers. Nobody should hunt for them during an incident.
3. **Decision tree, cheapest and most likely first:**
   - *Recent deploy or config change?* Roll back (`kubectl rollout undo deployment/orders`). It is fast and reversible, and you diagnose afterwards.
   - *Database slow?* Look at top SQL, locks and connection-pool waits. Limit or kill the offending query, or disable the feature that issues it. Scaling the API does not help here and can add load to the DB.
   - *Downstream service slow?* Check the circuit breaker, timeouts and fallback. Open the breaker or enable the fallback.
   - *CPU or GC problem?* Scale out to relieve pressure. Before restarting a pod, capture evidence with `jcmd <pid> Thread.print` and `jcmd <pid> GC.heap_dump`, then do heap analysis offline.
   - *Traffic spike?* Apply rate limits or scale out, but only if the bottleneck is not a shared dependency.
4. **Commands section:** `kubectl get pods`, `kubectl top pods`, `kubectl scale`, `kubectl rollout undo`, and the `jcmd` commands above. Copy-paste ready.
5. **Escalation contacts:** a named owner for the DB, the platform, and each downstream team, plus an incident commander and a rule for when to escalate (for example, no improvement after 15 minutes).
6. **Verification and closure:** confirm p95 is below threshold for a sustained period (for example 30 minutes), the error rate is normal, and user-facing checks pass. Then announce resolution, record the timeline, and schedule a blameless RCA.

**Trade-offs and what can go wrong**
- Rollback may be unsafe if a database migration is not backward compatible. The runbook should say so.
- Scaling out a slow DB or downstream makes things worse.
- Restarting a pod destroys the evidence, so capture dumps first.
- Stale runbooks are dangerous. Test them in game days and update them after each incident.
- Too many branches make a runbook unusable, so keep it short and link to deeper guides.

**How I'd monitor it**
- Alert on p95 and p99 per endpoint over a time window.
- Track DB pool wait time, slow-query counts, circuit-breaker state, GC pause time, CPU and the pod restart count.
- Splunk: search the orders service logs for slow-request entries and group by endpoint or downstream. Correlate with deploy events.
- Measure time-to-detect and time-to-mitigate per incident.

**Follow-ups to expect**
- *Why roll back before diagnosing?* -> It is the cheapest reversible step, and it restores users while evidence is preserved in logs and dumps.
- *How do you avoid alert fatigue?* -> Use a duration window, percentile thresholds based on SLOs, and alert on user impact rather than on every cause.
- *What goes in the RCA?* -> Timeline, root cause, why detection or mitigation was slow, and owned action items. The tone is blameless.

**60-second answer**
I'd start the runbook with an impact check: which endpoints and users are affected, and how severe it is. Then I'd link the dashboards and follow an ordered decision tree. A recent deploy means rollback. A slow database means checking top SQL and limiting or killing the offender. A slow downstream means the circuit breaker and fallback. CPU or GC trouble means scaling out and taking thread and heap dumps with jcmd before restarting. A traffic spike means rate limiting or scaling, but only if the bottleneck isn't shared. The runbook also lists ready commands, escalation contacts and a closing rule: p95 stays below threshold for a sustained period. Afterwards we run a blameless RCA and update the runbook.

### Q19 [mid] Tell me about a production issue you solved (template).
tags: production-incident, troubleshooting, rca, thread-dump, splunk, incident-response, basics

**Start here: the concepts**
- **Production incident**: something broken or badly degraded for real users right now. Incidents exist as a named process so that people act in order instead of panicking.
- **Detection**: how you learn about the problem. The best way is an automated alert on error rate or latency. The worst way is a customer phone call.
- **Mitigation**: making the pain stop before you know why it happened. Examples are rolling back the release, adding servers, or switching off a feature with a **feature flag** (a config switch that disables a code path without a deploy).
- **Thread dump**: a snapshot of what every thread in a JVM is doing, taken with `jstack` or `jcmd`. Many threads stuck on the same line show you where the system is blocked.
- **Heap dump / histogram**: a snapshot of objects in memory. Use it for memory leaks and `OutOfMemoryError`.
- **GC logs**: records of garbage-collection pauses. Long or frequent pauses freeze the application.
- **Splunk / APM**: Splunk searches centralised logs. APM (application performance monitoring) tools show slow requests and dependencies.
- **Root cause**: the precise underlying reason, not the symptom. "The server was slow" is a symptom.
- **Blameless RCA**: a written root-cause analysis that asks "what in our system allowed this?" instead of "who did it?". This makes people honest, so you learn more.

**The live scenario**
Illustrative numbers: a Spring Boot REST service handles about 800 requests per second. Twenty minutes after a release, the error rate jumps from 0.1% to 12% and p99 latency (the slowest 1% of requests) goes from 300 ms to 9 s. An alert fires. We roll back and service recovers in about 12 minutes. In a staging copy we take thread dumps, and 180 of 200 request threads are waiting for a database connection. The new code opened a transaction, then called a slow external HTTP service while holding the connection. The pool ran dry.

**What the interviewer is really checking**
Whether you have really owned an incident: you stabilised first, used evidence rather than guesses, found a precise cause, and left the system safer. They also want to hear how you communicated.

**How I answer it**
1. **Situation**: name the system, users affected and scale in one or two sentences. This gives the listener context for everything else.
2. **Detection**: say how it was found (alert or customer). If a customer found it first, say what monitoring you added afterwards.
3. **Mitigation first**: say what you did to stop the impact (rollback, scale, flag) and how long it took. Stopping the damage comes before understanding it.
4. **Investigation**: give 3-4 concrete steps with tools. For example: check the Splunk error pattern and timeline, correlate with the deploy time, take thread dumps, then read the dump.
   ```
   jcmd <pid> Thread.print > td1.txt   # repeat 10s later to compare
   ```
   Take two dumps so you can tell threads that are stuck from threads that are just busy.
5. **Root cause**: state it precisely and mechanically, like the scenario's "connection held during a slow remote call".
6. **Fix and prevention**: cover four things. Code: move the call outside the transaction and add timeouts. Alert: pool wait time and active connections. Test: a load test or regression test that reproduces it. Process: a review checklist item, plus a blameless RCA document.
7. **Result**: give numbers such as minutes of impact, errors avoided, and that it never recurred.
8. **Use your own story**: pick a real case from your Cvent, CBOS or Sambasafety work. Never memorise an invented one, because follow-up questions will expose it.

**Trade-offs and what can go wrong**
- Rollback is fast but loses the evidence. Capture dumps and logs first, or reproduce in staging.
- Do not blame a person in the story.
- Do not claim a root cause you cannot prove with evidence.
- Do not skip prevention. A fix without an alert or test is only half done.
- Do not inflate your role. Say what you personally did versus what the team did.

**How I'd monitor it**
Alert on error rate, p99 latency and connection-pool metrics (active and pending connections, exposed through Spring Boot Actuator). Add JVM metrics for GC pause and heap. Keep a saved Splunk search for the error signature, and a deploy marker on dashboards so you can see "it broke right after release X".

**Follow-ups to expect**
- *Why mitigate before diagnosing?* -> Every minute costs users and money. Rollback is reversible and diagnosis can continue on a copy.
- *How did you know it was the root cause?* -> The thread dumps showed the blocking line, the timing matched the deploy, and the fix removed the symptom in a load test.
- *What is a blameless RCA?* -> A written timeline, cause and action items that focuses on system gaps, not individuals.

**60-second answer**
"I'll describe an incident on our REST service. After a release, errors rose from 0.1% to 12% and an alert fired. We rolled back first, so impact lasted about 12 minutes. Then I looked at the Splunk error pattern, matched it to the deploy time, and took thread dumps. Most threads were waiting for a database connection, because new code held one while calling a slow external service. I moved that call outside the transaction, added timeouts, set an alert on pool wait time, added a load test, and wrote a blameless RCA. It has not recurred."

### Q20 [mid] What is a good logging practice during incidents?
tags: logging, incident-response, correlation-id, observability, spring-boot-actuator, splunk, basics

**Start here: the concepts**
- **Log line:** a text record that the application writes when something happens. During an incident, logs are often the only record of what the system did.
- **Correlation id:** a unique id (for example a UUID) created when a request first enters the system and attached to every log line that request causes. It exists because one user action passes through many services and threads, and the lines are interleaved with thousands of others. Searching for the id gives you that one request's story.
- **MDC (Mapped Diagnostic Context):** a per-thread key/value store in SLF4J/Logback. You put the id in once and the log pattern prints it on every line automatically.
- **Log level:** the importance label of a line: ERROR, WARN, INFO, DEBUG, TRACE. Levels let you keep normal output small and turn on detail only when needed.
- **Business identifiers:** values such as orderId or customerId, and for Kafka the topic, partition and offset (the message's position in a partition). They let you find the exact record that failed.
- **Tight loop:** code that runs very many times per second. A log line inside it can produce millions of lines.
- **Swallowing an exception:** catching it and neither handling it nor rethrowing it. The failure vanishes from the record.

**The live scenario**
An order service handles about 2,000 requests per second. At 10:05, 3% of payments fail. The logs show "Payment failed" with no order id, and the same error is also logged at each of 3 layers, so 1 failure produces about 3 lines. Elsewhere, a `catch (Exception e) {}` hides a timeout. A debug line inside a per-item loop writes about 5 million lines in a few minutes and fills the disk. The team cannot trace one customer's request and loses 40 minutes. A well-logged system would have found the failing orderId in a couple of minutes.

**What the interviewer is really checking**
Whether you treat logs as a designed tool for diagnosis under pressure, not as print statements, and whether you know the practical limits (volume, cost, safety) of logging during an outage.

**How I answer it**
1. **Put a correlation id on every line.** Create it at the edge (or accept it from an incoming header), store it in MDC, and pass it on in HTTP and Kafka headers. Reason: one search then reconstructs a request across services.
2. **Log one line per event, at the right level.** ERROR means someone must act, WARN means unexpected but handled, INFO marks business milestones, DEBUG is for detail. Reason: if everything is ERROR, the real errors are hidden and alerts become noise.
3. **Include identifiers.** Log orderId and, for Kafka, topic, partition and offset. Reason: you can replay or inspect the exact failing record.
4. **Avoid logging inside tight loops.** Log a summary instead ("processed 500 items, 3 failed"), or sample. Reason: huge volume slows the app, fills disks and increases log-platform cost.
5. **Never swallow exceptions; log with the cause once.** Pass the exception object so the stack trace is kept, and log it where you handle it, not at every layer. Reason: a swallowed error hides the root cause, and duplicate lines make the failure look larger than it is.
6. **Keep a runtime switch for log levels.** Change a level temporarily without redeploying. In Spring Boot, the Actuator `loggers` endpoint does this:
```
POST /actuator/loggers/com.shop.payment
{"configuredLevel":"DEBUG"}
```
Reason: a redeploy during an incident adds risk and may erase the very state you are investigating. Reset the level afterwards. The change is lost on restart.

**Trade-offs and what can go wrong**
- Too little detail leaves you blind. Too much costs money and hides the signal.
- DEBUG on a busy service can cause the outage you were investigating. Raise it for one package, for a short time.
- Never log secrets, card numbers or personal data. Mask them.
- Secure the Actuator endpoint, because anyone who can reach it can change your logging.
- Logging and rethrowing at every layer produces duplicates.
- Ids only help if they are propagated. Async and Kafka hops lose MDC unless you copy it across.

**How I'd monitor it**
- In Splunk, search by correlation id or orderId to follow one request: `index=app correlationId="abc-123" | sort _time`.
- Chart the ERROR count over time and alert on spikes.
- Watch log volume per service, since a sudden jump suggests a loop or an overly verbose level.
- Check Actuator `loggers` to confirm which levels are active, and alert if DEBUG stays on too long.

**Follow-ups to expect**
- *Log and rethrow, or just rethrow?* -> Do one or the other. Log where you finally handle the error, so each failure appears once with its stack trace.
- *How do you carry a correlation id across Kafka?* -> Put it in a record header at the producer, and have the consumer read it into MDC before processing.
- *How do you keep debugging detail without huge volume?* -> Enable DEBUG temporarily for one package or one request, or use sampling.

**60-second answer**
During an incident, logs must let me follow one request quickly. So every line carries a correlation id, and I include business identifiers like orderId, plus topic, partition and offset for Kafka. I log each event once at the right level and never inside tight loops. I don't swallow exceptions: I log them once with the full cause. I keep a way to raise the log level at runtime, for example Spring Boot Actuator's loggers endpoint, so I get more detail without redeploying, and I turn it back afterwards. I also never log sensitive data. In Splunk I search by correlation id to see the whole story.

### Q21 [senior] Explain graceful degradation versus failing fast.
tags: graceful-degradation, fail-fast, resilience, timeouts, circuit-breaker, fallback, incident-response, basics

**Start here: the concepts**
- **Dependency:** another service, database or API that your service calls to do its work. When it is slow or down, your service is affected too.
- **Core path vs non-critical feature:** the core path is what the business cannot live without (checkout, payment). A non-critical feature is nice to have (recommendations, "recently viewed"). Separating them is the first step in both strategies.
- **Graceful degradation:** when a dependency fails, the system gives a reduced but still useful result. It might serve cached or partial data, or switch off a non-critical feature, so the core path keeps working.
- **Fallback:** the substitute answer used when the real one is unavailable, such as yesterday's cached "popular items" list.
- **Fail fast:** when there is no useful fallback, return a quick, clear error immediately instead of waiting. The reason is that a waiting request holds a thread, a connection and memory, and these are limited.
- **Timeout:** the maximum time you wait for a dependency. Without one, a slow dependency can hold your resources indefinitely.
- **Circuit breaker:** a guard that counts failures. After too many, it "opens" and rejects calls instantly for a short time, then lets a few test calls through to see if the dependency has recovered.
- **Feature flag:** a runtime switch that turns a feature on or off without a deployment.

**The live scenario**
It is a sale day and checkout gets about 2,000 requests per second. The recommendation service slows from 50 ms to 30 seconds. The checkout page calls it synchronously, so each request holds a thread while it waits. The 200 server threads fill within a couple of minutes. Checkout, which does not need recommendations, starts timing out for every customer. An optional widget has taken down revenue. In the same week the payment service has a short outage. There is no fallback for payment, so the right behaviour is a fast "please retry" message rather than a spinner that holds threads.

**What the interviewer is really checking**
Whether you treat these as a per-feature business decision rather than a slogan. They also want to see that you know both depend on timeouts and isolation, and that you can connect this to real incident handling.

**How I answer it**
1. **Classify each dependency.** Is it on the core path, and is there an acceptable substitute? This decides the strategy, and the reason is that the business, not the code, defines "acceptable".
2. **Degrade where a fallback exists.** For recommendations, return cached popular items or hide the widget. The customer still buys and the core path is protected.
3. **Fail fast where no fallback exists.** For payment, a made-up success is worse than an error. Return a clear error quickly and release the thread so other requests are not starved.
4. **Put a short timeout on every remote call.** Both strategies depend on this, because degrading or failing fast only happens once you stop waiting. Choose the timeout from the dependency's normal latency, for example a few hundred ms rather than 30 s.
5. **Add a circuit breaker and isolation.** An open breaker rejects calls instantly, and separate thread pools or limits per dependency stop one slow service from consuming everything.
6. **In an incident, mitigate first.** Flip the feature flag to turn the feature off, or roll back, then diagnose. A thread dump (`jstack` or `jcmd <pid> Thread.print`) showing many threads blocked on a socket read to one host confirms the cause.
7. **Decide per feature and document it.** Record the choice (degrade or fail fast, fallback, timeout) in a runbook so on-call engineers are not guessing at 3 a.m. Then do a blameless RCA and add the missing timeout.

**Trade-offs and what can go wrong**
- Stale cached data may mislead users, for example showing a price or stock level that is out of date. Never degrade on money or safety data.
- Fallback code is rarely exercised, so it can be broken when you need it. Test it with fault injection.
- A timeout set too low causes false failures, and too high gives no protection.
- Retrying a struggling dependency can overload it. Use limited retries with backoff.
- Silent degradation hides problems, so always record when a fallback is used.

**How I'd monitor it**
- Thread pool usage and request latency (p95/p99) through Actuator and APM.
- Circuit breaker state and fallback counts as metrics, with an alert when a breaker stays open.
- A Splunk search such as `index=prod service=checkout fallback=true | timechart count by dependency`, and one for timeout exceptions by dependency.
- Error rate on the core path, which should stay flat when a non-critical dependency fails.

**Follow-ups to expect**
- *How do degradation and a circuit breaker relate?* -> The breaker detects failure and stops calls quickly. The fallback is what you return instead, which is the degradation.
- *Is failing fast ever wrong?* -> Yes, if a safe fallback exists and the feature is non-critical, an error needlessly hurts the user.
- *How do you prove it works before production?* -> Fault-injection or chaos tests that make a dependency slow or down and check that the core path stays healthy.

**60-second answer**
Graceful degradation means that when a dependency fails, I return a reduced but useful result, such as cached data or hiding a non-critical feature like recommendations, so the core path like checkout keeps working. Failing fast means that when there is no useful fallback, as with payment, I return a quick, clear error instead of holding threads and connections while waiting. Both rely on short timeouts, circuit breakers and isolation, otherwise a slow dependency fills the thread pool and takes everything down. I decide per feature with the business, based on whether an acceptable substitute exists, and I document it in a runbook. In an incident I mitigate first, for example by switching a feature flag off, then confirm the cause with thread dumps and Splunk. I also monitor fallback counts and breaker state so degradation is never silent.

### Q22 [mid] How would you find errors for a particular service?
tags: splunk, log-search, observability, troubleshooting, production-incidents, basics

**Start here: the concepts**
- **Log:** a line of text a service writes about something that happened, such as a request handled or a failure. Logs exist because you can't watch a running production system directly, so you read what it wrote down.
- **Log level:** a label such as INFO, WARN or ERROR that says how serious a line is. Filtering on ERROR hides the routine noise.
- **Splunk:** a tool that collects logs from many servers into one place and lets you search them.
- **Index:** a named storage bucket in Splunk. `index=application` means "search only this bucket". It is just an example name; yours will differ.
- **SPL (Search Processing Language):** Splunk's query language. You write a search, then pipe (`|`) the results into commands that count, group or chart them.
- **Field:** a named piece of an event, like `service` or `level`. Fields are extracted from the raw text, so which fields exist depends on how your logs are ingested.
- **Time range:** the window Splunk searches. A narrow window is faster and shows only the incident.
- **Correlation ID:** a unique ID attached to one request and passed through every service it touches. Searching it gives you that request's whole story.
- **Deployment version:** the release number of the running code. It lets you ask whether the errors started with a release.

**The live scenario**
`order-service` handles about 2,000 requests a minute. At 14:05, support reports that checkout is failing. Normally the service logs around 5 errors per 5 minutes. A chart shows about 600 per 5 minutes since 14:00, which is exactly when version 2.4.1 was deployed. Filtering the errors by version shows nearly all of them come from 2.4.1. The team rolls back first, then reads the stack traces to find the cause.

**What the interviewer is really checking**
Whether you can go from "something is wrong" to a focused, evidence-based view without drowning in logs. They also want to see that you know field names vary and that you check your assumptions.

**How I answer it**
1. **Set a narrow time range first.** Use the incident window, for example the last 30 minutes. It makes the search faster and keeps old, unrelated errors out of the results.
2. **Filter by service and level.** Search the right index for that service's ERROR events, then count them over time:
```spl
index=application service="order-service" level="ERROR"
| timechart span=5m count
```
   `timechart span=5m count` groups events into 5-minute buckets and counts each one. A spike or a sudden start shows you *when* it began. Compare that moment with deployments, config changes or traffic changes.
3. **Narrow down.** Add a filter or split the chart by endpoint, error code, or deployment version. This shows whether the errors come from one API, one failure type, or one release.
4. **Follow one failing request with its correlation ID.** Search that ID across services to see where the request actually broke.
5. **Check your fields.** Confirm that `service` and `level` exist in your events, because extraction depends on the source and ingestion setup. If they don't, search on the raw text or on the real field names. Field names are case-sensitive and values usually aren't, but verify.
6. **Then act.** If the spike lines up with a release, mitigate first (roll back or turn off a feature flag), and diagnose the stack traces afterwards.

**Trade-offs and what can go wrong**
- Wrong field names or a wrong index return zero results, which looks like "no errors". Check by searching without the level filter.
- Some failures are not logged as ERROR. They may be WARN, or HTTP 5xx responses logged at INFO. Also check status codes.
- Wide time ranges are slow and costly on a busy index.
- A count alone does not show impact. Compare it with total traffic to get an error rate.
- Missing correlation IDs make tracing across services very hard.

**How I'd monitor it**
- Save the search as a dashboard panel showing error count and error rate per service.
- Create a Splunk alert when errors exceed a threshold, say 10x the normal baseline for 5 minutes.
- Add deployment markers to the chart, and watch the application metrics (for example Spring Boot Actuator, or an APM tool) next to the logs.

**Follow-ups to expect**
- *How do you find the most common error?* -> Add `| top limit=10 error_code` (or a message field) to rank the causes.
- *How do you trace one request across services?* -> Search its correlation ID without the service filter and sort by time.
- *What if the errors aren't tagged ERROR?* -> Search the HTTP status (5xx), the exception class names, or WARN logs, and verify the field extraction.

**60-second answer**
First I set a narrow time range around the incident. Then I search Splunk for that service's ERROR events and run `timechart span=5m count` to see when errors started and how large the spike is. Next I narrow down by endpoint, error code, or deployment version, and I follow one failing request with its correlation ID across services. I also check that the fields I'm using really exist, because extraction differs between setups. If the spike matches a release, I roll back first and then read the stack traces to find the root cause. Afterwards I save the search as a dashboard and alert so we catch it faster next time.
