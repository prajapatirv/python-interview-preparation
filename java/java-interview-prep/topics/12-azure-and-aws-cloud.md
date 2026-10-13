---
id: 12-cloud-azure-aws
title: Cloud - Azure (weak area) mapped to AWS (your strength)
focus: Translate your AWS experience (S3, Lambda, SES, MWAA, CloudWatch, IAM, ECS) into Azure terms
---
Your strength is AWS (S3, EC2, Lambda, SES, MWAA, CloudWatch, IAM, Bedrock, ECS Fargate/RDS from the hackathon). Use the mapping table to answer Azure questions honestly: "I've worked on AWS; the Azure equivalent is X, and here's how it differs."

### Q1 [basic] Map the common AWS services to Azure.
| Need | AWS | Azure |
|---|---|---|
| VMs | EC2 | Virtual Machines |
| Object storage | S3 | Blob Storage |
| Serverless functions | Lambda | Azure Functions |
| Containers (managed) | ECS/Fargate | Container Apps / ACI |
| Kubernetes | EKS | AKS |
| Relational DB | RDS/Aurora | Azure SQL / Azure Database for PostgreSQL |
| NoSQL | DynamoDB | Cosmos DB |
| Queue / pub-sub | SQS/SNS | Service Bus / Event Grid |
| Streaming | MSK/Kinesis | Event Hubs (Kafka-compatible) |
| Identity | IAM | Entra ID (Azure AD) + RBAC |
| Secrets/keys | Secrets Manager/KMS | Key Vault |
| Monitoring | CloudWatch | Azure Monitor / Application Insights / Log Analytics |
| Workflow | MWAA/Step Functions | Data Factory / Logic Apps / Durable Functions |
| Email | SES | Azure Communication Services |
| IaC | CloudFormation/Terraform | ARM/Bicep/Terraform |

### Q2 [basic] What are regions, availability zones and resource groups in Azure?
Region = geographic area; Availability Zones = separate datacentres inside a region (deploy across zones for HA). **Resource group** = logical container for resources that share a lifecycle (delete the group to delete everything); a subscription holds many groups; tags and policies apply on top.

### Q3 [intermediate] How does Azure identity and access (RBAC) work?
Users/apps are identities in **Microsoft Entra ID**; permissions are **role assignments** (role + identity + scope: management group/subscription/resource group/resource). Apps use a **managed identity** (system- or user-assigned) instead of secrets - similar to an IAM role attached to EC2/Lambda. Secrets go into **Key Vault**.

### Q4 [intermediate] Which Azure services would host a Spring Boot microservice?
Azure App Service (simplest PaaS), **Azure Container Apps** (serverless containers with KEDA scaling, Dapr optional), **AKS** (full Kubernetes control), Azure Spring Apps (managed Spring; note its retirement path - verify the current status before recommending it). Choose Container Apps for most teams, AKS when you need Kubernetes features/mesh/custom operators.

### Q5 [intermediate] Azure messaging: Service Bus vs Event Hubs vs Event Grid?
Service Bus: enterprise queues/topics with sessions, dead-lettering, transactions, scheduled delivery (like RabbitMQ/SQS+SNS). Event Hubs: high-throughput event streaming with partitions and consumer groups, **Kafka protocol compatible** (like Kafka/Kinesis). Event Grid: reactive events/routing from Azure resources (like EventBridge).

### Q6 [intermediate] Azure data services for a Java app?
Azure SQL / PostgreSQL Flexible Server (managed relational, zone-redundant HA, read replicas), **Cosmos DB** (multi-model, global distribution, tunable consistency levels: strong, bounded staleness, session, consistent prefix, eventual; throughput in RUs), Blob Storage, Redis Cache. Cosmos DB's partition key choice is the key design decision.

### Q7 [intermediate] How would you monitor a Java app on Azure?
Application Insights (Java agent: auto-instrumentation, traces, dependencies, exceptions), Azure Monitor metrics/alerts, Log Analytics with KQL queries, dashboards/Workbooks, and OpenTelemetry export if you want vendor neutrality. Equivalent to CloudWatch + X-Ray or Datadog, which you've used.

### Q8 [intermediate] Azure Functions vs AWS Lambda - differences that matter?
Same idea (triggers: HTTP, queue, timer, Blob, Event Hub). Hosting plans: Consumption (scale to zero, cold starts), Premium (pre-warmed instances), Dedicated. **Durable Functions** give stateful orchestration (like Step Functions). Java supported; mind cold starts and connection reuse across invocations.

### Q9 [intermediate] How do you secure an application in the cloud (any provider)?
Least-privilege identities (no long-lived keys), private networking (VNet/VPC, private endpoints), secrets in a vault with rotation, encryption in transit and at rest with managed keys, WAF/gateway at the edge, policy-as-code (Azure Policy/SCP), audit logs, vulnerability scanning of images and dependencies, and separate subscriptions/accounts per environment.

