# Deep Dive 17 — Caching Mechanisms

> Runnable companions: [`07_caching_queues/01_cache_aside_pattern.py`](../07_caching_queues/01_cache_aside_pattern.py) ·
> [`02_cache_stampede_lock.py`](../07_caching_queues/02_cache_stampede_lock.py)
> Related deep dives: [Scaling](12_scaling_applications.md) · [Decorators](03_decorators.md) ·
> [Data structures](01_data_structures_collections.md) · [AI-first](20_ai_first_technologies.md)

## What interviewers are actually probing

Caching interviews test whether you understand the **consistency trade-off** you're buying
performance with. Anyone can `redis.get()`. What's assessed is: do you know the **strategies** and
when each applies, can you handle a **cache stampede**, do you have an **invalidation** story, and do
you know that a cache is a **new failure mode** as well as a speedup.

The stampede question is the one that separates people — it's the failure that takes down the
database at exactly the moment traffic is highest.

---

## Must-know points

- **Cache-aside** is the default: check cache → miss → load source → populate. Simple, and the source
  stays authoritative.
- **Cache stampede / thundering herd**: N concurrent requests miss simultaneously and all hit the
  database. Fix with a **distributed lock** or **stale-while-revalidate**.
- **Eviction**: `allkeys-lru` for a general cache, `allkeys-lfu` for skewed access, **never
  `noeviction` for a pure cache**.
- **Invalidation** patterns: TTL expiry, event-driven, write-through.
- **L1 (in-process) + L2 (Redis)** for extremely hot keys.
- **Always set a TTL.** A key with no expiry is a memory leak and a stale-data bug waiting to happen.

---

## Interview questions and full answers

### Q1. What are the main caching strategies?

| Strategy | How it works | Consistency | Use when |
|---|---|---|---|
| **Cache-aside (lazy)** | App checks cache; on miss loads the source and populates | Fresh on the populating read; stale until TTL | **Read-heavy, infrequent writes.** The default. |
| **Read-through** | The cache itself loads from the source on miss | Eventual after TTL | Library-managed caching; app code is unaware |
| **Write-through** | Write to cache **and** source synchronously | **Strong** | Read-heavy, and you can afford write latency |
| **Write-behind (write-back)** | Write to cache; flush to source asynchronously | Eventual — **data loss risk** | Very high write throughput, tolerant of lag |
| **Refresh-ahead** | Proactively refresh before the TTL expires | Near-real-time | Predictable access on a known hot set |

**Cache-aside is the default and the right first answer**, because:

- **The source stays authoritative.** If the cache is empty or down, the app still works — just
  slower. Write-through and write-behind make the cache part of the write path, so a cache outage
  becomes an application outage.
- **Only requested data is cached**, so you don't waste memory on cold keys.
- It's trivially simple to reason about.

Its costs: **every miss pays the full latency** (cache lookup **plus** DB query), the first request
after a deploy or eviction is always slow, and it's vulnerable to **stampede** (Q3).

**Write-behind deserves a specific warning:** if the cache node dies before the flush, **the writes
are gone**. It's only acceptable when the data is genuinely loss-tolerant (view counters, analytics
events) or when the buffer is itself durable.

**Refresh-ahead** is under-used and worth mentioning: a background job re-populates the top-N hot
keys before they expire, so users never experience a miss on the data they're most likely to want.

---

### Q2. Implement cache-aside with Redis in Python.

