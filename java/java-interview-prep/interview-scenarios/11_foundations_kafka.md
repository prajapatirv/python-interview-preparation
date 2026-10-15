---
id: foundations-kafka
title: Kafka from the basics: concepts, a real story, then the answer
stack: java
skill: kafka
---
These entries are written **from the ground up**: *Start here: the concepts* in plain words, then a real
production story, then the answer an interviewer expects. Read them before the dense crib answers.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What are topics, partitions and offsets, and why does Kafka need partitions?
tags: kafka, topic, partition, offset, ordering, parallelism, basics

**Start here: the concepts**
- **Broker:** a Kafka server that stores messages on disk.
- **Topic:** a named stream of messages, like a table or a folder, for example `orders`.
- **Partition:** a topic is split into partitions. Each partition is an append-only, ordered log stored on one broker (with replicas on others).
- **Offset:** the position number of a message inside one partition (0, 1, 2…). It is how a reader remembers where it stopped.
- **Key:** an optional value on each message. Messages with the same key always go to the same partition.

**The live scenario**
An e-commerce site publishes order events at 5,000 per second. One server cannot take that on a single log. The `orders` topic is split into 12 partitions spread across 3 brokers, so writes and reads run in parallel. Order events use `orderId` as the key, so all events of one order land in one partition and are read in order: created, paid, shipped.

**What the interviewer is really checking**
That you know partitions are the unit of both parallelism and ordering, and that ordering is only guaranteed within one partition.

**How I answer it**
1. **A topic is a set of partitions;** each partition is an ordered, append-only log.
2. **Partitions give parallelism:** many producers write and many consumers read different partitions at the same time.
3. **Ordering is per partition,** not per topic; the key decides the partition (`hash(key) % partitions`).
4. **Offsets are per partition;** a consumer group stores the last committed offset for each partition so it can resume.
5. **Partition count is a design decision:** it caps consumer parallelism, and increasing it later changes `hash(key) % count`, which breaks ordering for existing keys.

**Trade-offs and what can go wrong**
More partitions mean more parallelism but more open files, more replication work and longer leader elections. A badly chosen key creates a hot partition.

**How I'd monitor it**
Bytes in per partition for skew, consumer lag per partition, and under-replicated partitions.

**60-second answer**
A topic is split into partitions, each an ordered append-only log with its own offsets. Partitions give parallelism, and ordering is guaranteed only within one partition, chosen by the message key. I size the partition count from throughput and consumer parallelism up front because changing it later breaks key ordering.

### Q2 [mid] What is a consumer group, and why can't I have more useful consumers than partitions?
tags: kafka, consumer-group, partition-assignment, scaling, parallelism, basics

**Start here: the concepts**
- **Consumer:** an application instance that reads messages from topics.
- **Consumer group:** a set of consumers sharing the same `group.id`. Kafka splits the topic's partitions among them so each message is processed by *one* consumer in the group.
- **Assignment:** a partition is owned by exactly one consumer in a group at a time.
- **Independent groups:** two different groups each get *every* message (for example billing and analytics).

**The live scenario**
The `orders` topic has 6 partitions and one consumer processing 200 messages per second, but 600 arrive per second. The team scales the service to 3 pods: each now owns 2 partitions and throughput triples. They then scale to 10 pods and nothing improves: 6 pods own a partition each and 4 sit idle, because there is nothing left to assign them.

**What the interviewer is really checking**
That you can explain the rule "parallelism is capped by partitions" and what to do when you hit it.

**How I answer it**
1. **One partition, one consumer per group:** that is how Kafka preserves per-partition ordering.
2. **Therefore:** max useful consumers in a group = number of partitions; extras are idle standby.
3. **To go faster than that:** make each consumer faster (batching, async IO, bulk DB writes), or create a topic with more partitions and migrate.
4. **Different teams, different groups:** each group reads independently and keeps its own offsets.
5. **Membership changes cause rebalances,** which temporarily pause consumption.

**Trade-offs and what can go wrong**
Scaling pods beyond partitions wastes money. Per-record work that is slow caps throughput per partition regardless of pod count.

**How I'd monitor it**
Consumer lag per partition, partitions per consumer, idle consumers and CPU per pod.

