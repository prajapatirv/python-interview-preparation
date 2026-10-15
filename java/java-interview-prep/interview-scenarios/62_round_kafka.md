---
id: round-kafka
title: Real interview round: Kafka architecture, failures and scaling
stack: java
skill: kafka
---
Questions asked in a real interview round, answered from the basics.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] What is the architecture of Kafka?
tags: kafka, architecture, broker, topic, partition, replication, consumer-group, kraft, zookeeper, basics

**Start here: the concepts**
- **Event / record:** one message: a key, a value, a timestamp and headers.
- **Broker:** a Kafka server. A **cluster** is several brokers working together.
- **Topic:** a named stream of records, for example `orders`.
- **Partition:** a topic is split into partitions; each is an ordered, append-only log on disk. Partitions are what let Kafka scale and run in parallel.
- **Offset:** the position of a record inside a partition.
- **Replication:** each partition is copied to several brokers. One copy is the **leader** (serves reads and writes); the others are **followers**. The **in-sync replicas (ISR)** are followers that are caught up.
- **Producer:** an application that writes records to a topic.
- **Consumer and consumer group:** consumers read records; a group shares a topic's partitions so each partition is read by one consumer in the group.
- **Controller / cluster metadata:** the part of the cluster that elects leaders and tracks metadata. Older clusters used ZooKeeper; newer ones use **KRaft**, Kafka's built-in Raft-based metadata quorum.

**The live scenario**
A retailer publishes 20,000 order events per second. One server cannot hold or serve that, and they must not lose events if a machine dies. Kafka's design answers both: the `orders` topic is split into 12 partitions spread over 3 brokers, each partition is replicated 3 times, and several downstream services (billing, inventory, analytics) read the same events independently in their own consumer groups.

**What the interviewer is really checking**
That you can describe the components and how a record flows through them, and explain the properties that follow: scalability, ordering per partition, durability and consumer independence.

**How I answer it**
1. **Components:** producers, a cluster of brokers, topics divided into partitions, replication with leader and followers, consumers in groups, and a metadata/controller layer (KRaft in current versions, ZooKeeper in older ones).
2. **Write path:** the producer picks a partition (by key hash, round-robin or a custom partitioner), sends a batch to that partition's leader, the leader appends it to its log, followers replicate it, and the producer is acknowledged according to `acks` (with `acks=all`, once the in-sync replicas have it).
3. **Storage:** each partition is a sequence of segment files on disk; reads and writes are sequential, and Kafka relies heavily on the OS page cache, which is why it is fast.
4. **Read path:** a consumer in a group is assigned partitions, fetches from the leader, processes and **commits** its offset (stored in the internal `__consumer_offsets` topic) so it can resume after a restart.
5. **Key guarantees and their reasons:**
   - ordering only within a partition;
   - parallelism = number of partitions;
   - durability from replication and `min.insync.replicas`;
   - records are retained by time or size, not deleted on consumption, so many consumers can read and replay.
6. **Failure handling:** if a leader broker dies, the controller elects a new leader from the ISR; consumers in a group rebalance if a member dies.

```text
Producers -> [ Broker 1: P0(L) P1(F) ]   Consumer group A: C1 <- P0, C2 <- P1
             [ Broker 2: P0(F) P1(L) ]   Consumer group B: C1 <- P0,P1
             [ Broker 3: ...         ]
             metadata: KRaft controller quorum
```

**Trade-offs and what can go wrong**
- More partitions give more parallelism but more files, replication traffic and failover time.
- Ordering across partitions is not guaranteed.
- `acks=1` is fast but can lose data if the leader dies before replication; `acks=all` with `min.insync.replicas=2` is safer but slower.
- Unbalanced keys create hot partitions; unbalanced leaders create hot brokers.

**How I'd monitor it**
Under-replicated and offline partitions, ISR shrink rate, controller status, broker request latency and thread idle percent, disk usage, consumer lag per group and partition.

**Follow-ups to expect**
- *Why is Kafka fast?* -> sequential disk writes, page cache, batching, zero-copy transfer, compression.
- *What is the role of ZooKeeper / KRaft?* -> cluster metadata, controller election; newer versions replace ZooKeeper with KRaft.
- *What happens if the leader of a partition dies?* -> a new leader is elected from the ISR.
- *How is a record deleted?* -> by retention (time/size) or log compaction, not by consumption.

