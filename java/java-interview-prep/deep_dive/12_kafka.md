# Apache Kafka: topics, partitions, consumer groups, offsets, rebalancing, lag, performance, scaling

> **Runnable:** [`01_partitions_keys_and_ordering.java`](../examples/12_kafka/01_partitions_keys_and_ordering.java) ·
> [`02_consumer_groups_rebalancing_and_lag.java`](../examples/12_kafka/02_consumer_groups_rebalancing_and_lag.java) ·
> [`03_delivery_semantics_idempotency_dlt.java`](../examples/12_kafka/03_delivery_semantics_idempotency_dlt.java) ·
> [`04_kafka_config_and_capacity_math.java`](../examples/12_kafka/04_kafka_config_and_capacity_math.java)
> **Crib sheet:** [`topics/09-kafka-messaging.md`](../topics/09-kafka-messaging.md) · **Guide:** Q55–Q73, Q91, Q92

## What interviewers are actually probing

The requirement names the exact list: **topics, partitions, consumer groups, offsets, rebalancing, lag, performance, scaling**. Each is a thread they can pull:
partition → ordering → key choice → hot partition → rebalance → commit strategy → duplicates → idempotency → lag → capacity. The strongest answers connect them:
*"scaling consumers is bounded by partitions; ordering is per partition, so key choice drives both parallelism and correctness."*

## Must-know points

- **Topic** = named log split into **partitions**; each partition is an ordered, append-only sequence with **offsets**. Order is guaranteed **only within a partition**.
- Producer picks the partition: by **key hash** (`murmur2(key) % partitions`), or sticky/round-robin for null keys.
- **Consumer group**: partitions of a topic are divided among the group's consumers; **one partition → at most one consumer per group**; different groups each get all records. Max useful consumers = partition count.
- **Offsets** are per (group, partition), stored in `__consumer_offsets`. Commit semantic = "records < offset are done".
- **Rebalance** reassigns partitions on join/leave/crash/timeout; eager = stop-the-world, cooperative-sticky = incremental.
- **Lag** = log end offset − committed offset. It is a symptom; compare produce rate vs consume rate.
- Durability: `acks=all` + `min.insync.replicas=2` + RF=3 + `enable.idempotence=true`. Exactly-once is scoped to Kafka-to-Kafka (transactions); external sinks need idempotency.

## Interview questions and full answers

### Q1. What is Kafka and why use it instead of a queue like RabbitMQ?

A distributed, replicated, partitioned **commit log**. Consumers pull and track their own position, so records are **retained** (time/size) and can be **replayed**, and many independent consumer groups can read the same data. Throughput is very high (sequential disk I/O, batching, zero-copy).
RabbitMQ is a broker-centric **queue**: rich routing (exchanges), per-message ack and deletion, priorities, RPC patterns — better for task distribution; Kafka is better for **event streaming, integration, audit and replay**.

### Q2. Explain brokers, topics, partitions, replicas and leaders.

A cluster is N **brokers**. A topic's partitions are spread across brokers; each partition has a **leader** (serves reads/writes) and **follower** replicas (replicate the log). Replication factor 3 means three copies.
The **ISR** is the set of replicas caught up with the leader; on leader failure a new leader is elected from the ISR. Metadata is managed by the **KRaft** controller quorum (ZooKeeper was removed in Kafka 4.0).

### Q3. Why does Kafka partition topics, and how do you choose the partition count?

Partitions give **parallelism** (producers, brokers, consumers), **scalability** (spread across brokers) and the unit of ordering.
Count = max(target throughput ÷ per-partition producer throughput, target ÷ per-partition consumer throughput), then headroom for growth and for the maximum number of consumers you'll want (example 12/01 section 6: 120 MB/s → 24).
Costs of too many: open file handles, longer leader elections/rebalances, more memory, higher end-to-end latency. You can **add** partitions but never remove them, and adding **remaps keys** (example 12/01 section 5: 75% of keys move 6 → 8).

### Q4. How does key-based partitioning work, and how do you choose a key?

`partition = toPositive(murmur2(keyBytes)) % numPartitions` for the default partitioner. Same key ⇒ same partition ⇒ **per-key ordering**.
Choose the key from the **ordering requirement** (orderId, accountId), then check **distribution**: a skewed key (one huge tenant) creates a **hot partition** that no amount of consumers can fix (example 12/01 section 4). Mitigations: salt the key if per-key order isn't needed, custom partitioner, dedicated topic for the heavy tenant.
No key = best balance, **no ordering**.

### Q5. What is a consumer group, and how are partitions assigned?

