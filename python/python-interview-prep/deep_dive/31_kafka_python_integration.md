# Deep Dive 31 — Kafka Configuration and Integration from Python

> Runnable companions: [`06_kafka/07_kafka_python_config.py`](../06_kafka/07_kafka_python_config.py) ·
> [`06_kafka/08_kafka_to_aurora_sink.py`](../06_kafka/08_kafka_to_aurora_sink.py)
> Prerequisites: [13 — Kafka core](13_kafka_core.md) ·
> [14 — Pipelines & delivery semantics](14_kafka_pipelines_delivery_semantics.md) ·
> [15 — Failure handling](15_kafka_failure_handling.md) · [16 — Schema management](16_kafka_schema_management.md)
> Related: [27 — Zero-downtime changes](27_zero_downtime_production_changes.md) ·
> [29 — Capacity scaling](29_capacity_scaling_tps.md)

## What interviewers are actually probing

Deep dives 13–16 cover Kafka's concepts. This one covers the question that actually gets asked in a
Python interview: *"how do you configure and integrate Kafka from Python — and how do you get messages
into Aurora without losing or duplicating rows?"*

It's a config-and-plumbing question with four specific traps, and they are *all* configuration defaults
that are wrong for real work:

1. **`enable.auto.commit=True`** (the default) silently loses messages on a crash.
2. **`acks=1`** loses acknowledged writes when a leader fails before replicating.
3. **Ignoring the delivery callback** means a failed send disappears with no error anywhere.
4. **Row-at-a-time DB writes with a plain `INSERT`** are both slow and non-idempotent, so the first
   redelivery either duplicates data or kills the consumer.

The second half is the integration question, and the whole answer is **one ordering**:

> **DB commit first, Kafka offset second — and make the write idempotent so the replay is a no-op.**

---

## Must-know points

- **Which client**: `confluent-kafka-python` (librdkafka, C, fastest, most complete) for production;
  `aiokafka` when your service is asyncio; `kafka-python` is pure-Python and slower — avoid for new work.
- **No-loss producer**: `acks=all` + `enable.idempotence=True` + a bounded `delivery.timeout.ms`, and
  **act on the delivery callback's error**.
- **`enable.idempotence=True` implies** `acks=all`, `retries>0`, `max.in.flight<=5`. It dedupes
  *broker-side retries*, nothing else. It's effectively free — leave it on.
- **No-loss consumer**: `enable.auto.commit=False` and commit **after** the work succeeds.
  `auto.offset.reset=earliest` for a new group unless skipping the backlog is deliberate.
- **`linger.ms` / `batch.size` / `compression.type`** are the throughput knobs; `linger.ms` is a pure
  latency-for-throughput trade.
- **`max.poll.interval.ms`** is the rebalance trigger: exceed it between `poll()` calls and the broker
  declares you dead. The fix is lower `max.poll.records` or faster handling — **never a sleep in the
  loop**.
- **`cooperative-sticky`** assignment gives incremental rebalances instead of stop-the-world.
- **Always `flush()` the producer and `close()` the consumer on shutdown.** `close()` leaves the group
  cleanly, so the rebalance takes milliseconds rather than a 45-second session timeout.
- **Exactly-once covers Kafka→Kafka only.** For Kafka→database you get at-least-once delivery with an
  **idempotent upsert**, which is effectively-once *effect*.
- **Aurora specifics**: writer vs reader endpoint; failover invalidates pooled connections (treat
  `OperationalError` as retryable, use `pool_pre_ping`); RDS Proxy for serverless consumers; IAM auth
  tokens expire in 15 minutes.
- **Config comes from the environment**, mapped to librdkafka keys, validated at startup so a bad
  combination fails the deploy instead of the 3am page.

---

## Interview questions and full answers

### Q1. Which Python Kafka client, and why?

| Client | Based on | Use when | Watch out for |
|---|---|---|---|
| **`confluent-kafka-python`** | librdkafka (C) | **production default** — fastest, full feature set, transactions, Schema Registry | needs a wheel/compiler; config keys are librdkafka's dotted names |
| **`aiokafka`** | pure Python, asyncio | your service is already asyncio and you want `async for` | smaller community; slower; fewer features |
| **`kafka-python`** | pure Python | legacy code, or no binary wheels available | notably slower; maintenance has been patchy |
| **Faust / Quix** | stream-processing frameworks | windowed aggregations, joins, stateful streams | a framework, not a client — adopt deliberately |

