"""
A ~400-line stand-in for the parts of Apache Airflow this folder teaches: DAGs, operators,
dependencies, trigger rules, XComs, branching, retries, sensors, dynamic task mapping, Jinja-ish
templating, and a scheduler that produces DAG runs from a schedule.

WHY A FAKE: real Airflow is a multi-process system with a metadata database, a scheduler, a
webserver and a triggerer. You cannot `pip install apache-airflow` and meaningfully run a DAG in a
20-line script -- and it is awkward on Windows. So this module mirrors the REAL API SHAPE
(`with DAG(...) as dag`, `a >> b`, `PythonOperator(task_id=..., python_callable=...)`,
`ti.xcom_pull(task_ids=...)`, `TriggerRule.ALL_DONE`, `.expand()`) closely enough that the code in
01-04 is the code you would write against the real thing, while staying pure stdlib.

WHERE IT DIFFERS FROM REAL AIRFLOW -- know these, because an interviewer may well probe them:
  - runs in ONE process, synchronously; no executor, no worker pool, no parallelism
  - XComs live in a dict, not a metadata DB (so no size limit -- real XComs are DB rows)
  - templating resolves dotted lookups and simple calls; it is NOT a real Jinja environment
    (no loops, no filters, no `{% if %}`)
  - retry_delay is NOT actually slept; it is recorded so you can assert on it
  - no UI, no connections/variables backend, no pools enforcement across DAGs

Import it from a sibling file (01-04 do `sys.path.insert` on their own directory first, so they
stay runnable from any working directory).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# ================================================================ task states
class State:
    """Airflow's TaskInstance states -- the subset that matters for dependency evaluation."""
    NONE = "none"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UPSTREAM_FAILED = "upstream_failed"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"

    FINISHED = {SUCCESS, FAILED, SKIPPED, UPSTREAM_FAILED}


class TriggerRule:
    """When should this task run, given its upstream tasks' states?

    ALL_SUCCESS is the default and the reason a failed task "cancels" everything downstream.
    The two you actually reach for in production are ALL_DONE (cleanup that must always run) and
    NONE_FAILED_MIN_ONE_SUCCESS (the join after a branch).
    """
    ALL_SUCCESS = "all_success"                               # default
    ALL_FAILED = "all_failed"
    ALL_DONE = "all_done"                                     # cleanup / teardown
    ALL_SKIPPED = "all_skipped"
    ONE_SUCCESS = "one_success"
    ONE_FAILED = "one_failed"                                 # alerting
    ONE_DONE = "one_done"
    NONE_FAILED = "none_failed"
    NONE_FAILED_MIN_ONE_SUCCESS = "none_failed_min_one_success"  # the join after a branch
    NONE_SKIPPED = "none_skipped"
    ALWAYS = "always"


def evaluate_trigger_rule(rule, upstream_states):
    """Returns (should_run, resulting_state_if_not_run).

    This function IS the dependency engine -- everything Airflow does with red/green boxes in the
    UI comes down to running this per task instance.
    """
    if rule == TriggerRule.ALWAYS or not upstream_states:
        return True, None

    states = list(upstream_states)
    successes = states.count(State.SUCCESS)
    failures = sum(1 for s in states if s in (State.FAILED, State.UPSTREAM_FAILED))
    skips = states.count(State.SKIPPED)
    done = sum(1 for s in states if s in State.FINISHED)
    total = len(states)

    if rule == TriggerRule.ALL_SUCCESS:
        if failures:
            return False, State.UPSTREAM_FAILED
        if skips:
            return False, State.SKIPPED          # a skipped upstream SKIPS the downstream
        return successes == total, State.SKIPPED
    if rule == TriggerRule.ALL_DONE:
        return done == total, State.SKIPPED
    if rule == TriggerRule.ALL_FAILED:
        return failures == total, State.SKIPPED
    if rule == TriggerRule.ALL_SKIPPED:
        return skips == total, State.SKIPPED
    if rule == TriggerRule.ONE_SUCCESS:
        return successes >= 1, State.SKIPPED
    if rule == TriggerRule.ONE_FAILED:
        return failures >= 1, State.SKIPPED
    if rule == TriggerRule.ONE_DONE:
        return done >= 1, State.SKIPPED
    if rule == TriggerRule.NONE_FAILED:
        if failures:
            return False, State.UPSTREAM_FAILED
        return done == total, State.SKIPPED
    if rule == TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS:
        if failures:
            return False, State.UPSTREAM_FAILED
        return done == total and successes >= 1, State.SKIPPED
    if rule == TriggerRule.NONE_SKIPPED:
        if skips:
            return False, State.SKIPPED
        return done == total, State.SKIPPED
    raise ValueError(f"unknown trigger rule {rule!r}")


