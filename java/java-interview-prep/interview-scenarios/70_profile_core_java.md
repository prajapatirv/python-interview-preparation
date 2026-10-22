---
id: profile-java-genai-core-java
title: Java + GenAI profile (1/9): Core Java, 15 functional-requirement questions
stack: java
skill: java-core
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).
Every answer opens with a **functional requirement**, the way a PM/DM evaluation frames it, then the answer.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Explain the four OOP principles using a design you would actually build.
tags: oop, polymorphism, encapsulation, abstraction, inheritance, strategy-pattern, solid, profile-java-genai

**Start here: the concepts**
- **Encapsulation:** state is private and changed only through methods that keep it valid.
- **Abstraction:** callers depend on *what* something does (an interface), not *how*.
- **Inheritance:** reuse by "is-a"; useful but the tightest coupling Java offers.
- **Polymorphism:** one call site, many behaviours chosen at runtime by the actual object type.

**The live scenario (functional requirement)**
*FR: "The checkout must accept card, UPI and wallet payments today, and the business will add 'pay later' next quarter without a code freeze."* A naive `if (type == CARD) ... else if (type == UPI)` grows in one class, and every new method means editing and retesting checkout.

**What the interviewer is really checking**
That you can map textbook words to a design decision, and know when inheritance hurts (prefer composition).

**How I answer it**
1. **Abstraction:** a `PaymentMethod` interface with `authorize(Money amount)` and `refund(String txnId)`. Checkout depends only on it.
2. **Polymorphism:** `CardPayment`, `UpiPayment`, `WalletPayment` implement it. A `Map<PaymentType, PaymentMethod>` (Spring injects all beans of the type) picks one at runtime. Adding "pay later" is a new class, no edits to checkout: Open/Closed principle.
3. **Encapsulation:** `Money` keeps amount and currency private, validates in the constructor, and has no setters, so a negative amount can never exist.
4. **Inheritance, sparingly:** an `abstract class AbstractGatewayPayment` holds shared retry and logging code for gateway-backed methods. I would not build deep hierarchies; shared behaviour can also be a composed `GatewayClient`.
5. Close by naming the pattern: this is the **Strategy** pattern, and in Spring it is just a list of beans.

**Trade-offs and what can go wrong**
- Deep inheritance (fragile base class): a change in the parent silently breaks children. Favour composition.
- Over-abstraction: an interface with one implementation forever is ceremony; add it when variation is real or for testing seams.
- Polymorphism via a giant `switch` on an enum is still a code smell when behaviour per type is large.

**How I'd monitor it**
Metrics tagged by payment method (`payments_total{method="upi",outcome="declined"}`), so a new strategy's failure rate is visible from day one.

**Follow-ups to expect**
- *Abstract class or interface?* -> Interface for the contract; abstract class only to share state or code among closely related types. Interfaces can have default methods since Java 8.
- *Composition over inheritance, an example?* -> A `RetryingGatewayClient` wrapping a `GatewayClient` instead of every payment extending a retry base class.
- *Which SOLID principle did you use?* -> Open/Closed and Dependency Inversion: checkout depends on the abstraction.

**60-second answer**
"I'd explain it with checkout. Checkout depends on a `PaymentMethod` interface: that's abstraction. Card, UPI and wallet each implement it and Spring hands me a map of them, so the right one is picked at runtime: polymorphism, and the Strategy pattern. Adding 'pay later' is one new class with no change to checkout, which is Open/Closed. `Money` is encapsulated: private fields, validated in the constructor, no setters, so an invalid amount can't exist. I use inheritance only for a thin abstract base sharing gateway retry code, and I prefer composition, because deep hierarchies make every parent change risky."

### Q2 [mid] How do you design an immutable class, and where do records fit?
tags: immutability, records, value-object, thread-safety, defensive-copy, java-17, profile-java-genai

**Start here: the concepts**
- **Immutable object:** its state cannot change after construction. It is automatically thread-safe and safe as a map key.
- **Record (Java 16+):** a concise, final, shallowly immutable data carrier with generated constructor, accessors, `equals`, `hashCode`, `toString`.
- **Shallow vs deep immutability:** a `final List` field can still be mutated through the list itself.

**The live scenario (functional requirement)**
*FR: "Publish an `OrderPlaced` event to Kafka and also cache it in memory for 5 minutes for the status page."* The same object is read by the publisher thread, the cache and the status API. A bug where one consumer called `event.getItems().clear()` emptied the cached copy for everyone.

**What the interviewer is really checking**
The rules (final class, private final fields, no setters, defensive copies) and whether you know records are only *shallowly* immutable.

**How I answer it**
1. Make the class `final` (or a record) so no subclass adds mutable state.
2. All fields `private final`, set once in the constructor, validated there.
3. No setters. "Changes" return a new instance (`withStatus(...)`).
4. **Defensive copies** for mutable inputs and outputs: `this.items = List.copyOf(items)`. `List.copyOf` returns an unmodifiable list and rejects nulls.
5. With a record I do the copy in the **compact constructor**:

```java
record OrderPlaced(String orderId, List<LineItem> items, Instant at) {
    OrderPlaced { Objects.requireNonNull(orderId); items = List.copyOf(items); }
}
```

6. Make sure the element type (`LineItem`) is immutable too, otherwise the immutability is only one level deep.

**Trade-offs and what can go wrong**
- Allocation: "modifying" creates new objects. Usually negligible next to I/O; the JIT and young-gen GC handle short-lived objects cheaply.
- `Date` and arrays are mutable; use `Instant`/`LocalDate` and copy arrays.
- JPA entities cannot be records (they need a no-arg constructor and mutability); use records for DTOs, events and value objects.

