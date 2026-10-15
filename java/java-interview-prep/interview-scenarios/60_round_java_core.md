---
id: round-java-core
title: Real interview round: core Java and streams
stack: java
skill: java-core
---
Questions asked in a real interview round, answered from the basics. The two code answers were compiled
and run with a JDK before being written here.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Program output: Arrays.asList("A","B","C").stream().filter(x -> {System.out.println(x); return x.equals("B");}).findFirst();
tags: streams, lazy-evaluation, short-circuit, findfirst, filter, output-question, basics

**Start here: the concepts**
- **Stream pipeline:** a source (`list.stream()`), zero or more *intermediate* operations (`filter`, `map`), and one *terminal* operation (`findFirst`, `collect`, `forEach`).
- **Intermediate operation:** describes work but does **not run anything** by itself. `filter(...)` alone prints nothing.
- **Terminal operation:** starts the pipeline. Nothing in the stream executes until a terminal operation is called.
- **Lazy evaluation:** elements are pulled through the pipeline one at a time, only as far as the terminal operation needs.
- **Short-circuiting operation:** a terminal operation such as `findFirst`, `anyMatch` or `limit` that can stop as soon as it has its answer.
- **Optional:** the box `findFirst()` returns, which may or may not contain a value.

**The live scenario**
A team has a stream that calls a remote price service inside `filter` to find the first product under 100. They expected 10,000 remote calls and were surprised to see only 3 in the logs; on another day they saw all 10,000 because someone added `.sorted()` before `findFirst()`. Same code shape, very different behaviour. This "what does it print" question tests whether you understand exactly why.

**What the interviewer is really checking**
That you know streams are lazy and process **element by element**, and that a short-circuiting terminal operation stops the pipeline early.

**How I answer it**
1. **Output:**
```text
A
B
```
2. **Why:** `findFirst()` is the terminal operation and it is short-circuiting. The stream takes `"A"`: the filter prints `A` and returns false, so it asks for the next element. It takes `"B"`: prints `B`, returns true, and `findFirst` has its answer, so the pipeline stops. `"C"` is never touched, so it is never printed.
3. **The returned `Optional[B]` is discarded**, so nothing else prints. Only the `println` inside the filter produced output.
4. **Contrast to remember:**
   - replace `findFirst()` with `collect(Collectors.toList())` and it prints `A`, `B`, `C`, because it must see everything;
   - add `.sorted()` before `findFirst()` and all three elements are processed first, because `sorted` is a *stateful* operation that needs every element before it can emit the first.
5. **Side effects in lambdas are a smell.** Printing or mutating state inside `filter` or `map` makes behaviour depend on laziness and order; keep pipeline functions pure.

**Trade-offs and what can go wrong**
- Relying on side effects in a stream is fragile: parallel streams and reordering change the behaviour.
- `findFirst` respects encounter order (stable); `findAny` is cheaper in parallel streams but may return any match.
- A stream can only be consumed once; reusing it throws `IllegalStateException`.

**Test cases I'd walk through**
- `findFirst` on `"A","B","C"` with `equals("B")` prints `A`, `B`; result `Optional[B]`.
- No element matches: prints `A`, `B`, `C`; result `Optional.empty`.
- Without a terminal operation: prints nothing at all.

**Follow-ups to expect**
- *What if you use `anyMatch`?* -> same early exit: it stops at the first element that matches.
- *What changes with `parallelStream()`?* -> element order of the prints is not guaranteed, and more elements may be evaluated than strictly needed.
- *Why is `peek` risky?* -> it is meant for debugging; because of laziness it may not run for elements the pipeline never reaches.

**60-second answer**
It prints `A` and then `B`, and nothing else. Streams are lazy: the filter runs only when the terminal operation asks for elements, one at a time. `findFirst` is short-circuiting, so as soon as `B` passes the filter it stops and `C` is never evaluated. The returned `Optional[B]` is thrown away, so the only output is the prints inside the filter. If I used `collect` it would print all three, and with `sorted()` first it would also process every element.

### Q2 [mid] Write stream code to display, for each department, the employee with the highest salary: class Employee {String name; String department; int salary;}
tags: streams, collectors, groupingby, maxby, tomap, employee, department, coding, basics

