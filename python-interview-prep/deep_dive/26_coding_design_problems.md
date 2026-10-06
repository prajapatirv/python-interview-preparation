# Deep Dive 26 — Three Design-Coding Problems: Retry Decorator, Nested-Dict Search, LRU Cache

> Runnable companions: [`11_coding_challenges/05_retry_decorator.py`](../11_coding_challenges/05_retry_decorator.py) ·
> [`11_coding_challenges/06_nested_dict_search.py`](../11_coding_challenges/06_nested_dict_search.py) ·
> [`11_coding_challenges/03_lru_cache.py`](../11_coding_challenges/03_lru_cache.py)
> Related deep dives: [03 — Decorators](03_decorators.md) · [01 — Data structures](01_data_structures_collections.md) ·
> [12 — Scaling applications](12_scaling_applications.md) · [17 — Caching](17_caching.md) ·
> [25 — Nested exception handling](25_nested_exception_handling.md)

## What interviewers are actually probing

These three are **design** questions disguised as coding questions. Each one has a 10-line answer
that "works" and a 40-line answer that gets the offer, and the difference is never cleverness — it's
the production concerns:

| Problem | The naive answer | What they're actually checking |
|---|---|---|
| Retry decorator | a `for` loop with `time.sleep(1)` | jitter, which errors to retry, a time budget, **testability without sleeping** |
| Nested-dict search | one recursive function | the clarifying questions, returning the **path**, recursion limits, "now do it a million times" |
| LRU cache | `OrderedDict` | O(1) justification, the doubly-linked-list version, thread safety, TTL, and **distributed** invalidation |

The pattern for all three: **ask the clarifying questions first, write the simple correct version,
then name the upgrades and let the interviewer pick one.** Candidates who jump straight to code lose
marks they can't recover, because the clarifying questions *are* part of the answer.

---

## Problem 1 — A retry decorator with a retry limit and exponential backoff

### The requirement, fully stated

> *"Design a decorator `@retry` that retries a function with a retry limit and exponential backoff."*

Say the eight requirements out loud before writing anything:

1. A decorator **that takes arguments** → three nesting levels (factory → decorator → wrapper).
2. **Exponential backoff**: `delay = base × factor^(attempt−1)`, capped at `max_delay`.
3. **Jitter**, so N failing clients don't retry in the same instant.
4. **Retry only what's worth retrying**; everything else propagates immediately.
5. **Re-raise the last error** after the final attempt — never return `None` silently.
6. **`functools.wraps`**, so the decorated function keeps its name, docstring and signature.
7. **An injectable `sleep`**, so tests are instant and deterministic.
8. A **total time budget**, an `on_retry` callback, and an **async** variant.

Point 7 is the one most candidates miss and the one that makes it production code: *a retry decorator
you can't unit-test deterministically is a retry decorator nobody trusts.*

### The implementation

```python
import functools, random, time

class TransientError(Exception): """Worth retrying: timeout, 503, connection reset, DB deadlock."""
class PermanentError(Exception): """Never worth retrying: 400, validation failure, bad schema."""


def backoff_delay(attempt, base_delay=0.1, factor=2.0, max_delay=10.0,
                  jitter="full", rng=random.random):
    """Pulled OUT as a pure function: it's the part with arithmetic, so it's the part worth
    testing directly, and it's where the jitter strategies live."""
    delay = min(base_delay * (factor ** (attempt - 1)), max_delay)
    if jitter == "none":  return delay
    if jitter == "full":  return rng() * delay                      # AWS's recommended default
    if jitter == "equal": return delay / 2 + rng() * (delay / 2)     # keeps a minimum wait
    raise ValueError(f"unknown jitter strategy: {jitter!r}")


def retry(max_attempts=3, base_delay=0.1, factor=2.0, max_delay=10.0, jitter="full",
          retry_on=(TransientError,), give_up_on=(), total_budget=None,
          on_retry=None, sleep=time.sleep, rng=random.random):
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(fn):
        @functools.wraps(fn)                      # keeps __name__, __doc__, __wrapped__
        def wrapper(*args, **kwargs):
            started = time.monotonic()            # monotonic, not time(): immune to clock changes
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except give_up_on:                # listed FIRST so it beats a broader retry_on
                    raise
                except retry_on as exc:
                    if attempt == max_attempts:
                        raise                     # bare raise: original traceback preserved
                    delay = backoff_delay(attempt, base_delay, factor, max_delay, jitter, rng)
                    if total_budget is not None and \
                            time.monotonic() - started + delay > total_budget:
                        raise                     # the caller's SLA is spent; stop now
                    if on_retry is not None:
                        on_retry(attempt, exc, delay)
                    sleep(delay)
            raise AssertionError("unreachable")   # the loop always returns or raises
        return wrapper
    return decorator
```