**How I'd monitor it**
Not a runtime metric; I enforce it with ArchUnit rules (event classes must be records) and code review.

**Follow-ups to expect**
- *Why is String immutable?* -> Security (class loading, file paths), the string pool, cached hash code, thread safety.
- *Is `Collections.unmodifiableList` enough?* -> No, it is a view; the original list can still change. `List.copyOf` takes a snapshot.
- *Can a record have methods and static factories?* -> Yes, plus compact constructors for validation; it cannot extend another class.

**60-second answer**
"Immutable means no state change after construction: final class, private final fields, no setters, validation in the constructor, and defensive copies of anything mutable coming in or going out. For an `OrderPlaced` event shared between a Kafka publisher, a cache and an API, I use a record and do `items = List.copyOf(items)` in the compact constructor, because a record is only shallowly immutable. The payoff is thread safety without locks and safe map keys; the cost is a few extra allocations, which is negligible."

### Q3 [senior] HashMap, synchronizedMap or ConcurrentHashMap for a per-client request counter?
tags: concurrenthashmap, hashmap, thread-safety, atomic, longadder, compute, concurrency, profile-java-genai

**Start here: the concepts**
- **HashMap:** not thread-safe. Concurrent writes can lose entries or corrupt buckets.
- **Collections.synchronizedMap:** one lock for the whole map; correct but every call serialises.
- **ConcurrentHashMap:** lock-free reads, fine-grained locking per bin on writes, and atomic compound operations (`compute`, `merge`, `computeIfAbsent`).
- **Check-then-act race:** `if (!map.containsKey(k)) map.put(k, v)` is two operations; another thread can act between them.

**The live scenario (functional requirement)**
*FR: "Count requests per API client per minute so we can bill usage and reject clients over quota."* 400 Tomcat threads update the map at ~8,000 requests/s. The first version used a `HashMap` with `get`, `+1`, `put` and billing came out 6% lower than the gateway logs.

**What the interviewer is really checking**
That thread-safe map does not mean thread-safe *logic*, and that you know the atomic APIs.

**How I answer it**
1. `HashMap` is out: lost updates and possible corruption under concurrent writes.
2. `synchronizedMap` is correct but a single lock becomes the bottleneck at this rate.
3. `ConcurrentHashMap`, and crucially an **atomic update** rather than get/put:

```java
counters.computeIfAbsent(clientId, k -> new LongAdder()).increment();
```

4. `LongAdder` beats `AtomicLong` under high contention because it stripes the counter across cells and sums on read. Reads (`sum()`) are rarer than writes here.
5. For the per-minute window I key by `clientId + minuteBucket` or swap the whole map every minute with an `AtomicReference`, then flush the old one to the billing store.
6. With multiple service instances this local map is only a cache; the source of truth for quota is Redis (`INCR` with expiry) or the gateway.

**Trade-offs and what can go wrong**
- `computeIfAbsent` must not do slow work or touch the same map inside the function; it holds the bin lock.
- `ConcurrentHashMap` does not allow null keys or values.
- Iteration is weakly consistent: a snapshot sum during writes is approximate, which is fine for metrics, not for money unless you flush at a boundary.

**How I'd monitor it**
Reconcile the counter totals with gateway access logs daily; alert when the difference exceeds 0.1%.

**Follow-ups to expect**
- *How did ConcurrentHashMap change in Java 8?* -> From 16 segment locks to CAS on empty bins plus `synchronized` on the bin head, and treeified bins for heavy collisions.
- *Why not `AtomicLong`?* -> Fine at low contention; `LongAdder` scales better when many threads hit one counter.
- *What about distributed counting?* -> Redis `INCR` + `EXPIRE` or a gateway rate limiter; local maps are per instance.

**60-second answer**
"HashMap loses updates under concurrency and synchronizedMap serialises every call, so I use ConcurrentHashMap, but the important part is the update: `computeIfAbsent(client, k -> new LongAdder()).increment()` is atomic, while get-plus-put is a race even on a concurrent map. LongAdder stripes the count so 400 threads don't fight over one CAS. I roll the window every minute and flush to the billing store, and because there are several instances, the real quota check lives in Redis or the gateway."

### Q4 [senior] Build an order sales report with streams. What do you watch out for?
tags: streams, collectors, groupingby, parallel-streams, java-8, performance, profile-java-genai

**Start here: the concepts**
- **Stream pipeline:** source -> intermediate operations (lazy: `filter`, `map`) -> one terminal operation (`collect`, `reduce`).
- **Collectors:** `groupingBy`, `summingDouble`/`reducing`, `toMap`, `partitioningBy`, `teeing`.
- **Parallel streams:** split work on the common ForkJoinPool. Helps only for large, CPU-bound, stateless work.

**The live scenario (functional requirement)**
*FR: "Show revenue per region and per category for last month, plus the top 3 products per region, on the sales dashboard."* About 2 million order lines are loaded in memory by a nightly batch.

**What the interviewer is really checking**
Fluency with collectors, correctness with money, and judgement about `parallel()`.

**How I answer it**
1. Revenue per region and category with a nested `groupingBy`:

```java
Map<String, Map<String, BigDecimal>> revenue = lines.stream()
    .collect(groupingBy(OrderLine::region, groupingBy(OrderLine::category,
             reducing(BigDecimal.ZERO, OrderLine::amount, BigDecimal::add))));
```

2. Money is `BigDecimal`, never `double` (`summingDouble` would introduce rounding errors).
3. Top 3 per region: group product revenue per region, then sort each entry set by value descending and `limit(3)`.
4. **Push it down** if possible: for 2 million rows a SQL `GROUP BY` in the database is faster and uses less heap than loading everything into Java. Streams are right when data is already in memory or comes from several sources.
5. `parallel()` only after measuring: the work per element is tiny, so the split/merge overhead and the shared common pool usually make it slower inside a web app.

