---
id: company-jpmc-microservices-kafka-design
title: JPMorgan Chase pack (4/5): Kafka, microservices and system design, senior to architect
stack: java
skill: microservices
---
Part of the **JPMorgan Chase Java mid/senior pack** (hub: `../company-chase-travel/README.md`). Candidate reports describe
senior rounds as "**how would you handle this in production?**" interviews covering Kafka, microservices, observability and
scaling, plus design prompts such as a **rate limiter** and a **document upload and validation service**. JPMC lead-engineer
postings ask for "distributed micro-services using Java and Spring Boot" and "event-driven systems utilizing Apache Kafka".

Each answer has a **120-second point-by-point version** (*How I answer it*) and a **60-second answer**.

Levels: **mid** (3-6 yrs) · **senior** (6-10) · **architect** (10+, "expert").

### Q1 [senior] Explain Kafka's architecture and how ordering works.
tags: kafka, partitions, consumer-groups, ordering, replication, isr, offsets, jpmc

**Start here: the concepts**
- A **topic** is a named log of messages, split into **partitions**. Each partition is an ordered, append-only file.
- Each message in a partition has an **offset** (its position). Consumers remember the offset they have processed.
- A **consumer group** shares the partitions of a topic: each partition is read by exactly one consumer in the group.
- **Replication:** each partition has a leader and followers on other brokers; the **ISR** (in-sync replicas) are the followers that are up to date.

**The live scenario (functional requirement)**
*FR: "Account events (opened, debited, credited, closed) must be processed in order per account, at 20,000 events per second."*

**What the interviewer is really checking**
That you know ordering is **per partition only**, and how keys, partitions and consumer groups decide both order and scale.

**How I answer it** (120-second answer, point by point)
1. **Ordering is guaranteed only inside one partition.** There is no order across partitions.
2. **The message key picks the partition** (a hash of the key). With `key = accountId`, all events for one account go to one partition, so they stay in order. Different accounts are spread out for parallelism.
3. **Scaling:** the number of partitions is the maximum parallelism of a consumer group. 12 partitions means at most 12 busy consumers; a 13th sits idle.
4. **Durability:** `replication.factor=3` with `min.insync.replicas=2`, and the producer uses `acks=all`. A write is confirmed only when at least 2 replicas have it, so one broker can die without data loss.
5. **Consumers commit offsets** to the internal `__consumer_offsets` topic. After a restart they continue from the last committed offset.
6. **Rebalancing:** when consumers join or leave, partitions are reassigned. The new protocol (KIP-848, `group.protocol=consumer`, generally available in Kafka 4.0) does this incrementally, without stopping the whole group.
7. **Retention:** messages stay for a configured time or size regardless of consumption, so you can replay. Compacted topics keep the latest value per key.
8. **Metadata:** Kafka 4.0 removed ZooKeeper; clusters use **KRaft**.

**Trade-offs and what can go wrong**
- Changing the partition count later changes the key-to-partition mapping, which breaks ordering for in-flight keys. Plan partitions up front.
- One very busy key (a "hot" account) overloads one partition; ordering per key prevents spreading it.
- Retries with `max.in.flight.requests > 1` used to reorder messages; the idempotent producer (default since Kafka 3.0) prevents that.

**Follow-ups to expect**
- *How many partitions?* -> Target throughput / per-consumer throughput, with headroom; for example 20,000/s at 2,000/s per consumer = 10, so 12 or 24.
- *Can two groups read the same topic?* -> Yes, each group has its own offsets: that is publish-subscribe.

**60-second answer**
"A topic is split into partitions, each an ordered append-only log, and order is guaranteed only within a partition. The key decides the partition, so keying by account id keeps each account's events in order while spreading accounts for parallelism. In a consumer group each partition goes to one consumer, so the partition count is the maximum parallelism. For durability I use replication factor 3, min in-sync replicas 2 and acks=all. Consumers commit offsets, so they resume after restarts, and retention lets us replay. Kafka 4 runs on KRaft without ZooKeeper, and the new consumer rebalance protocol avoids stop-the-world rebalances."

### Q2 [senior] How do you get no message loss and no duplicate processing with Kafka?
tags: kafka, delivery-semantics, at-least-once, exactly-once, idempotent-producer, idempotent-consumer, outbox, jpmc