**60-second answer**
A consumer group splits a topic's partitions so each partition is read by one consumer, which preserves ordering. So useful consumers are capped by partition count; beyond that they idle. To scale further I make each consumer faster or add partitions, and I keep different applications in separate groups.

### Q3 [mid] What is consumer lag, and what does it tell you?
tags: kafka, consumer-lag, offsets, monitoring, backlog, basics

**Start here: the concepts**
- **Log-end offset:** the offset of the newest message in a partition.
- **Committed offset:** the offset up to which a consumer group has confirmed it has processed.
- **Lag:** log-end offset minus committed offset: how many messages are waiting.
- **Time lag:** lag divided by consume rate: how many *seconds or minutes* behind you are.

**The live scenario**
A payments consumer has lag of 50,000 and looks alarming, but it consumes 5,000 messages per second, so it is 10 seconds behind and stable. A different consumer has lag of only 3,000 but is consuming 10 per second, so it is 5 minutes behind and the gap grows every minute. The number of messages alone told the wrong story; the trend and the rate matter.

**What the interviewer is really checking**
That you read lag as a symptom, look at trend and distribution, and convert it into time.

**How I answer it**
1. **Define it:** log-end minus committed offset, per partition.
2. **Trend over value:** stable means keeping up; growing means consumers are slower than producers.
3. **Distribution:** all partitions growing means overall throughput; one partition means a hot key, a poison message or a slow instance.
4. **Convert to time lag** for an SLO such as "orders processed within 30 seconds".
5. **Find the cause:** processing time per record, downstream latency, rebalances, GC pauses.
6. **Read it with** `kafka-consumer-groups.sh --describe --group <g>` or Micrometer consumer metrics.

**Trade-offs and what can go wrong**
Zero lag does not prove correctness: the consumer may be committing without processing. Large lag together with short retention can cause data loss when messages expire.

**How I'd monitor it**
Alert on time lag and its growth rate per partition, plus rebalance rate and DLQ rate.

**60-second answer**
Lag is how far a consumer group is behind the newest message, per partition. I watch its trend and its distribution rather than a raw count, convert it to time lag for an SLO, and use the pattern to locate the cause: slow processing, a downstream dependency, rebalances or one poisoned partition.

### Q4 [mid] What is a rebalance, and why does it hurt?
tags: kafka, rebalance, consumer-group, cooperative-sticky, static-membership, max-poll-interval, basics

**Start here: the concepts**
- **Group coordinator:** a broker that manages which consumer owns which partition.
- **Rebalance:** the process of reassigning partitions among the consumers of a group.
- **Heartbeat:** a periodic signal a consumer sends to prove it is alive.
- **Poll loop:** the consumer repeatedly calls `poll()` to fetch records and must call it again within `max.poll.interval.ms`.
- **Stop-the-world rebalance:** the older "eager" protocol, where *all* consumers give up *all* partitions during reassignment.

**The live scenario**
A consumer pod takes 6 minutes to process a big batch, longer than `max.poll.interval.ms` (5 minutes). The coordinator decides it is dead and rebalances. Every consumer in the group pauses, partitions move, the slow pod finishes and tries to commit but no longer owns the partition, so the batch is processed again by someone else. Lag spikes in a saw-tooth pattern every deploy and every slow batch.

**What the interviewer is really checking**
That you know the triggers and the practical mitigations, not just the definition.

**How I answer it**
1. **Triggers:** a consumer joins or leaves (deploy, crash, autoscale), a missed heartbeat or `session.timeout.ms`, exceeding `max.poll.interval.ms`, or partitions added.
2. **Impact:** consumption pauses and in-flight work may be redone, so duplicates appear and lag spikes.
3. **Reduce triggers:** keep processing per poll well under `max.poll.interval.ms` by lowering `max.poll.records`; avoid autoscaler flapping.
4. **Reduce impact:** the cooperative sticky assignor moves only the partitions that must move; static membership (`group.instance.id`) lets a restarting pod return without a rebalance.
5. **Be safe regardless:** commit after processing and make handlers idempotent.

**Trade-offs and what can go wrong**
A larger session timeout detects real failures slowly. Static membership needs stable instance ids.

**How I'd monitor it**
`rebalance-rate-per-hour`, rebalance latency, `time-between-poll-max`, and lag saw-tooth shape.

