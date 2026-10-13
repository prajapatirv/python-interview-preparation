/*
 * 01 - Lambdas, method references and functional interfaces (Java 8)
 *
 * Run:  java 01_lambdas_functional_interfaces.java
 *
 * Interview angle: "What is a functional interface?", "lambda vs anonymous class",
 * "why must captured variables be effectively final?", "how do you handle checked
 * exceptions inside a lambda?".
 */
import java.util.*;
import java.util.function.*;

class LambdasFunctionalInterfaces {

    // ---- 1. A custom functional interface: exactly ONE abstract method
    @FunctionalInterface
    interface Validator<T> {
        boolean validate(T value);                       // the single abstract method

        default Validator<T> and(Validator<T> other) {   // default methods do not count
            return v -> validate(v) && other.validate(v);
        }

        static <T> Validator<T> not(Validator<T> v) {    // static methods do not count either
            return x -> !v.validate(x);
        }
    }

    // ---- 3. 'this' means different things in a lambda and an anonymous class
    static class Greeter {
        final String name = "Greeter-instance";

        Runnable viaAnonymous() {
            return new Runnable() {
                final String name = "anonymous-instance";
                public void run() { System.out.println("  anonymous class: this.name = " + this.name); }
            };
        }

        Runnable viaLambda() {
            return () -> System.out.println("  lambda:          this.name = " + this.name);
        }
    }

    // ---- 4. Checked exceptions: the standard functional interfaces do not declare them
    @FunctionalInterface
    interface ThrowingFunction<T, R> { R apply(T t) throws Exception; }

    static <T, R> Function<T, R> unchecked(ThrowingFunction<T, R> f) {
        return t -> {
            try { return f.apply(t); }
            catch (RuntimeException e) { throw e; }
            catch (Exception e) { throw new RuntimeException(e); }
        };
    }

    static int parseStrict(String s) throws Exception {
        if (s.isEmpty()) throw new Exception("empty input");
        return Integer.parseInt(s);
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("1. The core functional interfaces (java.util.function)");
        Function<String, Integer> length = String::length;                 // T -> R
        Predicate<String> isEmpty = String::isEmpty;                        // T -> boolean
        Consumer<String> printer = s -> System.out.println("  consumed: " + s); // T -> void
        Supplier<List<String>> factory = ArrayList::new;                    // () -> T
        BiFunction<Integer, Integer, Integer> add = Integer::sum;           // (T,U) -> R
        UnaryOperator<String> upper = String::toUpperCase;                  // T -> T
        BinaryOperator<Integer> max = Math::max;                            // (T,T) -> T
        printer.accept("length(hello) = " + length.apply("hello"));
        System.out.println("  isEmpty(\"\") = " + isEmpty.test("") + ", add = " + add.apply(2, 3)
                + ", upper = " + upper.apply("abc") + ", max = " + max.apply(4, 9)
                + ", factory = " + factory.get());

        section("2. Composition: andThen / compose / and / or / negate");
        Function<Integer, Integer> doubleIt = x -> x * 2;
        Function<Integer, Integer> plusTen = x -> x + 10;
        System.out.println("  doubleIt.andThen(plusTen)(5) = " + doubleIt.andThen(plusTen).apply(5)); // 20
        System.out.println("  doubleIt.compose(plusTen)(5) = " + doubleIt.compose(plusTen).apply(5)); // 30
        Predicate<String> longWord = s -> s.length() > 4;
        Predicate<String> startsWithA = s -> s.startsWith("a");
        System.out.println("  long AND startsWithA: " + longWord.and(startsWithA).test("apple"));
        System.out.println("  long OR  startsWithA: " + longWord.or(startsWithA).test("ant"));
        System.out.println("  negate(long): " + longWord.negate().test("ant"));

        Validator<String> notBlank = s -> !s.trim().isEmpty();
        Validator<String> shortEnough = s -> s.length() <= 8;
        Validator<String> username = notBlank.and(shortEnough);
        System.out.println("  username('ravi') = " + username.validate("ravi")
                + ", username('a-very-long-name') = " + username.validate("a-very-long-name")
                + ", not(notBlank)('   ') = " + Validator.not(notBlank).validate("   "));

        section("3. Lambda vs anonymous class: what does 'this' point to?");
        Greeter g = new Greeter();
        g.viaAnonymous().run();
        g.viaLambda().run();
        Runnable lambda = () -> { };
        System.out.println("  lambda class is JVM-generated at runtime (invokedynamic), not a .class file on disk: "
                + lambda.getClass().getName().contains("$$Lambda"));

        section("4. Captured variables must be effectively final");
        int base = 100;                      // effectively final: never reassigned
        Function<Integer, Integer> addBase = x -> x + base;
        System.out.println("  addBase(5) = " + addBase.apply(5));
        // EXPERIMENT: add 'base++;' after the lambda and watch the compiler refuse.
        // The workaround when you really need mutation is a holder (AtomicInteger / int[1]),
        // but that is usually a sign you should be using a stream reduction instead.
        int[] counter = {0};
        Runnable inc = () -> counter[0]++;
        inc.run(); inc.run();
        System.out.println("  mutated through a 1-element array: " + counter[0]);

        section("5. Checked exceptions inside a lambda");
        List<String> raw = Arrays.asList("1", "", "oops", "4");
        for (String s : raw) {
            try {
                System.out.println("  parse('" + s + "') = " + unchecked(LambdasFunctionalInterfaces::parseStrict).apply(s));
            } catch (RuntimeException e) {
                String how = e.getCause() == null ? "thrown as-is (already unchecked)"
                        : "wrapping checked " + e.getCause().getClass().getSimpleName();
                System.out.println("  parse('" + s + "') failed -> " + e.getClass().getSimpleName() + " " + how);
            }
        }

        section("6. Method reference flavours");
        Supplier<String> staticRef = LambdasFunctionalInterfaces::hello;             // Class::staticMethod
        String prefix = "Hi ";
        Function<String, String> boundRef = prefix::concat;                          // instance::method (bound)
        Function<String, Integer> unboundRef = String::length;                       // Class::instanceMethod (unbound)
        Function<String, StringBuilder> ctorRef = StringBuilder::new;                // Class::new
        System.out.println("  " + staticRef.get() + " | " + boundRef.apply("Ravi") + " | "
                + unboundRef.apply("four") + " | " + ctorRef.apply("sb").reverse());
    }

    static String hello() { return "static-ref"; }
}

// EXERCISE: write a generic 'retry(Supplier<T>, int attempts)' helper that returns the first
// successful result and rethrows the last exception. Then make it accept a ThrowingSupplier.
