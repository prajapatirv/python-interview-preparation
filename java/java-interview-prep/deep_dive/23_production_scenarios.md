# Production scenarios: 20 "why is it broken" questions for senior Java backend roles

> **Runnable (all self-asserting):**
> [`01_thread_pool_deadlock_and_async.java`](../examples/23_production_scenarios/01_thread_pool_deadlock_and_async.java) (Q1, Q2, Q10) ·
> [`02_language_and_collection_traps.java`](../examples/23_production_scenarios/02_language_and_collection_traps.java) (Q11, Q12, Q13, Q16, Q17) ·
> [`03_spring_jpa_and_security_simulations.java`](../examples/23_production_scenarios/03_spring_jpa_and_security_simulations.java) (Q3, Q4, Q8, Q9, Q15, Q18, Q19) ·
> [`04_connections_kafka_and_redis_simulations.java`](../examples/23_production_scenarios/04_connections_kafka_and_redis_simulations.java) (Q5, Q6, Q7, Q20)
> Q14 is configuration-only and has no runnable file.
> **Related:** [18 Production troubleshooting](18_production_troubleshooting.md) (the triage runbook) ·
> [04 Concurrency](04_concurrency.md) · [09 Spring Data JPA](09_spring_data_jpa.md) · [12 Kafka](12_kafka.md) ·
> [13 NoSQL](13_nosql.md) · [10 Spring Security](10_spring_security.md)

## What interviewers are actually probing

This is the format used for the 3-8 year, high-compensation Java backend rounds: **one symptom, one
question, expected answer in two or three sentences.** There is no whiteboard. They are checking that you
have *been paged for this*, so the answer must contain the **mechanism** (why), not only the **fix**.

The scoring pattern, in order:

1. **Name the mechanism in the first sentence.** "The proxy only sees what the method throws."
2. **Give the number or the default.** "10 threads", "-128 to 127", "`noeviction`", "Boot 2.6".
3. **Give the fix and one trade-off.** "Deny-list the `jti`, but now every request does a Redis lookup."
4. **Say how you would prove it** (thread dump, `redis-cli --hotkeys`, `pg_stat_activity`, SQL log).

## Cheat sheet: symptom -> mechanism -> fix

| # | Symptom | Mechanism | Fix |
|---|---|---|---|
| 1 | core 10 / max 50 / unbounded queue, 10x traffic | threads beyond core are created only when the queue is **full**; an unbounded queue is never full | bounded queue + rejection policy, or core = max |
| 2 | A->B and B->A hang | lock-ordering cycle | lock accounts in a global order (by id) |
| 3 | exception caught and logged, writes still commit | proxy sees a normal return | rethrow, or `setRollbackOnly()` |
| 4 | checked exception, no rollback | default rollback is `RuntimeException` and `Error` only | `rollbackFor = Exception.class` |
| 5 | 5 -> 20 pods, Postgres refuses | pods x pool size > `max_connections` | smaller pools, PgBouncer |
| 6 | add partitions, ordering breaks | partition = `hash(key) % count` | plan partitions up front, new topic + migrate |
| 7 | Redis full, writes fail | `maxmemory-policy` = `noeviction` | `allkeys-lru`/`lfu` for a cache |
| 8 | JWT works after logout | stateless token valid until `exp` | short TTL + refresh, deny-list `jti` |
| 9 | 90 s startup, pod restarts | liveness probe fires before startup ends | `startupProbe`, readiness for traffic |
| 10 | `supplyAsync` without executor | `ForkJoinPool.commonPool()` | pass your own executor for blocking work |
| 11 | shared `SimpleDateFormat` wrong dates | mutable internal `Calendar` | `DateTimeFormatter` |
| 12 | `Stream.toList()` then `add()` throws | returns an unmodifiable list | `Collectors.toCollection(ArrayList::new)` |
| 13 | `Long` `==` true in tests, false in prod | `Long.valueOf` caches -128..127 | `equals()` / `Objects.equals` |
| 14 | circular dependency after Boot upgrade | Boot 2.6 disabled circular references by default | break the cycle |
| 15 | `@Value` null in constructor | field injection runs after construction | constructor parameter |
| 16 | `remove()` in for-each -> CME | `modCount` check in the iterator | `Iterator.remove()` / `removeIf` |
| 17 | body and `close()` both throw | body wins, `close()` is suppressed | read `getSuppressed()` |
| 18 | `saveAll` = 10,000 INSERTs | no `batch_size`; `IDENTITY` disables batching | `SEQUENCE` + `batch_size` + `order_inserts` |
| 19 | `LazyInitializationException` | session closed when the transaction ended | fetch join / `@EntityGraph` / DTO in the tx |
| 20 | one Redis node at 100% | hot key, or hash tag funnelling | local cache, key splitting, replicas |

