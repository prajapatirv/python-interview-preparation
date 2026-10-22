---
id: profile-java-genai-cloud-microservices
title: Java + GenAI profile (4/9): Cloud microservice architecture, 15 functional-requirement questions
stack: java
skill: microservices
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).
Cloud-neutral: each answer names the AWS and Azure equivalents where it matters.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [architect] How do you break a monolith into microservices without a big-bang rewrite?
tags: monolith, strangler-fig, bounded-context, ddd, decomposition, migration, profile-java-genai

**Start here: the concepts**
- **Bounded context (DDD):** a part of the domain with its own model and language (Booking, Payment, Loyalty).
- **Strangler fig pattern:** put a facade/gateway in front, move one capability at a time to a new service, route its traffic there, retire the old code.
- **Anti-corruption layer:** a translation layer so the new model isn't polluted by the legacy one.

**The live scenario (functional requirement)**
*FR: "Our 12-year-old J2EE travel monolith must support a new mobile app and an AI trip-planner; releases take 6 weeks and one bad module takes the whole site down."*

**What the interviewer is really checking**
Incremental migration, choosing seams by domain and pain, and handling data.

**How I answer it**
1. **Why first:** independent deploys, isolate failures, scale hot parts. If none of those hurt, a modular monolith may be enough.
2. **Map bounded contexts** with domain experts (event storming): search, booking, payment, loyalty points, notifications, customer profile.
3. **Pick the first slice** by value and low coupling: e.g. notifications or search (read-heavy, independent), not payment.
4. **Strangler facade:** an API gateway routes `/search/**` to the new service, the rest to the monolith.
5. **Data:** the new service gets its own database; sync from the monolith via CDC (Debezium) or events during transition; one writer per data item at any time.
6. **Anti-corruption layer** translating legacy codes and shapes.
7. Repeat; each step is reversible by switching the route back. Retire monolith code as you go.

**Trade-offs and what can go wrong**
- Splitting by technical layer (a "DAO service") creates chatty, coupled services: a distributed monolith.
- Shared database between old and new means hidden coupling.
- Microservices add network failures, observability and ops cost; the platform (CI/CD, k8s, tracing) must exist first.

**How I'd monitor it**
Traffic share per route (monolith vs new), error rate and latency comparison, number of cross-service calls per user request.

**Follow-ups to expect**
- *How big should a service be?* -> Owned by one team, deployable alone, aligned to one bounded context.
- *Branch by abstraction?* -> Inside the code base, put an interface over the old implementation, build the new one behind it, switch by flag.
- *How do you validate the new service?* -> Shadow traffic or parallel run, comparing outputs before switching.

**60-second answer**
"I don't rewrite; I strangle. First map bounded contexts with the business, then put a gateway in front and move one low-coupling, high-value capability, like search, into its own service with its own database, synced by CDC during the transition. The gateway routes that path to the new service, so it's reversible. An anti-corruption layer keeps legacy concepts out of the new model. I repeat slice by slice, validating with shadow traffic, and avoid splitting by technical layer, which just builds a distributed monolith."

### Q2 [senior] Each service owns its database. How do you keep data consistent across services?
tags: database-per-service, saga, eventual-consistency, orchestration, choreography, distributed-transaction, profile-java-genai

**Start here: the concepts**
- **Database per service:** only the owner reads and writes its tables; others use its API or events.
- **No distributed ACID:** 2PC/XA is slow and fragile across services and brokers.
- **Saga:** a sequence of local transactions; each failure triggers **compensating** actions. **Orchestration** (a coordinator) or **choreography** (services react to events).

**The live scenario (functional requirement)**
*FR: "Booking a trip must reserve a flight, reserve a hotel, debit loyalty points and charge the card; if any step fails, everything already done is undone and the user is told clearly."*

**What the interviewer is really checking**
That you know sagas, compensations, idempotency and the user-facing status model.

**How I answer it**
1. **Orchestrated saga** for this flow (4+ steps, clear business process): a `TripBookingOrchestrator` holds the state machine: PENDING -> FLIGHT_HELD -> HOTEL_HELD -> POINTS_DEBITED -> PAID -> CONFIRMED.
2. Each step is a command (via Kafka or REST) to the owning service; each has a **compensation**: release flight, cancel hotel, refund points, refund payment.
3. Order steps so the hardest-to-undo happens **last** (charge the card last; hold seats first).
4. **Idempotent steps and compensations**: commands carry a saga id; retries don't double-debit.
5. State persisted (DB table) so a crash resumes; outbox pattern to publish commands reliably.
6. The API returns **202** with a booking id in PENDING; the UI polls or gets a push when CONFIRMED or FAILED.
7. Tools: hand-rolled state machine, or a workflow engine (Temporal, Camunda) when flows are long-running and many.

**Trade-offs and what can go wrong**
- Choreography is simple for 2–3 steps, but the overall flow becomes invisible as it grows.
- Compensations aren't always perfect (a non-refundable fare); the business must define them.
- Intermediate states are visible (isolation is lost); use semantic locks such as "HELD" statuses.

