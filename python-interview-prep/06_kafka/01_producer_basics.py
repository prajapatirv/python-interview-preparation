"""
Kafka producer basics: keyed partitioning, delivery callbacks, idempotence, flush().
Needs: pip install confluent-kafka, and a broker reachable at localhost:9092
       (see ../docker-compose.kafka.yml). Safe to READ without a broker -- every produce()
       call is commented with exactly what it would do on a real cluster.

Run me: python 01_producer_basics.py
"""
import json
import time

try:
    from confluent_kafka import Producer
except ImportError:
    Producer = None  # allows this file to be read/imported without the dependency installed


def build_producer():
    return Producer({
        "bootstrap.servers": "localhost:9092",
        "enable.idempotence": True,   # dedupes retried batches; implies acks=all
        "compression.type": "lz4",    # good throughput/CPU trade-off
        "linger.ms": 10,              # batch small bursts of produce() calls together
    })


def on_delivery(err, msg):
    """Called from inside producer.poll()/flush() -- NOT synchronously from produce()."""
    if err:
        print(f"  delivery FAILED: {err}")
    else:
        print(f"  delivered to {msg.topic()} [partition {msg.partition()}] @ offset {msg.offset()}")


def main():
    if Producer is None:
        print("confluent-kafka not installed -- run `pip install confluent-kafka` to execute this.")
        print("Reading the code below still teaches the pattern; every produce() call is annotated.")
        return

    producer = build_producer()
    orders = [
        {"order_id": "o-1", "customer_id": "c-1", "total": 100},
        {"order_id": "o-2", "customer_id": "c-2", "total": 250},
        {"order_id": "o-3", "customer_id": "c-1", "total": 75},  # same customer as o-1
    ]

    for order in orders:
        # KEY = customer_id -> Kafka hashes the key to pick a partition. All of c-1's orders
        # land on the SAME partition, so a consumer reading that partition sees them in the
        # order they were produced (o-1 before o-3). Without a key, ordering across records
        # from the same producer is NOT guaranteed across partitions.
        producer.produce(
            topic="orders",
            key=order["customer_id"].encode(),
            value=json.dumps(order).encode(),
            on_delivery=on_delivery,
        )
        producer.poll(0)  # serve any pending delivery callbacks without blocking

    print("flushing (blocks until every in-flight message is acknowledged or times out)...")
    remaining = producer.flush(timeout=10)
    if remaining > 0:
        print(f"  WARNING: {remaining} messages were not delivered before the timeout")
    else:
        print("  all messages delivered")


if __name__ == "__main__":
    main()

# EXPERIMENT (with a real broker running): produce 3 messages with the SAME key and 3 with
# DIFFERENT keys, then in 02_consumer_basics.py print msg.partition() for each -- confirm the
# same-key messages always land on the same partition number.
