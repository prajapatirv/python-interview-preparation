/*
 * 02 - Transaction isolation anomalies, optimistic vs pessimistic locking, propagation
 *
 * Run:  java 02_isolation_levels_and_optimistic_locking.java
 *
 * Deterministic interleavings of two transactions over an in-memory table. You see exactly which
 * anomaly each isolation level permits, and how a @Version column turns a silent lost update
 * into an exception you can retry.
 */
import java.util.*;

class IsolationLevelsAndOptimisticLocking {

    enum Isolation { READ_UNCOMMITTED, READ_COMMITTED, REPEATABLE_READ }

    /** committed + one uncommitted overlay per transaction; a snapshot for repeatable read. */
    static class Db {
        final Map<String, Integer> committed = new HashMap<>();
        final Map<String, Map<String, Integer>> uncommitted = new HashMap<>();
        final Map<String, Map<String, Integer>> snapshot = new HashMap<>();

        Tx begin(String name, Isolation level) { uncommitted.put(name, new HashMap<>()); return new Tx(this, name, level); }
    }

    static class Tx {
        final Db db; final String name; final Isolation level;
        Tx(Db db, String name, Isolation level) { this.db = db; this.name = name; this.level = level; }

        int read(String key) {
            if (db.uncommitted.get(name).containsKey(key)) return db.uncommitted.get(name).get(key);   // own writes
            if (level == Isolation.READ_UNCOMMITTED)
                for (Map.Entry<String, Map<String, Integer>> o : db.uncommitted.entrySet())
                    if (!o.getKey().equals(name) && o.getValue().containsKey(key)) return o.getValue().get(key);        // DIRTY read
            if (level == Isolation.REPEATABLE_READ) {
                Map<String, Integer> snap = db.snapshot.computeIfAbsent(name, n -> new HashMap<>(db.committed));
                return snap.get(key);
            }
            return db.committed.get(key);
        }
        void write(String key, int v) { db.uncommitted.get(name).put(key, v); }
        void commit() { db.committed.putAll(db.uncommitted.remove(name)); db.snapshot.remove(name); }
        void rollback() { db.uncommitted.remove(name); db.snapshot.remove(name); }
    }

    // ---- optimistic locking with a version column
    static class Row { int balance; int version; Row(int b) { balance = b; } }

    static class OptimisticLockException extends RuntimeException { OptimisticLockException(String m) { super(m); } }

    /** UPDATE account SET balance=?, version=version+1 WHERE id=? AND version=?   (0 rows => exception) */
    static void update(Row stored, int newBalance, int expectedVersion) {
        if (stored.version != expectedVersion)
            throw new OptimisticLockException("row was modified by another transaction (expected v" + expectedVersion + ", actual v" + stored.version + ")");
        stored.balance = newBalance;
        stored.version++;
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {

        section("1. Dirty read (only READ_UNCOMMITTED allows it)");
        for (Isolation level : new Isolation[]{Isolation.READ_UNCOMMITTED, Isolation.READ_COMMITTED}) {
            Db db = new Db(); db.committed.put("balance", 100);
            Tx a = db.begin("A", Isolation.READ_COMMITTED), b = db.begin("B", level);
            a.write("balance", 500);                          // A has not committed
            int seen = b.read("balance");
            a.rollback();                                     // ...and then A rolls back
            System.out.printf("  B at %-17s read balance=%d (true committed value is 100)%s%n", level, seen, seen == 500 ? "  <- read data that never existed" : "");
        }

        section("2. Non-repeatable read (READ_COMMITTED allows it, REPEATABLE_READ does not)");
        for (Isolation level : new Isolation[]{Isolation.READ_COMMITTED, Isolation.REPEATABLE_READ}) {
            Db db = new Db(); db.committed.put("price", 10);
            Tx a = db.begin("A", level), b = db.begin("B", Isolation.READ_COMMITTED);
            int first = a.read("price");
            b.write("price", 12); b.commit();                 // another transaction commits between A's two reads
            int second = a.read("price");
            System.out.printf("  A at %-16s read price twice: %d then %d%s%n", level, first, second, first != second ? "  <- changed inside one tx" : "  (stable)");
        }
        System.out.println("  Phantoms (new ROWS matching a range appear) are prevented by SERIALIZABLE (or gap locks in MySQL InnoDB RR).");
        System.out.println("  Defaults: PostgreSQL/Oracle/SQL Server = READ COMMITTED, MySQL InnoDB = REPEATABLE READ.");

        section("3. Lost update: two users edit the same row");
        Row naive = new Row(100);
        int aRead = naive.balance, bRead = naive.balance;     // both load balance=100
        naive.balance = aRead - 30;                           // A writes 70
        naive.balance = bRead - 50;                           // B writes 50 -> A's change is silently gone
        System.out.println("  without a version check: final balance=" + naive.balance + " (should be 20)");

        Row guarded = new Row(100);
        int aVer = guarded.version, bVer = guarded.version;
        update(guarded, 100 - 30, aVer);                      // A wins
        try { update(guarded, 100 - 50, bVer); }              // B's UPDATE ... WHERE version=0 matches 0 rows
        catch (OptimisticLockException e) {
            System.out.println("  with @Version: B fails -> " + e.getMessage());
            int fresh = guarded.balance, v = guarded.version; // retry: re-read, re-apply, re-submit
            update(guarded, fresh - 50, v);
            System.out.println("  after retry   : balance=" + guarded.balance + " version=" + guarded.version);
        }
        System.out.println("  Spring/JPA: @Version on the entity -> ObjectOptimisticLockingFailureException; retry the whole use case.");

        section("4. Optimistic vs pessimistic");
        System.out.println("  Optimistic : no DB locks, detect conflicts at write. Best when conflicts are RARE (most web apps). Needs a retry path.");
        System.out.println("  Pessimistic: SELECT ... FOR UPDATE (@Lock(PESSIMISTIC_WRITE)). Best when conflicts are COMMON and retries are costly");
        System.out.println("               (inventory of a hot SKU). Keep the transaction tiny; take locks in a consistent order; set a lock timeout.");
        System.out.println("  Queue-style claims: SELECT ... FOR UPDATE SKIP LOCKED lets many workers pull different rows without blocking.");

        section("5. @Transactional propagation you must be able to explain");
        System.out.println("  REQUIRED (default): join the caller's transaction or start one");
        System.out.println("  REQUIRES_NEW      : suspend the caller's, run in a NEW transaction (audit log that must survive a rollback)");
        System.out.println("  NESTED            : savepoint inside the caller's transaction (JDBC only, not JPA)");
        System.out.println("  SUPPORTS / NOT_SUPPORTED / MANDATORY / NEVER: run with/without/require/forbid a transaction");
        System.out.println("  Rollback: RuntimeException and Error by default; checked exceptions need rollbackFor.");
        System.out.println("  readOnly=true is a hint: skips dirty checking in Hibernate, lets the driver route to a replica.");
        System.out.println("  Keep transactions SHORT: never hold one open across an HTTP call, a Kafka send or user think-time.");
    }
}

// EXERCISE: add SERIALIZABLE using a lock on the whole key range and show which anomaly it removes.
