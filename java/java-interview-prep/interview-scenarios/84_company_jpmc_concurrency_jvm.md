---
id: company-jpmc-concurrency-jvm
title: JPMorgan Chase pack (2/5): concurrency, JVM memory and GC, mid to senior
stack: java
skill: java-core
---
Part of the **JPMorgan Chase Java mid/senior pack** (hub: `../company-chase-travel/README.md`). JPMC candidates report
that technical rounds go deep on **multithreading, `synchronized`, `ConcurrentHashMap`, locks, `CompletableFuture`, memory
management**, and that senior rounds extend concurrency "to distributed systems" and include a **code-review exercise**
on thread safety and performance. This file covers exactly that.

Each answer has a **120-second point-by-point version** (*How I answer it*) and a **60-second answer**.

Levels: **mid** (3-6 yrs) · **senior** (6-10) · **architect** (10+, "expert").

### Q1 [mid] synchronized vs ReentrantLock vs atomic classes: when do you use each?
tags: synchronized, reentrantlock, atomic, cas, locks, thread-safety, jpmc

**Start here: the concepts**
- **Race condition:** two threads read and write shared data at the same time and one update is lost.
- `synchronized`: a built-in lock on an object. Only one thread at a time runs the protected code.
- `ReentrantLock`: a lock object with extra features (timeouts, fairness, interruptible waiting).
- **Atomic classes** (`AtomicLong`, `LongAdder`): lock-free updates using a CPU instruction called **compare-and-swap (CAS)**.

**The live scenario (functional requirement)**
*FR: "Count requests per client for rate limiting, and update an account balance safely when two transfers arrive at the same time."*

**What the interviewer is really checking**
That you pick the lightest tool that is correct, and know the features that make you choose a `Lock` over `synchronized`.

**How I answer it** (120-second answer, point by point)
1. **Simple counter: an atomic class.** `AtomicLong.incrementAndGet()` uses CAS with no lock. Under heavy contention, `LongAdder` is faster because it spreads the count over several cells and adds them up when read.
2. **Several fields that must change together** (balance and last-updated time): `synchronized`. It is simple, the lock is released automatically even on an exception, and the JVM optimises it well.
3. **`ReentrantLock` when I need more:**
   - `tryLock(200, ms)`: give up instead of waiting forever. That is a deadlock defence.
   - `lockInterruptibly()`: a waiting thread can be cancelled.
   - A fairness option, and several `Condition`s (for example, "not full" and "not empty" in a buffer).
   - The rule: always `unlock()` in `finally`.
4. **`ReadWriteLock` / `StampedLock`** when reads far outnumber writes, such as a config or reference-data cache.
5. **Virtual threads note:** before Java 24, blocking inside `synchronized` **pinned** a virtual thread to its carrier thread. Java 24 (JEP 491) fixed that, so on 24+ `synchronized` is fine with virtual threads.
6. **In a real service the balance lives in a database,** so a Java lock only protects one JVM. The real answer there is a database row lock or optimistic locking (see Q10).

**Trade-offs and what can go wrong**
- Locking on `this` or a public object lets outside code take your lock; lock on a `private final Object lock`.
- CAS loops can spin under very high contention; `LongAdder` or a lock may be better.
- Holding any lock during I/O kills throughput.

**Follow-ups to expect**
- *What does "reentrant" mean?* -> The thread holding the lock can enter it again (a recursive call) without deadlocking itself.
- *What is CAS?* -> "Set the value to new only if it is still old", done atomically by the CPU; if it fails, read again and retry.
- *Static vs instance `synchronized`?* -> Static locks the `Class` object, instance locks `this`.

**60-second answer**
"For a simple counter I use an atomic class, or LongAdder under heavy contention: lock-free, using compare-and-swap. When several fields must change together I use synchronized, because it's simple and always released, even on exceptions. I switch to ReentrantLock when I need tryLock with a timeout, interruptible waiting, fairness or multiple conditions, and then I always unlock in finally. For read-heavy data, a ReadWriteLock or StampedLock. Since Java 24, synchronized no longer pins virtual threads. And in a real service a balance is in the database, so the real lock is a row lock or optimistic locking, not a Java lock."

### Q2 [mid] What does volatile do, and what is the happens-before relationship?
tags: volatile, visibility, happens-before, java-memory-model, double-checked-locking, jpmc

**Start here: the concepts**
- Each CPU core can cache values, and the compiler can reorder code. So one thread might **not see** another thread's write.
- `volatile` guarantees **visibility** (a write is seen by the next read) and stops harmful reordering around it. It does **not** make `count++` atomic.
- **Happens-before** is the Java memory model rule that says "if A happens-before B, B sees everything A did".

