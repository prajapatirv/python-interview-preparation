# 03 - Kafka Producer and Consumer (Basic to Advanced)

**Chase project brush-up, point 3 of 4** (requested by Sujay: Spring Boot REST API · database connection from Spring Boot · Kafka consumer and producer · AWS S3, ECS, Aurora Postgres). Hub: [`../README.md`](../README.md).

**Functional requirement these answers are framed around (illustrative):** *"Card members search and book hotels with points, card or both. The booking service (Spring Boot on ECS Fargate behind an ALB) exposes REST APIs, stores bookings in Aurora PostgreSQL, publishes `BookingConfirmed` to Kafka (MSK) for notifications and rewards, and stores itinerary PDFs in S3. No double booking or double charge, p95 under 800 ms, survive an Aurora failover."*

**Stack to assume:** Spring for Apache Kafka (`KafkaTemplate`, `@KafkaListener`), Kafka on AWS MSK (or Confluent), Avro/JSON with a schema registry.
**Version notes:** Kafka 4.0 (March 2025) removed ZooKeeper (KRaft only); Spring for Apache Kafka 4.0 supports Kafka 4 clients and the new consumer rebalance protocol (KIP-848). Say which versions your project uses.

> **How to use this document:** always connect an answer to a failure mode (loss, duplicates, ordering, lag). Travel examples are illustrative; replace them with real facts from your project.

---

## Part 1 - Basic (Q1-Q10)

### Q1 [basic] What is Kafka and when do you use it?
A distributed, durable, partitioned commit log. Producers append events to topics; consumers read at their own pace and can replay because records are retained by time/size, not deleted on read. Use it to decouple services, stream events (booking created, payment confirmed), feed analytics, and absorb traffic spikes.

### Q2 [basic] Explain topic, partition, offset, broker, replica.
Topic: named stream of records. Partition: ordered, append-only slice of a topic (the unit of parallelism). Offset: position of a record inside a partition. Broker: a Kafka server. Replica: copy of a partition on another broker (replication factor usually 3); one is the leader that serves reads and writes.

### Q3 [basic] How does a producer send a message in Spring?
```java
@Service
class BookingEventPublisher {
  private final KafkaTemplate<String, BookingConfirmed> kafka;
  void publish(BookingConfirmed e) {
    kafka.send("booking.confirmed", e.bookingId(), e)   // key = bookingId
         .whenComplete((r, ex) -> { if (ex != null) log.error("send failed", ex); });
  }
}
```
`send` is asynchronous; always handle the result or failure.

### Q4 [basic] How does a consumer receive messages?
```java
@KafkaListener(topics = "booking.confirmed", groupId = "notification-service")
void on(BookingConfirmed event) { notifications.send(event); }
```
Spring creates a listener container that polls Kafka, deserialises records and calls your method.

### Q5 [basic] What is a consumer group?
Consumers with the same `group.id` share a topic's partitions: each partition is assigned to exactly one consumer in the group. This gives parallelism up to the number of partitions, and extra consumers sit idle. Different groups each receive all messages (publish/subscribe).

### Q6 [basic] What is the message key for?
The key decides the partition (hash of key). All records with the same key land on the same partition and keep order. Use the entity id (`bookingId`, `customerId`) as the key whenever order matters for that entity. No key means round-robin distribution and no per-entity ordering.

### Q7 [basic] What is an offset commit and why does it matter?
The consumer records how far it has processed in the internal `__consumer_offsets` topic. After a restart or rebalance it continues from the committed offset. Commit before processing = risk of losing messages; commit after processing = risk of duplicates (the normal choice, with idempotent handlers).

### Q8 [basic] Which serializers and formats do you use?
Strings/JSON (`JsonSerializer`) are simple but have no enforced schema. Avro or Protobuf with a Schema Registry give compact messages and compatibility checks. The registry stores schemas; each message carries a small schema id. Choose a format your consumers can evolve safely.

