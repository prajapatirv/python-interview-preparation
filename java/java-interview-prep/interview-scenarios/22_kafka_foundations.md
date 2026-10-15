---
id: foundations-kafka
title: Apache Kafka: from the basics (drafted)
stack: java
skill: kafka
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is Kafka and what problems does it solve?
tags: kafka, event-streaming, commit-log, topics, partitions, consumer-groups, basics

**Start here: the concepts**
- **Event**: a small record of something that happened, such as "order 123 was placed". It is a fact and is not changed afterwards.
- **Commit log**: a file you can only add to at the end, never edit in the middle. Each entry gets the next number. It is simple, fast and keeps order.
- **Kafka**: a system that stores commit logs across several servers (called **brokers**) so many applications can write and read events. It is distributed (many machines) and durable (data is written to disk and copied to other brokers).
- **Topic**: a named log for one kind of event, e.g. `orders`.
- **Partition**: a topic is split into partitions so the work can be spread over many machines. Order is guaranteed only inside one partition, not across the whole topic.
- **Offset**: the position number of an event inside a partition. A consumer remembers "I have read up to offset 500".
- **Producer / consumer**: a producer appends events. A consumer reads them. Each consumer reads at its own pace.
- **Consumer group**: several copies of one application share a topic's partitions, so each event is handled once per group.
- **Retention**: Kafka keeps events for a set time or size (e.g. 7 days), whether or not anyone has read them.
- **Replay**: because events stay, a consumer can move its offset back and read old events again.

**The live scenario**
An online shop's order service called email, inventory and analytics directly, one after another. On a sale day, orders rose from 200/s to 5,000/s (illustrative numbers). Analytics slowed down, so order requests waited on it and checkout latency went from 150 ms to 6 s. Some orders failed. The team moved to Kafka. The order service now writes one `OrderPlaced` event (about 2 ms) and each service reads it independently. When analytics was down for 40 minutes, nothing else was affected. It restarted and carried on from its saved offset. A bug fix later was handled by replaying the last day of events.

**What the interviewer is really checking**
That you can explain Kafka in simple words, name the problems it solves (decoupling, spikes, replay), and know how it differs from a classic queue.

**How I answer it**
1. **Say what it is**: a distributed, durable, partitioned commit log. This tells the listener it is storage first, not just a pipe.
2. **Explain the flow**: producers append events to topics. Topics are split into partitions for scale. Consumers read by offset. This shows you understand the parts.
3. **Make the key difference clear**: messages are **not deleted when read**. They are kept by time or size. Many queues remove a message once it is acknowledged, so a second reader or a replay is not possible. In Kafka, each group has its own offset, so many groups read the same data independently and can replay.
4. **Name the problems it solves**:
   - **Decoupling services**: the producer does not know or wait for consumers.
   - **Event streaming**: reacting to data as it arrives.
   - **Log and CDC pipelines**: moving logs, or database changes (change data capture), to other systems.
   - **Buffering spikes**: Kafka absorbs bursts and consumers catch up later.
5. **Mention the ordering rule**: order is guaranteed per partition only. Events with the same key go to the same partition.

**Trade-offs and what can go wrong**
- Kafka is not a simple "send and forget" tool. You must design for partitions, keys, duplicates (delivery is typically at-least-once unless you add idempotency or transactions) and consumer lag.
- Too few partitions limit parallelism. A busy key can create a "hot" partition.
- Retention costs disk. If a consumer is down longer than the retention period, it loses data.
- For a small system with a few messages, Kafka is too heavy. Use a simple queue.
- Kafka 4.x runs without ZooKeeper (KRaft only). Queue-like "share groups" are still preview, so do not call them standard.

**How I'd monitor it**
- **Consumer lag** per partition, in messages and in time.
- **Produce rate vs consume rate**.
- Rebalance rate.
- Under-replicated partitions and broker disk usage.
- Dead-letter topic rate for failed messages.

**Follow-ups to expect**
- *How is Kafka different from a queue like RabbitMQ?* -> Kafka keeps events after reading, supports replay and many independent groups. A classic queue usually deletes a message once it is acknowledged.
- *Does Kafka guarantee ordering?* -> Only inside a partition. Use the same key to keep related events in order.
- *If events are kept, what stops disk filling up?* -> Retention by time or size deletes old segments. Compaction keeps the latest value per key.

**60-second answer**
Kafka is a distributed, durable, partitioned commit log. Producers append events to topics. Each topic is split into partitions, and consumers read by offset at their own pace. Unlike a classic queue, Kafka does not delete a message when it is read. It keeps it for a set time or size, so consumers can replay and many groups can read the same data. This lets us decouple services, stream events, move logs and database changes, and absorb traffic spikes. Order is guaranteed only within a partition, so we use keys for related events. I would also watch consumer lag to make sure readers keep up.

### Q2 [fresher] Explain topic, partition, offset, broker, replica.
tags: kafka, topic, partition, offset, broker, replica, replication, basics

**Start here: the concepts**
- **Record (message):** one piece of data, such as "order 1001 was placed". Kafka stores records instead of passing them straight from sender to receiver, so the sender and receiver don't have to be online at the same time.
- **Topic:** a named stream of records, like a table or folder called `orders`. Producers write to it and consumers read from it.
- **Partition:** a topic is split into partitions. Each one is an ordered, append-only log: new records go at the end and are never edited in place. Partitions exist so work can be spread over many machines and many consumers, so a partition is the unit of parallelism. Ordering is guaranteed only inside one partition, not across the whole topic.
- **Offset:** the position number of a record inside one partition (0, 1, 2...). It is per partition, not global. Consumers use it as a bookmark ("I have read up to offset 41 in partition 3").
- **Broker:** one Kafka server. A cluster is several brokers, and together they hold all the partitions. In Kafka 4.x the cluster manages its own metadata (KRaft), with no ZooKeeper.
- **Replica:** a copy of a partition on another broker, kept so data survives a server failure. The **replication factor** is the total number of copies, leader included, and is usually 3.
- **Leader and followers:** for each partition, one replica is the leader. Producers write to it, and consumers normally read from it. Followers copy the leader. If the leader's broker dies, an up-to-date follower becomes the new leader.
- **ISR (in-sync replicas):** the replicas that are fully caught up with the leader. Only these are safe to promote.

**The live scenario**
An `orders` topic has 6 partitions and replication factor 3, spread over 3 brokers, handling about 2,000 orders/s. At 2 a.m. broker 2 loses its disk. Partitions led by broker 2 elect new leaders from their followers within seconds. Producers and consumers reconnect and carry on, and no orders are lost. Without replicas (factor 1), a third of the partitions would be unavailable and their data gone.

**What the interviewer is really checking**
Whether you understand how these terms fit together: partitions give scale, offsets give position, and replicas give safety. Also whether you know that ordering and offsets exist per partition only.

**How I answer it**
1. **Start with the topic:** it is a named stream, which gives the data a logical home. Everything else explains how that stream is stored.
2. **Split it into partitions:** one log on one machine would limit throughput. Many partitions let many brokers and consumers work in parallel.
3. **Explain offsets:** each record gets the next number in its partition. Consumers remember their offset, so they can resume after a restart or re-read old data.
4. **State the ordering rule:** records with the same key go to the same partition, so they stay in order. Order across partitions is not guaranteed.
5. **Place partitions on brokers:** the cluster spreads partitions across brokers so no single server holds everything.
6. **Add replicas:** each partition is copied to other brokers, with one leader and the rest followers. This is what makes a broker failure survivable.

```
kafka-topics.sh --create --topic orders --partitions 6 --replication-factor 3
```

**Trade-offs and what can go wrong**
- More partitions give more parallelism but add overhead, and you can add partitions later but not remove them. Adding them also changes which partition a key maps to.
- Replication factor 3 uses three times the disk and network.
- Replication factor 1 means no protection at all.
- A common mistake is assuming the whole topic is ordered.
- Another is assuming the offset is unique across the topic.
- Durability needs settings too: `acks=all` with `min.insync.replicas=2` means a write is only confirmed when at least two copies have it.

**How I'd monitor it**
- Under-replicated partitions (should be 0) and offline partitions (must be 0).
- ISR shrink/expand rate, which shows unstable followers.
- Disk usage per broker.
- Consumer lag per partition, meaning how far the log-end offset is ahead of the consumer's offset.

**Follow-ups to expect**
- *Is a topic ordered?* -> Only within a partition. Use a key, such as customer ID, to keep related records together.
- *What happens if the leader broker dies?* -> A follower from the ISR is elected leader, and clients refresh their metadata and continue.
- *Can two partitions have the same offset number?* -> Yes. Offsets are per partition, so offset 5 exists in every partition.

**60-second answer**
A topic is a named stream of records. It is split into partitions, which are ordered, append-only logs, so many consumers can read in parallel. Each record in a partition has an offset, its position number, which consumers use as a bookmark. Order is guaranteed only within a partition. A broker is a Kafka server, and a cluster spreads partitions across several brokers. Each partition is copied to other brokers as replicas, usually 3 in total. One is the leader that handles reads and writes, and the others follow it, so if a broker dies a follower takes over and no data is lost.

### Q3 [fresher] What is a consumer group?
tags: kafka, consumer-group, partitions, offsets, parallelism, rebalancing, basics

**Start here: the concepts**
- **Topic**: a named stream of messages, such as `orders`. Producers append to it and consumers read from it. Reading does not delete anything.
- **Partition**: a topic is split into several ordered logs called partitions. This lets many machines share the work. Order is guaranteed only inside one partition.
- **Consumer**: an application instance that reads messages from a topic.
- **Consumer group**: a set of consumers that share the same `group.id` and act as one logical application. Kafka splits the topic's partitions among them, so the work is divided instead of duplicated.
- **Offset**: the position of a message in a partition. Kafka stores, for each group and partition, how far that group has read. That is how a group resumes after a restart.
- **Rebalance**: Kafka reassigns partitions among the group's members when a consumer joins, leaves or crashes.

**The live scenario**
The `orders` topic has 6 partitions and receives about 3,000 msg/s. The payments service needs roughly 500 msg/s per consumer, so 6 consumers just keep up. During a sale, the team scales payments from 6 to 10 pods because lag is growing. Lag does not improve, and 4 pods show 0% CPU. Meanwhile the analytics team runs its own app with a different `group.id` and receives every order without affecting payments. The team learned two things: parallelism is capped by the partition count, and each group reads the whole topic independently.

**What the interviewer is really checking**
Whether you know that the partition, not the consumer, is the unit of parallelism, and that the group id decides whether consumers share messages or each get a full copy.

**How I answer it**
1. **Define it**: a consumer group is consumers sharing one `group.id`. The reason is to scale reading horizontally while processing each message once per group.
2. **Each partition goes to exactly one consumer in the group.** This keeps per-partition order, because two consumers never read the same partition at the same time.
3. **One consumer can own several partitions.** With 6 partitions and 3 consumers, each gets about 2. The reverse does not hold: a partition is never split between consumers.
4. **Parallelism is capped by the partition count.** With 6 partitions, a 7th consumer has nothing to read and sits idle. It is only useful as a standby.
5. **Different groups each get all messages** (pub/sub). Each group keeps its own offsets, so payments and analytics progress independently. Inside one group it behaves like a work queue.
6. **Membership changes trigger a rebalance.** If a consumer dies, its partitions move to the others. This is why consumers must commit offsets carefully, so work is not lost or repeated.

```properties
group.id=payments-service   # same value = share work; different value = own full copy
```

**Trade-offs and what can go wrong**
- Too few partitions caps your scaling. Adding partitions later changes which partition a key maps to, which can break per-key ordering for existing keys.
- Too many partitions adds broker overhead and slower rebalances.
- Reusing a `group.id` by mistake in two different apps makes them steal messages from each other.
- Rebalances pause consumption. Newer Kafka versions (the KIP-848 protocol, GA in Kafka 4.x) make this less disruptive.
- Idle consumers cost money and give no speedup.

**How I'd monitor it**
- Per-partition lag, in messages and in time, using `kafka-consumer-groups.sh --describe --group payments-service`.
- Consume rate compared with produce rate.
- Number of active consumers compared with partitions, to spot idle ones.
- Rebalance frequency. Frequent rebalances point to unstable consumers.

**Follow-ups to expect**
- *What happens if a consumer crashes?* -> The group rebalances and its partitions are given to the remaining consumers. They resume from the last committed offset.
- *Can two groups read the same topic?* -> Yes. Each group has its own offsets and gets every message.
- *How do I scale beyond the partition count?* -> Add partitions, or make processing faster per consumer. Adding more consumers alone will not help.

**60-second answer**
A consumer group is a set of consumers with the same `group.id` that share the work of reading a topic. Kafka gives each partition to exactly one consumer in the group, which keeps order within the partition. One consumer can read several partitions, but a partition is never split. So the number of partitions is the ceiling on parallelism, and extra consumers just sit idle. Different groups each receive every message, because each keeps its own offsets. That is how payments and analytics can both read `orders` independently. If a consumer dies, Kafka rebalances and moves its partitions to the others.

### Q4 [mid] How does Kafka guarantee ordering?
tags: kafka, partitions, ordering, message-key, producer, consumer-group, basics

