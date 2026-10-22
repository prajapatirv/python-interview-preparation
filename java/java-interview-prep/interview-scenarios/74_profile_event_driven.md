---
id: profile-java-genai-event-driven
title: Java + GenAI profile (5/9): Event-driven architecture, 15 functional-requirement questions
stack: java
skill: kafka
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).
Kafka is the default broker in these answers (Kafka 4.x is KRaft-only, no ZooKeeper); alternatives are named where they fit better.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] What is event-driven architecture, and what kinds of events are there?
tags: event-driven, events, event-notification, event-carried-state-transfer, event-sourcing, decoupling, profile-java-genai

**Start here: the concepts**
- **Event:** an immutable fact that something happened (`PaymentCaptured`), named in past tense.
- **Producer** publishes without knowing consumers; **consumers** react independently.
- Four styles (Martin Fowler): **event notification** (thin, "go fetch"), **event-carried state transfer** (the event has the data), **event sourcing** (events are the source of truth), **CQRS** (read models built from events).

**The live scenario (functional requirement)**
*FR: "When a customer's card is reported stolen: block the card, cancel pending travel bookings, alert fraud, notify the customer, and update the AI assistant so it doesn't offer that card."* Today the card service calls 5 services synchronously, and one outage blocks the card block.

**What the interviewer is really checking**
Benefits and costs of EDA, and choosing the event style.

**How I answer it**
1. The card service blocks the card in its DB and publishes `CardReportedStolen` (via outbox). Its job ends there.
2. Booking, fraud, notification and assistant services each subscribe and act; one being down doesn't stop the others; it catches up from Kafka when back.
3. **Event style:** event-carried state transfer (card id, customer id, last 4, timestamp) so consumers don't call back the card service, avoiding a thundering herd of lookups.
4. Adding a sixth reaction later (e.g. rewards freeze) needs no change in the card service.
5. Document events as contracts (AsyncAPI + schema registry).

**Trade-offs and what can go wrong**
- Flow becomes implicit: "what happens when X?" needs tracing and documentation.
- Eventual consistency between services.
- Fat events leak internal models; thin events cause callback storms. Choose deliberately.

**How I'd monitor it**
Consumer lag per subscriber, end-to-end time from event to each reaction, DLQ counts.

**Follow-ups to expect**
- *Event vs message vs command?* -> Command asks one receiver to do something; event announces a fact to anyone.
- *When is EDA a bad idea?* -> When the caller needs an immediate answer, or for simple CRUD with one consumer.
- *What is the outbox for?* -> Atomically saving state and the event.

**60-second answer**
"In event-driven architecture a service records a fact and publishes it, and others react on their own. When a card is reported stolen, the card service blocks it and publishes CardReportedStolen; booking cancellations, fraud, notifications and the AI assistant each subscribe, so one outage doesn't stop the block and a new reaction needs no change to the producer. I use event-carried state transfer so consumers don't call back, publish through an outbox, and track lag and end-to-end time per subscriber."

### Q2 [senior] Design Kafka topics, partitions and keys for booking events with ordering requirements.
tags: kafka, topics, partitions, message-key, ordering, consumer-group, profile-java-genai

**Start here: the concepts**
- **Topic** split into **partitions**; order is guaranteed **only within a partition**.
- **Key** -> partition (hash of key), so the same key always lands in the same partition.
- **Consumer group:** each partition is consumed by one consumer in the group; parallelism = partition count.

**The live scenario (functional requirement)**
*FR: "Booking events (created, modified, cancelled) must be processed in order per booking; we expect 20,000 events/s at peak; 12 downstream consumers."*

**What the interviewer is really checking**
Key choice for ordering, partition count for throughput, and the hot-key problem.

**How I answer it**
1. **Key = bookingId**: all events of one booking go to one partition, so they stay ordered. Different bookings process in parallel.
2. **Partition count:** if one consumer handles ~1,000 events/s, 20,000/s needs ≥ 20; I'd choose 48 for headroom (adding partitions later remaps keys and breaks ordering during the change).
3. **Producer:** `acks=all`, `enable.idempotence=true` (default in recent clients) so retries don't duplicate or reorder.
4. **Replication factor 3, `min.insync.replicas=2`** for durability.
5. **Topic per event family** (`booking-events`) with an event type header, rather than one topic per event type, so ordering across created/modified/cancelled is preserved.
6. **Hot keys:** a corporate account generating 30% of events would skew one partition; key by booking, not account.

**Trade-offs and what can go wrong**
- Too many partitions increases broker metadata, rebalance time and end-to-end latency.
- Increasing partitions changes key -> partition mapping.
- Consumers processing in parallel threads inside one partition break ordering unless they shard by key.

**How I'd monitor it**
Per-partition lag and throughput (skew), under-replicated partitions, produce latency and errors.

**Follow-ups to expect**
- *Global ordering?* -> Single partition only, which kills parallelism; rarely truly needed.
- *How many consumers?* -> Up to the partition count; extra ones sit idle.
- *Retention?* -> Time/size based, or compacted topics for "latest state per key".

