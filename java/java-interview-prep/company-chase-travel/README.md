# Company pack: Chase Travel / Java rewrite

Preparation for an engagement described as the **Chase Travel "Java rewrite"**: rewriting and modernising travel-platform
services in Java, plus upgrading and migrating Java products. It complements the
[Java + GenAI profile pack](../profile-java-genai/README.md).

## Start here: Sujay's brush-up list (Chase project)

> *"Hello Ravikumar, Sujay here from Chase project. Can you just brush up on below points?
> 1. Spring boot rest API 2. Database connection from spring boot 3. Kafka consumer and producer 4. AWS S3, ECS, Aurora Postgres"*

These four points are the priority. Each has a 30-question file (10 basic, 10 mid, 10 advanced) with crisp answers,
a project hook per part, a revision card and a 60-second answer, all framed around one illustrative booking service.
Then one end-to-end bank shows how the four fit together, which is what a lead usually asks next.

| # | Sujay's point | File | Questions | What it covers |
|---|---|---|---|---|
| 1 | Spring Boot REST API | [brush-up/01-spring-boot-rest-api.md](brush-up/01-spring-boot-rest-api.md) | 30 | Annotations, status codes, DTOs, validation, Problem Details, idempotency keys, security, RestClient + resilience, testing, versioning, zero-downtime, Boot 3 to 4 |
| 2 | Database connection from Spring Boot | [brush-up/02-database-connection-spring-boot.md](brush-up/02-database-connection-spring-boot.md) | 30 | DataSource + HikariCP, JPA vs JdbcTemplate, transactions, N+1, locking, Aurora reader/writer routing, Flyway, batching, failover, pool exhaustion, outbox, IAM auth, RDS Proxy |
| 3 | Kafka consumer and producer | [brush-up/03-kafka-producer-consumer.md](brush-up/03-kafka-producer-consumer.md) | 30 | KafkaTemplate, `@KafkaListener`, groups, keys and ordering, offsets, no-loss producer settings, DLT and retry topics, rebalances, idempotent consumers, schemas, lag, exactly-once, MSK security |
| 4 | AWS S3, ECS, Aurora Postgres | [brush-up/04-aws-s3-ecs-aurora-postgres.md](brush-up/04-aws-s3-ecs-aurora-postgres.md) | 30 | S3 security, pre-signed URLs, multipart, ECS task vs execution role, health checks, autoscaling, Aurora endpoints, backups, failover, HA/DR, cost, troubleshooting |
| E2E | All four together | [82_company_chase_travel_brushup_e2e.md](../interview-scenarios/82_company_chase_travel_brushup_e2e.md) | 8 | Architecture walkthrough, one request through every layer, IAM/secrets, Kafka -> S3 + Aurora idempotently, scaling budget, Aurora failover end to end, local/CI testing, a cross-system incident |

**One-day revision plan:** morning: files 1 and 2 (say each Part 1 answer aloud, read Parts 2–3); afternoon: files 3 and 4;
evening: the 8 end-to-end questions, then the four 60-second answers at the bottom of each file. Replace every
illustrative travel example with a real one from your own project.

**What was updated from the original drafts** (`java/InterviewTopic/`, left unchanged): a Chase-project header and functional
requirement, a 60-second answer per point, and corrections for current facts: RFC 9457 Problem Details;
`@MockBean` removed in Boot 4; HTTP service clients and the OpenTelemetry starter in Boot 4; ECS built-in blue/green
(July 2025, canary/linear); S3 objects up to 50 TB (Dec 2025); Aurora PostgreSQL storage up to 256 TiB (July 2025);
Aurora Serverless v2 scale to 0 ACU; Hikari sizing formula (database cores, whole database); `LazyConnectionDataSourceProxy`
for reader routing; realistic Aurora failover timing; KIP-848 opt-in (`group.protocol=consumer`); `ErrorHandlingDeserializer`.

## JPMorgan Chase interview: what to target (Java, mid to senior)

Researched on 2026-10-23 from public candidate reports and job postings (sources at the bottom). These are **anecdotes,
not an official process**: formats vary by team, location and level, so confirm the stages with your recruiter.

