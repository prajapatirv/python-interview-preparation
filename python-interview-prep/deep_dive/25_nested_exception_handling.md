# Deep Dive 25 — Multi-Level Exception Handling and `with`

> Runnable companion: [`01_python_core/15_nested_exception_handling.py`](../01_python_core/15_nested_exception_handling.py)
> Prerequisite: [08 — Error handling](08_error_handling.md) (the single-level basics) ·
> [05 — Context managers](05_context_managers_descriptors_metaclasses.md)
> Related: [15 — Kafka failure handling](15_kafka_failure_handling.md) ·
> [10 — Web frameworks](10_web_frameworks.md) · [19 — Production stability](19_production_stability_monitoring.md)

## What interviewers are actually probing

[Deep dive 08](08_error_handling.md) covers one `try` with one `except`. This one covers what happens
when error handling gets **deep** — several `except` clauses on one `try`, nested `try` blocks, errors
crossing layer boundaries, `with` blocks that may swallow failures, and several things failing at
once. That's where the real bugs live, and the bugs are all variants of one theme:

> **An exception that was silently replaced, swallowed, or lost.**

What they're listening for:

- Do you know `except` clauses are checked **top-down** so a parent class above a child makes the
  child's handler **dead code** — with no warning from Python?
- Do you know an exception raised in `finally` **destroys** the one in flight?
- Can you describe **error translation across layers** (repo → service → API) without an
  `isinstance` ladder?
- Do you know `__exit__` returning `True` **swallows** the exception, and why that's catastrophic on
  a payment and fine on an audit log?
