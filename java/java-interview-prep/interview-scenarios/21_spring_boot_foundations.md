---
id: foundations-spring-boot
title: Spring & Spring Boot: from the basics (drafted)
stack: java
skill: spring-boot
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What are IoC and Dependency Injection?
tags: spring, ioc, dependency-injection, constructor-injection, spring-container, bean, basics

**Start here: the concepts**
- **Dependency:** an object that another object needs to do its job. If `OrderService` calls `PaymentClient`, then `PaymentClient` is its dependency.
- **Inversion of Control (IoC):** normally your code decides when to create objects (`new PaymentClient()`). With IoC you hand that decision to a framework. Control is "inverted" because the framework builds and connects the objects, and your code just declares what it needs. It exists so classes are not tied to specific implementations or to how those are built.
- **Container:** the part of Spring (the `ApplicationContext`) that creates objects, wires them together and manages their lifetime.
- **Bean:** an object the Spring container manages, for example a class marked `@Service` or `@Component`.
- **Dependency Injection (DI):** the technique IoC uses in Spring. Instead of an object fetching or creating its dependencies, the container passes them in. IoC is the principle; DI is how Spring applies it.
- **Three ways to inject:** *constructor* (dependencies arrive as constructor arguments), *setter* (via a setter method after construction) and *field* (Spring sets a private field directly, usually with `@Autowired`).

**The live scenario**
A team's order service used field injection (`@Autowired` on private fields). Its 300 unit tests each needed a Spring context to fill those fields, so the build took about 12 minutes. One developer also wrote `new OrderService()` in a helper. The fields stayed `null`, and it threw a `NullPointerException` in production on roughly 2% of requests. The team moved to constructor injection. Tests now create the class with plain `new` and mock objects, the build dropped to about 2 minutes (illustrative numbers), and a missing dependency became a compile error instead of a runtime surprise.

**What the interviewer is really checking**
Whether you know that IoC is the idea and DI is the mechanism, and whether you can explain why constructor injection is preferred, not just recite that it is.

**How I answer it**
1. **Define IoC first.** The container creates and wires objects instead of my code calling `new`. This keeps classes loosely coupled, because they depend on types, not on how those types are built.
2. **Define DI as the way IoC is delivered.** The container passes dependencies in, through the constructor, a setter or a field.
3. **Recommend constructor injection.** The reasons:
   - Fields can be `final`, so the object is never changed after it is built.
   - Dependencies are required: the object cannot exist half-built.
   - Tests work without Spring, because you just call the constructor.
4. **Show it briefly.** Since Spring 4.3, a class with a single constructor needs no `@Autowired`:
```java
@Service
public class OrderService {
    private final PaymentClient payment;
    public OrderService(PaymentClient payment) { this.payment = payment; }
}
```
5. **Say where the others fit.** Setter injection suits optional dependencies. Field injection hides dependencies and cannot be used without reflection or Spring, so I avoid it in new code.

**Trade-offs and what can go wrong**
- Constructors with many parameters (say 7 or more) are a signal that the class does too much. Split it rather than going back to field injection.
- Circular dependencies (A needs B, B needs A) cannot be solved by constructor injection. That is a useful warning about bad design. Spring Boot 2.6 and later forbids circular references by default.
- If two beans match one type, startup fails with an ambiguity error. Fix it with `@Primary` or `@Qualifier`.
- IoC adds some "magic". Wiring problems appear at startup, not at compile time.

**How I'd monitor it**
- Startup logs: failed wiring appears as `UnsatisfiedDependencyException`, `NoSuchBeanDefinitionException` or `BeanCurrentlyInCreationException`. Search for these in Splunk after each deployment.
- Build time: unit tests that need no Spring context run fast, so I track the test suite duration.
- Actuator: the `beans` endpoint (if exposed) shows what the container created and wired.

**Follow-ups to expect**
- *What is the difference between IoC and DI?* -> IoC is the general principle of handing control of object creation to a framework. DI is one concrete technique for it.
- *Why is field injection discouraged?* -> It hides dependencies, prevents `final` fields, and needs reflection or a Spring context to set them in tests.
- *What happens if two beans match the type being injected?* -> Startup fails with a `NoUniqueBeanDefinitionException`. Use `@Primary` or `@Qualifier` to choose one.

**60-second answer**
Inversion of Control means the framework, not my code, creates objects and connects them, so I do not write `new` everywhere. Dependency Injection is how Spring does that: it passes the objects a class needs through the constructor, a setter or a field. I prefer constructor injection. The dependencies can be `final`, the object cannot be created without them, and I can unit test the class with plain `new` and mocks, without starting Spring. I use setters only for optional dependencies and avoid field injection. If a constructor grows too long, that tells me the class has too many responsibilities.

### Q2 [fresher] What are bean scopes?
tags: spring, bean-scope, singleton, prototype, dependency-injection, scoped-proxy, basics

**Start here: the concepts**
- **Bean**: an object that Spring creates and manages for you, instead of you calling `new`.
- **Container (ApplicationContext)**: the Spring runtime that creates beans, wires them together and keeps them.
- **Scope**: the rule that says how many instances of a bean exist and how long each lives.
- **Singleton**: one shared instance per container, per bean definition. This is not the classic one-per-JVM design pattern. Every class that asks for it gets the same object.
- **Prototype**: a new instance every time the bean is requested from the container. Spring creates it and hands it over, but does not track it afterwards, so destroy callbacks such as `@PreDestroy` are not called.
- **Request, session, application scopes**: web-only scopes. A request-scoped bean lives for one HTTP request, a session-scoped bean for one user's session, and an application-scoped bean for the whole web application. They only work in a web-aware context. (There is also a `websocket` scope.)
- **Thread-safe / stateless**: many threads can use the object at once without corrupting it. Stateless means it holds no per-user data in fields.
- **Proxy**: a stand-in object that looks like the real bean but looks up the correct real instance on each call.

**The live scenario**
A checkout service handles about 50 concurrent users. A developer adds a field `List<Item> cart` to a `@Service` class. Spring makes services singletons by default, so all 50 users share one list. In testing with one user everything works. In production, customers start seeing items from other people's carts, and support gets about 30 complaints in an hour. The fix is to keep the cart in a local variable or a session-scoped bean, and keep the service stateless.

**What the interviewer is really checking**
Whether you know that singleton is the default and what that means for thread safety. Also whether you know the prototype-into-singleton trap.

**How I answer it**
1. Name the scopes: singleton (default), prototype, and the web scopes request, session and application. Web scopes need a web application.
2. Explain singleton first. Spring creates one instance and shares it, which is cheap and fast. The reason it must be stateless or thread-safe is that many request threads call that one object at the same time.
3. Explain prototype. Use it when each caller needs its own object with its own state. Spring gives a fresh one per request to the container but does not manage its destruction, so you must clean up resources yourself.
4. Explain the trap. A singleton is built once, and its dependencies are injected at that moment. If you inject a prototype into it, the prototype is created once and then stays fixed. You get one instance, not a new one each time.
5. Fix the trap with `ObjectProvider<T>`, which asks the container for a fresh instance on demand. The alternative is a scoped proxy, which injects a stand-in that resolves the right instance on every call.
6. The same issue applies to request or session beans injected into singletons. These need a scoped proxy too, otherwise Spring cannot inject them at startup.

```java
private final ObjectProvider<ReportBuilder> builders;
ReportBuilder b = builders.getObject(); // new prototype each call
```

**Trade-offs and what can go wrong**
- Mutable fields in singletons cause data leaking between users and race conditions. This is the most common mistake.
- Prototypes cost more to create. Because Spring does not call their destroy callbacks, resources such as connections or file handles can leak.
- Session scope keeps data in memory for every active user, which hurts when scaling to many users or multiple servers.
- Scoped proxies hide a lookup on every call, which is a small cost and can confuse debugging.

**How I'd monitor it**
- Actuator `/actuator/beans` shows the beans and their scopes, so you can confirm what you configured.
- Heap and GC metrics (Micrometer `jvm.memory.used`) reveal prototype or session objects piling up.
- With Tomcat metrics enabled, active session counts show session-scope memory pressure.
- Load tests with parallel users, checking that responses never contain another user's data.
- Splunk: search error logs for `ConcurrentModificationException` or complaints of wrong data, and for scope-related startup errors such as "Scope 'request' is not active".

**Follow-ups to expect**
- *Is a Spring singleton the same as the GoF singleton?* -> No. Spring gives one instance per bean definition per container, not one per JVM or classloader. Two containers can each hold their own.
- *Why does a prototype injected into a singleton not change?* -> Injection happens once when the singleton is created, so the singleton keeps that first prototype forever.
- *Does Spring call `@PreDestroy` on prototype beans?* -> No. The container creates and hands them over but does not manage their full lifecycle, so you must release their resources yourself.

**60-second answer**
A bean scope decides how many instances Spring creates and how long they live. The default is singleton, meaning one shared instance per container, so it must be stateless or thread-safe because many threads use it. Prototype gives a new instance each time it is requested, but Spring does not manage its destruction. The web scopes are request, session and application, and they only work in a web application. The classic trap is injecting a prototype into a singleton: injection happens once, so you only ever get one instance. To fix it I use `ObjectProvider<T>` or a scoped proxy, and I keep per-user state out of singleton fields.

### Q3 [fresher] What does `@SpringBootApplication` do?
tags: spring boot, annotations, auto-configuration, component-scan, ioc, configuration, basics

**Start here: the concepts**
- **Annotation**: a label such as `@Service` that you put on a class. Spring reads these labels and decides what to do with the class.
- **Bean**: an object that Spring creates and manages for you, instead of you writing `new`. Spring can then wire beans together (this is IoC/dependency injection).
- **`@Configuration`**: marks a class that declares beans, usually with `@Bean` methods. It is Spring's way of saying "these are instructions for building objects."
- **Component scanning (`@ComponentScan`)**: at startup Spring walks through the classes in a package and its sub-packages, and registers every class marked `@Component`, `@Service`, `@Repository` or `@Controller` as a bean. It saves you from listing each bean by hand.
- **Auto-configuration (`@EnableAutoConfiguration`)**: Spring Boot looks at the libraries on your classpath and creates sensible default beans. For example, if a database driver and Spring JDBC are present, it creates a `DataSource`. Each default is conditional (`@ConditionalOnClass`, `@ConditionalOnMissingBean`), so it backs off when you define your own bean.
- **Meta-annotation**: an annotation built from other annotations. `@SpringBootApplication` is one: a single label that stands for three.

**The live scenario**
A team of six refactors a service. Someone moves the `main` class into `com.acme.orders.boot`, while the 14 controllers stay in `com.acme.orders.web`. The app starts in about 4 seconds with no errors and the health check is green. But every endpoint returns 404, and in staging about 100% of requests fail. Nothing crashed, because component scanning only covers the main class's package and below. It never found the controllers. Moving the class back to `com.acme.orders` fixed it.

**What the interviewer is really checking**
Whether you know it is three annotations in one, and whether you understand component scanning's package rule and why it matters. A good candidate also knows that auto-configuration is conditional, not magic.

**How I answer it**
1. **It is a shortcut for three annotations.** `@SpringBootApplication` combines `@SpringBootConfiguration` (a specialised `@Configuration`, so the class can declare beans), `@EnableAutoConfiguration` and `@ComponentScan`. This lets one line on the main class bootstrap the whole app.
2. **`@ComponentScan` starts at the main class's package and goes downward.** Spring uses the annotated class's package as the starting point because it has no other hint about where your code lives. Classes in sibling or parent packages are silently ignored, which is why the main class belongs in the root package.
3. **`@EnableAutoConfiguration` creates default beans from the classpath.** Boot reads a list of auto-configuration classes shipped inside its jars. Each one checks conditions first and applies only if they hold. Your own beans win, because the defaults back off.
4. **You can adjust both behaviours.**
```java
@SpringBootApplication(scanBasePackages = "com.acme", exclude = DataSourceAutoConfiguration.class)
```
   `scanBasePackages` widens the scan. `exclude` switches off an auto-configuration you do not want.

**Trade-offs and what can go wrong**
- The main class in the wrong package gives silent 404s or `NoSuchBeanDefinitionException`, not a clear startup error.
- Auto-configuration hides what is happening. If you do not know which defaults were applied, debugging is hard.
- Scanning a very broad package (for example `com`) slows startup and can pick up unwanted classes.
- The default package (no `package` line) is a bad idea, because Spring would scan the entire classpath.
- Auto-configuration can create a bean you did not expect, such as a `DataSource` that fails because no URL is configured. Use `exclude` or provide the config.

**How I'd monitor it**
- Run the app with `--debug` to print the conditions report, which lists which auto-configurations matched and which did not.
- Use the Actuator `/actuator/beans` and `/actuator/conditions` endpoints (when exposed and secured) to see which beans exist.
- Write a `@SpringBootTest` that loads the context and calls one endpoint, so a missing scan fails in CI instead of in staging.
- Alert on a sudden rise in 404 rate right after a deployment. In Splunk, search the access logs for `status=404` grouped by `uri`.

**Follow-ups to expect**
- *My beans in another package are not found. What do I do?* -> Move the main class up to a common root package, or set `scanBasePackages` (or `@ComponentScan`) to include them.
- *How does Boot know which auto-configurations to apply?* -> It loads a list of candidate classes from the Boot jars (an `AutoConfiguration.imports` file in recent versions, `spring.factories` in older ones). Each class is guarded by conditions such as `@ConditionalOnClass` and `@ConditionalOnMissingBean`.
- *How do I turn off one auto-configuration?* -> Use `exclude` on `@SpringBootApplication`, or set `spring.autoconfigure.exclude` in properties.

**60-second answer**
`@SpringBootApplication` is a convenience annotation that combines three others. `@SpringBootConfiguration` is a specialised `@Configuration`, so the class can declare beans. `@ComponentScan` finds `@Component`, `@Service` and `@Controller` classes, starting from the main class's package and going down into sub-packages. `@EnableAutoConfiguration` makes Boot create default beans based on the libraries on the classpath, and each default backs off if I define my own bean. Because of the scan rule, I put the main class in the root package, otherwise my components are silently not found and I get 404s or missing-bean errors. If needed I can use `scanBasePackages` to widen the scan, or `exclude` to turn off a specific auto-configuration.

### Q4 [fresher] `@Component` vs `@Service` vs `@Repository` vs `@Controller` vs `@Bean`?
tags: spring, spring-boot, ioc, component-scanning, stereotype-annotations, dependency-injection, basics

**Start here: the concepts**
- **Bean**: an object that Spring creates, stores and manages for you. You ask for it instead of writing `new`.
- **IoC container**: the part of Spring that holds all the beans. "Inversion of control" means Spring decides when objects are created and wired, not your code.
- **Dependency injection (DI)**: Spring passes a bean the other beans it needs, usually through the constructor, so classes don't build their own collaborators.
- **Component scanning**: at startup Spring searches your packages for classes carrying certain annotations and registers each one as a bean. `@SpringBootApplication` scans its own package and all sub-packages.
- **Stereotype annotation**: a class-level label that says "register me as a bean" and also states the class's role. `@Component` is the base one. `@Service`, `@Repository` and `@Controller` are specialised versions of it.
- **Exception translation**: each database technology throws its own exceptions. Spring converts them into one common family, `DataAccessException`, so your code doesn't depend on a specific database or library.
- **`@Configuration` class and `@Bean` method**: a class holding methods that you write to build beans by hand. Whatever the method returns is registered as a bean.

**The live scenario**
A team ran an order service handling about 200 requests per second. A class that used JPA's `EntityManager` directly was annotated `@Component`. Another class caught `DataIntegrityViolationException` to return HTTP 409 for duplicate orders. After a promotion, duplicates appeared and customers got HTTP 500 instead of 409. About 3% of requests failed. The cause was that the persistence layer threw a raw JPA exception, because exception translation only applies to beans marked `@Repository`. The catch block never matched. Changing `@Component` to `@Repository` fixed it.

**What the interviewer is really checking**
Whether you know that three of these annotations are scanning labels with different meanings, and that `@Bean` is a different mechanism, not just another label.

**How I answer it**
1. **`@Component` is the generic one.** Spring finds it by scanning and registers the class as a bean. Use it when no other label fits.
2. **`@Service` marks business logic.** It adds no extra behaviour today. It documents the layer, and tools or aspects can target it.
3. **`@Controller` marks the web layer.** It handles HTTP requests. `@RestController` is `@Controller` plus `@ResponseBody`, so return values become JSON.
4. **`@Repository` marks data access and adds real behaviour.** Beans carrying it get their persistence exceptions translated into `DataAccessException`. Spring Boot registers the translator automatically. Spring Data interfaces such as `JpaRepository` already get this, so you don't annotate them.
5. **`@Bean` is different.** It goes on a method, not a class, and Spring registers the returned object. Use it for third-party classes you can't annotate, or when construction needs custom logic.
```java
@Configuration
class AppConfig { @Bean ObjectMapper mapper() { return new ObjectMapper(); } }
```
6. **Use `@Bean` inside `@Configuration`.** Spring then ensures that calling one `@Bean` method from another returns the same singleton, not a new object. In a plain `@Component` it still works, but without that guarantee.

**Trade-offs and what can go wrong**
- Using `@Component` everywhere works but loses the documentation value of the layer. It also loses translation if the class is really a repository.
- A class outside the scanned packages is silently ignored, which causes "no qualifying bean" errors at startup.
- Putting `@Service` on a data-access class gives no exception translation.
- Too many `@Bean` methods for your own classes is noise. Prefer annotations for code you own.

**How I'd monitor it**
- Expose `/actuator/beans` (it is not exposed over HTTP by default) to check whether a bean is registered.
- Read startup logs for `NoSuchBeanDefinitionException` and similar errors.
- In Splunk, search for raw exceptions such as `PersistenceException` reaching the controller layer. They show translation is missing.
- Alert on a rising 5xx rate per endpoint.

**Follow-ups to expect**
- *What does `@RestController` add?* -> It combines `@Controller` and `@ResponseBody`, so return values are written as JSON, not treated as view names.
- *Why not use `@Component` for everything?* -> It works, but you lose clear layering, and `@Repository` exception translation only applies to `@Repository` beans.
- *Why does `@Bean` usually sit in a `@Configuration` class?* -> Spring proxies that class so inter-bean method calls return the same singleton. Without it, each call would create a new object.

**60-second answer**
`@Component`, `@Service`, `@Repository` and `@Controller` are class-level labels. Spring finds them by component scanning and registers each class as a bean. `@Component` is the generic one. `@Service` marks business logic and `@Controller` marks the web layer. `@Repository` marks data access and also translates database exceptions into Spring's common `DataAccessException`. `@Bean` is different: it goes on a method inside a `@Configuration` class, and Spring registers whatever that method returns. I use it for third-party classes I can't annotate, or when creation needs custom logic. I once saw a 500 error where a 409 was expected, because a data class was labelled `@Component`, so its exceptions were never translated.

### Q5 [mid] How does auto-configuration work?
tags: spring-boot, auto-configuration, conditional, classpath, actuator, dependency-injection, basics

**Start here: the concepts**
- **Bean:** an object that Spring creates and manages for you, such as a `DataSource` or a JSON `ObjectMapper`. Other classes receive it by injection instead of building it themselves.
- **Configuration class:** a class annotated `@Configuration` whose methods (`@Bean`) tell Spring how to build beans.
- **Auto-configuration:** a set of ready-made configuration classes shipped with Boot and starters. They exist so you don't hand-write the same setup (connection pool, JSON, web server) in every project.
- **Classpath:** the jars your app has on board. Boot uses it as a clue: if the Kafka client jar is present, you probably want Kafka set up.
- **Condition (`@Conditional...`):** a rule attached to a configuration class or bean method. If the rule is false, Spring skips it. Examples:
  - `@ConditionalOnClass`: apply only if a given class is on the classpath, i.e. the library is present.
  - `@ConditionalOnMissingBean`: apply only if you haven't defined a bean of that type. This is called "backing off".
  - `@ConditionalOnProperty`: apply only if a config property has a given value.
- **Candidate list:** a text file inside each library, `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`, naming the auto-configuration classes to consider. Older Boot versions used `spring.factories` for this; Boot 3 uses the `.imports` file.

**The live scenario**
A payments team declared their own `ObjectMapper` bean to add one custom serializer. After release, dates in 12 downstream consumers' responses changed from ISO strings to numbers, and about 4% of requests failed to parse (illustrative). Boot's own `ObjectMapper` setup had silently backed off because of `@ConditionalOnMissingBean`, so all of Boot's defaults vanished with it. The team found the cause in minutes by reading the conditions report.

**What the interviewer is really checking**
Whether you know auto-configuration is not magic: it is ordinary configuration classes filtered by conditions. Can you also explain how to override it and how to debug it?

**How I answer it**
1. **Entry point.** `@SpringBootApplication` includes `@EnableAutoConfiguration`. That switch tells Boot to load the candidate list. Without it, nothing is auto-configured.
2. **Read the list.** Boot reads the `.imports` files from every jar on the classpath. Each line names one auto-configuration class.
3. **Evaluate conditions.** Each class is applied only if its conditions pass. `@ConditionalOnClass` checks whether the library is present. `@ConditionalOnProperty` checks your config. `@ConditionalOnMissingBean` checks whether you already defined the bean.
4. **Your beans win.** Auto-configuration is processed after your own configuration, so Boot can see what you defined and back off. This is why you override a default just by declaring your own bean.
5. **Opt out explicitly.** Use `exclude` on `@SpringBootApplication` or the `spring.autoconfigure.exclude` property to switch off a specific class.
6. **See what happened.** Start with `--debug` to print the conditions report. It lists "positive matches" (applied), "negative matches" (skipped, with the failed condition) and exclusions. The Actuator `conditions` endpoint shows the same at runtime, but you must expose it.
7. **Version note.** Boot 4 splits the big `spring-boot-autoconfigure` jar into smaller technology-specific modules, so apps pull in less.

```properties
management.endpoints.web.exposure.include=conditions
```

**Trade-offs and what can go wrong**
- Defining your own bean replaces the whole default, not just the part you wanted to change (the `ObjectMapper` story). Prefer customizer hooks, such as `Jackson2ObjectMapperBuilderCustomizer`, when one exists.
- A transitive jar can switch on something unexpected, such as an embedded database appearing because a driver is on the classpath.
- A typo in a property name makes `@ConditionalOnProperty` fail silently.
- Many auto-configurations add startup time and memory. Exclude what you don't use.
- Expose the `conditions` endpoint only to trusted users, because it reveals your internals.

**How I'd monitor it**
- Run locally or in CI with `--debug` and review the positive and negative matches after dependency upgrades.
- Check `/actuator/conditions` and `/actuator/beans` in a test environment.
- Watch startup time (`application.started.time` metric) for regressions.
- Search logs in Splunk for `CONDITIONS EVALUATION REPORT` if the report is enabled.

**Follow-ups to expect**
- *How do you override an auto-configured bean?* -> Declare your own bean of the same type. `@ConditionalOnMissingBean` makes Boot back off.
- *How do you turn one off?* -> Use `exclude` on `@SpringBootApplication` or `spring.autoconfigure.exclude`.
- *How do you write your own?* -> Write a `@Configuration` class with conditions and list it in an `.imports` file, as a custom starter would.

**60-second answer**
Auto-configuration is Boot setting up beans for you based on what it finds. `@SpringBootApplication` enables it, and Boot reads a list of auto-configuration classes from `AutoConfiguration.imports` files inside the jars. Each class is just a normal configuration class guarded by conditions: `@ConditionalOnClass` checks that the library is on the classpath, `@ConditionalOnProperty` checks a setting, and `@ConditionalOnMissingBean` checks that you haven't defined your own. That last one is why defining your own bean replaces the default. To see what was applied or skipped, I run with `--debug` or use the Actuator `conditions` endpoint. In Boot 4, the large autoconfigure jar is split into smaller technology modules.

### Q6 [mid] Describe the bean lifecycle.
tags: spring, bean-lifecycle, ioc, dependency-injection, beanpostprocessor, aop-proxy, basics

**Start here: the concepts**
- **Bean**: an object that the Spring container creates and manages for you, instead of your code calling `new`. Spring does this so it can wire objects together and add behaviour (transactions, security) around them.
- **Container (ApplicationContext)**: the part of Spring that holds all beans and controls when each is created, wired and destroyed.
- **Dependency injection**: Spring hands a bean the other beans it needs (through the constructor, a setter or a field), so the bean doesn't build them itself.
- **Aware callbacks**: optional interfaces such as `BeanNameAware` and `ApplicationContextAware`. Spring calls them to give the bean information about itself or the container. Most application code never needs them.
- **BeanPostProcessor (BPP)**: a hook that Spring calls for every bean, once before and once after initialization. It can inspect, change or *replace* the bean. Much of Spring's "magic" is built from BPPs.
- **Initialization callbacks**: methods that run once the bean is fully wired. They are `@PostConstruct`, `afterPropertiesSet()` (from `InitializingBean`) and a custom `init-method`.
- **Proxy**: a stand-in object wrapped around your real bean. It intercepts calls to add behaviour such as `@Transactional` or `@Async`. Other beans receive the proxy, not your raw object.
- **Destruction callbacks**: `@PreDestroy`, `DisposableBean.destroy()` and a custom `destroy-method`. They run when the container closes, so the bean can release resources.

**The live scenario**
A payments service has a `@PostConstruct` method that loads 200,000 reference rows into a cache. It takes about 90 seconds in production. The Kubernetes liveness probe starts checking at 60 seconds, so the pod is killed before it finishes and restarts in a loop. A second bug appeared in the same code. The developer called a `@Transactional` method from that `@PostConstruct`, and it ran with no transaction. At that point the proxy didn't exist yet, so the annotation had no effect.

**What the interviewer is really checking**
Whether you know the order of the steps, and whether you can use that order to explain real bugs. The key ones are why proxies appear late, why `@PostConstruct` is a poor place for heavy work, and why annotations sometimes "don't work".

**How I answer it**
1. **Instantiate**: the container calls the constructor and creates a plain, empty object. It must exist before anything can be wired into it.
2. **Inject dependencies**: Spring fills in constructor arguments, setters and `@Autowired` fields, so the bean has its collaborators.
3. **Aware callbacks**: if the bean implements an `Aware` interface, Spring passes it its name, the bean factory or the context.
4. **`BeanPostProcessor.postProcessBeforeInitialization`**: every BPP runs. This is also where `@PostConstruct` is handled, because Spring's annotation processor is itself a BPP. So `@PostConstruct` runs first, then `afterPropertiesSet()`, then any custom `init-method`.
5. **`BeanPostProcessor.postProcessAfterInitialization`**: Spring's AOP BPP wraps the finished bean in a proxy here, so the bean is fully initialized before it is wrapped. This explains the bugs in step 4's `@PostConstruct` call (no proxy yet) and in self-invocation (`this.method()` bypasses the proxy). In the rare case of a circular dependency, the proxy can be created earlier.
6. **Ready**: the singleton bean (the default scope) lives in the container and serves requests.
7. **Destroy**: when the context closes, `@PreDestroy`, then `destroy()`, then the custom `destroy-method` run. Spring Boot registers a JVM shutdown hook for this. Prototype-scoped beans are *not* destroyed by Spring.

**Trade-offs and what can go wrong**
- Heavy work in `@PostConstruct` slows startup and can fail the whole application. Prefer lazy loading, or run it after startup (`ApplicationReadyEvent`) with readiness reporting "not ready".
- Transactions, caching and security are not active inside `@PostConstruct`.
- A `kill -9` or a crash skips `@PreDestroy`, so never rely on it for critical cleanup.
- A custom BPP that forces early creation of other beans can leave those beans un-proxied. Spring logs a warning for this.

**How I'd monitor it**
- Check the "Started X in N seconds" log line, and compare it across releases in Splunk.
- Search Splunk for pod restart and `OOMKilled` or probe-failure events right after deploys.
- Use the Actuator `startup` endpoint, which needs `BufferingApplicationStartup`. It shows which beans take longest to create.
- Use Kubernetes `startupProbe` plus a separate readiness probe, so slow initialization isn't mistaken for a dead app.

**Follow-ups to expect**
- *Why does `@Transactional` fail on self-invocation?* -> The call goes through `this`, which is the raw object, not the proxy. The interceptor never runs.
- *Constructor vs field injection in the lifecycle?* -> Constructor dependencies are required before the object exists. Field injection happens after construction, so the bean can briefly exist half-wired.
- *Does `@PreDestroy` run for prototype beans?* -> No. Spring creates and hands them over, then forgets them, so the caller must clean up.

**60-second answer**
Spring creates the bean with its constructor, then injects its dependencies. It then calls any `Aware` callbacks and runs the BeanPostProcessors' "before" step, which is where `@PostConstruct` runs, followed by `afterPropertiesSet` and any custom init-method. Then the "after" BeanPostProcessors run, and this is where AOP wraps the bean in a proxy for `@Transactional` and similar annotations. After that the bean is ready, and on shutdown `@PreDestroy` runs. Because the proxy appears only at the end, annotations don't work inside `@PostConstruct` or on self-calls. That is why I keep heavy startup work out of `@PostConstruct`.

### Q7 [mid] How does Spring AOP work and what is the self-invocation problem?
tags: spring, aop, proxy, cglib, transactional, self-invocation, basics