**The process candidates usually describe (experienced hires)**

| Stage | What happens | How to prepare |
|---|---|---|
| Online assessment | HackerRank, about 60-90 min, usually 2 easy-to-medium coding problems | Arrays, strings, hash maps, sorting: [50_coding_round_problems.md](../interview-scenarios/50_coding_round_problems.md) |
| Recruiter screen | 15-30 min: background, stack, motivation | A 2-minute project story with numbers |
| Technical round(s) | Core Java, collections, multithreading, Spring/Spring Boot, Hibernate, SQL; sometimes **rapid-fire with a VP** | Banks 83, 84, 85 (60-second answers first) |
| Final loop ("Superday" / "Power Day") | 2-3 back-to-back sessions: coding, **a pull-request code review**, system design for senior levels, behavioural | Bank 84 Q11 (code review), bank 86 (design), STAR stories |
| Hiring manager / team match | Past projects, architecture decisions, leadership; experienced hires may go through team matching afterwards | Bank 40 (leadership) + your own incidents |

**Questions and topics candidates actually report** (each mapped to an answer in this repo)

| Reported topic | Where it is answered |
|---|---|
| `final`, `HashMap`, `synchronized`, `ConcurrentHashMap` | 83 Q1, Q4 · 84 Q1, Q3 |
| How does ConcurrentHashMap work, why better than a synchronized block; Lock vs synchronized | 84 Q1, Q3 |
| CompletableFuture and asynchronous operations | 84 Q5 |
| Multithreading, concurrency, memory management | 84 Q2, Q4, Q6, Q7, Q8, Q9 |
| "Concurrency control in Java, extended to distributed systems" | 84 Q10 |
| Code review: fix bugs, thread safety and performance follow-ups | 84 Q11 |
| ACID transactions | 85 Q6 (plus Q4 on `@Transactional`) |
| REST APIs and dependency injection | 85 Q1, Q3, Q7-Q10 |
| Kafka messaging | 86 Q1-Q4 · bank 62 · brush-up file 3 |
| Microservices, observability, "how would you handle this in production?", scaling | 86 Q5, Q8, Q9, Q10 · banks 09, 27 |
| System design: rate limiter; document upload and validation with a tracking link | 86 Q6, Q7 |
| Advantages of Java 21 features; compare Java with Scala and other languages | 87 Q3, Q11 |
| SQL, Linux | banks 29 (SQL), 18_production_troubleshooting deep dive |
| Behavioural: past projects, architecture decisions, leadership, conflict | bank 40 |

**The JPMorgan Chase Java mid/senior pack: 54 questions, each with a 120-second and a 60-second answer**

| File | Focus | Questions |
|---|---|---|
| [83_company_jpmc_java_core_mid_senior.md](../interview-scenarios/83_company_jpmc_java_core_mid_senior.md) | HashMap internals, equals/hashCode, String, final/finally/finalize, exceptions, streams, generics, collections, Comparator, patterns + SOLID | 10 |
| [84_company_jpmc_concurrency_jvm.md](../interview-scenarios/84_company_jpmc_concurrency_jvm.md) | synchronized vs Lock vs atomics, volatile, ConcurrentHashMap, pool sizing, CompletableFuture, deadlock, virtual threads, JVM memory, GC, distributed concurrency, **code review round** | 11 |
| [85_company_jpmc_spring_boot_data_rest.md](../interview-scenarios/85_company_jpmc_spring_boot_data_rest.md) | **Filter students by name and org (REST structure)**, auto-configuration, DI and scopes, @Transactional traps, N+1, ACID and locking, errors, security, idempotency, resilience, config, testing | 12 |
| [86_company_jpmc_microservices_kafka_design.md](../interview-scenarios/86_company_jpmc_microservices_kafka_design.md) | Kafka ordering, no loss / no duplicates, lag, poison messages, saga + outbox, **rate limiter**, **document upload design**, observability, 10x peak, monolith split | 10 |
| [87_company_jpmc_java_11_to_27.md](../interview-scenarios/87_company_jpmc_java_11_to_27.md) | **Java 11 to 27 version map** (table at the top), 8->11, 17, 21, 22-25, 26-27, LTS policy, data-oriented programming, structured concurrency and scoped values, upgrades, GC/startup evolution, Java vs Kotlin/Scala/Go | 11 |

