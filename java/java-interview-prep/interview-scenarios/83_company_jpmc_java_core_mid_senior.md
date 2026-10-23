---
id: company-jpmc-java-core
title: JPMorgan Chase pack (1/5): core Java and collections, mid to senior
stack: java
skill: java-core
---
Part of the **JPMorgan Chase Java mid/senior pack** (hub: `../company-chase-travel/README.md`, section
"JPMorgan Chase interview: what to target"). Topics are the ones candidates most often report from JPMC Java
rounds: `final`, `HashMap`, `equals/hashCode`, strings, exceptions, streams, generics, collections, design.

Every answer has two spoken versions:
- **How I answer it** = the **120-second** version, point by point, for mid and senior rounds.
- **60-second answer** = the short version for a rapid-fire round or a first answer before follow-ups.

Language is kept simple on purpose: say the idea, give one real example, name the trap.

Levels: **mid** (3-6 yrs) · **senior** (6-10) · **architect** (10+, "expert").

### Q1 [mid] How does HashMap work internally, and what happens on a collision?
tags: hashmap, hashcode, equals, collision, treeify, resize, load-factor, jpmc

**Start here: the concepts**
- A `HashMap` is an **array of buckets**. The key's `hashCode()` decides which bucket; `equals()` finds the exact key inside the bucket.
- A **collision** means two keys land in the same bucket. They are stored together, first as a linked list, then as a small red-black tree when the bucket gets crowded.
- **Resize** means the array doubles when it gets too full (default: 75% full), and entries are spread again.

**The live scenario (functional requirement)**
*FR: "Cache the latest FX rate per currency pair so the pricing API does not hit the database on every call."* The team used `Map<CurrencyPair, Rate>`. One day lookups started returning `null` for pairs that were clearly in the map. The cause: `CurrencyPair` was mutable, and someone changed a field after it was used as a key, so its hash pointed to a different bucket.

**What the interviewer is really checking**
Whether you understand the mechanics well enough to explain real bugs (mutable keys, bad `hashCode`) and performance (resize cost, worst case), not just recite "array plus linked list".

**How I answer it** (120-second answer, point by point)
1. **Put:** Java takes `key.hashCode()`, mixes the high bits into the low bits (`h ^ (h >>> 16)`), and uses `hash & (n - 1)` to pick a bucket. The table size `n` is always a power of two, so this is a fast modulo.
2. **Empty bucket:** store a new node. **Non-empty bucket:** walk the nodes; if `equals()` matches, replace the value; otherwise append.
3. **Collisions:** when one bucket has more than **8** nodes *and* the table has at least **64** buckets, that bucket becomes a **red-black tree**. Worst-case lookup goes from O(n) to O(log n). Below 6 nodes it turns back into a list.
4. **Resize:** when size > capacity × load factor (16 × 0.75 = 12 by default), the table doubles. Each entry either stays at its index or moves by exactly `oldCapacity`, so Java 8 splits buckets without recomputing hashes.
5. **Get:** same hash, same bucket, then `equals()` to find the key. That is why **both** methods matter.
6. **Practical points I mention:**
   - Keys must be **immutable** (String, records, enums). A mutated key is "lost" in the wrong bucket. That was the FX bug.
   - If I know the size, I pre-size: `new HashMap<>(expected * 4 / 3 + 1)` or `HashMap.newHashMap(expected)` (Java 19+), to avoid repeated resizes.
   - `HashMap` is **not thread-safe**. For shared caches I use `ConcurrentHashMap`.
   - One `null` key is allowed (it goes to bucket 0); `ConcurrentHashMap` allows no null keys or values.

**Trade-offs and what can go wrong**
- A poor `hashCode()` (for example returning a constant) puts everything in one bucket: lookups become slow even with trees.
- Iteration order is not guaranteed. If the order matters, use `LinkedHashMap` (insertion order) or `TreeMap` (sorted).
- Concurrent writes to a plain `HashMap` can lose entries or corrupt the structure. Before Java 8, a resize race could even cause an infinite loop.