Pick `confluent-kafka` unless you're asyncio-native. The specific reason to prefer it: it's a thin
binding over librdkafka, which is the same client the Java ecosystem's semantics are defined against, so
the config keys, the idempotent-producer implementation and the transaction support all match the
documentation you'll be reading.

**The gotcha with `confluent-kafka` in an asyncio service:** `produce()` is non-blocking but `poll()` and
`flush()` block, so calling them on the event loop stalls every coroutine. Either run the producer's
`poll` loop in a thread (`loop.run_in_executor`), or use `aiokafka`. This is a real and commonly-missed
point.

---

### Q2. What's the minimum producer config for "don't lose messages"?

```python
from confluent_kafka import Producer

producer = Producer({
    "bootstrap.servers": "b-1:9092,b-2:9092,b-3:9092",   # 2-3, not 1 — it's DISCOVERY, and a
                                                          # single entry is a startup SPOF
    "client.id": "orders-service-1",                      # shows up in broker metrics — always set it
    "acks": "all",                                        # leader + all in-sync replicas
    "enable.idempotence": True,                           # dedupes broker-side retries
    "delivery.timeout.ms": 120000,                        # the REAL deadline for a message
    "linger.ms": 10,                                      # small batching window
    "compression.type": "lz4",
    "max.in.flight.requests.per.connection": 5,
})

def on_delivery(err, msg):
    if err:                                   # THE ONLY PLACE you learn a send failed
        log.error("delivery failed", topic=msg.topic(), error=str(err))
        persist_to_outbox(msg)                # do NOT just log and move on
    else:
        metrics.inc("kafka_delivered_total", topic=msg.topic())

producer.produce("orders", key=order_id.encode(), value=payload, on_delivery=on_delivery)
producer.poll(0)        # serves delivery callbacks; without this they only fire on flush()
...
producer.flush(10)      # ALWAYS before exit — blocks until every queued message is acked
```

**Why each line:**

- **`acks=all`** means the leader waits for every in-sync replica. Combined with broker-side
  `min.insync.replicas=2` and RF=3, a write survives one broker failure with zero loss. `acks=1` returns
  as soon as the leader has it — so if that leader dies before replicating, the message is gone **and you
  were told it succeeded.** Acceptable for clickstream; never for orders.
- **`enable.idempotence=True`** gives each producer a PID and a per-partition sequence number, so a
  broker drops a duplicate caused by *its own* retry. It's the fix for "acks=all plus retries can produce
  duplicates". Essentially free. Note what it does **not** cover: if your application calls `produce()`
  twice, you get two messages.
- **`delivery.timeout.ms` is the knob that matters, not `retries`.** librdkafka's `retries` defaults to
  effectively infinite; the total time a message may spend in send + retries is bounded by
  `delivery.timeout.ms`. That's the number you tune, and it must exceed
  `linger.ms + request.timeout.ms`.
- **`max.in.flight <= 5`** with idempotence on preserves ordering across retries. With idempotence *off*
  and in-flight > 1, a retried batch can land **after** a later one — the classic silent reordering bug.
- **The delivery callback is not optional.** `produce()` is asynchronous: it enqueues to librdkafka's
  internal buffer and returns. **Without the callback, a permanent send failure is invisible to your
  code** — no exception, no log. And `poll(0)` is what services those callbacks; omit it and they only
  fire at `flush()`.
- **`flush()` on shutdown.** An unflushed buffer on SIGTERM means those events are **lost, not retried**
  — see [27 — Zero-downtime changes](27_zero_downtime_production_changes.md).

**One more trap: a full local queue is backpressure.** When librdkafka's buffer fills, `produce()` raises
`BufferError`. The correct response is to `poll()` to drain and then retry — *not* to catch and drop:

```python
try:
    producer.produce(topic, value=payload, on_delivery=on_delivery)
except BufferError:
    producer.poll(1)                     # let the queue drain, then retry once
    producer.produce(topic, value=payload, on_delivery=on_delivery)
```

---

### Q3. What's the minimum consumer config, and why is the default dangerous?

```python
consumer = Consumer({
    "bootstrap.servers": "b-1:9092,b-2:9092",
    "group.id": "orders-writer",                          # change it and you re-read from scratch
    "enable.auto.commit": False,                          # <-- THE IMPORTANT ONE
    "auto.offset.reset": "earliest",                      # a new group reads the backlog
    "partition.assignment.strategy": "cooperative-sticky",
    "max.poll.interval.ms": 300000,
    "isolation.level": "read_committed",                  # ignore aborted transactions
})
consumer.subscribe(["orders"])
try:
    while True:
        msg = consumer.poll(1.0)              # never poll(0) in a tight loop — it spins the CPU
        if msg is None:
            continue
        if msg.error():
            log.error("consumer error", error=str(msg.error()))
            continue
        process(msg)                          # YOUR idempotent handler
        consumer.commit(message=msg, asynchronous=False)   # commit AFTER the work succeeded
finally:
    consumer.close()                          # leaves the group cleanly -> fast rebalance
```

