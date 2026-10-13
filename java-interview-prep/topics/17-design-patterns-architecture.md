---
id: 17-patterns-architecture
title: Design Patterns, SOLID, Clean/Hexagonal Architecture
focus: Code-level and application-level design; how a Lead guides design decisions
deep_dive: 17,20
examples: 17_design_patterns
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

### Q21 [basic] What are Design Patterns? How many types are there?
Named, reusable solutions to recurring object-oriented design problems - a shared vocabulary, not code you copy. The Gang-of-Four catalogue has **23 patterns in 3 categories**:
- **Creational (5)** - how objects are made: Singleton, Factory Method, Abstract Factory, Builder, Prototype.
- **Structural (7)** - how objects are composed: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy.
- **Behavioural (11)** - how objects collaborate: Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor.

Beyond GoF: enterprise/J2EE patterns (DAO, DTO, Front Controller, Service Locator), concurrency patterns (producer-consumer, thread pool) and architectural patterns (see Q23).
> Follow-up: which three have you actually used, and what was the alternative?

### Q22 [intermediate] When should you NOT use a design pattern?
When there is no real problem yet: patterns add indirection. Warning signs - a `Factory` with one implementation, a `Strategy` interface with one class, a `Singleton` that is really global state, a pattern chosen "because it is in the book" (over-engineering, speculative generality).
Rules: apply YAGNI, wait for the second or third variation (rule of three), prefer a lambda/record/enum/DI when the language already solves it, and judge by readability for the next developer. Refactor *towards* a pattern when the pain appears.

### Q23 [intermediate] Design pattern vs architectural pattern?
| | Design pattern | Architectural pattern |
|---|---|---|
| Scope | classes/objects inside a component | structure of the whole system or a layer |
| Examples | Singleton, Strategy, Observer, Decorator | Layered, MVC, Hexagonal, Event-driven, Microservices, CQRS |
| Cost of change | a refactor | a re-platform / re-org |
| Decided by | developer | architect + team |

An architecture is usually *built from* design patterns (MVC uses Observer, Strategy and Front Controller).

### Q24 [basic] Commonly used design patterns in Spring?
- **Singleton** - default bean scope (one per container, not per JVM).
- **Factory / Abstract Factory** - `BeanFactory`, `ApplicationContext`, `FactoryBean`.
- **Proxy** - AOP, `@Transactional`, `@Cacheable`, `@Async`, Spring Data repositories.
- **Template Method** - `JdbcTemplate`, `RestTemplate`, `TransactionTemplate`, `KafkaTemplate`.
- **Observer** - `ApplicationEvent` / `@EventListener`.
- **Strategy** - `AuthenticationProvider`, `HandlerMapping`, `ResourceLoader`, `PlatformTransactionManager`.
- **Chain of Responsibility** - servlet / Spring Security filter chain, interceptors.
- **Front Controller** - `DispatcherServlet`.  **Builder** - `HttpSecurity`, `UriComponentsBuilder`.  **Adapter** - `HandlerAdapter`.  **Dependency Injection / IoC** - the container itself (a principle, not a GoF pattern).

### Q25 [intermediate] Is Spring MVC a design pattern? If yes, what is it?
**MVC is an architectural pattern** (separating Model, View, Controller in the presentation layer); "Spring MVC" is the framework module that implements it. Request flow: `DispatcherServlet` (**Front Controller**) -> `HandlerMapping` (Strategy) -> interceptors (Chain of Responsibility) -> `@Controller` -> model -> `ViewResolver` -> view. In a REST API the view step is replaced by `HttpMessageConverter`s writing JSON.

