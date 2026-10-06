# Deep Dive 24 — Python Basics That Still Get Asked at Senior Level

> Runnable companion: [`01_python_core/14_python_basics_essentials.py`](../01_python_core/14_python_basics_essentials.py)
> Related deep dives: [01 — Data structures](01_data_structures_collections.md) ·
> [22 — Variable scope](22_variable_scope_namespaces.md) ·
> [09 — Memory management notes in 01](01_data_structures_collections.md) ·
> [21 — Java → Python bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

These questions are not warm-ups. A senior interviewer asks "`is` vs `==`" because they've debugged
a production incident caused by `if user.discount:` swallowing a legitimate 0% discount, and they
want to know whether you've debugged one too.

So for every item below, the thing being tested is **"can you name the production bug this
causes?"** — not whether you can recite the definition. The answers here are organised that way:
rule, then the bug, then the fix.

The second thing being tested is **precision of language**. "Python passes by reference" is wrong
and an interviewer will hear it. "Python passes a reference to an object by value — so I can always
mutate the caller's object, never rebind the caller's name" is right and takes the same breath.

---

## Must-know points

- **`is` compares identity, `==` compares value.** Use `is` only for `None`, `True`, `False` and
  sentinels. CPython caches small ints (−5…256) and some strings — an implementation detail you must
  never rely on.
- **Pass-by-object-reference**: you can always **mutate** the caller's object; you can never
  **rebind** the caller's name.
- **Mutable default arguments are evaluated once, at `def` time.** Use `None` as the sentinel.
- **Falsy values**: `None, False, 0, 0.0, 0j, "", [], {}, set(), ()`. `if not x` and `if x is None`
  are different questions — confusing them silently drops zeros and empty strings.
- **`=` never copies.** `copy()`/`dict(d)`/`d[:]`/`{**d}` are **shallow** — nested objects stay
  shared. `copy.deepcopy` is deep, slow, and cycle-aware.
- **`*args` collects positionally, `**kwargs` collects by keyword**; the same `*`/`**` at a call site
  **unpacks**. `/` ends positional-only params, `*` starts keyword-only ones.
- **Strings are immutable** — `+=` in a loop is O(n²); `"".join(parts)` is O(n).
- **Sort is stable**; `sorted()` returns a new list, `list.sort()` returns `None` and mutates. A
  tuple key sorts by each element in turn.
- **Type hints are not enforced at runtime.** mypy/pyright in CI; Pydantic at the edges.
- `//` **floors toward −infinity** (so `-7 // 2 == -4`, unlike Java's `-3`), and `%` takes the
  **divisor's sign**.
- Floats are binary: `0.1 + 0.2 != 0.3`. Money uses `decimal.Decimal` or integer minor units.

---

## Interview questions and full answers

### Q1. `is` vs `==` — and why does `is` sometimes appear to work?

`==` calls `__eq__` (value equality). `is` compares `id()` — whether both names point at the *same
object*.

```python
a, b = [1, 2, 3], [1, 2, 3]
a == b      # True  — same contents
a is b      # False — two distinct objects
c = a
c is a      # True  — just another name for the same list
```

**Why `is` sometimes looks right:** CPython caches small objects.

```python
x, y = 256, 256
x is y            # True  — ints −5..256 are pre-created at interpreter start
x, y = 1000, 1000
x is y            # True in a single line of a script (constant folding in one code object)
                  # False when built separately, e.g. int("1000") is int("1000")
"ab" is "ab"      # True  — compile-time interning of identifier-like literals
"a b" is "a b"    # may be False — not identifier-like
```

**All of that is an implementation detail.** PyPy differs; CPython versions differ. Python 3.8+
actually emits a `SyntaxWarning: "is" with a literal` when you write `x is 1000`, which tells you how
common the mistake is.

**The one legitimate pattern — a sentinel**, and this is the thing worth volunteering:

```python
MISSING = object()               # unique, cheap, never equal to anything else

def update(name=MISSING, nickname=MISSING):
    """`None` is a MEANINGFUL value here: it means 'clear this field'. Only a distinct sentinel
    can tell 'caller said None' from 'caller said nothing'."""
    if name is not MISSING:
        record.name = name       # includes the case name=None → clear it
```

With `None` as the default, `update(nickname=None)` ("remove my nickname") is indistinguishable from
`update()` ("don't touch my nickname") — a real bug class in PATCH endpoints. Pydantic solves the
same problem with `model_fields_set`, and `dataclasses` with `MISSING`.

**Why `is None` rather than `== None`:** `None` is a singleton, so `is` is both correct and faster —
and `== None` can be hijacked by a class with a weird `__eq__` (numpy arrays return an *array* of
booleans, which then raises on `if`).

---

### Q2. Is Python pass-by-value or pass-by-reference?

**Neither — it's pass-by-object-reference** (also called call-by-sharing). The parameter name becomes
a *new local name bound to the same object*.

```python
def try_to_rebind(items, number):
    items = ["rebound"]          # rebinds the LOCAL name only
    number = 999
def mutate_in_place(items):
    items.append("appended")     # mutates the SAME object the caller holds

lst, num = ["a"], 1
try_to_rebind(lst, num);  lst, num     # (['a'], 1)            — unchanged
mutate_in_place(lst);     lst          # ['a', 'appended']     — changed
```

**The rule, in one line: you can always mutate the caller's object; you can never rebind the
caller's name.** Immutables (`int`, `str`, `tuple`, `frozenset`) appear to be "passed by value" only
because there is no mutating operation to observe.

Note that `+=` is the confusing case, because it's two different things:

```python
def f(xs, n):
    xs += [1]        # list.__iadd__ → IN-PLACE extend. Caller SEES it.
    n  += 1          # int has no __iadd__ → rebinds a local. Caller does NOT see it.
```

**The practical rules this generates:**

1. **Don't mutate arguments unless the function name says so.** `sort_in_place(rows)` is honest;
   `validate(rows)` quietly deleting bad rows is not.
2. **Return new data instead.** It's testable, thread-safe, and composable.
3. **If you must accept a mutable and keep it, copy at the boundary:**
   `self.items = list(items)` — otherwise the caller can mutate your object's internals later.
4. **Document it in the type**: `Sequence[str]` says "I only read"; `list[str]` says "I might write".

---

### Q3. What's the mutable default argument bug?

**Default values are evaluated once, when the `def` statement executes** — not per call. So a
mutable default is a single shared object that lives on the function:

```python
def broken(item, bucket=[]):
    bucket.append(item)
    return bucket

broken("a")     # ['a']
broken("b")     # ['a', 'b']    ← 'a' leaked in from the previous call
broken.__defaults__             # (['a', 'b'],) — you can SEE the shared object
```

The fix is the `None` sentinel:

```python
def correct(item, bucket=None):
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket
```

The same trap in a dataclass, where it's at least loud:

```python
@dataclass
class Order:
    items: list[str] = []                        # ValueError at class creation — Python stops you
    items: list[str] = field(default_factory=list)   # the correct spelling
```

**Where it actually bites:** `def __init__(self, handlers=[])` — every instance shares one handler
list, so registering a handler on one object registers it on all of them. And
`def fetch(cache={})` used as a poor man's memo, which then never evicts and leaks for the process
lifetime.

**The one time it's deliberate**, and knowing this is the senior half of the answer: the
evaluate-once behaviour is exactly what makes `lambda i=i: i` fix the late-binding closure bug
([22 — Variable scope](22_variable_scope_namespaces.md), Q7), and it's a legitimate micro-optimisation
for hoisting a global lookup into a local (`def f(x, _len=len):`). It's a sharp tool, not a wart.

---

### Q4. What is truthiness, and what bug does it cause?

An object is falsy if `__bool__` returns `False`, or (absent that) `__len__` returns `0`. The falsy
built-ins: `None`, `False`, `0`, `0.0`, `0j`, `""`, `[]`, `{}`, `set()`, `()`, `range(0)`, and
`datetime.time(0, 0)` before 3.5.

**The bug:**

```python
def apply_discount(discount=None):
    if not discount:                 # 0 is falsy → a deliberate 0% discount is ignored
        return "no discount"
    return f"{discount}% off"

apply_discount(0)       # "no discount"  ← WRONG. The caller explicitly said 0.
```

```python
def apply_discount(discount=None):
    if discount is None:             # test for ABSENCE, not for falsiness
        return "no discount"
    return f"{discount}% off"
```

The same bug with other types, each of which I've seen in production:

- `if not user.name:` — rejects a legitimately empty optional string
- `if not items:` vs `if items is None:` — "no filter supplied" vs "filter matched nothing", which
  are completely different queries
- `if not count:` — treats a count of 0 as "not counted yet"
- `if request.body:` — an empty-but-valid JSON `{}` is falsy
- `os.environ.get("RETRIES") or 3` — the string `"0"` is truthy so this one *works*, but
  `int(os.environ.get("RETRIES", 3)) or 3` turns a configured 0 into 3

**The rule: `if not x` asks "is this empty-or-zero-or-absent?". `if x is None` asks "was this
supplied?". Use the one you mean.**

And on `or` for defaults: `value = given or default` is idiomatic but inherits the same flaw. The
safe spellings are `value = default if given is None else given`, or
`d.get(key, default)` when the key may be absent, or `d[key] if key in d else default` when `None` is
a valid stored value.

---

### Q5. Shallow vs deep copy — and when does the difference matter?

```python
original = {"user": "ravi", "roles": ["admin", "dev"]}
assigned = original                 # NOT a copy — another name for the same dict
shallow  = original.copy()          # new dict, SAME inner list object
deep     = copy.deepcopy(original)  # new dict, new inner list

shallow["roles"].append("leaked")
original["roles"]                   # ['admin', 'dev', 'leaked']  ← the list was shared
deep["roles"]                       # ['admin', 'dev']            ← untouched
```

Equivalent shallow copies: `dict(d)`, `{**d}`, `d.copy()`, `copy.copy(d)`; for lists `lst[:]`,
`list(lst)`, `lst.copy()`.

**When it matters, concretely:**

- **Config defaults.** `config = {**DEFAULTS, **overrides}` is shallow, so a nested
  `DEFAULTS["db"]["pool"]` mutated by one request is changed for every subsequent request in that
  process. This is a genuinely nasty bug because it only appears under load.
- **Test fixtures.** A module-level `SAMPLE_ORDER` dict mutated by test A breaks test B, and the
  failure depends on ordering. Use a factory function or `deepcopy` in the fixture.
- **Caching.** Returning the cached object lets the caller mutate your cache. Return a copy, or make
  the cached value immutable.
- **Kafka/HTTP handlers.** Mutating the decoded payload before passing it on means the retry sees the
  modified version, not the original.

**The costs of `deepcopy`**, which is the follow-up: it's slow (it walks the whole graph and keeps a
memo dict to handle cycles), it calls `__deepcopy__`/`__reduce__` so it can trip on objects holding
sockets, file handles or DB connections, and it will happily copy an enormous object graph you didn't
mean to.

**What I use instead, in order of preference:**

1. **Immutability** — a frozen dataclass or `tuple`; nothing to copy. Best answer when it fits.
2. **A factory function** — `def default_config(): return {"db": {"pool": 5}}`. Fresh every call,
   explicit, fast.
3. **An explicit shallow copy at the boundary** when you know the structure is flat.
4. **`deepcopy`** when the structure is genuinely nested, arbitrary, and you need isolation.
5. **`json.loads(json.dumps(obj))`** — faster than deepcopy for plain JSON data, but loses types
   (tuples become lists, `Decimal` and `datetime` break). Know the trade-off before using it.

---

### Q6. Explain `*args`, `**kwargs`, and positional-only / keyword-only parameters.

Same symbols, two directions. **In a signature they collect; at a call site they unpack.**

```python
def describe(required, *args, mode="fast", **kwargs):
    return required, args, mode, kwargs

describe(1, 2, 3, mode="slow", retries=5)     # (1, (2, 3), 'slow', {'retries': 5})

def forward(*args, **kwargs):                  # the wrapper signature
    return describe(*args, **kwargs)           # UNPACKING here
```

Note that **anything after `*args` is automatically keyword-only** — that's why `mode="fast"` above
can't be passed positionally.

```python
def strict(a, b, /, c, *, d):
    ...
#          ^^^^^^^   ^   ^^^
#          positional-only | c: either | keyword-only
strict(1, 2, 3, d=4)        # ✅
strict(a=1, b=2, c=3, d=4)  # ❌ TypeError: positional-only arguments passed as keywords
strict(1, 2, 3, 4)          # ❌ TypeError: takes 3 positional arguments but 4 were given
```

**Why the markers matter — this is the API-design half of the answer:**

- **`*` (keyword-only)** lets you add, reorder or rename parameters later without breaking callers,
  and it forces readable call sites. `create_user(name, admin=True)` reads; `create_user(name, True)`
  doesn't. Every boolean flag should be keyword-only.
- **`/` (positional-only)** frees you to rename a parameter without breaking anyone, and it's how
  C-implemented builtins behave (`len(obj)`, not `len(obj=x)`). Use it for arguments whose name
  carries no information.

**Where `*args, **kwargs` is right:** a decorator wrapper, a thin proxy/adapter, and cooperative
`super().__init__(**kwargs)` in a mixin chain
([06 — OOP and MRO](06_oop_inheritance_mro.md)).

**Where it's wrong:** as your function's public signature. `def process(**kwargs)` destroys
autocomplete, type checking and the error message when someone typos a key — the typo silently lands
in `kwargs` and is ignored. If you catch yourself writing `**kwargs` to avoid naming parameters,
write a dataclass or a `TypedDict` instead.

---

### Q7. Why is `+=` on strings in a loop a performance bug?

Strings are immutable, so every concatenation allocates a **new** string and copies both operands.
In a loop that's O(n²) total work:

```python
slow = ""
for p in parts:          # n iterations, each copying the accumulated string
    slow += p + ","      # O(n²)

fast = ",".join(parts) + ","    # one pass, one allocation: O(n)
```

At 100 parts nobody notices. At 100,000 parts it's the difference between milliseconds and tens of
seconds, and it's a classic cause of "the report endpoint times out".

**The honest footnote:** CPython has an optimisation that mutates a string in place when its
refcount is exactly 1, so a tight `s += x` loop *sometimes* behaves linearly. It's fragile — it
disappears the moment anything else holds a reference (a list, a closure, a debugger) — and it
doesn't exist in PyPy. Never rely on it.

**What to use instead:**

| Situation | Reach for |
|---|---|
| joining a known collection | `",".join(parts)` |
| building incrementally | append to a `list`, `join` once at the end |
| very large / streaming output | `io.StringIO` and `.write()`, or `yield` the chunks |
| writing to a file or socket | write each chunk — don't build the whole thing |
| formatting a few values | an f-string |

The same principle generalises: **`list + list` in a loop is O(n²); `list.append` is amortised
O(1).** Any "immutable type accumulated in a loop" is the same bug (tuples, `bytes`, `frozenset`).
For bytes, `bytearray` is the mutable buffer.

While we're here, f-string formatting worth knowing:

```python
f"{1234.5678:,.2f}"   # '1,234.57'      thousands separator + 2dp
f"{0.0825:.2%}"       # '8.25%'
f"{'total':>10}"      # '     total'    right-align in 10 columns
f"{value!r}"          # repr(), which quotes strings — use it in log messages
f"{255:#x}"           # '0xff'
f"{amount=}"          # 'amount=1234.5678'  — the debug form, 3.8+
```

---

### Q8. Explain sorting: key functions, stability, `sorted()` vs `.sort()`.

```python
orders = [{"id": 3, "total": 50}, {"id": 1, "total": 50}, {"id": 2, "total": 120}]
sorted(orders, key=lambda o: (-o["total"], o["id"]))      # total DESC, then id ASC → [2, 1, 3]
```

- **`key=`** is called **once per element** (unlike a comparator, which is called O(n log n) times) —
  so `key=expensive` is fine, `cmp_to_key(expensive)` is not.
- **A tuple key** sorts by each element in turn. Negate a number to reverse just that field;
  `reverse=True` reverses *everything*, which is why the tuple trick exists.
- **For mixed directions on non-numeric keys**, exploit stability: sort by the secondary key first,
  then by the primary. Two passes, both stable, correct result.
- **Stability** means equal keys keep their original relative order. Guaranteed by the language (it's
  Timsort), and it's what makes multi-pass sorting and "sort the table by this column" UIs work.
- **`sorted()` returns a new list** from any iterable; **`list.sort()` returns `None`** and mutates.
  `x = lst.sort()` giving `None` is a top-5 beginner bug — and the signature is deliberate, to signal
  the mutation.
- `operator.itemgetter("total")` / `attrgetter("total")` are faster than an equivalent lambda (they're
  C-implemented) and read better for multi-key sorts: `itemgetter("region", "id")`.
- `min`/`max`/`heapq.nlargest` take the same `key=`, and `nlargest(10, data, key=...)` is O(n log k)
  — the right answer for top-k over a large stream rather than sorting everything.

---

### Q9. Are type hints enforced? What are they for?

**Not at runtime, at all:**

```python
@dataclass
class Order:
    id: int
    customer: str

bad = Order(id="not-an-int", customer=42)      # no error whatsoever
```

They're for:

1. **Static checking in CI** — mypy/pyright catch wrong signatures, `None` handling, incompatible
   overrides. This is the main payoff: the bug is found in the PR, not in production.
2. **Editor tooling** — autocomplete, inline errors, safe refactoring.
3. **Documentation that can't rot**, because the checker fails when it drifts.
4. **Runtime validation at the BOUNDARY** — which is a different thing. Pydantic/FastAPI *do*
   enforce hints, because they read `__annotations__` and generate validators:

```python
class OrderIn(BaseModel):
    id: int
    customer: str
# POST {"id": "abc"} → FastAPI returns 422 before your function body runs
```

**The design to describe: validate at the edges, trust inside.** Request bodies, config files, event
payloads and third-party responses get a Pydantic model. Internal functions get plain hints checked
by mypy. You don't pay validation cost on every internal call, and you never have unvalidated data
past the boundary. See [10 — Web frameworks](10_web_frameworks.md).

Modern syntax worth using:

```python
list[str]  dict[str, int]  tuple[int, ...]    # 3.9+ — no `typing.List` needed
int | None                                    # 3.10+ — replaces Optional[int]
from typing import TypedDict, Protocol, Literal, Final, Self
Status = Literal["PENDING", "SHIPPED"]        # better than a bare str for a small closed set
```

And `@dataclass`, which is where hints become load-bearing: the annotations *generate* `__init__`,
`__repr__` and `__eq__`. Note `field(default_factory=list)` is the dataclass spelling of the
`None`-sentinel fix from Q3, and that a field with no default can never follow one with a default.

---

### Q10. Which numeric and operator behaviours differ from what a Java developer expects?

```python
7 // 2      #  3
-7 // 2     # -4    ← FLOOR division: rounds toward −infinity. Java gives -3 (truncates toward 0)
-7 % 2      #  1    ← the sign follows the DIVISOR. Java gives -1
7 / 2       #  3.5  ← `/` is ALWAYS float division, even for two ints
2 ** 100            # exact — ints are arbitrary precision, no overflow, ever
0.1 + 0.2 == 0.3    # False — binary floating point, same as every other language
0 <= x < 10         # chained comparison; `x` is evaluated once
```

Each one, and why it matters:

- **Floor division and modulo**: `-7 // 2 == -4` and `-7 % 2 == 1`. Python's choice keeps the
  invariant `a == (a // b) * b + a % b` with a non-negative remainder for a positive divisor — which
  is what you want for hashing, ring buffers and "which shard/partition does this key go to?".
  Porting a Java hash-based partitioner directly will route negative hashes to the wrong shard.
- **No integer overflow**: `2 ** 100` is exact. A Java port relying on `int` wraparound (some hash
  functions do) will produce different values. `ctypes`/`numpy` fixed-width types exist when you
  need the wrap.
- **Floats are binary**: `0.1 + 0.2 == 0.30000000000000004`. **Never use `float` for money.** Use
  `decimal.Decimal("0.1")` (constructed from a *string*, not a float) or integer minor units
  (cents). For comparisons use `math.isclose(a, b)`.
- **Chained comparisons** read like maths and evaluate the middle operand once — so
  `lo <= f() < hi` calls `f()` once, which a naive `lo <= f() and f() < hi` would not.
- **`and`/`or` return an operand, not a bool**: `"" or "default"` → `"default"`; `0 and crash()` →
  `0` (short-circuited). Handy, and the source of the Q4 defaulting bug.
- **`==` on different numeric types compares values**: `1 == 1.0 == True` are all `True`, and
  `{1: "a", True: "b"}` is a **one-key dict** because `hash(1) == hash(True)`. That one shows up in
  real code when a dict is keyed by something that might be a bool.

---

### Q11. The loop idioms worth knowing cold.

```python
for i, name in enumerate(names, start=1):      # never `for i in range(len(names))`
    ...

list(zip(names, scores))                        # stops at the SHORTEST input — silently
list(zip(names, scores, strict=True))           # 3.10+: ValueError on a length mismatch
list(itertools.zip_longest(names, scores, fillvalue=0))

for key, value in d.items():                    # not `for key in d: d[key]`

for n in names:                                 # for/else: `else` runs if NO break happened
    if n == target:
        break
else:
    raise NotFound(target)                      # the "search miss" branch, no flag variable
```

- **`zip` truncating silently** is a real data bug: zipping a 1000-row list with a 999-row one
  silently drops a row. `strict=True` turns that into an error, and should be your default on data
  you didn't generate.
- **`for/else`** removes the `found = False` flag. Read `else` as "no break" — that's the only way
  the clause makes sense. (The same keyword on `try` means "no exception"; see
  [08 — Error handling](08_error_handling.md).)
- **Don't mutate a collection while iterating it.** `for k in d: del d[k]` raises
  `RuntimeError: dictionary changed size during iteration`; on a list it silently skips elements.
  Iterate a copy (`list(d)`) or build a new collection.
- `itertools` earns its keep: `batched(it, n)` (3.12+) for chunking, `islice` for paging a generator,
  `groupby` (on **sorted** input only), `chain` to flatten, `tee` to fork a stream.
  See [`01_python_core/04_generators_iterators.py`](../01_python_core/04_generators_iterators.py).

---

## Java contrast

| Java | Python |
|---|---|
| `==` on objects compares references; `.equals()` compares value | `is` compares identity; `==` compares value (`__eq__`) |
| `String` interning makes `==` sometimes work | small-int/string caching makes `is` sometimes work — same trap, same advice |
| Primitives pass by value, objects pass a reference by value | **everything** is an object; pass-by-object-reference |
| `int` overflows silently at 2³¹ | `int` is arbitrary precision — never overflows |
| `-7 / 2 == -3` (truncates toward zero) | `-7 // 2 == -4` (floors toward −infinity) |
| `-7 % 2 == -1` (sign of dividend) | `-7 % 2 == 1` (sign of divisor) |
| `if (x)` requires a boolean | any object is truthy/falsy — hence the `0`-is-falsy bug |
| `BigDecimal` for money | `decimal.Decimal` for money (or integer cents) |
| `StringBuilder` for loops | `list` + `"".join()`, or `io.StringIO` |
| Compiler enforces types | hints are advisory; mypy in CI + Pydantic at the boundary |
| Overloading by signature | one function; use default args, `*args`, or `functools.singledispatch` |
| `final` | nothing enforces it; `Final[int]` is checked only by a type checker |

---

## A worked example

A single function that steps on five of these traps, then the corrected version — this is the shape
of a real code review:

```python
# ------------------------------------------------------------------ BEFORE: five bugs
DEFAULT_CONFIG = {"retries": 3, "db": {"pool": 5}}

def process_orders(orders, config=DEFAULT_CONFIG, errors=[], discount=None):
    report = ""
    for i in range(len(orders)):                       # (5) un-Pythonic and error-prone
        order = orders[i]
        if not discount:                               # (1) a 0% discount is silently ignored
            total = order["amount"]
        else:
            total = order["amount"] * (1 - discount / 100)
        if total > config["db"]["pool"] * 100:
            config["db"]["pool"] += 1                  # (2) MUTATES the module-level default
            errors.append(order["id"])                 # (3) shared default list, grows forever
        report += f"{order['id']}: {total}\n"          # (4) O(n²) string building
    return report, errors
```

```python
# ------------------------------------------------------------------ AFTER
from dataclasses import dataclass, field
from decimal import Decimal

@dataclass(frozen=True)                  # frozen: nothing can mutate it, so no copy needed
class Config:
    retries: int = 3
    pool_size: int = 5

@dataclass
class Result:
    report: str
    failed_ids: list[str] = field(default_factory=list)   # the None-sentinel fix, dataclass style

def process_orders(orders, config: Config | None = None,
                   discount: Decimal | None = None) -> Result:
    """`config=None` means 'use defaults'; `discount=None` means 'no discount', and
    `discount=Decimal(0)` correctly means 'an explicit 0%'."""
    config = config or Config()           # safe here: Config() is never falsy
    failed: list[str] = []
    lines: list[str] = []                 # accumulate in a LIST, join once

    for order in orders:                  # iterate the objects, not the indices
        amount = Decimal(str(order["amount"]))        # Decimal from a STRING, never a float
        total = amount if discount is None else amount * (1 - discount / 100)
        if total > config.pool_size * 100:
            failed.append(order["id"])
        lines.append(f"{order['id']}: {total:.2f}")

    return Result(report="\n".join(lines), failed_ids=failed)
```

**What each fix buys:**

| Bug | Fix | Why it matters |
|---|---|---|
| `if not discount` | `if discount is None` | a deliberate 0% discount now works |
| mutating `DEFAULT_CONFIG` | `frozen=True` dataclass | one request can no longer change every later request's config |
| `errors=[]` default | `field(default_factory=list)` / a fresh local | no cross-call state leak |
| `report +=` in a loop | `list` + `"\n".join` | O(n) instead of O(n²) |
| `range(len(...))` | iterate the objects | shorter, no index errors |
| float money | `Decimal(str(...))` | `0.1 + 0.2` problems don't reach an invoice |
| `-> tuple` | a `Result` dataclass | callers stop unpacking positionally and the return is self-documenting |

Note `config = config or Config()` is only safe because `Config()` is never falsy. For a plain int or
string parameter it would be the Q4 bug again — which is exactly the kind of case-by-case judgement
the interviewer is checking for.

---

## Hands-on drills

1. Build `MISSING = object()` and write a PATCH-style `update(name=MISSING)` that distinguishes
   "not supplied" from "supplied as None". Then try it with `None` as the default and watch the
   distinction vanish.
2. Write the `broken(item, bucket=[])` function, call it three times, then print
   `broken.__defaults__` and see the accumulated state on the function object.
3. Write `apply_discount` with `if not discount`, call it with `0`, `None`, `""` and `0.0`, and
   tabulate what each returns. Then fix it and re-tabulate.
4. Nest a dict two levels deep. Copy it with `=`, `.copy()`, `{**d}` and `deepcopy`, mutate the inner
   list through each, and record which outer objects changed.
5. Time `+=` vs `"".join()` over 200,000 parts with `time.perf_counter()`. Report the ratio. That
   number is your answer to "why does string concatenation matter?".
6. Write `strict(a, b, /, c, *, d)` and trigger both `TypeError`s. Then make a boolean flag
   keyword-only in a function you've actually written.
7. Sort a list of dicts by one field descending and another ascending, using a tuple key. Then do it
   with two stable passes and confirm the results match.
8. Add `index: int` with no default *after* a defaulted field in a dataclass; read the `TypeError`.
9. Zip two lists of different lengths with and without `strict=True`. Then do it with
   `zip_longest`.
10. Compute `-7 // 2`, `-7 % 2`, `7 // -2`, `7 % -2` and the Java equivalents. Then write a shard
    function `hash(key) % n` and reason about whether a negative hash can route to a negative index.
11. Build `{1: "a", True: "b", 1.0: "c"}` and print it. Explain the length in one sentence.
12. Write `deep_merge(base, override)` that recursively merges nested dicts, override winning, and
    **never** mutates either input. Prove it with a test that mutates the result and asserts both
    inputs are unchanged.

---

## The 60-second spoken answer

> "`is` compares identity, `==` compares value, and I only use `is` for `None`, `True`, `False` and
> sentinels — small ints and short strings are cached in CPython, so `is` sometimes *looks* right,
> and that's an implementation detail I never rely on. The one place I reach for a sentinel is a
> PATCH-style API where `None` is a meaningful value: `MISSING = object()` is the only way to tell
> 'the caller said None' from 'the caller said nothing'.
>
> Python is pass-by-object-reference: I can always mutate the caller's object, I can never rebind the
> caller's name. So I don't mutate arguments unless the function name says I will, and I copy at the
> boundary if I'm going to keep a mutable the caller handed me.
>
> Default arguments are evaluated once at `def` time, so a mutable default is shared across every
> call — `None` as the sentinel, or `field(default_factory=list)` in a dataclass. And truthiness
> causes the bug I see most often: `if not discount` silently swallows a deliberate 0, and `if not
> items` can't tell 'no filter supplied' from 'filter matched nothing'. `if not x` and `if x is None`
> answer different questions.
>
> `=` never copies, and `.copy()`/`{**d}` are shallow, so a nested config default mutated by one
> request changes every later request in that process — which only shows up under load. I prefer
> immutability or a factory function over reaching for `deepcopy`, which is slow and will happily
> walk an object graph holding a DB connection.
>
> Strings are immutable, so `+=` in a loop is O(n²) — I accumulate in a list and `join` once. Sorting
> is stable with a `key=` called once per element, `sorted()` returns a new list and `.sort()`
> returns `None`. And type hints aren't enforced at runtime at all: mypy in CI for internal code,
> Pydantic at the boundaries. Validate at the edges, trust inside.
>
> Coming from Java the three that catch people are: `//` floors toward negative infinity so
> `-7 // 2` is `-4` not `-3` and `%` takes the divisor's sign — which matters the moment you port a
> hash-based sharding function; ints never overflow; and floats are binary, so money is `Decimal`
> or integer cents, never `float`."
