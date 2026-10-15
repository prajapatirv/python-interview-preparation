---
id: foundations-nosql
title: NoSQL: Couchbase, MongoDB, Cassandra: from the basics (drafted)
stack: java
skill: nosql
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is NoSQL and why use it?
tags: nosql, document-store, key-value, wide-column, horizontal-scaling, data-modelling, basics

**Start here: the concepts**
- **Relational database (SQL):** data lives in tables with fixed columns, and tables are linked by keys. You combine them with joins. It exists to keep data consistent and to answer flexible questions.
- **NoSQL:** a broad label for databases that are not built around relational tables. People often read it as "not only SQL". Each type trades some relational features for something else, usually scale, speed or flexibility.
- **Document store (MongoDB, Couchbase):** stores each record as a JSON-like document. One document can hold an order with its line items inside it.
- **Key-value store:** you give a key and get a value back, like a giant dictionary. Couchbase works this way for fast lookups.
- **Wide-column store (Cassandra):** rows are grouped by a partition key, and rows inside a partition are sorted by clustering columns. It is built for very heavy writes.
- **Graph database:** stores things and the relationships between them, which suits "friends of friends" questions.
- **Flexible schema:** two records in the same collection can have different fields, so you can add a field without altering a table.
- **Sharding / partitioning:** splitting data across many machines by a key, so each machine holds only a slice. Adding machines adds capacity. This is called horizontal scaling, in contrast to buying one bigger machine.
- **Access pattern:** the exact queries your application will run. In NoSQL you design the data around these.

**The live scenario**
An e-commerce app stores product-view events. Traffic grows from 2,000 to 40,000 writes per second during a sale. The single relational database hits 90% CPU and p99 latency goes from 20 ms to 800 ms. The team moves the event data to a wide-column store spread over 9 nodes. Writes spread across the nodes and p99 drops back to about 15 ms. But a report that joined events to customers now needs extra work, because the new store has no joins. The choice solved the scale problem and cost query flexibility.

**What the interviewer is really checking**
Whether you know NoSQL is a family of different stores with trade-offs, not "faster SQL". They also want to hear that you start from access patterns and know when SQL is still the better choice.

**How I answer it**
1. **Define it simply.** NoSQL means databases that are not relational tables: document, key-value, wide-column and graph. This shows you know it is several types.
2. **Give the reasons to use it.**
   - Flexible schema, so the data shape can change without migrations.
   - Horizontal scale by sharding, so you add cheap nodes instead of one giant server.
   - High write throughput, because writes go to many nodes in parallel.
   - Low-latency access by key, because the store goes straight to the right node.
3. **State the costs.** Joins are weak or absent, and transactions are usually narrower than in SQL. Some stores do offer them within limits, for example MongoDB multi-document transactions since version 4.0 and Cassandra lightweight transactions on a single partition.
4. **Explain the modelling shift.** In SQL you model the entities and then write any query. In NoSQL you list your queries first, then shape the data to answer them, often copying data on purpose (denormalising). The reason is that the store is fast only for the queries it was designed around.
5. **Match store to need.** Cassandra suits write-heavy time series. MongoDB suits flexible documents with rich queries. Couchbase suits low-latency key-value plus documents.

**Trade-offs and what can go wrong**
- Choosing NoSQL just because it is fashionable, when data is small and relational and SQL would be simpler.
- Poor key choice creates a hot partition, where one node takes most of the traffic.
- Denormalised copies can go out of sync, so your code must update every copy.
- Many stores are eventually consistent by default, meaning a read right after a write may briefly return old data. Consistency is usually tunable, but you must choose deliberately.
- Query patterns that change later can force a costly remodel.

**How I'd monitor it**
- Read and write latency at p95 and p99, per node.
- Per-node CPU, disk and request counts, to spot skew and hot partitions.
- Replication lag and timeout or error rates.
- Document or partition size growth.
- In Splunk, alert on slow-query or timeout log events and chart them by node.

**Follow-ups to expect**
- *Does NoSQL mean no transactions?* -> No. MongoDB supports multi-document ACID transactions since 4.0 and Cassandra has per-partition lightweight transactions, but they cost more and are narrower than in SQL.
- *What is eventual consistency?* -> Replicas may briefly disagree after a write, but they converge. Stores such as Cassandra let you tune how many replicas must respond.
- *When would you still pick SQL?* -> When data is relational, queries are varied, strong transactions matter and the volume fits a well-run database.

**60-second answer**
NoSQL is a group of databases that are not relational tables: document, key-value, wide-column and graph. People use them for a flexible schema, horizontal scaling by splitting data across many machines, high write throughput and fast lookups by key. The cost is weaker joins and narrower transactions, though some stores offer limited ones. You also have to design data around the queries you will run, not just the entities. In practice I would pick Cassandra for heavy time-series writes, MongoDB for flexible documents with rich queries, and Couchbase for low-latency key-value access. If the data is small, relational and queried in varied ways, I would stay with SQL.

### Q2 [fresher] Name the NoSQL types with one example each.
tags: nosql, key-value, document-store, wide-column, couchbase, basics

**Start here: the concepts**
- **NoSQL**: a database that does not use the classic relational model of tables, joins and fixed columns. It exists because some workloads need huge scale, very low latency or flexible data shapes. Relational databases handle those workloads awkwardly. "NoSQL" is a family of different designs, not one product type.
- **Key-value store**: works like a giant dictionary. You give it a key and it returns the value. It is very fast because the only question it answers is "get this key". Examples: Redis, DynamoDB.
- **Document store**: stores each record as a self-contained document, usually JSON, so one read returns a whole order or profile. Examples: MongoDB, Couchbase.
- **JSON**: a text format for nested data, such as `{"name":"Asha","items":[...]}`.
- **Wide-column store**: rows are found by a partition key, and each row can hold many columns, laid out for fast writes and scans within a partition. Examples: Cassandra, HBase.
- **Partition key**: the value the database hashes to decide which machine holds the data.
- **Graph database**: stores things (nodes) and the relationships between them (edges), so questions like "friends of friends" are cheap. Example: Neo4j.
- **Search engine**: builds an index of words so you can run text search with ranking. Examples: Elasticsearch, OpenSearch.
- **N1QL**: Couchbase's SQL-like query language for JSON. Couchbase now also calls it SQL++.
- **Full-text search**: finding documents by the words inside them, not by exact values.

**The live scenario**
A shopping app runs on one relational database. At a sale peak it handles about 5,000 requests per second. Session lookups, product text search (`LIKE '%shoe%'`) and order-event writes all hit the same database. The p99 latency (the time within which 99% of requests finish) climbs from about 20 ms to nearly 1 second. The team splits the load by access pattern:
- Sessions go to Redis.
- The product catalogue goes to a document store.
- Search goes to Elasticsearch.
- High-volume order events go to Cassandra.

Each store does the job it was designed for, and latency recovers.

**What the interviewer is really checking**
Whether you know that NoSQL is several different models, and whether you can match each model to the kind of question it answers well. Memorising names is not enough.

**How I answer it**
1. **Say the five families first**, because the question asks for types. They are key-value, document, wide-column, graph and search.
2. **Give one example per family**: Redis or DynamoDB, MongoDB or Couchbase, Cassandra or HBase, Neo4j, Elasticsearch or OpenSearch. One example is enough, and naming it shows you have met a real product.
3. **Add one line on what each is good at**: fast lookup by key, flexible whole-record reads, heavy writes by partition key, relationships, and text search. This shows you choose by access pattern (how the data will be read) and not by fashion.
4. **Mention that Couchbase spans models**: it offers key-value access, JSON documents, N1QL queries and full-text search in one product. It shows that real products often blur the categories.
5. **Be honest about the edge**: Elasticsearch is a search engine, and many teams treat it as a secondary copy of data kept elsewhere. Some people do not call it a database at all.

**Trade-offs and what can go wrong**
- Most NoSQL stores trade joins and flexible ad-hoc queries for speed and scale. You must design for your queries up front.
- Picking one store "because it is popular" for every need is the classic mistake.
- Several stores mean more systems to run, and data copied between them can drift out of sync.
- Consistency (whether every reader sees the latest write) differs by product and by setting. Do not assume it matches a relational database.

**How I'd monitor it**
- Track p99 read and write latency per store.
- Watch the cache hit ratio for Redis.
- Check node health, disk usage and replication lag.
- For partitioned stores, look for hot partitions, where one key gets far more traffic than the others.
- Search logs in Splunk for timeout and connection errors, grouped by data store.
- Alert when p99 latency or error rate crosses an agreed limit.

**Follow-ups to expect**
- *Is Elasticsearch a primary database?* -> Usually not. It is typically a search index fed from a system of record, because it is built for search, not strict durability.
- *When Cassandra over MongoDB?* -> Cassandra for very heavy writes with known queries, such as time series. MongoDB for flexible documents and richer queries.
- *Does NoSQL mean no SQL?* -> No. Couchbase has N1QL/SQL++, and "NoSQL" really means "not only the relational model".

**60-second answer**
NoSQL is a family of databases that do not use the relational table model. The main types are key-value, such as Redis or DynamoDB, and document, such as MongoDB or Couchbase. Then there is wide-column, such as Cassandra or HBase, graph, such as Neo4j, and search, such as Elasticsearch. Each fits a different access pattern. Key-value is for fast lookups, documents are for whole JSON records, wide-column is for heavy writes by partition key, graph is for relationships, and search is for text queries. Couchbase is a good example of mixing models, because it gives key-value access, JSON documents, N1QL queries and full-text search. I choose by how the data will be read, and I accept that this means designing around my queries up front.

### Q3 [fresher] SQL vs NoSQL - how do you choose?
tags: sql, nosql, data-modelling, consistency, scalability, polyglot-persistence, basics

**Start here: the concepts**
- **SQL (relational) database:** Data lives in tables with rows and columns, and the schema (the table layout) is defined up front. You can combine tables with joins. Examples are PostgreSQL, MySQL and Oracle. They exist to keep data correct and consistent.
- **NoSQL database:** A broad name for stores that are not table-and-join based. The main kinds are document stores (MongoDB, Couchbase), wide-column stores (Cassandra) and key-value stores. They exist mainly to spread data over many machines easily and to store flexible shapes of data.
- **Strong consistency:** After a write succeeds, every reader sees the new value. This matters for money. The opposite is eventual consistency, where replicas may briefly disagree and then catch up.
- **Transaction (ACID):** A group of changes that all succeed or all fail together, such as debiting one account and crediting another.
- **Join:** Combining rows from two tables in one query, for example orders with customers.
- **Schema:** The agreed structure of the data. A stable schema rarely changes. An evolving one changes often, such as new product attributes.
- **Access pattern:** The exact questions your application asks the database, such as "get the profile by user id".
- **Horizontal scaling:** Adding more machines instead of buying a bigger one. NoSQL databases are usually built for this, while relational databases find it harder.
- **Polyglot persistence:** Using different databases for different parts of one system.

**The live scenario**
An e-commerce team (illustrative numbers) kept everything in one relational database: orders, payments, product catalog, sessions and click events. During a sale, click events reached about 20,000 writes per second. The database CPU hit its limit and checkout latency rose from 50 ms to 2 s, so payments slowed down because of unimportant events. The team kept orders and payments in SQL, where they need transactions. They moved click events and sessions to a store built for heavy writes, and the catalog to a document store. Checkout became fast again, and money data stayed strictly correct.

**What the interviewer is really checking**
Whether you choose from the data's needs (correctness, shape, scale, access pattern) instead of from fashion, and whether you know that real systems often use both.

**How I answer it**
1. **Ask what must never be wrong.** Money, orders and inventory need strong consistency and multi-row transactions, so I start with SQL. Reason: relational databases were designed to protect correctness.
2. **Ask how the data will be read.** If I need ad-hoc queries, joins and reports, I choose SQL. If I know the few exact queries in advance (profile by id, events by user and time), NoSQL works well. Reason: NoSQL models data around queries, not around entities, and it often copies data on purpose (denormalising) so one read answers one question.
3. **Ask how stable the shape is.** A stable schema suits SQL. Documents that evolve, such as product catalogs with different attributes per category, suit a document store. Reason: you add fields without a table migration.
4. **Ask about scale and availability.** For very high write volume or users in several regions, NoSQL stores spread data across nodes and keep running if one fails. Reason: this is what they were built for.
5. **Don't treat the split as absolute.** Relational databases can scale with replicas and sharding. Several NoSQL stores now offer transactions (MongoDB multi-document transactions since 4.0, for example), though with limits. Cassandra lets you tune consistency per query.
6. **Combine when needed.** Use SQL for orders and payments, and NoSQL for profiles, catalogs, sessions and events. Reason: each part gets the tool that fits.

**Trade-offs and what can go wrong**
- NoSQL gives up easy joins and ad-hoc queries. A query you didn't plan for can be slow or impossible.
- Eventual consistency can show stale data if you don't design for it.
- A badly chosen partition key (the field deciding which node stores the data) creates a hot partition: one node overloaded while the others idle.
- Choosing NoSQL just because it is trendy, or SQL out of habit, are both common mistakes.
- Several databases means more to operate, back up and monitor.

