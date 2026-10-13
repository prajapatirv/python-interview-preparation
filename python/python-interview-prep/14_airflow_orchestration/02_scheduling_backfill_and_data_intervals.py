"""
Airflow part 2 -- SCHEDULING. The part everyone gets wrong, and the most-asked Airflow question:

  "A DAG is scheduled @daily with start_date 1 Jan. When does the first run happen, and what is
   its logical_date?"

  Answer: it runs just after MIDNIGHT ON 2 JAN, and its logical_date is 1 JAN.

Because Airflow schedules DATA INTERVALS, not clock times. A run covers [start, end) and can only
be triggered once `end` has passed -- the data for 1 Jan does not exist until 1 Jan is over.
Internalise that one sentence and every other scheduling question answers itself.

This file also covers: catchup/backfill, cron vs timedelta vs presets vs Assets, max_active_runs,
depends_on_past, the start_date traps, and why `datetime.now()` in a task is a correctness bug.

Run me: python 02_scheduling_backfill_and_data_intervals.py
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mini_airflow import (                      # noqa: E402
    DAG, EmptyOperator, Executor, PythonOperator, scheduled_runs, summarise,
)


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ 1. the core model
section("1. the data-interval model -- the one thing to understand")
print("""  Airflow does not think "run at 00:00 every day". It thinks in INTERVALS OF DATA:

      interval            [2026-01-01 00:00, 2026-01-02 00:00)
      logical_date         2026-01-01 00:00      <- the interval's START (was `execution_date`)
      data_interval_start  2026-01-01 00:00
      data_interval_end    2026-01-02 00:00
      ACTUALLY RUNS AT    ~2026-01-02 00:00      <- once the interval is COMPLETE

  So a @daily DAG is always processing YESTERDAY's data, and `logical_date` is NOT "now".
  That is a feature, not a quirk: it makes a run a pure function of its interval, which is what
  makes backfilling and re-running possible at all.

  The naming history, which you may be asked:
      execution_date       the old name. Confusing, because it is NOT when the task executed.
                           Deprecated in Airflow 2.2, REMOVED in Airflow 3.
      logical_date         the 2.2+ name for the same value.
      data_interval_start/_end   added in 2.2 -- use THESE in queries. They are unambiguous.

  If someone says "execution_date", they mean logical_date, and they have been doing this a while.""")


def show_interval(**context):
    print(f"         logical_date        = {context['logical_date']}")
    print(f"         data_interval_start = {context['data_interval_start']}")
    print(f"         data_interval_end   = {context['data_interval_end']}")
    print(f"         ds (the macro)      = {context['ds']}")
    return context["ds"]


with DAG("daily_pipeline", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as daily:
    show = PythonOperator(task_id="show_interval", python_callable=show_interval)

print("  a real run of a @daily DAG, as of 2026-01-05 09:00:")
run = scheduled_runs(daily, now=datetime(2026, 1, 5, 9, 0))[0]
Executor().run(daily, run)
print(f"\n  the LATEST complete interval as of 09:00 on the 5th is the 4th -> 5th.")
print(f"  The interval for the 5th is not complete yet, so no run exists for it.")


# ================================================================ 2. catchup
section("2. catchup -- the single biggest Airflow footgun")

with DAG("with_catchup", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=True) as catch_on:
    EmptyOperator(task_id="noop")

with DAG("without_catchup", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as catch_off:
    EmptyOperator(task_id="noop")

now = datetime(2026, 1, 11)
on_runs = scheduled_runs(catch_on, now=now)
off_runs = scheduled_runs(catch_off, now=now)
print(f"  deployed on {now.date()} with start_date=2026-01-01, schedule=@daily:\n")
print(f"    catchup=True  -> {len(on_runs)} runs queued IMMEDIATELY:")
for r in on_runs:
    print(f"        {r.logical_date.date()}  [{r.data_interval_start.date()} -> "
          f"{r.data_interval_end.date()})")
print(f"\n    catchup=False -> {len(off_runs)} run (only the latest complete interval):")
for r in off_runs:
    print(f"        {r.logical_date.date()}  [{r.data_interval_start.date()} -> "
          f"{r.data_interval_end.date()})")

print("""
  Now scale that up. start_date one year ago + schedule="@hourly" + catchup=True
  = 8,760 DAG runs queued the moment you deploy. They will saturate your workers, hammer the
  source database, and -- if the tasks are not idempotent -- corrupt the target.

  This is THE question to ask yourself before every deploy: "is this DAG supposed to process
  history, or only from now on?"
      processing history is the POINT        -> catchup=True, and cap it with max_active_runs
      the DAG is a cron replacement         -> catchup=False
  Either way: SET IT EXPLICITLY. The global default (`catchup_by_default`) has historically been
  True, and Airflow 3 moves toward False -- so never rely on the default. Write it in the file.

  Related: `backfill` is the DELIBERATE version -- you ask for a date range on purpose:
      airflow dags backfill -s 2026-01-01 -e 2026-01-31 orders_etl
  Catchup is the accidental version that happens at deploy time.""")


# ================================================================ 3. the start_date traps
section("3. start_date: three traps")
print("""  TRAP 1 -- `datetime.now()` or `days_ago(1)` as start_date.
      start_date=datetime.now()      # WRONG
    The file is re-parsed every ~30s, so start_date moves forward every time, so the first
    interval never completes, so THE DAG MAY NEVER RUN -- or runs erratically. Hardcode a fixed
    date. (`airflow.utils.dates.days_ago` was deprecated for exactly this reason.)

  TRAP 2 -- expecting a run AT start_date.
    With start_date=2026-01-01 and @daily, there is no run whose logical_date is 2025-12-31, and
    the 2026-01-01 run happens on the 2nd. Off-by-one confusion here is extremely common.

  TRAP 3 -- a start_date per task.
    Legal (via default_args or the task kwarg) and almost always a mistake: tasks in one DAG then
    have different first intervals, and the graph behaves differently per run. Set it once, on
    the DAG.

  And the modern alternative to all of this: Airflow 3 lets you omit start_date when the schedule
  is asset-driven. For time-based schedules, a fixed date is still the answer.""")


# ================================================================ 4. the schedule values
section("4. what you can pass to `schedule=`")
print("""  CRON STRING        "0 2 * * *"        daily at 02:00 UTC. Also "30 3 * * 1-5" (weekdays).
                                          Cron pins you to CLOCK TIMES.
  PRESET             "@daily" "@hourly" "@weekly" "@monthly" "@yearly" "@once"
                                          sugar for the obvious cron expressions.
  timedelta          timedelta(hours=6)   RELATIVE to the previous run's interval, not to the
                                          clock. timedelta(days=1) from a 03:00 start_date keeps
                                          running at 03:00; cron "0 0 * * *" would not.
  None               None                 no schedule: triggered manually, by the API, or by
                                          TriggerDagRunOperator. Correct for a "called" DAG.
  "@continuous"      (2.6+)               start a new run as soon as the previous one finishes,
                                          max_active_runs=1 enforced.
  Timetable          a custom class       for "last business day of the month", trading calendars,
                                          or any rule cron cannot express.
  [Asset(...)]       (2.4+ as Dataset,    DATA-AWARE scheduling: this DAG runs when another DAG
                      renamed Asset in 3) updates the asset it depends on. See section 7.

  The one distinction worth stating: CRON is absolute (clock times, and it can skip or double up
  across a DST change), timedelta is relative (steady spacing, drifts with the start_date).
  And everything in Airflow is UTC internally -- a cron of "0 9 * * *" is 09:00 UTC, not 09:00
  local, unless the DAG sets a timezone explicitly.""")

for schedule, label in [("@hourly", "hourly"), (timedelta(hours=6), "every 6h"),
                        ("0 2 * * *", "daily at 02:00")]:
    with DAG(f"sched_{label}", schedule=schedule, start_date=datetime(2026, 1, 1),
             catchup=True) as d:
        EmptyOperator(task_id="noop")
    runs = scheduled_runs(d, now=datetime(2026, 1, 2), limit=5)
    intervals = ", ".join(f"[{r.data_interval_start:%d %H:%M}->{r.data_interval_end:%d %H:%M})"
                          for r in runs[:4])
    print(f"\n  schedule={schedule!r:22s} ({label})\n    first intervals: {intervals}")


# ================================================================ 5. idempotency
section("5. why `datetime.now()` inside a TASK is a correctness bug")
print("""  The rule: a task must be a PURE FUNCTION OF ITS DATA INTERVAL. Run it again for the same
  interval and the result must be identical. That is what makes retries, catchup and backfill
  safe -- and all three WILL happen to you.

      WRONG  -- the result depends on WHEN it ran, so a backfill produces today's data for
                every historical date, silently:
          WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'
          WHERE created_at >= '{datetime.now().date()}'

      RIGHT  -- the result depends only on the interval:
          WHERE created_at >= '{{ data_interval_start }}' AND created_at < '{{ data_interval_end }}'

  And the WRITE must be idempotent too, or a retry doubles the data:
      WRONG   INSERT INTO fact_orders SELECT ...                 (appends again on every retry)
      RIGHT   DELETE FROM fact_orders WHERE day = '{{ ds }}';    (delete-then-insert the PARTITION)
              INSERT INTO fact_orders SELECT ...
      RIGHT   MERGE / INSERT ... ON CONFLICT DO UPDATE           (an upsert on a natural key)
      RIGHT   write to s3://bucket/dt={{ ds }}/                  (overwrite one partition)

  This is the same idempotency argument as the Kafka consumer in deep dive 31 -- at-least-once
  execution plus an idempotent write gives you effectively-once data.""")


def bad_extract(**context):
    """Uses `now` -- a backfill of January would write January 31st's data 31 times."""
    today = datetime(2026, 3, 15).date()          # pretend this is datetime.now().date()
    return f"WHERE created_at >= '{today}'   <-- same for EVERY historical run"