**The live scenario (functional requirement)**
*FR: "A background poller must stop when the operator flips a kill switch."* The flag was a plain `boolean`. The poller loop never stopped in production because the JIT hoisted the read out of the loop. Making it `volatile` fixed it.

**What the interviewer is really checking**
Visibility vs atomicity, and knowing the main happens-before rules.

**How I answer it** (120-second answer, point by point)
1. **Visibility problem:** without synchronisation, a thread may read a stale cached value forever.
2. **`volatile` gives:** visibility of the latest write, and ordering: everything written *before* a volatile write is visible to a thread that later reads that volatile variable.
3. **`volatile` does not give atomicity:** `volatileCount++` is read-modify-write, three steps. Two threads can still lose updates. Use `AtomicInteger`.
4. **Happens-before rules I name:**
   - Unlocking a monitor happens-before the next lock of the same monitor.
   - A volatile write happens-before the next read of that variable.
   - `Thread.start()` happens-before anything in the started thread; everything in a thread happens-before another thread's `join()` returns.
   - Final fields are visible after the constructor finishes.
   - Tasks submitted to an executor see what was written before submission; `Future.get()` sees the task's writes.
5. **Classic use: double-checked locking** for a lazy singleton needs the field to be `volatile`, otherwise another thread can see a half-constructed object. In practice I use the holder idiom, or a lazily-initialised Spring bean.
6. **Good uses of `volatile`:** stop flags, a reference to an immutable config that is swapped atomically, a status field read by monitoring.

**Trade-offs and what can go wrong**
- Overusing `volatile` gives a false feeling of safety. Compound actions need locks or atomics.
- Visibility bugs don't show up on a laptop and appear under load on many-core servers.

**Follow-ups to expect**
- *Is `long`/`double` assignment atomic?* -> Not guaranteed on 32-bit JVMs unless `volatile`; it is on 64-bit HotSpot in practice.
- *What are lazy constants?* -> A preview API (Java 26-27) for values computed once on first use and then treated as constants by the JIT; an alternative to double-checked locking.

**60-second answer**
"volatile solves visibility, not atomicity. Without it, a thread can keep reading a cached value: I had a kill-switch flag that the poller never saw until we made it volatile. A volatile write happens-before every later read of it, so everything written before it becomes visible too. But volatile count++ still loses updates, because it's read-modify-write; for that I use AtomicInteger. The main happens-before rules are unlock-before-lock, volatile write-before-read, thread start and join, final fields after construction, and executor submission. Double-checked locking needs volatile; I usually just use the holder idiom."

### Q3 [senior] How does ConcurrentHashMap work, and why is it better than a synchronized map?
tags: concurrenthashmap, cas, computeifabsent, merge, synchronizedmap, jpmc

**Start here: the concepts**
- `Collections.synchronizedMap(map)` wraps every method in **one lock**, so only one thread uses the map at a time.
- `ConcurrentHashMap` (CHM) lets many threads read with **no lock** and write to **different buckets** in parallel.

**The live scenario (functional requirement)**
*FR: "Aggregate live trade volume per instrument from 16 consumer threads."* With a synchronized map the threads queued behind one lock and the consumers fell behind. CHM with `merge` removed the contention. A second bug: the old code did `if (!map.containsKey(k)) map.put(k, v)`, which is not atomic even on a thread-safe map.

**What the interviewer is really checking**
The internals at the right depth (Java 8+, not the old segments), and the **atomic compound operations**.

**How I answer it** (120-second answer, point by point)
1. **Reads take no lock.** Fields are volatile, so `get` sees the latest completed write.
2. **Writes (Java 8+):**
   - If the bucket is empty, insert with a **CAS**, no lock at all.
   - If it is not empty, `synchronized` on the **first node of that bucket only**. Writes to different buckets run in parallel.
   - Crowded buckets become trees, as in `HashMap`.
3. **Java 7 used 16 "segments"** (16 locks); Java 8 replaced them with per-bucket locking. Mention it only if asked.
4. **Resizing is cooperative:** threads that write during a resize help move buckets.
5. **The real trap is check-then-act.** `containsKey` then `put` is two calls, and another thread can run between them. Use the atomic methods:
   - `putIfAbsent`, `computeIfAbsent(k, key -> load(key))`, `compute`, and `merge(k, 1L, Long::sum)` for counters.
6. **No `null` keys or values,** because `get` returning `null` must mean "absent" without ambiguity.
7. **Iterators are weakly consistent:** they never throw `ConcurrentModificationException`, and may or may not show concurrent changes. `size()` is an estimate under concurrent writes.

**Trade-offs and what can go wrong**
- The function in `computeIfAbsent` runs **while holding the bucket lock**. Never do slow I/O there, and never modify the same map inside it (this can throw or deadlock).
- CHM makes single operations atomic, not a sequence of them. For multi-key invariants you still need a lock or a different design.
- For a bounded cache with eviction, use Caffeine, not a bare CHM.

