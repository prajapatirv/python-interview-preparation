/*
 * 08 - Reported rounds: coin change, nearest-sum pair, joiners per month, proxies, a parallel Collector
 *
 * Run:  java 08_reported_rounds_coding_and_internals.java
 *
 * Interview angle: the hands-on questions from the Virtusa, Capgemini and Deloitte reports. Least
 * coins for a target, the pair whose sum is nearest a target, employees joined per month in month
 * order, an immutable class, Strategy with Factory, how a dynamic proxy works, why PECS, a custom
 * Collector that stays correct in parallel, and the four lock choices. Answers: banks 97 and 98.
 */
import java.lang.reflect.*;
import java.time.*;
import java.util.*;
import java.util.concurrent.locks.*;
import java.util.function.*;
import java.util.stream.*;

class ReportedRounds {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    /** Least coins to reach target with unlimited use of each coin; -1 when impossible. O(target * coins) time, O(target) space. */
    static int minCoins(int[] coins, int target) {
        if (target < 0) throw new IllegalArgumentException("target must be >= 0");
        int unreachable = target + 1;                     // more than the worst case of all 1s, and safe from overflow
        int[] best = new int[target + 1];
        Arrays.fill(best, unreachable);
        best[0] = 0;
        for (int amount = 1; amount <= target; amount++)
            for (int coin : coins)
                if (coin > 0 && coin <= amount) best[amount] = Math.min(best[amount], best[amount - coin] + 1);
        return best[target] == unreachable ? -1 : best[target];
    }

    /** The greedy "largest coin first" answer, kept here to show the counter-example. */
    static int greedyCoins(int[] coins, int target) {
        int[] desc = Arrays.stream(coins).boxed().sorted(Comparator.reverseOrder()).mapToInt(i -> i).toArray();
        int used = 0;
        for (int c : desc) { used += target / c; target %= c; }
        return target == 0 ? used : -1;
    }

    /** Pair whose sum is nearest target. Sort, then two pointers: O(n log n) time. Each element is used once. */
    static int[] nearestPair(int[] input, int target) {
        if (input.length < 2) throw new IllegalArgumentException("need at least two numbers");
        int[] a = input.clone();
        Arrays.sort(a);
        int lo = 0, hi = a.length - 1, bestLo = 0, bestHi = a.length - 1;
        long bestGap = Long.MAX_VALUE;
        while (lo < hi) {
            long sum = (long) a[lo] + a[hi];                 // long, because two large ints overflow
            long gap = Math.abs(sum - target);
            if (gap < bestGap) { bestGap = gap; bestLo = lo; bestHi = hi; }
            if (sum == target) break;
            if (sum < target) lo++; else hi--;
        }
        return new int[] { a[bestLo], a[bestHi] };
    }

    record Hire(String name, LocalDate joined) {}

    /** Immutable: final class, final fields, a defensive copy in, an unmodifiable view out. */
    static final class Money {
        private final long paise;
        private final List<String> tags;
        Money(long paise, List<String> tags) { this.paise = paise; this.tags = List.copyOf(tags); }
        long paise() { return paise; }
        List<String> tags() { return tags; }
        Money plus(long more) { return new Money(paise + more, tags); }
    }

    /** Strategy: the rule varies. Factory: one place decides which rule. Adding a type is one enum line. */
    interface Fee { long on(long amount); }
    enum Channel {
        UPI(a -> 0), CARD(a -> a * 2 / 100), WIRE(a -> 2_500);
        final Fee fee;
        Channel(Fee fee) { this.fee = fee; }
    }
    static Fee feeFor(String channel) { return Channel.valueOf(channel.toUpperCase()).fee; }

