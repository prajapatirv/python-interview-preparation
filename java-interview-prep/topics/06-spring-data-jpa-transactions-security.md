---
id: 06-data-security
title: Spring Data, JPA/Hibernate, Transactions & Spring Security
focus: Persistence pitfalls, transaction boundaries, OAuth2/JWT security
---

### Q1 [basic] What is JPA vs Hibernate vs Spring Data JPA?
JPA = specification (Jakarta Persistence). Hibernate = the most common implementation. Spring Data JPA = repository abstraction on top (`JpaRepository`, derived queries, `@Query`, paging). Know that Hibernate is doing the SQL.

### Q2 [basic] What are the entity states?
Transient (new), Managed/Persistent (in the persistence context, changes auto-flushed), Detached (session closed), Removed. "Dirty checking" means a managed entity changed in a transaction is updated at flush without calling `save()`.

### Q3 [basic] LAZY vs EAGER loading?
LAZY loads a relation when first accessed (a proxy); EAGER loads it immediately. Default is LAZY for `@OneToMany`/`@ManyToMany` and EAGER for `@ManyToOne`/`@OneToOne` - set `@ManyToOne(fetch = LAZY)` explicitly. `LazyInitializationException` = you touched a lazy field after the session closed; fix with a fetch join/DTO projection, not `open-in-view`.

### Q4 [intermediate] What is the N+1 select problem and how do you fix it?
Loading 1 list of orders then 1 query per order for its items = N+1 queries. Fix with `JOIN FETCH`, `@EntityGraph`, `@BatchSize`/`default_batch_fetch_size`, or a DTO projection. Detect: enable SQL logging in tests and assert query counts (Hypersistence Utils / datasource-proxy).

### Q5 [intermediate] How does `@Transactional` work and what are its traps?
A proxy opens a transaction, runs the method, commits or rolls back. Traps: self-invocation bypasses the proxy; only **unchecked** exceptions roll back by default (`rollbackFor = Exception.class` for checked); `private`/`final` methods; the transaction is thread-bound so work in another thread is outside it; long transactions hold connections - never call remote services inside one.

### Q6 [intermediate] Propagation and isolation levels?
Propagation: `REQUIRED` (join or create, default), `REQUIRES_NEW` (suspend and start a separate one - e.g. audit log that must survive rollback), `NESTED` (savepoint), `SUPPORTS`, `MANDATORY`, `NEVER`. Isolation: READ COMMITTED (default in Oracle/Postgres), REPEATABLE READ (MySQL default), SERIALIZABLE. Higher isolation = fewer anomalies, more locking/retries.

### Q7 [intermediate] Optimistic vs pessimistic locking?
Optimistic: a `@Version` column; the update fails with `OptimisticLockException` if someone else changed the row - good for low contention, retry on failure. Pessimistic: `SELECT ... FOR UPDATE` (`@Lock(PESSIMISTIC_WRITE)`) - good for high contention on the same row, but risks waits/deadlocks. Use `SKIP LOCKED` for job queues in a table.

### Q8 [intermediate] First-level vs second-level cache?
L1 is the persistence context (per transaction, always on). L2 is shared across sessions (Ehcache/Caffeine/Infinispan) and only suits read-mostly reference data; it adds invalidation complexity. Query cache is rarely worth it. Prefer an application-level cache with explicit TTL.

### Q9 [intermediate] When do you use JdbcTemplate/jOOQ/native SQL instead of JPA?
Reporting queries, bulk updates, complex joins/window functions, Oracle-specific features, and hot paths where you need exact SQL. JPA suits CRUD with an aggregate; mixing both is normal (CQRS-style: JPA for writes, SQL/projections for reads).

### Q10 [intermediate] How do you do paging safely?
`Pageable` with a stable sort. Offset paging gets slower with depth (O(offset)); for large tables use keyset/seek paging (`WHERE id > :last ORDER BY id LIMIT 50`). Avoid `Page` (it runs an extra `count(*)`) when you only need `Slice`.

### Q11 [advanced] Why is `equals/hashCode` on JPA entities tricky?
The id is null before persist and the proxy class differs from the entity class. Use a stable business key or compare ids only when non-null with a constant `hashCode`. Never include lazy collections in `equals`, `hashCode` or `toString` (it triggers loading or infinite recursion).

