# Spring Boot: auto-configuration, configuration, Actuator, startup and operations

> **Runnable:** [`01_autoconfiguration_and_externalized_config.java`](../examples/07_spring_boot/01_autoconfiguration_and_externalized_config.java) ·
> [`02_actuator_health_and_graceful_shutdown.java`](../examples/07_spring_boot/02_actuator_health_and_graceful_shutdown.java)
> **Crib sheet:** [`topics/05-spring-core-boot.md`](../topics/05-spring-core-boot.md) · **Guide:** Q30–Q36, Q38, Q95

## What interviewers are actually probing

Whether you understand Boot as a *mechanism* (conditional configuration, property binding) rather than a set of annotations you copy.
Expect: what happens on startup, how auto-configuration backs off, config precedence, profiles and secrets, Actuator and Kubernetes probes,
global exception handling, validation, testing slices, and how you would operate the thing (graceful shutdown, memory, startup time).

## Must-know points

- `@SpringBootApplication` = `@Configuration` + `@EnableAutoConfiguration` + `@ComponentScan` (from the main class's package **downward**).
- Auto-configuration classes are listed in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (Boot 2.7+/3) and guarded by `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty`. **Your bean wins.** `--debug` / `/actuator/conditions` shows why.
- Property precedence (high → low, abridged): command line → `SPRING_APPLICATION_JSON` → OS env vars → `application-{profile}.yml` → `application.yml` → `@PropertySource` → defaults.
- `@ConfigurationProperties` (typed, validated, relaxed binding) beats scattered `@Value`.
- Actuator: `health` (liveness/readiness groups), `metrics`, `prometheus`, `loggers`, `threaddump`, `heapdump`, `env`, `conditions`. **Secure and limit exposure.**
- Boot 3: Java 17+, `jakarta.*`, Spring Framework 6, native image/AOT support, `ProblemDetail` (RFC 7807/9457), Micrometer Observation API.

## Interview questions and full answers

### Q1. What happens when a Spring Boot application starts?

`SpringApplication.run`: create the `Environment` (load property sources, activate profiles) → create the `ApplicationContext` (servlet/reactive/none) → register bean definitions
(component scan + **auto-configuration imports**) → refresh the context (create singletons, run `BeanPostProcessor`s) → start the **embedded server** (Tomcat by default) → publish `ApplicationReadyEvent` and run `CommandLineRunner`/`ApplicationRunner` beans.
Startup time is dominated by classpath scanning, bean creation and any eager I/O in `@PostConstruct`.

### Q2. How does auto-configuration work, and how do you override it?

Each auto-configuration is an ordinary `@Configuration` with conditions. Example: `DataSourceAutoConfiguration` applies when a `DataSource` class is on the classpath **and** you haven't defined your own `DataSource` bean (`@ConditionalOnMissingBean`).
Override by defining the bean yourself, by property (`spring.datasource.*`), by excluding it (`@SpringBootApplication(exclude=...)` / `spring.autoconfigure.exclude`), or by a customiser bean (`Jackson2ObjectMapperBuilderCustomizer`).
Example 07/01 reproduces the condition report.

### Q3. What is a starter?

A dependency descriptor (often just a POM) that pulls a coherent set of libraries — `spring-boot-starter-web` (MVC + Jackson + Tomcat + validation), `-data-jpa`, `-security`, `-actuator`, `-test`. The versions come from the Boot BOM (`spring-boot-dependencies`), so you don't pick compatible versions yourself.
Custom starter = an `autoconfigure` module + a starter module + `@ConfigurationProperties` + conditions.

### Q4. Explain externalised configuration, profiles and precedence.

Same artifact, different environments: values come from files, env vars, args, and config servers. Higher sources override lower ones (example 07/01 section 3 prints the winner for each key and where it came from).
Profiles (`spring.profiles.active=prod`) layer `application-prod.yml` over `application.yml` and gate beans with `@Profile`. Use profiles for **behaviour**; use env vars / secret stores for **values**.
Secrets never go in git: Vault, AWS Secrets Manager/Parameter Store, Azure Key Vault or Kubernetes Secrets mounted as env vars or files (`spring.config.import=configtree:/etc/secrets/`).

### Q5. `@ConfigurationProperties` vs `@Value`?

```java
@ConfigurationProperties(prefix = "orders.client")
@Validated
public record OrdersClientProperties(@NotBlank String baseUrl, @DefaultValue("2s") Duration timeout, @Min(1) int maxConnections) {}
```

Typed, grouped, validated at startup (fail fast), relaxed binding (`max-connections`, `MAX_CONNECTIONS`), IDE metadata, easy to test. `@Value("${x}")` is fine for a single scalar; it doesn't validate as a group and spreads keys across classes.

### Q6. How do you handle exceptions globally in a REST API?

```java
@RestControllerAdvice
class ApiExceptionHandler extends ResponseEntityExceptionHandler {
    @ExceptionHandler(OrderNotFoundException.class)
    ProblemDetail notFound(OrderNotFoundException e) {
        ProblemDetail p = ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
        p.setTitle("Order not found"); p.setProperty("orderId", e.getId()); return p;
    }
    @ExceptionHandler(Exception.class)
    ProblemDetail unexpected(Exception e) { log.error("unhandled", e); return ProblemDetail.forStatus(500); }  // never leak stack traces
}
```

Business exceptions map to 4xx with a stable machine-readable `type`; unexpected errors map to 500 and are logged **once** with the correlation id; validation errors (`MethodArgumentNotValidException`) become 400 with field errors.

### Q7. How does request validation work?

Bean Validation (Jakarta Validation/Hibernate Validator): annotate DTOs (`@NotBlank`, `@Size`, `@Positive`, custom constraint), add `@Valid` on the `@RequestBody` parameter; `@Validated` on a class enables method-level validation of `@PathVariable`/`@RequestParam`.
Validate **at the boundary** (syntax and format) and again in the domain for invariants. Don't put validation logic in controllers by hand.

### Q8. What is Actuator and what do you expose in production?

Operational endpoints over HTTP/JMX. Expose the minimum (`management.endpoints.web.exposure.include=health,info,prometheus`), put them on a **separate management port**, secure the sensitive ones (`env`, `heapdump`, `threaddump`, `loggers`), and enable **probes**: `/actuator/health/liveness` and `/readiness`.
Metrics are Micrometer meters (`http.server.requests`, `jvm.*`, `hikaricp.*`) scraped by Prometheus.

### Q9. Liveness versus readiness, and graceful shutdown on Kubernetes?

Liveness answers "restart me?" and must **not** depend on downstreams (a DB outage would restart every pod). Readiness answers "send me traffic?" and may depend on DB/Kafka.
Graceful shutdown: `server.shutdown=graceful`, `spring.lifecycle.timeout-per-shutdown-phase=30s`. On SIGTERM readiness flips to refusing traffic, in-flight requests finish, then beans are destroyed.
Set `terminationGracePeriodSeconds` > that timeout and add a short `preStop` sleep so the load balancer stops sending first. Example 07/02 runs this against a real HTTP server.

### Q10. How do you test a Spring Boot application?

| Level | Annotation | Notes |
|---|---|---|
| Unit | plain JUnit + Mockito | no Spring; constructor injection pays off |
| Web slice | `@WebMvcTest` + `MockMvc` + `@MockBean` | controller, validation, advice |
| Data slice | `@DataJpaTest` (+ Testcontainers) | repository + real DB dialect |
| Integration | `@SpringBootTest(webEnvironment = RANDOM_PORT)` | whole app |
| Messaging | `@EmbeddedKafka` or Testcontainers `KafkaContainer` | consumer/DLT behaviour |
| Contracts | Spring Cloud Contract / Pact | between services |

Prefer Testcontainers over H2 when behaviour depends on the real engine (JSON columns, locking, SQL dialect).

### Q11. How would you reduce startup time and memory?

Remove unused starters/auto-configs, avoid classpath scanning on huge packages, `spring.main.lazy-initialization=true` (selectively), no network calls in `@PostConstruct`, use CDS/AppCDS, layered jars, **native image** (GraalVM, AOT) when cold start dominates, and right-size the heap with `MaxRAMPercentage`.
Measure with `--debug`, Actuator `startup` endpoint (`BufferingApplicationStartup`) and JFR.

### Q12. Describe how you'd structure and operate a Boot service (golden path).

Layers: web (controllers/DTOs) → application (use cases, transactions) → domain (entities, rules) → infrastructure (repositories, clients, messaging).
Cross-cutting: `ProblemDetail` handler, correlation-id filter + structured JSON logs, Micrometer metrics + OpenTelemetry tracing, timeouts/retries/circuit breakers on every client, Flyway/Liquibase migrations, Testcontainers tests,
Dockerfile with layered jar and non-root user, probes, `MaxRAMPercentage`, graceful shutdown, config via env/secret store.

## A worked example

Run [`01_autoconfiguration_and_externalized_config.java`](../examples/07_spring_boot/01_autoconfiguration_and_externalized_config.java):
section 1 shows `MongoAutoConfiguration` **not matched** because the class isn't on the classpath, section 2 shows your own `ObjectMapper` making the default back off,
section 3 prints each key's winning source. Then run [`02_actuator_health_and_graceful_shutdown.java`](../examples/07_spring_boot/02_actuator_health_and_graceful_shutdown.java) and read why liveness stays 200 while readiness goes 503.

## Hands-on drills

1. Write a custom `@ConditionalOnProperty`-guarded auto-configuration for an "audit" starter.
2. Bind a nested YAML structure into a record with validation and make startup fail on a bad value.
3. Add a custom `HealthIndicator` for a downstream and decide whether it belongs in liveness or readiness.
4. Expose a Prometheus endpoint and add a custom `Timer`/`Counter`; explain tag cardinality.
5. Produce a Dockerfile using layered jars and measure image size/startup before and after.

## The 60-second spoken answer

"Boot configures Spring from the classpath and properties: starters bring dependencies, auto-configurations apply conditionally and back off when I define
my own bean, and typed `@ConfigurationProperties` give me validated configuration with a clear precedence from files to environment variables.
Operationally I expose minimal Actuator endpoints, split liveness from readiness so a database outage doesn't restart pods, enable graceful shutdown with a
preStop delay, and instrument with Micrometer. For tests I use slices and Testcontainers rather than mocking the world."
