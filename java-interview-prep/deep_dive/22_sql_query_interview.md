# SQL query interview: ranking, window functions, optimisation, NULL traps and locking

> **Runnable (32 self-checking assertions, SQLite, stdlib only):**
> [`01_sql_interview_queries_sqlite.py`](../examples/22_sql_queries/01_sql_interview_queries_sqlite.py)
> (`py 01_sql_interview_queries_sqlite.py`; every query below that has a check is marked **[run]**)
> **Related:** [09 Spring Data JPA](09_spring_data_jpa.md) (isolation, N+1, locking) ·
> [`topics/10-sql-oracle.md`](../topics/10-sql-oracle.md) (crib sheet) · [13 NoSQL](13_nosql.md)

## What interviewers are actually probing

For an experienced candidate the SELECT/JOIN basics are assumed. The round checks four things:

1. **Can you express a business question as set logic?** Top N *per group*, gaps and islands,
   month-over-month, "who never did X". These almost always need a window function or an anti-join.
2. **Do you know the traps?** Ties (`ROW_NUMBER` vs `RANK` vs `DENSE_RANK`), `NOT IN` with a `NULL`,
   `COUNT(*)` vs `COUNT(col)`, `ROWS` vs `RANGE` frames, a function wrapped around an indexed column.
3. **Can you read an execution plan** and say why a query is slow, then fix it with an index or rewrite
   rather than guessing?
4. **Do you understand concurrency?** Isolation levels, locking order, deadlock handling, MVCC.

The format that scores best: *restate the requirement, ask about ties and NULLs, write the query, state
the complexity / index it needs, name one edge case.*

## Must-know points

- **Logical order of evaluation:** `FROM/JOIN -> WHERE -> GROUP BY -> HAVING -> window functions ->
  SELECT -> DISTINCT -> ORDER BY -> LIMIT`. This is why you cannot filter on a window function in the
  same `WHERE`: wrap it in a subquery or CTE.
- **`WHERE` filters rows before grouping, `HAVING` filters groups after.**
- **Ranking functions:**

  | Function | Ties (92.5, 92.5, 88) | Gaps after ties? |
  |---|---|---|
  | `ROW_NUMBER()` | 1, 2, 3 (arbitrary among ties unless you add a tiebreaker) | no |
  | `RANK()` | 1, 1, 3 | yes |
  | `DENSE_RANK()` | 1, 1, 2 | no |

- **`NULL` is not a value:** `= NULL` is never true, `NULL <> x` is unknown, `NOT IN` against a list that
  contains `NULL` returns **no rows**, aggregates skip `NULL`, `COUNT(*)` counts rows while `COUNT(col)`
  counts non-null values.
- **Join types:** `INNER`, `LEFT/RIGHT/FULL OUTER`, `CROSS`, self join, anti-join (`LEFT JOIN ... IS NULL`
  or `NOT EXISTS`), semi-join (`EXISTS`).
- **A predicate is SARGable** (Search ARGument able) when the engine can seek an index with it:
  `col >= x`, `col = x`, `col LIKE 'abc%'`. Wrapping the column in a function, casting it, or a leading
  wildcard defeats the index.

## Interview questions and full answers

### Q1. Find the top 3 students by percentage. (the ties follow-up decides the answer)

Ask first: *"Top 3 rows, or top 3 distinct percentages? What happens if two students tie for third?"*

```sql
-- exactly 3 rows; ties are cut arbitrarily unless you add a tiebreaker      [run]
SELECT name, percentage
FROM   students
ORDER  BY percentage DESC, name
LIMIT  3;                                   -- SQL Server: SELECT TOP 3 ...   Oracle 12c+: FETCH FIRST 3 ROWS ONLY

-- top 3 percentages, keeping everybody who ties for a place                 [run]
SELECT name, percentage
FROM  (SELECT name, percentage,
              DENSE_RANK() OVER (ORDER BY percentage DESC) AS r
       FROM students) t
WHERE  r <= 3;
```

With the sample data (Farah 95, Asha 92.5, Chen 92.5, Bala 88) the first query returns `Farah, Asha, Chen`
and silently drops Bala only because of the `LIMIT`; the `DENSE_RANK` version returns four students
because the top three *distinct* percentages are 95, 92.5 and 88. Both are correct; the requirement
decides. `LIMIT` is cheaper (it can stop early with an index on `percentage`).

