---
id: foundations-sql
title: SQL & relational databases: from the basics (drafted)
stack: java
skill: sql
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What are the SQL join types?
tags: sql, joins, inner-join, left-join, outer-join, cross-join, basics

**Start here: the concepts**
- **Relational database:** data is split into tables (for example `customers` and `orders`) so each fact is stored once. Splitting avoids duplication, but you need a way to put the pieces back together.
- **Join:** a query operation that combines rows from two tables, usually by matching a key. For example, `orders.customer_id` matches `customers.id`.
- **`ON` clause:** the rule that says which rows of the two tables belong together. It is applied while the join happens.
- **`WHERE` clause:** a filter applied to the result after the join has produced its rows.
- **NULL:** "no value". A join fills the missing side with NULLs when there is no match.
- **INNER JOIN:** returns only the rows that have a match on both sides.
- **LEFT OUTER JOIN:** returns every row from the left table. If there is no match on the right, the right columns are NULL. **RIGHT OUTER JOIN** is the mirror image. Most people just swap the table order and use LEFT.
- **FULL OUTER JOIN:** returns all rows from both sides, with NULLs where there is no match. Some databases, such as MySQL, don't support it. There you combine a LEFT and a RIGHT join with `UNION`.
- **CROSS JOIN:** pairs every row of one table with every row of the other (a cartesian product). It has no `ON` condition.
- **SELF join:** not a separate keyword. It means joining a table to itself under two aliases, using any join type. A typical use is employee and manager in the same `employees` table.

**The live scenario**
Marketing asks for a report of all 10,000 customers with their shipped orders. A developer writes `customers LEFT JOIN orders` and adds `WHERE orders.status = 'SHIPPED'`. The report shows only 6,200 customers, and the 3,800 who never shipped anything have vanished. Marketing mails the wrong segment. The cause is the filter's position, not the join type.

**What the interviewer is really checking**
Whether you can say what each join returns for unmatched rows, and whether you know the classic `WHERE` versus `ON` trap with outer joins.

**How I answer it**
1. **Name the five types and describe the unmatched rows.** INNER drops them, LEFT keeps unmatched left rows, FULL keeps both sides, and CROSS has no matching at all. Unmatched rows are the only thing that really separates the types.
2. **Say that SELF is a technique, not a type.** The same table is used twice under different aliases, so one row can be compared with another row of the same table.
3. **Explain the trap.** In a LEFT JOIN, unmatched rows get NULL in the right-table columns. A `WHERE orders.status = 'SHIPPED'` test is false for NULL, so those rows are removed. That quietly turns your LEFT JOIN into an INNER JOIN. Put the condition in `ON` so it limits which right-side rows match, while every left row stays:
```sql
SELECT c.name, o.id FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id AND o.status = 'SHIPPED';
```
4. **Mention the exception.** `WHERE o.id IS NULL` after a LEFT JOIN is deliberate. It finds customers with no orders at all.

**Trade-offs and what can go wrong**
- For an INNER JOIN, `ON` and `WHERE` give the same result. The difference only appears with outer joins.
- A CROSS JOIN, or a forgotten join condition, multiplies rows. 10,000 customers × 50,000 products is 500 million rows, which can exhaust memory and slow the database for everyone.
- Joining on columns that contain NULLs loses those rows, because NULL is never equal to NULL.
- Duplicate keys on the right side multiply left rows, so counts and sums come out inflated.
- Unindexed join columns force slow full scans on big tables.

**How I'd monitor it**
- Compare row counts before and after a join. A LEFT JOIN must return at least as many rows as the left table has.
- Test with deliberately unmatched rows.
- Read the query plan with `EXPLAIN` to confirm the join columns are indexed and the row estimates look sane.
- Watch slow-query logs for sudden jumps in rows returned.

**Follow-ups to expect**
- *How do you find customers with no orders?* -> `LEFT JOIN orders ... WHERE orders.id IS NULL`.
- *Does `ON` versus `WHERE` matter for an INNER JOIN?* -> No, the result is the same. It only matters for outer joins.
- *How do you do a FULL OUTER JOIN in MySQL?* -> `UNION` a LEFT JOIN and a RIGHT JOIN.

**60-second answer**
A join combines rows from two tables using a matching rule. INNER returns only matches. LEFT returns every left row and fills the right side with NULL when nothing matches, and RIGHT is the mirror image. FULL OUTER keeps unmatched rows from both sides. CROSS pairs every row with every row, so I use it carefully because it explodes row counts. A self join just joins a table to itself under two aliases, for example employee to manager. The classic trap is filtering the right table in `WHERE` after a LEFT JOIN. NULL rows fail that test, so the query behaves like an INNER JOIN. I put that condition in the `ON` clause instead.

### Q2 [fresher] WHERE vs HAVING? GROUP BY rules?
tags: sql, where, having, group-by, aggregation, query-tuning, basics

**Start here: the concepts**
- **Row**: one record in a table, for example one order.
- **Aggregate function**: a function that collapses many rows into one value, such as `COUNT`, `SUM`, `AVG`, `MIN` or `MAX`.
- **GROUP BY**: puts rows that share the same value in the listed column(s) into one bucket (a "group"). Each group then produces one output row. It exists so you can ask per-customer, per-day or per-department questions.
- **WHERE**: a filter on individual rows. A row that fails it is dropped before any grouping happens.
- **HAVING**: a filter on whole groups. It runs after the aggregates are computed, so it can use `COUNT(*)`, `SUM(...)` and so on.
- **Logical order of evaluation**: the order in which the database conceptually processes each clause. The optimizer may physically do things differently, but the result must match this order.

**The live scenario**
A reporting query on an `orders` table (about 50 million rows) listed customers with more than 5 orders since 1 January. A junior developer grouped by `customer_id, order_date` and put the date test in `HAVING`. It took about 40 seconds and slowed the dashboard. Moving the date test to `WHERE` let the database use the index on `order_date`. It then grouped only about 1 million rows, and the query dropped to about 2 seconds. The numbers are illustrative, but the pattern is common.

**What the interviewer is really checking**
Whether you understand the order in which a query is evaluated, and so know which clause to use and why. Choosing the right one also affects performance.

**How I answer it**
1. **Row conditions go in `WHERE`.** It runs right after `FROM`, so it throws away rows early. Less data reaches grouping, and an index can often be used.
2. **Group conditions go in `HAVING`.** An aggregate such as `COUNT(*) > 5` does not exist until grouping is done, so `WHERE` cannot use it. Using an aggregate in `WHERE` gives an error.
3. **Non-aggregated selected columns must be in `GROUP BY`.** If you select `customer_id` and `COUNT(*)`, each group has many rows but only one `customer_id`, so that works. If you also select `order_date`, which differs inside a group, the database cannot choose one value, so it raises an error. Exception: PostgreSQL allows a column that is functionally dependent on a grouped primary key. MySQL can be configured to be lenient, but do not rely on that.
4. **Logical order:** `FROM` -> `WHERE` -> `GROUP BY` -> `HAVING` -> `SELECT` -> `DISTINCT` -> `ORDER BY` -> `LIMIT` / `FETCH FIRST` (`FETCH FIRST` is available in Oracle 12c+ and PostgreSQL). `SELECT` runs late, so in PostgreSQL and Oracle you cannot use a `SELECT` alias in `WHERE` or `HAVING`. You can use it in `ORDER BY`.

```sql
SELECT customer_id, COUNT(*) AS order_count
FROM orders
WHERE order_date >= DATE '2024-01-01'   -- row filter, before grouping
GROUP BY customer_id
HAVING COUNT(*) > 5;                    -- group filter, after grouping
```

**Trade-offs and what can go wrong**
- Putting a plain row condition in `HAVING` can return the same result but forces extra work. Some optimizers rewrite it, but do not count on that.
- `HAVING` can be used without `GROUP BY`. The whole result is then treated as one group.
- `COUNT(*)` counts all rows, while `COUNT(column)` skips NULLs. This changes `HAVING` results.
- A column in `GROUP BY` does not have to appear in `SELECT`, but the reverse is not allowed.
- NULLs form one group together.

**How I'd monitor it**
- Run `EXPLAIN` / `EXPLAIN ANALYZE` in PostgreSQL, or `EXPLAIN PLAN` with `DBMS_XPLAN` in Oracle. Check that the filter is applied at the scan (index or table access) and not after the aggregate step.
- Compare rows scanned with rows aggregated.
- Use `pg_stat_statements` or Oracle AWR to find slow grouped queries.
- Search the application slow-query logs in Splunk for long-running `GROUP BY` statements, and alert on a rising p95 duration.

**Follow-ups to expect**
- *Can I use `WHERE` and `HAVING` together?* -> Yes. `WHERE` filters rows first, then `HAVING` filters the resulting groups.
- *Why does selecting a column not in `GROUP BY` fail?* -> The group holds many different values and the database cannot pick one.
- *Can `HAVING` use a `SELECT` alias?* -> Not in PostgreSQL or Oracle, because `SELECT` is evaluated after `HAVING`. Repeat the expression instead.

**60-second answer**
`WHERE` filters individual rows before grouping. `HAVING` filters groups after aggregation, so it is the place for conditions like `COUNT(*) > 5`. Every non-aggregated column in `SELECT` must appear in `GROUP BY`, because each group produces only one output row. PostgreSQL makes an exception for columns that depend on a grouped primary key. The logical order is `FROM`, `WHERE`, `GROUP BY`, `HAVING`, `SELECT`, `ORDER BY`, then `LIMIT` or `FETCH`. I put row conditions in `WHERE` so less data is grouped and indexes can help. I check the execution plan to confirm that.

### Q3 [fresher] DELETE vs TRUNCATE vs DROP?
tags: sql, delete, truncate, drop, ddl, transactions, basics

**Start here: the concepts**
- **DML (Data Manipulation Language):** statements that change the rows inside a table, such as INSERT, UPDATE and DELETE. They are normally part of a transaction, so you can undo them.
- **DDL (Data Definition Language):** statements that change the structure of the database, such as CREATE, ALTER, DROP and (in Oracle) TRUNCATE. In Oracle, DDL commits automatically.
- **Transaction, commit, rollback:** a transaction is a group of changes treated as one unit. COMMIT makes them permanent. ROLLBACK cancels them. Databases exist to make this safe.
- **Redo/undo log:** before changing a row, the database records the old and new values. That record lets it roll back or recover after a crash. More changed rows means more log written.
- **Trigger:** code the database runs automatically when something happens, for example "after a row is deleted, write it to an audit table".
- **High-water mark (Oracle):** a marker showing how far into its storage a table has ever grown. Full table scans read up to this marker, even if most rows are gone.
- **Foreign key:** a rule saying a row in one table must point to an existing row in another. It stops you removing data that other data depends on.

**The live scenario**
A nightly batch loads a staging table with about 50 million rows. The job began with `DELETE FROM staging`. It ran for roughly 45 minutes, the undo/redo logs grew very large, and other sessions waited on locks. The next morning's reports were late. The team changed that one statement to `TRUNCATE TABLE staging` and it finished in seconds. Separately, a developer once ran DROP on the wrong table in a shared environment, which taught everyone why DDL needs care.

**What the interviewer is really checking**
Do you know these are three different tools (remove some rows, remove all rows quickly, remove the object) and can you explain the transaction and logging consequences? Do you know that rollback behaviour differs between databases?

**How I answer it**
1. **DELETE removes rows, and you choose which.** It is DML, so it accepts a WHERE clause. It works row by row, writes undo/redo for each row, and fires row-level triggers. Because of this, you can roll it back until you commit. The cost is that it is slow on large tables. In Oracle it also does not lower the high-water mark, so the space is not released.
2. **TRUNCATE removes all rows, and cannot take a WHERE.** It deallocates the table's storage instead of touching each row, so it is very fast and writes little log. In Oracle it resets the high-water mark and is DDL, so it commits automatically and cannot be rolled back. It does not fire DELETE triggers. It is usually refused on a table referenced by a foreign key (in Oracle you must disable or drop the constraint first). In PostgreSQL, TRUNCATE is transactional and can be rolled back inside a transaction, so never assume Oracle's behaviour everywhere.
3. **DROP removes the object itself.** The table definition, its data, indexes and constraints all go. It is DDL and auto-commits in Oracle. Oracle normally moves the dropped table to the recycle bin, so it can be recovered with `FLASHBACK TABLE ... TO BEFORE DROP` unless you used PURGE.
4. **Choose by intent:**
```sql
DELETE FROM orders WHERE status = 'CANCELLED';  -- some rows
TRUNCATE TABLE staging;                         -- all rows, keep table
DROP TABLE staging;                             -- table gone
```

