# Plan — Scenario-Based Interview Coach + Repo Restructure (Java / Python)

Status: **Phases 0, 1, 3 and 4 done (2026-10-13)** — see section 6. Phase 2 (remaining Java scenario banks) waits on your review of the pilot banks.

Target role this is tuned for:

| | |
|---|---|
| Primary skill | Java / J2EE |
| Sub-skills | Apache Kafka, Java 11, REST API, Splunk, Spring Boot |
| Must be strong on | Java 8, Spring / Spring Boot, Microservices & REST APIs, Kafka (topics, partitions, consumer groups, offsets, rebalancing, lag, performance, scaling), NoSQL (Couchbase / MongoDB / Cassandra) |

---

## 1. The problem with what exists today

| Existing asset | What it is good for | Why it falls short for this goal |
|---|---|---|
| `java-interview-prep/examples/` (50 runnable files) | Proving behaviour | Code-first. Not how you *speak* in an interview. |
| `java-interview-prep/deep_dive/*.md` (23 docs) | Full technical treatment | Long, code-heavy, organised by technology, not by question. |
| `java-interview-prep/topics/*.md` (473 Q) | Fast revision | 3–5 line answers. Correct facts, but no story, no "what I did in production". |
| `Java_SpringBoot_Kafka_Interview_QA_Guide.md`, `Round_Questions_QA.md` | Breadth | Same: definition-style answers. |
| `javaprep-live` | Runs Java examples | **No AI**, no Q&A practice mode. |
| `pyprep-live` | Runs Python examples + AI coach | AI coach is tied to *a source file + its log*, not to a free question. |

**The gap:** a senior/architect interviewer asks *"How would you handle rebalancing?"* or *"A third-party
REST API is slow and flaky — how do you still give your client a proper response?"* The expected answer
is a **scenario narrative**: the situation, the decision, the trade-off, what went wrong, how you'd
monitor it — with at most a config line or two. None of the current material is written that way.

---

## 2. What we will build

### 2.1 A new content type: the **Scenario Answer Bank** (no programs)

One Markdown file per skill. Every question uses the **same fixed answer shape**, written in the
voice of a Java architect with 30 years of experience:

```markdown
### Q12 [kafka] [senior] How do you handle consumer-group rebalancing in production?
tags: rebalancing, consumer-groups, lag, deployments

**The live scenario**
Payments consumer group, 12 partitions, 6 pods on Kubernetes. Every rolling deploy caused
2–3 minutes of zero consumption and a lag spike of 400k messages; an alert fired on every release.

**What the interviewer is really checking**
That you know a rebalance is a *stop-the-world for the group*, what triggers it, and how to make it
incremental and rare — not just the definition.

**How I answer it (the architect's narrative)**
1. Diagnose the trigger: deploy (members leave/join), slow processing (> max.poll.interval.ms),
   or missed heartbeats (GC pauses / network).
2. Make it incremental: cooperative-sticky assignor so only moved partitions pause.
3. Make it rare: static membership (group.instance.id = pod name) so a restart inside
   session.timeout is not a rebalance at all.
4. Remove the slow-processing trigger: smaller max.poll.records, hand off heavy work, never sleep
   in the poll loop.
5. Make it safe: commit offsets in onPartitionsRevoked; idempotent handlers so replays are harmless.
6. Kafka 4 / KIP-848: broker-side assignment — the long-term fix.

**Trade-offs and what can go wrong**
Static membership delays failover of a truly dead pod until session.timeout expires …

**Numbers I quote** (optional)
Lag dropped from 400k to < 5k during deploys; rebalance time from ~150 s to ~3 s.

**Follow-ups to expect** → short answers
- "Why not just increase max.poll.interval.ms?" → …
- "What happens to in-flight messages during revoke?" → …

**60-second spoken answer**
A tight paragraph you can say out loud.

**Minimal config (only if it helps)** — max ~5 lines, never a full program.
```