**How I'd monitor it**
- p95/p99 read and write latency per store.
- Slow-query logs in SQL, and per-node load in NoSQL to spot hot partitions.
- Replication lag and node-down alerts.
- Disk growth.
- Timeout and error counts, searched in Splunk by service and database name.

**Follow-ups to expect**
- *Does NoSQL mean no transactions?* -> No. MongoDB and Couchbase support multi-document transactions, and Cassandra has lightweight conditional writes. They are more limited and costlier than in a relational database.
- *Can SQL scale?* -> Yes, with read replicas, partitioning and sharding, but it takes more effort than in stores designed for it.
- *What is polyglot persistence?* -> Using several database types in one system, each for the data it suits.

**60-second answer**
I choose by what the data needs. If correctness matters most, as with orders and payments, and I need transactions, joins and reports on a stable schema, I use SQL. If I need huge scale, high availability across regions, flexible documents that change often, or I know my exact queries in advance, I use NoSQL. With NoSQL I model data around the queries and accept less flexible querying and sometimes eventual consistency. The line is not absolute, because some NoSQL stores offer transactions and SQL can scale with effort. In real systems I often use both, with SQL for money and NoSQL for profiles, catalogs, sessions and events.

### Q4 [mid] Explain the CAP theorem and what "eventual consistency" means.
tags: cap-theorem, eventual-consistency, pacelc, consistency, cassandra, mongodb, basics

**Start here: the concepts**
- **Replica**: a copy of the same data on another machine. We keep replicas so one machine failing does not lose data or stop the service, and so reads can be spread out.
- **Network partition**: the network breaks so that some nodes cannot talk to others, although each node is still running. This happens in real systems (a switch fails, a data-centre link drops).
- **Consistency (the C in CAP)**: every read sees the latest successful write, as if there were one copy of the data. The formal name is linearizability.
- **Availability (the A in CAP)**: every request to a working node gets a real answer, not an error or timeout.
- **Partition tolerance**: the system keeps working when a partition happens. Any system spread over a network must tolerate partitions, so in practice it is not optional.
- **CAP theorem**: during a partition you cannot have both C and A. Outside a partition you can have both. It is not "pick two of three" for all time.
- **CP vs AP**: a CP system refuses or fails some requests to avoid returning wrong data. An AP system always answers, but the answer may be stale.
- **Eventual consistency**: replicas may disagree for a while, but if no new writes arrive they all converge to the same value.
- **PACELC**: if there is a Partition, choose Availability or Consistency. Else (normal running), choose Latency or Consistency. Waiting for more replicas to confirm costs time, even with no failure.

**The live scenario**
A retail platform runs Cassandra in two data centres, with 3 replicas per key. It handles about 20,000 reads/s. The link between the data centres drops for 4 minutes. The shopping-cart and product-view services keep answering using the local copy. A few customers see a cart that is a few seconds old, and it fixes itself after the link returns. The account-balance and stock-reservation features were also on the cluster and needed the latest value. They used a stricter setting, so some of their requests failed during those 4 minutes. The team had to decide per feature which was worse: a stale answer or an error.

**What the interviewer is really checking**
Whether you know CAP applies only during a partition, and whether you can connect it to real choices such as tunable consistency, instead of just reciting "pick two".

**How I answer it**
1. **State the theorem precisely.** When a partition happens, I must choose between consistency and availability. The reason is that a node cut off from the others cannot know whether it has the latest data. It can answer anyway (stale risk) or refuse (unavailable).
2. **Say partition tolerance is not a real choice.** Networks fail, so a distributed system has to survive partitions. The real choice is C or A while one is happening.
3. **Define CP and AP with an example.** A CP system rejects some requests to stay correct. An AP system answers everything and may return old data. Many databases are tunable per operation, so a database is not permanently one label.
4. **Define eventual consistency.** Replicas accept writes independently and sync in the background. If writes stop, all replicas end up equal. Until then, readers can see old values.
5. **Add PACELC.** Even with a healthy network, waiting for more replicas gives stronger consistency but higher latency. This is the everyday trade-off, and it is more common than partitions.
6. **Tie it to tuning.** In Cassandra with replication factor N=3, if reads (R) and writes (W) are acknowledged by enough replicas that `R + W > N`, a read overlaps the latest write. QUORUM (2 of 3) on both gives 2+2>3. In MongoDB, write concern and read concern `majority` give stronger guarantees. In Couchbase, durability levels and CAS (compare-and-swap, a version check on writes) protect against lost updates.
7. **Choose per feature.** Carts and feeds tolerate staleness. Payments and inventory usually need strong consistency.

**Trade-offs and what can go wrong**
- Strong consistency means higher latency and errors during partitions.
- Eventual consistency means stale reads and conflicting concurrent writes. You need a conflict rule (for example last-write-wins, which can silently drop updates) or conditional writes.
- A common mistake is calling a database "CP" or "AP" as a fixed label. Behaviour depends on settings and version.
- Another mistake is assuming eventual consistency means "data may be lost". It means data converges, not that it vanishes.

**How I'd monitor it**
- Read and write latency percentiles per consistency level.
- Error and timeout rates for strict-consistency operations during network incidents.
- Replica repair or hint backlog, and replication lag between data centres.
- Splunk searches for "UnavailableException" or timeout errors, grouped by service and time.
- Alerts on cross-DC link health.

**Follow-ups to expect**
- *Is Cassandra CP or AP?* -> It is tunable. ONE favours availability, and QUORUM or ALL favours consistency at the cost of availability.
- *What does the "E" in PACELC mean?* -> "Else": when there is no partition, you still trade latency against consistency.
- *How do you handle stale reads in an eventually consistent store?* -> Use conditional writes or CAS, versioning, read-your-writes via quorum reads, and idempotent updates.

**60-second answer**
The CAP theorem says that when a network partition happens, a distributed system must choose between consistency and availability. Partition tolerance is not optional, because networks fail. A CP system refuses some requests to avoid wrong answers. An AP system keeps answering but may return stale data. Eventual consistency means replicas may differ for a while, but they converge if writes stop. PACELC adds that even with no partition, you trade latency against consistency. In practice I choose per feature: Cassandra QUORUM or MongoDB majority for payments, and relaxed settings for carts or feeds.

### Q5 [mid] How do you model data in a document database?
tags: document-database, mongodb, data-modelling, embedding-vs-referencing, denormalisation, couchbase, basics

**Start here: the concepts**
- **Document database:** it stores each record as a self-contained JSON-like document (MongoDB uses BSON, a binary form of JSON). A document can hold nested objects and lists, so one record can carry data that a relational database would spread across several tables.
- **Normalisation:** storing each fact once and linking tables with keys. It avoids duplicates, but reading related data needs joins.
- **Denormalisation:** deliberately copying data into several places so one read gets everything. It exists because reads are fast when the data is in one place.
- **Embedding:** putting related data inside the parent document, e.g. line items inside an order.
- **Referencing:** storing only an ID that points to another document, e.g. `customerId` in the order.
- **Unbounded array:** a list inside a document that can grow forever, such as every comment on a popular post.
- **Document size limit:** MongoDB caps a document at 16 MB. Couchbase also has a cap (about 20 MB, so check the docs for your version).
- **Update path:** every place a copied value lives. If you copy data, you must update all those places.

**The live scenario**
An e-commerce team ports its relational schema to MongoDB table by table: `orders`, `order_items`, `customers`, `products`. The order page now needs 4 queries and application-side stitching. Latency is 180 ms at 2,000 requests/sec. Separately, a `watchers` array on a "flash sale" product grows to millions of entries, and writes start failing near the size limit. The team remodels. Order and line items are embedded, with a snapshot of product name and price at purchase time. The customer is referenced. Watchers move to their own collection. The order page becomes one read of about 15 ms.

**What the interviewer is really checking**
Whether you start from the application's queries rather than from entity diagrams. They also want to see that you know the limits (document size, unbounded growth) and that you can state the cost of denormalising.

**How I answer it**
1. **List the queries first.** Write down the screens and APIs, with read/write ratios. A document store has no cheap joins, so the shape of the document must match how it is read.
2. **Embed what is read together and changes together.** Order plus line items belong in one document. One read returns everything, and a write to one document is atomic. Multi-document transactions exist in MongoDB (since 4.0) but cost more.
3. **Reference what is large, shared, or changes independently.** A customer profile is shared by many orders and edited on its own. Embedding it would mean updating thousands of copies.
4. **Keep arrays bounded.** The 16 MB limit is the hard stop, but large documents also slow every read and write, since the whole document is loaded and rewritten. If a list can grow without limit, make it its own collection with a parent ID.
5. **Denormalise on purpose and own the update path.** Copy only fields that are read often and change rarely, such as a product name snapshot. Decide who updates the copies: the same write, an event consumer, or a batch job. Some copies should never change, e.g. the price paid on an order.
6. **Index for the queries.** Add indexes matching the filters and sorts from step 1, and check them with `explain`.

**Trade-offs and what can go wrong**
- Embedding speeds reads but duplicates data. Copies drift out of sync if the update path is not owned.
- Referencing keeps data consistent but costs extra reads. `$lookup` is not a free join.
- Large or ever-growing documents hurt memory and write speed long before reaching 16 MB.
- Common mistake: copying the relational schema one-to-one, or embedding everything because "it is a document store".
- The model fits today's queries. A new access pattern may need a remodel or a migration.

**How I'd monitor it**
- Document size distribution (e.g. aggregate on `$bsonSize`) and the maximum array length per collection.
- Slow query log or profiler, plus `explain` to catch collection scans.
- Count of queries per request; a rise suggests too many references.
- Consistency checks that compare copied fields with their source, and lag on the job that updates copies.
- Splunk searches on slow-operation logs and write errors such as "document too large", with alerts.

**Follow-ups to expect**
- *When do you embed versus reference?* -> Embed when data is read together, is bounded, and changes together. Reference when it is large, shared, or updated independently.
- *How do you keep denormalised copies correct?* -> Name one owner for updates, using the same write or an event-driven consumer. Make the consumer idempotent and reconcile periodically.
- *What if a list grows without limit?* -> Move it to a separate collection with a parent ID, or use a bucket pattern with fixed-size chunks.

**60-second answer**
In a document database I model for the queries, not for normalisation. First I list how the application reads and writes data. Data that is read together and bounded, like an order and its line items, I embed in one document, so one read serves the page. Data that is large, shared, or changes on its own, like the customer, I reference by ID. I keep arrays bounded because MongoDB caps documents at 16 MB, and huge documents are slow anyway. If I copy data, I decide up front who updates the copies. I check it all with explain plans and by watching document sizes.

### Q6 [mid] What is Couchbase and what are its main building blocks?
tags: couchbase, nosql, document-database, vbuckets, multi-dimensional-scaling, xdcr, basics

**Start here: the concepts**
- **Document database:** it stores each record as a self-contained JSON document (for example one customer with their addresses inside), found by a unique **key** (document id). It exists so data that is read together is stored together, with no joins.
- **Memory-first:** the Data service keeps recently used documents in RAM and serves reads from there. Writes are acknowledged from memory and persisted to disk in the background by default. That is why key lookups are very fast, typically sub-millisecond to low milliseconds.
- **Bucket -> scope -> collection:** the containers for documents. A bucket is the top-level unit that owns memory quota and replica settings. A scope groups collections, and a collection is like a table of documents. The usual analogy is database -> schema -> table. Scopes and collections arrived in Couchbase 7.0; earlier versions had only buckets.
- **vBucket:** a bucket's key space is split into 1024 fixed shards (64 on macOS). The cluster hashes each key (CRC32) to pick a vBucket, and each vBucket lives on one node, with replica copies on others. When nodes are added or removed, whole vBuckets move, never individual documents.
- **Services:** Data (key-value storage), Query (SQL++/N1QL), Index (secondary indexes), Search (full-text), Eventing (code that reacts to changes) and Analytics (heavy analytical queries). Each is a separate process.
- **Multi-Dimensional Scaling (MDS):** you choose which nodes run which services, so you can scale or size each independently.
- **XDCR (Cross Data Center Replication):** copies data between separate clusters, for disaster recovery or for placing data near users.

**The live scenario**
A cart service on Couchbase handles 20,000 key-value reads and writes per second with a p99 target of 5 ms. The team also runs an "orders by customer" query, and it works. Then a nightly index build on the same nodes drives CPU to 90%, and cart p99 jumps to 80 ms. The fix is MDS: move Index and Query to their own nodes and keep the Data nodes for key lookups. The cart latency recovers because the services no longer compete for the same CPU.

**What the interviewer is really checking**
Whether you can explain how Couchbase distributes and serves data (vBuckets, memory-first) and why separating services matters, not just recite a feature list.

