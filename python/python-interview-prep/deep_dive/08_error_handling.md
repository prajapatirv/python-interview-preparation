# Deep Dive 08 — Error Handling

> Runnable companion: [`01_python_core/08_exception_handling.py`](../01_python_core/08_exception_handling.py)
> Related deep dives: [Concurrency](07_concurrency.md) · [Web frameworks](10_web_frameworks.md) ·
> [Kafka failure handling](15_kafka_failure_handling.md) · [Production stability](19_production_stability_monitoring.md)

## What interviewers are actually probing

Error handling is where interviewers find out whether you've run things in production. Anyone can
write `try/except`. What they're listening for is: do you catch **narrowly**, do you **preserve the
root cause**, do you have a **custom exception hierarchy** that maps cleanly to HTTP or to
retry/DLQ decisions, and do you know that a `return` in `finally` silently eats exceptions.

Modern Python adds `ExceptionGroup`/`except*` and `add_note()`. Knowing those signals you're current.

---

## Must-know points

- `try` → `except` (handle) → `else` (runs only when nothing was raised) → `finally` (always runs).
- **Catch the narrowest exception you can act on.** Never bare `except:` — it also catches
  `KeyboardInterrupt` and `SystemExit`.
- **`raise NewError(...) from err`** preserves the root cause in `__cause__`.
- Build **one application base exception** with specific subclasses under it.
- **`logger.exception()`** inside an `except` block captures the traceback automatically.
- **Never `return` from `finally`** — it discards both the pending return value *and* any in-flight
  exception.
- `try` is **zero-cost when nothing raises** (3.11+); raising is comparatively expensive.

---

## Interview questions and full answers

### Q1. Explain `try` / `except` / `else` / `finally`.

Four clauses, each with a distinct job:

- **`try`** — the code that might fail. Keep it **as small as possible**.
- **`except`** — handles specific errors. Multiple clauses are tried top-to-bottom; the first
  matching one wins, so order subclasses before superclasses.
- **`else`** — runs **only if no exception was raised**. This is the clause people skip, and it
  matters: putting the success path here means its own errors aren't accidentally swallowed by your
  `except`.
- **`finally`** — **always** runs: on success, on exception, on `return`, on `break`, on `continue`.
  For cleanup.

```python
def read_config(path):
    try:
        f = open(path)                    # ONLY the risky call
    except FileNotFoundError:
        return {}
    else:
        with f:
            return json.load(f)           # if THIS raises JSONDecodeError, it propagates —
                                          # it is not caught by the FileNotFoundError above
    finally:
        print("read_config finished")     # runs in every path, including both returns
```

**Why `else` rather than putting `json.load` in the `try`:** if it were in the `try`, and you later
broadened the `except` to `OSError` or `Exception`, you'd silently swallow parse failures too. `else`
keeps the blast radius of your `except` tightly scoped to the line you meant.

**Execution order with `return`:** `finally` runs *after* the return value is computed but *before*
it's handed back to the caller. So the caller sees the original value — unless `finally` itself
returns (see Q9).

---

### Q2. Why is a bare `except:` or `except Exception: pass` bad?

**A bare `except:` catches `BaseException`**, which includes:

- **`KeyboardInterrupt`** — your program can no longer be stopped with Ctrl-C.
- **`SystemExit`** — `sys.exit()` stops working; graceful shutdown breaks.
- **`GeneratorExit`** — generator cleanup breaks.
- **`asyncio.CancelledError`** (3.8+, a `BaseException`) — timeouts and task cancellation stop
  working; tasks refuse to die.

```python
while True:
    try:
        process()
    except:            # Ctrl-C is caught and discarded. The loop is now unkillable.
        pass
```

**`except Exception: pass` is better but still usually wrong**, because it *silently discards
information*. The failure happened; you just can't see it. Days later there's a data gap and no log
line explaining it.

The defensible pattern — broad catch at a **boundary**, where you log and either re-raise or convert:

```python
try:
    process(record)
except (ValidationError, KeyError) as e:      # expected, actionable -> handle
    send_to_dlq(record, e)
except Exception:                              # unexpected -> log WITH traceback, then re-raise
    logger.exception("unexpected failure processing record_id=%s", record.get("id"))
    raise
```

A top-level catch-all in a consumer loop or a request handler is legitimate — it stops one bad
message killing the process — **provided** it logs the traceback and increments an error metric.
Silence is the sin, not breadth.

---

### Q3. Describe Python's exception hierarchy.

```
BaseException
├── SystemExit                 (sys.exit)
├── KeyboardInterrupt          (Ctrl-C)
├── GeneratorExit              (generator .close())
├── BaseExceptionGroup         (3.11+)
└── Exception                  <- catch at or below THIS line
    ├── ArithmeticError → ZeroDivisionError, OverflowError, FloatingPointError
    ├── LookupError     → IndexError, KeyError
    ├── OSError         → FileNotFoundError, PermissionError, ConnectionError
    │                     (→ ConnectionResetError, BrokenPipeError), TimeoutError,
    │                     IsADirectoryError
    ├── ValueError      → UnicodeError → UnicodeDecodeError / UnicodeEncodeError
    ├── TypeError
    ├── AttributeError
    ├── RuntimeError    → RecursionError, NotImplementedError
    ├── StopIteration / StopAsyncIteration
    ├── ImportError     → ModuleNotFoundError
    ├── ExceptionGroup  (3.11+)
    └── Warning         → DeprecationWarning, ...
```

**The line that matters: `Exception` is the boundary.** Everything you should routinely catch is at
or below it; everything above it is control flow for the interpreter.

Useful groupings to know:

- **`LookupError`** catches both `KeyError` and `IndexError` — handy for generic lookup code.
- **`OSError`** unified `IOError`, `EnvironmentError`, `socket.error` and `WindowsError` in Python
  3.3. Network errors live here: `ConnectionResetError`, `BrokenPipeError`, `TimeoutError`.
- **`asyncio.TimeoutError` is an alias for the builtin `TimeoutError`** as of 3.11.
- `ValueError` = right type, wrong value. `TypeError` = wrong type entirely. Choose deliberately when
  raising your own.

---

### Q4. How do you create custom exceptions? Show a good hierarchy.

Subclass **`Exception`**, never `BaseException`. Define **one base for your application** so callers
can catch everything you raise with a single clause, then specific subclasses carrying structured
context.

```python
class AppError(Exception):
    """Base for every error this application raises deliberately."""

class ValidationError(AppError):
    def __init__(self, field, msg):
        super().__init__(f"{field}: {msg}")
        self.field = field                 # structured, not just a string
        self.msg = msg

class NotFoundError(AppError):
    def __init__(self, entity, entity_id):
        super().__init__(f"{entity} {entity_id} not found")
        self.entity, self.entity_id = entity, entity_id

class ConflictError(AppError): pass
class PaymentError(AppError): pass

# Orthogonal axis: is it safe to retry?
class RetryableError(AppError):     """Transient — the caller may retry."""
class PermanentError(AppError):     """Will never succeed — do not retry."""

try:
    raise ValidationError("amount", "must be positive")
except AppError as e:
    print(type(e).__name__, e, getattr(e, "field", None))
```

**Design rules worth stating:**

1. **One root per application/library.** Callers get a single clean catch point, and you can add
   subclasses later without breaking anyone.
2. **Carry structured data as attributes**, not only inside the message string. Downstream code
   needs `e.field`, not a regex over `str(e)`.
3. **Model the *decision*, not just the cause.** The `RetryableError` / `PermanentError` split is
   what lets a Kafka consumer decide "retry topic" versus "DLQ immediately" without a giant `if`
   over exception types — see [Kafka failure handling](15_kafka_failure_handling.md).
4. **Don't subclass builtins gratuitously.** Inheriting from `ValueError` can cause a caller's
   unrelated `except ValueError` to swallow your domain error.