**Follow-ups to expect**
- *Why is the threshold 8?* -> With a good hash, the chance of 8 collisions in one bucket is tiny (Poisson distribution), so trees are only a defence against bad hashes or attacks.
- *Why must the capacity be a power of two?* -> So `hash & (n - 1)` works as a fast modulo, and resizing splits each bucket into exactly two.
- *Is `HashMap` ordered?* -> No. `LinkedHashMap` keeps insertion order and can be an LRU cache with `accessOrder = true` and `removeEldestEntry`.

**60-second answer**
"A HashMap is an array of buckets. On `put`, Java takes the key's hashCode, spreads the high bits, and picks a bucket with `hash & (n-1)`. If the bucket is empty it stores the node. If not, it walks the bucket and uses `equals` to replace or append. When a bucket goes past 8 nodes and the table has at least 64 slots, it becomes a red-black tree, so the worst case is O(log n). When the map is 75% full it doubles and re-spreads the entries. In practice I keep keys immutable, because a mutated key lands in the wrong bucket and disappears. I also pre-size big maps, and I use ConcurrentHashMap when threads share it."

### Q2 [mid] What is the equals and hashCode contract, and what breaks if you get it wrong?
tags: equals, hashcode, contract, hashset, records, lombok, jpa-entity, jpmc

**Start here: the concepts**
- `equals()` answers "are these two objects the same value?" `hashCode()` gives a number used to pick a bucket.
- **The rule:** if `a.equals(b)` is true, then `a.hashCode() == b.hashCode()` must be true. The reverse is not required: different objects may share a hash.

**The live scenario (functional requirement)**
*FR: "Do not send the same trade confirmation twice."* The service kept a `Set<TradeKey>` of confirmations already sent. `TradeKey` overrode `equals` but not `hashCode`. Duplicates went out because two equal keys had different default hash codes and landed in different buckets, so the set never compared them.

**What the interviewer is really checking**
That you know the contract, the concrete failure, and the practical way to get it right (records, IDE generation, and care with JPA entities).

**How I answer it** (120-second answer, point by point)
1. **The contract for `equals`:** reflexive, symmetric, transitive, consistent, and `x.equals(null)` is false.
2. **The link:** equal objects **must** have equal hash codes. Hash-based collections look in a bucket first and only then call `equals`.
3. **What breaks:**
   - `equals` without `hashCode`: `HashSet` holds "duplicates" and `HashMap.get` returns `null` for an equal key. That was the trade-confirmation bug.
   - `hashCode` built from **mutable fields**: the object gets lost after a field changes.
   - Using `instanceof` in a class hierarchy can break symmetry (`a.equals(b)` but not `b.equals(a)`).
4. **How I do it today:**
   - For value objects I use a **record**. Java generates correct `equals`, `hashCode` and `toString` from all components.
   - Otherwise, `Objects.equals(...)` and `Objects.hash(...)` over the same fields, generated by the IDE.
5. **JPA entities are special:** the database id is `null` before save, so an id-based `hashCode` changes after `persist`. I use a business key (for example an account number), or compare by id and return a constant `hashCode` per class. I never use Lombok's `@Data` on entities.

**Trade-offs and what can go wrong**
- `Objects.hash(...)` allocates an array on each call. That is fine for most code, but hand-write the method in a very hot path.
- Including lazy-loaded JPA relations in `equals` or `toString` triggers queries or infinite recursion.

**Follow-ups to expect**
- *Can two unequal objects have the same hash code?* -> Yes, that is a collision. It is legal but hurts performance if it is common.
- *Does a record do deep equality?* -> It calls `equals` on each component. Arrays inside a record are compared by reference, which is a common trap.
- *`==` vs `equals`?* -> `==` compares references (or primitive values); `equals` compares meaning.

**60-second answer**
"The contract is: if two objects are equal, their hash codes must be equal. Hash collections first use the hash to pick a bucket and only then call equals. If you override equals but not hashCode, two equal keys go to different buckets, so a HashSet keeps duplicates and HashMap.get returns null. I actually saw that cause duplicate trade confirmations. Today I use records for value objects, because they generate both methods correctly. Otherwise I build both from the same immutable fields. For JPA entities I avoid an id-based hash, because the id changes when the entity is saved."

### Q3 [mid] Why is String immutable, and when do you use StringBuilder?
tags: string, immutability, string-pool, stringbuilder, security, performance, jpmc

