---
id: reported-core-java-senior
title: Reported rounds, senior core Java (Deloitte, Mastercard): proxies, custom collectors, locks, concurrency failures
stack: java
skill: java-core
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`, which maps every reported
question to its answer). This bank holds only the gaps; questions the repo already answers, such as PECS (bank 83 Q7)
and Java modules (bank 20 Q28), are linked from the hub rather than repeated.

Code for Q1-Q3 ran and passed in `examples/21_coding_interview/08_reported_rounds_coding_and_internals.java`.
The production questions (Q5, Q6) use the three-tier shape: short answer, technical detail, deep dive.

### Q1 [senior] How do reflection and dynamic proxies work internally?
tags: reflection, dynamic-proxy, invocationhandler, cglib, spring-aop, transactional, self-invocation, deloitte, reported-rounds

**Start here: the concepts**
- **Reflection** lets code inspect and call classes, methods and fields by looking them up at run time, using the metadata the JVM loaded with each class.
- A **dynamic proxy** is a class **generated at run time** that implements your interface and sends every call to one handler.
- Spring's `@Transactional`, `@Cacheable` and `@Async` are built on proxies.

**The live scenario (functional requirement)**
*FR: "Every service call must start a transaction, commit on success and roll back on failure, without writing that in each method."* This is what `@Transactional` does, and a proxy is how.

**What the interviewer is really checking**
Whether you can explain the mechanism behind Spring, and predict the bugs that follow from it.

**How I answer it** (120-second answer, point by point)
1. **Class metadata:** when a class loads, the JVM keeps its methods and fields, and `Class<?>` exposes them. `Method.invoke` calls one by name.
2. **Reflection's speed:** since Java 18 (JEP 416), core reflection is built on method handles. It starts slowly and gets optimised, and is now close to a direct call once hot. Finding a `Method` is the slow part, so frameworks cache lookups.
3. **Generating a proxy:** `Proxy.newProxyInstance(loader, interfaces, handler)` creates a class at run time, like `$Proxy12`, that implements the interfaces. Each method body calls `handler.invoke(proxy, method, args)`.
4. **Handler:** the place for around-advice:

```java
InvocationHandler h = (proxy, method, args) -> {
    log.add("begin");
    try { Object r = method.invoke(target, args); log.add("commit"); return r; }
    catch (InvocationTargetException e) { log.add("rollback"); throw e.getCause(); }
};
```

5. **Unwrap the exception:** `method.invoke` wraps the target's exception in `InvocationTargetException`. Forget `getCause()` and callers see a confusing wrapper.
6. **JDK proxy vs CGLIB:** the JDK proxy needs an interface. CGLIB, or ByteBuddy, generates a **subclass**, so it works without one, and it can't override `final` methods or classes. Spring Boot defaults to subclass proxies.

**Trade-offs and what can go wrong**
- **Self-invocation:** `this.save()` inside the same bean bypasses the proxy, so `@Transactional` silently does nothing. This is the most common real bug that follows from this topic.
- `final` and `private` methods can't be intercepted by a subclass proxy.
- Since Java 16 (JEP 396), deep reflection into JDK internals fails unless opened with `--add-opens`.
- GraalVM native images need reflection declared ahead of time, because the closed-world build can't see it.

**Follow-ups to expect**
- *Why does `@Transactional` on a private method do nothing?* -> The proxy can't override it, so the advice never runs.
- *Who else uses reflection?* -> Jackson, JPA/Hibernate, JUnit, and Spring's dependency injection.

**60-second answer**
"Reflection reads the class metadata the JVM holds and can call a method by name. A dynamic proxy is a class generated at run time that implements your interface and sends every call to one InvocationHandler, which can run code before and after the real method. That's exactly how @Transactional works: begin, invoke, commit, or roll back on exception. The JDK proxy needs an interface, and CGLIB generates a subclass instead, so it can't handle final methods. The classic bug is self-invocation: calling this.save skips the proxy, so the transaction never starts."

### Q2 [senior] Build a custom Java Collector that supports parallel processing without wrong results or data races.
tags: collector, parallel-streams, combiner, accumulator, characteristics, thread-confinement, deloitte, reported-rounds

**Start here: the concepts**
- A `Collector` has four functions: **supplier** (new container), **accumulator** (add one element), **combiner** (merge two containers) and **finisher** (final result).
- In parallel, each worker gets its **own** container, so the accumulator needs no locks.

**The live scenario (functional requirement)**
*FR: "Compute count, sum and max per batch over a million readings in one pass, in parallel."*

**What the interviewer is really checking**
Whether you understand why collectors are safe by design, and what breaks that safety.

**How I answer it** (120-second answer, point by point)
1. Write a plain, non-thread-safe container. That's deliberate:

```java
static final class Stats {
    long count; double sum; double max = Double.NEGATIVE_INFINITY;
    void add(double v) { count++; sum += v; max = Math.max(max, v); }
    Stats merge(Stats o) { count += o.count; sum += o.sum; max = Math.max(max, o.max); return this; }
}
Collector<Double, Stats, Stats> c = Collector.of(Stats::new, Stats::add, Stats::merge,
        Collector.Characteristics.UNORDERED, Collector.Characteristics.IDENTITY_FINISH);