**Start here: the concepts**
- **AOP (Aspect-Oriented Programming):** a way to add behaviour such as transactions, caching or logging around many methods without editing each method. The extra behaviour is called **advice**, and the places it applies are chosen by a rule called a **pointcut**.
- **Proxy:** a stand-in object that looks like your bean. Callers talk to the proxy, which runs the advice (for example "begin transaction") and then calls your real object. This is how annotations like `@Transactional`, `@Async` and `@Cacheable` do their work.
- **JDK proxy vs CGLIB proxy:** a JDK proxy is built from an interface, so it only intercepts the interface's methods. CGLIB creates a generated subclass of your class. Spring Boot uses CGLIB by default (`spring.aop.proxy-target-class=true`).
- **Self-invocation:** a method calling another method on `this`, in the same object. `this` is the real object, not the proxy.
- **Weaving:** AspectJ rewrites the bytecode itself, at compile time or class-load time, so no proxy is involved.

**The live scenario**
An order service handles about 2,000 orders per minute. `placeOrder()` calls `this.writeAudit()`, which is marked `@Transactional(REQUIRES_NEW)` so the audit row survives even if the order rolls back. About 3% of orders (roughly 60 per minute) fail validation. Compliance found that none of those failures had audit rows. The audit ran inside the outer transaction and rolled back with it, because the `this.` call never went through the proxy and the annotation was ignored.

**What the interviewer is really checking**
Whether you know that annotations like `@Transactional` work through a proxy and not through magic on the class. They also want to see whether you can predict when the proxy is skipped and name the fixes.

**How I answer it**
1. **Spring wraps the bean in a proxy.** At startup a bean post-processor sees the annotations and replaces the bean in the container with a proxy. Other beans are injected with the proxy, so their calls pass through the advice.
2. **A call from outside goes proxy → advice → real object.** That is when the transaction begins, the cache is checked or the async thread is started.
3. **A call from inside the same class skips the proxy.** Inside `placeOrder()`, `this` is the raw object, so `this.writeAudit()` runs directly and the advice never fires. The same happens with `@Async` (it runs synchronously) and `@Cacheable` (it is never cached).
4. **Fix options, in order of preference:**
   - Move the method to another bean and inject it. This is the cleanest fix.
   - Inject the bean into itself lazily (`@Lazy`) or use `AopContext.currentProxy()` with `exposeProxy=true`. Both work, but they are awkward and couple the class to Spring.
   - Use AspectJ weaving (`@EnableTransactionManagement(mode = ASPECTJ)`), which has no proxy and so no self-invocation gap, but needs a build or agent setup.
5. **Visibility and `final` rules:**
   - `private` methods are never intercepted.
   - Before Spring 6.0, only `public` methods were intercepted. From 6.0, CGLIB proxies also support `protected` and package-visible methods for `@Transactional`.
   - CGLIB cannot subclass a `final` class. A `final` method cannot be overridden, so it is silently not intercepted.
   - Objects created with `new` are not Spring beans and get no proxy at all.

```java
@Transactional(propagation = REQUIRES_NEW)
public void writeAudit(...) { }   // call it from ANOTHER bean
```

**Trade-offs and what can go wrong**
- The failure is silent. Code compiles, runs and passes simple tests, and only the transaction, cache or thread behaviour is wrong.
- Self-injection fixes the symptom but hides a design smell. Usually the method belongs in a separate service.
- AspectJ weaving is more powerful but adds build complexity.
- A JDK proxy can be injected only by interface, and injecting it by concrete class fails.

**How I'd monitor it**
- Write an integration test that forces a failure and asserts the audit row exists.
- In test, set `org.springframework.transaction` logging to DEBUG. If there is no "Creating new transaction" line for the inner method, the proxy was skipped.
- Use `AopUtils.isAopProxy(bean)` to check that a bean is proxied.
- For `@Async`, search Splunk for the thread name. If the log shows `http-nio-…` instead of your async executor, the call ran synchronously.
- For `@Cacheable`, check that Micrometer `cache.gets` hit/miss counters move. If they never appear, the cache is not being called.

**Follow-ups to expect**
- *JDK proxy vs CGLIB?* -> JDK needs an interface and intercepts only interface methods. CGLIB subclasses the class, and Spring Boot defaults to it.
- *Why does `@Transactional` on a private method do nothing?* -> The proxy intercepts by calling an overridable method from outside, and a private method can neither be overridden nor called from outside.
- *Does self-invocation also break `@Async`?* -> Yes. The method runs on the caller's thread because no proxy submits it to the executor.

**60-second answer**
Spring AOP works with proxies. At startup Spring wraps beans that have annotations like `@Transactional`, `@Async` or `@Cacheable` in a proxy, using JDK or CGLIB, and other beans receive the proxy. The proxy runs the extra behaviour, such as starting a transaction, and then calls the real object. The self-invocation problem is that when a method calls another method in the same class, the call goes through `this`, not the proxy, so the annotation is ignored. The best fix is to move the method into another bean. Other options are injecting the bean into itself, using `AopContext.currentProxy()`, or switching to AspectJ weaving. I also remember that private methods are never intercepted, that before Spring 6 only public methods were, and that `final` classes and methods cannot be proxied by CGLIB.

### Q8 [mid] Circular dependency - why does it happen and how to fix?
tags: spring, spring-boot, dependency-injection, circular-dependency, bean-lifecycle, design, basics

**Start here: the concepts**
- **Bean**: an object that Spring creates and manages for you, such as a service or repository.
- **Dependency injection (DI)**: a class declares what it needs, and Spring supplies it instead of the class calling `new`. This keeps classes loosely coupled and easy to test.
- **Constructor injection**: dependencies arrive as constructor parameters. The object cannot exist without them.
- **Setter/field injection**: Spring creates the object first, then fills in its dependencies afterwards.
- **Circular dependency**: A needs B and B needs A, directly or through a longer chain (A→B→C→A). Neither can be fully built before the other.
- **Fail fast**: the app refuses to start when something is wrong, instead of breaking later under user traffic.
- **Proxy**: a stand-in object that forwards calls to the real one. `@Lazy` uses one to delay creating the real bean.
- **Application event**: one bean announces "something happened" and any interested bean reacts. The announcer does not need to know who listens.

**The live scenario**
A team upgrades 14 services from Spring Boot 2.5 to 2.7. Three fail at startup in staging with "The dependencies of some of the beans in the application context form a cycle", and the release is blocked. In one service, `OrderService` and `InventoryService` had used field injection to reference each other for years. Old Boot quietly allowed this. Boot 2.6 turned it off by default.

**What the interviewer is really checking**
Whether you understand why the cycle happens and why the framework now rejects it. They also want to see that you fix the design instead of silencing the error with a flag or `@Lazy`.

**How I answer it**
1. **Explain the cause.** Spring builds beans one by one, and with constructor injection it needs B to create A, and A to create B. Neither can finish first, so Spring throws `BeanCurrentlyInCreationException`. This has always failed for constructor injection. Failing at startup is good because the mistake never reaches production.
2. **Explain why old projects worked.** Setter and field cycles used to be allowed. Spring handed out a half-built singleton (an early reference) to break the loop. Since Boot 2.6, `spring.main.allow-circular-references` is `false` by default, so these now fail too.
3. **Find the real reason for the cycle.** A cycle usually means two classes share a responsibility that belongs somewhere else. Draw the call chain and ask what each side actually needs from the other.
4. **Fix the design, in this order of preference:**
   - Extract the shared logic into a third bean, so both depend on it and not on each other.
   - Use events when A only needs to notify B ("order placed"). This removes the direct dependency.
   - Move a method to the class that owns the data.
5. **Use `@Lazy` only as a last resort.** It injects a proxy and builds the real bean on first use. This hides the cycle without removing it.

```java
public OrderService(@Lazy InventoryService inventory) { ... }
```

6. **Avoid the global flag.** Setting `spring.main.allow-circular-references=true` brings the old behaviour back. Treat it as a short-term bridge during an upgrade, with a ticket to remove it.

**Trade-offs and what can go wrong**
- Extracting a third bean adds a class but gives a clearer design.
- Events decouple the beans, but the flow is harder to trace. Listeners also run synchronously by default, in the caller's thread and transaction, unless you make them async.
- `@Lazy` moves the failure from startup to first use, and the cycle stays in the design.
- Allowing cycles can expose half-initialised beans, and prototype-scoped cycles cannot be resolved at all.
- A common mistake is to switch the flag on and forget it.

**How I'd monitor it**
- Run a context-load test in CI (`@SpringBootTest`) so cycles fail the build, not the deployment.
- Search startup logs in Splunk for `BeanCurrentlyInCreationException` and "form a cycle".
- Alert on Kubernetes pods in CrashLoopBackOff right after a deploy.
- Check `/actuator/env` or `/actuator/configprops` to confirm nobody left `allow-circular-references=true` in production.
- Use ArchUnit rules to catch package-level cycles early.

**Follow-ups to expect**
- *How did Spring resolve setter cycles before 2.6?* -> It exposed an early reference to the half-built singleton so the other bean could be wired. This is why field-injection cycles hid for years.
- *Does `@Lazy` really fix it?* -> No. It only delays creation by using a proxy, so the design problem remains.
- *Why prefer constructor injection?* -> Dependencies are explicit and required, the fields can be `final`, and cycles fail at startup.

**60-second answer**
A circular dependency means bean A needs B and B needs A, so Spring cannot finish creating either one. With constructor injection it fails at startup, which is good because the problem shows up early. Older Spring versions hid setter and field cycles using early references, but Spring Boot 2.6 and later forbid cycles by default. I fix the design by extracting the shared logic into a third bean or by using events when one side only needs to notify the other. I would use `@Lazy` only as a last resort, and I would not turn the allow-circular-references flag on except as a short bridge during an upgrade. I also keep a context-load test in CI so cycles are caught before release.

### Q9 [mid] How do you manage configuration and profiles?
tags: spring-boot, configuration, profiles, configuration-properties, secrets, externalized-config, basics

**Start here: the concepts**
- **Configuration**: values that change between environments but not the code, such as database URL, timeouts and feature switches. Keeping them outside the code lets you build once and deploy the same artifact to dev, test and prod.
- **`application.yml`**: the default config file Spring Boot reads at startup. It holds settings that are the same everywhere.
- **Profile**: a named environment such as `dev` or `prod`. Activating a profile (`spring.profiles.active=prod`) makes Boot also load `application-prod.yml`. Its values override the defaults. `@Profile("prod")` on a bean makes that bean exist only in that profile.
- **Environment variable**: a value set in the operating system or container, e.g. `SPRING_DATASOURCE_URL`. Boot maps it onto the property `spring.datasource.url` (this is called relaxed binding).
- **`@ConfigurationProperties`**: binds a group of properties (e.g. everything under `payment.`) into a typed Java class. You get real types instead of loose strings.
- **`@Validated`**: adds Bean Validation (`@NotBlank`, `@Min`...) to that class so bad config fails at startup. It needs the validation starter on the classpath.
- **Secret**: a password, API key or token. It must not be in Git because Git history is permanent and widely readable.
- **Secret store**: Vault, AWS Secrets Manager or Kubernetes Secrets hold secrets with access control. The app receives them at runtime.

**The live scenario**
A team shipped a payments service to prod on a Friday. The `prod` profile was never activated, so the service started with the default file, which pointed at the dev database. It ran for 40 minutes and about 300 test-quality writes went to the wrong place. A second incident: someone typed `payment.timeout=3O00` (a letter O) in a file, and the service started fine and failed later at the first call. Typed, validated config and an explicit profile would have stopped both at startup.

**What the interviewer is really checking**
Whether you know that config is layered, which layer wins, and that you keep secrets and environment differences out of code. They also want to know whether you make misconfiguration fail fast.

**How I answer it**
1. **Put shared defaults in `application.yml`.** One file holds what is true everywhere, so there is a single place to look.
2. **Add `application-{profile}.yml` for differences only.** Boot loads the profile file on top of the default and the profile values win. Keeping only differences stops files drifting apart.
3. **Override per deployment with environment variables.** They sit above the files, so the same jar can be repointed without a rebuild. This is how containers and Kubernetes are normally configured.
4. **Know the precedence.** Roughly, highest wins: command-line arguments, then environment variables, then profile-specific files, then the default file. Files outside the jar beat files inside it. When a value is surprising, this order explains why.
5. **Bind to typed classes and validate.** Typos and missing values then stop the app at boot instead of causing a failure at 2 a.m.
```java
@ConfigurationProperties("payment") @Validated
public record PaymentProps(@NotBlank String url, @Min(1) int timeoutMs) {}
```
6. **Keep secrets in a secret store, never in Git.** The store controls who can read them and can rotate them. Inject them as environment variables, mounted files or `spring.config.import`.
7. **Set the profile explicitly in the deployment.** For example, set `SPRING_PROFILES_ACTIVE=prod` in the manifest, so it is not left to chance.

**Trade-offs and what can go wrong**
- Too many layers make "where did this value come from?" hard to answer.
- Kubernetes Secrets are only base64-encoded by default, not encrypted. Enable encryption at rest and restrict access.
- Secrets in environment variables can leak through crash dumps or the `/actuator/env` endpoint. Boot masks known sensitive keys, but you should still restrict that endpoint.
- Defaults that point at a real system (like dev DB in the default file) are dangerous. Prefer defaults that fail.
- Heavy use of `@Profile` on beans creates untested code paths per environment.

**How I'd monitor it**
- Check `/actuator/env` and `/actuator/configprops` (secured) to see the active profiles and the winning value for each property.
- Log the active profiles at startup and search for it in Splunk after each deploy.
- Alert if a prod service reports a profile other than `prod`.
- Treat a failed startup from validation as a failed deployment in the pipeline, with the readiness probe never going green.

**Follow-ups to expect**
- *Env var vs profile file, which wins?* -> The environment variable wins, so ops can override a value without rebuilding.
- *Why `@ConfigurationProperties` over `@Value`?* -> It groups related settings, gives type safety and validation, and is easier to test. `@Value` is fine for a single value.
- *How do you change config without restarting?* -> Use a config server with refresh (Spring Cloud) or redeploy. Plain Boot reads config at startup.

**60-second answer**
I keep shared settings in `application.yml` and put only the differences in `application-{profile}.yml`, activating the profile explicitly in the deployment. Environment variables and command-line arguments override the files, so the same jar runs in every environment. The order is command line, then environment variables, then profile file, then the default file. I bind settings into `@ConfigurationProperties` classes with `@Validated`, so a bad value stops the app at startup instead of failing later. Secrets live in Vault, AWS Secrets Manager or Kubernetes Secrets, never in Git, and I remember Kubernetes Secrets need encryption at rest. To prove it in production, I log the active profiles at startup and use secured Actuator endpoints to inspect values.

### Q10 [mid] `@ConfigurationProperties` vs `@Value`?
tags: spring-boot, configuration, configurationproperties, value, property-binding, validation, basics

**Start here: the concepts**
- **Property**: a named setting (like `payment.timeout`) read from `application.yml`, environment variables, command-line arguments, etc. It exists so you change behaviour without changing code.
- **`@Value`**: an annotation that injects one property into one field or constructor parameter, e.g. `@Value("${payment.timeout}")`. `${...}` means "look up this property". `#{...}` means "evaluate a SpEL expression". SpEL is Spring's small expression language, used for calculations or calling beans.
- **`@ConfigurationProperties`**: an annotation on a class that says "bind every property under this prefix into this object". Binding means Spring reads the values, converts them to the field types (numbers, durations, lists), and fills the object.
- **Type-safe**: the value is converted to a real Java type (`Duration`, `int`, `List<String>`), so a bad value fails early instead of being a stray String.
- **Relaxed binding**: `payment.max-retries`, `payment.maxRetries` and env var `PAYMENT_MAXRETRIES` all map to the field `maxRetries`. This helps because the same setting is written differently in YAML and in Kubernetes env vars. `@Value` is much stricter, so use the canonical kebab-case key (`payment.max-retries`).
- **Validation**: with `@Validated` and Bean Validation annotations (`@NotNull`, `@Min`), Spring checks the bound object at startup.

**The live scenario**
A payments service had 14 settings (timeouts, retry counts, URLs, a feature flag) spread across 9 classes via `@Value`. Someone set `PAYMENT_TIMEOUT=30` in production, expecting seconds, but one class parsed it as milliseconds. The service started fine, then 30 ms timeouts caused about 8% of calls to fail during peak traffic. It took 40 minutes to find, because no single place showed all the payment settings. After moving them into one validated `@ConfigurationProperties` class using `Duration`, the same mistake could not happen: `30` is ambiguous, while `30s` is explicit, and bad values stop startup.

**What the interviewer is really checking**
Whether you know when each tool fits, and whether you understand the benefits (grouping, type conversion, validation, fail-fast) rather than just the syntax.

**How I answer it**
1. **Define both in one line each.** `@Value` injects one property. `@ConfigurationProperties` binds a whole prefix into one typed object. This shows you know they solve different scales of the problem.
2. **Use `@ConfigurationProperties` for groups of related settings.** All settings live in one class, so they are easy to find, document and test. In Boot 3+ a record works, and with a single constructor it uses constructor binding automatically, so the object is immutable.
3. **Add validation.** `@Validated` plus constraints makes a missing or invalid setting stop startup. Failing at deploy time is cheaper than failing under traffic.
4. **Mention relaxed binding.** One class works with YAML, env vars and system properties without hand-written name mapping.
5. **Use `@Value` for a genuine one-off**, such as a single flag, a default via `${key:default}`, or a SpEL expression. It is quick, but the setting is scattered and gets no group validation.
6. **Remember to register the class.** Use `@ConfigurationPropertiesScan` or `@EnableConfigurationProperties`; the annotation alone does nothing.

```java
@ConfigurationProperties("payment") @Validated
record PaymentProps(@NotNull Duration timeout, @Min(0) int maxRetries) {}
```

**Trade-offs and what can go wrong**
- Forgetting to register the class means it is never bound (no error, just missing beans).
- `@Value` typos in keys fail only when that bean is created, and there is no IDE help.
- Mutable properties classes with setters can be changed at runtime by accident; prefer records or constructor binding.
- Binding does not refresh on its own when config changes; that needs extra tooling such as Spring Cloud.
- Over-engineering: a class for one flag is overkill.
- Never put secrets in logs when printing properties objects (`toString`).

**How I'd monitor it**
- Startup logs: a `BindValidationException` or "Failed to bind properties" shows exactly which key was wrong.
- Actuator `/actuator/configprops` shows bound values per prefix, and `/actuator/env` shows where each value came from. Both should be secured, and Boot sanitizes sensitive values by default.
- Add the `spring-boot-configuration-processor` so IDEs autocomplete keys and catch typos.
- In Splunk, alert on application startup failures right after a deployment.

**Follow-ups to expect**
- *Does `@ConfigurationProperties` support SpEL?* -> No. Use `@Value` when you need an expression.
- *How do you make the properties object immutable?* -> Use a record or constructor binding (automatic for a single constructor in Boot 3+).
- *How do you handle a missing property in `@Value`?* -> Provide a default with `${key:default}`, otherwise startup fails with an unresolved placeholder error.

**60-second answer**
`@Value` injects one property into one place, and it's fine for a one-off setting or a quick default. `@ConfigurationProperties` binds a whole prefix, like `payment.*`, into a typed object. Because it's typed, a duration is a `Duration`, not a loose string. It also supports relaxed binding, so YAML and environment variable names both work, and it can be validated at startup so bad config stops the deploy instead of causing an outage. In Boot 3 you can write it as an immutable record. I use `@ConfigurationProperties` for any group of related settings and keep `@Value` for rare single values or SpEL. I just need to remember to register the class, for example with `@ConfigurationPropertiesScan`.

### Q11 [mid] What are the Actuator endpoints you rely on?
tags: spring-boot, actuator, micrometer, kubernetes-probes, observability, security, basics

**Start here: the concepts**
- **Actuator**: a Spring Boot module that adds built-in HTTP (and JMX) endpoints to a running app so you can inspect and operate it. It exists so every team doesn't have to build its own health and diagnostics pages.
- **Endpoint**: one operation under `/actuator/...`, such as `health` or `metrics`. Each can be enabled and exposed separately.
- **Health endpoint**: reports UP or DOWN, built from checks such as database, disk and message broker.
- **Liveness vs readiness (Kubernetes probes)**: Kubernetes asks two questions. Liveness asks whether the process is stuck and should be restarted. Readiness asks whether it should receive traffic right now. Boot exposes them as `/actuator/health/liveness` and `/actuator/health/readiness`. They are enabled automatically when Boot detects Kubernetes, or with `management.endpoint.health.probes.enabled=true`.
- **Micrometer and Prometheus**: Micrometer is the metrics library inside Boot (JVM, HTTP, connection pool). Prometheus is a tool that scrapes numbers from `/actuator/prometheus` at intervals. You need the `micrometer-registry-prometheus` dependency for that endpoint.
- **`loggers`**: lists log levels and lets you change one at runtime with a POST. The change is lost on restart.
- **`threaddump` / `heapdump`**: a thread dump shows what every thread is doing right now, which helps with hangs and pool exhaustion. A heap dump is a snapshot of all objects in memory, which helps with memory leaks. It can contain passwords and tokens.
- **`env`**: shows configuration properties and environment variables.
- **`conditions`**: the auto-configuration report. It shows which auto-configurations were applied and which were skipped, and why.
- **`info`**: free-form app details such as build version and git commit.

**The live scenario**
A payments service runs 6 pods. At 2 a.m., latency jumps from 80 ms to 4 s. Readiness fails, so Kubernetes stops sending traffic and the remaining pods get overloaded. The on-call engineer checks `/actuator/metrics/hikaricp.connections.active` and sees it pinned at the pool maximum of 10. A `threaddump` shows many threads waiting on the database. She then raises the `com.zaxxer.hikari` log level to DEBUG through `loggers`, with no restart, and finds one slow query. In the same company, a different team once left `heapdump` and `env` open to the internet, and that was a security incident.

**What the interviewer is really checking**
Whether you have actually operated a service in production, not just listed endpoints. They want to hear which endpoints you use for which problem, and that you know these endpoints are powerful and must be locked down.

**How I answer it**
1. **Health groups for Kubernetes.** I use `health/liveness` and `health/readiness`. Keeping them separate means a slow dependency makes the pod unready (traffic stops) instead of restarting it. I keep external systems such as the database out of liveness, otherwise a database outage restarts every pod and makes things worse.
2. **Metrics through Micrometer and Prometheus.** `metrics` shows one number on demand. `/actuator/prometheus` lets Prometheus collect history for dashboards and alerts. History matters because you need to know what changed, not only the current value.
3. **`loggers` for runtime debugging.** I raise one package to DEBUG during an incident and set it back afterwards. This avoids a redeploy that would hide the problem.
4. **`threaddump` and `heapdump` for hangs and memory leaks.** I take a few thread dumps a few seconds apart to see what is stuck. I use the heap dump only as a last resort.
5. **`env`, `conditions` and `info` for configuration questions.** `env` answers "which profile or property is this pod using?" (a classic wrong-profile bug). `conditions` answers "why was this bean or auto-configuration not created?" `info` shows which build is running.
6. **Secure it.** I expose only what is needed, put actuator on a separate management port so it is never reachable through the public gateway, and require authentication for the sensitive endpoints.

```properties
management.server.port=9090
management.endpoints.web.exposure.include=health,info,prometheus,loggers
```

**Trade-offs and what can go wrong**
- Exposing everything (`include=*`) leaks data. `heapdump` can contain secrets, and `env` can reveal configuration. Boot 3.0 and later masks `env` values by default, while older versions only masked keys that look like passwords or secrets.
- A heap dump can pause the JVM and fill the disk, so avoid taking one on a struggling production pod without care.
- Deep health checks that call slow dependencies can themselves cause timeouts and restarts.
- A runtime log level change is per pod and temporary. People forget to revert it, and DEBUG logging then floods Splunk.

**How I'd monitor it**
- Alert on the Prometheus scrape failing, since a missing `/actuator/prometheus` means the app is probably down.
- Track `hikaricp.connections.active` and `pending`, `jvm.memory.used`, `http.server.requests` (rate, errors, latency percentiles) and `jvm.threads.live`.
- Watch Kubernetes events for probe failures and restart counts.
- Search Splunk for access to `/actuator/*` from unexpected IPs, and for "Changed level" log entries so you can see who changed a log level.

**Follow-ups to expect**
- *How do you secure actuator?* -> Expose only needed endpoints, use a separate management port, and apply Spring Security rules so only an ops role can reach the sensitive ones. Leave only the health probes open to the cluster.
- *Why not put the database in the liveness probe?* -> A database outage would make Kubernetes restart healthy pods, which does not fix the database and adds load. Put it in readiness instead.
- *How do you add a custom health check?* -> Implement a `HealthIndicator` bean that returns UP or DOWN with details, and include it in the right health group.

**60-second answer**
I use `health` with the liveness and readiness groups for Kubernetes. Liveness decides restarts and readiness decides traffic, and I keep the database out of liveness. I use `metrics` and the Prometheus endpoint for dashboards and alerts, and `loggers` to change a log level at runtime during an incident. For hangs I take `threaddump`, and for memory leaks `heapdump`. `env` shows which configuration or profile a pod is using, `conditions` shows why an auto-configuration was or was not applied, and `info` shows the build version. These endpoints are sensitive, so I expose only what I need, run them on a separate management port and require authentication. A heap dump can contain secrets, so I treat it carefully.

### Q12 [mid] How do you handle exceptions globally in a REST app?
tags: spring-boot, exception-handling, rest-api, problemdetail, controlleradvice, error-handling, basics

**Start here: the concepts**
- **Exception:** a Java object thrown when something goes wrong. If no code catches it, it travels up the call stack. In a web app it ends up at the framework, which by default returns a generic error page or JSON.
- **Global exception handling:** one central place that turns exceptions into HTTP responses, instead of `try/catch` in every controller. It exists so every endpoint fails in the same way.
- **`@RestControllerAdvice`:** a Spring class whose methods apply to all controllers. It is a cross-cutting "safety net" around them.
- **`@ExceptionHandler`:** marks a method in that class as the handler for a given exception type. Spring picks the most specific matching handler.
- **`ProblemDetail`:** Spring's built-in class for a standard error body (RFC 7807, since Spring Framework 6 / Boot 3; RFC 9457 now supersedes it with the same shape). Its fields are:
  - `type`: a URI naming the kind of error.
  - `title`: a short summary.
  - `status`: the HTTP code.
  - `detail`: a human-readable explanation.
- **Correlation id:** a unique id for one request, put in the response and the logs, so support can find that request's logs.
- **`MethodArgumentNotValidException`:** thrown when a `@Valid` request body fails validation, such as a blank name or a bad email.

**The live scenario**
A payments API with about 40 endpoints had no global handler. Each team handled errors differently. Some returned HTML, some JSON, and one leaked a SQL error with a table name in a 500 response. Mobile clients could not parse errors, and about 15% of support tickets were "something failed, no idea why". After a central handler with `ProblemDetail` and a correlation id, clients had one error format, and support found the matching logs in minutes.

**What the interviewer is really checking**
Whether you know the mechanism (advice class plus handler methods), whether you design a consistent and safe error contract, and whether you avoid leaking internals.

**How I answer it**
1. **Create one `@RestControllerAdvice` class.** Spring applies it to every controller, so no endpoint needs its own try/catch and all errors look the same.
2. **Return `ProblemDetail` with a stable `type`.** Clients branch on `type` and `status`, not on message text, which may change. A standard format means clients write one parser.
3. **Map validation errors to 400 with field errors.** Handle `MethodArgumentNotValidException`, and add the field-to-message list as an extra property. The client needs to know which field to fix. Field errors are not in the body by default, so you add them.
4. **Map business exceptions to specific codes.** For example, `OrderNotFoundException` becomes 404 and a duplicate becomes 409. The code tells the client whether retrying or fixing the request helps.
5. **Add a catch-all `Exception` handler returning 500.** Log the full stack trace on the server, but return only a generic message and the correlation id. A stack trace, class name or SQL fragment helps attackers.
6. **Add the correlation id to every error body.** Use `setProperty` on the `ProblemDetail`, and reuse the id from your logging context (MDC).

```java
@ExceptionHandler(Exception.class)
ProblemDetail unexpected(Exception e) { log.error("id={}", cid(), e);
  return ProblemDetail.forStatusAndDetail(HttpStatus.INTERNAL_SERVER_ERROR, "Unexpected error"); }
```

**Trade-offs and what can go wrong**
- A catch-all can swallow framework exceptions (405, 415) and turn them into 500s. Extend `ResponseEntityExceptionHandler`, or set `spring.mvc.problemdetails.enabled=true`, so Spring's standard exceptions keep correct codes.
- Spring Security 401/403 errors and exceptions thrown in servlet filters happen before controllers. `@RestControllerAdvice` does not see them, so they need a custom `AuthenticationEntryPoint` and `AccessDeniedHandler`.
- Do not return 200 with an error body, and do not log the same exception at every layer.
- Echoing `e.getMessage()` in `detail` can leak internals.

**How I'd monitor it**
- Track the rate of 4xx and 5xx responses per endpoint with Micrometer (`http.server.requests` by `status`). Alert on a 5xx spike.
- In Splunk, search by correlation id, or for `level=ERROR` grouped by exception class, to find the top recurring failures.
- A sudden rise in 400s after a release often means a client or contract change.