Rules for every answer: scenario first; code is optional and tiny; always include *what can go wrong*
and *how you'd monitor it (Splunk / metrics)*; always end with the 60-second version.

### 2.2 Skill files and question budget (Java track)

| File | Skill | Target Qs | Example scenario questions |
|---|---|---|---|
| `01_kafka_core.md` | Topics, partitions, keys, ordering, replication | 15 | "Orders for one customer arrive out of order — why and fix?" |
| `02_kafka_consumers.md` | Consumer groups, offsets, commits, **rebalancing**, **lag** | 20 | "How do you handle rebalancing?", "Lag is growing at 2 a.m. — walk me through it." |
| `03_kafka_reliability_scaling.md` | Delivery semantics, DLT/retry, idempotency, performance, scaling, partition sizing | 15 | "Scale from 1k to 50k msg/s", "Poison message blocks a partition." |
| `04_rest_api_design.md` | Contract, versioning, errors, pagination, idempotency keys | 12 | "Design an API that is safe to retry for payments." |
| `05_rest_third_party_integration.md` | **Calling 3rd-party APIs**: timeouts, retries, circuit breaker, fallback, bulkhead, caching, error mapping | 12 | "3rd-party API is slow/flaky — how do you still return a proper response?" |
| `06_microservices.md` | Decomposition, sagas, outbox, service-to-service, resilience, data ownership | 15 | "An order spans 3 services and step 2 fails." |
| `07_spring_boot.md` | Auto-config, profiles, transactions, actuator, startup/perf issues | 12 | "@Transactional didn't roll back in production — why?" |
| `08_java8_java11.md` | Streams, Optional, CompletableFuture, HttpClient, GC/memory in production | 12 | "Parallel stream made the service slower — explain." |
| `09_nosql.md` | Couchbase / MongoDB / Cassandra: modelling, consistency, partition keys, hot partitions | 15 | "Why Cassandra over Mongo for this write-heavy workload?" |
| `10_splunk_observability.md` | Correlation IDs, structured logs, SPL searches, alerts, dashboards, RCA | 10 | "Trace one failed request across 5 services using Splunk." |
| `11_architecture_design.md` | Design patterns applied in real systems, end-to-end designs | 12 | "Design a notification platform on Kafka for 10M users." |
| `12_production_incidents.md` | Live incident stories, RCA, behavioural-technical | 10 | "Tell me about a production outage you led." |
| **Total** | | **~160** | |

Python track gets the same format later (`python/interview-scenarios/`) — the app is stack-agnostic.

### 2.3 The app: **Interview Coach** (dynamic, AI-backed)

Recommendation: **one stack-agnostic app** reusing the proven `pyprep-live` AI design
(`app/services/ai.py`: Claude provider + offline mock provider, streamed). It reads the Scenario
Answer Banks for *any* stack, so Java and Python share one UI.

**Screens / modes**

| Mode | What happens | AI? |
|---|---|---|
| **Browse by skill** | Skill chips from the JD (Kafka, REST, Spring Boot, NoSQL, Splunk, Java 8/11 …), level filter, search. Answer shown section-by-section (scenario → narrative → trade-offs → follow-ups → 60 s). | No |
| **Ask anything** | Type any question, e.g. *"How can we do rebalancing in Kafka?"* Claude answers **in the fixed scenario format**, grounded on the closest questions from the bank (retrieved and passed in the prompt). | Yes |
| **Mock interview** | Pick skills + seniority → Claude acts as the interviewer, asks one question, you type (or paste) your answer, it scores you against a rubric (scenario, depth, trade-offs, monitoring, clarity) and asks a **follow-up**. | Yes |
| **Improve my answer** | Paste your own answer → Claude rewrites it as the architect would and lists what you missed. | Yes |
| **Generate new question** | For a chosen skill, Claude drafts a new question in the bank's format; you review and **save it into the Markdown bank** (the bank grows). | Yes |
| **Self-test & progress** | Hide answers, "I can answer this confidently" tick, random-10 round, progress per skill (localStorage). | No |

