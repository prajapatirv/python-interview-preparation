/*
 * 04 - CompletableFuture: composing async work (Java 8, orTimeout in 9)
 *
 * Run:  java 04_completable_future.java
 *
 * Interview angle: "Future vs CompletableFuture", "thenApply vs thenCompose",
 * "how do you call 3 services in parallel and combine results?", "error handling",
 * "which thread pool does supplyAsync use?".
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

class CompletableFutureDemo {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }

    static CompletableFuture<String> call(String svc, long ms, ExecutorService pool) {
        return CompletableFuture.supplyAsync(() -> { sleep(ms); return svc + "-result"; }, pool);
    }

    public static void main(String[] args) throws Exception {
        // Always pass your own executor: the default is ForkJoinPool.commonPool(), which is sized
        // to the CPU count and shared by every parallel stream and async stage in the JVM.
        ExecutorService pool = Executors.newFixedThreadPool(8);
        try {
            section("1. Sequential dependency: thenCompose (flatMap) vs thenApply (map)");
            CompletableFuture<Integer> userId = CompletableFuture.supplyAsync(() -> 42, pool);
            CompletableFuture<String> viaApply = userId.thenApply(id -> "profile-of-" + id);                       // sync transform
            CompletableFuture<String> viaCompose = userId.thenCompose(id -> call("orders-for-" + id, 50, pool));   // next async step
            System.out.println("  thenApply   -> " + viaApply.get());
            System.out.println("  thenCompose -> " + viaCompose.get() + "  (using thenApply here would give CompletableFuture<CompletableFuture<..>>)");

            section("2. Fan-out in parallel, then combine: total time ~ slowest call, not the sum");
            long t0 = System.nanoTime();
            CompletableFuture<String> a = call("inventory", 300, pool);
            CompletableFuture<String> b = call("pricing", 200, pool);
            CompletableFuture<String> c = call("shipping", 250, pool);
            String combined = a.thenCombine(b, (x, y) -> x + " + " + y).thenCombine(c, (xy, z) -> xy + " + " + z).get();
            long ms = (System.nanoTime() - t0) / 1_000_000;
            System.out.println("  " + combined);
            System.out.println("  elapsed ~" + (ms / 50 * 50) + "ms  (sequential would be ~750ms)");

            section("3. allOf for N futures");
            List<CompletableFuture<String>> many = IntStream.range(0, 5).mapToObj(i -> call("svc" + i, 100, pool)).collect(Collectors.toList());
            CompletableFuture.allOf(many.toArray(new CompletableFuture[0])).join();
            System.out.println("  " + many.stream().map(CompletableFuture::join).collect(Collectors.toList()));

            section("4. Error handling: exceptionally / handle / whenComplete");
            CompletableFuture<String> failing = CompletableFuture.supplyAsync(() -> {
                if (true) throw new IllegalStateException("pricing service down");
                return "never";
            }, pool);
            System.out.println("  exceptionally -> " + failing.exceptionally(ex -> "fallback(" + ex.getClass().getSimpleName()
                    + " -> " + ex.getCause().getMessage() + ")").get());
            System.out.println("  handle        -> " + failing.handle((v, ex) -> ex == null ? v : "recovered").get());
            failing.whenComplete((v, ex) -> System.out.println("  whenComplete  -> observed "
                    + (ex == null ? v : ex.getClass().getSimpleName()) + " (side effect only, result unchanged)"))
                    .exceptionally(ex -> null).get();
            try { failing.get(); }
            catch (ExecutionException e) { System.out.println("  get() wraps   -> ExecutionException cause=" + e.getCause()); }
            try { failing.join(); }
            catch (CompletionException e) { System.out.println("  join() wraps  -> CompletionException cause=" + e.getCause()); }

            section("5. Timeouts (Java 9+): never wait forever on a remote call");
            CompletableFuture<String> slow = call("slow-vendor", 2_000, pool).orTimeout(150, TimeUnit.MILLISECONDS)
                    .exceptionally(ex -> "timeout-fallback(" + ex.getClass().getSimpleName() + ")");
            System.out.println("  " + slow.get());
            CompletableFuture<String> withDefault = call("slow-vendor", 2_000, pool).completeOnTimeout("default-value", 150, TimeUnit.MILLISECONDS);
            System.out.println("  completeOnTimeout -> " + withDefault.get());

            section("6. Which thread runs the callback?");
            CompletableFuture<Void> f = CompletableFuture.supplyAsync(() -> Thread.currentThread().getName(), pool)
                    .thenAccept(n -> System.out.println("  supplier ran on a pool thread: " + n.startsWith("pool-")));
            f.get();
            System.out.println("  thenApply (no Async) runs on the completing thread or the caller; use thenApplyAsync(fn, pool) to move it.");
        } finally {
            pool.shutdown();
        }
    }
}

// EXERCISE: call the same flaky endpoint, retrying up to 3 times with exponential backoff, using
// only CompletableFuture (hint: recursion with exceptionallyCompose in 12+, or handle + thenCompose).
