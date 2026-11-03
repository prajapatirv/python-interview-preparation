---
id: aws-basics
title: AWS basics for backend developers: IAM, EC2, VPC, S3, Lambda, compute choices, load balancers, databases, messaging, monitoring
stack: java
skill: cloud-devops
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). Virtusa's walk-in asked "basic
AWS questions" in two rounds, and this is the answer to that gap. No previous AWS experience is assumed. For more depth on S3,
ECS and Aurora, see `../company-chase-travel/brush-up/04-aws-s3-ecs-aurora-postgres.md`.

Limits quoted here were checked against AWS documentation on 2026-11-04. AWS changes limits and adds options often, so
confirm a number before relying on it in a design. If you haven't used a service, say so, then explain how you'd reason about it.

### Q1 [fresher] What are AWS regions and availability zones? Why do they matter?
tags: aws, region, availability-zone, high-availability, multi-az, aws-basics, reported-rounds

**Start here: the concepts**
- A **region** is a geographic area, such as `ap-south-1` (Mumbai). Data stays in the region you choose unless you move it.
- An **availability zone (AZ)** is one or more separate data centres within a region. AZs in a region are connected by fast private links.

**The live scenario (functional requirement)**
*FR: "The order API must survive a data-centre failure, and Indian customer data must stay in India."* Running every instance in one AZ means one power or network failure takes the service down.

**What the interviewer is really checking**
That you can connect the terms to design choices.

**How I answer it** (120-second answer, point by point)
1. **Choose a region by:** data rules first, then user latency, service availability and price, which all vary by region.
2. **Survive an AZ failure:** run at least two instances across two or more AZs, behind a load balancer that spans them. Use a Multi-AZ database.
3. **Survive a region failure:** that's disaster recovery, which is much more work and cost. Decide from the business's RPO and RTO (bank 73 Q13).
4. **Global and regional services:** IAM is global, while most services, such as EC2, RDS and SQS, are regional. S3 bucket names are globally unique, while each bucket's data lives in one region.

**Trade-offs and what can go wrong**
- Traffic between AZs has a small cost and a little latency, and that's normally a fair price for availability.
- An autoscaling group limited to one subnet is in one AZ, however many instances it has.

**Follow-ups to expect**
- *Edge locations?* -> CloudFront points of presence for caching close to users. They aren't AZs.
- *How many AZs?* -> Two minimum; three is common, because the service keeps more capacity if one fails.

**60-second answer**
"A region is a geographic area and an availability zone is one or more separate data centres inside it. I pick a region based on data rules first, then latency and price. To survive a data-centre failure, I spread instances across at least two AZs behind a load balancer, with a Multi-AZ database. Surviving a whole region's loss is disaster recovery, which costs much more, so I'd decide that from the business's RPO and RTO."

### Q2 [mid] Explain IAM. What's the difference between a user, a role and a policy?
tags: aws, iam, role, policy, least-privilege, sts, temporary-credentials, aws-basics, reported-rounds

**Start here: the concepts**
- **User:** an identity with long-lived credentials.
- **Role:** an identity with no fixed credentials, which gets **temporary** credentials when assumed.
- **Policy:** a JSON document saying what's allowed or denied, on which resources.

**The live scenario (functional requirement)**
*FR: "The order service reads one S3 bucket."* A developer pastes an access key into `application.yml`. It reaches Git, and the key has admin rights, so a leak would expose the entire account.

**What the interviewer is really checking**
Roles over keys, and least privilege. Those two points cover most IAM questions.

**How I answer it** (120-second answer, point by point)

```json
{
  "Effect": "Allow",
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::order-invoices/*"
}
```

1. **Apps use roles,** never access keys: an EC2 instance profile, an ECS task role, a Lambda execution role, or IRSA or EKS Pod Identity on EKS. The AWS SDK picks up the credentials automatically, and they rotate on their own.
2. **Least privilege:** the specific actions and specific resources, not `s3:*` on `*`.
3. **How a decision is made:** everything is denied by default, an allow permits it, and an **explicit deny always wins**.
4. **Two kinds of policy:** identity-based policies attach to a user or role, and resource-based policies attach to a resource, such as an S3 bucket policy.
5. **People:** sign in through IAM Identity Center and SSO, with MFA, rather than as long-lived IAM users. Don't use the root account day to day.
6. **Cross-account:** assume a role in the other account through STS.

**Trade-offs and what can go wrong**
- Over-broad policies are common because they make the error go away. Use IAM Access Analyzer to find what's really used, then tighten.
- `AccessDenied` from a service usually means the task role is wrong. Don't confuse an ECS **task role** (for your code) with its **task execution role** (for pulling the image and reading secrets).

**How I'd monitor it**
CloudTrail for API activity, alerts on root usage and on policy changes, and Access Analyzer findings.

