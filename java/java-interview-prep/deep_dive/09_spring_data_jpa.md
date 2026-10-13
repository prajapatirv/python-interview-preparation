# Spring Data JPA, Hibernate and transactions

> **Runnable:** [`01_n_plus_one_and_lazy_loading.java`](../examples/09_spring_data_jpa/01_n_plus_one_and_lazy_loading.java) ·
> [`02_isolation_levels_and_optimistic_locking.java`](../examples/09_spring_data_jpa/02_isolation_levels_and_optimistic_locking.java)
> **Crib sheet:** [`topics/06-spring-data-jpa-transactions-security.md`](../topics/06-spring-data-jpa-transactions-security.md) · **Guide:** Q37

## What interviewers are actually probing

The ORM is where Java services quietly get slow or wrong: N+1 selects, lazy-loading exceptions, lost updates, transactions held across a remote call.
Expect "what is N+1 and how do you fix it", "isolation levels", "optimistic vs pessimistic locking", "propagation", "why is my `@Transactional` not rolling back",
and "how does `save()` decide insert vs update".

## Must-know points

- Persistence context (first-level cache) = per `EntityManager`/transaction; entities are *managed*, *detached*, *transient*, *removed*; changes to managed entities are flushed on commit (**dirty checking**).
- `@ManyToOne`/`@OneToOne` default **EAGER**, `@OneToMany`/`@ManyToMany` default **LAZY**. Make everything `LAZY` and fetch deliberately.
- **N+1**: 1 query for the parents + N for each child collection. Fix with `JOIN FETCH`, `@EntityGraph`, `@BatchSize`/`default_batch_fetch_size`, or DTO projections.
- Isolation anomalies: dirty read, non-repeatable read, phantom read, lost update.
- `@Version` = optimistic locking; `@Lock(PESSIMISTIC_WRITE)` = `SELECT … FOR UPDATE`.
- `@Transactional`: proxy-based, rollback on runtime exceptions, keep **short**, never across remote calls.
- `spring.jpa.open-in-view` defaults to **true** (a warning is logged): turn it off.

## Interview questions and full answers

### Q1. What is the N+1 problem and how do you detect and fix it?

Loading `N` parents and then touching a lazy association on each issues `1 + N` queries (example 09/01 section 1: 101 queries for 100 authors).
**Detect**: `spring.jpa.show-sql`/`logging.level.org.hibernate.SQL=DEBUG`, Hibernate statistics, `datasource-proxy`/`p6spy`, or a test that asserts the statement count.
**Fix**: `JOIN FETCH`/`@EntityGraph` for the specific use case (1 query, but beware cartesian products and pagination in memory); `@BatchSize(25)` or `hibernate.default_batch_fetch_size` (1 + N/25 queries, works with paging);
or a **DTO projection** for read models. Don't "fix" it by switching to EAGER — that just moves N+1 everywhere.

### Q2. What is `LazyInitializationException`?

You touched a lazy association after the persistence context closed (outside the transaction or after the session ended).
Fixes: fetch what you need inside the transaction (fetch join/entity graph), map to a DTO inside the service, or use a projection. Avoid `open-in-view=true`, which keeps the session open through the view layer and hides N+1/long connection holds.

### Q3. How do `save()`, `persist`, `merge`, `flush` and `saveAndFlush` behave?

`SimpleJpaRepository.save()` calls `persist` if the entity `isNew()` (null id or null `@Version`) else `merge` (which may SELECT first, returning a *managed copy*).
Changes to managed entities are flushed automatically before queries and on commit, so calling `save()` on an already-managed entity is redundant. `flush()` forces SQL now (useful to surface constraint violations inside a method); it does not commit.
Gotcha: assigned ids with no `@Version` make `save` do a SELECT + INSERT; implement `Persistable` or use generated ids.

### Q4. Explain the transaction isolation levels and the anomalies.

| Level | Dirty read | Non-repeatable read | Phantom |
|---|---|---|---|
| READ UNCOMMITTED | possible | possible | possible |
| READ COMMITTED | prevented | possible | possible |
| REPEATABLE READ | prevented | prevented | possible (prevented by gap locks/MVCC in some engines) |
| SERIALIZABLE | prevented | prevented | prevented |

Defaults: PostgreSQL/Oracle/SQL Server = READ COMMITTED; MySQL InnoDB = REPEATABLE READ. Higher isolation costs concurrency (locks/aborts). Example 09/02 sections 1–2 interleave two transactions to show each anomaly.
Say that **lost update** is not fixed by READ COMMITTED; it needs `@Version`, `SELECT FOR UPDATE`, or an atomic `UPDATE … SET x = x + ?`.

### Q5. Optimistic versus pessimistic locking?

**Optimistic** (`@Version`): no DB lock; the `UPDATE … WHERE id=? AND version=?` fails (0 rows → `OptimisticLockException`) if someone else changed it; retry the use case. Best when conflicts are rare — most web workloads.
**Pessimistic** (`@Lock(PESSIMISTIC_WRITE)`, `FOR UPDATE`, `SKIP LOCKED` for queues): blocks others; best when conflicts are common (hot inventory row) and retries are expensive. Keep the transaction tiny, lock in a consistent order, set lock timeouts.