**60-second answer**
"Ordering in Kafka is per partition, so I key booking events by booking id: one booking's events stay in order while different bookings run in parallel. At 20,000 events a second, with about 1,000 per consumer, I need at least 20 partitions, so I'd pick around 48 for headroom, since adding partitions later remaps keys. Idempotent producers with acks=all, replication 3 with min-ISR 2, one topic per event family so created-modified-cancelled stay ordered, and I watch per-partition skew for hot keys."

### Q3 [senior] At-least-once, at-most-once, exactly-once: how do you make consumers safe?
tags: delivery-semantics, idempotent-consumer, exactly-once, deduplication, kafka-transactions, offsets, profile-java-genai

**Start here: the concepts**
- **At-most-once:** commit before processing; a crash loses messages.
- **At-least-once:** process then commit; a crash causes redelivery (duplicates). The practical default.
- **Exactly-once (Kafka EOS):** transactions make read-process-write **within Kafka** atomic; side effects outside Kafka (DB, email, payment API) still need idempotency.

**The live scenario (functional requirement)**
*FR: "Award loyalty points for each completed trip; a customer must never get points twice or miss them, even through rebalances and crashes."*

**What the interviewer is really checking**
That "exactly-once" end to end really means at-least-once delivery + idempotent processing.

**How I answer it**
1. Consume with at-least-once: manual/after-processing commits (Spring Kafka's default container ack mode commits after the listener returns).
2. **Idempotent consumer:** each event has a unique `eventId`. In the **same DB transaction** that adds points, insert `eventId` into a `processed_events` table with a unique constraint. A duplicate hits the constraint -> skip.
3. Or make the operation naturally idempotent: `INSERT ... ON CONFLICT (trip_id) DO NOTHING` on a points ledger keyed by trip.
4. Kafka transactions (`transactional.id`, `isolation.level=read_committed`) only when the output is another Kafka topic (stream processing).
5. External APIs: pass an idempotency key so the provider dedupes.

**Trade-offs and what can go wrong**
- The dedupe table grows; keep it for longer than the maximum redelivery window, then purge.
- Committing offsets in a different transaction than the DB write is fine **only** because the write is idempotent.
- Async processing inside the listener (handing off to another thread) and committing early silently becomes at-most-once.

**How I'd monitor it**
Duplicate-detected counter, reconciliation job (trips completed vs points awarded), consumer errors and lag.

**Follow-ups to expect**
- *Why do duplicates happen?* -> Producer retries, consumer crash before commit, rebalances.
- *Does idempotent producer solve this?* -> Only producer-side duplicates per partition, not consumer reprocessing.
- *Outbox + idempotent consumer?* -> The standard pair for reliable cross-service events.

**60-second answer**
"I treat exactly-once as at-least-once delivery plus idempotent processing. The listener commits after processing, so crashes cause redelivery, never loss. The points service inserts the event id into a processed-events table with a unique constraint in the same transaction as the points update, or uses an upsert keyed by trip id, so a duplicate is a no-op. Kafka transactions help only when the output is another Kafka topic. A nightly reconciliation proves trips and points match."

### Q4 [senior] Publish an event reliably when you also update the database: the transactional outbox.
tags: transactional-outbox, cdc, debezium, dual-write, reliability, spring-modulith, profile-java-genai

**Start here: the concepts**
- **Dual-write problem:** writing to the DB and then to Kafka isn't atomic; one can succeed while the other fails.
- **Transactional outbox:** write the event into an `outbox` table in the same DB transaction; a relay publishes it to Kafka.
- **Relay options:** polling publisher, or **CDC** (Debezium reading the DB log).

**The live scenario (functional requirement)**
*FR: "When a booking is confirmed, the confirmation must be saved and `BookingConfirmed` must reach Kafka, always both or neither."* An incident: the DB commit succeeded, Kafka was briefly unavailable, and 1,200 customers never got confirmation emails.

**What the interviewer is really checking**
Understanding of dual writes and the standard solution's details (ordering, cleanup, duplicates).

**How I answer it**
1. In one local transaction: update `booking` and insert into `outbox (id, aggregate_id, type, payload, created_at)`.
2. **Relay:** Debezium's outbox event router streams new rows from the WAL/binlog to the `booking-events` topic, keyed by `aggregate_id` so order per booking is kept.
3. Relay delivery is at-least-once -> consumers are idempotent using the outbox `id` as event id.
4. Clean up outbox rows after publishing (or let CDC read and delete on a schedule).
5. Simpler stacks: a polling relay (`SELECT ... FOR UPDATE SKIP LOCKED` in batches) or **Spring Modulith's event publication registry** with externalisation.

**Trade-offs and what can go wrong**
- Polling adds latency and DB load; CDC adds infrastructure (Kafka Connect, Debezium).
- Publishing the event *inside* the transaction with KafkaTemplate before commit can send events for rolled-back data.
- Outbox table growth if the relay stops; alert on age of the oldest unpublished row.

**How I'd monitor it**
Oldest unpublished outbox row age, relay throughput, Debezium connector status and lag.

**Follow-ups to expect**
- *Listen to yourself pattern?* -> Publish first, then update your own state from the event; works but complicates reads.
- *Why not Kafka transactions with the DB?* -> Kafka can't join a DB transaction (no XA).
- *Ordering with polling?* -> Order by sequence per aggregate; single relay per partition range.

**60-second answer**
"Writing to the database and then Kafka is a dual write: one can fail, which is how 1,200 customers missed their emails. With the outbox, the booking update and an outbox row commit in one local transaction, and a relay, Debezium CDC or a polling publisher, pushes the row to Kafka keyed by booking id. Delivery is at-least-once, so consumers dedupe on the outbox id. I alert on the age of the oldest unpublished row, and Spring Modulith's event registry is a lighter option for smaller apps."

### Q5 [senior] Implement a choreographed saga with events and compensations.
tags: saga, choreography, compensation, kafka, eventual-consistency, distributed-transactions, profile-java-genai

**Start here: the concepts**
- **Choreography:** no coordinator; each service listens for events and emits the next.
- **Compensation:** a semantic undo (refund, release), not a database rollback.
- Fits short flows (2–4 steps) with clear owners.

**The live scenario (functional requirement)**
*FR: "Redeem loyalty points for a hotel: reserve points, book the room with the supplier, then confirm; if the supplier fails, points must return to the customer within a minute."*

**What the interviewer is really checking**
That you can design the event flow, failure paths and idempotency without a central coordinator.

**How I answer it**
1. `RedemptionRequested` (redemption service) -> **points service** reserves points (status HELD) -> `PointsReserved`.
2. **Hotel service** books with the supplier -> `HotelBooked` or `HotelBookingFailed`.
3. On `HotelBooked`, points service converts HELD -> DEBITED and redemption marks CONFIRMED.
4. On `HotelBookingFailed`, points service **releases** the hold -> `PointsReleased`; redemption marks FAILED and notifies the customer.
5. Every handler is idempotent (event id), state transitions are guarded (can't release a DEBITED hold), and all events carry the `redemptionId` for correlation.
6. **Timeouts:** a scheduled sweeper releases holds older than 10 minutes with no outcome (the supplier never answered).

**Trade-offs and what can go wrong**
- As steps grow, the flow is spread over many services; switch to orchestration (Q2 in the microservices pack) when it gets hard to follow.
- Cyclic event dependencies between services.
- Supplier "unknown" outcomes (timeout after sending): query the supplier's status before compensating.

**How I'd monitor it**
Redemptions by status, holds older than N minutes, compensation rate, end-to-end duration.

**Follow-ups to expect**
- *Pivot transaction?* -> The step after which the saga can't be compensated, only completed (supplier confirmation).
- *How to visualise choreography?* -> Distributed traces plus an event catalogue.
- *Semantic lock?* -> The HELD status that prevents the points being spent twice.

**60-second answer**
"With choreography each service reacts to the previous event. Redemption requested, points service holds the points; points reserved, hotel service books with the supplier; on success the hold becomes a debit and the redemption is confirmed, on failure the points service releases the hold and the customer is told. Handlers are idempotent, transitions are guarded, everything carries the redemption id, and a sweeper releases holds with no outcome after ten minutes. Past three or four steps I'd switch to orchestration."

### Q6 [senior] Evolve event schemas without breaking consumers: Avro/Protobuf and a schema registry.
tags: schema-registry, avro, protobuf, schema-evolution, compatibility, contracts, profile-java-genai

**Start here: the concepts**
- **Schema registry:** stores versioned schemas per topic subject; producers register, consumers fetch by id embedded in each message.
- **Compatibility modes:** BACKWARD (new consumers read old data; the default in Confluent's registry), FORWARD (old consumers read new data), FULL (both), plus TRANSITIVE variants.
- **Safe changes:** add optional fields with defaults; unsafe: rename, remove required, change types.

**The live scenario (functional requirement)**
*FR: "Add `loyaltyTier` and change `price` to amount + currency in `BookingConfirmed`; 12 consumer teams deploy on their own schedules."*

**What the interviewer is really checking**
Contract discipline and how the registry enforces it in CI.

**How I answer it**
1. Serialisation with Avro or Protobuf via the registry serializers (JSON Schema also works).
2. Compatibility **FULL_TRANSITIVE** (or BACKWARD at minimum) on the subject; the registry rejects incompatible schemas at producer registration, and I check in CI with the registry Maven plugin.
3. `loyaltyTier`: add as optional with a default -> compatible.
4. `price` type change is breaking -> **add** a new `priceDetail {amount, currency}` field, keep `price` populated (deprecated) until all consumers migrate, then remove in a later version, or publish a new topic version `booking-events.v2` for big changes.
5. Consumers use **tolerant readers**: ignore unknown fields.
6. An event catalogue (AsyncAPI) documents ownership and versions.

**Trade-offs and what can go wrong**
- Plain JSON without schemas breaks consumers silently at runtime.
- Registry is a critical dependency; clients cache schemas.
- Protobuf field numbers must never be reused.

**How I'd monitor it**
Deserialisation errors per consumer, schema registration failures in CI, consumers still reading deprecated fields.

**Follow-ups to expect**
- *Avro vs Protobuf?* -> Both compact with evolution; Protobuf fits gRPC estates, Avro is common in the Kafka ecosystem.
- *What is in each message?* -> A magic byte and the schema id, then the payload.
- *Topic per version?* -> For breaking changes, with dual publishing during migration.

**60-second answer**
"Events are contracts, so I use Avro or Protobuf with a schema registry set to full or backward compatibility, and CI fails a producer build that registers an incompatible schema. Adding loyaltyTier with a default is safe. Changing price's type isn't, so I add a new priceDetail field, keep price filled until all twelve teams migrate, then drop it later, or publish a v2 topic for bigger changes. Consumers are tolerant readers, and I watch deserialisation errors per consumer."

### Q7 [senior] Handle poison messages and failures: retries, retry topics and DLT in Spring Kafka.
tags: dead-letter-topic, retry-topic, retryabletopic, defaulterrorhandler, poison-message, spring-kafka, profile-java-genai

**Start here: the concepts**
- **Poison message:** one that always fails (bad data); without handling it blocks its partition forever.
- **Blocking retries:** retry in place a few times (`DefaultErrorHandler` with backoff); order preserved, partition paused meanwhile.
- **Non-blocking retries:** move the message to retry topics with delays (`@RetryableTopic`), then a **dead-letter topic (DLT)**; the partition keeps flowing but order is lost for that message.

**The live scenario (functional requirement)**
*FR: "The embedding consumer indexes documents into the vector store; a malformed document or a vector-store hiccup must not stop the other 50,000 documents."*

**What the interviewer is really checking**
Distinguishing transient vs permanent errors and the ordering trade-off.

**How I answer it**
1. **Classify:** deserialisation/validation errors are permanent -> straight to DLT, no retries (`addNotRetryableExceptions`).
2. **Transient** (vector store 503, embedding API 429): retry.
3. For this pipeline ordering doesn't matter, so **non-blocking** `@RetryableTopic(attempts = "4", backoff = @Backoff(delay = 2000, multiplier = 3))`: retries at 2 s, 6 s, 18 s on retry topics, then DLT.
4. Where ordering matters (booking state changes), use **blocking** `DefaultErrorHandler` with a few backoff retries, then `DeadLetterPublishingRecoverer`.
5. DLT records keep original headers + exception info; a **replay tool** re-publishes fixed messages.
6. `ErrorHandlingDeserializer` so bad bytes don't crash the consumer loop.

**Trade-offs and what can go wrong**
- Infinite blocking retries on a poison message = a stuck partition and growing lag.
- Non-blocking retries reorder messages for the same key.
- A DLT nobody watches is just a slower way to lose data.

**How I'd monitor it**
DLT message rate (alert on any for critical topics), retry topic depth, consumer lag, error type breakdown.

**Follow-ups to expect**
- *Back off on a whole dependency outage?* -> Pause the container (`KafkaListenerEndpointRegistry`) or let a circuit breaker stop consumption.
- *What headers are on DLT records?* -> Original topic, partition, offset, exception class and message.
- *Retry storms?* -> Exponential backoff with jitter and limited attempts.

**60-second answer**
"First I separate permanent from transient errors. Bad data goes straight to the dead-letter topic with no retries, and an ErrorHandlingDeserializer keeps bad bytes from killing the consumer. Transient failures like a vector-store 503 get retries. For the embedding pipeline order doesn't matter, so I use non-blocking `@RetryableTopic` with exponential delays and then the DLT, and the other 50,000 documents keep flowing. For ordered booking events I use blocking retries with DefaultErrorHandler. DLTs are alerted on and have a replay tool."

### Q8 [senior] Consumer lag is growing. How do you diagnose and scale consumers?
tags: consumer-lag, scaling, partitions, max-poll-records, rebalancing, keda, profile-java-genai

**Start here: the concepts**
- **Lag:** latest offset minus committed offset per partition.
- **Parallelism ceiling:** consumers in a group ≤ partitions.
- **Rebalance:** partitions reassigned when consumers join/leave or miss `max.poll.interval.ms`. Kafka 4.0 made the new consumer rebalance protocol (KIP-848) generally available, with incremental, broker-driven assignment.

**The live scenario (functional requirement)**
*FR: "Price-change events must reach the search index within 30 seconds."* During a sale, lag hits 2 million and prices on the site are 20 minutes stale.

**What the interviewer is really checking**
A diagnosis order before "add more pods".

**How I answer it**
1. **Where:** lag on all partitions (throughput problem) or a few (hot key / stuck message)?
2. **Why slow:** processing time per record. Here each event did a synchronous index write: 15 ms × records.
3. **Fix processing first:** batch writes to the search index (`@KafkaListener` batch mode, bulk API of 500 docs) -> 20× faster.
4. **Then scale:** add consumers up to the partition count (24); with KEDA on lag.
5. **Tune:** `max.poll.records` and `max.poll.interval.ms` so batches finish within the interval (otherwise rebalance storms), `fetch.min.bytes`/`fetch.max.wait.ms` for throughput.
6. **Compaction trick:** price events are "latest wins", so coalesce by key within a batch and skip superseded updates.
7. Long-term: more partitions if consumers hit the ceiling.

**Trade-offs and what can go wrong**
- Adding consumers beyond partitions does nothing.
- Big batches increase the redo window after a crash; idempotent writes make that safe.
- Rebalance storms from slow processing look like a scaling problem but are a timeout problem.

**How I'd monitor it**
Lag per partition and in seconds (time lag), records/s per consumer, processing time, rebalance count.

**Follow-ups to expect**
- *Lag in seconds vs messages?* -> Time lag is what the SLO is about.
- *Static membership?* -> `group.instance.id` reduces rebalances on restarts.
- *Share groups?* -> Kafka's queue semantics (KIP-932) let more consumers than partitions share work; check maturity in your Kafka version.

**60-second answer**
"First I check whether lag is on every partition or a few: a few means a hot key or a stuck message, all means throughput. Here each event did a synchronous index write, so I switched to batch listening with bulk index writes and coalesced price updates by key, about 20 times faster. Then I scaled consumers up to the partition count with KEDA on lag, tuned max.poll.records so batches finish inside the poll interval to avoid rebalance storms, and alerted on lag in seconds against the 30-second SLO."

### Q9 [architect] When would you use event sourcing, and what does it cost?
tags: event-sourcing, cqrs, audit, snapshots, replay, aggregates, profile-java-genai

**Start here: the concepts**
- **Event sourcing:** the state of an aggregate is the sequence of its events; current state = replay (fold) of events.
- **Snapshots:** periodic saved state to avoid replaying thousands of events.
- **Projections:** read models built from the event stream (CQRS).

**The live scenario (functional requirement)**
*FR: "A loyalty points ledger must show exactly how every balance was reached, support disputes years later, and let us rebuild balances if a calculation bug is found."*

**What the interviewer is really checking**
That you know when its strengths (audit, temporal queries, replay) justify its complexity.

**How I answer it**
1. The ledger is a natural fit: `PointsEarned`, `PointsRedeemed`, `PointsExpired`, `PointsAdjusted` are the business language; balances are derived.
2. Event store: a DB table (`stream_id, version, type, payload`) with a unique `(stream_id, version)` for **optimistic concurrency**, or a dedicated store (EventStoreDB, Axon Server). Kafka is the distribution channel, not the primary store (no per-entity optimistic concurrency).
3. Commands load the account stream (or snapshot + newer events), validate (enough points?), append new events.
4. Projections build balance views, statements and analytics; a bug fix = fix the projection and **replay**.
5. Events are immutable; corrections are new events (`PointsAdjusted`), which is exactly what auditors want.

**Trade-offs and what can go wrong**
- Schema evolution of old events forever (upcasters).
- GDPR erasure conflicts with immutability; use crypto-shredding (encrypt personal data per customer, delete the key).
- Steep learning curve; most of a system doesn't need it. Apply to the ledger, not to customer profiles.

**How I'd monitor it**
Append latency, concurrency conflicts, projection lag, replay duration.

**Follow-ups to expect**
- *Event sourcing vs audit table?* -> An audit table records changes alongside state; ES makes events the state.
- *How many events before a snapshot?* -> Measure; often every few hundred.
- *Frameworks?* -> Axon Framework is the established Java option.

**60-second answer**
"Event sourcing fits a points ledger: balances are derived from earned, redeemed, expired and adjusted events, so every balance is explainable, disputes years later are answerable, and a calculation bug is fixed by correcting the projection and replaying. The store is an append-only table with a unique stream-and-version for optimistic concurrency; Kafka distributes events but isn't the store. The costs are schema evolution forever, GDPR handled with crypto-shredding, and complexity, so I use it for the ledger, not everywhere."

### Q10 [senior] Replay or reprocess events after a bug, without breaking downstream systems.
tags: replay, reprocessing, offsets, compacted-topics, idempotency, backfill, profile-java-genai

**Start here: the concepts**
- **Retention:** Kafka keeps events for a time/size; **compacted topics** keep the latest value per key forever.
- **Offset reset:** `kafka-consumer-groups --reset-offsets --to-datetime ...` to re-read.
- **Replay safety** depends on idempotent consumers and side effects.

**The live scenario (functional requirement)**
*FR: "A bug in the chunking logic stored bad embeddings for 3 days of documents; re-index them without re-sending notifications or double-counting analytics."*

**What the interviewer is really checking**
Safe, scoped replay planning, especially side effects.

**How I answer it**
1. **Scope:** only the indexing consumer's output is wrong; other consumers of `document-events` are fine.
2. **Replay only that consumer group:** stop it, reset offsets to 3 days ago (by timestamp), deploy the fix, restart. Other groups are untouched.
3. Or a **separate replay consumer group** writing to a new index version, then switch the alias (blue-green index): zero impact on live search during re-indexing.
4. Consumer writes are **upserts** keyed by document+chunk id, so reprocessing replaces bad vectors rather than duplicating.
5. **Side effects** (notifications) live in other consumers, so they are not replayed; if one consumer does both, guard side effects with a "replay mode" flag or dedupe table.
6. If retention is shorter than needed, replay from the source of truth (object storage of the documents) via a backfill job.

**Trade-offs and what can go wrong**
- Resetting a shared group re-triggers everything that group does.
- Replays compete with live traffic; throttle them.
- Mixed old/new embeddings in one index corrupt similarity search; re-index into a new version.

**How I'd monitor it**
Replay progress (offset vs target), live lag of other groups, index document counts, retrieval quality on a golden set before switching.

**Follow-ups to expect**
- *Infinite retention?* -> Possible (tiered storage in Kafka moves old segments to object storage cheaply).
- *Why re-embed everything when the model changes?* -> Vectors from different embedding models aren't comparable.
- *How to find affected records?* -> Timestamps plus the code version recorded in metadata.

**60-second answer**
"I scope it: only the indexing consumer produced bad output, so I replay only that, never a shared consumer group. Best is a separate replay group reading from three days back into a new index version, then switching the alias, so live search isn't affected. Writes are upserts by document and chunk id, so nothing duplicates, and notifications live in other consumers so they don't fire again. If Kafka retention is too short, I backfill from object storage, and I check retrieval quality on a golden set before switching."

### Q11 [senior] Kafka, RabbitMQ, SQS/SNS or EventBridge/Event Grid: how do you choose a broker?
tags: kafka, rabbitmq, sqs, sns, eventbridge, broker-selection, profile-java-genai

**Start here: the concepts**
- **Kafka:** distributed log; high throughput, retention and replay, ordering per partition, consumer groups.
- **RabbitMQ:** message broker with flexible routing (exchanges), per-message acks, priority; messages leave once consumed (streams feature adds log semantics).
- **Cloud managed:** SQS (queues), SNS (fan-out), EventBridge (event bus with rules), Azure Service Bus / Event Grid / Event Hubs.

**The live scenario (functional requirement)**
*FR: "We need (a) a 50k events/s booking event stream replayable for analytics and AI indexing, (b) a task queue for PDF generation with per-task retries, (c) routing of partner webhooks to the right handler."*

**What the interviewer is really checking**
Matching tool semantics to each requirement, not one-broker-fits-all.

**How I answer it**
1. **(a) Kafka** (self-managed with Strimzi, or MSK / Confluent Cloud / Event Hubs Kafka API): throughput, retention, replay, many independent consumers.
2. **(b) Task queue:** SQS or RabbitMQ: per-message ack, visibility timeout, DLQ, competing consumers, no partition ceiling. Kafka can do it but with more ceremony.
3. **(c) Routing:** EventBridge/Event Grid rules or RabbitMQ topic exchanges: content-based routing without code.
4. Consider ops capacity: a managed service beats running a cluster for a small team.
5. Keep application code behind an abstraction (Spring Cloud Stream binders or ports) if switching is plausible.

**Trade-offs and what can go wrong**
- Kafka for small, simple queues is overkill to operate.
- SQS standard queues are at-least-once and not ordered (FIFO queues have throughput limits).
- Multiple brokers mean multiple skill sets and monitoring stacks.

**How I'd monitor it**
Queue depth/age (SQS `ApproximateAgeOfOldestMessage`), Kafka lag, DLQ counts, broker health.

**Follow-ups to expect**
- *Kafka for request-reply?* -> Possible, rarely ideal.
- *Ordering in SQS?* -> FIFO queues with message group ids.
- *Pulsar?* -> Log + queue semantics with tiered storage; fewer people know it.

**60-second answer**
"I match the semantics. The 50,000-a-second booking stream that analytics and AI indexing replay is Kafka, managed if possible. PDF generation is a task queue, so SQS or RabbitMQ, with per-message acks, visibility timeouts and a DLQ, and no partition ceiling. Partner webhook routing is content-based, which EventBridge rules or a RabbitMQ topic exchange do without code. I weigh the team's ops capacity, since managed beats self-run for a small team, and keep the code behind a binder or port."

### Q12 [mid] Spring Kafka vs Spring Cloud Stream: which do you use?
tags: spring-kafka, spring-cloud-stream, kafkalistener, functional-bindings, binder, profile-java-genai

**Start here: the concepts**
- **Spring for Apache Kafka:** `KafkaTemplate`, `@KafkaListener`, error handlers, transactions; Kafka-specific, full control.
- **Spring Cloud Stream:** binder abstraction (Kafka, RabbitMQ, Pulsar, Kinesis...) with functional beans `Supplier`/`Function`/`Consumer` bound by configuration.

**The live scenario (functional requirement)**
*FR: "A team building enrichment pipelines wants to write business functions without Kafka boilerplate; another team needs fine control of offsets, transactions and retry topics for payments."*

**What the interviewer is really checking**
Trade-off between abstraction and control.

**How I answer it**
1. **Payments -> Spring Kafka:** explicit `@KafkaListener`, `DefaultErrorHandler`, idempotent producer, Kafka transactions, manual ack mode where needed.
2. **Enrichment pipelines -> Spring Cloud Stream:**

```java
@Bean Function<DocumentUploaded, DocumentEnriched> enrich() { return d -> enricher.apply(d); }
```

   with `spring.cloud.function.definition=enrich` and binding properties mapping `enrich-in-0`/`enrich-out-0` to topics. Testable as plain functions.
3. Cloud Stream still exposes Kafka-specific settings via the Kafka binder (DLQ, partitioning).
4. Pick one per service, standardise per platform with shared starters.

**Trade-offs and what can go wrong**
- Abstraction leaks: advanced Kafka features need binder-specific config anyway.
- Debugging bindings by convention (`-in-0`) confuses newcomers.

**How I'd monitor it**
Same Kafka metrics either way (Micrometer binder metrics, consumer lag).

**Follow-ups to expect**
- *Kafka Streams?* -> For stateful stream processing (joins, windows, aggregations) inside the app.
- *Is the binder portable?* -> Mostly, between brokers with similar semantics.
- *How to test?* -> Test binder or Testcontainers Kafka; functions unit-tested directly.

**60-second answer**
"Spring Kafka gives full control: listeners, error handlers, transactions, retry topics. I use it where details matter, like payments. Spring Cloud Stream lets you write plain Function beans and bind them to topics by configuration, which suits enrichment pipelines and makes them trivially unit-testable, with Kafka specifics still available through the binder. One choice per service, standardised in a shared starter, and the metrics are the same either way."

### Q13 [senior] How do you test an event-driven system?
tags: testing, testcontainers, kafka, contract-testing, asyncapi, awaitility, profile-java-genai

**Start here: the concepts**
- **Unit tests:** handlers as plain methods.
- **Integration tests:** real Kafka via Testcontainers (or `@EmbeddedKafka`), asserting asynchronously with Awaitility.
- **Contract tests:** producer and consumer agree on the event schema (schema registry compatibility, Pact message contracts, Spring Cloud Contract).

**The live scenario (functional requirement)**
*FR: "Prove that a confirmed booking results in exactly one points award, survives a duplicate event, and that schema changes by the booking team never break the points consumer."*

**What the interviewer is really checking**
Testing async behaviour, idempotency and contracts, not just happy paths.

**How I answer it**
1. **Unit:** `PointsHandler.handle(event)` with an in-memory repository: correct points, duplicate ignored.
2. **Integration:** `@SpringBootTest` + Testcontainers Kafka and Postgres; publish `BookingConfirmed` twice with the same event id; `await().atMost(10, SECONDS).untilAsserted(...)` exactly one ledger row.
3. **Failure paths:** publish a malformed record -> it lands on the DLT; simulate DB down -> retries then success.
4. **Contracts:** schemas checked for compatibility in CI against the registry; consumer-driven message contracts (Pact) for semantics.
5. **End-to-end:** a small number of journey tests in a staging environment with synthetic bookings, cleaned up afterwards.

**Trade-offs and what can go wrong**
- `Thread.sleep` in tests -> flaky and slow; use Awaitility.
- Shared topics between tests leak messages; unique topic names or consumer groups per test.
- Embedded Kafka differs from real clusters in subtle ways; Testcontainers is closer.

**How I'd monitor it**
Flaky-test rate, test duration, contract-break incidents in production (should be zero).

**Follow-ups to expect**
- *Testing ordering?* -> Same key, sequence of events, assert final state.
- *Testing rebalances?* -> Start a second consumer mid-test; assert no loss/duplication.
- *Synthetic monitoring in prod?* -> Canary events through the pipeline measuring end-to-end latency.

**60-second answer**
"Handlers are unit-tested as plain methods, including duplicates. Integration tests run real Kafka and Postgres in Testcontainers: I publish the same BookingConfirmed twice and use Awaitility to assert exactly one points row, plus failure paths like a malformed record landing on the DLT. Schema compatibility is checked against the registry in CI and Pact covers semantics, so the booking team can't break us. A few synthetic journeys run in staging, and I never use sleeps."

### Q14 [senior] Trace and monitor an asynchronous flow end to end.
tags: observability, tracing, kafka-headers, correlation, end-to-end-latency, monitoring, profile-java-genai

**Start here: the concepts**
- **Trace context in headers:** OpenTelemetry injects `traceparent` into Kafka record headers; consumers continue the trace (as a link or child span).
- **End-to-end latency:** time from event creation to final effect, beyond broker lag.

**The live scenario (functional requirement)**
*FR: "Ops must know, per stage, where a document spends time from upload to being searchable by the AI assistant (target: 2 minutes), and be alerted when the pipeline slows."*

**What the interviewer is really checking**
Making async pipelines observable at stage and request level.

**How I answer it**
1. **Tracing:** OpenTelemetry instrumentation for Kafka producer/consumer (Spring Kafka with observation enabled, or the Java agent); one trace spans upload -> parse -> chunk -> embed -> index.
2. **Stage timestamps:** each event carries `createdAt`; each stage records `stage_latency = now - previous_stage_time` as a histogram.
3. **End-to-end metric:** `document_time_to_searchable_seconds` histogram; SLO 95% < 2 min.
4. **Per-stage health:** consumer lag in seconds, error and DLT rates, throughput.
5. **Business correlation id** (`documentId`) in logs and span attributes so support can follow one document.
6. **Synthetic canary:** upload a test document every 5 minutes and measure time until it is retrievable.

**Trade-offs and what can go wrong**
- Batch consumers process many traces at once; use span links rather than one parent.
- Clock skew across hosts distorts small latencies; fine at minute-level SLOs.
- Too many custom metrics per document id -> cardinality explosion; ids go into traces and logs only.

**How I'd monitor it**
The SLO dashboard: time-to-searchable p95, lag per stage, DLT rate, canary result.

**Follow-ups to expect**
- *Why is lag not enough?* -> Lag shows backlog, not processing time inside stages.
- *Alert on what?* -> SLO burn rate and canary failures, not on every error.
- *Sampling for pipelines?* -> Keep traces for slow and failed documents.

**60-second answer**
"I make the pipeline observable at two levels. Per document: OpenTelemetry propagates trace context through Kafka headers, so one trace shows upload, parse, chunk, embed and index, and the document id is on every span and log line. Per stage: each event carries timestamps, so I record per-stage latency and an end-to-end time-to-searchable histogram with a 2-minute SLO, alongside lag in seconds and DLT rates. A synthetic canary document every five minutes proves the whole path works."

### Q15 [architect] Design an event-driven ingestion pipeline that feeds a RAG system.
tags: rag, ingestion-pipeline, kafka, embeddings, vector-store, event-driven, profile-java-genai

**Start here: the concepts**
- **RAG ingestion:** load documents -> extract text -> chunk -> embed -> store vectors with metadata.
- **Why event-driven:** each stage scales and fails independently; documents keep flowing; re-processing is a replay.

**The live scenario (functional requirement)**
*FR: "Policy documents, FAQs and support tickets from 5 sources must become searchable by the AI assistant within 5 minutes of change; deletions must disappear just as fast; 200,000 documents, 5,000 changes a day, with spikes."*

**What the interviewer is really checking**
A complete, resilient pipeline design with idempotency, deletes and re-embedding.

**How I answer it**
1. **Sources -> events:** CDC (Debezium) for DB-backed sources, webhooks/polling connectors for SaaS sources, object-storage events for files. All publish `DocumentChanged {docId, source, version, op, uri, acl}` keyed by `docId`.
2. **Parse stage:** downloads, extracts text (Apache Tika/PDF parsers), normalises, emits `DocumentParsed` (large text stored in object storage, event carries the reference: claim-check pattern).
3. **Chunk + embed stage:** splits into chunks, calls the embedding model in batches with rate limiting, emits/writes chunks with metadata (docId, version, section, ACL groups, source, updatedAt).
4. **Index stage:** upserts into the vector store (pgvector/OpenSearch/Milvus) by `docId+chunkNo`; deletes old chunks of previous versions. `op=DELETE` removes all chunks of the doc.
5. **Idempotency & ordering:** keyed by docId so versions process in order; ignore events with an older version than stored.
6. **Failures:** retry topics + DLT per stage; replay on code fixes.
7. **Model change:** re-embedding into a new index version via a replay group, then alias switch.
8. **Scaling:** KEDA on lag per stage; the embedding stage capped by provider quota.

**Trade-offs and what can go wrong**
- Putting whole documents in Kafka messages hits size limits; use claim-check.
- Forgetting deletes means the assistant quotes withdrawn policies: a compliance risk.
- ACLs copied at ingest time go stale; refresh on permission-change events.

**How I'd monitor it**
Time-to-searchable SLO, lag per stage, DLT counts, embedding cost per day, index vs source document count reconciliation.

**Follow-ups to expect**
- *Why not a nightly batch?* -> Fails the 5-minute freshness and delete requirements, and spikes are harder.
- *Where do chunk sizes come from?* -> Evaluated on retrieval quality (see the GenAI pack).
- *How do you handle a source outage?* -> Connectors resume from their offset/cursor; CDC resumes from the log position.

**60-second answer**
"Every source emits a DocumentChanged event keyed by document id: CDC for databases, connectors for SaaS, storage events for files. Separate stages parse, chunk and embed, and index, each its own consumer group, so they scale on lag and fail independently, with big text passed by reference. The index stage upserts chunks by doc and chunk number and removes old versions; delete events remove everything, so withdrawn policies vanish within minutes. Versions are ordered per key, failures go through retry topics and DLTs, and a model change is a replay into a new index version."