### Q26 [intermediate] How many ways can you create a Singleton? How is it broken?
Ways: (1) eager `static final`, (2) lazy unsynchronized (**not** thread-safe), (3) `synchronized getInstance()` (safe, contended), (4) double-checked locking with `volatile`, (5) holder idiom (lazy, no locking), (6) **enum** (safest), plus (7) a container-managed Spring singleton bean.
Breakers: **reflection** (`setAccessible(true)` on the private constructor - guard in the constructor; enum is immune), **serialization** (add `readResolve()`; enum is immune), **cloning** (don't implement `Cloneable`), and **multiple classloaders** (one instance per loader). Prefer a Spring bean; it also fixes testability.

### Q27 [intermediate] Which pattern handles boilerplate like cleanly closing connections?
**Template Method** (in its callback/execute-around form): the template owns acquire -> use -> release -> translate exceptions, the caller supplies only the varying part. `JdbcTemplate.query(sql, rowMapper)` never exposes `Connection`/`ResultSet`, so a leak is impossible. In plain Java the language-level equivalent is **try-with-resources** (`AutoCloseable`). Not Strategy (swaps algorithms) and not Decorator (adds behaviour).

### Q28 [intermediate] How many design patterns are there in microservices?
There is no fixed number - it is a catalogue (microservices.io lists dozens) grouped by problem:
- **Decomposition**: by business capability / subdomain, strangler fig.
- **Data**: database per service, saga, CQRS, event sourcing, outbox, API composition.
- **Communication**: API gateway, BFF, service discovery, async messaging, idempotent consumer.
- **Resilience**: circuit breaker, retry + backoff, bulkhead, timeout, rate limiter.
- **Observability**: distributed tracing, log aggregation, health check, metrics.
- **Deployment/config**: sidecar, externalised configuration, blue-green / canary.
- **Security**: access token (JWT/OAuth2), mTLS.

Name the group and 1-2 patterns per group, with the problem each solves.

### Q29 [intermediate] Tell me a use case of a design pattern you used.
Structure: **problem -> pattern -> why not the alternative -> outcome**. Example: "Court-record files arrived in 100+ formats and every new source meant editing a growing `if/else`. I introduced a `FileParser` **Strategy** with a registry (Spring `Map<String, FileParser>`), so a new source is a new bean; a **Template Method** base class handled streaming, validation and quarantine; the output was a canonical record via an **Adapter** (anti-corruption layer). Onboarding a source dropped from days to hours and the shared code stopped changing." Only claim patterns you can defend with their trade-offs.

### Q30 [intermediate] Factory Method vs Abstract Factory vs Builder vs Prototype - and Singleton vs a static class?
- **Factory Method**: one product, a method (or subclass) decides the concrete type. **Abstract Factory**: a *family* of related products that must match (`UiFactory` -> Button + Checkbox for one theme).
- **Builder**: one complex object assembled step by step (many optional fields, validation in `build()`); a factory returns it in a single call.
- **Prototype**: create by copying an existing instance (`clone()`/copy constructor) when construction is expensive; prefer copy constructors over `Cloneable`.
- **Singleton vs static class**: a singleton is a real object - it can implement interfaces, be injected, mocked, lazily created and hold state; a static class cannot. That is why Spring beans beat static utility access.

### Q31 [intermediate] Proxy vs Decorator vs Adapter vs Facade vs Bridge - and when is Composite or Flyweight used?
- **Proxy**: same interface, *controls access* (lazy load, security, remote, caching; Spring AOP, Hibernate lazy entities). **Decorator**: same interface, *adds behaviour*, stackable (`BufferedReader(new FileReader())`). **Adapter**: *converts* one interface to another after the fact. **Facade**: one simpler interface over a subsystem. **Bridge**: split abstraction from implementation up front so both vary independently (JDBC `Driver`).
- **Composite**: treat a leaf and a group uniformly (file system, menu, UI tree). **Flyweight**: share immutable state to save memory (`Integer.valueOf` cache, String pool).
- Trap: Facade simplifies, Adapter makes compatible, Mediator centralises *peer* communication.

### Q32 [intermediate] Command, Iterator, Memento, Mediator, Null Object - what are they and where have you seen them?
- **Command**: request as an object (queue, undo, retry; `Runnable`, `Callable`, Kafka messages as commands). **Iterator**: traverse without exposing the structure (`Iterable`, fail-fast iterators). **Memento**: snapshot and restore state (undo, editor history). **Mediator**: peers talk through a hub (event bus, chat room, `DispatcherServlet` coordination). **Null Object**: a do-nothing implementation instead of `null` checks (`Collections.emptyList()`, `Optional`, a no-op logger).
- Chain of Responsibility vs Decorator: a chain handler may *stop* the request; a decorator always delegates and adds to the result.

### Q33 [intermediate] DAO vs Repository vs Service layer; DTO vs VO; Unit of Work; CQRS?
DAO: persistence-centric CRUD abstraction over a table. Repository: domain-centric collection of aggregates (Spring Data `JpaRepository`). Service layer: business rules and transaction boundary, calls repositories. DTO: carries data across a boundary (API, remote call), no behaviour. Value Object: immutable, compared by value (`Money`). Unit of Work: tracks changes and flushes once per transaction (JPA persistence context). CQRS: separate the write model from read models; use it only when read/write needs genuinely diverge.

### Q34 [intermediate] Which design patterns are used inside the JDK, Hibernate and Spring?
JDK: Singleton (`Runtime.getRuntime()`), Factory (`Calendar.getInstance`, `List.of`), Flyweight (`Integer.valueOf` cache), Decorator (`BufferedReader`, `Collections.unmodifiableList`), Adapter (`Arrays.asList`, `InputStreamReader`), Iterator, Strategy (`Comparator`), Observer (`PropertyChangeListener`), Template Method (`AbstractList`), Builder (`StringBuilder`, `HttpClient.newBuilder`). Hibernate: Factory (`SessionFactory`), Proxy (lazy loading), Unit of Work + Identity Map (persistence context), Template/DAO. Spring: see Q24.

### Q35 [intermediate] DI vs Service Locator? How do you choose a pattern, and what mistakes do people make?
DI: dependencies are pushed in from outside (visible in the constructor, easy to fake). Service Locator: the class pulls what it needs from a registry (hidden dependencies, global state, harder tests) - an anti-pattern in most application code.
Choosing: classify the problem (creation / structure / behaviour), pick the simplest option the language already offers, name the force it resolves, and check the cost. Common mistakes: patterns with one implementation, Singleton as global state, inheritance where composition fits, God-factories, ignoring SOLID, and cargo-culting names (`AbstractSingletonProxyFactoryBean` is a joke for a reason).
