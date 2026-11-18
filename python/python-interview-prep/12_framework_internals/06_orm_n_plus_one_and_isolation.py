"""
The ORM N+1 query problem and its fixes, then lost updates and optimistic vs pessimistic locking.

The Python twin of java/java-interview-prep/examples/09_spring_data_jpa/01_n_plus_one_and_lazy_loading.java
and 02_isolation_levels_and_optimistic_locking.java (see shared/cross-stack-pairs.md). Real SQL on an
in-memory SQLite database (standard library), with every statement counted through
sqlite3's trace callback, so "1 + N queries" is a number you see, not a claim. The SQLAlchemy calls
that do the same thing are named alongside.

Run me: python 06_orm_n_plus_one_and_isolation.py
Deep dive: ../deep_dive/11_python_framework_development.md
"""
import shutil
import sqlite3
import tempfile
from pathlib import Path

OPENED = []          # connections and temp folders to clean up at the end


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


class QueryCounter:
    """Counts SELECT statements on a connection, like SQLAlchemy's echo=True or Hibernate's statistics."""

    def __init__(self, conn):
        self.count = 0
        conn.set_trace_callback(self._seen)

    def _seen(self, sql):
        if sql.lstrip().upper().startswith("SELECT"):
            self.count += 1


def build_db(conn, authors=50, books_each=4):
    conn.executescript("""
        CREATE TABLE author (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE book (id INTEGER PRIMARY KEY, author_id INTEGER REFERENCES author(id), title TEXT, pages INTEGER);
        CREATE INDEX book_author ON book(author_id);
    """)
    conn.executemany("INSERT INTO author VALUES (?, ?)", [(a, f"author-{a}") for a in range(1, authors + 1)])
    conn.executemany("INSERT INTO book (author_id, title, pages) VALUES (?, ?, ?)",
                     [(a, f"book-{a}-{b}", 100 + b) for a in range(1, authors + 1) for b in range(books_each)])


# ================================================================ a tiny ORM with lazy relationships
class Author:
    """Like a mapped class with relationship(lazy="select"): books load on first access, ONE query each."""

    def __init__(self, conn, id_, name):
        self._conn, self.id, self.name, self._books = conn, id_, name, None

    @property
    def books(self):
        if self._books is None:
            self._books = self._conn.execute("SELECT title, pages FROM book WHERE author_id = ?", (self.id,)).fetchall()
        return self._books


def authors_lazy(conn):
    return [Author(conn, i, n) for i, n in conn.execute("SELECT id, name FROM author ORDER BY id")]


def pages_per_author_naive(conn):
    return {a.name: sum(p for _, p in a.books) for a in authors_lazy(conn)}           # touches books per author


def pages_per_author_join(conn):
    """joinedload(): one query with a JOIN."""
    out = {}
    for name, pages in conn.execute("SELECT a.name, b.pages FROM author a JOIN book b ON b.author_id = a.id"):
        out[name] = out.get(name, 0) + pages
    return out


def pages_per_author_selectin(conn):
    """selectinload(): one query for the parents, one IN (...) query for all their children."""
    authors = authors_lazy(conn)
    ids = [a.id for a in authors]
    rows = conn.execute(f"SELECT author_id, pages FROM book WHERE author_id IN ({','.join('?' * len(ids))})", ids)
    by_author = {}
    for author_id, pages in rows:
        by_author[author_id] = by_author.get(author_id, 0) + pages
    return {a.name: by_author.get(a.id, 0) for a in authors}


def pages_per_author_aggregate(conn):
    """Project only what the use case needs: let the database do the sum."""
    return dict(conn.execute("SELECT a.name, SUM(b.pages) FROM author a JOIN book b ON b.author_id = a.id GROUP BY a.id"))


def measure(label, fn, conn):
    counter = QueryCounter(conn)
    result = fn(conn)
    conn.set_trace_callback(None)
    print(f"  {label:<44} {counter.count:>3} SELECT(s)")
    return result


# ================================================================ concurrency on one row
def new_shared_db():
    folder = tempfile.mkdtemp()
    OPENED.append(folder)
    path = Path(folder) / "shop.db"
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE product (id INTEGER PRIMARY KEY, stock INTEGER, version INTEGER)")
    c.execute("INSERT INTO product VALUES (1, 10, 0)")
    c.commit()
    c.close()
    return path


def connect(path):
    conn = sqlite3.connect(path, isolation_level=None, timeout=0.2)    # autocommit; we write BEGIN ourselves
    OPENED.append(conn)
    return conn


def stock(path):
    c = sqlite3.connect(path)
    try:
        return c.execute("SELECT stock, version FROM product WHERE id = 1").fetchone()
    finally:
        c.close()


def optimistic_buy(conn, qty, read):
    """UPDATE ... WHERE version = <the version I read>. Zero rows changed means someone got there first."""
    stock_, version = read
    cur = conn.execute("UPDATE product SET stock = ?, version = version + 1 WHERE id = 1 AND version = ?",
                       (stock_ - qty, version))
    return cur.rowcount == 1


