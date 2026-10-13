/*
 * 02 - Coding round: the Java 8 stream questions every interviewer asks
 *
 * Run:  java 02_java8_stream_coding_questions.java
 *
 * Interview angle: "group employees by department", "second highest salary", "highest paid per
 * department", "partition even/odd", "count word frequency", "find duplicates", "first
 * non-repeated character using streams", "flatMap", "joining", "sort by two fields", "toMap with
 * duplicate keys", "sum/average/summary statistics", "convert a list to a map". Each answer is
 * checked, and the traps (empty stream, ties, null-unsafe comparators, duplicate keys) are shown.
 */
import java.util.*;
import java.util.function.Function;
import java.util.stream.*;

class Java8StreamCodingQuestions {

    record Emp(int id, String name, String dept, double salary, int age) { }

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    public static void main(String[] args) {
        List<Emp> emps = List.of(
                new Emp(1, "Asha", "ENG", 120_000, 34),
                new Emp(2, "Bala", "ENG", 150_000, 41),
                new Emp(3, "Chen", "ENG", 150_000, 29),      // tie with Bala on purpose
                new Emp(4, "Divya", "HR", 70_000, 38),
                new Emp(5, "Eli", "HR", 65_000, 26),
                new Emp(6, "Farah", "OPS", 90_000, 45));

        section("1. Grouping and counting");
        Map<String, Long> countByDept = emps.stream()
                .collect(Collectors.groupingBy(Emp::dept, TreeMap::new, Collectors.counting()));
        check("count per department", "{ENG=3, HR=2, OPS=1}", countByDept.toString());

        Map<String, Double> avgByDept = emps.stream()
                .collect(Collectors.groupingBy(Emp::dept, TreeMap::new, Collectors.averagingDouble(Emp::salary)));
        check("average salary per department", "{ENG=140000.0, HR=67500.0, OPS=90000.0}", avgByDept.toString());

        Map<String, List<String>> namesByDept = emps.stream()
                .collect(Collectors.groupingBy(Emp::dept, TreeMap::new,
                        Collectors.mapping(Emp::name, Collectors.toList())));
        check("names per department", "{ENG=[Asha, Bala, Chen], HR=[Divya, Eli], OPS=[Farah]}", namesByDept.toString());

        Map<Boolean, Long> over40 = emps.stream()
                .collect(Collectors.partitioningBy(e -> e.age() > 40, Collectors.counting()));
        check("partitioningBy age > 40 (always has both keys)", "{false=4, true=2}", over40.toString());

        section("2. Highest / second highest / top-N");
        Optional<Emp> top = emps.stream().max(Comparator.comparingDouble(Emp::salary));
        check("max by salary (first of the ties)", "Bala", top.map(Emp::name).orElse("none"));

        Map<String, String> topPerDept = emps.stream().collect(Collectors.groupingBy(Emp::dept, TreeMap::new,
                Collectors.collectingAndThen(Collectors.maxBy(Comparator.comparingDouble(Emp::salary)),
                        o -> o.get().name())));
        check("highest paid per department", "{ENG=Bala, HR=Divya, OPS=Farah}", topPerDept.toString());

        // Second highest DISTINCT salary. distinct() first, otherwise the tie makes "second" == highest.
        Optional<Double> second = emps.stream().map(Emp::salary).distinct()
                .sorted(Comparator.reverseOrder()).skip(1).findFirst();
        check("second highest distinct salary", 120_000.0, second.orElse(-1.0));

        List<String> top3 = emps.stream()
                .sorted(Comparator.comparingDouble(Emp::salary).reversed().thenComparing(Emp::name))
                .limit(3).map(Emp::name).collect(Collectors.toList());
        check("top 3 by salary desc, name asc as tie-break", "[Bala, Chen, Asha]", top3.toString());

        section("3. Sorting on several fields, and toMap");
        List<String> sorted = emps.stream()
                .sorted(Comparator.comparing(Emp::dept).thenComparing(Emp::salary, Comparator.reverseOrder())
                        .thenComparing(Emp::name))
                .map(Emp::name).toList();
        check("dept asc, salary desc, name asc", "[Bala, Chen, Asha, Divya, Eli, Farah]", sorted.toString());

        Map<Integer, String> byId = emps.stream().collect(Collectors.toMap(Emp::id, Emp::name));
        check("toMap id -> name (size)", 6, byId.size());

        try {   // THE trap: duplicate keys throw IllegalStateException unless you pass a merge function
            emps.stream().collect(Collectors.toMap(Emp::dept, Emp::name));
            check("toMap duplicate key must throw", "threw", "did not throw");
        } catch (IllegalStateException e) {
            check("toMap with duplicate key throws", true, e.getMessage().startsWith("Duplicate key"));
        }
        Map<String, String> merged = emps.stream().collect(
                Collectors.toMap(Emp::dept, Emp::name, (a, b) -> a + "+" + b, TreeMap::new));
        check("toMap with merge function", "{ENG=Asha+Bala+Chen, HR=Divya+Eli, OPS=Farah}", merged.toString());

        section("4. Strings with streams");
        String text = "to be or not to be that is the question to be";
        Map<String, Long> freq = Arrays.stream(text.split(" "))
                .collect(Collectors.groupingBy(Function.identity(), TreeMap::new, Collectors.counting()));
        check("word frequency", "{be=3, is=1, not=1, or=1, question=1, that=1, the=1, to=3}", freq.toString());

        String mostCommon = freq.entrySet().stream().max(Map.Entry.comparingByValue())
                .map(Map.Entry::getKey).orElse("");
        check("most frequent word (max keeps the first of ties)", "be", mostCommon);

        Character firstUnique = "swiss".chars().mapToObj(c -> (char) c)
                .collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
                .entrySet().stream().filter(e -> e.getValue() == 1).map(Map.Entry::getKey).findFirst().orElse(null);
        check("first non-repeating char via streams", 'w', firstUnique);

        Set<Integer> seen = new HashSet<>();
        List<Integer> dups = Stream.of(1, 2, 3, 2, 4, 3, 5, 1).filter(n -> !seen.add(n)).distinct().toList();
        check("duplicates (Set.add returns false)", "[2, 3, 1]", dups.toString());

        String joined = emps.stream().map(Emp::name).map(String::toUpperCase).collect(Collectors.joining(", ", "[", "]"));
        check("joining with prefix/suffix", "[ASHA, BALA, CHEN, DIVYA, ELI, FARAH]", joined);

        long vowels = "interview".chars().filter(c -> "aeiou".indexOf(c) >= 0).count();
        check("count vowels", 4L, vowels);

        boolean isPalin = IntStream.range(0, "madam".length() / 2)
                .allMatch(i -> "madam".charAt(i) == "madam".charAt("madam".length() - 1 - i));
        check("palindrome with IntStream", true, isPalin);

        section("5. Numbers and flattening");
        List<Integer> nums = List.of(5, 12, 7, 20, 3, 8);
        check("sum", 55, nums.stream().mapToInt(Integer::intValue).sum());
        check("average (OptionalDouble)", 9.166666666666666, nums.stream().mapToInt(i -> i).average().orElse(0));
        IntSummaryStatistics st = nums.stream().mapToInt(i -> i).summaryStatistics();
        check("summaryStatistics min/max/count", "3/20/6", st.getMin() + "/" + st.getMax() + "/" + st.getCount());
        check("reduce product 1..5", 120, IntStream.rangeClosed(1, 5).reduce(1, (a, b) -> a * b));
        check("even numbers squared", "[144, 400, 64]",
                nums.stream().filter(n -> n % 2 == 0).map(n -> n * n).toList().toString());
        check("sum of an EMPTY stream is 0, max is empty", "0/false",
                IntStream.empty().sum() + "/" + IntStream.empty().max().isPresent());

        List<List<Integer>> nested = List.of(List.of(1, 2), List.of(3), List.of(), List.of(4, 5));
        check("flatMap", "[1, 2, 3, 4, 5]",
                nested.stream().flatMap(List::stream).collect(Collectors.toList()).toString());
        check("fizzbuzz 1..15 tail", "[13, 14, FizzBuzz]",
                IntStream.rangeClosed(1, 15).mapToObj(i -> i % 15 == 0 ? "FizzBuzz" : i % 5 == 0 ? "Buzz"
                        : i % 3 == 0 ? "Fizz" : String.valueOf(i)).skip(12).toList().toString());

        section("6. Traps a reviewer will probe");
        Stream<Integer> s = Stream.of(1, 2, 3);
        s.forEach(x -> { });
        try {
            s.forEach(x -> { });
            check("reusing a stream must throw", "threw", "did not throw");
        } catch (IllegalStateException e) {
            check("a stream is single-use", "stream has already been operated upon or closed", e.getMessage());
        }

        List<String> lazy = new ArrayList<>();
        Stream.of("a", "b", "c").peek(lazy::add).filter(x -> x.equals("b")).findFirst();
        check("short-circuit: peek ran only until the match", "[a, b]", lazy.toString());

        // sorted() is a barrier; it needs every element, so it defeats lazy short-circuiting
        List<String> order = new ArrayList<>();
        Stream.of(3, 1, 2).peek(n -> order.add("p" + n)).sorted().peek(n -> order.add("s" + n)).findFirst();
        check("sorted() reads everything before emitting", "[p3, p1, p2, s1]", order.toString());

        // NPE in comparators: nulls need nullsFirst/nullsLast
        List<String> withNull = Arrays.asList("b", null, "a");
        withNull.sort(Comparator.nullsLast(Comparator.naturalOrder()));
        check("nullsLast comparator", "[a, b, null]", withNull.toString());

        System.out.println("\nAll " + checks + " checks passed.");
    }
}
