# Deep Dive 13 — Kafka Core: Topics, Partitions, Replication, Producers, Consumers

> Runnable companions: [`06_kafka/01_producer_basics.py`](../06_kafka/01_producer_basics.py) ·
> [`02_consumer_basics.py`](../06_kafka/02_consumer_basics.py) ·
> [`docker-compose.kafka.yml`](../06_kafka/docker-compose.kafka.yml)
> Related deep dives: [Delivery semantics](14_kafka_pipelines_delivery_semantics.md) ·
> [Failure handling](15_kafka_failure_handling.md) · [Schema management](16_kafka_schema_management.md) ·
> [Queue architectures](18_queue_architectures.md)

## What interviewers are actually probing

Kafka fundamentals come up in **every** event-driven interview, and the questions are remarkably
consistent. They want to know whether you understand Kafka as a **distributed commit log** rather
than "a queue" — because everything else (replay, multiple consumer groups, retention, compaction)
follows from that one idea.

The four things they will definitely probe: **how partitions give you both ordering and
parallelism** (and why those two are in tension), **how replication and ISR give durability**, **what
`acks` actually guarantees**, and **how consumer groups divide work**. Get those cold.

---

## Must-know points

- **Topic** = a named, append-only, **partitioned log**. Messages are retained by time/size and are
  **not deleted on read**.
- **Ordering is guaranteed only within a partition.** Key → partition via hashing, so the same key
  always lands on the same partition.
- **Replication factor N** = one leader + N−1 followers. **ISR** = replicas caught up with the leader.
- **Consumer group**: each partition is read by **exactly one** consumer in the group. Different
  groups each get a full copy of the stream.
- **Offsets** are committed per `(group, topic, partition)` in the internal `__consumer_offsets`
  topic.
- **`acks=all` + `min.insync.replicas=2` + `RF=3`** is the standard durability configuration.

---

## Interview questions and full answers

### Q1. What is Kafka and why is it used?

Apache Kafka is a **distributed, durable, partitioned commit log** used as an event streaming
platform. The mental model that matters: it is **not a queue**, it is an **append-only log that
consumers read at their own position**.

That single distinction explains almost every Kafka feature:

- Messages are **not deleted when consumed** — they're retained by policy (time or size), so
  **multiple independent consumer groups** can each read the whole stream, and you can **replay**
  history by resetting an offset.
- Consumers **pull** and track their own offset, so the broker holds no per-message, per-consumer
  state. That's why one broker can serve thousands of consumers.
- Ordering is a property of the **log** (a partition), not of the delivery mechanism.

**Why it's fast** (see Q15) and **why people choose it**: very high throughput via sequential disk
I/O, batching and zero-copy; horizontal scale via partitions; durability via replication; and
retention that turns the log into a source of truth you can rebuild state from.

**Common uses:** microservice event bus, CDC pipelines (Debezium), log and metric aggregation, stream
processing, feeding data lakes, and increasingly feeding ML/GenAI pipelines with real-time features.

> **When NOT to use Kafka** — worth volunteering, because it shows judgement: for simple task
> offloading with no replay or fan-out requirement, **SQS or Celery is simpler and cheaper**. Kafka
> is operationally heavy. For request/reply, use HTTP or gRPC — Kafka is not an RPC mechanism. See
> [Queue architectures](18_queue_architectures.md).

---

### Q2. Explain topic, partition, offset, broker and cluster.

- **Broker** — a single Kafka server. Brokers form a **cluster**.
- **Topic** — a logical stream of records, e.g. `orders`. Split into **partitions**.
- **Partition** — an **ordered, immutable, append-only log** stored on a broker (and replicated to
  others). Partitions are the unit of **both parallelism and ordering**.
- **Offset** — a monotonically increasing sequential ID of a record **within its partition**. Not
  global across the topic.
- **Segment** — a partition on disk is a series of segment files; retention deletes whole segments,
  which is why deletion is cheap.

```
Topic "orders"  (3 partitions, RF=3)

  P0: [0][1][2][3][4]            leader on broker-1, followers on 2 and 3
  P1: [0][1][2]                  leader on broker-2, followers on 1 and 3
  P2: [0][1][2][3][4][5][6]      leader on broker-3, followers on 1 and 2
       ^                    ^
       oldest retained      log-end offset (next write goes here)
```

