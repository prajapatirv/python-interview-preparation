# Deep Dive 18 — Queue-Based Architectures

> Runnable companion: [`07_caching_queues/03_queue_patterns.py`](../07_caching_queues/03_queue_patterns.py) —
> SQS-style worker, SNS→SQS fan-out and DLQ, all simulated with stdlib.
> Related deep dives: [Kafka core](13_kafka_core.md) ·
> [Kafka pipelines](14_kafka_pipelines_delivery_semantics.md) · [Scaling](12_scaling_applications.md) ·
> [AWS Lambda](../09_aws_lambda_streaming/README.md)

## What interviewers are actually probing

Whether you can **choose** the right messaging primitive and justify it. The trap is a candidate who
reaches for Kafka for everything (over-engineering) or SQS for everything (missing replay and
fan-out).

The second thing probed is the **dual-write problem** — "you saved to the database and then published
an event; what if the publish fails?" If you can explain the transactional outbox, you're
demonstrating that you've thought about consistency in a distributed system rather than just wiring
libraries together.

---

## Must-know points

- **Queue** (SQS, RabbitMQ) = **point-to-point**, message deleted after ack. **Broker/log** (Kafka)
  = **pub/sub with retention and replay**.
- **SNS + SQS fan-out** gives one event to N independent consumers, each with its own retry and DLQ.
- **DLQ** after `maxReceiveCount` attempts. **Monitor its depth; alert on non-zero.**
- **Visibility timeout** must exceed your processing time, or the message is redelivered while you're
  still working on it.
- **Outbox pattern** solves the dual-write problem: DB write and event row in one transaction.
- **CQRS** separates the write model from read-optimised projections.

---

## Interview questions and full answers

### Q1. What is the difference between a message queue and a message broker?

**A message queue** (SQS, RabbitMQ, Celery+Redis) is **point-to-point**:

- One producer, one logical consumer group.
- A message is **deleted once acknowledged** — it's gone.
- Consumers compete for messages; each is processed once (at-least-once).
- **No replay.** Once consumed, it's unrecoverable.
- Ordering is usually **best-effort** (SQS Standard) unless you pay for FIFO.

**A message broker / log** (Kafka, EventBridge, Pulsar) supports **publish-subscribe**:

- One producer, **many independent consumers**, each tracking its own position.
- Messages are **retained by policy**, not deleted on read.
- **Replay** by resetting an offset — the log is a durable record.
- **Ordering guaranteed** within a partition.

```
QUEUE (point-to-point)              LOG / BROKER (pub-sub)

producer → [ msg ] → consumer       producer → [0][1][2][3][4] (retained)
             ↑ deleted                             ↑    ↑    ↑
             after ack                       group A  group B  group C
                                             (each at its own offset)
```

**The decision rule:**

- **Queue for task offloading** — "do this work, once, somewhere else". Send an email, generate a
  PDF, resize an image. You don't care about history.
- **Log for event streaming** — "this happened; whoever cares can react". Multiple consumers, replay,
  and the ability to add a **new** consumer later that reads the whole history.

**The question that decides it:** *"Will a second consumer ever need this data, or might I need to
replay it?"* If yes, use a log. If it's genuinely one-and-done work, a queue is simpler, cheaper and
operationally far lighter.

**Say this, because over-engineering is the failure mode here:** Kafka is operationally heavy.
For a single-consumer background job, SQS or Celery is the right call, and choosing it is a strength,
not a limitation.

---

### Q2. AWS SQS vs SNS vs Kafka — when do you use which?

| Service | Pattern | Retention | Fan-out | Ordering | Best for |
|---|---|---|---|---|---|
| **SQS Standard** | Queue (P2P) | Up to 14 days | No | **Best-effort** | Task offloading, worker queues |
| **SQS FIFO** | Ordered queue | Up to 14 days | No | **Strict** per group | Ordered tasks, dedup (300–3,000 msg/s) |
| **SNS** | Pub/sub (push) | **None** | **Yes** (SQS, Lambda, HTTP, email) | No | Notifications, broadcast |
| **SNS + SQS** | Pub/sub + queuing | Queue TTL | **Yes** | Per queue | **Fan-out to multiple processors** |
| **Kafka / MSK** | Event streaming | Days → forever | Yes (consumer groups) | Per partition | High throughput, replay, analytics |
| **EventBridge** | Event bus (rules) | None | Yes | No | AWS service integration, scheduling |

