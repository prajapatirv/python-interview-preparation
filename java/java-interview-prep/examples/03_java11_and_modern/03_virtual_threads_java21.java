/*
 * 03 - Virtual threads (Java 21) vs platform threads
 *
 * Run:  java 03_virtual_threads_java21.java
 *
 * Interview angle: "what problem do virtual threads solve?", "do they make CPU work faster?",
 * "what is pinning?", "do you still need reactive?".
 */
import java.time.Duration;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.stream.*;

class VirtualThreadsJava21 {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static long blockingTasks(ExecutorService ex, int n, long sleepMs) throws Exception {
        long t0 = System.nanoTime();
        List<Future<Integer>> fs = new ArrayList<>();
        for (int i = 0; i < n; i++) fs.add(ex.submit(() -> { Thread.sleep(sleepMs); return 1; }));   // simulates a blocking I/O call
        for (Future<Integer> f : fs) f.get();
        return (System.nanoTime() - t0) / 1_000_000;
    }

    public static void main(String[] args) throws Exception {

        section("1. Creating them");
        Thread v = Thread.ofVirtual().name("virt-1").start(() -> System.out.println("  inside: isVirtual=" + Thread.currentThread().isVirtual()));
        v.join();
        Thread p = Thread.ofPlatform().name("plat-1").start(() -> System.out.println("  inside: isVirtual=" + Thread.currentThread().isVirtual()));
        p.join();

        section("2. 5,000 blocking 200ms tasks");
        int n = 5_000;
        long vms;
        try (ExecutorService ex = Executors.newVirtualThreadPerTaskExecutor()) { vms = blockingTasks(ex, n, 200); }
        System.out.println("  virtual thread per task      : " + vms + " ms  (all tasks overlap; each parks cheaply while sleeping)");
        long pms;
        try (ExecutorService ex = Executors.newFixedThreadPool(200)) { pms = blockingTasks(ex, n, 200); }
        System.out.println("  fixed pool of 200 platform   : " + pms + " ms  (~ n/200 x 200ms = " + (n / 200 * 200) + " ms - bounded by the pool)");
        System.out.println("  => the win is THROUGHPUT FOR BLOCKING WORK without a callback/reactive programming style.");

        section("3. They are not faster at CPU-bound work");
        int cores = Runtime.getRuntime().availableProcessors();
        System.out.println("  cores=" + cores + ": 10,000 virtual threads doing pure computation still share " + cores + " carrier threads.");
        System.out.println("  Use a pool sized ~cores (or ForkJoin / parallel streams) for CPU-bound work.");

        section("4. Do not pool virtual threads - create one per task");
        System.out.println("  They are cheap (a few KB, heap-allocated stacks). Limit concurrency to a RESOURCE with a Semaphore, not with pool size:");
        Semaphore dbPermits = new Semaphore(3);
        AtomicInteger maxInside = new AtomicInteger(), inside = new AtomicInteger();
        try (ExecutorService ex = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 30; i++) ex.submit(() -> {
                dbPermits.acquire();
                try {
                    int now = inside.incrementAndGet();
                    maxInside.accumulateAndGet(now, Math::max);
                    Thread.sleep(20);
                    inside.decrementAndGet();
                } finally { dbPermits.release(); }
                return null;
            });
        }
        System.out.println("  30 tasks, max concurrent 'DB calls' observed = " + maxInside.get() + " (limit was 3)");

        section("5. Pinning: what to avoid");
        System.out.println("  A virtual thread is pinned to its carrier while inside a synchronized block (Java 21) or native frame.");
        System.out.println("  Blocking there parks the carrier too -> throughput collapses. Prefer ReentrantLock around blocking I/O.");
        System.out.println("  Diagnose with: -Djdk.tracePinnedThreads=full   (JDK 24 removed most synchronized pinning).");

        section("6. Spring Boot");
        System.out.println("  Boot 3.2+: spring.threads.virtual.enabled=true  -> Tomcat and @Async use virtual threads.");
        System.out.println("  Watch out for: ThreadLocal-heavy code (millions of copies), connection pools that are now the bottleneck.");
    }
}

// EXERCISE: replace the Semaphore with a fixed pool of 3 platform threads and compare the code and timings.