**Start here: the concepts**
- **Immutable** means a `String` can never change after it is created. "Changing" it creates a new String.
- The **string pool** is a shared area where Java keeps one copy of each literal, such as `"USD"`.
- `StringBuilder` is a mutable buffer for building text step by step.

**The live scenario (functional requirement)**
*FR: "Generate a nightly CSV of 2 million transactions."* The first version used `line = line + field` in a loop. The job took 40 minutes and created huge amounts of garbage. With one `StringBuilder` per line written straight to a `BufferedWriter`, it took under 2 minutes.

**What the interviewer is really checking**
The *reasons* for immutability (safety, caching, pooling) and practical judgement about building strings.

**How I answer it** (120-second answer, point by point)
1. **Why immutable:**
   - **Security:** strings carry class names, file paths, URLs and usernames. If they could change after a security check, the check would be useless.
   - **Thread safety:** an immutable object can be shared between threads with no locks.
   - **Hash caching:** the hash is computed once and cached, which makes String a fast `HashMap` key.
   - **Pooling:** because nobody can change `"USD"`, all code can safely share one copy.
2. **The cost:** every change makes a new object. In a loop, `s = s + x` copies the whole string every time, which is O(n²).
3. **When I use `StringBuilder`:** building text in a loop, or a big message piece by piece. It is not synchronized, so it is fast. `StringBuffer` is the old synchronized version and is rarely needed.
4. **When I do not bother:** a single expression like `"Hello " + name + "!"`. Since Java 9 the compiler uses `invokedynamic` string concatenation, which is already efficient.
5. **Modern helpers:** `String.join`, `Collectors.joining`, text blocks (Java 15) for multi-line SQL or JSON, and `"%s".formatted(x)` (Java 15).
6. **Compact strings (Java 9):** Latin-1 strings use one byte per character instead of two, which roughly halves string memory in most services.

**Trade-offs and what can go wrong**
- `new String("x")` creates an extra object; just use the literal.
- `intern()` on random data can bloat the string table; use it rarely.
- Passwords are better kept in a `char[]` you can wipe; a String stays in memory until garbage collection.

**Follow-ups to expect**
- *Where is the string pool?* -> In the heap since Java 7 (it was in PermGen before).
- *Is `s1 == s2` true for two equal literals?* -> Yes, both point to the pooled instance. For a String built at runtime it is false, so always use `equals`.
- *Why is the String class `final`?* -> So nobody can subclass it and break immutability.

**60-second answer**
"String is immutable for security, thread safety and performance. A string that holds a path or a username can't be changed after it's validated, it can be shared between threads with no locking, and its hash is cached, which makes it a fast map key. Immutability also allows the string pool, where one copy of each literal is shared. The cost is that every change creates a new object, so concatenating in a loop is O(n²). In loops I use StringBuilder. In a single expression I just use plus, because the compiler already optimises it. I once took a CSV export from 40 minutes to 2 by fixing exactly that."

### Q4 [mid] Explain final, finally and finalize, and how you build an immutable class.
tags: final, finally, finalize, immutable, records, defensive-copy, jpmc

**Start here: the concepts**
- `final` is a keyword: a final **variable** can be assigned once, a final **method** cannot be overridden, a final **class** cannot be extended.
- `finally` is a block that always runs after `try`/`catch`, used for cleanup.
- `finalize()` was a method the garbage collector *might* call before removing an object. It is **deprecated for removal since Java 18**. Do not use it.

**The live scenario (functional requirement)**
*FR: "A `Payment` object is created by the API thread, validated, then read by the audit thread and the Kafka publisher."* A bug let the publisher change the amount after validation. Making `Payment` properly immutable removed the whole class of bug.

**What the interviewer is really checking**
That you don't mix up the three words, and that you know `final` on a reference does **not** make the object immutable.

**How I answer it** (120-second answer, point by point)
1. **`final` variable:** the reference cannot change, but the object can. A `final List<String> list` can still have `list.add(...)` called on it.
2. **`final` field:** the Java memory model guarantees other threads see the correct value once the constructor finishes. This is "safe publication", and it is why immutable objects are thread-safe.
3. **`final` method or class:** stops overriding or subclassing. `String` and records are final.
4. **`finally`:** runs whether or not an exception happens. Today I prefer **try-with-resources** for closing things. I never `return` from `finally`, because that swallows the exception.
5. **`finalize`:** unpredictable, slow and deprecated. The replacements are try-with-resources, or `Cleaner` as a safety net.
6. **Immutable class recipe:** a final class (or a record), `private final` fields, no setters, validation in the constructor, and **defensive copies** of mutable inputs, for example `List.copyOf(items)`. "Changes" return a new object, such as `withStatus(...)`.

