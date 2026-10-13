# Microservices: boundaries, communication, resilience, data consistency

> **Runnable:** [`01_circuit_breaker_retry_bulkhead.java`](../examples/11_microservices/01_circuit_breaker_retry_bulkhead.java) ·
> [`02_saga_orchestration_with_compensation.java`](../examples/11_microservices/02_saga_orchestration_with_compensation.java) ·
> [`03_transactional_outbox_and_idempotent_consumer.java`](../examples/11_microservices/03_transactional_outbox_and_idempotent_consumer.java)
> **Crib sheet:** [`topics/08-microservices.md`](../topics/08-microservices.md) · **Guide:** Q47–Q54, Q93, Q94

## What interviewers are actually probing

Not definitions: **failure semantics**. "Service B is down, what does A do?" "How do you keep order and payment consistent without a distributed transaction?"
"Why not a monolith?" They want to hear trade-offs: network failure modes, eventual consistency, idempotency, observability cost, team structure.

## Must-know points

- A microservice is an **independently deployable** service owning its **data** and a bounded context. If you must deploy several together, it's a distributed monolith.
- The network is unreliable: every remote call needs **timeout, bounded retry (idempotent only), circuit breaker, bulkhead, fallback**.
- No cross-service ACID: use **sagas** (orchestrated or choreographed) with **compensations**, and the **transactional outbox** to publish events atomically with state changes.
- Delivery is at-least-once ⇒ consumers must be **idempotent**.
- Observability is mandatory: correlation/trace ids, structured logs, RED metrics, distributed tracing.
- Start from a **modular monolith** unless there is a concrete reason to split (scale profile, team autonomy, failure isolation, release cadence).

## Interview questions and full answers

### Q1. When would you choose microservices, and when not?

