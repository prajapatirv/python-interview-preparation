# Deep dives: the long-form Java interview set

Each document follows the same structure as the Python deep dives:

1. **What interviewers are actually probing**
2. **Must-know points**
3. **Interview questions and full answers** (multi-paragraph, with code, trade-offs and failure modes)
4. **A worked example** (which runnable file to run and what to look for in the output)
5. **Hands-on drills**
6. **The 60-second spoken answer**

The division of labour:

| Where | Use it for |
|---|---|
| [`../topics/*.md`](../topics) (21 files, 458 Q&A) | quick revision, one answer per question, drives the Q&A drill / mock mode |
| [`../Java_SpringBoot_Kafka_Interview_QA_Guide.md`](../Java_SpringBoot_Kafka_Interview_QA_Guide.md) | 96 requirement-aligned Q&A, concise and conservative |
| **`deep_dive/NN_*.md` (this folder)** | the full treatment: mechanisms, traps, trade-offs, what to say |
| [`../examples/NN_*/*.java`](../examples) | runnable proof; each prints the behaviour the doc describes |

Folder names match one-to-one: `examples/12_kafka/` is explained by `deep_dive/12_kafka.md`.
The live app uses that convention to link them, so keep numbering append-only.

## Requirement coverage map

The requirement profile for this role (Java/J2EE with Java 8 and 11, Spring Boot, microservices and REST, Apache Kafka, NoSQL, Splunk) maps to chapters like this:

| Requirement | Chapters | Runnable proof |
|---|---|---|
| **Java 8** (lambdas, streams, Optional, CompletableFuture, collections) | [01](01_java8_core.md), [02](02_collections.md), [04](04_concurrency.md) | `01_java8_core/*`, `02_collections/*`, `04_concurrency/*` |
| **Java 11** (and migration from 8, what comes after) | [03](03_java11_and_modern.md), [05](05_jvm_gc_performance.md) | `03_java11_and_modern/*` |
| **Spring / Spring Boot** | [06](06_spring_core.md), [07](07_spring_boot.md), [09](09_spring_data_jpa.md), [10](10_spring_security.md) | `06_*`, `07_*`, `09_*`, `10_*` |
| **Microservices & REST APIs** | [08](08_rest_api.md), [11](11_microservices.md), [16](16_system_design.md) | `08_rest_api/*`, `11_microservices/*` |
| **Apache Kafka**: topics, partitions, consumer groups, offsets, rebalancing, lag, performance, scaling | [12](12_kafka.md) | `12_kafka/01`–`04` |
| **NoSQL**: Couchbase / MongoDB / Cassandra | [13](13_nosql.md) | `13_nosql/*` |
| **Splunk** and observability | [14](14_observability_splunk.md) | `14_observability_splunk/*` |
| Testing, design quality, production support | [15](15_testing.md), [17](17_design_patterns.md), [18](18_production_troubleshooting.md) | `15_*`, `17_*`, `18_*` |

## The chapters

| # | Document | Runnable examples |
|---|---|---|
| 01 | [Java 8 core: lambdas, streams, Optional, java.time, CompletableFuture](01_java8_core.md) | [01_java8_core/](../examples/01_java8_core) |
| 02 | [Collections: HashMap internals, concurrent collections](02_collections.md) | [02_collections/](../examples/02_collections) |
| 03 | [Java 11 and beyond: features and migration](03_java11_and_modern.md) | [03_java11_and_modern/](../examples/03_java11_and_modern) |
| 04 | [Concurrency and multithreading](04_concurrency.md) | [04_concurrency/](../examples/04_concurrency) |
| 05 | [JVM internals, GC and performance](05_jvm_gc_performance.md) | [05_jvm_gc_performance/](../examples/05_jvm_gc_performance) |
| 06 | [Spring core: IoC, DI, AOP, proxies](06_spring_core.md) | [06_spring_core/](../examples/06_spring_core) |
| 07 | [Spring Boot: auto-configuration, config, Actuator](07_spring_boot.md) | [07_spring_boot/](../examples/07_spring_boot) |
| 08 | [REST API design](08_rest_api.md) | [08_rest_api/](../examples/08_rest_api) |
| 09 | [Spring Data JPA, Hibernate, transactions](09_spring_data_jpa.md) | [09_spring_data_jpa/](../examples/09_spring_data_jpa) |
| 10 | [Spring Security, JWT, OAuth2](10_spring_security.md) | [10_spring_security/](../examples/10_spring_security) |
| 11 | [Microservices: resilience, sagas, outbox](11_microservices.md) | [11_microservices/](../examples/11_microservices) |
| 12 | [Apache Kafka](12_kafka.md) | [12_kafka/](../examples/12_kafka) |
| 13 | [NoSQL: MongoDB, Couchbase, Cassandra](13_nosql.md) | [13_nosql/](../examples/13_nosql) |
| 14 | [Observability and Splunk](14_observability_splunk.md) | [14_observability_splunk/](../examples/14_observability_splunk) |
| 15 | [Testing](15_testing.md) | [15_testing/](../examples/15_testing) |
| 16 | [System design: capacity, caching, zero downtime](16_system_design.md) | [16_system_design/](../examples/16_system_design) |
| 17 | [Design patterns, SOLID, clean architecture](17_design_patterns.md) | [17_design_patterns/](../examples/17_design_patterns) |
| 18 | [Production troubleshooting and RCA](18_production_troubleshooting.md) | [18_production_troubleshooting/](../examples/18_production_troubleshooting) |

## Seven-day plan (highest probability first for this profile)

| Day | Focus | Do |
|---|---|---|
| 1 | Kafka (12) | read the doc, run all four examples, narrate lag/rebalance/partition-key answers aloud |
| 2 | Spring + Boot (06, 07) | run the IoC and AOP examples, then explain "why my `@Transactional` didn't work" |
| 3 | REST + microservices (08, 11) | run the REST server example, then resilience/saga/outbox; practise "downstream is down" |
| 4 | Java 8 + 11 + collections (01, 02, 03) | streams drills, HashMap internals, 8 → 11 migration checklist |
| 5 | Concurrency + JVM (04, 05) | thread pools, deadlock, leak diagnosis |
| 6 | NoSQL + Splunk (13, 14) | data modelling questions, SPL queries, investigate-an-error-spike narration |
| 7 | Mock | Q&A drill: **Mock random 10** with answers hidden; two system-design answers (16) and two incident stories (18) |

## Conventions (the live app depends on them)

- Chapter folders and deep-dive files share the same `NN_name` stem.
- Examples are single-file, JDK-only programs (`java File.java`); Spring/Kafka/DB behaviour is simulated so failure modes are observable.
- Examples print only ASCII (the runner redirects output), start with a header comment (`* NN - Title`, then `Interview angle:`), and number their output with `section("N. Title")` calls.
- Keep numbering **append-only**: links in this folder, the README and the app use it.
