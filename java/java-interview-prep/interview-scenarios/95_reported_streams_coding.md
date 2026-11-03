---
id: reported-streams-coding
title: Reported rounds, Java Streams 1/2: 20 coding drills on Employee and Department data (SDE-2)
stack: java
skill: coding
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). These are the 20 coding
questions from a widely shared "35 Java Streams questions for SDE-2" list. The concept questions are in bank 96.

**Every solution here ran and passed**, on data that contains the awkward cases: `examples/21_coding_interview/07_streams_sde2_employee_drills.java`.
The data has two people tied on the top salary, because that is the first thing an interviewer changes.

```java
record Employee(int id, String name, String dept, double salary, LocalDate joined) {}
```

**The five things to say on any streams question** (the difference between SDE-1 and SDE-2):

| Topic | What to say |
|---|---|
| Complexity | Filter and map are O(n). `sorted` is O(n log n) and buffers everything. `distinct` is O(n) time and O(d) space for d distinct values. |
| Nulls | `sorted`, `toMap` values and `findFirst` on a null element all throw NPE. Filter with `Objects::nonNull` or use `Comparator.nullsLast`. |
| Duplicates | `toMap` throws on a duplicate key unless you give a merge function. |
| Ties | Ask "what if two people share the top salary?" before writing `skip(1)`. |
| Loop or stream | Stream when it reads like the requirement. Loop for early exit with state, checked exceptions, or a hot path where allocation shows up in a profiler. |

### Q1 [mid] Find the second-highest salary.
tags: streams, second-highest, distinct, sorted, comparator, optional, ties, coding, reported-streams

**Start here: the concepts**
- `sorted(reverseOrder())` then `skip(1)` gives the second *row*, which is not the same as the second *salary* when there are ties.
- `distinct()` removes repeated values first, so `skip(1)` then means the second *value*.
- `findFirst()` returns an `Optional` because there may be no second value.

**The live scenario (functional requirement)**
*FR: "Show the runner-up pay band on the compensation report."* Asha and Dev both earn 90,000 and Meera earns 75,000. The right answer is 75,000.

**What the interviewer is really checking**
Whether you spot the tie bug without being told, and whether you handle "there is no second salary".

**How I answer it** (120-second answer, point by point)
1. Ask first: "Do you want the second distinct salary, or the second person?" That one question signals experience.
2. Take the salaries as values, remove duplicates, sort descending, skip one:

```java
OptionalDouble second = es.stream().mapToDouble(Employee::salary).distinct()
    .boxed().sorted(Comparator.reverseOrder())
    .skip(1).mapToDouble(Double::doubleValue).findFirst();
```

3. Without `distinct` the same pipeline returns 90,000 on this data. I ran both, and that is the bug.
4. Return `OptionalDouble`, because one employee or all-equal salaries means no answer. Don't return 0, since 0 looks like real data.
5. Complexity: O(n log n) time for the sort and O(d) space.

**Trade-offs and what can go wrong**
- A faster O(n) version keeps the top two in a loop. It is worth writing only on a hot path; on a report the stream is clearer.
- `double` is fine for this exercise. Real money uses `BigDecimal` or integer paise.

**Follow-ups to expect**
- *Who earns it?* -> Compute the value, then `filter(e -> e.salary() == value)`, which also returns everyone tied.
- *Do it per department?* -> Bank 95 Q2 with the same idea inside `groupingBy`.
- *In SQL?* -> `DENSE_RANK() OVER (ORDER BY salary DESC)` and filter on rank 2. `DENSE_RANK` is the SQL form of `distinct`.

**60-second answer**
"I'd first ask whether they mean the second distinct salary. Assuming yes, I map to salaries, call distinct, sort in reverse, skip one and take findFirst, which returns an Optional because there may be no second value. The distinct matters: if two people tie at the top, a plain skip(1) just returns the top salary again. That's O(n log n) because of the sort. If they want the people, I filter by that value so ties are all returned."

### Q2 [mid] Find the highest salary in each department.
tags: streams, groupingby, maxby, collectingandthen, ties, department, coding, reported-streams

**Start here: the concepts**
- `groupingBy(classifier, downstream)` splits the stream into groups and runs a second collector on each group.
- `maxBy` returns `Optional<T>` and only one winner, even on a tie.
- `collectingAndThen` lets you post-process a group, which is how you keep ties.

**The live scenario (functional requirement)**
*FR: "For each department, list the top earner for the awards page."* Engineering has two people at 90,000. An arbitrary pick means one person silently misses the award.

**What the interviewer is really checking**
Downstream collectors, why `maxBy` gives an `Optional`, and whether you consider ties.

