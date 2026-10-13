/*
 * 05 - "What is Dependency Injection, how do you implement it, and which type when?" and
 *      "What is token-based / JWT authentication?" (both flagged very important)
 *
 * Run:  java 05_dependency_injection_and_token_auth.java
 *
 * Interview angle: DI = an object receives its collaborators instead of creating them;
 * constructor vs setter vs field injection and when to use each; why field injection hurts
 * tests; session vs token authentication; what a JWT is (header.payload.signature), what the
 * signature does and does not give you, expiry, tampering, the alg=none attack, revocation.
 * Everything is plain JDK so the mechanism is visible; Spring does the same wiring for you.
 */
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

class DependencyInjectionAndTokenAuth {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    // =====================================================================================
    // PART 1: Dependency injection
    // =====================================================================================
    interface PaymentGateway { String charge(int cents); }
    interface Notifier { void send(String msg); }

    static class RealGateway implements PaymentGateway {
        public String charge(int cents) { return "CHARGED:" + cents; }
    }
    static class RecordingNotifier implements Notifier {
        final List<String> sent = new ArrayList<>();
        public void send(String msg) { sent.add(msg); }
    }

    /** NO DI: the class builds its own collaborator. Cannot be tested without the real gateway. */
    static class OrderServiceHardWired {
        private final PaymentGateway gateway = new RealGateway();     // hidden, fixed dependency
        String checkout(int cents) { return gateway.charge(cents); }
    }

    /** CONSTRUCTOR injection: mandatory, final, visible, usable with plain 'new' in a test. */
    static class OrderServiceCtor {
        private final PaymentGateway gateway;
        private final Notifier notifier;
        OrderServiceCtor(PaymentGateway gateway, Notifier notifier) {
            this.gateway = Objects.requireNonNull(gateway, "gateway");    // fails at construction, not at first use
            this.notifier = Objects.requireNonNull(notifier, "notifier");
        }
        String checkout(int cents) { String r = gateway.charge(cents); notifier.send("paid " + cents); return r; }
    }

    /** SETTER injection: the object exists in a half-built state until the setter is called. */
    static class OrderServiceSetter {
        private PaymentGateway gateway;
        private Notifier notifier = msg -> { };                           // optional dependency with a safe default
        void setGateway(PaymentGateway g) { this.gateway = g; }
        void setNotifier(Notifier n) { this.notifier = n; }
        String checkout(int cents) { String r = gateway.charge(cents); notifier.send("paid " + cents); return r; }
    }

    /** FIELD injection (what @Autowired on a field does): a test cannot supply the dependency
     *  through the constructor or a setter, so it needs reflection or a running container. */
    static class OrderServiceField {
        private PaymentGateway gateway;                                    // imagine @Autowired here
        String checkout(int cents) { return gateway.charge(cents); }
    }

    /** A 12-line container: register providers, resolve by type, detect circular dependencies. */
    static class MiniContainer {
        private final Map<Class<?>, java.util.function.Function<MiniContainer, Object>> providers = new HashMap<>();
        private final Map<Class<?>, Object> singletons = new HashMap<>();
        private final Deque<Class<?>> resolving = new ArrayDeque<>();
        private final Set<Class<?>> prototypes = new HashSet<>();
        <T> void registerPrototype(Class<T> type, java.util.function.Function<MiniContainer, T> p) {
            register(type, p);
            prototypes.add(type);                                   // new instance on EVERY get()
        }
        <T> void register(Class<T> type, java.util.function.Function<MiniContainer, T> p) {
            providers.put(type, c -> p.apply(c));
        }
        @SuppressWarnings("unchecked")
        <T> T get(Class<T> type) {
            Object cached = singletons.get(type);
            if (cached != null) return (T) cached;
            if (resolving.contains(type)) throw new IllegalStateException("Circular dependency: " + path(type));
            resolving.push(type);
            try {
                var p = providers.get(type);
                if (p == null) throw new NoSuchElementException("No bean of type " + type.getSimpleName());
                Object o = p.apply(this);
                if (!prototypes.contains(type)) singletons.put(type, o);
                return (T) o;
            } finally { resolving.pop(); }
        }
        private String path(Class<?> again) {
            List<String> names = new ArrayList<>();
            for (Class<?> c : resolving) names.add(c.getSimpleName());
            Collections.reverse(names);
            names.add(again.getSimpleName());
            return String.join(" -> ", names);
        }
    }
    /** Stateless: safe as a singleton. All data arrives as arguments and leaves as the result. */
    static class PriceCalculator { int withTax(int cents) { return cents + cents / 5; } }
    /** Stateful: a per-request field on a shared singleton is a data leak between users. */
    static class RequestContextHolder {
        String currentUser;
        void begin(String user) { currentUser = user; }
        String whoAmI() { return currentUser; }
    }
    static class A { final B b; A(B b) { this.b = b; } }
    static class B { final A a; B(A a) { this.a = a; } }