**60-second answer**
A rebalance reassigns partitions among group members, pausing consumption. It is triggered by joins, leaves, missed heartbeats or a poll that takes too long. I reduce it with smaller batches, cooperative sticky assignment and static membership, and I make processing idempotent because a rebalance can cause reprocessing.

### Q5 [senior] What do `acks`, `linger.ms` and `batch.size` do, and how do you trade latency, throughput and durability?
tags: kafka, producer, acks, linger-ms, batch-size, compression, idempotence, basics

**Start here: the concepts**
- **Producer:** the client that sends messages to Kafka.
- **Batch:** several messages grouped into one network request for one partition.
- **`linger.ms`:** how long the producer waits to fill a batch before sending.
- **`batch.size`:** the maximum size in bytes of a batch.
- **`acks`:** how many broker acknowledgements the producer waits for. `0` none; `1` the leader only; `all` the leader and all in-sync replicas.
- **ISR (in-sync replicas):** the replicas that are caught up with the leader. `min.insync.replicas` is how many must be present for a write to succeed under `acks=all`.

**The live scenario**
An audit pipeline sends 50,000 small events per second with defaults (`linger.ms=0`, `batch.size=16 KB`): each message goes in its own tiny request and the producer spends its time on overhead. Setting `linger.ms=10`, `batch.size=128 KB` and `compression.type=lz4` cuts requests by 20x, raises throughput several-fold and adds at most 10 ms of delay. For payments the team keeps `acks=all`, `min.insync.replicas=2` and idempotence, accepting a few more milliseconds for no data loss.

**What the interviewer is really checking**
That you understand the three-way trade-off and can choose settings per use case rather than reciting defaults.

**How I answer it**
1. **Throughput:** raise `linger.ms` and `batch.size`, and enable compression, so each request carries many messages.
2. **Latency:** each of those adds a small wait; keep `linger.ms` within the latency budget.
3. **Durability:** `acks=all` with `min.insync.replicas=2` and replication factor 3 survives one broker loss without losing acknowledged data; `acks=1` can lose data if the leader dies before replicating.
4. **Retries without duplicates:** `enable.idempotence=true` makes producer retries safe.
5. **Pick by use case:** payments and audit favour durability; clickstream and metrics favour throughput.
6. **Verify with metrics:** `batch-size-avg`, `request-latency-avg`, `record-retry-rate`, `compression-rate-avg`.

**Trade-offs and what can go wrong**
`acks=all` with too few in-sync replicas makes writes fail rather than lose data (a deliberate choice). Compression costs CPU. A too-small `buffer.memory` makes `send()` block.

**How I'd monitor it**
Producer send rate, request latency, retry and error rate, buffer wait time, and broker under-replicated partitions.

**60-second answer**
`linger.ms`, `batch.size` and compression trade a little latency for much higher throughput by batching; `acks=all` with `min.insync.replicas=2` and idempotence trades a little latency for no acknowledged data loss. I choose per use case, payments for durability and telemetry for throughput, and confirm with batch size, latency and retry metrics.

### Q6 [senior] Kafka is at-least-once by default. How do duplicates happen and how do you handle them?
tags: kafka, delivery-semantics, at-least-once, idempotent-consumer, exactly-once, duplicates, basics

**Start here: the concepts**
- **At-most-once:** a message is delivered zero or one time; it can be lost, never duplicated.
- **At-least-once:** delivered one or more times; never lost, but can be duplicated.
- **Exactly-once:** the effect happens once; in Kafka this holds inside Kafka (transactions), not automatically for external systems.
- **Idempotent operation:** doing it twice has the same result as doing it once.
- **Commit:** telling Kafka "I have processed up to this offset".

**The live scenario**
A consumer writes each order to the database and then commits the offset. It crashes after the insert but before the commit. On restart it re-reads the same message and inserts the order again: two rows, and the customer is charged twice. No message was lost, which is exactly the at-least-once guarantee working as designed.

**What the interviewer is really checking**
That you know where duplicates come from and that the fix is at the consumer or sink, not "turn on exactly-once and forget".

