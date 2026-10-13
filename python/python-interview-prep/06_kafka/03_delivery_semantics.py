"""
The three delivery semantics, shown as a runnable SIMULATION (no broker needed) so you can see
the actual data-loss / duplication behavior without standing up Kafka. The comments map each
line back to the equivalent real confluent-kafka call.

Run me: python 03_delivery_semantics.py
"""
import random


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


class FakeBroker:
    """A tiny in-memory stand-in for a Kafka partition: an ordered log + per-consumer offset."""

    def __init__(self, messages):
        self.log = list(messages)
        self.committed_offset = 0  # equivalent to the group's committed offset for this partition

    def poll(self):
        if self.committed_offset >= len(self.log):
            return None
        return self.committed_offset, self.log[self.committed_offset]

    def commit(self, offset):
        # real equivalent: consumer.commit(message=msg, asynchronous=False)
        self.committed_offset = offset + 1


def simulate(name, commit_before_processing, crash_after_message_index, messages):
    """Runs the consume loop, injecting a crash after a given message, then restarts and drains
    the rest -- exactly like a process dying and a new one picking up from the last commit."""
    broker = FakeBroker(messages)
    delivered_to_business_logic = []
    crashed_once = False

    while True:
        result = broker.poll()
        if result is None:
            break
        offset, message = result

        if commit_before_processing:
            # AT-MOST-ONCE shape: commit() happens BEFORE process(). Real equivalent:
            #   consumer.commit(message=msg, asynchronous=False); process_order(msg)
            broker.commit(offset)
            if not crashed_once and offset == crash_after_message_index:
                crashed_once = True
                print(f"  [{name}] *** process crashes right here, before finishing this message ***")
                continue  # the "process" dies mid-handling; message is lost, never processed
            delivered_to_business_logic.append(message)
        else:
            # AT-LEAST-ONCE shape: process() happens BEFORE commit(). Real equivalent:
            #   process_order(msg); consumer.commit(message=msg, asynchronous=False)
            delivered_to_business_logic.append(message)  # processing side effect ALREADY happened
            if not crashed_once and offset == crash_after_message_index:
                crashed_once = True
                print(f"  [{name}] *** process crashes right here, AFTER processing but BEFORE commit ***")
                continue  # commit never runs -> committed_offset unchanged -> this message is
                          # redelivered on the next poll() and processed AGAIN below -> duplicate
            broker.commit(offset)

    return delivered_to_business_logic


messages = [f"order-{i}" for i in range(5)]

section("AT-MOST-ONCE: commit BEFORE processing -- a crash LOSES the in-flight message")
result = simulate("at-most-once", commit_before_processing=True, crash_after_message_index=2, messages=messages)
print("  business logic actually saw:", result)
print(f"  MISSING: {set(messages) - set(result)}  <- lost forever, never reprocessed")

section("AT-LEAST-ONCE: commit AFTER processing -- a crash causes a DUPLICATE, never a loss")
result = simulate("at-least-once", commit_before_processing=False, crash_after_message_index=2, messages=messages)
print("  business logic actually saw:", result)
dupes = [m for m in set(result) if result.count(m) > 1]
print(f"  DUPLICATED: {dupes}  <- 'order-2' was processed twice, nothing was lost")
print("  this is exactly why at-least-once consumers MUST be idempotent (see 06_kafka/04_retry_topic_dlq.py)")

section("EXACTLY-ONCE (conceptual): idempotent producer + transactional consume-transform-produce")
print("""
  Real Kafka gives you this via:
    1. enable.idempotence=true on the producer -- the broker deduplicates retried batches
       using a producer ID + per-partition sequence number.
    2. A transactional producer (transactional.id=...) wraps BOTH the output produce() calls
       AND the input consumer's offset commit in one atomic transaction via
       send_offsets_to_transaction(). Either both happen or neither does.
    3. Downstream consumers set isolation.level=read_committed so they never see the
       products of an aborted transaction.

  This only covers Kafka-to-Kafka flows. If the sink is a database, you still need an
  idempotent write there too (upsert keyed by event ID) -- see 06_kafka/04_retry_topic_dlq.py
  and 07_caching_queues/ for that pattern applied to external systems.
""")