**Start here: the concepts**
- **At-most-once:** may lose messages, never duplicates. **At-least-once:** never loses, may duplicate. **Exactly-once:** neither, but only within Kafka (read-process-write with transactions).
- In practice: **at-least-once delivery plus an idempotent consumer** gives "effectively once".

**The live scenario (functional requirement)**
*FR: "Every card transaction event must reach the ledger exactly once in effect: no lost transactions, no double postings."*

**What the interviewer is really checking**
Settings on both sides, the commit order, and how you deal with duplicates that *will* happen.

**How I answer it** (120-second answer, point by point)
1. **Producer, no loss:** `acks=all`, idempotence on (`enable.idempotence=true`, the default since Kafka 3.0), retries on, and `delivery.timeout.ms` set sensibly. Handle the send callback: on final failure, alert or store it, don't ignore it.
2. **Topic:** `replication.factor=3`, `min.insync.replicas=2`, `unclean.leader.election.enable=false`.
3. **Consumer, no loss:** turn off auto-commit and **commit after processing**, never before. In Spring Kafka the default ack mode commits after the listener returns.
4. **Duplicates still happen** (a crash after processing but before commit, or a rebalance). So the consumer must be **idempotent**:
   - Store the event id in a processed-events table with a unique constraint, in the same database transaction as the business change, or
   - Use a natural unique key (`transaction_id`) with an upsert.
5. **Publishing an event after a DB change:** the **transactional outbox**. Write the business row and an outbox row in one transaction; a relay (Debezium CDC or a poller) publishes it. This avoids "saved but never published" and "published but rolled back".
6. **Kafka-to-Kafka pipelines:** Kafka transactions (`transactional.id`, `isolation.level=read_committed`) give real exactly-once inside Kafka; Kafka Streams turns it on with `processing.guarantee=exactly_once_v2`.

**Trade-offs and what can go wrong**
- Exactly-once does not cover side effects outside Kafka (a DB write, an email). Those still need idempotency.
- `acks=all` adds a little latency; that is the right trade-off for money.

**Follow-ups to expect**
- *What if the consumer can't process a message?* -> Retry topics and a dead-letter topic (Q4).
- *Why not a distributed transaction between Kafka and the DB?* -> Kafka doesn't take part in XA; the outbox is the standard answer.

**60-second answer**
"On the producer I use acks=all with idempotence on, which is the default in modern clients, and I handle send failures. Topics have replication factor 3 and min in-sync replicas 2. Consumers commit only after processing, so nothing is lost, which means duplicates can happen after a crash or rebalance. So consumers are idempotent: the event id goes into a table with a unique constraint in the same transaction as the business change. To publish events after a DB change I use the transactional outbox. Kafka transactions give true exactly-once only for Kafka-to-Kafka flows, so side effects still need idempotency."

### Q3 [senior] Consumer lag is growing in production. What do you do?
tags: kafka, consumer-lag, scaling, max-poll-records, rebalance, monitoring, burrow, jpmc

**Start here: the concepts**
- **Consumer lag** = the latest offset in a partition minus the consumer's committed offset: how far behind the consumer is.
- Lag grows when messages arrive faster than they are processed, or when consumers are stuck or rebalancing.

**The live scenario (functional requirement)**
*FR: "Fraud scoring must process card events within 5 seconds."* At 9 a.m. lag grew from 0 to 2 million messages and fraud decisions were minutes late.

**What the interviewer is really checking**
A calm, structured diagnosis: is it volume, slow processing, a stuck partition or rebalancing? And the right fix for each.

**How I answer it** (120-second answer, point by point)
1. **Look at the shape of the lag:**
   - Lag on **all partitions** -> not enough processing capacity, or a slow dependency.
   - Lag on **one partition** -> a hot key or a poison message blocking it.
   - Lag going up and down with **rebalance logs** -> consumers are being kicked out.
2. **Check processing time per record** (a Micrometer timer) and the downstream dependencies (the DB, a scoring API). Usually the consumer is waiting on something.
3. **Fixes by cause:**
   - **Slow downstream:** batch writes (`saveAll`, JDBC batching), cache reference data, add timeouts.
   - **Not enough consumers:** add instances, up to the partition count; autoscale on lag with **KEDA**.
   - **Partition limit reached:** add partitions (plan for the key remapping), or process in parallel inside a partition with a key-ordered pool (Confluent Parallel Consumer).
   - **Rebalance storms:** processing takes longer than `max.poll.interval.ms`, so lower `max.poll.records` or make processing faster; use static membership (`group.instance.id`) or the KIP-848 protocol.
   - **Poison message:** a retry topic and DLT, so one bad record doesn't block the partition.
