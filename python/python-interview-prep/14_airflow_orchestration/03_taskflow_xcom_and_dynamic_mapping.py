"""
Airflow part 3 -- passing DATA between tasks, and building a VARIABLE number of tasks.

  "How do tasks share data?"                -> XCom, section 2. And what NOT to put in one.
  "Classic operators vs the TaskFlow API?"   -> section 3
  "You don't know how many files there are
   until run time. How many tasks?"          -> dynamic task mapping, section 5 -- the modern answer
  "What is templated, and what isn't?"       -> section 6 (template_fields + the macros)

Run me: python 03_taskflow_xcom_and_dynamic_mapping.py
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _mini_airflow import (                      # noqa: E402
    DAG, BashOperator, EmptyOperator, Executor, PythonOperator, TriggerRule,
    build_context, render, scheduled_runs, summarise,
)


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ 1. the classic style
section("1. the CLASSIC style: operators + explicit XCom")


def extract(**context):
    """A task's RETURN VALUE is pushed to XCom automatically, under the key `return_value`."""
    return {"order_ids": [101, 102, 103], "source": "postgres"}


def transform(ti, **context):
    """...and pulled by task_id. This is the explicit, pre-2.0 style you will still read a lot of."""
    payload = ti.xcom_pull(task_ids="extract")
    total = sum(payload["order_ids"])
    ti.xcom_push(key="checksum", value=total)          # an EXTRA xcom, under a named key
    return {"transformed": len(payload["order_ids"])}


def load(ti, **context):
    transformed = ti.xcom_pull(task_ids="transform")
    checksum = ti.xcom_pull(task_ids="transform", key="checksum")
    return f"loaded {transformed['transformed']} rows (checksum={checksum})"