**Trade-offs and what can go wrong**
- Parallel streams run on the **common ForkJoinPool**, shared with `CompletableFuture` defaults: one heavy report can starve other work.
- Side effects in `forEach` adding to a non-thread-safe list break in parallel.
- `toMap` throws on duplicate keys unless you give a merge function.
- Streams are single-use; a second terminal op throws `IllegalStateException`.

**How I'd monitor it**
Batch duration and heap after GC during the job; a Micrometer timer around report generation.

**Follow-ups to expect**
- *`map` vs `flatMap`?* -> `flatMap` flattens a stream of streams (orders -> lines).
- *Are streams faster than loops?* -> Not inherently; similar after JIT, sometimes slower. Choose for readability.
- *What is short-circuiting?* -> `findFirst`, `anyMatch`, `limit` stop processing early.

**60-second answer**
"I'd use a nested `groupingBy` by region then category with a `reducing` over `BigDecimal`, because money must not be a double. Top 3 per region is a sort plus `limit(3)` per group. But for 2 million rows I'd first ask whether the database should do the `GROUP BY`; it's faster and spares the heap. I don't add `parallel()` by default: it uses the shared common ForkJoinPool, the per-element work is tiny, and I'd only switch after a benchmark proved it helps."

### Q5 [senior] Call three downstream services in parallel with CompletableFuture and a time budget.
tags: completablefuture, async, timeout, executor, aggregation, java-8, profile-java-genai

**Start here: the concepts**
- **CompletableFuture:** a future you can compose: `supplyAsync`, `thenApply`, `thenCombine`, `allOf`, `exceptionally`.
- **Executor:** where the work runs. The default is the common ForkJoinPool, which is sized for CPU work, not blocking I/O.
- **Java 9+ timeouts:** `orTimeout` (fail) and `completeOnTimeout` (default value).

**The live scenario (functional requirement)**
*FR: "The customer 360 page must show profile, recent orders and loyalty points in under 500 ms; if loyalty is slow, show the page without it."* Sequential calls take 150 + 200 + 300 = 650 ms.

**What the interviewer is really checking**
Parallel composition, a dedicated executor for blocking calls, per-call timeouts and graceful degradation.

**How I answer it**
1. A dedicated bounded executor for the blocking HTTP calls (or virtual threads on Java 21+: `Executors.newVirtualThreadPerTaskExecutor()`).
2. Start all three at once:

```java
var profile = supplyAsync(() -> profileClient.get(id), ioPool).orTimeout(400, MILLISECONDS);
var orders  = supplyAsync(() -> orderClient.recent(id), ioPool).orTimeout(400, MILLISECONDS);
var points  = supplyAsync(() -> loyaltyClient.points(id), ioPool)
                 .completeOnTimeout(Points.UNKNOWN, 300, MILLISECONDS)
                 .exceptionally(ex -> Points.UNKNOWN);
```

3. Combine with `allOf(...).thenApply(v -> new Customer360(profile.join(), orders.join(), points.join()))`. Latency becomes roughly the slowest required call, about 300 ms.
4. Required parts (profile) fail the request; optional parts (loyalty) degrade to a default.
5. Also set **HTTP client timeouts**: `orTimeout` completes the future but does not stop the underlying socket call.

**Trade-offs and what can go wrong**
- Using the common pool for blocking I/O starves parallel streams and other async work.
- `join()` inside another async stage blocks a pool thread; compose instead.
- Exceptions arrive wrapped in `CompletionException`; unwrap before mapping to HTTP errors.
- MDC/trace context does not propagate across threads automatically; use context-propagating executors (Micrometer context propagation).

**How I'd monitor it**
Per-dependency latency percentiles, count of loyalty fallbacks, executor queue depth and active threads.

**Follow-ups to expect**
- *`thenApply` vs `thenCompose`?* -> `thenCompose` flattens when the function returns another future.
- *Would virtual threads replace this?* -> They make blocking cheap, so plain sequential-looking code in parallel tasks works; structured concurrency (preview in Java 25) makes the fan-out and cancellation cleaner.
- *How do you cancel the slow call?* -> Client-level timeouts; `cancel(true)` does not interrupt the work inside a CompletableFuture.

**60-second answer**
"I fire all three calls at once with `supplyAsync` on a dedicated I/O executor, not the common pool, so latency becomes the slowest call instead of the sum. Each gets a budget: profile and orders use `orTimeout` because the page needs them; loyalty uses `completeOnTimeout` with an 'unknown' default, so the page renders without it. Then `allOf` combines them. I also set HTTP client timeouts because `orTimeout` doesn't cancel the socket, and I propagate trace context to the pool threads."

### Q6 [senior] When do virtual threads help, and when don't they?
tags: virtual-threads, java-21, loom, pinning, throughput, blocking-io, profile-java-genai

**Start here: the concepts**
- **Platform thread:** a wrapper around an OS thread; about 1 MB of stack reserved, expensive to have thousands.
- **Virtual thread (Java 21):** a lightweight thread scheduled by the JVM onto a few carrier threads. When it blocks on I/O it unmounts, freeing the carrier.
- **Pinning:** a virtual thread that cannot unmount while blocked. Before Java 24, blocking inside `synchronized` pinned it; JEP 491 (Java 24) removed that. Native calls still pin.

**The live scenario (functional requirement)**
*FR: "The document-ingestion service must handle 3,000 concurrent requests, each calling an LLM embedding API that takes ~800 ms."* With Tomcat's 200 platform threads, throughput caps at about 250 requests/s and the rest queue.

**What the interviewer is really checking**
That virtual threads raise **concurrency for blocking I/O**, not CPU speed, and that you know the limits.

