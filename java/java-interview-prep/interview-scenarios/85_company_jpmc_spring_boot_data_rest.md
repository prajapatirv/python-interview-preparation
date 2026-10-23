---
id: company-jpmc-spring-boot-data-rest
title: JPMorgan Chase pack (3/5): Spring Boot, JPA, transactions and REST, mid to senior
stack: java
skill: spring-boot
---
Part of the **JPMorgan Chase Java mid/senior pack** (hub: `../company-chase-travel/README.md`). JPMC Java rounds
regularly cover **Spring, Spring Boot, Hibernate, ACID transactions, REST API design and dependency injection**, and
Chase Travel postings list **Java and Spring Boot**. Q1 is the "filter students by name and org" question, written up in full.

Each answer has a **120-second point-by-point version** (*How I answer it*) and a **60-second answer**.

Levels: **mid** (3-6 yrs) · **senior** (6-10) · **architect** (10+, "expert").

### Q1 [mid] Design a REST API to filter students by name and organisation. What structure do you follow in Spring Boot?
tags: rest-api, filtering, pagination, jpa-specification, layered-architecture, dto, controller-service-repository, jpmc

**Start here: the concepts**
- **Layered structure:** Controller (HTTP only) -> Service (business logic and transactions) -> Repository (database). Dependencies point one way.
- **Query parameters** are for filtering, sorting and paging (`?name=ravi&org=acme`). **Path variables** identify one resource (`/students/42`).
- A **JPA Specification** is a small piece of a `WHERE` clause that you can combine at runtime, which is ideal for *optional* filters.

**The live scenario (functional requirement)**
*FR: "The admin screen lists students. Users can filter by name (partial, case-insensitive), by organisation, both, or neither, with paging and sorting."* The first version had `findByName`, `findByOrg`, `findByNameAndOrg` and `findAll`. Four methods for two filters; adding "status" would make it eight.

**What the interviewer is really checking**
Clean REST conventions, a proper layered structure, a filtering approach that scales to more filters, and the production details (paging limits, indexes, N+1).

**How I answer it** (120-second answer, point by point)
1. **Endpoint:** `GET /api/v1/students?name=ravi&org=ACME&page=0&size=20&sort=name,asc`. Plural noun, no verbs, versioned. Empty results are **200 with an empty list**, not 404.
2. **Package by feature:** a `student` package with `StudentController`, `StudentService`, `StudentRepository`, `StudentSpecs`, the `Student` entity, a `StudentFilter` request record and a `StudentResponse` record. Shared items (`GlobalExceptionHandler`, `PageResponse`) live in `common`.
3. **Controller is thin:** binds the query params into `StudentFilter(String name, String org)` with `@Valid`, takes a `Pageable` with `@PageableDefault(size = 20, sort = "name")`, and calls the service. No business logic, no repository access.
4. **Service builds the query from Specifications:** `nameContains(name)` (lower-case `LIKE`) and `orgEquals(org)`. Each returns `null` when its filter is empty, and Spring skips null parts. `where(nameContains).and(orgEquals)` handles every combination with **one method**. Mark it `@Transactional(readOnly = true)`.
5. **Repository:** `extends JpaRepository<Student, Long>, JpaSpecificationExecutor<Student>`.
6. **Return DTOs, never entities:** map with MapStruct or a small mapper. Wrap the page in my own `PageResponse` (content, page, size, totalElements), because Spring's `Page` JSON is not a stable contract.
7. **Production details:**
   - Cap the page size (`spring.data.web.pageable.max-page-size=100`) and whitelist sortable fields.
   - Index `org_id`. `LIKE '%ravi%'` cannot use a normal index: use prefix search, a PostgreSQL trigram index, or a search engine for large tables.
   - Use `@EntityGraph` for the organisation, to avoid N+1 queries.
8. **Alternatives I compare:** derived methods (fine for one fixed filter), `@Query` with `(:name IS NULL OR ...)` (quick but planner-unfriendly), Querydsl (type-safe, extra build step), Elasticsearch/OpenSearch for fuzzy full-text search.

**Trade-offs and what can go wrong**
- Returning entities leaks internal fields and triggers lazy-loading errors during JSON serialisation.
- Unbounded `findAll` on a big table is an outage waiting to happen.
- `count` queries for total pages are expensive on huge tables; use `Slice` (no total) or keyset pagination for infinite scroll.

**Follow-ups to expect**
- *Org in the path or the query?* -> `/orgs/{orgId}/students` when students really belong to the org (and access is scoped by org); `?org=` when it is just one filter among several.
- *When is `POST /students/search` acceptable?* -> When the filter is too complex for a URL. Call it out as a deliberate exception.
- *Offset vs keyset pagination?* -> Offset gets slow on deep pages; keyset (`WHERE id > :lastId`) stays fast.

