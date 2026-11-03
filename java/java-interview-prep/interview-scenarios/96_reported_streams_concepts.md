---
id: reported-streams-concepts
title: Reported rounds, Java Streams 2/2: 15 concept questions, and how to explain them under pressure
stack: java
skill: java-core
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). The 15 concept questions
from the "35 Java Streams questions for SDE-2" list; the coding half is bank 95. Behaviour claimed here was run in
`examples/21_coding_interview/07_streams_sde2_employee_drills.java` unless it says otherwise.

### Q1 [fresher] Stream vs Collection: what is the difference?
tags: streams, collection, lazy, single-use, data-vs-computation, java8, reported-streams

**Start here: the concepts**
- A **Collection** stores data. A **Stream** describes a computation over data and stores nothing.

**The live scenario (functional requirement)**
*FR: "Export today's orders."* The `List<Order>` holds them in memory. `orders.stream().filter(...).map(...)` is a recipe that runs only when the terminal operation asks for a result.

**What the interviewer is really checking**
Whether you can give the differences that change how you write code, not just "one stores data".

**How I answer it** (120-second answer, point by point)

| | Collection | Stream |
|---|---|---|
| Purpose | Holds elements | Computes over elements |
| Evaluation | Eager, in memory | Lazy, on demand |
| Reuse | Any number of times | Once |
| Iteration | External, your loop | Internal, the library's |
| Size | Finite | Can be infinite (`Stream.iterate`) |
| Changes source | `add` and `remove` | No, it produces a new result |
| Parallel | Your own threads | `parallel()` |

**Trade-offs and what can go wrong**
- A stream from `Files.lines` or a database holds a resource, so close it with try-with-resources.
- Modifying the source collection during a pipeline gives undefined or failing behaviour.

**Follow-ups to expect**
- *Can a stream be infinite?* -> Yes, with `generate` or `iterate`, as long as something like `limit` stops it.

**60-second answer**
"A collection stores data and a stream describes a computation over it. Collections are eager and reusable, and you control the iteration. A stream is lazy, single-use, stores nothing, can be infinite, and uses internal iteration, which is what lets the library short-circuit and parallelise. I use a collection to hold data and a stream to transform it."

### Q2 [fresher] Intermediate vs terminal operations.
tags: streams, intermediate, terminal, lazy, pipeline, java8, reported-streams

**Start here: the concepts**
- **Intermediate** operations return a stream and do no work: `filter`, `map`, `flatMap`, `distinct`, `sorted`, `peek`, `limit`, `skip`.
- **Terminal** operations start execution and produce a result: `collect`, `toList`, `forEach`, `reduce`, `count`, `min`, `max`, `findFirst`, `anyMatch`.

**The live scenario (functional requirement)**
A developer writes `orders.stream().filter(this::audit);` and wonders why no audit row ever appears. There is no terminal operation, so nothing runs.

**What the interviewer is really checking**
That you understand laziness, not just the two lists.

**How I answer it** (120-second answer, point by point)
1. I traced `filter` then `map` with `findFirst` over 1, 2, 3, 4. Before the terminal call there were zero operations.
2. After it, the trace was `filter 1, filter 2, map 2`. Elements flow one at a time, and 3 and 4 were never touched.
3. So a pipeline isn't "filter everything, then map everything". It's vertical, which is what makes short-circuiting possible.
4. Intermediates also split into **stateless** (`filter`, `map`) and **stateful** (`sorted`, `distinct`), which matters for memory and parallel cost.

**Trade-offs and what can go wrong**
- Don't call `findFirst` and expect side effects in `map` to have run for every element.

**Follow-ups to expect**
- *Which terminal operations short-circuit?* -> `findFirst`, `findAny`, `anyMatch`, `allMatch`, `noneMatch`.

**60-second answer**
"Intermediate operations like filter and map return a new stream and only build the recipe. A terminal operation like collect or findFirst triggers it. I once traced this: with findFirst over four numbers, only two were looked at, and elements flow through one at a time. So a stream without a terminal operation does nothing at all, which is a classic bug."