### Q2. Find the top 3 students in each category. (the classic)

```sql
SELECT category, name, percentage, rn
FROM  (SELECT category, name, percentage,
              ROW_NUMBER() OVER (PARTITION BY category
                                 ORDER BY percentage DESC, name) AS rn
       FROM students) t
WHERE  rn <= 3
ORDER  BY category, rn;                      -- [run]: exactly 3 rows per category
```

- `PARTITION BY` restarts the numbering for each category; `ORDER BY` inside `OVER` defines the rank.
- Choose the function by the tie rule: `ROW_NUMBER` = exactly N rows; `RANK` / `DENSE_RANK` = include ties.
- It must be a subquery or CTE because window functions cannot appear in `WHERE`.
- **Oracle / PostgreSQL alternative:** `FETCH FIRST 3 ROWS WITH TIES` per group via `LATERAL` / `CROSS APPLY`.
- **No window functions available (old MySQL 5.7):** count how many rows in the same category beat this
  one; keep rows where that count is below 3. It is O(n^2) per category but portable. **[run]**

```sql
SELECT s.category, s.name
FROM   students s
WHERE (SELECT COUNT(DISTINCT x.percentage) FROM students x
       WHERE x.category = s.category AND x.percentage > s.percentage) < 3;
```

Index to support it: `(category, percentage DESC)`.

### Q3. Who is the topper of each category, and how do you handle a tie?

`RANK() ... WHERE r = 1` returns *every* student sharing the top mark: Science returns Asha **and** Chen,
Arts returns Jay **and** Kiran **[run]**. `ROW_NUMBER` would silently drop one of them, which is the
bug the interviewer is waiting for. Variation: `WHERE percentage = (SELECT MAX(percentage) FROM students
x WHERE x.category = s.category)`. Or `MAX(percentage) OVER (PARTITION BY category)` then compare.

### Q4. Find the Nth highest percentage (or salary).

```sql
SELECT DISTINCT percentage FROM students
ORDER BY percentage DESC LIMIT 1 OFFSET 2;                 -- 3rd highest; [run] returns 88.0

SELECT percentage FROM
  (SELECT percentage, DENSE_RANK() OVER (ORDER BY percentage DESC) r FROM students) t
WHERE r = 3;                                               -- portable, handles ties
```

Return `NULL` when it does not exist (wrap the `OFFSET` query in `SELECT (...)` or use `MAX` on a
`DENSE_RANK` filter). 2nd highest without window functions:
`SELECT MAX(p) FROM t WHERE p < (SELECT MAX(p) FROM t)` **[run]**.

### Q5. Students who scored above the average of **their own** category.

```sql
SELECT name FROM (
  SELECT name, percentage, AVG(percentage) OVER (PARTITION BY category) AS avg_cat
  FROM students) t
WHERE percentage > avg_cat;                -- [run]
```

Three equivalent forms: window function (one pass), join to a `GROUP BY` derived table, correlated
subquery. The check in the script asserts that all three return the same rows. Prefer the window or the
join; the correlated form re-evaluates the average per outer row unless the optimizer decorrelates it.

### Q6. Summary per category: count, average, maximum; only categories with at least 3 students.

```sql
SELECT category, COUNT(*) AS n, ROUND(AVG(percentage), 1) AS avg_pct, MAX(percentage) AS best
FROM   students
GROUP  BY category
HAVING COUNT(*) >= 3;                      -- [run]
```

`HAVING` filters groups, `WHERE` filters rows before grouping. Grade buckets use `CASE`:
`CASE WHEN percentage >= 85 THEN 'Distinction' WHEN percentage >= 70 THEN 'First' ELSE 'Pass' END`,
then `GROUP BY` the expression **[run]**.

### Q7. (yours) How do you solve "gaps and islands"? Practical scenario.

**Concept:** an *island* is a run of consecutive values; a *gap* is a break between runs. Scenario:
continuous periods when a server was `Active`.

**Technique:** within an island, `date - ROW_NUMBER()` is a **constant**, so it is a free group key.