**How I'd monitor it**
Sagas by state, stuck sagas older than N minutes (alert), compensation counts, end-to-end booking time.

**Follow-ups to expect**
- *Why not 2PC?* -> Blocking coordinator, poor availability, not supported by most brokers and NoSQL stores.
- *What if the compensation fails?* -> Retry with backoff; after N attempts park it for manual handling with an alert.
- *Choreography example?* -> OrderPlaced -> inventory reserves -> StockReserved -> payment charges.

**60-second answer**
"Across services I use a saga, not a distributed transaction. For trip booking I'd orchestrate it: a state machine holds flight, hotel, points and payment, each a local transaction with a compensation like release seat or refund points. The hardest-to-undo step, charging the card, goes last. Every step is idempotent with the saga id, state is persisted and commands go out via the outbox. The API returns 202 PENDING and the user is notified on confirm or failure, and I alert on stuck sagas."

### Q3 [senior] API gateway, service discovery and load balancing: what do you use on Kubernetes?
tags: api-gateway, service-discovery, spring-cloud-gateway, kubernetes-service, ingress, load-balancing, profile-java-genai

**Start here: the concepts**
- **API gateway:** single entry for clients: routing, auth, rate limiting, TLS, request shaping.
- **Service discovery:** how service A finds instances of B. Eureka (client-side) or **Kubernetes Services + DNS** (platform-side).
- **Ingress / Gateway API:** Kubernetes objects for external HTTP routing.

**The live scenario (functional requirement)**
*FR: "Expose booking, search and AI-assistant APIs to web, mobile and partners with one domain, per-partner rate limits and OAuth; internal services call each other by name."*

**What the interviewer is really checking**
That you avoid redundant layers and put each concern in the right place.

**How I answer it**
1. **Discovery:** on Kubernetes, use **Services** (`http://booking-service`) and cluster DNS. Eureka is redundant there; I'd keep it only for VM-based estates.
2. **Load balancing:** kube-proxy spreads connections across pods; for HTTP/2/gRPC long-lived connections, a mesh or client-side balancing distributes requests better.
3. **Edge:** a cloud load balancer -> **API gateway** (Spring Cloud Gateway, Kong, or managed: AWS API Gateway, Azure API Management) for auth (JWT validation), per-partner rate limits, routing, header normalisation.
4. Optionally **BFFs** per channel behind the gateway, shaping responses for mobile vs web.
5. **AI-assistant route:** long timeouts and streaming (SSE) enabled; token-based quotas in an AI gateway layer.

**Trade-offs and what can go wrong**
- The gateway must stay thin; business logic there becomes a new monolith.
- Single point of failure: run it with multiple replicas across zones.
- Double auth/rate-limit logic in gateway and services drifts; decide which layer owns what.

**How I'd monitor it**
Per-route and per-partner request rates, 429s, p99 at the gateway vs service (to locate latency), upstream errors.

**Follow-ups to expect**
- *Spring Cloud Gateway: MVC or reactive?* -> Both flavours exist now (Gateway Server WebFlux and Server Web MVC).
- *What does a service mesh add?* -> mTLS, retries, traffic splitting and telemetry without code changes.
- *Ingress vs Gateway API?* -> Gateway API is the newer, more expressive standard.

**60-second answer**
"On Kubernetes I don't run Eureka: Services and DNS are the discovery, and kube-proxy or a mesh balances. At the edge, a cloud load balancer feeds an API gateway, Spring Cloud Gateway or a managed one like API Management, which does JWT validation, per-partner rate limits and routing, and BFFs shape responses per channel. The AI route gets long timeouts and streaming. The gateway stays thin, with no business logic, and runs multi-zone."

### Q4 [senior] Synchronous REST, gRPC or asynchronous messaging between services: how do you choose?
tags: inter-service-communication, rest, grpc, messaging, kafka, coupling, profile-java-genai

**Start here: the concepts**
- **Sync (REST/gRPC):** the caller waits; simple; temporal coupling (both must be up).
- **Async (Kafka, RabbitMQ, SQS):** fire an event or command; decoupled in time; eventual consistency.
- **gRPC:** HTTP/2 + Protobuf, strongly typed contracts, efficient, streaming; less friendly to browsers.

**The live scenario (functional requirement)**
*FR: "On booking confirmation: show the confirmation immediately, send email/SMS, award loyalty points, update the analytics warehouse, and refresh the AI assistant's knowledge of the customer's trips."*

**What the interviewer is really checking**
That you choose per interaction, based on whether the caller needs the answer now.

**How I answer it**
1. **Rule:** if the user's response depends on the result now -> sync. If it's a side effect -> async event.
2. Booking service confirms in its own DB and returns -> publishes `BookingConfirmed` (outbox -> Kafka).
3. Notification, loyalty, analytics and the assistant's indexer **subscribe**; each can be slow or down without affecting booking.
4. **Sync** where needed: price check before booking (REST with timeout + breaker), or high-throughput internal calls with strict contracts (gRPC, e.g. a pricing engine called 50× per search).
5. Avoid long synchronous chains (A -> B -> C -> D); availability multiplies down (0.99⁴ ≈ 0.96).

