# Plan: every Java question gets a real, simple-language answer (then AI deep-dive)

Status: **started 2026-10-15**. Java first; Python after Java reaches the exit criteria below.

## 1. The problem (from your screenshots)

Examples you flagged: *How can a Java application leak memory despite the GC?*, *What is an immutable
class*, *Cohesion vs coupling*. Each jumped straight to jargon or a recipe without ever saying **what the
thing is**, why it exists, or showing it in a real situation. The AI "Go deeper" button was also a single
shot and, in offline mock mode, only echoed prompts.

## 2. Audit of the Java question bank (measured, not guessed)

| Measure | Value |
|---|---|
| Java questions in the coach | **1,148** (crib 473, deep dive 321, guide 244, scenario 110) |
| Crib + guide answers | 717 total, **median 50 words**, 188 under 40 words, 517 under 80 words |
| Short (< 60 words) with no concept layer | **~425** |
| Questions that now have a from-the-basics layer | **22** (this session) |

Shallow answers by topic (crib/guide under 60 words, no concept layer):

| Topic | Total Q | Shallow | Priority |
|---|---|---|---|
| java-core | 189 | 55 | P1 (your Java 8 gap, and the base of everything) |
| spring-boot | 134 | 46 | P1 |
| kafka | 139 | 22 | P1 (scale, lag, rebalancing, tuning) |
| rest-api | 70 | 25 | P1 |
| microservices | 51 | 21 | P1 |
| nosql | 44 | 21 | P1 (Couchbase/Mongo/Cassandra) |
| performance | 93 | 15 | P1 (weak area from feedback; mostly covered by banks 06-10) |
| production | 73 | 22 | P2 |
| architecture | 103 | 45 | P2 |
| splunk-observability | 39 | 21 | P2 |
| sql | 38 | 19 | P2 |
| testing | 36 | 19 | P3 |
| cloud-devops | 46 | 37 | P3 |
| leadership | 68 | 57 | P3 (behavioural: STAR stories, not definitions) |
| coding | 23 | 0 | done (code-first by nature) |

## 3. The answer standard (every question must meet this)

1. **Start here: the concepts** - every term defined in plain words, no jargon without a definition.
2. **A real scenario** - a concrete story with numbers: what happened, what the team saw.
3. **The answer** - step by step, each step with the *reason*, not just the rule.
4. **Trade-offs and what goes wrong.**
5. **How you would prove or monitor it** (tools, metrics, commands).
6. **Follow-ups with answers**, then the **60-second spoken answer**.
7. Then the learner chooses **Explain from basics** or **Go deeper (AI)** for more.

Format: scenario-bank files in `java/java-interview-prep/interview-scenarios/` with the new first section
label `**Start here: the concepts**` (key `concepts`). Existing entries are the reference:
`10_foundations_performance.md`, `11_foundations_kafka.md`, `12_foundations_spring_boot.md`,
`13_foundations_java_core.md`.

## 4. What is already built

| Item | Where |
|---|---|
| New optional section `concepts` in the bank parser | `interview-coach/app/services/bank.py` |
| **Explain from basics** button + `basics` AI mode (retrieves a matching from-the-basics entry offline; teaches from the ground up with a key) | `app/services/ai.py`, `app/api/routes.py`, `static/index.html` |
| **Go even deeper (level 2..6)** - each press builds on the previous reply: internals, scale, hardest follow-ups, incidents, synthesis | same files, `depth` request field |
| 22 from-the-basics Java entries (performance 6, Kafka 6, Spring Boot 3, core Java 7) | `interview-scenarios/10-13_*.md` |
| Production/monitoring Q&A in three tiers (12) + banks 06-09 | `deep_dive/24-25_*.md`, `interview-scenarios/06-09_*.md` |

## 5. Action list (Java)

Work in batches of 8-10 questions per file; run `pytest` in `interview-coach` after each batch.

