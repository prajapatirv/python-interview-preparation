# Spring Framework core: IoC, dependency injection, bean lifecycle, AOP and proxies

> **Runnable:** [`01_mini_ioc_container.java`](../examples/06_spring_core/01_mini_ioc_container.java) ·
> [`02_aop_proxy_and_self_invocation.java`](../examples/06_spring_core/02_aop_proxy_and_self_invocation.java)
> **Crib sheet:** [`topics/05-spring-core-boot.md`](../topics/05-spring-core-boot.md) · **Guide:** Q28, Q29, Q31

## What interviewers are actually probing

"Spring vs Spring Boot" and "what is dependency injection" are warm-ups. The discriminating questions are mechanical:
*how* does the container create beans, *where* do proxies come from, *why* did my `@Transactional`/`@Async`/`@Cacheable` do nothing,
and *what* breaks with circular dependencies or prototype beans injected into singletons. If you can narrate the bean lifecycle and the
proxy mechanism, you can debug 90% of "Spring magic" problems in an interview and at work.

## Must-know points

- **IoC**: the container creates and wires objects; **DI**: dependencies are supplied (constructor / setter / field). Prefer **constructor injection**: final fields, mandatory dependencies, testable with plain `new`.
- Scopes: `singleton` (default; must be stateless), `prototype`, `request`, `session`, `application`, `websocket`.
- Bean lifecycle: instantiate → populate → `*Aware` → `BeanPostProcessor.before` → `@PostConstruct` / `afterPropertiesSet` / init-method → `BeanPostProcessor.after` (**proxies are created here**) → in use → `@PreDestroy` / `destroy`.
- Spring AOP is **proxy-based**: JDK dynamic proxy (interface) or CGLIB subclass. Calls through the proxy get advice; **self-invocation** (`this.method()`) bypasses it.
- `@Transactional` rolls back on `RuntimeException`/`Error` by default, **not** on checked exceptions.
- Circular constructor dependencies fail fast; Boot 2.6+ disallows cycles by default.

## Interview questions and full answers

### Q1. What is the difference between Spring and Spring Boot?

**Spring Framework** is the programming model and container: DI, AOP, MVC, data access, transactions, testing.
**Spring Boot** is an opinionated layer on top that removes configuration work: **starters** (curated dependency sets), **auto-configuration** (conditional beans from the classpath and properties),
an **embedded server**, **externalised configuration**, **Actuator**, and a packaged executable jar. Boot does not replace Spring; it configures it.

### Q2. What is IoC / DI and why constructor injection?

Instead of `new PaymentGateway()` inside your class, the container supplies it. Benefits: loose coupling, substitutability (fakes in tests), lifecycle managed by the container.
Constructor injection makes dependencies **explicit, final, non-null** and the class usable without Spring; it also exposes classes with too many collaborators (a design smell) and surfaces circular dependencies at startup.
Field injection (`@Autowired` on fields) hides dependencies and requires reflection or a container in tests; use setter injection only for genuinely optional dependencies.

### Q3. What are the bean scopes and the prototype-into-singleton trap?

A singleton bean is created once and receives its dependencies **once**. If it depends on a `prototype` bean, it gets one instance for its whole life — the "prototype" behaviour is lost (example 06/01 section 2).
Fixes: inject `ObjectProvider<T>`/`Provider<T>` and call `getObject()` each time, use `@Lookup` method injection, or a scoped proxy (`@Scope(proxyMode = TARGET_CLASS)`).
Singleton beans are shared across threads, so keep them **stateless** (or immutable/thread-safe).

### Q4. `@Component`, `@Service`, `@Repository`, `@Controller`, `@Configuration`, `@Bean`?

The first four are stereotypes discovered by component scanning (`@Service` is purely semantic; `@Repository` adds persistence-exception translation to `DataAccessException`; `@Controller`/`@RestController` mark web handlers).
`@Configuration` classes hold `@Bean` factory methods — use `@Bean` for third-party classes you cannot annotate or when construction needs logic. `@Configuration` classes are CGLIB-proxied so inter-bean calls return the singleton (`proxyBeanMethods=false` disables this for speed).

### Q5. Walk me through the bean lifecycle.

(Example 06/01 prints this ordering.) 1) the container reads definitions; 2) instantiates via constructor; 3) injects dependencies; 4) `BeanNameAware`/`ApplicationContextAware` callbacks;
5) `BeanPostProcessor.postProcessBeforeInitialization` (handles `@PostConstruct`); 6) `afterPropertiesSet()`/custom init; 7) `postProcessAfterInitialization` — **where AOP proxies wrap the bean**;
8) ready; 9) on shutdown `@PreDestroy`/`destroy()`. Prototype beans are **not** destroyed by the container.
Insight to state: the bean you get injected can be a *proxy*, not your class — that is why `getClass()` looks odd and why `final` classes/methods are a problem for CGLIB.

### Q6. How does Spring AOP work? JDK proxy vs CGLIB?

