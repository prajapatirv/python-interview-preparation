# 04 - AWS S3, ECS and Aurora PostgreSQL (Basic to Advanced)

**Architecture to keep in mind:** Spring Boot services in containers on **ECS (Fargate)** behind an **ALB**, using **Aurora PostgreSQL** for data and **S3** for documents/files, with IAM roles, Secrets Manager, CloudWatch and Kafka/MSK around them.

> **How to use this document:** answer in the order "what it is -> why we use it -> how it fails -> how we secured/monitored it". Travel examples are illustrative; replace them with real facts from your project.

---

## Part 1 - Basic (Q1-Q10)

### Q1 [basic] What is Amazon S3?
Durable object storage: you store objects (files + metadata) in buckets and address them by key. It scales without capacity planning and is designed for 99.999999999% (11 nines) durability. Typical uses: documents (itineraries, receipts, passports scans), file ingestion, backups, static assets, data lake. S3 now gives strong read-after-write consistency for objects.

### Q2 [basic] Name the S3 storage classes and when you use them.
Standard (frequently accessed), Intelligent-Tiering (unknown/changing access, automatic tiering), Standard-IA and One Zone-IA (infrequent access), Glacier Instant/Flexible/Deep Archive (archive, cheaper but slower or with retrieval fees). Use lifecycle rules to move or expire objects automatically.

### Q3 [basic] How do you secure an S3 bucket?
Block Public Access on, bucket policy/IAM least privilege, encryption at rest (SSE-S3 or SSE-KMS), TLS only (`aws:SecureTransport` condition), versioning for recovery, access logging/CloudTrail data events, and VPC endpoints so traffic stays inside AWS. Applications use IAM roles, not access keys.

### Q4 [basic] What is ECS and what are its main concepts?
Elastic Container Service runs containers. **Cluster** (logical group), **Task definition** (blueprint: image, CPU/memory, ports, env vars, roles, logging), **Task** (running instance), **Service** (keeps N tasks running, integrates with the load balancer, handles rolling deployments). **ECR** stores the images.

### Q5 [basic] Fargate vs EC2 launch type?
Fargate is serverless for containers: you pay per task CPU/memory and AWS manages the servers (no patching). EC2 launch type means you manage the instances (more control, GPU, cost optimisation at large steady scale). Most teams start with Fargate.

### Q6 [basic] Task role vs task execution role in ECS?
**Execution role**: used by ECS itself to pull the image from ECR, write logs to CloudWatch and fetch secrets for injection. **Task role**: used by your application code to call AWS APIs (read S3, send to MSK, get a DB token). Mixing them up is a classic mistake.

### Q7 [basic] What is Amazon Aurora PostgreSQL?
A MySQL/PostgreSQL-compatible managed relational database with a distributed storage layer: data is stored in 6 copies across 3 Availability Zones, storage grows automatically (up to 128 TiB), and you can add up to 15 read replicas. It is PostgreSQL wire-compatible, so Spring Boot and the standard driver work.

### Q8 [basic] Aurora vs standard RDS PostgreSQL?
Aurora separates compute and storage, which gives faster failover and replica creation, shared storage for replicas (low replica lag), automatic storage growth and more built-in features (Global Database, Serverless v2). RDS PostgreSQL uses per-instance EBS storage and is simpler and often cheaper for small workloads.

### Q9 [basic] What are the Aurora endpoints?
**Cluster (writer) endpoint**: always points to the current writer. **Reader endpoint**: load-balances connections across replicas. **Instance endpoints**: a specific instance (avoid in apps because they break on failover). Spring Boot uses the cluster endpoint for writes and the reader endpoint for read-only queries.

### Q10 [basic] How does an ECS service connect to Aurora securely?
Run tasks and Aurora in private subnets of the same VPC. The Aurora security group allows port 5432 only from the ECS tasks' security group. Credentials come from Secrets Manager (injected via the task definition) or IAM authentication. Database is not publicly accessible; TLS is enabled.

**Project hook (Part 1):** "Our services run as Fargate tasks behind an ALB; the task role reads S3 and the DB credentials come from Secrets Manager; Aurora is reachable only from the service security group."

---

## Part 2 - Mid Level (Q11-Q20)

### Q11 [mid] What are pre-signed URLs and when do you use them?
A time-limited URL that lets a client upload or download a specific S3 object without AWS credentials. The API authorises the user, then returns a pre-signed URL; the browser talks to S3 directly, so large files do not pass through your service. Keep expiry short (minutes), restrict the key, content type and size, and validate the upload afterwards (virus scan, size/type check).

### Q12 [mid] How do you upload very large files to S3?
Use **multipart upload**: split into parts (5 MiB to 5 GiB each, up to 10,000 parts; objects up to 5 TiB), upload parts in parallel, retry only failed parts, then complete. Use the AWS SDK Transfer Manager (or S3 async client) and a lifecycle rule to abort incomplete multipart uploads. Recommended above roughly 100 MB; a single PUT is limited to 5 GB.