**60-second answer**
Kafka is a cluster of brokers storing topics split into partitions, each an ordered append-only log. Partitions are replicated, with one leader serving reads and writes and followers in the in-sync set. Producers write to a partition's leader, consumers in a group each read their assigned partitions and commit offsets, and a controller (KRaft, formerly ZooKeeper) manages metadata and leader election. This gives scalability through partitions, ordering within a partition, durability through replication, and independent replayable reads for many consumer groups.

### Q2 [senior] We have 10 partitions and 10 consumers in one group, and 2 consumers crash. What happens in production?
tags: kafka, consumer-group, rebalance, failure, lag, duplicates, session-timeout, cooperative-sticky, basics

**Start here: the concepts**
- **Consumer group:** consumers sharing a `group.id`; each partition is assigned to exactly one consumer in the group.
- **Group coordinator:** a broker that tracks group members and assigns partitions.
- **Heartbeat and session timeout:** each consumer sends heartbeats; if none arrive within `session.timeout.ms` (or the consumer exceeds `max.poll.interval.ms` between polls) it is considered dead.
- **Rebalance:** reassigning partitions among the surviving members.
- **Committed offset:** the last position a consumer group confirmed; a new owner of a partition resumes from there.
- **Consumer lag:** how far behind the newest record the group is.

**The live scenario**
During a deployment, two of ten pods running the payment-events consumers are killed by an out-of-memory error. The dashboard shows lag climbing on two partitions for about 45 seconds, then recovering, while processing throughput settles about 20% lower. A few payment events are processed twice, and the downstream database rejects them on a unique key. Nothing was lost; this is exactly how Kafka is meant to behave.

**What the interviewer is really checking**
That you can walk through detection, rebalance, resumption from committed offsets, the duplicate and lag effects, and what you would do about capacity.

**How I answer it**
1. **Detection:** the coordinator notices missing heartbeats after `session.timeout.ms` (a crashed process stops sending them). The two members are removed from the group.
2. **Rebalance:** their two partitions must be reassigned. With the default eager protocols every consumer briefly stops consuming (a stop-the-world rebalance); with the **cooperative sticky assignor** only the orphaned partitions move and the other eight keep working.
3. **Assignment:** 10 partitions over 8 consumers means two consumers will each own 2 partitions and six own 1. The load is now uneven; those two consumers carry double.
4. **Resumption:** the new owners start from the **last committed offset**. Anything processed but not yet committed by the crashed consumers is processed again, so duplicates are possible: this is at-least-once delivery.
5. **Effect on production:**
   - lag spike during detection and rebalance on the affected partitions;
   - 80% of the original parallelism, so if the load needs more than that, lag keeps growing;
   - possible duplicates, which idempotent handlers absorb.
6. **What I do:** restart or autoscale replacements (new members trigger another rebalance, which is why static membership and cooperative rebalancing help), check why they crashed (memory, poison message, slow processing exceeding `max.poll.interval.ms`), watch lag until it drains, and verify no duplicate side effects.
7. **Design so this is routine:** idempotent consumers, commit after processing, cooperative sticky assignor, static membership (`group.instance.id`) with a sensible session timeout, headroom of 20-30% capacity, and alerts on lag and rebalance rate.

**Trade-offs and what can go wrong**
- A long `session.timeout.ms` avoids false failures but delays real failure detection; a short one causes needless rebalances.
- Without idempotency, duplicates cause double charges or double inserts.
- A poison message that crashes consumers repeatedly causes a crash loop and repeated rebalances; use a dead-letter topic.
- Scaling consumers beyond the partition count helps nothing: 10 partitions never need more than 10 active consumers.

**How I'd monitor it**
Lag per partition, rebalance count and duration, consumer-group member count, consumer pod restarts, processing error rate and duplicate-detected counters.

**Follow-ups to expect**
- *What if 5 of 10 crash?* -> five consumers each own 2 partitions; throughput halves, so you scale back up.
- *What if there were 12 consumers for 10 partitions?* -> 2 are idle standbys and immediately replace failures.
- *How do you avoid reprocessing?* -> you cannot fully; make handlers idempotent and commit after processing.
- *Do messages get lost?* -> no, they stay in the log and the new owner resumes from the committed offset.

