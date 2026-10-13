/*
 * 01 - Resilience patterns: timeout, retry with backoff + jitter, circuit breaker, bulkhead, fallback
 *
 * Run:  java 01_circuit_breaker_retry_bulkhead.java
 *
 * What Resilience4j / Spring Cloud CircuitBreaker give you, in plain Java so the state machine is visible.
 * Interview angle: "a downstream service is slow/unavailable - what happens to your service?"
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.function.*;

class CircuitBreakerRetryBulkhead {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    // ---- circuit breaker: CLOSED -> (failure rate) -> OPEN -> (wait) -> HALF_OPEN -> CLOSED/OPEN
    static class CircuitBreaker {
        enum State { CLOSED, OPEN, HALF_OPEN }
        State state = State.CLOSED;
        final int window, minCalls, halfOpenProbes; final double failureRateThreshold; final long openMillis;
        final Deque<Boolean> recent = new ArrayDeque<>();     // true = failure
        long openedAt; int probesLeft; int probeSuccess;
        long now = 0;                                          // injected clock for deterministic output

        CircuitBreaker(int window, int minCalls, double threshold, long openMillis, int probes) {
            this.window = window; this.minCalls = minCalls; this.failureRateThreshold = threshold; this.openMillis = openMillis; this.halfOpenProbes = probes;
        }

        <T> T call(Supplier<T> action, Supplier<T> fallback) {
            if (state == State.OPEN) {
                if (now - openedAt >= openMillis) { state = State.HALF_OPEN; probesLeft = halfOpenProbes; probeSuccess = 0; }
                else return fallback.get();                    // fail fast: do not even call the dependency
            }
            try {
                T r = action.get();
                record(false);
                return r;
            } catch (RuntimeException e) {
                record(true);
                return fallback.get();
            }
        }

        private void record(boolean failure) {
            if (state == State.HALF_OPEN) {
                if (failure) { open(); return; }
                if (++probeSuccess >= halfOpenProbes) { state = State.CLOSED; recent.clear(); }
                return;
            }
            recent.addLast(failure);
            if (recent.size() > window) recent.removeFirst();
            if (recent.size() >= minCalls) {
                double rate = recent.stream().filter(f -> f).count() / (double) recent.size();
                if (rate >= failureRateThreshold) open();
            }
        }
        private void open() { state = State.OPEN; openedAt = now; recent.clear(); }
    }

    // ---- retry with exponential backoff and full jitter
    static <T> T retry(Supplier<T> action, int maxAttempts, long baseMs, long capMs, Random jitter, List<String> log) {
        RuntimeException last = null;
        for (int attempt = 1; attempt <= maxAttempts; attempt++) {
            try { return action.get(); }
            catch (RuntimeException e) {
                last = e;
                long exp = Math.min(capMs, baseMs * (1L << (attempt - 1)));
                long sleep = (long) (jitter.nextDouble() * exp);       // full jitter avoids synchronized retry storms
                log.add("attempt " + attempt + " failed -> wait ~" + sleep + " ms (cap of " + exp + " ms)");
            }
        }
        throw last;
    }

    public static void main(String[] args) throws Exception {

        section("1. Retry with exponential backoff and jitter");
        AtomicInteger calls = new AtomicInteger();
        List<String> log = new ArrayList<>();
        String result = retry(() -> {
            if (calls.incrementAndGet() < 4) throw new IllegalStateException("503 from inventory");
            return "stock=17";
        }, 5, 100, 2_000, new Random(3), log);
        log.forEach(l -> System.out.println("  " + l));
        System.out.println("  succeeded on call #" + calls.get() + " -> " + result);
        System.out.println("  Retry ONLY idempotent calls and only transient errors (timeouts, 502/503/504, 429). Never retry 400/401/404.");
        System.out.println("  Retries multiply load: 3 layers x 3 attempts = 27x. Budget retries and retry at ONE layer.");

        section("2. Circuit breaker state machine");
        CircuitBreaker cb = new CircuitBreaker(10, 5, 0.5, 5_000, 2);
        boolean[] downstreamHealthy = {true};
        AtomicInteger realCalls = new AtomicInteger();
        Supplier<String> downstream = () -> {
            realCalls.incrementAndGet();
            if (!downstreamHealthy[0]) throw new RuntimeException("timeout");
            return "OK";
        };
        System.out.println("  phase            state      fallback-count real-downstream-calls");
        String[] phases = {"healthy x6", "outage x10", "still down, breaker open x10", "outage over, wait 5s, probe x3"};
        for (int ph = 0; ph < phases.length; ph++) {
            int fallbacks = 0, realBefore = realCalls.get();
            if (ph == 1 || ph == 2) downstreamHealthy[0] = false;
            if (ph == 3) { downstreamHealthy[0] = true; cb.now += 5_000; }
            int n = ph == 0 ? 6 : ph == 3 ? 3 : 10;
            for (int i = 0; i < n; i++) {
                String r = cb.call(downstream, () -> "FALLBACK");
                if (r.equals("FALLBACK")) fallbacks++;
            }
            System.out.printf("  %-30s %-9s %5d %12d%n", phases[ph], cb.state, fallbacks, realCalls.get() - realBefore);
        }
        System.out.println("  While OPEN, calls fail in microseconds instead of tying up threads for the full timeout.");
        System.out.println("  HALF_OPEN lets a few probes through; success closes the breaker, any failure re-opens it.");

        section("3. Why timeouts come first: thread-pool exhaustion without them");
        int pool = 10; double normalMs = 50, slowMs = 5_000, rps = 100;
        System.out.printf("  pool=%d threads, normal latency %.0f ms -> capacity %.0f req/s (offered %.0f)%n", pool, normalMs, pool * 1000 / normalMs, rps);
        System.out.printf("  dependency hangs for %.0f ms -> capacity %.1f req/s: ALL %d threads blocked, the service looks dead%n", slowMs, pool * 1000 / slowMs, pool);
        System.out.println("  Fix: connect/read timeouts (< caller's timeout), bounded pool/queue, circuit breaker, bulkhead.");
        System.out.println("  Timeout budget: client 3s > gateway 2.5s > service 2s > DB 1s (inner timeouts shorter than outer).");

        section("4. Bulkhead: isolate a slow dependency so it cannot consume every thread");
        Semaphore reportsBulkhead = new Semaphore(2);              // at most 2 concurrent calls to the slow reports service
        ExecutorService ex = Executors.newFixedThreadPool(6);
        CountDownLatch release = new CountDownLatch(1);
        AtomicInteger admitted = new AtomicInteger(), rejected = new AtomicInteger();
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < 6; i++) fs.add(ex.submit(() -> {
            if (!reportsBulkhead.tryAcquire()) { rejected.incrementAndGet(); return; }   // fail fast, keep threads for other work
            try { admitted.incrementAndGet(); release.await(); } catch (InterruptedException ignored) { }
            finally { reportsBulkhead.release(); }
        }));
        Thread.sleep(150);
        System.out.println("  6 concurrent calls to a hung dependency with bulkhead=2 -> admitted " + admitted.get() + ", rejected immediately " + rejected.get());
        release.countDown();
        for (Future<?> f : fs) f.get();
        ex.shutdown();
        System.out.println("  Resilience4j: Bulkhead (semaphore) or ThreadPoolBulkhead; Spring: separate executors per dependency.");

        section("5. Fallbacks: choose a degraded answer on purpose");
        System.out.println("  recommendations down -> show popular items (cached)   | payment gateway down -> queue the order, tell the user");
        System.out.println("  inventory down -> allow checkout with 'backorder' flag | auth down -> NO fallback: fail closed");
        System.out.println("  A fallback that hides a failure from monitoring is worse than an error: always emit a metric.");
    }
}

// EXERCISE: add a time-based sliding window and a 'slow call' threshold (calls > 2s count as failures).