4. **Producer side:** a sudden traffic spike or a replay? Confirm that with producer metrics.
5. **Monitor ahead:** lag per partition, **time lag** (seconds behind, more meaningful than message counts), records per second, and rebalance counts. Alert on time lag against the SLA.

**Trade-offs and what can go wrong**
- Adding consumers beyond the partition count does nothing.
- Raising `max.poll.records` without faster processing causes more rebalances.

**Follow-ups to expect**
- *What tools?* -> `kafka-consumer-groups.sh --describe`, Burrow, Prometheus exporters, Confluent Control Center, Datadog.
- *How do you catch up quickly after an outage?* -> Temporarily scale consumers to the partition count, and pause non-critical consumers sharing the same resources.

**60-second answer**
"First I look at the shape: lag on every partition means not enough capacity or a slow dependency; lag on one partition means a hot key or a poison message; lag going up and down with rebalance logs means consumers are being kicked out. Then I check processing time per record, usually it's a slow DB or API. Fixes match the cause: batch writes and caching, more consumers up to the partition count with KEDA scaling on lag, fewer records per poll if processing exceeds max.poll.interval, and a retry topic with a DLT for poison messages. I alert on time lag in seconds against the SLA."

### Q4 [senior] How do you handle a poison message and retries in a Kafka consumer?
tags: kafka, dead-letter-topic, retry-topic, defaulterrorhandler, poison-pill, errorhandlingdeserializer, jpmc

**Start here: the concepts**
- A **poison message** fails every time (bad format, invalid data). If you retry it forever, the whole partition stops.
- A **dead-letter topic (DLT)** holds messages that failed after all retries, for investigation and replay.

**The live scenario (functional requirement)**
*FR: "Payment events must not block when one event is malformed, and every failed event must be recoverable."* One message with a bad date format made the consumer retry forever, and lag grew on that partition.

**What the interviewer is really checking**
Separating transient from permanent errors, non-blocking retries, and an operational replay process.

**How I answer it** (120-second answer, point by point)
1. **Deserialisation errors:** wrap the deserialiser in `ErrorHandlingDeserializer`, so a bad payload becomes an error the handler can route, instead of a crash loop.
2. **Classify errors:**
   - **Permanent** (validation failure, bad data) -> no retry, straight to the DLT.
   - **Transient** (DB timeout, 503) -> retry with backoff.
3. **Blocking retries** (`DefaultErrorHandler` with `ExponentialBackOff`, a few attempts) are fine for short transient failures. They keep order, but block the partition meanwhile.
4. **Non-blocking retries** (`@RetryableTopic`): failed messages go to `orders-retry-1`, `orders-retry-2` with delays, then `orders-dlt`. The main partition keeps flowing. The trade-off: **order is lost** for retried messages.
5. **The DLT message keeps context:** the original topic, partition, offset, exception and stack trace go in headers (Spring adds them).
6. **Operations:** an alert on DLT volume, a dashboard, and a **replay tool** that sends fixed messages back to the main topic after the bug is fixed.
7. **Ordering-sensitive flows:** if order per key matters, either use blocking retries, or park all later events for that key once one fails.

**Trade-offs and what can go wrong**
- A DLT that nobody watches is just a data-loss bin.
- Non-blocking retries can apply events out of order (a "debit" retried after a later "close").

**Follow-ups to expect**
- *How do you make replay safe?* -> Idempotent consumers, so replaying a message that partly succeeded doesn't double-apply.

**60-second answer**
"First, ErrorHandlingDeserializer so a malformed payload doesn't crash-loop the consumer. Then I split errors: permanent ones like validation failures go straight to a dead-letter topic; transient ones like DB timeouts get retries with backoff. Short blocking retries keep order; for longer ones I use non-blocking retry topics so the partition keeps flowing, accepting that order is lost for retried messages. DLT messages carry the original topic, offset and exception in headers. And DLTs have alerts, an owner and a replay tool, with idempotent consumers so replays are safe."

### Q5 [senior] How do you keep data consistent across microservices without distributed transactions?
tags: saga, outbox, choreography, orchestration, compensation, eventual-consistency, jpmc

