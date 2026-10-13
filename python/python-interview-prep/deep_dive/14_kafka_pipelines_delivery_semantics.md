# Deep Dive 14 — Designing Kafka Pipelines in Python & Delivery Semantics

> Runnable companion: [`06_kafka/03_delivery_semantics.py`](../06_kafka/03_delivery_semantics.py) —
> a dependency-free `FakeBroker` that reproduces message loss and duplication on purpose.
> Related deep dives: [Kafka core](13_kafka_core.md) · [Failure handling](15_kafka_failure_handling.md) ·
> [Schema management](16_kafka_schema_management.md) · [Queue architectures](18_queue_architectures.md)

## What interviewers are actually probing

This is the **engineering-judgement** section of a Kafka interview. The question is never "what is
at-least-once?" — it's "show me in code where the commit goes, and tell me what you lose."

The three things that get probed hardest: **where the offset commit sits relative to processing**
(that single line determines your delivery semantics), **whether you understand that exactly-once is
Kafka-to-Kafka only**, and **whether you know that at-least-once + an idempotent consumer is the
right answer for most systems** rather than reaching for transactions.

---

## Must-know points

- **At-most-once**: commit **before** processing → may lose. **At-least-once**: process **then**
  commit → may duplicate. **Exactly-once**: idempotent producer + transactions + `read_committed`.
- **`confluent-kafka-python`** wraps librdkafka (C): fastest, full feature set, transactions, Schema
  Registry. **`kafka-python`** is pure Python: easy install, slower, fewer features.
- The **idempotent producer** removes duplicates caused by **producer retries** — per partition, per
  session. It does **not** deduplicate your application sending the same business event twice.
- **End-to-end exactly-once with an external sink requires idempotent writes** — Kafka transactions
  don't span your database.
- **`produce()` is asynchronous.** Delivery reports arrive only when you call `poll()` or `flush()`.

---

## Interview questions and full answers

### Q1. Explain the three delivery semantics.

**At-most-once** — messages may be **lost** but are never redelivered. You commit the offset *before*
processing, so a crash between the commit and the work means the message is skipped forever. Use only
for genuinely disposable, high-volume data (raw metrics, sampled telemetry) where latency matters
more than completeness.

**At-least-once** — messages are **never lost** but may be **duplicated**. You process first and
commit after, so a crash before the commit means the message is redelivered on restart. **This is the
default you should reach for**, paired with an idempotent consumer.

**Exactly-once** — each message affects the result **once**. Kafka provides this for **Kafka-to-Kafka
flows** via idempotent producers + transactions + `isolation.level=read_committed`. For external
sinks you need idempotent writes or a transactional outbox.

**The sentence that matters most:**

> "Exactly-once *delivery* is impossible in a distributed system — that's the Two Generals problem.
> What Kafka gives you is exactly-once **processing semantics** within its own boundary: the
> consume-transform-produce cycle is atomic. The moment your sink is a database or an HTTP API,
> you're back to at-least-once plus idempotency."

That distinction is what separates people who've read the docs from people who've shipped it.

**And the practical recommendation:** in most systems, **at-least-once delivery + an idempotent
consumer = effectively-once**, at a fraction of the complexity and latency cost of transactions.

---

### Q2. Show at-most-once and at-least-once consumers in Python.

**The only difference is the order of two lines.** That's genuinely the whole thing, and saying so
plainly is the best answer.

```python
# Prerequisite for both: turn OFF auto-commit
c = Consumer({..., "enable.auto.commit": False})

# ---------- AT-MOST-ONCE: commit FIRST ----------
msg = c.poll(1.0)
c.commit(message=msg, asynchronous=False)
process(msg)                      # <- crash HERE: offset already advanced, message LOST

# ---------- AT-LEAST-ONCE: process FIRST ----------
msg = c.poll(1.0)
process(msg)                      # <- crash HERE: offset not advanced, message REDELIVERED
c.commit(message=msg, asynchronous=False)
```

**In the at-least-once version, what happens between the two lines is the entire risk window:**

- Crash **before** `process` completes → redelivered, no harm (assuming idempotency).
- Crash **after** `process` but **before** `commit` → redelivered → **duplicate side effect**.
- The window is small, but it is *not* zero, and rebalances make it fire regularly in practice —
  every deploy is a rebalance.

