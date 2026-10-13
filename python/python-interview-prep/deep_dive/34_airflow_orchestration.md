# Deep Dive 34 — Airflow and Workflow Orchestration

> Runnable companions: [`14_airflow_orchestration/`](../14_airflow_orchestration/) —
> [`01_dag_anatomy_and_operators.py`](../14_airflow_orchestration/01_dag_anatomy_and_operators.py) ·
> [`02_scheduling_backfill_and_data_intervals.py`](../14_airflow_orchestration/02_scheduling_backfill_and_data_intervals.py) ·
> [`03_taskflow_xcom_and_dynamic_mapping.py`](../14_airflow_orchestration/03_taskflow_xcom_and_dynamic_mapping.py) ·
> [`04_failures_retries_and_trigger_rules.py`](../14_airflow_orchestration/04_failures_retries_and_trigger_rules.py)
> Related deep dives: [30 — Large file processing](30_large_file_processing.md) ·
> [31 — Kafka from Python](31_kafka_python_integration.md) ·
> [28 — Observability](28_observability_distributed_systems.md) ·
> [18 — Queue architectures](18_queue_architectures.md) ·
> [27 — Zero-downtime changes](27_zero_downtime_production_changes.md)

## What interviewers are actually probing

Airflow is the topic where "I've used it" and "I understand it" diverge most. Anyone can write a DAG
by copying the one next to it. The questions that actually separate candidates are:

1. **"`@daily`, `start_date=1 Jan`. When does the first run happen, and what is its
   `logical_date`?"** — the data-interval model. If you say "midnight on 1 Jan" you have revealed
   that you've only ever copied DAGs.
2. **"You deployed and 500 runs started. What happened?"** — `catchup`.
3. **"Why did the task after my branch get skipped?"** — trigger rules and how skips cascade.
4. **"You don't know how many files will arrive. How many tasks?"** — dynamic task mapping, not a
   parse-time loop.
5. **"Why is your Airflow slow?"** — top-level code in DAG files.
6. **"A task failed at 3am. Walk me through it."** — the operational answer, which is the job.

And one framing question behind all of them: **do you understand that Airflow is an orchestrator,
not a compute engine?** It decides *when* and *in what order*; it should not be the thing
transforming your 100GB file.

---

## Must-know points

- **A DAG run covers a data interval `[start, end)` and is triggered once `end` has passed.** A
  `@daily` DAG always processes the *previous* day; `logical_date` is the interval **start**.
- `execution_date` is the old name for `logical_date` (renamed 2.2, **removed** in Airflow 3). Use
  `data_interval_start`/`data_interval_end` in queries — they are unambiguous.
- **`catchup=True` backfills every missed interval at deploy time.** Set it explicitly, every time.
- **`start_date=datetime.now()` means the DAG may never run** — the file is re-parsed every ~30s.
- **Operator** (class) ≠ **Task** (a node in a DAG) ≠ **Task Instance** (a `(task, run)` pair — the
  thing with a state, a try number and logs).
- Operator families: **action**, **transfer**, **sensor**. **Hooks** wrap connections; operators use
  hooks.
- `a >> b`, `a >> [b, c] >> d`, `chain(...)` (**pairwise** for equal-length lists),
  `cross_downstream(...)` (a mesh).
- **The join after a branch needs `trigger_rule="none_failed_min_one_success"`.** The four that
  matter: `all_success` (default), `all_done` (cleanup), `one_failed` (alerting),
  `none_failed_min_one_success` (the join).
- **Idempotency is the central correctness requirement.** Scope every query to the data interval and
  make the write delete-then-insert / upsert / partition-overwrite.
- **XCom is a metadata-DB row.** Pass pointers (an S3 key), never payloads.
- **Dynamic task mapping (`.expand()`, 2.3+)** for a run-time-determined number of tasks.
- **No expensive top-level code.** It runs on the scheduler every ~30 seconds, forever.
- **Sensors**: `mode="poke"` holds a worker slot for the whole wait; prefer `reschedule` or
  `deferrable=True`, and always set a `timeout`.
- **Pools** are the only concurrency control that is global across DAGs.
- **Cross-DAG**: Assets/Datasets (modern, data-aware) > `TriggerDagRunOperator` (push) >
  `ExternalTaskSensor` (brittle).

---

## Interview questions and full answers

### Q1. What is Airflow, and when is it the wrong tool?

**Airflow is a scheduler and dependency engine for batch workflows.** You declare a DAG of tasks in
Python; Airflow decides when each task instance runs, tracks its state in a metadata database,
retries it, and shows you the result. **It does not execute your business logic** — it starts
processes that do.

The architecture, which is worth being able to sketch:

```
  DAG files (.py)  --parsed every ~30s-->  SCHEDULER  --writes state-->  METADATA DB (Postgres)
                                              |                              ^
                                              | queues task instances        | state, XComs, logs index
                                              v                              |
                                          EXECUTOR  -->  WORKERS  -----------+
                                              |
                                          TRIGGERER (async waits for deferrable operators)
                                              |
                                          WEBSERVER (the UI reads the same DB)
```

**Executors**, and the one-line reason for each: `SequentialExecutor` (SQLite, local only, no
parallelism — never in production), `LocalExecutor` (subprocesses on one machine; genuinely fine for
small deployments), `CeleryExecutor` (a worker fleet + a broker like Redis/RabbitMQ; the classic
scale-out), `KubernetesExecutor` (one pod per task — strong isolation and per-task resources, at the
cost of pod startup latency).

