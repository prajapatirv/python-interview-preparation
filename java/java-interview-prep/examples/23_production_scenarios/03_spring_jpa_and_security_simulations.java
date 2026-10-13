/*
 * 03 - Production scenarios: Spring / JPA / JWT / Kubernetes probe behaviour, simulated
 *
 * Run:  java 03_spring_jpa_and_security_simulations.java
 *
 * Interview angle: (Q3) @Transactional method swallows the exception and still commits.
 * (Q4) checked exception does not roll back. (Q8) JWT still works after logout.
 * (Q9) liveness probe kills a slow-starting app. (Q15) @Value is null in the constructor.
 * (Q18) saveAll of 10,000 entities = 10,000 INSERTs. (Q19) LazyInitializationException after
 * turning off open-in-view. Spring, Hibernate and Kubernetes are modelled with the same rules
 * the real ones use, so the failure mode is observable without them.
 */
import java.lang.annotation.*;
import java.lang.reflect.Field;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.concurrent.Callable;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

class SpringJpaAndSecuritySimulations {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    // ------------------------------------------------------------ Q3 / Q4: the transaction proxy
    static class FakeDb {
        final List<String> committed = new ArrayList<>();
        final List<String> pending = new ArrayList<>();
        void insert(String row) { pending.add(row); }
    }

    static class TxStatus { boolean rollbackOnly; }
    static final ThreadLocal<TxStatus> CURRENT = new ThreadLocal<>();

    /** What the @Transactional proxy does: it only sees what the method THROWS or RETURNS. */
    static class TransactionProxy {
        final FakeDb db;
        TransactionProxy(FakeDb db) { this.db = db; }

        <T> T invoke(Class<? extends Throwable>[] rollbackFor, Callable<T> method) throws Exception {
            db.pending.clear();
            TxStatus status = new TxStatus();
            CURRENT.set(status);
            try {
                T result = method.call();
                if (status.rollbackOnly) { db.pending.clear(); return result; }   // setRollbackOnly()
                db.committed.addAll(db.pending);                                     // normal return -> COMMIT
                return result;
            } catch (Throwable t) {
                boolean rollback = t instanceof RuntimeException || t instanceof Error;   // default rule
                for (Class<? extends Throwable> c : rollbackFor) if (c.isInstance(t)) rollback = true;
                if (rollback) db.pending.clear(); else db.committed.addAll(db.pending);
                if (t instanceof Exception e) throw e;
                throw (Error) t;
            } finally {
                CURRENT.remove();
            }
        }
    }

    static class PaymentFailedException extends Exception { PaymentFailedException(String m) { super(m); } }

    @SuppressWarnings("unchecked")
    static final Class<? extends Throwable>[] NONE = new Class[0];
    @SuppressWarnings("unchecked")
    static final Class<? extends Throwable>[] ANY_EXCEPTION = new Class[] { Exception.class };

    static void q3q4() throws Exception {
        section("Q3/Q4. swallowed exception commits; checked exception does not roll back");
        FakeDb db = new FakeDb();
        TransactionProxy tx = new TransactionProxy(db);

        // Q3: method catches and logs
        tx.invoke(NONE, () -> {
            db.insert("order#1");
            try { db.insert("payment#1"); throw new IllegalStateException("gateway down"); }
            catch (IllegalStateException e) { System.out.println("    log.error(\"payment failed\", e)  <- swallowed"); }
            return null;
        });
        check("Q3 swallowed exception: proxy saw a normal return, half-finished writes COMMITTED",
                List.of("order#1", "payment#1"), new ArrayList<>(db.committed));

        // Q3 fix A: rethrow
        db.committed.clear();
        try {
            tx.invoke(NONE, () -> {
                db.insert("order#2");
                try { throw new IllegalStateException("gateway down"); }
                catch (IllegalStateException e) { throw e; }
            });
        } catch (IllegalStateException expected) { /* surfaces to caller */ }
        check("Q3 fix A (rethrow): rolled back", List.of(), new ArrayList<>(db.committed));

        // Q3 fix B: catch, but mark the transaction rollback-only
        tx.invoke(NONE, () -> {
            db.insert("order#3");
            try { throw new IllegalStateException("gateway down"); }
            catch (IllegalStateException e) { CURRENT.get().rollbackOnly = true; }   // setRollbackOnly()
            return null;
        });
        check("Q3 fix B (setRollbackOnly): rolled back, method still returns normally", List.of(), new ArrayList<>(db.committed));

        // Q4: checked exception
        try {
            tx.invoke(NONE, () -> { db.insert("order#4"); throw new PaymentFailedException("declined"); });
        } catch (PaymentFailedException expected) { /* caller sees it */ }
        check("Q4 checked exception, default rules: COMMITTED despite the exception", List.of("order#4"), new ArrayList<>(db.committed));

        db.committed.clear();
        try {
            tx.invoke(ANY_EXCEPTION, () -> { db.insert("order#5"); throw new PaymentFailedException("declined"); });
        } catch (PaymentFailedException expected) { /* caller sees it */ }
        check("Q4 fix: rollbackFor = Exception.class -> rolled back", List.of(), new ArrayList<>(db.committed));

        // self-invocation: no proxy in the call path -> the annotation is never consulted
        class Service {
            void outer() { inner(); }            // this.inner(): the proxy is bypassed
            void inner() { db.insert("never-in-a-tx"); }
        }
        new Service().outer();
        check("bonus: self-invocation bypasses the proxy, so there is no transaction at all", 1, db.pending.size());
    }