# ================================================================ XCom + task instance
class XComStore:
    """Real XComs are ROWS IN THE METADATA DATABASE, keyed by (dag_id, run_id, task_id, key).
    That is why they must stay small -- see 03_taskflow_xcom_and_dynamic_mapping.py."""

    def __init__(self):
        self._store: dict = {}

    def push(self, dag_id, run_id, task_id, key, value):
        self._store[(dag_id, run_id, task_id, key)] = value

    def pull(self, dag_id, run_id, task_ids, key="return_value", default=None):
        if isinstance(task_ids, str):
            return self._store.get((dag_id, run_id, task_ids, key), default)
        return [self._store.get((dag_id, run_id, t, key), default) for t in task_ids]

    def all_for_run(self, dag_id, run_id):
        return {k[2]: v for k, v in self._store.items() if k[0] == dag_id and k[1] == run_id}


class TaskInstance:
    """One (task, dag_run) pair -- the thing that actually has a state and a try number."""

    def __init__(self, task, dag_run, xcoms: XComStore):
        self.task = task
        self.task_id = task.task_id
        self.dag_run = dag_run
        self.state = State.NONE
        self.try_number = 0
        self.map_index = -1                   # -1 = not a mapped task instance
        self.recorded_sleeps: list = []        # retry delays we WOULD have slept
        self._xcoms = xcoms

    # -- the two methods every Airflow developer uses
    def xcom_push(self, key, value):
        self._xcoms.push(self.dag_run.dag_id, self.dag_run.run_id, self.task_id, key, value)

    def xcom_pull(self, task_ids, key="return_value", default=None):
        return self._xcoms.pull(self.dag_run.dag_id, self.dag_run.run_id, task_ids, key, default)

    def __repr__(self):
        suffix = "" if self.map_index < 0 else f"[{self.map_index}]"
        return f"<TI {self.task_id}{suffix} {self.state}>"


# ================================================================ operators
UNSET = object()      # sentinel: "the caller did not pass this", so default_args can supply it


class BaseOperator:
    """Every operator is a subclass of this. The constructor keywords here are the ones you are
    most likely to be asked to name.

    Note the resolution order for each keyword, which mirrors real Airflow:
        explicit task kwarg  >  the DAG's default_args  >  the hard-coded default
    """

    template_fields: tuple = ()               # ONLY these fields get Jinja-rendered

    # keyword -> hard default, for every field default_args is allowed to supply
    DEFAULTABLE = {
        "owner": "airflow",
        "retries": 0,
        "retry_delay": timedelta(minutes=5),
        "trigger_rule": TriggerRule.ALL_SUCCESS,
        "depends_on_past": False,
        "wait_for_downstream": False,
        "pool": "default_pool",
        "priority_weight": 1,
        "do_xcom_push": True,
        "sla": None,
        "execution_timeout": None,
        "on_failure_callback": None,
        "on_success_callback": None,
        "on_retry_callback": None,
        "max_active_tis_per_dag": None,
    }

    def __init__(self, task_id, dag=None, **kwargs):
        self.task_id = task_id
        self.dag = dag or DAG.current
        default_args = self.dag.default_args if self.dag is not None else {}

        for name, hard_default in self.DEFAULTABLE.items():
            explicit = kwargs.pop(name, UNSET)
            if explicit is not UNSET:
                value = explicit                       # the task won
            elif name in default_args:
                value = default_args[name]             # the DAG's default_args won
            else:
                value = hard_default
            setattr(self, name, value)

        self.upstream: list = []
        self.downstream: list = []
        self.expand_over = None                # set by .expand(), for dynamic task mapping
        self.partial_kwargs: dict = {}
        if self.dag is not None:
            self.dag.add_task(self)

    # -- dependency operators: a >> b  and  b << a
    def __rshift__(self, other):
        for task in _as_list(other):
            self.downstream.append(task)
            task.upstream.append(self)
        return other

    def __lshift__(self, other):
        for task in _as_list(other):
            task.__rshift__(self)
        return other

    # `[a, b] >> c` : Python finds no list.__rshift__, so it falls back to c.__rrshift__([a, b]).
    # Real Airflow defines these for exactly this reason -- it is what makes the fan-in idiom work.
    def __rrshift__(self, other):
        for task in _as_list(other):
            task.__rshift__(self)
        return self

    def __rlshift__(self, other):
        for task in _as_list(other):
            self.__rshift__(task)
        return self

    def set_downstream(self, other):
        return self.__rshift__(other)

    def set_upstream(self, other):
        return self.__lshift__(other)

    # -- dynamic task mapping (Airflow 2.3+)
    def partial(self, **kwargs):
        self.partial_kwargs.update(kwargs)
        return self

    def expand(self, **kwargs):
        """`.expand(x=[1,2,3])` creates one task instance PER element at run time."""
        if len(kwargs) != 1:
            raise ValueError("this mini version supports expanding exactly one argument")
        self.expand_over = kwargs
        return self

    def execute(self, context):
        raise NotImplementedError

    def __repr__(self):
        return f"<{type(self).__name__}: {self.task_id}>"