**Trade-offs and what can go wrong**
- A record is only *shallowly* immutable: a `List` component must be copied in the compact constructor.
- Too many copies in hot loops create allocation pressure. It is usually negligible next to I/O.

**Follow-ups to expect**
- *Does `finally` always run?* -> Not if the JVM exits (`System.exit`), the process is killed, or the thread never leaves the `try`.
- *What is "effectively final"?* -> A local variable that is never reassigned. Lambdas and inner classes may capture it without the keyword.
- *Can a constructor be final?* -> No; constructors are not inherited, so it means nothing.

**60-second answer**
"`final` means assign once for a variable, no override for a method, and no subclass for a class. On a reference it does not make the object immutable: a final list can still be modified. `finally` is the cleanup block that runs after try/catch; today I prefer try-with-resources, and I never return from finally because it hides exceptions. `finalize` was a GC hook; it's unreliable and deprecated for removal since Java 18. For a truly immutable object I use a record or a final class with private final fields, no setters, constructor validation and defensive copies such as `List.copyOf`. Final fields also give safe publication between threads."

### Q5 [mid] Checked vs unchecked exceptions: how do you design exception handling in a service?
tags: exceptions, checked, unchecked, try-with-resources, error-handling, controlleradvice, jpmc

**Start here: the concepts**
- **Checked** exceptions (`IOException`, `SQLException`) must be caught or declared. They are for problems the caller can reasonably recover from.
- **Unchecked** exceptions (`RuntimeException` subclasses such as `IllegalArgumentException`) are not forced on the caller. They are for programming errors or problems the caller cannot fix.
- **Errors** (`OutOfMemoryError`) are JVM-level problems; do not catch them in normal code.

**The live scenario (functional requirement)**
*FR: "A transfer API must return a clear 422 when the balance is too low, a 503 when the core-banking system is down, and never leak a stack trace."* The legacy code caught `Exception` everywhere, logged it three times, and returned 500 for everything.

**What the interviewer is really checking**
That you have a *policy*: where exceptions are thrown, translated, logged once, and turned into a response.

**How I answer it** (120-second answer, point by point)
1. **Domain exceptions are unchecked:** for example `InsufficientFundsException extends BusinessException extends RuntimeException`, carrying an error code. Spring rolls back `@Transactional` methods on unchecked exceptions by default, which is what I want.
2. **Wrap checked exceptions at the boundary:** an adapter that calls a file or socket catches `IOException` and throws `DownstreamUnavailableException(cause)`. **Always keep the cause** so the stack trace is not lost.
3. **Translate in one place:** a `@RestControllerAdvice` maps each exception type to a status and an RFC 9457 `ProblemDetail`: business rule -> 422, not found -> 404, downstream down -> 503, anything unknown -> 500 with a generic message.
4. **Log once,** at the place that handles it, with a correlation id. Not at every layer.
5. **Resources:** try-with-resources for anything `AutoCloseable`. Suppressed exceptions are kept on the main one.
6. **Never:** an empty `catch`, catching `Throwable`, using exceptions for normal control flow, or returning from `finally`.

**Trade-offs and what can go wrong**
- Too many custom exception types become noise; group them by how the caller must react.
- Checked exceptions do not work well with lambdas and streams, which is one reason modern code prefers unchecked ones.
- Stack traces are expensive. For very frequent, expected business failures, a result type or an exception without a stack trace is an option.

**Follow-ups to expect**
- *Does `@Transactional` roll back on a checked exception?* -> Not by default; add `rollbackFor = Exception.class` if you need it.
- *Difference between `throw` and `throws`?* -> `throw` raises an exception; `throws` declares it on the method signature.
- *Multi-catch?* -> `catch (IOException | TimeoutException e)` since Java 7.

