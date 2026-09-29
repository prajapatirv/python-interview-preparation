# Deep Dive 03 — Writing and Using Custom Decorators

> Runnable companion: [`01_python_core/03_decorators.py`](../01_python_core/03_decorators.py)
> Related deep dives: [Context managers & descriptors](05_context_managers_descriptors_metaclasses.md) ·
> [Framework development](11_python_framework_development.md) · [Caching](17_caching.md)

## What interviewers are actually probing

Decorators are the single most reliable "can this person actually write Python" test, because a
correct one requires you to hold four concepts at once: **first-class functions**, **closures**,
**`*args`/`**kwargs` forwarding**, and **metadata preservation**. Interviewers very often ask you to
*write one live* — usually `@retry`, `@timer`, `@cache` or `@require_role`.

The three-level version (a decorator that takes arguments) is where most candidates stumble, so
practise it until you can type it without thinking. The follow-up that separates senior candidates
is what happens with **methods**, **async functions** and **stacking order**.

---

## Must-know points

- A decorator is **any callable that takes a function and returns a replacement**, usually a wrapper
  closure that adds behaviour before/after calling the original.
- **`@deco` above `def f` is exactly `f = deco(f)`.** Nothing more. If you remember only this, you
  can derive the rest.
- **Always use `functools.wraps`.** Without it the wrapper's `__name__`, `__doc__`, `__module__`,
  `__qualname__` and `__annotations__` replace the original's, breaking introspection, logging,
  Sphinx, pytest, and framework routing.
- **A decorator with arguments needs three levels**: factory → decorator → wrapper.
- **Stacked decorators apply bottom-up at definition time and run top-down at call time.**
- Decorators run **at import time**. Expensive work in a decorator body slows every startup.

---

## Interview questions and full answers

### Q1. What is a decorator? Write the simplest possible one.

A decorator is a function that receives another function and returns a replacement — normally a
closure that wraps the original and adds behaviour around the call. It works because functions in
Python are **first-class objects**: they can be passed as arguments, returned from functions, and
assigned to names.

```python
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"-> {func.__name__}(args={args}, kwargs={kwargs})")
        result = func(*args, **kwargs)
        print(f"<- {func.__name__} returned {result!r}")
        return result
    return wrapper

@log_calls
def add(a, b):
    return a + b

add(2, 3)
```

**Unpack the syntax explicitly** — interviewers like hearing it:

```python
@log_calls
def add(a, b): ...

# is *identical* to:
def add(a, b): ...
add = log_calls(add)
```

`wrapper` can see `func` after `log_calls` has returned because it is a **closure** — `func` is
captured in `wrapper.__closure__`. You can prove it:

```python
print(add.__closure__[0].cell_contents)   # <function add at 0x...> — the original
```

The `*args, **kwargs` signature is what makes the decorator **generic**: it forwards any call shape
to any function without knowing its signature.

---

### Q2. Why do we use `functools.wraps`?

Because the wrapper is a *different function object*, and without help it advertises itself as
`wrapper`. That breaks a surprising amount of machinery:

```python
def bad(func):
    def wrapper(*a, **k):
        return func(*a, **k)
    return wrapper

@bad
def charge(order_id):
    """Charge the customer for an order."""

print(charge.__name__)   # 'wrapper'   <- logging now says the wrong function failed
print(charge.__doc__)    # None        <- Sphinx/help() produce nothing
```

`functools.wraps(func)` is itself a decorator (built on `functools.update_wrapper`) that copies
`__module__`, `__name__`, `__qualname__`, `__doc__` and `__dict__` from the original onto the
wrapper, and sets **`__wrapped__ = func`** so the original is still reachable.

Concretely, what breaks without it:

- **Logging and error reporting** name the wrong function.
- **`help()` and Sphinx** show nothing useful.
- **Flask** raises `AssertionError: View function mapping is overwriting an existing endpoint` — it
  keys routes by `__name__`, so two decorated views both called `wrapper` collide.
