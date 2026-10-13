/*
 * 01 - Kafka topics, partitions, keys and ordering (simulation using Kafka's real partitioner math)
 *
 * Run:  java 01_partitions_keys_and_ordering.java
 *
 * The default partitioner for keyed records is:  toPositive(murmur2(keyBytes)) % numPartitions.
 * The murmur2 below is the same algorithm as org.apache.kafka.common.utils.Utils.murmur2, so the
 * key -> partition numbers match a real cluster with the default partitioner.
 *
 * Interview angle: "how does a record choose a partition?", "what is guaranteed about ordering?",
 * "what happens when you add partitions?", "what is a hot partition?", "how many partitions?".
 */
import java.nio.charset.StandardCharsets;
import java.util.*;

class PartitionsKeysAndOrdering {

    static int murmur2(byte[] data) {
        int length = data.length, seed = 0x9747b28c, m = 0x5bd1e995, r = 24;
        int h = seed ^ length;
        int length4 = length / 4;
        for (int i = 0; i < length4; i++) {
            int i4 = i * 4;
            int k = (data[i4] & 0xff) + ((data[i4 + 1] & 0xff) << 8) + ((data[i4 + 2] & 0xff) << 16) + ((data[i4 + 3] & 0xff) << 24);
            k *= m; k ^= k >>> r; k *= m;
            h *= m; h ^= k;
        }
        switch (length % 4) {
            case 3: h ^= (data[(length & ~3) + 2] & 0xff) << 16;
            case 2: h ^= (data[(length & ~3) + 1] & 0xff) << 8;
            case 1: h ^= data[length & ~3] & 0xff; h *= m;
        }
        h ^= h >>> 13; h *= m; h ^= h >>> 15;
        return h;
    }

    static int partitionFor(String key, int partitions) {
        return (murmur2(key.getBytes(StandardCharsets.UTF_8)) & 0x7fffffff) % partitions;
    }

    /** A topic is N independent, append-only logs. Order exists ONLY inside a partition. */
    static class Topic {
        final List<List<String>> logs = new ArrayList<>();
        Topic(int partitions) { for (int i = 0; i < partitions; i++) logs.add(new ArrayList<>()); }
        long send(String key, String value) {
            List<String> p = logs.get(partitionFor(key, logs.size()));
            p.add(key + ":" + value);
            return p.size() - 1;                         // the offset of this record in its partition
        }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("1. Same key -> same partition (while the partition count is unchanged)");
        for (String key : new String[]{"order-1001", "order-1002", "order-1003", "order-1001", "order-1002"})
            System.out.printf("  key=%-11s -> partition %d of 6%n", key, partitionFor(key, 6));

        section("2. Ordering is per partition, not per topic");
        Topic orders = new Topic(3);
        String[] events = {"CREATED", "PAID", "SHIPPED"};
        for (String e : events) for (String o : new String[]{"A", "B", "C", "D"}) orders.send("order-" + o, e);
        for (int p = 0; p < 3; p++) System.out.println("  partition " + p + ": " + orders.logs.get(p));
        System.out.println("  Each order's events are in order within ONE partition; across partitions there is no global order.");
        System.out.println("  A consumer sees CREATED -> PAID -> SHIPPED per order. Use a key = the entity whose order matters.");

        section("3. No key -> records spread (sticky/round-robin batches): no per-entity ordering");
        System.out.println("  Null keys give best balance and zero ordering guarantees. Pick the key from the business rule.");

        section("4. Skew: one hot key overloads one partition no matter how many partitions exist");
        int partitions = 8;
        int[] load = new int[partitions];
        Random rnd = new Random(7);
        for (int i = 0; i < 10_000; i++) {
            String key = rnd.nextInt(100) < 40 ? "customer-ACME" : "customer-" + rnd.nextInt(5_000);   // 40% from one big tenant
            load[partitionFor(key, partitions)]++;
        }
        int hot = 0;
        for (int p = 0; p < partitions; p++) { System.out.printf("  p%d %5d %s%n", p, load[p], "#".repeat(load[p] / 200)); if (load[p] > load[hot]) hot = p; }
        System.out.println("  partition " + hot + " takes " + (100 * load[hot] / 10_000) + "% of traffic; adding consumers cannot split one partition.");
        System.out.println("  Fixes: salt the key (customer-ACME#0..#7) if per-customer order is not needed, or a custom partitioner,");
        System.out.println("  or split the tenant onto its own topic. Detect with per-partition lag / bytes-in metrics.");

        section("5. Adding partitions remaps keys (breaks per-key ordering across the change)");
        int moved = 0, total = 2_000;
        for (int i = 0; i < total; i++) {
            String key = "order-" + i;
            if (partitionFor(key, 6) != partitionFor(key, 8)) moved++;
        }
        System.out.println("  growing 6 -> 8 partitions: " + moved + " of " + total + " keys (" + (100 * moved / total) + "%) now map to a different partition");
        System.out.println("  In-flight events for a moved key can be consumed by two consumers; stateful consumers lose locality.");
        System.out.println("  You can add partitions, never remove them. Over-provision (e.g. 12/24/30) from capacity math, not a guess.");

        section("6. How many partitions? (parallelism ceiling + throughput)");
        double targetMBs = 120, producerPerPartMBs = 10, consumerPerPartMBs = 5;
        int needed = (int) Math.ceil(Math.max(targetMBs / producerPerPartMBs, targetMBs / consumerPerPartMBs));
        System.out.println("  target " + targetMBs + " MB/s, one partition: produce " + producerPerPartMBs + " MB/s, consume " + consumerPerPartMBs + " MB/s");
        System.out.println("  partitions >= max(120/10, 120/5) = " + needed + "; add headroom for growth and for max consumer instances you want");
        System.out.println("  Cost of more partitions: more open files, longer leader election/rebalance, more end-to-end latency, more memory in clients.");
    }
}

// EXERCISE: write a custom partitioner that sends the top-10 tenants to dedicated partitions and
// hashes everyone else over the remaining ones. What ordering guarantee do you keep?
