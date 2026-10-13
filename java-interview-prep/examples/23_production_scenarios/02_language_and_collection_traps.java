/*
 * 02 - Production scenarios: language and collection traps that only show up under load or in prod
 *
 * Run:  java 02_language_and_collection_traps.java
 *
 * Interview angle: (Q11) shared static SimpleDateFormat returns wrong dates under load.
 * (Q12) Stream.toList() then list.add() throws. (Q13) two Long ids are == in tests, not in prod.
 * (Q16) list.remove() in a for-each throws ConcurrentModificationException on ONE thread.
 * (Q17) try-with-resources: body throws and close() throws: which one do you get?
 */
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;

class LanguageAndCollectionTraps {

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

    // ---------------------------------------------------------------- Q11
    static final SimpleDateFormat SHARED = new SimpleDateFormat("yyyy-MM-dd");
    static final DateTimeFormatter SAFE = DateTimeFormatter.ofPattern("yyyy-MM-dd");

    static void q11() throws Exception {
        section("Q11. shared static SimpleDateFormat returns wrong dates under load");
        final String input = "2024-03-15";
        final int threads = 8, perThread = 20_000;

        AtomicInteger wrongOrFailed = new AtomicInteger();
        runConcurrently(threads, () -> {
            for (int i = 0; i < perThread; i++) {
                try {
                    Date d = SHARED.parse(input);               // mutates the internal Calendar: not thread-safe
                    String back = new SimpleDateFormat("yyyy-MM-dd").format(d);
                    if (!input.equals(back)) wrongOrFailed.incrementAndGet();
                } catch (ParseException | RuntimeException e) {
                    wrongOrFailed.incrementAndGet();           // NumberFormatException, ArrayIndexOutOfBounds...
                }
            }
        });
        System.out.println("  shared SimpleDateFormat: " + wrongOrFailed.get() + " wrong/failed out of "
                + (threads * perThread) + " parses (non-deterministic; typically > 0 on a multi-core box)");

        AtomicInteger safeWrong = new AtomicInteger();
        runConcurrently(threads, () -> {
            for (int i = 0; i < perThread; i++) {
                LocalDate d = LocalDate.parse(input, SAFE);
                if (!input.equals(SAFE.format(d))) safeWrong.incrementAndGet();
            }
        });
        check("shared DateTimeFormatter (immutable): wrong results", 0, safeWrong.get());

        ThreadLocal<SimpleDateFormat> perThreadFmt = ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));
        AtomicInteger tlWrong = new AtomicInteger();
        runConcurrently(threads, () -> {
            for (int i = 0; i < perThread; i++) {
                try {
                    if (!input.equals(perThreadFmt.get().format(perThreadFmt.get().parse(input)))) tlWrong.incrementAndGet();
                } catch (ParseException e) { tlWrong.incrementAndGet(); }
            }
        });
        check("ThreadLocal<SimpleDateFormat> (legacy fix): wrong results", 0, tlWrong.get());
    }

    static void runConcurrently(int n, Runnable r) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(n);
        CountDownLatch go = new CountDownLatch(1);
        List<Future<?>> fs = new ArrayList<>();
        for (int i = 0; i < n; i++) fs.add(pool.submit(() -> { go.await(); r.run(); return null; }));
        go.countDown();
        for (Future<?> f : fs) f.get(60, TimeUnit.SECONDS);
        pool.shutdown();
    }

    // ---------------------------------------------------------------- Q12
    static void q12() {
        section("Q12. Stream.toList() then list.add() throws");
        List<Integer> fromToList = java.util.stream.Stream.of(1, 2, 3).toList();
        boolean threw = false;
        try { fromToList.add(4); } catch (UnsupportedOperationException e) { threw = true; }
        checkTrue("Stream.toList() (Java 16+) returns an UNMODIFIABLE list: add() throws", threw);

        threw = false;
        try { fromToList.set(0, 9); } catch (UnsupportedOperationException e) { threw = true; }
        checkTrue("set() throws too, not only add()", threw);

        List<Integer> fromCollector = java.util.stream.Stream.of(1, 2, 3).collect(Collectors.toList());
        fromCollector.add(4);
        check("Collectors.toList() happens to be a mutable ArrayList (spec gives no guarantee)", 4, fromCollector.size());

        List<String> withNull = java.util.stream.Stream.of("a", null).toList();
        check("Stream.toList() allows null elements", 2, withNull.size());
        boolean npe = false;
        try { List.of("a", null); } catch (NullPointerException e) { npe = true; }
        checkTrue("List.of(...) rejects null (different from Stream.toList)", npe);

        List<Integer> mutableCopy = new ArrayList<>(fromToList);
        mutableCopy.add(4);
        check("fix: new ArrayList<>(stream.toList()) or collect(toCollection(ArrayList::new))", List.of(1, 2, 3, 4), mutableCopy);
    }

    // ---------------------------------------------------------------- Q13
    static void q13() {
        section("Q13. two Long ids == in tests, not in production");
        Long small1 = 127L, small2 = 127L;
        Long big1 = 128L, big2 = 128L;
        check("127L == 127L (boxed values cached for -128..127)", true, small1 == small2);
        check("128L == 128L (two different Long objects)", false, big1 == big2);
        check("128L .equals(128L)", true, big1.equals(big2));
        check("new Long ids from a DB sequence in prod are > 127 so == is false; test ids were 1,2,3", false,
                Long.valueOf(1_000_001L) == Long.valueOf(1_000_001L));
        long prim = 128L;
        check("unboxing: long == Long compares by value", true, prim == big1);
        check("Objects.equals is the safe habit for entity ids", true, Objects.equals(big1, big2));
        check("Long.equals(Integer) is always false (different type)", false, Long.valueOf(5).equals(5));
    }

    // ---------------------------------------------------------------- Q16
    static void q16() {
        section("Q16. list.remove() inside for-each throws ConcurrentModificationException on ONE thread");
        List<Integer> four = new ArrayList<>(List.of(1, 2, 3, 4));
        boolean cme = false;
        try { for (Integer i : four) if (i == 2) four.remove(i); } catch (ConcurrentModificationException e) { cme = true; }
        checkTrue("remove during iteration -> CME (modCount != expectedModCount at next()). No second thread needed", cme);

        List<Integer> three = new ArrayList<>(List.of(1, 2, 3));
        for (Integer i : three) if (i == 2) three.remove(i);
        check("remove the SECOND-TO-LAST element: no exception, hasNext() sees size==cursor and quits", List.of(1, 3), three);

        List<Integer> viaIterator = new ArrayList<>(List.of(1, 2, 3, 4));
        for (Iterator<Integer> it = viaIterator.iterator(); it.hasNext(); ) if (it.next() % 2 == 0) it.remove();
        check("fix 1: Iterator.remove()", List.of(1, 3), viaIterator);

        List<Integer> viaRemoveIf = new ArrayList<>(List.of(1, 2, 3, 4));
        viaRemoveIf.removeIf(i -> i % 2 == 0);
        check("fix 2: removeIf (one pass, clearer)", List.of(1, 3), viaRemoveIf);

        List<Integer> cow = new java.util.concurrent.CopyOnWriteArrayList<>(List.of(1, 2, 3, 4));
        for (Integer i : cow) if (i == 2) cow.remove(i);
        check("fix 3 (only for read-mostly): CopyOnWriteArrayList iterates a snapshot", List.of(1, 3, 4), cow);
    }

    // ---------------------------------------------------------------- Q17
    static class Res implements AutoCloseable {
        final String name; final List<String> log;
        Res(String name, List<String> log) { this.name = name; this.log = log; }
        @Override public void close() { log.add("close " + name); throw new IllegalStateException("close-" + name); }
    }

    static void q17() {
        section("Q17. try-with-resources: body throws and close() throws too");
        List<String> log = new ArrayList<>();
        try (Res r = new Res("R", log)) {
            throw new RuntimeException("body");
        } catch (Exception e) {
            check("exception you catch is the BODY's", "body", e.getMessage());
            check("close()'s exception is attached as suppressed", "close-R", e.getSuppressed()[0].getMessage());
        }

        Exception masked = null;
        try {
            Res r = new Res("R", new ArrayList<>());
            try { throw new RuntimeException("body"); }
            finally { r.close(); }
        } catch (Exception e) { masked = e; }
        check("old try/finally: close()'s exception MASKS the body's (root cause lost)", "close-R", masked.getMessage());

        List<String> order = new ArrayList<>();
        try (Res a = new Res("A", order); Res b = new Res("B", order)) {
            // nothing
        } catch (Exception e) {
            check("with no body exception the FIRST close failure (B, closed first) is thrown", "close-B", e.getMessage());
            check("later close failures are suppressed on it", "close-A", e.getSuppressed()[0].getMessage());
        }
        check("resources close in REVERSE order of declaration", List.of("close B", "close A"), order);
    }

    public static void main(String[] args) throws Exception {
        q11();
        q12();
        q13();
        q16();
        q17();
        System.out.println("\nALL " + checks + " CHECKS PASSED");
    }
}
