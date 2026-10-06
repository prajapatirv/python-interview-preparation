"""
Multi-level exception handling: many `except` clauses on one `try`, the order that matters, nested
`try` blocks, translating errors as they cross layers, `with` + exceptions together, swallowing via
`__exit__`, `ExceptionGroup`/`except*`, and the exact order `finally` runs in.

Companion to 08_exception_handling.py (which covers the single-level basics). This file is about
what happens when exception handling gets DEEP -- which is where the real bugs live.

Run me: python 15_nested_exception_handling.py
"""
import json
import logging
import time
from contextlib import contextmanager, suppress

logging.basicConfig(level=logging.INFO, format="  [%(levelname)s] %(message)s")
log = logging.getLogger("demo")


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- multiple except clauses
section("multiple except clauses: checked TOP-DOWN, first match wins, so SUBCLASS FIRST")


def classify(error_kind):
    try:
        if error_kind == "key":
            {}["missing"]
        elif error_kind == "index":
            [][5]
        elif error_kind == "file":
            open("no_such_file_12345.txt")
        elif error_kind == "zero":
            1 / 0
        else:
            raise RuntimeError("something else entirely")
    except FileNotFoundError as e:                 # subclass of OSError -- MUST come first
        return f"FileNotFoundError  -> {e.strerror}"
    except OSError as e:                           # the broader parent, second
        return f"OSError            -> {e}"
    except (KeyError, IndexError) as e:            # a tuple = one handler for several types
        return f"{type(e).__name__:18s} -> lookup failed: {e}"
    except ArithmeticError as e:                   # parent of ZeroDivisionError
        return f"ArithmeticError    -> {type(e).__name__}: {e}"
    except Exception as e:                         # the last-resort net, narrowest possible last
        return f"Exception          -> {type(e).__name__}: {e}"


for kind in ("key", "index", "file", "zero", "other"):
    print(f"  {kind:6s}: {classify(kind)}")

print("\n  reverse the first two clauses (OSError before FileNotFoundError) and the specific")
print("  handler becomes DEAD CODE -- no warning, no error, it simply never runs again.")


def wrong_order(path):
    try:
        open(path)
    except OSError:
        return "generic OSError branch ran"
    except FileNotFoundError:
        return "this line is unreachable"


print(f"  proof: {wrong_order('no_such_file_12345.txt')}")


# ---------------------------------------------------------------- nested try: inner handles, outer catches the rest
section("nested try -- an inner block recovers what it can; the rest propagates outward")

DEFAULTS = {"timeout": 30}


def load_settings(raw, fallback_path_exists=False):
    try:                                        # OUTER: anything the inner layers can't fix
        try:                                    # INNER 1: a parse problem is recoverable
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("payload unparseable, falling back to defaults")
            parsed = dict(DEFAULTS)

        try:                                    # INNER 2: a missing key is recoverable
            timeout = parsed["timeout"]
        except KeyError:
            log.warning("no timeout in payload, using default")
            timeout = DEFAULTS["timeout"]

        return {"timeout": int(timeout)}        # a bad TYPE is NOT recoverable here
    except (TypeError, ValueError) as e:
        raise ValueError(f"settings unusable: {e}") from e


print(f"  good json:     {load_settings('{\"timeout\": 5}')}")
print(f"  broken json:   {load_settings('{not json')}")
print(f"  missing key:   {load_settings('{}')}")
try:
    load_settings('{"timeout": "abc"}')
except ValueError as e:
    print(f"  bad type:      propagated out as {type(e).__name__}: {e}")
    print(f"                 root cause preserved in __cause__: {e.__cause__!r}")
print("  the shape to remember: handle at the layer that can ACTUALLY DO something about it.")


# ---------------------------------------------------------------- translating across layers
section("error translation across layers: repo -> service -> API, each layer raises ITS OWN type")


class AppError(Exception):
    """Base for everything our code raises deliberately."""


class RepositoryError(AppError):
    pass


class ServiceError(AppError):
    pass


def repository_layer(order_id):
    """Knows about storage. Translates driver errors into repository errors."""
    try:
        if order_id == 500:
            raise ConnectionResetError("tcp connection to db reset")   # a raw driver error
        if order_id == 404:
            return None
        return {"id": order_id, "total": 99}
    except OSError as e:
        raise RepositoryError(f"storage unavailable for order {order_id}") from e


def service_layer(order_id):
    """Knows about business rules. Never lets a storage type leak to the caller."""
    try:
        row = repository_layer(order_id)
    except RepositoryError as e:
        raise ServiceError("could not load order; try again later") from e
    if row is None:
        raise ServiceError(f"order {order_id} does not exist")
    return row


def api_layer(order_id):
    """Knows about HTTP. The ONLY place a status code is chosen."""
    try:
        return 200, service_layer(order_id)
    except ServiceError as e:
        status = 404 if "does not exist" in str(e) else 503
        return status, {"error": str(e), "root_cause": type(e.__cause__).__name__
                        if e.__cause__ else None}
    except Exception:
        log.exception("unhandled error reaching the API boundary")
        return 500, {"error": "internal error", "correlation_id": "abc-123"}