**How I answer it**
1. Little's Law: 3,000 concurrent × 0.8 s means the work is waiting, not computing. That is exactly what virtual threads are for.
2. In Spring Boot 3.2+ it is one property: `spring.threads.virtual.enabled=true` (Tomcat, `@Async` and scheduling use virtual threads).
3. **Throttle the downstream yourself.** Virtual threads remove the natural thread-pool limit, so 3,000 requests can hit the embedding API at once and trigger 429s. I add a `Semaphore` or a bulkhead sized to the provider's quota.
4. Size the JDBC pool honestly: 3,000 virtual threads still share, say, 30 connections; they queue on the pool.
5. Avoid `ThreadLocal` caches of heavy objects (a million threads means a million copies); look at scoped values (final in Java 25).

**Trade-offs and what can go wrong**
- **CPU-bound work gains nothing**; keep a bounded platform pool for it.
- Pinning on older JDKs with `synchronized` around I/O; upgrade to 24+ or use `ReentrantLock`.
- Do not pool virtual threads; create one per task.
- Unbounded concurrency moves the bottleneck to the database or the vendor.

**How I'd monitor it**
Request throughput and p99, downstream 429s, connection-pool wait time, JFR events `jdk.VirtualThreadPinned`.

**Follow-ups to expect**
- *Virtual threads vs WebFlux?* -> Similar scalability for I/O with simple blocking code; reactive still wins for streaming and backpressure-heavy pipelines.
- *How many carriers?* -> By default as many as CPU cores (a ForkJoinPool).
- *Do they make code faster?* -> No, they let more requests wait at the same time cheaply.

**60-second answer**
"Virtual threads help when requests mostly wait: 3,000 concurrent calls to an 800 ms embedding API. Platform threads cap me at the pool size; with virtual threads a blocked request unmounts and costs almost nothing, and in Spring Boot it's one property. They don't help CPU-bound work. The catch is that the thread pool was my accidental throttle, so I add an explicit semaphore sized to the vendor quota and watch the DB pool. On JDK 24+ synchronized no longer pins, and JFR shows any pinning that remains."

### Q7 [mid] What is your exception-handling strategy in a Java service?
tags: exceptions, checked, unchecked, try-with-resources, custom-exceptions, error-handling, profile-java-genai

**Start here: the concepts**
- **Checked exceptions:** must be declared or caught (`IOException`); for recoverable conditions the caller can act on.
- **Unchecked (RuntimeException):** programming errors or conditions most callers cannot fix.
- **try-with-resources:** closes `AutoCloseable` resources automatically, keeping suppressed exceptions.

**The live scenario (functional requirement)**
*FR: "When a loan application references a missing customer, return a clear 404; when the credit bureau is down, return 503 and retry later; never leak stack traces to clients."*

**What the interviewer is really checking**
A consistent policy: domain exceptions, translation at layer boundaries, one place that maps to HTTP, and no swallowed errors.

**How I answer it**
1. **Domain exceptions** extending `RuntimeException`: `CustomerNotFoundException`, `BureauUnavailableException`, each with an error code.
2. **Translate at the boundary:** the bureau client catches `IOException`/HTTP errors and throws `BureauUnavailableException(cause)`, keeping the cause.
3. **One handler** (`@RestControllerAdvice`) maps them to HTTP status and a Problem Details body. Controllers and services don't catch just to rethrow.
4. **Resources** in try-with-resources, always.
5. **Log once**, at the place you handle it, with the correlation id; not at every layer (log-and-rethrow produces five copies of the same stack trace).
6. Never `catch (Exception e) {}`. If you truly ignore something, comment why and count it.

**Trade-offs and what can go wrong**
- Checked exceptions across lambdas are awkward; wrap them at the boundary.
- Catching `Throwable` swallows `OutOfMemoryError`.
- `finally` with `return` hides the original exception.
- Exceptions for normal flow control are slow and unclear; return `Optional` for "not found" inside the domain when it is expected.

**How I'd monitor it**
Error counts by exception type and HTTP status, an alert on 5xx rate, and logs with error codes for Splunk searches.

**Follow-ups to expect**
- *Checked or unchecked for your domain?* -> Unchecked, with clear names and a central handler; Spring follows the same convention.
- *What happens to an exception thrown in `close()`?* -> It is added as a suppressed exception to the primary one.
- *`throw` vs `throws`?* -> `throw` raises; `throws` declares.

**60-second answer**
"My rule is: domain exceptions as unchecked types with error codes, translate low-level exceptions at the boundary while keeping the cause, and map them to HTTP in exactly one place, a `@RestControllerAdvice` returning Problem Details. So a missing customer becomes 404, a bureau outage becomes 503 with Retry-After, and no stack trace ever reaches the client. Resources go in try-with-resources, I log once where it's handled with the correlation id, and empty catch blocks are banned."

### Q8 [senior] Heap keeps growing in production until OutOfMemoryError. How do you find the leak?
tags: memory-leak, heap-dump, outofmemoryerror, threadlocal, gc, troubleshooting, profile-java-genai

**Start here: the concepts**
- **Memory leak in Java:** objects stay reachable from a GC root (static field, live thread, cache) after they are no longer needed.
- **Heap dump:** a snapshot of all objects; analysed with Eclipse MAT or VisualVM ("dominator tree", "path to GC roots").
- **Old-gen after GC:** the baseline that matters. A rising floor after each full collection means a leak.

**The live scenario (functional requirement)**
*FR: "The chat-assistant service must run for weeks without restarts."* After about 3 days pods are OOMKilled. Heap after GC climbs from 400 MB to 1.8 GB in a sawtooth that never returns to baseline.

