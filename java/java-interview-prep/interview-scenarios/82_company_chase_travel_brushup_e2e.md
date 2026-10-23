---
id: company-chase-travel-brushup-e2e
title: Company pack, Chase Travel (3/3): Sujay's brush-up list end to end, REST + Aurora + Kafka + S3/ECS (8 questions)
stack: java
skill: architecture
---
Company-level pack for the **Chase project** (see `../company-chase-travel/README.md`). Sujay asked to brush up on four
points: **Spring Boot REST API, database connection from Spring Boot, Kafka consumer and producer, AWS S3 / ECS / Aurora
Postgres**. Each point has a 30-question file in `../company-chase-travel/brush-up/`; this bank joins them into the
questions a lead asks when they want to hear how they **fit together in one service**.

**Illustrative architecture** (no inside knowledge of Chase systems): a Spring Boot booking service on ECS Fargate behind
an ALB, Aurora PostgreSQL for bookings, Kafka on MSK for events, S3 for itinerary documents. In the room, describe your own
project in this shape.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] Walk me through the architecture of a Spring Boot service that uses REST, Aurora PostgreSQL, Kafka and S3 on ECS.
tags: architecture, spring-boot, aurora, kafka, s3, ecs, end-to-end, company-chase-travel

**Start here: the concepts**
- **REST layer:** controllers, DTOs, validation, error handling. **Data layer:** HikariCP pool, JPA/JdbcTemplate, Flyway.
- **Events:** KafkaTemplate producer, `@KafkaListener` consumers, outbox for reliability.
- **AWS runtime:** ECS service (tasks from a task definition), ALB, Aurora cluster (writer + reader endpoints), S3 bucket,
  IAM task role, Secrets Manager, CloudWatch.

**The live scenario (functional requirement)**
*FR: "Card members book a hotel with points or card. The booking must be saved, confirmed to the member, rewarded, and an
itinerary PDF must be downloadable, at 300 bookings per minute at peak, p95 under 800 ms for the booking API."*

**What the interviewer is really checking**
That you can explain the request and event flow across all four technologies and why each piece is there.

**How I answer it**
1. **Edge:** Route 53 -> ALB (TLS, WAF) -> ECS Fargate service, tasks spread across 3 AZs, health check on
   `/actuator/health/readiness`.
2. **REST:** `POST /bookings` with an Idempotency-Key -> controller validates the record DTO -> `BookingService`.
3. **Database:** in one short transaction the service inserts the booking (PENDING -> CONFIRMED after the supplier and
   payment calls), the idempotency record and an **outbox** row, through HikariCP to the Aurora **cluster (writer) endpoint**.
   Reads like "my bookings" go to the **reader endpoint**.
4. **Kafka:** an outbox relay publishes `BookingConfirmed` to MSK keyed by `bookingId` (`acks=all`, idempotent producer).
5. **Consumers:** notification service (email), rewards service (points ledger) and document service each consume in their
   own consumer group and write idempotently.
6. **S3:** the document service renders the itinerary PDF and stores it in a private, KMS-encrypted bucket
   (`itineraries/{customerId}/{bookingId}.pdf`); the API returns a short-lived **pre-signed URL** after an ownership check.
7. **Security:** task role with least-privilege access to that bucket and MSK topics; DB credentials from Secrets Manager or
   IAM auth; everything in private subnets.
8. **Observability:** traces across HTTP and Kafka headers, CloudWatch alarms on ALB 5xx, Aurora connections, consumer lag.

**Trade-offs and what can go wrong**
- Synchronous everything (email and PDF inside the request) would blow the 800 ms budget and couple failures; events fix it.
- Eventual consistency: the PDF appears a few seconds after confirmation; the UI shows "preparing your itinerary".
- More moving parts mean more to monitor; the outbox and idempotency are what keep it correct.

**How I'd monitor it**
Booking API p95/error rate, booking success rate, outbox oldest-row age, consumer lag per group, DLT counts, Aurora CPU and
connections, S3 4xx/5xx, ECS task restarts.

**Follow-ups to expect**
- *Why not write to Kafka directly from the request?* -> Dual write: the DB commit and the send can disagree; the outbox makes them atomic.
- *Why pre-signed URLs?* -> Files never stream through our service, and access is time-limited and authorised per object.
- *Why the reader endpoint?* -> Offload read traffic; mind replica lag for read-your-own-write.