### Q3 [fresher] map() vs flatMap().
tags: streams, map, flatmap, one-to-many, optional, java8, reported-streams

**Start here: the concepts**
- `map`: one input gives exactly one output.
- `flatMap`: one input gives a stream of zero or more outputs, and they are joined into one stream.

**The live scenario (functional requirement)**
*FR: "All line items across all orders."* `orders.map(Order::items)` gives a stream of *lists*. `orders.flatMap(o -> o.items().stream())` gives a stream of *items*.

**What the interviewer is really checking**
A clear mental model, and whether you can use `flatMap` for the zero-or-one case too.

**How I answer it** (120-second answer, point by point)
1. `Stream<Order>` with `map(Order::items)` is `Stream<List<Item>>`, usually not what you want.
2. `flatMap` flattens one level: `Stream.of(List.of("a","b"), List.of("c")).flatMap(List::stream)` gives `a, b, c`.
3. Zero-or-one is the less obvious use: return `Stream.empty()` to drop an element. That is how I skip bad rows while parsing (Q15).
4. `Optional` has the same pair: use `flatMap` when the mapper already returns an `Optional`, or you get `Optional<Optional<T>>`.

**Trade-offs and what can go wrong**
- Java 16's `mapMulti` avoids allocating a small stream per element, which helps in hot paths.

**Follow-ups to expect**
- *Words in sentences?* -> `flatMap(s -> Arrays.stream(s.split(" ")))`.

**60-second answer**
"map is one-to-one, while flatMap is one-to-many, and it flattens the results into one stream. Mapping orders to their items gives a stream of lists; flatMap gives a stream of items. Since flatMap can return an empty stream, it's also how I drop elements while transforming, such as rows that fail to parse. Optional has the same pair, for mappers that already return an Optional."

### Q4 [fresher] filter() vs map().
tags: streams, filter, map, predicate, function, java8, reported-streams

**Start here: the concepts**
- `filter(Predicate)` decides **which** elements continue. The elements are unchanged.
- `map(Function)` decides **what** each element becomes. The count is unchanged.

**The live scenario (functional requirement)**
*FR: "Emails of active users."* `users.stream().filter(User::active).map(User::email).toList()`.

**What the interviewer is really checking**
The basic model, and that you put filters first.

**How I answer it** (120-second answer, point by point)
1. `filter` can reduce the count and never changes the type. `map` keeps the count and can change the type.
2. Order matters for cost: filter first when you can, so `map` runs on fewer elements, especially if the mapping is expensive.
3. Common trap: `map(u -> u.active())` gives a stream of booleans, not active users.

**Trade-offs and what can go wrong**
- Lambdas in `filter` and `map` should be side-effect free. Parallel execution and short-circuiting make side effects unreliable.

**Follow-ups to expect**
- *Filter on a mapped value?* -> `map` first when the mapping is cheap and the filter needs it, otherwise filter on the original.

**60-second answer**
"filter takes a predicate and decides which elements pass, so the count may drop but the type doesn't change. map takes a function and transforms each element, so the count stays the same but the type may change. I put filters first so that later steps do less work, and I keep both free of side effects."

### Q5 [mid] map() vs peek().
tags: streams, peek, map, side-effects, count-optimisation, debugging, java9, reported-streams

**Start here: the concepts**
- `map` returns a transformed element. `peek` runs a side effect and passes the same element along.
- The Javadoc says `peek` exists **mainly for debugging**.

**The live scenario (functional requirement)**
A team writes `orders.stream().peek(this::sendEmail).count()` to email every order and report the total. In production no emails go out, and no error appears.

**What the interviewer is really checking**
Whether you know `peek` can be skipped completely. This is the trap.