## Interview questions and full answers

### Q1. Core 10, max 50, unbounded queue. Traffic goes up 10x. How many threads run? **[run: 01]**

**10.** `ThreadPoolExecutor` follows a fixed order: *fewer than core threads -> start a thread; otherwise
offer to the queue; only if the queue **rejects** the offer, start a thread up to max; otherwise reject.*
An unbounded `LinkedBlockingQueue` always accepts, so the pool never grows past core and `maximumPoolSize`
is dead configuration. The extra load becomes queue depth, which is latency and heap, and eventually an
`OutOfMemoryError` because nothing pushes back.

The runnable file submits 1,000 blocked tasks: 10 run, 990 wait. With `ArrayBlockingQueue(20)` and 100
tasks you get 10 core + 20 queued + 40 extra = 70 accepted, **30 rejected**, and the pool reaches 50 only
after the queue is full.

Fix: a bounded queue sized from a latency budget (queue depth x service time), a deliberate rejection
policy (`CallerRunsPolicy` for back-pressure), and monitoring of queue size. `Executors.newFixedThreadPool`
and `newSingleThreadExecutor` hide exactly this unbounded queue.

*Related note for Java 21:* with virtual threads you stop sizing pools for blocking IO, but
`synchronized` blocks that block pin the virtual thread to its carrier, and carriers equal the number of
cores. Use `ReentrantLock` there, or Java 24+ (JEP 491 removes the pinning).

### Q2. Two transfers, A->B and B->A, hang forever. How do you prove it from a thread dump? **[run: 01]**

Take a dump (`jstack <pid>`, `jcmd <pid> Thread.print`, or `kill -3`). The JVM does the cycle detection for
you and prints `Found one Java-level deadlock:` at the end, naming each thread, the monitor it is waiting
for and the thread that owns it. Both threads show `BLOCKED` (monitors) or `WAITING` (`ReentrantLock`),
at **0% CPU**, which also separates a deadlock from a livelock (spinning, high CPU) and from a slow
dependency (threads in `RUNNABLE` inside socket read).

Cause: thread 1 locks A then waits for B, thread 2 locks B then waits for A. Fix: acquire locks in one
global order, e.g. lower account id first. Alternatives: `tryLock(timeout)` with back-off, or a single
serialised "transfer" path per account (one partition key per account). In a database the same shape
becomes a DB deadlock; the fix is the same ordering rule on row access, plus retry on the deadlock error.

The runnable file creates the deadlock, finds it with `ThreadMXBean.findDeadlockedThreads()`, then runs
40,000 opposite transfers with ordered locking and checks money is conserved.

### Q3. A `@Transactional` method catches the exception and logs it. The half-finished writes still commit. Why? **[run: 03]**

`@Transactional` is applied by a **proxy** around your bean. The proxy can only observe what the method
throws or returns. If you catch the exception inside, the method returns normally, and the proxy commits
everything written so far.

Fixes, in order of preference:

- **Rethrow** (or wrap and throw) so the proxy sees it.
- If you must swallow it: `TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()`.
- Do not catch it at the transactional boundary at all; handle it one layer up (controller advice).

A related trap: an inner `@Transactional` method (REQUIRED) that throws marks the **shared** transaction
rollback-only even if the outer method catches it; the outer commit then fails with
`UnexpectedRollbackException`. And **self-invocation** (`this.save()`) skips the proxy entirely, so there is
no transaction at all (the runnable file shows this too).

### Q4. A `@Transactional` method throws a checked exception. Does it roll back? **[run: 03]**

**No.** By default Spring rolls back only on `RuntimeException` and `Error`; a checked exception commits
(an EJB-era rule: a checked exception is a "business" outcome). Use
`@Transactional(rollbackFor = Exception.class)` (or a specific type), or make the exception unchecked.
`noRollbackFor` is the reverse switch. Many teams set `rollbackFor = Exception.class` as the house default.