**Trade-offs and what can go wrong**
- DELETE on millions of rows holds locks, bloats undo/redo, and can fail halfway. Delete in batches and commit between them.
- In Oracle, TRUNCATE cannot be undone. Running it on the wrong table or environment is permanent unless you have a backup.
- A TRUNCATE skips DELETE triggers, so audit logic you rely on will not run.
- DROP breaks anything that depends on the table, such as views, procedures and foreign keys.
- Do not claim "TRUNCATE is never rollbackable". That is true for Oracle but not for PostgreSQL.

**How I'd monitor it**
- Compare row counts before and after, and run the statement in a test environment first.
- Watch undo/redo usage and lock waits during large DELETEs. Use `pg_stat_activity` in PostgreSQL or `V$SESSION` and `V$TRANSACTION` in Oracle.
- Enable DDL auditing and restrict TRUNCATE and DROP privileges in production.
- Check backups and the Oracle recycle bin before any DROP.

**Follow-ups to expect**
- *Can you roll back a TRUNCATE?* -> Not in Oracle, because it auto-commits. In PostgreSQL, yes, when it is inside a transaction.
- *Why is TRUNCATE faster than DELETE?* -> It releases storage in one operation and does not log every row or fire row triggers.
- *How would you delete 20 million rows with a WHERE condition?* -> Delete in batches with commits in between, or copy the rows to keep into a new table and swap it in.

**60-second answer**
DELETE, TRUNCATE and DROP differ in what they remove. DELETE is DML. It removes rows one by one, can use a WHERE clause, writes undo/redo, fires triggers, and can be rolled back before commit. TRUNCATE removes all rows quickly by releasing storage. In Oracle it is DDL, commits automatically and resets the high-water mark, so it cannot be rolled back. PostgreSQL allows it inside a transaction. DROP removes the whole table with its data, indexes and constraints. I use DELETE for some rows, TRUNCATE to empty a table fast, and DROP when the table is no longer needed.

### Q4 [fresher] Primary key vs unique key vs foreign key; NULL behaviour?
tags: sql, primary-key, unique-key, foreign-key, null, constraints, oracle, basics

**Start here: the concepts**
- **Constraint:** a rule the database itself enforces on a table, so bad data is rejected no matter which application sends it.
- **Primary key (PK):** the column (or combination of columns) that identifies each row. It must be unique and can never be NULL. A table has at most one PK. It exists so every row has a reliable identity that other tables can point to.
- **Unique key:** a rule that no two rows may have the same value in the column(s). A table can have many. It protects business-unique things such as email or national ID that are not the main identity.
- **Foreign key (FK):** a column whose values must match an existing key in another (parent) table, usually its PK, or a unique key. This is **referential integrity**: you cannot create an order for a customer that does not exist. The FK column itself may hold NULL, meaning "no parent", unless it is declared NOT NULL.
- **NULL:** not a value, but a marker for "unknown or missing". It is not zero and not an empty string.
- **Three-valued logic:** comparisons with NULL give neither true nor false but UNKNOWN, and `WHERE` keeps only rows that are true. So `NULL = NULL` is UNKNOWN. You must write `IS NULL`.

**The live scenario**
A team moved a 50,000-row customer table from Oracle to PostgreSQL. A report, `WHERE middle_name IS NULL`, listed 12,000 customers on Oracle but 0 on PostgreSQL. In Oracle an empty string `''` is stored as NULL. PostgreSQL keeps `''` as a real value, so the migrated blanks were no longer NULL. The same migration also showed that a unique rule on an optional phone column behaves differently across databases. Nobody had learned how each database treats NULL and empty strings.

**What the interviewer is really checking**
Whether you know what each key guarantees, that NULL is "unknown" rather than a value, and that you know where databases differ, especially Oracle's empty-string behaviour.

**How I answer it**
1. **PK = unique + NOT NULL, one per table.** It can span several columns (composite). It gives each row one dependable identity, and the database automatically builds a unique index to enforce it.
2. **Unique key = no duplicates, but NULL is usually allowed, and the rules differ by database.** Oracle allows many NULLs in a single-column unique index. PostgreSQL also treats NULLs as distinct, so many are allowed. SQL Server allows only one NULL. In Oracle composite keys, rows that are entirely NULL are allowed many times, but a partly NULL pair with the same non-NULL part counts as a duplicate. The reason is that NULL means "unknown", so two unknowns cannot be proven equal. I say "check your database" instead of guessing.
3. **FK = child values must exist in the parent.** The database rejects inserts of orphan rows and deletes of parents that still have children. A NULL in the FK column passes, because "no parent" is not a broken reference.
4. **NULL comparisons: use `IS NULL` / `IS NOT NULL`.** `col = NULL` never matches anything, because the result is UNKNOWN. Related traps: `COUNT(col)` skips NULLs, and `NOT IN (subquery)` returns nothing if the subquery contains a NULL.
5. **Oracle trap: `''` is NULL.** `WHERE name = ''` never matches in Oracle, and `LENGTH('')` returns NULL. PostgreSQL and most other databases treat `''` as a real, empty value.

**Trade-offs and what can go wrong**
- Without an FK index, deleting a parent row can scan the whole child table. Oracle and PostgreSQL do not create FK indexes automatically. MySQL's InnoDB does.
- Choosing a big or changing PK (like email) makes every FK and index heavier. A stable surrogate ID is often better, with a unique key on the business value.
- Using NULL to mean several things ("unknown", "not applicable") makes queries ambiguous.
- Moving between Oracle and other databases silently changes the results of NULL and `''` checks.

**How I'd monitor it**
- Watch for constraint-violation errors. Oracle: ORA-00001 (unique), ORA-02291 (parent missing), ORA-02292 (child exists). PostgreSQL: SQLSTATE 23505, 23503, 23502. A Splunk search on these codes, charted over time, shows bad writes after a release.
- Run data-quality checks after migrations: compare `COUNT(*) WHERE col IS NULL` with `WHERE col = ''` on both sides.
- Use `EXPLAIN` on parent deletes to confirm the FK column is indexed.

**Follow-ups to expect**
- *Can a table have several unique keys and one PK?* -> Yes. One PK, any number of unique constraints, each backed by a unique index.
- *Can an FK point to a unique key rather than a PK?* -> Yes, if that unique key is on the parent column(s), though pointing to the PK is the norm.
- *Why does `NOT IN` return no rows when the list contains NULL?* -> `x <> NULL` is UNKNOWN, so no row can be proven "not in" the list. Use `NOT EXISTS` instead.

**60-second answer**
A primary key identifies each row: it is unique, not null, and there is one per table. A unique key also prevents duplicates, but a table can have several and NULL is usually allowed. How many NULLs are allowed depends on the database: Oracle and PostgreSQL allow many, while SQL Server allows one. A foreign key makes a column match a key in a parent table, so there are no orphan rows, and the FK column itself can be NULL. NULL means "unknown", so `NULL = NULL` is not true. You must write `IS NULL`. The classic Oracle trap is that an empty string is stored as NULL, which other databases do not do. I also index foreign key columns in Oracle and PostgreSQL, because they are not indexed automatically.

### Q5 [mid] How do indexes work and when do they not help?
tags: sql, indexes, b-tree, query-tuning, execution-plan, oracle, basics

**Start here: the concepts**
- **Index**: a separate, sorted lookup structure built on one or more columns. It exists so the database can find rows without reading the whole table, like a book's index versus reading every page.
- **B-tree index**: the default index type. It keeps keys in sorted order in a balanced tree, so finding a key takes a few steps (O(log n)) even with millions of rows. Because the keys are sorted, it is good at "equals" and "range" (`BETWEEN`, `>`, `<`) lookups.
- **Full table scan**: reading every row of the table. It is slow on big tables but can be the cheapest choice on small ones or when most rows are needed.
- **Selectivity**: the share of rows a condition filters out. `email = 'a@b.com'` returns about one row, so it is highly selective. `status = 'ACTIVE'` where 90% of rows are active is not selective.
- **Optimizer and statistics**: the optimizer is the part of the database that picks a plan. It relies on statistics, which are stored summaries of the data (row counts, value distribution). If the statistics are out of date, it can pick a bad plan.
- **Composite index**: one index on several columns, e.g. `(customer_id, created_at)`. It is sorted by the first column, then by the second within each first-column value.
- **Function-based index**: an index on an expression, e.g. `TRUNC(created_at)`, so that exact expression can be searched quickly.
- **Execution plan**: the database's step-by-step description of how it will run a query (`EXPLAIN` in PostgreSQL, `EXPLAIN PLAN` in Oracle).

**The live scenario**
An orders table has 50 million rows and an index on `created_at`. A daily report ran `WHERE TRUNC(created_at) = DATE '2024-05-01'` and took about 12 seconds. At peak it kept a lot of database CPU busy and slowed the checkout API. The index existed, but the plan showed a full table scan. Rewriting the filter as a range took it to about 20 ms.

**What the interviewer is really checking**
Whether you understand why an index helps (sorted structure) and can therefore predict when it is bypassed. They also want to see that you read execution plans instead of guessing.

**How I answer it**
1. **Explain the mechanism.** A B-tree keeps keys sorted, so the database walks down the tree to the start of the match instead of reading every row. This is why equality and range searches benefit.
2. **Don't wrap the indexed column in a function.** `TRUNC(created_at)` makes the database compute a new value for every row, and the index is sorted by the raw column, not the result. Instead, rewrite it as a range on the raw column, or create a function-based index on that exact expression.
```sql
WHERE created_at >= DATE '2024-05-01' AND created_at < DATE '2024-05-02'
```
3. **Avoid a leading wildcard.** `LIKE '%abc'` cannot use the sorted order, because the start of the value is unknown. `LIKE 'abc%'` can use the index. For "contains" searches, use a text-search feature (in PostgreSQL, a trigram index).
4. **Avoid implicit type conversion.** If a `VARCHAR` column is compared with a number, Oracle converts the column side for every row, which defeats the index. Make the literal or bind variable match the column type.
5. **Check selectivity.** If a condition matches a large share of the table, jumping between index and table for each row costs more than one sequential scan, so the optimizer rightly skips the index. There is no fixed percentage; it depends on the data and the plan.
6. **Keep statistics fresh.** With stale statistics the optimizer misjudges row counts and can ignore a good index. Re-gather statistics (Oracle `DBMS_STATS`, PostgreSQL `ANALYZE`).
7. **Respect the leftmost prefix.** An index on `(a, b)` is sorted by `a` first, so it serves `a`, or `a` and `b`, but normally not `b` alone. Oracle's skip scan can sometimes help, but only when `a` has few distinct values. Put equality columns first and the range column last.

**Trade-offs and what can go wrong**
- Every index costs disk space and slows `INSERT`, `UPDATE` and `DELETE`, because each index must be updated. Don't index everything.
- In Oracle, a single-column B-tree index does not store rows where the column is NULL, so `IS NULL` searches can't use it.
- Indexing a low-selectivity column such as a boolean or a status flag is rarely worth it.
- Forcing an index with hints can backfire when the data changes. Fix the query or the statistics first.

**How I'd monitor it**
- Read the execution plan: look for full scans on big tables, and compare estimated and actual row counts (`EXPLAIN ANALYZE` in PostgreSQL, `DBMS_XPLAN` in Oracle).
- Use the slow query log, AWR/`pg_stat_statements`, or Splunk searches on query duration to find the top offenders.
- Alert when statistics are stale and on sudden jumps in query time or CPU.
- Find unused indexes (`pg_stat_user_indexes`, Oracle index usage views) and drop them to save write cost.

**Follow-ups to expect**
- *Why does an index slow down writes?* -> Each insert or update must also change every index on the table, keeping them sorted.
- *What is a covering index?* -> An index that contains every column the query needs, so the database never visits the table.
- *Index on `(a, b)`: does `WHERE b = 5` use it?* -> Usually not efficiently, because it is sorted by `a` first. Oracle may use a skip scan if `a` has few distinct values.

**60-second answer**
An index is a separate sorted structure, usually a B-tree, so the database can find rows in a few steps instead of scanning the whole table. It works well for equality and range searches on selective columns. It stops helping when I wrap the column in a function like `TRUNC(date)`, so I rewrite it as a range or add a function-based index. It also fails with a leading wildcard `LIKE '%abc'`, an implicit type conversion, or a condition that matches a large share of rows, where a full scan is cheaper. Stale statistics can also mislead the optimizer. For composite indexes, order matters: the leftmost prefix must be in the filter. I always confirm with the execution plan rather than guessing, and I remember that every index slows writes.

### Q6 [mid] A query that was fast is now slow. What do you check?
tags: sql, query-tuning, execution-plan, indexes, oracle, postgresql, basics