**Follow-ups to expect**
- *What if a key leaks?* -> Deactivate it, rotate it, check CloudTrail for what it did, and remove it from history.

**60-second answer**
"A user has long-lived credentials, a role has none and gets temporary ones when assumed, and a policy is the JSON saying what's allowed on which resources. Applications should always use roles, like an ECS task role, so there are no keys to leak and credentials rotate automatically. I follow least privilege: specific actions on specific resources. By default everything's denied, an allow permits, and an explicit deny always wins. People sign in through SSO with MFA, and the root account stays locked away."

### Q3 [fresher] What is EC2? What are the pricing options and Auto Scaling?
tags: aws, ec2, instance-types, on-demand, spot, savings-plans, auto-scaling, ebs, aws-basics, reported-rounds

**Start here: the concepts**
- **EC2** is a virtual server you rent, and you manage the operating system and everything above it.
- **Auto Scaling group (ASG):** keeps a chosen number of instances running, replaces unhealthy ones, and adds or removes capacity.

**The live scenario (functional requirement)**
*FR: "An API with a daily peak, plus a nightly batch job that can be retried."* Paying on-demand for peak capacity all day wastes money.

**What the interviewer is really checking**
Matching the pricing model to the workload.

**How I answer it** (120-second answer, point by point)

| Pricing | Commitment | Good for |
|---|---|---|
| On-demand | None | Unpredictable or short workloads |
| Savings Plans or Reserved | 1 or 3 years | Steady baseline, at a large discount |
| Spot | None; can be reclaimed with a 2-minute warning | Retryable batch and stateless work |

1. **Instance families:** general purpose (`m`), compute optimised (`c`), memory optimised (`r`). Graviton (`g` suffix) is ARM and often cheaper per unit of work, and Java runs well on it.
2. **Storage:** EBS is a network disk that outlives the instance. Instance store is fast, and its data is lost when the instance stops.
3. **ASG for this FR:** minimum for the quiet period, maximum for the peak, across AZs, with target tracking such as 50% CPU. Add a scheduled scale-up, because a JVM takes time to warm.
4. **Combination:** Savings Plan for the baseline, on-demand for peaks, and Spot for the batch job.
5. **Treat instances as replaceable:** no state on the local disk, and an AMI or container for the setup.

**Trade-offs and what can go wrong**
- Spot isn't for anything that can't be interrupted, unless it can checkpoint.
- CPU-based scaling can miss a service that's really limited by database connections or memory.
- `t` burstable instances run out of CPU credits under sustained load, which looks like a sudden slowdown.

**Follow-ups to expect**
- *Vertical or horizontal?* -> Bank 30 Q21.

**60-second answer**
"EC2 is a rented virtual server, and I manage the OS upward. On-demand has no commitment, Savings Plans give a large discount for steady usage, and Spot is very cheap but can be reclaimed with two minutes' notice, so it suits retryable batch work. An Auto Scaling group keeps instances healthy and scales across AZs, usually using target tracking, with a scheduled scale-up before known peaks, because JVMs need warm-up. I'd cover the baseline with a Savings Plan, peaks on-demand, and batch on Spot."

### Q4 [mid] Explain a VPC: subnets, gateways, security groups and NACLs.
tags: aws, vpc, subnet, nat-gateway, internet-gateway, security-group, nacl, vpc-endpoint, aws-basics, reported-rounds

**Start here: the concepts**
- A **VPC** is your private network in AWS. **Subnets** are ranges inside it, each in one AZ.
- A **public subnet** has a route to an **internet gateway**. A **private subnet** doesn't.

**The live scenario (functional requirement)**
*FR: "Public API, private application servers, and a database nobody can reach from the internet."*

**What the interviewer is really checking**
The standard three-tier layout, and the difference between security groups and NACLs.

**How I answer it** (120-second answer, point by point)

```text
Internet -> Internet Gateway -> ALB (public subnets, 2+ AZs)
                                 -> App tasks (private subnets)
                                      -> Database (private subnets, no internet route)
App tasks -> NAT Gateway (public subnet) -> Internet, for outbound calls only
```

| | Security group | Network ACL |
|---|---|---|
| Applies to | Network interface, such as an instance | Whole subnet |
| Rules | Allow only | Allow and deny |
| State | **Stateful:** replies are allowed automatically | **Stateless:** allow both directions yourself |
| Typical use | The main control | Coarse extra layer, or blocking a range |

1. **Chain security groups by reference:** the database allows port 5432 from the **app's security group**, not from an IP range. It keeps working as IPs change.
2. **NAT gateway:** gives private instances outbound access, and nothing outside can start a connection in.
3. **VPC endpoints:** reach S3, DynamoDB or other services privately, without going through NAT. This improves security, and can cut NAT data charges.
4. **Debugging a timeout:** check in order: route table, security group, NACL, then whether the target is listening. A **timeout** usually suggests network rules, and **connection refused** usually means traffic arrived but nothing is listening.

