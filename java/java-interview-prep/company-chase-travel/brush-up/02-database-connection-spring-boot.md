# 02 - Database Connection from Spring Boot (Basic to Advanced)

**Chase project brush-up, point 2 of 4** (requested by Sujay: Spring Boot REST API · database connection from Spring Boot · Kafka consumer and producer · AWS S3, ECS, Aurora Postgres). Hub: [`../README.md`](../README.md).

**Functional requirement these answers are framed around (illustrative):** *"Card members search and book hotels with points, card or both. The booking service (Spring Boot on ECS Fargate behind an ALB) exposes REST APIs, stores bookings in Aurora PostgreSQL, publishes `BookingConfirmed` to Kafka (MSK) for notifications and rewards, and stores itinerary PDFs in S3. No double booking or double charge, p95 under 800 ms, survive an Aurora failover."*

**Stack to assume:** Spring Boot, HikariCP, Spring Data JPA/Hibernate (plus JdbcTemplate where needed), Aurora PostgreSQL on AWS, Flyway for migrations.

> **How to use this document:** give the direct answer first, then the production consequence. Travel examples are illustrative; replace them with real facts from your project.

---

## Part 1 - Basic (Q1-Q10)

### Q1 [basic] How does a Spring Boot app connect to a database?
Add the JDBC driver (`org.postgresql:postgresql`) and a starter (`spring-boot-starter-data-jpa` or `-jdbc`). Set properties and Boot auto-configures a `DataSource` (HikariCP by default).
```yaml
spring:
  datasource:
    url: jdbc:postgresql://aurora-writer.cluster-xyz.us-east-1.rds.amazonaws.com:5432/travel
    username: ${DB_USER}
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 10
```

### Q2 [basic] What is a connection pool and why is it needed?
Opening a database connection is slow (TCP, TLS, authentication). A pool keeps a fixed set of open connections and lends them out per request. This gives faster calls and protects the database from too many connections. HikariCP is the default pool in Spring Boot.

### Q3 [basic] JDBC vs JdbcTemplate vs JPA vs Spring Data JPA?
JDBC: low-level API. JdbcTemplate: Spring helper that removes boilerplate (connections, exceptions) while you write SQL. JPA: specification mapping objects to tables; Hibernate is the common implementation. Spring Data JPA: repositories on top (`JpaRepository`), derived queries, paging. Use JPA for CRUD on aggregates and SQL/JdbcTemplate for reports and bulk work.

### Q4 [basic] How do you map a table to a class?
```java
@Entity @Table(name = "booking")
public class Booking {
  @Id @GeneratedValue(strategy = GenerationType.SEQUENCE) private Long id;
  @Column(nullable = false) private String status;
  @Version private long version;
}
public interface BookingRepository extends JpaRepository<Booking, Long> {
  List<Booking> findByStatusAndCreatedAtAfter(String status, Instant from);
}
```

### Q5 [basic] What does `@Transactional` do?
It wraps a method in a database transaction through a proxy: begin, run, commit; roll back on an unchecked exception (checked exceptions need `rollbackFor`). Put it on the service layer, not the controller. Keep transactions short and do not call remote services inside one.

### Q6 [basic] What is the difference between lazy and eager loading?
Lazy loads a relation when first accessed; eager loads it at once. Defaults: `@OneToMany` lazy, `@ManyToOne` eager (set it to `LAZY` explicitly). Touching a lazy field after the session closed gives `LazyInitializationException`; fix with a fetch join or a DTO projection, not by keeping the session open in the view.

### Q7 [basic] What is `ddl-auto` and what should production use?
`spring.jpa.hibernate.ddl-auto` lets Hibernate create/update the schema. Use `none` or `validate` in production and manage the schema with Flyway or Liquibase versioned migrations, so changes are reviewed, repeatable and auditable.

### Q8 [basic] How do you keep passwords out of the code?
Environment variables injected by the platform from AWS Secrets Manager (ECS task definition `secrets`), or Spring Cloud AWS to load them at startup. Never commit credentials. Rotate secrets regularly and make the app tolerate rotation (see IAM auth/RDS Proxy later).

