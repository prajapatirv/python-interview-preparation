/*
 * 07 - Reported streams round: 20 coding drills and the concept traps, on Employee and Department data
 *
 * Run:  java 07_streams_sde2_employee_drills.java
 *
 * Interview angle: "35 Java Streams questions for SDE-2". Interviewers change the data to test
 * real understanding: two people share the top salary, a department is empty, an id repeats, a
 * value is null. Every drill here is asserted on data that contains those cases. The numbering
 * matches banks 95 (coding, Q1-Q20) and 96 (concepts, Q1-Q15) in interview-scenarios/.
 */
import java.time.LocalDate;
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

class StreamsSde2Drills {

    record Employee(int id, String name, String dept, double salary, LocalDate joined) {}

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    // Asha and Dev deliberately share the top salary: that is what breaks skip(1) answers.
    static final List<Employee> EMPLOYEES = List.of(
        new Employee(1, "Asha",  "Engineering", 90_000, LocalDate.of(2021, 1, 15)),
        new Employee(2, "Dev",   "Engineering", 90_000, LocalDate.of(2022, 3, 10)),
        new Employee(3, "Meera", "Engineering", 75_000, LocalDate.of(2021, 1, 20)),
        new Employee(4, "Ravi",  "Sales",       60_000, LocalDate.of(2023, 7, 1)),
        new Employee(5, "Sara",  "Sales",       55_000, LocalDate.of(2020, 3, 5)),
        new Employee(6, "Amit",  "HR",          45_000, LocalDate.of(2019, 11, 25)));

    static List<String> names(Collection<Employee> es) { return es.stream().map(Employee::name).toList(); }

    /** Q13: Nth highest DISTINCT salary. Optional because n can exceed the distinct count. */
    static OptionalDouble nthHighest(List<Employee> es, int n) {
        if (n < 1) throw new IllegalArgumentException("n must be >= 1");
        return es.stream().mapToDouble(Employee::salary).distinct()
                 .boxed().sorted(Comparator.reverseOrder())
                 .skip(n - 1).mapToDouble(Double::doubleValue).findFirst();
    }

    /** Q4: first non-repeated character. LinkedHashMap keeps encounter order; that is the whole trick. */
    static Optional<Character> firstNonRepeated(String s) {
        return s.chars().mapToObj(c -> (char) c)
                .collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
                .entrySet().stream().filter(e -> e.getValue() == 1).map(Map.Entry::getKey).findFirst();
    }

    /** Q7: first repeated character means the first one seen a second time. Set.add returns false on a repeat. */
    static Optional<Character> firstRepeated(String s) {
        Set<Character> seen = new HashSet<>();
        return s.chars().mapToObj(c -> (char) c).filter(c -> !seen.add(c)).findFirst();
    }

    public static void main(String[] args) {
        coding();
        concepts();
        System.out.println("\nAll " + checks + " checks passed.");
    }

