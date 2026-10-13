# Design patterns catalogue: every GoF pattern as a basic interview Q&A

> **Runnable proof:** [`02_creational_patterns.java`](../examples/17_design_patterns/02_creational_patterns.java) ·
> [`03_structural_patterns.java`](../examples/17_design_patterns/03_structural_patterns.java) ·
> [`04_behavioral_patterns.java`](../examples/17_design_patterns/04_behavioral_patterns.java) ·
> [`01_patterns_and_solid_in_modern_java.java`](../examples/17_design_patterns/01_patterns_and_solid_in_modern_java.java)
> **Judgement and comparisons:** [17 Design patterns, SOLID, architecture](17_design_patterns.md)

This chapter is the **"explain pattern X from scratch"** layer. Chapter 17 holds the comparisons, Spring usage and architecture questions; here every pattern gets the same
six-part answer so you can give it in 60 seconds: **Intent -> Problem -> Structure -> Java/Spring example -> Pros / cons -> When not to use it.**
The interview shape is always: define it, show the problem it removes, give one real example, name the cost.

## How to answer "what is pattern X?"

1. **One-line intent** (what it does, not how).
2. **The problem** that appears without it (the `if/else` explosion, the leaked connection, the tight coupling).
3. **The structure** in two or three words (participants).
4. **A real example** from the JDK or Spring, then one from your own work.
5. **Cost / when not**: the indirection, the extra class count, the cheaper language feature.

---

## Part 1 - Creational patterns (5): how objects are made

### 1. Singleton

- **Intent:** guarantee exactly one instance of a class and provide a global access point to it.
- **Problem:** several instances of something that must be unique (configuration, registry, connection pool, cache) cause inconsistent state or wasted resources.
- **Structure:** private constructor + a static accessor that returns the single instance.
- **Ways to write it:** eager `static final`; lazy unsynchronized (**broken** under threads); `synchronized getInstance()`; double-checked locking with `volatile`; holder idiom; `enum`. Full table and the breakers in [17 Q18](17_design_patterns.md).
- **JDK / Spring:** `Runtime.getRuntime()`, `Desktop.getDesktop()`; Spring's default bean scope (one per container).
- **Pros:** controlled access, one shared resource, lazy initialisation possible. **Cons:** hidden global state, hard to unit-test, tight coupling, breaks with reflection/serialization/multiple classloaders, concurrency pitfalls.
- **Do not use when:** it is just a convenient global. Use a container-managed singleton bean and inject it.
- **Follow-ups:** why `volatile` in DCL? how do you break a singleton? Singleton vs static class (a singleton is an object: interfaces, injection, mocking)? Is a Spring singleton the GoF one (no: one per container, not per JVM, and no private constructor)?

### 2. Factory Method

- **Intent:** define an interface for creating an object but let subclasses (or the method itself) decide which class to instantiate.
- **Problem:** callers do `new ConcreteX()` everywhere, so adding a type edits every caller.
- **Structure:** Creator (abstract `createProduct()`), ConcreteCreators, Product interface.
- **JDK / Spring:** `Calendar.getInstance()`, `List.of()`, `NumberFormat.getInstance()`, `Optional.of()`, `BeanFactory.getBean()`.
- **Pros:** decouples creation from use, open/closed for new products. **Cons:** a parallel class hierarchy for creators.
- **Do not use when:** there is one implementation and no variation expected. A static factory method (`Money.of(...)`) is often enough.
- **Follow-ups:** *Simple factory* is not a GoF pattern (a static method with a `switch`); *Factory Method* uses inheritance; *Abstract Factory* uses composition and produces families.

### 3. Abstract Factory

