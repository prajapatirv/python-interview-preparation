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

Files 03 and 06–08 target interview feedback received on 2026-10-13: *tuning backend APIs for response time and
throughput, using CPU and memory efficiently, tools to measure performance, tuning Kafka for large-scale traffic.*