**How I answer it**
1. **Define it:** a distributed JSON document database that combines a key-value cache and a document store. This sets the context for everything else.
2. **Describe the hierarchy:** bucket -> scope -> collection, with documents identified by key. The reason is that you organise data and permissions per collection, much like tables.
3. **Explain distribution:** the key is hashed to one of 1024 vBuckets, and vBuckets are spread across nodes with replicas. The SDK client holds the cluster map and goes straight to the right node, so there is no central router to bottleneck.
4. **Explain memory-first:** reads and writes hit RAM first, and disk persistence follows. This gives speed, but if you need a write confirmed as replicated or persisted, you ask for a durability level (Couchbase 6.5+).
5. **List the services and MDS:** Data, Query, Index, Search, Eventing and Analytics. Each has a different resource profile, so you scale them separately.
6. **Close with XDCR:** replication between clusters for DR or locality. It is asynchronous, so it is eventually consistent.

**Trade-offs and what can go wrong**
- Memory-first means you must size RAM for your working set. If it does not fit, reads fall back to disk and latency rises.
- Default writes are acknowledged before they are replicated or persisted. A node failure at the wrong moment can lose them unless you use durability levels, which cost latency.
- Queries need indexes. A query with no suitable index is slow or fails, and indexes consume memory and CPU.
- Mixing all services on every node is easy at first but causes the contention shown in the scenario.
- XDCR with writes in both clusters can create conflicts, so you must decide on a conflict-resolution approach.

**How I'd monitor it**
- Data service: cache hit ratio, resident ratio (the share of documents held in RAM), ops per second, disk write queue and replication queue.
- Query and Index: query latency and slow-query logs, index build and lag status.
- XDCR: replication backlog and lag between clusters.
- Per-node CPU and memory for each service.
- Application side: search Splunk for SDK timeout exceptions and correlate them with slow-query entries.

**Follow-ups to expect**
- *How does a client find the right node for a key?* -> It hashes the key to a vBucket and looks up the owning node in the cluster map it holds.
- *What does Couchbase use for safe concurrent updates?* -> CAS (compare-and-swap): a document version token, and an update fails if the token has changed since you read it.
- *Why use MDS?* -> So Data, Query and Index workloads do not steal CPU or memory from each other, and each can be sized on its own.

**60-second answer**
Couchbase is a distributed JSON document database with a memory-first design, so key lookups are very fast. Data is organised as bucket, scope and collection, which is roughly database, schema and table, and each document has a key. Under the hood each bucket is split into 1024 vBuckets. The key is hashed to a vBucket, and vBuckets are spread across nodes with replicas, so the cluster can rebalance by moving shards. It has separate services: Data, Query, Index, Search, Eventing and Analytics. With Multi-Dimensional Scaling I can run and size them on different nodes, so a heavy index build does not hurt key-value latency. For disaster recovery or regional data, XDCR replicates between clusters asynchronously.

### Q7 [mid] Couchbase consistency, durability and concurrency?
tags: couchbase, cas, durability, consistency, n1ql, optimistic-locking, transactions, basics

**Start here: the concepts**
- **Document and key:** Couchbase stores JSON documents under a unique key. Reading or writing by key is the fastest path.
- **Atomic single-document write:** A write to one document either fully happens or doesn't. Nobody sees half a document. This is why one document per aggregate (e.g. an order with its lines) is safe by default.
- **CAS (compare-and-swap):** Every document carries a version-like number that changes on each write. You read the document and its CAS, then write it back with that CAS. If someone else changed it in between, the write fails. This is **optimistic locking**: you assume no conflict and detect one only when it happens. It exists to stop lost updates.
- **Replica and failover:** Copies of data live on other nodes. If a node dies, a replica is promoted (failover).
- **Durability level:** By default a write is acknowledged once it is in memory on the active node. If that node dies before replicating, the write can be lost. A durability level makes the server wait for more copies before acknowledging:
  - `majority`: in memory on a majority of copies.
  - `majorityAndPersistToActive`: majority in memory, plus on disk on the active node.
  - `persistToMajority`: on disk on a majority.
- **Multi-document ACID transaction:** Several documents change all-or-nothing, with isolation from other readers. It is supported from about Couchbase 6.5 via the SDK; check the docs for your server and SDK version.
- **N1QL (SQL++) and scan consistency:** Queries use global secondary indexes, which update slightly after a write. The default `not_bounded` can miss very recent writes. `REQUEST_PLUS` waits for the index to catch up to the moment of the request.

**The live scenario**
An order service runs 6 pods and handles about 800 updates/s. Two pods updated the same order within milliseconds (a payment callback and a "cancel" click), and the later write silently overwrote the first. Later, a node failed over and about 40 acknowledged status updates disappeared because they had not yet reached a replica. Finally, a "my orders" N1QL query right after checkout did not show the new order.

**What the interviewer is really checking**
Whether you know that a single-document write is atomic but not conflict-safe, durable, or instantly visible to queries, and which tool fixes each gap.

**How I answer it**
1. **Single-document writes are atomic.** So I model each aggregate as one document, because this gives atomicity without transactions.
2. **Use CAS for concurrent updates.** Read with CAS, change, replace with that CAS. On a CAS mismatch, re-read and retry a few times. This prevents lost updates without holding locks.
   ```java
   collection.replace(id, doc, replaceOptions().cas(cas).durability(DurabilityLevel.MAJORITY));
   ```
3. **Pick the durability level per write by its value.** Payments and orders get `majority` or stronger. Low-value data such as view counters can use the default. Higher levels wait for more acknowledgements, so they cost latency.
4. **Use transactions only when documents truly must change together.** They are slower because of extra reads, writes and coordination. Better modelling is usually cheaper.
5. **Decide query freshness explicitly.** Reads by key see the latest data. For N1QL I use `REQUEST_PLUS` only where read-your-own-write matters, e.g. right after checkout. Elsewhere I accept the default for speed.

**Trade-offs and what can go wrong**
- CAS under heavy contention on a hot document causes retry storms. Split the document or use sub-document operations or counters.
- Stronger durability raises latency. It can also fail with a timeout when replicas are unavailable. An ambiguous result means the write may or may not have applied, so retries must be idempotent.
- Transactions add latency and can conflict and retry.
- `REQUEST_PLUS` makes queries slower under heavy write load.
- A common mistake is assuming "acknowledged" means "safe on disk and replicated".

**How I'd monitor it**
- In Splunk, alert on the rate of `CasMismatchException`, `DurabilityAmbiguousException` and `DurabilityImpossibleException`.
- Track p99 write latency per durability level.
- In the Couchbase UI, watch the disk write queue, replication queue and failover events.
- Watch index pending-mutation lag and N1QL query latency.

**Follow-ups to expect**
- *CAS or locking?* -> CAS is optimistic and cheap when conflicts are rare. `getAndLock` is pessimistic and blocks others, so use it only for short, high-conflict sections.
- *Why not always use the strongest durability?* -> It adds latency, and writes can fail when replicas are down. Match it to the data's value.
- *Do key reads need REQUEST_PLUS?* -> No. Reads by key see the latest write. Only index-based queries can lag.

**60-second answer**
In Couchbase, a write to one document is atomic, so I model each aggregate as one document. To stop two services overwriting each other I use CAS: I read the document with its CAS, write it back with that CAS, and retry if it fails. By default an acknowledged write may exist only in memory on one node, so for important data I set a durability level such as `majority`, accepting extra latency. Multi-document ACID transactions exist from about 6.5, but they are slower, so I use them only when needed. N1QL queries can be slightly stale, so I use `REQUEST_PLUS` where a user must see their own write. I monitor CAS mismatches, durability errors, replication queues and index lag.

### Q8 [mid] How do you use Couchbase from Spring Boot?
tags: couchbase, spring-boot, spring-data-couchbase, java-sdk, cas, sql++, nosql, basics

**Start here: the concepts**
- **Couchbase**: a NoSQL database that stores JSON documents under a unique key. You can fetch by key (very fast) or query by content.
- **Bucket, scope, collection**: Couchbase's folders. A bucket holds scopes, and a scope holds collections. A collection is roughly a table, and it holds documents.
- **Key-value (KV) access**: get, upsert or remove a document by its key. It skips the query engine, so it is the fastest path.
- **N1QL (now called SQL++)**: Couchbase's SQL-like query language for JSON. It needs indexes, or queries are slow or fail.
- **Java SDK**: Couchbase's official client library. **Spring Data Couchbase** sits on top of it and adds repositories and annotations.
- **Repository, `@Document`, `@Field`**: `CouchbaseRepository` gives ready-made save/find methods. `@Document` marks a class as stored in Couchbase. `@Field` maps a Java field to a JSON field name.
- **`Cluster`**: the object that holds connections to the Couchbase servers. It is expensive to create and is thread-safe.
- **CAS (compare-and-swap)**: a version number Couchbase puts on every document. If you write with a stale CAS, the write is rejected. That is optimistic locking, which stops lost updates.
- **Reactive/async**: non-blocking calls, so a few threads can serve many requests.

**The live scenario**
An order service handles about 2,000 requests/second. After a release, p99 latency jumps from 15 ms to 4 s and connections spike. A developer built a new `Cluster` inside a request method, so every call opened fresh connections. A second incident: a payment-status update retried blindly after a timeout and overwrote a newer status written by another instance.

**What the interviewer is really checking**
Whether you know the two access styles (repositories vs. direct SDK), the single shared `Cluster`, and how to handle failures safely, especially retries and concurrent updates.

**How I answer it**
1. **Pick the access style per use case.** I use Spring Data Couchbase for normal CRUD, with `@Document`, `@Field` and a `CouchbaseRepository`. Repositories cut boilerplate. For hot paths that look up by key, or when I need reactive/async calls, I use the Java SDK directly, since KV is the fastest route.
2. **Configure once.** I set the connection string, credentials, bucket/scope/collection and explicit timeouts. Property names differ between Boot versions, so I check the docs for mine.
   ```
   spring.couchbase.connection-string=couchbase://host1,host2
   spring.couchbase.username=app
   spring.data.couchbase.bucket-name=orders
   ```
3. **One shared `Cluster` bean per app.** It manages connection pools and topology. Creating one per request wastes connections and causes the latency spike above.
4. **Use `@Query` (N1QL) only when needed, with indexes.** Queries go through the query service, which is slower than KV. I create the right secondary index and avoid a primary index in production.
5. **Handle the three key exceptions.**
   - `DocumentNotFoundException`: the key does not exist. Treat it as "not found", not as an error.
   - `CasMismatchException`: someone changed the document after I read it. I re-read, reapply the change and retry. In Spring Data, a `@Version` field maps to CAS.
   - `TimeoutException`: I do not know if the write happened. I retry only if the operation is idempotent (safe to repeat, such as an upsert of the same state) or protected by CAS. Otherwise I verify first.

**Trade-offs and what can go wrong**
- Repositories hide the SDK, so you may not notice slow queries or missing indexes.
- Blind retries on timeouts can duplicate or overwrite writes.
- Long timeouts hide problems and pile up threads. Short ones cause false failures.
- Mixing blocking calls into a reactive flow starves threads.
- Modelling must follow access patterns. Heavy N1QL joins on normalised data defeat the purpose of the store.

**How I'd monitor it**
- Application metrics: KV and query latency (p50/p99), timeout counts, retry counts, CAS-mismatch rate.
- Couchbase UI: ops/sec, cache miss ratio, query service latency, and index usage and slow queries (system:completed_requests).
- Splunk: alert on a rising count of `TimeoutException` or `CasMismatchException` per minute, and search by document key to trace a single order.

**Follow-ups to expect**
- *Why not create a Cluster per request?* -> It is heavy, opens many connections, and slows or crashes the app. One shared bean is thread-safe.
- *How do you prevent lost updates?* -> Use CAS (`@Version` in Spring Data) and retry on `CasMismatchException`.
- *KV or N1QL?* -> KV when you know the key, because it is faster. N1QL for searches, backed by indexes.

**60-second answer**
In Spring Boot I use Spring Data Couchbase for everyday CRUD: `@Document` classes, `@Field` mapping, a `CouchbaseRepository`, and N1QL `@Query` where I need a search. For key lookups on hot paths, or reactive and async code, I use the Java SDK directly. I configure the connection string, credentials, bucket, scope, collection and timeouts, and expose one shared `Cluster` bean, because creating one per request is costly. I treat `DocumentNotFoundException` as "not found", and `CasMismatchException` as a concurrent update, so I re-read and retry. For `TimeoutException` I retry only when the write is idempotent or protected by CAS, since the write may have succeeded. I watch latency, timeouts and CAS-mismatch rates, and I make sure queries have indexes.

### Q9 [mid] MongoDB essentials?
tags: mongodb, nosql, replica-set, sharding, indexing, write-concern, basics