def _as_list(obj):
    return list(obj) if isinstance(obj, (list, tuple, set)) else [obj]


class EmptyOperator(BaseOperator):
    """Was `DummyOperator` before Airflow 2.4. A no-op used purely to shape the graph --
    a start/end marker, or a single join point so N tasks don't each need N edges."""

    def execute(self, context):
        return None


class PythonOperator(BaseOperator):
    """The workhorse. `op_kwargs` are passed to the callable; add `**context` or
    `ti`/`ds`/`data_interval_start` as parameters to receive the run context."""

    template_fields = ("op_kwargs",)

    def __init__(self, task_id, python_callable, op_kwargs=None, **kwargs):
        super().__init__(task_id, **kwargs)
        self.python_callable = python_callable
        self.op_kwargs = dict(op_kwargs or {})

    def execute(self, context):
        import inspect
        params = inspect.signature(self.python_callable).parameters
        call_kwargs = dict(self.op_kwargs)
        if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
            call_kwargs.update(context)       # def f(**context)
        else:
            for name in params:
                if name in context and name not in call_kwargs:
                    call_kwargs[name] = context[name]
        return self.python_callable(**call_kwargs)


class BashOperator(BaseOperator):
    """`bash_command` is a TEMPLATE FIELD, which is how `--date {{ ds }}` works."""

    template_fields = ("bash_command",)

    def __init__(self, task_id, bash_command, **kwargs):
        super().__init__(task_id, **kwargs)
        self.bash_command = bash_command

    def execute(self, context):
        print(f"         $ {self.bash_command}")
        return self.bash_command              # real Airflow pushes the last stdout line


class BranchPythonOperator(BaseOperator):
    """Returns the task_id(s) to FOLLOW. Every other direct downstream task is SKIPPED --
    and by default a skip cascades, which is why the join needs a trigger rule."""

    def __init__(self, task_id, python_callable, op_kwargs=None, **kwargs):
        super().__init__(task_id, **kwargs)
        self.python_callable = python_callable
        self.op_kwargs = dict(op_kwargs or {})

    def execute(self, context):
        return PythonOperator.execute(self, context)


class ShortCircuitOperator(BaseOperator):
    """Falsy return -> skip EVERYTHING downstream. The 'is there anything to do?' guard."""

    def __init__(self, task_id, python_callable, op_kwargs=None, **kwargs):
        super().__init__(task_id, **kwargs)
        self.python_callable = python_callable
        self.op_kwargs = dict(op_kwargs or {})

    def execute(self, context):
        return PythonOperator.execute(self, context)