Consumers with the same `group.id` form a group; the **group coordinator** (a broker) and the **group leader** (one consumer) compute assignment using the configured **assignor**:
`RangeAssignor` (per topic contiguous ranges — can be unbalanced across topics), `RoundRobinAssignor`, `StickyAssignor`, **`CooperativeStickyAssignor`** (balanced, minimal movement, incremental rebalances).
Example 12/02 sections 1–2: 6 partitions with 8 consumers → 2 idle; range gives 4 vs 2 over two topics, round-robin gives 3 vs 3.
(Kafka 4.0's new consumer group protocol KIP-848 moves assignment to the broker and removes the global stop-the-world.)

### Q6. What is an offset and how does committing work?

An offset is a record's position in a partition. The consumer's **committed offset** is the next record to read after a restart/rebalance. Commit styles: auto (`enable.auto.commit=true`, every 5 s, **commits before you've finished processing** if you use another thread or are slow), manual sync/async (`commitSync`/`commitAsync`), or Spring `AckMode` (`RECORD`, `BATCH`, `MANUAL`).
Safe default: **disable auto-commit; process, persist, then commit**. Committing offset N means everything below N in that partition is done — so with concurrent processing you must commit only the contiguous completed prefix.
`auto.offset.reset` (`earliest`/`latest`) applies **only when there is no committed offset**.

### Q7. At-most-once, at-least-once, exactly-once — what does each mean and what do you use?

- **At-most-once**: commit before processing → loses records on a crash.
- **At-least-once**: process, then commit → duplicates after a crash (the default design).
- **Exactly-once**: Kafka **transactions** make consume-process-produce between Kafka topics atomic (`transactional.id`, `isolation.level=read_committed`, Streams `exactly_once_v2`). They don't cover a database or HTTP call.
For DB sinks: at-least-once + **idempotent writes** (unique key/UPSERT, processed-event table) gives an exactly-once *effect*. Example 12/03 section 1 prints 3 lost / 2 duplicated / 0 lost-0-dup for the three strategies.

### Q8. What causes a rebalance and how do you minimise them?

Triggers: consumer joins/leaves, crash, **missed heartbeat** (`session.timeout.ms`), **`max.poll.interval.ms` exceeded** (processing between polls too long), subscription/partition change.
Effects: consumption pauses, lag spikes, duplicates (uncommitted work is reprocessed), and revoke callbacks run.
Mitigate: `CooperativeStickyAssignor`; keep per-poll work short (`max.poll.records` ↓, move heavy work to a bounded worker pool but then commit carefully); **static membership** (`group.instance.id`) so rolling restarts within `session.timeout.ms` don't rebalance; graceful shutdown (`close()`/Spring `stop`); avoid long GC pauses; stabilise deployments (one pod at a time with readiness).

### Q9. Explain `session.timeout.ms`, `heartbeat.interval.ms`, `max.poll.interval.ms`.

Heartbeats come from a **background thread**: if none arrive within `session.timeout.ms` the member is declared dead (defaults 45 s in recent clients, heartbeat 3 s). `max.poll.interval.ms` (5 min) is a **progress** check on your processing loop: if `poll()` isn't called in time the consumer leaves the group even though heartbeats flow.
So: heartbeats prove *liveness*, polling proves *progress*. Tuning only one blindly just shifts the failure mode.

### Q10. What is consumer lag, what causes it, and how do you reduce it?

Lag = log end offset − committed offset, per partition (aggregate with care; look at max and per-partition skew).
Causes: processing slower than production (slow DB/API call, heavy transform, logging), too few consumers vs partitions, **skewed keys**, frequent rebalances/GC pauses, producer burst, large messages/inefficient deserialisation, one poison message retried forever.
Process (example 12/02 sections 5–6): trend by partition → compare in-rate vs out-rate → check handler latency/errors → check rebalance count → fix the bottleneck (batch DB writes, async I/O, cache) → scale consumers **up to partition count** → if still skewed, fix the key. Time to drain = lag ÷ (consume rate − produce rate); if that denominator is ≤ 0 it never drains.

### Q11. How do you scale consumers? What is the ceiling?

Scale horizontally by adding instances (same `group.id`) or threads (`concurrency` in Spring Kafka creates N consumers) **up to the partition count**; beyond that they idle. To go further: raise partitions (mind key remapping), make each record faster (batching, async I/O), or fan out inside a consumer with a worker pool + safe commit tracking.
Always check the **downstream** (DB pool, partner rate limit) — more consumers just move the queue. In Kubernetes, scale on lag (KEDA) not CPU.

### Q12. Producer settings for reliability and throughput?

Reliability: `acks=all`, `enable.idempotence=true`, `retries` high with `delivery.timeout.ms` as the bound, `max.in.flight.requests.per.connection ≤ 5`, topic `min.insync.replicas=2`, RF=3, `unclean.leader.election.enable=false`.
Throughput: `linger.ms` 5–20, `batch.size` 32–128 KB, `compression.type=lz4|zstd`, enough partitions, async `send` with a callback (don't `get()` per record). Handle `send` failures — a fire-and-forget producer silently drops on error.
Example 12/04 prints the full table with the failure each setting prevents.

### Q13. What is retention vs log compaction?

`cleanup.policy=delete` removes old segments by time/size (`retention.ms`, `retention.bytes`). `compact` keeps at least the **latest value per key** (a tombstone — null value — deletes the key eventually): use for changelog/state topics (current customer profile).
Compaction is asynchronous and doesn't guarantee a single record per key at any instant; consumers must tolerate older values until compaction runs.

### Q14. Retry topics and dead-letter topics: how do you design them?

Classify errors: **non-retryable** (deserialisation, validation) → straight to the **DLT** with headers (original topic/partition/offset, exception, timestamp); **transient** (timeouts, 503) → retry with backoff, either **in place** (blocking: simple but stalls the partition) or via **retry topics** (`orders-retry-5s`, `-1m`, then DLT: non-blocking but reorders).
Spring Kafka: `DefaultErrorHandler` + `DeadLetterPublishingRecoverer` + `ExponentialBackOff`, `@RetryableTopic`, `ErrorHandlingDeserializer`. Define who monitors the DLT, how to replay, and that replay must be idempotent. A DLT does not fix a bug, it parks a symptom.

### Q15. How do you evolve schemas?

Use **Avro/Protobuf/JSON Schema** with a **Schema Registry** and a compatibility mode (BACKWARD is typical: new consumers can read old data → add optional fields with defaults, don't rename/remove). Roll out **consumers first** for backward, producers first for forward.
Never change a field's meaning or type in place; add a new field or a new event version. Test old-producer/new-consumer and the reverse in CI.

### Q16. How do you secure and operate Kafka?

TLS in transit, SASL (SCRAM/OAUTHBEARER/mTLS) authentication, **ACLs** per principal/topic/group, quotas per client, encryption at rest (disk/KMS), no PII in keys.
Monitor: under-replicated partitions, ISR shrink rate, request latency, disk, **consumer lag**, rebalance rate, produce/consume error rate. Alert on symptoms (lag growing, URP > 0) not just CPU.

### Q17. Kafka Streams vs a plain consumer vs Kafka Connect?

Plain consumer/producer for application logic; **Streams** for stateful stream processing (joins, windowing, aggregations with local RocksDB state and exactly-once); **Connect** for integration with databases/search/object stores (JDBC, Debezium CDC, S3, Elasticsearch) without code.

### Q18. Design: order events with Kafka end to end.

`orders` topic keyed by `orderId` (ordering per order), 12–24 partitions, RF=3, minISR=2; producer idempotent with `acks=all`, events written through the **outbox**; consumers per bounded context in their own groups, manual commit after an idempotent DB write, retry/DLT per consumer, schema registry with backward compatibility, lag + DLT-depth alerts, trace/correlation id in record headers, a compacted `order-state` topic for lookups.
Failure walk-through: broker down (producer buffers, `max.block.ms`, outbox keeps rows), consumer crash (rebalance, resume from commit, idempotency absorbs the replay), poison message (DLT), hot key (salting/dedicated topic).

### Q19. "Have you produced and consumed messages in Kafka?" - walk me through it end to end.

Don't answer "yes, producer and consumer". Give the **flow, then the failure handling**, because that is what proves production experience.

```text
Order Service -> KafkaProducer -> topic order-events [P0 | P1 | P2] -> consumer group payment-service (C1,C2,C3)
                                                                     -> consumer group inventory-service (own offsets)
```

**Produce path.** The service serialises an `OrderCreated` event (Avro/JSON + schema registry) and calls `send(key=orderId, value)`. The producer picks the partition (`murmur2(key) % partitions`, so one order always lands on one partition and stays ordered), **batches** records per partition (`linger.ms`, `batch.size`, compression), and sends to the partition **leader**. With `acks=all` the leader acknowledges only after every in-sync replica has the record (`min.insync.replicas=2`); idempotent producer (`enable.idempotence=true`) stops retries creating duplicates. The leader appends to the partition log and assigns the **offset**.

**Store path.** Records are an **append-only log**; consumers can only read up to the **high watermark** (replicated point). **Reading does not delete a record**: it stays until retention (`retention.ms`/`bytes`) or compaction removes it. That is what allows replay and many independent consumer groups, unlike a queue where consume = remove.

**Consume path.** Each consumer in a group gets a disjoint set of partitions (one partition -> one consumer *per group*; 3 partitions with 5 consumers leaves 2 idle). It `poll()`s a batch, processes, then **commits the offset** (manual commit after the work is persisted). Each group tracks its own offsets in `__consumer_offsets`, so the Payment and Inventory services read the same events independently, and the producer doesn't care if one of them is down: it resumes from its committed offset when it returns (decoupling, bounded by retention).

**Failure scenarios they will probe (and the answers):**

| Scenario | What happens | Answer |
|---|---|---|
| Consumer crashes mid-processing | no commit -> rebalance -> another consumer re-reads from the last committed offset | at-least-once; handler must be idempotent (Q7, Q8) |
| **DB commit succeeded, crash before offset commit** | record is redelivered, DB write would run twice | dedupe with a unique key / UPSERT / processed-event table in the *same DB transaction* as the business write; or commit the offset inside that design (Q7) |
| Processing throws (transient: timeout, 503) | not committed | bounded retry with backoff, then retry topic (Q14) |
| **Poison message** (bad payload, deserialisation, validation) | would block the partition forever if retried in place | `ErrorHandlingDeserializer`, classify as non-retryable, publish to **DLT** with original topic/partition/offset + exception headers, alert on DLT depth, replay idempotently after the fix (Q14) |
| Producer can't reach broker | `send` retries until `delivery.timeout.ms`, then fails the callback | outbox row stays, relay retries; never fire-and-forget (Q12, Q18) |
| Burst 100 -> 500 TPS | lag grows | check partition headroom first (consumers <= partitions), batch DB writes, scale consumers, add partitions only knowing keys remap (Q10, Q11; capacity math in 12/04) |

**Spoken answer (about 60 seconds):**
> "Yes. The order service publishes `OrderCreated` events to an `order-events` topic, keyed by order id so all events for an order go to one partition and stay ordered. We run the producer with `acks=all`, idempotence on and an outbox so a broker outage doesn't lose events. Payment and inventory are separate consumer groups, so each reads every event with its own offsets; inside a group, partitions are split across instances, and we size partitions for the parallelism we need because that is the ceiling. Kafka keeps the record after it's read, based on retention, so we can replay. We commit offsets manually after the DB write, which gives at-least-once, so handlers are idempotent with a unique key. Transient failures go through retry topics with backoff, poison messages go to a dead-letter topic with context headers and an alert, and we watch consumer lag, rebalances and DLT depth in production."

**Where each likely follow-up is answered:**

| Follow-up | See |
|---|---|
| Which partition does the producer pick? | Q4 |
| Topic vs partition | Q2, Q3 |
| Consumer group, assignment | Q5 |
| Consumer crash / rebalance | Q8, Q9 |
| Consumer lag, troubleshooting | Q10 |
| 100 -> 500 TPS | Q10, Q11, example 12/04; also `16_system_design.md` |
| Ordering guarantee | Q4 (per partition only) |
| Crash after DB commit | Q7 + this question |
| Idempotency | Q7 |
| At-most / at-least / exactly once | Q7 |
| Retry topic vs DLT, poison messages | Q14 |
| Monitoring | Q16 |

## A worked example

Work through the four examples in order; each answers the next interview question:

1. **12/01**: pick a key → see ordering and the 48% hot partition → see 75% of keys move on resize.
2. **12/02**: 6 partitions / 8 consumers → eager vs cooperative → the lag table (note ticks 5–8: lag stops growing but doesn't drain) → hot partition.
3. **12/03**: crash a consumer in each commit strategy → duplicate producer retries → DLT.
4. **12/04**: the config table and the drain-time/capacity arithmetic.

## Hands-on drills

1. Using the real `kafka-clients` (docker `apache/kafka`), reproduce a rebalance by starting/stopping a second consumer and log the revoke/assign callbacks.
2. Write a consumer that processes with 8 worker threads and commits only the **contiguous completed prefix** per partition.
3. Compute partitions, consumers and disk for 50k msg/s × 2 KB with 7-day retention and RF=3.
4. Build a retry-topic chain (5 s → 1 m → DLT) and decide its ordering consequences.
5. Explain what happens to `__consumer_offsets` and `auto.offset.reset` when a group is idle longer than `offsets.retention.minutes`.

## The 60-second spoken answer

"A topic is split into partitions; ordering is guaranteed per partition, and the producer's key decides the partition, so I choose the key from the
ordering requirement and check for skew. Consumers in a group split the partitions, so parallelism is capped at the partition count. Offsets are
committed after processing, which gives at-least-once, so handlers are idempotent; exactly-once is only for Kafka-to-Kafka with transactions.
Rebalances pause consumption, so I use cooperative-sticky assignment, static membership and short poll work. When lag grows I compare production
and consumption rates, look for skew, rebalances and slow downstreams, and scale consumers only up to the partition count and what the DB can take."
