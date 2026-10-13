# Design patterns, SOLID and clean architecture in modern Java

> **Runnable:** [`01_patterns_and_solid_in_modern_java.java`](../examples/17_design_patterns/01_patterns_and_solid_in_modern_java.java)
> **Per-pattern catalogue (every GoF pattern, basic Q&A):** [`20_design_patterns_catalogue.md`](20_design_patterns_catalogue.md)  
> **Crib sheet:** [`topics/17-design-patterns-architecture.md`](../topics/17-design-patterns-architecture.md) · **Guide:** Q3, Q4, Q32 · **Interview checklist:** crib-sheet Q21-Q35

## What interviewers are actually probing

Judgement, not memorisation: "which patterns have you *used* and why", "where does Spring use the proxy/template pattern",
"show me a thread-safe singleton", "what's wrong with this class (SOLID)?". Naming 23 GoF patterns is worse than explaining three well with their trade-offs.

## Must-know points

- Patterns are **names for recurring solutions**; modern Java (lambdas, records, enums, DI) shrinks many of them (Strategy = a lambda; Singleton = a Spring bean).
- Thread-safe singletons: **enum**, **holder idiom**, or DCL with `volatile`. Prefer container-managed singletons.
- SOLID: **S**ingle responsibility, **O**pen/closed, **L**iskov substitution, **I**nterface segregation, **D**ependency inversion.
- Prefer **composition over inheritance**; program to interfaces; keep domain logic free of framework types (hexagonal/clean architecture).
- Know where Spring uses them: proxy, template, factory, observer, strategy, chain of responsibility, builder.

## Interview questions and full answers

### Q1. Implement a thread-safe singleton and discuss alternatives.

```java
enum AppConfig { INSTANCE; ... }                       // simplest; safe against reflection/serialization

final class Registry {                                 // lazy holder idiom: class loading guarantees safe, lazy init
    private Registry() { }
    private static class Holder { static final Registry I = new Registry(); }
    static Registry get() { return Holder.I; }
}
```

Double-checked locking needs the field to be `volatile` (otherwise another thread may see a partially constructed object). In a Spring application you almost never hand-write one: a singleton-scoped bean gives lifecycle, injection and testability; static singletons hide dependencies and are hard to test.

### Q2. When do you use Builder, and what does it give over constructors?

When a type has many optional parameters or needs validation before construction: readable call sites, immutability, and the invariants enforced in `build()` (example 17 section 2). Records with compact constructors cover simple cases; Lombok `@Builder` is common.
Avoid telescoping constructors and JavaBean setters on objects that must be valid at all times.

### Q3. Strategy and Factory in modern Java?

**Strategy**: interchangeable algorithm behind an interface — in Java 8+ usually a lambda or method reference, or a `Map<String, Strategy>` injected by Spring (`Map<String, Notifier>` keyed by bean name) so adding a case is adding a bean. **Factory**: centralises creation and hides concrete types (`List.of`, `Optional.of`, `BeanFactory`); a `switch` returning lambdas is often enough.

### Q4. Decorator vs Proxy vs Adapter?

All wrap an object. **Decorator** adds behaviour with the same interface (caching/logging repository). **Proxy** controls access (lazy loading, security, transactions — Spring AOP). **Adapter** converts one interface to another (wrapping a third-party SDK behind your port).
Spring's `@Transactional`, `@Cacheable`, `@Async` are proxies/decorators created in a `BeanPostProcessor`.

### Q5. Observer and domain events?

Publishers notify subscribers without knowing them. In Spring: `ApplicationEventPublisher` + `@EventListener`; use `@TransactionalEventListener(phase = AFTER_COMMIT)` so listeners run only after the data is committed.
Across services this becomes domain events on Kafka. Keep listeners idempotent and don't rely on in-process event ordering for correctness.

### Q6. Explain each SOLID principle with a concrete violation.

- **S**: a `UserService` that validates, persists, sends email and renders reports → split by reason to change.
- **O**: `if (type.equals("csv")) … else if (type.equals("json"))` — add a format by *adding* a class/bean, not editing the chain (example 17 section 8).
- **L**: `Square extends Rectangle` where `setWidth` also changes height breaks callers' expectations; subtypes must honour the base contract (preconditions not stronger, postconditions not weaker).
- **I**: a fat `Repository` interface with 20 methods forcing no-op implementations → role-specific interfaces.
- **D**: high-level service constructs `new MySqlOrderRepo()` → depend on an `OrderRepository` abstraction injected from outside.

### Q7. What is hexagonal / clean architecture and how does it map to Spring?

Domain at the centre (entities, rules, no framework imports); **ports** (interfaces the domain needs: `OrderRepository`, `PaymentGateway`) and **adapters** (JPA repository, REST client, Kafka publisher) at the edge; dependencies point **inward**.
Spring wires adapters to ports. Benefit: domain tests run without Spring/DB; swapping infrastructure is local; ArchUnit can enforce "domain must not depend on infrastructure".