Notice **offsets restart at 0 in each partition** — offset 3 is meaningless without knowing the
partition. A record is uniquely identified by `(topic, partition, offset)`.

**Metadata management:** modern Kafka (3.x, and mandatory in **4.0**) uses **KRaft** — a Raft quorum
of controller nodes — instead of ZooKeeper. ZooKeeper support was **removed in Kafka 4.0**.
Mentioning this signals currency; a candidate still describing ZooKeeper as required sounds several
years out of date.

---

### Q3. How does Kafka decide which partition a message goes to?

Three cases, in priority order:

1. **An explicit partition is specified** → that one is used.
2. **The record has a key** → the default partitioner **hashes the key** and takes it modulo the
   partition count. **The same key always lands on the same partition** (for a fixed partition
   count).
3. **No key** → a **sticky partitioner**: the client fills a batch for one partition before moving
   on, which improves batching and throughput. (Older clients used plain round-robin per record,
   which produced many small batches.)

**A Python-specific gotcha worth knowing**, because it causes real cross-language bugs: the **Java**
client hashes with **murmur2**, while **librdkafka** (which `confluent-kafka-python` wraps) defaults
to `consistent_random`, based on **CRC32**. So a Java producer and a Python producer writing the same
key can land on **different partitions**, breaking per-key ordering in a polyglot system.

```python
from confluent_kafka import Producer

p = Producer({
    "bootstrap.servers": "localhost:9092",
    "partitioner": "murmur2_random",        # match the Java client's hashing
})
p.produce("orders", key="customer-42", value=b"...")   # same key -> same partition
```

**Custom partitioners** are occasionally justified — routing by tenant to isolate noisy neighbours,
or geographic partitioning — but they're a maintenance burden and can create hot partitions. Default
key hashing is almost always right.

---

### Q4. How does Kafka guarantee ordering?

**Only within a single partition.** There is no global ordering across a topic, and there cannot be
without giving up parallelism entirely.

To keep all events for one entity ordered, **use the entity ID as the message key** so they all route
to the same partition:

```python
producer.produce(
    topic="order-events",
    key=order.customer_id.encode(),     # all this customer's events -> one partition
    value=json.dumps(order).encode(),
)
# Consumers see CREATED -> PAID -> SHIPPED for this customer in order. Guaranteed.
```

**The two things that silently break ordering**, and both are strong senior signals:

1. **Producer retries without idempotence.** If batch 1 fails and is retried while batch 2 succeeds,
   they land out of order. The fix: **`enable.idempotence=true`**, which lets the broker deduplicate
   and reorder using per-partition sequence numbers — and safely allows up to **5 in-flight
   requests**. Without idempotence you must set
   `max.in.flight.requests.per.connection=1`, which costs you a lot of throughput.

2. **Increasing the partition count later.** The mapping is `hash(key) % partitions`, so adding
   partitions **remaps existing keys**. Events for `customer-42` that used to go to P1 now go to P4
   — and the old ones are still sitting in P1, possibly unprocessed. **Ordering for existing keys is
   broken across the change.** This is why you over-provision partitions up front.

3. **A third, subtler one:** if a consumer hands messages to a thread pool, ordering within the
   partition is lost at the processing stage even though Kafka delivered them in order. Route by key
   to a fixed worker if order matters.

**Global ordering** requires a single partition — which caps you at one consumer and one broker's
throughput. Almost always the wrong trade; the right answer is usually "per-entity ordering is what
the business actually needs."

---

### Q5. How do you choose the number of partitions?

**Partitions cap consumer parallelism**: the maximum number of active consumers in one group equals
the partition count. Extra consumers sit idle.

The sizing estimate:

```
partitions >= max( target_throughput / per_partition_producer_throughput,
                   target_throughput / per_consumer_throughput )
```

Then **add headroom for growth**, because adding partitions later remaps keys (Q4).

Worked example: you need 100 MB/s. A partition sustains ~10 MB/s of produce. One consumer instance
processes ~5 MB/s. So you need ≥10 partitions for the producer side and ≥20 for the consumer side →
**20 minimum**, and you'd provision 30–40 for headroom.

