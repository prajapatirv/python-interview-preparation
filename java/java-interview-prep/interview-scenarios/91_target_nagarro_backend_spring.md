---
id: target-nagarro-backend
title: Target company, Nagarro (2/3): backend, Spring Boot and microservices technical round
stack: java
skill: microservices
---
Part of the **target-company section** (hub: `../target-companies/README.md`, section "Nagarro").
Nagarro's backend technical rounds, as candidates report them, mix **fundamentals** (REST vs gRPC, indexing,
transactions, CAP), **Spring Boot** (auto-configuration, DI, validation, caching), **microservices patterns**
(gateway, discovery, load balancing, idempotency, eventual consistency with Kafka) and a short **Java 8 streams**
coding question. Several candidates describe a quick "do you know Kafka / Docker?" round as well, so keep a
crisp 60-second answer ready for each.

Every answer has a **120-second** point-by-point version (*How I answer it*) and a **60-second answer**.

### Q1 [mid] REST vs gRPC: how do they differ and when would you choose each?
tags: rest, grpc, protobuf, http2, streaming, api-design, inter-service, nagarro

**Start here: the concepts**
- **REST** = resources over HTTP (usually JSON), verbs like GET/POST, human-readable, works everywhere.
- **gRPC** = remote procedure calls defined in a `.proto` file, binary **Protocol Buffers** over **HTTP/2**, with generated client and server code.
- HTTP/2 allows many requests over one connection (multiplexing) and **streaming** in both directions.

**The live scenario (functional requirement)**
*FR: "The mobile app and partners need a public order API. Internally, the pricing service is called 20 times per
checkout by the order service and must answer in under 10 ms."*

**What the interviewer is really checking**
That you pick by consumer and constraint (public vs internal, latency, streaming, tooling), not by fashion.

**How I answer it** (120-second answer, point by point)
1. **Contract:** REST uses OpenAPI (optional, often drifts); gRPC's `.proto` is mandatory and generates typed stubs, so contract breaks show at compile time.
2. **Payload and speed:** protobuf is binary and typically several times smaller and faster to parse than JSON; HTTP/2 multiplexing avoids connection overhead. It matters for chatty internal calls.
3. **Streaming:** gRPC supports server, client and bidirectional streaming natively; REST needs SSE or WebSockets.
4. **Reach and tooling:** REST works from any browser, curl, API gateways and caches (GET + ETag). Browsers cannot call gRPC directly (need gRPC-Web or a proxy).
5. **Errors and evolution:** REST uses HTTP status codes and Problem Details; gRPC has its own status codes. Protobuf evolves safely if you never reuse field numbers.
6. **My choice in the scenario:** **REST** for the public order API (partners, mobile, caching, gateway policies); **gRPC** for order -> pricing inside the cluster (low latency, typed contract, high call volume).

**Trade-offs and what can go wrong**
- gRPC needs L7 load balancing that understands HTTP/2; with plain L4, one long-lived connection pins all calls to one pod.
- Binary payloads are harder to debug; you need grpcurl and good logging.
- Over-using gRPC for everything couples teams to shared proto repos and release coordination.

**Follow-ups to expect**
- *What about GraphQL?* -> Good when many clients need different shapes of the same data (BFF); adds query complexity and caching difficulty.
- *How do you version gRPC?* -> Add fields with new numbers, never change or reuse old ones; a new package (`v2`) for breaking changes.

**60-second answer**
"REST is resources over HTTP with JSON. It's readable, works from any browser or tool, and fits gateways and HTTP caching,
so it's my default for public and partner APIs. gRPC uses a proto contract that generates typed code, with binary protobuf
over HTTP/2, so it's smaller, faster and supports streaming in both directions. That suits high-volume internal calls,
like an order service calling pricing twenty times per checkout. The catches: browsers need gRPC-Web, you need HTTP/2-aware
load balancing or traffic sticks to one pod, and debugging binary payloads needs tooling. So: REST at the edge, gRPC
inside when latency and call volume justify it."

### Q2 [mid] How does a database index work, and how do you decide which indexes to create?
tags: database-indexing, b-tree, composite-index, covering-index, explain-plan, query-performance, sql, nagarro

