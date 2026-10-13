"""
01 - SQL interview queries, executed and checked (SQLite, Python stdlib only)

Run:  py 01_sql_interview_queries_sqlite.py

Interview angle: top-N and top-N-per-group (students by percentage / category), ties (ROW_NUMBER vs
RANK vs DENSE_RANK), Nth highest, gaps and islands, moving average, running total, month-over-month
with LAG, de-duplication, correlated subquery vs window, NOT IN with NULL, SARGability and index use.

SQLite supports window functions (3.25+), CTEs and EXPLAIN QUERY PLAN, so the SQL below is the same
shape you would write on PostgreSQL / SQL Server / Oracle. Dialect differences are noted inline.
Output is ASCII only (stdout may be redirected on Windows).
"""
import sqlite3

CHECKS = 0


def section(title):
    print("\n=== " + title + " ===")


def check(label, expected, actual):
    global CHECKS
    CHECKS += 1
    if expected != actual:
        raise AssertionError(f"{label}: expected {expected!r} but got {actual!r}")
    print(f"  ok  {label} -> {actual}")


db = sqlite3.connect(":memory:")
q = lambda sql, *a: db.execute(sql, a).fetchall()

db.executescript("""
CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, category TEXT, percentage REAL);
INSERT INTO students VALUES
 (1,'Asha','Science',92.5),(2,'Bala','Science',88.0),(3,'Chen','Science',92.5),(4,'Divya','Science',75.0),
 (5,'Eli','Commerce',81.0),(6,'Farah','Commerce',95.0),(7,'Gita','Commerce',81.0),(8,'Hari','Commerce',60.0),
 (9,'Isha','Arts',70.0),(10,'Jay','Arts',85.0),(11,'Kiran','Arts',85.0);

CREATE TABLE employees (id INTEGER PRIMARY KEY, name TEXT, dept TEXT, salary INTEGER, manager_id INTEGER);
INSERT INTO employees VALUES
 (1,'Meera','ENG',200,NULL),(2,'Nikhil','ENG',150,1),(3,'Om','ENG',150,1),(4,'Pooja','ENG',100,2),
 (5,'Ravi','HR',90,1),(6,'Sana','HR',70,5),(7,'Tara','OPS',120,1);

CREATE TABLE server_logs (status_date TEXT, status TEXT);
INSERT INTO server_logs VALUES
 ('2026-01-01','Active'),('2026-01-02','Active'),('2026-01-03','Active'),
 ('2026-01-04','Down'),
 ('2026-01-05','Active'),('2026-01-06','Active'),
 ('2026-01-07','Down'),
 ('2026-01-08','Active');

CREATE TABLE daily_sales (order_date TEXT, daily_sales INTEGER);
INSERT INTO daily_sales VALUES
 ('2026-02-01',10),('2026-02-02',20),('2026-02-03',30),('2026-02-04',40),
 ('2026-02-05',50),('2026-02-06',60),('2026-02-07',70),('2026-02-08',80);

CREATE TABLE client_logs (entry_id INTEGER PRIMARY KEY, client_id INTEGER, log_timestamp TEXT);
INSERT INTO client_logs VALUES
 (1,100,'t1'),(2,100,'t1'),(3,100,'t2'),(4,200,'t1'),(5,200,'t1'),(6,200,'t1'),(7,300,'t9');

CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, amount INTEGER, order_date TEXT);
INSERT INTO orders VALUES
 (1,1,100,'2026-01-10'),(2,1,150,'2026-01-25'),(3,2,200,'2026-02-03'),
 (4,1,50,'2026-02-14'),(5,3,300,'2026-03-01'),(6,2,100,'2026-03-20');
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT);
INSERT INTO customers VALUES (1,'C1'),(2,'C2'),(3,'C3'),(4,'C4-never-ordered');
""")

# ---------------------------------------------------------------------------------------------
section("1. Top N students: overall, per category, and the ties question")
check("top 3 overall (LIMIT cuts ties arbitrarily: Asha/Chen tie, Bala is 4th)",
      ["Farah", "Asha", "Chen"],
      [r[0] for r in q("SELECT name FROM students ORDER BY percentage DESC, name LIMIT 3")])

# DENSE_RANK keeps everyone who ties for a place: "top 3 percentages", not "3 rows".
rows = q("""SELECT name, percentage FROM (
              SELECT name, percentage, DENSE_RANK() OVER (ORDER BY percentage DESC) AS r FROM students)
            WHERE r <= 3 ORDER BY percentage DESC, name""")
check("top 3 DISTINCT percentages incl. ties (DENSE_RANK)",
      ["Farah", "Asha", "Chen", "Bala"], [r[0] for r in rows])

