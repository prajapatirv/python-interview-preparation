# 07 — Caching & Queues

All examples run with pure stdlib (a dict-based `FakeRedis` stands in for the real thing) so you
can see every pattern without any infra. `01_cache_aside_pattern.py` also shows the two-line diff
to switch to real Redis if you have `pip install redis` and a local server.

## Crib sheet

- **Cache-aside (lazy loading)**: app checks cache → miss → load from source → populate cache.
  Simple, strong consistency on the read that populates it. The default choice for read-heavy,
  infrequent-write workloads.
- **Write-through**: write to cache AND source synchronously. Strong consistency always, at the
  cost of write latency.
- **Cache stampede** (a.k.a. thundering herd): many concurrent requests miss the cache at the
  same instant and all hit the source simultaneously. Fix with a **distributed lock**
  (`SET key val NX EX ttl` — only one requester rebuilds, others wait briefly and retry) or
  **stale-while-revalidate** (serve the expired value immediately, refresh in the background).
- **Eviction policies**: `allkeys-lru` (general cache), `allkeys-lfu` (skewed/hot-key access),
  `volatile-lru` (mixed persistent + cached data in one store), `noeviction` (never for a pure
  cache — that's for a database).
- **Message queue vs. broker**: a queue (SQS, RabbitMQ) is point-to-point — one producer, one
  consumer group, message deleted after ack. A broker (Kafka) is pub/sub with retention/replay.
  Use a queue for task offloading; a broker for event streaming and fan-out.
- **Fan-out (SNS→SQS style)**: one event delivered to N independent queues, each with its own
  consumer, visibility timeout, and DLQ — adding a new consumer never touches the producer.
- **DLQ**: after `maxReceiveCount` failed attempts, a message moves to a dead-letter queue instead
  of blocking the main queue forever. Monitor DLQ depth; alert on non-zero.

## Files

| File | Topic |
|---|---|
| `01_cache_aside_pattern.py` | cache-aside with hit/miss metrics, TTL, invalidation on write |
| `02_cache_stampede_lock.py` | reproduce the stampede, then fix it with a `SET NX` style lock |
| `03_queue_patterns.py` | bounded `queue.Queue` producer/consumer, visibility-timeout retry, DLQ |

## Exercise

Extend `01_cache_aside_pattern.py`'s `FakeRedis` with an `allkeys-lru` eviction policy (a
`maxsize`, evicting the least-recently-*accessed* key on overflow — reuse the `OrderedDict` LRU
from `01_python_core/01_data_structures.py`). Then write a small load test that proves eviction
kicks in at the right size.

> **Deep dives**: [17 — Caching mechanisms](../deep_dive/17_caching.md) (stampede, eviction,
> L1/L2, invalidation, CDN) · [18 — Queue-based architectures](../deep_dive/18_queue_architectures.md)
> (SQS/SNS/Kafka selection, fan-out, DLQ, outbox, CQRS).
