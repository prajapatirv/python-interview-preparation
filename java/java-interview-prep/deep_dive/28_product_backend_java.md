# Core Java, the JVM and concurrency

Questions 86–114 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Trace a visibility bug

Two workers both read a volatile counter at 41, each computes 42 and each writes 42. Volatile visibility was satisfied throughout. AtomicInteger.incrementAndGet() makes that single update atomic. If the counter represents the last seat, use compareAndSet against the observed positive balance and retry on contention. For multiple service instances the reservation invariant must also be enforced by shared storage. Rehearse the distinction between visibility, atomicity and the scope of the invariant.

## Interview questions and answers

### Q86. Java 8: lambdas, functional interfaces, default/static methods, Optional, Streams, Date-Time API.

A lambda implements a target functional interface with one abstract method. Interfaces can share behavior through defaults and namespace helpers with static methods. Streams express bulk transformations and Optional represents an absent result at an API boundary. Use immutable java.time types such as Instant for event timestamps and ZoneId when converting for display.

### Q87. Java 9: modules, JShell, factory methods, private interface methods.

JPMS modules declare dependencies and exported packages in module-info.java, making boundaries explicit. JShell evaluates snippets interactively. List.of and related factories create unmodifiable collections and reject nulls. Private interface methods share internal code between defaults. An unmodifiable collection can still contain mutable objects.

### Q88. Java 10: local variable type inference (var); limitations of var.

var infers a local variable's static type from its initializer. It works for initialized locals and loop variables, and cannot replace a field, method return type or ordinary method parameter. A bare null gives insufficient type information. var prices = new ArrayList<Integer>() infers the concrete ArrayList type.

### Q89. Java 11: HttpClient, String utility methods, single-file source execution.

Java 11 standardized HttpClient with synchronous send and asynchronous sendAsync. Set connection and request deadlines for remote calls. String.isBlank(), strip() and lines() simplify parsing. Running java Hello.java compiles and runs a single source file for a small demonstration without a separate javac command.

### Q90. Java 14: switch expressions and yield; Java 15: text blocks.

A switch expression returns a value and must handle all relevant cases. Arrow cases avoid fall-through and a block can yield its result. Java 15 text blocks express multiline strings such as SQL with defined indentation handling. SQL values still belong in bound parameters.

### Q91. Java 16: records and pattern matching for instanceof.

A record declares components and derives accessors, equality, hash code and a representation, making it useful for an immutable-by-convention DTO. Its component references are final, so copy mutable collections defensively. Pattern matching with instanceof binds a typed variable in the branch where the test succeeds.

### Q92. Java 17: sealed classes, records, pattern matching for instanceof; LTS changes.

Java 17 finalized sealed types: a sealed result interface can restrict direct implementations to Success and Failure, each declaring its permitted continuation. Records and instanceof patterns were finalized in 16 and are available in 17. An LTS migration also needs build-tool, dependency, runtime flag and integration checks.

### Q93. Java 21: virtual threads, record patterns, pattern matching for switch, sequenced collections.

Virtual threads make blocking I/O concurrency cheaper. Record patterns deconstruct record fields, and pattern switches dispatch on type with exhaustiveness checks. Sequenced collections standardize first, last and reversed views for ordered collections. For example a sealed payment result can be handled exhaustively with record-pattern switch arms.

### Q94. Which Java 17/21 features have you used in production? What problem did they solve?

Use an actual migration story and identify the first release supporting the feature. Example rehearsal: replacing transport POJOs with records removed hand-maintained equality and uncovered a mutable list needing List.copyOf. For virtual threads compare concurrent requests, p95, CPU and dependency saturation at equal load. Only claim production use or measured gains you can substantiate.

### Q95. Explain abstraction, encapsulation, inheritance and polymorphism with backend examples.

Abstraction exposes an operation such as charge through a PaymentGateway. Encapsulation keeps balance updates behind account methods that enforce invariants. Inheritance permits a specialized type to extend shared behavior. Polymorphism lets checkout invoke the same gateway method while runtime dispatch selects a card or wallet implementation. Test the common behavioral contract across implementations.

### Q96. Overloading vs overriding; compile-time vs runtime polymorphism.

Overload selection uses declared argument types at compile time. Overriding selects the implementation of that chosen instance signature by receiver type at runtime. If Object x holds a String, calling log(x) chooses log(Object) even if log(String) exists. A subclass may still override log(Object).

### Q97. Interface vs abstract class; composition vs inheritance.

An interface models a capability across unrelated types. An abstract class can provide state, initialization and a template method for closely related implementations. Composition delegates work to collaborators, for example injecting RetryPolicy into a client. Use inheritance where subtype behavior satisfies every caller of the base contract.

### Q98. Immutable class design; String immutability and String pool.

Keep fields private and final, validate at construction, avoid leaking this, prevent overriding of invariants and defensively copy mutable inputs and outputs. String operations create or reuse immutable values, allowing safe sharing and interning of equal literals. Compare content with equals because separately constructed strings may have different identities.

### Q99. == vs equals(); final vs finally vs finalize(); static keyword.

For references == compares identity and equals delegates to value semantics when implemented. final restricts reassignment, overriding or inheritance depending on placement. finally executes cleanup on ordinary control transfer. finalize is an unreliable historical GC hook. static members belong to the class, so mutable static state needs coordination across threads.

### Q100. Checked vs unchecked exceptions; custom exception design; try-with-resources.