**60-second answer**
"Checked exceptions are for recoverable conditions the compiler forces you to handle; unchecked ones are for bugs or problems the caller can't fix. In a service I make domain exceptions unchecked, with an error code. I wrap checked exceptions from I/O at the adapter boundary into my own type, keeping the cause. Then a single `@RestControllerAdvice` turns each type into the right status and a Problem Details body: 422 for business rules, 503 for a downstream outage, a generic 500 for anything unknown, so no stack trace leaks. I log once where the exception is handled, with a correlation id, and use try-with-resources for cleanup."

### Q6 [senior] Explain how streams work, and when would you NOT use a parallel stream?
tags: streams, lazy-evaluation, map, flatmap, collectors, groupingby, parallel-stream, forkjoin, jpmc

**Start here: the concepts**
- A **stream** is a pipeline: a source, then **intermediate** operations (`filter`, `map`) that are lazy, then one **terminal** operation (`collect`, `sum`) that runs everything.
- **Lazy** means nothing happens until the terminal operation, and elements flow through one at a time.
- A **parallel stream** splits the work across the shared **ForkJoinPool common pool**.

**The live scenario (functional requirement)**
*FR: "Show total exposure per counterparty from 500,000 positions."* `positions.stream().collect(groupingBy(Position::counterparty, summingDouble(Position::exposure)))` worked well. Then someone added `.parallel()` to a stream that called a REST service per element. All request threads shared the common pool, which became blocked on I/O, and the whole service slowed down.

**What the interviewer is really checking**
That you know laziness, the important collectors, `map` vs `flatMap`, and the real risks of parallel streams in a server.

**How I answer it** (120-second answer, point by point)
1. **Laziness:** `filter` and `map` only describe work. The terminal operation pulls elements through. Short-circuit operations (`findFirst`, `anyMatch`, `limit`) stop early.
2. **`map` vs `flatMap`:** `map` turns one element into one element. `flatMap` turns one element into a stream and flattens it; for example, orders to their line items.
3. **Collectors I use daily:** `groupingBy` (with a downstream such as `counting()`, `summingDouble`, `mapping`), `partitioningBy`, `toMap` (watch for duplicate keys: pass a merge function), and `joining`. Since Java 16, `stream.toList()` returns an unmodifiable list.
4. **Stateless vs stateful:** `filter` and `map` are stateless. `sorted` and `distinct` are stateful: they must see everything first, which costs memory.
5. **When I would NOT use `parallel()`:**
   - In a **web server**: requests already run in parallel, and all parallel streams share one common pool sized to the CPU count.
   - With **blocking I/O** inside: it starves the pool.
   - With **small data** or cheap per-element work: splitting costs more than it saves.
   - With **order-dependent** or **shared mutable state**: wrong results.
   - When the source splits badly, such as `LinkedList` or `Stream.iterate`.
6. **When it helps:** large, CPU-heavy, independent work on an `ArrayList` or array, usually in a batch job, and **measured** with JMH or a real benchmark.

**Trade-offs and what can go wrong**
- Streams are not always faster than loops; in very hot code a plain loop can win.
- Side effects in `forEach` or `map` (adding to an outside list) are bugs waiting for `parallel()`.
- Debugging long chains is harder; split them into named methods.

**Follow-ups to expect**
- *Can a stream be reused?* -> No. After the terminal operation it throws `IllegalStateException`.
- *`Collectors.toMap` throws on duplicate keys?* -> Yes, `IllegalStateException`. Pass a merge function such as `(a, b) -> a`.
- *What are stream gatherers?* -> Java 24 added `Stream.gather(...)` for custom intermediate operations such as sliding windows (`Gatherers.windowSliding`).

**60-second answer**
"A stream is a lazy pipeline: intermediate operations like filter and map just describe the work, and the terminal operation pulls elements through one at a time, stopping early for things like findFirst. `map` is one-to-one and `flatMap` flattens a stream per element. I use groupingBy with downstream collectors a lot, and toMap with a merge function. I'm careful with parallel streams. In a web service they all share the ForkJoin common pool, so a parallel stream doing blocking I/O starved our whole service. I use parallel only for big, CPU-bound, independent work in batch jobs, and only after measuring."

### Q7 [senior] Explain generics, type erasure and wildcards (PECS) with a real example.
tags: generics, type-erasure, wildcards, pecs, bounded-types, jpmc