**60-second answer**
"I'd expose `GET /api/v1/students` with optional name, org, page, size and sort query params. The structure is controller to service to repository, packaged by feature. The controller only binds the params into a filter record and a Pageable. The service composes JPA Specifications, one per filter, each returning null when its filter is empty, so one method handles any combination instead of a method per combination. The repository extends JpaSpecificationExecutor. I return DTOs wrapped in my own page response. For production I cap the page size, whitelist sort fields, index org, avoid leading-wildcard LIKE on big tables, and use an entity graph to prevent N+1."

### Q2 [mid] How does Spring Boot auto-configuration work?
tags: spring-boot, auto-configuration, conditionalonclass, conditionalonmissingbean, starters, jpmc

**Start here: the concepts**
- **Auto-configuration** means Spring Boot creates beans for you based on what is on the classpath and in your properties.
- **Starters** (`spring-boot-starter-web`) are dependency bundles that bring the libraries in.
- **Conditions** (`@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty`) decide whether each auto-configured bean is created.

**The live scenario (functional requirement)**
*FR: "Every team's service must get the same audit logging, security headers and metrics tags without copying code."* We built an internal starter with its own auto-configuration, so teams only add a dependency.

**What the interviewer is really checking**
That Boot is not magic to you: you can explain the mechanism, debug it, and override it.