**`enable.auto.commit=True` is the default and it is the #1 source of silent message loss.** The
mechanism: a background thread commits the offsets returned by the most recent `poll()` on a timer
(`auto.commit.interval.ms`, default 5s). So:

```
poll() returns messages 100-150
  ... you are 20 messages in ...
auto-committer fires and commits offset 151     <-- it committed messages you haven't processed
  ... the process crashes ...
restart: the group resumes at 151. Messages 120-150 are GONE. No error, no log, no clue.
```

Manual commit after processing turns that into at-least-once: a crash means redelivery, which is
survivable **if the handler is idempotent** (Q6).

**The other defaults worth challenging:**

- **`auto.offset.reset=latest`** means a brand-new group **silently skips the existing backlog**. For a
  consumer that must process everything, `earliest`. The related trap: changing `group.id` creates a new
  group, so a typo in a deploy re-reads the entire topic from the beginning (or skips everything, with
  `latest`) — both are production incidents.
- **`max.poll.interval.ms` (5 min)** is the rebalance trigger. If handling one `poll()`'s worth of
  messages takes longer than this, the broker declares you dead and reassigns your partitions — and you
  commit into a partition you no longer own. See Q5.
- **`isolation.level`**: `read_committed` to skip records from aborted transactions. Required if any
  producer on that topic uses transactions; a small latency cost (it waits for the commit marker).
- **`cooperative-sticky`**: the old `range`/`roundrobin` strategies do a **stop-the-world** rebalance —
  every consumer revokes everything and re-joins, so the whole group pauses. Cooperative rebalancing
  revokes only what's moving. For a group of any size, this is a significant availability difference.

---

### Q4. How do you tune for throughput versus latency?

They're opposing goals, and the honest answer is that there are four named profiles with one or two lines
differing between them:

| | throughput | low-latency | **no-loss (default)** | exactly-once |
|---|---|---|---|---|
| `acks` | `1` | `1` | **`all`** | `all` |
| `enable.idempotence` | False | False | **True** | True |
| `linger.ms` | 50 | **0** | 10 | 10 |
| `batch.size` | 256KB | default | default | default |
| `compression.type` | lz4 | **none** | lz4 | lz4 |
| `transactional.id` | — | — | — | **set, and STABLE** |

**The levers, in order of effect:**

1. **`linger.ms`** — wait this long to fill a batch. 0 is lowest latency; 20–100 means far fewer, larger
   requests. This is the single biggest throughput knob and it costs exactly that many milliseconds of
   latency.
2. **`batch.size`** — bigger batches compress better and amortise the request overhead; they cost memory
   per partition.
3. **`compression.type=lz4`** — typically 3–5× fewer network bytes for JSON at negligible CPU. `zstd` for
   the best ratio, `gzip` is the slowest. **Not setting it at all is the common mistake**; the default is
   `none`.
4. **More partitions** — consumer parallelism is capped by partition count, not by thread count. This is
   the one people forget: adding consumer instances beyond the partition count does literally nothing.

**And the config validator**, which is the thing worth demonstrating because it catches real shipped
mistakes:

```python
def validate_producer_config(cfg):
    problems = []
    idempotent = cfg.get("enable.idempotence", True)
    acks = str(cfg.get("acks", "all"))
    in_flight = int(cfg.get("max.in.flight.requests.per.connection", 5))

    if idempotent and acks not in ("all", "-1"):
        problems.append(("ERROR", "enable.idempotence requires acks=all; the client won't start"))
    if idempotent and in_flight > 5:
        problems.append(("ERROR", f"idempotence allows max.in.flight<=5, got {in_flight}"))
    if not idempotent and in_flight > 1 and int(cfg.get("retries", 1)) > 0:
        problems.append(("WARN", "retries>0 + in.flight>1 + idempotence off can REORDER messages"))
    if acks in ("0", "1"):
        problems.append(("WARN", f"acks={acks} loses acknowledged messages if the leader fails"))
    return problems
```

Run it at startup and **fail the boot on any ERROR**. A contradictory Kafka config should break the
deploy, not the 3am page — and "I validate the config at startup" is a strong, concrete thing to say.

---