for oid in (1, 404, 500):
    print(f"  GET /orders/{oid} -> {api_layer(oid)}")
print("  each layer catches the layer below's type and raises its own, with `from e`.")
print("  the traceback keeps the WHOLE chain, so logs still show the TCP reset at the bottom.")


# ---------------------------------------------------------------- except + else + finally ordering
section("the exact execution order of try / except / else / finally")


def trace_order(mode):
    order = []
    try:
        order.append("try")
        if mode == "raise":
            raise ValueError("boom")
        if mode == "return":
            order.append("return-computed")
            return order
    except ValueError:
        order.append("except")
    else:
        order.append("else")           # only when NOTHING was raised
    finally:
        order.append("finally")        # ALWAYS, including after return and after re-raise
    order.append("after-block")
    return order


for mode in ("ok", "raise", "return"):
    print(f"  mode={mode:7s}: {trace_order(mode)}")
print("  note 'finally' lands AFTER 'return-computed' but the caller still gets the right value.")
print("  and in the return case 'else' and 'after-block' never run -- return left the block.")


# ---------------------------------------------------------------- retry inside except
section("retrying from inside an except block -- and keeping the last error for the caller")


class TransientError(Exception):
    pass


def flaky_call(attempt_log):
    attempt_log.append(len(attempt_log) + 1)
    if len(attempt_log) < 3:
        raise TransientError(f"attempt {len(attempt_log)} timed out")
    return "ok"


def call_with_retry(max_attempts=4, base_delay=0.01):
    attempts = []
    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            return flaky_call(attempts), attempts
        except TransientError as e:
            last_error = e
            if attempt == max_attempts:
                raise                     # bare `raise`: original traceback intact
            delay = base_delay * (2 ** (attempt - 1))
            log.info("retrying after %.3fs (%s)", delay, e)
            time.sleep(delay)
    raise AssertionError("unreachable")   # keeps linters and readers honest
    # (never swallow `last_error` silently -- see the next section for the trap)


print(f"  result: {call_with_retry()}")
print("  a full production version (jitter, caps, retry-only-transient) is in")
print("  08_scaling_production_resilience/01_retry_backoff.py and 11_coding_challenges/05_retry_decorator.py")


# ---------------------------------------------------------------- the swallowing traps
section("three ways nested handling silently loses errors")

# TRAP 1: raising inside an except block replaces the error -- unless you chain it
try:
    try:
        1 / 0
    except ZeroDivisionError:
        raise ValueError("replaced")          # no `from` -> __context__ set, __cause__ is None
except ValueError as e:
    print(f"  1. implicit chaining: __cause__={e.__cause__!r} __context__={type(e.__context__).__name__}")
    print("     the original IS still in the traceback ('During handling of the above...'),")
    print("     but `from e` is what states the link deliberately and sets __cause__.")

# TRAP 2: an exception raised in `finally` destroys the one in flight
def finally_overwrite():
    try:
        raise ValueError("the real problem")
    finally:
        raise RuntimeError("cleanup also failed")   # this one reaches the caller


try:
    finally_overwrite()
except RuntimeError as e:
    print(f"  2. error in finally wins: caller sees {type(e).__name__}; "
          f"the real cause is only in __context__ ({type(e.__context__).__name__})")

# TRAP 3: an over-broad inner handler eats what the outer one was meant to see
def over_broad(records):
    processed = []
    for r in records:
        try:
            processed.append(int(r))
        except Exception:                       # swallows EVERYTHING, including the typo below
            continue                            # ...and `continue` means zero evidence
    return processed


print(f"  3. over-broad inner handler: int() over ['1','x','3'] -> {over_broad(['1', 'x', '3'])}")
print("     the 'x' row vanished with no log line and no metric. Count and log skipped rows.")


def over_broad_fixed(records):
    processed, skipped = [], []
    for r in records:
        try:
            processed.append(int(r))
        except ValueError as e:                 # NARROW: only the failure we expected
            skipped.append((r, str(e)))
    if skipped:
        log.warning("skipped %d malformed rows: %s", len(skipped), skipped)
    return processed, skipped


print(f"     fixed: {over_broad_fixed(['1', 'x', '3'])}")


# ---------------------------------------------------------------- with + exceptions
section("`with` and exceptions: __exit__ sees the error, and may CHOOSE to swallow it")


class Transaction:
    """__exit__ returning True swallows the exception. Returning False/None lets it propagate.
    Getting this backwards is how a rollback silently turns into a success."""

    def __init__(self, name, swallow=False):
        self.name, self.swallow = name, swallow

    def __enter__(self):
        print(f"  BEGIN {self.name}")
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            print(f"  COMMIT {self.name}")
            return False
        print(f"  ROLLBACK {self.name} (saw {exc_type.__name__}: {exc})")
        return self.swallow


with Transaction("orders"):
    print("    ...work...")

