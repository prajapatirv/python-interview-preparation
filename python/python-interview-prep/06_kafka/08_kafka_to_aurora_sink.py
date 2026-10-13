"""
Kafka -> Aurora (PostgreSQL) sink: the integration question "how do you consume from Kafka and
write to a database in Python without losing or duplicating rows?"

Everything here is a dependency-free SIMULATION (FakeBroker + FakeAurora with a real unique
index, a real transaction and an injectable failure) so the three bugs are observably reproduced:

  1. commit-offset-first   -> LOST rows
  2. naive INSERT on retry -> DUPLICATE rows / IntegrityError
  3. row-at-a-time writes  -> 10-50x slower than batching, and the reason your lag never drains

...and then fixed with the pattern you should describe in an interview:

  poll a BATCH -> one DB transaction -> idempotent UPSERT keyed on event_id -> DB COMMIT
  -> only then commit the Kafka offset -> on failure, rollback + retry, DLQ the poison rows.

The commented lines show the exact psycopg / SQLAlchemy / confluent-kafka calls each fake stands
in for, including the Aurora-specific operational points (writer vs reader endpoint, failover,
RDS Proxy, IAM auth).

Run me: python 08_kafka_to_aurora_sink.py
"""
import json
import random
import time
from collections import defaultdict


def section(title):
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


# ================================================================ the fakes
class FakeBroker:
    """One partition: an ordered log plus the consumer group's committed offset."""

    def __init__(self, messages):
        self.log = list(messages)
        self.committed_offset = 0

    def poll_batch(self, max_records):
        """Real equivalent: consumer.consume(num_messages=max_records, timeout=1.0)"""
        start = self.committed_offset
        batch = [(start + i, m) for i, m in enumerate(self.log[start:start + max_records])]
        return batch

    def commit(self, offset):
        """Real equivalent: consumer.commit(offsets=[TopicPartition(t, p, offset + 1)])
        -- note the +1: Kafka stores the NEXT offset to read, not the last one processed."""
        self.committed_offset = offset + 1

    def remaining(self):
        return len(self.log) - self.committed_offset


class IntegrityError(Exception):
    """Stands in for psycopg.errors.UniqueViolation."""


class OperationalError(Exception):
    """Stands in for a lost connection / Aurora failover / deadlock -- i.e. RETRYABLE."""


class FakeAurora:
    """A tiny transactional store with a UNIQUE index, so duplicate handling is real.

    Mirrors psycopg3:  with pool.connection() as conn:  with conn.cursor() as cur: ...
    `autocommit` is False, exactly like a real connection, so nothing lands until commit().
    """

    def __init__(self, fail_on_commit_once=False):
        self.rows = {}                       # order_id -> row   (the committed table)
        self.processed_event_ids = set()      # the UNIQUE index on event_id
        self._pending = []                    # statements inside the open transaction
        self._in_transaction = False
        self.commit_count = 0
        self.rollback_count = 0
        self.statements_executed = 0
        self.round_trips = 0
        self._fail_on_commit_once = fail_on_commit_once

    # -- transaction control ------------------------------------------------
    def begin(self):
        self._in_transaction, self._pending = True, []

    def commit(self):
        if self._fail_on_commit_once:
            self._fail_on_commit_once = False
            self._pending, self._in_transaction = [], False
            raise OperationalError("connection reset during COMMIT (Aurora failover)")
        for event_id, row in self._pending:
            self.processed_event_ids.add(event_id)
            self.rows[row["order_id"]] = row
        self._pending, self._in_transaction = [], False
        self.commit_count += 1

    def rollback(self):
        self._pending, self._in_transaction = [], False
        self.rollback_count += 1

    # -- statements ---------------------------------------------------------
    def insert(self, event_id, row):
        """A plain INSERT -- raises on a duplicate event_id, like a real unique index."""
        self.statements_executed += 1
        self.round_trips += 1
        if event_id in self.processed_event_ids or any(e == event_id for e, _ in self._pending):
            raise IntegrityError(f'duplicate key value violates unique constraint '
                                 f'"orders_event_id_key" (event_id={event_id})')
        self._pending.append((event_id, row))

    def upsert_many(self, pairs):
        """ONE round trip for the whole batch. Real equivalent:

            INSERT INTO orders (event_id, order_id, status, amount)
            VALUES %s
            ON CONFLICT (event_id) DO NOTHING          -- idempotent: a replay is a no-op
            -- or: ON CONFLICT (order_id) DO UPDATE SET status = EXCLUDED.status
            --        WHERE orders.updated_at < EXCLUDED.updated_at   -- last-write-wins guard

        executed with psycopg.extras.execute_values(cur, sql, rows, page_size=1000)
        or cur.executemany(...) -- the point is ONE statement, not len(rows) statements.
        """
        self.statements_executed += 1
        self.round_trips += 1                 # <-- the whole batch costs ONE round trip
        for event_id, row in pairs:
            if event_id in self.processed_event_ids:
                continue                      # ON CONFLICT DO NOTHING
            self._pending.append((event_id, row))