### Q9 [basic] What are the Spring Data repository methods you use most?
`save`, `findById`, `findAll(Pageable)`, `deleteById`, `existsById`, derived queries (`findByEmail`), `@Query` with JPQL or native SQL, and `@Modifying` for bulk updates. Return `Optional` for single results and a `Slice`/`Page` for lists.

### Q10 [basic] How do you test database code?
Repository tests with `@DataJpaTest` against a real database started by Testcontainers (PostgreSQL image), so dialect, constraints and indexes behave as in production. H2 hides differences and can pass tests that fail in Aurora PostgreSQL.

**Project hook (Part 1):** "Our service reads host/user/password from Secrets Manager through the ECS task definition, uses Hikari, and every schema change is a Flyway script reviewed in the PR."

---

## Part 2 - Mid Level (Q11-Q20)

### Q11 [mid] How do you size and tune the HikariCP pool?
A small pool is usually faster. HikariCP's guideline is `(database server cores * 2) + effective spindle count` for the **whole database**, not per app instance, so a per-task pool is often 5-20; then load test. The sum across all running tasks must stay below the database `max_connections` (tasks x pool size). Settings that matter: `maximumPoolSize`, `connectionTimeout` (fail fast, e.g. 3 s), `maxLifetime` (below any network/DB idle timeout), `minimumIdle`, and `leakDetectionThreshold`. Watch `hikaricp.connections.active/pending/timeout` metrics.

### Q12 [mid] Explain transaction propagation and isolation levels.
Propagation: `REQUIRED` (join or start; default), `REQUIRES_NEW` (suspend and start a separate transaction, for audit rows that must survive a rollback), `NESTED` (savepoint), `MANDATORY`, `SUPPORTS`. Isolation: PostgreSQL default is READ COMMITTED; REPEATABLE READ and SERIALIZABLE give stronger guarantees but can fail with serialization errors that you must retry.

### Q13 [mid] What is the N+1 query problem and how do you fix it?
Loading N parents and then one query per parent for a lazy relation (1 + N queries). Fix with `JOIN FETCH`, `@EntityGraph`, `@BatchSize` / `hibernate.default_batch_fetch_size`, or a DTO projection that selects only what the screen needs. Detect it by logging SQL in tests and asserting query counts.

### Q14 [mid] Optimistic vs pessimistic locking?
Optimistic: `@Version` column; an update fails with `OptimisticLockException` if the row changed since it was read; retry the operation. Best for low contention (booking edits). Pessimistic: `@Lock(PESSIMISTIC_WRITE)` -> `SELECT ... FOR UPDATE`; best for hot rows (inventory counters) but risks waits and deadlocks. Use `FOR UPDATE SKIP LOCKED` for table-based work queues.

### Q15 [mid] How do you do paging safely on large tables?
Offset paging scans and discards rows, so deep pages are slow. Use keyset paging on an indexed ordering: `WHERE (created_at, id) < (?, ?) ORDER BY created_at DESC, id DESC LIMIT 50`. Use `Slice` instead of `Page` when you do not need the total count (it avoids a `count(*)`).

### Q16 [mid] How do you use read replicas from Spring Boot with Aurora?
Aurora gives a **writer (cluster) endpoint** and a **reader endpoint** that load-balances across replicas. Define two `DataSource`s (or an `AbstractRoutingDataSource`) and send `@Transactional(readOnly = true)` work to the reader. Wrap the router in a `LazyConnectionDataSourceProxy` so the connection is chosen after the read-only flag is set, otherwise everything goes to the writer. Remember replica lag (usually milliseconds, but not zero): do not read your own write from a replica immediately after saving.

### Q17 [mid] How do you run Flyway/Liquibase migrations safely?
Version scripts (`V12__add_booking_index.sql`), run on startup or in a separate pipeline step, never edit an applied script. Use `CREATE INDEX CONCURRENTLY` for big tables (not inside a transaction), make each migration backward compatible with the previous app version, and test migrations on a copy of production-size data.