### Why each decision

**Three nesting levels.** `@retry(max_attempts=4)` is a *call*, so it must return the decorator. The
levels are: `retry(...)` captures the config → `decorator(fn)` captures the function →
`wrapper(*args)` runs per call. See [03 — Decorators](03_decorators.md).

**`functools.wraps`.** Without it the wrapper's `__name__` is `"wrapper"` for every decorated
function, which breaks logging, breaks Flask/FastAPI route registration (they key on `__name__`),
breaks `pytest` test discovery, and makes stack traces useless. It also sets `__wrapped__`, so
`inspect.signature()` still reports the real signature and the undecorated function stays reachable
for testing.

**Jitter, and why it's not optional.** Without it, 100 clients that failed together retry together:

```
no jitter   : every client waits exactly 0.1s, 0.2s, 0.4s, 0.8s …
                → a synchronised spike at each of those instants, exactly while the
                  service is trying to recover. This is the thundering herd, and it
                  turns a 2-second blip into a 10-minute outage.
full jitter : uniform(0, delay)        → best spread; AWS's recommendation
equal jitter: delay/2 + uniform(0, delay/2) → spread, with a guaranteed minimum wait
```

**`retry_on` + `give_up_on`.** Retrying a `400 Bad Request` wastes four round trips and delays the
error the caller needs. `give_up_on` is checked **first** so you can retry `OSError` in general but
not its `FileNotFoundError` child. In an HTTP client the equivalent is retry on
`429/500/502/503/504` and timeouts, never on `4xx` other than `429`.

**`max_delay` cap.** Pure exponential growth means attempt 10 waits ~17 minutes. Cap it.

**`total_budget`.** The decorator's limit is *attempts*; the caller's limit is *time*. A caller with a
2-second SLA doesn't care that you had 5 attempts left. Checking the budget **before** sleeping is
what makes the guarantee real.

**Bare `raise` on the last attempt** preserves the original traceback. `raise exc` would reset it to
this line; `raise RetryExhausted(...) from exc` is also defensible (it tells the caller *why* the
operation gave up) — just never swallow it and return `None`.

**`time.monotonic()`, not `time.time()`** — `time.time()` can jump backwards (NTP), which would make
a budget check nonsense.

**The injectable `sleep` and `rng`.** This is the testability requirement, and it changes the test
suite completely:

```python
class FakeSleep:
    def __init__(self): self.calls = []
    def __call__(self, seconds): self.calls.append(seconds)

def test_delays_are_exponential_and_capped():
    sleeper = FakeSleep()
    @retry(max_attempts=4, base_delay=1.0, factor=2.0, jitter="none", sleep=sleeper)
    def always_fails(): raise TransientError("x")
    with pytest.raises(TransientError):
        always_fails()
    assert sleeper.calls == [1.0, 2.0, 4.0]       # instant, exact, no flakiness
```

A real `time.sleep` here means a 7-second test that everyone eventually marks `@skip`. With injection
it's microseconds and asserts the *actual delay sequence*. The same trick with `rng=lambda: 1.0`
removes the jitter randomness so the arithmetic is assertable.

### The async variant, and the trap

```python
def retry_async(max_attempts=3, base_delay=0.1, retry_on=(TransientError,),
                sleep=None, **kw):
    sleeper = sleep or asyncio.sleep                 # NOT time.sleep
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retry_on:
                    if attempt == max_attempts: raise
                    await sleeper(backoff_delay(attempt, base_delay, **kw))
        return wrapper
    return decorator
```