**Trade-offs and what can go wrong**
- Async means eventual consistency: points may appear seconds later; set UI expectations.
- Debugging async flows needs trace context in message headers.
- gRPC needs HTTP/2-aware load balancing and Protobuf schema management.

**How I'd monitor it**
Sync: latency and error rate per dependency. Async: consumer lag per subscriber, DLQ counts, end-to-end event age.

**Follow-ups to expect**
- *Request-reply over Kafka?* -> Possible (`ReplyingKafkaTemplate`), but if you need the reply now, REST is usually simpler.
- *Commands vs events?* -> Command = "do this" to one owner; event = "this happened" to anyone.
- *How do you version event schemas?* -> Schema registry with backward-compatible evolution.

**60-second answer**
"I decide per interaction: if the user's response needs the answer now, it's synchronous, REST or gRPC for high-volume typed internal calls, always with timeouts and breakers. Everything else is an event. Booking confirms locally, returns, and publishes BookingConfirmed through the outbox; notifications, loyalty, analytics and the AI indexer react independently, so none of them can slow or break the booking. I avoid long sync chains, because availability multiplies down the chain."

### Q5 [senior] Which resilience patterns do you apply to every remote call, and in what order?
tags: resilience, timeout, retry, circuit-breaker, bulkhead, fallback, profile-java-genai

**Start here: the concepts**
- **Timeout:** never wait forever. **Retry:** transient errors, with backoff + jitter. **Circuit breaker:** stop calling a failing dependency. **Bulkhead:** isolate resources per dependency. **Rate limiter:** cap your call rate. **Fallback:** a degraded answer.

**The live scenario (functional requirement)**
*FR: "Hotel search aggregates 6 supplier APIs; one supplier being slow must not slow the whole search beyond 2 s or take the service down."*

**What the interviewer is really checking**
Layering the patterns correctly and tying them to a latency budget.

**How I answer it**
1. **Budget:** 2 s total -> each supplier gets 1.5 s; calls run in parallel.
2. **Timeout** per supplier on the HTTP client (connect 300 ms, read 1.2 s).
3. **Bulkhead** per supplier (separate pool or semaphore of e.g. 50), so a slow supplier can't consume all threads.
4. **Circuit breaker** per supplier: open at 50% failures/slow calls over 20 calls; while open, skip that supplier instantly.
5. **Retry** only for idempotent searches, at most 1, with jitter, and only if the budget allows.
6. **Fallback:** return results from the other 5 suppliers plus a "some results unavailable" flag, or cached availability.
7. Resilience4j decoration order (outer to inner): Retry -> CircuitBreaker -> RateLimiter -> TimeLimiter -> Bulkhead -> call.

**Trade-offs and what can go wrong**
- Retries at multiple layers multiply load during outages.
- Thresholds tuned on guesses either trip constantly or never; base them on real latency distributions.
- Fallbacks can hide real outages; count and alert on them.

**How I'd monitor it**
Per supplier: latency percentiles, error rate, breaker state, bulkhead rejections; search completeness percentage.

**Follow-ups to expect**
- *Where do you configure these?* -> Resilience4j properties per instance, or a service mesh for timeouts/retries.
- *Hedged requests?* -> Send a second request after p95 latency to another replica; cuts tail latency for idempotent reads.
- *Retry after 429?* -> Honour Retry-After; it's a rate limit, not a failure.

**60-second answer**
"I start from the latency budget: 2 seconds for search, so each supplier gets 1.5 in parallel. Every call has a client timeout, a per-supplier bulkhead so one slow supplier can't eat all threads, and a circuit breaker that skips a failing supplier instantly. I retry at most once, only idempotent calls, with jitter and only inside the budget. The fallback returns the other suppliers' results with a partial flag. And I watch breaker state and search completeness per supplier."

### Q6 [mid] How do you manage configuration and secrets for 30 microservices in the cloud?
tags: configuration, secrets-management, configmap, vault, aws-secrets-manager, azure-key-vault, profile-java-genai

**Start here: the concepts**
- **Config vs secrets:** endpoints and flags vs passwords, keys and certificates.
- **Options:** Kubernetes ConfigMaps/Secrets, Spring Cloud Config Server, HashiCorp Vault, AWS Secrets Manager/Parameter Store, Azure Key Vault/App Configuration.
- **Workload identity:** pods get cloud permissions without static keys (IRSA / EKS Pod Identity on AWS, Workload Identity on Azure/GCP).

**The live scenario (functional requirement)**
*FR: "30 services across 3 environments use DB passwords, Kafka credentials and LLM API keys; auditors require rotation every 90 days and no secret in git or images."*

**What the interviewer is really checking**
A secure, automated setup with least privilege and rotation.

