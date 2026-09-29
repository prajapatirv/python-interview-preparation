# 06 — Kafka: Core Concepts, Delivery Semantics, Failure Handling, Schema Registry

Kafka is the one topic here that genuinely needs infrastructure to run against for real. This
folder gives you both: a `docker-compose.kafka.yml` to spin up a real local broker, **and** every
file is written so you can read the code and reason about it even without running it — the
`# WOULD PRODUCE / WOULD CONSUME` comments show exactly what happens on a real cluster.

## Crib sheet

- **Topic/partition/offset**: a topic is a named log split into partitions for parallelism; each
  partition is ordered and immutable; each record has a sequential offset within its partition.
- **Ordering is guaranteed only within a partition.** Same key → same partition (via hashing) →
  preserved order for that key. No key → round-robin/sticky, no ordering guarantee across keys.
- **Replication**: RF=3 typical → 1 leader + 2 followers. ISR = replicas caught up with the
  leader. `acks=all` + `min.insync.replicas=2` means a write only succeeds once 2 of the 3
  replicas have it — survives 1 broker failure with zero data loss.
- **Consumer groups**: partitions are divided among the consumers sharing a `group.id`; each
  partition is owned by exactly one consumer in the group at a time. Max useful parallelism =
  number of partitions.
- **Delivery semantics** — the single most-asked Kafka question:
  - **At-most-once**: commit offset *before* processing → crash after commit = message lost.
  - **At-least-once**: process *then* commit → crash before commit = message redelivered
    (duplicate). This is the default you should reach for; make consumers idempotent.
  - **Exactly-once**: idempotent producer + transactions + `read_committed` isolation. High
    overhead — reserve for cases where duplicates have real business cost (payments, inventory).
- **Poison pills**: a message that always fails (bad JSON, broken schema). Retrying forever blocks
  the partition. Route it to a **DLQ** with error metadata instead, and keep moving.
- **Retry topics**: for transient failures needing a real delay, republish to `topic.retry.1m`,
  `topic.retry.10m`, etc. rather than sleeping inside the consumer loop (which blocks
  `max.poll.interval.ms` and can trigger a rebalance). Trade-off: this breaks strict per-key
  ordering — call that out explicitly if it matters for your use case.
- **Schema Registry**: producers/consumers agree on message shape via a versioned schema; the
  wire format is `[magic byte][4-byte schema ID][payload]` — only 5 bytes of overhead per message.
  `BACKWARD` compatibility (the default) means: add fields *with defaults*, or remove fields —
  never change a type or remove a required field without one.

## Files

| File | Topic |
|---|---|
| `01_producer_basics.py` | producing with a key (partition affinity), delivery callbacks, `flush()` |
| `02_consumer_basics.py` | consumer group, manual offset commit (at-least-once shape) |
| `03_delivery_semantics.py` | at-most-once vs at-least-once shown side by side via commit order |
| `04_retry_topic_dlq.py` | classify transient vs poison-pill errors, route to retry tier or DLQ |
| `05_schema_registry_avro_notes.md` | wire format, compatibility modes, safe vs unsafe Avro changes |
| `docker-compose.kafka.yml` | one-command local broker + Schema Registry for hands-on runs |

## Running against a real broker (optional but recommended)

```bash
docker compose -f docker-compose.kafka.yml up -d
pip install confluent-kafka
python 01_producer_basics.py
python 02_consumer_basics.py   # in a second terminal, while the producer is running
docker compose -f docker-compose.kafka.yml down
```

If you don't have Docker available, read the files anyway — every one has inline commentary
describing the exact broker-side behavior each call triggers.
