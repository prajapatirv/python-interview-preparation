/*
 * 05 - Data wrangling with streams: the pandas operations, done in Java
 *
 * Run:  java 05_data_wrangling_with_streams.java
 *
 * Interview angle: "process this list of orders: handle missing values, remove duplicates, total per
 * customer, join with the customer table" - the Java twin of
 * python/python-interview-prep/03_pandas_data_handling (see shared/cross-stack-pairs.md). Each section
 * names the pandas call it mirrors, so a Python interviewer and a Java one get the same answer.
 */
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

class DataWranglingWithStreams {

    record Order(int id, String customer, Double amount, String region) { }
    record Customer(String id, String name, String tier) { }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static final List<Order> ORDERS = List.of(
            new Order(1, "c1", 120.0, "EU"),
            new Order(2, "c2", 80.0, "US"),
            new Order(2, "c2", 80.0, "US"),          // re-delivered message: same order twice
            new Order(3, "c1", null, "EU"),          // amount unknown (a failed price lookup)
            new Order(4, "c3", 45.5, null),          // region unknown
            new Order(5, "c4", 300.0, "US"),
            new Order(6, "c2", 20.0, "US"));

    static final List<Customer> CUSTOMERS = List.of(
            new Customer("c1", "Asha", "gold"),
            new Customer("c2", "Ben", "silver"),
            new Customer("c3", "Chen", "silver"),
            new Customer("c9", "Dara", "gold"));      // a customer with no orders

    public static void main(String[] args) {

        section("1. Missing data: count first, then decide by MEANING (df.isna().sum(), fillna, dropna)");
        long noAmount = ORDERS.stream().filter(o -> o.amount() == null).count();
        long noRegion = ORDERS.stream().filter(o -> o.region() == null).count();
        System.out.println("  missing amount: " + noAmount + ", missing region: " + noRegion);
        List<Order> priced = ORDERS.stream().filter(o -> o.amount() != null).toList();          // dropna(subset=["amount"])
        List<Order> withRegion = ORDERS.stream()
                .map(o -> o.region() == null ? new Order(o.id(), o.customer(), o.amount(), "UNKNOWN") : o)
                .toList();                                                                        // fillna({"region": "UNKNOWN"})
        System.out.println("  drop rows with no amount (an unknown price is NOT a price of 0): " + priced.size() + " rows");
        System.out.println("  fill a missing region with UNKNOWN (keeps the row in the counts): "
                + withRegion.stream().filter(o -> o.region().equals("UNKNOWN")).count() + " filled");
        System.out.println("  Filling amount with 0 would silently understate revenue: decide per column.");

        section("2. Duplicates: keep the first per key (df.drop_duplicates(subset=['id']))");
        Collection<Order> unique = ORDERS.stream()
                .collect(Collectors.toMap(Order::id, o -> o, (first, dup) -> first, LinkedHashMap::new))
                .values();
        System.out.println("  " + ORDERS.size() + " rows -> " + unique.size() + " unique order ids (insertion order kept)");
        System.out.println("  Without the merge function, toMap throws IllegalStateException on the duplicate key.");

        section("3. Aggregate vs transform (groupby().agg() vs groupby().transform())");
        List<Order> clean = unique.stream().filter(o -> o.amount() != null).toList();
        Map<String, Double> total = clean.stream().collect(
                Collectors.groupingBy(Order::customer, TreeMap::new, Collectors.summingDouble(Order::amount)));
        System.out.println("  agg (one row per group)      : " + total);
        Map<String, DoubleSummaryStatistics> stats = clean.stream().collect(
                Collectors.groupingBy(Order::customer, TreeMap::new, Collectors.summarizingDouble(Order::amount)));
        stats.forEach((c, s) -> System.out.printf("    %s: count=%d sum=%.1f mean=%.1f max=%.1f%n", c, s.getCount(), s.getSum(), s.getAverage(), s.getMax()));
        System.out.println("  transform (keeps every row, adds the group value):");
        for (Order o : clean) {
            double share = o.amount() / total.get(o.customer());
            System.out.printf("    order %d %s %.1f -> %.0f%% of %s's total%n", o.id(), o.customer(), o.amount(), share * 100, o.customer());
        }

        section("4. Join with an indicator (pd.merge(..., how='outer', indicator=True))");
        Map<String, Customer> byId = CUSTOMERS.stream().collect(Collectors.toMap(Customer::id, Function.identity()));
        Set<String> withOrders = clean.stream().map(Order::customer).collect(Collectors.toCollection(TreeSet::new));
        for (String c : withOrders) {
            Customer cu = byId.get(c);
            System.out.println("  " + c + "  " + (cu == null ? "left_only   (an order for an unknown customer: a data-quality bug)"
                    : "both        " + cu.name() + " (" + cu.tier() + ") total " + total.get(c)));
        }
        CUSTOMERS.stream().filter(cu -> !withOrders.contains(cu.id()))
                .forEach(cu -> System.out.println("  " + cu.id() + "  right_only  " + cu.name() + " has no orders"));
        System.out.println("  The indicator is what makes a join auditable: count each kind before trusting the result.");

        section("5. Pivot: total by region and tier (df.pivot_table(index='region', columns='tier'))");
        Map<String, Map<String, Double>> pivot = clean.stream()
                .filter(o -> byId.containsKey(o.customer()))
                .collect(Collectors.groupingBy(o -> o.region() == null ? "UNKNOWN" : o.region(), TreeMap::new,
                        Collectors.groupingBy(o -> byId.get(o.customer()).tier(), TreeMap::new, Collectors.summingDouble(Order::amount))));
        pivot.forEach((region, row) -> System.out.println("  " + region + " " + row));

        section("6. When the data is big");
        System.out.println("  boxing   : Stream<Double> allocates an object per value; mapToDouble(...).sum() does not");
        System.out.println("  laziness : Files.lines(path) streams a CSV line by line; nothing is loaded until the terminal op");
        System.out.println("  parallel : .parallel() helps only for big CPU-bound work with no shared state - measure first");
        System.out.println("  beyond one machine: Spark (Java/Scala API) or the database; see 16_system_design/03 for streaming files");
        System.out.println("  Python contrast: pandas is columnar and vectorized (NumPy), so a column sum often beats a Python");
        System.out.println("  loop by 10-100x; Java streams are already JIT-compiled loops, so the gap is about allocation.");
    }
}

// EXERCISE: add a "rolling 2-order total per customer" (pandas: groupby().rolling(2).sum()) - sort by
// id within each customer and keep a running window of the last two amounts.