### Q5. The consumer keeps rebalancing. Why, and how do you fix it?

**Because processing takes longer than `max.poll.interval.ms` between `poll()` calls.** The broker's
contract is "call `poll()` regularly or I'll assume you're dead". With `max.poll.records=500` and 1 second
of work per message, one poll's worth of work is 500 seconds — well past the 300-second default.

The failure spiral is what makes it severe: rebalance → partitions reassigned → the new owner starts from
the last *committed* offset, so it reprocesses → it's also slow, so it also times out → rebalance. The
group makes no progress while spending all its time rebalancing.

**The fixes, in the order you should try them:**

1. **Make the handler faster.** Usually the real answer: batch the DB writes (Q6), remove an N+1, cache a
   lookup. A handler that takes 1ms doesn't have this problem.
2. **Lower `max.poll.records`** (e.g. to 10–50). Fewer messages per poll means less work between polls.
   This is the correct *configuration* fix and it's reversible in seconds.
3. **Raise `max.poll.interval.ms`** — legitimate for genuinely slow work (an LLM call, a third-party API),
   but it also delays detection of a genuinely dead consumer. Raise it *and* lower `max.poll.records`.
4. **Move slow work off the poll thread.** Hand messages to a worker pool and `pause()`/`resume()` the
   partitions for backpressure. More complex, and now *you* own the commit/ordering correctness — only do
   this if 1–3 aren't enough.
5. **Never `time.sleep()` in the consume loop.** This is the classic accidental version: a retry that
   sleeps 30 seconds inside the handler blows `max.poll.interval.ms`. Delays belong in a **retry topic**,
   not in the loop — see [15 — Failure handling](15_kafka_failure_handling.md).

**The distinction worth stating:** `session.timeout.ms` (heartbeat liveness, ~45s) and
`max.poll.interval.ms` (progress liveness, ~5min) are different clocks. Since KIP-62 the heartbeat runs on
a background thread, so a slow handler keeps heartbeating but still breaches the poll interval. Diagnosing
a rebalance means knowing which one you broke.

**And the consequence to mention:** after a rebalance, `commit()` for a partition you no longer own fails
or is ignored. Any work you did for those messages will be redone by the new owner — which is survivable
only because the handler is idempotent. Everything comes back to idempotency.

---

### Q6. Kafka → Aurora: how do you avoid losing or duplicating rows?

**This is the integration question, and the answer is one ordering plus one SQL clause.**

```python
class KafkaToAuroraSink:
    """poll a BATCH -> validate (poison -> DLQ) -> ONE transaction, ONE idempotent upsert
       -> DB COMMIT -> THEN commit the Kafka offset."""

    def run(self):
        while True:
            batch = self.consumer.consume(num_messages=500, timeout=1.0)
            if not batch:
                continue
            parsed = []
            for msg in batch:
                try:
                    row = json.loads(msg.value())
                    if not row.get("event_id"):
                        raise ValueError("missing event_id")
                    parsed.append(row)
                except (json.JSONDecodeError, ValueError) as e:
                    self.dlq(msg, e)          # a poison pill must NEVER block the partition
            if parsed and not self._write_with_retry(parsed):
                break                          # DB down: do NOT commit — let it be redelivered
            self.consumer.commit(asynchronous=False)    # ONLY after the DB committed

    def _write_with_retry(self, rows, max_retries=3):
        for attempt in range(1, max_retries + 1):
            try:
                with self.pool.connection() as conn, conn.transaction():
                    execute_values(conn.cursor(), """
                        INSERT INTO orders (event_id, order_id, status, amount, updated_at)
                        VALUES %s
                        ON CONFLICT (event_id) DO NOTHING          -- THE idempotency clause
                    """, [(r["event_id"], r["order_id"], r["status"],
                           r["amount"], r["updated_at"]) for r in rows], page_size=1000)
                return True
            except OperationalError as e:       # Aurora failover / connection reset: RETRYABLE
                if attempt == max_retries:
                    return False
                time.sleep(0.05 * 2 ** (attempt - 1))
            except IntegrityError:              # a data problem, not transient — isolate the bad row
                return self._write_one_by_one(rows)
```

**The three bugs this fixes, each reproduced in the companion file:**

| Bug | What happens | The fix |
|---|---|---|
| **commit the offset first** | crash between commit and write → the row is **lost forever, silently** (also what auto-commit does to you on a timer) | DB commit, *then* offset commit |
| **plain `INSERT`** | a redelivery (normal at-least-once behaviour after any rebalance) → `IntegrityError` that kills the batch, or — with no unique index — **double-counted revenue** | `ON CONFLICT (event_id) DO NOTHING` |
| **one transaction per row** | 200 rows = 200 round trips = 0.4s of pure network wait at 2ms each; consumer lag never drains | `execute_values` — 200 rows in **one** round trip |