**60-second answer**
Kafka detects the dead consumers by missed heartbeats, removes them from the group and rebalances: their two partitions are reassigned to surviving consumers, so two of them now own two partitions each. They resume from the last committed offset, so nothing is lost but some records can be processed twice, and lag spikes briefly. With cooperative sticky rebalancing only the orphaned partitions move. I then restore capacity by restarting or autoscaling, find why they crashed, and rely on idempotent handlers and lag alerts.

### Q3 [architect] A production application handles 1 million records and must scale to 10 million. What approach do you take with Kafka?
tags: kafka, scaling, capacity-planning, partitions, consumers, batching, throughput, backlog, load-testing, basics

**Start here: the concepts**
- **Throughput:** records (and MB) processed per second; the thing that must grow.
- **Capacity planning:** estimating how many partitions, consumers and brokers you need from a target rate.
- **Partition:** the unit of parallelism; consumers in a group are limited by it.
- **Batching:** moving many records per request and per database write.
- **Backlog:** records waiting unprocessed; lag.
- **Idempotent write:** an operation that has the same result if repeated, so retries are safe.

**The live scenario**
A nightly settlement job publishes 1 million transaction records and the consumers process them in 20 minutes. After a merger the volume is 10 million records for the same window. A simple 10x on the same design would need 200 minutes and overrun the morning cut-off. The team must decide whether this is a tuning problem or an architectural change, and prove it before the next run.

**What the interviewer is really checking**
That you first translate "10 million records" into a rate and a deadline, then scale each layer deliberately, and do not assume Kafka is the bottleneck.

**How I answer it**
1. **Clarify the numbers.** 10 million per day is about 115 records per second, trivial. 10 million within a 20-minute window is about 8,300 per second. 10 million per minute is 167,000 per second, a different league. Also ask for record size (10 million x 1 KB = 10 GB), latency deadline, ordering needs and whether it is bursty or steady.
2. **Find today's bottleneck.** Measure per-consumer throughput and where time goes: Kafka fetch, deserialisation, business logic, or the database write. In many systems the database insert is the limit, not Kafka.
3. **Partitions and consumers.** Required consumers = target rate / per-consumer rate; the topic needs at least that many partitions, with headroom. Plan the count now, because adding partitions later changes key routing.
4. **Producer side.** Batching (`linger.ms`, `batch.size`), compression, and a key that spreads data evenly.
5. **Consumer side.** Process in batches, use bulk database writes, keep handlers idempotent, tune `max.poll.records` and fetch sizes, commit after processing.
6. **Downstream.** Scale the database or API with the consumers: connection pools, bulk inserts, partitioned tables, read/write separation; otherwise lag just moves into the sink.
7. **Cluster.** Check broker disk (10 GB x replication factor 3 x retention), network, and partition spread; add brokers if needed.
8. **Operations.** Retry and dead-letter topics, backpressure, autoscaling consumers on lag (for example KEDA), and a way to backfill or replay.
9. **Prove it.** Load-test at 10x with realistic data and compare throughput, p99, lag drain time and resource use; run a game day for a consumer failure.

**Trade-offs and what can go wrong**
- Over-partitioning wastes resources; under-partitioning caps scale.
- Larger batches raise throughput and latency per record.
- Bulk writes complicate partial-failure handling.
- A single hot key ruins parallelism however many partitions exist.
- Replaying 10 million records after a bug needs idempotency and a controlled rate.

**How I'd monitor it**
Consumer lag and time-to-drain, per-stage latency (fetch, process, write), database load, broker disk and network, partition skew, and DLQ rate.

**Follow-ups to expect**
- *How many partitions?* -> target throughput divided by the lower of producer and consumer per-partition rates, plus headroom.
- *What if ordering matters?* -> key by the entity; ordering holds per partition only.
- *What if the database cannot keep up?* -> batch, add replicas or shard, or buffer with a queue and accept a longer drain time.
- *Can you scale Kafka without downtime?* -> add brokers and reassign partitions online; plan partition counts for new topics.

**60-second answer**
I first convert 10 million records into a rate and a deadline, and measure where the time goes today. Then I scale each layer: enough partitions and consumers for the target rate, producer batching and compression, consumer batching with bulk idempotent database writes, and capacity on the database and brokers so the bottleneck does not just move. I add retry and dead-letter topics and lag-based autoscaling, and I prove it with a 10x load test comparing throughput, p99 and lag drain time.
