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
| [50_coding_round_problems.md](50_coding_round_problems.md) | Coding round: 31 classic problems, every Java solution compiled and run | 31 |
| [60_round_java_core.md](60_round_java_core.md) | Real round: stream output question, department top earner, HashMap internals | 3 |
| [61_round_spring_boot.md](61_round_spring_boot.md) | Real round: circuit breaker with Resilience4j, conditional beans | 2 |
| [62_round_kafka.md](62_round_kafka.md) | Real round: Kafka architecture, 2 of 10 consumers crash, scaling 1M to 10M records | 3 |
| [63_round_performance.md](63_round_performance.md) | Real round: TPS from 1,000 to 100,000 | 1 |
| [64_round_cloud_devops.md](64_round_cloud_devops.md) | Real round: KEDA and event-driven autoscaling | 1 |
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

Files 03 and 06–08 target interview feedback received on 2026-10-13: *tuning backend APIs for response time and
throughput, using CPU and memory efficiently, tools to measure performance, tuning Kafka for large-scale traffic.*

Files 70–78 are the **Java/J2EE + Gen AI profile pack** (hub: [`../profile-java-genai/README.md`](../profile-java-genai/README.md));
files 80–82 are the **Chase Travel company pack** (hub: [`../company-chase-travel/README.md`](../company-chase-travel/README.md)).
Each answer opens with *The live scenario (functional requirement)*.
