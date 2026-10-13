---
id: 09-kafka
title: Apache Kafka (and RabbitMQ) for Java Developers
focus: Delivery guarantees, ordering, consumer groups, failure handling, Spring Kafka, Kafka 4
deep_dive: 12
examples: 12_kafka
---
Kafka 4.0 (Mar 2025) removed ZooKeeper: clusters run **KRaft** only. Queues for Kafka (share groups, KIP-932) arrived in early access, then preview in 4.1. Spring for Apache Kafka 4.0 supports the new consumer rebalance protocol (KIP-848).

### Q1 [basic] What is Kafka and what problems does it solve?
A distributed, durable, partitioned commit log. Producers append events to topics, consumers read at their own pace and can replay. Used for decoupling services, event streaming, log/CDC pipelines, and buffering spikes. Difference from a classic queue: messages are **not deleted on read**; they're retained by time/size.

### Q2 [basic] Explain topic, partition, offset, broker, replica.
Topic = named stream. Partition = ordered, append-only slice of a topic (unit of parallelism). Offset = position of a record in a partition. Broker = Kafka server. Each partition has a leader and follower replicas (replication factor, usually 3).

### Q3 [basic] What is a consumer group?
Consumers with the same `group.id` share the partitions of a topic - each partition is read by **one consumer in the group**, so parallelism is limited by the partition count. Different groups each get all messages (pub/sub). Extra consumers beyond partitions sit idle.

### Q4 [intermediate] How does Kafka guarantee ordering?
Only **within a partition**. Records with the same key go to the same partition (hash of key), so all events for one order/customer stay ordered. No global ordering across partitions. Changing partition count breaks the key->partition mapping for existing keys.

### Q5 [intermediate] Explain delivery semantics: at-most-once, at-least-once, exactly-once.
At-most-once: commit offset before processing (can lose). At-least-once: process, then commit (can duplicate) - the practical default. Exactly-once: idempotent producer + transactions (read-process-write within Kafka) with `read_committed` consumers. For an external DB sink, make the write **idempotent** (unique event id / upsert).

### Q6 [intermediate] What producer settings give "don't lose messages"?
`acks=all`, `enable.idempotence=true` (dedupes broker-side retries; implies safe `max.in.flight`), `retries` high with `delivery.timeout.ms` bounded, topic `min.insync.replicas=2` with replication factor 3, and always handle the send callback/future failure. `linger.ms` and `batch.size` trade latency for throughput; `compression.type=lz4/zstd`.

### Q7 [intermediate] Why disable auto-commit and how do you commit offsets?
Auto-commit commits on a timer, possibly before your processing finishes -> silent loss on a crash. Use manual commit after success (`AckMode.RECORD`/`BATCH`/`MANUAL` in Spring Kafka) or commit transactionally with the DB write result. Commit per batch to reduce overhead.

### Q8 [intermediate] What is a rebalance and why does it hurt?
When consumers join/leave or time out, partitions are reassigned and consumption pauses. Causes: slow processing exceeding `max.poll.interval.ms`, missed heartbeats (`session.timeout.ms`), deployments. Reduce impact: cooperative sticky assignor (incremental), static membership (`group.instance.id`), smaller `max.poll.records`, fast handlers; the new protocol (KIP-848) moves assignment to the broker and is much smoother.

### Q9 [intermediate] How do you handle a poison message and retries?
Classify errors: **non-retryable** (bad schema/validation) -> straight to a Dead Letter Topic; **retryable** (DB down) -> bounded retries with backoff. In Spring Kafka use `DefaultErrorHandler` with `ExponentialBackOff` and `DeadLetterPublishingRecoverer`, or `@RetryableTopic` for non-blocking retry topics (trade-off: loses strict ordering per key). Never block the poll loop with long `sleep`.

### Q10 [intermediate] How do you make a consumer idempotent?
Store a processed event id (unique key) in the same transaction as the side effect; use upserts (`INSERT ... ON CONFLICT DO NOTHING`, `MERGE` in Oracle); make state changes conditional on version. Redelivery is normal (rebalance, retry), so every handler must tolerate duplicates.

### Q11 [intermediate] Kafka vs RabbitMQ - when each?
Kafka: high throughput, retention/replay, event streaming, ordering per key, many independent consumer groups. RabbitMQ: smart broker with routing (exchanges), per-message ack/TTL/priorities, request/reply, work queues, lower latency for small loads. Pick Kafka for event log/analytics/integration; RabbitMQ for task distribution and complex routing.

### Q12 [intermediate] RabbitMQ basics: exchange types, acks, DLQ?
Producers publish to an **exchange** (direct, topic, fanout, headers) which routes to **queues** by binding key. Consumers `ack` after processing (`nack`/requeue on failure); use publisher confirms, durable queues + persistent messages, prefetch (QoS) to limit in-flight messages, and a dead-letter exchange with TTL/`x-delivery-limit` for poison messages. Quorum queues are the recommended HA type.