**When Airflow is the WRONG tool** — volunteering this is the senior move:

| Need | Use instead | Why |
|---|---|---|
| sub-minute latency, per-event | Kafka consumers, Lambda ([18](18_queue_architectures.md), [31](31_kafka_python_integration.md)) | Airflow's scheduling loop is seconds-to-minutes; it is a **batch** scheduler |
| streaming | Kafka Streams, Flink, Spark Streaming | Airflow has no concept of an unbounded stream |
| heavy data transformation | Spark/EMR, DuckDB, the warehouse itself ([30](30_large_file_processing.md)) | Airflow should **submit** the job, not be it. Processing 100GB inside a `PythonOperator` puts the load on your orchestrator |
| simple cron, one script, no deps | cron, a systemd timer, EventBridge | Airflow is a lot of infrastructure to run one script |
| request/response | a web service | DAG runs are not interactive |
| SQL-only transformation | dbt (orchestrated *by* Airflow) | dbt owns the model graph; Airflow triggers it |

The sentence to land: **Airflow orchestrates; it should not compute.** The common anti-pattern is a
`PythonOperator` that pulls 40GB into the worker — the right shape is a task that submits a Spark/Glue
job and waits.

---

### Q2. Walk me through a DAG file. (The keywords.)

```python
with DAG(
    dag_id="orders_etl",                   # the PRIMARY KEY. Renaming it orphans all history.
    schedule="@daily",                     # cron / timedelta / preset / [Asset] / None
    start_date=datetime(2026, 1, 1),       # a FIXED date. Never datetime.now().
    catchup=False,                         # EXPLICIT, always (Q4)
    max_active_runs=1,                     # runs share a target table
    max_active_tasks=16,                   # task parallelism within this DAG (was `concurrency`)
    dagrun_timeout=timedelta(hours=2),     # kill an overrunning run
    tags=["orders", "etl", "team-data"],   # free, and essential at 200 DAGs
    params={"warehouse": "analytics"},     # per-run parameters, overridable when triggering
    doc_md=__doc__,                        # the runbook, shown in the UI
    default_args={                         # applied to EVERY task unless the task overrides it
        "owner": "data-platform",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "on_failure_callback": notify_slack,
        "execution_timeout": timedelta(minutes=30),
    },
) as dag:
    ...
```

The resolution order worth stating: **explicit task kwarg > the DAG's `default_args` > the
hard-coded default.** That is why `retries` lives in `default_args` (write it once) but a validation
task sets `retries=0` on itself.

**Task-level keywords** you should be able to name: `task_id` (unique per DAG), `trigger_rule`,
`retries`/`retry_delay`/`retry_exponential_backoff`/`max_retry_delay`, `execution_timeout`,
`depends_on_past`, `wait_for_downstream`, `pool`/`pool_slots`/`priority_weight`,
`max_active_tis_per_dag`, `sla`, `do_xcom_push`, and the `on_*_callback` family.

**Why `dag_id` is the primary key** is a nice detail: rename it and Airflow sees a brand-new DAG
with no history, while the old one becomes an orphan in the UI. Renaming a DAG is a migration, not an
edit.

---

### Q3. Operator vs Task vs Task Instance — and which operators have you used?

- **Operator** — a **class**; a template for a unit of work. `PythonOperator`, `BashOperator`.
- **Task** — an **instance of an operator inside a DAG**; a node in the graph.
- **Task Instance** — a specific **(task, dag_run)** pair. This is the thing that has a *state*, a
  *try_number* and *logs*. One task becomes many task instances over time, one per run.

So: you **clear a task instance** to re-run it; the coloured boxes in the UI grid are task instances,
one column per run. Getting this vocabulary right signals experience immediately.

**The three operator families** — a much better answer than listing names at random:

| Family | Does | Examples |
|---|---|---|
| **Action** | performs work | `PythonOperator`, `BashOperator`, `SQLExecuteQueryOperator`, `KubernetesPodOperator`, `SparkSubmitOperator`, `LambdaInvokeFunctionOperator`, `GlueJobOperator` |
| **Transfer** | moves data A→B | `S3ToRedshiftOperator`, `GCSToBigQueryOperator`, `SftpToS3Operator` |
| **Sensor** | waits for a condition | `S3KeySensor`, `ExternalTaskSensor`, `SqlSensor`, `DateTimeSensor` |

Plus the **control-flow** operators, which aren't really any of the three: `EmptyOperator` (was
`DummyOperator`; a graph marker), `BranchPythonOperator`, `ShortCircuitOperator`,
`TriggerDagRunOperator`, `LatestOnlyOperator`.

**Hooks are not operators.** A hook wraps a **connection** (`S3Hook`, `PostgresHook`), resolving
credentials from a `conn_id`. Operators use hooks internally. When no operator fits, writing a
`PythonOperator` that uses a hook is the **normal** escape hatch, not a failure:

```python
def load(**context):
    hook = PostgresHook(postgres_conn_id="warehouse")
    hook.run("DELETE FROM fact WHERE day = %s", parameters=(context["ds"],))
```

Note also that most provider operators have been consolidated — `PostgresOperator`/`MySqlOperator`
etc. are deprecated in favour of **`SQLExecuteQueryOperator`** from the `common.sql` provider. Saying
that shows you've worked on a recent version.

---

### Q4. `@daily`, `start_date=1 Jan`. When does the first run happen?