**Start here: the concepts**
- **Collector:** a recipe that says how to gather stream elements into a result (a list, a map, a count).
- **`groupingBy(classifier)`:** splits elements into groups by a key, producing a `Map<Key, List<Element>>`. A *downstream collector* can reduce each group further.
- **`maxBy(comparator)`:** a collector that picks the largest element and returns it as an `Optional`, because a group could be empty.
- **`toMap(key, value, mergeFunction)`:** builds a map; the merge function decides what to keep when two elements share a key.
- **Comparator:** a rule for ordering objects, for example `Comparator.comparingInt(Employee::salary)`.

**The live scenario**
HR asks for a report: "the top earner in every department". With 5,000 employees a nested loop with manual max tracking works but is long and easy to get wrong when a department has several people on the same top salary. The interviewer wants to see whether you reach for `groupingBy` and a downstream collector, and whether you think about ties and empty groups.

**What the interviewer is really checking**
Comfort with `Collectors.groupingBy` and downstream collectors, handling `Optional`, and awareness of ties.

**How I answer it**
1. **Clarify:** one employee per department, or all employees tied for the top salary? What if two have the same salary? I assume one per department and mention ties.
2. **Brute force:** loop over employees, keep a `Map<String, Employee>` and replace when a higher salary appears. Correct, but verbose.
3. **Stream solution with `groupingBy` and `maxBy`:**

```java
Map<String, Optional<Employee>> topByDept = employees.stream()
    .collect(Collectors.groupingBy(Employee::department,
             Collectors.maxBy(Comparator.comparingInt(Employee::salary))));

topByDept.forEach((dept, emp) ->
    emp.ifPresent(e -> System.out.println(dept + " -> " + e.name() + " (" + e.salary() + ")")));
```

4. **A cleaner alternative with `toMap` and `BinaryOperator.maxBy`**, which avoids the `Optional`:

```java
Map<String, Employee> topByDept = employees.stream()
    .collect(Collectors.toMap(Employee::department, e -> e,
             BinaryOperator.maxBy(Comparator.comparingInt(Employee::salary))));
```

5. **Ties:** both versions keep one employee (the first encountered for equal salaries). To list everyone tied, group, compute the maximum salary per group, then filter the group on that value.
6. **Complexity:** one pass over the data, O(n) time, O(d) extra space for d departments.

**Trade-offs and what can go wrong**
- `groupingBy` + `maxBy` returns `Optional` values (never empty in practice, but the type says so); `toMap` with `maxBy` is neater.
- `toMap` **without** a merge function throws `IllegalStateException` on duplicate keys, a classic bug.
- `Collectors.toMap` rejects null values; the result map is a `HashMap`, so department order is not stable: use `LinkedHashMap::new` or `TreeMap::new` as the map supplier when order matters.
- Do not sort the whole list by salary and take the first per department when only the maximum is needed: that is O(n log n).

**Test cases I'd walk through**
- Two employees in IT (90, 120) -> Ben, 120.
- A department with one employee returns that employee.
- Two employees tied at the top in HR -> one returned (document the rule), or both with the tie-aware version.
- Empty list -> empty map.

**Follow-ups to expect**
- *Second highest salary per department?* -> group, sort each group by salary descending, skip(1), findFirst.
- *Return just the names?* -> add `Collectors.collectingAndThen(maxBy(...), o -> o.map(Employee::name).orElse(null))` as the downstream collector.
- *Why not `sorted().findFirst()`?* -> it sorts everything; `max` is one pass.

**60-second answer**
I group the employees by department and reduce each group with `maxBy` on salary: `groupingBy(Employee::department, maxBy(comparingInt(Employee::salary)))`. That gives a map of department to an `Optional` of its top earner, which I print. A neater option is `toMap` with `BinaryOperator.maxBy`, which avoids the `Optional`. It is one pass, O(n). I would ask about ties, because both versions keep only one employee per department by default.

### Q3 [senior] What is the internal mechanism of HashMap after Java 8?
tags: hashmap, internals, treeify, resize, hash-collision, load-factor, java8, basics

