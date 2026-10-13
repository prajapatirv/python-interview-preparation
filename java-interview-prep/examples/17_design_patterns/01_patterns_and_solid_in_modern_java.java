/*
 * 01 - The design patterns that still matter in Java, and SOLID with concrete violations
 *
 * Run:  java 01_patterns_and_solid_in_modern_java.java
 *
 * Interview angle: "which patterns have you used and where in Spring?", "thread-safe singleton",
 * "builder vs telescoping constructors", "strategy with lambdas", "SOLID with an example".
 */
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

class PatternsAndSolidInModernJava {

    // ---- Singleton: three safe ways
    enum EnumSingleton { INSTANCE; int hits; int next() { return ++hits; } }       // serialization- and reflection-safe

    static class HolderSingleton {                                                  // lazy + thread-safe via class loading
        private HolderSingleton() { System.out.println("    HolderSingleton created"); }
        private static class Holder { static final HolderSingleton I = new HolderSingleton(); }
        static HolderSingleton get() { return Holder.I; }
    }

    static class DclSingleton {                                                     // double-checked locking REQUIRES volatile
        private static volatile DclSingleton instance;
        private DclSingleton() { }
        static DclSingleton get() {
            if (instance == null) { synchronized (DclSingleton.class) { if (instance == null) instance = new DclSingleton(); } }
            return instance;
        }
    }

    // ---- Builder
    static final class HttpCall {
        final String url, method; final Map<String, String> headers; final int timeoutMs;
        private HttpCall(Builder b) { url = b.url; method = b.method; headers = Collections.unmodifiableMap(new LinkedHashMap<>(b.headers)); timeoutMs = b.timeoutMs; }
        static Builder to(String url) { return new Builder(url); }
        static final class Builder {
            private final String url; private String method = "GET"; private final Map<String, String> headers = new LinkedHashMap<>(); private int timeoutMs = 3_000;
            private Builder(String url) { this.url = Objects.requireNonNull(url); }
            Builder method(String m) { method = m; return this; }
            Builder header(String k, String v) { headers.put(k, v); return this; }
            Builder timeoutMs(int t) { if (t <= 0) throw new IllegalArgumentException("timeout"); timeoutMs = t; return this; }
            HttpCall build() { return new HttpCall(this); }
        }
        @Override public String toString() { return method + " " + url + " " + headers + " timeout=" + timeoutMs; }
    }

    // ---- Strategy via lambdas (no class per algorithm)
    interface DiscountPolicy { int apply(int cents); }
    static final Map<String, DiscountPolicy> POLICIES = new LinkedHashMap<>();
    static { POLICIES.put("none", c -> c); POLICIES.put("tenPercent", c -> c * 90 / 100); POLICIES.put("flat5", c -> Math.max(0, c - 500)); }

    // ---- Factory
    interface Notifier { String send(String msg); }
    static Notifier notifierFor(String channel) {
        switch (channel) {
            case "email": return m -> "EMAIL: " + m;
            case "sms":   return m -> "SMS: " + m;
            default: throw new IllegalArgumentException("unknown channel " + channel);
        }
    }

    // ---- Decorator
    interface Repo { String load(String id); }
    static Repo cachingDecorator(Repo inner, Map<String, String> cache, int[] hits) {
        return id -> cache.computeIfAbsent(id, k -> { hits[0]++; return inner.load(k); });
    }

    // ---- Observer (domain events)
    static class EventBus {
        private final Map<Class<?>, List<Consumer<Object>>> handlers = new HashMap<>();
        <T> void on(Class<T> type, Consumer<T> h) { handlers.computeIfAbsent(type, k -> new ArrayList<>()).add(o -> h.accept(type.cast(o))); }
        void publish(Object event) { handlers.getOrDefault(event.getClass(), Collections.emptyList()).forEach(h -> h.accept(event)); }
    }
    static class OrderPlaced { final String id; OrderPlaced(String id) { this.id = id; } }

    // ---- Template method
    static abstract class ImportJob {
        final List<String> run(List<String> raw) { return raw.stream().filter(this::valid).map(this::transform).collect(Collectors.toList()); }
        protected abstract boolean valid(String line);
        protected abstract String transform(String line);
    }