```sql
-- SQL Server (as in your note)
WITH g AS (
  SELECT status_date,
         DATEADD(day, -ROW_NUMBER() OVER (ORDER BY status_date), status_date) AS island_id
  FROM   server_logs WHERE status = 'Active')
SELECT MIN(status_date) AS island_start, MAX(status_date) AS island_end, COUNT(*) AS days_active
FROM   g GROUP BY island_id;
```

| Dialect | Island key expression |
|---|---|
| SQL Server | `DATEADD(day, -ROW_NUMBER() OVER (ORDER BY d), d)` |
| PostgreSQL | `d - (ROW_NUMBER() OVER (ORDER BY d))::int` |
| Oracle | `d - ROW_NUMBER() OVER (ORDER BY d)` |
| MySQL 8 | `DATE_SUB(d, INTERVAL ROW_NUMBER() OVER (ORDER BY d) DAY)` |
| SQLite (the script) | `julianday(d) - ROW_NUMBER() OVER (ORDER BY d)` **[run]**: islands `01-01..01-03`, `01-05..01-06`, `01-08` |

Details that cost marks: you need **one row per date** (de-duplicate or use `DENSE_RANK`); the filter
(`status = 'Active'`) must be applied *before* the row number; for non-date sequences use
`id - ROW_NUMBER()`. Alternative with `LAG`: flag rows where `date <> prev + 1`, take a running `SUM` of the
flags as the island id. To find the **gaps**, use `LEAD(date)` and keep rows where `next_date - date > 1`.

### Q8. (yours) 7-day moving average without collapsing the rows.

```sql
SELECT order_date, daily_sales,
       AVG(daily_sales) OVER (ORDER BY order_date
                              ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS moving_avg_7_day
FROM   daily_sales;                        -- [run]
```

The window function keeps every row (unlike `GROUP BY`). What to add to your answer:

- the **first six rows average fewer than 7 values** (the frame is partial). Return `NULL` for them if
  the business wants a full window: `CASE WHEN COUNT(*) OVER (...) = 7 THEN AVG(...) END`;
- **`ROWS` counts rows, `RANGE` counts values.** If a date is missing, `6 PRECEDING` covers more than 7
  calendar days. For true calendar days use `RANGE BETWEEN INTERVAL '6' DAY PRECEDING AND CURRENT ROW`
  (PostgreSQL 11+, Oracle) or join to a calendar table;
- a **running total** is `SUM(x) OVER (ORDER BY d)` (default frame is `RANGE UNBOUNDED PRECEDING`).

### Q9. Month-over-month change and the previous value (`LAG` / `LEAD`).

```sql
WITH m AS (SELECT substr(order_date,1,7) AS month, SUM(amount) AS total FROM orders GROUP BY 1)
SELECT month, total, total - LAG(total) OVER (ORDER BY month) AS change   -- [run]
FROM m;
```

The first month has `NULL` (no previous row); give `LAG` a default (`LAG(total, 1, 0)`) when that is
wrong for the business. Percentage change needs a `NULLIF` on the divisor to avoid divide-by-zero.

### Q10. (yours) How do you find a poorly performing query and fix it?

**Process:** reproduce with real parameters -> get the **actual** plan (`EXPLAIN ANALYZE` in
PostgreSQL, `SET STATISTICS IO, TIME ON` + actual plan in SQL Server, `DBMS_XPLAN.DISPLAY_CURSOR` in
Oracle) -> find the most expensive operator -> compare estimated vs actual rows (a big gap means stale
statistics) -> fix -> re-measure.

**What to look for and the fix:**

| Symptom in the plan | Usual cause | Fix |
|---|---|---|
| Full table scan on a selective filter | no index, or non-SARGable predicate | add an index; rewrite the predicate |
| Index scan instead of seek | function on the column, implicit type conversion, leading wildcard | compare bare column to a range |
| Key lookup / table access per row | index not covering | add `INCLUDE` / extra columns |
| Sort or hash spill to disk | big sort, memory grant too small | index in the `ORDER BY` order; reduce rows earlier |
| Nested loop over a huge outer set | stale stats, missing join index | update statistics, index the join key |
| Estimated 1 row, actual 1,000,000 | outdated or skewed statistics, parameter sniffing | update stats, `OPTION (RECOMPILE)`, histogram |