**The trap they're testing:** a blocking `time.sleep()` inside an async retry **stalls the entire
event loop** — every other coroutine in the process waits too. At 600 TPS a 2-second backoff on one
request becomes 2 seconds of total service downtime. Use `await asyncio.sleep()`.

Two more async-specific points: `asyncio.CancelledError` is a `BaseException` in 3.8+, so it is *not*
caught by `except Exception` — correct, because a cancelled task must die rather than retry. And if
you retry an HTTP call, pass the same client/session rather than creating one per attempt.

### What retries alone cannot fix

Volunteer this; it's the senior half of the answer.

**Retries make a struggling dependency worse.** If the downstream is at 100% capacity, retrying
triples your offered load at exactly the wrong moment. You need three things together:

1. **Retry with jitter** — for transient blips (this decorator).
2. **A circuit breaker** — after N consecutive failures, stop calling entirely for a cool-off window,
   then probe with one request. This is what stops you hammering a dead dependency.
   [`08_scaling_production_resilience/02_circuit_breaker.py`](../08_scaling_production_resilience/02_circuit_breaker.py)
3. **Idempotency** — a retry is only safe if the operation can be repeated. For a POST that means an
   idempotency key the server deduplicates on; for a Kafka consumer it means an upsert on `event_id`.
   **Retrying a non-idempotent operation is how you double-charge a customer.**

And one architectural point: retries *inside* a request have a hard ceiling — the caller's timeout.
Beyond that, retry **asynchronously**: accept the request, enqueue it, and retry from a worker with a
retry topic or a delay queue. That's [15 — Kafka failure handling](15_kafka_failure_handling.md) and
[18 — Queue architectures](18_queue_architectures.md).

### Complexity and the follow-ups

- Time: O(max_attempts) calls, total wall time bounded by `min(Σ delays, total_budget)`.
- Space: O(1).
- **"Make it log/metric."** `on_retry` is the hook: increment `retries_total{function=...}` and log at
  WARNING with the attempt number. Alert on the *rate*, because a rising retry rate is a leading
  indicator of a dependency failing.
- **"What if the function is a generator?"** The wrapper returns the generator without executing it,
  so nothing is ever retried. You'd need to materialise it or wrap each `__next__`. Spotting this is a
  strong signal.
- **"Should it be a class?"** Only if the state (a shared retry counter, a shared breaker) must be
  readable from outside. Both forms are in the companion file.
- **"Don't write it yourself"** is the right production answer: `tenacity` (`@retry(stop=stop_after_attempt(4),
  wait=wait_exponential_jitter())`) or `urllib3.util.Retry` on a `requests` adapter. Say that *after*
  demonstrating you could write it — they're testing understanding, not library recall.

---

## Problem 2 — Search a keyword in a nested dictionary and return the key

### The four clarifying questions (ask these; they are most of the score)

> *"Search for a keyword in a nested dictionary. If the keyword matches a value, return the
> corresponding key."*

1. **How deep, and are there lists?** Real JSON has dicts inside lists inside dicts. Almost always
   yes.
2. **First match or all matches?** Real payloads have duplicates — `"status"` appears three times.
3. **Exact equality, or substring / case-insensitive?** The word *"search"* hints at substring; a
   human looking for `"pune"` expects to find `"Pune"`.
4. **Just the key, or the PATH?** `"city"` appearing twice is useless. `customer.address.city` is an
   answer.

### Version A — first match, exact, recursive

```python
def find_key_by_value(data, target):
    """Return the key whose value == target, searching nested dicts and lists. None if absent."""
    if isinstance(data, dict):
        for key, value in data.items():
            if value == target:
                return key
            found = find_key_by_value(value, target)
            if found is not None:            # `is not None`, NOT a truthy check
                return found
    elif isinstance(data, (list, tuple)):
        for item in data:
            found = find_key_by_value(item, target)
            if found is not None:
                return found
    return None
```

**The detail worth pointing at: `if found is not None`.** A truthy check (`if found:`) breaks on a
falsy *key* — `{0: "zero"}` or `{"": "empty"}` — and silently keeps searching past a correct answer.
Interviewers probe exactly this with `find_key_by_value({0: "zero"}, "zero")`.

