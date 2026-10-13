---
id: 15-system-design
title: Distributed Systems & System Design
focus: Core theory plus worked design questions (rated 6/10 - invest here)
deep_dive: 16,19
examples: 16_system_design
---
Design answer template: **1) clarify requirements and scale -> 2) APIs and data model -> 3) high-level components -> 4) deep dive on the bottleneck -> 5) failure modes and trade-offs -> 6) metrics/operations.** Say assumptions out loud.

### Q1 [basic] What are the fallacies of distributed computing in practice?
The network is not reliable, latency is not zero, bandwidth is finite, the network is not secure, topology changes, there are many administrators, transport has a cost, the network is not homogeneous. Practical result: timeouts, retries, idempotency, backpressure and observability on every remote call.

### Q2 [basic] Explain CAP and PACELC in one minute.
During a partition choose consistency (CP: reject/limit requests) or availability (AP: serve possibly stale data). PACELC: Else (no partition) choose latency vs consistency. Payments tend to CP; feeds/profiles tend to AP.

### Q3 [intermediate] What consistency models should you know?
Strong (linearizable), sequential, causal, read-your-writes, monotonic reads, eventual. Pick the weakest that is correct for the feature - e.g. read-your-writes for profile edits, strong for account balance.

### Q4 [intermediate] How do you scale a stateless service and a database?
Service: horizontal replicas behind a load balancer, autoscaling, no local state, shared cache. Database: vertical scale -> read replicas (reads) -> caching -> partitioning/sharding (writes) -> CQRS/separate stores. Remove bottlenecks in this order, measuring each step.

### Q5 [intermediate] Caching strategies and invalidation?
Cache-aside, read-through, write-through, write-behind; TTL + explicit invalidation on write; versioned keys; protection against stampede (single-flight/lock, jittered TTL, serve-stale-while-revalidate); two levels (local Caffeine + Redis). "There are two hard things: cache invalidation..." - say what staleness is acceptable.

### Q6 [intermediate] Load balancing algorithms and levels?
L4 (TCP) vs L7 (HTTP, path/header routing). Algorithms: round robin, least connections, weighted, consistent hashing (sticky by key, cache-friendly). Health checks remove bad nodes; connection draining for deploys.

### Q7 [intermediate] How do you achieve idempotency across a distributed flow?
Every command carries a unique id; each service stores processed ids (unique constraint) and returns the original result for duplicates; side effects to third parties use their idempotency keys; retries are then safe. It is the foundation of "at-least-once + idempotent = effectively once".

### Q8 [intermediate] What are consistent hashing and why is it used?
Keys and nodes are mapped on a ring; a key belongs to the next node clockwise. Adding/removing a node moves only ~1/N keys instead of reshuffling everything. Used in caches, Cassandra, Couchbase vBuckets, load balancers; virtual nodes even out the load.

### Q9 [intermediate] Explain leader election, consensus and distributed locks.
Consensus (Raft/Paxos; used by etcd, ZooKeeper-style systems, Kafka KRaft) lets nodes agree on one value/leader despite failures. For app-level locks use a lease (Redis `SET NX PX`, DB row, etcd/ZooKeeper) with a **fencing token** so a paused old holder can't corrupt data. Prefer designs that avoid locks (partitioning, idempotency).

### Q10 [advanced] What happens with clock skew and ordering of events?
Wall clocks differ between machines; never use timestamps alone to order concurrent updates. Use per-entity version numbers, sequence/offset (Kafka partition offset), logical/vector clocks, or a single writer per key. Last-write-wins by timestamp can silently drop updates.

### Q11 [advanced] Backpressure, load shedding and bulkheads?
Backpressure: slow producers when consumers can't keep up (bounded queues, Kafka lag-based scaling, reactive streams). Load shedding: reject low-priority work early (429/503) to protect the core. Bulkheads: separate pools/queues per dependency or tenant so one slow dependency cannot exhaust shared resources.

### Q12 [advanced] Retry storms and thundering herd - prevention?
Exponential backoff **with jitter**, retry budgets (cap retries to a % of traffic), circuit breakers, request deadlines propagated downstream, and don't retry at every layer (multiplies load). Cache locking and staggered TTLs prevent herd on cache expiry.

### Q13 [advanced] How do you handle hot partitions / hot keys?
Detect via per-partition metrics; add a salt to the key or split by sub-key when ordering allows, local caching for hot reads, rate limit heavy tenants, choose a higher-cardinality partition key, dedicated partitions/queues for top tenants.

