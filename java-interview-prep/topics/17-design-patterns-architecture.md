---
id: 17-patterns-architecture
title: Design Patterns, SOLID, Clean/Hexagonal Architecture
focus: Code-level and application-level design; how a Lead guides design decisions
---

### Q1 [basic] Explain the SOLID principles with one example each.
S: a class has one reason to change (separate `InvoicePrinter` from `InvoiceCalculator`). O: extend behaviour without modifying code (new `DiscountStrategy`). L: subtypes must work wherever the base type is used (a `Square` that breaks `Rectangle` setters violates it). I: small client-specific interfaces. D: depend on abstractions, inject implementations (Spring DI).

### Q2 [basic] Which design patterns do you use most in Java/Spring?
Strategy (pluggable algorithms, e.g. court-specific parsers), Factory/Abstract Factory, Builder, Singleton (Spring beans), Template Method (`JdbcTemplate`), Decorator/Proxy (AOP), Observer (events), Adapter (integrations), Chain of Responsibility (filters). Give a project example for each you claim.

### Q3 [intermediate] Strategy vs State vs Template Method?
Strategy: the caller picks an interchangeable algorithm. State: the object changes behaviour as its internal state changes (order status). Template Method: base class defines the skeleton and subclasses fill steps. Example: a `Parser` interface with `CsvParser`, `XmlParser` chosen by a registry keyed by file type.

### Q4 [intermediate] Implement a thread-safe Singleton and say why Spring beans make it mostly unnecessary.
Best: `enum Singleton { INSTANCE }` or the holder idiom:
```java
class Config { private Config(){}
  private static class H { static final Config I = new Config(); }
  static Config get(){ return H.I; } }
```
In Spring prefer a singleton-scoped bean injected where needed - testable, no static access.

### Q5 [intermediate] Builder vs telescoping constructors vs records?
Builder for objects with many optional fields (readable, validated in `build()`); records for simple immutable data with required fields; static factory methods for named constructors. Lombok's `@Builder` is common - but generate sparingly and keep invariants in the constructor.

### Q6 [intermediate] What is Dependency Inversion vs Dependency Injection vs IoC?
DIP: high-level policy shouldn't depend on low-level details - both depend on abstractions. DI: a technique to supply dependencies from outside. IoC: the container controls creation and lifecycle. DIP is the design principle; DI/IoC are the mechanisms.

### Q7 [intermediate] Composition vs inheritance?
Prefer composition: it avoids fragile base classes and allows runtime changes. Use inheritance for a true is-a relationship with a stable base. Interfaces + delegation give reuse without tight coupling.

### Q8 [intermediate] What is Domain-Driven Design - the key terms?
Ubiquitous language, **bounded context**, **entity** (identity), **value object** (immutable, compared by value), **aggregate** (consistency boundary with a root; one transaction per aggregate), **repository**, **domain service**, **domain event**. Helps find microservice boundaries and keep business logic out of controllers.

### Q9 [intermediate] Explain Hexagonal (Ports & Adapters) / Clean Architecture.
The domain core has no dependency on frameworks. **Ports** are interfaces the core defines (`OrderRepository`, `PaymentGateway`); **adapters** implement them (JPA, REST client, Kafka). Inbound adapters (controllers, consumers) call use cases. Benefits: testable core, swap infrastructure, clearer dependency rule (dependencies point inward). Enforce with ArchUnit tests.

### Q10 [intermediate] What is an anti-corruption layer?
A translation layer between your domain and an external/legacy model so their concepts don't leak into your code - e.g. an adapter mapping a vendor's court-record XML into your canonical record.

### Q11 [advanced] Anemic domain model vs rich domain model?
Anemic: entities are just data and all logic is in services - easy but spreads rules and allows invalid states. Rich: entities enforce invariants (`order.addItem()` checks status). Don't overdo it: pragmatic teams put invariants in aggregates and orchestration in application services.

### Q12 [advanced] How do you manage technical debt as a Lead?
Make it visible (a debt register with impact), allocate a fixed capacity (e.g. 15-20% per sprint), tie items to business risk (incidents, velocity), prioritise by cost-of-delay, use the boy-scout rule in feature work, automate guard rails (Sonar quality gate, ArchUnit, dependency updates), and avoid giant rewrites.

### Q13 [advanced] Code review: what do you look for and how do you give feedback?
Correctness and edge cases, tests, readability, naming, security (injection, authz, secrets), performance (N+1, blocking), error handling and logging, API compatibility, observability. Feedback: be specific, explain why, prefer questions to commands, separate must-fix from nits, automate style (formatter/linter) so reviews focus on design.

### Q14 [advanced] Event-driven architecture: events vs commands vs messages?
Event = fact that happened (`OrderPlaced`), many consumers, producer doesn't care. Command = request to do something (`ChargeCard`), one handler. Message = the transport envelope. Name events in the past tense, keep payloads stable and versioned, and don't create hidden coupling by making consumers depend on producer internals.

### Q15 [advanced] Feature flags - benefits and risks?
Decouple deploy from release, enable canary, kill switch, A/B tests. Risks: flag debt (remove after rollout), combinatorial testing, hidden coupling. Use a platform (LaunchDarkly, Unleash, Spring Cloud Config/AppConfig), give each flag an owner and an expiry date.

### Q16 [design] Design an extensible parser framework for 100+ file formats/sources.
Define `FileParser` (`supports(FileMeta)`, `parse(InputStream) -> Stream<Record>`) and a registry that discovers implementations (Spring beans / `ServiceLoader` / Quarkus CDI). Canonical record schema with versioning; per-source mapping config; streaming parsing (no whole-file in memory); validation + quarantine for bad rows; contract tests with sample files per source; metrics per parser; CLI wrapper (Picocli) for local runs.

### Q17 [design] Design an audit-trail capability for an ERP.
Capture who/what/when/before/after for sensitive entities via JPA entity listeners/Hibernate Envers or CDC; write to an append-only store; include correlation id and tenant; ensure audit write is in the same transaction (or via outbox for async); protect from tampering (restricted writes, hashes), retention policy and search UI.

### Q18 [design] Design a multi-step approval workflow engine.
Model workflow definitions (steps, conditions, approvers) as data; a state machine per instance (Spring Statemachine or a simple enum + transitions table); persisted history; timers for escalation (scheduler/Quartz); idempotent actions; notifications via events; consider Camunda/Temporal for complex cases rather than building from scratch.

### Q19 [intermediate] How do you decide build vs buy vs open source?
Compare total cost (build + run + maintain), time to market, fit with requirements, vendor lock-in, security/licensing, community health, and team skills. Build only what differentiates the business; document the decision (ADR).

### Q20 [intermediate] What is an Architecture Decision Record (ADR)?
A short document: context, options considered, decision, consequences. Stored in the repo, immutable (superseded by a new ADR). Gives new team members the "why", prevents repeated debates and shows leadership maturity.