The second subtlety: `True == 1`, so searching for `True` matches a value of `1`. If that matters,
compare `type(value) is type(target)` as well.

### Version B — every match, with the path

```python
def find_all_keys_by_value(data, target, _path=()):
    """Yield (key, path) for EVERY match. A generator, so 'just the first' costs only the first."""
    if isinstance(data, dict):
        for key, value in data.items():
            here = _path + (key,)
            if value == target:
                yield key, ".".join(str(p) for p in here)
            yield from find_all_keys_by_value(value, target, here)
    elif isinstance(data, (list, tuple)):
        for index, item in enumerate(data):
            yield from find_all_keys_by_value(item, target, _path + (f"[{index}]",))
```

```python
list(find_all_keys_by_value(doc, "Pune"))
# [('city', 'customer.address.city'), ('city', 'items.[1].supplier.city')]

next(find_all_keys_by_value(doc, "SHIPPED"), None)     # lazy: stops after the first
```

**Why a generator and not a list:** the caller chooses how much to pay. `next(gen, None)` stops at the
first match; `list(gen)` walks everything; `itertools.islice(gen, 10)` takes ten. One function, three
cost profiles. Saying that is worth more than the code.

### Version C — the "keyword" reading (substring, case-insensitive)

```python
def search_values(data, keyword, exact=False, case_sensitive=False, _path=()):
    def matches(value):
        if value is None: return False
        if exact: return value == keyword
        text   = str(value)   if case_sensitive else str(value).casefold()
        needle = str(keyword) if case_sensitive else str(keyword).casefold()
        return needle in text
    ...   # same walk; yields (key, value, path)
```

`casefold()` rather than `lower()`, because it handles non-ASCII correctly (German `ß` → `ss`). Note a
bare element inside a list has **no key**, so the path *is* the answer there — a case the original
question doesn't mention and you should raise.

### Version D — iterative, for data that's too deep

```python
def find_iterative(data, target, breadth_first=False):
    pending = deque([(data, ())])
    while pending:
        node, path = pending.popleft() if breadth_first else pending.pop()
        if isinstance(node, dict):
            for key, value in node.items():
                if value == target:
                    return key, ".".join(str(p) for p in path + (key,))
                pending.append((value, path + (key,)))
        elif isinstance(node, (list, tuple)):
            for i, item in enumerate(node):
                pending.append((item, path + (f"[{i}]",)))
    return None, None
```

**Why it matters:** Python's recursion limit is ~1000 frames. Deeply nested or **adversarial** JSON
(3000 levels of `{"child": {...}}` is trivial to construct) raises `RecursionError` in the recursive
version — and if you're parsing untrusted input, that's a denial-of-service vector, not just an
inconvenience. An explicit stack is bounded only by heap. The companion file demonstrates both at
3000 levels.

The second payoff: `popleft()` instead of `pop()` makes it **breadth-first**, which finds the
*shallowest* match — usually the one a human means.

### Version E — "now do it a million times a second"

One search is O(n) and cannot be beaten: the value could be in the last leaf. But **repeated**
searches over the same document should pay O(n) once:

```python
def flatten(data, _path=()):
    """-> {dotted.path: leaf_value}"""
    ...

def build_value_index(data):
    """-> {value: [paths]}. O(n) to build, O(1) per lookup after."""
    index = {}
    for path, value in flatten(data).items():
        try:
            index.setdefault(value, []).append(path)
        except TypeError:          # an unhashable leaf — skip it
            pass
    return index
```

`index["Pune"]` → `['customer.address.city', 'items.[1].supplier.city']` in O(1).

### The escalation ladder — this is the answer

| They ask | You reach for |
|---|---|
| "find the key" | recursive walk, exact match, `is not None` guard |
| "all of them" | a generator yielding `(key, path)` |
| "which one did you find?" | carry the path down the recursion |
| "it's huge / deeply nested / untrusted" | explicit stack — no `RecursionError`, no DoS |
| "shallowest match please" | BFS with `deque.popleft()` |
| "substring / case-insensitive" | `casefold()` + `in` |
| "we do this constantly" | flatten once into a `value → [paths]` index |
| "it's a 100GB JSON file" | you can't hold it at all — stream with `ijson` and match on events ([30](30_large_file_processing.md)) |
| "it's in a database" | this is a `jsonb` query: `WHERE data @> '{"city":"Pune"}'` with a GIN index. Don't walk JSON in Python if Postgres can index it. |