### Q18 [mid] How do you do efficient batch inserts/updates?
Set `hibernate.jdbc.batch_size=50`, `order_inserts=true`, `order_updates=true`. Avoid `IDENTITY` ids (they disable batching); use a sequence with `allocationSize`. Flush and clear the persistence context every batch. For very large loads use JDBC batch (`JdbcTemplate.batchUpdate`) or PostgreSQL `COPY`. Add `reWriteBatchedInserts=true` to the PostgreSQL JDBC URL for faster multi-row inserts.

### Q19 [mid] Which exceptions do you handle and how do you translate them?
Spring translates driver errors into `DataAccessException` subclasses: `DuplicateKeyException`/`DataIntegrityViolationException` (409), `OptimisticLockingFailureException` (retry or 409), `CannotAcquireLockException` and `QueryTimeoutException` (retryable), `TransientDataAccessException` (retry with backoff), `PessimisticLockingFailureException`. Handle them in one `@RestControllerAdvice`; never leak SQL text to clients.

### Q20 [mid] What are the common JPA mistakes in code reviews?
Using entities as API DTOs, `FetchType.EAGER` on collections, `findAll()` without paging, business logic in entity listeners, `equals/hashCode` using lazy collections or generated ids, `toString` that triggers lazy loading, long transactions that call remote services, open-session-in-view left enabled (`spring.jpa.open-in-view=false` is the safer setting), and unbounded `IN (...)` lists.

**Project hook (Part 2):** "We sized the pool from load tests and the task count, sent read-only queries to the Aurora reader endpoint, and caught an N+1 on the itinerary screen using a query-count assertion."

---

## Part 3 - Advanced and Design (Q21-Q30)

### Q21 [advanced] What happens to your app during an Aurora failover and how do you make it survive?
On failover Aurora promotes a replica to writer; the promotion itself is typically under 30 seconds, but with DNS updates and reconnects plan for up to about 60 seconds of errors; existing connections break. Make the app survive: use the **cluster endpoint** (not an instance endpoint), keep Hikari `maxLifetime` bounded and `connectionTimeout` short, enable connection validation (`keepaliveTime`), keep JVM/DNS caching low (`networkaddress.cache.ttl=10`), treat `SQLTransientConnectionException` as retryable with backoff for idempotent operations, expose readiness so the load balancer stops sending traffic during the blip, and consider the AWS Advanced JDBC Wrapper (failover plugin) or RDS Proxy. Test failover regularly in a lower environment.

### Q22 [advanced] "Connection is not available, request timed out after 30000ms" - how do you diagnose it?
Pool exhaustion. Check `hikaricp.connections.active` stuck at max and `pending` rising. Causes: slow queries holding connections, a transaction holding a connection while calling a remote service, a connection leak (use `leakDetectionThreshold`), a retry storm, database CPU/locks, or too many tasks x pool size hitting `max_connections`. Look at `pg_stat_activity` (state, wait_event, query), find long transactions, fix the root cause (shorten transaction, add index, add timeout), and only then adjust pool size.

### Q23 [advanced] How do you update the database and publish a Kafka event atomically?
You cannot with one transaction across both systems. Use the **transactional outbox**: in the same DB transaction, insert the business row and an `outbox` row. A relay (poller with `FOR UPDATE SKIP LOCKED`, or Debezium CDC) publishes outbox rows to Kafka and marks them sent. Consumers must be idempotent because delivery is at-least-once.

### Q24 [advanced] How do you make writes idempotent at the database level?
Use natural/unique keys and upserts: `INSERT ... ON CONFLICT (event_id) DO NOTHING` or `DO UPDATE ... WHERE excluded.version > target.version`. Store processed message ids in the same transaction as the side effect. This makes retries and Kafka redeliveries harmless.

