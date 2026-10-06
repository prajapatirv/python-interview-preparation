# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this workspace is

This is `E:\Ravi_Workspace\python-interview-preparation`, a personal practice/interview-prep
workspace, not a single deployable application. It has three areas:

- **`python-interview-prep/`** — the active, structured project: a hands-on Python interview-prep
  lab with 13 numbered topic folders (core language through Kafka, GenAI patterns, framework
  internals and system-design scenarios) plus a `deep_dive/` documentation set. This is where
  nearly all commands and architecture notes below apply.
- **`material_ref/`** — the source interview-prep PDFs the notes are distilled from. Read-only
  reference; see `material_ref/README.md` for which three of the six actually contain content.
- **`Java/`** and **`python-interview-prep/legacy_examples/`** — unstructured scratch files with
  no build system or tests. Treat anything here as reference material only, not code to maintain
  to the same standard as `python-interview-prep/`.

All work should assume `python-interview-prep/` as the working root unless told otherwise.

## Commands

Run from `python-interview-prep/`.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt  # installs everything; see requirements.txt for which
                                  # folder needs which extra (pandas, fastapi, confluent-kafka, redis)
```

**Tests** (pytest.ini lives at the project root and governs discovery):

```bash
pytest                                          # entire suite (04, 05, 11) — 54 tests in 11 alone
pytest 04_testing_tdd -v
pytest 05_web_apis_fastapi -v
pytest 11_coding_challenges -v
pytest 11_coding_challenges/01_anagram_grouping.py::test_sorted_key -v   # single test
pytest 11_coding_challenges/05_retry_decorator.py -v                     # the retry decorator
pytest -k "empty"                               # every test whose name matches
pytest --cov=src --cov-report=term-missing      # needs pytest-cov (not in requirements.txt)
```

**Running a single example file** (every numbered `.py` file in every topic folder is directly
executable and self-contained):

```bash
python 01_python_core/03_decorators.py
python 02_concurrency/benchmark_concurrency_models.py
```

**FastAPI app** (`05_web_apis_fastapi/`):

```bash
cd 05_web_apis_fastapi
uvicorn app.main:app --reload      # serves on :8000, interactive docs at /docs
```

**Local Kafka broker** (`06_kafka/`, optional — most files run and teach the concept without it):

```bash
cd 06_kafka
docker compose -f docker-compose.kafka.yml up -d
python 01_producer_basics.py
python 02_consumer_basics.py       # in a second terminal
docker compose -f docker-compose.kafka.yml down -v
```

There is no lint/format tooling configured in this repo.

## Architecture

### The topic-folder convention

Every numbered folder (`01_python_core/` … `13_system_design_scenarios/`) follows the same shape:
a `README.md` with a condensed crib sheet + file map, then numbered `.py` files each runnable
standalone (`python NN_name.py`) with inline `# EXPERIMENT:` prompts and `# EXERCISE` blocks at
the end. Files are written to have zero required dependencies wherever the topic allows —
concurrency, resilience patterns, caching, queues, AWS Lambda, framework internals, GenAI and
system-design folders all use pure-stdlib simulations (`FakeRedis`, `SimpleQueue`, `FakeS3Client`,
`FakeBroker`, `FakeAurora`, a fake pod fleet + load balancer, a mocked LLM, a miniature Schema
Registry, a hand-built DI container) that mirror the real library's API shape exactly, so the
pattern is visible without provisioning infrastructure. Only `03_pandas_data_handling/`,
`05_web_apis_fastapi/`, and (optionally) `06_kafka/01`–`02` need real external packages/services.

All 53 stdlib-only examples are expected to run clean; verify with:

```bash
for f in 01_python_core/*.py 02_concurrency/*.py 06_kafka/0[3-8]*.py 07_caching_queues/*.py \
         08_scaling_production_resilience/*.py 09_aws_lambda_streaming/*.py \
         10_genai_llm_patterns/*.py 11_coding_challenges/*.py 12_framework_internals/*.py \
         13_system_design_scenarios/*.py; do
  py "$f" >/dev/null 2>&1 && echo "ok   $f" || echo "FAIL $f"
done
```

Two of those are slower than the rest by design: `02_concurrency/01_threading_demo.py` and
`01_python_core/11_java_to_python_bridge.py` (~7s each, from deliberate `sleep`-driven race demos).
`09_aws_lambda_streaming/03_large_file_processing.py` generates a ~13MB temp file under
`tempfile.mkdtemp()` and deletes it on exit — raise its `ROWS` constant to feel the memory
behaviour, but note peak memory is designed *not* to move.

### `deep_dive/` — the long-form documentation set

`deep_dive/` holds **32 long-form Q&A documents**, one per interview topic, and is the answer to
"the folder READMEs are one-liners, I need the full answer". Each follows a fixed structure:
*What interviewers are actually probing* → *Must-know points* → *Interview questions and full
answers* (multi-paragraph, with code) → *A worked example* → *Hands-on drills* → *The 60-second
spoken answer*. Most carry a **Java contrast** block where semantics genuinely differ.

The division of labour matters and should be preserved when editing:

- **Folder `README.md`** = crib sheet, for revision. One or two lines per concept.
- **`QUESTION_INDEX.md`** = a lookup table, question → the exact line that demonstrates it.
- **`deep_dive/NN_*.md`** = the full treatment, with trade-offs and failure modes.

`deep_dive/README.md` is the index and carries the topic → document map plus a day-before
checklist. When adding a runnable file, add a row to its folder README's file table, a Q&A block
to `QUESTION_INDEX.md`, and a link from the relevant deep dive.