**How I answer it** (120-second answer, point by point)
1. The simple version, if one winner is acceptable: `groupingBy(Employee::dept, maxBy(comparingDouble(Employee::salary)))`. The value is `Optional<Employee>`.
2. Unwrap it with `collectingAndThen(maxBy(...), Optional::orElseThrow)`. It cannot be empty, because a group only exists if it has at least one member.
3. To keep ties:

```java
es.stream().collect(groupingBy(Employee::dept, TreeMap::new, collectingAndThen(toList(), group -> {
    double max = group.stream().mapToDouble(Employee::salary).max().orElseThrow();
    return group.stream().filter(e -> e.salary() == max).map(Employee::name).toList();
})));
```

4. `TreeMap::new` gives sorted departments, so the output is stable for a report and a test.
5. Complexity: O(n) to group and O(n) across the group scans, so O(n) overall.

**Trade-offs and what can go wrong**
- A department with no employees never appears, because the data only has rows that exist. If the report must show empty departments, start from the department list and left-join in memory.
- In SQL this is `RANK() OVER (PARTITION BY dept ORDER BY salary DESC)`, and the database does it much better on large data.

**Follow-ups to expect**
- *Why Optional if a group can't be empty?* -> `maxBy` is a general collector and doesn't know that it runs inside `groupingBy`.
- *Only the salary?* -> `mapping(Employee::salary, maxBy(naturalOrder()))`, or a `summarizingDouble` downstream.

**60-second answer**
"groupingBy on department with a downstream maxBy gives one Optional employee per department, and I unwrap it with collectingAndThen because a group is never empty. The catch is ties: maxBy returns just one. If two people share the top salary, I collect the group to a list, find the max, and filter everyone equal to it. I'd use a TreeMap so the output order is stable. On large data I'd push this to SQL with RANK over a partition."

### Q3 [fresher] Find the duplicate elements in a list.
tags: streams, duplicates, set-add, groupingby, stateful-lambda, coding, reported-streams

**Start here: the concepts**
- `Set.add` returns `false` if the element was already there, so it detects a repeat in one call.
- A lambda that changes outside state is a **stateful lambda**, and it is unsafe in a parallel stream.

**The live scenario (functional requirement)**
*FR: "Before a bulk import, report the customer ids that appear more than once."* Input `[4, 1, 4, 2, 1, 3]` should report `[4, 1]`.

**What the interviewer is really checking**
That you know both approaches and can say which is safe.

**How I answer it** (120-second answer, point by point)
1. The short version: `Set<Integer> seen = new HashSet<>(); list.stream().filter(n -> !seen.add(n)).distinct().toList();`. It is O(n), but it mutates shared state, so it works only in a sequential stream.
2. The clean version has no shared state:

```java
list.stream().collect(groupingBy(identity(), LinkedHashMap::new, counting()))
    .entrySet().stream().filter(e -> e.getValue() > 1).map(Map.Entry::getKey).toList();
```

3. `LinkedHashMap` keeps first-seen order, which makes the output predictable.
4. Keep the `.distinct()` in the first version, or an id seen three times gets reported twice.

**Trade-offs and what can go wrong**
- `groupingBy` allocates a counter per distinct value. For most inputs that doesn't matter.
- The element type must have correct `equals` and `hashCode`. Records generate them.

**Follow-ups to expect**
- *How often does each repeat?* -> Keep the map instead of the keys.
- *Sorted input?* -> Compare neighbours in a loop: O(n) time and O(1) extra space.

**60-second answer**
"Two ways. A HashSet inside a filter works because Set.add returns false on a repeat, but it mutates shared state, so it's only safe sequentially. The cleaner way is groupingBy with counting into a LinkedHashMap, then keep entries with a count above one, which has no shared state and keeps first-seen order. Both are O(n), and both depend on correct equals and hashCode."

### Q4 [mid] Find the first non-repeated character in a string.
tags: streams, first-non-repeated, linkedhashmap, groupingby, encounter-order, coding, reported-streams

**Start here: the concepts**
- A plain `HashMap` has no useful order, so "first" needs a `LinkedHashMap`.
- `chars()` returns an `IntStream`; `mapToObj(c -> (char) c)` turns it into a stream of `Character`.

**The live scenario (functional requirement)**
*FR: "In a support-chat tool, highlight the first character that appears only once in a token."* `"swiss"` gives `w`. `"aabb"` gives nothing.

**What the interviewer is really checking**
That the choice of map is deliberate, because it is the whole answer.

**How I answer it** (120-second answer, point by point)

```java
s.chars().mapToObj(c -> (char) c)
 .collect(groupingBy(identity(), LinkedHashMap::new, counting()))
 .entrySet().stream().filter(e -> e.getValue() == 1).map(Map.Entry::getKey).findFirst();
```

