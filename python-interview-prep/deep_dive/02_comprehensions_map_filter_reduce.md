# Deep Dive 02 — Comprehensions, and `map` / `filter` / `reduce`

> Runnable companions: [`01_python_core/02_comprehensions.py`](../01_python_core/02_comprehensions.py) ·
> [`01_python_core/10_map_filter_reduce.py`](../01_python_core/10_map_filter_reduce.py)
> Related deep dives: [Generators](04_generators_iterators.md) · [Pandas](09_pandas.md) · [Java bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

Comprehensions are a readability question dressed up as a syntax question. Everyone can write
`[x*x for x in xs]`. What separates candidates is knowing **when not to**, understanding the **scope
rules**, spotting the **hidden quadratic cost** in an innocent-looking one-liner, and being able to
explain **why a comprehension is faster than the equivalent loop** in bytecode terms.

`map`/`filter`/`reduce` almost always comes up with a Java or Scala background on the CV, because
the interviewer wants to know whether you've mapped Streams onto Python idiomatically or are writing
Java in Python. The correct Python answer is nuanced: `map`/`filter` are fine and sometimes
preferable; `reduce` was **deliberately demoted out of builtins in Python 3** and is usually the
wrong tool.

---

## Must-know points

- **Four comprehension forms**: `[list]`, `{set}`, `{k: v for ...}` dict, and `(generator
  expression)`. The first three build the whole collection eagerly; the generator expression is lazy.
- **Nested loops read left-to-right**, in the same order you'd write nested `for` statements.
- **`x if cond else y` goes *before* the `for`** (it transforms every item);
  **a bare `if cond` goes *after* the `for`** (it filters items out).
- **Comprehensions have their own scope** in Python 3 — the loop variable does not leak. The walrus
  operator `:=` is a deliberate exception and binds in the *enclosing* scope.
- **A comprehension cannot contain `try`/`except`.** Wrap the risky call in a helper returning a
  sentinel, then filter the sentinel.
- **`map`/`filter` are lazy iterators in Python 3** (they were lists in Python 2). `reduce` lives in
  `functools`, not builtins.

---

## Part A — Comprehensions

### Q1. What are the four kinds of comprehension?

```python
nums = range(6)

print([n * n for n in nums])                # list  -> [0, 1, 4, 9, 16, 25]
print({n % 3 for n in nums})                # set   -> {0, 1, 2}  (deduplicated)
print({n: n * n for n in nums if n % 2})    # dict  -> {1: 1, 3: 9, 5: 25}
print(sum(n * n for n in nums))             # genexp-> 55, no list ever materialised
```

Note the last one: when a generator expression is the **sole argument** to a function, you can drop
the extra parentheses — `sum(x for x in xs)` rather than `sum((x for x in xs))`.

There is no "tuple comprehension". `(x for x in xs)` is a generator, not a tuple; use
`tuple(x for x in xs)` if you actually want a tuple.

---

### Q2. Why is a list comprehension usually faster than a `for` loop with `.append()`?

Because of what the bytecode does, not because of magic. The loop version must, **on every
iteration**:

1. `LOAD_FAST result` — look up the list,
2. `LOAD_METHOD append` — perform an attribute lookup on it,
3. `CALL_METHOD` — execute a full Python-level method call.

The comprehension compiles to a specialised opcode, **`LIST_APPEND`**, which appends directly to a
list held on the interpreter's value stack. No attribute lookup, no method call frame.

```python
import dis

def loop():
    out = []
    for i in range(3):
        out.append(i)
    return out

def comp():
    return [i for i in range(3)]

dis.dis(loop)   # look for LOAD_METHOD / CALL_METHOD inside the loop body
dis.dis(comp)   # look for LIST_APPEND
```

The gain is typically **10–30%** — a *constant-factor* win, not an algorithmic one. Both are O(n).
Say that explicitly, because the trap in this question is a candidate who implies comprehensions
change complexity. And note: readability is the better reason to use one. If the comprehension is
harder to read than the loop, the loop wins.

> In CPython 3.12, PEP 709 *inlines* comprehensions — they no longer create a separate function
> frame, which removes the call overhead and speeds them up further (roughly 2× for small
> comprehensions). The loop variable still does not leak.

---

### Q3. How do you read a nested comprehension?

**Write the `for` clauses in exactly the order you'd nest the loops.** Left-to-right, outermost
first. The expression that gets collected sits at the far left.

```python
matrix = [[1, 2, 3], [4, 5, 6]]

flat = [x for row in matrix for x in row]
# equivalent to:
#   result = []
#   for row in matrix:          <- first for clause
#       for x in row:           <- second for clause
#           result.append(x)    <- the leading expression
print(flat)          # [1, 2, 3, 4, 5, 6]
```

The confusing case is a comprehension **nested inside the expression**, which reads in the opposite
direction:

```python
transposed = [[row[i] for row in matrix] for i in range(3)]
print(transposed)    # [[1, 4], [2, 5], [3, 6]]
```

Here the *outer* comprehension iterates `i` and the *inner* one builds each row. Two levels is the
practical limit; beyond that use a loop or `itertools`.

A later `for` clause can reference variables bound by an earlier one, which makes triangular
iteration easy:

```python
pairs = [(i, j) for i in range(4) for j in range(i)]
print(pairs)   # [(1,0), (2,0), (2,1), (3,0), (3,1), (3,2)]
```

---

### Q4. Where do `if` and `if/else` go?

This is the single most-confused piece of comprehension syntax, and the reason is that the two
constructs are different things that happen to share a keyword.

- **A filtering `if` goes after the `for`.** It is part of the comprehension grammar and *removes*
  items.
- **A conditional expression `a if cond else b` goes before the `for`.** It is an ordinary Python
  expression and *transforms* every item. It must have an `else`, because an expression must produce
  a value.

```python
nums = [1, 2, 3, 4, 5]

evens  = [n for n in nums if n % 2 == 0]                     # filter -> [2, 4]
labels = ["even" if n % 2 == 0 else "odd" for n in nums]     # transform -> 5 items

# combine both: transform the survivors of a filter
big_labels = ["big" if n > 3 else "small" for n in nums if n % 2]   # ['small','small','big']
```

Multiple filters chain as an implicit AND: `[n for n in nums if n % 2 if n > 2]` is the same as
`if n % 2 and n > 2`.

---

### Q5. Does the loop variable leak into the enclosing scope?

**Not in Python 3.** Each comprehension executes in its own implicit function scope, so the loop
variable is local to it and any same-named outer variable is untouched. (This was *not* true of list
comprehensions in Python 2, which is where the folklore comes from.)

```python
x = "outer"
squares = [x * x for x in range(3)]
print(x)          # 'outer' — untouched
```

**The walrus operator `:=` is a deliberate exception.** It binds in the *enclosing* scope on
purpose, which is precisely what makes it useful for capturing a value out of a comprehension:

```python
data = [3, 8, 1]
if any((big := n) > 5 for n in data):
    print(big)     # 8 — leaked on purpose
```

The most useful walrus pattern in a comprehension is **computing once and using twice**, avoiding a
duplicated expensive call:

```python
# BAD: expensive() runs twice per surviving item
result = [expensive(x) for x in items if expensive(x) is not None]

# GOOD: runs once
result = [y for x in items if (y := expensive(x)) is not None]
```

---

### Q6. What is the late-binding closure trap?

**Closures capture variables, not values.** A lambda created inside a loop holds a reference to the
loop variable; by the time the lambda is *called*, the loop has finished and the variable holds its
final value. So every lambda sees the same last value.

```python
fns = [lambda: i for i in range(3)]
print([f() for f in fns])          # [2, 2, 2]  <- all see the final i
```

The standard fix is to bind the current value as a **default argument**, because defaults are
evaluated at definition time (the same mechanism behind the mutable-default bug — see
[Deep Dive 01 Q7](01_data_structures_collections.md#q7-what-is-the-classic-mutable-default-argument-bug)):

```python
fns = [lambda i=i: i for i in range(3)]
print([f() for f in fns])          # [0, 1, 2]
```

`functools.partial(lambda i: i, i)` works too and is arguably cleaner because it doesn't add a fake
parameter to the signature.

This is not academic: it bites whenever you build a list of callbacks, event handlers, retry
closures, or `Depends()` providers in a loop.

> **Java contrast.** Java sidesteps this by requiring captured locals to be effectively final — the
> compiler simply refuses the equivalent code. Python allows it and gives you the surprising result.

---

### Q7. When should you NOT use a comprehension?

Five concrete cases:

1. **Side effects.** `[print(x) for x in xs]` builds a throwaway list of `None`s to do I/O. Use a
   plain `for` loop. If the result isn't used, it isn't a comprehension — it's a loop in disguise.
2. **More than two levels of nesting**, or a filter condition longer than the expression. Readability
   collapses fast.
3. **Per-item exception handling** — comprehensions cannot hold `try`/`except` (see Q8).
4. **Large results iterated once.** Use a generator expression and stay at O(1) memory.
5. **Hidden quadratic cost.** See Q9 — the most important one.

---

### Q8. How do you handle a function that may fail for some items?

You can't put `try`/`except` in a comprehension, so **push the error handling into a small helper**
that returns a sentinel, then filter the sentinel out. The walrus makes this a single pass:

```python
def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None

raw = ["1", "x", "3"]
nums = [n for s in raw if (n := to_int(s)) is not None]
print(nums)      # [1, 3]
```

If `None` is a legitimate result, use a unique sentinel object so you can distinguish them:

```python
_FAILED = object()

def safe(fn, x):
    try:
        return fn(x)
    except Exception:
        return _FAILED

results = [y for x in raw if (y := safe(int, x)) is not _FAILED]
```

In production you'd normally also **log** the failures, which pushes you back to a plain loop — and
that's the right call. Silently dropping bad records is how data pipelines lose data without anyone
noticing.

---

### Q9. Count word frequency with a dict comprehension — what's wrong with the obvious version?

```python
words = "a b a c b a".split()

# Looks clever, is O(n * k) — count() rescans the whole list for every unique word
freq = {w: words.count(w) for w in set(words)}

# Idiomatic and O(n) — single pass
from collections import Counter
freq = Counter(words)
```

Interviewers plant this one specifically to see whether you spot the **hidden quadratic cost**.
`list.count()` is O(n), and calling it once per unique word makes the whole thing O(n·k). With
10,000 log lines and 3,000 unique messages that's 30 million comparisons for something `Counter`
does in 10,000.

The same trap in other clothing: `[x for x in a if x in b]` where `b` is a **list** — O(len(a) ·
len(b)). Convert `b` to a `set` first and it becomes O(len(a)).

---

### Q10. Build a dict from two lists.

```python
keys, vals = ["a", "b"], [1, 2]

print({k: v for k, v in zip(keys, vals)})   # works
print(dict(zip(keys, vals)))                # simpler — prefer this
```

The detail worth volunteering: **`zip` stops silently at the shortest input.** If your two lists are
meant to be the same length, a mismatch is a bug you want to hear about, not absorb:

```python
dict(zip(keys, vals, strict=True))     # Python 3.10+: raises ValueError on length mismatch
```

For the opposite behaviour — pad to the longest — use `itertools.zip_longest(keys, vals,
fillvalue=None)`.

---

## Part B — `map`, `filter`, `reduce`

### Q11. What do `map` and `filter` do, and how do they differ from comprehensions?

`map(func, iterable)` applies `func` to every item. `filter(pred, iterable)` keeps items where
`pred(item)` is truthy. **In Python 3 both return lazy iterators**, not lists — a common Python-2
holdover mistake.

```python
nums = [1, 2, 3, 4, 5]

squares = map(lambda x: x * x, nums)        # <map object> — nothing computed yet
evens   = filter(lambda x: x % 2 == 0, nums)

print(squares)                               # <map object at 0x...>
print(list(squares))                         # [1, 4, 9, 16, 25]
print(list(squares))                         # [] — EXHAUSTED, single-pass!
```

That second `list(squares)` returning `[]` is the classic bug. Like all iterators, a `map` object is
consumed once.

**Equivalences:**

| `map`/`filter` | Comprehension |
|---|---|
| `map(f, xs)` | `(f(x) for x in xs)` |
| `filter(p, xs)` | `(x for x in xs if p(x))` |
| `map(f, filter(p, xs))` | `(f(x) for x in xs if p(x))` |
| `map(f, xs, ys)` | `(f(x, y) for x, y in zip(xs, ys))` |

`filter(None, xs)` is a special form: passing `None` as the predicate filters out **falsy** values
(`0`, `""`, `[]`, `None`, `False`).

```python
print(list(filter(None, [1, 0, "a", "", None, 3])))   # [1, 'a', 3]
```

---

### Q12. Which is more Pythonic — `map`/`filter` or a comprehension?

The honest answer, and the one that shows judgement rather than dogma:

**Prefer a comprehension when the transform needs a lambda.** `map(lambda x: x * 2, xs)` is strictly
noisier and *slower* than `[x * 2 for x in xs]`, because the lambda adds a Python function call per
item that the comprehension inlines.

**Prefer `map` when you're passing an existing named function**, especially a C-implemented builtin.
There `map` is cleaner *and* genuinely faster, because it never enters the Python interpreter loop
for the call:

```python
# map wins — no lambda, C-level function
names = list(map(str.upper, ["ravi", "asha"]))
ids   = list(map(int, ["1", "2", "3"]))

# comprehension wins — needs an expression anyway
doubled = [x * 2 for x in nums]
```

**`map` also wins for multi-iterable zips** where a comprehension would need an explicit `zip`, and
for **lazy pipelines over huge inputs** — though a generator expression is equally lazy and usually
more readable.

Guido's own position, in the PEP 3100 rationale for demoting `reduce`, was that comprehensions are
the preferred spelling for map and filter. Treat `map`/`filter` as a tool you use when it is
*clearly* cleaner, not as a default.

> **Java contrast.** `stream().map(...).filter(...).collect(toList())` maps onto
> `[f(x) for x in xs if p(x)]`. Python has no `.stream()` because every iterable already is one.
> The big difference: Java streams are **fluent/chained**, Python's are **nested**
> (`map(f, filter(p, xs))` reads inside-out), which is exactly why comprehensions — which read
> left-to-right — won out idiomatically.

---

### Q13. What is `reduce` and why is it not a builtin any more?

`functools.reduce(func, iterable[, initial])` folds an iterable into a single value by repeatedly
applying a two-argument function: `f(f(f(a, b), c), d)`.

```python
from functools import reduce
import operator

nums = [1, 2, 3, 4]

print(reduce(operator.add, nums))         # 10
print(reduce(operator.mul, nums))         # 24
print(reduce(operator.add, nums, 100))    # 110 — with an initial value
print(reduce(operator.add, [], 0))        # 0   — initial saves you from TypeError on empty
```

**Always pass `initial` when the input can be empty.** Without it, `reduce` on an empty sequence
raises `TypeError: reduce() of empty iterable with no initial value`.

**Why it was moved out of builtins in Python 3**: Guido's argument was that almost every real use of
`reduce` is either (a) already a builtin — `sum`, `max`, `min`, `any`, `all`, `math.prod`,
`"".join` — or (b) unreadable. A `reduce` with a non-trivial lambda forces the reader to simulate
the fold in their head; an explicit loop does not.

```python
# Don't do this
total = reduce(lambda a, b: a + b, nums)
# Do this
total = sum(nums)

# Don't do this
product = reduce(lambda a, b: a * b, nums)
# Do this (3.8+)
import math
product = math.prod(nums)

# Don't do this
flat = reduce(lambda a, b: a + b, [[1,2],[3,4]])     # also O(n²) — builds a new list each step!
# Do this
flat = [x for sub in [[1,2],[3,4]] for x in sub]
```

That flatten example is worth remembering: `reduce` with `+` on lists is **quadratic**, because each
step allocates a new list. It's a correctness-adjacent performance bug, not just a style issue.

**When `reduce` is genuinely the right tool** — a non-associative or stateful fold with no builtin
equivalent, where the accumulator type differs from the element type:

```python
from functools import reduce

# Merge a list of config dicts, later ones winning
configs = [{"a": 1}, {"b": 2}, {"a": 9}]
merged = reduce(lambda acc, d: {**acc, **d}, configs, {})
print(merged)          # {'a': 9, 'b': 2}

# Walk a nested structure by a path
def dig(obj, key):
    return obj.get(key) if isinstance(obj, dict) else None

data = {"user": {"address": {"city": "Pune"}}}
print(reduce(dig, ["user", "address", "city"], data))    # 'Pune'
```

Even there, a three-line loop is defensible. Know `reduce`, use it sparingly, and be able to say
*why* you'd usually not.

> **Java contrast.** `Stream.reduce(identity, accumulator)` is the direct analogue and is used far
> more freely in Java, partly because Java lacks comprehensions. `Collectors.toMap`,
> `groupingBy` and `summingInt` map onto `dict`, `defaultdict(list)`/`itertools.groupby`, and `sum`
> respectively — reach for those, not `reduce`.

---

### Q14. What is `operator` and why use it with `map`/`reduce`/`sorted`?

The `operator` module exposes Python's operators as **C-implemented functions**, so you can pass them
where a callable is expected without paying for a lambda.

```python
import operator
from functools import reduce

reduce(operator.add, [1, 2, 3])                  # faster than lambda a, b: a + b

rows = [{"name": "b", "age": 30}, {"name": "a", "age": 25}]
rows.sort(key=operator.itemgetter("age"))        # instead of lambda r: r["age"]

class P:
    def __init__(self, n): self.n = n
ps = [P(3), P(1)]
ps.sort(key=operator.attrgetter("n"))            # instead of lambda p: p.n

# itemgetter with multiple keys returns a tuple — multi-column sort for free
rows.sort(key=operator.itemgetter("age", "name"))
```

`itemgetter`/`attrgetter`/`methodcaller` are the three you'll actually use, overwhelmingly as
`sorted(..., key=...)` arguments. Mentioning them signals fluency.

---

### Q15. How do `map`/`filter`/`reduce` compose into a data pipeline, and what's the Python-native alternative?

The functional composition reads inside-out and gets ugly fast:

```python
from functools import reduce
import operator

orders = [
    {"id": 1, "amount": 250, "status": "PAID"},
    {"id": 2, "amount":  90, "status": "FAILED"},
    {"id": 3, "amount": 410, "status": "PAID"},
]

# Functional style — read this from the inside out
total = reduce(operator.add,
               map(lambda o: o["amount"],
                   filter(lambda o: o["status"] == "PAID", orders)),
               0)
print(total)   # 660
```

The Python-native spelling of the same pipeline is a **generator expression fed to a builtin
reducer** — lazy, O(1) memory, and it reads left-to-right:

```python
total = sum(o["amount"] for o in orders if o["status"] == "PAID")
print(total)   # 660
```

This is the answer to give. It demonstrates you understand the functional decomposition *and* that
you know Python's preferred spelling. For genuinely staged pipelines over large or infinite inputs,
chain **generator functions** instead — see
[Deep Dive 04](04_generators_iterators.md#q10-build-a-lazy-data-pipeline-with-generators), which is
the same pattern a Kafka consumer uses.

---

## Worked example — transform API records with nested comprehensions

A realistic shape: flatten nested line items, drop zero-quantity rows, then aggregate per SKU.

```python
orders = [
    {"id": 1, "items": [{"sku": "A", "qty": 2}, {"sku": "B", "qty": 0}]},
    {"id": 2, "items": [{"sku": "A", "qty": 1}]},
]

# 1. Flatten + filter in one nested comprehension
lines = [(o["id"], it["sku"], it["qty"])
         for o in orders
         for it in o["items"]
         if it["qty"] > 0]
print(lines)      # [(1, 'A', 2), (2, 'A', 1)]

# 2. Aggregate. The naive comprehension below is O(n * k) — it rescans `lines` per SKU:
skus = {sku for _, sku, _ in lines}
totals_slow = {s: sum(q for _, sk, q in lines if sk == s) for s in skus}

# 3. The single-pass version — this is what you should write:
from collections import defaultdict
totals = defaultdict(int)
for _, sku, qty in lines:
    totals[sku] += qty
print(dict(totals))    # {'A': 3}
```

Step 2 vs step 3 is the whole lesson: a comprehension that *looks* neat can hide a nested scan.
Volunteering that trade-off is worth more than the one-liner itself.

---

## Hands-on drills

1. Run `dis.dis` on a list comprehension and the equivalent append-loop. Find `LIST_APPEND` in one
   and `CALL_METHOD` in the other. Time both with `timeit` over 100,000 items and report the ratio.
2. Write `[lambda: i for i in range(3)]`, call each, and explain the output. Fix it two ways —
   default argument and `functools.partial` — and say which you'd put in a code review.
3. Build a 5,000-item list `b`. Time `[x for x in a if x in b]`, then convert `b` to a set and time
   it again. State both complexities.
4. Write the same "sum of paid order amounts" three ways: `reduce`+`map`+`filter`, a comprehension,
   and a plain loop. Rank them for readability and justify the ranking out loud.
5. Call `list()` twice on the same `map` object and explain the empty second result.
6. Use `operator.itemgetter` to sort a list of dicts by two keys descending. Do it without a lambda.
7. Flatten `[[1,2],[3,4],[5]]` with `reduce(operator.add, ...)` and with a nested comprehension.
   Explain why the `reduce` version is O(n²).

---

## The 60-second spoken answer

> "Comprehensions are the idiomatic spelling of map and filter — a filtering `if` goes after the
> `for`, a conditional expression before it, and nested `for` clauses read left-to-right like nested
> loops. They're 10–30% faster than an append-loop because they compile to `LIST_APPEND` instead of
> a method call, and since 3.12 they're inlined so there's no extra frame. They have their own
> scope, so the loop variable doesn't leak — the walrus is the deliberate exception. I switch to a
> generator expression whenever the result is large or consumed once. `map` and `filter` are lazy
> iterators in Python 3; I use `map` when I'm passing an existing named function like `int` or
> `str.upper`, and a comprehension when I'd otherwise need a lambda. `reduce` is in `functools`, not
> builtins, because nearly every real use is already `sum`, `max`, `any`, `math.prod` or `join` —
> I'd only reach for it on a genuinely custom fold, and never with `+` on lists because that's
> quadratic."
