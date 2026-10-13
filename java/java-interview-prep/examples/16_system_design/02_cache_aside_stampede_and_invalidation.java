/*
 * 02 - Caching: cache-aside, cache stampede (thundering herd), single-flight, negative caching, TTL jitter
 *
 * Run:  java 02_cache_aside_stampede_and_invalidation.java
 *
 * 50 concurrent requests miss the same hot key at the same instant. How many database calls?
 * Counting them makes the fix (single-flight / lock-per-key) a number instead of a slogan.
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

class CacheAsideStampedeAndInvalidation {

    static final AtomicInteger DB_CALLS = new AtomicInteger();

    static String slowDatabase(String key) {
        DB_CALLS.incrementAndGet();
        try { Thread.sleep(150); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        return key.startsWith("missing") ? null : "value-of-" + key;
    }

    // ---- naive cache-aside
    static class NaiveCache {
        final ConcurrentHashMap<String, String> map = new ConcurrentHashMap<>();
        String get(String key) {
            String v = map.get(key);
            if (v == null) { v = slowDatabase(key); if (v != null) map.put(key, v); }   // every concurrent miss goes to the DB
            return v;
        }
    }

    // ---- single-flight: only the first miss loads, the rest wait on the same future
    static class SingleFlightCache {
        final ConcurrentHashMap<String, CompletableFuture<String>> inflight = new ConcurrentHashMap<>();
        final ConcurrentHashMap<String, String> map = new ConcurrentHashMap<>();
        String get(String key) {
            String v = map.get(key);
            if (v != null) return v;
            CompletableFuture<String> f = new CompletableFuture<>();
            CompletableFuture<String> existing = inflight.putIfAbsent(key, f);
            if (existing != null) return existing.join();
            try {
                v = slowDatabase(key);
                if (v != null) map.put(key, v);
                f.complete(v);
                return v;
            } catch (RuntimeException e) { f.completeExceptionally(e); throw e; }
            finally { inflight.remove(key); }
        }
    }

    static int herd(java.util.function.Function<String, String> lookup, String key, int threads) throws Exception {
        DB_CALLS.set(0);
        ExecutorService pool = Executors.newFixedThreadPool(threads);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<String>> fs = new ArrayList<>();
        for (int i = 0; i < threads; i++) fs.add(pool.submit(() -> { go.await(); return lookup.apply(key); }));
        go.countDown();
        for (Future<String> f : fs) f.get();
        pool.shutdown();
        return DB_CALLS.get();
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) throws Exception {

        section("1. Cache stampede: a hot key expires, 50 requests arrive together");
        System.out.println("  naive cache-aside     : " + herd(new NaiveCache()::get, "hot-product", 50) + " database calls for ONE key");
        System.out.println("  single-flight/per-key : " + herd(new SingleFlightCache()::get, "hot-product", 50) + " database call");
        System.out.println("  In Spring: @Cacheable(sync = true) or Caffeine's LoadingCache (computes per key atomically).");

        section("2. Cache penetration: requests for keys that do not exist bypass the cache every time");
        NaiveCache c = new NaiveCache();
        DB_CALLS.set(0);
        for (int i = 0; i < 5; i++) c.get("missing-123");
        System.out.println("  5 lookups of a missing key -> " + DB_CALLS.get() + " DB calls (null is never cached)");
        System.out.println("  Fix: cache a NULL marker with a short TTL (negative caching), or a Bloom filter in front for huge key spaces.");

        section("3. Expiry avalanche: many keys with the same TTL expire together");
        Random r = new Random(9);
        int[] perSecondSame = new int[800], perSecondJitter = new int[800];
        for (int i = 0; i < 1_000; i++) {
            perSecondSame[600]++;                                   // all keys loaded together with ttl = 600 s
            perSecondJitter[600 + r.nextInt(121) - 60]++;           // ttl = 600 s +- 60 s
        }
        System.out.println("  1,000 keys, ttl=600s : worst second sees " + Arrays.stream(perSecondSame).max().getAsInt() + " expiries -> that many DB reloads at once");
        System.out.println("  ttl = 600s +- 10%    : worst second sees " + Arrays.stream(perSecondJitter).max().getAsInt() + " expiries");
        System.out.println("  Fix: ttl = base + random jitter, plus refresh-ahead for the hottest keys.");

        section("4. Invalidation strategies (the hard part)");
        System.out.println("  TTL only            : simplest; stale for up to TTL - fine for catalog data, wrong for balances");
        System.out.println("  Cache-aside + delete: write DB first, THEN evict the key; a concurrent reader can still re-cache old data briefly");
        System.out.println("  Write-through       : write cache and DB together; consistent reads, slower writes, caches rarely-read data");
        System.out.println("  Write-behind        : write cache, flush async; fast but can lose data on crash");
        System.out.println("  Event-driven        : publish 'ProductChanged' (Kafka) -> consumers evict/refresh; best for multi-service/multi-node caches");
        System.out.println("  Local (Caffeine) vs distributed (Redis): local = nanoseconds but per-node staleness; Redis = shared, network hop.");

        section("5. What belongs in a cache?");
        System.out.println("  Read-heavy, expensive to compute, tolerant of slight staleness, with a clear key. Measure hit ratio and eviction rate.");
        System.out.println("  Never cache per-user secrets under a shared key; always bound size (maximumSize) so the cache cannot cause an OOM.");
    }
}

// EXERCISE: add stale-while-revalidate: serve the expired value immediately and refresh in the background.