def make_events(n=10, duplicates=(), poison=()):
    """Builds a topic's worth of order events. `duplicates` replays an earlier event (which is
    exactly what at-least-once delivery does after a rebalance); `poison` holds unparseable rows."""
    events = []
    for i in range(1, n + 1):
        if i in poison:
            events.append("{not-json")
            continue
        events.append(json.dumps({
            "event_id": f"evt-{i}",
            "order_id": f"ORD-{1000 + i}",
            "status": "SHIPPED" if i % 2 else "PAID",
            "amount": round(10 + i * 1.5, 2),
        }))
    for i in duplicates:                      # the same event_id delivered a second time
        events.append(json.dumps({
            "event_id": f"evt-{i}",
            "order_id": f"ORD-{1000 + i}",
            "status": "SHIPPED" if i % 2 else "PAID",
            "amount": round(10 + i * 1.5, 2),
        }))
    return events


# ================================================================ 1. the broken versions
def sink_commit_first(events, crash_at=3):
    """BUG 1: commit the Kafka offset before the DB transaction commits.
    This is also what `enable.auto.commit=True` does to you, on a timer, invisibly."""
    broker, db = FakeBroker(events), FakeAurora()
    crashed = False
    while broker.remaining():
        for offset, raw in broker.poll_batch(1):
            broker.commit(offset)                    # <-- offset committed FIRST
            if not crashed and offset == crash_at:
                crashed = True
                print(f"    *** process dies at offset {offset}, after the offset commit ***")
                continue                             # the DB write never happens
            db.begin()
            db.insert(json.loads(raw)["event_id"], json.loads(raw))
            db.commit()
    return db


def sink_naive_insert(events):
    """BUG 2: a plain INSERT. A redelivered message (normal at-least-once behaviour) now
    either duplicates the row or kills the batch with an IntegrityError."""
    broker, db = FakeBroker(events), FakeAurora()
    errors = []
    while broker.remaining():
        for offset, raw in broker.poll_batch(1):
            row = json.loads(raw)
            db.begin()
            try:
                db.insert(row["event_id"], row)
                db.commit()
            except IntegrityError as e:
                db.rollback()
                errors.append(str(e))
            broker.commit(offset)
    return db, errors


def sink_row_at_a_time(events):
    """BUG 3: correct, but one transaction and one round trip PER ROW. At 600 TPS with a 2ms
    round trip you have spent 1.2s of every second just waiting on the network."""
    broker, db = FakeBroker(events), FakeAurora()
    while broker.remaining():
        for offset, raw in broker.poll_batch(1):
            row = json.loads(raw)
            db.begin()
            db.upsert_many([(row["event_id"], row)])
            db.commit()
            broker.commit(offset)
    return db