def main():
    conn = sqlite3.connect(":memory:")
    build_db(conn)

    section("1. Naive: loop over authors and touch author.books -> 1 + N queries")
    naive = measure("lazy relationship in a loop (50 authors)", pages_per_author_naive, conn)
    print("  1 query for the authors + 1 per author. On a page that lists 50 authors it is 51 round trips;")
    print("  in production each one is a network hop, so latency grows with the data, not the code.")

    section("2. Fix A: one JOIN (SQLAlchemy joinedload, JPA JOIN FETCH)")
    joined = measure("JOIN", pages_per_author_join, conn)

    section("3. Fix B: one IN (...) query for all children (SQLAlchemy selectinload, @BatchSize)")
    selectin = measure("parents + one IN query", pages_per_author_selectin, conn)
    print("  selectinload avoids the row explosion a JOIN causes when a parent has many children.")

    section("4. Fix C: fetch only what the use case needs (an aggregate or a projection)")
    agg = measure("GROUP BY in the database", pages_per_author_aggregate, conn)
    print(f"  all four give the same answer: {naive == joined == selectin == agg}")
    print("  Spot it in tests: count queries (sqlalchemy event 'before_cursor_execute', pytest fixtures),")
    print("  or set lazy='raise' on relationships so an accidental lazy load fails loudly.")
    # EXPERIMENT: change build_db(conn) to 500 authors - the naive count becomes 501, the others stay 1-2.

    section("5. Lost update: two users read the same stock, both write")
    path = new_shared_db()
    alice, bob = connect(path), connect(path)
    a_read = alice.execute("SELECT stock FROM product WHERE id = 1").fetchone()[0]
    b_read = bob.execute("SELECT stock FROM product WHERE id = 1").fetchone()[0]
    alice.execute("UPDATE product SET stock = ? WHERE id = 1", (a_read - 3,))
    bob.execute("UPDATE product SET stock = ? WHERE id = 1", (b_read - 2,))
    print(f"  both read {a_read}; Alice buys 3, Bob buys 2; stock is now {stock(path)[0]} (should be 5)")
    print("  Each statement was correct on its own. Read-modify-write in application code loses one update.")

    section("6. Fix: optimistic locking with a version column (SQLAlchemy version_id_col, JPA @Version)")
    path = new_shared_db()
    alice, bob = connect(path), connect(path)
    a_read = alice.execute("SELECT stock, version FROM product WHERE id = 1").fetchone()
    b_read = bob.execute("SELECT stock, version FROM product WHERE id = 1").fetchone()
    print(f"  Alice's write: {'applied' if optimistic_buy(alice, 3, a_read) else 'CONFLICT'}")
    ok = optimistic_buy(bob, 2, b_read)
    print(f"  Bob's write  : {'applied' if ok else 'CONFLICT - 0 rows matched his stale version'}")
    if not ok:
        fresh = bob.execute("SELECT stock, version FROM product WHERE id = 1").fetchone()
        print(f"  Bob re-reads {fresh} and retries: {'applied' if optimistic_buy(bob, 2, fresh) else 'CONFLICT'}")
    print(f"  stock and version now: {stock(path)}  (correct: 5, two updates)")
    print("  SQLAlchemy raises StaleDataError here; JPA raises OptimisticLockException. Catch it and retry.")

    section("7. Pessimistic locking: take the write lock before reading")
    path = new_shared_db()
    alice, bob = connect(path), connect(path)
    alice.execute("BEGIN IMMEDIATE")                  # SQLite's write lock; Postgres/MySQL: SELECT ... FOR UPDATE
    alice.execute("SELECT stock FROM product WHERE id = 1")
    try:
        bob.execute("BEGIN IMMEDIATE")
        print("  Bob got the lock too (unexpected)")
    except sqlite3.OperationalError as e:
        print(f"  Bob tries to lock the same data: {e} (he waits, then times out)")
    alice.execute("UPDATE product SET stock = stock - 3 WHERE id = 1")
    alice.execute("COMMIT")
    bob.execute("BEGIN IMMEDIATE")
    bob.execute("UPDATE product SET stock = stock - 2 WHERE id = 1")
    bob.execute("COMMIT")
    print(f"  after Alice commits, Bob goes: stock = {stock(path)[0]}")
    print("  Optimistic: cheap when conflicts are rare, retries when they happen (web forms, carts).")
    print("  Pessimistic: blocks others while you hold it; for hot rows with frequent conflicts. Keep it short.")
    print("  Simplest of all here: an atomic UPDATE ... SET stock = stock - 2 WHERE stock >= 2.")

    section("8. Isolation levels in one table (Postgres / MySQL InnoDB)")
    print("  READ UNCOMMITTED : dirty reads possible (Postgres treats it as READ COMMITTED)")
    print("  READ COMMITTED   : no dirty reads; a row can change between two reads (Postgres default)")
    print("  REPEATABLE READ  : one snapshot per transaction (MySQL InnoDB default). Read-modify-write:")
    print("                     MySQL still LOSES the update; Postgres aborts the second writer with a")
    print("                     serialization error you must retry")
    print("  SERIALIZABLE     : as if one at a time; the database aborts conflicts and you must RETRY")
    print("  SQLite (this file) is serializable: one writer at a time, which is why section 7 times out.")
    print("  SQLAlchemy: create_engine(url, isolation_level='REPEATABLE READ'); Spring: @Transactional(isolation=...).")


def cleanup():
    for item in OPENED:
        if isinstance(item, sqlite3.Connection):
            item.close()
    for item in OPENED:
        if isinstance(item, str):
            shutil.rmtree(item, ignore_errors=True)


if __name__ == "__main__":
    try:
        main()
    finally:
        cleanup()


# EXERCISE 1: write a test helper `assert_max_queries(conn, n)` (a context manager around QueryCounter)
#             and use it to fail a test that introduces an N+1.
# EXERCISE 2: make the optimistic retry a loop with a maximum number of attempts. What should the API
#             return to the user when it gives up? (Hint: 409 Conflict.)