**The key design consequence:** you cannot shrink that window to nothing, so you must **make
`process` idempotent** instead. See
[Failure handling Q9](15_kafka_failure_handling.md#q9-show-techniques-for-implementing-an-idempotent-consumer).

**Batch commits** are the throughput version — commit once per batch rather than per message. The
duplicate window widens to the whole batch, but throughput improves enormously:

```python
batch = c.consume(num_messages=200, timeout=1.0)
for m in batch:
    if m.error(): continue
    process(json.loads(m.value()))       # must be idempotent
if batch:
    c.commit(asynchronous=False)          # one commit per 200 messages
```

---

### Q3. Why is `enable.auto.commit=True` risky?

Auto-commit fires on a **timer** (`auto.commit.interval.ms`, default 5 s) and commits the offsets of
messages **returned by `poll()`** — **regardless of whether your code has finished processing them**.

That creates *both* failure modes, which is the worst of both worlds:

- **Message loss**: `poll()` returns 100 messages. The auto-commit timer fires after you've processed
  20. You crash. Offsets say 100 are done; **80 messages are silently lost.** This is the dangerous
  one, because it looks like at-least-once but behaves like at-most-once.
- **Duplicates**: you process all 100 and crash *before* the next auto-commit. All 100 are
  redelivered.

```python
# RISKY — the commit is decoupled from your processing
c = Consumer({"enable.auto.commit": True})    # DEFAULT — this is the trap

# CORRECT — explicit commit after processing
c = Consumer({"enable.auto.commit": False})
```

**The librdkafka middle ground** is worth knowing because it gives you auto-commit's throughput with
explicit control:

```python
c = Consumer({
    "enable.auto.commit": True,        # the timer still batches commits efficiently
    "enable.auto.offset.store": False, # but YOU decide which offsets are eligible
})

msg = c.poll(1.0)
process(msg)
c.store_offsets(message=msg)           # mark as processed; the timer commits it later
```

`store_offsets()` records "this offset is safe to commit"; the background timer does the actual
commit. You get correct at-least-once semantics **and** batched commit efficiency. This is the
recommended production pattern with `confluent-kafka-python`, and mentioning it is a strong signal.

---

### Q4. What is an idempotent producer and how do you enable it?

Set **`enable.idempotence=true`** (the default in modern clients). The broker assigns the producer a
**Producer ID (PID)** and tracks a **per-partition sequence number**. Each batch carries its sequence
number, so the broker can:

- **Discard a duplicate batch** caused by a retry where the ack was lost in flight.
- **Reject out-of-order batches**, preserving ordering even with **up to 5 in-flight requests**.

```python
from confluent_kafka import Producer

p = Producer({
    "bootstrap.servers": "localhost:9092",
    "enable.idempotence": True,     # implies acks=all, retries=MAX, max.in.flight<=5
    "compression.type": "zstd",
    "linger.ms": 10,
    "batch.size": 131072,
})
```

**The problem it solves**, concretely: the producer sends a batch, the broker writes it, the **ack is
lost on the network**. The producer times out and retries. Without idempotence the broker writes the
batch **again** — a duplicate created entirely inside Kafka, with your application code blameless.
With idempotence, the broker sees the same PID + sequence number and silently discards it.

**The limits, which is what the follow-up asks:**

1. **Per producer session.** A restarted producer gets a **new PID**, so duplicates across a restart
   are not caught. (`transactional.id` fixes this — see Q5.)
2. **Per partition.** Sequence numbers are tracked per `(PID, partition)`.
3. **It does NOT deduplicate your application.** If your code calls `produce()` twice for the same
   business event — say, an HTTP retry from the client — idempotence sees two different records and
   writes both. **Application-level duplicates need a business event ID and an idempotent consumer.**

That third point is the one candidates miss, and it's worth stating unprompted: `enable.idempotence`
protects against *Kafka's* retries, not against *your* logic.

It also **forces `acks=all`** and sets `max.in.flight.requests.per.connection <= 5` and
`retries=MAX_INT`. So enabling it gives you durability for free — there's essentially no reason to
turn it off.

---

### Q5. How do Kafka transactions give exactly-once processing?

A **transactional producer** (one with a `transactional.id`) can **atomically**:

1. Write output records to **multiple partitions and topics**, and
2. **Commit the consumer's input offsets** — via `send_offsets_to_transaction`.

Both happen in one transaction. Either everything commits or everything aborts. Consumers reading the
output set **`isolation.level=read_committed`** so they never see records from aborted transactions.

```python
from confluent_kafka import Producer, Consumer

c = Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": "enricher",
    "enable.auto.commit": False,          # MANDATORY — the producer commits offsets
    "isolation.level": "read_committed",  # don't read aborted records from upstream
})
p = Producer({
    "bootstrap.servers": "kafka:9092",
    "transactional.id": "enricher-1",     # UNIQUE and STABLE per producer instance
})

p.init_transactions()
c.subscribe(["orders"])

while True:
    msgs = c.consume(num_messages=100, timeout=1.0)
    if not msgs:
        continue
    p.begin_transaction()
    try:
        for m in msgs:
            if m.error():
                continue
            p.produce("orders-enriched", key=m.key(), value=enrich(m.value()))
        # The offsets become part of the SAME transaction as the output records
        p.send_offsets_to_transaction(
            c.position(c.assignment()),
            c.consumer_group_metadata(),
        )
        p.commit_transaction()
    except Exception:
        p.abort_transaction()
        for tp in c.committed(c.assignment()):   # rewind so the batch is reprocessed
            c.seek(tp)
```

**How it actually works** — worth being able to sketch:

- A **transaction coordinator** (a broker) writes transaction state to the internal
  `__transaction_state` topic.
- Records are written to their partitions **immediately**, but marked as part of an open transaction.
- On commit, the coordinator writes a **transaction marker** (a control record) into each affected
  partition.
- A `read_committed` consumer **buffers records past the last stable offset** until it sees the
  marker, then either delivers them (commit) or discards them (abort).

**`transactional.id` fences zombies.** If instance A hangs and a rebalance gives its partitions to
instance B, B calls `init_transactions()` with the same `transactional.id`, which **bumps the epoch**
and causes any later write from A to be rejected with `ProducerFenced`. That's what stops a zombie
producing duplicates after it's been replaced.

**The costs, which you must volunteer:**

- **Latency** — `read_committed` consumers wait for markers, so end-to-end latency rises.
- **Throughput** — typically **10–30% lower**.
- **Operational complexity** — a unique, stable `transactional.id` per instance (awkward in
  Kubernetes; needs a StatefulSet or an ordinal-derived ID), plus `transaction.timeout.ms` tuning.
- **It only covers Kafka.** Your database is not in the transaction.

**The recommendation to give:** use EOS only when duplicate processing has **real business
consequences** — payments, inventory decrements, ledger entries. For analytics, logging, search
indexing and most enrichment, **at-least-once with an idempotent consumer** is the right trade.

---

### Q6. `confluent-kafka-python` vs `kafka-python` — which would you choose?

| | `confluent-kafka-python` | `kafka-python` | `aiokafka` |
|---|---|---|---|
| **Implementation** | C (librdkafka) binding | Pure Python | Pure Python, asyncio |
| **Maintainer** | Confluent | Community | Community (aio-libs) |
| **Throughput** | **Highest** (~1M msg/s) | ~50–100k msg/s | Moderate |
| **Transactions / EOS** | **Yes** | No | Partial |
| **Idempotent producer** | **Yes** | Limited | Yes |
| **Schema Registry** | **Yes** — Avro/Protobuf/JSON Schema serialisers | No (third-party) | No |
| **SASL/OAuth/mTLS** | **Full** | Partial | Partial |
| **Admin API** | **Yes** | Yes | Limited |
| **asyncio-native** | No (sync; newer versions add an AsyncIO layer) | No | **Yes** |
| **Install** | Wheels for most platforms; may need librdkafka | `pip install`, pure Python | `pip install` |

**The answer: `confluent-kafka-python` for production.** It's faster by an order of magnitude,
maintained by Confluent in lockstep with the broker, and it's the **only** one with full transaction
and Schema Registry support. `kafka-python` had long maintenance gaps (hence the `kafka-python-ng`
fork), though releases resumed.

**When the others win:**

- **`kafka-python`** — a constrained environment where you can't compile or install a C extension, or
  a throwaway script. Its API is also closer to the Java client, which can ease a Java port.
- **`aiokafka`** — an **asyncio-native** service. With `confluent-kafka` you must bridge a sync C
  library into the event loop with a poll thread and `loop.call_soon_threadsafe` (see
  [Web frameworks](10_web_frameworks.md#worked-example--fastapi-service-that-validates-an-order-and-publishes-it-to-kafka)).
  `aiokafka` removes that friction entirely. The trade-off is lower raw throughput and no
  transactions.

**The nuance worth adding:** `confluent-kafka` releasing the GIL during its C calls means a **thread
pool actually parallelises** Kafka I/O — which is unusual for Python and is part of why it's so fast.

---

### Q7. Show the equivalent producer/consumer in `kafka-python`.

The API is closer to the Java client — `send()` returns a **future**, and serialisers are plain
functions passed at construction.

```python
from kafka import KafkaProducer, KafkaConsumer
import json

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    acks="all",
    retries=5,
    key_serializer=str.encode,
    value_serializer=lambda v: json.dumps(v).encode(),
)

# send() returns a Future; .get() makes it synchronous (and slow — one round trip per message)
meta = producer.send("orders", key="o-1", value={"amt": 10}).get(timeout=10)
print(meta.partition, meta.offset)

# Async with a callback — the throughput-friendly way
producer.send("orders", key="o-2", value={"amt": 20}) \
        .add_callback(lambda m: log.debug("ok %s", m.offset)) \
        .add_errback(lambda e: log.error("failed %s", e))
producer.flush()

consumer = KafkaConsumer(
    "orders",
    bootstrap_servers="localhost:9092",
    group_id="billing",
    enable_auto_commit=False,
    auto_offset_reset="earliest",
    value_deserializer=lambda b: json.loads(b),
)

for msg in consumer:                  # a blocking iterator — nicer than poll() loops
    handle(msg.value)
    consumer.commit()                 # at-least-once
```

**Differences to note versus `confluent-kafka`:**

- **Deserialisers are built in** (`value_deserializer=`); `confluent-kafka` gives you raw bytes and
  you deserialise yourself (or use `DeserializingConsumer`).
- **The consumer is a plain iterator**, which is more Pythonic than an explicit `poll()` loop.
- **`.get()` on the send future is synchronous and slow** — one network round trip per message.
  Batching with callbacks is how you get throughput, exactly as in `confluent-kafka`.

---

### Q8. How do producer delivery reports work in `confluent-kafka-python`?

**`produce()` is asynchronous.** It enqueues the message in a local buffer (librdkafka's queue) and
returns immediately. It does **not** mean the message reached the broker.

Delivery results arrive through the **`on_delivery` callback**, which is invoked **only when you call
`poll()` or `flush()`**. This is the single most important operational detail of this client.

```python
import json, logging
log = logging.getLogger(__name__)

def report(err, msg):
    if err:
        log.error("delivery failed: %s", err)       # route to a fallback / alert
    else:
        log.debug("%s [%d] @ %d", msg.topic(), msg.partition(), msg.offset())

for rec in records:
    while True:
        try:
            p.produce("orders", key=rec["id"], value=json.dumps(rec), on_delivery=report)
            break
        except BufferError:
            p.poll(0.5)         # local queue full — serve callbacks to drain it, then retry
    p.poll(0)                   # serve callbacks without blocking

p.flush(30)                     # block until every message is delivered or fails
```

**Three things that go wrong in production if you don't know this:**

1. **Never calling `poll()`** → callbacks never fire → the queue fills → `BufferError` → and you
   never learn that deliveries are failing. Silent data loss with a healthy-looking process.
2. **Not calling `flush()` before shutdown** → every buffered message is **lost** on exit. This is
   why a Kafka producer belongs in a
   [`lifespan` teardown](05_context_managers_descriptors_metaclasses.md#worked-example--async-context-manager-for-a-kafka-style-client)
   and why the [FastAPI example](10_web_frameworks.md) runs a dedicated poll thread.
3. **Treating `produce()` returning as success.** It isn't. Only the delivery callback (or a
   successful `flush()`) tells you the record was acknowledged.

**`BufferError` handling** is the pattern above: the local queue (`queue.buffering.max.messages`,
default 100,000) is full, so `poll()` to drain callbacks and free space, then retry. This is
**producer-side backpressure** — see [Scaling Q10](12_scaling_applications.md#q10-what-is-load-shedding-and-backpressure).

---

### Q9. Synchronous vs asynchronous commits — trade-offs?

```python
c.commit(asynchronous=False)    # blocks until the broker confirms; retries on retriable errors
c.commit(asynchronous=True)     # fire and forget; result only via a callback
```

| | Synchronous | Asynchronous |
|---|---|---|
| **Latency** | Blocks (a network round trip) | Returns immediately |
| **Throughput** | Lower | Higher |
| **Failure visible?** | Yes — raises | Only via callback |
| **Ordering** | Guaranteed | A later commit can **overtake** an earlier one |

**The async ordering hazard is the interesting part.** If commit(offset=100) is in flight, fails and
retries, while commit(offset=200) succeeds in between, the retried commit could set the offset **back
to 100** — causing 100 messages to be reprocessed. (Modern clients guard against this, but the
pattern is why you don't blindly retry async commits.)

**The standard production pattern:**

```python
try:
    while running:
        batch = c.consume(num_messages=500, timeout=1.0)
        for m in batch:
            process(m)
        if batch:
            c.commit(asynchronous=True)     # fast during steady-state processing
finally:
    try:
        c.commit(asynchronous=False)        # SYNCHRONOUS on shutdown — must not be lost
    finally:
        c.close()
```

Async during normal operation for throughput; **synchronous on shutdown and on partition
revocation**, where losing the commit means reprocessing a large batch.

**And the biggest throughput lever here:** commit **per batch**, not per message. A per-message
synchronous commit adds a full round trip to every message and will cap you at a few thousand
messages per second.

---

### Q10. How do you achieve exactly-once when the sink is a database?

**Kafka transactions don't cover external systems.** A Kafka transaction can't include your
PostgreSQL write. So you need a different mechanism. Three options, in order of practicality:

**Option 1 — Idempotent writes (the usual answer).** Make the write naturally repeatable: upsert
keyed by a business event ID, or by `(topic, partition, offset)`.

```python
cur.execute("""
    INSERT INTO orders (event_id, order_id, amount, status)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (event_id) DO NOTHING
""", (event["event_id"], event["order_id"], event["amount"], event["status"]))
```

Replays become harmless. **This is what most production systems do**, and it's the answer to give
first.

**Option 2 — Store the offset in the same DB transaction as the result.** The database becomes the
source of truth for both, so they can never diverge. On assignment, `seek()` to the stored offset
instead of trusting Kafka's.

```python
with conn:                                 # one atomic transaction
    cur.execute("INSERT INTO orders ... ON CONFLICT DO NOTHING", ...)
    cur.execute("""
        INSERT INTO consumer_offsets (topic, partition, offset_val)
        VALUES (%s, %s, %s)
        ON CONFLICT (topic, partition) DO UPDATE SET offset_val = EXCLUDED.offset_val
    """, (msg.topic(), msg.partition(), msg.offset() + 1))
# Both committed, or neither. Kafka's own offsets are ignored.

def on_assign(consumer, partitions):
    for tp in partitions:
        stored = fetch_stored_offset(tp.topic, tp.partition)
        if stored is not None:
            tp.offset = stored
    consumer.assign(partitions)
```

This gives genuine exactly-once **for that sink**, at the cost of managing offsets yourself.

**Option 3 — Transactional outbox** for the **DB → Kafka** direction (the reverse problem). See Q13.

**The line to finish on:**

> "In practice: **at-least-once delivery plus an idempotent consumer equals effectively-once**, and
> that's what I'd build unless there's a specific reason to pay for transactions."

---

### Q11. How do you design a high-throughput producer?

```python
p = Producer({
    "bootstrap.servers": "kafka:9092",
    "enable.idempotence": True,                  # safety, ~free
    "compression.type": "zstd",                  # or lz4 for lower CPU
    "linger.ms": 20,                             # wait up to 20ms to fill a batch
    "batch.size": 262144,                        # 256 KB batches
    "queue.buffering.max.messages": 500000,
    "queue.buffering.max.kbytes": 1048576,       # 1 GB local buffer
})
```

**The levers, and what each trades:**

1. **`linger.ms`** — the single biggest lever. The default of 0 sends each record as soon as
   possible, producing tiny batches. Setting 5–50 ms lets batches fill, which improves throughput
   **dramatically** (often 10×+) at the cost of that much added latency. Almost always worth it.
2. **`batch.size`** — the maximum bytes per partition batch. Larger batches compress better.
3. **Compression** — `zstd` gives the best ratio; `lz4` the lowest CPU; `snappy` is the middle. A
   batch compresses far better than individual records. Set `compression.type=producer` on the
   **topic** so the broker doesn't decompress and recompress.
4. **Async produce with delivery callbacks**, never `flush()` per message (Q8).
5. **One producer per process.** The `Producer` object is **thread-safe** and internally batches
   across threads. Creating one per request destroys batching and leaks connections.
6. **Spread keys evenly.** A skewed key distribution creates a **hot partition** that becomes your
   throughput ceiling regardless of how many partitions you have. Check partition-level byte rates.
7. **Tune the local buffer** (`queue.buffering.max.*`) so bursts don't hit `BufferError`.

**The trade-off to state plainly:** `linger.ms` buys throughput with latency. For an event pipeline
20 ms is invisible. For a synchronous request/response path where a user is waiting, it may not be —
though if a user is waiting on a Kafka produce, that's usually an architecture question.

---

### Q12. How do you scale a slow consumer?

In order of what to try:

1. **Batch the processing.** `consume(num_messages=500)` and do **one bulk DB write** instead of 500
   individual ones. Usually a 10–50× win and by far the cheapest fix. Try this first.
2. **Add consumers**, up to the partition count. Beyond that they idle.
3. **Add partitions** if you've hit the cap — accepting that key→partition remapping breaks per-key
   ordering across the change ([Kafka core Q4](13_kafka_core.md#q4-how-does-kafka-guarantee-ordering)).
4. **Parallelise within the consumer** — hand messages to a thread or process pool. But:
   - **Route by key to a fixed worker** if per-key ordering matters.
   - **Only commit contiguous completed offsets.** If messages 1–100 are in flight and 50 finishes
     first, you cannot commit 50 — 1–49 might still fail. Track a completion window and commit the
     highest contiguous prefix.
5. **Fix the processing itself.** If each message triggers an N+1 query or a synchronous HTTP call,
   more consumers just multiply load on a downstream that's already the bottleneck. Profile before
   scaling.
6. **Tune fetch sizes** — `fetch.min.bytes`, `max.partition.fetch.bytes` — to reduce round trips.

**Watch consumer lag as the primary metric** (`kafka-consumer-groups --describe`, Burrow, the
Prometheus JMX exporter, or Confluent Control Center). Autoscale on lag rather than CPU — see
[Scaling Q6](12_scaling_applications.md#q6-explain-auto-scaling-in-kubernetes--ecs-for-a-python-service).

**The pause/resume pattern** for slow async processing, which keeps you in the group without
breaking `max.poll.interval.ms`:

```python
c.pause(c.assignment())          # stop fetching new records
# ... hand off to workers, keep calling poll() to heartbeat and stay in the group ...
c.resume(c.assignment())         # fetch again once the workers have drained
```

---

### Q13. What is the transactional outbox pattern?

It solves the **dual-write problem**: you need to save to the database *and* publish an event, but
there's no transaction spanning both. Whichever you do second can fail, leaving the two
inconsistent — an order in the database with no event, or an event for an order that was rolled back.

**The pattern:** write the event to an **`outbox` table in the same local DB transaction** as the
business data. A separate relay reads unpublished outbox rows and publishes them to Kafka, marking
them published.

```python
# 1. ONE database transaction — atomic by definition
async with db.begin():
    order = Order(user_id=uid, total=200)
    db.add(order)
    db.add(OutboxEvent(
        aggregate_id=order.id,
        event_type="OrderPlaced",
        payload=json.dumps({"order_id": order.id, "total": 200}),
        published=False,
    ))
# Either BOTH the order and the event row exist, or neither does.

# 2. A separate relay publishes them
async def outbox_relay():
    while True:
        events = await db.query(OutboxEvent).filter_by(published=False) \
                         .order_by(OutboxEvent.id).limit(100).all()
        for evt in events:
            producer.produce("orders", key=str(evt.aggregate_id), value=evt.payload)
        producer.flush()
        for evt in events:
            evt.published = True
        await db.commit()
        await asyncio.sleep(1)
```

**Why it works:** the database transaction is the **single source of atomicity**. The relay may
publish a row twice (if it crashes after `flush()` but before marking it published), so the guarantee
is **at-least-once** — which is why consumers must still be idempotent. But **nothing is ever lost**,
which is the property you actually need.

**The production version uses CDC instead of polling.** **Debezium** reads the database's
**write-ahead log** and streams outbox inserts to Kafka:

- No polling load on the database.
- Lower latency (milliseconds, not the poll interval).
- No application code in the relay path at all.
- Ordering follows the WAL.

**Operational notes:** index on `(published, id)` so the poll query is fast; **purge published rows**
or the table grows without bound; and `ORDER BY id` to preserve insertion order.

The mirror-image problem — Kafka → DB — is solved by
[idempotent writes](#q10-how-do-you-achieve-exactly-once-when-the-sink-is-a-database).

---

### Q14. How would you design an end-to-end order-processing pipeline?

A complete answer, which is what this question wants:

```
┌─────────────┐
│ FastAPI     │  validates the order (Pydantic)
│ order-api   │  writes order + outbox event in ONE DB transaction
└──────┬──────┘
       │
┌──────▼──────┐
│  Debezium   │  CDC on the outbox table -> no dual write
└──────┬──────┘
       │
┌──────▼──────────────────────────────────────┐
│ topic: orders                                │
│   key = order_id  (per-order ordering)       │
│   partitions = 12, RF = 3, min ISR = 2       │
│   Avro + Schema Registry, BACKWARD compat    │
└───┬───────────────┬───────────────┬──────────┘
    │               │               │
┌───▼────────┐ ┌────▼─────────┐ ┌───▼──────────┐
│ payment-svc│ │ enrichment   │ │ analytics    │
│ group:     │ │ group:       │ │ group:       │
│  payments  │ │  enricher    │ │  analytics   │
│            │ │              │ │              │
│ at-least-  │ │ transactional│ │ at-least-once│
│ once +     │ │ consume-     │ │ -> S3/       │
│ idempotent │ │ transform-   │ │   warehouse  │
│ upsert     │ │ produce      │ │              │
└───┬────────┘ └────┬─────────┘ └──────────────┘
    │               │
    │          ┌────▼──────────────┐
    │          │ orders-enriched   │
    │          └───────────────────┘
    │
┌───▼──────────────────────────────┐
│ orders.retry.1m -> .retry.10m    │  transient failures
│ orders.dlq                       │  poison pills
└──────────────────────────────────┘
```

**The decisions, each with its justification** — this is what gets you the marks:

| Decision | Why |
|---|---|
| **Outbox + Debezium** | Eliminates the dual-write problem; no lost events |
| **`key = order_id`** | All events for one order → one partition → ordering guaranteed |
| **12 partitions, RF=3, min ISR=2** | Parallelism with headroom; survives a broker loss with no data loss |
| **Avro + Schema Registry, BACKWARD** | Producers and consumers evolve independently; consumers upgrade first |
| **Separate consumer groups** | Each service reads the full stream at its own pace and fails independently |
| **payment-svc: at-least-once + idempotent upsert** | Duplicates are harmless; EOS complexity isn't justified |
| **enrichment: transactional** | Kafka→Kafka, so real EOS is available and cheap to adopt |
| **analytics: at-least-once** | Duplicates are tolerable in aggregates; simplest is best |
| **Retry topics + DLQ** | Transient failures don't block the partition; poison pills are parked |
| **Monitor lag, error rate, DLQ depth** | Lag is the leading indicator of everything |

**The consumer-specific choices matter most.** Notice that the **same topic** is consumed with
**different delivery semantics** by different services, chosen from each one's business requirements.
That's the judgement the question is testing — not "use exactly-once everywhere."

**Operational layer:** alert on consumer lag (> 10,000 or > 10 minutes), DLQ depth > 0,
under-replicated partitions > 0, and error rate by class. See
[Production stability](19_production_stability_monitoring.md).

---

## Worked example — reusable at-least-once consumer with batch commit and graceful shutdown

The template worth memorising. Every line is there for a reason.

```python
import signal, json, logging
from confluent_kafka import Consumer, KafkaException

log = logging.getLogger("consumer")
running = True

def stop(*_):
    global running
    running = False                              # cooperative shutdown flag

signal.signal(signal.SIGTERM, stop)              # Kubernetes sends SIGTERM
signal.signal(signal.SIGINT, stop)               # Ctrl-C

def on_revoke(consumer, partitions):
    """Commit before losing these partitions, so work isn't redone."""
    try:
        consumer.commit(asynchronous=False)
    except KafkaException:
        pass                                     # best effort; at-least-once tolerates failure

c = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "billing",
    "enable.auto.commit": False,                 # explicit commits only
    "auto.offset.reset": "earliest",             # new group reads the backlog
    "partition.assignment.strategy": "cooperative-sticky",
    "max.poll.interval.ms": 300000,
})
c.subscribe(["orders"], on_revoke=on_revoke)

try:
    while running:
        batch = c.consume(num_messages=200, timeout=1.0)
        for m in batch:
            if m.error():
                log.error("consume error: %s", m.error())
                continue
            handle(json.loads(m.value()))        # MUST be idempotent
        if batch:
            c.commit(asynchronous=False)         # at-least-once: after processing
finally:
    c.close()                                    # leaves the group cleanly -> fast rebalance
```

**Why each piece is there:**

- **`signal` handlers + `running` flag** — a cooperative shutdown that finishes the current batch
  rather than dropping it mid-flight.
- **`on_revoke` commit** — without it, a rebalance means the new owner reprocesses everything since
  the last commit.
- **`enable.auto.commit=False` + commit after processing** — this *is* at-least-once.
- **Batch of 200** — throughput. The duplicate window widens to 200 messages, which idempotency
  covers.
- **`cooperative-sticky`** — no stop-the-world pause.
- **`c.close()` in `finally`** — leaves the group explicitly, so the coordinator rebalances
  immediately instead of waiting out `session.timeout.ms`. Skipping this adds ~45 seconds of lag to
  every deploy.
- **`handle` must be idempotent** — stated in a comment because it's the load-bearing assumption of
  the whole design.

---

## Hands-on drills

1. Run [`03_delivery_semantics.py`](../06_kafka/03_delivery_semantics.py) — the `FakeBroker`
   reproduces loss and duplication without a real cluster. Then do it for real: move the commit line
   above and below `process()`, kill the consumer mid-batch, and count messages each way.
2. Run a consumer with `enable.auto.commit=True` and a slow handler. Kill it after the auto-commit
   timer fires but before processing finishes. Count the lost messages.
3. Convert that consumer to `enable.auto.offset.store=False` + `store_offsets()` and confirm the loss
   stops while throughput stays high.
4. Produce with `enable.idempotence=False` and `max.in.flight=5` while forcing retries (kill a
   broker). Look for out-of-order records. Enable idempotence and repeat.
5. Build the transactional consume-transform-produce loop. Kill the process mid-transaction and
   confirm a `read_committed` consumer never sees the aborted records.
6. Produce 100,000 messages with `linger.ms=0` and then `linger.ms=20`. Compare wall time and the
   average batch size in the client statistics.
7. Implement the outbox pattern with a polling relay. Kill the relay between `flush()` and marking
   rows published, then confirm duplicates appear — and that your idempotent consumer absorbs them.
8. Commit synchronously per message, then per batch of 500. Measure messages/second for both.

---

## The 60-second spoken answer

> "Delivery semantics come down to where the offset commit sits. Commit before processing is
> at-most-once — you can lose messages. Process then commit is at-least-once — you can duplicate.
> That's the default I reach for, with auto-commit disabled, because auto-commit fires on a timer
> regardless of whether processing finished, which can lose data silently. Exactly-once means
> idempotent producer plus transactions plus `read_committed`, and the producer commits the consumer
> offsets inside the same transaction — but that only works **Kafka to Kafka**. The moment the sink
> is a database, the transaction doesn't reach it, so I use idempotent upserts keyed by a business
> event ID, or store the offset in the same DB transaction as the result. In practice at-least-once
> plus an idempotent consumer is effectively-once at a fraction of the cost, and I'd only pay for
> transactions where duplicates have real business consequences like payments. I use
> `confluent-kafka-python` because it wraps librdkafka — it's an order of magnitude faster and it's
> the only client with transactions and Schema Registry support — and I'm careful that `produce()` is
> asynchronous: delivery callbacks only fire inside `poll()`, and if I don't `flush()` on shutdown I
> lose every buffered message. For throughput it's `linger.ms` and batching on the producer side, and
> batch commits with `consume(num_messages=N)` on the consumer side. And for the DB-to-Kafka
> direction I use the transactional outbox with Debezium CDC, so there's no dual write to get wrong."