**The cost of too many partitions** — the other half of the answer:

- **More open file handles** and memory on every broker (each partition is several files).
- **Larger metadata**, slower **rebalances** and slower **leader election** after a broker failure —
  recovery time scales with partition count.
- **Worse batching** — the producer's buffer is spread thinner across more partitions, so batches are
  smaller and throughput per request drops.
- **End-to-end latency can rise** because of that reduced batching.

**Practical guidance:** tens to low hundreds per topic is typical. A few thousand per broker is a
reasonable ceiling (KRaft raised the practical cluster limit into the millions, but per-broker limits
still apply). Start at 6–12 for a normal service topic and over-provision rather than repartition.

---

### Q6. Explain replication: leader, followers, ISR.

Each partition has a **replication factor** (3 in production). One replica is the **leader** and
handles all writes (and, by default, all reads); the others are **followers** that continuously fetch
from the leader.

The **In-Sync Replica set (ISR)** is the set of replicas — including the leader — that are **caught
up within `replica.lag.time.max.ms`** (default 30 s). A follower that falls behind (slow disk,
network, GC pause) is removed from the ISR and rejoins when it catches up.

```
Partition 0, RF=3
  broker-1: LEADER    [0][1][2][3][4]   <- all writes go here
  broker-2: follower  [0][1][2][3][4]   <- in ISR
  broker-3: follower  [0][1][2]         <- LAGGING, removed from ISR

  ISR = {broker-1, broker-2}
```

**A record is "committed" once every replica in the ISR has it.** Only committed records are visible
to consumers — which is why a consumer can never read data that might be lost on a leader failure.

**On leader failure**, the controller elects a new leader **from the ISR**, so no committed data is
lost. That's the guarantee.

**`replication.factor=3` is the standard** because it survives **two** broker failures for
availability and, paired with `min.insync.replicas=2`, one broker failure with **zero data loss** and
continued writes. RF=2 with min ISR=2 means any single broker failure stops writes entirely.

**Rack awareness** (`broker.rack`) spreads replicas across availability zones so an AZ outage doesn't
take all three copies. Worth mentioning for cloud deployments.

---

### Q7. What do `acks=0`, `acks=1` and `acks=all` mean?

| Setting | Producer waits for | Durability | Throughput |
|---|---|---|---|
| **`acks=0`** | Nothing — fire and forget | **Data loss likely**; you won't even know | Highest |
| **`acks=1`** | Leader wrote to **its own log** | Lost if the leader dies before followers replicate | Medium |
| **`acks=all`** (`-1`) | **All ISR replicas** have the record | Strongest | Lowest (marginally) |

**`acks=1` is the dangerous middle ground**, and explaining *why* is the point of this question:

> The leader acknowledges after writing to its local log. If the leader **crashes before the
> followers fetch that record**, a new leader is elected from the ISR — and it never received the
> record. The producer already got a success. **The message is silently lost.**

**The production configuration is a triple, not a single setting:**

```python
producer = Producer({
    "bootstrap.servers": "kafka:9092",
    "acks": "all",                    # wait for the full ISR
    "enable.idempotence": True,       # implies acks=all, retries, in-flight<=5
})
# AND on the topic:
#   replication.factor = 3
#   min.insync.replicas = 2
```

**Why all three together:** `acks=all` alone is not enough. If two of three replicas fail, the ISR
shrinks to just the leader — and `acks=all` now means "acked by one replica", silently degrading to
`acks=1` with no error. **`min.insync.replicas=2` makes the write *fail* instead**, which is what
you want: an explicit error is recoverable; silent single-copy storage is not.

**The latency cost is smaller than people expect** — the followers are fetching continuously, so
`acks=all` typically adds a few milliseconds. For almost every business workload that's worth it.
`acks=0` is defensible only for genuinely disposable, high-volume telemetry.

---

### Q8. What is `min.insync.replicas` and what happens when the ISR falls below it?

It's a topic (or broker) setting giving the **minimum ISR size required for an `acks=all` write to
succeed**.

With `RF=3, min.insync.replicas=2` you tolerate **one** broker failure and keep writing. If a second
broker fails, the ISR drops to 1 and producers with `acks=all` receive
**`NotEnoughReplicasException`** — writes are **rejected**.

