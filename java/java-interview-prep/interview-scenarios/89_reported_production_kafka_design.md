---
id: reported-production-kafka-design
title: Reported rounds, production and Kafka design (Deloitte, Mastercard, Virtusa): fraud platform, millions of events, hangs, pool exhaustion, Git rules, secrets in logs
stack: java
skill: architecture
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). The production questions
use the three-tier shape: short answer, technical detail, deep dive.

### Q1 [architect] Design a Kafka-based fraud detection platform that processes transactions in near real time and supports recovery after failures.
tags: kafka, fraud-detection, kafka-streams, flink, feature-store, exactly-once, replay, dlt, system-design, deloitte, reported-rounds

**Start here: the concepts**
- **Sync vs async decision:** a card authorisation must answer in about 100 ms, so the blocking check can't wait for a slow pipeline.
- **Stream processing:** computing rolling features, such as "transactions in the last 5 minutes", over an event stream.
- **Recovery:** Kafka retains events, so state can be rebuilt by replaying them.

**The live scenario (functional requirement)**
*FR: "Score each card payment before approval in under 100 ms at 10,000 per second at peak. Analysts get alerts for suspicious patterns. Nothing is lost, and scoring resumes correctly after a crash."*

**What the interviewer is really checking**
That you separate the fast path from the analysis path, and that "recovery" is a real design rather than a hope.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** block or just alert? How costly is a false positive? What's the latency budget? I assume a blocking check with a fail-open or fail-closed decision by amount.
2. **Two paths:**
   - **Fast path, synchronous:** the payment service calls the scoring service. It reads precomputed features from Redis, applies rules and a model, and answers within the budget. No Kafka in this request path.
   - **Slow path, asynchronous:** every transaction goes to Kafka, feeding feature computation, deeper models, and analyst alerts.
3. **Topics:** `txn.events` keyed by card id, so one card's events stay ordered in one partition. `txn.scores`, `fraud.alerts`, and `txn.events.dlt`.
4. **Stream processing:** Kafka Streams or Flink computes windowed features (velocity, distinct merchants, distance from last location), using event time with watermarks, because events arrive late. Features are written to Redis for the fast path.
5. **Partitions:** 10,000 per second at about 5,000 per consumer gives a floor of 2. For headroom, peaks and replay, I'd start much higher, perhaps 32, since increasing later changes key routing.
6. **Delivery settings:** `acks=all`, `min.insync.replicas=2`, `enable.idempotence=true`, replication factor 3, across availability zones.

Failure and recovery plan:

| Failure | What happens | Recovery |
|---|---|---|
| Processor crash | Rebalance; another instance takes over | Offsets and changelog topics restore its state |
| Duplicate after a crash | At-least-once redelivery | Idempotent alert on `transactionId`; EOS for Kafka-to-Kafka |
| Bad message | Would block the partition | Retry topic, then DLT, with an alert |
| Bug in the model or a feature | Wrong scores for hours | Fix it, replay from the retained offset into a new consumer group, and correct downstream with versioned outputs |
| Redis down | Fast path has no features | Timeout, then rules only, with a decision per risk level |
| Scoring service down | Payment can't be checked | Circuit breaker, then fail open for small amounts and closed for large |
| Region lost | All of the above | Multi-region replication; declare RPO and RTO |

**Trade-offs and what can go wrong**
- **Kafka exactly-once** covers Kafka-to-Kafka only. Side effects like emails or database writes still need idempotency.
- **Replay risk:** replaying must not re-send customer alerts, so keep the side effects behind a flag or a separate consumer.
- **Feature drift:** the online and offline computations must match, or models degrade silently.
- Keep PII out of event payloads where possible, and tokenise card numbers. PCI scope applies.

**How I'd monitor it**
Fast-path p99 against the budget, consumer lag per group, event-time lag, DLT rate, the fraud-catch and false-positive rates, and feature freshness in Redis.