That last row is worth volunteering. The best answer to "search nested JSON" is sometimes "don't — put
it where it can be indexed".

### Complexity

- Time **O(n)** in nodes for every version; **O(1)** per lookup after indexing.
- Space **O(depth)** for the recursive/stack versions (the path tuples), **O(n)** for the index.
- Worst case is the same as best case for a miss: you must visit every node.

---

## Problem 3 — Design and implement an LRU cache

### The requirement

> *"Design an LRU cache with O(1) `get` and `put`. On overflow, evict the least recently USED key."*

The word doing the work is **used**: a key that was just *read* counts as recently used, even if it
was inserted long ago. That's what distinguishes LRU from FIFO, and it's the first thing to say.

### Version 1 — `OrderedDict` (the pragmatic answer)

```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._store: OrderedDict = OrderedDict()

    def get(self, key):
        if key not in self._store:
            return -1
        self._store.move_to_end(key)          # mark as most-recently-used — O(1)
        return self._store[key]

    def put(self, key, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)   # evict the LRU (the front) — O(1)
```

**Why it's O(1):** `OrderedDict` is a dict **plus an internal doubly linked list** of keys.
`move_to_end` unlinks and relinks one node (pointer updates only, no shifting), and `popitem(last=False)`
pops the head. Both O(1). Saying *"OrderedDict is a dict plus a doubly linked list"* is the whole
justification, and it's the bridge to version 2.

### Version 2 — from scratch (when they say "don't use OrderedDict")

They're checking whether you know *why* it's O(1). The answer is the data-structure pairing:

> **a dict for O(1) lookup by key + a doubly linked list for O(1) reordering.**

Why each half is necessary:

- A dict alone has no order, so you can't find the LRU without scanning — O(n).
- A list alone needs O(n) to find the node for a key.
- A **singly** linked list can't delete a node in O(1) (you can't reach its predecessor).
- The dict maps `key → node`, so you get the node in O(1) and then relink in O(1).

```python
class _Node:
    __slots__ = ("key", "value", "prev", "next")      # no per-instance __dict__: smaller, faster
    def __init__(self, key=None, value=None):
        self.key, self.value = key, value
        self.prev = self.next = None

class LRUCacheFromScratch:
    """head.next is always the MOST recently used; tail.prev is always the LEAST."""
    def __init__(self, capacity):
        self.capacity, self._map = capacity, {}
        self.head, self.tail = _Node(), _Node()       # SENTINELS: no null checks at the edges
        self.head.next, self.tail.prev = self.tail, self.head

    def _remove(self, node):
        node.prev.next, node.next.prev = node.next, node.prev

    def _insert_at_front(self, node):
        node.next, node.prev = self.head.next, self.head
        self.head.next.prev = self.head.next = node

    def get(self, key):
        if key not in self._map: return -1
        node = self._map[key]
        self._remove(node); self._insert_at_front(node)
        return node.value

    def put(self, key, value):
        if key in self._map:
            self._remove(self._map[key])
        node = _Node(key, value)
        self._map[key] = node
        self._insert_at_front(node)
        if len(self._map) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self._map[lru.key]                     # ← the reason nodes store their KEY
```

**The two implementation details interviewers look for:**

1. **Sentinel head/tail nodes.** They remove every `if node.prev is None` edge case. Without them,
   `_remove` and `_insert_at_front` each need three branches and at least one of them will be wrong.
2. **The node stores its `key`.** On eviction you have the *node* (via `tail.prev`) and need to delete
   the **dict entry** — which requires the key. Candidates who store only the value get stuck here,
   and it's a satisfying "aha" to name upfront.

`__slots__` is a nice extra: it removes the per-instance `__dict__`, roughly halving memory per node,
which matters at a million entries.

### The follow-ups, which are the real interview

**"Is it thread-safe?"** No. `get` does read-remove-insert — three steps, and a thread switch between
them corrupts the linked list. The fix:

```python
self._lock = threading.Lock()
def get(self, key):
    with self._lock:                 # guards the WHOLE read-modify-write, not just the read
        ...
```

A `RLock` isn't needed unless methods call each other. Note that under heavy concurrency the lock
becomes the bottleneck — the production answer is **sharding**: N independent caches keyed by
`hash(key) % N`, each with its own lock, which is exactly what Java's `ConcurrentHashMap` and Caffeine
do.

**"Add a TTL."** LRU evicts on *size*; TTL evicts on *age*. They're orthogonal and real caches need
both — LRU alone will happily serve a stale price forever if the key stays hot.

```python
def put(self, key, value, ttl=None):
    expires = time.monotonic() + ttl if ttl else None
    self._store[key] = (value, expires)

def get(self, key):
    if key not in self._store: return -1
    value, expires = self._store[key]
    if expires and time.monotonic() > expires:
        del self._store[key]                   # LAZY expiry, on read
        return -1
    self._store.move_to_end(key)
    return value
```

**Lazy expiry (on read) vs active (a sweeper thread):** lazy is simpler and costs nothing when idle,
but an expired-and-never-read key occupies capacity forever. Redis does both: lazy on access plus a
background sampler. Mention `monotonic()` rather than `time()` so an NTP adjustment can't resurrect or
prematurely expire entries.

**"Why not just `functools.lru_cache`?"** For memoising a pure function, use it — it's C-implemented
and faster than anything you'll write:

```python
@functools.lru_cache(maxsize=1024)
def expensive(user_id: int) -> dict: ...
expensive.cache_info()     # CacheInfo(hits=..., misses=..., maxsize=1024, currsize=...)
```

Its limits, which is why the question still gets asked: **no TTL**, **no per-key invalidation** (only
`cache_clear()`), **arguments must be hashable** (so no dict or list arguments), it's **per-process**
(4 pods = 4 caches), and it **keeps a strong reference to every argument and result**, so caching
`self` methods leaks instances. `functools.cache` is `lru_cache(maxsize=None)` — unbounded, so it's a
memory leak waiting to happen on unbounded input.

**"What about other eviction policies?"**

| Policy | Evicts | Good for |
|---|---|---|
| **LRU** | least recently used | general purpose; strong temporal locality |
| **LFU** | least *frequently* used | stable hot sets; survives a one-off scan that would flush an LRU |
| **FIFO** | oldest inserted | trivial; ignores access, usually worse |
| **TTL only** | anything expired | correctness-driven caching (prices, tokens) |
| **TinyLFU / W-TinyLFU** | frequency sketch + a small LRU window | what Caffeine and modern Redis-likes use; near-optimal hit ratios |
| **ARC** | adapts between recency and frequency | patented, hence rare in OSS |

The practical point: **LRU's weakness is a sequential scan**. One batch job reading a million keys
once evicts your entire hot set. LFU or a scan-resistant policy (or a separate cache for the batch
job) is the fix — and naming that failure mode is a strong senior signal.

**"Now make it distributed."** This is the real architecture question and the most valuable thing to
have ready. An in-process LRU per pod means:

- **N× the memory** for the same data, and a cold cache on every deploy.
- **Inconsistency**: pod A has the old price, pod B the new one, and the customer's answer depends on
  which pod the load balancer picked.
- **No shared invalidation**: updating a row can't evict it from four processes.

The standard answer is a **two-tier cache**:

```
L1: in-process LRU, TTL ~5s   → absorbs the hot keys, zero network cost
L2: Redis, TTL ~5min          → shared across pods, survives a deploy
L3: the database              → the source of truth
```

L1's TTL is deliberately short, because the cost of inconsistency is bounded by it. Invalidation goes
to Redis plus a pub/sub message so each pod can drop its L1 entry. And the stampede problem (when a
hot key expires, N requests all miss and hit the DB simultaneously) needs a lock or
`stale-while-revalidate` — shown in
[`07_caching_queues/02_cache_stampede_lock.py`](../07_caching_queues/02_cache_stampede_lock.py) and
[17 — Caching](17_caching.md).

### Complexity