**Follow-ups to expect**
- *Why not try/catch in each controller?* -> It duplicates code, produces inconsistent responses, and some methods get forgotten.
- *Does `@RestControllerAdvice` catch exceptions from filters?* -> No. Filters run outside the controller layer, so you handle them in the filter or in Spring Security handlers.
- *Where does the correlation id come from?* -> A filter reads it from an incoming header or generates one, and puts it in MDC and the response.

**60-second answer**
I put all error handling in one `@RestControllerAdvice` class, so every endpoint fails in the same way. Each `@ExceptionHandler` method maps an exception to an HTTP status and returns a `ProblemDetail`, the standard error format built into Spring 6. It has a stable `type`, a `title`, the `status`, a `detail`, and a correlation id. Validation failures become a 400 listing the bad fields. Business errors get specific codes like 404 or 409. Anything unexpected becomes a 500 with a generic message, while the full stack trace goes only to the logs, so nothing internal leaks. I watch 5xx rates in Micrometer and use the correlation id to find the matching logs in Splunk.

### Q13 [mid] How does bean validation work?
tags: spring, spring-boot, bean-validation, hibernate-validator, rest-api, dto, basics

**Start here: the concepts**
- **Validation**: checking that incoming data follows the rules (required, right length, valid format) before the code uses it. It exists so bad data is rejected early with a clear message, instead of causing a crash or corrupt data later.
- **Bean Validation**: a standard Java specification (package `jakarta.validation` in Spring Boot 3, `javax.validation` in Boot 2) that lets you declare rules as annotations on fields. Hibernate Validator is the implementation Spring Boot uses. It has nothing to do with the Hibernate ORM.
- **Constraint annotation**: a rule attached to a field, such as `@NotNull`, `@NotBlank`, `@Size`, `@Email`, `@Min`.
- **DTO (Data Transfer Object)**: a simple class or record that carries the request body into your controller. It is the natural place to put the rules.
- **`@Valid`**: put on a parameter, it tells Spring to run the rules on that object before your method body runs.
- **`@Validated`**: Spring's own annotation. On a class, it makes Spring wrap the bean in a proxy (a stand-in object that intercepts calls) so method parameters and return values are checked. It also supports **validation groups**, which are named subsets of rules, for example "on create" and "on update".
- **Custom constraint**: your own annotation plus a validator class, for rules the built-ins cannot express.

**The live scenario**
An orders API handles about 5,000 requests a minute. It had no validation, and a client sent `quantity = -3` and a missing `customerId`. Around 2% of requests ended as HTTP 500 from a `NullPointerException`. A few negative-quantity orders were saved and produced wrong invoices. The team added constraints on the DTO and `@Valid` on the controller. Bad requests now get a 400 with a clear message, and the 500s and bad rows stopped.

**What the interviewer is really checking**
Whether you know where validation runs, the difference between `@Valid` and `@Validated`, and that validation at the API edge does not replace protecting domain rules.

**How I answer it**
1. **Add the starter and annotate the DTO.** In Boot 2.3 and later, `spring-boot-starter-validation` is not included in the web starter, so it must be added. Rules go on the fields:
   ```java
   record CreateOrder(@NotBlank String customerId, @Min(1) int qty, @Email String email) {}
   // controller: create(@Valid @RequestBody CreateOrder body)
   ```
2. **Put `@Valid` on the controller parameter.** Spring runs the validator before your method. If a rule fails, the method never runs. For `@RequestBody` Spring throws `MethodArgumentNotValidException`, which becomes a 400.
3. **Use `@Validated` for method-level checks and groups.** On a service class, it creates a proxy that validates parameters when the method is called. Because it is proxy-based, calling the method from another method in the same class (self-invocation) skips validation. Groups are chosen through `@Validated`, since `@Valid` cannot select a group.
4. **Write a custom constraint when needed.** Create an annotation and a `ConstraintValidator`, for example for an "order code format" rule that spans several fields.
5. **Validate at the boundary and again in the domain.** The boundary check gives fast, friendly 400s. The domain check (constructor or service) protects invariants when data arrives from Kafka, batch jobs or other code that never passed the controller.
6. **Translate errors in one place.** A `@RestControllerAdvice` returns a consistent error body listing the failing fields.

**Trade-offs and what can go wrong**
- `@Size` and `@Email` treat `null` as valid. Combine them with `@NotNull`, or use `@NotBlank` for strings.
- Forgetting `@Valid` means silently no validation.
- `@Valid` on a nested object field is needed for the rules inside it to run (cascading).
- Self-invocation or `private` methods bypass `@Validated` proxies.
- Format rules at the edge are not business rules. "Does this customer exist?" belongs in the service.
- Spring 6.1 and later adds built-in method validation for controllers, which can throw `HandlerMethodValidationException` instead. Handle both exceptions.
- Do not echo sensitive values back in error messages.

**How I'd monitor it**
- Micrometer's `http.server.requests` metric, filtered to status 400 per endpoint. A sudden spike means a broken client or a release that changed a rule.
- A Splunk search for `MethodArgumentNotValidException` grouped by field name, logging field names only, not values.
- An alert when 400s exceed a baseline, and a check that 500s from `NullPointerException` stay near zero.

**Follow-ups to expect**
- *@Valid vs @Validated?* -> `@Valid` is the standard annotation that triggers validation and cascades into nested objects. `@Validated` is Spring's, adds group selection, and enables method-level validation on proxied beans.
- *@NotNull vs @NotEmpty vs @NotBlank?* -> `@NotNull` rejects only null. `@NotEmpty` also rejects empty strings or collections. `@NotBlank` also rejects whitespace-only strings.
- *How do you return clean errors?* -> Handle the exception in a `@RestControllerAdvice` and return a 400 with the field and message, for example as a `ProblemDetail`.

**60-second answer**
Bean validation lets me declare rules as annotations like `@NotBlank`, `@Size` and `@Email` on a DTO. I add `@Valid` to the controller parameter, and Spring runs the Hibernate Validator before my method, returning a 400 if a rule fails. For service methods and validation groups I use `@Validated` on the class, which works through a proxy, so self-invocation skips it. For special rules I write a custom constraint. I validate at the API boundary for fast feedback and again in the domain, because Kafka consumers and batch jobs never touch the controller. I watch the 400 rate and validation exceptions in logs to catch bad clients early.

### Q14 [mid] What is the difference between `RestTemplate`, `WebClient`, `RestClient`, and HTTP interfaces?
tags: spring, rest-client, restclient, webclient, http-interface, timeouts, basics

**Start here: the concepts**
- **HTTP client:** code that calls another service's REST API (send a request, read the response). Almost every microservice needs one.
- **Blocking:** the calling thread waits, doing nothing, until the response arrives. Simple to write and debug, but each in-flight call holds one thread.
- **Non-blocking / reactive:** the thread starts the call and moves on. A callback or a stream (`Mono`/`Flux`) delivers the result later. It handles many slow calls with few threads, but you must write in the reactive style.
- **Fluent API:** calls chained like `client.get().uri(...).retrieve().body(...)`, which reads like a sentence.
- **Maintenance mode:** the class still works and gets bug fixes, but gets no new features. The Spring team points people to newer options.
- **HTTP interface client:** you write a Java interface, annotate the methods (`@GetExchange`, `@PostExchange`), and Spring generates the implementation at runtime. It is similar to Feign.
- **Timeout:** the maximum time to wait. The *connect* timeout covers opening the connection. The *read* timeout covers waiting for response data.

**The live scenario**
An orders service handles about 300 requests/second and calls a pricing service on every request. Pricing has a bad deploy and starts answering in 60+ seconds instead of 50 ms. The orders service's `RestTemplate` had no read timeout, so threads waited indefinitely. In about 40 seconds all 200 Tomcat threads were stuck, and the orders service stopped answering even its health checks. Kubernetes restarted the pods, which made things worse. The fix was a 2 s read timeout and a move to `RestClient`. Choosing the client matters less than configuring it safely.

**What the interviewer is really checking**
Whether you know which client to pick for new code and why (blocking vs reactive). Also whether you know these are different layers, and whether you remember timeouts.

**How I answer it**
1. **`RestTemplate`:** blocking, template-style, in maintenance mode. It is everywhere in old code, so you must read it, but I would not start new code with it. The Spring team has signalled it will be deprecated in later versions.
2. **`WebClient`:** non-blocking and reactive, part of `spring-webflux`. I use it when the app is already reactive or I need streaming or many parallel calls. It can be forced to block with `.block()`, but then you pay the reactive complexity for no benefit.
3. **`RestClient`** (Spring Framework 6.1, Boot 3.2): a modern blocking client with the fluent style of `WebClient`. It is the default choice for new code in a normal servlet app, and the successor to `RestTemplate`. With virtual threads (Java 21), blocking calls are cheap, which makes this choice even stronger.
4. **HTTP interfaces:** these are a layer on top, not a fourth transport. You declare an interface, and Spring generates it by delegating to `RestClient`, `WebClient` or `RestTemplate`. This removes repetitive call code and makes mocking easy. Boot 4 / Framework 7 adds `@ImportHttpServices` to register them with little configuration.
5. **Always set timeouts.** Without them, a slow dependency can consume all your threads (see the scenario). In Boot 3.4+ you can set them globally:
```properties
spring.http.client.connect-timeout=1s
spring.http.client.read-timeout=2s
```

**Trade-offs and what can go wrong**
- `WebClient` has a learning curve, and a hidden `.block()` on an event-loop thread can freeze the app.
- Build clients from the Spring-provided builder (`RestClient.Builder`), not `new`, so metrics and tracing are attached.
- Timeouts that are too short cause false failures. Combine them with retries (only for idempotent calls) and a circuit breaker.
- Mixing several clients in one codebase makes error handling inconsistent.
- Boot 4 specifics may differ by milestone or release, so check the reference docs for your exact version.

**How I'd monitor it**
- Micrometer's `http.client.requests` metric (count, latency, status, URI) via Actuator, with alerts on p99 latency and error rate.
- Thread-pool saturation: `tomcat.threads.busy` against the configured maximum.
- Splunk search for `SocketTimeoutException` or `ResourceAccessException` by target service.
- Circuit-breaker state, if one is used.

**Follow-ups to expect**
- *Can I still use `WebClient` in a Spring MVC app?* -> Yes, if you include `spring-webflux`. It is useful for parallel calls, but for simple sequential calls `RestClient` is simpler.
- *How do HTTP interfaces relate to Feign?* -> They are similar declarative clients, but built into Spring and powered by the standard clients, with no extra library.
- *How do you migrate from `RestTemplate`?* -> Use `RestClient.create(restTemplate)` to reuse its configuration, then migrate call by call.

**60-second answer**
`RestTemplate` is the old blocking client, now in maintenance mode, so I only meet it in legacy code. `WebClient` is the reactive, non-blocking one, and I use it when the app is reactive or needs streaming. `RestClient`, from Spring 6.1, is the modern blocking client with a fluent API, and it is my default for new servlet-style services. HTTP interfaces sit on top of these: I declare an interface with `@GetExchange`, and Spring generates the client. Boot 4 adds `@ImportHttpServices` to register them easily. Whatever I choose, I always set connect and read timeouts, because a missing timeout once let a slow dependency use up all our threads.

### Q15 [senior] How would you migrate Spring Boot 2.x to 3.x/4.x?
tags: spring-boot, migration, jakarta-ee, hibernate-6, spring-security, openrewrite, basics

**Start here: the concepts**
- **Major upgrade:** Boot 3 is built on Spring Framework 6 and Boot 4 on Spring Framework 7. Old APIs are removed, not just deprecated, so code that compiled yesterday can fail to compile or start.
- **Deprecation:** a warning that an API will be removed. Fixing deprecations while still on the old version means the real upgrade has far less to change.
- **Spring Boot 2.7 (last 2.x):** it already contains most replacements for things Boot 3 removes. It is the safest launch point.
- **Java 17 baseline:** Boot 3 needs at least Java 17, and Boot 4 also builds on it. Older Java will not run.
- **`javax.*` to `jakarta.*`:** Java EE moved to the Eclipse Foundation, which could not reuse the `javax` name. Packages such as `javax.persistence` and `javax.servlet` became `jakarta.persistence` and `jakarta.servlet`. Every import, and every library that uses them, must match.
- **OpenRewrite:** a tool that applies automated, rule-based code edits (imports, properties, dependencies). It does the mechanical 80%.
- **Hibernate 6:** the JPA engine behind Spring Data JPA, version 6 in Boot 3. It has a stricter query parser (HQL) and different default ID (primary key) generation.
- **`WebSecurityConfigurerAdapter`:** the old base class for Spring Security config. It is removed in Spring Security 6, so you declare a `SecurityFilterChain` bean instead, using the lambda DSL (configuration written as lambdas such as `auth -> auth...`).
- **Migration guide:** the official release-notes page for each version listing removed, renamed and changed behaviour.

**The live scenario**
A payments platform runs 40 services on Boot 2.5 and Java 8, and security scanners flag unsupported versions. A team that jumped one service straight to 3.x got 1,800 compile errors from `javax` imports, a startup crash from a missing `WebSecurityConfigurerAdapter`, and wrong ID values in staging. They lost three weeks. A second team went 2.7, then Java 17, then Jakarta, then 3.x in small steps, with tests after each. They finished in four days per service, and each failure pointed to exactly one change.

**What the interviewer is really checking**
Whether you treat the upgrade as a sequence of small, testable hops that separates causes, and whether you know the real breaking points (Java, Jakarta, Hibernate, Security) rather than just "bump the version".

**How I answer it**
1. **Upgrade to the latest 2.7.x first.** Its deprecation warnings and replacements show what Boot 3 will remove. Jumping from older 2.x mixes old and new problems.
2. **Fix deprecations on 2.7**, including moving to a `SecurityFilterChain` bean. That is available from Spring Security 5.7, so you can do it before the big jump.
3. **Move to Java 17 while still on 2.7.** Boot 2.7 runs on 17, so any failure is a Java problem, not a Boot problem.
4. **Convert `javax.*` to `jakarta.*` with OpenRewrite**, then review the diff. Boot 3 will not run with `javax` servlet or JPA classes.
5. **Check every third-party library** (Hibernate Validator, JWT, Swagger/OpenAPI, Kafka or Couchbase starters, internal shared jars) for a Jakarta-compatible version. One old jar breaks startup.
6. **Handle Hibernate 6.** Rewrite sloppy HQL/JPQL. Verify ID generation: sequence/identity defaults changed, so a wrong strategy can produce duplicate-key errors or gaps against existing tables.
7. **Finish Spring Security.** `WebSecurityConfigurerAdapter` is gone in version 6, so use the lambda style:
```java
@Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
  return http.authorizeHttpRequests(a -> a.anyRequest().authenticated()).build();
}
```
8. **Upgrade to the latest 3.5.x**, run all integration tests, and deploy it. This is a stable stopping point.
9. **Then go to 4.x with its migration guide**, reading the removed APIs, the Spring Framework 7 changes and any changes to dependencies such as JSON handling. Again, run integration tests after each hop.

**Trade-offs and what can go wrong**
- Small hops cost more pipeline runs but isolate failures. A big-bang jump is faster only if it works.
- Unit tests with mocks miss Jakarta, Hibernate and security problems. You need integration tests against a real database and real security rules.
- Silent changes are the dangerous ones: ID generation, trailing-slash URL matching, renamed properties, and observability (Sleuth replaced by Micrometer Tracing).
- Shared internal libraries must be migrated first, or every service blocks.

**How I'd monitor it**
- Compare before and after on a canary: error rate, p95 latency, heap, startup time, and connection-pool use through Actuator/Micrometer.
- Search Splunk for `ClassNotFoundException`, `NoSuchMethodError`, `jakarta`, `javax`, `BeanCreationException` and `ConstraintViolation` after deploy.
- Use `spring-boot-properties-migrator` temporarily to catch renamed config.
- Alert on database duplicate-key errors, which show ID-strategy mistakes.

**Follow-ups to expect**
- *Why not jump straight to 3.x?* -> You could not tell whether a failure came from Java, Jakarta, Hibernate or Security.
- *Can you automate it?* -> Yes. OpenRewrite handles imports, properties and dependencies, but the output needs review and tests.
- *What if a library has no Jakarta version?* -> Look for a newer fork, replace it, or isolate it behind an adapter. Do not ship a mix of `javax` and `jakarta`.

**60-second answer**
I upgrade in small steps so each failure has one cause. First I go to the latest 2.7 and fix deprecations, including replacing `WebSecurityConfigurerAdapter` with a `SecurityFilterChain` bean. I move to Java 17 while still on 2.7. Then I convert `javax` to `jakarta` with OpenRewrite and check that every third-party library has a Jakarta version. Next I deal with Hibernate 6: stricter queries and different ID generation. Then I go to the latest 3.5, then to 4.x using the migration guide. After every hop I run integration tests, and I canary-deploy while watching errors in Splunk and Micrometer metrics.

### Q16 [senior] Spring MVC request flow end to end?
tags: spring-mvc, dispatcherservlet, request-flow, interceptors, controlleradvice, filters, basics

**Start here: the concepts**
- **Servlet container**: the web server part (Tomcat, embedded in Spring Boot by default). It accepts HTTP connections, turns each request into a Java request object, and hands it to a servlet.
- **Filter**: code that runs in the container *before* the servlet and knows nothing about Spring MVC. Spring Security is built from filters.
- **`DispatcherServlet`**: the single "front controller" servlet of Spring MVC. Every request enters through it, and it coordinates the rest. One entry point means cross-cutting behaviour lives in one place.
- **`HandlerMapping`**: a lookup table from "URL + HTTP method" to a *handler*, usually a controller method. It returns the handler together with its interceptors.
- **`HandlerAdapter`**: the component that actually calls the handler. `DispatcherServlet` doesn't know how to call every handler type, so adapters do it.
- **Interceptor (`HandlerInterceptor`)**: Spring-aware hooks around the handler call: `preHandle`, `postHandle`, `afterCompletion`.
- **Argument resolvers**: build each controller parameter (`@PathVariable`, `@RequestBody`, and so on).
- **`HttpMessageConverter`**: converts between HTTP body bytes and Java objects (for example JSON via Jackson). It reads the request and writes the response.
- **Validation**: `@Valid` checks the object against rules such as `@NotNull`. It runs while arguments are built.
- **`HandlerExceptionResolver` / `@ControllerAdvice`**: the central place that turns exceptions into HTTP responses.

**The live scenario**
An orders API handles about 300 requests/s. A developer added an interceptor that sets an `X-Request-Id` header in `postHandle`. The header was present on HTML pages but missing on every JSON endpoint, so support couldn't trace customer errors. The cause is the flow: for `@RestController` methods the body is written *during* the handler call, before `postHandle`, so headers set afterwards may be ignored. Moving the code to `preHandle` (or a filter) fixed it.

**What the interviewer is really checking**
Whether you know the *order* of components and which layer owns what (filter vs interceptor vs advice), not just the names. They also want to know whether you can reason about where a bug like the one above lives.

**How I answer it**
1. **Container and filters first.** Tomcat receives the request and runs the filter chain (security, encoding, and so on). Filters run first because they work at the raw servlet level and can reject a request before Spring is involved.
2. **`DispatcherServlet` receives it.** It is the single entry point, so every request follows the same pipeline.
3. **`HandlerMapping` picks the handler.** It matches URL and method to a controller method and returns it with its interceptor chain. If nothing matches, the result is a 404.
4. **Interceptors `preHandle` run.** This is good for auth checks, request IDs and timing. If one returns `false`, the chain stops and the controller is never called.
5. **`HandlerAdapter` invokes the method.** It builds the arguments: it reads the JSON body through an `HttpMessageConverter`, binds path and query values, and runs `@Valid`. Bad input fails here, before your code runs.
6. **The controller runs.** It holds business logic only.
7. **The return value is written.** For `@ResponseBody`/`@RestController`, a return value handler uses a converter to turn the object into JSON and writes it straight to the response. For view-based apps, a `ViewResolver` and view render the page instead.
8. **`postHandle`, then `afterCompletion`.** `postHandle` runs after the handler succeeds, but it cannot change an already-written JSON body. `afterCompletion` runs at the end whether or not there was an exception (as long as `preHandle` passed), so use it for cleanup and timing.
9. **Exceptions** thrown in steps 4–7 go to `HandlerExceptionResolver` beans, including the `@ControllerAdvice`/`@ExceptionHandler` mechanism, which produces the error response. `postHandle` is skipped in that case.

**Trade-offs and what can go wrong**
- Putting response-modifying logic in `postHandle` on REST endpoints silently fails (see the scenario).
- Exceptions thrown in filters never reach `@ControllerAdvice`, because they happen before `DispatcherServlet`.
- Heavy work in `preHandle` slows every request.
- Forgetting to clear a `ThreadLocal` set in an interceptor leaks data between requests on pooled threads. Clear it in `afterCompletion`.

**How I'd monitor it**
- Actuator and Micrometer: `http.server.requests`, broken down by `uri`, `status` and `exception`, to watch latency and error rates per endpoint.
- Splunk: search for `status=500` grouped by exception class and request ID, and check that the request ID appears on every response.
- Alert on p99 latency and 4xx spikes (validation failures often mean a client released a bad payload).

**Follow-ups to expect**
- *Filter vs interceptor?* -> Filters are servlet-level, run before `DispatcherServlet` and see raw requests. Interceptors are Spring-level, know the matched handler, and only cover requests going through MVC.
- *Where does `@ControllerAdvice` fit?* -> It is consulted by the exception resolvers when the handler or argument processing throws. It doesn't cover filter exceptions.
- *What does `HandlerAdapter` add?* -> It lets the dispatcher call different handler types uniformly. `RequestMappingHandlerAdapter` handles `@RequestMapping` methods, including argument resolution and return handling.

**60-second answer**
A request reaches the servlet container, such as Tomcat, and passes through the filters first. Then `DispatcherServlet`, Spring MVC's single front door, asks `HandlerMapping` which controller method matches. Interceptors' `preHandle` run next, and a `false` return stops the request. The `HandlerAdapter` then builds the method arguments, converting JSON to objects with `HttpMessageConverter` and validating them, and calls the controller. For REST, the return value is converted back to JSON and written to the response immediately, so `postHandle` can't change it. `afterCompletion` always runs at the end for cleanup. Exceptions go to the exception resolvers and `@ControllerAdvice`, but filter exceptions don't.

### Q17 [senior] Filter vs Interceptor vs AOP?
tags: spring, spring-boot, servlet-filter, handler-interceptor, aop, basics

**Start here: the concepts**
- **Servlet container:** Tomcat (or Jetty/Undertow) is the server that accepts HTTP requests and hands them to Java code. Everything below sits inside it.
- **Filter:** a piece of code from the Servlet standard (`jakarta.servlet.Filter` in Spring Boot 3, `javax.servlet` before). The container runs it before the request reaches Spring MVC and again as the response leaves. It sees only the raw request and response: URL, headers, body stream. It exists so cross-cutting work (security, encoding, CORS) can happen for every request, whatever framework is behind it.
- **DispatcherServlet:** Spring MVC's front door. It picks the controller method (the *handler*) for each request.
- **Interceptor (`HandlerInterceptor`):** a Spring MVC hook that runs *after* the DispatcherServlet has chosen the handler. It has `preHandle` (before the controller), `postHandle` (after the controller, before the view is rendered) and `afterCompletion` (always, even after an error). It knows which controller method will run.
- **AOP (Aspect-Oriented Programming):** a way to attach behaviour ("advice") to method calls on Spring beans without editing those methods. Spring does it with *proxies*: a wrapper object that stands in for your bean, runs the advice, then calls the real method. `@Transactional` works this way.
- **Cross-cutting concern:** work needed in many places that is not business logic, such as logging, security and timing.

**The live scenario**
An orders API takes about 2,000 requests per second. Support could not trace a failed checkout across 12 services. The team added a correlation-id **filter**, and it covered even requests that security rejected with 401, because filters run before everything else. They then wanted latency per endpoint, which needed the controller method name, so they used an **interceptor**. For an audit trail on `PaymentService.refund()`, they used an **aspect**. The first audit version missed refunds triggered from another method in the same class (about 3% of refunds in this illustration). Self-invocation bypasses the proxy, so the advice never ran.

**What the interviewer is really checking**
Whether you know where each mechanism sits in the request path, what information it has there, and the proxy limits of AOP. A senior answer also names Spring Security as a filter chain.

**How I answer it**
1. **Draw the order:** Container → Filters → DispatcherServlet → Interceptors → Controller → Service beans (AOP proxies). Everything else follows from where each one sits.
2. **Filter for raw HTTP concerns that apply to everything:** security, CORS, request/correlation ids, compression. Spring Security is itself a filter chain. Filters run before MVC, so they can reject or wrap a request early. Reading the body needs a wrapper (such as `ContentCachingRequestWrapper`) because the stream can be read only once.
3. **Interceptor when you need the handler:** per-endpoint metrics, checking a custom annotation on the controller method, and request-scoped setup or cleanup in `afterCompletion`. It only sees requests that reached Spring MVC.
4. **AOP when the concern belongs to a method, not to HTTP:** transactions, auditing, retries and metrics on service methods. It works for any Spring-managed bean, including ones never called from a web request (Kafka listeners, schedulers).
5. **Pick the narrowest level that has the information you need.** Don't use a filter to guess the controller method, and don't use AOP to read HTTP headers. A wider level is blunt, and a narrower one may not see the request at all.
6. **Know AOP's mechanism limits:** only calls that go through the proxy are intercepted. Self-invocation (`this.foo()`), `private` methods, `final` classes and objects made with `new` are not advised.

**Trade-offs and what can go wrong**
- Filter order matters. A logging filter placed after the security filter never sees rejected requests.
- Exceptions thrown in a filter do not reach `@ControllerAdvice`, because that is MVC-level. Exceptions in interceptors and controllers do.
- `postHandle` is skipped if the handler throws, so put cleanup in `afterCompletion`.
- Aspects hide behaviour, which makes debugging harder. Broad pointcuts add overhead and surprises.
- Reading the body in a filter without caching it breaks the controller.

**How I'd monitor it**
- Micrometer timers (`http.server.requests`) tagged by URI and method. Compare the filter-level total against the handler-level time to see where time goes.
- Splunk: search by correlation id across services. Alert when the share of log lines without an id rises.
- A test or log counter confirming an aspect fires, to catch silent proxy bypass.
- Debug logging on filter-chain order at startup.

**Follow-ups to expect**
- *Why did my @Transactional or audit aspect not run?* -> The call went through `this` or a private method, so it bypassed the proxy. Move the method to another bean or inject the proxy.
- *Where does Spring Security sit?* -> In a servlet filter chain (`FilterChainProxy`), before the DispatcherServlet. That is why `@ControllerAdvice` cannot handle its 401s directly.
- *Filter vs interceptor for logging the request body?* -> A filter with a caching wrapper, since the interceptor sees a stream that may already be consumed.

**60-second answer**
A request passes through three layers. Filters belong to the servlet container and run first. They see only raw HTTP, so I use them for security, CORS and correlation ids. Interceptors belong to Spring MVC and run after Spring picks the controller method, so I use them when I need to know which handler runs, for example per-endpoint metrics. AOP works on Spring bean methods through proxies, so it suits transactions, auditing and metrics on services. It does not see HTTP and it misses self-invocation and private methods. My rule is to use the narrowest level that has the information I need. I check it with tagged Micrometer timers and by tracing correlation ids in Splunk.

### Q18 [senior] How do you do graceful shutdown and health probes on Kubernetes?
tags: spring-boot, kubernetes, graceful-shutdown, actuator, health-probes, readiness-liveness, basics

**Start here: the concepts**
- **Graceful shutdown:** when the app is told to stop, it stops taking new requests but lets the ones already running finish, up to a time limit. Without it, a deploy cuts live requests mid-way and users see errors.
- **SIGTERM:** the polite "please stop" signal Kubernetes sends to a container. If the process is still alive after the grace period, Kubernetes sends SIGKILL, which kills it instantly.
- **Readiness probe:** a check Kubernetes runs to ask "can this pod take traffic right now?" If not, the pod is taken out of the load-balancing list, but it is not restarted.
- **Liveness probe:** a check that asks "is this process stuck beyond repair?" If it fails repeatedly, Kubernetes restarts the container.
- **Startup probe:** holds off the other probes until a slow-starting app has booted, so it is not killed while starting.
- **preStop hook:** a command Kubernetes runs *before* sending SIGTERM. It is commonly used to just sleep for a few seconds.
- **terminationGracePeriodSeconds:** the total time Kubernetes gives a pod to shut down (default 30s) before SIGKILL. It covers the preStop hook *and* the app's own shutdown.

**The live scenario**
An order service runs 6 pods at about 800 requests/second. Every rolling deploy produced a burst of roughly 150 HTTP 502/503 errors over 10 seconds, and some payments were cut mid-request. The cause was that old pods began shutting down while the load balancer was still sending them traffic. After enabling graceful shutdown, adding a 5s preStop sleep and sizing the grace period correctly, deploys produced zero errors.

**What the interviewer is really checking**
Whether you understand the timing race between "pod gets SIGTERM" and "load balancer stops routing to it", and whether you know liveness and readiness have different jobs.