### Q14 [advanced] Eventual consistency in the UI - how do you handle it?
Return `202` + status endpoint, optimistic UI updates, show "processing" states, read-your-writes via reading from the primary for a short window or passing a version token, and make the UI tolerant of reordering/duplicates.

### Q15 [design] Design a URL shortener.
Requirements: 100M new URLs/month, 10:1 read:write, <50 ms redirects, no collisions. API: `POST /urls`, `GET /{code}` -> 301/302. Code generation: base62 of a distributed counter/ID range per node (no collisions) or hash + collision check. Storage: key-value (code -> url, owner, expiry). Reads: cache hot codes (Redis/CDN), replicas. Analytics: async click events to Kafka. Trade-offs: 301 (cacheable, less analytics) vs 302; custom aliases; expiry cleanup; abuse/rate limiting.

### Q16 [design] Design a notification service (email/SMS/push).
Producers publish `NotificationRequested` events (Kafka) -> router resolves user preferences/templates -> per-channel queues with workers calling providers (SES/Twilio/FCM) behind circuit breakers and per-provider rate limits -> status updates stored -> retry with backoff then DLQ -> dedupe by notification id -> user opt-out/quiet hours -> metrics: delivery rate, latency, failures per provider.

### Q17 [design] Design a rate-limited API gateway for partners.
Auth (API keys/OAuth2 client credentials) -> per-partner token bucket in Redis (Lua for atomicity) -> quotas per plan (daily/monthly) -> `429` with `Retry-After` -> async usage metering to Kafka for billing -> dashboards and alerts. Decide behaviour when Redis is down (fail-open for low risk, fail-closed for abuse-sensitive).

### Q18 [design] Design a file processing platform (bulk files from many sources to a database/Kafka).
Ingestion adapters (SFTP, email attachments, web download, upload) -> object storage (S3) with metadata record -> event triggers a parser by file type/source (plugin per format) -> normalise to a canonical schema -> validate -> publish to Kafka/DB with idempotent keys -> orchestration with Airflow (retry, schedule, SLAs) -> notifications (SES) -> audit trail and replay. Handle huge files with streaming/multipart, checksum dedupe, quarantine for bad files, and per-source metrics.

### Q19 [design] Design a payment/wallet transfer system (strong correctness).
Double-entry ledger table (immutable entries), transfers executed in a single DB transaction per account shard or via saga across services; idempotency keys; optimistic locking/serializable for balance checks; outbox for events; reconciliation jobs; audit; strict CP choice. Discuss exactly-once illusions and how retries are made safe.

### Q20 [design] Design a real-time chat / notification push system (WebSocket/SSE).
Gateway layer holding WebSocket connections (sticky by connection id), a presence registry in Redis, messages through Kafka/Redis pub-sub keyed by conversation, persistence in a scalable store (Cassandra/Couchbase) ordered by conversation + time, offline delivery via push notifications, and reconnect with last-seen id to avoid gaps.

### Q21 [design] Design a distributed job scheduler (run a cron job once across 10 pods).
Options: leader election (Kubernetes lease), DB-based lock with `SELECT ... FOR UPDATE SKIP LOCKED`, ShedLock, Quartz in cluster mode, or a K8s CronJob (one pod per run). Make jobs idempotent, record runs and status, add timeouts/heartbeat to recover from a crashed worker, and alert on missed runs.

### Q22 [design] How do you design for zero-downtime deployments including database changes?
Backward-compatible API and schema (expand/contract), rolling/canary deploys with readiness gates, feature flags, graceful shutdown, versioned events, and automated rollback on SLO regression. Never deploy a code change that needs a schema change in the same step.

### Q23 [intermediate] What is the difference between horizontal and vertical scaling and the limit of each?
Vertical: bigger machine, simplest, hard cap and single point of failure. Horizontal: more machines, near-linear for stateless tiers, requires partitioning/replication for state and brings consistency problems.

### Q24 [intermediate] Back-of-envelope estimation - show the method.
Example: 10M DAU x 20 requests/day = 200M/day ~ 2,300 RPS average, ~10k RPS peak (x4). 1 KB per record x 100M new records/year = 100 GB/year. State assumptions, compute QPS, storage, bandwidth, then derive node counts with headroom. The method matters more than the exact numbers.
