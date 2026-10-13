/*
 * 02 - Cassandra thinking: consistent-hash ring, replication, tunable consistency, query-first modeling
 *
 * Run:  java 02_cassandra_ring_quorum_and_modeling.java
 *
 * Interview angle: "how does Cassandra distribute data?", "what is QUORUM and R+W>N?",
 * "what is a partition key vs clustering key?", "why no joins?", "hot partitions",
 * "CAP: what does Cassandra give up?".
 */
import java.util.*;
import java.util.stream.*;

class CassandraRingQuorumAndModeling {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    // ---- a consistent-hash ring with virtual nodes
    static class Ring {
        final TreeMap<Integer, String> tokens = new TreeMap<>();
        Ring(List<String> nodes, int vnodes) {
            for (String n : nodes) for (int v = 0; v < vnodes; v++) tokens.put(hash(n + "#" + v), n);
        }
        static int hash(String s) {                                   // MD5-based token (Cassandra's old RandomPartitioner idea)
            try {
                byte[] d = java.security.MessageDigest.getInstance("MD5").digest(s.getBytes(java.nio.charset.StandardCharsets.UTF_8));
                return ((d[0] & 0xff) << 24) | ((d[1] & 0xff) << 16) | ((d[2] & 0xff) << 8) | (d[3] & 0xff);
            } catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
        }
        /** First `rf` DISTINCT nodes clockwise from the key's token. */
        List<String> replicasFor(String partitionKey, int rf) {
            LinkedHashSet<String> out = new LinkedHashSet<>();
            Integer t = tokens.ceilingKey(hash(partitionKey));
            Iterator<String> it = tokens.tailMap(t == null ? tokens.firstKey() : t, true).values().iterator();
            while (out.size() < rf) {
                if (!it.hasNext()) it = tokens.values().iterator();
                out.add(it.next());
            }
            return new ArrayList<>(out);
        }
    }

    // ---- replicas with versioned cells; read repair picks the newest timestamp
    static class Replica { String value; long ts = -1; boolean up = true; }

    static boolean write(List<Replica> reps, String v, long ts, int required) {
        int acks = 0;
        for (Replica r : reps) if (r.up) { r.value = v; r.ts = ts; acks++; }
        return acks >= required;
    }

    static String read(List<Replica> reps, int required) {
        List<Replica> answered = reps.stream().filter(r -> r.up).limit(required).collect(Collectors.toList());
        if (answered.size() < required) return "UNAVAILABLE";
        return answered.stream().max(Comparator.comparingLong(r -> r.ts)).map(r -> r.value == null ? "null" : r.value).get();
    }

    public static void main(String[] args) {

        section("1. The ring: the partition key decides which nodes own the row");
        Ring ring = new Ring(Arrays.asList("node-A", "node-B", "node-C", "node-D", "node-E"), 16);
        for (String user : new String[]{"user-1", "user-2", "user-3"})
            System.out.println("  partition key " + user + " -> replicas " + ring.replicasFor(user, 3) + " (RF=3)");
        Map<String, Long> spread = IntStream.range(0, 10_000).mapToObj(i -> ring.replicasFor("k" + i, 1).get(0))
                .collect(Collectors.groupingBy(n -> n, TreeMap::new, Collectors.counting()));
        System.out.println("  primary-owner spread over 10,000 keys with 16 vnodes/node: " + spread);
        System.out.println("  No master: any node can coordinate a request. Adding a node moves only ~1/N of the data.");

        section("2. Tunable consistency: choose R and W against N (replication factor)");
        int n = 3;
        int[][] combos = {{1, 1}, {2, 2}, {1, 3}, {3, 1}};
        for (int[] rw : combos) {
            boolean strong = rw[0] + rw[1] > n;
            System.out.printf("  W=%d R=%d  R+W=%d %s N=%d -> %s%n", rw[1], rw[0], rw[0] + rw[1], strong ? ">" : "<=", n,
                    strong ? "read always overlaps the latest write (strong)" : "may read stale data (eventual)");
        }
        System.out.println("  LOCAL_QUORUM (= RF/2+1 in the local DC) is the common production choice: strong enough, tolerates 1 node down.");

        section("3. What stale reads look like, and read repair");
        List<Replica> reps = new ArrayList<>(Arrays.asList(new Replica(), new Replica(), new Replica()));
        write(reps, "v1", 1, 3);
        reps.get(2).up = false;                                       // replica 3 is down during the next write
        boolean ok = write(reps, "v2", 2, 2);                         // QUORUM write succeeds with 2 of 3
        reps.get(2).up = true;                                        // it comes back with the OLD value
        System.out.println("  write v2 at QUORUM succeeded: " + ok);
        reps.get(0).up = false;                                       // now an unlucky read set: replica 2 (v2) + replica 3 (v1)
        System.out.println("  read at ONE   (touching only the stale replica): " + readOnly(reps.get(2)));
        System.out.println("  read at QUORUM (2 replicas, newest timestamp wins): " + read(reps, 2));
        System.out.println("  Hinted handoff + read repair + anti-entropy repair (nodetool repair) converge replicas over time.");
        reps.get(0).up = true;

        section("4. Availability vs consistency (CAP) with nodes down");
        reps.get(1).up = false; reps.get(2).up = false;
        System.out.println("  2 of 3 replicas down: ONE -> " + read(reps, 1) + ", QUORUM -> " + read(reps, 2));
        System.out.println("  Cassandra is AP by default; strong consistency per query by raising R/W, at the cost of availability.");

        section("5. Query-first modeling: one table per query pattern");
        System.out.println("  Query: 'latest 50 orders for a customer'");
        System.out.println("    CREATE TABLE orders_by_customer (");
        System.out.println("      customer_id uuid, order_ts timestamp, order_id uuid, total decimal,");
        System.out.println("      PRIMARY KEY ((customer_id), order_ts, order_id)   -- partition key | clustering columns");
        System.out.println("    ) WITH CLUSTERING ORDER BY (order_ts DESC);");
        System.out.println("    SELECT * FROM orders_by_customer WHERE customer_id = ? LIMIT 50;   -- one partition, one node read");
        System.out.println("  Partition key  = which node(s); clustering columns = sort order INSIDE the partition.");
        System.out.println("  Need the same data by order_id? Write a SECOND table (denormalise), not a join. Writes are cheap.");

        section("6. Anti-patterns that cause incidents");
        System.out.println("  Unbounded partitions : (sensor_id) with years of readings -> bucket by (sensor_id, day)");
        System.out.println("  Hot partitions       : a celebrity key or time-only key (all writes to 'today') -> add a bucket/salt");
        System.out.println("  ALLOW FILTERING      : scans across the cluster; model another table instead");
        System.out.println("  Secondary indexes on high-cardinality columns; large IN lists; tombstone-heavy queues (delete + read patterns)");
        System.out.println("  LWT (IF NOT EXISTS) : Paxos, ~4x latency - use sparingly for true uniqueness");
    }

    static String readOnly(Replica r) { return r.value; }
}

// EXERCISE: add a node to the ring and measure what fraction of 10,000 keys changes primary owner.
// Compare with modulo hashing (hash % nodes) to see why consistent hashing exists.