```python
import redis.asyncio as aioredis
import json
from datetime import timedelta

redis_client = aioredis.from_url("redis://redis:6379", decode_responses=True)

async def get_order(order_id: int) -> dict:
    cache_key = f"order:{order_id}"

    # 1. Try the cache
    try:
        cached = await redis_client.get(cache_key)
    except redis.RedisError:
        cached = None                       # cache DOWN -> degrade, don't fail
        metrics.increment("cache.error")

    if cached:
        metrics.increment("cache.hit", tags=["entity:order"])
        return json.loads(cached)

    # 2. Miss -> load from the source of truth
    metrics.increment("cache.miss", tags=["entity:order"])
    order = await db.fetch_order(order_id)
    if order is None:
        raise NotFoundError(f"Order {order_id}")

    # 3. Populate with a TTL (plus jitter — see below)
    ttl = 900 + random.randint(0, 120)
    try:
        await redis_client.setex(cache_key, ttl, json.dumps(order))
    except redis.RedisError:
        pass                                # failing to cache is not a request failure

    return order

async def update_order(order_id, data):
    order = await db.update_order(order_id, data)
    await redis_client.delete(f"order:{order_id}")    # INVALIDATE, don't update
    return order
```

**Five decisions worth explaining:**

1. **A Redis failure must not fail the request.** Wrap cache calls and fall through to the database.
   A cache is an optimisation; treating it as a hard dependency turns a performance feature into a
   new single point of failure. This is the most common production mistake.
2. **Always set a TTL.** No TTL means the key lives until eviction — a memory leak *and* a
   permanently-stale-data bug if an invalidation is ever missed. The TTL is your safety net for every
   invalidation bug you haven't found yet.
3. **TTL jitter.** If 10,000 keys are populated in the same second (after a deploy), they all expire
   in the same second and you get a synchronised stampede. Randomising ±10% spreads it out.
4. **Delete on write, don't update.** Updating the cache from the write path creates a race: two
   concurrent writers can interleave so the cache ends up holding the *older* value. Deleting means
   the next read repopulates from the source — always correct.
5. **Instrument hit and miss.** Hit rate is the metric that tells you whether the cache is earning
   its keep. Below ~80% for a read-heavy workload, question the key design or the TTL.

**Caching negative results** is the follow-up: if `order_id` doesn't exist, every request for it
hits the database. That's **cache penetration** — and it's an attack vector, since an attacker can
request random non-existent IDs to bypass your cache entirely. Cache the "not found" with a **short**
TTL (30–60 s), or use a Bloom filter to reject impossible IDs.

---

### Q3. How do you avoid cache stampede (thundering herd)?

**The problem:** a hot key expires. In the milliseconds before anyone repopulates it, **100
concurrent requests all miss** and all issue the same expensive database query simultaneously. The
database — which was comfortable serving one such query every 15 minutes — now gets 100 at once and
falls over. Worse, the requests that *would* have been cache hits now time out too.

This reliably happens at **peak traffic** (more concurrency, more simultaneous misses) and **after a
deploy** (empty cache).

**Solution 1 — a distributed lock (`SET NX`).** Only the first requester rebuilds; the rest wait
briefly and retry.

```python
import asyncio, json

async def get_with_lock(key, fetch_fn, ttl=300, lock_ttl=10, max_wait=5.0):
    cached = await redis_client.get(key)
    if cached:
        return json.loads(cached)

    lock_key = f"lock:{key}"
    # SET key value NX EX ttl -> atomic "acquire if not held"
    acquired = await redis_client.set(lock_key, "1", nx=True, ex=lock_ttl)

    if acquired:
        try:
            value = await fetch_fn()                    # only ONE request does this
            await redis_client.setex(key, ttl, json.dumps(value))
            return value
        finally:
            await redis_client.delete(lock_key)

    # Someone else is rebuilding — poll briefly for their result
    deadline = asyncio.get_running_loop().time() + max_wait
    while asyncio.get_running_loop().time() < deadline:
        await asyncio.sleep(0.05)
        cached = await redis_client.get(key)
        if cached:
            return json.loads(cached)

    return await fetch_fn()          # lock holder died or is slow -> fall back
```

**The details that make it correct:**

- **`nx=True, ex=lock_ttl` must be one atomic command.** A separate `SETNX` then `EXPIRE` can leave a
  permanent lock if the process dies between them — deadlocking that key forever.
- **`ex` on the lock is mandatory** for the same reason.
- **A bounded wait with a fallback.** If the lock holder crashes, waiters must not block forever.
- **The waiters still fall through to `fetch_fn`** after the deadline — a degraded outcome is better
  than a timeout.