- **Intent:** create **families** of related objects without naming their concrete classes.
- **Problem:** products must be used together (dark theme button with dark theme checkbox; one cloud vendor's queue + storage clients) and mixing them is a bug.
- **Structure:** AbstractFactory interface with several `createX()` methods; ConcreteFactory per family.
- **JDK / Spring:** `DocumentBuilderFactory`, `javax.xml.transform.TransformerFactory`, JDBC `Connection` as a factory of `Statement`s, Spring `@Configuration` profiles that choose a whole set of beans.
- **Pros:** consistency across a family, swap an entire family at once. **Cons:** adding a *new product type* means changing every factory.
- **Follow-up:** Factory Method = one product; Abstract Factory = several related products.

### 4. Builder

- **Intent:** construct a complex object step by step, separating construction from representation.
- **Problem:** telescoping constructors (`new Pizza(size, true, false, true, ...)`) and JavaBean setters that leave the object half-built and mutable.
- **Structure:** Builder with fluent setters and `build()`; optional Director that knows common recipes; immutable Product.
- **JDK / Spring:** `StringBuilder`, `Stream.Builder`, `HttpClient.newBuilder()`, `UriComponentsBuilder`, `HttpSecurity`, Lombok `@Builder`.
- **Pros:** readable call sites, optional parameters, immutability, validation in `build()`. **Cons:** boilerplate (Lombok or records reduce it), a second class.
- **Do not use when:** the type has 2-3 required fields: use a record or constructor.
- **Follow-ups:** Builder vs Factory (Builder: many steps and one product; Factory: one call, picks the type); builder vs telescoping constructors vs records.

### 5. Prototype

- **Intent:** create new objects by copying an existing instance.
- **Problem:** construction is expensive (parsing, DB lookups) or the exact configured state is hard to rebuild.
- **Structure:** Prototype interface with `copy()`; clients clone a registered prototype.
- **JDK / Spring:** `Object.clone()`, copy constructors (`new ArrayList<>(other)`), Spring `prototype` bean scope (a new instance per request for the bean).
- **Pros:** cheap duplicates, hides concrete classes. **Cons:** deep vs shallow copy bugs, `Cloneable` is a flawed API, cyclic references.
- **Follow-up:** shallow vs deep copy (see example 02 section 5); prefer a copy constructor or a static copy factory to `clone()`.

---

## Part 2 - Structural patterns (7): how objects are composed

### 6. Adapter

- **Intent:** convert the interface of a class into the one the client expects.
- **Problem:** a legacy or third-party API has the right behaviour and the wrong shape.
- **Structure:** Target interface, Adapter implementing it, Adaptee being wrapped (object adapter via composition is preferred over class adapter via inheritance).
- **JDK / Spring:** `Arrays.asList()`, `InputStreamReader` (bytes -> chars), `Collections.enumeration`, Spring `HandlerAdapter`, `HttpMessageConverter`.
- **Pros:** reuse without changing the adaptee, isolates vendor types (anti-corruption layer). **Cons:** an extra layer, many adapters if the vendor API is wide.
- **Follow-up:** Adapter vs Facade (adapter makes one interface fit another; facade simplifies many classes).

### 7. Bridge

- **Intent:** decouple an abstraction from its implementation so the two vary independently.
- **Problem:** subclassing along two dimensions gives a combinatorial explosion (`VectorCircle`, `RasterCircle`, `VectorSquare`, ...).
- **Structure:** Abstraction holds a reference to an Implementor interface; RefinedAbstractions and ConcreteImplementors vary separately.
- **JDK / Spring:** JDBC (`DriverManager` + vendor `Driver`), SLF4J facade over logging backends, `java.awt` peers.
- **Pros:** m + n classes instead of m x n, runtime switching. **Cons:** more up-front design.
- **Follow-up:** Bridge vs Adapter: a bridge is **designed in** before the code exists; an adapter fixes an incompatibility **after the fact**.

### 8. Composite

- **Intent:** compose objects into trees and treat individual objects and groups uniformly.
- **Problem:** client code keeps branching on "is this a file or a folder?".
- **Structure:** Component interface, Leaf, Composite holding child Components.
- **JDK / Spring:** `java.awt.Container`/`Component`, `Map.putAll`, JSF/Swing component trees, Spring Security `CompositeFilter`, org charts, menus.
- **Pros:** uniform recursion, easy to add node types. **Cons:** hard to restrict what a composite may contain; the interface can become too general.
- **Follow-up:** where do `add()/remove()` live (transparency vs safety trade-off)?

### 9. Decorator

- **Intent:** attach additional responsibilities to an object dynamically by wrapping it, using the same interface.
- **Problem:** subclassing for every feature combination (`BufferedGzipEncryptedStream`...) explodes.
- **Structure:** Component interface, ConcreteComponent, Decorator holding a Component, ConcreteDecorators.
- **JDK / Spring:** `BufferedReader(new FileReader(..))`, `Collections.unmodifiableList`, `Collections.synchronizedList`, servlet request/response wrappers, Spring `@Cacheable` / `@Transactional` proxies.
- **Pros:** composable at runtime, open/closed. **Cons:** many small objects, order-dependent behaviour, identity (`==`) differs from the wrapped object.
- **Follow-up:** Decorator vs Proxy vs Adapter, and Decorator vs Chain of Responsibility ([17 Q23](17_design_patterns.md)).

### 10. Facade

- **Intent:** provide one simple interface to a complex subsystem.
- **Problem:** clients must orchestrate several classes in the right order to do one business thing.
- **Structure:** Facade class delegating to subsystem classes; the subsystem stays accessible if needed.
- **JDK / Spring:** `javax.faces.context.FacesContext`, SLF4J `LoggerFactory`, a Spring application service orchestrating repositories, `JdbcTemplate` over JDBC.
- **Pros:** fewer dependencies for clients, a stable entry point. **Cons:** can become a god class that accumulates unrelated methods.
- **Follow-up:** Facade vs Mediator (facade: one-way simplification; mediator: peers communicate through it).

### 11. Flyweight

- **Intent:** share fine-grained immutable objects to cut memory.
- **Problem:** millions of tiny objects (characters in a document, map tiles, `Integer`) with mostly identical state.
- **Structure:** Flyweight (intrinsic, shared, immutable state), FlyweightFactory/pool, extrinsic state passed in by the client.
- **JDK / Spring:** `Integer.valueOf` cache (-128..127), the `String` pool, `Boolean.valueOf`, enum constants.
- **Pros:** big memory savings. **Cons:** complexity, extrinsic state handling, shared state must be immutable and thread-safe.
- **Follow-up:** why `new Integer(5) == new Integer(5)` is false while `Integer.valueOf(5) == Integer.valueOf(5)` is true (see 01/03 examples).

### 12. Proxy

- **Intent:** provide a surrogate that controls access to another object.
- **Problem:** you need lazy loading, access checks, caching, remoting or cross-cutting behaviour without changing the real class.
- **Structure:** Subject interface, RealSubject, Proxy with the same interface holding a reference.
- **Types:** virtual (lazy), protection (security), remote (RPC stubs), caching, smart reference (counting, locking).
- **JDK / Spring:** `java.lang.reflect.Proxy`, RMI stubs, Spring AOP (`@Transactional`, `@Cacheable`, `@Async`), Hibernate lazy-loaded entities, Spring Data repository interfaces.
- **Pros:** transparent to callers, separates concerns. **Cons:** extra hop, self-invocation bypasses it (a classic Spring trap: see chapter 06), JDK proxies need interfaces, CGLIB needs non-final classes.
- **Follow-up:** JDK dynamic proxy vs CGLIB; Proxy vs Decorator (intent: control access vs add behaviour).

---

## Part 3 - Behavioural patterns (11): how objects collaborate

### 13. Chain of Responsibility

- **Intent:** pass a request along a chain of handlers until one handles it.
- **Problem:** the sender should not know which receiver handles the request, and handlers should be orderable and replaceable.
- **Structure:** Handler interface with `handle(request)` and a reference to the next handler.
- **JDK / Spring:** servlet `FilterChain`, Spring Security filter chain, `HandlerInterceptor`, Log4j/Logback appender chains, approval workflows.
- **Pros:** decouples sender and receiver, flexible ordering. **Cons:** no guarantee a request is handled, long chains are hard to debug.
- **Follow-up:** order matters, so make it explicit; chain vs decorator (a handler may stop the request).

### 14. Command

- **Intent:** encapsulate a request as an object so it can be queued, logged, retried or undone.
- **Problem:** the invoker should not know the operation or its receiver; you need undo or a job queue.
- **Structure:** Command (`execute`, optionally `undo`), ConcreteCommand holding a Receiver, Invoker, Client.
- **JDK / Spring:** `Runnable`, `Callable`, `ExecutorService.submit`, `javax.swing.Action`, Spring Batch steps, Kafka messages used as commands, saga compensations.
- **Pros:** queueing, undo/redo, audit trail, macro commands. **Cons:** a class per action (lambdas reduce this).
- **Follow-up:** command vs event (a command asks for something and has one handler; an event reports a fact).

### 15. Interpreter

- **Intent:** define a grammar and an interpreter that evaluates sentences in it.
- **Problem:** a small, stable language (rules, expressions, filters) must be evaluated repeatedly.
- **Structure:** AbstractExpression with `interpret(context)`; TerminalExpression and NonterminalExpression forming an AST.
- **JDK / Spring:** `java.util.regex.Pattern`, `java.text.Format`, Spring Expression Language (SpEL), SQL/JPQL parsers.
- **Pros:** easy to extend a tiny grammar. **Cons:** poor for large grammars (class explosion): use a parser generator or library.
- **Follow-up:** rarely hand-written; say where you have *used* one (SpEL in `@Value`/`@PreAuthorize`, regex).

### 16. Iterator

- **Intent:** access the elements of a collection sequentially without exposing its representation.
- **Structure:** Iterable (`iterator()`), Iterator (`hasNext`, `next`, `remove`).
- **JDK / Spring:** every `Collection`, `Iterable` in for-each, `ResultSet`, `Scanner`, `Stream` (internal iteration), `Spliterator`.
- **Pros:** uniform traversal, multiple simultaneous traversals, lazy sequences. **Cons:** fail-fast iterators throw `ConcurrentModificationException`; weakly consistent iterators in concurrent collections do not.
- **Follow-up:** fail-fast vs fail-safe; internal (`forEach`, streams) vs external (`Iterator`) iteration.

### 17. Mediator

- **Intent:** centralise how a set of objects communicate so they do not reference each other.
- **Problem:** many-to-many references create a tangle that cannot change.
- **Structure:** Mediator interface/hub, Colleagues that only know the mediator.
- **JDK / Spring:** `java.util.Timer`, `ExecutorService` (tasks and workers), `ApplicationEventPublisher`, `DispatcherServlet`, chat rooms, air-traffic control.
- **Pros:** looser coupling, one place for interaction logic. **Cons:** the mediator can become a god object.
- **Follow-up:** Mediator vs Observer (mediator coordinates two-way interaction; observer broadcasts one-way); vs Facade.

### 18. Memento

- **Intent:** capture and externalise an object's state so it can be restored later, without breaking encapsulation.
- **Problem:** you need undo, checkpoints or rollback.
- **Structure:** Originator (creates/restores), Memento (opaque snapshot), Caretaker (stores them).
- **JDK / Spring:** `java.io.Serializable` snapshots, editor undo history, database savepoints, event-sourced aggregates (replay as a memento).
- **Pros:** undo without exposing internals. **Cons:** memory cost for large or frequent snapshots.
- **Follow-up:** make mementos immutable; combine with Command for undo/redo.

### 19. Observer

- **Intent:** when one object changes state, all dependents are notified automatically.
- **Problem:** the publisher should not hardcode who needs to react.
- **Structure:** Subject (`subscribe`, `notify`), Observer (`update`).
- **JDK / Spring:** `PropertyChangeListener`, Swing listeners, `java.util.Observable` (deprecated), Spring `ApplicationEvent`/`@EventListener`, RxJava/Reactor streams.
- **Pros:** loose coupling, dynamic subscribers. **Cons:** unexpected cascades, memory leaks if observers are never removed (the **lapsed listener** leak), no ordering guarantee, synchronous by default.
- **Follow-up:** Observer vs pub/sub (a broker adds durability, async delivery and cross-service reach); `@TransactionalEventListener(AFTER_COMMIT)`.

### 20. State

- **Intent:** let an object change its behaviour when its internal state changes, appearing to change class.
- **Problem:** a status field and a growing `switch` in every method.
- **Structure:** Context holding a State; ConcreteStates implementing the behaviour and choosing the next state (an `enum` with abstract methods is the compact Java form).
- **JDK / Spring:** `java.lang.Thread` lifecycle, TCP connection states, Spring Statemachine, order/payment/approval workflows.
- **Pros:** removes conditionals, makes transitions explicit and testable. **Cons:** more classes; overkill for two states.
- **Follow-up:** State vs Strategy (state transitions itself; the client picks a strategy).

### 21. Strategy

- **Intent:** define a family of interchangeable algorithms and let the client choose one at runtime.
- **Problem:** `if (type == ...)` chains for pricing, sorting, parsing, routing.
- **Structure:** Strategy interface, ConcreteStrategies, Context holding one.
- **JDK / Spring:** `Comparator`, `Collections.sort(list, c)`, `ThreadPoolExecutor` rejection handlers, Spring `AuthenticationProvider`, `HandlerMapping`, `PlatformTransactionManager`, injected `Map<String, Strategy>`.
- **Pros:** open/closed, testable in isolation, runtime selection. **Cons:** clients must know the options; trivial strategies are just lambdas.
- **Follow-ups:** Strategy vs State; Strategy vs Template Method (composition vs inheritance).

### 22. Template Method

- **Intent:** define the skeleton of an algorithm in a base class and let subclasses (or callbacks) fill in steps.
- **Problem:** several classes repeat the same sequence (open, process, close, handle errors) differing in one step.
- **Structure:** abstract class with a `final` template method plus abstract/hook steps.
- **JDK / Spring:** `InputStream.read(byte[])` built on `read()`, `AbstractList`, `HttpServlet.service` -> `doGet`, `JdbcTemplate`, `RestTemplate`, `TransactionTemplate`.
- **Pros:** reuse, enforced order, the "Hollywood principle" (don't call us, we'll call you). **Cons:** inheritance coupling, fragile base class; the callback form avoids it.
- **Follow-up:** the answer to "which pattern removes connection-closing boilerplate?" ([17 Q19](17_design_patterns.md)).

### 23. Visitor

- **Intent:** add new operations to a class hierarchy without modifying the classes (double dispatch).
- **Problem:** many unrelated operations (print, evaluate, validate, export) clutter stable element classes.
- **Structure:** Visitor with `visit(ElementA)`, `visit(ElementB)`; elements implement `accept(visitor)`.
- **JDK / Spring:** `java.nio.file.FileVisitor` / `Files.walkFileTree`, annotation processors' `ElementVisitor`, ASTs in compilers, Spring `BeanDefinitionVisitor`.
- **Pros:** new operations without touching elements; groups related logic. **Cons:** adding a new *element type* forces every visitor to change; breaks encapsulation. Pattern matching for `switch` and sealed types (Java 21) often replace it.
- **Follow-up:** when is it worth it (stable element set, growing operation set).

---

## Beyond GoF - patterns that come up in Java interviews

### Null Object
A do-nothing implementation used instead of `null` so callers need no checks (`Collections.emptyList()`, a no-op logger, `Optional.empty()` as the functional cousin). Pros: removes `if (x != null)`. Cons: can hide a genuinely missing value.

### Dependency Injection and Service Locator
DI supplies collaborators from outside (constructor injection preferred); a Service Locator makes the class look them up from a registry, hiding dependencies. Prefer DI; know that `ApplicationContext.getBean` is the locator the container uses internally.

### DAO, Repository, DTO, Value Object, Unit of Work
DAO = persistence-centric CRUD; Repository = domain-centric collection of aggregates; DTO = data across a boundary with no behaviour; Value Object = immutable, compared by value; Unit of Work = track changes and commit once (JPA persistence context). See [17 Q24](17_design_patterns.md).

### Front Controller and MVC
`DispatcherServlet` is the single entry point (Front Controller); MVC is the architectural pattern it implements. See [17 Q17](17_design_patterns.md).

### Concurrency patterns
Producer-consumer (`BlockingQueue`), thread pool (`ExecutorService`), future/promise (`CompletableFuture`), immutability, thread confinement (`ThreadLocal`), read-write lock. Chapter [04](04_concurrency.md).

---

## One-page cheat table

| Pattern | One-line intent | JDK / Spring anchor |
|---|---|---|
| Singleton | one instance, global access | `Runtime`, bean scope |
| Factory Method | subclass picks the product | `Calendar.getInstance`, `List.of` |
| Abstract Factory | family of related products | `DocumentBuilderFactory` |
| Builder | build complex object stepwise | `StringBuilder`, `HttpSecurity` |
| Prototype | copy an existing instance | `clone()`, prototype scope |
| Adapter | make interfaces fit | `Arrays.asList`, `HandlerAdapter` |
| Bridge | abstraction x implementation | JDBC drivers |
| Composite | tree with uniform interface | Swing/AWT components |
| Decorator | wrap to add behaviour | `BufferedReader` |
| Facade | simple front for a subsystem | `JdbcTemplate`, SLF4J |
| Flyweight | share immutable objects | `Integer` cache |
| Proxy | control access | AOP, Hibernate lazy |
| Chain of Responsibility | pass until handled | filter chains |
| Command | request as object | `Runnable` |
| Interpreter | evaluate a grammar | SpEL, regex |
| Iterator | sequential access | `Iterator`, `ResultSet` |
| Mediator | hub for peers | event bus |
| Memento | save/restore state | undo history |
| Observer | notify dependents | `@EventListener` |
| State | behaviour follows state | `Thread.State`, Statemachine |
| Strategy | swap algorithm | `Comparator` |
| Template Method | skeleton + steps | `JdbcTemplate` |
| Visitor | new operation, same elements | `FileVisitor` |

## Hands-on drills

1. Take the one pattern you are weakest on, close this file, and write its 6-part answer from memory; check against the section above.
2. Run the three example files and, for each section, predict the output before looking.
3. Spot the pattern: `new BufferedReader(new InputStreamReader(System.in))` (Decorator over Adapter), `Executors.newFixedThreadPool` (Factory), `list.sort(Comparator.comparing(...))` (Strategy + Builder-ish).
4. Replace a `switch` on a status string in your own code with an `enum` State.
5. Write the "pattern I used at work" story in 90 seconds: problem, pattern, alternative rejected, outcome ([17 Q21](17_design_patterns.md)).

## The 60-second spoken answer

"Patterns are named solutions with known trade-offs, grouped as creational (how objects are made: Singleton, Factory, Abstract Factory, Builder, Prototype), structural (how they are composed: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy) and behavioural (how they collaborate: Strategy, Observer, Command, State, Template, Chain, and the rest). For each one I can say the problem it removes, the structure, where the JDK or Spring uses it, and the cost - and I reach for a lambda, record, enum or DI first, adding a pattern only when the variation is real."
