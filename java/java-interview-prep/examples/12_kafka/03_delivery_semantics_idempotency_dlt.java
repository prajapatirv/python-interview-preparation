/*
 * 03 - Delivery semantics: loss, duplicates, idempotent processing, retries and a dead-letter topic
 *
 * Run:  java 03_delivery_semantics_idempotency_dlt.java
 *
 * A broker + consumer with CRASH INJECTION, so each guarantee is something you can observe:
 *   at-most-once  (commit, then process)  -> lost records
 *   at-least-once (process, then commit)  -> duplicates after a crash
 *   at-least-once + idempotent sink       -> effectively-once outcome
 *   producer retries with/without idempotence
 *   poison message -> bounded retries -> DLT
 */
import java.util.*;

class DeliverySemanticsIdempotencyDlt {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    // ---- a single-partition log and a consumer that can crash after a given number of records
    static class Log { final List<String> records = new ArrayList<>(); }

    static class Sink {                                         // "the database"
        final List<String> writes = new ArrayList<>();
        final Set<String> processedIds = new HashSet<>();       // the unique index / dedupe table
        void insert(String id) { writes.add(id); }
        boolean insertIdempotent(String id) {                   // INSERT ... ON CONFLICT DO NOTHING
            if (!processedIds.add(id)) return false;
            writes.add(id);
            return true;
        }
    }

    enum Mode { AT_MOST_ONCE, AT_LEAST_ONCE, AT_LEAST_ONCE_IDEMPOTENT }

    /** Runs a consumer that crashes once (right after record #crashAfter is handled but before the commit batch). */
    static Sink consume(Log log, Mode mode, int crashAfter) {
        Sink sink = new Sink();
        long committed = 0;
        boolean crashed = false;
        while (committed < log.records.size()) {
            long pos = committed;                                // after a restart the consumer resumes from the COMMITTED offset
            int batchEnd = (int) Math.min(log.records.size(), pos + 5);
            if (mode == Mode.AT_MOST_ONCE) committed = batchEnd; // commit first (like auto-commit firing early)
            boolean crashNow = false;
            for (int i = (int) pos; i < batchEnd; i++) {
                if (!crashed && i == crashAfter) { crashed = true; crashNow = true; break; }   // process dies mid-batch
                String id = log.records.get(i);
                if (mode == Mode.AT_LEAST_ONCE_IDEMPOTENT) sink.insertIdempotent(id); else sink.insert(id);
            }
            if (crashNow) continue;                              // restart: loop again from 'committed'
            if (mode != Mode.AT_MOST_ONCE) committed = batchEnd; // commit AFTER processing
        }
        return sink;
    }

    static String verdict(Log log, Sink s) {
        Set<String> unique = new HashSet<>(s.writes);
        int lost = (int) log.records.stream().filter(r -> !unique.contains(r)).count();
        int dups = s.writes.size() - unique.size();
        return "written=" + s.writes.size() + " lost=" + lost + " duplicates=" + dups;
    }

    // ---- producer retries
    static class Broker {
        final List<String> log = new ArrayList<>();
        final Map<String, Integer> lastSeqByProducer = new HashMap<>();
        boolean idempotent;
        /** Returns true if the ack reached the producer. The write itself always succeeds in this scenario. */
        boolean append(String producerId, int seq, String value, boolean ackLost) {
            Integer last = lastSeqByProducer.get(producerId);
            if (idempotent && last != null && seq <= last) {
                // duplicate retry detected via (producerId, partition, sequence): dropped, but acked
            } else {
                log.add(value);
                lastSeqByProducer.put(producerId, seq);
            }
            return !ackLost;
        }
    }

    static List<String> sendWithRetry(boolean idempotent) {
        Broker b = new Broker();
        b.idempotent = idempotent;
        for (int seq = 0; seq < 3; seq++) {
            boolean acked = b.append("producer-1", seq, "event-" + seq, seq == 1);   // the ack for event-1 is lost on the network
            if (!acked) b.append("producer-1", seq, "event-" + seq, false);          // producer retries (retries > 0)
        }
        return b.log;
    }