    // ---- SOLID: a violation and its fix
    static class BadReportService {                                                  // SRP + OCP violations
        String render(String type, List<Integer> data) {
            if (type.equals("csv")) return data.stream().map(String::valueOf).collect(Collectors.joining(","));
            if (type.equals("json")) return data.toString();
            throw new IllegalArgumentException(type);                                // every new format edits this class
        }
    }
    interface Renderer { String render(List<Integer> data); }
    static class GoodReportService {                                                 // open for extension, closed for modification; DIP
        private final Map<String, Renderer> renderers;
        GoodReportService(Map<String, Renderer> r) { renderers = r; }
        String render(String type, List<Integer> data) {
            Renderer r = renderers.get(type);
            if (r == null) throw new IllegalArgumentException(type);
            return r.render(data);
        }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        section("1. Singleton (and why Spring beans are usually enough)");
        System.out.println("  enum: " + EnumSingleton.INSTANCE.next() + ", " + EnumSingleton.INSTANCE.next());
        System.out.println("  holder: same instance twice = " + (HolderSingleton.get() == HolderSingleton.get()));
        System.out.println("  DCL   : same instance = " + (DclSingleton.get() == DclSingleton.get()) + "  (without volatile another thread can see a half-built object)");
        System.out.println("  In Spring: singleton SCOPE, injected. Avoid static singletons - they hide dependencies and block testing.");

        section("2. Builder: readable, validated, immutable construction");
        System.out.println("  " + HttpCall.to("https://api.example.com/orders").method("POST").header("Idempotency-Key", "k1").timeoutMs(1_500).build());
        System.out.println("  Records + compact constructors cover simple cases; Lombok @Builder is common in Spring codebases.");

        section("3. Strategy with lambdas / Map dispatch");
        POLICIES.forEach((name, p) -> System.out.println("  " + name + " on $20.00 -> " + p.apply(2_000) + " cents"));

        section("4. Factory");
        System.out.println("  " + notifierFor("email").send("hi") + " | " + notifierFor("sms").send("hi"));
        System.out.println("  Spring does this with Map<String, Notifier> injection (bean name -> implementation).");

        section("5. Decorator (Spring AOP / @Cacheable are decorators)");
        int[] hits = {0};
        Repo cached = cachingDecorator(id -> "row-" + id, new HashMap<>(), hits);
        cached.load("1"); cached.load("1"); cached.load("2");
        System.out.println("  3 loads, underlying repo hit " + hits[0] + " times");

        section("6. Observer / domain events");
        EventBus bus = new EventBus();
        bus.on(OrderPlaced.class, e -> System.out.println("  inventory reserves for " + e.id));
        bus.on(OrderPlaced.class, e -> System.out.println("  email confirmation for " + e.id));
        bus.publish(new OrderPlaced("o-7"));
        System.out.println("  Spring: ApplicationEventPublisher + @EventListener / @TransactionalEventListener(AFTER_COMMIT).");

        section("7. Template method");
        ImportJob job = new ImportJob() {
            protected boolean valid(String l) { return !l.isBlank() && !l.startsWith("#"); }
            protected String transform(String l) { return l.trim().toUpperCase(); }
        };
        System.out.println("  " + job.run(Arrays.asList("# header", " a ", "", "b")) + "   (Spring: JdbcTemplate, RestTemplate, AbstractRoutingDataSource)");

        section("8. SOLID: adding a format");
        Map<String, Renderer> map = new HashMap<>();
        map.put("csv", d -> d.stream().map(String::valueOf).collect(Collectors.joining(",")));
        map.put("json", Object::toString);
        map.put("xml", d -> d.stream().map(i -> "<i>" + i + "</i>").collect(Collectors.joining()));   // NEW: no edit to GoodReportService
        System.out.println("  bad  csv: " + new BadReportService().render("csv", Arrays.asList(1, 2)));
        System.out.println("  good xml: " + new GoodReportService(map).render("xml", Arrays.asList(1, 2)));
        System.out.println("  S single responsibility | O open/closed | L Liskov (subtypes honour the contract) | I small interfaces | D depend on abstractions");

        section("9. Patterns you will see named in Spring");
        System.out.println("  Singleton (bean scope), Factory (BeanFactory), Proxy (AOP/@Transactional), Template (JdbcTemplate),");
        System.out.println("  Observer (events), Strategy (AuthenticationProvider, HandlerMapping), Chain of Responsibility (filter chain), Builder (HttpSecurity).");
    }
}

// EXERCISE: replace the if/else chain in BadReportService via a Map, then explain the Liskov rule with a Square/Rectangle example.