1. Count every character, keeping insertion order.
2. Walk the entries in that order and return the first with a count of 1.
3. Return `Optional<Character>`, because there may be none.
4. Complexity: O(n) time and O(k) space for k distinct characters.

**Trade-offs and what can go wrong**
- With `groupingBy` and the default `HashMap`, the code runs and looks right, and it fails on some inputs. That is the trap to name.
- `chars()` works on UTF-16 units. For emoji and other supplementary characters, use `codePoints()`.

**Follow-ups to expect**
- *Case-insensitive?* -> `toLowerCase()` first, and mention `Locale.ROOT`.
- *ASCII only?* -> An `int[128]` array is faster and allocates almost nothing.
- *The second non-repeating character?* -> `skip(1)` before `findFirst`. See bank 91 Q10.

**60-second answer**
"I count characters with groupingBy and counting, passing LinkedHashMap::new so insertion order is kept. Then I stream the entries, filter on a count of one, and take findFirst, which returns an Optional since there may be none. The LinkedHashMap is the key decision, because a HashMap has no useful order and the answer would be wrong on some inputs. It's O(n) time and O(k) space for k distinct characters."

### Q5 [fresher] Count the frequency of each character in a string.
tags: streams, frequency, groupingby, counting, treemap, coding, reported-streams

**Start here: the concepts**
- `groupingBy(identity(), counting())` is the standard frequency recipe. `counting()` produces `Long`.

**The live scenario (functional requirement)**
*FR: "Show letter frequency for a text-analysis feature."* `"banana"` gives `{a=3, b=1, n=2}`.

**What the interviewer is really checking**
Fluency with the recipe, and awareness of what order the map returns.

**How I answer it** (120-second answer, point by point)

```java
s.chars().mapToObj(c -> (char) c).collect(groupingBy(identity(), TreeMap::new, counting()));
```

1. `identity()` means the character is its own key.
2. `TreeMap::new` sorts by key. Use `LinkedHashMap::new` for first-seen order, or the two-argument form if order doesn't matter.
3. To sort by count, stream the entries with `Map.Entry.comparingByValue(reverseOrder())`.
4. O(n) time with a hash map. With a `TreeMap`, O(n log k).

**Trade-offs and what can go wrong**
- The boxing cost is real. On a large text in a hot path, an `int[]` counter is far cheaper.

**Follow-ups to expect**
- *Why Long, not Integer?* -> `counting()` is defined to return `Long`. For `Integer`, use `summingInt(c -> 1)`.
- *Ignore spaces?* -> `filter(c -> !Character.isWhitespace(c))` before collecting.

**60-second answer**
"I turn the string into a stream of characters with chars and mapToObj, then collect with groupingBy on identity and counting. I pass TreeMap or LinkedHashMap if the output order matters. Counting gives Long values. It's linear time, and in a really hot path I'd use an int array because boxing every character costs allocation."

### Q6 [fresher] Count the frequency of each word in a sentence.
tags: streams, word-frequency, split, regex, normalisation, coding, reported-streams

**Start here: the concepts**
- The hard part is deciding what a word is. Split on `\W+` and lower-case first.

**The live scenario (functional requirement)**
*FR: "Tag cloud for customer reviews."* `"The cat sat, the mat."` must count `the` twice, even though the case differs and one word has a trailing comma next to it.

**What the interviewer is really checking**
Whether you normalise the input instead of splitting on a single space.

**How I answer it** (120-second answer, point by point)

```java
Arrays.stream(text.toLowerCase().split("\\W+")).filter(w -> !w.isBlank())
      .collect(groupingBy(identity(), TreeMap::new, counting()));
```

1. Lower-case, so `The` and `the` match.
2. `\W+` splits on any run of non-word characters, which handles commas, full stops and double spaces.
3. The filter removes the empty token you get when text starts with punctuation.
4. For the top N words, sort the entries by value descending and `limit(n)`.

**Trade-offs and what can go wrong**
- `\W` treats non-ASCII letters as separators by default, which breaks Hindi or accented text. Use the `UNICODE_CHARACTER_CLASS` flag or a proper tokenizer for real language data.
- Loading the whole text with `split` is wrong for a huge file. Use `Files.lines` and `flatMap`, which reads lazily.

**Follow-ups to expect**
- *Large file?* -> `Files.lines(path).flatMap(l -> Arrays.stream(l.split("\\W+")))` inside try-with-resources, because the stream holds a file handle.

**60-second answer**
"Lower-case the text, split on the regex backslash-W-plus so punctuation and repeated spaces all act as separators, filter out blanks, then groupingBy identity with counting. The normalising is what they're really checking, because splitting on one space would count 'the' and 'The,' as different words. For a large file I'd use Files.lines with flatMap so it reads lazily, inside try-with-resources."