**What the interviewer is really checking**
A method: confirm it's a leak, capture evidence, find the root, fix, prove the fix.

**How I answer it**
1. **Confirm:** GC logs or Micrometer `jvm_memory_used_bytes{area="heap"}` after GC rising steadily under steady traffic. Not just high usage.
2. **Capture:** `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps` on a persistent volume, or `jcmd <pid> GC.heap_dump` before it dies. Two dumps an hour apart show what grows.
3. **Analyse in MAT:** dominator tree. In this case: a `static Map<String, List<Message>> conversations` holding every chat session ever, never evicted.
4. **Fix:** bounded cache with TTL (Caffeine `maximumSize` + `expireAfterAccess`) or move conversation memory to Redis with expiry.
5. **Other classic roots:** `ThreadLocal` on pooled threads never `remove()`d, listeners never unregistered, unbounded queues, classloader leaks on redeploy.
6. **Prove:** load test for hours; heap-after-GC flat.

**Trade-offs and what can go wrong**
- Heap dumps pause the JVM and are as large as the heap; take them from a pod drained from the load balancer.
- Dumps contain user data (chat text!), so treat them as sensitive.
- OOMKilled by Kubernetes with no Java OOM means **native or off-heap memory** (metaspace, threads, direct buffers), not heap: check NMT (`-XX:NativeMemoryTracking=summary`).

**How I'd monitor it**
Alert on heap-after-GC trend and GC time percentage, container memory vs limit, restart count per pod.

**Follow-ups to expect**
- *How do you tell heap OOM from container OOMKill?* -> Java OOM logs `java.lang.OutOfMemoryError`; OOMKill shows exit code 137 and `OOMKilled` in `kubectl describe`.
- *Weak references for caches?* -> `WeakHashMap` keys are weak, not values; prefer a real cache library.
- *How to find ThreadLocal leaks?* -> In MAT look at `Thread` -> `threadLocals` holding big objects.

**60-second answer**
"First I confirm it's a leak and not just load: heap after GC keeps rising. Then I capture evidence with heap-dump-on-OOM, or two `jcmd` dumps an hour apart, and open them in Eclipse MAT's dominator tree. Last time it was a static map of chat conversations with no eviction; I replaced it with a Caffeine cache with size and TTL limits and moved long-lived memory to Redis. I prove the fix with a long soak test. And if Kubernetes kills the pod without a Java OOM, I look at native memory instead, with NMT."

### Q9 [senior] Which garbage collector would you choose and how do you size the heap in a container?
tags: gc, g1, zgc, jvm-tuning, containers, maxrampercentage, latency, profile-java-genai

**Start here: the concepts**
- **G1:** the default; region-based, aims for a pause target (`MaxGCPauseMillis`, default 200 ms). Good general choice.
- **ZGC:** concurrent, sub-millisecond pauses even on large heaps; **generational** by default since JDK 23. Costs some CPU and memory headroom.
- **Parallel GC:** maximum throughput, long pauses; batch jobs.
- **Container awareness:** modern JVMs read cgroup limits; `-XX:MaxRAMPercentage` sets heap as a share of the container memory.

**The live scenario (functional requirement)**
*FR: "The pricing API must keep p99 under 100 ms."* p99 sits at 350 ms; GC logs show G1 pauses of 250 ms on a 12 GB heap full of a large in-memory price cache.

**What the interviewer is really checking**
That you decide from data (GC logs, pause times vs latency SLO), not folklore, and you know container sizing.

**How I answer it**
1. **Measure:** `-Xlog:gc*:file=gc.log` and correlate pauses with the p99 spikes. If GC is not in the p99, tuning it is pointless.
2. **Reduce garbage first:** a 12 GB cache of boxed objects is the real problem; move it off-heap or to Redis, or use primitive collections.
3. **Choose:** for a latency SLO on a big heap, **generational ZGC** (`-XX:+UseZGC`). For a small 1–2 GB service, G1 is usually fine.
4. **Container sizing:** `-XX:MaxRAMPercentage=70` leaves room for metaspace, thread stacks, direct buffers and the code cache. Set `-Xms` = `-Xmx` equivalent (`InitialRAMPercentage` too) to avoid resizing.
5. Re-test with production-like load and compare p99 and CPU.

**Trade-offs and what can go wrong**
- ZGC trades some CPU throughput and needs heap headroom; under-sized it stalls allocation.
- 100% heap of the container limit leads to OOMKilled.
- Tuning dozens of flags is cargo cult; pick the collector, the heap size and the pause goal.

**How I'd monitor it**
GC pause time histogram, GC CPU %, heap after GC, allocation rate (JFR), alongside the latency SLO.

**Follow-ups to expect**
- *What is a stop-the-world pause?* -> All application threads stop while GC does part of its work.
- *Why are short-lived objects cheap?* -> Generational hypothesis: most die young and a young collection copies only survivors.
- *What about Shenandoah?* -> Another low-pause concurrent collector (in OpenJDK builds from Red Hat and others); a similar trade-off to ZGC.

**60-second answer**
"I start from the SLO and GC logs: if pauses line up with p99 spikes, GC matters. Usually the first fix is less garbage; a 12 GB on-heap cache was the real issue. For a big heap with a strict latency target I pick generational ZGC, the default ZGC mode since JDK 23, with sub-millisecond pauses. For small services G1 is fine. In containers I set MaxRAMPercentage around 70 so metaspace, stacks and direct buffers fit, then verify p99 and CPU under real load."

### Q10 [mid] Explain generics, wildcards and PECS with a reusable component.
tags: generics, wildcards, pecs, type-erasure, bounded-types, api-design, profile-java-genai

