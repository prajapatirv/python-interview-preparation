---
id: profile-java-genai-containerization
title: Java + GenAI profile (6/9): Containerization (Docker and Kubernetes), 15 functional-requirement questions
stack: java
skill: cloud-devops
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Build a small, fast, secure Docker image for a Spring Boot service.
tags: docker, dockerfile, multi-stage-build, layered-jar, buildpacks, jib, profile-java-genai

**Start here: the concepts**
- **Image layers:** each Dockerfile instruction makes a cached layer; unchanged layers are reused on rebuild and pull.
- **Multi-stage build:** build in a JDK image, copy only the result into a small JRE image.
- **Spring Boot layered jars:** split dependencies (rarely change) from application classes (change every build).
- **Alternatives:** Cloud Native Buildpacks (`mvn spring-boot:build-image`), Jib (no Dockerfile, no Docker daemon).

**The live scenario (functional requirement)**
*FR: "Every commit should produce a deployable image in under 3 minutes; images must be small and pass the security scan."* The current image is 900 MB, built from a full JDK with the fat jar copied in one layer, so every build re-uploads 120 MB.

**What the interviewer is really checking**
Layer caching, minimal runtime images, and non-root execution.

**How I answer it**
1. Multi-stage: stage 1 `eclipse-temurin:25-jdk` builds and extracts layers; stage 2 `eclipse-temurin:25-jre` (or a distroless Java image) runs.
2. Extract layers (`java -Djarmode=tools -jar app.jar extract --layers --launcher`) and `COPY` dependencies, spring-boot-loader, snapshot-dependencies and application **as separate layers**; code changes only rebuild the small last layer.
3. **Non-root user** (`USER 1001`), no shell tools in distroless.
4. JVM flags via `JAVA_TOOL_OPTIONS` (`-XX:MaxRAMPercentage=75`), exec-form `ENTRYPOINT` so the JVM gets SIGTERM.
5. Or skip the Dockerfile: **buildpacks** produce layered, non-root, CDS-ready images with one command; **Jib** for daemonless CI.
6. Pin base images by digest and rebuild regularly for patches.

**Trade-offs and what can go wrong**
- Alpine (musl) images can surprise JVM users; prefer Debian/Ubuntu-based or distroless JRE images.
- Distroless means no shell for debugging; use ephemeral debug containers (`kubectl debug`).
- Shell-form `ENTRYPOINT` makes `sh` PID 1, which doesn't forward signals -> no graceful shutdown.

**How I'd monitor it**
Image size and build time in CI, vulnerability counts per image, base-image age.

**Follow-ups to expect**
- *Why JRE not JDK at runtime?* -> Smaller and fewer tools to exploit; use `jlink` for a custom minimal runtime if needed.
- *`.dockerignore`?* -> Keeps `target/`, `.git`, secrets out of the build context.
- *Image tags?* -> Immutable tags (git SHA), never deploy `latest`.

**60-second answer**
"Multi-stage build: compile in a JDK image, run in a slim JRE or distroless image. I extract Spring Boot's layers so dependencies, loader and application code are separate layers, so a code change rebuilds and pushes only a few hundred KB. The container runs as non-root with an exec-form entrypoint so SIGTERM reaches the JVM, and memory is set as a percentage. Buildpacks or Jib give the same result without a Dockerfile. Images are tagged by git SHA and rebuilt for base patches."

### Q2 [senior] Run the JVM correctly inside containers: memory, CPU and OOMKilled.
tags: jvm, containers, maxrampercentage, oomkilled, cpu-limits, native-memory, profile-java-genai

**Start here: the concepts**
- **Container awareness:** modern JVMs (10+, and 8u191+) read cgroup limits for memory and CPU.
- **Heap is not all memory:** metaspace, thread stacks, code cache, direct buffers, GC structures, native libraries.
- **OOMKilled (exit 137):** the kernel killed the container for exceeding its memory limit, regardless of the heap.

**The live scenario (functional requirement)**
*FR: "The RAG API pod has a 2 GiB limit and must not restart under load."* It's OOMKilled every few hours with no Java `OutOfMemoryError`; it was started with `-Xmx2g`.

**What the interviewer is really checking**
Understanding total JVM footprint and CPU effects of limits.

**How I answer it**
1. `-Xmx2g` in a 2 GiB container leaves zero room for non-heap memory -> OOMKilled.
2. Use `-XX:MaxRAMPercentage=70` (heap ~1.4 GiB) so ~600 MiB covers metaspace, threads, direct buffers (Netty, HTTP clients), code cache.
3. Measure with **Native Memory Tracking** (`-XX:NativeMemoryTracking=summary`, `jcmd <pid> VM.native_memory summary`) under load.
4. **Requests = limits for memory** (Guaranteed-style memory): avoids eviction surprises.
5. **CPU:** the JVM sizes GC threads and the common pool from the CPU limit. A limit of 1 CPU means few GC threads and **CFS throttling** under spikes, which shows as latency. Give at least 2 CPUs to latency-sensitive JVMs, or set CPU requests without hard limits where policy allows.
6. Libraries that load ML models off-heap (e.g. local ONNX embedding) need extra headroom.

