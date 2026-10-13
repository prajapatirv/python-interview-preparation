/*
 * 02 - ThreadPoolExecutor: core/max/queue, rejection, sizing
 *
 * Run:  java 02_thread_pools_and_sizing.java
 *
 * Interview angle: "how does a ThreadPoolExecutor decide to create a thread?",
 * "why not Executors.newFixedThreadPool in production?", "how do you size a pool?",
 * "what happens when the queue is full?".
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

class ThreadPoolsAndSizing {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }

    public static void main(String[] args) throws Exception {

        section("1. The submit order: core threads -> queue -> extra threads (up to max) -> reject");
        ThreadPoolExecutor pool = new ThreadPoolExecutor(
                2, 4,                                     // core=2, max=4
                30, TimeUnit.SECONDS,
                new ArrayBlockingQueue<>(3),              // bounded queue of 3
                r -> new Thread(r, "worker"),
                new ThreadPoolExecutor.AbortPolicy());    // throw RejectedExecutionException
        CountDownLatch release = new CountDownLatch(1);
        int accepted = 0, rejected = 0;
        for (int i = 1; i <= 10; i++) {
            try {
                pool.execute(() -> { try { release.await(); } catch (InterruptedException ignored) { } });
                accepted++;
                System.out.printf("  task %2d accepted -> threads=%d queued=%d%n", i, pool.getPoolSize(), pool.getQueue().size());
            } catch (RejectedExecutionException e) {
                rejected++;
                System.out.printf("  task %2d REJECTED (threads=%d queue full)%n", i, pool.getPoolSize());
            }
        }
        System.out.println("  accepted=" + accepted + " rejected=" + rejected + "  (2 core + 3 queued + 2 extra = 7)");
        release.countDown();
        pool.shutdown();
        pool.awaitTermination(2, TimeUnit.SECONDS);

        section("2. Rejection policies");
        for (RejectedExecutionHandler h : new RejectedExecutionHandler[]{
                new ThreadPoolExecutor.AbortPolicy(), new ThreadPoolExecutor.CallerRunsPolicy(),
                new ThreadPoolExecutor.DiscardPolicy(), new ThreadPoolExecutor.DiscardOldestPolicy()}) {
            ThreadPoolExecutor p = new ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, new ArrayBlockingQueue<>(1), h);
            CountDownLatch gate = new CountDownLatch(1);
            AtomicInteger ranOnCaller = new AtomicInteger();
            String caller = Thread.currentThread().getName();
            String outcome = "ok";
            try {
                for (int i = 0; i < 4; i++) p.execute(() -> {
                    if (Thread.currentThread().getName().equals(caller)) ranOnCaller.incrementAndGet();
                    try { gate.await(300, TimeUnit.MILLISECONDS); } catch (InterruptedException ignored) { }
                });
            } catch (RejectedExecutionException e) { outcome = "threw RejectedExecutionException"; }
            System.out.printf("  %-22s -> %s, tasks run on caller thread: %d%n", h.getClass().getSimpleName(), outcome, ranOnCaller.get());
            gate.countDown();
            p.shutdownNow();
        }
        System.out.println("  CallerRunsPolicy = natural back-pressure: the submitter slows down because it does the work itself.");

        section("3. Why Executors.newFixedThreadPool is risky in production");
        ExecutorService fixed = Executors.newFixedThreadPool(2);
        System.out.println("  its queue is an UNBOUNDED LinkedBlockingQueue -> under overload it grows until OutOfMemoryError,");
        System.out.println("  and you never see rejections. newCachedThreadPool is the opposite: unbounded THREADS.");
        fixed.shutdown();

        section("4. Sizing: CPU-bound vs I/O-bound");
        int cores = Runtime.getRuntime().availableProcessors();
        double waitMs = 90, computeMs = 10;
        System.out.println("  cores=" + cores);
        System.out.println("  CPU-bound   : threads ~ cores (+1)            = " + (cores + 1));
        System.out.println("  I/O-bound   : threads ~ cores * (1 + wait/compute) = " + (int) Math.ceil(cores * (1 + waitMs / computeMs))
                + "   (wait=" + waitMs + "ms, compute=" + computeMs + "ms)");
        System.out.println("  Little's law: concurrency = throughput x latency, e.g. 200 req/s x 0.25 s = 50 in flight.");
        System.out.println("  Measure, then cap the pool below what the downstream (DB pool, partner API) can absorb.");

        section("5. Graceful shutdown pattern");
        ExecutorService svc = Executors.newFixedThreadPool(2);
        for (int i = 0; i < 4; i++) svc.submit(() -> sleep(50));
        svc.shutdown();                                                   // stop accepting, finish queued work
        boolean clean = svc.awaitTermination(1, TimeUnit.SECONDS);
        if (!clean) svc.shutdownNow();                                    // interrupt stragglers
        System.out.println("  terminated cleanly = " + clean);

        section("6. Handling exceptions: submit() swallows them into the Future");
        ExecutorService ex = Executors.newSingleThreadExecutor();
        Future<?> f = ex.submit(() -> { throw new IllegalStateException("boom"); });
        try { f.get(); } catch (ExecutionException e) { System.out.println("  only visible via get(): " + e.getCause()); }
        ex.shutdown();
        System.out.println("  with execute() the exception reaches the thread's UncaughtExceptionHandler instead.");
    }
}

// EXERCISE: run the section-1 experiment with a SynchronousQueue (what newCachedThreadPool uses)
// and explain why task 3 is already rejected when max=2.