**Documents 01–21 mirror the source PDFs; 22–32 go beyond them** — variable scope/LEGB, ABCs and
`Protocol`, senior-level language basics, multi-level exception handling, the three design-coding
problems (retry decorator / nested-dict search / LRU), the four system-design scenarios
(zero downtime, observability, 100→600 TPS, 100GB files), Kafka-from-Python config and the
Kafka→Aurora sink, and the two behavioural-but-technical questions. Keep the numbering
append-only: the folder READMEs, `QUESTION_INDEX.md` and `deep_dive/README.md` all reference these
by number, so renumbering breaks dozens of links.

`QUESTION_INDEX.md` link lines use a Unicode arrow (`→ [file.py:12](path#L12)`), not `->`. Match it
when adding entries, or the index renders inconsistently.

### A CPython version gotcha baked into two files

On **CPython 3.13+** a bare `counter += 1` in a tight loop usually loses **no** updates under
threading, because the interpreter only checks for a GIL handoff at the loop back-edge — i.e.
*after* the `STORE`. The textbook race demo therefore prints the correct answer and proves
nothing. `02_concurrency/01_threading_demo.py` and `01_python_core/11_java_to_python_bridge.py`
both show a bare `+=` alongside a `read / time.sleep(0) / write` version, which reliably loses
~75% of updates, and explain that the bug hides until the critical section contains a function
call. Do not "simplify" these back to a bare `+=` — the demo stops working.

### `pytest.ini` discovery — two things that look like bugs but are deliberate

- `04_testing_tdd/tests/` and `05_web_apis_fastapi/tests/` deliberately have **no**
  `__init__.py`. Adding one back will break collection: pytest treats both as the same top-level
  `tests` package and errors with `ModuleNotFoundError` on the second one collected, since they
  live in different directories but would share one module name.
- `11_coding_challenges/` files are named by topic (`01_anagram_grouping.py`, not
  `test_anagram_grouping.py`) because each file doubles as a standalone runnable demo. `pytest.ini`
  lists these six filenames explicitly in `python_files` so their embedded `test_*` functions are
  still discovered. **A seventh challenge file must be added to that list or it won't be collected.**
- None of the challenge files `import pytest` — deliberately, so `python 05_retry_decorator.py`
  stays dependency-free while pytest still discovers plain `test_*` functions. That also means
  `pytest.raises` is unavailable in them; they use `try/except` + `raise AssertionError` instead.
  `05_retry_decorator.py` injects a `FakeSleep` so its 15 tests run in milliseconds rather than
  actually waiting out the backoff — don't "simplify" that back to `time.sleep`.

Each of `04_testing_tdd/` and `05_web_apis_fastapi/` has its own `conftest.py` that inserts its
own folder onto `sys.path` — that's what makes `from src.order_service import ...` and
`from app.main import app` resolve regardless of the directory pytest was invoked from.

### `05_web_apis_fastapi/` — the layered app

`app/routers/` (thin HTTP layer, no business logic) → `app/services.py` (business logic, raises
domain exceptions like `ValidationError`) → `app/repositories.py` (an in-memory store standing in
for a real DB, raises `NotFoundError`). Domain exceptions are **not** caught in the router; they
propagate to `@app.exception_handler(...)` registrations in `app/main.py`, which is the single
place HTTP status codes get decided. `app/dependencies.py` holds every `Depends()` provider
(auth, the service singleton, the rate limiter) so tests can swap them via
`app.dependency_overrides` (see `tests/test_orders_api.py`) without touching route code.

One FastAPI-specific gotcha documented in `05_web_apis_fastapi/README.md`: a required
`Header(...)` with no default fails FastAPI's own request validation (422) *before* your function
body runs if the header is missing entirely — only a present-but-wrong value reaches your code to
raise a deliberate 401. Get this backwards and an auth test will assert the wrong status code.

### `13_system_design_scenarios/` — the scenario-round folder

The newest folder, and the only one whose output *is* the answer: each file computes the numbers you
would quote in a system-design round (Little's Law and the utilization cliff, a bottleneck table, an
SLO burn rate, a canary abort threshold) rather than just describing them. All four are stdlib-only
simulations with no sleeps longer than a few milliseconds.

Two things in here are easy to break:

- `01_zero_downtime_change.py`'s rolling-deploy simulation relies on `Instance.handle()` decrementing
  `warmup_requests_left` **only while `state == "serving"`**. The readiness-gated branch therefore
  sets `state = "serving"` *before* draining the warm-up counter; reordering those two lines makes the
  warm-up loop spin forever.
- `03_capacity_scaling_tps.py`'s `simulate()` must dispatch queued work to free workers **before** the
  admission-control check, even on an arrival it goes on to reject. Reject-then-skip-dispatch starves
  the workers and makes the load-shedding table show ~100% rejections at 100% utilization.

### `06_kafka/` — dual-mode files

`03_delivery_semantics.py`, `04_retry_topic_dlq.py`, `06_schema_registry_simulation.py`,
`07_kafka_python_config.py` and `08_kafka_to_aurora_sink.py` are runnable, dependency-free
simulations (a `FakeBroker` class, in-memory "topics", a `FakeAurora` with a real unique index and
transaction) that reproduce real bugs — message loss, duplication, offset-committed-first,
non-idempotent inserts — on purpose, so the failure mode is visibly observable without a broker.
`07_kafka_python_config.py` additionally imports `confluent_kafka` behind a try/except purely so its
last section can execute against a real broker when one is available.

`01_producer_basics.py` and `02_consumer_basics.py` import `confluent_kafka` with a try/except
fallback — they're readable and annotated even without the package installed, but only actually
execute against a real broker (`docker-compose.kafka.yml`).