**Trade-offs and what can go wrong**
- NAT gateways charge for data processed, which can become a surprising bill. Add endpoints for heavy S3 traffic.
- A NACL needs a rule for return traffic on ephemeral ports, which is the classic mistake.
- Use one NAT per AZ, or one AZ's failure can cut outbound traffic for all.

**Follow-ups to expect**
- *Connect two VPCs?* -> Peering, or Transit Gateway for many.

**60-second answer**
"A VPC is my private network, split into subnets per AZ. Public subnets route to an internet gateway, and private ones don't. The standard layout is a load balancer in public subnets, and application and database in private ones, with a NAT gateway for outbound-only access. Security groups are stateful, allow-only, and attach to instances. NACLs are stateless, and work at the subnet level. I chain security groups, so the database accepts traffic only from the app's group, and I use VPC endpoints for S3 to stay private and reduce NAT charges."

### Q5 [fresher] What is S3? What are its consistency model and storage classes?
tags: aws, s3, object-storage, storage-classes, strong-consistency, presigned-url, lifecycle, aws-basics, reported-rounds

**Start here: the concepts**
- **S3** is object storage: files by key in a bucket, accessed over an API. It isn't a file system or a database.

**The live scenario (functional requirement)**
*FR: "Customers upload invoices, which are read often for 30 days, then rarely, and kept for 7 years."*

**What the interviewer is really checking**
Practical use: uploads, access control, costs, and knowing the current consistency model.

**How I answer it** (120-second answer, point by point)
1. **Consistency:** S3 provides **strong read-after-write consistency** for object PUTs and DELETEs, and for list operations. Older material says "eventually consistent", which has been out of date since December 2020.
2. **Durability** is designed for 11 nines, by storing across multiple AZs in most storage classes.
3. **Storage classes:**

| Class | Use |
|---|---|
| Standard | Frequently read |
| Intelligent-Tiering | Unknown or changing patterns |
| Standard-IA | Rarely read, but needed fast |
| Glacier Instant, Flexible, Deep Archive | Archive, with cheaper storage and costlier or slower retrieval |

4. **For this FR:** a lifecycle rule moves objects to Standard-IA after 30 days, then to Glacier, and expires them after 7 years.
5. **Uploads:** the client uploads directly using a **pre-signed URL**, so large files don't go through your API. Large files use **multipart upload**.
6. **Security:** keep Block Public Access on, encrypt objects, and use bucket policies with least privilege.
7. **Events:** a new object can trigger Lambda, SQS or EventBridge for processing.

**Trade-offs and what can go wrong**
- There's no partial update: changing an object replaces all of it.
- Infrequent-access classes have minimum storage periods and retrieval fees, so moving small or short-lived objects can cost more.
- Abandoned multipart uploads keep costing money, so add a lifecycle rule to abort them.

**Follow-ups to expect**
- *Deeper?* -> The S3 section of the brush-up file named at the top.

**60-second answer**
"S3 is object storage: files stored by key in a bucket, with very high durability, and it's been strongly consistent for reads and listings since 2020. Storage classes trade storage price against retrieval cost, so for invoices, I'd use a lifecycle rule to move them to Infrequent Access after 30 days, then to Glacier, then expire them. Users upload directly through a pre-signed URL, using multipart for large files, so my API isn't in the path. Block Public Access stays on, and new objects can trigger processing through events."

### Q6 [mid] What is Lambda? What are its limits and cold starts, and when wouldn't you use it with Java?
tags: aws, lambda, serverless, cold-start, snapstart, concurrency, timeout, aws-basics, reported-rounds

**Start here: the concepts**
- **Lambda** runs your function on an event, and you don't manage servers. You pay per request and for compute time.
- **Cold start:** the first call on a new environment must start the runtime and your code.

**The live scenario (functional requirement)**
*FR: "Generate a thumbnail when a file reaches S3."* Traffic is spiky, and often zero. Lambda fits. A Spring Boot API with steady traffic and a p99 of 100 ms likely doesn't.

**What the interviewer is really checking**
That you know the limits, and how Java specifically behaves.

**How I answer it** (120-second answer, point by point)

| Fact | Value |
|---|---|
| Maximum timeout | 15 minutes (standard functions) |
| Memory | 128 MB to 10,240 MB |
| CPU | Scales with memory |
| Concurrency | Each environment handles one request at a time on standard functions |

