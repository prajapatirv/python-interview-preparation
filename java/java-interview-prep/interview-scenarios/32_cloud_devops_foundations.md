---
id: foundations-cloud-devops
title: Cloud, Docker & Kubernetes: from the basics (drafted)
stack: java
skill: cloud-devops
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What are regions, availability zones and resource groups in Azure?
tags: azure, regions, availability-zones, resource-groups, high-availability, governance, basics

**Start here: the concepts**
- **Region**: a geographic area, such as West Europe or East US, that contains one or more Azure datacentres. You pick a region to be close to users, meet data-residency rules, and get the services and prices you need.
- **Datacentre**: a physical building full of servers, with its own power, cooling and network.
- **Availability Zone (AZ)**: a physically separate location inside one region, made of one or more datacentres. Each zone has independent power, cooling and networking. Zone-enabled regions have at least three zones. Not every region has zones, and not every service supports them. It exists so one building's failure doesn't take down your whole app.
- **High availability (HA)**: designing so the app keeps working when one part fails.
- **Resource**: any single thing you create in Azure, such as a VM, database or storage account.
- **Resource group**: a logical container that holds resources sharing the same lifecycle, meaning they are created, updated and deleted together. Each resource lives in exactly one group, and groups cannot be nested. Its resources can sit in different regions.
- **Subscription**: the billing and access boundary. One subscription holds many resource groups.
- **Tags and policies**: tags are name-value labels (e.g. `env=dev`, `team=orders`) used for cost reports and search. Policies are rules (e.g. "only allow these regions"). Tags are not inherited by resources from their group by default, so enforce them with a policy.

**The live scenario**
An orders API ran on 3 VMs in one zone of a region (the numbers here are illustrative). One night that zone had a power problem. All 3 VMs went down, and about 2,000 orders per minute failed for 40 minutes. The VMs were healthy copies, but they all sat in the same failure area. Afterwards the team spread the VMs across 3 zones. When one zone fails again, two-thirds of capacity stays up.

The same team had a dev environment with 60 resources scattered around. Deleting it took a day of hunting. After they put each environment in its own resource group, cleanup became one delete.

**What the interviewer is really checking**
Whether you know the difference between a physical concept (region, zone) and a logical one (resource group). They also want to see that you connect zones to high availability and resource groups to lifecycle and organisation.

**How I answer it**
1. **Start with the region.** It is the geographic area where I deploy. I choose it for latency, legal data location and service availability. It's the biggest unit.
2. **Then explain zones.** They are separate locations inside the region with independent power, cooling and network. I deploy copies of the app across at least two or three zones, so one zone failing doesn't cause an outage. A single zone is a single point of failure.
3. **Then explain resource groups.** They are logical, not physical. They group resources that live and die together, such as one app's VMs, database and network. Deleting the group deletes everything in it, which keeps environments tidy.
4. **Place it in the hierarchy:** subscription → resource groups → resources. Access control (RBAC) and policies apply at the subscription or group and flow down. Tags help with cost tracking.
5. **Connect them.** Regions and zones answer "where does it run, and how does it survive failure?" Resource groups answer "how do I organise, secure and clean it up?"

**Trade-offs and what can go wrong**
- Zones add cost (more instances, possibly cross-zone data transfer charges) and a little latency between zones.
- Some regions or services don't support zones, so check before designing.
- Zones protect against a zone failure, not a whole-region failure. For that you need a second region.
- Putting everything for all environments into one group makes cleanup and permissions messy.
- Deleting a group is irreversible and removes everything inside, so protect production with resource locks.
- Assuming tags inherit from the group is a common mistake.

**How I'd monitor it**
- Azure Service Health and Resource Health alert on zone or region incidents.
- Azure Monitor shows how many instances are healthy in each zone, and availability tests check the app from outside.
- Azure Policy compliance shows whether resources use approved regions and carry required tags.
- Cost Management, filtered by resource group or tag, shows spend per app or team.
- The Activity Log shows who deleted or changed a group.

**Follow-ups to expect**
- *Can a resource group contain resources from different regions?* -> Yes. The group has its own location only for storing its metadata, but its resources can be anywhere.
- *How do you survive a whole region going down?* -> Deploy to a second region (often a paired one) and use something like Azure Front Door or Traffic Manager to route traffic, with data replicated across regions.
- *How do you stop someone accidentally deleting a production group?* -> Apply a delete resource lock and limit access with RBAC.

**60-second answer**
A region is a geographic area where Azure has datacentres, and I choose it for latency, data-residency rules and service availability. Availability Zones are physically separate locations inside a region, each with its own power, cooling and network. I spread my app across zones so one zone failing doesn't cause an outage. A resource group is a logical container for resources that share a lifecycle, such as one app's VMs, database and network. Deleting the group deletes everything in it. A subscription holds many resource groups, and access control and policies apply at those levels, while tags help with cost tracking. So regions and zones are about where it runs and how it survives failure, and resource groups are about organising and cleaning up.

### Q2 [mid] How does Azure identity and access (RBAC) work?
tags: azure, rbac, entra-id, managed-identity, key-vault, authorization, basics

**Start here: the concepts**
- **Identity**: the "who" making a request. It can be a person (user), a group, or a program (a service principal or managed identity).
- **Microsoft Entra ID**: Azure's identity directory (formerly Azure Active Directory). It keeps identities and proves who they are (authentication). It answers "who are you?", not "what may you do?".
- **Azure RBAC (role-based access control)**: the system that decides what an identity may do to Azure resources (authorization). Instead of giving permissions to each person one by one, you hand out roles.
- **Role**: a named bundle of allowed actions. Built-in examples are Reader (view only), Contributor (create and change, but not grant access) and Owner (everything, including granting access). You can also write custom roles.
- **Scope**: where the role applies. The levels are management group > subscription > resource group > resource. A role assigned at a higher level is inherited by everything below it.
- **Role assignment**: the thing that actually grants access. It is three items together: **role + identity + scope**. Assignments are additive, so an identity gets the union of all its roles.
- **Managed identity**: an identity Azure creates for your app so it needs no password or secret in code. *System-assigned* is tied to one resource and deleted with it. *User-assigned* is a separate object that several resources can share. It is similar to an IAM role attached to an EC2 instance or Lambda function in AWS.
- **Key Vault**: a managed store for secrets, keys and certificates. It exists so secrets are not in code, config files or pipelines. Access to it is also controlled by RBAC (or the older access policies).

**The live scenario**
A team ran 12 microservices on Azure. Each one read from a storage account using a connection string kept in a config file. One string leaked through a Git repo. Rotating it meant editing 12 services and redeploying, which took a full day. Worse, the string gave full access to the account. They moved to managed identities. Each service got a role such as *Storage Blob Data Reader* on only its own storage account. Nothing secret sat in config any more, and nothing needed rotating.

**What the interviewer is really checking**
Whether you separate *authentication* (Entra ID) from *authorization* (RBAC), understand scope and inheritance, and know to avoid stored secrets by using managed identities.

**How I answer it**
1. **Start with Entra ID.** Every user, group and app is an identity there. Azure must know who is calling before it can decide anything.
2. **Explain a role assignment as role + identity + scope.** Permissions live in roles, not on people, so access is easy to audit and change.
3. **Choose the narrowest scope.** Scopes inherit downward, so a role on a subscription reaches every resource inside it. Assign at resource-group or resource level to limit damage if an identity is compromised (least privilege).
4. **Give apps a managed identity.** Azure issues and rotates the credentials, so no secret exists to leak. Use system-assigned for a one-to-one app, and user-assigned when several resources share an identity or it must survive redeployment.
5. **Put the remaining secrets in Key Vault.** Some third-party API keys cannot be replaced by an identity. The app's managed identity gets a role like *Key Vault Secrets User* and reads them at runtime.
6. **Prefer built-in roles and groups.** Assign to groups, not individuals, so joiners and leavers are handled in one place.

```
az role assignment create --assignee <principalId> --role "Storage Blob Data Reader" --scope <storageAccountId>
```

**Trade-offs and what can go wrong**
- Granting Owner or Contributor at subscription level "to make it work" gives far too much access.
- Entra roles (managing users and directory) are separate from Azure RBAC roles (managing resources). Mixing them up is a common mistake.
- Management-plane roles (e.g. Contributor) do not always grant data access, such as reading blobs. Data roles are separate.
- New assignments can take a few minutes to take effect, which can cause confusing 403 errors.
- A shared user-assigned identity widens the blast radius. Deleting a system-assigned identity's resource also deletes its access.

**How I'd monitor it**
- **Activity Log**: alert on role assignment writes and deletes.
- **Entra sign-in logs**: these include managed identity sign-ins, so you can see unusual callers.
- **Key Vault diagnostic logs**: send them to Log Analytics or Splunk (for example via Event Hubs) and search for unexpected secret reads or failures.
- **App logs**: search for `AuthorizationFailed` or HTTP 403 spikes after deployments.
- **Access reviews** and Azure Policy, to find stale or over-broad assignments.

**Follow-ups to expect**
- *What is the difference between Entra roles and Azure roles?* -> Entra roles manage the directory (users, groups, apps). Azure roles manage resources like VMs and storage.
- *Contributor vs Owner?* -> Both can manage resources, but only Owner (or User Access Administrator) can grant access to others.
- *System-assigned vs user-assigned managed identity?* -> System-assigned lives and dies with one resource. User-assigned is standalone and reusable across resources.

**60-second answer**
Azure separates who you are from what you can do. Microsoft Entra ID holds the identities, users and apps, and proves who they are. Azure RBAC then grants permissions through role assignments, which combine a role, an identity and a scope. Scopes run from management group to subscription, resource group and resource, and permissions inherit downward, so I assign at the narrowest scope that works. For applications I use managed identities, system-assigned or user-assigned, so there are no passwords in config. It works like an IAM role on EC2 or Lambda. Any secrets that remain go in Key Vault, which the managed identity reads through its own role. I audit it all with the Activity Log and Key Vault diagnostic logs.

### Q3 [mid] Which Azure services would host a Spring Boot microservice?
tags: azure, spring-boot, aks, container-apps, app-service, basics