Levels: 18 mid, 32 senior, 4 architect ("expert"). Every answer uses the same parts: *Start here: the concepts* (plain
language) -> *The live scenario* -> *What the interviewer is really checking* -> **How I answer it (120-second, point by
point)** -> *Trade-offs* -> *Follow-ups* -> **60-second answer**.

**How to use the two answer lengths**
- In a rapid-fire round, give the **60-second answer** and stop. Let the interviewer pick the follow-up.
- In a mid or senior deep-dive round, give the 60-second answer first, then expand into the **120-second points** when they say
  "go deeper" or "how exactly?".
- Replace every illustrative example (FX cache, payments, trade blotter) with a real one from your own project when you can.

**Three-day plan for the JPMC pack**
1. **Day 1:** banks 83 and 84. Say each 60-second answer aloud; read the 120-second points for HashMap, ConcurrentHashMap,
   CompletableFuture, virtual threads, and the code-review question.
2. **Day 2:** bank 85 (start with Q1, the student-filter API) and bank 86 Q1-Q5 (Kafka and sagas).
3. **Day 3:** bank 86 Q6-Q10 (design: draw the rate limiter and the upload pipeline on paper) and bank 87 (learn the version
   table at the top, then Q3 and Q5). Finish with two coding problems from bank 50 under a 30-minute timer.

## Read first: what is public and what is assumed

**Publicly reported facts** (sources at the bottom):

- JPMorgan Chase agreed in December 2020 to acquire **cxLoyalty's** travel and loyalty platform; the deal closed in early 2021
  and was described as bringing a modern, scalable travel technology platform in-house.
- Chase had moved its rewards travel portal to Expedia in 2018 and later **migrated card members back onto the
  cxLoyalty-based platform**, now branded Chase Travel.
- Chase Travel engineering job postings list **Java or .NET, React and Spring Boot** among the skills.
- JPMorgan Chase is publicly cited (by Moderne) as running **OpenRewrite** at large scale (over 16,000 users) to keep
  applications on supported Java versions.

**Not public:** the platform's internal architecture, the scope of any "Java rewrite", the source technologies, and the
timelines. The scenarios in this pack are **illustrative**, built from the facts above and standard travel-industry and
enterprise-migration practice. A reasonable working assumption, consistent with the job postings, is that a "Java
rewrite" means moving older services (older J2EE and/or .NET) onto modern Java/Spring Boot microservices, and
keeping a large Java estate current (Java 8/11 to 17/21/25, Spring Boot 2 to 3 to 4).

**How to use this in the interview:** say "in a platform like yours..." or "if the rewrite involves X, I would...", and
ask them what the scope actually is. Never present assumptions as inside knowledge.

## The question banks

| File | Focus | Questions |
|---|---|---|
| [80_company_chase_travel_migration.md](../interview-scenarios/80_company_chase_travel_migration.md) | Rewrite strategy, strangler fig, shadow traffic, ACL/adapters, branch by abstraction, data migration with CDC, Java 8 to 25 upgrade, OpenRewrite at scale, Spring Boot 2 to 3 to 4, characterisation tests, design patterns, stateless conversion, batch migration, cutover/rollback, performance parity, GenAI-assisted migration | 15 |
| [81_company_chase_travel_domain.md](../interview-scenarios/81_company_chase_travel_domain.md) | Rewards-travel platform design: architecture, supplier search aggregation, points + cash split payment, unknown supplier outcomes, quotes and price changes, cancellation state machine, PCI/PII, promotional peaks, business observability, GenAI trip assistant | 10 |
| [82_company_chase_travel_brushup_e2e.md](../interview-scenarios/82_company_chase_travel_brushup_e2e.md) | Sujay's four points end to end: REST + Aurora + Kafka + S3 on ECS | 8 |
| [brush-up/](brush-up/) (4 files) | Sujay's four points, 30 questions each, basic to advanced | 120 |

## Where these questions are used

