---
id: 11-nosql
title: NoSQL (Couchbase, MongoDB, Cassandra) - from SQL to NoSQL thinking
focus: Weak-area topic - concepts first, then Couchbase specifics, with honest-answer guidance
deep_dive: 13
examples: 13_nosql
---
Strategy: your base is SQL and limited Couchbase exposure. Interviewers accept "I know the model and trade-offs; I have used X at a basic level" - they punish bluffing about operations you never did. Always map NoSQL ideas back to SQL ones you know well.

### Q1 [basic] What is NoSQL and why use it?
Databases that are not table/relational: document, key-value, wide-column, graph. Reasons: flexible schema, horizontal scale by sharding, high write throughput, low-latency key access. Cost: weaker joins/transactions, query flexibility depends on your access patterns.

### Q2 [basic] Name the NoSQL types with one example each.
Key-value (Redis, DynamoDB), Document (MongoDB, Couchbase), Wide-column (Cassandra, HBase), Graph (Neo4j), Search (Elasticsearch/OpenSearch). Couchbase combines key-value access, JSON documents, N1QL (SQL for JSON) and full-text search.

### Q3 [basic] SQL vs NoSQL - how do you choose?
SQL: strong consistency, complex joins/transactions, stable schema, reporting (orders, payments, ERP). NoSQL: massive scale, flexible/evolving documents, known access patterns, high availability across regions (profiles, catalogs, sessions, events). Many systems use both (polyglot persistence).

### Q4 [intermediate] Explain the CAP theorem and what "eventual consistency" means.
In a network partition you must choose Consistency or Availability (partition tolerance is not optional). CP systems refuse some requests to stay consistent; AP systems answer but may return stale data. **Eventual consistency**: replicas converge if no new writes arrive. PACELC adds: even without partitions you trade latency vs consistency.

### Q5 [intermediate] How do you model data in a document database?
Model for your **queries**, not for normalisation. Embed data read together (order + line items); reference data that is large, shared or changes independently (customer). Watch the document size limit (16 MB in MongoDB) and unbounded arrays. Denormalise on purpose and own the update path.

### Q6 [intermediate] What is Couchbase and what are its main building blocks?
A distributed JSON document database with a memory-first architecture. Terms: **bucket -> scope -> collection** (like database -> schema -> table), documents keyed by id, **vBuckets** (1024 shards spread over nodes), services (Data, Query, Index, Search, Eventing, Analytics) that can be scaled separately (Multi-Dimensional Scaling), and XDCR for cross-cluster replication.

### Q7 [intermediate] How do you query in Couchbase?
Primary access is by key (fastest, `get`). For queries use **SQL++ / N1QL**: `SELECT o.id, o.total FROM orders o WHERE o.customerId = $1 AND o.status = "PAID"`. N1QL needs a **GSI** (global secondary index) matching the filter; without an index you get a primary scan (slow) or an error. Use `EXPLAIN` to confirm the index is used, and covering indexes to avoid fetching documents.

### Q8 [intermediate] Couchbase consistency, durability and concurrency?
Single-document operations are atomic. Use **CAS** (compare-and-swap) for optimistic locking. Durability levels (`majority`, `majorityAndPersistToActive`, `persistToMajority`) trade latency for safety. Multi-document ACID transactions exist (since 6.5) but are slower - design aggregates as one document where possible. N1QL queries may be stale unless `scan_consistency=REQUEST_PLUS`.

### Q9 [intermediate] How do you use Couchbase from Spring Boot?
Spring Data Couchbase (`CouchbaseRepository`, `@Document`, `@Field`, N1QL `@Query`) or the Java SDK directly for key-value access and reactive/async use. Configure connection string, bucket/scope/collection, timeouts and a shared `Cluster` bean (one per app). Handle `DocumentNotFoundException`, `CasMismatchException` and `TimeoutException` with retry only when safe.

### Q10 [intermediate] MongoDB essentials?
Collections of BSON documents, `_id`, rich query/aggregation pipeline (`$match`, `$group`, `$lookup`), indexes (compound, TTL, text), replica sets (primary + secondaries, automatic failover), sharding by shard key (a bad key creates hot shards), multi-document transactions on replica sets, write concern (`w:majority`) and read concern/preference.