**That rejection is the feature, not a bug.** Without it, Kafka would silently keep accepting writes
stored on a single replica, and the next failure loses them. Failing loudly lets your producer retry,
buffer, or alert — an explicit error is recoverable.

**Note:** reads still work. The partition is readable but not writable — a deliberate
**consistency-over-availability** choice (CP rather than AP, in CAP terms).

**The `RF` / `min.insync.replicas` relationship:**

| RF | min ISR | Broker failures tolerated (writes continue) | Data loss on failure |
|---|---|---|---|
| 3 | 2 | 1 | None |
| 3 | 1 | 2 | **Possible** — effectively `acks=1` |
| 3 | 3 | **0** — any failure stops writes | None |
| 2 | 2 | 0 | None |

**`min.insync.replicas = RF` is a common mistake**: maximum durability, but a single broker restart
(including a routine rolling upgrade) halts all writes. `RF=3, min ISR=2` is the standard because it
survives ordinary maintenance.

---

### Q9. What is unclean leader election?

If **every** ISR replica is unavailable, Kafka has two options:

- **`unclean.leader.election.enable=false` (the default)** — the partition stays **offline** until an
  ISR member returns. **Consistency over availability. No data loss.**
- **`unclean.leader.election.enable=true`** — elect an **out-of-sync** replica as leader. The
  partition is available again, but **every message that replica never received is permanently
  lost**, and consumers may see offsets go backwards.

**Keep it `false` for anything with business meaning** — orders, payments, financial events. Losing
data silently is far worse than a partition being briefly unavailable, and you have monitoring to
detect the outage.

Enable it only for genuinely disposable high-volume streams (raw clickstream, metrics) where
availability genuinely matters more than completeness — and say explicitly that it's a data-loss
trade you're making knowingly.

---

### Q10. How do consumer groups work?

Consumers sharing a **`group.id`** form a group. The **group coordinator** (a broker) assigns each
partition to **exactly one** consumer in that group, so the work is divided with no duplication
inside the group.

**Different groups each receive the full stream independently** — that's how Kafka does pub/sub. The
billing service and the analytics service each have their own group and their own offsets, and
neither affects the other.

```
Topic "orders" — 4 partitions

Group "billing"     (2 consumers)      Group "analytics"  (4 consumers)
  consumer-A: P0, P1                     consumer-W: P0
  consumer-B: P2, P3                     consumer-X: P1
                                         consumer-Y: P2
                                         consumer-Z: P3

Both groups see EVERY message. Offsets are tracked per (group, topic, partition).
```

If there are **more consumers than partitions**, the extras sit **idle** — they're standby capacity
that takes over on a rebalance, which is useful, but they add no throughput.

```python
from confluent_kafka import Consumer

c = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "billing-service",          # identity of the group
    "auto.offset.reset": "earliest",        # only when there's no committed offset
    "enable.auto.commit": False,            # commit explicitly after processing
})
c.subscribe(["orders"])

while True:
    msg = c.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(msg.error()); continue
    print(msg.partition(), msg.offset(), msg.key(), msg.value())
    c.commit(message=msg, asynchronous=False)     # at-least-once
```

**Offsets are stored in the internal compacted topic `__consumer_offsets`**, keyed by
`(group, topic, partition)` — which is why a restarted consumer resumes exactly where the group left
off, and why compaction keeps only the latest offset per key.

---

### Q11. What is a rebalance, and how do you reduce its impact?

A **rebalance** redistributes partitions among group members. Triggered when a consumer joins,
leaves, crashes, or the subscription/partition count changes.

**Eager rebalancing (the old default)** is **stop-the-world**: *every* consumer revokes *all* its
partitions, then the coordinator reassigns and everyone resumes. Processing pauses across the whole
group, even for consumers whose assignment didn't change. With a large group and slow startup, that
pause can be tens of seconds.

**Cooperative-sticky rebalancing** (`CooperativeStickyAssignor`, Kafka 2.4+) is **incremental**: only
the partitions that actually need to move are revoked, in two rounds. Consumers keeping their
partitions **keep processing throughout**.