- **FastAPI/Pydantic** read `__annotations__` and the signature to build the OpenAPI schema and to
  validate; losing them silently changes your API contract.
- **pytest** collects by name; decorated tests can vanish or collide.
- **`inspect.signature`** reports `(*args, **kwargs)` instead of the real parameters — unless
  `__wrapped__` is set, which `wraps` does, and which `inspect.signature` follows automatically.

```python
import functools, inspect

def good(func):
    @functools.wraps(func)
    def wrapper(*a, **k):
        return func(*a, **k)
    return wrapper

@good
def charge(order_id: int, amount: float) -> bool:
    """Charge the customer."""

print(charge.__name__)              # 'charge'
print(inspect.signature(charge))    # (order_id: int, amount: float) -> bool
print(charge.__wrapped__)           # the undecorated original
```

---

### Q3. How do you write a decorator that takes arguments? Write `@retry(times=3)`.

You need **one extra level of nesting**. `@retry(times=3)` is a *call* that must **return a
decorator**, which is then applied to the function:

```python
@retry(times=3)
def f(): ...

# expands to:
def f(): ...
f = retry(times=3)(f)
#   ^^^^^^^^^^^^^^  this call returns the actual decorator
```

So the shape is **factory → decorator → wrapper**:

```python
import functools, time, logging

log = logging.getLogger(__name__)

def retry(times=3, delay=0.5, backoff=2.0, exceptions=(Exception,)):
    """Retry a flaky call with exponential backoff."""
    def decorator(func):                      # <- receives the function
        @functools.wraps(func)
        def wrapper(*args, **kwargs):         # <- receives the call
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == times:
                        log.error("%s failed after %d attempts", func.__name__, times)
                        raise
                    sleep_for = delay * (backoff ** (attempt - 1))
                    log.warning("%s attempt %d/%d failed: %s — retrying in %.1fs",
                                func.__name__, attempt, times, exc, sleep_for)
                    time.sleep(sleep_for)
        return wrapper
    return decorator

@retry(times=3, delay=1.0, exceptions=(ConnectionError, TimeoutError))
def call_payment_api(order_id):
    ...
```

**Three things to say unprompted**, because they're what a production reviewer would ask:

1. **Only retry transient errors.** Passing `exceptions=(Exception,)` will happily retry a
   `ValueError` three times and waste three seconds proving your data is still invalid.
2. **Add jitter** in real systems: `sleep_for *= random.uniform(0.5, 1.5)`. Without it, every client
   that failed at the same instant retries at the same instant — a retry storm against a service
   that's already struggling. See [Scaling](12_scaling_applications.md).
3. **The retried call must be idempotent**, or you may charge a card twice.

In production, reach for **`tenacity`** rather than hand-rolling — but be able to write this from
memory, because that's the interview ask.

---

### Q4. In what order are stacked decorators applied?

**Applied bottom-up at definition time; executed top-down at call time.** They nest like onion
layers.

```python
@bold           # applied SECOND -> outermost -> runs FIRST
@italic         # applied FIRST  -> innermost -> runs LAST
def text():
    return "hi"

# definition time:  text = bold(italic(text))
# call time:        bold's wrapper -> italic's wrapper -> original text()
```

```python
import functools

def tag(name):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            return f"<{name}>{func(*a, **k)}</{name}>"
        return wrapper
    return deco

@tag("b")
@tag("i")
def text():
    return "hi"

print(text())     # <b><i>hi</i></b>
```

The outer tag wraps the result of the inner one, so `b` is on the outside.

**Where order genuinely matters in real code:**

```python
# CORRECT — authenticate before spending time/money on the cached work
@app.get("/report")
@require_auth
@cache(ttl=300)
def report(): ...

# WRONG — a cache hit would serve data to an unauthenticated caller,
# because @cache is now outside @require_auth and short-circuits first.
@app.get("/report")
@cache(ttl=300)
@require_auth
def report(): ...
```

Routing decorators (`@app.get`, `@celery.task`) must be **outermost**, because they register
whatever function object they receive — you want them to register the fully-wrapped version.