**Start here: the concepts**
- **Document and BSON:** A document is one record shaped like JSON, with nested fields and arrays. BSON is the binary format MongoDB stores it in. It adds types such as dates and 64-bit integers. A collection is a group of documents, roughly like a table without a fixed schema.
- **`_id`:** The unique primary key of every document, indexed automatically. If you don't supply one, MongoDB generates an ObjectId.
- **Query and aggregation pipeline:** Queries filter documents. A pipeline passes documents through stages. `$match` filters, `$group` summarises (counts, sums), and `$lookup` joins in documents from another collection.
- **Index:** A sorted side structure that lets MongoDB find documents without scanning the whole collection. A *compound* index covers several fields in order. A *TTL* index makes a background job delete documents after a set time. A *text* index supports word search.
- **Replica set:** Several copies of the data. One primary takes writes and the secondaries copy it. If the primary dies, the members elect a new one automatically (failover).
- **Sharding and shard key:** Sharding splits one collection across several servers (shards) so no single machine holds everything. The shard key is the field that decides which shard owns a document.
- **Transaction:** Several changes that succeed or fail together. Multi-document transactions work on replica sets, and from MongoDB 4.2 on sharded clusters too.
- **Write concern:** How many members must confirm a write before you are told "OK". `w:majority` means most members have it.
- **Read concern and read preference:** Read concern is how safe the data you read must be, for example only majority-confirmed data. Read preference is which member you read from, such as the primary or a secondary.

**The live scenario**
An events service writes about 5,000 documents per second into a collection sharded on `createdAt`. Within a week one shard of three is at 95% CPU while the others idle, because every new document has the newest timestamp and lands on the same shard. During a primary failover, a few writes that were acknowledged with `w:1` also disappeared. Only the old primary had them, and they were rolled back. The fix was a hashed or compound shard key and `w:majority`.

**What the interviewer is really checking**
Whether you understand MongoDB as a system, not a list of features. That means indexes for query speed, replica sets for safety, shard keys for scale, and how write concern and read concern trade durability against latency.

**How I answer it**
1. **Start with the data model.** Documents in collections, `_id` as the key. Related data is often embedded in one document so a single read fetches it, because that is faster than joining.
2. **Querying.** Simple filters for most reads, and the aggregation pipeline for reporting. `$lookup` exists, but if you use it everywhere you are modelling relationally and paying for it.
3. **Indexes.** Create them for your real queries. In a compound index, field order matters (equality fields first, then sort and range fields). Use TTL for expiring data such as sessions, and a text index for basic search. Each index speeds up reads but slows writes and uses memory.
4. **Replica sets for availability.** Writes go to the primary, secondaries replicate, and failover is automatic. Without replication, one dead server means an outage.
5. **Sharding for scale.** Use it only when one replica set can't hold the data or the write load. Choose a key with many distinct values that spreads writes. A key that always increases (timestamps, ObjectId) with range sharding creates a hot shard, and hashing the key avoids it.
6. **Transactions.** They are available across documents, but they cost performance. Good document design often avoids needing them.
7. **Durability and freshness.** `w:majority` makes sure an acknowledged write survives failover, because a majority has it. Pair it with a suitable read concern, and use read preference to decide whether secondaries may serve reads.

```js
db.events.insertOne(doc, { writeConcern: { w: "majority" } })
```

**Trade-offs and what can go wrong**
- `w:majority` adds latency. `w:1` is faster but can lose acknowledged writes on failover.
- Reading from secondaries can return stale data because replication lags.
- Too many indexes slow writes. Missing ones cause full collection scans.
- A bad shard key is hard to fix later. Resharding exists in newer versions (5.0+) but is costly.
- Unbounded arrays inside a document can hit the 16 MB document limit.
- TTL deletion is not instant. The background job runs periodically.

**How I'd monitor it**
- Replication lag and replica set member health (`rs.status()`).
- Slow-query log and `explain()` to check that queries use indexes (look for `COLLSCAN`).
- Per-shard data size and operations, to spot hot shards.
- Cache usage, connections and failover events, through Atlas or Ops Manager dashboards, plus a Splunk search on slow-query log lines.

**Follow-ups to expect**
- *Why can a bad shard key cause hot shards?* -> If most writes target one key range, one shard does all the work while the others sit idle. Choose a high-cardinality key, or hash it.
- *What does `w:majority` protect against?* -> Losing acknowledged writes after a primary failover, because a majority of members already hold the write.
- *Embed or reference?* -> Embed data that is read together and bounded in size. Reference data that is large, shared or grows without limit.

**60-second answer**
MongoDB stores BSON documents in collections, each with a unique `_id`. I query with filters and the aggregation pipeline (`$match`, `$group`, `$lookup`) and speed that up with indexes: compound, TTL and text. For availability I run a replica set, with one primary, secondaries and automatic failover. For scale I shard by a shard key, and a bad key such as a raw timestamp creates a hot shard. For safety I use `w:majority` so acknowledged writes survive failover, and I choose read concern and read preference based on how fresh the data must be. Multi-document transactions exist, but I prefer designing documents so I rarely need them.

### Q10 [mid] Cassandra essentials?
tags: cassandra, nosql, partition-key, tunable-consistency, data-modeling, time-series, basics

**Start here: the concepts**
- **Wide-column store:** data lives in tables with rows, but each partition can hold many rows, and rows are stored together on disk. It is built for fast reads and writes by key, not for ad-hoc queries.
- **Masterless ring:** there is no leader node. Every node can accept any read or write, so losing one node doesn't stop the cluster. The nodes are arranged logically as a ring.
- **Consistent hashing:** Cassandra hashes the partition key to a number, and each node owns a range of numbers. This spreads data evenly and means adding a node moves only part of the data.
- **Partition key vs clustering key:** the partition key decides which nodes store the data. The clustering columns decide the sort order of rows inside that partition. Together they form the primary key.
- **Replication factor (RF):** the number of nodes holding a copy of each partition, commonly 3.
- **Tunable consistency:** per request, you choose how many replicas must answer. `ONE` needs one. `QUORUM` needs a majority (2 of 3). `LOCAL_QUORUM` needs a majority inside the local data centre only, avoiding slow cross-region calls.
- **Write path:** a write is appended to the **commitlog** (disk, for crash safety) and put in the **memtable** (memory). Memtables are later flushed to immutable **SSTables** on disk. Writes are sequential appends, so they are very fast.
- **Tombstone:** a delete marker. Cassandra doesn't erase data immediately, and reads must skip many tombstones.
- **`ALLOW FILTERING`:** a flag that lets a query scan data without using the key. It is slow at scale.

**The live scenario**
An IoT platform ingests about 50,000 sensor readings per second. The first table used `sensor_id` as the partition key, so all history for a sensor sat in one partition. After a few months, the busiest sensors had huge partitions, and read p99 rose from about 5 ms to about 800 ms. The team also deleted old rows one by one, which created many tombstones and slowed reads further. The fix was to bucket the partition key by day, `(sensor_id, day)`, order rows by timestamp, and expire data with TTL (a built-in time-to-live on each row).

**What the interviewer is really checking**
That you understand Cassandra is modelled around queries and partitions, not entities and joins. Also that you know why writes are fast and which patterns hurt it.

**How I answer it**
1. **List the queries first.** Cassandra has no joins, so I design **one table per query**, duplicating data if needed. Reads then hit exactly one partition.
2. **Choose the partition key for even spread and bounded size.** It decides which nodes hold the data. A key that is too coarse creates hot or unbounded partitions.
3. **Choose clustering columns for in-partition order.** Rows are stored sorted, so "latest 100 readings" is a cheap sequential read.
   ```sql
   PRIMARY KEY ((sensor_id, day), ts) WITH CLUSTERING ORDER BY (ts DESC)
   ```
4. **Pick consistency per use case.** With RF=3, `QUORUM` is 2 replicas. If reads plus writes exceed RF (2+2>3), a read sees the latest write. I use `LOCAL_QUORUM` in multi-region setups and `ONE` only where stale data is acceptable.
5. **Avoid `ALLOW FILTERING`.** It scans many partitions and can't scale. If I need a new query, I add a new table.
6. **Avoid heavy deletes.** I prefer TTL and time-bucketed partitions, because mass deletes leave tombstones that reads must skip.

**Trade-offs and what can go wrong**
- Denormalisation means duplicated data. The application must write to every table, and the tables can drift apart on partial failure.
- Lower consistency gives speed but risks stale reads. Higher consistency costs latency and availability.
- A poor partition key causes hot nodes or huge partitions.
- Ad-hoc queries and joins are not supported. Changing the access pattern later often means a new table and a data migration.
- Great for write-heavy and time-series data, a poor fit for flexible, rich querying.

**How I'd monitor it**
- Read and write latency percentiles (p99, not averages).
- `nodetool tablestats` for maximum partition size and tombstones per read.
- `nodetool tpstats` for pending or dropped mutations.
- `nodetool status` for node health.
- Pending compactions.
- Cassandra logs, searched in Splunk for tombstone warnings and slow-query messages.
- Alerts when partition size or p99 latency crosses agreed limits.

**Follow-ups to expect**
- *What does QUORUM mean with RF=3?* -> A majority, so 2 replicas must respond. Quorum reads plus quorum writes overlap on at least one replica, so reads see the latest write.
- *Why are Cassandra writes so fast?* -> They are sequential appends to the commitlog plus an in-memory memtable, with no read-before-write and no random disk updates. SSTables are written later in the background.
- *What is a tombstone and why does it hurt?* -> It is a delete marker kept until compaction and the grace period pass. Reads must scan past many tombstones, which makes them slow.

**60-second answer**
Cassandra is a masterless, wide-column database. Keys are hashed to spread data across a ring, so any node can serve any request and there is no single point of failure. Writes go to a commitlog and an in-memory memtable, then are flushed to SSTables, which is why they are so fast. I model one table per query. The partition key decides which nodes hold the data, and the clustering key sorts rows inside the partition. Consistency is tunable per request: `ONE`, `QUORUM`, or `LOCAL_QUORUM` for a majority in the local data centre. I avoid joins, `ALLOW FILTERING`, unbounded partitions and tombstone-heavy deletes. That makes it a great fit for time-series and write-heavy workloads.

### Q11 [mid] What is a quorum and how does `R + W > N` give consistency?
tags: quorum, consistency, replication, cassandra, tunable-consistency, mongodb, basics

**Start here: the concepts**
- **Replica:** one copy of a piece of data stored on one node. Databases keep several copies so that a dead machine does not lose data or take the service down.
- **N (replication factor):** how many replicas of each piece of data exist. In Cassandra this is the replication factor (RF). N=3 is common.
- **W (write consistency):** how many replicas must confirm a write before the database tells the client "success". The write is still sent to all N replicas. W only controls how many acknowledgements you wait for.
- **R (read consistency):** how many replicas must answer a read before the database returns a result. The newest version among those answers wins (in Cassandra, by write timestamp).
- **Quorum:** a majority of the replicas, `floor(N/2) + 1`. For N=3 that is 2, for N=5 it is 3. Any two majorities of the same group must share at least one member.
- **Stale read:** a read that returns an older value because the replica asked has not yet received the latest write.
- **Tunable consistency:** you choose R and W per query, trading speed and availability against freshness. Cassandra does this with levels like ONE, QUORUM and ALL.

**The live scenario**
An order service runs on Cassandra with N=3 and about 5,000 reads/s. Reads and writes use ONE for speed, with p99 around 5 ms. After payment, the "My Orders" page sometimes still shows "PENDING" for a moment. Support gets a few hundred tickets a day. The cause is that the write was acknowledged by replica A, but the read hit replica C, which had not yet received it. The team switches both to LOCAL_QUORUM. Stale reads stop, and p99 rises only slightly, to around 8 ms (illustrative numbers).

**What the interviewer is really checking**
Whether you understand the overlap argument, not just the formula. They also want to know whether you know that it gives a freshness guarantee, not magic, and that it costs latency and availability.

**How I answer it**
1. **Define quorum as a majority.** The reason is that any two majorities of the same replica set must overlap in at least one node.
2. **State the rule: `R + W > N`.** The reason is that the replicas you read from and the replicas that acknowledged the write cannot be completely separate groups. With N=3, W=2 and R=2, 2+2=4 > 3. At least one replica you read from has the latest acknowledged write, and the newest timestamp wins, so you get fresh data.
3. **Walk through the example.** The write lands on A and B, and C is still behind. A read of any 2 of {A, B, C} must include A or B, so it sees the new value.
4. **Contrast with ONE/ONE.** 1+1=2, which is not greater than 3. The write may sit on A only, and the read may hit C, so it can be stale. In exchange it is the fastest option and works with 2 nodes down.
5. **Pick per use case.** Use QUORUM/QUORUM (or LOCAL_QUORUM within one datacentre) for orders and balances. Use ONE for tolerant data such as view counts.

```
CONSISTENCY LOCAL_QUORUM;   -- cqlsh: applies to following reads and writes
```

**Trade-offs and what can go wrong**
- Higher R or W means you wait for slower replicas, so latency rises. Fewer nodes can be down: with N=3 and QUORUM, one node may fail, but two failing makes requests error out.
- The stored claim "strong consistency" needs care. R+W>N guarantees you overlap the latest *acknowledged* write. It is not full linearizability. Concurrent writes resolve by last-write-wins timestamps, so clock skew can matter, and a failed write may still land on some replicas. For true compare-and-set, Cassandra uses lightweight transactions (SERIAL).
- A common mistake is W=ONE with R=ONE while expecting fresh reads. Another is using plain QUORUM across datacentres and paying cross-region latency.

