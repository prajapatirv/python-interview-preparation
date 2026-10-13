# Deep Dive 15 — Kafka Failure Handling: Retry Topics, DLQ, Consumer Idempotency

> Runnable companion: [`06_kafka/04_retry_topic_dlq.py`](../06_kafka/04_retry_topic_dlq.py) —
> a dependency-free simulation of the retry-tier → DLQ flow.
> Related deep dives: [Delivery semantics](14_kafka_pipelines_delivery_semantics.md) ·
> [Error handling](08_error_handling.md) · [Kafka core](13_kafka_core.md) ·
> [Production stability](19_production_stability_monitoring.md)

## What interviewers are actually probing

Real systems fail: downstream APIs time out, messages are malformed, consumers crash mid-batch. What
interviewers want is a **layered strategy**, not a `try/except`:

1. **Classify** the error — transient or permanent?
2. **Retry transient failures without blocking the partition.**
3. **Park poison messages in a DLQ** so one bad record doesn't wedge a topic.
4. **Make the consumer idempotent** so redelivery is harmless.

The single highest-value thing you can say here is why **in-place retries block the partition** — it
proves you've thought about head-of-line blocking rather than just exception handling.

---

## Must-know points

- **Classify**: transient (retry) vs permanent/poison (DLQ immediately). They need opposite
  responses.
- **In-place retries block the partition** — head-of-line blocking. Retry topics keep the main flow
  moving.
- A **DLQ message** = the original payload **plus** headers: error, stack, source
  topic/partition/offset, attempt count.
- **Idempotent consumer**: dedupe on **event ID**, upsert, or a processed-events table.
- **Retry topics trade away strict per-key ordering** — call that out before being asked.

---

## Interview questions and full answers

### Q1. What kinds of failures occur in a Kafka consumer?

Three families, each needing a different response — and the whole design follows from this
classification:

**1. Transient** — will probably succeed on retry.
Downstream timeouts, HTTP 5xx, DB deadlocks, connection resets, rate limiting (429), a broker
failover. **Response: retry with backoff.**

**2. Permanent / poison pill** — will **never** succeed, no matter how often you retry.
Malformed JSON, schema mismatch, failed business validation, a reference to an entity that will never
exist, a bug in the handler. **Response: DLQ immediately.** Retrying is pure waste and blocks the
partition.

**3. Infrastructure** — the consumer itself is disrupted.
Process crash, rebalance mid-processing, broker failover, pod eviction. **Response: rely on offset
replay plus idempotency.** You don't handle these in a `try/except`; you handle them by making
reprocessing safe.

```python
class Transient(Exception):  """Retry: timeout, 503, DB deadlock, rate limited."""
class Permanent(Exception):  """DLQ now: bad schema, failed validation, unknown entity."""
```

**The classification IS the design.** Get it wrong in either direction and you have a production
incident: treating a permanent error as transient wedges the partition forever; treating a transient
error as permanent fills your DLQ with messages that would have succeeded, and someone has to replay
them by hand.

**The hard cases to acknowledge**, because interviewers probe for nuance:

- A **404 from a downstream** — is the entity missing forever (permanent), or has the event just
  arrived before the entity was created (transient, an ordering race)? Usually **retry a few times
  then DLQ** — a bounded retry answers the question empirically.
- **Unexpected exceptions** — unknown by definition. Safest default is **DLQ with a loud alert**,
  because an unknown error retried forever blocks the partition. Better to park it and page someone.

---

### Q2. What is a poison pill message and how do you handle it?

A message that **always fails processing** — undeserialisable bytes, a schema the consumer can't
read, data that fails validation.

**Why it's dangerous:** if you retry it forever, the consumer is **stuck at that offset**. It never
advances. Lag grows for the **entire partition**, and every message behind it — thousands of perfectly
good ones — is blocked indefinitely. One bad record takes out a partition.

**The handling:**

```python
try:
    data = json.loads(msg.value())
    validate_schema(data)
    process_order(data)
except (json.JSONDecodeError, ValidationError) as e:
    send_to_dlq(producer, msg, error=e)     # park it with full context
    # and CRITICALLY:
finally:
    consumer.commit(message=msg, asynchronous=False)   # ADVANCE regardless
```

**The `commit` is the load-bearing line.** You must advance past a poison pill, or the whole design
fails. Committing an unprocessed message feels wrong — and it is, unless you've preserved it in the
DLQ first. That's exactly the trade the DLQ exists to make: *lose it from the main flow, keep it
somewhere you can inspect and replay*.

