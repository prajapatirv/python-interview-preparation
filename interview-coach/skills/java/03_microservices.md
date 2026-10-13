---
id: microservices
title: Microservices architecture
order: 3
summary: Decomposition, data ownership, sagas, outbox, service-to-service communication, resilience.
crib: java/java-interview-prep/topics/08-microservices.md
docs: java/java-interview-prep/deep_dive/11_microservices.md
examples: java/java-interview-prep/examples/11_microservices
keywords: microservice, microservices, monolith, saga, outbox, service discovery, api gateway, gateway, bff, eureka, distributed transaction, two-phase, 2pc, cqrs, event sourcing, bounded context, service mesh, inter-service, eventual consistency, aggregate
---
Skill focus for Microservices architecture answers:
- Start from business boundaries (bounded contexts) and data ownership: one service owns its data.
- Distributed transactions: saga (choreography vs orchestration), transactional outbox, idempotent consumers; avoid 2PC.
- Sync vs async communication and when each fits; API gateway, BFF, service discovery, configuration.
- Resilience and failure isolation; zero-downtime deploys; API versioning.
- Always discuss the cost: operational complexity, eventual consistency, debugging across services (correlation ids, tracing).