### Q9 [basic] At-most-once, at-least-once, exactly-once?
At-most-once: may lose messages. At-least-once: never loses but may deliver duplicates (practical default). Exactly-once: Kafka transactions + idempotent producer give it for Kafka-to-Kafka flows. For a database or other side effects, achieve "effectively once" with idempotent writes.

### Q10 [basic] How do you configure Kafka in `application.yml`?
```yaml
spring:
  kafka:
    bootstrap-servers: ${KAFKA_BROKERS}
    producer:
      acks: all
      properties: { enable.idempotence: true }
    consumer:
      group-id: notification-service
      enable-auto-commit: false
      auto-offset-reset: earliest
    listener:
      ack-mode: record
```

**Project hook (Part 1):** "Our booking service publishes `BookingConfirmed` keyed by bookingId; notification and rewards services consume it in separate groups."

---

## Part 2 - Mid Level (Q11-Q20)

### Q11 [mid] Which producer settings prevent message loss?
`acks=all` (wait for all in-sync replicas), `enable.idempotence=true` (broker dedupes retried batches; also the safe default in modern clients), bounded `delivery.timeout.ms`, topic `min.insync.replicas=2` with replication factor 3, and always handle the send callback. Tune throughput with `linger.ms`, `batch.size` and `compression.type` (lz4/zstd). Call `flush()` on shutdown (Spring does this when the context closes).

### Q12 [mid] How does ordering work and how can it break?
Ordering exists only within a partition. It breaks when: different partitions are used (no key), retries with `max.in.flight.requests.per.connection > 1` without idempotence, key changes, partition count increases (key-to-partition mapping changes), or non-blocking retry topics reorder events. Use a stable key and idempotence; if strict order matters per key, avoid retry-topic patterns for that flow.

### Q13 [mid] How do you handle consumer errors and poison messages in Spring Kafka?
Use `DefaultErrorHandler` with a back-off and a `DeadLetterPublishingRecoverer`.
```java
@Bean DefaultErrorHandler errorHandler(KafkaTemplate<Object,Object> t) {
  var recoverer = new DeadLetterPublishingRecoverer(t);   // sends to <topic>.DLT
  var backoff = new ExponentialBackOffWithMaxRetries(4); backoff.setInitialInterval(500);
  var h = new DefaultErrorHandler(recoverer, backoff);
  h.addNotRetryableExceptions(ValidationException.class);  // deserialization errors are already not retryable
  return h;
}
```
Non-retryable errors go straight to the dead-letter topic; retryable ones are retried with backoff. Configure `ErrorHandlingDeserializer` so a malformed record becomes a handled error instead of crashing the poll loop. Monitor the DLT size and build a replay tool.

### Q14 [mid] `@RetryableTopic` vs blocking retries?
Blocking retries (the error handler) retry in the poll loop; a long wait blocks the partition and risks exceeding `max.poll.interval.ms`. `@RetryableTopic` forwards failures to delayed retry topics (`-retry-0`, `-retry-1`) and finally a DLT, so the main topic keeps flowing. Trade-off: loses strict ordering per key and adds topics. Use blocking retries for short transient errors and retry topics for long ones.

### Q15 [mid] How do you scale consumers and what limits you?
Add consumer instances (or `concurrency` threads per instance) up to the partition count; more consumers than partitions do nothing. If processing is slow, optimise the handler (batch DB writes, avoid remote calls in the loop), increase partitions (planned, as it changes key mapping), or process batches (`batch listener`). Autoscale ECS tasks on consumer lag.

### Q16 [mid] What is a rebalance and how do you reduce its impact?
Partitions are reassigned when consumers join, leave or are considered dead (slow processing beyond `max.poll.interval.ms`, missed heartbeats beyond `session.timeout.ms`). During it, consumption pauses. Reduce: faster handlers or smaller `max.poll.records`, cooperative sticky assignment, static membership (`group.instance.id`) for rolling deploys, and graceful shutdown. The newer protocol (KIP-848, GA in Kafka 4.0) moves assignment to the broker and is incremental and smoother; clients opt in with `group.protocol=consumer`.

