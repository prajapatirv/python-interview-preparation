---
id: 03-concurrency
title: Concurrency & Multithreading
focus: Thread safety, executors, CompletableFuture, locks, Java Memory Model
deep_dive: 04
examples: 04_concurrency
---
Interviewers look for: "can you find the race condition", "can you size a pool", "do you know the JMM".

### Q1 [basic] Process vs thread? How do you create a thread?
A process has its own memory; threads inside a process share heap and have their own stack. Prefer submitting a `Runnable`/`Callable` to an `ExecutorService` over `new Thread()`; extend `Thread` only for special cases.

### Q2 [basic] What is the difference between `synchronized` and `volatile`?
`synchronized` gives **mutual exclusion + visibility** (one thread in the block; changes visible after release). `volatile` gives **visibility and ordering only** for one variable - no atomicity, so `count++` on a volatile is still a race. Use `AtomicInteger`/`LongAdder` for counters.

### Q3 [basic] What are the thread states and what does `wait/notify` do?
NEW, RUNNABLE, BLOCKED (waiting for a monitor), WAITING, TIMED_WAITING, TERMINATED. `wait()` releases the monitor and sleeps until `notify()`; always call it in a `while(!condition)` loop (spurious wakeups). In modern code use `BlockingQueue`, `CountDownLatch` or `Condition` instead.

### Q4 [intermediate] What is a race condition vs a deadlock vs a livelock vs starvation?
Race: result depends on timing (check-then-act, `i++`). Deadlock: two threads each hold a lock the other needs. Livelock: threads keep reacting to each other and make no progress. Starvation: a thread never gets the CPU/lock (unfair locks, priority). Fix deadlock by **global lock ordering**, `tryLock(timeout)`, or fewer locks.

### Q5 [intermediate] How do you detect a deadlock in production?
`jcmd <pid> Thread.print` or `jstack` - the dump prints "Found one Java-level deadlock" with the cycle. Take 3 dumps 10 seconds apart to see which threads never move. Also `ThreadMXBean.findDeadlockedThreads()` can be exposed as a health metric.

### Q6 [intermediate] ExecutorService - how do you size a thread pool?
CPU-bound: ~ number of cores (+1). I/O-bound: `cores * (1 + wait/compute)` - e.g. 8 cores, 90% waiting -> ~80. Always use a **bounded queue** and a rejection policy (`CallerRunsPolicy` gives back-pressure); `Executors.newFixedThreadPool` uses an unbounded queue and can cause OOM. Name your threads and export pool metrics (active, queue size, rejected).

### Q7 [intermediate] Runnable vs Callable vs Future vs CompletableFuture?
`Callable` returns a value and can throw. `Future.get()` blocks. `CompletableFuture` chains non-blocking steps:
```java
CompletableFuture.supplyAsync(() -> userSvc.get(id), pool)
  .thenCombine(CompletableFuture.supplyAsync(() -> orderSvc.get(id), pool),
               Profile::new)
  .orTimeout(2, TimeUnit.SECONDS)
  .exceptionally(ex -> Profile.fallback());
```
Pass your own executor - the default is the common pool. Know `allOf`, `anyOf`, `thenCompose` (flatMap) vs `thenApply` (map).

### Q8 [intermediate] ReentrantLock vs synchronized? ReadWriteLock vs StampedLock?
`ReentrantLock` adds `tryLock`, timeouts, interruptibility, fairness and multiple `Condition`s - and must be released in `finally`. `ReadWriteLock` allows many readers or one writer (good for read-heavy). `StampedLock` adds optimistic reads (fastest, not reentrant, easy to misuse).

### Q9 [intermediate] What are CountDownLatch, CyclicBarrier, Semaphore, Phaser?
Latch: wait until N events happen (one-shot). Barrier: N threads wait for each other, reusable. Semaphore: limit concurrent access (e.g. 10 calls to a partner API). Phaser: flexible multi-phase barrier. Example: a `Semaphore(20)` around a rate-limited downstream call.

### Q10 [intermediate] What is the Java Memory Model "happens-before"?
A set of rules that guarantee one thread's write is visible to another: unlock -> later lock of the same monitor, volatile write -> later read, `Thread.start()` -> actions in the thread, thread end -> `join()` return, final fields after safe construction. Without a happens-before edge the compiler/CPU may reorder or cache values.

