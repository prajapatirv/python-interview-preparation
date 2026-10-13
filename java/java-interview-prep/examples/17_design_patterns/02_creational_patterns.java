/*
 * 02 - Creational patterns, one runnable demo each: Singleton, Factory Method, Abstract Factory, Builder, Prototype
 *
 * Run:  java 02_creational_patterns.java
 *
 * Interview angle: "what is the singleton pattern and why is the lazy version unsafe?", "factory method vs abstract
 * factory", "builder vs telescoping constructors", "prototype and deep vs shallow copy".
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

class CreationalPatterns {

    // ---- Singleton: the lazy version with the classic race
    static final AtomicInteger UNSAFE_CREATED = new AtomicInteger();
    static class LazyUnsafe {
        private static LazyUnsafe instance;
        private LazyUnsafe() { UNSAFE_CREATED.incrementAndGet(); try { Thread.sleep(30); } catch (InterruptedException e) { } }
        static LazyUnsafe get() { if (instance == null) instance = new LazyUnsafe(); return instance; }          // check-then-act race
    }
    static final AtomicInteger SAFE_CREATED = new AtomicInteger();
    static class LazySynchronized {
        private static LazySynchronized instance;
        private LazySynchronized() { SAFE_CREATED.incrementAndGet(); try { Thread.sleep(30); } catch (InterruptedException e) { } }
        static synchronized LazySynchronized get() { if (instance == null) instance = new LazySynchronized(); return instance; }
    }
    static int hammer(Callable<Object> getter) throws Exception {
        int threads = 8;
        CountDownLatch go = new CountDownLatch(1);
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        Set<Object> seen = ConcurrentHashMap.newKeySet();
        for (int i = 0; i < threads; i++) pool.submit(() -> { go.await(); seen.add(getter.call()); return null; });
        go.countDown();
        pool.shutdown();
        pool.awaitTermination(5, TimeUnit.SECONDS);
        return seen.size();
    }

    // ---- Factory Method: subclass decides the product
    interface Transport { String deliver(String cargo); }
    static abstract class Logistics {
        abstract Transport createTransport();                                       // the factory method
        String plan(String cargo) { return createTransport().deliver(cargo); }      // creator uses the product via the interface
    }
    static class RoadLogistics extends Logistics { Transport createTransport() { return c -> "truck carries " + c; } }
    static class SeaLogistics extends Logistics { Transport createTransport() { return c -> "ship carries " + c; } }

    // ---- Abstract Factory: a family of matching products
    interface Button { String render(); }
    interface Checkbox { String render(); }
    interface UiFactory { Button button(); Checkbox checkbox(); }
    static class DarkUi implements UiFactory {
        public Button button() { return () -> "[dark button]"; }
        public Checkbox checkbox() { return () -> "[dark checkbox]"; }
    }
    static class LightUi implements UiFactory {
        public Button button() { return () -> "[light button]"; }
        public Checkbox checkbox() { return () -> "[light checkbox]"; }
    }

    // ---- Builder with a Director (the classic GoF shape)
    static final class Pizza {
        final String size; final List<String> toppings;
        private Pizza(Builder b) { size = b.size; toppings = Collections.unmodifiableList(new ArrayList<>(b.toppings)); }
        static class Builder {
            private String size = "medium"; private final List<String> toppings = new ArrayList<>();
            Builder size(String s) { size = s; return this; }
            Builder topping(String t) { toppings.add(t); return this; }
            Pizza build() { if (toppings.size() > 5) throw new IllegalStateException("too many toppings"); return new Pizza(this); }
        }
        @Override public String toString() { return size + " pizza " + toppings; }
    }
    static class PizzaDirector {                                                    // knows recipes, drives any builder
        Pizza margherita() { return new Pizza.Builder().size("large").topping("tomato").topping("mozzarella").build(); }
    }

    // ---- Prototype: copy instead of construct; shallow vs deep
    static class Doc implements Cloneable {
        String title; List<String> tags = new ArrayList<>();
        Doc(String t) { title = t; }
        Doc shallow() throws CloneNotSupportedException { return (Doc) super.clone(); }   // shares the tags list
        Doc deep() { Doc d = new Doc(title); d.tags = new ArrayList<>(tags); return d; }  // copy-constructor style, preferred
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
        section("1. Singleton: one instance per JVM/classloader, global access point");
        System.out.println("  lazy, unsynchronized : instances created by 8 racing threads = " + hammer(LazyUnsafe::get) + "  (expected 1; usually > 1)");
        System.out.println("  lazy, synchronized   : instances created by 8 racing threads = " + hammer(LazySynchronized::get) + "  (always 1)");
        System.out.println("  Use when: exactly one shared coordinator (config, registry). Avoid: as hidden global state. Spring: singleton scope.");

        section("2. Factory Method: let a subclass pick the concrete product");
        for (Logistics l : new Logistics[] {new RoadLogistics(), new SeaLogistics()}) System.out.println("  " + l.plan("crates"));
        System.out.println("  Use when: the creator should not know the concrete class. JDK: Calendar.getInstance, List.of, NumberFormat.getInstance.");

        section("3. Abstract Factory: a family of products that must match");
        for (UiFactory f : new UiFactory[] {new DarkUi(), new LightUi()}) System.out.println("  " + f.button().render() + " " + f.checkbox().render());
        System.out.println("  Factory Method = one product via inheritance; Abstract Factory = several related products via composition.");

        section("4. Builder: step-by-step construction with validation");
        System.out.println("  " + new PizzaDirector().margherita());
        try { Pizza.Builder b = new Pizza.Builder(); for (int i = 0; i < 6; i++) b.topping("t" + i); b.build(); }
        catch (IllegalStateException e) { System.out.println("  invalid combination rejected in build(): " + e.getMessage()); }
        System.out.println("  JDK/Spring: StringBuilder, HttpClient.newBuilder(), UriComponentsBuilder, HttpSecurity.");

        section("5. Prototype: clone an expensive or configured object");
        Doc original = new Doc("spec"); original.tags.add("v1");
        Doc s = original.shallow(), d = original.deep();
        original.tags.add("v2");
        System.out.println("  after mutating original.tags -> shallow copy sees " + s.tags + ", deep copy sees " + d.tags);
        System.out.println("  Prefer copy constructors / static copy factories over Cloneable; JDK: ArrayList(Collection), Object.clone.");
    }
}

// EXERCISE: make LazyUnsafe safe with the holder idiom, then run hammer() again and confirm the count is 1 without a synchronized method.
