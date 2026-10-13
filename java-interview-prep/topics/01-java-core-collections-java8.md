---
id: 01-java-core
title: Java Core, Collections, Streams (Java 8+)
focus: Fundamentals every Lead is expected to explain crisply and with trade-offs
deep_dive: 01,02
examples: 01_java8_core,02_collections
---
Lead interviews start here to check depth, not definitions. Always add "when it breaks in production".

### Q1 [basic] What is the difference between JDK, JRE and JVM?
JVM runs bytecode. JRE = JVM + core libraries. JDK = JRE + compiler (`javac`) and tools (`jar`, `jcmd`, `jshell`). Since Java 11 there is no separate JRE download; you ship the JDK or a trimmed runtime made with `jlink`.

### Q2 [basic] What is the equals/hashCode contract and what breaks if you violate it?
If `a.equals(b)` then `a.hashCode() == b.hashCode()`. Equal objects must land in the same hash bucket.
- Override `equals` only -> `HashMap.get()` returns null for an equal key because it looks in the wrong bucket.
- Mutable fields inside `hashCode` -> the object "disappears" from a `HashSet` after you change it.
- Use `Objects.equals` / `Objects.hash`, or a `record`, which generates both.

### Q3 [basic] Why is String immutable and what is the String pool?
Immutability makes strings thread-safe, cacheable (hash is computed once) and safe as map keys and security parameters. Literals are stored in the pool, so `"a" == "a"` is true but `new String("a") == "a"` is false. Use `StringBuilder` in loops (`StringBuffer` is the old synchronized version).

### Q4 [basic] Abstract class vs interface - which one when?
Interface = contract (can have `default`, `static`, `private` methods since Java 8/9; no instance state). Abstract class = shared state and partial implementation. A class can implement many interfaces but extend one class. Prefer interfaces for APIs; use an abstract class when subclasses share fields or a template-method skeleton.

### Q5 [basic] Checked vs unchecked exceptions? What is try-with-resources?
Checked exceptions (`IOException`) must be declared or caught; unchecked (`RuntimeException`) need not. Modern Spring code uses unchecked domain exceptions and handles them in one place. `try (var in = ...)` closes any `AutoCloseable` automatically, even on exception, and keeps the original exception with the close failures attached as *suppressed*.

### Q6 [basic] `final` vs `finally` vs `finalize`?
`final`: constant / not overridable / not subclassable. `finally`: block that runs after try/catch (except JVM exit). `finalize()`: deprecated for removal - unreliable; use `try-with-resources` or `Cleaner`.

### Q7 [intermediate] How does HashMap work internally (Java 8+)?
Array of buckets; index = `(n-1) & hash(key)`. Collisions form a linked list; when a bucket reaches 8 entries and the table is at least 64 long, it becomes a red-black tree (O(log n) worst case). Default capacity 16, load factor 0.75, resize doubles the table and redistributes. Not thread-safe: concurrent resize can lose data.
> Follow-up they may ask: why capacity is a power of two (fast bit-mask index).

### Q8 [intermediate] HashMap vs Hashtable vs ConcurrentHashMap vs Collections.synchronizedMap?
`Hashtable` and `synchronizedMap` lock the whole map. `ConcurrentHashMap` (Java 8+) uses CAS plus per-bucket `synchronized`, so reads are lock-free and writes lock only one bucket. It forbids null keys/values and gives atomic `computeIfAbsent`, `merge`. Prefer it for shared caches/counters.

### Q9 [intermediate] ArrayList vs LinkedList? Fail-fast vs fail-safe iterators?
ArrayList: array, O(1) index, O(n) insert in the middle, cache friendly - the default choice. LinkedList: O(1) add/remove at the ends, but O(n) access and more memory; rarely wins in practice. Fail-fast iterators (`ArrayList`, `HashMap`) throw `ConcurrentModificationException` if the structure changes during iteration; fail-safe ones (`CopyOnWriteArrayList`, `ConcurrentHashMap`) iterate on a snapshot / weakly consistent view.

### Q10 [intermediate] Comparable vs Comparator? HashSet vs LinkedHashSet vs TreeSet?
`Comparable` = natural order inside the class (`compareTo`); `Comparator` = external, composable order (`Comparator.comparing(Emp::dept).thenComparing(Emp::salary).reversed()`). HashSet: O(1), no order. LinkedHashSet: insertion order. TreeSet: sorted, O(log n), needs ordering consistent with `equals`.

### Q11 [intermediate] What is a functional interface? Name the common ones.
An interface with one abstract method; a lambda or method reference implements it. `Function<T,R>`, `Predicate<T>`, `Consumer<T>`, `Supplier<T>`, `BiFunction`, `UnaryOperator`, `Runnable`, `Callable`. Lambdas capture only effectively-final variables, and `this` inside a lambda is the enclosing class (unlike an anonymous class).

### Q12 [intermediate] Intermediate vs terminal stream operations? map vs flatMap?
Intermediate ops (`filter`, `map`, `sorted`, `distinct`) are lazy and return a stream; nothing runs until a terminal op (`collect`, `forEach`, `reduce`, `findFirst`). A stream can be consumed once. `map` is 1->1; `flatMap` is 1->many and flattens: `orders.stream().flatMap(o -> o.items().stream())`.