Checked exceptions require declaration or handling. RuntimeException subclasses are unchecked. Define exceptions around meaningful recovery decisions, for example a retryable gateway timeout versus an invalid order, preserving causes. try-with-resources closes AutoCloseable resources in reverse declaration order and preserves cleanup failures as suppressed exceptions.

### Q101. Shallow copy vs deep copy; cloning; serialization basics.

A shallow copy duplicates the container and shares nested references. A deep copy reconstructs mutable nested state, preserving shared identity if required. Object.clone normally performs a field-wise shallow copy, so explicit copy constructors clarify intent. Serialization encodes state for reconstruction and needs a compatible schema. Use constrained data formats at untrusted boundaries.

### Q102. JVM memory areas; heap vs stack; metaspace; class loading process.

Shared heap stores ordinary objects, per-thread stacks hold frames and local variables, and HotSpot metaspace uses native memory for class metadata. Class loading finds the definition, linking verifies and prepares it and resolves references, and initialization runs static initializers on active use. Excess generated classes can exhaust metaspace even when heap usage is modest.

### Q103. JIT compiler; garbage collection; G1 vs ZGC basics.

The JIT compiles hot methods using runtime profiles and can deoptimize when assumptions fail. GC reclaims unreachable objects. G1 collects regions and balances throughput with pause targets. ZGC performs much work concurrently to reduce pauses, with CPU and memory headroom costs. Compare pause percentiles, allocation rate and total throughput on a warmed representative workload.

### Q104. How do you investigate memory leak, high CPU, high GC or OutOfMemoryError?

Identify the OOM category first: heap, direct buffer, metaspace or native thread. Compare post-GC live-set trends and allocation profiles, then inspect dominators and paths to GC roots in a safely captured dump. For high CPU correlate hot threads and repeated stack samples with JFR. Frequent collections with stable live set suggest allocation churn; a rising retained set warrants leak investigation.

### Q105. Process vs thread; thread lifecycle; Runnable vs Callable.

Processes isolate address spaces, while threads share heap state and keep separate stacks. Java states include NEW, RUNNABLE, BLOCKED, WAITING, TIMED_WAITING and TERMINATED. Runnable returns no value and cannot declare checked exceptions. Callable returns a result or throws, which an executor conveys through a Future.

### Q106. synchronized vs volatile; intrinsic lock vs ReentrantLock.

synchronized provides mutual exclusion and visibility through monitor release/acquire. volatile publishes individual reads and writes, but increment is still read-modify-write. ReentrantLock supports timed or interruptible acquisition and multiple conditions. Always unlock in finally. Use one consistently applied lock for invariants spanning multiple fields.

### Q107. AtomicInteger and CAS; race condition; deadlock and livelock.

CAS replaces an expected value atomically. AtomicInteger.incrementAndGet retries when another writer wins. Multiple atomic fields still cannot jointly enforce a transfer invariant. A race makes results depend on interleaving. Deadlock forms a wait cycle, preventable with lock ordering. Livelock has active contenders repeatedly yielding without progress, mitigated by asymmetric or randomized backoff.

### Q108. wait(), notify(), notifyAll(); sleep() vs wait().

Call wait and notify while owning the same object's monitor. wait releases it and reacquires it before returning. Recheck the condition in a while loop for spurious wakeups and competing consumers. notify selects one waiter and notifyAll lets all recheck. sleep pauses a thread while retaining any locks it holds.

### Q109. ExecutorService; thread pool sizing; rejection policies; graceful shutdown.

Size CPU pools around effective core capacity and size blocking concurrency against measured wait times and downstream limits. Bound queues so overload becomes visible. Rejection can fail fast or apply caller-runs backpressure where blocking the caller is acceptable. On shutdown stop admission, call shutdown, await with a deadline and interrupt stragglers that honor cancellation.

### Q110. Future vs CompletableFuture; thenApply vs thenCompose; allOf vs anyOf.

Future.get waits for one result. CompletableFuture composes stages: thenApply maps a value and thenCompose flattens an asynchronous result. allOf completes after all inputs and returns Void, so retain original futures for results. anyOf reports the first completion, possibly exceptional. Set timeouts and choose executors deliberately for blocking stages.

### Q111. ConcurrentHashMap internals; BlockingQueue; producer-consumer problem.

ConcurrentHashMap coordinates per-bin writes and supplies atomic per-key updates. A bounded BlockingQueue coordinates a producer and consumer by making put wait for capacity and take wait for data. This bounds backlog. Define an interruption or end-of-stream policy so consumers can terminate after producers finish.

### Q112. CountDownLatch vs CyclicBarrier vs Semaphore.

A CountDownLatch opens once after N completions, useful for startup readiness. A CyclicBarrier makes a fixed number of participants rendezvous repeatedly between phases. A Semaphore limits concurrent permit holders, such as database calls. Release in finally only after successful acquisition, and set a wait deadline when protecting a request path.

### Q113. ThreadLocal use cases and memory-leak risks.

ThreadLocal gives each thread independent context, such as a correlation ID. A pooled worker survives individual requests, so stale values may leak into later requests or retain large objects. Set on entry and remove in finally. When crossing executor boundaries explicitly propagate the required context.

### Q114. Virtual threads vs platform threads; when not to use virtual threads.

Virtual threads let many I/O-bound tasks block in a thread-per-request style while a smaller group of platform threads executes runnable work. CPU-bound work still competes for the same cores. Limit scarce database connections with a pool or semaphore and measure pinning behavior for your JDK. A million inexpensive threads can still overwhelm a dependency.