### Q8. Anemic domain model vs rich domain model?

Anemic: entities are data bags and all logic sits in services — simple but spreads invariants. Rich: entities/aggregates enforce their own invariants (`order.addItem(...)`, `order.pay()` rejects illegal state transitions).
Use DDD tactically: aggregates around transactional consistency boundaries, value objects (records) for money/ids, domain events for side effects.

### Q9. Template method vs Strategy?

Template method fixes the algorithm skeleton in a base class with overridable steps (inheritance; `JdbcTemplate`-style callbacks are the functional version). Strategy swaps the whole algorithm via composition. Prefer composition/callbacks; use template method when the skeleton must be enforced.

### Q10. Chain of responsibility and where you've seen it?

A request passes through handlers that may act or pass on: servlet filters, Spring Security's filter chain, `HandlerInterceptor`s, Netty pipelines, validation rule pipelines. Good for cross-cutting steps with independent ordering; hard to debug if the order is implicit — make it explicit and log it.

### Q11. How do you handle exceptions as part of design?

Domain exceptions that carry meaning and a stable code; translate at the boundary (one `@RestControllerAdvice`); don't use exceptions for control flow; don't catch `Exception` broadly; wrap with cause, log once at the boundary; checked exceptions for recoverable conditions the caller can act on (a judgement call; most Spring code uses unchecked).

### Q12. Immutability and value objects — why prioritise them?

Immutable objects are thread-safe, safe as map keys, easy to reason about and cache. Use `record`s, `final` fields, defensive copies (`List.copyOf`), and builders/withers. Model money, ids, ranges as value objects (`Money(BigDecimal, Currency)`) — never pass raw `double` and `String` everywhere ("primitive obsession").

### Q13. What are design patterns, and how many types are there?

Named, reusable solutions to recurring design problems; their main value is a shared vocabulary ("it's a decorator") and a known set of trade-offs.
The Gang-of-Four catalogue has **23 patterns** in three categories:

| Category | Count | Patterns |
|---|---|---|
| Creational | 5 | Singleton, Factory Method, Abstract Factory, Builder, Prototype |
| Structural | 7 | Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy |
| Behavioural | 11 | Chain of Responsibility, Command, Interpreter, Iterator, Mediator, Memento, Observer, State, Strategy, Template Method, Visitor |

Outside GoF you will be asked about enterprise patterns (DAO, DTO, Front Controller, Service Locator), concurrency patterns (producer-consumer, thread pool, future) and architectural patterns (Q15).
A good answer closes with the three you have really used and what the alternative was.

### Q14. When should you not use a design pattern?

When there is no problem yet. Patterns trade simplicity for flexibility, and that trade only pays off when the variation is real:
a factory with one implementation, a strategy interface with one class, a singleton that is just global mutable state, a visitor over a type hierarchy that never changes.
Guidance: YAGNI, the rule of three (abstract on the third variation), use the language first (lambda instead of Strategy classes, `enum` instead of Singleton, DI instead of Service Locator), and refactor *towards* a pattern when the pain shows up.
The cost is indirection: more types, harder navigation, and a debugging session that crosses five classes to find one `if`.

### Q15. Design pattern vs architectural pattern?

A **design pattern** solves a problem inside a component at class/object level (Strategy, Observer, Builder) and is cheap to change. An **architectural pattern** defines the structure and responsibilities of a whole system or layer
(layered, MVC, hexagonal, event-driven, CQRS, microservices) and is expensive to change because teams, deployments and data stores are built around it. Architectures are composed of design patterns:
MVC uses Observer (view updates), Strategy (controller selection) and Front Controller. Say which level a problem lives at before you propose a solution.

### Q16. Which design patterns does Spring use, and where?

| Pattern | Where |
|---|---|
| Singleton | default bean scope (one per `ApplicationContext`, not per JVM) |
| Factory / Abstract Factory | `BeanFactory`, `ApplicationContext`, `FactoryBean` |
| Proxy | AOP, `@Transactional`, `@Cacheable`, `@Async`, Spring Data repository interfaces |
| Template Method | `JdbcTemplate`, `RestTemplate`, `TransactionTemplate`, `KafkaTemplate` |
| Observer | `ApplicationEventPublisher`, `@EventListener` |
| Strategy | `AuthenticationProvider`, `HandlerMapping`, `ViewResolver`, `PlatformTransactionManager` |
| Chain of Responsibility | servlet and Spring Security filter chains, `HandlerInterceptor` |
| Front Controller | `DispatcherServlet` |
| Adapter | `HandlerAdapter`, `HttpMessageConverter` |
| Builder | `HttpSecurity`, `UriComponentsBuilder`, `ResponseEntity.BodyBuilder` |

