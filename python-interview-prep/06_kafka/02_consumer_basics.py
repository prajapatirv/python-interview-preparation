"""
Kafka consumer basics: consumer groups and manual offset commit (the at-least-once shape).
Needs: pip install confluent-kafka, and a broker reachable at localhost:9092.
Run me: python 02_consumer_basics.py   (run 01_producer_basics.py first, or concurrently)
"""
import json

try:
    from confluent_kafka import Consumer
except ImportError:
    Consumer = None


def build_consumer(group_id="order-processor"):
    return Consumer({
        "bootstrap.servers": "localhost:9092",
        "group.id": group_id,              # all instances sharing this id split the partitions
        "auto.offset.reset": "earliest",   # only used the FIRST time this group reads the topic
        "enable.auto.commit": False,       # WE decide exactly when an offset is "done" -- see below
        "partition.assignment.strategy": "cooperative-sticky",  # smoother rebalances
    })


def process_order(order: dict):
    print(f"  processing order {order['order_id']} for {order['customer_id']} (${order['total']})")
    # ... real business logic would go here: charge payment, update inventory, etc.
    # If this raises, we must NOT commit the offset below -- see 03_delivery_semantics.py.


def main():
    if Consumer is None:
        print("confluent-kafka not installed -- run `pip install confluent-kafka` to execute this.")
        return

    consumer = build_consumer()
    consumer.subscribe(["orders"])

    print("polling for up to 10s (Ctrl+C to stop earlier)...")
    try:
        import time
        deadline = time.time() + 10
        while time.time() < deadline:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                print("  consumer error:", msg.error())
                continue

            order = json.loads(msg.value())
            print(f"  [partition {msg.partition()} offset {msg.offset()}] key={msg.key()}")
            process_order(order)

            # AT-LEAST-ONCE: commit only AFTER processing succeeds. If the process crashes
            # between process_order() and this commit, the message is re-delivered on restart --
            # a duplicate, never a silent loss. This is why process_order (and anything it calls)
            # must be idempotent in a real system.
            consumer.commit(message=msg, asynchronous=False)
    finally:
        consumer.close()  # leaves the group cleanly, triggering an immediate rebalance


if __name__ == "__main__":
    main()

# EXPERIMENT: change enable.auto.commit to True and remove the manual commit() call. Kill the
# process (Ctrl+C) mid-batch and restart it -- with auto-commit, messages the consumer had
# already "seen" via poll() but not necessarily finished processing may be silently skipped on
# restart. That gap is exactly why production consumers disable auto-commit.