**How I answer it**
1. **Enable graceful shutdown in Spring Boot.** Set `server.shutdown=graceful` and `spring.lifecycle.timeout-per-shutdown-phase=30s`. On SIGTERM the web server stops accepting new requests, in-flight ones get up to 30s to finish, and only then are beans (connection pools, Kafka consumers) destroyed. This way, work in progress is not cut off.
2. **Expose probe endpoints.** Spring Boot's actuator has liveness and readiness health groups (`/actuator/health/liveness` and `/readiness`), switched on automatically when it detects Kubernetes or via `management.endpoint.health.probes.enabled=true`. During shutdown, readiness reports "refusing traffic".
3. **Add a preStop sleep of about 5s.** Removing a pod from the load balancer is asynchronous: Kubernetes updates the endpoint list, and proxies and ingress controllers pick it up a moment later. SIGTERM and that removal start at about the same time, so the app may stop accepting requests while some traffic is still arriving. The sleep keeps the app fully serving during that window.
4. **Size the grace period for the whole sequence.** `terminationGracePeriodSeconds` must be greater than preStop time **plus** the shutdown timeout (5 + 30 = 35, so use about 45). Otherwise Kubernetes sends SIGKILL in the middle of your graceful drain. The stored shorthand of "greater than the timeout" understates this.
5. **Keep liveness local.** Liveness should only say whether the JVM itself is healthy. If it checks the database and the database blips, Kubernetes restarts every pod at once and turns a small outage into a big one. Downstream checks, if any, belong in readiness, and only for dependencies without which the pod is useless.

```yaml
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
# pod spec: preStop sleep 5, terminationGracePeriodSeconds: 45
```

**Trade-offs and what can go wrong**
- Longer grace periods make deploys and scale-downs slower.
- Requests longer than the timeout are still killed, so long jobs need to be made resumable or moved to a queue.
- The `sleep` preStop needs a `sleep` binary in the image (minimal images may lack it).
- Readiness that checks a shared dependency can drop *all* pods from traffic at once.
- Too-aggressive liveness timeouts cause restart loops during GC pauses or slow startup. Use a startup probe instead.
- Background consumers (Kafka, schedulers) also need clean stopping, or they may reprocess messages.

**How I'd monitor it**
- During deploys, track 5xx rate at the ingress or load balancer, which should stay flat.
- Watch pod restarts and `OOMKilled` or `Error` exit codes (exit code 137 means SIGKILL, so the grace period was too short).
- Search Splunk for shutdown logs and "Commencing graceful shutdown" versus "Graceful shutdown aborted/timed out" messages.
- Alert on rising liveness failures, and compare probe failures with deploy times.
- Micrometer metrics such as in-flight requests and connection pool usage show whether the drain completes.

**Follow-ups to expect**
- *Why is the preStop sleep needed if readiness already flips?* -> Readiness changes only after SIGTERM, and endpoint removal races with it. The sleep gives the load balancer time to stop sending traffic.
- *What goes in readiness versus liveness?* -> Liveness: only internal process health. Readiness: can I serve right now, including critical dependencies and the shutdown state.
- *What if the pod is killed before draining finishes?* -> The grace period is too short, or requests outlast the timeout. Raise the grace period, shorten requests, or make the work retryable and idempotent.

**60-second answer**
I turn on `server.shutdown=graceful` with a 30-second shutdown timeout, so on SIGTERM Spring stops taking new requests, lets running ones finish, and then closes beans. I expose Actuator's liveness and readiness probes, and readiness goes to "refusing traffic" during shutdown. Because Kubernetes removes the pod from the load balancer at the same time as sending SIGTERM, I add a preStop sleep of about 5 seconds so traffic stops arriving before the app stops listening. I set `terminationGracePeriodSeconds` higher than the preStop plus the shutdown timeout, say 45 seconds, so Kubernetes does not SIGKILL us mid-drain. I keep liveness purely internal, because a database blip that fails liveness would restart every pod together. I verify with a flat 5xx rate during rolling deploys.

### Q19 [senior] What are common Spring Boot startup/memory problems and fixes?
tags: spring-boot, startup-time, memory, auto-configuration, actuator, lazy-initialization, basics

**Start here: the concepts**
- **Bean**: an object that Spring creates and manages for you. Each bean costs some startup time and some memory.
- **Auto-configuration**: Spring Boot looks at the libraries on your classpath and creates beans for them automatically (for example, a DataSource if a JDBC driver is present). It is convenient, but every unused starter can add beans you never asked for.
- **Classpath scanning**: at startup Spring searches your packages for annotations like `@Component` to find beans. A wide scan over many classes takes time.
- **`@PostConstruct`**: a method that runs right after a bean is built. If it makes a remote call or loads big data, startup waits for it.
- **Lazy initialization**: beans are created when first needed, not at startup. Startup is faster, but the first request pays the cost.
- **AOT, CDS, native image**: AOT (ahead-of-time processing, Spring 6 / Boot 3) does bean-definition work at build time instead of at startup. CDS (Class Data Sharing) stores pre-parsed JVM classes in an archive so they load faster. A native image (GraalVM) is a compiled executable with very fast startup and low memory, but a slower build and some limits on reflection.
- **Startup actuator**: `BufferingApplicationStartup` records how long each startup step takes. The `/actuator/startup` endpoint then shows it.

**The live scenario**
A Spring Boot service on Kubernetes takes about 90 seconds to start. Illustratively, the readiness probe (the check that says "ready for traffic") gives up at 60 seconds, so pods restart in a loop during a deployment. Separately, a multi-tenant version creates a full set of beans, a cache and a thread pool per tenant. At 200 tenants, pods hit the container memory limit and get OOMKilled (killed by Kubernetes for using too much memory).

**What the interviewer is really checking**
Whether you measure before tuning, and whether you understand what Spring does at startup, so your fixes target the real cause instead of being a list of flags.

**How I answer it**
1. **Measure first.** Run with `--debug` to print the auto-configuration conditions report, which lists what was applied and what was skipped. Then enable startup recording to see which beans take the longest. Guessing wastes time because one slow bean often accounts for most of the delay.
```java
app.setApplicationStartup(new BufferingApplicationStartup(2048)); // then GET /actuator/startup
```
2. **Remove what you don't use.** Drop unused starters and exclude unneeded auto-configurations. Fewer beans means less work and less memory.
3. **Narrow classpath scanning.** Point scanning at your own packages instead of a broad root.
4. **Fix eager `@PostConstruct` work.** Move remote calls and big loads to async or lazy paths, or run them after startup. Slow external calls should not block readiness.
5. **Use lazy initialization selectively.** `spring.main.lazy-initialization=true` helps, but it is a fix, not a measuring tool. Use it globally only after testing, or mark specific heavy beans `@Lazy`. Selective use avoids slow first requests.
6. **Use build-time options if startup is still too slow.** Try AOT processing, CDS, or a native image. They cut work done at runtime, at the cost of build complexity.
7. **For memory, look at multiplication.** Beans per tenant, unbounded caches and a thread pool per feature all grow with scale. Share pools, bound caches (maximum size and expiry), and avoid creating per-tenant bean graphs.

**Trade-offs and what can go wrong**
- Global lazy init hides wiring errors until runtime, so a misconfigured bean fails in production on first use, not at deploy time.
- Native images restrict reflection and dynamic proxies, and builds are slower.
- Excluding an auto-configuration can silently break a feature that needed it.
- Setting the container memory limit without matching JVM heap settings causes OOMKills even when the heap looks fine, because metaspace and thread stacks count too.
- Raising probe timeouts only hides slow startup, so treat it as a stopgap.

**How I'd monitor it**
- Startup time: `/actuator/startup` and the `application.started.time` / `application.ready.time` Micrometer metrics.
- Memory: `jvm.memory.used` and `jvm.memory.max` (heap and non-heap), `jvm.threads.live`, and GC pause metrics.
- Cache size and hit-rate metrics.
- Kubernetes: pod restarts and OOMKilled events.
- Splunk: search for the "Started ... in X seconds" log line across deployments, and alert if it drifts upward.

**Follow-ups to expect**
- *Why not just enable lazy init everywhere?* -> It moves cost and failures to the first request, which hurts latency and hides config errors. Use it where measurements show gain.
- *What does `--debug` actually show?* -> The conditions evaluation report: which auto-configurations matched and which did not, and why.
- *How do you find a memory leak versus a big cache?* -> Take a heap dump and check the dominators (the objects holding the most memory). A bounded cache plateaus, while a leak grows steadily.

**60-second answer**
Startup problems usually come from too many auto-configured beans, wide classpath scanning and slow `@PostConstruct` work. Memory problems come from things multiplying, such as beans, caches or thread pools per tenant or feature. I measure first: `--debug` shows which auto-configurations applied, and `BufferingApplicationStartup` with the startup actuator shows which beans are slow. Then I remove unused starters, narrow scanning, move heavy init work out of startup, and use lazy initialization selectively. If that's not enough, I consider AOT, CDS or native images. For memory, I share thread pools, bound caches and avoid per-tenant bean graphs. I watch startup time and JVM memory metrics, and I align JVM settings with the container limit.

### Q20 [architect] Design a Spring Boot service skeleton you would give a new team (golden path).
tags: spring-boot, golden-path, architecture, observability, resilience, testing, basics

**Start here: the concepts**
- **Golden path:** a pre-built, supported way to start a service so every team begins with the same safe defaults. It exists so teams don't spend week one re-solving logging, errors and deployment.
- **Layers:** `api` holds controllers and DTOs (the request/response shapes). `application` holds use-case services and transaction boundaries. `domain` holds entities and business rules. `infrastructure` holds repositories, HTTP clients and messaging. Each layer has one job, so changes stay local.
- **Dependency direction:** the stored arrow chain ends `domain -> infrastructure`, which is wrong. Domain must not depend on infrastructure. Domain or application defines interfaces, and infrastructure implements them.
- **ProblemDetail:** Spring's standard JSON error body (RFC 7807, updated by RFC 9457), supported from Spring Framework 6. Every service then fails in the same shape.
- **Correlation ID:** a unique ID per request, put in a filter and in every log line, so one request can be followed across services.
- **Structured JSON logs:** one JSON object per log line, so Splunk can search by field instead of regex.
- **Micrometer / OpenTelemetry:** Micrometer is the metrics API. OpenTelemetry provides distributed tracing, which records the path of one request across services.
- **Timeouts, retry, circuit breaker:** a timeout bounds a wait. A retry repeats a failed call. A circuit breaker stops calling a failing dependency for a while. Resilience4j is the usual library.
- **Flyway:** versioned SQL migrations applied automatically, so the schema is in source control.
- **Testcontainers:** runs a real database or Kafka in Docker during tests.
- **ArchUnit:** unit tests that enforce architecture rules, such as "domain must not import Spring web".
- **Layered jar:** a Docker image split into dependencies and app code, so rebuilds reuse cached layers.

**The live scenario**
Ten teams each built their own service. Every service had a different error format, and only some had a correlation ID. During one incident, support spent 90 minutes tracing a single failed order across four services. One service had no HTTP timeout, so a slow dependency exhausted its threads and the failure spread. The platform team then published one template with these defaults. New services reached production in days, and a similar incident was traced in minutes.

**What the interviewer is really checking**
Whether you think in terms of defaults, enforcement and organisational scale, not only code structure. A golden path should make the right thing the easy thing, and prove it automatically.

**How I answer it**
1. **Layer by responsibility and point dependencies inward.** `api` calls `application`, which uses `domain`. `infrastructure` implements interfaces owned by the inner layers. This keeps business rules testable without a database or HTTP.
2. **Put `@Transactional` on application services.** That is the use-case boundary. Calls must come from another bean, because the proxy is bypassed on self-invocation.
3. **Standardise errors and traceability.** Use a `@RestControllerAdvice` returning `ProblemDetail`, a correlation-ID filter, JSON logs, Micrometer metrics and OpenTelemetry tracing. Without these, no one can debug across services.
4. **Make every outbound call safe.** Set connect and read timeouts, retry only idempotent calls, and add a circuit breaker. This stops one slow dependency from taking down the caller.
5. **Own the schema with Flyway.** Migrations are versioned and repeatable across environments, so no one changes a database by hand.
6. **Test against real dependencies.** Use Testcontainers, because H2 behaves differently from production databases. Add ArchUnit rules to the build so layer violations fail CI.
7. **Package for operations.** Use a Dockerfile with layered jars for fast builds, and health probes for Kubernetes. Harden `/actuator` by exposing only what is needed and securing it.
8. **Ship it as a template repo or Maven archetype.** A template repo is easier to keep current. An archetype is a one-time copy.

```properties
management.endpoint.health.probes.enabled=true
management.endpoints.web.exposure.include=health,info,prometheus
```

**Trade-offs and what can go wrong**
- Templates drift: services copied last year never get updates. Use shared starters or libraries for behaviour that must change centrally.
- Too rigid a path makes teams bypass it. Keep it opinionated but allow documented exceptions.
- Retries without idempotency cause duplicate side effects, and retries on top of retries amplify load.
- Exposing all actuator endpoints leaks environment data and heap dumps.
- Full layering is overkill for a tiny CRUD service. Say that you would scale the ceremony to the service.

**How I'd monitor it**
- Micrometer metrics: HTTP latency and error rate, JVM, and connection-pool usage.
- Circuit-breaker state and retry counts per dependency.
- Splunk searches by correlation ID, plus an alert on error-log rate.
- Kubernetes liveness and readiness probe failures.
- CI results: ArchUnit failures, and how many services still use the latest template version.

**Follow-ups to expect**
- *How do you stop template drift?* -> Put shared behaviour in versioned starters, and run automated dependency-update pull requests against all services.
- *Why Testcontainers over H2?* -> It tests the real database engine, SQL dialect and migrations, so passing tests mean more.
- *Liveness vs readiness probe?* -> Liveness says "restart me". Readiness says "don't send traffic yet". Keep dependency checks out of liveness.

**60-second answer**
I would give teams a template repo with a layered structure: `api`, `application`, `domain` and `infrastructure`. Dependencies point inward, and infrastructure implements interfaces owned by the inner layers. Cross-cutting concerns come built in: `ProblemDetail` errors, a correlation-ID filter, JSON logs, Micrometer metrics and OpenTelemetry tracing. Every outbound call gets timeouts, careful retries and a circuit breaker. Flyway owns the schema, Testcontainers gives realistic tests, and ArchUnit enforces the layering in CI. The Dockerfile uses layered jars, Kubernetes gets health probes, and `/actuator` is locked down. The main risk is drift, so I keep shared behaviour in versioned starters and track template adoption.

### Q21 [architect] Monolith vs modular monolith vs microservices for a new product - how do you decide?
tags: spring-modulith, modular-monolith, microservices, architecture, spring-boot, basics

**Start here: the concepts**
- **Monolith:** the whole application is built, deployed and run as one unit. Calls between parts are ordinary method calls, and one database transaction can cover everything. It exists because it is the simplest thing that works.
- **Modular monolith:** still one deployable unit, but the code is divided into modules with clear boundaries. Each module exposes a small public API and hides its internals. It exists to keep a monolith from turning into tangled code, a "big ball of mud".
- **Microservices:** the application is split into many small services. Each is deployed on its own, usually owns its own database, and talks to the others over the network (REST or messaging such as Kafka). They exist so teams can release and scale independently.
- **Spring Modulith:** a Spring project that treats each top-level package as a module. It can verify in a test that modules do not reach into each other's internals, and it supports event-based communication between modules.
- **Distributed transaction:** one business action that spans several services and databases. You cannot rely on a single database commit, so you use patterns such as a saga (a chain of local steps with compensating undo steps) and eventual consistency.
- **Fault isolation:** a failure in one part does not take down the rest.

**The live scenario**
*Illustrative numbers.* A start-up with 8 engineers builds a new product as 14 microservices in six months. The domain is still changing, so every feature touches 3-4 services. A checkout request now makes 6 network hops, and p99 latency is 1.2 s. A "simple" change needs 3 coordinated releases. Half the team's time goes to pipelines, contracts and debugging timeouts. A competitor ships the same features as a modular monolith with one deployment and in-process calls.

**What the interviewer is really checking**
Whether you decide from evidence (team size, domain clarity, scaling needs) rather than fashion. They also want to see that you know the real costs of microservices and can plan a path between the options.

**How I answer it**
1. **Treat it as a spectrum, not a three-way vote.** Plain monolith, modular monolith and microservices differ mainly in how strict the boundaries are and how much operational cost you accept.
2. **Default to a modular monolith for a new product with an unclear domain and a small team.** Early on you do not yet know where the right boundaries are. Moving a boundary inside one codebase is cheap, while moving it between services is expensive.
3. **Enforce the boundaries.** Boundaries that are only a convention erode. Spring Modulith can fail the build when a module breaks the rules:
   ```java
   ApplicationModules.of(Application.class).verify();
   ```
4. **Keep each module's data separate** (its own tables or schema, with no cross-module joins). This makes a later split possible.
5. **Split out a service only when there is a concrete reason:**
   - independent scaling, such as one module needing 20x the capacity of the rest;
   - a different release cadence;
   - clear team ownership, with many teams blocking each other;
   - fault isolation, such as a flaky integration that must not drag down checkout.
6. **Weigh the price before splitting.** You gain independence but take on network failure, retries, timeouts, distributed transactions, versioned contracts, tracing and a heavier deployment setup. Pay that price only when the benefit is real.
7. **A plain monolith is acceptable** for a prototype or a very small, short-lived tool, but I would still keep packages clean.

**Trade-offs and what can go wrong**
- Modular monolith: one deployment unit means one failure domain, and you scale everything together. The whole team shares one release train.
- Without enforced boundaries it silently decays into a big ball of mud.
- Microservices too early give you a "distributed monolith": services that must still be released together, plus network cost on top.
- A late split is hard if modules share tables or call each other's internals. Enforcing boundaries early keeps this cost down.
- Too many tiny services push the complexity into the network, where it is harder to see.

**How I'd monitor it**
- Run module verification in CI and track violations.
- Track deployment frequency, lead time for change and change-failure rate. These show whether the architecture is helping or hurting.
- In a monolith, watch per-module CPU, memory and latency (Micrometer tags). Persistent hotspots are evidence for a split.
- After splitting, track p99 latency per hop, error rate and retry counts with distributed tracing. Search Splunk by correlation ID to follow one request across services.

**Follow-ups to expect**
- *How do you extract a module into a service later?* -> Make sure it owns its data and talks through a defined API or events. Then move it behind the same interface, route traffic gradually (strangler approach) and remove the old code.
- *How do you handle a transaction across services?* -> Avoid it by design where possible. Otherwise use a saga with compensating actions, and the outbox pattern to publish events reliably.
- *Isn't microservices better for scale?* -> Only for the parts that need it. A monolith can scale horizontally behind a load balancer. Microservices pay off when parts have very different load or ownership.

**60-second answer**
I start from the problem, not the trend. For a new product with an unclear domain and a small team, I choose a modular monolith: one deployment, but modules with clear boundaries, enforced by Spring Modulith's verification in the build. That keeps changes cheap while we learn where the real boundaries are. I split out a service only for a concrete reason: independent scaling, a different release cadence, team ownership, or fault isolation. Microservices bring network failures, distributed transactions and heavy operations, so I pay that cost only when the benefit is real. If modules already own their data and communicate through clear APIs, the later split is straightforward.

### Q22 [fresher] What is JPA vs Hibernate vs Spring Data JPA?
tags: jpa, hibernate, spring-data-jpa, orm, persistence, spring-boot, basics

**Start here: the concepts**
- **Database table vs Java object:** Databases store rows in tables. Java code works with objects. Moving data between the two by hand (JDBC) means a lot of repetitive code.
- **ORM (Object-Relational Mapping):** A technique that maps a Java class to a table and an object to a row. You work with objects, and the tool writes the SQL.
- **Specification:** A written set of rules and interfaces with no working code behind it. Many vendors can implement it, which is why it exists: your code does not get tied to one product.
- **JPA (Jakarta Persistence):** The standard ORM specification for Java. It defines annotations such as `@Entity` and `@Id`, plus the `EntityManager` interface for saving and finding objects. It was formerly called Java Persistence API. Since Jakarta EE 9 the package changed from `javax.persistence` to `jakarta.persistence`, and Spring Boot 3 uses the `jakarta` one.
- **Hibernate:** A library that implements JPA. It does the real work: it builds SQL, runs it, and converts result rows into objects. It is the most common implementation, but not the only one (EclipseLink is another). It also has extra features beyond JPA.
- **Spring Data JPA:** A Spring layer on top of JPA. It is not a JPA implementation. You write an interface, and Spring generates the repository code that calls JPA, which in turn calls Hibernate. It gives you `JpaRepository`, derived queries (queries built from method names), `@Query` (your own query text), and paging (fetching data in pages).

**The live scenario**
An order service's "list orders" endpoint took about 2.5 seconds for 100 orders, and the database CPU was climbing. A junior developer said, "Spring Data is slow." The team turned on Hibernate SQL logging and found 101 SQL statements for one request: one query for the orders, then one per order for its items. This is the "N+1 problem". The code looked harmless because Spring Data hid it. Only someone who knew that Hibernate generates the SQL, and how, could fix it. They added a fetch join, and the request dropped to one query and about 120 ms (illustrative numbers).

**What the interviewer is really checking**
Whether you understand the layers: a standard (JPA), an engine (Hibernate) and a convenience layer (Spring Data JPA). Also whether you know that SQL is still being run underneath, so you can debug it.

**How I answer it**
1. **Start with JPA as the rule book.** It is a specification, so it defines interfaces and annotations but runs nothing. This keeps application code vendor-neutral.
2. **Name Hibernate as the engine.** It implements JPA and generates and executes the SQL. Say "most common", not "only".
3. **Place Spring Data JPA on top.** It removes boilerplate by generating repository implementations at startup. It calls JPA, and Hibernate does the work.
   ```java
   public interface OrderRepository extends JpaRepository<Order, Long> {
       List<Order> findByStatus(String status); // SQL generated from the method name
   }
   ```
4. **Describe the call flow.** Your code calls the repository, which calls the `EntityManager` (JPA), which Hibernate implements, which sends SQL over JDBC to the database.
5. **Close with why it matters.** Convenience does not remove SQL. When something is slow or wrong, you read the SQL Hibernate produced.

**Trade-offs and what can go wrong**
- **Hidden SQL:** Simple-looking methods can trigger many queries (N+1) or load far more data than needed.
- **Leaky abstraction:** "Swapping Hibernate for another provider" is rarely painless in practice, because teams often use Hibernate-specific features.
- **Common mistake:** Saying "Spring Data JPA replaces Hibernate". It does not. Hibernate is still running underneath.
- **Over-trusting derived queries:** Long method names get unreadable. Use `@Query` for complex cases.

**How I'd monitor it**
- In development, log `org.hibernate.SQL` at debug level to see the generated statements. Avoid verbose SQL logging in production.
- Count queries per request. Hibernate statistics can help, but they add overhead.
- Watch the Hikari connection pool metrics in Micrometer (active vs pending connections) to catch queries holding connections too long.
- Search logs in Splunk for slow endpoints, then match them to slow database queries.

**Follow-ups to expect**
- *What is the EntityManager?* -> The main JPA interface for saving, finding and removing entities. Spring Data repositories use it internally.
- *Can you use Hibernate without Spring Data JPA?* -> Yes. You can use JPA or Hibernate APIs directly. Spring Data only removes boilerplate.
- *What is the N+1 problem and how do you fix it?* -> One query for the parent rows plus one per child. Fix it with a fetch join, `@EntityGraph` or batch fetching.

**60-second answer**
JPA is a specification: a standard set of annotations and interfaces for mapping Java objects to database tables. It does not run anything by itself. Hibernate is the most common implementation of that specification, and it generates and runs the SQL. Spring Data JPA is a layer on top that creates repository code for you, with methods like `findById`, derived queries, `@Query` and paging. It calls JPA, and Hibernate does the real work underneath. So when a query is slow, I look at the SQL Hibernate generated, for example to spot the N+1 problem.

### Q23 [fresher] What are the entity states?
tags: jpa, hibernate, entity-lifecycle, persistence-context, dirty-checking, spring-data, basics

**Start here: the concepts**
- **Entity**: a Java object mapped to a database table row, usually marked with `@Entity`.
- **Persistence context**: a workspace, tied to the current transaction, where JPA/Hibernate keeps the entities it is tracking. In Hibernate it is the `Session`; in JPA it is the `EntityManager`. It exists so the framework knows which objects you loaded and can reuse them instead of re-querying. It is also called the first-level cache.
- **Entity state (lifecycle state)**: the relationship between a Java object and the persistence context. It decides whether changes to the object reach the database.
- **Transient (new)**: you created the object with `new`. The persistence context does not know it, and it has no database row yet.
- **Managed (persistent)**: the persistence context is tracking the object. This happens after you load it (`find`, a repository query) or save a new one.
- **Detached**: the object has a row, but the persistence context no longer tracks it. This happens when the transaction/session ends, or after `detach`, `clear` or `evict`. Changes to it are ignored.
- **Removed**: a managed object that you asked to delete. The `DELETE` runs at flush or commit.
- **Flush**: sending the pending SQL (`INSERT`/`UPDATE`/`DELETE`) to the database. It happens automatically before the transaction commits, and usually before a query that might be affected by pending changes. Flush is not commit: the data becomes permanent only at commit.
- **Dirty checking**: when the context loads an entity it keeps a snapshot. At flush it compares the entity with the snapshot and issues an `UPDATE` for any difference.

**The live scenario**
An order service marks about 2,000 orders a day as `SHIPPED`. A developer wrote `order.setStatus(SHIPPED)` with no `save()` and it worked in one service method, because that method was `@Transactional`. In another method, with no transaction, the same code changed nothing. The order was loaded, the repository's own short transaction ended, and the object became detached. The next morning about 800 orders were still `PENDING`, with no error in the logs.

**What the interviewer is really checking**
Whether you understand that an entity's behaviour depends on its state, and why `save()` is sometimes unnecessary. A fresher is expected to name the four states and explain dirty checking.

