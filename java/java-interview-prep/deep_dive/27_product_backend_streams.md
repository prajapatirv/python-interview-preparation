# Java Streams, collections and generics

Questions 52–85 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Work through a tied salary

Assume a Java 17 record Employee(String id, String department, String name, long salary), with salary in one currency's minor units. Stream expressions below use java.util.stream.Collectors and Comparator static methods.

```java
Map<String, Optional<Employee>> bestByDepartment = employees.stream()
    .collect(groupingBy(Employee::department,
        maxBy(comparingLong(Employee::salary).thenComparing(Employee::id))));
```

Given engineering employees A and B at 9000 and C at 7000, the winner is B because maxBy uses the larger ID on a tie. The second distinct salary is 7000. Top two employee rows are A and B under a descending-salary, ascending-ID sort. Before coding, ask which of those three outputs the interviewer wants.

## Interview questions and answers

### Q52. Given Employee list, find highest, second-highest and Nth-highest salary.

For distinct salary ranks use employees.stream().map(Employee::salary).distinct().sorted(reverseOrder()).skip(n-1L).findFirst(). Validate n≥1 and return Optional for a missing rank. For salaries 90,90,70 the second distinct salary is 70. Ranking employees individually requires a tie-breaker. For maximum alone use max in O(n), avoiding the full sort.

### Q53. Find highest-paid employee in each department.

Use groupingBy(Employee::department, maxBy(comparing(Employee::salary))). Each downstream accumulator retains the best employee seen for that department. Add an employee-ID tie-breaker for a deterministic single winner. To return everyone tied for first, compute department maxima then filter the original employees against their group's maximum.

### Q54. Group employees by department; count employees in each department.

groupingBy(Employee::department) builds a map of lists for later per-employee inspection. groupingBy(Employee::department, counting()) stores only a Long count per department, so retained space is proportional to the number of departments. Define how missing department values are represented before grouping.

### Q55. Calculate average salary department-wise; sum salaries by department.

For whole minor currency units, groupingBy(Employee::department, summingLong(Employee::salary)) totals by department. averagingLong produces a double suitable for approximate reporting. For financial calculations accumulate BigDecimal amounts and counts, then divide using an explicit scale and rounding rule. Group by currency as well if currencies differ.

### Q56. Partition employees by salary / age threshold.

partitioningBy(e -> e.salary() >= cutoff) creates true and false buckets, even if one is empty. Substitute an age predicate for an age threshold. For a report needing counts only, pass counting() downstream. Test the employee exactly at the cutoff to demonstrate the inclusive rule.

### Q57. Sort employees by salary descending and name ascending.

Use comparing(Employee::salary).reversed().thenComparing(Employee::name). Reversing before adding the name comparator keeps tied names ascending. Add an immutable ID as the final comparator for reproducible page boundaries. State null ordering if names are optional.

### Q58. Find duplicate numbers / strings and their frequency using Streams.

Collect groupingBy(identity(), counting()), then filter the resulting entries to counts greater than one. The same pipeline works for numbers and strings whose equality implements the intended identity. Normalize case first if business rules demand it. Frequency storage costs O(distinct keys), and the source is traversed once.

### Q59. Find first non-repeating character and first repeated character.

Count code points and scan the original order for the first count of one. Clarify “first repeated”: in “abba” the first second-occurrence is b, found by scanning with a set, while the earliest-position character that repeats is a, found by rescanning counts. Keep set mutation in an ordinary loop for deterministic encounter behavior.

### Q60. Find frequency of each character / word in a string.

Use s.codePoints().boxed() with groupingBy(identity(), counting()) for Unicode code-point counts. For words, agree on tokenization, punctuation and case folding, then stream the tokens into the same collector. Splitting on whitespace alone treats “order” and “order,” as distinct keys.

### Q61. Flatten List<List<Integer>> and transform nested objects using flatMap.

nested.stream().flatMap(List::stream) turns each inner list into zero or more elements. For order lines use orders.stream().flatMap(o -> o.lines().stream().map(line -> toDto(o,line))). Capturing the outer order retains parent context. Define whether missing child lists should be rejected or treated as empty.