try:
    with Transaction("payments", swallow=False):
        raise ValueError("insufficient funds")
except ValueError:
    print("  caller saw the ValueError (returned False)")

with Transaction("audit-log", swallow=True):
    raise ValueError("non-critical audit write failed")
print("  caller saw NOTHING (returned True) -- correct for a best-effort audit write,")
print("  catastrophic if you do it to a payment. Swallow ONLY a specific, expected type.")


@contextmanager
def generator_style(name):
    """The @contextmanager equivalent: the exception surfaces AT the `yield`, so you handle it
    with an ordinary try/except/finally around that one line."""
    print(f"  enter {name}")
    try:
        yield name
    except ValueError as e:                     # swallow just this one type
        print(f"  handled inside the context manager: {e}")
    finally:
        print(f"  exit {name} (always)")


with generator_style("resource-1"):
    raise ValueError("recoverable")
print("  @contextmanager form: `except` at the yield == returning True from __exit__")

with suppress(FileNotFoundError, PermissionError):
    open("definitely_missing_file.txt")
print("  contextlib.suppress(...) = a readable, explicitly-typed 'ignore these two'")


# ---------------------------------------------------------------- nested context managers
section("nested `with`: cleanup runs INNERMOST-FIRST, even when the body raises")


@contextmanager
def resource(name, fail_on_exit=False):
    print(f"  open  {name}")
    try:
        yield name
    finally:
        print(f"  close {name}")
        if fail_on_exit:
            raise RuntimeError(f"{name} failed to close")


try:
    with resource("outer-conn"), resource("inner-cursor"):   # one `with`, two managers
        print("    ...work...")
        raise ValueError("work failed")
except ValueError as e:
    print(f"  both closed in reverse order, then the error propagated: {e}")


# ---------------------------------------------------------------- ExceptionGroup / except*
section("ExceptionGroup and except* -- when SEVERAL things fail at once (3.11+)")


def fan_out_to_three_services():
    """Concurrent work produces concurrent failures. One exception cannot represent two
    independent outages, so group them."""
    errors = [
        TimeoutError("inventory-service timed out"),
        ValueError("pricing-service returned a malformed payload"),
        TimeoutError("tax-service timed out"),
    ]
    raise ExceptionGroup("3 of 3 downstream calls failed", errors)


try:
    fan_out_to_three_services()
except* TimeoutError as eg:                  # handles ONLY the timeouts in the group
    print(f"  except* TimeoutError caught {len(eg.exceptions)}: "
          f"{[str(e) for e in eg.exceptions]}")
    print("    -> these are retryable; schedule a retry")
except* ValueError as eg:                    # ...and this branch ALSO runs, same group
    print(f"  except* ValueError caught {len(eg.exceptions)}: {[str(e) for e in eg.exceptions]}")
    print("    -> this one is a poison payload; send it to the DLQ")

print("  the key difference from plain `except`: MULTIPLE except* branches can run for one group,")
print("  because a group can contain several unrelated failures. asyncio.TaskGroup raises these.")

# Ordinary `except` still works on a group, as a whole-object catch:
try:
    fan_out_to_three_services()
except ExceptionGroup as eg:
    print(f"  plain `except ExceptionGroup` -> {eg.message} ({len(eg.exceptions)} sub-exceptions)")


# ---------------------------------------------------------------- add_note
section("add_note() -- attach context without changing the exception type (3.11+)")

try:
    try:
        raise TransientError("broker unreachable")
    except TransientError as e:
        e.add_note("topic=orders partition=3 offset=98421")
        e.add_note("consumer_group=orders-writer attempt=4/4")
        raise
except TransientError as e:
    print(f"  {type(e).__name__}: {e}")
    for note in e.__notes__:
        print(f"    note: {note}")
print("  notes print with the traceback, so the on-call engineer gets the coordinates for free.")


# EXPERIMENT 1: in classify(), move `except OSError` above `except FileNotFoundError` and confirm
# the specific branch becomes unreachable with no warning from Python.
# EXPERIMENT 2: in trace_order(), add `return "from finally"` inside the `finally` block and run
# mode="raise". The ValueError disappears completely. (3.14 emits a SyntaxWarning for this.)
# EXPERIMENT 3: set swallow=True on the "payments" Transaction and note that the caller now thinks
# the payment succeeded. Write down the one sentence you'd say in review to reject that change.
# EXPERIMENT 4: change `except* TimeoutError` to `except*  Exception` and observe that a single
# branch now swallows the whole group -- losing the retry/DLQ distinction.

# EXERCISE: build `process_batch(records)` that for each record runs validate -> transform -> save,
# where validate raises ValidationError, transform raises TypeError and save raises
# ConnectionError. Requirements: one bad record never stops the batch; transient save failures are
# retried twice; permanent failures are collected; and at the end the function raises a single
# ExceptionGroup containing every permanent failure, with each sub-exception carrying an
# add_note() naming its record id. Then handle it at the call site with two `except*` branches.
