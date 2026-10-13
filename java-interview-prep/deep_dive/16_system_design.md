# System design for backend engineers: capacity, scaling, caching, zero downtime

> **Runnable:** [`01_capacity_littles_law_100_to_600_tps.java`](../examples/16_system_design/01_capacity_littles_law_100_to_600_tps.java) ·
> [`02_cache_aside_stampede_and_invalidation.java`](../examples/16_system_design/02_cache_aside_stampede_and_invalidation.java)
> **Crib sheet:** [`topics/15-distributed-systems-system-design.md`](../topics/15-distributed-systems-system-design.md) · **Guide:** Q90, Q93–Q95

## What interviewers are actually probing

Structured thinking with **numbers**. "How would you scale from 100 TPS to 600 TPS?" is answered with a method: measure, find the bottleneck tier,
apply the cheapest lever, protect dependencies, and prove it with a load test — not "add more servers". Also: caching correctness,
availability trade-offs, zero-downtime change.

## Must-know points

- **Little's law**: in-flight requests = throughput × latency. It sizes pools and connection limits.
- **Utilisation cliff**: response time ≈ service time ÷ (1 − utilisation). Run at 50–70% peak.
- Scale the **bottleneck**, not the tier you like; usually the database or a partner API.
- Levers in order of cost: query/index fixes → caching → batching → async/queues → read replicas → horizontal scale → sharding.
- Cache pitfalls: stampede, penetration, avalanche, stale data. **Bound** every cache.
- Zero downtime = backward-compatible changes + rolling/canary + readiness-gated traffic + graceful shutdown + a rollback path.

## Interview questions and full answers

### Q1. How would you scale a service from 100 TPS to 600 TPS?

1. **Baseline**: p50/p95/p99, error rate, CPU, DB pool/wait, queue depth at 100 TPS.
2. **Capacity model** (example 16/01): per-instance sustainable TPS at target latency from a load test, 65% target utilisation → 600 / (90 × 0.65) ≈ 11 instances, +1 for N+1.
3. **Load test to 1.5× target**; find the first thing that breaks — often the primary DB writes or a partner rate limit, not CPU.
4. **Fix the bottleneck** with the cheapest lever (index/query, cache 80% reads at 90% hit → DB sees ~28% of traffic, batch writes, async via queue, replicas).
5. **Protect**: timeouts, circuit breakers, bulkheads, rate limiting, load shedding.
6. **Autoscale** on RPS-per-pod/queue depth with warm-up in mind; multiple AZs.
7. **Verify** with canary + SLO dashboards; rehearse a node/AZ failure.

### Q2. What does Little's law tell you in practice?

`L = λ × W`. At 600 TPS and 120 ms latency you need ~72 requests in flight across the fleet — so if each instance has 10 worker threads and 10 DB connections, the pool arithmetic must work *per instance*.
When a dependency slows from 50 ms to 5 s the same law predicts the pool saturates at 2 req/s (example 11/01 section 3). It also converts "queue depth" and "latency" into each other for capacity planning.

### Q3. Why does latency explode near 100% utilisation?

Queueing: even random arrivals create bursts; at 90% utilisation the mean wait is 10× the service time, at 99% it's 100× (M/M/1: `W = S / (1 − ρ)`, example 16/01 section 2). So "the CPU is only at 85%" is already an incident for latency-sensitive services; autoscale before the cliff and leave headroom for deploys/failures.

### Q4. Design a cache strategy and say what goes wrong.

**Cache-aside** (app reads cache → DB on miss → populates). Choose key, TTL (+ jitter), max size/eviction, and invalidation (TTL only; delete on write; or event-driven from the change stream).
Failures: **stampede** (a hot key expires and N requests hit the DB — use single-flight/`@Cacheable(sync=true)`/Caffeine `LoadingCache`, or refresh-ahead), **penetration** (missing keys bypass the cache — negative caching/Bloom filter), **avalanche** (same TTL — jitter), **stale reads** after a write race (delete after commit, short TTL for critical data), memory blow-up (always bound).
Example 16/02: 50 concurrent misses → 50 DB calls vs 1 with single-flight.

### Q5. Local cache vs distributed cache?

Local (Caffeine): nanosecond access, no network, but per-node copies diverge and are invalidated independently. Distributed (Redis/Couchbase): shared, consistent view and bigger capacity, adds a network hop and an availability dependency (design a fallback to the DB or a local near-cache).
Common: two tiers, local with short TTL in front of Redis.