**Then alert.** A message arriving in the DLQ means something is broken — a producer sending bad
data, a schema change that wasn't coordinated, a bug. **DLQ depth > 0 should be an alert**, not a
dashboard nobody looks at.

**Preventing them upstream is better than handling them:** a **Schema Registry with compatibility
enforcement** (see [Deep Dive 16](16_kafka_schema_management.md)) stops most poison pills ever being
produced. Handling them well is the safety net; schema enforcement is the fix.

---

### Q3. Why not just retry in a loop inside the consumer?

**Short in-memory retries are fine** — two or three attempts with a small backoff (under a second or
so) for a brief network blip. That's cheap and avoids the complexity of retry topics for the common
case.

**Long retries inside the poll loop are a serious problem**, for three compounding reasons:

1. **Head-of-line blocking.** While you sleep 60 seconds retrying message 5, messages 6–10,000 in
   that partition **wait**. Lag grows for everything behind it. One slow downstream stalls a whole
   partition's throughput.

2. **You exceed `max.poll.interval.ms`.** The consumer must call `poll()` within that window
   (default 5 minutes). Sleep for 10 minutes and the coordinator **evicts you from the group**,
   triggering a rebalance. Your partitions go to another consumer, which picks up the same message
   and hits the same failure.

3. **The rebalance storm.** That new consumer now has more partitions, so it's slower, so it also
   exceeds the interval, so it's evicted too. **Lag grows unboundedly while nothing is processed.**
   This is a genuine production death spiral and describing it is a strong senior signal.

```python
# BAD — blocks the partition and risks eviction
for attempt in range(10):
    try:
        process(msg); break
    except Transient:
        time.sleep(60)          # 10 minutes of blocking the whole partition

# GOOD — short inline retries for blips, then hand off
for attempt in range(3):
    try:
        process(msg); break
    except Transient:
        if attempt == 2:
            route_to_retry_topic(producer, msg)    # someone else's problem now
            break
        time.sleep(0.2 * 2 ** attempt)             # sub-second backoff only
```

**The rule: keep total in-loop retry time well under `max.poll.interval.ms`, and use a retry topic
for anything longer.**

---

### Q4. Explain the retry-topic pattern.

Instead of blocking, **republish the failed message to a dedicated retry topic with a delay tier**,
then commit the original and move on. The main flow never stalls.

```
orders ──(transient failure)──> orders.retry.1m ──(fails again)──> orders.retry.10m
                                                                          │
                                                             (fails again)│
                                                                          ▼
                                                                    orders.dlq
```

```python
RETRY_TIERS = [("orders.retry.1m", 60), ("orders.retry.10m", 600), ("orders.retry.1h", 3600)]
DLQ = "orders.dlq"

def route_failure(producer, msg, err, attempt):
    headers = dict(msg.headers() or [])
    headers.update({
        "x-error":         str(err).encode(),
        "x-attempt":       str(attempt + 1).encode(),
        "x-origin-topic":  headers.get("x-origin-topic") or msg.topic().encode(),
        "x-origin-partition": str(msg.partition()).encode(),
        "x-origin-offset": str(msg.offset()).encode(),
        "x-first-failed-at": headers.get("x-first-failed-at") or str(time.time()).encode(),
    })
    target = RETRY_TIERS[attempt][0] if attempt < len(RETRY_TIERS) else DLQ
    producer.produce(target, key=msg.key(), value=msg.value(),
                     headers=list(headers.items()))
    producer.flush()
```

**Key design points:**

- **Preserve the key.** `key=msg.key()` keeps whatever ordering is still achievable within the retry
  topic, and keeps related events together.
- **`x-origin-topic` is set only once** (`headers.get(...) or ...`) so it still names the *original*
  topic after several hops. Without that guard, after two hops it says `orders.retry.1m` and you've
  lost the provenance.
- **The attempt counter lives in a header** — the message carries its own retry state, so the retry
  consumer is stateless.
- **Escalating tiers** (1m → 10m → 1h) give a downstream time to recover without hammering it, and
  bound the total retry duration.
- **Cap the tiers.** After the last one, it goes to the DLQ. An uncapped retry loop is how you build
  an infinite message.

**One consumer can subscribe to all tiers** and use the timestamp to decide whether a message is due
(see Q5), or you can run a separate consumer per tier — simpler, at the cost of more deployments.

**Spring Kafka has `@RetryableTopic`** which generates this whole structure declaratively. **In
Python you build it yourself** — which is exactly why this question is asked in Python interviews.