**Start here: the concepts**
- **Array of buckets:** a `HashMap` is backed by an array (called the *table*); each slot is a *bucket*.
- **Hash code and index:** `hashCode()` of the key is turned into a bucket index so a lookup jumps almost directly to the right slot.
- **Collision:** two different keys landing in the same bucket. Collisions are normal and must be handled.
- **Load factor:** how full the table may get before it grows; the default is 0.75.
- **Resize (rehash):** when the number of entries exceeds `capacity x load factor`, the table doubles and entries are redistributed.
- **Treeification:** a long chain in one bucket is converted from a linked list to a balanced red-black tree.

**The live scenario**
A session cache keyed by a custom object has a poor `hashCode()` that returns only a few distinct values. Before Java 8, lookups in those buckets degraded to scanning long linked lists, and a flood of colliding keys could even be used to slow a server down. Since Java 8, a heavily colliding bucket becomes a tree, so the worst case drops from O(n) to O(log n), and the service stays usable while the real fix (a better `hashCode`) is deployed.

**What the interviewer is really checking**
That you can walk through `put` and `get`, name the thresholds, and explain what Java 8 changed.

**How I answer it**
1. **Structure:** `Node<K,V>[] table`, default capacity 16, load factor 0.75, capacity always a power of two. Each node holds the hash, key, value and a `next` pointer.
2. **Hash spreading:** the hash is `h ^ (h >>> 16)`, mixing high bits into low bits so poor hash codes still distribute across the table.
3. **Index:** `(n - 1) & hash`, which equals `hash % n` for power-of-two sizes but is faster.
4. **`put`:**
   - empty bucket: place the node there;
   - occupied: walk the bucket comparing `hash` and then `equals()`; replace the value if the key exists, otherwise append to the **tail** of the list (Java 7 inserted at the head);
   - when a chain reaches 8 nodes and the table capacity is at least 64, the bucket is converted into a **red-black tree**; if the table is smaller than 64, it resizes instead;
   - when the size exceeds the threshold, the table **doubles**.
5. **`get`:** compute the index, check the first node, then walk the list or search the tree, comparing hash then `equals()`. Average O(1), worst case O(log n) for a tree bucket.
6. **Resize:** nodes are split into a "low" and a "high" list depending on one extra hash bit, preserving relative order; no full recomputation of hashes is needed.
7. **Untreeify:** a tree bucket shrinks back to a linked list when it falls to 6 nodes.
8. **Other facts:** one `null` key is allowed (stored in bucket 0); it is not thread-safe; iteration order is not guaranteed.

**Trade-offs and what can go wrong**
- Tree buckets need keys to be `Comparable` for efficient ordering; otherwise the tree falls back to identity-hash tie-breaking.
- Resizing is expensive; pre-size with `new HashMap<>(expected / 0.75 + 1)` when the count is known.
- Mutable keys whose hash changes after insertion make entries unreachable.
- Concurrent writes can corrupt the map or lose updates; use `ConcurrentHashMap`.

**Test cases I'd walk through**
- Insert 13 entries into a default map: the 13th triggers a resize from 16 to 32 (13 > 12).
- Insert many keys with the same hash: the bucket converts to a tree after 8 and the table has at least 64 slots.
- `put(null, "x")` then `get(null)` returns `"x"`.

**Follow-ups to expect**
- *Why is capacity a power of two?* -> index calculation becomes a bitwise AND, and resize can split buckets with one bit.
- *HashMap vs ConcurrentHashMap?* -> `ConcurrentHashMap` uses CAS and per-bin locking for thread-safe updates and does not allow null keys or values.
- *HashMap vs Hashtable?* -> Hashtable is legacy and fully synchronised.
- *What is the contract between equals and hashCode?* -> equal objects must have equal hash codes.

**60-second answer**
A `HashMap` is an array of buckets; the key's hash is spread with `h ^ (h >>> 16)` and the index is `(n - 1) & hash`. Collisions chain nodes in a linked list; since Java 8, when a bucket reaches 8 nodes and the table has at least 64 slots it becomes a red-black tree, turning the worst case from O(n) into O(log n), and it reverts at 6. The table doubles when the size passes 0.75 of capacity, and entries are split by one hash bit. Appending goes to the tail, null key is allowed, and the map is not thread-safe.