**SARGability, proven by the script [run]:**

```sql
WHERE strftime('%Y', txn_date) = '2025'                          -- SCAN, index ignored
WHERE txn_date >= '2025-01-01' AND txn_date < '2026-01-01'       -- SEARCH using idx_txn_date
```

(the same applies to `YEAR(txn_date) = 2025`, `UPPER(name) = 'X'`, `col + 1 = 5`, or comparing a `VARCHAR`
column with a numeric literal).

Also: select only the columns you need (a covering index can answer the query from the index alone, shown
in the script as `COVERING INDEX`), paginate by keyset (`WHERE id > :last ORDER BY id LIMIT 50`) not
`OFFSET 100000`, avoid `SELECT DISTINCT` as a fix for a bad join, and batch writes.

> **Correction to a common claim:** "prefer `EXISTS` to `IN` for performance." Modern optimizers rewrite
> both to the same semi-join, so it is rarely a speed difference. The real reason to choose is
> **`NOT IN` versus `NOT EXISTS` when the subquery column can be `NULL`** (see Q12).

### Q11. (yours) Nested Loop vs Hash Join vs Merge Join.

| Join | How it works | Best when | Cost / needs |
|---|---|---|---|
| **Nested loop** | for each outer row, probe the inner side (ideally an index seek) | small outer set, selective predicate, index on the inner join key; supports **any** predicate (`<`, `LIKE`, `OR`) | O(outer x lookup); tiny memory; terrible when both sides are large and unindexed |
| **Hash join** | build an in-memory hash table on the smaller input, stream the larger one through it | large, unsorted inputs, **equality** joins, no useful index | needs memory (spills to disk when too small); blocking build phase |
| **Merge join** | walk two **sorted** inputs in step | both sides already sorted on the join key (index or earlier sort), range or equality | needs sorted input (adds a sort if absent); very fast once sorted, streams with no memory build |

How to use this in an interview: when a plan shows a nested loop with millions of outer rows, the answer is
"missing index on the inner join key or stale statistics"; a hash join with a spill means "increase memory
grant, reduce the build side with a filter or a better index". Do not claim you can *force* one without
hints; you steer it with indexes, statistics and query shape.

### Q12. `NOT IN` returns nothing; `COUNT(*)` vs `COUNT(col)`; anti-joins.

```sql
-- blocked contains (1) and (NULL)
SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM blocked);        -- [run] -> NO ROWS
SELECT name FROM customers c WHERE NOT EXISTS
       (SELECT 1 FROM blocked b WHERE b.customer_id = c.id);                          -- [run] -> correct
SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
WHERE  o.order_id IS NULL;                                                            -- [run] never ordered
```

`id NOT IN (1, NULL)` expands to `id <> 1 AND id <> NULL`; the second term is *unknown*, so the whole
predicate is never true. `NOT EXISTS` and the `LEFT JOIN ... IS NULL` anti-join are the safe forms.
`COUNT(*)` counted 7 employees while `COUNT(manager_id)` counted 6 because the CEO's manager is `NULL`
**[run]**. Use `COALESCE(x, default)` to substitute, and `IS NULL` / `IS NOT NULL` (never `= NULL`).

### Q13. (yours) CTE vs temporary table.

| | CTE (`WITH`) | Temporary table (`#t` / `CREATE TEMP TABLE`) |
|---|---|---|
| Lifetime | the one statement | the session / procedure |
| Materialised? | **depends on the engine** (see below) | yes, physically stored |
| Statistics and indexes | no own statistics, no indexes | **yes**: can index, optimizer sees real row counts |
| Referenced several times | may be re-evaluated each time | computed once |
| Recursion | **yes** (`WITH RECURSIVE`), the main unique use | no |
| Cost | none to create | write I/O, possible recompiles |

> **Correction:** "a CTE is always recalculated on every reference" is true on **SQL Server** only (it is
> inlined, never materialised). **PostgreSQL 12+** inlines a CTE referenced once and materialises one
> referenced several times (control with `MATERIALIZED` / `NOT MATERIALIZED`); **Oracle** may materialise
> automatically or with the `MATERIALIZE` hint. So: say "engine-dependent" and name the engine.