---

### Q5. How does a delayed retry consumer wait without breaking the group?

**You cannot `sleep()` for minutes inside the poll loop** — that's the `max.poll.interval.ms` problem
from Q3. The technique is **pause / seek / resume**, while continuing to call `poll()` so the
consumer stays in the group.

```python
import time
from confluent_kafka import TopicPartition

def handle_retry(c, msg, delay_s):
    _, ts = msg.timestamp()                      # when the message was produced
    due_at = ts / 1000 + delay_s
    if time.time() < due_at:
        tp = TopicPartition(msg.topic(), msg.partition(), msg.offset())
        c.pause([tp])                            # stop fetching from this partition
        c.seek(tp)                               # rewind so we re-read this message later
        schedule_resume(tp, at=due_at)           # resume() when due
        return False                             # not due yet
    return True                                  # due — process it

# The loop keeps calling poll() even while paused — that's what keeps us in the group
while running:
    msg = c.poll(1.0)                            # returns None for paused partitions
    resume_due_partitions(c)                     # un-pause anything whose time has come
    if msg is None:
        continue
    if handle_retry(c, msg, DELAY_FOR[msg.topic()]):
        process(msg)
        c.commit(message=msg, asynchronous=False)
```

**Why each call is needed:**

- **`pause(tp)`** — stop fetching from that partition. Other partitions keep flowing, so one delayed
  key doesn't stall the consumer.
- **`seek(tp)`** — rewind to this message's offset, so when we resume we get it again. Without the
  seek, resuming would fetch from the *next* offset and the message would be skipped.
- **Keep calling `poll()`** — this is the crucial part. `poll()` drives the heartbeat *and* satisfies
  `max.poll.interval.ms`. A paused partition returns nothing, so `poll()` returns quickly and the
  consumer stays healthy indefinitely.
- **`resume(tp)`** when due.

**Because retry topics are ordered by production time and all messages in a tier share the same
delay**, the head of the partition is always the earliest-due message. So pausing at the head is
efficient — you're not scanning.

**The simpler alternative worth mentioning:** run a **separate consumer per retry tier** on a cron-like
schedule (e.g. every minute, drain whatever is due). Less elegant, much less code, and perfectly
adequate for many systems.

---

### Q6. What should a DLQ message contain?

**The original message, completely untouched** — key, value, and original headers — **plus** metadata
headers. The original payload must be byte-identical so you can replay it without transformation.

| Header | Why |
|---|---|
| `x-origin-topic` | Where to replay it to |
| `x-origin-partition`, `x-origin-offset` | Exact provenance; lets you find it in the source log |
| `x-origin-timestamp` | When it was originally produced (lag analysis) |
| `x-consumer-group` | Which consumer failed — the same message may succeed elsewhere |
| `x-error-class` | Exception type — for grouping and alerting |
| `x-error-message` | The message |
| `x-stack-trace` | Truncated (~2 KB) — the first thing a debugger wants |
| `x-attempt-count` | How many retries were burned |
| `x-first-failed-at` | Total time in the retry pipeline |
| `x-service-version` | Which build failed — was it a bad deploy? |
| `x-failed-at` | When it landed in the DLQ |

```python
import traceback, time, json

def send_to_dlq(producer, msg, error, group, attempt=0):
    headers = dict(msg.headers() or [])
    headers.update({
        "x-origin-topic":     (headers.get("x-origin-topic") or msg.topic().encode()),
        "x-origin-partition": str(msg.partition()).encode(),
        "x-origin-offset":    str(msg.offset()).encode(),
        "x-consumer-group":   group.encode(),
        "x-error-class":      type(error).__name__.encode(),
        "x-error-message":    str(error)[:500].encode(),
        "x-stack-trace":      traceback.format_exc()[-2000:].encode(),
        "x-attempt-count":    str(attempt).encode(),
        "x-service-version":  SERVICE_VERSION.encode(),
        "x-failed-at":        str(time.time()).encode(),
    })
    producer.produce(
        "orders.dlq",
        key=msg.key(),                      # PRESERVE — needed for ordered replay
        value=msg.value(),                  # PRESERVE — byte-identical original
        headers=list(headers.items()),
    )
    producer.flush()
```

**Operational requirements to state:**

- **Long retention** — weeks, not the usual 7 days. You need time to notice, fix, and replay. A DLQ
  that expires before anyone looks at it is worse than no DLQ, because it creates false confidence.
- **Restrict read access if payloads contain PII.** A DLQ is a durable copy of production data with
  looser access controls than the source — it's a common compliance gap.