### Q6. Explain transaction propagation and a real use for `REQUIRES_NEW`.

`REQUIRED` joins or starts; `REQUIRES_NEW` suspends the current and starts an independent transaction (commits/rolls back separately); `NESTED` uses a savepoint; `SUPPORTS/NOT_SUPPORTED/MANDATORY/NEVER` control presence.
Use `REQUIRES_NEW` for an **audit/outbox record that must persist even if the business transaction rolls back**. Danger: it needs a second connection; with a small pool all threads can end up waiting for a second connection while holding the first → deadlock under load.

### Q7. Why did my transaction not roll back?

Checked exception (default commit; use `rollbackFor`); exception swallowed by a `try/catch`; self-invocation/proxy bypass; method not `public`; `@Transactional` on a non-bean; the failure happened in another thread; or a `REQUIRES_NEW` inner transaction committed already.
`TransactionAspectSupport.currentTransactionStatus().setRollbackOnly()` is the explicit lever when you catch but still want rollback.

### Q8. Entity design: `equals`/`hashCode`, ids, and `@Entity` pitfalls?

Don't use Lombok `@Data` on entities (it includes lazy collections in `toString/hashCode`, causing loads and recursion). Base `equals/hashCode` on a business key or on the id with a constant hash (`getClass().hashCode()`) when the id is generated.
Keep a no-arg constructor (protected), avoid `final` classes (proxies), prefer `Long` + sequence (`SEQUENCE` + `allocationSize` for batching; `IDENTITY` disables JDBC insert batching), and `Instant` for timestamps. Use DTOs at the API boundary.

### Q9. What is the second-level cache and when do you use it?

L1 is per persistence context (automatic). **L2** (Ehcache/Infinispan/Hazelcast/Redis via provider) is shared across sessions; opt in per entity (`@Cache`). It suits read-mostly reference data; it needs an invalidation strategy and doesn't see out-of-band DB changes.
Often an application-level cache (`@Cacheable` with Caffeine/Redis) on service results is simpler and more explicit.

### Q10. Spring Data repositories: derived queries, `@Query`, specifications, projections?

Derived (`findByStatusAndCreatedAtAfter`) for simple cases; `@Query` (JPQL/native) for control; `Specification`/Querydsl for dynamic filters; **projections** (interfaces/records) to select only needed columns; `Slice` vs `Page` (Page runs a COUNT).
Use `@Modifying` bulk updates carefully: they bypass the persistence context (`clearAutomatically=true`).

### Q11. How do you do schema migrations safely?

Flyway/Liquibase versioned scripts run at startup or as a pipeline step; **expand → migrate → contract** so old and new app versions both work during a rolling deploy (add nullable column, backfill, switch reads, then drop).
Never let `ddl-auto=update` manage production schemas; use `validate`.

### Q12. Connection pool sizing (HikariCP) — how and why?

Pool size is a DB-capacity decision, not a thread-count one: a small pool (often `(cores × 2) + effective spindles` per DB, e.g. 10–20 per service instance) outperforms a huge one because the DB serialises work anyway.
Watch `hikaricp.connections.active/pending` and acquisition time; set `connectionTimeout`, `maxLifetime` (< DB/firewall idle timeout), `leakDetectionThreshold`. Total connections = pool × instances must fit the DB `max_connections`.

## A worked example

Run [`01_n_plus_one_and_lazy_loading.java`](../examples/09_spring_data_jpa/01_n_plus_one_and_lazy_loading.java): it prints the **exact SQL strings** for the naive, fetch-join and batch strategies and the query count for each.
Then [`02_isolation_levels_and_optimistic_locking.java`](../examples/09_spring_data_jpa/02_isolation_levels_and_optimistic_locking.java): section 3 shows balance=50 (lost update) without a version check and an exception + successful retry with one.

## Hands-on drills

1. Using any Spring Boot + H2 project, reproduce N+1 and fix it three ways; compare SQL counts.
2. Write a test that fails when a use case runs more than 5 SQL statements.
3. Implement an optimistic-lock retry with `@Retryable` and exponential backoff; explain idempotency requirements.
4. Process a queue table with `SELECT … FOR UPDATE SKIP LOCKED` from two workers.
5. Explain why `@Transactional` on a controller method that calls a remote service is dangerous.

## The 60-second spoken answer

"I keep associations lazy and fetch deliberately: fetch joins or entity graphs for a use case, batch fetching for lists, and DTO projections for read models,
and I watch SQL counts to catch N+1. Transactions are short and never span remote calls. For concurrent updates I use `@Version` optimistic locking with a retry,
and pessimistic locks only for genuinely hot rows. I know the isolation levels and that lost updates need a version or atomic update, not just a higher level.
Schema changes go through Flyway with expand-and-contract so rolling deploys stay safe."
