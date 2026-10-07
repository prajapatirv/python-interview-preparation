"""
Airflow part 1 -- the KEYWORDS and the OPERATORS. The two things you will be asked to name.

  "Walk me through a DAG file."           -> the DAG(...) keywords, section 1
  "Which operators have you used?"        -> section 3, and WHY each one exists
  "How do you express dependencies?"      -> section 4 (>>, chain, cross_downstream)
  "What is an Operator vs a Task vs a Task Instance?" -> section 2, and get this right

Runs with ZERO dependencies: `_mini_airflow.py` in this folder reimplements the Airflow API shape
(DAG, operators, >>, trigger rules, XComs, a scheduler) in ~400 lines of stdlib. The code you
write here is the code you would write against real Airflow.

Run me: python 01_dag_anatomy_and_operators.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))      # so this file runs from ANY directory
from _mini_airflow import (                          # noqa: E402
    DAG, BaseSensorOperator, BashOperator, BranchPythonOperator, EmptyOperator, Executor,
    PythonOperator, ShortCircuitOperator, TriggerDagRunOperator, TriggerRule, chain,
    cross_downstream, scheduled_runs, summarise,
)


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ 1. the DAG keywords
section("1. the DAG(...) keywords -- the ones you must be able to name and justify")

DAG_KEYWORDS = [
    ("dag_id", "unique across the whole deployment",
     "the primary key. Renaming it creates a NEW dag and ORPHANS all history."),
    ("schedule", "cron / timedelta / preset / list of Assets / None",
     "`None` = triggered only manually or by another DAG. Replaced `schedule_interval` in 2.4."),
    ("start_date", "a FIXED datetime, never datetime.now()",
     "datetime.now() makes the first interval move every time the file is parsed -> the DAG may "
     "never run. Hardcode it."),
    ("end_date", "optional stop date",
     "rarely used; prefer pausing the DAG."),
    ("catchup", "True = backfill every missed interval since start_date",
     "THE footgun: start_date a year ago + catchup=True + @hourly = 8,760 runs queued at once. "
     "Set it explicitly, always."),
    ("default_args", "dict applied to EVERY task unless the task overrides it",
     "where retries / retry_delay / owner / on_failure_callback belong, so you write them once."),
    ("max_active_runs", "how many runs of THIS dag may be in flight",
     "set it to 1 whenever runs share mutable state (a target table, a cursor)."),
    ("max_active_tasks", "task-level parallelism within the dag (was `concurrency`)",
     "protects a downstream DB from your own fan-out."),
    ("dagrun_timeout", "kill a run that overruns",
     "stops a stuck run blocking the next one when max_active_runs=1."),
    ("tags", "list of strings for filtering in the UI",
     "free, and the first thing you want at 200 DAGs."),
    ("params", "dict of run-time parameters, overridable when triggering",
     "reachable as {{ params.x }}; the clean alternative to editing the file."),
    ("doc_md", "markdown shown on the DAG page in the UI",
     "put the runbook here: what it does, who owns it, what to do when it fails."),
]
for name, what, why in DAG_KEYWORDS:
    print(f"\n  {name}")
    print(f"    what : {what}")
    print(f"    why  : {why}")


# ================================================================ 2. operator vs task vs TI
section("2. Operator vs Task vs Task Instance -- a definition question that trips people up")
print("""  OPERATOR       a CLASS -- a template for a unit of work. `PythonOperator`, `BashOperator`.
  TASK           an INSTANCE of an operator inside a DAG -- i.e. a node in the graph.
                 `PythonOperator(task_id="extract", ...)` is a task.
  TASK INSTANCE  a specific (task, dag_run) pair -- the thing that actually has a STATE, a
                 try_number and logs. One task becomes many task instances over time, one per run.

  So: you RETRY a task instance, not a task. You CLEAR a task instance to make it re-run. The
  red/green boxes in the UI grid are task instances, and each column is one DAG run.

  Three operator families, which is the useful way to answer "which operators have you used?":
    ACTION     does something            PythonOperator, BashOperator, SQLExecuteQueryOperator
    TRANSFER   moves data A -> B         S3ToRedshiftOperator, GCSToBigQueryOperator
    SENSOR     waits for a condition     S3KeySensor, ExternalTaskSensor, SqlSensor

  And HOOKS are not operators: a hook wraps a CONNECTION (S3Hook, PostgresHook). Operators use
  hooks. When no operator fits, you write a PythonOperator that uses a hook -- that is the normal
  escape hatch, not a failure.""")


# ================================================================ 3. the operators
section("3. a realistic DAG, using the operators you should be able to name")


def extract_orders(data_interval_start, data_interval_end, **context):
    """A real extract is ALWAYS scoped to the data interval, never to `now` -- that is what makes
    the task idempotent and backfillable. See 02_scheduling_backfill_and_data_intervals.py."""
    print(f"         SELECT * FROM orders "
          f"WHERE created_at >= '{data_interval_start}' AND created_at < '{data_interval_end}'")
    return {"rows": 1_250, "window": str(data_interval_start.date())}


def validate_orders(ti, **context):
    extracted = ti.xcom_pull(task_ids="extract_orders")
    if extracted["rows"] == 0:
        raise ValueError("no rows extracted -- upstream is broken")
    return extracted["rows"]


def choose_load_path(ti, **context):
    """A BranchPythonOperator returns the task_id(s) to FOLLOW; the rest are skipped."""
    rows = ti.xcom_pull(task_ids="validate_orders")
    return "load_bulk" if rows > 1_000 else "load_incremental"


def load(mode, **context):
    print(f"         COPY orders FROM s3://... ({mode})")
    return mode


def publish_metrics(**context):
    return "metrics published"


def alert_oncall(**context):
    print("         PagerDuty: orders pipeline failed")
    return "alerted"


with DAG(
    dag_id="orders_etl",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,                                  # explicit, always
    max_active_runs=1,                              # runs share a target table
    tags=["orders", "etl", "team-data"],
    params={"warehouse": "analytics"},
    description="Daily orders extract -> validate -> load -> publish",
    default_args={                                  # applied to EVERY task below
        "owner": "data-platform",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
) as orders_etl:

    start = EmptyOperator(task_id="start")          # was DummyOperator pre-2.4: a graph marker

    wait_for_file = BaseSensorOperator(             # stands in for S3KeySensor
        task_id="wait_for_dump",
        poke_fn=lambda ctx: True,                   # pretend the file has landed
        mode="reschedule",                          # frees the worker slot between pokes
        poke_interval=60,
        timeout=60 * 60 * 4,
    )

    extract = PythonOperator(
        task_id="extract_orders",
        python_callable=extract_orders,
    )

    validate = PythonOperator(
        task_id="validate_orders",
        python_callable=validate_orders,
        retries=0,                                  # OVERRIDES default_args: bad data won't fix itself
    )

    branch = BranchPythonOperator(
        task_id="choose_load_path",
        python_callable=choose_load_path,
    )

    load_bulk = PythonOperator(task_id="load_bulk", python_callable=load,
                               op_kwargs={"mode": "bulk COPY"})
    load_incremental = PythonOperator(task_id="load_incremental", python_callable=load,
                                      op_kwargs={"mode": "row-by-row MERGE"})

    # the JOIN after a branch MUST relax its trigger rule, or the skipped branch skips it too
    join = EmptyOperator(task_id="join_after_branch",
                         trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)

    refresh_views = BashOperator(
        task_id="refresh_views",
        bash_command="dbt run --select orders+ --vars 'run_date: {{ ds }}'",
    )

    metrics = PythonOperator(task_id="publish_metrics", python_callable=publish_metrics)

    trigger_downstream = TriggerDagRunOperator(
        task_id="trigger_reporting_dag",
        trigger_dag_id="daily_reporting",
        conf={"upstream_run": "{{ run_id }}"},
    )

    on_failure = PythonOperator(
        task_id="alert_oncall",
        python_callable=alert_oncall,
        trigger_rule=TriggerRule.ONE_FAILED,        # runs ONLY if something upstream failed
    )

    end = EmptyOperator(task_id="end", trigger_rule=TriggerRule.ALL_DONE)   # always runs

    # ---------------------------------------------------------- 4. dependencies
    start >> wait_for_file >> extract >> validate >> branch
    branch >> [load_bulk, load_incremental] >> join       # fan out, then fan in
    join >> refresh_views >> metrics >> trigger_downstream >> end
    [extract, validate, refresh_views] >> on_failure      # alerting edge
    on_failure >> end

print(f"  {orders_etl}")
print(f"  tasks in topological order, with their downstream edges:\n{orders_etl.structure()}")


# ================================================================ 4. dependency syntax
section("4. the four ways to wire dependencies -- and when each reads better")
print("""  a >> b                      a runs, then b.  (`a.set_downstream(b)`)
  b << a                      the same edge, written the other way. Pick ONE direction per file.
  a >> [b, c] >> d            fan out to b and c, then fan in to d. The idiom you use most.
  chain(a, b, c, d)           a >> b >> c >> d, without the operator noise
  chain(a, [b, c], [d, e], f) pairwise: b>>d and c>>e -- NOT a mesh. Lists must be equal length.
  cross_downstream([a,b],[c,d])  a FULL MESH: a>>c, a>>d, b>>c, b>>d

  The one that surprises people: `a >> [b, c] >> d` works in two steps. `a >> [b, c]` returns the
  LIST (because `>>` returns its right operand), and then `[list] >> d` has no `list.__rshift__`,
  so Python falls back to `d.__rrshift__([b, c])` -- which BaseOperator defines for exactly this.""")

with DAG("dependency_syntax", schedule=None, start_date=datetime(2026, 1, 1)) as demo:
    a, b, c, d, e, f = (EmptyOperator(task_id=n) for n in "abcdef")
    chain(a, [b, c], [d, e], f)                 # pairwise: b>>d, c>>e
print(f"  chain(a, [b, c], [d, e], f) gives pairwise edges:\n{demo.structure()}")

with DAG("mesh_syntax", schedule=None, start_date=datetime(2026, 1, 1)) as mesh:
    e1, e2 = EmptyOperator(task_id="extract_a"), EmptyOperator(task_id="extract_b")
    t1, t2 = EmptyOperator(task_id="transform_x"), EmptyOperator(task_id="transform_y")
    cross_downstream([e1, e2], [t1, t2])
print(f"  cross_downstream gives a full mesh:\n{mesh.structure()}")


# ================================================================ 5. the cycle check
section("5. the 'A' in DAG: a cycle is rejected, and this is where")
with DAG("cyclic", schedule=None, start_date=datetime(2026, 1, 1)) as bad:
    x = EmptyOperator(task_id="x")
    y = EmptyOperator(task_id="y")
    z = EmptyOperator(task_id="z")
    x >> y >> z >> x                            # z back to x -- a cycle
try:
    bad.topological_order()
except ValueError as exc:
    print(f"  {exc}")
print("  real Airflow raises AirflowDagCycleException when the file is parsed, so the DAG never")
print("  appears in the UI -- which is why a cycle is a deploy-time error, not a runtime one.")


# ================================================================ 6. run it
section("6. executing one DAG run -- the happy path")
run = scheduled_runs(orders_etl, now=datetime(2026, 3, 2))[0]
print(f"  logical_date        = {run.logical_date}")
print(f"  data_interval       = [{run.data_interval_start}, {run.data_interval_end})")
print(f"  ...so it is triggered only after {run.would_start_after} -- see file 02\n")
executor = Executor()
executor.run(orders_etl, run)
print(f"\n  {summarise(run)}")
print("  note `alert_oncall` was SKIPPED (trigger_rule=one_failed, nothing failed) and `end` still")
print("  ran (trigger_rule=all_done). `load_incremental` was skipped by the branch.")


# ================================================================ 7. the failure path
section("7. the same DAG when validation fails -- watch the states propagate")
run2 = scheduled_runs(orders_etl, now=datetime(2026, 3, 3))[0]
run2.run_id = "scheduled__2026-03-02T00:00:00--failing"
Executor().run(orders_etl, run2, fail_tasks={"validate_orders"})
print(f"\n  {summarise(run2)}")
print("""  read the states: validate FAILED (retries=0, because we overrode default_args), everything
  after it is UPSTREAM_FAILED, `alert_oncall` RAN because its trigger_rule is one_failed, and
  `end` RAN because its trigger_rule is all_done. That combination -- alert on one_failed,
  cleanup on all_done -- is the standard production shape.""")


# ================================================================ 8. ShortCircuitOperator
section("8. ShortCircuitOperator: skip everything downstream when there is nothing to do")


def any_new_files(**context):
    return False                                 # pretend the source dropped nothing today


with DAG("short_circuit_demo", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as sc_dag:
    check = ShortCircuitOperator(task_id="any_new_files", python_callable=any_new_files)
    process = PythonOperator(task_id="process", python_callable=lambda: "processed")
    notify = PythonOperator(task_id="notify", python_callable=lambda: "notified")
    check >> process >> notify

sc_run = scheduled_runs(sc_dag, now=datetime(2026, 1, 3))[0]
Executor().run(sc_dag, sc_run)
print(f"\n  {summarise(sc_run)}")
print("  a falsy return skips the WHOLE downstream subtree -- better than raising, because a")
print("  skipped run is green in the UI and 'nothing to do' is not a failure.")


# ================================================================ 9. the top-level code rule
section("9. the single most important practical rule: NO EXPENSIVE TOP-LEVEL CODE")
print("""  The scheduler re-PARSES every DAG file on a loop (`min_file_process_interval`, default 30s).
  Anything at module level therefore runs every ~30 seconds, forever, on the scheduler -- not
  once per run.

  WRONG -- runs every 30s on the scheduler, for every DAG file:
      rows = psycopg.connect(DSN).execute("SELECT ...").fetchall()   # a query, at import
      config = requests.get("https://config/api").json()             # a network call, at import
      for customer in rows:                                          # dynamic DAG from a query
          PythonOperator(task_id=f"load_{customer}", ...)

  RIGHT -- the work moves INSIDE a task, so it runs once per run, on a worker:
      def load(**context):
          rows = psycopg.connect(DSN).execute("SELECT ...").fetchall()
      PythonOperator(task_id="load", python_callable=load)
  ...and for a variable number of tasks, use DYNAMIC TASK MAPPING (file 03), which decides the
  count at RUN time from an XCom rather than at PARSE time from a database.

  Symptoms of getting it wrong: the scheduler lags, the UI is slow, DAGs appear and vanish, and
  `dag_processing.last_duration` climbs. It is the #1 cause of 'our Airflow is slow'.

  Also avoid at top level: `datetime.now()` in start_date, Variable.get() (one DB hit per parse --
  use `{{ var.value.x }}` templating instead, which resolves at run time), and heavy imports.""")

# EXPERIMENT 1: remove `trigger_rule=NONE_FAILED_MIN_ONE_SUCCESS` from `join` and re-run section 6.
# The branch skip now cascades and the whole tail of the DAG is skipped. That one keyword is the
# difference between a working branch and a silently dead pipeline.
# EXPERIMENT 2: change `end`'s trigger rule to the default ALL_SUCCESS and re-run section 7.
# Your cleanup task no longer runs on failure -- which is exactly when you needed it.
# EXPERIMENT 3: give `validate` back the inherited `retries=3` (delete the override) and re-run
# section 7. Count the attempts, and decide whether retrying a validation error is ever right.
# EXPERIMENT 4: add a second task with task_id="extract_orders" and read the ValueError. Duplicate
# task_ids are a real mistake when tasks are generated in a loop.
# EXPERIMENT 5: in section 8, make `any_new_files` return True and compare the states.

# EXERCISE: write a DAG `customer_sync` that:
#   - runs hourly, catchup=False, max_active_runs=1, tagged ["crm", "team-data"]
#   - default_args give every task 2 retries with a 2-minute delay and an owner
#   - waits for an API to be reachable with a sensor in mode="reschedule"
#   - extracts scoped to the DATA INTERVAL (not now()), then validates
#   - branches on row count: full refresh vs incremental
#   - joins with the correct trigger rule, then triggers a downstream DAG
#   - has an alerting task on one_failed and a cleanup task on all_done
# Then run it twice -- once clean, once with the extract failing -- and read every state.
