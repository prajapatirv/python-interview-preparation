# Deep Dive 01 — Data Structures (List, Tuple, Dict, Set/FrozenSet) + `collections`

> Runnable companion: [`01_python_core/01_data_structures.py`](../01_python_core/01_data_structures.py)
> Related deep dives: [Comprehensions](02_comprehensions_map_filter_reduce.md) · [OOP](06_oop_inheritance_mro.md) · [Java bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

Nobody asks "what is a list" to find out whether you know what a list is. They ask it to find out
whether you know the **internal representation**, the **time complexity that falls out of it**, and
whether you pick structures deliberately or by habit. For a 6–10 year candidate the expected answer
to "list vs tuple" is not "one is mutable" — it's mutability *plus* hashability *plus* memory layout
*plus* a concrete situation where the difference decided a design.

The `collections` module is where interviewers separate people who have written a lot of Python from
people who have written Java in Python. `Counter`, `defaultdict`, `deque`, `namedtuple`,
`OrderedDict` and `ChainMap` turn ten-line loops into one line, and the fact that you reach for them
is itself the signal.

---

## Must-know points (the compressed version)

- **`list`** is a *dynamic array* of pointers — a contiguous block of `PyObject*`. `append` is
  amortised O(1) because CPython over-allocates (growth factor ~1.125 for large lists, so the array
  is resized only occasionally). `insert(0, x)` and `pop(0)` are **O(n)** because every pointer after
  the insertion point shifts. `x in list` is O(n) — a linear scan.
- **`tuple`** is a fixed-size array, immutable, and **hashable if and only if every element is
  hashable**. It is smaller than the equivalent list (no over-allocation, no `__dict__`) and CPython
  caches small tuples for reuse.
- **`dict`** is an *open-addressing* hash table. Since CPython 3.6 it uses a **compact layout**: a
  sparse array of indices plus a dense array of `(hash, key, value)` entries. That dense array is why
  iteration order matches insertion order — a 3.6 implementation detail that became a **language
  guarantee in 3.7**. Get/set/delete are O(1) average, O(n) worst case (pathological collisions).
  The table resizes when it is roughly two-thirds full.
- **`set`** is the same hash table machinery storing keys only. O(1) membership, unordered.
  **`frozenset`** is the immutable — and therefore hashable — version.
- **`deque`** (from `collections`) is a doubly-linked list of fixed-size blocks: O(1) append and pop
  at *both* ends, but O(n) indexing into the middle. `deque(maxlen=n)` gives you a free ring buffer.

---

## Interview questions and full answers

### Q1. What is the difference between a list and a tuple, and when would you genuinely choose a tuple?

The textbook half of the answer is that a list is mutable and a tuple is immutable. The half that
gets you the job is *what immutability buys you*:

1. **Hashability.** Because a tuple's contents cannot be rebound, Python can compute a stable hash
   for it (provided every element is itself hashable). That makes a tuple usable as a dict key or a
   set member. A list can never be.
2. **Memory and speed.** A list over-allocates so it can grow cheaply; a tuple allocates exactly what
   it needs. A tuple literal of constants is also *folded into a constant* by the compiler, so it
   costs nothing at runtime.
3. **Intent.** A tuple communicates "this is one record with a fixed shape" — coordinates, an RGB
   colour, a database row, the multiple return values of a function. A list communicates "this is a
   homogeneous, growing collection."

```python
import sys

print(sys.getsizeof([1, 2, 3]))   # 88 — bigger: over-allocates headroom for growth
print(sys.getsizeof((1, 2, 3)))   # 64 — exactly sized

d = {(10, 20): "point"}           # tuple as a dict key -> fine
# d[[10, 20]] = "x"               # TypeError: unhashable type: 'list'
```

**Rule of thumb:** heterogeneous fixed record → tuple (or better, a `NamedTuple`/`dataclass`).
Homogeneous varying-length sequence → list.

> **Java contrast.** There is no direct equivalent. A tuple is closest to a small immutable
> `record` (Java 16+) used as a `HashMap` key, and a list is `ArrayList`. Java's `List.of(...)`
> creates an *unmodifiable* list, which is not the same as a tuple — it's still not hashable in the
> value-based way a tuple is.

---

### Q2. Is a tuple always hashable? Is it truly immutable?

**No to both, strictly speaking** — and this is the follow-up interviewers use to see whether you
understood or memorised.

A tuple is immutable in the sense that you cannot rebind its slots: `t[0] = x` raises `TypeError`.
But if a slot *holds a reference to a mutable object*, that object can still be mutated. The tuple's
contents (the references) never change; what they point at can.

Hashability follows from this: `hash(t)` recursively hashes every element, so a tuple containing a
list is unhashable.

```python
t = (1, [2, 3])
t[1].append(4)      # allowed -> (1, [2, 3, 4]); the reference didn't change
# t[1] = [9]        # TypeError: 'tuple' object does not support item assignment
# hash(t)           # TypeError: unhashable type: 'list'
```

This is exactly the "shallow immutability" idea you know from Java's `final` — `final List<X> xs`
stops reassignment of `xs`, not `xs.add(...)`.

---

### Q3. How is a Python dict implemented, and what are the complexities?

A dict is an **open-addressing hash table** (not separate chaining like Java's `HashMap`). On a
collision, CPython probes for another slot using a perturbation scheme derived from the full hash,
rather than walking a linked list in a bucket.

Since 3.6 the layout is **split in two**:

```
indices:  [ -1, 1, -1, -1, 0, -1, 2, -1 ]     # sparse; small ints pointing into entries
entries:  [ (hash, key, value),                # dense; append-only in insertion order
            (hash, key, value),
            (hash, key, value) ]
```

Two consequences follow, and both are worth stating out loud:

- **Memory.** The sparse array holds small integers instead of full 24-byte entries, so a dict is
  roughly 20–25% smaller than the pre-3.6 layout.
- **Ordering.** Iteration walks the *dense* array, which is append-ordered. That is why dicts
  preserve insertion order. It was an implementation detail in 3.6 and became a **guarantee in 3.7**.

Complexities: `get`/`set`/`del`/`in` are **O(1) average**, **O(n) worst case** when many keys collide.
The table **resizes (and rehashes) when it is about two-thirds full**, which is an amortised O(n)
event — relevant if you are building a huge dict in a tight loop and can pre-size it.

One more detail interviewers like: **overwriting an existing key does not move it.** The key keeps
its original position in the entries array; only a brand-new key is appended at the end.

```python
d = {"a": 1, "b": 2, "c": 3}
d["a"] = 99
print(list(d))      # ['a', 'b', 'c'] — 'a' stayed first
d["z"] = 0
print(list(d))      # ['a', 'b', 'c', 'z'] — new key appended
```

> **Java contrast.** `HashMap` uses buckets with linked lists that convert to red-black trees past 8
> entries; `LinkedHashMap` is what you'd reach for to get insertion order. In Python, plain `dict`
> already *is* the `LinkedHashMap`, which is why `OrderedDict` is now a niche tool (see Q12).

---

### Q4. What makes an object usable as a dict key or set element?

It must be **hashable**, which is a contract, not a type:

1. It implements `__hash__`, returning an `int` that **never changes during the object's lifetime**.
2. It implements `__eq__` **consistently** with that hash: if `a == b`, then `hash(a) == hash(b)`.
   (The converse need not hold — unequal objects may share a hash; that's a collision.)

Built-in immutables satisfy this: `int`, `float`, `str`, `bytes`, `tuple`-of-hashables, `frozenset`,
`None`, and `bool`.

A user-defined class is hashable **by identity** by default (`hash(obj)` derives from `id(obj)`,
`__eq__` is identity). The trap:

> **If you override `__eq__` and do not override `__hash__`, Python sets `__hash__ = None` and your
> instances become unhashable.**

This is deliberate: once you've said "two distinct objects can be equal", identity-based hashing
would break the contract. You must supply a matching `__hash__`.

```python
class Money:
    def __init__(self, amount): self.amount = amount
    def __eq__(self, other):
        return isinstance(other, Money) and self.amount == other.amount
    __hash__ = None          # what Python does implicitly

# {Money(5)}   -> TypeError: unhashable type: 'Money'

class MoneyFixed:
    def __init__(self, amount): self.amount = amount
    def __eq__(self, other):
        return isinstance(other, MoneyFixed) and self.amount == other.amount
    def __hash__(self):
        return hash(self.amount)     # consistent with __eq__

print(len({MoneyFixed(5), MoneyFixed(5)}))   # 1
```

The shortcut for real code: `@dataclass(frozen=True)` generates a consistent `__eq__` **and**
`__hash__` for you.

> **Java contrast.** This is exactly the `equals()`/`hashCode()` contract, except Java lets you
> break it silently and Python actively disables hashing to stop you.

---

### Q5. `set` vs `frozenset` — give a real use for `frozenset`.

Both are unordered collections of unique hashable items with O(1) membership and the full algebra
(`|` union, `&` intersection, `-` difference, `^` symmetric difference). The difference is that
`set` is mutable (`add`, `discard`, `update`) and `frozenset` is not — which makes `frozenset`
**hashable**, so it can be a dict key or an element of another set.

The realistic use case is **caching or grouping keyed by an unordered combination**: a permission
set, a set of feature tags, a group of participants. You want `{"read", "write"}` and
`{"write", "read"}` to hit the same cache entry.

```python
role_for = {}
role_for[frozenset({"read", "write"})] = "editor"
role_for[frozenset({"read"})] = "viewer"

print(role_for[frozenset({"write", "read"})])   # 'editor' — order irrelevant

# frozensets nest; plain sets cannot
pairs = {frozenset({1, 2}), frozenset({2, 1})}
print(len(pairs))                               # 1 — deduplicated
```

Second use: **memoising a function whose argument is a set.** `lru_cache` requires hashable
arguments, so you convert the incoming set to a `frozenset` at the boundary.

---

### Q6. Explain shallow copy vs deep copy.

A **shallow copy** creates a new outer container but copies *references* to the inner objects. The
idioms are `list.copy()`, `dict.copy()`, a full slice `xs[:]`, `list(xs)`, and `copy.copy(x)`.

A **deep copy** (`copy.deepcopy`) walks the object graph and recursively copies everything, keeping a
memo dict so shared references stay shared and cycles don't loop forever.

```python
import copy

a = [[1, 2], [3, 4]]
shallow = a.copy()
deep    = copy.deepcopy(a)

a[0].append(99)
print(shallow)   # [[1, 2, 99], [3, 4]]  <- inner list is the SAME object
print(deep)      # [[1, 2], [3, 4]]      <- fully independent
```

**When it matters in production:** any time you hand a caller a mutable attribute of your object.
Returning `self._items` lets the caller mutate your internals; returning `self._items.copy()` (or
better, a tuple) does not. Deep copies are expensive — never deep-copy in a hot path just to feel
safe; prefer immutable structures.

---

### Q7. What is the classic mutable default argument bug?

**Default argument values are evaluated exactly once, at function *definition* time**, and stored on
the function object (`func.__defaults__`). A mutable default is therefore shared by every call that
doesn't supply the argument, and it accumulates state across calls.

```python
def add_bad(item, bucket=[]):          # BAD
    bucket.append(item)
    return bucket

print(add_bad(1))      # [1]
print(add_bad(2))      # [1, 2]   <- surprise: same list
print(add_bad.__defaults__)   # ([1, 2],) — you can literally see it

def add_good(item, bucket=None):       # GOOD
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

Use `None` as a sentinel and construct inside the body. If `None` is a legitimate value for that
parameter, create your own sentinel: `_MISSING = object()`.

The same trap applies to `datetime.now()` as a default — it freezes the import-time timestamp
forever. And it applies to **class attributes**, which are shared across all instances:

```python
class Cart:
    items = []          # BAD — one list shared by every Cart
    def __init__(self):
        self.items = [] # GOOD — per-instance
```

---

### Q8. When would you use `collections.Counter`? Show a top-k example.

`Counter` is a `dict` subclass for counting hashable items. Three things make it worth reaching for:

- **`most_common(k)`** gives the top-k by frequency using a heap — O(n log k), not a full sort.
- **Arithmetic between counters**: `+` adds counts, `-` subtracts (dropping non-positive), `&` takes
  element-wise minimum (intersection), `|` element-wise maximum (union).
- **Missing keys return `0`** instead of raising `KeyError` — but note a *read* does not insert the
  key (unlike `defaultdict`).

```python
from collections import Counter

words = "a b a c b a d".split()
c = Counter(words)
print(c.most_common(2))                        # [('a', 3), ('b', 2)]
print(c["zzz"])                                # 0 — no KeyError, no insertion

# Anagram check in one line: two Counters are equal iff the multisets match
print(Counter("listen") == Counter("silent"))  # True

# Multiset algebra — what's in the order but not in stock?
order = Counter({"widget": 5, "gizmo": 2})
stock = Counter({"widget": 3, "gizmo": 9})
print(order - stock)                           # Counter({'widget': 2})
```

Real uses: log-level frequency analysis, top-N API endpoints by error count, deduplicating with
counts, and the anagram-grouping class of coding-round problems.

---

### Q9. `defaultdict` vs `dict.setdefault` vs `dict.get` — which and why?

All three deal with "the key might not be there," but they behave differently:

| | Inserts missing key? | Constructs the default eagerly? | Typical use |
|---|---|---|---|
| `d.get(k, default)` | No | Yes (it's an argument) | Pure read with a fallback |
| `d.setdefault(k, v)` | Yes | **Yes — always**, even on a hit | One-off grouping on a plain dict |
| `defaultdict(factory)` | **Yes, on any access** | No — factory called only on miss | Repeated grouping/accumulating |

The `setdefault` gotcha: `d.setdefault(k, expensive())` calls `expensive()` **every time**, hit or
miss, because arguments are evaluated before the call. `defaultdict` calls the factory only on a
genuine miss.

The `defaultdict` gotcha, which is the real interview point: **even a read inserts the key.**

```python
from collections import defaultdict

by_user = defaultdict(list)
orders = [("alice", 10), ("bob", 5), ("alice", 7)]
for user, amt in orders:
    by_user[user].append(amt)          # no `if user not in ...` needed
print(dict(by_user))                   # {'alice': [10, 7], 'bob': [5]}

print(by_user["carol"])                # [] — looks harmless...
print(dict(by_user))                   # ...but 'carol' is now a key!
```

That silent insertion has caused real bugs (a membership test that mutates the dict it's testing).
If you want lookups to stay read-only after building, convert with `dict(by_user)` when you're done.

---

### Q10. Why use `deque` instead of `list` for a queue?

Because `list` is a *dynamic array*: `list.pop(0)` and `list.insert(0, x)` are **O(n)** — every
remaining element is memmoved one slot. Build a queue on a list and you get O(n²) behaviour that
looks fine for 100 items and falls over at 100,000.

`collections.deque` is a doubly-linked list of fixed-size blocks, giving **O(1) `append`,
`appendleft`, `pop`, `popleft`**. The trade-off is that random indexing into the middle is O(n),
because it has to walk blocks — so a deque is a bad list, just as a list is a bad queue.

`deque(maxlen=n)` is the hidden gem: a fixed-size ring buffer that silently discards from the
opposite end when full. Perfect for "last N events", a sliding window, or a bounded audit trail.

```python
from collections import deque

last5 = deque(maxlen=5)
for i in range(8):
    last5.append(i)
print(last5)          # deque([3, 4, 5, 6, 7], maxlen=5)

q = deque([1, 2])
q.appendleft(0)       # O(1)
print(q.popleft())    # 0, O(1)
```

`deque` is also the backbone of the classic **sliding-window maximum** problem (see the worked
example below), and it's thread-safe for `append`/`popleft` — though for real producer/consumer work
you want `queue.Queue`, which adds blocking and `task_done()`.

> **Java contrast.** `deque` ≈ `ArrayDeque`. Python's `list` ≈ `ArrayList`, and the O(n) `remove(0)`
> penalty is identical in both languages — the difference is only that Python makes `list` so
> convenient that people reach for it reflexively.

---

### Q11. What are `namedtuple` and `dataclass`, and how do they differ?

Both give you a "record with named fields" instead of a bare tuple or dict.

**`collections.namedtuple`** (or the typed `typing.NamedTuple`) creates an actual **tuple subclass**:
immutable, hashable, unpackable, indexable, and very memory-light (no `__dict__`). It's the right
choice for a small value returned from a function.

**`@dataclasses.dataclass`** generates `__init__`, `__repr__`, `__eq__` (and optionally ordering) on a
normal class. It is **mutable by default**; `frozen=True` makes it immutable and hashable, and
`slots=True` (3.10+) drops the per-instance `__dict__` for a big memory win. It supports type hints,
defaults, `field(default_factory=...)`, methods, inheritance and `__post_init__` validation.

```python
from collections import namedtuple
from dataclasses import dataclass, field

Point = namedtuple("Point", "x y")
p = Point(1, 2)
x, y = p                     # unpacks like a tuple
print(p.x, p[0], p._asdict())

@dataclass(frozen=True, slots=True)
class Order:
    id: int
    amount: float = 0.0
    tags: tuple = ()                       # immutable default is safe
    # NOT: tags: list = []  -> dataclass raises; use field(default_factory=list)

@dataclass
class Cart:
    items: list = field(default_factory=list)   # the correct mutable default
```

**Choosing:** `namedtuple` for lightweight positional records and tuple-compatibility (it will
unpack into existing tuple-consuming code); `dataclass` for domain objects with behaviour,
validation or mutability. `pydantic.BaseModel` when you additionally need **runtime coercion and
validation** at a system boundary (see [FastAPI deep dive](10_web_frameworks.md)).

> **Java contrast.** `namedtuple`/`frozen dataclass` ≈ a `record`. A mutable `dataclass` ≈ a Lombok
> `@Data` POJO.

---

### Q12. Is `OrderedDict` still useful now that `dict` preserves order?

Yes, in three specific cases — and knowing them signals you understand the difference between
"ordered" and "order-aware":

1. **`move_to_end(key, last=True/False)`** — reposition an existing key in O(1). Plain `dict` has no
   equivalent; you'd delete and re-insert.
2. **`popitem(last=False)`** — pop from the *front*. Plain `dict.popitem()` only pops the last item.
3. **Order-sensitive equality.** `OrderedDict([("a",1),("b",2)]) != OrderedDict([("b",2),("a",1)])`,
   whereas the equivalent plain dicts compare **equal**. If order is semantically part of the value,
   `OrderedDict` encodes that.

The canonical use of 1+2 together is an **LRU cache**:

```python
from collections import OrderedDict

class LRU:
    def __init__(self, capacity):
        self.cap = capacity
        self.d = OrderedDict()

    def get(self, k):
        if k not in self.d:
            return -1
        self.d.move_to_end(k)            # mark as most-recently used, O(1)
        return self.d[k]

    def put(self, k, v):
        self.d[k] = v
        self.d.move_to_end(k)
        if len(self.d) > self.cap:
            self.d.popitem(last=False)   # evict least-recently used, O(1)
```

In application code you'd normally use `functools.lru_cache`; the manual version is a very common
coding-round question (see [`11_coding_challenges/03_lru_cache.py`](../11_coding_challenges/03_lru_cache.py)).

---

### Q13. What is `ChainMap` used for?

`ChainMap` layers several mappings into **one read view without copying them**. Lookup tries each
mapping in order and returns the first hit. The classic application is **layered configuration**:
CLI arguments override environment variables, which override a config file, which overrides
built-in defaults.

```python
from collections import ChainMap
import os

defaults = {"env": "dev", "debug": False, "workers": 4}
file_cfg = {"workers": 8}
cli      = {"debug": True}

cfg = ChainMap(cli, os.environ, file_cfg, defaults)
print(cfg["debug"])     # True     <- from cli
print(cfg["workers"])   # 8        <- from file_cfg (cli didn't set it)
print(cfg["env"])       # 'dev'    <- fell all the way through to defaults
```

Two behaviours to call out: **writes and deletes affect only the first mapping** (`cfg["x"] = 1`
writes into `cli`), and because it is a *view*, changes to the underlying dicts are visible
immediately — no rebuild needed. `new_child()` gives you a cheap scoped overlay, which is how you'd
model nested scopes in an interpreter.

---

### Q14. How do you remove duplicates from a list while keeping order?

`list(set(items))` deduplicates but **destroys order** (set iteration order depends on hashes).
Since dicts preserve insertion order, the idiom is:

```python
items = [3, 1, 3, 2, 1]
print(list(dict.fromkeys(items)))      # [3, 1, 2] — O(n), order preserved
```

`dict.fromkeys` builds a dict with those keys and `None` values, which is exactly an ordered set.

For **unhashable** items, or when you want to dedupe on a *projection* of the item (e.g. one record
per `order_id`), you need an explicit loop with a seen-set of the hashable key:

```python
def dedupe_by(records, key):
    seen, out = set(), []
    for r in records:
        k = key(r)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out

rows = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
print(dedupe_by(rows, key=lambda r: r["id"]))   # keeps the FIRST id=1
```

This shape appears constantly in Kafka consumers (dedupe by event ID) and Pandas pipelines
(`drop_duplicates(subset=..., keep=...)`).

---

### Q15. What do `is` and `==` check, and why does `a is b` sometimes return `True` for small ints?

`==` invokes `__eq__` and compares **values**. `is` compares **identity** — whether both names refer
to the same object in memory (equivalent to `id(a) == id(b)`).

CPython performs two optimisations that make `is` *accidentally* work and mislead people:

- **Small integer caching**: integers from `-5` to `256` are pre-allocated singletons at interpreter
  start, so `256 is 256` is `True` but `257 is 257` may be `False` at runtime.
- **String interning**: identifier-like string literals are interned at compile time, so
  `"abc" is "abc"` is `True` but `"".join(["a","b","c"]) is "abc"` is `False`.

```python
a, b = 256, 256
print(a is b)              # True  — cached
a, b = 257, 257
print(a is b)              # often False (depends on compilation unit)

x = "hello world"
y = "hello world"
print(x is y)              # True in a single module; don't rely on it
print(x == y)              # True — always, and this is what you meant
```

**Rule:** use `is` **only** for singletons — `None`, `True`, `False`, and your own sentinel objects.
Linters flag `x is 0` and `x == None` for exactly this reason.

> **Java contrast.** Identical to `==` (reference) vs `.equals()` (value), including the analogous
> `Integer` cache for `-128..127` that makes `Integer.valueOf(127) == Integer.valueOf(127)` true and
> `128` false. If you've been bitten by that in Java, it's the same bug.

---

## Complexity cheat sheet

| Operation | `list` | `tuple` | `dict` | `set` | `deque` |
|---|---|---|---|---|---|
| Index `x[i]` | O(1) | O(1) | — | — | O(n) |
| `append` / `add` | O(1)* | — | O(1)* | O(1)* | O(1) |
| `insert(0, x)` | **O(n)** | — | — | — | O(1) (`appendleft`) |
| `pop()` (end) | O(1) | — | O(1) (`popitem`) | O(1) | O(1) |
| `pop(0)` (front) | **O(n)** | — | — | — | O(1) (`popleft`) |
| `x in c` | **O(n)** | **O(n)** | O(1)* | O(1)* | O(n) |
| `del c[k]` | O(n) | — | O(1)* | O(1)* | O(n) |
| Memory per element | high | lowest | highest | high | medium |

`*` = amortised average; worst case O(n) on hash collision or resize.

**The single most common real-world perf bug in this table:** using `x in some_list` inside a loop.
That's O(n·m). Convert the list to a `set` once and it becomes O(n).

---

## Worked example 1 — sliding-window maximum with `deque`

A genuine favourite in coding rounds, and the clearest demonstration of why `deque` exists. The
deque stores **indices**, kept in decreasing order of their values (a monotonic queue), so the front
is always the max of the current window. Each index is pushed and popped at most once → **O(n)**.

```python
from collections import deque

def max_sliding_window(nums, k):
    dq, out = deque(), []            # dq holds indices; values at them decrease
    for i, n in enumerate(nums):
        while dq and nums[dq[-1]] < n:
            dq.pop()                 # anything smaller can never be the max again
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()             # front has slid out of the window
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out

print(max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3))   # [3, 3, 5, 5, 6, 7]
```

The naive `max(nums[i:i+k])` per window is O(n·k). Be ready to state both complexities.

---

## Worked example 2 — group anagrams with `defaultdict` + tuple keys

```python
from collections import defaultdict

def group_anagrams(words):
    groups = defaultdict(list)
    for w in words:
        groups[tuple(sorted(w))].append(w)   # tuple is hashable; list would not be
    return list(groups.values())

print(group_anagrams(["eat", "tea", "tan", "ate", "nat", "bat"]))
# [['eat', 'tea', 'ate'], ['tan', 'nat'], ['bat']]
```

Two things to say unprompted: the key **must** be a tuple (a `list` is unhashable), and sorting each
word is O(m log m), so the total is O(n·m log m). The O(n·m) alternative is a 26-slot count tuple as
the key — mention it as the optimisation if asked for one.

---

## Hands-on drills

Do these in a REPL and predict the output *before* running:

1. Build a dict of 1,000,000 entries in a loop and time it; then time the same with
   `dict.fromkeys(range(1_000_000))`. Explain the gap using the resize/rehash behaviour.
2. Write `x in big_list` inside a loop over another 10,000-element list. Time it. Convert
   `big_list` to a set and time it again. Report the speedup as a ratio, not a feeling.
3. Take `d = {"a":1,"b":2,"c":3}`, run `d["a"] = 99`, then `d["z"] = 0`. Print `list(d)` after each.
   Explain the positions using the compact-layout entries array.
4. Create `@dataclass class P: x: int; y: list = []` and observe the error. Fix it with
   `field(default_factory=list)` and explain what the dataclass machinery is protecting you from.
5. Implement `LRU` from Q12 and add a `stats()` method returning hit/miss counts. Compare against
   `functools.lru_cache`'s `cache_info()`.
6. Write a `frozenset`-keyed memo for a function taking a set of permissions; call it with the same
   permissions in different orders and prove you get one cache entry.

---

## The 60-second spoken answer

> "Lists are dynamic arrays — O(1) append, O(n) insert at the front, O(n) membership. Tuples are
> fixed-size and hashable if their contents are, so they work as dict keys. Dicts and sets are
> open-addressing hash tables; since 3.6 dicts use a compact two-array layout, which is why they're
> insertion-ordered — guaranteed from 3.7 — and O(1) average for get/set/delete. For queues I use
> `deque` because list `pop(0)` is O(n). From `collections` I lean on `Counter` for frequency and
> top-k, `defaultdict` for grouping — remembering that even a read inserts the key — `deque` with
> `maxlen` for sliding windows, and `ChainMap` for layered config. The two traps I always check for
> in review are mutable default arguments and `x in list` inside a loop."