**AI design**

- Persona system prompt: *Java architect, 30+ years, Kafka/microservices/NoSQL expert; answer as a
  live scenario; minimal code; always cover trade-offs and monitoring; finish with a 60-second answer.*
- **Skills = prompt packs**: each skill has a small instruction block (what to emphasise, what
  interviewers probe, key terms) loaded alongside the persona. Adding a skill = adding a file.
- Grounding: simple keyword/tag retrieval over the bank (no vector DB needed at ~160 Qs); top 3
  matching Q&As included in the prompt so answers stay consistent with your material.
- Prompt caching on the persona + skill pack (they repeat on every call).
- Model configurable via env (`ANTHROPIC_MODEL`); `AI_MODE=auto|claude|mock` exactly as pyprep-live.
- **Mock mode** (no API key): returns the closest stored answer, so the app is fully usable offline.
- API key read from env only, never stored in content or the browser.

**Backend shape** (same layering as pyprep-live: `api/ → services/ → config`)

```text
interview-coach/
  app/
    main.py
    api/routes.py           /api/stacks, /api/skills, /api/questions, /api/ask (SSE),
                            /api/interview/next, /api/interview/grade (SSE), /api/improve (SSE),
                            /api/generate (SSE), /api/save-question
    services/bank.py        parses the Markdown banks (fixed headings -> structured JSON)
    services/retrieve.py    tag/keyword scoring for grounding
    services/ai.py          persona + skill packs + providers (claude / mock)
    config.py
  skills/                   persona.md + one prompt pack per skill (java/*.md, python/*.md)
  static/index.html         single page, no CDN, light/dark
  tests/                    parser, retrieval, mock-mode endpoints, real-bank canary
```

---

## 3. Repo restructure by technology

Current root mixes Java, Python, scratch and reference material. Proposed:

```text
python-interview-preparation/          (consider renaming the repo root to interview-preparation/)
  java/
    java-interview-prep/               (moved, unchanged inside)
      interview-scenarios/             NEW — the Java Scenario Answer Bank
    javaprep-live/                     (moved; still finds ../java-interview-prep)
  python/
    python-interview-prep/             (moved, unchanged inside)
      interview-scenarios/             NEW later — Python bank
    pyprep-live/                       (moved; still finds ../python-interview-prep)
  interview-coach/                     NEW — the shared AI scenario app
  shared/
    material_ref/                      (source PDFs)
  scratch/
    Java/  example/                    (unstructured scratch, unchanged)
  CLAUDE.md  README.md  PLAN.md  PLAN_INTERVIEW_COACH.md
```

Why this is low-risk: both live apps locate their content via **sibling-relative paths**
(`../python-interview-prep`, `../java-interview-prep`), so moving each app *together with* its content
keeps them working without code changes.

Things that must be updated in the same change:

- `git mv` everything (keeps history).
- `CLAUDE.md` — every path, plus a new section for the coach and the scenario-bank format contract.
- Root `README.md`, `.vscode/settings.json` (check), `pyprep-live/docker-compose.yml` relative mounts
  (still `../python-interview-prep` — fine), deep-dive links that climb above the project root (grep).
- `pyprep-live/.venv` is path-sensitive on Windows → recreate it after the move (`start.cmd` does).
- `java-interview-prep.zip` at root: move to `shared/` or delete — your call.

Verification after the move: pyprep-live 32 tests + `test_real_repo.py`, python-interview-prep 68 tests,
`java-interview-prep/verify_examples.sh`, `javaprep-live --check`.

---

## 4. Phases