**How I answer it** (120-second answer, point by point)
1. Since Java 9, `count()` can skip the pipeline if the size is known up front. I ran it: `List.of(1,2,3).stream().peek(list::add).count()` returns 3, and the list stays **empty**.
2. Add a `filter`, so the size isn't known, and `peek` does run. So the behaviour depends on the shape of the pipeline. That makes it a hidden bug waiting for a refactor.
3. It also misses elements after a short-circuit: `findFirst` stops the stream early.
4. Rule: `peek` for temporary debug logging only. Business side effects go in `forEach`, or better, in a plain loop.

**Trade-offs and what can go wrong**
- `peek` that mutates an object (`peek(o -> o.setStatus(...))`) compiles and sometimes works, and it is exactly the unreliability above.

**Follow-ups to expect**
- *Why not `map` with a side effect?* -> It has the same problem and misleads the reader.

**60-second answer**
"map transforms and peek just looks. The important thing is that peek isn't guaranteed to run. Since Java 9, count can skip the pipeline when the size is already known, so a peek with a side effect silently does nothing. I've verified that with a list that stayed empty. Add a filter and it runs again, which makes this a nasty bug. So peek is only for debugging, and business side effects go in forEach or a loop."

### Q6 [fresher] findFirst() vs findAny().
tags: streams, findfirst, findany, parallel, encounter-order, java8, reported-streams

**Start here: the concepts**
- `findFirst` returns the first element in **encounter order**.
- `findAny` returns any element and may be faster in parallel.

**The live scenario (functional requirement)**
*FR: "Check any available warehouse with stock."* Any one will do, so `parallelStream().filter(...).findAny()` can return as soon as one thread finds a match.

**What the interviewer is really checking**
That the difference only shows in parallel.

**How I answer it** (120-second answer, point by point)
1. In a sequential stream, both usually return the first match. Don't rely on that for `findAny`, because the spec doesn't promise it.
2. In a parallel stream, `findFirst` must coordinate to keep order. I ran `range(0, 1000).parallel().boxed().findFirst()` and it returned 0.
3. `findAny` has no such duty, so it can be cheaper.
4. Both return `Optional`, and both throw NPE if the selected element is null.

**Trade-offs and what can go wrong**
- Use `findFirst` if the result must be reproducible. `findAny` can change between runs.

**Follow-ups to expect**
- *Do you just need a yes or no?* -> `anyMatch` says it directly.

**60-second answer**
"findFirst respects encounter order, while findAny can return any element. Sequentially they usually behave the same. In a parallel stream, findFirst must coordinate between threads to keep order, whereas findAny can return as soon as any thread finds a match, so it can be faster. I use findAny when any match will do, and findFirst when the result must be reproducible. If I only need yes or no, anyMatch is clearer."

### Q7 [mid] reduce() vs collect().
tags: streams, reduce, collect, immutable-reduction, mutable-reduction, identity, java8, reported-streams

**Start here: the concepts**
- `reduce` combines **immutable values** into one, making a new value at each step.
- `collect` puts elements into a **mutable container**, one per thread, and merges the containers.

**The live scenario (functional requirement)**
*FR: "Join 100,000 order ids into one string."* `reduce("", String::concat)` is O(n squared), because each step copies the string so far. `collect(joining(","))` is O(n).

**What the interviewer is really checking**
Whether you know which to use, and the identity and associativity rules.

**How I answer it** (120-second answer, point by point)
1. `reduce` suits sums, products and max: `IntStream.reduce(0, Integer::sum)`.
2. `collect` suits lists, maps, strings and anything built up.
3. Rules for `reduce`, needed for parallel to be correct: the identity must truly be neutral, and the operation must be associative. `reduce(10, Integer::sum)` in parallel adds 10 once *per split*, which gives a wrong total. `reduce(0, (a, b) -> a - b)` isn't associative, so it is also wrong.
4. Never mutate inside `reduce`. Adding to a shared list in a parallel `reduce` corrupts it. That is what `collect` exists to prevent.

**Trade-offs and what can go wrong**
- For plain sums, `sum()` on a primitive stream beats both: no boxing.

