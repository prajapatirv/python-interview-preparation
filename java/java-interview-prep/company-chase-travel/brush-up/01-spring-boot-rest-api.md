# 01 - Spring Boot REST API (Basic to Advanced)

**Chase project brush-up, point 1 of 4** (requested by Sujay: Spring Boot REST API · database connection from Spring Boot · Kafka consumer and producer · AWS S3, ECS, Aurora Postgres). Hub: [`../README.md`](../README.md).

**Functional requirement these answers are framed around (illustrative):** *"Card members search and book hotels with points, card or both. The booking service (Spring Boot on ECS Fargate behind an ALB) exposes REST APIs, stores bookings in Aurora PostgreSQL, publishes `BookingConfirmed` to Kafka (MSK) for notifications and rewards, and stores itinerary PDFs in S3. No double booking or double charge, p95 under 800 ms, survive an Aurora failover."*

**Target:** Java Lead / Senior Java Developer, travel booking platform (Chase Travel style: search, book, pay, rewards).
**Versions to mention:** Java 17/21 (25 LTS is current), Spring Boot 3.5 (support ended June 2026) and Spring Boot 4 / Spring Framework 7. Say which one your project runs.

> **How to use this document:** answer the first sentence of each answer out loud, then add one example from your own project. The "Project hook" at the end of each part shows where to plug in a real story. Travel examples are illustrative; replace them with facts from your actual project.

---

## Part 1 - Basic (Q1-Q10)

### Q1 [basic] What is Spring Boot and why use it for REST APIs?
Spring Boot is an opinionated layer on top of Spring that gives you auto-configuration, starter dependencies, an embedded server (Tomcat by default) and production features (Actuator). You write `main()` and a controller, and you get a runnable service without XML or a separate application server. It removes boilerplate so the team spends time on business logic.

### Q2 [basic] What does `@SpringBootApplication` do?
It combines three annotations: `@Configuration` (this class can declare beans), `@EnableAutoConfiguration` (configure beans based on the classpath and properties) and `@ComponentScan` (find components from this package downward). Put the main class in the root package, otherwise your controllers are not found.

### Q3 [basic] `@Controller` vs `@RestController`?
`@RestController` = `@Controller` + `@ResponseBody`. Every method returns data (JSON) written to the response body by an `HttpMessageConverter` (Jackson), not a view name. Use `@RestController` for APIs.

### Q4 [basic] Which annotations map HTTP requests, and how do you read inputs?
`@GetMapping`, `@PostMapping`, `@PutMapping`, `@PatchMapping`, `@DeleteMapping` (shortcuts for `@RequestMapping(method=...)`). Inputs: `@PathVariable` (`/bookings/{id}`), `@RequestParam` (`?status=CONFIRMED`), `@RequestBody` (JSON body), `@RequestHeader` (e.g. `Idempotency-Key`).
```java
@GetMapping("/bookings/{id}")
public BookingResponse get(@PathVariable UUID id) { return service.get(id); }
```

### Q5 [basic] Which HTTP status codes do you return and when?
200 OK (read), 201 Created (+ `Location` header) for a new booking, 202 Accepted (async work), 204 No Content (delete), 400 invalid input, 401 not authenticated, 403 not allowed, 404 not found, 409 conflict (duplicate or version clash), 422 business rule violation, 429 too many requests, 500 our bug, 502/503/504 upstream failure. Never return 200 with an error inside the body.

### Q6 [basic] Why use DTOs instead of returning JPA entities?
Entities model the database; DTOs model the API contract. Returning entities leaks internal fields (security risk), couples the API to the schema, triggers lazy-loading problems during JSON serialisation, and makes versioning hard. Use `record` DTOs and map with MapStruct or by hand.

### Q7 [basic] How does request validation work?
Add Bean Validation annotations on the DTO and `@Valid` on the parameter.
```java
public record CreateBooking(@NotNull UUID tripId, @Size(min=1, max=9) List<@Valid Passenger> passengers,
                            @Email String contactEmail) {}
@PostMapping ResponseEntity<?> create(@Valid @RequestBody CreateBooking req) { ... }
```
Failure throws `MethodArgumentNotValidException`, which you map to a 400 with field errors.