**Follow-ups to expect**
- *`Hashtable` vs CHM?* -> `Hashtable` locks the whole table for every call, like a synchronized map.
- *How do you count words in parallel?* -> `map.merge(word, 1L, Long::sum)`, or `LongAdder` values via `computeIfAbsent(k, x -> new LongAdder()).increment()`.

**60-second answer**
"A synchronized map has one lock, so every thread queues. ConcurrentHashMap reads without locking, and since Java 8 it writes with a CAS into an empty bucket, or by locking only the first node of the bucket, so writes to different buckets run in parallel. Resizes are shared between threads. The bug I watch for is check-then-act: containsKey then put isn't atomic even on a concurrent map, so I use computeIfAbsent, compute or merge. For example, merge with Long::sum for counters. Its iterators never throw ConcurrentModificationException. I keep the function inside computeIfAbsent fast, because it runs under the bucket lock."

### Q4 [senior] How do you size a thread pool, and what goes wrong with Executors.newFixedThreadPool?
tags: executorservice, threadpoolexecutor, thread-pool-sizing, rejection-policy, backpressure, jpmc

**Start here: the concepts**
- A **thread pool** reuses a fixed set of threads to run tasks from a **queue**, instead of creating a thread per task.
- `ThreadPoolExecutor` has a core size, a max size, a queue and a **rejection policy** (what to do when everything is full).

**The live scenario (functional requirement)**
*FR: "Enrich each incoming trade by calling two reference-data services."* The team used `Executors.newFixedThreadPool(10)`. During a slowdown of the reference service, the **unbounded** queue grew to millions of tasks and the JVM died with `OutOfMemoryError`.

**What the interviewer is really checking**
That you size pools from the workload, use bounded queues, and think about backpressure and monitoring.

**How I answer it** (120-second answer, point by point)
1. **CPU-bound work:** about the number of cores (`availableProcessors()`, which respects container CPU limits on modern JDKs). More threads only add context switching.
2. **I/O-bound work:** threads ≈ cores × (1 + wait time / compute time). For example 4 cores, 90 ms waiting and 10 ms computing: 4 × 10 = 40 threads. Then I **verify with a load test**.
3. **Little's Law cross-check:** concurrency needed = throughput × latency. 200 requests/s × 0.1 s = 20 tasks in flight.
4. **Why the `Executors` factories are risky:**
   - `newFixedThreadPool` and `newSingleThreadExecutor` use an **unbounded** `LinkedBlockingQueue`, which grows until OOM.
   - `newCachedThreadPool` can create **unlimited threads**.
5. **What I do:** build a `ThreadPoolExecutor` with a **bounded queue**, named threads, and a deliberate rejection policy:
   - `CallerRunsPolicy` slows the producer down. That is natural backpressure.
   - `AbortPolicy` fails fast, so the API can return 503.
