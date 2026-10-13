/*
 * 02 - Consumer groups, assignment strategies, rebalancing, committed offsets and lag
 *
 * Run:  java 02_consumer_groups_rebalancing_and_lag.java
 *
 * A deterministic, in-memory model of the group protocol: it reproduces the behaviours you are
 * asked about (idle consumers, range vs round-robin imbalance, eager vs cooperative rebalance,
 * crash -> reprocessing from the committed offset, lag growth and drain, hot partition).
 */
import java.util.*;
import java.util.stream.*;

class ConsumerGroupsRebalancingAndLag {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    /** partition id like "orders-2" -> owner consumer. */
    static Map<String, String> range(List<String> topics, int partitionsPerTopic, List<String> consumers) {
        Map<String, String> out = new LinkedHashMap<>();
        List<String> sorted = new ArrayList<>(consumers); Collections.sort(sorted);
        for (String t : topics) {                                    // per topic: contiguous ranges, first consumers get the remainder
            int per = partitionsPerTopic / sorted.size(), extra = partitionsPerTopic % sorted.size(), p = 0;
            for (int c = 0; c < sorted.size(); c++) {
                int count = per + (c < extra ? 1 : 0);
                for (int i = 0; i < count; i++) out.put(t + "-" + p++, sorted.get(c));
            }
        }
        return out;
    }

    static Map<String, String> roundRobin(List<String> topics, int partitionsPerTopic, List<String> consumers) {
        Map<String, String> out = new LinkedHashMap<>();
        List<String> sorted = new ArrayList<>(consumers); Collections.sort(sorted);
        int i = 0;
        for (String t : topics) for (int p = 0; p < partitionsPerTopic; p++) out.put(t + "-" + p, sorted.get(i++ % sorted.size()));
        return out;
    }

    static String describe(Map<String, String> assignment, List<String> consumers) {
        StringBuilder sb = new StringBuilder();
        for (String c : consumers) {
            List<String> ps = assignment.entrySet().stream().filter(e -> e.getValue().equals(c)).map(Map.Entry::getKey).collect(Collectors.toList());
            sb.append(String.format("%n    %-3s %d partition(s) %s", c, ps.size(), ps));
        }
        return sb.toString();
    }

