# Deep Dive 22 — Variable Scope, Declaration and Namespaces

> Runnable companion: [`01_python_core/12_variable_scope_namespaces.py`](../01_python_core/12_variable_scope_namespaces.py)
> Related deep dives: [03 — Decorators](03_decorators.md) · [04 — Generators](04_generators_iterators.md) ·
> [06 — OOP and MRO](06_oop_inheritance_mro.md) · [24 — Python basics](24_python_basics_essentials.md) ·
> [21 — Java → Python bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

This looks like a beginner topic and isn't. It gets asked at senior level because **scope is where
Python's design differs most sharply from Java/C#**, and because three of the most common
production bugs in Python are scope bugs wearing a disguise:

- `UnboundLocalError` on a counter that "obviously exists"
- a closure in a loop where every callback sees the last value
- a module-level mutable that quietly accumulates state across requests in a long-running server

What separates a 3-year answer from a 10-year one is whether you can state the **rule that causes
all three**, rather than memorising the three fixes. That rule is one sentence:

> **Assignment anywhere in a function body makes that name local for the entire function, decided
> at compile time — not at the moment the line executes.**

Everything else in this document is a consequence of that.

---

## Must-know points

- **LEGB** is the lookup order: **L**ocal → **E**nclosing (any enclosing *function*) → **G**lobal
  (module-level) → **B**uilt-in. First hit wins; a miss at the end is `NameError`.
- "**Global**" in Python means **module-level**, not program-wide. There is no cross-module global.
- **There is no declaration.** The first assignment creates the name; *where* that assignment
  appears determines the scope. A bare annotation (`x: int`) creates **no name at all**.
- **`global name`** = "rebind the module-level name". **`nonlocal name`** = "rebind the nearest
  enclosing *function*'s name". Both are about **rebinding a name**, never about mutating an object.
- **Mutating needs no declaration.** `config["k"] = v` and `items.append(x)` work on a global
  without `global`; only `config = {}` needs it.
- **Reading before assigning in the same function** → `UnboundLocalError` (a subclass of
  `NameError`), raised at the *read*, caused by the *assignment* below it.
- **A class body is not an enclosing scope.** Methods cannot see class attributes as bare names,
  and comprehensions inside a class body cannot see the class's own attributes.
- **Comprehensions have their own function scope** (Python 3+), so the loop variable never leaks.
  The walrus `:=` is the deliberate exception — it binds in the *enclosing* scope.
- **Closures capture the variable, not the value** (late binding). Bind eagerly with a default
  argument (`lambda i=i: i`) or `functools.partial`.
- `globals()` is the module's live `__dict__` (writable). `locals()` inside a function is a
  **snapshot** — writing to it does not create a local in CPython.
- **Shadowing a built-in is legal and silent**, and breaks the rest of that scope.

---

## Interview questions and full answers

### Q1. Explain the LEGB rule.

LEGB is the order in which Python resolves a **bare name**:

```python
name = "global"                 # G — module level

def outer():
    name = "enclosing"          # E — local to outer, enclosing for inner

    def inner():
        name = "local"          # L
        print(name)             # "local"      → L
    def inner2():
        print(name)             # "enclosing"  → no L, so E
    inner(); inner2()

outer()
print(name)                     # "global"     → G
print(len)                      # B — builtins, the last stop
```

Two precisions that make the answer senior:

**1. The resolution is decided at COMPILE time, not at runtime.** When CPython compiles a function
it classifies every name as local (`LOAD_FAST`), closure cell (`LOAD_DEREF`), or
global/builtin (`LOAD_GLOBAL`). You can see it:

```python
import dis
def f():
    x = 1
    return x + y          # y is not assigned here
dis.dis(f)                # LOAD_FAST x ; LOAD_GLOBAL y
```

That is *why* `UnboundLocalError` happens on a line that looks like a read: the opcode was already
chosen as `LOAD_FAST` before the function ever ran.

**2. "Global" means module-level.** Each module has its own namespace; there is no process-wide
global namespace. `from other import x` **copies the binding** into your module, so rebinding
`other.x` later does not change your `x`. That surprises people coming from Java `static`.

**3. Only functions create an Enclosing scope.** Not `if`, not `for`, not `while`, not `try`, and —
critically — **not a class body** (Q6). So:

```python
for i in range(3):
    pass
print(i)        # 2 — the loop variable survives; a `for` is not a scope
```

---

### Q2. Why does this raise `UnboundLocalError`, and what are the fixes?

```python
counter = 10

def increment():
    print(counter)        # UnboundLocalError
    counter = counter + 1
```

**Because `counter = ...` appears in the function body, `counter` is local for the whole
function** — including the `print` above it. At the `print`, the local exists but has no value
bound yet, so CPython raises:

```
UnboundLocalError: cannot access local variable 'counter' where it is not associated with a value
```

Note the exception is a subclass of `NameError`, which is why a bare `except NameError` catches it.

The same trap with augmented assignment is even sneakier, because `+=` *looks* like mutation:

```python
total = 0
def add(n):
    total += n        # UnboundLocalError: `total` is local because of this line
```

**The three fixes, in the order you should prefer them:**

```python
# 1. BEST — don't share state. Take it in, return it out.
def increment(current):
    return current + 1
counter = increment(counter)

# 2. GOOD — encapsulate the state in an object (or a closure, Q3)
class Counter:
    def __init__(self): self.value = 10
    def increment(self): self.value += 1      # `self.value` is attribute access, not a rebind

# 3. LAST RESORT — `global`
def increment():
    global counter
    counter += 1
```

Why `global` is the last resort, specifically: in a web service or a consumer, module-level mutable
state is **shared by every request/message in that process and across threads**. It makes the
function untestable in isolation (tests leak into one another through it), unsafe under threading
(`+=` is not atomic — see [07 — Concurrency](07_concurrency.md)), and invisible in the signature,
so a reader cannot tell the function has side effects. In a FastAPI app the right homes for that
state are `app.state`, a dependency-injected singleton, or Redis — all of which are visible and
mockable. See [`05_web_apis_fastapi/app/dependencies.py`](../05_web_apis_fastapi/app/dependencies.py).

---

### Q3. What does `nonlocal` do, and when do you actually use it?

`nonlocal` rebinds a name in the **nearest enclosing function scope**. It does not reach module
level (that's `global`) and it requires the name to **already exist** in an enclosing function —
unlike `global`, which will happily create a module-level name.

```python
def make_counter():
    total = 0
    def increment(by=1):
        nonlocal total        # without this: UnboundLocalError on `total += by`
        total += by
        return total
    def read():
        return total          # READING needs no declaration
    return increment, read

inc, read = make_counter()
inc(); inc(5); read()          # 6
```

Each call to `make_counter()` creates an independent `total`. That is the real use case: **a tiny
object with one or two methods, without writing a class.** The state lives in a closure cell, which
is inspectable:

```python
inc.__code__.co_freevars            # ('total',)
inc.__closure__[0].cell_contents    # 6
```

**Where you meet it in real code:** stateful decorators (a call counter, a rate limiter, a cache),
and callbacks. In the decorator case there's a genuine choice to make:

```python
def count_calls(fn):                      # closure + nonlocal
    calls = 0
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        nonlocal calls
        calls += 1
        return fn(*a, **kw)
    wrapper.calls = lambda: calls          # awkward: the state is hard to expose
    return wrapper

class CountCalls:                          # class + attribute
    def __init__(self, fn): self.fn, self.calls = fn, 0
    def __call__(self, *a, **kw):
        self.calls += 1                    # no `nonlocal` needed — it's attribute access
        return self.fn(*a, **kw)
```

**Say this:** a closure is cleaner when the state is private and small; a class is better the moment
the state needs to be *read, reset or inspected from outside*, because an attribute is a better
public surface than a smuggled-out lambda. Both are shown in
[`01_python_core/03_decorators.py`](../01_python_core/03_decorators.py).

**The thread-safety caveat, which is the follow-up question:** a closure counter is no safer than a
global one. `total += by` is read-modify-write and a thread can be pre-empted between the read and
the write. If the counter matters, use a `threading.Lock` or `itertools.count()` (whose `__next__`
is atomic at the C level).

---

### Q4. `global` vs `nonlocal` — state the difference precisely.

| | `global x` | `nonlocal x` |
|---|---|---|
| Target | the **module-level** namespace | the nearest **enclosing function** scope |
| Must already exist? | **No** — it will create it | **Yes** — `SyntaxError` at compile time if not found |
| Skips intermediate scopes? | Yes — jumps straight to module level | No — nearest enclosing function wins |
| Legal at module level? | Yes (a no-op) | No — `SyntaxError: nonlocal declaration not allowed at module level` |
| Typical use | a module singleton, a lazily-initialised cache | closure state, stateful decorators |

```python
level = "module"

def demo():
    level = "enclosing"
    def use_nonlocal():
        nonlocal level
        level = "rebound-by-nonlocal"      # changes demo()'s local
    def use_global():
        global level
        level = "rebound-by-global"        # changes the MODULE-level one
    use_nonlocal(); print(level)           # "rebound-by-nonlocal"
    use_global();   print(level)           # still "rebound-by-nonlocal"
demo()
print(level)                               # "rebound-by-global"
```

The sentence to land: **both keywords are about rebinding a name; neither has anything to do with
mutating an object.** `global config` is unnecessary for `config["retries"] = 5` and required for
`config = {}`.

---

### Q5. Does Python have variable declarations? What does `x: int` do?

**No declarations.** The first assignment both creates the binding and fixes its scope. The
consequences:

```python
count = 0              # creates a module-level name
count_str: str         # ANNOTATION ONLY — creates no name, no value
print(count_str)       # NameError
```

Annotations are stored separately from the namespace, in `__annotations__`, and they are **not
enforced at runtime at all**:

```python
def charge(amount: int) -> str:
    return amount * 2          # returns an int. No error. Hints are not checks.
```

Two modern details worth knowing because they signal you're current:

- **PEP 563 / `from __future__ import annotations`** made annotations strings at runtime, so a
  forward reference like `-> "Order"` needs no quotes.
- **PEP 649 (Python 3.14)** replaced that with **lazy evaluation**: annotations are computed on
  first access via a `__annotate__` function. Practical effect: at module level, the *bare* name
  `__annotations__` may raise `NameError` until something forces evaluation — read it as an
  attribute (`sys.modules[__name__].__annotations__`) or via `inspect.get_annotations()`.

**Where hints ARE enforced, which is the point of using them:** `mypy`/`pyright` in CI, and
Pydantic at the edges of your system (request bodies, config, event payloads). That split —
*validated at the boundary, trusted inside* — is the design to describe. See
[10 — Web frameworks](10_web_frameworks.md).

---

### Q6. Why can't a method see a class attribute as a bare name?

```python
MULTIPLIER = 3

class Config:
    base = 10
    doubled = base * 2                      # ✅ class-body code sees earlier class-body names
    tripled = [base * MULTIPLIER for _ in range(3)]   # ❌ NameError: name 'base' is not defined

    def read(self):
        return base                          # ❌ NameError
```

**A class body is executed once, in its own temporary namespace, which then becomes the class
`__dict__` — but it is NOT an enclosing scope for anything nested inside it.** So:

- **Line 2 works** because plain class-body statements run sequentially *in* that namespace.
- **The comprehension fails** because a comprehension gets its own function scope, and when that
  inner function looks outward, the class body is **skipped**. It can see `MULTIPLIER` (a global),
  never `base`.
- **The method fails** for the same reason: `read` is a function whose enclosing scopes are the
  module and any enclosing *functions* — not `Config`.

The fixes:

```python
class Config:
    base = 10
    tripled = [b * MULTIPLIER for b in (base,) * 3]   # pass it in via the ITERABLE —
                                                      # the outermost iterable IS evaluated
                                                      # in the class scope
    def read(self):
        return self.base            # or Config.base — explicit lookup, always correct
```

Worth knowing *why* the iterable trick works: in a comprehension the **leftmost `for`'s iterable is
evaluated in the enclosing scope** and passed into the implicit function as an argument. Everything
else runs inside it.

**Java contrast:** in Java an instance method sees `base` directly because the compiler resolves it
to `this.base`. Python requires the explicit `self.`/`Config.` — which is the same reason you write
`self` in every method signature. Explicit beats implicit, consistently.

---

### Q7. Why do all these callbacks print the same number?

```python
handlers = [lambda: print(i) for i in range(3)]
for h in handlers: h()        # 2, 2, 2
```

**Closures capture the variable, not the value.** All three lambdas share one cell for `i`; by the
time any of them runs, the comprehension has finished and the cell holds `2`. This is **late
binding**, and it's correct — it's what makes recursion and mutual references work:

```python
def make_pair():
    def ping(n): return "done" if n == 0 else pong(n - 1)   # pong not defined YET
    def pong(n): return ping(n)
    return ping                                              # works: resolved at CALL time
```

Three fixes, in order of how often they're right:

```python
early   = [lambda i=i: i for i in range(3)]              # default arg: evaluated at `def` time
partial = [functools.partial(lambda x: x, i) for i in range(3)]   # explicit, no fake parameter
factory = [(lambda v: lambda: v)(i) for i in range(3)]   # an extra scope per iteration
```

The default-argument form is idiomatic but leaks a parameter into the public signature, which
matters for a callback someone else calls. `functools.partial` is the cleaner choice there.

**Where this actually bites in production:** registering handlers in a loop (`for route in routes:
app.add_route(route, lambda: handle(route))` — every route handles the last route), building
`ThreadPoolExecutor` tasks in a loop, and attaching retry callbacks per item. The symptom is always
"it works for one item and does the last item N times".

---

### Q8. Do comprehension and `except` variables leak?

**Comprehensions: no.** Each comprehension (list, set, dict, generator) runs in its own implicit
function scope:

```python
x = "untouched"
squares = [x * 2 for x in range(3)]
print(x)                  # "untouched"
```

In Python 2 the list comprehension *did* leak — fixed in Python 3, and the fix is why a
comprehension cannot see a class body (Q6). The two exceptions:

```python
if any((found := n) > 1 for n in [0, 1, 2]):
    print(found)          # 2 — the walrus DELIBERATELY binds in the enclosing scope
```

**`except ... as e`: the opposite — it is explicitly DELETED.** Python 3 deletes the name at the end
of the `except` block, to break a reference cycle (the exception holds a traceback which holds the
frame which holds `e`):

```python
try:
    1 / 0
except ZeroDivisionError as e:
    pass
print(e)        # NameError: name 'e' is not defined
```

So if you need the exception afterwards, **copy it out**:

```python
error = None
try:
    risky()
except ValueError as e:
    error = e               # survives the block
```

That detail comes up constantly in retry loops — see
[25 — Nested exception handling](25_nested_exception_handling.md).

**`for` loop variables: they leak**, because `for` is not a scope. Useful for `for/else` searches,
and a trap when you reuse `i` later.

---

### Q9. What's the difference between `globals()`, `locals()` and `vars()`?

```python
globals()          # the module's live __dict__ — WRITABLE, and writes take effect
locals()           # module level: same as globals(). In a function: a SNAPSHOT dict
vars()             # locals() with no argument; vars(obj) is obj.__dict__
vars(SomeClass)    # the class __dict__ (a mappingproxy — read-only)
```

The one that matters: **`locals()` in a function body is a snapshot**, because CPython stores locals
in a fixed-size array on the frame, not a dict. Writing to it does nothing:

```python
def f():
    locals()["injected"] = 1
    return injected          # NameError
```

(Python 3.13 formalised this behaviour in PEP 667; in older versions it was an implementation
detail that occasionally appeared to work inside `exec`.)

Legitimate uses of `globals()`: a module-level plugin registry, lazy singletons, and
`globals()[name]` for a dispatch table built from the module's own functions. Legitimate uses of
`locals()`: debugging and logging (`log.debug("state=%s", locals())`). If you find yourself
*writing* to either to pass data around, you want a dict, a dataclass or a parameter.

---

### Q10. What are the real-world consequences of module-level state?

This is the question behind the question, and the one worth volunteering. Module-level mutable
state is a **process-wide singleton**, so:

1. **Tests leak into each other.** Test A increments the counter; test B asserts on it and passes
   only because of the ordering. The fix is a fixture that constructs fresh state, which requires
   the state to be constructible — i.e. not a module global.
2. **It is not thread-safe.** `requests_served += 1` from 8 Gunicorn threads loses updates. See
   [`02_concurrency/01_threading_demo.py`](../02_concurrency/01_threading_demo.py) — and note the
   CPython 3.13+ wrinkle documented there: a *bare* `+=` often *looks* safe because the interpreter
   only checks for a thread switch at the loop back-edge, so the race hides until the critical
   section contains a function call.
3. **It does not survive scaling out.** Four pods mean four independent counters. An in-process
   rate limiter is per-pod, so "100 requests/minute" silently becomes 400. The fix is shared state
   (Redis) — see [`08_scaling_production_resilience/03_rate_limiter.py`](../08_scaling_production_resilience/03_rate_limiter.py).
4. **Import-time side effects are scope bugs too.** Module-level code runs once per process, on
   first import, in import order. A module-level `DB = connect()` makes importing the module open a
   socket, which breaks tests, breaks `--help`, and in AWS Lambda runs during the init phase where
   the timeout is different.

**The exception that's genuinely fine:** module-level **immutable** constants and caches keyed
safely — `MAX_RETRIES = 3`, a compiled regex, an `lru_cache`-decorated pure function, or a Lambda
handler's module-level client (which you *want* reused across warm invocations; see
[`09_aws_lambda_streaming/01_lambda_handler_patterns.py`](../09_aws_lambda_streaming/01_lambda_handler_patterns.py)).
The distinction is **mutable, request-specific state** — that is what must not live at module level.

**And the right tool for per-request state in async code: `contextvars.ContextVar`**, not a global
and not thread-local. A `ContextVar` is isolated per asyncio task *and* per thread, which is exactly
what a correlation ID needs:

```python
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")
token = correlation_id.set(incoming_header or new_id())
try:    ...                       # every log line in this request reads correlation_id.get()
finally: correlation_id.reset(token)
```

A `threading.local()` would be wrong here: thousands of asyncio tasks share one thread, so they'd
share one value. That's shown end-to-end in
[`13_system_design_scenarios/02_observability_pillars.py`](../13_system_design_scenarios/02_observability_pillars.py).

---

## Java contrast

| Java | Python |
|---|---|
| `int x = 0;` — type declared, scope is the block | `x = 0` — no declaration; scope is the whole **function** |
| Block-scoped: `if`/`for`/`while` each create a scope | **Only functions** create a scope (plus comprehensions) |
| Reading an uninitialised local = **compile error** | Reading before assignment = **`UnboundLocalError` at runtime** |
| `static` field = class-level, shared | module-level name — but **per module**, not per program |
| Shadowing a field needs `this.x` to disambiguate | shadowing a global needs `global x` to *rebind* it |
| Lambdas capture **effectively final** values (compile error otherwise) | closures capture the **variable** — late binding, all callbacks see the final value |
| Inner class sees the outer instance's fields | a method does **not** see class attributes as bare names — use `self.` |
| `final` prevents reassignment | nothing prevents reassignment; `Final[int]` is a hint a checker enforces |

**The two that cause real bugs for Java developers:** the loop-closure difference (Java refuses to
compile what Python silently does wrong), and the function-wide locality of assignment (Java's
block scoping means the `UnboundLocalError` pattern cannot exist). Both are in
[`01_python_core/11_java_to_python_bridge.py`](../01_python_core/11_java_to_python_bridge.py).

---

## A worked example

A request-scoped context for a service — the shape that gets all of this right at once:

```python
"""One module showing each scope tool used for the job it's actually for."""
import functools
import threading
from contextvars import ContextVar

# ---- module level: IMMUTABLE config only. Safe: never rebound, never mutated.
MAX_RETRIES = 3
RETRYABLE = (TimeoutError, ConnectionError)

# ---- per-request state: a ContextVar. Isolated per task AND per thread.
request_id: ContextVar[str] = ContextVar("request_id", default="-")

# ---- process-wide mutable state: explicitly guarded, and named so reviewers see it.
_metrics_lock = threading.Lock()
_metrics = {"requests": 0, "errors": 0}


def record(metric):
    """Mutating a module-level dict needs NO `global` — we never rebind `_metrics`.
    The lock is needed because `+= 1` is read-modify-write, not because of scope."""
    with _metrics_lock:
        _metrics[metric] += 1


def make_retry(max_attempts=MAX_RETRIES):
    """Closure state via `nonlocal`: private, per-decorator, no class needed."""
    total_retries = 0

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            nonlocal total_retries                 # rebinding the enclosing name
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except RETRYABLE as exc:
                    error = exc                    # COPY IT OUT: `exc` is deleted at block end
                    if attempt == max_attempts:
                        record("errors")
                        raise
                    total_retries += 1
                    log(f"retry {attempt} for request {request_id.get()}: {error}")
        return wrapper

    decorator.total_retries = lambda: total_retries   # read-only view of the closure state
    return decorator


def log(message):
    print(f"[{request_id.get()}] {message}")


def handle_request(incoming_id=None):
    token = request_id.set(incoming_id or "req-generated")
    try:
        record("requests")
        log("handling")
        return "ok"
    finally:
        request_id.reset(token)      # ALWAYS reset — otherwise the value leaks to the next
                                     # request that reuses this task/thread
```

**Why each choice:**

- `MAX_RETRIES` at module level is fine because it is **immutable and never rebound**.
- `request_id` is a `ContextVar`, not a global and not `threading.local()`, because async tasks
  share a thread.
- `_metrics` is mutated, never rebound, so no `global` — but it **is** shared across threads, so it
  takes a lock. Naming the *two separate reasons* (scope vs. concurrency) is the senior move.
- `nonlocal total_retries` keeps the retry count private to the decorator instance.
- `error = exc` exists because `exc` is deleted at the end of the `except` block (Q8).
- The `finally: reset(token)` is non-negotiable: without it, a worker thread reused for the next
  request logs the previous request's ID, which is a genuinely horrible bug to debug.

---

## Hands-on drills

1. Write the `UnboundLocalError` function from Q2. Then delete only the assignment line and confirm
   the read now succeeds — proving the error came from the assignment, at compile time.
2. `dis.dis()` two functions: one that reads a global, one that assigns to the same name. Find
   `LOAD_GLOBAL` vs `LOAD_FAST` in the output and explain `UnboundLocalError` in terms of opcodes.
3. Write `make_counter()` with `nonlocal`, create two counters, and prove their state is
   independent. Then print `inc.__closure__[0].cell_contents`.
4. Build the class-body `NameError` from Q6 three ways (comprehension, method, nested function).
   Then fix each, and say in one sentence why the iterable trick works.
5. Create 5 lambdas in a loop that all print the same value; fix it three ways (default arg,
   `partial`, factory function) and state when you'd use each.
6. Write a function that does `locals()["x"] = 1` then tries to read `x`. Then do the same with
   `globals()` at module level and note that *that* one works.
7. Shadow `list` inside a function, then call `list(...)` later in the same function. Read the
   `TypeError` and write down the five built-ins you're most likely to shadow by accident.
8. Spin up 8 threads each incrementing a module-level counter 100,000 times with `counter += 1`.
   Run it on your Python version. If you get the right answer, put a `time.sleep(0)` between a read
   and a write and run again. Explain the difference (see
   [`02_concurrency/01_threading_demo.py`](../02_concurrency/01_threading_demo.py)).
9. Set a `ContextVar` in one asyncio task and read it in another; confirm isolation. Then do the
   same with a module-level global and watch them collide.

---

## The 60-second spoken answer

> "Python resolves bare names with LEGB — local, enclosing function, global meaning module-level,
> then builtins — and the resolution is decided at compile time, not when the line runs. That one
> fact explains most scope surprises: if a name is assigned anywhere in a function, it's local for
> the *whole* function, so reading it before that assignment gives `UnboundLocalError` even though
> a module-level name with that name exists.
>
> There are no declarations — the first assignment creates the name, and a bare annotation like
> `x: int` creates no name at all, just an entry in `__annotations__`, which nothing enforces at
> runtime. `global` rebinds a module-level name and `nonlocal` rebinds the nearest enclosing
> function's name; both are about *rebinding a name*, never about mutating an object, so
> `config['k'] = v` needs neither and `config = {}` needs `global`.
>
> Two things catch people out specifically. A class body isn't an enclosing scope, so a method
> can't see a class attribute as a bare name — it goes through `self` — and a comprehension in a
> class body can't see the class's own attributes either. And closures capture the *variable*, not
> the value, so lambdas built in a loop all see the final value; I bind eagerly with a default
> argument or `functools.partial`.
>
> In practice I avoid module-level mutable state altogether: it leaks between tests, it isn't
> thread-safe because `+=` is read-modify-write, and it doesn't survive scaling to four pods — an
> in-process rate limiter silently becomes four limiters. Module level is for immutable constants.
> For per-request state in async code I use a `ContextVar`, not a global and not `threading.local`,
> because thousands of asyncio tasks share one thread; and I always reset the token in a `finally`,
> or the value leaks into the next request on that task."
