/*
 * 01 - JVM memory in practice: GC beans, a classic leak, weak references, stack depth, String pool
 *
 * Run:  java 01_memory_leaks_gc_and_strings.java
 * Try:  java -Xmx64m -Xlog:gc 01_memory_leaks_gc_and_strings.java     (watch GC events)
 *
 * Interview angle: "what is a memory leak in a GC language?", "heap vs stack", "how do you
 * find a leak?", "equals vs == on Strings", "StackOverflowError vs OutOfMemoryError".
 */
import java.lang.management.*;
import java.lang.ref.*;
import java.util.*;

class MemoryLeaksGcAndStrings {

    static final Map<String, byte[]> LEAKY_CACHE = new HashMap<>();   // static + never evicted = classic leak

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static long usedMb() {
        Runtime r = Runtime.getRuntime();
        return (r.totalMemory() - r.freeMemory()) / (1024 * 1024);
    }

    static int depth = 0;
    static void recurse() { depth++; recurse(); }

    public static void main(String[] args) throws Exception {

        section("1. What the JVM is running with");
        for (GarbageCollectorMXBean gc : ManagementFactory.getGarbageCollectorMXBeans())
            System.out.println("  collector bean: " + gc.getName());
        MemoryUsage heap = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage();
        System.out.println("  max heap = " + heap.getMax() / (1024 * 1024) + " MB (default = 1/4 of RAM; set with -Xmx)");
        System.out.println("  Java 9+ default collector is G1 (region based, pause-time goal via -XX:MaxGCPauseMillis).");

        section("2. Allocation, garbage and GC activity");
        long before = totalGcCount();
        for (int i = 0; i < 2_000; i++) { byte[] shortLived = new byte[100_000]; if (shortLived.length == 0) System.out.println(); }
        long after = totalGcCount();
        System.out.println("  allocated ~200MB of short-lived arrays; young GCs triggered: " + (after - before));
        System.out.println("  Short-lived objects die in the young generation cheaply - that is the generational hypothesis.");

        section("3. A leak: objects stay reachable from a static map");
        System.gc();                                          // start from a clean baseline
        long base = usedMb();
        for (int i = 0; i < 40; i++) LEAKY_CACHE.put("key-" + i, new byte[1_000_000]);
        System.gc();
        System.out.println("  after adding 40MB to a static map and System.gc(): used grew by ~" + (usedMb() - base) + " MB (GC cannot free reachable objects)");
        LEAKY_CACHE.clear();
        System.gc();
        System.out.println("  after clear() + gc: used grew by ~" + Math.max(0, usedMb() - base) + " MB");
        System.out.println("  Common leak sources: static collections, unbounded caches, listeners never deregistered,");
        System.out.println("  ThreadLocal in pooled threads, un-closed resources, classloader leaks on redeploy.");

        section("4. Weak/soft references allow the GC to reclaim cache entries");
        WeakReference<byte[]> weak = new WeakReference<>(new byte[5_000_000]);
        System.gc();
        Thread.sleep(50);
        System.out.println("  WeakReference after gc -> " + (weak.get() == null ? "collected" : "still there"));
        WeakHashMap<Object, String> metadata = new WeakHashMap<>();
        Object k = new Object();
        metadata.put(k, "meta");
        k = null;
        System.gc();
        Thread.sleep(50);
        System.out.println("  WeakHashMap entry after key unreachable -> size " + metadata.size());
        System.out.println("  In real apps prefer Caffeine with size/time bounds over hand-rolled weak caches.");

        section("5. StackOverflowError: the stack is per thread and small (-Xss)");
        try { recurse(); } catch (StackOverflowError e) { System.out.println("  recursion depth reached ~" + depth + " frames before StackOverflowError"); }
        System.out.println("  OutOfMemoryError is a different problem: heap (or metaspace/direct memory/threads) exhausted.");

        section("6. String pool and ==");
        String a = "java", b = "java", c = new String("java"), d = new StringBuilder("ja").append("va").toString();
        System.out.println("  literal == literal           : " + (a == b));
        System.out.println("  literal == new String        : " + (a == c));
        System.out.println("  literal == built at runtime  : " + (a == d));
        System.out.println("  equals() always true         : " + a.equals(c) + "," + a.equals(d));
        System.out.println("  intern() returns pooled one  : " + (a == d.intern()));
        long t0 = System.nanoTime();
        String s = "";
        for (int i = 0; i < 5_000; i++) s += i;               // O(n^2) copying
        long concatMs = (System.nanoTime() - t0) / 1_000_000;
        t0 = System.nanoTime();
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 5_000; i++) sb.append(i);
        System.out.println("  += in a loop ~" + concatMs + " ms vs StringBuilder ~" + (System.nanoTime() - t0) / 1_000_000 + " ms (same result length: " + (s.length() == sb.length()) + ")");

        section("7. Production diagnosis cheat sheet");
        System.out.println("  jcmd <pid> GC.heap_info | jcmd <pid> Thread.print | jmap -dump:live,format=b,file=heap.hprof <pid>");
        System.out.println("  -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps   (always set in containers)");
        System.out.println("  -XX:MaxRAMPercentage=75 so the heap follows the container limit; -Xlog:gc*:file=gc.log");
        System.out.println("  Analyse the dump in Eclipse MAT: Dominator Tree -> 'path to GC roots' on the biggest retainer.");
    }

    static long totalGcCount() {
        long n = 0;
        for (GarbageCollectorMXBean gc : ManagementFactory.getGarbageCollectorMXBeans()) n += Math.max(0, gc.getCollectionCount());
        return n;
    }
}

// EXERCISE: run with -Xmx32m and remove the clear() call. Capture the OOM with
// -XX:+HeapDumpOnOutOfMemoryError and find the leaking map in a heap dump.
