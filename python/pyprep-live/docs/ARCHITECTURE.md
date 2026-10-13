# Architecture

## Package layout

```
pyprep-live/
├─ app/
│  ├─ main.py              create_app(): builds the Catalog, mounts the router and /static
│  ├─ config.py            env + .env settings (single source of truth, read at call time via `config.X`)
│  ├─ api/                 HTTP layer only - no business logic
│  │  ├─ routes.py         /api/catalog /reload /source /docs/{id} /run /ai
│  │  └─ schemas.py        RunBody, AiBody (mode is a Literal)
│  └─ services/            everything that does real work; no FastAPI imports
│     ├─ catalog.py        scans PREP_ROOT with `ast` + regex -> topics/examples (Catalog class)
│     ├─ docs.py           maps examples to deep_dive/*.md via deep_dive/README.md; safe doc reader
│     ├─ runner.py         child process -> reader threads -> asyncio.Queue -> event dicts
│     └─ ai.py             two providers behind stream_answer(): Claude API or offline mock (AI_MODE)
├─ static/index.html       single-file UI, no CDN
├─ start.cmd / start.sh    create venv, install, run in background (or `docker` arg); stop.cmd / stop.sh undo it
├─ Dockerfile, docker-compose.yml, requirements-examples.txt   local Docker run (not for hosting)
├─ tests/                  conftest (fake repo), test_catalog, test_runner, test_api, test_real_repo
└─ docs/ARCHITECTURE.md    this file
```

Dependency direction is one-way: `main -> api -> services -> config`. Services never import the
API layer, so they can be reused from a CLI or tests without FastAPI.

## Why it was restructured

The first prototype had `catalog.py`, `runner.py`, `ai.py` and `main.py` side by side, with the
catalog held in a module-level global that `/api/reload` replaced via `global`. Now:

- the catalog is a `Catalog` object on `app.state` (a lock makes `reload()` swap atomically);
- request models and handlers are separate from services;
- settings are read through `config.X` at call time, so tests can override them with `monkeypatch`.

## Request flow: `POST /api/run`

1. `routes.run` looks the id up in the catalog (404 if unknown), checks edit permission (403) and
   that a suite is not given code (400).
2. `runner.run_example` waits for a slot (per-event-loop semaphore, `MAX_PARALLEL_RUNS`).
3. It starts `python -u <file>` (or `python -u -m pytest -v <topic>` for suites) with `cwd` = topic
   folder (suites: repo root so the repo's `pytest.ini` applies), `stdin` closed, in its own process
   group / session.
4. Two reader threads push `(kind, t, line)` into an asyncio queue; the generator yields
   `start`, then `out`/`err` events, then `end` with `reason` = `ok | error | timeout | truncated`.
5. `finally` always kills the process tree and deletes the temp file, including when the browser
   disconnects (Stop).

## Behaviour worth knowing

- **Timeout** is checked on every loop iteration (earlier version only when output paused, so a
  constantly printing script never timed out).
- **Edited code** runs from `_live_*.py` in the topic folder; the catalog ignores that prefix, so a
  run in progress never shows up as an example.
- **Deep-dive mapping** is derived from the repo's own `deep_dive/README.md` tables; a link to a
  folder applies to every example in it. Only files directly inside `deep_dive/` are served.
- **Suites** exist for any topic with a `tests/` folder or top-level `def test_` functions
  (04, 05, and 11 whose challenge files embed tests).
- **Outline** uses `# ------ title` banners, falling back to `section("title")` calls.

## Extending

| Want to | Change |
|---|---|
| Add an example | Drop a file in the repo, then `POST /api/reload` (or restart) |
| Add an AI mode | Add a key to `MODES` in `services/ai.py` and to `AiBody.mode`; add a button with `data-ai` |
| Add another LLM provider | Implement the same async generator as `stream_answer`, select by env var |
| Add an endpoint | New handler in `api/routes.py`, logic in a service |

## AI providers

`ai.mode()` returns `claude` or `mock`: `AI_MODE=auto` (default) means Claude when `ANTHROPIC_API_KEY`
is set, else mock; `claude` without a key (or without the `anthropic` package) degrades to mock instead of
erroring. The mock reuses `catalog.analyse_source()` on the example's source, so its quiz questions,
experiments and outline come from the file itself, and streams in small chunks so the UI behaves the same.

## Run scripts

`start.*` (native): find Python 3.10+, create `.venv`, install `requirements.txt` +
`requirements-examples.txt` once (`.venv/.deps-ok` marker), launch uvicorn detached on `127.0.0.1:$PORT`,
write `.run/app.pid` and `.run/app.log`, poll `/api/catalog` until ready, open the browser.
`start.* docker`: `docker compose up -d --build` (build context is the repo root; examples mounted at `/prep`).
`stop.*`: kill the PID's process tree and/or `docker compose down`. `.cmd` files are CRLF and `.sh` files LF
(pinned in `.gitattributes`).

`confluent-kafka` is intentionally absent from `requirements-examples.txt`: Kafka is explain-only here.