def good_extract(data_interval_start, data_interval_end, **context):
    return (f"WHERE created_at >= '{data_interval_start:%Y-%m-%d}' "
            f"AND created_at < '{data_interval_end:%Y-%m-%d}'")


with DAG("idempotency_demo", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=True) as idem:
    PythonOperator(task_id="bad_uses_now", python_callable=bad_extract)
    PythonOperator(task_id="good_uses_interval", python_callable=good_extract)

print("  backfilling three days -- watch the WHERE clauses:")
executor = Executor(verbose=False)
for r in scheduled_runs(idem, now=datetime(2026, 1, 4), limit=3):
    executor.run(idem, r)
    xcoms = executor.xcoms.all_for_run(idem.dag_id, r.run_id)
    print(f"\n    run {r.logical_date:%Y-%m-%d}")
    print(f"      bad : {xcoms['bad_uses_now']}")
    print(f"      good: {xcoms['good_uses_interval']}")
print("\n  the 'bad' task produced the SAME query for all three days. Three runs, one day of data,")
print("  written three times. Nothing errors -- which is why this survives code review.")


# ================================================================ 6. concurrency controls
section("6. the four concurrency knobs, and which problem each one solves")
print("""  max_active_runs      (DAG)   how many RUNS of this dag at once.
                               Set to 1 when runs share mutable state (a table, a cursor, a file).
                               This is also what stops a catchup=True backfill from running 8,760
                               runs in parallel.
  max_active_tasks     (DAG)   how many TASK INSTANCES of this dag at once (was `concurrency`).
                               Protects a downstream DB from your own fan-out.
  max_active_tis_per_dag (task) how many instances of THIS ONE TASK across all runs
                               (was `task_concurrency`). For the one task that must not overlap.
  pool                 (task)  a named, shared slot budget ACROSS DAGS. The only one of the four
                               that is global -- this is how you stop 12 unrelated DAGs opening
                               200 connections to the same warehouse.
  parallelism          (config) a deployment-wide cap on running task instances.

  The interview framing: the first three protect the DAG from itself; a POOL protects a SHARED
  RESOURCE from every DAG. If the question is "how do you stop Airflow overwhelming the database",
  the answer is a pool sized to the database's connection budget, not max_active_tasks.

  And `priority_weight` decides who gets a free slot first when the pool is full.""")