### Q6. How do you achieve zero downtime when fixing an issue in a distributed production system?

Make the change **backward compatible** (expand → migrate → contract for schemas and APIs), use **feature flags**, roll out via **rolling/blue-green/canary** with readiness probes gating traffic, graceful shutdown (drain connections, finish in-flight, commit Kafka offsets, then stop), connection draining at the load balancer, and keep a **fast rollback** (previous image/flag off).
Watch SLO metrics during the canary and halt automatically on regressions. For data: dual-write/shadow-read before cutting over; Kafka consumers must handle both event versions.

### Q7. Active-passive vs active-active, RTO and RPO?

RPO = tolerable data loss, RTO = tolerable downtime. Active-passive: cheaper, failover takes time and may lose recent async-replicated data. Active-active: lowest RTO but requires conflict handling and region-affine data (CRDTs/LWW/partitioning). Choose from the business RPO/RTO numbers and rehearse failover — an untested DR plan is a hypothesis.

### Q8. How do you protect a service from overload?

Admission control: rate limits per client (token bucket), concurrency limits (semaphore/bulkhead), **load shedding** (reject early with 429/503 + `Retry-After` when queue/latency exceeds a threshold), bounded queues, back-pressure to producers, priorities (shed low-priority first), and autoscaling for the sustained part. Rejecting 10% quickly beats timing out 100% slowly.

### Q9. SQL vs NoSQL, read replicas, sharding — what do you pick for a write-heavy workload?

First fix batching/indexes/connection use. Then partition by a good key: **sharding** (application- or proxy-level, or a natively distributed store like Cassandra) when a single primary can't absorb writes; replicas only help reads. Pay for cross-shard queries and rebalancing; choose a key that spreads load and aligns with the dominant access pattern.

### Q10. How would you design an idempotent, resilient order-processing pipeline?

API accepts with an idempotency key → writes order + outbox in one transaction → Kafka (`orderId` key) → workers (idempotent, bounded retries, DLT) → state machine in the DB → notifications; reconciliation job for stuck orders; dashboards on lag, DLT depth, order-state counts.
(Chapters 11 and 12 give the pieces.)

### Q11. What are the CAP/consistency choices in a typical design?

Money movement: strong consistency (single-primary relational, sagas). Product catalogue/search: eventual (replicated, cached). Counters/analytics: eventual and approximate (HyperLogLog, async aggregation).
State the consistency requirement **per data type**; don't apply one rule to the whole system.

### Q12. How do you estimate storage and bandwidth quickly?

Per-record bytes × records/day × retention × replication, plus indexes (~+30–100%). Example: 10k msg/s × 1 KB = 10 MB/s → ~864 GB/day raw → × RF 3 = ~2.6 TB/day on disk (example 12/04 section 6). Round up, state assumptions, and say what you'd measure.

## A worked example

Run [`01_capacity_littles_law_100_to_600_tps.java`](../examples/16_system_design/01_capacity_littles_law_100_to_600_tps.java) and read it as a script for the 100 → 600 question: the sections are exactly the order of your answer.
Run [`02_cache_aside_stampede_and_invalidation.java`](../examples/16_system_design/02_cache_aside_stampede_and_invalidation.java) and quote "50 DB calls → 1" for stampede protection.

## Hands-on drills

1. Take any API you built and compute per-instance TPS from a quick JMeter/k6 run, then derive instance count for 3× growth.
2. Draw the dependency graph and mark each tier's saturation limit with a number.
3. Add a token-bucket rate limiter and demonstrate 429 under a burst while latency of admitted requests stays flat.
4. Write a zero-downtime plan for renaming a DB column used by two services.
5. Compare local+Redis two-tier caching with Redis-only for a 95% read workload.

## The 60-second spoken answer

"I'd baseline first, then model capacity with Little's law and a target utilisation near 65%, load-test to find the real bottleneck — usually the database or a
partner limit — and apply the cheapest lever: indexes and queries, caching with stampede protection, batching, async queues, then replicas or sharding.
I protect dependencies with timeouts, circuit breakers and rate limiting, autoscale on a leading signal across availability zones, and verify with a canary and SLO
dashboards. For zero downtime I keep changes backward compatible, gate traffic with readiness, drain gracefully and keep a quick rollback."
