# Python Interview Lab: Live Runner — Plan & Design

Turn `python-interview-preparation` (45 CLI example scripts) into a web app where every example
runs on click and streams its output as a live log, with AI help layered on top.

Status legend used throughout: **[VERIFIED]** = I executed it in a sandbox (Linux, Python 3.12).
**[NOT VERIFIED]** = designed but untested. Section 11 lists exactly what is still unproven.

---

## Contents

1. Findings: what the repo actually is
2. Options considered (and why one wins)
3. Recommended architecture
4. Libraries
5. Run lifecycle and event protocol (the "transitions")
6. Topic-by-topic coverage plan
7. AI features
8. Security
9. Migration plan: CLI repo to web app (phases, VS Code steps)
10. VS Code / Windows setup
11. Test plan and what is still unproven
12. Decisions I need from you

---

## 1. Findings: what the repo actually is

I cloned the repo and ran **every** `.py` file under the 12 topic folders (45 scripts, 1,561 lines of
combined output).

| Measurement | Result | Why it matters |
|---|---|---|
| Runnable scripts | 45 | Each becomes one "card" in the UI |
| Run time under 1 s | 35 | Instant feedback |
| Run time 1–5 s | 8 | Streaming makes these feel alive |
| Run time 5 s or more | 2 (`01_threading_demo` 7.1 s, `11_java_to_python_bridge` 6.9 s) | Need a visible progress/elapsed timer and a Stop button |
| Use `threading` / `multiprocessing` / `signal` | 9 | **Rules out running in the browser** (see section 2) |
| Need a Kafka broker | 2 (`06_kafka/01`, `02`) | They print a "not installed" hint and exit 0 without one |
| Need `pandas` | 3 | Fail with `FileNotFoundError` unless the working directory is the topic folder |
| `input()` / server code | 11 files, all in `legacy_examples/` | Excluded from v1 (section 12) |
| Section banners (`# ----- title`) | 33 of 45 files (24 have 3 or more); the other 12 use a different style | Auto-extracted into a clickable outline. For the 12 without, Phase 2 adds a fallback: parse the `print` banners (`=====` lines) from the log, or ask the AI for an outline |
| `# EXPERIMENT:` prompts | 37 across 27 files | Natural hook for the "Edit and re-run" mode |

Three facts drove the design:

1. **The repo is already web-friendly.** Per its `CLAUDE.md`, 40 examples are stdlib-only simulations
   (`FakeRedis`, `FakeBroker`, mocked LLM). They need no infrastructure and finish quickly.
2. **The `pandas` failures are a working-directory bug, not a code bug.** Running from inside the
   topic folder makes all three pass **[VERIFIED]**. The runner therefore sets `cwd` to the topic folder.
3. **Output differs by interpreter.** `CLAUDE.md` documents that on CPython 3.13+ a bare `counter += 1`
   race demo prints the "correct" answer and proves nothing. The runner must use the *same*
   interpreter the learner chose, and the UI should display the Python version. (Phase 2 item.)

---

## 2. Options considered

| Option | How it works | Fit for this repo | Verdict |
|---|---|---|---|
| **A. FastAPI + subprocess + SSE** | Server launches `python -u file.py`, streams stdout/stderr to the browser | Runs all 45 scripts unchanged, real threads/processes, real timing | **Chosen** |
| B. Pyodide (Python in the browser) | CPython compiled to WebAssembly, no server | Official docs state `multiprocessing` and `threading` can be imported but are not functional | Rejected as primary: breaks 9 of 45 files, including the whole concurrency topic. Keep as an optional static-hosting mode for the other 36 |
| C. Jupyter / Marimo / Streamlit / NiceGUI | Notebook or Python-UI frameworks | Great for authoring; poor for "stream a raw process log with Stop/timeout" and you would rewrite scripts into cells | Rejected for v1 |
| D. Docker container per run | Same as A, but each run in a throwaway container | Best isolation | Phase 4, only if you ever host it publicly |
| E. WebSocket instead of SSE | Two-way channel | Needed only for interactive `input()` | Phase 3, if you decide to support interactive scripts |