Measured in the companion: **5 round trips instead of 200 (40× fewer)** for the same data, with three
redelivered duplicates absorbed silently and two unparseable messages routed to the DLQ.

**Why the ordering gives you "exactly once" in practice:** a crash between the DB commit and the offset
commit means the batch is redelivered — and the upsert makes the replay a **no-op**. That's at-least-once
*delivery* with effectively-once *effect*, which is what people actually mean by exactly-once for a
Kafka→DB sink.

**Why Kafka transactions do NOT help here, and this is the key insight:** `transactional.id` +
`read_committed` gives atomicity across *Kafka* reads and writes. It cannot span Kafka and Aurora — there
is no two-phase commit between them, and you should not want one. **The idempotent write is what makes
the replay harmless**, and it's cheaper and more robust than any distributed transaction.

**One refinement on the upsert.** `DO NOTHING` on `event_id` is right for append-only events. For
last-write-wins updates you need a guard, or a replayed *old* event will overwrite a *newer* one:

```sql
ON CONFLICT (order_id) DO UPDATE
   SET status = EXCLUDED.status, updated_at = EXCLUDED.updated_at
 WHERE orders.updated_at < EXCLUDED.updated_at     -- never let an old event win
```

---

### Q7. What's Aurora-specific about this?

Five things, and they're the difference between "I've read about RDS" and "I've operated it":

**1. Two endpoints, and using the wrong one is the most common mistake.**

```
writer: my-cluster.cluster-xxxx.ap-south-1.rds.amazonaws.com        <- all INSERT/UPDATE
reader: my-cluster.cluster-ro-xxxx.ap-south-1.rds.amazonaws.com     <- read replicas only
```

A sink writes to the **writer** endpoint. Point it at the reader and every write fails with *"cannot
execute INSERT in a read-only transaction"*. Note the writer endpoint is a DNS CNAME that **moves on
failover** — which is why you must never cache the resolved IP.

**2. Failover takes 30–60s and invalidates pooled connections.** The DNS record flips, but an already-open
socket does not. So:

```python
# SQLAlchemy
engine = create_engine(dsn, pool_size=10, max_overflow=5,
                       pool_pre_ping=True,    # validate before handing out a connection
                       pool_recycle=300)      # don't keep sockets across a likely failover
# psycopg3
pool = ConnectionPool(dsn, min_size=2, max_size=10, timeout=5, max_lifetime=600)
```

And **treat `OperationalError` as retryable** — which is exactly what `_write_with_retry` does. A failover
is a transient error that looks like a crash.

**3. Connection count is a hard resource.** `max_connections` on a db.r6g.large is around 1,000, and
every consumer instance multiplies your pool size. 40 pods × 20 connections is 800 — and the deploy that
adds 5 pods takes the database down. Use **RDS Proxy** (or pgbouncer) in front of anything serverless,
where concurrency is unbounded by design. Compute it: `max_pods × pool_size < max_connections`, and write
the number down. See [29 — Capacity scaling](29_capacity_scaling_tps.md).

**4. IAM auth instead of a password** (no secret to rotate):

```python
token = boto3.client("rds").generate_db_auth_token(host, 5432, user, Region=region)
conn = psycopg.connect(host=host, user=user, password=token, sslmode="require")
```

**The token expires in 15 minutes**, so generate it per connection — caching it for the process lifetime
produces a service that works for 15 minutes after every deploy and then fails, which is a memorably
confusing bug.

**5. Batch size vs transaction size.** 500–1,000 rows per `execute_values` is the sweet spot: large enough
to amortise the round trip, small enough that a rollback is cheap, the WAL doesn't bloat, locks aren't
held long, and you stay well inside `max.poll.interval.ms`. Measure it rather than guessing.

**The same shape, other sinks** — worth having ready:

| Sink | Batching | Idempotency |
|---|---|---|
| **DynamoDB** | `batch_write_item`, 25 items max | a conditional expression on `event_id` |
| **Redshift** | buffer to S3, then `COPY` — never row-by-row | a staging table + `MERGE` |
| **S3** | buffer by size/time, one object per batch | deterministic key = `{topic}/{partition}/{offset}` |
| **Elasticsearch** | `_bulk` API | the document `_id` = `event_id` |
| **Snowflake** | Snowpipe / staged files | a MERGE on the dedup key |

