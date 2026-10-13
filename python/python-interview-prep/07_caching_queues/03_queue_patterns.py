"""
Queue-based architecture patterns using stdlib queue.Queue: a bounded producer/consumer
(backpressure), a visibility-timeout-style retry, and a dead-letter queue. This is the SQS/RabbitMQ
shape -- point-to-point, one consumer group, message removed once acknowledged.

Run me: python 03_queue_patterns.py
"""
import queue
import random
import threading
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- bounded queue = backpressure
section("bounded queue.Queue(maxsize=N) — put() blocks the producer once full")
q = queue.Queue(maxsize=3)
events_produced = []


def producer():
    for i in range(8):
        q.put(i)  # blocks here if the queue already has 3 items -- natural backpressure
        events_produced.append(i)
    q.put(None)  # sentinel: no more work


def consumer():
    while (item := q.get()) is not None:
        time.sleep(0.02)  # simulate slower processing than production
        q.task_done()
    q.task_done()


t_prod = threading.Thread(target=producer)
t_cons = threading.Thread(target=consumer)
t_prod.start(); t_cons.start()
t_prod.join(); t_cons.join()
print(f"produced {len(events_produced)} events; consumer never had more than 3 buffered at once")


# ---------------------------------------------------------------- visibility timeout + DLQ
section("SQS-style visibility timeout: a message 'reappears' if not acked in time, up to maxReceiveCount")


class SimpleQueue:
    """A minimal SQS-like queue: messages are only removed after an explicit ack(); if a message
    isn't acked within visibility_timeout, it becomes visible again for redelivery. After
    max_receives failed attempts, it moves to a DLQ automatically."""

    def __init__(self, visibility_timeout=0.3, max_receives=3):
        self.messages = []  # each: {"body": ..., "receive_count": 0, "hidden_until": 0}
        self.dlq = []
        self.visibility_timeout = visibility_timeout
        self.max_receives = max_receives
        self.lock = threading.Lock()

    def send(self, body):
        with self.lock:
            self.messages.append({"body": body, "receive_count": 0, "hidden_until": 0})

    def receive(self):
        now = time.time()
        with self.lock:
            for msg in self.messages:
                if msg["hidden_until"] <= now:
                    msg["receive_count"] += 1
                    if msg["receive_count"] > self.max_receives:
                        self.messages.remove(msg)
                        self.dlq.append(msg)
                        continue
                    msg["hidden_until"] = now + self.visibility_timeout
                    return msg
        return None

    def ack(self, msg):
        with self.lock:
            if msg in self.messages:
                self.messages.remove(msg)


q2 = SimpleQueue(visibility_timeout=0.2, max_receives=3)
q2.send("order-1")  # will succeed on first try
q2.send("order-2")  # will "fail to process" every time -> ends up in the DLQ

processed = []


def flaky_worker():
    deadline = time.time() + 2.0
    while time.time() < deadline and (q2.messages or True):
        msg = q2.receive()
        if msg is None:
            time.sleep(0.05)
            continue
        if msg["body"] == "order-2":
            # simulate a handler that always crashes before acking -- never call ack()
            print(f"  received {msg['body']} (attempt {msg['receive_count']}) -- 'processing' fails")
            continue
        print(f"  received {msg['body']} (attempt {msg['receive_count']}) -- processing succeeds")
        processed.append(msg["body"])
        q2.ack(msg)
        if not q2.messages and q2.dlq:
            break


flaky_worker()
print(f"\nprocessed successfully: {processed}")
print(f"moved to DLQ after {q2.max_receives} failed attempts: {[m['body'] for m in q2.dlq]}")

# EXERCISE: extend SimpleQueue with a `redrive(from_dlq=True)` method that moves DLQ messages
# back onto the main queue with receive_count reset to 0 -- the pattern used to reprocess a DLQ
# once the root cause (a bug, bad data) has been fixed.