```python
c = Consumer({
    ...,
    "partition.assignment.strategy": "cooperative-sticky",
})
```

**The full mitigation list:**

1. **`cooperative-sticky`** — the single biggest win.
2. **Static membership** (`group.instance.id`) — a consumer with a stable ID that restarts within
   `session.timeout.ms` **rejoins with its old assignment and triggers no rebalance at all**. Ideal
   for rolling restarts in Kubernetes with a StatefulSet.
3. **Tune the timeouts**: `session.timeout.ms` (heartbeat deadline) and `max.poll.interval.ms`
   (processing deadline) — see Q12.
4. **Keep processing within the poll interval** — reduce `max.poll.records` rather than raising the
   interval indefinitely.
5. **Commit offsets in the `on_revoke` callback**, so partitions you're losing don't get reprocessed
   from an older offset:

```python
def on_revoke(consumer, partitions):
    try:
        consumer.commit(asynchronous=False)     # flush before losing these partitions
    except KafkaException:
        pass

c.subscribe(["orders"], on_revoke=on_revoke)
```

6. **Kafka 4.0's new consumer group protocol (KIP-848)** moves assignment to the **broker side**,
   removing the group-wide synchronisation barrier entirely. Mentioning it shows currency.

**The rebalance death spiral** is worth describing, because it's a real production failure: slow
processing exceeds `max.poll.interval.ms` → the consumer is evicted → rebalance → the remaining
consumers get more partitions → they're now even slower → they get evicted → repeat. Lag grows
unboundedly. The fix is to **reduce `max.poll.records`**, not to raise the interval.

---

### Q12. What is the difference between `session.timeout.ms` and `max.poll.interval.ms`?

Two independent liveness checks, and confusing them is the most common Kafka consumer
misconfiguration.

| | `session.timeout.ms` | `max.poll.interval.ms` |
|---|---|---|
| **Checks** | Is the **process** alive? | Is **your processing** keeping up? |
| **Signal** | Heartbeats, sent by a **background thread** | Time between calls to `poll()` |
| **Default** | 45 s (10 s in older clients) | 5 min |
| **Fails when** | Process crashed, GC pause, network partition | Your handler is too slow |

**The crucial asymmetry:** heartbeats come from a **background thread**, so a consumer stuck in a
10-minute database call is still **heartbeating happily** — the broker thinks it's healthy. But it
isn't calling `poll()`, so `max.poll.interval.ms` fires and it's removed from the group anyway. This
is why "my consumer keeps rebalancing but the process is clearly alive" is a `max.poll.interval.ms`
problem, not a `session.timeout.ms` one.

**Tuning rules:**

- **Slow processing** → reduce **`max.poll.records`** first (fewer messages per batch means less work
  before the next `poll()`). Raising `max.poll.interval.ms` is the blunt instrument: it works, but it
  also means a genuinely hung consumer takes that long to be detected and replaced.
- `heartbeat.interval.ms` should be **≤ 1/3 of `session.timeout.ms`** so a couple of missed
  heartbeats don't evict a healthy consumer.
