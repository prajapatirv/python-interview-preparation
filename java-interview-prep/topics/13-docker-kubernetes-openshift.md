---
id: 13-k8s-openshift
title: Docker, Kubernetes & OpenShift for Java Services
focus: Weak-ish area (K8s 4/10, OpenShift none) - core objects, deployment, troubleshooting, OpenShift differences
---

### Q1 [basic] Container vs VM? What is a Docker image vs container?
A container shares the host kernel and isolates processes with namespaces/cgroups: lighter and faster to start than a VM. Image = immutable layered template; container = running instance of an image.

### Q2 [basic] How do you write a good Dockerfile for a Spring Boot app?
Multi-stage or layered jar, small JRE base image (distroless/Temurin JRE), **non-root user**, copy dependencies layer before app layer for caching, set `JAVA_TOOL_OPTIONS`/`MaxRAMPercentage`, a `HEALTHCHECK` or K8s probes, no secrets in layers. Or skip the Dockerfile: `./mvnw spring-boot:build-image` (Buildpacks) / Jib.

### Q3 [basic] Name the main Kubernetes objects.
Pod (smallest unit, 1+ containers), Deployment (replicas + rolling updates via ReplicaSet), Service (stable virtual IP/DNS), Ingress/Gateway API (HTTP routing), ConfigMap/Secret, Namespace, StatefulSet (stable identity/storage), DaemonSet, Job/CronJob, PersistentVolume(Claim), HPA, Node.

### Q4 [intermediate] Explain liveness, readiness and startup probes.
Liveness failing -> kubelet **restarts** the container. Readiness failing -> pod is removed from Service endpoints (no restart). Startup probe gives slow-starting apps time before liveness starts. With Spring Boot: `management.endpoint.health.probes.enabled=true` -> `/actuator/health/liveness` and `/readiness`. Don't make liveness depend on the database - a DB blip would restart every pod.

### Q5 [intermediate] Requests vs limits and how they affect scheduling and OOM?
`requests` = what the scheduler reserves (affects placement); `limits` = hard cap. CPU over the limit is throttled; memory over the limit gets **OOMKilled**. Set memory request = limit for Java (predictable), CPU limit carefully (throttling hurts latency); align JVM `MaxRAMPercentage` with the limit.

### Q6 [intermediate] How does a rolling update work and how do you roll back?
The Deployment creates new pods gradually (`maxSurge`, `maxUnavailable`), waiting for readiness before removing old ones. Roll back with `kubectl rollout undo deployment/orders` (history via `rollout history`). For stronger control use canary/blue-green (Argo Rollouts, Flagger, service mesh).

### Q7 [intermediate] How do you scale in Kubernetes?
HPA scales replicas on CPU/memory or custom metrics (RPS, queue lag via KEDA); VPA adjusts requests; Cluster Autoscaler/Karpenter adds nodes. Kafka consumers: scale by lag with KEDA but never beyond partitions. Ensure pods are stateless and start quickly.

### Q8 [intermediate] ConfigMap vs Secret, and how do you manage secrets safely?
ConfigMap: non-sensitive config; Secret: base64-encoded (NOT encrypted by default) sensitive data. Enable encryption at rest, restrict RBAC, prefer external secret managers (External Secrets Operator, CSI driver for Vault/AWS/Azure Key Vault), mount as files or env vars, rotate regularly.

### Q9 [intermediate] How do pods communicate and how is traffic exposed?
Pods get cluster IPs; a `Service` (ClusterIP) gives a stable name and load-balances across ready pods; `NodePort`/`LoadBalancer` expose externally; **Ingress** (or Gateway API) provides L7 routing/TLS. NetworkPolicies restrict pod-to-pod traffic (default allow-all otherwise).

### Q10 [intermediate] A pod is in CrashLoopBackOff. How do you debug?
`kubectl describe pod` (events, last state/exit code), `kubectl logs <pod> --previous`, check exit code 137 (OOMKilled/SIGKILL), 1 (app error), probe failures, missing config/secret, wrong image/command. `kubectl get events --sort-by=.lastTimestamp`; `kubectl exec`/ephemeral `kubectl debug` for a shell. Fix the root cause rather than raising the limits blindly.

### Q11 [intermediate] Pod stuck in Pending / ImagePullBackOff?
Pending: insufficient CPU/memory on nodes, unsatisfied node selector/affinity/taints, unbound PVC - read `describe` events. ImagePullBackOff: wrong tag, private registry without `imagePullSecret`, no network to the registry.