### Q13 [intermediate] Write a stream that groups employees by department and gets the average salary.
```java
Map<String, Double> avg = emps.stream()
    .collect(Collectors.groupingBy(Employee::dept,
             Collectors.averagingDouble(Employee::salary)));
```
Also know `partitioningBy`, `toMap` (needs a merge function for duplicate keys or it throws), `counting`, `joining`, `teeing` (Java 12).

### Q14 [intermediate] How should Optional be used - and abused?
Use it as a **return type** to say "may be empty": `findById(id).map(...).orElseThrow(NotFound::new)`. Don't use it for fields, method parameters or collections (return an empty list). Avoid `get()` without `isPresent()`; prefer `orElseGet` (lazy) over `orElse` (always evaluated) for expensive defaults.

### Q15 [intermediate] How do you make a class truly immutable?
`final` class, `private final` fields, no setters, defensive copies of mutable inputs/outputs (dates, lists - or `List.copyOf`), no `this` escape in the constructor. Today: use a `record` (shallow immutable - still copy collections inside the compact constructor). Immutable objects are thread-safe by design.

### Q16 [advanced] When does `parallelStream()` hurt?
It uses the shared common ForkJoinPool, so a blocking call (DB/HTTP) inside starves every other parallel stream in the JVM. It helps only for CPU-bound work on large, cheap-to-split data (arrays, `ArrayList`) with stateless, non-blocking lambdas. For I/O, use an explicit executor or virtual threads. Always measure.

### Q17 [advanced] Explain generics, type erasure and PECS.
Generics are checked at compile time and erased at runtime (`List<String>` and `List<Integer>` are both `List`), so you cannot do `new T()` or `instanceof List<String>`. PECS: **P**roducer **E**xtends, **C**onsumer **S**uper - read from `List<? extends Number>`, write into `List<? super Integer>`. `Collections.copy(dest, src)` is the classic example.

### Q18 [advanced] How can a Java application leak memory despite the GC?
GC frees only unreachable objects, so leaks are *reachable-but-unused* objects: static maps/caches without eviction, listeners never removed, `ThreadLocal` not cleared on pooled threads, unclosed resources, classloader leaks on redeploy, and a mutable key in a `HashMap`. Diagnose with a heap dump (`jcmd <pid> GC.heap_dump`) in Eclipse MAT: find the dominator tree and "path to GC roots".

### Q19 [advanced] Why is Java serialization discouraged and what is serialVersionUID for?
Default deserialization can instantiate arbitrary classes - a well-known security hole (gadget chains); it also freezes your class layout. `serialVersionUID` is the version stamp; a mismatch throws `InvalidClassException`. Prefer JSON/Avro/Protobuf with an explicit schema. If you must, use serialization filters (`ObjectInputFilter`).

### Q20 [advanced] What is the difference between `Comparable` consistency with equals, and why does `BigDecimal` surprise people?
`new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is **false** (scale differs) but `compareTo` returns 0. So a `HashSet` keeps both, while a `TreeSet` keeps one. For money use `BigDecimal` with explicit scale and `RoundingMode`, never `double`; construct from `String`, not `double`.

### Q21 [design] Design a thread-safe LRU cache. What would you use in production?
Interview version: `LinkedHashMap` with `accessOrder=true` and `removeEldestEntry`, wrapped in `Collections.synchronizedMap` (or a `ReentrantLock`).
```java
class Lru<K,V> extends LinkedHashMap<K,V> {
  private final int max;
  Lru(int max){ super(16,0.75f,true); this.max=max; }
  protected boolean removeEldestEntry(Map.Entry<K,V> e){ return size()>max; }
}
```
Production: use **Caffeine** (window-TinyLFU, async loading, TTL, stats) or Redis for a shared cache. Discuss invalidation, stampede protection (`LoadingCache` loads once per key) and cache metrics.

### Q22 [design] Design an exception strategy for a layered service (controller -> service -> repository).
- One `AppException` base (unchecked) with an error code; subclasses by *decision*: `NotFoundException`, `ValidationException`, `ConflictException`, `DependencyUnavailableException` (retryable).
- Lower layers wrap with a cause (`throw new X("...", e)`) and never leak persistence types upward.
- One `@RestControllerAdvice` maps exceptions to HTTP status + a stable error body (RFC 7807 `ProblemDetail`).
- Log once, at the boundary, with a correlation id; never log and rethrow at every layer.

### Q23 [design] Design an in-memory deduplication and top-N analytics component for a stream of 10 million events per hour.
- **Requirements:** exact vs approximate counts, memory ceiling, one JVM or many.
- **Approach:** dedupe with a bounded `Caffeine` cache or a `Set` of event ids per time window; top-N with a `ConcurrentHashMap<String, LongAdder>` plus a size-N `PriorityQueue` (min-heap) built at read time.
- **Trade-offs:** exact counts cost memory; for very high cardinality use a Bloom filter / Count-Min Sketch and accept a small error.
- **Failure modes:** unbounded key growth (OOM) - always cap and expire; hot keys - `LongAdder` over `AtomicLong`.