**Start here: the concepts**
- **Execution plan:** the database's step-by-step recipe for running a query: which index or table scan to use, which join method, in what order. The same SQL can run very differently depending on the plan.
- **Optimizer and statistics:** the optimizer picks the plan by estimating row counts. Those estimates come from statistics, which are summaries of the data (row counts, value distribution). Stale or changed statistics lead to different plans.
- **Data skew:** values are unevenly spread. For example, 95% of orders have status `CLOSED` and 0.1% are `FAILED`. The best plan for one value is bad for the other.
- **Bind variable and peeking:** a bind variable is a placeholder (`WHERE status = ?`) that lets the database reuse one plan. In Oracle, "bind peeking" means the optimizer looks at the first value used to build the plan. If that value was unrepresentative, every later run inherits a poor plan. PostgreSQL has a similar effect: prepared statements can switch to a cached "generic" plan after several executions.
- **Index (missing or invalid):** a sorted lookup structure that avoids reading the whole table. An index can be missing, or exist but be unusable. In Oracle it can be `UNUSABLE`, and in PostgreSQL it can be `INVALID` after a failed `CREATE INDEX CONCURRENTLY`.
- **Lock wait:** a query is not slow, it is waiting for another transaction to release a row or table lock.
- **Implicit type conversion:** if you compare a column with a value of a different type, the database may convert the column side, and then it cannot use the index.
- **N+1:** an ORM runs one query for a list and then one more query per row, so one fast query becomes hundreds.

**The live scenario**
An order-search API had a p95 of 80 ms. After a Monday release, the p95 rose to 6 s and the connection pool saturated. The SQL text had not changed. Over the weekend, statistics were refreshed on a table that had grown from 20M to 30M rows. The optimizer switched from an index lookup to a full scan for a common customer ID. In the same release, a new screen triggered N+1 calls. Two causes were stacked, so fixing only one would not have helped.

**What the interviewer is really checking**
That you diagnose in a methodical order (what changed, then measure) rather than guessing "add an index", and that you know the plan is the main evidence.

**How I answer it**
1. **Ask what changed and when.** Look at deployments, statistics jobs, data loads and config changes. A clear start time narrows the causes quickly.
2. **Confirm it is the database.** Compare the app's timing with the database's own time for that statement. Slowness can come from the network, the pool or the app.
3. **Check for waiting before tuning.** If the session waits on locks, a plan fix won't help. Find the blocker, which is often a long-running transaction.
4. **Get the current plan and compare it with the old one.** In Oracle, use AWR (historical plans per SQL ID) or SQL Monitor for live executions. Both are licensed options, so check your licence. In PostgreSQL, `pg_stat_statements` shows which queries got slower (calls, mean time) but does not store plans. Use `EXPLAIN (ANALYZE, BUFFERS)` for the real plan and `auto_explain` to capture plans of slow runs.
5. **Look for a plan change.** Typical causes are new statistics, skew, or a bind value that produced a poor plan. Compare estimated rows with actual rows. A big gap points to bad statistics.
6. **Check indexes and types.** Confirm the index exists and is valid. Check that parameter types match column types so the index can be used.
7. **Consider growth and resources.** A table 50% bigger may push a query past the point where data fits in memory. Also check CPU, I/O, memory and connection limits.
8. **Look at call patterns.** If each query is still fast but there are many more of them, it is N+1. Fix it with a join fetch or batching.
9. **Fix the cause, then verify.** Options include refreshing statistics, adding histograms, pinning a plan, rewriting the query or adding an index.

**Trade-offs and what can go wrong**
- Re-gathering statistics can change other plans too, so test first.
- Forcing hints or plan baselines can freeze a plan that becomes wrong as data grows.
- A new index speeds reads but slows writes and uses space.
- Don't assume a single cause. In the scenario, both a plan change and N+1 were involved.
- Clearing the cache or restarting only hides the problem.

**How I'd monitor it**
- Per-query latency and call counts (`pg_stat_statements`, AWR top SQL).
- Plan hash changes per SQL ID, with an alert when a hot query's plan changes.
- Lock waits and long-running transactions.
- Statement counts per request in the app logs, to catch N+1.
- Splunk searches on slow-query logs, plus a dashboard of p95 by endpoint around deploy times.

**Follow-ups to expect**
- *Why can a query slow down with no code change?* -> Statistics, data volume or skew changed the plan, or the environment (locks, memory, I/O) changed.
- *How do you tell a lock wait from a bad plan?* -> A bad plan burns CPU or I/O. A lock wait shows low resource use and a wait event or blocked session.
- *How do you fix a bad bind-peeked plan?* -> Use histograms, adaptive features, or plan baselines. If needed, rewrite the query or split the hot value out.

**60-second answer**
First I ask what changed: a release, a statistics refresh, data growth or a load. Then I confirm the time is really spent in the database. I check for lock waits, because no plan fix helps a blocked query. Then I compare the current execution plan with the old one, using AWR or SQL Monitor in Oracle, or `pg_stat_statements` plus `EXPLAIN (ANALYZE, BUFFERS)` in Postgres. I look for new statistics, skew or bind-variable effects, and I check that indexes exist and are valid and that parameter types match the columns. I also check for N+1 from a new code path, and for resource limits. Then I fix the cause and add alerts on plan changes and query latency.

### Q7 [mid] Window functions - examples?
tags: sql, window-functions, rank, lead-lag, running-total, analytics, basics

**Start here: the concepts**
- **Window function:** a function that calculates a value for each row by looking at a related set of rows, without collapsing those rows. It exists because `GROUP BY` returns one row per group and loses the detail, and people often need both the detail and the group figure side by side.
- **`OVER (...)`:** the clause that makes a function a window function. It defines which rows each row can "see".
- **`PARTITION BY`:** splits rows into independent groups (here, one per department). It is like `GROUP BY` for the window, but rows are not merged. Without it, the whole result is one group.
- **`ORDER BY` inside `OVER`:** sets the row order within each partition. Ranking, previous/next and running totals depend on it. It is separate from the query's final `ORDER BY`.
- **`ROW_NUMBER`, `RANK`, `DENSE_RANK`:** all number rows in order. They differ only on ties (equal salaries):
  - `ROW_NUMBER` gives unique numbers: 1,2,3,4.
  - `RANK` gives ties the same number and then skips: 1,2,2,4.
  - `DENSE_RANK` gives ties the same number and does not skip: 1,2,2,3.
- **`LAG` / `LEAD`:** read a column from the previous (`LAG`) or next (`LEAD`) row in the window order. The first row for `LAG` (or last for `LEAD`) returns NULL.
- **Frame (`ROWS BETWEEN`):** the exact slice of the partition used for one row's calculation, for example "from the first row up to this row". It is what turns `SUM` into a running total.

**The live scenario**
A reporting service for a 20,000-employee company showed "top 3 earners per department" and "salary change versus previous hire". It did this by loading all rows into Java and looping, plus one query per department (about 60 extra queries). The page took 6 seconds. A senior engineer replaced all of it with one SQL query using window functions. The database sorted and partitioned once, the page dropped to well under a second, and the Java code shrank to a simple mapping.

**What the interviewer is really checking**
Whether you understand that window functions keep every row while adding group-aware values, and whether you can pick the right ranking function and frame. Mid-level candidates are often caught on tie behaviour and on "why can't I filter on `RANK` in `WHERE`".

**How I answer it**
1. **Start from the need.** If I want detail rows plus a group figure, I use a window function instead of `GROUP BY` plus a self-join. The reason is that it keeps the rows and is usually one pass over the data.
2. **Write the three classic patterns in one query:**
   ```sql
   SELECT emp_id, dept, salary,
     RANK() OVER (PARTITION BY dept ORDER BY salary DESC) AS rnk,
     salary - LAG(salary) OVER (PARTITION BY dept ORDER BY hire_date) AS diff,
     SUM(salary) OVER (PARTITION BY dept) AS dept_total
   FROM employees;
   ```
   `rnk` ranks salary within each department. `diff` is the salary minus the previous hire's salary in that department. `dept_total` repeats the department's total on every row.
3. **Choose the ranking function by tie rule.** For "top 3 people" where exactly 3 rows are needed, I use `ROW_NUMBER`. For "everyone in the top 3 salary levels", I use `DENSE_RANK`. `RANK` is right when the gaps are meaningful, as in sports.
4. **Use `LAG`/`LEAD` for row-to-row comparison.** They replace self-joins on "previous row", and the `ORDER BY` inside `OVER` defines what "previous" means. I handle the NULL on the first row with `COALESCE` or by accepting it.
5. **Use a frame for running totals.** `SUM(salary) OVER (PARTITION BY dept ORDER BY hire_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)` gives a cumulative sum. I state `ROWS` explicitly because the default frame when `ORDER BY` is present is `RANGE`, which treats ties as one group and can surprise you. Without `ORDER BY`, the default frame is the whole partition, which is why `dept_total` works.
6. **Filter in an outer query.** Window functions run after `WHERE`, so `WHERE rnk <= 3` fails. I wrap the query in a subquery or CTE and filter there.

**Trade-offs and what can go wrong**
- Each distinct `PARTITION BY`/`ORDER BY` combination can need its own sort. On large tables this uses memory or spills to disk.
- An index matching the partition and order columns can avoid the sort. I confirm that in the plan.
- Using `RANK` when you wanted exactly N rows returns more than N on ties.
- Forgetting that `LAG` returns NULL on the first row gives NULL results downstream.
- Mixing up the window's `ORDER BY` and the final `ORDER BY` returns rows in an unexpected order.
- Both Oracle and PostgreSQL support these functions. Neither has a `QUALIFY` clause, so the subquery pattern is needed.

**How I'd monitor it**
- Run `EXPLAIN (ANALYZE)` in PostgreSQL, or `EXPLAIN PLAN` in Oracle, and look for the WindowAgg and Sort steps, row estimates, and sorts spilling to disk.
- Check slow-query logs or `pg_stat_statements` / AWR for the query's time before and after.
- In Splunk, search the application's query-duration log field for the report endpoint and alert on a rising p95.

**Follow-ups to expect**
- *Difference between `GROUP BY` and a window function?* -> `GROUP BY` collapses rows into one per group. A window function keeps every row and adds a group-aware value.
- *How do you get the top 3 per department?* -> Compute `ROW_NUMBER()` (or `DENSE_RANK()`) partitioned by department in a subquery or CTE, then filter `rn <= 3` outside.
- *Why does `RANK` skip numbers?* -> After a tie, `RANK` jumps by the number of tied rows (1,2,2,4). `DENSE_RANK` does not skip (1,2,2,3).

**60-second answer**
A window function calculates a value per row while still returning every row, unlike `GROUP BY`. You add `OVER` with `PARTITION BY` to define groups and `ORDER BY` to define order inside them. `ROW_NUMBER` gives unique numbers, `RANK` gives ties the same number and then skips, and `DENSE_RANK` gives ties the same number without skipping. `LAG` and `LEAD` read the previous or next row, for example to compute salary change. `SUM() OVER (PARTITION BY dept)` gives a department total on every row, and adding `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW` gives a running total. I remember that you can't filter on a window result in `WHERE`, so I wrap the query in a subquery or CTE. On big tables I check the plan for sorts and add an index that matches the partition and order columns.

### Q8 [mid] Find the Nth highest salary / duplicates / delete duplicates.
tags: sql, window-functions, dense-rank, group-by, deduplication, unique-constraint, basics

**Start here: the concepts**
- **Window function:** a calculation that looks at related rows without collapsing them into one. `DENSE_RANK() OVER (ORDER BY salary DESC)` adds a rank column to every row and keeps all rows.
- **DENSE_RANK vs RANK vs ROW_NUMBER:** all three number rows in sorted order, but they treat ties differently. Take salaries 100, 100, 90.
  - `ROW_NUMBER` gives 1, 2, 3 and ignores ties.
  - `RANK` gives 1, 1, 3 and skips a number after a tie.
  - `DENSE_RANK` gives 1, 1, 2 and never skips. This is what "Nth highest salary" usually means.
- **GROUP BY:** squeezes rows that share a value (such as an email) into one group so you can count or aggregate them.
- **HAVING:** a filter applied after grouping. `WHERE` filters rows before grouping, so it cannot see `COUNT(*)`.
- **Duplicate:** here, two or more rows with the same business key (the email), even though their `id` values differ.
- **Subquery:** a query inside another query. A subquery in `FROM` needs an alias in PostgreSQL (Oracle does not insist).
- **Unique constraint:** a database rule that rejects a second row with the same value. It is the real fix for duplicates.

**The live scenario**
A signup form had a double-click bug and the `users` table (about 5 million rows) had no unique rule on `email`. About 12,000 customers had two or three rows, so the marketing tool sent them repeated emails and support tickets rose. Separately, the HR report asked for "the 3rd highest salary", and the first version used `ROW_NUMBER`. Two people tied for the top salary, so the report showed the wrong person. We found the duplicates, cleaned them safely, then added the constraint.