**Just after midnight on 2 January, with `logical_date = 1 January.`**

This is *the* Airflow question, and the model behind it is the one thing to understand:

```
  interval            [2026-01-01 00:00, 2026-01-02 00:00)
  logical_date         2026-01-01 00:00      <- the interval's START
  data_interval_start  2026-01-01 00:00
  data_interval_end    2026-01-02 00:00
  ACTUALLY RUNS AT    ~2026-01-02 00:00      <- once the interval is COMPLETE
```

**Why:** Airflow schedules **intervals of data**, not clock times. The data for 1 January does not
exist until 1 January is over, so a run that processes it cannot start before then. A `@daily` DAG is
therefore always processing *yesterday*.

That is a feature, not a quirk: it makes a run a **pure function of its interval**, which is what
makes re-running and backfilling possible at all.

**The naming history**, which you may be asked:

| Name | Status |
|---|---|
| `execution_date` | the original name. Confusing — it is *not* when the task executed. Deprecated 2.2, **removed in Airflow 3** |
| `logical_date` | the 2.2+ name for the same value |
| `data_interval_start` / `data_interval_end` | added 2.2. **Use these in queries** |

If someone says "execution_date", they mean `logical_date`, and they have been doing this a while.

**The follow-ups this model answers:**

- *"Why is my DAG processing yesterday's data?"* — It isn't a bug; the interval ends now.
- *"Why has my DAG never run?"* — `start_date=datetime.now()`, or it's paused, or `schedule=None`.
- *"I need 09:00 data at 09:05."* — Then your interval is hourly, not daily; or use a cron schedule
  that fits, and accept that the interval still ends before the run starts.

---

### Q5. What is `catchup`, and why is it the biggest footgun?

`catchup=True` tells the scheduler to create a run for **every missed interval since `start_date`**.
Deploy a DAG with `start_date` a year ago and `schedule="@hourly"` and you get **8,760 runs queued
the moment it unpauses** — saturating workers, hammering the source database, and if the tasks aren't
idempotent, corrupting the target.

```
deployed 2026-01-11, start_date=2026-01-01, @daily:
  catchup=True  -> 10 runs queued immediately (01-01 … 01-10)
  catchup=False -> 1 run (the latest complete interval only)
```

**The question to ask before every deploy: is this DAG supposed to process history, or only from now
on?**

- Processing history *is the point* → `catchup=True`, **and** cap it with `max_active_runs` (plus a
  pool), and run it off-peak.
- The DAG is a cron replacement → `catchup=False`.

Either way, **set it explicitly in the file.** The global default (`catchup_by_default`) has
historically been `True`, and Airflow 3 moves toward `False` — so relying on the default is how you
get surprised on an upgrade.

**`catchup` vs `backfill`:** catchup is the *accidental* version that happens at deploy time;
`airflow dags backfill -s 2026-01-01 -e 2026-01-31 orders_etl` is the *deliberate* version where you
ask for a range on purpose. (Airflow 3 moves backfills into the scheduler rather than a blocking CLI
process.)

---

### Q6. Why must a task be idempotent, and what does that mean concretely?

**Because retries, catchup, backfills and manual clears all re-run the same task for the same
interval — and all four will happen to you.** A task must therefore be a **pure function of its data
interval**: run it again, get the same result.

**Two halves, and people usually only get the first:**

**1. Scope the READ to the interval, never to `now`:**

```sql
-- WRONG: the answer depends on WHEN it ran, so a backfill writes today's data for every
-- historical date -- silently, with no error anywhere
WHERE created_at >= CURRENT_DATE - INTERVAL '1 day'

-- RIGHT: the answer depends only on the interval
WHERE created_at >= '{{ data_interval_start }}' AND created_at < '{{ data_interval_end }}'
```

The companion file demonstrates this over a 3-day backfill: the `now()`-based task emits the
*identical* query for all three days. Three runs, one day of data, written three times.

**2. Make the WRITE idempotent, or a retry doubles the data:**

```sql
-- WRONG  INSERT INTO fact_orders SELECT ...          (appends again on every retry)
-- RIGHT  DELETE FROM fact_orders WHERE day = '{{ ds }}';   -- delete-then-insert the PARTITION
--        INSERT INTO fact_orders SELECT ...
-- RIGHT  MERGE / INSERT ... ON CONFLICT DO UPDATE    (upsert on a natural key)
-- RIGHT  write to s3://bucket/dt={{ ds }}/           (overwrite one partition)
```

**This is exactly the same argument as the Kafka→Aurora sink** in
[31](31_kafka_python_integration.md): at-least-once *execution* plus an idempotent *write* gives you
effectively-once data. Making that connection out loud is a strong signal — it shows the principle
is one you hold, not one you memorised per tool.

---

### Q7. How do tasks share data? What are the XCom rules?

**An XCom is a row in Airflow's metadata database**, keyed by
`(dag_id, run_id, task_id, map_index, key)`. `xcom_push` INSERTs; `xcom_pull` SELECTs. A task's
**return value is pushed automatically** under the key `return_value`.

That single fact gives you every rule:

- **DO** pass small scalars: a row count, an S3 key, a batch id, a flag.
- **DON'T** pass a DataFrame, a file's contents, or a 50MB blob. You'd be using your orchestrator's
  control-plane database as a data bus — slow, it bloats the metadata DB, and large values hit a hard
  column limit. **The limit is not the point**; the architecture is.

**The pattern:** write the data to object storage, pass the **key**:

```python
def extract(**c):
    s3.put_object(Bucket=B, Key=f"stage/{c['ds']}/orders.parquet", Body=...)
    return f"stage/{c['ds']}/orders.parquet"          # ~40 bytes in XCom

def load(ti, **c):
    key = ti.xcom_pull(task_ids="extract")
    ...
```

Other things to know: XComs are scoped to a run (`include_prior_dates=True` to reach back);
`do_xcom_push=False` disables the automatic return-value push; XComs are **not** auto-cleaned in
older versions (`airflow db clean` exists for exactly this, and an unbounded XCom table is a real
production problem); and a **custom XCom backend** (`xcom_backend`) makes the S3-pointer pattern
automatic, which is the production answer when a team keeps passing big objects.

---

### Q8. Classic operators vs the TaskFlow API?

**Classic** wires operators together with `>>` and moves data with explicit `xcom_push`/`xcom_pull`:

```python
e = PythonOperator(task_id="extract", python_callable=extract)
t = PythonOperator(task_id="transform", python_callable=transform)   # calls ti.xcom_pull inside
e >> t
```

The problem: **the data flow and the dependency graph are declared twice**, and nothing stops them
disagreeing.

**TaskFlow (`@task`, 2.0+)** collapses them — ordinary function calls declare both:

```python
@task
def extract():            return {"order_ids": [101, 102, 103]}
@task
def transform(payload):   return len(payload["order_ids"])
@task
def load(count):          return f"loaded {count}"

load(transform(extract()))          # 3 tasks and 2 edges, from one line
```

The XComs still exist; the decorator just does the push/pull.

**Which to use:**

- **TaskFlow** for Python-native ETL where tasks pass values. The default for new code.
- **Classic** when you need a provider operator (`KubernetesPodOperator`,
  `SQLExecuteQueryOperator`, `S3ToRedshiftOperator`) — there is no `@task` for those.
- **Mixed**, which is the usual reality: `files = list_files()` (TaskFlow) `>> KubernetesPodOperator(...)`.

The decorator family is worth naming: `@task_group`, `@task.bash`, `@task.branch`,
`@task.short_circuit`, `@task.sensor`, `@task.docker`, `@task.kubernetes`.

---

### Q9. You don't know how many files will arrive. How many tasks?

**Dynamic task mapping (`.expand()`, Airflow 2.3+): one task definition, N task instances created at
run time.**

```python
@task
def list_files():      return ["a.csv", "b.csv", "c.csv"]      # length unknown until this runs
@task
def process(name):     return f"processed {name}"

process.expand(name=list_files())                      # 3 instances today, 50 tomorrow
process.partial(bucket="my-lake").expand(name=list_files())     # constant + mapped args
process.expand_kwargs([{"name": "a", "rows": 1}, {"name": "b", "rows": 2}])   # map several args
collect(process.expand(name=list_files()))             # the reduce step gets the LIST of results
```

**The wrong answer, and why it's wrong** — this is the real content of the question:

```python
for f in list_s3_files():                      # runs every ~30s ON THE SCHEDULER
    PythonOperator(task_id=f"process_{f}")     # and the graph changes shape between parses
```

That's the top-level-code anti-pattern (Q10) *plus* a DAG whose history is unreadable, because the
task set changed over time and old runs reference tasks that no longer exist.

**Why mapping beats a loop inside one task:** each mapped instance has **its own log, its own retry
and its own state**. One file failing doesn't re-process the other 49. In the UI they collapse into a
single expandable row. `max_map_length` (default 1024) caps the fan-out so a bad upstream can't
create two million task instances.

---

### Q10. Why is your Airflow slow? (The top-level code rule.)

**Because the scheduler re-parses every DAG file on a loop** —
`min_file_process_interval`, default 30 seconds. Anything at module level therefore runs **every ~30
seconds, forever, on the scheduler**, not once per run.

```python
# WRONG -- every one of these runs every 30s, for every DAG file:
rows = psycopg.connect(DSN).execute("SELECT ...").fetchall()   # a query, at import
config = requests.get("https://config/api").json()             # a network call, at import
secret = Variable.get("api_key")                               # a metadata-DB hit, at import
for customer in rows:                                          # a DAG shape from a query
    PythonOperator(task_id=f"load_{customer}", ...)
```

```python
# RIGHT -- the work moves INSIDE a task (runs once per run, on a worker):
def load(**context):
    rows = psycopg.connect(DSN).execute("SELECT ...").fetchall()
PythonOperator(task_id="load", python_callable=load)
# ...and for a variable number of tasks, dynamic task mapping (Q9).
# ...and for the secret, `{{ var.value.api_key }}` -- templated, so it resolves at RUN time.
```

**The symptoms**, which is how you recognise it in the wild: the scheduler lags, the UI is slow, DAGs
flicker in and out of the list, and `dag_processing.last_duration` climbs. It is the single most
common cause of "our Airflow is slow".

Also avoid at top level: `datetime.now()` in `start_date`, heavy imports (import inside the callable
instead), and any `Variable.get()`/`Connection.get()`.

---

### Q11. Explain trigger rules. Why did the task after my branch get skipped?

A trigger rule decides **when a task may run given its upstream tasks' states**. The default is
`all_success`, which is why a failure "cancels" everything downstream — **and why a *skip* does too.**

Executed matrix (from the companion file), two upstream tasks:

| rule | 2 success | 1 failed | 2 failed | 1 skipped | 2 skipped |
|---|---|---|---|---|---|
| `all_success` *(default)* | **RUN** | upstream_failed | upstream_failed | skipped | skipped |
| `all_done` | **RUN** | **RUN** | **RUN** | **RUN** | **RUN** |
| `all_failed` | skipped | skipped | **RUN** | skipped | skipped |
| `one_success` | **RUN** | **RUN** | skipped | **RUN** | skipped |
| `one_failed` | skipped | **RUN** | **RUN** | skipped | skipped |
| `none_failed` | **RUN** | upstream_failed | upstream_failed | **RUN** | **RUN** |
| `none_failed_min_one_success` | **RUN** | upstream_failed | upstream_failed | **RUN** | skipped |
| `none_skipped` | **RUN** | **RUN** | **RUN** | skipped | skipped |
| `all_skipped` | skipped | skipped | skipped | skipped | **RUN** |
| `always` | **RUN** | **RUN** | **RUN** | **RUN** | **RUN** |

**The branch question.** `BranchPythonOperator` returns the `task_id`(s) to follow. Airflow then
skips **everything downstream of the branch that is not reachable from the chosen branch**
(`skip_all_except`). So the un-chosen branch is skipped — and with the default `all_success`, that
skip **cascades** into the join and kills the rest of the DAG.

```python
branch >> [load_bulk, load_incremental] >> join
join = EmptyOperator(task_id="join", trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
#                                                 ^ without this, the whole tail is skipped
```

`none_failed_min_one_success` is exactly right: tolerate the skipped branch, but still refuse to run
if something actually **failed**. (It replaced the older `none_failed_or_skipped`.)

**The four that matter in practice**, and the standard production shape:

```python
alert    = PythonOperator(..., trigger_rule=TriggerRule.ONE_FAILED)  # alert as soon as anything fails
cleanup  = PythonOperator(..., trigger_rule=TriggerRule.ALL_DONE)    # always release the lock
join     = EmptyOperator(..., trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS)
# everything else: the default all_success
```

**The `all_done` trap to name:** `all_done` means a *failed* upstream doesn't stop you. That's right
for cleanup and wrong for anything that publishes — put `all_done` on a publish task and you'll
publish on top of a broken upstream.

---

### Q12. A task failed at 3am. Walk me through it.

**The operational answer, in order** — this is the question that most reveals experience:

1. **The UI grid** — which task instance is red, in which run? One run or every run?
2. **Its log**, for the right **attempt** (the try_number tabs).
3. **The Rendered Template view.** Nine times out of ten the bug is a template that resolved to
   something unexpected — `WHERE day = ''`. People forget this view exists; it's the highest-value
   debugging tool in the UI.
4. **One run or all runs?** → a data problem versus a code problem.
5. **Fix, then clear the task instance(s)** to re-run — which is only safe because the task is
   idempotent (Q6).
6. If it's transient and recurring, the fix is config (`retries`, `execution_timeout`, a pool), not a
   clear.

**And the design that made it survivable**, which is what they're really checking:

```python
retries=3, retry_delay=timedelta(minutes=5), retry_exponential_backoff=True
execution_timeout=timedelta(minutes=30)      # WITHOUT this, a hung task holds its slot forever
on_failure_callback=notify_slack             # or a provider Notifier
retries=0                                    # ON VALIDATION TASKS specifically
```

**What retries do and don't fix** is the follow-up:

- **Do** fix: a transient failure — a network blip, a DB failover, a 503, a rate limit, a reclaimed
  spot instance.
- **Don't** fix: **bad data** (retrying a validation error three times just fails three times, 15
  minutes apart, and *delays the alert* — so `retries=0` there), a **bug**, or a **non-idempotent
  task**, where retries actively make it worse.

`execution_timeout` is the one people omit: without it, "hung" never becomes "failed", so the retry
never even happens.

---

### Q13. How do you alert, and how do SLAs actually behave?

**Callbacks**, usually in `default_args` so every task gets them:

```python
default_args = {
    "on_failure_callback": notify_slack,
    "on_retry_callback": count_retry_metric,
    "on_success_callback": None,
}
```

Also `on_execute_callback`, `on_skipped_callback`, DAG-level `on_failure_callback` (fires when the
*run* fails), and `sla_miss_callback`. In production, prefer the built-in **Notifiers**
(`SlackNotifier`) over hand-rolled callbacks — reusable and testable.

**SLA semantics, and be precise, because they surprise people:**

- `sla=timedelta(hours=2)` on a task means *"this task should be done within 2 hours **of the DAG
  run's data interval end**"* — **not** 2 hours after the task started.
- A miss calls `sla_miss_callback` and is recorded. It does **not** fail or kill the task.
- **There is no SLA on the DAG as a whole** — you put it on the last task.
- The implementation has historically been quirky (missed SLAs for skipped tasks, scheduler load),
  and Airflow 3 reworks this area. Check what *your* version does.

**The pragmatic alternative many teams use**, and it's a good thing to offer: `dagrun_timeout` plus
an **external freshness check on the output** ("is the table newer than 2 hours?"). That measures
what the customer actually cares about rather than what the orchestrator did — the same
symptoms-not-causes argument as [28](28_observability_distributed_systems.md).

---

### Q14. A sensor is blocking all your workers. Why, and what are the modes?

**Because `mode="poke"` — the default — holds a worker slot for the entire wait.** A 6-hour sensor
occupies a slot for 6 hours. Ten of those on a 16-slot deployment and nothing else can run: the
classic *"Airflow is stuck but nothing is running"* incident.