### Q13 [advanced] How does replication and `min.insync.replicas` work?
Writes go to the partition leader and followers copy it; the **ISR** (in-sync replicas) are followers caught up. With `acks=all`, a write succeeds only when all ISR have it, and fails if ISR size < `min.insync.replicas`. RF=3, min.isr=2 survives one broker loss without data loss or unavailability. `unclean.leader.election` should stay off.

### Q14 [advanced] How do you size partitions and choose keys?
Partitions >= max consumers you want in parallel; start from target throughput / per-partition throughput (~10 MB/s is a rough rule), leave growth room (you can add but not reduce, and adding changes key mapping). Choose a key with even distribution and the ordering unit you need (orderId, accountId). Beware hot keys (one huge customer) - consider salting if ordering allows.

### Q15 [advanced] Explain log compaction and retention.
Retention deletes old segments by time/size. Compaction keeps the **latest value per key** (a changelog / table-like topic; tombstone = null value deletes the key). Used for state topics, CDC, config. Compaction doesn't guarantee immediate removal.

### Q16 [advanced] How do you manage schemas and evolution?
Schema Registry with Avro/Protobuf/JSON Schema; messages carry a schema id. Use BACKWARD (or BACKWARD_TRANSITIVE) compatibility: new consumers read old data - so add fields with defaults, don't rename/remove required fields. Disable auto-register in production; CI registers schemas after a compatibility check.

### Q17 [advanced] How do you monitor Kafka consumers?
**Consumer lag** per partition (the most important metric), records consumed rate, processing time, rebalance count, error/DLT rate, under-replicated partitions and request latency on brokers (JMX -> Prometheus/Datadog/CloudWatch). Alert on lag growing for N minutes, not on one spike. Burrow/Kafka UI/Conduktor help inspect.

### Q18 [advanced] Consumer lag is growing - how do you debug?
1. Is the producer rate up or the consumer rate down? 2. Check the handler time per record (slow DB call, downstream timeout). 3. Rebalance loops (poll interval exceeded). 4. Partition skew (one hot partition). 5. Poison message retrying forever. Fix: optimise the handler/batch writes, increase partitions + consumers (not beyond partitions), use concurrency in the listener, move slow work off the poll thread safely, scale downstream.

### Q19 [advanced] What are Kafka transactions and exactly-once in Kafka Streams?
A transactional producer atomically writes output records and the consumed offsets; consumers using `read_committed` only see committed data. Kafka Streams enables it with `processing.guarantee=exactly_once_v2`. It covers Kafka-to-Kafka only; an external database still needs idempotency.

### Q20 [advanced] What changed with Kafka 4.0 (KRaft, queues)?
ZooKeeper is gone: metadata is managed by a Raft quorum inside Kafka (simpler ops, faster failover and recovery, higher partition limits). Clusters on ZooKeeper must migrate to KRaft (via 3.x) before upgrading. **Queues for Kafka / share groups** let multiple consumers cooperatively read the same partition with per-record acknowledgement (early access in 4.0, preview in 4.1) - helpful for queue-style workloads. Say "check the current release notes" for production use.

### Q21 [design] Design an event pipeline: ingest court files -> parse -> publish to Kafka -> sink to a database.
Files land in S3 -> an S3 event/notification triggers a parser (Quarkus CLI/Lambda) -> normalised JSON/Avro events keyed by record id are produced to Kafka -> a consumer group batches records, validates, upserts into the DB (idempotent), then commits offsets -> failures go to a DLT with the reason and original offset -> replay tool re-drives the DLT. Metrics: lag, parse failures per court/format, DLT size. Make parsers pure and unit-testable.

### Q22 [design] Design a notification system handling 50k events/sec with retries and ordering per user.
Key by `userId` (ordering per user), enough partitions (e.g. 48-96) and consumers, producers with idempotence, a consumer that deduplicates by event id, channel-specific retry topics with backoff (email/SMS/push) and a DLT, rate limiting per provider, templates in a separate service, and a read model of delivery status. Scale by partitions; protect providers with circuit breakers.

### Q23 [design] Design a Change Data Capture (CDC) pipeline from Oracle/PostgreSQL to Kafka.
Debezium (Kafka Connect) reads the DB log (LogMiner/XStream for Oracle, logical decoding for Postgres) and emits change events per table; use the outbox event router for domain events; schema registry for evolution; sink connectors to search/analytics; handle initial snapshot, DDL changes, large transactions and monitoring of connector lag.

### Q24 [intermediate] How do you test Kafka code?
Unit-test handlers as plain methods; integration-test with **Testcontainers Kafka** (or `@EmbeddedKafka`, KRaft-only now) and Awaitility for async assertions; test retries/DLT paths and duplicate delivery; contract-test schemas. Avoid `Thread.sleep`.

### Q25 [intermediate] Honest answer if asked "have you run Kafka clusters yourself?"
Say what is true: "I've built producers/consumers and the delivery/retry/DLT patterns, and operated them on managed services (e.g. MSK). Broker administration (partition reassignment, KRaft quorum) was handled by the platform team, but I understand the concepts - replication, ISR, min.insync.replicas, retention - and can reason about capacity and failure modes."
