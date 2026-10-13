# Java interview prep (Java 8/11, Spring Boot, microservices, REST, Kafka, NoSQL, Splunk)

A hands-on Java interview-prep lab with the same shape as `python-interview-prep`: runnable examples,
long-form deep dives, a question bank, and a local app that runs it all.

## Start here

```bash
cd ../javaprep-live
start.cmd            # Windows (or ./start.sh)   ->  http://127.0.0.1:8090
```

Needs only a **JDK 21+** on PATH. No Maven, no Gradle, no pip. See [`../javaprep-live/README.md`](../javaprep-live/README.md).

Or work from the terminal:

```bash
java examples/12_kafka/02_consumer_groups_rebalancing_and_lag.java      # any example, any folder
./verify_examples.sh                                                    # all examples, expects exit 0
./verify_examples.sh 12_kafka                                           # one chapter
```

## What is in here

| Path | What | Count |
|---|---|---|
| `examples/NN_*/*.java` | single-file, dependency-free runnable programs; Spring/Kafka/DB behaviour is **simulated** so failure modes are visible | 46 in 19 chapters |
| `deep_dive/NN_*.md` | long-form Q&A per chapter: probes, must-knows, full answers, worked example, drills, 60-second answer. Start at [`deep_dive/README.md`](deep_dive/README.md) (requirement coverage map + 7-day plan + `.docx` question index) | 21 |
| `topics/*.md` | crib-sheet Q&A, one answer per question (feeds the app's Q&A drill and `build_site.py`) | 21 files, 473 Q |
| `Java_SpringBoot_Kafka_Interview_QA_Guide.md` | 96 requirement-aligned questions with concise, conservative answers | 96 Q |
| `Docx_Gap_Supplement_QA.md` | coverage map of the 44-question `.docx` + 23 extra Q&A (Q97-Q119) with small examples; long form in `deep_dive/19_docx_gap_topics.md` | 23 Q |
| `Round_Questions_QA.md` | 102 real interview-round questions (Cybage list, fresher, experienced, Kafka round, other) in simple language; each has a simple answer, key points and one industry example | 102 Q |
| `QUESTION_INDEX.md` | auto-generated index of `topics/` | |
| `build_site.py`, `index.html` | the original standalone static study site (works offline, no server) | |

## Chapters

| # | Chapter | Examples |
|---|---|---|
| 01 | Java 8: lambdas, streams, Optional, java.time, CompletableFuture | 4 |
| 02 | Collections: HashMap internals, pitfalls, concurrent collections | 2 |
| 03 | Java 11 and beyond: features, HttpClient, virtual threads | 3 |
| 04 | Concurrency: races, atomics, thread pools, deadlocks | 3 |
| 05 | JVM, GC, leaks, strings | 1 |
| 06 | Spring core: mini IoC container, AOP proxies and self-invocation | 2 |
| 07 | Spring Boot: auto-configuration, config precedence, Actuator, graceful shutdown | 2 |
| 08 | REST API: status codes, ETag, idempotency (real HTTP server) | 1 |
| 09 | Spring Data JPA: N+1, isolation levels, optimistic locking | 2 |
| 10 | Spring Security: JWT from scratch, password hashing | 1 |
| 11 | Microservices: circuit breaker/retry/bulkhead, saga, outbox | 3 |
| 12 | **Kafka**: partitions/keys, consumer groups/rebalancing/lag, delivery semantics/DLT, config and capacity | 4 |
| 13 | **NoSQL**: document store/indexes, Cassandra ring/quorum/modeling | 2 |
| 14 | **Splunk** and observability: structured logs + SPL, SLOs and burn rates | 2 |
| 15 | Testing: test doubles, mini-Mockito | 1 |
| 16 | System design: 100 -> 600 TPS capacity math, caching | 2 |
| 17 | Design patterns and SOLID, plus a per-pattern creational/structural/behavioural set | 4 |
| 18 | Production troubleshooting: incident triage runbook | 1 |
| 21 | **Coding round**: strings/arrays, Java 8 stream problems, lists/trees/graphs, LRU/singleton/idempotent POST/rate limiter, DI types, JWT, output traps | 6 |

## How to study

See the 7-day plan and the requirement-to-chapter map in [`deep_dive/README.md`](deep_dive/README.md).
Short version: run an example, read its deep dive, then drill the matching topic in the app with answers hidden.

## Adding content

1. New example: `examples/NN_chapter/NN_name.java` (header comment `* NN - Title` and `Interview angle:`; use `section("N. ...")` for outline; ASCII output only; must exit 0).
2. Add it to the chapter's `deep_dive/NN_chapter.md` ("Runnable" line + a Q&A or worked-example reference).
3. New Q&A: add to the deep dive, or to `topics/NN-*.md` using the heading format
   `### Q<n> [basic|intermediate|advanced|design] Question` (see `topics/_TEMPLATE.md`), then
   `python3 build_site.py --title "Java Lead Interview Prep"` to refresh `index.html` and `QUESTION_INDEX.md`.
4. `./verify_examples.sh` (or `javaprep-live/start.cmd --check`).

## Static site (original workflow)

```bash
python3 build_site.py --title "Java Lead Interview Prep"   # writes index.html + QUESTION_INDEX.md
# open index.html in a browser (works offline)
```

`build_site.py` validates headings and warns when a topic has fewer than 15 or more than 25 questions
or fewer than 3 `[design]` questions. Commit `index.html` and enable GitHub Pages to publish it.

## Notes

- `index_1.html` is an older generated copy of `index.html`; `java_interview_app_prompts.md` is identical to `APP_BUILD_PROMPT.md`. Both can be deleted when you are happy with the rest.
- `topics/19-resume-tech-stack-deep-dive.md` and `topics/20-...` contain profile-specific material; the rest is generic.
