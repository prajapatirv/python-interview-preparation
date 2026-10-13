/*
 * 01 - Production scenarios: thread pool sizing, deadlock from a thread dump, supplyAsync threads
 *
 * Run:  java 01_thread_pool_deadlock_and_async.java
 *
 * Interview angle: (Q1) core 10 / max 50 / unbounded queue and 10x traffic, how many threads run?
 * (Q2) two transfers A->B and B->A hang forever: prove it from a thread dump, then fix it with lock
 * ordering. (Q10) CompletableFuture.supplyAsync() with no executor: which threads run the task?
 * Every claim is asserted, so the printed behaviour is verified.
 */
import java.lang.management.ManagementFactory;
import java.lang.management.ThreadInfo;
import java.lang.management.ThreadMXBean;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;

class ThreadPoolDeadlockAndAsync {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }
    static void checkTrue(String label, boolean cond) {
        checks++;
        if (!cond) throw new AssertionError(label);
        System.out.println("  ok  " + label);
    }

    // ---------------------------------------------------------------- Q1
    static ThreadPoolExecutor blockedPool(BlockingQueue<Runnable> queue, int tasks, CountDownLatch release) {
        ThreadPoolExecutor pool = new ThreadPoolExecutor(10, 50, 60, TimeUnit.SECONDS, queue);
        for (int i = 0; i < tasks; i++) {
            try {
                pool.execute(() -> { try { release.await(); } catch (InterruptedException ignored) { } });
            } catch (RejectedExecutionException rejected) {
                // counted by the caller through pool state
            }
        }
        return pool;
    }

    static void q1() throws Exception {
        section("Q1. core=10, max=50, unbounded queue, traffic x10: how many threads?");

        CountDownLatch release = new CountDownLatch(1);
        ThreadPoolExecutor unbounded = blockedPool(new LinkedBlockingQueue<>(), 1_000, release);
        System.out.println("  unbounded LinkedBlockingQueue: submitted 1000 blocked tasks");
        System.out.println("    poolSize=" + unbounded.getPoolSize() + " largest=" + unbounded.getLargestPoolSize()
                + " queued=" + unbounded.getQueue().size());
        check("threads never exceed core (max=50 is dead config)", 10, unbounded.getLargestPoolSize());
        check("everything else waits in the queue", 990, unbounded.getQueue().size());
        release.countDown();
        unbounded.shutdown();

        CountDownLatch release2 = new CountDownLatch(1);
        ThreadPoolExecutor bounded = new ThreadPoolExecutor(10, 50, 60, TimeUnit.SECONDS, new ArrayBlockingQueue<>(20));
        int rejected = 0;
        for (int i = 0; i < 100; i++) {
            try {
                bounded.execute(() -> { try { release2.await(); } catch (InterruptedException ignored) { } });
            } catch (RejectedExecutionException e) { rejected++; }
        }
        System.out.println("  bounded ArrayBlockingQueue(20): submitted 100 blocked tasks");
        System.out.println("    poolSize=" + bounded.getPoolSize() + " queued=" + bounded.getQueue().size()
                + " rejected=" + rejected);
        check("threads grow to max only AFTER the queue is full", 50, bounded.getLargestPoolSize());
        check("10 core + 20 queued + 40 extra = 70 accepted, 30 rejected", 30, rejected);
        release2.countDown();
        bounded.shutdown();
        System.out.println("  rule: core -> queue -> (only if queue full) up to max -> reject.");
    }

    // ---------------------------------------------------------------- Q2
    static class Account {
        final long id;
        long balance;
        Account(long id, long balance) { this.id = id; this.balance = balance; }
    }

    /** Naive: locks "from" then "to" in argument order: A->B and B->A cross. */
    static void transferNaive(Account from, Account to, long amt, CountDownLatch bothHoldFirst) throws InterruptedException {
        synchronized (from) {
            bothHoldFirst.countDown();
            bothHoldFirst.await();           // widens the race window so the demo is deterministic
            synchronized (to) { from.balance -= amt; to.balance += amt; }
        }
    }

    /** Fixed: always lock the lower id first, regardless of direction. */
    static void transferOrdered(Account from, Account to, long amt) {
        Account first = from.id < to.id ? from : to;
        Account second = first == from ? to : from;
        synchronized (first) {
            synchronized (second) { from.balance -= amt; to.balance += amt; }
        }
    }

    static void q2() throws Exception {
        section("Q2. A->B and B->A hang forever: prove it from a thread dump");
        Account a = new Account(1, 100), b = new Account(2, 100);
        CountDownLatch bothHoldFirst = new CountDownLatch(2);
        Thread t1 = new Thread(() -> { try { transferNaive(a, b, 10, bothHoldFirst); } catch (InterruptedException ignored) { } }, "transfer-A-to-B");
        Thread t2 = new Thread(() -> { try { transferNaive(b, a, 10, bothHoldFirst); } catch (InterruptedException ignored) { } }, "transfer-B-to-A");
        t1.setDaemon(true); t2.setDaemon(true);
        t1.start(); t2.start();

        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        long[] ids = null;
        for (int i = 0; i < 100 && ids == null; i++) {      // poll up to ~2 s
            Thread.sleep(20);
            ids = mx.findDeadlockedThreads();
        }
        checkTrue("JVM reports a deadlock (this is what jstack prints as 'Found one Java-level deadlock')", ids != null);
        check("two threads are in the cycle", 2, ids.length);
        for (ThreadInfo ti : mx.getThreadInfo(ids)) {
            System.out.println("    " + ti.getThreadName() + " state=" + ti.getThreadState());
            System.out.println("      waiting for   " + ti.getLockName().replaceAll("@[0-9a-f]+", "@<id>"));
            System.out.println("      which is held by " + ti.getLockOwnerName());
        }
        Set<String> names = new HashSet<>();
        for (ThreadInfo ti : mx.getThreadInfo(ids)) {
            names.add(ti.getThreadName());
            check(ti.getThreadName() + " is BLOCKED (not RUNNABLE: zero CPU, that is the tell)", Thread.State.BLOCKED, ti.getThreadState());
        }
        checkTrue("the cycle is exactly the two transfer threads",
                names.equals(Set.of("transfer-A-to-B", "transfer-B-to-A")));

        // fix: global lock order
        Account c = new Account(1, 100), d = new Account(2, 100);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < 20_000; i++) {
            fs.add(pool.submit(() -> transferOrdered(c, d, 1)));
            fs.add(pool.submit(() -> transferOrdered(d, c, 1)));
        }
        for (Future<?> f : fs) f.get(10, TimeUnit.SECONDS);
        pool.shutdown();
        check("ordered locking: 40,000 opposite transfers finish, no deadlock, money conserved", 200L, c.balance + d.balance);
        check("net effect of 20,000 each way is zero", 100L, c.balance);
    }

    // ---------------------------------------------------------------- Q10
    static void q10() throws Exception {
        section("Q10. CompletableFuture.supplyAsync() with no executor: which threads?");
        int parallelism = ForkJoinPool.commonPool().getParallelism();
        System.out.println("  commonPool parallelism=" + parallelism + " (availableProcessors-1)");

        String[] info = new String[2];
        CompletableFuture.supplyAsync(() -> {
            Thread t = Thread.currentThread();
            info[0] = t.getName();
            info[1] = String.valueOf(t.isDaemon());
            return "x";
        }).get();
        System.out.println("  default executor ran on: " + info[0] + " daemon=" + info[1]);
        if (parallelism > 1) {
            checkTrue("runs on ForkJoinPool.commonPool-worker-N", info[0].startsWith("ForkJoinPool.commonPool-worker-"));
            check("common pool workers are DAEMON threads (JVM can exit mid-task)", "true", info[1]);
        } else {
            System.out.println("  (1-CPU box: JDK falls back to a new thread per task, skipping the name check)");
        }

        // blocking work in the common pool starves everyone else (also parallel streams, CompletableFuture)
        int blockers = Math.max(parallelism, 1);
        CountDownLatch release = new CountDownLatch(1);
        List<CompletableFuture<Void>> hogs = new ArrayList<>();
        for (int i = 0; i < blockers; i++)
            hogs.add(CompletableFuture.runAsync(() -> { try { release.await(); } catch (InterruptedException ignored) { } }));
        Thread.sleep(100);
        CompletableFuture<String> victim = CompletableFuture.supplyAsync(() -> "never ran while pool was hogged");
        boolean starved = false;
        if (parallelism > 1) {
            try { victim.get(300, TimeUnit.MILLISECONDS); } catch (TimeoutException e) { starved = true; }
            checkTrue("unrelated task starves while blocking calls hold every common-pool thread", starved);
        }
        release.countDown();
        victim.get(2, TimeUnit.SECONDS);
        for (CompletableFuture<Void> h : hogs) h.get(2, TimeUnit.SECONDS);

        ExecutorService io = Executors.newFixedThreadPool(4, r -> { Thread t = new Thread(r, "io-pool-" + System.nanoTime() % 1000); return t; });
        String name = CompletableFuture.supplyAsync(() -> Thread.currentThread().getName(), io).get();
        checkTrue("dedicated executor: task runs on your pool (" + name + ")", name.startsWith("io-pool-"));
        io.shutdown();
        System.out.println("  rule: pass an executor for any blocking / IO work; the common pool is for CPU-bound work.");
    }

    public static void main(String[] args) throws Exception {
        q1();
        q2();
        q10();
        System.out.println("\nALL " + checks + " CHECKS PASSED");
    }
}
