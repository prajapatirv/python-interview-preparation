# Distributed services, Kafka and Redis

Questions 145–171 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Trace a consumer crash

An OrderCreated consumer inserts (consumer_name, event_id) under a unique constraint and reserves stock in the same database transaction. It commits, then crashes before acknowledging Kafka. On replay the insert detects a duplicate. Treat that duplicate as a completed event, acknowledge it and leave stock untouched. Inject a second crash before database commit: both writes must roll back, so replay must reserve stock. Testing both sides of the commit proves why the dedupe marker and business effect share one transaction.

## Interview questions and answers

### Q145. Monolith vs microservices; when should a monolith not be split?

A monolith gives one deployment and easy local transactions. Microservices give independent releases, ownership and scaling at the cost of network failures, deployment coordination and eventual consistency. Keep a modular monolith when boundaries are changing or one small team owns the whole workflow. Extract a measured bottleneck or independently evolving capability first.

### Q146. How do you identify service boundaries? Domain-driven design basics.

Find bounded contexts by following business language, invariants and ownership. Catalog describes a product, pricing decides a quote and fulfillment reserves stock, each with different change drivers. Keep strongly coupled updates within an aggregate or service when possible. Frequent synchronous back-and-forth and coordinated releases suggest the boundary needs revision.

### Q147. Database per service; why avoid shared databases?

Give each service authority over its own schema and writes so changes can be deployed independently. Direct reads of another schema couple clients to migrations. For cross-service views replicate events into a query model or compose APIs. Accept freshness lag explicitly. Logical ownership can share a database server while access controls isolate schemas.

### Q148. REST vs gRPC vs messaging; synchronous vs asynchronous communication.

REST provides interoperable resource-oriented calls. gRPC provides typed contracts and efficient streaming for controlled clients. Messaging buffers work and decouples availability but adds duplicate delivery, lag and correlation concerns. Use a synchronous call when checkout needs an immediate quote and an event when analytics can follow later.

### Q149. API Gateway, service discovery, load balancing and centralized configuration.

A gateway authenticates and routes external requests. Discovery identifies available service instances, and load balancing selects healthy targets. Central configuration distributes versioned settings with validation and rollback. Cache safe last-known configuration so a control-plane outage need not stop serving requests. Keep business ownership in services.

### Q150. How do you handle service-to-service authentication and authorization?

Use workload identity with short-lived credentials, for example mTLS between services or audience-scoped OAuth client tokens. Authenticate the calling workload and authorize its specific operation. When acting for a user, propagate constrained user context and enforce tenant ownership at the receiving service. Rotate keys and audit denied and privileged calls.

### Q151. How do you maintain backward compatibility during API changes?

Prefer additive optional fields with safe defaults and tolerant readers. Renaming a required property, changing units or adding an enum value can break older clients. Deploy consumers able to read both formats, then switch writers and remove the old form after usage disappears. Contract-test old and new clients during mixed-version rollout.

### Q152. Timeout vs retry vs circuit breaker vs bulkhead; how do they work together?

Bound each call with a deadline derived from the request budget. Retry only transient, replay-safe failures within the remaining time. A breaker stops sending to an unhealthy target and probes recovery. A bulkhead caps concurrent work for that dependency. Without the bulkhead, slow calls can exhaust threads before the breaker opens.

### Q153. Retry with exponential backoff and jitter; when can retries make an outage worse?

Backoff increases delay across attempts and jitter spreads clients over time. Cap attempts, elapsed time and total retry traffic. Three layers each making three attempts can multiply one request into 27 dependency calls. Retry at the layer that understands idempotency and the deadline. Honor backpressure and avoid retrying deterministic validation failures.

### Q154. Fallback strategies; rate limiting; load shedding.

Serve a timestamped cached catalog or omit optional recommendations if their service fails. For payments return a pending state and reconcile uncertain outcomes. Rate limits allocate capacity among callers, while load shedding rejects excess work early to protect latency. Track fallback usage as a degradation signal even when HTTP status is successful.

### Q155. Saga pattern: choreography vs orchestration; compensating transactions.

A saga coordinates local commits and compensations. Choreography uses events such as StockReserved and PaymentFailed, while orchestration persists explicit workflow state and commands participants. If payment fails release the reservation using an idempotent command. Compensation can fail too, requiring retries, reconciliation and an operator-visible terminal state.

### Q156. 2-phase commit vs Saga; why distributed transactions are difficult.

Two-phase commit prepares participants and records a coordinator decision before final commit. Prepared resources may hold locks during coordinator or network failure, and every participant needs compatible support. A saga permits intermediate visible states and later semantic compensation. A refund is a new business event and can have fees or timing constraints.

### Q157. How do you achieve idempotency? Idempotency keys and deduplication.

Persist a caller-scoped key, payload fingerprint and result under a unique constraint. Create the order and record success in one transaction. Replays with identical payload receive the recorded result and mismatched reuse is rejected. Define behavior for concurrent in-flight requests and retain keys across the retry horizon. Propagate keys to external payment operations.