**Start here: the concepts**
- **Generics** let a class or method work with a type parameter, `List<Trade>`, so the compiler checks types for you.
- **Type erasure:** the type parameters exist only at compile time. At runtime a `List<Trade>` is just a `List`.
- **Wildcards:** `? extends T` means "some subtype of T", `? super T` means "some supertype of T".

**The live scenario (functional requirement)**
*FR: "One utility should copy validated items from any list of trades (equity, FX, bond) into an audit sink."* The first version took a `List<Trade>`, and passing a `List<EquityTrade>` did not compile. With wildcards it accepted every kind of list.

**What the interviewer is really checking**
Whether you can write flexible, type-safe APIs and know the limits erasure imposes.

**How I answer it** (120-second answer, point by point)
1. **Why generics:** compile-time type safety and no casts. A `List<Trade>` cannot accidentally hold a `String`.
2. **Generics are invariant:** a `List<EquityTrade>` is **not** a `List<Trade>`. If it were, you could add an `FxTrade` to a list of equities.
3. **PECS, "Producer Extends, Consumer Super":**
   - When you only **read** from it, use `List<? extends Trade>`.
   - When you only **write** into it, use `List<? super Trade>`.
   - The JDK does this: `Collections.copy(List<? super T> dest, List<? extends T> src)`.