### Q8 [basic] How do you handle exceptions globally?
Use `@RestControllerAdvice` with `@ExceptionHandler` methods that return a consistent error body (`ProblemDetail`, RFC 9457 Problem Details, which replaced RFC 7807). Set `spring.mvc.problemdetails.enabled=true` so Spring's own errors (405, 415, missing params) use the same format. One place decides status codes, so controllers stay clean and no stack traces leak.
```java
@RestControllerAdvice
class ApiErrors {
  @ExceptionHandler(BookingNotFound.class)
  ProblemDetail notFound(BookingNotFound e){ return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage()); }
}
```

### Q9 [basic] What are idempotent and safe HTTP methods?
Safe (no state change): GET, HEAD. Idempotent (repeating gives the same result): GET, PUT, DELETE, HEAD. POST is not idempotent, so booking creation needs an idempotency key to make retries safe.

### Q10 [basic] How do you configure an app per environment?
`application.yml` plus `application-{profile}.yml` (`dev`, `uat`, `prod`), selected with `SPRING_PROFILES_ACTIVE`. Environment variables override files. Secrets never go in Git; read them from AWS Secrets Manager/Parameter Store. Use `@ConfigurationProperties` for typed, validated settings.

**Project hook (Part 1):** "In our service, controllers only translate HTTP to a service call, DTOs are records, errors go through one `@RestControllerAdvice` returning ProblemDetail, and config comes from environment variables injected by ECS."

---

## Part 2 - Mid Level (Q11-Q20)

### Q11 [mid] Describe the layering you use in a Spring Boot service.
Controller (HTTP only) -> Service (business rules, transactions) -> Repository (data access) plus clients/adapters for outside systems. Use constructor injection so dependencies are final and testable. Keep the service free of web types so a Kafka consumer or batch job can reuse it.

### Q12 [mid] How do you design pagination, filtering and sorting?
`GET /bookings?status=CONFIRMED&from=2026-10-01&page=0&size=20&sort=createdAt,desc`. Spring Data gives `Pageable`. Offset paging gets slower on deep pages, so for large or fast-changing data use keyset (cursor) paging: `WHERE (created_at, id) < (:ts, :id) ORDER BY created_at DESC, id DESC LIMIT 20`. Cap `size`, whitelist sort fields, and return a `nextCursor`.

### Q13 [mid] How do you make `POST /bookings` idempotent?
The client sends an `Idempotency-Key` header. The service stores `key -> request hash -> response` under a unique constraint in the same transaction as the booking. A repeat with the same key returns the stored response; the same key with a different body returns 422/409. Keys expire after about 24 hours. This protects against double charges on timeouts and retries.

### Q14 [mid] How do you secure the API (authentication and authorization)?
Use OAuth2/OIDC: the API is a resource server validating JWTs (signature, `exp`, `iss`, `aud`) from the identity provider. Roles/scopes drive coarse rules (`hasAuthority('SCOPE_bookings:write')`); object-level checks verify the caller owns the booking (stops IDOR). Use `SecurityFilterChain` beans with the lambda DSL, method security (`@PreAuthorize`), CORS allow-list and security headers. Always TLS.

### Q15 [mid] How do you call other services safely with `RestClient`/`WebClient`?
Always set connect and read timeouts, pool connections, and wrap calls with a circuit breaker and bounded retry (idempotent calls only, exponential backoff with jitter). `RestClient` (Spring 6.1+) is the modern blocking client; `RestTemplate` is in maintenance; `WebClient` is for reactive code. Declarative HTTP interfaces (`@HttpExchange`, `@GetExchange`) sit on top of `RestClient`, and Boot 4 can auto-configure them as HTTP service clients. Map downstream errors to your own exceptions so partner errors do not leak.

### Q16 [mid] Filter vs Interceptor vs AOP - when each?
Filter: servlet level, sees raw request/response (correlation id, security, request logging). Interceptor: Spring MVC level, knows the handler method (auth checks per controller, timing). AOP: method level on any bean (transactions, audit, metrics). Use the lowest level that has the information you need.

