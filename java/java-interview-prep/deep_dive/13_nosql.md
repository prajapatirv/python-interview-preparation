# NoSQL: MongoDB, Couchbase and Cassandra (document and wide-column thinking)

> **Runnable:** [`01_document_store_indexes_and_modeling.java`](../examples/13_nosql/01_document_store_indexes_and_modeling.java) ·
> [`02_cassandra_ring_quorum_and_modeling.java`](../examples/13_nosql/02_cassandra_ring_quorum_and_modeling.java)
> **Crib sheet:** [`topics/11-nosql-couchbase-mongodb-cassandra.md`](../topics/11-nosql-couchbase-mongodb-cassandra.md) · **Guide:** Q74–Q81

## What interviewers are actually probing

The requirement says "Couchbase / MongoDB / Cassandra or similar", so they test **the mindset shift**, not product trivia:
model for the **query** instead of normalising, accept **eventual consistency** with tunable knobs, understand the **partition/shard key** (the most important decision),
and know when SQL is still the right answer. Be honest about which one you have used, then show you understand the model.

## Must-know points

- NoSQL = several models: **document** (MongoDB, Couchbase), **wide-column** (Cassandra), key-value (Redis, DynamoDB), graph. They aren't interchangeable.
- Document stores: embed vs reference; single-document writes are atomic; secondary indexes and `explain()` matter; multi-document transactions exist but cost.
- Cassandra: **partition key** chooses the nodes, **clustering columns** sort within the partition; one table per query; no joins; writes are cheap; tunable consistency (`ONE`, `QUORUM`, `LOCAL_QUORUM`, `ALL`).
- **CAP**: during a partition choose consistency or availability; **PACELC** adds the latency/consistency trade-off when there's no partition.
- **R + W > N** gives read-your-latest-write overlap with N replicas.
- Hot partitions, unbounded partitions and tombstones are the classic Cassandra incidents; unbounded arrays/documents and missing indexes the document-store ones.

## Interview questions and full answers

### Q1. When would you pick NoSQL over a relational database, and when not?

Pick it when the **access pattern and scale** fit: huge write throughput or data volume with simple key-based access (Cassandra), flexible/hierarchical documents with evolving shape (MongoDB/Couchbase), low-latency key lookups and caching (Couchbase/Redis), multi-region active-active.
Stay relational when you need **complex joins, ad hoc queries, strong multi-row ACID, reporting**, or the data is small and relational — a well-indexed PostgreSQL scales further than most teams need. "Polyglot" is fine: Postgres as system of record, Couchbase/Redis for read models.

### Q2. Compare MongoDB, Couchbase and Cassandra.

| | MongoDB | Couchbase | Cassandra |
|---|---|---|---|
| Model | JSON/BSON documents, collections | JSON documents in buckets/scopes/collections | wide-column, partitioned rows |
| Query | rich query + aggregation pipeline | **N1QL/SQL++**, key-value, FTS | **CQL**, query-first, limited |
| Scale | sharding (shard key) + replica sets | auto-sharding (vBuckets), memory-first | consistent hash ring, peer-to-peer |
| Consistency | strong by default on primary (tunable read/write concern) | strong per doc via active vBucket; CAS; XDCR is eventual | tunable per query; AP by default |
| Sweet spot | flexible app data, analytics-lite | caching + KV + SQL++ with low latency | massive writes, time series, always-on |
| Watch out | shard key choice, unbounded arrays | memory sizing, index service, N1QL cost | modelling, tombstones, repairs |

### Q3. Embed or reference in a document model?

**Embed** data read together, bounded in size, and owned by the parent (order lines). **Reference** when it grows unbounded (comments, events), is shared/updated independently (customer profile), or documents would approach the size cap (16 MB MongoDB).
Duplicate (denormalise) fields you need frozen in time (invoice snapshot of price/address) and accept update fan-out for the rest. Atomicity is per document, so model the unit of consistency as one document.

### Q4. How do indexes work in document databases and how do you tune queries?

B-tree style secondary indexes (compound, partial, TTL, text/geo). Check `explain()` for `COLLSCAN` vs `IXSCAN`, `docsExamined ≫ nReturned`, in-memory sorts (example 13/01 section 1: 100,000 docs examined vs 23).
Compound index order: **Equality, Sort, Range (ESR)**. Indexes cost write amplification and memory — index for real queries only. In Couchbase use **covering indexes** and `EXPLAIN`; unneeded primary indexes are an anti-pattern.

### Q5. What is eventual consistency and how do you live with it?

Replicas may temporarily disagree; given no new writes they converge. Techniques: read-your-writes by routing a user's reads to the primary or using session/causal consistency; **idempotent, commutative** updates; versions/CAS and timestamps for conflict resolution (last-write-wins is lossy);
compensating actions; design UX for "pending". Choose per operation (`QUORUM` for balances, `ONE` for a view counter).

### Q6. Explain Cassandra's architecture in simple terms.

Peer-to-peer ring (no master). A row's **partition key** is hashed to a token owned by a node (with **virtual nodes** for balance); the next RF−1 nodes clockwise hold replicas (example 13/02 section 1).
Writes go to a **commit log + memtable** and flush to immutable **SSTables**; background **compaction** merges them. A coordinator node (any node) handles the request and waits for the required replicas per the consistency level.
Repair mechanisms: **hinted handoff**, **read repair**, **anti-entropy repair** (`nodetool repair`).

