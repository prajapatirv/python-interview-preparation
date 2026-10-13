"""
Airflow part 4 -- FAILURE HANDLING, which is what the job actually is.

  "A task failed at 3am. Walk me through it."     -> sections 1-3
  "Explain trigger rules."                        -> section 2, with every rule executed
  "How do you alert?"                             -> section 4 (callbacks, SLAs)
  "A sensor is blocking all your workers. Why?"   -> section 5 (poke vs reschedule vs deferrable)
  "How do you stop Airflow killing the database?" -> section 6 (pools)
  "How do you test a DAG?"                        -> section 7

Run me: python 04_failures_retries_and_trigger_rules.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mini_airflow import (                      # noqa: E402
    DAG, BaseSensorOperator, EmptyOperator, Executor, PythonOperator, State, TriggerRule,
    evaluate_trigger_rule, scheduled_runs, summarise,
)


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ 1. retries
section("1. retries -- the keywords, and what they do NOT fix")
print("""  On the task (usually via the DAG's default_args, so you write it once):
      retries=3                              how many extra attempts
      retry_delay=timedelta(minutes=5)       wait between attempts
      retry_exponential_backoff=True         5m, 10m, 20m, 40m... instead of a flat 5m
      max_retry_delay=timedelta(hours=1)     cap the growth
      execution_timeout=timedelta(minutes=30) kill a task that hangs -- WITHOUT this, a wedged
                                              task holds its slot until a human notices

  What retries DO fix: a transient failure -- a network blip, a database failover, a 503, a
  rate limit, a spot instance reclaimed.

  What retries do NOT fix, and this is the part to say out loud:
      - BAD DATA. Retrying a validation error three times just fails three times, 15 minutes
        apart, and delays the alert. Set retries=0 on validation.
      - A BUG. Same.
      - A NON-IDEMPOTENT TASK. Here retries make things WORSE: attempt 1 inserted 10,000 rows and
        then timed out; attempt 2 inserts them again. Retries are only safe because the task is
        idempotent -- which is the same argument as file 02.

  So: retries are for transient failures, idempotency is the precondition, and
  `execution_timeout` is what makes "hung" become "failed" so the retry can even happen.""")


def flaky_api(**context):
    """Fails twice, then succeeds -- the classic transient failure."""
    return "fetched 1,200 records"


def bad_data(**context):
    raise ValueError("column `amount` is null in 412 rows")


with DAG("retry_demo", schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False,
         default_args={"retries": 3, "retry_delay": timedelta(minutes=5)}) as retry_dag:
    fetch = PythonOperator(task_id="fetch_from_api", python_callable=flaky_api)
    validate = PythonOperator(task_id="validate", python_callable=bad_data,
                              retries=0)       # bad data will not fix itself
    fetch >> validate

run = scheduled_runs(retry_dag, now=datetime(2026, 1, 5))[0]
Executor().run(retry_dag, run, flaky_tasks={"fetch_from_api": 2})
print(f"\n  {summarise(run)}")
ti = run.task_instances["fetch_from_api"]
print(f"  fetch_from_api: {ti.try_number} attempts, waits of "
      f"{[int(d.total_seconds()) for d in ti.recorded_sleeps]}s")
print("  validate failed on attempt 1 because we set retries=0 -- the alert fires immediately")
print("  instead of 15 minutes later. That is a deliberate choice, not an oversight.")


# ================================================================ 2. trigger rules
section("2. trigger rules -- every rule, evaluated")
print("  given two upstream tasks, which combinations let the downstream task run?\n")
combos = [
    ("2 success", [State.SUCCESS, State.SUCCESS]),
    ("1 failed", [State.SUCCESS, State.FAILED]),
    ("2 failed", [State.FAILED, State.FAILED]),
    ("1 skipped", [State.SUCCESS, State.SKIPPED]),
    ("2 skipped", [State.SKIPPED, State.SKIPPED]),
]
rules = [TriggerRule.ALL_SUCCESS, TriggerRule.ALL_DONE, TriggerRule.ALL_FAILED,
         TriggerRule.ONE_SUCCESS, TriggerRule.ONE_FAILED,
         TriggerRule.NONE_FAILED, TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
         TriggerRule.NONE_SKIPPED, TriggerRule.ALL_SKIPPED, TriggerRule.ALWAYS]

header = "  " + " " * 31 + "".join(f"{label:>17s}" for label, _ in combos)
print(header)
for rule in rules:
    cells = []
    for _, states in combos:
        should_run, blocked = evaluate_trigger_rule(rule, states)
        cells.append("RUN" if should_run else blocked)
    print(f"  {rule:29s}" + "".join(f"{c:>17s}" for c in cells))

print("""
  The four that matter in practice:
    ALL_SUCCESS (default)          the normal case. A failed or skipped upstream stops you --
                                   note that a SKIP cascades, which is the branch trap.
    ALL_DONE                       CLEANUP / teardown. Runs whatever happened upstream. Use it
                                   for "release the lock", "drop the temp table", "close the run".
    ONE_FAILED                     ALERTING. Runs as soon as any upstream fails, without waiting
                                   for the others to finish.
    NONE_FAILED_MIN_ONE_SUCCESS    the JOIN after a branch. Tolerates the skipped branch but
                                   still refuses to run if something actually failed.
                                   (It replaced the old `none_failed_or_skipped`.)

  The trap to name: ALL_DONE on a task means a FAILED upstream does not stop it -- so if that task
  publishes results, you will publish on top of a broken upstream. ALL_DONE is for cleanup, not
  for "carry on regardless".""")


# ================================================================ 3. the failure shapes
section("3. the standard production shape: alert on one_failed, clean up on all_done")


def cleanup(**context):
    return "dropped staging table, released lock"


def alert(**context):
    return "paged #data-oncall"


with DAG("failure_shape", schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False) as fs:
    begin = EmptyOperator(task_id="begin")
    stage = PythonOperator(task_id="stage_data", python_callable=lambda: "staged")
    transform = PythonOperator(task_id="transform", python_callable=lambda: "transformed")
    publish = PythonOperator(task_id="publish", python_callable=lambda: "published")
    alert_task = PythonOperator(task_id="alert_oncall", python_callable=alert,
                                trigger_rule=TriggerRule.ONE_FAILED)
    teardown = PythonOperator(task_id="cleanup", python_callable=cleanup,
                              trigger_rule=TriggerRule.ALL_DONE)
    begin >> stage >> transform >> publish
    [stage, transform, publish] >> alert_task
    [publish, alert_task] >> teardown

for label, failing in [("everything works", set()), ("transform fails", {"transform"})]:
    r = scheduled_runs(fs, now=datetime(2026, 1, 5))[0]
    r.run_id = f"run--{label.replace(' ', '_')}"
    print(f"\n  --- {label} ---")
    Executor().run(fs, r, fail_tasks=failing)
    print(f"  {summarise(r)}")
print("""
  Read both runs: `cleanup` ran in BOTH (all_done), `alert_oncall` ran only in the second
  (one_failed), and `publish` was correctly blocked as upstream_failed. The DAG run is marked
  FAILED even though cleanup and the alert succeeded -- which is right: the business outcome
  did not happen.""")


# ================================================================ 4. callbacks and SLAs
section("4. callbacks and SLAs -- how the alert actually leaves the building")

callback_log = []
with DAG("callback_demo", schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False,
         default_args={
             "retries": 1,
             "on_failure_callback": lambda ctx: callback_log.append(
                 f"FAILURE: {ctx['task'].task_id} run={ctx['run_id']}"),
             "on_retry_callback": lambda ctx: callback_log.append(
                 f"RETRY:   {ctx['task'].task_id} attempt={ctx['ti'].try_number}"),
             "on_success_callback": lambda ctx: callback_log.append(
                 f"SUCCESS: {ctx['task'].task_id}"),
         }) as cb_dag:
    ok = PythonOperator(task_id="ok_task", python_callable=lambda: "fine")
    doomed = PythonOperator(task_id="doomed_task", python_callable=lambda: "never gets here")
    ok >> doomed

cb_run = scheduled_runs(cb_dag, now=datetime(2026, 1, 5))[0]
Executor(verbose=False).run(cb_dag, cb_run, fail_tasks={"doomed_task"})
print("  the callbacks that fired, in order:")
for line in callback_log:
    print(f"    {line}")

print("""
  The callback keywords:
      on_success_callback / on_failure_callback / on_retry_callback   (task or default_args)
      on_execute_callback, on_skipped_callback                        (less used)
      sla_miss_callback                                              (DAG level)
      DAG-level: on_failure_callback fires when the RUN fails

  In production these call Slack/PagerDuty via a notifier. Prefer the built-in NOTIFIERS
  (`airflow.providers.slack.notifications.slack.SlackNotifier`) over a hand-rolled callback --
  they are reusable and testable.

  SLAs -- and be precise here, because the semantics surprise people:
      sla=timedelta(hours=2) on a task means "this task should be DONE within 2 hours OF THE DAG
      RUN'S DATA INTERVAL END", not 2 hours after the task started. A miss triggers
      sla_miss_callback and is recorded, but it does NOT fail or kill the task.
      There is no SLA on the DAG as a whole -- you put it on the last task.
      The implementation has historically been quirky (missed SLAs for skipped tasks, scheduler
      load), and Airflow 3 reworks this area -- so check what your version actually does.

  The pragmatic alternative many teams use: a `dagrun_timeout` plus an external freshness check on
  the OUTPUT ("is the table newer than 2 hours?"), because that measures what the customer cares
  about rather than what the orchestrator did. That is the same symptoms-not-causes argument as
  deep dive 28.""")


# ================================================================ 5. sensors
section("5. sensors -- the question is which MODE, and it is a resource question")
print("""  A sensor waits for a condition: a file lands, a partition appears, another DAG finishes.
  Keywords: poke_interval, timeout, mode, exponential_backoff, soft_fail, deferrable.

  mode="poke" (the DEFAULT)
      holds a worker slot for the ENTIRE wait. A 6-hour sensor occupies a slot for 6 hours.
      Ten of those on a 16-slot deployment and nothing else can run -- the classic
      "Airflow is stuck but nothing is running" incident, a SENSOR DEADLOCK.

  mode="reschedule"
      releases the slot between pokes: the task goes to `up_for_reschedule` and is re-queued
      after poke_interval. Costs a scheduler round trip per poke; use it whenever the wait is
      long (minutes+).

  deferrable=True  (+ the TRIGGERER process, 2.2+)
      the best option where a deferrable version exists (`S3KeySensorAsync`, or `deferrable=True`
      on modern operators). The task yields a TRIGGER to the async triggerer process; thousands
      of waits cost one process and no worker slots at all.

  Also:
      timeout         ALWAYS set it. Without one a sensor waits ~7 days by default.
      soft_fail=True  on timeout mark SKIPPED rather than FAILED -- "the file did not arrive, and
                      that is acceptable today" instead of a 3am page.
      exponential_backoff=True  widen the poke interval over time.

  And the design-level answer worth volunteering: if the thing you are waiting for is produced by
  ANOTHER AIRFLOW DAG, do not use a sensor at all -- use Assets/Datasets (file 03, section 7) so
  the consumer is TRIGGERED by the data instead of polling for it.""")

poke_count = {"n": 0}


def file_has_landed(context):
    poke_count["n"] += 1
    return poke_count["n"] >= 3          # lands on the third poke


with DAG("sensor_demo", schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False) as sd:
    waiter = BaseSensorOperator(task_id="wait_for_file", poke_fn=file_has_landed,
                                mode="reschedule", poke_interval=30, timeout=3600)
    consume = PythonOperator(task_id="process_file", python_callable=lambda: "processed")
    waiter >> consume

s_run = scheduled_runs(sd, now=datetime(2026, 1, 5))[0]
Executor().run(sd, s_run)
print(f"\n  the sensor poked {waiter.pokes} times before the condition was true")
print(f"  in mode={waiter.mode!r} the worker slot was released between each poke")

timeout_count = {"n": 0}
with DAG("sensor_timeout", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as st:
    never = BaseSensorOperator(task_id="wait_forever", poke_fn=lambda ctx: False,
                               mode="reschedule", poke_interval=600, timeout=1800)
    after = PythonOperator(task_id="never_runs", python_callable=lambda: "x")
    never >> after
t_run = scheduled_runs(st, now=datetime(2026, 1, 5))[0]
Executor().run(st, t_run)
print(f"\n  {summarise(t_run)}  <- the timeout is what turns 'waiting' into 'failed'")


# ================================================================ 6. pools and priority
section("6. pools -- the only control that protects a SHARED resource")
print("""  A pool is a named budget of slots, enforced ACROSS ALL DAGS:

      airflow pools set warehouse 5 "max 5 concurrent warehouse queries"
      PythonOperator(task_id="query", pool="warehouse", pool_slots=1, ...)

  Why it is the right answer to "how do you stop Airflow overwhelming the database": every other
  concurrency control (max_active_runs, max_active_tasks, max_active_tis_per_dag) is scoped to ONE
  DAG. Twelve DAGs each politely limited to 4 tasks still open 48 connections. A pool of 5 caps
  the TOTAL, whoever asks.

  Size it from the resource's budget, not from Airflow's: if the warehouse allows 20 connections
  and other services need 10, the pool is 10. That is the same connection-count arithmetic as
  deep dive 29.

  Related keywords:
      pool_slots=2        a heavy task can consume more than one slot
      priority_weight     who gets the next free slot when the pool is full (default 1;
                          `weight_rule` controls whether upstream tasks inherit it)
      parallelism         deployment-wide cap on running task instances (config, not per-DAG)

  And the failure mode to name: a POOL DEADLOCK. Sensors in mode="poke" sitting in a pool occupy
  slots while waiting for something that needs a slot in the same pool to produce it. Nothing ever
  finishes. The fix is mode="reschedule"/deferrable, or a separate pool for sensors.""")


# ================================================================ 7. testing and debugging
section("7. how to test and debug a DAG -- a question that separates users from engineers")
print("""  THE IMPORT TEST -- cheap, catches most real breakage, and belongs in CI:
      def test_dags_import():
          dagbag = DagBag(dag_folder="dags/", include_examples=False)
          assert not dagbag.import_errors        # syntax errors, bad imports, CYCLES
          assert len(dagbag.dags) == EXPECTED
  This alone catches the mistakes that take a production DAG off the schedule silently.

  STRUCTURAL TESTS -- assert the graph, not the behaviour:
      assert dag.task_dict["publish"].upstream_task_ids == {"transform"}
      assert dag.tasks[0].retries == 3                     # default_args really applied
      for task in dag.tasks: assert task.on_failure_callback is not None

  UNIT-TEST THE LOGIC, NOT THE OPERATOR -- the highest-value rule:
      the callable should be a plain, importable function with plain arguments, so it is testable
      with no Airflow at all:
          def transform_orders(rows, interval_start): ...        # testable in 2ms
          PythonOperator(task_id="transform", python_callable=lambda **c:
                         transform_orders(fetch(), c["data_interval_start"]))
      If your business logic only runs inside an operator, you cannot test it cheaply -- and that
      is a design problem, not a testing problem.

  RUN ONE TASK / ONE DAG LOCALLY:
      airflow tasks test my_dag my_task 2026-01-01     # one task, no scheduler, no DB state
      airflow dags test my_dag 2026-01-01              # the whole DAG, in-process
      dag.test()                                       # the same, from Python (2.5+)
  `tasks test` is the one to reach for when debugging: it runs the real task with a real context
  and does not record state, so you can run it repeatedly.

  WHAT TO DO AT 3AM, in order:
      1. the UI grid -> which task instance is red, and in which run
      2. its LOG (per task instance, per attempt -- the try_number tabs)
      3. the RENDERED TEMPLATE view -- nine times out of ten the bug is a template that resolved
         to something unexpected ("WHERE day = ''")
      4. is it this run only, or every run? -> data problem vs code problem
      5. FIX, then CLEAR the task instance(s) to re-run -- which is only safe because the task is
         idempotent.""")


# ================================================================ 8. the checklist
section("8. the production-DAG checklist")
print("""  [ ] catchup set EXPLICITLY, and start_date is a fixed date (never datetime.now())
  [ ] every task is IDEMPOTENT and scoped to the data interval, never to `now()`
  [ ] the write is delete-then-insert / upsert / partition-overwrite, so a retry cannot double data
  [ ] default_args give sensible retries + retry_delay; retries=0 on validation tasks
  [ ] execution_timeout on anything that talks to the network
  [ ] dagrun_timeout, and max_active_runs=1 if runs share mutable state
  [ ] no expensive code at module level (no queries, no API calls, no Variable.get())
  [ ] sensors have a timeout AND mode="reschedule"/deferrable
  [ ] a pool for every shared external resource, sized to that resource
  [ ] an on_failure_callback (or notifier) that actually reaches a human
  [ ] cleanup on trigger_rule=ALL_DONE; alerting on ONE_FAILED; the join after a branch on
      NONE_FAILED_MIN_ONE_SUCCESS
  [ ] XComs carry pointers, not payloads
  [ ] tags + doc_md, so the next person knows what it is and who owns it
  [ ] a DagBag import test in CI""")

# EXPERIMENT 1: in section 1, give `validate` retries=3 and re-run. It fails three times, 5 minutes
# apart. Decide what that bought you.
# EXPERIMENT 2: in section 3, change `cleanup`'s trigger rule to the default ALL_SUCCESS and re-run
# the failing case. The staging table is now never dropped -- on exactly the runs where it matters.
# EXPERIMENT 3: in section 3, change `publish`'s trigger rule to ALL_DONE and re-run the failing
# case. You now publish on top of a failed transform. That is the ALL_DONE trap.
# EXPERIMENT 4: in section 5, set timeout=60 with poke_interval=30 on the never-true sensor and
# count the pokes before it fails. Then add soft_fail and compare the final state.
# EXPERIMENT 5: add a task with trigger_rule=ALWAYS downstream of a failing task and confirm it
# runs regardless -- then think of a legitimate use for that (hint: a run-level audit record).

# EXERCISE: take the `orders_etl` DAG from 01_dag_anatomy_and_operators.py and make it
# production-ready against the section 8 checklist. Specifically: add execution_timeout to the
# network tasks, put the warehouse tasks in a pool, give the sensor a timeout and soft_fail, add an
# on_failure_callback, make the load idempotent with a delete-then-insert scoped to {{ ds }}, and
# write the three tests (import, structure, logic). Then run it with each of the extract, validate
# and load failing in turn, and confirm that in all three cases: an alert fires, the staging table
# is cleaned up, and nothing is published.
