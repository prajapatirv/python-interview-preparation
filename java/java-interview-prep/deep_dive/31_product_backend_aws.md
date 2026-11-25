# AWS backend engineering and project discussion

Questions 172–197 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Trace an asynchronous image-processing job

An S3 upload feeds SQS and a Lambda consumer. A worker finishes generating a thumbnail and times out before deleting its message. The visibility timeout expires and another worker receives it. Derive the output identity from the input object version, make publication idempotent, and record the version processed. Track oldest queue age alongside errors because retries can mask slow progress. Isolate the output prefix to avoid recursive notifications.

## Interview questions and answers

### Q172. EC2 vs ECS vs EKS vs Lambda; when would you choose each?

EC2 gives host and OS control with patching responsibility. ECS schedules containers with AWS-native operations, including Fargate for managed compute. EKS fits teams needing Kubernetes APIs and their ecosystem. Lambda runs event-driven handlers with managed scaling and bounded execution duration. Compare startup latency, utilization and operational ownership against the workload.

### Q173. How does AWS Lambda work? Cold starts, concurrency, timeout and memory settings.

Lambda initializes an execution environment, loads the Java runtime and handler, invokes it and may reuse the environment. Reuse clients across calls while keeping request data local. Cold starts affect tail latency. Memory setting also influences CPU allocation. Bound timeout and downstream concurrency, and measure initialization separately from handler duration.

### Q174. Lambda synchronous vs asynchronous invocation; retries and DLQ / destinations.