**What the interviewer is really checking**
Do you know the tie-handling difference between the ranking functions? Can you find duplicates with `GROUP BY ... HAVING`? Can you delete them without removing every copy? A mid-level candidate should also mention NULLs and preventing the problem.

**How I answer it**
1. **Nth highest:** use `DENSE_RANK` and filter on the rank. The reason is that salaries can tie, and "2nd highest" means the second distinct value. Change `2` to N. If fewer than N distinct salaries exist, you get no rows, which is correct.
2. **Find duplicates:** group by the business key and keep groups with more than one row. `WHERE` cannot filter on a count, so we use `HAVING`.
3. **Delete duplicates:** keep one row per group (the lowest `id`) and delete the rest. `MIN(id)` per email picks the survivor, and `NOT IN` removes everything else.
4. **Preview first:** run the same condition as a `SELECT` to see which rows would go, and take a backup.
5. **Prevent it:** add a unique constraint or index on `email`. Cleanup without it only fixes today's data.

```sql
SELECT salary FROM (SELECT salary, DENSE_RANK() OVER (ORDER BY salary DESC) r FROM emp) t WHERE r = 2;
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;
DELETE FROM users WHERE id NOT IN (SELECT MIN(id) FROM users GROUP BY email);
```

**Trade-offs and what can go wrong**
- `ROW_NUMBER` or `LIMIT 1 OFFSET n` without `DISTINCT` gives wrong answers when salaries tie.
- `GROUP BY` puts all NULL emails into one group. They show up as "duplicates" and the delete would remove all but one of them. Decide whether that is wanted.
- `NOT IN` returns nothing if the subquery produces a NULL. Here `MIN(id)` is safe only because `id` is never NULL.
- MySQL rejects deleting from a table while selecting from it in a subquery (error 1093). Wrap it in a derived table or use a join.
- A single huge delete holds locks for a long time and generates a lot of log. On big tables delete in batches.
- Emails differing only by case or trailing spaces are not caught. Normalise first, for example with `LOWER(TRIM(email))`.

**How I'd monitor it**
- After cleanup, re-run the duplicate query and expect zero rows.
- Check the plan with `EXPLAIN` (PostgreSQL) or `EXPLAIN PLAN` (Oracle). An index on `email` avoids a full table scan and sort.
- During a big delete, watch for blocked sessions (`pg_stat_activity` in PostgreSQL, `V$SESSION` in Oracle).
- In Splunk, alert on constraint errors (`duplicate key value violates unique constraint` in PostgreSQL, `ORA-00001` in Oracle). They show the app is still sending duplicates.

**Follow-ups to expect**
- *How would you find the Nth highest without window functions?* -> `SELECT DISTINCT salary ... ORDER BY salary DESC OFFSET N-1 ROWS FETCH FIRST 1 ROW ONLY` (Oracle 12c+ and PostgreSQL), or a correlated subquery that counts distinct higher salaries.
- *How else can you delete duplicates?* -> Number rows per email with `ROW_NUMBER() OVER (PARTITION BY email ORDER BY id)` and delete those with number above 1. In Oracle you can also compare `ROWID`.
- *How do you stop duplicates for good?* -> Add a unique index or constraint on `email`, and handle the violation in the application (for example return "already registered").

**60-second answer**
For the Nth highest salary I use `DENSE_RANK` over salary descending and filter where rank equals N. I choose it over `ROW_NUMBER` because ties would otherwise give the wrong person, and it counts distinct salaries. To find duplicates I group by the key, such as email, and use `HAVING COUNT(*) > 1`, because `WHERE` cannot filter on a count. To delete them I keep the lowest `id` per email and delete the rest with `NOT IN (SELECT MIN(id) ... GROUP BY email)`. I preview with a `SELECT` first, watch for NULL emails, and delete in batches on large tables. Then I add a unique constraint so the problem cannot come back.

### Q9 [mid] What are ACID and the isolation anomalies?
tags: acid, transactions, isolation-levels, mvcc, oracle, postgresql, basics

**Start here: the concepts**
- **Transaction:** a group of SQL statements treated as one unit of work, ending in COMMIT (keep it all) or ROLLBACK (undo it all). It exists so that "debit one account, credit another" cannot be half done.
- **Atomicity:** all or nothing. If anything fails midway, the database undoes the earlier steps.
- **Consistency:** a commit moves the database from one valid state to another. Rules such as primary keys, foreign keys, CHECK constraints and NOT NULL are never broken by committed data. The database enforces the declared rules, and your code must define the business rules correctly.
- **Isolation:** concurrent transactions should not see each other's half-finished work. Perfect isolation is slow, so databases offer levels that trade safety for speed.
- **Durability:** once COMMIT returns, the data survives a crash. The database writes a log (redo/WAL) to disk before it confirms.
- **Dirty read:** you read another transaction's uncommitted change, which may later be rolled back.
- **Non-repeatable read:** you read the same row twice in one transaction and get different values, because someone committed a change in between.
- **Phantom read:** you run the same query twice and the set of rows changes, because someone inserted or deleted matching rows.
- **Lost update:** two transactions read the same value, both change it, and the second write silently overwrites the first.
- **Write skew:** two transactions read overlapping data, each updates a *different* row based on what it read, and together they break a rule. Example: two doctors each go off-call because the other is still on call.
- **MVCC (multi-version concurrency control):** the database keeps older versions of changed rows, so a reader sees a consistent snapshot without locking. Oracle rebuilds old versions from **undo** data. PostgreSQL keeps old row versions in the table and cleans them up later with VACUUM.

**The live scenario**
A flash sale has 1 item left (stock = 1). Two requests arrive within 5 ms. Each runs `SELECT stock`, sees 1, and then `UPDATE stock = 0` and creates an order. Both commit, so 2 orders exist for 1 item. Each transaction was individually correct, but the interleaving was not. Support receives about 40 such complaints a day at peak. The fix was not "a bigger isolation level everywhere". It was a precise one: an atomic conditional update or a row lock.

**What the interviewer is really checking**
Whether you can name each anomaly with a concrete example, and whether you know that the defaults (READ COMMITTED) still allow lost updates and write skew, so you must choose a fix deliberately.

**How I answer it**
1. **Define ACID in one line each.** Atomicity is all or nothing, consistency is rules stay valid, isolation is concurrent work doesn't interfere, and durability is committed data survives a crash. This shows I know what each letter protects.
2. **Say isolation is the tunable one.** Atomicity and durability are always on. Isolation is a dial between correctness and concurrency, so that is where the anomalies live.
3. **Walk through the anomalies, from simplest to subtle.** Dirty read, non-repeatable read and phantom read are the three in the SQL standard. Lost update and write skew are not in the standard's list, but they occur in real systems, so I mention them.
4. **State the defaults.** Oracle and PostgreSQL both default to READ COMMITTED: each *statement* sees only data committed before that statement began. It prevents dirty reads. It still allows non-repeatable reads, phantoms, lost updates and write skew.
5. **Explain MVCC.** Readers read old versions, so readers don't block writers and writers don't block readers. Only two writers on the same row wait for each other. This is why Oracle and PostgreSQL scale well on mixed workloads.
6. **Name the stronger options precisely.** Oracle offers READ COMMITTED, SERIALIZABLE and READ ONLY. Oracle's SERIALIZABLE is snapshot isolation, which can still allow write skew. PostgreSQL has REPEATABLE READ (a snapshot per transaction), and its SERIALIZABLE detects dangerous patterns and aborts one transaction. PostgreSQL treats READ UNCOMMITTED as READ COMMITTED, so dirty reads never happen.
7. **Fix the scenario in the narrowest way.** Use an atomic update, or lock the row you read:
```sql
UPDATE item SET stock = stock - 1 WHERE id = 7 AND stock > 0;
```
Check the rows-updated count. If it is 0, the item sold out.

**Trade-offs and what can go wrong**
- Higher isolation means more waiting or more aborted transactions, so the code must be ready to retry (Oracle `ORA-08177`, PostgreSQL SQLSTATE `40001`).
- `SELECT ... FOR UPDATE` fixes lost updates but can cause lock waits and deadlocks if rows are locked in different orders.
- Long transactions hold locks and keep old versions alive. That means "snapshot too old" in Oracle, or table bloat in PostgreSQL.
- A common mistake is saying "SERIALIZABLE solves everything" without mentioning the retries, or claiming Oracle's SERIALIZABLE prevents write skew.

**How I'd monitor it**
- Oracle: `V$LOCK`, `V$SESSION` blocking_session, and AWR wait events such as `enq: TX - row lock contention`.
- PostgreSQL: `pg_stat_activity` (long `xact_start`), `pg_locks`, and `log_lock_waits`.
- Application: count deadlock and serialization-failure errors in Splunk and alert on spikes.
- Business check: a nightly query that finds negative stock or duplicate orders.

**Follow-ups to expect**
- *What is the difference between non-repeatable read and phantom read?* -> A non-repeatable read is the same row changing between reads. A phantom is the set of matching rows changing because of inserts or deletes.
- *How do you prevent lost updates under READ COMMITTED?* -> Use an atomic `SET x = x - 1`, `SELECT ... FOR UPDATE`, or optimistic locking with a version column.
- *What is a deadlock?* -> Two transactions each hold a lock the other needs. The database aborts one, and the fix is to lock in a consistent order and keep transactions short.

