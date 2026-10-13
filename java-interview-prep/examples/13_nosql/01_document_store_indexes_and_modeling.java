/*
 * 01 - Document databases (MongoDB / Couchbase style): modeling, indexes and query cost
 *
 * Run:  java 01_document_store_indexes_and_modeling.java
 *
 * A miniature document store that counts how many documents each query had to examine,
 * so "why is this query slow / why do we need an index?" becomes a number you can see.
 */
import java.util.*;
import java.util.function.*;
import java.util.stream.*;

class DocumentStoreIndexesAndModeling {

    /** A document is a nested map. Real stores keep BSON/JSON; the access patterns are the same. */
    static class Collection {
        final Map<String, Map<String, Object>> byId = new LinkedHashMap<>();
        final Map<String, Map<Object, Set<String>>> indexes = new HashMap<>();   // field -> value -> ids
        long examined = 0;

        void insert(String id, Map<String, Object> doc) {
            byId.put(id, doc);
            for (Map.Entry<String, Map<Object, Set<String>>> idx : indexes.entrySet()) {
                Object v = doc.get(idx.getKey());
                if (v != null) idx.getValue().computeIfAbsent(v, k -> new HashSet<>()).add(id);
            }
        }
        void createIndex(String field) {
            Map<Object, Set<String>> idx = new HashMap<>();
            for (Map.Entry<String, Map<String, Object>> e : byId.entrySet()) {
                Object v = e.getValue().get(field);
                if (v != null) idx.computeIfAbsent(v, k -> new HashSet<>()).add(e.getKey());
            }
            indexes.put(field, idx);
        }
        List<Map<String, Object>> findEq(String field, Object value) {
            examined = 0;
            List<Map<String, Object>> out = new ArrayList<>();
            Map<Object, Set<String>> idx = indexes.get(field);
            if (idx != null) {                                           // IXSCAN
                for (String id : idx.getOrDefault(value, Collections.emptySet())) { examined++; out.add(byId.get(id)); }
            } else {                                                     // COLLSCAN
                for (Map<String, Object> d : byId.values()) { examined++; if (value.equals(d.get(field))) out.add(d); }
            }
            return out;
        }
    }

    static Map<String, Object> doc(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("1. Query cost with and without an index (100,000 order documents)");
        Collection orders = new Collection();
        String[] statuses = {"NEW", "PAID", "SHIPPED", "CANCELLED"};
        Random r = new Random(1);
        for (int i = 0; i < 100_000; i++)
            orders.insert("o" + i, doc("customerId", "c" + r.nextInt(5_000), "status", statuses[r.nextInt(4)], "total", r.nextInt(500)));
        orders.findEq("customerId", "c42");
        System.out.println("  find customerId=c42 WITHOUT index : examined " + orders.examined + " docs  (COLLSCAN)");
        orders.createIndex("customerId");
        List<Map<String, Object>> hit = orders.findEq("customerId", "c42");
        System.out.println("  find customerId=c42 WITH index    : examined " + orders.examined + " docs, returned " + hit.size() + "  (IXSCAN)");
        orders.findEq("status", "CANCELLED");
        int cancelled = orders.findEq("status", "CANCELLED").size();
        System.out.println("  low-cardinality 'status' (4 values): a query returns " + cancelled + " docs (~25%); an index on it alone barely helps - pair it in a compound index");
        System.out.println("  Check plans with explain(): look for COLLSCAN, 'docsExamined >> nReturned', in-memory sorts.");
        System.out.println("  Compound index rule (ESR): Equality fields first, then Sort, then Range.");

        section("2. Embedding vs referencing: model for the read path");
        Map<String, Object> embedded = doc(
                "_id", "order-9", "customer", doc("id", "c1", "name", "Alice"),
                "items", Arrays.asList(doc("sku", "A", "qty", 2, "price", 10), doc("sku", "B", "qty", 1, "price", 25)));
        System.out.println("  embedded order (one read returns everything): " + embedded);
        System.out.println("  Embed when: data is read together, bounded in size, owned by the parent (order lines).");
        System.out.println("  Reference when: unbounded growth (comments, events), shared/updated independently (customer profile),");
        System.out.println("                  or the document would approach the 16 MB (MongoDB) / 20 MB (Couchbase) size limit.");
        System.out.println("  Denormalise copies (customer name on the order) when history must be frozen, e.g. invoice snapshot.");

        section("3. Atomicity boundary = one document");
        System.out.println("  Single-document writes are atomic in MongoDB and Couchbase; multi-document ACID transactions exist");
        System.out.println("  (MongoDB 4.0+, Couchbase 6.5+) but cost latency and locks - design so the common case is ONE document.");

        section("4. Optimistic concurrency with a version / CAS");
        Map<String, Object> stored = doc("_id", "acct-1", "balance", 100, "cas", 1);
        int readCas = (int) stored.get("cas");                       // client A reads, thinks cas=1
        stored.put("balance", 90); stored.put("cas", 2);              // client B updates first
        boolean applied = (int) stored.get("cas") == readCas;         // client A's conditional update
        System.out.println("  client A conditional write with stale CAS applied? " + applied + "  -> retry with a fresh read");
        System.out.println("  Couchbase: CAS value on every get/replace. MongoDB: filter on a version field or use findOneAndUpdate.");

        section("5. Quick comparison for the interview");
        System.out.printf("  %-10s %-22s %-34s%n", "Store", "Model", "Sweet spot");
        System.out.printf("  %-10s %-22s %-34s%n", "MongoDB", "documents (BSON)", "flexible queries, aggregation pipeline");
        System.out.printf("  %-10s %-22s %-34s%n", "Couchbase", "documents (JSON)", "key-value speed + N1QL SQL + caching");
        System.out.printf("  %-10s %-22s %-34s%n", "Cassandra", "wide-column", "massive write throughput, always-on");
        System.out.println("  Pick by access pattern and consistency need, not by fashion. See example 02 for the Cassandra mindset.");
    }
}

// EXERCISE: add a compound index (customerId, status) and show how many documents the query
// customerId=c42 AND status=NEW examines compared with using only the customerId index.