4. **Bounded type parameters:** `<T extends Comparable<? super T>> T max(List<T> list)` means "T can be compared with itself or a parent".
5. **Type erasure consequences:**
   - No `new T()`, no `instanceof List<String>`, no `T[]` creation.
   - The workaround is to pass a `Class<T>` or a type token (Jackson's `TypeReference<List<Trade>>`).
   - Overloads that differ only by type parameter will not compile, because they erase to the same signature.
6. **Why erasure exists:** backward compatibility with pre-Java-5 code.

**Trade-offs and what can go wrong**
- Raw types (`List` without `<>`) turn off checking; fix every "unchecked" warning, don't suppress it blindly.
- Heavy wildcard signatures hurt readability. Use them in library or utility APIs, not everywhere.

**Follow-ups to expect**
- *What is heap pollution?* -> A variable of a generic type pointing to an object of the wrong type, usually through raw types or generic varargs (`@SafeVarargs`).
- *`List<?>` vs `List<Object>`?* -> `List<?>` is a list of some unknown type (read-only, effectively); `List<Object>` really holds objects.
- *Will Project Valhalla change generics?* -> It aims at value classes and, later, generics over primitives. It is not in the JDK as of Java 27.

**60-second answer**
"Generics give compile-time type safety without casts. They're invariant: a List of EquityTrade is not a List of Trade, otherwise you could insert an FX trade into it. To make APIs flexible I use PECS: `? extends` when I only read from a collection, `? super` when I only write into it, like Collections.copy does. Generics are erased at runtime, so I can't do `new T()` or `instanceof List<String>`; I pass a Class or a type token instead, like Jackson's TypeReference. Erasure exists for backward compatibility. I keep wildcards in utility APIs and keep business code simple."

### Q8 [mid] How do you choose between ArrayList, LinkedList, ArrayDeque, HashSet and TreeMap? What is fail-fast?
tags: collections, arraylist, linkedlist, arraydeque, treemap, fail-fast, concurrentmodificationexception, jpmc

**Start here: the concepts**
- `ArrayList`: a resizable array. Fast reads by index, appends at the end are cheap.
- `LinkedList`: a chain of nodes. Each node has extra memory and poor cache locality.
- `ArrayDeque`: a fast queue or stack.
- `HashSet`/`HashMap`: unordered, O(1) average lookup. `TreeMap`/`TreeSet`: sorted, O(log n).
- **Fail-fast iterator:** throws `ConcurrentModificationException` if the collection is changed while you iterate over it (except through the iterator itself).

**The live scenario (functional requirement)**
*FR: "Remove cancelled orders from today's list before pricing."* A `for (Order o : orders) if (o.cancelled()) orders.remove(o);` threw `ConcurrentModificationException` in production, but only on days with cancellations.

**What the interviewer is really checking**
Practical choice by access pattern, Big-O plus real-world memory effects, and the classic modification bug.

**How I answer it** (120-second answer, point by point)
1. **Default list: `ArrayList`.** O(1) index access, cheap appends, and good CPU-cache use. Pre-size it when the size is known.
2. **`LinkedList` almost never.** In theory it inserts in the middle in O(1), but you must walk to the position first, and each node costs about 24+ bytes. `ArrayList` wins in nearly every benchmark.
3. **Queue or stack: `ArrayDeque`.** It is faster than `Stack` (old and synchronized) and than `LinkedList`.
4. **Uniqueness and fast lookup: `HashSet`/`HashMap`.** Keep insertion order with `LinkedHashSet`/`LinkedHashMap`.
5. **Sorted data or range queries: `TreeMap`.** For example, "the price level just below 101.5" with `floorKey`, or `headMap`/`tailMap` for ranges.
6. **Priorities: `PriorityQueue`** (a heap), for example the top-K largest trades.
7. **Fail-fast:** collections keep a `modCount`; the iterator checks it and throws on a change. The fixes are `orders.removeIf(Order::cancelled)` (Java 8), `iterator.remove()`, or building a new filtered list with a stream.
8. **Concurrency:** for shared access use `ConcurrentHashMap`, `CopyOnWriteArrayList` (many reads, rare writes), or the `BlockingQueue` types. Their iterators are *weakly consistent*: they never throw CME.

**Trade-offs and what can go wrong**
- `Arrays.asList` is fixed-size: `add` throws `UnsupportedOperationException`. `List.of` is fully immutable and rejects nulls.
- `CopyOnWriteArrayList` copies the whole array on each write; it is terrible for write-heavy data.
- Fail-fast detection is best effort; it is not a thread-safety guarantee.

**Follow-ups to expect**
- *How does `ArrayList` grow?* -> By about 1.5×, copying into a new array.
- *What is a `SequencedCollection`?* -> Java 21 added `getFirst()`, `getLast()` and `reversed()` to lists, deques and linked sets/maps.
- *`HashMap` vs `Hashtable`?* -> `Hashtable` is legacy and fully synchronized; use `ConcurrentHashMap`.

**60-second answer**
"I choose by access pattern. ArrayList is my default list because index access is O(1) and it's cache-friendly; LinkedList almost never wins in practice. ArrayDeque for queues and stacks. HashMap and HashSet for fast lookup, the Linked versions when insertion order matters, and TreeMap when I need sorting or range queries like floorKey. PriorityQueue for top-K. The classic bug is removing from a list inside a for-each loop: the iterator is fail-fast and throws ConcurrentModificationException. I use removeIf instead. For shared data I use the concurrent collections, whose iterators never throw."

### Q9 [mid] Comparable vs Comparator: how do you sort trades by several fields, null-safely?
tags: comparable, comparator, sorting, thencomparing, nullsfirst, jpmc, coding-round

**Start here: the concepts**
- `Comparable` gives a class **one natural order** (`compareTo`), for example a `Money` amount.
- `Comparator` is a **separate** ordering you can create for any use, for example "by desk, then newest first".

**The live scenario (functional requirement)**
*FR: "The blotter screen shows trades by desk, then by largest notional, then newest first; some trades have no desk yet and must appear last."* The old comparator was hand-written with nested `if`s and broke when `desk` was null.

**What the interviewer is really checking**
Fluency with the Java 8 `Comparator` API, and awareness of the contract (consistency with `equals`, overflow).

**How I answer it** (120-second answer, point by point)
1. **`Comparable`** for the natural order of a value type: `record Money(BigDecimal amount) implements Comparable<Money>`.
2. **`Comparator`** for screen-specific or business orderings. Build it, don't hand-write it:

```java
Comparator.comparing(Trade::desk, Comparator.nullsLast(Comparator.naturalOrder()))
          .thenComparing(Trade::notional, Comparator.reverseOrder())
          .thenComparing(Trade::tradeTime, Comparator.reverseOrder());
```

3. **Use the primitive versions** (`comparingInt`, `comparingLong`, `comparingDouble`) to avoid boxing.
4. **Never write `return a - b;`** in `compareTo`: it overflows for large or negative ints. Use `Integer.compare(a, b)`.
5. **Consistency with `equals`:** a `TreeSet` uses `compareTo`, not `equals`. If two different trades compare as 0, the set silently keeps only one. Add a tiebreaker such as the trade id.
6. **Stability:** `List.sort` and `Collections.sort` are stable (TimSort), so equal elements keep their order.

**Trade-offs and what can go wrong**
- Sorting very large datasets in memory belongs in the database (`ORDER BY` with an index) or in paged queries.
- `BigDecimal.equals` treats `2.0` and `2.00` as different, but `compareTo` says they are equal. Use `compareTo` for amounts.

**Follow-ups to expect**
- *Sort a map by value?* -> `map.entrySet().stream().sorted(Map.Entry.comparingByValue(Comparator.reverseOrder()))`.
- *Which algorithm does Java use?* -> TimSort for objects, dual-pivot quicksort for primitives.

**60-second answer**
"Comparable is a class's single natural order, like Money by amount. Comparator is any other ordering, built from outside the class. For the blotter I chain Comparator.comparing by desk with nullsLast, then thenComparing by notional reversed, then by trade time reversed: readable and null-safe. I use comparingInt or comparingLong to avoid boxing, and I never write `a - b` because it overflows. I always add a final tiebreaker like the trade id, because a TreeSet treats compare-equal elements as duplicates and silently drops one."

### Q10 [senior] Which design patterns and SOLID principles do you actually use in a Spring service?
tags: design-patterns, solid, strategy, builder, factory, singleton, template-method, decorator, jpmc

**Start here: the concepts**
- **SOLID:** Single responsibility, Open/closed, Liskov substitution, Interface segregation, Dependency inversion.
- **Patterns** are named, reusable solutions: Strategy, Factory, Builder, Singleton, Template Method, Decorator, Adapter, Observer and others.

**The live scenario (functional requirement)**
*FR: "Payments must support card, ACH and wire today, and RTP next quarter, each with its own validation and fee rules, without touching the core flow."*

**What the interviewer is really checking**
Whether patterns are tools you apply for a reason, not a list you memorised, and whether you know where Spring already gives them to you.

**How I answer it** (120-second answer, point by point)
1. **Strategy + Spring injection:** a `PaymentProcessor` interface with one bean per rail. Spring injects `Map<String, PaymentProcessor>`, so adding RTP is one new class. That is **Open/Closed** and **Dependency Inversion**.
2. **Template Method:** an abstract base defines the fixed flow (validate -> reserve -> send -> confirm); each rail fills in the steps that differ. I use it only when the flow really is shared.
3. **Builder:** for objects with many optional fields, such as a `PaymentInstruction`. A record plus a small builder, or Lombok `@Builder`.
4. **Factory:** choosing the right implementation at runtime, often just the Spring map lookup.
5. **Adapter / anti-corruption layer:** wraps a legacy or external API so its model does not leak into my domain.
6. **Decorator:** add retry, metrics or caching around a client without changing it. Spring AOP proxies (`@Transactional`, `@Cacheable`) are decorators.
7. **Singleton:** Spring beans are singletons by default, so I almost never hand-write one. If I must, I use an enum or the holder idiom.
8. **Observer:** domain events (`ApplicationEventPublisher`, or Kafka between services).
9. **SOLID in one line each:** small focused classes (S), extend by adding classes (O), subclasses honour the parent's contract (L), small interfaces (I), depend on interfaces injected by Spring (D).

**Trade-offs and what can go wrong**
- Pattern overuse: a factory of factories for one implementation is noise. Add the abstraction when the second variant arrives.
- Template Method uses inheritance, so it couples tightly. Composition (strategies inside one flow) is often cleaner.

**Follow-ups to expect**
- *Thread-safe singleton without Spring?* -> An enum singleton, or a static holder class; double-checked locking needs `volatile`.
- *Which pattern does `RestTemplate`/`JdbcTemplate` use?* -> Template Method with callbacks.
- *Liskov violation example?* -> A `ReadOnlyList` that throws on `add` while claiming to be a `List`.

**60-second answer**
"In a payments service, each rail (card, ACH, wire) is a Strategy implementing PaymentProcessor, and Spring injects all of them as a map, so adding RTP is one new class with no change to the core flow. That's Open/Closed and Dependency Inversion. I use a Builder for instructions with many optional fields, an Adapter as an anti-corruption layer around legacy APIs, and Decorators for retry and metrics. Spring itself uses proxies for transactions and caching. Singletons come free with Spring beans. I add a pattern when real variation appears, not before, because unnecessary abstraction is a cost too."