**Start here: the concepts**
- An index is a separate sorted structure (usually a **B-tree**) that maps column values to row locations, like the index at the back of a book.
- It makes reads by that column fast (O(log n) instead of a full scan) but **every insert/update must also update the index**.
- A **composite index** covers several columns in order; a **covering index** contains every column a query needs, so the table is not touched.

**The live scenario (functional requirement)**
*FR: "Customers see their last 20 orders, newest first."* The query
`SELECT ... FROM orders WHERE customer_id = ? AND status <> 'DELETED' ORDER BY created_at DESC LIMIT 20` took 2 seconds
on 80 million rows.

**What the interviewer is really checking**
Whether you use the execution plan, understand column order in composite indexes, and know when an index hurts.

**How I answer it** (120-second answer, point by point)
1. **Measure first:** `EXPLAIN ANALYZE` showed a sequential scan plus a sort of all of the customer's rows.
2. **Composite index in the right order:** `(customer_id, created_at DESC)`. Equality column first, then the sort column, so the database reads the 20 newest entries directly and stops: no sort.
3. **Leftmost-prefix rule:** that index also serves `WHERE customer_id = ?` alone, but not `WHERE created_at > ?` alone.
4. **Selectivity:** index columns that filter strongly. An index on `status` with three values rarely helps (use a **partial index** like `WHERE status = 'PENDING'` instead).
5. **Covering:** `INCLUDE (total, status)` in PostgreSQL lets an index-only scan answer the list page.
6. **What kills index use:** functions on the column (`WHERE LOWER(email) = ?` needs a functional index), leading wildcards (`LIKE '%abc'`), implicit type casts, `OR` across different columns.
7. **Cost side:** each index slows writes and uses memory. I review unused indexes (`pg_stat_user_indexes`) and drop them.
8. **Result:** 2 s -> 3 ms. In production I create it with `CREATE INDEX CONCURRENTLY` so the table is not locked.

**Trade-offs and what can go wrong**
- Too many indexes on a write-heavy table (events, logs) slow inserts and bloat storage.
- Indexes are useless for low-selectivity columns and can even make the planner choose badly; keep statistics fresh (`ANALYZE`).
- Hash indexes only support equality; B-tree supports ranges and sorting.

**Follow-ups to expect**
- *Clustered vs non-clustered?* -> In MySQL InnoDB the primary key is clustered (rows stored in PK order); secondary indexes point to the PK. PostgreSQL tables are heaps; all indexes are secondary.
- *Why is my index not used?* -> Low selectivity, a function or cast on the column, wrong column order, or stale statistics.

**60-second answer**
"An index is a sorted B-tree that points to rows, so lookups are logarithmic instead of a full scan, but every write
also maintains it. I always start from EXPLAIN ANALYZE. For 'last 20 orders of a customer, newest first' I'd create a
composite index on customer id then created_at descending: equality column first, sort column second, so the database
reads 20 entries and stops without sorting. That took a real query from 2 seconds to 3 milliseconds. I index selective
columns, use partial or covering indexes where they fit, avoid functions on indexed columns, drop unused indexes on
write-heavy tables, and build them concurrently in production."

### Q3 [mid] Explain transactions: ACID, isolation levels, and how @Transactional works in Spring
tags: transactions, acid, isolation-levels, transactional, propagation, rollback, self-invocation, spring, nagarro