# ================================================================ 2. the correct version
class KafkaToAuroraSink:
    """The pattern to describe in an interview.

    Ordering of the four operations is the entire answer:
        1. poll a batch                     (consumer.consume(num_messages=500, timeout=1.0))
        2. parse + validate; poison -> DLQ  (never let one bad row block the partition)
        3. ONE transaction, ONE upsert      (execute_values + ON CONFLICT DO NOTHING)
        4. DB commit, THEN Kafka commit     (a crash between them replays -> the upsert absorbs it)

    That gives at-least-once delivery with effectively-once EFFECT, which is what "exactly once"
    means in practice for a Kafka->DB sink. True Kafka transactions do not help here: they cannot
    span Kafka and Aurora. The idempotent write is what makes the replay harmless.
    """

    def __init__(self, broker, db, batch_size=100, max_retries=3, sleep=time.sleep):
        self.broker, self.db = broker, db
        self.batch_size, self.max_retries, self.sleep = batch_size, max_retries, sleep
        self.stats = defaultdict(int)
        self.dlq = []

    def run(self):
        while self.broker.remaining():
            batch = self.broker.poll_batch(self.batch_size)
            if not batch:
                break
            parsed, last_offset = [], batch[-1][0]

            # -- step 2: parse/validate. A poison row goes to the DLQ and is NOT retried.
            for offset, raw in batch:
                try:
                    row = json.loads(raw)
                    if not row.get("event_id") or not row.get("order_id"):
                        raise ValueError("missing event_id/order_id")
                    parsed.append((row["event_id"], row))
                    self.stats["parsed"] += 1
                except (json.JSONDecodeError, ValueError) as e:
                    self.dlq.append({"offset": offset, "payload": raw, "error": str(e)})
                    self.stats["dlq"] += 1

            # -- step 3 + 4: write the batch, then advance the offset
            if parsed and not self._write_with_retry(parsed):
                # the batch failed every retry: do NOT commit the offset. The consumer will
                # redeliver it after a restart, which is the correct behaviour for a DB outage.
                self.stats["batches_abandoned"] += 1
                print("      batch abandoned without committing the offset -- it will be redelivered")
                break
            self.broker.commit(last_offset)
            self.stats["batches"] += 1
        return self.stats

    def _write_with_retry(self, pairs):
        for attempt in range(1, self.max_retries + 1):
            try:
                self.db.begin()
                self.db.upsert_many(pairs)      # ONE statement for the whole batch
                self.db.commit()
                self.stats["rows_written"] += len(pairs)
                return True
            except OperationalError as e:
                self.db.rollback()              # ALWAYS roll back before reusing the connection
                self.stats["db_retries"] += 1
                if attempt == self.max_retries:
                    print(f"      DB unavailable after {attempt} attempts: {e}")
                    return False
                delay = 0.01 * (2 ** (attempt - 1))
                print(f"      transient DB error ({e}); retry {attempt} in {delay:.3f}s")
                self.sleep(delay)
            except IntegrityError as e:
                # A constraint other than our idempotency key -- a data problem, not a transient
                # one. Retrying cannot help, so split the batch and DLQ the offending rows.
                self.db.rollback()
                print(f"      integrity error, splitting batch: {e}")
                return self._write_one_by_one(pairs)
        return False

    def _write_one_by_one(self, pairs):
        """Fallback after a batch-level constraint failure: isolate the bad row instead of losing
        the whole batch. Slower, but it only happens on the exceptional path."""
        for event_id, row in pairs:
            try:
                self.db.begin()
                self.db.upsert_many([(event_id, row)])
                self.db.commit()
                self.stats["rows_written"] += 1
            except (IntegrityError, OperationalError) as e:
                self.db.rollback()
                self.dlq.append({"event_id": event_id, "error": str(e)})
                self.stats["dlq"] += 1
        return True


