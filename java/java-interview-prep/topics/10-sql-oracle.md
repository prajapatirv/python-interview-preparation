---
id: 10-sql-oracle
title: SQL & Oracle (with PostgreSQL/MySQL notes)
focus: Query tuning, indexes, transactions, window functions, Oracle specifics
deep_dive: 09
examples: 09_spring_data_jpa
---

### Q1 [basic] What are the SQL join types?
INNER (matching rows), LEFT/RIGHT OUTER (all rows from one side), FULL OUTER (all from both), CROSS (cartesian product), SELF join. A frequent trap: a filter on the right table in the `WHERE` clause turns a LEFT JOIN into an inner join - put it in the `ON` clause.

### Q2 [basic] WHERE vs HAVING? GROUP BY rules?
`WHERE` filters rows before grouping; `HAVING` filters groups after aggregation. Every non-aggregated selected column must be in `GROUP BY`. Logical order: FROM -> WHERE -> GROUP BY -> HAVING -> SELECT -> ORDER BY -> LIMIT/FETCH.

### Q3 [basic] DELETE vs TRUNCATE vs DROP?
DELETE: row-by-row, can have WHERE, logged, rollbackable, fires triggers. TRUNCATE: removes all rows fast, resets high-water mark, DDL (auto-commit in Oracle). DROP: removes the object itself.

### Q4 [basic] Primary key vs unique key vs foreign key; NULL behaviour?
PK: unique + not null, one per table. Unique: allows NULL (Oracle allows multiple NULLs in a single-column unique index; behaviour differs by DB). FK: referential integrity. `NULL = NULL` is unknown, use `IS NULL`; Oracle treats empty string as NULL (a classic Oracle trap).

### Q5 [intermediate] How do indexes work and when do they not help?
A B-tree index keeps keys sorted so lookups are O(log n). Not used when: you wrap the column in a function (`WHERE TRUNC(date_col)=...` -> use a function-based index or a range), leading wildcard `LIKE '%abc'`, implicit type conversion, low selectivity on a big share of rows, or stale statistics. Composite index order matters: **leftmost prefix** rule.

### Q6 [intermediate] How do you read an execution plan? (Oracle)
`EXPLAIN PLAN FOR ...; SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY);` or `DBMS_XPLAN.DISPLAY_CURSOR` for the real plan with runtime stats. Look for full table scans on big tables, wrong join order/method (nested loops vs hash join), big difference between estimated and actual rows (stale stats), `TABLE ACCESS BY INDEX ROWID` repeated millions of times. Fix with indexes, stats (`DBMS_STATS`), rewriting the query, or hints as a last resort. PostgreSQL: `EXPLAIN (ANALYZE, BUFFERS)`.

### Q7 [intermediate] A query that was fast is now slow. What do you check?
Plan change (stats updated, data skew, bind-variable peeking), data growth, missing/invalid index, lock waits, parameter/type mismatch, a new code path (N+1), resource limits. Compare the old and new plan (AWR/SQL Monitor in Oracle, `pg_stat_statements` in Postgres).

### Q8 [intermediate] Window functions - examples?
```sql
SELECT emp_id, dept, salary,
  RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS rnk,
  salary - LAG(salary) OVER (PARTITION BY dept ORDER BY hire_date) AS diff,
  SUM(salary) OVER (PARTITION BY dept) AS dept_total
FROM employees;
```
Know `ROW_NUMBER` vs `RANK` vs `DENSE_RANK`, `LEAD/LAG`, running totals with `ROWS BETWEEN`.

### Q9 [intermediate] Find the Nth highest salary / duplicates / delete duplicates.
```sql
-- 2nd highest
SELECT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) r FROM emp) WHERE r = 2;
-- duplicates
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
-- delete duplicates keeping the lowest id
DELETE FROM users WHERE id NOT IN (SELECT MIN(id) FROM users GROUP BY email);
```

### Q10 [intermediate] What are ACID and the isolation anomalies?
Atomicity, Consistency, Isolation, Durability. Anomalies: dirty read, non-repeatable read, phantom read, lost update, write skew. Oracle/Postgres default READ COMMITTED (a statement sees data committed before it started); Oracle also offers SERIALIZABLE and read-only; its **MVCC** (undo) means readers don't block writers.

