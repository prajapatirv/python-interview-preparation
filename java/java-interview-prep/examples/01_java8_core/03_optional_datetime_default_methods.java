/*
 * 03 - Optional, java.time and interface default methods (Java 8)
 *
 * Run:  java 03_optional_datetime_default_methods.java
 *
 * Interview angle: "how should Optional be used?", "orElse vs orElseGet",
 * "why is java.util.Date bad?", "diamond problem with default methods".
 */
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;

class OptionalDateTimeDefaults {

    static int expensiveCalls = 0;
    static String expensiveDefault() { expensiveCalls++; return "computed-default"; }

    interface Walker { default String move() { return "walk"; } }
    interface Swimmer { default String move() { return "swim"; } }
    // Two defaults with the same signature: the compiler FORCES you to resolve it.
    static class Duck implements Walker, Swimmer {
        @Override public String move() { return Walker.super.move() + "+" + Swimmer.super.move(); }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static Optional<String> findEmail(String user) {
        return "ravi".equals(user) ? Optional.of("ravi@example.com") : Optional.empty();
    }

    public static void main(String[] args) {

        section("1. Optional: the useful operations");
        System.out.println("  map/filter chain : " + findEmail("ravi").map(String::toUpperCase).filter(s -> s.contains("@")).orElse("none"));
        System.out.println("  missing user     : " + findEmail("zed").map(String::toUpperCase).orElse("none"));
        System.out.println("  ifPresent        : "); findEmail("ravi").ifPresent(e -> System.out.println("    got " + e));
        try { findEmail("zed").orElseThrow(() -> new NoSuchElementException("user zed not found")); }
        catch (NoSuchElementException e) { System.out.println("  orElseThrow      : " + e.getMessage()); }

        section("2. orElse evaluates EAGERLY, orElseGet lazily");
        expensiveCalls = 0;
        findEmail("ravi").orElse(expensiveDefault());
        System.out.println("  orElse(expensive())    on a PRESENT optional -> expensive ran " + expensiveCalls + " time(s)");
        expensiveCalls = 0;
        findEmail("ravi").orElseGet(OptionalDateTimeDefaults::expensiveDefault);
        System.out.println("  orElseGet(expensive)   on a PRESENT optional -> expensive ran " + expensiveCalls + " time(s)");

        section("3. flatMap avoids Optional<Optional<T>>");
        Optional<Optional<String>> nested = Optional.of("ravi").map(OptionalDateTimeDefaults::findEmail);
        Optional<String> flat = Optional.of("ravi").flatMap(OptionalDateTimeDefaults::findEmail);
        System.out.println("  map     -> " + nested);
        System.out.println("  flatMap -> " + flat);
        // Rules of thumb: Optional is for RETURN types. Do not use it for fields, method
        // parameters, collections elements, or call .get() without isPresent() (use orElseThrow()).

        section("4. java.time is immutable and thread-safe (unlike Date / SimpleDateFormat)");
        LocalDate d = LocalDate.of(2024, 1, 31);
        System.out.println("  d.plusMonths(1)  = " + d.plusMonths(1) + "   (clamps to month end; d itself is unchanged: " + d + ")");
        LocalDateTime meeting = LocalDateTime.of(2025, 3, 30, 9, 0);
        ZonedDateTime utc = meeting.atZone(ZoneId.of("UTC"));
        ZonedDateTime ist = utc.withZoneSameInstant(ZoneId.of("Asia/Kolkata"));
        System.out.println("  same instant     : " + utc.toLocalTime() + " UTC = " + ist.toLocalTime() + " IST");
        System.out.println("  Duration         : " + Duration.ofMinutes(135));
        System.out.println("  Period           : " + Period.between(LocalDate.of(2020, 2, 29), LocalDate.of(2025, 3, 1)));
        System.out.println("  days between     : " + ChronoUnit.DAYS.between(LocalDate.of(2025, 1, 1), LocalDate.of(2025, 12, 31)));
        System.out.println("  formatted        : " + meeting.format(DateTimeFormatter.ofPattern("dd MMM yyyy HH:mm")));
        System.out.println("  Instant (epoch)  : " + Instant.ofEpochSecond(0));
        // Store/transport instants in UTC (Instant / OffsetDateTime); convert to a ZoneId only
        // at the edge for display. LocalDateTime has NO zone: never use it to represent a moment.

        section("5. Default methods and the diamond problem");
        System.out.println("  Duck.move() = " + new Duck().move());
        // Rule 1: a class method always wins over an interface default.
        // Rule 2: the more specific interface wins. Rule 3: otherwise you must override and pick
        // with Iface.super.method().  Default methods exist so List.stream() / Map.forEach() could
        // be added in Java 8 without breaking every existing implementation.
    }
}

// EXERCISE: rewrite a method that returns null for "not found" and throws NPE two layers up so it
// returns Optional<T>. Where would you still keep null (hint: hot loops, JPA entities)?
