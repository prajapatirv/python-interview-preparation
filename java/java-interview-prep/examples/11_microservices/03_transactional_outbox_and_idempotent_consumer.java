/*
 * 03 - The dual-write problem, the transactional outbox, and the idempotent consumer
 *
 * Run:  java 03_transactional_outbox_and_idempotent_consumer.java
 *
 * "Save the order, then publish OrderCreated" is two systems and therefore NOT atomic.
 * Show the failure, fix it with an outbox written in the SAME database transaction, and make the
 * consumer safe against the duplicates that at-least-once delivery produces.
 */
import java.util.*;

class TransactionalOutboxAndIdempotentConsumer {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    // ---- a tiny transactional database: commit applies ALL staged writes or none
    static class Database {
        final List<String> orders = new ArrayList<>();
        final List<String[]> outbox = new ArrayList<>();      // {eventId, payload, status}
        private List<String> stagedOrders; private List<String[]> stagedOutbox;
        void begin() { stagedOrders = new ArrayList<>(); stagedOutbox = new ArrayList<>(); }
        void insertOrder(String id) { stagedOrders.add(id); }
        void insertOutbox(String eventId, String payload) { stagedOutbox.add(new String[]{eventId, payload, "NEW"}); }
        void commit() { orders.addAll(stagedOrders); outbox.addAll(stagedOutbox); }
        void rollback() { stagedOrders = null; stagedOutbox = null; }
    }

    static class Broker {
        final List<String> topic = new ArrayList<>();
        boolean available = true;
        void publish(String eventId, String payload) {
            if (!available) throw new IllegalStateException("broker unavailable");
            topic.add(eventId + "|" + payload);
        }
    }

    static class CrashException extends RuntimeException { }

    public static void main(String[] args) {

        section("1. The dual write: DB commit succeeds, publish fails -> the event is lost");
        Database db = new Database(); Broker broker = new Broker();
        broker.available = false;
        db.begin(); db.insertOrder("o-1"); db.commit();
        try { broker.publish("e-1", "OrderCreated o-1"); } catch (IllegalStateException e) { System.out.println("  publish failed: " + e.getMessage()); }
        System.out.println("  DB orders=" + db.orders + " topic=" + broker.topic + "   <- order exists, nobody was told");
        System.out.println("  Reverse order (publish, then DB fails) leaves a phantom event for an order that does not exist.");
        System.out.println("  @Transactional does not cover Kafka; try/catch + retry still loses events if the process dies between the two.");

        section("2. Outbox: business row + event row commit atomically");
        Database db2 = new Database(); Broker b2 = new Broker();
        db2.begin();
        db2.insertOrder("o-2");
        db2.insertOutbox("e-2", "OrderCreated o-2");
        db2.commit();                                                     // one local ACID transaction
        System.out.println("  committed: orders=" + db2.orders + " outbox rows=" + db2.outbox.size());
        b2.available = false;
        relay(db2, b2);                                                   // relay fails: row stays NEW
        System.out.println("  relay while broker down: pending=" + pending(db2) + " published=" + b2.topic.size());
        b2.available = true;
        relay(db2, b2);                                                   // later, the relay catches up
        System.out.println("  relay after recovery   : pending=" + pending(db2) + " published=" + b2.topic);
        System.out.println("  Relay = polling publisher (SELECT ... WHERE status='NEW' FOR UPDATE SKIP LOCKED) or CDC (Debezium reads the WAL).");

        section("3. The relay can crash after publish and before marking SENT -> duplicates");
        Database db3 = new Database(); Broker b3 = new Broker();
        db3.begin(); db3.insertOrder("o-3"); db3.insertOutbox("e-3", "OrderCreated o-3"); db3.commit();
        try { relayWithCrash(db3, b3); } catch (CrashException e) { System.out.println("  relay crashed after publish, before UPDATE status=SENT"); }
        relay(db3, b3);                                                   // restart: row still NEW -> published again
        System.out.println("  topic now holds " + b3.topic.size() + " copies: " + b3.topic);
        System.out.println("  Outbox gives AT-LEAST-ONCE publishing. That is why every event carries a stable eventId.");

        section("4. Idempotent consumer: dedupe on eventId in the same transaction as the side effect");
        Set<String> processed = new HashSet<>();                          // table: processed_event(event_id PRIMARY KEY)
        List<String> inventoryReservations = new ArrayList<>();
        for (String msg : b3.topic) {
            String eventId = msg.split("\\|")[0];
            if (!processed.add(eventId)) { System.out.println("  skip duplicate " + eventId); continue; }   // INSERT fails on PK conflict
            inventoryReservations.add("reserve for " + msg.split("\\|")[1]);
        }
        System.out.println("  reservations performed: " + inventoryReservations);

        section("5. Choosing the dedupe key and keeping it correct");
        System.out.println("  natural key (orderId + eventType) or a UUID eventId assigned in the producer's transaction");
        System.out.println("  insert the dedupe row and apply the effect in ONE transaction, else you re-create the dual-write problem");
        System.out.println("  retention of the dedupe table must exceed the topic retention + max replay window");
        System.out.println("  Alternatives: natural idempotency (UPSERT by key, 'set status=PAID' rather than 'balance += x'), version checks.");
    }

    static long pending(Database db) { return db.outbox.stream().filter(r -> r[2].equals("NEW")).count(); }

    static void relay(Database db, Broker broker) {
        for (String[] row : db.outbox) {
            if (!row[2].equals("NEW")) continue;
            try { broker.publish(row[0], row[1]); row[2] = "SENT"; }
            catch (IllegalStateException e) { return; }                   // leave NEW, retry on the next poll
        }
    }

    static void relayWithCrash(Database db, Broker broker) {
        for (String[] row : db.outbox) {
            if (!row[2].equals("NEW")) continue;
            broker.publish(row[0], row[1]);
            throw new CrashException();                                   // process killed before the status update
        }
    }
}

// EXERCISE: replace polling with a CDC-style tail of an append-only list and compare latency.