### Q11 [intermediate] Locks and deadlocks in a database?
Row locks on update; a second session waits (`ORA-00054` for `NOWAIT`, `ORA-00060` deadlock detected). Avoid by updating rows in a consistent order, keeping transactions short, indexing foreign keys (unindexed FKs cause table-level lock escalation in Oracle), and using `SELECT ... FOR UPDATE SKIP LOCKED` for work queues.

### Q12 [intermediate] Normalization vs denormalization?
Normalise (3NF) to avoid update anomalies for OLTP; denormalise deliberately for read performance/reporting (summary tables, materialized views), accepting redundancy and the need to keep it in sync.

### Q13 [intermediate] Oracle-specific: sequences, `ROWNUM`, `MERGE`, `DUAL`, partitioning?
Sequences for ids (`NEXTVAL`, 12c identity columns). `ROWNUM` is assigned before `ORDER BY` - use `FETCH FIRST n ROWS ONLY` (12c+) or a subquery. `MERGE` = upsert. `DUAL` = one-row dummy table. **Partitioning** (range/list/hash) speeds pruning and archiving of large tables. Know PL/SQL: packages, bulk collect/`FORALL`, cursors, exceptions.

### Q14 [advanced] How do you handle a table with 500 million rows?
Partition by date/key, index only what queries need, archive old data, use covering indexes, avoid `SELECT *`, batch deletes (don't delete 50M rows in one transaction), parallel query for reporting, materialized views for aggregates, and keyset pagination. Consider moving analytics to a warehouse/lakehouse.

### Q15 [advanced] Optimistic locking and idempotent upsert patterns in SQL?
`UPDATE t SET ..., version = version + 1 WHERE id = ? AND version = ?` -> zero rows updated means conflict. Idempotent insert: `INSERT ... ON CONFLICT (event_id) DO NOTHING` (Postgres) or `MERGE` / unique constraint + catch `ORA-00001` (Oracle).

### Q16 [advanced] Bind variables vs literals and SQL injection?
Bind variables let the DB reuse the parsed plan (less hard-parsing) and prevent SQL injection. Never concatenate user input; use `PreparedStatement`/named parameters. Dynamic ORDER BY needs a whitelist.

### Q17 [advanced] How do you do online schema change on a big table?
Add nullable columns (cheap), backfill in small batches, add index concurrently (`CREATE INDEX CONCURRENTLY` in Postgres, `ONLINE` in Oracle), use expand/contract, avoid long locks, run in a low-traffic window, and rehearse on a copy.

### Q18 [advanced] Backup, recovery and replication basics you should know?
RPO (data loss tolerated) and RTO (downtime tolerated) drive design. Oracle: RMAN backups, Data Guard standby; Postgres: WAL archiving, streaming replicas, PITR; Aurora/RDS: automated backups and Multi-AZ failover (30-60 s; connections must reconnect). **A backup is real only if the restore has been tested.**

### Q19 [design] Design the schema for a multi-tenant SaaS (e.g. ERP).
Options: shared tables with `tenant_id` (cheapest, needs row-level security and tenant-leading indexes), schema-per-tenant (better isolation, harder migrations), database-per-tenant (strongest isolation, costly). Choose by tenant count and compliance. Always enforce the tenant filter centrally (Hibernate filter/RLS) and test cross-tenant leaks.

### Q20 [design] Design reporting on a busy OLTP database without slowing it.
Read replica or standby for reports, summary/materialized tables refreshed incrementally, CDC to a warehouse, caching of dashboards, query timeouts and resource limits (Oracle Resource Manager), and scheduled heavy jobs off-peak.

### Q21 [design] Design the indexing and partitioning strategy for a table that grows by 100 million rows a month.
Start from the query patterns: index the filters and sort columns (composite index, equality columns first), partition by date (range/interval partitioning) so old partitions are dropped or archived cheaply and queries prune. Keep indexes lean because each one slows writes. Plan retention, statistics gathering and partition-local vs global indexes. Failure modes: global index invalidated on partition drop, skewed partitions, plans that stop pruning because of a function on the partition key.