### Q7 [fresher] Find the first repeated character.
tags: streams, first-repeated, set-add, short-circuit, coding, reported-streams

**Start here: the concepts**
- "First repeated" means the first character *seen a second time* while scanning. In `abcba` that is `b`, because the second `b` arrives before the second `a`.
- `findFirst` short-circuits: the scan stops as soon as it has an answer.

**The live scenario (functional requirement)**
*FR: "Reject a generated code at the first repeated symbol, and report which one."*

**What the interviewer is really checking**
Whether you define "first" correctly, and whether you notice that this can stop early.

**How I answer it** (120-second answer, point by point)

```java
Set<Character> seen = new HashSet<>();
s.chars().mapToObj(c -> (char) c).filter(c -> !seen.add(c)).findFirst();
```

1. `seen.add` returns false on the first repeat, and the filter lets exactly that character through.
2. `findFirst` stops the pipeline there, so a long string with an early repeat costs almost nothing.
3. This is a stateful lambda, so it is sequential only. In this problem order is the requirement anyway.

**Trade-offs and what can go wrong**
- A plain `for` loop is just as short and has no stateful-lambda concern. Saying so is a good answer to "stream or loop?".

**Follow-ups to expect**
- *How does it differ from Q4?* -> Q4 must scan everything, because a later repeat disqualifies an earlier character. This one can stop early.

**60-second answer**
"I keep a HashSet, and filter on not seen.add, which lets through the first character that's already in the set, then findFirst stops the pipeline right there. In 'abcba' the answer is b, not a, because the second b comes first. It's a stateful lambda, so sequential only, and honestly a simple for loop is equally good here."

### Q8 [fresher] Find employees earning above the average salary.
tags: streams, average, filter, two-passes, optional, coding, reported-streams

**Start here: the concepts**
- `mapToDouble(...).average()` returns `OptionalDouble`, because an empty list has no average.
- A stream is single-use, so computing the average and then filtering takes two pipelines.

**The live scenario (functional requirement)**
*FR: "Flag above-average earners on the HR dashboard."*

**What the interviewer is really checking**
Whether you compute the average once, outside the filter.

**How I answer it** (120-second answer, point by point)

```java
double avg = es.stream().mapToDouble(Employee::salary).average().orElse(0);
List<String> above = es.stream().filter(e -> e.salary() > avg).map(Employee::name).toList();
```

1. Compute the average first and store it. Computing it inside the filter makes the job O(n squared).
2. Decide what an empty list means. `orElse(0)` is safe here, because an empty list has nothing to filter.
3. O(n) time and O(1) extra space beyond the result.

**Trade-offs and what can go wrong**
- `avg` must be effectively final to be used in a lambda, which is another reason to compute it first.

**Follow-ups to expect**
- *Above average within their own department?* -> Group and compute the per-department average first, then filter against that map.

**60-second answer**
"Two passes. First mapToDouble and average, which gives an OptionalDouble because an empty list has no average. Then filter on salary greater than that value. I compute it once outside the lambda, since computing it inside the filter would make it quadratic. For above-average within a department, I'd build a map of department to average first and filter against it."

### Q9 [fresher] Group employees by department.
tags: streams, groupingby, counting, mapping, downstream-collector, coding, reported-streams

**Start here: the concepts**
- `groupingBy(f)` returns `Map<K, List<T>>`. A second argument changes what each group becomes.

**The live scenario (functional requirement)**
*FR: "Org page: departments with their people, plus headcount."*

**What the interviewer is really checking**
Whether you know the downstream forms, because that is where the follow-up always goes.

**How I answer it** (120-second answer, point by point)

| Want | Collector |
|---|---|
| Employees per department | `groupingBy(Employee::dept)` |
| Headcount per department | `groupingBy(Employee::dept, counting())` |
| Names only | `groupingBy(Employee::dept, mapping(Employee::name, toList()))` |
| Salary total | `groupingBy(Employee::dept, summingDouble(Employee::salary))` |
| Sorted departments | `groupingBy(Employee::dept, TreeMap::new, counting())` |
| By department, then by city | `groupingBy(Employee::dept, groupingBy(Employee::city))` |

**Trade-offs and what can go wrong**
- A null classifier result throws NPE, so filter or default a nullable department first.
- The result map's type isn't guaranteed. Pass a factory if you rely on `HashMap` or order.

**Follow-ups to expect**
- *Concurrent version?* -> `groupingByConcurrent`, for parallel streams where order doesn't matter.