### Q10 [intermediate] How would you build a CI/CD pipeline for Azure?
Azure DevOps Pipelines or GitHub Actions (you've used GitHub Actions/Jenkins): build + test + scan -> push image to Azure Container Registry -> deploy via Helm/Kustomize or Bicep/Terraform to staging -> approval gate -> production with canary/blue-green. Use OIDC federation instead of storing cloud secrets in the pipeline.

### Q11 [intermediate] Explain Infrastructure as Code and why.
Describe infra in version-controlled files (Terraform, Bicep, CloudFormation) so environments are reproducible, reviewable and auditable; plan -> review -> apply; remote state with locking; modules for reuse; drift detection. Your hackathon agent generated Terraform for ECS Fargate + RDS + ALB - a good concrete example.

### Q12 [advanced] Cloud cost optimisation (FinOps) - what do you do?
Right-size instances/pods, autoscale, use spot/low-priority for stateless/batch, reserved/savings plans for steady load, lifecycle rules (S3/Blob tiers), delete idle resources, tag everything for cost allocation, set budgets/alerts, watch egress and log-ingestion costs, and make cost a design review item.

### Q13 [advanced] Multi-region and disaster recovery strategies?
Backup & restore (cheapest, slow RTO) -> pilot light -> warm standby -> active-active (fastest, most complex, needs conflict handling). Choose by RTO/RPO and cost. Components: global traffic routing (Traffic Manager/Front Door, Route 53), replicated data, IaC to rebuild, regular failover drills.

### Q14 [intermediate] Serverless vs containers vs VMs - how do you choose?
Serverless: event-driven, spiky, low ops, watch cold starts/time limits/vendor lock-in. Containers: portable, steady services, more control. VMs: legacy/special OS needs. For a Java service with steady traffic, containers; for glue/ETL triggers, functions.

### Q15 [advanced] How do you connect on-prem/legacy systems securely to the cloud?
Site-to-site VPN or dedicated links (ExpressRoute / Direct Connect), private DNS, private endpoints, IP allow-lists, mTLS, and a message broker or API gateway as the integration boundary. Plan for latency and failure of the link.

### Q16 [design] Design a file-ingestion workflow on Azure equivalent to your S3/MWAA/Lambda solution.
Files arrive in Blob Storage (SFTP support or upload via pre-signed SAS URL) -> Event Grid triggers an Azure Function or a Container Apps job -> parsers convert to normalised JSON -> publish to Event Hubs/Service Bus -> consumers write to Azure SQL/Cosmos with idempotent upserts -> Data Factory or Durable Functions orchestrate multi-step workflows -> alerts via Azure Monitor/Communication Services -> dead-letter and replay. Same architecture, different names.

### Q17 [intermediate] Honest answer: "Have you worked on Azure?"
"My hands-on cloud experience is AWS - S3, Lambda, MWAA, SES, CloudWatch, IAM and ECS in production. On Azure I've had only basic exposure. The concepts transfer directly - identity, networking, managed services, IaC, observability - and I can map each service I've used to its Azure equivalent. I'd be productive in a few weeks and would start with Microsoft Learn's AZ-204 path."

### Q18 [intermediate] What is Azure Key Vault and managed identity in a Spring app?
Store secrets/keys/certs in Key Vault; the app authenticates with its **managed identity** (no credentials in config), and Spring Cloud Azure can load secrets as properties. Same pattern as reading Secrets Manager via an IAM role.

### Q19 [advanced] Explain private networking: VNet, subnets, NSG, private endpoint.
VNet = isolated network; subnets segment it; NSGs are allow/deny rules per subnet/NIC; **private endpoints** give a PaaS service (SQL, Storage) a private IP in your VNet so traffic never crosses the public internet. AWS equivalents: VPC, subnets, security groups/NACLs, VPC endpoints/PrivateLink.

### Q20 [design] Design a landing zone / environment strategy for a team.
Separate subscriptions (or AWS accounts) for dev/test/prod, a shared network hub, central logging, policies (allowed regions, required tags, no public storage), RBAC groups (not individual users), budgets, IaC for everything, and a pipeline that is the only way to change production.

### Q21 [design] Design a cost-governance approach for a team that suddenly doubled its cloud bill.
Make cost visible first: mandatory tags/labels, budgets and alerts per subscription/account, and a weekly cost report by service. Then act: right-size and schedule non-prod shutdown, move steady load to reservations/savings plans and bursty to spot, set storage lifecycle rules, cap log retention and data-egress paths. Add cost as a metric in design reviews. Trade-off: aggressive savings can reduce resilience - never remove redundancy on tier-1 paths without sign-off.