    public static void main(String[] args) {

        section("1. One group, 6 partitions: consumers beyond the partition count sit idle");
        for (int n : new int[]{1, 3, 6, 8}) {
            List<String> cs = new ArrayList<>();
            for (int i = 1; i <= n; i++) cs.add("c" + i);
            Map<String, String> a = roundRobin(Collections.singletonList("orders"), 6, cs);
            long active = a.values().stream().distinct().count();
            System.out.println("  " + n + " consumer(s): " + active + " active, " + (n - active) + " idle, max partitions per consumer = "
                    + a.values().stream().collect(Collectors.groupingBy(x -> x, Collectors.counting())).values().stream().max(Long::compare).get());
        }
        System.out.println("  Max useful parallelism of a group = number of partitions. Different groups each get ALL records.");

        section("2. Range vs RoundRobin with two topics of 3 partitions and 2 consumers");
        List<String> two = Arrays.asList("c1", "c2");
        List<String> topics = Arrays.asList("orders", "payments");
        System.out.println("  RangeAssignor:" + describe(range(topics, 3, two), two));
        System.out.println("  RoundRobinAssignor:" + describe(roundRobin(topics, 3, two), two));
        System.out.println("  Range works per topic, so the first consumer collects the remainder of EVERY topic (4 vs 2).");
        System.out.println("  Prefer CooperativeStickyAssignor: balanced AND keeps partitions where they were (fewer moves).");

        section("3. Rebalance cost: eager (stop-the-world) vs cooperative incremental");
        Map<String, String> before = roundRobin(Collections.singletonList("orders"), 6, Arrays.asList("c1", "c2"));
        Map<String, String> after = stickyAdd(before, "c3", 6);
        long moved = before.entrySet().stream().filter(e -> !e.getValue().equals(after.get(e.getKey()))).count();
        System.out.println("  c3 joins a group of {c1,c2} owning 6 partitions");
        System.out.println("  eager      : all 6 partitions revoked, everyone pauses, then reassigned       -> 6 paused");
        System.out.println("  cooperative: only the partitions that must move are revoked and re-granted    -> " + moved + " paused");
        System.out.println("  after join:" + describe(after, Arrays.asList("c1", "c2", "c3")));
        System.out.println("  Triggers: member joins/leaves/crashes, missed heartbeats, max.poll.interval.ms exceeded, topic partitions change.");

        section("4. Committed offset vs processed position: what a crash costs");
        long processed = 1_480, committed = 1_400;                  // consumer processed up to 1480 but commits every 100
        System.out.println("  consumer processed offsets 0.." + (processed - 1) + ", last commit = " + committed);
        System.out.println("  after a crash the new owner resumes at " + committed + " -> " + (processed - committed) + " records are processed AGAIN");
        System.out.println("  => with at-least-once the handler MUST be idempotent. Commit more often = fewer duplicates, more commit overhead.");
        System.out.println("  Never auto-commit before processing is durable: that is how records are silently lost.");

        section("5. Lag over time: producer 600 msg/tick, each consumer handles 150 msg/tick, 6 partitions");
        int partitions = 6;
        long[] lag = new long[partitions];
        int consumers = 2;
        System.out.println("  tick consumers active capacity   lag(total)  action");
        for (int tick = 1; tick <= 14; tick++) {
            String action = "";
            if (tick == 5) { consumers = 4; action = "scale to 4"; }
            if (tick == 9) { consumers = 8; action = "scale to 8 (only 6 useful)"; }
            int active = Math.min(consumers, partitions);
            for (int p = 0; p < partitions; p++) lag[p] += 100;                        // even key distribution
            // capacity is per consumer; each consumer drains its own partitions
            int[] owned = new int[partitions];
            for (int p = 0; p < partitions; p++) owned[p] = p % active;
            for (int c = 0; c < active; c++) {
                long cap = 150;
                for (int p = 0; p < partitions && cap > 0; p++) if (owned[p] == c) { long take = Math.min(cap, lag[p]); lag[p] -= take; cap -= take; }
            }
            long total = Arrays.stream(lag).sum();
            System.out.printf("  %4d %9d %6d %8d %12d  %s%n", tick, consumers, active, active * 150, total, action);
        }
        System.out.println("  Lag is a SYMPTOM. Rate in (600) > rate out (300) makes it grow linearly; time to drain = lag / (out - in).");
        System.out.println("  Ticks 5-8: 4 consumers exactly match the arrival rate, so lag STOPS GROWING but never drains - you need headroom.");

        section("6. Hot partition: scaling consumers does not help");
        long[] hotLag = new long[6];
        for (int tick = 1; tick <= 6; tick++) {
            hotLag[0] += 300;                                      // one key family = 300/tick on partition 0
            for (int p = 1; p < 6; p++) hotLag[p] += 60;
            for (int p = 0; p < 6; p++) hotLag[p] = Math.max(0, hotLag[p] - 150);   // 6 consumers, one partition each, 150/tick
        }
        System.out.println("  per-partition lag after 6 ticks (6 consumers): " + Arrays.toString(hotLag));
        System.out.println("  Only partition 0 is behind: a consumer per partition is already the limit. Fix the key skew / process faster per record.");

        section("7. Settings that decide whether a slow consumer triggers a rebalance");
        System.out.println("  heartbeat.interval.ms = 3000     (liveness pings from a background thread)");
        System.out.println("  session.timeout.ms    = 45000    (no heartbeat this long => removed from the group)");
        System.out.println("  max.poll.interval.ms  = 300000   (no poll() this long => removed, even though heartbeats flow)");
        System.out.println("  max.poll.records      = 500      (lower it when each record is slow, so you stay under max.poll.interval.ms)");
        System.out.println("  group.instance.id (static membership) = restarts within session.timeout do not trigger a rebalance");
    }

    /** Cooperative-sticky style: keep owners, hand the new member only what is needed for balance. */
    static Map<String, String> stickyAdd(Map<String, String> current, String newcomer, int partitions) {
        Map<String, String> next = new LinkedHashMap<>(current);
        Set<String> members = new TreeSet<>(current.values());
        members.add(newcomer);
        int fair = partitions / members.size();
        int need = fair;
        for (String owner : new TreeSet<>(current.values())) {
            Iterator<Map.Entry<String, String>> it = next.entrySet().iterator();
            long count = next.values().stream().filter(owner::equals).count();
            while (it.hasNext() && need > 0 && count > fair) {
                Map.Entry<String, String> e = it.next();
                if (e.getValue().equals(owner)) { e.setValue(newcomer); need--; count--; }
            }
        }
        return next;
    }
}

// EXERCISE: add static membership to section 3 and show that a pod restart inside session.timeout
// moves ZERO partitions, while a normal restart moves its partitions twice (leave + rejoin).