**60-second answer**
"groupingBy on department gives a map from department to a list of employees. The second argument is a downstream collector: counting for headcount, mapping for just names, summingDouble for totals, and another groupingBy for nesting. A three-argument form takes a map factory like TreeMap for sorted keys. A null key throws NPE, so I handle a nullable department first."

### Q10 [fresher] Sort employees by salary.
tags: streams, sorted, comparator, thencomparing, reversed, coding, reported-streams

**Start here: the concepts**
- `Comparator.comparingDouble(f)` builds a comparator; `.reversed()` flips it; `.thenComparing(g)` breaks ties.
- `Stream.sorted` is stable for ordered streams, so equal elements keep their input order.

**The live scenario (functional requirement)**
*FR: "Payroll export: highest pay first, and alphabetical among equals, so the file is reproducible."*

**What the interviewer is really checking**
Tie-breaking, and how `.reversed()` behaves in a chain.

**How I answer it** (120-second answer, point by point)

```java
es.stream().sorted(comparingDouble(Employee::salary).reversed().thenComparing(Employee::name)).toList();
```

1. `reversed()` applies to everything built so far. Placed before `thenComparing`, it flips only the salary. Placed at the end, it flips the name order too.
2. Always add a tie-break when the output is compared or paged. Otherwise two runs can differ across a page boundary.
3. O(n log n), and the stream buffers everything before emitting.

**Trade-offs and what can go wrong**
- `comparing(e -> e.salary())` with `.reversed()` can fail to compile, because type inference loses the lambda's type. Use a method reference or `Comparator.<Employee, Double>comparing`.
- Don't sort in Java what the database can sort with an index.

**Follow-ups to expect**
- *Nulls in the sort field?* -> `comparing(Employee::name, nullsLast(naturalOrder()))`.
- *Why not `(a, b) -> a - b`?* -> Integer overflow on large differences. Use `Integer.compare`.

**60-second answer**
"sorted with comparingDouble on salary, reversed, then thenComparing on name for a stable, reproducible order. The placement of reversed matters: it flips everything built so far. Sorted is O(n log n) and buffers the whole stream, so if this comes from a database I'd rather sort there with an index, especially when paging."

### Q11 [fresher] Find the maximum and minimum elements.
tags: streams, max, min, summarystatistics, primitive-streams, coding, reported-streams

**Start here: the concepts**
- `Stream.max(comparator)` returns `Optional<T>`.
- `IntStream.max()` needs no comparator and returns `OptionalInt`.
- `summaryStatistics()` computes count, sum, min, max and average in one pass.

**The live scenario (functional requirement)**
*FR: "Show the lowest and highest sensor reading in one API call."*

**What the interviewer is really checking**
Whether you run two pipelines when one will do, and whether you avoid boxing.

**How I answer it** (120-second answer, point by point)
1. One value: `nums.stream().max(Integer::compare)`.
2. Both, efficiently: `var s = nums.stream().mapToInt(Integer::intValue).summaryStatistics(); s.getMin(); s.getMax();`.
3. An empty list: `Optional` forces a decision. `summaryStatistics` instead returns `Integer.MAX_VALUE` as the min and `Integer.MIN_VALUE` as the max, so check `getCount()` first.

**Trade-offs and what can go wrong**
- `sorted().findFirst()` also works, and it costs O(n log n) for an O(n) job. Don't.
- `max(Integer::max)` compiles and is wrong, because `Integer.max` is not a comparator contract. It is a classic trap question.

**Follow-ups to expect**
- *Max of a field, returning the object?* -> `max(comparingDouble(Employee::salary))`.

**60-second answer**
"For a single value, max or min with a comparator, which returns an Optional. For both together, mapToInt and summaryStatistics gives min, max, sum, count and average in one pass without boxing. On an empty stream the statistics return the extreme int values, so I check the count first. I'd never sort just to find a maximum, because that's O(n log n) for an O(n) job."

### Q12 [mid] Find the top 3 highest salaries.
tags: streams, top-n, limit, distinct, priorityqueue, heap, coding, reported-streams

**Start here: the concepts**
- `sorted` then `limit(3)` still sorts everything, because `sorted` buffers its whole input.
- A size-limited heap keeps only N items, for O(n log N) time and O(N) memory.

**The live scenario (functional requirement)**
*FR: "Leaderboard: top 3 pay bands."* With ties, the distinct values are 90,000, 75,000 and 60,000.

**What the interviewer is really checking**
Top-3 *values* or top-3 *people*, and whether you know the heap option exists for large data.

**How I answer it** (120-second answer, point by point)

```java
es.stream().map(Employee::salary).distinct().sorted(reverseOrder()).limit(3).toList();
```

