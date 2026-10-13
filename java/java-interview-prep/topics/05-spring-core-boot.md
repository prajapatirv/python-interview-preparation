---
id: 05-spring-boot
title: Spring Framework & Spring Boot (3.x / 4.x)
focus: IoC, auto-configuration, proxies, configuration, Boot 4 changes
deep_dive: 06,07
examples: 06_spring_core,07_spring_boot
---
Boot 4.0 (Nov 2025) is built on Spring Framework 7; Boot 3.5 open-source support ended June 2026. Mention both versions if asked "what are you on".

### Q1 [basic] What are IoC and Dependency Injection?
IoC: the container creates and wires objects instead of your code calling `new`. DI is how: constructor, setter or field injection. **Prefer constructor injection** - dependencies are final, required and testable without Spring.

### Q2 [basic] What are bean scopes?
`singleton` (default, one per container - must be stateless/thread-safe), `prototype` (new each request), `request`, `session`, `application`. Injecting a prototype into a singleton gives you one instance only - use `ObjectProvider<T>` or a scoped proxy.

### Q3 [basic] What does `@SpringBootApplication` do?
Combines `@Configuration`, `@EnableAutoConfiguration` and `@ComponentScan` (from the package of the class downward). Put the main class in the root package or your components are not found.

### Q4 [basic] `@Component` vs `@Service` vs `@Repository` vs `@Controller` vs `@Bean`?
First four are stereotypes found by component scanning; `@Repository` also translates persistence exceptions to `DataAccessException`. `@Bean` is a factory method inside a `@Configuration` class - used for third-party classes you cannot annotate.

### Q5 [intermediate] How does auto-configuration work?
Boot reads the list of auto-configuration classes (`META-INF/spring/...AutoConfiguration.imports`) and applies each one only if its `@Conditional...` passes: `@ConditionalOnClass` (library on classpath), `@ConditionalOnMissingBean` (you did not define your own), `@ConditionalOnProperty`. See what happened with `--debug` or the Actuator `conditions` endpoint. Boot 4 splits the big autoconfigure jars into smaller technology modules.

### Q6 [intermediate] Describe the bean lifecycle.
Instantiate -> inject dependencies -> `Aware` callbacks -> `BeanPostProcessor.before` -> `@PostConstruct` / `afterPropertiesSet` -> `BeanPostProcessor.after` (AOP proxies are created here) -> ready -> `@PreDestroy` on shutdown. Knowing that proxies are made in `postProcessAfterInitialization` explains most "why didn't my annotation work" bugs.

### Q7 [intermediate] How does Spring AOP work and what is the self-invocation problem?
Spring wraps beans in a JDK or CGLIB proxy that applies advice (`@Transactional`, `@Async`, `@Cacheable`). A call from **inside** the same class bypasses the proxy, so the annotation is ignored. Fixes: move the method to another bean, inject self lazily, or use AspectJ weaving. Also: only `public` methods on proxied beans, and `final` classes/methods cannot be proxied by CGLIB.

### Q8 [intermediate] Circular dependency - why does it happen and how to fix?
A needs B and B needs A. Constructor injection fails fast (good); Boot 2.6+ forbids cycles by default. Fix the design: extract the shared logic into a third bean or use events. `@Lazy` is a last resort.

### Q9 [intermediate] How do you manage configuration and profiles?
`application.yml` + `application-{profile}.yml`, environment variables (override file values), `@ConfigurationProperties` with validation (`@Validated`) for typed config, and secrets from Vault/AWS Secrets Manager/Kubernetes Secrets - never in Git. Order of precedence: command line > env vars > profile file > default file.

### Q10 [intermediate] `@ConfigurationProperties` vs `@Value`?
`@ConfigurationProperties` binds a whole prefix into a typed, validated, relaxed-binding object (best for groups of settings, works with records in Boot 3+). `@Value` injects a single value with SpEL - fine for one-offs but scattered and not type-checked as a group.

### Q11 [intermediate] What are the Actuator endpoints you rely on?
`/actuator/health` (liveness/readiness groups for Kubernetes), `metrics` + Prometheus registry, `info`, `loggers` (change log level at runtime), `threaddump`, `heapdump`, `env`, `conditions`. Secure them: expose only what's needed, put them on a separate management port, require auth for sensitive ones.

### Q12 [intermediate] How do you handle exceptions globally in a REST app?
`@RestControllerAdvice` with `@ExceptionHandler` methods returning `ProblemDetail` (RFC 7807, built in since Spring 6) with a stable `type`, `title`, `status`, `detail` and a correlation id. Validation errors (`MethodArgumentNotValidException`) become a 400 with field errors; unknown errors become a 500 with no stack trace leaked.

### Q13 [intermediate] How does bean validation work?
Annotate DTOs (`@NotNull`, `@Size`, `@Email`, custom constraint) and add `@Valid` on the controller parameter; use `@Validated` on a class for method-level validation and validation groups. Validate at the boundary and again in the domain for invariants.