**60-second answer**
ACID means a transaction is atomic (all or nothing), consistent (constraints always hold), isolated (concurrent work doesn't interfere) and durable (committed data survives a crash). Isolation is the tunable part. The classic anomalies are dirty reads, non-repeatable reads and phantoms, and in practice we also worry about lost updates and write skew. Oracle and PostgreSQL both default to READ COMMITTED, where each statement sees only data committed before it started. That stops dirty reads but not lost updates, so for something like the last item in stock I use an atomic update or `FOR UPDATE`. Both databases use MVCC, so readers don't block writers. Oracle's SERIALIZABLE is really snapshot isolation and still allows write skew, whereas PostgreSQL's SERIALIZABLE detects it, at the cost of retries.

### Q10 [mid] Locks and deadlocks in a database?
tags: locks, deadlocks, transactions, oracle, postgresql, row-locking, basics

**Start here: the concepts**
- **Lock:** a marker the database puts on data so two sessions cannot change the same thing at once. Without locks, two concurrent updates could overwrite each other.
- **Row lock:** taken automatically on each row an `UPDATE`, `DELETE` or `SELECT ... FOR UPDATE` touches. It is held until `COMMIT` or `ROLLBACK`. Other sessions can still read the row in Oracle and PostgreSQL (they see the old committed version), but a second writer must wait.
- **Blocking:** session B waits because session A holds a lock. It is normal and usually brief. It becomes a problem when A holds the lock for a long time.
- **Deadlock:** A holds row 1 and wants row 2, while B holds row 2 and wants row 1. Neither can ever proceed. The database detects the cycle and kills one victim. Oracle raises `ORA-00060: deadlock detected` and rolls back only the victim's current statement, not the whole transaction. PostgreSQL aborts the whole transaction (SQLSTATE `40P01`).
- **`NOWAIT`:** `SELECT ... FOR UPDATE NOWAIT` fails immediately instead of waiting. Oracle raises `ORA-00054: resource busy`. PostgreSQL raises `55P03`.
- **Foreign key (FK):** a column that points to a row in another table, for example `order_item.order_id` points to `orders.id`.
- **`SKIP LOCKED`:** a `FOR UPDATE` option that silently skips rows other sessions have locked. It suits work queues. PostgreSQL has had it since 9.5, and Oracle supports it from 12c onward.

**The live scenario**
A payments service runs two batch jobs and a REST API on an `accounts` table. At month end, about 5 times a minute, API calls fail with `ORA-00060`. Job 1 updates accounts in ascending ID order. Job 2 processes a reversal file in whatever order it arrives. They collide on the same accounts in opposite orders. Separately, a 20-minute transaction that forgot to commit left 40 threads waiting and exhausted the connection pool.

**What the interviewer is really checking**
Whether you separate normal waiting from deadlock, know the cause of each, and have practical prevention habits. Mid-level candidates should also know how to diagnose a lock in production.

**How I answer it**
1. **Explain the default behaviour.** An update locks only the rows it changes, and the lock lasts until commit or rollback. This keeps data correct, but it means long transactions are expensive.
2. **Separate waiting from deadlock.** Waiting resolves itself when the holder commits. A deadlock is a cycle that cannot, so the database must break it by choosing a victim.
3. **Update rows in a consistent order**, for example always by ascending primary key. A cycle needs two sessions grabbing locks in opposite orders, so one agreed order makes the cycle impossible.
4. **Keep transactions short.** Do no remote calls or user waits between the first write and the commit. A lock is held only while the transaction is open, so shorter transactions mean fewer collisions.
5. **Index foreign keys.** Oracle does not escalate row locks to table locks. But if the child FK column has no index, deleting a parent row or changing its key forces Oracle to lock or scan the child table. That can block ordinary child inserts and updates. Later releases (11g onwards) softened the lock mode, but the full scan remains. An index lets Oracle find child rows directly.
6. **Use `SKIP LOCKED` for queues.** Workers claim different rows instead of queueing behind one another.
```sql
SELECT id FROM jobs WHERE status='NEW' FETCH FIRST 10 ROWS ONLY FOR UPDATE SKIP LOCKED;
```
7. **Handle the victim.** Catch the deadlock error and retry the transaction a limited number of times.

**Trade-offs and what can go wrong**
- Consistent ordering is hard when the order comes from external input. You may need to sort the keys first.
- `SKIP LOCKED` gives an inconsistent view by design. It is fine for queues and wrong for reports.
- Blind retries can multiply load. Use a retry limit and backoff.
- Extra FK indexes cost write speed and space, so index the FKs that the parent delete/update paths actually use.
- Do not "fix" blocking by lowering safeguards. Add a timeout (`NOWAIT`, `lock_timeout` in PostgreSQL) so waits fail visibly.

**How I'd monitor it**
- Oracle: `V$SESSION` (`blocking_session`, `event` like `enq: TX - row lock contention`) and the alert log and trace files written on each `ORA-00060`.
- PostgreSQL: `pg_stat_activity` and `pg_locks`, plus `log_lock_waits` and `deadlock_timeout`.
- Application logs: search Splunk for `ORA-00060` or `40P01`, and alert on the count per minute.
- Track the age of the oldest open transaction and connection pool wait time.

**Follow-ups to expect**
- *Does a deadlock roll back my whole transaction?* -> In Oracle only the failing statement is rolled back, and you should still roll back or retry. In PostgreSQL the whole transaction is aborted.
- *Do readers block writers?* -> Not in Oracle or PostgreSQL. They use MVCC (multi-version concurrency control), so readers see an older committed version.
- *How do you find who is blocking?* -> Query `V$SESSION.blocking_session` in Oracle or `pg_blocking_pids()` in PostgreSQL, then find that session's SQL and transaction age.

**60-second answer**
A database locks the rows you change until you commit, so a second writer waits. Waiting is normal. A deadlock is two sessions each holding a row the other needs, so the database kills one, giving `ORA-00060` in Oracle. To prevent deadlocks I update rows in the same order everywhere and keep transactions short, with no slow calls inside them. I index foreign keys, because in Oracle an unindexed FK makes parent deletes lock or scan the child table. Oracle doesn't escalate locks, but that still blocks child writes. For work queues I use `FOR UPDATE SKIP LOCKED` so workers don't queue behind each other. I retry the deadlock victim a few times and watch blocking sessions and deadlock errors in the logs.

### Q11 [mid] Normalization vs denormalization?
tags: normalization, denormalization, 3nf, oltp, materialized-view, sql, basics

**Start here: the concepts**
- **Normalization:** organising tables so each fact is stored in exactly one place. Customer details live in a `customer` table, and orders point to them by an ID (a foreign key). It exists so that changing a fact means changing one row.
- **Update anomaly:** a bug caused by storing the same fact in many rows. If a customer's address is copied into 40 order rows and you update only 39, the data now contradicts itself. Related problems are insert anomalies (you can't record a customer without an order) and delete anomalies (deleting the last order erases the customer).
- **Third Normal Form (3NF):** a common normalization target. Every column should describe the key of its row, and nothing but the key. A column like `customer_city` in an orders table breaks this, because it describes the customer, not the order.
- **OLTP (online transaction processing):** workloads with many small, concurrent reads and writes, such as placing orders or updating balances. Correctness of each write matters most.
- **Denormalization:** deliberately duplicating or pre-combining data to make reads faster, because it avoids joins (combining tables at query time).
- **Summary table / materialized view:** a stored copy of a query's result. A summary table is one you maintain yourself, and a materialized view is one the database stores for you. Both must be refreshed when the source data changes. In PostgreSQL, a materialized view is refreshed manually or on a schedule. Oracle can also refresh on commit or incrementally.
- **Reporting/analytics (OLAP):** large read-heavy queries that scan and aggregate many rows.

**The live scenario**
An order system stored `customer_address` in every order row, about 5 million rows. When customers moved, a batch job updated only recent orders. Support then saw two addresses for one customer, and a shipment went to the old one. The team normalized the address into a `customer` table.

Later, the finance dashboard joined 6 tables over about 200 million rows and took roughly 40 seconds. The team added a nightly summary table of daily revenue per product, and the dashboard dropped to about 50 ms. The first problem was caused by too much duplication, and the second was fixed by adding some on purpose.

**What the interviewer is really checking**
Whether you treat this as a trade-off rather than a rule. They want to see that you start normalized, denormalize only for a measured read problem, and know how you'd keep the copy correct.

**How I answer it**
1. **Define normalization and its goal.** Store each fact once (to 3NF). That way an update touches one row and the data can't contradict itself.
2. **Default to normalized for OLTP.** Writes are frequent and correctness matters. Joins on indexed foreign keys are usually cheap, so the cost of normalizing is small.
3. **Measure before denormalizing.** Check the query plan and the indexes first. Often a missing index is the real problem, not the schema.
4. **Denormalize deliberately for a specific read path.** Reporting and dashboards read far more than they write, and joins over huge tables are costly. Use a summary table or materialized view rather than polluting the core tables.
5. **Decide how the copy stays in sync.** Options are a scheduled refresh, a refresh on commit, a trigger, or application code. State how stale the data may be.
6. **Keep the normalized tables as the source of truth.** You can rebuild the denormalized copy from them at any time.

```sql
CREATE MATERIALIZED VIEW daily_revenue AS
SELECT order_date, product_id, SUM(amount) AS revenue
FROM orders GROUP BY order_date, product_id;  -- PostgreSQL: REFRESH MATERIALIZED VIEW daily_revenue;
```

**Trade-offs and what can go wrong**
- Denormalized data costs extra storage, slower writes, and more code to keep it in sync.
- Stale data can mislead users, so agree on an acceptable delay.
- Copies that are updated by several code paths drift apart. This is the same anomaly you normalized away.
- Over-normalizing into many tiny tables makes every query a long join.
- Denormalizing too early, before measuring, adds complexity without a proven benefit.

**How I'd monitor it**
- Slow-query logs and execution plans (`EXPLAIN ANALYZE` in PostgreSQL, `EXPLAIN PLAN` in Oracle) to prove a join is the bottleneck.
- Refresh duration and last-refresh time of each materialized view or summary job, with an alert if it fails or runs late.
- A periodic reconciliation query comparing summary totals to the source tables.
- In Splunk, a search on slow-query or job-failure logs, with an alert when refresh jobs error.

**Follow-ups to expect**
- *When would you denormalize?* -> When a measured, read-heavy query is too slow even with good indexes, and some staleness is acceptable.
- *How do you keep denormalized data consistent?* -> Refresh on a schedule or on commit, use triggers, or write through one code path. Reconcile regularly against the source tables.
- *Is a data warehouse normalized?* -> Usually not. Star schemas deliberately denormalize into fact and dimension tables for fast analytical reads.

**60-second answer**
Normalization means storing each fact once, usually to 3NF, so an update changes one row and the data can't contradict itself. That's why I use it by default for OLTP systems, where there are many small writes and correctness matters. Denormalization means deliberately duplicating or pre-computing data, like a summary table or materialized view, so reads avoid expensive joins. I only do it after checking the plan and indexes and finding a real read bottleneck, usually in reporting. The cost is redundancy, slower writes, and the need to keep the copy in sync, so I decide the refresh method and acceptable staleness up front. I keep the normalized tables as the source of truth and reconcile the copy against them.

### Q12 [mid] Oracle-specific: sequences, `ROWNUM`, `MERGE`, `DUAL`, partitioning?
tags: oracle, sequences, rownum, merge, dual, partitioning, plsql, basics

**Start here: the concepts**
- **Sequence**: a database object that hands out increasing numbers. `my_seq.NEXTVAL` gives the next one. It exists so many sessions can get unique ids at the same time without locking a table. Numbers can have gaps (rollbacks, cache loss), so never rely on gap-free ids.
- **Identity column (12c+)**: `GENERATED ALWAYS AS IDENTITY` on a column. Oracle creates and uses a sequence behind the scenes, so you don't write `NEXTVAL` yourself.
- **ROWNUM**: a pseudo-column that numbers rows in the order Oracle fetches them, *before* `ORDER BY` sorts them. So `WHERE ROWNUM <= 10 ORDER BY x` takes 10 arbitrary rows, then sorts those.
- **FETCH FIRST n ROWS ONLY (12c+)**: the standard way to say "top n after sorting".
- **MERGE**: one statement that updates a row if it exists (`WHEN MATCHED`) or inserts it if not (`WHEN NOT MATCHED`). This is an "upsert".
- **DUAL**: a built-in table with one row and one column. Oracle's `SELECT` traditionally needs a `FROM`, so `SELECT my_seq.NEXTVAL FROM DUAL` or `SELECT SYSDATE FROM DUAL` uses it as a stand-in. (Oracle 23ai allows `SELECT` without `FROM`.)
- **Partitioning**: splitting one big table into smaller physical pieces by a rule: range (dates), list (regions) or hash (even spread). To the application it is still one table. It is a separately licensed option of Enterprise Edition.
- **Partition pruning**: the optimizer skips partitions that cannot contain matching rows.
- **PL/SQL**: Oracle's procedural language inside the database. Packages group related code. `BULK COLLECT` and `FORALL` process rows in batches.

**The live scenario**
An orders table has 400 million rows. A dashboard query, `WHERE ROWNUM <= 10 ORDER BY created_at DESC`, showed "latest orders" that were months old, because Oracle picked 10 rows first and sorted only those. The nightly load did a select-then-insert-or-update loop, 2 million rows, row by row, and took 3 hours. Replacing it with one `MERGE` took minutes. Reports on one month were still scanning everything until the table was range-partitioned by month.

**What the interviewer is really checking**
Whether you know Oracle's well-known traps (`ROWNUM` ordering, sequence gaps) and the right tools for bulk work and big tables, not just generic SQL.

**How I answer it**
1. **Ids:** use a sequence, or an identity column on 12c+. Sequences avoid table locks, and `CACHE` makes them fast. The price is that gaps are normal.
2. **Top-n:** use `FETCH FIRST n ROWS ONLY` on 12c+. Before 12c, sort in a subquery and apply `ROWNUM` in the outer query. Reason: `ROWNUM` is assigned before the sort.
3. **Upsert:** use `MERGE` for one set-based statement instead of a loop. It is faster and avoids the race of "check, then insert".
4. **DUAL:** use it when you need a value but have no table, e.g. `SELECT my_seq.NEXTVAL FROM DUAL`.
5. **Partitioning:** pick the key your queries filter on, usually a date. Then pruning reads only the relevant partitions. Archiving becomes `DROP` or `EXCHANGE PARTITION`, which is far cheaper than a huge `DELETE`.
6. **PL/SQL:** use packages for organisation and `BULK COLLECT` with `FORALL` to cut the round trips between the PL/SQL and SQL engines. Handle errors in `EXCEPTION` blocks.

```sql
SELECT * FROM orders ORDER BY created_at DESC FETCH FIRST 10 ROWS ONLY;
```

**Trade-offs and what can go wrong**
- `ROWNUM > 1` or `ROWNUM = 2` return nothing, because the first row is never accepted.
- Sequence gaps after rollbacks or restarts. A large `CACHE` is faster but loses more numbers on a crash. Don't use sequences for gap-free invoice numbers.
- `MERGE` fails with ORA-30926 if the source has duplicate rows for one target row. It also cannot update columns used in its `ON` condition.
- Partitioning needs a licence, and a wrong key gives no benefit. Global indexes can become unusable after partition maintenance unless you maintain them.
- `FORALL` on millions of rows can exhaust memory. Use `BULK COLLECT ... LIMIT`.

**How I'd monitor it**
- Read plans with `DBMS_XPLAN.DISPLAY_CURSOR`. Look for `PARTITION RANGE SINGLE` or a small Pstart/Pstop range to confirm pruning.
- Check AWR or ASH for sequence contention waits.
- Search Splunk for `ORA-30926`, `ORA-00001` (duplicate key) and slow batch durations.
- Watch partition sizes and the job that creates future partitions. A missing one causes insert errors.

**Follow-ups to expect**
- *Why might a sequence skip numbers?* -> Rollbacks don't return values, and cached values are lost on restart or flush. Uniqueness is guaranteed, continuity is not.
- *Difference between local and global index on a partitioned table?* -> A local index is split the same way as the table, so partition maintenance is easy. A global index spans all partitions and may need rebuilding after maintenance.
- *Why use BULK COLLECT and FORALL?* -> They fetch and write many rows per call, which avoids a context switch per row.