### Q12 [intermediate] What are Helm and Kustomize?
Helm = package manager with templated charts and values per environment (releases, rollback). Kustomize = patch-based overlays on plain YAML (no templating). GitOps (Argo CD/Flux) applies the desired state from Git and continuously reconciles drift.

### Q13 [advanced] What is a StatefulSet and when do you avoid running databases in K8s?
StatefulSet gives stable pod names, ordered rollout and per-pod persistent volumes - used for Kafka, Cassandra, databases. Operating stateful systems yourself is hard (backups, upgrades, failover); prefer managed services (RDS, MSK, Cosmos) unless you have an operator and the skills.

### Q14 [advanced] Pod disruption, anti-affinity and topology spread - why?
To survive node/zone loss and maintenance: `podAntiAffinity` or `topologySpreadConstraints` spread replicas across nodes/zones; `PodDisruptionBudget` keeps a minimum number available during voluntary disruptions (node drain); `preStop` hook + graceful termination avoid dropped requests.

### Q15 [advanced] RBAC and security best practices in Kubernetes?
Namespaces per team/env, least-privilege Roles/ServiceAccounts, no `cluster-admin` for apps, Pod Security Standards (non-root, read-only root filesystem, drop capabilities), NetworkPolicies, image scanning and signing, admission policies (Kyverno/OPA Gatekeeper), secrets management, and audit logs.

### Q16 [basic] What is OpenShift and how does it differ from Kubernetes?
OpenShift = Red Hat's enterprise Kubernetes distribution with batteries included: built-in image registry and build tooling (S2I, BuildConfigs), **Routes** (HAProxy-based, predate Ingress), **Projects** (namespaces + extra metadata), integrated CI/CD (OpenShift Pipelines = Tekton, GitOps = Argo CD), an operator catalogue (OperatorHub), a web console, and stricter default security. Same core API: your Kubernetes skills transfer.

### Q17 [intermediate] OpenShift security difference to know: SCCs and non-root.
OpenShift runs containers with an **arbitrary non-root UID** by default under **Security Context Constraints (SCC)** (default `restricted`). Images that need root or fixed UID fail - build images to run as non-root and with group-0 writable directories. This is the #1 migration problem from plain Docker/K8s.

### Q18 [intermediate] Route vs Ingress; DeploymentConfig vs Deployment; `oc` basics?
Routes expose services (edge/passthrough/re-encrypt TLS, weighted routes for canary). DeploymentConfig is legacy - use standard Deployments. `oc login`, `oc project`, `oc get pods`, `oc logs`, `oc rsh`, `oc new-app`, `oc rollout` mirror `kubectl`.

### Q19 [design] Design the deployment of 10 Spring Boot services on Kubernetes/OpenShift.
Namespace per environment, Helm/Kustomize per service, Deployments with 3 replicas across zones, HPA + PDB, readiness/liveness/startup probes, resource requests/limits tuned from load tests, Ingress/Route + TLS at the edge, ConfigMaps/Secrets from a vault, centralised logging and Prometheus metrics, GitOps pipeline with canary and automated rollback, NetworkPolicies and non-root images.

### Q20 [intermediate] Honest answer on OpenShift.
"I've worked with Kubernetes - deployments, services, probes, config, troubleshooting. I haven't operated OpenShift directly. I know it's Kubernetes plus Routes, SCC-based security, Operators and integrated CI/CD, so the main adjustments are building non-root images and using `oc`/Routes. I'd be productive quickly."

### Q21 [design] Design a safe rollout and rollback strategy for a risky release on Kubernetes.
Use readiness/liveness/startup probes and `maxUnavailable: 0` rolling updates for routine releases; for risky ones use canary (Argo Rollouts or a service-mesh traffic split) with automatic analysis on error rate and p95, then promote. Keep database changes backward compatible (expand/contract) so rollback is just redeploying the previous image. Add PodDisruptionBudgets and keep the previous ReplicaSet. Failure mode: a probe that passes before the app can really serve, sending traffic to cold pods.

### Q22 [design] Design multi-tenant isolation on a shared Kubernetes/OpenShift cluster for several teams.
One namespace (project) per team/environment with `ResourceQuota` and `LimitRange`, RBAC scoped to namespaces, `NetworkPolicy` default-deny, Pod Security Standards (OpenShift: SCCs), separate node pools for noisy or sensitive workloads, and per-team image registries with scanning. Trade-off: namespaces are a soft boundary - stronger isolation (regulated data) needs separate clusters. Failure mode: one team without limits starving the node and evicting neighbours.