**Why SSE and not WebSocket for v1:** logs flow one way (server to browser). SSE is plain HTTP, needs no
extra library, and FastAPI now ships it natively (`fastapi.sse.EventSourceResponse`, which the FastAPI
docs say works with POST). My prototype uses a hand-written `StreamingResponse` so it runs on older
FastAPI versions too; switching later is a small change.

---

## 3. Recommended architecture

```
 Browser (single index.html, zero CDN dependencies)
 ├─ sidebar: topics/examples (auto-discovered)   ├─ code viewer + outline (jump to section)
 ├─ live log pane (timestamps, stderr in red)     └─ AI coach pane (explain / quiz / experiments / vs Java)
        │  POST /api/run  ──────────────►  text/event-stream (SSE)
        ▼
 FastAPI app
 ├─ catalog.py   scans PREP_ROOT, reads docstring/sections/imports via `ast`   (no manifest to maintain)
 ├─ runner.py    Popen + 2 reader threads → asyncio.Queue → SSE events
 │                timeout · output cap · kill process tree · concurrency limit
 ├─ ai.py        streams an LLM answer built from source + captured log
 └─ main.py      /api/catalog  /api/source  /api/run  /api/ai  /api/reload
        │
        ▼
 child process:  python -u <topic>/<file>.py     (cwd = topic folder, stdin closed)
```

Design decisions worth knowing:

- **Auto-discovery.** Adding `NN_new_example.py` to the repo makes it appear after `POST /api/reload`.
  Title, description, outline and dependency badges are derived from the file itself.
- **Threads, not `asyncio.create_subprocess_exec`.** Asyncio subprocesses need the Proactor event loop
  on Windows, which `uvicorn --reload` does not provide. `Popen` plus reader threads behaves the same on
  Windows, macOS and Linux. This matters because your workspace path (`E:\Ravi_Workspace\...`) is Windows.
- **`python -u` and `PYTHONUNBUFFERED=1`.** Without these, a piped child buffers output and the "live"
  log arrives in one lump at the end. **[VERIFIED]**: for a 1.8 s script, lines arrived spread across
  the whole 1.8 s (first at 0.11 s, last at 1.82 s).
- **Folder-level `pytest` suites.** Topics 04 and 05 become one card that runs `pytest -v` so the
  per-test PASSED lines stream live **[VERIFIED]**.

---

## 4. Libraries

**Required (all pure Python, all installed and exercised in the sandbox [VERIFIED])**

| Library | Role | Notes |
|---|---|---|
| `fastapi` (tested 0.142) | HTTP API + SSE | You already know it (topic 05) |
| `uvicorn[standard]` (tested 0.54) | ASGI server | |
| `pydantic` | Request models | Comes with FastAPI |
| stdlib `subprocess`, `threading`, `asyncio`, `ast`, `tempfile` | Runner and discovery | No new dependency |

**Optional**

| Library | Role | When |
|---|---|---|
| `anthropic` (tested 1.11) | AI coach | Needs `ANTHROPIC_API_KEY` |
| `boto3` | Same AI coach via Amazon Bedrock | Fits your Bedrock focus; swap inside `ai.py` only (section 7) |
| `pytest`, `httpx` | Tests of the app itself | Dev only |
| `pytest-json-report` or junit XML | Per-test pass/fail table for suites | Phase 2 |
| `psutil` | Show CPU/memory per run | Phase 3 |
| `ptyprocess` / `pywinpty` | Real terminal for `input()` scripts | Phase 3, only if needed |
| Pyodide (CDN) | Static-site mode for the 36 non-threaded examples | Phase 4, optional |
| `sse-starlette` | Alternative SSE helper | Not needed on current FastAPI |