| mode | Slot behaviour | Use when |
|---|---|---|
| `poke` *(default)* | **holds** a worker slot for the whole wait | the wait is seconds |
| `reschedule` | releases the slot between pokes (`up_for_reschedule`) | the wait is minutes+ |
| `deferrable=True` | hands off to the **triggerer**; no worker slot at all (async) | available, and best |

Plus: **always set `timeout`** (the default is ~7 days); `soft_fail=True` marks a timeout as
**skipped** rather than failed ("the file didn't arrive and that's acceptable" instead of a 3am page);
`exponential_backoff=True` widens the poke interval.

**The pool deadlock** is worth naming: sensors in `mode="poke"` sitting in a pool occupy slots while
waiting for something that needs a slot *in the same pool* to produce it. Nothing ever finishes. Fix
with `reschedule`/`deferrable`, or a separate pool for sensors.

**And the design-level answer:** if the thing you're waiting for is produced by **another Airflow
DAG**, don't use a sensor at all — use Assets/Datasets (Q15) so the consumer is *triggered* by the
data instead of polling for it.

---

### Q15. How do you coordinate two DAGs?

Three mechanisms, in the order you should prefer them:

**1. Assets / Datasets — data-aware scheduling (2.4+ as `Dataset`, renamed `Asset` in Airflow 3).**
The modern answer:

```python
orders = Asset("s3://lake/orders")                       # Dataset(...) on 2.x

@task(outlets=[orders])                                  # the PRODUCER declares what it updates
def write_orders(): ...

with DAG("reporting", schedule=[orders]):                # the CONSUMER is TRIGGERED by the data
    ...
```

No shared schedule, no sensor holding a slot, and the dependency is declared in terms of **data**
rather than timing. Airflow 3 extends this with conditional expressions (`asset_a & asset_b`).

**2. `TriggerDagRunOperator` — push.** Use when the parent must explicitly control the child and pass
`conf`. `wait_for_completion=True` makes the parent block.

**3. `ExternalTaskSensor` — pull, and the legacy option.** DAG B waits for a task in DAG A, matched
**by logical_date** — so if the schedules differ you need `execution_delta` or `execution_date_fn`.
Brittle: get the delta wrong and it waits forever, and it couples the two schedules. Only on older
versions.

Related: `depends_on_past=True` makes a task wait for **its own previous run** to have succeeded —
correct for a cumulative/stateful load, but it **serialises** the DAG, so a catchup becomes strictly
sequential and one failed historical run blocks everything after it. `wait_for_downstream` is the
stronger, rarer version.

---

### Q16. How do you stop Airflow overwhelming the database?

**A pool.** It's the only concurrency control that is **global across DAGs**:

```bash
airflow pools set warehouse 5 "max 5 concurrent warehouse queries"
```
```python
PythonOperator(task_id="query", pool="warehouse", pool_slots=1, ...)
```

The four knobs, and the distinction that matters:

| Control | Scope | Protects |
|---|---|---|
| `max_active_runs` | one DAG | the DAG from itself (runs sharing a table) |
| `max_active_tasks` | one DAG | a downstream system from *this* DAG's fan-out |
| `max_active_tis_per_dag` | one task | the one task that must not overlap itself |
| **`pool`** | **all DAGs** | **a shared external resource** |
| `parallelism` | the deployment | the whole cluster |

Twelve DAGs each politely limited to 4 tasks still open 48 connections. **A pool of 5 caps the total,
whoever asks.** Size it from the *resource's* budget, not Airflow's: if the warehouse allows 20
connections and other services need 10, the pool is 10 — the same connection-count arithmetic as
[29](29_capacity_scaling_tps.md). `priority_weight` decides who gets the next free slot.

---

### Q17. How do you test a DAG?

**Four layers, cheapest first.**

**1. The import test — belongs in CI, catches most real breakage:**

```python
def test_dags_import():
    dagbag = DagBag(dag_folder="dags/", include_examples=False)
    assert not dagbag.import_errors          # syntax errors, bad imports, CYCLES
    assert len(dagbag.dags) == EXPECTED_COUNT
```

This alone catches the mistakes that silently take a DAG off the schedule.

**2. Structural tests — assert the graph:**

```python
assert dag.task_dict["publish"].upstream_task_ids == {"transform"}
assert all(t.on_failure_callback is not None for t in dag.tasks)
assert dag.task_dict["validate"].retries == 0
```

**3. Unit-test the LOGIC, not the operator — the highest-value rule.** Keep the callable a plain,
importable function with plain arguments:

```python
def transform_orders(rows, interval_start): ...     # testable in 2ms, no Airflow
PythonOperator(task_id="transform",
               python_callable=lambda **c: transform_orders(fetch(), c["data_interval_start"]))
```

If your business logic only runs inside an operator, you can't test it cheaply — and that's a
**design** problem, not a testing problem.

**4. Run it locally:**

```bash
airflow tasks test my_dag my_task 2026-01-01    # ONE task, no scheduler, no DB state recorded
airflow dags test my_dag 2026-01-01            # the whole DAG, in-process
dag.test()                                     # the same, from Python (2.5+)
```

`tasks test` is the debugging tool: it runs the real task with a real context and records no state,
so you can run it repeatedly.

---

## A worked example

**The brief: a vendor drops hourly clickstream files in S3. Build a daily aggregate, and make it
survivable.**