1. **Java cold starts** can reach seconds, because of JVM start and framework scanning. Options are **SnapStart**, which restores from a snapshot of an initialised environment; **provisioned concurrency**, which keeps environments warm at a cost; smaller frameworks and less classpath scanning; or a GraalVM native image.
2. **Connections:** many concurrent environments can overwhelm a database, so use **RDS Proxy** and cap concurrency.
3. **Good fit:** event-driven, spiky, short work: file processing, queue consumers, scheduled jobs.
4. **Poor fit:** steady high traffic, where containers are usually cheaper; tight latency needs; long jobs; and work needing local state.
5. **Failures:** async invokes and queue triggers retry, so handlers must be idempotent. Use a dead-letter destination.

**Trade-offs and what can go wrong**
- SnapStart restores the same snapshot many times, so uniqueness or network connections created during initialisation need care.
- New AWS accounts may start with lower quotas, so check before a launch.
- A newer option, Lambda Managed Instances, allows async and event-source invocations of up to 90 minutes. Synchronous calls keep the 15-minute limit, so check the docs if this matters.

**How I'd monitor it**
Duration, errors, throttles, concurrent executions, init duration for cold starts, and iterator age for streams.

**Follow-ups to expect**
- *Azure equivalent?* -> Azure Functions, in bank 32 Q7.

**60-second answer**
"Lambda runs a function on an event, with no servers to manage, at up to 15 minutes and about 10 GB of memory, with CPU scaling alongside memory. For Java, the main issue is cold starts, so I'd use SnapStart or provisioned concurrency and cut classpath scanning. It suits spiky, event-driven work like file processing. For a steady, latency-sensitive Spring Boot API, containers are usually cheaper and more predictable. I also guard the database with RDS Proxy, because concurrency multiplies connections, and I make handlers idempotent, since retries happen."

### Q7 [mid] EC2, ECS, EKS, Fargate, Lambda: where would you run a Spring Boot service?
tags: aws, ecs, eks, fargate, lambda, ec2, compute-choice, containers, aws-basics, reported-rounds

**Start here: the concepts**
- These differ mainly in **how much you manage**. **ECS** and **EKS** orchestrate containers, and **Fargate** runs those containers without you managing servers.

**The live scenario (functional requirement)**
*FR: "Five Spring Boot microservices, a small team, no Kubernetes experience."*

**What the interviewer is really checking**
A decision based on team and workload, not on fashion.

**How I answer it** (120-second answer, point by point)

| Option | You manage | Fits |
|---|---|---|
| EC2 | OS, patches, deploys, scaling | Special needs, legacy apps, or very cost-tuned setups |
| ECS on Fargate | Task definitions and scaling rules | Most small and mid teams |
| ECS on EC2 | The above, plus the server fleet | Better unit cost at large steady scale; GPUs |
| EKS | Kubernetes itself, add-ons and upgrades | Teams already on Kubernetes, or needing its ecosystem or portability |
| Lambda | Only code | Spiky, event-driven work (Q6) |

For this FR, I'd choose **ECS on Fargate**: no servers to patch, a simple model, deep integration with ALB and IAM, and scaling with Application Auto Scaling.

Things to set for the JVM in any container:
- Align `-XX:MaxRAMPercentage` with the container's memory limit, or the task gets killed (exit code 137).
- Give enough CPU for start-up, as well as a health-check grace period, so that a slow-starting JVM isn't killed in a loop.
- Handle `SIGTERM` for graceful shutdown: `server.shutdown=graceful`.

**Trade-offs and what can go wrong**
- EKS brings a larger operational load, with upgrades, networking, and add-ons. Choosing it for five services with no experience is usually over-engineering.
- Fargate costs more per unit of compute than well-used EC2, in exchange for less work.
- Lock-in is a real but often overstated concern: a container image moves easily, and the surrounding config is what takes the work.

**Follow-ups to expect**
- *ECS scaling and health checks?* -> The brush-up file's ECS section.
- *JVM in containers?* -> Bank 07 Q5.

**60-second answer**
"It's mainly about how much I want to manage. For a small team with no Kubernetes experience, I'd choose ECS on Fargate: no servers to patch, simple scaling, and good ALB and IAM integration. EKS makes sense if the team already knows Kubernetes or needs its ecosystem. EC2 suits legacy or highly tuned workloads, and Lambda suits spiky events rather than a steady API. Whatever I choose, for the JVM I set MaxRAMPercentage to fit the memory limit, allow a start-up grace period, and shut down gracefully."

### Q8 [mid] ALB vs NLB: which do you use, and how do health checks work?
tags: aws, alb, nlb, load-balancer, target-group, health-check, layer-7, layer-4, aws-basics, reported-rounds

**Start here: the concepts**
- **ALB (Application Load Balancer):** layer 7. It understands HTTP, so it can route by path and host.
- **NLB (Network Load Balancer):** layer 4. It handles TCP and UDP, with very low latency and static IPs.

**The live scenario (functional requirement)**
*FR: "Route `/orders` and `/payments` to different services, and let a partner allow-list a fixed IP for a TCP feed."* These are two different needs.