**Follow-ups to expect**
- *Why not score straight from Kafka?* -> Round-trip latency and consumer lag don't fit in 100 ms.
- *How much retention?* -> Enough for replay: several days, or tiered storage for longer.
- *Bank 62 Q2* covers consumer crashes, and bank 74 Q10 covers replay.

**60-second answer**
"I'd split it. The blocking check is a synchronous scoring service reading precomputed features from Redis, within about 100 milliseconds, with no Kafka on that path. All transactions also flow into Kafka, keyed by card so each card stays ordered, and Kafka Streams or Flink computes windowed features into Redis and raises analyst alerts. For recovery, Kafka is the source of truth: on crash, a rebalance and the changelog restore state. Bad messages go to a retry topic then a DLT. After a bug, I replay from a retained offset, with alerts turned off. And if scoring is down, I fail open for small amounts and closed for large ones."

### Q2 [senior] How would you process millions of Kafka events per hour using Spring Boot, while controlling concurrency, batching and database load?
tags: spring-kafka, batch-listener, concurrency, backpressure, hikari, jdbc-batch, max-poll-records, deloitte, reported-rounds, topic-kafka

**Start here: the concepts**
- 10 million events per hour is only about 2,800 per second. Getting Kafka to deliver that is easy. **The database is usually the bottleneck.**
- **Concurrency** in Spring Kafka is the number of consumer threads, capped in effect by the partition count.

**The live scenario (functional requirement)**
*FR: "Load 10 million order events per hour into PostgreSQL, without hurting the API that shares that database."*

**What the interviewer is really checking**
Doing the arithmetic, then controlling flow end to end, not just raising numbers.

**How I answer it** (120-second answer, point by point)

Short answer: batch-listen, write with JDBC batches, set concurrency from a measured per-thread rate, cap database connections below what the API needs, and let Kafka hold the excess, since lag is safe and overload isn't.

Technical detail:

| Setting | Example | Why |
|---|---|---|
| Partitions | 24 | Sets the maximum parallelism |
| `concurrency` | 6 pods x 4 threads = 24 | One thread per partition |
| Listener | Batch mode | Writes many rows per commit |
| `max.poll.records` | 500 | Sets the batch size |
| `max.poll.interval.ms` | Above worst batch time | Avoids a rebalance mid-batch |
| `fetch.min.bytes` | 64 KB | Fewer, fuller fetches |
| Ack mode | `MANUAL` or `BATCH` | Commit after the database commit |
| Hikari pool | Thread count plus a small margin | A connection per writer thread |
| `reWriteBatchedInserts=true` | PostgreSQL driver | Several times faster inserts |

```java
@KafkaListener(topics = "orders", concurrency = "4", batch = "true")
void onBatch(List<OrderEvent> events, Acknowledgment ack) {
    repo.upsertAll(events);   // JDBC batch: INSERT ... ON CONFLICT (order_id) DO NOTHING
    ack.acknowledge();
}
```

Deep dive:
1. **Arithmetic:** 10M per hour is 2,800/s average. Plan for a 3x peak, so 8,400/s. If one thread with batches writes 500/s, that's about 17 threads, so 24 partitions gives headroom.
2. **Idempotency:** at-least-once delivery will redeliver after a crash, so `ON CONFLICT DO NOTHING` on a business key makes repeats harmless.
3. **Don't use JPA `saveAll` for this.** With `IDENTITY` keys, Hibernate can't batch inserts. Use `JdbcTemplate.batchUpdate` or `COPY`.
4. **Protecting the database:** give this consumer its own limited pool, or a separate writer instance. If the database slows, pause with `container.pause()`, or let batches take longer. Lag rises, which is the safe outcome.
5. **Poison messages:** in a batch, one bad record shouldn't fail 499. Use `DefaultErrorHandler` with `BatchListenerFailedException` to point at the failed record, retry and send to a DLT.
6. **Order:** keep ordering per key with key-based partitions. Avoid thread handoff inside a listener, which breaks it.