    static void coding() {
        section("1. Coding drills Q1-Q20 (bank 95)");
        var es = EMPLOYEES;

        check("Q1 second highest (distinct) salary", 75_000.0, nthHighest(es, 2).orElseThrow());
        check("Q1 the naive sorted().skip(1) is wrong on ties", 90_000.0,
              es.stream().map(Employee::salary).sorted(Comparator.reverseOrder()).skip(1).findFirst().orElseThrow());

        // Q2: everyone tied at the top of each department, not an arbitrary one.
        Map<String, List<String>> topPerDept = es.stream().collect(Collectors.groupingBy(Employee::dept, TreeMap::new,
            Collectors.collectingAndThen(Collectors.toList(), group -> {
                double max = group.stream().mapToDouble(Employee::salary).max().orElseThrow();
                return group.stream().filter(e -> e.salary() == max).map(Employee::name).toList();
            })));
        check("Q2 highest paid per department, ties kept",
              Map.of("Engineering", List.of("Asha", "Dev"), "HR", List.of("Amit"), "Sales", List.of("Ravi")), topPerDept);
        check("Q2 maxBy returns Optional and only one winner", "Asha",
              es.stream().collect(Collectors.groupingBy(Employee::dept,
                  Collectors.maxBy(Comparator.comparingDouble(Employee::salary)))).get("Engineering").orElseThrow().name());

        List<Integer> withDups = List.of(4, 1, 4, 2, 1, 3);
        Set<Integer> seen = new HashSet<>();
        check("Q3 duplicates with Set.add (stateful, sequential only)", List.of(4, 1),
              withDups.stream().filter(n -> !seen.add(n)).distinct().toList());
        check("Q3 duplicates with groupingBy (safe, no shared state)", List.of(4, 1),
              withDups.stream().collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
                      .entrySet().stream().filter(e -> e.getValue() > 1).map(Map.Entry::getKey).toList());

        check("Q4 first non-repeated char", Optional.of('w'), firstNonRepeated("swiss"));
        check("Q4 none exists", Optional.empty(), firstNonRepeated("aabb"));
        check("Q5 char frequency", new TreeMap<>(Map.of('a', 3L, 'b', 1L, 'n', 2L)),
              "banana".chars().mapToObj(c -> (char) c)
                      .collect(Collectors.groupingBy(Function.identity(), TreeMap::new, Collectors.counting())));
        check("Q6 word frequency, case and punctuation folded", new TreeMap<>(Map.of("the", 2L, "cat", 1L, "sat", 1L, "mat", 1L)),
              Arrays.stream("The cat sat, the mat.".toLowerCase().split("\\W+")).filter(w -> !w.isBlank())
                    .collect(Collectors.groupingBy(Function.identity(), TreeMap::new, Collectors.counting())));
        check("Q7 first repeated char", Optional.of('b'), firstRepeated("abcba"));

        double avg = es.stream().mapToDouble(Employee::salary).average().orElse(0);
        check("Q8 above the average salary", List.of("Asha", "Dev", "Meera"),
              es.stream().filter(e -> e.salary() > avg).map(Employee::name).toList());
        check("Q9 group by department", List.of("Ravi", "Sara"),
              names(es.stream().collect(Collectors.groupingBy(Employee::dept)).get("Sales")));
        check("Q9 count per department", new TreeMap<>(Map.of("Engineering", 3L, "HR", 1L, "Sales", 2L)),
              es.stream().collect(Collectors.groupingBy(Employee::dept, TreeMap::new, Collectors.counting())));
        check("Q10 sort by salary desc, then name", List.of("Asha", "Dev", "Meera", "Ravi", "Sara", "Amit"),
              es.stream().sorted(Comparator.comparingDouble(Employee::salary).reversed().thenComparing(Employee::name))
                .map(Employee::name).toList());

        List<Integer> nums = List.of(7, 2, 9, 4);
        check("Q11 max", 9, nums.stream().max(Integer::compare).orElseThrow());
        check("Q11 min on primitives", 2, nums.stream().mapToInt(Integer::intValue).min().orElseThrow());
        var stats = nums.stream().mapToInt(Integer::intValue).summaryStatistics();
        check("Q11 one pass for both", "2..9", stats.getMin() + ".." + stats.getMax());

        check("Q12 top 3 distinct salaries", List.of(90_000.0, 75_000.0, 60_000.0),
              es.stream().map(Employee::salary).distinct().sorted(Comparator.reverseOrder()).limit(3).toList());
        check("Q13 Nth highest, n=4", 55_000.0, nthHighest(es, 4).orElseThrow());
        check("Q13 n beyond the data is empty, not an exception", OptionalDouble.empty(), nthHighest(es, 99));

        Map<Boolean, List<Integer>> parts = IntStream.rangeClosed(1, 6).boxed().collect(Collectors.partitioningBy(n -> n % 2 == 0));
        check("Q14 evens", List.of(2, 4, 6), parts.get(true));
        check("Q14 odds", List.of(1, 3, 5), parts.get(false));

        var salary = es.stream().mapToDouble(Employee::salary).summaryStatistics();
        check("Q15 sum", 415_000.0, salary.getSum());
        check("Q15 average rounded", 69_167L, Math.round(salary.getAverage()));

        Map<Integer, Employee> byId = es.stream().collect(Collectors.toMap(Employee::id, Function.identity()));
        check("Q16 List to Map by id", "Ravi", byId.get(4).name());

        check("Q17 names starting with A", List.of("Asha", "Amit"),
              es.stream().map(Employee::name).filter(n -> n.startsWith("A")).toList());
        check("Q18 longest string", Optional.of("Meera"),
              es.stream().map(Employee::name).max(Comparator.comparingInt(String::length)));
        check("Q19 distinct keeps first-seen order", List.of(4, 1, 2, 3), withDups.stream().distinct().toList());

        List<Integer> a = List.of(1, 2, 3, 4, 4), b = List.of(3, 4, 4, 5);
        Set<Integer> inB = new HashSet<>(b);   // O(n + m); b.contains inside the filter would be O(n * m)
        check("Q20 common elements", List.of(3, 4), a.stream().filter(inB::contains).distinct().toList());
    }

