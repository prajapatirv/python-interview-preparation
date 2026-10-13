/*
 * 04 - Coding round: "implement this component" questions (LRU, singleton, idempotent REST
 *      handler, rate limiter, producer-consumer, retry, CompletableFuture)
 *
 * Run:  java 04_design_coding_lru_idempotency_concurrency.java
 *
 * Interview angle: "implement an LRU cache", "thread-safe singleton", "make POST /payments
 * idempotent", "implement a rate limiter", "producer-consumer with wait/notify", "retry with
 * backoff", "run three calls in parallel and combine". Each component is small, thread-safe where
 * it must be, and proven under concurrency (50 threads, one key) so the claim is demonstrated.
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.function.*;

class DesignCodingComponents {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    // ---- 1. LRU cache -------------------------------------------------------------------
    /** The 5-line answer. NOT thread-safe: wrap with Collections.synchronizedMap or lock. */
    static class LruByLinkedHashMap<K, V> extends LinkedHashMap<K, V> {
        private final int cap;
        LruByLinkedHashMap(int cap) { super(16, 0.75f, true); this.cap = cap; }   // true = access order
        @Override protected boolean removeEldestEntry(Map.Entry<K, V> e) { return size() > cap; }
    }

    /** The "no LinkedHashMap allowed" answer: HashMap + doubly linked list, O(1) get and put. */
    static class LruManual<K, V> {
        private class N { K k; V v; N prev, next; N(K k, V v) { this.k = k; this.v = v; } }
        private final Map<K, N> map = new HashMap<>();
        private final N head = new N(null, null), tail = new N(null, null);   // sentinels: no null checks
        private final int cap;
        LruManual(int cap) { this.cap = cap; head.next = tail; tail.prev = head; }
        synchronized V get(K k) {
            N n = map.get(k);
            if (n == null) return null;
            unlink(n); addFront(n);
            return n.v;
        }
        synchronized void put(K k, V v) {
            N n = map.get(k);
            if (n != null) { n.v = v; unlink(n); addFront(n); return; }
            if (map.size() == cap) { N lru = tail.prev; unlink(lru); map.remove(lru.k); }
            n = new N(k, v); map.put(k, n); addFront(n);
        }
        private void unlink(N n) { n.prev.next = n.next; n.next.prev = n.prev; }
        private void addFront(N n) { n.next = head.next; n.prev = head; head.next.prev = n; head.next = n; }
        synchronized List<K> keysMostRecentFirst() {
            List<K> r = new ArrayList<>();
            for (N n = head.next; n != tail; n = n.next) r.add(n.k);
            return r;
        }
    }

    // ---- 2. Singletons ------------------------------------------------------------------
    enum EnumSingleton { INSTANCE; final long created = System.nanoTime(); }   // safest: serialization + reflection proof

    static class HolderSingleton {                                              // lazy, no locking, JVM guarantees
        private HolderSingleton() { }
        private static class Holder { static final HolderSingleton I = new HolderSingleton(); }
        static HolderSingleton get() { return Holder.I; }
    }

    static class DoubleCheckedSingleton {                                       // 'volatile' is the whole point
        private static volatile DoubleCheckedSingleton instance;
        static final AtomicInteger constructed = new AtomicInteger();
        private DoubleCheckedSingleton() { constructed.incrementAndGet(); }
        static DoubleCheckedSingleton get() {
            DoubleCheckedSingleton r = instance;
            if (r == null) {
                synchronized (DoubleCheckedSingleton.class) {
                    r = instance;
                    if (r == null) instance = r = new DoubleCheckedSingleton();
                }
            }
            return r;
        }
    }

    // ---- 3. Idempotent REST handler (Idempotency-Key) ------------------------------------
    /**
     * Rules: same key + same payload -> replay the stored response, run the business logic ONCE;
     * same key + DIFFERENT payload -> 422 (client bug, never silently accept); the first request
     * may still be running -> concurrent duplicates wait for it instead of running again.
     * The reservation must be ATOMIC (putIfAbsent / computeIfAbsent); containsKey-then-put is a race.
     */
    static class IdempotentHandler {
        record Response(int status, String body) { }
        private record Entry(String payloadHash, CompletableFuture<Response> result, long expiresAt) { }

        private final ConcurrentHashMap<String, Entry> store = new ConcurrentHashMap<>();
        private final LongSupplier clock;
        private final long ttlMillis;
        final AtomicInteger executions = new AtomicInteger();

        IdempotentHandler(LongSupplier clock, long ttlMillis) { this.clock = clock; this.ttlMillis = ttlMillis; }

        Response handle(String key, String payload, Supplier<Response> businessLogic) {
            if (key == null || key.isBlank()) return new Response(400, "Idempotency-Key header required");
            String hash = Integer.toHexString(payload.hashCode());          // use SHA-256 in production
            long now = clock.getAsLong();
            store.computeIfPresent(key, (k, e) -> e.expiresAt() <= now && e.result().isDone() ? null : e);

            CompletableFuture<Response> mine = new CompletableFuture<>();
            Entry candidate = new Entry(hash, mine, now + ttlMillis);
            Entry existing = store.putIfAbsent(key, candidate);             // atomic reservation: one winner

            if (existing == null) {                                          // I own this key: do the work
                try {
                    executions.incrementAndGet();
                    Response r = businessLogic.get();
                    mine.complete(r);
                } catch (RuntimeException ex) {
                    store.remove(key, candidate);                            // failure is retryable: release the key
                    mine.completeExceptionally(ex);
                    throw ex;
                }
                return mine.join();
            }
            if (!existing.payloadHash().equals(hash))
                return new Response(422, "Idempotency-Key reused with a different request body");
            Response replay = existing.result().join();                      // waits if still in flight
            return new Response(replay.status(), replay.body());             // same answer, no second side effect
        }
    }

    // ---- 4. Rate limiters ---------------------------------------------------------------
    /** Token bucket: allows bursts up to capacity, sustained rate = refill per second. Clock injected. */
    static class TokenBucket {
        private final long capacity; private final double refillPerMs; private double tokens; private long last;
        private final LongSupplier clock;
        TokenBucket(long capacity, double refillPerSecond, LongSupplier clock) {
            this.capacity = capacity; this.refillPerMs = refillPerSecond / 1000.0;
            this.tokens = capacity; this.clock = clock; this.last = clock.getAsLong();
        }
        synchronized boolean tryAcquire() {
            long now = clock.getAsLong();
            tokens = Math.min(capacity, tokens + (now - last) * refillPerMs);
            last = now;
            if (tokens >= 1) { tokens -= 1; return true; }
            return false;
        }
    }
    /** Semaphore limits CONCURRENCY (in-flight calls), a different thing from a rate. */
    static class ConcurrencyLimiter {
        private final Semaphore permits;
        ConcurrencyLimiter(int max) { permits = new Semaphore(max); }
        boolean run(Runnable r) {
            if (!permits.tryAcquire()) return false;
            try { r.run(); return true; } finally { permits.release(); }    // release in finally or you leak permits
        }
    }

    // ---- 5. Producer-consumer with wait/notify -------------------------------------------
    static class BoundedBuffer<T> {
        private final Queue<T> q = new ArrayDeque<>();
        private final int cap;
        BoundedBuffer(int cap) { this.cap = cap; }
        synchronized void put(T t) throws InterruptedException {
            while (q.size() == cap) wait();                                  // WHILE, never if: spurious wakeups
            q.add(t);
            notifyAll();                                                     // notifyAll: producers and consumers share one monitor
        }
        synchronized T take() throws InterruptedException {
            while (q.isEmpty()) wait();
            T t = q.remove();
            notifyAll();
            return t;
        }
    }

    // ---- 6. Retry with exponential backoff ----------------------------------------------
    static <T> T retry(int maxAttempts, long baseDelayMs, Callable<T> call, LongConsumer sleeper) throws Exception {
        Exception last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try { return call.call(); }
            catch (Exception e) {
                last = e;
                if (attempt < maxAttempts) sleeper.accept(baseDelayMs << (attempt - 1));   // 100, 200, 400 ...
            }
        }
        throw last;
    }

    public static void main(String[] args) throws Exception {
        section("1. LRU cache");
        LruByLinkedHashMap<String, Integer> lru = new LruByLinkedHashMap<>(2);
        lru.put("a", 1); lru.put("b", 2); lru.get("a"); lru.put("c", 3);     // touching a makes b the eldest
        check("LinkedHashMap LRU evicts the least recently used", "[a, c]", lru.keySet().toString());
        LruManual<String, Integer> m = new LruManual<>(3);
        m.put("a", 1); m.put("b", 2); m.put("c", 3); m.get("a"); m.put("d", 4);
        check("manual LRU order, most recent first", "[d, a, c]", m.keysMostRecentFirst().toString());
        check("manual LRU miss after eviction", null, m.get("b"));

        section("2. Singletons");
        check("enum singleton identity", true, EnumSingleton.INSTANCE == EnumSingleton.valueOf("INSTANCE"));
        check("holder singleton identity", true, HolderSingleton.get() == HolderSingleton.get());
        ExecutorService pool = Executors.newFixedThreadPool(16);
        List<Future<DoubleCheckedSingleton>> fs = new ArrayList<>();
        for (int i = 0; i < 200; i++) fs.add(pool.submit(DoubleCheckedSingleton::get));
        Set<DoubleCheckedSingleton> uniq = Collections.newSetFromMap(new IdentityHashMap<>());
        for (Future<DoubleCheckedSingleton> f : fs) uniq.add(f.get());
        check("double-checked locking: 200 racing callers, 1 instance", "1/1", uniq.size() + "/" + DoubleCheckedSingleton.constructed.get());

        section("3. Idempotent POST with an Idempotency-Key");
        AtomicLong now = new AtomicLong(1_000);
        IdempotentHandler h = new IdempotentHandler(now::get, 60_000);
        AtomicInteger orderSeq = new AtomicInteger();
        Supplier<IdempotentHandler.Response> createOrder = () -> {
            try { Thread.sleep(30); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
            return new IdempotentHandler.Response(201, "order-" + orderSeq.incrementAndGet());
        };
        List<Future<IdempotentHandler.Response>> calls = new ArrayList<>();
        for (int i = 0; i < 50; i++)
            calls.add(pool.submit(() -> h.handle("key-1", "{\"sku\":\"A\",\"qty\":1}", createOrder)));
        Set<String> bodies = new TreeSet<>();
        for (Future<IdempotentHandler.Response> f : calls) bodies.add(f.get().status() + ":" + f.get().body());
        check("50 concurrent duplicates -> every caller sees the SAME response", "[201:order-1]", bodies.toString());
        check("business logic executed exactly once", 1, h.executions.get());
        check("different body, same key -> 422",
                422, h.handle("key-1", "{\"sku\":\"B\",\"qty\":9}", createOrder).status());
        check("missing key -> 400", 400, h.handle(null, "{}", createOrder).status());
        check("a NEW key creates a NEW order", "order-2", h.handle("key-2", "{}", createOrder).body());

        IdempotentHandler.Response[] boom = new IdempotentHandler.Response[1];
        try {
            h.handle("key-3", "{}", () -> { throw new IllegalStateException("db down"); });
        } catch (IllegalStateException expected) { boom[0] = null; }
        check("a FAILED first attempt does not poison the key (retry runs again)",
                "order-3", h.handle("key-3", "{}", createOrder).body());
        now.addAndGet(61_000);
        check("after the TTL the key is forgotten (new execution)", "order-4", h.handle("key-1", "{\"sku\":\"A\",\"qty\":1}", createOrder).body());

        section("4. Rate limiting");
        AtomicLong t = new AtomicLong(0);
        TokenBucket tb = new TokenBucket(5, 2, t::get);                       // burst 5, then 2 per second
        int burst = 0; for (int i = 0; i < 10; i++) if (tb.tryAcquire()) burst++;
        check("burst allowed up to capacity", 5, burst);
        t.addAndGet(1_000);
        int afterOneSecond = 0; for (int i = 0; i < 10; i++) if (tb.tryAcquire()) afterOneSecond++;
        check("one second later: refill rate (2 tokens)", 2, afterOneSecond);
        ConcurrencyLimiter cl = new ConcurrencyLimiter(1);
        CountDownLatch inside = new CountDownLatch(1), release = new CountDownLatch(1);
        Future<Boolean> first = pool.submit(() -> cl.run(() -> {
            inside.countDown();
            try { release.await(); } catch (InterruptedException ignored) { }
        }));
        inside.await();
        check("second caller rejected while the permit is held", false, cl.run(() -> { }));
        release.countDown();
        check("first caller completed", true, first.get());
        check("permit released afterwards", true, cl.run(() -> { }));

        section("5. Producer-consumer");
        BoundedBuffer<Integer> buf = new BoundedBuffer<>(3);
        int items = 1_000;
        Future<Long> producer = pool.submit(() -> { for (int i = 1; i <= items; i++) buf.put(i); return 0L; });
        Future<Long> consumer = pool.submit(() -> { long s = 0; for (int i = 0; i < items; i++) s += buf.take(); return s; });
        producer.get();
        check("consumer received every item once (sum 1..1000)", 500_500L, consumer.get());

        section("6. Retry with exponential backoff (injected sleeper, no real waiting)");
        List<Long> delays = new ArrayList<>();
        AtomicInteger tries = new AtomicInteger();
        String ok = retry(4, 100, () -> {
            if (tries.incrementAndGet() < 3) throw new java.io.IOException("flaky");
            return "done@" + tries.get();
        }, delays::add);
        check("succeeds on 3rd attempt", "done@3", ok);
        check("backoff delays", "[100, 200]", delays.toString());
        try {
            retry(2, 10, () -> { throw new java.io.IOException("always"); }, d -> { });
            check("must rethrow", "threw", "did not");
        } catch (java.io.IOException e) {
            check("exhausted retries rethrow the last exception", "always", e.getMessage());
        }

        section("7. CompletableFuture: combine, timeout, fallback");
        ExecutorService io = Executors.newFixedThreadPool(4);
        CompletableFuture<String> user = CompletableFuture.supplyAsync(() -> sleepThen("user", 40), io);
        CompletableFuture<String> orders = CompletableFuture.supplyAsync(() -> sleepThen("orders", 40), io);
        CompletableFuture<String> slow = CompletableFuture.supplyAsync(() -> sleepThen("recs", 2_000), io)
                .completeOnTimeout("recs-fallback", 100, TimeUnit.MILLISECONDS);
        long start = System.nanoTime();
        String combined = user.thenCombine(orders, (u, o) -> u + "+" + o)
                .thenCombine(slow, (uo, r) -> uo + "+" + r).get(1, TimeUnit.SECONDS);
        long ms = (System.nanoTime() - start) / 1_000_000;
        check("three calls in parallel, slow one falls back", "user+orders+recs-fallback", combined);
        check("wall time is the SLOWEST call, not the sum (<1s)", true, ms < 1_000);
        CompletableFuture<String> failing = CompletableFuture.<String>supplyAsync(() -> { throw new IllegalStateException("x"); }, io)
                .exceptionally(ex -> "recovered:" + ex.getCause().getClass().getSimpleName());
        check("exceptionally unwraps CompletionException via getCause", "recovered:IllegalStateException", failing.get());

        io.shutdownNow();
        pool.shutdownNow();
        System.out.println("\nAll " + checks + " checks passed.");
    }

    static String sleepThen(String v, long ms) {
        try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        return v;
    }
}