```python
"""Daily clickstream aggregate. Owner: data-platform. Runbook: <link>.
On failure: check the Rendered Template view first, then the vendor's SFTP status page."""
from datetime import datetime, timedelta

from airflow.decorators import task
from airflow.models.dag import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.common.sql.operators.sql import SQLExecuteQueryOperator
from airflow.utils.trigger_rule import TriggerRule

with DAG(
    dag_id="clickstream_daily",
    schedule="@daily",
    start_date=datetime(2026, 3, 1),          # FIXED. We want March onward.
    catchup=True,                             # we DO want to process March from the start...
    max_active_runs=2,                        # ...but not 15 days at once
    dagrun_timeout=timedelta(hours=3),
    tags=["clickstream", "team-data"],
    doc_md=__doc__,
    default_args={
        "owner": "data-platform",
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "execution_timeout": timedelta(minutes=45),
        "on_failure_callback": SlackNotifier(text="clickstream_daily failed"),
    },
) as dag:

    # 1. WAIT -- reschedule mode so a 4-hour wait doesn't hold a worker slot.
    #    soft_fail: a late vendor file is a SKIP, not a 3am page.
    wait = S3KeySensor(
        task_id="wait_for_vendor_files",
        bucket_key="s3://vendor-drop/clicks/{{ ds }}/_SUCCESS",
        mode="reschedule",
        poke_interval=300,
        timeout=60 * 60 * 4,
        soft_fail=True,
    )

    # 2. LIST -- the count is unknown until run time, so it must come from a TASK, not a loop
    @task
    def list_parts(ds=None) -> list[str]:
        return s3_list(f"vendor-drop/clicks/{ds}/")      # 12 files today, 400 tomorrow

    # 3. MAP -- one task instance per file: own log, own retry, independent failure
    @task(pool="vendor_api", max_active_tis_per_dag=8)
    def normalise(key: str, bucket: str = "lake") -> str:
        out = f"staged/clicks/{key.split('/')[-1]}.parquet"
        write_parquet(out, read_csv(key))                 # data to S3...
        return out                                        # ...and only the KEY in XCom

    # 4. REDUCE -- idempotent write, scoped to the interval, in a POOL sized to the warehouse
    aggregate = SQLExecuteQueryOperator(
        task_id="aggregate_into_warehouse",
        conn_id="warehouse",
        pool="warehouse",                                  # global cap across every DAG
        sql="""
            DELETE FROM fact_clicks WHERE day = '{{ ds }}';     -- delete-then-insert the PARTITION
            INSERT INTO fact_clicks (day, page, clicks)
            SELECT '{{ ds }}', page, count(*)
              FROM staging_clicks
             WHERE event_at >= '{{ data_interval_start }}'       -- the INTERVAL, never now()
               AND event_at <  '{{ data_interval_end }}'
             GROUP BY page;
        """,
    )

    # 5. VALIDATE -- retries=0, because bad data will not fix itself in 5 minutes
    @task(retries=0)
    def assert_row_count(ds=None):
        n = query_scalar(f"SELECT count(*) FROM fact_clicks WHERE day = '{ds}'")
        if n == 0:
            raise ValueError(f"fact_clicks is empty for {ds}")
        return n

    # 6. CLEANUP -- ALL_DONE: it must run whatever happened above
    cleanup = SQLExecuteQueryOperator(
        task_id="drop_staging",
        conn_id="warehouse",
        sql="TRUNCATE staging_clicks;",
        trigger_rule=TriggerRule.ALL_DONE,
    )

    done = EmptyOperator(task_id="done", trigger_rule=TriggerRule.ALL_DONE)

    staged = normalise.expand(key=list_parts())
    wait >> staged >> aggregate >> assert_row_count() >> cleanup >> done
```

**Why each decision — this is what you'd be asked to justify:**

| Choice | Reason |
|---|---|
| `start_date` fixed, `catchup=True`, `max_active_runs=2` | we genuinely want March backfilled, but two runs at a time, not fifteen |
| `S3KeySensor(mode="reschedule", soft_fail=True, timeout=...)` | a 4-hour wait must not hold a worker slot; a late vendor is a skip, not a page |
| `list_parts` as a **task** | the file count is run-time data. A parse-time loop would query S3 every 30s on the scheduler |
| `.expand(key=...)` | one instance per file, each independently retryable — one bad file doesn't re-run the other 399 |
| XCom carries `out` (a key), not the parquet | an XCom is a metadata-DB row |
| `DELETE … ; INSERT …` scoped to `{{ ds }}` | idempotent: a retry, a clear or a backfill produces the same result |
| `data_interval_start/_end`, never `CURRENT_DATE` | a backfill must produce *historical* data, not today's |
| `pool="warehouse"` | caps warehouse connections across **every** DAG, not just this one |
| `retries=0` on validation | bad data won't fix itself; retrying delays the alert by 15 minutes |
| `execution_timeout` in `default_args` | without it a hung task holds its slot forever and never retries |
| `cleanup`/`done` on `ALL_DONE` | they must run on failure too — that's when the staging table most needs truncating |
| `doc_md` + `tags` | the next person on call can find the runbook |

**And what it deliberately does NOT do:** no heavy transformation inside a `PythonOperator`. If the
daily volume outgrows a worker, `aggregate` becomes a Spark/Glue submission and Airflow just waits —
because Airflow orchestrates, it doesn't compute ([30](30_large_file_processing.md)).

---

## Airflow vs the alternatives

