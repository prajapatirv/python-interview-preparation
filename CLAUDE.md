# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this workspace is

This is `E:\Ravi_Workspace\PythonWork\Training`, a personal practice/interview-prep workspace, not
a single deployable application. It has two unrelated areas:

- **`python-interview-prep/`** — the active, structured project: a hands-on Python interview-prep
  lab with 11 numbered topic folders (core language through Kafka and GenAI patterns). This is
  where nearly all commands and architecture notes below apply.
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
pytest                                          # entire suite (04, 05, 11)
pytest 04_testing_tdd -v
pytest 05_web_apis_fastapi -v
pytest 11_coding_challenges -v
pytest 11_coding_challenges/01_anagram_grouping.py::test_sorted_key -v   # single test
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

Every numbered folder (`01_python_core/` … `11_coding_challenges/`) follows the same shape:
a `README.md` with a condensed crib sheet + file map, then numbered `.py` files each runnable
standalone (`python NN_name.py`) with inline `# EXPERIMENT:` prompts. Files are written to have
zero required dependencies wherever the topic allows — concurrency, resilience patterns, caching,
queues, AWS Lambda, and GenAI folders all use pure-stdlib simulations (`FakeRedis`, `SimpleQueue`,
`FakeS3Client`, a mocked LLM) that mirror the real library's API shape exactly, so the pattern is
visible without provisioning infrastructure. Only `03_pandas_data_handling/`, `05_web_apis_fastapi/`,
and (optionally) `06_kafka/` need real external packages/services.

### `pytest.ini` discovery — two things that look like bugs but are deliberate

- `04_testing_tdd/tests/` and `05_web_apis_fastapi/tests/` deliberately have **no**
  `__init__.py`. Adding one back will break collection: pytest treats both as the same top-level
  `tests` package and errors with `ModuleNotFoundError` on the second one collected, since they
  live in different directories but would share one module name.
- `11_coding_challenges/` files are named by topic (`01_anagram_grouping.py`, not
  `test_anagram_grouping.py`) because each file doubles as a standalone runnable demo. `pytest.ini`
  lists these four filenames explicitly in `python_files` so their embedded `test_*` functions are
  still discovered. A fifth challenge file must be added to that list or it won't be collected.

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

### `06_kafka/` — dual-mode files

`03_delivery_semantics.py` and `04_retry_topic_dlq.py` are runnable, dependency-free simulations
(a `FakeBroker` class, in-memory "topics") that reproduce real delivery-semantics bugs
(message loss, duplication) on purpose so the failure mode is visibly observable without a
broker. `01_producer_basics.py` and `02_consumer_basics.py` import `confluent_kafka` with a
try/except fallback — they're readable and annotated even without the package installed, but only
actually execute against a real broker (`docker-compose.kafka.yml`).