**Trade-offs and what can go wrong**
- Too small a heap -> GC thrash; too large -> OOMKilled. Size from measurements.
- Thousands of platform threads (1 MB stack reservation each) eat native memory; virtual threads help.

**How I'd monitor it**
Container working-set memory vs limit, restarts with reason OOMKilled, JVM heap and non-heap metrics, CPU throttling (`container_cpu_cfs_throttled_periods_total`).

**Follow-ups to expect**
- *Exit code 137 vs 143?* -> 137 = SIGKILL (OOM or forced), 143 = SIGTERM (normal stop).
- *`-XX:ActiveProcessorCount`?* -> Overrides detected CPUs when the limit misleads sizing.
- *Swap?* -> Usually disabled on Kubernetes nodes.

**60-second answer**
"`-Xmx2g` in a 2 GiB container leaves nothing for metaspace, thread stacks, direct buffers and the code cache, so the kernel kills it with no Java OOM. I size heap as a percentage, about 70%, and verify the rest with native memory tracking under load, with memory request equal to limit. CPU matters too: the JVM sizes GC and pools from the limit, and a 1-CPU limit causes throttling that shows up as latency spikes, so latency-sensitive JVMs get at least two CPUs."

### Q3 [senior] Secure the container supply chain: scanning, SBOM, signing and runtime hardening.
tags: container-security, trivy, sbom, image-signing, non-root, supply-chain, profile-java-genai

**Start here: the concepts**
- **Vulnerability scanning:** Trivy, Grype, cloud registry scanners check OS packages and Java dependencies.
- **SBOM:** a software bill of materials (CycloneDX/SPDX) listing every component.
- **Signing:** Sigstore cosign signs images; admission policies verify before deploy.
- **Runtime hardening:** non-root, read-only filesystem, drop Linux capabilities, no privilege escalation.

**The live scenario (functional requirement)**
*FR: "The bank's security policy: no critical CVEs in production images, provenance proof for every image, and containers must not run as root."*

**What the interviewer is really checking**
Shift-left security integrated into CI/CD and enforced at deploy time.

