/*
 * 04 - Kafka client configuration (producer/consumer) and the capacity arithmetic behind it
 *
 * Run:  java 04_kafka_config_and_capacity_math.java
 *
 * Prints the properties you are expected to explain, with the failure each one prevents, and
 * works the numbers for: lag drain time, partitions needed, batching vs latency, replication.
 * Detects whether kafka-clients is on the classpath so you know whether live code would run.
 */
import java.util.*;

class KafkaConfigAndCapacityMath {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    static void table(String[][] rows) {
        for (String[] r : rows) System.out.printf("  %-34s %-12s %s%n", r[0], r[1], r[2]);
    }

    public static void main(String[] args) {

        section("0. Is a real Kafka client available in this JVM?");
        try { Class.forName("org.apache.kafka.clients.producer.KafkaProducer"); System.out.println("  kafka-clients found: live code would work"); }
        catch (ClassNotFoundException e) { System.out.println("  kafka-clients not on classpath (expected): this lab simulates the broker"); }

        section("1. Producer: durability first, then throughput");
        table(new String[][]{
            {"acks", "all", "wait for all in-sync replicas; 1 = leader only (can lose on leader crash); 0 = fire and forget"},
            {"enable.idempotence", "true", "no duplicates from retries (default true in 3.x); requires acks=all"},
            {"retries / delivery.timeout.ms", "MAX / 120000", "bound total time per record, not the retry count"},
            {"max.in.flight.requests.per.conn", "<=5", "<=5 keeps ordering WITH idempotence; >1 without it can reorder on retry"},
            {"linger.ms", "5-20", "wait to fill a batch: higher throughput, +latency"},
            {"batch.size", "32-128 KB", "bytes per partition batch; bigger = better compression/throughput"},
            {"compression.type", "lz4 / zstd", "less network + disk; CPU cost on producer and consumer"},
            {"buffer.memory / max.block.ms", "32MB / 60s", "when full, send() blocks then throws: your back-pressure signal"},
            {"key.serializer / value.serializer", "-", "use a schema (Avro/Protobuf/JSON Schema) + registry, not ad hoc JSON"},
        });

        section("2. Consumer: correctness first");
        table(new String[][]{
            {"group.id", "required", "the unit of load sharing and of committed offsets"},
            {"enable.auto.commit", "false", "commit after processing succeeds (manual / Spring ack-mode)"},
            {"auto.offset.reset", "earliest|latest", "ONLY when no committed offset exists (new group / expired offsets)"},
            {"max.poll.records", "100-500", "batch size per poll; keep processing time << max.poll.interval.ms"},
            {"max.poll.interval.ms", "300000", "max gap between polls before the member is kicked out"},
            {"session.timeout.ms", "45000", "heartbeat-based failure detection"},
            {"heartbeat.interval.ms", "3000", "~1/3 of session timeout"},
            {"fetch.min.bytes / fetch.max.wait.ms", "1 / 500", "raise to trade latency for fewer, bigger fetches"},
            {"isolation.level", "read_committed", "only see committed transactional writes"},
            {"partition.assignment.strategy", "CooperativeSticky", "incremental rebalances, fewer stop-the-world pauses"},
        });

        section("3. Broker / topic durability");
        table(new String[][]{
            {"replication.factor", "3", "copies per partition; 3 is the production norm across racks/AZs"},
            {"min.insync.replicas", "2", "with acks=all, writes need >=2 in-sync copies, tolerating one broker loss"},
            {"unclean.leader.election.enable", "false", "never elect an out-of-sync replica (would lose acknowledged data)"},
            {"retention.ms / retention.bytes", "7d / -", "delete old segments; or cleanup.policy=compact for latest-per-key"},
        });
        System.out.println("  RF=3, minISR=2, acks=all  => survives 1 broker failure with no data loss and no downtime;");
        System.out.println("  two failures => producers get NotEnoughReplicas (consistency chosen over availability).");

        section("4. Lag arithmetic: how long to catch up?");
        double lag = 1_200_000, produceRate = 4_000, consumeRate = 6_500;       // msgs and msgs/sec
        double drainSec = lag / (consumeRate - produceRate);
        System.out.printf("  lag=%,.0f msgs, in=%,.0f/s, out=%,.0f/s -> drains in %.0f s (%.1f min)%n", lag, produceRate, consumeRate, drainSec, drainSec / 60);
        System.out.println("  If out <= in the lag never drains: you need more throughput, not more patience.");
        double perConsumer = 1_300;                                             // msgs/sec one consumer sustains
        int partitions = 12;
        int neededConsumers = (int) Math.ceil(produceRate * 1.5 / perConsumer);  // 50% headroom
        System.out.println("  one consumer = " + (int) perConsumer + " msg/s; need ceil(" + (int) produceRate + " x 1.5 / " + (int) perConsumer + ") = "
                + neededConsumers + " consumers, cap = " + partitions + " partitions");

        section("5. Batching vs latency (linger.ms)");
        for (int linger : new int[]{0, 5, 20}) {
            double reqPerSec = 1000.0 / Math.max(1, linger) ;                  // at most one batch per partition per linger window
            System.out.printf("  linger.ms=%-3d -> up to %.0f batches/s per partition, adds <= %d ms latency%n", linger, reqPerSec, linger);
        }
        System.out.println("  With high rates batches fill by size before linger expires, so latency cost shrinks as load grows.");

        section("6. Storage and network sizing");
        double msgPerSec = 10_000, avgBytes = 1_000; int rf = 3; int retentionDays = 7;
        double inMBs = msgPerSec * avgBytes / 1e6;
        double dailyGB = inMBs * 86_400 / 1_000 * rf;
        System.out.printf("  ingest %.1f MB/s -> replicated disk %.0f GB/day -> %.0f GB for %d days (before compression)%n", inMBs, dailyGB, dailyGB * retentionDays, retentionDays);
        System.out.printf("  follower fetch + producer traffic ~ %.0f MB/s of inter-broker replication%n", inMBs * (rf - 1));

        section("7. Quick answers");
        System.out.println("  Kafka vs RabbitMQ : log (replay, many consumer groups, high throughput) vs broker queue (routing, per-message ack).");
        System.out.println("  Pull model       : consumers control their pace; slow consumers do not stall producers.");
        System.out.println("  KRaft            : Kafka 3.3+ replaces ZooKeeper with Raft-based metadata quorum (ZooKeeper removed in 4.0).");
    }
}

// EXERCISE: given 50k msg/s at 2 KB with p99 end-to-end latency < 200ms, pick partitions, linger.ms,
// batch.size, compression, RF and min.insync.replicas, and justify each number.