Use a CTE for readability and recursion (org-chart, bill of materials, dates generator). Use a temp table
when an intermediate result is large, reused several times, or needs an index before the next join.

### Q14. (yours) Delete duplicates from a large, busy table safely.

```sql
WITH d AS (
  SELECT entry_id,
         ROW_NUMBER() OVER (PARTITION BY client_id, log_timestamp ORDER BY entry_id) AS rk
  FROM client_logs)
DELETE FROM client_logs WHERE entry_id IN (SELECT entry_id FROM d WHERE rk > 1);   -- [run]
```

`PARTITION BY` lists the columns that define "duplicate"; `ORDER BY` picks the survivor (here the lowest
id). The script confirms the survivors are `[1, 3, 4, 7]`.

Make it **safe on a live table**: (1) run the `SELECT` first and count; (2) take a backup or copy the
victims into an archive table; (3) delete in **batches** (`TOP (10000)` / `LIMIT`) in a loop with a
commit between batches to avoid a huge transaction, lock escalation and log growth; (4) run off-peak;
(5) afterwards add a **unique constraint / index** so it cannot happen again. SQL Server can delete
through the CTE directly (`DELETE FROM d WHERE rk > 1`); Oracle often uses `ROWID`. Find duplicates first
with `GROUP BY client_id, log_timestamp HAVING COUNT(*) > 1`.

### Q15. (yours) Correlated subquery vs standard subquery; performance implications.

A standard (uncorrelated) subquery has no reference to the outer query, so it is evaluated **once**. A
correlated subquery references an outer column, so *logically* it runs once per outer row.

```sql
-- correlated: employees above their department average
SELECT name FROM employees e
WHERE salary > (SELECT AVG(salary) FROM employees x WHERE x.dept = e.dept);   -- [run]
```

> **Correction:** it is not automatically O(N^2). With an index on the correlated column it is N index
> lookups, and most optimizers **decorrelate (unnest)** simple cases into a join. It is slow when the
> inner side is a full scan per row, the correlation is on an unindexed column, or the optimizer cannot
> flatten it. Confirm in the plan: look for a subquery operator executed N times ("loops" in PostgreSQL).

Fix by rewriting: a window function (`AVG(salary) OVER (PARTITION BY dept)`), or a join to a pre-aggregated
derived table. The script asserts that all three forms return the same rows **[run]**. Keep correlated
`EXISTS` when it reads better and the plan is a semi-join.

### Q16. (yours) How do you handle deadlocks?

A **deadlock** is two transactions each holding a lock the other needs; the engine kills one (the
*victim*) with an error (`1205` SQL Server, `ORA-00060`, `40P01` PostgreSQL, `1213` MySQL).

Prevent:

1. **Consistent lock ordering:** every code path updates tables and rows in the same order (always
   account A before B, ordered by id).
2. **Short transactions:** no user interaction or remote call inside a transaction; commit early.
3. **Narrow lock footprint:** index the `WHERE` columns of updates so they lock only the rows they need,
   not a range or the table.
4. **Right isolation level:** use row-versioning so readers do not take shared locks: **RCSI / snapshot**
   on SQL Server; **MVCC** is already the default on PostgreSQL and Oracle. `SELECT ... FOR UPDATE` only
   when you truly need the lock.
5. **Take the strongest lock first** (`UPDLOCK`, `FOR UPDATE`) so a read-then-write does not deadlock on
   lock upgrade.

Handle: **retry** the victim transaction (idempotent, bounded, with jitter), log the deadlock graph
(`system_health` extended event / `pg_stat_activity` + `log_lock_waits`), and fix the conflicting order.
Optimistic locking (`@Version` column) avoids holding locks across user think time.

> Precision: deadlocks are about *concurrency control / isolation*, not about ACID as a whole;
> "I" (isolation) is the property whose implementation causes them.

### Q17. Pivot rows to columns; find consecutive days; second highest per group.