5. **Never put secrets or PII in the message** — it will be logged.

---

### Q5. What is exception chaining? `raise ... from ...`?

When you translate a low-level error into a domain error, the original cause must survive or you've
thrown away the only useful debugging information.

- **Explicit chaining**: `raise NewError(...) from err` sets `__cause__` and prints
  *"The above exception was the direct cause of the following exception"*.
- **Implicit chaining**: raising inside an `except` block automatically sets `__context__` and prints
  *"During handling of the above exception, another exception occurred"*.
- **Suppression**: `raise NewError(...) from None` clears the context — use it when the low-level
  cause is noise (and never to hide a bug).

```python
import json

class ConfigError(Exception): pass

def load(s):
    try:
        return json.loads(s)
    except json.JSONDecodeError as e:
        raise ConfigError("invalid config file") from e   # preserves the root cause

try:
    load("{bad")
except ConfigError as e:
    print(e)                # invalid config file
    print(e.__cause__)      # Expecting property name enclosed in double quotes: line 1 ...
```

The traceback shows **both** stacks. Without `from e` you'd still get implicit chaining via
`__context__`, but `from` states the causal relationship explicitly — and `__cause__` is what
debuggers and error trackers (Sentry) key on.

**The anti-pattern to name:**

```python
except json.JSONDecodeError:
    raise ConfigError("invalid config")     # implicit context kept, but intent unclear
except json.JSONDecodeError as e:
    raise ConfigError(str(e))               # WORSE: flattens to a string, type and traceback lost
```

---

### Q6. How do you re-raise while preserving the traceback?

Use a **bare `raise`** inside the `except` block. It re-raises the *current* exception with its
traceback intact.

```python
import logging
log = logging.getLogger(__name__)

def process(x):
    try:
        return 1 / x
    except ZeroDivisionError:
        log.exception("bad input x=%s", x)   # logs message + full traceback
        raise                                # re-raise the ORIGINAL, unchanged
```

`raise e` also works in Python 3 (the traceback rides on the exception object), but it appends the
current line to the traceback, adding noise. Bare `raise` is the idiom.

**`logger.exception(...)` is the detail to get right.** It is equivalent to
`logger.error(..., exc_info=True)` and **must be called inside an `except` block** — outside one,
there's no active exception and it logs `NoneType: None`. Use `logger.exception` when handling,
`logger.error(..., exc_info=e)` when you have the exception object but aren't in its handler.

Note also: `log.exception("bad input x=%s", x)` uses **`%s` lazy formatting**, not an f-string. With
an f-string the message is formatted even when the log level would discard it, and structured log
aggregators lose the ability to group by message template.

---

### Q7. EAFP vs LBYL — which is Pythonic?

- **LBYL** ("Look Before You Leap") — check preconditions, then act.
- **EAFP** ("Easier to Ask Forgiveness than Permission") — just do it, handle the exception.

**Python favours EAFP**, for two concrete reasons:

1. **It eliminates TOCTOU race conditions.** Between `os.path.exists(p)` and `open(p)` another
   process can delete the file. The check bought you nothing but a false sense of safety.
2. **It avoids double lookups.** `if k in d: v = d[k]` hashes `k` twice; `try: v = d[k]` hashes once.

```python
# LBYL — two lookups, and racy for files/network
if "key" in d:
    v = d["key"]

# EAFP — one lookup, atomic
try:
    v = d["key"]
except KeyError:
    v = None

# For dicts specifically, the built-in is better than either
v = d.get("key")
```

**When LBYL is right:** when failure is *common* (exceptions are expensive if they fire on most
iterations), when the check is cheap and unambiguous, or when validating user input where you want to
collect *all* problems rather than stop at the first.

```python
# EAFP in a hot loop where most items fail = slow. Prefer a cheap check.
for s in million_strings:
    if s.isdigit():          # cheap check beats raising a million ValueErrors
        total += int(s)
```

---

