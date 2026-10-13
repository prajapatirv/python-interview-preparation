/*
 * 02 - Streams API and Collectors (Java 8)
 *
 * Run:  java 02_streams_collectors.java
 *
 * Interview angle: "map vs flatMap", "intermediate vs terminal", "are streams lazy?",
 * "groupingBy / partitioningBy / toMap duplicates", "when NOT to use parallel streams".
 */
import java.util.*;
import java.util.stream.*;
import static java.util.stream.Collectors.*;

class StreamsCollectors {

    static final class Emp {
        final String name, dept; final int salary, age;
        Emp(String name, String dept, int salary, int age) { this.name = name; this.dept = dept; this.salary = salary; this.age = age; }
        String getName() { return name; } String getDept() { return dept; }
        int getSalary() { return salary; } int getAge() { return age; }
        @Override public String toString() { return name; }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        List<Emp> emps = Arrays.asList(
                new Emp("Asha", "ENG", 150, 31), new Emp("Bela", "ENG", 120, 27),
                new Emp("Chen", "ENG", 120, 45), new Emp("Dev", "OPS", 90, 38),
                new Emp("Esha", "OPS", 95, 29), new Emp("Farid", "HR", 70, 50));

        section("1. Laziness: nothing happens until a terminal operation");
        Stream<Integer> pipeline = Stream.of(1, 2, 3, 4, 5, 6)
                .filter(n -> { System.out.println("  filter " + n); return n % 2 == 0; })
                .map(n -> { System.out.println("  map    " + n); return n * 10; });
        System.out.println("  pipeline built, nothing printed above this line");
        Optional<Integer> first = pipeline.findFirst();   // short-circuits: stops after 2 elements
        System.out.println("  findFirst -> " + first.get() + "  (elements 3..6 were never touched)");

        section("2. map vs flatMap");
        List<List<String>> nested = Arrays.asList(Arrays.asList("a", "b"), Arrays.asList("c"), Arrays.asList("d", "e"));
        System.out.println("  map     -> " + nested.stream().map(l -> l.size()).collect(toList()));
        System.out.println("  flatMap -> " + nested.stream().flatMap(List::stream).collect(toList()));

        section("3. groupingBy with downstream collectors");
        System.out.println("  count per dept   : " + new TreeMap<>(emps.stream().collect(groupingBy(Emp::getDept, counting()))));
        System.out.println("  avg salary/dept  : " + new TreeMap<>(emps.stream().collect(groupingBy(Emp::getDept, averagingInt(Emp::getSalary)))));
        System.out.println("  names per dept   : " + new TreeMap<>(emps.stream().collect(groupingBy(Emp::getDept, mapping(Emp::getName, joining("/"))))));
        Map<String, Optional<Emp>> top = emps.stream().collect(groupingBy(Emp::getDept, maxBy(Comparator.comparingInt(Emp::getSalary))));
        System.out.println("  top earner/dept  : " + new TreeMap<>(top));

        section("4. partitioningBy always has BOTH keys, even when empty");
        Map<Boolean, List<Emp>> parts = emps.stream().collect(partitioningBy(e -> e.getAge() > 60));
        System.out.println("  age > 60 -> " + parts);

        section("5. toMap: duplicate keys throw unless you give a merge function");
        try {
            emps.stream().collect(toMap(Emp::getDept, Emp::getName));
        } catch (IllegalStateException e) {
            System.out.println("  no merge fn -> IllegalStateException: " + e.getMessage());
        }
        Map<String, String> merged = emps.stream().collect(toMap(Emp::getDept, Emp::getName, (a, b) -> a + "," + b, TreeMap::new));
        System.out.println("  with merge fn -> " + merged);

        section("6. Sorting with a comparator chain");
        List<Emp> sorted = emps.stream()
                .sorted(Comparator.comparingInt(Emp::getSalary).reversed().thenComparing(Emp::getName))
                .collect(toList());
        System.out.println("  salary desc, then name -> " + sorted);

        section("7. reduce, summary statistics and primitive streams");
        int total = emps.stream().mapToInt(Emp::getSalary).sum();
        IntSummaryStatistics stats = emps.stream().mapToInt(Emp::getSalary).summaryStatistics();
        System.out.println("  sum=" + total + " stats=" + stats);
        System.out.println("  second highest distinct salary = "
                + emps.stream().map(Emp::getSalary).distinct().sorted(Comparator.reverseOrder()).skip(1).findFirst().get());
        System.out.println("  IntStream.rangeClosed(1,5).reduce(1,*) = " + IntStream.rangeClosed(1, 5).reduce(1, (a, b) -> a * b));

        section("8. A stream can be consumed only once");
        Stream<String> once = Stream.of("x", "y");
        once.forEach(s -> { });
        try { once.forEach(s -> { }); }
        catch (IllegalStateException e) { System.out.println("  second use -> " + e.getMessage()); }

        section("9. Parallel streams: correct only if the work is stateless and associative");
        List<Integer> unsafeTarget = new ArrayList<>();
        try {
            IntStream.range(0, 20_000).parallel().forEach(unsafeTarget::add);   // data race on ArrayList
            System.out.println("  unsafe add : expected 20000, got " + unsafeTarget.size() + "  (may differ, or throw)");
        } catch (RuntimeException e) {
            System.out.println("  unsafe add : threw " + e.getClass().getSimpleName() + " (the race corrupted the list)");
        }
        List<Integer> safe = IntStream.range(0, 20_000).parallel().boxed().collect(toList());
        System.out.println("  collect()  : always " + safe.size() + "  <- use collectors, not shared mutation");
        // EXPERIMENT: time a parallel stream over a LinkedList vs ArrayList of 5M ints. Splitting a
        // LinkedList is O(n), so parallel is often *slower* there. Parallel also shares the common
        // ForkJoinPool with every other parallel stream in the JVM - a blocking call starves them.
    }
}

// EXERCISE: given a list of sentences, return the 3 most frequent words (case-insensitive) as
// Map<String, Long> ordered by count desc, using only one stream pipeline.
