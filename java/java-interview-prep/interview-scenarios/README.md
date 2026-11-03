# Scenario answer banks

Interview answers written the way you speak in the room: **a live production scenario first**, then
the reasoning, trade-offs, monitoring, likely follow-ups and a 60-second spoken version. Minimal code.

Each file's front matter `skill:` attaches it to a topic of the Interview Coach
(`../../../interview-coach/skills/java/`). The format is machine-read — see
`../../../interview-coach/README.md` ("Scenario answer format").

| File | Topic | Questions |
|---|---|---|
| [02_kafka_consumers.md](02_kafka_consumers.md) | Kafka: consumer groups, offsets, rebalancing, lag, scaling | 20 |
| [03_kafka_performance_tuning.md](03_kafka_performance_tuning.md) | Kafka: tuning producers, consumers, brokers and partitions for large-scale traffic | 12 |
| [05_rest_third_party_integration.md](05_rest_third_party_integration.md) | REST: calling third-party APIs and still giving a proper response | 13 |
| [06_api_performance_tuning.md](06_api_performance_tuning.md) | Performance: API response time and throughput | 12 |
| [07_cpu_memory_efficiency.md](07_cpu_memory_efficiency.md) | Performance: using CPU and memory efficiently | 11 |
| [08_performance_measurement_tools.md](08_performance_measurement_tools.md) | Performance: tools and techniques to measure application performance | 10 |
| [09_production_monitoring.md](09_production_monitoring.md) | Production support, monitoring, incident handling and RCA | 12 |
| [10_foundations_performance.md](10_foundations_performance.md) | From the basics: concepts, real story, then the answer (performance) | 6 |
| [11_foundations_kafka.md](11_foundations_kafka.md) | From the basics (Kafka) | 7 |
| [12_foundations_spring_boot.md](12_foundations_spring_boot.md) | From the basics (Spring Boot) | 3 |
| [13_foundations_java_core.md](13_foundations_java_core.md) | From the basics (core Java: immutability, equals/hashCode, HashMap, volatile, exceptions, cohesion/coupling, singleton) | 7 |
| [14_foundations_rest_integration.md](14_foundations_rest_integration.md) | From the basics: aggregating several third-party APIs into one response | 1 |
| [33_aws_basics.md](33_aws_basics.md) | Reported pack: AWS basics, from regions and IAM to deployment and cost | 15 |
| [50_coding_round_problems.md](50_coding_round_problems.md) | Coding round: 31 classic problems, every Java solution compiled and run | 31 |
| [60_round_java_core.md](60_round_java_core.md) | Real round: stream output question, department top earner, HashMap internals | 3 |
| [61_round_spring_boot.md](61_round_spring_boot.md) | Real round: circuit breaker with Resilience4j, conditional beans | 2 |
| [62_round_kafka.md](62_round_kafka.md) | Real round: Kafka architecture, 2 of 10 consumers crash, scaling 1M to 10M records | 3 |
| [63_round_performance.md](63_round_performance.md) | Real round: TPS from 1,000 to 100,000 | 1 |
| [64_round_cloud_devops.md](64_round_cloud_devops.md) | Real round: KEDA and event-driven autoscaling | 1 |
| [66_genai_spring_ai_recipes.md](66_genai_spring_ai_recipes.md) | Reported pack, GenAI: ChatClient, advisors, logging, multiple LLMs, structured output, memory, semantic cache, local models, Responses API, voice, guardrails, fact-checking | 12 |
| [67_genai_rag_vector_databases.md](67_genai_rag_vector_databases.md) | Reported pack, GenAI: vector databases, embeddings, similarity, HNSW, chunking, filters, hybrid search, reranking, HyDE, recall@k, freshness, agentic RAG | 14 |
| [68_genai_agents_mcp_deep_dive.md](68_genai_agents_mcp_deep_dive.md) | Reported pack, GenAI: agent loop, workflow vs agent, planning patterns, tool design, memory, MCP features and the 2026 spec, MCP security, A2A, skills, graphs, Embabel, agent UIs, GraphRAG | 15 |
| [69_genai_fundamentals_40_concepts.md](69_genai_fundamentals_40_concepts.md) | Reported pack, GenAI: 40 fundamentals from tokens and attention to context rot, in 12 answers | 12 |
| [70_profile_core_java.md](70_profile_core_java.md) | Java + GenAI profile 1/9: core Java (functional-requirement framing) | 15 |
| [71_profile_spring_boot.md](71_profile_spring_boot.md) | Java + GenAI profile 2/9: Spring Boot | 15 |
| [72_profile_spring_mvc.md](72_profile_spring_mvc.md) | Java + GenAI profile 3/9: Spring MVC | 15 |
| [73_profile_cloud_microservices.md](73_profile_cloud_microservices.md) | Java + GenAI profile 4/9: cloud microservice architecture | 15 |
| [74_profile_event_driven.md](74_profile_event_driven.md) | Java + GenAI profile 5/9: event-driven architecture | 15 |
| [75_profile_containerization.md](75_profile_containerization.md) | Java + GenAI profile 6/9: containerization (Docker, Kubernetes) | 15 |
| [76_profile_rest_api.md](76_profile_rest_api.md) | Java + GenAI profile 7/9: REST API design | 15 |
| [77_profile_genai_rag_llm.md](77_profile_genai_rag_llm.md) | Java + GenAI profile 8/9: LLM basics, RAG, vector stores, evaluation | 13 |
| [78_profile_genai_agents_mcp.md](78_profile_genai_agents_mcp.md) | Java + GenAI profile 9/9: tool calling, MCP servers, agents, guardrails, LLMOps | 12 |
| [80_company_chase_travel_migration.md](80_company_chase_travel_migration.md) | Company pack (Chase Travel): Java rewrite, upgrade and migration | 15 |
| [81_company_chase_travel_domain.md](81_company_chase_travel_domain.md) | Company pack (Chase Travel): rewards travel platform design | 10 |
| [82_company_chase_travel_brushup_e2e.md](82_company_chase_travel_brushup_e2e.md) | Company pack (Chase Travel): Sujay's brush-up list end to end (REST, Aurora, Kafka, S3/ECS) | 8 |
| [83_company_jpmc_java_core_mid_senior.md](83_company_jpmc_java_core_mid_senior.md) | JPMorgan Chase pack 1/5: core Java and collections (HashMap, equals/hashCode, String, final, exceptions, streams, generics, patterns) | 10 |
| [84_company_jpmc_concurrency_jvm.md](84_company_jpmc_concurrency_jvm.md) | JPMorgan Chase pack 2/5: locks, volatile, ConcurrentHashMap, pools, CompletableFuture, deadlock, virtual threads, JVM memory, GC, distributed concurrency, code review | 11 |
| [85_company_jpmc_spring_boot_data_rest.md](85_company_jpmc_spring_boot_data_rest.md) | JPMorgan Chase pack 3/5: student filter API, auto-config, DI, @Transactional, N+1, ACID/locking, errors, security, idempotency, resilience, config, testing | 12 |
| [86_company_jpmc_microservices_kafka_design.md](86_company_jpmc_microservices_kafka_design.md) | JPMorgan Chase pack 4/5: Kafka ordering, no loss/no duplicates, lag, DLT, saga, rate limiter, document upload, observability, 10x scaling, monolith split | 10 |
| [87_company_jpmc_java_11_to_27.md](87_company_jpmc_java_11_to_27.md) | JPMorgan Chase pack 5/5: Java 11 to 27 version map and differences, Java 21/25/26/27 features, LTS policy, upgrades, GC evolution, Java vs Kotlin/Scala/Go | 11 |
| [88_reported_database_rounds.md](88_reported_database_rounds.md) | Reported rounds: MVCC in PostgreSQL vs MySQL, cascade and orphan removal, database locking, SQL vs NoSQL for money | 4 |
| [89_reported_production_kafka_design.md](89_reported_production_kafka_design.md) | Reported rounds: Kafka fraud platform, millions of events in Spring Boot, hangs, pool exhaustion, GitHub rules, secrets in logs | 6 |
| [90_target_nagarro_system_design.md](90_target_nagarro_system_design.md) | Target company, Nagarro 1/3: URL shortener, chat, checkout, CAP, load balancing/failover, notifications, clickstream pipeline, security | 8 |
| [91_target_nagarro_backend_spring.md](91_target_nagarro_backend_spring.md) | Target company, Nagarro 2/3: REST vs gRPC, indexing, transactions, payment idempotency, consistency, auto-config, caching, gateway, Kafka, Java 8 streams | 10 |
| [92_target_nagarro_behavioural.md](92_target_nagarro_behavioural.md) | Target company, Nagarro 3/3: STAR stories: client delivery, conflict, why Nagarro, deadlines, learning, production issue | 6 |
| [93_target_persistent_java_spring.md](93_target_persistent_java_spring.md) | Target company, Persistent Systems: wrappers, functional interfaces, map/flatMap, singleton, odd/even threads, error handling, two databases, scheduler, circuit breaker, microservices, OAuth | 11 |
| [94_target_epam_java_engineering.md](94_target_epam_java_engineering.md) | Target company, EPAM Systems: iterators, hashing, live coding (substring, ranges, tree path), SOLID, TDD, CompletableFuture, Kafka groups/DLQ, Spring Security, architecture walkthrough | 11 |
| [95_reported_streams_coding.md](95_reported_streams_coding.md) | Reported rounds, streams: 20 coding drills, all run on data with ties and nulls | 20 |
| [96_reported_streams_concepts.md](96_reported_streams_concepts.md) | Reported rounds, streams: 15 concept questions | 15 |
| [97_reported_core_java_senior.md](97_reported_core_java_senior.md) | Reported rounds: proxies, custom Collector, lock choice, language features, shared HashMap, all-requests timeout, concurrency failures, threads | 9 |
| [98_reported_spring_backend_rounds.md](98_reported_spring_backend_rounds.md) | Reported rounds: coins, nearest pair, month grouping, controller, JUnit void and static, composite keys, OAuth/JWT, immutable class, rate limiter keys, Redis vs local, WebSocket, SonarQube, discovery, Java 17, Boot 1 to 4, why Spring Boot | 20 |
| [99_reported_api_design_patterns.md](99_reported_api_design_patterns.md) | Reported rounds: 12 API patterns as one design, consistent errors, lost updates with ETags | 3 |

Files 03 and 06–08 target interview feedback received on 2026-10-13: *tuning backend APIs for response time and
throughput, using CPU and memory efficiently, tools to measure performance, tuning Kafka for large-scale traffic.*

Files 70–78 are the **Java/J2EE + Gen AI profile pack** (hub: [`../profile-java-genai/README.md`](../profile-java-genai/README.md));
files 80–82 are the **Chase Travel company pack** and files 83–87 the **JPMorgan Chase Java mid/senior pack**
(hub for both: [`../company-chase-travel/README.md`](../company-chase-travel/README.md)). Files 83–87 give every answer
twice: a 120-second point-by-point version (*How I answer it*) and a *60-second answer*.
Each answer opens with *The live scenario (functional requirement)*.

Files 90–94 are the **target-company section** for Nagarro, Persistent Systems and EPAM Systems
(hub: [`../target-companies/README.md`](../target-companies/README.md)): rounds, reported questions mapped to answers,
prep plans and sources. Every question is tagged with the company name.

Files 33, 66–69, 88–89 and 95–99 are the **reported interview questions and GenAI study pack**
(hub: [`../reported-interviews/README.md`](../reported-interviews/README.md)): real reported questions mapped to answers,
popular GenAI material, a table of corrections to that material, and known gaps.