| Operation | `OrderedDict` | from scratch | with a lock |
|---|---|---|---|
| `get` | O(1) | O(1) | O(1) + contention |
| `put` | O(1) | O(1) | O(1) + contention |
| eviction | O(1) | O(1) | O(1) |
| space | O(capacity) | O(capacity), ~2 pointers/entry more | same |

---

## A worked example — the three composed

They are three parts of one real code path, which is a satisfying thing to point out:

```python
"""Fetch a price: check the cache, call the pricing service with retries, search the response."""

price_cache = LRUCache(capacity=10_000)          # problem 3

@retry(max_attempts=4, base_delay=0.2, max_delay=5.0,            # problem 1
       retry_on=(TransientError,), give_up_on=(PermanentError,),
       total_budget=3.0,                                          # the caller's SLA
       on_retry=lambda n, e, d: metrics.inc("pricing_retries_total"))
def fetch_price_payload(sku: str) -> dict:
    response = http.get(f"/pricing/{sku}", timeout=1.0)
    if response.status_code in (429, 500, 502, 503, 504):
        raise TransientError(f"pricing service {response.status_code}")
    if 400 <= response.status_code < 500:
        raise PermanentError(f"bad request for {sku}: {response.status_code}")
    return response.json()


def get_price(sku: str) -> float:
    cached = price_cache.get(sku)
    if cached != -1:
        metrics.inc("price_cache_hits_total")
        return cached

    payload = fetch_price_payload(sku)           # retried, bounded by a 3s budget

    # problem 2: the vendor nests the figure differently per product type, so SEARCH for it
    key, path = find_iterative(payload, sku)     # iterative: the payload is untrusted
    amount_matches = list(find_all_keys_by_value(payload, "USD"))
    if not amount_matches:
        raise PermanentError(f"no USD amount in pricing payload for {sku} (searched {path})")

    price = float(payload_at(payload, amount_matches[0][1].replace("currency", "amount")))
    price_cache.put(sku, price)
    return price
```

**What this shows, and why it's the right way to present all three:**

- The **retry** is bounded by the caller's SLA (`total_budget=3.0`), not just by attempts, and it
  splits transient from permanent so a 400 doesn't cost four round trips.
- The **search** is iterative because the payload comes from outside — an adversarially nested
  response would `RecursionError` the recursive version.
- The **cache** sits in front of everything, so the retry/backoff cost is paid once per SKU per TTL
  rather than per request. At a 90% hit ratio the pricing service sees 10% of the traffic — which is
  the same arithmetic as [29 — Capacity scaling](29_capacity_scaling_tps.md).
- And the missing piece, which you should name: **a circuit breaker** around
  `fetch_price_payload`, so a dead pricing service fails fast instead of adding 3 seconds to every
  request. Retry + breaker + cache is the complete set.

---

## Hands-on drills

1. Write `@retry` from scratch with no reference. Then add the injectable `sleep` and write the test
   asserting `sleeper.calls == [1.0, 2.0, 4.0]`.
2. Make `retry` wrap a generator function. Observe that nothing is ever retried, and explain why in
   one sentence.
3. Implement `jitter="decorrelated"` (`min(cap, uniform(base, previous * 3))`) and compare the spread
   against full jitter over 100 simulated clients.
4. Write the retry decorator so it *also* respects a circuit breaker, and decide which wraps which.
   (Breaker outside, retry inside — or the reverse? Justify it.)
5. `find_key_by_value({0: "zero"}, "zero")` with a truthy `if found:` check. Watch it return `None`.
   Fix it.
6. Build a 3000-level nested dict and run both the recursive and iterative searches. Then argue
   whether `sys.setrecursionlimit(10000)` is a fix or a liability.
7. Add a `max_depth` parameter to the search and make it raise on deeper input. Explain why that
   matters for untrusted JSON.
8. Build the `value → [paths]` index and time 10,000 lookups against 10,000 recursive searches.
9. Implement the LRU from scratch without sentinel nodes. Count the `if node is None` branches you
   needed, then add the sentinels back.
10. Store only values in the node (not keys) and try to implement eviction. Find the wall.
11. Add a TTL to the `OrderedDict` version with lazy expiry. Then add a background sweeper and decide
    which you'd ship.
12. Hammer the LRU from 8 threads with no lock and assert the invariant `len(self._map) <= capacity`.
    Watch it break. Add the lock. Then shard it 16 ways and measure the throughput difference.
