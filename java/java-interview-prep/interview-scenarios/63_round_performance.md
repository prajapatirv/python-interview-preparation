---
id: round-performance
title: Real interview round: scaling a service when traffic grows 100x
stack: java
skill: performance
---
A question asked in a real interview round, answered from the basics.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [architect] What happens if TPS increases from 1,000 to 100,000? What approach do you take to fix it, and what measures do you check?
tags: scaling, tps, capacity-planning, bottleneck, load-testing, horizontal-scaling, caching, async, database, basics

**Start here: the concepts**
- **TPS (transactions per second):** how many requests the system completes each second.
- **Bottleneck:** the first resource that saturates as load rises, and therefore sets the maximum throughput.
- **Vertical scaling:** a bigger machine. **Horizontal scaling:** more machines behind a load balancer.
- **Stateless service:** keeps no per-user data in memory between requests, so any instance can serve any request and you can add instances freely.
- **Little's Law:** requests in flight = throughput x latency. At 100,000 TPS and 50 ms latency you hold about 5,000 requests in flight at any moment.
- **Back-pressure and load shedding:** deliberately slowing or rejecting some work so the system stays healthy under overload.
- **Queueing:** near saturation waiting time dominates, so latency climbs steeply.

**The live scenario**
A ticketing platform runs comfortably at 1,000 TPS on 4 instances with one primary database. A viral on-sale pushes traffic to 20,000 TPS in minutes. The load balancer adds instances, but the database CPU hits 100%, connection pools empty, latency goes from 80 ms to 12 seconds, retries from clients multiply the load, and the site collapses. A 100x target (100,000 TPS) cannot be reached by turning a few dials; the architecture has to change in several places, and the team has to know in advance which one breaks first.

**What the interviewer is really checking**
That you treat 100x as a capacity and architecture problem, not a configuration tweak: you quantify, find the bottleneck with evidence, remove it layer by layer, and prove it with load tests.

**How I answer it**
1. **Quantify first.** What is the real target: sustained or peak? Which operations (reads vs writes)? Latency SLO and error budget? From Little's Law: 100,000 TPS x 50 ms = 5,000 concurrent requests. If one instance handles 1,000 TPS, I need at least 100 instances plus headroom, so a 100x change is horizontal scale plus removal of every shared bottleneck.
2. **What breaks, in order of likelihood:** a single database (CPU, connections, locks), connection and thread pools, a shared cache or session store, synchronous calls to slow dependencies, one hot key or partition, the load balancer or network, and logging volume.
3. **Make the service horizontally scalable.** Stateless instances, externalised sessions, autoscaling on a leading signal (CPU, concurrency or queue lag), and enough pods and nodes pre-warmed for a spike.
4. **Cut the work per request.**
   - cache reads at the edge (CDN), in a shared cache (Redis) and locally (Caffeine) with sensible TTLs and stampede protection;
   - batch and compress; avoid N+1 queries; reduce payloads.
5. **Move work off the request path.** Return `202 Accepted` and process asynchronously through Kafka or a queue; use the outbox pattern so writes and events stay consistent.
6. **Scale the data layer.** Read replicas for reads, partitioning or sharding for writes, appropriate indexes, CQRS with a read model for heavy queries, and connection pooling sized to what the database can actually run.
7. **Protect the system.** Rate limiting per client, back-pressure, load shedding of non-critical features, timeouts, circuit breakers and bulkheads so one slow dependency cannot take everything down; retries with backoff and jitter to avoid retry storms.
8. **Prove it, step by step.** Load-test at 2x, 5x, 10x, then the target, using an open arrival-rate model; at each step find the first saturating resource, fix it, and repeat. Use production-like data volume.
9. **Release and operate.** Capacity reviews before known peaks, runbooks, dashboards, and a game day with failure injection.

**Measures I check (golden signals plus saturation)**
- **Latency:** p50, p95, p99 per endpoint.
- **Traffic:** TPS and its mix.
- **Errors:** 5xx, timeouts, rejected requests.
- **Saturation:** CPU, memory and GC, thread-pool and connection-pool use and queue depth, database CPU/IO/locks/replication lag, cache hit ratio, Kafka lag, network bandwidth.
- **Cost and autoscaling:** time for new instances to become ready.

**Trade-offs and what can go wrong**
- Horizontal scale moves the bottleneck to the database or cache; scaling only the app tier is a common failure.
- Caching adds staleness and invalidation complexity; async processing adds eventual consistency and idempotency needs.
- Sharding is hard to undo; do it when measurements prove it is needed.
- Autoscaling that reacts too slowly cannot absorb a sudden spike; pre-scale for known events.
- Cost grows with capacity; right-size after the peak.

**How I'd monitor it**
SLO burn-rate alerts on latency and errors, saturation dashboards for each shared resource, and a per-release performance comparison against the baseline.

**Follow-ups to expect**
- *Where do you start if you have one day?* -> measure the current limit with a load test, find the first bottleneck, and fix cheap items such as caching and pool sizing while planning the structural changes.
- *Is it only the app servers?* -> almost never; the shared database or cache usually fails first.
- *Reads vs writes?* -> reads scale with caches and replicas; writes need partitioning, batching or async processing.
- *What if the spike is short?* -> queue and shed load instead of building full capacity.

**60-second answer**
At 100x I treat it as capacity planning, not tuning. I turn TPS and latency into concurrency with Little's Law, load-test to find the first saturating resource, and remove bottlenecks layer by layer: stateless horizontally scaled services with autoscaling, caching to cut work, asynchronous processing through Kafka for non-critical work, and a scaled data tier with replicas and partitioning. I add rate limiting, timeouts and circuit breakers so overload degrades gracefully, and I validate with staged load tests watching p95/p99, errors, CPU, pool usage, database load and queue lag.