**What the interviewer is really checking**
Picking by requirement, and knowing how deployments and health checks interact.

**How I answer it** (120-second answer, point by point)

| Need | Choose |
|---|---|
| HTTP routing by path, host or header; TLS termination; WAF | ALB |
| TCP or UDP; extreme performance | NLB |
| Static or Elastic IP; PrivateLink | NLB (it can forward to an ALB when you need both) |

1. **Target group:** the set of instances, tasks or IPs, with its own health check.
2. **Health check:** hit a real endpoint, such as `/actuator/health/readiness`. Unhealthy targets stop getting traffic.
3. **Keep readiness shallow:** if it fails whenever a shared database blips, every target goes unhealthy together, and an outage becomes total.
4. **Deregistration delay:** on deploy, the ALB stops new requests and lets in-flight ones finish. Pair it with graceful shutdown in Spring Boot.
5. **Span two or more AZs.**

**Trade-offs and what can go wrong**
- Idle timeouts: the ALB's timeout should be shorter than the backend's keep-alive, or you get intermittent 502s.
- 502 means a bad response from the target; 503 means no healthy target; 504 means the target timed out. Those three point you in different directions.

**How I'd monitor it**
Target 5xx against load balancer 5xx, target response time, healthy host count, and rejected connections.

**Follow-ups to expect**
- *API Gateway instead?* -> It adds API keys, usage plans and Lambda integration, and costs more per request at high volume.

**60-second answer**
"ALB works at layer 7, so it routes HTTP by path or host, terminates TLS, and integrates with WAF. NLB works at layer 4 for TCP and UDP, with very low latency and static IPs. I use ALB for nearly all REST APIs, and NLB when I need a fixed IP or non-HTTP traffic. Target groups health-check a real endpoint like readiness, kept shallow so a shared database blip doesn't take all targets out. On deploy, deregistration delay and graceful shutdown let in-flight requests finish."

### Q9 [mid] RDS, Aurora or DynamoDB: how do you choose?
tags: aws, rds, aurora, dynamodb, multi-az, read-replica, partition-key, aws-basics, reported-rounds

**Start here: the concepts**
- **RDS:** managed relational databases, such as PostgreSQL and MySQL.
- **Aurora:** AWS's PostgreSQL- and MySQL-compatible engine with a distributed storage layer.
- **DynamoDB:** serverless key-value and document database.

**The live scenario (functional requirement)**
*FR: "Orders need transactions and reporting joins. Session data is 50,000 reads a second by key."* These are two different stores.

**What the interviewer is really checking**
Knowing access patterns come first, and Multi-AZ vs read replica, which is often confused.

**How I answer it** (120-second answer, point by point)

| | RDS | Aurora | DynamoDB |
|---|---|---|---|
| Model | Relational | Relational | Key-value, document |
| Scale writes | Bigger instance | Bigger instance (or sharding options) | Partitions automatically |
| Read scale | Read replicas | Many replicas on shared storage | Built in |
| Best for | Standard relational needs at lower cost | Higher availability and read scale | Known key-based access at any scale |
| Queries | Full SQL | Full SQL | By key; design around access patterns |

1. **Multi-AZ vs read replica:** Multi-AZ is for **availability**, with automatic failover. A read replica is for **read scaling**, and is usually asynchronous, so reads can be slightly stale.
2. **Aurora** stores six copies of data across three AZs, and typically fails over faster than standard RDS.
3. **DynamoDB design:** choose the **partition key** carefully. A poor key creates a hot partition. There are no joins, so model around your queries, and items are limited to 400 KB.
4. **Connections:** many containers multiply connections, so use RDS Proxy or size pools by the arithmetic in bank 89 Q4.

**Trade-offs and what can go wrong**
- Picking DynamoDB without knowing access patterns leads to expensive scans later.
- Applications must handle failover: use cluster endpoints, retry, and don't cache DNS forever (the JVM's DNS TTL matters here).
- Aurora costs more than RDS, so justify it.

**How I'd monitor it**
Connections, CPU, replica lag, freeable memory, slow query logs; on DynamoDB, throttles and consumed capacity.

**Follow-ups to expect**
- *General SQL or NoSQL decision?* -> Bank 88 Q4 and bank 25 Q3.

**60-second answer**
"I start from access patterns. Orders with transactions and joins go relational: RDS by default, or Aurora if I need more read replicas and faster failover. High-volume lookups by key, like sessions, suit DynamoDB, where the partition key design is the critical decision. And keep the distinction clear: Multi-AZ is for availability with automatic failover, and read replicas are for read scaling and can lag. With many containers I watch connection counts, using RDS Proxy if needed."

### Q10 [mid] SQS, SNS, EventBridge or Kafka (MSK)?
tags: aws, sqs, sns, eventbridge, msk, kafka, fifo, visibility-timeout, dlq, fan-out, aws-basics, reported-rounds