**How I'd monitor it**
- p99 read and write latency per consistency level.
- Cassandra `UnavailableException` and `ReadTimeoutException`/`WriteTimeoutException` counts. In Splunk, search for these by service and node.
- Hinted handoff backlog, dropped mutations (`nodetool tpstats`), and node status (`nodetool status`).
- Regular repair completion, because repair brings lagging replicas back in sync.
- Alert when fewer than the quorum count of replicas are up.

**Follow-ups to expect**
- *With N=3 and QUORUM, how many nodes can fail?* -> One. Two replicas are still available, which meets the quorum of 2.
- *Is QUORUM/QUORUM linearizable?* -> No. It gives read-after-acknowledged-write overlap, but concurrent writes and timestamps can still cause surprises. Use LWT (SERIAL) for compare-and-set.
- *How does this look in MongoDB?* -> Use write concern `w: "majority"` with read concern `"majority"` (or `"linearizable"` for the strongest reads). The idea is the same: acknowledgement from a majority.

**60-second answer**
A quorum is a majority of the replicas, which is `floor(N/2)+1`. With N=3 copies of the data, W is how many replicas must acknowledge a write and R is how many must answer a read. If R + W is greater than N, the replicas you read from must overlap with the ones that took the write, so at least one has the latest value and the newest timestamp wins. With QUORUM reads and writes, that is 2+2 > 3, so you see the latest acknowledged write. ONE/ONE is 1+1, which is not greater than 3, so it is faster and survives more failures but can return stale data. I would add that this is not full linearizability, and that you need lightweight transactions for compare-and-set. I'd watch latency, timeouts and unavailable errors to see the cost.

### Q12 [mid] Compare sharding strategies and rebalancing.
tags: sharding, partitioning, consistent-hashing, vbuckets, rebalancing, hot-partitions, basics

**Start here: the concepts**
- **Shard (partition):** one slice of a dataset stored on one node or replica set. We split data because one machine cannot hold all of it or serve all the traffic.
- **Shard key:** the field(s) used to decide which shard owns a record. Every read and write is routed by it.
- **Hash sharding:** run the key through a hash function and use the result to pick the shard. Data spreads evenly, but neighbouring keys land on different shards, so range scans (e.g. "all orders from 1-7 May") must ask every shard.
- **Range sharding:** each shard owns a contiguous key range (A-F, G-M...). Range scans are cheap, but if new keys always increase (timestamps, auto-increment IDs), every new write hits the last shard. That is a **hot spot**.
- **Directory (lookup) sharding:** a separate lookup table says "key X lives on shard 7". It is very flexible (you can move one tenant), but the lookup service is an extra dependency and a possible bottleneck.
- **Rebalancing:** moving data between nodes when nodes are added or removed, or when load is uneven.
- **Consistent hashing:** nodes and keys are placed on a hash ring, and each key belongs to the next node on the ring. Adding a node moves only the keys in its slice, not almost everything, as `hash(key) % N` would.
- **vBuckets (Couchbase):** a fixed number of virtual buckets (1024 on most platforms). A key hashes to a vBucket, and a cluster map says which node holds each vBucket. Rebalancing moves whole vBuckets. This is fixed-slot hashing with a map, in the same spirit as consistent hashing. Cassandra uses a token ring with vnodes, and MongoDB moves **chunks** (key ranges) with a balancer.
- **Cardinality:** the number of distinct values a key has. Low cardinality (e.g. country) means few possible shards.

**The live scenario**
An orders store on MongoDB holds 2 TB and takes 8,000 writes/s. The team range-sharded on `createdAt`. All inserts went to the newest chunk, so one shard sat at 90% CPU while three others idled at 10%. The balancer moved chunks constantly but could not keep up, because new data always arrived at the same place. Switching to a hashed key on `customerId` spread writes evenly. The "orders for one customer" query still hit a single shard.

**What the interviewer is really checking**
Whether you pick a strategy from the access pattern, not from memory of definitions. They also want to see that you know the key choice causes hot spots and that rebalancing has a real cost.

**How I answer it**
1. **List the main queries first.** The key must match the main access path. Queries that include the shard key go to one shard, and the rest scatter to all shards.
2. **Use hash sharding for even write spread and point lookups.** The hash breaks up sequential keys. The price is that range scans become scatter-gather.
3. **Use range sharding only when range scans matter and the key is not monotonic.** Otherwise the latest range becomes a hot spot. A compound key (e.g. `tenantId` + `date`) keeps ranges useful and spreads load.
4. **Use directory sharding when you need control.** Examples are moving one big tenant to its own node, or mixed shard sizes. Cache the lookup and make it highly available.
5. **Choose a key with high cardinality and even frequency.** High cardinality alone is not enough. If one customer owns 40% of traffic, that key still creates a hot shard.
6. **Plan rebalancing up front.** Prefer schemes where adding a node moves only a slice of the data (consistent hashing, vBuckets, chunks). Throttle the moves and run them off-peak. Avoid `hash % N`, because changing N reshuffles almost every key.

**Trade-offs and what can go wrong**
- Hash sharding gives even load but costly range queries. Range sharding gives cheap ranges but a risk of hot spots.
- A bad shard key is hard to change. MongoDB 5.0+ can reshard online, but it is heavy, and in other systems it means a migration.
- Rebalancing uses network, disk and CPU, and can raise latency while it runs.
- Low-cardinality or skewed keys give "jumbo" chunks that cannot split.
- A directory service that fails stops all routing.

**How I'd monitor it**
- Per-shard or per-node metrics: CPU, disk, write ops/s and data size. Alert when one node is 2x or more above the average.
- MongoDB: `sh.status()` for chunk distribution and balancer state. Cassandra: `nodetool status` and `nodetool tpstats`. Couchbase: vBucket distribution and rebalance progress in the UI.
- p99 latency per shard during rebalance.
- Splunk: search for slow queries and group by shard or host to find scatter-gather queries.

**Follow-ups to expect**
- *Why is `hash % N` bad?* -> Changing N changes the result for nearly every key, so almost all data moves. Consistent hashing or vBuckets move only a small share.
- *Can hash sharding support range queries?* -> Not efficiently. Fix it by modelling: put a coarse range value in a compound key, or keep a secondary query store.
- *How do you handle one huge tenant?* -> Use directory sharding to isolate it, or add a salt or sub-key so its data spreads across shards.

**60-second answer**
Sharding splits data across nodes by a shard key. Hash sharding spreads data evenly but makes range scans expensive. Range sharding makes range scans cheap but creates hot spots when keys increase, such as timestamps. Directory sharding uses a lookup table, so it is flexible but adds a dependency. For rebalancing I want consistent hashing, vBuckets or chunk-based moves, so adding a node moves only a slice of the data, not nearly everything as with `hash % N`. I start from the main query, then pick a high-cardinality key with even load that matches it. After that I watch per-shard load and rebalance throttling.

### Q13 [senior] How do you handle schema evolution in a schemaless store?
tags: nosql, schema-evolution, mongodb, couchbase, document-model, data-migration, basics

**Start here: the concepts**
- **Schema**: the agreed shape of your data: which fields exist, their types, which are required. A relational database enforces it for you.
- **"Schemaless" store**: a database such as MongoDB or Couchbase that accepts any JSON document without checking its shape. The schema does not vanish. It moves into your application code, which is why people prefer the term **schema-on-read**: the shape is interpreted when the data is read, not enforced when it is written. Optional validation exists (MongoDB supports JSON Schema validation). Cassandra is different: it has a real table schema changed with `ALTER TABLE`, though adding columns is cheap.
- **Schema evolution**: changing the data shape over time (rename a field, split one into two) while the system keeps running.
- **Schema version field**: a number such as `schemaVersion: 2` stored in every document, so code knows which shape it is looking at.
- **Tolerant reader**: code that handles every known version and ignores unknown extra fields, instead of crashing.
- **Lazy migration**: upgrade a document only when the app reads it, then save it back in the new shape.
- **Background migration**: a batch job that upgrades all remaining documents.

**The live scenario**
An orders collection holds 120 million documents, and about 2,000 reads/sec hit it. A release splits `name` into `firstName` and `lastName`. New code writes the new shape, but the old version of the service is still running on half the pods during the rolling deploy. Those old pods read new documents, find `name` missing and throw a NullPointerException. About 3% of requests fail with HTTP 500 until rollback. The data was fine. The code had no plan for two shapes coexisting.

**What the interviewer is really checking**
Whether you know that the schema still exists and the application owns it, and whether you can change it safely with old and new code and old and new documents live at the same time.

**How I answer it**
1. **Treat the document shape as a public contract, like an API.** Many versions of code and data coexist, so the shape needs the same discipline as a REST API: it is documented and changed carefully.
2. **Put `schemaVersion` in every document from day one.** Without it, you must guess the shape from which fields are present, which is fragile.
3. **Deploy readers first, writers second.** First ship code that reads both v1 and v2 and ignores unknown fields. Only after every instance runs it, start writing v2. This removes the outage in the scenario.
4. **Use lazy migration on read for the hot data.** When a v1 document is read, convert it in memory and save it back as v2. The write must be conditional so two concurrent readers cannot overwrite a newer update:
   ```
   updateOne({_id: id, schemaVersion: 1}, {$set: {firstName: f, lastName: l, schemaVersion: 2}, $unset: {name: ""}})
   ```
   Couchbase gives the same protection with CAS (compare-and-swap).
5. **Run a throttled background migration for the long tail.** Lazy migration never touches documents nobody reads, so old shapes stay forever. Process in small batches, with the same conditional update, off-peak.
6. **Test with real old documents.** Copy a sample of production data (anonymised) into tests. Hand-written fixtures only contain the shape you remember, not the shapes that actually exist.
7. **Remove old-version reader code only after the data proves it is unused.** A count of documents at the old version must be zero first.

**Trade-offs and what can go wrong**
- Reader code grows with every version. Without cleanup you carry v1 to v7 logic forever.
- Lazy migration turns reads into writes, which adds latency and load, and can collide with Kafka-driven updates to the same document. Use conditional or idempotent writes.
- Background jobs can starve production traffic if not throttled.
- A mixed-version collection makes queries and indexes awkward: a query on `lastName` misses v1 documents until they are migrated.
- No rollback story: once v2 is written, old code may break, so keep readers tolerant before you flip writers.

**How I'd monitor it**
- A periodic aggregation grouping documents by `schemaVersion` shows migration progress and when v1 reaches zero.
- Splunk searches for deserialization errors and "unknown schemaVersion" warnings, alerting on any rise after a deploy.
- Migration job metrics: documents per second, failures, conditional-update misses (CAS or version mismatches).
- Read p99 latency and error rate during rollout.

**Follow-ups to expect**
- *How do you rename a field with zero downtime?* -> Write both old and new fields, deploy readers that prefer the new one, migrate the data, then stop writing and remove the old field.
- *Why not just enforce a schema in the database?* -> You can, with MongoDB validation, but it only checks new writes. You still need versioning and migration for existing data.
- *How does this relate to Kafka events?* -> Same idea. Use a schema registry with compatibility rules, and make consumers tolerant of new fields.

**60-second answer**
"Schemaless really means schema-on-read: the database doesn't enforce the shape, so my application owns it and I treat it like an API. I store a `schemaVersion` in every document and make readers tolerant of all versions and of unknown fields. I deploy tolerant readers first and new writers second, so a rolling deploy never breaks. Hot documents get upgraded lazily on read with a conditional write, and a throttled background job handles the rest. I test against real old documents, and I only delete old-version code once a count by `schemaVersion` shows none left."

### Q14 [senior] How do you do transactions/relationships without joins?
tags: nosql, mongodb, couchbase, cassandra, transactions, saga, basics

**Start here: the concepts**
- **Join:** a query that combines rows from two tables. Many NoSQL stores skip it (Cassandra has none at all) because joining data spread over many servers is slow and hard to scale.
- **Transaction (ACID):** a group of changes that all succeed or all fail, with no half-finished state visible to others. Relational databases provide it by default.
- **Aggregate / embedding:** store data that is read and changed together inside one document, such as an order with its line items. A write to a single document is atomic in MongoDB and Couchbase, so no transaction is needed.
- **Reference:** store another record's ID instead of copying it, then fetch it with a second query. This is an *application-side join*.
- **`$lookup` / N1QL JOIN:** server-side joins in MongoDB and Couchbase (N1QL is now called SQL++). They work, but they cost more as data grows, so use them only on small or bounded sets.
- **Saga:** a long business process split into local steps, each with an undo ("compensating") step. If step 3 fails, you run the undo for steps 2 and 1.
- **Outbox:** write your data change and an "event to publish" record in the same atomic write. A separate process then publishes the event to Kafka, so a state change and its message are never out of sync.
- **Idempotent update:** running the same update twice gives the same result as running it once. This makes retries safe.
- **CAS (compare-and-swap):** Couchbase gives each document a version token. A write succeeds only if the token is unchanged since you read it, which prevents lost updates. MongoDB achieves the same with a version field in the update filter. Cassandra uses lightweight transactions (`IF ...`), which are slower.
- **Reconciliation:** a periodic job that finds and repairs data that drifted out of agreement.