# ================================================================ the real-world notes
AURORA_NOTES = """\
  Connecting to Aurora PostgreSQL from Python -- the five things that actually bite:

  1. TWO endpoints, and using the wrong one is the most common mistake.
       writer:  my-cluster.cluster-xxxx.ap-south-1.rds.amazonaws.com        <- all INSERT/UPDATE
       reader:  my-cluster.cluster-ro-xxxx.ap-south-1.rds.amazonaws.com     <- read replicas only
     A sink writes to the WRITER endpoint. Point it at the reader and every write fails with
     "cannot execute INSERT in a read-only transaction".

  2. Failover takes 30-60s and your pooled connections go stale. The DNS record flips, but an
     open socket does not. So: a connection pool with pre-ping / recycle, and treat
     OperationalError as RETRYABLE (exactly what _write_with_retry does above).

       # SQLAlchemy
       engine = create_engine(dsn, pool_size=10, max_overflow=5,
                              pool_pre_ping=True,      # validates before handing out a connection
                              pool_recycle=300)        # avoid stale sockets after a failover
       # psycopg3
       pool = ConnectionPool(dsn, min_size=2, max_size=10, timeout=5, max_lifetime=600)

  3. Connection count is a hard resource. max_connections on a db.r6g.large is ~1000, and every
     Lambda/pod/consumer multiplies it. Use RDS Proxy (or pgbouncer) in front for serverless
     consumers; a pool per process otherwise. Never open a connection per message.

  4. IAM auth instead of a password (no secret to rotate):
       token = boto3.client("rds").generate_db_auth_token(host, 5432, user, Region=region)
       conn  = psycopg.connect(host=host, user=user, password=token, sslmode="require")
     The token expires in 15 minutes -- generate it per connection, never cache it for the
     process lifetime.

  5. Batch size vs. transaction size. 500-1000 rows per execute_values() is the sweet spot:
     big enough to amortise the round trip, small enough that a rollback is cheap and that you
     stay well inside max.poll.interval.ms. Measure, don't guess.

  The same shape, other sinks:
    DynamoDB  -> batch_write_item (25 items max) + a conditional expression for idempotency
    Redshift  -> buffer to S3, then COPY; never row-by-row INSERT
    S3        -> buffer by size/time, write one object per batch (see 09_aws_lambda_streaming/)
    Snowflake -> Snowpipe / staged files, same buffer-then-load idea"""