### Q11 [intermediate] Cassandra essentials?
Wide-column, masterless ring, consistent hashing, tunable consistency (`ONE`, `QUORUM`, `LOCAL_QUORUM`), writes go to commitlog + memtable then SSTables (very fast writes). Model **one table per query**; partition key decides distribution, clustering key decides order inside a partition. No joins, avoid `ALLOW FILTERING`, avoid unbounded partitions and tombstone-heavy deletes. Great for time-series and write-heavy workloads.

### Q12 [intermediate] What is a quorum and how does `R + W > N` give consistency?
With N replicas, reading R and writing W nodes so that R + W > N guarantees the read overlaps the latest write. N=3, QUORUM (2) reads + QUORUM (2) writes -> strong consistency for that key; ONE/ONE is faster but may be stale.

### Q13 [intermediate] Compare sharding strategies and rebalancing.
Hash sharding (even spread, no range scans), range sharding (range scans, hot spots), directory/lookup sharding. Consistent hashing/vBuckets minimise data movement when nodes join or leave. Choose a key with high cardinality that matches your main access path.

### Q14 [advanced] How do you handle schema evolution in a schemaless store?
"Schemaless" really means schema-on-read: the application owns the schema. Keep a `schemaVersion` in each document, write readers that tolerate old versions (lazy migration on read) or run a background migration, and test with real old documents. Document the model like an API.

### Q15 [advanced] How do you do transactions/relationships without joins?
Prefer one-document aggregates (atomic). For cross-document consistency use sagas/outbox, idempotent updates, CAS, and reconciliation. Use references and application-side joins (or `$lookup`/N1QL JOIN for small sets) sparingly.

### Q16 [advanced] Caching with Redis - patterns and pitfalls?
Cache-aside (read -> miss -> load -> set with TTL; on write invalidate), write-through, write-behind. Pitfalls: stampede (use a lock/single-flight or jittered TTLs), stale data, big keys, hot keys, eviction policy surprises, treating a cache as the source of truth. Redis also does rate limits, distributed locks (lease + fencing token) and pub/sub.

### Q17 [advanced] How do you migrate a feature from Oracle to Couchbase/MongoDB?
Pick one bounded context with key-based access, model aggregates around queries, dual-write or CDC to populate, shadow-read and compare, switch reads then writes, keep the old store for rollback, and measure latency/consistency. Do not move relational reporting workloads.

### Q18 [design] Design a user-profile/session store for 50M users with <10 ms reads, multi-region.
Key = userId, one JSON document per user (preferences, flags), key-value reads, TTL for sessions. Cluster in each region with XDCR/multi-region replication, local reads and conflict resolution (last-write-wins by timestamp or CRDT-like merge for counters), cache hot profiles, back it with an event stream for downstream consumers. Capacity: memory quota for the working set, 3 replicas, monitor ejection/resident ratio.

### Q19 [design] Design a product catalog with flexible attributes and search.
Documents per product with an `attributes` map (different per category), index category/brand/price in the DB, and replicate to OpenSearch/Elasticsearch for full-text, facets and ranking via CDC or events. Writes go to the source of truth; search is eventually consistent and rebuildable.

### Q20 [intermediate] Honest answer: "How much NoSQL have you actually done?"
Say it plainly: "My production database work is mostly Oracle and PostgreSQL. I've had basic exposure to Couchbase - key-value access and N1QL with indexes - and I've used OpenSearch/Elasticsearch and cache stores. I understand the modelling and consistency trade-offs, and I would ramp up quickly because the hard part - data modelling around access patterns and idempotent writes - is the same discipline I use in SQL."

### Q21 [design] Design a data model and consistency strategy for an order-history service on a document or wide-column store.
Model for the read path: one document per order (embedding line items), keyed by customer id plus time for 'recent orders' queries; for Cassandra, a table per query with a partition key that bounds partition size. Choose consistency per operation (for example `LOCAL_QUORUM` for writes and reads, eventual for analytics). Handle duplicates with idempotent upserts and a version field. Failure modes: unbounded arrays inside a document, hot partitions, and cross-document transactions you assumed existed.