**Trade-offs and what can go wrong**
- Concurrency above the partition count leaves threads idle.
- Larger batches increase throughput, but also duplicates after a crash, and rebalance risk.
- Autoscale on lag (KEDA, bank 64) only up to what the database can take.

**How I'd monitor it**
Lag per partition, records per second, batch duration, Hikari pending, database CPU and IOPS, DLT rate, and rebalance count.

**Follow-ups to expect**
- *Virtual threads in a listener?* -> They don't help a single partition, because order requires one at a time. The database pool is still the limit.
- *Tuning at scale?* -> Bank 03 and bank 62 Q3.

**60-second answer**
"First the arithmetic: 10 million an hour is under 3,000 a second, so Kafka isn't the constraint; the database is. I use batch listeners with 500-record polls and write with a JDBC batch using ON CONFLICT DO NOTHING, so redelivery is harmless, committing offsets only after the database commit. I measure one thread's rate, and set partitions and concurrency from that with headroom for peaks. This consumer gets a capped connection pool, so it can't starve the API. If the database slows, lag grows, and that's the safe outcome. One bad record goes to a DLT without failing the whole batch."

### Q3 [senior] A production application hangs intermittently because of lock contention and database waits. How would you investigate?
tags: thread-dump, lock-contention, blocked, pg-locks, jfr, async-profiler, deadlock, production, deloitte, reported-rounds, topic-production

**Start here: the concepts**
- A "hang" usually means threads are **waiting**, not working, so CPU may be low.
- Intermittent problems need evidence captured **while** it happens, or a recording running beforehand.

**The live scenario (functional requirement)**
*FR: "Checkout freezes for 20 to 40 seconds a few times a day, then recovers."* There's no error, and CPU stays at 30%.

**What the interviewer is really checking**
Separating JVM waits from database waits, with real evidence from both sides.

**How I answer it** (120-second answer, point by point)

Short answer: I capture thread dumps during the freeze to see what threads are waiting on, then correlate with database lock views to find who holds the lock. Low CPU with high latency means waiting, not computing. I fix the holder by shortening the critical section or the transaction.

Technical detail:

| Layer | Evidence | Command |
|---|---|---|
| JVM threads | `BLOCKED` on a monitor, `WAITING` on a `ReentrantLock` | `jcmd <pid> Thread.print` x 3, 10 s apart |
| JVM over time | Lock events with durations | JFR: `jcmd <pid> JFR.start duration=10m` and look at `jdk.JavaMonitorEnter` |
| Profiling | Time spent waiting | `async-profiler -e lock` |
| DB pool | Threads waiting for a connection | `hikaricp.connections.pending` |
| PostgreSQL | Who's waiting on whom | `pg_stat_activity`, `pg_blocking_pids(pid)` |
| MySQL | Same | `performance_schema.data_lock_waits`, `SHOW ENGINE INNODB STATUS` |

Deep dive:
1. **Trigger capture automatically,** since a freeze may be over before anyone looks: an alert on p99 or pending connections runs a script that takes dumps. Keep JFR running continuously (about 1% overhead).
2. **Read the thread dump:** many threads `BLOCKED` with `waiting to lock <0x...>`. Search that address to find the thread that holds it, and see what *it* is doing. Usually it's a slow call inside the lock.
3. **Database side:** in `pg_stat_activity`, look for `wait_event_type = 'Lock'`, and for `idle in transaction`. That second state usually means the app opened a transaction, then went off and did something else.
4. **Correlate by time:** does it match a nightly job, a schema migration (`ALTER TABLE` waits on a strong lock, and everything queues behind it), a large batch update, or a Kafka rebalance?
5. **Typical root causes and fixes:**

