/*
 * 03 - Deadlock: create it, detect it programmatically, fix it
 *
 * Run:  java 03_deadlock_detection_and_fix.java
 *
 * Interview angle: "four conditions for deadlock", "how do you find one in production?"
 * (jstack / thread dump / ThreadMXBean), "how do you prevent it?" (lock ordering, tryLock, timeouts).
 */
import java.lang.management.*;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.locks.*;

class DeadlockDetectionAndFix {

    static final Object A = new Object();
    static final Object B = new Object();

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }

    static class Account {
        final int id; long balance;
        final ReentrantLock lock = new ReentrantLock();
        Account(int id, long balance) { this.id = id; this.balance = balance; }
    }

    /** FIX 1: always acquire locks in a global order (by id). */
    static void transferOrdered(Account from, Account to, long amt) {
        Account first = from.id < to.id ? from : to, second = first == from ? to : from;
        first.lock.lock();
        try {
            sleep(20);
            second.lock.lock();
            try { from.balance -= amt; to.balance += amt; } finally { second.lock.unlock(); }
        } finally { first.lock.unlock(); }
    }

    /** FIX 2: tryLock with timeout and back off, so no thread waits forever. */
    static boolean transferTry(Account from, Account to, long amt) throws InterruptedException {
        if (from.lock.tryLock(100, TimeUnit.MILLISECONDS)) {
            try {
                sleep(20);
                if (to.lock.tryLock(100, TimeUnit.MILLISECONDS)) {
                    try { from.balance -= amt; to.balance += amt; return true; } finally { to.lock.unlock(); }
                }
            } finally { from.lock.unlock(); }
        }
        return false;                                           // caller retries with jitter
    }

    public static void main(String[] args) throws Exception {

        section("1. Create a classic lock-ordering deadlock");
        Thread t1 = new Thread(() -> { synchronized (A) { sleep(100); synchronized (B) { System.out.println("never printed"); } } }, "T1-holds-A-wants-B");
        Thread t2 = new Thread(() -> { synchronized (B) { sleep(100); synchronized (A) { System.out.println("never printed"); } } }, "T2-holds-B-wants-A");
        t1.setDaemon(true); t2.setDaemon(true);                 // daemon so the JVM can still exit
        t1.start(); t2.start();
        sleep(400);

        section("2. Detect it with ThreadMXBean (same data as jstack / kill -3)");
        ThreadMXBean mx = ManagementFactory.getThreadMXBean();
        long[] ids = mx.findDeadlockedThreads();
        System.out.println("  deadlocked thread count = " + (ids == null ? 0 : ids.length));
        if (ids != null) {
            for (ThreadInfo ti : mx.getThreadInfo(ids)) {
                System.out.println("  " + ti.getThreadName() + " is BLOCKED on " + ti.getLockName() + " owned by " + ti.getLockOwnerName());
            }
        }
        System.out.println("  In production: jstack <pid> (or Thread.print via jcmd) prints 'Found one Java-level deadlock'.");
        System.out.println("  Take 3 dumps 10s apart; threads stuck at the same frame are the culprits.");

        section("3. The four Coffman conditions (break any one to prevent deadlock)");
        System.out.println("  mutual exclusion | hold-and-wait | no preemption | circular wait");
        System.out.println("  lock ordering breaks circular wait; tryLock/timeout breaks hold-and-wait/no preemption.");

        section("4. Fix 1: consistent lock ordering (two opposite transfers, no deadlock)");
        Account x = new Account(1, 1_000), y = new Account(2, 1_000);
        ExecutorService pool = Executors.newFixedThreadPool(2);
        Future<?> f1 = pool.submit(() -> transferOrdered(x, y, 100));
        Future<?> f2 = pool.submit(() -> transferOrdered(y, x, 50));
        f1.get(2, TimeUnit.SECONDS); f2.get(2, TimeUnit.SECONDS);
        System.out.println("  balances x=" + x.balance + " y=" + y.balance + " (sum preserved = " + (x.balance + y.balance) + ")");

        section("5. Fix 2: tryLock with timeout");
        Account p = new Account(10, 500), q = new Account(11, 500);
        Future<Boolean> g1 = pool.submit(() -> transferTry(p, q, 10));
        Future<Boolean> g2 = pool.submit(() -> transferTry(q, p, 20));
        System.out.println("  results: " + g1.get() + ", " + g2.get() + "  (false = backed off; retry with jitter)");
        pool.shutdownNow();

        section("6. Related liveness problems");
        System.out.println("  livelock  : threads keep reacting to each other and make no progress (fix: randomised back-off)");
        System.out.println("  starvation: a thread never gets the lock/CPU (fix: fair locks, priorities-free design)");
        System.out.println("  Also avoid calling alien/overridable methods while holding a lock.");
    }
}

// EXERCISE: dining philosophers with 5 locks - make it deadlock, then fix it two different ways.
