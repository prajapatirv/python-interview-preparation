---
id: sql
title: SQL & relational databases
order: 10
summary: Joins, indexes, query tuning, transactions and isolation, Oracle/PostgreSQL specifics.
crib: java/java-interview-prep/topics/10-sql-oracle.md
docs: java/java-interview-prep/deep_dive/22_sql_query_interview.md
examples: java/java-interview-prep/examples/22_sql_queries
keywords: sql, query, queries, join, index, indexes, oracle, postgres, postgresql, mysql, isolation level, acid, normalization, normalisation, explain plan, stored procedure, group by, window function, rownum, deadlock in database, database transaction
---
Skill focus for SQL & relational databases answers:
- Show the query thinking: what the data looks like, which index serves it, how you'd read the plan.
- Transactions: isolation levels and the anomaly each prevents, locking vs MVCC, deadlocks.
- Production stories: a missing index under load, N+1 from the ORM, a long transaction holding locks.