| Cause | Fix |
|---|---|
| HTTP call inside `@Transactional` | Call outside the transaction |
| Lock held during slow work | Copy the data, release, then work; or use `ConcurrentHashMap` |
| Report or batch updating many rows | Smaller batches, off-peak, or a replica |
| `ALTER TABLE` queueing | `lock_timeout` on migrations; online schema tools |
| Inconsistent lock order | Consistent order; retry on deadlock |
| GC pause mistaken for a hang | Check the GC log first |

**Trade-offs and what can go wrong**
- One thread dump can mislead. Take several and compare what stays stuck.
- A restart clears the symptom and destroys the evidence.
- Adding timeouts (`statement_timeout`, `lock_timeout`, query timeouts) turns a hang into a visible error. That's an improvement.

**How I'd monitor it**
Blocked thread count, lock wait time from JFR, Hikari acquire time, database lock waits and deadlocks, and long transactions.

**Follow-ups to expect**
- *How is that different from high CPU?* -> Bank 07 Q2: hot threads at 100%, found via `top -H`. A hang is threads doing nothing.
- *High CPU, frequent GC, and rising latency together?* -> Usually a leak: GC runs constantly and takes the CPU. See bank 07 Q3.

**60-second answer**
"Low CPU with freezes means threads are waiting. I'd capture three thread dumps during the freeze, automatically from an alert, and keep JFR running. BLOCKED threads point at a monitor, and I find the holder in the dump and see what it's doing. On the database, pg_stat_activity and pg_blocking_pids show who's blocking whom, especially idle-in-transaction sessions. Then I correlate timing with batch jobs and migrations. The usual cause is slow work while holding a lock, like an HTTP call inside a transaction. The fix is shortening that, and adding lock timeouts so a hang becomes a visible error."

### Q4 [senior] A database connection pool is exhausted even though queries are fast. How would you investigate?
tags: hikaricp, connection-pool, leak-detection, transaction-scope, open-in-view, idle-in-transaction, production, deloitte, reported-rounds, topic-production

**Start here: the concepts**
- A connection is held for the **whole transaction**, not just for the query. A 2 ms query inside a 3-second transaction holds its connection for 3 seconds.

**The live scenario (functional requirement)**
*FR: "Orders API: all database queries are under 5 ms in the logs, yet requests fail with `HikariPool-1 - Connection is not available, request timed out after 30000ms`."*

**What the interviewer is really checking**
Whether you know that the query time isn't the same as the time the connection is held.

**How I answer it** (120-second answer, point by point)

Short answer: fast queries don't mean short connection use. Something holds connections between queries: an HTTP call inside a transaction, Open Session in View, or a leak. Hikari's metrics show whether connections are being held, and its leak detection shows by whom.

Technical detail:

| Evidence | Meaning | How |
|---|---|---|
| `hikaricp.connections.active` at max, `pending` above 0 | Exhausted | Micrometer |
| `hikaricp.connections.usage` p99 far above query time | Held between queries | Micrometer |
| Stack trace of the holder | Who took it and kept it | `spring.datasource.hikari.leak-detection-threshold=20000` |
| `state = 'idle in transaction'` | App holds an open transaction doing nothing | `pg_stat_activity` |
| Threads inside `HikariPool.getConnection` | Waiting for a connection | Thread dump |

Deep dive, usual causes in order:
1. **Remote call inside `@Transactional`:** the connection stays checked out for the whole HTTP call. Slow vendor, slow everything. Do the call outside the transaction.
2. **Open Session in View:** `spring.jpa.open-in-view` defaults to true, and it can keep a connection through view rendering, or a slow response after lazy loading. Set it to false.
3. **A leak:** a `getConnection()` with no close. Use try-with-resources or `JdbcTemplate`.
4. **Nested `REQUIRES_NEW`:** the thread holds one connection while asking for a second. Under load, all threads hold one and wait for another: a pool deadlock.
5. **Too many pods for the database:** 50 pods x 20 connections is 1,000 connections, more than the database's `max_connections`, even though each pool is fine. Use PgBouncer or RDS Proxy.
6. **A slow statement that's outside your logs**, such as commit time under heavy fsync, or lock waits.