### Q13 [mid] Encryption options in S3?
SSE-S3 (AWS-managed keys), SSE-KMS (your KMS key, audit trail in CloudTrail, per-key access control, but KMS request limits/costs), SSE-C (you supply keys), and client-side encryption. For regulated data use SSE-KMS with a customer-managed key and a bucket policy that denies unencrypted uploads.

### Q14 [mid] How do you trigger processing when a file lands in S3?
S3 Event Notifications to SQS/SNS/EventBridge/Lambda. A common pattern: S3 -> SQS -> ECS worker (Spring Boot with Spring Cloud AWS `@SqsListener`) so processing is buffered, retried and scalable. Make processing idempotent (events can repeat), use a DLQ, and store metadata (key, ETag, status) in the database.

### Q15 [mid] How does an ECS service scale?
Service Auto Scaling with target tracking on CPU/memory, ALB request count per target, or custom CloudWatch metrics (for example queue depth or Kafka lag via a custom metric). Set min/max tasks, a cooldown, and ensure the Aurora connection budget (tasks x pool size) can handle the maximum. Spread tasks across AZs.

### Q16 [mid] How do health checks work with ALB and ECS?
The ALB target group probes a path (for example `/actuator/health/readiness`); unhealthy targets receive no traffic and ECS replaces tasks that fail. Set a health check grace period so slow-starting Java tasks are not killed during startup. Container health checks (task definition) are separate from ALB checks. Keep liveness light and independent of downstream systems.

### Q17 [mid] How do you inject configuration and secrets into ECS tasks?
Task definition `environment` for non-secrets and `secrets` referencing Secrets Manager or SSM Parameter Store ARNs; the execution role needs permission to read them. Values arrive as environment variables mapped to Spring properties. Rotation requires a new task or a refresh mechanism (Spring Cloud AWS or restart).

### Q18 [mid] Aurora backups, restore and replicas?
Continuous backup to S3 with point-in-time restore inside the retention window (1-35 days), plus manual snapshots. A restore creates a new cluster. Up to 15 Aurora replicas share the same storage, so lag is typically milliseconds, and any replica can be promoted on failover. Test restore, not only backup.

### Q19 [mid] How do you monitor this stack?
CloudWatch metrics and alarms: ECS CPU/memory, task count, ALB 5xx/target response time/unhealthy hosts; Aurora CPU, `DatabaseConnections`, replica lag, freeable memory, deadlocks; S3 request errors. Logs through the `awslogs` driver (structured JSON). **Performance Insights** for top SQL and wait events, Container Insights for ECS, X-Ray/OpenTelemetry for traces. Alert on user-facing symptoms first.

### Q20 [mid] What is a VPC endpoint and why use one for S3?
A **gateway endpoint** for S3 (and DynamoDB) routes traffic to S3 over the AWS network, not via a NAT gateway or the internet. It improves security (restrict by endpoint policy) and cuts NAT data-processing cost. Interface endpoints (PrivateLink) serve other services such as ECR, Secrets Manager and CloudWatch Logs.

**Project hook (Part 2):** "Large uploads use pre-signed multipart URLs, S3 events go through SQS to an ECS worker, and CloudWatch alarms on ALB 5xx and Aurora connections page the on-call."

---

## Part 3 - Advanced and Design (Q21-Q30)

### Q21 [advanced] Design secure storage and retrieval of customer travel documents (itineraries, receipts, ID scans).
Private bucket with Block Public Access, SSE-KMS with a customer-managed key, versioning and object lock if required, keys structured by tenant/customer/booking, no public URLs. Upload and download through short-lived pre-signed URLs issued after an authorisation check (object-level), antivirus/type scan before the file becomes "available", metadata and access audit in Aurora, lifecycle rules for retention and deletion, CloudTrail data events, cross-region replication for DR if the RTO/RPO needs it, and PII redaction in logs.

### Q22 [advanced] Design zero-downtime deployments for the ECS service.
Rolling update (`minimumHealthyPercent`/`maximumPercent`) with the ECS **deployment circuit breaker** and CloudWatch alarm rollback, or blue/green with CodeDeploy and ALB weighted target groups (canary 10% -> 100%). Requirements: readiness-gated health checks, graceful shutdown (`server.shutdown=graceful`, `stopTimeout` and ALB deregistration delay longer than request time), backward-compatible DB changes (expand/contract), and automated rollback on error-rate or latency alarms.

### Q23 [advanced] Tasks scale out and Aurora starts rejecting connections. What happened and how do you fix it?
Total connections = running tasks x Hikari pool size (plus other clients) exceeded `max_connections` (derived from instance memory). Fix: cap pool size, set autoscaling max tasks consistent with the connection budget, reduce transaction time, add **RDS Proxy** for connection multiplexing, use read replicas for read traffic, and scale the instance class if CPU/memory bound. Add an alarm on `DatabaseConnections` at ~80% of the limit.