### Q62. Find common elements between two lists; remove duplicates while preserving order.

Build a HashSet from the second list, then stream the first through filter(allowed::contains).distinct() to retain first encounter order. Expected time O(m+n). For multiset intersection store counts from the second list and decrement on matches in a loop. For simple ordered deduplication, ordered-stream distinct() suffices.

### Q63. Convert List to Map; handle duplicate keys with a merge function.

Use toMap(Employee::id, identity(), mergeFn). Design the collision rule from the domain, for example retaining the record with the greatest revision and resolving equal revisions explicitly. Use LinkedHashMap::new as the fourth argument if iteration order is part of the contract. Silent first-wins can conceal bad upstream IDs.

### Q64. Find top 3 highest-paid employees; top N elements using sorted and limit.

Sort by decreasing salary, then ascending ID and limit(3), collecting the employees. Generalize to limit(n) for nonnegative n. This selects exactly up to n rows, so it may exclude employees tied at the cutoff. A bounded heap gives O(m log n) for m employees when n is small, followed by sorting the winners.

### Q65. Join names with delimiter; convert list of strings to uppercase.

Map employees to names then collect(joining(", ")) to insert separators only between names. For uppercase labels use map(s -> s.toUpperCase(Locale.ROOT)) and collect to a list. Choose a user locale for natural-language presentation and define how blank names should appear.

### Q66. Separate even and odd numbers; find sum, average, min and max.

partitioningBy(x -> x % 2 == 0) separates both signs correctly. For summary values use mapToInt(Integer::intValue).summaryStatistics() in one pass. Inspect count before reporting min, max or average for empty input because summary statistics expose sentinel extrema. Sum uses a long accumulator.

### Q67. Find the longest string; strings beginning with a given prefix.

Use max(comparingInt(String::length)) for an Optional longest string and filter(s -> s.startsWith(prefix)) for prefix matches. Length counts UTF-16 code units. If equal-length ties need a stable business ordering, include it in the comparator. An empty prefix matches every non-null string.

### Q68. map() vs flatMap(); filter() vs map(); findFirst() vs findAny().

map produces one result per input, flatMap concatenates nested streams, and filter preserves elements passing a predicate. findFirst respects encounter order, while findAny allows any match, useful for parallel searches without a ranking requirement. All find operations return Optional for an empty result.

### Q69. Intermediate vs terminal operations; lazy evaluation; short-circuiting.

Intermediate operations build a lazy pipeline. A terminal operation triggers traversal, so filter and map may execute element by element until anyMatch succeeds. Stateful sorted generally must buffer the input first. Side effects in peek are unreliable for business updates because stages may short-circuit or be optimized away.

### Q70. How does a Stream pipeline execute? Can a stream be reused?

A source spliterator feeds elements through intermediate stages into a terminal sink. Stateless stages can fuse into one pass, while distinct or sorted may store state. A consumed stream cannot be traversed again. For two independent computations obtain fresh streams from the collection or combine the summaries in one collector.

### Q71. Collectors.toMap(): what happens when duplicate keys exist?

The two-argument toMap collector throws IllegalStateException on duplicate keys. If multiple rows really belong to one key, groupingBy preserves them. If the domain specifies one winner, pass an associative merge such as maxBy(revisionComparator) and define ties. Test with two different objects sharing an ID.

### Q72. groupingBy() vs partitioningBy(); reducing() vs summingInt().

groupingBy supports many classifier keys. partitioningBy always represents both Boolean partitions. reducing expresses a general associative combination, such as maximum by comparator. summingInt specializes integer addition and returns an Integer, so widen to summingLong for potentially large totals.

### Q73. How do you preserve encounter order? ordered vs unordered streams.

A list supplies encounter order and an ordered pipeline can preserve it into a list. Use forEachOrdered when terminal action order matters, including in parallel. unordered() relaxes the order constraint and does not shuffle. To define order on an unordered source, sort explicitly using a total comparator.

### Q74. Stream vs parallelStream; common ForkJoinPool and thread-safety risks.