```

2. **Why no data race:** the framework gives each worker a container from the supplier. Nobody shares one until the combiner runs, and the framework runs combiners without overlap.
3. **The correctness rules:** the supplier must return a **new** object each time. The combiner must be **associative**, and an empty container must act as an identity. Merging then gives the same result however the data was split.
4. I ran this over a million values: count and max matched exactly between sequential and parallel, and so did the sum on that data. Note that floating-point sums aren't strictly associative, so `DoubleSummaryStatistics` uses compensated summation.
5. **Characteristics:** `IDENTITY_FINISH` skips the finisher. `UNORDERED` means order doesn't matter, which allows optimisations. `CONCURRENT` means one shared container, which must then be thread-safe. I'd avoid it unless contention is measured to be worthwhile.

**Trade-offs and what can go wrong**
- Returning a shared singleton from the supplier, or capturing an external list in the accumulator, brings the data race straight back.
- A combiner that just returns the left side loses data, but only in parallel, so sequential tests pass.
- Test by running sequential and parallel on the same data and comparing, with `Collectors` for reference.

**Follow-ups to expect**
- *Which built-in does this?* -> `summarizingDouble`.
- *Combine two collectors?* -> `Collectors.teeing`.

**60-second answer**
"A Collector has a supplier, accumulator, combiner and finisher. The key idea is thread confinement: in parallel, each worker gets its own container from the supplier, so the accumulator can be plain unsynchronised code, and containers only meet in the combiner. For correct results, the supplier must return a new object every time, and the combiner must be associative, with an empty container as the identity. I only use the CONCURRENT characteristic when I've measured a need. And I test it by comparing sequential and parallel results, because a bad combiner passes every sequential test."

### Q3 [senior] When would you choose ReentrantLock, ReadWriteLock, StampedLock or synchronized?
tags: synchronized, reentrantlock, readwritelock, stampedlock, optimistic-read, virtual-threads, deloitte, reported-rounds

**Start here: the concepts**
- **synchronized:** the built-in monitor. Simple, and released automatically.
- **ReentrantLock:** the same mutual exclusion, plus timeout, interruptibility, fairness and multiple conditions.
- **ReadWriteLock:** many readers or one writer.
- **StampedLock:** adds an **optimistic read**, which takes no lock at all and validates afterwards.

**The live scenario (functional requirement)**
*FR: "A currency-rate table is read 50,000 times a second and updated once a minute."* Mutual exclusion here makes every reader queue behind every other reader, for no reason.

**What the interviewer is really checking**
That you start with the simplest option and can justify each step up.

**How I answer it** (120-second answer, point by point)

| Need | Choose | Why |
|---|---|---|
| Short critical section, no extras | `synchronized` | Least code, can't forget to unlock |
| Give up after a timeout, or be interruptible | `ReentrantLock` | `tryLock(timeout)`, `lockInterruptibly` |
| Several wait conditions, like not-full and not-empty | `ReentrantLock` | Multiple `Condition`s |
| Long reads, rare writes | `ReentrantReadWriteLock` | Readers don't block each other |
| Very short, very frequent reads | `StampedLock` | Optimistic read writes no shared state |
| One counter or reference | `AtomicLong`, `LongAdder` | No lock at all |
| Map-shaped data | `ConcurrentHashMap` | Already solved |

1. **Default to synchronized** for short sections. It is simple, and modern JVMs make the uncontended case cheap.
2. **Optimistic read** in my run:

```java
long stamp = lock.tryOptimisticRead();
double cx = x, cy = y;
if (!lock.validate(stamp)) {
    stamp = lock.readLock();
    try { cx = x; cy = y; } finally { lock.unlockRead(stamp); }
}
```

3. **Always unlock in `finally`** with an explicit lock. It is the bug `synchronized` cannot have.
4. **Virtual threads:** before JDK 24 a `synchronized` block pinned the carrier thread during blocking, so teams moved to `ReentrantLock`. JEP 491 in JDK 24 largely removed that, so it's no longer a general reason to switch.

**Trade-offs and what can go wrong**
- `ReadWriteLock` is slower than a plain lock if the read section is tiny, because readers still update a shared counter. Measure before switching.
- `StampedLock` is **not reentrant**: re-acquiring it in the same thread can deadlock. It has no `Condition` support either.
- Writer starvation can occur with non-fair read-write locks under constant reads.
- Fair locks reduce throughput significantly.

**Follow-ups to expect**
- *Immutable snapshot instead?* -> For the rate table, a `volatile` reference to an immutable map replaced on update is simplest and fastest. This is the answer I'd actually ship here.

**60-second answer**
"I start with synchronized for short critical sections, because it's simple and can't leak a lock. I go to ReentrantLock when I need a timeout, interruptibility or several conditions. ReadWriteLock helps when reads are long and writes are rare. StampedLock adds an optimistic read that takes no lock and validates afterwards, for very short frequent reads, but it isn't reentrant. Often the best answer is none of these: for a read-mostly table, a volatile reference to an immutable map replaced on update is simpler and faster."

### Q4 [senior] How do you decide whether a new Java language feature improves maintainability or merely makes code shorter?
tags: language-features, records, sealed, pattern-matching, var, maintainability, code-review, judgement, deloitte, reported-rounds

**Start here: the concepts**
- Shorter isn't the goal. A feature earns its place if it **removes a class of bug**, **makes intent explicit**, or **lets the compiler check more**.

**The live scenario (functional requirement)**
*FR: "Payment outcomes: Success, Declined, Pending."* A class hierarchy with an `if-instanceof` chain silently ignores a newly added `Refunded` outcome. Sealed types with an exhaustive `switch` turn that into a compile error at every call site.

**What the interviewer is really checking**
Engineering judgement: can you give a criterion and an example of saying no?

**How I answer it** (120-second answer, point by point)
My test has four questions:
1. **Does it remove a bug class?** Sealed + pattern `switch`: a missed case becomes a compile error. Text blocks: no more broken SQL string escaping. Yes, so adopt.
2. **Does it state intent?** A `record` says "this is immutable data" and generates correct `equals` and `hashCode`. Yes.
3. **Does it lose information the reader needs?** `var x = service.process(input);` hides the type, so I'd reject that in review. `var orders = new ArrayList<Order>();` loses nothing, so that's fine.
4. **Can the whole team read it, and do our tools support it?** Check the build, static analysis and framework support. A record can't be a JPA entity, because entities need a no-arg constructor and mutability. It suits DTOs instead.

Then I roll it out deliberately: agree on a short guideline, apply it to new code, and don't do a mass rewrite with no functional benefit.

**Trade-offs and what can go wrong**
- Dense chained streams or nested ternaries can be shorter and worse.
- Preview features can change between releases, so avoid them in production code unless there's a real reason.
- A sweeping migration PR has real review and merge-conflict costs for no user benefit.

**Follow-ups to expect**
- *An example you rejected?* -> Long `var` chains, or replacing clear loops with streams that need comments to explain.
- *Who decides?* -> A short team guideline, enforced in review and static analysis, not one person's taste.

**60-second answer**
"I ask whether it removes a class of bug, states intent more clearly, or lets the compiler check more. Sealed types with exhaustive switch do: a new case becomes a compile error everywhere it matters. Records state that something is immutable data. But var on a method call hides the type the reader needs, so I'd reject that even though it's shorter. I also check tooling and framework fit, for example records can't be JPA entities. Then we adopt it in new code with a short guideline, not a mass rewrite."

### Q5 [senior] Why would requests time out when a shared HashMap is used across threads, even though the application isn't crashing?
tags: hashmap, concurrency, thread-dump, data-race, concurrenthashmap, tomcat-threads, production, mastercard, reported-rounds

**Start here: the concepts**
- `HashMap` isn't thread-safe. Concurrent writes can corrupt its internal structure **without throwing anything**.
- A request thread stuck in the map holds its Tomcat thread, so the thread pool drains while the process stays up.

**The live scenario (functional requirement)**
*FR: "Cache product prices in a static map."* It works in test. After a few days under load, CPU rises, requests pile up and time out, and health checks may still pass. No exception appears in the logs.

**What the interviewer is really checking**
Whether you can connect a data structure to a production symptom, and how you'd prove it.

**How I answer it** (120-second answer, point by point)

Short answer: unsynchronised writes corrupted the map, so some threads spin or wait forever inside `get` or `put`. Each stuck thread is one less Tomcat worker, so the pool runs out and new requests queue until they time out. Nothing crashes, because nothing threw.

Technical detail:

| Evidence | What it shows | Command |
|---|---|---|
| Thread dump | Many threads `RUNNABLE` in `HashMap.getNode`, `putVal`, or `TreeNode` methods | `jstack <pid>` or `jcmd <pid> Thread.print`, three dumps 10 seconds apart |
| Per-thread CPU | The hot threads match those stack traces | `top -H -p <pid>` |
| Tomcat metrics | Busy threads at max, queue growing | `tomcat.threads.busy` in Micrometer |
| Latency | p99 climbs before errors do | APM or `http.server.requests` |

Deep dive:
1. **How a map corrupts:** two threads resizing or inserting can both change bucket links. In Java 7, this could create a **cycle** in a bucket's linked list, and `get` then looped forever at 100% CPU.
2. **Java 8 and later:** the resize keeps list order, which removed that specific cycle, but the map is still unsafe. Entries can vanish, sizes go wrong, and tree-bin operations can loop or throw `ClassCastException` under races. Don't claim Java 8 fixed it.
3. **The other failure mode:** wrapping it in `Collections.synchronizedMap`, or a `synchronized` block with slow work inside, gives lock contention. Dumps then show `BLOCKED` threads on one monitor.
4. **Fix:** `ConcurrentHashMap` for shared mutable maps, and use `computeIfAbsent`, keeping the function short. If it's a cache, use Caffeine, which adds size limits and expiry so it can't grow forever. For read-mostly config, swap a `volatile` reference to an immutable `Map.copyOf`.
5. **Prevent it:** code review of `static` mutable fields, static analysis, and a load test in CI, since the bug only shows under real concurrency.

**Trade-offs and what can go wrong**
- Restarting clears the symptom for days, which often leads teams to blame "a memory issue".
- `ConcurrentHashMap` makes single operations atomic, not sequences. `if (!map.containsKey(k)) map.put(k, v)` is still a race.

**How I'd monitor it**
Alert on Tomcat busy threads above about 80% of max, on p99, and capture a thread dump automatically when the pool saturates.

**Follow-ups to expect**
- *Why is the process still healthy?* -> It's alive, and a simple liveness check may use a different thread. Readiness should include pool saturation.
- *Can this be a memory leak too?* -> An unbounded static map also leaks, so check the heap dump as well.

**60-second answer**
"HashMap isn't thread-safe, and concurrent writes can corrupt its internal links silently, with no exception. Threads then spin or get stuck inside get or put, and each stuck thread is a Tomcat worker lost. The pool runs out, new requests queue and time out, but the process stays up, so nothing looks crashed. I'd prove it with three thread dumps: many threads in HashMap methods. Then I'd check per-thread CPU with top -H. The fix is ConcurrentHashMap or a bounded cache like Caffeine."

### Q6 [senior] All requests are timing out with exceptions, yet the application is running on the server. Why?
tags: timeouts, troubleshooting, thread-pool, connection-pool, gc, downstream, production, mastercard, reported-rounds

**Start here: the concepts**
- "Process is running" says little. A request needs a free thread, a free connection, memory headroom and a healthy downstream. Any one of those running out stops everything.

**The live scenario (functional requirement)**
*FR: "The checkout API is up, but every call fails after 30 seconds."* The JVM is alive, the logs are full of timeouts, and restarting helps for an hour.

**What the interviewer is really checking**
A systematic path from symptom to cause, not a list of guesses.

**How I answer it** (120-second answer, point by point)

Short answer: when all requests fail but the process lives, a shared resource is exhausted. I check in order: is traffic reaching it, are threads free, are connections free, is the JVM stuck in GC, and is a dependency slow? A thread dump and three metrics usually settle it within minutes.

Technical detail:

| Check | Tool | What points at the cause |
|---|---|---|
| Is traffic arriving? | LB and gateway logs, `ss -s` | Failing health checks, 502/504 at the LB, security group or DNS change |
| Threads | `jcmd <pid> Thread.print` | All Tomcat threads waiting on one thing |
| DB pool | HikariCP metrics | `hikaricp.connections.pending` above 0, `active` at max, "Connection is not available" |
| GC | `jstat -gcutil <pid> 1000`, GC logs | Old gen full, GC time above 10-20% |
| Downstream | Traces, client timeout logs | One dependency's latency jumped |
| Host | `top`, `df -h`, `ulimit -n`, `ss -tan` | Disk full, file descriptors exhausted, ephemeral ports used up |

Deep dive, what the thread dump shows:
1. **All waiting in `HikariPool.getConnection`:** pool exhaustion. Leaks, a slow query, or a slow HTTP call inside a transaction (bank 89 Q4).
2. **All in a socket read to one host:** a slow dependency with no timeout or breaker. This is the classic cascade: one slow call holds a thread for 30 seconds.
3. **All `BLOCKED` on one monitor:** a lock with slow work inside. Find the thread that holds it.
4. **Deadlock:** `jstack` prints "Found one Java-level deadlock".
5. **Threads barely moving, with GC at 90%:** a memory leak heading for OOM. Take a heap dump.
6. **All threads free, and no requests:** it isn't the app. Look at the network and load balancer.

Fix the immediate problem first: shift traffic, roll back, or restart one pod **after saving a thread dump and heap dump**. Then fix the cause: timeouts on every outbound call, a circuit breaker, a bulkhead per dependency.

**Trade-offs and what can go wrong**
- Restarting first destroys the evidence and guarantees a repeat.
- Raising pool sizes hides a slow dependency and can overload the database.
- A timeout that's longer than the caller's own timeout does no good, because the caller has already given up.

**How I'd monitor it**
Alert on saturation before failure: Hikari pending above 0 for a minute, Tomcat busy above 80%, GC time, and dependency p99. Bank 09 covers the incident flow.

**Follow-ups to expect**
- *Restart fixed it, so are we done?* -> No. That means something accumulates: leak, stuck threads or lost connections. Find it.
- *What timeouts do you set?* -> Connect around 1 second, read near the dependency's p99 plus a margin, and a total deadline below the caller's.

**60-second answer**
"If every request fails but the process is up, something shared is exhausted. I first confirm traffic reaches it, then take a thread dump before anything else, because it usually gives the answer. Threads all waiting in HikariPool means connection exhaustion. All in a socket read means a slow dependency with no timeout. All blocked on one monitor means a lock. If GC is at 90%, it's a leak. If threads are idle, it's the network. I save dumps, restore service by shifting traffic or rolling back, and only then fix the cause, usually with timeouts, a breaker and a bulkhead."

### Q7 [mid] In which scenarios will you get concurrency issues?
tags: concurrency, race-condition, check-then-act, read-modify-write, singleton-bean, visibility, deadlock, mastercard, reported-rounds

**Start here: the concepts**
- You need **shared** state, **mutable** state, and **more than one thread**. Remove any one and the problem disappears.

**The live scenario (functional requirement)**
*FR: "A Spring service counts today's orders in an instance field."* Spring beans are **singletons**, so every request thread shares that field. This is the most common source of concurrency bugs in Spring code.

**What the interviewer is really checking**
Whether you recognise the patterns in everyday code, not just textbook definitions.

**How I answer it** (120-second answer, point by point)

| Pattern | Example | Fix |
|---|---|---|
| Read-modify-write | `count++` on a shared field | `AtomicLong`, `LongAdder` |
| Check-then-act | `if (!map.containsKey(k)) map.put(k, v)` | `computeIfAbsent`, `putIfAbsent` |
| Mutable state in a singleton bean | Instance field `private Order current;` | Local variables, or a request-scoped holder |
| Non-thread-safe classes | Shared `SimpleDateFormat`, `HashMap`, `ArrayList` | `DateTimeFormatter`, concurrent collections |
| Visibility | A non-`volatile` stop flag never seen by another thread | `volatile`, or a proper executor shutdown |
| Lock ordering | Thread 1 locks A then B; thread 2 locks B then A | One global lock order |
| Publishing unsafely | Sharing an object before its constructor finishes | Final fields, safe publication |
| Across instances | Two pods both pass the "stock > 0" check | Database constraint, optimistic lock, or distributed lock |

The last row is important: Java locks only protect one JVM. With several pods, the database or Kafka partitioning must enforce the rule.

**Trade-offs and what can go wrong**
- Over-locking gives low throughput, or deadlocks, so reduce sharing first.
- `ThreadLocal` context is lost when work moves to a pool or a parallel stream.

**Follow-ups to expect**
- *How do you find them?* -> Code review of shared mutable fields, static analysis, stress tests with JCStress, and thread dumps in production.

**60-second answer**
"A concurrency issue needs shared, mutable state and multiple threads. In real code the patterns are read-modify-write like count++, check-then-act like containsKey then put, instance fields in Spring singleton beans, and non-thread-safe classes like SimpleDateFormat. Then visibility without volatile, and lock ordering that causes deadlock. Also, across pods, a Java lock is useless, so the database has to enforce the rule. My first fix is always to remove the sharing, then immutability, and only then a lock."

### Q8 [mid] Why does a race condition appear in production with many threads, when the code works fine in testing?
tags: race-condition, testing, load, timing, jcstress, concurrency-testing, mastercard, reported-rounds

**Start here: the concepts**
- A race needs two threads inside a tiny window at the same moment. Its probability grows sharply with load and with the number of cores.

**The live scenario (functional requirement)**
*FR: "Prevent double-booking of a seat."* A unit test with one thread always passes. The first flash sale sells the same seat twice.

**What the interviewer is really checking**
That you can explain why tests hide races, and what would actually expose them.

**How I answer it** (120-second answer, point by point)
1. **Tests usually run with one thread.** No concurrency means no race, so a passing test proves nothing here.
2. **Timing:** the window may be nanoseconds wide. At 2 requests a second it almost never overlaps. At 5,000 a second on 32 cores it overlaps constantly.
3. **Hardware and JIT:** after warm-up, the JIT may reorder or cache reads, and multi-core CPUs have per-core caches. Without `volatile` or a lock, those effects are legal, and they're rarely seen on a laptop run with cold code.
4. **Data:** production has shared hot keys, such as one popular product, while test data is spread out.
5. **What exposes it:** a concurrent test that releases many threads together with a `CountDownLatch`, repeated many times. JCStress for low-level concurrency. A load test on hot keys.
6. **What I'd check in code first:** shared mutable fields, and check-then-act sequences.

**Trade-offs and what can go wrong**
- Adding logging can hide a race, because it changes the timing and adds synchronisation inside the logger.
- `Thread.sleep` in tests makes them slow and flaky. Use latches.

**Follow-ups to expect**
- *Newer JDK makes it rarer?* -> Sometimes, and that makes it worse: it hides until the critical section contains a call. The repo's Python folder has the same lesson.
- *How do you fix the seat bug?* -> A unique constraint on `(show_id, seat_id)`. The database is the single point of truth across pods.

**60-second answer**
"A race needs two threads inside a tiny window together. Tests usually run single-threaded, so they can't hit it, and even a concurrent test at low load rarely overlaps. In production, high traffic, many cores, hot keys, and JIT optimisations after warm-up make it happen constantly. To expose it, I release many threads together with a CountDownLatch and repeat it, or use JCStress. And for something like double-booking, I'd rely on a database unique constraint rather than Java locks, since there are several pods."

### Q9 [fresher] How do you implement threads in Java?
tags: threads, runnable, callable, executorservice, virtual-threads, completablefuture, deloitte, reported-rounds

**Start here: the concepts**
- A **thread** is an independent path of execution. You give it a task and something runs it.

**The live scenario (functional requirement)**
*FR: "Send a confirmation email without making the order API wait."*

**What the interviewer is really checking**
That you can list the ways, and that you'd use an executor in production rather than `new Thread`.

**How I answer it** (120-second answer, point by point)

| Way | Code | Use |
|---|---|---|
| Extend `Thread` | `class T extends Thread { public void run() {...} }` | Almost never: uses up your one superclass |
| `Runnable` | `new Thread(() -> send()).start();` | Learning, or very simple cases |
| `Callable` + `Future` | `Future<Integer> f = pool.submit(() -> 42);` | When you need a result or an exception |
| Executor | `Executors.newFixedThreadPool(8)` | The default in production: reuses threads, limits them |
| `CompletableFuture` | `supplyAsync(() -> call(), pool).thenApply(...)` | Combining async steps |
| Virtual threads | `Executors.newVirtualThreadPerTaskExecutor()` | Many blocking tasks, Java 21+ |
| Spring | `@Async` with a configured executor | Spring apps |

Key points:
1. **`start()`, not `run()`.** `run()` executes on the current thread with no concurrency, a classic question.
2. **Use an executor**, because thread creation is expensive and unbounded creation can exhaust memory.
3. **Bound the queue:** `newFixedThreadPool` has an unbounded queue, so under overload it grows until out-of-memory. In production I build a `ThreadPoolExecutor` with a bounded queue and a rejection policy.
4. **Shut it down:** `try (var pool = ...)` with `ExecutorService` as `AutoCloseable` (Java 19+), or an explicit shutdown.

**Trade-offs and what can go wrong**
- An exception in a plain `execute` task only reaches the uncaught handler, and with `submit` it hides until `get()`. Both can look like "nothing happened".
- For an email, a durable queue or Kafka is often better. A thread pool loses the job on restart.

**Follow-ups to expect**
- *Pool size?* -> CPU-bound: about the core count. I/O-bound: more, or virtual threads with a semaphore limit.
- *Daemon threads?* -> They don't keep the JVM alive.

**60-second answer**
"You can extend Thread or pass a Runnable, and Callable if you need a result. In production I use an ExecutorService, because reusing a limited set of threads is cheaper and safer, and I set a bounded queue with a rejection policy. CompletableFuture combines async steps, and for many blocking tasks on Java 21+, virtual threads. Remember that start creates the thread, while run just calls the method. For something that mustn't be lost, like an email, I'd use a durable queue."