**Start here: the concepts**
- **Generics:** compile-time type safety and no casts (`List<Order>`).
- **Bounded types:** `<T extends Comparable<T>>`.
- **Wildcards:** `? extends T` (read as T: producer), `? super T` (write T: consumer). **PECS:** Producer Extends, Consumer Super.
- **Type erasure:** generic types are removed at runtime; you cannot do `new T()` or `instanceof List<String>`.

**The live scenario (functional requirement)**
*FR: "Build one validation framework used by orders, customers and documents, so each team just plugs in rules."*

**What the interviewer is really checking**
That you can design a generic API that is flexible for callers, not just recite PECS.

**How I answer it**
1. A generic rule: `interface Rule<T> { Optional<Violation> check(T target); }`.
2. A validator that accepts rules written for a supertype, because a `Rule<Object>` "not null" rule should apply to an `Order`:

```java
<T> List<Violation> validate(T target, Collection<? extends Rule<? super T>> rules)
```

3. `? super T` on the rule is **consumer super**: the rule consumes a `T`. `? extends` on the collection lets callers pass a `List<NotNullRule>`.
4. Erasure consequence: to know the type at runtime (for JSON parsing) I pass `Class<T>` or a type token.
5. Keep public APIs readable: wildcards in parameters, never in return types.

**Trade-offs and what can go wrong**
- Raw types (`List`) disable checks and cause heap pollution.
- Over-generic APIs become unreadable; generalise when you have two or three real uses.
- Arrays are covariant and checked at runtime; generics are invariant and checked at compile time; mixing them causes `ArrayStoreException` or warnings.

**How I'd monitor it**
Not runtime; compiler warnings treated as errors (`-Xlint:unchecked -Werror`) in CI.

**Follow-ups to expect**
- *Why is `List<Integer>` not a `List<Number>`?* -> Otherwise you could add a `Double` into a list of integers.
- *What is a bridge method?* -> A compiler-generated method that keeps polymorphism working after erasure.
- *Example of PECS in the JDK?* -> `Collections.copy(List<? super T> dest, List<? extends T> src)`.

**60-second answer**
"Generics give compile-time type safety. For a shared validation framework I define `Rule<T>` and a validator taking `Collection<? extends Rule<? super T>>`, so a generic not-null rule written for Object also applies to Order. That's PECS: the rule consumes T, so super; the collection produces rules, so extends. Because of type erasure I pass a `Class<T>` when I need the type at runtime, and I keep wildcards out of return types so the API stays readable."

### Q11 [senior] Explain the Java Memory Model, volatile and happens-before with a real bug.
tags: java-memory-model, volatile, happens-before, visibility, double-checked-locking, concurrency, profile-java-genai

**Start here: the concepts**
- **Visibility:** without synchronisation, one thread's write may never be seen by another (CPU caches, compiler reordering).
- **happens-before:** the JMM guarantee that a write is visible to a later read: unlock -> lock, volatile write -> volatile read, `Thread.start`, `join`.
- **volatile:** visibility and ordering for one variable; **not** atomicity for `count++`.

**The live scenario (functional requirement)**
*FR: "Ops must be able to switch the assistant from the primary LLM provider to the fallback at runtime via an admin endpoint, without restart."* The admin call set `useFallback = true`, but some request threads kept calling the primary for minutes.

**What the interviewer is really checking**
Whether you understand visibility vs atomicity and pick the right tool.

**How I answer it**
1. Cause: a plain `boolean` field; JIT hoisted the read out of a loop and threads kept a stale value. There was no happens-before edge.
2. Fix for a simple flag: `volatile boolean useFallback`. A volatile write happens-before every subsequent read.
3. Better for a group of settings: an immutable `ProviderConfig` record in an `AtomicReference<ProviderConfig>`, swapped as a whole, so threads never see half-updated settings.
4. For counters use `AtomicLong`/`LongAdder`, not volatile.
5. Lazy singletons: double-checked locking needs the field `volatile`, or better, the holder-class idiom or an enum.

**Trade-offs and what can go wrong**
- `volatile` on compound actions (`check-then-act`) is still a race.
- Over-synchronising kills throughput; immutable snapshots plus atomic references avoid locks entirely.
- In a cluster this flag is per JVM; the switch should come from a config service or feature-flag system so every pod changes.

**How I'd monitor it**
A metric for calls per provider, so after the switch the primary's rate should drop to zero within seconds; alert if not.

**Follow-ups to expect**
- *Does `synchronized` give visibility?* -> Yes, releasing a monitor happens-before the next acquire of the same monitor.
- *What are `final` field semantics?* -> Correctly constructed objects' final fields are visible to all threads without synchronisation.
- *Why was DCL broken before Java 5?* -> Reordering could publish a reference before the constructor finished; volatile semantics were fixed in JSR-133.

**60-second answer**
"The JMM says a write is only guaranteed visible to another thread if there's a happens-before edge. We had a plain boolean 'use fallback provider' flag and threads kept the stale value. A volatile write happens-before later reads, so `volatile` fixes a single flag. For several related settings I swap an immutable config record in an AtomicReference, so nobody sees a half-update. Volatile doesn't make `count++` atomic, that's what atomics are for. And in a cluster the switch belongs in a feature-flag service so all pods flip."

### Q12 [mid] Pick the right collection for four requirements.
tags: collections, linkedhashmap, treemap, priorityqueue, arraydeque, lru, data-structures, profile-java-genai

**Start here: the concepts**
- **ArrayList:** O(1) index access, amortised O(1) append. **LinkedList:** rarely better in practice.
- **HashMap/HashSet:** O(1) average lookup. **LinkedHashMap:** insertion or access order. **TreeMap:** sorted keys, O(log n), range queries.
- **ArrayDeque:** fast stack/queue. **PriorityQueue:** heap, O(log n) insert, O(1) peek.

