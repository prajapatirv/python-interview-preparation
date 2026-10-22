---
id: profile-java-genai-spring-boot
title: Java + GenAI profile (2/9): Spring Boot, 15 functional-requirement questions
stack: java
skill: spring-boot
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).
Versions as of late 2026: Spring Boot 4.x on Spring Framework 7 (Java 17 baseline, Java 25 recommended).

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] How does Spring Boot auto-configuration work? Build a company starter to show it.
tags: auto-configuration, conditional, starter, spring-boot, autoconfiguration-imports, profile-java-genai

**Start here: the concepts**
- **Auto-configuration:** configuration classes Boot applies only when their conditions hold (a class is on the classpath, a property is set, no user bean exists).
- **Conditions:** `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty`, `@ConditionalOnWebApplication`.
- **Registration:** classes listed in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (the old `spring.factories` key was removed in Boot 3).

**The live scenario (functional requirement)**
*FR: "All 40 microservices must emit the same audit log for every state-changing request, with zero copy-paste."*

**What the interviewer is really checking**
That you understand the mechanism behind "magic", and that user configuration always wins.

**How I answer it**
1. Create `audit-spring-boot-starter` (dependencies) plus an autoconfigure module.
2. `@AutoConfiguration` class creating an `AuditFilter` and an `AuditPublisher`, guarded by `@ConditionalOnWebApplication` and `@ConditionalOnProperty(prefix="company.audit", name="enabled", matchIfMissing=true)`.
3. Every bean is `@ConditionalOnMissingBean`, so a team can override it by declaring its own.
4. Typed settings with `@ConfigurationProperties("company.audit")`, plus the configuration processor for IDE hints.
5. Register in the `AutoConfiguration.imports` file. Services just add the dependency.
6. Debugging: `--debug` or `/actuator/conditions` shows which auto-configurations matched and why.

**Trade-offs and what can go wrong**
- Too much hidden behaviour surprises teams; document every property and keep the starter small.
- Ordering: use `@AutoConfiguration(after = ...)` when you depend on another auto-config's beans.
- Component scanning the starter's package by accident bypasses the conditions.

**How I'd monitor it**
Audit events per service in the log platform; a dashboard that shows services missing audit traffic.

**Follow-ups to expect**
- *What does `@SpringBootApplication` contain?* -> `@SpringBootConfiguration`, `@EnableAutoConfiguration`, `@ComponentScan`.
- *How do you exclude one auto-config?* -> `@SpringBootApplication(exclude = ...)` or `spring.autoconfigure.exclude`.
- *What changed in Boot 4?* -> The autoconfigure jar was split into smaller modules, so starters pull in only what they need.

**60-second answer**
"Auto-configuration is just conditional configuration classes: Boot reads the `AutoConfiguration.imports` file and applies each class whose conditions pass, like a class on the classpath or no user bean. To give 40 services a consistent audit log, I'd build a starter whose auto-config registers an audit filter only for web apps, enabled by a property, and every bean is `@ConditionalOnMissingBean` so teams can override it. `/actuator/conditions` or `--debug` shows exactly why something did or didn't apply."

### Q2 [mid] Explain bean scopes and lifecycle, and the prototype-in-singleton trap.
tags: bean-scope, lifecycle, prototype, singleton, postconstruct, objectprovider, profile-java-genai

**Start here: the concepts**
- **Scopes:** singleton (default, one per context), prototype (new each lookup), request, session, application.
- **Lifecycle:** instantiate -> inject dependencies -> `BeanPostProcessor` before -> `@PostConstruct` -> post-processor after (proxies made here) -> in use -> `@PreDestroy`.
- Spring does **not** call destroy callbacks on prototype beans.

**The live scenario (functional requirement)**
*FR: "Each document-summarisation job needs its own `PromptContext` holding job-specific state, while the summariser service is shared."* A developer made `PromptContext` prototype and injected it into the singleton service; every job shared one context and summaries mixed data between customers.

**What the interviewer is really checking**
That injection happens once, and how to get a fresh prototype per use.

**How I answer it**
1. A prototype injected into a singleton is created **once**, when the singleton is built.
2. Fix: inject `ObjectProvider<PromptContext>` and call `getObject()` per job, or use a method annotated `@Lookup`.
3. Even better: don't make it a bean at all. Job state is plain data: `new PromptContext(job)` or a record passed as a parameter. Beans are for collaborators, not per-request data.
4. Singletons must be stateless or hold only thread-safe state, since all request threads share them.
5. Use `@PostConstruct` for warm-up (load a prompt template), `@PreDestroy` to close clients.

**Trade-offs and what can go wrong**
- Mutable fields on singletons are a concurrency bug.
- Request scope outside a web request throws; scoped proxies hide that until runtime.
- Heavy work in `@PostConstruct` slows startup and readiness.

**How I'd monitor it**
Tests that run two jobs concurrently and assert isolation; startup time per bean via `/actuator/startup` (with `BufferingApplicationStartup`).

**Follow-ups to expect**
- *Constructor vs field injection?* -> Constructor: immutable, testable, required dependencies explicit.
- *What is a BeanPostProcessor used for?* -> AOP proxies, `@Async`, `@Transactional`, validation.
- *How do you make a bean lazy?* -> `@Lazy` or `spring.main.lazy-initialization=true`.