    // --- ways OUT of a cycle -----------------------------------------------------------
    /** Setter-injected pair: can be created with no-arg constructors, wired afterwards. */
    static class SetterA { SetterB b; void setB(SetterB b) { this.b = b; } }
    static class SetterB { SetterA a; void setA(SetterA a) { this.a = a; } }
    /** Constructor cycle broken with a lazy provider (what @Lazy / ObjectProvider<T> do). */
    static class LazyB {
        private final java.util.function.Supplier<LazyA> a;            // resolved at first use, not at construction
        LazyB(java.util.function.Supplier<LazyA> a) { this.a = a; }
        String ping() { return "B->" + a.get().name(); }
    }
    static class LazyA {
        final LazyB b;
        LazyA(LazyB b) { this.b = b; }
        String name() { return "A"; }
    }
    /**
     * What Spring does for singleton setter/field cycles: create the raw object, publish an EARLY
     * reference in a cache BEFORE populating its properties, so the other bean can grab the
     * half-built instance (Spring's three-level singleton cache). Constructor cycles cannot do
     * this because there is no object to publish until the constructor returns.
     */
    static class EarlyRefResolver {
        final Map<String, Object> early = new HashMap<>();
        final Map<String, Object> done = new HashMap<>();
        final List<String> log = new ArrayList<>();
        Object getA() {
            if (done.containsKey("a")) return done.get("a");
            if (early.containsKey("a")) { log.add("early ref to a"); return early.get("a"); }
            SetterA a = new SetterA();
            early.put("a", a);                                         // publish before populate
            a.setB((SetterB) getB());
            early.remove("a"); done.put("a", a);
            return a;
        }
        Object getB() {
            if (done.containsKey("b")) return done.get("b");
            SetterB b = new SetterB();
            early.put("b", b);
            b.setA((SetterA) getA());                                  // finds a's early reference
            early.remove("b"); done.put("b", b);
            return b;
        }
    }

    // =====================================================================================
    // PART 2: Token-based authentication and JWT
    // =====================================================================================
    static final byte[] SECRET = "demo-secret-32-bytes-minimum-0123456789".getBytes(StandardCharsets.UTF_8);
    static String b64(byte[] b) { return Base64.getUrlEncoder().withoutPadding().encodeToString(b); }
    static byte[] unb64(String s) { return Base64.getUrlDecoder().decode(s); }

