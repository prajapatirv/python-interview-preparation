# Deep Dive 04 — Generators, Iterators and Iterables

> Runnable companion: [`01_python_core/04_generators_iterators.py`](../01_python_core/04_generators_iterators.py)
> Related deep dives: [Comprehensions](02_comprehensions_map_filter_reduce.md) ·
> [Concurrency](07_concurrency.md) · [Kafka pipelines](14_kafka_pipelines_delivery_semantics.md) ·
> [AWS streaming](../09_aws_lambda_streaming/README.md)

## What interviewers are actually probing

This topic is a proxy for **"can you process data larger than memory?"** — which is the whole job in
a Kafka/Pandas/Lambda profile. The precise questions are: do you know the **iterator protocol** (not
just that `for` works), can you explain **what `yield` does to the stack frame**, and can you build a
**lazy pipeline** rather than materialising every intermediate list?

The distinction between *iterable* and *iterator* looks pedantic and is not: almost every "why is my
loop empty the second time?" bug traces back to confusing them.

---

## Must-know points

- **Iterable**: implements `__iter__` returning a *fresh* iterator (list, dict, str, file, range).
- **Iterator**: implements `__next__` **and** `__iter__` returning `self`; raises `StopIteration`
  when exhausted. **Single-pass.**
- **Generator function**: any function containing `yield`. Calling it runs *no code* — it returns a
  generator object, which is an iterator.
- **Generators are lazy, single-pass, and preserve local state** between yields.
- **`yield from`** delegates to a sub-iterable and forwards `send`/`throw`, and evaluates to the
  sub-generator's `return` value.
- A generator holds **O(1) memory** regardless of how many items it produces.

---

## Interview questions and full answers

### Q1. What is the difference between an iterable and an iterator?

An **iterable** is anything you can get an iterator *from*: it implements `__iter__`, or (legacy
protocol) `__getitem__` accepting consecutive integers from 0. A list, dict, string, set, file and
`range` are all iterables.

An **iterator** is the thing that actually produces values: it implements `__next__`, returning the
next value or raising `StopIteration`, and `__iter__` returning **itself**.

The practical difference is **reusability**. A list is iterable but *not* an iterator — each `for`
loop calls `iter(list)` and gets a brand-new iterator, so you can loop over it as many times as you
like. An iterator is consumed once and is then permanently exhausted.

```python
nums = [1, 2]
print(iter(nums) is iter(nums))   # False — a fresh iterator each time

it = iter(nums)                   # list -> list_iterator
print(iter(it) is it)             # True  — iterators return themselves
print(next(it), next(it))         # 1 2
# next(it)                        -> StopIteration

for _ in nums: pass               # fine
for _ in nums: pass               # fine again — list is re-iterable
for _ in it:  pass                # nothing — `it` is exhausted
```

**Why `__iter__` returning `self` matters:** it's what lets you pass an iterator anywhere an iterable
is expected. `for x in it` calls `iter(it)`, which must return something with `__next__` — so
iterators must be iterable too.

**The bug this causes in real code:**

```python
def process(records):
    total = sum(r["amount"] for r in records)    # consumes the iterator...
    for r in records:                            # ...so this loop does nothing
        audit(r)

process([{"amount": 1}])          # works — list is re-iterable
process(iter([{"amount": 1}]))    # silently audits nothing
process(csv.DictReader(f))        # silently audits nothing — readers are iterators!
```

The fix is either to materialise (`records = list(records)`) or to restructure to a single pass. A
defensive API documents which it requires.

---

### Q2. How does a `for` loop work internally?

`for x in obj:` desugars to roughly this:

```python
it = iter(obj)                 # calls obj.__iter__() — ONCE
while True:
    try:
        x = next(it)           # calls it.__next__()
    except StopIteration:
        break
    # ... loop body ...
else:
    # the for/else clause runs here — only if StopIteration ended the loop
    pass
```

Three things fall out of this that interviewers ask about:

- **`iter()` is called once**, not per iteration. Mutating the container mid-loop gives undefined
  behaviour (`RuntimeError: dictionary changed size during iteration` for dicts; silently skipped
  elements for lists).
- **`StopIteration` is swallowed by the loop.** This is why a `StopIteration` accidentally raised
  *inside* a generator body used to silently truncate the generator — PEP 479 fixed that in 3.7 by
  converting it to a `RuntimeError`.