**How I answer it** (120-second answer, point by point)
1. `@SpringBootApplication` = `@Configuration` + `@ComponentScan` + `@EnableAutoConfiguration`.
2. **`@EnableAutoConfiguration`** loads the class names listed in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` inside every jar (this replaced `spring.factories` in Boot 3).
3. **Each auto-configuration class is guarded by conditions.** For example `DataSourceAutoConfiguration` runs only if a JDBC driver class is present, and creates a `DataSource` only `@ConditionalOnMissingBean`. So **your bean always wins**.
4. **Properties drive it:** `spring.datasource.url` binds into a `@ConfigurationProperties` class that the auto-config uses.
5. **Debugging:** start with `--debug` to print the **condition evaluation report** (what matched and why), or look at the `/actuator/conditions` endpoint.
6. **Overriding or turning off:** define your own bean, set a property, or `@SpringBootApplication(exclude = ...)`.
7. **Custom starter:** an `@AutoConfiguration` class with conditions, listed in the imports file, plus `@ConfigurationProperties` for settings. Teams just add the dependency.

**Trade-offs and what can go wrong**
- Hidden behaviour: a transitive dependency on the classpath can switch on auto-config you didn't expect (for example, a second `DataSource`).
- Startup time grows with classpath size; trim unused starters.

**Follow-ups to expect**
- *What are conditional beans?* -> `@ConditionalOnProperty(name = "feature.x.enabled", havingValue = "true")`, `@ConditionalOnClass`, `@Profile`; Boot's own auto-config is built from them.
- *Order of auto-configurations?* -> `@AutoConfiguration(after = ..., before = ...)`.

**60-second answer**
"@SpringBootApplication turns on component scanning and auto-configuration. Auto-configuration reads a list of configuration classes from each jar's AutoConfiguration.imports file. Each class is guarded by conditions: on class, on property, and most importantly on missing bean, so if I define my own DataSource, Boot backs off. Properties bind into @ConfigurationProperties classes that drive it. When something is surprising, I run with --debug or look at the conditions actuator endpoint, which shows what matched and why. We used the same mechanism to build an internal starter, so every team got audit logging and metrics just by adding a dependency."

### Q3 [mid] Why constructor injection? Explain bean scopes and the bean lifecycle.
tags: dependency-injection, constructor-injection, bean-scope, singleton, prototype, lifecycle, postconstruct, jpmc

**Start here: the concepts**
- **Dependency injection:** objects receive what they need from the container instead of creating it.
- **Bean scope:** how many instances exist. `singleton` (default, one per container), `prototype` (new each time), and web scopes `request` and `session`.

**The live scenario (functional requirement)**
*FR: "Unit-test the pricing service without starting Spring."* Field injection (`@Autowired private RateClient client`) made this impossible without reflection. Switching to constructor injection made tests plain `new PricingService(fakeClient)`.

**What the interviewer is really checking**
Good DI practice, the singleton thread-safety consequence, and the lifecycle hooks.

**How I answer it** (120-second answer, point by point)
1. **Constructor injection is my default:**
   - Dependencies are `final`, so the object is complete and immutable after construction.
   - Required dependencies are obvious; too many constructor arguments signal the class does too much.
   - Easy to test without Spring. With one constructor, no `@Autowired` is needed.
   - Field injection hides dependencies and needs reflection; setter injection only for truly optional ones.
2. **Singleton scope** means one instance serves all threads, so **beans must be stateless** or use thread-safe state.
3. **Prototype inside a singleton:** injected once, so it's effectively a singleton. Use `ObjectProvider<T>` to get a fresh one each time.
4. **Multiple implementations:** `@Primary`, `@Qualifier`, or inject a `List<T>`/`Map<String, T>` for the Strategy pattern.
5. **Lifecycle:** instantiate -> inject dependencies -> `Aware` callbacks -> `BeanPostProcessor` before -> `@PostConstruct` -> `BeanPostProcessor` after (**this is where AOP proxies are created**) -> ready -> `@PreDestroy` on shutdown.
6. **Circular dependencies** are forbidden by default since Boot 2.6. That is a design smell: extract a third class, or use events.

**Trade-offs and what can go wrong**
- Doing heavy work (remote calls) in `@PostConstruct` slows startup and can fail the whole app; use `ApplicationReadyEvent` or lazy loading.
- `@Lazy` hides startup errors until the first request.

**Follow-ups to expect**
- *`@Component` vs `@Bean`?* -> `@Component` on your own classes (found by scanning); `@Bean` methods for third-party classes or conditional creation.
- *Why does calling a `@Bean` method twice in a `@Configuration` class return the same instance?* -> The configuration class is CGLIB-proxied, so the call is intercepted.

**60-second answer**
"I use constructor injection by default: dependencies are final, required ones are obvious, and I can unit test with a plain new, no Spring. Field injection hides dependencies. Beans are singletons by default, so they must be stateless, because one instance serves every request thread. If a singleton needs a fresh prototype each time, I use ObjectProvider. The lifecycle is: construct, inject, @PostConstruct, then BeanPostProcessors, which is where proxies for @Transactional and @Cacheable are created, and @PreDestroy at shutdown. Circular dependencies are blocked by default since Boot 2.6, and I fix the design rather than re-enable them."

### Q4 [senior] How does @Transactional work, and what are the common traps?
tags: transactional, propagation, isolation, self-invocation, proxy, rollback, jpmc

**Start here: the concepts**
- A **transaction** groups database changes so they all succeed or all fail (ACID).
- `@Transactional` works through a **proxy**: Spring wraps your bean, starts a transaction before the method and commits or rolls back after.
- **Propagation** decides what happens when a transactional method calls another one (join, new, none).

**The live scenario (functional requirement)**
*FR: "Book a payment and always write an audit record, even when the payment fails."* The audit method had `@Transactional(propagation = REQUIRES_NEW)` but was called from the same class, so the annotation was ignored. When the payment rolled back, the audit row disappeared with it.

**What the interviewer is really checking**
The proxy mechanism and the traps that come from it, plus rollback rules and the right propagation choice.

**How I answer it** (120-second answer, point by point)
1. **Proxy mechanism:** callers get the proxy; the proxy opens the transaction, binds the connection to the thread, calls your method, then commits or rolls back.
2. **Trap 1: self-invocation.** `this.audit()` inside the same class bypasses the proxy, so its annotation is ignored. Fix: move it to another bean.
3. **Trap 2: rollback rules.** By default rollback happens only on **unchecked** exceptions and `Error`. A checked exception **commits**. Use `rollbackFor = Exception.class` where needed.
4. **Trap 3: catching the exception inside** the method means the proxy sees success and commits. Or with `REQUIRED`, an inner failure marks the transaction rollback-only and the outer commit throws `UnexpectedRollbackException`.
5. **Trap 4: visibility.** Only public methods are proxied with the default setup (Spring 6 also allows protected and package-private with class-based proxies). Private methods never are.
6. **Propagation I use:**
   - `REQUIRED` (default): join or start.
   - `REQUIRES_NEW`: suspend the outer one and run independently. Good for audit or outbox records that must survive. It uses a **second connection**, so watch pool size.
   - `MANDATORY`: must be called inside an existing transaction (guards repository-style code).
7. **Isolation:** the database default (READ COMMITTED in PostgreSQL) unless there is a reason; `readOnly = true` for queries.
8. **Keep transactions short:** never call a remote API inside one. It holds a DB connection and locks the whole time.

**Trade-offs and what can go wrong**
- Putting `@Transactional` on the controller widens the transaction to include serialisation.
- `REQUIRES_NEW` under load can exhaust the connection pool (each request holds two connections).

**Follow-ups to expect**
- *What is `@TransactionalEventListener`?* -> It runs a listener after commit (`AFTER_COMMIT`), for example to publish an event only if the data was saved.
- *Does `@Transactional` work across two databases or Kafka?* -> Not atomically; use the outbox pattern, not XA, in most designs.

**60-second answer**
"@Transactional works through a proxy that opens a transaction, runs the method, then commits or rolls back. Most bugs come from that. A call from the same class bypasses the proxy, so its annotation is ignored. Checked exceptions commit by default unless you add rollbackFor. Catching an exception inside the method makes the proxy commit. For propagation, I use REQUIRED by default, and REQUIRES_NEW for an audit or outbox record that must survive a rollback, knowing it takes a second connection. I keep transactions short, never calling remote APIs inside them, and use readOnly for queries."

### Q5 [senior] What is the N+1 problem in JPA/Hibernate, and how do you fix it?
tags: jpa, hibernate, n-plus-one, fetch-join, entitygraph, lazy-loading, projections, jpmc

**Start here: the concepts**
- **N+1:** one query loads N parents, then Hibernate runs one more query **per parent** to load a lazy relation. 1 + N queries.
- **Lazy loading** means related data is loaded only when you touch it; that is when the extra queries happen.

**The live scenario (functional requirement)**
*FR: "Show 50 accounts per page with their owner's name."* The page took 2 seconds. SQL logging showed 1 query for accounts plus 50 queries for owners.

**What the interviewer is really checking**
Diagnosis, the right fix per situation, and awareness of pagination and memory traps.

**How I answer it** (120-second answer, point by point)
1. **Detect it:** turn on SQL logging in tests (`spring.jpa.show-sql` or a datasource proxy), Hibernate statistics, or APM traces showing many identical queries. A test can assert the query count.
2. **Fix 1: fetch join** for one specific query: `select a from Account a join fetch a.owner where ...`.
3. **Fix 2: `@EntityGraph(attributePaths = "owner")`** on the repository method. This works with derived queries and Specifications.
4. **Fix 3: batch fetching:** `hibernate.default_batch_fetch_size=50` loads lazy relations in groups with `IN (...)`. That gives 2 queries instead of 51.
5. **Fix 4: DTO projections** for read screens: select only the columns needed into a record. This is often the best option for lists.
6. **Pagination trap:** a fetch join on a **collection** with paging makes Hibernate page **in memory** (warning HHH90003004). Page the ids first, then fetch, or use batch fetching.
7. **Defaults:** keep everything `LAZY` (make `@ManyToOne` lazy explicitly, since it is eager by default), and fetch per use case. Turn off `spring.jpa.open-in-view` so lazy loads cannot hide in the view layer.

**Trade-offs and what can go wrong**
- Fetching several collections at once creates a Cartesian product (or `MultipleBagFetchException`).
- `EAGER` everywhere "fixes" N+1 on one screen and loads half the database on another.

**Follow-ups to expect**
- *What is `LazyInitializationException`?* -> Touching a lazy relation after the session is closed; fix it by fetching what you need inside the transaction, not by enabling open-in-view.
- *First- vs second-level cache?* -> First level is per persistence context (always on); second level is shared across sessions (opt-in, for reference data).

**60-second answer**
"N+1 is one query for the list and then one query per row for a lazy relation: 50 accounts became 51 queries and 2 seconds. I detect it with SQL logging or query-count assertions in tests. For a specific query I use a fetch join or an @EntityGraph. As a general safety net, a batch fetch size, which turns the 50 queries into one IN query. For read-only list screens, DTO projections are usually best. I keep relations lazy, including @ManyToOne, turn off open-in-view, and never fetch-join a collection with pagination, because Hibernate then pages in memory."

### Q6 [senior] Explain ACID, isolation levels, and optimistic vs pessimistic locking.
tags: acid, isolation-levels, dirty-read, phantom-read, optimistic-locking, pessimistic-locking, version, jpmc

**Start here: the concepts**
- **ACID:** **A**tomic (all or nothing), **C**onsistent (rules and constraints hold), **I**solated (concurrent transactions don't interfere badly), **D**urable (committed data survives a crash).
- **Isolation levels** trade safety for concurrency: READ UNCOMMITTED, READ COMMITTED, REPEATABLE READ, SERIALIZABLE.
- **Optimistic locking:** don't lock, detect a conflict at commit time using a version. **Pessimistic locking:** lock the row before changing it.

**The live scenario (functional requirement)**
*FR: "Two operators may edit the same client's credit limit at the same time; neither change may be silently lost."* Without protection, the second save overwrote the first: a **lost update**.

**What the interviewer is really checking**
JPMC candidates report direct ACID questions. They want the anomalies, the defaults, and practical locking choices.

**How I answer it** (120-second answer, point by point)
1. **ACID in one line each,** with a bank example: the transfer debits and credits together (A); the balance never violates a check constraint (C); two transfers don't see each other's half-done work (I); once committed, a crash doesn't undo it (D).
2. **The anomalies:**
   - **Dirty read:** reading uncommitted data.
   - **Non-repeatable read:** the same row read twice gives different values.
   - **Phantom read:** the same query returns new rows.
   - **Lost update:** two read-modify-writes overwrite each other.
3. **Levels:** READ COMMITTED (default in PostgreSQL and Oracle) prevents dirty reads; REPEATABLE READ (MySQL InnoDB default) also prevents non-repeatable reads; SERIALIZABLE behaves as if transactions ran one by one, and may abort them with a retryable error.
4. **Optimistic locking:** a `@Version` column. The update includes `WHERE version = ?`; if 0 rows change, Spring throws `ObjectOptimisticLockingFailureException`. I return **409 Conflict** (or retry for system jobs). Best when conflicts are rare, as in user edits. For REST, expose the version as an **ETag** and require `If-Match`.
5. **Pessimistic locking:** `@Lock(PESSIMISTIC_WRITE)` gives `SELECT ... FOR UPDATE`. Best for hot rows with frequent conflicts, such as inventory or a balance. Always set a lock timeout.
6. **Simplest of all:** an atomic SQL update, `balance = balance - :x WHERE balance >= :x`.

**Trade-offs and what can go wrong**
- SERIALIZABLE everywhere means many aborted transactions; use it only where invariants need it, with retries.
- Pessimistic locks held across user think time or remote calls cause pile-ups and deadlocks.

**Follow-ups to expect**
- *What is MVCC?* -> Multi-version concurrency control: readers see a snapshot, so readers don't block writers (PostgreSQL, Oracle).
- *Distributed transactions across services?* -> Avoid two-phase commit; use a saga with the outbox pattern and compensations.

**60-second answer**
"ACID means all-or-nothing, rules always hold, concurrent transactions don't see each other's partial work, and committed data survives crashes. Isolation levels trade safety for concurrency. PostgreSQL defaults to READ COMMITTED, which prevents dirty reads but still allows lost updates. For two operators editing the same credit limit, I use optimistic locking: a version column, a conflict detected at save, returned as 409, and exposed as an ETag in the API. For hot rows like a balance, pessimistic SELECT FOR UPDATE with a timeout, or a single conditional UPDATE. SERIALIZABLE only where invariants demand it, with retries."

### Q7 [mid] How do you validate input and return consistent errors from a REST API?
tags: validation, bean-validation, controlleradvice, problem-details, rfc-9457, error-handling, jpmc

**Start here: the concepts**
- **Bean Validation** (`@NotBlank`, `@Size`, `@Positive`) declares rules on request DTOs; `@Valid` triggers them.
- **`@RestControllerAdvice`** is one class that handles exceptions for all controllers.
- **Problem Details (RFC 9457)** is a standard JSON error format (`type`, `title`, `status`, `detail`, `instance`); Spring's `ProblemDetail` class supports it.

**The live scenario (functional requirement)**
*FR: "Mobile and partner clients must get the same error shape everywhere, with field-level messages, and no stack traces."* Each controller returned its own format, and partners had to write special parsing per endpoint.

**What the interviewer is really checking**
A single, consistent error contract, correct status codes, and security awareness.

**How I answer it** (120-second answer, point by point)
1. **Validate at the edge:** request records with constraints, `@Valid @RequestBody`. Cross-field rules use a custom constraint or a check in the service.
2. **Validation failure -> 400** with a list of field errors (`field`, `message`), built from `MethodArgumentNotValidException`.
3. **One `@RestControllerAdvice`** maps exceptions to `ProblemDetail`:
   - Business rule broken -> 422 (or 409 for a state conflict).
   - Not found -> 404. Not allowed -> 403. Downstream down -> 503 with `Retry-After`.
   - Anything unexpected -> 500 with a **generic** message plus a correlation id; the details go to logs only.
4. **Turn on** `spring.mvc.problemdetails.enabled=true` so Spring's own errors (wrong media type, missing parameter) use the same format.
5. **Error codes:** add a stable machine-readable `code` property (for example `INSUFFICIENT_FUNDS`) so clients don't parse message text.
6. **Document it** in OpenAPI so partners generate clients from it.

**Trade-offs and what can go wrong**
- Echoing invalid input back in messages can leak data or enable injection into logs; keep messages generic.
- 400 vs 422 debates: pick one convention, document it and be consistent.

**Follow-ups to expect**
- *Validate path and query params?* -> Yes, add constraints on the parameters; since Spring 6.1 method validation for controller params is built in.
- *Where do you validate business rules?* -> In the service/domain; annotations are for shape and format.

**60-second answer**
"I validate request DTOs at the edge with Bean Validation and @Valid, and put business rules in the service. All errors go through one @RestControllerAdvice that returns RFC 9457 Problem Details: 400 with field-level errors for validation, 422 or 409 for business rules, 404, 403, 503 with Retry-After for downstream outages, and a generic 500 with a correlation id for anything unexpected. The details go to the logs, never to the client. I enable Spring's problem-details setting so framework errors look the same, and add a stable error code so clients never parse messages."

### Q8 [senior] How do you secure a Spring Boot REST API?
tags: spring-security, oauth2, jwt, resource-server, method-security, cors, csrf, jpmc

**Start here: the concepts**
- **Authentication:** who are you? **Authorization:** what are you allowed to do?
- **OAuth2 / OpenID Connect:** a central identity provider issues **tokens**; your API (a *resource server*) only validates them.
- **JWT:** a signed token carrying claims (user, roles, expiry) that the API checks using the issuer's public keys.

**The live scenario (functional requirement)**
*FR: "Clients may only see their own accounts; operations staff may see all accounts but not change them; every call must be auditable."*

**What the interviewer is really checking**
Modern Spring Security configuration, fine-grained authorization, and the OWASP basics. In a bank this is never optional.

**How I answer it** (120-second answer, point by point)
1. **Resource server:** `spring-boot-starter-oauth2-resource-server` with `issuer-uri`. Spring downloads the public keys (JWKS) and validates the signature, expiry, issuer and audience on every request.
2. **A `SecurityFilterChain` bean** (no more `WebSecurityConfigurerAdapter`): stateless sessions, all endpoints authenticated by default, explicit `permitAll` only for health checks.
3. **Map claims to authorities:** scopes or roles from the token become `ROLE_OPS`, `SCOPE_accounts.read`.
4. **Method security:** `@EnableMethodSecurity` and `@PreAuthorize("hasRole('OPS') or @accountAccess.isOwner(authentication, #accountId)")`. **Object-level checks** are the most common bank bug (IDOR: changing the id in the URL shows someone else's account).
5. **Service-to-service:** client-credentials tokens or mTLS inside the cluster.
6. **CSRF:** disable it only for stateless token APIs; keep it for cookie-based sessions. **CORS:** an explicit allow-list of origins.
7. **Other basics:** validate all input, use parameterised queries, put secrets in a vault (never in git), keep sensitive data out of logs, add rate limiting, and audit-log who did what with a correlation id.

**Trade-offs and what can go wrong**
- JWTs can't easily be revoked; keep them short-lived and use refresh tokens.
- Putting too much data in the token makes it large and stale.

**Follow-ups to expect**
- *Where do you put authorization logic?* -> Coarse rules in the filter chain, ownership rules in method security or the service.
- *How do you test it?* -> `@WithMockUser` or `jwt()` request post-processors in MockMvc tests.

**60-second answer**
"I make the API an OAuth2 resource server. Spring validates the JWT's signature, expiry, issuer and audience against the identity provider's keys. A SecurityFilterChain bean makes it stateless and authenticated by default. Token scopes become authorities, and I use method security with @PreAuthorize, including object-level checks, so a client can only read their own accounts; that ID-swapping bug is the classic one in banking. Services call each other with client-credentials tokens or mTLS. CSRF is off only because it's a stateless token API, CORS is an explicit list, secrets live in a vault, and every action is audit-logged."

### Q9 [senior] How do you make a POST endpoint idempotent, for example a payment?
tags: idempotency, idempotency-key, retries, duplicate-requests, unique-constraint, payments, jpmc

**Start here: the concepts**
- **Idempotent** means doing it twice has the same effect as doing it once. `GET`, `PUT` and `DELETE` are idempotent by definition; `POST` is not.
- Clients and gateways **retry** on timeouts, so without idempotency a slow payment can be charged twice.

**The live scenario (functional requirement)**
*FR: "A mobile client submits a payment. If the network drops before the response, the app retries. The customer must be charged once."*

**What the interviewer is really checking**
A concrete mechanism that survives concurrency and multiple instances, not just "check if it exists first".

**How I answer it** (120-second answer, point by point)
1. **The client sends an `Idempotency-Key` header** (a UUID per logical operation).
2. **I store the key in a table with a unique constraint,** along with a hash of the request body, the status (`IN_PROGRESS`, `DONE`) and the saved response.
3. **First request:** the insert succeeds; process the payment; save the response in the **same transaction** as the business change.
4. **Repeat with the same key:**
   - `DONE` -> return the stored response (same status and body).
   - `IN_PROGRESS` -> return 409 or 202, so the client retries later.
   - Same key with a **different body** -> 422, because it's a client bug.
5. **Concurrency is handled by the database:** two pods inserting the same key at once both hit the unique constraint, and only one wins. A "check then insert" in code is a race.
6. **Expiry:** keep keys for 24-72 hours, then clean them up.
7. **Downstream calls:** pass the same key to the payment processor, and make Kafka consumers idempotent too (dedupe by event id).

**Trade-offs and what can go wrong**
- Storing keys in Redis only is fast but can be lost; for money use the database.
- If processing crashes in the middle, `IN_PROGRESS` must time out and be recoverable.

**Follow-ups to expect**
- *Why not just make it a PUT?* -> If the client can choose the resource id (`PUT /payments/{clientGeneratedId}`), that also works; it's the same idea.
- *What does the IETF draft say?* -> There is an IETF draft standardising the `Idempotency-Key` header, following the pattern popularised by Stripe.

**60-second answer**
"POST isn't idempotent by default, and clients retry on timeouts, so a payment can be charged twice. I require an Idempotency-Key header and store it with a unique constraint, a hash of the request and the stored response, in the same transaction as the payment. A retry with the same key returns the stored response. If it's still in progress I return 409. The same key with a different body is a 422. The unique constraint is what makes it safe across pods: two concurrent inserts can't both win, which a check-then-insert in code can't guarantee. I pass the key downstream too, and make consumers idempotent."

### Q10 [senior] How do you call a slow or unreliable downstream service safely from Spring Boot?
tags: restclient, webclient, timeouts, retry, circuit-breaker, resilience4j, bulkhead, jpmc

**Start here: the concepts**
- **Timeout:** stop waiting after a set time.
- **Retry:** try again for temporary failures, with **backoff and jitter** (waiting longer each time, randomly).
- **Circuit breaker:** after many failures, stop calling for a while and fail fast, so you don't pile up.
- **Bulkhead:** limit how many concurrent calls go to one dependency, so it can't use all your threads.

**The live scenario (functional requirement)**
*FR: "The booking API calls a supplier that is sometimes slow. A supplier outage must not take down booking for other suppliers."* Without timeouts, every request thread waited 60+ seconds and the whole service became unresponsive.

**What the interviewer is really checking**
Layered resilience with the right order and sensible numbers, plus a user-facing fallback.

**How I answer it** (120-second answer, point by point)
1. **Client:** `RestClient` (Spring 6.1+) or HTTP service interfaces (`@HttpExchange`) for blocking code, `WebClient` for reactive code. `RestTemplate` is in maintenance mode.
2. **Timeouts on every call:** connect timeout (about 1 s) and read timeout (based on the downstream's p99, for example 2 s). The total must fit inside my own SLA.
3. **Retry only what is safe:** idempotent calls and transient errors (connection reset, 503, 429 with `Retry-After`). 2-3 attempts with exponential backoff and jitter. Never retry 400s.
4. **Circuit breaker (Resilience4j):** opens at, say, 50% failures over a sliding window, then fails fast, then tries a few test calls (half-open).
5. **Bulkhead per supplier:** a semaphore or thread-pool limit, so one bad supplier can't take every thread.
6. **Order:** Retry wraps CircuitBreaker wraps TimeLimiter wraps the call, so retries stop when the circuit is open.
7. **Fallback that makes sense:** cached data, a partial response ("supplier unavailable"), or a clear 503. Never a fake success.
8. **Observe it:** metrics for circuit state, retries and timeouts, plus alerts when a circuit stays open.

**Trade-offs and what can go wrong**
- Retries multiply load: 3 retries at 3 layers is 27 calls (a retry storm). Retry at one layer only.
- A circuit breaker threshold that is too sensitive flaps open on normal noise.

**Follow-ups to expect**
- *Where do these settings live?* -> `resilience4j.*` properties per instance, so they can differ per supplier.
- *How do you test it?* -> WireMock with delays and faults in integration tests; chaos testing in lower environments.

**60-second answer**
"Every downstream call gets a connect and a read timeout that fit within my own SLA. I retry only idempotent calls on transient errors, two or three times with exponential backoff and jitter, at one layer only to avoid retry storms. A Resilience4j circuit breaker fails fast when the supplier is clearly down, and a bulkhead per supplier stops one bad supplier from taking every thread. The order is retry around the circuit breaker around the timeout. The fallback is honest: cached data, a partial response or a 503, never a fake success. And circuit state and timeouts are on dashboards with alerts."

### Q11 [mid] How do you manage configuration, profiles and secrets across environments?
tags: configuration, profiles, configurationproperties, secrets, vault, externalized-config, jpmc

**Start here: the concepts**
- **Externalised configuration:** the same jar runs everywhere; settings come from properties files, environment variables or a config service.
- **Profiles** (`dev`, `uat`, `prod`) switch groups of settings.
- **Secrets** (passwords, keys) must never be in git or in the image.

**The live scenario (functional requirement)**
*FR: "One build artifact is promoted from dev to UAT to production; database credentials rotate every 30 days with no redeploy."*

**What the interviewer is really checking**
Build-once-deploy-many discipline, type-safe config, and secure secret handling.

**How I answer it** (120-second answer, point by point)
1. **Build once:** one image for every environment; only configuration differs.
2. **Typed config:** `@ConfigurationProperties(prefix = "payments")` on a record, with `@Validated` so a missing value fails at **startup**, not at 2 a.m.
3. **Precedence** (simplified): command line > environment variables > profile-specific files > `application.yml`. In Kubernetes, use env vars or mounted ConfigMaps.
4. **Profiles** only for real environment differences, not feature switches. Use feature flags for features.
5. **Secrets:** HashiCorp Vault, AWS Secrets Manager or Kubernetes secrets backed by a vault (External Secrets Operator), loaded with `spring.config.import`. For AWS databases, **IAM authentication** removes the static password entirely.
6. **Rotation:** short-lived credentials; a refresh mechanism, or a rolling restart triggered by the rotation.
7. **Audit:** `/actuator/env` and `/actuator/configprops` mask secrets by default; don't expose them publicly.

**Trade-offs and what can go wrong**
- Too many profiles makes it unclear what production actually runs; keep it to environment differences.
- Runtime refresh (`@RefreshScope`) is powerful but makes behaviour change without a deploy; use it carefully.

**Follow-ups to expect**
- *How do you avoid a bad config breaking production?* -> Validate at startup, roll out with canaries, and keep config in git with review.

**60-second answer**
"I build one artifact and promote it through every environment; only configuration changes. Config is bound into @ConfigurationProperties records with validation, so a missing value fails at startup. Environment differences come from env vars or ConfigMaps, and profiles only for real environment differences, not features. Secrets never go in git or the image: they come from Vault or AWS Secrets Manager via config import, or I use IAM database authentication so there's no password at all. Credentials are short-lived and rotate without a redeploy, and actuator endpoints that show config stay masked and internal."

### Q12 [senior] What is your testing strategy for a Spring Boot microservice?
tags: testing, junit5, mockito, webmvctest, datajpatest, testcontainers, contract-testing, jpmc

**Start here: the concepts**
- **Test pyramid:** many fast unit tests, fewer integration tests, very few end-to-end tests.
- **Slice tests** start only part of Spring: `@WebMvcTest` (the web layer), `@DataJpaTest` (repositories).
- **Testcontainers** run a real database or Kafka in Docker for tests.

**The live scenario (functional requirement)**
*FR: "We deploy several times a day; a broken contract with the mobile app or a bad SQL migration must be caught before production."*

**What the interviewer is really checking**
A balanced strategy that catches real bugs quickly, not just high coverage numbers.

**How I answer it** (120-second answer, point by point)
1. **Unit tests (JUnit 5 + Mockito/AssertJ):** business logic in services and domain objects, no Spring, milliseconds each.
2. **Web slice (`@WebMvcTest`):** status codes, validation, JSON shape, security rules. Mock the service with `@MockitoBean` (Spring Framework 6.2+; `@MockBean` is deprecated and removed in Boot 4).
3. **Repository tests (`@DataJpaTest` + Testcontainers PostgreSQL):** real SQL and real migrations. H2 hides dialect differences.
4. **Integration tests (`@SpringBootTest` + Testcontainers):** a few important flows end to end inside the service, including Kafka. `@ServiceConnection` wires containers with no manual properties.
5. **Downstream calls:** WireMock for success, slow and error responses.
6. **Contract tests:** Spring Cloud Contract or Pact, so a provider change that breaks a consumer fails the build.
7. **Non-functional:** a load test (Gatling or JMeter) on critical endpoints in the pipeline; security scans.
8. **Quality gates:** coverage as a signal (around 80% on business logic), plus mutation testing (PIT) on critical code.

**Trade-offs and what can go wrong**
- Too many `@SpringBootTest`s make the build slow; reuse the context and prefer slices.
- Mocking everything gives green tests that don't catch real integration bugs.

**Follow-ups to expect**
- *How do you test time-dependent code?* -> Inject a `Clock`.
- *How do you test concurrency?* -> Many threads with a `CountDownLatch` start gate, asserting invariants.

**60-second answer**
"Most tests are fast unit tests of business logic with JUnit 5 and Mockito, no Spring. @WebMvcTest checks status codes, validation, JSON and security, with @MockitoBean, since @MockBean is gone in Boot 4. Repository tests run against real PostgreSQL in Testcontainers with the real migrations, because H2 hides dialect bugs. A few @SpringBootTest flows cover Kafka and the database together, WireMock simulates slow and failing downstreams, and contract tests catch API breaks with consumers. Critical endpoints get a load test in the pipeline. Coverage is a signal, not the goal."
