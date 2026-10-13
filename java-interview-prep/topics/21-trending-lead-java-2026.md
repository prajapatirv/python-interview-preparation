---
id: 21-trending-2026
title: Hot & Trending Topics for Lead Java Interviews (2026)
focus: Task 7 - what companies are asking right now, with ready answers
---
Priority order for your interview (most likely first): 1) Java 21/25 + virtual threads, 2) Spring Boot 3.5 -> 4 migration, 3) event-driven design with Kafka (outbox, idempotency, DLQ), 4) resilience + observability (OpenTelemetry, SLOs), 5) system design/RCA stories, 6) cloud/Kubernetes basics, 7) AI-assisted engineering and GenAI integration, 8) security/supply chain. Verify versions before quoting them.

### Q1 [intermediate] What are the biggest Java platform changes a Lead should know in 2026?
Java 25 is the current LTS (Sept 2025). Virtual threads are final (Java 21) and no longer pin on `synchronized` (Java 24). **Scoped Values are final in 25**; Structured Concurrency is still preview; Stream Gatherers (final in 24); records/sealed types/pattern matching are mainstream; faster startup via Leyden/AOT cache; GraalVM native image for serverless.

### Q2 [intermediate] Why is "Spring Boot 3 -> 4" a hot question right now?
Boot 3.5 open-source support ended in June 2026, so many teams must migrate to Boot 4 (Spring Framework 7, Jakarta EE 11, Spring Security 7). Expect "plan the migration": upgrade to latest 3.5 first, clear deprecations, use the migration guide and OpenRewrite, handle modular starters, Jackson 3, test-annotation changes, third-party compatibility, run perf/regression tests, roll out via canary.

### Q3 [intermediate] What new Spring Framework 7 features are interview favourites?
Built-in resilience annotations (`@Retryable`, `@ConcurrencyLimit`), API versioning, JSpecify null safety, `@ImportHttpServices` for declarative HTTP clients, `BeanRegistrar`, `RestTestClient`, Spring Data AOT (faster startup), modular auto-configuration. The best answer connects each feature to a problem it removes (e.g. dropping Resilience4j for simple retry cases).

### Q4 [advanced] Virtual threads in production: what is your adoption playbook?
Enable on Java 21+ (`spring.threads.virtual.enabled=true`), load-test before/after, watch pinning (`-Djdk.tracePinnedThreads`/JFR), limit concurrency to protect DB pools (semaphore/bulkhead), replace `ThreadLocal` heavy code with scoped values where possible, keep CPU-bound work on bounded platform pools, and monitor carrier thread and pool saturation. Not a free win for CPU-bound or lock-heavy code.

### Q5 [advanced] Event-driven architecture: what do interviewers probe?
Outbox + CDC, idempotent consumers, ordering by key, retries/DLQ topics, schema evolution (Avro/Protobuf registry), exactly-once myths, saga orchestration vs choreography, replay/backfill, consumer lag SLOs, and testing with Testcontainers. Kafka 4.0 specifics: KRaft-only, new consumer rebalance protocol, share groups (queues, preview in 4.1).

### Q6 [advanced] Observability with OpenTelemetry and SLOs - what is expected?
Instrument with Micrometer/OTel, propagate `traceparent` through HTTP and Kafka headers, use the Collector to export to any backend, define SLIs/SLOs and burn-rate alerts, correlate logs/metrics/traces by id, control cardinality and cost (sampling), and write runbooks. Spring Boot's observability stack is built around Micrometer Observation.

### Q7 [advanced] Resilience engineering (timeouts, retries, circuit breakers, bulkheads) - expected depth?
Know ordering and when each backfires (retry storms, retries on non-idempotent calls), deadline propagation, fallback design, chaos testing, and capacity limits. Know both Resilience4j and the new Spring Framework 7 core resilience annotations and when to use which.

### Q8 [advanced] GenAI in Java backends: what should a Lead say?
Use **Spring AI** or LangChain4j for model calls, prompt templates, structured output, RAG (embeddings + vector store such as pgvector/OpenSearch), tool calling, and MCP integration. Design concerns: latency and cost, caching, streaming responses, evaluation and guardrails, PII redaction, rate limits and fallbacks, observability of prompts/tokens, and keeping the model behind a port/adapter. Your Bedrock (Claude) and agentic-workflow experience is a strong story.

### Q9 [advanced] How is AI-assisted development changing engineering practice?
Faster scaffolding, tests and refactors; code review assistants; documentation. Lead responsibilities: policy on data/secrets, mandatory human review, tests/security gates unchanged, measure impact (cycle time, defect rate), train juniors to verify not just accept, avoid skill atrophy, and standardise prompts/context files (e.g. repo conventions).