6. **Separate pools (bulkheads)** for different downstreams, so one slow service cannot use up every thread.
7. **Shutdown:** `shutdown()` then `awaitTermination`, so in-flight work finishes on deploys.
8. **On Java 21+, for blocking I/O,** virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`) remove most sizing work. I then limit concurrency to the downstream with a `Semaphore`.

**Trade-offs and what can go wrong**
- A pool far too large overloads the downstream and the database connection pool. The thread count must match the connection pool size.
- `ThreadLocal` values leak between tasks on pooled threads; clean them up (for example the MDC).
- Exceptions in `execute()` tasks kill the thread silently; with `submit()` they hide inside the `Future`.

**Follow-ups to expect**
- *What metrics do you watch?* -> Active threads, queue size, rejected count, task time. Micrometer's `ExecutorServiceMetrics` exposes them.
- *Core vs max size?* -> Threads above core are only created when the queue is **full**, a common surprise.

**60-second answer**
"For CPU-bound work I size the pool to the number of cores. For I/O-bound work I use cores times one plus wait over compute, cross-check with Little's Law, and confirm with a load test. I avoid the Executors factory methods: newFixedThreadPool has an unbounded queue, and I've seen it fill up during a downstream slowdown and kill the JVM with an OutOfMemoryError. So I create a ThreadPoolExecutor with a bounded queue, named threads, and a rejection policy: CallerRuns for backpressure, or Abort so the API returns 503. I use separate pools per downstream as bulkheads, and monitor queue size and rejections. On Java 21, virtual threads plus a semaphore often replace all of this for I/O."

### Q5 [senior] CompletableFuture: how do you call three services in parallel with timeouts and error handling?
tags: completablefuture, thenapply, thencompose, allof, exceptionally, timeout, async, jpmc

**Start here: the concepts**
- A `CompletableFuture` is a result that will arrive later, which you can chain steps onto.
- `thenApply` transforms the result. `thenCompose` chains another async call (it flattens, like `flatMap`). `thenCombine` joins two results.
- `allOf` waits for many. `exceptionally`/`handle` deal with failures.

**The live scenario (functional requirement)**
*FR: "The client dashboard shows positions, cash balance and alerts. Each comes from a different service. The page must load in under 800 ms, and if alerts are down, still show the rest."*

**What the interviewer is really checking**
Correct composition, timeouts, partial failure handling, and knowing which thread pool runs your code. Candidates report CompletableFuture discussions in JPMC Java rounds.

**How I answer it** (120-second answer, point by point)
1. **Start all three at once** with `supplyAsync(() -> client.positions(id), ioPool)`. **Always pass my own executor.** The default is the ForkJoin common pool, which is sized for CPU work and shared with parallel streams.
2. **Timeout each call:** `.orTimeout(500, MILLISECONDS)` (Java 9). For optional parts, use `.completeOnTimeout(fallback, 300, MILLISECONDS)`.
3. **Fallback per call:** `.exceptionally(ex -> Alerts.unavailable())` for the optional alerts. Positions are required, so their failure fails the request.
4. **Combine:** `CompletableFuture.allOf(p, c, a).thenApply(v -> new Dashboard(p.join(), c.join(), a.join()))`. After `allOf`, `join()` does not block.
5. **Know the methods:**
   - `thenApply` (sync transform) vs `thenCompose` (the next step is also async: avoids `CompletableFuture<CompletableFuture<T>>`).
   - `handle` sees the result *or* the exception; `whenComplete` is for side effects such as logging.
   - The `...Async` variants run the next step on an executor instead of the completing thread.
6. **Exceptions arrive wrapped** in `CompletionException`; unwrap `getCause()` before mapping to an error response.
7. **Context:** MDC and trace ids don't follow threads automatically; use a context-propagating executor (Micrometer context-propagation).
8. **Modern option (Java 21+):** virtual threads with plain blocking calls are often simpler to read; structured concurrency is still in preview in Java 27.

**Trade-offs and what can go wrong**
- Calling `.get()` or `.join()` too early makes it sequential again.
- A timeout does not cancel the underlying HTTP call; also set client-level timeouts.
- An exception that nobody handles is silently lost in the future.

**Follow-ups to expect**
- *`thenApply` vs `thenApplyAsync`?* -> Non-async runs on whichever thread completes the previous stage; Async moves it to an executor.
- *`anyOf`?* -> Completes with the first result; useful for hedged requests to replicas.

**60-second answer**
"I start all three calls at once with supplyAsync on my own I/O executor, never the common pool, which is shared and sized for CPU work. Each call gets orTimeout. The optional alerts call gets completeOnTimeout or exceptionally with a fallback, so the page still loads without it, while a failure in positions fails the request. Then allOf, and thenApply to build the dashboard; after allOf, join doesn't block. I use thenCompose when the next step is itself async, and I unwrap CompletionException in error handling. I also set HTTP client timeouts, because orTimeout doesn't cancel the socket. On Java 21, virtual threads with blocking code are often simpler."

### Q6 [senior] What is a deadlock? How do you find one in production and prevent it?
tags: deadlock, jstack, thread-dump, lock-ordering, trylock, livelock, starvation, jpmc

**Start here: the concepts**
- **Deadlock:** thread A holds lock 1 and waits for lock 2, while thread B holds lock 2 and waits for lock 1. Both wait forever.
- It needs four conditions: mutual exclusion, hold-and-wait, no pre-emption, circular wait. Break any one and there is no deadlock.

**The live scenario (functional requirement)**
*FR: "Transfer money between two accounts, locking both."* `transfer(a, b)` locked `a` then `b`, and a simultaneous `transfer(b, a)` locked `b` then `a`. Under load, two request threads hung forever and the pool slowly filled with stuck threads.

**What the interviewer is really checking**
The cause, the production diagnosis steps, and design-level prevention.

**How I answer it** (120-second answer, point by point)
1. **Symptoms:** throughput drops, CPU is *low* (threads are waiting, not working), requests time out, and the thread pool's active count stays at its maximum.
2. **Diagnose:** take a thread dump with `jcmd <pid> Thread.print` or `jstack <pid>`, two or three times a few seconds apart. The JVM prints **"Found one Java-level deadlock"** with the two threads and the locks they hold. JFR and APM tools also show blocked threads.
3. **Prevent with a global lock order:** always lock the account with the smaller id first. Then a circular wait cannot happen.
4. **Prevent with timeouts:** `tryLock(timeout)`; on failure, release everything, back off and retry.
5. **Prevent by design:** hold one lock at a time; keep critical sections short; never call external code or I/O while holding a lock.
6. **Database deadlocks are more common in real services:** two transactions update the same rows in different orders. The database detects it and kills one (PostgreSQL error `40P01`). The fixes are the same: a consistent update order, short transactions, and a retry on that error.
7. **Related terms:** *livelock* (threads keep reacting to each other and make no progress); *starvation* (a thread never gets the lock; fair locks help).

**Trade-offs and what can go wrong**
- Fair locks reduce starvation but lower throughput.
- Retries after a timeout need jitter, or the same threads collide again.

**Follow-ups to expect**
- *Can a deadlock happen with one lock?* -> Yes, with non-reentrant locks, or with a thread waiting on a future that needs the same full pool (pool-induced deadlock).
- *How do you detect it from code?* -> `ThreadMXBean.findDeadlockedThreads()`, which you can expose as a health indicator.

**60-second answer**
"A deadlock is two threads each holding a lock the other needs, so both wait forever. A classic case is transfer(a, b) running at the same time as transfer(b, a). In production you see low CPU, timeouts and a pool full of stuck threads. I take two or three thread dumps with jcmd or jstack, and the JVM literally prints 'Found one Java-level deadlock' with the locks involved. To prevent it, I lock in a global order, for example the smaller account id first, use tryLock with a timeout, and never do I/O while holding a lock. In databases it's the same idea: a consistent update order, short transactions, and a retry on the deadlock error."

### Q7 [senior] What are virtual threads, when do they help, and what are the pitfalls?
tags: virtual-threads, java-21, project-loom, pinning, carrier-thread, semaphore, jpmc

**Start here: the concepts**
- A **platform thread** is a wrapper around an operating-system thread: about 1 MB of stack reserved and expensive to create. A few thousand is a practical limit.
- A **virtual thread** (final in Java 21) is a lightweight thread managed by the JVM. When it blocks on I/O, the JVM *unmounts* it and the underlying **carrier** thread runs other work. You can have millions.

**The live scenario (functional requirement)**
*FR: "A statement service calls four slow downstream APIs per request and must handle 5x more concurrent users without more servers."* With 200 Tomcat threads it hit a ceiling at 200 concurrent requests, while CPU was at 15%. With `spring.threads.virtual.enabled=true` (Spring Boot 3.2+), concurrency was no longer limited by threads.

**What the interviewer is really checking**
That you know they fix **I/O-bound** scalability, not CPU work, and know the pitfalls (pinning, `ThreadLocal`, the next bottleneck).

**How I answer it** (120-second answer, point by point)
1. **What they solve:** thread-per-request code that mostly *waits*. You keep simple blocking code (JDBC, `RestClient`) and get scalability close to reactive code.
2. **What they don't solve:** CPU-bound work. There are still only as many cores; virtual threads do not make computation faster.
3. **How to use them:** `Executors.newVirtualThreadPerTaskExecutor()`, `Thread.ofVirtual().start(...)`, or one property in Spring Boot 3.2+. **Never pool them**: create one per task.
4. **Pitfalls:**
   - **Pinning:** before Java 24, blocking inside `synchronized` (or native code) kept the carrier thread busy. Java 24 (JEP 491) fixed `synchronized`, so on 21 prefer `ReentrantLock` in hot paths. Find pinning with the JFR event `jdk.VirtualThreadPinned`.
   - **The bottleneck moves:** 10,000 concurrent requests now hit a 20-connection database pool or a downstream rate limit. Limit concurrency with a `Semaphore` or bulkhead and keep pool timeouts.
   - **`ThreadLocal`** caches (one expensive object per thread) multiply with millions of threads. Prefer **scoped values** (final in Java 25) for passing context.
5. **When I choose them:** new blocking-style services on Java 21+, especially with many slow downstream calls. I keep reactive (WebFlux) where it already exists or where streaming and backpressure are core to the design.

**Trade-offs and what can go wrong**
- Thread dumps can contain huge numbers of threads; use `jcmd <pid> Thread.dump_to_file -format=json`.
- Libraries that relied on a small fixed thread count (some connection pools, `ThreadLocal`-heavy frameworks) need checking.

**Follow-ups to expect**
- *Are virtual threads faster?* -> Not per request; they raise *throughput* under concurrency. Latency is roughly the same.
- *Virtual threads vs WebFlux?* -> Similar scalability for I/O, much simpler code and stack traces; reactive still wins for streaming with backpressure.
- *What is structured concurrency?* -> Treat a group of subtasks as one unit with shared cancellation; still a preview (seventh) in Java 27.

**60-second answer**
"Virtual threads, final in Java 21, are lightweight threads managed by the JVM. When one blocks on I/O, it's unmounted and the carrier thread runs something else, so you can have millions. They help I/O-bound, thread-per-request services: we hit a 200-thread ceiling at 15% CPU, and one Spring Boot property removed it. They don't speed up CPU-bound work, and you never pool them. Pitfalls: pinning inside synchronized before Java 24, so I'd use ReentrantLock on 21. The bottleneck moves to the DB pool or downstream, so I add a semaphore. And ThreadLocal caches multiply, which is where scoped values come in."

### Q8 [mid] Explain JVM memory areas, and the different kinds of OutOfMemoryError.
tags: jvm-memory, heap, stack, metaspace, outofmemoryerror, stackoverflowerror, jpmc

**Start here: the concepts**
- **Heap:** where objects live; shared by all threads; cleaned by the garbage collector.
- **Stack:** one per thread; holds method frames, local variables and references.
- **Metaspace:** class metadata (since Java 8; it replaced PermGen), in native memory.
- Others: the code cache (compiled code), thread stacks, and direct buffers (off-heap, used by NIO and Netty).

**The live scenario (functional requirement)**
*FR: "A report service runs in a 2 GB container."* It was OOM-killed by Kubernetes even though `-Xmx` was 2 GB. The heap was not the only memory the JVM used: metaspace, thread stacks and direct buffers pushed the process past the container limit.

**What the interviewer is really checking**
That you know the areas, can read each OOM message, and size a JVM inside a container.

**How I answer it** (120-second answer, point by point)
1. **Heap** is split into young generation (new objects; most die young) and old generation (survivors). Size it with `-Xms`/`-Xmx`, or in containers with `-XX:MaxRAMPercentage=75`.
2. **Stack:** each thread has its own. Deep recursion gives `StackOverflowError` (an error, not an OOM). Size it with `-Xss`.
3. **The OOM messages and what they mean:**
   - `Java heap space`: too many live objects (a leak or an undersized heap).
   - `GC overhead limit exceeded`: the JVM is almost only collecting garbage and freeing little.
   - `Metaspace`: too many classes, usually a classloader leak from redeploys or runtime-generated proxies.
   - `unable to create native thread`: an OS or container thread limit, or a thread leak.
   - `Direct buffer memory`: off-heap NIO buffers; limit with `-XX:MaxDirectMemorySize`.
4. **Container sizing:** total ≈ heap + metaspace + threads × stack + code cache + direct memory + GC overhead. So set the heap to around 70-75% of the container limit, not 100%.
5. **Always enable** `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=...` so you have evidence after a crash.
6. **Kubernetes exit code 137 means the OS killed the process.** If no Java OOM appears in the logs, the problem is non-heap or total memory.

**Trade-offs and what can go wrong**
- A bigger heap means fewer GCs but longer pauses with some collectors, and longer heap dumps.
- Setting `-Xms` equal to `-Xmx` avoids resizing; common in containers.

**Follow-ups to expect**
- *How do you see native memory?* -> `-XX:NativeMemoryTracking=summary` then `jcmd <pid> VM.native_memory summary`.
- *Where do static fields live?* -> In the heap (with the `Class` object) since Java 8.
- *What does compact object headers change?* -> Object headers shrink from 12 to 8 bytes; on by default in Java 27 (JEP 534), often 10-20% less heap.

**60-second answer**
"The heap holds objects and is split into young and old generations; each thread has its own stack for frames and locals; metaspace holds class metadata in native memory; then there's the code cache and direct buffers. Each OutOfMemoryError message points at a different area: heap space means too many live objects, Metaspace usually means a classloader leak, unable to create native thread means too many threads, Direct buffer memory means off-heap NIO. In containers I set MaxRAMPercentage around 75, because the JVM uses more than the heap. A pod OOM-killed with exit code 137 and no Java error is usually non-heap memory. And I always turn on heap dumps on OOM."

### Q9 [senior] How do you choose and tune a garbage collector for a low-latency service?
tags: garbage-collection, g1, zgc, parallel-gc, shenandoah, gc-tuning, latency, jpmc

**Start here: the concepts**
- The **garbage collector** frees memory used by objects nobody references any more. While it works, it may **pause** the application ("stop-the-world").
- **G1:** the default (and, from Java 27, the default everywhere). It balances throughput and pause time, aiming for about 200 ms pauses.
- **ZGC:** very short pauses (under a millisecond), almost independent of heap size. Generational since Java 21, and the only mode since Java 24.
- **Parallel GC:** best raw throughput for batch jobs, with longer pauses.

**The live scenario (functional requirement)**
*FR: "The pricing API's p99 latency must be under 50 ms."* Graphs showed regular 300 ms spikes. The GC logs showed G1 mixed-collection pauses on a 24 GB heap. Moving to Generational ZGC brought GC pauses under 1 ms, and p99 stabilised.

**What the interviewer is really checking**
Evidence-driven tuning: measure first, choose the collector by goal, and fix allocation before turning knobs.

**How I answer it** (120-second answer, point by point)
1. **Measure first:** turn on GC logging (`-Xlog:gc*:file=gc.log`) and check whether latency spikes line up with GC pauses. Use JFR or GCeasy for analysis.
2. **Choose by goal:**
   - Most web services: **G1** (default), maybe with `-XX:MaxGCPauseMillis` adjusted.
   - Strict tail latency or large heaps: **ZGC** (`-XX:+UseZGC`). It uses a bit more CPU and memory.
   - Batch and throughput jobs: **Parallel GC**.
   - Shenandoah (Red Hat builds and others) is another low-pause option, generational since Java 25.
3. **Size the heap properly:** too small means constant GC; let the collector have headroom (for example a live set at 50-60% of the heap).
4. **Reduce allocation:** the cheapest GC is the one that doesn't happen. Find allocation hot spots with JFR (for example boxing, building huge strings, loading whole result sets).
5. **Container facts:** the JVM reads container limits. Before Java 27, with fewer than 2 CPUs or under about 1.8 GB of memory, the JVM silently chose **Serial GC**; Java 27 (JEP 523) makes G1 the default everywhere. On older JDKs I set the collector explicitly.
6. **Compact object headers** (product in 25, default in 27) reduce heap use, which means fewer GCs.
7. **Validate with a load test** at the real peak, and compare p99 and CPU before and after.

**Trade-offs and what can go wrong**
- Copying random flags from blogs. Most G1 tuning is just heap size and the pause goal.
- ZGC trades extra CPU and memory for latency. On a CPU-starved pod it can hurt.
- Calling `System.gc()` in code causes full GCs; remove it.

**Follow-ups to expect**
- *Why do most objects die young?* -> The "weak generational hypothesis"; this is why young collection is cheap and frequent.
- *What is a full GC in G1?* -> A fallback when concurrent marking can't keep up; a sign of a too-small heap or allocation spikes.

**60-second answer**
"I start with evidence: GC logs and JFR, to confirm the latency spikes actually line up with GC pauses. Then I choose by goal. G1 is the default and right for most services. ZGC, which is generational since Java 21, gives sub-millisecond pauses for strict p99 targets or large heaps, at some CPU cost. Parallel GC is for batch throughput. Before touching flags I size the heap with headroom and cut allocation, because fewer objects means fewer GCs. In containers, older JDKs silently picked Serial GC on small pods; Java 27 makes G1 the default everywhere. I validate every change with a peak load test, comparing p99 and CPU."

### Q10 [senior] Concurrency in Java vs in a distributed system: how do you stop two instances double-processing the same thing?
tags: distributed-concurrency, optimistic-locking, pessimistic-locking, idempotency, distributed-lock, jpmc

**Start here: the concepts**
- A Java lock (`synchronized`, `ReentrantLock`) only works **inside one JVM**. With 6 pods, there are 6 separate locks.
- In a distributed system the shared state is in a **database**, a **cache** or a **message log**, so concurrency control has to live there.

**The live scenario (functional requirement)**
*FR: "A payment must be debited exactly once, even when the client retries and two pods receive the same request."* A `synchronized` block passed every test on one instance and failed in production with 4 replicas: two pods debited the same payment.

**What the interviewer is really checking**
A JPMC candidate reported exactly this follow-up: "concurrency control in Java, extended to distributed systems". They want you to move the guarantee to the right place.

**How I answer it** (120-second answer, point by point)
1. **Idempotency key first:** the client sends an `Idempotency-Key`. I store it with a **unique constraint**. The second insert fails, so I return the first result instead of debiting again.
2. **Optimistic locking for updates:** a `@Version` column. `UPDATE ... SET balance = ?, version = version + 1 WHERE id = ? AND version = ?`. If 0 rows change, someone else won; reload and retry. Best when conflicts are rare.
3. **Pessimistic locking when conflicts are common:** `SELECT ... FOR UPDATE` (JPA `PESSIMISTIC_WRITE`) inside a short transaction, with a lock timeout.
4. **Atomic conditional updates:** `UPDATE account SET balance = balance - :amt WHERE id = :id AND balance >= :amt` does the check and the change in one statement.
5. **Distributed locks** (Redis with fencing tokens, a DB advisory lock, ShedLock for scheduled jobs) only when there is no natural row to lock, such as "only one pod runs the nightly job". A lock can expire while the holder is still working, so I use **fencing tokens** and keep the operation idempotent anyway.
6. **With Kafka:** partition by the account id, so all events for one account are processed by one consumer in order. That removes most contention, and an idempotent consumer handles redelivery.
7. **Summary:** in-JVM locks protect memory; **databases, unique keys, versions and partitioning** protect business data.

**Trade-offs and what can go wrong**
- Optimistic locking under heavy contention means many retries; switch to pessimistic or partitioning.
- Long pessimistic transactions block other requests and can deadlock.
- A Redis lock without fencing can let two holders write after a GC pause or network partition.

**Follow-ups to expect**
- *What isolation level would you use?* -> READ COMMITTED (the PostgreSQL default) plus explicit locking or versioning; SERIALIZABLE only where needed, with retries.
- *How does `@Version` surface in Spring?* -> `ObjectOptimisticLockingFailureException`; retry it, or return 409.

**60-second answer**
"A Java lock only protects one JVM: with four pods there are four locks, and I've seen a synchronized block let two pods debit the same payment. So I move the guarantee to shared state. First, an idempotency key with a unique constraint, so a retry returns the stored result. For updates, optimistic locking with a version column when conflicts are rare, or SELECT FOR UPDATE with a short transaction when they're common. Or a single conditional UPDATE that checks and changes together. For events, I partition Kafka by account id so one consumer owns each account. Distributed locks only for things like a single scheduled job, with fencing tokens."

### Q11 [senior] Code review round: what is wrong with this service class?
tags: code-review, thread-safety, simpledateformat, singleton-state, resource-leak, performance, jpmc

**Start here: the concepts**
- JPMC candidates report a **pull-request review** exercise in the final loop: you read code and find bugs in thread safety, performance and design.
- Spring beans are **singletons by default**: one instance serves every request thread at the same time.

**The live scenario (functional requirement)**
*FR: "Review this PR before it ships."* A simplified version of the code they show:

```java
@Service
public class TradeService {
    private SimpleDateFormat fmt = new SimpleDateFormat("yyyy-MM-dd");
    private List<Trade> processed = new ArrayList<>();
    private Map<String, Rate> cache = new HashMap<>();