**Start here: the concepts**
- **PaaS (Platform as a Service):** the cloud provider runs the servers, operating system and patching. You upload your app and it runs. It exists so small teams don't manage machines.
- **Container:** your app plus its Java runtime and libraries packed into one image that runs the same everywhere. It exists to end "works on my machine".
- **Kubernetes:** software that runs many containers across many machines. It restarts crashed ones, scales them and rolls out new versions. It is powerful but has a lot to learn and operate.
- **Azure App Service:** the simplest PaaS. You deploy a JAR or a container and Azure runs it behind a URL.
- **Azure Container Apps:** serverless containers. You give it an image and Azure runs it without exposing the Kubernetes cluster to you. It is built on Kubernetes underneath.
- **KEDA:** an autoscaler that scales on events, such as HTTP requests or Kafka consumer lag, and can scale down to zero copies. Container Apps has it built in.
- **Dapr (optional):** a helper process beside your app that provides common microservice features such as service calls, pub/sub messaging and state storage. This avoids writing that plumbing yourself.
- **AKS (Azure Kubernetes Service):** managed Kubernetes. Azure runs the control plane (the cluster's brain) and you manage workloads, nodes and upgrades. You get full control: service mesh, custom operators and fine-grained networking.
- **Azure Spring Apps:** a managed service built specifically for Spring apps. Microsoft has announced its retirement, so verify the current dates and replacement guidance before recommending it.

**The live scenario**
A team has 12 Spring Boot services. Traffic is about 300 requests/second at peak and near zero at night. Two engineers handle operations. They first considered AKS because "everyone uses Kubernetes". After two months they were spending about a third of their time on node upgrades, ingress setup and cluster security. They moved the stateless services to Container Apps. Operations work dropped, and the idle night-time cost fell because replicas scaled down. One service, which uses a custom operator and a service mesh, stayed on AKS. An older team on Azure Spring Apps had to plan a migration once the retirement was announced.

**What the interviewer is really checking**
Whether you know the main hosting options, can match one to a team's needs and skills (not just name them), and know the Azure Spring Apps retirement caveat.

**How I answer it**
1. **List the options from simple to powerful:** App Service, Container Apps, AKS, and Azure Spring Apps with its caveat. This shows you understand the range of control versus effort.
2. **Containerize first.** Build a Docker image and push it to Azure Container Registry (ACR), Azure's private image store. A container image is portable across Container Apps, AKS and App Service, so the choice stays reversible.
3. **Pick App Service** for one or a few simple web or API apps where the team wants minimal operations and no container knowledge.
4. **Pick Container Apps as the default** for most microservice teams. Scaling comes from KEDA, rollouts and revisions are built in, and the team never touches Kubernetes.
5. **Pick AKS** only when you need Kubernetes features: a service mesh, custom operators, special networking or full scheduling control. Choose it knowing you take on the operations work.
6. **Treat Azure Spring Apps as a legacy path.** Check Microsoft's current status and dates, and avoid starting new projects on it.

**Trade-offs and what can go wrong**
- Container Apps hides Kubernetes, which is simpler but gives less control. Some Kubernetes features are unavailable.
- Scale-to-zero means a cold start. A Spring Boot JVM can take several seconds to start, so set a minimum of one replica for latency-sensitive APIs.
- AKS gives flexibility but costs people time: upgrades, security patches and capacity planning.
- A common mistake is choosing AKS by default because it is popular, without the skills to run it.
- Another is picking a service just because it is Spring-specific, then facing a forced migration.

**How I'd monitor it**
- Use Azure Monitor, Application Insights and Log Analytics for logs. Splunk can also receive them if the company standardizes on it.
- Watch replica count, restarts, CPU and memory, p95 latency and error rate.
- Expose Spring Boot Actuator health endpoints for the platform's health checks.
- Track monthly cost per service to confirm scaling saves money.

**Follow-ups to expect**
- *When would you choose AKS over Container Apps?* -> When you need a service mesh, custom operators, or deep control over networking and scheduling, and the team can afford to run Kubernetes.
- *How do you scale on Kafka lag in Container Apps?* -> Use a KEDA Kafka scaler rule that adds replicas as consumer lag grows. This is capped by the topic's partition count.
- *How do you avoid cold starts?* -> Set a minimum replica count of 1 or more, and optionally use faster-starting builds such as GraalVM native image.

**60-second answer**
Azure has four main options for a Spring Boot microservice. App Service is the simplest PaaS: you deploy and Azure runs it. Container Apps runs containers serverlessly with KEDA-based scaling, including scale-to-zero, and optional Dapr, without exposing Kubernetes. AKS is managed Kubernetes with full control but more operational work. Azure Spring Apps is Spring-specific, but Microsoft has announced its retirement, so I'd verify the current status and not start new work on it. For most teams I'd containerize the app, push it to ACR and use Container Apps. I'd choose AKS only when we need a mesh, custom operators or deep control. I'd set a minimum replica count to avoid JVM cold starts and monitor through Azure Monitor.

### Q4 [mid] Azure messaging: Service Bus vs Event Hubs vs Event Grid?
tags: azure, service-bus, event-hubs, event-grid, messaging, kafka, basics

**Start here: the concepts**
- **Message vs event:** A *message* is a command or piece of work ("charge this card") that one receiver must handle. An *event* is a fact that something happened ("a file was uploaded") that anyone may react to.
- **Broker:** A middleman that stores what a sender sends until receivers are ready. It decouples them, so a slow or crashed receiver does not break the sender.
- **Queue and topic:** A queue delivers each message to one consumer. A topic with subscriptions gives every subscription its own copy (publish/subscribe).
- **Dead-letter queue (DLQ):** A side queue where messages that repeatedly fail go. This stops one bad message from blocking everything and lets you inspect it later.
- **Session:** A group key (e.g. an order ID). Service Bus delivers all messages with that key in order to one receiver at a time.
- **Transaction:** Several broker operations (e.g. complete one message, send another) succeed or fail together.
- **Scheduled delivery:** A message that becomes visible only at a chosen future time.
- **Event streaming:** A long, append-only log of events that consumers read at their own pace and can re-read.
- **Partition:** One ordered slice of the log. More partitions means more parallel throughput. Order is guaranteed only inside a partition.
- **Consumer group:** An independent set of readers with its own position, so analytics and billing can read the same stream separately.
- **Kafka protocol compatible:** Existing Kafka clients can talk to Event Hubs by changing connection settings, so you do not need to rewrite them. It is not a full Kafka cluster, so some features differ by tier.
- **Event Grid:** A router that *pushes* small notifications (usually over HTTP) from sources such as Blob Storage to handlers such as Functions or webhooks.

**The live scenario**
An online shop on Azure ran three flows. Orders (about 200/s) needed ordered, reliable processing. Clickstream (about 50,000 events/s) fed analytics. When a product image was uploaded, a thumbnail had to be created. Early on, the team put orders on a streaming log and had no DLQ. One malformed order kept failing and held up processing, and nobody could easily set it aside. After the redesign, orders went to Service Bus, clicks to Event Hubs, and uploads to Event Grid.

**What the interviewer is really checking**
Whether you pick the service by the *shape of the problem* (command vs stream vs notification) and not by name, and whether you know what each one guarantees.

**How I answer it**
1. **Ask "what is being sent?"** A command that must be processed exactly by one worker points to Service Bus. A huge flow of facts to be analysed or replayed points to Event Hubs. A "something happened" notification points to Event Grid.
2. **Service Bus for business workflows.** It has queues, topics, sessions (ordering per key), DLQ, transactions and scheduled delivery. These features exist because business messages must not be lost or block each other. It is similar to RabbitMQ, or SQS plus SNS.
3. **Event Hubs for throughput.** It splits the stream into partitions and lets consumer groups read independently by tracking their position (checkpoint). It is similar to Kafka or Kinesis. Existing Kafka apps can often move over by changing connection settings:
   ```
   bootstrap.servers=<namespace>.servicebus.windows.net:9093
   security.protocol=SASL_SSL
   ```
   The Kafka endpoint needs the Standard tier or above.
4. **Event Grid for reaction.** It routes events from Azure resources (and custom sources) to handlers, similar to AWS EventBridge. It pushes events and retries delivery, so it suits "when X happens, trigger Y", not bulk data transport.
5. **Combine them** when needed, e.g. Event Grid notices an upload and a handler puts a work item on Service Bus.

**Trade-offs and what can go wrong**
- Using Event Hubs as a work queue: there is no per-message DLQ or completion, so a bad record is awkward to handle, and you must manage checkpoints yourself.
- Using Service Bus for massive telemetry: it is costlier and not built for replaying huge streams.
- Delivery is at-least-once in all three, so handlers must be idempotent (safe to run twice).
- Event Hubs: too few partitions limits parallelism, and the count is hard to change on lower tiers. Event Grid events are small notifications, not large payloads.
- "Kafka compatible" does not mean every Kafka feature is available.

**How I'd monitor it**
- **Service Bus:** active message count, dead-letter count, throttled requests.
- **Event Hubs:** incoming vs outgoing messages, throttled requests, and consumer lag (latest sequence number minus checkpoint).
- **Event Grid:** delivery failures, dead-lettered events.
- Alert on a growing DLQ or lag in Azure Monitor, and search application logs (e.g. in Splunk) by message or correlation ID.

**Follow-ups to expect**
- *How do you keep order?* -> Service Bus: use sessions with a key. Event Hubs: send related events to the same partition with a partition key.
- *Event Hubs vs Kafka?* -> Event Hubs is a managed service that speaks the Kafka protocol, so there is less operations work. It is not identical to Kafka, so check which features you need.
- *What if a handler gets the same event twice?* -> Make it idempotent, e.g. by storing processed IDs. Service Bus can also detect duplicates for you.

**60-second answer**
All three move data, but for different jobs. Service Bus is an enterprise message broker with queues, topics, sessions, dead-lettering, transactions and scheduled delivery, so I use it for business commands like orders. Event Hubs is a high-throughput streaming log with partitions and consumer groups, and it speaks the Kafka protocol, so I use it for telemetry and clickstream. Event Grid pushes lightweight "something happened" events from Azure resources to handlers, so I use it for reactions like processing an uploaded file. Delivery is at-least-once everywhere, so I make handlers idempotent and watch DLQ size and consumer lag.

### Q5 [mid] Azure data services for a Java app?
tags: azure, cosmos-db, azure-sql, postgresql, redis, blob-storage, partition-key, basics

**Start here: the concepts**
- **Managed service:** Azure runs the servers, patching, backups and failover. You only use the database. It exists so your team does not spend time on database operations.
- **Relational database (Azure SQL, Azure Database for PostgreSQL Flexible Server):** data lives in tables with fixed columns, and you use SQL, joins and transactions. Use it when data is structured and consistency matters, such as orders and payments. A Java app usually reaches it through JDBC, or Spring Data JPA on top of it.
- **Zone-redundant HA (high availability):** the database keeps a standby copy in another datacenter ("availability zone") in the same region. If one zone fails, Azure switches over automatically.
- **Read replica / readable secondary:** a copy of the database that serves only reads. It takes reporting and read-heavy traffic off the main database. It lags slightly behind, so it can return slightly old data.
- **Cosmos DB:** a managed NoSQL database that stores JSON-like documents and can replicate across Azure regions worldwide. "Multi-model" means it offers several APIs, such as NoSQL (its native one), MongoDB and Cassandra.
- **Consistency levels:** a dial between "always the latest data" and "fastest and cheapest". From strongest to weakest:
  - **Strong:** reads always see the latest write.
  - **Bounded staleness:** reads may lag by a set amount of time or number of updates.
  - **Session:** within one client's session you always see your own writes. This is the default.
  - **Consistent prefix:** reads never see writes out of order.
  - **Eventual:** reads may be stale for a while, but replicas converge.
- **RU (Request Unit):** Cosmos DB's currency for throughput. Every read, write or query costs some RUs, and you buy RUs per second. If you exceed your budget, you get an HTTP 429 ("too many requests").
- **Partition key:** a field (for example `customerId`) whose value decides which physical partition stores a document. It spreads data and load across machines. You cannot change it on an existing container. Documents with the same key value form a *logical partition*, which is capped at 20 GB.
- **Blob Storage:** cheap object storage for files such as images, PDFs and exports.
- **Redis cache:** a managed in-memory key-value store. It is very fast and is used to avoid repeating slow database reads.

**The live scenario**
An order service handles about 2,000 requests/second at peak. The team picks Cosmos DB and sets the partition key to `orderStatus`, because it looked natural. Almost all active orders have status `PENDING`, so one logical partition takes nearly all the traffic. That partition has a per-partition throughput ceiling, so the app starts returning 429s even though the account has plenty of unused RUs overall. Latency rises from 20 ms to over 800 ms. The team recreates the container with `customerId` as the key, which spreads load evenly, and the 429s disappear. Because the key cannot be changed in place, the fix needed a data migration.

**What the interviewer is really checking**
Whether you pick a data service by workload (relational vs document vs cache vs files) instead of listing names, and whether you understand Cosmos DB's two big levers: partition key and consistency level.

**How I answer it**
1. **Match the service to the data.** Orders, payments and anything needing joins and transactions go in Azure SQL or PostgreSQL Flexible Server, because relational databases give strong transactional guarantees.
2. **Make the relational tier survive failures.** Enable zone-redundant HA so a datacenter outage triggers automatic failover. Add read replicas (Flexible Server) or readable secondaries (Azure SQL) for read-heavy traffic, accepting a little replica lag.
3. **Use Cosmos DB for high-volume, flexible-shape or globally distributed data**, such as user profiles, catalogs and event data. It scales horizontally and replicates to the regions where your users are.
4. **Choose the partition key first.** Pick a field with many distinct values that appears in most queries, such as `customerId`. That spreads load and keeps queries inside one partition, which is cheaper. A low-cardinality key creates a hot partition.
5. **Pick the weakest consistency level the business accepts.** Session is a good default. Strong costs more latency and RUs, especially across regions.
6. **Add Redis in front of hot reads** so repeated lookups skip the database, and **put files in Blob Storage** instead of database rows, because it is far cheaper per GB.

**Trade-offs and what can go wrong**
- A bad partition key is the classic Cosmos mistake: hot partitions, 429s, and a costly migration. Cross-partition queries also cost more RUs.
- Provisioning RUs for peak wastes money off-peak. Autoscale or serverless helps, depending on the traffic pattern.
- Stronger consistency means higher latency and cost. Strong consistency is also not available in combination with multi-region writes.
- Redis can serve stale data if invalidation is sloppy, and the cache is not the source of truth.
- Read replicas lag, so "write then immediately read from replica" can return old data.
- Using Cosmos DB for relational, join-heavy data is a poor fit.

**How I'd monitor it**
- **Cosmos DB (Azure Monitor):** Normalized RU Consumption (per partition, to spot hot keys), 429 count and server-side latency.
- **Azure SQL/PostgreSQL:** CPU, storage, connection count and replica lag.
- **Redis:** cache hit ratio, memory use and evicted keys.
- **Splunk:** search the app logs for throttling, for example `index=app "CosmosException" statusCode=429 | timechart count by service`, and alert if it stays above a threshold.

**Follow-ups to expect**
- *What makes a good Cosmos DB partition key?* -> High cardinality, even traffic spread, and present in most queries so they hit a single partition. It is immutable, so choose carefully.
- *Which consistency level would you use by default?* -> Session. Users see their own writes, and it is cheaper and faster than strong.
- *Why not put everything in Cosmos DB?* -> Join-heavy, transactional data fits relational databases better, and Cosmos queries across partitions get expensive.

**60-second answer**
I choose Azure data services by workload. Transactional, structured data like orders goes in Azure SQL or PostgreSQL Flexible Server, with zone-redundant HA for failover and read replicas for read-heavy traffic. For high-volume, flexible or globally distributed data I use Cosmos DB, where throughput is bought in Request Units and consistency is tunable from strong to eventual, with session as my default. The most important Cosmos decision is the partition key: it must have many distinct values and match my queries, otherwise one hot partition causes 429 throttling. I add Redis to cache hot reads and Blob Storage for files. I watch RU consumption, 429s, replica lag and cache hit ratio, and alert on throttling in Splunk.

### Q6 [mid] How would you monitor a Java app on Azure?
tags: azure, application-insights, azure-monitor, kql, observability, java, basics

**Start here: the concepts**
- **Monitoring vs observability:** Monitoring tells you *that* something is wrong (error rate is up). Observability gives you enough data (metrics, logs, traces) to find out *why*.
- **Azure Monitor:** The umbrella Azure service that collects, stores, queries and alerts on telemetry. Platform metrics such as CPU and memory of your App Service or AKS cluster arrive automatically.
- **Application Insights (App Insights):** The Azure Monitor feature for application-level data: requests, response times, failures, dependency calls and exceptions. It exists because infrastructure graphs cannot tell you that one endpoint is slow.
- **Java agent:** A JAR attached with `-javaagent` at JVM start. It instruments common libraries (HTTP, JDBC, Kafka clients) without code changes. That is called auto-instrumentation.
- **Trace:** The path of one request across services. Each step is a span. A **dependency** is a call your app makes to something else, such as a database, REST API or queue.
- **Log Analytics and KQL:** Log Analytics is the workspace where logs and telemetry are stored. KQL (Kusto Query Language) is its query language, similar to a Splunk search. Current App Insights resources are workspace-based, so their data lives here.
- **Alerts, dashboards, Workbooks:** Alerts notify you when a rule fires. Dashboards and Workbooks are saved visual views, and Workbooks are more interactive.
- **OpenTelemetry (OTel):** A vendor-neutral standard for producing telemetry. You can send the same data to Azure, Datadog or Splunk. The App Insights Java agent is itself built on OTel.

**The live scenario**
An order service on Azure (App Service or AKS) handles about 300 requests per second. After a release, customers report a slow checkout, but CPU and memory look normal. In App Insights, the p95 latency of `POST /orders` has jumped from 300 ms to 4 s. The dependency view shows that calls to Azure SQL are taking 3.5 s. A KQL query finds one new query without an index. The team fixes it in 20 minutes. Without application-level telemetry, they would have been guessing from CPU graphs.

**What the interviewer is really checking**
Do you know which Azure tool answers which question? Can you describe a practical flow from alert to root cause, instead of just listing service names?

**How I answer it**
1. **Attach the App Insights Java agent.** It gives traces, dependencies and exceptions with no code changes, so every team gets the same baseline quickly.
   ```
   java -javaagent:applicationinsights-agent-3.x.jar -jar app.jar
   # plus env var APPLICATIONINSIGHTS_CONNECTION_STRING
   ```
2. **Watch infrastructure with Azure Monitor metrics.** CPU, memory, restarts and instance count show whether the platform is healthy. On AKS, Container Insights adds pod-level data.
3. **Send logs to Log Analytics and query with KQL.** Metrics show the symptom, and logs and traces show the cause. Use structured logs with a correlation or trace ID so you can follow one request.
4. **Create alerts on user-facing symptoms.** Examples are failed-request rate, p95 latency and dependency failures. Route them to a team channel or on-call tool. Symptom alerts catch real impact, while raw CPU alerts are noisy.
5. **Build a dashboard or Workbook.** Show the request rate, error rate, latency and dependency health (the "golden signals") on one screen, so anyone can read service health during an incident.
6. **Prefer OpenTelemetry for vendor neutrality.** If you may move to Datadog or Splunk, instrument with OTel standards so you are not locked in. Azure's OTel-based Java agent and distro support this.

**Trade-offs and what can go wrong**
- **Cost:** Ingestion is billed by data volume. Verbose logging or 100% trace capture gets expensive. Use sampling and log levels, and set retention deliberately.
- **Agent overhead:** It is usually small but not zero, so load-test with it on.
- **Alert fatigue:** Too many alerts means people ignore them. Alert on symptoms, not every metric.
- **Sampling can hide rare failures.** Check what your sampling settings drop.
- **Lock-in:** Proprietary SDKs make switching vendors harder. Check current Microsoft docs, as the older classic SDKs are being replaced by the OTel-based options.
- **Fragmented tooling:** If other teams use Splunk or Datadog, agree on one correlation ID.

**How I'd monitor it**
- Request rate, failure rate, p95/p99 duration per endpoint.
- Dependency duration and failure rate (database, Kafka, downstream APIs).
- JVM metrics: heap, GC pauses, thread count.
- Platform: CPU, memory, pod restarts, instance count.
- KQL checks on `requests`, `dependencies` and `exceptions` tables, for example p95 duration grouped by 5-minute bins.
- Availability tests (synthetic pings) and alerts on the golden signals.

**Follow-ups to expect**
- *How is this different from CloudWatch + X-Ray?* -> It is broadly equivalent. Azure Monitor and Log Analytics correspond to CloudWatch metrics and logs, and App Insights to X-Ray plus application metrics.
- *How do you keep costs under control?* -> Use sampling, appropriate log levels, daily caps and shorter retention for noisy data.
- *How do you trace a request across microservices?* -> Propagate the trace context (W3C `traceparent` header). The agent does this automatically, and you log the trace ID.

**60-second answer**
I would attach the Application Insights Java agent so I get requests, dependencies, exceptions and traces without code changes. Azure Monitor gives me platform metrics like CPU, memory and restarts, and I send logs to Log Analytics, where I query them with KQL. I would alert on user-facing symptoms such as error rate and p95 latency, and build a dashboard or Workbook for the golden signals. During an incident, I start from the alert, look at the slow endpoint, check the dependency view, then use KQL and the trace ID to find the cause. I would watch ingestion cost with sampling, and I would use OpenTelemetry if we want vendor neutrality. It is similar to CloudWatch with X-Ray, or Datadog.

### Q7 [mid] Azure Functions vs AWS Lambda - differences that matter?
tags: azure-functions, aws-lambda, serverless, cold-start, durable-functions, hosting-plans, basics

**Start here: the concepts**
- **Serverless function:** a small piece of code the cloud runs for you when an event arrives. You don't manage servers, and the platform adds or removes copies of your code as load changes.
- **Trigger:** the event that starts a function, such as an HTTP call, a queue message, a timer, a new file in Blob/S3 storage, or an Event Hub message. Both platforms have the same idea but different names (Lambda uses SQS, S3, EventBridge schedules, Kinesis).
- **Cold start:** when no warm copy of your code exists, the platform must start a new instance, load the runtime and your code, and run initialisation before handling the request. This adds latency, and it is worst for Java because of JVM and framework startup.
- **Hosting plan (Azure):** the rule for how your function app is run and billed.
  - *Consumption* scales to zero and you pay per execution, but it has cold starts.
  - *Premium* keeps pre-warmed and always-ready instances, so cold starts are largely avoided. It costs more because you pay for those instances.
  - *Dedicated* runs on an App Service plan of VMs you already pay for.
  - Lambda has no plans. You set memory and timeout per function. Its cold-start tools are *provisioned concurrency* and, for Java, *SnapStart*.
- **Durable Functions:** an Azure extension for stateful workflows. You write the orchestration as ordinary code, and the framework saves progress so it can wait, retry or resume. AWS **Step Functions** does a similar job, but you define the workflow as a state-machine definition, not as code.
- **Connection reuse:** objects created outside the handler survive between calls on a warm instance, so you don't reconnect on every invocation.

**The live scenario**
An order service handles about 50 requests a second, and a nightly bulk import pushes it to about 2,000 messages a second. The team ran Java Functions on the Consumption plan. Most calls took 120 ms, but the first call after idle took about 6 seconds, and the checkout API timed out on those. During the import, the scaled-out instances each opened their own database connections, and the database hit its connection limit. They moved the HTTP functions to Premium, kept the import on Consumption, and reused one shared client per instance.

**What the interviewer is really checking**
Whether you know the two are conceptually similar but differ in hosting, scaling and workflow models, and whether you can choose between them for a workload and handle cold starts and connections.

**How I answer it**
1. **Say they are the same idea.** Both run event-triggered code and scale automatically. This shows you understand the model before the differences.
2. **Compare hosting.** Azure has Consumption, Premium and Dedicated plans, and Lambda has per-function memory and timeout settings. Pick the plan by latency need and cost: scale-to-zero is cheap but cold, pre-warmed is faster but you pay for idle capacity.
3. **Explain cold starts for Java.** The JVM and frameworks are slow to start. On Azure, use Premium. On AWS, use provisioned concurrency or SnapStart. Also keep dependencies small.
4. **Cover workflows.** Durable Functions let you write long-running orchestration in code. Step Functions is a managed state machine. Code is easier to test and refactor, while a state machine is easier to see and audit.
5. **Cover connections.** Create HTTP, database and messaging clients once, outside the function body, so warm calls reuse them:
```java
private static final HttpClient CLIENT = HttpClient.newHttpClient();
```
6. **Mention scaling limits.** Many instances multiplied by connections each can overwhelm a database. Cap concurrency or use pooling or a proxy.

**Trade-offs and what can go wrong**
- Premium and provisioned concurrency remove most cold starts but cost money even when idle.
- Scale-out can overload downstream systems such as databases and third-party APIs.
- Timeouts differ by plan and platform, so check current limits before putting long jobs in a function.
- Durable orchestrator code must be deterministic, because it is replayed. Avoid random values, current time and direct I/O inside it.
- Static clients that are never refreshed can hold stale DNS or credentials.

**How I'd monitor it**
- Azure: Application Insights for duration, failures, and cold-start traces. Watch the instance count.
- AWS: CloudWatch for duration, errors, throttles, concurrent executions, and `Init Duration` in REPORT log lines.
- Downstream: database connection count and queue age.
- Splunk: search for first-call latency outliers per instance, and alert on a rising p99 or throttling.

**Follow-ups to expect**
- *How do you cut Java cold starts?* -> Use Premium on Azure, or provisioned concurrency or SnapStart on AWS. Trim dependencies and avoid heavy classpath scanning.
- *Durable Functions vs Step Functions?* -> Durable defines the workflow in code and is replayed. Step Functions defines it as a managed state machine with a visual view.
- *Why is connection reuse important?* -> It avoids reconnect latency, but with large scale-out you still need to limit total connections.

**60-second answer**
Azure Functions and Lambda are the same idea: code that runs when a trigger fires, such as HTTP, a queue, a timer, a file, or Event Hub. The differences are in the details. Azure has hosting plans: Consumption scales to zero but has cold starts, Premium keeps pre-warmed instances, and Dedicated runs on VMs you already pay for. Lambda uses per-function settings and offers provisioned concurrency or SnapStart against cold starts. Durable Functions give stateful workflows written in code, much like Step Functions, which uses a state-machine definition. For Java, I'd reduce cold starts, create clients once so warm calls reuse them, and cap scale-out so databases aren't overloaded.

### Q8 [mid] How do you secure an application in the cloud (any provider)?
tags: cloud-security, iam, secrets-management, private-networking, encryption, devsecops, basics

**Start here: the concepts**
- **Shared responsibility:** The provider secures the data centres and hardware. You secure your identities, configuration, network rules, data and code. Most cloud breaches come from the customer side, such as a public storage bucket or a leaked key.
- **Identity and least privilege:** An identity is anything that can call a cloud API, either a person or an application (a role or managed identity). Least privilege means giving it only the permissions it needs, so a stolen identity can do little damage.
- **Long-lived keys vs short-lived credentials:** A static access key never expires and can sit in Git for years. Roles and managed identities hand out temporary tokens that expire automatically, so there is nothing permanent to leak.
- **Private networking:** A VPC (AWS) or VNet (Azure) is your private network in the cloud. A private endpoint gives a cloud service (database, storage) a private IP inside that network, so traffic never crosses the public internet.
- **Secrets vault and rotation:** A vault (AWS Secrets Manager, Azure Key Vault) stores passwords and API keys centrally, with access control and audit. Rotation means changing them regularly, so a leaked secret stops working quickly.
- **Encryption in transit and at rest:** In transit means TLS on the wire. At rest means disks and databases are stored encrypted. Managed keys (a key service such as KMS or Key Vault) handle key storage and rotation for you.
- **WAF / gateway:** A Web Application Firewall filters malicious web requests (SQL injection, bot floods). An API gateway adds authentication and rate limits. Both sit at the edge, before your app.
- **Policy-as-code:** Rules written as code that the cloud enforces automatically, such as Azure Policy ("no public storage") or AWS Service Control Policies (SCPs), which cap what any account in an organisation may do.
- **Audit logs:** A record of who called which API and when (AWS CloudTrail, Azure Activity Log).
- **Vulnerability scanning:** Tools check container images and libraries against lists of known security flaws (CVEs).

**The live scenario**
A team of 12 runs a payments API on Kubernetes. A developer commits a database password to a private repo, and months later a contractor's laptop is compromised. With a static password and a publicly reachable database, the attacker could connect from anywhere. Because the team had already moved the password into a vault, given pods a managed identity, and put the database behind a private endpoint, the leaked value was useless: it was rotated, and the database was not reachable from the internet. The audit logs showed the failed attempts within minutes.

**What the interviewer is really checking**
Whether you think in layers (identity, network, data, edge, governance) rather than naming one tool. Also whether you understand that a breach in one layer should not become a breach of everything.

**How I answer it**
1. **Separate environments into their own accounts/subscriptions.** Dev, test and prod each get their own. This limits the blast radius, because a mistake or compromise in dev cannot touch prod, and permissions can be stricter in prod.
2. **Use least-privilege identities with no long-lived keys.** Apps use roles or managed identities, and people use SSO with MFA. A leaked token expires, and a narrow role limits what it can do.
3. **Keep services on private networking.** Databases and internal services get private endpoints and no public IP. Only the gateway is exposed. Attackers cannot attack what they cannot reach.
4. **Put secrets in a vault with rotation.** Never put them in code, images or environment files. The app fetches them at runtime, and rotation shrinks the window in which a leak is useful.
5. **Encrypt in transit and at rest with managed keys.** Use TLS everywhere and turn on storage and database encryption. Managed keys avoid homemade key handling, which is easy to get wrong.
6. **Add a WAF or gateway at the edge.** It blocks common attacks and enforces authentication and rate limits before traffic reaches the app.
7. **Enforce rules with policy-as-code.** Block public buckets or unapproved regions automatically. Humans forget, but policies do not. Note that an SCP only sets the maximum allowed permissions, it does not grant any.
8. **Scan images and dependencies in CI/CD.** Fail the build on critical findings, so known flaws never reach production.
9. **Turn on audit logs and alert on them.** You cannot investigate or detect what you did not record.

**Trade-offs and what can go wrong**
- Tight permissions slow developers down at first, and over-broad "temporary" admin roles tend to become permanent.
- Private endpoints add cost and DNS complexity, and misconfigured routing causes outages.
- Rotation can break apps that cache secrets, so test it.
- Scanners produce noise, so set severity thresholds or people will ignore them.
- Common mistake: believing the provider handles everything, or securing prod but leaving dev wide open with real data.

**How I'd monitor it**
- Send audit logs (CloudTrail, Activity Log) to a central tool such as Splunk. Alert on root or admin logins, logins without MFA, policy or role changes, and spikes in access-denied errors.
- Track vault access, and alert on unusual reads.
- Run a cloud posture or compliance dashboard to catch public resources and policy violations.
- Track scanner findings by severity and time to fix.
- Check WAF block rates for attack patterns.

**Follow-ups to expect**
- *How does a pod get cloud access without a stored key?* -> It uses a workload identity (for example IAM Roles for Service Accounts on EKS, or Azure Workload Identity). The cluster issues a short-lived token tied to the pod's service account.
- *Difference between a security group and a WAF?* -> A security group filters by IP and port (network level). A WAF inspects HTTP content for attacks (application level).
- *How do you handle a leaked secret?* -> Rotate it immediately, check audit logs for misuse, find how it leaked, and fix that path, for example with a pre-commit secret scan.

**60-second answer**
I secure cloud apps in layers. First, each environment gets its own account or subscription to limit blast radius. Apps and people use least-privilege identities with short-lived credentials, not permanent keys. Databases and internal services sit behind private networking and private endpoints, with only a gateway or WAF exposed. Secrets live in a vault and are rotated, and data is encrypted in transit and at rest with managed keys. Policy-as-code such as Azure Policy or AWS SCPs blocks risky configuration automatically, and CI scans images and dependencies for known vulnerabilities. Finally, I send audit logs to a central tool like Splunk and alert on suspicious activity, because prevention alone is never enough.

### Q9 [mid] How would you build a CI/CD pipeline for Azure?
tags: azure, ci-cd, github-actions, azure-devops, docker, aks, helm, oidc, basics

**Start here: the concepts**
- **CI/CD**: Continuous Integration automatically builds and tests every code change. Continuous Delivery/Deployment automatically ships the tested result to environments. It exists so releases are small, repeatable and not dependent on one person's laptop.
- **Pipeline**: a scripted sequence of stages (build, test, scan, publish, deploy) that runs on every commit. Azure DevOps Pipelines, GitHub Actions and Jenkins all do this. Jenkins is self-hosted, so you run and patch it yourself.
- **Container image**: a packaged app plus its runtime, built from a Dockerfile, so it runs the same everywhere.
- **Azure Container Registry (ACR)**: a private store for images in Azure.
- **Security scan**: automated checks for known vulnerabilities in dependencies and images, and for secrets committed by mistake.
- **AKS**: Azure Kubernetes Service, the managed cluster that runs the containers.
- **Helm / Kustomize**: tools that turn Kubernetes YAML into reusable, per-environment config. Helm uses templates and values. Kustomize uses overlays that patch a base.
- **Bicep / Terraform**: Infrastructure as Code (IaC). They create the cloud resources themselves (AKS, ACR, databases, networks). They create the platform; Helm and Kustomize deploy the app onto it.
- **Approval gate**: a manual check before a stage proceeds.
- **Canary / blue-green**: canary sends a small share of traffic to the new version first. Blue-green runs old and new side by side and switches traffic between them.
- **OIDC federation**: the pipeline proves its identity to Azure with a short-lived token from GitHub or Azure DevOps. No long-lived password is stored, so there is nothing to leak.

**The live scenario**
A team of 12 ships an order service to AKS. Deploys are manual, take 2 hours and happen monthly. Last quarter a service principal secret stored in the pipeline expired on a Friday night, and the release failed. Earlier, a bad build reached production because staging ran a different image than the one tested. They moved to an automated pipeline: roughly 15 minutes to staging, daily production releases, no stored cloud secrets.

**What the interviewer is really checking**
Whether you can describe a safe path from commit to production (build once, scan, promote, gate, roll out gradually) and handle credentials securely. Naming tools is the minimum.

**How I answer it**
1. **Pick the pipeline tool and trigger it on every pull request and merge.** Azure DevOps Pipelines or GitHub Actions fit well with Azure, and I've used GitHub Actions and Jenkins. Early feedback catches defects while they are cheap to fix.
2. **Build, unit test and scan.** Compile, run tests, then scan dependencies, code and the image. Fail the build on serious findings, so a vulnerable image never reaches the registry.
3. **Build the image once and push it to ACR, tagged with the commit SHA.** Every environment then runs the exact artifact that was tested. Rebuilding per environment is how "worked in staging" bugs happen. Deploy by digest or immutable tag, never `latest`.
4. **Authenticate with OIDC federation, not stored secrets.** I create a federated credential on a Microsoft Entra identity that trusts only my repo and branch or environment. The pipeline gets a short-lived token on each run. Nothing expires on a Friday night and nothing can be stolen from the pipeline settings.
```yaml
permissions: { id-token: write, contents: read }
- uses: azure/login@v2   # uses client-id, tenant-id, subscription-id; no secret
```
5. **Keep infrastructure and application deployment separate.** Bicep or Terraform create AKS, ACR and networking in their own reviewed pipeline. The app pipeline runs `helm upgrade` or `kubectl apply -k` with per-environment values. Infrastructure changes rarely, the app changes daily, and they carry different risk.
6. **Deploy to staging automatically and run smoke and integration tests.** This proves the deployment works in a production-like place.
7. **Add an approval gate before production.** Use an Azure DevOps environment check or a GitHub Environment with required reviewers. This gives a human checkpoint for regulated or high-risk changes.
8. **Release to production with canary or blue-green.** Canary: 5% of traffic, watch errors and latency, then 25%, then 100%. Blue-green: switch traffic only once the new stack is healthy. Rollback is then a traffic switch or `helm rollback`, not a rebuild.

**Trade-offs and what can go wrong**
- Heavy scans slow the pipeline; run quick ones on every PR and deeper ones nightly.
- Canary needs traffic splitting (ingress or service mesh) and good metrics. Blue-green temporarily doubles capacity cost.
- Database schema changes break rollback. Make them backward compatible (expand, then contract).
- Approval gates can become a bottleneck if everything needs manual sign-off.
- A federated credential scoped too broadly (any branch) weakens the security benefit.
- AKS must be allowed to pull from ACR (managed identity with the AcrPull role); otherwise you get `ImagePullBackOff`.

**How I'd monitor it**
- The DORA metrics: deployment frequency, lead time, change failure rate and time to restore.
- Pipeline duration and flaky-test rate.
- During a canary: error rate, p95 latency and pod restarts via Azure Monitor and Splunk. Alert and auto-halt if errors exceed the baseline.
- Splunk search on deployment events, for example by `release` or image SHA, to correlate an error spike with a release.

**Follow-ups to expect**
- *Why OIDC over a service principal secret?* -> Tokens are short-lived and scoped to a repo or environment, so there is no secret to rotate or leak.
- *How do you roll back?* -> Redeploy the previous immutable image with `helm rollback`, or switch traffic back to the blue environment.
- *Helm or Kustomize?* -> Helm for packaging and versioned releases with templating; Kustomize for simple overlays without templates. Many teams pick one and stay consistent.

**60-second answer**
I'd use GitHub Actions or Azure DevOps Pipelines. On each commit it builds, runs tests and scans, then pushes one image tagged with the commit SHA to Azure Container Registry. That same image is promoted through every environment. The pipeline logs into Azure with OIDC federation, so there are no stored secrets. Helm or Kustomize deploys the app to AKS staging, and Bicep or Terraform manage the infrastructure separately. After smoke tests and an approval gate, I release to production with canary or blue-green and watch error rate and latency. If they degrade I roll back to the previous image.

### Q10 [mid] Explain Infrastructure as Code and why.
tags: infrastructure-as-code, iac, terraform, cloudformation, bicep, devops, basics

**Start here: the concepts**
- **Infrastructure**: the servers, networks, load balancers and databases your application runs on.
- **Infrastructure as Code (IaC)**: you describe that infrastructure in text files instead of clicking through a cloud console. A tool reads the files and creates or changes the real resources to match. It exists because hand-clicked setups can't be repeated exactly, reviewed or traced.
- **Declarative**: you write the end state you want ("one load balancer, one database"), not the steps. The tool works out the steps.
- **Tools**: Terraform (works across clouds), CloudFormation (AWS only) and Bicep (Azure only).
- **Version control**: the files live in Git, so every change has an author, a diff, a reviewer and a history.
- **Plan -> review -> apply**: `plan` previews what would be created, changed or destroyed. People review it. `apply` then makes the change.
- **State**: the tool's record of which real resources it manages. **Remote state** is stored in shared storage (for example an S3 bucket) instead of on one laptop. **Locking** lets only one run change the state at a time, so two people can't corrupt it.
- **Modules**: reusable packages of infrastructure code, for example a "standard service" module used by many teams.
- **Drift**: the real environment no longer matches the code, usually because someone changed it by hand. **Drift detection** finds those differences.

**The live scenario**
(Numbers are illustrative.) A team of six runs a payments API in dev, staging and prod. During an incident at night, an engineer raises the load balancer idle timeout in the console. Nobody records it. Three weeks later, staging is rebuilt by hand from a wiki page and is missing that setting. Tests pass in staging, but prod behaves differently. The rebuild also takes two days and the environments differ in about ten small ways. After moving to IaC, a new environment takes about 30 minutes from the same code, and the timeout is a reviewed line in Git.

**What the interviewer is really checking**
Whether you understand IaC as a way of working (review, repeatability, audit, safe change), not just "Terraform syntax". Also whether you know the practical risks: state, drift and secrets.

**How I answer it**
1. **Define it simply.** Infrastructure is described in version-controlled files, so it is code like any other. The reason is that manual setups can't be reproduced or explained later.
2. **Name the benefits.**
   - *Reproducible*: the same code builds dev, staging and prod the same way.
   - *Reviewable*: a pull request shows exactly what will change before it happens.
   - *Auditable*: Git history answers who changed what and why.
3. **Describe the workflow.** Plan, then review, then apply, ideally from a CI/CD pipeline. The reason is that the plan shows destructive changes, such as "this database will be replaced", before they happen.
   ```
   terraform plan -out=tfplan   # preview, attach to the pull request
   terraform apply tfplan       # apply exactly what was reviewed
   ```
4. **Protect the state.** Keep it remote with locking. The reason is that a local state file is lost with a laptop, and two simultaneous applies can corrupt it.
5. **Reuse with modules.** One reviewed module for "service behind a load balancer" avoids dozens of slightly different copies.
6. **Detect drift.** Run `plan` on a schedule and alert on unexpected differences. Then either fix the code or revert the manual change.
7. **Give a concrete example.** If it's true for you: "In a hackathon, our agent generated Terraform for ECS Fargate, an RDS database and an ALB. I read the plan before applying, because generated code can include wrong or risky settings."

**Trade-offs and what can go wrong**
- There is a learning curve, and the state file needs care.
- State can contain secrets, so encrypt it and restrict access. Never commit secrets to the code.
- Manual console fixes cause drift. During an incident, make the fix and then back-port it to code.
- Applying without reading the plan can destroy a database. Use deletion protection and approvals for production.
- Huge single states are slow and risky, so split them by environment and component.
- Tool choice: Terraform is multi-cloud, while CloudFormation and Bicep integrate tightly with their own cloud.

**How I'd monitor it**
- Scheduled `plan` runs in CI that fail or alert when drift appears.
- Pipeline logs and approval records for every apply.
- Cloud audit logs (such as CloudTrail on AWS) to catch console changes made outside IaC.
- Alerts on lock contention or failed applies.

**Follow-ups to expect**
- *What happens if two people apply at once?* -> Without locking, state can be corrupted. Remote state with locking makes the second run wait or fail.
- *How do you handle secrets?* -> Keep them out of code and pull them from a secrets manager. Encrypt the state, since it may contain sensitive values.
- *Declarative vs imperative?* -> Declarative describes the end state and the tool computes the steps. Imperative scripts list the steps and can't easily tell what already exists.

**60-second answer**
Infrastructure as Code means describing servers, networks and databases in version-controlled files, using tools like Terraform, CloudFormation or Bicep, instead of clicking in a console. That makes environments reproducible, changes reviewable in pull requests, and history auditable. The workflow is plan, review, apply: the plan shows exactly what will change before anything happens. I keep state remote with locking so teams don't corrupt it, use modules to reuse proven patterns, and run scheduled plans to detect drift from manual changes. In a hackathon, an agent generated Terraform for ECS Fargate, RDS and an ALB, and I reviewed the plan before applying. The main risks are secrets in state and unreviewed applies, so I protect both.

### Q11 [senior] Cloud cost optimisation (FinOps) - what do you do?
tags: finops, cloud-cost, autoscaling, spot-instances, savings-plans, kubernetes, basics

**Start here: the concepts**
- **FinOps:** the practice of engineering and finance sharing responsibility for cloud spend. Cloud bills grow silently because anyone can create resources in minutes, so cost needs an owner.
- **Right-sizing:** matching CPU and memory to what a workload actually uses. Teams usually over-request "to be safe", and you pay for the unused part. For pods, the *request* is the amount Kubernetes reserves, and the node bill follows the requests, not the real usage.
- **Autoscaling:** adding or removing instances or pods as load changes, so you don't pay for peak capacity at 3 a.m.
- **Spot / low-priority instances:** spare cloud capacity sold at a big discount, but the provider can reclaim it on short notice. It suits work that tolerates interruption, such as stateless services with several replicas and retryable batch jobs. It does not suit a single-copy database.
- **Reserved instances / savings plans:** you commit to one or three years of usage or hourly spend in exchange for a lower price. They suit steady baseline load. Committing to unused capacity wastes money.
- **Lifecycle rules:** automatic policies that move old data to cheaper storage tiers (S3 or Azure Blob) or delete it after a set time.
- **Tagging:** labels such as team, service and environment on every resource. Without them you cannot say who owns a cost.
- **Egress:** data leaving the cloud, or crossing regions or zones, which is billed per GB. **Log-ingestion cost:** tools like Splunk charge by volume ingested, so noisy logs cost real money.

**The live scenario**
A platform runs about 40 microservices on Kubernetes. The monthly bill rose from $80k to $120k in a quarter while traffic grew only 10%. Cost reports showed that 30% of the spend could not be attributed to any team. Pods requested 2 CPUs but used about 0.4. A nightly batch ran on on-demand nodes, and old test clusters were still running. Debug logs from one service doubled Splunk ingestion. Cross-zone traffic was also adding up.

**What the interviewer is really checking**
Whether you treat cost as a continuous engineering discipline with a sensible order of actions (visibility, then waste removal, then commitments), rather than a list of discounts. They also want to see that you protect reliability while cutting cost.

**How I answer it**
1. **Make cost visible first.** I enforce tags (team, service, environment) and build cost reports per team. You cannot cut or assign what you cannot see, and owners act once they see their own bill.
2. **Set budgets and alerts.** Alerts fire at, say, 80% of the monthly budget or on anomalies. This catches surprises in days, not at month-end.
3. **Delete idle resources.** I remove unused clusters, unattached disks, old snapshots and forgotten test environments. This is the cheapest saving, with no risk to production.
4. **Right-size.** I compare pod requests with real usage (for example the p95 over two weeks) and lower them with some headroom. Do this before buying commitments, or you lock in the oversized footprint.
5. **Autoscale.** I use HPA for pods and a node autoscaler so capacity follows load. Minimum replicas stay high enough for availability.
6. **Use spot or low-priority for interruption-tolerant work.** Batch jobs and stateless services with several replicas go on spot, with retries and graceful shutdown. Spot capacity can disappear, so critical single-copy workloads stay on-demand.
7. **Commit only for the steady baseline.** After right-sizing, I buy reserved instances or savings plans to cover the minimum, always-on load, and leave the variable part on-demand.
8. **Apply lifecycle rules to storage.** Hot data stays in the standard tier. Old data moves to cheaper tiers, then expires, matching how often it is really read.
9. **Watch egress and log ingestion.** I keep traffic in-zone or in-region where possible and use caching or CDNs. I cut debug logging, sample noisy events and set retention per index.
10. **Make cost a design-review item.** Each new design states its expected monthly cost and data-transfer pattern, because fixing architecture later is far more expensive.

**Trade-offs and what can go wrong**
- Over-aggressive right-sizing causes CPU throttling, OOM kills and latency spikes. Keep headroom and roll changes out gradually.
- Spot interruptions hurt services that don't handle shutdown signals.
- Commitments lock you in. If traffic drops or you migrate, you still pay. Cover only the proven baseline.
- Cheaper storage tiers add retrieval fees and delays, and deleting data may break retention or compliance rules.
- Cutting logs too far removes the evidence you need during incidents.
- Savings that nobody tracks creep back.

**How I'd monitor it**
- The cloud cost tools (AWS Cost Explorer, Azure Cost Management) grouped by tag, plus the percentage of untagged spend.
- Cost per transaction or per customer, which shows efficiency better than the raw total.
- CPU and memory requested vs used per pod, and node utilisation.
- Commitment coverage and utilisation, and the spot interruption rate.
- Splunk ingestion volume per index and per source, plus alerts on sudden jumps.
- Data-transfer cost line items.

**Follow-ups to expect**
- *Savings plan or reserved instance?* -> Both trade commitment for discount. Reserved instances are tied to specific instance attributes. Savings plans commit to hourly spend and are more flexible. Either way, buy after right-sizing and only for the baseline.
- *How do you use spot safely?* -> Use it for stateless or retryable work, spread across instance types and zones, keep an on-demand base, and handle the termination notice with graceful shutdown.
- *How do you get teams to care?* -> Show each team its own cost, set budgets, review cost in design reviews, and track unit cost, not just the total.

**60-second answer**
I start with visibility: every resource is tagged by team and service, and budgets with alerts catch surprises early. Then I remove waste, such as idle environments and unused disks, and right-size instances and pods against real usage. I add autoscaling so capacity follows load, and I run batch and stateless replicated work on spot capacity, keeping critical stateful pieces on-demand. Only after that do I buy reserved instances or savings plans, for the steady baseline, so I don't commit to waste. I add lifecycle rules for storage and watch hidden costs like egress and log ingestion. Finally, I make cost a standard item in design reviews and track cost per transaction, so savings last without hurting reliability.

### Q12 [senior] Multi-region and disaster recovery strategies?
tags: multi-region, disaster-recovery, rto, rpo, failover, route53, active-active, basics

**Start here: the concepts**
- **Region / Availability Zone (AZ):** A region is a geographic area with cloud data centres (e.g. Frankfurt). An AZ is one isolated data centre group inside it. Multi-AZ survives a building failure; only multi-region survives a whole-region outage.
- **Disaster recovery (DR):** The plan and setup to bring the system back after a large failure, such as a region outage, bad deployment, deleted data or ransomware.
- **RTO (Recovery Time Objective):** How long the business accepts being down.
- **RPO (Recovery Point Objective):** How much recent data the business accepts losing, measured in time. An RPO of 5 minutes means losing at most the last 5 minutes of writes.
- **Failover / failback:** Moving traffic to the standby region, and later moving it back.
- **Global traffic routing:** A service that decides which region users reach. Route 53 and Azure Traffic Manager work at DNS level (they return different addresses). Azure Front Door is a global HTTP entry point that routes requests and can switch faster. DNS answers are cached, so DNS failover is only as fast as the TTL (cache lifetime) allows.
- **Replication:** Continuously copying data to another region. It is usually asynchronous, so the copy lags slightly and RPO is not zero.
- **IaC (Infrastructure as Code):** Describing servers, networks and clusters in files (Terraform, CloudFormation, Bicep) so an environment can be rebuilt reliably, not by hand.

**The live scenario**
An order platform earns about $20,000 per hour. One region has a networking outage lasting 3 hours. The team had only nightly backups in that same region. Rebuilding by hand took 9 hours, and they lost up to 24 hours of orders. The business then set targets of RTO 15 minutes and RPO 1 minute for checkout, and RTO 4 hours for reporting. The tiers below were chosen against those targets.

**What the interviewer is really checking**
Whether you start from business RTO/RPO and cost, not from technology, and whether you know that DR needs tested failover, not just replicated data.

**How I answer it**
1. **Set RTO/RPO per system first.** Each step up the ladder costs more, so only critical systems get the expensive options.
2. **Backup and restore:** Take backups and copy them to another region. This is the cheapest, but RTO is slow (hours) because you rebuild and restore from scratch. RPO is the age of the last backup.
3. **Pilot light:** Keep the data replicated and only a tiny core running in the second region. Compute is off or minimal. On disaster, scale it up. RTO is shorter, and cost is low.
4. **Warm standby:** Run a full but scaled-down copy that already serves health checks or some traffic. On disaster, scale up and switch. RTO is minutes.
5. **Active-active:** Both regions serve live traffic. It has the fastest recovery and near-zero downtime, but is the most complex and costly. The same data can be written in two regions, so you need conflict handling (last-write-wins, region ownership of records, or merge rules).
6. **Build the common parts:** global routing (Route 53, Traffic Manager or Front Door) with health checks, replicated data stores, and IaC so the standby is identical and can be rebuilt.
7. **Run regular failover drills.** An untested plan usually fails because of missing config, secrets, quotas or expired credentials in the standby region.

**Trade-offs and what can go wrong**
- Cost rises with each step up the ladder, as does operational complexity.
- Async replication means some data loss on failover. Synchronous replication across regions adds write latency.
- Multi-AZ is not DR, and same-region backups are not DR.
- Long DNS TTLs delay failover.
- Active-active can corrupt data if write conflicts are not designed for.
- Standby regions may lack capacity quota, so scale-up fails when you need it.
- Failback is often forgotten and can be riskier than failover.
- Dependencies (auth, third-party APIs, Kafka, DNS) may exist in one region only.

**How I'd monitor it**
- Replication lag per datastore, compared with the RPO.
- Health-check status and routing-endpoint health.
- Backup success and periodic restore tests.
- Drill results: measured RTO and RPO against targets.
- Standby capacity and quota checks.
- Alerts when the IaC state differs from what is deployed (drift).

**Follow-ups to expect**
- *How do you choose between warm standby and active-active?* -> If the RTO is minutes and some downtime is acceptable, warm standby is far simpler. Choose active-active only when downtime is near-unacceptable and the data model can handle multi-region writes.
- *Why not just use multi-AZ?* -> It protects against a data-centre failure, not a region-wide outage or a shared control-plane failure.
- *How do you handle data conflicts in active-active?* -> Avoid them by routing each user or record to a home region, or use conflict resolution rules such as last-write-wins or merges. Choose by what the business can tolerate.

**60-second answer**
I start with the business RTO and RPO per system, because they decide the cost. The options run from backup and restore, which is cheapest and slowest, to pilot light, warm standby and active-active. Pilot light keeps data replicated and a minimal core running. Warm standby runs a scaled-down full copy. Active-active serves traffic from both regions: fastest recovery, but most complex and it needs write-conflict handling. In all cases I need global routing such as Route 53 or Front Door with health checks, replicated data, and IaC to rebuild the environment. I watch replication lag and drift, and I run regular failover drills, because an untested plan usually fails when it is needed.

### Q13 [mid] Serverless vs containers vs VMs - how do you choose?
tags: serverless, containers, virtual-machines, aws-lambda, kubernetes, compute-choice, basics

**Start here: the concepts**
- **Virtual machine (VM):** a full pretend computer, with its own operating system, running on a physical server. It exists so one big machine can be split into many isolated ones. You control everything, including the OS, and you also patch and maintain everything.
- **Container:** a packaged app plus its libraries that runs as an isolated process and shares the host's OS kernel. It is lighter and starts faster than a VM, and it runs the same on a laptop and in production. Docker builds and runs containers. Kubernetes starts, restarts and scales many of them.
- **Serverless (functions):** you upload code and the cloud runs it only when an event arrives, such as a file upload, a queue message or an HTTP call. You do not manage servers and you pay per execution. AWS Lambda is an example.
- **Cold start:** the delay when the platform has no warm copy of your function and must start one first. A Java function pays extra because the JVM must start and load classes.
- **Time limit:** a function cannot run forever. Lambda, for example, stops after 15 minutes.
- **Vendor lock-in:** your code depends on one cloud's triggers and services, so moving later is costly.
- **Spiky traffic:** long idle periods broken by sudden bursts.

**The live scenario**
A team put an orders REST API on functions. Traffic was steady, about 300 requests per second all day. Median latency was 80 ms, but p99 (the slowest 1% of requests) hit 4 seconds whenever the platform added new instances and Java cold-started. The monthly bill was also higher than for a few always-on containers. Meanwhile, a nightly job that processed about 50 uploaded CSV files ran on a container fleet that sat idle 23 hours a day. They swapped the two: the API went to containers on Kubernetes, and the file processing became an upload-triggered function. Latency stabilised and cost dropped.

**What the interviewer is really checking**
Whether you choose by workload shape (steady or spiky, short or long, how much control is needed) and not by fashion, and whether you know the real limits of each option.

**How I answer it**
1. **Look at the traffic shape first.** Steady, predictable load suits containers or VMs, because you pay for always-on capacity that is actually used. Spiky or rare load suits serverless, because you pay nothing while idle.
2. **Check the runtime limits.** A job longer than the function time limit, or one needing persistent connections or a lot of memory, does not fit serverless. A cold start of a few seconds is fine for a background trigger but bad for a user-facing API.
3. **Decide how much control and portability you need.** Containers give control over the runtime and run on any cloud or on-premises, so lock-in is lower. Serverless gives the least operational work but the most lock-in.
4. **Use VMs when the container model does not fit.** That means legacy software that expects a full OS, a custom kernel or drivers, special licensing, or strict isolation requirements. Containers share the host kernel, so VMs isolate more strongly.
5. **Map this to examples.** A steady Java service goes in containers. Glue and ETL (extract-transform-load) work triggered by events goes in functions. A legacy app goes on a VM.
6. **Mention the blur.** Managed container platforms such as AWS Fargate and Google Cloud Run run containers without you managing servers, so the choice is a spectrum. Kubernetes nodes are usually VMs anyway.

**Trade-offs and what can go wrong**
- Serverless: cold starts (Java mitigations exist, such as Lambda SnapStart or native images, but they add complexity), time limits, harder local debugging, and cost that climbs sharply at constant high volume.
- Containers: you own more, including cluster upgrades, resource limits, scaling rules and image security. Kubernetes is overkill for two small services.
- VMs: slow to scale, patching burden, and low utilisation if oversized.
- Common mistake: picking serverless "because it is modern" for a steady, latency-sensitive API.

**How I'd monitor it**
- Latency percentiles (p50, p95, p99), and cold-start counts or init duration for functions.
- Function duration against its timeout, plus throttles and error counts.
- Container CPU and memory against requests and limits, restarts, and autoscaler activity.
- Cost per request or per month, compared across options.
- Log searches in Splunk or CloudWatch for timeouts and out-of-memory kills.

**Follow-ups to expect**
- *How do you reduce Java cold starts?* -> Use a smaller dependency footprint, Lambda SnapStart, native compilation, or provisioned concurrency (pre-warmed instances, which cost money).
- *When does serverless get more expensive than containers?* -> When load is high and constant, because you pay per invocation all day and an always-on container is cheaper per request.
- *Can you mix them?* -> Yes. Run core services in containers and use functions for event glue, such as file uploads or queue triggers.

**60-second answer**
I choose by workload shape. Serverless fits event-driven, spiky work where I want almost no operations, but I watch cold starts, time limits like Lambda's 15 minutes, and lock-in. Containers fit steady services because they are portable, I control the runtime, and always-on capacity is cheap when it is well used. VMs are for legacy software, special OS or kernel needs, or strong isolation. So a steady Java API goes in containers, and ETL or file-triggered glue goes in functions. In practice I often mix them, and I confirm the choice with p99 latency and cost numbers.

### Q14 [senior] How do you connect on-prem/legacy systems securely to the cloud?
tags: hybrid-cloud, vpn, direct-connect, expressroute, private-endpoint, mtls, api-gateway, basics

**Start here: the concepts**
- **On-prem/legacy system:** software running in your own data centre, often old (a mainframe or a large Oracle database). It cannot easily move, but cloud services need its data.
- **Site-to-site VPN:** an encrypted tunnel over the public internet between your network and the cloud network. It is quick and cheap to set up, but speed and delay vary with the internet.
- **Dedicated link (AWS Direct Connect, Azure ExpressRoute):** a private physical circuit from your data centre to the cloud provider, bypassing the public internet. It gives steadier latency and bandwidth. It is not encrypted by default, so add encryption on top (an IPsec VPN over it, or link-level encryption where offered).
- **Private DNS:** name lookup that works only inside your networks, so `core.internal` resolves to a private address and the two sides can find each other without public names.
- **Private endpoint (AWS PrivateLink, Azure Private Endpoint):** a private IP inside your network that reaches a cloud service (storage, database), so traffic never touches the public internet.
- **IP allow-list:** a rule saying "accept traffic only from these addresses". It is a useful outer fence, but addresses can be spoofed or shared, so it is never the only control.
- **mTLS (mutual TLS):** both sides show a certificate, so the server also verifies the caller, not just the caller verifying the server. It proves *who* is calling.
- **Integration boundary:** one controlled place (a message broker such as Kafka, or an API gateway) where the two worlds meet. The legacy system is never exposed directly.

**The live scenario**
A bank's cloud-hosted Spring Boot services call a legacy core-banking system on-prem through a site-to-site VPN, about 300 requests per second. At 02:10 the tunnel dropped for 4 minutes. The services called the legacy system synchronously with no timeouts, so threads piled up, the cloud pods went unhealthy, and customer-facing APIs returned errors even for requests that never needed legacy data. Afterwards the team put an API gateway and Kafka between the two sides, added timeouts and circuit breakers, and moved to two redundant tunnels.

**What the interviewer is really checking**
Whether you think in layers (network, name resolution, identity, integration pattern), and whether you design for the link failing instead of assuming it is always up.

**How I answer it**
1. **Choose the transport by need.** A site-to-site VPN suits a start or low volume. Direct Connect or ExpressRoute suits high volume or strict latency. I often use both, with the VPN as backup. Reason: the internet path is cheap but unpredictable; the dedicated path is predictable but costs more and takes weeks to order.
2. **Encrypt and make it redundant.** A dedicated link is private, not automatically encrypted, so I add IPsec or link encryption. I use two tunnels or circuits. Reason: one link is a single point of failure.
3. **Keep traffic off the public internet.** Use private endpoints for cloud services, plus private DNS so names resolve to private addresses on both sides. Reason: a name that resolves to a public address silently sends traffic the wrong way.
4. **Restrict who can connect.** Use IP allow-lists and firewall rules at the edge, then mTLS between the services. Reason: network location says where traffic came from; certificates say who it is.
5. **Put a boundary in the middle.** Use an API gateway for request/response calls (authentication, rate limits, throttling the legacy system). Use a message broker for asynchronous work, so messages queue while the link is down. Reason: the legacy system is not exposed and cloud services are decoupled from its availability.
6. **Plan for latency and link failure.** Set timeouts, retries with backoff, circuit breakers, and idempotent operations. Reason: a call that is not idempotent can run twice after a retry. Latency is now tens of milliseconds, not microseconds, so avoid chatty calls.

**Trade-offs and what can go wrong**
- Dedicated links cost more and have long lead times; VPN throughput is limited per tunnel.
- Asynchronous messaging means eventual consistency, so users may see stale data briefly.
- Overlapping IP ranges between on-prem and cloud break routing; plan address space early.
- Certificates expire, and an expired mTLS certificate causes an outage.
- DNS misconfiguration is a common hidden failure.
- Common mistake: relying on an IP allow-list alone, or assuming a dedicated circuit is encrypted.

**How I'd monitor it**
- Tunnel/circuit state and bandwidth from the provider's metrics (for example CloudWatch or Azure Monitor).
- Round-trip latency p95/p99 across the link.
- Splunk searches for timeout, connection-reset and circuit-breaker-open events, with alerts on spikes.
- Certificate expiry alerts well ahead of the date.
- Kafka consumer lag, which shows backlog building during an outage.
- DNS resolution failures.

**Follow-ups to expect**
- *VPN or Direct Connect/ExpressRoute?* -> VPN for fast, low-cost start or backup; dedicated link for steady latency and high volume. Production often uses both.
- *Is a dedicated link encrypted?* -> No, not by default. Add IPsec or link-level encryption if your policy requires it.
- *Why not just IP allow-lists?* -> They only say where traffic comes from, not who sent it. Combine them with mTLS and gateway authentication.

**60-second answer**
First I pick the network path: a site-to-site VPN for a quick start, or Direct Connect or ExpressRoute for steady latency and volume, usually with the VPN as backup. A dedicated link is private but not encrypted by default, so I add encryption and run two paths for redundancy. Then I keep traffic private with private endpoints and private DNS, and restrict access with IP allow-lists plus mTLS so both sides prove identity. I never expose the legacy system directly. An API gateway or message broker is the boundary, and the broker lets work queue while the link is down. Because the link will fail sometimes, I use timeouts, retries, circuit breakers and idempotent calls, and I monitor tunnel state, latency, certificate expiry and Kafka lag.

### Q15 [mid] What is Azure Key Vault and managed identity in a Spring app?
tags: azure, key-vault, managed-identity, spring-boot, secrets-management, spring-cloud-azure, basics

**Start here: the concepts**
- **Secret:** any value that gives access to something, such as a database password, an API key or a signing key. If it leaks, someone else can act as your app.
- **Azure Key Vault:** a managed Azure service that stores secrets, cryptographic keys and certificates in one protected place. It exists so secrets are not scattered across code, config files and pipelines. It adds access control, audit logs, versioning and rotation.
- **Identity (Microsoft Entra ID, formerly Azure AD):** Azure's login system. Every caller, human or application, must prove who it is before Azure lets it do anything.
- **Managed identity:** an identity Azure creates and manages for your app's host (App Service, VM, AKS and so on). Azure issues and rotates its credentials, and your code never sees a password. It exists to solve the bootstrap problem: to fetch a secret you normally need a credential, which is itself a secret.
  - *System-assigned:* tied to one resource and deleted with it.
  - *User-assigned:* created separately and shareable across resources.
- **Authorization (RBAC):** having an identity is not enough. You must grant it a role on the vault, for example "Key Vault Secrets User" (read secrets). Access policies are the older alternative model.
- **Spring Cloud Azure:** a library that plugs Key Vault into Spring's `Environment`, so a secret can be read like any other property.

**The live scenario**
A team's orders service ran on 6 instances and had its database password in `application.yml`, which was committed to Git. A contractor's laptop copy leaked it. Rotating it meant editing config, rebuilding and redeploying all 6 instances, and it took half a day. The team moved the password into Key Vault and gave the app a managed identity. Rotation became "update the secret, restart the app", and Git no longer held anything sensitive.

**What the interviewer is really checking**
Whether you understand how an app gets a secret without holding a credential, and whether you know that authentication (identity) and authorization (role) are separate steps.

**How I answer it**
1. **Put secrets in Key Vault, not in code or config.** This gives one audited, access-controlled home, with versions and rotation.
2. **Enable a managed identity on the host.** The app can then ask Azure for a token with no stored password, which removes the bootstrap secret. Use system-assigned for a single app and user-assigned when several resources share access.
3. **Grant that identity the least role it needs on the vault.** For example, "Key Vault Secrets User" on that one vault, because a leaked identity should only reach what it needs.
4. **Point Spring at the vault with Spring Cloud Azure.** At startup, it authenticates with the managed identity and loads secrets as properties, so your code just uses `@Value` or `@ConfigurationProperties`:
   ```properties
   spring.cloud.azure.keyvault.secret.property-sources[0].endpoint=https://myvault.vault.azure.net/
   ```
5. **Mind naming and locally running.** Secret names allow only letters, digits and hyphens, so you cannot use dots or underscores. Locally, the Azure credential chain can fall back to your `az login`, so the same code works on a laptop.
6. **Know the AWS equivalent.** It is the same pattern as reading Secrets Manager through an IAM role: the platform supplies the identity and the app holds no credentials.

**Trade-offs and what can go wrong**
- Missing role assignment gives a 403 at startup, which is the most common failure. It is an authorization problem, not an authentication one.
- Secrets are read at startup, so a rotated value needs a restart or a configured refresh.
- Key Vault is a startup dependency. If it is unreachable or throttled, the app may fail to start, so avoid calling it per request.
- Managed identity works only for Azure-hosted resources. Outside Azure you need other options, such as a service principal or federated credentials. On AKS, use workload identity to give a pod its identity.
- Never log resolved property values.

**How I'd monitor it**
- Enable Key Vault diagnostic logs to Log Analytics or Splunk, and search for failed requests (403/401) and unexpected callers.
- Alert on a spike in vault requests (throttling) and on secrets nearing expiry.
- Check startup logs for credential or vault errors after each deploy.

**Follow-ups to expect**
- *System-assigned vs user-assigned identity?* -> System-assigned lives and dies with one resource. User-assigned is independent and reusable, which suits several apps or slot swaps.
- *How do you pick up a rotated secret without redeploying?* -> Configure periodic refresh in Spring Cloud Azure, or restart rolling instances. Either way, test it.
- *Why not environment variables?* -> They are visible to anyone who can inspect the deployment, and they lack the vault's audit trail and central rotation.

**60-second answer**
Azure Key Vault is a managed store for secrets, keys and certificates, so passwords don't live in code or config. The app needs a way to prove who it is without its own password, and that is a managed identity: an identity Azure creates and rotates for the host. I enable it, then give it a minimal role on the vault, such as Key Vault Secrets User. In Spring, Spring Cloud Azure uses that identity at startup to load vault secrets as normal properties. The usual pitfalls are a missing role (a 403), secret names that allow only hyphens, and needing a restart or refresh to see rotated values. It is the same idea as reading Secrets Manager through an IAM role on AWS.

### Q16 [senior] Explain private networking: VNet, subnets, NSG, private endpoint.
tags: azure, networking, vnet, nsg, private-endpoint, aws-vpc, basics

**Start here: the concepts**
- **Virtual network (VNet in Azure, VPC in AWS):** your own private network inside the cloud. It exists so your resources can talk to each other without being reachable from everyone else. You choose its private address range, for example 10.0.0.0/16.
- **Subnet:** a slice of the VNet's address range, for example 10.0.1.0/24. You split a VNet into subnets so different tiers (web, app, database) can have different rules.
- **NSG (Network Security Group):** a list of allow/deny rules on source, destination, port and protocol. Each rule has a priority number, and the lowest number is checked first. It attaches to a subnet or a single network interface (NIC). It exists to enforce "only the app tier may talk to the database tier".
- **PaaS service:** a managed service such as Azure SQL or Storage. By default you reach it through a public address.
- **Private endpoint:** a network interface in your subnet with a private IP that maps to one specific PaaS resource. You reach the service at that private IP, over the provider's backbone network, not the public internet.
- **Private DNS zone:** a DNS setup that makes the service's normal name (for example `myserver.database.windows.net`) resolve to the private IP inside your VNet. Without it, a private endpoint does not work properly.
- **AWS equivalents:**
  - VPC, subnets.
  - **Security groups:** stateful, attached to instances/NICs.
  - **NACLs:** stateless, attached to subnets.
  - **VPC endpoints:** gateway type for S3/DynamoDB, interface type (PrivateLink) for most other services.

**The live scenario**
A payments API on 40 pods in a VNet calls Azure SQL. A security audit finds the database is reachable from the public internet, protected only by a firewall allow-list. The team adds a private endpoint and turns off public network access. At 2 a.m. the API starts timing out, with about 100% of DB calls failing. The cause: the private DNS zone was not linked to the VNet, so the DB name still resolved to the public IP, which now refused connections. Linking the zone fixed it in minutes.

**What the interviewer is really checking**
Whether you understand the layers (isolate, segment, filter, privately reach PaaS) and know the practical traps, especially DNS and leftover public access, rather than only reciting definitions.

**How I answer it**
1. **Create the VNet with a planned address range.** Non-overlapping ranges keep peering and VPN to other networks possible later. Overlaps are painful to fix.
2. **Split it into subnets by tier** (web, app, data, private endpoints). Rules and routing then apply per tier.
3. **Attach NSGs with default deny and narrow allows.** For example, the data subnet accepts port 1433 only from the app subnet. NSGs are stateful, so replies to allowed traffic need no extra rule.
4. **Create a private endpoint for each PaaS service**, such as SQL or Storage. Traffic then reaches a private IP inside your VNet, not the service's public address.
5. **Set up private DNS** so the normal service name resolves to that private IP. Check it:
   ```
   nslookup myserver.database.windows.net   # expect a 10.x address
   ```
6. **Disable public network access on the PaaS resource.** A private endpoint adds a private path but does not remove the public one. Only turning public access off closes it.

**Trade-offs and what can go wrong**
- DNS is the most common failure: a missing zone link or on-premises DNS that does not forward the private zone.
- Private endpoints cost per endpoint and per GB processed, and you need one per service (and per sub-resource, such as blob vs file).
- NSG priority mistakes: a broad allow with a lower number overrides a later deny.
- In AWS, mixing up security groups (stateful, instance level) with NACLs (stateless, subnet level, need return-traffic rules).
- Overlapping address ranges block peering later.
- Over-open rules such as "allow any" to get things working, which are never tightened.

**How I'd monitor it**
- NSG flow logs (Azure) or VPC Flow Logs (AWS) to see allowed and denied traffic.
- Connection-failure and timeout rates in the app, with a Splunk search on DB timeout errors after any network change.
- A DNS check from inside the VNet confirming a private IP.
- Policy or config scans (Azure Policy, AWS Config) that alert if a resource has public access enabled.

**Follow-ups to expect**
- *Private endpoint vs service endpoint?* -> A private endpoint gives the service a private IP in your subnet. A service endpoint keeps the service's public IP but restricts access to your subnet over the backbone.
- *Security group vs NACL?* -> Security groups are stateful and attach to instances. NACLs are stateless and attach to subnets, so return traffic needs explicit rules.
- *Why can't my app connect after creating the private endpoint?* -> Usually DNS. Check that the name resolves to the private IP, then NSG rules, then whether public access is disabled.

**60-second answer**
A VNet is my private network in the cloud, and I split it into subnets by tier, such as web, app and data. NSGs sit on subnets or NICs and allow or deny traffic by port and source, with default deny and narrow allows. A private endpoint gives a PaaS service like SQL or Storage a private IP inside my subnet, so traffic stays on the provider's private backbone, not the public internet. Two things must go with it: a private DNS zone so the service name resolves to that private IP, and disabling public access on the service. In AWS the equivalents are VPC, subnets, security groups and NACLs, and VPC endpoints or PrivateLink. I've seen an outage where DNS still pointed at the public IP after public access was turned off, so I always verify resolution first.

### Q17 [architect] Design a landing zone / environment strategy for a team.
tags: landing-zone, environment-strategy, azure, aws, iac, governance, basics

**Start here: the concepts**
- **Landing zone:** a pre-built, governed cloud foundation (accounts, network, security rules, logging) that every new workload is placed into. It exists so each team does not reinvent security and networking, and so mistakes are hard to make.
- **Subscription (Azure) / account (AWS):** the top-level container for resources, with its own billing, permissions and quotas. It is the strongest everyday isolation boundary, so a mistake in one cannot easily touch another.
- **Management group / AWS Organizations:** a layer above subscriptions or accounts where rules are applied once and inherited by all below.
- **Hub-and-spoke network:** one shared "hub" network holds common things (firewall, DNS, VPN or private link to on-premises). Each environment is a "spoke" that connects through it. This avoids rebuilding and re-securing these pieces per team.
- **Central logging:** audit and application logs from every account are copied to one protected place that workload teams cannot edit. It exists so evidence survives an incident.
- **Policy:** an automatic rule that blocks or flags non-compliant resources, for example "only these regions", "must carry cost-owner tags", "no public storage". Azure calls this Azure Policy; AWS uses Service Control Policies and AWS Config.
- **RBAC (role-based access control):** permissions are given to roles. People get roles through **groups** from the company identity provider, never as individuals. When someone leaves or moves, you change group membership, not hundreds of grants.
- **Budget:** a spending limit with alerts, so a runaway resource is noticed in days, not at month end.
- **IaC (infrastructure as code):** infrastructure described in files such as Terraform, Bicep or CloudFormation, kept in Git. It is reviewable, repeatable and detects drift.

**The live scenario**
A team of 25 engineers ran 8 microservices in one shared subscription. In one week:
- A load test used up the regional CPU quota, so production autoscaling could not add pods during a 3x peak.
- A developer made a storage container public "temporarily", exposing about 40,000 customer records.
- The bill rose 2.5x and nobody could say which team caused it, because nothing was tagged.
- A hand-edited firewall rule in production could not be reproduced in test.

**What the interviewer is really checking**
Whether you think in terms of blast radius, guardrails and auditability, not just "make three accounts". At architect level, also whether you can balance safety against team speed and cost.

**How I answer it**
1. **Group resources hierarchically and split by environment.** Use separate subscriptions or accounts for dev, test and prod, plus separate platform ones (network, logging, identity). Reason: quotas, permissions, billing and failures stay contained, so a load test cannot starve prod.
2. **Build a shared network hub.** Reason: security controls and on-premises connectivity are built once. Spokes are peered to it, and dev has no route to prod data.
3. **Send all logs to a central, write-protected account.** Reason: if a workload account is compromised or deleted, the audit trail remains.
4. **Apply policies at the management-group level.** Examples: allowed regions (data residency), mandatory tags (cost ownership), no public storage. Reason: guardrails prevent errors up front instead of relying on review. Start in audit mode, then enforce.
5. **Grant access through RBAC to groups, not individuals.** Developers get broad rights in dev, read-only in prod. Reason: least privilege, easy joiner/leaver handling, clean audits. Add a time-limited break-glass role for emergencies.
6. **Set budgets with alerts per subscription or tag.** Reason: cost surprises become early warnings.
7. **Define everything as IaC.** Reason: environments are identical, changes are reviewed, drift is detectable.
8. **Make the CI/CD pipeline the only way to change production.** Humans get read access; the pipeline uses its own identity. Reason: every change is tested, approved and traceable, and rollback is a re-run of the previous version.

**Trade-offs and what can go wrong**
- More subscriptions mean more overhead (networking, shared-service access) and a need for automation to create them.
- Strict policies can block teams. Without a fast exception process, people work around them.
- A pipeline-only rule fails during an outage unless break-glass access exists and is audited.
- The hub can become a bottleneck or single point of failure, so size it and make it redundant.
- Common mistake: "prod" and "non-prod" are separated but dev data is copied from prod unmasked.

**How I'd monitor it**
- Policy compliance percentage (Azure Policy / AWS Config) and a count of non-compliant resources by team.
- Budget alerts and cost reports by tag, plus the share of untagged spend.
- Audit logs (Azure Activity Log / CloudTrail) in Splunk: alert on any human write action or role assignment in prod.
- Scheduled `terraform plan` to detect drift between code and reality.
- Quota usage per subscription.

**Follow-ups to expect**
- *Why not one subscription with resource groups?* -> Quotas, permissions and billing are shared, so blast radius is large. Resource groups organise but do not isolate.
- *How do you give developers speed without breaking guardrails?* -> Self-service templates, sandbox subscriptions with low budgets, and policies that guide rather than block.
- *What if the pipeline itself is compromised?* -> Use short-lived credentials, separate pipeline identities per environment, approvals for prod and protected branches.

**60-second answer**
I'd give each environment, dev, test and prod, its own subscription or account, so quotas, permissions and failures stay isolated. A shared hub network and central, protected logging sit alongside them. At the top, I'd apply policies such as allowed regions, mandatory tags and no public storage, so mistakes are blocked automatically. Access goes through RBAC to groups from the identity provider, never to individuals, with a audited break-glass role. Budgets alert on cost per team. Everything is IaC in Git, and the pipeline is the only route into production, so every change is reviewed and traceable. I'd monitor policy compliance, drift, cost by tag and any manual prod changes in the audit logs.

### Q18 [fresher] Container vs VM? What is a Docker image vs container?
tags: docker, containers, virtual-machines, docker-image, namespaces, cgroups, kernel, basics

**Start here: the concepts**
- **Kernel:** the core of an operating system. It talks to the hardware, schedules processes, and manages memory and networking. Every program asks the kernel for these services.
- **Virtual machine (VM):** a full computer simulated in software. A hypervisor splits one physical server into several VMs, and each VM runs its own complete operating system with its own kernel. It is strongly isolated but heavy.
- **Container:** an ordinary process (or group of processes) on the host, fenced off so it believes it has the machine to itself. It has no OS of its own and uses the host's kernel. That is why it is light.
- **Namespaces:** a Linux feature that limits what a process can *see*, such as its own process list, network interfaces and filesystem view.
- **cgroups (control groups):** a Linux feature that limits what a process can *use*, such as CPU and memory. Together, namespaces give isolation and cgroups give resource caps.
- **Docker image:** a read-only package holding your app, its runtime (for example a JRE), libraries and config. It is built in **layers** (base OS files, then the JRE, then your JAR). Layers are cached and shared, so rebuilds and downloads are fast. *Immutable* means it never changes after it is built.
- **Docker container:** a running instance of an image. Docker adds a thin writable layer on top, and that layer is lost when the container is removed. One image can start many containers.

**The live scenario**
A team ran 10 Spring Boot services, each on its own VM. Each VM took about 3 minutes to boot, and the guest OS used roughly 1 GB of RAM before the app started. During a traffic spike they needed more instances, but scaling took minutes and the servers were only about 30% utilised. They also hit "works on my machine" bugs because each VM had slightly different Java and library versions. They moved to containers built from one image per service. Instances started in seconds, more of them fit on each server, and the same image ran identically in dev, test and production. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you understand that the difference is *what is shared*: VMs virtualise hardware and carry a whole OS, while containers share the host kernel. They also check that you don't confuse image (the template) with container (the running thing).

**How I answer it**
1. **Start with the VM.** It has its own OS and kernel on virtual hardware, so it is isolated but heavy and slow to boot. I begin here because the container is easiest to explain by contrast.
2. **Define the container.** It is a normal process on the host kernel, isolated by namespaces (what it sees) and limited by cgroups (what it uses). With no OS to boot, it starts in seconds and uses less memory.
3. **Define the image.** It is a read-only, layered template, and I say it is immutable. It is immutable so that what you tested is exactly what you deploy.
4. **Define the container as an instance.** It is an image plus a thin writable layer. The analogy: image is to container as a class is to an object.
5. **Show the relationship in one line:**
```
docker run -d --memory=512m my-service:1.0   # start a container from an image, capped at 512 MB
```

**Trade-offs and what can go wrong**
- **Weaker isolation:** all containers share one kernel, so a kernel vulnerability affects all of them. VMs isolate more strongly, which is why sensitive multi-tenant workloads sometimes still use VMs.
- **Same-kernel limit:** a Linux container needs a Linux kernel. On Windows or Mac, Docker Desktop quietly runs a small Linux VM underneath.
- **Data loss:** the writable layer disappears with the container. Persistent data belongs in volumes or external storage.
- **No memory limit:** one container can starve its neighbours. If it exceeds its limit, it is killed (OOMKilled).
- **Bloated or mutable images:** huge images, secrets baked into them, or the `latest` tag make deployments slow and unrepeatable.

**How I'd monitor it**
- `docker ps` and `docker stats` for running containers and their CPU and memory.
- Restart counts and OOMKilled events, which show limits set too low.
- Image size and vulnerability scans in the build pipeline.
- Start-up time per instance, tracked over releases.
- On Kubernetes, `kubectl top pods` and container-level dashboards.

**Follow-ups to expect**
- *Are containers as secure as VMs?* -> Not by default. They share the host kernel, so isolation is weaker. Mitigate with non-root users, minimal images, and keeping the host patched.
- *What happens to data when a container is deleted?* -> Anything in its writable layer is lost. Use volumes or external databases for state.
- *Why are images layered?* -> Unchanged layers are cached and shared, so builds and pulls only handle what changed.

**60-second answer**
A virtual machine simulates a whole computer with its own operating system, so it is strongly isolated but heavy and slow to boot. A container is just a process on the host that shares the host's kernel. Linux namespaces control what it can see, and cgroups limit the CPU and memory it can use, so it is lighter and starts in seconds. A Docker image is the read-only, layered template holding the app and its dependencies. A container is a running instance of that image, with a thin writable layer on top that disappears when it is removed. One image can start many containers, like a class and its objects. The trade-off is that containers isolate less strongly than VMs because they share a kernel.

### Q19 [fresher] How do you write a good Dockerfile for a Spring Boot app?
tags: docker, spring-boot, dockerfile, containers, jvm, security, basics

**Start here: the concepts**
- **Docker image**: a read-only package holding your app, its Java runtime and the files it needs. A container is a running copy of it. It exists so the app runs the same on a laptop, in test and in production.
- **Layer**: each Dockerfile instruction creates a layer. Docker caches layers and reuses any that haven't changed. If one layer changes, every layer after it is rebuilt.
- **Multi-stage build**: one Dockerfile with several `FROM` stages. The first stage uses a full JDK and Maven to build the jar. The final stage copies only the result into a small image, so build tools never ship.
- **JRE vs JDK**: the JDK has compilers and tools for building. The JRE only runs the app and is smaller. Temurin is a common free OpenJDK build. **Distroless** images contain almost nothing except the runtime, with no shell or package manager, so there is less to attack.
- **Layered jar**: Spring Boot can split its fat jar into folders (dependencies, loader, application classes) so each becomes its own Docker layer.
- **Non-root user**: by default a container process runs as root. If an attacker breaks in, root is far more dangerous than an ordinary user.
- **MaxRAMPercentage**: a JVM flag that sizes the heap as a percentage of the container's memory limit.
- **Buildpacks / Jib**: tools that build an image for you without a hand-written Dockerfile.

**The live scenario**
A team's Spring Boot image was 650 MB because it shipped the full JDK and Maven. Every code change re-uploaded a 90 MB fat jar layer, so the CI build took 6 minutes and each deploy pulled a lot of data. The container also ran as root, and a security scan flagged it. Pods were killed for exceeding memory (OOMKilled, exit code 137) because the heap was not tied to the container limit. After switching to a multi-stage build with a layered jar, a JRE base, a non-root user and a percentage-based heap, the image was a fraction of the size. Rebuilds only re-pushed the small application layer, and the OOM kills stopped.

**What the interviewer is really checking**
Whether you understand image size, build caching, security basics and how the JVM behaves inside a container, not whether you can recite Dockerfile keywords.

**How I answer it**
1. **Use a multi-stage build.** Build the jar in a JDK stage and copy only the output into a small JRE stage. This keeps compilers, Maven and source code out of production, which means a smaller image and less attack surface.
2. **Use a small JRE base image** such as Temurin JRE or distroless, and pin a specific version tag. Less software means fewer vulnerabilities and faster pulls, and pinning makes builds repeatable. Distroless has no shell, which makes debugging harder.
3. **Extract the layered jar and copy the dependencies layer before the application layer.** Dependencies change rarely and your code changes constantly. Putting the stable layer first lets Docker reuse its cache, so only the small layer is rebuilt and pushed. Spring Boot has supported layered jars since 2.3.
4. **Run as a non-root user** by creating one and switching to it with `USER`. This limits the damage if the app is compromised.
5. **Set JVM memory relative to the container.** Use `-XX:MaxRAMPercentage=75` through `JAVA_TOOL_OPTIONS`. A fixed `-Xmx` drifts out of sync when someone changes the pod memory limit. Leave headroom, because the JVM also uses memory outside the heap.
6. **Use exec-form `ENTRYPOINT ["java","-jar","app.jar"]`.** This makes Java the main process, so it receives SIGTERM and can shut down gracefully (`server.shutdown=graceful`). Shell form can swallow the signal.
7. **Health checks:** Docker's `HEALTHCHECK` works for plain Docker, but Kubernetes ignores it. On Kubernetes, use liveness and readiness probes against Spring Boot Actuator.
8. **Keep secrets out of the image.** Anything copied or set with `ENV` at build time stays readable in the layers. Inject secrets at runtime through Kubernetes Secrets or a vault. Add a `.dockerignore` so `.git` and `.env` files are never copied.
9. **Or skip the Dockerfile.** `./mvnw spring-boot:build-image` uses Cloud Native Buildpacks, and Jib builds layered images without a Docker daemon. Both apply good defaults, but you get less control than with a hand-written file.

**Trade-offs and what can go wrong**
- Distroless is secure but hard to debug. You may need a debug variant or ephemeral debug containers.
- Setting the heap too high causes OOMKilled, because metaspace, thread stacks and native memory sit outside the heap.
- Using `latest` tags makes builds unrepeatable.
- Buildpacks hide detail and can be slower to customize.
- Running as root, or baking secrets into a layer, is the most common security mistake.

**How I'd monitor it**
- Scan images in CI with Trivy or Grype for known vulnerabilities.
- Track image size and build time over releases.
- Use `kubectl describe pod` to look for OOMKilled and restart counts.
- Watch JVM heap and memory metrics (Actuator with Prometheus) against the container limit.
- Check that probes pass after deploy.

**Follow-ups to expect**
- *Why copy dependencies before application code?* -> Docker caches layers in order. Stable dependencies stay cached, so only your small, changing layer is rebuilt.
- *Why not hardcode `-Xmx`?* -> It breaks when the pod memory limit changes. A percentage adapts to the limit.
- *Does Kubernetes use the Dockerfile `HEALTHCHECK`?* -> No. It uses its own liveness, readiness and startup probes.

**60-second answer**
I use a multi-stage build. One stage builds the jar with a JDK, and the final stage runs it on a small JRE or distroless image. I extract Spring Boot's layered jar and copy the rarely changing dependencies first, so rebuilds only touch the small application layer. I create a non-root user, set `MaxRAMPercentage` so the heap follows the container memory limit, and use exec-form `ENTRYPOINT` so the app gets shutdown signals. On Kubernetes I use probes instead of Docker's `HEALTHCHECK`, and I never put secrets in the image. If I don't want to maintain a Dockerfile, I use Buildpacks or Jib.

### Q20 [fresher] Name the main Kubernetes objects.
tags: kubernetes, pod, deployment, service, configmap, basics

**Start here: the concepts**
- **Container**: an application packaged with everything it needs to run, so it behaves the same on a laptop and on a server. Kubernetes runs containers but never handles them directly. It wraps them in Pods.
- **Cluster and Node**: a cluster is a group of machines managed together. Each machine (physical or virtual) is a **Node**, and Nodes are where your containers actually run.
- **Pod**: the smallest unit Kubernetes deploys. It holds one or more tightly coupled containers that share a network address and can share storage. Pods are disposable and a replacement gets a new IP.
- **Deployment**: you say "I want 3 copies of this Pod". It creates a **ReplicaSet**, which keeps that number running, replacing any Pod that dies. When you ship a new version, the Deployment does a rolling update, swapping Pods gradually.
- **Service**: Pod IPs change, so a Service gives a group of Pods one stable virtual IP and DNS name and spreads traffic across them.
- **Ingress / Gateway API**: rules for routing outside HTTP traffic (for example `/orders` goes to one Service, `/users` to another). Ingress needs an ingress controller to act on the rules. Gateway API is the newer, more expressive successor.
- **ConfigMap / Secret**: settings kept outside the image. A Secret is for sensitive values, but by default it is only base64-encoded, not encrypted, so access to it must be restricted.
- **Namespace**: a named partition of the cluster, used to separate teams or environments.
- **StatefulSet**: like a Deployment, but each Pod keeps a stable name and its own storage. It suits databases.
- **DaemonSet**: runs one Pod on every Node, for example a log collector.
- **Job / CronJob**: a Job runs a task to completion. A CronJob runs a Job on a schedule.
- **PersistentVolume (PV) / PersistentVolumeClaim (PVC)**: a PV is a piece of storage. A PVC is a Pod's request for storage, so data survives Pod restarts.
- **HPA (HorizontalPodAutoscaler)**: adds or removes Pod copies based on load, such as CPU.

**The live scenario**
A team ran an orders API as a single bare Pod. At 2 a.m. its Node failed, and nobody was serving 500 requests per second for about 20 minutes until someone recreated it by hand. They moved to a Deployment with 3 replicas behind a Service. Kubernetes now replaces lost Pods automatically, and traffic keeps flowing to the survivors. They also moved the database URL into a ConfigMap and the password into a Secret, and added an HPA for the evening peak.

**What the interviewer is really checking**
Whether you know what each object is *for*, not just its name, and whether you can say why you would use a Deployment instead of a bare Pod.

**How I answer it**
1. Start with **Pod**, the unit that runs containers. Everything else exists to manage Pods.
2. Add **Deployment (via ReplicaSet)** because Pods are disposable and something must keep the right count running and roll out updates safely.
3. Add **Service**, because Pod IPs change and clients need one stable address. Then **Ingress/Gateway API** for HTTP traffic from outside.
4. Cover configuration: **ConfigMap** and **Secret** keep settings out of the image. **Namespace** separates teams or environments.
5. Cover special workloads: **StatefulSet** (stable identity and storage), **DaemonSet** (one Pod per Node), **Job/CronJob** (one-off or scheduled work).
6. Cover storage and scaling: **PV/PVC** for durable data, **HPA** for automatic scaling, **Node** as the machine underneath.

```
kubectl create deployment orders --image=orders:1.0 --replicas=3
```

**Trade-offs and what can go wrong**
- A bare Pod is not rescheduled if its Node dies, so use a Deployment.
- A Secret is not encrypted by default, so lock down access and consider encryption at rest.
- Running databases in a StatefulSet is harder than using a managed service.
- An Ingress does nothing without an ingress controller.
- An HPA needs resource requests set, or it cannot calculate utilisation.

**How I'd monitor it**
- `kubectl get pods` and `kubectl describe pod` for status and events.
- `kubectl rollout status deployment/orders` during releases.
- Watch Pod restart counts, Pods stuck in Pending, and available versus desired replicas.
- Alert when available replicas stay below desired.
- Search Splunk logs by namespace and Pod name.

**Follow-ups to expect**
- *Deployment vs StatefulSet?* -> A Deployment's Pods are interchangeable. A StatefulSet gives each Pod a stable name and its own storage.
- *Why not talk to Pod IPs directly?* -> They change whenever a Pod is replaced. A Service gives a stable address.
- *Pod vs container?* -> A Pod wraps one or more containers that share network and storage.

**60-second answer**
The smallest Kubernetes object is the Pod, which wraps one or more containers. Pods are disposable, so a Deployment manages them through a ReplicaSet, keeping the desired count running and doing rolling updates. A Service gives those Pods a stable IP and DNS name, and Ingress or Gateway API routes outside HTTP traffic to Services. ConfigMaps and Secrets hold configuration, and Namespaces separate teams or environments. For special cases there are StatefulSets for stable identity and storage, DaemonSets for one Pod per Node, and Jobs and CronJobs for batch work. PersistentVolumes and Claims give durable storage, an HPA scales Pods with load, and Nodes are the machines everything runs on.

### Q21 [mid] Explain liveness, readiness and startup probes.
tags: kubernetes, probes, liveness, readiness, spring-boot, basics

**Start here: the concepts**
- **Pod and container:** a container is your running app process. A pod is the unit Kubernetes schedules, and it holds one or more containers.
- **kubelet:** the agent on each node that starts containers and checks their health.
- **Probe:** a small check the kubelet runs repeatedly against your container, such as an HTTP GET on a URL. A 2xx/3xx answer means pass. Anything else, or a timeout, means fail. Probes exist because a running process is not always a working process: it can be deadlocked, still starting, or temporarily overloaded.
- **Service and endpoints:** a Service is a stable address that load-balances across pods. Its endpoints list holds the pods currently allowed to receive traffic.
- **Liveness probe:** asks "is this container stuck beyond recovery?" After enough consecutive failures, the kubelet **restarts the container**.
- **Readiness probe:** asks "can this pod serve requests right now?" If it fails, the pod is **removed from the Service endpoints**. It is not restarted, and it is added back when the probe passes again.
- **Startup probe:** asks "has the app finished starting?" Liveness and readiness probes do not begin until it succeeds. This protects slow-starting apps from being killed before they are up.
- **Spring Boot Actuator:** a Spring Boot module that exposes health endpoints.

**The live scenario**
An order service ran 12 pods. Its liveness endpoint also checked the database. During a 40-second database failover, every liveness check failed on every pod at once. Kubernetes restarted all 12 pods together. Each JVM needed about 90 seconds to start, so the service was fully down for roughly 2 minutes, well beyond the 40-second database problem. The restarts also hit the recovering database with a burst of new connections. The fix was to make liveness check only the app's own process state and to let readiness handle dependency problems.

**What the interviewer is really checking**
Whether you know what each probe does to the pod (restart vs. remove from traffic vs. delay), and whether you can avoid the classic mistake of tying liveness to an external dependency.

**How I answer it**
1. **Liveness means "restart me".** Use it only for states a restart can fix, such as a deadlock or a hung process. Restarting does not fix a broken database, so a dependency check here only causes outages.
2. **Readiness means "don't send me traffic".** Use it when the pod is temporarily unable to serve, for example while warming up, while shutting down, or when overloaded. The pod stays alive and rejoins when healthy. Because no restart happens, this is the safe place to react to problems.
3. **Startup protects slow starters.** Without it, liveness can fail during a long JVM start and kill the pod in a loop. Once the startup probe passes, liveness and readiness take over. If startup never passes within `failureThreshold × periodSeconds`, the container is killed and restarted.
4. **Spring Boot wiring:** set `management.endpoint.health.probes.enabled=true`. This exposes `/actuator/health/liveness` and `/actuator/health/readiness`, which you point the probes at. (Spring Boot 2.3 introduced these probe groups.)
5. **Keep each probe's meaning separate**, as in this example. It allows up to 30 × 10 = 300 seconds to start:

```yaml
startupProbe:   {httpGet: {path: /actuator/health/liveness, port: 8080}, failureThreshold: 30, periodSeconds: 10}
livenessProbe:  {httpGet: {path: /actuator/health/liveness, port: 8080}}
readinessProbe: {httpGet: {path: /actuator/health/readiness, port: 8080}}
```

**Trade-offs and what can go wrong**
- **Liveness too strict** (tiny timeout, low threshold): healthy but busy pods get restarted under load, which makes the load worse.
- **Liveness depends on the DB or another service:** one blip restarts everything, as in the scenario.
- **Readiness depends on a shared dependency:** if every pod fails readiness, the Service has no endpoints and users get errors. Include a dependency only if you truly cannot serve without it.
- **No startup probe plus a short initial delay:** a crash loop on slow starts, especially during deployments.
- **Probe endpoint doing heavy work:** it runs every few seconds on every pod, so keep it cheap.

**How I'd monitor it**
- `kubectl describe pod` shows events like "Liveness probe failed" and "Readiness probe failed".
- Alert on the container restart count (`kube_pod_container_status_restarts_total` from kube-state-metrics) and on pods stuck in CrashLoopBackOff.
- Watch ready pods vs. desired replicas and the number of Service endpoints. A sudden drop means readiness is failing.
- In Splunk, search Kubernetes events for probe failures and group by pod and time. Many pods failing together points to a shared dependency rather than a bad pod.

**Follow-ups to expect**
- *Why not just use a bigger initialDelaySeconds instead of a startup probe?* -> A fixed delay wastes time on fast starts and still fails on slow ones. A startup probe starts checking right away and waits only as long as needed, up to its limit.
- *What happens during a rolling update if readiness is wrong?* -> New pods may get traffic before they are ready, or the rollout stalls because they never become ready. A correct readiness probe is what makes rolling updates safe.
- *Does a failing readiness probe restart the pod?* -> No. The pod only leaves the Service endpoints and returns once the probe passes.

**60-second answer**
Kubernetes uses probes to check my container's health. A failing liveness probe makes the kubelet restart the container, so I use it only for stuck states a restart can fix. A failing readiness probe removes the pod from the Service endpoints without restarting it, so it handles "not ready for traffic right now". A startup probe holds off the other two until a slow app has finished starting, which prevents crash loops. In Spring Boot I enable `management.endpoint.health.probes.enabled=true` and use `/actuator/health/liveness` and `/readiness`. I never make liveness depend on the database, because a DB blip would restart every pod and turn a short problem into a long outage.

### Q22 [mid] Requests vs limits and how they affect scheduling and OOM?
tags: kubernetes, resource-requests, resource-limits, oomkilled, cpu-throttling, jvm-containers, basics

**Start here: the concepts**
- **Pod and container:** A container is your app packaged with its dependencies. A pod is the smallest unit Kubernetes schedules, and it wraps one or more containers.
- **Node and scheduler:** A node is a machine (VM) that runs pods. The scheduler is the Kubernetes component that picks which node a new pod goes on.
- **Request:** The amount of CPU or memory you tell Kubernetes your container needs. The scheduler uses it to place the pod: it only picks a node with enough unreserved capacity. It reserves that amount on paper and does not measure real usage at placement time. Under CPU contention, requests also decide each container's share of CPU.
- **Limit:** The maximum the container may use. The Linux kernel enforces it, not the scheduler.
- **CPU is compressible:** If a container wants more CPU than its limit, it is slowed down (**throttled**). It keeps running, just slower, because the kernel hands out CPU time in small slices (100 ms periods by default).
- **Memory is not compressible:** Memory cannot be taken back without losing data. If a container goes over its memory limit, the kernel kills it. Kubernetes shows this as **OOMKilled** (exit code 137). OOM means "out of memory".
- **CPU unit:** `500m` means 500 millicores, which is half a CPU core.
- **QoS class:** Kubernetes ranks pods by how you set requests and limits. *Guaranteed* means request = limit for every container, *Burstable* means partial settings, and *BestEffort* means none. When a node runs short of memory, BestEffort pods are evicted first and Guaranteed pods last.
- **JVM heap vs. total memory:** The Java heap is only part of a Java process's memory. Metaspace, thread stacks and direct buffers sit outside it. `MaxRAMPercentage` sets the heap as a percentage of the container's memory limit. Container-aware JVMs (Java 10+, and Java 8 from 8u191) read that limit.

**The live scenario**
A payments service ran 6 pods at about 800 requests per second. We had set memory request 512Mi, limit 2Gi, and no JVM flags. Pods looked fine on a 4 GB node until peak hour, when three pods landed on the same node and all grew past the node's real memory. Pods were evicted and restarted at random, and p99 latency jumped from 120 ms to 2 s during restarts. Another team's pod with a 1 CPU limit showed healthy CPU graphs but latency spikes: it was being throttled during garbage collection. We fixed it by setting memory request = limit and sizing the heap to leave headroom.

**What the interviewer is really checking**
That you know requests drive scheduling and limits drive enforcement. That you know CPU overuse means throttling while memory overuse means a kill. And that you can connect this to JVM sizing in a real Java service.

**How I answer it**
1. **Requests decide placement.** The scheduler adds up requests per node and places the pod only where they fit. Requests set too low cause overcommitted nodes. Requests set too high waste money on idle capacity.
2. **Limits are enforced at runtime.** CPU over the limit is throttled. Memory over the limit is OOMKilled.
3. **For Java, set memory request = limit.** This gives predictable placement because the node really has the memory you reserved. It also avoids node-level eviction surprises, and with CPU request = limit it makes the pod Guaranteed.
4. **Be careful with CPU limits.** Throttling hurts latency, especially during GC and startup. Set a CPU request from measured usage. Use a generous CPU limit, or none if your platform's policy allows it.
5. **Align the JVM with the limit.** Set `MaxRAMPercentage` below 100 (for example 60-75) so non-heap memory fits under the limit.
```yaml
resources:
  requests: { memory: "1Gi", cpu: "500m" }
  limits:   { memory: "1Gi" }   # JVM: -XX:MaxRAMPercentage=70
```

**Trade-offs and what can go wrong**
- Heap at about 100% of the limit: heap plus metaspace and threads exceed the limit, and the pod is OOMKilled even though the heap is "fine".
- Request far below the limit (Burstable): the scheduler packs pods too tightly, and a node memory squeeze evicts them.
- Request = limit set too high: pods are safe but costly, with low node utilisation.
- Tight CPU limits: throttled threads cause latency spikes while average CPU still looks low.
- Not every restart is an OOM. Check the pod's last state before changing numbers.

**How I'd monitor it**
- `kubectl describe pod`: look for `Reason: OOMKilled` and the restart count.
- `container_memory_working_set_bytes` against the limit.
- `container_cpu_cfs_throttled_periods_total` divided by total periods, to see the throttling ratio.
- Alerts on restart rate and on memory above 85% of the limit.
- JVM heap and GC metrics, and Splunk searches for pod restart events.

**Follow-ups to expect**
- *What happens if a pod's request is bigger than any node's free capacity?* -> It stays Pending, and the scheduler event shows "Insufficient cpu/memory".
- *Why does an HPA need CPU requests?* -> HPA computes utilisation as a percentage of the request, so with no request it cannot scale on CPU.
- *OOMKilled vs. evicted?* -> OOMKilled means the container hit its own limit. Eviction means the node ran low on memory and kubelet removed the pod.

**60-second answer**
A request is what the scheduler reserves for a pod, so it controls which node the pod lands on. A limit is the hard cap the kernel enforces. If a container goes over its CPU limit it is throttled and slows down, but if it goes over its memory limit it is OOMKilled. For Java I set the memory request equal to the limit so placement is predictable. I set `MaxRAMPercentage` around 60-75% so non-heap memory also fits in the limit. I set CPU requests from measured usage and keep CPU limits generous, because throttling hurts latency. I watch OOMKilled restarts, memory against the limit, and the CPU throttling ratio.

### Q23 [mid] How does a rolling update work and how do you roll back?
tags: kubernetes, rolling-update, rollback, deployment, readiness-probe, devops, basics

**Start here: the concepts**
- **Pod**: the smallest unit Kubernetes runs. It wraps one or more containers, and your app instance runs inside it.
- **Deployment**: an object where you declare "I want 4 copies of this pod template, running image X". Kubernetes keeps reality matching that declaration.
- **ReplicaSet**: the object a Deployment creates to hold a fixed number of identical pods. Each new pod template (for example, a new image tag) gets a new ReplicaSet, and the old ones are kept as history.
- **Rolling update**: the default way to ship a new version. New pods start and old pods stop a few at a time, so some pods are always serving traffic. It exists to avoid downtime.
- **maxSurge**: how many extra pods above the desired count may exist during the update.
- **maxUnavailable**: how many pods below the desired count may be missing during the update. Both default to 25%.
- **Readiness probe**: a check (usually an HTTP endpoint) that tells Kubernetes "this pod can take traffic now". Until it passes, the pod receives no requests.
- **Rollback**: returning to an earlier ReplicaSet, which means the previous pod template.
- **Canary / blue-green**: stricter strategies. A canary sends a small share of traffic to the new version first. Blue-green runs two full environments and switches traffic between them. Plain Deployments don't do this. Tools such as Argo Rollouts, Flagger or a service mesh add it.

**The live scenario**
The orders service runs 4 pods and handles about 300 requests per second. A new release has a bug that crashes on startup when a config value is missing. Because the pods never become ready, the rolling update stalls with 1 new pod failing and 3 old pods still serving. Customers see no outage. Without a readiness probe, Kubernetes would have counted the broken pod as ready and kept replacing healthy ones. The team runs `kubectl rollout undo` and is back on the old version in about a minute.

**What the interviewer is really checking**
Whether you understand that readiness probes and the surge/unavailable settings are what make a rolling update safe. They also want to know whether you can roll back quickly and know where rollback stops working.

**How I answer it**
1. **A rolling update starts when the pod template changes** (image, env vars, probes). Scaling the replica count alone does not trigger one. The reason is that the Deployment compares templates to decide whether a new ReplicaSet is needed.
2. **The Deployment creates a new ReplicaSet and scales it up while scaling the old one down.** `maxSurge` and `maxUnavailable` set the pace and the capacity floor. For example:
   ```yaml
   strategy:
     type: RollingUpdate
     rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }
   ```
   With 4 replicas this means 5 pods at most and never fewer than 4 ready. It is safest for capacity but slower and needs spare cluster room.
3. **Each new pod must pass its readiness probe before it counts.** Only then is an old pod removed. This stops a broken version from taking over.
4. **Old pods should shut down gracefully.** They receive SIGTERM and finish in-flight requests within `terminationGracePeriodSeconds`. Otherwise users see errors during the roll.
5. **Watch the rollout** with `kubectl rollout status deployment/orders`. If it makes no progress within `progressDeadlineSeconds`, it is marked failed. It does not undo itself, so a human or pipeline must act.
6. **Roll back** with `kubectl rollout undo deployment/orders`. Use `kubectl rollout history deployment/orders` to see revisions and `--to-revision=N` to pick one. Rollback is itself a rolling update back to the old ReplicaSet, so it is also zero-downtime. It works only while old ReplicaSets are kept (`revisionHistoryLimit`, default 10).
7. **When I need more control**, I use canary or blue-green with Argo Rollouts, Flagger or a service mesh. They shift traffic in steps and roll back automatically when metrics degrade.

**Trade-offs and what can go wrong**
- No readiness probe, or a probe that is too shallow, lets bad pods count as healthy.
- During the roll, old and new versions run side by side. Their APIs and message formats must be compatible.
- Rollback does not undo database migrations. Use backward-compatible schema changes (expand, then contract).
- `maxUnavailable: 0` with no spare cluster capacity leaves new pods stuck in Pending.
- Rolling back through manual `kubectl` can drift from what is in Git. Prefer reverting the commit in GitOps setups.
- For Kafka consumers, every pod replacement triggers a consumer group rebalance. A slow rollout can cause repeated pauses and lag.

**How I'd monitor it**
- `kubectl rollout status`, plus the Deployment's available/unavailable replica counts.
- Pod restarts and CrashLoopBackOff events.
- Error rate and p99 latency per version, compared before and after the release (Prometheus/Grafana).
- Splunk searches on the new version's logs for errors in the first minutes.
- Alerts on a stalled rollout (`progressDeadlineSeconds` exceeded) and, for Kafka services, on consumer lag.

**Follow-ups to expect**
- *What if the new pods never become ready?* -> The rollout stalls, old pods keep serving, and after `progressDeadlineSeconds` it is marked failed. I then run `rollout undo`.
- *Does rollback restore the old replica count or config maps?* -> No. It restores only the old pod template. Replica count, ConfigMap contents and database state are not reverted.
- *When would you pick canary over a rolling update?* -> When a bug is costly and I want real traffic on a small slice with automatic metric checks before going wider.

**60-second answer**
A rolling update replaces pods gradually when the pod template changes. The Deployment creates a new ReplicaSet and scales it up while scaling the old one down. `maxSurge` and `maxUnavailable` control how many extra or missing pods are allowed. A new pod must pass its readiness probe before an old one is removed, so a broken release stalls instead of causing an outage. To roll back I run `kubectl rollout undo deployment/orders`, after checking `rollout history`. That is itself a zero-downtime rolling update back to the previous ReplicaSet. It doesn't revert database migrations, so I keep schema changes backward compatible. For finer control I use canary or blue-green with Argo Rollouts or Flagger, which can roll back automatically on bad metrics.

### Q24 [mid] How do you scale in Kubernetes?
tags: kubernetes, hpa, keda, cluster-autoscaler, kafka-consumers, autoscaling, basics

**Start here: the concepts**
- **Pod**: the smallest unit Kubernetes runs, usually one container of your app. "Scaling" mostly means changing how many pods run, or how big each one is.
- **Replica**: one identical copy of a pod. More replicas means more requests handled in parallel.
- **Requests and limits**: a request is the CPU/memory a pod reserves, and the scheduler uses it to pick a node. A limit is the maximum the pod may use. Autoscalers compare usage against requests.
- **HPA (Horizontal Pod Autoscaler)**: a control loop that adds or removes replicas. It watches CPU, memory or custom metrics such as requests per second (RPS).
- **VPA (Vertical Pod Autoscaler)**: adjusts a pod's requests (its size) instead of its count. It usually applies the change by restarting the pod.
- **Cluster Autoscaler / Karpenter**: add or remove nodes (the machines) when pods can't fit or nodes sit empty. Without them, new pods stay Pending.
- **KEDA**: an add-on that scales on external signals such as Kafka consumer lag or queue depth, and can scale to zero. Internally it drives an HPA.
- **Consumer lag**: how many messages are waiting that the consumer group hasn't processed yet.
- **Partition**: a Kafka topic is split into partitions. Within one consumer group, each partition is read by at most one consumer at a time.
- **Stateless**: the pod keeps no important data locally, so any copy can be added or killed freely.

**The live scenario**
An order-events service consumes a 12-partition Kafka topic. At a sale, traffic jumps from 500 to 6,000 events/sec. CPU stays low because the work is mostly waiting on a database, so CPU-based HPA never fires. Lag climbs to 2 million and processing is 20 minutes late. The team moves to KEDA on lag, with a max of 12 replicas. Lag drains in minutes. Earlier, someone had set max replicas to 30, and 18 pods sat idle.

**What the interviewer is really checking**
Whether you know the three scaling layers (pods, pod size, nodes) and can pick the right signal for the workload. Also whether you know the Kafka partition ceiling.

**How I answer it**
1. **Make the app scale-friendly first.** It should be stateless and start fast, with readiness probes and graceful shutdown. Autoscaling adds and removes pods constantly, and slow or stateful pods make that painful.
2. **Set realistic requests.** HPA's "70% CPU" means 70% of the request. A wrong request makes every scaling decision wrong.
3. **Use HPA for replicas.** Start with CPU/memory. If the bottleneck is elsewhere, use a custom metric like RPS, because CPU can look idle while users wait.
4. **Use KEDA for event-driven work.** Scale Kafka consumers on lag, because lag measures the actual backlog.
5. **Cap replicas at the partition count.** Extra consumers beyond the number of partitions get nothing to read and just waste money. To go higher, increase partitions deliberately (this affects key ordering).
6. **Use VPA to right-size pods.** It's good for finding the right requests. Don't let VPA and HPA both act on CPU/memory for the same workload, because they fight. A common pattern is VPA in recommendation-only mode.
7. **Add node scaling.** Cluster Autoscaler or Karpenter adds nodes when new pods are Pending, and removes underused ones. Without this, HPA just creates Pending pods.

**Trade-offs and what can go wrong**
- Node provisioning takes minutes, so pod scaling is faster than node scaling. Keep some headroom for spikes.
- Each consumer scale-up or scale-down triggers a Kafka rebalance, which briefly pauses consumption. Flapping replicas cause repeated pauses. Use cooldown/stabilisation windows.
- Scaling consumers doesn't help if the real bottleneck is the database. More pods then just add pressure.
- Aggressive scale-down without graceful shutdown drops in-flight work.
- Autoscaling raises cost. Always set a max.

**How I'd monitor it**
- HPA: current vs desired replicas and `kubectl describe hpa` events.
- Pods stuck in Pending, and node count over time.
- Kafka consumer-group lag per partition (Burrow, Prometheus Kafka exporter or your platform's tooling).
- Rebalance frequency, pod restarts and OOMKilled events.
- Latency and error rate during scale events, plus cost dashboards.

**Follow-ups to expect**
- *Why not just use CPU for everything?* -> CPU misses I/O-bound or queue-driven work. Use RPS or lag, which reflect real demand.
- *HPA vs VPA?* -> HPA changes the number of pods and VPA changes their size. Don't combine them on the same metric.
- *What if lag is high but replicas are at the partition count?* -> Make each consumer faster (batching, parallel processing, fixing downstream calls), or add partitions with care for ordering.

**60-second answer**
In Kubernetes I think of scaling in three layers. HPA adds or removes pod replicas, using CPU or memory by default, or custom metrics like requests per second. For queue-driven work I use KEDA to scale on Kafka consumer lag. VPA adjusts pod requests, and Cluster Autoscaler or Karpenter adds nodes so new pods have somewhere to run. For Kafka I never scale consumers beyond the partition count, because extra ones sit idle. None of this works well unless pods are stateless, start fast and shut down gracefully. I watch HPA decisions, Pending pods, consumer lag and rebalances to confirm it behaves.

### Q25 [mid] ConfigMap vs Secret, and how do you manage secrets safely?
tags: kubernetes, configmap, secret, rbac, etcd, external-secrets, secret-rotation, basics

**Start here: the concepts**
- **ConfigMap:** a Kubernetes object that holds non-sensitive settings as key-value pairs, such as a log level, a feature toggle or a service URL. It exists so you can change configuration without rebuilding the container image.
- **Secret:** the same idea, but for sensitive values like passwords, API keys and TLS certificates. It is a separate object so you can apply stricter access rules to it than to ordinary config.
- **base64:** a way to write bytes as plain text. It is an encoding, not encryption. Anyone can decode it with one command, so a Secret is not protected just because it looks scrambled.
- **etcd:** the database where the Kubernetes cluster stores all its objects, including Secrets. By default the values sit there unencrypted.
- **Encryption at rest:** a setting on the API server that encrypts Secret data before it is written to etcd. Without it, a stolen etcd backup or disk exposes every secret.
- **RBAC (role-based access control):** the rules that say which users and service accounts may read or change which objects. Anyone allowed to `get` or `list` Secrets in a namespace can read their values.
- **External secret manager:** a dedicated system (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) that stores secrets, audits access and supports rotation.
- **External Secrets Operator / CSI driver:** two ways to bring those secrets into pods. The operator copies them into native Kubernetes Secrets. The Secrets Store CSI driver mounts them directly into the pod as files.
- **Rotation:** replacing a secret regularly, or immediately after a leak, so a stolen value stops working.

**The live scenario**
A payments team ran about 15 services. A security audit found a Secret YAML with the production database password committed to Git, readable by roughly 40 developers. The team also learned that a broad "view everything" role let a CI service account list Secrets. They rotated the password, but 4 services read it as an environment variable, so each needed a rolling restart. One service was missed and failed at 2 a.m. when the old password expired.

**What the interviewer is really checking**
Whether you know that a Secret is only base64-encoded, not encrypted, and whether you can describe layered protection: encryption, access control, external storage and rotation.

**How I answer it**
1. **Use a ConfigMap for non-sensitive settings and a Secret for sensitive ones.** This lets you give the two different permissions, and Kubernetes can handle Secrets more carefully (for example, it avoids writing them to disk on nodes).
2. **State plainly that a Secret is base64-encoded, not encrypted.** Treat it as readable by anyone with access to the object or to etcd.
3. **Turn on encryption at rest for etcd.** On managed clusters this usually means enabling KMS-backed encryption. Otherwise a leaked backup exposes everything.
4. **Lock down RBAC.** Give each app its own service account, and grant `get` on only the specific Secrets it needs. Avoid wildcard roles. Remember that anyone who can create a pod in a namespace can mount its Secrets, so restrict that too.
5. **Keep secrets out of Git.** Store them in an external manager and sync them with External Secrets Operator or the CSI driver. If you must keep them in Git, encrypt them first (Sealed Secrets or SOPS).
6. **Prefer mounting as files over environment variables.** Env vars can leak through logs, crash dumps and child processes, and they never change while the pod is running. Mounted files are refreshed after a rotation (except with `subPath`), so the app can re-read them.
7. **Rotate regularly and after any suspected leak.** Design the app to reload credentials, or automate restarts, so rotation is routine rather than an emergency.

```yaml
volumes:
- name: db-creds
  secret: { secretName: db-creds, defaultMode: 0400 }
```

**Trade-offs and what can go wrong**
- External managers add moving parts. If the manager is down, new pods may fail to start.
- Syncing into native Secrets means the value still lands in etcd, so encryption at rest is still needed.
- File mounts update after a delay, and the app must actually re-read the file.
- Common mistakes: believing base64 is security, committing Secret YAML, over-broad RBAC, and printing config or env vars in logs.

**How I'd monitor it**
- Enable Kubernetes audit logs and search them (for example in Splunk) for `get`/`list` on `secrets` by unexpected users or service accounts.
- Alert on failed secret syncs (External Secrets status) and on secrets close to expiry.
- Scan Git history and CI for committed secrets with a secret-scanning tool.
- Review RBAC periodically for wildcard or cluster-wide Secret access.
- Track the age of each credential against your rotation policy.

**Follow-ups to expect**
- *Is a Secret encrypted?* -> Not by default. It is base64-encoded in etcd until you enable encryption at rest.
- *Env var or mounted file?* -> Files are usually safer and pick up rotated values. Env vars need a pod restart to change.
- *Why use an external secret manager?* -> It gives central storage, access audit trails, fine-grained policies and automated rotation, none of which native Secrets provide.

**60-second answer**
A ConfigMap holds non-sensitive settings, and a Secret holds sensitive values like passwords and keys. A Secret is only base64-encoded, which anyone can decode, and by default it sits unencrypted in etcd. So I enable encryption at rest and restrict RBAC so each service account can read only the Secrets it needs. I keep secrets out of Git and store them in an external manager such as Vault, AWS Secrets Manager or Azure Key Vault, synced with External Secrets Operator or the CSI driver. I prefer mounting them as files rather than env vars, because files refresh after rotation and env vars leak more easily. Finally, I rotate regularly and watch audit logs for unexpected Secret reads.

### Q26 [mid] How do pods communicate and how is traffic exposed?
tags: kubernetes, services, ingress, networking, networkpolicy, dns, basics

**Start here: the concepts**
- **Pod**: the smallest unit Kubernetes runs, one or more containers sharing one network identity. Each pod gets its own IP address, but that IP is temporary. When a pod is replaced, the new one gets a different IP.
- **Service**: a stable virtual address placed in front of a changing set of pods. It exists because pod IPs change. A label selector decides which pods belong to it.
- **ClusterIP**: the default Service type. It gets a virtual IP reachable only inside the cluster. Cluster DNS (CoreDNS) gives it a name such as `payment.shop.svc.cluster.local`, or just `payment` from the same namespace.
- **Readiness**: a Service only sends traffic to pods whose readiness probe passes. Kubernetes tracks those pods in an *EndpointSlice* list, and kube-proxy on each node (or the network plugin) routes to them.
- **NodePort**: opens the same port on every node, so outside traffic can reach the Service via `nodeIP:port`.
- **LoadBalancer**: asks the cloud (AWS, Azure) to create an external load balancer pointing at the Service. Usually one per Service, which costs money.
- **Ingress**: rules for HTTP routing (L7), such as host and path routing and TLS termination, so one entry point serves many Services. It needs an **Ingress controller** (e.g. NGINX) to work. **Gateway API** is the newer, more expressive replacement. OpenShift has its own *Routes*.
- **NetworkPolicy**: firewall rules between pods. By default all pods can talk to all pods. Once a policy selects a pod, only the traffic the policies allow reaches it. Policies are enforced by the network plugin (CNI), so it must support them.

**The live scenario**
A shop runs `orders` calling `payment`, with 6 payment pods. A developer hardcoded a payment pod IP in config "because it worked". During a routine rolling update, all 6 pods were replaced. For about 3 minutes, roughly 40% of checkouts failed with connection timeouts. The fix was to call `http://payment` through its Service. Later, a security review found that a debug pod in the same cluster could reach the orders database, because no NetworkPolicy existed.

**What the interviewer is really checking**
Whether you know pod IPs are ephemeral and Services give stable discovery. Also whether you can separate internal traffic (Service), external traffic (NodePort, LoadBalancer, Ingress) and restriction (NetworkPolicy).

**How I answer it**
1. **Pod to pod:** every pod has its own IP, and any pod can reach any other directly, with no NAT. I never depend on those IPs, because pods are replaced during deploys, scaling and failures.
2. **Use a Service for stability:** callers use the Service name via DNS. The Service spreads requests across ready pods only, so a pod that is starting up or failing its readiness probe gets no traffic.
   ```yaml
   kind: Service
   spec: { selector: {app: payment}, ports: [{port: 80, targetPort: 8080}] }
   ```
3. **Expose externally, cheapest suitable option:** NodePort for simple or test cases. LoadBalancer for one Service needing a cloud load balancer. For many HTTP services I use one Ingress (or Gateway API) with host/path rules and TLS, behind a single load balancer.
4. **Restrict with NetworkPolicy:** since the default is allow-all, I add a default-deny policy per namespace, then allow only needed flows (e.g. `orders` to `payment`). I also allow DNS egress, or name lookups break.

**Trade-offs and what can go wrong**
- Ingress resources do nothing without a controller installed.
- NetworkPolicy is silently ignored if the CNI doesn't enforce it. Test it.
- Default-deny without a DNS allowance causes confusing "unknown host" errors.
- One LoadBalancer per Service gets expensive.
- A Service with a wrong selector has no endpoints, so traffic goes nowhere.
- Kubernetes load-balancing happens per connection, so long-lived connections (gRPC, HTTP/2) can stick to a few pods.

**How I'd monitor it**
- `kubectl get endpointslices` (or `kubectl get endpoints`) to confirm a Service has ready pods.
- Readiness failures and restart counts.
- Ingress controller metrics: 4xx/5xx rate, latency, and upstream connect errors.
- CoreDNS error rates.
- In Splunk, search app logs for `UnknownHostException`, `Connection refused` or `timed out`, grouped by target host and time, to spot a bad rollout or blocked policy.
- Alert when a Service's ready endpoints drop to zero.

**Follow-ups to expect**
- *What is a headless Service?* -> `clusterIP: None`. DNS returns the individual pod IPs instead of one virtual IP, which is useful for StatefulSets such as Kafka or databases where clients need specific pods.
- *How does a Service know which pods are ready?* -> It selects pods by label and tracks only those passing readiness probes in EndpointSlices. kube-proxy routes to that list.
- *Ingress vs LoadBalancer?* -> LoadBalancer is L4 and one per Service. Ingress is L7 routing, many services behind one entry point, with TLS and path rules.

**60-second answer**
Every pod gets its own IP and can reach any other pod directly, but those IPs change whenever pods are replaced, so we never hardcode them. Instead we put a Service in front, usually ClusterIP, which gives a stable DNS name and load-balances only across ready pods. To expose traffic outside, NodePort opens a port on every node and LoadBalancer creates a cloud load balancer. For many HTTP services I use an Ingress, or Gateway API, with a controller for host and path routing and TLS. By default every pod can talk to every pod, so I add NetworkPolicies, starting with default-deny and allowing only needed flows, remembering the network plugin must enforce them. I'd monitor Service endpoints, ingress 5xx rates and connection errors in logs.

### Q27 [mid] A pod is in CrashLoopBackOff. How do you debug?
tags: kubernetes, crashloopbackoff, kubectl, troubleshooting, probes, containers, basics

**Start here: the concepts**
- **Pod**: the smallest unit Kubernetes runs. It wraps one or more containers that share a network and storage.
- **Container restart policy**: by default, if a container exits, the kubelet (the agent on each node) starts it again.
- **CrashLoopBackOff**: a status, not a root cause. It means the container keeps starting and dying, so Kubernetes waits longer between restarts (10s, 20s, 40s and so on, capped at about 5 minutes). It says "restarting repeatedly", nothing more.
- **Exit code**: the number a process returns when it ends. 0 is success and 1 is a generic application error. 126 or 127 means the command can't be run or isn't found. Codes above 128 mean a signal killed it: 137 is SIGKILL (128+9) and 143 is SIGTERM (128+15).
- **OOMKilled**: the container went over its memory limit and the Linux kernel killed it. This is the most common reason for 137, but not the only one.
- **Probe**: a health check run by the kubelet. A *liveness* probe failure makes the kubelet kill and restart the container. A *readiness* probe only removes the pod from traffic.
- **Ephemeral debug container**: a temporary extra container attached to a running pod with `kubectl debug`, used for a shell and tools when the app image has none.

**The live scenario**
After a Friday release, an orders service (6 pods, about 800 requests/second) had 3 new pods in CrashLoopBackOff. The remaining pods carried the load, and p99 latency rose from 200 ms to 900 ms. The restart count was climbing. The new build had a bigger startup cache, so the pods ran out of memory during startup. Nobody had checked the exit code, and the first reaction was "raise the limit". That would have hidden a memory regression.

**What the interviewer is really checking**
Whether you follow a systematic path from symptom to evidence to root cause, rather than guessing or restarting things. They also want to see that you know CrashLoopBackOff is only a symptom.

**How I answer it**
1. **Run `kubectl describe pod <pod>`.** Read *Last State*, *Reason*, *Exit Code* and the *Events* section. This tells you how the container died, which decides where to look next.
2. **Run `kubectl logs <pod> --previous`.** The current container may have just restarted with empty logs, and `--previous` shows the output of the instance that crashed. Use `-c <container>` if the pod has several.
3. **Read the exit code.**
   - 137 with reason OOMKilled: memory limit exceeded.
   - 137 or 143 without OOMKilled: often a failing liveness probe, where the kubelet killed the container.
   - 1: the application failed itself, for example a stack trace or a bad config value.
   - 126 or 127: wrong command or entrypoint.
4. **Check probes.** A liveness probe that fires before the app finishes starting kills a healthy but slow container. Compare the probe path, port and timing with the real startup time, and consider a startup probe.
5. **Check config and image.** Look for wrong environment values, an unreachable database or missing mounted files. Note that a missing Secret or ConfigMap reference usually shows `CreateContainerConfigError`, and a wrong image name shows `ImagePullBackOff`, not CrashLoopBackOff. A wrong command or args does cause CrashLoopBackOff.
6. **Look at the timeline.** `kubectl get events --sort-by=.lastTimestamp` shows what happened across the namespace in order, such as node pressure, evictions or failed mounts.
7. **Get a shell if logs aren't enough.** `kubectl exec` fails if the container is already dead. Use `kubectl debug` to attach an ephemeral container, or `--copy-to` to run a modified copy of the pod.
8. **Fix the root cause.** Don't just raise limits. Profile the memory, fix the probe timing or correct the config.

```
kubectl debug -it <pod> --image=busybox --target=<container>
```

**Trade-offs and what can go wrong**
- Raising memory limits hides leaks and wastes node capacity.
- Removing the liveness probe stops the restarts but leaves real hangs undetected.
- The backoff means each retry takes longer, so recovery after a fix can take up to 5 minutes unless you delete the pod.
- Logs are lost if the pod was rescheduled, so centralised logging matters.
- Blaming the app when the real cause is the node (disk or memory pressure) wastes time.

**How I'd monitor it**
- Alert on `kube_pod_container_status_restarts_total` rising, and on `kube_pod_container_status_waiting_reason{reason="CrashLoopBackOff"}`.
- Track `kube_pod_container_status_last_terminated_reason` to catch OOMKilled.
- Watch memory usage against the limit.
- In Splunk, search the app's logs by pod name around the restart times, and search Kubernetes event logs for `OOMKilling` and `Unhealthy` (probe failures).
- Use a canary or rolling update so a crashing release stops at one pod.

**Follow-ups to expect**
- *Why is exit code 137 not always OOM?* -> 137 means SIGKILL. OOM is one cause, but a liveness-probe kill after the grace period can also end this way. Confirm with the `OOMKilled` reason in `describe`.
- *`kubectl logs` shows nothing. What now?* -> Use `--previous`, check events for startup failures such as a bad command, and use `kubectl debug` to inspect the pod.
- *How do you stop a bad release from taking down all pods?* -> Use a rolling update with readiness probes and `maxUnavailable`, and roll back with `kubectl rollout undo`.

**60-second answer**
CrashLoopBackOff just means the container keeps dying and Kubernetes is waiting longer between restarts, so I look for why it dies. First I run `kubectl describe pod` and read the last state, exit code and events. Then I run `kubectl logs --previous` to see the crashed instance's output. The exit code points the way: 137 with OOMKilled is memory, 1 is an application error, and 126 or 127 is a bad command. I also check whether a liveness probe is killing a slow-starting app, and I look at the events timeline. If I need a shell, I use `kubectl debug`, because `exec` won't work on a dead container. I fix the real cause rather than just raising limits.

### Q28 [mid] Pod stuck in Pending / ImagePullBackOff?
tags: kubernetes, pod-scheduling, troubleshooting, imagepullbackoff, pending, kubectl, basics

**Start here: the concepts**
- **Pod:** the smallest unit Kubernetes runs. It wraps one or more containers that share a network and storage.
- **Scheduler:** the Kubernetes component that picks which node (machine) a new pod runs on. A pod it cannot place stays **Pending**.
- **Requests:** the CPU and memory a pod declares it needs. The scheduler places pods using these numbers, not live usage. A node can look idle and still be "full" on paper.
- **Node selector / affinity:** rules that say "only run on nodes with this label" or "prefer these nodes".
- **Taint / toleration:** a taint marks a node as off-limits unless a pod carries a matching toleration. It reserves nodes, for example for GPU or system workloads.
- **PVC (PersistentVolumeClaim):** a pod's request for disk storage. If no matching volume or storage class can satisfy it, it stays unbound and the pod cannot start.
- **Image and registry:** an image is the packaged application. A registry (ECR, ACR, Docker Hub) is the server that stores it. The node must pull the image before starting the container.
- **imagePullSecret:** credentials stored in Kubernetes that let a node log in to a private registry.
- **ImagePullBackOff:** the node failed to pull the image (first seen as `ErrImagePull`), so Kubernetes retries with growing delays.
- **`kubectl describe pod`:** shows the pod's details and an **Events** section, which is a log of what the scheduler and kubelet tried and why they failed.

**The live scenario**
A payments service release goes out at 10:00. The new version needs 8 replicas, and 3 pods are not serving after 10 minutes. Two sit in **Pending** and one in **ImagePullBackOff**. The team's first instinct is to restart things. The Pending pods' events say `0/6 nodes available: Insufficient memory`. The new version requests 2 GiB each instead of 512 MiB, and the cluster cannot fit them. The third pod's events say `manifest unknown`, because the CI job pushed tag `1.4.2` but the YAML says `1.4.2-rc1`. Reading the events fixes both problems in minutes.

**What the interviewer is really checking**
Whether you have a method, not a memorised list. Can you tell "never scheduled" from "scheduled but can't start", and do you go to `describe` events first?

**How I answer it**
1. **Check the status first.** `kubectl get pod` tells you which stage failed. Pending means the scheduler has not placed the pod. ImagePullBackOff means the pod was placed on a node but the image pull failed. These are different problems with different fixes.
2. **Read the events.** `kubectl describe pod <name>` puts the reason in plain text at the bottom, so you don't have to guess.
```
kubectl describe pod payments-7d9f -n prod   # read the Events section
```
3. **Pending causes:**
   - *Insufficient CPU/memory:* the scheduler compares **requests** with free capacity on each node. Fix by lowering oversized requests, adding nodes (or letting the cluster autoscaler do it), or freeing capacity.
   - *Unsatisfied node selector/affinity:* no node carries the required label. Fix the label or the rule.
   - *Taints:* nodes are tainted and the pod has no toleration. Add the toleration or use other nodes.
   - *Unbound PVC:* check `kubectl get pvc`. The storage class may be missing, or the volume may be in a different availability zone from the only nodes that fit.
   - *Namespace ResourceQuota* can also block pods.
4. **ImagePullBackOff causes:**
   - *Wrong image name or tag:* the image does not exist. This is the most common cause.
   - *Private registry without credentials:* add an `imagePullSecret`. It must be in the **same namespace** as the pod, and credentials expire (ECR tokens, for example).
   - *No network path* from the node to the registry: firewall, proxy, DNS or a missing NAT.
   - *Registry rate limits*, such as anonymous Docker Hub pulls.
5. **Fix at the source and prevent repeats.** Change the manifest or pipeline, not just the live pod. Use immutable tags or digests, and make CI check the image exists before deploying.

**Trade-offs and what can go wrong**
- Requests set too high leave pods Pending and waste money. Requests set too low pack nodes tightly and cause noisy-neighbour and OOM problems.
- Adding nodes hides a bad request value instead of fixing it.
- Using `latest` tags makes pulls unpredictable and rollbacks unclear.
- Don't confuse Pending with `CrashLoopBackOff`. In that case the container started and then crashed, so you debug with logs, not scheduling.

**How I'd monitor it**
- Alert on pods in Pending for more than about 5 minutes (kube-state-metrics: `kube_pod_status_phase{phase="Pending"}`).
- Alert on waiting reasons such as ImagePullBackOff (`kube_pod_container_status_waiting_reason`).
- Track node allocatable vs requested, and cluster autoscaler events.
- In Splunk, search cluster events for `FailedScheduling`, `ErrImagePull` and `Failed to pull image`.
- Make the pipeline fail if `kubectl rollout status` times out.

**Follow-ups to expect**
- *Node shows 20% CPU use but pods are Pending. Why?* -> The scheduler uses requests, not actual usage, so the node is already fully reserved.
- *How do you fix ImagePullBackOff on a private registry?* -> Create a registry secret in the pod's namespace and reference it as `imagePullSecrets` in the pod spec or the service account. Check that it has not expired.
- *Pod is Pending only in one availability zone. Why?* -> Often the PVC is bound to a volume in another zone, or the nodes in that zone are full or tainted.

**60-second answer**
First I check the pod status, because it tells me the stage that failed. Pending means the scheduler could not find a node. ImagePullBackOff means a node was chosen but could not download the image. Then I run `kubectl describe pod` and read the Events. For Pending, the usual reasons are that the CPU or memory requests don't fit any node, a node selector or taint rule excludes every node, or a PVC is unbound. For ImagePullBackOff, I check for a wrong image name or tag, missing or expired registry credentials in that namespace, and network access to the registry. I fix the manifest or pipeline at the source, and I alert on pods stuck in Pending or ImagePullBackOff so we notice before users do.

### Q29 [mid] What are Helm and Kustomize?
tags: helm, kustomize, kubernetes, yaml, gitops, argocd, deployment, basics

**Start here: the concepts**
- **Kubernetes manifest**: a YAML file describing what you want to run (a Deployment, a Service, a ConfigMap). Real apps need many of these files, and they are nearly identical across dev, test and prod.
- **The problem both tools solve**: copy-pasting the YAML per environment leads to drift, where prod quietly differs from test in ways nobody remembers. Helm and Kustomize let you keep one base definition and vary only what differs.
- **Helm**: a package manager for Kubernetes. A **chart** is a folder of YAML **templates** with placeholders such as `{{ .Values.replicas }}`. A **values file** fills the placeholders (one per environment). Installing a chart creates a **release**, a named, versioned install. Helm keeps the release history in the cluster, so `helm rollback` can return to an earlier revision.
- **Kustomize**: it keeps plain, valid YAML with no placeholders. An **overlay** (e.g. `prod`) points to a **base** and applies **patches**, such as "change replicas to 6". It is built into `kubectl` (`kubectl apply -k`).
- **GitOps**: Git is the single source of truth for what should run. A tool like **Argo CD** or **Flux** watches Git and applies it to the cluster. It continuously **reconciles**: if someone changes the cluster by hand (**drift**), the tool detects it and puts it back, or flags it. These tools can render both Helm charts and Kustomize overlays.

**The live scenario**
A team runs 12 microservices across dev, test and prod, with copy-pasted YAML (about 36 sets of files). During an incident someone raised a memory limit by hand on one prod service with `kubectl edit`. Two weeks later the next release overwrote it, the pods were OOMKilled, and about 8% of requests failed for 15 minutes. The team moved to one Helm chart for the services (with a values file per environment) and Git-driven deploys with Argo CD, so hand edits are detected and reverted.

**What the interviewer is really checking**
Whether you know the different philosophies (templating vs patching), when to pick each, and that you understand deployment as "desired state in Git", not people running commands by hand.

**How I answer it**
1. **Start with the problem**: the same app is deployed to several environments with small differences. Reason: this shows why the tools exist, not just what they are.
2. **Explain Helm**: templates plus values, packaged as a chart, installed as a release with history and rollback. Reason: it suits apps you want to package, version and reuse, and third-party software (databases, ingress controllers) is usually shipped as charts.
3. **Explain Kustomize**: plain YAML plus overlays that patch it, with no template language. Reason: the files stay valid YAML you can read directly, so there is less to learn and debug.
4. **Compare**: Helm is more powerful (conditionals, loops, packaging) but templates get hard to read. Kustomize is simpler but cannot easily express heavy logic. Many teams combine them, e.g. render a third-party chart, then patch it with Kustomize.
5. **Add GitOps**: Argo CD or Flux applies what is in Git and reconciles drift. Reason: this gives an audit trail, reviewable changes through pull requests, and consistent environments.

```
helm upgrade --install orders ./chart -f values-prod.yaml
```

**Trade-offs and what can go wrong**
- Helm templates with too many conditionals become unreadable, and a bad indent can produce subtly wrong YAML.
- Kustomize patches can get fragile when the base changes, and overlays multiply with many environments.
- Secrets in values files committed to Git are a real risk. Use sealed or external secret tooling instead.
- With GitOps, rollback should be a `git revert`. Running `helm rollback` by hand creates drift that the tool may overwrite.
- Auto-sync with auto-prune can delete resources unexpectedly, so test it first.

**How I'd monitor it**
- Argo CD or Flux sync status (Synced/OutOfSync) and health, with alerts on apps that stay OutOfSync.
- `helm list` and `helm history` to see releases and revisions.
- Run `helm template` or `kustomize build` in CI, plus a diff, to see what will change before merging.
- After each deploy, check rollout status, restarts and error rate on dashboards.

**Follow-ups to expect**
- *When would you choose Helm over Kustomize?* -> When you need to package and version an app for reuse, need logic in the config, or install third-party software shipped as charts.
- *How does Helm roll back?* -> It stores each release revision in the cluster, and `helm rollback <release> <revision>` reapplies an older one. Under GitOps, prefer reverting in Git.
- *What does "reconcile drift" mean?* -> The tool compares the cluster with Git and brings the cluster back to match Git, or alerts you.

**60-second answer**
Both tools solve the problem of deploying the same app to many environments without copy-pasting YAML. Helm is a package manager: a chart holds templates with placeholders, a values file per environment fills them in, and each install is a release with history, so you can roll back. Kustomize keeps plain YAML and applies patches in overlays, such as more replicas in prod, with no templating, and it is built into kubectl. I use Helm for packaging and third-party software, and Kustomize for simple per-environment tweaks. On top of that, GitOps tools like Argo CD or Flux keep the desired state in Git, apply it, and continuously fix drift, so manual cluster edits don't survive.

### Q30 [senior] What is a StatefulSet and when do you avoid running databases in K8s?
tags: kubernetes, statefulset, persistent-volume, stateful-workloads, operators, managed-services, basics

**Start here: the concepts**
- **Pod:** the smallest unit Kubernetes runs, usually one container. Pods are disposable. Kubernetes kills and recreates them freely.
- **Stateless vs stateful:** a stateless app keeps nothing important locally, so any replica can replace any other. A stateful system (database, Kafka broker) keeps data on disk, and each replica has its own data and role.
- **Deployment:** the normal controller for stateless apps. Its pods get random names, are interchangeable, and share no identity.
- **StatefulSet:** a controller for pods that must not be interchangeable. It gives each pod:
  - a stable name (`db-0`, `db-1`, `db-2`) that survives restarts;
  - ordered startup and rolling updates (0, then 1, then 2; updates go in reverse). This is the default; `podManagementPolicy: Parallel` turns it off;
  - its own persistent volume, created from a template, that reattaches to the same pod after a restart.
- **Persistent volume (PV) / claim (PVC):** a PV is disk storage that outlives pods. A PVC is a pod's request for one.
- **Headless Service:** a Service with no virtual IP. It gives each StatefulSet pod a stable DNS name such as `db-0.db`, so replicas can find each other.
- **Operator:** software that encodes an expert's runbook (failover, backups, upgrades) for one system, such as a database, and runs it automatically inside the cluster.
- **Managed service:** the cloud vendor runs the system for you (RDS, MSK for Kafka, Cosmos DB).

Important correction: a StatefulSet gives identity and storage only. It does not replicate data, take backups, elect leaders, or fail over. The database software or an operator must do those.

**The live scenario**
Illustrative numbers: a team ran a 3-broker Kafka cluster on a StatefulSet with an operator, and it was stable. The same team ran a single PostgreSQL pod on Kubernetes without an operator. During a node drain the pod went `Pending` for about 25 minutes. Its volume lived in zone A, but the free capacity was in zone B. Checkout (about 2,000 orders/min) was down. Their last backup had never been test-restored.

**What the interviewer is really checking**
Whether you know that a StatefulSet solves identity and storage but not operations, and whether you can judge whether running a database yourself is worth the burden.

**How I answer it**
1. **Define the problem.** Stateful pods need a fixed identity and their own disk. A Deployment cannot give that, because its pods are random and share nothing.
2. **Explain what StatefulSet adds.** It provides stable names, a headless Service for stable DNS, ordered rollout, and one PVC per pod via `volumeClaimTemplates`. Ordering matters because a database often needs the primary or quorum healthy before the next replica is touched.
   ```yaml
   kind: StatefulSet
   spec:
     serviceName: db          # headless Service
     volumeClaimTemplates: [...]  # one PVC per pod
   ```
3. **State its limits.** Deleting a StatefulSet does not by default delete its PVCs (newer Kubernetes versions have a retention-policy setting). It does not replicate or back up data, and storage is often tied to a zone.
4. **Say when I run it in Kubernetes.** I do so when I have a mature operator, a team with operational skill, and a reason such as portability, cost at scale, or a Kafka/Cassandra platform team.
5. **Say when I avoid it.** For critical relational or document databases without that expertise, I use a managed service. Backups, point-in-time restore, patching, failover and multi-zone replication are then the vendor's job, and the cost of running it ourselves is usually higher than the fee.
6. **Decide by testing.** If we can't show a tested restore and a tested failover, the database stays out of Kubernetes.

**Trade-offs and what can go wrong**
- Managed services cost more per unit and bring lock-in and fewer tuning options, but they remove on-call risk.
- Self-run: zone-bound volumes strand pods, slow storage causes latency, node drains break quorum, and the team skips restore tests.
- Setting resource limits too low gets pods killed (OOM) mid-write.
- Common mistake: believing "StatefulSet = highly available database".
- Use PodDisruptionBudgets so upgrades don't take down too many replicas at once.

**How I'd monitor it**
- Pod restarts and `Pending` pods; PVC usage and free space.
- Disk latency and IOPS.
- Replication lag, and Kafka under-replicated partitions.
- Backup job success and the age of the last restore test.
- Splunk searches for OOMKilled, `FailedScheduling` and volume-attach errors, with alerts on each.

**Follow-ups to expect**
- *Why not a Deployment for a database?* -> Its pods have random names and shared or no storage, so replicas can't keep their own data or roles across restarts.
- *What happens to the data if a StatefulSet pod dies?* -> The pod is recreated with the same name and reattaches to its same PVC, but only if that volume can be attached where the pod is scheduled (zone constraints).
- *Is a StatefulSet enough for HA?* -> No. Replication and failover come from the database or an operator, plus PodDisruptionBudgets and multi-zone placement.

**60-second answer**
A StatefulSet is a Kubernetes controller for pods that need a fixed identity. Each pod gets a stable name like `db-0`, ordered startup and updates, a stable DNS name through a headless Service, and its own persistent volume that follows it across restarts. That's why it fits Kafka, Cassandra and databases. But it only gives identity and storage. It doesn't replicate data, back it up, or fail over. Running a database myself means owning backups, upgrades, failover and zone-bound volumes. So I avoid it for critical databases and prefer RDS, MSK or Cosmos DB, unless we have a mature operator, a skilled team, and a tested restore and failover.

### Q31 [senior] Pod disruption, anti-affinity and topology spread - why?
tags: kubernetes, pod-disruption-budget, pod-anti-affinity, topology-spread, high-availability, graceful-shutdown, basics

**Start here: the concepts**
- **Replica**: one running copy of your pod. Several replicas let the service keep working when one copy dies.
- **Node and zone**: a node is a machine that runs pods. A zone is a data-centre section of a cloud region. Nodes and zones fail independently, which is why spreading across them helps.
- **Scheduler**: the Kubernetes component that picks a node for each new pod. By default it does not guarantee your replicas land on different nodes or zones.
- **podAntiAffinity**: a rule saying "do not place this pod near pods with label X". "Near" is defined by a topology key such as `kubernetes.io/hostname` (node) or `topology.kubernetes.io/zone`. The `required...` form is a hard rule. The `preferred...` form is a soft hint.
- **topologySpreadConstraints**: a rule saying "keep the number of matching pods roughly even across nodes or zones". `maxSkew` is the largest allowed difference between the fullest and emptiest domain. `whenUnsatisfiable` chooses `DoNotSchedule` (hard) or `ScheduleAnyway` (soft).
- **Voluntary vs involuntary disruption**: voluntary means a planned action such as `kubectl drain`, a node upgrade or autoscaler scale-down. Involuntary means a crash, hardware failure or zone outage.
- **PodDisruptionBudget (PDB)**: a policy object with `minAvailable` or `maxUnavailable`. It makes the eviction API refuse to remove too many pods at once during voluntary disruptions. It does nothing for involuntary ones.
- **Graceful termination**: when a pod is deleted, Kubernetes runs the `preStop` hook, sends SIGTERM, and waits up to `terminationGracePeriodSeconds` (default 30s) before SIGKILL. The wait covers the hook time too.

**The live scenario**
A payments API runs 4 replicas at about 800 requests/second. The scheduler packed 3 replicas onto one node. During a monthly node-pool upgrade, that node was drained. Three of the four pods vanished at once, the remaining pod saturated, and p99 latency went from 120 ms to 6 s for about 90 seconds. Some in-flight requests also returned 502 because the pods were killed while the load balancer was still sending traffic to them. After the fix (spread across zones, PDB `maxUnavailable: 1`, `preStop` sleep), the next upgrade showed no error spike.

**What the interviewer is really checking**
Whether you can separate three different problems: where pods are placed, how many may be removed during planned work, and how a single pod exits cleanly. Also whether you know the limits of each tool.

**How I answer it**
1. **Spread the replicas.** Without a rule, one node or zone can hold most replicas, so one failure takes most of the service. I prefer `topologySpreadConstraints` because they allow a controlled imbalance (`maxSkew`). Hard anti-affinity allows only one pod per domain, so with 6 replicas and 3 zones the extra pods stay Pending.
   ```yaml
   topologySpreadConstraints:
   - maxSkew: 1
     topologyKey: topology.kubernetes.io/zone
     whenUnsatisfiable: DoNotSchedule
     labelSelector: { matchLabels: { app: payments } }
   ```
2. **Add a node-level spread too.** A zone key protects against zone loss. A hostname key protects against single-node loss. I often combine zone (hard) with hostname (soft).
3. **Add a PDB for planned disruption.** A drain evicts pods one by one, and the PDB makes the eviction API refuse any eviction that would drop availability below the budget. With 4 replicas I would use `maxUnavailable: 1`.
4. **Make each exit graceful.** Pods removed by a drain still get killed. A `preStop` sleep of a few seconds lets the Service and load balancer stop routing to the pod before SIGTERM arrives. The app then finishes in-flight work, and `terminationGracePeriodSeconds` must be longer than hook plus drain time.
5. **State the limits.** Spreading reduces the blast radius of a failure but does not prevent it. A PDB cannot stop a node crash. Rolling updates of a Deployment are governed by `maxUnavailable`/`maxSurge`, not by the PDB.

**Trade-offs and what can go wrong**
- A PDB with `minAvailable` equal to the replica count blocks every drain, so upgrades hang. A single-replica service with `minAvailable: 1` has the same problem.
- Hard rules cause Pending pods when capacity is short in a zone. Use soft rules where availability of scheduling matters more than perfect spread.
- Spread constraints apply at scheduling time only. After pods are deleted, the layout can become uneven. The descheduler can rebalance.
- Hard anti-affinity on large deployments is expensive for the scheduler. Spread constraints are generally preferred.
- Spreading across zones can add cross-zone network cost and latency.
- A `preStop` sleep that exceeds the grace period gets cut off by SIGKILL.

**How I'd monitor it**
- `kubectl get pdb`: watch `ALLOWED DISRUPTIONS`. 0 means drains will block.
- `kubectl get pods -o wide`: check the node and zone distribution per app.
- Alert on pods Pending longer than a few minutes (hard-rule symptom).
- Track 5xx rate and p99 latency during deployments and node upgrades. In Splunk, search for 502/503 spikes in ingress logs aligned with drain times.
- Watch `kube_poddisruptionbudget_status_*` metrics (kube-state-metrics) and kube events for eviction failures.

**Follow-ups to expect**
- *Does a PDB protect me when a node crashes?* -> No. It only governs voluntary evictions, so you need spreading and enough replicas.
- *Anti-affinity or topology spread?* -> Spread for even distribution with tolerated skew. Anti-affinity when you truly need "never together".
- *Why a `preStop` sleep?* -> Endpoint removal and SIGTERM happen in parallel, so the sleep gives traffic routing time to catch up.

**60-second answer**
These three features solve different failure cases. Topology spread constraints, or pod anti-affinity, make the scheduler place replicas on different nodes and zones, so one failure cannot take out most of the service. A PodDisruptionBudget limits how many pods can be evicted at once during planned work like a node drain, but it does not help with crashes. A `preStop` hook plus a sensible termination grace period lets each pod finish requests and be removed from load balancing before it stops. I'd use spread with `maxSkew: 1` across zones, a PDB of `maxUnavailable: 1`, and watch for Pending pods and for drains blocked by a PDB. The common mistake is a PDB that allows zero disruptions, which stops upgrades.

### Q32 [senior] RBAC and security best practices in Kubernetes?
tags: kubernetes, rbac, security, networkpolicy, pod-security, admission-control, secrets, basics

**Start here: the concepts**
- **RBAC (Role-Based Access Control):** the Kubernetes system that decides who may do what to which API objects. It is allow-only: you grant permissions, and there are no "deny" rules. It exists so nobody, human or program, gets more power than their job needs.
- **Role / ClusterRole:** a list of permissions such as "can `get` and `list` Pods". A Role applies inside one namespace. A ClusterRole applies cluster-wide.
- **RoleBinding / ClusterRoleBinding:** attaches a Role to a user, group or ServiceAccount.
- **ServiceAccount:** the identity a Pod uses when it talks to the Kubernetes API. If a Pod is hacked, the attacker inherits this identity.
- **`cluster-admin`:** the built-in all-powerful role. Binding it to an app means one compromised Pod controls the whole cluster.
- **Namespace:** a logical partition of the cluster, used per team or environment. It scopes names and RBAC, but alone it is not a hard security wall.
- **Pod Security Standards (PSS):** three built-in profiles (privileged, baseline, restricted) describing how safe a Pod's settings must be. They are enforced by the built-in Pod Security Admission. The older PodSecurityPolicy was removed in Kubernetes 1.25.
- **NetworkPolicy:** a firewall rule for Pod-to-Pod traffic. By default every Pod can reach every Pod. It only works if the network plugin (CNI) supports it.
- **Admission policy:** a gatekeeper that checks or changes objects before they are stored, using tools like Kyverno or OPA Gatekeeper.
- **Image scanning / signing:** scanning finds known vulnerabilities in an image. Signing proves the image came from your pipeline and was not swapped.
- **Audit logs:** a record of who called the API, when, and what they did.

**The live scenario**
A payments team runs 30 Pods in a shared cluster. A vulnerable library lets an attacker run commands inside one Pod. A developer had bound `cluster-admin` to that Pod's ServiceAccount "to make a deploy script work". In about 10 minutes the attacker read Secrets in 40 namespaces, and flat networking let them reach the database. Afterwards the team applied least-privilege RBAC, default-deny network rules and non-root Pods, and the same flaw would have been contained to one Pod.

**What the interviewer is really checking**
Whether you think in layers (identity, workload, network, supply chain, secrets, detection) and can explain what each layer stops, rather than reciting a checklist.

**How I answer it**
1. **Namespaces per team and environment.** This gives RBAC, quotas and network rules a boundary to attach to. Namespaces alone are not isolation, so they must be combined with the steps below.
2. **Least-privilege Roles and a ServiceAccount per app.** Grant only the verbs and resources the app needs, and bind them at namespace level. Never give apps `cluster-admin`. If the app doesn't call the API, disable token auto-mount. A stolen identity is then worth almost nothing.
3. **Harden Pods with Pod Security Standards.** Run non-root, use a read-only root filesystem, drop Linux capabilities, and block privilege escalation. This limits what an attacker can do after getting in.
   ```yaml
   securityContext:
     runAsNonRoot: true
     readOnlyRootFilesystem: true
     allowPrivilegeEscalation: false
     capabilities: { drop: ["ALL"] }
   ```
   Note that the "restricted" profile enforces non-root, dropped capabilities and no escalation, but not the read-only filesystem. Enforce that with Kyverno or Gatekeeper.
4. **NetworkPolicies with default-deny.** Block all traffic first, then allow only the needed paths (for example, the API to its database). A compromised Pod then cannot roam.
5. **Image scanning and signing.** Scan in CI, sign what passes, and verify signatures at admission. This stops vulnerable or tampered images from running.
6. **Admission policies (Kyverno / OPA Gatekeeper).** Reject Pods that run as root, use `latest` tags or come from unknown registries. Rules are then enforced automatically, not by human memory.
7. **Secrets management.** Kubernetes Secrets are only base64-encoded, not encrypted. Enable encryption at rest, restrict who can read Secrets, and prefer an external manager (Vault, a cloud KMS or secrets manager) so rotation is possible.
8. **Audit logs.** Turn them on and ship them to a central place, so you can answer "who did this?" after an incident.

**Trade-offs and what can go wrong**
- Strict Pod rules break images that need root or write to their filesystem. Roll out in audit or warn mode first.
- Default-deny can silently break DNS, metrics scraping or ingress traffic. Add those allow rules explicitly.
- NetworkPolicies do nothing on a CNI that does not support them, which gives false confidence.
- Wildcard roles (`*` verbs or resources) and long-lived tokens quietly undo least privilege.
- Too many admission policies slow deploys and frustrate teams, so start with a few high-value rules.

**How I'd monitor it**
- Check permissions with `kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>`, and scan regularly for `cluster-admin` bindings.
- Search audit logs in Splunk for `forbidden` (403) responses, Secret reads by unusual identities, and `exec` into Pods.
- Alert on admission policy violations and failed signature checks.
- Run CIS benchmark scans (kube-bench) and image scans in CI and on a schedule.

**Follow-ups to expect**
- *Are Kubernetes Secrets secure by default?* -> No. They are base64-encoded and stored unencrypted in etcd unless encryption at rest is enabled. Combine encryption with tight RBAC or an external secrets manager.
- *Role vs ClusterRole?* -> A Role is namespaced. A ClusterRole is cluster-wide, but it can be bound inside one namespace with a RoleBinding to limit its reach.
- *PodSecurityPolicy vs Pod Security Standards?* -> PodSecurityPolicy was removed in 1.25. Pod Security Admission with the PSS profiles replaced it, and Kyverno or Gatekeeper cover custom rules.

**60-second answer**
I secure Kubernetes in layers. Each team and environment gets its own namespace, and every app gets its own ServiceAccount with a minimal Role, never `cluster-admin`, so a stolen identity can do very little. Pods follow the Pod Security Standards: non-root, dropped capabilities, no privilege escalation and a read-only filesystem. I add default-deny NetworkPolicies so a hacked Pod cannot reach others. Images are scanned and signed in CI, and admission policies in Kyverno or Gatekeeper reject anything that breaks the rules. Secrets are encrypted at rest or kept in an external manager, and audit logs go to Splunk so I can alert on suspicious API activity.

### Q33 [fresher] What is OpenShift and how does it differ from Kubernetes?
tags: openshift, kubernetes, red-hat, containers, routes, operators, security, basics

**Start here: the concepts**
- **Container**: an application packaged with everything it needs to run, isolated from other processes on the same machine.
- **Kubernetes**: open-source software that runs containers across many machines. It restarts failed ones, scales them and routes traffic to them. On its own it is only the core, and you choose and install the extras yourself.
- **Distribution**: Kubernetes plus a tested bundle of extra components, support and updates, like Linux and Ubuntu. OpenShift is Red Hat's enterprise Kubernetes distribution.
- **Namespace / Project**: a named partition of a cluster, so teams do not collide. An OpenShift *Project* is a namespace plus extra metadata and access settings.
- **Image registry**: a store for container images. OpenShift has one built in.
- **S2I (Source-to-Image) and BuildConfig**: S2I builds an image directly from your source code. A BuildConfig describes how OpenShift runs that build, so you do not write a Dockerfile.
- **Ingress vs Route**: both expose an app to outside traffic. A **Route** is OpenShift's own HAProxy-based mechanism, and it predates Kubernetes Ingress.
- **CI/CD**: automating build, test and deploy. **Tekton** (OpenShift Pipelines) runs pipelines as cluster objects. **Argo CD** (OpenShift GitOps) keeps the cluster matching what is in Git.
- **Operator / OperatorHub**: an operator is software that installs and manages another application (such as a database) on the cluster. OperatorHub is the catalogue of them.

**The live scenario**
A team with 20 microservices runs plain Kubernetes. Over a year they assemble an image registry, a build server, an ingress controller, a dashboard and a security policy tool. One engineer spends about 40% of their time keeping these compatible. A security audit then finds 6 services running as root. The company moves to OpenShift. Registry, builds, routes, console and operators now come supported in one product. Root containers are blocked by default, so the 6 services must be fixed before they run. The cost is licence fees and some friction, but the platform work shrinks.

**What the interviewer is really checking**
Whether you know OpenShift is Kubernetes plus extras, not a different thing, and whether you can name concrete differences instead of saying "it is more enterprise".

**How I answer it**
1. **Say it is Kubernetes underneath.** It uses the same core API, so Deployments, Services, Pods and `kubectl` knowledge transfer. The reason: you do not relearn the basics.
2. **Name what is built in.** This covers the image registry, S2I and BuildConfigs, the web console, Tekton pipelines, Argo CD GitOps and OperatorHub. With plain Kubernetes you install and maintain each of these yourself.
3. **Explain Routes.** A Route exposes a service through HAProxy and existed before Ingress. OpenShift still understands Ingress objects, so both work.
4. **Explain Projects.** A Project is a namespace with extra metadata and access controls, which suits multi-team clusters.
5. **Explain stricter security.** By default OpenShift runs containers as a random non-root user and restricts what they may do. The reason: a compromised container then has less power over the host. The usual symptom is an image that works on Kubernetes but fails on OpenShift because it assumes root.
6. **Mention the CLI.** `oc` is a superset of `kubectl`:
```
oc new-project shop      # kubectl create namespace shop
```

**Trade-offs and what can go wrong**
- Licence and subscription cost, and heavier resource needs than a minimal cluster.
- Lock-in risk: Routes, BuildConfigs and S2I are OpenShift-specific. Using plain Ingress and standard Deployments keeps manifests portable.
- Images built to run as root fail under the default security rules. Fix the image rather than loosening the policy.
- Saying "OpenShift replaces Kubernetes" is wrong. It is built on it.

**How I'd monitor it**
- The built-in console and its monitoring dashboards show pod health, CPU, memory and restarts.
- Check `oc get pods` and `oc describe pod` for security-related start failures.
- Watch pipeline run success and duration in OpenShift Pipelines.
- Check Argo CD for apps that are out of sync with Git.
- Search Splunk for container start errors such as permission denied.

**Follow-ups to expect**
- *Route or Ingress?* -> Route is OpenShift-native and HAProxy-based. Ingress is the Kubernetes standard and is more portable, and OpenShift supports both.
- *What is a Project?* -> A namespace plus extra metadata and access controls.
- *Why might my image fail on OpenShift but work on Kubernetes?* -> The default security rules run containers as a random non-root user, so an image that needs root will fail.

**60-second answer**
OpenShift is Red Hat's enterprise distribution of Kubernetes, so the core API is the same and Kubernetes skills transfer directly. The difference is what comes included. It has a built-in image registry, S2I and BuildConfigs for building from source, a web console, Tekton-based pipelines, Argo CD for GitOps and OperatorHub for installing operators. It uses Routes, an HAProxy-based way to expose apps that predates Ingress, and Projects, which are namespaces with extra metadata. It also has stricter default security, such as running containers as non-root. The trade-offs are cost and some OpenShift-specific features that reduce portability. In return, teams spend less time assembling and securing a platform themselves.

### Q34 [mid] OpenShift security difference to know: SCCs and non-root.
tags: openshift, scc, non-root, container-security, uid, kubernetes, basics

**Start here: the concepts**
- **Container user (UID):** Every process on Linux runs as a numeric user ID. UID 0 is root, the all-powerful user. A container's process is still a normal Linux process on the host, so running as root inside it is riskier than it looks.
- **Non-root:** Running the app as a normal, low-privilege user. If an attacker breaks out of the app, they have far less power on the node.
- **Security Context Constraints (SCC):** An OpenShift admission rule that decides what a pod may do: which UID it may use, whether it may be privileged, which Linux capabilities it may have, and so on. Every pod is checked against an SCC when it is created. Plain Kubernetes has a similar idea (Pod Security Admission), but it is looser by default.
- **`restricted` SCC:** The default for ordinary users. On OpenShift 4.10 and earlier it is called `restricted`. From 4.11 it is `restricted-v2`, which also drops all capabilities and requires a default seccomp profile.
- **Arbitrary UID:** OpenShift assigns each project (namespace) a UID range. Under `restricted`, it ignores the `USER` in your image and starts the container with a random UID from that range. Your image cannot know the UID in advance.
- **Group 0 (root group):** The random UID is always placed in GID 0. That group has no special power, but it lets you give the random user access to files by making them group-writable.

**The live scenario**
A team moves 12 Spring Boot services from plain Docker/Kubernetes to OpenShift. Eight start fine. Four go into `CrashLoopBackOff`. Two log `Permission denied` writing to `/app/logs`. One fails with `Permission denied` binding port 80. One uses an init script that runs `chown` and needs root. A developer proposes granting the `anyuid` SCC to everything. That would unblock the release, but it removes the protection for all 12 services. The platform team asks them to fix the images instead, which takes about two days.

**What the interviewer is really checking**
Whether you know OpenShift is secure by default and that you fix images to fit it, rather than loosening security. They also want to know whether you understand why the random UID breaks images.

**How I answer it**
1. **State the default.** OpenShift runs containers as a random non-root UID from the project's range under the `restricted` SCC (`restricted-v2` on 4.11+). Reason: if one container is compromised, the attacker is not root on the node.
2. **Explain why images fail.** Images that assume root, or a fixed UID such as a `USER` that owns files, break because the real UID differs. Root-only actions fail too, such as `chown`, `apt install` at startup, or writing to root-owned folders.
3. **Make writable folders group-0 writable.** The random UID belongs to group 0, so give group 0 the same rights as the owner:
   ```
   RUN chgrp -R 0 /app /tmp/work && chmod -R g=u /app /tmp/work
   USER 1001
   ```
4. **Avoid privileged ports.** Non-root processes cannot bind ports below 1024, so listen on 8080 and map it in the Service.
5. **Do the work at build time.** Install packages and set permissions in the Dockerfile, not at container startup.
6. **Test before release.** Run `oc get pod -o yaml` and check `openshift.io/scc`, or run locally with `docker run --user 123456:0`.
7. **Use an exception only when truly needed.** If a workload really needs more, create a dedicated ServiceAccount and grant a specific SCC to that account only, with approval. Do not grant `anyuid` or `privileged` broadly.

**Trade-offs and what can go wrong**
- Quick fixes such as `anyuid` weaken security cluster-wide and often get left in place.
- Mounted volumes may carry the wrong ownership, so a fix in the image alone does not always work.
- Third-party images from Docker Hub are often root-based. Prefer vendor images built for OpenShift or rebuild them.
- Failures can look like generic crashes, so people blame the app instead of the SCC.

**How I'd monitor it**
- `oc describe pod` and namespace events show messages like `unable to validate against any security context constraint`.
- Check the `openshift.io/scc` annotation on running pods.
- Search logs (for example in Splunk) for `Permission denied` and for CrashLoopBackOff restart counts.
- Alert on pods using `privileged` or `anyuid`, and audit who has been granted those SCCs.
- Add a CI step that runs the image with a random UID before deployment.

**Follow-ups to expect**
- *Why not just add `USER root`?* -> Under `restricted`, the platform overrides it or rejects the pod. Even where it worked, it would remove the main protection.
- *What if the app needs a specific UID?* -> Make the app UID-agnostic. If it is truly impossible, use a dedicated ServiceAccount with a narrowly scoped SCC, after review.
- *How does this differ from Kubernetes?* -> Plain Kubernetes lets a pod run as whatever the image says unless you add policies. OpenShift enforces non-root and a random UID by default.

**60-second answer**
OpenShift is secure by default. Through Security Context Constraints, the default `restricted` one (`restricted-v2` from 4.11), it runs my container as a random non-root UID from the project's range, ignoring the `USER` in the image. Images that expect root or a fixed UID then fail, for example when writing to a folder or binding port 80. I fix this in the image: run as non-root, listen on a port above 1024, and make writable folders owned by group 0 with `chmod g=u`, because the random user is always in group 0. I avoid granting `anyuid` broadly. If a workload truly needs more, I use a dedicated ServiceAccount with a narrow SCC. I check the `openshift.io/scc` annotation on running pods and watch for `Permission denied` in logs. This is one of the most common problems when moving from plain Docker or Kubernetes.

### Q35 [mid] Route vs Ingress; DeploymentConfig vs Deployment; `oc` basics?
tags: openshift, route, ingress, deployment, deploymentconfig, oc-cli, basics

**Start here: the concepts**
- **Container orchestrator (Kubernetes):** software that runs containers across many machines and restarts them when they fail. **OpenShift** is Red Hat's Kubernetes distribution with extra features and its own objects.
- **Service:** a stable internal address and load balancer in front of a changing set of pods. Pods get new IPs when they restart; the Service does not.
- **Ingress:** the standard Kubernetes object for letting outside HTTP/HTTPS traffic reach a Service, by host name and path. It does nothing alone. An **ingress controller** (a proxy such as NGINX) must read it and apply the rules.
- **Route:** OpenShift's own object for the same job. It is older than Ingress and is served by OpenShift's built-in router, which is HAProxy-based. It has features Ingress lacked, such as built-in TLS modes and traffic weights.
- **TLS termination:** where HTTPS is decrypted.
  - **Edge:** the router decrypts, then talks plain HTTP to the pod.
  - **Passthrough:** the router forwards the encrypted bytes untouched, and the pod decrypts.
  - **Re-encrypt:** the router decrypts, then opens a new TLS connection to the pod.
- **Deployment:** the standard Kubernetes object that keeps N copies of a pod running and does rolling updates. It uses ReplicaSets underneath.
- **DeploymentConfig (DC):** the older OpenShift-only equivalent. It uses ReplicationControllers, image-change triggers and lifecycle hooks.
- **`oc`:** the OpenShift command-line tool. It is a superset of `kubectl`, so the same verbs work, plus OpenShift extras.

**The live scenario**
A team runs 40 services on OpenShift, about 15 of them still on DeploymentConfigs from 2019. During a cluster upgrade review, the platform team notes that DC is deprecated (from OpenShift 4.14) and that the DC services cannot be moved to another Kubernetes platform, because DC is OpenShift-only. The team plans a migration to Deployments. For a new payments API they use a Route with re-encrypt TLS, because the security team requires encryption all the way to the pod. For the release they use a weighted Route sending 10% of the traffic to v2, and watch the error rate before going to 100%.

**What the interviewer is really checking**
Whether you know which objects are portable Kubernetes and which are OpenShift-specific, and whether you can use the CLI to inspect and debug a running app.

**How I answer it**
1. **Define Route vs Ingress.** Both expose a Service outside the cluster. Ingress is portable Kubernetes and needs a controller. Route is OpenShift-native and works out of the box through the router. OpenShift also turns an Ingress object into a Route automatically, so both work there.
2. **Pick the TLS mode by security need.** Edge is simplest, because the router holds the certificate. Re-encrypt keeps traffic encrypted inside the cluster. Passthrough is for cases where the pod must see the original TLS, such as client-certificate auth.
3. **Mention weighted routes for canary.** A Route can list alternate backends with weights, so 90/10 splits are possible without extra tooling.
   ```yaml
   spec: { to: {name: api-v1, weight: 90}, alternateBackends: [{name: api-v2, weight: 10}] }
   ```
4. **Say Deployment over DeploymentConfig.** A Deployment is standard, portable, and supported by the wider Kubernetes tooling. DC is deprecated: it still runs, but new work should not use it. DC had features like built-in triggers and hooks, so migration needs a check of what each DC relied on.
5. **Show `oc` basics.**
   - `oc login` authenticates.
   - `oc project` switches namespace.
   - `oc get pods` lists pods.
   - `oc logs <pod>` shows output.
   - `oc rsh <pod>` opens a shell inside a pod.
   - `oc new-app` creates an app from an image or source. Recent versions create a Deployment, older ones a DC.
   - `oc rollout status|undo|restart` manages rollouts. `kubectl` verbs mostly work the same.

**Trade-offs and what can go wrong**
- Routes lock you into OpenShift, while Ingress keeps you portable. Many teams pick Routes anyway for the simplicity.
- Edge TLS leaves the last hop unencrypted, which may fail a compliance audit.
- Migrating DC to Deployment can silently drop image-change triggers or hooks, so a new image no longer rolls out automatically.
- Weighted routes split by request, not by user, so one user may see both versions.
- Running `oc` against the wrong project is a common mistake. Check `oc project` before deleting anything.

**How I'd monitor it**
- Router metrics: HTTP 5xx rate and latency per route, compared between v1 and v2 during a canary.
- `oc get route` and `oc describe route` to confirm the host, TLS mode and weights.
- `oc rollout status deployment/<name>` in CI, so a pipeline fails if the rollout stalls.
- Alert on pods in CrashLoopBackOff or unready, and on certificate expiry dates.

**Follow-ups to expect**
- *Does Ingress work on OpenShift?* -> Yes. OpenShift creates a matching Route for it, but Route-only features such as weights need a Route.
- *Why was DeploymentConfig deprecated?* -> Deployments cover the same need with a standard API, so maintaining a second OpenShift-only controller was no longer worth it.
- *How do you roll back?* -> `oc rollout undo deployment/<name>` returns to the previous ReplicaSet. For a canary, set the weight back to 100/0.

**60-second answer**
Both Route and Ingress expose a Service to outside traffic. Ingress is standard Kubernetes and needs an ingress controller, while Route is OpenShift's own object served by its built-in router. A Route supports edge, passthrough and re-encrypt TLS, and weighted backends for canary releases. A Deployment is the standard way to run and update pods. DeploymentConfig is the older OpenShift-only version, deprecated since 4.14, so I use Deployments and migrate old DCs carefully, checking their triggers and hooks. For daily work, `oc` is `kubectl` plus extras: `oc login`, `oc project`, `oc get pods`, `oc logs`, `oc rsh`, `oc new-app` and `oc rollout`.

### Q36 [architect] Design the deployment of 10 Spring Boot services on Kubernetes/OpenShift.
tags: kubernetes, openshift, spring-boot, helm, hpa, gitops, canary, basics

**Start here: the concepts**
- **Container / Pod:** a container is an app packaged with its dependencies. A Pod is the smallest unit Kubernetes runs, usually one container.
- **Deployment:** declares "run N identical Pods of this image" and replaces them gradually (a rolling update) when the image changes.
- **Namespace:** a named partition of a cluster for names, quotas and access rules. Many teams add a separate cluster for production for stronger isolation.
- **Helm / Kustomize:** tools that template or overlay YAML so one service definition can be reused per environment with different values.
- **Probes:** health checks Kubernetes runs on a container. *Startup* waits for slow boots. *Readiness* decides whether the Pod receives traffic. *Liveness* decides whether to restart it.
- **Requests / limits:** a request is the CPU/memory reserved for scheduling. A limit is the ceiling. Exceeding the memory limit gets the container killed (OOMKilled). Exceeding the CPU limit gets it throttled.
- **HPA (Horizontal Pod Autoscaler):** adds or removes Pods based on a metric such as CPU.
- **PDB (PodDisruptionBudget):** a guarantee such as "at least 2 Pods stay up" during planned disruptions like node drains.
- **Ingress / Route:** the edge entry that routes outside HTTP(S) traffic to services and terminates TLS. Route is the OpenShift equivalent.
- **ConfigMap / Secret:** configuration and sensitive values injected into Pods.
- **NetworkPolicy:** a firewall rule saying which Pods may talk to which.
- **GitOps:** Git holds the desired state, and a controller (Argo CD, Flux) makes the cluster match it.
- **Canary:** send a small share of traffic to the new version first.

**The live scenario**
Ten Spring Boot services ran with 3 replicas each, 30 Pods in total. During a node upgrade, the scheduler had put all 3 `orders` Pods on two nodes in one zone. With no PDB, the drain removed them together, causing about 4 minutes of 503s at roughly 800 requests/s. Earlier, a liveness probe that checked the database restarted every Pod during a 20-second database blip, turning a small problem into an outage.

**What the interviewer is really checking**
Whether you can design for failure (node, zone, bad release, slow start, shutdown), not just list YAML objects, and whether you can explain what each setting prevents.

**How I answer it**
1. **Namespace per environment, with prod in its own cluster if possible.** Quotas and RBAC stop one team or environment starving or breaking another.
2. **One Helm chart or Kustomize base for all ten services, with per-service and per-environment values.** Ten hand-written copies drift apart.
3. **Deployment with 3 replicas, spread across zones.** Replicas alone don't guarantee separation, so I add topology spread constraints or anti-affinity. Otherwise one zone failure can take out every replica.
4. **PDB (e.g. minAvailable 2) plus HPA.** The PDB protects against drains. The HPA handles load, scaling on CPU measured against the *request*.
5. **Three probes.** Startup covers slow JVM boot. Readiness checks "can I serve now". Liveness checks only "is the process stuck" and never checks downstream dependencies, which prevents the restart storm above. Spring Boot (2.3+) exposes these with `management.endpoint.health.probes.enabled=true`.
6. **Requests and limits tuned from load tests.** Memory request equals memory limit, to avoid surprise kills. I am cautious with CPU limits, since throttling hurts JVM latency. The JVM must be container-aware (heap as a percentage of the limit).
7. **Graceful shutdown.** `server.shutdown=graceful` with `spring.lifecycle.timeout-per-shutdown-phase=30s`, and a short preStop sleep so the load balancer stops sending traffic before the app stops. This prevents errors on every rolling update.
8. **Ingress/Route with TLS at the edge.** One controlled front door.
9. **Config and secrets.** ConfigMaps for non-sensitive settings. Secrets come from a vault via External Secrets or the CSI driver, because plain Kubernetes Secrets are only base64-encoded.
10. **Observability.** Centralised logs (e.g. Splunk) and Prometheus metrics.
11. **GitOps pipeline with canary and automated rollback.** A plain Deployment does rolling updates only. Real canary needs Argo Rollouts, Flagger or OpenShift's equivalent, which promotes or rolls back on error rate and latency.
12. **Security.** Default-deny NetworkPolicies with explicit allows, and non-root minimal images.

**Trade-offs and what can go wrong**
- More replicas and zone spread cost more, and cross-zone traffic has its own cost.
- An aggressive HPA causes flapping, and a slow JVM start delays scale-up.
- Too-tight limits cause OOMKills, while too-loose requests waste nodes.
- A canary is only as good as its metrics. Database schema changes must be backward compatible so rollback works.
- A PDB that is too strict can block node upgrades.

**How I'd monitor it**
- Restarts and OOMKilled counts, and Pods not Ready.
- CPU throttling, JVM heap and GC.
- HPA current vs desired replicas.
- p95 latency and 5xx rate per version during canary, which also drive the auto-rollback.
- Splunk searches for shutdown errors during deploys, and alerts when available replicas drop below the PDB minimum.

**Follow-ups to expect**
- *Why not check the database in liveness?* -> A dependency outage would restart healthy Pods and worsen the incident. Put it in readiness only if the service truly cannot work without it.
- *Rolling update vs canary vs blue-green?* -> Rolling replaces gradually with no metric gate. Canary gates on live metrics. Blue-green runs two full stacks and switches instantly, at double the cost.
- *How do you stop one service starving others?* -> Resource requests, namespace quotas, and limit ranges.

**60-second answer**
I give each environment its own namespace, with prod ideally in a separate cluster, and package the ten services with one Helm or Kustomize base. Each service runs 3 replicas spread across zones, protected by a PDB and scaled by an HPA. I use startup, readiness and liveness probes, with liveness never checking dependencies, and I set memory requests equal to limits from load tests. I enable graceful shutdown so rolling updates drop no requests. Traffic enters through Ingress or Route with TLS, config comes from ConfigMaps, and secrets come from a vault. Releases go through a GitOps pipeline using canary tooling like Argo Rollouts, which rolls back automatically on error-rate or latency regressions. NetworkPolicies and non-root images secure it, and logs and Prometheus metrics prove it works.

### Q37 [mid] Honest answer on OpenShift.
tags: openshift, kubernetes, routes, security-context-constraints, operators, basics

**Start here: the concepts**
- **Kubernetes:** a system that runs containers across many machines. You declare what you want (3 copies of this app) and it keeps that true.
- **OpenShift:** Red Hat's distribution of Kubernetes. It is Kubernetes plus extra features and stricter defaults, aimed at enterprises. Your Deployments, Services, probes and ConfigMaps work the same way.
- **`oc`:** OpenShift's command-line tool. It accepts the usual `kubectl` commands and adds extras such as `oc login` and `oc new-app`. A *project* is OpenShift's name for a namespace, with some extra metadata.
- **Route:** OpenShift's way to expose a service to the outside world with a hostname and optional TLS. It is similar to Kubernetes Ingress, and OpenShift also accepts Ingress objects and turns them into Routes.
- **SCC (Security Context Constraints):** rules that say what a pod may do, such as run as root, use host networking or mount host paths. Kubernetes has a similar feature, Pod Security admission, but OpenShift's default SCC is stricter. By default it runs your container as a random, non-root user ID, not the one in your Dockerfile. It exists so one compromised container cannot take over the node.
- **Operator:** a program running inside the cluster that installs and manages a complex application (a database or Kafka, for example), and handles upgrades and backups. Operators are a Kubernetes idea, but OpenShift uses them heavily, including to manage itself.
- **Integrated CI/CD:** built-in build and deploy tooling, such as OpenShift Pipelines (Tekton), OpenShift GitOps (Argo CD) and Source-to-Image builds.

**The live scenario**
A team moved a Spring Boot service from a plain Kubernetes cluster to OpenShift. The image ran fine before, but on OpenShift the pod went into CrashLoopBackOff within seconds. The log said "Permission denied" writing to `/app/logs`. The Dockerfile ran as root and the directory was owned by root, but OpenShift started the container as a random non-root user. After the team fixed directory permissions, the service worked. Nothing in the Java code changed. A candidate who had never seen this would lose half a day, and one who knows it fixes it in minutes.

**What the interviewer is really checking**
Whether you are honest about your experience, and whether you can map what you know onto what you don't. They want to see that you understand how OpenShift differs from Kubernetes and that you can learn it fast.

**How I answer it**
1. **Say plainly what I have done:** deployments, services, probes, config and troubleshooting on Kubernetes. Reason: honesty builds trust, and a bluff is exposed by the first follow-up question.
2. **Say I haven't operated OpenShift directly.** Reason: it is better to say this myself than to be caught out.
3. **Show I know what it is:** Kubernetes plus Routes, SCC-based security, Operators and integrated CI/CD. Reason: this proves I have studied it, not just heard the name.
4. **Name the real adjustments.** First, images must run as a non-root, arbitrary user ID, so I make directories group-writable:
   ```
   RUN chgrp -R 0 /app && chmod -R g=u /app
   USER 1001
   ```
   Reason: OpenShift picks the user ID but always puts it in group 0. Second, I use `oc` and Routes in place of what I would do with `kubectl` and Ingress.
5. **Close with a learning plan:** I would learn it hands-on, for example on a local OpenShift sandbox. Reason: the core skills carry over, so ramp-up is mostly the security model and tooling.

**Trade-offs and what can go wrong**
- Don't claim "I'd be productive quickly" without backing it up. Back it up with the specific adjustments above.
- Don't "fix" SCC errors by granting the `anyuid` or `privileged` SCC. That removes the safety OpenShift gives you.
- Old tutorials mention DeploymentConfig, which is deprecated. Use the standard Deployment.
- Operators and OpenShift pipelines add convenience but also lock-in to Red Hat tooling.

**How I'd monitor it**
- `oc get pods` and `oc describe pod` show CrashLoopBackOff and the events behind it.
- `oc logs` shows the "Permission denied" error.
- `oc get events` shows admission errors such as "unable to validate against any security context constraint".
- Splunk: search container logs for `"Permission denied"` or `"CrashLoopBackOff"` by namespace. Alert when the restart count rises.

**Follow-ups to expect**
- *Why does my image fail on OpenShift but work on Docker?* -> OpenShift runs it as a random non-root user, so files and directories must be group-0 writable and the app must not bind ports below 1024.
- *Route vs Ingress?* -> A Route is OpenShift's native object for exposing services, handled by its built-in router. Ingress is the Kubernetes standard, and OpenShift converts it to Routes.
- *What is an Operator?* -> A controller that automates installing and operating a complex app, such as upgrades and backups.

**60-second answer**
"I've worked with Kubernetes: deployments, services, probes, config and troubleshooting. I haven't operated OpenShift directly, and I'd rather say that up front. I understand it as Kubernetes plus extras: Routes to expose services, SCC security rules, Operators to manage complex apps, and built-in CI/CD. The biggest practical change is security. OpenShift runs containers as a random non-root user, so I'd build images with group-writable directories and avoid privileged settings. I'd also use `oc` and Routes instead of `kubectl` and Ingress. Because the core concepts are the same, I'd be productive quickly and would learn the rest hands-on."