### Q12 [advanced] How do you manage schema changes safely?
Flyway/Liquibase versioned migrations, run by the pipeline, never `ddl-auto=update` in production. For zero downtime use **expand/contract**: add nullable column -> deploy code writing both -> backfill in batches -> switch reads -> drop the old column in a later release. Keep every migration backward compatible with the previous app version.

### Q13 [advanced] How do you do bulk inserts efficiently with JPA?
`hibernate.jdbc.batch_size=50`, `order_inserts/order_updates=true`, avoid `IDENTITY` ids (disables batching) - use sequences with `allocationSize`, flush and clear the persistence context every batch. For millions of rows use JDBC batch, `COPY` (Postgres), or SQL*Loader/`MERGE` (Oracle).

### Q14 [basic] How does Spring Security's filter chain work?
Requests pass through a `SecurityFilterChain` of filters: authentication filters build an `Authentication`, authorization filters check rules (`authorizeHttpRequests`), then the request reaches the controller. Configure with a `SecurityFilterChain` bean and the lambda DSL (the old `WebSecurityConfigurerAdapter` is gone).

### Q15 [intermediate] Authentication vs authorization; sessions vs JWT?
Authentication = who are you; authorization = what may you do. Session: server state, easy revoke, needs sticky/shared store. JWT: stateless signed token, scales easily, hard to revoke before expiry -> short TTL access token + refresh token + a revocation list when needed. Always validate signature, `exp`, `iss`, `aud`.

### Q16 [intermediate] Explain OAuth2 / OIDC flows you would use.
Authorization Code + PKCE for user login (SPA/mobile/web), Client Credentials for service-to-service, refresh token for renewal. The API acts as a **resource server** validating JWTs from the IdP (Keycloak, Azure AD/Entra ID, Okta, Cognito). Use scopes/roles for authorization; never use the implicit flow.

### Q17 [advanced] Method security and common vulnerabilities to mention?
`@PreAuthorize("hasRole('ADMIN') or #id == authentication.name")` for fine-grained rules. OWASP list: broken access control (check ownership, not just roles - IDOR), injection (parameterised queries), mass assignment (use DTOs), SSRF, security misconfiguration, vulnerable dependencies (SBOM + Dependabot/Snyk), secrets in code. Add CSRF protection for cookie sessions, CORS allow-list, rate limiting, security headers.

### Q18 [design] Design authentication/authorization for a set of microservices.
Edge: API gateway validates the JWT from the IdP (or passes it on); each service re-validates (zero trust) as a resource server. Service-to-service: client-credentials tokens or mTLS from a service mesh. Propagate user identity via the token, not custom headers. Central policy/roles with least privilege, audit logging, short TTL + key rotation (JWKS), secrets in a vault.

### Q19 [intermediate] How do you protect sensitive data in the database and logs?
Encrypt at rest (TDE / disk), encrypt specific columns (PII) with envelope encryption (KMS), hash passwords with bcrypt/argon2, mask PII in logs, never log tokens/card data, restrict DB users per service, and rotate credentials (the API-key rotation work you did is a good story).

### Q20 [design] Design the data access layer so that the service can later move from Oracle to PostgreSQL (or add Couchbase).
Repository interfaces in the domain layer, implementations in infrastructure; avoid vendor SQL in the service; keep SQL in one place; use Flyway per vendor if dialects differ; contract tests that run against both DBs with Testcontainers; map entities <-> domain objects so the model does not depend on JPA annotations.

### Q21 [design] Design a safe approach for a long-running batch update of 50 million rows without locking users out.
Process in small keyset-paginated chunks (1-5k rows) per transaction, commit between chunks, run off-peak, use a checkpoint table so restarts resume, and throttle based on replication lag or lock waits. Avoid loading entities into the persistence context - use JDBC batch or a bulk `UPDATE ... WHERE id BETWEEN`. Add idempotency so a re-run is harmless. Failure modes: huge undo/redo, long transactions blocking vacuum or purge, deadlocks with online traffic.