**60-second answer**
"Singleton is the default; prototype gives a new instance per lookup, but if you inject a prototype into a singleton, injection happens once, so everyone shares it. We hit exactly that with a per-job prompt context. The fix is `ObjectProvider.getObject()` per job, or better, not making per-job state a bean at all and just passing a record. Singletons stay stateless, warm-up goes in `@PostConstruct`, cleanup in `@PreDestroy`, which Spring never calls for prototypes."

### Q3 [senior] @Transactional did not roll back. Explain propagation and the common pitfalls.
tags: transactional, propagation, rollback, self-invocation, proxy, spring-data, profile-java-genai

**Start here: the concepts**
- **Proxy-based:** `@Transactional` works through a proxy wrapping the bean; only calls coming through the proxy are transactional.
- **Rollback rules:** by default roll back on unchecked exceptions and `Error`, **not** on checked exceptions.
- **Propagation:** `REQUIRED` (join or create, default), `REQUIRES_NEW` (suspend and start a new one), `NESTED` (savepoint), `MANDATORY`, `SUPPORTS`, `NOT_SUPPORTED`, `NEVER`.

**The live scenario (functional requirement)**
*FR: "Placing an order must save the order and reserve stock atomically; an audit row must be written even if the order fails."* In production, orders were saved without stock reservation.

**What the interviewer is really checking**
The proxy mechanism and rollback rules, plus choosing propagation intentionally.

**How I answer it**
1. **Found the causes:** `placeOrder()` called `this.reserveStock()` (self-invocation bypasses the proxy), and `reserveStock` threw a checked `StockException`, which doesn't trigger rollback.
2. Put `@Transactional` on the public entry method `placeOrder` in the service, so both writes join one transaction; make `StockException` unchecked or use `rollbackFor = StockException.class`.
3. **Audit even on failure:** an `AuditService.record()` in a separate bean with `REQUIRES_NEW`, so it commits independently.
4. Keep transactions short: no HTTP or LLM calls inside them. They hold DB connections and locks while waiting.
5. Read paths: `@Transactional(readOnly = true)` lets Hibernate skip dirty checking.
6. Across services there is no shared transaction; that's the outbox and saga patterns.

**Trade-offs and what can go wrong**
- `REQUIRES_NEW` takes a second connection; under load this can exhaust the pool (deadlock on the pool itself).
- Private methods and final classes can't be proxied as expected.
- Catching the exception inside the transactional method and not rethrowing commits the partial work.

**How I'd monitor it**
Hikari active connections and wait time, transaction duration, and a data-consistency check (orders without reservations) as a scheduled query with alerting.

**Follow-ups to expect**
- *Where should `@Transactional` live: controller, service or repository?* -> Service layer, the use-case boundary.
- *What is `UnexpectedRollbackException`?* -> An inner `REQUIRED` call marked the shared transaction rollback-only, and the outer method tried to commit.
- *Isolation levels?* -> Default is the database's (often READ COMMITTED); raise only for specific anomalies.

**60-second answer**
"Two classic causes: self-invocation, because `@Transactional` works through a proxy and `this.method()` skips it, and checked exceptions, which don't roll back by default. I put the annotation on the public service entry point so order and stock join one transaction, and use rollbackFor or unchecked exceptions. The audit row goes through a separate bean with REQUIRES_NEW so it commits even when the order fails, watching pool size since that needs a second connection. And no remote calls inside a transaction."

### Q4 [mid] How do you manage configuration and secrets across dev, test and prod?
tags: configuration, profiles, configurationproperties, secrets, vault, externalized-config, profile-java-genai

**Start here: the concepts**
- **Externalised configuration:** the same artifact runs everywhere; config comes from files, environment variables, config servers.
- **Property precedence:** command-line args > env vars > profile-specific files > `application.yml`.
- **`@ConfigurationProperties`:** typed, validated configuration objects (records work).

**The live scenario (functional requirement)**
*FR: "The assistant service uses a different LLM endpoint, model name and API key per environment; keys must never be in git; ops must rotate a key without redeploying."*

**What the interviewer is really checking**
12-factor thinking, typed config, and real secret management.

**How I answer it**
1. One image for all environments; `application.yml` holds safe defaults, profile files (`application-prod.yml`) hold non-secret differences.
2. Typed, validated settings:

```java
@ConfigurationProperties("assistant.llm") @Validated
record LlmProps(@NotBlank String baseUrl, @NotBlank String model, Duration timeout) {}
```

3. **Secrets** from a secret store: Kubernetes Secrets (ideally synced from Vault or a cloud secret manager by the External Secrets Operator), or Spring Cloud Vault. Injected as env vars or mounted files (`spring.config.import=configtree:/etc/secrets/`).
4. **Rotation:** mounted secret files update in place; the client re-reads on a refresh event, or supports two valid keys during rotation. Otherwise a rolling restart is the safe default.
5. Fail fast: validation stops the app at startup if a required setting is missing.

**Trade-offs and what can go wrong**
- `@Value` scattered everywhere is untyped and hard to find; centralise in properties classes.
- Env vars can leak in crash dumps and `/actuator/env`; restrict actuator and mask values.
- Profile explosion (`prod-eu-blue`) becomes unmanageable; prefer environment-specific values from the platform.