**Start here: the concepts**
- **ACID:** Atomic (all or nothing), Consistent (constraints hold), Isolated (concurrent transactions do not see each other's half-work), Durable (committed data survives a crash).
- **Isolation levels** trade correctness for concurrency: Read Committed (default in PostgreSQL/Oracle), Repeatable Read (default in MySQL), Serializable.
- Spring's `@Transactional` wraps a method in a **proxy** that begins, commits or rolls back the transaction.

**The live scenario (functional requirement)**
*FR: "Transfer points between two loyalty accounts."* Under load, two concurrent transfers from the same account both
read balance 100, both debited 80, and the account went to -60.

**What the interviewer is really checking**
That you know which anomaly happened (lost update), how to prevent it, and the Spring traps (self-invocation, checked
exceptions, private methods).

**How I answer it** (120-second answer, point by point)
1. **Anomalies:** dirty read, non-repeatable read, phantom read, and the one here, **lost update** (read-modify-write race).
2. **Fixes for the race:** an atomic conditional update `UPDATE account SET balance = balance - 80 WHERE id = ? AND balance >= 80` (best), or pessimistic `SELECT ... FOR UPDATE`, or optimistic locking with `@Version` and retry. Isolation level alone at Read Committed does not prevent it.
3. **Lock order:** when locking two accounts, always lock the lower id first to avoid deadlocks.
4. **Spring mechanics:** `@Transactional` works through a proxy, so it applies only to **public methods called from another bean**. A call from inside the same class (`this.transfer()`) bypasses the proxy: no transaction.
5. **Rollback rules:** by default rollback on `RuntimeException` and `Error`, **not on checked exceptions**; use `rollbackFor = Exception.class` if needed.
6. **Propagation:** `REQUIRED` (join or create, the default), `REQUIRES_NEW` (separate transaction, for example an audit log that must survive a rollback), `NESTED` (savepoint).
7. **Practical rules:** keep transactions short, no remote HTTP calls inside them, `readOnly = true` for queries (lets Hibernate skip dirty checking).

**Trade-offs and what can go wrong**
- Serializable prevents all anomalies but causes serialization failures that you must retry.
- Long transactions hold locks and connections and become the hidden cause of pool exhaustion.
- Catching an exception inside a transactional method and swallowing it can still mark the transaction rollback-only, causing `UnexpectedRollbackException` at commit.

**Follow-ups to expect**
- *Optimistic or pessimistic locking?* -> Optimistic when conflicts are rare (retry on `OptimisticLockException`); pessimistic for hot rows with frequent conflicts.
- *Does @Transactional work across microservices?* -> No; each service commits locally, and cross-service consistency needs a saga with an outbox.

**60-second answer**
"ACID means all-or-nothing, constraints hold, concurrent transactions are isolated, and commits are durable. Isolation
levels trade safety for concurrency; most databases default to read committed. A common real bug is a lost update: two
transfers both read balance 100 and both debit 80. Isolation level alone doesn't fix that. I use an atomic conditional
update, `balance >= amount`, or `FOR UPDATE`, or optimistic locking with a version column. In Spring, @Transactional works
through a proxy, so self-invocation and private methods get no transaction, and by default it rolls back only on runtime
exceptions. I keep transactions short and never make remote calls inside them."

### Q4 [senior] You are building a payment API and receive duplicate requests. How do you ensure idempotency?
tags: idempotency, idempotency-key, payment-api, duplicate-requests, unique-constraint, retries, redis, nagarro

**Start here: the concepts**
- **Idempotent** = doing the same request twice has the same effect as once.
- Duplicates come from double-clicks, mobile retries after a timeout, gateway retries, and message redelivery.
- The usual tool is an **Idempotency-Key** header: a client-generated unique id per business operation.

**The live scenario (functional requirement)**
*FR: "Charge the customer for an order."* A mobile client timed out after 5 seconds and retried. The first request had
actually succeeded, so the customer was charged twice.

**What the interviewer is really checking**
That you store the key and the outcome atomically, handle the in-progress case, and push idempotency down to the
payment provider too.

**How I answer it** (120-second answer, point by point)
1. **Client contract:** every `POST /payments` carries `Idempotency-Key: <uuid>`, generated once per payment attempt and reused on every retry.
2. **Server store:** table `idempotency_keys(key PK, request_hash, status, response_code, response_body, created_at)`.
3. **Flow:**
   - Insert the key with status `IN_PROGRESS`. The **unique constraint** is the guard: a concurrent duplicate fails the insert.
   - Key already `COMPLETED` -> return the stored response, same status and body. No second charge.
   - Key `IN_PROGRESS` -> return 409 (or wait briefly), so two parallel retries don't both charge.
   - Same key with a **different request body** -> 422: the client is misusing keys.
4. **Downstream:** pass the same key (or the order id) to the payment gateway as its idempotency key, so even our own retries cannot double-charge.
5. **Business guard too:** a unique constraint on `payments(order_id)` where one payment per order is the rule.
6. **Expiry:** keep keys 24-72 hours, then purge.
7. **Messaging side:** consumers of `PaymentCompleted` dedupe by event id in a processed-events table inside the same transaction as their update.

**Trade-offs and what can go wrong**
- Redis `SET key NX EX` is fast, but if Redis loses the key you lose the guarantee; for money I keep it in the same database as the payment, in the same transaction.
- If the server crashes after charging but before storing `COMPLETED`, the retry sees `IN_PROGRESS`: a recovery job queries the gateway with the key and completes the record.
- Generating the key on the server defeats the purpose; it must come from the client per user intent.

**Follow-ups to expect**
- *Which HTTP methods are idempotent?* -> GET, PUT, DELETE (and HEAD, OPTIONS) by definition; POST is not, so it needs the key.
- *How do you return the same response?* -> Store the status code and body with the key and replay them.

**60-second answer**
"I make the client send an Idempotency-Key header, generated once per payment and reused on every retry. On the server I
insert that key with status in-progress, and the unique constraint stops concurrent duplicates. If the key is already
completed I replay the stored response, so the retry gets the same answer with no second charge. If it's still in
progress I return 409, and if the same key arrives with a different body I reject it. I pass the same key to the payment
gateway, so even our own retries can't double-charge, and I keep a unique constraint on order id as a business guard. A
recovery job resolves records left in progress after a crash by asking the gateway."

### Q5 [senior] Money was deducted but order creation failed. How do you keep data consistent across services?
tags: data-consistency, saga, outbox, compensation, eventual-consistency, reconciliation, kafka, nagarro

**Start here: the concepts**
- In microservices each service has its own database, so one ACID transaction cannot cover payment and order.
- **Eventual consistency** = the system may be inconsistent for a short time but converges to a correct state.
- **Saga** = local transactions + compensating actions; **outbox** = reliable event publishing.

**The live scenario (functional requirement)**
*FR: "Pay, then create the order."* The payment service charged the card; the order service crashed before saving the
order. The customer saw "something went wrong" and an SMS from their bank.

**What the interviewer is really checking**
That you redesign the flow so this state is detectable and self-healing, instead of hoping the network does not fail.

**How I answer it** (120-second answer, point by point)
1. **Reorder the flow:** create the order **first** in `PENDING_PAYMENT`, then charge with the order id as the idempotency key. Now a payment always has an order to attach to.
2. **Saga orchestration:** the order service drives: reserve stock -> charge -> confirm. Each step result updates the order state.
3. **Outbox:** the payment service writes `payment` + `PaymentCompleted` event in one local transaction; a relay publishes to Kafka. The event cannot be lost even if the service crashes after commit.
4. **Idempotent consumers:** the order service applies `PaymentCompleted` once (processed-event table), retrying safely after its own crash.
5. **Compensation:** if the order can't be confirmed (stock gone, validation failed), the saga issues a **refund** and moves the order to `CANCELLED_REFUNDED`, then notifies the customer.
6. **Timeouts:** an order stuck in `PENDING_PAYMENT` beyond N minutes triggers a status query to the gateway, then completes or cancels.
7. **Reconciliation:** a daily job matches gateway settlements to orders; any orphan payment is refunded automatically and reported.

**Trade-offs and what can go wrong**
- 2PC/XA across services and an external gateway is not practical: the gateway won't participate, and locks are held across the network.
- Compensation is not "undo": a refund takes days to show on a card, so tell the customer clearly.
- Without monitoring for stuck states, a saga can silently stall.

**Follow-ups to expect**
- *Orchestration or choreography?* -> Orchestration for money flows (one place shows the state); choreography for loosely coupled side effects such as notifications.
- *Why not publish to Kafka right after the DB commit?* -> The process can crash between commit and publish (dual-write problem); the outbox removes that gap.

**60-second answer**
"You can't have one ACID transaction across payment and order services, so I design for failure. First I create the
order in pending-payment, then charge with the order id as the idempotency key, so a payment always has an order. The
payment service writes the payment and its event in one transaction through an outbox, so the event can't be lost, and
the order service consumes it idempotently. An orchestrated saga moves the order through its states. If it can't be
confirmed, the compensation is an automatic refund and a clear message to the customer. Orders stuck in pending trigger a
status check with the gateway, and a daily reconciliation catches anything left."

### Q6 [mid] What is auto-configuration in Spring Boot, and how does @SpringBootApplication work?
tags: spring-boot, auto-configuration, springbootapplication, starters, conditional, component-scan, nagarro

**Start here: the concepts**
- **Auto-configuration** = Spring Boot creates sensible beans for you based on what is on the classpath and in your properties (a `DataSource` when a JDBC driver is present, for example).
- **Starters** are dependency bundles (`spring-boot-starter-web`) that bring the libraries and trigger the matching auto-configuration.
- `@SpringBootApplication` = `@SpringBootConfiguration` + `@EnableAutoConfiguration` + `@ComponentScan`.

**The live scenario (functional requirement)**
*FR: "A new service must connect to PostgreSQL and expose REST endpoints with minimal setup."* Adding
`spring-boot-starter-web`, `spring-boot-starter-data-jpa` and the driver, plus three properties, gave a running app with
Tomcat, Jackson, Hikari, JPA and transactions.

**What the interviewer is really checking**
That you know the mechanism (conditional beans loaded from imports files), how to override it, and how to debug it.

**How I answer it** (120-second answer, point by point)
1. **Entry point:** `@SpringBootApplication` on the main class. `@ComponentScan` scans its package and sub-packages (so put it at the root package). `@EnableAutoConfiguration` imports auto-configuration classes.
2. **Where they come from:** each library lists its auto-configuration classes in `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` (Boot 2.7+; `spring.factories` before that).
3. **Conditions decide:** `@ConditionalOnClass` (library present), `@ConditionalOnMissingBean` (you did not define your own), `@ConditionalOnProperty` (feature flag). Example: `DataSourceAutoConfiguration` creates Hikari only if a driver is present and you have not declared a `DataSource`.
4. **Overriding:** define your own bean (back-off via `@ConditionalOnMissingBean`), set properties (`spring.datasource.hikari.maximum-pool-size`), or exclude: `@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)`.
5. **Debugging:** run with `--debug` (or `debug=true`) for the **condition evaluation report**, or `/actuator/conditions`: it lists which auto-configurations matched and why.
6. **Writing your own:** a company starter with an `@AutoConfiguration` class plus the imports file, for shared logging, security or tracing defaults.

**Trade-offs and what can go wrong**
- "Magic" surprises: an unexpected dependency on the classpath (an embedded DB, for example) activates configuration you did not want.
- Putting the main class in a sub-package means beans elsewhere are not scanned.
- Too many starters slow startup and enlarge the attack surface; include only what you use.

**Follow-ups to expect**
- *Difference between @Component and @Bean?* -> `@Component` marks a class for scanning; `@Bean` is a factory method in a `@Configuration` class, useful for third-party classes.
- *What are the bean scopes?* -> singleton (default), prototype, and web scopes request/session/application.

**60-second answer**
"@SpringBootApplication combines configuration, component scanning from the main class's package, and enable
auto-configuration. Auto-configuration classes are listed by each library in an AutoConfiguration.imports file, and
they're guarded by conditions: on-class, on-missing-bean, on-property. So if the PostgreSQL driver is on the classpath
and I haven't defined a DataSource, Boot creates a Hikari pool from my properties. I override it by declaring my own bean,
setting properties, or excluding the auto-configuration. To debug I use the condition evaluation report with --debug or
the actuator conditions endpoint. And I've written a company starter the same way for shared logging and security."

### Q7 [mid] How do you add caching to a Spring Boot service, and how do you keep the cache correct?
tags: caching, cacheable, cacheevict, redis, caffeine, ttl, cache-aside, invalidation, stampede, spring-boot, nagarro

**Start here: the concepts**
- **Cache-aside:** read from the cache; on a miss, read from the database and put it in the cache.
- Spring's cache abstraction: `@EnableCaching`, `@Cacheable`, `@CachePut`, `@CacheEvict`, backed by **Caffeine** (local, in-memory) or **Redis** (shared).
- The hard part is **invalidation**: when the data changes, stale copies must expire or be removed.

**The live scenario (functional requirement)**
*FR: "Product details are read 5,000 times a second and change a few times a day. Price changes must show within
1 minute."*

**What the interviewer is really checking**
Choosing local vs distributed cache, a TTL that matches the business freshness rule, and the classic failure modes
(stampede, stale data, proxy self-invocation).

**How I answer it** (120-second answer, point by point)
1. **Annotate:** `@Cacheable(value = "products", key = "#id")` on `getProduct(id)`; `@CacheEvict(value = "products", key = "#product.id")` on update.
2. **Choose the store:** 8 pods with local Caffeine each hold a copy and cannot evict each other, so a change is visible only after the TTL. **Redis** gives one shared copy and one eviction. For hot, tiny reference data I use two levels: Caffeine (10-30 s) in front of Redis.
3. **TTL from the business rule:** price must show within 1 minute -> TTL 60 s maximum, plus eviction on update for faster consistency.
4. **Cache the DTO, not the JPA entity** (lazy proxies and serialization trouble).
5. **Stampede:** when a hot key expires, hundreds of requests hit the database together. Use `@Cacheable(sync = true)` (one loader per key per instance), TTL jitter, or refresh-ahead.
6. **Null and negative caching:** cache "not found" briefly to protect against repeated misses (and enumeration attacks).
7. **Measure:** hit ratio, eviction rate and latency via Micrometer cache metrics.

**Trade-offs and what can go wrong**
- `@Cacheable` is proxy-based, so calling it from the same class skips the cache.
- Evict-on-update plus a parallel read can race and put the old value back; short TTLs bound the damage.
- Caching everything hides slow queries until the cache is flushed and the database collapses.

**Follow-ups to expect**
- *What is cache-through/write-behind?* -> Write-through updates cache and DB together; write-behind writes the DB later (fast, risk of loss).
- *How do you evict across pods with Caffeine?* -> Publish an invalidation event (Redis pub/sub or Kafka) that each pod listens to.

**60-second answer**
"I enable Spring's cache abstraction, put @Cacheable on the read method keyed by id, and @CacheEvict on updates. With
eight pods I use Redis as the shared cache, so one eviction is enough. For very hot reference data I add a short local
Caffeine layer in front. The TTL comes from the business rule: prices visible within a minute means at most 60 seconds.
I cache DTOs, not entities. To avoid a stampede on expiry I use sync equals true and add TTL jitter, and I cache
not-found results briefly. I watch the hit ratio through Micrometer, and I remember @Cacheable is proxy-based, so
self-calls skip it."

### Q8 [mid] Explain API gateway, service discovery and load balancing in a microservices setup
tags: api-gateway, service-discovery, load-balancing, spring-cloud-gateway, eureka, kubernetes-service, bff, nagarro

**Start here: the concepts**
- **API gateway** = one entry point for clients: routing, authentication, rate limiting, TLS, request aggregation.
- **Service discovery** = how a service finds the current addresses of another service (instances come and go).
- **Load balancing** = spreading calls across those instances, either server-side (a load balancer) or client-side (the caller picks).

**The live scenario (functional requirement)**
*FR: "Web and mobile call 12 backend services. Instances scale from 2 to 20 during sales. Clients must only know one
host name."*

**What the interviewer is really checking**
That you know what each piece does, the Spring Cloud vs Kubernetes-native options, and the gateway's risks.

**How I answer it** (120-second answer, point by point)
1. **Gateway:** Spring Cloud Gateway (or a managed gateway / Kong) routes `/orders/**` to the order service, validates JWTs, rate-limits per client, adds correlation ids, and can host a **BFF** per client type. No business logic in it.
2. **Discovery, two worlds:**
   - **Kubernetes:** a `Service` gives a stable DNS name (`order-service.prod.svc`); kube-proxy or the mesh balances across ready pods. No Eureka needed.
   - **Outside Kubernetes:** Eureka or Consul registries; instances register and send heartbeats, callers look them up.
3. **Load balancing:** in Kubernetes, the Service (or Istio/Linkerd) does it; with Eureka, **Spring Cloud LoadBalancer** on the client picks an instance (round robin by default).
4. **Resilience around calls:** timeouts, retries with backoff for idempotent calls, and circuit breakers (Resilience4j) on the caller side.
5. **Gateway availability:** run several replicas behind the cloud load balancer; it is on every request path, so it must be stateless and fast.
6. **Scenario answer:** cloud LB -> Spring Cloud Gateway (3 replicas) -> Kubernetes Services -> pods scaled by HPA from 2 to 20; the gateway only knows service names.

**Trade-offs and what can go wrong**
- Putting business logic or orchestration in the gateway turns it into a distributed monolith bottleneck.
- Client-side load balancing with stale registry data sends traffic to dead instances; keep heartbeat/TTL short and retry once on another instance.
- Over-aggregation in the gateway increases latency coupling; a BFF per client is cleaner.

**Follow-ups to expect**
- *Gateway vs service mesh?* -> Gateway handles north-south (client to cluster) traffic; a mesh handles east-west (service to service) with mTLS, retries and telemetry.
- *How does the gateway rate-limit across replicas?* -> A shared Redis token bucket (Spring Cloud Gateway's `RequestRateLimiter`).

**60-second answer**
"The API gateway is the single entry point: it routes by path, validates tokens, rate-limits, adds correlation ids, and
can serve a BFF per client, but it holds no business logic. Service discovery tells callers where instances are. On
Kubernetes a Service gives a stable DNS name, and the platform or a mesh balances across ready pods, so Eureka isn't
needed. Outside Kubernetes I'd use Eureka or Consul with Spring Cloud LoadBalancer on the client. Around every call I add
timeouts, retries for idempotent calls and circuit breakers. The gateway runs as several stateless replicas, because
it's on every request path."

### Q9 [mid] Do you know Kafka? How do partitions give you ordering and scale?
tags: kafka, partitions, ordering, message-key, consumer-group, offsets, scaling, nagarro

**Start here: the concepts**
- A **topic** is split into **partitions**; each partition is an ordered, append-only log.
- Messages with the **same key** go to the same partition, so their order is kept.
- In a **consumer group**, each partition is read by exactly one consumer, so partitions are the unit of parallelism.

**The live scenario (functional requirement)**
*FR: "Order events (created, paid, shipped) must be processed in order per order, at 10,000 events a second."*

**What the interviewer is really checking**
Several candidates report a quick yes/no Kafka check, then a probe on ordering and partitions. They want precise
answers: ordering per partition only, key choice, consumer-group scaling limits.

**How I answer it** (120-second answer, point by point)
1. **Ordering is per partition, not per topic.** Key by `orderId`, so every event for one order lands in the same partition in order; different orders run in parallel.
2. **Scale:** partitions = maximum parallel consumers in one group. 10,000 events/s with each consumer handling 1,000/s -> at least 10 partitions; I'd pick 24-30 for headroom (adding partitions later changes key-to-partition mapping).
3. **Producer settings for order and no loss:** `acks=all`, `enable.idempotence=true` (default since Kafka 3.0), which keeps ordering safe even with retries and up to 5 in-flight requests.
4. **Consumer side:** commit offsets **after** processing (at-least-once), and make processing idempotent. Don't process one partition's records in parallel threads unless you key-partition the work again, or you lose order.
5. **Failures:** a poison message would block the partition; route it to a retry topic/DLT after N attempts (Spring Kafka `DefaultErrorHandler` + `DeadLetterPublishingRecoverer`).
6. **Rebalancing:** consumers joining/leaving trigger a rebalance; cooperative sticky assignment (or KIP-848's new protocol) reduces pauses.

**Trade-offs and what can go wrong**
- A hot key (one giant customer) overloads one partition: consider a compound key if strict per-customer order is not needed.
- Sending a failed event to a retry topic breaks strict order for that key; if order is critical, pause/retry in place or park all later events for that key.
- More partitions = more open files, longer leader elections and rebalances; don't create thousands without need.

**Follow-ups to expect**
- *More consumers than partitions?* -> The extra consumers sit idle.
- *How do two groups read the same topic?* -> Independently; each group has its own offsets, so every group gets every message.

**60-second answer**
"Yes, I've used Kafka in production. A topic is split into partitions, and each is an ordered log, so ordering is only
guaranteed within a partition. I key by order id, so all events of one order land in one partition in sequence, while
different orders are processed in parallel. Partitions are the unit of scaling: one consumer per partition in a group,
so for 10,000 events a second I'd start around 24 partitions. Producers use acks all with idempotence, which keeps
ordering safe with retries. Consumers commit after processing and are idempotent. Poison messages go to a retry topic or
DLT so they don't block the partition."

### Q10 [mid] Java 8 streams round: find the second non-repeating character, and group employees by department and role
tags: java8, streams, collectors, groupingby, linkedhashmap, coding-round, nagarro

**Start here: the concepts**
- `Collectors.groupingBy(classifier, mapFactory, downstream)` groups elements; nesting it gives multi-level maps.
- `Function.identity()` + `LinkedHashMap::new` + `counting()` keeps **insertion order** while counting, which is what "first/second non-repeating" needs.
- Streams are declarative: say *what* (group, filter, count), not *how* (loops and indexes).

**The live scenario (functional requirement)**
Candidates report two short live-coding prompts in the technical round: *"Return the second non-repeating character of
'swiss bank'"* and *"From a list of employees, build department -> role -> list of names."*

**What the interviewer is really checking**
Fluency with `groupingBy` and ordered maps, handling the empty case, and knowing when a plain loop is clearer.

**How I answer it** (120-second answer, point by point)
1. **Second non-repeating character:**
   ```java
   Optional<Character> second = input.chars().mapToObj(c -> (char) c)
       .collect(Collectors.groupingBy(Function.identity(), LinkedHashMap::new, Collectors.counting()))
       .entrySet().stream().filter(e -> e.getValue() == 1)
       .map(Map.Entry::getKey).skip(1).findFirst();
   ```
   `LinkedHashMap` keeps the first-seen order; `skip(1)` gives the second. Return `Optional` for the "none" case. O(n) time.
2. **Explain the edge cases:** spaces (filter them out if required), case sensitivity (`Character.toLowerCase`), Unicode surrogate pairs (use `codePoints()` for full correctness).
3. **Group by department and role:**
   ```java
   Map<String, Map<String, List<String>>> byDeptRole = employees.stream()
       .collect(Collectors.groupingBy(Employee::department,
                Collectors.groupingBy(Employee::role,
                    Collectors.mapping(Employee::name, Collectors.toList()))));
   ```
4. **Variants they ask next:** count per department (`counting()`), highest-paid per department (`maxBy(comparing(Employee::salary))` or `toMap` with `BinaryOperator.maxBy`), average salary (`averagingDouble`), sorted output (`TreeMap::new` as the map factory).
5. **Say when not to use streams:** for very hot loops or complex early-exit logic, a simple loop is clearer and avoids boxing.

**Trade-offs and what can go wrong**
- `groupingBy` with a `null` key throws `NullPointerException`; filter nulls first.
- Plain `groupingBy` returns a `HashMap` with no order; say which order you need.
- Parallel streams on small lists are slower, not faster.

**Follow-ups to expect**
- *First non-repeating character?* -> Same pipeline without `skip(1)`.
- *map vs flatMap?* -> `map` transforms one to one; `flatMap` flattens one element into a stream of many (lists of lists, words in lines).

**60-second answer**
"For the second non-repeating character I group the characters with groupingBy, using identity, a LinkedHashMap
factory and counting, so insertion order is kept. Then I filter entries with count one, skip one and findFirst,
returning an Optional for the 'none' case. It's O(n), and I'd mention case, spaces and code points. For employees I nest
groupingBy: department, then role, then mapping to names into a list. Common variants are counting, maxBy salary per
department, or a TreeMap factory for sorted keys. I'd also say that groupingBy fails on null keys, and that a plain loop
is fine when it's clearer."