---

### Q5. How do you write a decorator that works both with and without parentheses?

Users will write both `@timer` and `@timer(unit="s")`, and you'd like both to work. The trick is to
**check whether the first positional argument is callable**: if it is, the decorator was used bare
and you've been handed the function; if not, you were called with options and must return the
decorator.

Make the options **keyword-only** (the `*` in the signature) so there's no ambiguity.

```python
import functools, time

def timer(_func=None, *, unit="ms", logger=print):
    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            start = time.perf_counter()
            try:
                return func(*a, **k)
            finally:
                elapsed = time.perf_counter() - start
                value = elapsed * 1000 if unit == "ms" else elapsed
                logger(f"{func.__name__}: {value:.2f}{unit}")
        return wrapper
    return deco(_func) if callable(_func) else deco

@timer                      # bare — _func is the function
def f(): time.sleep(0.01)

@timer(unit="s")            # called — _func is None, returns deco
def g(): time.sleep(0.01)
```

Note the `try/finally`: the timing is reported **even if the function raises**, which is what you
want from an instrumentation decorator.

---

### Q6. How do you write a class-based decorator, and when is it useful?

Implement `__init__(self, func)` to capture the function and `__call__(self, *args, **kwargs)` to
intercept calls. Use `functools.update_wrapper(self, func)` — the class-based equivalent of
`@wraps` — to copy metadata onto the instance.

Class-based decorators are worth it **when the decorator needs state**: call counts, a cache, a
rate-limit token bucket, a circuit-breaker's open/closed status. The state lives on `self` rather
than in closure cells, which makes it **inspectable and resettable** from outside.

```python
import functools

class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.func(*args, **kwargs)

    def reset(self):
        self.calls = 0

@CountCalls
def ping():
    return "pong"

ping(); ping()
print(ping.calls)     # 2       <- inspectable
ping.reset()          #         <- and controllable
```

With a closure-based decorator you'd have to reach into `wrapper.__closure__` to get at that count,
which is not something you want in real code.

---

### Q7. How do decorators work on methods? What about `self`?

**A function-based decorator works on methods unchanged.** Decoration happens at class-body
execution time, on the plain function, before the descriptor protocol turns it into a bound method.
When you later call `obj.method(x)`, `self` simply arrives as the first element of `*args`:

```python
import functools

def log_calls(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"{func.__name__} called with {args[1:]}")   # args[0] is self
        return func(*args, **kwargs)
    return wrapper

class Service:
    @log_calls
    def charge(self, amount):
        return amount * 2

Service().charge(10)    # charge called with (10,)
```

**A class-based decorator does NOT work on methods out of the box**, and this is the trap. Replacing
the function with an *instance of your class* breaks binding: your instance is not a descriptor, so
`obj.method` returns the decorator instance itself rather than a bound method, and `self` is never
passed.

```python
class Broken:
    def __init__(self, func): self.func = func
    def __call__(self, *a, **k): return self.func(*a, **k)

class Svc:
    @Broken
    def charge(self, amount): return amount

# Svc().charge(10)  -> TypeError: charge() missing 1 required positional argument
```

The fix is to implement **`__get__`** so your decorator becomes a descriptor and can bind:

```python
import functools

class Counted:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *a, **k):
        self.calls += 1
        return self.func(*a, **k)

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return functools.partial(self.__call__, obj)   # bind `obj` as self

class Svc:
    @Counted
    def charge(self, amount): return amount * 2

s = Svc()
print(s.charge(10))          # 20
print(Svc.charge.calls)      # 1
```