**How I answer it**
1. **Non-secret config** in git (Helm values/Kustomize overlays) -> ConfigMaps, applied by GitOps (Argo CD). Versioned and reviewed.
2. **Secrets** in a vault (AWS Secrets Manager / Azure Key Vault / HashiCorp Vault), synced to Kubernetes by the **External Secrets Operator** or mounted with the Secrets Store CSI driver.
3. **No static cloud keys:** workload identity lets each pod's service account access only its own secrets.
4. **Dynamic DB credentials** with Vault where possible: short-lived, per pod.
5. **Rotation:** the vault rotates; the app re-reads mounted files or restarts in a rolling fashion; clients accept two valid keys during rotation.
6. Spring reads them via `spring.config.import` (configtree, Vault, AWS/Azure integrations).

**Trade-offs and what can go wrong**
- Kubernetes Secrets are only base64 by default; enable etcd encryption and restrict RBAC.
- Env-var secrets show up in process listings and crash reports; prefer mounted files.
- A central Config Server is another critical dependency; cache config locally.

**How I'd monitor it**
Secret age vs policy, failed secret fetches, access audit logs from the vault.

**Follow-ups to expect**
- *Feature flags?* -> A flag service (Unleash, LaunchDarkly, AWS AppConfig) rather than config redeploys.
- *How do you detect leaked secrets?* -> Secret scanning in CI and repo hosting (gitleaks, GitHub secret scanning).
- *Config Server still useful?* -> For non-Kubernetes estates or when you need refresh across many apps.

**60-second answer**
"Non-secret config lives in git as Helm or Kustomize values, applied by GitOps. Secrets live in a vault, AWS Secrets Manager, Azure Key Vault or HashiCorp Vault, and the External Secrets Operator syncs them into Kubernetes, mounted as files. Pods use workload identity, so there are no static cloud keys, and each service reads only its own secrets. The vault rotates on schedule, apps pick up new values with a refresh or rolling restart, and we scan repos for leaks."

### Q7 [senior] Make a request across 8 services debuggable: tracing, logs and metrics.
tags: observability, distributed-tracing, opentelemetry, correlation-id, red-metrics, slo, profile-java-genai

