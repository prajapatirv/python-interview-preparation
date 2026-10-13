---
id: 19-resume-stack
title: Resume Tech-Stack Deep Dive (Quarkus, Dropwizard, Spring Batch, RabbitMQ, OpenSearch, AWS)
focus: Questions an interviewer asks about technologies listed on a Java lead's resume (Python/Groovy/Grails excluded)
deep_dive: 11,12
examples: 11_microservices,12_kafka
---
Interviewers pick 2-3 resume items and drill down. For each, prepare: what the system did, your decision, a trade-off, a number, and a failure you handled. Replace placeholders in answers with your real figures.

### Q1 [basic] Quarkus vs Spring Boot - why would you choose Quarkus?
Quarkus does work at **build time** (CDI wiring, config, reflection hints) so it starts fast with low memory and supports native images well; it has live coding dev mode, a Dev Services feature (auto-starts DB/Kafka containers) and a Spring-compat layer. Spring Boot has the bigger ecosystem and hiring pool. Quarkus fits CLI tools, serverless and many small services; use what the team can support.

### Q2 [intermediate] How does Quarkus DI differ from Spring?
Quarkus uses **ArC**, a build-time CDI-lite implementation (`@ApplicationScoped`, `@Inject`, `@Produces`); beans are resolved at build time, no runtime classpath scanning or reflection-heavy proxying. Config via `application.properties` and MicroProfile Config (`@ConfigProperty`). Unused beans are removed at build.

### Q3 [intermediate] What is Picocli and why did you use it for parsers?
A Java library for building command-line tools with annotations (`@Command`, `@Option`, `@Parameters`), generating help, validation, subcommands and shell completion; the Quarkus Picocli extension integrates DI and can build a native executable. Good for batch utilities: each parser runs as `parse --format csv --input file --output out.json`, easy to run in Airflow/ECS/Lambda or locally.

### Q4 [intermediate] How did you design the multi-format file parsers (CSV, XLS/XLSX, XML, PDF, ZIP -> standard JSON)?
Strategy per format behind one `Parser` interface; streaming readers (SAX/StAX for XML, streaming CSV, Apache POI streaming reader for big XLSX, PDFBox for text extraction) to bound memory; ZIP handled by iterating entries and delegating by extension; court-specific mapping config to the canonical JSON schema; validation + a quarantine path for malformed rows; unit tests with sample files per court. Mention numbers (files/day, max size).
> Follow-up: how do you avoid zip bombs (limit entries, size, nesting)?

### Q5 [intermediate] How did you handle very large file uploads to S3?
Use **multipart upload** (parts of 8-100 MB uploaded in parallel, retry a failed part, complete at the end; abort incomplete uploads with a lifecycle rule), a transfer manager/async client, streaming from source so memory stays flat, checksum verification, and pre-signed URLs when clients upload directly. Track progress and make the step idempotent (same key + checksum).

### Q6 [intermediate] Explain the end-to-end data-acquisition workflow architecture.
Sources (SFTP/FTP, email attachments/links, portals, physical media) -> ingestion -> S3 landing -> orchestrated by an Airflow DAG (MWAA) with retries/SLAs -> court-specific parser (Java/Quarkus) -> canonical JSON -> database or Kafka for downstream consumers -> SES notifications on success/failure -> audit and replay. Be ready to draw it and to say where it can fail and how it recovers.

### Q7 [intermediate] Why Airflow for orchestration, and what are its limits for a Java engineer?
DAGs give scheduling, dependency management, retries, backfills, visibility and alerting without custom code. Limits: not a streaming engine, task latency overhead, DAG code is Python (Java parsers run as containers/CLI/Lambda tasks). Keep tasks idempotent and small; pass references (S3 keys), not data, between tasks.

### Q8 [intermediate] How do you send notifications with SES and avoid problems?
SES for transactional email (success/failure alerts): verified identities (SPF/DKIM/DMARC), sandbox limits, bounce/complaint handling through SNS, rate limits, templated messages, retries with backoff, and alert aggregation to avoid noise. For incident alerting also route to Slack/PagerDuty.

### Q9 [intermediate] What is Dropwizard and how is it different from Spring Boot?
An opinionated Java framework bundling Jetty, Jersey (JAX-RS), Jackson, Hibernate Validator, metrics, health checks and Logback with a YAML config class and a simple `Application`/`Resource` model. Lightweight and explicit (little "magic"), fast to understand; smaller ecosystem than Spring. You ran Dropwizard 4.0.10 at Cvent: be ready to talk about `Managed` lifecycle, health checks, bundles, Jersey filters and metrics.

### Q10 [intermediate] How did you do the Elasticsearch -> OpenSearch migration?
OpenSearch is the AWS-led fork of Elasticsearch 7.10. Steps: check client compatibility (switch to the OpenSearch Java client or REST client), verify mappings/analyzers and queries, test plugins, snapshot/restore or reindex into the new domain, run dual-write or shadow reads and compare results, cut over, monitor latency and relevance, keep rollback. Risks: version-specific APIs, auth changes (IAM/fine-grained access), index lifecycle policies.

