/*
 * 04 - Production scenarios: connection budgets, Kafka partition keys, Redis memory and slots
 *
 * Run:  java 04_connections_kafka_and_redis_simulations.java
 *
 * Interview angle: (Q5) 5 pods -> 20 pods and Postgres refuses connections.
 * (Q6) add partitions to a Kafka topic and per-customer ordering breaks.
 * (Q7) Redis hits maxmemory and writes fail: which setting decides?
 * (Q20) one Redis Cluster node at 100% CPU, the others idle.
 * The Kafka murmur2 partitioner and the Redis CRC16 slot function are real implementations of
 * the published algorithms; brokers and servers are modelled.
 */
import java.nio.charset.StandardCharsets;
import java.util.*;

class ConnectionsKafkaAndRedisSimulations {

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

    // ------------------------------------------------------------ Q5
    static void q5() {
        section("Q5. 5 pods -> 20 pods and Postgres refuses connections");
        int maxConnections = 100, superuserReserved = 3;
        int usable = maxConnections - superuserReserved;
        int hikariDefaultMax = 10;                       // HikariCP default maximumPoolSize
        for (int pods : new int[] { 5, 20 }) {
            int demand = pods * hikariDefaultMax;
            System.out.println("  " + pods + " pods x " + hikariDefaultMax + " = " + demand + " connections vs " + usable + " usable");
        }
        checkTrue("5 pods fit", 5 * hikariDefaultMax <= usable);
        checkTrue("20 pods do not fit: FATAL: sorry, too many clients already", 20 * hikariDefaultMax > usable);

        int perPodBudget = usable / 20;
        check("per-pod pool size that fits 20 pods (leave none for jobs/migrations)", 4, perPodBudget);
        int withHeadroom = (int) Math.floor(usable * 0.8 / 20);
        check("with 20% headroom for admin / batch / rolling deploy overlap", 3, withHeadroom);
        int rollingDeploy = 20 + 5;                      // maxSurge: new pods start before old ones stop
        System.out.println("  during a rolling update up to " + rollingDeploy + " pods hold pools at once");
        System.out.println("  fixes: size pool = (max_connections - reserved) / max pods incl. surge; PgBouncer in transaction mode;");
        System.out.println("         a pool of 10 per pod is almost always bigger than the DB can usefully run in parallel (cores x 2).");
    }