if __name__ == "__main__":
    random.seed(7)

    section("BUG 1 -- committing the Kafka offset before the DB transaction: LOST ROWS")
    events = make_events(8)
    db = sink_commit_first(events, crash_at=3)
    print(f"    events on the topic : 8")
    print(f"    rows in the database: {len(db.rows)}  <-- one row LOST, forever, silently")
    print("    this is exactly what enable.auto.commit=True does to you on a 5-second timer.")

    section("BUG 2 -- plain INSERT with at-least-once redelivery: DUPLICATE KEY ERRORS")
    events = make_events(5, duplicates=(2, 4))      # evt-2 and evt-4 redelivered
    db, errors = sink_naive_insert(events)
    print(f"    rows written: {len(db.rows)}, failed inserts: {len(errors)}")
    for e in errors:
        print(f"      {e}")
    print("    with no unique index it would instead be DOUBLE-COUNTED revenue -- worse, because")
    print("    nothing errors and nobody notices until finance does.")

    section("BUG 3 -- one transaction per row: correct, but it will never drain the lag")
    events = make_events(200)
    t0 = time.perf_counter()
    db_slow = sink_row_at_a_time(events)
    slow_elapsed = time.perf_counter() - t0
    print(f"    200 rows -> {db_slow.round_trips} DB round trips, "
          f"{db_slow.commit_count} transactions")
    print(f"    at a realistic 2ms per round trip that is "
          f"{db_slow.round_trips * 2 / 1000:.2f}s of pure network wait")

    section("THE FIX -- batch + idempotent upsert + commit the offset LAST")
    events = make_events(200, duplicates=(5, 17, 99), poison=(50, 120))
    broker, db_fast = FakeBroker(events), FakeAurora()
    sink = KafkaToAuroraSink(broker, db_fast, batch_size=50)
    t0 = time.perf_counter()
    stats = sink.run()
    fast_elapsed = time.perf_counter() - t0
    print(f"    messages on topic   : {len(events)}")
    print(f"    parsed              : {stats['parsed']}")
    print(f"    routed to DLQ       : {stats['dlq']}  (the two unparseable payloads)")
    print(f"    rows in the database: {len(db_fast.rows)}")
    print(f"    duplicates absorbed : {stats['parsed'] - len(db_fast.rows)} "
          f"(replayed event_ids hit ON CONFLICT DO NOTHING)")
    print(f"    DB round trips      : {db_fast.round_trips} vs {db_slow.round_trips} row-at-a-time "
          f"({db_slow.round_trips // max(db_fast.round_trips, 1)}x fewer)")
    print(f"    transactions        : {db_fast.commit_count} vs {db_slow.commit_count}")
    print(f"    DLQ contents        : {[d['offset'] for d in sink.dlq]}")

    section("THE FIX under a DB failover during COMMIT -- retried, then replayed, never lost")
    events = make_events(20)
    broker = FakeBroker(events)
    db_flaky = FakeAurora(fail_on_commit_once=True)
    sink = KafkaToAuroraSink(broker, db_flaky, batch_size=10, sleep=lambda s: None)
    stats = sink.run()
    print(f"    rows in the database: {len(db_flaky.rows)} of 20")
    print(f"    retries             : {stats['db_retries']}, rollbacks: {db_flaky.rollback_count}")
    print(f"    offset committed to : {broker.committed_offset} (the batch was retried, not skipped)")
    print("    the COMMIT failed, the transaction rolled back, the offset was NOT advanced ->")
    print("    the batch was retried and the upsert made the replay a no-op. Nothing lost,")
    print("    nothing duplicated. That is the whole design, in one sentence.")

    section("Aurora-specific operational notes")
    print(AURORA_NOTES)

    section("the 60-second answer")
    print("""  "I consume in batches with enable.auto.commit=false. For each batch I parse and
  validate first, routing unparseable records straight to a DLQ topic so one poison pill can
  never block the partition. The valid rows go to Aurora in a SINGLE transaction as one
  execute_values upsert with ON CONFLICT (event_id) DO NOTHING -- the event_id is the
  idempotency key, backed by a unique index. The database commits first, and only then do I
  commit the Kafka offset. If the process dies in between, Kafka redelivers the batch and the
  upsert turns the replay into a no-op: at-least-once delivery, effectively-once effect.
  Transient OperationalErrors -- which on Aurora means a failover -- get a bounded retry with
  backoff on the same batch, with a connection pool using pre-ping so I don't hand out a stale
  socket. Writes go to the cluster WRITER endpoint; anything read-only uses the reader endpoint.
  I size batches at 500-1000 rows, which amortises the round trip while staying well inside
  max.poll.interval.ms so I don't trigger a rebalance.\"""")

# EXPERIMENT 1: set batch_size=1 in the fixed sink and compare round_trips with batch_size=50.
# That ratio is the single number that explains "why is my consumer lag growing?".
# EXPERIMENT 2: change `ON CONFLICT DO NOTHING` semantics to last-write-wins by having
# upsert_many() overwrite rows whose event_id was already seen. Then ask: is a replayed OLD event
# allowed to overwrite a NEWER one? (It is -- which is why real upserts carry
# `WHERE orders.updated_at < EXCLUDED.updated_at`.)
# EXPERIMENT 3: make FakeAurora.commit() fail every time and confirm the offset never advances and
# nothing is written -- a full DB outage must stall the consumer, not drop data.
# EXPERIMENT 4: move broker.commit(last_offset) ABOVE the _write_with_retry call and re-run the
# failover scenario. Count the rows you lose.

# EXERCISE: add a transactional-outbox producer to this file: a `write_order_and_event()` that
# inserts the order row AND an outbox row in the SAME transaction, plus a relay loop that reads
# unpublished outbox rows, produces them to Kafka, and marks them sent. Then explain in two
# sentences why that is the only safe way to "update the DB and publish an event" without
# distributed transactions -- and what the dual-write bug looks like when you skip it.