class BaseSensorOperator(BaseOperator):
    """Waits for something. The `mode` keyword is the interview question:

      mode="poke"       (default) HOLDS a worker slot for the whole wait -- deadlocks a pool
      mode="reschedule"           releases the slot between pokes
      deferrable=True             hands off to the triggerer; frees the slot entirely (async)
    """

    def __init__(self, task_id, poke_fn, mode="poke", poke_interval=60, timeout=60 * 60 * 7,
                 exponential_backoff=False, deferrable=False, **kwargs):
        super().__init__(task_id, **kwargs)
        self.poke_fn = poke_fn
        self.mode = mode
        self.poke_interval = poke_interval
        self.timeout = timeout
        self.exponential_backoff = exponential_backoff
        self.deferrable = deferrable
        self.pokes = 0

    def poke(self, context):
        self.pokes += 1
        return self.poke_fn(context)

    def execute(self, context):
        waited = 0
        while not self.poke(context):
            waited += self.poke_interval
            if waited >= self.timeout:
                raise TimeoutError(f"{self.task_id}: sensor timed out after {waited}s")
        return True


class TriggerDagRunOperator(BaseOperator):
    """Start another DAG. `wait_for_completion=True` makes this DAG block on it."""

    template_fields = ("conf", "trigger_dag_id")   # so `conf={"run": "{{ run_id }}"}` renders

    def __init__(self, task_id, trigger_dag_id, conf=None, wait_for_completion=False, **kwargs):
        super().__init__(task_id, **kwargs)
        self.trigger_dag_id = trigger_dag_id
        self.conf = conf or {}
        self.wait_for_completion = wait_for_completion

    def execute(self, context):
        print(f"         triggered DAG {self.trigger_dag_id!r} with conf={self.conf}"
              f"{' (waiting)' if self.wait_for_completion else ''}")
        return self.trigger_dag_id


# ================================================================ the DAG
class DAG:
    """The keywords in this constructor are the single most likely Airflow interview question."""

    current: "DAG | None" = None

    def __init__(self, dag_id, schedule=None, start_date=None, end_date=None, catchup=False,
                 default_args=None, max_active_runs=16, max_active_tasks=16, tags=None,
                 params=None, description=None, dagrun_timeout=None, doc_md=None):
        self.dag_id = dag_id
        self.schedule = schedule
        self.start_date = start_date
        self.end_date = end_date
        self.catchup = catchup
        self.default_args = dict(default_args or {})
        self.max_active_runs = max_active_runs
        self.max_active_tasks = max_active_tasks
        self.tags = list(tags or [])
        self.params = dict(params or {})
        self.description = description
        self.dagrun_timeout = dagrun_timeout
        self.doc_md = doc_md
        self.tasks: dict = {}

    # -- `with DAG(...) as dag:` so operators find their DAG implicitly
    def __enter__(self):
        DAG.current = self
        return self

    def __exit__(self, *exc):
        DAG.current = None
        return False

    def add_task(self, task):
        """Airflow raises on a duplicate task_id -- a real and easily-made mistake when a DAG is
        generated in a loop. (default_args are applied in BaseOperator.__init__.)"""
        if task.task_id in self.tasks:
            raise ValueError(f"duplicate task_id {task.task_id!r} in DAG {self.dag_id!r}")
        self.tasks[task.task_id] = task

    def topological_order(self):
        """Kahn's algorithm -- and it is what DETECTS A CYCLE, which is the 'A' in DAG."""
        indegree = {tid: len(t.upstream) for tid, t in self.tasks.items()}
        ready = sorted([tid for tid, n in indegree.items() if n == 0])
        order = []
        while ready:
            tid = ready.pop(0)
            order.append(tid)
            for down in self.tasks[tid].downstream:
                indegree[down.task_id] -= 1
                if indegree[down.task_id] == 0:
                    ready.append(down.task_id)
                    ready.sort()
        if len(order) != len(self.tasks):
            unresolved = sorted(set(self.tasks) - set(order))
            raise ValueError(f"CYCLE DETECTED in {self.dag_id!r}, involving: {unresolved}")
        return order

    def structure(self):
        lines = []
        for tid in self.topological_order():
            task = self.tasks[tid]
            down = ", ".join(t.task_id for t in task.downstream) or "-"
            lines.append(f"    {tid:28s} -> {down}")
        return "\n".join(lines)

    def __repr__(self):
        return f"<DAG {self.dag_id!r}: {len(self.tasks)} tasks, schedule={self.schedule!r}>"


