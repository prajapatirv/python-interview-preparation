/*
 * 01 - Race conditions, volatile, atomics and locks
 *
 * Run:  java 01_race_volatile_atomic_locks.java
 *
 * Interview angle: "is count++ atomic?", "volatile vs synchronized", "AtomicInteger vs LongAdder",
 * "ReentrantLock vs synchronized", "what is the Java Memory Model guarantee?".
 */
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;
import java.util.concurrent.locks.*;

class RaceVolatileAtomicLocks {

    static int plain = 0;                                  // unsynchronised
    static int synced = 0;
    static final Object LOCK = new Object();
    static final AtomicInteger atomic = new AtomicInteger();
    static final LongAdder adder = new LongAdder();
    static final ReentrantLock rl = new ReentrantLock();
    static int locked = 0;
    static volatile int volatileCounter = 0;               // volatile does NOT make ++ atomic

    static final int THREADS = 8, PER_THREAD = 200_000;

    static long run(Runnable body) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch done = new CountDownLatch(THREADS);
        for (int t = 0; t < THREADS; t++) pool.submit(() -> {
            try { start.await(); } catch (InterruptedException e) { return; }
            for (int i = 0; i < PER_THREAD; i++) body.run();
            done.countDown();
        });
        long t0 = System.nanoTime();
        start.countDown();
        done.await();
        pool.shutdown();
        return (System.nanoTime() - t0) / 1_000_000;
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static volatile boolean stop = false;
    static boolean nonVolatileFlag = false;

    public static void main(String[] args) throws Exception {
        int expected = THREADS * PER_THREAD;
        System.out.println("expected total per strategy = " + expected);

        section("1. Five ways to increment a shared counter");
        long ms;
        ms = run(() -> plain++);
        System.out.printf("  plain int++        = %,d  (%d ms)  <- lost updates: read-modify-write is 3 steps%n", plain, ms);
        ms = run(() -> volatileCounter++);
        System.out.printf("  volatile int++     = %,d  (%d ms)  <- visibility yes, atomicity NO%n", volatileCounter, ms);
        ms = run(() -> { synchronized (LOCK) { synced++; } });
        System.out.printf("  synchronized       = %,d  (%d ms)%n", synced, ms);
        ms = run(() -> { rl.lock(); try { locked++; } finally { rl.unlock(); } });
        System.out.printf("  ReentrantLock      = %,d  (%d ms)%n", locked, ms);
        ms = run(atomic::incrementAndGet);
        System.out.printf("  AtomicInteger (CAS)= %,d  (%d ms)%n", atomic.get(), ms);
        ms = run(adder::increment);
        System.out.printf("  LongAdder          = %,d  (%d ms)  <- striped cells: best under heavy contention%n", adder.sum(), ms);

        section("2. volatile gives visibility and ordering (happens-before)");
        Thread reader = new Thread(() -> {
            long spins = 0;
            while (!stop) spins++;                          // sees the write because 'stop' is volatile
            System.out.println("  reader stopped cleanly after spinning");
        });
        reader.start();
        Thread.sleep(50);
        stop = true;
        reader.join(2000);
        System.out.println("  reader alive after join? " + reader.isAlive());
        System.out.println("  (with a NON-volatile flag the JIT may hoist the read and the loop can spin forever - never rely on it)");
        // EXPERIMENT: make 'stop' non-volatile and run with -Xint vs default JIT. Behaviour is allowed to differ.

        section("3. Compare-and-set loop (what AtomicInteger does internally)");
        AtomicInteger bal = new AtomicInteger(100);
        int prev, next;
        do { prev = bal.get(); next = prev - 30; } while (!bal.compareAndSet(prev, next));
        System.out.println("  balance after CAS withdraw = " + bal.get());
        System.out.println("  ABA problem: value goes A->B->A and CAS cannot tell; AtomicStampedReference adds a version.");

        section("4. tryLock avoids waiting forever");
        ReentrantLock a = new ReentrantLock();
        Thread holder = new Thread(() -> { a.lock(); try { sleep(300); } finally { a.unlock(); } });
        holder.start();
        Thread.sleep(50);
        boolean got = a.tryLock(100, TimeUnit.MILLISECONDS);
        System.out.println("  tryLock(100ms) while another thread holds it -> " + got + "  (back off / fail fast instead of blocking)");
        if (got) a.unlock();
        holder.join();

        section("5. Read-heavy data: ReadWriteLock / StampedLock");
        ReentrantReadWriteLock rw = new ReentrantReadWriteLock();
        rw.readLock().lock(); rw.readLock().lock();         // many readers allowed
        System.out.println("  concurrent read holds = " + rw.getReadLockCount() + ", write lock free? " + rw.writeLock().tryLock());
        rw.readLock().unlock(); rw.readLock().unlock();
    }

    static void sleep(long ms) { try { Thread.sleep(ms); } catch (InterruptedException e) { Thread.currentThread().interrupt(); } }
}

// EXERCISE: implement a thread-safe bounded counter that refuses to go above N using only CAS.