**The critical points:**

1. **SNS alone has no durability.** If a subscriber is down when the message is published, **it is
   lost**. SNS retries HTTP endpoints for a while, but there's no buffer. This is why
   **SNS → SQS** is the standard pattern rather than SNS → Lambda directly: the queue absorbs the
   outage.

2. **SQS Standard is at-least-once and unordered** — duplicates are explicitly possible and messages
   can arrive out of order. **SQS FIFO** gives exactly-once processing and strict ordering per message
   group, but caps at 300 msg/s (3,000 with batching) and costs more.

3. **Kafka's differentiator is retention and replay.** Add a new consumer group six months later and
   it can read everything from the beginning. No queue can do that. If "we'll want to reprocess this
   history with new logic" is even plausible, that's the deciding factor.

4. **EventBridge for AWS-native glue** — routing based on event content, scheduled rules,
   third-party SaaS integrations. Weaker throughput than Kafka, far less operational burden.

**A concrete framing for the answer:** "For an order placement that triggers billing, inventory,
notification and analytics, I'd use **SNS + SQS fan-out** if we're AWS-native and don't need
replay — each consumer gets its own queue, retry policy and DLQ. I'd use **Kafka** if we need replay,
if analytics wants to reprocess history, or if throughput is in the hundreds of thousands per second.
For a single 'send this email' task, plain **SQS** or Celery."

---

### Q3. How do you implement an SQS worker in Python?

```python
import boto3, json, logging

sqs = boto3.client("sqs")
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/123/order-queue"
log = logging.getLogger(__name__)

def process_messages():
    while True:
        resp = sqs.receive_message(
            QueueUrl=QUEUE_URL,
            MaxNumberOfMessages=10,        # batch — max allowed
            WaitTimeSeconds=20,            # LONG POLLING — see below
            VisibilityTimeout=60,          # hidden from other consumers for 60s
            AttributeNames=["ApproximateReceiveCount"],
        )

        entries_to_delete = []
        for msg in resp.get("Messages", []):
            receive_count = int(msg["Attributes"]["ApproximateReceiveCount"])
            try:
                body = json.loads(msg["Body"])
                process_order(body)                       # MUST be idempotent
                entries_to_delete.append({
                    "Id": msg["MessageId"],
                    "ReceiptHandle": msg["ReceiptHandle"],
                })
            except PermanentError as e:
                log.error("poison message, letting it reach the DLQ: %s", e)
                # Do NOT delete -> visibility timeout expires -> redelivered
                # -> after maxReceiveCount, SQS moves it to the DLQ automatically
            except Exception as e:
                log.warning("attempt %d failed: %s", receive_count, e)
                # Same: leave it for redelivery

        if entries_to_delete:
            sqs.delete_message_batch(QueueUrl=QUEUE_URL, Entries=entries_to_delete)
```

**The details that matter:**

1. **`WaitTimeSeconds=20` — long polling.** Without it (short polling), you poll continuously,
   getting empty responses and **paying for every request**. Long polling waits up to 20 s for a
   message, which cuts cost dramatically **and** reduces latency (you're notified as soon as a message
   arrives rather than on your next poll). Always set it.

2. **`VisibilityTimeout` must exceed your processing time.** While a message is invisible, no other
   consumer sees it. If processing takes 90 s and the timeout is 60 s, **another worker picks up the
   same message at 60 s** and you process it twice concurrently. For variable processing time, extend
   it while working:

```python
sqs.change_message_visibility(
    QueueUrl=QUEUE_URL, ReceiptHandle=msg["ReceiptHandle"], VisibilityTimeout=300
)
```