**Follow-ups to expect**
- *Three-argument reduce?* -> Identity, accumulator, combiner: for when the result type differs. Usually `collect` is clearer.

**60-second answer**
"reduce is for combining immutable values, like a sum, where each step produces a new value. collect is mutable reduction: each thread fills its own container and they're merged, which is right for lists, maps and strings. Joining strings with reduce is quadratic; joining collector is linear. For reduce to be correct in parallel, the identity must be truly neutral and the operation associative. Reducing with an identity of 10 gives a wrong answer."

### Q8 [fresher] groupingBy() vs partitioningBy().
tags: streams, groupingby, partitioningby, boolean, empty-keys, java8, reported-streams

**Start here: the concepts**
- `groupingBy(Function)`: any key type, any number of groups, and only the keys it saw.
- `partitioningBy(Predicate)`: exactly two groups, `true` and `false`, **always both present**.

**The live scenario (functional requirement)**
*FR: "Pass and fail counts for today's batch."* If nothing failed, the report must say 0 failed, and not throw an NPE on `map.get(false)`.

**What the interviewer is really checking**
The empty-key difference.

**How I answer it** (120-second answer, point by point)
1. On an empty stream I got `{false=0, true=0}` from `partitioningBy`, and `{}` from `groupingBy` with the same predicate.
2. So `partitioningBy` for a yes/no split, since the caller needs no null checks.
3. `groupingBy` for anything with more than two values: department, month, status.
4. Both take a downstream collector.

**Trade-offs and what can go wrong**
- With `groupingBy(x -> x > 0, counting())`, `map.get(false)` is null when nothing matched, and unboxing it to `long` throws NPE.

**Follow-ups to expect**
- *Internally?* -> `partitioningBy` uses a small two-slot map, not a `HashMap`.

**60-second answer**
"groupingBy works with any key and creates a group only for keys it has seen. partitioningBy takes a predicate and always returns both true and false keys, even for an empty stream. I checked that: one gives false=0, true=0 and the other gives an empty map. So for a yes/no split, partitioningBy saves null checks. For more than two groups, groupingBy."

### Q9 [fresher] What is lazy evaluation?
tags: streams, lazy-evaluation, short-circuit, pipeline, infinite-stream, java8, reported-streams

**Start here: the concepts**
- **Lazy** means do no work until a result is needed, and then only as much as needed.

**The live scenario (functional requirement)**
*FR: "Is there any order over 1 crore in the 5 million rows?"* With `anyMatch`, the pipeline stops at the first match instead of checking all rows.

**What the interviewer is really checking**
Why laziness has practical value.

**How I answer it** (120-second answer, point by point)
1. Intermediate operations build the pipeline, and the terminal operation pulls elements through it.
2. Gains: short-circuiting (the first match ends the work), fusing several steps into one pass over the data, and infinite sources: `Stream.iterate(1, n -> n * 2).limit(10)`.
3. A cost: errors appear late. Building the stream succeeds, and the exception comes at the terminal operation, with a stack trace that may not point at the line you expect.
4. Stateful steps like `sorted` must see everything, so they partly defeat laziness.

**Trade-offs and what can go wrong**
- A lazy stream over a closed resource fails when the terminal runs. Returning `Stream<T>` from a method inside try-with-resources is a classic bug, because the file is closed by the time anyone reads it.

**Follow-ups to expect**
- *Is `Optional` lazy?* -> `orElseGet` is, and `orElse` isn't: its argument is always evaluated.

**60-second answer**
"Lazy evaluation means intermediate operations don't run until a terminal operation asks for a result, and then only as much work happens as needed. That allows short-circuiting, so anyMatch can stop at the first hit, and it allows infinite streams with limit. The cost is that exceptions show up at the terminal operation, and returning a stream from inside try-with-resources fails because the resource is already closed."

### Q10 [fresher] Can a Stream be reused?
tags: streams, reuse, illegalstateexception, supplier, java8, reported-streams

