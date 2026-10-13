/*
 * 01 - The design patterns that still matter in Java, and SOLID with concrete violations
 *
 * Run:  java 01_patterns_and_solid_in_modern_java.java
 *
 * Interview angle: "which patterns have you used and where in Spring?", "thread-safe singleton",
 * "builder vs telescoping constructors", "strategy with lambdas", "SOLID with an example",
 * "how many ways to write a singleton and how is it broken?", "pattern for closing connections?",
 * "is Spring MVC a design pattern?", "design vs architectural pattern", "how many GoF patterns / types?".
 */
import java.lang.reflect.*;
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

    // ---- Singleton: how it gets broken (reflection, serialization) and the fixes
    static class NaiveSingleton implements java.io.Serializable {
        static final NaiveSingleton INSTANCE = new NaiveSingleton();               // eager: thread-safe, built at class load
        private NaiveSingleton() { }
    }
    static class HardenedSingleton implements java.io.Serializable {
        private static final HardenedSingleton INSTANCE = new HardenedSingleton();
        private HardenedSingleton() { if (INSTANCE != null) throw new IllegalStateException("already created"); }
        static HardenedSingleton get() { return INSTANCE; }
        private Object readResolve() { return INSTANCE; }                          // deserialization returns the SAME object
    }
    @SuppressWarnings("unchecked")
    static <T> T roundTrip(T o) throws Exception {
        java.io.ByteArrayOutputStream bos = new java.io.ByteArrayOutputStream();
        try (java.io.ObjectOutputStream out = new java.io.ObjectOutputStream(bos)) { out.writeObject(o); }
        try (java.io.ObjectInputStream in = new java.io.ObjectInputStream(new java.io.ByteArrayInputStream(bos.toByteArray()))) {
            return (T) in.readObject();
        }
    }
    static String reflect(Class<?> c) {
        try {
            Constructor<?> k = c.isEnum() ? c.getDeclaredConstructor(String.class, int.class) : c.getDeclaredConstructor();
            k.setAccessible(true);
            return "second instance created = " + (k.newInstance(c.isEnum() ? new Object[] {"X", 1} : new Object[0]) != null);
        } catch (InvocationTargetException e) {
            return "blocked -> " + e.getCause().getClass().getSimpleName() + ": " + e.getCause().getMessage();
        } catch (Exception e) {
            return "blocked -> " + e.getClass().getSimpleName() + ": " + e.getMessage();
        }
    }

    // ---- Boilerplate (open/close/handle errors): Template Method + callback, or try-with-resources
    static class FakeConnection implements AutoCloseable {
        static int open;
        FakeConnection() { open++; }
        String query(String q) { if (q.contains("boom")) throw new IllegalStateException("db error"); return "rows(" + q + ")"; }
        @Override public void close() { open--; }
    }
    interface ConnectionCallback<T> { T doWith(FakeConnection c); }
    static <T> T withConnection(ConnectionCallback<T> cb) {                         // the template owns open/close; callers supply the work
        try (FakeConnection c = new FakeConnection()) { return cb.doWith(c); }
    }

    // ---- Spring MVC in miniature: Front Controller + HandlerMapping (Strategy) + interceptors (Chain) + ViewResolver
    static class DispatcherServletLite {
        final Map<String, Function<String, String>> handlerMapping = new LinkedHashMap<>();
        final List<UnaryOperator<String>> interceptors = new ArrayList<>();
        final Function<String, String> viewResolver = model -> "<html>" + model + "</html>";
        String service(String path, String req) {
            String r = req;
            for (UnaryOperator<String> i : interceptors) r = i.apply(r);              // preHandle chain
            Function<String, String> controller = handlerMapping.get(path);
            if (controller == null) return "404";
            return viewResolver.apply(controller.apply(r));                           // controller -> model -> view
        }
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    static String tryAdd(List l) {
        try { l.add(null); return "added"; } catch (UnsupportedOperationException e) { return "UnsupportedOperationException"; }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {
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

        section("10. Ways to write a singleton, and how each is broken");
        System.out.println("  eager static final | lazy unsynchronized (NOT thread-safe) | synchronized getInstance (slow) | DCL + volatile | holder | enum | Spring scope");
        System.out.println("  plain class, reflection : " + reflect(NaiveSingleton.class));
        System.out.println("  guarded ctor, reflection: " + reflect(HardenedSingleton.class));
        System.out.println("  enum, reflection        : " + reflect(EnumSingleton.class));
        System.out.println("  serialization, no readResolve : same instance = " + (roundTrip(NaiveSingleton.INSTANCE) == NaiveSingleton.INSTANCE));
        System.out.println("  serialization, readResolve    : same instance = " + (roundTrip(HardenedSingleton.get()) == HardenedSingleton.get()));
        System.out.println("  Also: clone() (do not implement Cloneable) and multiple classloaders give one instance PER loader.");

        section("11. Boilerplate like closing connections: Template Method / execute-around");
        System.out.println("  " + withConnection(c -> c.query("select 1")) + "  open after = " + FakeConnection.open);
        try { withConnection(c -> c.query("boom")); } catch (IllegalStateException e) { System.out.println("  failed with '" + e.getMessage() + "'; open after = " + FakeConnection.open + " (still closed)"); }
        System.out.println("  Spring: JdbcTemplate, RestTemplate, TransactionTemplate, KafkaTemplate. Plain Java: try-with-resources (AutoCloseable).");

        section("12. Design pattern vs architectural pattern; Spring MVC");
        System.out.println("  GoF 23 = 5 creational + 7 structural + 11 behavioural (+ enterprise/J2EE and concurrency patterns outside GoF)");
        System.out.println("  design pattern: class/object level inside one component. architectural pattern: structure of the whole system (layered, hexagonal, MVC, event-driven, microservices).");
        DispatcherServletLite ds = new DispatcherServletLite();
        ds.interceptors.add(r -> r.trim());
        ds.handlerMapping.put("/orders", r -> "orders for " + r);
        System.out.println("  GET /orders -> " + ds.service("/orders", "  alice ") + " | GET /nope -> " + ds.service("/nope", "x"));
        System.out.println("  Spring MVC = MVC (architectural) realised with Front Controller (DispatcherServlet), Strategy (HandlerMapping/ViewResolver), Chain (interceptors).");

        section("13. Patterns hiding in the JDK (verifiable)");
        Integer a = 127, b = 127, c = 128, d = 128;
        System.out.println("  Flyweight : Integer 127 == 127 is " + (a == b) + ", 128 == 128 is " + (c == d) + "  (cache covers -128..127)");
        List<Integer> src = new ArrayList<>(Arrays.asList(1, 2));
        List<Integer> ro = Collections.unmodifiableList(src);
        src.add(3);
        System.out.println("  Decorator : unmodifiableList wraps the same list, sees " + ro + "; add() -> " + tryAdd(ro));
        List<String> fixed = Arrays.asList("x", "y");
        System.out.println("  Adapter   : Arrays.asList is an array behind the List interface; add() -> " + tryAdd(fixed));
        System.out.println("  Singleton : Runtime.getRuntime() same instance = " + (Runtime.getRuntime() == Runtime.getRuntime()));
        System.out.println("  Strategy  : Comparator " + Stream.of("pear", "fig", "apple").sorted(Comparator.comparingInt(String::length)).collect(Collectors.toList()));
    }
}

// EXERCISE (a): replace the if/else chain in BadReportService via a Map, then explain the Liskov rule with a Square/Rectangle example.
// EXERCISE (b): add a lazy, unsynchronized singleton, break it with two threads and a sleep in the constructor, then fix it with the holder idiom.