Frontend is intentionally **one HTML file with a ~30-line built-in syntax highlighter** and no CDN,
matching your preference for self-contained artifacts. Upgrade path if you want a real editor: Monaco or
CodeMirror 6 (both need a build step or a CDN).

---

## 5. Run lifecycle and event protocol (the "transitions")

Interpreting "check how transition works" two ways; both are covered. This section is the **runtime
state transitions**; section 9 is the **migration transition** from CLI repo to web app.

### 5.1 State machine (UI status chip)

```
            select example
   idle ───────────────────────► idle (code + outline loaded, Run enabled)
     │ click Run / Ctrl+Enter
     ▼
  running ──exit 0───────────────► ok
     │   ├─exit ≠ 0──────────────► error        (e.g. sys.exit(3) → "error, exit code 3")
     │   ├─> RUN_TIMEOUT_S───────► timeout      (process tree killed, code −9)
     │   ├─> MAX_OUTPUT_BYTES────► truncated    (runaway print loop protection)
     │   └─ user clicks Stop / closes tab ─► stopped (browser aborts → server kills child)
   Selecting another example while running = implicit Stop.
```

### 5.2 Event stream (server → browser, one JSON object per SSE `data:` line)

```jsonc
{"type":"start","cmd":"python -u 03_asyncio_demo.py","cwd":".../02_concurrency"}
{"type":"out","t":0.112,"line":"============================================================"}
{"type":"err","t":0.540,"line":"Traceback (most recent call last): ..."}
{"type":"end","code":0,"reason":"ok","elapsed":1.78}
```

`t` is seconds since process start, so the log doubles as a timing diagram: concurrency demos show *when*
each thread/coroutine printed, which is the actual lesson.

### 5.3 Behaviour I tested end to end against a live server **[VERIFIED]**

| Scenario | Observed |
|---|---|
| Streaming | 36 lines of `03_asyncio_demo` arrived across 8 distinct 0.1 s buckets, i.e. genuinely incremental |
| Timeout | A 7 s script with a 5 s limit ended `reason: timeout, code: -9, elapsed 5.06 s` |
| Stop / disconnect | Child process present mid-stream; **gone within 1.5 s** of the client disconnecting (checked via `/proc`) |
| stdout vs stderr | `print('x')` tagged `out`, `print('x', file=sys.stderr)` tagged `err`; `sys.exit(3)` reported as `error, code 3` |
| Edit-and-run | Edited code executed from a temp file; **0 leftover `_live_*.py` files** afterwards; request refused with HTTP 403 unless `PREP_ALLOW_EDIT=1` |
| pandas | All three examples pass once `cwd` is the topic folder |
| Kafka without broker | Prints "confluent-kafka not installed" hint, exit 0, UI shows an "infra" badge |
| Automated tests | 7 tests pass (catalog, sections, streaming, pandas cwd, 404/403, pytest suite, AI-without-key) |

One honest note: during testing, my first process-leak check reported "2 survivors". That was my
`pgrep` matching its own shell, not a leak. Re-checked through `/proc`, there were none.

---

## 6. Topic-by-topic coverage plan

"Works today" = included in the prototype and exercised. Everything else is a proposed enhancement.