### Q11 [advanced] Why is double-checked locking broken without `volatile`?
`instance = new Singleton()` is three steps (allocate, construct, publish the reference) and may be reordered, so another thread can see a non-null but half-built object. Declare the field `volatile`, or better use the holder idiom or an `enum` singleton.

### Q12 [advanced] ConcurrentHashMap: what is atomic and what is not?
Single operations (`put`, `putIfAbsent`, `computeIfAbsent`, `merge`) are atomic. A sequence like `if(!map.containsKey(k)) map.put(k,v)` is a race - use `putIfAbsent`. Don't do slow work or modify the map inside `computeIfAbsent` (it holds the bucket lock). `size()` is an estimate under concurrent updates.

### Q13 [advanced] What is ForkJoinPool and work stealing?
A pool where each worker has its own deque; idle workers *steal* tasks from others, which keeps all cores busy for divide-and-conquer jobs (parallel streams, `RecursiveTask`). Don't block inside it.

### Q14 [advanced] ThreadLocal: use, danger and the alternative?
Per-thread storage (user context, MDC). In pooled threads values leak to the next request unless you `remove()` in `finally`. With virtual threads, copies multiply. Use `ScopedValue` (Java 25) or pass context explicitly.

### Q15 [advanced] Explain `@Async` and `@Scheduled` pitfalls in Spring.
`@Async` works only through the proxy (calling it from the same class does nothing); the default executor in older setups is a `SimpleAsyncTaskExecutor` (new thread each time) - define a bounded `ThreadPoolTaskExecutor`. `@Scheduled` runs on a single thread by default and every pod runs it -> use **ShedLock/Quartz cluster** or a leader election so the job runs once.

### Q16 [advanced] How do you make a check-then-act operation safe across multiple pods?
JVM locks don't cross processes. Use a DB constraint/optimistic lock (`@Version`), `SELECT ... FOR UPDATE`, an atomic Redis `SET NX PX` lease, or serialize by partition key in Kafka. Always combine with **idempotency keys** so a retry is harmless.

### Q17 [design] Design a rate limiter for an API (single node, then distributed).
- Single node: token bucket (`tokens`, `refillRate`, `lastRefill`) guarded by a lock or `AtomicLong`; per-key map with eviction (Caffeine).
- Distributed: Redis Lua script doing the token-bucket math atomically, or a gateway (Kong / Spring Cloud Gateway `RequestRateLimiter` / Resilience4j `RateLimiter`).
- Decide: fail-open or fail-closed if Redis is down; return `429` + `Retry-After`; limit by API key, not IP only; export "rejected" metrics.

### Q18 [design] Design a bulk-processing job that calls a slow partner API 1 million times with a limit of 50 calls/second.
Producer reads work in pages -> bounded queue -> N workers (virtual threads or a pool of 50) guarded by a rate limiter (token bucket) -> results written in batches -> failures to a retry/DLQ table with attempt count. Make each call idempotent, store a checkpoint so a restart resumes, add a circuit breaker, and track progress (processed / failed / ETA) as metrics.

### Q19 [intermediate] A service's CPU is at 100%. How do you find the busy thread?
`top -H -p <pid>` shows the hot native thread id -> convert to hex -> find `nid=0x..` in `jstack`/`jcmd Thread.print`. Or use async-profiler / JFR for a flame graph. Typical causes: infinite loop, regex backtracking, GC thrash (check GC logs), lock spinning.

### Q20 [advanced] Explain false sharing and `LongAdder`.
Two threads update different variables that sit on the same CPU cache line, so the cores keep invalidating each other. `LongAdder` spreads increments over several cells and sums them on read - far faster than `AtomicLong` under heavy contention, but `sum()` is not an atomic snapshot.

### Q21 [design] Design an in-process job scheduler with priorities, retries and graceful shutdown.
- **Components:** `PriorityBlockingQueue` of tasks, a bounded `ThreadPoolExecutor`, a `ScheduledExecutorService` for delayed retries with exponential backoff and jitter, a status store.
- **Rules:** cap attempts, make tasks idempotent, give each task a timeout (`Future.get(timeout)` / structured concurrency).
- **Shutdown:** stop accepting, drain with `awaitTermination`, then `shutdownNow()` and persist unfinished work.
- **Failure modes:** starvation of low priority (aging), unbounded queue (OOM) - use a bounded queue with a rejection policy.