**How I answer it**
1. **How duplicates arise:** consumer crash between process and commit, rebalances, producer retries without idempotence, replays.
2. **Choose the commit order deliberately:** commit after processing gives at-least-once; commit before gives at-most-once and can lose work.
3. **Make the handler idempotent:** a unique key (event id or business key) with an upsert or a unique index, or an "already processed" table checked inside the same transaction.
4. **Producer side:** `enable.idempotence=true` removes duplicates caused by producer retries.
5. **Kafka-to-Kafka exactly-once:** transactions plus `isolation.level=read_committed`.
6. **Kafka-to-database:** use the outbox pattern or write the offset and the data in the same database transaction.

**Trade-offs and what can go wrong**
Idempotency tables add storage and a lookup. Transactions reduce throughput. "Exactly-once" claims often stop at the Kafka boundary.

**How I'd monitor it**
Duplicate-detected counters, DLQ rate, unique-constraint violations, and reconciliation jobs comparing source and sink counts.

**60-second answer**
Kafka delivers at-least-once, so a crash between processing and committing replays the message. I commit after processing and make the handler idempotent with a unique key, use an idempotent producer, and use transactions only for Kafka-to-Kafka flows, with the outbox or a single database transaction for the sink.

### Q7 [senior] Tuning Kafka configuration for handling large scale of traffic
tags: kafka, tuning, throughput, partitions, producer, consumer, broker, replication, lag, capacity, basics

**Start here: the concepts**
- **Throughput:** how much data Kafka moves per second, in messages per second and in MB per second. Large scale means both are high.
- **Partition:** one ordered log inside a topic. It is the unit of parallelism: one partition has one leader broker and is read by one consumer of a group at a time.
- **Batch:** many messages sent in one request. Network and disk are far more efficient with big batches than with many tiny requests.
- **Replication and ISR:** every partition is copied to other brokers. The in-sync replicas (ISR) are the copies that are caught up. More copies mean safer data but more network and disk work.
- **Page cache:** Kafka leans on the operating system's file cache, so recent data is served from memory instead of disk. Memory left to the OS matters.
- **Consumer lag:** how far consumers are behind the newest message; the scoreboard that says whether you are keeping up.
- **Backpressure:** when a downstream part is slower, pressure travels backwards: the producer buffer fills and `send()` blocks or fails.
- **Tuning is a trade-off** between throughput, latency and durability; every setting moves one of them.

**The live scenario**
A retail platform publishes order and click events. On a normal day it handles 5,000 messages per second; for a flash sale it must handle 50,000 per second for an hour. In the first load test at 30,000 per second three things appear: producer buffers fill and `send()` blocks; broker request latency climbs because every small message is its own request; and consumers fall four minutes behind because six partitions allow only six busy consumers and each inserts rows into the database one at a time. Nothing is "broken"; the defaults suit moderate traffic, and each layer needs its own adjustment.

**What the interviewer is really checking**
That you do not recite settings. They want an ordered method: start from numbers, find the limiting layer, change one thing at a time, and state the trade-off each setting costs.

**How I answer it**
1. **Start from requirements, with numbers.** Peak messages per second, average message size (so MB per second), latency target, whether loss or duplicates are acceptable, and ordering needs. Example: 50,000 msg/s x 1 KB is about 50 MB/s in; with replication factor 3 the cluster writes about 150 MB/s, and consumers read more.
2. **Partitions first, because they set the ceiling.**
   - `partitions >= max(target MB/s / MB/s one partition can take, target MB/s / MB/s one consumer can process)`. If a partition takes about 10 MB/s and a consumer processes 5 MB/s, 50 MB/s needs about 10 partitions; add headroom, so 24 to 48.
   - Consumers beyond the partition count sit idle, so partitions also cap consumer parallelism.
   - Plan it now: adding partitions later changes `hash(key) % count` and breaks per-key ordering.
   - Use a high-cardinality key so no single partition becomes hot.
3. **Producer: batch and compress.**
   - `linger.ms` 5 to 20 and `batch.size` 64 to 256 KB so each request carries many messages; `compression.type=lz4` (fast) or `zstd` (smaller).
   - `acks=all` with `enable.idempotence=true` for important data; keep in-flight requests at 5 or fewer.
   - Raise `buffer.memory` if the producer blocks, and send asynchronously with a callback.