### Q17 [mid] How do you add logging, tracing and metrics?
Structured JSON logs with `traceId`, `bookingId`, no PII. Micrometer for metrics (`/actuator/prometheus` or Datadog/CloudWatch), Micrometer Tracing/OpenTelemetry for traces propagated over HTTP and Kafka headers (Boot 4 adds a dedicated OpenTelemetry starter). Keep label cardinality low (route template, not full URL). Actuator health groups feed the ALB/ECS health checks.

### Q18 [mid] How do you document and version the API?
Generate an OpenAPI spec (springdoc) and publish it; review it as a contract. Version only for breaking changes: URL (`/v2/...`) is simplest to see, header/media-type versioning is cleaner. Spring Framework 7 adds first-class API versioning in mapping annotations. Additive changes (new optional fields) need no new version; announce deprecations with dates and `Sunset` headers.

### Q19 [mid] How do you test a REST controller?
- Unit: plain JUnit + Mockito on the service.
- Slice: `@WebMvcTest(BookingController.class)` + `MockMvc`, mock the service, assert status/JSON/validation errors.
- Integration: `@SpringBootTest` + Testcontainers (PostgreSQL, Kafka) for real wiring.
- Contract: Pact or Spring Cloud Contract between consumer and provider.
Use `@MockitoBean` (Spring Framework 6.2+); `@MockBean` was deprecated in Boot 3.4 and removed in Boot 4.

### Q20 [mid] What causes `@Transactional` or other annotations to "not work" on a controller/service method?
Self-invocation (calling a method on `this` bypasses the proxy), `private` or `final` methods, the bean not being Spring-managed, checked exceptions not rolling back by default (`rollbackFor`), and work done in another thread (outside the transaction). Fix by moving the method to another bean or restructuring.

**Project hook (Part 2):** "We retried the payment-provider call only because the request carried an idempotency key, and a circuit breaker protected our threads when the partner was slow."

---

## Part 3 - Advanced and Design (Q21-Q30)

### Q21 [advanced] Design the booking API so a retry or timeout never double-books or double-charges.
- Client sends `Idempotency-Key`; server stores key + request hash + outcome with a unique constraint.
- Create the booking in `PENDING` in one DB transaction and write an outbox event.
- Reserve inventory (supplier call) with its own idempotency key; charge payment with a provider idempotency key.
- Confirm or compensate (saga): payment fails -> release inventory -> `CANCELLED`.
- Return `202` + `Location: /bookings/{id}` if the flow is async; the client polls or gets a webhook/event.
- Reconciliation job finds bookings stuck in `PENDING` and repairs them.
Trade-off: more states and moving parts, but safe retries without distributed transactions.

### Q22 [advanced] How do you prevent two users booking the last seat or room?
Atomic conditional update in the database: `UPDATE inventory SET available = available - 1 WHERE id = ? AND available > 0` and check the update count (or optimistic `@Version`). Use pessimistic locking (`FOR UPDATE`) only for short, hot rows. For external supplier inventory, use their hold/reserve API with an expiry, then confirm. Always make the confirm idempotent.

### Q23 [advanced] Which resilience patterns do you apply on a call chain (API -> supplier/payment), and in what order?
Timeout (always), bounded retry with backoff and jitter on idempotent calls, circuit breaker, bulkhead (separate pool per dependency), rate limiter, fallback, and deadline propagation so downstream stops when the caller gave up. Typical nesting: `Retry( CircuitBreaker( RateLimiter( TimeLimiter( call ))))`. Spring Framework 7 adds `@Retryable` and `@ConcurrencyLimit`; Resilience4j remains common. Warning: retries at every layer multiply load (retry storm).

### Q24 [advanced] Design an API that aggregates results from several slow partner systems (flight/hotel search).
Fan out in parallel with a per-partner timeout (for example 800 ms) using virtual threads or `CompletableFuture`, collect whatever returns in time, merge/rank, and return partial results with a flag. Circuit breaker + bulkhead per partner, cache popular searches (Caffeine/Redis with short TTL), normalise partner responses behind an adapter (anti-corruption layer), stream results with SSE if the UI wants progressive loading, and track per-partner latency and error metrics.