**Start here: the concepts**
- **SQS:** a queue. One consumer group processes each message, then it's deleted.
- **SNS:** pub/sub. One message is pushed to many subscribers.
- **EventBridge:** an event bus with content-based routing.
- **Kafka (MSK):** a replayable log that many consumer groups read independently.

**The live scenario (functional requirement)**
*FR: "An order is placed. Billing, email and analytics each react. Slow email must not affect billing."*

**What the interviewer is really checking**
The queue vs pub/sub vs log difference, plus SQS mechanics.

**How I answer it** (120-second answer, point by point)
1. **Fan-out:** SNS topic to three SQS queues. Each consumer gets its own queue, retries independently, and slow email doesn't affect billing.
2. **SQS mechanics:** a consumer receives a message, and it becomes invisible for the **visibility timeout**. The consumer deletes it on success. If not deleted, it reappears, so set the timeout longer than processing time. After N failures, it goes to a **dead-letter queue**.

| | SQS Standard | SQS FIFO |
|---|---|---|
| Throughput | Nearly unlimited | Limited; higher in high-throughput mode |
| Order | Best effort | Per message group |
| Delivery | At least once | Deduplicated within a window |

3. **Handlers must be idempotent,** since at-least-once means duplicates.
4. **Choosing:**

| Need | Choose |
|---|---|
| Background work queue | SQS |
| Simple fan-out | SNS + SQS |
| Routing events by content, SaaS and AWS events | EventBridge |
| Replay, stream processing, very high throughput, many readers | Kafka or MSK |

**Trade-offs and what can go wrong**
- SQS has no replay: once deleted, a message is gone.
- A too-short visibility timeout causes duplicate processing while the first attempt is still running.
- MSK has a lot more to run and tune than SQS, so don't take it on without a reason for it.
- Long polling (`WaitTimeSeconds`) reduces empty receives and cost.

**How I'd monitor it**
Age of the oldest message (the most useful one), queue depth, DLQ count, and consumer errors.

**Follow-ups to expect**
- *Kafka internals?* -> Bank 02, bank 22 Q3.

**60-second answer**
"SQS is a queue: consumers process a message, then delete it. SNS pushes one message to many subscribers. EventBridge routes events by content. Kafka is a replayable log with independent consumer groups. For an order with three reactions, I'd use SNS fan-out to three SQS queues, so each retries independently. With SQS, the visibility timeout must exceed processing time, failures go to a DLQ, and handlers must be idempotent. I'd choose Kafka only if I need replay, stream processing or very high throughput, since it costs more to run."

### Q11 [mid] CloudWatch vs CloudTrail: how do you monitor an application on AWS?
tags: aws, cloudwatch, cloudtrail, x-ray, alarms, logs-insights, opentelemetry, monitoring, aws-basics, reported-rounds

**Start here: the concepts**
- **CloudWatch** tells you **how the system is behaving:** metrics, logs and alarms.
- **CloudTrail** tells you **who did what:** a record of AWS API calls.
- **X-Ray** or OpenTelemetry show **where a request spent time**.

**The live scenario (functional requirement)**
*FR: "Orders are slow since this morning, and someone may have changed a security group."* Latency is a CloudWatch question. The change is a CloudTrail one.

**What the interviewer is really checking**
That you don't mix those up, and can alert on something meaningful.

**How I answer it** (120-second answer, point by point)
1. **Infrastructure metrics** come free or built in: CPU, ALB 5xx, RDS connections.
2. **Application metrics:** Micrometer publishes to CloudWatch or Prometheus. Note that `EC2` doesn't report memory usage by default, because that's inside the OS. Use the CloudWatch agent.
3. **Logs:** structured JSON to stdout, shipped to CloudWatch Logs or Splunk, and searched with Logs Insights. Set a retention period, since the default is to keep logs forever.
4. **Alarms:** on user-facing symptoms such as p99 latency and error rate, more than on CPU alone. Route them through SNS to on-call.
5. **Tracing:** OpenTelemetry to X-Ray or another backend, propagating a trace id.
6. **Audit:** CloudTrail on in all regions, stored in a separate locked-down account.

**Trade-offs and what can go wrong**
- Log ingestion can be a large bill, so control debug logs.
- High-cardinality custom metrics, such as one per customer, get expensive quickly.

**How I'd monitor it**
This question is the monitoring answer. The general method is in bank 09.

**Follow-ups to expect**
- *Audit a change?* -> CloudTrail by event name, such as `AuthorizeSecurityGroupIngress`.

**60-second answer**
"CloudWatch shows how the system is behaving: metrics, logs and alarms. CloudTrail records who did what, as an audit trail of API calls. So a latency spike is CloudWatch, and a mystery security group change is CloudTrail. I add application metrics through Micrometer, send structured logs with a retention setting, trace with OpenTelemetry, and alarm on user-facing symptoms like p99 and error rate. EC2 memory needs the agent, since it isn't reported by default."