**How I'd monitor it**
Startup validation failures, secret age vs rotation policy, actuator endpoints locked down.

**Follow-ups to expect**
- *Spring Cloud Config vs ConfigMaps?* -> Config Server adds versioned central config and refresh; on Kubernetes ConfigMaps plus GitOps usually suffice.
- *How does `@RefreshScope` work?* -> Rebuilds the bean on a refresh event; use sparingly.
- *How do you activate a profile?* -> `SPRING_PROFILES_ACTIVE` env var.

**60-second answer**
"Same artifact everywhere, with config from outside. Defaults in application.yml, environment differences in profiles or platform env vars, all bound to validated `@ConfigurationProperties` records so the app fails fast if the LLM endpoint or model is missing. Secrets never live in git: they come from Vault or a cloud secret manager, synced into Kubernetes Secrets and mounted as files. For rotation, the provider allows two keys at once and we refresh or do a rolling restart. I also lock down `/actuator/env`."

### Q5 [senior] Make a Spring Boot service production-observable with Actuator, Micrometer and OpenTelemetry.
tags: actuator, micrometer, opentelemetry, observability, health-checks, tracing, profile-java-genai

**Start here: the concepts**
- **Actuator:** production endpoints such as `health`, `info`, `metrics`, `prometheus`, `loggers`.
- **Micrometer:** a metrics facade (like SLF4J for metrics) plus the **Observation API** that produces metrics and traces from one instrumentation point.
- **OpenTelemetry:** the vendor-neutral standard for traces, metrics and logs; Boot 4 has a dedicated OpenTelemetry starter.

**The live scenario (functional requirement)**
*FR: "Support must see, for any slow chat answer, whether time went to retrieval, the LLM or the database, and get paged when p99 exceeds 4 s."*

**What the interviewer is really checking**
That you instrument the golden signals and traces, not just enable `/health`.