**Start here: the concepts**
- **Topic:** a named stream of records (for example `orders`). Think of it as a category that producers write to and consumers read from.
- **Partition:** a topic is split into several partitions. Each partition is an append-only log, and every record gets a position number in it called an **offset**. Partitions exist so a topic can be spread over many brokers and read by many consumers in parallel.
- **Record key:** an optional value on each record, such as `orderId` or `customerId`. It tells Kafka which records belong together.
- **Key-to-partition mapping:** the default producer hashes the key and takes the result modulo the number of partitions. The same key therefore always lands in the same partition, as long as the partition count stays the same.
- **Consumer group:** consumers that share the work of a topic. Each partition is read by exactly one consumer in the group at a time.
- **Ordering:** records are read in the same order they were written to that log.

**The live scenario**
An e-commerce `orders` topic has 12 partitions and carries about 5,000 msg/s, keyed by `orderId`. To handle growth, the team raises it to 24 partitions during the day. Orders already in progress now hash to different partitions for their later events. For example, `OrderCancelled` is read by a different consumer than the earlier `OrderPaid`, and it is sometimes processed first. In 10 minutes, about 40 orders ship after being cancelled, and support tickets follow.

**What the interviewer is really checking**
Whether you know that ordering is per partition and not per topic, and that you can connect this to keys, partition count changes, and producer and consumer behaviour.

**How I answer it**
1. **Ordering is guaranteed only within one partition.** Records are appended to the log in arrival order and read back in offset order. Two different partitions are independent logs, so there is no global order across them.
2. **Use a key to keep related events together.** The same key always goes to the same partition, so all events for one order or customer stay in order. Records with a null key are spread across partitions and have no ordering relationship.
3. **Don't let producer retries reorder records.** If batch 1 fails and batch 2 succeeds, a retry of batch 1 can land after batch 2. Setting `enable.idempotence=true` prevents this, with `acks=all` and up to 5 in-flight requests. It is the default in clients since Kafka 3.0.
   ```
   enable.idempotence=true
   acks=all
   ```