| # | Topic | Runs today | What makes the log *better* than `python file.py` | Phase |
|---|---|---|---|---|
| 01 | Python core (11 files) | Yes, all exit 0 | Outline from section banners; AI "predict the output" quiz; `# EXPERIMENT:` lines surfaced as buttons that pre-fill Edit mode | 1–2 |
| 02 | Concurrency (6 files) | Yes (up to 7 s) | Timestamps show interleaving; add a per-thread color by parsing thread names; Python-version badge (3.13 race caveat) | 1–2 |
| 03 | Pandas (3 files) | Yes (needs `cwd` fix, done) | Render printed DataFrames as HTML tables, or run with `pandas` display options set to HTML | 2 |
| 04 | Testing / TDD | Yes, as `pytest -v` suite | Parse results into a green/red per-test table; "break a test" Edit mode | 2 |
| 05 | FastAPI app | Tests run; the app itself is not a script | "Try it" panel: start `uvicorn` on a free port, fire the sample requests, show request/response pairs | 3 |
| 06 | Kafka (6 files) | 4 simulations run; 2 need a broker | Toggle "start broker" using the provided `docker-compose.kafka.yml`; until then show the hint and explain-only AI mode | 3 |
| 07 | Caching / queues | Yes | Timestamped logs make stampede-lock behaviour visible | 1 |
| 08 | Resilience (5 files) | Yes | Retry/backoff delays visible via `t`; circuit-breaker state changes highlighted | 1–2 |
| 09 | AWS Lambda / streaming | Yes (simulated S3) | Lambda event JSON in, response out; memory-use line for the streaming demo | 2 |
| 10 | GenAI patterns | Yes (mocked LLM) | **Bonus:** "Live mode" swaps the mock for a real model call when a key is set | 3 |
| 11 | Coding challenges | Yes | Run embedded `test_*` functions via pytest; timing comparison | 1–2 |
| 12 | Framework internals | Yes | DI container / middleware chain logs as a call tree | 2 |
| — | `deep_dive/*.md` (21 docs) | Not yet | Render alongside each example (side panel), linked via the mapping in `QUESTION_INDEX.md` | 2 |
| — | `legacy_examples/` | Excluded | Interactive; see section 12 | 3 |

---

## 7. AI features

**Implemented in the prototype** (`app/ai.py`, streaming): *Explain* (walk through the log), *Quiz me*
(5 questions with hidden answers), *Experiments* (3 modifications with predicted output), *vs Java*
(contrast with Spring/Java; tuned to your 12-year Java background), and free-form *Ask*.
The prompt receives the source (first 12 KB) and the **captured log** (last 6 KB), so answers reference what
actually printed. With no key it returns a clear "AI is disabled" message instead of failing
**[VERIFIED]**.

**Not verified:** I could not make a real API call from the sandbox, so the live model round-trip and the
default model string (`claude-sonnet-5-5`, overridable with `ANTHROPIC_MODEL`) are untested. Please
confirm the model name against your account first.

**Proposed next:**

1. **Predict-then-run.** AI asks "what will this print?", you answer, then the real log is the grader.
   Best active-recall tool for this material.
2. **Auto-annotated log.** AI adds one-line margin notes to the 3–5 key log lines.
3. **Mock interviewer.** Picks a topic, asks follow-ups, scores the answer against the matching
   `deep_dive/*.md` "60-second spoken answer".
4. **Q&A over your notes.** Retrieval over `deep_dive/` and `QUESTION_INDEX.md`. This is a small RAG
   exercise that doubles as GenAI portfolio material.
5. **Bedrock provider.** Keep `stream_answer()` as the only seam and add a second implementation using
   `boto3` `bedrock-runtime` `converse_stream`; choose via an env var. Directly relevant to your Bedrock focus.

---

## 8. Security

This app executes code from disk, so treat it as a **local developer tool**.

| Risk | Mitigation in prototype |
|---|---|
| Arbitrary code via "Edit and run" | **Off by default**; needs `PREP_ALLOW_EDIT=1` (HTTP 403 otherwise) |
| Runaway or infinite loop | Timeout (default 60 s), 1 MB output cap, process-tree kill |
| Resource exhaustion | Max 2 parallel runs (`MAX_PARALLEL_RUNS`) |
| Path traversal via `id` | Only IDs present in the discovered catalog are accepted; unknown IDs get 404 |
| API key leakage | Key read from env / `.env` (git-ignored), never sent to the browser |
| Edited code can still do anything your user can | **Not mitigated.** Bind to `127.0.0.1` only. If you ever host it, add Docker-per-run (phase 4), no network, read-only mount, CPU/memory limits |