**60-second answer**
"In Oracle I use sequences, or identity columns from 12c, for ids, and I accept gaps. `ROWNUM` is assigned before `ORDER BY`, so for top-n I use `FETCH FIRST n ROWS ONLY` on 12c+, or sort in a subquery first. `MERGE` is the upsert: one statement that updates matching rows and inserts the rest, which beats a row-by-row loop, though duplicate source rows cause ORA-30926. `DUAL` is the one-row table I select from when I need a value, like `NEXTVAL`. For very large tables I use partitioning, usually by date, so queries skip irrelevant partitions and archiving is a partition drop. It is a licensed option and I check the plan to confirm pruning. In PL/SQL I use packages, and `BULK COLLECT` with `FORALL` for batch work."

### Q13 [senior] How do you handle a table with 500 million rows?
tags: sql, large tables, partitioning, indexing, keyset pagination, query tuning, basics

**Start here: the concepts**
- **Partitioning:** one logical table is split into smaller physical pieces, usually by date range or key hash. If a query filters on the partition key, the database reads only the matching pieces (*partition pruning*). Old pieces can also be removed cheaply.
- **Index:** a sorted lookup structure, like a book's index. It avoids reading every row, but every insert and update must also maintain it, so each extra index slows writes and uses disk.
- **Covering index:** an index that contains every column a query needs, so the database never visits the table. PostgreSQL 11+ supports `INCLUDE` columns for this. Index-only scans there also depend on vacuum keeping the visibility map current.
- **`SELECT *`:** fetches every column. It wastes I/O and network, and it blocks covering indexes.
- **Batch delete:** deleting in small chunks. One huge delete holds locks, generates huge undo/redo (Oracle) or WAL (PostgreSQL) logs, and leaves dead rows.
- **Archiving:** moving old, rarely read rows to cheaper storage so the hot table stays small.
- **Parallel query:** one query is split across several CPU workers. It is useful for big scans and aggregates.
- **Materialized view:** a stored, precomputed query result (e.g. daily totals). Reads are fast, but the data is only as fresh as the last refresh.
- **Keyset pagination:** "give me the next page after the last row I saw", instead of `OFFSET`, which makes the database read and discard all the skipped rows.
- **Warehouse/lakehouse:** a separate system built for analytics, so heavy reports don't compete with transactions.

**The live scenario**
An orders table has grown to 500M rows (about 400 GB). Checkout lookups are fine, but the nightly report takes 3 hours. The "orders page 40,000" API call takes 8 seconds. A cleanup job running `DELETE ... WHERE created < now() - 2 years` for 50M rows blocked writers for 40 minutes and filled the log disk. The team needed to keep checkout under 50 ms while handling all three problems.

**What the interviewer is really checking**
Whether you treat a big table as a set of access patterns to design for, not a size problem. They also want to see that you know the operational risks: long transactions, index bloat and heavy reports on the primary.

**How I answer it**
1. **Start from the queries.** I list the top queries and read their plans (`EXPLAIN ANALYZE`). Size alone is not the problem; full scans are.
2. **Partition by the column most queries filter on, usually date.** Pruning shrinks the work per query. The filter must include the partition key or every partition is scanned. In PostgreSQL, unique keys must include the partition key. In Oracle, partitioning is a separately licensed option.
3. **Index only what queries need.** Each index costs write time and space, so I drop unused ones. For hot queries I add covering indexes, so the table is never touched.
4. **Never `SELECT *`.** Selecting only the needed columns reduces I/O and allows index-only reads.
5. **Archive and delete in a controlled way.** With date partitions, I detach or drop an old partition, which is near-instant and creates no dead rows. Otherwise I delete in batches (say 10k rows per commit) with a pause between them, so locks stay short and logs stay small.
6. **Use keyset pagination for large lists.** The cost stays flat however deep the page is, and it needs an index on the sort columns:
```sql
WHERE (created, id) < (:lastCreated, :lastId) ORDER BY created DESC, id DESC LIMIT 50
```
7. **Keep reporting off the OLTP path.** Parallel query speeds up scans, and materialized views precompute aggregates. I run both on a read replica where possible. When analytics grows beyond that, I move it to a warehouse or lakehouse.

**Trade-offs and what can go wrong**
- Partitioning adds operational work: creating future partitions, and queries without the key scan everything.
- Too many partitions slow planning.
- Extra indexes slow inserts, and index maintenance gets slower on huge tables.
- Materialized views go stale, and refreshes cost resources. In PostgreSQL, `REFRESH ... CONCURRENTLY` needs a unique index.
- Parallel queries can consume CPU needed by OLTP.
- Keyset pagination can't jump to an arbitrary page, and it needs a unique tie-breaker column.
- Archiving needs a plan for how to query the archived data.

**How I'd monitor it**
- Slow-query logs and `pg_stat_statements` (PostgreSQL), or AWR/ASH (Oracle).
- Plans showing partitions scanned, and index usage stats to find unused indexes.
- Table and index size growth, and bloat or dead-row counts with autovacuum lag.
- Lock waits, long-running transactions, and WAL/redo volume during batch jobs.
- Replica lag, and p95/p99 latency alerts. In Splunk, I'd search for slow-query log entries by query hash.

**Follow-ups to expect**
- *Why not just add more indexes?* -> Each one slows writes and uses space, and the optimizer may ignore it. I add indexes only for proven queries.
- *Why is OFFSET slow?* -> The database reads and discards all skipped rows, so deep pages cost more and more.
- *Is partitioning a replacement for indexing?* -> No. It narrows which data is read, while indexes find rows inside it. They work together.

**60-second answer**
I start with the access patterns and the query plans, because a big table is only a problem if queries scan it. I partition by the column most queries filter on, usually date, so queries touch only the relevant slices and old data can be dropped instantly. I keep only the indexes real queries need, add covering indexes for hot paths, and never use `SELECT *`. For deletes I drop partitions or delete in small batches so there are no long locks or giant logs. I use keyset pagination instead of OFFSET. Reports run on a replica with parallel query or materialized views, and heavy analytics moves to a warehouse. I watch slow queries, index usage, bloat and lock waits to prove it works.

### Q14 [senior] Optimistic locking and idempotent upsert patterns in SQL?
tags: sql, optimistic-locking, idempotency, upsert, postgresql, oracle, basics

**Start here: the concepts**
- **Lost update:** two users read the same row, both change it, and the second save silently overwrites the first. Locking exists to prevent this.
- **Pessimistic locking:** lock the row when you read it (`SELECT ... FOR UPDATE`) so nobody else can change it. It is safe but makes others wait.
- **Optimistic locking:** assume conflicts are rare. Don't lock on read. Instead, detect a conflict at write time and let the loser retry or report an error.
- **Version column:** a number stored on each row that goes up by 1 on every update. If the version you read is no longer the version in the table, someone else changed the row.
- **Idempotent:** doing the operation twice has the same effect as doing it once. This matters because retries, redelivered Kafka messages and double-clicks all repeat requests.
- **Unique constraint:** a database rule that rejects a second row with the same key. It is the one place where two concurrent requests are forced to agree.
- **Upsert:** "insert, or if it already exists, update or skip." Postgres uses `INSERT ... ON CONFLICT`. Oracle uses `MERGE`.

**The live scenario**
A payments service consumes about 2,000 events/s from Kafka. Kafka delivers at-least-once, so after a consumer rebalance about 0.5% of events arrive twice. The code did "SELECT, then INSERT if missing", so two consumers could both see "missing" and both insert. Customers were credited twice, and about 300 duplicate rows a day needed manual cleanup. Separately, two support agents edited the same account and one agent's change vanished. The fix was a unique key on `event_id` for the events and a version column for edits.

**What the interviewer is really checking**
Whether you know that "check, then write" is a race condition, and that the fix is to make the database enforce the rule atomically. They also want to see that you handle the failure case (retry, or treat it as a duplicate) and not just the happy path.

**How I answer it**
1. **Optimistic lock with a version column.** Read the row with its version, then write only if the version is unchanged. The reason is that the `WHERE` clause and the update happen as one atomic statement, so no one can slip in between.
   ```sql
   UPDATE t SET ..., version = version + 1 WHERE id = ? AND version = ?;
   -- idempotent insert (Postgres):
   INSERT INTO events (event_id, ...) VALUES (?, ...) ON CONFLICT (event_id) DO NOTHING;
   ```
2. **Check the affected-row count.** Zero rows updated means a conflict: the version moved, or the row is gone. The application must then reload and retry, or return HTTP 409. Ignoring the count defeats the whole pattern.
3. **Idempotent insert via a unique key.** Put a unique constraint on a stable business identifier such as `event_id`, not a generated one. `ON CONFLICT (event_id) DO NOTHING` (Postgres 9.5+) skips the duplicate silently, and a count of 0 tells you it was a duplicate.
4. **Oracle.** Use `MERGE` (Postgres 15+ also has it), or just insert and catch `ORA-00001` (unique constraint violated), then treat it as "already processed." Two concurrent `MERGE` statements can still both try to insert, and one fails with ORA-00001. So keep the unique constraint and handle that error.
5. **Use `DO UPDATE` when you want a true upsert.** `DO NOTHING` means the first writer wins. If the latest value should win, use `DO UPDATE`, ideally with a version or timestamp guard.

**Trade-offs and what can go wrong**
- Optimistic locking is cheap when conflicts are rare. Under heavy contention on a hot row, retries pile up and pessimistic locking or a queue is better.
- Every writer must include the version check. One code path that skips it breaks the guarantee.
- Without the unique constraint, `ON CONFLICT` has nothing to detect, and "SELECT then INSERT" stays racy.
- Retries need a limit and backoff, or they cause a retry storm.
- An idempotent insert only protects that one table. Side effects such as emails or payments need their own idempotency key.

**How I'd monitor it**
- Count optimistic-lock failures (zero-row updates) and duplicate skips per minute. A sudden rise means contention or a rebalance storm.
- Track the retry count and the HTTP 409 rate.
- In Splunk, search for `ORA-00001` or "duplicate key" and alert on spikes.
- Run a nightly query: `GROUP BY event_id HAVING COUNT(*) > 1` should return nothing.

**Follow-ups to expect**
- *Optimistic or pessimistic locking?* -> Optimistic when conflicts are rare and holding locks is costly. Pessimistic when conflicts are frequent and a retry is expensive.
- *Can you use a timestamp instead of a version number?* -> Yes, but a counter is safer. Timestamps can collide or lose precision.
- *Is `MERGE` safe under concurrency?* -> Not on its own. Concurrent inserts can still collide, so keep the unique constraint and handle ORA-00001.

**60-second answer**
Optimistic locking means I don't lock rows when I read. I keep a version column and update with `WHERE id = ? AND version = ?`, setting `version = version + 1`. If zero rows were updated, someone else got there first, so I reload and retry or return a conflict. For idempotent inserts, I put a unique constraint on a stable event ID. In Postgres I use `INSERT ... ON CONFLICT (event_id) DO NOTHING`. In Oracle I use `MERGE`, or I insert and catch ORA-00001. The point is that the database enforces the rule atomically, which "SELECT then INSERT" cannot do. I monitor conflict and duplicate rates, and I cap retries.

### Q15 [senior] Bind variables vs literals and SQL injection?
tags: sql, bind-variables, prepared-statement, sql-injection, query-performance, jdbc, basics

**Start here: the concepts**
- **Literal:** a value written directly into the SQL text, e.g. `WHERE customer_id = 4711`. Each different value makes a different SQL string.
- **Bind variable (parameter):** a placeholder such as `?` or `:id` in the SQL text. The value is sent separately, so the SQL text stays identical for every call.
- **Parsing:** before running a statement, the database checks the syntax and permissions and builds an execution plan (the step-by-step recipe for reading the data). A **hard parse** builds the plan from scratch, which is expensive. A **soft parse** finds an already-built plan in cache and reuses it, which is cheap.
- **Plan cache:** memory where the database keeps parsed statements, matched by their exact text. Different literals mean different text, so no cache hit. Oracle calls this the shared pool.
- **SQL injection:** an attacker types SQL syntax into an input field, and the application glues it into the query, so the database runs it as code, not as data.
- **PreparedStatement:** the JDBC object that sends the SQL text with placeholders first and the values separately. The values are never parsed as SQL, so they cannot change the query's structure.
- **Whitelist:** a fixed list of allowed values that the code checks input against.

**The live scenario**
An order-search service handles about 2,000 requests/s. A developer built the query with string concatenation: `"... WHERE customer_id = " + id`. Within hours the plan cache filled with hundreds of thousands of near-identical statements. Database CPU hit 90% on parsing alone, and p99 latency went from about 80 ms to about 2 s. A week later a security scan sent `1 OR 1=1` and got back every customer's orders. Switching to bind variables fixed both problems. CPU dropped sharply because plans were reused, and the injection stopped working.