4. **Keep order on the consumer side too.** Within a group, one consumer reads a partition sequentially. If you hand records to a thread pool, they can finish out of order. Process by key sequentially, or keep one worker per partition.
5. **Never change the partition count on a topic that depends on key ordering.** The modulo changes, so existing keys map to new partitions (the stored answer's last point). Old and new events for the same key then sit in different logs. Plan the partition count up front, or create a new topic and migrate with a drain step.

**Trade-offs and what can go wrong**
- Strict ordering for a key limits that key's throughput to one partition and one consumer.
- A very busy key creates a hot partition and growing lag on that partition only.
- Need total order across the whole topic? Use one partition, which caps throughput and parallelism. Most systems only need per-entity order.
- Retries without idempotence, and multi-threaded consumers, are the most common ways to lose order by accident.
- A consumer rebalance can move a partition to another consumer. This is safe for order only if offsets were committed correctly, and otherwise you may see duplicates.

**How I'd monitor it**
- Per-partition consumer lag, plus message distribution per partition to spot key skew.
- Include a version or sequence number in each event, and have the consumer log or count any event that arrives out of sequence.
- Search the logs (for example in Splunk) by `orderId` and check that partition and offset are consistent for that key.
- Alert on any partition-count change on keyed topics (a change-control check).
- Watch producer retry and error rates.

**Follow-ups to expect**
- *How do you get ordering across the whole topic?* -> Use a single partition. That limits throughput to one consumer, so it is rarely acceptable.
- *Can you add partitions safely?* -> You can add them, but keys remap. Drain the topic first, or create a new topic and migrate.
- *Do retries break order?* -> They can, unless the producer has idempotence enabled.

**60-second answer**
Kafka guarantees order only within a single partition, not across a topic. A partition is an append-only log, and consumers read it in offset order. To keep related events together I give them the same key, such as the order ID. The producer hashes the key to pick the partition, so all events for that order stay in one partition and in order. I also enable idempotence so retries don't reorder records, and I process each partition sequentially on the consumer side. I avoid changing the partition count on keyed topics, because it changes the key-to-partition mapping and breaks order for existing keys. If I truly needed global ordering I would use one partition, and I would accept the throughput limit.

### Q5 [mid] Explain delivery semantics: at-most-once, at-least-once, exactly-once.
tags: kafka, delivery-semantics, offsets, idempotency, exactly-once, transactions, basics

**Start here: the concepts**
- **Offset**: the position number of a message inside a partition. A consumer's *committed offset* is its saved bookmark ("I have handled everything before this"). After a crash or restart, it resumes from that bookmark.
- **Commit**: saving the bookmark to Kafka. *When* you save it relative to doing the work decides what happens on a crash.
- **Delivery semantics**: the guarantee about how many times a message's effect happens: zero or one, one or more, or exactly one.
- **Duplicate**: the same message processed twice. It happens when the work was done but the bookmark was not saved before a crash, or when a producer retries a send whose acknowledgement was lost.
- **Idempotent**: doing an operation twice has the same result as doing it once. Setting `status=PAID` is idempotent. Adding 100 to a balance is not.
- **Idempotent producer**: the broker recognises and discards a retried send of the same message from the same producer within a partition. It uses a producer id plus sequence numbers. It is on by default since Kafka 3.0.
- **Transaction**: a group of writes (output messages plus the input offset commit) that become visible all together or not at all.
- **`read_committed`**: a consumer setting (`isolation.level`) that hides messages from aborted or still-open transactions.

**The live scenario**
A payments service consumes about 2,000 msg/s and writes each charge to a database. During a deploy, a consumer was killed after processing but before committing. On restart it re-read about 500 messages and charged some customers twice. The team was using at-least-once, which is correct, but the DB insert was not idempotent. The fix was a unique `eventId` column and an upsert, so replays became harmless.

**What the interviewer is really checking**
Whether you link the *commit order* to the guarantee, and whether you know that "exactly-once" has limits: it holds inside Kafka, not automatically for external systems.

**How I answer it**
1. **At-most-once**: commit the offset *before* processing. If the app crashes mid-work, the bookmark has already moved, so the message is never retried and is lost. It is acceptable only for data you can lose, such as sampled metrics. Note that auto-commit can behave this way by accident.
2. **At-least-once**: process *first*, commit *after*. A crash between the two means the message is replayed, so duplicates are possible but loss is not. This is the practical default because losing money events is usually worse than seeing them twice. Producer-side it needs `acks=all`.
3. **Exactly-once (EOS)**: for a read-process-write pipeline *inside Kafka*, combine the idempotent producer with transactions. The output messages and the input offset commit go in one transaction. Downstream consumers use `read_committed`:
```
transactional.id=orders-svc-1   # producer
isolation.level=read_committed  # consumer
```
Reason: output and bookmark succeed or fail together, so a replay cannot produce a visible duplicate.
4. **External sink (DB, REST call)**: a Kafka transaction cannot roll back a database write. So keep at-least-once and make the write idempotent with a unique event id or an upsert. This is often called "effectively once".

**Trade-offs and what can go wrong**
- EOS adds latency and complexity: transaction coordination, a stable `transactional.id`, and aborted-transaction handling. Use it only when Kafka-to-Kafka duplicates are truly harmful.
- Forgetting `read_committed` means consumers see aborted data, which silently breaks EOS.
- Claiming "exactly-once" for a DB or email sink is the classic mistake. The side effect can still happen twice.
- Idempotency keys need a stable id from the producer, not one generated at consume time. Otherwise each replay looks like a new event.
- Slow processing past `max.poll.interval.ms` triggers a rebalance, which causes replays even without a crash.

**How I'd monitor it**
- Consumer lag per partition (messages and time) and rebalance rate, since rebalances drive replays.
- A counter of duplicate-key rejections or upsert conflicts. A spike means more redelivery.
- Producer retry rate and transaction abort rate.
- Dead-letter topic rate.
- A Splunk search that groups by `eventId` and flags counts above 1 in the logs.

**Follow-ups to expect**
- *Does Kafka exactly-once work with my database?* -> No. EOS covers Kafka-to-Kafka only. For a DB, use at-least-once plus an idempotent write, or the outbox pattern.
- *What does `enable.idempotence` actually do?* -> The broker de-duplicates producer retries per partition using producer id and sequence numbers. It stops duplicates from retries, not from consumer replays.
- *Why is at-least-once the default choice?* -> A duplicate can be neutralised with idempotency, but a lost message cannot be recovered.

**60-second answer**
Delivery semantics describe how many times a message's effect happens. At-most-once commits the offset before processing, so a crash loses the message. At-least-once processes first and commits after, so a crash causes a replay and possible duplicates. It is the usual default because loss is worse. Exactly-once uses the idempotent producer plus transactions, which commit output and input offsets together, with `read_committed` consumers. It works inside Kafka only. For a database or other external system, I keep at-least-once and make the write idempotent with a unique event id or an upsert. I watch lag, rebalances and duplicate-key counts to confirm it holds.

### Q6 [mid] What producer settings give "don't lose messages"?
tags: kafka, producer, acks, idempotence, min-insync-replicas, durability, basics

**Start here: the concepts**
- **Broker, topic, partition:** A broker is a Kafka server. A topic is a named stream of messages, split into partitions, and each partition is an ordered log.
- **Replication factor (RF):** Each partition is copied to several brokers. With RF=3 there is one **leader**, which handles reads and writes, and two **followers**, which copy from it. Copies exist so one broker dying doesn't lose data.
- **ISR (in-sync replicas):** The replicas, leader included, that are currently caught up. Only an ISR member can safely become the new leader.
- **`acks`:** How many confirmations the producer waits for before treating a send as successful. `0` means none, `1` means the leader only, and `all` means every replica currently in the ISR.
- **`min.insync.replicas`:** A topic/broker setting. With `acks=all`, the write is rejected unless at least this many replicas are in the ISR. Without it, "all" could mean just the leader.
- **Retries and `delivery.timeout.ms`:** The producer resends after temporary failures. `delivery.timeout.ms` is the total time budget (default 2 minutes) before it gives up and reports an error.
- **Idempotence:** If a retry sends a message the broker already stored (the ack was lost), the broker detects and discards the duplicate. It does this using a producer ID and per-partition sequence numbers.
- **Callback/future:** `send()` is asynchronous. The result, success or failure, arrives later through a callback or `Future`.

**The live scenario**
A payments service publishes about 5,000 events/s. During a rolling broker restart, the producer used `acks=1`. A leader acknowledged a batch and died before followers copied it. The new leader never had those messages, so roughly 300 events vanished. Nobody noticed until a reconciliation job the next day showed that payments and ledger counts didn't match. The fix was a handful of config lines and a callback.

**What the interviewer is really checking**
Whether you know that durability depends on several settings working together (producer, topic, and your own error handling), not on `acks=all` alone, and whether you separate durability settings from throughput tuning.

**How I answer it**
1. **`acks=all`.** The leader confirms only after every in-sync replica has the message. A leader crash then can't lose acknowledged data.
2. **`min.insync.replicas=2` with RF=3.** This makes "all" meaningful. Writes need at least two copies, and one broker can fail without stopping writes or losing data. With `min.insync.replicas=1`, "all" can shrink to just the leader.
3. **`enable.idempotence=true`.** Retries are needed for safety but can create duplicates. Idempotence removes them and keeps ordering within a partition (it requires `max.in.flight.requests.per.connection` ≤ 5). In Kafka 3.0+ it's on by default, but I set it explicitly so intent is visible.
4. **Retries high, `delivery.timeout.ms` bounded.** Retries ride out leader elections, and the timeout stops the producer from retrying forever. It should be longer than a typical failover.
5. **Always handle send failure.** If the timeout expires, the producer reports an error only through the callback/future. Ignoring it silently drops the message. I log, retry, or park the message in an outbox or DLQ.
6. **Flush/close on shutdown.** Buffered, unsent messages are lost if the process exits without `flush()` or `close()`.

```properties
acks=all
enable.idempotence=true
delivery.timeout.ms=120000
# topic: replication.factor=3, min.insync.replicas=2
```

`linger.ms`, `batch.size` and `compression.type` (lz4/zstd) are throughput tuning, not durability. Larger batches and compression raise throughput at the cost of a little latency.

**Trade-offs and what can go wrong**
- `acks=all` adds latency because it waits for followers.
- With `min.insync.replicas=2`, if two of three brokers are down, producers get `NotEnoughReplicasException`. You chose consistency over availability.
- Idempotence only dedupes retries inside one producer session. It is not end-to-end exactly-once. That needs transactions plus idempotent consumers.
- Keep `unclean.leader.election.enable=false` (the default), or an out-of-sync replica can become leader and lose data.
- Fire-and-forget `send()` makes every other setting pointless.

**How I'd monitor it**
- Producer metrics: `record-error-rate`, `record-retry-rate`, `request-latency-avg`.
- Broker metrics: `UnderReplicatedPartitions`, `UnderMinIsrPartitionCount`, `OfflinePartitionsCount`.
- In Splunk, search for `NotEnoughReplicasException`, `TimeoutException` and "Failed to send", and alert on spikes.
- Reconcile produced counts against consumed or stored counts per hour.

**Follow-ups to expect**
- *Why is `acks=all` alone not enough?* -> If the ISR shrinks to the leader, "all" means one copy. `min.insync.replicas=2` enforces at least two.
- *Does idempotence give exactly-once?* -> No. It dedupes producer retries per partition within a session. End-to-end needs transactions and idempotent consumers.
- *What happens if the send callback reports an error?* -> The message is not safely stored. I retry, write it to an outbox or DLQ, and alert, never ignore it.

**60-second answer**
To avoid losing messages, I set `acks=all` so every in-sync replica confirms the write. On the topic I use replication factor 3 and `min.insync.replicas=2`, so "all" always means at least two copies. I turn on `enable.idempotence=true` so retries don't create duplicates or break ordering. I keep retries high but bounded by `delivery.timeout.ms`. I always check the send callback, because that is the only place a failed send shows up. Settings like `linger.ms`, `batch.size` and compression are about throughput, not safety. I watch under-min-ISR partitions and producer error rates to confirm it holds.

### Q7 [mid] Why disable auto-commit and how do you commit offsets?
tags: kafka, offsets, auto-commit, consumer-groups, ack-mode, spring-kafka, basics

**Start here: the concepts**
- **Offset:** the position number of a message inside a partition (0, 1, 2...). It is how Kafka tracks "where I am" in the log.
- **Committed offset:** the offset a consumer group saves in Kafka (in the internal `__consumer_offsets` topic) as "processed up to here". After a crash or restart, a consumer resumes from this saved position. The commit is the only progress record Kafka keeps.
- **Auto-commit:** the default client setting `enable.auto.commit=true`. The client commits the offsets from the previous `poll()` every `auto.commit.interval.ms` (default 5 seconds). The check runs inside the next `poll()` call, not on a background timer.
- **Manual commit:** your code decides when the commit happens, normally after the work succeeded.
- **Delivery guarantees:**
  - *At-most-once:* a message may be lost, but is never repeated.
  - *At-least-once:* a message is never lost, but may be repeated.
  - Committing after processing gives at-least-once.
- **Spring Kafka AckMode:** controls when the listener container commits. `RECORD` commits after each record. `BATCH` (the default) commits after each poll's records are processed. `MANUAL` means your code calls `acknowledge()`.

**The live scenario**
An orders service reads a 12-partition topic at about 2,000 msg/s. To go faster, a developer handed each record to a thread pool, but left auto-commit on. A pod was OOM-killed mid-shift. The poll loop had already committed offsets for records still waiting in the pool queue, so about 3,400 orders were never written to the database. Consumer lag showed zero, so no alert fired. Finance found the gap the next day.

**What the interviewer is really checking**
Do you understand that the offset commit is a promise that the work is done, and that you must tie it to real completion? They also want to see that you know commit timing decides between loss and duplicates.

**How I answer it**
1. **Set `enable.auto.commit=false`.** Auto-commit acts on the clock and on `poll()`, not on whether your work finished. If processing is asynchronous, or errors are swallowed, offsets get committed for records that were never handled, so they are silently lost on a crash.
2. **Commit only after success.** In Spring Kafka, choose the AckMode: `RECORD` (safest, most commits), `BATCH` (one commit per poll, good default) or `MANUAL` (you call `acknowledge()` once the database write is done).
   ```java
   props.put("enable.auto.commit", false);
   factory.getContainerProperties().setAckMode(AckMode.MANUAL);
   ```
   (Spring Kafka's container already sets auto-commit off by default, but state it explicitly.)
3. **Commit per batch, not per record.** Each commit is a network write to the broker. At 2,000 msg/s, committing every record adds needless load, while one commit per poll (`max.poll.records`, e.g. 500) costs far less. The price is that a crash replays up to one batch.
4. **Make the handler idempotent.** If the app crashes after the database write but before the commit, the records are redelivered. Use a unique key or upsert so that processing twice is harmless.
5. **For atomicity, be precise.** A Kafka offset cannot join a normal database transaction. You have two options. Either store the offset in the same database transaction as the result and `seek()` to it on startup. Or use Kafka transactions (`sendOffsetsToTransaction`), which work for Kafka-to-Kafka flows.

**Trade-offs and what can go wrong**
- Manual commit moves the risk from loss to duplicates, so idempotency is required.
- Committing before processing is just auto-commit's loss problem done by hand.
- A slow batch longer than `max.poll.interval.ms` causes a rebalance, and uncommitted records are processed again.
- With a thread pool, commit only offsets that are fully done, and never commit past a gap.
- Auto-commit with strictly synchronous processing is effectively at-least-once, but it is fragile and hides your intent.
- A poison message that never succeeds will block commits unless you add a retry and dead-letter strategy (`DefaultErrorHandler` with `DeadLetterPublishingRecoverer`).

**How I'd monitor it**
- Per-partition consumer lag, in messages and in time.
- Commit rate and commit failures.
- Rebalance rate.
- Redelivery and duplicate counts from the idempotency check.
- DLT (dead-letter topic) rate.
- Reconciliation of records consumed against rows written. Lag alone would not have caught the scenario above.

**Follow-ups to expect**
- *What is the difference between `commitSync` and `commitAsync`?* -> `commitSync` blocks and retries, so it is safer. `commitAsync` is faster but does not retry. A common pattern is async during normal running and one sync commit on shutdown or rebalance.
- *What does `auto.offset.reset` do?* -> It applies only when the group has no valid committed offset: `earliest` reads from the start, `latest` reads only new messages.
- *How do you get exactly-once?* -> For Kafka-to-Kafka, use an idempotent producer plus transactions with `read_committed`. For external systems, use at-least-once delivery plus idempotent writes.

**60-second answer**
Auto-commit saves offsets on a schedule, checked during `poll()`, not when my work is actually finished. If processing is asynchronous or fails quietly, the offset moves past records I never handled, and a crash loses them without any alert. So I turn it off and commit after the work succeeds, using Spring Kafka's `RECORD`, `BATCH` or `MANUAL` ack mode. I usually commit per batch to avoid the cost of committing every record. That gives at-least-once delivery, so a crash causes duplicates, and I make the handler idempotent to cope. I watch per-partition lag and rebalances, and I reconcile consumed counts against stored results.

### Q8 [mid] What is a rebalance and why does it hurt?
tags: kafka, rebalance, consumer-group, partitions, offsets, session-timeout, basics

**Start here: the concepts**
- **Partition:** a topic is split into partitions, and each partition is an ordered log. Partitions let many consumers read one topic in parallel.
- **Consumer group:** a set of consumers sharing one `group.id`. Kafka gives each partition to exactly one consumer in the group, so the work is split without two consumers handling the same message.
- **Offset:** a message's position in a partition. A consumer commits its offset to record how far it has read, so a replacement consumer knows where to resume.
- **Rebalance:** the group redistributing partitions among its members. It exists so that every partition always has an owner, even as consumers come and go.
- **Heartbeat and `session.timeout.ms`:** consumers send heartbeats in the background. If none arrive within `session.timeout.ms`, the broker treats the consumer as dead.
- **`max.poll.interval.ms`:** the longest allowed gap between two `poll()` calls. A consumer that is alive but stuck processing a batch is also removed after this gap.
- **Assignor:** the algorithm that decides which consumer gets which partition.

**The live scenario**
An orders topic has 48 partitions and 12 consumer pods, receiving 20,000 msg/s. During a rolling deployment, each pod restart caused two rebalances (one on leaving, one on joining). With the default eager protocol, every pod stopped and waited about 10 seconds each time. Lag peaked near 1.5 million messages, about 75 seconds of traffic. Because offsets were only committed periodically, some messages were reprocessed afterwards, and the downstream system saw duplicates.

**What the interviewer is really checking**
Whether you know that a rebalance is normal but costly, and can name its triggers, explain the damage (pause, duplicates, lag) and list the concrete fixes.

**How I answer it**
1. **Define it:** a rebalance reassigns partitions when a consumer joins, leaves, crashes or times out, or when partitions are added. Reassignment is needed so no partition is left unread.
2. **Name the triggers:**
   - Slow processing that exceeds `max.poll.interval.ms`.
   - Missed heartbeats beyond `session.timeout.ms`, for example from a long GC pause or a network problem.
   - Deployments and autoscaling, which cause repeated joins and leaves.
3. **Explain why it hurts.** With the classic eager protocol, all consumers give up all their partitions and wait for a new assignment, so the whole group pauses. Uncommitted work is re-read by the new owner, which creates duplicates. Lag grows during the pause, and in-memory state or caches tied to a partition are lost.
4. **Reduce the impact:**
   - Use the **cooperative sticky assignor**, which moves only the partitions that need to move, in steps. The rest keep running.
   - Use **static membership** with `group.instance.id`. A pod that restarts within `session.timeout.ms` gets its old partitions back with no rebalance. So set that timeout longer than a typical restart.
   - Lower `max.poll.records` and keep handlers fast so each `poll()` finishes in time. Move slow calls out of the poll loop.
5. **Mention the newer option:** the KIP-848 consumer protocol (GA in Kafka 4.0) moves assignment to the broker. There is no group-wide stop-the-world step, so it is much smoother. Check your client version and enable it with `group.protocol=consumer`. Some settings, such as the session timeout, then become broker-side.
```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
group.instance.id=orders-pod-7
```
6. **Make processing safe anyway:** rebalances will happen, so handlers should be idempotent (safe to run twice).

**Trade-offs and what can go wrong**
- Static membership delays failure detection. A truly dead pod keeps its partitions until the session timeout expires.
- Setting `max.poll.interval.ms` very high hides slow handlers instead of fixing them.
- Too small a `session.timeout.ms` causes false "dead" verdicts.
- Cooperative rebalancing needs all members to use it, so mixed-assignor groups need a careful migration.
- Committing an offset after a rebalance has taken the partition away fails (`CommitFailedException`). Expect duplicates.

**How I'd monitor it**
- Client metrics: `rebalance-total`, `rebalance-rate-per-hour`, `rebalance-latency-avg`, `last-rebalance-seconds-ago`.
- Per-partition lag, in messages and in seconds, as well as consume rate against produce rate.
- In Splunk, search consumer logs for "Revoking previously assigned partitions", "Request joining group due to" and "consumer poll timeout has expired". Chart them by pod to correlate with deployments.
- Alert when rebalances happen outside deploy windows.

**Follow-ups to expect**
- *Eager vs cooperative rebalancing?* -> Eager revokes everything and stops the group. Cooperative revokes only the partitions that move, so most consumers keep working.
- *How do you tell whether a slow handler or a heartbeat problem caused it?* -> Read the log reason. "Poll timeout expired" means processing is too slow. A session timeout points to GC, network or a dead process.
- *Does static membership remove all rebalances?* -> No. It avoids them for quick restarts only. A new member or a timeout still triggers one.

**60-second answer**
A rebalance is Kafka reassigning partitions among the consumers in a group. It happens when a consumer joins, leaves, crashes, stops sending heartbeats within `session.timeout.ms`, or takes longer than `max.poll.interval.ms` between polls. It hurts because with the classic protocol the whole group pauses, lag builds up, and uncommitted messages get reprocessed, so duplicates appear. To reduce it, I use the cooperative sticky assignor, static membership with `group.instance.id` so quick restarts don't trigger one, and a smaller `max.poll.records` with fast handlers. On Kafka 4.0 I can also use the KIP-848 protocol, where the broker does the assignment and it is much smoother. I keep handlers idempotent and watch rebalance rate and lag per partition.

### Q9 [mid] How do you handle a poison message and retries?
tags: kafka, poison-message, retries, dead-letter-topic, spring-kafka, error-handling, backoff, basics

**Start here: the concepts**
- **Poison message:** a record that fails every time you process it, such as malformed JSON, a missing mandatory field, or a schema mismatch. Retrying never fixes it.
- **Offset and commit:** a consumer tracks its position in a partition with an offset. It only moves forward after it commits. If a record keeps failing and you never move past it, that partition is stuck.
- **Retryable vs non-retryable error:** a retryable error is temporary (database down, downstream timeout), so trying again later can work. A non-retryable error is permanent (bad data), so retrying only wastes time.
- **Backoff:** waiting between retries, usually longer each time (exponential), so you don't hammer a struggling dependency.
- **Dead Letter Topic (DLT):** a separate Kafka topic where you park records you gave up on. This keeps the main flow moving and lets you inspect and replay the records later.
- **Poll loop:** the consumer repeatedly calls `poll()`. If it doesn't call it again within `max.poll.interval.ms` (default 5 minutes), the broker assumes the consumer is dead and triggers a rebalance, which moves its partitions to other consumers.
- **Blocking vs non-blocking retry:** blocking retry pauses the partition and retries in place. Non-blocking retry moves the failed record to a retry topic so later records keep flowing.

**The live scenario**
An orders service consumes 2,000 msg/s from `orders` (12 partitions). One producer deploys a bug and sends a record with a null `customerId`. The consumer throws on it, retries forever, and never commits. Partition 7 stops, and its lag grows by about 170 msg/s (2,000 ÷ 12). Within 10 minutes about 100,000 orders are delayed and customers are calling support. A separate day, the database is down for 2 minutes and every record fails. If those records went to the DLT, thousands of good orders would need manual replay.

**What the interviewer is really checking**
Whether you separate "bad data" from "bad moment", protect the rest of the partition from one bad record, and know the ordering and poll-loop costs of each retry style.

**How I answer it**
1. **Classify errors first.** Permanent failures (validation, bad schema) go straight to the DLT with no retries, because retrying is pointless. Temporary failures (DB down) get bounded retries with backoff, so a short outage heals itself without a human.
2. **Handle deserialization failures explicitly.** If a record can't even be deserialized, the failure happens before your listener runs. Wrap the deserializer with Spring's `ErrorHandlingDeserializer` so the error reaches the error handler instead of looping forever at `poll()`.
3. **Use `DefaultErrorHandler` in Spring Kafka.** Give it an `ExponentialBackOff` and a `DeadLetterPublishingRecoverer`. After retries are exhausted, the recoverer publishes the record to the DLT, the offset moves on, and the partition continues.
   ```java
   var backoff = new ExponentialBackOffWithMaxRetries(4); // illustrative
   new DefaultErrorHandler(new DeadLetterPublishingRecoverer(template), backoff);
   ```
4. **Choose blocking or non-blocking retry deliberately.** The `DefaultErrorHandler` backoff blocks the consumer thread, which preserves order per key but holds up that partition. `@RetryableTopic` sends failures to retry topics with delays, so the main topic keeps flowing, but a retried record can be overtaken by a later record with the same key and **strict per-key ordering is lost**.
5. **Never block the poll loop with a long `sleep`.** If total backoff nears `max.poll.interval.ms`, the broker evicts the consumer and causes a rebalance, which can create duplicates. Keep blocking retries short (seconds) and use retry topics for longer delays.

**Trade-offs and what can go wrong**
- Blocking retries keep order but stall the partition. Retry topics keep throughput but break per-key order.
- Retried processing can run twice, so the consumer must be idempotent (a repeat has no extra effect).
- `DeadLetterPublishingRecoverer` by default sends to the same partition number in `<topic>.DLT`, so the DLT needs enough partitions (or a custom resolver).
- A DLT nobody watches is a silent data-loss bin. Keep the original headers and exception details so records can be diagnosed and replayed.
- Retrying a permanent error wastes capacity. Sending a temporary error straight to the DLT creates manual work.

**How I'd monitor it**
- Per-partition consumer lag, in messages and in time. One partition rising while others are flat points to a stuck poison record.
- DLT message rate, with an alert on any sustained non-zero rate.
- Retry-topic depth and the ratio of retries to successes.
- Rebalance rate, to catch backoff that exceeds `max.poll.interval.ms`.
- Splunk search on the listener's error logs, grouped by exception class and topic-partition-offset.

**Follow-ups to expect**
- *How do you replay DLT messages?* -> Fix the cause first, then run a controlled consumer or tool that republishes to the original topic at a safe rate. The consumer must be idempotent, because duplicates are possible.
- *Why not retry forever?* -> The partition stalls and lag grows. Bound the retries and park the record in the DLT.
- *How do you keep ordering with retries?* -> Use blocking retries on the same partition, or accept the loss of per-key order with `@RetryableTopic`.

**60-second answer**
First I decide whether the error is permanent or temporary. Permanent ones, like bad data, go straight to a Dead Letter Topic. Temporary ones, like a database outage, get a limited number of retries with exponential backoff. In Spring Kafka I use `DefaultErrorHandler` with `ExponentialBackOff` and `DeadLetterPublishingRecoverer`, plus `ErrorHandlingDeserializer` so unreadable records don't loop forever. For longer delays I use `@RetryableTopic`, which doesn't block the partition, but the cost is that strict order per key is lost. I never sleep for long in the poll loop, because exceeding `max.poll.interval.ms` triggers a rebalance. I watch per-partition lag and DLT rate, and I make the consumer idempotent because retries can cause duplicates.

### Q10 [mid] How do you make a consumer idempotent?
tags: kafka, idempotency, consumer, at-least-once, duplicates, database, basics

**Start here: the concepts**
- **Consumer**: a program that reads messages from a Kafka topic and acts on them, for example by charging a card or updating a row.
- **Offset**: the position of a message in a partition. The consumer commits its offset to say "I have finished up to here." After a crash, it restarts from the last committed offset.
- **At-least-once delivery**: if the consumer processes a message but crashes before committing the offset, Kafka sends that message again. Nothing is lost, but duplicates can happen.
- **Rebalance**: Kafka moves partitions between consumers when one joins, leaves, or is too slow. Messages processed but not yet committed get redelivered to the new owner.
- **Idempotent**: doing the operation twice has the same final result as doing it once. Setting a balance to 90 is idempotent. "Subtract 10" is not.
- **Event id**: a unique id for each business event, set by the producer, such as `paymentId`. It lets the consumer recognise "I have seen this one."
- **Upsert**: a database write that inserts a row or does nothing or updates if it already exists, in one atomic step.

**The live scenario**
A payments service handles about 2,000 events/s. During a deploy, a rebalance happens and about 5,000 events that were processed but not yet committed are redelivered. Without protection, around 300 customers get a second "payment captured" email and a duplicate ledger entry. Support tickets arrive within the hour. With a dedupe check, the same replay produces zero visible effects, and 5,000 "duplicate skipped" log lines.

**What the interviewer is really checking**
That you accept duplicates as normal in Kafka and design the handler to survive them, rather than hoping the broker prevents them. A strong answer also knows where the guarantee ends.

**How I answer it**
1. **Assume every message can arrive more than once.** Commit offsets after processing (at-least-once), because the other order can lose messages. Rebalances and retries make redelivery routine, so the handler must tolerate it.
2. **Pick a stable unique key.** Use a business event id from the producer. It is the same on every redelivery, so duplicates are detectable.
3. **Record the id in the same database transaction as the side effect.** If the id insert and the business write commit together, a crash leaves both or neither. Recording the id separately can leave a gap where the work happens twice or never.
   ```sql
   INSERT INTO processed_event(event_id) VALUES (?) ON CONFLICT DO NOTHING; -- Postgres
   ```
   If 0 rows were inserted, it is a duplicate, so skip. Oracle uses `MERGE`.
4. **Prefer naturally idempotent writes.** Use upserts and "set to value" instead of "add to value."
5. **Make state changes conditional on a version.** For example, `UPDATE ... WHERE id=? AND version=?`. A replayed or out-of-order event matches no row and does nothing.
6. **For external side effects** (payment gateway, email), the DB transaction cannot cover them. Pass the event id as the provider's idempotency key where supported.

**Trade-offs and what can go wrong**
- An extra write and index lookup on every message adds latency. Measure it.
- The processed-id table grows forever. Purge ids older than the longest realistic redelivery window, such as topic retention.
- Checking an in-memory cache only is not enough. It is lost on restart and not shared across consumers.
- Kafka's idempotent producer (`enable.idempotence`) and transactions do not fix this for external systems. They only cover producer retries and Kafka-to-Kafka flows.
- Using a random id generated by the consumer defeats the purpose, because it changes on each delivery.

**How I'd monitor it**
- Counter of "duplicate skipped" events, plus a Splunk search on that log line by `eventId`. A spike should line up with rebalances or deploys.
- Rebalance rate, consumer lag (messages and time), and dead-letter topic rate.
- Table size and cleanup job health for the processed-id store.
- Reconciliation checks, such as ledger entries per payment id, to confirm no duplicates got through.

**Follow-ups to expect**
- *Does Kafka exactly-once solve this?* -> Only for read-process-write inside Kafka (transactions, `read_committed`). Writes to a database or API still need idempotent handling.
- *How long do you keep processed ids?* -> At least as long as a message could be redelivered, usually topic retention plus a safety margin.
- *Why not just commit offsets before processing?* -> A crash then loses messages (at-most-once). Duplicates that you can handle are better than lost payments.

**60-second answer**
Kafka normally gives at-least-once delivery, so a rebalance or retry will redeliver messages. I make the consumer idempotent so doing the work twice gives the same result as once. I take a unique business event id from the producer and store it in the same database transaction as the side effect, using an upsert such as insert-on-conflict-do-nothing, or MERGE in Oracle. If the insert finds the id already there, I skip the work. I also make state changes conditional on a version and prefer "set" over "add" writes. For external calls I pass the event id as the provider's idempotency key. I monitor duplicates skipped, rebalances and lag, and I purge old ids so the table stays small.

### Q11 [mid] Kafka vs RabbitMQ - when each?
tags: kafka, rabbitmq, messaging, event-streaming, message-queue, basics

**Start here: the concepts**
- **Message broker:** a server that sits between programs that send data (producers) and programs that process it (consumers), so they don't call each other directly. It exists so each side can be slow, down, or scaled independently.
- **Log (Kafka's model):** Kafka stores messages in an append-only file-like structure. Consuming does not delete a message; each consumer just remembers its position (the offset). Messages are removed only when retention (time or size) expires.
- **Queue (RabbitMQ's classic model):** messages wait in a queue, are handed to a consumer, and are deleted once the consumer acknowledges them.
- **Replay:** re-reading old messages by moving the offset back. A log allows it; a classic queue doesn't, because acknowledged messages are gone.
- **Partition and ordering per key:** a Kafka topic is split into partitions. Messages with the same key go to the same partition, and order is guaranteed only inside one partition.
- **Consumer group:** consumers sharing one subscription, with partitions divided among them. Many independent groups can each read the full stream.
- **Smart broker vs dumb broker:** RabbitMQ's broker decides where messages go and tracks each message's state. Kafka's broker mostly stores the log and leaves position-tracking to consumers.
- **Exchange:** RabbitMQ's router. Producers publish to an exchange, and rules (bindings) send copies to the right queues.
- **TTL and priority:** TTL is a per-message expiry time. Priority lets urgent messages jump ahead in a queue.
- **Request/reply:** the sender asks a question and waits for an answer on a reply queue.
- **Work queue:** many workers pull tasks from one queue, and each task is done once.

**The live scenario**
An e-commerce team publishes about 15,000 order events/s on RabbitMQ. Fraud, search and analytics all need them. Then the data team asks to re-process the last 7 days after finding a bug, and that is impossible because acknowledged messages are deleted. They move the event stream to Kafka with 7-day retention. Separately, their email-sending jobs (unpredictable, retried, some urgent) stay on RabbitMQ. A trial on Kafka showed that one slow message blocked everything behind it in the same partition.

**What the interviewer is really checking**
Whether you pick by the shape of the problem (event log vs task distribution) rather than "Kafka is faster", and whether you know the real differences in retention, routing and acknowledgement.

**How I answer it**
1. **Start with the core difference.** Kafka is a retained log, and RabbitMQ is a smart broker that routes messages and deletes them after ack. Everything else follows from that.
2. **Choose Kafka for event streaming, analytics and integration.** It handles high throughput, keeps data for replay, guarantees order per key (within a partition), and lets many independent consumer groups read the same data without affecting each other.
3. **Choose RabbitMQ for task distribution and complex routing.** Exchanges route by rules, and it offers per-message ack, TTL and priorities. It also supports request/reply and work queues, and can have lower latency at small loads.
4. **Check the consumption pattern.** If several teams need the same events or may need history, go with Kafka. If each message is a job to be done once, with retry and priority, go with RabbitMQ.
5. **Mention scaling limits.** Kafka scales a consumer group only up to the partition count. RabbitMQ adds workers easily, but one queue is a throughput limit.

**Trade-offs and what can go wrong**
- Kafka has no per-message TTL, priority or per-message ack. It commits offsets, so one slow or poison message blocks its partition unless you add retry or dead-letter topics.
- Kafka is heavier to run (partitions, rebalancing, capacity planning). Share groups (KIP-932) in Kafka 4.x add queue-like behaviour but are still preview.
- RabbitMQ queues can pile up if consumers are slow, and classic queues have no replay. RabbitMQ Streams (newer versions) add a log-style option, so "RabbitMQ can't replay" is no longer fully true.
- A common mistake is choosing Kafka only for hype, or RabbitMQ for a multi-team event backbone.

**How I'd monitor it**
- **Kafka:** per-partition consumer lag (messages and seconds), produce vs consume rate, rebalance rate, DLT rate, under-replicated partitions.
- **RabbitMQ:** queue depth, unacked messages, consumer count, publish vs ack rate, memory/disk alarms.
- **Splunk:** alert on rising lag or queue depth, and search for retry/DLT log spikes.

**Follow-ups to expect**
- *Is Kafka always faster?* -> No. It wins on sustained throughput and retention, but for small loads RabbitMQ can have lower latency.
- *Can Kafka do a work queue?* -> Partly. Consumers in a group share partitions, but parallelism is capped by the partition count and there is no per-message ack or priority.
- *Can you use both?* -> Yes, and it is common: Kafka for the event backbone, RabbitMQ for task jobs and routing.

**60-second answer**
Kafka is a retained log, while RabbitMQ is a smart broker that routes messages and deletes them after ack. I pick Kafka for event streaming, analytics and integration. It handles high throughput, keeps data for replay, keeps order per key, and lets many consumer groups read the same events independently. I pick RabbitMQ for task distribution and complex routing. It has exchanges, per-message ack, TTL, priorities, request/reply, and can have lower latency at small loads. The deciding question is whether many consumers need the same stream and history, or whether each message is a job to be done once. The trade-off is that Kafka is heavier to run and weak at per-message handling, and RabbitMQ lacks classic replay. Many companies run both.

### Q12 [mid] RabbitMQ basics: exchange types, acks, DLQ?
tags: rabbitmq, messaging, exchange, ack, dead-letter-queue, quorum-queue, basics

**Start here: the concepts**
- **Message broker:** a middleman that holds messages between a sender and a receiver. They don't have to be online at the same time, and the receiver can work at its own pace.
- **Producer / consumer:** the app that sends a message and the app that processes it.
- **Queue:** an ordered buffer inside RabbitMQ where messages wait until a consumer takes them.
- **Exchange:** the router. Producers never write to a queue directly; they publish to an exchange, which decides which queue(s) get a copy. This keeps producers unaware of who consumes.
- **Binding and routing key:** a binding is a rule linking an exchange to a queue. The routing key is a label on the message that the exchange matches against the binding.
- **Exchange types:**
  - *Direct:* exact key match.
  - *Topic:* pattern match, e.g. `order.*.created`.
  - *Fanout:* copy to every bound queue and ignore the key.
  - *Headers:* match on message headers instead of the key.
- **Ack (acknowledgement):** the consumer's "done" signal. Until it acks, RabbitMQ keeps the message and redelivers it if the consumer dies. A **nack** or reject says "failed", and you choose whether to requeue.
- **Publisher confirm:** the broker's ack back to the producer, meaning it has taken responsibility for the message.
- **Durable queue + persistent message:** both are needed for a message to survive a broker restart.
- **Prefetch (QoS):** the maximum number of unacked messages pushed to one consumer.
- **Dead-letter exchange (DLX) / dead-letter queue (DLQ):** where a message is re-routed when it is rejected without requeue, expires by TTL, overflows a length limit, or exceeds the delivery limit. The DLQ is an ordinary queue bound to the DLX.
- **Quorum queue:** a replicated queue that uses the Raft consensus protocol and survives node failure. It is the recommended HA type; classic mirrored queues are deprecated.

**The live scenario**
An order-email service handles about 2,000 msg/s at peak. One malformed message throws an exception, and the consumer calls `nack` with `requeue=true`. The message goes straight back to the head of the queue and fails again, thousands of times a minute. CPU hits 100%, the queue grows to about 400k messages, and customers get confirmation emails 20 minutes late. The fix was a delivery limit plus a DLX, so the bad message is parked after a few tries.

**What the interviewer is really checking**
Whether you know how a message travels (exchange, binding, queue) and how it is kept safe at each hop. That means confirms, durability, acks and a plan for poison messages, not just the type names.

**How I answer it**
1. **Explain the flow:** producer, exchange, binding, queue, consumer. The exchange decouples the producer from the queues, so you can add a consumer queue without touching producer code.
2. **Pick the exchange type by need:** direct for exact routing, topic for pattern routing, fanout for broadcast, headers when the key is not enough. Fanout ignores the key, so "routes by binding key" is not true for every type.
3. **Protect the producer side:** enable publisher confirms. Without them, a message sent just before a broker crash can vanish silently.
4. **Protect the broker side:** use durable queues and persistent messages. Durable queue alone keeps the queue but not the messages.
5. **Ack after the work is done, not on receipt.** Auto-ack deletes the message on delivery, so a crash mid-processing loses it. Manual ack gives at-least-once delivery, which means duplicates are possible, so consumers should be idempotent.
6. **Set prefetch.** Without a limit, one consumer can hoard thousands of messages while others sit idle. A small value, e.g. 10 to 50, spreads load fairly.
7. **Handle failures with a DLX.** Reject with `requeue=false` or set a delivery limit so poison messages move to the DLQ for inspection instead of looping.
8. **Use quorum queues for HA.** Messages are replicated across nodes. For example:
```
x-queue-type=quorum
x-delivery-limit=5
x-dead-letter-exchange=orders.dlx
```

**Trade-offs and what can go wrong**
- Requeue-on-failure causes hot loops.
- Auto-ack loses messages.
- Persistence and confirms cost throughput.
- Quorum queues use more disk and memory than classic queues.
- Ordering is only guaranteed per queue with a single consumer; multiple consumers or redelivery break it.
- An unmonitored DLQ becomes a silent graveyard.
- RabbitMQ deletes messages once acked, so unlike Kafka you cannot replay them.

**How I'd monitor it**
- Use the management UI or Prometheus plugin to watch *ready* vs *unacked* counts, publish vs ack rates, and the redelivery rate.
- Alert on DLQ depth above zero and on consumer count dropping.
- Watch for memory or disk alarms, which block publishers.
- Search Splunk for the `redelivered` flag, or for repeated message IDs in consumer errors.

**Follow-ups to expect**
- *Ack vs publisher confirm?* -> The ack is consumer-to-broker ("I processed it"). The confirm is broker-to-producer ("I safely have it").
- *How do you stop a poison message looping?* -> Reject with `requeue=false` or set a delivery limit, with a DLX so it lands in a DLQ.
- *RabbitMQ vs Kafka?* -> RabbitMQ is smart routing with messages deleted after ack. Kafka is a replayable partitioned log for high-throughput streams.

**60-second answer**
Producers publish to an exchange, which routes messages to queues through bindings. Direct matches the exact key, topic matches patterns, fanout broadcasts to all bound queues, and headers match on message headers. To avoid loss, I use publisher confirms, durable queues and persistent messages, and consumers ack manually after processing, accepting that duplicates are possible. I set prefetch so one consumer cannot hoard messages. For failures, I configure a dead-letter exchange and a delivery limit, so poison messages go to a DLQ instead of looping. I run quorum queues for high availability and monitor queue depth, unacked counts and DLQ size.

### Q13 [senior] How does replication and `min.insync.replicas` work?
tags: kafka, replication, min-insync-replicas, acks, isr, durability, basics

**Start here: the concepts**
- **Partition**: one ordered log that holds a slice of a topic's messages. Replication works per partition.
- **Replica**: a copy of a partition stored on a broker (a Kafka server). The **replication factor (RF)** is how many copies exist. RF=3 means three copies on three different brokers. Copies exist so a dead machine does not mean lost data.
- **Leader and followers**: one replica is the leader. All producer writes go to it, and consumers read from it by default. Followers continuously fetch from the leader to stay identical.
- **ISR (in-sync replicas)**: the leader plus the followers that are fully caught up. A follower that falls behind for longer than `replica.lag.time.max.ms` (30 seconds by default in recent versions) is removed from the ISR. It rejoins once it catches up.
- **High watermark**: the offset up to which every ISR member has the data. Consumers only see messages up to this point, so they never read data that could vanish in a failover.
- **`acks`** (producer setting): how many copies must confirm a write. `acks=1` waits for the leader only. `acks=all` waits for every replica currently in the ISR.
- **`min.insync.replicas` (min ISR)**: the minimum ISR size (leader included) the broker needs before it accepts an `acks=all` write. Below that, it rejects the write.
- **Unclean leader election**: promoting an out-of-sync replica to leader when the ISR is empty. This is controlled by `unclean.leader.election.enable`.

**The live scenario**
A payments topic runs at about 5,000 msg/s with RF=3, `min.insync.replicas=2` and `acks=all`. At peak, a broker's disk fails. The ISR for its partitions shrinks from 3 to 2. Leaders on that broker move to followers that already hold every acknowledged message. Producers see a brief latency blip and then carry on, with no lost payments. An hour later a second broker is lost during maintenance. The ISR is now 1, below the minimum of 2, so producers get `NotEnoughReplicasException`. The team prefers this to silently accepting writes that exist on only one machine. Reads continue, and writes resume when a broker returns.

**What the interviewer is really checking**
Whether you understand that durability comes from three settings working together (RF, `acks`, `min.insync.replicas`), and that you can explain the trade between availability and data safety.

**How I answer it**
1. **Writes go to the leader and followers copy them.** One leader per partition keeps ordering simple. Followers fetch from it, much like consumers do.
2. **The ISR is the set of caught-up replicas.** It is dynamic. A slow or dead follower drops out so it cannot block writes forever.
3. **With `acks=all`, the leader waits for every current ISR member.** A message is only acknowledged once all those copies have it. That means a new leader chosen from the ISR always has it.
4. **`min.insync.replicas` sets the floor.** Without it, a shrunken ISR of just the leader would still satisfy `acks=all`, which then behaves like `acks=1`. With the floor, the write is rejected if the ISR size is below it.
5. **Use RF=3 with min ISR=2.** One broker can fail or be restarted and writes still succeed with no data loss. Two copies always hold every acknowledged write, so at least one survives any single failure.
   ```properties
   # topic/broker: replication.factor=3, min.insync.replicas=2, unclean.leader.election.enable=false
   # producer:     acks=all, enable.idempotence=true
   ```
6. **Keep unclean leader election off.** Turning it on trades consistency for availability: a stale replica becomes leader and acknowledged messages are silently lost. Off is the default.

**Trade-offs and what can go wrong**
- Min ISR is only enforced for `acks=all`. With `acks=1` or `0` it is ignored, which is a common mistake.
- `min.insync.replicas=1` with `acks=all` gives a false sense of safety.
- Setting min ISR equal to RF (3 of 3) means one broker restart blocks all writes.
- `acks=all` adds latency because the slowest ISR member sets the pace.
- A slow follower (GC pause, bad disk, network) shrinks the ISR and can push you under the minimum.
- Producers must retry and handle `NotEnoughReplicasException`, or messages are dropped on the client side.
- Rolling restarts must go one broker at a time, waiting for the ISR to recover between brokers.

**How I'd monitor it**
- Broker metrics: `UnderReplicatedPartitions` (should be 0), `UnderMinIsrPartitionCount` (alert on anything above 0), `OfflinePartitionsCount`, and `IsrShrinksPerSec`/`IsrExpandsPerSec` (frequent flapping signals a slow follower).
- Producer error rates, plus a Splunk search for `NotEnoughReplicasException` or `NotEnoughReplicasAfterAppendException` in application logs.
- Follower fetch lag and disk or network health on the brokers.

**Follow-ups to expect**
- *What if RF=3 and min ISR=2 and two brokers die?* -> Writes with `acks=all` fail, because the ISR is 1. Reads continue from the remaining leader. You bring a broker back rather than relax the setting.
- *Does `acks=all` mean all three replicas have the message?* -> No, it means all replicas currently in the ISR. That is why the min ISR floor is needed.
- *Why is unclean leader election dangerous?* -> It can promote a replica that missed acknowledged messages. Those messages are lost and consumer offsets can become inconsistent.

**60-second answer**
Each partition has a leader that takes all writes and followers that copy it. The followers that are caught up form the ISR. With `acks=all` the leader waits for every replica in the ISR before acknowledging. `min.insync.replicas` sets the smallest ISR size allowed, and below that the broker rejects writes. Without that floor, `acks=all` could degrade to a single copy. The standard setup is RF=3, min ISR=2 and `acks=all`. It survives one broker loss with no data loss and no write outage, while two failures stop writes rather than risk data. I keep unclean leader election off so an out-of-date replica can never become leader. I alert on under-min-ISR partitions and ISR shrink rates.

### Q14 [senior] Explain log compaction and retention.
tags: kafka, log-compaction, retention, cleanup-policy, topics, tombstone, basics

**Start here: the concepts**
- **Topic, partition, log:** A topic is split into partitions. Each partition is an append-only file-like log, and every record gets a number called its **offset**. Records are never edited in place.
- **Segment:** A partition log is stored as a series of files called segments. Only the newest one, the **active segment**, is being written to. Kafka cleans up whole segments, not single records, and never touches the active one.
- **Key:** Each record can carry a key, such as a customer ID. Records with the same key go to the same partition.
- **Retention (`cleanup.policy=delete`):** Without cleanup the disk would fill up forever, so Kafka drops old data. A segment is deleted once its newest record is older than `retention.ms` (default 7 days) or the partition exceeds `retention.bytes`. Deletion is based on age or size only. It has nothing to do with whether consumers have read the data.
- **Compaction (`cleanup.policy=compact`):** Some topics hold state, not events. Here we only care about the latest value per key, not the full history. A background cleaner thread rewrites older segments and keeps at least the newest record for each key. Offsets of surviving records do not change, so gaps appear.
- **Tombstone:** A record with a key and a null value. It means "delete this key". Kafka keeps it for `delete.retention.ms` (default 24 hours) so consumers can see the delete, then removes it.

**The live scenario**
A `customer-profile` topic has about 2M customers and takes 5,000 updates/s. It was on 7-day retention. A new service started after a 10-day outage and found customers who had not changed in 10 days were missing, because their only record had expired. The team switched the topic to compaction. The topic now holds roughly the latest record per customer, a few GB instead of hundreds, and any new consumer can rebuild the full table by reading from the start.

**What the interviewer is really checking**
Whether you know there are two different cleanup models (time/size versus latest-per-key), when to use each, and the practical limits of compaction: it is not instant, not a real delete, and needs keys.

**How I answer it**
1. **Define retention first.** It removes whole old segments by age or size. Reason: it bounds disk use for event streams, such as clicks or payments, where history is the point.
2. **Define compaction.** It keeps the latest value per key. Reason: for state, the last value is the truth, and old values only waste disk and slow down rebuilds.
3. **Explain tombstones.** A null value marks the key for deletion. Reason: compaction has no other way to express "this key is gone".
4. **Explain the timing.** The cleaner only works on closed segments, and only when enough of the log is "dirty" (`min.cleanable.dirty.ratio`). `min.compaction.lag.ms` can delay it further. Reason: rewriting files is costly, so Kafka batches the work. Consumers can therefore still see older values for a key, and compaction never guarantees immediate removal.
5. **Pick by use case.** Compaction suits state topics, CDC, config and Kafka Streams changelogs. Retention suits event streams. `cleanup.policy=compact,delete` combines both.

```
cleanup.policy=compact
min.cleanable.dirty.ratio=0.5
```

**Trade-offs and what can go wrong**
- Compaction is not a delete button. Old values live on until the cleaner runs, so it does not meet strict "erase within X hours" rules by itself.
- Records need non-null keys. Compacted topics cannot sensibly hold keyless records.
- A consumer slower than `delete.retention.ms` may miss a tombstone and keep a stale key.
- Compaction loses history, so it is not suitable for audit trails.
- The cleaner uses disk I/O and CPU. A stuck cleaner thread makes the topic grow without bound.
- With plain retention, a consumer offline longer than `retention.ms` loses data.

**How I'd monitor it**
- Broker JMX: `kafka.log:type=LogCleaner,name=max-dirty-percent` and `kafka.log:type=LogCleanerManager,name=uncleanable-partitions-count`.
- Disk usage and log size per compacted topic, compared against the expected number of keys times average value size.
- Broker logs in Splunk for log-cleaner thread errors.
- Consumer errors about offsets out of range, which show retention deleted data a consumer still needed.

**Follow-ups to expect**
- *Does compaction reorder or renumber records?* -> No. Order and offsets of surviving records stay the same, and only gaps appear.
- *Why do I still see old values on a compacted topic?* -> They may be in the active segment, or the dirty ratio or compaction lag has not triggered cleaning yet.
- *How does this relate to Kafka Streams?* -> KTable state-store changelog topics are compacted so state can be rebuilt after a failure.

**60-second answer**
Kafka has two ways to clean a topic. Retention deletes whole old segments once they pass a time or size limit, which suits event streams. Compaction keeps at least the latest record for each key, which suits state such as CDC, config or changelogs. A new consumer can then rebuild the full table from the topic. A record with a key and a null value is a tombstone that deletes the key, and it is itself removed after `delete.retention.ms`. Compaction runs in the background on closed segments, so old values can stay visible for a while and removal is never immediate. You can also combine both with `compact,delete`.

### Q15 [senior] How do you manage schemas and evolution?
tags: kafka, schema-registry, avro, protobuf, schema-evolution, compatibility, basics

**Start here: the concepts**
- **Schema**: a written contract describing the fields of a message (names, types, which are optional). Kafka only moves bytes, so producers and consumers need a shared contract to agree what those bytes mean.
- **Avro / Protobuf / JSON Schema**: three formats for writing that contract. Avro and Protobuf also encode data compactly in binary.
- **Schema Registry**: a separate service that stores every version of every schema and gives each one a numeric **schema id**. It exists so schemas live in one place instead of being copied into every application.
- **Schema id in the message**: the serializer writes a magic byte plus a 4-byte schema id before the payload (Confluent wire format). The consumer reads the id, fetches the schema from the registry (and caches it), then decodes the bytes.
- **Subject**: the name under which versions of a schema are grouped. By default it is the topic name plus `-value` (or `-key`).
- **Schema evolution**: changing the contract over time while old and new producers and consumers still run together, and while old messages remain in the topic.
- **Compatibility mode**: a rule the registry enforces when a new version is registered. **BACKWARD** means a consumer using the *new* schema can read data written with the *previous* schema. **BACKWARD_TRANSITIVE** checks against *all* earlier versions, not just the latest. BACKWARD is the Confluent default.
- **Default value**: the value used when a field is missing from the data. It is what lets new code read old messages.

**The live scenario**
An orders topic carries 8,000 msg/s and has 12 consuming services. A producer team renames `amount` to `total` and deploys on a Friday. The registry has auto-register on, so the new schema is accepted silently. Consumers get null or failed reads, and retries push traffic into the dead-letter topic. Lag grows by about 480,000 messages per minute and billing is wrong until rollback. With a CI compatibility check, the build would have failed on the pull request.

**What the interviewer is really checking**
Whether you know what a compatibility mode actually allows and forbids, and whether you treat schema changes as a governed release process rather than a developer convenience.

**How I answer it**
1. **Use a registry with a schema format, so messages carry only a schema id.** The payload stays small and every version is stored centrally and checked.
2. **Set BACKWARD, or BACKWARD_TRANSITIVE, per subject.** Use the transitive form when consumers may replay a topic from the beginning, because old data of every version must stay readable. Under BACKWARD, upgrade **consumers first, then producers**.
3. **Make safe changes only.** Add fields **with defaults**. Under BACKWARD you may also delete a field, since a new reader just ignores it. What BACKWARD forbids is adding a field *without* a default, because old messages lack it. Do not change a field's type, and do not rename in place: a rename is a delete plus an add, so it breaks readers. (Avro aliases can help; in Protobuf never reuse a field number, and mark retired ones `reserved`.)
4. **Disable auto-registration in production.** Otherwise any app can publish a new schema at runtime and bypass review.
   ```
   auto.register.schemas=false
   use.latest.version=true
   ```
5. **Register schemas from CI.** The pipeline calls the registry's compatibility check on each pull request and registers the schema only after merge. The schema file lives in Git and is reviewed like code.
6. **For a truly breaking change, create a new topic or subject** (for example `orders-v2`). Dual-write, migrate consumers, then retire the old one.

**Trade-offs and what can go wrong**
- BACKWARD alone checks only the latest version, so a consumer reading very old data can still fail. Use the transitive form when replaying.
- Strict rules slow teams down, but the cost is small compared with a production incident.
- Defaults must be meaningful. A default of 0 for `amount` can hide bugs instead of exposing them.
- If the registry is down, new producers and consumers cannot fetch schemas they have not cached. Run it highly available (multiple instances; its data is stored in a Kafka topic).
- FULL compatibility (backward and forward) is safest but the most restrictive.

**How I'd monitor it**
- CI failures from compatibility checks (a healthy sign).
- Deserialization error counts and DLT rate per topic; in Splunk, search for `SerializationException` or `Schema not found`.
- Registry audit: alert on any schema registered outside the CI service account.
- Consumer lag per partition, to catch a stuck consumer after a bad release.

**Follow-ups to expect**
- *BACKWARD vs FORWARD?* -> BACKWARD: new readers handle old data (upgrade consumers first). FORWARD: old readers handle new data (upgrade producers first). FULL requires both.
- *How do you handle a breaking change?* -> Publish to a new topic or subject version, dual-write, migrate consumers, then retire the old one.
- *Does the schema id add much overhead?* -> No, it is 5 bytes per message (magic byte plus 4-byte id), and consumers cache schemas.

**60-second answer**
I keep schemas in a Schema Registry using Avro or Protobuf, so each message carries only a small schema id and the registry stores every version. I set BACKWARD compatibility, or BACKWARD_TRANSITIVE if consumers replay old data, which means new consumers can read old messages. So I add fields with defaults and never rename or change types in place, and I upgrade consumers before producers. In production I turn off auto-registration, and CI checks compatibility and registers the schema after review. If a change really is breaking, I move to a new topic and migrate consumers gradually. I watch deserialization errors, DLT rate and any schema registered outside CI.

### Q16 [senior] How do you monitor Kafka consumers?
tags: kafka, consumer-lag, monitoring, observability, consumer-groups, rebalancing, basics

**Start here: the concepts**
- **Topic and partition:** A topic is a named stream of messages. It is split into partitions, which are ordered logs. Each message in a partition has a number called its offset.
- **Consumer group:** A set of consumer instances that share a topic's work. Each partition is read by only one consumer in the group at a time.
- **Committed offset:** The position a group has recorded as "processed up to here". After a restart, the consumer resumes from it.
- **Consumer lag:** The log-end offset (newest message) minus the committed offset, per partition. It counts messages the group has not processed yet. It exists because producers and consumers run at different speeds, and lag shows whether consumers keep up.
- **Rebalance:** Kafka reassigns partitions among group members when someone joins, leaves or looks dead. Consumption pauses or slows during it.
- **DLT (dead-letter topic):** A side topic where messages that keep failing are parked, so one bad message does not block the partition.
- **Under-replicated partition:** A partition whose copies on other brokers have fallen behind. This is a broker-health signal, not a consumer one.
- **JMX:** Java's built-in metrics interface. Exporters turn it into data for Prometheus, Datadog or CloudWatch.

**The live scenario**
An `orders` topic has 12 partitions, 6 consumers and about 1,000 msg/s of traffic. After a release, a downstream database slowed down. Processing time per message rose from 5 ms to 25 ms, so each consumer dropped from about 200 msg/s to 40 msg/s. Together they handled only 240 msg/s against 1,000 arriving. The only alert was on CPU, which stayed low because consumers were waiting on the database. Lag grew by roughly 760 messages per second. Within 20 minutes it was about 900,000 messages, roughly 15 minutes of traffic, and customers received confirmation emails very late. A lag alert would have fired in the first few minutes.

**What the interviewer is really checking**
Whether you know that "consumer is running" is not the same as "consumer is keeping up". Seniors should also separate consumer metrics from broker metrics and know how to alert without noise.

**How I answer it**
1. **Start with lag per partition.** It is the most important metric because it directly says whether consumers keep up. Per-partition matters because a total can look fine while one hot partition falls behind.
2. **Express lag in messages and in time.** 900,000 messages means little alone. "About 15 minutes behind" tells the business what users feel.
3. **Compare the consumed rate with the produced rate.** If consumption stays below production, lag will keep growing, and this shows why.
4. **Track processing time per record.** This is usually the root cause of lag, for example a slow database or API call. If a poll loop takes longer than `max.poll.interval.ms`, Kafka evicts the consumer.
5. **Watch the rebalance count.** Frequent rebalances mean unstable consumers (slow processing, restarts, short timeouts). They cause pauses and often duplicate processing.
6. **Watch the error and DLT rate.** A rising DLT rate means messages are being skipped into the side topic, even if lag looks healthy.
7. **Add broker health.** Under-replicated partitions and broker request latency are not consumer metrics, but they explain slow fetches and commits.
8. **Collect via JMX into Prometheus, Datadog or CloudWatch.** Kafka clients and brokers already expose JMX metrics, and these tools give dashboards and alerting.
9. **Alert on lag that keeps growing for N minutes, not on one spike.** Spikes happen during deploys and rebalances and recover on their own. Sustained growth means real trouble.
10. **Use Burrow, Kafka UI or Conduktor to inspect.** Burrow judges lag by its trend over time. The UIs let you see per-partition offsets and group state.

**Trade-offs and what can go wrong**
- Alerting on a fixed lag number gives false alarms on busy topics and misses problems on quiet ones. Trend or time-based alerts are better.
- Total lag hides hot partitions caused by skewed keys.
- Lag of zero can be misleading if the consumer is stuck and committing offsets before processing. Check the commit strategy too.
- Too many per-partition metrics across many topics can overload the metrics system.
- Broker metrics alone will not tell you a consumer is slow.

**How I'd monitor it**
- Per-partition lag, in messages and estimated time.
- Consumed rate against produced rate.
- Processing time per record.
- Rebalance rate.
- Time since last poll.
- DLT message rate.
- Broker under-replicated partitions and request latency.
- Logs: in Splunk, search consumer logs for rebalance, "Revoking previously assigned partitions" and commit failures.

**Follow-ups to expect**
- *Lag is growing. What do you do?* -> Check whether consumption or production changed. Find the slow step. Then fix it, or add consumers up to the partition count.
- *Why can't I just add more consumers?* -> Consumers beyond the partition count sit idle, because one partition is read by one group member at a time.
- *How do you turn lag into time?* -> Divide lag by the current consume rate, or compare the timestamp of the oldest unprocessed message with now.

**60-second answer**
I start with consumer lag per partition, because it shows whether consumers are keeping up, and I express it in messages and in time. Next to it I watch the consumed rate against the produced rate, and processing time, which is usually the cause. I also track rebalance count and the error and DLT rate. On the broker side I watch under-replicated partitions and request latency. I collect everything through JMX into Prometheus, Datadog or CloudWatch. I alert when lag keeps growing for several minutes, not on a single spike. For inspection I use Burrow, Kafka UI or Conduktor.

### Q17 [senior] What are Kafka transactions and exactly-once in Kafka Streams?
tags: kafka, transactions, exactly-once, kafka-streams, idempotency, basics

**Start here: the concepts**
- **Offset:** a record's position number in a partition. A consumer "commits" its offset to remember how far it has read.
- **At-least-once:** if a crash happens between writing output and committing the offset, the input is re-read and the output is written again. This gives duplicates.
- **Idempotent producer** (`enable.idempotence=true`, with `acks=all`): the broker discards retried sends of the same record, so a producer retry does not create duplicates inside one partition. It does not cover a crash and restart of the whole app.
- **Transaction:** a group of writes to several partitions and topics that either all become visible or none do. The producer needs a stable `transactional.id`.
- **Consume-transform-produce:** read input, compute, write output, commit the input offset. The producer sends the consumed offsets inside the same transaction (`sendOffsetsToTransaction`), so output and "I have processed this input" commit together or not at all.
- **`read_committed`:** a consumer setting (`isolation.level`) that hides records from open or aborted transactions. The default, `read_uncommitted`, shows everything.
- **Zombie:** an old instance that is presumed dead but is still running, for example after a long GC pause. Kafka fences it using the `transactional.id` and an epoch number, so its writes are rejected.
- **Exactly-once in Kafka Streams:** Streams does all of the above for you. Its state-store changelog writes are in the same transaction.

**The live scenario**
A payments team runs a Streams app that aggregates about 5,000 events/s into running account totals. It used at-least-once. During a rolling deploy, rebalances caused some events to be reprocessed. About 12,000 events were counted twice, and the totals on a downstream topic were wrong. Reconciliation took a day. They switched on exactly-once and the totals stayed correct through restarts. Writes to their reporting database still needed idempotent upserts.

**What the interviewer is really checking**
Whether you know what exactly-once actually guarantees and where it stops. It is atomic Kafka-to-Kafka processing, not magic across external systems.

**How I answer it**
1. **Name the problem.** At-least-once gives duplicates after a crash or rebalance, because output and offset commit are two separate steps.
2. **Make them one step.** A transactional producer writes the output records and the consumed offsets in one atomic transaction. Either both appear or neither does.
3. **Make readers respect it.** Downstream consumers must use `isolation.level=read_committed`. Otherwise they can see data from transactions that later abort.
4. **Let Streams handle it.** Set the following, and Streams manages transactions, changelog writes and fencing:
```
processing.guarantee=exactly_once_v2
```
5. **State the boundary.** Exactly-once covers reading from Kafka, processing, and writing to Kafka. A database, REST call or email sits outside the transaction. A retry can repeat it, so use idempotent writes there (unique key, upsert, dedup table).
6. **Be precise about the claim.** Records may be processed more than once internally after an abort, but only one result becomes visible. This is "exactly-once effect", not exactly-once delivery.

**Trade-offs and what can go wrong**
- Extra latency and throughput cost. Streams commits more often with EOS (the default `commit.interval.ms` drops to 100 ms), and results appear only at commit.
- A long-open transaction holds back the `read_committed` reader at the last stable offset, which raises end-to-end lag.
- Version note: `exactly_once_v2` needs brokers 2.5 or later. In Kafka 4.x the older `exactly_once` option is removed.
- Common mistake: assuming a downstream consumer is protected when it still uses the default isolation level.
- Common mistake: assuming side effects outside Kafka are covered.

**How I'd monitor it**
- Consumer lag per partition, in messages and in time, on `read_committed` consumers.
- Streams metrics for commit latency and rate.
- Producer fenced or transaction-abort errors in Splunk logs. Alert on spikes.
- Rebalance rate.
- Downstream reconciliation counts, such as input events versus aggregated totals.

**Follow-ups to expect**
- *How does Kafka stop zombie producers?* -> Each `transactional.id` has an epoch. When a new instance initialises, the broker bumps the epoch and rejects writes from the older one.
- *Can I get exactly-once into a database?* -> Not through Kafka transactions. Use idempotent upserts keyed by a unique event ID, or store the offset in the same database transaction.
- *What does `exactly_once_v2` improve?* -> It uses one producer per stream thread instead of one per task. This reduces resource use and scales better.

**60-second answer**
Without transactions, a crash between writing output and committing the offset causes duplicates. A transactional producer fixes this by writing the output and the consumed offsets in one atomic transaction. Consumers set `read_committed` so they only see committed data. In Kafka Streams I turn this on with `processing.guarantee=exactly_once_v2`, which also covers state-store changelogs and fences zombie instances. It costs some latency and throughput. The guarantee only covers Kafka-to-Kafka work, so for a database or API call I still make the write idempotent. I monitor lag, commit latency and fencing errors.

### Q18 [architect] Design a notification system handling 50k events/sec with retries and ordering per user.
tags: kafka, partitions, ordering, retries, idempotency, system-design, basics

**Start here: the concepts**
- **Topic and partition:** A topic is a named log of events. It is split into partitions, and each partition is an append-only list read in order. Kafka guarantees order only inside one partition.
- **Key:** The producer attaches a key (here `userId`). Kafka hashes it to pick the partition, so one user's events always land in the same partition and stay in order.
- **Consumer group:** Consumers sharing a group split the partitions between them, and each partition goes to one consumer. So 64 partitions allow at most 64 useful consumers.
- **Offset and commit:** The offset is the consumer's position in a partition. Committing it records "done up to here". A crash before the commit means the events are redelivered (at-least-once).
- **Idempotent producer:** With `enable.idempotence=true`, the broker discards duplicates caused by the producer's own retries. It does not stop a consumer from seeing an event twice.
- **Dedup by event id:** The consumer records processed event ids so a redelivery does not send a second SMS.
- **Retry topic and DLT:** A failed event is republished to a delayed retry topic so the main partition keeps moving. After the retries are exhausted it goes to a dead-letter topic (DLT) for humans or tooling.
- **Circuit breaker:** It stops calls to a failing provider for a while instead of hammering it.

**The live scenario**
A flash sale pushes 50k events/sec (order, shipping, OTP). The email provider allows 2k/sec and starts returning 429s. The first design retried in place, so partitions stalled and lag grew to 20 minutes. OTPs arrived after they had expired. Elsewhere, a "shipped" message beat "order placed" because a retry topic reordered them. The numbers are illustrative, but the failure modes are real.

**What the interviewer is really checking**
Whether you connect key, ordering, retries, duplicates, and provider limits, and whether you notice that retry topics break ordering.

**How I answer it**
1. **Split by channel and priority.** Ingest topic, then a routing step that checks preferences and templates (a separate service) and writes to `email`, `sms`, and `push` topics. OTPs get their own high-priority topic. The reason is that a slow email provider must not delay SMS.
2. **Key by `userId`.** This gives per-user order. A user's events share a partition, and different users run in parallel.
3. **Size partitions up front.** 50k/s over 64 partitions is about 800 msg/s each. I would pick 48-96 and leave headroom. Partitions can be added later but never removed, and adding them changes the key-to-partition mapping, which breaks ordering during the change.
4. **Make producers safe.** Use `acks=all`, `enable.idempotence=true`, replication factor 3, and `min.insync.replicas=2`. This avoids losing or duplicating events on the producer side.
5. **Make consumers idempotent.** Delivery is at-least-once, so dedupe by event id in a fast store with a TTL. Commit offsets only after the send is recorded.
6. **Get concurrency.** A provider call takes about 50 ms, so one thread per partition gives only about 20/s. Run a worker pool inside each consumer, routed by `hash(userId)`. This keeps per-user order and adds parallelism. Commit only up to the last contiguous finished offset.
7. **Retry without blocking.** Use per-channel retry topics with growing delays, then a DLT (Spring Kafka: `@RetryableTopic` or `DefaultErrorHandler` with `DeadLetterPublishingRecoverer`). **The correction to the stored answer:** retry topics break strict ordering. Fix this by attaching a per-user sequence number and dropping stale messages, or by retrying in place only for message types where order truly matters. Most notifications are independent, so order is enforced only where the business needs it.
8. **Protect providers.** Apply a token-bucket rate limit per provider and a circuit breaker. When the breaker opens, pause the consumer or route to a fallback provider.
9. **Keep a read model.** Write delivery status (queued, sent, failed, DLT) to a store such as Couchbase or Cassandra so support can answer "was it sent?".

**Trade-offs and what can go wrong**
- A **hot partition** forms if one key, such as a bulk sender, dominates. Salt keys for system-wide broadcasts that need no order.
- Dedup storage costs memory and money.
- Retries add delay, so OTP retries should be short or skipped.
- A rebalance causes a pause. Use static membership (`group.instance.id`) and cooperative assignment.
- Too many retry topics add operational overhead.

**How I'd monitor it**
Per-partition lag, in messages and in seconds. Produce rate versus consume rate. Rebalance rate. Retry-topic and DLT rates per channel. Provider 429/5xx rates and breaker state. Under-replicated partitions. A Splunk search on `eventId` to trace one notification end to end, with alerts on DLT growth and lag above an SLA (for example, OTP over 10 seconds).

**Follow-ups to expect**
- *Does idempotence give exactly-once?* -> No. It covers producer retries only. Consumers still need dedupe by event id.
- *How do you add partitions without breaking order?* -> Drain and pause, or create a new topic and migrate. Adding partitions in place remaps keys.
- *What if the DLT fills?* -> Alert on it, fix the cause, then replay with a tool, using dedup to stay safe.

**60-second answer**
I'd key events by `userId` so each user's notifications stay in order, and use about 64 partitions with headroom, since you can't shrink them later. Producers use `acks=all` and idempotence. Consumers are at-least-once, so they dedupe by event id and commit only after the send is recorded. Each channel has its own topic, with delayed retry topics and a DLT, so a slow provider never blocks others. I'd call out that retry topics break ordering, so I'd use sequence numbers or in-place retry only where order matters. Providers get rate limits and circuit breakers, and I'd store delivery status in a read model. I'd watch per-partition lag, DLT rate, and provider errors.

### Q19 [architect] Design a Change Data Capture (CDC) pipeline from Oracle/PostgreSQL to Kafka.
tags: kafka, cdc, debezium, kafka-connect, outbox-pattern, schema-registry, basics

**Start here: the concepts**
- **CDC (Change Data Capture):** Instead of asking a database "what changed?" by querying it, you read the changes it already records. Consumers get every insert, update and delete as an event, without extra load on the tables.
- **Transaction log:** The file where the database writes every change before applying it, so it can recover after a crash. It is an ordered, reliable record of changes. Oracle calls it the redo log and Postgres calls it the WAL.
- **Debezium and Kafka Connect:** Kafka Connect is a framework that runs "connectors" to move data in and out of Kafka. Debezium is a set of source connectors that read database logs and publish one Kafka topic per table.
- **Oracle and Postgres readers:** Oracle can be read through LogMiner, which is built in, or XStream, which is faster but needs GoldenGate licensing. Postgres uses logical decoding: a replication slot (a server-side bookmark) plus an output plugin such as pgoutput.
- **Snapshot:** Before streaming, the connector copies existing rows once, so consumers start with the full state and then receive live changes.
- **Outbox pattern:** The service writes a business event into an `outbox` table in the same transaction as its data. CDC publishes that table, so you never get "DB committed but Kafka publish failed". Debezium's **EventRouter** transform routes outbox rows to proper domain topics.
- **Schema registry:** A service that stores the event schemas (Avro, Protobuf or JSON Schema) and checks that changes stay compatible, so old consumers don't break.

**The live scenario**
An orders service on Postgres peaks at about 2,000 transactions/s. Five teams were polling it with `updated_at` queries, which loaded the primary and missed deletes. We moved to Debezium. One weekend the connector task failed and nobody was paged. Postgres kept the WAL for the idle replication slot, and the disk went from 40% to 95% in about 30 hours. The lesson was that CDC moves risk into the database itself, so connector health is a database-health concern.

**What the interviewer is really checking**
Whether you can design the whole pipeline, not just name Debezium. That means snapshot, ordering, schema change, delivery guarantees and failure modes on the source database.

**How I answer it**
1. **Pick the capture method.** I read the log, not poll tables. The log captures deletes, preserves commit order and adds almost no query load.
2. **Run Debezium on a Kafka Connect cluster** with several workers, so a failed task restarts elsewhere. Connector offsets are stored in Kafka.
3. **Choose raw table events or the outbox.** Raw table events suit replication and analytics. For domain events between services I use the outbox, so consumers aren't coupled to my table design.
   ```
   transforms=outbox
   transforms.outbox.type=io.debezium.transforms.outbox.EventRouter
   ```
4. **Key by primary key (or aggregate id for outbox).** Kafka orders only within a partition, so all changes to one row land in one partition and stay in order.
5. **Register schemas** with compatibility rules such as BACKWARD. DDL changes (a new column) then reach consumers safely. Postgres emits no DDL events, so the schema is inferred from the row events. Oracle keeps a schema-history topic.
6. **Plan the initial snapshot.** Run it off-peak, for large tables use incremental snapshots (they can run alongside streaming and be resumed), and size the topic partitions beforehand.
7. **Handle large transactions.** A bulk update of millions of rows produces a burst of events. Postgres can spill big transactions to disk, and Oracle LogMiner buffers them in memory. I tune memory and batch limits, and I ask the application team to batch their jobs.
8. **Sink with idempotent consumers.** Delivery is at-least-once, so after a restart you can see duplicates. Sink connectors upsert by key, and consumers dedupe by event id.

**Trade-offs and what can go wrong**
- An abandoned Postgres slot fills the disk (the scenario above). Set `max_slot_wal_keep_size` and alert on slot lag.
- Oracle LogMiner adds CPU load and has a mining lag. XStream needs a licence.
- Raw CDC leaks your table design to everyone, and a column rename becomes a breaking change.
- Re-snapshots are expensive, and ordering is guaranteed only per key, not across tables.
- Sensitive columns (PII) flow into Kafka unless you mask or exclude them.

**How I'd monitor it**
- Connector and task state through the Connect REST API, with an alert on `FAILED`.
- The Debezium JMX metric `MilliSecondsBehindSource`, which measures source lag in time.
- Postgres: `pg_replication_slots` retained WAL size and `confirmed_flush_lsn`. Oracle: archived-log retention.
- Consumer lag per partition on the sink consumer groups, plus DLT rate.
- Splunk searches on Connect worker logs for task failures and rebalances.

**Follow-ups to expect**
- *How do you avoid duplicates?* -> Delivery is at-least-once, so make consumers idempotent with upserts by primary key or an event-id check.
- *Why outbox instead of dual writes?* -> Dual writes to the DB and Kafka can't be atomic. The outbox row commits with the business data, and CDC publishes it.
- *How do you evolve a schema?* -> Use additive, backward-compatible changes, with the registry enforcing compatibility. Deploy consumers before producers for breaking changes.

**60-second answer**
I would use log-based CDC with Debezium on Kafka Connect, reading Oracle through LogMiner or XStream and Postgres through logical decoding. Each table's changes go to a topic keyed by primary key, so per-row order is kept. For domain events between services I'd use the outbox table with Debezium's EventRouter, so events commit atomically with the business data. Schemas live in a schema registry with compatibility rules. I'd run the initial snapshot off-peak, using incremental snapshots for big tables, and plan for large transactions. Delivery is at-least-once, so sinks must be idempotent. I'd monitor connector state, `MilliSecondsBehindSource` and replication-slot WAL size, because a stalled connector can fill the source database's disk.

### Q20 [mid] How do you test Kafka code?
tags: kafka, testing, testcontainers, embedded-kafka, awaitility, spring-kafka, basics

**Start here: the concepts**
- **Unit test**: runs one small piece of code (here, the method that handles one message) with no broker. It is fast and shows whether your business logic is right.
- **Integration test**: runs your code against a real Kafka broker, so serialization, consumer groups, offsets and error handling are exercised too. It exists because mocks cannot show how Kafka really behaves.
- **Testcontainers**: a library that starts a real Kafka in a Docker container for the test and removes it afterwards. The broker is the same software you run in production.
- **@EmbeddedKafka**: a Spring Kafka annotation that starts a broker inside the test JVM, with no Docker. Since Kafka 4.x has no ZooKeeper, an embedded broker runs in KRaft mode (Kafka's built-in metadata management).
- **Awaitility**: a library that polls until a condition becomes true or a timeout expires. Kafka processing is asynchronous, so a test must wait for the result without guessing how long it takes.
- **Thread.sleep**: a fixed pause. It makes tests either slow (sleep too long) or flaky (sleep too short), so avoid it.
- **Retry and DLT**: when a message fails, the consumer retries it. After the retries are used up, the message goes to a **dead-letter topic (DLT)**, a side topic that holds poison messages so the main flow keeps moving.
- **Duplicate delivery**: Kafka is normally at-least-once. After a rebalance or a crash before the offset is committed, the same message can arrive twice. A consumer that is safe against this is called **idempotent**.
- **Contract/schema test**: a check that producers and consumers agree on the message format, for example that a schema change does not break old consumers.

**The live scenario**
A payments service consumes about 2,000 msg/s. Its unit tests used mocks and all passed. After a deploy, a rebalance made the consumer re-read roughly 500 messages whose offsets were not yet committed. The handler was not idempotent, so customers were charged twice. No test had ever delivered the same message twice, and no test had checked what happens when a message keeps failing.

**What the interviewer is really checking**
Whether you know that Kafka's failure modes (duplicates, retries, poison messages, schema drift) need tests beyond mocked unit tests, and whether you can write async tests that are not flaky.

**How I answer it**
1. **Unit-test the handler as a plain method.** Keep business logic in a normal class that takes the message and returns or does something. Call it directly with no broker. The reason is speed: hundreds of cases run in milliseconds.
2. **Integration-test with a real broker.** Use Testcontainers Kafka (or `@EmbeddedKafka`). Publish a message, let your real listener consume it, and check the outcome. The reason is that serializers, consumer config and error handlers only prove themselves against real Kafka.
3. **Assert asynchronously with Awaitility, never `Thread.sleep`.** It returns as soon as the condition is true, and fails clearly after the timeout:
   `await().atMost(10, SECONDS).untilAsserted(() -> assertEquals(1, repo.count()));`
4. **Test the failure paths.** Send a message that always throws. Assert that it is retried the configured number of times and then lands in the DLT. The reason is that this path runs rarely in production, so it breaks unnoticed.
5. **Test duplicate delivery.** Send the same message twice (same key and id) and assert the side effect happens once. This proves the idempotency that at-least-once delivery requires.
6. **Contract-test the schemas.** In CI, check that a new schema version is compatible with what consumers already expect. The reason is that producer and consumer teams deploy separately.

**Trade-offs and what can go wrong**
- Testcontainers is closest to production but needs Docker on CI and starts slower. `@EmbeddedKafka` is lighter but less realistic.
- Starting a broker per test class makes the suite slow. Share one container and use unique topic names per test.
- Tests that reuse topics or group ids see each other's leftover messages and become flaky.
- Awaitility timeouts that are too short fail on slow CI machines.
- Passing integration tests do not prove behaviour under production load or real rebalances.

**How I'd monitor it**
- In CI: track the flaky-test rate, suite duration and schema-compatibility check results.
- In production, to confirm the tests cover the right things: DLT message rate, retry counts, consumer lag per partition, and a counter of duplicates skipped by the idempotency check. In Splunk, search for the DLT-publish log lines and alert if they spike.

**Follow-ups to expect**
- *Why not just mock KafkaTemplate or the consumer?* -> Mocks only check that your code calls an API. They cannot show real serialization, offset commits, rebalances or error-handler behaviour.
- *How do you test a rebalance?* -> Start two consumers in the same group in a Testcontainers test, stop one, and assert that its partitions move and no message is lost or wrongly double-processed.
- *How do you keep tests independent?* -> Use a unique topic and group id per test, and clean up or recreate topics between tests.

**60-second answer**
I test Kafka code in layers. First I unit-test the message handler as a plain method, because that is fast and needs no broker. Then I run integration tests against a real broker using Testcontainers, or `@EmbeddedKafka`, which runs in KRaft mode now that Kafka 4 has no ZooKeeper. Because processing is asynchronous, I assert with Awaitility instead of `Thread.sleep`, so tests are fast and not flaky. I deliberately test the failure paths: a message that keeps failing should be retried and then reach the dead-letter topic. I also send the same message twice to prove the consumer is idempotent, because Kafka delivers at least once. Finally, I add schema contract tests in CI so producer and consumer changes cannot silently break each other.

### Q21 [mid] Honest answer if asked "have you run Kafka clusters yourself?"
tags: kafka, interview-honesty, replication, isr, managed-kafka, operations, basics

**Start here: the concepts**
- **Broker**: one Kafka server that stores messages on disk and serves producers and consumers. A cluster is several brokers working together.
- **Replication**: each partition (an ordered log that a topic is split into) is copied to several brokers, so losing one machine loses no data. The replication factor is the number of copies, commonly 3.
- **Leader and followers**: for each partition, one copy (the leader) handles all reads and writes. The other copies (followers) keep copying from it.
- **ISR (in-sync replicas)**: the set of copies that are fully caught up with the leader. A follower that falls too far behind is dropped from the ISR.
- **min.insync.replicas**: the smallest ISR size at which Kafka still accepts writes sent with `acks=all`. With replication factor 3 and a minimum of 2, a write is acknowledged only after at least 2 copies have it. If the ISR shrinks below 2, writes fail instead of risking data loss.
- **Retention**: how long (or how much) data Kafka keeps before deleting it, for example 7 days. It drives disk size and how far back a consumer can replay.
- **Partition reassignment**: an admin operation that moves partition copies between brokers to balance load or disk after you add brokers.
- **KRaft quorum**: the small group of controller nodes that holds cluster metadata (which broker leads which partition). It replaced ZooKeeper, and Kafka 4.x is KRaft-only.
- **Managed service (e.g. Amazon MSK)**: the cloud provider runs the brokers and patching, and you use the cluster.

**The live scenario**
Our order service sent about 2,000 msg/s to a 3-broker MSK cluster. Topics used replication factor 3 and `min.insync.replicas=2`, and producers used `acks=all`. During a planned patch, one broker restarted. Producers saw a few seconds of retries, then recovered, and no orders were lost. In the review, people asked why some sends were slow and what would happen if a second broker had also gone down. Because I understood ISR, I could answer: with only one copy in sync, writes would be rejected rather than silently risked.

**What the interviewer is really checking**
Whether you are honest about your experience, and whether you can still reason about replication, durability and failure without bluffing about work you did not do.

**How I answer it**
1. **Say what is true first.** I have built producers and consumers, and the delivery, retry and dead-letter topic (DLT) patterns around them. Interviewers probe quickly, and a bluff collapses at the first follow-up.
2. **Name where I ran it.** I operated these applications on a managed service (MSK). That shows real production exposure without overclaiming.
3. **Draw the boundary plainly.** Broker administration, such as partition reassignment and the KRaft quorum, was handled by the platform team. I did not do it myself.
4. **Show the concepts anyway.** I can explain replication, ISR, `min.insync.replicas` and retention, and how they combine:
```
replication.factor=3, min.insync.replicas=2   (topic)
acks=all, enable.idempotence=true             (producer)
```
This survives one broker failure with no data loss. Two failures stop writes but protect the data.
5. **Show I can reason about capacity and failures.** For example, disk needed is roughly write rate × retention × replication factor. I would also describe what clients see when a broker restarts or the ISR shrinks.

**Trade-offs and what can go wrong**
- Overclaiming ("I ran the cluster") is the main mistake, and it is easily exposed.
- Underselling ("I only use it") hides real skills. Concrete failure-mode knowledge is the point.
- `acks=all` with a higher `min.insync.replicas` gives stronger durability, but higher latency and less availability during failures.
- A managed service does not remove your responsibilities. You still choose partition counts, retention and client settings.

**How I'd monitor it**
- Under-replicated partitions, ISR shrink and expand rate, and offline partitions, to show replication health.
- Broker disk usage against retention settings.
- Producer error and retry rates, including `NotEnoughReplicas` errors.
- Per-partition consumer lag, rebalance rate and DLT rate.

**Follow-ups to expect**
- *Why replication factor 3 with min ISR 2?* -> It tolerates one broker down while still writing, and every acknowledged write exists on at least two brokers.
- *What if two of three brokers fail?* -> The ISR drops below 2, so `acks=all` writes fail with `NotEnoughReplicas`. Data is not lost, and reads from the remaining copy may still work.
- *What does partition reassignment do?* -> It moves replicas between brokers to rebalance load or disk. It copies a lot of data, so it is usually throttled and done by the platform team.

**60-second answer**
"I've built Kafka producers and consumers and the retry and dead-letter patterns around them, and I've run them in production on a managed service, MSK. The platform team handled broker administration, like partition reassignment and the KRaft quorum, so I haven't done that myself. I do understand the concepts behind it. Each partition is replicated, followers that are caught up form the ISR, and with replication factor 3, `min.insync.replicas=2` and `acks=all`, we survive one broker failure without losing data. I can also reason about retention and disk capacity, and about what clients see when a broker restarts. I'd be happy to go deeper on any of that."

### Q22 [mid] Can you send files through Kafka?
tags: kafka, message-size, claim-check, object-storage, s3, producer, basics

**Start here: the concepts**
- **Kafka message (record):** the unit Kafka stores and delivers. Its value is just a sequence of bytes, so Kafka does not care whether it holds JSON, an image or a PDF.
- **Broker:** a Kafka server that stores messages and serves them to consumers. Every message is held and copied (replicated) across brokers, so bigger messages cost more everywhere.
- **Message size limit:** Kafka is tuned for many small messages. The default maximum is about 1 MB (broker `message.max.bytes`, topic `max.message.bytes`). The producer (`max.request.size`) and consumer (`max.partition.fetch.bytes`) have their own limits, and all of them must agree.
- **Object storage (S3):** a service built to store large files cheaply and fetch them by a URL or key.
- **Claim-check pattern:** instead of carrying the heavy item, you store it elsewhere and pass a small "ticket" (the link) that lets the receiver collect it.

**The live scenario**
A KYC (customer identity check) service sends scanned passports, about 5 MB each, straight through Kafka at 200 uploads a minute. The producer starts throwing `RecordTooLargeException`. The team raises the size limits, and then the consumers slow down. Each poll now pulls a few big messages, processing takes longer, and consumer lag grows. Broker disks and network fill up, and the same topic also carries small, urgent events that now queue behind the files. They redesign: the file goes to S3 and Kafka carries `{"customerId":101,"fileUrl":"s3://..."}`, which is about 200 bytes. Lag disappears.

**What the interviewer is really checking**
Whether you know that "possible" is not the same as "a good design". They want to hear the size limits, the reason Kafka suits small messages, and the claim-check alternative.

**How I answer it**
1. **Say yes, technically.** A message is bytes, so a file can be sent. This shows you know how Kafka works instead of just repeating a rule.
2. **Say it is a bad idea for big files.** Kafka's 1 MB default limit exists because large messages put pressure on broker memory, replication, disk and consumer fetches. They also slow every other message sharing that partition.
3. **Say small files are fine.** A few KB, such as a tiny icon or a small JSON document, is normal.
4. **Use the claim-check pattern for big files.** The producer uploads the file to S3 or other object storage first. It publishes the message only after the upload succeeds, so the link never points to nothing.
5. **Put only metadata in the message:** customer ID, file location, size, and optionally a checksum. The consumer reads the message and downloads the file when it needs it.
6. **Show the example.** The passport scan goes to S3 and Kafka carries the customer ID and file URL.

```
{"customerId":101,"fileUrl":"s3://kyc-docs/101/passport.pdf"}
```

**Trade-offs and what can go wrong**
- **Two systems to keep consistent.** If the upload succeeds but the publish fails, you get an orphan file. Clean these up with retries and a storage lifecycle rule.
- **Retention mismatch.** Kafka may delete the message after 7 days while the file lives on, or the reverse. Align the two.
- **Security.** Do not put a permanent public URL in a message. Use a short-lived pre-signed URL, or send only the key and let the consumer use its own access role.
- **Raising limits is a trap.** It hides the problem and hurts every topic's performance. If you must, compression helps but does not fix it.

**How I'd monitor it**
- Search Splunk for `RecordTooLargeException` on producers.
- Track producer `request-size-max` and `record-size-max`.
- Watch consumer lag in messages and in time, plus broker network throughput.
- Watch S3 upload and download error rates (4xx/5xx) and orphan object counts.

**Follow-ups to expect**
- *What if you truly must send a large payload?* -> Raise the limits consistently (`message.max.bytes`, `max.request.size`, `max.partition.fetch.bytes`) and compress. Splitting into chunks is possible but complicated, so I prefer claim-check.
- *What if the S3 upload succeeds but the Kafka publish fails?* -> Retry the publish. If it still fails, the file is an orphan that a cleanup job or storage lifecycle rule removes.
- *Is the link safe to put in a message?* -> Only if it is short-lived (a pre-signed URL with expiry) or the consumer has its own access rights. Never use a public permanent link for sensitive documents.

**60-second answer**
"Technically yes, because a Kafka message is just bytes, but I would not send big files. Kafka's default limit is about 1 MB, and large messages slow down brokers, replication and consumers. Small files of a few KB are fine. For anything bigger I use the claim-check pattern. I upload the file to object storage like S3, then publish a small message with the file link and metadata. For example, in a KYC flow the passport scan goes to S3 and Kafka carries the customer ID and the URL. I make sure the upload finishes before publishing, secure the link, and clean up orphan files."