```sql
-- pivot with conditional aggregation (portable, works everywhere)
SELECT customer_id,
       SUM(CASE WHEN substr(order_date,6,2) = '01' THEN amount ELSE 0 END) AS jan,
       SUM(CASE WHEN substr(order_date,6,2) = '02' THEN amount ELSE 0 END) AS feb
FROM orders GROUP BY customer_id;

-- 2nd highest salary per department
SELECT dept, name, salary FROM (
  SELECT dept, name, salary, DENSE_RANK() OVER (PARTITION BY dept ORDER BY salary DESC) r
  FROM employees) t WHERE r = 2;

-- users with 3+ consecutive login days = gaps-and-islands (Q7), HAVING COUNT(*) >= 3
```

## Dialect cheat sheet

| Need | MySQL / PostgreSQL / SQLite | SQL Server | Oracle |
|---|---|---|---|
| first N rows | `LIMIT n` | `SELECT TOP n` / `OFFSET .. FETCH` | `FETCH FIRST n ROWS ONLY` (12c+), `ROWNUM` before |
| skip M rows | `OFFSET m` | `OFFSET m ROWS` | `OFFSET m ROWS` |
| null-safe default | `COALESCE` | `COALESCE` / `ISNULL` | `COALESCE` / `NVL` |
| string concat | `\|\|` (PG, SQLite) / `CONCAT` | `+` / `CONCAT` | `\|\|` |
| current date | `CURRENT_DATE` | `GETDATE()` / `CAST(GETDATE() AS date)` | `SYSDATE` / `TRUNC(SYSDATE)` |
| date arithmetic | `d + INTERVAL '7 day'` (PG), `DATE_ADD` (MySQL) | `DATEADD(day, 7, d)` | `d + 7` |
| upsert | `ON CONFLICT` (PG) / `ON DUPLICATE KEY` | `MERGE` | `MERGE` |

## A worked example

Run the script and read **section 1**, then break it on purpose:

```text
=== 1. Top N students: overall, per category, and the ties question ===
  ok  top 3 overall (LIMIT cuts ties arbitrarily: Asha/Chen tie, Bala is 4th) -> ['Farah', 'Asha', 'Chen']
  ok  top 3 DISTINCT percentages incl. ties (DENSE_RANK) -> ['Farah', 'Asha', 'Chen', 'Bala']
  ok  topper(s) per category with RANK (ties both returned) -> [('Arts', 'Jay'), ('Arts', 'Kiran'), ...]
```

Change `RANK()` to `ROW_NUMBER()` in the topper query: Arts loses one of its two toppers and the check
fails. Then swap `DENSE_RANK` for `RANK` in the "top 3 percentages" query: the result changes because
`RANK` skips numbers after a tie. That is exactly the distinction the interviewer is testing.

## Hands-on drills

1. Add a `marks` and `total` column and compute `percentage = marks * 100.0 / total`. Where should the
   division guard go (`NULLIF(total, 0)`)?
2. Return, for each category, the gap between the topper and the runner-up (`LEAD` / `LAG`).
3. Find categories where *every* student is above 60 (`HAVING MIN(percentage) > 60`).
4. Rank students across **all** categories but show the rank *within* the category too (two window
   functions with different `PARTITION BY`).
5. Write the gaps (not islands) query: the missing dates between the first and last log date, using a
   recursive CTE calendar and an anti-join.
6. Take a slow query you know, capture its plan, change one thing, and write down the before/after row
   counts and elapsed time.
7. Reproduce a deadlock with two sessions updating two rows in opposite order; fix it with ordering.

## The 60-second spoken answers

**Top N per group:** "I would use a window function: `ROW_NUMBER() OVER (PARTITION BY category ORDER BY
percentage DESC)` in a subquery and keep rank 3 or less. I ask about ties first: `ROW_NUMBER` gives exactly
N rows, `DENSE_RANK` keeps everyone who ties. I would back it with an index on category and percentage."

**Slow query:** "I get the actual execution plan, find the costliest operator and compare estimated to
actual rows. Typical fixes are an index that matches the filter and join keys, making the predicate
SARGable by not wrapping the column in a function, a covering index, updating statistics, or rewriting a
correlated subquery as a join or window function. I measure before and after."

**Deadlocks:** "Keep a consistent lock order, keep transactions short, index the update predicates, use
row versioning so readers do not block writers, and retry the victim with a bounded, idempotent retry."
