---
id: performance
title: Performance engineering
order: 3
summary: API response time and throughput, CPU and memory efficiency, measuring performance, JVM/GC tuning.
crib: java/java-interview-prep/topics/04-jvm-gc-performance.md
docs: java/java-interview-prep/deep_dive/05_jvm_gc_performance.md, java/java-interview-prep/deep_dive/24_performance_tuning_answers.md, java/java-interview-prep/deep_dive/25_production_monitoring_qa.md
examples: java/java-interview-prep/examples/05_jvm_gc_performance
keywords: performance, tuning, tune, latency, throughput, response time, slow, high cpu, cpu, memory, memory leak, outofmemory, oom, gc, garbage collection, gc pause, g1, zgc, profiling, profiler, jfr, flame graph, jmeter, gatling, load test, load testing, benchmark, jmh, heap dump, thread dump, jstack, jcmd, connection pool, thread pool, hikari, large data, millions of records, millions, tps, rps, p99, percentile
---
Skill focus for Performance engineering answers:
- This is a known weak area for the candidate (interview feedback): be concrete and numeric, never generic.
- Always go symptom -> evidence -> fix: name the measurement (percentiles, flame graph, GC log, pool metrics) before the fix.
- API: Little's Law (concurrency = throughput x latency), the latency knee near 70-80% utilisation, N+1 and indexes, pool sizing, caching and stampedes, parallel downstream calls, async via outbox, virtual threads (Java 21) and their traps.
- CPU/memory: heap vs native memory in containers (MaxRAMPercentage, NMT, OOMKilled vs OutOfMemoryError, CFS throttling), allocation reduction, collector choice (G1 / generational ZGC / Parallel), leaks via heap dump + MAT.
- Tools: RED/USE, Micrometer + Prometheus, OpenTelemetry tracing, JFR + JMC, async-profiler flame graphs, jcmd/jstat, JMH, Gatling/k6/JMeter with an open arrival-rate model (coordinated omission), Splunk perc95/perc99 SPL, SLO burn-rate alerts.
- Kafka tuning lives in the Kafka topic; link to it when the question is about Kafka throughput.
- Quote before/after numbers in every scenario (p99, rps, CPU %, heap size, cost).
