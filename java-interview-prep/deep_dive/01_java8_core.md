# Java 8 core: lambdas, streams, Optional, java.time, CompletableFuture

> **Runnable:** [`01_lambdas_functional_interfaces.java`](../examples/01_java8_core/01_lambdas_functional_interfaces.java) ·
> [`02_streams_collectors.java`](../examples/01_java8_core/02_streams_collectors.java) ·
> [`03_optional_datetime_default_methods.java`](../examples/01_java8_core/03_optional_datetime_default_methods.java) ·
> [`04_completable_future.java`](../examples/01_java8_core/04_completable_future.java)
> **Crib sheet:** [`topics/01-java-core-collections-java8.md`](../topics/01-java-core-collections-java8.md) · **Guide:** Q11–Q18

## What interviewers are actually probing

Java 8 is the baseline the requirement names first. The questions are rarely "name the features";
they are "show me you can *use* them without introducing bugs": a stream that mutates shared
state, an `Optional` used as a field, a `CompletableFuture` on the common pool that starves
everything, a lambda that swallows a checked exception. They also check that you know *why* the
features exist (default methods let `List.stream()` be added without breaking every implementer).

## Must-know points

- A **functional interface** has exactly one abstract method (default/static methods don't count). `@FunctionalInterface` is a compile-time guard, not a requirement.
- A lambda is **not** an anonymous inner class: `this` is the enclosing instance, it is compiled via `invokedynamic`, and it captures only **effectively final** locals.
- Streams are **lazy** (intermediate ops build a pipeline; one terminal op pulls), **single-use**, and should be **side-effect free**.
- `map` is 1→1; `flatMap` is 1→0..n and flattens one level.
- `Collectors.toMap` throws on duplicate keys unless you pass a merge function.
- `Optional` is a **return type** for "might be absent". Not a field, parameter, or collection element. Prefer `orElseGet` when the default is expensive.
- `java.time` types are immutable and thread-safe; `Instant` for machine time, `LocalDate/Time` for calendar, `ZonedDateTime` when a zone matters.
- `CompletableFuture` composes async steps: `thenApply` (map), `thenCompose` (flatMap), `thenCombine` (join two), `allOf`. **Pass your own executor.**

## Interview questions and full answers

### Q1. What is a functional interface, and which ones should you know?

An interface with a single abstract method (SAM). The `java.util.function` package gives the standard shapes so you rarely write your own:

| Interface | Shape | Typical use |
|---|---|---|
| `Function<T,R>` | `T → R` | `map`, transformations |
| `Predicate<T>` | `T → boolean` | `filter`, validation rules |
| `Consumer<T>` | `T → void` | `forEach`, side effects |
| `Supplier<T>` | `() → T` | lazy values, factories, `orElseGet` |
| `BiFunction`, `UnaryOperator`, `BinaryOperator` | two-arg / same-type | `reduce`, `merge` |
| `Runnable`, `Callable<V>`, `Comparator<T>` | older, also functional | executors, sorting |

Composition methods (`andThen`, `compose`, `and`, `or`, `negate`) are default methods on these interfaces,
which is exactly what default methods were introduced for.

### Q2. Lambda versus anonymous class: what are the real differences?

1. **`this`**: inside a lambda `this` is the enclosing object; inside an anonymous class it is the anonymous instance.
2. **Compilation**: an anonymous class is a separate `.class` file; a lambda is generated at runtime through `invokedynamic`/`LambdaMetafactory`, which is lighter and lets the JVM optimise.
3. **Shadowing**: a lambda body shares the enclosing scope (you can't redeclare a local with the same name); an anonymous class has its own scope.
4. **Capability**: an anonymous class can implement interfaces with multiple methods, hold state in fields, and extend a class. A lambda can only target a functional interface.

> Follow-up: *"Why must captured variables be effectively final?"* Because the lambda captures the **value**; allowing mutation would make the copy and the original diverge and, across threads, create data races without a memory model story.

### Q3. How do you deal with checked exceptions inside a lambda?

The standard functional interfaces don't declare checked exceptions, so you must either handle them inside the lambda or wrap them.
The usual approach is a small adaptor that converts to an unchecked exception:

```java
@FunctionalInterface interface ThrowingFunction<T, R> { R apply(T t) throws Exception; }

static <T, R> Function<T, R> unchecked(ThrowingFunction<T, R> f) {
    return t -> {
        try { return f.apply(t); }
        catch (RuntimeException e) { throw e; }          // don't double-wrap
        catch (Exception e) { throw new RuntimeException(e); }
    };
}
```

Mention the trade-off: you lose compile-time checking, so wrap into a *meaningful* domain exception, not a bare `RuntimeException`.
(Example 01, section 5.)

### Q4. Explain the Stream API pipeline and laziness.

A stream has a **source** (collection, array, generator), zero or more **intermediate operations** (`filter`, `map`, `sorted`, `distinct`, `limit`) and one **terminal operation** (`collect`, `forEach`, `reduce`, `count`, `findFirst`).
Nothing runs until the terminal op. Elements flow **one at a time** through the whole pipeline (vertical processing), so a short-circuiting terminal like `findFirst` can stop early.
Example 02 prints `filter`/`map` calls to show only two elements are touched.

Stateful ops (`sorted`, `distinct`) must buffer, which breaks the "one at a time" picture and is why they are costly on big streams.

### Q5. `map` versus `flatMap`?

`map` applies a function and keeps the nesting: `Stream<List<String>>` stays a stream of lists.
`flatMap` takes a function that returns a *stream* and concatenates them: `Stream<List<String>>.flatMap(List::stream)` gives `Stream<String>`.
Same idea on `Optional`: `flatMap` avoids `Optional<Optional<T>>`.

### Q6. What do `groupingBy`, `partitioningBy` and `toMap` give you, and what are their traps?

- `groupingBy(classifier, downstream)` → `Map<K, List<V>>` by default; a downstream collector (`counting`, `summingInt`, `mapping`, `averagingInt`) changes the value type. The result map is a `HashMap` unless you supply a factory (`TreeMap::new`).
- `partitioningBy(predicate)` → always a map with **both** `true` and `false` keys, even when one list is empty.
- `toMap(k, v)` throws `IllegalStateException` on duplicate keys; supply a merge function `(a, b) -> a`. It also throws NPE if a value is `null`.

### Q7. When should you not use a parallel stream?

Parallel streams run on the **common ForkJoinPool**, shared JVM-wide. Avoid them when:
- the work is **I/O or blocking** (starves everything else using the pool);
- the source splits badly (`LinkedList`, `Stream.iterate`);
- the operation has **side effects** or shared mutable state (example 02 section 9 loses elements in an `ArrayList`);
- the data is small, so splitting overhead dominates;
- you need **ordering** guarantees you didn't pay for.
Use it for CPU-bound, stateless, associative reductions over large arrays/ArrayLists, and **measure**.

### Q8. How should `Optional` be used? What is wrong with `Optional.get()`?

Use it as a **return type** to say "no result is a normal outcome". Chain with `map`, `filter`, `flatMap`, then terminate with `orElse`, `orElseGet`, `orElseThrow` or `ifPresent`.
Don't use it for fields (not `Serializable`, extra allocation), method parameters (callers pass `null` anyway), or collections (return an empty collection).
`get()` without a check throws `NoSuchElementException` and recreates the NPE problem; use `orElseThrow()` (Java 10+) so the intent is explicit.
`orElse(x)` evaluates `x` **eagerly**; `orElseGet(supplier)` only when empty.

### Q9. What's wrong with `java.util.Date` and `SimpleDateFormat`, and what replaced them?

`Date` is mutable, represents an instant but is named like a date, has month 0-based and a 1900-offset year; `SimpleDateFormat` is **not thread-safe** (a classic production bug when stored in a static field). `java.time` fixes it:

| Need | Type |
|---|---|
| A moment on the timeline (store/transport) | `Instant`, `OffsetDateTime` (UTC) |
| Calendar date, no zone | `LocalDate`, `LocalDateTime` |
| Zone-aware wall clock (DST rules) | `ZonedDateTime` |
| Amount of time | `Duration` (seconds/nanos), `Period` (years/months/days) |
| Format/parse | `DateTimeFormatter` (immutable, thread-safe) |

Rule: store UTC `Instant`s, convert to a `ZoneId` only at the display edge. `LocalDateTime` has no zone, so never use it to represent "when something happened".

### Q10. What are default and static methods in interfaces, and what is the diamond problem?

Default methods provide an implementation in the interface so APIs can evolve without breaking implementers (`Collection.stream()`, `Map.getOrDefault`, `Comparator.reversed`).
If a class inherits the same default from two interfaces the compiler **forces** you to override and choose, e.g. `Walker.super.move()`.
Resolution order: **class wins** over interface; **more specific interface** wins; otherwise you resolve explicitly.
Interfaces still can't hold instance state.

### Q11. Explain `CompletableFuture` and when `thenApply` differs from `thenCompose`.

`Future` only offers a blocking `get()`. `CompletableFuture` is a promise you can **compose without blocking**.
- `thenApply(fn)`: synchronous transform of the result (`map`).
- `thenCompose(fn)`: `fn` returns another `CompletableFuture`; flattens it (`flatMap`).
- `thenCombine(other, bi)`: waits for two independent futures.
- `allOf(...)`/`anyOf(...)`: wait for many / first.
- `exceptionally`, `handle`, `whenComplete`: error recovery / observation.
- `orTimeout`, `completeOnTimeout` (Java 9+): time bounds.

### Q12. How do you call three services in parallel and combine the results safely?

```java
ExecutorService io = Executors.newFixedThreadPool(16);   // YOUR pool, sized for I/O
CompletableFuture<Price>  p = supplyAsync(() -> pricing.get(id), io).orTimeout(800, MILLISECONDS);
CompletableFuture<Stock>  s = supplyAsync(() -> stock.get(id),   io).orTimeout(800, MILLISECONDS);
CompletableFuture<Ship>   h = supplyAsync(() -> ship.get(id),    io).exceptionally(e -> Ship.UNKNOWN);
Product result = p.thenCombine(s, Partial::new).thenCombine(h, Partial::with).join();
```

Points to say out loud: custom executor (not the common pool), a timeout on every remote call, a deliberate fallback for non-critical parts,
and that total latency is ~ the **slowest** call, not the sum (example 04 section 2: ~300 ms vs ~750 ms).

### Q13. `get()` versus `join()`, and why does `exceptionally` receive a `CompletionException`?

`get()` throws checked `ExecutionException`/`InterruptedException`; `join()` throws unchecked `CompletionException`. In dependent stages an upstream failure is wrapped in `CompletionException`, so `ex.getCause()` holds the original. Unwrap before deciding on the type of failure.

### Q14. Which thread runs my `thenApply` callback?

Without `Async`, it runs on whichever thread completes the stage (or the caller if already complete). `thenApplyAsync(fn)` uses the common pool; `thenApplyAsync(fn, executor)` uses yours.
This matters for thread-locals (MDC, security context, transactions), which **do not propagate** to the other thread.

## A worked example

Run [`02_streams_collectors.java`](../examples/01_java8_core/02_streams_collectors.java) and look at:

1. Section 1: the `filter`/`map` print order proves laziness and short-circuiting.
2. Section 5: the exact `IllegalStateException` message from `toMap` duplicates.
3. Section 9: the parallel `ArrayList::add` loses elements; the `collect()` version never does.

Then run [`04_completable_future.java`](../examples/01_java8_core/04_completable_future.java) and compare `exceptionally` (receives `CompletionException`) with `get()`/`join()` wrapping.

## Hands-on drills

1. Given `List<Order>`, return the top 3 customers by total spend as `Map<String, BigDecimal>` preserving rank order.
2. Rewrite a nested-loop "find duplicates" method as one stream pipeline; then explain its time/space cost.
3. Convert a method that returns `null` to `Optional`, and a caller that did `if (x != null)` chains to `map/flatMap`.
4. Make a retrying `CompletableFuture` helper with exponential backoff (no blocking sleep on the common pool).
5. Show a bug caused by a static `SimpleDateFormat` under 2 threads, then fix with `DateTimeFormatter`.

## The 60-second spoken answer

"Java 8 gave us functional-style code: lambdas over functional interfaces, method references, and the Stream API for declarative
data processing. Streams are lazy and single-use, so I keep them side-effect free and use `collect` rather than mutating shared lists;
I only use parallel streams for CPU-bound work on big, cheaply-splittable data because they share the common pool. I use `Optional`
as a return type, `java.time` instead of `Date`, and `CompletableFuture` with my own executor and timeouts to fan out remote calls,
so latency is the slowest call rather than the sum. The traps I watch for are `toMap` duplicates, checked exceptions in lambdas,
and losing thread-locals like the correlation id when work hops threads."