**The live scenario**
An order service handles about 2,000 orders a minute at peak. The team split Order, OrderLines and Customer into separate collections, like a relational schema. Every order page needed three reads. Worse, when the payment write succeeded but the inventory write failed, about 40 orders a day ended up inconsistent, and support fixed them by hand.

**What the interviewer is really checking**
Whether you design data around access patterns so most invariants live inside one document. For the rest, do you know the real tools: sagas, outbox, idempotency, CAS and reconciliation? And do you know that modern versions *do* offer limited multi-document transactions, with costs?

**How I answer it**
1. **Model the aggregate first.** Embed order lines and a snapshot of the customer's name and address in the order document. Reason: one write is atomic and one read serves the page, so most "transactions" disappear.
2. **Use references only for data that is shared or changes independently,** such as the product catalogue. Reason: copying it everywhere would make updates painful.
3. **Make updates conditional.** Use CAS in Couchbase, a version field in MongoDB, or `IF` in Cassandra:
   `db.orders.updateOne({_id:1, version:3}, {$set:{status:"PAID"}, $inc:{version:1}})`
   Reason: two writers cannot silently overwrite each other.
4. **For cross-document or cross-service work, use a saga with an outbox.** Write the state change and the event atomically, then publish to Kafka. Reason: it avoids the "saved but never announced" gap.
5. **Make every consumer idempotent.** Use a unique event ID or conditional writes. Reason: Kafka delivers at-least-once, so duplicates will happen.
6. **Run reconciliation jobs.** Reason: some failures slip through, so you need a safety net.
7. **Use native multi-document transactions only for small, rare cases.** MongoDB supports them on replica sets from 4.0 and on sharded clusters from 4.2. Couchbase supports distributed ACID transactions from 6.5 through its SDKs. Cassandra offers only lightweight transactions and atomic single-partition batches. Reason: they add latency, locking and retry complexity.

