# Python Interview Prep — Hands-On Lab

A self-contained playground for Python backend interview prep (6-10 yrs level): core language,
concurrency, Pandas, FastAPI/REST, Kafka, caching/queues, production resilience, AWS Lambda, and
GenAI patterns. Every topic folder has a `README.md` with the condensed concept notes + interview
Q&A crib sheet, and runnable `.py` files you're meant to open, run, break, and modify.

**Looking for a specific question?** See **[QUESTION_INDEX.md](QUESTION_INDEX.md)** — every
question below, one file, each linked straight to the line that demonstrates it.

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
| `01_python_core/` | data structures, comprehensions, decorators, generators/iterators, context managers, descriptors, metaclasses, OOP/MRO, exceptions, memory management | Yes |
| `02_concurrency/` | GIL, threading, multiprocessing, asyncio, synchronization primitives | Yes |
| `03_pandas_data_handling/` | Series/DataFrame, missing data, groupby/merge, performance at scale | Needs `pandas` |
| `04_testing_tdd/` | TDD workflow, pytest, mocking, fixtures | Needs `pytest` |
| `05_web_apis_fastapi/` | FastAPI app (routers/services/repos/DI), REST semantics, status codes, auth | Needs `fastapi`, `uvicorn` |
| `06_kafka/` | topics/partitions/replication, delivery semantics, retry+DLQ, schema registry | Needs a broker (docker-compose provided) |
| `07_caching_queues/` | cache-aside, stampede protection, SQS/SNS-style fan-out, DLQ | Yes (simulated); Redis optional |
| `08_scaling_production_resilience/` | retry+backoff, circuit breaker, rate limiting, health checks | Yes |
| `09_aws_lambda_streaming/` | Lambda handler patterns, streaming large files without loading them fully | Yes (simulated S3) |
| `10_genai_llm_patterns/` | prompt engineering, RAG pipeline shape, semantic caching | Yes (mocked, no API key needed) |
| `11_coding_challenges/` | anagram grouping, sliding window max, LRU cache, string reversal | Yes |
| `legacy_examples/` | your original scratch files, kept as-is for reference | — |

## Source material

The concept notes distilled into each README come from three interview-prep documents already
reviewed for this project: *Python Developer Deep-Dive Interview Q&A*, *Python Advanced Topics
Interview* (framework dev, scaling, Kafka, caching, production stability, AI-first tech), and the
*Python & Kafka Interview Q&A Handbook* (194 questions across 14 topics). This project turns their
Q&A into something you can actually execute and poke at.

## Suggested order for a first pass

`01` → `11` → `02` → `04` → `05` → `03` → `07` → `08` → `06` → `09` → `10`

(Core language and coding challenges first since they show up in every round; Kafka and infra-heavy
topics last since they need the most setup.)