- Do you know `ExceptionGroup` / `except*` and *why* it had to exist (concurrency produces several
  independent failures, and one exception object can't represent two outages)?

---

## Must-know points

- **Multiple `except` clauses are tried top-down; the first match wins.** Order **subclass before
  superclass**, or the specific handler is unreachable. Python does not warn.
- A **tuple** `except (KeyError, IndexError) as e:` is one handler for several types.
- **Nested `try`**: handle at the layer that can actually *do* something; let everything else
  propagate. Each layer translates the layer below's errors into its own, with `raise ... from e`.
- **Execution order**: `try` → (`except` | `else`) → `finally`. `finally` runs on success, on
  exception, and on `return`/`break`/`continue`. `else` runs **only** when nothing was raised.
- **Never `return` from `finally`** — it discards both the pending return value *and* any in-flight
  exception. **Never `raise` from `finally`** either — it replaces the real error.
- **`raise X` inside `except` sets `__context__`** (implicit chaining); **`raise X from e` sets
  `__cause__`** (explicit). `from None` suppresses the chain. Prefer explicit.
- **`except ... as e` deletes `e`** at the end of the block — copy it out if you need it after.
- **`__exit__` returning `True` swallows** the exception; `False`/`None` lets it propagate. In the
  `@contextmanager` form, the exception surfaces **at the `yield`**.
- Nested `with` cleans up **innermost-first**, even when the body raises. `contextlib.ExitStack` for
  a dynamic number of resources.
- **`ExceptionGroup` + `except*`** (3.11+): several failures at once; **multiple `except*` branches
  can all run** for one group. `asyncio.TaskGroup` raises these.
- **`add_note()`** (3.11+) attaches context without changing the exception type.

---

## Interview questions and full answers

### Q1. How are multiple `except` clauses evaluated, and what's the classic bug?

**Top-down, first match wins — and a match is `isinstance`-based.** So a parent class listed above a
child makes the child's clause **dead code**:

```python
def wrong_order(path):
    try:
        open(path)
    except OSError:                 # FileNotFoundError IS an OSError → this always wins
        return "generic branch"
    except FileNotFoundError:       # UNREACHABLE. No warning, no error, ever.
        return "never runs"
```

The correct order, specific to general:

```python
try:
    ...
except FileNotFoundError as e:        # most specific
    ...
except PermissionError as e:
    ...
except OSError as e:                  # the parent, as the catch-all for this family
    ...
except Exception:                     # last-resort net, and it LOGS and RE-RAISES
    log.exception("unexpected")
    raise
```

Three things worth adding:

**1. Nothing catches this for you.** No linter flags unreachable `except` clauses by default, and
there's no runtime error. The only defence is knowing the hierarchy
([08 — Error handling](08_error_handling.md) Q3) and a test per branch.

**2. Group with a tuple when the handling is identical**, and *don't* when it isn't:

```python
except (KeyError, IndexError) as e:            # same handling → one clause
    return f"lookup failed: {e}"
```

**3. Order by decision, not by taxonomy.** In production code the useful ordering is usually
*retryable → permanent → unknown*, because that's what the handler does differently:

```python
except (TimeoutError, ConnectionError) as e:   # transient → retry
    schedule_retry(msg, e)
except (ValidationError, json.JSONDecodeError) as e:   # permanent → DLQ
    send_to_dlq(msg, e)
except Exception:                               # unknown → log loudly, DLQ, keep the consumer alive
    log.exception("unexpected; treating as poison")
    send_to_dlq(msg, RuntimeError("unexpected"))
```

That shape — the **transient/permanent split** — is the single most reusable idea in this document.
It appears again in Kafka consumers ([15](15_kafka_failure_handling.md)), retry decorators
([26](26_coding_design_problems.md)) and HTTP clients.

---

### Q2. When do you nest `try` blocks instead of adding more `except` clauses?

**Nest when different parts of the body have different recovery strategies.** The guiding rule:
**handle an error at the layer that can actually do something about it.**

```python
def load_settings(raw):
    try:                                       # OUTER: whatever the inner layers can't fix
        try:                                   # INNER 1: an unparseable payload IS recoverable
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("payload unparseable, falling back to defaults")
            parsed = dict(DEFAULTS)

        try:                                   # INNER 2: a missing key IS recoverable
            timeout = parsed["timeout"]
        except KeyError:
            timeout = DEFAULTS["timeout"]

        return {"timeout": int(timeout)}       # a bad TYPE is NOT recoverable here
    except (TypeError, ValueError) as e:
        raise ValueError(f"settings unusable: {e}") from e
```

Each inner block is **narrow** — one statement, one expected failure, one recovery. The outer block
converts anything left into a single meaningful error for the caller.

**The anti-pattern this replaces** is one giant `try` around twenty lines with five `except` clauses.
Its problem is that you can no longer tell *which* statement raised: a `KeyError` could be the config
lookup or the response parsing, and the recovery for those is completely different.

**The other anti-pattern is nesting for its own sake.** Three levels of `try` in one function is a
smell; extract functions instead. The depth should come from **layers**, not from one function's
ambition — which is Q3.

---

### Q3. How do you handle errors across layers (repository → service → API)?

**Each layer catches the layer below's exception type and raises its own, with `from e` to preserve
the root cause.** The low-level type never leaks upward.

```python
class AppError(Exception): pass
class RepositoryError(AppError): pass
class ServiceError(AppError): pass

def repository_layer(order_id):
    """Knows about STORAGE. Translates driver errors into repository errors."""
    try:
        return db.fetch_one(order_id)              # may raise psycopg/OSError
    except OSError as e:
        raise RepositoryError(f"storage unavailable for {order_id}") from e

def service_layer(order_id):
    """Knows about BUSINESS RULES. Never lets a storage type reach the caller."""
    try:
        row = repository_layer(order_id)
    except RepositoryError as e:
        raise ServiceError("could not load order; try again later") from e
    if row is None:
        raise OrderNotFound(order_id)
    return row

@app.exception_handler(OrderNotFound)              # the API layer: the ONLY place status codes live
async def not_found(request, exc):
    return JSONResponse(status_code=404, content={"detail": str(exc)})

@app.exception_handler(ServiceError)
async def unavailable(request, exc):
    log.exception("service error", exc_info=exc)   # the WHOLE chain lands in the log
    return JSONResponse(status_code=503,
                        content={"detail": "temporarily unavailable",
                                 "correlation_id": correlation_id.get()})
```

**Why this shape, point by point:**

- **The router catches nothing.** Domain exceptions propagate to centrally-registered handlers, so
  status codes are decided in **one** place and can't drift between endpoints. That's exactly how
  [`05_web_apis_fastapi/`](../05_web_apis_fastapi/) is built.
- **`from e` everywhere**, so the 503's log line still shows the TCP reset at the bottom of the
  chain. Without it you get "could not load order" and no idea why.
- **No `isinstance` ladder.** The *type* carries the decision. Adding a new failure mode means adding
  a subclass, not editing a dispatch chain.
- **One base (`AppError`)** means a boundary can say `except AppError` for "something we anticipated"
  versus `except Exception` for "a bug".
- **The 503 body contains a correlation ID, never a stack trace.** The trace goes to the log; the
  customer gets an ID they can quote to support ([28 — Observability](28_observability_distributed_systems.md)).

**The subtlety worth raising unprompted:** don't translate *too* eagerly. Converting
`TimeoutError` into a generic `ServiceError` at the bottom destroys the retryable/permanent
distinction the caller needs. Either keep a `TransientServiceError` subclass, or carry a
`retryable: bool` attribute on the exception. The error type is an API; design it.

---

### Q4. What's the exact execution order of `try`/`except`/`else`/`finally`?

```python
def trace(mode):
    order = []
    try:
        order.append("try")
        if mode == "raise":  raise ValueError("boom")
        if mode == "return": order.append("return-computed"); return order
    except ValueError:
        order.append("except")
    else:
        order.append("else")          # ONLY when nothing was raised
    finally:
        order.append("finally")       # ALWAYS
    order.append("after-block")
    return order
```

| mode | result |
|---|---|
| `"ok"` | `['try', 'else', 'finally', 'after-block']` |
| `"raise"` | `['try', 'except', 'finally', 'after-block']` |
| `"return"` | `['try', 'return-computed', 'finally']` |

The two details that matter:

**1. On `return`, the value is computed first, then `finally` runs, then the value is handed back.**
So `finally` can observe state after the return value exists, but the caller still gets the original
value — *unless* `finally` returns (Q5).

**2. `else` exists to keep your `except` narrow.** Putting the success path in `else` means its
errors can't be swallowed by your handler:

```python
try:
    f = open(path)                 # ONLY the risky call
except FileNotFoundError:
    return {}
else:
    with f:
        return json.load(f)        # a JSONDecodeError here PROPAGATES — it isn't
                                   # caught by the FileNotFoundError handler
```

If `json.load` were inside the `try`, then the day someone broadens `except FileNotFoundError` to
`except OSError` or `except Exception`, parse failures start being silently swallowed too. `else`
makes that impossible.

---

### Q5. What are the three ways nested handling silently loses an error?

This is the highest-value question in the topic. All three are invisible in review unless you know
to look.

**TRAP 1 — raising inside `except` without `from`.**

```python
try:
    try:
        1 / 0
    except ZeroDivisionError:
        raise ValueError("replaced")
except ValueError as e:
    e.__cause__       # None
    e.__context__     # ZeroDivisionError — implicit chaining kept it
```

The original *is* preserved in `__context__` and printed as *"During handling of the above exception,
another exception occurred"*. But `from e` sets `__cause__`, which prints as *"The above exception was
the direct cause"* and states the relationship **deliberately**. The difference matters for tooling:
Sentry and most log aggregators group and display `__cause__` chains properly. Use `from e` when you
mean "this error is because of that one", and `from None` when the inner error is noise you're
deliberately hiding:

```python
except KeyError:
    raise ConfigError("missing 'timeout' in config") from None   # the KeyError adds nothing
```

**TRAP 2 — raising (or returning) in `finally` destroys the exception in flight.**

```python
def overwrite():
    try:
        raise ValueError("the real problem")
    finally:
        raise RuntimeError("cleanup also failed")    # THIS reaches the caller

# caller sees RuntimeError; the ValueError survives only in __context__
```

`return` in `finally` is worse, because it loses the error *silently*:

```python
def footgun():
    try:
        raise ValueError("boom")
    finally:
        return "fine"          # the ValueError VANISHES. No trace, no log, no clue.
footgun()                      # 'fine'
```

Python 3.14 emits a `SyntaxWarning` for `return` in `finally` — which tells you how bad it is. The
rule: **`finally` is for cleanup only. It must not return, and it must not raise.** If cleanup can
fail, handle it there:

```python
finally:
    try:
        conn.close()
    except Exception:
        log.warning("failed to close connection", exc_info=True)   # log, don't raise
```

**TRAP 3 — an over-broad inner handler eats what the outer one was meant to see.**

```python
def over_broad(records):
    processed = []
    for r in records:
        try:
            processed.append(int(r))
        except Exception:        # swallows EVERYTHING — a typo'd attribute, a KeyboardInterrupt path
            continue             # ...and `continue` means ZERO evidence it happened
    return processed

over_broad(["1", "x", "3"])      # [1, 3] — the 'x' row vanished with no log line and no metric
```

A silently skipped row is a data bug nobody finds for weeks. The fix is **narrow + count + log**:

```python
def fixed(records):
    processed, skipped = [], []
    for r in records:
        try:
            processed.append(int(r))
        except ValueError as e:                  # NARROW: only the failure we expected
            skipped.append((r, str(e)))
    if skipped:
        log.warning("skipped %d malformed rows: %s", len(skipped), skipped[:10])
        metrics.inc("rows_skipped_total", len(skipped))   # ALERTABLE
    return processed, skipped
```

**The principle behind all three: silence is the sin, not breadth.** A broad `except Exception` at a
boundary (a consumer loop, a request handler) is legitimate and necessary — *provided* it logs the
traceback, increments a metric, and either re-raises or routes the item somewhere a human can find it.

---

### Q6. How do `with` and exceptions interact? What does `__exit__` returning `True` mean?

`__exit__(exc_type, exc, tb)` is called **whichever way the block ends**. Its **return value decides
whether the exception propagates**: truthy swallows it, falsy (`False`/`None`) lets it through.

```python
class Transaction:
    def __enter__(self):
        print("BEGIN"); return self
    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            print("COMMIT"); return False
        print(f"ROLLBACK (saw {exc_type.__name__}: {exc})")
        return self.swallow          # ← the load-bearing line
```

- **`return False`** — roll back, then let the caller see the error. **Correct for a payment.**
- **`return True`** — roll back and pretend nothing happened. **Correct for a best-effort audit-log
  write.** Catastrophic on a payment: the caller is told the charge succeeded.

**Getting this backwards is a real incident**, and it's why a reviewer should reject any `__exit__`
returning a bare `True`. The defensible version swallows exactly one expected type:

```python
def __exit__(self, exc_type, exc, tb):
    if exc_type is None:
        self.commit(); return False
    self.rollback()
    return issubclass(exc_type, AuditWriteError)    # swallow ONLY this, and say so in the name
```

In the generator form, the exception is **thrown in at the `yield`**, so you handle it with an
ordinary `try`:

```python
@contextmanager
def generator_style(name):
    print(f"enter {name}")
    try:
        yield name
    except ValueError as e:              # equivalent to returning True for ValueError only
        print(f"handled: {e}")
    finally:
        print(f"exit {name}")            # equivalent to the cleanup half of __exit__
```

Three more things worth knowing:

- **`contextlib.suppress(FileNotFoundError, PermissionError)`** is the readable, explicitly-typed
  "ignore these two". Infinitely better than `try/except/pass` because the intent is in the name.
- **Reraising from `__exit__`** wraps/translates: `raise RepositoryError(...) from exc` inside
  `__exit__` is a legitimate way to do the Q3 translation at a resource boundary.
- **`__exit__` must not raise during normal exit** either — same reason as `finally` (it *is* the
  `finally`).

---

### Q7. In what order does nested cleanup run, and what if there are N resources?

**Innermost-first (reverse of acquisition), even when the body raises** — the same guarantee as nested
`finally`:

```python
with resource("outer-conn"), resource("inner-cursor"):   # one `with`, two managers
    raise ValueError("work failed")
# close inner-cursor
# close outer-conn
# then ValueError propagates
```

That ordering is the whole point: the cursor must close before the connection, and the transaction
must roll back before the connection returns to the pool.

**For an unknown-at-write-time number of resources, `ExitStack`:**

```python
with ExitStack() as stack:
    files = [stack.enter_context(open(p)) for p in paths]      # N files, N unknown
    # all closed in reverse order on exit, even if one open() raised midway
```

`ExitStack` also gives you:

- **`stack.callback(fn, *args)`** — run arbitrary cleanup on exit without writing a context manager.
- **`stack.push(cm)`** — register an already-entered manager.
- **`stack.pop_all()`** — *transfer* ownership of the cleanup to the caller. This is the idiom for a
  factory that acquires several resources and must not leak if a later step fails:

```python
def open_connections(dsns):
    with ExitStack() as stack:
        conns = [stack.enter_context(connect(d)) for d in dsns]
        validate(conns)                      # if this raises, EVERY conn is closed
        stack.pop_all()                      # success: hand ownership to the caller
        return conns
```

And `AsyncExitStack` for `async with`. See
[`01_python_core/05_context_managers.py`](../01_python_core/05_context_managers.py).

---

### Q8. What is `ExceptionGroup` / `except*`, and why did it have to exist?

**Because concurrency produces several independent failures at once, and a single exception object
cannot represent two separate outages.**

```python
def fan_out():
    raise ExceptionGroup("3 of 3 downstream calls failed", [
        TimeoutError("inventory-service timed out"),
        ValueError("pricing-service returned a malformed payload"),
        TimeoutError("tax-service timed out"),
    ])

try:
    fan_out()
except* TimeoutError as eg:              # handles ONLY the timeouts in the group
    schedule_retry(eg.exceptions)        # 2 of them — retryable
except* ValueError as eg:                # ...and THIS BRANCH ALSO RUNS, same group
    send_to_dlq(eg.exceptions)           # 1 of them — a poison payload
```

**The behavioural difference from plain `except`: several `except*` branches can run for one raise.**
Python splits the group by type, routes each sub-group to the matching branch, and re-raises anything
unmatched as a smaller group. With plain `except`, the first match wins and the other failures are
invisible — which is exactly the information loss that motivated PEP 654.

**Where you meet it without asking for it:** `asyncio.TaskGroup`.

```python
async with asyncio.TaskGroup() as tg:        # 3.11+
    tg.create_task(fetch_inventory())
    tg.create_task(fetch_pricing())
    tg.create_task(fetch_tax())
# if two tasks fail, this raises an ExceptionGroup containing BOTH
```

That's why `TaskGroup` is strictly better than bare `asyncio.gather`: `gather(return_exceptions=False)`
raises only the *first* exception and leaves the rest as "exception never retrieved" warnings;
`gather(return_exceptions=True)` returns them in a list you must remember to inspect. `TaskGroup` also
cancels siblings on first failure and guarantees nothing is left running. See
[07 — Concurrency](07_concurrency.md).

Details worth having ready:

- **`BaseExceptionGroup`** is the parent; `ExceptionGroup` only holds `Exception` subclasses. A group
  containing `KeyboardInterrupt` is a `BaseExceptionGroup`, and `except*` won't quietly catch it.
- **You can still catch the whole thing**: `except ExceptionGroup as eg:` then inspect
  `eg.exceptions`.
- **Groups nest**, and `eg.subgroup(T)` / `eg.split(T)` let you filter them programmatically.
- **You cannot mix** `except` and `except*` on the same `try`, and you can't `except*` a bare
  `ExceptionGroup` type.
- **Validation is the non-async use case**: collecting *all* field errors rather than failing on the
  first is a better API, and a group expresses it precisely. (Pydantic does the same thing with its
  own error-list type.)

---

### Q9. What is `add_note()` for?

Attaching context **without changing the exception type** (3.11+):

```python
try:
    process(msg)
except TransientError as e:
    e.add_note(f"topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}")
    e.add_note(f"consumer_group={group} attempt=4/4")
    raise
```

Notes are stored in `e.__notes__` and **printed with the traceback**, so the on-call engineer gets the
Kafka coordinates for free.

**Why it's better than the alternatives:**

- `raise TransientError(f"{old} (topic={t} offset={o})")` — changes the message, so log-based
  grouping and alerting break every time you add context.
- `raise WrappedError(...) from e` — changes the *type*, so a caller's `except TransientError` no
  longer matches. That's a behavioural change dressed as logging.
- `add_note` changes neither type nor message. Handlers above still match; humans still get context.

Use it at each layer you pass through: the consumer adds the offset, the service adds the order ID,
the retry wrapper adds the attempt number. By the time it's logged the traceback carries the whole
story, and no handler's matching behaviour changed.

---

## Java contrast

| Java | Python |
|---|---|
| `catch` blocks checked top-down; **the compiler rejects** an unreachable subclass catch | checked top-down; an unreachable `except` is **silently dead code** |
| `catch (A \| B e)` multi-catch | `except (A, B) as e:` |
| Checked exceptions — the compiler forces `throws`/`catch` | no checked exceptions; the signature says nothing about what can be raised |
| `try-with-resources` closes in reverse order | `with` (nested, or `ExitStack` for N) — same ordering guarantee |
| `AutoCloseable.close()` **cannot** suppress the exception | `__exit__` returning `True` **does** suppress it |
| `return` in `finally` discards the exception (and the compiler warns) | identical behaviour; `SyntaxWarning` only from 3.14 |
| `e.getCause()` / `initCause()` | `e.__cause__` (from `raise ... from`) and `e.__context__` (implicit) |
| `addSuppressed()` for try-with-resources extras | `ExceptionGroup`, and `__context__` |
| `e` stays in scope after `catch` | **`e` is deleted** at the end of the `except` block |
| No standard "several failures at once" type | `ExceptionGroup` + `except*` (3.11+) |

**The two that trip Java developers hardest:** no checked exceptions (you must read the code or the
docs to know what a call raises — which is *why* a documented custom hierarchy matters so much more in
Python), and `except ... as e` deleting `e`. The second one bites in retry loops:

```python
last_error = None
for attempt in range(1, 4):
    try:
        return call()
    except TransientError as e:
        last_error = e          # COPY IT OUT — `e` is gone after this block
raise last_error
```

---

## A worked example

A Kafka consumer handler: multi-level `except`, layer translation, `with` for the transaction, notes
for context, and a group for the batch. This is the shape to draw on a whiteboard.

```python
import json, logging
from contextlib import contextmanager

log = logging.getLogger("orders")

class AppError(Exception): pass
class Transient(AppError):  """Retry: timeout, 503, DB deadlock, Aurora failover."""
class Permanent(AppError):  """DLQ immediately: bad schema, failed validation."""


@contextmanager
def transaction(conn):
    """Rolls back on ANY error and RE-RAISES (returns falsy). It deliberately does not swallow:
    a silently-swallowed rollback is how 'the data just isn't there' incidents happen."""
    conn.begin()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise                              # <-- NOT `return True`. Never swallow a write failure.
    else:
        conn.commit()
    finally:
        try:
            conn.release()                 # cleanup that can itself fail
        except Exception:
            log.warning("failed to release connection", exc_info=True)   # LOG, don't raise


def handle_message(msg, conn, producer, consumer, attempt=1):
    try:
        # ---- INNER 1: parsing. Unparseable is PERMANENT, no retry will ever fix it.
        try:
            event = json.loads(msg.value())
        except json.JSONDecodeError as e:
            raise Permanent("unparseable payload") from e

        # ---- INNER 2: validation + the write. Classified by WHAT THE CALLER SHOULD DO.
        try:
            validate(event)
            with transaction(conn) as tx:            # commit/rollback handled by the CM
                upsert_idempotently(tx, event)       # ON CONFLICT (event_id) DO NOTHING
        except ValidationError as e:
            raise Permanent(f"invalid event: {e}") from e
        except (TimeoutError, ConnectionError) as e: # Aurora failover, network blip
            raise Transient(f"downstream unavailable: {e}") from e

    # ---- the ROUTING layer: one place, decided by TYPE, no isinstance ladder
    except Transient as e:
        e.add_note(f"topic={msg.topic()} partition={msg.partition()} offset={msg.offset()}")
        e.add_note(f"attempt={attempt}")
        log.warning("transient failure -> retry topic", exc_info=e)
        route_to_retry_topic(producer, msg, e)

    except Permanent as e:
        e.add_note(f"topic={msg.topic()} offset={msg.offset()}")
        log.error("poison pill -> DLQ", exc_info=e)
        send_to_dlq(producer, msg, e)

    except Exception:
        # UNEXPECTED = a bug in our code. Log the full traceback and DLQ, so one bad message
        # cannot wedge the partition forever. Breadth is fine here; silence would not be.
        log.exception("UNEXPECTED, treating as poison")
        send_to_dlq(producer, msg, RuntimeError("unexpected"))

    finally:
        # Advance in EVERY case, so a poison pill never blocks the partition.
        # NOTE: no `return` here — that would discard any in-flight exception.
        consumer.commit(message=msg, asynchronous=False)


def handle_batch(messages, conn, producer, consumer):
    """One bad message must not stop the batch, and the caller should learn about ALL of them."""
    failures = []
    for msg in messages:
        try:
            handle_message(msg, conn, producer, consumer)
        except Exception as e:                  # nothing should escape handle_message, but belt+braces
            e.add_note(f"offset={msg.offset()}")
            failures.append(e)
    if failures:
        raise ExceptionGroup(f"{len(failures)}/{len(messages)} messages failed", failures)
```

Call site:

```python
try:
    handle_batch(messages, conn, producer, consumer)
except* Transient as eg:
    metrics.inc("batch_transient_failures", len(eg.exceptions))   # retry scheduled already
except* Permanent as eg:
    metrics.inc("batch_poison_messages", len(eg.exceptions))      # already DLQ'd
```

**Why it's shaped this way:**

- **The transient/permanent split is the decision**, made where the error occurs and acted on where
  the routing lives. Adding a failure mode means adding a subclass.
- **`from e` everywhere**, so the DLQ record and the log carry the real root cause.
- **`add_note`** attaches the Kafka coordinates without changing type or message, so the retry-topic
  handler above still matches.
- **The `transaction` CM re-raises rather than swallowing**, and its own cleanup failure is logged
  rather than raised — the Q5 Trap 2 fix, applied.
- **`finally` commits the offset** so a poison pill can't wedge the partition, and it does **not**
  `return`.
- **The batch raises a group**, so a caller learns about all failures, not just the first.

Full runnable versions: [`06_kafka/04_retry_topic_dlq.py`](../06_kafka/04_retry_topic_dlq.py) and
[`06_kafka/08_kafka_to_aurora_sink.py`](../06_kafka/08_kafka_to_aurora_sink.py).

---

## Hands-on drills

1. Write a function with `except OSError` above `except FileNotFoundError`. Confirm the second is
   dead. Then swap them and confirm it works. Note that nothing warned you.
2. Reproduce the `finally`-overwrites-the-exception trap, then print `e.__context__` to find the
   original. Then make `finally` `return` instead and watch the exception vanish entirely.
3. Build the three-layer repo→service→API translation. Trigger a connection error at the bottom and
   print `e.__cause__.__cause__` at the top — the whole chain should be there.
4. Write a `__exit__` that returns `True` for a payment transaction. Write the one-sentence review
   comment that rejects it.
5. Convert that class-based CM to `@contextmanager` and swallow exactly one exception type at the
   `yield`. Confirm the behaviour is identical.
6. Use `ExitStack` to open 5 files where the 3rd `open()` raises. Confirm the first two are closed.
   Then use `pop_all()` to transfer ownership out on success.
7. Raise an `ExceptionGroup` of three different types and handle it with two `except*` branches.
   Confirm **both** run. Then add a third unhandled type and see what gets re-raised.
8. Use `asyncio.TaskGroup` with three failing tasks. Compare the result with
   `asyncio.gather(..., return_exceptions=False)` and write down what information `gather` loses.
9. Add two `add_note()` calls and re-raise. Print the full traceback and find both notes.
10. Write a retry loop that keeps the last error for the caller. First do it with a bare
    `raise last_error` *outside* the `except` block and hit the `NameError` from the deleted `e`.
11. Write the Q5 Trap 3 `over_broad` function, then the fixed version with a skipped-row counter.
    Add a metric and decide what threshold would page you.

---

## The 60-second spoken answer

> "Multiple `except` clauses are tried top-down and the first `isinstance` match wins — so a parent
> class above a child makes the child's handler dead code, with no warning from Python. I order them
> specific-to-general, and in production code I order them by *decision* rather than taxonomy:
> retryable first, permanent second, then a last-resort `except Exception` that logs the traceback,
> increments a metric and re-raises or routes the item somewhere a human can find it. Silence is the
> sin, not breadth.
>
> I nest `try` blocks when different parts of the body have different recovery strategies, and I
> handle each error at the layer that can actually do something about it. Across layers, each one
> catches the layer below's type and raises its own with `raise ... from e`, so storage errors never
> leak into the service layer and the root cause survives in `__cause__`. In a web app those domain
> exceptions propagate uncaught to centrally-registered handlers, so status codes are decided in one
> place.
>
> The three ways nested handling loses errors: raising inside `except` without `from`, which keeps the
> original only in `__context__`; raising *or returning* in `finally`, which destroys the exception in
> flight — returning from `finally` loses it completely and silently; and an over-broad inner handler
> with a `continue`, which drops rows with no log line and no metric.
>
> For `with`, `__exit__`'s return value decides whether the exception propagates: `True` swallows it.
> That's right for a best-effort audit write and catastrophic for a payment, so I never return a bare
> `True` — I return `issubclass(exc_type, TheOneExpectedError)`. Nested `with` cleans up
> innermost-first, and `ExitStack` handles an unknown number of resources, with `pop_all()` to
> transfer ownership on success.
>
> And `ExceptionGroup` with `except*` exists because concurrency produces several independent
> failures at once and one exception object can't represent two outages. Multiple `except*` branches
> can all run for a single group, which is how I split a failed batch into 'retry these' and 'DLQ
> those'. `asyncio.TaskGroup` raises these natively, which is why I prefer it to `gather`. I use
> `add_note()` to attach the Kafka offset or the attempt number without changing the exception's type
> or message, so handlers above still match and the on-call engineer still gets the context."