**Solution 2 — stale-while-revalidate.** Serve the stale value **immediately** and refresh in the
background. No request ever waits.

```python
import time, asyncio, json

async def get_swr(key, fetch_fn, hard_ttl=600, soft_ttl=300):
    raw = await redis_client.get(key)
    if raw:
        entry = json.loads(raw)
        if time.time() > entry["soft_expires_at"]:
            # Stale but usable: trigger a background refresh, return the stale value NOW
            asyncio.create_task(_refresh(key, fetch_fn, hard_ttl, soft_ttl))
        return entry["data"]
    return await _refresh(key, fetch_fn, hard_ttl, soft_ttl)

async def _refresh(key, fetch_fn, hard_ttl, soft_ttl):
    data = await fetch_fn()
    await redis_client.setex(key, hard_ttl, json.dumps({
        "data": data,
        "soft_expires_at": time.time() + soft_ttl,
    }))
    return data
```

**The trade-off:** users may see data up to `soft_ttl` stale, but **latency is always cache-speed**
and the database sees exactly one refresh per key per interval. For catalogues, config and reference
data this is almost always the better choice. It's also what HTTP's `stale-while-revalidate` cache
directive does, so the same idea applies at the CDN layer (Q8).

**Solution 3 — probabilistic early expiration** (XFetch). Each read recomputes with probability
rising as the TTL approaches, so refreshes spread naturally with no locks and no stale reads:

```python
import random, math, time

def should_refresh(delta_ms, expiry_ts, beta=1.0):
    """delta_ms = how long the last recompute took."""
    return time.time() - delta_ms * beta * math.log(random.random()) >= expiry_ts
```

Elegant, lock-free, and worth naming — it shows you've read beyond the basics.

---

### Q4. What are Redis eviction policies and which do you choose?

When Redis hits `maxmemory`, `maxmemory-policy` decides what happens:

| Policy | Evicts | Use for |
|---|---|---|
| `noeviction` | Nothing — **writes return an error** | A datastore (never a pure cache) |
| **`allkeys-lru`** | Least-recently-used, any key | **General-purpose cache** |
| `volatile-lru` | LRU, **only keys with a TTL** | Mixed persistent + cached data in one instance |
| **`allkeys-lfu`** | Least-**frequently**-used | **Skewed access** — a few very hot keys |
| `volatile-lfu` | LFU among keys with a TTL | Mixed, skewed |
| `allkeys-random` | A random key | Uniform access; lowest CPU |
| `volatile-ttl` | Shortest remaining TTL first | When TTL encodes priority |

```
maxmemory 2gb
maxmemory-policy allkeys-lru
```

**Choosing:**

- **`allkeys-lru`** for a pure cache — the safe default. Recency is a good proxy for future use.
- **`allkeys-lfu`** when access is **heavily skewed**. LRU has a known weakness: a one-off scan (a
  batch job, a crawler) touches thousands of cold keys and **evicts your genuinely hot ones**, because
  they're now less *recently* used. LFU counts frequency and resists that. If you've been bitten by
  a nightly report job destroying your cache hit rate, LFU is the fix.
- **`volatile-*`** only when one instance holds both cached and persistent data — which is itself a
  design smell. **Separate instances** for cache and for durable data is better: different eviction
  policies, different persistence settings, different failure blast radius.
- **`noeviction`** for a pure cache is the classic misconfiguration: the cache fills, writes start
  failing, and you get errors instead of a graceful hit-rate decline.

**Also mention:** Redis's LRU and LFU are **approximate** — it samples `maxmemory-samples` keys
(default 5) and evicts the best candidate, rather than maintaining an exact ordering. That's a
deliberate speed/accuracy trade, and raising the sample count improves accuracy at some CPU cost.

---

### Q5. How do you implement function-level caching with decorators?

**In-process, single instance:**