### Q158. At-most-once vs at-least-once vs effectively-once processing.

Acknowledging before processing risks losing the effect on a crash, giving at-most-once attempts. Acknowledging after durable success allows replay on a crash before acknowledgment. Achieve effectively-once business outcomes by combining at-least-once transport with atomic deduplication and the update in one transaction. Specify which effect the guarantee covers.

### Q159. Outbox pattern; CDC; solving the dual-write problem.

Writing an order then separately publishing an event leaves a crash window. Insert both the order and an outbox row in the same transaction. A poller or CDC connector publishes committed rows. A relay crash after publish can duplicate events, so consumers deduplicate by event ID. Monitor oldest unpublished age and preserve per-aggregate sequencing.

### Q160. CAP theorem; eventual consistency; strong consistency; quorum basics.

During a partition, a system cannot guarantee both linearizable reads/writes and successful responses from every reachable nonfailed node. Eventual replicas can converge after communication resumes. With N replicas, R+W>N gives overlapping read/write quorums under fixed membership, but overlap alone does not ensure linearizability. Consider concurrent writers and version selection.

### Q161. Distributed locks, leader election, clock skew and split-brain scenarios.

A lease-based leader may pause past expiry and later issue stale writes after another leader takes over. Use consensus-backed election and monotonically increasing fencing tokens checked by the resource on each write. Wall-clock timestamps from separate machines can disagree. A lock without fencing cannot by itself protect against split-brain effects.

### Q162. Kafka topics, partitions, offsets, brokers, replication and ISR.

A topic consists of partition logs. An offset identifies position within one partition. Brokers host leaders and replicas. The in-sync replica set tracks replicas sufficiently caught up with the leader. With acks=all and a suitable minimum ISR, writes can fail when too few replicas remain, protecting durability at an availability cost.

### Q163. Consumer groups; partition assignment; rebalancing; ordering guarantees.

In a conventional consumer group each partition is assigned to at most one member at a time, and members can own multiple partitions. Membership changes trigger assignment changes. Persist progress and handle revocation without committing unfinished work. Order exists per partition; key related events consistently and serialize their effects if order matters.

### Q164. Kafka delivery semantics; idempotent producer; transactions and exactly-once caveats.

Idempotent producers suppress duplicates caused by producer retries within Kafka's protocol. Transactions can atomically publish multiple Kafka records and consumed offsets. Consumers using read_committed see committed transactional output. A database write or external payment lies outside this boundary and needs its own deduplication protocol. [Kafka design](https://kafka.apache.org/41/design/design/)

### Q165. Retry topic vs DLQ; poison messages; offset commit strategies.

Retry transient failures with bounded attempts or delayed retry topics. Send permanently invalid records to a DLQ with event identity, schema and failure context. Commit the next offset after effects or durable handoff succeed, accounting for contiguous completion within a partition. Moving records aside can change business order. Make redrive observable and idempotent.

### Q166. How do you handle duplicate events and out-of-order events?

Track event ID and aggregate version. Insert the dedupe marker and update state atomically. On replay return success without reapplying the business effect. Ignore superseded updates when safe, and buffer or recover missing predecessors if deltas require contiguous versions. A timestamp alone is unreliable for ordering across producers.

### Q167. How do you monitor consumer lag and troubleshoot a growing backlog?

Inspect per-partition end minus committed offset and age of oldest work. Compare arrival and completion rates with processing latency, errors, rebalances and downstream saturation. One hot partition suggests key skew. All partitions lagging after a release suggests a systemic slowdown. Extra consumers help only where partitions and dependencies allow parallel work.

### Q168. Redis cache-aside vs write-through; TTL and invalidation.

Cache-aside reads cache first, fills on miss and normally invalidates after authoritative writes. Write-through synchronously updates through a cache layer that also persists data. Define behavior on partial failure. TTL bounds ordinary staleness but concurrent old fills can resurrect stale values. Use versioned entries where stale reads would matter.

### Q169. Cache stampede, cache penetration, hot keys and distributed caching.

Coalesce same-key misses and jitter expiries to limit stampedes. Short negative caching or a Bloom filter reduces misses for absent keys. A hot key can saturate one shard despite balanced overall traffic. Local replicas or brief in-process caching help read-heavy keys, with an explicit freshness budget. Measure per-key skew and eviction rate.

### Q170. Production: one downstream service is slow--how do you prevent cascading failure?

Trace the slow dependency and cap its concurrency immediately so it cannot exhaust the request pool. Apply a short deadline, stop excessive retries and open the breaker if calls keep timing out. Degrade optional fields or return a retryable response for mandatory ones. Recover gradually and verify queue depth and tail latency return to baseline.

### Q171. Production: API latency, error rate or Kafka lag suddenly increases--how do you investigate?

Scope the increase by route, tenant, release and partition. Overlay traffic, error codes, latency percentiles and saturation with recent changes. Follow a slow trace to separate queue wait, application CPU and remote I/O. For Kafka compare production and consumption slopes. Mitigate the evidenced cause, then reproduce under comparable load and alert on recurrence.