### Q25 [advanced] How do you handle long-running operations (refund, document generation) in a REST API?
Return `202 Accepted` with a `Location` to a job resource (`/refunds/{id}`) showing `status`, `progress` and result. Persist the job, process it with a worker (Kafka consumer or ECS task), make processing idempotent, and notify with a webhook or event when done. Never keep an HTTP request open for minutes.

### Q26 [advanced] How do you protect sensitive data (PII, card data) in the API?
Minimise: never store card numbers; use payment tokens from the processor. Encrypt in transit (TLS) and at rest (KMS), field-level encryption for sensitive columns, mask PII in logs and error messages, strict authorization per object, audit logs for access, short-lived tokens, least-privilege IAM roles, and dependency/secret scanning. Know the OWASP API Top 10 (BOLA/IDOR, mass assignment, SSRF, unrestricted resource consumption).

### Q27 [advanced] Performance: the endpoint's p99 doubled after a release. How do you investigate?
Check deploy markers and traces to find the slow span (DB, downstream, CPU). Look at saturation: Hikari pending connections, thread pools, GC pauses, CPU throttling. Common causes: N+1 queries, missing index, a new synchronous call, bigger payloads, cache misses, retry storms. Capture a JFR/async-profiler flame graph, fix the biggest bar, and roll back first if the SLO is burning.

### Q28 [advanced] Virtual threads in a Spring Boot REST service: benefits and pitfalls?
`spring.threads.virtual.enabled=true` (Java 21+) lets each request run on a virtual thread, so blocking I/O no longer ties up scarce OS threads, with simple imperative code. Pitfalls: the DB pool is now the real limit (cap concurrency with a semaphore/bulkhead), `synchronized` pinning in older JDKs (fixed in Java 24), heavy `ThreadLocal` use, and no gain for CPU-bound code. Load-test before and after.

### Q29 [advanced] How do you do zero-downtime deployments for the API?
Rolling or blue/green on ECS behind an ALB with health checks (ECS has built-in blue/green since July 2025, with canary and linear traffic shifting, so CodeDeploy is optional), `server.shutdown=graceful`, deregistration delay longer than request time, backward-compatible API and DB changes (expand/contract), feature flags, canary traffic with automatic rollback on error-rate or latency alarms. Never ship a code change and its breaking schema change in one step.

### Q30 [advanced] Plan a migration from Spring Boot 3.x to 4.x (or Boot 2 to 3).
1) Upgrade to the latest 3.5 patch and clear deprecation warnings. 2) Java 17 minimum (25 recommended). 3) Run OpenRewrite recipes; `javax.*` -> `jakarta.*` if coming from Boot 2. 4) Handle Boot 4 modular starters, Jackson 3, test annotation changes, Spring Security 7, Hibernate version changes. 5) Check third-party library compatibility. 6) Run integration, contract and performance tests. 7) Canary rollout with rollback. Mention Framework 7 benefits: built-in resilience annotations, API versioning, JSpecify null-safety, HTTP service clients.

**Project hook (Part 3):** "The hardest case was [your real incident: duplicate booking / slow partner / pool exhaustion]. Detection, root cause, fix, and what we changed so it can't recur."

---

## Quick revision card
- Controller thin, service holds rules, DTOs not entities.
- One error format (ProblemDetail), validate at the edge.
- Idempotency key for every money/booking POST.
- Timeouts, bounded retries, circuit breaker on every remote call.
- Observability: traceId in logs, RED metrics, health groups.
- Safe change: backward-compatible APIs, graceful shutdown, canary.

## 60-second answer for this point
"Controllers stay thin and only translate HTTP: validated record DTOs in, a service call, the right status code out, errors through one `@RestControllerAdvice` returning RFC 9457 Problem Details. Every booking or payment POST carries an Idempotency-Key stored under a unique constraint, so retries never double-book. Outbound calls use RestClient with timeouts, a circuit breaker and bounded retries on idempotent calls. Security is an OAuth2 resource server with object-level checks. Traces, RED metrics and readiness health groups feed the ALB, and releases are backward compatible with graceful shutdown and a canary on ECS."
