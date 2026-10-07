# 14 — Airflow & Orchestration

Pure stdlib — every file runs with `py <file>.py`, no `pip install apache-airflow` required.

Airflow is the one topic where "I've used it" and "I understand it" are very far apart. Plenty of
candidates can write a DAG by copying the one next to it; far fewer can say **when the first run
happens and why**, **what `catchup` will do to you on deploy day**, or **why the task after a branch
got skipped**. Those three questions are most of an Airflow interview.

> **Full Q&A**: [`deep_dive/34_airflow_orchestration.md`](../deep_dive/34_airflow_orchestration.md)

## How this folder runs without Airflow

[`_mini_airflow.py`](_mini_airflow.py) reimplements the Airflow **API shape** in ~450 lines of
stdlib: `with DAG(...) as dag`, `a >> [b, c] >> d`, `PythonOperator(task_id=..., python_callable=...)`,
`ti.xcom_pull(...)`, `TriggerRule.ALL_DONE`, `.expand()`, Jinja-ish templating, and a scheduler that
turns a `schedule` into data intervals. **The DAG code in `01`–`04` is the code you would write
against the real thing.**

What it deliberately does *not* model — worth knowing, because an interviewer may probe it:

- one process, synchronous: no executor, no worker pool, no real parallelism
- XComs are a dict, not metadata-DB rows (so no size limit — real XComs have one)
- `retry_delay` is recorded, not slept
- templating resolves dotted lookups and simple calls, but it is not a real Jinja environment
- no UI, no triggerer, no pools enforcement, no secrets backend

## Crib sheet

- **A run covers a DATA INTERVAL `[start, end)` and is triggered once `end` has passed.** So a
  `@daily` DAG with `start_date=1 Jan` first runs just after **midnight on 2 Jan**, with
  `logical_date = 1 Jan`. Internalise this and most scheduling questions answer themselves.
- `execution_date` is the **old** name for `logical_date` (renamed 2.2, removed in Airflow 3).
  In queries, prefer `data_interval_start` / `data_interval_end` — they're unambiguous.
- **`catchup` is the biggest footgun.** `start_date` a year ago + `@hourly` + `catchup=True` =
  8,760 runs queued the moment you deploy. **Set it explicitly, always.**
- **`start_date=datetime.now()` means the DAG may never run** — the file is re-parsed every ~30s,
  so the first interval never completes. Hardcode a fixed date.
- **Operator ≠ Task ≠ Task Instance.** The operator is the class, the task is the node in the graph,
  the task instance is a `(task, run)` pair — the thing with a state, a try number and logs.
- **Dependencies**: `a >> b`, `a >> [b, c] >> d` (fan out then in), `chain(...)` (pairwise for
  equal-length lists — *not* a mesh), `cross_downstream(...)` (a mesh).
- **A branch skips everything downstream that isn't reachable from the chosen branch**, so the join
  needs `trigger_rule="none_failed_min_one_success"`. Forget it and the whole tail dies silently.
- **The four trigger rules that matter**: `all_success` (default), `all_done` (cleanup),
  `one_failed` (alerting), `none_failed_min_one_success` (the join after a branch).
- **Tasks must be idempotent and scoped to the data interval.** `WHERE created_at >= CURRENT_DATE`
  is a correctness bug: a backfill then writes today's data for every historical date, silently.
  And the write must be delete-then-insert / upsert / partition-overwrite, or a retry doubles data.
- **XCom is a row in the metadata database.** Pass an S3 key, never a DataFrame.
- **Don't know how many tasks until run time?** Dynamic task mapping (`.expand()`), **not** a
  parse-time `for` loop over a database query.
- **Nothing expensive at module level.** The scheduler re-parses every DAG file every ~30 seconds,
  so a top-level query or API call runs forever on the scheduler. It's the #1 cause of "Airflow is
  slow".
- **Sensors**: `mode="poke"` (the default) holds a worker slot for the whole wait — ten long pokes
  can deadlock a deployment. Use `mode="reschedule"` or `deferrable=True`, and **always** a `timeout`.
- **Pools are the only control that protects a shared resource**, because every other concurrency
  knob is scoped to one DAG.
- **Cross-DAG**: Assets/Datasets (data-aware, modern) > `TriggerDagRunOperator` (push) >
  `ExternalTaskSensor` (brittle, couples schedules).

## Files