### Q24 [advanced] Design for high availability and disaster recovery.
Within a region: tasks across at least 2-3 AZs, ALB across AZs, Aurora writer plus at least one replica in another AZ (failover typically 30-60 seconds), S3 is multi-AZ by design. Cross-region: Aurora Global Database (low-latency replication, promotion in about a minute for DR), S3 Cross-Region Replication, images in ECR replicated, infrastructure as code to recreate the stack, Route 53 failover/health checks. Define RTO/RPO per service, document the runbook, and rehearse failover.

### Q25 [advanced] Aurora failover happens during peak traffic. Describe application impact and mitigation.
Connections to the old writer drop; the cluster endpoint flips to the new writer in roughly 30-60 seconds; in-flight transactions fail. Mitigation: short Hikari `connectionTimeout`, bounded `maxLifetime`, low DNS TTL in the JVM, retry idempotent operations with backoff, circuit breakers so tasks fail fast instead of piling up threads, readiness probe flips so the ALB drains, outbox/idempotency make retries safe, and the AWS Advanced JDBC Wrapper or RDS Proxy speeds up reconnection. Run game days to prove it.

### Q26 [advanced] How do you control cost across S3, ECS and Aurora?
S3: lifecycle to Intelligent-Tiering/IA/Glacier, abort incomplete multipart uploads, expire old versions, VPC gateway endpoint to avoid NAT charges. ECS: right-size CPU/memory from metrics, Fargate Spot for stateless/batch work, Savings Plans for steady load, scale in off-peak. Aurora: right-size instances, replicas only as needed, Serverless v2 for spiky workloads, I/O-Optimized if I/O cost dominates, delete old snapshots. Tag everything and review a monthly cost report.

### Q27 [advanced] Design a file-ingestion pipeline (partner files -> S3 -> parse -> Aurora/Kafka).
Files arrive via SFTP/upload into a landing bucket -> S3 event to SQS -> ECS worker streams the object (no full load in memory), parses by format with a pluggable parser, validates rows, and writes in batches to Aurora with idempotent upserts or publishes events to Kafka -> bad rows to a quarantine prefix with an error report -> status in a `file_ingest` table (RECEIVED, PARSING, DONE, FAILED) -> alerts and a retry endpoint. Handle large files with ranged reads or partitioned processing, checksum de-duplication, DLQ, autoscaling on queue depth, and per-source metrics.

### Q28 [advanced] A task keeps restarting in a loop (exit code 137 / health check failing). How do you troubleshoot?
Check ECS service events and the stopped-task reason, CloudWatch logs, and exit code. 137 = killed (OOM or SIGKILL): compare container memory limit with JVM heap plus non-heap (`-XX:MaxRAMPercentage`, metaspace, threads, direct buffers). Health check failing: grace period too short for Java startup, wrong port/path, security group blocking the ALB, dependency checks inside liveness. Also look for missing secrets/permissions (execution role) and image pull errors (ECR access via NAT or VPC endpoint).

### Q29 [advanced] How do you apply least privilege and compliance controls for a payments-adjacent travel platform?
Separate AWS accounts per environment, IAM roles per service with narrow policies and permission boundaries, no long-lived keys, KMS customer-managed keys with key policies, private networking and security groups per tier, WAF at the ALB, encryption everywhere, centralised logging and CloudTrail, AWS Config and Security Hub for drift/compliance, secrets rotation, vulnerability scanning of images (ECR scan) and dependencies, and tokenised payment data (never store raw card numbers).

### Q30 [advanced] Aurora Serverless v2 vs provisioned, and when would you pick each?
Serverless v2 scales capacity in fine-grained ACU steps with the load, suiting variable or unpredictable traffic and dev/test, and it can mix with provisioned instances in one cluster. Provisioned is predictable and usually cheaper for steady high load (with reserved pricing). Consider minimum capacity (warm buffer cache), scaling speed under sudden spikes, connection limits tied to capacity, and cost per ACU-hour versus a fixed instance.

**Project hook (Part 3):** "When [real incident: connection storm / failed deployment / S3 permission issue] happened, I traced it with [ECS events / CloudWatch / Performance Insights] and fixed it by ..."

---

## Quick revision card
- S3: private, encrypted, pre-signed URLs, multipart for big files, lifecycle rules.
- ECS: task role (app) vs execution role (platform), health-check grace period, circuit-breaker rollback.
- Aurora: cluster endpoint writes, reader endpoint reads, failover ~30-60 s, connections = tasks x pool.
- Scale and failover are tested, not assumed: budget connections, retry idempotent work.
- Secure by default: private subnets, KMS, least-privilege roles, no card data.