### Q5. You scale from 5 pods to 20 and Postgres starts refusing connections. Why? **[run: 04]**

Every pod owns its own Hikari pool. HikariCP defaults to 10, so 20 pods x 10 = **200** against Postgres's
default `max_connections = 100` (3 of which are reserved for superusers). 5 pods x 10 = 50 fit; 20 do not,
and the error is `FATAL: sorry, too many clients already`.

Budget it as `(max_connections - reserved - admin/batch headroom) / max pods`, where *max pods* includes
rolling-update surge and HPA ceiling, not today's count. Then either shrink pools (a DB can usefully run
roughly `cores x 2` queries at once, so a pool of 10 per pod is rarely buying throughput), or put
**PgBouncer** (transaction pooling) in front. Note that raising `max_connections` costs memory per backend
and usually makes the database slower, not faster.

### Q6. You add partitions to a Kafka topic and per-customer ordering breaks. Why? **[run: 04]**

The default partitioner for a keyed record is `murmur2(key) % numPartitions`. Change the partition count
and most keys map to a **different** partition. A customer's older events are in partition 2, their new
ones in partition 5, and Kafka guarantees order only **within** a partition, so two consumers process them
in parallel with no ordering. The runnable file uses the real murmur2 and shows over half of 1,000 keys
move going from 6 to 8 partitions.

Prevention: choose partition count for the future load up front (partitions cannot be reduced). If you
must grow: create a new topic, stop producers, drain the old topic, then switch; or make consumers
resequence by a per-key version number. Also, a consumer-group consumer count above the partition count
sits idle, so partitions are your parallelism ceiling.

### Q7. Redis hits its memory limit and writes start failing. Which setting decides that? **[run: 04]**

`maxmemory-policy`. The default is **`noeviction`**: once `maxmemory` is reached, writes fail with
`OOM command not allowed when used memory > 'maxmemory'` while reads still work. `allkeys-lru` /
`allkeys-lfu` evict across all keys (right for a pure cache); `volatile-lru` / `volatile-ttl` evict only
keys that have a TTL, so if nothing has a TTL they behave like `noeviction`. Redis used as a primary store,
a queue or for distributed locks should stay on `noeviction` with an alert, because silently evicting a
lock or a job is worse than a failed write. Also set TTLs on cache keys and watch `evicted_keys`.

### Q8. A user logs out, but their JWT keeps working for 30 more minutes. Why, and what do you change? **[run: 03]**

A JWT is self-contained and stateless: the server verifies signature and `exp` and nothing else. "Logout"
only deletes it on the client, so a copy (a stolen token, a second tab) is valid until `exp`.

Options, with the trade-off for each: **short-lived access tokens** (5-15 min) plus a **refresh token**
that the server *can* revoke (smaller window, extra refresh traffic); a **deny-list of the token's
`jti`** in Redis with TTL = remaining lifetime (immediate, but a lookup per request, i.e. stateful again);
or opaque tokens with introspection. Rotate refresh tokens and revoke the whole family on reuse.

### Q9. Spring Boot takes 90 s to start and Kubernetes keeps restarting it. What's wrong? **[run: 03]**

The **liveness probe** starts failing before the app is up, and after `failureThreshold` consecutive
failures kubelet kills the container, so it restarts and gets killed again (`CrashLoopBackOff`). With
`initialDelaySeconds: 30`, `periodSeconds: 10`, `failureThreshold: 3` the container is killed at
**second 50**, well before the 90 s start.

Fix: add a **`startupProbe`** (for example period 5 s x failureThreshold 30 = 150 s budget); liveness and
readiness are suspended until it succeeds. Use **readiness** to decide when the pod receives traffic and
**liveness** only for "this process is wedged". Then fix why it takes 90 s: lazy-init, classpath scanning,
migrations at boot, a blocking remote call in a `@PostConstruct`, or CPU limits throttling startup.

### Q10. `CompletableFuture.supplyAsync()` with no executor. Which threads run your task? **[run: 01]**

`ForkJoinPool.commonPool()`: daemon threads named `ForkJoinPool.commonPool-worker-N`, parallelism =
cores - 1, **shared with parallel streams** and every other default async stage in the JVM. If that
parallelism is 1 or less (a 1- or 2-core container) the JDK uses a new thread per task instead. Blocking
IO in the common pool starves everything else (the runnable file shows an unrelated task never starting
while blocking calls hold every worker), and daemon threads mean the JVM can exit mid-task. Pass a
dedicated, named, bounded executor for blocking work.