**Start here: the concepts**
- No. After a terminal operation the stream is consumed.

**The live scenario (functional requirement)**
A method stores a `Stream<Order>` in a field to compute both the count and the total. The second call throws `IllegalStateException: stream has already been operated upon or closed`.

**What the interviewer is really checking**
The exception's name, and the fix.

**How I answer it** (120-second answer, point by point)
1. A second terminal operation throws `IllegalStateException`. I confirmed this.
2. Why: a stream may have no stored data. It could be reading a file or a socket, so "go back to the start" has no general meaning.
3. Fix 1: a `Supplier<Stream<T>>`, which builds a fresh one each time: `Supplier<Stream<Integer>> s = () -> list.stream();`.
4. Fix 2: collect to a `List` first, and stream that as needed.
5. Fix 3, for multiple results in one pass: `Collectors.teeing` (Java 12+) or `summaryStatistics`.

**Trade-offs and what can go wrong**
- Don't return or store streams as fields. Return a `List`, unless laziness is the point.

**Follow-ups to expect**
- *Is a stream reused by chaining?* -> Each intermediate call links to the previous stream, and calling two operations on the same variable throws too.

**60-second answer**
"No. After a terminal operation, another call throws IllegalStateException, because a stream isn't data. It might be reading a file, so there's no general way back to the start. If I need it twice, I use a Supplier that builds a new stream, or collect to a list first. For two results from one pass, I'd use Collectors.teeing or summaryStatistics."

### Q11 [mid] Sequential vs parallel streams.
tags: streams, parallel, forkjoinpool, spliterator, commonpool, java8, reported-streams

**Start here: the concepts**
- `parallel()` splits the source with a **Spliterator**, runs parts on the **ForkJoinPool common pool**, and combines the results.
- The whole pipeline runs one way or the other. The last `parallel()` or `sequential()` call wins.

**The live scenario (functional requirement)**
*FR: "Compute a risk score over 2 million in-memory records, CPU-only, in a nightly job."* This is a good fit.

**What the interviewer is really checking**
How it works, and that you don't assume parallel is faster.

**How I answer it** (120-second answer, point by point)
1. Source splits, each part is processed, results are merged. The default pool has CPU cores minus 1 workers, plus the calling thread.
2. It wins when: the data is large, the per-element work is CPU-heavy, the source splits well (`ArrayList`, arrays, `IntStream.range`), and the operations are stateless.
3. It loses on: small data, where overhead dominates; `LinkedList` and `Stream.iterate`, which split badly; and `limit` or `sorted` on ordered data, which need coordination.
4. Rule from the Java docs: measure with JMH before deciding.

**Trade-offs and what can go wrong**
- All parallel streams in the JVM share one pool by default.
- In Kubernetes, the pool size follows the container's CPU limit, so a 1-CPU pod gets little or no parallelism.

**Follow-ups to expect**
- *Custom pool?* -> `pool.submit(() -> stream.parallel()...)` works but relies on implementation behaviour. Prefer an explicit executor when you need isolation.

**60-second answer**
"A parallel stream splits its source with a Spliterator, runs the parts on the common ForkJoinPool and merges the results. It helps only with large data, CPU-heavy work, a source that splits well such as an array, and stateless operations. It hurts on small data, linked lists, and ordered limit or sorted. It also shares one pool across the JVM. So I treat it as an optimisation that I measure first, and not as a default."

### Q12 [senior] When should you avoid parallelStream()?
tags: streams, parallelstream, blocking-io, common-pool, thread-safety, shared-state, reported-streams

**Start here: the concepts**
- The common pool is **shared by the entire JVM**. Blocking one of its threads hurts every other user.

**The live scenario (functional requirement)**
A team calls a REST API per order inside `parallelStream()` on a request path. Under load, unrelated parallel streams stall too, and p99 latency climbs across the service.

**What the interviewer is really checking**
This is the senior-level production answer.