### Q8. What are `ExceptionGroup` and `except*` (Python 3.11)?

An **`ExceptionGroup`** bundles several *unrelated* exceptions that were raised together — the
natural result of concurrent work where three of ten tasks failed for three different reasons.
Before 3.11 you had to pick one to raise and lose the rest.

**`except*`** handles each *type within* the group separately. Multiple `except*` clauses can all run
for a single group, and anything unmatched propagates as a smaller group.

```python
try:
    raise ExceptionGroup("batch failed", [
        ValueError("bad row 3"),
        KeyError("id"),
        ValueError("bad row 9"),
    ])
except* ValueError as eg:
    print("value errors:", [str(e) for e in eg.exceptions])   # both ValueErrors
except* KeyError as eg:
    print("key errors:", [str(e) for e in eg.exceptions])
```

**Where you meet it for real: `asyncio.TaskGroup`.** If several tasks fail, the group raises an
`ExceptionGroup` containing all of them:

```python
import asyncio

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fails_with_value_error())
            tg.create_task(fails_with_timeout())
    except* ValueError as eg:
        log.error("validation failures: %s", eg.exceptions)
    except* TimeoutError as eg:
        log.error("timeouts: %s", eg.exceptions)
```

Two details: `except*` and plain `except` **cannot be mixed** in the same `try`; and
`BaseExceptionGroup` is used automatically if any member is a `BaseException` (e.g. `CancelledError`)
so that those aren't accidentally caught by `except* Exception`.

---

### Q9. What happens when `return` appears in both `try` and `finally`?

**The `finally` return wins, and it silently discards both the `try`'s return value and any in-flight
exception.** This is a genuine footgun.

```python
def f():
    try:
        return "try"
    finally:
        return "finally"

print(f())      # 'finally'

def g():
    try:
        raise ValueError("boom")
    finally:
        return "swallowed"

print(g())      # 'swallowed' — the ValueError VANISHES. No traceback, no log, nothing.
```

`break` and `continue` in a `finally` do the same thing. **Python 3.14 emits a `SyntaxWarning`** for
`return`/`break`/`continue` in a `finally` block precisely because it's so reliably a bug.

**The rule: `finally` is for cleanup only — never for control flow.** If you need a fallback value,
compute it in an `except` clause.

---

### Q10. How do you add context to an exception without changing its type? (3.11+)

`err.add_note("...")` attaches a string that prints below the traceback. It preserves the exception's
type and traceback, so `except SpecificError` clauses upstream still match — which is exactly what
you want when you're enriching, not translating.

```python
rows = ["1", "x", "3"]
for i, r in enumerate(rows):
    try:
        int(r)
    except ValueError as e:
        e.add_note(f"row index {i}")
        e.add_note(f"raw value {r!r}")
        raise
# ValueError: invalid literal for int() with base 10: 'x'
# row index 1
# raw value 'x'
```

Before 3.11 the options were worse: re-raise a new exception (changing the type and breaking callers'
`except` clauses), or mutate `e.args` (fragile). `add_note` is the clean answer.

In a batch pipeline, note the record ID, batch number, and source topic/offset — that's the
difference between a five-minute fix and an afternoon of log archaeology.

---

### Q11. How do you handle errors in a thread or process pool?

**An exception inside a worker is captured in the `Future` and re-raised when you call
`future.result()`.** If you never call `result()`, the failure is **completely silent** — no log, no
traceback, no non-zero exit code. This is the most common concurrency bug in production Python.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def job(x):
    if x == 2:
        raise ValueError("bad")
    return x

# WRONG — submit and forget. The ValueError disappears.
with ThreadPoolExecutor() as ex:
    for i in range(4):
        ex.submit(job, i)

# RIGHT — always consume results, handling each independently
with ThreadPoolExecutor() as ex:
    futures = {ex.submit(job, i): i for i in range(4)}
    for fut in as_completed(futures):
        i = futures[fut]
        try:
            print("ok", fut.result())
        except Exception:
            log.exception("job %s failed", i)