Same idea every time: **batch for throughput, a natural key for idempotency, commit the source offset
last.**

---

### Q8. How do you publish an event and update the database atomically?

**The dual-write problem**, and it's the mirror image of Q6. This is broken:

```python
db.insert(order)                 # succeeds
producer.produce("orders", ...)  # the process dies here
# -> the order exists with no event. Downstream never hears about it. Silent divergence.
```

There is no transaction spanning Postgres and Kafka. So you pick one of three patterns:

**1. Transactional outbox (the standard answer).** Write the event to an `outbox` table **in the same
transaction** as the business data, then relay it:

```python
with conn.transaction():                       # ONE atomic transaction
    conn.execute("INSERT INTO orders (...) VALUES (...)")
    conn.execute("INSERT INTO outbox (id, topic, key, payload) VALUES (...)")

# a separate relay loop (or Debezium reading the WAL)
for row in conn.execute("SELECT * FROM outbox WHERE sent_at IS NULL ORDER BY id LIMIT 100"):
    producer.produce(row["topic"], key=row["key"], value=row["payload"],
                     on_delivery=lambda err, msg, rid=row["id"]:
                         None if err else mark_sent(rid))
producer.flush()
```

Either both the order and the outbox row commit, or neither does. The relay is **at-least-once** (it may
send a row twice if it dies before marking it sent), which is fine because consumers are idempotent — and
the whole system's guarantee is now consistent end to end.

**2. Change Data Capture.** Debezium reads the Postgres WAL/MySQL binlog and publishes changes to Kafka
automatically. No outbox table, no relay code, and the events are a guaranteed-accurate reflection of
committed state. The costs: the events are **row-shaped, not domain-shaped** (`orders` rows, not
`OrderPlaced` events), and Debezium is real infrastructure to operate. The outbox pattern is often used
*with* CDC — Debezium tails the outbox table, which gives you domain events with no relay to run.

**3. Event-first.** Publish to Kafka as the source of truth, and the database becomes a projection built
by a consumer (Q6). Clean, but reads are eventually consistent — a client that POSTs and immediately GETs
may see nothing, which is a product decision, not just a technical one.

**What not to do:** try to order the two writes cleverly. Every ordering has a window. "Write to Kafka
first, then the DB" just moves the inconsistency (an event for an order that doesn't exist). The outbox
exists because there is no clever ordering.

---

### Q9. Where does the configuration live?

**In the environment, never in the repo**, with a mapping rule that needs no code change per setting:

```python
def config_from_environment(prefix="KAFKA_"):
    """Strip the prefix, lowercase, underscores -> dots. One function covers every
    librdkafka property, so adding a setting is an env-var change, not a deploy."""
    return {k[len(prefix):].lower().replace("_", "."): v
            for k, v in os.environ.items() if k.startswith(prefix)}
```

```
KAFKA_BOOTSTRAP_SERVERS=b-1:9092,b-2:9092   ->  bootstrap.servers
KAFKA_SECURITY_PROTOCOL=SASL_SSL            ->  security.protocol
KAFKA_SASL_MECHANISM=SCRAM-SHA-512          ->  sasl.mechanism
KAFKA_SASL_PASSWORD=...                     ->  sasl.password   (from Secrets Manager at boot)
```

**Auth per platform**, which is the practically useful bit:

```python
# Amazon MSK with IAM (the common AWS setup)
{"security.protocol": "SASL_SSL", "sasl.mechanism": "OAUTHBEARER",
 "oauth_cb": msk_token_callback}        # aws-msk-iam-sasl-signer-python
# from aws_msk_iam_sasl_signer import MSKAuthTokenProvider
#   token, expiry_ms = MSKAuthTokenProvider.generate_auth_token("ap-south-1")

# Confluent Cloud
{"security.protocol": "SASL_SSL", "sasl.mechanism": "PLAIN",
 "sasl.username": API_KEY, "sasl.password": API_SECRET}

# self-managed with SCRAM
{"security.protocol": "SASL_SSL", "sasl.mechanism": "SCRAM-SHA-512",
 "ssl.ca.location": "/etc/ssl/certs/ca-bundle.crt"}
```

Then **layer and validate**: defaults → environment → explicit overrides (`collections.ChainMap` is one
clean way), run both validators from Q4, and raise on any ERROR at startup. Plus a `--dry-run` that
prints the merged config with `sasl.password` redacted, so an operator can see what the service will
actually use.

---

### Q10. How do you test and monitor a Kafka consumer?

**Testing, three levels:**