    public static void main(String[] args) {
        Log log = new Log();
        for (int i = 1; i <= 12; i++) log.records.add("evt-" + i);

        section("1. Consumer crashes mid-batch (record #7 of 12). What happens to each strategy?");
        for (Mode m : Mode.values()) System.out.printf("  %-26s %s%n", m, verdict(log, consume(log, m, 7)));
        System.out.println("  at-most-once  : offset committed first -> the unprocessed tail of the batch is gone");
        System.out.println("  at-least-once : resumed from last commit -> the already-processed head of the batch repeats");
        System.out.println("  + idempotent  : the repeat is a no-op -> the DB state equals exactly-once");

        section("2. Producer retries: network drops the ACK, the producer resends");
        System.out.println("  retries, enable.idempotence=false : " + sendWithRetry(false) + "   <- duplicate event-1");
        System.out.println("  retries, enable.idempotence=true  : " + sendWithRetry(true) + "   <- broker de-duplicates by (producerId, sequence)");
        System.out.println("  Idempotence is per producer SESSION and per partition; it does not dedupe your application re-sending after a restart.");

        section("3. Kafka transactions / EOS: what they do and do not cover");
        System.out.println("  read-process-write between Kafka topics: consume + produce + offset commit are ONE atomic transaction");
        System.out.println("    (transactional.id on the producer, isolation.level=read_committed on consumers).");
        System.out.println("  Writing to PostgreSQL/Couchbase/an HTTP API is OUTSIDE the transaction -> use idempotent writes,");
        System.out.println("  a processed-event table, or the transactional outbox. 'Exactly-once' is a property of a defined scope.");

        section("4. Bounded retries then a dead-letter topic (poison pill handling)");
        List<String> input = Arrays.asList("ok-1", "BAD-json", "ok-2", "ok-3");
        List<String> dlt = new ArrayList<>(), done = new ArrayList<>();
        int maxAttempts = 3;
        for (String rec : input) {
            int attempt = 0;
            boolean success = false;
            while (attempt < maxAttempts && !success) {
                attempt++;
                if (rec.startsWith("BAD")) {
                    long backoffMs = 100L * (1L << (attempt - 1));
                    System.out.println("  " + rec + " attempt " + attempt + " failed (non-retryable parse error) backoff would be " + backoffMs + " ms");
                    if (attempt >= 1) break;                // deserialization errors are not worth retrying: go straight to DLT
                } else { success = true; }
            }
            if (success) done.add(rec); else dlt.add(rec + " {origTopic=orders, partition=0, exception=JsonParseException}");
        }
        System.out.println("  processed: " + done);
        System.out.println("  DLT      : " + dlt);
        System.out.println("  The partition kept moving: one bad record must not block everything behind it (head-of-line blocking).");
        System.out.println("  Classify errors: transient (timeout, 503) -> retry with backoff/retry topics; permanent (bad payload) -> DLT immediately.");

        section("5. Spring Kafka wiring, for reference");
        System.out.println("  @KafkaListener(topics = \"orders\", groupId = \"billing\", concurrency = \"3\")");
        System.out.println("  DefaultErrorHandler(new DeadLetterPublishingRecoverer(kafkaTemplate), new ExponentialBackOff(200, 2.0));");
        System.out.println("  handler.addNotRetryableExceptions(DeserializationException.class, ValidationException.class);");
        System.out.println("  spring.kafka.listener.ack-mode=record|manual ; use ErrorHandlingDeserializer to survive bad payloads.");
    }
}

// EXERCISE: make the idempotent sink also protect against a duplicate that arrives AFTER the
// dedupe table was pruned. What retention must the dedupe table have relative to topic retention?
