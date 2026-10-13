# Python Interview Lab: Live Runner

Click an example, watch it run with a live, timestamped log. Auto-discovers every example in
`../python-interview-prep`. Optional AI coach explains the log, quizzes you, and suggests experiments.

- **Why and how it was designed:** [PLAN.md](PLAN.md) (findings, options, phases, section 13 = what is built).
- **How the code is organised:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Quick start: one command

From `pyprep-live/`:

| | Windows | macOS / Linux / Git Bash |
|---|---|---|
| Start (native) | `start.cmd` | `./start.sh` |
| Start (Docker) | `start.cmd docker` | `./start.sh docker` |
| Stop (either) | `stop.cmd` | `./stop.sh` |

**Native** (default) needs Python 3.10+. The script creates `.venv`, installs `requirements.txt` +
`requirements-examples.txt` (first run only; add `--install` to force it), starts uvicorn in the
background on `127.0.0.1:8000`, waits until it answers, and opens the browser. Logs go to
`.run/app.log`; the PID is in `.run/app.pid`. Running it twice is safe ("already running").

**Docker** (local use only, not for hosting) builds `Dockerfile`, mounts `../python-interview-prep`
at `/prep`, and publishes `127.0.0.1:8000`. Needs Docker Desktop running. `stop` runs
`docker compose down`. Examples execute inside the Linux container (Python 3.12).

Set `PORT=9000` first to use another port. The scripts create `.env` from `.env.example` if missing.

### Manual / development

```powershell
py -m venv .venv ; .venv\Scripts\activate          # macOS/Linux: python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt -r requirements-examples.txt
py -m uvicorn app.main:app --port 8000 --reload
```

Or press **F5** in VS Code ("Live Runner (uvicorn)" in `.vscode/launch.json`, which enables edit mode).
**Ctrl+Enter** runs the selected example.

The examples run with the **same interpreter as the server**, which is why their packages are in
`requirements-examples.txt`. The Python version is shown next to the title (it matters: see the
CPython 3.13 race-demo note in the repo's `CLAUDE.md`).

## AI coach: Claude or mock

| Mode | When | Behaviour |
|---|---|---|
| **Claude** | `ANTHROPIC_API_KEY` is set (env var or `.env`) | real streamed answers using the example's source and captured log |
| **mock** | no key, or `AI_MODE=mock` | offline and free: answers built from the file itself (docstring, outline, `# EXPERIMENT:` comments, exit status, errors, keyword search for *Ask*) |

`AI_MODE=auto` (default) picks Claude when a key exists, otherwise mock. If the `anthropic` package is
missing, or `AI_MODE=claude` is set without a key, it falls back to mock rather than failing. The badge
next to "AI coach" shows which mode is active.

## Kafka is explain-only

No broker is provided and nothing needs one. `confluent-kafka` is deliberately **not** installed, so
`06_kafka/01` and `02` print their "not installed" hint and exit 0; `03`-`06` are pure simulations that
reproduce delivery-semantics and DLQ behaviour. Learn it from the log, the deep dives
(`13`-`16`) and the AI coach. To try a real broker yourself, use the repo's own
`06_kafka/docker-compose.kafka.yml` and `pip install confluent-kafka` outside this app.

## What the UI gives you

| Feature | Details |
|---|---|
| Live log | stdout/stderr streamed line by line with `t` = seconds since start; **Stop** kills the whole process tree |
| Status chip | `idle` / `running 3.2s` (live) / `ok` / `error` / `timeout` / `truncated` / `stopped` |
| Code + outline | Section banners (`# ------ title`, or `section("title")` calls) become a clickable outline |
| Experiments | Every `# EXPERIMENT:` comment is listed; click to jump to it (with edit mode on, it opens the editor on that line) |
| Deep dive | Buttons open the matching `deep_dive/*.md` document, mapped from `deep_dive/README.md` |
| pytest suites | Folders with tests (04, 05, 11) get a "Run the test suite" card with pass/fail chips |
| History | Last 10 runs per example, replayable from the log pane's dropdown (kept in the browser tab) |
| AI coach | Predict, Explain, Quiz me, Experiments, vs Java, free-form Ask; Claude or offline mock |
| Edit and run | Optional (`PREP_ALLOW_EDIT=1`): edit the source and run it from a temp file |

## Settings

Environment variables, or a git-ignored `.env` in this folder (copy `.env.example`). Real environment variables win.

| Variable | Default | Meaning |
|---|---|---|
| `PREP_ROOT` | `../python-interview-prep` | Folder containing `01_python_core/` ... (relative paths resolve against this folder, not the CWD) |
| `RUN_TIMEOUT_S` | 60 | Kill a run after N seconds |
| `MAX_OUTPUT_BYTES` | 1000000 | Kill a run that prints more than this |
| `MAX_PARALLEL_RUNS` | 2 | Concurrent runs |
| `PREP_ALLOW_EDIT` | 0 | `1` enables "Edit code" + run (localhost only!) |
| `ANTHROPIC_API_KEY` | unset | Enables the real Claude coach (otherwise mock mode) |
| `AI_MODE` | auto | `auto`, `claude` or `mock` |
| `PORT` | 8000 | used by the start scripts and docker compose |
| `ANTHROPIC_MODEL` | claude-sonnet-5-5 | Confirm against your account |

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/catalog` | topics, examples (sections, experiments, deep-dive links, needs) and feature flags |
| `POST /api/reload` | re-scan the repo after adding a file |
| `GET /api/source?id=` | source of one example |
| `GET /api/docs/{doc_id}` | a `deep_dive/*.md` document as `{markdown}` |
| `POST /api/run {id, code?}` | run; response is an SSE stream of `start` / `out` / `err` / `end` events |
| `POST /api/ai {id, mode, output, question, code?}` | AI answer as an SSE stream; `mode` is one of `explain quiz break java predict ask` |

Errors: `404` unknown id, `403` edit not enabled, `400` edited code sent for a test suite, `422` bad `mode`.

## Tests

```powershell
py -m pytest
```

`test_catalog.py`, `test_runner.py` and `test_api.py` run against a throw-away repo built in a temp
folder (no dependency on your real examples). `test_real_repo.py` checks the real
`../python-interview-prep` and is skipped if that folder is missing.

## Known gaps (see PLAN.md section 13)

Not built (by decision or yet): Kafka end-to-end broker (explain-only by design), DataFrame HTML rendering, FastAPI "Try it" panel, interactive
`input()` scripts, Bedrock provider. Hosting is out of scope (Docker is for local runs only). The app is a **local developer tool**:
keep it bound to `127.0.0.1`.