Parallel streams split input and combine partial reductions, typically using the common ForkJoinPool. They can help large CPU-bound associative workloads. Blocking calls compete for workers and shared mutable lists can lose updates. Prefer collectors with isolated accumulators, and measure representative input sizes against a sequential baseline.

### Q75. How do you handle checked exceptions inside lambda expressions?

Standard Function cannot declare arbitrary checked exceptions. Extract a helper that catches the specific checked exception and either wraps it with context or returns an explicit per-record result. For an import needing all error rows, collect those results. For fail-fast file processing, propagate UncheckedIOException and preserve the original cause.

### Q76. Primitive streams: IntStream, LongStream, DoubleStream and boxing overhead.

mapToInt, mapToLong and mapToDouble feed primitive pipelines with sum, average and specialized optionals. This avoids boxing every arithmetic intermediate. boxed() returns to a reference stream when collectors require objects. Widen to long before summation if integer totals can overflow.

### Q77. When should you prefer a loop over Streams?

Prefer a loop when a parser maintains several dependent pieces of state, must break on an error with its index, or needs checked-exception handling. For example a two-pointer scan updating both ends is clearer as a while loop. For measured hot paths compare allocations and throughput before rewriting a readable pipeline.

### Q78. ArrayList vs LinkedList; HashSet vs TreeSet vs LinkedHashSet.

ArrayList gives constant-time indexing and amortized append. LinkedList has node overhead and O(n) indexed access, with cheap insertion at a known iterator position. HashSet offers expected constant-time membership, LinkedHashSet adds encounter order, and TreeSet provides ordered iteration and range operations in O(log n) per update. Its comparator defines which keys count as equal.

### Q79. HashMap vs Hashtable vs ConcurrentHashMap.

HashMap suits single-threaded or externally guarded access and accepts null. Hashtable synchronizes individual calls and rejects null keys and values. ConcurrentHashMap permits concurrent access and atomic per-key operations such as compute. With any concurrent map, a sequence of separate calls can still race.

### Q80. How does HashMap work internally? Collision handling, resizing and treeification.

HashMap spreads the hash and indexes a power-of-two bucket array. It compares hashes and equality within a bucket, chains collisions and may treeify a long bin at sufficient table capacity. Resizing redistributes bins and costs O(n) for that operation. Good hash distribution yields expected constant-time lookup. Pre-size for known bulk loads.

### Q81. equals() and hashCode() contract; mutable keys in HashMap.

Equality must be reflexive, symmetric, transitive and consistent. Equal objects must have equal hash codes, while collisions among unequal objects are allowed. If a field used by hashCode changes after insertion, lookup searches the new bucket and may miss the entry. Use immutable value keys such as an immutable order identifier.

### Q82. Comparable vs Comparator; fail-fast vs fail-safe iterators.

Comparable supplies one natural ordering. Comparator supplies external or composed alternatives. A fail-fast ArrayList iterator may detect structural changes and throw ConcurrentModificationException on a best-effort basis. “Fail-safe” is informal: CopyOnWriteArrayList iterates a snapshot, whereas ConcurrentHashMap offers weak consistency as updates proceed.

### Q83. How does ConcurrentHashMap provide thread safety?

ConcurrentHashMap in modern JDK implementations combines volatile reads, CAS for some uncontended writes, and coordination on affected bins for competing updates. Reads generally avoid locking. Use merge(key,1,Integer::sum) for atomic increments per key. Aggregate views during writes can reflect different instants.

### Q84. Collection vs Collections; List vs Set vs Map.

Collection is the root interface for element containers such as List and Set. Collections is a utility class with algorithms and wrappers. A List preserves positional order and permits duplicates. A Set enforces uniqueness. Map is a separate key-to-value interface, exposing entries, keys and values through collection views.

### Q85. Generics, wildcards, extends vs super, type erasure.

Generic types are invariant, so List<Integer> cannot be passed as List<Number>. A producer declared ? extends Number safely supplies Numbers, while ? super Integer accepts Integer values but reads generally as Object. Erasure removes most type arguments at runtime, explaining why instanceof List<String> and new T() are unavailable.