**Start here: the concepts**
- Each microservice owns its own database, so one ACID transaction can't cover several services.
- A **saga** is a sequence of local transactions; if a step fails, earlier steps are undone with **compensating actions**.
- **Choreography:** services react to each other's events. **Orchestration:** a central coordinator tells each service what to do.

**The live scenario (functional requirement)**
*FR: "A travel booking: redeem points, charge the card for the rest, confirm with the hotel. If the hotel fails, refund the card and restore the points."*

**What the interviewer is really checking**
The saga pattern done properly: outbox, idempotency, compensations, timeouts and visibility of stuck flows.

**How I answer it** (120-second answer, point by point)
1. **Why not two-phase commit:** it locks resources across services, needs every participant to support it (Kafka and most HTTP APIs don't), and a coordinator failure blocks everyone.
2. **Orchestrated saga** for a business flow like this one: a `BookingSaga` (a state machine stored in the database) runs the steps: reserve points -> charge card -> confirm hotel.
3. **Compensations in reverse:** hotel fails -> refund the card -> release the points. A compensation is a new business action ("refund"), not a database rollback.
4. **Every step and compensation is idempotent** and retried, because messages can be duplicated.
5. **Reliable messaging:** each service uses the **transactional outbox** to publish its result in the same transaction as its own change.
6. **Unknown outcomes:** if the hotel call times out, the result is unknown. **Query the supplier's status** before compensating, otherwise you may refund a booking that actually succeeded.
7. **Timeouts and stuck sagas:** each step has a deadline, and a dashboard shows sagas stuck in each state, with manual repair for the rare cases.
8. **Choreography** works for simple flows with 2-3 steps; beyond that, the flow becomes hard to follow, so I prefer orchestration (or a workflow engine such as Temporal or Camunda).

**Trade-offs and what can go wrong**
- Eventual consistency is visible to users: show "pending" states honestly.
- Missing compensation for one step leaves money in limbo; test every failure path.

**Follow-ups to expect**
- *What is the "pivot" step?* -> The step after which you can't compensate (for example a non-refundable supplier booking); order steps so risky, reversible ones come first.
- *What is CQRS?* -> Separate write and read models; useful alongside sagas for fast read views.

**60-second answer**
"Each service owns its data, so I don't use distributed transactions. For a booking I use an orchestrated saga: a persisted state machine that reserves points, charges the card, then confirms the hotel. If the hotel fails, it runs compensations in reverse: refund, then release points. Every step is idempotent and publishes through a transactional outbox, so nothing is lost or half-sent. Timeouts are tricky: an unknown outcome means I check the supplier's status before compensating. Stuck sagas show up on a dashboard. For flows with two or three steps, choreography with events is fine; beyond that I prefer orchestration."

### Q6 [architect] Design a rate limiter for a public API.
tags: system-design, rate-limiter, token-bucket, sliding-window, redis, api-gateway, jpmc

**Start here: the concepts**
- A **rate limiter** caps how many requests a client can make in a time window, protecting the system and enforcing fair use.
- **Token bucket:** a bucket refills at a steady rate; each request takes a token; when it's empty, the request is rejected. It allows short bursts.
- **Sliding window:** counts requests in the last N seconds, with smoother limits than fixed windows.

**The live scenario (functional requirement)**
*FR: "Partners may call the quotes API 100 times per second each, with short bursts allowed; the limit must hold across 20 API pods; responses must say when to retry."* Candidates report this exact design prompt in JPMC system-design rounds.

**What the interviewer is really checking**
Clarifying requirements, choosing an algorithm, making it work across many instances, and failure behaviour.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** limit per what (API key, user, IP)? Hard or soft limit? How accurate must it be? What latency budget (about 1 ms)?
2. **Algorithm:** **token bucket** (capacity = burst size, refill = 100/s). It is simple, allows bursts, and needs only two values per client (tokens, last refill time).
3. **Where:** at the **API gateway** (Spring Cloud Gateway, Kong, AWS API Gateway) so bad traffic is stopped before services. Services can add their own limits per downstream.
4. **Shared state across 20 pods:** **Redis** with an atomic **Lua script** that refills and takes a token in one step. Key: `rl:{partnerId}`, with a TTL so idle clients expire.
5. **Response:** `429 Too Many Requests` with `Retry-After` and `RateLimit-*` headers, so clients back off properly.
6. **Scale:** Redis Cluster sharded by key; a local in-memory pre-check can absorb extreme bursts.
7. **Failure mode:** if Redis is down, **fail open** for most APIs (allow traffic, with a local per-pod limit as a backstop) or **fail closed** for sensitive ones like login. Decide it per API.
8. **Observability:** metrics for rejections per partner, Redis latency, and top limited clients; per-partner limits stored in config.

**Trade-offs and what can go wrong**
- Fixed windows allow double bursts at window edges; sliding windows or token buckets avoid that.
- A Redis round trip per request adds latency; keep Redis close (same AZ) and pipelined.
- Local-only limits multiply by the pod count: 20 pods × 100/s = 2,000/s.

**Follow-ups to expect**
- *Token bucket vs leaky bucket?* -> Token bucket allows bursts; leaky bucket smooths output to a constant rate.
- *How do you limit by cost?* -> Each request takes a different number of tokens (a heavy report costs 10).

**60-second answer**
"I'd clarify the key (API key or user), the limits and burst size, and the latency budget. I'd use a token bucket: capacity is the burst, the refill rate is the limit, and it only needs two values per client. I enforce it at the API gateway so abuse stops early. Because there are 20 pods, the state lives in Redis, updated atomically by a Lua script, with a TTL. Rejected calls get 429 with Retry-After. If Redis is down, I fail open with a local per-pod limit for normal APIs, and fail closed for sensitive ones like login. Rejections per partner go on a dashboard."

### Q7 [architect] Design a document upload and validation service with a tracking link.
tags: system-design, file-upload, s3, presigned-url, async-processing, kafka, virus-scan, status-tracking, jpmc

**Start here: the concepts**
- **Pre-signed URL:** a time-limited URL that lets a client upload directly to object storage (S3) without the file passing through your servers.
- **Asynchronous processing:** accept the upload quickly, validate in the background, and let the client check the status.

**The live scenario (functional requirement)**
*FR: "Customers upload KYC documents (up to 50 MB). Each is virus-scanned, format-checked and data-extracted. The customer gets a tracking link that shows status: received, scanning, accepted, rejected."* A JPMC candidate reported a design question of exactly this shape.

**What the interviewer is really checking**
Not streaming large files through app servers, async pipelines, a status model, security and retention.

**How I answer it** (120-second answer, point by point)
1. **API:** `POST /documents` creates a record (status `PENDING_UPLOAD`) and returns a **pre-signed S3 PUT URL** plus a `documentId`. The tracking link is `GET /documents/{id}/status`.
2. **Upload:** the client uploads **directly to S3** (multipart for large files). App servers never hold the bytes, so they stay small and fast.
3. **Trigger:** an S3 event notification -> SQS or Kafka -> status `RECEIVED`.
4. **Pipeline workers:** virus scan -> file type check (by magic bytes, not the extension) -> size and page limits -> OCR/data extraction -> business validation. Each step updates the status and publishes an event.
5. **Quarantine:** files land in a quarantine bucket; only clean files move to the final bucket. Rejected files are kept briefly for audit, then deleted.
6. **Status tracking:** a status table (document id, state, reason, timestamps). The client polls the link, or gets a webhook or push notification when it finishes.
7. **Security:** pre-signed URLs expire in minutes and are limited to one key and content type; buckets are private with SSE-KMS encryption; the tracking link needs authentication or an unguessable token; PII stays out of logs.
8. **Reliability:** idempotent workers (the same S3 event can arrive twice), retries with a DLQ, and a reconciliation job for uploads that never arrived.
9. **Scale:** workers autoscale on queue depth; heavy OCR runs on separate workers.

**Trade-offs and what can go wrong**
- Uploading through the API servers ties up threads and memory and limits throughput.
- Trusting the client's content type lets disguised executables through.
- Retention rules (regulatory) must drive lifecycle policies, not ad-hoc deletes.

**Follow-ups to expect**
- *How do you handle a 2 GB file?* -> Multipart upload with parallel parts and resume; stream processing in workers, never loading the whole file into memory.
- *How do you show progress?* -> The status table plus events; for real-time, server-sent events or WebSockets.

**60-second answer**
"The client calls POST /documents and gets back a document id and a short-lived pre-signed S3 URL, then uploads directly to S3, so our servers never hold the file. An S3 event goes to a queue, and workers run the pipeline: virus scan, real file-type check, limits, OCR and business validation. Each step updates a status table and publishes an event. The tracking link reads that status, with polling or a webhook. Files sit in a quarantine bucket until clean, everything is KMS-encrypted and private, workers are idempotent with a DLQ, and they autoscale on queue depth."

### Q8 [senior] How do you make a microservice observable in production?
tags: observability, logging, metrics, tracing, opentelemetry, micrometer, slo, correlation-id, jpmc

**Start here: the concepts**
- **Logs:** what happened, in detail. **Metrics:** numbers over time (rate, errors, latency). **Traces:** the path of one request across services.
- An **SLO** is a target such as "99.9% of requests succeed within 300 ms over 30 days".

**The live scenario (functional requirement)**
*FR: "When a payment is slow, on-call must find which service and which dependency within 5 minutes."* Before, each team had different log formats and no trace ids, and incidents took hours.

**What the interviewer is really checking**
That you instrument by default, connect the three signals, and alert on user impact, not on noise.

**How I answer it** (120-second answer, point by point)
1. **Metrics with Micrometer**, exported to Prometheus, Datadog or another backend. **RED** per endpoint (Rate, Errors, Duration as p50/p95/p99 histograms), plus JVM, connection pool, thread pool, Kafka lag and circuit breaker states.
2. **Tracing with OpenTelemetry** (Boot 3 Micrometer Tracing; Boot 4 has an OpenTelemetry starter). The trace id flows through HTTP headers (W3C `traceparent`) and Kafka headers.
3. **Structured JSON logs** with the trace id and span id in every line (MDC), so you can jump from a trace to its logs. Spring Boot 3.4+ has built-in structured logging. Never log PII or card numbers.
4. **Business metrics:** payments per minute, failure rate by reason. These often catch problems before technical metrics do.
5. **Alerting on SLOs:** alert on **error-budget burn rate** (user impact), not on every CPU spike. Each alert links to a runbook.
6. **Dashboards:** one per service (golden signals) plus one per business flow across services.
7. **Health:** Actuator liveness and readiness probes. Readiness checks the critical dependencies; liveness doesn't (or a DB outage restarts every pod).

**Trade-offs and what can go wrong**
- High-cardinality metric tags (user id, order id) explode metrics storage; put those in logs and traces.
- Sampling traces at 100% is costly; use sampling, keeping all errors and slow traces.

**Follow-ups to expect**
- *Splunk queries?* -> Search by trace id, `stats count by status`, `timechart p99(latency)`; see the Splunk banks in this repo.
- *How do you find the slow dependency?* -> The trace waterfall shows which span takes the time.

**60-second answer**
"I instrument three signals by default. Micrometer metrics with RED per endpoint, p99 histograms, plus JVM, pool, Kafka lag and circuit breaker metrics. OpenTelemetry tracing, with trace ids carried through HTTP and Kafka headers. And structured JSON logs with the trace id in every line, so I can jump from a slow trace straight to its logs, without PII. I add business metrics like payments per minute. Alerts fire on SLO burn rate, meaning user impact, each with a runbook. Readiness checks critical dependencies; liveness doesn't, so a DB blip doesn't restart every pod."

### Q9 [architect] Traffic will grow 10x for a seasonal peak. How do you prepare the service?
tags: scaling, capacity-planning, load-testing, autoscaling, caching, database-scaling, backpressure, jpmc

**Start here: the concepts**
- **Horizontal scaling:** more instances. **Vertical scaling:** bigger instances.
- **The bottleneck** is the one resource that limits throughput; adding capacity anywhere else does nothing.
- **Little's Law:** concurrent requests = throughput × latency.

**The live scenario (functional requirement)**
*FR: "A rewards promotion is expected to bring 10x normal booking traffic for 48 hours."*

**What the interviewer is really checking**
A method: measure, find the bottleneck, scale each tier, protect the system, and rehearse.

**How I answer it** (120-second answer, point by point)
1. **Numbers first:** today's peak (for example 500 requests/s at a p99 of 200 ms) -> target 5,000 requests/s. By Little's Law that is about 1,000 requests in flight.
2. **Load test** at 10x in a production-like environment to find the **first bottleneck**. It is usually the database or a downstream service, not the Java pods.
3. **Stateless app tier:** horizontal autoscaling (HPA on CPU or requests per second, KEDA on queue lag), pre-scaled before the event because autoscaling reacts slowly to sudden spikes.
4. **Database:** this is usually the limit.
   - Read replicas for reads, connection pool sizing (the total across all pods must stay under the DB's limit; or use RDS Proxy or PgBouncer).
   - Fix slow queries and indexes; cache hot reads (Redis with TTLs).
5. **Asynchronous work:** move non-critical steps (emails, analytics) to Kafka queues, so the request path stays short.
6. **Protect the system:** rate limits per client, bulkheads, circuit breakers and **load shedding** (reject early with 503 rather than time out everything).
7. **Downstreams:** tell partners the expected volume; check their limits; cache their responses where allowed.
8. **Operations:** dashboards for the event, an on-call plan, a feature-flag kill switch for expensive features, and a rollback plan. Rehearse with a game day.

**Trade-offs and what can go wrong**
- Scaling pods without the DB just moves the queue into the connection pool.
- Caches create staleness; decide per data type what is acceptable (prices vs static content).

**Follow-ups to expect**
- *Utilisation target?* -> Keep critical resources around 60-70% at peak; above about 80%, queueing makes latency rise steeply.
- *What about cost?* -> Scale back down after the event; use scheduled scaling.

**60-second answer**
"I start with numbers: today's peak and latency, then the 10x target, and Little's Law for concurrency. Then a production-like load test at 10x to find the first bottleneck, usually the database or a downstream, not the Java pods. The app tier scales horizontally and I pre-scale before the event. For the database: query fixes, read replicas, a Redis cache for hot reads, and a pool budget across all pods. Non-critical work moves to Kafka. I protect the system with rate limits, bulkheads and load shedding, warn partners, and run a game day with a kill switch and rollback plan."

### Q10 [senior] How do you break a monolith into microservices, and when should you NOT?
tags: microservices, monolith, strangler-fig, bounded-context, ddd, modular-monolith, jpmc

**Start here: the concepts**
- A **microservice** is a small, independently deployable service that owns one business capability and its data.
- A **bounded context** (from Domain-Driven Design) is a part of the business with its own consistent model, for example "Payments" or "Rewards".
- The **strangler fig** pattern replaces a legacy system piece by piece behind a routing layer.

**The live scenario (functional requirement)**
*FR: "A 10-year-old booking monolith deploys once a month; teams block each other. The business wants weekly releases for the pricing team."* This matches the Chase Travel "Java rewrite" theme in this pack.

**What the interviewer is really checking**
Judgement: why to split, where to cut, how to migrate safely, and the honesty to say when not to.

**How I answer it** (120-second answer, point by point)
1. **Start from the problem:** release speed, team independence, scaling one hot part, or a technology limit. If none of these hurts, don't split.
2. **Find boundaries by business capability,** not by technical layer: pricing, booking, payments, notifications. The data each owns follows from that.
3. **Modular monolith first** when the boundaries are unclear: enforce module boundaries inside one deployable (Spring Modulith, ArchUnit). It is cheap to split later.
4. **Strangler fig:** put a gateway in front; move one capability (for example pricing) to a new service; route its traffic there; repeat.
5. **Data is the hard part:** the new service gets its own schema. Sync with CDC during migration; never let two services share a table long-term.
6. **Communication:** synchronous REST for queries that need an immediate answer; events (Kafka) for state changes, which reduces coupling.
7. **Platform needs before splitting widely:** CI/CD per service, observability with tracing, service discovery or Kubernetes, and contract tests.
8. **When NOT to:** a small team, an unclear domain, or no platform maturity. You get a "distributed monolith": all the network costs and none of the independence.

**Trade-offs and what can go wrong**
- Splitting too fine creates chatty services and latency chains.
- Shared libraries containing domain models couple services together again.

**Follow-ups to expect**
- *How do you verify the new service behaves like the old one?* -> Shadow traffic with response diffing, then a gradual canary cutover.
- *Conway's Law?* -> The system mirrors team structure; align service boundaries with team boundaries.

**60-second answer**
"I start from the pain: release speed, team independence or scaling one hot area. If none of those hurts, I don't split. I cut by business capability, like pricing, booking and payments, with each service owning its data. When the boundaries are unclear I begin with a modular monolith and enforce the boundaries with Spring Modulith or ArchUnit. Migration is a strangler fig: a gateway routes one capability at a time to the new service, with CDC keeping data in sync and shadow traffic to compare results. And I'm honest that with a small team or no CI/CD and observability, you just get a distributed monolith."