Spring creates a proxy that implements the same interfaces (**JDK dynamic proxy**) or subclasses your class (**CGLIB**, default in Boot via `proxyTargetClass=true`).
Method calls on the proxy run an **interceptor chain** (transaction, security, caching, async, your `@Aspect`) and then delegate to the real object.
Consequences: `final` classes/methods and `private` methods are not advised; only calls **through the proxy** are intercepted; and the advice is applied only to Spring-managed beans.

### Q7. Why didn't my `@Transactional` work? (self-invocation and friends)

Checklist, most to least common:
1. **Self-invocation**: `this.audit()` from another method of the same class bypasses the proxy (example 02 section 2). Move it to another bean, or inject the bean into itself lazily, or use AspectJ mode.
2. The method is `private`/`final`, or the class is `final` (CGLIB).
3. The object isn't a Spring bean (`new Service()`).
4. The exception is **checked** (commit by default) or is **caught** inside the method.
5. A different `@Transactional` import (`javax` vs Spring's), wrong transaction manager, or the call is on another thread.
6. `readOnly=true` hides writes on some setups.
Same family: `@Async`, `@Cacheable`, `@Retryable`, `@PreAuthorize`.

### Q8. What are the `@Transactional` propagation levels you must know?

`REQUIRED` (join or start), `REQUIRES_NEW` (suspend and start a new one — e.g. an audit record that must survive a rollback), `NESTED` (savepoint; JDBC only), `SUPPORTS`, `NOT_SUPPORTED`, `MANDATORY`, `NEVER`.
Remember `REQUIRES_NEW` holds **two connections** at once — a source of pool exhaustion deadlocks under load. (More in chapter 09.)

### Q9. How do you resolve ambiguity when two beans match a type?

`@Primary` on the preferred one, `@Qualifier("name")` at the injection point, or inject by parameter name/`Map<String, T>`/`List<T>` to receive all implementations (a clean strategy pattern).
`NoSuchBeanDefinitionException` = none; `NoUniqueBeanDefinitionException` = more than one (example 06/01 section 3).

### Q10. What are circular dependencies and how do you fix them?

A needs B and B needs A. With constructor injection Spring can't create either (fails fast with `BeanCurrentlyInCreationException`). With setters/fields Spring used to resolve it via early references; Boot 2.6+ forbids this by default.
Fix the **design**: extract the shared behaviour into a third bean, invert one dependency with an interface, or publish an event. `@Lazy` on one injection point is a last-resort patch.

### Q11. What are `BeanFactoryPostProcessor` and `BeanPostProcessor`?

`BeanFactoryPostProcessor` modifies **bean definitions** before any bean is created (`PropertySourcesPlaceholderConfigurer` resolves `${...}`).
`BeanPostProcessor` modifies **bean instances** around initialisation (autowiring annotations, `@Async`/AOP proxying). Most Spring features you use are implemented as one of these.

### Q12. `ApplicationContext` vs `BeanFactory`; events; `@Profile`; `@Conditional`?

`ApplicationContext` extends `BeanFactory` with eager singleton creation, events, i18n, resource loading, environment/profiles. Events (`ApplicationEventPublisher`, `@EventListener`, `@TransactionalEventListener(phase = AFTER_COMMIT)`) decouple modules in-process.
`@Profile` and `@Conditional*` include/exclude beans by environment — the foundation of auto-configuration.

## A worked example

Run [`01_mini_ioc_container.java`](../examples/06_spring_core/01_mini_ioc_container.java) and map each console line to a lifecycle step. Then run
[`02_aop_proxy_and_self_invocation.java`](../examples/06_spring_core/02_aop_proxy_and_self_invocation.java) and notice that section 2 prints **one** BEGIN/COMMIT for a call chain that *looks* like two transactional methods.
That single observation answers the most common Spring debugging interview question.

## Hands-on drills

1. Extend the mini container with `@Qualifier` and setter injection; make it detect a prototype injected into a singleton.
2. Write an `@Aspect` that logs method duration for all `@Service` beans and show it does not fire for self-calls.
3. Reproduce `BeanCurrentlyInCreationException`, then remove the cycle with an event.
4. Show the difference between `@Configuration` and `@Component` for `@Bean` methods calling each other (`proxyBeanMethods`).
5. Print `AopUtils.isCglibProxy(bean)` and `bean.getClass()` for a `@Transactional` service.

## The 60-second spoken answer

"Spring's container owns object creation and wiring; I use constructor injection so dependencies are explicit and testable.
Beans are singletons by default, so they're stateless. Cross-cutting features like transactions, caching and async are implemented by
proxies created in a `BeanPostProcessor` after initialisation, which is why a call from inside the same class skips them. When
`@Transactional` seems ignored I check self-invocation, visibility and final, whether the exception is checked, and whether the object is
actually a bean. Spring Boot adds auto-configuration, starters and an embedded server on top of that core."