4. **Brokers: replication and resources.**
   - Replication factor 3 with `min.insync.replicas=2` and `unclean.leader.election.enable=false`.
   - `num.network.threads` and `num.io.threads` sized from the idle-percent metrics; `num.replica.fetchers` for follower catch-up.
   - Fast disks, enough RAM left for the page cache, and a network that can carry ingest x replication x consumer fan-out.
   - Even leader and partition spread across brokers, and quotas so one noisy client cannot starve the rest.
5. **Consumers: process in bulk and stay in the group.**
   - `max.poll.records` sized so one batch finishes well inside `max.poll.interval.ms`; raise `fetch.min.bytes` to avoid tiny fetches.
   - **Batch the downstream write** (one bulk insert, not a row per message). This is usually the biggest consumer win.
   - Cooperative sticky assignor and static membership to avoid stop-the-world rebalances; commit after processing and make handlers idempotent.
   - Retry topic and dead-letter topic so one bad message cannot block a partition.
6. **Retention and storage.** Set `retention.ms` or `retention.bytes` so disks never fill at peak; use compaction only where the data model needs it.
7. **Prove it, one change at a time.** Load-test with realistic message size and key distribution, change one setting, and compare produce p99, consume rate, max lag, and broker CPU, disk and network against the baseline.

```text
# producer                          # consumer                       # topic
linger.ms=10                        max.poll.records=500             partitions=48
batch.size=131072                   fetch.min.bytes=65536            replication.factor=3
compression.type=lz4                enable.auto.commit=false         min.insync.replicas=2
acks=all, enable.idempotence=true   partition.assignment.strategy=CooperativeStickyAssignor
```

**Trade-offs and what can go wrong**
- Larger batches and `linger.ms` raise throughput but add a few milliseconds of latency per message.
- `acks=all` and replication are safer but slower than `acks=1`; with too few in-sync replicas writes fail instead of losing data, which is deliberate.
- More partitions give more parallelism but cost file handles, replication work and longer leader elections, and make key ordering harder to keep.
- Compression saves network and disk but costs CPU on producers and consumers.
- A bigger `max.poll.records` means fewer polls, but if one batch takes longer than `max.poll.interval.ms` the consumer is removed and a rebalance follows.
- The most common mistake is tuning Kafka while the real bottleneck is the consumer's database write.

**How I'd monitor it**
- **Producer:** `record-send-rate`, `request-latency-avg`, `record-retry-rate`, `batch-size-avg`, `bufferpool-wait-time`.
- **Brokers:** `BytesInPerSec` and `BytesOutPerSec` per broker, `RequestHandlerAvgIdlePercent` and `NetworkProcessorAvgIdlePercent` (investigate below about 30%), `UnderReplicatedPartitions` (should be 0), disk usage, partition and leader balance.
- **Consumers:** lag per partition and its trend (alert on time lag), `records-consumed-rate`, `rebalance-rate-per-hour`, `time-between-poll-max`.

**Follow-ups to expect**
- *How many partitions would you create?* -> compute from target throughput divided by what one partition and one consumer can handle, then add headroom; state the formula and that you cannot shrink later.
- *Consumers are at the partition limit and lag still grows?* -> make each consumer faster (bulk writes, async IO, caching), or create a new topic with more partitions and migrate.
- *How do you keep ordering while scaling?* -> key by the entity that needs ordering; ordering only holds per partition.
- *What about exactly-once at this scale?* -> idempotent producer plus transactions inside Kafka; for a database sink use an idempotent write or the outbox pattern.
- *One broker is hot?* -> rebalance leaders and partitions, check key skew, and add brokers before it saturates.

**60-second answer**
I start from the numbers: peak messages per second, message size, and the latency and durability needs. Then I size partitions from throughput and consumer parallelism, with replication factor 3 and min in-sync replicas 2. On the producer I batch with `linger.ms`, `batch.size` and compression, with idempotence and `acks=all`. On the brokers I check thread idle percent, disk, network and balance. On the consumers I size `max.poll.records`, write to the database in batches, use cooperative rebalancing and commit after processing. I load-test one change at a time and judge by produce p99, consume rate and lag, because the bottleneck is often the consumer's sink and not Kafka itself.