- **`for/else`** exists: the `else` block runs if the loop completed *without* `break`. Useful for
  search loops.

---

### Q3. Write a custom iterator class.

Implement `__iter__` returning `self` and `__next__` returning the next value or raising
`StopIteration`.

```python
class Countdown:
    def __init__(self, start):
        self.cur = start

    def __iter__(self):
        return self

    def __next__(self):
        if self.cur <= 0:
            raise StopIteration
        self.cur -= 1
        return self.cur + 1

print(list(Countdown(3)))     # [3, 2, 1]
```

Note this class is **single-pass** — a second `list()` gives `[]`, because `self.cur` is spent. If
you want a *reusable* iterable, separate the two roles: the container's `__iter__` returns a **new**
iterator each time.

```python
class CountdownRange:
    """Iterable (reusable) — not itself an iterator."""
    def __init__(self, start):
        self.start = start

    def __iter__(self):
        return Countdown(self.start)      # fresh iterator per loop

r = CountdownRange(3)
print(list(r), list(r))       # [3, 2, 1] [3, 2, 1] — reusable
```

That split is exactly how `list`/`list_iterator` and `dict`/`dict_keyiterator` are built. In practice
you'd write `__iter__` as a **generator function** and skip the second class entirely:

```python
class CountdownRange:
    def __init__(self, start): self.start = start
    def __iter__(self):
        n = self.start
        while n > 0:
            yield n
            n -= 1
```

---

### Q4. What is a generator and how does `yield` work?

A **generator function** is any function whose body contains `yield`. Calling it **executes none of
the body** — it immediately returns a *generator object*, which is an iterator.

Each `next()` call resumes the function, runs until the next `yield`, hands back that value, and then
**freezes the entire frame**: local variables, the instruction pointer, and the try/except block
stack are all preserved on the generator object. The next `next()` picks up exactly where it left
off. When the function returns (or falls off the end), `StopIteration` is raised.

```python
def countdown(n):
    print("  (body starts)")
    while n > 0:
        yield n
        n -= 1
    print("  (body ends)")

g = countdown(3)
print("nothing has run yet")
print(next(g))        # (body starts) then 3
print(next(g))        # 2  — resumed after the yield, with n still in scope
print(list(g))        # [1] then (body ends)
```

This is why generators can express **infinite sequences** and **stateful streams** in a few lines,
where an iterator class needs explicit attributes for every piece of state.

**Generator state** is observable, which is a nice thing to mention:

```python
from inspect import getgeneratorstate
g = countdown(3)
print(getgeneratorstate(g))   # GEN_CREATED
next(g)
print(getgeneratorstate(g))   # GEN_SUSPENDED
list(g)
print(getgeneratorstate(g))   # GEN_CLOSED
```

---

### Q5. Why are generators memory-efficient? Give a real example.

Because they hold **only the current state**, never the whole sequence. Memory is O(1) in the number
of items produced.

```python
import sys

lst = [i for i in range(1_000_000)]
gen = (i for i in range(1_000_000))

print(sys.getsizeof(lst))     # ~8,000,000 bytes
print(sys.getsizeof(gen))     # ~200 bytes
```

The canonical real example is **line-by-line file processing**. A 20 GB log file processed this way
uses constant memory, because file objects are themselves lazy iterators:

```python
def read_errors(path):
    with open(path) as f:
        for line in f:                  # lazy — one line at a time from the OS buffer
            if "ERROR" in line:
                yield line.rstrip()

for err in read_errors("app.log"):
    handle(err)
```

Contrast with `f.readlines()` or `f.read().split("\n")`, both of which load the entire file.

The same shape is why generators matter for this workspace's other topics:

- **Kafka**: `for msg in consumer` is an unbounded stream you cannot materialise.
- **S3/Lambda**: `boto3`'s `StreamingBody` is read in chunks, never `.read()` in full — see
  [`09_aws_lambda_streaming/02_stream_large_file_s3_simulation.py`](../09_aws_lambda_streaming/02_stream_large_file_s3_simulation.py).
- **Pandas**: `pd.read_csv(..., chunksize=N)` returns a generator of DataFrames.

---

### Q6. What does `yield from` do?

`yield from iterable` delegates the whole of the sub-iterable to the caller. It:

1. Yields every item the sub-iterable produces,
2. **Forwards `send()` and `throw()`** into the sub-generator,
3. **Evaluates to the sub-generator's `return` value**.

Points 2 and 3 are the reason it exists — a manual `for x in sub: yield x` only does point 1.

```python
def flatten(items):
    for x in items:
        if isinstance(x, list):
            yield from flatten(x)      # recursion becomes trivial
        else:
            yield x

print(list(flatten([1, [2, [3, 4]], 5])))     # [1, 2, 3, 4, 5]
```

Capturing the return value:

```python
def counter(n):
    for i in range(n):
        yield i
    return f"produced {n}"             # becomes StopIteration.value

def wrapper():
    result = yield from counter(3)     # result is the RETURN value, not a yielded item
    print(result)                      # 'produced 3'

list(wrapper())
```

`yield from` was introduced by PEP 380 and is the machinery that `await` was originally built on —
`asyncio`'s coroutines were `yield from`-based generators before `async`/`await` syntax arrived. See
[Concurrency](07_concurrency.md).

---

### Q7. Explain `generator.send()`, `throw()` and `close()`.

These turn a generator from a *producer* into a **coroutine** — something you push values into, not
just pull from.

- **`send(value)`** resumes the generator and makes the paused `yield` **expression evaluate to
  `value`**. The generator must first be *primed* with `next(g)` or `g.send(None)` to advance to the
  first `yield` — sending to a brand-new generator raises `TypeError`.
- **`throw(exc)`** raises an exception *at the paused `yield`*, so the generator's own `try/except`
  can handle it.
- **`close()`** raises `GeneratorExit` inside it, so `finally` blocks run and resources are released.
  It's called automatically when the generator is garbage-collected.

```python
def running_avg():
    total = count = 0
    avg = None
    while True:
        value = yield avg          # `yield` is an EXPRESSION here
        total += value
        count += 1
        avg = total / count

g = running_avg()
next(g)                            # prime: run to the first yield
print(g.send(10))                  # 10.0
print(g.send(20))                  # 15.0
print(g.send(30))                  # 20.0
g.close()
```

The `finally`-runs-on-close behaviour is what makes generator-based context managers work:

```python
def managed():
    print("acquire")
    try:
        yield "resource"
    finally:
        print("release")           # runs on close(), GC, or exception

g = managed()
next(g)          # acquire
g.close()        # release
```