**How I answer it**
1. **Build:** minimal base images; dependency scanning (OWASP Dependency-Check or Trivy on the jar) and image scanning in CI; fail the build on critical CVEs with an exception process.
2. **SBOM:** generate CycloneDX (Maven plugin or Syft) and attach it to the image as an attestation.
3. **Sign:** cosign signs the image digest in CI (keyless with OIDC); **provenance** attestations (SLSA).
4. **Admission:** Kyverno or OPA Gatekeeper policies: only signed images from our registry, `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, `capabilities: drop: [ALL]`, no `:latest`. Pod Security Admission at "restricted".
5. **Continuous:** rescan running images daily; new CVEs trigger rebuilds.
6. **Secrets:** never baked into images; scan layers for leaked secrets.

**Trade-offs and what can go wrong**
- Blocking on every CVE stalls delivery; triage by exploitability (VEX) and fix windows.
- Read-only filesystems need explicit `emptyDir` for temp dirs (Tomcat, multipart uploads).

**How I'd monitor it**
CVE counts by severity per running image, unsigned-image admission denials, image age.

**Follow-ups to expect**
- *Log4Shell lesson?* -> Know what's deployed (SBOM) to answer "are we affected?" in minutes.
- *Distroless benefit?* -> Fewer packages = fewer CVEs and no shell for attackers.
- *Runtime threat detection?* -> Falco watches syscalls for suspicious behaviour.

**60-second answer**
"I secure the chain end to end. CI builds from minimal bases, scans dependencies and the image with Trivy and fails on criticals, generates a CycloneDX SBOM and signs the image with cosign plus a provenance attestation. At deploy, Kyverno or Gatekeeper admits only signed images from our registry that run as non-root with a read-only filesystem and all capabilities dropped. Running images are rescanned daily, and the SBOM answers 'are we affected?' in minutes when the next Log4Shell lands."

### Q4 [mid] Which Kubernetes objects does a typical Spring Boot microservice need?
tags: kubernetes, deployment, service, configmap, secret, ingress, hpa, profile-java-genai

**Start here: the concepts**
- **Pod:** smallest unit (one or more containers). **Deployment:** manages ReplicaSets for rolling updates.
- **Service:** stable name/IP load-balancing to pods. **Ingress / Gateway API:** external HTTP routing.
- **ConfigMap / Secret:** configuration. **HPA:** autoscaling. **PDB:** disruption budget. **ServiceAccount:** pod identity.

**The live scenario (functional requirement)**
*FR: "Deploy the booking API: 3+ replicas across zones, reachable at api.example.com/bookings, config per environment, autoscale on load, survive node maintenance."*

**What the interviewer is really checking**
That you can assemble a production-ready set, not just a Deployment.

**How I answer it**
1. **Deployment:** replicas 3, resource requests/limits, liveness/readiness/startup probes, `topologySpreadConstraints` across zones, rolling-update strategy, security context (non-root).
2. **Service** (ClusterIP) on port 8080 -> pods by label.
3. **Ingress/HTTPRoute** for `api.example.com/bookings` with TLS (cert-manager).
4. **ConfigMap** for settings, **Secret** (synced from a vault) for credentials, mounted as files.
5. **HPA** on CPU or requests per second, min 3 / max 20.
6. **PodDisruptionBudget** `minAvailable: 2` so node drains don't take all pods.
7. **ServiceAccount** with workload identity for cloud access; **NetworkPolicy** limiting who can call it.
8. Packaged with **Helm** or Kustomize; deployed by GitOps.

**Trade-offs and what can go wrong**
- No requests set -> the scheduler overpacks nodes; noisy neighbours.
- No PDB -> a cluster upgrade can evict every replica at once.
- One replica per zone missing -> a zone failure takes the service out.

**How I'd monitor it**
Ready replicas vs desired, restarts, HPA status, Ingress 5xx, pod distribution across zones.

**Follow-ups to expect**
- *Deployment vs StatefulSet?* -> StatefulSet for stable identity and storage (databases, Kafka).
- *DaemonSet?* -> One pod per node (log or metrics agents).
- *Job/CronJob?* -> Run-to-completion and scheduled work.

**60-second answer**
"A Deployment with three replicas spread across zones, requests and limits, the three probes and a non-root security context. A ClusterIP Service in front, an Ingress or Gateway route for api.example.com/bookings with cert-manager TLS, a ConfigMap and vault-synced Secrets mounted as files. An HPA from 3 to 20, a PodDisruptionBudget so node drains keep two pods, a ServiceAccount with workload identity and a NetworkPolicy. All packaged in Helm and deployed through GitOps."

### Q5 [senior] Configure liveness, readiness and startup probes and graceful shutdown for Spring Boot.
tags: probes, liveness, readiness, startup-probe, graceful-shutdown, actuator, profile-java-genai

**Start here: the concepts**
- **Liveness:** "is the process stuck?" Failing -> restart. **Readiness:** "can it take traffic now?" Failing -> removed from Service endpoints. **Startup:** protects slow boots from liveness kills.
- **Spring Boot Actuator** exposes `/actuator/health/liveness` and `/readiness` (auto-enabled on Kubernetes).
- **Graceful shutdown:** on SIGTERM stop accepting, finish in-flight requests.

**The live scenario (functional requirement)**
*FR: "Deploys and node drains must cause zero failed requests; a database blip must not restart all pods."* Last month a DB outage made liveness fail, Kubernetes restarted every pod, and recovery took 15 minutes longer than the DB outage.

**What the interviewer is really checking**
That external dependencies never go into liveness, and the shutdown sequence is right.

**How I answer it**
1. **Liveness** = only the app's own state (the `livenessState`), **never** DB/Kafka/LLM checks. A DB blip shouldn't restart healthy JVMs.
2. **Readiness** = can serve: include the DB if requests can't be served without it (choose carefully; if all pods go unready at once, the Service has no endpoints anyway).
3. **Startup probe** with enough budget (e.g. 30 × 5 s) for a slow boot; liveness starts after it passes.
4. **Graceful shutdown:** `server.shutdown=graceful` (default since Boot 3.4) and `spring.lifecycle.timeout-per-shutdown-phase=30s`.
5. **preStop sleep** (~5–10 s) so endpoints are removed from load balancers *before* the app stops accepting; `terminationGracePeriodSeconds` > preStop + shutdown phase.
6. Readiness also goes DOWN during shutdown automatically (Boot publishes `ReadinessState.REFUSING_TRAFFIC`).

**Trade-offs and what can go wrong**
- Aggressive liveness timeouts kill pods during long GC pauses or CPU throttling.
- Heavy health checks (calling the LLM) cost money and add load; keep them cheap.

**How I'd monitor it**
Restart counts and reasons, 5xx during deploys, readiness flaps, probe latency.

**Follow-ups to expect**
- *What does a failing readiness probe do?* -> Pod stays running but gets no traffic.
- *Kafka consumers on shutdown?* -> Stop the container, commit offsets, then exit.
- *Why preStop sleep?* -> Endpoint removal propagates asynchronously to kube-proxy and ingress.

**60-second answer**
"Liveness only reflects the JVM's own health, never the database; that mistake turned a DB blip into restarting every pod. Readiness says whether this pod can serve now, a startup probe protects slow boots, and Actuator exposes both groups. For zero-downtime shutdown: graceful shutdown with a 30-second phase timeout, a short preStop sleep so load balancers drop the pod before it stops accepting, and a termination grace period longer than both. Readiness flips to refusing traffic automatically during shutdown."

### Q6 [senior] Set resource requests and limits and understand QoS classes.
tags: kubernetes, resources, requests, limits, qos, cpu-throttling, profile-java-genai

**Start here: the concepts**
- **Requests:** what the scheduler reserves; **limits:** the hard cap.
- **CPU over limit** -> throttled; **memory over limit** -> OOMKilled.
- **QoS classes:** Guaranteed (requests = limits for all), Burstable, BestEffort (none); evicted in reverse order under node pressure.

**The live scenario (functional requirement)**
*FR: "Run 40 services on a shared cluster at good density, without noisy neighbours hurting the checkout's p99."*

**What the interviewer is really checking**
Data-driven sizing and the CPU-limit debate.

**How I answer it**
1. Set **requests from measured usage** (p95 CPU and memory over a week), via VPA in recommendation mode or metrics.
2. **Memory:** request = limit (predictable, avoids surprise eviction).
3. **CPU:** request for scheduling; for latency-critical JVM services consider **no CPU limit** (or a generous one) to avoid throttling, while namespaces have quotas to prevent abuse.
4. Checkout gets Guaranteed QoS and a higher PriorityClass; batch jobs BestEffort/Burstable on separate node pools (taints/tolerations).
5. **LimitRange** defaults and **ResourceQuota** per namespace.
6. Re-check sizing after major releases (JVM upgrades, new features).

**Trade-offs and what can go wrong**
- Over-requesting wastes money; under-requesting overpacks nodes.
- CPU limits below JVM burst needs (JIT, GC at startup) slow startup and cause throttling.

**How I'd monitor it**
Usage vs requests per pod (efficiency), CPU throttling ratio, OOMKills, node allocatable vs requested.

**Follow-ups to expect**
- *What is millicores?* -> 1000m = one CPU.
- *VPA and HPA together?* -> Not on the same metric; VPA in recommendation mode is safest.
- *Pod priority?* -> Higher priority pods can preempt lower ones when the cluster is full.

**60-second answer**
"Requests are what the scheduler reserves, limits are the cap: CPU over limit is throttled, memory over limit is killed. I set requests from a week of measured usage, memory request equal to limit, and for latency-critical JVMs I avoid tight CPU limits because throttling shows up as p99 spikes, relying on namespace quotas instead. Checkout gets Guaranteed QoS and a higher priority class, batch runs on its own tainted node pool, and I review efficiency and throttling dashboards."

### Q7 [mid] Manage configuration and secrets in Kubernetes safely.
tags: configmap, secret, external-secrets, vault, csi-driver, configuration, profile-java-genai

**Start here: the concepts**
- **ConfigMap:** non-sensitive key-values or files. **Secret:** sensitive data, base64-encoded (not encrypted) by default.
- **External Secrets Operator / Secrets Store CSI driver:** sync or mount secrets from Vault, AWS Secrets Manager, Azure Key Vault.
- **Mounted files** update in place (not for `subPath`); env vars don't change until restart.

**The live scenario (functional requirement)**
*FR: "The assistant service needs the vector DB password and the LLM API key per environment; rotation monthly; developers must not be able to read prod secrets."*

**What the interviewer is really checking**
Secure storage, access control and rotation mechanics.

**How I answer it**
1. Source of truth in a vault; **External Secrets Operator** creates Kubernetes Secrets in each namespace from it.
2. **etcd encryption at rest** enabled (or KMS provider); **RBAC**: developers have no `get secrets` in prod namespaces.
3. Mount as files: `spring.config.import=optional:configtree:/etc/secrets/`.
4. **Rotation:** vault rotates; ESO refreshes the Secret; the app re-reads files or a tool like Reloader triggers a rolling restart.
5. Config in ConfigMaps from Git (Helm values per environment).
6. Avoid secrets in Helm values files in Git; if they must be in Git, use Sealed Secrets or SOPS encryption.

**Trade-offs and what can go wrong**
- `kubectl describe` doesn't show values, but `get -o yaml` does: RBAC matters.
- Env-var secrets leak through `/actuator/env` or crash dumps if not masked.

**How I'd monitor it**
Sync failures in ESO, secret age, RBAC audit logs for secret access.

**Follow-ups to expect**
- *Immutable ConfigMaps?* -> `immutable: true` protects and improves performance; changes need a new name.
- *Why not bake config into the image?* -> Breaks one-image-for-all-environments.
- *GitOps with secrets?* -> ESO references in Git, values stay in the vault.

**60-second answer**
"The vault is the source of truth and the External Secrets Operator syncs secrets into each namespace, with etcd encryption on and RBAC so developers can't read prod secrets. Apps read them as mounted files through Spring's configtree import, not env vars. When the vault rotates a key, ESO refreshes the Secret and the app reloads or does a rolling restart via Reloader. Non-secret config is ConfigMaps from Helm values in Git; secrets in Git only ever appear encrypted, with SOPS or Sealed Secrets."

### Q8 [senior] Achieve zero-downtime rolling updates on Kubernetes.
tags: rolling-update, maxsurge, maxunavailable, pdb, prestop, zero-downtime, profile-java-genai

**Start here: the concepts**
- **Rolling update parameters:** `maxSurge` (extra pods during the update), `maxUnavailable` (pods allowed down).
- **Readiness gates traffic;** a new pod receives requests only when ready.
- **PodDisruptionBudget** protects against voluntary disruptions (drains), not against deploys.

**The live scenario (functional requirement)**
*FR: "Deploy the payment API 10 times a day with zero failed requests."* Each deploy shows a burst of 502s and connection resets.

**What the interviewer is really checking**
The full sequence: startup, readiness, endpoint propagation, shutdown.

**How I answer it**
1. Strategy: `maxSurge: 25%`, `maxUnavailable: 0`: always full capacity.
2. **Readiness** returns UP only after warm-up (caches, connection pools, a few JIT warm-up calls).
3. **Shutdown:** preStop `sleep 10` -> SIGTERM -> Spring graceful shutdown drains in-flight requests -> exit; `terminationGracePeriodSeconds: 45`.
4. **Keep-alive:** server keep-alive timeout longer than the load balancer's idle timeout, avoiding 502 on reused connections.
5. **Backward compatibility:** old and new versions run together for minutes: API and DB schema changes must be compatible (expand-contract).
6. **Progressive delivery:** Argo Rollouts canary with automated metric analysis for risky changes.
7. Clients retry idempotent requests once on connection reset.

**Trade-offs and what can go wrong**
- `maxUnavailable: 0` needs spare cluster capacity for the surge pods.
- Long-lived connections (SSE streams, WebSockets) are cut on shutdown; clients must reconnect, and drain time should cover typical stream length.

**How I'd monitor it**
5xx and connection resets annotated with deploy events, rollout duration, readiness time per pod.

**Follow-ups to expect**
- *Rollback?* -> `kubectl rollout undo` or revert in Git with GitOps.
- *Why 502 and not 503?* -> The LB forwarded to a pod that closed the connection.
- *minReadySeconds?* -> Waits a pod being ready for N seconds before counting it available.

**60-second answer**
"Zero downtime is a sequence. Surge with maxUnavailable zero, so capacity never drops. New pods report ready only after warm-up. Old pods get a preStop sleep so load balancers stop sending them traffic, then SIGTERM triggers Spring's graceful shutdown, inside a long enough grace period. The server's keep-alive outlives the LB's idle timeout to avoid 502s, and old and new versions must be compatible because they overlap. Risky changes go through an Argo Rollouts canary with automated analysis."

### Q9 [senior] Package and deploy with Helm or Kustomize, and GitOps with Argo CD.
tags: helm, kustomize, gitops, argo-cd, deployment, configuration-management, profile-java-genai

**Start here: the concepts**
- **Helm:** templated charts with values files; releases and rollbacks.
- **Kustomize:** template-free overlays patching a base (built into kubectl).
- **GitOps:** Git holds desired state; an agent (Argo CD, Flux) continuously syncs the cluster to it.

**The live scenario (functional requirement)**
*FR: "30 services, 3 environments; every change auditable; production changes approved; drift (manual kubectl edits) detected and reverted."*

**What the interviewer is really checking**
A maintainable, auditable deployment model.

**How I answer it**
1. A **shared Helm library chart** with the company's standard Deployment/Service/HPA/PDB/probes; each service has a small chart or values file.
2. Environment repos (or folders): `values-dev.yaml`, `values-prod.yaml`. Image tag updated by CI via a PR.
3. **Argo CD** watches the repo and syncs; **drift detection** shows and reverts manual changes (self-heal).
4. Production promotion = merge a PR with required approvals: audit trail for free.
5. ApplicationSets generate apps for all services/environments.
6. Secrets via ESO references, not values.

**Trade-offs and what can go wrong**
- Over-templated Helm charts become unreadable; keep the library opinionated and small.
- GitOps adds a repo hop; CI needs bot access to update tags.
- Kustomize lacks packaging/versioning; fine for in-house overlays.

**How I'd monitor it**
Argo sync status and health per app, out-of-sync alerts, deployment frequency and lead time.

**Follow-ups to expect**
- *Push vs pull deployments?* -> GitOps pull means the cluster pulls; CI doesn't need cluster credentials.
- *Rollback?* -> Revert the Git commit.
- *Helm hooks?* -> For migrations, though a separate Job managed by Argo sync waves is clearer.

**60-second answer**
"A shared Helm library chart encodes the standard Deployment, probes, HPA and PDB, so each service has only a small values file per environment. Argo CD watches Git and syncs the cluster, self-heals drift from manual kubectl edits, and production promotion is just a PR with approvals, so every change is audited and rollback is a revert. CI updates image tags by PR, and secrets are only referenced, never stored in values."

### Q10 [mid] Design a CI/CD pipeline for a containerised Spring Boot service.
tags: ci-cd, pipeline, github-actions, jenkins, testing, deployment, profile-java-genai

**Start here: the concepts**
- **CI:** build and test every change. **CD:** deliver automatically to environments, with gates.
- **Quality gates:** tests, coverage, static analysis (SonarQube), security scans.

**The live scenario (functional requirement)**
*FR: "From merge to production in under an hour, with automatic rollback, and no untested or unscanned image ever reaching prod."*

**What the interviewer is really checking**
Ordered stages, fast feedback, and safe promotion.

**How I answer it**
1. **PR stage:** compile, unit + slice tests, static analysis, dependency scan; Testcontainers integration tests in parallel. Target < 10 min.
2. **Merge:** build image once (Jib/buildpacks), tag with git SHA, scan, sign, generate SBOM, push.
3. **Deploy dev** (GitOps PR auto-merged) -> smoke tests + contract tests.
4. **Staging:** the same image (build once, promote many); performance smoke test; for GenAI features an **evaluation suite** on a golden question set with a quality threshold.
5. **Production:** canary via Argo Rollouts with automated analysis; auto-rollback on SLO breach.
6. DB migrations run as a pre-sync Job, backward compatible.

**Trade-offs and what can go wrong**
- Rebuilding per environment means prod runs an untested artifact.
- Slow pipelines get bypassed; parallelise and cache dependencies.
- LLM-based eval tests are non-deterministic; use thresholds over a set, not exact matches.

**How I'd monitor it**
DORA metrics (deployment frequency, lead time, change failure rate, MTTR), pipeline duration, flaky tests.

**Follow-ups to expect**
- *Trunk-based vs GitFlow?* -> Trunk-based with feature flags for frequent releases.
- *Where do secrets for CI live?* -> CI's secret store with OIDC federation to the cloud, no static keys.
- *How do you test infrastructure changes?* -> Plan/diff in PR, policy checks (OPA/conftest).

**60-second answer**
"PRs run compile, unit, slice and Testcontainers tests, static analysis and dependency scans in under ten minutes. On merge we build the image once, tag it with the git SHA, scan, sign and attach an SBOM. The same image is promoted through dev, with smoke and contract tests, and staging, where GenAI features also pass an evaluation threshold on a golden question set, then to prod as an Argo Rollouts canary with automated rollback. We track the DORA metrics."

### Q11 [mid] Set up local development with Docker Compose and Spring Boot's container support.
tags: docker-compose, local-development, testcontainers, spring-boot-docker-compose, devex, profile-java-genai

**Start here: the concepts**
- **Docker Compose:** run multi-container environments from one YAML.
- **`spring-boot-docker-compose`:** Boot starts `compose.yaml` services on run and wires connection details automatically.
- **Testcontainers at dev time:** `TestApplication` with `@ServiceConnection` containers for `spring-boot:test-run`.

**The live scenario (functional requirement)**
*FR: "A new developer must run the RAG service locally (Postgres with pgvector, Kafka, Redis, a local LLM) within 30 minutes of cloning, with no shared dev database."*

**What the interviewer is really checking**
Developer experience and dev/prod parity.

**How I answer it**
1. `compose.yaml` with `pgvector/pgvector` Postgres, Kafka (KRaft single node), Redis, and **Ollama** serving a small open-weight chat model and an embedding model.
2. Add `spring-boot-docker-compose` (dev-only dependency): `./mvnw spring-boot:run` starts the services and sets datasource/Kafka/Redis properties automatically (ServiceConnection).
3. Spring AI pointed at Ollama locally (`spring.ai.ollama.base-url`), the real provider in other environments: same code, different config.
4. Seed data: Flyway migrations + a sample document set ingested on startup in the `local` profile.
5. Same image versions as production for Postgres/Kafka.
6. README with one command; a Makefile/Taskfile for common tasks.

**Trade-offs and what can go wrong**
- Local LLMs answer differently (and slower) than production models; fine for development flow, not for quality evaluation.
- Laptops with low memory struggle with Kafka + Ollama; offer a "lite" profile.

**How I'd monitor it**
Time-to-first-successful-run for new joiners, number of "works on my machine" issues.

**Follow-ups to expect**
- *Compose in production?* -> No; Kubernetes or a managed container platform.
- *Testcontainers vs Compose?* -> Testcontainers for tests (and can serve dev too); Compose for a long-running local stack.
- *Hot reload?* -> Spring Boot DevTools.

**60-second answer**
"A compose.yaml with pgvector Postgres, single-node KRaft Kafka, Redis and Ollama running a small open-weight chat model and an embedding model. With spring-boot-docker-compose as a dev dependency, `spring-boot:run` starts the stack and wires the connection properties automatically. Spring AI talks to Ollama locally and the real provider elsewhere, with the same code. Flyway and a seed ingest make it usable immediately, and versions match production. A new joiner is running in minutes."

### Q12 [senior] A pod is in CrashLoopBackOff. Walk through your debugging.
tags: crashloopbackoff, kubectl, troubleshooting, pod-debugging, events, production-incident, profile-java-genai

**Start here: the concepts**
- **CrashLoopBackOff:** the container keeps exiting and Kubernetes restarts it with growing back-off delays.
- Key commands: `kubectl describe pod`, `kubectl logs --previous`, `kubectl get events`, `kubectl debug`.
- Exit codes: 1 (app error), 137 (SIGKILL/OOM), 143 (SIGTERM), 126/127 (command not executable/not found).

**The live scenario (functional requirement)**
*FR: "After a release, the embedding-worker pods crash-loop; ingestion has stopped and the assistant is answering from stale data."*

**What the interviewer is really checking**
A systematic, calm approach and rollback-first thinking.

**How I answer it**
1. **Mitigate first:** roll back (revert in Git/Argo or `kubectl rollout undo`) if the release is the obvious cause; investigate in parallel.
2. `kubectl describe pod`: last state, **exit code**, reason (OOMKilled?), events (probe failures, image pull errors, failed mounts).
3. `kubectl logs <pod> --previous`: the crashed container's logs. Typical: missing config property -> Spring fails at startup with `APPLICATION FAILED TO START`.
4. **Common causes:** missing Secret/ConfigMap key, wrong env, OOMKilled (limit too low), liveness probe killing a slow-starting app (needs a startup probe), DB unreachable at startup, wrong image architecture (arm64 vs amd64).
5. `kubectl debug -it <pod> --image=busybox --target=app` for an ephemeral debug container in distroless images.
6. Fix forward with a test that catches it (config validation, startup smoke test in CI).

**Trade-offs and what can go wrong**
- Deleting pods repeatedly doesn't fix anything and loses `--previous` logs.
- Debugging in prod before rolling back prolongs the outage.

**How I'd monitor it**
Alerts on restart counts and pods not ready, deployment health in Argo, ingestion lag alert (the user-facing symptom).

**Follow-ups to expect**
- *ImagePullBackOff?* -> Wrong tag, registry auth, or rate limits.
- *Pending pods?* -> Insufficient resources, node selectors/taints, PVC not bound: check events.
- *OOMKilled at startup?* -> Limits too low for JIT/class loading peaks; raise or tune heap.

**60-second answer**
"If the release is the obvious trigger I roll back first and debug in parallel. Then `kubectl describe` for the exit code, reason and events: 137 with OOMKilled is memory, probe failures point to liveness killing a slow start. `kubectl logs --previous` shows the crashed container's output, often a missing config key that stops Spring at startup. Ephemeral debug containers help with distroless images. Then I add a guard, config validation or a startup smoke test, so CI catches it next time."

### Q13 [architect] Do you need a service mesh? Explain sidecar vs ambient and what you get.
tags: service-mesh, istio, linkerd, mtls, ambient-mesh, traffic-management, profile-java-genai

**Start here: the concepts**
- **Service mesh:** a network layer providing mTLS, traffic control (retries, timeouts, canary splits), and telemetry without app code.
- **Sidecar model:** a proxy (Envoy, Linkerd2-proxy) beside each pod. **Ambient mode (Istio):** per-node L4 proxies (ztunnel) plus optional L7 waypoint proxies, no sidecars.

**The live scenario (functional requirement)**
*FR: "Security requires encryption and identity on every internal call; product wants percentage-based canaries for the AI assistant; 60 services in 4 languages."*

**What the interviewer is really checking**
Cost-benefit judgement on a mesh.

**How I answer it**
1. With 60 services in 4 languages, implementing mTLS, retries and telemetry in every library is costly and inconsistent; a mesh gives it uniformly.
2. **Gains:** automatic mTLS with workload identity and authorisation policies, traffic splitting for canaries, consistent golden metrics per service pair.
3. **Choice:** Linkerd for simplicity; Istio for rich features. **Ambient mode** reduces per-pod overhead and avoids sidecar lifecycle issues (startup ordering, Jobs that never finish).
4. Avoid double retries: if the mesh retries, app-level retries must be off for those calls (or vice versa).
5. If only 8 Java services: Spring + Resilience4j + OpenTelemetry may be enough; no mesh.

**Trade-offs and what can go wrong**
- Operational complexity, upgrade risk, extra latency (sub-ms to ~1 ms per hop) and memory per sidecar.
- Debugging moves into proxies; teams need the skills.

**How I'd monitor it**
Mesh control-plane health, mTLS coverage, proxy resource usage, policy denials.

**Follow-ups to expect**
- *Mesh vs API gateway?* -> Gateway for north-south (external) traffic; mesh for east-west (internal).
- *Kubernetes native sidecars?* -> Init containers with `restartPolicy: Always` fix sidecar start/stop ordering.
- *Can a mesh replace circuit breakers in code?* -> Partly (outlier detection), but fallbacks are business logic.

**60-second answer**
"With 60 services in four languages and a mandate for encryption and identity on every call, a mesh pays off: automatic mTLS and authorisation policies, percentage traffic splits for canaries, and consistent per-service metrics without library work in every language. I'd look at Istio ambient mode to avoid per-pod sidecars, or Linkerd for simplicity, and make sure retries happen in one layer only. For eight Java services I'd skip it and use Resilience4j and OpenTelemetry."

### Q14 [senior] Should you run Kafka, Postgres or a vector database on Kubernetes?
tags: statefulset, operators, strimzi, persistent-volumes, managed-services, stateful-workloads, profile-java-genai

**Start here: the concepts**
- **StatefulSet:** stable pod identity and per-pod persistent volumes, ordered rollout.
- **Operators:** controllers encoding operational knowledge (Strimzi for Kafka, CloudNativePG / Zalando for Postgres, operators for Milvus/Qdrant).
- **Managed alternatives:** MSK/Confluent, RDS/Aurora/Azure Database, managed vector search.

**The live scenario (functional requirement)**
*FR: "The platform team of 4 must provide Kafka, Postgres with pgvector, and a vector store for 3 product teams, with 99.9% availability and backups."*

**What the interviewer is really checking**
Pragmatism: ops capacity and failure modes, not "Kubernetes can run anything".

**How I answer it**
1. **Default to managed** for databases with a small platform team: backups, failover, patching and point-in-time recovery are solved.
2. **Run on Kubernetes when** there's a reason: cost at scale, portability/on-prem, or no managed option, and then **only with a mature operator** (Strimzi for Kafka, CloudNativePG for Postgres).
3. Storage: SSD storage classes, topology-aware volumes per zone, anti-affinity across zones, PDBs.
4. Backups tested by restores; disaster recovery runbooks.
5. Vector store: start with **pgvector in managed Postgres** (one less system); move to a dedicated vector DB only at scale or for features (billions of vectors, advanced filtering).

**Trade-offs and what can go wrong**
- Node failures, volume re-attachment delays and operator upgrades become your incidents.
- Managed services cost more per unit and limit tuning/versions.

**How I'd monitor it**
Replication lag, disk usage and IOPS, backup success and restore tests, broker/DB health.

**Follow-ups to expect**
- *Why StatefulSet for Kafka?* -> Brokers need stable ids and their own disks.
- *Local SSDs?* -> Fast but data lost with the node; only with replication.
- *Redis on k8s?* -> Common for caches; managed for durable use.

**60-second answer**
"With a four-person platform team I default to managed services for state, since backups, failover and patching are solved problems. I run stateful systems on Kubernetes only with a real reason, cost at scale, on-prem or portability, and only through mature operators like Strimzi or CloudNativePG, with zone anti-affinity, PDBs and restore-tested backups. For vectors I'd start with pgvector in managed Postgres and add a dedicated vector database only when scale or features demand it."

### Q15 [architect] Containerise and scale self-hosted LLM and embedding models on Kubernetes.
tags: gpu, llm-serving, vllm, ollama, kubernetes, model-serving, profile-java-genai

**Start here: the concepts**
- **Model servers:** vLLM, Hugging Face TGI, NVIDIA Triton, Ollama (simple, dev-friendly); most expose an **OpenAI-compatible API**, so Spring AI/LangChain4j clients work unchanged.
- **GPU scheduling:** NVIDIA device plugin/GPU operator, `nvidia.com/gpu` resource requests, GPU node pools with taints.
- **Throughput drivers:** continuous batching, KV cache memory, quantisation.

**The live scenario (functional requirement)**
*FR: "Data-residency rules mean customer documents can't leave our cloud account; serve an open-weight chat model and an embedding model for 300 concurrent users at p95 time-to-first-token under 1.5 s."*

**What the interviewer is really checking**
That you can treat models as containerised services with special scheduling and scaling.

**How I answer it**
1. **Serving:** vLLM container for the chat model (continuous batching), a lighter server (TEI or Triton) for embeddings; both behind Kubernetes Services with OpenAI-compatible endpoints.
2. **Images & weights:** don't bake 15 GB of weights into the image; pull from object storage/model registry into a cached volume (or a node-local cache) at startup; pin model versions.
3. **GPU node pool** with taints; pods request `nvidia.com/gpu: 1`; the GPU operator installs drivers.
4. **Scaling:** HPA/KEDA on **queue depth or running requests** (from vLLM metrics), not CPU; keep min replicas warm because cold start (weights loading) takes minutes.
5. **Capacity:** benchmark tokens/s per GPU for your prompt lengths; quantised models (e.g. 4-bit/8-bit) fit smaller GPUs at some quality cost.
6. **Gateway:** an AI gateway in front for auth, quotas, routing (self-hosted vs cloud fallback), and observability.
7. Java apps use Spring AI's OpenAI-compatible client with a different base URL: no code change.

**Trade-offs and what can go wrong**
- GPUs are expensive and scarce; low utilisation destroys the cost case versus APIs.
- Model quality of open-weight models may trail top hosted models; evaluate on your tasks.
- Long contexts blow up KV cache memory -> fewer concurrent requests.

**How I'd monitor it**
Time to first token, tokens/s, GPU utilisation and memory, queue length, request errors, cost per 1,000 requests.

**Follow-ups to expect**
- *Ollama in production?* -> Fine for small scale/dev; vLLM/TGI for high-concurrency serving.
- *Spot GPUs?* -> For batch embedding jobs, with checkpointing.
- *Multi-model on one GPU?* -> Possible with MIG partitioning or model multiplexing.

**60-second answer**
"I run models as services: vLLM for the chat model because continuous batching gives throughput, a lighter server for embeddings, both exposing OpenAI-compatible APIs so our Spring AI clients just change base URL. Weights come from a model registry into a cached volume, not baked into images. Pods request GPUs on a tainted node pool, and scaling is on queue depth from the server's metrics, with warm minimum replicas because loading weights takes minutes. An AI gateway handles auth, quotas and fallback, and I watch time-to-first-token and GPU utilisation."