**Sizing:** after fixing the cause, size by arithmetic: throughput x hold time. 500 requests/s x 20 ms = 10 connections, plus margin. Raising the pool first only hides the bug and moves the pressure to the database.

**Trade-offs and what can go wrong**
- `connectionTimeout` of 30 seconds means requests queue for 30 seconds. A shorter one, such as 2 seconds, fails fast and protects threads.
- `leak-detection-threshold` only logs. It doesn't fix anything, and it has small overhead.

**How I'd monitor it**
Alert on `pending > 0` for one minute, and chart usage time against query time. The gap between them is the bug.

**Follow-ups to expect**
- *Pool size formula?* -> Bank 26 Q12 and bank 06 Q4.
- *Does a bigger pool help?* -> Rarely. It increases the database's load and hides the hold time.

**60-second answer**
"Query time isn't connection hold time: a connection stays out for the whole transaction. So fast queries with an exhausted pool means something holds connections between queries. I compare Hikari's usage time with query time, and turn on leak detection to get the stack trace of the holder, and look for idle-in-transaction sessions in Postgres. The usual cause is an HTTP call inside @Transactional, then Open Session in View, a real leak, or nested REQUIRES_NEW. I fix that first. I don't just raise the pool size, because that hides the bug and pushes the load onto the database."

### Q5 [mid] What branching strategies are available in GitHub, and how do you configure branch protection rules?
tags: git, github, branching-strategy, trunk-based, gitflow, branch-protection, rulesets, codeowners, mastercard, reported-rounds, topic-testing

**Start here: the concepts**
- A **branching strategy** decides how work reaches `main`. **Branch protection** enforces it, so nobody can bypass the process.

**The live scenario (functional requirement)**
*FR: "A payments service: regulators want every production change reviewed and traceable, and the team wants to release daily."*

**What the interviewer is really checking**
That you know the options, and can name the settings in GitHub.

**How I answer it** (120-second answer, point by point)

| Strategy | How it works | Fits |
|---|---|---|
| **Trunk-based** | Short-lived branches, merge daily, feature flags hide unfinished work | Frequent releases and strong CI |
| **GitHub Flow** | Branch from `main`, PR, merge, deploy | Most web services |
| **GitFlow** | `develop`, `release/*`, `hotfix/*` | Versioned products with scheduled releases |
| **Release branches** | `main` plus a long-lived `release/x` | Several supported versions at once |

For this FR, I'd use GitHub Flow or trunk-based with feature flags.

**Setting it up:** Settings -> Rules -> Rulesets (or the older Branches -> Branch protection rules), for `main`:
1. **Require a pull request**, with one or two approvals. Dismiss stale approvals on new commits.
2. **Require review from Code Owners**, using a `CODEOWNERS` file, for sensitive paths.
3. **Require status checks to pass:** build, tests, SonarQube gate, security scan. And require the branch to be up to date, or use a **merge queue**.
4. **Require conversation resolution.**
5. **Require signed commits**, and linear history if the team prefers it.
6. **Block force pushes and deletions**, and apply the rules to admins too, with a recorded bypass only.

Rulesets can apply across repositories at organisation level, and several can be layered. That's why I'd prefer them to the older rules.

**Trade-offs and what can go wrong**
- Long-lived branches cause merge pain and delayed integration, which is the main criticism of GitFlow for web services.
- Requiring "up to date" blocks merges on busy repos, so use a merge queue.
- Protection on `main` doesn't help if deployment can start from any branch. Restrict that with deployment environments.

**Follow-ups to expect**
- *Squash, rebase or merge commit?* -> Squash gives one clean commit per PR, which is simple to revert.
- *Bank 31 Q12* covers GitFlow vs trunk-based.