    /** What Spring's @Transactional proxy does, in miniature: same interface, advice around the real call. */
    interface OrderService { String place(String item); }
    static class RealOrderService implements OrderService {
        public String place(String item) { return "placed " + item; }
    }
    @SuppressWarnings("unchecked")
    static <T> T traced(T target, Class<T> type, List<String> log) {
        InvocationHandler handler = (proxy, method, args) -> {
            log.add("begin " + method.getName());
            try {
                Object result = method.invoke(target, args);
                log.add("commit " + method.getName());
                return result;
            } catch (InvocationTargetException e) {
                log.add("rollback " + method.getName());
                throw e.getCause();                          // unwrap, or callers see the reflection wrapper
            }
        };
        return (T) Proxy.newProxyInstance(type.getClassLoader(), new Class<?>[] { type }, handler);
    }

    /** PECS: read from a producer of T (extends), write to a consumer of T (super). */
    static <T> void copyAll(Collection<? extends T> producer, Collection<? super T> consumer) { consumer.addAll(producer); }

    /** A custom Collector safe in parallel: each thread owns its accumulator, and the combiner merges them. */
    static final class Stats {
        long count; double sum; double max = Double.NEGATIVE_INFINITY;
        void add(double v) { count++; sum += v; max = Math.max(max, v); }
        Stats merge(Stats o) { count += o.count; sum += o.sum; max = Math.max(max, o.max); return this; }
    }
    static Collector<Double, Stats, Stats> toStats() {
        return Collector.of(Stats::new, Stats::add, Stats::merge, Collector.Characteristics.UNORDERED,
                            Collector.Characteristics.IDENTITY_FINISH);
    }

    /** StampedLock's optimistic read: no lock taken, validated afterwards, retried under a real read lock. */
    static final class Point {
        private final StampedLock lock = new StampedLock();
        private double x, y;
        void move(double nx, double ny) {
            long stamp = lock.writeLock();
            try { x = nx; y = ny; } finally { lock.unlockWrite(stamp); }
        }
        double sumOfCoordinates() {
            long stamp = lock.tryOptimisticRead();
            double cx = x, cy = y;
            if (!lock.validate(stamp)) {
                stamp = lock.readLock();
                try { cx = x; cy = y; } finally { lock.unlockRead(stamp); }
            }
            return cx + cy;
        }
    }