| # | Phase | Output | Review gate |
|---|---|---|---|
| 0 | **Restructure** | `java/`, `python/`, `shared/`, `scratch/`; all tests green; CLAUDE.md updated | You confirm layout |
| 1 | **Format + pilot content** | Answer template frozen; `02_kafka_consumers.md` and `05_rest_third_party_integration.md` written in full (~32 Q, incl. your two example questions) | **You review tone/depth** before we write 130 more |
| 2 | **Remaining Java banks** | Files 01, 03, 04, 06–12 | Spot-check |
| 3 | **Coach backend** | Parser, retrieval, AI service (claude + mock), endpoints, tests | Tests green |
| 4 | **Coach UI** | Browse / Ask / Mock interview / Improve / Generate / Progress | You try it live |
| 5 | **Python track** | Python scenario bank in the same format; app picks it up with no code change | — |
| 6 | **Docs** | README per project, CLAUDE.md contract section, start scripts | — |

Phase 1 is deliberately small: the expensive mistake is writing 160 answers in a voice you don't like.

---

## 5. Decisions I need from you

1. **App choice** — (a) new shared `interview-coach` (FastAPI, reuses pyprep-live AI design) — *recommended*;
   (b) add AI + Q&A to `javaprep-live` in pure Java (zero dependencies, but re-implements streaming/mock);
   (c) bolt a Q&A tab onto `pyprep-live`.
2. **"Skills"** — I read this as the JD skill areas acting as AI prompt packs (above). If you meant
   Claude Code *skills* (`/kafka-coach` slash commands in this repo), say so — that is a small add-on we
   can do in Phase 6.
3. **Restructure depth** — move into `java/` and `python/` as above, and rename the repo root folder?
4. **Existing material** — keep `topics/`, `deep_dive/`, guides as-is (scenario bank *complements* them),
   or eventually retire `topics/` once the bank covers it?
5. **Default model** — balanced cost (`claude-sonnet-5-5`) or best quality (`claude-opus-5-5`) for the coach?

---

## 6. Decisions taken and what was built (2026-10-13)

**Decisions (from review):** one shared Interview Coach for Java and Python · "skills" = per-topic
instruction files for the AI · restructure by technology and rename the root folder · organise the
experience around topics so a learner sees *all* questions for a topic in one place, existing and new ·
default model `claude-sonnet-5-5` · **every existing question must stay included**.

| Phase | Status |
|---|---|
| 0 Restructure | Done. `java/`, `python/`, `shared/`, `scratch/` via `git mv`. Links to `material_ref` fixed. pyprep-live 32 tests, prep lab 68 tests, 50 Java examples all pass after the move. **Root folder rename is left to you** (VS Code holds it open) — see below. |
| 1 Pilot content | Done. `java/java-interview-prep/interview-scenarios/02_kafka_consumers.md` (20 Q) and `05_rest_third_party_integration.md` (13 Q). **Awaiting your review of tone and depth.** |
| 2 Remaining Java banks | Not started — after your review. Topics already exist; their crib/deep-dive/guide questions are already in the app. |
| 3 Coach backend | Done. `interview-coach/app/` — library, parsers, retrieval, AI (Claude + offline mock). |
| 4 Coach UI | Done. Topics, practice, quick revision, ask, mock interview with scorecards, JD plan, draft-and-save, coverage. |
| 5 Python scenario banks | Not started. The Python topics already show all 687 existing questions. |
| 6 Docs | Done. `interview-coach/README.md`, `docs/RESEARCH.md`, CLAUDE.md, root README. |

**Coverage at build time:** Java 1,051 questions (33 scenario, 473 crib, 301 deep dive, 244 guide);
Python 687 (382 deep dive, 305 index). No question-bearing file is unwired; a test enforces it.

**Renaming the root folder** (do it with VS Code and both live apps closed):

```powershell
Rename-Item E:\Ravi_Workspace\python-interview-preparation interview-coach-workspace
```

Then recreate the two venvs (`python/pyprep-live/.venv`, `interview-coach/.venv`) — their launcher
scripts embed absolute paths — by deleting them and running each `start` script once.