1. **Unit-test the handler, not the client.** Extract `process(message_dict) -> rows` as a pure function
   and test it with dicts. No broker, no mocks, microseconds per test. **Most of your coverage should be
   here.**
2. **Integration-test with a real broker** via `testcontainers` or the provided
   `docker-compose.kafka.yml`. Test the things only a broker exposes: commit semantics, rebalance
   behaviour, a poison pill reaching the DLQ, and that a redelivered message produces no duplicate row.
3. **Simulate the failure modes with a fake broker** — which is what
   [`06_kafka/03_delivery_semantics.py`](../06_kafka/03_delivery_semantics.py) and
   [`08_kafka_to_aurora_sink.py`](../06_kafka/08_kafka_to_aurora_sink.py) do. A deterministic in-memory
   `FakeBroker` lets you reproduce "crash between the DB commit and the offset commit" exactly, which is
   almost impossible to trigger reliably against a real cluster.

**Monitoring — the five signals, with what each one tells you:**

| Metric | Alert when | Why |
|---|---|---|
| **consumer lag** (per partition) | growing steadily | the single most important Kafka metric: consumption is slower than production |
| **lag *age*** (time, not count) | > your SLO | 10,000 messages behind is meaningless; "30 minutes behind" is actionable |
| **rebalance rate** | > a few per hour | the Q5 spiral; the group is spending its time rebalancing |
| **DLQ rate** | any sustained increase | a schema change or a bad producer upstream |
| **producer delivery errors** | any | messages are being dropped **right now** |

Add a per-partition breakdown, because lag is almost never uniform — one hot partition (a skewed key) is
a common and otherwise invisible cause. And trace through the message: inject `traceparent` into the
message headers so a trace spans producer → topic → consumer → database. Without it, the trace stops at
the queue, which is usually exactly where the latency is. See
[28 — Observability](28_observability_distributed_systems.md).

---

## A worked example

**An order-events pipeline: FastAPI writes, Kafka transports, a consumer projects into Aurora.**

```
                     ┌──────────────── one DB transaction ───────────────┐
  POST /orders  ──>  │ INSERT orders ... ; INSERT outbox (OrderPlaced)   │  (Q8: no dual write)
                     └──────────────────────────────────────────────────┘
                                          |
                        relay loop (or Debezium on the outbox table)
                        producer: acks=all, idempotence=True, lz4, flush on exit     (Q2)
                                          v
                              topic: orders.events  (18 partitions, RF=3,
                                      min.insync.replicas=2, key=order_id)
                                          |
          ┌───────────────────────────────┴───────────────────────────────┐
          v                                                               v
  consumer group: orders-writer                            consumer group: analytics
  enable.auto.commit=False, earliest,                       (independent offsets; a slow
  cooperative-sticky, max.poll.records=500        (Q3)       analytics consumer cannot
          |                                                  affect the writer)
          v
  batch 500 -> validate -> poison to orders.dlq
            -> ONE txn: execute_values + ON CONFLICT (event_id) DO NOTHING   (Q6)
            -> DB COMMIT
            -> THEN consumer.commit()
            -> OperationalError (Aurora failover) => bounded retry on the SAME batch; never commit
                                          |
                                          v
                              Aurora PostgreSQL (WRITER endpoint)
                              psycopg pool: 16/pod, pre_ping, max_lifetime=600     (Q7)
                              10 pods x 16 = 160 < max_connections 1000

  OBSERVABILITY: traceparent in message headers end to end; consumer lag AGE alert;
                 rebalance-rate alert; DLQ-rate alert; producer delivery-error alert.   (Q10)
  SHUTDOWN:      SIGTERM -> stop polling -> finish batch -> DB commit -> offset commit
                 -> producer.flush() -> consumer.close()                               (Q2/Q3)
```

**The three guarantees this gives you, stated plainly:**

1. **No lost events at the source.** The order and its event commit atomically (outbox), so there is no
   window where the order exists and the event doesn't.
2. **No lost events in transit.** `acks=all` + `min.insync.replicas=2` + RF=3 survives one broker
   failure; the delivery callback catches a permanent failure instead of swallowing it.
3. **No duplicate rows at the sink.** At-least-once delivery plus an idempotent upsert keyed on
   `event_id` means every replay is a no-op — and replays *will* happen, on every rebalance and every
   failover.

And the one thing it does **not** give you: ordering across different `order_id`s. Ordering is guaranteed
only within a partition, and keying by `order_id` means all events for one order are ordered — which is
the guarantee that actually matters. Say that explicitly; claiming global ordering is a tell.

