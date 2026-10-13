/*
 * 01 - What changed after Java 8: the features worth naming in an interview
 *
 * Run:  java 01_java9_to_21_language_features.java        (needs JDK 21 to compile everything)
 *
 * Each section is tagged with the Java version that introduced the feature. If your project is
 * on Java 11, sections tagged 14+ are "what you gain by upgrading".
 */
import java.util.*;
import java.util.stream.*;

class Java9To21Features {

    // [16] records: immutable data carriers with equals/hashCode/toString generated
    record Point(int x, int y) {
        Point {                                           // compact constructor = validation hook
            if (x < 0 || y < 0) throw new IllegalArgumentException("negative coordinate");
        }
        double distanceToOrigin() { return Math.sqrt((double) x * x + (double) y * y); }
    }

    // [17] sealed hierarchy: the compiler knows every permitted subtype
    sealed interface Shape permits Circle, Square, Rect { }
    record Circle(double r) implements Shape { }
    record Square(double side) implements Shape { }
    record Rect(double w, double h) implements Shape { }

    static double area(Shape s) {                          // [21] pattern matching for switch, exhaustive: no default
        return switch (s) {
            case Circle c -> Math.PI * c.r() * c.r();
            case Square q -> q.side() * q.side();
            case Rect r -> r.w() * r.h();
        };
    }

    static String describe(Object o) {                     // [21] type patterns + guards + record deconstruction
        return switch (o) {
            case null -> "null!";
            case Integer i when i > 100 -> "big int " + i;
            case Integer i -> "int " + i;
            case String s -> "string of length " + s.length();
            case Point(int x, int y) -> "point at " + x + "," + y;
            default -> "something else: " + o.getClass().getSimpleName();
        };
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("[10/11] var and the new String methods");
        var names = new ArrayList<String>();                // local variable type inference (compile-time, still static typing)
        names.add("  ravi ");
        System.out.println("  isBlank=" + "   ".isBlank() + ", strip='" + names.get(0).strip() + "', repeat=" + "ab".repeat(3)
                + ", lines=" + "a\nb\nc".lines().count());
        // 'var' is for locals only: not for fields, parameters or return types; never var x = null.

        section("[9/10] Immutable factories and Collectors.toUnmodifiable*");
        List<Integer> immutable = List.of(1, 2, 3);
        Map<String, Integer> map = Map.of("a", 1, "b", 2);
        List<Integer> evens = Stream.of(1, 2, 3, 4).filter(i -> i % 2 == 0).collect(Collectors.toUnmodifiableList());
        System.out.println("  " + immutable + " " + new TreeMap<>(map) + " " + evens + "  | Stream.toList() (16): " + Stream.of(9, 8).toList());

        section("[9/11] Optional additions and Stream.takeWhile / dropWhile");
        System.out.println("  Optional.isEmpty (11): " + Optional.empty().isEmpty()
                + ", or (9): " + Optional.empty().or(() -> Optional.of("alt")).get()
                + ", ifPresentOrElse (9) ->");
        Optional.of("x").ifPresentOrElse(v -> System.out.println("    present " + v), () -> System.out.println("    absent"));
        System.out.println("  takeWhile(<4): " + Stream.of(1, 2, 3, 6, 1).takeWhile(n -> n < 4).collect(Collectors.toList())
                + "  dropWhile(<4): " + Stream.of(1, 2, 3, 6, 1).dropWhile(n -> n < 4).collect(Collectors.toList()));

        section("[15] Text blocks");
        String json = """
                {
                  "service": "orders",
                  "ok": true
                }""";
        System.out.println(json.indent(2).stripTrailing());

        section("[16] Records");
        Point p = new Point(3, 4);
        System.out.println("  " + p + " equals=" + p.equals(new Point(3, 4)) + " hash-equal=" + (p.hashCode() == new Point(3, 4).hashCode())
                + " dist=" + p.distanceToOrigin());
        try { new Point(-1, 0); } catch (IllegalArgumentException e) { System.out.println("  compact ctor validation -> " + e.getMessage()); }

        section("[16] Pattern matching for instanceof");
        Object o = "hello";
        if (o instanceof String s && s.length() > 3) System.out.println("  no cast needed: " + s.toUpperCase());

        section("[14/17/21] Switch expressions, sealed types, pattern switch");
        int day = 3;
        String kind = switch (day) { case 1, 7 -> "weekend"; case 2, 3, 4, 5, 6 -> "weekday"; default -> "invalid"; };
        System.out.println("  day " + day + " is a " + kind);
        List<Shape> shapes = List.of(new Circle(1), new Square(2), new Rect(2, 3));
        shapes.forEach(sh -> System.out.printf("  %-28s area=%.2f%n", sh, area(sh)));
        for (Object x : new Object[]{7, 700, "hey", new Point(1, 2), 3.5, null}) System.out.println("  describe -> " + describe(x));

        section("[21] Sequenced collections");
        List<String> seq = new ArrayList<>(List.of("first", "middle", "last"));
        System.out.println("  getFirst=" + seq.getFirst() + " getLast=" + seq.getLast() + " reversed=" + seq.reversed());

        section("Which LTS has what (for 'why upgrade?' questions)");
        System.out.println("  Java 8  (2014): lambdas, streams, Optional, java.time, CompletableFuture");
        System.out.println("  Java 11 (2018): var in lambda, HttpClient, String methods, Files.readString, Epsilon/ZGC (experimental)");
        System.out.println("  Java 17 (2021): records, sealed classes, text blocks, switch expressions, strong encapsulation, ZGC/G1 gains");
        System.out.println("  Java 21 (2023): virtual threads, pattern switch, record patterns, sequenced collections, generational ZGC");
        System.out.println("  Java 25 (2025): next LTS - scoped values, structured concurrency previews/finalised, compact object headers");
    }
}

// EXERCISE: model a payment result as a sealed interface (Approved, Declined(reason), Pending) and
// write a switch that is exhaustive without 'default'. Add a 4th case and see the compiler complain.