### Q7. What are partition keys, clustering keys and "query-first" modelling?

`PRIMARY KEY ((customer_id), order_ts, order_id)`: `customer_id` = partition key (placement; all rows of a customer live together), `order_ts, order_id` = clustering columns (on-disk sort order within the partition).
You design **one table per query** (`orders_by_customer`, `orders_by_id`), duplicating data — there are no joins and writes are cheap. A query must provide the full partition key; `ALLOW FILTERING` is a smell.
Bound partitions (e.g. `(sensor_id, day)`) so they don't grow forever.

### Q8. What is a hot partition and how do you avoid it?

One partition receiving disproportionate traffic or growth (celebrity user, "today" as the key, one tenant) overloads its replica set no matter how big the cluster.
Fixes: add a **bucket/salt** to the key (`(user_id, bucket)` with read fan-out), time-bucket partitions, choose a higher-cardinality key, cache the hot reads. Detect via per-node load skew and large partition warnings.

### Q9. Explain tunable consistency and quorum.

With replication factor N, a write waits for W acks and a read consults R replicas. If **R + W > N** the sets overlap, so reads see the latest acknowledged write (example 13/02 section 2). RF=3: `QUORUM` = 2; `QUORUM` read + `QUORUM` write = strong, tolerates one node down.
`LOCAL_QUORUM` confines this to the local data centre (low latency); `ALL` hurts availability; `ONE` is fast but may be stale. Lightweight transactions (`IF NOT EXISTS`, Paxos) give compare-and-set at ~4× the latency.

### Q10. CAP theorem and PACELC — apply them.

CAP: under a **network partition** you choose Consistency or Availability (not both). Cassandra defaults to AP, tunable towards CP per query; MongoDB's primary-based writes favour C (a minority partition can't accept writes); Couchbase favours C per document with eventual cross-cluster replication (XDCR).
PACELC: else (no partition) you still trade **Latency vs Consistency** — e.g. waiting for more replicas. Mentioning PACELC signals depth.

### Q11. How do you handle duplicates and idempotency with NoSQL?

Use deterministic keys (`orderId`, or `eventId`) with **insert-if-absent** (`upsert`, Couchbase `insert`, Mongo `_id` unique, Cassandra LWT `IF NOT EXISTS` sparingly); CAS/version for updates; store processed event ids with TTL.
This is the sink side of at-least-once Kafka consumers (chapter 12).

### Q12. How do you migrate from SQL to NoSQL, or run both?

List the **queries**, not the tables; model documents/partitions per query; migrate with dual write or CDC (Debezium → Kafka → sink) and a verification/backfill job; shift reads gradually behind a flag; keep the relational store as source of truth until parity is proven. Beware re-implementing joins in application code — that's the sign you chose the wrong store for that data.

### Q13. Couchbase specifics worth knowing?

Memory-first architecture (managed cache + persistence), **buckets/scopes/collections**, services you scale independently (data, query, index, search, eventing, analytics), **N1QL/SQL++**, **CAS** for optimistic concurrency, sub-document operations (patch a field without re-writing the whole doc), TTL on documents, **XDCR** for cross-data-centre replication, durability levels (`majority`, `persistToMajority`).
Spring Data Couchbase gives repositories and `CouchbaseTemplate`; the Java SDK is async/reactive-capable.

### Q14. MongoDB specifics worth knowing?

Replica sets (primary + secondaries, automatic failover), read preference/concern and write concern (`w: majority`), sharding with a shard key (hashed vs ranged; a monotonically increasing key creates a hot shard), aggregation pipeline, change streams (CDC), TTL indexes, schema validation, transactions (4.0+/4.2 sharded).
Spring Data MongoDB: `MongoRepository`, `MongoTemplate`, `@Document`, `@Indexed`, optimistic `@Version`.

## A worked example

Run [`01_document_store_indexes_and_modeling.java`](../examples/13_nosql/01_document_store_indexes_and_modeling.java) and quote the 100,000-vs-23 comparison when asked about indexes.
Run [`02_cassandra_ring_quorum_and_modeling.java`](../examples/13_nosql/02_cassandra_ring_quorum_and_modeling.java): section 3 stages a quorum write while one replica is down, then shows a `ONE` read returning stale `v1` and a `QUORUM` read returning `v2`.

## Hands-on drills

1. Model "order history per customer" and "lookup by order id" for Cassandra; write both `CREATE TABLE` statements and the write path that keeps them in sync.
2. Design a MongoDB schema for a blog with comments and justify embed vs reference with growth numbers.
3. For a 5-node RF=3 ring, list which failures each consistency level tolerates for reads and writes.
4. Write the Couchbase N1QL query and index for "latest 20 PAID orders for a customer" and say what makes it covering.
5. Explain why a timestamp partition key is dangerous and show a bucketing fix.

## The 60-second spoken answer

"I choose a NoSQL store when the access pattern and scale fit it, and I model for the queries instead of normalising: embedded documents with a
bounded size in MongoDB or Couchbase, one table per query with a well-distributed partition key in Cassandra. I know consistency is tunable —
with replication factor N, R plus W greater than N overlaps — and I pick per operation. The incidents I design against are hot or unbounded
partitions, missing indexes, and duplicate writes, so I use idempotent upserts keyed by a business id. For complex joins and ACID reporting I'd keep a relational database."