### Q12 [mid] Secrets Manager, Parameter Store and KMS: what's each for?
tags: aws, secrets-manager, parameter-store, kms, encryption, rotation, envelope-encryption, aws-basics, reported-rounds

**Start here: the concepts**
- **KMS** manages **encryption keys**, and doesn't store your secrets.
- **Secrets Manager** stores secrets, with rotation built in.
- **Parameter Store** stores configuration, and optionally encrypted values.

**The live scenario (functional requirement)**
*FR: "An ECS service needs a database password that rotates, a feature-flag setting, and encrypted documents in S3."* That's one of each.

**What the interviewer is really checking**
The distinction, and not storing secrets in images or environment files.

**How I answer it** (120-second answer, point by point)

| Need | Use |
|---|---|
| Database password, API key, with rotation | Secrets Manager |
| Config values, or simple secrets at low cost | Parameter Store (`SecureString`) |
| Encrypting data, or controlling who may decrypt | KMS |

1. **Envelope encryption:** KMS protects a small data key, and the data key encrypts the actual data. Services like S3 do this for you.
2. **Injecting on ECS:** reference a secret ARN in the task definition, and the agent injects it as an environment variable, using the **execution role**.
3. **Rotation:** the app must handle a change. Env-injected secrets need a task restart, and fetching at runtime with a short cache picks up changes. Rotation with two valid credentials avoids a gap.
4. **Permissions:** a role needs both `secretsmanager:GetSecretValue` and access to the KMS key, if it's a customer-managed key.

**Trade-offs and what can go wrong**
- Environment variables can leak through logs, crash dumps or Actuator's `/env` endpoint.
- Secrets Manager charges per secret, so don't use it for plain config.

**Follow-ups to expect**
- *Secrets in logs?* -> Bank 89 Q6.

**60-second answer**
"KMS manages encryption keys. Secrets Manager stores secrets with built-in rotation, for things like database passwords. Parameter Store is for config and low-cost secure strings. On ECS, I reference the secret in the task definition, and it's injected using the execution role. With rotation, the app must cope, either by restarting tasks or by fetching at runtime with a short cache. KMS uses envelope encryption, with a master key protecting data keys, and services like S3 handle that for you."

### Q13 [senior] Walk me through deploying a Spring Boot service on AWS end to end.
tags: aws, deployment, ecs, ecr, alb, ci-cd, blue-green, terraform, spring-boot, aws-basics, reported-rounds

**Start here: the concepts**
- An interviewer wants a full path from a commit to a request being served, with the reasons for each part.

**The live scenario (functional requirement)**
*FR: "Deploy the order service with no downtime, secure access to a database, and a safe rollback."*

**What the interviewer is really checking**
Whether you've seen the full picture, and can connect the services above.

**How I answer it** (120-second answer, point by point)
1. **Build:** CI runs tests, scans, and builds a Docker image with layered JARs, tagged with the commit SHA, and pushes it to **ECR**.
2. **Infrastructure as code:** Terraform or CDK, so that it's reviewable and repeatable.
3. **Network:** VPC, ALB in public subnets, tasks and database in private subnets, with security groups chained.
4. **Runtime:** ECS on Fargate across two or more AZs, with a task role for AWS access and secrets from Secrets Manager.
5. **Database:** RDS or Aurora Multi-AZ, with Flyway or Liquibase migrations that stay backward compatible (bank 73 Q9).
6. **Deploy:** a rolling update, or blue-green with CodeDeploy, using health checks on readiness. A deployment circuit breaker rolls back failed deployments automatically.
7. **Shutdown:** `server.shutdown=graceful`, with the ALB's deregistration delay.
8. **Scale:** target tracking on CPU or request count per target, with a sensible maximum that respects database connections.
9. **Observe:** logs, metrics, traces and alarms (Q11), watching the new version's error rate during rollout.
10. **Rollback:** redeploy the previous image tag. That's why database changes must remain compatible with the old version.

**Trade-offs and what can go wrong**
- Using `latest` as an image tag makes rollback and audit unreliable.
- A long JVM start-up, with too short a health grace period, gives a restart loop (exit code 137 or failing health checks).
- Scaling tasks without limits can exhaust database connections.

**How I'd monitor it**
Deployment state, new-version error rate and p99, healthy targets, and task restarts.

**Follow-ups to expect**
- *What's the fastest way to explain this?* -> Draw one request from DNS through the ALB to a task and the database, then one deploy.