Choose when different parts need **independent scaling, release cadence, technology, or fault isolation**, and when several teams need to move without coordinating (Conway's law).
Don't when the domain is unclear, the team is small, or you lack CI/CD, observability and platform maturity: you inherit network failure, distributed data and operational cost with none of the benefit.
A **modular monolith** with enforced boundaries (Spring Modulith/ArchUnit) is the right start; extract a service when a module has a proven different scale or ownership need.

### Q2. How do you define service boundaries?

By **business capability / bounded context** (Domain-Driven Design), not by technical layer or database table. A good boundary has high cohesion, minimal chatty calls, and owns its data and invariants.
Smells: two services always changed together, a shared database, one service calling another 10 times to serve a request, "entity services" that are just CRUD over a table.

### Q3. Synchronous vs asynchronous communication?

**Sync (REST/gRPC)**: simple, immediate response, but temporal coupling — if the callee is down you fail. **Async (Kafka/RabbitMQ)**: decoupled in time, absorbs bursts, natural for events and workflows, but eventual consistency and harder debugging.
Rule of thumb: queries and user-facing request/response over sync; state-change notifications and long workflows over events. Never chain 5 sync calls on the request path.

### Q4. What happens when a downstream service is slow or down?

Without protection, threads block on the slow call, the pool exhausts, and the failure **cascades** upward (example 11/01 section 3: 10 threads × 5 s = 2 req/s capacity).
Protection stack: **timeouts** (always), **bounded retries with exponential backoff + jitter** (only idempotent), **circuit breaker** (fail fast while open, probe in half-open), **bulkhead** (limit concurrency per dependency), **fallback/degraded response**, **load shedding/rate limiting**, and **async decoupling** where the business allows.
In Spring: Resilience4j (`@CircuitBreaker`, `@Retry`, `@Bulkhead`, `@TimeLimiter`) or Spring Cloud CircuitBreaker; Spring Framework 7 adds `@Retryable`/`@ConcurrencyLimit`.

### Q5. Explain the circuit breaker states.

**Closed**: calls pass; failures are counted in a sliding window. When the failure (or slow-call) rate exceeds the threshold → **Open**: calls fail immediately (fallback) for a wait duration. → **Half-open**: allow a few probe calls; success closes it, failure re-opens it.
Tune: window size, minimum calls, failure-rate threshold, slow-call threshold, wait time. Emit a metric/alert on state changes. (Example 11/01 section 2 shows the exact transitions.)

### Q6. How should retries be designed?

Retry only **transient** errors (timeouts, 502/503/504, 429 honouring `Retry-After`) on **idempotent** operations, with exponential backoff and **jitter** to avoid synchronised retry storms, a max attempts/total-time budget, and ideally at **one layer only** (3 layers × 3 attempts = 27× load).
Make non-idempotent operations safe with idempotency keys.

### Q7. How do you maintain data consistency across services (the saga pattern)?

A **saga** is a sequence of local transactions; if one fails, **compensating** transactions undo the earlier ones (cancel reservation, refund).
**Orchestration**: a coordinator drives the steps (explicit flow, easy timeouts/monitoring; the coordinator is a component to own — Temporal, Camunda, Step Functions, or your own state machine).
**Choreography**: services react to events (loose coupling; the flow is implicit and gets hard to follow/cyclic as it grows).
Design points: idempotent steps and compensations, durable saga state, per-step timeouts, **semantic** undo (the customer may have seen "payment taken"), and handling a stuck compensation (retry then alert). Example 11/02 runs both failure paths.

### Q8. What is the transactional outbox and why is it needed?

"Update DB then publish to Kafka" is a **dual write**; a crash between them loses or duplicates the event. The **outbox** writes the business change and an `outbox` row in **one local transaction**; a relay (polling publisher using `FOR UPDATE SKIP LOCKED`, or **CDC** such as Debezium reading the WAL) publishes the rows and marks them sent.
Delivery becomes at-least-once, so consumers dedupe by event id (**inbox/idempotent consumer** table). Example 11/03 shows the lost-event failure, the fix, and the duplicate after a relay crash.

### Q9. How do you achieve idempotent message handling?

Give every event a stable id (assigned in the producer's transaction). In the consumer, in the **same transaction** as the side effect, `INSERT INTO processed_event(id)` with a primary key; a duplicate violates the key and is skipped.
Or make the operation naturally idempotent (UPSERT by business key, `status = PAID` rather than `balance += x`, version check). Keep the dedupe table longer than topic retention / maximum replay window.

### Q10. API gateway, service discovery and configuration — what do they do?

**API gateway** (Spring Cloud Gateway, Kong, AWS API Gateway): single entry, routing, auth, rate limiting, TLS, aggregation — keep business logic out of it.
**Service discovery**: on Kubernetes use DNS Services (kube-dns) — you rarely need Eureka; client-side load balancing via Spring Cloud LoadBalancer is optional.
**Configuration**: ConfigMaps/Secrets, Spring Cloud Config or Vault; hot reload via Actuator `refresh` only where justified. Service mesh (Istio/Linkerd) can move mTLS, retries and telemetry out of application code.

### Q11. CQRS and event sourcing — when are they appropriate?

**CQRS** separates the write model from read models (denormalised views, search index) — useful when read and write shapes/scale differ greatly; the cost is eventual consistency between them.
**Event sourcing** stores state as an append-only event log (strong audit/temporal queries; complexity in versioning, replay and snapshots). Neither is a default; say "I'd use CQRS for a read-heavy search view fed by events, not event-source the whole system".

### Q12. How do you test microservices?

Unit tests; component tests with the service in-process and its dependencies faked or containerised (Testcontainers); **consumer-driven contract tests** (Pact/Spring Cloud Contract) so provider changes can't silently break consumers; a small number of end-to-end happy paths in a staging environment;
chaos/failure injection (latency, 503s, broker down) to verify the resilience configuration actually works; and production **canary + SLO** monitoring.

### Q13. How do you version events and APIs between services?

Additive changes, tolerant readers (ignore unknown fields), explicit schema (Avro/Protobuf/JSON Schema with a registry and compatibility rules: backward, forward, full), version in the event type/name for breaking changes, run old and new in parallel and migrate consumers, then remove.

### Q14. Design: "Place order" across Order, Inventory, Payment, Shipping.

Order service saves `PENDING` order + outbox event atomically → `OrderCreated` (key = orderId) → Inventory reserves (idempotently) and emits `InventoryReserved/Rejected` → Payment charges (idempotency key) → on failure, compensate (release inventory) → Order becomes `CONFIRMED/REJECTED` → notification.
Say: state machine for the order, timeouts per step, DLT per consumer, reconciliation job for stuck sagas, and observability keyed by orderId. See example 11/02 and 11/03 together.

## A worked example

Run example 11/01, then adjust `CircuitBreaker(window=10, minCalls=5, threshold=0.5, open=5s, probes=2)` to see how a smaller window opens sooner but flaps more.
Run example 11/03 and note that the topic contains **two copies** of the event after the relay crash: that duplicate is the justification for section 4's dedupe.

## Hands-on drills

1. Add a "slow call" threshold to the breaker (calls > 1 s count as failures).
2. Make the saga resumable: persist the journal and recover after a crash mid-way.
3. Implement a polling outbox relay with `SELECT … FOR UPDATE SKIP LOCKED` for two relay instances.
4. Draw the failure modes of a 4-hop synchronous call chain and the timeout budget for each hop.
5. Write the contract (JSON schema) for `OrderCreated` v1 and a compatible v2.

## The 60-second spoken answer

"I'd split services along business capabilities that own their data, but start with a modular monolith unless scale or team autonomy demands otherwise.
Every remote call gets timeouts, bounded retries for idempotent operations, a circuit breaker and a bulkhead, so a slow dependency can't exhaust our threads.
For cross-service consistency I use sagas with compensations and the transactional outbox so events are published atomically with state changes;
since delivery is at-least-once, consumers are idempotent. And I make it observable with correlation ids, structured logs, RED metrics and traces."