# ================================================================ 7. depends_on_past etc.
section("7. depends_on_past, wait_for_downstream, and data-aware scheduling")
print("""  depends_on_past=True (task)
      this task instance will not start until the SAME task in the PREVIOUS run succeeded.
      Correct for a cumulative/stateful load (a running balance, an SCD2 dimension).
      The cost: it SERIALISES the DAG, so a catchup becomes strictly sequential -- and one failed
      historical run blocks every later run until you clear it. Use it only when the data really
      is order-dependent.

  wait_for_downstream=True (task)
      stronger: wait for the previous run's instance of this task AND everything downstream of it.
      Rarely what you want; it serialises even harder.

  ExternalTaskSensor (cross-DAG, the OLD way)
      DAG B waits for a specific task in DAG A, matched by logical_date (`execution_delta` or
      `execution_date_fn` when the schedules differ). Brittle: get the delta wrong and it waits
      forever, and it couples the two schedules.

  Assets / Datasets (cross-DAG, the MODERN way -- 2.4+, `Dataset`; renamed `Asset` in Airflow 3)
      producer:  @task(outlets=[Asset("s3://lake/orders")])  ...
      consumer:  with DAG("reporting", schedule=[Asset("s3://lake/orders")]): ...
      The consumer runs WHEN THE DATA IS UPDATED, with no shared schedule and no sensor holding a
      slot. This is the answer to "how do you coordinate two DAGs?" in any recent Airflow.

  TriggerDagRunOperator -- push instead of pull. Use it when the parent must control the child
  explicitly (passing `conf`), rather than the child declaring what it depends on.""")