13. Simulate the scan problem: fill an LRU with 1000 hot keys, then read 100,000 cold keys once, then
    measure the hit ratio on the hot set. That number is LRU's weakness in one experiment.

---

## The 60-second spoken answers

**Retry decorator:**

> "Three nesting levels because the decorator takes arguments, `functools.wraps` so the function keeps
> its name and signature, and the delay is `base × factor^(attempt−1)` capped by a `max_delay` —
> plus **jitter**, because without it a hundred clients that failed together retry in the same instant
> and the thundering herd turns a blip into an outage. I retry only transient errors and let permanent
> ones propagate immediately, with a `give_up_on` list that's checked first so I can retry `OSError`
> but not `FileNotFoundError`. I bound it by a total time budget as well as attempts, because the
> caller has an SLA and doesn't care that I had attempts left. On the last attempt I use a bare
> `raise` so the original traceback survives — never return `None`. And critically I inject `sleep`
> and the RNG, so tests assert the exact delay sequence in microseconds instead of actually waiting
> seven seconds. For async I `await asyncio.sleep`, because a blocking sleep stalls the whole event
> loop. In production I'd pair it with a circuit breaker, because retries alone just hammer a dying
> dependency, and I'd make the operation idempotent — retrying a non-idempotent charge double-bills a
> customer. And I'd reach for `tenacity` rather than shipping my own."

**Nested-dict search:**

> "First I'd ask four things: does it nest through lists as well as dicts, do you want the first match
> or all of them, is it exact or substring, and do you want the key or the path — because `city`
> appearing twice is useless without `customer.address.city`. Then a recursive walk, O(n) in nodes,
> with the guard being `if found is not None` rather than a truthy check, or a falsy key like `0`
> breaks it. I'd make the all-matches version a generator yielding `(key, path)`, so the caller
> chooses to pay for one match or all of them. If the data is large, deeply nested or untrusted I
> switch to an explicit stack, because Python's ~1000-frame recursion limit makes the recursive
> version a DoS vector — and `popleft` instead of `pop` gives me breadth-first, which finds the
> shallowest match, usually the one a human meant. If we're doing this constantly I flatten once into
> a `value → [paths]` index and every lookup becomes O(1). And if this is actually a 100GB file I
> can't hold it at all — that's streaming with `ijson`; if it's in Postgres, it's a `jsonb` containment
> query with a GIN index, and I shouldn't be walking JSON in Python at all."

**LRU cache:**

> "The word that matters is *used*: a key that was just read counts as recently used, which is what
> separates LRU from FIFO. The pragmatic answer is `OrderedDict` with `move_to_end` on every access and
> `popitem(last=False)` to evict — both O(1), because `OrderedDict` is a dict plus an internal doubly
> linked list. If they ask me not to use it, I build exactly that: a dict from key to node for O(1)
> lookup, plus a doubly linked list for O(1) reordering, with sentinel head and tail nodes so there are
> no null-check edge cases. A singly linked list wouldn't work because you can't unlink a node in O(1),
> and each node has to store its key, because on eviction you reach the node via `tail.prev` and still
> need the key to delete the dict entry.
>
> It isn't thread-safe — `get` is a read-modify-write — so it needs a lock around the whole operation,
> and under contention I'd shard into N caches by key hash, which is what Caffeine and
> `ConcurrentHashMap` do. LRU evicts on size, so I'd usually add a TTL too, with lazy expiry on read
> plus a sampler, and `monotonic` rather than wall time. For a pure function I'd just use
> `functools.lru_cache`, but it has no TTL, no per-key invalidation and it's per-process.
>
> Which is the real issue: in-process means four pods hold four copies with four different answers and
> no shared invalidation. So in production it's two tiers — a small in-process LRU with a ~5-second
> TTL to absorb hot keys, Redis behind it as the shared tier, and the DB as the source of truth — with
> pub/sub invalidation and stampede protection on the hot keys. And LRU's weakness worth naming is a
> sequential scan: one batch job reading a million keys once flushes the entire hot set, which is what
> LFU or a scan-resistant policy like W-TinyLFU is for."