| Bank file | Questions | Interview Coach topic card (Java stack) | Coach `skill:` id |
|---|---|---|---|
| `80_company_chase_travel_migration.md` | 15 | System design & design patterns | `architecture` |
| `81_company_chase_travel_domain.md` | 10 | System design & design patterns | `architecture` |
| `82_company_chase_travel_brushup_e2e.md` | 8 | System design & design patterns | `architecture` |
| `brush-up/01-spring-boot-rest-api.md` | 30 | REST APIs & third-party integration | `rest-api` |
| `brush-up/02-database-connection-spring-boot.md` | 30 | Spring & Spring Boot | `spring-boot` |
| `brush-up/03-kafka-producer-consumer.md` | 30 | Apache Kafka | `kafka` |
| `brush-up/04-aws-s3-ecs-aurora-postgres.md` | 30 | Cloud, Docker & Kubernetes | `cloud-devops` |
| `83_company_jpmc_java_core_mid_senior.md` | 10 | Java 8, Java 11 & modern Java | `java-core` |
| `84_company_jpmc_concurrency_jvm.md` | 11 | Java 8, Java 11 & modern Java | `java-core` |
| `85_company_jpmc_spring_boot_data_rest.md` | 12 | Spring & Spring Boot | `spring-boot` |
| `86_company_jpmc_microservices_kafka_design.md` | 10 | Microservices | `microservices` |
| `87_company_jpmc_java_11_to_27.md` | 11 | Java 8, Java 11 & modern Java | `java-core` |
| **Total company pack** | **207** | | |

In the coach: **Topics** -> *System design & design patterns* lists the scenario banks (shown first); the four brush-up files appear as
*deep dive* questions inside their own topic cards. **Ask anything** and **Mock interview** use all of them for grounding
and scoring; **Coverage** shows every file wired in.

## Migration playbook on one page

```text
 1. WHY      measurable goals: one stack, release speed, cloud scale for peaks, supported runtimes, security
 2. ASSESS   inventory services, data, supplier integrations, batch jobs; map bounded contexts
 3. DECIDE   per component: retain / rehost / replatform / refactor / REWRITE / replace / retire
 4. PLATFORM CI/CD, Kubernetes, observability, security baseline, company Spring Boot starter
 5. SLICE    strangler facade -> new Java service -> shadow traffic + diffing -> progressive cutover
 6. DATA     CDC first, backfill, continuous reconciliation, cutover, reverse CDC for rollback
 7. VERIFY   characterisation tests, contract tests, record/replay, performance parity at peak
 8. RETIRE   decommission legacy after a stable period; delete toggles and adapters
 Upgrades in parallel: OpenRewrite recipes (Java version, Boot version, javax->jakarta), reviewed as PRs, in waves
```

## Design patterns map (what to use where)

| Problem in the rewrite | Pattern |
|---|---|
| Replace a legacy capability incrementally | **Strangler fig** (gateway routing), **branch by abstraction** (inside a codebase) |
| Keep legacy/supplier models out of the new domain | **Anti-corruption layer** = Adapter + Facade + translators |
| Many suppliers with different APIs | **Adapter** per supplier + **Strategy**/registry selection |
| Pricing rules (markups, tier redemption, promotions) | **Chain of responsibility**, **Specification** for eligibility |
| Booking lifecycle | **State** pattern / explicit state machine |
| Complex itinerary or booking requests | **Builder** (immutable) |
| Common flow with supplier-specific steps | **Template method** |
| Cross-service booking (points + card + supplier) | **Saga** + **transactional outbox** + **idempotent consumer** |
| Trip history across services | **CQRS** read model |
| Supplier failures and slowness | **Circuit breaker**, **bulkhead**, **timeout**, **fallback** |
| Wrapping clients with caching/metrics/retry | **Decorator** |
| Reacting to bookings (notifications, loyalty, analytics) | **Observer** / domain events |
| Safe progressive release | **Feature toggles**, **canary**, **shadow traffic** |

## Questions to ask them