```python
from functools import lru_cache, cached_property

@lru_cache(maxsize=512)
def get_exchange_rate(from_ccy: str, to_ccy: str) -> float:
    return fetch_from_api(from_ccy, to_ccy)

print(get_exchange_rate.cache_info())   # hits, misses, maxsize, currsize
get_exchange_rate.cache_clear()
```

See [Decorators Q8](03_decorators.md#q8-what-does-functoolslru_cache-do-and-what-are-the-caveats) for
the full caveat list — the headline ones being **no TTL**, **hashable arguments only**, **per-process
so it doesn't scale**, and **a memory leak on instance methods** because `self` is part of the key.

**Distributed, Redis-backed:**

```python
import functools, hashlib, json

def cache(ttl_secs=300, prefix="fn", key_fn=None):
    def deco(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            raw_key = (key_fn(*args, **kwargs) if key_fn
                       else f"{prefix}:{func.__module__}.{func.__qualname__}"
                            f":{args}:{sorted(kwargs.items())}")
            cache_key = f"{prefix}:{hashlib.sha256(raw_key.encode()).hexdigest()[:32]}"

            try:
                hit = await redis_client.get(cache_key)
                if hit:
                    return json.loads(hit)          # JSON, not pickle — see below
            except redis.RedisError:
                pass                                 # degrade to the real call

            result = await func(*args, **kwargs)

            try:
                await redis_client.setex(cache_key, ttl_secs, json.dumps(result))
            except redis.RedisError:
                pass
            return result
        return wrapper
    return deco

@cache(ttl_secs=600, prefix="catalog")
async def get_product_catalog(category: str): ...
```

**Three things this version gets right that naive ones don't:**

1. **JSON, not `pickle`.** `pickle.loads` on data from a shared store is **remote code execution** if
   anyone can write to Redis. Use JSON, or msgpack for speed. This is a genuine security issue and
   worth flagging unprompted.
2. **The key includes the module and qualified name**, so two functions called `get` in different
   modules don't collide.
3. **Cache failures degrade to a real call**, never to an error.

**The remaining weakness to name:** stringifying `args` is fragile — `f(1)` and `f(1.0)` produce
different keys for the same logical call, and an object argument produces a key containing its
memory address. A `key_fn` hook (above) is the escape hatch for anything non-trivial.

---

### Q6. What is cache invalidation and what are the common patterns?

Phil Karlton's line — "there are only two hard things in Computer Science: cache invalidation and
naming things" — is quoted so often that interviewers want to hear the *patterns*, not the joke.

**Pattern 1 — TTL expiry.** Simplest. Accept bounded staleness. Every cache should have this as a
floor, even with other invalidation, because **it's the backstop for every invalidation bug you
haven't found**.

**Pattern 2 — explicit delete on write.** Delete the key when the underlying data changes. Correct
for a single service owning its data; fails when *another* service writes to the same table.

**Pattern 3 — event-driven invalidation.** Publish a change event; every instance invalidates. This
is what you need with an L1 in-process cache, because you can't reach into other pods' memory.

```python
async def invalidate_product(product_id):
    await redis_client.delete(f"product:{product_id}")              # L2
    await redis_client.publish("cache:invalidate",                   # tell every instance
                               json.dumps({"key": f"product:{product_id}"}))

async def listen_invalidations(local_cache):
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("cache:invalidate")
    async for msg in pubsub.listen():
        if msg["type"] == "message":
            data = json.loads(msg["data"])
            local_cache.pop(data["key"], None)                       # clear L1
```

**The caveat:** Redis Pub/Sub is **fire-and-forget**. A pod that's restarting misses the message and
keeps stale data until its TTL. For stronger guarantees use a **Kafka topic** (durable, replayable)
or Redis Streams.

**Pattern 4 — write-through.** Update cache and source together. Strong consistency, at the cost of
write latency and a cache that's now on the critical write path.

**Pattern 5 — versioned keys.** Instead of deleting, **change the key**:

```python
version = await redis_client.incr("catalog:version")
key = f"catalog:v{version}:{category}"     # old keys are simply orphaned; TTL reaps them
```

No delete needed, no race, and it invalidates an entire logical group at once. Very useful for
"invalidate everything for this tenant" — otherwise you'd need `SCAN` with a pattern, which is slow
and must never be `KEYS` in production (`KEYS` blocks the whole server).

**The rule to state:** **prefer delete to update.** Two concurrent writers updating a cache can
interleave so the cache retains the older value. Deleting means the next read repopulates from the
source, which is always correct.

---

### Q7. What is a two-level (L1/L2) caching architecture?

- **L1** = in-process memory (`dict`, `cachetools.TTLCache`, `lru_cache`). **Microsecond** access.
  Limited to one instance, and each instance has its own copy.
- **L2** = shared Redis. **Millisecond** access (a network round trip). Shared by all instances.
- **L3** = the database.

```python
from cachetools import TTLCache
import json

l1 = TTLCache(maxsize=1000, ttl=30)      # SHORT ttl — this is the staleness budget

async def get_config(key):
    if key in l1:                         # L1 — no network at all
        return l1[key]

    val = await redis_client.get(key)     # L2 — one network hop
    if val:
        parsed = json.loads(val)
        l1[key] = parsed
        return parsed

    val = await db.fetch_config(key)      # L3 — the source of truth
    await redis_client.setex(key, 300, json.dumps(val))
    l1[key] = val
    return val
```

**When it's worth it:** an extremely hot key read thousands of times per second — feature flags,
configuration, a currency table, a permissions matrix. At 10,000 reads/sec, even a 1 ms Redis
round trip is 10 seconds of cumulative latency per second of traffic, plus 10,000 Redis operations.
L1 removes essentially all of it.

**The cost, and the whole reason to keep L1 TTLs short:** each instance has its **own** L1, so they
can disagree, and **you cannot invalidate another pod's memory directly**. Your options:

1. **A short L1 TTL** (10–60 s) that bounds the inconsistency window. Simplest and usually enough.
2. **Pub/sub invalidation** (Q6) to actively clear L1 across instances.
3. **Redis client-side caching** (RESP3 tracking) — Redis itself notifies clients when a key they've
   cached changes. Effectively L1 with server-driven invalidation, and worth naming as the modern
   answer.

**Don't add L1 by default.** It doubles your invalidation problem. Add it for a measured hot key, not
speculatively.

---

### Q8. What is CDN caching and how do you control it from a Python API?

A CDN caches responses at **edge locations** near users. For cacheable content it removes both the
network distance and your server load entirely — the cheapest request is the one that never reaches
you.

```python
from fastapi.responses import JSONResponse
import hashlib, json

@app.get("/products/{id}")
async def get_product(id: int):
    product = await svc.get(id)
    body = json.dumps(product)
    etag = hashlib.md5(body.encode()).hexdigest()

    response = JSONResponse(content=product)
    # public: any cache may store it. max-age: 5 min fresh.
    # stale-while-revalidate: serve stale for 60s more while refreshing in the background.
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=60"
    response.headers["ETag"] = etag
    return response
```

**The directives that matter:**

| Directive | Meaning |
|---|---|
| `public` | Any cache (CDN, proxy, browser) may store it |
| **`private`** | **Browser only** — never a shared cache. Use for per-user data |
| **`no-store`** | Never cache. **Use for anything sensitive** |
| `max-age=N` | Fresh for N seconds |
| `s-maxage=N` | Overrides `max-age` **for shared caches** — lets the CDN cache longer than the browser |
| `stale-while-revalidate=N` | Serve stale for N more seconds while refreshing |
| `must-revalidate` | Never serve stale, even on error |

**`ETag` enables conditional requests:** the client sends `If-None-Match: <etag>`, and if it matches
you return **304 Not Modified** with no body. Saves bandwidth even on a cache miss.

**Purging on update:**

```python
import boto3
from uuid import uuid4

cf = boto3.client("cloudfront")
cf.create_invalidation(
    DistributionId=DIST_ID,
    InvalidationBatch={"Paths": {"Quantity": 1, "Items": [f"/products/{id}"]},
                       "CallerReference": str(uuid4())},
)
```

**The warnings worth giving:**

1. **CDN invalidation is slow (minutes) and often metered.** Don't design around frequent purges —
   prefer **versioned URLs** (`/products/123?v=7` or a content hash in the path), which are
   invalidated *instantly* because the URL itself changes.
2. **Never `public`-cache authenticated responses.** A `Cache-Control: public` on a
   per-user endpoint means the CDN serves **one user's data to another**. This is a real and
   catastrophic bug class. Use `private` or `no-store`, and set `Vary: Authorization` if a response
   genuinely varies by user.
3. **`Vary` headers fragment the cache.** `Vary: Accept-Encoding` is fine; `Vary: User-Agent`
   effectively disables caching, because there are millions of distinct user agents.

---

## The caching hierarchy

Latency is why caching works, and having these numbers to hand is persuasive:

| Layer | Typical latency | Scope |
|---|---|---|
| CPU L1/L2 cache | ~1 ns | One core |
| **In-process (L1)** | **~100 ns** | One process |
| **Redis, same AZ (L2)** | **~0.5–1 ms** | All instances |
| Redis, cross-AZ | ~2–5 ms | All instances |
| **Database (indexed)** | **~1–10 ms** | Source of truth |
| Database (complex join/scan) | 50–5,000 ms | Source of truth |
| External API | 50–2,000 ms | — |
| **CDN edge** | **~10–50 ms to the user** | Global, pre-origin |

**The point to draw out:** Redis is ~1,000× slower than process memory but ~10–1,000× faster than a
complex query. So L2 gives a huge win over the database, and L1 gives a further large win over L2 —
but only if the key is hot enough to justify the added invalidation complexity.

---

## When NOT to cache

Worth volunteering, because it shows judgement:

- **Write-heavy data** — you invalidate more often than you read. Net loss plus added complexity.
- **Data that must be exactly current** — account balances at the moment of a transaction, inventory
  at checkout, anything with a legal or financial guarantee.
- **Already-fast queries.** Caching a 1 ms indexed primary-key lookup behind a 1 ms Redis call gains
  nothing and adds a failure mode.
- **Low-cardinality-miss data** — if the hit rate would be under ~50%, you've added latency to most
  requests (cache lookup + DB query) for a minority benefit.
- **As a substitute for fixing a query.** A cache in front of a query missing an index hides the
  problem until the cache is cold — and then you have an outage at the worst possible time. **Fix the
  query first, then decide whether you still need the cache.**

That last one is the most valuable thing to say in this section.

---

## Worked example — a production cache helper

Everything above in one reusable function.

```python
import asyncio, json, random, time, hashlib, logging
import redis.asyncio as aioredis

log = logging.getLogger(__name__)
redis_client = aioredis.from_url("redis://redis:6379", decode_responses=True)

async def cached_fetch(key, fetch_fn, *, ttl=300, soft_ttl=None,
                       lock_ttl=10, negative_ttl=60):
    """Cache-aside with stampede protection, SWR, negative caching and graceful degradation."""
    soft_ttl = soft_ttl or ttl // 2

    # --- L2 read; a cache failure must never fail the request ---
    try:
        raw = await redis_client.get(key)
    except Exception as e:
        log.warning("cache read failed for %s: %s", key, e)
        return await fetch_fn()                       # degrade straight to the source

    if raw:
        entry = json.loads(raw)
        if entry.get("missing"):
            return None                               # cached negative result
        if time.time() > entry["soft_at"]:
            asyncio.create_task(_rebuild(key, fetch_fn, ttl, soft_ttl))  # SWR
        return entry["data"]

    # --- miss: only one caller rebuilds ---
    if await redis_client.set(f"lock:{key}", "1", nx=True, ex=lock_ttl):
        try:
            return await _rebuild(key, fetch_fn, ttl, soft_ttl, negative_ttl)
        finally:
            await redis_client.delete(f"lock:{key}")

    # --- someone else is rebuilding: wait briefly for their result ---
    for _ in range(40):
        await asyncio.sleep(0.05)
        raw = await redis_client.get(key)
        if raw:
            entry = json.loads(raw)
            return None if entry.get("missing") else entry["data"]

    return await fetch_fn()                           # lock holder stalled -> fall back

async def _rebuild(key, fetch_fn, ttl, soft_ttl, negative_ttl=60):
    data = await fetch_fn()
    jittered = ttl + random.randint(0, ttl // 10)     # avoid synchronised expiry
    payload = ({"missing": True} if data is None
               else {"data": data, "soft_at": time.time() + soft_ttl})
    try:
        await redis_client.setex(key, negative_ttl if data is None else jittered,
                                 json.dumps(payload))
    except Exception as e:
        log.warning("cache write failed for %s: %s", key, e)
    return data
```

**The checklist this implements** — worth reciting as the summary of the whole topic:

- ✅ Cache-aside with the source authoritative
- ✅ Stampede protection via an atomic `SET NX EX` lock
- ✅ Stale-while-revalidate so reads never block on a rebuild
- ✅ Negative caching with a short TTL (prevents cache penetration)
- ✅ TTL jitter (prevents synchronised expiry)
- ✅ Graceful degradation on any cache failure
- ✅ A bounded wait with a fallback if the lock holder dies
- ✅ JSON rather than pickle (no RCE from a shared store)

---

## Hands-on drills

1. Implement plain cache-aside. Then fire 100 concurrent requests at a cold key while counting
   database calls. You should see ~100. Add the `SET NX` lock and confirm it drops to 1.
2. Populate 10,000 keys with an identical TTL in one loop. Watch them all expire together and count
   the database queries in that second. Add jitter and re-run.
3. Set `maxmemory 10mb` and `maxmemory-policy noeviction`. Fill it and watch writes start failing.
   Switch to `allkeys-lru`.
4. Build a hot key set, then run a scan over 100,000 cold keys. Measure the hit rate on the hot set
   under `allkeys-lru`, then under `allkeys-lfu`. Explain the difference.
5. Implement stale-while-revalidate and measure p99 latency around the soft-TTL boundary against the
   lock-based version.
6. Add an L1 `TTLCache` in front of Redis. Run two instances, update the underlying data, and observe
   how long each pod serves stale values. Then wire up pub/sub invalidation.
7. Write a `@cache` decorator with `pickle`, then write a "malicious" value into Redis directly and
   demonstrate the RCE. Switch to JSON.
8. Request 10,000 non-existent IDs and watch every one hit the database. Add negative caching.

---

## The 60-second spoken answer

> "I default to cache-aside: check the cache, on a miss load from the source and populate, with a TTL
> always set — the TTL is the backstop for every invalidation bug I haven't found. Crucially, a
> Redis failure must not fail the request; I wrap cache calls and fall through to the database,
> because treating the cache as a hard dependency turns an optimisation into a new single point of
> failure. The failure everyone asks about is the stampede: a hot key expires, a hundred concurrent
> requests all miss, and they all hit the database at once — which happens precisely at peak traffic
> and after every deploy. I fix that with an atomic `SET key val NX EX` lock so only one request
> rebuilds, or better, stale-while-revalidate so I serve the stale value immediately and refresh in
> the background, which means reads never block. I also add TTL jitter so ten thousand keys
> populated in the same second don't expire in the same second. For eviction it's `allkeys-lru`
> generally, but `allkeys-lfu` when access is skewed, because a nightly batch job scanning cold keys
> will evict your hot ones under LRU. On invalidation I prefer delete over update, since concurrent
> writers updating a cache can interleave and leave the older value. And I'd push back on caching as
> a first response to slowness — if a query is slow because it's missing an index, a cache just hides
> it until the cache goes cold, and then you have an outage."