**How I answer it**
1. Add Actuator and expose only `health`, `info`, `prometheus` publicly on a management port.
2. **Health groups** for Kubernetes: `liveness` (process ok) and `readiness` (can serve: DB, vector store), via `management.endpoint.health.probes.enabled`.
3. **Metrics:** HTTP server timers come free (`http_server_requests_seconds`); I add custom timers and counters: `llm.call.duration` by model, `llm.tokens` by type, `retrieval.duration`.
4. **Tracing:** OpenTelemetry starter, OTLP export to the collector, W3C trace context propagated through RestClient, Kafka and JDBC. Each span shows retrieval vs LLM vs DB.
5. Logs in JSON with `traceId` (Boot's structured logging), so a trace links to its logs.
6. Alerts on SLOs (p99 latency, error rate) and burn rate, not on CPU alone.

**Trade-offs and what can go wrong**
- High-cardinality tags (user id, full prompt) explode metric storage; keep tags bounded.
- 100% trace sampling is costly at scale; sample head-based at a few percent plus always keep errors (tail sampling in the collector).
- Exposing all actuator endpoints publicly leaks env and heap dumps.

**How I'd monitor it**
This *is* the monitoring: RED dashboards per endpoint, LLM latency and token panels, trace search for slow requests.

**Follow-ups to expect**
- *Custom health indicator?* -> Implement `HealthIndicator`; keep it cheap and don't put downstream dependencies in liveness.
- *Change log level at runtime?* -> `/actuator/loggers/{name}` POST.
- *Micrometer vs OpenTelemetry?* -> Micrometer instruments; it can export through OTLP; they complement each other.

**60-second answer**
"I add Actuator with only health, info and prometheus exposed, on a separate port, and split health into liveness and readiness groups for Kubernetes. Micrometer gives HTTP timers for free; I add LLM latency by model, token counts and retrieval time. Tracing goes through the OpenTelemetry starter to a collector, so one slow chat request shows retrieval, LLM and DB spans, and JSON logs carry the trace id. Alerts are on p99 and error-rate SLOs, and I keep metric tags low-cardinality."

### Q6 [senior] Fix a slow Spring Data JPA endpoint: N+1, pagination and connection pool.
tags: jpa, hibernate, n-plus-one, entity-graph, pagination, hikaricp, performance, profile-java-genai

**Start here: the concepts**
- **N+1:** one query loads N parents, then one query per parent loads its lazy children.
- **Fixes:** fetch join, `@EntityGraph`, batch fetching (`hibernate.default_batch_fetch_size`), DTO projections.
- **HikariCP:** Boot's default connection pool; `maximumPoolSize` default 10.

**The live scenario (functional requirement)**
*FR: "The booking history page shows a customer's last 50 bookings with their segments in under 300 ms."* It takes 2.4 s; SQL logs show 51 queries.

**What the interviewer is really checking**
That you diagnose from SQL, know the fixes and their pitfalls (fetch join + pagination).

**How I answer it**
1. **See it:** enable SQL statistics in test (`hibernate.generate_statistics`) or a datasource proxy; count queries per request. 51 queries = N+1 on `segments`.
2. Fix with `@EntityGraph(attributePaths = "segments")` on the repository method, or a `JOIN FETCH` query.
3. **Pagination trap:** fetch-joining a collection with `Pageable` makes Hibernate paginate in memory (warning `HHH90003004`). Better: page the booking ids first, then fetch bookings with segments `WHERE id IN (:ids)`, or use batch fetching.
4. For read-only screens, a **DTO projection** (`select new BookingView(...)` or an interface projection) skips entity management.
5. Indexes on `customer_id, created_at desc`; check the plan with `EXPLAIN`.
6. Disable **open-session-in-view** (`spring.jpa.open-in-view=false`) so lazy loading can't sneak into serialisation.
7. Pool: size from measured concurrency, not "bigger is better"; watch `hikaricp_connections_pending`.

**Trade-offs and what can go wrong**
- Eager fetching everywhere (`FetchType.EAGER`) causes huge joins on unrelated screens.
- Multiple bag fetch joins throw `MultipleBagFetchException`; use `Set` or separate queries.
- Long transactions hold connections; keep them short.

**How I'd monitor it**
Queries per request, slow-query log, Hikari pending and usage metrics, endpoint p99.

**Follow-ups to expect**
- *`findAll()` on a big table?* -> Never; page, or stream with a cursor.
- *Second-level cache?* -> For read-mostly reference data; not for bookings.
- *Optimistic locking?* -> `@Version` column; concurrent updates get `OptimisticLockException`.

**60-second answer**
"51 queries for 50 bookings is N+1 on the lazy segments collection. I fix it with an entity graph or fetch join, but not combined with pagination on a collection, because Hibernate then paginates in memory; I page the ids first and fetch the graph for those ids, or use batch fetching. For a read-only screen a DTO projection is lighter still. Then indexes checked with EXPLAIN, open-in-view turned off, and the Hikari pool sized from metrics. That took the page from 2.4 s to around 120 ms."

### Q7 [senior] Secure a Spring Boot API as an OAuth2 resource server with JWT.
tags: spring-security, oauth2, jwt, resource-server, method-security, authorization, profile-java-genai

**Start here: the concepts**
- **Authentication vs authorisation:** who you are vs what you may do.
- **OAuth2 / OIDC:** an identity provider (Keycloak, Okta, Entra ID, Cognito) issues access tokens; APIs are **resource servers** that validate them.
- **JWT:** a signed token with claims (`sub`, `scope`, `exp`); validated with the issuer's public keys (JWKS), no session needed.

**The live scenario (functional requirement)**
*FR: "Agents can read any customer's tickets; customers only their own; only supervisors can trigger the AI auto-reply feature."*

**What the interviewer is really checking**
Stateless security wiring, scope/role mapping, and object-level authorisation (the top API vulnerability).

**How I answer it**
1. `spring-boot-starter-oauth2-resource-server` with `spring.security.oauth2.resourceserver.jwt.issuer-uri`. Spring fetches JWKS and validates signature, expiry, issuer, and I add an audience validator.
2. `SecurityFilterChain`: stateless sessions, CSRF off for a pure token API, every endpoint authenticated by default.
3. Map claims to authorities (`scope` -> `SCOPE_x`, or a custom `roles` claim converter).
4. Coarse rules in the chain (`/admin/**` needs `ROLE_SUPERVISOR`); fine rules with method security: `@PreAuthorize("hasRole('SUPERVISOR')")` on `triggerAutoReply`.
5. **Object-level check:** a customer reading ticket 123 must own it: `@PreAuthorize("@ticketAccess.canRead(authentication, #id)")` or a check in the service. Never trust ids from the client alone.
6. Short-lived access tokens (5–15 min); revocation via short expiry plus refresh tokens at the client.

**Trade-offs and what can go wrong**
- JWTs can't be revoked instantly; keep them short or use opaque tokens with introspection for high-risk operations.
- Putting too much into the token (all permissions) makes it big and stale.
- Missing audience validation lets tokens for another API be accepted.

**How I'd monitor it**
401/403 rates by endpoint, spikes of 403 on object access (enumeration attempts), auth failures in the security log.

**Follow-ups to expect**
- *Service-to-service auth?* -> Client-credentials grant, or mTLS through a service mesh.
- *Where do you store tokens in the browser?* -> Prefer a backend-for-frontend with HttpOnly cookies over localStorage.
- *What is BOLA?* -> Broken object-level authorisation, number one in the OWASP API Top 10.

**60-second answer**
"The API is an OAuth2 resource server: Spring validates the JWT against the identity provider's JWKS, expiry, issuer and audience, statelessly. I map scopes and roles to authorities, keep coarse URL rules in the filter chain, and put fine rules on methods, so only supervisors can trigger the AI auto-reply. The key one is object-level: a customer may read only their own tickets, checked in the service, not trusted from the URL. Tokens are short-lived, and I alert on 403 spikes."

### Q8 [mid] Add caching with @Cacheable and Redis without serving stale or stampeding.
tags: caching, cacheable, redis, ttl, cache-stampede, spring-cache, profile-java-genai

**Start here: the concepts**
- **Spring Cache abstraction:** `@Cacheable`, `@CachePut`, `@CacheEvict` over a provider (Caffeine local, Redis distributed).
- **Cache-aside:** read cache, on miss load from source and store.
- **Stampede:** many requests miss the same key at once and all hit the database.

**The live scenario (functional requirement)**
*FR: "Hotel content (descriptions, images, amenities) is read 5,000 times per second and changes a few times a day; the content DB must stay under 30% CPU."*

**What the interviewer is really checking**
Correct invalidation, TTLs, stampede protection, and local vs distributed trade-offs.

**How I answer it**
1. `@Cacheable(cacheNames = "hotel", key = "#hotelId")` on the service read method; Redis as the shared cache with TTL 30 min plus random jitter.
2. On update, `@CacheEvict(key = "#hotel.id")`, or publish a "hotel changed" event so every instance evicts.
3. **Two levels:** Caffeine in-process (seconds-level TTL, absorbs hot keys) in front of Redis.
4. **Stampede:** `@Cacheable(sync = true)` serialises loads per key within an instance; across instances, a short Redis lock or serve-stale-while-refresh.
5. Cache **DTOs** serialised as JSON, not JPA entities with lazy proxies.
6. Size limits and eviction policy so the cache can't eat memory.

**Trade-offs and what can go wrong**
- `@Cacheable` uses the proxy; self-invocation is not cached.
- Caching `null` or errors hides recovery; use `unless = "#result == null"`.
- A Redis outage shouldn't take the app down; use a cache error handler that falls back to the DB with a rate limit.

**How I'd monitor it**
Hit ratio per cache, Redis latency and memory, DB QPS, eviction rate.

**Follow-ups to expect**
- *Write-through vs write-behind?* -> Write-through updates cache with the DB synchronously; write-behind batches later and risks loss.
- *How do you choose TTL?* -> From how stale the business tolerates, plus jitter.
- *Can you cache LLM answers?* -> Exact-match cache for identical prompts; semantic cache by embedding similarity for near-duplicates, carefully.

**60-second answer**
"Hotel content is read-heavy and changes rarely, ideal for cache-aside. `@Cacheable` on the service, Redis as the shared layer with a 30-minute TTL plus jitter, and a small Caffeine layer in front for hot keys. Updates evict via an event so all instances drop the key. For stampedes I use `sync = true` locally and serve-stale-while-refresh across instances. I cache DTOs, not entities, and if Redis is down the app falls back to the DB rather than failing."

### Q9 [mid] Run scheduled jobs and async work safely when the service has 6 replicas.
tags: scheduled, async, shedlock, distributed-lock, executor, spring-boot, profile-java-genai

**Start here: the concepts**
- **`@Scheduled`:** runs a method on a cron or fixed rate, **in every instance**.
- **`@Async`:** runs a method on a task executor, returning `CompletableFuture` or void.
- **Distributed lock:** ensures only one instance runs a job (ShedLock using the DB or Redis).

**The live scenario (functional requirement)**
*FR: "Every night at 2 am, re-embed documents changed that day; the nightly email digest must go out exactly once."* With 6 replicas every customer got 6 emails.

**What the interviewer is really checking**
That you know scheduling is per JVM and how to make it single-run and observable.

**How I answer it**
1. Add **ShedLock**: `@SchedulerLock(name = "digest", lockAtMostFor = "30m", lockAtLeastFor = "1m")` with a JDBC lock table; only one replica runs it.
2. Make the job **idempotent** anyway (record "digest sent for date X"), because locks can expire mid-run.
3. For heavy jobs, better: a Kubernetes **CronJob** or a batch platform, separate from the API pods.
4. `@Async` with a **named, bounded** `ThreadPoolTaskExecutor` (or virtual threads); handle exceptions with an `AsyncUncaughtExceptionHandler`.
5. For durable background work (re-embedding thousands of docs) use a queue/topic, not in-memory `@Async`, so a pod restart doesn't lose work.

**Trade-offs and what can go wrong**
- `@Async` on a method in the same class (self-invocation) runs synchronously.
- In-memory async work is lost on deploys.
- `lockAtMostFor` too short lets a second instance start while the first still runs.

**How I'd monitor it**
Job last-success timestamp (alert if older than 26 hours), duration, items processed, failures.

**Follow-ups to expect**
- *fixedRate vs fixedDelay?* -> fixedRate starts on a schedule regardless; fixedDelay waits after completion.
- *Default @Async executor?* -> Boot auto-configures a `ThreadPoolTaskExecutor` (or virtual threads when enabled).
- *Quartz?* -> Clustered scheduling with persistence and misfire handling, for complex schedules.

**60-second answer**
"`@Scheduled` runs on every replica, which is why customers got six emails. I add ShedLock with a JDBC lock table so one instance runs the job, and I still make the job idempotent by recording what was sent, because locks can expire. Heavy nightly work like re-embedding I'd move to a Kubernetes CronJob or a queue so a deploy doesn't kill it. `@Async` gets a named bounded executor and an exception handler, and I alert on the job's last-success timestamp."

### Q10 [senior] How do you test a Spring Boot service: slices, Testcontainers and full context?
tags: testing, springboottest, webmvctest, datajpatest, testcontainers, serviceconnection, profile-java-genai

**Start here: the concepts**
- **Unit tests:** plain JUnit + Mockito, no Spring.
- **Slice tests:** `@WebMvcTest` (controllers), `@DataJpaTest` (repositories), `@JsonTest`: a partial context, fast.
- **`@SpringBootTest`:** the full context, for integration tests.
- **Testcontainers:** real Postgres, Kafka, Redis in Docker; `@ServiceConnection` wires their URLs automatically.

**The live scenario (functional requirement)**
*FR: "The RAG service must be safe to deploy several times a day."* The test suite took 25 minutes because every test used `@SpringBootTest` with H2, and still missed a Postgres-specific pgvector query bug.

**What the interviewer is really checking**
A test pyramid, real dependencies where it matters, and fast feedback.

**How I answer it**
1. **Unit** for domain logic (chunking rules, prompt building): milliseconds.
2. **`@WebMvcTest`** for controllers with `MockMvc`/`MockMvcTester`, mocking services with `@MockitoBean` (replaced `@MockBean`).
3. **`@DataJpaTest` + Testcontainers Postgres with pgvector**, never H2 for a vector query: the bug only shows on the real engine.
4. **Few `@SpringBootTest`** end-to-end tests with Kafka and Postgres containers; reuse one context (same config), so Spring's context cache keeps them fast.
5. **LLM calls:** a stub `ChatModel` bean or WireMock for the HTTP API; deterministic tests never call a real model. Separate evaluation suites check quality.
6. Contract tests (Spring Cloud Contract or Pact) for APIs other teams consume.

**Trade-offs and what can go wrong**
- Too many distinct `@MockitoBean` combinations create many contexts and slow the suite.
- Shared containers need data isolation (unique ids or truncation).
- Mocks drift from reality; contract tests close that gap.

**How I'd monitor it**
Suite duration trend, flaky-test rate, coverage of critical paths, escaped defects.

**Follow-ups to expect**
- *Why not H2?* -> Different SQL dialect and features; false confidence.
- *Testing Kafka listeners?* -> Testcontainers Kafka plus Awaitility for async assertions.
- *Testing security?* -> `@WithMockUser` or `jwt()` request post-processors.

**60-second answer**
"A pyramid: fast unit tests for domain logic, slice tests like `@WebMvcTest` and `@DataJpaTest` for each layer, and a few full `@SpringBootTest` journeys. Persistence tests run on Testcontainers with real Postgres and pgvector, because H2 hid a real vector-query bug. `@ServiceConnection` wires the containers automatically. LLM calls are stubbed so tests are deterministic, with separate evaluation suites for answer quality. That took us from 25 minutes to about 6."

### Q11 [senior] Reduce Spring Boot startup time and memory for Kubernetes.
tags: startup-time, graalvm, native-image, cds, aot, lazy-initialization, virtual-threads, profile-java-genai

**Start here: the concepts**
- **Startup cost:** classpath scanning, bean creation, Hibernate metadata, JIT warm-up.
- **CDS / AOT cache:** the JVM stores pre-parsed classes from a training run (Java 24+ adds the AOT cache, JEP 483).
- **GraalVM native image:** compile ahead of time into a binary; starts in ~100 ms with low memory, but a long build and reflection limits.

**The live scenario (functional requirement)**
*FR: "Scale the summarisation service from 2 to 30 pods within a minute when the batch queue grows."* Each pod took 45 s to become ready.

**What the interviewer is really checking**
Measured, layered options and their trade-offs.

**How I answer it**
1. **Measure:** `/actuator/startup` shows slow beans; often a few (eager connections, big caches loaded at boot, a prompt-template scan).
2. **Quick wins:** load caches lazily or asynchronously after readiness; trim unused starters; `spring.main.lazy-initialization=true` for non-critical beans (careful: errors move to first request).
3. **JVM:** class data sharing / the AOT cache from a training run; Boot supports extracting the jar for CDS. Typically 30–50% faster.
4. **Native image** with Spring AOT for scale-to-zero style workloads: startup under 1 s, smaller memory; costs longer builds and reflection config, and peak throughput can be lower than a warmed JIT.
5. **Readiness probe** tied to real readiness; a startup probe for slow boots.
6. Scale on queue depth (KEDA) earlier rather than only making pods faster.

**Trade-offs and what can go wrong**
- Lazy init hides misconfiguration until traffic arrives.
- Native images break on dynamic proxies/reflection without hints; test the native build in CI.
- JIT warm-up means first requests are slow even after "ready"; warm up with synthetic calls.

**How I'd monitor it**
Time to ready per pod, scale-out time vs queue growth, first-minute latency of new pods.

**Follow-ups to expect**
- *CRaC?* -> Checkpoint/restore of a warmed JVM; supported by some JDK distributions and by Spring.
- *Does `spring.threads.virtual.enabled` speed startup?* -> No, it changes request concurrency.
- *Memory?* -> Right-size heap with MaxRAMPercentage; native images also cut RSS.

**60-second answer**
"I measure first with the startup actuator; usually a few beans load big caches or connect eagerly, and moving that after readiness gives quick wins. Then the JVM's class data sharing / AOT cache from a training run cuts startup a lot with no code change. For true scale-to-zero I'd consider a GraalVM native image, accepting longer builds and reflection hints. And I make the scaling trigger smarter, KEDA on queue depth, so pods start before the backlog hurts."

### Q12 [architect] Plan an upgrade from Spring Boot 2.7 / Java 8 to Spring Boot 4 / Java 25.
tags: migration, spring-boot-4, jakarta, java-25, openrewrite, upgrade, profile-java-genai

**Start here: the concepts**
- **Boot 3 (2022):** Java 17 baseline, `javax.*` -> `jakarta.*`, Spring Security 6.
- **Boot 4 (Nov 2025):** Spring Framework 7, Java 17 baseline with Java 25 support, Jakarta EE 11, Jackson 3, modular auto-configuration, JSpecify null-safety, built-in API versioning.
- **OpenRewrite:** automated, recipe-based refactoring (Java version, Boot version, javax->jakarta).

**The live scenario (functional requirement)**
*FR: "Spring Boot 2.7 is out of OSS support; security says all 25 services must be on supported versions within two quarters, without a feature freeze."*

**What the interviewer is really checking**
An incremental, low-risk plan with tooling, not a big-bang rewrite.

**How I answer it**
1. **Inventory:** versions, dependencies, unsupported libraries (old Hystrix, Springfox, Spring Cloud Netflix) per service.
2. **Hop, don't leap:** Java 8 -> 17 on Boot 2.7 first, then Boot 2.7 -> 3.5 (jakarta switch), then 3.5 -> 4.x, then Java 21/25. Each hop is releasable.
3. **Automate:** OpenRewrite recipes for the Java upgrade, javax->jakarta and Boot migrations, run from the Maven/Gradle plugin, reviewed as normal PRs.
4. **Fix the manual parts:** Security config to `SecurityFilterChain` lambdas, replace Springfox with springdoc, Hystrix with Resilience4j or Framework 7 resilience, Jackson 3 changes, renamed properties (`spring-boot-properties-migrator` reports them at runtime).
5. **Safety net:** characterisation tests and contract tests before upgrading; canary deploys; compare error rates and latency.
6. **Order:** shared libraries and the company parent POM first, then services in waves, lowest risk first.

**Trade-offs and what can go wrong**
- Libraries that are not Jakarta-ready block the jump; find replacements early.
- Behaviour changes (trailing-slash matching removed in Spring 6, Jackson defaults) break clients silently; contract tests catch them.
- Big-bang upgrades of 25 services at once make failures hard to isolate.

**How I'd monitor it**
A version dashboard (service -> Java/Boot version), error-rate and latency diff between canary and baseline.

**Follow-ups to expect**
- *Why not jump straight to Boot 4?* -> You must be on 3.5 first; the guide assumes it, and the property migrator works hop by hop.
- *What is the biggest Boot 3 change?* -> The jakarta namespace and Java 17 baseline.
- *How do you handle a library with no Jakarta version?* -> Replace it, or fork/shade as a last resort.

**60-second answer**
"I'd go in releasable hops: Java 17 on Boot 2.7, then Boot 3.5 for the jakarta move, then Boot 4 and Java 21 or 25. OpenRewrite recipes do most of the mechanical change, javax to jakarta, version bumps and deprecated APIs, as reviewable PRs. The manual work is security config, replacing dead libraries like Springfox and Hystrix, Jackson 3, and renamed properties, where the properties migrator helps. Shared parent POM first, then services in waves behind canaries, with contract tests as the safety net."

### Q13 [senior] Spring Framework 7 resilience features vs Resilience4j: what do you use for retries and limits?
tags: resilience, retryable, concurrencylimit, resilience4j, spring-framework-7, fault-tolerance, profile-java-genai

**Start here: the concepts**
- **Spring Framework 7** added core resilience: `@Retryable` (with backoff and jitter) and `@ConcurrencyLimit`, enabled with `@EnableResilientMethods`, plus `RetryTemplate`.
- **Resilience4j:** circuit breaker, retry, bulkhead, rate limiter, time limiter, with rich metrics.
- **Retry safety:** retry only idempotent operations and transient errors.

**The live scenario (functional requirement)**
*FR: "Calls to the embedding API fail ~2% with transient 503s; the provider allows at most 20 concurrent requests from us."*

**What the interviewer is really checking**
That you pick the right primitive and know retries can make outages worse.

**How I answer it**
1. Transient 503/timeouts: retry 3 times with exponential backoff and jitter. With Framework 7: `@Retryable(maxRetries = 3, delay = 200, multiplier = 2, jitter = 100)` on the client method.
2. Concurrency cap of 20: `@ConcurrencyLimit(20)` on the same method, so virtual-thread floods can't exceed the vendor limit.
3. If the provider is truly down, retries just multiply load: a **circuit breaker** (Resilience4j) opens and fails fast to a fallback (queue the job, or a smaller self-hosted model).
4. Retry only on retryable errors (503, 429 honouring `Retry-After`, connect timeouts); never on 400 or auth errors.
5. Budget: total retry time must fit the caller's timeout.

**Trade-offs and what can go wrong**
- Retry storms: every layer retrying 3× gives 27× load. Retry at one layer.
- Non-idempotent POSTs retried can duplicate work; use idempotency keys.
- Annotations rely on proxies; self-invocation bypasses them.

**How I'd monitor it**
Retry count and success-after-retry rate, breaker state, concurrency-limit rejections, provider error rate.

**Follow-ups to expect**
- *Why jitter?* -> To stop synchronised retry waves from many clients.
- *Bulkhead?* -> Isolates resources per dependency so one slow vendor can't consume all threads.
- *Spring Retry project?* -> Its core ideas moved into Framework 7; existing apps can keep using it.

**60-second answer**
"For transient 503s I retry three times with exponential backoff and jitter; on Spring Framework 7 that's the built-in `@Retryable`, and `@ConcurrencyLimit(20)` enforces the vendor's concurrency cap. Retries only help blips. If the provider is down, I need a Resilience4j circuit breaker to fail fast to a fallback, like queueing the job. I retry only idempotent calls and retryable status codes, at one layer only, and the total retry time stays inside the caller's timeout."

### Q14 [mid] Why prefer constructor injection, and how do you resolve circular dependencies?
tags: dependency-injection, constructor-injection, circular-dependency, ioc, design, profile-java-genai

**Start here: the concepts**
- **IoC / DI:** the container creates objects and supplies their dependencies.
- **Constructor injection:** dependencies as constructor parameters; fields can be `final`.
- Since Boot 2.6, **circular references are prohibited by default** (`spring.main.allow-circular-references=false`).

**The live scenario (functional requirement)**
*FR: "`ChatService` must use `RetrievalService`, and retrieval must log feedback through `ChatService`."* After an upgrade the app failed to start: "The dependencies of some of the beans form a cycle".

**What the interviewer is really checking**
That you treat a cycle as a design smell, not a config switch.

**How I answer it**
1. Constructor injection: required dependencies explicit, immutable, easy to unit test with `new`, no reflection.
2. The cycle means responsibilities are tangled. Retrieval doesn't need the whole chat service, only "record feedback".
3. **Extract** a `FeedbackRecorder` used by both, or
4. **Invert with events:** retrieval publishes `RetrievalFeedbackEvent`; a listener handles it (`ApplicationEventPublisher`). No compile-time dependency.
5. Only as a last resort: `@Lazy` on one parameter (it injects a proxy). Re-enabling circular references globally just hides the design problem.

**Trade-offs and what can go wrong**
- Field injection hides dependencies and lets classes grow to 15 collaborators unnoticed; constructor injection makes that pain visible.
- Events add indirection; document them.

**How I'd monitor it**
ArchUnit tests that forbid package cycles in CI.

**Follow-ups to expect**
- *Do you need `@Autowired` on a single constructor?* -> No, since Spring 4.3.
- *Setter injection?* -> For optional dependencies only.
- *How does `@Lazy` break the cycle?* -> It injects a proxy that resolves the real bean on first use.

**60-second answer**
"Constructor injection makes dependencies explicit and final and lets me unit test with plain `new`. A circular dependency is a design smell, and Boot has refused them by default since 2.6. Here retrieval only needed to record feedback, so I extracted a small FeedbackRecorder, or published an event that a listener handles. `@Lazy` works as a last resort, but turning circular references back on globally just hides tangled responsibilities."

### Q15 [architect] How would you structure a large Spring Boot application: layers, hexagonal or modular monolith?
tags: hexagonal-architecture, ports-and-adapters, spring-modulith, modular-monolith, package-structure, design, profile-java-genai

**Start here: the concepts**
- **Layered:** controller -> service -> repository. Simple, but domain logic leaks into services and entities.
- **Hexagonal (ports and adapters):** the domain core defines **ports** (interfaces); **adapters** implement them (REST, JPA, Kafka, LLM provider).
- **Modular monolith:** one deployable split into well-bounded modules; **Spring Modulith** verifies module boundaries and supports module events.

**The live scenario (functional requirement)**
*FR: "Build a claims-processing app with intake, AI document extraction, fraud scoring and payouts. The LLM provider may change, and some modules may become microservices later."*

**What the interviewer is really checking**
Architectural judgement: isolating volatile dependencies (the LLM!) and keeping options open.

**How I answer it**
1. **Package by feature/module**, not by layer: `intake`, `extraction`, `fraud`, `payout`, each with its own internal layers.
2. **Hexagonal inside each module:** the domain defines `DocumentExtractor` (a port). Adapters: `SpringAiDocumentExtractor`, later perhaps a self-hosted model. Switching providers touches one adapter.
3. Modules communicate through **public APIs or domain events** (`ClaimSubmitted`), never by reaching into each other's repositories.
4. **Spring Modulith** `ApplicationModules.of(App.class).verify()` in a test fails the build on boundary violations; its event publication registry gives outbox-like reliability.
5. Start as a **modular monolith**; extract a module into a service when it has a real reason (different scaling, team ownership, release cadence). Event-based boundaries make that extraction cheap.

**Trade-offs and what can go wrong**
- Hexagonal for a CRUD app is over-engineering; use it where the domain or external dependencies are volatile.
- Shared database tables across modules quietly recreate the big ball of mud.
- Premature microservices bring distributed transactions and ops cost.

**How I'd monitor it**
Architecture tests in CI, module-level metrics, and dependency graphs reviewed each quarter.

**Follow-ups to expect**
- *Where do DTOs and mapping go?* -> In adapters; the domain doesn't know about JSON or JPA.
- *DDD terms?* -> Bounded contexts map to modules; aggregates enforce invariants.
- *Why isolate the LLM behind a port?* -> Providers, models and prices change monthly; the domain shouldn't.

**60-second answer**
"I package by feature (intake, extraction, fraud, payout) and use hexagonal design inside modules where dependencies are volatile. The LLM is the clearest case: the domain owns a DocumentExtractor port and the Spring AI adapter implements it, so changing provider is one class. Modules talk through APIs or events, never each other's tables, and Spring Modulith verifies that in a test. I start as a modular monolith and extract a module only when scaling or ownership justifies it, and event boundaries make that cheap."