- For long-running work, an alternative is to **`pause()` the partitions, process asynchronously, and
  keep calling `poll()`** to stay in the group — this decouples your processing time from the poll
  interval entirely. It's also exactly the technique used for
  [delayed retries](15_kafka_failure_handling.md#q5-how-does-a-delayed-retry-consumer-wait-without-breaking-the-group).

---

### Q13. What does `auto.offset.reset` do?

It applies in **exactly two situations**, and only those:

1. The group has **no committed offset** for a partition — a brand-new consumer group.
2. The committed offset **no longer exists** — retention deleted the segment it pointed at, which
   means the consumer fell so far behind that data was lost.

| Value | Behaviour |
|---|---|
| `earliest` | Start from the oldest retained message |
| `latest` (default) | Start from new messages only — **skips everything already in the topic** |
| `none` / `error` | Raise an error |

**It does NOT apply on a normal restart** — a group with a valid committed offset always resumes from
there, whatever this setting says. That misunderstanding is the source of "why didn't my consumer
re-read from the beginning?"

**Which to choose:**

- **`earliest`** for anything where you must not miss events — a new billing consumer should process
  the backlog. The trade-off: deploying a new group against a topic with 30 days of retention means
  reading 30 days of data at startup.
- **`latest`** for live-only consumers (real-time dashboards, notifications) where history is
  irrelevant.
- **`none`** when silently skipping data would be unacceptable and you want to be paged instead —
  it turns case (2), the data-loss case, into a loud failure. That's a strong production choice for
  critical pipelines.

**To replay deliberately**, don't rely on this setting — use `kafka-consumer-groups --reset-offsets`
or `consumer.seek()` explicitly.

---

### Q14. How do Kafka retention and log compaction work?

Two **cleanup policies**, controlled by `cleanup.policy`:

**`delete` (default)** — remove whole **segments** once they exceed `retention.ms` (default 7 days)
or `retention.bytes`. Deletion is cheap because it drops entire files rather than individual records.

**`compact`** — keep **at least the latest record per key** and remove older versions of that key.
The log becomes a **changelog / snapshot**: replaying it from the start reconstructs the current state
of every key.

```
Before compaction:
  (user1, {name:"A"}) (user2, {name:"B"}) (user1, {name:"A2"}) (user2, null) (user1, {name:"A3"})

After compaction:
  (user1, {name:"A3"})            <- only the latest per key survives
  (user2, null)                   <- TOMBSTONE: deletes the key, kept for delete.retention.ms
```

A record with a **`null` value is a tombstone** — it marks the key deleted, and is itself removed
after `delete.retention.ms` (default 24 h). That delay exists so consumers have a chance to observe
the deletion; if it were removed immediately, a slow consumer would never learn the key was deleted.

**`cleanup.policy=compact,delete`** combines both — compact, *and* drop anything older than the
retention window.

**Where compaction is used:**

- **`__consumer_offsets`** — Kafka's own offset storage. You only need the latest offset per
  `(group, topic, partition)`.
- **Kafka Streams / KSQL state store changelogs** — restore state by replaying the compacted log.
- **Reference/lookup data** as a topic — a "current state of every customer" topic that a new service
  can read from the beginning to build its own local cache.
- **Event sourcing snapshots**.

**Two caveats to mention:** compaction is **not immediate** — the active segment is never compacted,
and the cleaner runs based on `min.cleanable.dirty.ratio` (default 0.5), so duplicates persist for a
while. And compacted topics **require keys** — a null key on a compacted topic is rejected.

---

### Q15. Why is Kafka so fast?

Five mechanisms, and being able to name them all is a good depth signal:

1. **Sequential disk I/O.** Kafka only **appends**. Sequential writes on spinning disks reach
   hundreds of MB/s versus a few MB/s for random writes — and even on SSDs, sequential access is far
   friendlier to the controller. The log structure is the design.

2. **The OS page cache.** Kafka deliberately **does not maintain its own cache in the JVM heap**. It
   writes to the page cache and lets the OS handle flushing. Consumers reading recent data are served
   **from RAM without a disk read**, and there's no GC pressure from cached messages. Restarting a
   broker doesn't cold-start the cache, because it belongs to the OS.

3. **Batching and compression.** Producers accumulate records into batches (`linger.ms`,
   `batch.size`) and compress the **whole batch** (lz4/zstd/snappy), which compresses far better than
   per-record. The batch stays compressed on disk and is sent compressed to consumers — compressed
   once, not per hop.

4. **Zero-copy transfer.** For an uncompressed fetch, Kafka uses `sendfile()` to move bytes **from
   the page cache straight to the network socket**, entirely in kernel space. No copy into user
   space, no JVM object allocation.

5. **A simple, consumer-driven pull model.** The broker tracks **no per-message, per-consumer
   state** — no acknowledgements per message, no redelivery bookkeeping, no locks. Consumers track
   their own offsets. That's why a broker can serve thousands of consumers, and it's the core
   architectural difference from a traditional broker like RabbitMQ or ActiveMQ.

Plus **partitioned parallelism** across brokers, which is how you scale the whole thing horizontally.

---

## Worked example — create a topic programmatically and inspect replication

```python
from confluent_kafka.admin import AdminClient, NewTopic

admin = AdminClient({"bootstrap.servers": "localhost:9092"})

topic = NewTopic(
    "orders",
    num_partitions=6,                 # caps consumer parallelism — over-provision
    replication_factor=3,             # survives 2 broker failures
    config={
        "min.insync.replicas": "2",                   # with acks=all: no silent single-copy writes
        "retention.ms": str(7 * 24 * 3600 * 1000),    # 7 days
        "cleanup.policy": "delete",
        "compression.type": "producer",               # keep the producer's compression, don't recompress
    },
)

for name, fut in admin.create_topics([topic]).items():
    try:
        fut.result()
        print("created", name)
    except Exception as e:
        print("failed", name, e)      # TopicAlreadyExistsError is usually fine

# Inspect leader and ISR per partition — this is your durability health check
md = admin.list_topics(timeout=10)
for p in md.topics["orders"].partitions.values():
    print(f"partition {p.id}: leader={p.leader} replicas={p.replicas} isr={p.isrs}")
    if len(p.isrs) < 2:
        print(f"  !! UNDER-REPLICATED — acks=all writes will fail")
```

**Why this matters operationally:** `len(isr) < min.insync.replicas` on any partition means writes to
it are failing right now. **Under-replicated partitions should be a monitored metric with an alert at
> 0** — see [Production stability](19_production_stability_monitoring.md).

**Note on `auto.create.topics.enable`:** disable it in production. Auto-creation gives you the broker
defaults (often RF=1, one partition), which is how a critical topic ends up with no replication and
nobody notices until a broker dies.

---

## Hands-on drills

Start the local broker first: `docker compose -f 06_kafka/docker-compose.kafka.yml up -d`

1. Create a topic with 3 partitions. Produce 100 messages **with no key** and 100 **with 5 distinct
   keys**. Consume and print `(partition, key)`. Confirm each key always lands on one partition.
2. Start 2 consumers in one group against 3 partitions. Print the assignment. Start a third, then a
   fourth, and watch the fourth stay idle.
3. Start a second consumer group on the same topic and confirm it receives **every** message
   independently of the first group's progress.
4. With `acks=1`, produce continuously while killing the leader broker. Count produced vs consumed
   messages and find the gap. Repeat with `acks=all` + `min.insync.replicas=2`.
5. Set `min.insync.replicas=2` on an RF=3 topic, stop two brokers, and read the
   `NotEnoughReplicas` error. Confirm reads still work.
6. Create a compacted topic. Write `(k1,v1) (k1,v2) (k1,null)`, force a roll, and observe what
   survives compaction.
7. Add a `time.sleep(400)` inside a consumer loop with `max.poll.interval.ms=300000`. Watch the
   eviction and rebalance. Fix it by reducing `max.poll.records`.
8. Switch a group from the default assignor to `cooperative-sticky`. Add a consumer during
   processing and compare the pause duration between the two.

---

## The 60-second spoken answer

> "Kafka is a distributed, partitioned, append-only commit log — not a queue. Messages aren't deleted
> when read, they're retained by policy, which is what gives you replay and lets multiple consumer
> groups each read the whole stream independently. A topic is split into partitions; a partition is
> an ordered immutable log and is the unit of both parallelism and ordering. Ordering is guaranteed
> only within a partition, so I key by entity ID to keep one customer's events in order — and I'm
> careful that adding partitions later remaps keys and breaks that. Each partition has a leader and
> followers; the ISR is the set caught up with the leader, and a record is committed once the whole
> ISR has it. For durability I run `acks=all` with `replication.factor=3` and
> `min.insync.replicas=2` — `acks=all` alone isn't enough, because if the ISR shrinks to one it
> silently degrades to `acks=1`, whereas min ISR makes the write fail loudly. Consumer groups divide
> partitions one-to-one, so parallelism is capped at the partition count. I use `cooperative-sticky`
> and static membership to avoid stop-the-world rebalances, and I watch for the trap where slow
> processing blows `max.poll.interval.ms` — heartbeats come from a background thread so the consumer
> looks alive while it's actually being evicted; the fix is fewer `max.poll.records`, not a longer
> interval. And Kafka is fast because of sequential appends, the OS page cache, batch compression and
> zero-copy sendfile, with the broker tracking no per-consumer state."