def chain(*tasks):
    """chain(a, b, c) == a >> b >> c.

    Lists behave exactly as in real Airflow, and this is the subtle bit:
      - single >> list   : fan out
      - list   >> single : fan in
      - list   >> list   : PAIRWISE (zipped), and the lengths MUST match -- it is NOT a mesh.
                           For a mesh you want cross_downstream().
    """
    for upstream, downstream in zip(tasks, tasks[1:]):
        up_list, down_list = _as_list(upstream), _as_list(downstream)
        both_lists = isinstance(upstream, (list, tuple, set)) and             isinstance(downstream, (list, tuple, set))
        if both_lists:
            if len(up_list) != len(down_list):
                raise ValueError(
                    f"chain() got lists of different length ({len(up_list)} and "
                    f"{len(down_list)}); it zips them pairwise, so they must match")
            for u, d in zip(up_list, down_list):      # PAIRWISE, not a mesh
                u >> d
        else:
            for u in up_list:
                for d in down_list:
                    u >> d


def cross_downstream(from_tasks, to_tasks):
    """Every task in the first list becomes upstream of every task in the second (a full mesh)."""
    for u in _as_list(from_tasks):
        for d in _as_list(to_tasks):
            u >> d


# ================================================================ DAG runs + scheduling
@dataclass
class DagRun:
    dag_id: str
    run_id: str
    logical_date: datetime
    data_interval_start: datetime
    data_interval_end: datetime
    run_type: str = "scheduled"
    conf: dict = field(default_factory=dict)
    state: str = State.NONE
    task_instances: dict = field(default_factory=dict)

    @property
    def would_start_after(self):
        """THE scheduling insight: a run for interval [start, end) is only triggered once `end`
        has passed -- because the data for that interval does not exist until then."""
        return self.data_interval_end


def parse_schedule(schedule):
    """Returns a timedelta for the schedules this mini version understands.
    Real Airflow accepts a cron string, a timedelta, a Timetable, or a list of Assets/Datasets."""
    presets = {
        "@hourly": timedelta(hours=1), "0 * * * *": timedelta(hours=1),
        "@daily": timedelta(days=1), "0 0 * * *": timedelta(days=1),
        "@weekly": timedelta(weeks=1), "0 0 * * 0": timedelta(weeks=1),
    }
    if isinstance(schedule, timedelta):
        return schedule
    if schedule in presets:
        return presets[schedule]
    if isinstance(schedule, str) and re.fullmatch(r"0 \d+ \* \* \*", schedule):
        return timedelta(days=1)              # "0 2 * * *" -> daily at 02:00
    raise ValueError(f"this mini scheduler does not understand schedule={schedule!r}")


def scheduled_runs(dag, now, limit=20):
    """What the SCHEDULER would create, given `now`.

    Reproduces the two behaviours people get wrong:
      1. a run for [start, end) is created only AFTER end has passed
      2. catchup=True creates every missed interval since start_date (a backfill storm);
         catchup=False creates only the most recent one
    """
    if dag.schedule is None:
        return []
    delta = parse_schedule(dag.schedule)
    runs = []
    interval_start = dag.start_date
    while interval_start + delta <= now and len(runs) < limit:
        interval_end = interval_start + delta
        if dag.end_date and interval_end > dag.end_date:
            break
        runs.append(DagRun(
            dag_id=dag.dag_id,
            run_id=f"scheduled__{interval_start.isoformat()}",
            logical_date=interval_start,          # == data_interval_start for a cron schedule
            data_interval_start=interval_start,
            data_interval_end=interval_end,
        ))
        interval_start = interval_end
    if not dag.catchup and runs:
        runs = runs[-1:]                          # only the latest interval
    return runs


# ================================================================ templating + context
TEMPLATE = re.compile(r"\{\{\s*([^}]+?)\s*\}\}")


def build_context(dag, dag_run, ti):
    """The `context` dict Airflow passes to every task, and the namespace Jinja renders against."""
    ds = dag_run.data_interval_start.strftime("%Y-%m-%d")
    return {
        "dag": dag, "dag_run": dag_run, "ti": ti, "task_instance": ti,
        "task": getattr(ti, "task", None),        # ti=None is allowed: render DAG-level params only
        "run_id": dag_run.run_id,
        "logical_date": dag_run.logical_date,
        "data_interval_start": dag_run.data_interval_start,
        "data_interval_end": dag_run.data_interval_end,
        "ds": ds,
        "ds_nodash": ds.replace("-", ""),
        "prev_data_interval_start_success": None,
        "params": {**dag.params, **dag_run.conf},
        "macros": _Macros(),
        "var": {"value": {"env": "prod", "s3_bucket": "my-data-lake"}},
        "conn": {"warehouse": type("C", (), {"host": "db.internal", "schema": "analytics"})()},
    }