**Start here: the concepts**
- **Three pillars:** metrics (aggregates), logs (events), traces (one request's path as spans).
- **OpenTelemetry:** standard SDKs + OTLP protocol + a collector; vendor-neutral backends (Jaeger, Tempo, Grafana, Splunk, Datadog, Azure Monitor, X-Ray).
- **W3C trace context:** `traceparent` header propagated across HTTP and message headers.

**The live scenario (functional requirement)**
*FR: "When a customer says 'my booking took 30 seconds and failed', support must find that exact request and the failing service within 5 minutes."*

**What the interviewer is really checking**
End-to-end correlation, including async hops, and SLO-based alerting.

**How I answer it**
1. **Instrument** every service with OpenTelemetry (Spring Boot starter or the Java agent): HTTP server/client, JDBC, Kafka producer/consumer are auto-instrumented.
2. **Propagate** context through Kafka headers too, so the trace continues across async hops.
3. **Logs** in JSON with `traceId`/`spanId`; ship to the log platform. The booking id is attached as a span attribute and log field, so support searches by booking id -> trace.
4. **Metrics:** RED per service (rate, errors, duration) + business metrics (bookings confirmed/failed).
5. **Sampling:** keep 100% of errors and slow traces via tail sampling in the collector; a few percent of the rest.
6. **SLOs** per user journey (booking success 99.5%, p95 < 3 s), alerting on burn rate.

**Trade-offs and what can go wrong**
- Missing propagation at one hop (a thread pool, a custom client) breaks the trace.
- High-cardinality labels in metrics (booking id) explode costs; put those in traces/logs.
- Logging full payloads leaks PII; mask.

**How I'd monitor it**
Trace completeness (spans with missing parents), collector drop rate, alert noise vs incidents.

**Follow-ups to expect**
- *Agent or SDK?* -> Agent: zero code, broad coverage; SDK/starter: more control, native-image friendly.
- *What is exemplars?* -> Links from a metric data point to a sample trace.
- *Logs vs events?* -> Structured events with consistent fields make logs queryable.

**60-second answer**
"Every service is instrumented with OpenTelemetry, so HTTP, JDBC and Kafka spans are automatic, and trace context rides in Kafka headers too, keeping async hops in the same trace. Logs are JSON with trace ids, and the booking id is a span attribute, so support goes from booking id to the full trace in seconds and sees which service failed. RED and business metrics drive dashboards, the collector keeps all error and slow traces, and alerts fire on SLO burn rate."

### Q8 [senior] Secure service-to-service communication in a zero-trust cloud setup.
tags: zero-trust, mtls, service-mesh, oauth2, client-credentials, jwt-propagation, profile-java-genai

**Start here: the concepts**
- **Zero trust:** being inside the network grants nothing; every call is authenticated and authorised.
- **mTLS:** both sides present certificates; proves workload identity and encrypts traffic. A **service mesh** (Istio, Linkerd) automates it.
- **OAuth2 client credentials:** a service gets its own token from the identity provider. **Token exchange** (RFC 8693) passes user context downstream safely.

**The live scenario (functional requirement)**
*FR: "The AI assistant service can read a customer's bookings only on behalf of that logged-in customer; the payment service accepts calls only from the booking service."*

**What the interviewer is really checking**
Workload identity vs user identity, least privilege, and practical tools.

**How I answer it**
1. **Transport + workload identity:** mesh mTLS everywhere (SPIFFE identities); mesh authorisation policy: payment accepts only the booking service's identity.
2. **User context:** the assistant passes the user's token (or an exchanged, down-scoped token with audience `booking-service`) to the booking service, which enforces "customer may read own bookings".
3. **Service-only calls** (batch jobs) use client-credentials tokens with narrow scopes.
4. Validate tokens in every service (Spring resource server), not only at the gateway.
5. **AI-specific:** the assistant's tools act with the **user's** permissions, never a super-user service account, so a prompt injection can't read other customers' data.
6. Network policies (default deny) as a second layer.

**Trade-offs and what can go wrong**
- Forwarding the raw user token everywhere widens the blast radius; token exchange limits audience and scope.
- A mesh adds latency (~1 ms per hop) and operational complexity.
- Certificates expire; automate rotation (the mesh does).

**How I'd monitor it**
Denied requests by policy, mTLS coverage percentage, token validation failures, unusual access patterns.

**Follow-ups to expect**
- *Without a mesh?* -> mTLS in the HTTP client with cert-manager-issued certificates, or tokens only.
- *API keys between services?* -> Weak: static, shared, hard to rotate.
- *Confused deputy?* -> A privileged service tricked into acting for an unprivileged caller; solved by passing and checking the user's identity.

**60-second answer**
"Two identities: the workload and the user. A service mesh gives every call mTLS and workload identity, so I can say payment only accepts calls from booking, with default-deny network policies as a second layer. User context travels as the user's token or an exchanged, down-scoped one, and every service validates it, not just the gateway. That matters for AI: the assistant's tools act with the customer's permissions, so a prompt injection can't read someone else's bookings."

### Q9 [senior] Release changes with zero downtime: deployment strategies and database migrations.
tags: zero-downtime, blue-green, canary, feature-flags, expand-contract, flyway, profile-java-genai

**Start here: the concepts**
- **Rolling update:** replace pods gradually. **Blue-green:** two full environments, switch traffic. **Canary:** send a small percentage to the new version, watch, then increase.
- **Expand-contract (parallel change):** DB schema changes in backward-compatible steps.
- **Feature flags:** deploy code dark, release by toggling.

**The live scenario (functional requirement)**
*FR: "Rename `customer_name` to `first_name` + `last_name` and ship a new RAG prompt, during business hours, with no downtime and instant rollback."*

**What the interviewer is really checking**
That you decouple deploy from release and handle schema changes with old and new code running together.

**How I answer it**
1. **Expand:** Flyway migration adds `first_name`, `last_name` (nullable). Old code still works.
2. **Dual write:** new version writes both old and new columns; backfill existing rows in batches.
3. **Switch reads** to the new columns (behind a flag), verify.
4. **Contract:** after all pods run the new version and no reader uses the old column, drop `customer_name` in a later release.
5. **Rollout:** canary 5% -> 25% -> 100% with automated analysis (Argo Rollouts/Flagger) on error rate and p99; auto-rollback on breach.
6. **Prompt change** behind a feature flag with a percentage rollout, compared on quality metrics (thumbs-up rate, groundedness) before 100%.
7. Readiness probes and graceful shutdown so rolling updates don't drop requests.

**Trade-offs and what can go wrong**
- A destructive migration in the same release as the code breaks rollback.
- Long-running migrations lock tables; use online schema change tools or batched updates.
- Blue-green doubles capacity cost during the switch.

**How I'd monitor it**
Canary vs baseline error rate and latency, flag exposure, migration progress, rollback count.

**Follow-ups to expect**
- *Who runs migrations?* -> A job/init step before rollout, or the app via Flyway with a lock; one runner only.
- *Rollback of a migration?* -> Prefer roll-forward; expand-contract makes rollback of code safe without schema rollback.
- *Dark launch?* -> Run new code on real traffic without exposing results.

**60-second answer**
"I separate deploy from release. Schema changes use expand-contract: add the new columns, dual-write and backfill, switch reads behind a flag, and drop the old column only in a later release, so old and new pods always work and rollback stays safe. Rollouts are canaries, 5, 25, 100 percent, with automated analysis on errors and latency and auto-rollback. The new prompt goes behind a feature flag with a percentage rollout, judged on answer-quality metrics before full release."

### Q10 [mid] What does cloud-native and 12-factor mean for a Spring Boot microservice?
tags: twelve-factor, cloud-native, stateless, disposability, config, logs, profile-java-genai

**Start here: the concepts**
- **12-factor app:** codebase, dependencies, config in the environment, backing services as attached resources, build/release/run, stateless processes, port binding, concurrency, disposability, dev/prod parity, logs as streams, admin processes.
- **Cloud-native:** containers, dynamic orchestration, microservices, automation, observability.

**The live scenario (functional requirement)**
*FR: "The chat service must scale from 3 to 40 pods automatically and survive any pod being killed at any time."* The legacy version stored chat sessions in an in-memory `HashMap` and wrote logs to `/var/log/app.log`.

**What the interviewer is really checking**
That you can turn the principles into concrete changes.

**How I answer it**
1. **Stateless processes:** move chat sessions and conversation memory to Redis or a database; any pod can serve any request.
2. **Config in the environment:** env vars / mounted config; one image for all environments.
3. **Logs as event streams:** write to stdout in JSON; the platform ships them.
4. **Disposability:** fast startup, graceful shutdown on SIGTERM, idempotent processing so a killed pod's work can be retried.
5. **Backing services** (DB, Kafka, vector store, LLM endpoint) as URLs in config; swap without code change.
6. **Dev/prod parity:** Testcontainers / Docker Compose locally with the same Postgres and Kafka versions.
7. **Admin processes:** migrations as one-off jobs, not manual SQL.

**Trade-offs and what can go wrong**
- Sticky sessions are a crutch that breaks autoscaling and failover.
- Externalising state adds latency (Redis ~1 ms) and a dependency to monitor.

**How I'd monitor it**
Pod churn vs error rate (kill a pod in a chaos test, errors should stay flat), startup time, log ingestion.

**Follow-ups to expect**
- *Is 12-factor still relevant?* -> Yes, it's the baseline that Kubernetes assumes.
- *What about local file uploads?* -> Object storage, never pod disk.
- *Health checks?* -> Liveness and readiness probes, part of disposability.

**60-second answer**
"Concretely: no state in the pod. Chat sessions moved from an in-memory map to Redis, so any pod can serve any request and autoscaling or a killed pod loses nothing. Config comes from the environment with one image everywhere, logs go to stdout as JSON, startup is fast and SIGTERM triggers graceful shutdown, and backing services like the vector store and LLM endpoint are just URLs in config. Local dev uses the same Postgres and Kafka versions through Testcontainers."

### Q11 [senior] Autoscale microservices: HPA, KEDA and the limits of scaling.
tags: autoscaling, hpa, keda, kubernetes, capacity, scaling, profile-java-genai

**Start here: the concepts**
- **HPA:** scales pods on CPU, memory or custom metrics. **VPA:** adjusts requests/limits. **Cluster Autoscaler / Karpenter:** adds nodes.
- **KEDA:** event-driven autoscaling on external signals (Kafka lag, queue length, Prometheus queries), including scale to zero.

**The live scenario (functional requirement)**
*FR: "Document ingestion bursts to 50,000 PDFs when a client onboards; it must finish within 2 hours, and cost nothing when idle."* CPU-based HPA scaled too late because workers wait on the embedding API (low CPU).

**What the interviewer is really checking**
Choosing the right scaling signal and knowing downstream limits.

**How I answer it**
1. **Signal:** for queue workers, scale on **backlog** (Kafka consumer lag or queue length) with KEDA, not CPU.
2. Target: lag per pod, e.g. 500 messages; min 0, max bounded by **partitions** (Kafka consumers in a group can't exceed partition count usefully) and the **embedding API quota**.
3. **Capacity math:** 50,000 docs / 7,200 s ≈ 7 docs/s; each doc takes ~4 s of embedding calls -> ~28 concurrent; with 4 per pod -> ~7–10 pods.
4. **API-facing services:** HPA on CPU or requests per second; keep min replicas ≥ 2 across zones.
5. **Nodes:** Karpenter/Cluster Autoscaler; consider spot instances for batch workers.
6. Stabilisation windows to avoid flapping; fast scale-up, slow scale-down.

**Trade-offs and what can go wrong**
- Scaling consumers beyond partitions gives idle pods.
- Scale-up is limited by startup time and node provisioning (minutes).
- Scaling workers can just overload the downstream (DB, LLM quota): the bottleneck moves.

**How I'd monitor it**
Lag and its trend, replica count, time-to-drain, downstream 429s, cost per document.

**Follow-ups to expect**
- *Scale to zero for HTTP?* -> Possible with KEDA HTTP add-on or Knative, at the cost of cold starts.
- *HPA on JVM memory?* -> Poor signal; the heap doesn't shrink after load.
- *Predictive scaling?* -> Schedule scale-ups for known peaks (cron-based KEDA scaler).

**60-second answer**
"For ingestion workers CPU is the wrong signal, since they wait on the embedding API. I scale on backlog with KEDA: Kafka lag per pod, minimum zero so idle costs nothing, and a maximum capped by partition count and the embedding quota. Capacity math says 50,000 docs in two hours needs about 28 concurrent embeddings, so roughly 8 pods. API services stay on HPA with at least two replicas across zones, Karpenter adds nodes, and I watch downstream 429s because scaling just moves the bottleneck."

### Q12 [senior] Separate reads from writes with CQRS for an order-history screen.
tags: cqrs, read-model, materialized-view, events, elasticsearch, eventual-consistency, profile-java-genai

**Start here: the concepts**
- **CQRS:** separate models (and often stores) for commands (writes) and queries (reads).
- **Read model / materialised view:** a denormalised projection built from events, shaped for one screen.

**The live scenario (functional requirement)**
*FR: "Customers see their full trip history (flights, hotels, cars, points earned) on one screen with search and filters; the data comes from 4 services."* Today the screen makes 4 synchronous calls and joins in memory, taking 2.5 s.

**What the interviewer is really checking**
When CQRS is justified, how projections stay in sync, and the consistency trade-off.

**How I answer it**
1. A **trip-history query service** subscribes to `FlightBooked`, `HotelBooked`, `CarBooked`, `PointsEarned`, `BookingCancelled` events.
2. It maintains a denormalised document per customer trip in a store fit for querying (Elasticsearch/OpenSearch for search, or MongoDB/Postgres JSONB).
3. The screen does **one query** -> ~50 ms.
4. Projections are **idempotent** (upsert by event id/version) and can be **rebuilt** by replaying topics from the start.
5. Writes still go to each owning service; the read side never writes back.
6. UI handles lag: after booking, show the confirmation from the write response, and the history catches up in seconds.

**Trade-offs and what can go wrong**
- Eventual consistency: the new booking may take a second to appear.
- More moving parts: a projection bug needs a replay.
- CQRS for simple CRUD is overkill; use it for read-heavy, multi-source, or search screens.

**How I'd monitor it**
Projection lag (event time vs applied time), consumer lag, reconciliation counts between source and read model.

**Follow-ups to expect**
- *CQRS requires event sourcing?* -> No; they combine well but are independent.
- *Out-of-order events?* -> Version per aggregate; ignore older versions.
- *API composition instead?* -> Fine for low traffic; CQRS when latency and load matter.

**60-second answer**
"Instead of four synchronous calls and an in-memory join, I build a read model: a trip-history service consumes booking and points events and keeps one denormalised document per trip in OpenSearch. The screen does a single query in about 50 milliseconds. Projections are idempotent and rebuildable by replaying topics, writes still go to the owning services, and the UI covers the second or so of lag by showing the write response first. For plain CRUD I wouldn't bother."

### Q13 [architect] Design for high availability and disaster recovery across zones and regions.
tags: high-availability, disaster-recovery, multi-region, rto, rpo, active-active, profile-java-genai

**Start here: the concepts**
- **RTO:** how long you can be down. **RPO:** how much data you can lose.
- **Multi-AZ:** survives a data-centre failure within a region; table stakes.
- **Multi-region:** active-passive (warm standby, pilot light) or active-active (hardest: data conflicts).

**The live scenario (functional requirement)**
*FR: "Booking must survive a full region outage with RTO 30 minutes and RPO 5 minutes; search and the AI assistant may degrade."*

**What the interviewer is really checking**
Matching architecture and cost to stated RTO/RPO, and actually testing failover.

**How I answer it**
1. **Every region:** services across 3 AZs, PDBs, managed DB with multi-AZ.
2. **Region strategy:** RTO 30 min / RPO 5 min fits **warm standby**: a smaller copy running in region B.
3. **Data:** DB cross-region replicas (Aurora Global Database / Azure SQL geo-replication: typically seconds of lag), Kafka mirrored with MirrorMaker 2 / cluster linking, object storage replication, vector index rebuildable or replicated.
4. **Failover:** DNS/global load balancer (Route 53 / Front Door) health-based switch; promote replicas; scale up region B via autoscaling.
5. **Degrade non-critical:** the AI assistant may run on a different model endpoint/region; search can serve cached content.
6. **Runbooks and game days:** fail over for real twice a year; untested DR is a hope, not a plan.

**Trade-offs and what can go wrong**
- Active-active needs conflict handling (idempotent writes, region-owned records); costly in complexity.
- Async replication means some data loss within RPO; communicate it.
- Hidden single-region dependencies (an identity provider, a secrets store, an LLM endpoint) break failover.

**How I'd monitor it**
Replication lag vs RPO, health of standby, failover drill results (actual RTO/RPO achieved).

**Follow-ups to expect**
- *Backups vs replication?* -> Replication copies mistakes too; backups protect against deletion and corruption.
- *Why not active-active?* -> Only when RTO near zero justifies conflict-resolution complexity.
- *LLM provider outage?* -> Multi-provider or multi-region routing behind an AI gateway, plus graceful "assistant unavailable".

**60-second answer**
"I start from the numbers: RTO 30 minutes and RPO 5 minutes point to warm standby, not active-active. Each region runs across three AZs; data replicates cross-region with seconds of lag: the database's global replicas, Kafka mirroring, object storage replication. A health-based global load balancer fails over, we promote replicas and scale region B. The AI assistant and search degrade gracefully. Above all, we run failover drills, because hidden single-region dependencies only show up when you test."

### Q14 [senior] How do you control and reduce cloud cost for microservices, including GenAI spend?
tags: finops, cost-optimization, rightsizing, spot-instances, llm-cost, cloud, profile-java-genai

**Start here: the concepts**
- **FinOps:** making cost visible, owned and optimised continuously.
- **Levers:** rightsizing, autoscaling, spot/preemptible capacity, reservations/savings plans, storage tiers, data transfer.
- **GenAI cost** = tokens in + tokens out × price per model; often the biggest new line item.

**The live scenario (functional requirement)**
*FR: "Cut the platform's monthly cloud bill by 30% without hurting SLOs; the new AI features alone cost as much as the rest of compute."*

**What the interviewer is really checking**
A data-driven approach and GenAI-specific levers.

**How I answer it**
1. **Visibility:** tag every resource by team/service; cost per request and per customer; showback to teams.
2. **Compute:** rightsize requests from real usage (many JVM pods ask for 2 CPUs and use 0.3); autoscale down at night; spot for batch workers; savings plans for the steady baseline.
3. **Data:** log retention tiers (hot 7 days, cold 90), compress, drop debug logs in prod; avoid cross-AZ chatter.
4. **GenAI:**
   - **Route by task:** a small/cheap model for classification and extraction, the big model only for hard reasoning.
   - **Cut tokens:** trim retrieved context (top 4 re-ranked chunks instead of 15), shorter system prompts, cap `max_tokens`.
   - **Cache:** provider-side prompt caching for long stable prefixes, an exact-match response cache, and a careful semantic cache.
   - **Batch APIs** for offline jobs (often ~50% cheaper), embeddings computed once and stored.
   - Consider self-hosted open-weight models for very high steady volume.
5. Budgets and anomaly alerts per team.

**Trade-offs and what can go wrong**
- Aggressive rightsizing causes CPU throttling and latency; leave headroom.
- Smaller models reduce quality; route with evaluation, not guesses.
- Spot interruptions need idempotent, checkpointed jobs.

**How I'd monitor it**
Cost per service per day, cost per 1,000 requests, tokens per request by feature, cache hit ratio, anomaly alerts.

**Follow-ups to expect**
- *Self-host vs API for LLMs?* -> Self-hosting needs GPUs at high utilisation to pay off, plus MLOps skill.
- *Biggest hidden cost?* -> Data transfer (NAT gateways, cross-region) and log ingestion.
- *How do you make teams care?* -> Show cost next to their SLO dashboards.

**60-second answer**
"First visibility: tags, cost per service and per request, shown to the owning team. Then the usual levers: rightsizing JVM pods from real usage, scaling down at night, spot for batch, savings plans for the baseline, log retention tiers. For GenAI, which was half the bill: route easy tasks to a small model, send four re-ranked chunks instead of fifteen, cap output tokens, use prompt and response caching, and push offline jobs to batch APIs. Every change is checked against quality evaluations and SLOs."

### Q15 [architect] When would you NOT choose microservices?
tags: modular-monolith, architecture-decision, microservices, trade-offs, team-topology, profile-java-genai

**Start here: the concepts**
- **Microservices tax:** network failures, distributed data, observability, CI/CD per service, on-call.
- **Modular monolith:** one deployable with strict module boundaries; much of the design benefit at a fraction of the cost.
- **Conway's law:** systems mirror the communication structure of the organisation.

**The live scenario (functional requirement)**
*FR: "A 6-developer team must launch a GenAI-powered expense-audit product in 4 months; scale is 200 users at launch."* Leadership asks for "microservices on Kubernetes because that's modern".

**What the interviewer is really checking**
Senior judgement: architecture serves constraints, not trends.

**How I answer it**
1. Ask what microservices would buy: independent team deploys (one team), independent scaling (200 users), fault isolation (low traffic). None is a current need.
2. Recommend a **modular monolith** in Spring Boot with Spring Modulith: modules for intake, extraction (LLM), policy rules, reporting; communication via events; hexagonal ports around the LLM.
3. Deploy as a container on a managed platform (App Runner / Azure Container Apps / a small k8s); one DB with schema per module.
4. **Exception:** the GPU-hungry or bursty piece (e.g. a document OCR/embedding worker) can be a separate worker from day one because it scales differently.
5. Define **extraction triggers**: a second team, different scaling profile, different release cadence. The module boundaries make extraction a refactor, not a rewrite.

**Trade-offs and what can go wrong**
- A monolith without enforced boundaries decays into a big ball of mud; boundaries must be tested.
- Too late to split can also hurt; watch the triggers.

**How I'd monitor it**
Lead time and deployment frequency, build time, module dependency violations; these tell you when it's time to split.

**Follow-ups to expect**
- *How do you convince leadership?* -> Show time-to-market and ops cost, and the documented path to split later.
- *Shared DB in a modular monolith?* -> Shared instance, but each module owns its schema/tables.
- *Microservices and team size?* -> A rough guide: a service per team, not per developer.

**60-second answer**
"When the constraints don't need it. Six developers, one team, 200 users and a four-month deadline get nothing from independent deploys or scaling, but would pay the full distributed-systems tax. I'd build a modular monolith with Spring Modulith, modules talking through events and the LLM behind a port, plus one separately scaled worker for the bursty embedding work. I'd write down the triggers for splitting, like a second team or a different scaling profile, and the module boundaries make that a refactor later, not a rewrite."
