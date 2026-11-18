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
| [`shared/cross-stack-pairs.md`](shared/cross-stack-pairs.md) | Java and Python programs that teach the same topic |
| [`shared/prepkit/`](shared/prepkit/) | Code both FastAPI apps share (`.env` loading, Claude or offline mock) |
| [`scripts/`](scripts/) | Workspace checks: every example runs, `QUESTION_INDEX.md` links resolve |

Plans: [`PLAN_INTERVIEW_COACH.md`](PLAN_INTERVIEW_COACH.md) (the coach and this layout), [`PLAN.md`](PLAN.md) (pyprep-live).

## Getting started on your own machine

You need **Python 3.10 or newer** (and **JDK 21** only for the Java examples runner). Nothing else: no
Docker, no database, no account.

```bash
git clone https://github.com/prajapatirv/python-interview-preparation.git
cd python-interview-preparation/interview-coach
start.cmd          # Windows (PowerShell, cmd or Git Bash). macOS / Linux: ./start.sh
```

The first start creates the app's own `.venv`, installs its packages (a minute or two) and opens the
browser. Stop it with `stop.cmd` / `./stop.sh`. The other apps work the same way:

| App | Folder | URL |
|---|---|---|
| Interview Coach: every question by topic, practice, mock interviews | `interview-coach/` | http://127.0.0.1:8100 |
| Run the Python examples in the browser | `python/pyprep-live/` | http://127.0.0.1:8000 |
| Run the Java examples in the browser | `java/javaprep-live/` | http://127.0.0.1:8090 |

The Java runner stays in the foreground: stop it with Ctrl+C. It finds Java on PATH, in `JAVA_HOME`, or in
`~/.jdks` (where IntelliJ installs JDKs).

**Same idea in both languages.** [`shared/cross-stack-pairs.md`](shared/cross-stack-pairs.md) pairs 36 topics
that have a program in both stacks (Kafka delivery semantics, circuit breakers, 100 to 600 TPS, cache
stampede, DI, LRU and more). Run both runners and each paired example shows a **Same idea in Java** /
**Same idea in Python** link that opens its twin in the other runner. The file also lists the topics that
exist in only one stack.
 Set `PORT` to use another port. Add `docker` (`start.cmd docker`) to run the coach or the Python runner
in a container instead; Docker is optional.

## AI: offline by default, sign-in optional

**Everything works offline, at no cost.** Every question has a stored answer, and practice, mock-interview
scorecards and search all run from the bank on your machine. The AI coach only adds generated material
(deeper explanations, a model rewrite of your answer, fact-checking).

To turn the AI coach on, pick one:

1. **Recommended: sign in once with the Anthropic CLI.** Install `ant`
   (macOS: `brew install anthropics/tap/ant`; Windows and Linux: download it from
   [github.com/anthropics/anthropic-cli/releases](https://github.com/anthropics/anthropic-cli/releases)),
   then run `ant auth login`, pick your organization in the browser, and restart the app. No key is
   stored in the repo.
2. **Or use an API key**: create one at [platform.claude.com](https://platform.claude.com) and put it in
   the app's `.env` as `ANTHROPIC_API_KEY=...` (the first start creates `.env` for you).

Both bill API usage to your Claude Console organization. A Claude Pro or Max chat subscription does not
cover them: Anthropic does not allow apps like this one to use a claude.ai login. The AI pill in the
coach (and the "AI coach" tag in the runner) shows which credential is in use.

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