That is precisely the mechanism behind `@contextlib.contextmanager` — see
[Deep Dive 05](05_context_managers_descriptors_metaclasses.md#q3-how-do-you-write-a-context-manager-using-contextlib).

---

### Q8. What happens if you iterate a generator twice?

**The second pass gets nothing.** A generator is an iterator, so it's exhausted after one traversal
and immediately raises `StopIteration`.

```python
g = (x * x for x in range(3))
print(list(g))     # [0, 1, 4]
print(list(g))     # []  <- silently empty, no error
```

The silence is what makes this dangerous — no exception, just missing data.

Three ways out, in order of preference:

1. **Restructure to a single pass** (compute everything you need in one traversal).
2. **Call the generator function again** — `make_gen()` produces a fresh generator each call. This is
   why returning a generator *function* is more flexible than returning a generator *object*.
3. **Materialise** with `list(g)` — only if it fits in memory, which defeats the point.
4. **`itertools.tee(g, 2)`** — splits into two independent iterators, but it **buffers** everything
   consumed by the faster branch, so it can use as much memory as a list if the branches drift apart.

```python
from itertools import tee
a, b = tee((x * x for x in range(3)), 2)
print(list(a), list(b))   # [0, 1, 4] [0, 1, 4]
```

---

### Q9. Generator expression vs generator function — when do you need which?

A **generator expression** `(f(x) for x in xs)` is the concise form for a simple map/filter. Use it
when the logic fits on one line.

A **generator function** is required when you need:

- multiple `yield` statements or yields in different branches,
- non-trivial state carried between yields,
- `try`/`finally` for cleanup,
- `send`/`throw` handling,
- a `return` value,
- recursion (`yield from`).

```python
# expression — fine
paid = (o for o in orders if o["status"] == "PAID")

# function — required: state, cleanup, multiple yields
def batched_with_flush(rows, n):
    batch = []
    try:
        for r in rows:
            batch.append(r)
            if len(batch) == n:
                yield batch
                batch = []
        if batch:
            yield batch            # flush the partial final batch
    finally:
        log.info("batching finished")
```

---

### Q10. Build a lazy data pipeline with generators.

Chain small single-purpose generator stages. Each stage pulls from the previous one **only when
asked**, so nothing is materialised and memory stays flat no matter how large the source is. This is
the same architecture as a Kafka consumer (`consume → parse → filter → sink`) or a Unix pipe.

```python
import json

def read(lines):
    for line in lines:
        yield line

def parse(lines):
    for line in lines:
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue                          # skip poison records

def only_paid(events):
    return (e for e in events if e.get("status") == "PAID")

def enrich(events, rates):
    for e in events:
        e["amount_usd"] = e["amount"] * rates.get(e.get("ccy", "USD"), 1.0)
        yield e

raw = ['{"id":1,"status":"PAID","amount":100}',
       'not json',
       '{"id":2,"status":"NEW","amount":50}']

pipeline = enrich(only_paid(parse(read(raw))), rates={"USD": 1.0})
for event in pipeline:
    print(event)          # {'id': 1, 'status': 'PAID', 'amount': 100, 'amount_usd': 100.0}
```

**Why this design wins**, and worth saying aloud:

- Each stage is independently **unit-testable** with a small list as input.
- Stages **compose** in any order without touching each other.
- Memory is **O(1)**, so the same code handles 10 records or 10 billion.
- Nothing executes until you iterate — you can build the pipeline and pass it around.

The trade-offs to acknowledge: **debugging is harder** (a traceback spans several frozen frames), and
**exceptions surface late**, at consumption time rather than construction time.

---

### Q11. Which `itertools` functions do you use most?

| Function | Does | Typical use |
|---|---|---|
| `chain(a, b)` / `chain.from_iterable(xs)` | Concatenate iterables lazily | Merge streams without `+` |
| `islice(it, start, stop)` | Slice an iterator lazily | Take first N from an infinite source |
| `groupby(it, key)` | Group **consecutive** equal keys | Run-length work; **sort first!** |
| `count()` / `cycle()` / `repeat()` | Infinite sequences | ID generators, round-robin |
| `product` / `permutations` / `combinations` | Combinatorics | Test-matrix generation |
| `accumulate(it, func)` | Running totals | Cumulative sums, running max |
| `tee(it, n)` | Split into n iterators (buffers!) | Two passes over one stream |
| `zip_longest(a, b, fillvalue=)` | Zip padding to the longest | Aligning ragged data |
| `batched(it, n)` (3.12+) | Fixed-size chunks | Bulk inserts, Kafka batches |
| `pairwise(it)` (3.10+) | Overlapping consecutive pairs | Deltas between readings |

```python
from itertools import islice, groupby, accumulate, pairwise

print(list(islice(range(100), 5)))              # [0,1,2,3,4] — lazily

# groupby only groups CONSECUTIVE runs — sorting first is mandatory
data = sorted(["apple", "avocado", "banana"], key=lambda s: s[0])
print({k: list(g) for k, g in groupby(data, key=lambda s: s[0])})
# {'a': ['apple', 'avocado'], 'b': ['banana']}

print(list(accumulate([1, 2, 3, 4])))           # [1, 3, 6, 10]
print(list(pairwise([1, 4, 9])))                # [(1, 4), (4, 9)]
```

**The `groupby` trap is asked constantly**: unlike SQL `GROUP BY` or `itertools.groupby`'s name,
it groups *runs*, not values. `groupby([1,2,1])` gives three groups, not two. Sort by the same key
first, or use `collections.defaultdict(list)`.

---

### Q12. How do you read a large iterable in fixed-size batches?

Python 3.12 has it built in; before that, build it with `islice` and a walrus:

```python
from itertools import islice

def batched(iterable, n):
    it = iter(iterable)                       # iter() once — crucial
    while chunk := list(islice(it, n)):       # islice pulls at most n more
        yield chunk

print(list(batched(range(7), 3)))             # [[0,1,2],[3,4,5],[6]]

# Python 3.12+:
from itertools import batched as std_batched
print(list(std_batched(range(7), 3)))         # [(0,1,2),(3,4,5),(6,)]  — tuples
```

The `it = iter(iterable)` line is the whole trick: `islice` must consume from **the same** iterator
each round. Pass the raw iterable and you'd restart from the beginning forever.

This is exactly how you batch before a **bulk DB insert**, a **Kafka produce loop**, or an
**embeddings API call** — all three have per-call overhead that makes one-at-a-time ruinous:

```python
for chunk in batched(records, 500):
    db.bulk_insert(chunk)                     # 1 round-trip per 500 rows, not per row
```

---

### Q13. What's the difference between `return` and `yield` inside a generator?

- **`yield value`** produces a value and *pauses*.
- **`return value`** *ends* the generator. The value is attached to the `StopIteration` exception as
  `.value`, and becomes the result of a `yield from` expression. A bare `return` just stops
  iteration with `StopIteration.value = None`.

You cannot "return a value" from a generator in the ordinary sense — the `for` loop discards it.

```python
def gen():
    yield 1
    return "done"           # not yielded; attached to StopIteration
    yield 2                 # unreachable

g = gen()
print(next(g))              # 1
try:
    next(g)
except StopIteration as e:
    print(e.value)          # 'done'
```

**PEP 479 corollary** (3.7+): raising `StopIteration` *inside* a generator body no longer silently
ends it — it is converted to a `RuntimeError`. Before that, a `next()` on an inner exhausted iterator
would silently truncate your generator, which was a genuinely nasty class of bug.

---

## Worked example — infinite paginated API fetcher with `islice`

A generator that pages through an API forever, plus `islice` to take exactly as much as you need.
The caller controls how much work actually happens.

```python
from itertools import islice

def fetch_pages(client, path="/orders", page_size=100):
    """Yield every row across every page, one row at a time."""
    page = 1
    while True:
        rows = client.get(path, params={"page": page, "size": page_size})
        if not rows:
            return                    # ends the generator cleanly
        yield from rows               # flatten the page into individual rows
        page += 1

# Take only the first 250 orders — exactly 3 HTTP calls, never the whole dataset
first_250 = list(islice(fetch_pages(client), 250))

# Or stream indefinitely with constant memory
for order in fetch_pages(client):
    process(order)
```

Why this is the right shape: the **consumer decides** how much to fetch, the **producer** knows
nothing about limits, memory is flat, and the HTTP calls happen lazily so an early `break` costs you
nothing.

---

## Hands-on drills

1. Write `Countdown` as an iterator class, confirm it's single-pass, then rewrite `__iter__` as a
   generator so it becomes reusable. Explain the difference in one sentence.
2. Pass `csv.DictReader(f)` to a function that both `sum()`s and loops over it. Watch the loop do
   nothing. Fix it two ways and state the memory implication of each.
3. Build the four-stage lazy pipeline from Q10 over a 1,000,000-line generated file. Measure peak
   memory with `tracemalloc` against a version using intermediate lists.
4. Implement `running_avg()` with `send()`. Then add a `throw()` handler that resets the average.
5. Use `itertools.groupby` *without* sorting first and explain the wrong output. Then sort and rerun.
6. Write `batched()` yourself, then compare against `itertools.batched` on 3.12+. Note the tuple
   vs list difference and why it matters for `db.bulk_insert`.
7. Write a generator with a `try/finally` that prints on cleanup. Trigger the cleanup three ways:
   exhausting it, calling `close()`, and letting it be garbage-collected.

---

## The 60-second spoken answer

> "An iterable gives you a fresh iterator from `__iter__`; an iterator has `__next__`, returns itself
> from `__iter__`, and is single-pass — which is why looping twice over a generator or a
> `csv.DictReader` silently gives you nothing the second time. A generator function is any function
> with `yield`; calling it runs no code, it returns a generator object, and each `next()` resumes the
> frozen frame — locals, instruction pointer and all — until the next `yield`. That makes memory O(1)
> regardless of how many items you produce, which is how I process 20 GB log files or an unbounded
> Kafka stream. `yield from` delegates to a sub-iterable and forwards `send`/`throw` and the return
> value. I build data pipelines as chained generator stages because each stage is independently
> testable and nothing materialises; from `itertools` I use `islice`, `chain`, `accumulate` and
> `batched` most, and I'm careful that `groupby` only groups consecutive runs so the input must be
> sorted first."