per_cat = q("""SELECT category, name, percentage, rn FROM (
                 SELECT category, name, percentage,
                        ROW_NUMBER() OVER (PARTITION BY category ORDER BY percentage DESC, name) AS rn
                 FROM students)
               WHERE rn <= 3 ORDER BY category, rn""")
check("top 3 PER CATEGORY (ROW_NUMBER, exactly 3 rows each)", 9, len(per_cat))
check("Science top 3 in order", ["Asha", "Chen", "Bala"], [r[1] for r in per_cat if r[0] == "Science"])

topper = q("""SELECT category, name FROM (
                SELECT category, name, RANK() OVER (PARTITION BY category ORDER BY percentage DESC) AS r
                FROM students) WHERE r = 1 ORDER BY category, name""")
check("topper(s) per category with RANK (ties both returned)",
      [("Arts", "Jay"), ("Arts", "Kiran"), ("Commerce", "Farah"), ("Science", "Asha"), ("Science", "Chen")], topper)

# Portable "no window function" version: correlated subquery.
legacy = q("""SELECT s.category, s.name FROM students s
              WHERE (SELECT COUNT(DISTINCT percentage) FROM students x
                     WHERE x.category = s.category AND x.percentage > s.percentage) < 1
              ORDER BY s.category, s.name""")
check("same answer without window functions (correlated COUNT)", topper, legacy)

check("2nd highest percentage overall (DISTINCT, NULL-safe)", 92.5,
      q("SELECT MAX(percentage) FROM students WHERE percentage < (SELECT MAX(percentage) FROM students)")[0][0])
check("Nth highest via OFFSET (N=3 -> 88.0)", 88.0,
      q("SELECT DISTINCT percentage FROM students ORDER BY percentage DESC LIMIT 1 OFFSET 2")[0][0])
check("students above THEIR category average", ["Asha", "Bala", "Chen", "Eli", "Farah", "Gita", "Jay", "Kiran"],
      sorted(r[0] for r in q("""SELECT name FROM (
                                  SELECT name, percentage, AVG(percentage) OVER (PARTITION BY category) AS avg_cat
                                  FROM students) WHERE percentage > avg_cat""")))
check("category summary: count / avg / max", ("Arts", 3, 80.0, 85.0),
      q("""SELECT category, COUNT(*), ROUND(AVG(percentage),1), MAX(percentage)
           FROM students GROUP BY category HAVING COUNT(*) >= 3 ORDER BY category""")[0])
check("percent rank bucket with CASE", {"Distinction": 6, "First": 4, "Pass": 1},
      dict(q("""SELECT grade, COUNT(*) FROM (
                  SELECT CASE WHEN percentage >= 85 THEN 'Distinction'
                              WHEN percentage >= 70 THEN 'First' ELSE 'Pass' END AS grade FROM students)
                GROUP BY grade""")))

# ---------------------------------------------------------------------------------------------
section("2. Gaps and islands (continuous Active periods)")
islands = q("""WITH numbered AS (
                 SELECT status_date,
                        julianday(status_date) - ROW_NUMBER() OVER (ORDER BY status_date) AS island_id
                 FROM server_logs WHERE status = 'Active')
               SELECT MIN(status_date), MAX(status_date), COUNT(*) FROM numbered
               GROUP BY island_id ORDER BY 1""")
check("islands = date minus row_number is constant inside an island",
      [("2026-01-01", "2026-01-03", 3), ("2026-01-05", "2026-01-06", 2), ("2026-01-08", "2026-01-08", 1)], islands)
check("longest island", 3, max(r[2] for r in islands))

# ---------------------------------------------------------------------------------------------
section("3. Window frames: moving average, running total, month-over-month")
mov = q("""SELECT order_date, AVG(daily_sales) OVER (ORDER BY order_date
                                                   ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)
           FROM daily_sales ORDER BY order_date""")
check("7-day moving average keeps every row", 8, len(mov))
check("first row averages only itself (partial window)", 10.0, mov[0][1])
check("7th row averages 7 values", 40.0, mov[6][1])
check("8th row slides the window", 50.0, mov[7][1])
run = q("""SELECT order_date, SUM(daily_sales) OVER (ORDER BY order_date) FROM daily_sales ORDER BY 1""")
check("running total last row", 360, run[-1][1])

mom = q("""WITH m AS (SELECT substr(order_date,1,7) AS month, SUM(amount) AS total FROM orders GROUP BY 1)
           SELECT month, total, total - LAG(total) OVER (ORDER BY month) AS change FROM m ORDER BY month""")
check("month-over-month with LAG (first month has NULL change)",
      [("2026-01", 250, None), ("2026-02", 250, 0), ("2026-03", 400, 150)], mom)

