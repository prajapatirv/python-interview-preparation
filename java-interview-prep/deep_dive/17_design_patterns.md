# Design patterns, SOLID and clean architecture in modern Java

> **Runnable:** [`01_patterns_and_solid_in_modern_java.java`](../examples/17_design_patterns/01_patterns_and_solid_in_modern_java.java)
> **Crib sheet:** [`topics/17-design-patterns-architecture.md`](../topics/17-design-patterns-architecture.md) · **Guide:** Q3, Q4, Q32

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

## A worked example

Run [`01_patterns_and_solid_in_modern_java.java`](../examples/17_design_patterns/01_patterns_and_solid_in_modern_java.java) and pick three sections you could describe from memory with the Spring equivalent (section 9 lists them).
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
without the framework. I favour composition, immutability and value objects."