**What the interviewer is really checking**
Do you know that binds solve two separate problems (performance and security), where binds cannot be used (identifiers like column names), and that binds have a plan-quality side effect on skewed data?

**How I answer it**
1. **Never concatenate user input into SQL. Use `PreparedStatement` or named parameters (JPA, Spring `NamedParameterJdbcTemplate`).** The database receives the structure and the values separately, so input like `' OR '1'='1` is treated as a plain string value.
2. **Explain the performance benefit.** The SQL text is identical on every call, so the database soft-parses and reuses the cached plan instead of hard-parsing each time. This saves CPU and plan-cache memory.
3. **Know the limit: binds only replace values, not identifiers or keywords.** You cannot bind a table name, a column name or `ASC`/`DESC`. Dynamic `ORDER BY` therefore needs a whitelist that maps the request value to a known column:
```java
String col = ALLOWED.getOrDefault(sortParam, "created_at"); // never use sortParam directly
```
4. **Mention the plan trade-off.** One shared plan may not suit every value. If 99% of rows have `status='DONE'` and 1% have `'FAILED'`, the best plan differs between the two. Oracle handles this with bind peeking and adaptive cursor sharing. PostgreSQL may switch a prepared statement to a generic plan after several executions (controllable with `plan_cache_mode` from version 12).
5. **Be precise about what a PreparedStatement guarantees.** It protects you only if the values are really bound. `prepareStatement("... " + userInput)` is still injectable.

**Trade-offs and what can go wrong**
- Concatenating into a "prepared" statement gives a false sense of safety.
- Skewed data plus a shared plan can cause occasional slow queries. Fix with histograms, adaptive cursor sharing, or deliberately using a literal for a few low-cardinality, stable values.
- Dynamic `IN` lists need one placeholder per element, and varying list lengths create many distinct statements. Pad lists to fixed sizes.
- Least privilege on the DB account limits damage even if injection slips through. Binds do not replace it.

**How I'd monitor it**
- Oracle: hard parses per second in AWR, and `v$sql` grouped by `FORCE_MATCHING_SIGNATURE` to find many statements that differ only by literal.
- PostgreSQL: `pg_stat_statements` normalizes literals, so you can see whether query volume is sane.
- Splunk: search application logs for SQL syntax errors and unusual quote or `--` patterns in request parameters, and alert on spikes.
- Code review and static analysis rules that flag SQL built with `+` or `String.format`.

**Follow-ups to expect**
- *Can a PreparedStatement still be vulnerable?* -> Yes, if you concatenate input into the SQL string before preparing it, or put unvalidated input into an identifier.
- *How do you handle a dynamic ORDER BY or column list?* -> Map the request value to a fixed list of known columns and directions, and default if there is no match.
- *Why can binds cause a bad plan?* -> The plan is built for the first value seen, which may be unrepresentative on skewed data. Use adaptive cursor sharing (Oracle), `plan_cache_mode` (PostgreSQL 12+) or histograms.

**60-second answer**
A literal is a value written into the SQL text, and a bind variable is a placeholder whose value is sent separately. Binds help in two ways. The SQL text stays identical, so the database reuses the cached plan instead of hard-parsing every call. And user input is treated only as data, so it can never change the query's structure, which stops SQL injection. So I never concatenate input and always use `PreparedStatement` or named parameters. Binds only work for values, not column or table names, so a dynamic `ORDER BY` goes through a whitelist. The one trade-off is that a shared plan may not suit skewed data, which Oracle and PostgreSQL have features to handle. I'd watch hard-parse rates and near-duplicate statements in the database, and suspicious input patterns in Splunk.

### Q16 [senior] How do you do online schema change on a big table?
tags: sql, postgresql, oracle, schema-migration, locking, indexes, expand-contract, basics

**Start here: the concepts**
- **Schema change (DDL):** a statement such as `ALTER TABLE` or `CREATE INDEX` that changes the table's structure, not its rows.
- **Online schema change:** changing the structure while the application keeps reading and writing. The aim is no outage.
- **Lock:** a "do not touch" flag the database puts on a table or row. A DDL statement often needs a strong lock that blocks every other query on that table.
- **Lock queue:** if a DDL waits for a strong lock behind a long-running transaction, every new query queues behind the DDL. A change that "should take milliseconds" can freeze the table.
- **Metadata-only change:** the database edits only its catalog and does not rewrite the rows. Adding a nullable column with no default is usually this, so it is fast on any table size. Adding a column with a default is also metadata-only in Postgres 11+ (constant defaults) and in recent Oracle versions. Older versions rewrite the whole table.
- **Backfill:** filling the new column for existing rows. Done in one huge `UPDATE`, it holds locks, bloats the log and causes replica lag. So it is done in small batches.
- **Concurrent/online index build:** the index is built while writes continue. Postgres uses `CREATE INDEX CONCURRENTLY`, Oracle uses `CREATE INDEX ... ONLINE`. Both are slower than a normal build but do not block writes.
- **Expand/contract:** a pattern with two phases. Expand: add the new structure alongside the old one. Contract: remove the old structure once nothing uses it.

**The live scenario**
`orders` has 400 million rows and takes about 3,000 writes per second. We need to split `status` into a new `status_v2` column and index it. A teammate runs a plain `ALTER TABLE` with a default and a normal `CREATE INDEX` at 2 pm. The index build blocks writes for 20 minutes, checkout fails, and the connection pool fills with waiting sessions. The retry makes things worse. The same change done online causes no visible impact.

**What the interviewer is really checking**
Whether you know that the dangers are lock queues and long transactions, not just "big table = slow", and whether you can split a change into small, reversible, safe steps.

**How I answer it**
1. **Rehearse on a production-sized copy.** Run the exact script and time each step, because plans and durations on a small table mislead.
2. **Expand: add the column as nullable, with no heavy default.** This is metadata-only, so it is cheap. Even so, it needs a brief strong lock, so set a short lock timeout and retry rather than queue behind a long transaction:
   ```sql
   SET lock_timeout = '3s';
   ALTER TABLE orders ADD COLUMN status_v2 text;
   ```
3. **Deploy code that writes to both old and new columns.** New rows stay correct while old rows are backfilled.
4. **Backfill in small batches.** Use ranges of a few thousand rows by primary key, commit each batch, and pause between batches. Short transactions keep locks brief, limit log growth and let replicas keep up.
5. **Build the index online.** Use `CREATE INDEX CONCURRENTLY idx_orders_status ON orders(status_v2);` in Postgres, or `ONLINE` in Oracle. This avoids blocking writes. In Postgres it cannot run inside a transaction block, and a failed build leaves an `INVALID` index that you must drop and retry.
6. **Add constraints safely.** In Postgres, add a `CHECK` or foreign key as `NOT VALID`, then run `VALIDATE CONSTRAINT`, which does not block writes. Set `NOT NULL` only after the backfill.
7. **Switch reads to the new column, then contract.** Once the old column is unused for a release or two, drop it. Each step can be rolled back until this last one.
8. **Pick a quiet period, but don't rely on it.** A low-traffic window reduces risk and does not replace the steps above. For changes that need a table rewrite, consider Oracle `DBMS_REDEFINITION` or Postgres `pg_repack`.

**Trade-offs and what can go wrong**
- Expand/contract takes several releases and temporarily doubles the writes.
- Concurrent index builds take longer and use more I/O.
- A forgotten open transaction can stall the DDL and everything behind it.
- Batch backfills can still saturate I/O or cause replica lag if batches are too large.
- Dropping the old column too early removes your rollback path.

**How I'd monitor it**
- Lock waits and blocked sessions: `pg_stat_activity` and `pg_locks` in Postgres, `v$session` in Oracle.
- Index build progress: `pg_stat_progress_create_index`.
- Replica lag, transaction log growth, and p99 latency and error rate on the service.
- Splunk searches for lock-timeout or deadlock errors during the change window.
- Alerts that pause the backfill automatically when lag or latency passes a threshold.

**Follow-ups to expect**
- *Why is adding a column sometimes dangerous even when it is "instant"?* -> It needs a brief strong lock. If a long transaction holds the table, the DDL waits and blocks all new queries behind it, so use `lock_timeout` and retry.
- *What if `CREATE INDEX CONCURRENTLY` fails?* -> It leaves an `INVALID` index that still slows writes. Drop it and rebuild.
- *How do you handle a change that must rewrite the table?* -> Create a new table, sync it by triggers or a tool, and swap. Tools include `pg_repack` and Oracle `DBMS_REDEFINITION`.

**60-second answer**
I never run a big change as one blocking statement. First I rehearse it on a production-sized copy. Then I follow expand/contract: add a nullable column, which is metadata-only, with a short lock timeout so it can't queue behind a long transaction. I deploy code that writes both columns, backfill old rows in small committed batches, and build the index online with `CREATE INDEX CONCURRENTLY` in Postgres or `ONLINE` in Oracle. Only when the old column is unused do I drop it. A quiet window helps, but the safety comes from short locks, small batches and reversible steps. I watch lock waits, replica lag and latency throughout.

### Q17 [senior] Backup, recovery and replication basics you should know?
tags: backup, recovery, replication, rpo-rto, postgresql, oracle, basics

**Start here: the concepts**
- **Backup:** a copy of the data that you can restore after a disaster, a bad deploy or a human error. It exists because disks fail, people run wrong `DELETE`s, and whole data centres go down.
- **RPO (Recovery Point Objective):** how much recent data the business can afford to lose, measured in time. RPO of 5 minutes means that after a failure, at most the last 5 minutes of writes may be gone.
- **RTO (Recovery Time Objective):** how long the system may be down before it must be working again.
- **WAL / redo log:** the database first writes every change to a sequential log, then to the data files. Postgres calls it the WAL (write-ahead log); Oracle calls it redo. Replaying this log rebuilds changes made after a backup.
- **WAL archiving and PITR (point-in-time recovery):** you keep a base backup plus a continuous stream of archived log files. To recover, you restore the base backup and replay the log up to a chosen moment, such as 10:41, just before someone dropped a table.
- **RMAN:** Oracle's built-in backup and restore tool. It takes full and incremental backups and checks block integrity.
- **Replica / standby:** a second server that continuously applies the primary's log. *Streaming replication* (Postgres) ships log records live. *Data Guard* is Oracle's standby system. Replicas exist for fast failover and for read scaling.
- **Multi-AZ failover (AWS RDS/Aurora):** the database keeps a standby in another availability zone (a separate data centre). If the primary dies, AWS promotes the standby and repoints the DNS name. Open connections break, so clients must reconnect.

**The live scenario**
A payments service ran on Postgres with a nightly backup and a streaming replica. At 14:05 a release ran a migration script with a wrong `WHERE` clause and wiped 2 million rows from a table. The replica had copied the damage within a second. The team had no WAL archive, so the best they could do was last night's backup, which meant about 14 hours of lost payments. Later, a restore drill showed that the backup also took 6 hours to restore, far beyond the 1-hour RTO the business had assumed.

**What the interviewer is really checking**
That you start from business targets (RPO/RTO) rather than tools, that you know replication is not backup, and that you have actually restored a database, not just configured backups.

**How I answer it**
1. **Ask for RPO and RTO first.** They decide the design and the cost. A 24-hour RPO needs only nightly backups. A near-zero RPO needs log shipping or synchronous replication.
2. **Take base backups plus continuous log archiving.** In Oracle, use RMAN backups with archived redo. In Postgres, use a base backup plus WAL archiving. A backup alone recovers only to the backup time. With logs you can recover to any minute (PITR).
3. **Add a standby for fast failover.** Use Data Guard in Oracle or a streaming replica in Postgres. Replication is asynchronous by default, so a crash can lose the last few transactions. Synchronous mode closes that gap but makes commits wait for the standby.
4. **Never treat the replica as the backup.** A bad `DELETE` or `DROP TABLE` replicates instantly. Only backups with PITR undo human error.
5. **On managed services, use automated backups and Multi-AZ.** RDS/Aurora automated backups give PITR within the retention window. Multi-AZ failover is typically quoted at about 30-60 seconds for Aurora; standard RDS Multi-AZ can take longer, around 1-2 minutes, so check current AWS documentation. Either way, the application needs a connection pool that reconnects and retries, or failover turns into an outage.
6. **Test the restore regularly.** A backup is real only if a restore has been tested. Restore into a scratch environment, time it against the RTO, and verify the data.

**Trade-offs and what can go wrong**
- Tighter RPO/RTO costs more: extra servers, storage, network, and slower commits with synchronous replication.
- Untested backups can be corrupt, incomplete, or missing a log segment, which breaks PITR.
- Backups stored in the same account or region as production are lost together with it.
- Apps that cache DNS or never rebuild their connection pool stay down after a failover.
- Restore time grows with data size, so RTO that was fine at 100 GB may not hold at 5 TB.

