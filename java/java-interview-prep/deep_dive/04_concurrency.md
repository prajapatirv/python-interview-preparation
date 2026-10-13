# Concurrency and multithreading

> **Runnable:** [`01_race_volatile_atomic_locks.java`](../examples/04_concurrency/01_race_volatile_atomic_locks.java) ·
> [`02_thread_pools_and_sizing.java`](../examples/04_concurrency/02_thread_pools_and_sizing.java) ·
> [`03_deadlock_detection_and_fix.java`](../examples/04_concurrency/03_deadlock_detection_and_fix.java)
> **Crib sheet:** [`topics/03-concurrency-multithreading.md`](../topics/03-concurrency-multithreading.md) · **Guide:** Q23–Q25

## What interviewers are actually probing

Whether you can reason about shared state without hand-waving. "Is `count++` atomic?" and "volatile vs synchronized"
are entry questions; the real signal is whether you can size a thread pool from numbers, say what happens when
the queue is full, diagnose a deadlock from a thread dump, and describe the Java Memory Model guarantee in one sentence.

## Must-know points

- `count++` is **read-modify-write** (three steps): not atomic, even on a `volatile` field.
- **Visibility** (one thread sees another's write), **atomicity** and **ordering** are three separate problems. `volatile` gives visibility + ordering for a single variable; `synchronized`/locks give all three for a block; atomics give atomic single-variable updates via CAS.
- **happens-before**: unlock → later lock of the same monitor; volatile write → later volatile read; `Thread.start()` → everything in the thread; thread end → `join()` return.
- `ThreadPoolExecutor` order: core threads → **queue** → extra threads up to max → rejection. An unbounded queue means `maximumPoolSize` is never used.
- Pool sizing: CPU-bound ≈ cores (+1); I/O-bound ≈ cores × (1 + wait/compute); then cap by what downstream can absorb.
- Deadlock needs four conditions; **lock ordering** and **tryLock with timeout** are the two practical cures.

## Interview questions and full answers

### Q1. Is `count++` thread-safe? What are the options?

No. It compiles to load, add, store; two threads can both load the same value and one increment is lost.
Options (example 01 measures them):

| Technique | Correct? | When |
|---|---|---|
| `volatile int` | **No** | flags only |
| `synchronized` / `ReentrantLock` | yes | compound invariants over several fields |
| `AtomicInteger/AtomicLong` (CAS) | yes | a single counter, moderate contention |
| `LongAdder` | yes | very high contention counters/metrics (striped cells; `sum()` is not a snapshot) |
| Confinement (per-thread then merge) | yes | best: no sharing at all |

### Q2. `volatile` versus `synchronized`?

`volatile`: every read sees the latest write and the compiler/CPU may not reorder around it. No mutual exclusion, so check-then-act and `++` are still races. Good for a `stop` flag, a published immutable reference, double-checked locking.
`synchronized`: mutual exclusion **and** a memory barrier on entry/exit; reentrant; the monitor is the object. Prefer `ReentrantLock` when you need `tryLock`, timed or interruptible waits, fairness, or several conditions.

### Q3. Explain the Java Memory Model in simple terms.

Each thread may keep values in registers/caches and the JIT may reorder instructions, so without synchronisation one thread may never see another's write or may see writes out of order.
The JMM defines **happens-before** edges (monitor unlock/lock, volatile write/read, thread start/join, `final` field freeze after constructor). If action A happens-before B, B sees A's effects. No edge, no guarantee.
That's why a non-volatile `boolean running` can make a loop spin forever (example 01 section 2).

### Q4. How does a `ThreadPoolExecutor` decide to create a thread? What are the rejection policies?

1. Fewer than `corePoolSize` threads → start a new thread (even if others are idle).
2. Otherwise → offer to the **queue**.
3. Queue full and threads < `maximumPoolSize` → start an extra thread.
4. Else → **reject**.

Policies: `AbortPolicy` (throws `RejectedExecutionException`), `CallerRunsPolicy` (submitter runs it — natural back-pressure), `DiscardPolicy`, `DiscardOldestPolicy`.
Example 02 section 1 prints exactly this for core 2, max 4, queue 3: 7 accepted, 3 rejected.

### Q5. Why is `Executors.newFixedThreadPool` frowned upon?

It uses an **unbounded `LinkedBlockingQueue`**, so under overload tasks pile up until you get an `OutOfMemoryError`, and rejection never signals back-pressure.
`newCachedThreadPool` has the opposite problem: unbounded **threads**. In production construct `ThreadPoolExecutor` directly with a bounded `ArrayBlockingQueue`, a named `ThreadFactory`, and a deliberate rejection policy; expose its metrics (active, queued, rejected).

### Q6. How would you size a thread pool?

Start from the work: `threads ≈ cores × target utilisation × (1 + wait time / compute time)`.
For a 4-core service where each request computes 10 ms and waits 90 ms on a DB: `4 × (1 + 90/10) = 40`. Then check **Little's law** (`concurrency = throughput × latency`): 200 req/s × 0.25 s = 50 in flight.
Finally cap by downstream limits (DB pool of 20 means 40 threads just queue). Verify with a load test and watch queue depth and rejection rate.

### Q7. What is a deadlock, and how do you find and prevent one?

Two or more threads each hold a lock the other needs. Four necessary conditions: **mutual exclusion, hold-and-wait, no preemption, circular wait**.
Detect: thread dump (`jstack <pid>` / `jcmd <pid> Thread.print`) prints `Found one Java-level deadlock`; programmatically `ThreadMXBean.findDeadlockedThreads()` (example 03).
Prevent: always take locks in a **global order**; `tryLock(timeout)` and back off; keep critical sections small; don't call foreign code under a lock; prefer higher-level constructs (`ConcurrentHashMap`, queues).
Distinguish **livelock** (busy, no progress) and **starvation** (never scheduled).

### Q8. `Runnable` vs `Callable` vs `Future` vs `CompletableFuture`?

`Runnable`: no result, no checked exception. `Callable<V>`: returns a value and may throw. `Future`: handle to the pending result (`get`, `cancel`) that blocks. `CompletableFuture`: composable, non-blocking pipeline. Note `submit(Runnable)` swallows exceptions into the `Future`; with `execute` they reach the thread's uncaught-exception handler — log in both cases.

### Q9. What are `wait/notify`, `Condition`, `BlockingQueue`, `CountDownLatch`, `Semaphore`, `CyclicBarrier`?

- `wait/notify`: low-level monitor signalling; always in a `while` loop (spurious wakeups).
- `BlockingQueue` (`ArrayBlockingQueue`, `LinkedBlockingQueue`): producer/consumer with built-in back-pressure; prefer it to hand-written wait/notify.
- `CountDownLatch`: one-shot "wait for N things" (single use).
- `CyclicBarrier`: N threads wait for each other repeatedly.
- `Semaphore`: bound concurrent access to a resource (DB, partner API) — also the right tool with virtual threads.
- `Phaser`, `Exchanger`: rarer.

### Q10. What is thread confinement and why is it the best concurrency strategy?

If data is touched by only one thread (local variables, `ThreadLocal`, message passing to a single owner) no synchronisation is needed.
Combine with **immutability**: immutable objects are safely shareable. Design services to be stateless singletons whose mutable state lives in the DB, cache or a queue.
`ThreadLocal` caveats: leaks in pooled threads (always `remove()`), and context (MDC, security) **does not propagate** to async tasks.

### Q11. What problems do thread pools plus `ThreadLocal` cause in Spring Boot?

Request-scoped data (correlation id, tenant, `SecurityContext`) is lost when work is submitted to another thread; stale data can leak to the next request on a reused thread if not cleared.
Fix with a `TaskDecorator` (copy and clear MDC/security context), `DelegatingSecurityContextExecutor`, or Micrometer **context-propagation**; with virtual threads prefer `ScopedValue` (preview/final in newer JDKs).

### Q12. Design: process 1M records quickly without exhausting memory or hammering the DB.

Producer reads in **chunks** (cursor/stream, not `findAll`), pushes into a **bounded** `BlockingQueue`; N workers (sized for the DB pool, not for cores) batch-write with JDBC batching; a `CompletionService`/latch collects results; failures go to a dead-letter file/table with the record id.
Back-pressure is the bounded queue; idempotency is a unique key so a restart can safely resume; progress is checkpointed (last processed id) so you never restart from zero.

## A worked example

Run [`02_thread_pools_and_sizing.java`](../examples/04_concurrency/02_thread_pools_and_sizing.java) and read section 1 line by line:
task 6 creates the 3rd thread **only after** the queue holds 3, tasks 8–10 are rejected. Then explain what would differ with a `SynchronousQueue`
(extra threads from task 3, rejection from task 5 with max 4). Run [`03_deadlock_detection_and_fix.java`](../examples/04_concurrency/03_deadlock_detection_and_fix.java)
to see `ThreadMXBean` name the exact lock and owner.

## Hands-on drills

1. Make a bank transfer safe with lock ordering, then with `tryLock`; show the unsafe version failing.
2. Implement a bounded blocking queue with `wait/notify`, then replace it with `ArrayBlockingQueue`.
3. Write a rate limiter (token bucket) with `AtomicLong` + CAS, no locks.
4. Reproduce a `SimpleDateFormat` race, then fix three ways (`ThreadLocal`, `DateTimeFormatter`, confinement).
5. Take a thread dump of a running app and identify blocked, waiting and runnable states (`BLOCKED` vs `WAITING` vs `TIMED_WAITING`).

## The 60-second spoken answer

"Shared mutable state needs visibility, atomicity and ordering. `volatile` gives visibility and ordering for one variable, but `++` isn't atomic,
so I use atomics or locks, and I prefer to avoid sharing at all through immutability and confinement. For pools I build a `ThreadPoolExecutor`
with a bounded queue and an explicit rejection policy, size it from CPU versus wait time and Little's law, and cap it by what the downstream
can take. Deadlocks I diagnose from a thread dump and prevent with lock ordering and `tryLock` timeouts. I also keep in mind that
thread-locals like the correlation id don't cross to other threads without a decorator."
