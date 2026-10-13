---
id: 08-microservices
title: Microservices Architecture & Patterns
focus: Boundaries, data, sagas, resilience, communication, deployment
---

### Q1 [basic] What is a microservice and what are the benefits and costs?
A small, independently deployable service owning one business capability and its data. Benefits: independent scaling/deploys, team autonomy, fault isolation, technology choice. Costs: network failures, distributed data consistency, testing and debugging complexity, operational overhead (deploy, monitor, secure N services).

### Q2 [basic] How do you decide service boundaries?
Use Domain-Driven Design: **bounded contexts** around business capabilities (Orders, Payments, Inventory), high cohesion inside, low coupling between. A good boundary changes for one reason and one team owns it. Splitting by technical layer (a "DB service") is a smell.

### Q3 [intermediate] Synchronous vs asynchronous communication?
Sync (REST/gRPC): simple, immediate answer, but couples availability and latency. Async (Kafka/RabbitMQ events): decouples, absorbs spikes, enables fan-out, but is eventually consistent and harder to trace. Rule: commands that need an immediate answer = sync; facts that others react to = events.

### Q4 [intermediate] Why "database per service" and how do you handle joins?
Shared DBs couple services at the schema level. Each service owns its data and exposes it by API/events. For cross-service queries: API composition (aggregator/BFF), **CQRS read models** built from events, or replicate needed reference data via events.

### Q5 [intermediate] Explain the Saga pattern. Choreography vs orchestration?
A saga is a sequence of local transactions with **compensating actions** if a later step fails (Order -> Reserve stock -> Charge payment; on payment failure release stock and cancel order). Choreography: services react to each other's events (simple, hard to see the whole flow). Orchestration: a coordinator drives steps (clear flow, central logic; Temporal, Camunda, Step Functions). Compensations must be idempotent.

### Q6 [intermediate] What is the Transactional Outbox pattern and why?
You can't atomically write to the DB **and** publish to Kafka. Write the event into an `outbox` table in the same DB transaction, then a relay (poller or CDC such as Debezium) publishes it. Consumers dedupe by event id. This gives at-least-once publishing without dual-write bugs.

### Q7 [intermediate] How do you handle distributed transactions without 2PC?
Avoid them: design aggregates inside one service, use sagas/outbox, make operations idempotent, accept eventual consistency, and add reconciliation jobs that detect and repair drift. 2PC (XA) hurts availability and is not supported by most cloud messaging.

### Q8 [intermediate] Which resilience patterns do you apply on every remote call?
Timeout, retry with backoff + jitter (idempotent calls only), circuit breaker, bulkhead, rate limiter, fallback, and load shedding. Order matters: `Retry( CircuitBreaker( RateLimiter( TimeLimiter( call ))))`. Test with fault injection (Chaos Monkey, Toxiproxy).

### Q9 [intermediate] What is service discovery and how does it work in Kubernetes?
Clients find instances by name. In Kubernetes a `Service` gives a stable DNS name (`orders.default.svc`) and load-balances across ready pods, so Eureka/Consul are usually unnecessary. Client-side load balancing (Spring Cloud LoadBalancer) matters for non-Kubernetes setups.

### Q10 [intermediate] What is an API Gateway vs BFF vs Service Mesh?
Gateway: one entry point for external traffic (auth, routing, limits). BFF (Backend for Frontend): an API tailored per client type (web, mobile). Service mesh (Istio/Linkerd): sidecar proxies handling mTLS, retries, traffic shifting and telemetry for east-west traffic - adds operational complexity, so adopt when you have many services.

### Q11 [intermediate] How do you handle configuration and secrets across services?
Externalised config (ConfigMaps, Spring Cloud Config, AWS Parameter Store/AppConfig), secrets in Vault/Secrets Manager (injected at runtime, rotated), environment-specific overlays (Kustomize/Helm), no secrets in images or Git, and feature flags for runtime toggles.

### Q12 [advanced] How do you version events and APIs between services?
Add-only changes (new optional fields), never repurpose a field, use a schema registry (Avro/Protobuf/JSON Schema) with BACKWARD compatibility, tolerate unknown fields (tolerant reader), dual-publish old+new versions during migration, and use consumer-driven contract tests.

### Q13 [advanced] How do you test microservices?
Pyramid: many unit tests, service-level integration tests with **Testcontainers** (real DB/Kafka), consumer-driven **contract tests** between services, a few end-to-end tests in a staging environment, plus load and chaos tests. Avoid relying on full-system E2E for every change.

### Q14 [advanced] How do you do deployments safely?
CI builds an immutable image -> deploy to staging -> smoke/contract tests -> **canary or blue/green** with automatic rollback on SLO breach -> feature flags to decouple deploy from release. Database changes follow expand/contract so old and new versions run together.

### Q15 [advanced] How do you decompose a monolith (strangler fig)?
Put a facade/gateway in front, route one capability at a time to a new service, keep the monolith running, sync data via events/CDC, and delete the old code once traffic is moved. Start with a module that has clear boundaries and high change rate; avoid a big-bang rewrite.

### Q16 [advanced] What are the signs you've built a "distributed monolith"?
Services must be deployed together, share a database, call each other in long synchronous chains, share a big common library with domain logic, or one failure takes everything down. Remedy: re-draw boundaries, introduce events, remove shared DB, shrink shared libs to technical utilities.

### Q17 [design] Design an e-commerce checkout across Order, Inventory, Payment and Notification services.
Orchestrated saga: Order creates `PENDING` -> Inventory reserves stock -> Payment charges (idempotency key) -> Order marks `CONFIRMED` -> Notification sends email from the `OrderConfirmed` event. Failure paths: payment fails -> release stock -> `CANCELLED`; timeouts handled by a saga timer. Use outbox for every event, idempotent consumers, a dead-letter queue, a status API for the UI, and dashboards for stuck sagas.

### Q18 [design] Design for high availability: what do you do at service, data and infrastructure level?
Service: multiple replicas across zones, readiness/liveness, graceful shutdown, timeouts and breakers. Data: replicated DB with failover, backups and tested restore, idempotent writes. Infra: multi-AZ nodes, pod anti-affinity/topology spread, PodDisruptionBudgets, autoscaling, no single point of failure (gateway, DNS, queue). Define RTO/RPO and test failover regularly.

### Q19 [design] Design the observability for 30 microservices.
Three pillars with one correlation id: **metrics** (RED: rate, errors, duration per endpoint + JVM/pool metrics), **logs** (structured JSON with `traceId`, central search), **traces** (OpenTelemetry across HTTP and Kafka headers). SLOs and burn-rate alerts per service, golden-signal dashboards, an on-call runbook per alert.

### Q20 [intermediate] When should you NOT use microservices?
Small team, unclear domain, simple CRUD, low scale, or no DevOps maturity. A modular monolith with clean module boundaries is faster to build and easy to split later.

### Q21 [intermediate] What is CQRS and when is Event Sourcing worth it?
CQRS separates the write model from read models optimised for queries (often separate stores). Event sourcing stores state as an append-only list of events - great for audit and replay, but adds complexity (schema evolution, snapshots, eventual consistency). Use it only where history is a core requirement (finance, ledger).