**How I answer it** (120-second answer, point by point)
Short answer: avoid it for blocking I/O, for shared mutable state, for ordering-sensitive work, for small data, and on request paths.

1. **Blocking I/O:** HTTP and JDBC calls park common-pool threads. Use a dedicated executor with `CompletableFuture`, or virtual threads, with a concurrency limit.
2. **Shared mutable state:** I ran `parallel().forEach(unsafe::add)` on an `ArrayList`, which kept 66,748 of 100,000 elements, and it can also throw. Use `collect`.
3. **`ThreadLocal` context:** MDC, security context and transaction are all thread-bound, and worker threads don't have them. Logs lose their correlation id, and JPA calls run outside the transaction.
4. **Small data or cheap work:** splitting and merging cost more than the work saved.
5. **Busy services:** each request competing for the same pool means no real gain under load, only more contention.
6. **Limited CPUs:** in a small container the pool may be tiny.

**Trade-offs and what can go wrong**
- Parallel streams can be a good fit in a batch job that owns the CPU. The problem is the request path in a shared service.

**Follow-ups to expect**
- *What would you use instead for parallel HTTP calls?* -> Virtual threads or a bounded executor with `CompletableFuture`, with timeouts on every call. See bank 05 Q13.

**60-second answer**
"I avoid it for anything that blocks, because all parallel streams share one ForkJoinPool, so an HTTP or JDBC call can stall unrelated work across the JVM. I also avoid it with shared mutable state: I've seen an ArrayList keep only two thirds of its items. It also loses thread-bound context like MDC, security and transactions, and it's slower on small data. It fits CPU-heavy batch work on large arrays. For I/O I use virtual threads or a bounded executor."

### Q13 [mid] How does distinct() work?
tags: streams, distinct, equals-hashcode, linkedhashset, stateful, parallel, reported-streams

**Start here: the concepts**
- `distinct` uses `equals` and `hashCode`, in effect a `LinkedHashSet` of what it has seen.
- It is **stateful**: it remembers every distinct element.

**The live scenario (functional requirement)**
*FR: "Remove repeated orders."* A class with no `equals`/`hashCode` passes through `distinct` unchanged, and duplicates reach the invoice run.

**What the interviewer is really checking**
The equality contract and the memory cost.

**How I answer it** (120-second answer, point by point)
1. For each element, it checks a hash-based set and passes the element through if it's new. So O(n) time and O(d) memory.
2. It keeps the first occurrence, and order is stable for ordered streams.
3. Records generate `equals`/`hashCode`, so `new Point(1)` twice gives one element. I checked that.
4. Mutable keys break it: changing a field used in `hashCode` during the pipeline makes equal objects look different.
5. Optimisation: on an already-`DISTINCT` source, such as a `Set`, it does nothing. On a `SORTED` source it only compares neighbours.
6. In parallel on an ordered stream, it must keep the first-seen element across threads, which is expensive. If order doesn't matter, `unordered().distinct()` is much cheaper.

**Trade-offs and what can go wrong**
- On unbounded streams, memory grows without limit. Use a windowed or bounded approach instead.

**Follow-ups to expect**
- *Distinct by a field?* -> Bank 95 Q19.

**60-second answer**
"distinct uses equals and hashCode, in effect a LinkedHashSet of what it's seen, keeping the first occurrence in order. It's O(n) time but stores every distinct value, so it's a stateful operation. Without equals and hashCode it removes nothing. In parallel with order preserved it's costly, so if order doesn't matter I'd use unordered first. On a sorted source it can just compare neighbours."

### Q14 [mid] How does sorted() work internally?
tags: streams, sorted, stateful, buffer, timsort, comparable, memory, reported-streams

**Start here: the concepts**
- `sorted` is a **stateful barrier**: it collects its entire input, sorts it, and only then emits.
- It uses the `Arrays.sort` / `List.sort` family, TimSort for objects, which is stable.