with DAG("classic_style", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as classic:
    e = PythonOperator(task_id="extract", python_callable=extract)
    t = PythonOperator(task_id="transform", python_callable=transform)
    l = PythonOperator(task_id="load", python_callable=load)
    e >> t >> l

run = scheduled_runs(classic, now=datetime(2026, 1, 5))[0]
ex = Executor()
ex.run(classic, run)
print(f"\n  the XComs this run produced:")
for task_id, value in sorted(ex.xcoms.all_for_run(classic.dag_id, run.run_id).items()):
    print(f"    {task_id:12s} -> {value!r}")
print("""
  Note what is implicit and what is explicit here:
    implicit: the return value becomes an XCom under key `return_value`
    explicit: the DEPENDENCY (e >> t >> l) and the PULL (xcom_pull(task_ids="transform"))
  So the data flow and the dependency graph are declared TWICE -- and nothing stops them
  disagreeing. That duplication is the problem the TaskFlow API solves.""")


# ================================================================ 2. XCom: the rules
section("2. XCom -- what it is, and the rule that matters")
print("""  An XCom is A ROW IN AIRFLOW'S METADATA DATABASE, keyed by
  (dag_id, run_id, task_id, map_index, key). `xcom_push` INSERTs; `xcom_pull` SELECTs.

  That one fact gives you every rule:

    DO     pass small scalars and short lists: a row count, an S3 key, a batch id, a flag.
    DON'T  pass a DataFrame, a file's contents, or a 50MB JSON blob. You would be using your
           orchestrator's control-plane database as a data bus. It will be slow, it will bloat the
           metadata DB, and large values hit a hard limit (the value column is a BLOB -- commonly
           ~48KB on MySQL, ~1GB on Postgres, but the LIMIT IS NOT THE POINT).

    THE PATTERN: write the data to object storage, pass the KEY through XCom.
        def extract(**c):  s3.put_object(Bucket=B, Key=f"stage/{c['ds']}/orders.parquet", ...)
                           return f"stage/{c['ds']}/orders.parquet"       # <- 40 bytes in XCom
        def load(ti, **c): key = ti.xcom_pull(task_ids="extract"); s3.get_object(...)

    Other things to know:
      - XComs are scoped to a RUN. A task cannot read another run's XCom without asking for it
        explicitly (`include_prior_dates=True`).
      - `do_xcom_push=False` turns off the automatic return-value push (useful on a BashOperator
        whose stdout you do not want stored).
      - XComs are NOT cleaned up automatically in older versions -- `airflow db clean` exists for
        exactly this reason, and an unbounded XCom table is a real production problem.
      - A CUSTOM XCOM BACKEND (`xcom_backend` config) makes the s3-key pattern automatic: it
        serialises large values to S3/GCS and stores only a pointer. That is the production answer
        when teams keep passing big objects.""")


# ================================================================ 3. the TaskFlow API
section("3. the TaskFlow API -- the same pipeline, with the duplication removed")
print("""  The `@task` decorator (Airflow 2.0+) turns a plain function into a task, and then
  ORDINARY PYTHON FUNCTION CALLS declare both the data flow AND the dependency graph:

      @task
      def extract():                       return {"order_ids": [101, 102, 103]}
      @task
      def transform(payload):              return len(payload["order_ids"])
      @task
      def load(count):                     return f"loaded {count}"

      load(transform(extract()))           # <- this ONE line creates 3 tasks and 2 edges

  What you no longer write: `>>`, `task_id=`, `python_callable=`, `xcom_push`, `xcom_pull`.
  The XComs still exist -- the decorator just does the push/pull for you, so the data path and
  the dependency path cannot drift apart.

  When to use which, which is the real question:
      TaskFlow  -- Python-native ETL where tasks pass values. The default for new code.
      Classic   -- when you need a PROVIDER operator (S3ToRedshift, KubernetesPodOperator,
                   SQLExecuteQueryOperator). There is no @task for those, and wrapping them in
                   one would be worse.
      MIXED     -- completely normal and the usual reality:
                       files = list_files()                 # @task
                       files >> KubernetesPodOperator(...)   # classic operator
  Other decorators in the family: @task_group, @task.bash, @task.short_circuit, @task.branch,
  @task.sensor, @task.docker, @task.kubernetes.""")

# This mini version has no decorator, so here is the equivalent wiring written out longhand --
# which is precisely what @task generates for you.
with DAG("taskflow_equivalent", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as tf:
    tf_extract = PythonOperator(task_id="extract", python_callable=extract)
    tf_transform = PythonOperator(task_id="transform", python_callable=transform)
    tf_load = PythonOperator(task_id="load", python_callable=load)
    tf_extract >> tf_transform >> tf_load
print(f"  `load(transform(extract()))` is sugar for exactly this graph:\n{tf.structure()}")


# ================================================================ 4. task groups
section("4. TaskGroup -- visual grouping, and what replaced SubDAGs")
print("""  A TaskGroup collapses a set of tasks into one expandable box in the UI. It is PURELY
  organisational: no extra scheduling, no extra overhead, no separate run.

      with TaskGroup(group_id="staging") as staging:
          clean = clean_data()
          dedupe = dedupe_data()
          clean >> dedupe
      extract >> staging >> load          # you can depend on the GROUP

  Task ids become `staging.clean`, `staging.dedupe` -- so group_ids must be unique too.

  SubDagOperator was the old way and is GONE (deprecated in 2.0, removed in Airflow 3). Why it
  was bad: a SubDAG was a real DAG with its own scheduler record, it ran on the SequentialExecutor
  by default (so no parallelism inside it), and it deadlocked pools in ways that were very hard to
  debug. If you meet one in a legacy codebase, replacing it with a TaskGroup is nearly always a
  pure win.

  And note `@task_group` as the TaskFlow equivalent, which can be parameterised and even mapped.""")

with DAG("taskgroup_shape", schedule=None, start_date=datetime(2026, 1, 1)) as tg_dag:
    tg_start = EmptyOperator(task_id="extract")
    # the mini version has no TaskGroup class; the dotted ids show the shape it produces
    clean = PythonOperator(task_id="staging.clean", python_callable=lambda: "cleaned")
    dedupe = PythonOperator(task_id="staging.dedupe", python_callable=lambda: "deduped")
    tg_end = EmptyOperator(task_id="load")
    tg_start >> clean >> dedupe >> tg_end
print(f"  the dotted task_ids a TaskGroup produces:\n{tg_dag.structure()}")


# ================================================================ 5. dynamic task mapping
section("5. dynamic task mapping -- N tasks decided at RUN time (Airflow 2.3+)")
print("""  THE question: "you don't know how many files will arrive. How do you build the tasks?"

  THE WRONG ANSWER (and what everyone used to do): generate tasks at PARSE time from a query.
      for f in list_s3_files():                    # runs every ~30s on the SCHEDULER
          PythonOperator(task_id=f"process_{f}")   # and the graph changes shape between parses
  That is the top-level-code anti-pattern from file 01, plus a DAG whose history is unreadable
  because the task set changed.

  THE RIGHT ANSWER: `.expand()`. One task DEFINITION; N task INSTANCES created at run time from
  an XCom, each with its own map_index, log and retry.

      @task
      def list_files():                 return ["a.csv", "b.csv", "c.csv"]   # length unknown
      @task
      def process(name):                return f"processed {name}"

      process.expand(name=list_files())              # 3 instances this run, 50 the next

      # with constant arguments too:
      process.partial(bucket="my-lake").expand(name=list_files())
      # and over several arguments at once:
      process.expand_kwargs([{"name": "a", "rows": 1}, {"name": "b", "rows": 2}])

  Then `collect(process.expand(...))` receives the LIST of all mapped results -- a reduce step.
  (`max_map_length`, default 1024, caps the fan-out so a bad upstream cannot create 2 million
  task instances.)""")


def list_files(**context):
    """In reality: s3.list_objects_v2(...). The COUNT is not known until this runs."""
    ds = context["ds"]
    return [f"orders_{ds}_part{i}.csv" for i in range(4)]


def process_file(name, bucket="my-data-lake"):
    return f"s3://{bucket}/{name} -> 250 rows"


def summarise_all(ti, **context):
    results = ti.xcom_pull(task_ids="process_file")
    return f"reduced {len(results)} mapped results"


with DAG("dynamic_mapping", schedule="@daily", start_date=datetime(2026, 1, 1),
         catchup=False) as mapped_dag:
    lister = PythonOperator(task_id="list_files", python_callable=list_files)
    processor = PythonOperator(task_id="process_file", python_callable=process_file)
    processor.partial(bucket="my-data-lake").expand(name="list_files")   # name= from that XCom
    reducer = PythonOperator(task_id="summarise_all", python_callable=summarise_all)
    lister >> processor >> reducer

map_run = scheduled_runs(mapped_dag, now=datetime(2026, 2, 2))[0]
Executor().run(mapped_dag, map_run)
print(f"\n  {summarise(map_run)}")
print("""  Read the output: ONE `process_file` task in the code became FOUR task instances, each with
  its own map_index. In the UI they appear as a single expandable row. Each one retries
  independently, and one failing does not re-run the other three -- which is the real operational
  win over doing the loop inside a single task.""")


# ================================================================ 6. templating
section("6. Jinja templating -- and the rule about WHICH fields are templated")
print("""  Airflow renders Jinja into the fields an operator declares in `template_fields`. Nothing
  else. So this works:
      BashOperator(bash_command="load.sh --date {{ ds }}")        # bash_command IS templated
  and this does NOT -- the braces end up in the string, verbatim:
      PythonOperator(python_callable=lambda: print("{{ ds }}"))   # the BODY is never templated
  Inside a Python callable you take the value from the CONTEXT instead (`ds`, `data_interval_start`,
  `ti`), which is why every example in this folder does that.

  Check an operator's docs (or `Operator.template_fields`) when a template "doesn't work" -- nine
  times out of ten the field simply is not templated.

  The context values worth knowing:
      {{ ds }}                   logical date as YYYY-MM-DD        {{ ds_nodash }}  YYYYMMDD
      {{ data_interval_start }}  / {{ data_interval_end }}         <- PREFER THESE in queries
      {{ logical_date }}         the interval start as a datetime
      {{ run_id }}  {{ dag.dag_id }}  {{ task.task_id }}  {{ ti.try_number }}
      {{ params.x }}             DAG params, overridable per run via `conf`
      {{ var.value.my_key }}     an Airflow Variable, resolved AT RUN TIME (good) rather than
                                 Variable.get() at parse time (one DB hit every 30s -- bad)
      {{ conn.my_conn.host }}    a Connection's fields
      {{ macros.ds_add(ds, -7) }}  date arithmetic; also macros.ds_format, macros.datetime
      {{ ti.xcom_pull(task_ids="extract") }}   an XCom, straight into a templated field""")

with DAG("templating", schedule="@daily", start_date=datetime(2026, 1, 1), catchup=False,
         params={"warehouse": "analytics", "mode": "full"}) as tmpl:
    templated = BashOperator(
        task_id="templated_command",
        bash_command=("python load.py --date {{ ds }} --nodash {{ ds_nodash }} "
                      "--week-ago {{ macros.ds_add(ds, -7) }} "
                      "--warehouse {{ params.warehouse }} --bucket {{ var.value.s3_bucket }} "
                      "--host {{ conn.warehouse.host }} --run {{ run_id }}"),
    )

tmpl_run = scheduled_runs(tmpl, now=datetime(2026, 3, 2))[0]
print("\n  before rendering:")
print(f"    {templated.bash_command}")
Executor(verbose=False).run(tmpl, tmpl_run)
print("  after rendering:")
print(f"    {templated.bash_command}")


# ================================================================ 7. params and conf
section("7. params vs Variables vs Connections vs conf -- four different things")
print("""  params        declared ON THE DAG, overridable when you trigger a run. Versioned WITH the
                code, visible in the trigger form. Use for "which mode should this run use?".
  dag_run.conf  the dict passed when triggering (UI "Trigger DAG w/ config", the REST API, or
                TriggerDagRunOperator). Reachable as {{ dag_run.conf["x"] }} or via params.
  Variables     a key/value store in the metadata DB, shared across DAGs, editable in the UI
                without a deploy. Read them with `{{ var.value.key }}` (run time), NOT
                `Variable.get()` at module level (a DB query every parse).
  Connections   credentials + host for an external system, referenced by `conn_id`. Hooks and
                operators resolve them. Back them with a SECRETS BACKEND (AWS Secrets Manager,
                Vault) in production rather than storing secrets in the metadata DB.

  The decision rule: does it change per RUN (params/conf), per ENVIRONMENT (Variables, or better,
  env vars), or is it a CREDENTIAL (Connections + a secrets backend)?""")

print(f"\n  params on the DAG: {tmpl.params}")
override = scheduled_runs(tmpl, now=datetime(2026, 3, 2))[0]
override.conf = {"mode": "incremental"}                 # as if triggered with config
ctx = build_context(tmpl, override, None)
print(f"  with conf={{'mode': 'incremental'}} the merged params are: {ctx['params']}")
print(f"  so `{{{{ params.mode }}}}` renders as: "
      f"{render('{{ params[\"mode\"] }}', ctx)}  (conf wins over the DAG default)")

# EXPERIMENT 1: in section 5, make `list_files` return 8 names. The code does not change -- only the
# number of task instances does. That is the whole point of mapping.
# EXPERIMENT 2: make `process_file` raise for one specific name and re-run. Only that map_index
# fails; the others still succeed. Compare that with putting the loop inside one task.
# EXPERIMENT 3: in section 6, add `--extra {{ ti.try_number }}` to the bash_command and re-run.
# Then add `{{ nonexistent.thing }}` and see that the unresolved braces are left as-is.
# EXPERIMENT 4: try to template a PythonOperator's callable body (print("{{ ds }}")) and confirm
# the braces come out literally. Then fix it by taking `ds` as a parameter.

# EXERCISE: build a DAG that (a) lists an unknown number of partitions, (b) processes each as its
# own mapped task instance with a constant `bucket` via .partial(), (c) reduces the mapped results
# into one summary row, and (d) passes ONLY an S3 key through XCom -- never the data. Then state,
# in one sentence each, what would go wrong if you instead returned the parsed rows from (b), and
# if you had generated the tasks in a parse-time `for` loop.