**60-second answer**
"The main options are trunk-based with short branches and feature flags, GitHub Flow, GitFlow for scheduled versioned releases, and release branches when several versions are supported. For a service that releases daily, I'd pick trunk-based or GitHub Flow. In GitHub, I'd use rulesets on main: require a PR with approvals and code owner review, required status checks including tests and a quality gate, conversation resolution, no force pushes or deletions, and apply them to admins too. Busy repos should add a merge queue."

### Q6 [senior] How would you securely manage passwords, API keys, secrets and sensitive information in application logs?
tags: secrets-management, vault, secrets-manager, log-masking, logback, pii, rotation, security, deloitte, reported-rounds, topic-cloud-devops

**Start here: the concepts**
- Two separate problems: **storing** secrets safely, and **keeping** secrets and personal data out of logs.
- Logs get copied widely (Splunk, S3, support tickets), so a secret in a log counts as leaked.

**The live scenario (functional requirement)**
*FR: "A payment service holds a database password and a vendor API key. A debug log line printed a full request, including an Authorization header and a card number, into Splunk."*

**What the interviewer is really checking**
Prevention in layers, and knowing what to do once it has already leaked.

**How I answer it** (120-second answer, point by point)

Storing secrets:
1. Never in Git, images or plain `application.yml`. Scan commits with gitleaks or GitHub secret scanning.
2. Use a manager: AWS Secrets Manager, HashiCorp Vault or Azure Key Vault. Spring: `spring.config.import=aws-secretsmanager:...` or Spring Cloud Vault.
3. Access by workload identity (IAM role, IRSA), so no bootstrap password exists.
4. Rotate automatically. Short-lived database credentials from Vault are the best version.

Keeping them out of logs, in layers:
1. **Don't log whole objects.** Exclude them from `toString`, such as `@ToString.Exclude`. A record's generated `toString` prints every field, so override it for sensitive ones.
2. **A wrapper type:** `Secret` or `Masked<T>` whose `toString` returns `***`, so an accident can't print the value. This works by construction, which beats relying on people remembering.
3. **Log an allow-list** of fields, rather than excluding a block-list. New fields are then safe by default.
4. **Masking at the logger** as a safety net: a Logback pattern converter or JSON provider that masks by field name and by regex for card numbers and bearer tokens.
5. **HTTP filters:** never log `Authorization`, `Cookie` or `Set-Cookie`. Mask in any request-logging filter.
6. **Stack traces and SQL:** Hibernate's bind-value logging prints parameters, so keep it off in production. Exceptions can embed data too.
7. **Pipeline:** a second masking stage in the log shipper or at Splunk (`SEDCMD` in `props.conf`), with restricted access and a retention limit.
8. **Test it:** an automated test asserts that log output has no card number or token patterns.

**If a secret has leaked:** **rotate first**, then find its usage, purge or mask the logs, audit access, and add a guard so that it can't recur. Deleting the log isn't enough, because copies exist.

**Trade-offs and what can go wrong**
- Regex masking has false positives and costs CPU on hot log paths, which is why prevention comes first.
- Hashing an email isn't anonymising it, since common values can be guessed.
- PCI DSS forbids logging full card numbers and security codes.

**How I'd monitor it**
Scheduled log scans for secret patterns, secret-scanning alerts, an audit trail of secret access, and rotation age.

**Follow-ups to expect**
- *Environment variables?* -> Better than code, but visible through `/proc` and Actuator. Secure `/actuator/env`.
- *Bank 85 Q11* covers config and secrets broadly. Kubernetes `Secret`s are only base64 unless encrypted at rest: bank 32 Q25.

**60-second answer**
"Two problems. For storage, secrets never go in Git or config files. They live in Secrets Manager or Vault, accessed by workload identity, and rotated automatically. For logs, I prevent first: never log whole objects, use a wrapper type whose toString prints stars, and log an allow-list of fields. Then a masking layer in Logback for card and token patterns, and exclude Authorization headers from HTTP logging. And a test asserts that logs are clean. If something leaks, the first step is rotating the secret, since copies of logs already exist."
