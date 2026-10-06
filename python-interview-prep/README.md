# Python Interview Prep — Hands-On Lab

A self-contained playground for Python backend interview prep (6-10 yrs level): core language,
concurrency, Pandas, FastAPI/REST, Kafka, caching/queues, production resilience, AWS Lambda,
GenAI patterns, and the system-design scenario rounds (zero downtime, observability, capacity
planning). Every topic folder has a `README.md` with the condensed concept notes + interview
Q&A crib sheet, and runnable `.py` files you're meant to open, run, break, and modify.

**Looking for a specific question?** See **[QUESTION_INDEX.md](QUESTION_INDEX.md)** — every
question below, one file, each linked straight to the line that demonstrates it.

**Want the full answer, not the crib-sheet version?** See **[`deep_dive/`](deep_dive/)** — 32
long-form Q&A documents, one per interview topic, with multi-paragraph answers, trade-offs,
failure modes, hands-on drills and a "60-second spoken answer" for each.

## How to use this

1. Pick a folder in the order below (or jump to whatever you're weak on).
2. Read that folder's `README.md` first — it's the "explain this in 60 seconds" version.
3. Run the numbered example files top to bottom: `python 01_something.py`.
4. Each example has `# EXPERIMENT:` comments — prompts to change something and re-run to see the
   effect. That's the actual learning; reading the code is not enough.
5. Where a file ends with an `exercises.md` or an `# EXERCISE` block, try it yourself before
   peeking at the reference solution mentioned there.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Some folders need extra infrastructure (a local Kafka broker, Redis) — each of those READMEs says
exactly what's optional vs. required, and gives a fallback pure-Python simulation you can run
without any infra when you just want to see the pattern.

## Map of topics

| Folder | Covers | Runs with just stdlib? |
|---|---|---|
| `01_python_core/` | data structures, comprehensions, decorators, generators/iterators, context managers, descriptors, metaclasses, OOP/MRO, exceptions, memory management, **variable scope/LEGB**, **ABCs & `Protocol`**, **senior-level basics**, **multi-level exception handling** | Yes |
| `02_concurrency/` | GIL, threading, multiprocessing, asyncio, synchronization primitives | Yes |
| `03_pandas_data_handling/` | Series/DataFrame, missing data, groupby/merge, performance at scale | Needs `pandas` |
| `04_testing_tdd/` | TDD workflow, pytest, mocking, fixtures | Needs `pytest` |
| `05_web_apis_fastapi/` | FastAPI app (routers/services/repos/DI), REST semantics, status codes, auth | Needs `fastapi`, `uvicorn` |
| `06_kafka/` | topics/partitions/replication, delivery semantics, retry+DLQ, schema registry, **client config profiles**, **Kafka → Aurora sink** | Partly — 5 of its 7 Python files need no broker |
| `07_caching_queues/` | cache-aside, stampede protection, SQS/SNS-style fan-out, DLQ | Yes (simulated); Redis optional |
| `08_scaling_production_resilience/` | retry+backoff, circuit breaker, rate limiting, health checks | Yes |
| `09_aws_lambda_streaming/` | Lambda handler patterns, streaming large files without loading them fully, **the full 100GB-file answer** (external sort, dedupe, parallel chunks, resume) | Yes (simulated S3) |
| `10_genai_llm_patterns/` | prompt engineering, RAG pipeline shape, semantic caching | Yes (mocked, no API key needed) |
| `11_coding_challenges/` | anagram grouping, sliding window max, LRU cache, string reversal, **retry decorator**, **nested-dict search** | Yes |
| `12_framework_internals/` | repository pattern, DI from scratch, plugin architecture, middleware chain, config | Yes |
| `13_system_design_scenarios/` | **zero-downtime production changes**, **observability** (metrics/logs/traces/SLO), **scaling 100 → 600 TPS**, **AI leverage & customer-impact stories** | Yes |
| `deep_dive/` | **32 long-form Q&A documents** — the full answers behind every crib sheet | — (reading) |
| `legacy_examples/` | your original scratch files, kept as-is for reference | — |

## Source material

The concept notes and deep dives are distilled from the interview-prep PDFs in
[`../material_ref/`](../material_ref/): *Python Developer Deep-Dive Interview Q&A* (37pp),
*Python Advanced Interview Topics* (35pp — framework dev, scaling, Kafka, caching, queues,
production stability, AI-first), and the *Python & Kafka Interview Q&A Handbook* (58pp, 194
questions across the 14 topics the `deep_dive/` set mirrors). This project turns their Q&A into
something you can actually execute and poke at, and the deep dives expand each answer with the
trade-offs, failure modes and production detail the sources summarise in a line or two.

> The other three PDFs in `material_ref/` (`Kafka_Master_Guide`, `Kafka_Advanced_Master_Pack`,
> `Full_Interview_Preparation`) are largely generated placeholder text — "Explain Kafka concept
> 17", "Answer includes design, trade-offs…" — and contributed only their few genuine sections.

## Suggested order for a first pass

`01` → `11` → `02` → `04` → `05` → `03` → `07` → `08` → `13` → `12` → `06` → `09` → `10`

(Core language and coding challenges first since they show up in every round; Kafka and infra-heavy
topics last since they need the most setup. `13` sits after `08` because the resilience patterns in
`08` are what the system-design scenarios assume you already have.)

Read the matching [`deep_dive/`](deep_dive/) document **before** running each folder's files — the
crib sheet tells you *what*, the deep dive tells you *why*, and the `# EXPERIMENT:` prompts in the
code are where it actually sticks.

## If you're coming from Java

Start with [`deep_dive/21_java_to_python_bridge.md`](deep_dive/21_java_to_python_bridge.md) and
[`01_python_core/11_java_to_python_bridge.py`](01_python_core/11_java_to_python_bridge.py). The
concepts transfer; the syntax, the idioms and about seven specific traps do not. Every other deep
dive also carries a **Java contrast** block where the semantics genuinely differ.