class _Macros:
    @staticmethod
    def ds_add(ds, days):
        return (datetime.strptime(ds, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")

    @staticmethod
    def ds_format(ds, from_fmt, to_fmt):
        return datetime.strptime(ds, from_fmt).strftime(to_fmt)


DOTTED = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*$")


def _resolve_dotted(expr, context):
    """Jinja resolves `a.b` by trying ATTRIBUTE access first and falling back to ITEM access.
    That is why `{{ params.warehouse }}` works on a plain dict, and why plain Python `eval`
    (which would need `params["warehouse"]`) is not a faithful stand-in on its own."""
    first, *rest = expr.split(".")
    value = context[first]
    for part in rest:
        try:
            value = getattr(value, part)
        except AttributeError:
            value = value[part]
    return value


def render(value, context):
    """A deliberately small stand-in for Jinja. It handles the two forms that matter here:
    dotted lookups (`{{ params.warehouse }}`, `{{ var.value.key }}`, `{{ conn.x.host }}`) with
    Jinja's attribute-then-item fallback, and expressions/calls (`{{ macros.ds_add(ds, -7) }}`).
    An unresolvable expression is left in place, exactly as a missing Jinja variable would be
    visible to you in the rendered-template view of the UI."""
    if isinstance(value, dict):
        return {k: render(v, context) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, context) for v in value]
    if not isinstance(value, str):
        return value

    def substitute(match):
        expr = match.group(1)
        if DOTTED.match(expr):
            try:
                return str(_resolve_dotted(expr, context))
            except (KeyError, AttributeError, TypeError):
                return match.group(0)
        try:
            return str(eval(expr, {"__builtins__": {}}, context))   # noqa: S307 - demo only
        except Exception:
            return match.group(0)

    return TEMPLATE.sub(substitute, value)


# ================================================================ the executor
class Executor:
    """Runs one DAG run to completion, in topological order, honouring trigger rules, branch
    skips, short-circuits and retries. Real Airflow does this across many worker processes with a
    database as the source of truth; the LOGIC is the same."""

    def __init__(self, verbose=True):
        self.xcoms = XComStore()
        self.verbose = verbose
        self.events: list = []

    def log(self, message):
        self.events.append(message)
        if self.verbose:
            print(message)

    def run(self, dag, dag_run, fail_tasks=(), flaky_tasks=None):
        """fail_tasks: task_ids that always raise. flaky_tasks: {task_id: times_to_fail}."""
        flaky = dict(flaky_tasks or {})
        dag.topological_order()                     # validates: raises on a cycle
        for tid in dag.tasks:
            dag_run.task_instances[tid] = TaskInstance(dag.tasks[tid], dag_run, self.xcoms)

        # task_id -> why it was skipped. Real Airflow's SkipMixin does the same bookkeeping.
        skipped_upfront: dict = {}

        for tid in dag.topological_order():
            task = dag.tasks[tid]
            ti = dag_run.task_instances[tid]
            upstream_states = [dag_run.task_instances[u.task_id].state for u in task.upstream]

            if tid in skipped_upfront:
                ti.state = State.SKIPPED
                self.log(f"    {tid:28s} SKIPPED   ({skipped_upfront[tid]})")
                continue

            should_run, blocked_state = evaluate_trigger_rule(task.trigger_rule, upstream_states)
            if not should_run:
                ti.state = blocked_state
                self.log(f"    {tid:28s} {blocked_state.upper():9s} "
                         f"(trigger_rule={task.trigger_rule}, upstream={upstream_states})")
                continue

            # -- expand(): one task instance per mapped value (dynamic task mapping)
            if task.expand_over:
                (arg_name, values), = task.expand_over.items()
                if isinstance(values, str):                      # an XCom reference
                    values = self.xcoms.pull(dag.dag_id, dag_run.run_id, values) or []
                results = []
                for index, value in enumerate(values):
                    mapped = TaskInstance(task, dag_run, self.xcoms)
                    mapped.map_index = index
                    context = build_context(dag, dag_run, mapped)
                    call = {**task.partial_kwargs, arg_name: value}
                    results.append(task.python_callable(**call))
                    self.log(f"    {tid}[{index}]{'':<{max(0, 22 - len(tid))}} SUCCESS   "
                             f"{arg_name}={value!r} -> {results[-1]!r}")
                ti.state = State.SUCCESS
                ti.xcom_push("return_value", results)
                continue

            # -- normal execution, with retries
            context = build_context(dag, dag_run, ti)
            for field_name in task.template_fields:
                setattr(task, field_name, render(getattr(task, field_name), context))

            attempts = task.retries + 1
            for attempt in range(1, attempts + 1):
                ti.try_number = attempt
                try:
                    if tid in fail_tasks:
                        raise RuntimeError("deliberate failure")
                    if flaky.get(tid, 0) > 0:
                        flaky[tid] -= 1
                        raise ConnectionError("transient failure")
                    result = task.execute(context)
                except Exception as exc:
                    if attempt < attempts:
                        delay = task.retry_delay
                        ti.recorded_sleeps.append(delay)
                        self.log(f"    {tid:28s} RETRY {attempt}/{task.retries} after "
                                 f"{int(delay.total_seconds())}s ({type(exc).__name__}: {exc})")
                        if task.on_retry_callback:
                            task.on_retry_callback(context)
                        continue
                    ti.state = State.FAILED
                    self.log(f"    {tid:28s} FAILED    ({type(exc).__name__}: {exc}) "
                             f"after {attempt} attempt(s)")
                    if task.on_failure_callback:
                        task.on_failure_callback(context)
                    break
                else:
                    ti.state = State.SUCCESS
                    if task.do_xcom_push and result is not None:
                        ti.xcom_push("return_value", result)
                    detail = f" -> {result!r}" if result is not None and not isinstance(
                        task, BashOperator) else ""
                    self.log(f"    {tid:28s} SUCCESS{detail}")
                    if task.on_success_callback:
                        task.on_success_callback(context)

                    # BRANCHING -- this is Airflow's skip_all_except, and the algorithm matters:
                    # skip everything downstream of the branch EXCEPT what is reachable from the
                    # chosen branch(es). That is why a join after a branch is NOT skipped, and why
                    # it only needs a relaxed trigger_rule (one upstream will be `skipped`).
                    if isinstance(task, BranchPythonOperator):
                        chosen = set(_as_list(result))
                        unknown = chosen - set(dag.tasks)
                        if unknown:
                            raise ValueError(
                                f"{tid} returned task_id(s) that are not in the DAG: "
                                f"{sorted(unknown)}")
                        reachable_from_chosen = set(chosen)
                        for chosen_id in chosen:
                            reachable_from_chosen |= _descendants(dag.tasks[chosen_id])
                        for skip_id in _descendants(task) - reachable_from_chosen:
                            skipped_upfront[skip_id] = f"not reachable from branch {sorted(chosen)}"

                    # SHORT-CIRCUIT -- a falsy return skips the ENTIRE downstream subtree, with no
                    # exceptions. (`ignore_downstream_trigger_rules=False` narrows it to direct
                    # children in real Airflow; the default True is what is shown here.)
                    if isinstance(task, ShortCircuitOperator) and not result:
                        for skip_id in _descendants(task):
                            skipped_upfront[skip_id] = "short-circuited (falsy condition)"
                    break

        states = [ti.state for ti in dag_run.task_instances.values()]
        dag_run.state = State.FAILED if State.FAILED in states or \
            State.UPSTREAM_FAILED in states else State.SUCCESS
        return dag_run


def _descendants(task, seen=None):
    """Every task reachable downstream -- which is how far a branch skip cascades."""
    seen = seen if seen is not None else set()
    for down in task.downstream:
        if down.task_id not in seen:
            seen.add(down.task_id)
            _descendants(down, seen)
    return seen


def summarise(dag_run):
    """One line per DAG run, the way you would read it off the UI's grid view."""
    counts: dict = {}
    for ti in dag_run.task_instances.values():
        counts[ti.state] = counts.get(ti.state, 0) + 1
    tally = ", ".join(f"{state}={n}" for state, n in sorted(counts.items()))
    return f"{dag_run.run_id} -> {dag_run.state.upper()}  ({tally})"