**60-second answer**
"CI tests the code, builds an image tagged with the commit SHA, and pushes to ECR. Infrastructure is Terraform: a VPC with the ALB in public subnets, and tasks and database in private ones. ECS on Fargate runs tasks in at least two AZs, with a task role and secrets from Secrets Manager. Migrations run with Flyway and stay backward compatible. Deploys are rolling or blue-green, gated by readiness, with automatic rollback. Graceful shutdown lets in-flight requests finish. To roll back, I redeploy the previous image, which is why compatible migrations matter."

### Q14 [mid] How do you make an AWS service scalable and highly available? What does the shared responsibility model mean?
tags: aws, high-availability, scalability, auto-scaling, shared-responsibility, well-architected, caching, aws-basics, reported-rounds

**Start here: the concepts**
- **Scalability:** handles more load. **Availability:** keeps working when parts fail. They're related, but separate.
- **Shared responsibility:** AWS secures **the cloud**, and you secure **what's in it**.

**The live scenario (functional requirement)**
*FR: "Grow from 1,000 to 10,000 users, with no single point of failure."*

**What the interviewer is really checking**
That you can find single points of failure, and know what remains your responsibility.

**How I answer it** (120-second answer, point by point)
1. **Stateless app tier:** sessions go to Redis or a token, so any instance can serve anyone.
2. **Spread out:** multiple AZs, a load balancer, and Auto Scaling.
3. **Protect the database:** cache with ElastiCache, add read replicas, and move slow work onto a queue.
4. **Static content:** S3 and CloudFront, off the app servers entirely.
5. **Look for single points of failure:** one NAT, one AZ, one database without failover, one Redis without a replica.
6. **Practice failure:** kill an instance in a test environment, and test a database failover.

| AWS is responsible for | You are responsible for |
|---|---|
| Data centres, hardware, the virtualisation layer | IAM and access |
| The managed service's underlying platform | Your data and its encryption choices |
| | Network rules and security groups |
| | App code, and the OS patches on EC2 |

The boundary moves with the service. On EC2 you patch the OS, while on Fargate or Lambda AWS handles that, and app security is still yours.

**Trade-offs and what can go wrong**
- More availability costs more, so match it to the real need. Moving from 99.9% to 99.99% is a big step in cost.
- Scaling the app tier just moves the bottleneck to the database.

**Follow-ups to expect**
- *How do you know what's needed?* -> Bank 30 Q21 on scaling, and bank 63 Q1 on high TPS.

**60-second answer**
"For scale, I make the app stateless, put it behind a load balancer with Auto Scaling, cache with ElastiCache, add read replicas, and move slow work to queues. For availability, I remove single points of failure: multiple AZs, a Multi-AZ database, and redundant NAT. Then I test failure, because untested failover often fails. Shared responsibility means AWS secures the cloud itself, and I secure what's in it: IAM, data, network rules and code, plus OS patches if I'm on EC2."

### Q15 [mid] How do you control AWS costs?
tags: aws, cost, finops, savings-plans, graviton, budgets, cost-explorer, tagging, aws-basics, reported-rounds

**Start here: the concepts**
- You can't reduce what you can't see, so visibility comes first.

**The live scenario (functional requirement)**
*FR: "The AWS bill rose 40% this quarter, and nobody knows why."*

**What the interviewer is really checking**
A method, rather than a list of random tips.

**How I answer it** (120-second answer, point by point)
1. **See it:** tag resources by team and service, use Cost Explorer, and set AWS Budgets alerts.
2. **Find the biggest items first,** and check for the usual surprises:

| Surprise | Fix |
|---|---|
| NAT gateway data charges | VPC endpoints for S3 and DynamoDB |
| Idle or oversized instances | Rightsize with Compute Optimizer |
| Non-production running at night | Schedule it off |
| Old snapshots, unattached EBS volumes | Lifecycle rules, and clean up |
| Log ingestion and retention | Reduce debug logs, and set retention |
| Inter-AZ and internet data transfer | Keep chatty services close, use CloudFront |

3. **Commit for the steady base:** Savings Plans, after rightsizing rather than before.
4. **Use cheaper options:** Spot for batch, Graviton where the app runs well on ARM, and S3 lifecycle rules.
5. **Keep it going:** cost in dashboards, and a review each month.

**Trade-offs and what can go wrong**
- Don't commit to a Savings Plan before rightsizing, or you lock in waste.
- Removing redundancy to save money swaps a known cost for an outage risk.

**Follow-ups to expect**
- *More?* -> Bank 73 Q14 covers cloud cost in depth.

**60-second answer**
"First I get visibility, with tagging, Cost Explorer and Budgets alerts, and I look at the biggest items first. The usual surprises are NAT data charges, oversized instances, non-production running overnight, forgotten snapshots, and log ingestion. I rightsize first, then buy Savings Plans for the steady base, use Spot for batch and Graviton where it fits, and add lifecycle rules. And I don't remove redundancy just to save money without weighing the outage risk."