1. Remove `distinct` for the top 3 *people*. Add a tie-break so the result is deterministic.
2. Cost: O(n log n) and all elements in memory. Fine for thousands.
3. For millions, or for an unbounded feed, use a min-heap of size 3: add each item, and evict the smallest once it exceeds 3. That is O(n log 3), effectively linear, and holds only 3 items.

**Trade-offs and what can go wrong**
- `limit` on a parallel ordered stream is expensive. Keep this sequential.

**Follow-ups to expect**
- *Top 3 per department?* -> `groupingBy` with a downstream that sorts and limits, or `ROW_NUMBER` in SQL.

**60-second answer**
"Map to salary, distinct if they want values rather than people, sort in reverse and limit to three. It reads well, but sorted buffers everything, so it's O(n log n) in time and O(n) in memory. For very large or streaming data I'd use a min-heap capped at size three, which holds only three items and is effectively linear."

### Q13 [mid] Find the Nth highest salary.
tags: streams, nth-highest, distinct, skip, optional, validation, coding, reported-streams

**Start here: the concepts**
- Generalises Q1: `skip(n - 1)`. The edge cases are the point: n is too large, n is zero, or n is negative.

**The live scenario (functional requirement)**
*FR: "API: GET /salaries/rank/{n}."* A client sends `n=99`, and a client sends `n=0`.

**What the interviewer is really checking**
Input validation, and using `Optional` for a legitimate "no answer".

**How I answer it** (120-second answer, point by point)

```java
static OptionalDouble nthHighest(List<Employee> es, int n) {
    if (n < 1) throw new IllegalArgumentException("n must be >= 1");
    return es.stream().mapToDouble(Employee::salary).distinct()
             .boxed().sorted(Comparator.reverseOrder())
             .skip(n - 1).mapToDouble(Double::doubleValue).findFirst();
}
```

1. `n < 1` is a caller bug, so it throws. `skip` itself throws on a negative argument, but with a less helpful message.
2. `n` beyond the data is a normal outcome, so it returns empty. In the API that becomes a 404.
3. I ran it: `n=4` gives 55,000 on the sample data and `n=99` gives empty.

**Trade-offs and what can go wrong**
- For large n on large data, pushing to SQL with `DENSE_RANK` is better than loading the table.

**Follow-ups to expect**
- *In SQL?* -> `SELECT DISTINCT salary ... ORDER BY salary DESC OFFSET n-1 LIMIT 1`, or `DENSE_RANK`.

**60-second answer**
"Same as second-highest with skip of n minus one: map to salary, distinct, sort descending, skip, findFirst. What matters is the edges. An n below one is a programming error, so I throw IllegalArgumentException. An n larger than the number of distinct salaries is a normal outcome, so I return an empty Optional, which the API layer turns into a 404."

### Q14 [fresher] Partition numbers into even and odd.
tags: streams, partitioningby, boolean-key, intstream, coding, reported-streams

**Start here: the concepts**
- `partitioningBy(predicate)` returns `Map<Boolean, List<T>>` with **both keys always present**.

**The live scenario (functional requirement)**
*FR: "Split transactions into pass and fail for the reconciliation report."* A day with no failures must still show an empty fail list.

**What the interviewer is really checking**
Why you'd choose this over `groupingBy`.

**How I answer it** (120-second answer, point by point)

```java
Map<Boolean, List<Integer>> parts = IntStream.rangeClosed(1, 6).boxed()
    .collect(partitioningBy(n -> n % 2 == 0));
```

1. `parts.get(true)` is the evens and `parts.get(false)` the odds.
2. `boxed()` is needed, because `IntStream` has no such `collect` overload.
3. Both keys exist even on an empty stream. I checked this: `partitioningBy` gives `{false=0, true=0}`, and `groupingBy` gives `{}`.

**Trade-offs and what can go wrong**
- `n % 2 == 1` is wrong for negative odd numbers, where the result is -1. Use `== 0` or `!= 0`.

**Follow-ups to expect**
- *Counts only?* -> `partitioningBy(pred, counting())`.

**60-second answer**
"partitioningBy with a predicate gives a map with Boolean keys, and unlike groupingBy both keys are always present, even when the stream is empty, so the caller never gets a null. I use n mod 2 equals zero rather than equals one, because the remainder of a negative odd number is minus one."

### Q15 [fresher] Calculate the salary sum and average.
tags: streams, sum, average, summarystatistics, bigdecimal, coding, reported-streams

**Start here: the concepts**
- `mapToDouble` gives a `DoubleStream`, which has `sum`, `average` and `summaryStatistics`.

**The live scenario (functional requirement)**
*FR: "Payroll summary with the total and average."* On the sample data the sum is 415,000 and the average is about 69,167.