---

## Hands-on drills

1. Run `07_kafka_python_config.py`. Validate the "throughput" profile and decide out loud whether you'd
   accept `acks=1` for clickstream data, and for payments.
2. Run `08_kafka_to_aurora_sink.py` and read the three bug demonstrations. Then move
   `broker.commit(last_offset)` **above** `_write_with_retry` and count the rows you lose in the failover
   scenario.
3. Set `batch_size=1` in the sink and compare `round_trips` with `batch_size=50`. That ratio is the
   answer to "why is my consumer lag growing?".
4. Write a consumer with `enable.auto.commit=True`, kill it mid-batch with a real broker, restart, and
   count the messages that were never processed.
5. Add a `time.sleep(30)` inside the handler with `max.poll.interval.ms=10000` and watch the rebalance
   loop. Then fix it with a retry topic instead.
6. Build the outbox table and relay loop. Kill the relay between `produce()` and `mark_sent()` and confirm
   the message is sent twice — then confirm the consumer's upsert makes that harmless.
7. Implement `merge_config(defaults, env, overrides)` with `ChainMap`, run both validators, and make a
   contradictory config fail the startup.
8. Change `ON CONFLICT DO NOTHING` to a `DO UPDATE` without the `updated_at` guard, then replay an old
   event and watch it overwrite a newer one.
9. Inject `traceparent` into a message header, extract it in the consumer as the parent span, and confirm
   one trace spans the queue.
10. Compute `max_pods × pool_size` for your consumer deployment and compare with the database's
    `max_connections`. If you can't find both numbers in five minutes, that's the finding.

---

## The 60-second spoken answer

> "I'd use `confluent-kafka-python` — it's librdkafka underneath, so it's the fastest and the most
> complete — or `aiokafka` if the service is asyncio, because `confluent-kafka`'s `poll` and `flush`
> block and would stall the event loop.
>
> On the producer, no-loss means `acks=all` plus `enable.idempotence=True`, which gives per-partition
> sequence numbers so the broker drops duplicates from its own retries, with a bounded
> `delivery.timeout.ms` — that's the real deadline, not `retries`. And critically I act on the delivery
> callback, because `produce()` is asynchronous and without the callback a permanent send failure is
> invisible to my code. `flush()` before exit, always, or an unflushed buffer on SIGTERM means those
> events are lost rather than retried.
>
> On the consumer the single most important setting is `enable.auto.commit=False`. The default commits
> on a timer, so it can commit offsets for messages you haven't finished — that's silent data loss on a
> crash. I commit manually after the work succeeds, with `auto.offset.reset=earliest` and
> `cooperative-sticky` so rebalances are incremental rather than stop-the-world. If the consumer is
> rebalancing constantly it's because processing exceeded `max.poll.interval.ms` between polls — the fix
> is a faster handler or a lower `max.poll.records`, never a sleep in the loop. Delays belong in a retry
> topic.
>
> For writing to Aurora, the whole answer is one ordering: poll a batch of 500, validate first and route
> unparseable records straight to a DLQ so a poison pill can't block the partition, then one transaction
> with one `execute_values` upsert — `ON CONFLICT (event_id) DO NOTHING`, backed by a unique index. The
> database commits, and only *then* do I commit the Kafka offset. If the process dies in between, Kafka
> redelivers and the upsert makes the replay a no-op: at-least-once delivery, effectively-once effect.
> Kafka transactions don't help here, because they can't span Kafka and Aurora — the idempotent write is
> what makes the replay harmless.
>
> Aurora-specific: writes go to the cluster **writer** endpoint, a failover takes 30 to 60 seconds and
> invalidates pooled sockets, so I use `pool_pre_ping` with a bounded lifetime and treat
> `OperationalError` as retryable on the same batch. I check pods × pool size against `max_connections`,
> and use RDS Proxy for anything serverless. IAM auth tokens expire in 15 minutes, so they're generated
> per connection.
>
> And for the reverse direction — updating the database *and* publishing an event — there's no
> transaction spanning both, so it's the transactional outbox: the event row commits in the same
> transaction as the business data, and a relay or Debezium publishes it at-least-once. Trying to order
> two separate writes cleverly always leaves a window.
>
> Config lives in environment variables mapped to librdkafka keys, secrets from Secrets Manager, and I
> validate the combination at startup so a contradictory config fails the deploy instead of the 3am
> page. For monitoring, the signals are consumer lag *age* rather than count, rebalance rate, DLQ rate
> and producer delivery errors — and `traceparent` in the message headers so a trace spans the queue."