    static byte[] hmac(String data) throws Exception {
        Mac m = Mac.getInstance("HmacSHA256");
        m.init(new SecretKeySpec(SECRET, "HmacSHA256"));
        return m.doFinal(data.getBytes(StandardCharsets.UTF_8));
    }
    static String issue(String sub, String role, long expEpochSec) throws Exception {
        String h = b64("{\"alg\":\"HS256\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));
        String p = b64(("{\"sub\":\"" + sub + "\",\"role\":\"" + role + "\",\"exp\":" + expEpochSec + "}")
                .getBytes(StandardCharsets.UTF_8));
        return h + "." + p + "." + b64(hmac(h + "." + p));
    }
    /** Verify order matters: algorithm allow-list, signature (constant time), THEN expiry, THEN trust claims. */
    static Map<String, String> verify(String token, long nowSec) throws Exception {
        String[] parts = token.split("\\.", -1);   // -1 keeps the empty signature of alg=none tokens
        if (parts.length != 3) throw new SecurityException("malformed token");
        String header = new String(unb64(parts[0]), StandardCharsets.UTF_8);
        if (!header.contains("\"alg\":\"HS256\"")) throw new SecurityException("algorithm not allowed");   // blocks alg=none
        byte[] expected = hmac(parts[0] + "." + parts[1]);
        if (!MessageDigest.isEqual(expected, unb64(parts[2]))) throw new SecurityException("bad signature");
        Map<String, String> claims = new LinkedHashMap<>();
        String json = new String(unb64(parts[1]), StandardCharsets.UTF_8).replaceAll("[{}\"]", "");
        for (String kv : json.split(",")) { String[] x = kv.split(":", 2); claims.put(x[0], x[1]); }
        if (Long.parseLong(claims.get("exp")) <= nowSec) throw new SecurityException("token expired");
        return claims;
    }
    static String outcome(String token, long now) {
        try { return "OK " + verify(token, now); } catch (SecurityException e) { return "REJECT " + e.getMessage(); }
        catch (Exception e) { return "REJECT " + e.getClass().getSimpleName(); }
    }

    /** Session auth: the SERVER remembers; the client holds an opaque id. Revocation is trivial. */
    static class SessionServer {
        final Map<String, String> sessions = new HashMap<>();             // sessionId -> user (server memory)
        String login(String user) { String id = UUID.randomUUID().toString(); sessions.put(id, user); return id; }
        String whoAmI(String id) { return sessions.get(id); }
        void logout(String id) { sessions.remove(id); }
    }

    static final LazyA[] la = new LazyA[1];

    // --- BeanFactory vs ApplicationContext, reduced to the behaviours that differ ----------
    /** BeanFactory: the basic container. Beans are created lazily, on the first getBean(). */
    static class SimpleBeanFactory {
        final Map<String, java.util.function.Supplier<Object>> defs = new LinkedHashMap<>();
        final Map<String, Object> cache = new HashMap<>();
        final List<String> created = new ArrayList<>();
        void define(String name, java.util.function.Supplier<Object> s) { defs.put(name, s); }
        Object getBean(String name) {
            Object hit = cache.get(name);
            if (hit != null) return hit;
            if (!defs.containsKey(name)) throw new NoSuchElementException("No bean named " + name);
            Object bean = defs.get(name).get();                       // may throw: nothing is cached or logged then
            created.add(name);
            cache.put(name, bean);
            return bean;
        }
    }
    /** ApplicationContext: a BeanFactory PLUS eager singleton creation at refresh(), events, profiles. */
    static class SimpleApplicationContext extends SimpleBeanFactory {
        final Set<String> activeProfiles = new HashSet<>();
        final List<java.util.function.Consumer<String>> listeners = new ArrayList<>();
        final Map<String, String> profileOf = new HashMap<>();
        void define(String name, String profile, java.util.function.Supplier<Object> s) {
            define(name, s);
            if (profile != null) profileOf.put(name, profile);
        }
        void addListener(java.util.function.Consumer<String> l) { listeners.add(l); }
        void publishEvent(String event) { listeners.forEach(l -> l.accept(event)); }
        void refresh() {                                              // eager: fail-fast at startup
            for (String n : defs.keySet()) {
                String p = profileOf.get(n);
                if (p == null || activeProfiles.contains(p)) getBean(n);
            }
            publishEvent("ContextRefreshedEvent");
        }
    }

    public static void main(String[] args) throws Exception {
        section("1. DI: constructor injection makes the class testable with plain new");
        RecordingNotifier spy = new RecordingNotifier();
        OrderServiceCtor svc = new OrderServiceCtor(cents -> "FAKE:" + cents, spy);   // lambda = test double
        check("constructor-injected fake gateway", "FAKE:500", svc.checkout(500));
        check("collaborator interaction observed", "[paid 500]", spy.sent.toString());
        check("hard-wired class can only ever use the real gateway", "CHARGED:500", new OrderServiceHardWired().checkout(500));
        try { new OrderServiceCtor(null, spy); check("must throw", "threw", "did not"); }
        catch (NullPointerException e) { check("constructor fails fast on a missing dependency", "gateway", e.getMessage()); }

        section("2. DI: the failure modes of setter and field injection");
        OrderServiceSetter half = new OrderServiceSetter();           // legal to construct, illegal to use
        try { half.checkout(1); check("must throw", "threw", "did not"); }
        catch (NullPointerException e) { check("setter injection: half-built object fails at first USE", true, true); }
        half.setGateway(cents -> "FAKE:" + cents);
        check("setter injection works once wired (optional notifier has a default)", "FAKE:7", half.checkout(7));
        OrderServiceField field = new OrderServiceField();
        try { field.checkout(1); check("must throw", "threw", "did not"); }
        catch (NullPointerException e) { check("field injection: no way to supply the dependency without reflection", true, true); }
        var f = OrderServiceField.class.getDeclaredField("gateway");
        f.setAccessible(true);                                           // this is what a test must do
        f.set(field, (PaymentGateway) cents -> "REFLECTED:" + cents);
        check("field injection needs reflection (or a Spring test context)", "REFLECTED:9", field.checkout(9));

        section("3. DI: a container resolves the graph and spots cycles");
        MiniContainer c = new MiniContainer();
        c.register(PaymentGateway.class, k -> new RealGateway());
        c.register(Notifier.class, k -> new RecordingNotifier());
        c.register(OrderServiceCtor.class, k -> new OrderServiceCtor(k.get(PaymentGateway.class), k.get(Notifier.class)));
        check("container wires the graph", "CHARGED:100", c.get(OrderServiceCtor.class).checkout(100));
        check("singleton scope: same instance", true, c.get(OrderServiceCtor.class) == c.get(OrderServiceCtor.class));
        c.register(A.class, k -> new A(k.get(B.class)));
        c.register(B.class, k -> new B(k.get(A.class)));
        try { c.get(A.class); check("must throw", "threw", "did not"); }
        catch (IllegalStateException e) { check("constructor cycle is detected at startup", "Circular dependency: A -> B -> A", e.getMessage()); }

        section("3b. Singleton scope: shared instance, so it must be stateless");
        c.register(PriceCalculator.class, k -> new PriceCalculator());
        check("singleton scope returns ONE shared instance", true,
                c.get(PriceCalculator.class) == c.get(PriceCalculator.class));
        c.registerPrototype(RequestContextHolder.class, k -> new RequestContextHolder());
        check("prototype scope returns a NEW instance each time", false,
                c.get(RequestContextHolder.class) == c.get(RequestContextHolder.class));
        RequestContextHolder shared = new RequestContextHolder();          // what a singleton would be
        shared.begin("alice");                                             // request A starts
        shared.begin("bob");                                               // request B starts before A finishes
        check("stateful singleton: request A now sees request B's user (leak)", "bob", shared.whoAmI());
        RequestContextHolder reqA = c.get(RequestContextHolder.class), reqB = c.get(RequestContextHolder.class);
        reqA.begin("alice"); reqB.begin("bob");
        check("per-request (prototype/request-scope) instances stay isolated", "alice/bob", reqA.whoAmI() + "/" + reqB.whoAmI());

        section("3c. Circular dependencies: what Spring does and the ways out");
        EarlyRefResolver er = new EarlyRefResolver();
        SetterA sa = (SetterA) er.getA();
        check("setter cycle resolved through an early (half-built) reference", true, sa.b.a == sa);
        check("the early reference was used exactly once", "[early ref to a]", er.log.toString());
        LazyB lb = new LazyB(() -> la[0]);                              // provider defers the lookup
        la[0] = new LazyA(lb);
        check("constructor cycle broken with a lazy provider", "B->A", lb.ping());
        System.out.println("  note the real fix is the design: extract the shared part (A -> C <- B) so the graph is a DAG");

        section("3d. BeanFactory versus ApplicationContext");
        SimpleBeanFactory bf = new SimpleBeanFactory();
        bf.define("orderService", OrderServiceHardWired::new);
        bf.define("broken", () -> { throw new IllegalStateException("bad wiring"); });
        check("BeanFactory creates nothing until asked (lazy)", "[]", bf.created.toString());
        bf.getBean("orderService");
        check("BeanFactory created only the requested bean", "[orderService]", bf.created.toString());
        SimpleApplicationContext ctx = new SimpleApplicationContext();
        ctx.activeProfiles.add("prod");
        List<String> events = new ArrayList<>();
        ctx.addListener(events::add);
        ctx.define("orderService", null, OrderServiceHardWired::new);
        ctx.define("prodDataSource", "prod", () -> "pool");
        ctx.define("devDataSource", "dev", () -> "h2");
        ctx.refresh();
        check("ApplicationContext pre-instantiates singletons at refresh (profile-aware)",
                "[orderService, prodDataSource]", ctx.created.toString());
        check("ApplicationContext publishes lifecycle events", "[ContextRefreshedEvent]", events.toString());
        SimpleApplicationContext bad = new SimpleApplicationContext();
        bad.define("broken", null, () -> { throw new IllegalStateException("bad wiring"); });
        try { bad.refresh(); check("must throw", "threw", "did not"); }
        catch (IllegalStateException e) {
            check("ApplicationContext fails FAST at refresh; a BeanFactory would fail at first use", "bad wiring", e.getMessage());
        }

        section("4. Token auth: session versus token");
        SessionServer s = new SessionServer();
        String sid = s.login("ravi");
        check("session: server looks the id up", "ravi", s.whoAmI(sid));
        s.logout(sid);
        check("session: logout revokes immediately", null, s.whoAmI(sid));
        long now = 1_700_000_000L;
        String jwt = issue("ravi", "ADMIN", now + 900);
        check("JWT has three dot-separated parts", 3, jwt.split("\\.").length);
        check("valid JWT verifies with NO server-side session lookup",
                "OK {sub=ravi, role=ADMIN, exp=" + (now + 900) + "}", outcome(jwt, now));

        section("5. JWT: what the signature does and does not protect");
        check("expired token is rejected", "REJECT token expired", outcome(jwt, now + 901));
        String[] p = jwt.split("\\.");
        String forgedPayload = b64(("{\"sub\":\"ravi\",\"role\":\"SUPERUSER\",\"exp\":" + (now + 900) + "}")
                .getBytes(StandardCharsets.UTF_8));
        check("tampered payload fails the signature", "REJECT bad signature", outcome(p[0] + "." + forgedPayload + "." + p[2], now));
        String noneHeader = b64("{\"alg\":\"none\",\"typ\":\"JWT\"}".getBytes(StandardCharsets.UTF_8));
        check("alg=none attack is blocked by an algorithm allow-list", "REJECT algorithm not allowed",
                outcome(noneHeader + "." + p[1] + ".", now));
        check("payload is only base64, NOT encrypted: anyone can read it", "ADMIN",
                new String(unb64(p[1]), StandardCharsets.UTF_8).contains("ADMIN") ? "ADMIN" : "hidden");
        check("garbage input is rejected, not a 500", "REJECT malformed token", outcome("abc", now));

        section("6. The revocation trade-off, in one line each");
        System.out.println("  session : revoke = delete one map entry; cost = shared session store when you scale out");
        System.out.println("  JWT     : any server verifies offline; cost = valid until exp, so keep it short (5-15 min)");
        System.out.println("            + refresh token (rotated, stored server-side) + a deny-list only for emergencies");

        System.out.println("\nAll " + checks + " checks passed.");
    }
}