**How I answer it**
1. Name the four states: transient, managed, detached, removed. These cover the whole life of an object in JPA.
2. Explain that state depends on the persistence context. Only managed objects are watched, so state is about being tracked, not about whether a row exists.
3. Walk the transitions. `new` gives transient. `persist` or `save` gives managed. Loading by id gives managed. Ending the transaction gives detached. `remove` gives removed.
4. Explain dirty checking. Inside a transaction, a managed entity that changes is updated at flush without `save()`, because Hibernate compares it to its snapshot:
```java
@Transactional
void ship(Long id) { repo.findById(id).orElseThrow().setStatus(SHIPPED); } // UPDATE at commit
```
5. Explain detached objects. Changes are lost unless you reattach them with `merge` (Spring Data's `save()` calls `merge` for objects that already have an id). `merge` returns a managed copy, so use the returned object.

**Trade-offs and what can go wrong**
- Missing `@Transactional` means silent lost updates, as in the scenario.
- Detached entities with lazy fields throw `LazyInitializationException` when the lazy data is read after the session closes.
- Dirty checking over thousands of managed entities uses memory and CPU. For bulk work, batch and `clear()` the context.
- Flush timing surprises people: SQL runs at commit or before a query, not at the line where you changed the field.

**How I'd monitor it**
- Set `spring.jpa.show-sql` or the `org.hibernate.SQL` log level to DEBUG in dev to see when `UPDATE`s fire.
- Enable Hibernate statistics in staging to count flushes and entity updates.
- Search Splunk for `LazyInitializationException`.
- Add a data-quality check, such as orders stuck in `PENDING` past a threshold, with an alert.

**Follow-ups to expect**
- *Difference between `persist` and `merge`?* -> `persist` makes a new object managed. `merge` copies a detached object's state onto a managed instance and returns that instance.
- *Is flush the same as commit?* -> No. Flush sends the SQL, and commit makes it permanent. A rollback after a flush undoes the flushed changes.
- *Why do we sometimes need `save()` on an existing entity?* -> Only when it is detached or transient. A managed entity does not need it.

**60-second answer**
An entity in JPA is always in one of four states. Transient means a new object the framework does not know. Managed means the persistence context is tracking it. Detached means it has a row but is no longer tracked, usually because the transaction ended. Removed means it is scheduled for deletion. Only managed entities are watched, and that is why dirty checking works: inside a transaction, if I change a managed entity, Hibernate compares it to its snapshot at flush time and issues the `UPDATE` itself, so I don't need `save()`. If the object is detached, the change is silently ignored unless I `merge` it. A common bug is forgetting `@Transactional` and wondering why nothing was saved.

### Q24 [fresher] LAZY vs EAGER loading?
tags: jpa, hibernate, lazy-loading, eager-loading, n-plus-one, lazyinitializationexception, spring-data, basics

**Start here: the concepts**
- **Entity relationship**: a link between two database tables that JPA models as a field. For example, an `Order` has many `OrderItem`s (`@OneToMany`), and each `Order` belongs to one `Customer` (`@ManyToOne`).
- **Fetching**: deciding when JPA reads related rows from the database. Reading everything up front is costly. Reading nothing is risky if you need it later.
- **EAGER**: the related data is loaded in the same operation as the parent, whether or not you use it.
- **LAZY**: the related data is not loaded until your code first touches it. Until then the field holds a **proxy**.
- **Proxy**: a stand-in object generated by Hibernate. It looks like the real one, but the first time you call a method on it, it runs a SQL query to fetch the real data.
- **Session / persistence context**: Hibernate's working area for one unit of work. It remembers loaded objects and can run lazy queries only while it is open. In Spring it usually lasts as long as the `@Transactional` method.
- **LazyInitializationException**: the error you get when you touch a lazy field after the session has closed. The proxy has no database connection left to fetch with.
- **Fetch join**: a query (`join fetch`) that loads the parent and the related rows in one SQL statement.
- **DTO projection**: a query that selects only the columns you need into a plain object, so no entity or proxy is involved.
- **Open-in-view (OSIV)**: a Spring Boot setting (`spring.jpa.open-in-view`, on by default) that keeps the session open until the web response is written.

**The live scenario**
An orders API returns 50 orders per page and normally answers in 80 ms. After a release, p95 jumps to 1.5 s, and the database shows about 1,000 queries per second. A developer had changed `Order.customer` and `Order.items` to EAGER to fix a `LazyInitializationException`. Now each order triggers extra queries for its customer and its items. That is 1 query for the page plus roughly 100 follow-ups, the **N+1 problem**. A week earlier, the same bug had been "fixed" by leaving open-in-view on. That held a database connection for the whole request, including JSON rendering, and the pool nearly ran out at peak.

**What the interviewer is really checking**
Whether you know the defaults, can explain why `LazyInitializationException` happens, and know the right fix (load what you need, in the query) instead of the quick wrong ones: switching to EAGER or leaning on open-in-view.

**How I answer it**
1. **Define both.** LAZY loads a relation on first access through a proxy. EAGER loads it immediately with the parent. This shows you understand "when" is the whole difference.
2. **State the defaults.** `@OneToMany` and `@ManyToMany` default to LAZY, because collections can be huge. `@ManyToOne` and `@OneToOne` default to EAGER, because it is only one row.
3. **Override the defaults.** Set `@ManyToOne(fetch = FetchType.LAZY)` explicitly. An EAGER default means every query for the parent also pulls the related row, even when you never use it, and these costs add up across a model.
   ```java
   @ManyToOne(fetch = FetchType.LAZY) private Customer customer;
   ```
4. **Explain the exception.** If you read `order.getItems()` after the transaction has ended, the session is closed and the proxy cannot query. That is `LazyInitializationException`.
5. **Fix it by loading what you need.** Use a fetch join (`select o from Order o join fetch o.items`), an entity graph, or a DTO projection. The query then states exactly which data the use case needs.
6. **Avoid open-in-view as the fix.** It hides the error by keeping the session and a database connection open through the web layer. It also lets lazy queries fire unnoticed during serialization, so you pay for them in the pool and in latency.

**Trade-offs and what can go wrong**
- EAGER is a global, fixed decision. Every query pays for it, and a JPQL query ignores it and loads the relation with extra queries anyway, so you get N+1 without the benefit.
- LAZY gives control but needs discipline. Each use case must load what it needs, or you get N+1 or the exception.
- Fetch-joining several collections at once multiplies rows (a cartesian product), and pagination on a fetch-joined collection happens in memory. Hibernate logs a warning when it does this.
- LAZY on the non-owning side of a `@OneToOne` often cannot work without extra setup, because Hibernate must query to know whether the row exists.
- Never return entities directly from controllers. Serialization can touch lazy fields. Map to DTOs.

**How I'd monitor it**
- Enable Hibernate statistics, or log the SQL count per request in non-production environments, and look for a query count that grows with the page size.
- Watch HikariCP metrics through Micrometer/Actuator (`hikaricp.connections.active`, `hikaricp.connections.pending`) for pool pressure.
- Search logs (for example in Splunk) for `LazyInitializationException` and for slow-query warnings.
- Check that Spring Boot's startup warning about open-in-view is acted on, not ignored.

**Follow-ups to expect**
- *What is the N+1 problem?* -> One query loads N parents, then one extra query per parent loads its relation. Fix it with a fetch join, an entity graph, or batch fetching.
- *Why not just use EAGER everywhere?* -> It loads data you may not need on every query and still causes N+1 for JPQL queries, so performance gets worse and is hard to tune.
- *Why is open-in-view discouraged?* -> It holds a database connection for the whole request and hides lazy loading in the view layer, which hurts the pool under load.

**60-second answer**
LAZY means a related object is loaded only when you first use it, through a proxy. EAGER means it is loaded right away with the parent. By default, collections (`@OneToMany`, `@ManyToMany`) are LAZY, and single-value relations (`@ManyToOne`, `@OneToOne`) are EAGER. I set `@ManyToOne` to LAZY explicitly to avoid loading data I don't need. `LazyInitializationException` happens when I touch a lazy field after the session has closed. I fix that by loading what the use case needs in the query, with a fetch join, an entity graph or a DTO projection. I don't switch to EAGER or rely on open-in-view, because they cause N+1 queries and hold database connections too long.

### Q25 [mid] What is the N+1 select problem and how do you fix it?
tags: spring, jpa, hibernate, n-plus-one, lazy-loading, performance, basics

**Start here: the concepts**
- **ORM (Object-Relational Mapper, e.g. Hibernate/JPA):** a library that turns database rows into Java objects, so you write `order.getItems()` instead of SQL. It saves effort, but it hides when SQL actually runs.
- **Entity relationship:** an `Order` has many `OrderItem` rows. In Java this is a `List<OrderItem>` field on `Order`.
- **Lazy loading:** Hibernate does not load the items when it loads the order. It loads them the first time you touch `getItems()`. This avoids fetching data you may never use.
- **N+1 select problem:** you run 1 query to get N parent rows, then touch each parent's lazy collection. That triggers N more queries, one per parent, so 1 + N in total.
- **Why it hurts:** each query is a network round trip plus a pool connection. 100 queries of 2 ms each is 200 ms, and it grows with data size.
- **JOIN FETCH / @EntityGraph:** tell Hibernate to load parent and children in one SQL join.
- **Batch fetching:** load the lazy collections for many parents at once using `WHERE order_id IN (...)`.
- **DTO projection:** select only the columns you need into a plain object, bypassing entities.

**The live scenario**
An orders screen showed 50 orders per page. In test it was instant. In production, p95 latency rose from 80 ms to 900 ms at peak, and the DB showed about 4,000 queries per second for a few hundred requests. Splunk showed 51 near-identical `select ... from order_items where order_id=?` statements per request. The cause was the mapper looping over orders and calling `getItems()`. One fetch-join query dropped it to 1 statement.

**What the interviewer is really checking**
Whether you understand that lazy loading is the mechanism behind N+1, and whether you know several fixes and when each one fails (pagination, multiple collections). Many candidates can only name `JOIN FETCH`.

**How I answer it**
1. **Define it with numbers.** "1 query for 50 orders plus 50 for items = 51." This shows the cost is proportional to N.
2. **Name the cause.** Lazy loading fires a query on first access, per parent. Switching to `EAGER` is not a fix: it often creates the same N+1 everywhere, even where you don't need the data.
3. **Fix with a fetch join** when you need the children:
   ```java
   @Query("select o from Order o join fetch o.items where o.status = :s")
   ```
   One SQL join loads everything. Use `@EntityGraph` for the same effect without writing JPQL.
4. **Use batch fetching as a global safety net.** Set `hibernate.default_batch_fetch_size` (e.g. 50; in Spring Boot via `spring.jpa.properties.…`), or `@BatchSize` on one collection. 51 queries become about 2, and paging still works.
5. **Use a DTO projection for read-only screens.** Select just the columns you need. This is usually the fastest and avoids loading entities.
6. **Detect it before production.** Count SQL statements in tests (datasource-proxy or Hypersistence Utils) and fail the test if a call exceeds the expected count.

**Trade-offs and what can go wrong**
- Fetch-joining a collection while paginating makes Hibernate page in memory after loading all rows (it logs a warning). Use batch fetching or a two-step query (page the IDs, then fetch).
- Fetch-joining two `List` collections can throw `MultipleBagFetchException` and multiplies rows (a cartesian product). Use `Set`, or batch fetching.
- A join returns parent columns repeated per child, so payload grows.
- Batch size is a guess: too big means large `IN` lists.
- Open-session-in-view (Spring Boot's `spring.jpa.open-in-view`, on by default) hides the problem by letting lazy loads fire in the controller or JSON serialization.

**How I'd monitor it**
- Enable SQL logging in dev and tests only, not production.
- Run query-count assertions in CI.
- Hibernate statistics (`hibernate.generate_statistics`) or Micrometer metrics show statements per request.
- In Splunk, search for the same SQL repeated many times with the same trace ID or request ID.
- Watch DB queries per second and connection pool wait time against request rate.

**Follow-ups to expect**
- *Why not just make the relation EAGER?* -> It loads the data on every query, including where it isn't needed, and can still cause N+1 with JPQL queries.
- *How do you fetch-join with pagination?* -> Page the parent IDs first, then fetch those parents with their children, or use batch fetching.
- *Does N+1 happen with `@ManyToOne`?* -> Yes, if it is lazy, or if it is eager and loaded through a JPQL query without a fetch join.

**60-second answer**
N+1 happens when I load N parent rows with one query, then lazy loading fires one extra query per parent for its children. For 50 orders that is 51 queries instead of 1 or 2, and latency grows with data size. I fix it with `JOIN FETCH` or `@EntityGraph` when I need the children, and batch fetching (`default_batch_fetch_size`) when I'm paginating or have several collections. For read-only screens I use a DTO projection. I avoid `EAGER`, because it only moves the problem. I catch it early by asserting SQL statement counts in tests and checking repeated queries in the logs.

### Q26 [mid] How does `@Transactional` work and what are its traps?
tags: spring, transactional, aop-proxy, rollback, connection-pool, spring-boot, basics

**Start here: the concepts**
- **Transaction:** a group of database changes that must all succeed or all be undone. Example: take money from account A and add it to account B. It exists so a failure halfway never leaves half-finished data.
- **Commit / rollback:** commit makes the changes permanent. Rollback throws them all away.
- **Proxy:** a stand-in object Spring puts in front of your bean. Callers talk to the proxy, which does extra work (here, starting a transaction) before and after calling your real method. `@Transactional` is just a marker that tells Spring to build this proxy.
- **Self-invocation:** a method calling another method on `this`. That call goes straight to the real object and never passes through the proxy, so the annotation is ignored.
- **Checked vs unchecked exception:** unchecked ones (`RuntimeException`, `Error`) need no `throws` declaration. Checked ones (such as `IOException`) must be declared or caught.
- **Thread-bound:** Spring stores the current transaction and its connection in a `ThreadLocal`, a variable that each thread sees separately. Another thread cannot see that transaction.
- **Connection pool:** a small, fixed set of ready database connections (HikariCP by default in Spring Boot). A transaction holds one connection until it finishes.

**The live scenario**
A checkout service handles about 200 requests/s with a pool of 20 connections. Two incidents happened in one month.
1. `placeOrder()` saved the order, then threw a checked `PaymentDeclinedException`. Nothing rolled back, so 340 orders sat in the database with no payment.
2. After a release, `placeOrder()` called a slow fraud-check API (about 3 s) inside the transaction. Every request held a connection for 3 s, the pool ran dry within seconds, and the whole service timed out.

**What the interviewer is really checking**
Whether you know that `@Transactional` is proxy-based, and can predict from that mechanism when it silently does nothing, rather than reciting a list of rules.

**How I answer it**
1. **Explain the mechanism.** Spring wraps the bean in a proxy. On a call it gets a connection, begins the transaction, runs your method, then commits. If the exception qualifies, it rolls back instead. Every trap below follows from this.
2. **Self-invocation.** `this.other()` skips the proxy, so no transaction starts. The fix is to move the method into another bean, so the call crosses a proxy.
3. **Private and final methods.** Spring builds the proxy by subclassing your class (CGLIB, the default in Spring Boot). A subclass cannot override `private` or `final` methods, so they are never intercepted. Keep `@Transactional` on public methods; non-public support depends on the Spring version, so I don't rely on it.
4. **Rollback rules.** By default only unchecked exceptions and errors roll back. A checked exception commits the work. If you want rollback, say so explicitly: `@Transactional(rollbackFor = Exception.class)`. Also, if you catch the exception yourself and swallow it, the proxy never sees it and commits.
5. **Thread boundary.** The transaction lives in a `ThreadLocal`. Code run in `@Async`, a new thread, or a parallel stream does not join it, so its writes happen outside it and are not rolled back with it.
6. **Keep transactions short.** The connection stays held for the whole method. Never call remote services, send emails or wait on slow work inside one. Do the remote call first, then open a short transaction for the writes.

**Trade-offs and what can go wrong**
- Using `rollbackFor = Exception.class` everywhere is safe but can hide that you rely on a default. Agree on a team convention.
- With the default propagation (`REQUIRED`), an inner method that marks the shared transaction rollback-only makes the outer commit fail with `UnexpectedRollbackException`, even if the outer code caught the error.
- `REQUIRES_NEW` suspends the current transaction and takes a second connection. Under load, that can deadlock the pool.
- Tests marked `@Transactional` roll back automatically and can hide commit-time problems.

**How I'd monitor it**
- Micrometer/Actuator: `hikaricp.connections.active`, `hikaricp.connections.pending` and `hikaricp.connections.acquire` time. Alert when pending is above 0 for a sustained period.
- Splunk: search for `Connection is not available, request timed out` and `UnexpectedRollbackException`.
- In a test environment, set the `org.springframework.transaction` logger to DEBUG or TRACE to see "Getting transaction" and "Rolling back" lines. A missing line means the proxy was bypassed.
- A reconciliation query, such as orders without payments, catches silent commits.

**Follow-ups to expect**
- *Why does `@Transactional` not work when I call a method in the same class?* -> The call uses `this`, not the proxy. Move the method to another bean.
- *What does `REQUIRES_NEW` do?* -> It suspends the current transaction and starts an independent one on a new connection. It commits or rolls back on its own.
- *Does `readOnly = true` stop writes?* -> It is a hint. It can enable optimisations, but the effect depends on the persistence provider and database, so don't use it as protection.

**60-second answer**
`@Transactional` works through a proxy. Spring puts a stand-in object in front of my bean. When someone calls a method, the proxy opens a transaction, runs the method, then commits, or rolls back on an exception. The traps come from that design. A call from inside the same class skips the proxy, and private or final methods can't be intercepted. By default only unchecked exceptions roll back, so for checked ones I add `rollbackFor = Exception.class`. The transaction is tied to the current thread, so work on another thread is outside it. A transaction also holds a database connection, so I keep it short and never call remote services inside it. Otherwise the connection pool runs out under load.

### Q27 [mid] Propagation and isolation levels?
tags: spring, transactions, propagation, isolation, jdbc, databases, basics

**Start here: the concepts**
- **Transaction:** a group of database operations that either all succeed (commit) or all undo (rollback). It exists so a failure halfway never leaves half-written data, such as money taken from one account but not added to another.
- **Propagation:** the rule for what a `@Transactional` method does when it is called while a transaction is already running. It can join it, start its own, or refuse to run.
- **Isolation:** the rule for how much one running transaction can see of other transactions' uncommitted or changing data. It exists because many transactions run at the same time.
- **Dirty read:** reading data another transaction has not committed yet. It may later be rolled back, so you saw something that never officially existed.
- **Non-repeatable read:** you read a row twice in one transaction and get different values because someone committed a change in between.
- **Phantom read:** you run the same query twice and the second run returns extra or missing rows because someone inserted or deleted rows in between.
- **Savepoint:** a bookmark inside a transaction. You can roll back to the bookmark without undoing everything before it.
- **Proxy:** Spring wraps your bean in a stand-in object that starts and ends the transaction around your method. Calls that do not go through the proxy get no transaction behaviour.

**The live scenario**
An order service handles about 200 orders per second. `placeOrder()` saves the order and calls `auditService.log()`. The team wanted audit rows even when the order fails, so they marked `log()` as `REQUIRES_NEW`. It worked, but at peak the connection pool (illustratively 20 connections) was exhausted. Each request held one connection for the outer transaction and took a second one for the audit, so threads waited on the pool and latency went from 80 ms to several seconds. In another service, a report running at the default isolation showed totals that changed between two reads in the same method. Both problems came from not understanding these two settings.

**What the interviewer is really checking**
Whether you know what each option actually does at runtime, not just its name. That includes the proxy limits, the cost of `REQUIRES_NEW`, and why a higher isolation level is not "free".

**How I answer it**
1. **Propagation decides join or new.** `REQUIRED` (default) joins the existing transaction or creates one. It is the default because most business methods should commit or roll back together.
2. **`REQUIRES_NEW`** suspends the current transaction and starts a separate one on a separate connection. Use it for work that must survive an outer rollback, such as an audit log. The cost is a second connection, which is the pool risk from the scenario.
3. **`NESTED`** creates a savepoint inside the current transaction. If the inner part fails, only that part is undone. If the outer transaction rolls back, everything goes. It needs savepoint support, which is mainly JDBC-based, so check your transaction manager.
4. **The remaining options** control presence of a transaction:
   - `SUPPORTS`: join if one exists, otherwise run without one.
   - `MANDATORY`: a transaction must already exist, otherwise throw an exception.
   - `NEVER`: throw an exception if one exists.
   - `NOT_SUPPORTED` (not in the stored answer): suspend any transaction and run without one.
5. **Isolation is about concurrent transactions.** From weakest to strongest:
   - `READ_UNCOMMITTED`: allows dirty reads.
   - `READ_COMMITTED`: no dirty reads. This is the default in Oracle, PostgreSQL and SQL Server.
   - `REPEATABLE_READ`: a row read twice gives the same value. This is the default in MySQL InnoDB.
   - `SERIALIZABLE`: transactions behave as if run one after another.
6. **Spring's `Isolation.DEFAULT` means "use the database's default".** Isolation only applies when a new transaction begins. A method that joins an existing one does not change it.
7. **Higher isolation means fewer anomalies but more locking or failed transactions that need a retry.** Pick the lowest level that is correct for the use case.

```java
@Transactional(propagation = Propagation.REQUIRES_NEW, isolation = Isolation.READ_COMMITTED)
```

**Trade-offs and what can go wrong**
- Calling a `REQUIRES_NEW` method from the same class bypasses the proxy, so it silently runs in the caller's transaction. Put it in another bean.
- If an inner `REQUIRED` method throws a runtime exception and the outer code catches it, the shared transaction is already marked rollback-only. The outer commit then fails with `UnexpectedRollbackException`.
- Nested `REQUIRES_NEW` calls inside loops multiply connection use and can deadlock the pool.
- `SERIALIZABLE` (and PostgreSQL's `REPEATABLE READ`) can fail with serialization errors, so the caller must retry.
- Database behaviour differs by engine, for example PostgreSQL treats `READ_UNCOMMITTED` as `READ_COMMITTED`. Test on your real database.

**How I'd monitor it**
- Connection pool metrics: HikariCP `hikaricp.connections.active`, `hikaricp.connections.pending` and `hikaricp.connections.acquire` through Micrometer and Actuator. Alert when pending is above zero for a sustained period.
- Database views for lock waits and deadlocks (for example `pg_stat_activity` or the MySQL InnoDB status).
- Splunk searches for `UnexpectedRollbackException`, `CannotAcquireLockException` and serialization failure messages, grouped by service.
- Debug logging for `org.springframework.transaction` in a test environment to see joins, suspends and savepoints.

**Follow-ups to expect**
- *Why did my `REQUIRES_NEW` not start a new transaction?* -> You called it from within the same class, so the proxy was bypassed. Move it to another bean.
- *Difference between `NESTED` and `REQUIRES_NEW`?* -> `NESTED` is a savepoint inside the same transaction and connection. `REQUIRES_NEW` is a fully independent transaction that commits on its own.
- *Which isolation fixes phantom reads?* -> `SERIALIZABLE` by the SQL standard. Some databases, such as PostgreSQL at `REPEATABLE READ`, also prevent them using snapshots.

**60-second answer**
Propagation says what a transactional method does when a transaction already exists. `REQUIRED`, the default, joins it or creates one. `REQUIRES_NEW` suspends it and runs separately on another connection, which suits audit logs that must survive a rollback but can exhaust the connection pool. `NESTED` uses a savepoint, so only the inner part rolls back. `SUPPORTS`, `MANDATORY`, `NEVER` and `NOT_SUPPORTED` control whether a transaction must, may or must not be present. Isolation controls what concurrent transactions can see, covering dirty, non-repeatable and phantom reads. `READ_COMMITTED` is the default in Oracle and PostgreSQL, and `REPEATABLE_READ` in MySQL. Higher levels give fewer anomalies but more locking or retries, so I choose the lowest level that is still correct. Also, none of this works if the call skips the Spring proxy, for example a self-invocation.

### Q28 [mid] Optimistic vs pessimistic locking?
tags: spring, jpa, hibernate, locking, concurrency, transactions, basics

**Start here: the concepts**
- **Concurrency problem (lost update):** Two users read the same row, both change it, and the second save silently overwrites the first. Locking exists to prevent this.
- **Lock:** A marker on a row that makes other transactions wait or fail instead of overwriting.
- **Transaction:** A group of database steps that succeed or fail together. Database locks live only until the transaction commits or rolls back.
- **Optimistic locking:** Assume collisions are rare and take no database lock. Each row has a version number. On update, the database checks that the version is still the one you read. If not, someone else got there first and your update is rejected.
- **`@Version`:** The JPA annotation that marks that version column. Hibernate runs roughly `UPDATE ... SET ..., version = version + 1 WHERE id = ? AND version = ?`. If zero rows match, it throws `OptimisticLockException`. Spring Data usually wraps it as `ObjectOptimisticLockingFailureException`.
- **Pessimistic locking:** Assume collisions are likely and lock the row up front. `SELECT ... FOR UPDATE` makes every other transaction that wants that row wait until you finish. In JPA this is `@Lock(PESSIMISTIC_WRITE)`.
- **Contention:** How often many transactions want the same row at the same time.
- **Deadlock:** Transaction A holds row 1 and waits for row 2, while B holds row 2 and waits for row 1. The database kills one of them.
- **`SKIP LOCKED`:** A clause that makes a query ignore rows that are already locked instead of waiting. It is supported by PostgreSQL, MySQL 8+ and Oracle.

**The live scenario**
An inventory service handles 40 requests per second on ordinary products. Optimistic locking works fine there: about 1 in 10,000 updates collides and is retried. During a flash sale, 2,000 requests per second hit 20 hot products. Most updates now fail the version check, retries pile up, p99 latency goes from 80 ms to 4 s, and users see errors. The team switches only the stock-decrement path to pessimistic locking. Requests queue briefly on the row, and every one succeeds. Separately, a `jobs` table is polled by 8 workers. They were blocking each other until the team added `SKIP LOCKED`.

**What the interviewer is really checking**
Whether you choose by contention level rather than by habit. They also want to know whether you understand that locking is enforced by the database and tied to the transaction, and that you know the failure modes of each approach.

**How I answer it**
1. **Define the problem.** Two concurrent writers can cause a lost update, so I need either detection or prevention.
2. **Optimistic = detect.** Add a version column. No lock is held while the user thinks or the code runs, so it scales well when collisions are rare.
   ```java
   @Version private long version;
   ```
3. **Handle the failure.** On `OptimisticLockException`, retry the whole transaction: reload the row, reapply the change, save. Retrying with the stale object fails again. For user-facing edits, return HTTP 409 so the user can refresh.
4. **Pessimistic = prevent.** Lock the row when reading it, so others wait.
   ```java
   @Lock(LockModeType.PESSIMISTIC_WRITE) Optional<Item> findById(Long id);
   ```
   This must run inside a `@Transactional` method, because the lock is released on commit or rollback.
5. **Choose by contention.** Low contention and mostly reads means optimistic. High contention on the same row, or when a failed retry is expensive or has side effects, means pessimistic.
6. **Job queues.** Use `FOR UPDATE SKIP LOCKED` so each worker grabs different unlocked rows instead of queuing behind one another. In Hibernate this is set through a lock hint, and the exact syntax depends on the version.

**Trade-offs and what can go wrong**
- Optimistic under high contention causes retry storms: wasted work and rising latency.
- Pessimistic causes waiting, lock timeouts and deadlocks. Lock rows in a consistent order to reduce deadlocks.
- Long transactions that hold pessimistic locks (for example, one that calls a remote API) can exhaust the connection pool.
- Forgetting to retry with fresh data, or retrying outside the transaction boundary.
- `SKIP LOCKED` gives no strict ordering, so it is unsuitable when order matters.

**How I'd monitor it**
- Micrometer counter for optimistic failures, and a Splunk search on `ObjectOptimisticLockingFailureException` with a count by endpoint.
- Retry count and p99 latency per endpoint.
- Database lock waits and deadlock logs (for example, `pg_locks` or `pg_stat_activity` in PostgreSQL).
- HikariCP metrics: active and pending connections, since long lock waits show up there first.
- Alert when the optimistic failure rate or lock-wait time rises above its normal baseline.

**Follow-ups to expect**
- *Does optimistic locking use database locks?* -> No lock is held while you work. Only the final `UPDATE ... WHERE version = ?` briefly locks the row, and it fails if the version changed.
- *How do you avoid deadlocks with pessimistic locking?* -> Acquire locks in a consistent order, keep transactions short, and set a lock timeout.
- *Can an atomic update avoid locking in code?* -> Yes. `UPDATE stock SET qty = qty - 1 WHERE id = ? AND qty > 0` is a single atomic statement and is often the simplest fix for counters.

**60-second answer**
Both approaches stop two users from overwriting each other's changes. Optimistic locking uses a `@Version` column and takes no lock. If the version changed before my update, it throws an exception and I retry the whole transaction with fresh data. It is cheap and works well when collisions are rare. Pessimistic locking uses `SELECT ... FOR UPDATE`, or `@Lock(PESSIMISTIC_WRITE)` in JPA, to make others wait for the row. I use it when many requests fight over the same row, accepting the risk of waits and deadlocks. For job tables I add `SKIP LOCKED` so workers pick different rows. I choose by contention and watch retry rates, lock waits and connection-pool usage.

### Q29 [mid] First-level vs second-level cache?
tags: hibernate, jpa, caching, persistence-context, second-level-cache, spring-data, basics

**Start here: the concepts**
- **Cache:** a copy of data kept close at hand so you skip a slow trip to the database. The cost is that the copy can go stale.
- **Persistence context (first-level cache, L1):** the in-memory map of entities that one Hibernate `Session` / JPA `EntityManager` is currently tracking, keyed by entity type and id. It exists so one unit of work sees one object per row and Hibernate can detect changes ("dirty checking"). It is always on and cannot be turned off.
- **Second-level cache (L2):** an optional cache owned by the `SessionFactory` / `EntityManagerFactory`, shared by all sessions in the application. It is off by default and needs a cache provider, such as Ehcache or Infinispan, or Caffeine through JCache. It stores entity data (not live objects) and is used for lookups by id.
- **Query cache:** an optional extra cache that stores the list of ids a query returned. It also needs L2 for the entities themselves.
- **Invalidation:** removing or updating cached copies when the underlying data changes. This is the hard part of any cache.
- **TTL (time to live):** a cache entry expires after a fixed time, which limits how stale it can get.

**The live scenario**
An order service handles about 800 requests/s. Every request loads the same 200-row `Country` table, and the database CPU sits at 70%. The team marks `Country` as a read-only L2 entity, and DB reads for it vanish. A month later someone caches the `Inventory` entity in a local L2 on three pods. Pod A updates stock, but pods B and C keep serving old counts, and customers oversell items. The same feature was a win for reference data and a bug for fast-changing data.

**What the interviewer is really checking**
Whether you know L1 and L2 have different scope and lifetime, and whether you understand the stale-data risk of L2 well enough to say when *not* to use it.

**How I answer it**
1. **L1 is per session and always on.** Within one session, loading the same id twice runs one SQL statement and returns the same object. In Spring this is usually one transaction. With Open Session in View it lasts the whole web request, so it is not strictly "per transaction".
2. **L1 is cleared when the session closes**, so it never helps across requests. That is why people reach for L2.
3. **L2 is shared across sessions and must be enabled explicitly.** Mark an entity as cacheable and pick a concurrency strategy:
   ```java
   @Entity @Cacheable
   @org.hibernate.annotations.Cache(usage = CacheConcurrencyStrategy.READ_ONLY)
   ```
4. **Use L2 only for read-mostly reference data** such as countries, currencies and configuration. Hit rates are high and changes are rare. Entities that change often just churn the cache and risk stale reads.
5. **Know that L2 adds invalidation complexity.** Updates made through Hibernate refresh the cache, but direct SQL, other applications or other nodes can leave it stale. A multi-node setup needs a distributed or replicated provider.
6. **The query cache is rarely worth it.** Any write to a table invalidates every cached query on it, so it only pays off for read-only tables queried with identical parameters.
7. **Prefer an application-level cache with explicit TTL**, such as Spring's `@Cacheable` backed by Caffeine or Redis. You control what is cached, for how long and when it is evicted, and the staleness is visible in your code.

**Trade-offs and what can go wrong**
- Stale data across nodes or after bulk or native updates, which bypass Hibernate's invalidation.
- Memory pressure from unbounded cache regions.
- Hidden behaviour: a developer sees no SQL and can't tell whether the data is fresh.
- L1 surprise: in a long session, reads can return stale objects, and a big persistence context slows dirty checking.
- Turning L2 on everywhere "for performance" is a common mistake.

**How I'd monitor it**
- Enable Hibernate statistics and watch L2 hit, miss and put counts per region. A low hit ratio means the cache isn't helping.
- Track DB query counts and latency before and after enabling it.
- Check JVM heap and cache size or eviction metrics (Micrometer exposes Caffeine and JCache stats).
- Log SQL in a test environment to confirm the second lookup no longer hits the database.

**Follow-ups to expect**
- *Does L2 cache JPQL query results?* -> No. It serves lookups by id (and cached collections). JPQL queries hit the DB unless the query cache is on, and even then only ids are cached.
- *What do the L2 concurrency strategies mean?* -> `READ_ONLY` is fastest and for data that never changes. `NONSTRICT_READ_WRITE` allows brief staleness. `READ_WRITE` locks entries on update for stronger consistency. `TRANSACTIONAL` needs a JTA-capable provider.
- *Why might the same entity be loaded twice in one request?* -> Two separate sessions or transactions were used, so each has its own L1 and there is no sharing unless L2 is on.

**60-second answer**
The first-level cache is Hibernate's persistence context. It belongs to one session, which is usually one transaction, and it is always on. Within that session, the same id gives you the same object with one query. The second-level cache is shared across sessions, off by default, and needs a provider such as Ehcache or Infinispan. I only use it for read-mostly reference data, because it brings invalidation problems: stale reads across nodes or after native updates. I avoid the query cache because any write to the table invalidates its entries. For most needs I prefer an application-level cache with an explicit TTL, so I control what is cached and how stale it can get. I'd check hit ratios and database load to confirm it actually helps.

### Q30 [mid] When do you use JdbcTemplate/jOOQ/native SQL instead of JPA?
tags: spring, jpa, hibernate, jdbctemplate, jooq, sql, basics

**Start here: the concepts**
- **JPA / Hibernate**: JPA is the Java standard for mapping objects to database tables (ORM, object-relational mapping). Hibernate is the usual implementation. It exists so you don't hand-write SQL and row-to-object code for every table.
- **Persistence context**: the in-memory "tracking area" where JPA keeps loaded entities and notices changes, so it can write them back automatically. It is convenient, but it costs memory and CPU for every object it tracks.
- **Aggregate**: a small group of objects treated as one unit, such as an Order with its OrderLines. JPA fits this well: load the unit, change it, save it.
- **JdbcTemplate**: Spring's thin helper over plain JDBC. You write the SQL yourself, and it handles connections, exceptions and row mapping.
- **jOOQ**: a library that lets you write SQL in Java code with compile-time checking against your schema. You still control the SQL, but typos in column names become compile errors.
- **Native SQL**: SQL written for your specific database. JPA can also run it (`@Query(nativeQuery = true)`), so "native SQL" and "JPA" are not strictly exclusive.
- **Window function**: SQL such as `RANK() OVER (PARTITION BY ...)` that computes running totals or rankings across rows without collapsing them. JPQL (JPA's query language) has no support for it.
- **Bulk update**: one statement that changes many rows (`UPDATE ... WHERE ...`) instead of loading each row as an object.
- **Projection**: reading only the columns you need into a simple read-only object instead of a full entity.

**The live scenario**
A nightly report for 2 million orders was built with JPA entities. It took about 40 minutes, pushed the heap near its limit, and caused long GC pauses that slowed the live API on the same service. The work was just "sum revenue per region per day". We replaced it with one SQL `GROUP BY` through JdbcTemplate, returning about 5,000 rows. It finished in under a minute with almost no memory. A similar "expire 500k old invoices" job, which loaded and saved entities one by one, became a single `UPDATE`.

**What the interviewer is really checking**
Whether you pick the tool by the shape of the job rather than by habit. JPA suits object-style CRUD, while SQL suits set-based work, and you should say that using both is normal.

**How I answer it**
1. **Default to JPA for writes on an aggregate.** It gives you change tracking, relationships and less boilerplate, and the volume per request is small.
2. **Use SQL for reports and aggregations.** The database is built for set-based work, so let it do the summing. Pulling millions of entities into Java wastes memory and time.
3. **Use SQL for bulk updates and deletes.** One `UPDATE` replaces thousands of round trips. A JPQL bulk update also works, but it bypasses the persistence context, so already-loaded entities go stale unless you clear them.
4. **Use SQL for complex joins and window functions.** JPQL can't express them cleanly, and forcing them often produces odd or slow queries.
5. **Use SQL for database-specific features.** Examples are Oracle hints, `MERGE`, hierarchical queries and Postgres `ON CONFLICT`. These tie you to one database, so isolate them.
6. **Use SQL on hot paths where you need exact SQL.** When profiling shows ORM-generated queries are too slow or too many (for example N+1), hand-written SQL gives predictable behaviour.
7. **Mix them on purpose.** A common split is JPA for the write side and SQL or projections for the read side. This is "CQRS-lite" (separate read and write models). It does not require separate databases. Both can share one transaction manager.

```java
jdbc.query("select region, sum(total) from orders where day = ? group by region", mapper, day);
```

**Trade-offs and what can go wrong**
- Raw SQL loses automatic mapping, portability and refactor safety. jOOQ recovers some of that, but adds a dependency and code generation.
- Mixing JPA and JDBC in one transaction: JPA may hold unflushed changes that your SQL cannot see. Call `flush()` first, or keep the two paths separate.
- After a bulk update, entities in the persistence context are stale.
- SQL strings spread everywhere become hard to maintain. Keep them in repository classes and test them against a real database (for example with Testcontainers).
- Don't drop JPA because of one slow query. Fix N+1 with fetch joins or projections first.

**How I'd monitor it**
- Hikari pool metrics via Micrometer (`hikaricp.connections.active`, `.pending`, `.usage`) to catch long-running queries holding connections.
- Hibernate statistics (statement counts per request) to spot N+1.
- Database slow-query views (`pg_stat_statements`, Oracle AWR) and Splunk searches on slow-query logs.
- JVM heap and GC pause metrics to catch entity-heavy jobs.

**Follow-ups to expect**
- *Why is loading entities for a report slow?* -> Each one is mapped, tracked in the persistence context and kept in memory, so cost grows with row count.
- *Can JPA run native SQL?* -> Yes, via native queries, which is often enough when you only need one special query.
- *JdbcTemplate or jOOQ?* -> JdbcTemplate for simple queries with no extra dependency. jOOQ when SQL is complex and you want type safety.

**60-second answer**
I use JPA by default for CRUD on an aggregate, because it removes boilerplate and tracks changes for me. I switch to JdbcTemplate, jOOQ or native SQL when the job is set-based. That means reports, bulk updates, complex joins, window functions, database-specific features, and hot paths where I need exact SQL. For example, summing 2 million orders through entities used lots of memory and 40 minutes, while one `GROUP BY` took seconds. Mixing is normal: JPA for writes and SQL or projections for reads, which is a light form of CQRS. I watch for stale entities after bulk updates and unflushed JPA changes inside the same transaction. I'd confirm the choice with Hikari metrics, Hibernate statement counts and the database's slow-query views.

### Q31 [mid] How do you do paging safely?
tags: spring-data, pagination, jpa, keyset-pagination, sql-performance, database-indexes, basics

**Start here: the concepts**
- **Paging:** returning a big result set in small chunks (say 50 rows) instead of all at once. It protects memory, network and the database, and keeps screens and APIs fast.
- **`Pageable`:** a Spring Data object holding the page number, page size and sort order. You pass it to a repository method and Spring turns it into SQL.
- **Offset paging:** "skip N rows, then take 50" (`OFFSET`/`LIMIT`). To skip N rows, the database still walks past them, so cost grows with N. That is the O(offset) in the stored answer.
- **Stable sort:** an `ORDER BY` that always puts rows in exactly the same order. Without it, or when sorting on a column with duplicates (like `created_date`), rows can appear on two pages or on none while you page.
- **Keyset (seek) paging:** instead of "skip N", you remember the last key you saw and ask for rows after it: `WHERE id > :last ORDER BY id LIMIT 50`. With an index on the key, the database jumps straight there, so page 10,000 costs about the same as page 1.
- **`Page` vs `Slice`:** `Page` knows the total row count, so it runs an extra `select count(*)`. `Slice` only knows whether a next page exists. It fetches one extra row (size + 1) and skips the count.

**The live scenario**
An orders screen shows 50 rows per page over a 40-million-row table. Early pages return in 20 ms. A nightly export job loops through pages with `Page<Order>` and reaches offset 30 million, and each call takes about 8 seconds. Every call also runs a `count(*)` over the whole table. The database CPU spikes and the user-facing API slows down. Support also reports duplicate rows in the export, because it sorted by `created_date` and many orders share the same timestamp. Switching the export to keyset paging on an indexed key brought every call back to tens of milliseconds.

**What the interviewer is really checking**
Whether you know that offset paging degrades with depth and that `Page` has a hidden count query. They also want to see that you can choose the right approach for the use case instead of using one default everywhere.

**How I answer it**
1. **Always pass a `Pageable` with an explicit, deterministic sort.** Sort by a unique column, or add a unique tie-breaker such as `ORDER BY created_date, id`. Without that, the database may return tied rows in any order, so pages can overlap or skip rows.
2. **Cap the page size on the server.** Never trust a client sending `size=1000000`. Set a sensible maximum (Spring Data web support has a configurable max page size).
3. **Use offset paging only for shallow, human-driven browsing.** It is simple and allows "jump to page 7", but the database must read and discard all the skipped rows.
4. **For large tables, deep scrolling, exports or "infinite scroll", use keyset paging.** The client sends back the last key it saw, and you query:
   ```sql
   WHERE id > :last ORDER BY id LIMIT 50
   ```
   An index on the sort columns lets the database seek directly to the start. For multi-column sorts, the condition must match the full sort key, for example `(created_date, id) > (:d, :id)`. Spring Data 3.1+ also has a built-in scroll API for keyset scrolling.
5. **Return `Slice` when you don't need a total.** `Slice` avoids the `count(*)`, which on a big table can cost more than the page query itself. Use `Page` only when the UI really shows "page 3 of 800".

**Trade-offs and what can go wrong**
- Keyset paging cannot jump to an arbitrary page number, and it only moves forward (going backward needs extra work).
- It needs an index matching the sort. Without one, it is no faster than offset.
- Sorting by a nullable or non-unique column without a tie-breaker causes skipped or repeated rows.
- With offset paging, rows inserted or deleted between requests shift the pages, which causes duplicates or gaps. Keyset paging is much more resilient to this.
- Fetching a collection with `JOIN FETCH` plus `Pageable` in JPA makes Hibernate page in memory (it logs a warning). Page the parent IDs first, then fetch the children.

**How I'd monitor it**
- Slow-query log and `EXPLAIN` on the paging query. Look for a full scan, or a growing "rows examined" as the offset increases.
- Micrometer timers on repository or endpoint calls, with latency plotted against page number.
- Enable `hibernate.generate_statistics` in a test environment to count queries, and watch for the extra `count` statements.
- In Splunk, search for slow requests where the `page` parameter is high, and for requests with a very large `size`.
- Database CPU and buffer-read metrics during export jobs.

**Follow-ups to expect**
- *Why is `OFFSET 1000000` slow even with an index?* -> The database still has to walk through and discard a million index entries before it returns your 50 rows.
- *When would you still choose `Page`?* -> For small or moderate tables where the UI needs a total and page numbers, and the count is cheap or cached.
- *How do you page a result sorted by a non-unique column with keyset?* -> Add a unique tie-breaker (`id`) to the sort and compare on both columns together.

**60-second answer**
I always use `Pageable` with a deterministic sort, usually a unique column or a column plus `id` as a tie-breaker, so pages never overlap or skip rows. I also cap the page size on the server. Offset paging is fine for small, shallow lists, but it gets slower the deeper you go because the database has to read and discard all the skipped rows. For large tables, exports or infinite scroll, I use keyset paging, which means `WHERE id > :last ORDER BY id LIMIT 50` with an index, so every page costs about the same. I also use `Slice` instead of `Page` when I don't need a total, because `Page` runs an extra `count(*)` that can be expensive. I'd verify it with `EXPLAIN` and latency metrics by page depth.

### Q32 [senior] Why is `equals/hashCode` on JPA entities tricky?
tags: jpa, hibernate, equals-hashcode, entity-proxy, lazy-loading, basics

**Start here: the concepts**
- **`equals` / `hashCode`**: `equals` says whether two objects mean the same thing. `hashCode` is a number used by `HashSet` and `HashMap` to decide which bucket an object goes in. The rule is that equal objects must return the same hash code, and an object's hash code must not change while it sits in a hash collection.
- **JPA entity**: a Java object mapped to a database row. Its **id** is the primary key.
- **Generated id**: with `IDENTITY` or sequence generation, the id is `null` until the entity is persisted or flushed. The database or sequence assigns it then.
- **Proxy**: for lazy loading, Hibernate may hand you a generated subclass of your entity (for example `Order$HibernateProxy`). It holds only the id and loads the row on first access. It is not exactly `Order.class`.
- **Lazy collection**: a `@OneToMany` list that is not loaded until you touch it. Touching it runs a query, and outside a session it throws `LazyInitializationException`.
- **Business key**: a natural identifier from the domain that never changes, such as an ISBN, an order number or an email.

**The live scenario**
A team's order screen added items to a `HashSet<OrderLine>`. Lombok `@Data` generated `hashCode` from all fields. Lines were added before saving, so the hash was computed with `id = null`. After `save()` the id appeared, the hash changed, and `set.contains(line)` returned false. Duplicates then appeared on the page. Separately, the `toString` of an `Order` printed its lines, and each line printed its `Order`. That caused a `StackOverflowError` in the logs, and a 5,000-row export ran 5,000 extra queries.

**What the interviewer is really checking**
Whether you know that an entity's identity changes over its lifecycle (new, persisted, proxied, detached). Also whether you can name the concrete failure modes and give a safe pattern, rather than just saying "use Lombok".

**How I answer it**
1. **Do not use all fields.** Mutable fields change, so the hash changes while the object is in a set and it gets lost. Lazy collections get loaded or recurse.
2. **Prefer a stable business key** if one exists. It is the same before and after persist and across proxies, so `equals` and `hashCode` stay consistent. Alternatively, assign a UUID in the constructor.
3. **If you only have a generated id, compare ids only when non-null.** A new entity with a `null` id is equal only to itself (`this == o`). Two unsaved rows are not the same row.
4. **Return a constant `hashCode`** (such as the class hash) in that case. The id may appear later, and a constant hash never changes, so the object is not lost from a `HashSet`. The cost is that all entities of that type share one bucket, which is acceptable because entity sets are usually small.
5. **Handle proxies.** Use `instanceof`, not `getClass() ==`, because the proxy is a subclass. Compare through getters (`other.getId()`), because the fields of a proxy are empty until it loads.
6. **Keep lazy associations out of `equals`, `hashCode` and `toString`.** Touching them triggers a query or a recursive loop.

```java
@Override public boolean equals(Object o) {
  if (this == o) return true;
  if (!(o instanceof Order other)) return false;
  return id != null && id.equals(other.getId());
}
@Override public int hashCode() { return Order.class.hashCode(); }
```

**Trade-offs and what can go wrong**
- Constant `hashCode` makes huge hash collections slow, so avoid putting tens of thousands of entities in one set.
- A business key breaks if it can change or is not truly unique.
- `@Data`, `@EqualsAndHashCode` and `@ToString` in Lombok include every field by default. Exclude associations or write the methods by hand.
- Using `getClass()` hides the proxy bug: two representations of the same row compare as different.
- Many teams use `List` for associations to avoid the issue, but the correct `equals`/`hashCode` still matters for `Set`, caches and merges.

**How I'd monitor it**
- Enable Hibernate statistics, or log SQL in a test, and watch for query-count spikes (an N+1 pattern) when printing or comparing entities.
- Search Splunk for `StackOverflowError`, `LazyInitializationException` and `HibernateProxy` stack frames near `toString` or `hashCode`.
- Add a unit test: put a new entity in a `HashSet`, persist it, and assert `contains` is still true. Also assert a proxy equals the real entity.

**Follow-ups to expect**
- *Why not just use `getClass()` in `equals`?* -> A proxy has a different class, so the same row would compare as unequal. Use `instanceof` and getters.
- *Is a constant `hashCode` legal?* -> Yes. The contract only needs equal objects to share a hash. It costs performance on large sets but keeps the hash stable across persist.
- *Why not use a generated UUID in the constructor?* -> That is a good option. The id exists from the start, so `equals` and `hashCode` can use it directly. The trade-off is larger keys and index size.

**60-second answer**
Entity identity changes over its life. The id is `null` before persist, and Hibernate may give you a proxy subclass instead of the real class. If `hashCode` uses the id or mutable fields, it changes after save and the entity gets lost in a `HashSet`. If `equals` uses `getClass()`, a proxy and the real object look different. So I use a stable business key, or compare ids only when non-null with a constant `hashCode`. I use `instanceof` and getters so proxies work. I never include lazy collections in `equals`, `hashCode` or `toString`, because that triggers extra queries or endless recursion. I also watch out for Lombok `@Data`, which includes everything by default.

### Q33 [senior] How do you manage schema changes safely?
tags: spring boot, flyway, liquibase, schema migration, expand contract, zero downtime, database, basics

**Start here: the concepts**
- **Schema:** the structure of the database: tables, columns, types, indexes, constraints. Code and schema must agree, or queries fail.
- **Schema change (migration):** a script that moves the schema from one version to the next, such as adding a column.
- **Flyway / Liquibase:** tools that keep numbered migration scripts in source control. They record which scripts have run in a history table (`flyway_schema_history` in Flyway) and apply only the new ones. Every environment ends up with the same schema, and it is traceable.
- **`ddl-auto=update`:** a Hibernate setting that edits the schema automatically from your entity classes. It is unreviewed, can't drop or rename safely, and leaves no history. Fine for a throwaway demo, never for production.
- **Rolling deploy:** new app instances replace old ones gradually. For several minutes, **old and new code run against the same database**.
- **Expand/contract:** change the schema in two safe phases. *Expand* adds new things without breaking old code. *Contract* removes old things once nothing uses them.
- **Backfill:** copying or computing values for existing rows after adding a column.

**The live scenario**
An `orders` table has 120 million rows. A developer ships one migration that renames `phone` to `contact_phone` and makes it `NOT NULL`. The pipeline runs it, but the rename takes a lock and the old pods are still running. For about 10 minutes, 6 old pods throw "column phone does not exist" and checkout returns 500s. A rollback of the app doesn't help, because the old code now has no column to read. The fix was to split the change into small, backward-compatible steps.

**What the interviewer is really checking**
Whether you know that during a deploy two app versions share one database, and whether you can split a risky change into safe steps. They also want to see that you treat migrations as reviewed, versioned code.

**How I answer it**
1. **Use versioned migrations (Flyway or Liquibase), run by the pipeline.** Scripts are reviewed in pull requests and applied identically in every environment. Never edit a migration that has already run, because the tool checksums it and will fail. Add a new one instead.
2. **Never use `ddl-auto=update` in production.** Use `validate` so the app refuses to start if schema and entities disagree.
   ```properties
   spring.jpa.hibernate.ddl-auto=validate
   spring.flyway.enabled=true
   ```
3. **Expand:** add the new column as *nullable*. Old code ignores it, so nothing breaks.
4. **Deploy code that writes to both** the old and new columns. New data stays consistent while old pods still run.
5. **Backfill in small batches** (for example, a few thousand rows per transaction, with pauses). One giant `UPDATE` holds locks and can stall live traffic.
6. **Switch reads** to the new column once the backfill is verified.
7. **Contract in a later release:** only after no running version uses the old column, drop it, and add `NOT NULL` if needed. Waiting means a rollback to the previous app version still works.
8. **Rule for every migration:** it must be compatible with the app version currently running, not just the new one.

**Trade-offs and what can go wrong**
- Zero downtime costs more releases, temporary duplicate data and extra code to maintain.
- Dropping or renaming in the same release as the code change is the classic outage.
- Adding an index or a `NOT NULL` constraint on a huge table can lock it. Use your database's online options (for example, `CREATE INDEX CONCURRENTLY` in PostgreSQL).
- Rolling back the schema is hard. Prefer rolling forward with a fix. Liquibase supports rollback scripts, but they must be written and tested.
- If migrations run at app startup, several instances could start together. Both tools use a lock to prevent this, but running them as a pipeline step is cleaner.

**How I'd monitor it**
- Watch the migration step's status and duration in the pipeline, and the `flyway_schema_history` table (or the Actuator `flyway` endpoint) for failed entries.
- Watch the database for lock waits and long-running queries during the backfill, and for replication lag.
- Watch the 5xx rate and latency during the deploy.
- Search Splunk for `SQLSyntaxErrorException` or "column ... does not exist" after a release.
- Track backfill progress (rows remaining) and alert if it stalls.

**Follow-ups to expect**
- *How do you rename a column safely?* -> Don't rename in place. Add the new column, dual-write, backfill, switch reads, and drop the old one later.
- *What if two instances start at once?* -> Flyway and Liquibase take a database lock, so one runs migrations and the other waits.
- *Can you roll back a migration?* -> It's risky. Design migrations to be backward compatible so you can roll back the app instead, and roll the schema forward with a fix.

**60-second answer**
I keep every schema change as a versioned Flyway or Liquibase script, reviewed and run by the pipeline. I never use `ddl-auto=update` in production, only `validate`. The key point is that during a rolling deploy, old and new code share the database, so each migration must work with both. I use expand/contract: add a nullable column, deploy code that writes to both columns, backfill in small batches, switch reads, and drop the old column in a later release. Big operations like indexes or constraints are done online to avoid long locks. I watch the migration history, database locks and error rates during the deploy, and I prefer rolling forward over rolling back.

### Q34 [senior] How do you do bulk inserts efficiently with JPA?
tags: jpa, hibernate, bulk-insert, jdbc-batching, sequences, persistence-context, performance, basics

**Start here: the concepts**
- **JDBC batching:** The app sends many INSERTs to the database in one network round trip instead of one trip per row. Network round trips are usually the main cost, so this is where the speed comes from.
- **`hibernate.jdbc.batch_size`:** Tells Hibernate how many statements to group into one batch. Without it, Hibernate sends rows one by one.
- **Persistence context (first-level cache):** The in-memory set of entities Hibernate is tracking in the current transaction. It checks each tracked entity for changes at flush time. Every entity you save stays in it until you clear it.
- **Flush:** Hibernate sends its pending SQL to the database. **Clear** detaches all tracked entities so memory can be freed.
- **`IDENTITY` id:** The database generates the id when the row is inserted. Hibernate must insert immediately to learn the id, so it cannot hold rows back and batch them.
- **Sequence and `allocationSize`:** A sequence is a database counter. With `allocationSize=50`, Hibernate reserves 50 ids in one call and assigns them in memory, so inserts can be queued. `allocationSize` must match the sequence's `INCREMENT BY`, or you get id gaps or duplicate-key errors.
- **`order_inserts` / `order_updates`:** Hibernate sorts pending statements by entity type. A batch only holds statements for the same table, so mixed-type inserts would otherwise break it into many tiny batches.

**The live scenario**
A nightly import loaded 500,000 order rows with `saveAll()`. It ran about 55 minutes and the heap kept growing. Statement logs showed one INSERT per row, because the id was `IDENTITY` and no batch size was set. The team switched to a sequence with `allocationSize=50`, set `batch_size=50`, and flushed and cleared every 50 rows. The job dropped to a few minutes with flat memory. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you know that JPA does not batch by default, and why: the id strategy, the persistence context growth and the statement ordering. A senior should also know when to stop using JPA for bulk work.

**How I answer it**
1. **Turn batching on:** set `hibernate.jdbc.batch_size` (for example 50) because the default sends row by row.
2. **Group statements:** set `order_inserts=true` and `order_updates=true` so parent and child inserts do not interleave and split batches.
3. **Avoid `IDENTITY`:** use a sequence generator with `allocationSize` equal to the database increment, because identity forces an immediate insert per row.
4. **Flush and clear every batch,** so the persistence context does not grow to millions of entities and slow every flush.
5. **Commit in chunks** rather than one huge transaction, to limit undo/redo log growth and the cost of a failure.
6. **Know the limits:** for millions of rows, leave JPA and use plain JDBC batch, PostgreSQL `COPY`, or Oracle SQL*Loader (a bulk loader). `MERGE` is Oracle SQL for upserts (insert-or-update) from a staging table.

```properties
spring.jpa.properties.hibernate.jdbc.batch_size=50
spring.jpa.properties.hibernate.order_inserts=true
```

**Trade-offs and what can go wrong**
- If `allocationSize` and the sequence increment disagree, you get duplicate keys or wasted ids.
- Spring Data `save()` on an entity with an assigned id does a SELECT first (it calls `merge`), which adds a query per row.
- Forgetting `clear()` causes memory growth and slower flushes.
- JDBC drivers may need a flag to rewrite batches into multi-row statements, such as `reWriteBatchedInserts=true` (PostgreSQL) or `rewriteBatchedStatements=true` (MySQL).
- MySQL has no native sequences, so `IDENTITY` is common there. Use JDBC batch instead.
- Batching hides row-level errors: one bad row fails the whole batch.
- Bulk loaders bypass entity listeners, auditing and Hibernate-level validation.

**How I'd monitor it**
- Log SQL with datasource-proxy or p6spy to confirm batches of the expected size.
- Compare Hibernate statistics (`hibernate.generate_statistics`, prepared statement count) against the row count.
- Watch heap and GC pauses during the job.
- Track job duration and rows per second in Micrometer, and alert on a regression. Search Splunk for the job's start and end logs.

**Follow-ups to expect**
- *Why does `IDENTITY` disable batching?* -> Hibernate needs the generated id right after each insert, so it must execute immediately instead of queuing.
- *When would you skip JPA entirely?* -> For very large loads, use `JdbcTemplate.batchUpdate`, `COPY` or SQL*Loader, because there is no entity tracking overhead.
- *Is `StatelessSession` an option?* -> Yes. It has no persistence context, so no clearing is needed, but it also has no cascading or caching.

**60-second answer**
JPA does not batch by default, so I enable `hibernate.jdbc.batch_size` and `order_inserts`/`order_updates` so Hibernate groups statements per table. I avoid `IDENTITY` ids because Hibernate must insert each row immediately to get the id. I use a sequence with an `allocationSize` that matches the database increment. Every batch I flush and clear the persistence context so memory stays flat, and I commit in chunks. I verify with SQL logging that batches really happen. For millions of rows I leave JPA and use JDBC batch, PostgreSQL `COPY`, or Oracle SQL*Loader, with `MERGE` if I need upserts.

### Q35 [fresher] How does Spring Security's filter chain work?
tags: spring, spring-security, filter-chain, authentication, authorization, servlet-filter, basics

**Start here: the concepts**
- **Servlet filter:** a piece of code that sees every HTTP request before it reaches your controller, and can inspect, change, or reject it. It exists so cross-cutting work (logging, security) does not have to be repeated in every controller.
- **Filter chain:** several filters lined up in a fixed order. Each one does its job and passes the request to the next, or stops it and returns a response.
- **`SecurityFilterChain`:** Spring Security's own list of security filters for a set of URLs. Spring Security registers one servlet filter (`FilterChainProxy`, reached through `DelegatingFilterProxy`), and that filter picks the matching `SecurityFilterChain` and runs its filters.
- **Authentication:** proving who you are (password, token). The result is an `Authentication` object holding the user and their roles, which is stored in the `SecurityContext` for the rest of the request.
- **Authorization:** deciding what an identified user may do. For example, only `ADMIN` may call `/admin/**`.
- **Lambda DSL:** the style of writing rules as small lambdas, such as `authorizeHttpRequests(a -> ...)`, instead of chained `.and()` calls.
- **`WebSecurityConfigurerAdapter`:** the old base class for configuration. It was deprecated in Spring Security 5.7 and removed in 6.0 (Spring Boot 3). You now declare a `SecurityFilterChain` bean instead.

**The live scenario**
A team added `/api/admin/**`, meant for admins only. A developer wrote `.requestMatchers("/api/**").permitAll()` above the admin rule. Rules are checked top to bottom and the first match wins, so the admin rule never ran. For two days, about 3,000 requests per day reached admin endpoints without login. A Splunk search for 200 responses on `/api/admin/*` with no username caught it. The fix was one line moved, but it showed that the order of rules, and the filter chain itself, must be understood.

**What the interviewer is really checking**
Whether you know security is a pipeline of filters that runs before your controller, and that authentication comes before authorization. Whether you also know the modern configuration style, with a bean and no adapter class.

**How I answer it**
1. **A request arrives and goes through the security filter chain before any controller.** Security sits in front so that unprotected code never runs for an unauthorized caller.
2. **Authentication filters run first.** Examples are the username/password filter, a JWT/bearer-token filter, or HTTP Basic. Each one reads credentials, checks them, and on success puts an `Authentication` into the `SecurityContext`. Authorization needs to know who the caller is, so this must come first.
3. **Authorization comes next.** The authorization filter (`AuthorizationFilter` in Spring Security 6) compares the `Authentication` with your rules from `authorizeHttpRequests`. If the rules allow it, the request moves on.
4. **If a check fails,** the response is 401 when the caller is not identified, or 403 when the caller is known but not allowed. A filter called `ExceptionTranslationFilter` turns the security exception into that response.
5. **If everything passes,** the request reaches the `DispatcherServlet` and then your controller.
6. **I configure it with a `SecurityFilterChain` bean and the lambda DSL:**
```java
@Bean SecurityFilterChain chain(HttpSecurity http) throws Exception {
  http.authorizeHttpRequests(a -> a.requestMatchers("/public/**").permitAll()
      .anyRequest().authenticated());
  return http.build();
}
```
   Rules go from most specific to most general, and `anyRequest()` goes last, because the first match wins.

**Trade-offs and what can go wrong**
- Wrong rule order can leave endpoints open, as in the scenario above.
- Filter order matters. A custom filter placed in the wrong position may run before the authentication it depends on.
- Following older tutorials leads to the removed `WebSecurityConfigurerAdapter`, which fails on Spring Boot 3.
- Forgetting `anyRequest()` can leave some URLs unprotected.
- Every request pays a small cost for passing through the filters. This is acceptable, but a slow custom filter (for example a remote call per request) hurts every endpoint.

**How I'd monitor it**
- In non-production, set `logging.level.org.springframework.security=DEBUG`. It logs the filters in the chain and why a request was allowed or denied.
- Track the Actuator/Micrometer metric `http.server.requests`, tagged by status, and alert on spikes in 401/403.
- Search Splunk for 200 responses on sensitive paths with no authenticated user, and for repeated failed logins from one IP.
- Write `MockMvc` tests that check protected URLs return 401/403 without credentials.

**Follow-ups to expect**
- *What is the difference between 401 and 403?* -> 401 means "I don't know who you are" (not authenticated). 403 means "I know you, but you are not allowed."
- *Can an application have more than one filter chain?* -> Yes. You define several `SecurityFilterChain` beans, each limited to certain URLs (for example `/api/**` with JWT and the rest with a form login), and the first matching chain handles the request.
- *Where is the logged-in user stored?* -> In the `SecurityContext`, reached through `SecurityContextHolder`, normally tied to the current request thread.

**60-second answer**
Spring Security puts a chain of servlet filters in front of my controllers. A request first meets the authentication filters, which read credentials such as a password or a JWT and, if valid, store an `Authentication` object saying who the user is. Then the authorization filter checks that user against my `authorizeHttpRequests` rules. If it fails, the caller gets 401 when unidentified or 403 when not allowed. If it passes, the request reaches the controller. Today I configure this with a `SecurityFilterChain` bean and the lambda DSL, because `WebSecurityConfigurerAdapter` was removed in Spring Security 6. Rule order matters because the first match wins, so I put specific rules first and `anyRequest()` last.

### Q36 [mid] Authentication vs authorization; sessions vs JWT?
tags: spring-security, authentication, authorization, sessions, jwt, basics

**Start here: the concepts**
- **Authentication (authn):** proving who you are, for example with a password or a login via an identity provider. It answers "who is this?"
- **Authorization (authz):** deciding what an already-identified user may do, such as "can this user refund an order?" It answers "is this allowed?" It always runs after authentication.
- **Why HTTP needs help:** HTTP is stateless, so every request arrives with no memory of the last one. We need a way to carry "this user is already logged in" from request to request.
- **Session:** after login, the server stores the user's state in memory or a store and gives the browser a random session ID, usually in a cookie. Each request sends the ID and the server looks the state up.
- **Sticky session / shared store:** with several servers, a request must reach the server that holds the session (sticky), or all servers must read sessions from one shared place such as Redis.
- **JWT (JSON Web Token):** a signed string that carries the user's identity and claims inside it. The server checks the signature instead of looking anything up, so it needs no stored state. It is signed, not encrypted, so anyone can read the payload. Never put secrets in it.
- **Claims:** `exp` is the expiry time, `iss` is the issuer (who created the token), and `aud` is the audience (who it is meant for).
- **Access token / refresh token:** the access token is short-lived and sent on every API call. The refresh token is long-lived and used only to get a new access token.
- **Revocation list:** a list of tokens or users that are blocked even though the tokens have not expired.

**The live scenario**
An e-commerce API runs 12 pods behind a load balancer at about 3,000 requests per second. It uses server sessions in a single Redis, and every request costs one extra Redis lookup. During a sale, Redis latency rises and API p99 goes from 120 ms to 900 ms. The team moves to JWTs with a 10-minute lifetime, which removes the lookup. Then security reports a stolen laptop, and the team realises they cannot kill the thief's token for up to 10 minutes. They add a small revocation check for high-risk cases.

**What the interviewer is really checking**
Whether you separate the two ideas cleanly, and whether you understand the real trade-off: state and easy revocation versus statelessness and scale. A mid-level candidate should also know what must be validated on a JWT.

**How I answer it**
1. **Define the two terms first.** Authentication is who you are, authorization is what you may do. They are different steps, and in Spring Security they fail differently: 401 for not authenticated, 403 for authenticated but not allowed.
2. **Explain sessions.** The server keeps the state, so logout or a ban takes effect immediately. The cost is that every server needs access to that state, through sticky routing or a shared store, and that store becomes a dependency.
3. **Explain JWT.** The token carries the claims and is signed, so any service with the key can verify it without a lookup. This scales easily across pods and microservices.
4. **Name the weakness.** A valid JWT stays valid until `exp`, so you cannot easily revoke it.
5. **Give the fix.** Use a short-lived access token (minutes) plus a refresh token. Revoking the refresh token stops new access tokens from being issued. For urgent cases, keep a revocation list that is checked on each request.
6. **Always validate** the signature, `exp`, `iss` and `aud`. Without these checks, a forged, expired or wrong-audience token could be accepted. Also pin the allowed signing algorithm.
```
spring.security.oauth2.resourceserver.jwt.issuer-uri=https://idp.example.com
```
With Spring Security's resource server, this checks the signature, expiry and issuer. The `aud` check needs a custom validator.

**Trade-offs and what can go wrong**
- Sessions: a shared store is a scaling bottleneck and a single point of failure. Cookies also need CSRF protection.
- JWT: a revocation list brings back state and partly defeats the point. A very short TTL means more refresh traffic.
- Large tokens make every request heavier.
- Storing tokens in browser localStorage exposes them to XSS.
- Mistakes: putting secrets in the payload, skipping `aud` validation, and accepting the `none` algorithm.

**How I'd monitor it**
- Track the 401 and 403 rate per endpoint, and alert on spikes.
- Log token validation failures by reason (expired, bad signature, wrong audience) and search for them in Splunk.
- Watch session-store latency, memory and hit rate.
- Track the refresh-token rate and revocation-list size.
- Use Actuator and Micrometer for the HTTP status metrics.

**Follow-ups to expect**
- *Where should a browser keep a JWT?* -> An HttpOnly, Secure cookie is safer against XSS than localStorage, but then you must handle CSRF, for example with SameSite.
- *Is a JWT encrypted?* -> No. It is signed, so it cannot be changed, but anyone can read it. Use JWE or keep sensitive data out of it.
- *Is JWT always better for microservices?* -> No. If you need instant revocation or very small tokens, sessions or opaque tokens with introspection can be the better choice.

**60-second answer**
Authentication is proving who you are, and authorization is deciding what you are allowed to do after that. With sessions, the server stores the user's state and gives the browser an ID. Logout and revocation are instant, but the servers need sticky routing or a shared store like Redis. With JWT, the token carries signed claims, so any service can verify it without a lookup, and that scales easily. The weakness is that a JWT stays valid until it expires, so I use a short-lived access token plus a refresh token, and a revocation list for urgent cases. I always validate the signature, `exp`, `iss` and `aud`. I remember that a JWT is signed, not encrypted, so I never put secrets in it.

### Q37 [mid] Explain OAuth2 / OIDC flows you would use.
tags: oauth2, oidc, jwt, pkce, spring-security, resource-server, basics

**Start here: the concepts**
- **OAuth2**: a standard that lets an app get limited access to an API *without* handling the user's password. The app receives a token instead.
- **OIDC (OpenID Connect)**: a thin layer on top of OAuth2 that adds *login*, meaning "who is this user?". OAuth2 alone only says what an app may do. OIDC adds an **ID token** that describes the user.
- **IdP (identity provider)**: the server that authenticates users and issues tokens, such as Keycloak, Microsoft Entra ID (formerly Azure AD), Okta or Cognito.
- **Access token**: a short-lived "key" the client sends to an API. Often it is a **JWT**, a signed, self-describing token the API can check without calling the IdP each time.
- **Refresh token**: a longer-lived token used only to get a new access token quietly, so the user doesn't log in every few minutes.
- **Grant/flow**: the step-by-step way a client obtains a token.
- **Authorization Code flow**: the browser is sent to the IdP to log in, and the app gets back a one-time *code*, which it exchanges for tokens over a direct back-channel call.
- **PKCE**: the app invents a random secret, sends only its hash at the start, and reveals the original when exchanging the code. A stolen code is then useless. It exists because SPAs and mobile apps can't keep a client secret.
- **Client Credentials flow**: a service logs in as itself using its own ID and secret, with no user involved.
- **Resource server**: your API. It doesn't log anyone in; it only validates tokens.
- **Scopes/roles**: labels inside the token such as `orders:read` that say what the caller may do.

**The live scenario**
A shop has a React SPA (about 20,000 daily users) and 12 microservices. The SPA used the implicit flow, so access tokens came back in the URL. A security review found tokens in browser history and proxy logs. Separately, a nightly batch job called the order API with a shared user's password. The team moved the SPA to Authorization Code + PKCE and gave the batch job its own client with Client Credentials. Tokens left the URLs, and the shared password disappeared.

**What the interviewer is really checking**
Whether you can match the flow to the type of caller (user or machine), and whether you know that the API only validates tokens and never handles login.

**How I answer it**
1. **User logs in (SPA, mobile, web): Authorization Code + PKCE.** The password goes only to the IdP, and the code exchange happens on a direct call, so tokens never pass through the URL. PKCE protects public clients that can't hold a secret. Adding the `openid` scope makes it OIDC and returns an ID token.
2. **Service-to-service: Client Credentials.** No user is present, so the service authenticates as itself and gets a token with its own scopes.
3. **Renewal: refresh token.** Access tokens stay short-lived (minutes) to limit damage if stolen, and the refresh token gets new ones silently. Rotate refresh tokens and store them carefully.
4. **Never use the implicit flow.** It puts tokens in the URL and has no code-exchange protection. Current security guidance deprecates it.
5. **The API is a resource server.** It checks the signature (using the IdP's public keys), issuer, audience and expiry, then reads scopes/roles for authorization. In Spring Boot, `spring-boot-starter-oauth2-resource-server` does this:
```yaml
spring.security.oauth2.resourceserver.jwt.issuer-uri: https://idp.example.com/realms/shop
```
6. **Authorize with scopes/roles**, for example method security such as `@PreAuthorize("hasAuthority('SCOPE_orders:read')")`.

**Trade-offs and what can go wrong**
- A JWT can't be recalled before it expires, so keep lifetimes short or add revocation/introspection for sensitive APIs.
- Skipping the audience check means a token meant for another API gets accepted.
- Storing tokens in browser local storage exposes them to XSS. Many teams use a backend-for-frontend (BFF) that keeps tokens server-side.
- Client secrets in source code or images leak. Use a secret store.
- Clock skew and IdP key rotation can cause sudden 401s.

**How I'd monitor it**
- Track 401/403 rates per endpoint, using Micrometer's `http.server.requests` by status.
- Search Splunk for token validation failures, grouped by reason (expired, bad issuer, bad audience).
- Watch IdP latency and availability, since login and key fetches depend on it.
- Alert on spikes in token requests from one client, which can signal a leaked secret or a retry loop.

**Follow-ups to expect**
- *ID token vs access token?* -> The ID token is for the client, to learn who logged in. The access token is for the API, to say what is allowed. Don't send ID tokens to APIs.
- *Why PKCE if there's already a code?* -> An attacker who intercepts the code can't redeem it without the original random secret.
- *How do you log a user out or revoke access?* -> Revoke the refresh token at the IdP and keep access tokens short. For immediate cutoff, use token introspection.

**60-second answer**
OAuth2 gives apps tokens instead of passwords, and OIDC adds login and an ID token on top. For users on a SPA, mobile or web app, I use Authorization Code with PKCE, because the password stays at the IdP and PKCE protects apps that can't keep a secret. For service-to-service calls I use Client Credentials, where the service authenticates as itself. Short-lived access tokens are renewed with refresh tokens, and I never use the implicit flow because it exposes tokens in the URL. My Spring Boot API is a resource server: it validates the JWT signature, issuer, audience and expiry against the IdP, then authorizes using scopes or roles. I'd monitor 401/403 rates and token validation failures in Splunk.

### Q38 [senior] Method security and common vulnerabilities to mention?
tags: spring-security, method-security, preauthorize, owasp, idor, access-control, basics

**Start here: the concepts**
- **Authentication vs authorization:** Authentication asks "who are you?". Authorization asks "what may you do?". Method security is authorization, applied at the Java method.
- **Method security:** Rules written as annotations on service methods, such as `@PreAuthorize` (checked before the call) and `@PostAuthorize` (checked after, using the return value). It exists because URL rules alone can't express "only the owner may read this record". In Spring Security 6 you turn it on with `@EnableMethodSecurity`. The older `@EnableGlobalMethodSecurity` is deprecated.
- **SpEL (Spring Expression Language):** The small expression language inside the annotation. `hasRole('ADMIN')` checks the user's authorities (Spring adds the `ROLE_` prefix). `#id` refers to the method parameter named `id`, which needs parameter names kept at compile time (`-parameters`, which Spring Boot's build plugins normally set). `authentication.name` is the logged-in username.
- **Proxy:** Spring wraps your bean in a stand-in object that runs the security check, then calls your method. Calls from inside the same class skip the proxy, so the check is skipped too.
- **OWASP:** A non-profit that publishes lists of the most common web and API security flaws, used as a shared checklist.
- **IDOR (Insecure Direct Object Reference):** The user changes an ID in a request and reaches someone else's data. It is a form of broken access control.
- **Mass assignment:** The framework copies all incoming JSON fields onto your object, so a client can set fields like `role` or `balance`.
- **SSRF (Server-Side Request Forgery):** An attacker makes your server fetch a URL they choose, for example internal services or cloud metadata.
- **CSRF, CORS, SBOM:**
  - CSRF: a malicious site makes the browser send a request with the user's cookie.
  - CORS: browser rules on which other sites may call your API.
  - SBOM: a Software Bill of Materials, the list of every library you ship.

**The live scenario**
An orders API serves 40,000 customers. `GET /orders/{id}` only required a logged-in user. One customer changed 1001 to 1002 in the URL and saw a stranger's order. Over a weekend a script pulled about 12,000 orders. Roles were fine, since everyone was a valid USER, but nobody checked ownership. The fix was an ownership rule at the service layer, plus alerts on the pattern.

**What the interviewer is really checking**
Whether you know that a role check is not enough, and that you check ownership of the specific record. They also want to see that you know how method security works (proxies) and can name common vulnerabilities with a concrete defence for each.

**How I answer it**
1. **Turn on method security and write the rule next to the business method.**
   ```java
   @PreAuthorize("hasRole('ADMIN') or #id == authentication.name")
   public Profile getProfile(String id) { ... }
   ```
   Admins pass by role, and everyone else passes only if the ID is their own. Putting the rule on the service means every caller (controller, job, message listener) is covered.
2. **Check ownership, not just roles.** For database records use `@PostAuthorize` on the returned object, or filter in the query (`WHERE owner = :user`). Without this you get IDOR.
3. **Prevent injection.** Use parameterised queries so user input is never treated as SQL.
4. **Prevent mass assignment.** Bind requests to small DTOs that contain only the fields a client may set, never straight to entities.
5. **Block SSRF.** Allow-list the hosts your server may call.
6. **Fix misconfiguration, dependencies and secrets.** Use secure defaults and no debug endpoints open. Produce an SBOM and scan with Dependabot or Snyk. Keep secrets in a vault or environment, never in code.
7. **Add the web-layer protections.**
   - CSRF protection is needed for cookie sessions. A stateless API using a header token usually doesn't need it.
   - Use a CORS allow-list, not `*`.
   - Apply rate limiting.
   - Set security headers.

**Trade-offs and what can go wrong**
- Self-invocation, or annotating private methods, silently skips the check because the proxy is bypassed.
- Forgetting to enable method security means annotations do nothing, with no error.
- Complex SpEL is hard to test, so move big rules into a bean (`@authz.canView(#id)`).
- Ownership checks add a query or filter cost.
- Roles alone give false confidence.
- Scanners flag many low-risk dependency alerts, so triage them or the team ignores them all.

**How I'd monitor it**
- Track 401/403 rates per endpoint in Micrometer (`http.server.requests` by status), and alert on spikes.
- Log authorization-denied events (Spring Security publishes them; the event name varies by version).
- In Splunk, search for one user requesting many sequential IDs, which signals IDOR scraping.
- Watch the 429 rate for rate limiting.
- Run dependency scans in CI and fail the build on critical findings.
- Add tests that call an endpoint as user A for user B's data and expect 403.

**Follow-ups to expect**
- *Why did my `@PreAuthorize` not fire?* -> Most likely a self-invocation or private method (proxy bypassed), or method security wasn't enabled.
- *401 vs 403?* -> 401 means not authenticated. 403 means authenticated but not allowed.
- *Do JWT APIs need CSRF protection?* -> Generally not, when the token is sent in a header and not an automatic cookie. Cookie-based auth does need it.

**60-second answer**
Method security means putting authorization rules on service methods with `@PreAuthorize`, after enabling it with `@EnableMethodSecurity`. A role check isn't enough, so I also check that the caller owns the record, which stops IDOR. Then I walk the OWASP list: parameterised queries for injection, DTOs against mass assignment, allow-lists against SSRF, and secure configuration. I add SBOM scanning for vulnerable dependencies and keep secrets out of code. At the web layer I use CSRF protection for cookie sessions, a CORS allow-list, rate limiting and security headers. I remember that proxies skip self-invocation, and I watch 403 spikes and sequential-ID access in Splunk.

### Q39 [architect] Design authentication/authorization for a set of microservices.
tags: spring-security, oauth2, jwt, microservices, zero-trust, mtls, api-gateway, basics

**Start here: the concepts**
- **Authentication (authN) vs authorization (authZ):** authN answers "who are you?", authZ answers "what may you do?". They are separate decisions, and both are needed.
- **Identity provider (IdP):** a central server (Keycloak, Okta, Entra ID) that logs users in and issues tokens. Login logic lives in one place, not in 40 services.
- **OAuth2 / OpenID Connect:** OAuth2 is the standard for issuing access tokens. OpenID Connect adds a standard way to say who the user is.
- **JWT (JSON Web Token):** a signed token containing claims: user id (`sub`), issuer (`iss`), audience (`aud`, the service it is meant for), expiry (`exp`), and roles or scopes. A service can verify it offline using the IdP's public key, without calling the IdP on every request.
- **JWKS:** a URL where the IdP publishes its current public signing keys. Services download and cache them, so keys can be rotated without redeploying.
- **Resource server:** any service that protects its API by validating incoming tokens. Spring Security has built-in support.
- **API gateway:** the single entry point for outside traffic. It does coarse checks, rate limiting and routing.
- **Zero trust:** being "inside the network" is not proof of anything. Every service checks every call.
- **Client-credentials grant:** a service gets a token for itself (not a user) by proving its own id and secret to the IdP.
- **mTLS (mutual TLS) / service mesh:** both sides of a connection present certificates, so each proves its identity. A mesh (Istio, Linkerd) automates this with sidecar proxies.
- **Least privilege:** give each user or service only the permissions it needs.
- **TTL:** token lifetime. Short lifetimes limit damage if a token leaks.

**The live scenario**
A platform has 40 services and about 3,000 requests per second at the gateway. The gateway validated JWTs, and the services behind it trusted anything on the internal network. An attacker exploited a low-priority reporting service and called the payment service directly. It had no checks, so the attacker pulled customer data for roughly two hours before anyone noticed. The fix was to make every service validate tokens, give services their own identities, and log every access decision.

**What the interviewer is really checking**
Whether you treat security as layered (edge, service, service-to-service) rather than "the gateway handles it". Also whether you can separate user identity from workload identity and handle token lifetime and key rotation.

**How I answer it**
1. **Use a central IdP with OAuth2/OIDC.** Users log in once, and no service stores passwords or builds its own login.
2. **The gateway validates the JWT at the edge** (or passes it on). It rejects bad traffic cheaply and applies rate limits, but it is not the only gate.
3. **Every service is also a resource server and re-validates the token.** Check signature, issuer, audience and expiry. This is zero trust: if the gateway is bypassed or a neighbour is compromised, the service still defends itself.
   `spring.security.oauth2.resourceserver.jwt.issuer-uri=https://idp.example.com/realms/shop`
4. **Propagate user identity in the token, not custom headers** such as `X-User-Id`. Headers can be forged by any caller that reaches the service, whereas a signed token cannot be altered. Where needed, exchange the token for a narrower one aimed at the downstream service (OAuth2 token exchange).
5. **Service-to-service calls:** use client-credentials tokens for a service's own identity, or mTLS via a mesh. mTLS proves which workload is calling, but it carries no user context and no permissions. Authorization still comes from tokens and policy.
6. **Authorize centrally defined, enforce locally.** Define roles and scopes centrally, and enforce them in each service (for example `@PreAuthorize`). Grant least privilege.
7. **Short TTL and key rotation.** Use access tokens of a few minutes. A JWT cannot be recalled once issued, so a short life is the revocation strategy. Services fetch new keys from JWKS.
8. **Secrets in a vault** (client secrets, private keys), never in Git or images. **Audit-log** who accessed what.

**Trade-offs and what can go wrong**
- Validating at every hop adds a little CPU (signature checks are cheap) and more configuration.
- Short TTLs mean more refreshes and more load on the IdP. The IdP becomes a critical dependency, so cache the JWKS and run it highly available.
- Forgetting to check `aud` lets a token meant for one service work on another.
- Roles inside a JWT go stale until the token expires.
- Forwarding the user's token everywhere gives every downstream service full user power. Prefer token exchange or narrow scopes.
- A mesh gives encryption and workload identity but no business authorization.

**How I'd monitor it**
- Alert on spikes in 401/403 per service, and on JWT validation failures by reason (expired, bad signature, wrong audience).
- Track IdP latency and availability, and JWKS fetch errors.
- Search Splunk audit logs for denied calls, and for unusual service-to-service pairs or calls without a user token.
- Alert on certificates and secrets nearing expiry.

**Follow-ups to expect**
- *How do you revoke a token before it expires?* -> Keep TTLs short. For emergencies, add a deny list or use token introspection for sensitive APIs, accepting the extra call.
- *Gateway validation or per-service validation?* -> Both. The gateway gives cheap early rejection, and services give defence in depth.
- *Why not just use mTLS everywhere?* -> It authenticates workloads but says nothing about the end user or their permissions.

**60-second answer**
I use a central identity provider with OAuth2 and OIDC. The gateway validates the JWT at the edge, but every service also acts as a resource server and checks signature, issuer, audience and expiry, because being inside the network proves nothing. User identity travels in the signed token, never in custom headers. For service-to-service calls, services use client-credentials tokens or mTLS from a mesh, and I narrow tokens by audience or token exchange. Roles are defined centrally with least privilege and enforced in each service. Tokens live a few minutes, keys rotate through JWKS, secrets sit in a vault, and I audit-log every access decision and alert on spikes in 401/403 and validation failures.

### Q40 [mid] How do you protect sensitive data in the database and logs?
tags: security, encryption, pii, logging, spring-boot, secrets, basics

**Start here: the concepts**
- **Sensitive data / PII**: information that causes harm if leaked, such as passwords, card numbers, emails, phone numbers and national IDs. PII means personally identifiable information.
- **Encryption at rest**: data is stored scrambled on disk, so someone who steals a disk or a backup file cannot read it. **TDE** (Transparent Data Encryption) is the database doing this for you automatically. Disk encryption does the same at the storage level. Neither helps if an attacker logs in through the application or with a valid DB account, because the database decrypts for them.
- **Column-level encryption**: the application encrypts specific fields (for example a national ID) before saving them. Even a DB admin or a SQL-injection attacker sees only ciphertext.
- **Envelope encryption and KMS**: a KMS (Key Management Service, such as AWS KMS or Vault) guards a master key that never leaves it. For each record or batch you generate a small data key, encrypt the data with it, then have the KMS encrypt the data key and store that next to the data. This is fast, and rotating the master key means re-wrapping small keys, not re-encrypting all the data.
- **Hashing vs encrypting**: encryption can be reversed with a key. A hash is one-way. Passwords must be hashed so that nobody, including you, can recover them. **bcrypt** and **argon2** are deliberately slow and add a random salt, which makes brute-forcing stolen hashes expensive.
- **Masking**: replacing part of a value, such as `j***@mail.com` or `**** **** **** 1234`.
- **Least privilege**: each service gets its own DB user with only the permissions it needs.
- **Credential rotation**: regularly replacing passwords and API keys so a leaked one stops working.

**The live scenario**
A payments service handles about 2 million requests a day. During an incident, someone turned on DEBUG logging for HTTP requests. Three days later, a security review searching Splunk found full email addresses and `Authorization: Bearer` tokens in millions of log lines, readable by 200 people. Separately, a production DB backup had been restored in a test environment. The disk was encrypted, but the shared service account could read everything. The team had to purge the logs, rotate every exposed token and key, and report it. Data protection is needed in the database and in the logs.

**What the interviewer is really checking**
Whether you think in layers (storage, application, logs, access, secrets) rather than just saying "encrypt it", and whether you know the difference between hashing and encrypting.

**How I answer it**
1. **Classify the data first.** I list which fields are secret, personal or harmless. Reason: you cannot protect everything equally, and encryption costs performance and complexity.
2. **Encrypt at rest** with TDE or disk encryption. Reason: it is cheap and covers stolen disks and backups, but I state its limit: it does not stop a legitimate-looking query.
3. **Encrypt high-risk columns** (PII) in the application with envelope encryption through a KMS. Reason: this protects against SQL injection and over-curious DB users, and the master key stays out of the app and the database.
4. **Hash passwords** with bcrypt or argon2, never encrypt them. In Spring Security, `PasswordEncoder` does this:
   ```java
   PasswordEncoder enc = PasswordEncoderFactories.createDelegatingPasswordEncoder();
   ```
   Reason: a hash cannot be reversed, and the salt and slowness defeat precomputed and brute-force attacks.
5. **Mask PII in logs and never log tokens or card data.** I use a Logback converter or a log-sanitising layer, and I watch entity `toString()` methods and request or header logging. Reason: logs are copied widely, kept for a long time and readable by many people. For cards, I avoid storing the number at all and use the payment provider's token. Never store the CVV.
6. **Give each service its own DB user** with only the needed permissions, no DDL rights and no shared admin account. Reason: it limits the damage when one service is compromised.
7. **Keep secrets out of code and config files.** They go in a secrets manager and are **rotated** on a schedule and after any suspected leak. My API-key rotation work is a good example: issue a new key, support old and new in parallel for a short window, then revoke the old one. Reason: this rotates without downtime, and a leaked key stops being useful.

**Trade-offs and what can go wrong**
- Encrypted columns cannot be searched or indexed normally. Use a separate blind index (a keyed hash) for exact-match lookups.
- Every KMS call adds latency and a dependency. Cache data keys briefly.
- Losing the key means losing the data, so back up and control key access carefully.
- Common mistakes: hashing with fast algorithms like plain SHA-256, masking in one log format but not another, secrets in `application.yml` or Git, and Actuator endpoints such as `/env` exposing config. Recent Spring Boot versions hide values by default, but check your version and settings.
- Data in test environments and backups needs the same care as production.

**How I'd monitor it**
- Scheduled Splunk searches for patterns such as card numbers (with a Luhn check), `Bearer ey...` and email regexes, with an alert on any hit.
- DB audit logs for unusual queries or logins, and alerts on access from unexpected accounts.
- KMS and secrets-manager access logs, and alerts when a key or secret is nearing its rotation age.
- Secret scanning in CI to catch credentials in Git.

**Follow-ups to expect**
- *Why not encrypt passwords?* -> Encryption can be reversed if the key leaks. Hashing with salt cannot, so stolen data stays hard to crack.
- *Does TDE protect against SQL injection?* -> No. The database decrypts data for any authorised query, so you need column encryption, parameterised queries and least privilege.
- *How do you rotate a DB password with no downtime?* -> Use dynamic or dual credentials: create the new one, roll the services over, then revoke the old one.

**60-second answer**
I first classify which data is sensitive, then protect it in layers. The disk or database is encrypted at rest, which covers stolen disks and backups. High-risk fields like PII get column encryption with envelope encryption through a KMS. Passwords are hashed with bcrypt or argon2, not encrypted. In logs, I mask PII and never write tokens or card data, because logs spread widely. Each service has its own least-privilege DB user, and secrets live in a secrets manager and are rotated. In my API-key rotation work, I ran old and new keys side by side and then revoked the old one. I monitor with Splunk searches for leaked patterns and with audit logs.

### Q41 [architect] Design the data access layer so that the service can later move from Oracle to PostgreSQL (or add Couchbase).
tags: spring-data, repository-pattern, hexagonal-architecture, database-migration, flyway, testcontainers, basics

**Start here: the concepts**
- **Data access layer:** the code that reads and writes the database. It exists so the rest of the app does not care how data is stored.
- **Repository interface:** a Java interface in the domain layer that describes what the business needs, such as `findOpenOrdersByCustomer(id)`. It says nothing about SQL or tables.
- **Infrastructure implementation:** the class that implements that interface using JPA, JDBC or the Couchbase SDK. Only this class knows the database.
- **Vendor SQL:** SQL that works on one database only, such as Oracle `ROWNUM` or `NVL`, or PostgreSQL `ILIKE`. It breaks on a different database.
- **Domain object vs JPA entity:** a domain object holds business rules. A JPA entity is a class shaped by annotations (`@Table`, `@OneToMany`) to fit a relational table. Mapping between them keeps the business model free of persistence details.
- **Flyway:** a tool that applies versioned SQL migration scripts to the schema in order. Table definitions differ per vendor, so you may need separate script folders.
- **Contract test:** one test suite that every repository implementation must pass. It proves they behave the same.
- **Testcontainers:** a library that starts a real database in Docker during tests, so you test against the real engine rather than a fake such as H2.

**The live scenario**
A payments service handles 800 requests per second on Oracle. Licensing is renewal-critical, so management wants PostgreSQL in 9 months, and a new read-heavy profile feature may go to Couchbase. The service has 140 native Oracle queries scattered across services, and `@Entity` classes are returned directly in REST responses. A spike on one query shows the cost. Oracle treats an empty string as NULL, PostgreSQL does not, so the same code gives different results. The estimate is 6 months of rewrite and regression testing, when it should be a few weeks of work in one package.

**What the interviewer is really checking**
Whether you can isolate a volatile dependency without pretending it is free. A good answer also admits that abstractions leak, and that NoSQL is not a drop-in replacement for relational storage.

**How I answer it**
1. **Define repository interfaces in the domain layer, implement them in infrastructure.** The dependency then points inward, so services never import JPA, JDBC or Couchbase types. This is what makes a swap possible. Do not let the domain interface extend `JpaRepository`, because that leaks Spring Data.
2. **Shape the methods around business use cases, not tables.** Prefer `findOpenOrdersByCustomer` to generic query builders. Relational joins do not exist in Couchbase, and use-case methods can be implemented either way.
3. **Keep vendor SQL out of services and in one place.** Use JPQL or Criteria queries first. Where native SQL is needed, keep it inside the infrastructure package so a migration touches one place.
4. **Map entities to domain objects.** The domain model then has no JPA annotations, and each store can have its own persistence model, such as a JSON document for Couchbase. The cost is mapping code, so MapStruct helps.
5. **Use Flyway with per-vendor script folders when dialects differ.** For example, `db/migration/{vendor}` selects the right folder for the connected database. Keep shared scripts to a minimum and review dialect-specific types such as Oracle `NUMBER` vs PostgreSQL `numeric`.
6. **Write contract tests and run them against each database with Testcontainers.** The same suite runs against Oracle and PostgreSQL containers. It catches differences such as empty-string/NULL handling, pagination and sort order, and locking behaviour before production does.
7. **Keep `@Transactional` at the application-service layer, not in repositories.** Business use cases define the transaction boundary. Be explicit that Couchbase transactions work differently, so do not assume multi-document atomicity.

**Trade-offs and what can go wrong**
- Abstractions leak: sequences vs identity columns, isolation levels, locking, case sensitivity and date handling all differ.
- A "least common denominator" interface wastes database strengths. Allow vendor-specific adapters behind the same interface where performance matters.
- Mapping adds code and a small runtime cost.
- Oracle test containers are large and slow, and licensing needs checking. Run the full matrix in CI nightly and a fast PostgreSQL subset on each commit.
- Do not over-engineer if no migration is realistic. For an architect, the answer is to pay for isolation where the change is likely.

**How I'd monitor it**
- Compare query latency (p95/p99) and error rates before and after a migration, using Micrometer timers on repository calls.
- Watch the connection pool metrics (`hikaricp.connections.active`, `pending`) for exhaustion.
- Search Splunk for slow-query logs and SQL exceptions, split by database vendor.
- Track contract-test pass rates per vendor in CI.
- Run both databases in parallel during cut-over, compare read results (shadow reads), and alert on mismatches.

**Follow-ups to expect**
- *Does JPA already make you database-independent?* -> Only partly. Hibernate dialects hide basic syntax, but native queries, locking and type behaviour still differ, so you still need contract tests.
- *Why not test with H2?* -> H2 is not the real engine, and its behaviour differs from Oracle and PostgreSQL, so it can pass tests that fail in production.
- *How does Couchbase change the design?* -> You model aggregates as documents, avoid joins, and design for the access pattern. Transactions and consistency are weaker or different, so the repository interface must not promise relational behaviour.

**60-second answer**
I put repository interfaces in the domain layer and implement them in an infrastructure package, so the service never sees JPA, JDBC or Couchbase types. I design the methods around business use cases, not tables, so a document store can implement them too. Any vendor SQL stays in that one package, and I map JPA entities to domain objects so the business model has no persistence annotations. For schema changes I use Flyway with per-vendor script folders where the dialects differ. I run one contract test suite against every database with Testcontainers, because that catches real differences such as Oracle treating an empty string as NULL. The abstraction is not free, since it adds mapping code and still leaks, but it turns a migration from a rewrite into a contained change.

### Q42 [mid] What is the difference between Spring and Spring Boot?
tags: spring, spring-boot, auto-configuration, starters, actuator, dependency-injection, basics

**Start here: the concepts**
- **Spring Framework:** a Java library for building applications out of many small objects without hand-wiring them. It is the foundation.
- **Dependency injection (DI) / IoC:** instead of a class creating the objects it needs with `new`, Spring creates them and hands them in. This makes code easier to test and swap.
- **AOP (aspect-oriented programming):** a way to add behaviour such as transactions or logging around methods without editing them. Spring does this with proxies, wrapper objects that intercept calls.
- **Transaction:** a group of database operations that either all succeed or all roll back. Spring lets you declare this with `@Transactional`.
- **Web MVC:** Spring's module for handling HTTP requests with controllers, including REST endpoints.
- **Integration abstractions:** common Spring APIs over messaging, databases and so on (for example `JdbcTemplate`), so your code does not depend on a specific vendor.
- **Spring Boot:** a layer on top of Spring that removes setup work. It exists because plain Spring needed a lot of manual configuration.
- **Auto-configuration:** Boot looks at the libraries on your classpath and creates sensible default beans (objects Spring manages). For example, if a database driver is present, it sets up a `DataSource`. Your own definitions override the defaults.
- **Starter dependency:** one dependency (such as `spring-boot-starter-web`) that pulls in a tested, compatible set of libraries.
- **Externalized configuration:** settings live outside the code (`application.yml`, environment variables, profiles), so one build runs in dev and prod.
- **Embedded server:** Tomcat (or similar) runs inside your app, so you start it with `java -jar`.
- **Actuator:** built-in operational endpoints for health, metrics and environment info.

**The live scenario**
A team of 6 must launch a new payment-notification service in a week. The older services are plain Spring: XML and Java config for the data source, the MVC setup and transaction manager, with a WAR deployed to a shared Tomcat. Setup takes about 3 days, and one library version clash causes a startup failure. Meanwhile Kubernetes needs a health check. The new service uses Boot with starters, so the app runs as a JAR, and the health endpoint comes from Actuator. The first deployable version is ready on day 1. The business logic is still Spring DI, transactions and MVC. Boot only removed the setup work.

**What the interviewer is really checking**
Whether you know Boot is not a competing framework, and whether you can explain what it automates (config, dependencies, running, operations) rather than just saying "it's easier".

**How I answer it**
1. **Start with the relationship.** Spring Framework is the core: DI, AOP, transactions, Web MVC and integration abstractions. Boot is built on it and does not replace it. Every Boot app is a Spring app.
2. **Name what Boot adds, one by one.** Auto-configuration, starters, externalized configuration, embedded server and Actuator. Each one removes a manual step from plain Spring.
3. **Explain the mechanism behind auto-configuration.** Boot checks conditions such as "is this class on the classpath?" and "has the user defined this bean?". If you defined your own bean, Boot's default backs off.
4. **Show the entry point.**
```java
@SpringBootApplication // = @Configuration + @EnableAutoConfiguration + @ComponentScan
```
This one annotation enables component scanning and auto-configuration.
5. **Close with a practical contrast.** Plain Spring means you assemble and deploy; Boot means you run a JAR with sensible defaults.

**Trade-offs and what can go wrong**
- Auto-configuration can feel like magic. When a bean is unexpectedly present or missing, you need to know how to see why.
- Starters can pull in more libraries than you need, which increases startup time and memory.
- Exposing all Actuator endpoints publicly leaks internal details. Expose only what is needed and secure it.
- Wrong profile or property in production is a common mistake. Externalized configuration is powerful but must be controlled.
- Boot 3 is built on Spring Framework 6 and needs Java 17 or later, so upgrades can be a real project.

**How I'd monitor it**
- `/actuator/health` (with liveness and readiness groups for Kubernetes probes) and `/actuator/metrics` via Micrometer.
- `/actuator/conditions` or running with `--debug` to see which auto-configurations were applied and why.
- `/actuator/env` to check which profile and properties are active (secured, with sensitive values masked).
- Startup time and memory tracked per release, plus `mvn dependency:tree` to review what starters pulled in.

**Follow-ups to expect**
- *Can you use Spring without Boot?* -> Yes. Boot is optional, and you configure everything yourself.
- *How do you override an auto-configured bean?* -> Define your own bean of that type. Most defaults use `@ConditionalOnMissingBean`, so they back off.
- *How does Boot find auto-configurations?* -> It reads a list of candidate classes from the library's metadata (an `.imports` file in recent versions) and applies each only if its conditions match.

**60-second answer**
Spring Framework is the core library: dependency injection, AOP, transactions, Web MVC and integration abstractions. Spring Boot is built on top of it and does not replace it. Boot removes the setup work through auto-configuration, which creates default beans based on what is on the classpath. It also adds starter dependencies for compatible library sets, externalized configuration for different environments, an embedded server so you run a JAR, and Actuator for health and metrics. If I define my own bean, Boot's default backs off. So the business code is still Spring, and Boot just makes it faster to configure, run and operate.

### Q43 [mid] What are `@Component`, `@Service`, `@Repository`, and `@RestController`?
tags: spring, stereotype-annotations, component-scan, ioc, exception-translation, basics

**Start here: the concepts**
- **Bean**: an object that Spring creates, stores and wires for you instead of you calling `new`. This is IoC (Inversion of Control): Spring controls object creation. DI (Dependency Injection) means Spring passes a bean's collaborators into it.
- **Component scanning**: at startup Spring searches packages for classes carrying `@Component` or an annotation built on it, and registers them as beans. Spring Boot's `@SpringBootApplication` scans its own package and sub-packages only.
- **Stereotype annotation**: an annotation that marks a class's role. `@Service`, `@Repository` and `@Controller` are all meta-annotated with `@Component` (annotated with it themselves), so scanning treats them as components.
- **Exception translation**: each persistence technology throws its own exceptions (JPA, Hibernate, JDBC). Spring converts them into one family, `DataAccessException`, so the service layer does not depend on the technology.
- **`@ResponseBody`**: tells Spring to write the method's return value straight into the HTTP response (usually as JSON), not treat it as a view name.

**The live scenario**
A team of 6 ran an orders API at about 20,000 requests a day. A new `OrderDao` used `EntityManager` and was annotated `@Component`. The service caught `DataIntegrityViolationException` on duplicate order IDs and returned HTTP 409. In production, duplicates returned 500 instead, because the raw `PersistenceException` leaked through and the catch block never matched. That was a few hundred wrong 500s a day and noisy alerts. Changing `@Component` to `@Repository` fixed it. A second bug: a new endpoint used `@Controller` and returned a POJO, so Spring looked for a view with that name and the call failed. `@RestController` fixed that.

**What the interviewer is really checking**
Whether you know the annotations are not just labels. Three of them are `@Component` with a role name, `@Repository` adds real behaviour, and `@RestController` changes how responses are written.

**How I answer it**
1. **`@Component` is the base.** It means "Spring, manage this class as a bean". Use it for generic classes that fit no other role, such as a utility or a helper.
2. **`@Service` marks business logic.** It currently adds no extra behaviour. I use it because it documents the layer and lets tools or AOP pointcuts target it.
3. **`@Repository` marks the persistence layer and adds exception translation.** Spring wraps the bean in a proxy that converts technology-specific exceptions into `DataAccessException`. This needs a `PersistenceExceptionTranslationPostProcessor`, which Spring Boot registers automatically. Spring Data repository interfaces get translation without the annotation.
4. **`@RestController` is `@Controller` plus `@ResponseBody`.** Every handler method writes its return value to the response body, usually as JSON via Jackson. Plain `@Controller` is for views (such as Thymeleaf pages).
5. **Correcting the stored answer:** all four are scan candidates, including `@RestController`, because `@Controller` is itself meta-annotated with `@Component`. Scanning does not treat it differently.
6. **Choose by role.** The annotation tells the next developer what the class is for.

```java
@Repository  // enables exception translation
public class OrderDao { /* uses EntityManager */ }
```

**Trade-offs and what can go wrong**
- Using `@Component` everywhere works but loses meaning, and it loses exception translation for DAOs.
- Putting `@Service` on a persistence class misleads readers and skips translation.
- A class outside the `@SpringBootApplication` package is silently not scanned, and you get "no bean found" errors.
- `@Controller` without `@ResponseBody` returns a view name, not JSON.
- Do not expect `@Service` to make anything transactional. That needs `@Transactional`.

**How I'd monitor it**
- Actuator `/actuator/beans` and `/actuator/mappings` confirm that beans and endpoints were registered.
- The Micrometer metric `http.server.requests` shows 5xx rates per endpoint.
- In Splunk, search logs for raw `PersistenceException` or `HibernateException` reaching the controller advice. In a correct setup you should only see `DataAccessException` subtypes.
- Alert on a sudden rise in 500s after a deploy.

**Follow-ups to expect**
- *Does `@Service` do anything special?* -> Not today. It is a semantic marker, but it keeps layers clear and allows targeted AOP.
- *Why might my `@Component` class not be picked up?* -> It is outside the scanned package, so use `scanBasePackages` or move it.
- *What is the difference between `@Controller` and `@RestController`?* -> `@RestController` adds `@ResponseBody`, so return values are serialized into the response body.

**60-second answer**
`@Component` is the generic annotation that tells Spring to create and manage a class as a bean. `@Service`, `@Repository` and `@Controller` are specialisations of it, so component scanning finds all of them, and `@RestController` too because it builds on `@Controller`. `@Service` is a marker for business logic and does nothing extra. `@Repository` marks the persistence layer and enables exception translation, converting JPA or JDBC exceptions into Spring's `DataAccessException`. `@RestController` is `@Controller` plus `@ResponseBody`, so return values go into the response as JSON. I pick the annotation that matches the class's role, because a wrong one can cause real bugs, like raw persistence exceptions leaking out of a DAO.

### Q44 [mid] Explain the controller-service-repository layering.
tags: spring-boot, layered-architecture, controller, service, repository, dto, transactions, basics

**Start here: the concepts**
- **Layering:** splitting code into stacked groups, each with one job. A layer only talks to the layer directly below it. This keeps each change small and local.
- **Controller:** the class that receives the HTTP request (for example `@RestController`). It maps URLs to methods, checks that the input is well-formed, calls the service and chooses the HTTP status code. It exists so that web concerns stay in one place.
- **Service:** the class that holds the business rules, such as "a discount applies only to orders above 100" or "stock must be reserved before payment". It exists so the rules can be reused and tested without a web server.
- **Repository:** the class that reads and writes the database (in Spring, often a Spring Data interface). It exists so the rest of the code never needs to know how data is stored.
- **Transaction boundary:** the start and end of a group of database changes that must all succeed or all be undone. It sits in the service because one business action may touch several repositories.
- **Entity:** a Java object mapped to a database table.
- **DTO (Data Transfer Object):** a plain object designed only for the API request or response. It is a separate contract from the table structure.

**The live scenario**
An order system had three endpoints, and each controller contained its own discount calculation and called the database directly. The mobile app and the admin portal used different endpoints, so the discount rule existed in three copies. When the rule changed, the team fixed two copies and missed one. About 1,800 orders were priced wrongly over a weekend. In the same release, a new `costPrice` column was added to the entity, and because the controller returned the entity directly, the field leaked into the public JSON. Both problems came from the same cause: the layers were not separated.

**What the interviewer is really checking**
Whether you know what belongs in each layer and why, and whether you can name the real consequences of mixing them: duplicated rules, wrong transaction scope and leaked entities.

**How I answer it**
1. **Describe the flow:** HTTP request → controller → service → repository → database, and the response travels back up. Each layer calls only the one below it. That keeps dependencies one-directional and easy to follow.
2. **Keep controllers thin.** They handle HTTP mapping, input validation and status codes, and then delegate. Business logic in a controller can only be reached through HTTP, so it is hard to reuse and test.
3. **Put business rules in services.** Several controllers, a Kafka listener or a scheduled job can then call the same rule, so there is one copy to fix.
4. **Put the transaction boundary on the service method.** One business action can then update several tables atomically:
   ```java
   @Transactional
   public OrderDto placeOrder(PlaceOrderRequest req) { ... }
   ```
   Spring applies this through a proxy (a wrapper object around your bean). It therefore works when the call comes from another bean and public method, but not for self-invocation (a method calling another method in the same class) or private methods.
5. **Keep database access in repositories.** Queries and persistence details stay in one place, so a change of query or database does not touch business code.
6. **Return DTOs from public APIs, not entities.** A DTO gives a stable contract: adding a column does not change the JSON, internal fields stay hidden, and lazy-loaded relations are not serialised by accident.

**Trade-offs and what can go wrong**
- More classes and mapping code (entity ↔ DTO). For a tiny CRUD app, a service that only forwards calls can feel like ceremony.
- A common mistake is an "anemic" service that only forwards calls while the rules live in the controller.
- Calling a repository straight from the controller skips the transaction boundary.
- Putting `@Transactional` on the controller widens the transaction to include JSON serialisation and holds a database connection longer.
- Business checks belong in the service. Controller validation covers only the shape of the input, such as a missing field.

**How I'd monitor it**
- Micrometer metric `http.server.requests` (via Actuator), broken down by URI and status, shows slow or failing endpoints.
- HikariCP pool metrics (active and pending connections) reveal transactions that are too wide.
- Splunk searches on 5xx errors per endpoint and on slow-request logs.
- An architecture test (for example ArchUnit) in the build that fails if a controller depends on a repository.
- Contract or JSON-snapshot tests to catch accidental fields in responses.

**Follow-ups to expect**
- *Why is `@Transactional` on the service and not the repository?* -> The service method represents one business action that may call several repositories, and all of those calls must commit or roll back together.
- *Where does validation go?* -> Format checks (`@Valid`, required fields) go in the controller layer. Business checks (stock available, credit limit) go in the service.
- *Why not return entities directly?* -> It couples the public API to the table structure, can expose sensitive fields and can trigger lazy-loading problems. A DTO keeps the contract stable.

**60-second answer**
The request goes from the controller to the service to the repository to the database. The controller is thin: it maps the URL, validates the input and returns the right HTTP status. The service holds the business rules and the transaction boundary, so one business action commits or rolls back as a whole. The repository only talks to the database. I return DTOs rather than entities so the API stays stable and no internal fields leak. Without this separation, rules get copied across controllers, and a fix in one place misses the others. I would enforce the layering with an architecture test and watch endpoint latency and connection-pool metrics.

### Q45 [mid] How do you handle exceptions globally in Spring Boot?
tags: spring-boot, exception-handling, rest-api, controlleradvice, error-handling, observability, basics

**Start here: the concepts**
- **Exception:** a Java object that signals something went wrong, such as a customer that does not exist. If nothing catches it, it travels up the call stack.
- **HTTP status code:** a number in the response telling the client what happened (404 not found, 400 bad request, 500 server error). Clients and monitoring tools rely on it.
- **Exception handler:** a method that catches a specific exception type and decides which response to return. In Spring it is marked with `@ExceptionHandler`.
- **`@RestControllerAdvice`:** a class whose handlers apply to all controllers. It is `@ControllerAdvice` plus `@ResponseBody`, so return values are written as JSON. It exists so error handling lives in one place instead of try/catch in every controller.
- **Stable error code:** a fixed string like `CUSTOMER_NOT_FOUND` that clients can depend on. Message text may change or be translated, so clients should not parse it.
- **Correlation/trace ID:** a unique ID attached to a request and written in every log line for it. The client gets the same ID, so support can find the exact server logs.
- **Stack trace:** the list of code locations where an error occurred. It helps developers but leaks internals (class names, SQL, library versions) to attackers.

**The live scenario**
A customer API handles about 2,000 requests/min. Each of three controllers had its own try/catch, and each returned a different error shape. A mobile app got a raw 500 with a stack trace showing table names when a customer ID was missing. Support got around 40 tickets a day saying "something failed" and could not match them to logs. The security team flagged the leaked internals. One global handler with consistent JSON and a trace ID fixed both problems.

**What the interviewer is really checking**
Whether you know that error handling is centralised and not scattered, and that you separate what the client sees (safe, stable) from what you log (full detail). A strong mid-level answer also knows what the advice class does not catch.

**How I answer it**
1. **Create one `@RestControllerAdvice` class.** Spring's MVC layer finds it and consults it whenever a controller throws. This keeps controllers focused on business logic.
2. **Add an `@ExceptionHandler` per exception type, mapped to the right status.** The type tells Spring which handler to call, and the status tells the client who is at fault: 404 for missing data, 400 or 422 for bad input, 409 for conflicts.
   ```java
   @RestControllerAdvice
   class ApiExceptionHandler {
     @ExceptionHandler(CustomerNotFoundException.class)
     ResponseEntity<Map<String,String>> notFound(CustomerNotFoundException ex) {
       return ResponseEntity.status(404).body(Map.of("error","CUSTOMER_NOT_FOUND")); } }
   ```
3. **Return one consistent body:** a stable error code, a safe message, a timestamp and the trace ID. Clients then write one parser. In Spring Framework 6 / Boot 3 you can use the built-in `ProblemDetail`, which follows the standard "problem details for HTTP APIs" format, instead of inventing your own shape.
4. **Add a catch-all `@ExceptionHandler(Exception.class)` that returns 500.** Without it, unexpected errors fall through to the default error page. The catch-all returns a generic message, never `ex.getMessage()`.
5. **Cover framework exceptions too,** such as validation failures (`MethodArgumentNotValidException`) and malformed JSON. Extending `ResponseEntityExceptionHandler` gives you these as a base.
6. **Log the details server-side** (full stack trace, trace ID) and **never return stack traces or secrets** to the client. The client needs enough to act, and the team needs enough to debug.

**Trade-offs and what can go wrong**
- Exceptions thrown in servlet filters (including Spring Security filters) happen before the controller layer, so the advice never sees them. They need an `AuthenticationEntryPoint`, an `AccessDeniedHandler` or a filter-level handler.
- If you catch an exception inside a `@Transactional` service and swallow it, the transaction will not roll back. Let it propagate to the advice.
- A very broad catch-all can hide bugs if you forget to log. Log every 500 at ERROR level.
- Returning 200 with an error body breaks clients and monitoring. Use real status codes.
- Too many exception classes become noise. Group them by meaning (not found, invalid, conflict).

**How I'd monitor it**
- Track the rate of 4xx and 5xx responses per endpoint with Micrometer's `http.server.requests` metric, exposed via Actuator, and alert on a 5xx spike.
- Search logs in Splunk by trace ID, or for ERROR entries from the handler class grouped by error code.
- Check that the 5xx log count matches the 500 responses. A mismatch means errors are being swallowed.
- Add a test that checks no response body contains "at com." or "Exception".

**Follow-ups to expect**
- *Difference between `@ControllerAdvice` and `@RestControllerAdvice`?* -> The latter adds `@ResponseBody`, so return values are serialised straight to the response body (JSON).
- *Why does my handler not catch a 401 from Spring Security?* -> Security filters run before the controller layer, so the advice is never involved. Use `AuthenticationEntryPoint` and `AccessDeniedHandler`.
- *What if two handlers match?* -> Spring picks the closest match in the exception hierarchy, so a specific handler wins over `Exception.class`.

**60-second answer**
I put all error handling in one `@RestControllerAdvice` class, with an `@ExceptionHandler` method per exception type, so controllers stay clean. Each handler maps the exception to the right status, such as 404 for a missing customer, and returns one consistent body with a stable error code, a safe message, a timestamp and a trace ID. I add a catch-all handler for unexpected errors that returns a generic 500. Full details and the stack trace are logged on the server, and I never send stack traces or secrets to the client. I also remember that filter-level errors, like Spring Security's, need separate handling. I monitor 4xx/5xx rates and search logs by trace ID.

### Q46 [mid] What is Spring Boot Actuator?
tags: spring-boot, actuator, health-checks, micrometer, kubernetes, probes, basics

**Start here: the concepts**
- **Actuator:** a Spring Boot module (`spring-boot-starter-actuator`) that adds ready-made "management" endpoints to your running app. It exists so you can see inside a live service without writing that plumbing yourself.
- **Endpoint:** a named operational feature, such as health, metrics or env. It can be exposed over HTTP (`/actuator/health`) or JMX, a Java management protocol.
- **Health endpoint:** reports whether the app is working, as `UP` or `DOWN`. It aggregates *health indicators*, which are small checks for things like the database, disk space or a message broker.
- **Metrics endpoint:** lists numbers about the running app, such as JVM memory, HTTP request timings and connection-pool usage. These come from Micrometer, a metrics library that monitoring tools like Prometheus can read.
- **Environment endpoint:** shows configuration properties and active profiles. This is useful for debugging and risky if exposed.
- **Exposure:** an endpoint can exist but not be reachable. In recent Boot versions only `health` is exposed over HTTP by default, and you opt in to the rest.
- **Liveness probe:** asks "is this process stuck beyond repair, so should it be restarted?"
- **Readiness probe:** asks "can this instance handle traffic right now?" If not, the load balancer stops sending requests but does not kill it.
- **Kubernetes probe:** the platform calls an HTTP URL periodically and acts on the answer. Actuator provides `/actuator/health/liveness` and `/actuator/health/readiness` for this.

**The live scenario**
A payments service runs 6 pods at about 800 requests/second. The team puts the database check inside the liveness probe. The database has a 90-second slowdown, every pod fails liveness, and Kubernetes restarts all 6 at once. Startup takes 40 seconds, so a 90-second database blip becomes a 5-minute outage. In the same review, a security scan finds `/actuator/env` and `/actuator/heapdump` open to the internet. A heap dump can contain secrets and customer data.

**What the interviewer is really checking**
Whether you know Actuator is an operations tool and not just "the health URL". They also want to see that you can expose it safely and tell liveness from readiness.

**How I answer it**
1. **Define it:** Actuator exposes operational endpoints (health, metrics, environment and more, depending on configuration and dependencies). Teams and platforms need a standard way to ask a running app how it is doing.
2. **Name the common ones:** `/actuator/health` for status and `/actuator/metrics` for numbers. Which endpoints exist depends on which starters and libraries are on the classpath. For example, a database health check appears only if a datasource is present.
3. **Expose only what is needed:** each extra endpoint widens the attack surface.
   ```properties
   management.endpoints.web.exposure.include=health,metrics
   ```
4. **Protect what is exposed:** apply authentication (Spring Security rules for `/actuator/**`), network restrictions (a separate management port or internal network only), and endpoint-specific access controls. For example, health can be open to the cluster while `env` and `heapdump` need an admin role or stay disabled.
5. **Separate liveness from readiness:** liveness should check only the process itself, and a failure triggers a restart. Readiness can include dependencies the app needs to serve requests, and a failure only removes the pod from traffic. This avoids the restart storm in the scenario above.

**Trade-offs and what can go wrong**
- Exposing everything with `include=*` without security leaks configuration, thread dumps and heap dumps.
- Putting external dependencies in liveness causes cascading restarts.
- Very slow health checks can time out and cause false failures.
- Readiness that is too strict can remove all pods from traffic at once.
- Actuator adds a small overhead, and a high number of distinct metric labels (tags) can use a lot of memory.

**How I'd monitor it**
- Scrape metrics such as `http.server.requests`, JVM memory and `hikaricp.connections.*` into Prometheus or a similar tool, and alert on them.
- Watch Kubernetes events for probe failures and a rising pod restart count.
- Alert when readiness flips to `DOWN` for more than a set time.
- Periodically test from outside the network that sensitive endpoints return 401, 403 or 404.
- In Splunk, search for access to `/actuator/*` from unexpected IPs.

**Follow-ups to expect**
- *How do you enable Kubernetes probes?* -> Probes are enabled automatically when Boot detects Kubernetes. Otherwise set `management.endpoint.health.probes.enabled=true` to get the `/liveness` and `/readiness` health groups.
- *How would you add a custom health check?* -> Implement `HealthIndicator` (or extend `AbstractHealthIndicator`) and return `UP` or `DOWN` with details. Then decide deliberately whether it belongs in readiness, liveness or neither.
- *How do metrics reach Prometheus?* -> Actuator uses Micrometer. Add the Prometheus registry dependency and expose the `prometheus` endpoint for scraping.

**60-second answer**
Spring Boot Actuator adds operational endpoints to a running app, such as health and metrics, plus environment and others depending on configuration and dependencies. I expose only what is needed, because endpoints like `env` and `heapdump` can leak secrets. I protect them with authentication, network restrictions and endpoint-specific access rules. For Kubernetes I separate the two probes. Liveness asks whether the process should be restarted, and readiness asks whether it can accept traffic. I keep dependency checks like the database out of liveness, so a database outage does not cause every pod to restart. I also scrape the metrics and alert on probe failures and restarts.
