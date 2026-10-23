# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this workspace is

A personal interview-preparation workspace (the folder is planned to be renamed `interview-coach-workspace`;
nothing inside depends on the root folder's name). It is **organised by technology**:

```text
interview-coach/              the AI Interview Coach app (FastAPI) - serves BOTH stacks; see its section below
java/java-interview-prep/     Java content: examples, deep_dive/, topics/ crib sheets, Q&A guides,
                              interview-scenarios/ (scenario answer banks)
java/javaprep-live/           zero-dependency Java runner for the Java examples
python/python-interview-prep/ Python content: 14 topic folders, deep_dive/, QUESTION_INDEX.md
python/pyprep-live/           FastAPI runner for the Python examples
shared/material_ref/          source PDFs (read-only)      shared/java-interview-prep.zip  archive
scratch/Java/, scratch/example/   unstructured scratch files
PLAN.md                       design doc for pyprep-live   PLAN_INTERVIEW_COACH.md  design doc for the coach
```

Each live app finds its content as a **sibling folder** (`../python-interview-prep`, `../java-interview-prep`),
so an app and its content must always move together. The sections below use project names
(`python-interview-prep/`, `pyprep-live/`, ...) relative to their technology folder.

- **`python-interview-prep/`** — the content project: a hands-on Python interview-prep lab with 14
  numbered topic folders (core language through Kafka, GenAI patterns, framework internals,
  system-design scenarios and Airflow) plus a `deep_dive/` documentation set. Most commands and
  architecture notes below apply here.
- **`pyprep-live/`** — a **real FastAPI web app** that auto-discovers and executes the examples in
  `../python-interview-prep`, streaming each run's output as a live log, with an optional AI coach.
  It has its own `requirements.txt`, `.venv`, `pytest.ini`, `tests/`, Dockerfile and
  `docs/ARCHITECTURE.md`. **It machine-reads the prep lab's conventions** — see
  "The cross-project contract" below before changing folder names, file names or
  `deep_dive/README.md`.
- **`java-interview-prep/`** + **`javaprep-live/`** — the Java counterpart (Java 8/11, Spring Boot,
  microservices, REST, Kafka, NoSQL, Splunk): runnable single-file examples, `deep_dive/` docs, a Q&A
  bank, and a zero-dependency Java runner app. See "Java projects" at the end of this file.
- **`interview-coach/`** — the scenario-based Interview Coach for both stacks, with the Claude API.
  See "Interview Coach" near the end of this file.
- **`shared/material_ref/`** — the source interview-prep PDFs the notes are distilled from. Read-only
  reference; see `shared/material_ref/README.md` for which three of the six actually contain content.
- **`scratch/Java/`**, **`python-interview-prep/legacy_examples/`**, **`scratch/example/`** — unstructured
  scratch files with no build system or tests. Reference material only, not code to maintain to the
  same standard.
- **`PLAN.md`** (workspace root) — the design document for `pyprep-live`: findings, options
  considered, phases. Its section 13 records what was actually built. `pyprep-live/PLAN.md` is the
  project-local copy. **`PLAN_INTERVIEW_COACH.md`** is the plan for the coach and the restructure.

Unless told otherwise, assume `python/python-interview-prep/` is the working root for Python work.

**Windows gotcha:** the filesystem is case-insensitive, so `java/` and the old scratch folder `Java/`
collide — that is why scratch lives under `scratch/`. Don't create a top-level `Java/` again.

## Interpreter: use `py`, not `python`

**`python` is not on PATH in this environment** (neither Git Bash nor PowerShell); the Windows Python
Launcher **`py`** is. The system interpreter is **CPython 3.14**. Several version-sensitive notes
below depend on that.

**There is no `.venv` in `python-interview-prep/`, and `pytest` is not installed for the system
interpreter.** Two options:

```bash
# A. create one (what the project README tells a learner to do)
cd python/python-interview-prep
py -m venv .venv
source .venv/Scripts/activate     # Git Bash on Windows
pip install -r requirements.txt   # see the file for which folder needs which extra

# B. borrow pyprep-live's venv, which already has pytest + fastapi + pandas (fastest for a one-off)
../pyprep-live/.venv/Scripts/python.exe -m pytest -q
```

## Commands

### Tests — `python-interview-prep/`

`pytest.ini` at the project root governs discovery (`testpaths = 04_testing_tdd/tests
05_web_apis_fastapi/tests 11_coding_challenges`). **68 tests total**, 54 of them in folder 11.

```bash
cd python/python-interview-prep
pytest                                   # the whole suite (folders 04, 05, 11)
pytest 11_coding_challenges -v
pytest 11_coding_challenges/01_anagram_grouping.py::test_sorted_key -v   # a single test
pytest -k "empty"                        # every test whose name matches
pytest --cov=src --cov-report=term-missing   # needs pytest-cov (not in requirements.txt)
```

### Tests — `pyprep-live/`

```bash
cd python/pyprep-live
.venv/Scripts/python.exe -m pytest -q          # 32 tests
.venv/Scripts/python.exe -m pytest tests/test_real_repo.py -q   # integration vs the real prep repo
```

`tests/test_real_repo.py` runs **against the actual `../python-interview-prep` folder** (skipped if
absent) — it is the test that catches structural breakage in the content project.

### Running a single example

Every numbered `.py` file in every topic folder is directly executable and self-contained:

```bash
cd python/python-interview-prep
py 01_python_core/03_decorators.py
py 02_concurrency/benchmark_concurrency_models.py
```

`03_pandas_data_handling/` files read relative CSV paths, so run them **from their own folder**.

### The apps

```bash
# the prep lab's own teaching FastAPI app
cd python/python-interview-prep/05_web_apis_fastapi && uvicorn app.main:app --reload   # :8000, docs at /docs

# the Live Runner (creates its own venv on first run; `docker` arg for the container path)
cd python/pyprep-live && ./start.sh        # Windows: start.cmd   |   stop with ./stop.sh / stop.cmd
```

### Optional local Kafka (`06_kafka/`)

Only `01_producer_basics.py` and `02_consumer_basics.py` need it; the rest are simulations.

```bash
cd python/python-interview-prep/06_kafka
docker compose -f docker-compose.kafka.yml up -d
py 01_producer_basics.py
py 02_consumer_basics.py       # in a second terminal
docker compose -f docker-compose.kafka.yml down -v
```

There is **no lint/format tooling** configured in either project.

## The cross-project contract

`pyprep-live` builds its catalog by **scanning `python-interview-prep` with `ast` + regex**
(`app/services/catalog.py`) and maps examples to deep dives by **parsing the tables in
`deep_dive/README.md`** (`app/services/docs.py`). The content project's conventions are therefore a
**machine-read interface**, not just documentation. Four concrete couplings:

1. **Numbered folders and files.** `NN_name/` and `NN_name.py` are how topics and examples are
   discovered and ordered.
2. **`deep_dive/README.md` table rows** must keep the shape
   `| [34](34_airflow_orchestration.md) | **Title** | [`file.py`](../14_folder/file.py) |` —
   `docs.py`'s `ROW_RE` matches `| [digits](something.md) |` and `TARGET_RE` matches
   `](../folder/file)`. Reformat those tables and every example silently loses its deep-dive link.
3. **`# ---- section` banners** become the clickable outline in the UI. Files without them fall back
   to parsing `=====` banners out of the log.
4. **`pyprep-live/tests/test_real_repo.py` hardcodes the topic count** (currently `== 14`). **Adding
   a numbered folder to the content project breaks that test until you bump it** — it is a
   deliberate canary against the catalog silently losing a folder, so update it rather than
   loosening it.

A file prefixed with `_` (e.g. `14_airflow_orchestration/_mini_airflow.py`) is still listed as an
example by the catalog, with zero sections. Harmless, but don't be surprised by it.

## Windows constraint: keep example output cp1252-safe

When stdout is redirected on Windows, Python encodes with **cp1252**, so a character outside that
set crashes the example with `UnicodeEncodeError` — even though it prints fine to a terminal. This
bites exactly when the verification loop below redirects to `/dev/null`, and in `pyprep-live`, which
captures output from a child process.

Em dashes, curly quotes, `×` and `…` are cp1252-safe. **Greek letters (`ρ`, `λ`), `→`, `≈`, `≤`, `−`
and `∞` are not** — use `rho`, `->`, `<=` in printed strings. (Markdown files are read as UTF-8 and
are unaffected; this applies only to what a `.py` file *prints*.)

## Architecture — `python-interview-prep/`

### The topic-folder convention

Every numbered folder (`01_python_core/` … `14_airflow_orchestration/`) has the same shape: a
`README.md` with a condensed crib sheet + file map, then numbered `.py` files each runnable
standalone, with inline `# EXPERIMENT:` prompts and an `# EXERCISE` block at the end.

Files have **zero required dependencies wherever the topic allows**. Concurrency, resilience,
caching, queues, AWS Lambda, framework internals, GenAI, system-design and Airflow all use
pure-stdlib simulations (`FakeRedis`, `SimpleQueue`, `FakeS3Client`, `FakeBroker`, `FakeAurora`, a
fake pod fleet + load balancer, a mocked LLM, a miniature Schema Registry, a hand-built DI
container, a mini-Airflow) that mirror the real library's API shape exactly, so the pattern is
visible without provisioning infrastructure. Only `03_pandas_data_handling/`,
`05_web_apis_fastapi/` and (optionally) `06_kafka/01`–`02` need real external packages or services.

All **59 stdlib-only examples** are expected to exit 0. Verify with:

```bash
cd python/python-interview-prep
for f in 01_python_core/*.py 02_concurrency/*.py 06_kafka/0[3-8]*.py 07_caching_queues/*.py \
         08_scaling_production_resilience/*.py 09_aws_lambda_streaming/*.py \
         10_genai_llm_patterns/*.py 11_coding_challenges/*.py 12_framework_internals/*.py \
         13_system_design_scenarios/*.py 14_airflow_orchestration/0*.py; do
  py "$f" >/dev/null 2>&1 && echo "ok   $f" || echo "FAIL $f"
done
```

The redirection is the point — it is what catches the cp1252 problem above. Notes:

- `02_concurrency/01_threading_demo.py` and `01_python_core/11_java_to_python_bridge.py` take ~7s
  each, from deliberate `sleep`-driven race demos.
- `01_python_core/17_java_to_python_advanced.py` takes ~10s: section 7 benchmarks 4 x 6M-iteration
  loops four ways (serial / threads / subinterpreters / processes) to prove threads don't
  parallelise CPU-bound Python. **Its narration lives in `main()` under an `if __name__` guard on
  purpose** — `ProcessPoolExecutor` re-imports the module per child on Windows, so module-level
  prints appear once per child and a module-level pool raises outright. Definitions stay at module
  level because they must be importable *and* picklable.
- `09_aws_lambda_streaming/03_large_file_processing.py` generates a ~13MB temp file under
  `tempfile.mkdtemp()` and removes it on exit. Raising its `ROWS` constant is the intended
  experiment; peak memory is designed *not* to move.
- `01_python_core/08_exception_handling.py:119` emits `SyntaxWarning: 'return' in a 'finally' block`
  on 3.14. **That is the lesson** — it is the return-in-finally footgun demo. Don't "fix" it.

### `deep_dive/` — the long-form documentation set

**34 long-form Q&A documents**, one per interview topic — the answer to "the folder READMEs are
one-liners, I need the full answer". Each follows a fixed structure: *What interviewers are actually
probing* → *Must-know points* → *Interview questions and full answers* (multi-paragraph, with code)
→ *A worked example* → *Hands-on drills* → *The 60-second spoken answer*. Most carry a **Java
contrast** block where semantics genuinely differ.

The division of labour matters and should be preserved:

- **Folder `README.md`** = crib sheet, for revision. One or two lines per concept.
- **`QUESTION_INDEX.md`** = a lookup table, question → the exact line that demonstrates it.
- **`deep_dive/NN_*.md`** = the full treatment, with trade-offs and failure modes.

When adding a runnable file: add a row to its folder README's file table, a Q&A block to
`QUESTION_INDEX.md`, and a link from the relevant deep dive.

**Documents 01–21 mirror the source PDFs; 22–34 go beyond them** — variable scope/LEGB, ABCs and
`Protocol`, senior-level language basics, multi-level exception handling, the built-in decorators
(`@classmethod`/`@staticmethod`/`@property`/`functools`), the three design-coding problems (retry
decorator / nested-dict search / LRU), the four system-design scenarios (zero downtime,
observability, 100→600 TPS, 100GB files), Kafka-from-Python config and the Kafka→Aurora sink,
Airflow orchestration, and the two behavioural-but-technical questions.

**Keep the numbering append-only.** The folder READMEs, `QUESTION_INDEX.md`, `deep_dive/README.md`
*and `pyprep-live`'s docs mapping* all reference these by number; renumbering breaks dozens of links
plus the Live Runner's deep-dive panel.

`QUESTION_INDEX.md` uses a Unicode arrow on link lines (`→ [file.py:12](path#L12)`), not `->`, and an
em dash in headings. Match both when adding entries.

### A CPython version gotcha baked into two files

On **CPython 3.13+** a bare `counter += 1` in a tight loop usually loses **no** updates under
threading, because the interpreter only checks for a GIL handoff at the loop back-edge — i.e. *after*
the `STORE`. The textbook race demo therefore prints the correct answer and proves nothing.
`02_concurrency/01_threading_demo.py` and `01_python_core/11_java_to_python_bridge.py` both show a
bare `+=` alongside a `read / time.sleep(0) / write` version, which reliably loses ~75% of updates,
and explain that the bug hides until the critical section contains a function call. **Do not
"simplify" these back to a bare `+=`** — the demo stops working.

### `pytest.ini` discovery — three things that look like bugs but are deliberate

- `04_testing_tdd/tests/` and `05_web_apis_fastapi/tests/` deliberately have **no** `__init__.py`.
  Adding one back breaks collection: pytest treats both as the same top-level `tests` package and
  errors with `ModuleNotFoundError` on the second one collected.
- `11_coding_challenges/` files are named by topic (`01_anagram_grouping.py`, not
  `test_anagram_grouping.py`) because each doubles as a standalone runnable demo. `pytest.ini` lists
  these **six** filenames explicitly in `python_files` so their embedded `test_*` functions are still
  discovered. **A seventh challenge file must be added to that list or it won't be collected.**
- None of the challenge files `import pytest` — deliberately, so `py 05_retry_decorator.py` stays
  dependency-free while pytest still discovers plain `test_*` functions. That also means
  `pytest.raises` is unavailable in them; they use `try/except` + `raise AssertionError` instead.
  `05_retry_decorator.py` injects a `FakeSleep` so its 15 tests run in milliseconds rather than
  waiting out the backoff — don't "simplify" that back to `time.sleep`.

Each of `04_testing_tdd/` and `05_web_apis_fastapi/` has its own `conftest.py` inserting its own
folder onto `sys.path` — that's what makes `from src.order_service import ...` and
`from app.main import app` resolve regardless of where pytest was invoked.

### `05_web_apis_fastapi/` — the layered app

`app/routers/` (thin HTTP layer, no business logic) → `app/services.py` (business logic, raises
domain exceptions like `ValidationError`) → `app/repositories.py` (in-memory store standing in for a
DB, raises `NotFoundError`). Domain exceptions are **not** caught in the router; they propagate to
`@app.exception_handler(...)` registrations in `app/main.py`, which is the single place HTTP status
codes get decided. `app/dependencies.py` holds every `Depends()` provider (auth, the service
singleton, the rate limiter) so tests can swap them via `app.dependency_overrides` (see
`tests/test_orders_api.py`) without touching route code.

One FastAPI gotcha, documented in that folder's README: a required `Header(...)` with no default
fails FastAPI's own validation (**422**) *before* your function body runs if the header is missing
entirely — only a present-but-wrong value reaches your code to raise a deliberate **401**. Get this
backwards and an auth test asserts the wrong status code.

### `13_system_design_scenarios/` — where the output *is* the answer

Each file computes the numbers you would quote in a system-design round (Little's Law and the
utilization cliff, a bottleneck table, an SLO burn rate, a canary abort threshold) rather than
describing them. All four are stdlib-only, with no sleeps longer than a few milliseconds.

Two things here are easy to break:

- `01_zero_downtime_change.py`'s rolling deploy relies on `Instance.handle()` decrementing
  `warmup_requests_left` **only while `state == "serving"`**. The readiness-gated branch therefore
  sets `state = "serving"` *before* draining the warm-up counter; reordering those two lines makes
  the warm-up loop spin forever.
- `03_capacity_scaling_tps.py`'s `simulate()` must dispatch queued work to free workers **before**
  the admission-control check, even on an arrival it goes on to reject. Reject-then-skip-dispatch
  starves the workers and makes the load-shedding table show ~100% rejections at 100% utilization.

### `14_airflow_orchestration/` — the mini-Airflow shim

Airflow is a multi-process system with a metadata DB and is not officially supported on native
Windows, so this folder ships **`_mini_airflow.py`**: a **785-line** stdlib reimplementation of the
Airflow *API shape* (`with DAG(...) as dag`, `a >> [b, c] >> d`, `PythonOperator`, `ti.xcom_pull`,
`TriggerRule`, `.expand()`, templating, a scheduler that derives data intervals, an executor that
honours trigger rules and retries). Files `01`–`04` add their own directory to `sys.path` and import
it, so they run from any working directory — and **the DAG code they contain is the code you would
write against real Airflow**.

Three details in the shim are load-bearing; they encode real Airflow semantics, so don't "simplify"
them:

- **`BaseOperator.__rrshift__`/`__rlshift__`** are what make `a >> [b, c] >> d` work. Python finds no
  `list.__rshift__`, so it falls back to `d.__rrshift__([b, c])`. Real Airflow defines these for the
  same reason.
- **Branch skipping is `skip_all_except`**, not "skip the whole subtree": a branch skips everything
  downstream of itself *except what is reachable from the chosen branch*. That is precisely why a
  join after a branch survives with `trigger_rule="none_failed_min_one_success"`. An eager subtree
  skip makes that keyword look pointless and teaches the wrong lesson.
- **`chain()` is PAIRWISE for two equal-length lists**, not a mesh (`cross_downstream` is the mesh).
  Getting this wrong silently contradicts the file's own explanation.

`render()` resolves dotted lookups with Jinja's **attribute-then-item** fallback, which is why
`{{ params.warehouse }}` works on a plain dict; plain `eval` would need `params["warehouse"]`.

### `06_kafka/` — dual-mode files

`03_delivery_semantics.py`, `04_retry_topic_dlq.py`, `06_schema_registry_simulation.py`,
`07_kafka_python_config.py` and `08_kafka_to_aurora_sink.py` are runnable, dependency-free
simulations (a `FakeBroker`, in-memory "topics", a `FakeAurora` with a real unique index and
transaction) that reproduce real bugs — message loss, duplication, offset-committed-first,
non-idempotent inserts — **on purpose**, so the failure mode is observable without a broker.

`01_producer_basics.py` and `02_consumer_basics.py` import `confluent_kafka` behind a try/except:
readable and annotated without the package, but they only execute against a real broker.
`07_kafka_python_config.py` does the same, purely so its last section can run live when one exists.

## Architecture — `pyprep-live/`

Full detail is in `pyprep-live/docs/ARCHITECTURE.md`; the essentials:

```text
main.py (create_app)  ->  api/  ->  services/  ->  config.py
```

Dependency direction is **one-way**: `services/` never imports the API layer, so it is usable from a
CLI or tests without FastAPI. Settings are read through `config.X` **at call time** so tests can
`monkeypatch` them. The catalog lives as a `Catalog` object on `app.state` with a lock, so
`/api/reload` can swap it atomically.

- `services/catalog.py` — scans `PREP_ROOT` with `ast` + regex into topics/examples
- `services/docs.py` — maps examples to `deep_dive/*.md` via `deep_dive/README.md`; the doc reader
  refuses paths outside `deep_dive/`
- `services/runner.py` — spawns `python -u <file>` (or `python -u -m pytest -v <topic>` for a suite)
  with `cwd` set to the topic folder (repo root for suites, so the repo's `pytest.ini` applies),
  stdin closed, in its own process group; two reader threads feed an `asyncio.Queue` of event dicts
- `services/ai.py` — `stream_answer()` behind two providers: the Claude API or an offline mock,
  selected by `AI_MODE`

## Java projects — `java-interview-prep/` and `javaprep-live/`

Independent of the Python projects above. **Only a JDK is needed** (21 is installed; `java`, not `py`).
There is no Maven/Gradle in this environment, so nothing here uses a build tool.

```bash
cd java/java-interview-prep
java examples/12_kafka/02_consumer_groups_rebalancing_and_lag.java   # single-file source launch
./verify_examples.sh                  # all 50 examples, stdout redirected, expects exit 0 (~2 min)
./verify_examples.sh 12_kafka         # one chapter

cd ../javaprep-live
start.cmd                             # or ./start.sh -> http://127.0.0.1:8090 ; --check runs every example headless
```

- **Content layout**: `examples/NN_chapter/NN_file.java` (runnable) ↔ `deep_dive/NN_chapter.md` (long-form
  Q&A) — **same `NN_chapter` stem**, which is how the app links them. `topics/*.md` is the older crib-sheet
  Q&A (473 Q, parsed by `build_site.py` and by the app). `Java_SpringBoot_Kafka_Interview_QA_Guide.md` is a
  96-question guide the app also parses (`# N. Section` / `## Qn. Question` headings).
- **Examples are single-file programs**: no imports from sibling files (JDK 21 source launcher can't), classes
  are deliberately **not** `public`, output is **ASCII only** (stdout is redirected on Windows), and Spring /
  Kafka / database behaviour is **simulated** so failure modes are observable. Each starts with a header
  comment (` * NN - Title`, then `Interview angle: ...`) and prints `section("N. Title")` banners — the app
  builds its title, summary and outline chips from exactly those.
- **`javaprep-live/JavaPrepLive.java`** is one file on `com.sun.net.httpserver` (binds 127.0.0.1 only, runs
  only `examples/**/*.java`, serves only whitelisted markdown) plus `static/index.html` (vanilla JS, its
  own small Markdown renderer, no CDN). Nothing to edit when adding an example: the catalog is scanned.
- Examples that are intentionally non-deterministic or "demonstrate a bug" (`02_streams_collectors` section 9
  parallel `ArrayList::add`, `15_testing` last assertion) must still **exit 0**; keep them that way.
- `01_java8_core/04_completable_future` and `03_java11_and_modern/03_virtual_threads_java21` take several seconds
  (deliberate sleeps / a 200-thread-pool comparison). `10_spring_security/01` spends ~0.5 s per PBKDF2 hash on purpose.

## Interview Coach — `interview-coach/`

The scenario-based coach for **both** stacks (FastAPI + one static page + the Claude API, offline mock
without a key). Full detail in `interview-coach/README.md`; research notes in `interview-coach/docs/RESEARCH.md`.

```bash
cd interview-coach
./start.sh                                  # Windows: start.cmd -> http://127.0.0.1:8100 ; stop: ./stop.sh
.venv/Scripts/python.exe -m pytest          # 61 tests, incl. tests/test_real_repo.py against the real content
```

- **Content is file-driven.** `skills/<stack>/_persona.md` (stack, content root, mixed `guides`, Python
  `index`; body = AI persona) and `skills/<stack>/NN_topic.md` (one topic: `crib`, `docs`, `examples`,
  `folders`, `keywords`; body = the AI instruction pack). Scenario banks live in
  `<content root>/interview-scenarios/*.md` and attach to a topic by front-matter `skill:`.
  Adding content never needs a code change.
- **Every existing question is included** — crib sheets, deep-dive Q&A, the three Java guides,
  `deep_dive/19_docx_gap_topics.md`, the Python `QUESTION_INDEX.md` (1,096 Java + 687 Python at the
  time of writing). Mixed guides are classified by `keywords:`; unmatched ones land in `general`.
  `java-interview-prep/QUESTION_INDEX.md` is deliberately not read (generated from `topics/`).
- **The canary:** `tests/test_real_repo.py` fails if any question-bearing `.md` under a content root is not
  wired in, if the crib count changes from 473, if a scenario answer lacks a required section, or if
  `general` grows past 10. **Adding a new Q&A file means wiring it into a skill/persona file**, not
  loosening the test. The in-app **Coverage** screen shows the same report.
- **Scenario answer format is machine-read** (parser: `app/services/bank.py`): `### Q<n> [fresher|mid|senior|architect] text`,
  a `tags:` line, then bold section labels — *The live scenario*, *What the interviewer is really checking*,
  *How I answer it*, *Trade-offs and what can go wrong*, *How I'd monitor it*, optional *Numbers I quote*,
  *Follow-ups to expect* (`- *question* -> answer`), *60-second answer*, optional *Minimal config*.
  Renaming those labels breaks the section rendering and the mock scorer.
- **Known weak areas from real interview feedback (2026-10-13)** — API response time/throughput, CPU/memory
  efficiency, performance-measurement tools, Kafka tuning at scale. Covered by the `performance` topic
  (`skills/java/15_performance.md`, banks 06–08) and Kafka bank 03; give these priority when extending content.
- **Profile and company packs (2026-10-22)**: `java-interview-prep/profile-java-genai/README.md` (Java/J2EE + Gen AI
  requirement: banks `interview-scenarios/70`–`78`, 7 sections × 15 + 25 GenAI incl. RAG and MCP, vendor-neutral, no
  provider-specific API) and `java-interview-prep/company-chase-travel/README.md` (banks `80`–`82`, plus `brush-up/` = 4 × 30 crib-style Q&A for
  the Chase brush-up list, wired as `docs:` into rest-api, spring-boot, kafka and cloud-devops). The GenAI banks
  attach to the `genai` topic (`skills/java/16_genai.md`). The Chase Travel pack is **illustrative**: its internal
  architecture is not public, so keep public facts and assumptions clearly separated when extending it.
- **Answer style the user wants**: scenario-first, spoken-interview narrative, minimal code (a few config
  lines at most). The `_persona.md` files encode it for the AI; keep new bank entries in the same voice.
  For production / monitoring / performance questions use the **three-tier format**: *Short answer*
  (3-5 sentences) -> *Technical detail* (tables, commands, settings) -> *Deep dive* (mechanism, worked
  example, pitfalls, follow-ups). Reference implementation: `java/java-interview-prep/deep_dive/25_production_monitoring_qa.md`.
- **Self-improving layer** (design: `interview-coach/docs/SELF_IMPROVING_DESIGN.md`): `POST /api/check` fact-checks
  an answer and stores an *attempt*; saved answers can be submitted as alternatives, gated, reviewed, and promoted
  into the bank file as `**Another strong answer (<angle>)**` (`bank.alternatives()`). Evidence lives in SQLite
  (`data/coach.db`, gitignored) or Supabase; **truth stays in Markdown in git**. `scripts/run_eval.py` gates checker
  prompt/model changes on `evals/checker_cases.json`; its case titles must exist in the bank (canary test).
  Supabase store and auth are tested only against a fake PostgREST, never a live project.
- AI: `ANTHROPIC_MODEL` defaults to `claude-sonnet-5-5` (the user's choice), `AI_EFFORT=medium`, system prompt
  cached per topic, server-side refusal fallback on. Question ids are a hash of (stack, source, label, title),
  so browser progress survives re-ordering but not retitling.