---

## 9. Migration plan: CLI repo to web app

Principle: **the web app is additive.** It reads the repo; it never modifies your example files, and the CLI
workflow in `CLAUDE.md` keeps working.

| Phase | Goal | Work | Exit check |
|---|---|---|---|
| **0. Place the app** | Folder layout | Put `pyprep-live/` next to `python-interview-prep/` inside your workspace | `PREP_ROOT` resolves (default `../python-interview-prep`) |
| **1. Run the prototype** (about 1 hour) | Prove it on your machine | Install, start, click through all 12 topics | All 45 scripts show exit 0 (3 pandas + 2 Kafka behave as in section 1) |
| **2. Polish learning value** | Make the log teach | Python-version badge, DataFrame HTML, pytest results table, `deep_dive` side panel, EXPERIMENT buttons, run history | Each topic has at least one "better than CLI" feature from section 6 |
| **3. Advanced** | Cover the hard cases | FastAPI "Try it", Kafka docker toggle, interactive stdin, Bedrock provider, predict-then-run | 05 and 06 fully demonstrable; legacy scripts runnable |
| **4. Optional hosting** | Share it | Docker-per-run sandbox, Pyodide static mode for the 36 non-threaded examples | Only if you decide to publish |

**Behaviour-preservation check for every phase:** run the batch loop from `CLAUDE.md` before and after; the
set of `ok`/`FAIL` lines must be identical.

---

## 10. VS Code / Windows setup

From your workspace root (`E:\Ravi_Workspace\python-interview-preparation`), after unzipping `pyprep-live`
beside `python-interview-prep`:

```powershell
cd pyprep-live
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# optional AI
copy .env.example .env      # then put your key in .env
$env:ANTHROPIC_API_KEY = "sk-ant-..."   # or load it however you prefer

# allow the Edit-and-run mode (localhost only)
$env:PREP_ALLOW_EDIT = "1"

py -m uvicorn app.main:app --port 8000 --reload
# open http://127.0.0.1:8000
```

- Or press **F5** in VS Code: `.vscode/launch.json` is included ("Live Runner (uvicorn)").
- Run the app's own tests: `py -m pytest`.
- If your examples live elsewhere: `$env:PREP_ROOT = "E:\path\to\python-interview-prep"`.
- Install the example dependencies in the **same venv** (`pip install -r ..\python-interview-prep\requirements.txt`),
  because the runner executes examples with the server's interpreter.

---

## 11. Test plan and what is still unproven

**Proven in the sandbox (Linux, Python 3.12):** everything marked [VERIFIED] above, plus JavaScript
syntax check of the frontend (`node --check`).

**Not proven. Please check these first on your machine:**

1. **Windows behaviour.** The kill-process-tree path uses `taskkill /F /T` and
   `CREATE_NEW_PROCESS_GROUP`. It is the standard approach but I could not run it. Test Stop on
   `01_threading_demo.py` and confirm no stray `python.exe` remains in Task Manager.
2. **The UI in a real browser.** I validated the JS syntax and exercised every API it calls, but I did not
   render the page or take screenshots. Expect to fix small CSS or layout issues.
3. **A real AI call** (model name, key, streaming display).
4. **Python 3.13+.** Per your `CLAUDE.md` the race demos behave differently; confirm the version badge idea.
5. **Large outputs / many reruns**: only lightly tested.

**Suggested manual checklist (15 minutes):** run one fast file, one 7 s file and press Stop at 2 s, run the
pytest suite, run a pandas file, run a Kafka file with no broker, edit code and re-run, ask the AI to
explain a log with a key and without.

---

## 12. Decisions I need from you

1. **`legacy_examples/`**: 11 files call `input()` or start servers. Exclude them (current), or build
   interactive stdin support (phase 3)?