**60-second answer**
"Requests come through an ALB to Spring Boot tasks on ECS Fargate across three AZs. POST /bookings is validated, and in
one short transaction through HikariCP to the Aurora writer endpoint we save the booking, the idempotency key and an
outbox row. A relay publishes BookingConfirmed to MSK keyed by booking id. Notification, rewards and document services
consume in their own groups and write idempotently, and the document service stores the itinerary PDF in a private,
encrypted S3 bucket that members download through short-lived pre-signed URLs. Roles, Secrets Manager and private
subnets secure it; traces, lag and connection alarms watch it."

### Q2 [senior] Trace one POST /bookings request through every layer, and say what happens when each layer fails.
tags: request-flow, failure-modes, idempotency, timeouts, resilience, end-to-end, company-chase-travel

**Start here: the concepts**
- A request crosses: ALB -> Tomcat thread -> filters/security -> controller -> service -> Hikari connection -> Aurora ->
  commit -> outbox relay -> Kafka.
- Each hop needs a **timeout** and a defined **failure response**.

**The live scenario (functional requirement)**
*FR: "A member taps 'Book' on a flaky mobile network. Whatever fails, they must never be charged twice or left with an
unknown booking state."*

**What the interviewer is really checking**
Failure thinking per layer, not just the happy path.

**How I answer it**
1. **ALB -> task:** a task dying mid-request returns 502; the app retries with the same **Idempotency-Key**, and the server
   returns the stored result if the first attempt completed.
2. **Validation/security:** bad body gives 400 with field errors; bad token gives 401; someone else's booking gives 403/404.
3. **Supplier/payment calls:** RestClient with timeouts and a circuit breaker; supplier timeout means booking stays
   PENDING with a status check later, never a blind retry of a non-idempotent call; the response is 202 with a status URL.
4. **Hikari:** pool exhausted fails fast after `connectionTimeout` (e.g. 3 s) with 503 and Retry-After, instead of hanging.
5. **Aurora:** unique-key violation on the idempotency key means "already processed", so return the stored response;
   failover means transient errors for up to about a minute; idempotent operations retried with backoff.
6. **After commit:** the outbox row guarantees the event is eventually published even if Kafka is down; the relay retries.
7. **Kafka consumers:** at-least-once delivery, idempotent handlers, DLT for poison messages.

**Trade-offs and what can go wrong**
- Retries without idempotency create duplicates; idempotency without timeouts creates hung threads. You need both.
- Returning 500 for transient states confuses clients; 202/503 with Retry-After communicates intent.

**How I'd monitor it**
Error rate by status code and endpoint, PENDING bookings older than N minutes, Hikari pending/timeout counts, breaker states,
outbox age.

**Follow-ups to expect**
- *Where is the idempotency key stored?* -> In Aurora, unique constraint, same transaction as the booking.
- *What if the client never retries?* -> A reconciliation job resolves PENDING bookings and notifies the member.
- *What timeout order?* -> Client > ALB idle timeout > server request budget > downstream timeouts.

**60-second answer**
"At every hop I define a timeout and a failure answer. A dropped connection at the ALB is safe because the client retries
with the same Idempotency-Key and gets the stored result. Validation and auth fail early with 400, 401 or 403. Supplier and
payment calls have timeouts and breakers, and an unknown outcome leaves the booking PENDING with a 202 and a status URL
rather than a blind retry. Hikari fails fast with a 503 instead of hanging. A duplicate key in Aurora means already
processed, and the outbox guarantees the event even if Kafka is down. Consumers are idempotent with a DLT."

### Q3 [senior] How does the service on ECS get secure access to Aurora, MSK and S3 without any secrets in code?
tags: iam, task-role, execution-role, secrets-manager, msk-iam, iam-database-auth, company-chase-travel

**Start here: the concepts**
- **Execution role** (ECS uses it to pull images, write logs, inject secrets) vs **task role** (the app's identity for AWS
  APIs).
- **Secrets Manager** secrets injected into the task definition; **IAM database authentication** (15-minute tokens);
  **MSK IAM auth** (`SASL_SSL` + `AWS_MSK_IAM`).

**The live scenario (functional requirement)**
*FR: "Security review requires no long-lived credentials in code, images or Git, least privilege per service, and
rotation of database secrets every 90 days without downtime."*

**What the interviewer is really checking**
Practical IAM and secret handling on AWS for a Spring Boot app.

**How I answer it**
1. **Execution role:** `ecr:GetAuthorizationToken`/pull, CloudWatch Logs write, `secretsmanager:GetSecretValue` for the
   specific secret ARNs injected into the container.