### Q14 [intermediate] What is the difference between `RestTemplate`, `WebClient`, `RestClient`, and HTTP interfaces?
`RestTemplate`: blocking, in maintenance mode. `WebClient`: reactive and non-blocking. `RestClient` (6.1): modern blocking fluent API, the replacement for RestTemplate. HTTP Interface clients: declare an interface with `@GetExchange` and Spring generates the client; Boot 4 adds `@ImportHttpServices` to register them with little configuration. Always set connect/read timeouts.

### Q15 [advanced] What's new and important in Spring Framework 7 / Boot 4?
- Built-in resilience: `@Retryable`, `@ConcurrencyLimit`, `@EnableResilientMethods` (Spring Retry features moved into core).
- First-class **API versioning** in `@RequestMapping` (MVC and WebFlux).
- **JSpecify** null-safety annotations across the portfolio.
- Modularised auto-configuration (smaller starters like `spring-boot-starter-webmvc`).
- Jackson 3 support, `BeanRegistrar` for programmatic bean registration, Spring Security 7, Jakarta EE 11.
- Spring Data AOT for faster startup; Java 17 minimum, Java 25 recommended.
Say you'd verify against the migration guide before upgrading.

### Q16 [advanced] How would you migrate Spring Boot 2.x to 3.x/4.x?
Upgrade to the last 2.7 first -> fix deprecations -> Java 17 -> `javax.*` to `jakarta.*` (OpenRewrite) -> Hibernate 6 query/ID-generation changes -> Spring Security lambda DSL (`WebSecurityConfigurerAdapter` removed) -> then 3.5 -> then 4.x via the migration guide. Run integration tests after each hop and check third-party libs for Jakarta versions.

### Q17 [advanced] Spring MVC request flow end to end?
Servlet container -> `DispatcherServlet` -> `HandlerMapping` finds the controller method -> interceptors `preHandle` -> argument resolvers/`HttpMessageConverter` (JSON -> object) + validation -> controller -> return value converter (object -> JSON) -> interceptors `postHandle` -> response. Filters run before the servlet; exceptions go to `HandlerExceptionResolver`/`@ControllerAdvice`.

### Q18 [advanced] Filter vs Interceptor vs AOP?
Filter: servlet level, sees raw request/response (security, CORS, request ids). Interceptor: Spring MVC level, knows the handler method. AOP: method level on any bean (transactions, auditing, metrics). Use the lowest level that has the information you need.

### Q19 [advanced] How do you do graceful shutdown and health probes on Kubernetes?
`server.shutdown=graceful` + `spring.lifecycle.timeout-per-shutdown-phase=30s`; readiness probe flips to "refusing traffic" first, then in-flight requests finish, then beans are destroyed; set `terminationGracePeriodSeconds` > that timeout and add a `preStop` sleep (~5s) so the load balancer stops sending traffic. Liveness must not depend on downstream services.

### Q20 [advanced] What are common Spring Boot startup/memory problems and fixes?
Slow startup: too many auto-configs, classpath scanning, eager `@PostConstruct` calls -> use lazy init selectively, AOT/CDS/native, remove unused starters. Memory: too many beans per tenant, big caches, thread pools per feature. Measure with `--debug`, `spring.main.lazy-initialization`, and startup actuator (`BufferingApplicationStartup`).

### Q21 [design] Design a Spring Boot service skeleton you would give a new team (golden path).
Layers: `api` (controllers/DTO) -> `application` (services/use-cases, transactions) -> `domain` (entities, rules) -> `infrastructure` (repositories, clients, messaging). Cross-cutting: `ProblemDetail` error handling, correlation-id filter, structured JSON logs, Micrometer metrics + OpenTelemetry tracing, Resilience (timeouts, retry, circuit breaker), Flyway migrations, Testcontainers tests, ArchUnit rules, Dockerfile with layered jars, health probes, `/actuator` hardened. Publish it as a template repo or Maven archetype.

### Q22 [design] Monolith vs modular monolith vs microservices for a new product - how do you decide?
Start with a **modular monolith** (Spring Modulith 2.0 can verify module boundaries) when the domain is unclear and the team is small; split into services only for independent scaling, different release cadence, team ownership or fault isolation. Microservices add network failure, distributed transactions and operational cost - pay only when the benefit is real.

### Q23 [design] Design a configuration and secrets strategy for a Spring Boot service across dev, test and prod.
Layer config: defaults in the jar, environment-specific values from Spring Cloud Config / Kubernetes ConfigMaps, secrets from Vault / Azure Key Vault / AWS Secrets Manager injected at runtime (never in git or images). Use profiles sparingly, `@ConfigurationProperties` with validation for fail-fast startup, and rotate secrets without redeploying (refresh scope or sidecar). Trade-off: central config servers add a startup dependency - cache the last good config. Audit who can read prod secrets.