**What the interviewer is really checking**
Whether you avoid two passes, and whether you raise the money-precision issue unprompted.

**How I answer it** (120-second answer, point by point)
1. One pass: `var s = es.stream().mapToDouble(Employee::salary).summaryStatistics();` then `s.getSum()` and `s.getAverage()`.
2. Group-wise: `groupingBy(Employee::dept, averagingDouble(Employee::salary))`.
3. Real money: `double` can't represent 0.1 exactly. Use `BigDecimal` with `reduce(BigDecimal.ZERO, BigDecimal::add)`, or store integer paise.

**Trade-offs and what can go wrong**
- `average()` on an empty stream is an empty `OptionalDouble`; `sum()` is 0. They differ on purpose.

**Follow-ups to expect**
- *Why not `reduce(0.0, Double::sum)`?* -> It boxes, and `sum()` uses compensated summation, which reduces floating-point error.

**60-second answer**
"mapToDouble followed by summaryStatistics gives the sum and average in one pass with no boxing. Per department, I'd use groupingBy with averagingDouble or summingDouble. For real money I wouldn't use double at all, since it can't represent decimal amounts exactly. I'd use BigDecimal with reduce, or store whole paise as a long."

### Q16 [mid] Convert List<Employee> into Map<Id, Employee>.
tags: streams, tomap, duplicate-key, merge-function, null-values, coding, reported-streams

**Start here: the concepts**
- `Collectors.toMap(keyFn, valueFn)` throws `IllegalStateException` on a duplicate key.
- It also throws `NullPointerException` on a null value, even in the `HashMap` form, because it uses `Map.merge` internally.

**The live scenario (functional requirement)**
*FR: "Load employees from two HR feeds into a lookup."* A person appears in both feeds, and production fails at 2 a.m. with "Duplicate key".

**What the interviewer is really checking**
This is the question "duplicate key handling" in the SDE-2 tip refers to.

**How I answer it** (120-second answer, point by point)
1. The basic form: `toMap(Employee::id, identity())`.
2. Duplicates are a business decision, so make it explicit: `toMap(Employee::id, identity(), (oldV, newV) -> newV)`, or throw with a clear message.
3. Ordered map: `toMap(Employee::id, identity(), (a, b) -> a, LinkedHashMap::new)`.
4. Null values: `toMap` throws NPE. I tested that. Use `collect(HashMap::new, (m, e) -> m.put(e.id(), e.nick()), HashMap::putAll)`, or filter them out.

**Trade-offs and what can go wrong**
- "Keep the last one" hides a data problem. If duplicates should never happen, let it fail, or at least log and count them.

**Follow-ups to expect**
- *Group instead of overwrite?* -> `groupingBy(Employee::id)` keeps all rows.
- *Bank 50 Q20* goes through the toMap exception message.

**60-second answer**
"toMap with id and identity. It has two traps. A duplicate key throws IllegalStateException, so I pass a merge function, and which side wins is a business decision. If duplicates should be impossible, I let it fail loudly rather than hide bad data. A null value throws NPE even though HashMap allows nulls, because toMap uses Map.merge, so I filter them or collect manually into a HashMap."

### Q17 [fresher] Find employees whose names start with a given character.
tags: streams, filter, startswith, case-insensitive, null-safe, coding, reported-streams

**Start here: the concepts**
- `filter` with `String.startsWith`. The details are case, nulls and blank input.

**The live scenario (functional requirement)**
*FR: "Directory A-Z filter: the user clicks 'A'."*

**What the interviewer is really checking**
Whether you think about real input, and whether this belongs in the database.

**How I answer it** (120-second answer, point by point)

```java
es.stream().map(Employee::name).filter(Objects::nonNull)
  .filter(n -> n.regionMatches(true, 0, prefix, 0, prefix.length())).toList();
```

1. `regionMatches(true, ...)` ignores case without allocating a new lower-cased string per element.
2. Filter nulls first, or `startsWith` throws NPE.
3. On a real directory this should be `WHERE name LIKE 'A%'`. A trailing wildcard can use an index, while `%A%` can't.

**Trade-offs and what can go wrong**
- `toLowerCase()` without a locale misbehaves on Turkish systems. Use `Locale.ROOT`.

**Follow-ups to expect**
- *Starts with any of several letters?* -> Build a `Set<Character>` and check the first character.

**60-second answer**
"Filter out nulls, then filter with startsWith, or regionMatches for case-insensitive matching without allocating. It's O(n). If this is a real directory page I'd do it in the database with LIKE 'A%', because a prefix pattern can use an index and loading every employee just to filter them isn't sensible."