3. **Delete only after successful processing.** That's what makes it at-least-once. Deleting first
   would be at-most-once — the same distinction as
   [Kafka's commit placement](14_kafka_pipelines_delivery_semantics.md#q2-show-at-most-once-and-at-least-once-consumers-in-python).

4. **`delete_message_batch`** — one API call per 10 messages instead of 10. Meaningful cost and
   latency saving at volume.

5. **`ApproximateReceiveCount`** tells you how many times this message has been delivered — use it to
   decide whether to give up early, and to log why something is looping.

6. **`process_order` must be idempotent.** SQS Standard is explicitly at-least-once; duplicates are a
   documented behaviour, not an edge case.

**The alternative worth mentioning: Lambda with an SQS event source.** AWS polls for you, scales the
concurrency automatically, and handles deletion on success. No worker loop, no long-polling
configuration, no scaling logic. For most SQS workloads this is the better answer — see
[`09_aws_lambda_streaming/`](../09_aws_lambda_streaming/).

---

### Q4. What is the SNS + SQS fan-out pattern and why use it?

**SNS delivers one message to multiple SQS queues in parallel.** Each queue has its own consumer, its
own visibility timeout, its own retry policy and its own DLQ.

```
                    ┌──────────────┐
                    │ SNS topic    │
   order-service ──>│ order-events │
                    └──┬───┬───┬───┘
            ┌──────────┘   │   └──────────┐
            ▼              ▼              ▼
     ┌────────────┐ ┌─────────────┐ ┌──────────────┐
     │ billing-q  │ │ inventory-q │ │ analytics-q  │
     └─────┬──────┘ └──────┬──────┘ └──────┬───────┘
           ▼               ▼               ▼
     billing-svc     inventory-svc    analytics-svc
     (own DLQ)       (own DLQ)        (own DLQ)
```

```python
import boto3, json

sns = boto3.client("sns")
sns.publish(
    TopicArn=ORDER_EVENTS_ARN,
    Message=json.dumps({"order_id": "1", "total": 200}),
    MessageAttributes={
        "event_type": {"DataType": "String", "StringValue": "OrderPlaced"},
    },
)
```

**The benefits, each concrete:**

1. **Decoupling.** Adding a fourth consumer means creating a queue and a subscription — **the
   producer doesn't change and isn't redeployed**. That's the entire point.
2. **Independent failure.** If analytics is down, its queue backs up. Billing and inventory are
   unaffected. With a single shared queue, one slow consumer starves the others.
3. **Per-consumer tuning.** Billing needs a 300 s visibility timeout and 5 retries; analytics needs
   30 s and 2. Separate queues make that trivially configurable.
4. **Per-consumer DLQs**, so you know *which* consumer failed on *which* message.
5. **Buffering.** The queue absorbs a consumer being redeployed or scaled down.

**Message filtering** is the feature that makes this much more useful — a subscription filter policy
means a queue only receives events it cares about, so consumers don't waste effort discarding
messages:

```json
{"event_type": ["OrderPlaced", "OrderCancelled"]}
```

**Two gotchas:**

- **Raw message delivery.** By default SNS **wraps** the payload in an SNS envelope, so your consumer
  must unwrap `json.loads(body)["Message"]`. Enable `RawMessageDelivery=true` on the subscription to
  get the payload directly — otherwise every consumer needs unwrapping logic.
- **The 256 KB message size limit** (both SNS and SQS). For larger payloads use the **claim check
  pattern**: store the payload in S3 and send the key. The Extended Client Library does this
  automatically in Java; in Python you do it yourself.

**Versus Kafka:** SNS+SQS gives you fan-out but **no replay** — a new consumer added tomorrow sees
only new messages. Kafka's consumer groups give you fan-out **and** the full history. That's the
deciding question.

---

### Q5. How does a dead-letter queue work in production?

A **DLQ** is a secondary queue receiving messages that couldn't be processed after
`maxReceiveCount` attempts. It captures poison pills **without losing them** and — critically —
**without blocking the main queue**.

**The SQS redrive policy:**

```json
{
  "deadLetterTargetArn": "arn:aws:sqs:us-east-1:123:order-queue-dlq",
  "maxReceiveCount": 5
}
```

After 5 deliveries without a successful delete, SQS moves the message to the DLQ automatically. No
application code required — that's the advantage over Kafka, where you
[build it yourself](15_kafka_failure_handling.md#q4-explain-the-retry-topic-pattern).

**The operational practice, which is what the question is really about:**

```python
import boto3, json, logging

log = logging.getLogger(__name__)
s3 = boto3.client("s3")

def handler(event, ctx):
    """Lambda triggered by the DLQ — inspect, archive and alert."""
    for record in event["Records"]:
        body = json.loads(record["body"])
        log.critical("DLQ message: %s", body)

        send_slack_alert(f":fire: DLQ message on order-queue: {body}")

        # Archive for analysis and replay
        s3.put_object(
            Bucket="dlq-archive",
            Key=f"orders/{ctx.aws_request_id}.json",
            Body=json.dumps({"body": body, "attributes": record.get("attributes", {})}),
        )
```

**The practices that matter:**

1. **Alert on DLQ depth > 0.** Not on a threshold — on **any** message. A DLQ message means something
   is broken. A DLQ nobody watches is just a slower way to lose data.
2. **Set the DLQ retention to the maximum (14 days).** You need time to notice, fix and replay.
3. **Set `maxReceiveCount` deliberately.** Too low (1–2) and a transient blip sends good messages to
   the DLQ. Too high (50) and a poison pill is retried for hours, wasting capacity. **3–5 is the
   usual range.**
4. **Have a redrive process.** AWS's built-in **DLQ redrive** moves messages back to the source queue
   from the console or API — but **fix the root cause first**, or they'll bounce straight back.
5. **Give the DLQ its own DLQ?** No — but **do** cap the redrive attempts, or you build a DLQ → main
   → DLQ loop.
6. **Watch for PII.** A DLQ is a durable copy of production data, often with looser access controls
   than the source. This is a common compliance gap.

**A `maxReceiveCount` subtlety:** the counter increments on *delivery*, not on *failure*. A worker
that crashes without processing anything still increments it. So a pod being OOM-killed repeatedly
can push perfectly good messages into the DLQ.

---

### Q6. How do you implement an outbox pattern to guarantee event publishing?

**The dual-write problem**: you need to save to the database **and** publish an event. There is no
transaction spanning both.

```python
# BROKEN — two writes, no atomicity
async def place_order(order):
    await db.save(order)                    # succeeds
    await kafka.publish("order.placed", order)   # CRASHES HERE
    # Result: an order exists in the DB with no event. Billing never runs.
    # Reversing the order is equally broken: an event for an order that was rolled back.
```

**The outbox pattern** makes it one write: put the event in an `outbox` table **in the same local
database transaction** as the business data. A separate relay publishes it.

```python
# 1. ONE database transaction — atomic by construction
async with db.begin():
    order = Order(user_id=uid, total=200)
    db.add(order)
    db.add(OutboxEvent(
        aggregate_id=order.id,
        event_type="OrderPlaced",
        payload=json.dumps({"order_id": order.id, "total": 200}),
        published=False,
    ))
# Either BOTH rows exist or NEITHER does. No third state.

# 2. A separate relay publishes them
async def outbox_relay():
    while True:
        events = await (db.query(OutboxEvent)
                          .filter_by(published=False)
                          .order_by(OutboxEvent.id)        # preserve insertion order
                          .limit(100).all())
        for evt in events:
            producer.produce("orders", key=str(evt.aggregate_id), value=evt.payload)
        producer.flush()                                   # confirm delivery FIRST
        for evt in events:
            evt.published = True
        await db.commit()                                  # then mark published
        await asyncio.sleep(1)
```

**Why it works:** the database transaction is the **single source of atomicity**. The relay may
publish twice (if it crashes after `flush()` but before the commit), so the guarantee is
**at-least-once** — which is why consumers must be idempotent. **But nothing is ever lost**, which is
the property you actually need.

**Note the ordering in the relay:** `flush()` **before** marking published. The reverse would mark
events published that never reached Kafka — silent data loss.

**The production version uses CDC rather than polling.** **Debezium** reads the database's
write-ahead log and streams outbox inserts to Kafka:

- **No polling load** on the database.
- **Lower latency** — milliseconds, not the poll interval.
- **No application code** in the relay path.
- **Ordering follows the WAL**, which is authoritative.

**Operational notes:** index on `(published, id)`; **purge published rows** on a schedule or the table
grows unbounded; and if you run multiple relay instances, use `SELECT ... FOR UPDATE SKIP LOCKED` so
they don't publish the same rows.

**The mirror-image problem** — Kafka → database — is solved by
[idempotent writes](14_kafka_pipelines_delivery_semantics.md#q10-how-do-you-achieve-exactly-once-when-the-sink-is-a-database).

---

### Q7. What is CQRS?

**Command Query Responsibility Segregation** — separate the **write model** (commands:
create/update/delete) from the **read model** (queries: optimised projections).

```python
# WRITE side — a command goes through the service, publishes an event
@app.post("/orders")
async def place_order(cmd: PlaceOrderCommand, svc=Depends(get_order_service)):
    order = Order.create(cmd)
    await order_repo.save(order)                    # normalised, transactional
    await kafka.publish("order.placed", OrderPlacedEvent.from_order(order))
    return {"id": order.id}

# READ side — a consumer maintains a denormalised projection
async def update_read_model(events):
    async for ev in events:
        view = OrderSummaryView.from_event(ev)
        await redis.hset(f"order_summary:{ev.user_id}", ev.order_id, view.json())

@app.get("/orders/summary")
async def summary(user=Depends(current_user)):
    return await redis.hgetall(f"order_summary:{user.id}")   # no joins, one round trip
```

**What it buys you:**

1. **Independent scaling.** Reads usually outnumber writes 100:1. Scale them separately.
2. **Query-optimised storage.** The write side stays normalised and transactional (PostgreSQL); the
   read side can be **Elasticsearch** for search, **Redis** for speed, or a denormalised table with
   no joins.
3. **Simpler models.** The write model enforces invariants; the read model is a dumb projection
   shaped exactly like the UI needs. Neither compromises for the other.
4. **Multiple read models** from the same events — a customer view, an ops dashboard, an analytics
   warehouse.

**The costs, which you must state** — CQRS is frequently over-applied:

1. **Eventual consistency.** A user places an order and immediately refreshes the list — the
   projection may not have caught up. You must design for it: optimistic UI updates, read-your-own-
   writes routing for the requesting user, or a "processing" state.
2. **More moving parts** — an event pipeline, a projection consumer, and a second datastore, all to
   operate and monitor.
3. **Projection rebuilds.** When the read model's shape changes, you replay the events to rebuild it.
   That's a genuine advantage of Kafka's retention — but it's an operation you must build and test.
4. **Debugging is harder** — "why is this view wrong?" spans two systems and a pipeline.

**When it's justified:** a genuine read/write asymmetry (100:1 or more), fundamentally different
query shapes (full-text search over transactional data), or multiple consumers needing different
views. **When it isn't:** ordinary CRUD. A read replica plus a cache solves the same problem with a
fraction of the complexity, and that should be your first answer.

**On event sourcing:** CQRS is often paired with it but is **independent**. Event sourcing means the
event log *is* the source of truth and current state is derived by replay. That's a much bigger
commitment — every state change is an immutable event, and you need snapshotting, versioning and a
replay story. You can do CQRS without it, and usually should.

---

## Choosing: a decision table

| Requirement | Choice |
|---|---|
| One consumer, fire-and-forget task | **SQS** or **Celery** |
| Strict ordering + deduplication, modest volume | **SQS FIFO** |
| Many independent consumers, AWS-native, no replay | **SNS + SQS fan-out** |
| Many consumers **and** replay **and** high throughput | **Kafka** |
| AWS service glue, scheduled rules, SaaS integration | **EventBridge** |
| Durable retryable tasks with scheduling, Python-native | **Celery** / **Arq** |
| Guaranteed publish alongside a DB write | **Outbox** (+ Debezium) |
| Read/write asymmetry with different query shapes | **CQRS** |

**The meta-answer to give:** "Start with the simplest thing that meets the requirement. Kafka is
powerful and operationally expensive — a cluster to run, partitions to size, consumer groups to
monitor, schemas to manage. If a single consumer is doing one-and-done work, SQS or Celery is the
right call. I'd move to Kafka when I need **replay**, **multiple independent consumers**, or
throughput a queue can't sustain."

---

## Worked example — order placement, three ways

The same requirement implemented with three different primitives, to show the trade-offs concretely.

**Requirement:** when an order is placed, bill the customer, reserve inventory, send a confirmation,
and record it for analytics.

**Option A — Celery (simplest).**

```python
@app.post("/orders")
async def place_order(order: OrderIn):
    saved = await svc.create(order)
    bill_customer.delay(saved.id)          # 4 independent durable tasks
    reserve_inventory.delay(saved.id)
    send_confirmation.delay(saved.id)
    record_analytics.delay(saved.id)
    return saved
```
✅ Simple, durable, retryable. ❌ The API **knows all four consumers** — adding a fifth means
redeploying the API. No replay. And the dual-write problem is still there: a crash after `create`
loses all four tasks.

**Option B — SNS + SQS fan-out.**

```python
@app.post("/orders")
async def place_order(order: OrderIn):
    saved = await svc.create(order)
    sns.publish(TopicArn=ORDER_EVENTS, Message=saved.json(),
                MessageAttributes={"event_type": {"DataType": "String",
                                                  "StringValue": "OrderPlaced"}})
    return saved
```
✅ The API knows **nothing** about consumers. Each has its own queue, retry policy and DLQ. Adding a
fifth is an infrastructure change only. ❌ No replay — a consumer added tomorrow sees only new
events. Dual-write problem remains.

**Option C — Outbox + Kafka (most robust).**

```python
@app.post("/orders")
async def place_order(order: OrderIn):
    async with db.begin():                          # ONE transaction
        saved = Order(**order.dict())
        db.add(saved)
        db.add(OutboxEvent(aggregate_id=saved.id, event_type="OrderPlaced",
                           payload=saved.json(), published=False))
    return saved
# Debezium CDC streams outbox rows -> Kafka -> 4 consumer groups
```
✅ **No dual write** — the event cannot be lost. **Replay** available. Multiple independent consumer
groups. Ordering per `order_id`. ❌ Most infrastructure: Kafka, Debezium, Schema Registry, plus the
monitoring for all three.

**The answer to give when asked "which would you build?"** — B for an AWS-native service with a small
number of known consumers; **C when the events have lasting value** (analytics reprocessing, audit,
new consumers over time) or when losing an event is unacceptable. A for an internal tool where
simplicity wins. The point is that **all three are defensible**, and saying which and why is the
actual answer.

---

## Hands-on drills

Run [`03_queue_patterns.py`](../07_caching_queues/03_queue_patterns.py) first — it simulates all of
this with stdlib and no AWS account.

1. Build an SQS worker with `VisibilityTimeout=30` and a handler that sleeps 60 s. Log the message ID
   and watch the same message processed twice concurrently. Fix it with
   `change_message_visibility`.
2. Run the same worker with short polling (`WaitTimeSeconds=0`) and then long polling. Count the API
   calls over a minute of an empty queue.
3. Set `maxReceiveCount=3` with a DLQ. Send a message your handler always rejects and watch it arrive
   in the DLQ after exactly 3 deliveries.
4. Set up SNS → 2 SQS queues. Stop one consumer, publish 100 messages, and confirm the other is
   unaffected and the stopped one catches up on restart. Then publish with SNS → Lambda directly and
   show the message is lost when the Lambda is throttled.
5. Add a filter policy to one subscription so it only receives `OrderCancelled`. Verify.
6. Implement the outbox with a polling relay. Kill the relay **between** `flush()` and the commit and
   confirm duplicates appear — then confirm your idempotent consumer absorbs them. Then swap the
   order (commit before flush) and demonstrate the **lost** event.
7. Build a CQRS read model in Redis fed by an event consumer. Place an order and immediately query
   the summary. Observe the eventual-consistency gap, then implement read-your-own-writes for the
   placing user.

---

## The 60-second spoken answer

> "A queue like SQS is point-to-point — the message is deleted after acknowledgement, there's no
> replay, and consumers compete. A log like Kafka retains messages by policy, so many consumer groups
> each read the full stream at their own offset and you can replay history. The question I ask is
> whether a second consumer will ever need this data or whether I might need to reprocess it; if yes,
> a log, otherwise a queue — and I'd deliberately choose SQS or Celery for a single fire-and-forget
> task rather than over-engineering with Kafka. For AWS fan-out I use SNS into several SQS queues,
> because SNS alone has no durability: if a subscriber is down when you publish, the message is gone,
> whereas the queue buffers it. Each queue then gets its own visibility timeout, retry policy and
> DLQ, so a slow analytics consumer can't starve billing. On SQS specifically I always enable long
> polling, make sure the visibility timeout exceeds worst-case processing or I'll process the same
> message twice, and delete only after success — that's what makes it at-least-once, so handlers must
> be idempotent. DLQ depth above zero is always an alert, never a dashboard. And the thing I'd raise
> unprompted is the dual-write problem: saving to the database and then publishing an event isn't
> atomic, so a crash between them loses the event. I solve that with the transactional outbox —
> the event row goes in the same DB transaction as the business data, and a relay, ideally Debezium
> reading the WAL, publishes it. That's at-least-once rather than exactly-once, but nothing is ever
> lost, which is the property that actually matters."