Dependency Injection/IoC is the container's founding principle rather than a GoF pattern; say so, it shows you know the difference.
Trap: Spring's "singleton" is one instance per container per bean definition, so two contexts (or two bean definitions of one class) give two instances.

### Q17. Is Spring MVC a design pattern? If yes, which?

Precisely: **MVC is an architectural pattern** for the presentation layer; **Spring MVC** is a framework module that implements it, built from design patterns. The flow:

1. `DispatcherServlet` receives every request - the **Front Controller** pattern.
2. `HandlerMapping` (Strategy) picks the controller method; `HandlerAdapter` (Adapter) invokes it.
3. `HandlerInterceptor`s run before/after (Chain of Responsibility).
4. The `@Controller` returns a model (and a view name).
5. `ViewResolver` (Strategy) renders the view; in a `@RestController` an `HttpMessageConverter` writes JSON instead.

Run section 12 of the example for a 20-line version of this loop.

### Q18. How many ways can you create a Singleton, and how is each one broken?

| Approach | Thread-safe | Lazy | Notes |
|---|---|---|---|
| eager `static final` | yes | no | simplest; built at class load |
| lazy, unsynchronized `if (i == null)` | **no** | yes | two threads can create two instances |
| `synchronized getInstance()` | yes | yes | lock on every call |
| double-checked locking | yes with `volatile` | yes | without `volatile` a half-built object can leak |
| holder idiom | yes | yes | class loading guarantees safety; no locking |
| `enum` | yes | on first use | immune to reflection and serialization |
| Spring singleton bean | yes | configurable | lifecycle, DI, testable; preferred in applications |

**How they break:** reflection (`setAccessible(true)` then `newInstance()` - guard in the constructor, or use an enum); serialization (a deserialized copy is a new object unless you add `readResolve()`);
`clone()` (do not implement `Cloneable`); several classloaders (one instance per loader, common in app servers); and, most commonly, tests that cannot reset the static state.
Section 10 of the example demonstrates the reflection and serialization failures and their fixes.

### Q19. Which pattern removes boilerplate such as cleanly closing connections?

**Template Method**, in the callback ("execute-around") form: the template owns the lifecycle - acquire, use, release, translate exceptions - and the caller passes only the variable step.
`JdbcTemplate.query(sql, rowMapper)` never exposes a `Connection`, so a leak is impossible by construction; `TransactionTemplate` does the same for commit/rollback.
At language level the equivalent is **try-with-resources** over `AutoCloseable` (closes in reverse order, keeps the primary exception and records close failures as *suppressed*).
Distractors in a multiple-choice question: Strategy swaps an algorithm, Decorator adds behaviour, Singleton controls instance count - none manage a lifecycle.

### Q20. How many design patterns are there in microservices?