    public static void main(String[] args) throws Exception {
        section("1. Least coins for a target, each coin reusable (bank 98 Q1)");
        check("1,2,5 for 11", 3, minCoins(new int[] {1, 2, 5}, 11));
        check("target 0 needs no coins", 0, minCoins(new int[] {2}, 0));
        check("impossible returns -1", -1, minCoins(new int[] {2}, 3));
        check("greedy gives 3 coins for 1,3,4 target 6", 3, greedyCoins(new int[] {1, 3, 4}, 6));
        check("the true minimum is 2 (3+3): greedy is wrong", 2, minCoins(new int[] {1, 3, 4}, 6));

        section("2. Pair whose sum is nearest a target (bank 98 Q2)");
        check("nearest to 54", List.of(22, 30), Arrays.stream(nearestPair(new int[] {10, 22, 28, 29, 30, 40}, 54)).boxed().toList());
        check("exact match", List.of(1, 4), Arrays.stream(nearestPair(new int[] {4, 1, 7}, 5)).boxed().toList());
        check("negatives", List.of(-80, 85), Arrays.stream(nearestPair(new int[] {-80, -10, 1, 60, 70, 85}, 0)).boxed().toList());
        check("no int overflow", List.of(2_000_000_000, 2_000_000_001),
              Arrays.stream(nearestPair(new int[] {2_000_000_000, 2_000_000_001}, 2_147_483_647)).boxed().toList());

        section("3. Employees per month, in month order (bank 98 Q3)");
        List<Hire> hires = List.of(new Hire("A", LocalDate.of(2024, 3, 5)), new Hire("B", LocalDate.of(2023, 1, 9)),
                                   new Hire("C", LocalDate.of(2024, 3, 21)), new Hire("D", LocalDate.of(2024, 1, 2)));
        check("extract the month", Month.MARCH, hires.get(0).joined().getMonth());
        check("count by month name mixes years", new TreeMap<>(Map.of(Month.JANUARY, 2L, Month.MARCH, 2L)),
              hires.stream().collect(Collectors.groupingBy(h -> h.joined().getMonth(), TreeMap::new, Collectors.counting())));
        check("count by YearMonth separates them", "{2023-01=1, 2024-01=1, 2024-03=2}",
              hires.stream().collect(Collectors.groupingBy(h -> YearMonth.from(h.joined()), TreeMap::new, Collectors.counting())).toString());
        check("employees per month in calendar order", "{2023-01=[B], 2024-01=[D], 2024-03=[A, C]}",
              hires.stream().collect(Collectors.groupingBy(h -> YearMonth.from(h.joined()), TreeMap::new,
                                     Collectors.mapping(Hire::name, Collectors.toList()))).toString());

        section("4. Immutable class (bank 98 Q9)");
        List<String> tags = new ArrayList<>(List.of("salary"));
        Money money = new Money(100, tags);
        tags.add("bonus");
        check("a later change to the caller's list cannot reach inside", List.of("salary"), money.tags());
        try { money.tags().add("x"); throw new AssertionError(); }
        catch (UnsupportedOperationException e) { check("the exposed list refuses writes", "UnsupportedOperationException", e.getClass().getSimpleName()); }
        check("change returns a new object", 150L, money.plus(50).paise());
        check("the original is untouched", 100L, money.paise());

        section("5. Strategy with Factory (bank 98 Q11)");
        check("UPI is free", 0L, feeFor("upi").on(10_000));
        check("card is 2 percent", 200L, feeFor("card").on(10_000));
        check("wire is flat", 2_500L, feeFor("wire").on(10_000));

        section("6. Reflection and dynamic proxies (bank 97 Q1)");
        List<String> log = new ArrayList<>();
        OrderService service = traced(new RealOrderService(), OrderService.class, log);
        check("the proxy forwards the call", "placed pen", service.place("pen"));
        check("the advice ran around it", List.of("begin place", "commit place"), log);
        check("the proxy is a generated class, not ours", true, Proxy.isProxyClass(service.getClass()));
        check("reflection can read metadata by name", "place", OrderService.class.getMethod("place", String.class).getName());

        section("7. PECS (bank 97 intro)");
        List<Integer> ints = List.of(1, 2);
        List<Number> numbers = new ArrayList<>(List.of(0.5));
        ReportedRounds.<Number>copyAll(ints, numbers);
        check("Integers flow into a List<Number>", List.of(0.5, 1, 2), numbers);

        section("8. A custom Collector that is correct in parallel (bank 97 Q2)");
        List<Double> values = IntStream.rangeClosed(1, 1_000_000).mapToDouble(i -> i).boxed().toList();
        Stats seq = values.stream().collect(toStats());
        Stats par = values.parallelStream().collect(toStats());
        check("sequential count", 1_000_000L, seq.count);
        check("parallel count matches", seq.count, par.count);
        check("parallel sum matches", seq.sum, par.sum);
        check("parallel max matches", seq.max, par.max);

        section("9. Lock choices (bank 97 Q3)");
        Point p = new Point();
        p.move(3, 4);
        check("StampedLock optimistic read", 7.0, p.sumOfCoordinates());
        ReentrantLock timed = new ReentrantLock();
        timed.lock();
        Thread other = new Thread(() -> {
            try { check("ReentrantLock can give up instead of hanging", false, timed.tryLock(10, java.util.concurrent.TimeUnit.MILLISECONDS)); }
            catch (InterruptedException e) { Thread.currentThread().interrupt(); }
        });
        other.start(); other.join();
        timed.unlock();
        ReadWriteLock rw = new ReentrantReadWriteLock();
        rw.readLock().lock();
        check("two readers can hold a ReadWriteLock", true, rw.readLock().tryLock());
        rw.readLock().unlock(); rw.readLock().unlock();

        System.out.println("\nAll " + checks + " checks passed.");
    }
}