**The live scenario (functional requirement)**
*FR: (a) cache the 1,000 most recently used product prompts; (b) find which price applies at a timestamp; (c) keep the top 10 most expensive LLM calls of the day; (d) process document-ingestion jobs in arrival order.*

**What the interviewer is really checking**
That you choose by access pattern and complexity, not habit.

**How I answer it**
1. **(a) LRU:** `LinkedHashMap` with `accessOrder=true` and `removeEldestEntry` returning `size() > 1000`. For multi-threaded production I'd use Caffeine instead.
2. **(b) price at time:** `TreeMap<Instant, Price>` and `floorEntry(timestamp)`: O(log n).
3. **(c) top 10:** a **min-heap** `PriorityQueue` of size 10; if a new cost beats the smallest, poll and offer. O(n log 10).
4. **(d) FIFO:** `ArrayDeque` single-threaded, `LinkedBlockingQueue` (bounded!) between producer and consumer threads.
5. Sequenced collections (Java 21) give `getFirst()`/`getLast()`/`reversed()` uniformly on lists, deques and linked maps.

**Trade-offs and what can go wrong**
- `LinkedHashMap` LRU is not thread-safe.
- Unbounded queues hide overload until OOM; bound them and decide a rejection policy.
- `TreeMap` keys must be consistently comparable; `compareTo` inconsistent with `equals` causes surprises.

**How I'd monitor it**
Cache hit ratio and eviction count, queue depth, job wait time.

**Follow-ups to expect**
- *Why not LinkedList for a queue?* -> Poor cache locality and per-node allocation; ArrayDeque is faster.
- *HashMap vs Hashtable?* -> Hashtable is legacy and fully synchronised; use HashMap or ConcurrentHashMap.
- *Fail-fast iterator?* -> Throws `ConcurrentModificationException` on structural change during iteration.

**60-second answer**
"I pick by access pattern. Recent-prompt cache: LinkedHashMap in access order with removeEldestEntry, or Caffeine when threads share it. Price at a timestamp: TreeMap with floorEntry, log n. Top 10 costliest calls: a size-10 min-heap PriorityQueue. Ingestion jobs in order: ArrayDeque on one thread or a bounded LinkedBlockingQueue between threads. Bounding queues is important; unbounded ones just turn overload into an OutOfMemoryError later."

### Q13 [senior] Which modern Java (17 to 25) features do you use, and why?
tags: java-17, java-21, java-25, records, sealed-classes, pattern-matching, scoped-values, profile-java-genai

**Start here: the concepts**
- **Java 17 LTS:** records, sealed classes, text blocks, switch expressions, pattern matching for `instanceof`.
- **Java 21 LTS:** virtual threads, pattern matching for `switch`, record patterns, sequenced collections.
- **Java 25 LTS (Sept 2025):** scoped values final, flexible constructor bodies, compact source files, compact object headers; structured concurrency still in preview.

**The live scenario (functional requirement)**
*FR: "Model the result of an LLM call (success, refused, rate-limited, timed out) so every caller must handle every case."*

**What the interviewer is really checking**
Whether you use the features to make code safer, not just know the release list.

**How I answer it**
1. A **sealed interface** with **records**:

```java
sealed interface LlmResult permits Success, Refused, RateLimited, TimedOut {}
record Success(String text, int tokens) implements LlmResult {}
record RateLimited(Duration retryAfter) implements LlmResult {}
```

2. **Pattern matching for switch** with record patterns. The compiler checks the switch is exhaustive, so adding a new result type breaks the build everywhere it isn't handled:
   `case RateLimited(var after) -> scheduleRetry(after);`
3. **Text blocks** for prompt templates and JSON in tests.
4. **Virtual threads** for I/O-heavy services; **sequenced collections** for first/last access.
5. **Scoped values** (Java 25) to pass request context such as tenant id to deep code, instead of `ThreadLocal`, which costs a lot with millions of virtual threads.
6. On upgrades I stay on LTS releases (17 -> 21 -> 25) and Spring Boot 4 supports Java 17 to 25.

**Trade-offs and what can go wrong**
- Preview features need `--enable-preview` and may change; not for production code.
- Records are not for JPA entities.
- Sealed hierarchies across modules/packages have placement rules.

**How I'd monitor it**
n/a at runtime; I track the JDK version per service and plan LTS upgrades.

**Follow-ups to expect**
- *Why sealed over an enum?* -> Each case carries different data.
- *What did Java 11 add?* -> `var` in lambdas, the `HttpClient`, `String` helpers (`isBlank`, `lines`), single-file launch.
- *Biggest upgrade blocker 17 -> 21?* -> Libraries and bytecode tools (Lombok, Mockito, ByteBuddy) needing newer versions.

**60-second answer**
"I use modern Java to make illegal states unrepresentable. An LLM call result is a sealed interface of records (success, refused, rate-limited, timed out) and callers use a pattern-matching switch, which the compiler checks for exhaustiveness, so a new case can't be forgotten. Text blocks hold prompt templates, virtual threads handle I/O-heavy services, and on Java 25 scoped values replace ThreadLocal for request context. I stick to LTS versions: 17, 21, now 25."

### Q14 [senior] Size and configure a thread pool for a bulk file import.
tags: executorservice, thread-pool, rejection-policy, backpressure, littles-law, concurrency, profile-java-genai

**Start here: the concepts**
- **ThreadPoolExecutor:** core size, max size, queue, rejection policy, keep-alive.
- **Sizing rule of thumb:** CPU-bound ≈ number of cores; I/O-bound ≈ cores × (1 + wait time / compute time).
- **Backpressure:** slowing the producer when consumers cannot keep up.