2. **Task role:** `s3:GetObject/PutObject` on `arn:...:itineraries-bucket/itineraries/*` only, MSK IAM permissions for the
   topics this service produces/consumes, `rds-db:connect` if using IAM DB auth. The AWS SDK picks up these credentials
   automatically.
3. **Aurora:** either the DB password from Secrets Manager (with rotation; the app must reconnect on new credentials, so
   use a rolling restart or the AWS JDBC wrapper's Secrets Manager plugin) or IAM database auth tokens generated per new
   connection.
4. **MSK:** `security.protocol=SASL_SSL`, `sasl.mechanism=AWS_MSK_IAM`, the `aws-msk-iam-auth` library; topic-level
   permissions in IAM policies.
5. **Network:** private subnets, security groups (Aurora 5432 only from the service SG), VPC endpoints for S3 (gateway),
   Secrets Manager, ECR and CloudWatch (interface).
6. **Encryption:** TLS to Aurora (`sslmode=verify-full`), TLS to MSK, SSE-KMS on S3.

**Trade-offs and what can go wrong**
- Mixing up execution and task roles: either the task can't start (secrets) or the app can't call S3.
- Rotation without reconnect logic causes authentication failures after rotation.
- Wildcard policies (`s3:*` on `*`) fail audits.

**How I'd monitor it**
CloudTrail for access-denied events, secret age, IAM Access Analyzer findings, failed DB authentications.

**Follow-ups to expect**
- *Why IAM DB auth?* -> No password to rotate or leak; tokens expire in 15 minutes.
- *How does Spring read secrets?* -> Env vars from the task definition, or Spring Cloud AWS `spring.config.import=aws-secretsmanager:...`.
- *Cross-account S3?* -> Bucket policy plus role trust; prefer same-account.

**60-second answer**
"Two roles: the execution role lets ECS pull the image, write logs and inject specific secrets; the task role is the app's
identity, scoped to the itinerary prefix in S3, its own MSK topics, and rds-db:connect if we use IAM database auth. The
database password comes from Secrets Manager with rotation and reconnect handling, or we skip passwords with 15-minute IAM
tokens. MSK uses IAM over SASL_SSL. Everything runs in private subnets with tight security groups and VPC endpoints, with
TLS everywhere and KMS on S3. Nothing secret lives in code, images or Git."

### Q4 [senior] BookingConfirmed reaches the document service: generate the itinerary PDF, store it in S3, and record it in Aurora, idempotently.
tags: kafka-consumer, s3, idempotency, aurora, document-generation, outbox, company-chase-travel

**Start here: the concepts**
- **At-least-once** delivery means the same event can arrive twice.
- **Deterministic S3 key** makes the upload naturally idempotent (overwrite with the same content).
- **Processed-event table** or upsert for the DB side.

**The live scenario (functional requirement)**
*FR: "Every confirmed booking gets exactly one itinerary PDF record that the member can download within 30 seconds; a
rebalance or crash must not create duplicates or lose any itinerary."*

**What the interviewer is really checking**
Combining Kafka consumer semantics, S3 writes and DB writes without distributed transactions.

**How I answer it**
1. `@KafkaListener(topics = "booking.confirmed", groupId = "document-service")`, auto-commit off, record ack mode.
2. Check `processed_event` (or the `itinerary` row by `booking_id`): already DONE means acknowledge and return.
3. Render the PDF (template + booking data from the event, a fat event so no callback storm).
4. **Upload to S3** with a deterministic key `itineraries/{customerId}/{bookingId}/v{bookingVersion}.pdf`, SSE-KMS, and
   a checksum. Repeating the upload is harmless.
5. **One DB transaction:** upsert `itinerary(booking_id PK, s3_key, checksum, status=DONE)` +
   insert `processed_event(event_id)` with `ON CONFLICT DO NOTHING`.
6. **Then** commit the Kafka offset. A crash before the offset commit means redelivery, which steps 2/4/5 make a no-op.
7. Failures: S3 throttling or timeouts retried with backoff; template errors are non-retryable and go to the DLT with an
   alert; the member UI shows "itinerary delayed" and support can trigger regeneration.

**Trade-offs and what can go wrong**
- Random S3 keys (UUID per attempt) create orphan files on retries; deterministic keys avoid it, and a lifecycle rule
  cleans any leftovers.
- Generating the PDF inside the booking request would slow the API and couple failures.
- Large batches risk exceeding `max.poll.interval.ms`; keep per-record work bounded.

**How I'd monitor it**
Consumer lag (time to itinerary), DLT count, S3 put errors/latency, itineraries missing for confirmed bookings
(reconciliation query), PDF generation time.

**Follow-ups to expect**
- *Why not S3 event -> DB instead?* -> Possible, but then you coordinate two triggers; writing the DB record after a
  successful put is simpler.
- *How does download work?* -> `GET /bookings/{id}/itinerary` checks ownership and returns a 5-minute pre-signed URL.
- *Booking modified later?* -> New version event creates a new versioned key; the row points to the latest.

**60-second answer**
"The document service consumes BookingConfirmed with auto-commit off. It first checks whether the event was already
processed, renders the PDF and uploads it to S3 under a deterministic key built from customer, booking and version, so a
repeat upload just overwrites the same object. Then in one Aurora transaction it upserts the itinerary row and records the
event id, and only after that commits the Kafka offset. A crash anywhere just causes a harmless redelivery. Template errors
go to the DLT with an alert, and a reconciliation query catches any confirmed booking without an itinerary."

### Q5 [senior] ECS autoscaling, the Aurora connection limit and Kafka partitions: how do you keep them consistent?
tags: scaling, ecs-autoscaling, hikari, max-connections, kafka-partitions, capacity, company-chase-travel

**Start here: the concepts**
- **Connections used = running tasks × Hikari pool size** (+ other clients), which must stay below Aurora `max_connections`.
- **Kafka parallelism = partitions**: more consumer tasks than partitions sit idle.
- ECS Service Auto Scaling: target tracking on CPU, ALB requests per target, or custom metrics (consumer lag).

**The live scenario (functional requirement)**
*FR: "A card-member promotion triples traffic for two hours; the API and consumers must scale without the database
refusing connections or consumers sitting idle."*

**What the interviewer is really checking**
Seeing the system as connected capacity limits, not independent knobs.

**How I answer it**
1. **Connection budget:** say Aurora allows ~1,000 connections; reserve 20% for admin and other services leaving 800. API
   tasks max 30 × pool 15 = 450; consumer tasks max 24 × pool 10 = 240. Total 690 < 800. Autoscaling **max** values come
   from this budget.
2. **API scaling:** target tracking on ALB requests per target and CPU; scale out early, scale in slowly; pre-scale for
   known promotions.
3. **Consumer scaling:** custom CloudWatch metric for consumer lag (or the lag-in-seconds you care about); max tasks = partition
   count (24) divided by listener concurrency per task.
4. **If the budget is too small:** shorten transactions, smaller pools (virtual threads don't need bigger pools), send reads to
   replicas, add **RDS Proxy** for multiplexing, or scale the instance class.
5. **Kafka:** partitions sized for peak consumer parallelism ahead of time (adding later remaps keys).
6. Load-test the scaled-out state, not just a single task.

**Trade-offs and what can go wrong**
- Autoscaling into a connection storm: new tasks can't get connections, health checks fail, and tasks churn.
- RDS Proxy adds a hop, cost and pinning caveats.
- Scaling consumers past partitions wastes money.

**How I'd monitor it**
Aurora `DatabaseConnections` with an alarm at ~80% of the limit, Hikari pending, ECS desired vs running tasks, consumer lag,
partition count vs consumer count.

**Follow-ups to expect**
- *How is max_connections set?* -> Derived from instance memory by default; can be tuned in the parameter group.
- *Serverless v2?* -> Capacity (and connection headroom) scales with ACUs; still budget connections.
- *Virtual threads?* -> More concurrent requests, same pool; the pool becomes the limiter by design.

**60-second answer**
"I treat them as one budget. Connections used equal running tasks times pool size, so I reserve headroom under Aurora's
limit and derive the autoscaling maximums from it: API tasks times pool 15, consumer tasks times pool 10, total safely
under the limit. The API scales on requests per target and CPU, pre-scaled for promotions. Consumers scale on lag, capped
at the partition count. If the budget is too tight, I shorten transactions, use the reader, add RDS Proxy or scale the
instance. And I load-test the scaled-out state with a connections alarm at 80%."

### Q6 [senior] Aurora fails over during peak traffic while the APIs and Kafka consumers are running. What happens end to end?
tags: aurora-failover, resilience, hikari, kafka-consumer, outbox, incident, company-chase-travel

**Start here: the concepts**
- Failover promotes a replica; existing connections break; the cluster endpoint points to the new writer within tens of
  seconds (plan for up to ~60 s of errors).
- **Idempotency + outbox + at-least-once** make retries safe.

**The live scenario (functional requirement)**
*FR: "An AZ problem triggers an Aurora failover at 8 pm on a promotion day. No booking may be lost or duplicated, and the
service must recover by itself."*

**What the interviewer is really checking**
Whether your design survives a real infrastructure event, and how you'd prove it.

**How I answer it**
1. **API requests in flight:** transactions fail; the booking service returns 503 with Retry-After (not 500); mobile
   clients retry with the same Idempotency-Key, which is safe because nothing was committed or the stored response is returned.
2. **Hikari:** broken connections are evicted; new ones resolve the cluster endpoint again (low JVM DNS TTL, e.g. 10 s);
   short `connectionTimeout` keeps threads from piling up; a circuit breaker on the DB path fails fast.
3. **Readiness:** optionally reports DOWN while the DB is unreachable so the ALB drains, but **liveness stays UP** so ECS
   doesn't kill every task.
4. **Outbox relay:** pauses and resumes; rows committed before the failover are published afterwards.
5. **Kafka consumers:** DB writes fail -> the error handler retries with backoff (blocking retries are fine here because the
   outage is short); offsets aren't committed, so no loss; idempotent upserts absorb redelivery. Lag grows briefly and drains.
6. **Faster recovery:** AWS Advanced JDBC Wrapper failover plugin or RDS Proxy shortens reconnection.
7. **Proof:** quarterly failover game days in staging, measuring errors and recovery time.

**Trade-offs and what can go wrong**
- Liveness probes that check the DB turn a 30-second failover into a fleet restart.
- Infinite consumer retries without backoff hammer the database as it comes back.
- Caching DNS forever in the JVM keeps connecting to the old writer.

**How I'd monitor it**
Aurora failover events, error rate spike and recovery time, Hikari connection timeouts, consumer lag peak and drain time,
outbox age.

**Follow-ups to expect**
- *Any data loss in Aurora failover?* -> Committed data is in the shared storage volume; in-flight uncommitted transactions are lost.
- *Writes during failover?* -> Fail; clients retry idempotently.
- *How long?* -> Typically well under a minute; measure yours in game days.

**60-second answer**
"In-flight transactions fail, and we return 503 with Retry-After, so clients retry with the same Idempotency-Key, which is
safe because idempotency is enforced in the database. Hikari evicts broken connections and reconnects through the cluster
endpoint with a low JVM DNS TTL, short timeouts and a breaker keeping threads free, and liveness never checks the DB so ECS
doesn't restart the fleet. The outbox relay resumes and publishes anything committed. Consumers retry with backoff without
committing offsets, and idempotent upserts absorb redelivery. We prove it with failover game days."

### Q7 [mid] How do you develop and test this whole stack locally and in CI?
tags: testing, testcontainers, localstack, kafka, postgres, s3, company-chase-travel

**Start here: the concepts**
- **Testcontainers:** real PostgreSQL and Kafka in Docker for tests; `@ServiceConnection` wires Spring automatically.
- **LocalStack** (or MinIO): S3-compatible API locally; Testcontainers has a LocalStack module.
- **Slices:** `@WebMvcTest`, `@DataJpaTest`; full `@SpringBootTest` for flows.

**The live scenario (functional requirement)**
*FR: "Any developer can run the booking service with its database, Kafka and S3 on a laptop, and CI proves the booking
-> event -> itinerary flow on every pull request."*

**What the interviewer is really checking**
Practical engineering hygiene for a multi-dependency service.

**How I answer it**
1. **Local run:** `compose.yaml` with `postgres` (same major version as Aurora), Kafka (KRaft single node), LocalStack S3;
   `spring-boot-docker-compose` starts them and sets connection properties.
2. **Unit tests:** service logic with mocks; no containers.
3. **Controller slice:** `@WebMvcTest` + MockMvc for status codes, validation errors, Problem Details, security.
4. **Repository tests:** `@DataJpaTest` + Testcontainers PostgreSQL (never H2): constraints, upserts, Flyway migrations.
5. **Kafka tests:** Testcontainers Kafka; publish an event, assert with Awaitility that the consumer wrote the row; test
   the duplicate event and DLT paths.
6. **S3 tests:** LocalStack container; assert the object exists with the expected key and metadata; pre-signed URL
   generation tested against it.
7. **End-to-end in CI:** one `@SpringBootTest` starting all containers: POST booking -> outbox -> Kafka -> document consumer
   -> S3 object + itinerary row.

**Trade-offs and what can go wrong**
- LocalStack doesn't reproduce IAM policy behaviour or every S3 edge case; keep a smoke test in a real dev account.
- Containers slow CI; reuse containers across tests and keep the end-to-end suite small.

**How I'd monitor it**
CI duration, flaky-test rate, defects escaping to UAT.

**Follow-ups to expect**
- *Why not H2?* -> Different SQL; it hides PostgreSQL-specific behaviour like `ON CONFLICT`.
- *Mocking AWS SDK instead?* -> Fine for unit tests; integration needs a real API surface.
- *Aurora-specific features?* -> Test in a dev Aurora cluster (failover, IAM auth).

**60-second answer**
"Locally a compose file starts PostgreSQL at Aurora's major version, single-node Kafka and LocalStack S3, and Spring
Boot's Docker Compose support wires them up automatically. Tests are layered: unit tests with mocks, `@WebMvcTest` for the
HTTP contract, `@DataJpaTest` on Testcontainers PostgreSQL rather than H2, Kafka tests with Testcontainers and Awaitility
including duplicates and the DLT, and S3 tests on LocalStack. One end-to-end test in CI proves booking, outbox, Kafka,
itinerary PDF in S3. Real IAM and failover behaviour get checked in a dev AWS account."

### Q8 [senior] Production incident: bookings succeed but members get no confirmation email and no itinerary. How do you debug across Kafka, S3 and Aurora?
tags: production-incident, debugging, kafka-lag, outbox, dlt, cloudwatch, company-chase-travel

**Start here: the concepts**
- Follow the data: **booking row -> outbox row -> Kafka topic -> consumer group -> side effect (email, S3 object, DB row)**.
- Tools: SQL on Aurora, Kafka consumer-group lag, DLT, CloudWatch logs/metrics, traces, S3 listing.

**The live scenario (functional requirement)**
*FR: "Support reports that since 14:10 new bookings show as confirmed in the app, but customers get no email and the
itinerary download says 'not available'."*

**What the interviewer is really checking**
A calm, systematic, data-flow-driven investigation and the mitigation, under pressure.

**How I answer it**
1. **Scope:** all bookings or some? Since a deploy? Both email and itinerary means a **common upstream** (the event), not
   two separate consumer bugs.
2. **Outbox:** `SELECT count(*), min(created_at) FROM outbox WHERE published_at IS NULL`. Growing since 14:10 means the
   relay is stuck (crashed task, MSK auth error, a poison row blocking a sequential relay).
3. **Kafka:** if published, check the topic's latest offsets and the consumer groups' lag. Lag growing on both groups means
   consumers are down or stuck (rebalance loop, poll interval exceeded, deserialization failure after a schema change).
4. **DLT:** messages landing there means a processing error; read headers for the exception (e.g. a new event field broke
   deserialization in old consumers).
5. **Logs and traces:** follow one booking id through traces; check ECS events for task restarts and CloudWatch logs for
   exceptions.
6. **Correlate with change:** a 14:05 deploy of the booking service changed the event schema incompatibly -> consumers fail
   -> DLT.
7. **Mitigate:** roll back the producer (or deploy consumers that accept the new schema), then **replay** DLT/affected
   records; idempotent consumers make replay safe. Notify support with an ETA.
8. **Prevent:** schema-registry compatibility check in CI, consumer-lag and DLT alerts, outbox-age alert, a synthetic
   booking that checks email + itinerary end to end.

**Trade-offs and what can go wrong**
- Debugging consumers first wastes time if the outbox never published; follow the flow in order.
- Replaying without idempotency would send duplicate emails.

**How I'd monitor it**
Outbox age, consumer lag per group, DLT rate, end-to-end "booking to itinerary" latency, synthetic transaction success.

**Follow-ups to expect**
- *How do you replay a DLT?* -> A replay tool republishes selected records to the main topic after the fix; consumers dedupe.
- *Communication?* -> Incident channel, status updates to support, blameless postmortem.
- *Why didn't alerts fire?* -> Add alerts on lag trend, DLT growth and outbox age if missing.

**60-second answer**
"Both email and itinerary failing points to the shared upstream, the event, so I follow the data flow. First, are outbox
rows unpublished since 14:10? If yes, the relay is stuck. If they're published, I check consumer-group lag and the DLT. Here
the DLT headers showed a deserialization error: a 14:05 booking-service deploy changed the event schema incompatibly. We
rolled back the producer, replayed the DLT records, which idempotent consumers made safe, and briefed support. Prevention:
schema-compatibility checks in CI, alerts on lag, DLT and outbox age, and a synthetic booking that checks email and
itinerary end to end."