### Q11 [intermediate] How do you design search with OpenSearch/Elasticsearch in a Java service?
Source-of-truth DB + an index populated by events/CDC; explicit mappings (keyword vs text), analyzers, aliases for zero-downtime reindex, pagination with `search_after`, bulk indexing with backoff, circuit breaker around searches, and a rebuild job. Search is eventually consistent.

### Q12 [intermediate] RabbitMQ in your projects - how did you use it reliably?
Durable exchanges/queues, persistent messages, publisher confirms, manual acks after processing, prefetch tuning, dead-letter exchange with retry delay queues, idempotent consumers, and monitoring queue depth/consumer count. Compare honestly with Kafka (see the Kafka topic).

### Q13 [intermediate] Spring Batch - chunk processing, restart and scaling?
Job -> Steps; a chunk step reads N items, processes, writes in one transaction (`chunk(100)`); `JobRepository` stores execution state so a failed job **restarts** from the last committed chunk; skip/retry policies, listeners, partitioning and remote chunking for scale; idempotent writers; Spring Batch 5/6 uses `JobBuilder`/`StepBuilder` (no `JobBuilderFactory`). You used 3.0 for batch submission to a vendor REST service - describe retries and status polling.

### Q14 [intermediate] How did you handle submitting files in batches to a third-party REST service and tracking status?
Batch table with parent/child batch status, submit in controlled batch size with timeouts and retries, store vendor correlation ids, scheduled poller (Spring Batch/Scheduler) updates status, dashboard reads from DB, failures flagged for resubmission, idempotent submit to avoid duplicates, audit logs of requests/responses.

### Q15 [intermediate] Maven build and dependency upgrade work (ConfStrMig) - what did you handle?
Parent POM/BOM alignment, dependency convergence (`mvn dependency:tree`, enforcer plugin), upgrading vulnerable versions, plugin upgrades, removing duplicates, reproducible builds, profiles, multi-module layout, faster CI with caching. Story: the biggest risk you hit and how tests protected the upgrade.

### Q16 [intermediate] API key rotation - how do you do it without downtime?
Support **two valid keys** during a window (old + new), distribute the new key via a secret store, roll clients gradually, monitor usage per key, then revoke the old key; automate expiry alerts and rotation schedule; audit every use. Never hard-code keys; reload without restart.

### Q17 [intermediate] Logging improvement work - what did you change?
Structured JSON logging, correlation ids via MDC, consistent levels, removal of noisy/PII logs, log aggregation with searchable fields, and metrics for the key events. Show before/after impact (search time, incident time-to-diagnose).

### Q18 [intermediate] Multi-tenant / "DB sharding" work in the ERP (CBOS).
For 30+ clients: per-tenant data separation (shared schema with tenant id or separate DBs), routing by tenant at connection level (routing DataSource), per-tenant migrations, noisy-neighbour control, and tenant-aware backups. Describe how you maintained the sharding module and any incident.

### Q19 [intermediate] OSGi/iDempiere - what should you say?
Only claim what you know: OSGi gives modular bundles with their own classloaders and lifecycle; iDempiere is an OSGi-based open-source ERP; you built warehouse/manufacturing/signature modules as plug-ins. If probed on OSGi internals, say it was a legacy platform and pivot to modular design lessons.

### Q20 [intermediate] How are you using Claude via Amazon Bedrock and Amazon Q in engineering?
Integrated Claude (through Bedrock) across Bitbucket repositories for code review/insights and used Amazon Q for generation, reviews and explanations. Talk about guardrails (data stays in AWS, human review, tests/security still gate merges), productivity metrics, and prompt standards for the team.

### Q21 [design] Redesign the data-acquisition pipeline to handle 10x volume and add Azure support.
Make ingestion event-driven (object-created events), parsers as stateless containers autoscaled by queue depth, Kafka (or Event Hubs on Azure) between parse and sink, idempotent upserts, per-source backpressure and quotas, metadata in a relational DB, orchestrations in Airflow/Durable Functions, IaC for both clouds, and observability with OpenTelemetry. Show the trade-offs and migration path.

### Q22 [design] Describe the agentic infrastructure workflow from your hackathon (Ops Master Agent) as an architecture.
Seven-stage workflow: plain-English request -> LLM (Claude on Bedrock) plans -> Terraform generated -> validation + human approval gate -> apply to AWS (ECS Fargate, RDS PostgreSQL, ALB) -> verification checks -> second approval and audit trail. Highlight guardrails: approval gates, least-privilege credentials, plan-before-apply, verification, full audit log, rollback.

### Q23 [design] Design how you would present one project from your resume as a story with measurable outcomes.
Use Situation -> Decision -> Trade-off -> Result: the business problem and constraint, the options you compared and why you chose one, what you gave up, and numbers (throughput, latency, cost, incident count, delivery time). Prepare two failure moments and what you changed afterwards, and be clear about your own contribution versus the team's. Failure modes: describing tools instead of decisions, and claiming production experience you cannot defend with details.