# ---------------------------------------------------------------------------------------------
section("4. De-duplication")
q("""WITH d AS (SELECT entry_id, ROW_NUMBER() OVER (PARTITION BY client_id, log_timestamp ORDER BY entry_id) AS rk
                FROM client_logs)
     DELETE FROM client_logs WHERE entry_id IN (SELECT entry_id FROM d WHERE rk > 1)""")
check("kept the lowest entry_id of every duplicate group", [1, 3, 4, 7],
      [r[0] for r in q("SELECT entry_id FROM client_logs ORDER BY 1")])

# ---------------------------------------------------------------------------------------------
section("5. Correlated subquery vs window function vs join")
corr = q("""SELECT name FROM employees e
            WHERE salary > (SELECT AVG(salary) FROM employees x WHERE x.dept = e.dept) ORDER BY name""")
win = q("""SELECT name FROM (SELECT name, salary, AVG(salary) OVER (PARTITION BY dept) AS a FROM employees)
           WHERE salary > a ORDER BY name""")
joined = q("""SELECT e.name FROM employees e JOIN (SELECT dept, AVG(salary) a FROM employees GROUP BY dept) d
              ON d.dept = e.dept WHERE e.salary > d.a ORDER BY e.name""")
check("correlated == window == join result", True, corr == win == joined)
check("who earns above their dept average", ["Meera", "Ravi"], [r[0] for r in win])
check("self join: employee with manager name", ("Nikhil", "Meera"),
      q("""SELECT e.name, m.name FROM employees e LEFT JOIN employees m ON m.id = e.manager_id
           WHERE e.id = 2""")[0])
check("top earner per dept via window", ["Meera", "Ravi", "Tara"],
      [r[0] for r in q("""SELECT name FROM (SELECT name, ROW_NUMBER() OVER
                          (PARTITION BY dept ORDER BY salary DESC, name) rn FROM employees)
                          WHERE rn = 1 ORDER BY name""")])

# ---------------------------------------------------------------------------------------------
section("6. NULL traps: NOT IN versus NOT EXISTS, LEFT JOIN anti-join")
db.execute("CREATE TABLE blocked (customer_id INTEGER)")
db.executemany("INSERT INTO blocked VALUES (?)", [(1,), (None,)])
check("NOT IN with a NULL in the list returns NOTHING", [],
      q("SELECT name FROM customers WHERE id NOT IN (SELECT customer_id FROM blocked)"))
check("NOT EXISTS ignores the NULL and is correct", ["C2", "C3", "C4-never-ordered"],
      [r[0] for r in q("""SELECT name FROM customers c
                          WHERE NOT EXISTS (SELECT 1 FROM blocked b WHERE b.customer_id = c.id) ORDER BY id""")])
check("customers who never ordered (LEFT JOIN ... IS NULL)", ["C4-never-ordered"],
      [r[0] for r in q("""SELECT c.name FROM customers c LEFT JOIN orders o ON o.customer_id = c.id
                          WHERE o.order_id IS NULL""")])
check("COUNT(*) vs COUNT(col) with NULLs", (7, 6),
      q("SELECT COUNT(*), COUNT(manager_id) FROM employees")[0])

# ---------------------------------------------------------------------------------------------
section("7. Performance: SARGability and index use (EXPLAIN QUERY PLAN)")
db.execute("CREATE TABLE txn (id INTEGER PRIMARY KEY, txn_date TEXT, amount INTEGER)")
db.executemany("INSERT INTO txn (txn_date, amount) VALUES (?, ?)",
               [(f"2025-{m:02d}-{d:02d}", m * d) for m in range(1, 13) for d in range(1, 28)])
db.execute("CREATE INDEX idx_txn_date ON txn(txn_date)")


def plan(sql):
    return " ".join(r[3] for r in db.execute("EXPLAIN QUERY PLAN " + sql))


p_func = plan("SELECT * FROM txn WHERE strftime('%Y', txn_date) = '2025'")
p_range = plan("SELECT * FROM txn WHERE txn_date >= '2025-01-01' AND txn_date < '2026-01-01'")
check("function on the indexed column forces a scan", True, "SCAN" in p_func and "idx_txn_date" not in p_func)
check("range predicate on the bare column uses the index", True, "SEARCH" in p_range and "idx_txn_date" in p_range)
p_cover = plan("SELECT txn_date FROM txn WHERE txn_date >= '2025-06-01'")
check("covering index: answered from the index alone", True, "COVERING INDEX" in p_cover)
p_lead = plan("SELECT * FROM txn WHERE amount = 5")
check("no index on amount: full scan", True, "SCAN" in p_lead)

print(f"\nAll {CHECKS} checks passed.")