### Q17 [mid] How do you make a consumer idempotent?
Redelivery is normal, so handlers must tolerate duplicates. Store the processed `eventId` with a unique constraint in the same DB transaction as the side effect; use upserts (`ON CONFLICT DO NOTHING`); compare version numbers; make external calls idempotent with their own keys. Commit the offset only after the DB commit.

### Q18 [mid] Explain manual acknowledgment in Spring Kafka.
Set `enable.auto.commit=false` and `ack-mode: manual` (or `manual_immediate`); inject `Acknowledgment` and call `ack.acknowledge()` after successful processing. Record mode commits after each record, batch mode after each poll batch. Auto-commit is risky because it commits on a timer even if processing failed.

### Q19 [mid] How do you manage schemas and evolution?
Use a Schema Registry with Avro/Protobuf and BACKWARD compatibility (new consumers read old data): add fields with defaults, never rename or remove required fields. Disable auto-registration in production; CI registers schemas after a compatibility check. Upgrade consumers before producers under BACKWARD rules.

### Q20 [mid] How do you test Kafka producers and consumers?
Unit-test handler logic as plain methods. Integration-test with Testcontainers Kafka (or `@EmbeddedKafka`, KRaft-only in current versions) and Awaitility instead of `Thread.sleep`. Test retry and DLT paths, duplicate delivery, and schema compatibility. Use contract tests for event schemas shared between teams.

**Project hook (Part 2):** "We disabled auto-commit, committed after the DB write, sent poison messages to a DLT with the failure reason in headers, and built a replay endpoint."

---

## Part 3 - Advanced and Design (Q21-Q30)

### Q21 [advanced] Design reliable event publishing from the booking service (DB write + event).
Transactional outbox: insert the booking and an `outbox` row in one DB transaction; a relay (Debezium CDC or a poller with `FOR UPDATE SKIP LOCKED`) publishes to Kafka keyed by `bookingId`, then marks the row sent. Producer uses `acks=all` + idempotence. Event carries `eventId`, `type`, `version`, timestamp and payload. Consumers dedupe on `eventId`. Monitor outbox age (alert if the oldest unsent row exceeds a threshold).

### Q22 [advanced] Design the consumer that writes events into Aurora PostgreSQL without loss or duplicates.
Poll a batch -> validate (bad records to DLT) -> one transaction with an idempotent batch upsert (`INSERT ... ON CONFLICT (event_id) DO NOTHING` or a conditional update by version) -> commit the DB transaction -> **then** commit the Kafka offset. A crash between the DB commit and the offset commit causes redelivery, which the upsert turns into a no-op. Batch the writes for throughput; bound batch size so processing stays under `max.poll.interval.ms`.

### Q23 [advanced] Consumer lag keeps growing. Walk through the diagnosis.
1) Compare produce rate with consume rate. 2) Check per-record processing time (slow DB/remote call, GC pauses, CPU throttling in ECS). 3) Look for rebalance loops (poll interval exceeded, crash looping tasks). 4) Check partition skew (hot key). 5) Check a poison message being retried forever. 6) Check fewer consumers than expected. Fix: optimise the handler, batch writes, scale tasks up to partition count, split hot keys if ordering allows, and add alerts on lag trend (not a single spike).

### Q24 [advanced] How do Kafka transactions and "exactly-once" work, and where do they stop?
A transactional producer atomically writes output records and the consumed offsets (`sendOffsetsToTransaction`); consumers with `isolation.level=read_committed` see only committed data. Kafka Streams enables it with `exactly_once_v2`. It covers Kafka-to-Kafka only. A database or HTTP side effect is outside the transaction, so you still need idempotent writes (effectively-once).