# ================================================================ 8. the summary
section("8. the scheduling questions, answered in one line each")
print("""  Q "@daily, start_date 1 Jan -- when is the first run and what is its logical_date?"
  A  Just after midnight on 2 Jan, with logical_date = 1 Jan. It covers [1 Jan, 2 Jan).

  Q "Why is my DAG processing yesterday's data?"
  A  It isn't a bug. A run covers a COMPLETE interval, and that interval ends now.

  Q "I deployed and 500 runs started. Why?"
  A  catchup=True (the historical default) with a start_date far in the past.

  Q "Why has my DAG never run?"
  A  start_date=datetime.now() -- the first interval never completes. Or the DAG is paused, or
     the schedule is None.

  Q "How do I re-run one day?"
  A  Clear the task instances for that run (UI, or `airflow tasks clear -s ... -e ...`). Airflow
     re-runs them -- which only works because the tasks are idempotent and interval-scoped.

  Q "How do I make two DAGs cooperate?"
  A  Assets/Datasets if the relationship is about DATA (preferred); TriggerDagRunOperator if the
     parent must push with conf; ExternalTaskSensor only on older versions, and mind the delta.

  Q "How do you stop a backfill melting the source database?"
  A  max_active_runs=1 plus a pool sized to the database, and run the backfill off-peak.""")

# EXPERIMENT 1: set `now=datetime(2026, 1, 5, 0, 0)` exactly in section 1 and see which interval is
# the latest complete one. Then try 23:59 on the 4th. That boundary IS the question.
# EXPERIMENT 2: change `catchup=True` to a start_date of 2025-01-01 in section 2 and raise `limit`
# in scheduled_runs to 400. Count the runs. That number is why catchup is the big footgun.
# EXPERIMENT 3: in section 4, change the timedelta DAG's start_date to datetime(2026, 1, 1, 3, 0)
# and compare its intervals with the cron DAG's. Note the cron one ignores the 03:00.
# EXPERIMENT 4: make `bad_extract` in section 5 use a real `datetime.now()` and run the backfill
# again tomorrow. The historical runs change answer -- the definition of non-idempotent.

# EXERCISE: a DAG must aggregate hourly clickstream into a daily table. It is deployed on
# 2026-03-15 and must process all of 2026-03 from the start. Decide and justify, in one sentence
# each: the schedule, the start_date, catchup, max_active_runs, whether any task needs
# depends_on_past, and the exact WHERE clause and write strategy that make a re-run safe.
# Then write it and prove with three runs that re-running one day changes nothing.
