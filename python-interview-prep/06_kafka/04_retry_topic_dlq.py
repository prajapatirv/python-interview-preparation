"""
Failure handling: classify errors (transient vs poison pill), a few short inline retries,
then route to a retry-tier topic or straight to a DLQ -- WITHOUT blocking the partition.
This is a runnable SIMULATION (no broker needed); every produce()/topic name maps 1:1 to the
real confluent-kafka calls shown in the comments.

Run me: python 04_retry_topic_dlq.py
"""
import json
import random


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


class Transient(Exception):
    """A downstream timeout, 5xx, DB deadlock -- worth retrying."""


class Permanent(Exception):
    """Bad JSON, failed validation, a poison pill -- retrying changes nothing."""


RETRY_TIERS = ["orders.retry.1m", "orders.retry.10m"]  # each tier = a real Kafka topic
DLQ_TOPIC = "orders.dlq"

# simulated "topics" as lists, standing in for real produce() calls
topics = {name: [] for name in RETRY_TIERS + [DLQ_TOPIC]}


def send_to_dlq(message, error, attempt):
    """Real equivalent:
        producer.produce("orders.dlq", key=msg.key(), value=msg.value(),
                          headers=[("x-error", str(error).encode()),
                                   ("x-attempt", str(attempt).encode()),
                                   ("x-origin-topic", b"orders")])
    """
    topics[DLQ_TOPIC].append({"message": message, "error": str(error), "attempt": attempt})


def route_to_retry_tier(message, error, attempt):
    """Real equivalent: produce the same payload to the next retry-tier topic with an
    incremented x-attempt header, then COMMIT the original message's offset (we're done with
    it on THIS topic -- a separate delayed consumer owns the retry topic)."""
    if attempt <= len(RETRY_TIERS):
        target = RETRY_TIERS[attempt - 1]
        topics[target].append({"message": message, "error": str(error), "attempt": attempt})
        return target
    send_to_dlq(message, error, attempt)
    return DLQ_TOPIC


def process_order(order: dict):
    """Business logic that can fail in two very different ways."""
    if order.get("_simulate") == "malformed":
        raise Permanent("schema validation failed: missing 'total' field")
    if order.get("_simulate") == "flaky" and random.random() < 0.7:
        raise Transient("downstream payment service timed out")
    return f"charged order {order['order_id']}"


def handle_message(raw_message: dict, max_inline_retries=2):
    """The real consumer loop's per-message handler. Short inline retries absorb brief blips;
    anything longer is handed off to a retry topic instead of sleeping in the poll loop (which
    would block every OTHER message on this partition and risk exceeding
    max.poll.interval.ms -> an unwanted rebalance)."""
    order = raw_message
    for attempt in range(1, max_inline_retries + 1):
        try:
            result = process_order(order)
            print(f"  SUCCESS on attempt {attempt}: {result}")
            return
        except Transient as e:
            print(f"  attempt {attempt} transient failure: {e}")
            if attempt == max_inline_retries:
                target = route_to_retry_tier(order, e, attempt=1)
                print(f"  -> exhausted inline retries, routed to {target}")
                return
        except Permanent as e:
            print(f"  PERMANENT failure, no point retrying: {e}")
            send_to_dlq(order, e, attempt)
            print(f"  -> routed straight to {DLQ_TOPIC}")
            return


section("case 1: a poison pill goes straight to the DLQ")
handle_message({"order_id": "o-1", "_simulate": "malformed"})

section("case 2: a transient failure (mostly) succeeds within inline retries")
random.seed(1)  # deterministic for the demo
handle_message({"order_id": "o-2", "_simulate": "flaky"})

section("case 3: a transient failure that outlasts inline retries -> retry topic")
random.seed(3)
handle_message({"order_id": "o-3", "_simulate": "flaky"})

section("final state of each simulated topic")
for name, msgs in topics.items():
    print(f"  {name}: {len(msgs)} message(s)")
    for m in msgs:
        print(f"    {m}")

print("""
Key trade-off to say out loud in an interview: while order o-3 sits in orders.retry.1m waiting
for its delay to elapse, orders for OTHER customers on the same partition keep flowing normally
on the main topic -- but if strict per-key ordering matters (e.g. account balance events), a
later event for o-3's same key could now be processed BEFORE o-3's retried event catches up.
Either accept that trade-off, block-and-retry in place for that specific key, or design events
to be commutative/versioned so out-of-order application is safe.
""")