**How I'd monitor it**
- Last successful backup age, plus alerts on backup job failures (RMAN logs, `pg_stat_archiver` for failed archive counts).
- Replication lag in seconds and bytes (`pg_stat_replication` in Postgres, the Data Guard lag views in Oracle). Alert when lag exceeds the RPO.
- WAL archive gaps and disk usage on the archive location.
- Scheduled restore drills with measured duration, recorded against the RTO.
- Failover game-days: watch application error rates and reconnect time in logs and dashboards.

**Follow-ups to expect**
- *Is a replica a backup?* -> No. It copies mistakes and corruption immediately. You still need backups with PITR.
- *How do you recover from an accidental `DROP TABLE` at 14:05?* -> Restore the last base backup to a separate server, replay the logs to 14:04, then export the table and load it back.
- *Synchronous versus asynchronous replication?* -> Synchronous waits for the standby, so RPO is near zero but commits are slower. Asynchronous is faster but can lose the last transactions on failover.

**60-second answer**
I start with RPO and RTO, meaning how much data loss and downtime the business accepts, because they drive the design and cost. For recovery I use base backups plus continuous log archiving: RMAN in Oracle, WAL archiving with PITR in Postgres, and automated backups on RDS or Aurora. For fast failover I add a standby, such as Data Guard, a streaming replica, or Multi-AZ. Failover takes roughly a minute or so, and applications must reconnect. Replication is not backup, because a bad delete replicates instantly, so I need PITR for human error. Most important, a backup only counts once I have tested a restore and timed it against the RTO.

### Q18 [architect] Design the schema for a multi-tenant SaaS (e.g. ERP).
tags: multi-tenancy, schema-design, row-level-security, postgresql, hibernate, data-isolation, basics

**Start here: the concepts**
- **Multi-tenant SaaS:** one software product serves many customer companies (tenants). Each tenant must see only its own data, yet you don't want to run a separate copy of the system per customer.
- **Shared tables with `tenant_id`:** every table has a `tenant_id` column, and all tenants' rows live together. It is the cheapest model because there is one schema to run and migrate.
- **Schema-per-tenant:** one database, but each tenant gets its own set of tables (a schema, i.e. a namespace). Isolation is better, but a change to the table design must be rolled out N times.
- **Database-per-tenant:** each tenant gets its own database. This gives the strongest isolation and per-tenant backup, restore and tuning, but costs the most to run.
- **Row-level security (RLS):** the database itself adds a hidden filter to every query, so a forgotten `WHERE tenant_id = ...` in app code cannot leak data. PostgreSQL has RLS, and Oracle has a similar feature called VPD.
- **Hibernate filter:** an ORM-level filter that appends the tenant condition to queries. It lives in the application, so anything that bypasses the ORM (native SQL, reports, scripts) bypasses it too.
- **Tenant-leading index:** a composite index that starts with `tenant_id`, such as `(tenant_id, created_at)`. Almost every query is "this tenant's rows", so the index narrows to one tenant first.
- **Noisy neighbour:** one heavy tenant slows everyone who shares the same resources.

**The live scenario**
An ERP vendor has 800 small tenants and 5 large ones, and signs a bank that demands its data be isolated. In the shared-table design, a developer writes a native SQL report and forgets the tenant filter. In staging, tenant A's invoice totals include tenant B's rows. Separately, one large tenant runs a month-end job that scans 40 million rows, and p95 latency for all tenants goes from 120 ms to 2 s. The team needed leak protection that does not depend on developer discipline, and a way to move big or regulated tenants out.

**What the interviewer is really checking**
Whether you pick the model from tenant count, compliance and operations cost rather than by habit. They also want to see that you enforce isolation in the database and test for leaks, not just trust application code.

**How I answer it**
1. **Ask first:** how many tenants, how big is the largest, and what do compliance and contracts require? These answers decide the model.
2. **Default to shared tables with `tenant_id`** for many small tenants. It costs the least and a single migration covers everyone.
3. **Put `tenant_id` first in indexes and in keys.** Use `(tenant_id, id)` as the primary key, and put `tenant_id` in unique constraints and foreign keys. This keeps queries fast, and the database refuses a row in tenant A that points to a row in tenant B.
4. **Enforce the filter centrally, in two layers.** The application layer (a Hibernate filter or tenant support) is convenient. The database layer (RLS) is the safety net, because it also covers native SQL:
```sql
ALTER TABLE invoice ENABLE ROW LEVEL SECURITY;
CREATE POLICY t ON invoice USING (tenant_id = current_setting('app.tenant_id')::bigint);
-- per transaction: SET LOCAL app.tenant_id = '42';
```
5. **Handle connection pools carefully.** Pooled connections are reused across tenants. Set the tenant per transaction (`SET LOCAL`) so it is cleared automatically. Otherwise tenant A's setting can leak into tenant B's request.
6. **Use schema-per-tenant** for moderate tenant counts that need better isolation or per-tenant restore. Accept that migrations must be automated and run N times.
7. **Use database-per-tenant** for large or regulated tenants, accepting the cost. In practice, go hybrid: shared pool by default, dedicated database for premium or regulated customers, with a tenant-to-database routing table.
8. **Test for leaks.** Automated tests create two tenants, run every endpoint as one, and assert none of the other's data appears.

**Trade-offs and what can go wrong**
- Shared tables carry noisy-neighbour risk, and one bad query or a missing filter affects everyone. Restoring a single tenant from backup is hard.
- RLS is bypassed by superusers and table owners unless you use `FORCE ROW LEVEL SECURITY` and a non-owner application role. It also adds some planning overhead.
- Schema-per-tenant with thousands of tenants strains the catalog and slows migrations. Database-per-tenant multiplies connections, patching and cost.
- Skewed data (one huge tenant) can make the query planner choose poor plans for small tenants.

**How I'd monitor it**
- Per-tenant query latency, rows scanned and connection usage (tag logs and metrics with tenant id), to spot noisy neighbours.
- Slow-query log or `pg_stat_statements`, checking that plans use the tenant-leading index.
- Alerts on queries that touch a tenant-scoped table without a tenant predicate.
- Splunk search for tenant-id mismatches between the request context and the data returned.
- Migration success per tenant (schema model), and the scheduled cross-tenant leak test.

**Follow-ups to expect**
- *How do you move a big tenant out of the shared database?* -> Copy its rows by `tenant_id` into a dedicated database, sync changes, then switch the routing table and delete the old rows.
- *Hibernate filter or RLS?* -> Use both. The filter is convenient, while RLS is the safety net that covers native SQL and other tools.
- *How do you run migrations in schema-per-tenant?* -> Use a tool like Flyway or Liquibase looped over all tenants, with versions tracked per tenant and rollout in batches.

**60-second answer**
I choose by tenant count, isolation needs and operating cost. For many small tenants I use shared tables with a `tenant_id` column, with `tenant_id` first in indexes, primary keys and foreign keys. For moderate numbers with stronger isolation needs I use schema-per-tenant, and for large or regulated customers a database each, often as a hybrid with a routing table. The tenant filter must never depend on developers remembering it. I apply it centrally through the ORM and back it with database row-level security, setting the tenant per transaction so pooled connections don't leak. I run automated cross-tenant leak tests and monitor per-tenant latency to catch noisy neighbours.

### Q19 [architect] Design reporting on a busy OLTP database without slowing it.
tags: sql, oltp, reporting, read-replica, cdc, materialized-view, resource-limits, basics

**Start here: the concepts**
- **OLTP (online transaction processing):** the database behind the live application. It handles many small, fast reads and writes, such as placing an order, and users wait on each one.
- **Reporting/analytics query:** a query that scans millions of rows to group and total them. It uses a lot of CPU, I/O and memory, and it competes with OLTP work for the same resources.
- **Read replica / standby:** a second copy of the database, kept current by replaying the primary's change log. Reports run on the copy, so the primary is not touched. In Oracle, a standby you can query while it applies changes needs Active Data Guard, a separately licensed option. In PostgreSQL it is called a hot standby.
- **Replication lag:** the delay between a change on the primary and its appearance on the replica. Reports on a replica are slightly stale.
- **Summary table / materialized view:** a table holding pre-computed results, such as daily sales per region, so a dashboard reads a few hundred rows instead of scanning millions. *Incremental refresh* updates only what changed instead of recomputing everything. Oracle can do this with materialized view logs (fast refresh). PostgreSQL's built-in `REFRESH MATERIALIZED VIEW` recomputes everything, so incremental summaries there are usually built by your own job or by a stream processor.
- **CDC (change data capture):** reading the database's change log and streaming each insert, update and delete to another system, usually a **data warehouse**. A warehouse is a database built for large analytical scans. It also keeps history, which OLTP does not.
- **Resource Manager:** an Oracle feature that assigns sessions to groups and caps each group's CPU, parallelism and runtime. A runaway report cannot starve checkout.

**The live scenario**
An e-commerce primary handles about 2,000 transactions per second, with checkout p95 at 80 ms. At month-end, finance runs a 10-minute "revenue by category" query on the primary. CPU hits 95%, the buffer cache is flushed of hot pages, and checkout p95 rises to 2 s. Timeouts cause retries and abandoned carts. The fix was not a bigger primary. We separated reporting workloads from the transactional path. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you treat reporting as a separate workload with its own architecture, rather than "add an index", and whether you understand the costs: staleness, replica conflicts and operational complexity.

**How I answer it**
1. **Classify the reports by freshness need.** Ask who reads each report and how stale it may be. Real-time operational views, hourly dashboards and month-end analytics need different solutions, and the cheapest one that meets the need wins.
2. **Move ad-hoc and heavy queries to a read replica or standby.** This removes the CPU and I/O contention from the primary. It is the fastest win, but the replica has the same schema and is still row-oriented.
3. **Pre-compute common dashboards into summary tables or materialized views, refreshed incrementally.** Most dashboard queries are the same few aggregations. Computing them once and reading many times is far cheaper than re-scanning raw rows.
4. **For heavy analytics, stream changes by CDC to a warehouse.** The warehouse can be modelled and scaled independently, holds history, and can join data from several systems. The OLTP schema stays untouched.
5. **Cache dashboard results** for a short TTL (time to live). Fifty people opening the same dashboard should cost one query, not fifty.
6. **Put guardrails on whatever still touches the primary or replica.** Set query timeouts and resource limits (Oracle Resource Manager, or in PostgreSQL a role-level setting):
```sql
ALTER ROLE reporting_user SET statement_timeout = '60s';
```
   Guardrails ensure that one bad query cannot hurt everyone.
7. **Schedule heavy batch jobs off-peak.** This is a supporting measure only. Global businesses may have no quiet window, so it never replaces isolation.

**Trade-offs and what can go wrong**
- Replica data is stale. Never use it for read-after-write logic, such as "show the order I just placed".
- On a PostgreSQL hot standby, long queries can conflict with replay of changes. You then either cancel the query or let lag grow (`max_standby_streaming_delay`, `hot_standby_feedback`). The feedback setting can cause bloat on the primary.
- Incremental summaries can drift from the source if a job fails. Plan reconciliation checks.
- CDC adds infrastructure and schema-change coordination, and needs a team to run it.
- Caching can show wrong numbers if invalidation is sloppy.
- Common mistake: pointing BI tools at the primary "just for now".

**How I'd monitor it**
- Primary: CPU, active sessions, p95/p99 transaction latency, buffer cache hit ratio, and lock waits.
- Replica: replication lag in seconds, with an alert when it passes the freshness promise, plus count of cancelled queries.
- Resource Manager and timeouts: queries killed or throttled per consumer group.
- CDC pipeline: consumer lag and row-count reconciliation against the source.
- Splunk: search slow-query logs by user or application to catch reports that appear on the primary.

**Follow-ups to expect**
- *Why not just add indexes for the report?* -> Indexes help selective lookups, but aggregations scan most rows anyway. Each index also slows every OLTP write.
- *How do you handle a report that needs real-time data?* -> Make it a narrow, indexed query on the primary, or use a replica with a lag alert. Do not run a wide aggregation on live data.
- *Replica vs warehouse?* -> A replica is quick, same schema, and fine for moderate reports. A warehouse suits large history, multi-source joins, and heavy scans.

**60-second answer**
I treat reporting as a different workload from OLTP, so I first ask how fresh each report must be. Heavy ad-hoc queries go to a read replica or standby, so they cannot compete with transactions. Common dashboards use summary tables or materialized views refreshed incrementally, with short-lived caching on top. For serious analytics I stream changes through CDC into a warehouse. Whatever still touches the database gets timeouts and resource limits, such as Oracle Resource Manager, and batch jobs run off-peak. I watch replica lag and primary latency, because the costs of this design are stale data and extra moving parts.