    // ------------------------------------------------------------ Q8: JWT after logout
    static String b64(byte[] b) { return Base64.getUrlEncoder().withoutPadding().encodeToString(b); }
    static byte[] hmac(String key, String data) throws Exception {
        Mac m = Mac.getInstance("HmacSHA256");
        m.init(new SecretKeySpec(key.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
        return m.doFinal(data.getBytes(StandardCharsets.UTF_8));
    }
    static String sign(String key, String jti, long exp) throws Exception {
        String body = b64(("{\"sub\":\"ravi\",\"jti\":\"" + jti + "\",\"exp\":" + exp + "}").getBytes(StandardCharsets.UTF_8));
        return body + "." + b64(hmac(key, body));
    }
    /** stateless verification: signature + expiry only. Returns jti or null. */
    static String verify(String key, String token, long now, Set<String> denyList) throws Exception {
        String[] p = token.split("\\.");
        if (!b64(hmac(key, p[0])).equals(p[1])) return null;
        String json = new String(Base64.getUrlDecoder().decode(p[0]), StandardCharsets.UTF_8);
        long exp = Long.parseLong(json.replaceAll(".*\"exp\":(\\d+).*", "$1"));
        String jti = json.replaceAll(".*\"jti\":\"([^\"]+)\".*", "$1");
        if (now >= exp) return null;
        if (denyList != null && denyList.contains(jti)) return null;
        return jti;
    }

    static void q8() throws Exception {
        section("Q8. user logs out, JWT keeps working for 30 more minutes");
        String key = "server-secret";
        long issued = 0, exp = 30 * 60;
        String token = sign(key, "jti-123", exp);

        check("before logout (t=60s) token accepted", "jti-123", verify(key, token, 60, null));
        // logout only deletes the token in the browser; the server holds no state about it
        check("after logout (t=120s) the stolen/copied token is STILL accepted", "jti-123", verify(key, token, 120, null));
        check("only expiry ends it (t=30m)", null, verify(key, token, exp, null));

        Set<String> denyList = new HashSet<>();      // in prod: Redis SET jti EX <remaining lifetime>
        denyList.add("jti-123");
        check("fix: deny-list on logout, checked per request -> rejected at t=120s", null, verify(key, token, 120, denyList));
        String shortLived = sign(key, "jti-9", 5 * 60);
        check("fix: short-lived access token (5 min) shrinks the window to 5 min worst case", null, verify(key, shortLived, 5 * 60, null));
        System.out.println("  trade-off: a deny-list makes JWT stateful again (one Redis lookup per request).");
    }

    // ------------------------------------------------------------ Q9: probes
    /** Returns the second at which Kubernetes kills the container, or -1 if it survives. */
    static int killedAt(int startupSeconds, int livenessInitialDelay, int livenessPeriod, int livenessFailures,
                        Integer startupPeriod, Integer startupFailures) {
        if (startupPeriod != null) {
            // liveness is DISABLED until the startup probe succeeds; startup has its own budget
            int budget = startupPeriod * startupFailures;
            return startupSeconds <= budget ? -1 : budget;
        }
        // no startup probe: liveness starts after initialDelay and fails every period until the app is up
        int firstProbe = livenessInitialDelay;
        int killTime = firstProbe + (livenessFailures - 1) * livenessPeriod;     // third consecutive failure
        return startupSeconds > killTime ? killTime : -1;
    }

    static void q9() {
        section("Q9. Spring Boot takes 90 s to start, Kubernetes keeps restarting it");
        int startup = 90;
        int killed = killedAt(startup, 30, 10, 3, null, null);
        check("liveness only (initialDelay 30s, period 10s, failureThreshold 3): killed at second", 50, killed);
        System.out.println("    -> restart -> same 90 s start -> killed again = CrashLoopBackOff");

        check("startupProbe (period 5s x failureThreshold 30 = 150 s budget): survives", -1,
                killedAt(startup, 30, 10, 3, 5, 30));
        check("startupProbe too tight (period 5s x 12 = 60 s budget): killed at second", 60,
                killedAt(startup, 30, 10, 3, 5, 12));
        System.out.println("  also: fix WHY it takes 90 s (lazy init, classpath scan, Flyway on boot, a blocking remote call).");
    }

    // ------------------------------------------------------------ Q15: @Value in the constructor
    @Retention(RetentionPolicy.RUNTIME) @Target({ElementType.FIELD, ElementType.PARAMETER})
    @interface Value { String value(); }

    static class FieldInjectedService {
        @Value("timeout") String timeout;
        final String seenInConstructor;
        FieldInjectedService() { this.seenInConstructor = timeout; }      // field not injected yet
    }
    static class ConstructorInjectedService {
        final String seenInConstructor;
        ConstructorInjectedService(@Value("timeout") String timeout) { this.seenInConstructor = timeout; }
    }

    /** minimal container: instantiate, THEN populate annotated fields. */
    static <T> T createWithFieldInjection(Class<T> type, Map<String, String> props) throws Exception {
        T bean = type.getDeclaredConstructor().newInstance();
        for (Field f : type.getDeclaredFields()) {
            Value v = f.getAnnotation(Value.class);
            if (v != null) { f.setAccessible(true); f.set(bean, props.get(v.value())); }
        }
        return bean;
    }

    static void q15() throws Exception {
        section("Q15. @Value field is null inside the constructor");
        Map<String, String> props = Map.of("timeout", "30s");
        FieldInjectedService s = createWithFieldInjection(FieldInjectedService.class, props);
        check("field injection: value seen INSIDE constructor", null, s.seenInConstructor);
        check("field injection: value after the container finished", "30s", s.timeout);

        ConstructorInjectedService c = new ConstructorInjectedService(props.get("timeout"));
        check("fix: constructor parameter, value present in the constructor", "30s", c.seenInConstructor);
        System.out.println("  other fixes: @PostConstruct (runs after injection) or InitializingBean.afterPropertiesSet().");
    }

    // ------------------------------------------------------------ Q18: saveAll batching
    static int sqlRoundTrips(int rows, boolean identity, int batchSize, int sequenceAllocation) {
        if (identity || batchSize <= 1) return rows;                 // IDENTITY needs the id back per row: no batching
        int inserts = (rows + batchSize - 1) / batchSize;            // one JDBC batch per batch_size rows
        int sequenceCalls = (rows + sequenceAllocation - 1) / sequenceAllocation;   // pooled optimizer
        return inserts + sequenceCalls;
    }

    static void q18() {
        section("Q18. saveAll() of 10,000 entities sends 10,000 INSERTs");
        int rows = 10_000;
        check("IDENTITY id, batch_size unset: round trips", 10_000, sqlRoundTrips(rows, true, 0, 1));
        check("IDENTITY id, batch_size=50: STILL one INSERT per row (IDENTITY disables insert batching)", 10_000,
                sqlRoundTrips(rows, true, 50, 1));
        check("SEQUENCE (allocationSize 50), batch_size unset: still one INSERT per row", 10_000,
                sqlRoundTrips(rows, false, 0, 50));
        int fixed = sqlRoundTrips(rows, false, 50, 50);
        check("SEQUENCE (allocationSize 50) + batch_size=50: 200 batches + 200 sequence calls", 400, fixed);
        System.out.println("  config: spring.jpa.properties.hibernate.jdbc.batch_size=50, hibernate.order_inserts=true,");
        System.out.println("          PostgreSQL JDBC url ...?reWriteBatchedInserts=true");
        System.out.println("  also: flush()+clear() every batch so the persistence context does not grow to 10,000 entities.");
    }

    // ------------------------------------------------------------ Q19: open-in-view
    static class Session { boolean open = true; void close() { open = false; } }
    static class LazyList<T> {
        final Session session; final List<T> backing;
        LazyList(Session s, List<T> data) { session = s; backing = data; }
        List<T> get() {
            if (!session.open) throw new IllegalStateException(
                    "LazyInitializationException: could not initialize proxy - no Session");
            return backing;
        }
    }
    static class OrderEntity { final String id; final LazyList<String> lines;
        OrderEntity(String id, LazyList<String> lines) { this.id = id; this.lines = lines; } }

    static OrderEntity loadInTransaction(Session s, boolean fetchJoin) {
        List<String> lines = List.of("sku-1", "sku-2");
        OrderEntity e = new OrderEntity("o-1", new LazyList<>(s, lines));
        if (fetchJoin) e.lines.get();                 // JOIN FETCH / @EntityGraph: collection loaded while session is open
        return e;
    }

    static void q19() {
        section("Q19. open-in-view=false gives LazyInitializationException");
        Session s = new Session();
        OrderEntity lazy = loadInTransaction(s, false);
        s.close();                                    // @Transactional service method returned
        String msg = null;
        try { lazy.lines.get(); } catch (IllegalStateException e) { msg = e.getMessage(); }    // controller / Jackson
        check("lazy collection touched after the transaction ended", true, msg != null && msg.startsWith("LazyInitializationException"));

        // fix: do the work (fetch join or DTO mapping) inside the transaction
        Session s2 = new Session();
        OrderEntity fetched = loadInTransaction(s2, true);
        record OrderDto(String id, List<String> lines) { }
        OrderDto dto = new OrderDto(fetched.id, new ArrayList<>(fetched.lines.get()));   // mapped inside the tx
        s2.close();
        check("fix: fetch join / EntityGraph + map to DTO inside the transaction", List.of("sku-1", "sku-2"), dto.lines());
        System.out.println("  not a fix: open-in-view=true or FetchType.EAGER (hides N+1, holds a DB connection during view rendering).");
    }

    public static void main(String[] args) throws Exception {
        q3q4();
        q8();
        q9();
        q15();
        q18();
        q19();
        System.out.println("\nALL " + checks + " CHECKS PASSED");
    }
}