1. What does "Java rewrite" cover: rewriting services from another stack, re-architecting old Java, or upgrading versions?
2. What is the target stack (Java and Spring Boot versions, cloud, Kubernetes platform, Kafka)?
3. How are you verifying parity with the existing system: shadow traffic, golden datasets?
4. Which capabilities are already migrated, and which are next?
5. Is OpenRewrite (or similar tooling) part of the upgrade approach?
6. Where does GenAI fit: customer-facing assistant, agent tools, or engineering productivity in the migration?

## Sources

- [JPMorgan Chase acquiring a leading travel and loyalty business (Business Wire, Dec 2020)](https://www.businesswire.com/news/home/20201228005218/en/JPMorgan-Chase-Acquiring-a-Leading-Travel-and-Loyalty-Business)
- [JPMorgan is acquiring a major credit card rewards business (CNBC, Dec 2020)](https://www.cnbc.com/2020/12/28/jpmorgan-is-acquiring-a-major-credit-card-rewards-business-in-a-bet-on-travel.html)
- [Chase moves travel portal back to cxLoyalty from Expedia (Doctor of Credit)](https://www.doctorofcredit.com/chase-moves-travel-portal-back-to-cxloyalty-from-expedia/)
- [Chase migrates cardholders to new travel booking portal (The Points Guy)](https://thepointsguy.com/news/chase-new-travel-portal/)
- [Senior Lead Software Engineer, Chase Travel Technology: Java/.NET (job posting)](https://www.themuse.com/jobs/jpmorganchase/senior-lead-software-engineer-chase-travel-technology-java-net)
- [Modernizing legacy Java code at scale (Moderne blog, JPMorgan Chase OpenRewrite usage)](https://moderne.ai/blog/modernizing-legacy-java-code-at-scale)
- [OpenRewrite: Migrate to Java 25 recipe](https://docs.openrewrite.org/recipes/java/migrate/upgradetojava25)
- [Spring Boot 4.0.0 available now (spring.io)](https://spring.io/blog/2025/11/20/spring-boot-4-0-0-available-now/)

JPMorgan Chase interview research and Java version facts (checked 2026-10-23):

- [JPMorganChase Senior Java Developer interview questions (Glassdoor)](https://www.glassdoor.com/Interview/JPMorganChase-Senior-Java-Developer-Interview-Questions-EI_IE5224839.0,13_KO14,35.htm)
- [JPMorganChase Software Engineer Java Developer interview questions (Glassdoor)](https://www.glassdoor.com/Interview/JPMorganChase-Software-Engineer-Java-Developer-Interview-Questions-EI_IE5224839.0,13_KO14,46.htm)
- [JPMorgan Chase SDE-3 Java full-stack interview experience, Bangalore (LeetCode Discuss)](https://leetcode.com/discuss/post/7359766/jpmorgan-chase-sde-3-java-full-stack-dev-rxak/)
- [AVP Java Developer interview, Mumbai, January 2025 (Taro)](https://www.jointaro.com/interviews/companies/jpmorgan-chase/work-experiences/avp-java-developer-mumbai-january-30-2025-4-3fca2270/)
- [JP Morgan interview experience: Java, multithreading, microservices (Medium)](https://medium.com/@pardeepgill82/jp-morgan-interview-experience-java-multithreading-microservices-3df9473dfb94)
- [JPMorgan Chase software engineer interview guide 2026 (Interview Query)](https://www.interviewquery.com/interview-guides/jp-morgan-chase-software-engineer)
- [JPMorgan's interview process 2026 (TechPrep)](https://www.techprep.app/blog/jpmorgan-interview-process)
- [Lead Software Engineer: Java, Spring Boot, Kafka, microservices (JPMorganChase posting)](https://www.themuse.com/jobs/jpmorganchase/lead-software-engineer-java-spring-boot-kafka-microservices)
- [JDK 27 project page: features and GA date (OpenJDK)](https://openjdk.org/projects/jdk/27/)
- [The arrival of Java 26 (Oracle Java blog)](https://blogs.oracle.com/java/the-arrival-of-java-26)
- [The arrival of Java 27 (Oracle Java blog)](https://blogs.oracle.com/java/the-arrival-of-java-27)
- [JDK 27 and JDK 28: what we know so far (InfoQ)](https://www.infoq.com/news/2026/08/java-27-so-far/)