**The live scenario (functional requirement)**
*FR: "Import a 2-million-row customer CSV nightly: validate each row, call an address-verification API (~50 ms), write to the DB, finish within 1 hour."*

**What the interviewer is really checking**
Bounded resources, a reasoned pool size, and what happens when the queue is full.

**How I answer it**
1. Budget: 2,000,000 rows / 3,600 s ≈ 560 rows/s. Each row waits ~50 ms on the API, so Little's Law: 560 × 0.05 ≈ 28 in flight. A pool of ~40 gives headroom.
2. Check the downstream: the API allows 600 requests/s and the DB pool has 20 connections; batch inserts (500 rows per batch) so DB isn't the limit.
3. Configure explicitly, never `Executors.newFixedThreadPool` (its queue is unbounded):

```java
new ThreadPoolExecutor(40, 40, 0, SECONDS, new ArrayBlockingQueue<>(1_000),
        named("import-"), new ThreadPoolExecutor.CallerRunsPolicy());
```

4. `CallerRunsPolicy` gives natural backpressure: the reader thread processes a row itself when the queue is full, so it slows reading.
5. Stream the file (`BufferedReader`, never load 2 million rows into memory), record progress (checkpoint the last line) so a failure resumes, and send bad rows to an error file instead of failing the whole job.
6. Shutdown properly: `shutdown()` then `awaitTermination`.

**Trade-offs and what can go wrong**
- Unbounded queues -> OOM. Too many threads -> context switching and API 429s.
- `AbortPolicy` drops work with an exception; acceptable only if the caller retries.
- Exceptions inside `submit()` tasks disappear unless you check the `Future`.

**How I'd monitor it**
Rows/s, queue depth, active threads, API latency and 429s, error-row count, ETA on a dashboard.

**Follow-ups to expect**
- *Would virtual threads change this?* -> Thread count stops mattering; a semaphore of ~40 still guards the API rate.
- *Spring Batch?* -> Yes for production: chunking, restartability, skip policies out of the box.
- *Why name threads?* -> Thread dumps and logs become readable.

**60-second answer**
"I size from the target: 2 million rows in an hour is about 560 per second; at 50 ms per API call Little's Law says ~28 in flight, so a pool of about 40. I build the ThreadPoolExecutor explicitly with a bounded queue and CallerRunsPolicy, so when it's full the reader slows down instead of the heap filling. I stream the file, batch the inserts, checkpoint progress and route bad rows to an error file. For a real nightly job I'd use Spring Batch, which gives chunking and restart for free."

### Q15 [architect] Design a thread-safe rate limiter in core Java for calls to an LLM provider.
tags: rate-limiter, token-bucket, concurrency, design, llm, resilience, profile-java-genai

**Start here: the concepts**
- **Token bucket:** a bucket refills at a fixed rate up to a capacity; each call takes tokens; empty bucket means wait or reject. Allows short bursts.
- **LLM quotas** are usually twofold: **requests per minute** and **tokens per minute**.
- **CAS loop:** lock-free update with `AtomicLong.compareAndSet`.

**The live scenario (functional requirement)**
*FR: "Our provider contract allows 500 requests/min and 200,000 tokens/min per API key. The assistant must never get throttled (429) at peak and must prioritise interactive chat over batch summarisation."*

**What the interviewer is really checking**
Design under concurrency, awareness of LLM-specific quotas, and knowing when not to hand-roll it.

**How I answer it**
1. **Two buckets per API key:** requests (capacity 500, refill 500/min) and tokens (capacity 200k, refill 200k/min). A call must acquire 1 request token and its **estimated** token cost (prompt tokens counted + max output tokens).
2. **Lazy refill, thread-safe:** store `availableTokens` and `lastRefillNanos`; on `tryAcquire(n)`, compute refill from elapsed time, then update. A small `ReentrantLock` per bucket is simple and fast enough; a CAS loop on a packed state is the lock-free version.
3. **Reconcile:** after the response, the provider returns actual usage; refund or charge the difference.
4. **Priority:** two pools of permits, for example 80% reserved for interactive, batch only gets what's left, or batch goes through a queue that drains only when tokens are spare.
5. **Waiting:** interactive calls wait up to 200 ms then fail fast with a friendly message; batch waits longer.
6. **Distributed reality:** with 6 pods a local bucket must be divided (500/6) or moved to Redis (Lua script for atomic refill-and-take) or the API gateway. For production I'd use Bucket4j (has Redis/Hazelcast backends) or Resilience4j RateLimiter rather than hand-rolling.

**Trade-offs and what can go wrong**
- Estimating output tokens wrong under-reserves; use `max_tokens` as the reservation and refund.
- Per-pod split wastes quota when traffic is uneven; centralised Redis adds a network hop (~1 ms).
- Clock: use `System.nanoTime()` (monotonic), not wall-clock time.

**How I'd monitor it**
Tokens and requests used vs quota per key, wait time in the limiter, 429s from the provider (should be ~0), rejected batch jobs.

**Follow-ups to expect**
- *Token bucket vs leaky bucket?* -> Leaky smooths to a constant rate; token bucket allows bursts up to capacity.
- *Sliding window?* -> More accurate counts at the window edge; more memory.
- *What if the provider still returns 429?* -> Honour `Retry-After`, exponential backoff with jitter, and lower the local rate adaptively.

**60-second answer**
"LLM providers limit both requests and tokens per minute, so I'd use two token buckets per API key. A call reserves one request plus its estimated tokens, prompt plus max output, and after the response I reconcile with actual usage. Each bucket refills lazily from `nanoTime` under a small lock, or a CAS loop. Interactive chat gets a reserved share and fails fast after 200 ms; batch only uses spare capacity. With several pods I move the buckets to Redis or use Bucket4j, and I watch provider 429s, which should stay at zero."