2. **AI provider**: Anthropic API directly, Bedrock, or both?
3. **Hosting**: strictly local (current assumption), or do you want to share it? That changes the security work.
4. **Kafka**: is Docker available on your machine, so we can do the broker toggle?
5. **Previous app:** you mentioned doing live logs in "other app". I searched your past chats and did not
   find one with that pattern, so I designed from scratch. If you point me to it, I can align the UX.

---

## 13. Implementation status (updated 2026-10-04)

The prototype was reviewed, restructured into packages and extended. **None of this was executed
in the review environment** (no Python, Node or running Docker daemon was available), so the new
code and its tests are written but **[NOT VERIFIED]**. First action on your machine:
`pip install -r requirements-dev.txt` then `py -m pytest`.

### Restructure

`app/` is now `main.py` + `config.py` + `api/` (routes, schemas) + `services/` (catalog, docs,
runner, ai). See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Requirements split into
`requirements.txt` (runtime) and `requirements-dev.txt` (pytest, httpx).

### Bugs fixed

| Problem found in the prototype | Fix |
|---|---|
| Timeout only checked when output was idle 0.25 s, so a constantly printing script never timed out | checked every iteration (regression test added) |
| `.env` was documented but never loaded | minimal loader in `config.py` |
| `PREP_ROOT` relative paths depended on the CWD | resolved against the project folder |
| `.vscode/launch.json` pointed at the wrong folder when the workspace is the repo root | `cwd` set to `${workspaceFolder}/pyprep-live`, bogus `envFile` removed |
| Edit-and-run temp files (`_live_*.py`) could appear as catalog entries mid-run | catalog ignores that prefix |
| Sending `code` for a pytest suite was silently ignored | returns HTTP 400 |
| Catalog was a mutable module global | `Catalog` object on `app.state`, atomic reload |
| Global `asyncio.Semaphore` could bind to one event loop | one semaphore per loop |
| UI: no-op timer, stale source shown if you clicked quickly between examples, unhandled non-200 AI responses | live elapsed timer, stale-load guard, error shown |

### Plan items now implemented (Phase 1-2)

Python-version badge · `# EXPERIMENT:` list with jump / open-in-editor · deep-dive viewer ·
pytest pass/fail chips · run history (last 10, replayable) · outline fallback for files using
`section("...")` · suite card for topic 11 · "Predict" AI mode (predict-then-run) · `GET /api/docs/{id}`.

### Still open

DataFrame HTML rendering (03) · FastAPI "Try it" panel (05) · Kafka docker toggle (06) · interactive
`input()` scripts · Bedrock provider · mock interviewer / RAG over `deep_dive/` · Docker-per-run
sandbox · Pyodide static mode. Section 11's "not proven" list (Windows Stop behaviour, real browser
rendering, real AI call, Python 3.13) still applies, plus the new code above.

### 13.1 Decisions applied (follow-up, 2026-10-04)

Answers to section 12, as implemented:

| Decision | Outcome |
|---|---|
| Kafka | **Explain-only.** No broker/docker toggle; `confluent-kafka` is not installed, so 06/01-02 print their hint and the 03-06 simulations teach the behaviour. |
| Docker | Used for **local runs only** (`Dockerfile`, `docker-compose.yml`, `start.* docker`). Hosting and Docker-per-run sandboxing are out of scope. |
| AI provider | **Claude API when a key is set, offline mock otherwise** (`AI_MODE=auto|claude|mock`); the UI shows the active mode. Bedrock stays a future option behind `stream_answer()`. |
| Run scripts | `start.cmd/.sh` and `stop.cmd/.sh` added (native default, `docker` argument). |

Verified in this environment: `start`/`stop` failure paths only (no Python 3.10+ found, Docker not running,
nothing running, unknown argument) and `bash -n` syntax of the shell scripts. The successful start path,
Docker build, mock/Claude answers and the new tests have **not** been executed.