**The live scenario (functional requirement)**
*FR: "Show the 10 newest orders."* `stream.sorted(...).limit(10)` on 5 million rows loads all 5 million first, even though only 10 are needed.

**What the interviewer is really checking**
That `sorted` breaks the one-at-a-time flow. Most candidates don't know this.

**How I answer it** (120-second answer, point by point)
1. I traced `peek`, `sorted`, `peek`, `limit(1)` over 3, 1, 2. The output was `before 3, before 1, before 2, after 1`: all three were read first, and only one came out.
2. So `limit` after `sorted` does not reduce the sort's work.
3. Cost: O(n log n) time and O(n) memory. Without a comparator, elements must be `Comparable`, or it throws `ClassCastException` at runtime.
4. A null element throws NPE unless the comparator handles it.
5. Stable for ordered streams. Already-`SORTED` sources skip the sort when using natural order.
6. In parallel, it uses a parallel sort and merge.

**Trade-offs and what can go wrong**
- For top N on large data, use a bounded heap, or `ORDER BY ... LIMIT` in the database.

**Follow-ups to expect**
- *Does `sorted` on an infinite stream work?* -> It never finishes, because it waits for the end of the input.

**60-second answer**
"sorted is a stateful barrier. It buffers its whole input, sorts it, and only then emits anything, so it breaks the usual one-at-a-time flow. I traced this, and all elements are read before the first comes out. That means limit after sorted doesn't save work: it's still O(n log n) with all elements in memory. So for top N on large data I'd use a bounded heap or ORDER BY LIMIT in the database."

### Q15 [senior] How are exceptions handled in Streams?
tags: streams, exceptions, checked-exception, wrapper, flatmap, partial-failure, reported-streams

**Start here: the concepts**
- A lambda for `Function` or `Predicate` can't throw a **checked** exception, because those interfaces don't declare one.
- There is no built-in error channel: the first unchecked exception **aborts the entire pipeline**.

**The live scenario (functional requirement)**
*FR: "Parse 100,000 CSV rows. Bad rows go to a reject file, and good rows continue."* One bad row in `map(Integer::parseInt)` kills the whole import.

**What the interviewer is really checking**
That you can choose between fail-fast and per-element handling.

**How I answer it** (120-second answer, point by point)
1. **Unchecked, fail-fast:** it propagates to the terminal operation and stops everything. I confirmed `NumberFormatException` from `toList()`. This is right when any failure invalidates the batch.
2. **Checked:** catch inside the lambda and rethrow as unchecked, preserving the cause (`UncheckedIOException` for I/O). Put it in a small named method rather than a multi-line lambda.
3. **Per-element, keep going:** catch and use `flatMap` to drop the row and record it:

```java
Stream.of("1", "x", "3").flatMap(s -> {
    try { return Stream.of(Integer.parseInt(s)); }
    catch (NumberFormatException e) { bad.add(s); return Stream.empty(); }
}).toList();   // [1, 3], and bad holds "x"
```

4. A cleaner form returns a small `Result<T>` type (a sealed interface with `Ok` and `Err`), then `partitioningBy` splits good from bad without shared state. Note that `bad` above is sequential only.
5. If rows fail in large numbers or need retries, a plain loop is honest and easier to debug.

**Trade-offs and what can go wrong**
- In a parallel stream other threads may keep working after the failure, and only one exception is reported.
- Never swallow an exception silently. Always count, log or store rejects.

**Follow-ups to expect**
- *Debugging?* -> Stack traces show internals such as `ReferencePipeline`; extract named methods so your own names appear in them.

**60-second answer**
"Stream lambdas can't throw checked exceptions and have no error channel, so the first unchecked exception aborts the pipeline. For fail-fast, that's fine, and I wrap checked exceptions as unchecked, keeping the cause. To skip bad records and continue, I catch inside a flatMap, return an empty stream and record the reject. Cleanest is a Result type with partitioningBy, which avoids shared state. If the logic gets complicated, I switch to a loop."