Worth having an opinion, because "why Airflow?" is a fair follow-up:

| Tool | Strength | Pick it over Airflow when |
|---|---|---|
| **Airflow** | huge provider ecosystem, mature, the de-facto standard, Python-native | — |
| **Dagster** | asset-centric, strong typing, excellent local dev and testing | your mental model is "tables I own", not "tasks I run" |
| **Prefect** | dynamic flows, lighter, feels like plain Python | the workflow shape genuinely changes per run |
| **Step Functions** | serverless, AWS-native, no infrastructure | you're AWS-only and want nothing to operate |
| **dbt** | SQL model graph, lineage, tests | the transformation is SQL — and then Airflow *triggers dbt* |
| **Temporal** | durable execution, long-running stateful workflows | you need per-entity workflows and sub-second latency, not batch |

The honest summary: **Airflow wins on ecosystem and ubiquity**; Dagster and Prefect are better
developer experiences; Step Functions wins if you want zero operations. For a batch data platform
with many external systems, Airflow's provider library is usually the deciding factor.

---

## Hands-on drills

1. Run `01` and remove `trigger_rule=NONE_FAILED_MIN_ONE_SUCCESS` from the join. Watch the branch
   skip cascade and kill the whole tail. That one keyword is the difference between a working branch
   and a silently dead pipeline.
2. In `02`, set `now=datetime(2026, 1, 5, 0, 0)` exactly, then `23:59` on the 4th. That boundary **is**
   the Q4 question.
3. In `02`, set `start_date=2025-01-01` with `catchup=True` and raise the `limit`. Count the runs.
4. In `02`, make the "bad" extract use a real `datetime.now()`, run the backfill, then run it again
   tomorrow. The historical answers change — the definition of non-idempotent.
5. In `03`, make `list_files` return 8 names. The code doesn't change; only the instance count does.
6. In `03`, make one mapped instance raise. Only that `map_index` fails. Compare with a `for` loop
   inside one task.
7. In `03`, try to template a `PythonOperator`'s callable body and confirm the braces come out
   literally. Then fix it by taking `ds` as a parameter.
8. In `04`, change `cleanup` to the default `all_success` and re-run the failing case. The staging
   table is now never dropped — on exactly the runs where it matters.
9. In `04`, change `publish` to `all_done` and re-run the failing case. You now publish on top of a
   failed transform: the `all_done` trap.
10. In `04`, set `timeout=60` with `poke_interval=30` on the never-true sensor. Count the pokes, then
    add `soft_fail` and compare the final state.
11. Write the `DagBag` import test and deliberately introduce a cycle. Confirm CI catches it.
12. Take a DAG you've written and audit it against the checklist at the end of `04`.

---

## The 60-second spoken answer

> "Airflow is a scheduler and dependency engine for batch workflows: you declare a DAG of tasks in
> Python, and it decides when each task instance runs, tracks state in a metadata database, retries,
> and gives you a UI. The thing I'd stress is that it **orchestrates, it doesn't compute** — a
> `PythonOperator` pulling 40GB into a worker is the classic anti-pattern; the right shape is a task
> that submits a Spark or Glue job and waits.
>
> The core model is data intervals, and it's what most people get wrong. A run covers `[start, end)`
> and is only triggered once `end` has passed — so a `@daily` DAG with `start_date` of 1 January first
> runs just after midnight on the **2nd**, with `logical_date` of the **1st**. It's always processing
> the previous period. That's deliberate: it makes a run a pure function of its interval, which is
> what makes backfills and re-runs possible. `execution_date` is the old name for `logical_date`, and
> in queries I use `data_interval_start`/`end` because they're unambiguous.
>
> That leads straight to the biggest footgun, `catchup`. A `start_date` a year ago with `@hourly` and
> `catchup=True` queues nearly 9,000 runs the moment you deploy. I set it explicitly every time, and
> if I do want history I cap it with `max_active_runs` and a pool.
>
> The correctness requirement is idempotency, because retries, catchups, backfills and manual clears
> all re-run the same interval. So every query is scoped to the data interval, never to `now()` —
> otherwise a backfill writes today's data for every historical date, silently — and the write is
> delete-then-insert on the partition, or an upsert. It's exactly the same argument as a Kafka
> consumer: at-least-once execution plus an idempotent write gives effectively-once data.
>
> On the mechanics: XCom is a row in the metadata DB, so it carries an S3 key, never a DataFrame. When
> the number of tasks isn't known until run time I use dynamic task mapping with `.expand()`, not a
> parse-time loop — which matters because the scheduler re-parses every DAG file every thirty seconds,
> so top-level queries or API calls are the usual reason someone's Airflow is slow. Trigger rules are
> the other thing I'd be precise about: the default `all_success` means a *skip* cascades, so the join
> after a branch needs `none_failed_min_one_success`, cleanup goes on `all_done`, and alerting on
> `one_failed`.
>
> Operationally: retries with exponential backoff and an `execution_timeout` — without the timeout a
> hung task never fails, so it never retries — but `retries=0` on validation, because bad data won't
> fix itself and retrying just delays the alert. Sensors get `mode="reschedule"` or `deferrable=True`
> and always a timeout, because the default `poke` mode holds a worker slot for the whole wait and can
> deadlock a deployment. Shared resources get a pool, because that's the only control that's global
> across DAGs. And when I'm debugging at 3am, after the log the first place I look is the Rendered
> Template view — nine times out of ten the bug is a template that resolved to something empty."