| # | Action | Scope | Done when |
|---|---|---|---|
| J1 | Write from-the-basics entries for **java-core** shallow questions: generics/PECS, serialisation, String pool, streams vs loops, Optional, functional interfaces, `Comparable` vs `Comparator`, `final`/`finally`/`finalize`, `ConcurrentHashMap`, `ExecutorService`, CompletableFuture, memory model | ~55 Q (priority first 25) | every java-core crib/guide answer has a concept layer or is covered |
| J2 | **spring-boot**: DI and bean scopes, lifecycle, `@Transactional` (done), profiles/config, exception handling, validation, Actuator (done), security basics, testing slices | ~46 Q (first 20) | same |
| J3 | **kafka**: replication/ISR, retention/compaction, DLQ/retry topics, Schema Registry, Streams vs consumer, exactly-once, partition keys | ~22 Q | same |
| J4 | **rest-api + microservices**: idempotency, versioning, pagination, status codes, saga, circuit breaker, service discovery, API gateway, eventual consistency | ~46 Q | same |
| J5 | **nosql**: document vs wide-column vs key-value, partition/shard keys, consistency levels, indexing, when not to use | ~21 Q | same |
| J6 | **production, splunk-observability, sql, architecture**: logs/metrics/traces, SPL, window functions, indexes, CAP, caching, scaling | ~107 Q | same |
| J7 | **testing, cloud-devops, leadership**: mocking, test pyramid, CI/CD, containers, STAR stories (stories need *your* real experience) | ~113 Q | same |
| J8 | **Offline mock quality:** make `basics` fall back to the nearest deep-dive answer and its `docs:` link when no concept entry exists, and show the crib's linked deep dive inline | code | any card gives a meaningful offline explanation |
| J9 | **Drafting script** `interview-coach/scripts/draft_foundations.py`: uses the API key to draft a concepts-first entry for every flagged question into a review file; a human edits and promotes it | code + needs `ANTHROPIC_API_KEY` | drafts for all remaining shallow questions |
| J10 | **Coverage screen metric:** show "questions with a concept layer" per topic so progress is visible; add a canary threshold that only ratchets up | code | number visible and enforced |
| J11 | **Review pass:** read each batch aloud for jargon, wrong claims and missing numbers; fix | all batches | no undefined term in any answer |

## 6. Exit criteria for Java

- Every Java crib/guide/deep-dive question either has a concept layer or links to an entry that does.
- Any answer, in offline mock or AI mode, can answer: *what is it, why, a real scenario, how to prove it*.
- "Go even deeper" gives new material on each level with an API key, and a meaningful ladder offline.
- Coach test suite green, and the concept-layer metric is at 100% of questions flagged shallow.

## 7. Then Python

Same audit and the same standard for `python/python-interview-prep` (14 topic folders, `deep_dive/`,
`QUESTION_INDEX.md` with 687 questions): run the audit script, write the concept layer for flagged
questions in `python-interview-prep/interview-scenarios/`, wire the `skills/python/*` front matter, and
reuse the `basics` and `depth` features already built (they are stack-neutral).

## 8. Decisions needed from you

1. **API key:** can you set `ANTHROPIC_API_KEY`? It unlocks J9 (drafting at scale) and real "go deeper".
2. **Order:** I propose J1 -> J2 -> J3 -> J4 -> J5, then J6/J7.
3. **Leadership/behavioural:** these need your real projects; send 4-5 of your own stories and I will
   shape them into STAR answers.

## 9. Status update (2026-10-15, end of session)

| Action | State |
|---|---|
| J1-J7 drafting of all shallow Java questions (13 topics + leadership) | **Done** - `interview-scenarios/20-32_*_foundations.md`, `40_leadership_foundations.md`; 0 failures |
| J8 offline fallback | **Done** - a card merges its concepts-first answer by title, so no AI is needed (`Library._merge_foundations`) |
| J9 drafting script | **Done** - `interview-coach/scripts/draft_foundations.py` |
| J10 coverage metric | **Done** - `coverage()["depth"]`: 451 questions with a concepts layer, 0 shallow without one |
| J11 human review of drafts | **Open** - drafts are model output; read each topic file for wrong claims and fill `[placeholders]` in leadership answers with your own facts |
| Python | **On hold** at your request |

Principle agreed: the detailed answer is the product and works offline; AI ("Go deeper (optional AI)") is an
optional extra the learner pays for.