| File | Covers |
|---|---|
| `_mini_airflow.py` | the stdlib Airflow stand-in: DAG, operators, `>>`, trigger rules, XComs, templating, scheduler, executor. Read it once — it's a short, honest model of what Airflow *does* |
| `01_dag_anatomy_and_operators.py` | **the keywords and the operators** — every `DAG(...)` argument and why; operator vs task vs task instance; the operator families; all four dependency syntaxes; cycle detection; branching; a full run of the happy *and* failure paths; the no-top-level-code rule |
| `02_scheduling_backfill_and_data_intervals.py` | **the data-interval model**; `logical_date` vs `execution_date`; catchup vs backfill; the three `start_date` traps; cron vs timedelta vs presets vs Assets; why `datetime.now()` in a task is a correctness bug (demonstrated over a 3-day backfill); the four concurrency knobs; `depends_on_past` |
| `03_taskflow_xcom_and_dynamic_mapping.py` | classic operators vs the TaskFlow API; XCom rules and the S3-key pattern; TaskGroups (and why SubDAGs are gone); **dynamic task mapping** with `.expand()`/`.partial()`; Jinja templating and `template_fields`; params vs Variables vs Connections vs `conf` |
| `04_failures_retries_and_trigger_rules.py` | retries and what they *don't* fix; **every trigger rule evaluated in a matrix**; the alert-on-`one_failed` + cleanup-on-`all_done` production shape; callbacks and SLA semantics; sensor modes and the pool deadlock; pools; how to test and debug a DAG; a production checklist |

## Run them in order

```bash
cd 14_airflow_orchestration
py 01_dag_anatomy_and_operators.py
py 02_scheduling_backfill_and_data_intervals.py
py 03_taskflow_xcom_and_dynamic_mapping.py
py 04_failures_retries_and_trigger_rules.py
```

Each prints the DAG structure *and* executes real runs, so you can see states propagate. Then do
the `# EXPERIMENT:` prompts — several of them (removing the join's trigger rule, changing cleanup to
`all_success`) break the pipeline in exactly the way a real DAG breaks.

## If you want to run against real Airflow

The DAG code transfers almost unchanged. The quickest honest path:

```bash
pip install "apache-airflow==2.10.*" --constraint \
  "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.5/constraints-3.9.txt"
export AIRFLOW_HOME=~/airflow
airflow standalone          # scheduler + webserver + a SQLite metadata DB, on :8080
```

Then drop a DAG in `$AIRFLOW_HOME/dags/`, and debug single tasks without the scheduler:

```bash
airflow tasks test orders_etl extract_orders 2026-01-01    # one task, no state recorded
airflow dags test orders_etl 2026-01-01                    # the whole DAG, in-process
```

The constraint file matters — Airflow has a very large dependency tree and an unconstrained install
usually resolves to something broken. On Windows, use WSL2 or Docker (`astro dev start`, or the
official `docker-compose.yaml`); Airflow does not officially support native Windows.

## Version notes (say the version you've used)

- **2.0** — TaskFlow API (`@task`), the scheduler became HA, `SubDagOperator` deprecated
- **2.2** — `execution_date` → `logical_date`, `data_interval_*` added, deferrable operators + the
  **triggerer**
- **2.3** — **dynamic task mapping** (`.expand()`)
- **2.4** — `schedule=` replaced `schedule_interval`; `Dataset` (data-aware scheduling);
  `DummyOperator` → `EmptyOperator`
- **2.5–2.10** — `dag.test()`, setup/teardown tasks, object storage, incremental UI work
- **3.0** — `execution_date` and SubDAGs **removed**, DAG versioning, a Task SDK that decouples task
  code from the scheduler, `Dataset` renamed **`Asset`**, a new React UI, scheduler-managed backfills

Behaviour genuinely differs across these, so in an interview name your version — "on 2.x we did X"
is a stronger answer than a version-free assertion. Where this folder makes a version-specific
claim it says so; `catchup`'s global default in particular has moved, which is exactly why every
example here sets it explicitly.

## Where this connects

- **Idempotency** is the same argument as the Kafka→Aurora sink:
  [`deep_dive/31`](../deep_dive/31_kafka_python_integration.md) — at-least-once execution plus an
  idempotent write gives effectively-once data.
- **Lambda ↔ Airflow** orchestration patterns:
  [`09_aws_lambda_streaming/`](../09_aws_lambda_streaming/) and `QUESTION_INDEX.md` Part 2.
- **Processing a file too big for one task**:
  [`deep_dive/30`](../deep_dive/30_large_file_processing.md) — Airflow fans the chunks out, it
  doesn't process them itself.
- **Alerting on symptoms, not causes**, and why an output-freshness check often beats an SLA:
  [`deep_dive/28`](../deep_dive/28_observability_distributed_systems.md).
- **Retries, backoff and circuit breakers** as code:
  [`08_scaling_production_resilience/`](../08_scaling_production_resilience/).