For direct synchronous calls the caller receives the result and decides whether to retry. Asynchronous invocation queues the event and Lambda normally retries function errors up to two additional times. Configure event age, attempts and a failure destination or DLQ. SQS event-source mappings instead follow queue visibility and redrive settings. Make each handler replay-safe. [AWS invocation retries](https://docs.aws.amazon.com/lambda/latest/dg/invocation-retries.html)

### Q175. How do you deploy a Spring Boot service on EC2, ECS or EKS?

Build and test one immutable version. On EC2 run the JAR under a supervised service or bake an image and roll an autoscaling group. On ECS deploy a task-definition revision pointing to the image digest. On EKS update a Deployment behind a Service. Inject configuration and workload identity, pass readiness checks, drain old traffic and retain the prior version.

### Q176. Docker image layers, multi-stage builds, health checks and container resource limits.

Docker caches filesystem layers, so separating dependencies from frequently changing app code improves rebuilds. A multi-stage build copies only runtime artifacts into the final image. Set CPU and memory limits and leave headroom beyond JVM heap for metaspace, stacks and native buffers. Separate liveness from readiness so a slow dependency cannot trigger a restart storm.

### Q177. How does Kubernetes manage pods, deployments, services, ingress and autoscaling?

A Pod runs one or more colocated containers. A Deployment reconciles replica sets and rolling updates. A Service supplies a stable address over ready pods. An Ingress with a controller routes external HTTP traffic. HPA adjusts replica counts from metrics; scaling pods still needs node capacity and a dependency able to absorb the added load.

### Q178. Blue-green vs canary vs rolling deployment; rollback strategy.

Blue-green keeps two environments and switches traffic quickly at extra capacity cost. Canary sends a subset to the new version and compares health. Rolling gradually replaces old replicas. Choose rollback thresholds on errors and tail latency, and retain compatible schema and event formats because old and new processes may overlap or resume after rollback.

### Q179. S3 storage classes, versioning, lifecycle policies, encryption and pre-signed URLs.

Choose S3 storage class from access frequency, retrieval delay and cost. Versioning preserves earlier object versions and lifecycle rules transition or expire versions. Use server-side encryption with appropriate key permissions. A pre-signed URL delegates a specific operation for bounded time under the signer's permissions. Treat it as a bearer credential and scope key and lifetime tightly.

### Q180. S3 event notifications; avoiding duplicate event processing.

S3 notifications can repeat and arrive out of order. Identify the object by bucket, key and version where available, and use event type plus sequencer where appropriate for same-key events. Claim work conditionally and couple completion with the durable effect or an idempotent sink. Avoid triggering the same pipeline on its own output prefix.

### Q181. RDS vs DynamoDB; relational vs NoSQL data modeling.

RDS fits relational constraints, joins and transactions with relatively flexible queries. DynamoDB fits known key-based access patterns at distributed scale. Model an order history around customer key and time-ordered sort key if the dominant query is recent customer orders. Price the secondary indexes and write amplification needed for other views.

### Q182. DynamoDB partition key, sort key, GSI, LSI, hot partitions and capacity modes.

Partition key determines distribution, while a sort key orders items within that key. A GSI permits an alternate partition and sort key with eventual reads. An LSI retains the table partition key with a different sort key and is defined at creation. Provisioned and on-demand modes change capacity management. Neither cures an extremely skewed partition key.

### Q183. DynamoDB conditional writes, transactions, TTL and optimistic locking.

A conditional update such as version=expected atomically rejects a stale write while incrementing the version on success. A transaction can coordinate multiple item checks and mutations at higher cost. TTL deletion is asynchronous, so filter expired items or test expiry during critical operations. Use conditional creation for a deduplication record.

### Q184. SQS Standard vs FIFO; visibility timeout, long polling, DLQ and redrive.

Standard queues favor throughput with possible duplicates and best-effort order. FIFO orders within each message group and deduplicates sends within a bounded window. A received message becomes temporarily invisible and must be deleted after success. Extend visibility for long jobs, use long polling to reduce empty polls, and redrive DLQ messages after resolving the cause.

### Q185. SNS vs SQS; fan-out pattern; SNS to SQS subscription.

SNS pushes a publication to subscribers. SQS buffers work for consumers that pull at their own pace. Subscribe separate queues for billing and analytics to one order topic, grant the topic permission to send to each queue, and use filters for selective delivery. Each team can retry and drain its backlog independently.

### Q186. EventBridge vs SNS vs SQS; event-driven architecture use cases.

EventBridge routes structured events with content-based rules across sources and targets. SNS suits straightforward push fan-out. SQS supplies durable work buffering and backpressure. For an order-created integration, route matching events through EventBridge to a fulfillment queue, then let workers scale to the backlog. Define schema ownership and failure destinations.

### Q187. Kinesis vs Kafka; shards, ordering and consumer scaling.

Kinesis Data Streams uses shards and partition keys, while Kafka uses partitions and offsets. Consumers checkpoint progress and can replay within retention. Key choice controls ordering and hot spots. Compare managed integration, retention, client ecosystem and consumer throughput. More consumers in one Kafka group cannot increase active partition readers beyond partition count.

### Q188. IAM users, roles, policies and least-privilege access; role assumption.

IAM users are long-lived identities. Roles provide temporary credentials through an assumption flow controlled by a trust policy. Permissions policies scope allowed actions, resources and conditions. Give a task role read access only to the required object prefix, and keep deployment permissions on a separate role. Evaluate explicit denies and resource policies when debugging.

### Q189. Secrets Manager vs SSM Parameter Store vs KMS.

Secrets Manager stores secrets with versioning and rotation workflows. Parameter Store handles hierarchical configuration and SecureString parameters. KMS manages encryption keys and cryptographic operations. A Spring service can fetch a secret with workload credentials, use KMS-backed decryption where permitted and cache briefly while supporting rotation.

### Q190. How does envelope encryption work? Encrypting data in S3 and RDS.

Envelope encryption uses a data key to encrypt the payload and a KMS key to wrap the data key. Store the encrypted data key with ciphertext and restrict decryption permissions. S3 SSE-KMS and RDS encryption manage this integration for their respective storage. Plan key access for restore and recovery as well as normal reads.

### Q191. VPC, public/private subnets, route tables, NAT Gateway and Security Groups.

A VPC contains subnets and route tables. A public subnet has a route to an internet gateway; a workload also needs suitable addressing and permissions for direct internet access. Private workloads can reach external IPv4 endpoints through a NAT gateway without accepting unsolicited inbound connections. Stateful security groups restrict traffic, for example allowing DB ingress only from the app group.

### Q192. ALB vs NLB; health checks and target groups.

ALB routes HTTP traffic by application-level attributes such as host and path. NLB handles transport-level flows such as TCP and UDP and suits workloads needing static addresses or non-HTTP protocols. Register backends in target groups and configure health checks that reflect ability to serve. Drain connections before terminating a healthy target.

### Q193. CloudWatch Logs, Metrics, Alarms and dashboards; custom application metrics.

CloudWatch Logs stores diagnostic events, Metrics stores time series, Alarms evaluate thresholds or anomaly conditions and dashboards display trends. Publish request count, failure count and duration distributions by bounded dimensions such as route and environment. Keep request IDs in logs. Alert on user-facing symptoms and use resource saturation metrics for diagnosis.

### Q194. CloudTrail vs CloudWatch; tracing with X-Ray / OpenTelemetry.

CloudTrail records AWS API activity, useful for discovering who changed a role before an outage. CloudWatch shows operational logs, metrics and alarms. Distributed traces link request spans across services. Instrument with OpenTelemetry, propagate trace context, and export to a backend such as X-Ray. Sampling affects which individual traces are available.

### Q195. How do you troubleshoot Lambda timeout, throttling, out-of-memory and permission errors?

For timeout inspect duration near the configured limit and trace blocked network or database calls. For throttling compare concurrency against reserved or regional capacity and downstream limits. For OOM compare maximum memory and allocation profiles, including JVM native usage. For permission errors inspect the exact denied action, resource, execution role and any key or resource policy.

### Q196. How do you design a highly available and fault-tolerant backend on AWS?

Start with availability target, recovery time and acceptable data loss. Spread stateless replicas across availability zones behind a load balancer, use multi-AZ database failover and buffer async work durably. Enforce deadlines and replay safety. Test zone loss and restore backups. Cross-region recovery requires an explicit data replication, routing and failback plan.

### Q197. How do you manage infrastructure using CloudFormation or CDK and deploy through CI/CD?

CloudFormation reconciles declared resources as stacks. CDK synthesizes constructs into CloudFormation templates. In CI validate and synthesize, review a change set for replacement or deletion, deploy with a constrained role and verify health before promotion. Handle stateful resource retention and backward-compatible migrations explicitly. Detect drift and exercise rollback before a production emergency.

## Senior-level project discussion

These are rehearsal examples. Substitute your own ownership, constraints, measurements and outcomes when answering.

### P1. Walk through one backend service you owned, including APIs, data model, traffic and dependencies.

Start at one request. For an order service, POST /orders accepts a cart and an idempotency key. In one transaction it stores the order, lines and an outbox event. Payment and fulfillment consume events and report state transitions. Explain why the order ID is the aggregate key, which calls are on the latency-critical path, and how a client retrieves pending status. Give measured peak requests per second, p95 and database headroom from your own service. Mark which design decisions you personally owned.

### P2. Describe a production incident, its root cause and permanent fix.

Example: checkout latency rises while CPU stays flat. Traces show requests waiting for database connections and thread samples show a payment call inside an open transaction. Temporarily limit payment concurrency to restore capacity. Move remote work outside the transaction and use a persisted pending state with reconciliation. Prove the cause by injecting a slow dependency under load and comparing pool wait and completion rates before and after the change.

### P3. What performance improvement did you deliver and how did you measure it?

For an order listing, establish request mix, dataset size, query count, warm-up and baseline p95. Trace a page that loads one customer per order, replace repeated round trips with a projection, then rerun the same workload. Inspect the query plan and payload size as well as latency. Describe the trade-off if the endpoint now fetches extra columns. Use measured before/after figures and check correctness for empty pages and repeated customers.

### P4. How did you change a database schema without downtime?

To rename a required column, add a nullable replacement, deploy compatible writers and backfill in bounded, resumable batches. Account for old binaries still writing only the old field. Reconcile mismatches after they retire, switch reads behind a flag and verify invariants. Enforce constraints using the engine's online facilities where available. Remove the old field in a later release after the rollback window.

### P5. Which design decision changed after a scaling or reliability issue?

Example: analytics events were keyed only by tenant to preserve order, and one large tenant saturated a partition. Establish which operations truly require order. If order is per shipment, repartition by shipment ID and version events. Cut over at a known boundary or reconcile overlapping streams. Compare maximum partition lag, end-to-end event age and lost or repeated state transitions. Explain why adding consumers alone could not drain the hot partition.

### P6. How do you review code, mentor engineers and ensure quality across services?

Walk through a concrete review. For a retrying payment consumer, ask the author to trace a crash after charge and before acknowledgment. Pair on an idempotency test, agree on the persistence boundary and let the author implement and explain it. Capture the case in a shared contract suite for other consumers. Describe how you tracked recurrence and review turnaround, and how you would handle disagreement over the additional complexity.
