---
id: reported-database-rounds
title: Reported rounds, databases (Mastercard, Deloitte): MVCC in PostgreSQL vs MySQL, cascade and orphan removal, locking, SQL vs NoSQL for money
stack: java
skill: sql
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`).

### Q1 [senior] What databases have you worked with? How does PostgreSQL handle MVCC differently from MySQL?
tags: mvcc, postgresql, mysql, innodb, vacuum, undo-log, isolation, bloat, mastercard, reported-rounds

**Start here: the concepts**
- **MVCC (multi-version concurrency control):** a writer keeps old versions of rows, so readers see a consistent snapshot and don't block on writers.
- Both databases do this. They differ in **where the old versions live**, and that changes how you operate them.

**The live scenario (functional requirement)**
*FR: "A high-update orders table runs for months."* On PostgreSQL the table has grown to five times its live data with bloat. On MySQL a long-running report makes the undo log grow, and purge falls behind.

**What the interviewer is really checking**
Whether you know the mechanism and its operational effects, rather than only "both support MVCC".

**How I answer it** (120-second answer, point by point)

| | PostgreSQL | MySQL (InnoDB) |
|---|---|---|
| An update | Writes a **new row version** in the table | Changes the row **in place** |
| Old versions | Stay in the table as dead tuples | Rebuilt from the **undo log** |
| Visibility check | `xmin`/`xmax` transaction ids on each row | Transaction id and rollback pointer |
| Cleanup | **VACUUM** (autovacuum) | **Purge** threads |
| Default isolation | Read Committed | Repeatable Read |
| Repeatable Read blocks phantoms by | Snapshot | Snapshot, plus **gap and next-key locks** for locking reads and writes |
| Primary key | Heap table with separate indexes | Table **clustered** on the primary key |
| Index on update | New version may need index updates, unless **HOT** applies | Secondary indexes point at the primary key |
| Main risk | Bloat, wraparound if vacuum can't keep up | Long transactions swell undo; gap-lock deadlocks |

1. **For update-heavy PostgreSQL:** tune autovacuum per table, and use a lower `fillfactor` so HOT updates stay on the same page, which avoids index writes.
2. **Long transactions hurt both,** because the old versions can't be removed while someone might need them. In PostgreSQL, an idle-in-transaction session blocks vacuum; in MySQL it grows the undo history.
3. **Gap locks:** at Repeatable Read, InnoDB locks ranges, so inserts can block or deadlock in surprising ways. Some high-write teams run MySQL at Read Committed for this reason.
4. **Serializable:** PostgreSQL uses SSI (detects conflicts and aborts one transaction, so you must retry); InnoDB uses shared locks on reads.

**Trade-offs and what can go wrong**
- Answer the first half honestly: name the databases you've really used, with one fact about what you did there.
- Don't say "MySQL doesn't have MVCC". InnoDB does.

**How I'd monitor it**
PostgreSQL: `n_dead_tup`, last autovacuum time, `pg_stat_activity` for long transactions, and transaction-id age. MySQL: `SHOW ENGINE INNODB STATUS` for history list length and deadlocks.

**Follow-ups to expect**
- *How do you find bloat?* -> `pg_stat_user_tables`, then `pg_repack` to reclaim without a long lock.
- *Why is a long report dangerous?* -> It holds its snapshot, so cleanup stops behind it. Run it on a replica.

**60-second answer**
"Both keep old row versions so readers don't block writers, but differently. PostgreSQL writes a new row version in the table and leaves the old one as a dead tuple, which VACUUM removes, so update-heavy tables risk bloat. InnoDB updates in place and rebuilds old versions from the undo log, which purge threads clean. Their default isolation differs too: Read Committed on Postgres, Repeatable Read on MySQL, where gap locks can surprise you. In both, long transactions are the enemy, since cleanup can't pass them, so I run heavy reports on a replica."

### Q2 [mid] What are cascade types and orphan removal in JPA?
tags: jpa, cascade, orphanremoval, cascadetype-remove, parent-child, hibernate, mastercard, reported-rounds

**Start here: the concepts**
- **Cascade:** when I do something to the parent, do the same thing to its children.
- **Orphan removal:** when a child is **removed from the parent's collection**, delete it from the database.

**The live scenario (functional requirement)**
*FR: "An order owns its line items."* `order.getItems().remove(item)` should delete that row. With `CascadeType.ALL` alone, the row stays, and depending on the mapping, its foreign key is set to null or left alone.

**What the interviewer is really checking**
The exact difference between the two, and when cascade is dangerous.

**How I answer it** (120-second answer, point by point)

```java
@OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true)
private List<LineItem> items = new ArrayList<>();
```

| Cascade type | Effect |
|---|---|
| `PERSIST` | Saving the parent saves new children |
| `MERGE` | Merging the parent merges the children |
| `REMOVE` | Deleting the parent deletes the children |
| `REFRESH` | Reloading the parent reloads the children |
| `DETACH` | Detaching the parent detaches the children |
| `ALL` | All of the above |

The difference:

| Action | `CascadeType.REMOVE` | `orphanRemoval = true` |
|---|---|---|
| Delete the parent | Deletes children | Deletes children |
| Remove a child from the collection | Nothing is deleted | Deletes that child |

1. **Use both** only when the child has **no meaning without the parent**, like order lines.
2. **Never cascade `REMOVE` on `@ManyToOne` or `@ManyToMany`.** Deleting one employee could delete the shared department, and then everyone else in it.
3. **Don't replace the collection:** `order.setItems(newList)` throws an error under `orphanRemoval`. Modify the existing collection instead.
4. **Keep both sides in sync** with an `addItem` helper that sets `item.setOrder(this)`.

**Trade-offs and what can go wrong**
- Cascading `REMOVE` loads and deletes children **one by one**. For large collections, a database `ON DELETE CASCADE` (with `@OnDelete`) or a bulk delete is far faster.
- Moving a child to another parent with `orphanRemoval` can delete it, so don't use `orphanRemoval` if children move.

**Follow-ups to expect**
- *`@OnDelete` vs `CascadeType.REMOVE`?* -> One happens in the database, and the other in Hibernate.
- *N+1?* -> A separate issue, but this mapping is often where it occurs. See bank 85.

**60-second answer**
"Cascade propagates an operation from parent to child, so PERSIST saves children with the parent, and REMOVE deletes them with it. Orphan removal is different: it deletes a child when it's removed from the parent's collection, where REMOVE alone would do nothing. I use both only when the child can't exist without the parent, like order lines. I never cascade remove on a ManyToOne, because deleting an employee could delete a shared department. And for big collections, I use a database ON DELETE CASCADE, because Hibernate deletes one by one."

### Q3 [senior] Have you used a locking mechanism in your code, such as database-level locking?
tags: database-locking, pessimistic-lock, select-for-update, skip-locked, advisory-lock, optimistic-lock, deadlock, mastercard, reported-rounds

**Start here: the concepts**
- **Pessimistic:** lock now, and others wait (`SELECT ... FOR UPDATE`).
- **Optimistic:** no lock, and check a version at write (bank 99 Q3).
- **Constraint:** let the database reject the bad case with a unique index.

**The live scenario (functional requirement)**
*FR: "Transfer money between two accounts, and let 10 pods share one job queue table with no job processed twice."*

**What the interviewer is really checking**
That you can pick by contention, and that you have thought about deadlocks and timeouts.

**How I answer it** (120-second answer, point by point)

| Situation | Choice | Why |
|---|---|---|
| Rare conflicts, user edits | Optimistic `@Version` | No lock held; retry on conflict |
| Must not sell the same seat | Unique constraint | The simplest guarantee |
| Simple counter | Atomic `UPDATE ... SET n = n - 1 WHERE n > 0` | One statement, no read-then-write |
| High contention, money movement | `SELECT ... FOR UPDATE` | Conflicts are likely, so wait rather than retry |
| Workers sharing a queue table | `FOR UPDATE SKIP LOCKED` | Each pod skips rows held by others |
| One job across pods | PostgreSQL advisory lock, or ShedLock | Coordinates something that isn't one row |

In Spring Data:

```java
@Lock(LockModeType.PESSIMISTIC_WRITE)
@QueryHints(@QueryHint(name = "jakarta.persistence.lock.timeout", value = "2000"))
@Query("select a from Account a where a.id in :ids order by a.id")
List<Account> lockAccounts(List<Long> ids);
```

1. **Lock in a consistent order.** `order by a.id` above prevents the classic deadlock, where one transfer locks A then B and another locks B then A.
2. **Set a timeout**, so that a stuck transaction doesn't stall everyone.
3. **Keep the transaction short.** Never call an HTTP service while holding a row lock.
4. **Deadlocks still happen:** the database aborts one transaction, so retry that error.

**Trade-offs and what can go wrong**
- A lock on an unindexed column can lock far more rows than intended.
- Transaction boundaries matter: the lock is released at commit, and `@Transactional` self-invocation means there may be no transaction at all.
- A connection is held the whole time, so locks and pool exhaustion go together (bank 89 Q4).

**How I'd monitor it**
Lock wait time, deadlock count, `pg_locks` joined to `pg_stat_activity`, and `lock_timeout` errors.

**Follow-ups to expect**
- *Why not a Java lock?* -> It only protects one JVM.
- *Distributed lock in Redis?* -> It works for efficiency, but use a fencing token or the database when correctness truly depends on it.

**60-second answer**
"Yes, and I choose by contention. For rare conflicts, optimistic locking with a version column. For things that must never happen twice, a unique constraint. A counter gets one atomic update. For high-contention money movement, SELECT FOR UPDATE with a timeout, always locking rows in id order to avoid deadlocks, and retrying if the database aborts one. For worker pods sharing a queue table, FOR UPDATE SKIP LOCKED. I keep those transactions short, with no HTTP calls inside, because a held lock also holds a connection."

### Q4 [senior] How would you choose between SQL and NoSQL for a high-volume financial transaction system?
tags: sql, nosql, acid, ledger, financial, partitioning, cqrs, consistency, deloitte, reported-rounds

**Start here: the concepts**
- The decision is driven by **access patterns and consistency needs**, not by "SQL doesn't scale".
- Money has one hard rule: a transfer must be atomic, and a balance must never be wrong.

**The live scenario (functional requirement)**
*FR: "5,000 payments a second, double-entry bookkeeping, full audit, and customers viewing their statements."*

**What the interviewer is really checking**
Whether you split the system by requirement, instead of forcing one database to do everything.

**How I answer it** (120-second answer, point by point)
1. **System of record: relational,** for multi-row ACID transactions, constraints, and rich reconciliation queries. A double-entry ledger is a textbook fit: debit and credit commit together, or neither does.
2. **Scaling the relational side:** an append-only ledger, connection pooling, partitioning by account or date, read replicas, and sharding by account when one node isn't enough.
3. **Distributed SQL** (CockroachDB, Spanner, YugabyteDB, Aurora DSQL) if you need horizontal write scale with ACID, accepting higher latency per transaction.
4. **Where NoSQL fits, alongside:**

| Need | Store | Why |
|---|---|---|
| Statement history at huge read volume | Cassandra or DynamoDB | Known query by account and time; easily partitioned |
| Idempotency keys, sessions | Redis or DynamoDB | Simple key lookups with TTL |
| Search across transactions | OpenSearch | Text search and aggregations |
| Event history | Kafka | Replayable log for downstream services |

5. **Keep them in step** with an outbox: the ledger commit writes an event in the same transaction, and consumers build the read stores (CQRS).
6. **Say what the read side can tolerate:** statements a few seconds stale are fine. The balance used to approve a payment comes from the system of record.

**Trade-offs and what can go wrong**
- DynamoDB and MongoDB now offer multi-document transactions, so "NoSQL has no transactions" is outdated. The real limits are query flexibility, and transaction size and cost.
- Two stores mean reconciliation work. Have a job that verifies them.
- Eventually consistent reads must never drive a debit decision.

**Follow-ups to expect**
- *Why append-only?* -> History can't be altered, which suits audit. Balance is a derived figure, with periodic snapshots.
- *Bank 25 Q3* covers the general choice.

**60-second answer**
"For the system of record, I'd pick relational: a double-entry ledger needs multi-row ACID and constraints, and SQL scales further than people assume with an append-only design, partitioning, replicas and sharding by account. If write volume outgrows that, distributed SQL keeps ACID at some latency cost. NoSQL fits alongside, not instead: Cassandra or DynamoDB for statement history, Redis for idempotency keys, OpenSearch for search. An outbox keeps them in sync, and eventually consistent reads never decide a debit."