```

**Three related points:**

1. **`ex.map` re-raises on iteration**, at the position of the failing item — so later results are
   never reached. `submit` + `as_completed` lets every task report independently.
2. **Process pools require picklable exceptions.** A custom exception whose `__init__` takes extra
   required arguments can fail to unpickle, and you get a confusing secondary error. Keep custom
   exceptions simple, or implement `__reduce__`.
3. **For manually-started threads**, an unhandled exception prints to stderr and kills only that
   thread. Install `threading.excepthook` to route these into your logger:

```python
import threading
def hook(args):
    log.error("uncaught in thread %s", args.thread.name,
              exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
threading.excepthook = hook
```

For asyncio the equivalents are `loop.set_exception_handler(...)` and, crucially, **keeping a
reference to every `create_task()` result** — a task whose only reference is dropped can be garbage
collected mid-flight, and its exception is reported as "Task exception was never retrieved" (or lost).

---

### Q12. Design a retry strategy for transient failures.

The principles, in the order they matter:

1. **Only retry transient errors.** Timeouts, connection resets, HTTP 429/502/503/504, DB deadlocks.
   **Never** retry validation errors, 400s, 401/403, or anything deterministic — you'll just fail
   three times more slowly. This is what a `RetryableError`/`PermanentError` split buys you (Q4).
2. **Exponential backoff**: `delay = base * 2**attempt`. Gives the downstream room to recover.
3. **Jitter**, and this is not optional. Without it, every client that failed at the same instant
   retries at the same instant, so the recovering service gets a synchronised thundering herd and
   falls over again. Full jitter (`random.uniform(0, delay)`) or equal jitter is standard.
4. **Cap attempts *and* total elapsed time.** A caller with a 5 s SLA doesn't want 5 retries over
   60 s; fail fast instead.
5. **The operation must be idempotent**, or a retry after a *partial* success double-charges the
   customer. Use an idempotency key.
6. **Log every attempt** with the attempt number and the error, and emit a metric — retry rate is a
   leading indicator of a downstream problem.
7. **After the final failure**, surface the error or route to a DLQ. Don't swallow.

```python
import random, time, logging

log = logging.getLogger(__name__)

class RetryableError(Exception): pass

def retry(fn, *, attempts=5, base=0.2, cap=5.0, deadline=30.0,
          retry_on=(TimeoutError, ConnectionError, RetryableError)):
    started = time.monotonic()
    for i in range(attempts):
        try:
            return fn()
        except retry_on as e:
            elapsed = time.monotonic() - started
            if i == attempts - 1 or elapsed > deadline:
                log.error("giving up after %d attempts / %.1fs", i + 1, elapsed)
                raise
            delay = min(cap, base * 2 ** i)
            delay = random.uniform(0, delay)          # full jitter
            log.warning("attempt %d failed (%s), retrying in %.2fs", i + 1, e, delay)
            time.sleep(delay)
```

**In production use `tenacity`** (or `backoff`) rather than hand-rolling — it handles async, gives
you `stop_after_attempt`/`wait_exponential_jitter`/`retry_if_exception_type` declaratively, and has
the edge cases right. But be able to write the above from memory.

**Pair retries with a circuit breaker.** Retrying into a service that is fully down just multiplies
load. The breaker fails fast once the error rate crosses a threshold. See
[Scaling](12_scaling_applications.md) and
[`08_scaling_production_resilience/02_circuit_breaker.py`](../08_scaling_production_resilience/02_circuit_breaker.py).

---

### Q13. How should a REST API map exceptions to responses?

**Raise domain exceptions in the service layer; translate them centrally.** The router should contain
no `try/except` for domain errors, and HTTP status codes should be decided in exactly one place.

The mapping:

| Domain condition | HTTP | Notes |
|---|---|---|
| Malformed/invalid input | **400** / **422** | 422 for schema validation (FastAPI's default) |
| Not authenticated | **401** | Include `WWW-Authenticate` |
| Authenticated but not allowed | **403** | |
| Entity not found | **404** | |
| Duplicate / state conflict | **409** | |
| Payload too large | **413** | |
| Unsupported media type | **415** | |
| Rate limited | **429** | Include `Retry-After` |
| Unexpected | **500** | **Correlation ID only — never leak internals** |
| Downstream unavailable | **503** | Include `Retry-After` |

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import logging, uuid

class AppError(Exception):
    status, code = 500, "INTERNAL"

class NotFound(AppError):  status, code = 404, "NOT_FOUND"
class Conflict(AppError):  status, code = 409, "CONFLICT"
class Invalid(AppError):   status, code = 422, "VALIDATION_ERROR"

app = FastAPI()
log = logging.getLogger("api")

@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError):
    cid = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    log.error("cid=%s path=%s %s", cid, request.url.path, exc, exc_info=exc)
    return JSONResponse(
        status_code=exc.status,
        content={"code": exc.code, "message": str(exc), "correlation_id": cid},
    )

@app.exception_handler(Exception)                    # the safety net
async def handle_unexpected(request: Request, exc: Exception):
    cid = str(uuid.uuid4())
    log.exception("cid=%s unhandled", cid)
    return JSONResponse(500, content={
        "code": "INTERNAL",
        "message": "An unexpected error occurred",   # deliberately vague
        "correlation_id": cid,                       # the user quotes this to support
    })

@app.get("/orders/{oid}")
async def get_order(oid: int):
    raise NotFound(f"order {oid} not found")          # no try/except in the router
```

**Four things to say:**

- **Never leak internals** — stack traces, SQL, file paths, library versions — in a 500 response.
  They're reconnaissance for an attacker. Log them server-side, return a correlation ID.
- **The correlation ID is the whole point**: the user quotes it to support, support greps the logs,
  and you have the exact traceback. See
  [Production stability](19_production_stability_monitoring.md).
- **Consistent error shape** across every endpoint — clients can parse one structure.
- **Registering the handlers in one place** (`main.py`) is what makes status codes auditable; this is
  exactly how [the app in this repo](../05_web_apis_fastapi/app/main.py) is wired.

---

### Q14. What is the cost of exceptions in Python?

**Entering a `try` block is essentially free** in Python 3.11+ (PEP 659 "zero-cost exceptions").
Previously the interpreter pushed a block onto a stack on every `try`; now the compiler emits an
exception table consulted **only when an exception actually occurs**. So wrapping code in `try` costs
nothing on the happy path.

**Raising and catching is comparatively expensive** — roughly microseconds. It allocates an exception
object, captures a traceback frame by frame, and unwinds.

The practical guidance:

- **Exceptional paths: use exceptions freely.** That is what they're for, and EAFP is idiomatic.
- **Frequent normal control flow in a hot loop: don't.** If half your million iterations raise, a
  cheap `if` check is far faster.

```python
import timeit

setup = "d = {'a': 1}"
print(timeit.timeit("d['a']", setup=setup))                                  # fastest
print(timeit.timeit("try: d['zz']\nexcept KeyError: pass", setup=setup))     # ~5-10x slower
print(timeit.timeit("d.get('zz')", setup=setup))                             # fast, no raise
```

The classic exception used as control flow is **`StopIteration`**, raised once per iterator
exhaustion — which is fine because it fires *once*, not per item.

---

## Worked example — layered error handling in a Kafka consumer

Everything above combined: a hierarchy that encodes the retry decision, narrow catching, chaining,
notes, and a central routing decision.

```python
import json, logging, traceback

log = logging.getLogger("orders")

class AppError(Exception): pass
class Transient(AppError):  """Retry: timeout, 503, DB deadlock."""
class Permanent(AppError):  """DLQ immediately: bad schema, failed validation."""

def handle_message(msg, producer, consumer):
    try:
        try:
            event = json.loads(msg.value())
        except json.JSONDecodeError as e:
            raise Permanent("unparseable payload") from e      # chain the root cause

        try:
            validate(event)
            process_idempotently(event)                        # dedupe on event_id
        except ValidationError as e:
            raise Permanent(f"invalid event: {e}") from e
        except (TimeoutError, ConnectionError) as e:
            raise Transient(f"downstream unavailable: {e}") from e

    except Transient as e:
        e.add_note(f"topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}")
        log.warning("transient failure, routing to retry topic", exc_info=e)
        route_to_retry_topic(producer, msg, e)

    except Permanent as e:
        e.add_note(f"topic={msg.topic()} offset={msg.offset()}")
        log.error("poison pill, routing to DLQ", exc_info=e)
        send_to_dlq(producer, msg, e)

    except Exception:
        log.exception("UNEXPECTED — treating as poison to avoid blocking the partition")
        send_to_dlq(producer, msg, RuntimeError("unexpected"))

    finally:
        consumer.commit(message=msg, asynchronous=False)   # advance in EVERY case
        # NOTE: no `return` here — that would discard any in-flight exception (Q9)
```

**Why it's shaped this way:**

- The **`Transient` / `Permanent` split is the decision**, made where the error occurs and acted on
  where the routing lives. No giant `isinstance` ladder.
- **`from e` everywhere** so the DLQ record and the logs carry the genuine root cause.
- **`add_note`** attaches the Kafka coordinates without changing the exception type.
- **The catch-all** stops one unexpected bug blocking the partition forever — but it logs the full
  traceback and still DLQs, so nothing is silently lost.
- **`finally` commits** so the consumer always advances; a poison pill must never wedge the partition.
  And it does *not* `return`.

See [Kafka failure handling](15_kafka_failure_handling.md) for the full retry-topic/DLQ design.

---

## Hands-on drills

1. Write a loop with a bare `except:` and try to Ctrl-C out of it. Then change it to
   `except Exception:` and try again. Explain the difference in one sentence.
2. Write `f()` with `return` in both `try` and `finally`. Then make the `try` raise. Watch the
   exception disappear. Run it on 3.14 and look for the `SyntaxWarning`.
3. Build a three-level custom hierarchy and catch at each level, showing that the base catches all.
4. Raise `ConfigError from e` and print `e.__cause__` and `e.__context__`. Then use `from None` and
   see what changes in the traceback.
5. Submit 10 jobs to a `ThreadPoolExecutor` where 3 raise, and **never** call `result()`. Confirm
   total silence. Then add `as_completed` + `result()`.
6. Write `retry()` with and without jitter. Simulate 100 clients failing simultaneously, log the
   retry timestamps, and plot/print the distribution to see the thundering herd.
7. Use `asyncio.TaskGroup` with three tasks failing with different types. Handle them with `except*`.
8. Time `d['missing']` in a try/except versus `d.get('missing')` over 1,000,000 iterations. State
   when each is the right choice.

---

## The 60-second spoken answer

> "I catch the narrowest exception I can act on — never a bare `except:`, because that catches
> `KeyboardInterrupt`, `SystemExit` and `CancelledError` and makes the process unkillable. I use
> `else` for the success path so my `except` doesn't accidentally swallow it, and `finally` strictly
> for cleanup — never a `return` there, because that silently discards both the return value and any
> in-flight exception. I define one application base exception with specific subclasses carrying
> structured attributes, and I split them on the *decision*: retryable versus permanent, which is
> what lets a consumer choose retry-topic versus DLQ without an isinstance ladder. When I translate a
> low-level error I use `raise ... from err` so the root cause survives, and `add_note` when I just
> want to attach context like a Kafka offset. In a REST API domain exceptions propagate to central
> `exception_handler` registrations so status codes are decided in one place, and a 500 returns only
> a correlation ID — never a stack trace. For retries: only transient errors, exponential backoff
> with jitter, a cap on attempts and total time, and the operation must be idempotent. And I always
> call `future.result()` on pool futures, because otherwise worker exceptions vanish completely."