### Q11. A shared static `SimpleDateFormat` starts returning wrong dates under load. Why? **[run: 02]**

`SimpleDateFormat` keeps parse state (an internal `Calendar`) in the instance. Two threads calling
`parse()` or `format()` overwrite each other's fields, giving wrong dates or random
`NumberFormatException`/`ArrayIndexOutOfBoundsException`, and only under concurrency, so it passes in
tests. Fix: `java.time.format.DateTimeFormatter` (immutable, thread-safe, share one constant);
`ThreadLocal<SimpleDateFormat>` if you are stuck on legacy; never `synchronized` around a hot path.

### Q12. You switch to `Stream.toList()` and a later `list.add()` throws. Why? **[run: 02]**

`Stream.toList()` (Java 16+) returns an **unmodifiable** list: `add`, `set` and `remove` throw
`UnsupportedOperationException`. `Collectors.toList()` happens to return an `ArrayList`, but the spec makes
no promise, so code relied on it by accident. Two other differences: `Stream.toList()` allows `null`
elements (`List.of` does not), and `Collectors.toUnmodifiableList()` rejects them. If you need a mutable
list say so: `collect(Collectors.toCollection(ArrayList::new))`.

### Q13. Two `Long` ids compare equal with `==` in tests and not in production. Why? **[run: 02]**

`==` on boxed types compares **references**. `Long.valueOf` caches -128..127, so test ids 1, 2, 3 are
the same cached object; production ids from a sequence are above 127 and are distinct objects. Same trap
for `Integer`, `Short`, `Byte` and `Character`. Use `equals()` or `Objects.equals` (null-safe), or unbox to
`long`. Note `Long.equals(Integer)` is always false: the type must match.

### Q14. After a Spring Boot upgrade, startup fails on a circular dependency that worked before. What changed?

**Spring Boot 2.6** set `spring.main.allow-circular-references=false` by default. Before that the container
silently resolved bean cycles with early references for setter/field injection; now it fails fast with
`BeanCurrentlyInCreationException` and prints the cycle. The real fix is to break it: extract the shared
behaviour into a third bean, invert one dependency with an event, or inject `ObjectProvider<B>` / use
`@Lazy` on one edge (a patch, not a design). Setting the property to `true` is a stop-gap only. Constructor
injection cannot form a cycle at all, which is one reason to prefer it.

### Q15. Your `@Value` field is null inside the constructor. Why? **[run: 03]**

The container instantiates the bean first (constructor runs) and **then** populates annotated fields, so
during construction the field is still `null`. Take the value as a constructor parameter:
`MyService(@Value("${x}") String x)`. Alternatives: `@PostConstruct` or `InitializingBean`, which run after
injection. This is also why constructor injection makes the class testable without a container.

### Q16. `list.remove()` inside a for-each loop throws `ConcurrentModificationException` on one thread. How? **[run: 02]**

for-each compiles to an `Iterator`. `ArrayList.remove` bumps `modCount`; the iterator's next `next()`
compares it with the `expectedModCount` it captured and throws. No second thread is involved; the name is
misleading. The famous exception: removing the **second-to-last** element does *not* throw, because
`hasNext()` becomes false before `next()` is called, so the bug hides until the list changes. Use
`Iterator.remove()` or `removeIf(...)`. `CopyOnWriteArrayList` iterates a snapshot (fine for read-mostly,
expensive for writes).

### Q17. In try-with-resources, the body throws and `close()` throws too. Which exception do you get? **[run: 02]**

The **body's** exception. The `close()` exception is added to it with `addSuppressed`, and you read it
through `getSuppressed()`. Old `try/finally` did the opposite: the exception thrown in `finally` replaced
the original and the root cause was lost. Resources close in **reverse** order of declaration; when there is
no body exception, the first `close()` failure is thrown and later ones are suppressed on it.

### Q18. `saveAll()` on 10,000 entities sends 10,000 separate INSERTs. Why? **[run: 03]**