### Q25 [advanced] Choose partition count and keys for a booking-events topic.
Partitions >= the maximum consumers you want in parallel, sized from target throughput divided by per-partition throughput, with growth room (you can increase but not decrease, and increases change key mapping). Key by `bookingId` for per-booking ordering. Beware hot keys (one very busy customer or supplier); if ordering is only needed per booking, a high-cardinality key spreads load well. Document the ordering guarantee consumers may rely on.

### Q26 [advanced] How do you run Kafka securely on AWS MSK from a Spring Boot app on ECS?
Private subnets and security groups allowing only the ECS tasks; TLS in transit; authentication with IAM (`SASL_SSL` + `AWS_MSK_IAM` using the task role) or mTLS/SCRAM; topic-level ACLs/IAM policies (least privilege per service); KMS encryption at rest; no secrets in code. MSK stays in the VPC, so ECS tasks reach brokers through the VPC network. Note: AWS does not convert a ZooKeeper-based MSK cluster to KRaft in place; plan a new cluster and migration.

### Q27 [advanced] How do you replay or backfill events safely?
Replay from a retained topic by resetting consumer-group offsets to a timestamp (`kafka-consumer-groups --reset-offsets`) or use a separate replay consumer group writing to the same idempotent sink. Pause live processing if ordering with live events matters, throttle the replay, and ensure handlers are idempotent. For long history use compacted topics or an S3 archive (Kafka Connect S3 sink).

### Q28 [advanced] Design a notification flow (email/push) driven by booking events with retries and no duplicates.
`BookingConfirmed` -> notification service consumes (group per channel) -> idempotency table keyed by `eventId + channel` -> call provider (SES/push) with provider idempotency key and timeout -> on transient failure use retry topics with backoff -> on permanent failure go to DLT and alert -> store delivery status for support. Rate-limit per provider and use a circuit breaker so a provider outage does not stall the partition.

### Q29 [advanced] What would you monitor for Kafka producers and consumers in production?
Producer: send error rate, retry rate, request latency, batch size, record-error-rate, outbox age. Consumer: **lag per partition**, records consumed rate, processing duration histogram, rebalance count, DLT/retry-topic rates, commit failures. Broker (managed by platform): under-replicated partitions, offline partitions, ISR shrink, request latency. Alert on sustained lag growth, DLT growth and outbox age, with runbooks.

### Q30 [advanced] Kafka vs SQS/SNS vs RabbitMQ for this platform - how do you choose?
Kafka: high throughput, ordered per key, retention and replay, many independent consumers, event streaming and CDC. SQS/SNS: fully managed, simple queues and fan-out, per-message visibility timeout and DLQ, no ordering by default (FIFO has limits), easy for task queues. RabbitMQ: rich routing, per-message acks, priorities, request/reply. Pick Kafka for the booking event backbone and analytics; use SQS for simple work queues if the team prefers managed simplicity. Explain the trade-off rather than naming a winner.

**Project hook (Part 3):** "The issue we solved was [real: lag spike after deploy / duplicate notifications / rebalance loop]; I checked lag per partition, found [cause], and prevented a repeat with [alert, idempotency, config change]."

---

## Quick revision card
- Producer: key by entity, `acks=all`, idempotence on, handle callbacks.
- Consumer: manual commit after success, idempotent handler, DLT for poison messages.
- Order only inside a partition; scale only up to partition count.
- DB + event = outbox. DB sink = idempotent upsert, then commit offset.
- Watch lag trend, DLT size, rebalances, outbox age.

## 60-second answer for this point
"The booking service writes the booking and an outbox row in one transaction, and a relay publishes `BookingConfirmed` keyed by bookingId with acks=all and idempotence, so per-booking order holds and nothing is lost. Notification and rewards services consume in separate groups with auto-commit off, committing only after their idempotent DB write. Poison messages go through DefaultErrorHandler with backoff to a dead-letter topic, and retry topics handle long transient failures. Consumers scale up to the partition count on ECS based on lag. We monitor lag per partition, DLT growth, rebalances and outbox age. On MSK we use IAM auth over TLS from the task role."
