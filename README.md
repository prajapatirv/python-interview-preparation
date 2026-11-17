# Interview preparation workspace

Interview preparation for **Java** and **Python** developers, from freshers to architects.

| Folder | What it is |
|---|---|
| [`interview-coach/`](interview-coach/) | **Start here.** The AI Interview Coach: every question in this repo by topic, scenario-based answers, practice mode, mock interviews with scorecards, job-description plans. `./start.sh` -> http://127.0.0.1:8100 |
| [`java/java-interview-prep/`](java/java-interview-prep/) | Java content: scenario answer banks, deep dives, crib sheets, Q&A guides, runnable examples |
| [`java/javaprep-live/`](java/javaprep-live/) | Runs the Java examples in the browser |
| [`python/python-interview-prep/`](python/python-interview-prep/) | Python content: 14 hands-on topic folders, deep dives, question index |
| [`python/pyprep-live/`](python/pyprep-live/) | Runs the Python examples in the browser |
| [`shared/material_ref/`](shared/material_ref/) | Source PDFs |
| [`shared/prepkit/`](shared/prepkit/) | Code both FastAPI apps share (`.env` loading, Claude or offline mock) |
| [`scripts/`](scripts/) | Workspace checks: every example runs, `QUESTION_INDEX.md` links resolve |

Plans: [`PLAN_INTERVIEW_COACH.md`](PLAN_INTERVIEW_COACH.md) (the coach and this layout), [`PLAN.md`](PLAN.md) (pyprep-live).

## Running the apps

Each app runs natively by default and needs only Python: `start.cmd` (Windows) or `./start.sh` creates its
own `.venv` and starts the server; `stop.cmd` / `./stop.sh` stops it. Add `docker` to run the same app in a
container instead (`start.cmd docker`); Docker is optional for both.

| App | URL |
|---|---|
| `interview-coach/` | http://127.0.0.1:8100 |
| `python/pyprep-live/` | http://127.0.0.1:8000 |

## Checking everything

```bash
dev-setup.cmd        # Windows; ./dev-setup.sh elsewhere. Add --no-checks to only install.
```

This creates `.venv` at the root from [`requirements-dev.txt`](requirements-dev.txt), then runs ruff, the
three Python test suites, every stdlib example (with Windows cp1252 output forced) and the
`QUESTION_INDEX.md` line-link check. CI ([`.github/workflows/ci.yml`](.github/workflows/ci.yml)) runs the
same steps, plus the Java examples.

Each app finds its content as a sibling folder by default. To point one somewhere else, set
`PREP_ROOT` (pyprep-live), `JAVAPREP_ROOT` (javaprep-live) or `COACH_ROOT` (interview-coach, the folder
that holds `java/` and `python/`).