    public String book(Trade t) {
        Connection c = dataSource.getConnection();
        if (!cache.containsKey(t.ccy())) cache.put(t.ccy(), rateClient.get(t.ccy()));
        processed.add(t);
        log.info("Booked " + t);
        return fmt.format(t.date());
    }
}
```

**What the interviewer is really checking**
A structured review: correctness first (threads, resources), then performance, then design, each with a concrete fix.

**How I answer it** (120-second answer, point by point)
1. **Shared mutable state in a singleton:** `processed` and `cache` are mutated by every request thread at once. `ArrayList` and `HashMap` are not thread-safe, so updates can be lost or the map corrupted. `processed` also grows forever: a **memory leak**.
   - Fix: remove `processed` (log or persist instead), and use `ConcurrentHashMap.computeIfAbsent`, or better a bounded cache (Caffeine with a TTL) for rates.
2. **`SimpleDateFormat` is not thread-safe:** shared, it gives wrong dates under load. Fix: `DateTimeFormatter` (immutable) and `java.time` types.
3. **Connection leak:** `getConnection()` is never closed, so the pool runs dry after N calls. Fix: try-with-resources, or better, let Spring manage it (`JdbcTemplate`/JPA).
4. **Check-then-act race:** `containsKey` then `put` lets several threads call the rate service. `computeIfAbsent` fixes it.
5. **A remote call on the request path with no timeout:** the rate client needs a timeout, and possibly a circuit breaker and a fallback.
6. **Logging:** string concatenation always builds the message; use `log.info("Booked {}", t.id())`, and don't log the whole trade (it may contain sensitive data).
7. **Design:** fields should be `private final` and constructor-injected; `book` has no transaction boundary or validation; there are no tests.
8. **How I report it:** blocking issues first (thread safety, leak), then important (timeouts), then nits, each with a suggested fix. Be kind in tone.

**Trade-offs and what can go wrong**
- Spending the whole time on style nits and missing the concurrency bug is the common failure in this round.
- Proposing a big rewrite in a review: suggest the smallest safe fix and a follow-up ticket.

**Follow-ups to expect**
- *How would you test the race?* -> A concurrency test with many threads and a `CountDownLatch` start gate, or jcstress for low-level cases.
- *Is `DateTimeFormatter` safe to share?* -> Yes, it is immutable and thread-safe.

**60-second answer**
"First I look for correctness. The bean is a singleton, so the ArrayList and HashMap fields are shared by every request thread. They aren't thread-safe, and the list grows forever, which is a memory leak. SimpleDateFormat isn't thread-safe either; I'd use DateTimeFormatter. The connection is never closed, so the pool will run dry; try-with-resources or let Spring manage it. containsKey-then-put is a race: computeIfAbsent, or a bounded Caffeine cache. The rate call needs a timeout. Then smaller items: parameterised logging without sensitive data, final constructor-injected fields, tests. I'd list blockers first, each with a concrete fix."