Two independent reasons. (1) Hibernate sends no JDBC batches until
`hibernate.jdbc.batch_size` is set. (2) With `GenerationType.IDENTITY` the database assigns the id, so
Hibernate must execute each INSERT immediately to learn the id, which **disables insert batching
completely**, whatever `batch_size` says. Fix: `SEQUENCE` ids with a pooled optimizer
(`allocationSize = 50`), `hibernate.jdbc.batch_size=50`, `hibernate.order_inserts=true` (and
`order_updates`), PostgreSQL `reWriteBatchedInserts=true`. 10,000 rows then cost about 200 batches + 200
sequence calls instead of 10,000 round trips. In long loops `flush()` + `clear()` per batch so the
persistence context does not hold every entity. For truly bulk loads use `JdbcTemplate.batchUpdate` or
`COPY`.

### Q19. You turn off open-in-view and get `LazyInitializationException`. Why, and what's the fix? **[run: 03]**

With open-in-view the Hibernate session stays open for the whole HTTP request, so lazy associations
loaded in the controller or in JSON serialization still work (while holding a DB connection through view
rendering and hiding N+1 queries). Turn it off and the session closes when the `@Transactional` service
method returns; a lazy collection touched later has no session. Fix by loading what the use case needs
**inside** the transaction: `JOIN FETCH`, `@EntityGraph`, or map to a DTO / projection in the service.
Do not "fix" it with `FetchType.EAGER` (it makes every query pay) or by putting open-in-view back.

### Q20. One Redis Cluster node sits at 100% CPU while the others are idle. What's going on? **[run: 04]**

The key space is split into 16,384 slots, `slot = CRC16(key) % 16384`, and each slot belongs to exactly one
master. So skew has two usual causes: (1) a **hot key**: every request for it goes to the one node that
owns its slot, however many nodes you add; (2) **hash tags**: keys with `{tenant}` hash only the tag, so a
big tenant's keys all land in one slot. Also check for one huge value or an O(N) command
(`HGETALL`, `KEYS`, `SMEMBERS` on a large set).

Prove it: `redis-cli --hotkeys` (needs an LFU policy), `--bigkeys`, `INFO commandstats`, `MONITOR` briefly.
Fix: an in-process cache (Caffeine) in front of the hot key, split it into N sub-keys (`feed:global#0..15`)
and read a random one, read from replicas (`READONLY`), and use hash tags only where you need multi-key
atomicity, with the tag chosen so it spreads.

## A worked example: answering in 60 seconds under pressure

*"Postgres refuses connections after we scaled to 20 pods."*

> "Each pod has its own Hikari pool, default ten, so 20 pods is 200 connections against a Postgres default
> of 100. I'd confirm with `pg_stat_activity` grouped by application name. The fix is to budget pool size
> as max connections minus reserved over the maximum pod count including rolling-update surge, so about
> four per pod here, and put PgBouncer in transaction mode in front if we need more. Raising
> `max_connections` is the trap: it costs memory per backend and usually slows the database down."

Structure: mechanism, number, proof, fix, trade-off.

## Hands-on drills

1. In `01`, change `ArrayBlockingQueue(20)` to `SynchronousQueue` and predict accepted/rejected counts.
   (`newCachedThreadPool` uses it: one thread per task, up to unbounded.)
2. In `03`, add `noRollbackFor` to the proxy and write a case where a `RuntimeException` still commits.
3. In `04`, change 6 -> 8 partitions to 6 -> 12 and count how many keys move. Predict first: `h % 12` is
   either `h % 6` or `h % 6 + 6`, so about half stay put. Why is a multiple still not safe for ordering?
4. In `04`, make the hot key 5% of traffic: at what share does one node stop being the bottleneck?
5. Write the thread-dump excerpt you would expect for Q2 using `ReentrantLock` instead of `synchronized`.

## The 60-second spoken answer

"For production scenarios I always give mechanism first, then the default or number, then the fix with its
trade-off, then how I would prove it. A pool with an unbounded queue never grows past core, so ten
threads. A transaction rolls back only if the proxy sees a runtime exception, so a swallowed exception or a
checked one commits. Pods times pool size must stay under the database's connection limit. Kafka ordering
is per partition and the partition is a hash modulo the count, so changing the count reshuffles keys. A JWT
is valid until it expires unless you keep state. A probe that fires before startup finishes kills the
pod. Boxed `==` and shared mutable formatters work in tests and fail in production. And Redis Cluster
skew is almost always a hot key or a hash tag."