### Q18 [fresher] Find the longest string in a list.
tags: streams, max, comparingint, ties, optional, coding, reported-streams

**Start here: the concepts**
- `max(Comparator.comparingInt(String::length))` returns `Optional<String>`.

**The live scenario (functional requirement)**
*FR: "Set a column width from the longest name."*

**What the interviewer is really checking**
That you use `max`, not a sort, and what happens on ties.

**How I answer it** (120-second answer, point by point)
1. `list.stream().max(comparingInt(String::length))`. O(n) and no buffering.
2. Ties: `max` returns one of them, not all. For all longest strings, get the maximum length with `mapToInt(...).max()`, then filter on it.
3. For the width alone: `mapToInt(String::length).max().orElse(0)`, which avoids handling the string.

**Trade-offs and what can go wrong**
- `sorted(...).findFirst()` works and costs O(n log n). Mentioning why not is the point.

**Follow-ups to expect**
- *Group by length?* -> `groupingBy(String::length, TreeMap::new, toList())`, then `lastEntry()`.

**60-second answer**
"max with comparingInt on String::length, which is O(n) and returns an Optional for the empty case. If there's a tie it returns only one, so if they want all of them I find the max length first and filter by it. Sorting would also work but costs O(n log n) for no benefit."

### Q19 [fresher] Remove duplicates using Streams.
tags: streams, distinct, equals-hashcode, distinct-by-key, ordering, coding, reported-streams

**Start here: the concepts**
- `distinct()` uses `equals` and `hashCode` and keeps the first occurrence, in encounter order, for ordered streams.

**The live scenario (functional requirement)**
*FR: "De-duplicate customers by email, where the rest of the fields may differ."* `distinct()` can't do this, because the objects aren't equal.

**What the interviewer is really checking**
The distinct-by-key follow-up, which always comes next.

**How I answer it** (120-second answer, point by point)
1. Plain: `list.stream().distinct().toList()`. `[4,1,4,2,1,3]` gives `[4,1,2,3]`, first-seen order kept.
2. By a key, keeping the first:

```java
customers.stream().collect(toMap(Customer::email, identity(), (a, b) -> a, LinkedHashMap::new)).values();
```

3. Or use a `Set<K> seen` with `filter(c -> seen.add(c.email()))`, which is shorter but sequential only.

**Trade-offs and what can go wrong**
- A class without `equals`/`hashCode` is compared by identity, so `distinct` removes nothing, with no error.
- On a parallel ordered stream, `distinct` is costly. If order doesn't matter, call `unordered()` first.

**Follow-ups to expect**
- *Compared with `new HashSet<>(list)`?* -> The set loses order. `new LinkedHashSet<>(list)` keeps it, and is simplest when no other stream steps are needed.

**60-second answer**
"distinct uses equals and hashCode and keeps the first occurrence in order. If the class doesn't implement them it silently removes nothing, so records help. For de-duplicating by one field, I use toMap with the field as key, a merge function keeping the first, and a LinkedHashMap to preserve order. If there's nothing else in the pipeline, a LinkedHashSet is simpler."

### Q20 [mid] Find the common elements between two lists.
tags: streams, intersection, hashset, contains, complexity, coding, reported-streams

**Start here: the concepts**
- `list.contains` is O(n). `set.contains` is O(1) on average. That single decision changes the whole complexity.

**The live scenario (functional requirement)**
*FR: "Find customers in both the CRM export and the billing export."* Both have 200,000 rows.

**What the interviewer is really checking**
Complexity awareness. The short answer is quadratic and most candidates write it.

**How I answer it** (120-second answer, point by point)

```java
Set<Integer> inB = new HashSet<>(b);
a.stream().filter(inB::contains).distinct().toList();
```

1. Build the set first. It is O(m), then the filter is O(n), so O(n + m) overall.
2. The tempting `a.stream().filter(b::contains)` is O(n x m). At 200,000 rows each, that is up to 40 billion comparisons.
3. `distinct()` so that repeats in `a` don't repeat in the output. `[1,2,3,4,4]` and `[3,4,4,5]` give `[3,4]`.

**Trade-offs and what can go wrong**
- If the data is in one database, use a join. Don't pull 200,000 rows into memory.
- `retainAll` is the non-stream way, and it mutates its list.

**Follow-ups to expect**
- *Must duplicates count (multiset)?* -> Count occurrences in one map and decrement as you match.
- *Elements in only one list?* -> `filter(not(inB::contains))`.

**60-second answer**
"I put the second list in a HashSet first, then filter the first list with set::contains and call distinct. That's O(n plus m). The version many people write, filtering with list::contains, is O(n times m), which at a couple of hundred thousand rows is billions of comparisons. If both lists come from one database, a join is better than either."