There is no fixed number; it is a catalogue, and the honest answer is the groups plus examples (see Chris Richardson's catalogue at microservices.io):

| Concern | Patterns |
|---|---|
| Decomposition | by business capability, by subdomain, strangler fig |
| Data | database per service, saga, CQRS, event sourcing, transactional outbox, API composition |
| Communication | API gateway, backend-for-frontend, service discovery, async messaging, idempotent consumer |
| Resilience | circuit breaker, retry with backoff and jitter, bulkhead, timeout, rate limiter |
| Observability | distributed tracing, log aggregation, health check API, application metrics |
| Deployment and config | sidecar, externalised configuration, blue-green, canary |
| Security | access token (JWT/OAuth2), mTLS between services |

Tie each to a failure mode: "saga because there is no distributed transaction; outbox because the DB write and the Kafka publish are not atomic" (see [11 microservices](11_microservices.md)).

### Q21. Tell me about a use case where you applied a design pattern.

Use **problem -> pattern -> alternative rejected -> measurable outcome**, and only claim what you can defend.
Example: *"Court-record files came in 100+ formats and each new source meant editing a growing `if/else` in the import service. I defined a `FileParser` Strategy with a registry of Spring beans, so a source became a new bean (open/closed);
a Template Method base class owned streaming, validation and quarantine; and an Adapter mapped each vendor's schema into our canonical record, which acted as an anti-corruption layer.
I rejected one class per format with inheritance because the variation was in parsing only. Onboarding a new source went from days to hours and the shared pipeline stopped changing."*
Follow-ups to prepare: how you tested it (contract tests with sample files), what went wrong (registry ordering, duplicate `supports()` matches) and when you would not do it again.

### Q22. Factory Method vs Abstract Factory vs Builder vs Prototype; Singleton vs a static class?

| Pattern | Creates | Use when |
|---|---|---|
| Factory Method | one product; subclass or method picks the concrete type | caller should not know the concrete class |
| Abstract Factory | a *family* of products that must match | themes, per-vendor SDK sets, per-environment clients |
| Builder | one complex object, step by step | many optional fields, validation before construction |
| Prototype | a copy of an existing instance | construction is expensive; prefer copy constructors over `Cloneable` |

**Singleton vs static class:** a singleton is an object - it can implement an interface, be injected, mocked, created lazily and hold state; a static class is a bag of functions with no polymorphism and no seam for tests.
Use static only for pure, stateless helpers.

### Q23. Structural and behavioural patterns that are easy to confuse

| Pair | Distinguishing question |
|---|---|
| Proxy vs Decorator | does it *control access* (proxy) or *add behaviour* (decorator)? Both keep the same interface |
| Adapter vs Bridge | fixing an incompatibility *after the fact* (adapter) vs designing abstraction and implementation to vary independently *up front* (bridge) |
| Adapter vs Facade | converts one interface vs simplifies a whole subsystem |
| Facade vs Mediator | one-way simplification for clients vs peers communicating through a hub |
| Strategy vs State | the client picks the algorithm vs the object changes behaviour as its own state changes |
| Strategy vs Template Method | composition (swap whole algorithm) vs inheritance (fixed skeleton, overridden steps) |
| Chain of Responsibility vs Decorator | a handler may stop the request; a decorator always delegates and augments |

Also know: **Composite** (leaf and group behind one interface; trees), **Flyweight** (share immutable state, e.g. the `Integer` cache), **Command** (request as an object: queue, undo, retry),
**Iterator**, **Memento** (snapshot/restore), **Null Object** (no-op instead of `null`).

### Q24. Patterns inside the JDK and Hibernate; DAO vs Repository vs Service; DI vs Service Locator

**JDK:** `Runtime.getRuntime()` (Singleton), `List.of`/`Calendar.getInstance` (Factory), `Integer.valueOf` cache (Flyweight), `BufferedReader` and `Collections.unmodifiableList` (Decorator), `Arrays.asList` and `InputStreamReader` (Adapter),
`Comparator` (Strategy), `Iterator`, `StringBuilder` / `HttpClient.newBuilder()` (Builder). **Hibernate:** `SessionFactory` (Factory), lazy-loading proxies, persistence context = Unit of Work + Identity Map.

**DAO vs Repository vs Service:** DAO is persistence-centric CRUD around a table; a Repository is a domain-centric collection of aggregates (Spring Data); the service layer holds business rules and the transaction boundary.
DTOs cross boundaries without behaviour; value objects are immutable and compared by value.

**DI vs Service Locator:** with DI dependencies are pushed in and visible in the constructor; with a locator the class pulls them from a global registry, hiding the dependency and making tests harder.
Frameworks hide a locator inside (`ApplicationContext.getBean`) - application code should not call it.

**Choosing a pattern and common mistakes:** classify the problem (creation, structure, behaviour), take the simplest thing the language gives you, and state the cost.
Mistakes: one-implementation factories, Singleton as global state, inheritance where composition fits, ignoring SOLID, and pattern names used as decoration.
Section 13 of the example prints a few JDK patterns you can verify yourself.

## A worked example

Run [`01_patterns_and_solid_in_modern_java.java`](../examples/17_design_patterns/01_patterns_and_solid_in_modern_java.java) and pick three sections you could describe from memory with the Spring equivalent (section 9 lists them).
Per-pattern runnable demos: [02 creational](../examples/17_design_patterns/02_creational_patterns.java), [03 structural](../examples/17_design_patterns/03_structural_patterns.java), [04 behavioural](../examples/17_design_patterns/04_behavioral_patterns.java).
Sections 10-13 of example 01 add the singleton breakers (reflection, serialization), the execute-around / Template Method idiom a miniature `DispatcherServlet` and JDK patterns you can verify (Flyweight, Decorator, Adapter, Singleton).
For each, say the *problem* it solved, the alternative, and the cost.

## Hands-on drills

1. Refactor a 200-line `if/else` service method to strategies registered as Spring beans.
2. Show a Liskov violation in a type hierarchy you know and fix it with composition.
3. Introduce a port/adapter for an external payment API and test the domain with a fake.
4. Replace primitive `String email, String currency` params with value objects.
5. Write an ArchUnit test forbidding `domain` → `infrastructure` imports.

## The 60-second spoken answer

"I treat patterns as vocabulary: Strategy is usually a lambda or an injected map of beans, singletons are container-managed, Builder gives
validated immutable objects, and Spring itself is built on proxy, template and observer. I apply SOLID practically — split by reason to change,
add behaviour by adding a bean rather than editing a switch, depend on ports — and organise code hexagonally so the domain is testable
without the framework. I favour composition, immutability and value objects, and I do not reach for a pattern until there is a second variation."