See [descriptors](05_context_managers_descriptors_metaclasses.md#q6-what-is-a-descriptor) for why
`__get__` is the mechanism behind every bound method in Python.

**Order also matters with the built-in method decorators**: `@staticmethod`/`@classmethod` must be
**outermost**, because they must receive a plain function, not your wrapper:

```python
class C:
    @staticmethod       # outermost — correct
    @log_calls
    def helper(x): ...
```

---

### Q8. What does `functools.lru_cache` do, and what are its caveats?

It memoises results in a dict keyed by the call arguments, evicting the **least-recently-used**
entry once `maxsize` is exceeded. `@functools.cache` (3.9+) is `lru_cache(maxsize=None)` — unbounded.

```python
from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

print(fib(100))
print(fib.cache_info())    # CacheInfo(hits=98, misses=101, maxsize=None, currsize=101)
fib.cache_clear()
```

**The caveats are the actual interview content:**

1. **All arguments must be hashable.** A `dict` or `list` argument raises `TypeError`. Convert at the
   boundary — `frozenset(d.items())`, `tuple(xs)`.
2. **Keyword vs positional calls cache separately.** `f(1)` and `f(x=1)` are two distinct entries.
3. **It holds strong references to arguments and results** — an unbounded cache is a memory leak
   waiting to happen. Always set a `maxsize` in long-running services.
4. **On instance methods it caches per-`self` and keeps every instance alive forever**, because
   `self` is part of the key and the cache holds a strong reference to it. This is a genuine
   production memory leak. Use `functools.cached_property` for per-instance caching, or a
   per-instance cache created in `__init__`.
5. **It is thread-safe but not process-shared.** With Gunicorn and 4 workers you have 4 independent
   caches and a 4× cold-start cost. For shared caching use Redis — see
   [Caching deep dive](17_caching.md).
6. **No TTL.** Entries never expire on time, only on eviction. If you need time-based expiry, use
   `cachetools.TTLCache` or a Redis-backed decorator.

```python
# The leak:
class Repo:
    @lru_cache(maxsize=128)          # BAD — every Repo ever created stays in memory
    def fetch(self, key): ...

# The fixes:
class Repo:
    def __init__(self):
        self._cache = {}             # per-instance, dies with the instance

    @functools.cached_property       # computed once per instance, stored on the instance
    def config(self): ...
```

---

### Q9. How do you write a decorator for async functions?

**The wrapper itself must be `async def` and must `await` the original.** A normal wrapper would
return an un-awaited coroutine object, so the body never runs and you get a
`RuntimeWarning: coroutine was never awaited`.

```python
import functools, inspect, time

def timed(func):
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*a, **k):
            start = time.perf_counter()
            try:
                return await func(*a, **k)
            finally:
                print(f"{func.__name__}: {time.perf_counter() - start:.3f}s")
        return async_wrapper

    @functools.wraps(func)
    def sync_wrapper(*a, **k):
        start = time.perf_counter()
        try:
            return func(*a, **k)
        finally:
            print(f"{func.__name__}: {time.perf_counter() - start:.3f}s")
    return sync_wrapper
```

The `inspect.iscoroutinefunction` check makes one decorator serve both — which is how real libraries
do it, because users will apply your decorator to both kinds without thinking.

**The trap to mention:** never `time.sleep()` inside an async wrapper (e.g. in an async `@retry`).
It blocks the whole event loop. Use `await asyncio.sleep(...)`. See
[Concurrency](07_concurrency.md#q10-what-happens-if-you-call-timesleep-inside-async-code).

---

### Q10. Can you decorate a class?

Yes. A class decorator receives the **class object** and returns it (usually modified) or a
replacement. `@dataclass`, `@functools.total_ordering` and `@runtime_checkable` all work this way.

The two common custom uses are a **registry** and adding behaviour across a family of classes:

```python
REGISTRY = {}

def register(cls):
    REGISTRY[cls.__name__] = cls
    return cls                  # MUST return the class

@register
class CsvParser: ...

@register
class JsonParser: ...

print(REGISTRY)   # {'CsvParser': <class 'CsvParser'>, 'JsonParser': <class 'JsonParser'>}
```

Forgetting the `return cls` is the classic bug — your class name silently becomes `None`.

A class decorator is usually **a better choice than a metaclass** for this: simpler, composable, and
it doesn't infect subclasses. For automatic registration of *subclasses*, `__init_subclass__` is
better still — see
[metaclass alternatives](05_context_managers_descriptors_metaclasses.md#q13-what-are-the-alternatives-to-metaclasses).

---

### Q11. Write an authorisation decorator like those in Flask/FastAPI apps.

The decorator inspects the current user and raises **before** the view body runs.

```python
import functools

class Forbidden(Exception):
    pass

def require_role(*roles):
    def deco(func):
        @functools.wraps(func)
        def wrapper(user, *a, **k):
            user_roles = set(user.get("roles", []))
            if not user_roles.intersection(roles):
                raise Forbidden(f"one of {roles} required, have {sorted(user_roles)}")
            return func(user, *a, **k)
        return wrapper
    return deco

@require_role("admin", "superuser")
def delete_user(user, uid):
    return f"deleted {uid}"

print(delete_user({"roles": ["admin"]}, 7))     # deleted 7
# delete_user({"roles": ["viewer"]}, 7)         -> Forbidden
```

**The FastAPI-specific point worth making:** in FastAPI you would *not* write this as a decorator.
You'd write it as a **dependency**, because dependencies participate in the DI graph, can be
overridden in tests via `app.dependency_overrides`, and show up in the generated OpenAPI schema —
none of which a hand-rolled decorator gives you:

```python
from fastapi import Depends, HTTPException

def require_role(*roles):
    def checker(user=Depends(current_user)):
        if not set(user["roles"]).intersection(roles):
            raise HTTPException(403, "forbidden")
        return user
    return checker

@app.delete("/users/{uid}")
async def delete_user(uid: int, user=Depends(require_role("admin"))):
    ...
```

Knowing *when a decorator is the wrong abstraction* is a senior-level signal. See
[FastAPI deep dive](10_web_frameworks.md).

---

### Q12. Which built-in decorators should you know?

| Decorator | What it does |
|---|---|
| `@staticmethod` | No `self`/`cls` — a plain function namespaced in the class |
| `@classmethod` | Receives `cls` — alternative constructors, respects subclassing |
| `@property` (+ `.setter`, `.deleter`) | Computed attribute; a **data descriptor** |
| `@functools.wraps` | Copy metadata onto a wrapper |
| `@functools.lru_cache` / `@functools.cache` | Memoisation (see Q8) |
| `@functools.cached_property` | Compute once per instance, store in `__dict__` |
| `@functools.singledispatch` / `singledispatchmethod` | Dispatch on the first argument's type |
| `@functools.total_ordering` | Generate the other five comparisons from `__eq__` + one of `__lt__`… |
| `@dataclasses.dataclass` | Generate `__init__`/`__repr__`/`__eq__` |
| `@contextlib.contextmanager` | Turn a generator into a context manager |
| `@abc.abstractmethod` | Mark a method abstract on an `ABC` |
| `@typing.overload` | Multiple signatures for type checkers only (no runtime effect) |

`singledispatch` is the one people forget, and it is Python's closest thing to method overloading:

```python
from functools import singledispatch

@singledispatch
def serialise(value):
    raise TypeError(f"cannot serialise {type(value)}")

@serialise.register
def _(value: dict): return {k: serialise(v) for k, v in value.items()}

@serialise.register
def _(value: list): return [serialise(v) for v in value]

@serialise.register
def _(value: int): return value
```

---

### Q13. How do you unit-test a decorated function, or bypass the decorator?

Three techniques, used together:

1. **Test the decorator in isolation** against a trivial dummy function, so you test the *behaviour*
   (retries happen, timing is logged) rather than retesting your business logic.
2. **Reach the original via `__wrapped__`**, which `functools.wraps` sets for you:

```python
@retry(times=3)
def flaky(): ...

flaky.__wrapped__()      # calls the undecorated function — no retry logic
```

3. **Monkeypatch the slow part.** A `@retry` decorator with real `time.sleep` makes your test suite
   crawl:

```python
def test_retry_gives_up(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda _: None)   # no real waiting
    calls = []

    @retry(times=3, delay=10)
    def always_fails():
        calls.append(1)
        raise ConnectionError("boom")

    with pytest.raises(ConnectionError):
        always_fails()
    assert len(calls) == 3
```

For decorators applied at **import time** (routes, registrations), remember you cannot patch them
after import — patch before importing the module, or design the decorator to read a value at call
time rather than capture it at definition time.

---

## Worked example — production-style token-bucket rate limiter

A thread-safe rate limiter with a token bucket: tokens refill continuously at `calls/per` per second
and a call consumes one. It allows short bursts up to the bucket size while enforcing the average
rate — which is why token buckets are preferred to naive fixed windows.

```python
import functools, threading, time

def rate_limit(calls: int, per: float):
    """Allow `calls` per `per` seconds, with bursting up to `calls`."""
    lock = threading.Lock()
    state = {"tokens": float(calls), "last": time.monotonic()}

    def deco(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            with lock:
                now = time.monotonic()                 # monotonic: immune to clock changes
                elapsed = now - state["last"]
                state["tokens"] = min(calls, state["tokens"] + elapsed * calls / per)
                state["last"] = now
                if state["tokens"] < 1:
                    raise RuntimeError("rate limit exceeded")
                state["tokens"] -= 1
            return func(*a, **k)                       # call OUTSIDE the lock
        return wrapper
    return deco

@rate_limit(calls=5, per=1.0)
def send_sms(to):
    return f"sent to {to}"
```

**Four details worth narrating**, because each is a deliberate decision:

- **`time.monotonic()` not `time.time()`** — monotonic never jumps backwards on an NTP correction.
- **The function is called outside the lock.** Holding a lock across I/O serialises every caller and
  destroys throughput.
- **State lives in a dict**, not as closure locals, because rebinding a closure variable would need
  `nonlocal`; a mutable container sidesteps that.
- **This is per-process.** With 4 Gunicorn workers you get 4× the intended rate. For a real
  multi-instance limit you need Redis — see
  [Scaling](12_scaling_applications.md) and
  [`08_scaling_production_resilience/03_rate_limiter.py`](../08_scaling_production_resilience/03_rate_limiter.py).

---

## Hands-on drills

1. Write `@log_calls` **without** `functools.wraps`, then register two decorated views with Flask and
   watch the endpoint collision. Add `wraps` and watch it go away.
2. Write `@retry` from a blank file, from memory, in under three minutes. Then add jitter and a
   `max_total_time` cap.
3. Stack `@timer` and `@retry` in both orders around a function that fails twice then succeeds.
   Predict what each order reports, then verify.
4. Apply a class-based decorator to a method and reproduce the `missing 1 required positional
   argument` error. Fix it with `__get__`.
5. Put `@lru_cache` on an instance method, create 100,000 instances in a loop, and watch memory with
   `tracemalloc`. Replace with `cached_property` and measure again.
6. Write one `@timed` decorator that handles both sync and async functions, and prove it with both.
7. Write a decorator that reads `__wrapped__` to assert it was applied to an async function, raising
   at *decoration* time if not.

---

## The 60-second spoken answer

> "A decorator is a callable that takes a function and returns a replacement — `@deco` above `def f`
> is just `f = deco(f)`. The wrapper is a closure over the original and forwards `*args, **kwargs`,
> and I always apply `functools.wraps` so `__name__`, `__doc__`, the signature and `__wrapped__`
> survive — without it Flask route registration and FastAPI's OpenAPI generation break. A decorator
> that takes arguments needs three levels: factory, decorator, wrapper. Stacked decorators apply
> bottom-up and run top-down, which matters for things like putting auth outside caching. For
> methods, function-based decorators just see `self` in `*args`; a class-based one needs `__get__`
> to bind. For async I check `inspect.iscoroutinefunction` and return an `async def` wrapper that
> awaits. The ones I write most are retry-with-backoff, timing, and a Redis-backed cache — and I'd
> note that `lru_cache` on an instance method leaks memory because `self` is part of the key."