    static void concepts() {
        section("2. Laziness: nothing runs until a terminal operation (bank 96 Q2, Q9)");
        List<String> trace = new ArrayList<>();
        Stream<Integer> pipeline = Stream.of(1, 2, 3, 4).filter(n -> { trace.add("filter " + n); return n % 2 == 0; })
                                         .map(n -> { trace.add("map " + n); return n * 10; });
        check("no work before the terminal op", 0, trace.size());
        check("short-circuits on the first match", Optional.of(20), pipeline.findFirst());
        check("elements flow one at a time, and 3 and 4 are never touched",
              List.of("filter 1", "filter 2", "map 2"), trace);

        section("3. A stream is single-use (bank 96 Q10)");
        Stream<Integer> once = Stream.of(1, 2);
        once.count();
        try { once.count(); throw new AssertionError("expected IllegalStateException"); }
        catch (IllegalStateException e) { check("second terminal op throws", "IllegalStateException", e.getClass().getSimpleName()); }
        Supplier<Stream<Integer>> reusable = () -> Stream.of(1, 2);
        check("a Supplier gives a fresh stream each time", 4L, reusable.get().count() + reusable.get().count());

        section("4. peek is for debugging: the JVM may skip it (bank 96 Q5)");
        List<Integer> peeked = new ArrayList<>();
        check("count() of a SIZED source", 3L, List.of(1, 2, 3).stream().peek(peeked::add).count());
        check("peek was elided, so a side effect in it silently vanishes (Java 9+)", 0, peeked.size());
        List<Integer> peekedAgain = new ArrayList<>();
        List.of(1, 2, 3).stream().peek(peekedAgain::add).filter(n -> n > 1).count();
        check("a filter makes the size unknown, so peek runs", 3, peekedAgain.size());

        section("5. toMap traps (bank 95 Q16)");
        List<Employee> dupId = List.of(new Employee(1, "A", "X", 1, LocalDate.EPOCH), new Employee(1, "B", "X", 2, LocalDate.EPOCH));
        try { dupId.stream().collect(Collectors.toMap(Employee::id, Employee::name)); throw new AssertionError(); }
        catch (IllegalStateException e) { check("duplicate key throws", "IllegalStateException", e.getClass().getSimpleName()); }
        check("a merge function decides the winner", "B",
              dupId.stream().collect(Collectors.toMap(Employee::id, Employee::name, (old, neu) -> neu)).get(1));
        try {
            Stream.of("a").collect(Collectors.toMap(k -> k, v -> (String) null));
            throw new AssertionError();
        } catch (NullPointerException e) { check("a null VALUE throws NPE", "NullPointerException", e.getClass().getSimpleName()); }
        Map<String, String> nullsAllowed = Stream.of("a").collect(HashMap::new, (m, s) -> m.put(s, null), HashMap::putAll);
        check("collect with a HashMap accepts null values", true, nullsAllowed.containsKey("a") && nullsAllowed.get("a") == null);

        section("6. Null handling (bank 95 intro)");
        List<String> withNull = Arrays.asList("b", null, "a");
        try { withNull.stream().sorted().toList(); throw new AssertionError(); }
        catch (NullPointerException e) { check("sorted() on a null element throws", "NullPointerException", e.getClass().getSimpleName()); }
        check("filter nulls first", List.of("a", "b"), withNull.stream().filter(Objects::nonNull).sorted().toList());
        check("or nullsLast", Arrays.asList("a", "b", null), withNull.stream().sorted(Comparator.nullsLast(Comparator.naturalOrder())).toList());
        try { Stream.of("x").map(s -> (String) null).findFirst(); throw new AssertionError(); }
        catch (NullPointerException e) { check("findFirst on a null element throws", "NullPointerException", e.getClass().getSimpleName()); }

        section("7. map vs flatMap, reduce vs collect, groupingBy vs partitioningBy (bank 96 Q3, Q7, Q8)");
        check("flatMap flattens one level", List.of("a", "b", "c"),
              Stream.of(List.of("a", "b"), List.of("c")).flatMap(List::stream).toList());
        check("reduce folds immutable values", 10, IntStream.rangeClosed(1, 4).reduce(0, Integer::sum));
        check("collect mutates a container: O(n) string building", "abc",
              Stream.of("a", "b", "c").collect(Collectors.joining()));
        Map<Boolean, Long> none = Stream.<Integer>empty().collect(Collectors.partitioningBy(n -> n > 0, Collectors.counting()));
        check("partitioningBy always has both keys, even when empty", Map.of(true, 0L, false, 0L), none);
        Map<Boolean, Long> grouped = Stream.<Integer>empty().collect(Collectors.groupingBy(n -> n > 0, Collectors.counting()));
        check("groupingBy has only the keys it saw", Map.of(), grouped);

        section("8. distinct and sorted are stateful (bank 96 Q13, Q14)");
        record Point(int x) {}
        check("distinct uses equals/hashCode, and records generate both", 1L, Stream.of(new Point(1), new Point(1)).distinct().count());
        List<String> order = new ArrayList<>();
        Stream.of(3, 1, 2).peek(n -> order.add("before " + n)).sorted().peek(n -> order.add("after " + n)).limit(1).toList();
        check("sorted buffers ALL input before it emits anything",
              List.of("before 3", "before 1", "before 2", "after 1"), order);

        section("9. findFirst vs findAny, parallel (bank 96 Q6, Q11, Q12)");
        check("findFirst respects encounter order, even in parallel", Optional.of(0),
              IntStream.range(0, 1_000).parallel().boxed().findFirst());
        Optional<Integer> any = IntStream.range(0, 1_000).parallel().boxed().findAny();
        check("findAny returns some element", true, any.isPresent() && any.get() >= 0 && any.get() < 1_000);
        check("a parallel sum is correct with a stateless reduction", 499_500,
              IntStream.range(0, 1_000).parallel().sum());
        List<Integer> unsafe = new ArrayList<>();
        try { IntStream.range(0, 100_000).parallel().forEach(unsafe::add); } catch (RuntimeException ignored) { }
        System.out.println("  note parallel add to ArrayList kept " + unsafe.size() + " of 100000 (non-deterministic, may also throw)");
        check("the safe form collects", 100_000, IntStream.range(0, 100_000).parallel().boxed().toList().size());

        section("10. Exceptions in streams (bank 96 Q15)");
        Function<String, Integer> parse = Integer::parseInt;
        try { Stream.of("1", "x", "3").map(parse).toList(); throw new AssertionError(); }
        catch (NumberFormatException e) { check("first failure aborts the pipeline, unchecked", "NumberFormatException", e.getClass().getSimpleName()); }
        List<String> bad = new ArrayList<>();
        check("collect failures per element instead of aborting", List.of(1, 3),
              Stream.of("1", "x", "3").flatMap(s -> {
                  try { return Stream.of(Integer.parseInt(s)); }
                  catch (NumberFormatException e) { bad.add(s); return Stream.<Integer>empty(); }
              }).toList());
        check("and the rejects are reported", List.of("x"), bad);
    }
}