    // ------------------------------------------------------------ Q6
    /** Kafka's Utils.murmur2 (used by the default partitioner for keyed records). */
    static int murmur2(byte[] data) {
        int length = data.length;
        int seed = 0x9747b28c;
        final int m = 0x5bd1e995;
        final int r = 24;
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

    static void q6() {
        section("Q6. add partitions and per-customer ordering breaks");
        int customers = 1_000, before = 6, after = 8;
        int moved = 0;
        String example = null;
        for (int i = 0; i < customers; i++) {
            String key = "customer-" + i;
            int p1 = partitionFor(key, before), p2 = partitionFor(key, after);
            if (p1 != p2) { moved++; if (example == null) example = key + ": partition " + p1 + " -> " + p2; }
        }
        System.out.println("  " + moved + " of " + customers + " customers map to a DIFFERENT partition after 6 -> 8");
        System.out.println("  e.g. " + example);
        checkTrue("a large share of keys move (hash % n changes for most keys when n changes)", moved > customers / 2);
        check("same key, same partition count: stable (that is the only guarantee)",
                partitionFor("customer-7", 6), partitionFor("customer-7", 6));
        System.out.println("  consequence: old events sit in partition P1, new events go to P2; two consumers read them");
        System.out.println("  in parallel with NO ordering between partitions. Order is guaranteed only inside one partition.");
        System.out.println("  fixes: over-provision partitions up front; create a new topic and drain-then-switch; or let");
        System.out.println("  consumers resequence by a per-key version number.");
    }

    // ------------------------------------------------------------ Q7
    static class FakeRedis {
        final String policy; final int maxKeys;
        final LinkedHashMap<String, String> data = new LinkedHashMap<>(16, 0.75f, true);   // access order = LRU
        FakeRedis(String policy, int maxKeys) { this.policy = policy; this.maxKeys = maxKeys; }

        String set(String k, String v) {
            if (!data.containsKey(k) && data.size() >= maxKeys) {
                if (policy.equals("noeviction")) return "(error) OOM command not allowed when used memory > 'maxmemory'";
                String victim = data.keySet().iterator().next();          // least recently used
                data.remove(victim);
            }
            data.put(k, v);
            return "OK";
        }
        String get(String k) { return data.get(k); }
    }

    static void q7() {
        section("Q7. Redis hits its memory limit and writes start failing");
        FakeRedis no = new FakeRedis("noeviction", 3);
        no.set("a", "1"); no.set("b", "2"); no.set("c", "3");
        String res = no.set("d", "4");
        check("noeviction (default): write rejected, reads keep working", true, res.startsWith("(error) OOM"));
        check("noeviction: existing data intact", "1", no.get("a"));

        FakeRedis lru = new FakeRedis("allkeys-lru", 3);
        lru.set("a", "1"); lru.set("b", "2"); lru.set("c", "3");
        lru.get("a");                                  // a is now most recently used
        check("allkeys-lru: write accepted", "OK", lru.set("d", "4"));
        check("allkeys-lru: coldest key (b) evicted", null, lru.get("b"));
        check("allkeys-lru: hot key (a) kept", "1", lru.get("a"));
        System.out.println("  maxmemory-policy: noeviction | allkeys-lru | allkeys-lfu | volatile-lru | volatile-ttl | allkeys-random ...");
        System.out.println("  volatile-* policies evict only keys WITH a TTL: if none have one, they behave like noeviction.");
        System.out.println("  pick: cache -> allkeys-lru/lfu; Redis as primary store / queue / locks -> noeviction + alert on memory.");
    }

    // ------------------------------------------------------------ Q20
    /** CRC16-CCITT (XMODEM), the function Redis Cluster uses for key -> slot. */
    static int crc16(byte[] bytes) {
        int crc = 0;
        for (byte b : bytes) {
            crc ^= (b & 0xff) << 8;
            for (int i = 0; i < 8; i++) crc = (crc & 0x8000) != 0 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff;
        }
        return crc;
    }
    static int slotFor(String key) {
        int open = key.indexOf('{');
        if (open >= 0) {
            int close = key.indexOf('}', open + 1);
            if (close > open + 1) key = key.substring(open + 1, close);      // hash tag: only {...} is hashed
        }
        return crc16(key.getBytes(StandardCharsets.UTF_8)) % 16384;
    }
    static int nodeFor(int slot) { return slot <= 5460 ? 0 : slot <= 10922 ? 1 : 2; }     // 3 masters

    static void q20() {
        section("Q20. one Redis Cluster node at 100% CPU, the others idle");
        check("CRC16(\"123456789\") matches the published XMODEM check value 0x31C3", 0x31C3,
                crc16("123456789".getBytes(StandardCharsets.US_ASCII)));
        check("hash tags: {tenant42}:a and {tenant42}:b share a slot", slotFor("{tenant42}:a"), slotFor("{tenant42}:b"));
        checkTrue("without a tag, different keys spread over slots", slotFor("user:1") != slotFor("user:2"));

        Random rnd = new Random(7);
        int requests = 30_000;
        int[] load = new int[3];
        for (int i = 0; i < requests; i++) {
            String key = rnd.nextInt(100) < 40 ? "feed:global" : "user:" + rnd.nextInt(100_000);   // 40% on one key
            load[nodeFor(slotFor(key))]++;
        }
        int hot = nodeFor(slotFor("feed:global"));
        System.out.println("  requests per node: " + Arrays.toString(load) + "  (hot key lives on node " + hot + ")");
        checkTrue("the node owning the hot key takes more than 40% of all traffic", load[hot] > requests * 0.4);

        int[] tagged = new int[3];
        for (int i = 0; i < requests; i++) {
            String key = "{big-tenant}:user:" + rnd.nextInt(100_000);          // misused hash tag
            tagged[nodeFor(slotFor(key))]++;
        }
        System.out.println("  with a shared {big-tenant} tag: " + Arrays.toString(tagged));
        checkTrue("a single hash tag funnels 100% of keys to ONE node", Arrays.stream(tagged).max().getAsInt() == requests);

        int[] split = new int[3];
        for (int i = 0; i < requests; i++) {
            String key = rnd.nextInt(100) < 40 ? "feed:global#" + rnd.nextInt(16) : "user:" + rnd.nextInt(100_000);
            split[nodeFor(slotFor(key))]++;
        }
        System.out.println("  hot key split into 16 shards: " + Arrays.toString(split));
        checkTrue("fix: key splitting spreads the hot key; no node above 50%", Arrays.stream(split).max().getAsInt() < requests * 0.5);
        System.out.println("  other fixes: in-process (Caffeine) cache in front of the hot key, read from replicas (READONLY),");
        System.out.println("  redis-cli --hotkeys / --bigkeys to find it, and check for one huge value or slow O(N) commands (KEYS, HGETALL).");
    }

    public static void main(String[] args) {
        q5();
        q6();
        q7();
        q20();
        System.out.println("\nALL " + checks + " CHECKS PASSED");
    }
}