**Trade-offs and what can go wrong**
- Embedding duplicates data. Updating a customer name means touching many documents, so duplicate only data that is stable or historical.
- Unbounded arrays make documents huge (MongoDB's limit is 16 MB per document).
- Sagas give *eventual* consistency, so users may briefly see in-between states. Compensations must themselves be retryable.
- Application-side joins create N+1 query storms.
- Overusing multi-document transactions rebuilds a slow relational system.

**How I'd monitor it**
- Count CAS or version-conflict failures and retries, and set an alert on a rising rate.
- Track outbox backlog age and Kafka consumer lag.
- Count compensation runs and dead-letter messages.
- Check reconciliation mismatch counts per day.
- Search Splunk by order ID or correlation ID across services to follow a stuck saga.
- Watch transaction abort and latency metrics if native transactions are used.

**Follow-ups to expect**
- *Does MongoDB really have no transactions?* -> It does: multi-document ACID since 4.0 (replica sets) and 4.2 (sharded). Single-document atomicity is still the preferred design.
- *Why an outbox instead of writing to the database and then Kafka?* -> Those are two systems, so one write can succeed while the other fails. The outbox makes the intent part of the atomic database write.
- *How do you handle duplicate Kafka messages in a sink?* -> Use a deterministic ID or a conditional write, so a repeat has no effect.

**60-second answer**
Without joins, I start by modelling around how the data is read and changed. I embed what changes together into one document, because a single-document write is atomic. I keep references only for shared data, and I use `$lookup` or N1QL joins sparingly on small sets. For consistency across documents or services, I use a saga with an outbox. Every step is idempotent and uses CAS or a version check, because Kafka can redeliver. I add a reconciliation job to repair drift. MongoDB and Couchbase do offer multi-document transactions now, but I save them for rare, small cases because of their cost. I monitor conflict rates, outbox lag and reconciliation mismatches.

### Q15 [senior] Caching with Redis - patterns and pitfalls?
tags: redis, caching, cache-aside, ttl, cache-stampede, distributed-lock, eviction, basics

**Start here: the concepts**
- **Cache:** a small, fast copy of data kept close to the application, so repeated reads skip the slow database. It exists because memory is far faster than disk-backed stores.
- **Redis:** an in-memory key-value store. Commands run on one main thread, so one slow command delays everyone.
- **TTL (time to live):** an expiry time on a key. Redis deletes the key after it passes, which bounds how stale a copy can get.
- **Cache-aside:** the app checks the cache first. On a miss it loads from the database, stores the result with a TTL and returns it. On a write it updates the database, then deletes the cached key.
- **Write-through:** every write goes to the cache and the database together, so reads stay fresh but writes are slower.
- **Write-behind:** the app writes to the cache and a background job saves to the database later. Writes are fast, but a cache crash can lose data not yet saved.
- **Stampede:** many requests miss the same key at once and all hit the database together.
- **Single-flight:** only one request reloads a key while the others wait for its result.
- **Jitter:** a small random offset added to TTLs so keys do not all expire together.
- **Big key / hot key:** a big key holds a huge value, and moving it blocks Redis. A hot key gets a disproportionate share of traffic and overloads one node.
- **Eviction policy:** the rule for what Redis removes when memory is full (for example, least recently used). Redis can also refuse writes instead.
- **Fencing token:** an increasing number issued with a lock. The protected resource rejects any holder whose number is older than one it has already seen.

**The live scenario**
A product-catalogue API serves 5,000 reads/s from a database that handles about 500/s. Redis absorbs most reads with a 10-minute TTL. A bulk import loaded 50,000 keys with the same TTL, so they all expired together. Thousands of requests hit the database at once, latency went from 20 ms to 6 s, and the database was nearly knocked over. Later, a "cache" holding carts had no database copy, an eviction removed carts, and customers lost them.

**What the interviewer is really checking**
Whether you know the main caching patterns and, more importantly, the failure modes: stampede, staleness, memory limits and misuse of Redis as a source of truth. A senior answer also knows where Redis locks are unsafe.

**How I answer it**
1. **Default to cache-aside.** The app controls what is cached, and a cache outage only slows reads rather than breaking them.
2. **On a write, update the database first, then delete the key.** Deleting is safer than rewriting the value, because two concurrent writers can leave an old value in the cache. A TTL is the backstop for anything missed.
3. **Use write-through when reads must be fresh.** Accept the slower writes. Use write-behind only for data you can afford to lose or replay, because unsaved writes die with the cache.
4. **Prevent stampedes.** Add jitter to TTLs, and use a short lock or single-flight so one caller reloads a missing hot key. Together these stop synchronized expiry and duplicate reloads.
5. **Plan memory.** Set `maxmemory` and choose an eviction policy on purpose. Split big values into smaller keys, and spread hot keys with replicas or a short-lived local cache.
6. **Never treat Redis as the only copy** of important data. Evictions, restarts and failovers can lose it.
7. **Use Redis for other jobs with care.**
   - Rate limits use atomic counters with expiry.
   - Pub/sub is fire-and-forget, so subscribers who are offline miss messages. Use Streams or Kafka if you need durability.
   - A lock takes the form `SET lock:order:42 <token> NX PX 30000`, which is a lease: it expires on its own. A lease alone is unsafe, because a paused client can wake up after expiry and still act. Pass a fencing token to the protected resource so stale holders are rejected. Redis failover can also hand the same lock to two clients, so do not use it where a double action would be a disaster.

**Trade-offs and what can go wrong**
- Stale data is the price of speed. Choose a TTL based on how stale the business can tolerate.
- Caching null results briefly prevents repeated misses for missing keys, but it can hide newly created data.
- Hot keys cannot be fixed by adding nodes, because one key lives on one shard.
- Eviction can silently drop data you assumed was permanent.
- A cold cache after a restart sends the full load to the database, so warm it up or rate-limit reloads.

**How I'd monitor it**
- Hit ratio, from `keyspace_hits` and `keyspace_misses` in `INFO`.
- `evicted_keys`, `used_memory` against `maxmemory`, and latency.
- `redis-cli --bigkeys` and `--hotkeys` to find problem keys. The hotkeys option needs an LFU eviction policy.
- Database queries per second and p99 latency. A spike right after a Redis expiry or restart points to a stampede.
- Splunk searches on cache-miss and loader-timeout logs, with an alert when the hit ratio drops.

**Follow-ups to expect**
- *Why delete the cache on write instead of updating it?* -> Concurrent writers can store an older value last. Deleting forces the next read to reload the truth.
- *Is a Redis lock safe?* -> Only for efficiency, such as avoiding duplicate work. For correctness, use a fencing token checked by the resource, or a database constraint.
- *Redis versus Couchbase as a cache?* -> Redis is simple and very fast in memory. Couchbase adds persistence and queryable documents, so it suits cases where the data must survive.

**60-second answer**
I default to cache-aside: read from Redis, on a miss load from the database and set a TTL, and on a write update the database and delete the key. I use write-through when reads must be fresh, and write-behind only when losing a few writes is acceptable. The main pitfalls are stampedes, which I handle with jittered TTLs and single-flight reloads, plus stale data, big keys, hot keys and surprising eviction. I set `maxmemory` and an eviction policy deliberately, and I never make Redis the only copy of important data. Redis also does rate limits, pub/sub and locks. A lock needs a lease plus a fencing token, and pub/sub loses messages for offline subscribers. I watch hit ratio, evictions, memory and database load to catch problems early.

### Q16 [senior] How do you migrate a feature from Oracle to Couchbase/MongoDB?
tags: nosql, couchbase, mongodb, oracle, migration, cdc, basics

**Start here: the concepts**
- **Bounded context**: a self-contained slice of the business (for example "user profile" or "shopping cart") with clear edges and few links to other data. It is migrated alone so a failure stays small.
- **Key-based access**: the code mostly says "give me the record with this ID" instead of joining many tables. Document stores such as Couchbase and MongoDB are very fast at this.
- **Aggregate / document**: everything that is read and written together, stored as one JSON document. Oracle spreads it over several tables, and the document store keeps it in one place, so one read replaces several joins.
- **Model around queries**: list the exact reads and writes first, then shape the documents to serve them. Copying the Oracle tables one-to-one loses the benefit.
- **Dual-write**: the application writes to both Oracle and the new store. There is no atomic transaction across two databases, so one write can succeed while the other fails, and the stores drift apart.
- **CDC (change data capture)**: a tool reads Oracle's change log and replays each change into the new store. It is usually safer than dual-write because Oracle stays the single source of truth.
- **Shadow read**: the app reads from both stores, serves the Oracle answer, and only compares the new store's answer in the background.
- **Rollback**: the ability to go back to Oracle quickly if the new store misbehaves.

**The live scenario**
A "customer preferences" feature loads from 6 Oracle tables. At peak, 4,000 reads/sec push p99 latency to about 250 ms, and it slows the shared database for other teams. The team migrates only this feature. It stores one document per customer, keyed by customer ID, and copies data over with CDC. For two weeks it shadow-reads and finds 0.02% mismatches, caused by a date-format bug. After the fix, p99 is about 15 ms (illustrative). The nightly finance reports stay in Oracle.

**What the interviewer is really checking**
Whether you treat migration as a staged, reversible, measured process and not a big-bang copy. Also whether you know which workloads do not belong in a document store.

**How I answer it**
1. **Pick one bounded context with key-based access.** Reason: a small, isolated slice limits the blast radius and proves the approach before you commit more.
2. **Model aggregates around the queries.** Reason: the speed gain comes from reading one document instead of joining. Embed data that is read together. Reference data that is large, shared or changes independently.
3. **Populate the new store with CDC, or dual-write if you must.** Reason: you need a full copy before trusting it. Prefer CDC because it avoids split-write failures. If you dual-write, make writes idempotent (upsert by key) and add a reconciliation job.
4. **Shadow-read and compare.** Reason: real traffic exposes mapping and format bugs that tests miss, and users are never affected because Oracle still answers.
5. **Switch reads first, then writes.** Reason: reads are easy to reverse. Use a feature flag and ramp 1%, 10%, 50%, 100%. Once writes move, the new store becomes the source of truth.
6. **Keep Oracle for rollback.** Reason: if you roll back after writes moved, Oracle needs the new writes too. So keep a reverse sync, or keep dual-writing, until you are confident.
7. **Measure latency and consistency.** Reason: you need proof, not a feeling. Compare p99 latency, mismatch rate and error rate against the Oracle baseline.
8. **Leave relational reporting in Oracle.** Reason: ad-hoc joins, aggregations and ACID-heavy reports are what Oracle does well. Forcing them into documents makes them slower and harder.

**Trade-offs and what can go wrong**
- Dual-write drift, and CDC lag making the new store briefly stale.
- Documents that grow without limit (embedding a never-ending list) hurt performance.
- Weaker cross-document guarantees. Both products offer multi-document transactions (MongoDB 4.0+ on replica sets, Couchbase 6.5+), but they are slower, so design so that one document is one atomic unit.
- Duplicated data must be kept in sync by your code.
- Running two databases costs more and needs more skills until Oracle is retired.

**How I'd monitor it**
- Shadow-read mismatch rate, with sampled diffs logged and searchable in Splunk by customer ID.
- p50/p99 latency and error rate on both stores.
- CDC lag, and counts or checksums compared between Oracle and the new store.
- Alerts on mismatch rate above a threshold, and a rollback-ready runbook.

**Follow-ups to expect**
- *Why CDC over dual-write?* -> Dual-write cannot be atomic across two databases, so failures cause drift. CDC replays committed Oracle changes in order.
- *How do you handle a rollback after writes moved?* -> Keep a reverse sync (new store to Oracle) during the safety window, and rehearse the rollback.
- *What would you never migrate?* -> Reporting, heavy joins and strongly relational transactional workloads.

**60-second answer**
I start with one bounded context that is mostly read by key, such as customer preferences. I design documents around the actual queries, so one read replaces several Oracle joins. I fill the new store with CDC, or idempotent dual-writes if CDC is not possible. Then I shadow-read: Oracle still answers while I compare results in the background and fix mismatches. I then move reads gradually behind a feature flag, then writes, and I keep Oracle with a reverse sync so I can roll back. I measure latency and mismatch rate throughout. Relational reporting stays in Oracle because document stores are the wrong tool for it.

### Q17 [architect] Design a user-profile/session store for 50M users with <10 ms reads, multi-region.
tags: couchbase, nosql, multi-region, xdcr, session-store, conflict-resolution, basics

**Start here: the concepts**
- **Key-value access:** you fetch a record by its exact ID (here `userId`) with no search or join. It is the fastest read a database offers, which is why it suits a <10 ms target.
- **Document:** one JSON record holding everything for a user (preferences, feature flags). One read returns the whole profile.
- **TTL (time to live):** a timer on a record. When it expires, the database deletes it. This suits sessions, which should disappear on their own.
- **Replica:** a copy of data on another node in the same cluster. It protects against a node dying and does not protect against a whole region going down.
- **XDCR (cross data centre replication):** Couchbase's asynchronous copying of changes from one cluster to another, usually in another region. Async means the remote copy lags by a short time.
- **Active-active:** both regions accept writes. Users get fast local reads and writes, but two regions can change the same record at once.
- **Conflict resolution:** the rule for choosing a winner when that happens. Couchbase XDCR offers revision-based (the doc with more updates wins, the default) or timestamp-based last-write-wins (LWW). LWW needs clocks synced with NTP.
- **Working set and resident ratio:** the working set is the data touched often. The resident ratio is the percentage of documents held in RAM. Reads served from RAM are fast, and reads that must go to disk are slower.
- **Ejection:** the server drops a document's value from RAM to make room. It stays on disk, but the next read is slower.

**The live scenario**
A streaming app has 50M users in EU and US. Login reads a profile on every request, so the p99 budget is 10 ms. Illustrative sizing: 50M docs at about 2 KB is about 100 GB per copy. The first design had one cluster in the US, and EU users paid about 90 ms per read, so the SLA failed. The team moved to a cluster per region. Then a user logged in from a laptop in the EU and a phone in the US in the same second, and two writes hit the same profile. One preference silently vanished. That is the conflict problem this design must plan for.

**What the interviewer is really checking**
Whether you can reach a latency target with a memory-first key-value design, and whether you understand that cross-region replication is asynchronous. That means you must have an explicit answer for conflicts and for the failure of a region.

**How I answer it**
1. **Model by access pattern:** the only hot query is "get the profile or session by userId". So the key is `userId`, with one JSON document per user. One key lookup is the cheapest read there is. Sessions go in a separate bucket or collection with a TTL, so they expire on their own and do not bloat profile data.
2. **One cluster per region, with local reads:** the app reads and writes its nearest cluster, so no read crosses an ocean. That is how you meet <10 ms.
3. **Replicate between regions with XDCR:** this gives each region a full copy and survives losing a region.
4. **Choose conflict resolution deliberately:** timestamp LWW is simple, but a slightly wrong clock can pick the wrong winner. For profile fields, LWW is usually acceptable. Couchbase does not merge counters across regions for you, so a CRDT-style merge (a data structure designed so concurrent updates combine correctly) is something you build, for example one counter per region summed on read. Better still, keep counters out of the profile document.
5. **Reduce conflicts at the source:** route a user to a "home" region (sticky routing), so one region normally writes a given user. Conflicts then become rare.
6. **Cache only truly hot profiles:** Couchbase already serves from its own memory, so an extra cache is optional and adds invalidation work.
7. **Publish changes to an event stream** such as Kafka, so downstream consumers (analytics, search) do not query the store. Make consumers idempotent.
8. **Capacity:** size the memory quota for the working set, ideally the whole 100 GB if affordable. Replicas protect against node loss within a cluster (Couchbase allows up to 3, and 1 or 2 is common), so the "3 replicas" in the original answer is a ceiling and not a requirement. Regions are covered by XDCR, not by replicas.

**Trade-offs and what can go wrong**
- Async XDCR means a user who switches region right after a write may see stale data for a moment. Pin sessions to a region to hide this.
- LWW can drop a legitimate update. Concurrent counter increments in two regions lose one.
- A low resident ratio means disk reads and missed latency targets.
- More replicas cost more RAM. Expiry (TTL) deletes also replicate, so confirm that is what you want.
- Full active-active costs more and is harder to reason about than active-passive.

**How I'd monitor it**
- Read and write latency percentiles (p95 and p99) per region.
- Resident ratio, ejections and cache miss rate.
- XDCR replication lag and backlog, and counts of conflicts resolved.
- Node health and rebalance status.
- Splunk alerts on read timeouts and on conflict-resolution spikes.

**Follow-ups to expect**
- *Why not MongoDB or Cassandra?* -> Cassandra fits write-heavy time series. MongoDB fits rich queries on flexible documents. This workload is key lookups with low latency, which suits Couchbase's memory-first design. Any of them could work with care.
- *How do you handle a region outage?* -> Route traffic to the other region, which already holds a near-complete copy. Accept that the last few seconds of writes may be missing until the region returns, then let XDCR catch up.
- *How do you avoid lost updates in one region?* -> Use CAS (compare-and-swap: the write succeeds only if the document has not changed since you read it) and retry on mismatch.

**60-second answer**
I'd key one JSON document per user by `userId`, because the hot path is a key lookup, which is the fastest read there is. Sessions get a TTL so they expire on their own. I'd run a Couchbase cluster in each region and serve reads locally, which is how we hit <10 ms. I'd link the clusters with XDCR for cross-region copies and region failover. Because XDCR is asynchronous, I'd pick conflict resolution on purpose: timestamp last-write-wins for most fields, sticky routing to a home region so conflicts are rare, and no shared counters in the profile. I'd size RAM for the working set and use replicas for node failures. I'd also publish changes to Kafka for downstream consumers. I'd monitor p99 latency, resident ratio, ejections and XDCR lag.

### Q18 [architect] Design a product catalog with flexible attributes and search.
tags: nosql, mongodb, couchbase, elasticsearch, cdc, data-modelling, basics

**Start here: the concepts**
- **Document database (MongoDB, Couchbase):** stores each record as a JSON-like document, so two products in the same collection can have different fields. It exists because real data is often uneven, and fixed table columns fit it badly.
- **Flexible attributes:** a laptop has RAM and screen size, while a shoe has size and colour. Common fields (name, brand, price) stay at the top level. Category-specific ones go in an `attributes` map inside the document.
- **Index:** a lookup structure the database keeps so it does not scan every document. Each index speeds up reads but slows writes and uses memory.
- **Search engine (OpenSearch/Elasticsearch):** it uses an *inverted index*, a map from each word to the documents that contain it. That makes full-text search, typo tolerance and relevance ranking fast.
- **Facets:** the filter counts on a shop page, such as "Brand: Dell (120), HP (80)". Search engines compute these cheaply.
- **Source of truth:** the one store whose data is correct if two stores disagree.
- **CDC (change data capture):** reading the database's change log, such as MongoDB change streams or Debezium, to publish every change as an event.
- **Eventual consistency:** the copy is briefly stale but catches up.

**The live scenario**
A retailer has 2 million products in 40 categories. Their relational schema used a key-value attribute table, and category pages with filters took about 1.2 s at p99 (the slowest 1% of requests). Every new category needed a schema change. Search for "red running shoes" ranked poorly. They moved to documents plus a search engine, and the category page dropped to tens of milliseconds. (Numbers are illustrative.)

**What the interviewer is really checking**
Do you model by query pattern, keep the database separate from search with a clear source of truth, and handle the sync, consistency and rebuild problems?

**How I answer it**
1. **List the queries first:** product by id, browse by category, filter by brand/price/attributes, and free-text search. Each one decides where it is served.
2. **One document per product:** common fields at the top level, category-specific fields in `attributes`. This avoids a join and lets a new category go live without a migration.
3. **Index only what you query in the database:** category, brand and price. For dynamic attributes, use the attribute pattern (`{"k":"ram_gb","v":16}` in an array) with one index, or a wildcard index in MongoDB 4.2+. Indexing every key bloats writes and memory.
4. **Put search in OpenSearch/Elasticsearch:** it does full-text, facets and ranking, which a general database does badly at scale. Couchbase has built-in full-text search, but a separate engine gives richer facets and ranking.
5. **Writes go only to the database:** it is the source of truth. Never write to both stores from application code, because if one write fails they silently diverge.
6. **Sync via CDC or events:** use CDC, or an outbox table (an events table written in the same transaction as the product), through Kafka to an indexer. Use the product id as the search document id and the version number as the guard. Replays and duplicates then do no harm.
7. **Define the search mapping explicitly:** price is numeric, brand is a keyword, and attributes use `flattened` or `nested`. Auto-mapping thousands of distinct attribute names causes *mapping explosion*, where the index metadata balloons.
8. **Keep search rebuildable:** build a new index from a database snapshot, replay changes from the saved offset, then switch an alias to it.

**Trade-offs and what can go wrong**
- Search is stale for seconds, so a deleted or sold-out item may show briefly. Read price and stock from the database at cart and checkout.
- Two systems mean more operations work and more cost.
- Dual writes and unbounded dynamic fields are the classic mistakes.
- Cassandra is a poor fit. It queries efficiently only by partition key, not by arbitrary filter combinations.

**How I'd monitor it**
- Indexing lag: database change time versus the time the document is searchable.
- CDC connector and Kafka consumer lag, and dead-letter queue size.
- Periodic count and checksum reconciliation between database and index.
- Search p99 latency, zero-result rate and index field count.
- Splunk searches on indexer errors, such as bulk rejections and mapping conflicts, with alerts on rising lag.

**Follow-ups to expect**
- *How do you rebuild the index without downtime?* -> Build a new index from a snapshot, replay changes from the saved offset, then atomically swap the alias.
- *Why not just use MongoDB for search?* -> It handles filters well, but ranking, typo tolerance and facets at scale are what search engines are built for.
- *How do you stop stale prices being sold?* -> Search is for discovery only. Cart and checkout read price and stock from the database.

**60-second answer**
I start from the queries: browse, filter, free-text search and fetch by id. Each product is one document, with common fields at the top level and a per-category `attributes` map. The database indexes category, brand and price. The database is the source of truth and all writes go there. I replicate to OpenSearch through CDC or an outbox and Kafka, using the product id and version so replays are safe. The search engine serves full-text, facets and ranking, and it can be rebuilt at any time. The cost is a few seconds of staleness, so checkout reads price and stock from the database. I watch indexing lag, DLQ size and reconciliation counts.

### Q19 [mid] What is NoSQL, and when should you use it?
tags: nosql, data-modelling, access-patterns, partition-key, consistency, cassandra, basics

**Start here: the concepts**
- **Relational database:** stores data in tables with fixed columns. It links tables with *joins* and enforces rules (constraints) such as "an order must point to a real customer". It exists to keep data correct and flexible to query.
- **NoSQL:** an umbrella name for databases that do not use the relational table model. It is often read as "not only SQL". It exists mainly because some workloads need very high scale, flexible shapes of data, or always-on availability.
- **Document store (MongoDB, Couchbase):** stores a whole JSON-like record, including nested parts, as one unit. One read returns everything about, say, an order.
- **Key-value store:** you look up a value by its key, like a giant hash map. Couchbase is often used this way for fast lookups.
- **Wide-column store (Cassandra):** rows are grouped by a *partition key*, and inside a partition they are sorted by *clustering columns*. It is built for huge write volumes.
- **Graph database:** stores things and the relationships between them. It suits questions like "friends of friends".
- **Access pattern:** the exact queries your application runs. In NoSQL you design the data around these queries first.
- **Horizontal scaling and partitioning:** you add more machines and split data across them by a partition (shard) key. A bad key can overload one machine, called a *hot partition*.
- **Consistency:** whether every reader sees the latest write. Cassandra lets you tune it per query. With replication factor 3, QUORUM means 2 of 3 replicas must answer.
- **Transaction:** a group of changes that all succeed or all fail together.

**The live scenario**
A fleet platform receives readings from 200,000 devices, about 50,000 writes per second at peak. The single relational primary hit 90% CPU, and nightly index maintenance slowed inserts. The only query that mattered was "last 24 hours of readings for one device". The team moved readings to Cassandra with partition key (device_id, day) and clustering by timestamp. Writes spread across nodes, and each query read one partition. Billing and invoices stayed in the relational database, because they needed joins and multi-row transactions.

**What the interviewer is really checking**
Whether you know NoSQL is several different models, not one product, and whether you choose by access pattern, scale and consistency needs rather than fashion.

**How I answer it**
1. **Define it as a family, not one thing.** Document, key-value, wide-column and graph stores solve different problems, so they are not interchangeable.
2. **Start from the access patterns.** Write down the queries, their read/write ratio and the latency target. NoSQL schemas are shaped by queries, and you often copy (denormalise) data on purpose to answer each query from one place.
3. **Check the scale and availability needs.** If one relational server can handle the load, stay relational. If you need to spread writes across many nodes or survive node loss, partitioned stores fit better.
4. **Pick the model that matches.** Write-heavy time series fits Cassandra. Flexible documents with rich queries fit MongoDB. Low-latency key-value plus documents fits Couchbase.
5. **Choose the consistency level deliberately.** For example, QUORUM writes plus QUORUM reads on replication factor 3 give overlapping replicas (2+2>3), so reads see the latest acknowledged write.
6. **Keep relational where it fits.** Where constraints, joins and multi-row transactions dominate, such as money or inventory, a relational database is usually safer.

```
-- Cassandra: PRIMARY KEY ((device_id, day), ts)
-- partition key = (device_id, day), clustering column = ts
```

**Trade-offs and what can go wrong**
- Queries you did not design for are slow or impossible, and changing the model later can be expensive.
- Denormalised copies can drift apart, so your code must keep them in sync.
- A bad partition key (for example, a date alone) creates a hot partition.
- Many NoSQL stores have weaker or narrower transactions. MongoDB supports multi-document transactions (since 4.0) and Couchbase has them too, but they cost more than in a relational database. Cassandra offers only single-partition conditional writes (lightweight transactions).
- "Schema-less" does not mean "no schema". The schema just moves into your application code.
- Weaker consistency settings can return stale data.

**How I'd monitor it**
- Track read and write latency at p95/p99 per table or collection, and timeout or "unavailable" error counts.
- Check partition or document size and request skew across nodes to spot hot partitions.
- Watch node CPU, disk, compaction backlog and replication lag. In Cassandra, use `nodetool tablestats` and `tpstats`; in MongoDB, the slow query profiler.
- In Splunk, alert on spikes of timeout or consistency-level errors, grouped by service and host.

**Follow-ups to expect**
- *Does NoSQL mean no transactions or no consistency?* -> No. Guarantees vary by product, and some stores let you tune consistency per operation. You must read what each store promises.
- *Is NoSQL faster than SQL?* -> Only for workloads it was designed for. A well-indexed relational database can beat a badly modelled NoSQL one.
- *How do you make Kafka consumers safe when writing to NoSQL?* -> Use idempotent writes (same key, same result) or conditional writes, so a re-delivered message does not create duplicates.

**60-second answer**
NoSQL is a family of databases beyond relational tables: document, key-value, wide-column and graph. They are not interchangeable. I use one when its model, access patterns, scaling or availability fit my needs, for example huge write volumes spread across many nodes. I start from the queries I must serve and design the data and partition key around them. I choose the consistency level on purpose, such as QUORUM in Cassandra. If joins, constraints and multi-row transactions dominate, as with payments, I stay relational. Many real systems use both.

### Q20 [mid] How do you handle duplicate requests in a NoSQL-backed service?
tags: nosql, idempotency, duplicate-requests, couchbase, mongodb, cassandra, basics

**Start here: the concepts**
- **Duplicate request:** the same request arrives more than once. Clients retry after a timeout, load balancers retry, users double-click, and Kafka delivers messages at least once. The service must not apply the effect twice.
- **Idempotent:** doing the operation once or five times leaves the same final result. This is the goal.
- **Idempotency key:** a unique ID for one logical request, such as a client-generated UUID or a business ID like an order number. It is the same on every retry, so the service can recognise a repeat.
- **Unique constraint:** a database rule that rejects a second record with the same key. Because the database enforces it, two concurrent requests cannot both succeed.
- **Race condition:** two requests run at the same moment and interleave badly. A check-then-insert is the classic case. Both check, both see "not found", and both insert.
- **Conditional write / compare-and-set (CAS):** "change this only if it still looks as I last saw it." In Couchbase, CAS is a version token on each document. In MongoDB, you put the condition in the update filter. In Cassandra, you use `IF`.
- **Atomic operation:** one indivisible step. No other request can slip in the middle.

**The live scenario**
A payment service takes 2,000 requests/s. A slow database call pushes some responses past the client's 3-second timeout, and the client retries. About 2% of requests are retried, and the original is often still running. The code did "find by orderId, and if none, insert". In one afternoon, 40 customers were charged twice because both attempts passed the find at the same time. Fixing it meant moving the uniqueness check into the database.

**What the interviewer is really checking**
Whether you know that application-level check-then-insert is unsafe under concurrency. They also want to see that you know how each NoSQL store gives you an atomic "only once" primitive, and that you return the original result on a repeat.

**How I answer it**
1. **Choose a stable key.** Use a client-supplied idempotency key or a business identifier. A key generated fresh on each attempt cannot identify a repeat.
2. **Make the database enforce uniqueness, per store:**
   - MongoDB: a unique index. The duplicate fails with a duplicate-key error. On a sharded collection, a unique index must include the shard key.
   - Couchbase: use the key as the document ID and do an insert. It fails if the document exists.
   - Cassandra: a plain write is an upsert, so duplicates silently overwrite. For "only once", use a lightweight transaction:
   ```sql
   INSERT INTO requests (id, status) VALUES (?, 'DONE') IF NOT EXISTS;
   ```
3. **Make updates conditional or atomic.** Use CAS in Couchbase, a version or state filter in a MongoDB update, and `IF` in Cassandra. A stale or repeated update is then rejected instead of applied twice.
4. **Record state and the outcome.** Store the key, a status (IN_PROGRESS or COMPLETED) and the response. On a repeat, return the stored result instead of re-running the work. This is what "record enough state" means.
5. **Never rely on check-then-insert.** It is correct only when one request runs at a time.
6. **Expire old records.** Use a TTL (time-to-live, automatic deletion) longer than the longest realistic retry window.

**Trade-offs and what can go wrong**
- Cassandra lightweight transactions use extra coordination between replicas, so they are slower. Use them only for the dedupe record, not on every write.
- A crash after IN_PROGRESS is recorded can block retries forever. Add a timeout or lease so a stale record can be retaken.
- Unique indexes cost write time and storage. If the TTL is too short, late retries slip through.
- Idempotency on the record does not cover side effects such as emails or payment calls. Pass the key to those systems too.

**How I'd monitor it**
- Rate of duplicate-key errors or `[applied]=false` results. Some are expected, but a spike points to a retry storm.
- A Splunk search that groups by idempotency key and flags keys with more than one "executed" log line. This should always return zero.
- Latency of lightweight transactions and CAS-failure rate.
- Business reconciliation, such as double charges per day.

**Follow-ups to expect**
- *Why not read first, then insert?* -> Two requests can both read "absent" before either writes. Only an atomic database operation closes that gap.
- *How do you dedupe a Kafka consumer writing to NoSQL?* -> Use a deterministic ID such as topic-partition-offset or a business key. Then make the write an idempotent upsert or conditional insert.
- *What if the same key arrives with a different payload?* -> Store a hash of the payload with the key. If the hash differs, reject the request as a conflict.

**60-second answer**
Duplicates are normal because of retries, timeouts and at-least-once delivery. So I give each logical request a stable idempotency key, such as a client UUID or an order ID. I let the database enforce uniqueness, because a check-then-insert in code can race under concurrency. In MongoDB I use a unique index. In Couchbase I use the key as the document ID and insert. In Cassandra I use `IF NOT EXISTS`, since normal writes are upserts. For updates I use conditional writes such as CAS. I store the status and the result, so a repeat returns the original outcome. I also set a TTL and handle crashed in-progress records, and I monitor duplicate-key rates and double executions in Splunk.

### Q21 [mid] How do you choose between a relational database and NoSQL?
tags: relational, nosql, data-modeling, consistency, access-patterns, cassandra, basics

**Start here: the concepts**
- **Relational database (RDBMS):** Data lives in tables with fixed columns, and tables are linked by keys. You query it with SQL. It exists so data is stored once, kept correct, and combined flexibly later.
- **NoSQL:** A loose label for stores that are not classic relational tables. Examples are document stores (MongoDB, Couchbase), wide-column stores (Cassandra) and key-value stores. They exist to make certain access patterns, huge scale or flexible data shapes easier.
- **Transaction (ACID):** A group of changes that all succeed or all fail, such as debiting one account and crediting another. Relational databases do this by default. Some NoSQL stores support it only in limited form.
- **Consistency:** After a write, whether every reader sees the new value immediately (strong) or may briefly see the old one (eventual).
- **Join:** Combining rows from two tables at query time. Most NoSQL stores avoid joins, so you copy data into the shape each query needs (denormalising).
- **Access pattern:** The exact questions your application asks, such as "all orders for customer X, newest first".
- **Partition (shard) key:** The field that decides which node holds a record. A poor key makes one node a "hot partition" that is overloaded while the others sit idle.
- **Schema evolution:** Changing the data shape over time, such as adding fields.

**The live scenario**
A team building an order service chose Cassandra because "microservices need NoSQL and it is faster". The service had about 2,000 orders a day. Finance then asked for reports joining orders, payments and customers, and checkout needed payment and stock updated together. The team ended up writing joins in application code and a nightly reconciliation job for mismatches. Meanwhile, another team in the same company ingested 150,000 device readings per second, queried only by device and time range. A single relational primary struggled with that write rate, and a wide-column store fitted it well. The same choice was right for one workload and wrong for the other.

**What the interviewer is really checking**
Whether you decide from workload needs (consistency, queries, scale, operations) instead of fashion, and whether you know NoSQL is a trade-off, not an upgrade.

**How I answer it**
1. **Start with transactions and consistency.** If money or stock must change together and be correct immediately, lean relational. Strong guarantees are built in, and doing this yourself on top of eventual consistency is costly and error-prone.
2. **List the query patterns and joins.** If queries are varied, ad hoc or join-heavy, relational wins. If you have a few known, repeated queries, NoSQL works, because you design the data around them.
3. **Look at data shape and how it evolves.** Highly varied or fast-changing records suit documents. Stable, well-structured data suits tables.
4. **Estimate scale and traffic distribution.** One well-tuned relational node with replicas handles far more than people assume. Choose NoSQL when write volume or data size outgrows that, and when a good partition key spreads load evenly.
5. **State latency and availability goals.** Ask how fast reads must be and whether the system must keep accepting writes during node or network failure. Many NoSQL stores trade strict consistency for availability.
6. **Count operational skills, backup/recovery and cost.** A store your team cannot run, back up, restore or tune is a risk, whatever its benchmarks say.
7. **Check reporting and analytics.** SQL makes reporting easy. With NoSQL you often need an extra pipeline to a warehouse.
8. **Avoid the two traps.** Do not pick NoSQL just because the system is "microservices", or because it is assumed to be automatically faster. Speed comes from fitting the access pattern.

**Trade-offs and what can go wrong**
- Picking NoSQL early can force you to rebuild joins and consistency in application code.
- Denormalised copies can drift apart and need update logic.
- Bad partition keys cause hot partitions.
- Relational databases can hit write limits on one primary, and sharding them is hard.
- Many stores now offer partial transaction support, but check its limits (scope, performance) for your product and version before relying on it.
- A mixed approach (relational for core data, NoSQL for one specific workload) adds operational burden.

**How I'd monitor it**
- p95/p99 read and write latency against targets.
- Replication lag and node-level load, to spot hot partitions.
- Slow-query logs and growing application-side join code.
- Timeout, conflict and retry errors, searchable in Splunk by service and datastore.
- Disk growth and cost per month.
- A scheduled restore test, to prove backups actually work.

**Follow-ups to expect**
- *Can NoSQL do transactions?* -> Partly. MongoDB has multi-document transactions (since 4.0 on replica sets) and Cassandra has conditional writes within a partition. Scope and cost differ from a relational database, so verify the limits.
- *How do you scale a relational database?* -> First tune queries and indexes, then add read replicas and caching, then partition or shard, which is harder.
- *Can you use both?* -> Yes, this is polyglot persistence. Use each store for the workload it fits, and accept the extra operational cost.

**60-second answer**
I choose from the workload, not from fashion. First I ask how strict consistency and transactions must be, because money and stock usually point to relational. Then I look at query patterns and joins, data shape, expected scale and how evenly traffic spreads. I also check latency and availability goals, plus reporting needs. Finally I weigh team skills, backup and recovery, and cost. I choose NoSQL when I have known access patterns, very high scale or flexible data, not simply because the system uses microservices or because NoSQL sounds faster.