### Q10 [advanced] Modular monolith vs microservices - what is the 2026 stance?
Many companies are moving back toward **modular monoliths** (Spring Modulith) for cost and simplicity, using microservices only where independent scaling/ownership is real. Be ready with a decision framework and a story of consolidating or splitting a service.

### Q11 [intermediate] Platform engineering and "golden paths" - what is it?
An internal developer platform provides templates, pipelines, observability, security defaults and self-service infra so product teams ship faster. As a Lead you contribute service templates, shared starters and docs. Tools: Backstage, Crossplane, Terraform modules, Argo CD.

### Q12 [intermediate] Software supply-chain security - what questions come up?
SBOM (CycloneDX/SPDX), dependency scanning, signed artifacts (cosign), SLSA provenance, pinning, private registries, secret scanning, least-privilege CI (OIDC), CVE patch SLAs, and regulatory drivers (e.g. EU Cyber Resilience Act). Mention how you track EOL (Java 8, Boot 2/3).

### Q13 [intermediate] Zero-trust and API security in microservices?
mTLS between services (mesh), short-lived tokens, OAuth2/OIDC at the edge and re-validation inside, authorization per object, secrets in vaults, policy-as-code, audit logs, rate limiting, and input validation. Know OWASP API Top 10.

### Q14 [intermediate] Cloud cost (FinOps) as an engineering concern?
Right-sizing, autoscaling, spot instances, storage tiering, log/metric cost control, efficient runtimes (virtual threads, native image for serverless), cost allocation tags, and cost dashboards per team. Interviewers like candidates who quote concrete savings.

### Q15 [intermediate] Kubernetes expectations for a Java Lead?
Probes, requests/limits tuned for JVM, HPA/KEDA by lag, graceful shutdown, PDBs, config/secrets, Helm/Kustomize, GitOps (Argo CD), basic troubleshooting (CrashLoop, OOMKilled, Pending), and awareness of OpenShift differences (Routes, SCC non-root).

### Q16 [intermediate] Data and caching trends interviewers raise?
CDC with Debezium, outbox, lakehouse/analytics offload, Redis/Caffeine caching strategies, polyglot persistence (Postgres + search + cache), vector databases for AI features, and consistency trade-offs in multi-region setups.

### Q17 [advanced] Performance and cost efficiency: JVM startup/footprint techniques?
AppCDS/AOT cache (Leyden), Spring AOT + native image for short-lived workloads, `MaxRAMPercentage` and G1/ZGC tuning, lazy initialisation, removing unused starters, virtual threads to avoid oversized pools, and profiling with JFR before tuning.

### Q18 [advanced] Testing trends: what is "expected" now?
Testcontainers for all external dependencies, contract tests, mutation testing, property-based testing (jqwik), ArchUnit, performance tests in CI, and AI-assisted test generation reviewed by humans. Boot 4 introduces `RestTestClient`.

### Q19 [design] A common 2026 design question: "Design an AI-assisted support/ops assistant for an enterprise platform."
Gateway service in Spring Boot calling an LLM (Bedrock/Azure OpenAI) via a port; retrieval from runbooks/tickets (vector store + keyword search); tool calling to read-only ops APIs; guardrails (PII masking, allow-listed tools, human approval for actions); caching and rate limits; async processing for long tasks; audit log of prompts/responses; evaluation sets and feedback loop; metrics for latency, cost per request, answer quality.

### Q20 [design] "Design a high-throughput event pipeline with exactly-once-like behaviour and replay."
Kafka topics keyed by entity, producers with idempotence, outbox from the source DB, consumers with idempotent upserts and offset commit after DB commit, DLT + replay tool, schema registry with compatibility checks, lag/error SLOs, backfill by reading from a retained topic or compacted topic, and capacity planning by partitions.

### Q21 [intermediate] Interview day checklist for a Lead Java role.
Prepare 6 stories (incident, conflict, mentoring, migration, failure, improvement); two system designs you can draw (file ingestion pipeline, order saga); a 2-minute explanation of each project on your resume; honest "gap" answers for NoSQL, Azure, OpenShift, Splunk/Grafana/Prometheus, each paired with your nearest equivalent; and 5 questions to ask them.

### Q22 [design] Design the guard rails for using AI coding assistants across a 30-engineer team.
Define what data may leave the company (no secrets, customer data or proprietary code unless an approved enterprise tool), require human review and the same test and quality gates for generated code, track licensing and provenance concerns, and measure outcomes (cycle time, defect rate), not usage. Add training on prompt hygiene and verification. Trade-off: speed gains versus subtle defects and skill atrophy - keep code review and design ownership human. Failure mode: unreviewed generated code merged because the tests it wrote also pass.