- **Never mutate the payload.** Put all diagnostics in headers so the value stays replayable as-is.
- **One DLQ per source topic** (not one global DLQ) so replay targets are unambiguous.

---

### Q7. How do you reprocess messages from a DLQ?

**Fix the root cause first.** Replaying into the same bug just re-fills the DLQ and wastes a
maintenance window. Establish *why* the messages failed — a code bug, bad producer data, a schema
mismatch, or a downstream that was down — before touching anything.

**Then run a controlled replay job:**

```python
def replay_dlq(dlq_topic, limit=1000, dry_run=True, error_filter=None):
    consumer = Consumer({..., "group.id": "dlq-replayer",
                         "enable.auto.commit": False,
                         "auto.offset.reset": "earliest"})
    consumer.subscribe([dlq_topic])
    replayed = skipped = 0

    while replayed + skipped < limit:
        msg = consumer.poll(5.0)
        if msg is None:
            break
        headers = dict(msg.headers() or [])

        # Only replay the failures you actually fixed
        if error_filter and headers.get(b"x-error-class", b"").decode() != error_filter:
            skipped += 1
            consumer.commit(message=msg, asynchronous=False)
            continue

        # Guard against an infinite DLQ -> main -> DLQ loop
        replays = int(headers.get(b"x-replay-count", b"0"))
        if replays >= 3:
            log.error("giving up on %s after %d replays", msg.key(), replays)
            skipped += 1
            consumer.commit(message=msg, asynchronous=False)
            continue

        origin = headers[b"x-origin-topic"].decode()
        if not dry_run:
            headers[b"x-replay-count"] = str(replays + 1).encode()
            producer.produce(origin, key=msg.key(), value=msg.value(),
                             headers=list(headers.items()))
            producer.flush()
            consumer.commit(message=msg, asynchronous=False)
        replayed += 1

    log.info("replayed=%d skipped=%d dry_run=%s", replayed, skipped, dry_run)
```

**The essential safeguards:**

1. **Dry run first.** Count and inspect before you publish anything.
2. **Filter by error class.** If you fixed the `ValidationError` bug, replay only those — leave the
   `TimeoutError` ones alone.
3. **A replay counter with a cap.** Without it you can build an infinite loop:
   **DLQ → main → fails → DLQ → …**. This is a real incident pattern.
4. **Replays must be idempotent** — some messages may have *partially* succeeded before failing.
5. **Preserve the key** so ordering is maintained on the replay.
6. **Rate-limit the replay.** Dumping 100,000 messages back onto a live topic can overwhelm the
   consumers currently handling real-time traffic. Throttle it.
7. **Track outcomes** — how many replayed, how many succeeded, how many bounced back.

**Alternative for small volumes:** replay **directly into the handler** rather than back through
Kafka. Fewer moving parts and no risk of a loop, but it bypasses whatever else consumes that topic.

---

### Q8. What is consumer idempotency and why is it essential?

An **idempotent consumer produces the same outcome whether it processes a message once or ten
times**.

**It is not optional, because with at-least-once delivery duplicates are guaranteed**, not
hypothetical. The sources:

1. **A crash between processing and commit** — the window from
   [Deep Dive 14 Q2](14_kafka_pipelines_delivery_semantics.md#q2-show-at-most-once-and-at-least-once-consumers-in-python).
2. **A rebalance mid-batch** — the new owner reprocesses from the last commit. **This happens on
   every single deploy.**
3. **Producer retries without idempotence** — the same record written twice.
4. **DLQ replays** — deliberate reprocessing.
5. **Upstream producing the same business event twice** — an HTTP client retry, for example.

Sources 2 and 4 alone make duplicates a certainty in any real deployment. Idempotency is what turns
**at-least-once into effectively-once**, and it's far cheaper than Kafka transactions.

**The test to apply to any handler:** "if this runs twice with the same input, is the outcome the
same?" `balance = balance + amount` fails that test. `balance = <computed value>` passes it. Sending
an email fails it (the customer gets two) unless you record that you sent it.

---

### Q9. Show techniques for implementing an idempotent consumer.

**1. Natural idempotency** — make the operation inherently repeatable. Best where it applies, because
there's no extra state to manage.

```sql
-- Upsert keyed by a business ID
INSERT INTO orders (order_id, status, amount)
VALUES (%s, %s, %s)
ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status, amount = EXCLUDED.amount;
```

Prefer **set-state** operations over **increments**. `SET status = 'PAID'` is idempotent;
`balance = balance + 100` is not.

**2. A processed-events table** — the general-purpose solution. Insert the event ID **in the same
transaction** as the business change; a unique-constraint violation means "already done".

```python
def handle(conn, event):
    with conn:                                   # ONE transaction — this is the whole trick
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO processed_events (event_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (event["event_id"],),
        )
        if cur.rowcount == 0:
            return "duplicate - skipped"         # the ID was already there
        cur.execute(
            "UPDATE accounts SET balance = balance + %s WHERE id = %s",
            (event["amount"], event["account_id"]),
        )
    return "applied"
```

**Both statements are in one transaction**, which is what makes it correct: you cannot record the
event as processed without the business change also committing, or vice versa. Doing the dedupe check
in Redis and the update in Postgres re-introduces exactly the dual-write problem you're solving.

**Housekeeping:** the table grows forever. Partition by date and drop old partitions, or purge rows
older than your maximum replay window.

**3. Redis `SET NX`** — fast, but **weaker**. It is not transactional with your database, so you can
set the key and then have the DB write fail, permanently skipping the event.

```python
if not redis.set(f"processed:{event_id}", "1", nx=True, ex=86400):
    return "duplicate"
process(event)                    # if THIS fails, the key is already set -> event lost
```

Use it as a **fast pre-filter** in front of a proper check, or where losing an occasional event is
acceptable. Don't present it as the primary mechanism.

**4. Version checks (optimistic concurrency)** — apply only if the event is newer than what you have.
This also handles **out-of-order** delivery, which the other techniques don't.

```sql
UPDATE orders SET status = %s, version = %s
WHERE order_id = %s AND version < %s;      -- 0 rows affected = stale or duplicate, ignore
```

**Choosing:** natural idempotency where the data model allows; processed-events table as the general
answer; version checks when events can arrive out of order; Redis only as an optimisation.

---

### Q10. Which ID should you deduplicate on — Kafka offset or event ID?

**A producer-assigned business event ID (a UUID) carried in the payload or a header.** Not
`(topic, partition, offset)`.

**Why the offset fails:**

- `(topic, partition, offset)` identifies **one physical copy of one record**. If the same business
  event is published twice — a producer retry without idempotence, an outbox relay double-publish, an
  upstream HTTP retry — you get **two different offsets** for the same event, and offset-based
  deduplication treats them as distinct. It doesn't dedupe the case you most need it to.
- **A DLQ replay republishes at a new offset**, so offset-based dedupe lets the replay through as if
  it were new.
- **Partition reassignment** after increasing the partition count changes the coordinates.
- **Cross-cluster replication** (MirrorMaker) does not preserve offsets.

**The event ID is generated once, at the source, and travels with the event forever.** It survives
replays, republishing, partition changes and cluster migrations.

```python
# Producer — generate ONCE at the point the event actually occurs
event = {
    "event_id": str(uuid.uuid4()),          # the deduplication key, for all time
    "event_type": "OrderPlaced",
    "order_id": order.id,
    "occurred_at": datetime.utcnow().isoformat(),
    "payload": {...},
}
```

**The critical detail:** generate it **where the business event happens** — inside the same DB
transaction as the order insert (see the
[outbox pattern](14_kafka_pipelines_delivery_semantics.md#q13-what-is-the-transactional-outbox-pattern)).
Generating a fresh UUID in the *producing* code path means a retry of that path produces a **new**
ID, and deduplication silently stops working.

`(topic, partition, offset)` is still worth putting in the DLQ headers — as **provenance for
debugging**, not as a dedupe key.

---

### Q11. What happens to ordering when you use retry topics?

**Ordering is broken, and you must say so before being asked.** This is the central trade-off of the
pattern, and volunteering it is what marks you as having actually operated one.

The scenario: message A (key `order-1`) fails and moves to `orders.retry.1m`. Messages B and C for
the **same key** arrive on the main topic and are processed **immediately**. A is retried a minute
later. So the processing order is **B, C, A** — not A, B, C.

For an order lifecycle (`CREATED` → `PAID` → `SHIPPED`) that can produce nonsense: you process
`SHIPPED` before `PAID`.

**The options, with their costs:**

**1. Accept it.** For many workloads (notifications, analytics, search indexing) order genuinely
doesn't matter. **This is the right answer more often than people assume** — check before adding
complexity.

**2. Block and retry in place for that key.** Preserves order, but reintroduces head-of-line blocking
(Q3). Sometimes correct for a low-volume, order-critical topic.

**3. Park the whole key.** Keep an "in-retry" set of keys; when a message for a key currently in
retry arrives on the main topic, route **it** to the retry path too. Order is preserved *per key*,
and other keys keep flowing.

```python
IN_RETRY = set()          # in production: Redis, shared across consumer instances

def handle(msg):
    key = msg.key()
    if key in IN_RETRY:
        route_to_retry_topic(producer, msg)    # keep this key's events together
        return
    try:
        process(msg)
    except Transient:
        IN_RETRY.add(key)
        route_to_retry_topic(producer, msg)
```

The cost: shared state across consumers (Redis), and you must remove the key once its retries drain —
including on final DLQ. Getting the cleanup wrong parks a key forever.

**4. Design events to be commutative or versioned.** Make ordering irrelevant: carry a version or
timestamp and apply only if newer (Q9, technique 4), or use set-state rather than delta events. This
is the most robust answer and the one to lead with in a design discussion — **the best fix for an
ordering problem is often to not need ordering.**

---

### Q12. How do you handle deserialisation errors in `confluent-kafka-python`?

**With a plain `Consumer`** you get raw bytes and deserialise yourself, so it's an ordinary
`try/except`:

```python
msg = c.poll(1.0)
try:
    event = json.loads(msg.value())
except (json.JSONDecodeError, UnicodeDecodeError) as e:
    send_to_dlq(producer, msg, e, group)      # can't parse -> definitively poison
    c.commit(message=msg, asynchronous=False)
    continue
```

**With `DeserializingConsumer` or the Schema Registry deserialisers**, failures surface as exceptions
from `poll()` itself — typically `ValueDeserializationError` / `ConsumeError` — which **carry the raw
message**, so you can still route the original bytes to the DLQ:

```python
from confluent_kafka.error import ConsumeError, ValueDeserializationError

try:
    msg = consumer.poll(1.0)
except ValueDeserializationError as e:
    raw = e.kafka_message                     # the undecoded original
    send_to_dlq(producer, raw, e, group)
    consumer.commit(message=raw, asynchronous=False)
    continue
```

**Deserialisation failures are always permanent** — bytes that don't match the schema today won't
match tomorrow. Straight to the DLQ, never to a retry topic.

**The causes, and the real fix:** a producer using an incompatible schema, a non-Avro message on an
Avro topic, corruption, or a schema deleted from the registry. **The fix is upstream** — Schema
Registry with `BACKWARD` compatibility enforcement and `auto.register.schemas=false` in production.
See [Deep Dive 16](16_kafka_schema_management.md).

**One practical tip:** log the **first 100 bytes** of the failing payload (hex or repr). The Confluent
wire format starts with magic byte `0` + a 4-byte schema ID, so you can immediately tell whether it's
a framing problem, a plain-JSON message on an Avro topic, or genuine corruption.

---

### Q13. How do you prevent a retry storm on a failing downstream?

When a downstream goes fully down, **every** message fails, so every message gets retried — and your
retry traffic **multiplies** load on a service that's already unhealthy, delaying its recovery. You
also flood your retry topics and DLQ with messages that would succeed fine in ten minutes.

**The layered defence:**

1. **Exponential backoff with jitter** — see
   [Scaling Q7](12_scaling_applications.md#q7-how-do-you-implement-retry-with-exponential-backoff).
   Without jitter, every retry fires simultaneously.

2. **Cap attempts and total elapsed time.**

3. **A circuit breaker that pauses consumption.** This is the Kafka-specific move and the best answer
   to this question: when the error rate crosses a threshold, **`pause()` all partitions** instead of
   consuming and failing.

```python
from collections import deque
import time

class ConsumerCircuitBreaker:
    def __init__(self, threshold=0.5, window=60, probe_after=30):
        self.results = deque()              # (timestamp, ok?)
        self.threshold, self.window = threshold, window
        self.probe_after = probe_after
        self.opened_at = None

    def record(self, ok):
        now = time.time()
        self.results.append((now, ok))
        while self.results and now - self.results[0][0] > self.window:
            self.results.popleft()

    def should_pause(self):
        if self.opened_at:
            if time.time() - self.opened_at > self.probe_after:
                self.opened_at = None       # half-open: let one batch through to probe
                return False
            return True
        if len(self.results) >= 20:
            failures = sum(1 for _, ok in self.results if not ok)
            if failures / len(self.results) > self.threshold:
                self.opened_at = time.time()
                return True
        return False

# In the poll loop:
if breaker.should_pause():
    c.pause(c.assignment())
    metrics.gauge("consumer.circuit_open", 1)
else:
    c.resume(c.assignment())
    metrics.gauge("consumer.circuit_open", 0)
msg = c.poll(1.0)                           # KEEP POLLING — stays in the group while paused
```

**Why pausing beats retrying, in three points:**

- **It preserves order** — nothing is diverted to retry topics, so the sequence is untouched.
- **It avoids flooding the DLQ** during an outage with messages that aren't actually poison.
- **The backlog is safe in Kafka.** The messages are still in the log; you resume and catch up when
  the downstream recovers. That's Kafka's core advantage over a queue that deletes on read.

4. **Rate-limit calls to the downstream** so you never exceed its known capacity.

5. **Alert on the open circuit.** A silently paused consumer is an invisible outage — lag grows and
   nobody knows why.

---

### Q14. How do you monitor failure handling in production?

**Metrics** — what to emit and alert on:

| Metric | Alert threshold | Why |
|---|---|---|
| **Consumer lag** per topic/partition | > 10,000 msgs or > 10 min | The leading indicator of everything |
| **Processing error rate** by error class | > 1% for 5 min | Distinguishes a transient blip from a bug |
| **Retry topic throughput** | Sudden rise | A downstream is degrading |
| **Retry topic depth** | Growing | Retries aren't draining |
| **DLQ throughput** | **> 0** | Poison messages — **always** alert |
| **DLQ depth** | > 0 and rising | Unaddressed failures accumulating |
| **Retry attempt histogram** | Shifting right | Downstream getting slower |
| **End-to-end latency** (produced → processed) | p99 > SLA | What the business actually feels |
| **Circuit breaker state** | Open | A paused consumer is an invisible outage |
| **Rebalance rate** | > a few per hour | Consumers being evicted — check `max.poll.interval.ms` |

```python
from prometheus_client import Counter, Histogram, Gauge

MESSAGES   = Counter("kafka_messages_total", "", ["topic", "result"])
ERRORS     = Counter("kafka_errors_total", "", ["topic", "error_class"])
E2E_LATENCY = Histogram("kafka_e2e_seconds", "produced->processed", ["topic"])
LAG        = Gauge("kafka_consumer_lag", "", ["topic", "partition"])

def report_lag(consumer, partitions):
    committed = consumer.committed(partitions)
    for i, tp in enumerate(partitions):
        _, high = consumer.get_watermark_offsets(tp)
        lag = high - (committed[i].offset or 0)
        LAG.labels(tp.topic, tp.partition).set(lag)
```

**Logging** — every log line for a message must carry the **event ID**, the origin
topic/partition/offset, the consumer group, and the attempt count. Use a `ContextVar` so it's
attached automatically rather than threaded through every function (see
[Framework development Q3](11_python_framework_development.md#q3-how-do-you-build-custom-middleware-in-fastapi)).

**Consumer lag is the single most important metric.** It tells you whether you're keeping up, and
**if lag exceeds the retention window you lose data permanently** — the messages are deleted before
you read them. Alert on it in *both* message count and time-behind, because 10,000 messages means
something different on a 10/s topic than on a 10,000/s one.

**Tooling:** `kafka-consumer-groups --describe`, Burrow (lag-specialised), the Prometheus JMX
exporter, CloudWatch for MSK, Confluent Control Center. Dashboards in Grafana.

---

## Worked example — complete consumer: classify → retry topic or DLQ, idempotent handler

Everything in this deep dive, in one piece.

```python
import json, logging, traceback, time
from confluent_kafka import Consumer, Producer

log = logging.getLogger("orders")

class Transient(Exception): pass           # timeout, 503, DB deadlock
class Permanent(Exception): pass           # validation failure, unknown entity

MAX_INLINE = 3                             # short in-memory retries for brief blips
GROUP = "orders-svc"

p = Producer({"bootstrap.servers": "kafka:9092", "enable.idempotence": True})
c = Consumer({
    "bootstrap.servers": "kafka:9092",
    "group.id": GROUP,
    "enable.auto.commit": False,
    "partition.assignment.strategy": "cooperative-sticky",
})
# One consumer serves the main topic AND the retry tiers
c.subscribe(["orders", "orders.retry.1m", "orders.retry.10m"])

def attempt_of(msg):
    return int(dict(msg.headers() or []).get("x-attempt", b"0"))

while running:
    msg = c.poll(1.0)
    if msg is None or msg.error():
        continue

    try:
        event = json.loads(msg.value())        # may raise -> poison pill

        for i in range(MAX_INLINE):            # short inline retries: sub-second only
            try:
                process_idempotently(event)    # dedupes on event["event_id"]
                break
            except Transient:
                if i == MAX_INLINE - 1:
                    raise                      # exhausted -> escalate to a retry topic
                time.sleep(0.2 * 2 ** i)

    except Transient as e:
        # Downstream is struggling: hand off to the next delay tier, don't block the partition
        route_failure(p, msg, e, attempt_of(msg))

    except (Permanent, json.JSONDecodeError, KeyError, ValueError) as e:
        # Will never succeed: park it with full diagnostics
        send_to_dlq(p, msg, e, GROUP, attempt_of(msg))

    except Exception as e:
        # Unknown: treat as poison so it can't wedge the partition, but alert loudly
        log.exception("UNEXPECTED error, routing to DLQ")
        send_to_dlq(p, msg, e, GROUP, attempt_of(msg))

    p.poll(0)                                   # serve delivery callbacks
    c.commit(message=msg, asynchronous=False)   # ALWAYS advance — in every branch
```

**The five decisions worth narrating:**

1. **One consumer, all tiers.** Simpler deployment than one consumer per retry topic, and the
   `x-attempt` header carries the state.
2. **Short inline retries first.** A 200 ms blip doesn't deserve a round trip through a retry topic.
   Kept well under `max.poll.interval.ms`.
3. **The commit is outside every branch.** Whatever happened, the message has been preserved
   somewhere (retry topic or DLQ) before we advance. **Never wedge a partition.**
4. **The catch-all routes to DLQ, not retry.** An unknown error retried forever is worse than one
   parked with an alert.
5. **`process_idempotently` is the load-bearing assumption.** Every path here can deliver the same
   message twice.

---

## Hands-on drills

1. Run [`04_retry_topic_dlq.py`](../06_kafka/04_retry_topic_dlq.py) — it reproduces the tier→DLQ flow
   with no broker. Then build it for real against the docker-compose cluster.
2. Produce one message with invalid JSON into a topic of 1,000 good ones. Write a consumer that
   retries forever and watch lag grow for the whole partition. Add DLQ routing and watch it drain.
3. Put `time.sleep(400)` in a handler with `max.poll.interval.ms=300000`. Observe the eviction, then
   the rebalance, then the second consumer hitting the same message. Fix it with a retry topic.
4. Implement the processed-events table. Feed the **same** message twice and confirm the balance
   changes once. Then move the dedupe to Redis and the update to Postgres, kill the process between
   them, and demonstrate the lost event.
5. Build the retry-topic router. Confirm `x-origin-topic` still names `orders` after two hops.
6. Demonstrate the ordering break: fail `order-1 CREATED`, let `PAID` and `SHIPPED` through, and show
   the processing order. Then implement the "park the whole key" fix.
7. Write the DLQ replay job with `dry_run=True`. Then remove the replay-count cap and build yourself
   an infinite DLQ→main→DLQ loop. Put the cap back.
8. Implement the consumer circuit breaker. Kill the downstream and confirm the consumer pauses rather
   than filling the DLQ, then confirm it catches up when the downstream returns.

---

## The 60-second spoken answer

> "I classify failures first, because transient and permanent need opposite responses. Transient
> gets a couple of short in-memory retries for brief blips, then a retry topic — because retrying in
> the poll loop causes head-of-line blocking for the whole partition and, if it exceeds
> `max.poll.interval.ms`, gets the consumer evicted, which starts a rebalance storm where lag grows
> while nothing is processed. So I republish to escalating delay tiers with an attempt counter in the
> headers and commit the original, and the delayed consumer uses pause/seek/resume while continuing
> to poll so it stays in the group. Permanent failures — bad JSON, failed validation — go straight to
> a DLQ with the payload byte-identical and all the diagnostics in headers: origin topic, partition,
> offset, error class, stack trace, attempt count. Then I commit, because the one thing I must never
> do is let a poison pill wedge a partition. DLQ depth above zero is always an alert. I'd flag
> upfront that retry topics break per-key ordering, since later messages for the same key overtake
> the retried one — I either accept that, park the whole key, or design the events to be versioned so
> ordering stops mattering. And all of it rests on the consumer being idempotent, because duplicates
> are guaranteed, not hypothetical — every deploy causes a rebalance. I dedupe on a producer-assigned
> event ID, not on the offset, because the offset changes on a replay, and I insert the event ID in
> the same database transaction as the business change so the two can't diverge."