### Q25 [advanced] How do you secure the database connection and credentials?
TLS to the database (`sslmode=verify-full` with the RDS CA bundle), least-privilege DB users per service (no superuser), credentials from Secrets Manager with rotation, or **IAM database authentication** (the app requests a short-lived token, valid 15 minutes, used as the password; refresh it when creating new connections). Private subnets, security group allowing only the ECS tasks, encryption at rest with KMS, and audit logging (pgaudit) for sensitive tables.

### Q26 [advanced] When would you add RDS Proxy, and what are the trade-offs?
RDS Proxy pools and shares connections between many clients and the database, which helps with spiky or many-connection workloads (Lambda, many small tasks) and speeds up failover handling. Trade-offs: extra hop and cost, connection pinning when you use session state (`SET`, prepared statements in some modes) which reduces sharing, and one more component to monitor. For a few ECS services with a well-sized Hikari pool it may be unnecessary.

### Q27 [advanced] Design the data model and consistency for a booking system with inventory, payment and itinerary.
Aggregates: `Booking` (root; status machine `PENDING -> CONFIRMED -> CANCELLED`), `Payment` (references booking id, provider reference, idempotency key), `Inventory` hold with expiry. One transaction per aggregate; cross-aggregate/service steps use a saga with compensations and an outbox. Constraints do the heavy lifting: unique keys on idempotency keys and provider references, check constraints on status transitions, foreign keys, version column. Index for the real queries (by customer and date, by status for sweepers). Add audit/history tables for status changes.

### Q28 [advanced] How do you scale a database that is growing fast?
In order: fix queries and indexes (`EXPLAIN (ANALYZE, BUFFERS)`, `pg_stat_statements`), cache hot reads, add read replicas, partition large tables by time (drop old partitions instead of deleting rows), archive cold data to S3, increase the instance class, and only then consider sharding or a purpose-built store. Aurora storage scales automatically, so the limits are usually CPU, connections and I/O patterns, not disk.

### Q29 [advanced] How do you change the schema with zero downtime?
Expand/contract: (1) add the new nullable column or table, (2) deploy code that writes both old and new, (3) backfill in small batches, (4) switch reads to the new column, (5) remove the old one in a later release. Avoid long locks: add constraints as `NOT VALID` then `VALIDATE`, create indexes `CONCURRENTLY`, set `lock_timeout`, and never rename/drop a column the running version still uses.

### Q30 [advanced] Walk through a production incident: database CPU at 100%.
Mitigate first (throttle or stop the heavy caller, scale reads to replicas, kill the runaway session). Then find top SQL by total time (`pg_stat_statements`, Performance Insights), check plan changes and missing indexes (`EXPLAIN ANALYZE`), lock waits, and connection storms. Fix with an index, a rewritten query, caching or a limit; add a slow-query alert and a regression test. Write a blameless RCA with timeline, root cause and actions.

**Project hook (Part 3):** "We hit [real example: pool exhaustion / failover blip / slow query]; I led the diagnosis with pg_stat_activity and Hikari metrics and the fix was ..."

---

## Quick revision card
- Hikari pool: small, bounded, total across tasks < DB max_connections.
- Short transactions; no remote calls inside them.
- Writer endpoint for writes, reader endpoint for read-only, mind replica lag.
- Flyway for schema, expand/contract for zero downtime.
- Outbox + idempotent upserts for DB-to-Kafka consistency.
- Failover: cluster endpoint, short timeouts, retry idempotent work, test it.

## 60-second answer for this point
"Boot auto-configures a HikariCP DataSource from the Aurora cluster endpoint, with credentials from Secrets Manager or IAM database auth, never in code. The pool is small and bounded, and tasks times pool size stays under max_connections. JPA handles aggregates; JdbcTemplate or COPY handles bulk work. Transactions live in the service, stay short and never wrap remote calls. Read-only work goes to the reader endpoint, keeping replica lag in mind. Flyway owns the schema with expand-contract changes. For failover: cluster endpoint, short timeouts, low DNS TTL, and retries only for idempotent work. DB-to-Kafka consistency comes from the outbox plus idempotent upserts."
