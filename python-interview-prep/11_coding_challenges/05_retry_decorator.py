"""
Problem: design a retry decorator with a RETRY LIMIT and an EXPONENTIAL BACKOFF strategy.

The full requirement an interviewer is actually after:
  1. `@retry(max_attempts=4)` -- a decorator that takes arguments (so: three nesting levels).
  2. Exponential backoff: delay = base * (factor ** (attempt - 1)), capped by max_delay.
  3. Jitter, so N failing clients don't all retry in the same instant (the thundering herd).
  4. Retry ONLY the exceptions worth retrying; everything else propagates immediately.
  5. Re-raise the last error after the final attempt -- never return None silently.
  6. `functools.wraps`, so the decorated function keeps its name, docstring and signature.
  7. An injectable `sleep` so the behaviour is TESTABLE without the test actually waiting.
  8. (Bonus) a total-time budget, an on-retry callback, and an async variant.

Point 7 is the one most candidates miss and the one that makes this production code: a retry
decorator you cannot unit-test deterministically is a retry decorator nobody trusts.

Run me:          python 05_retry_decorator.py
Run the tests:   pytest 05_retry_decorator.py -v
"""
import asyncio
import functools
import random
import time


# ---------------------------------------------------------------- the error taxonomy
class TransientError(Exception):
    """Worth retrying: a timeout, a 503, a connection reset, a DB deadlock."""


class PermanentError(Exception):
    """Never worth retrying: a 400, a validation failure, a bad schema."""


# ---------------------------------------------------------------- the delay calculation, alone
def backoff_delay(attempt, base_delay=0.1, factor=2.0, max_delay=10.0, jitter="full",
                  rng=random.random):
    """Delay BEFORE the given attempt number (1-based: attempt 1 has already failed).

    Pulled out as a pure function on purpose -- it's the part with the arithmetic, so it's the
    part worth testing directly, and it's where interviewers probe the jitter strategies:

      "none"  -> base * factor**(n-1)                exact, synchronised, thundering herd
      "full"  -> uniform(0, delay)                   AWS's recommended default; best spread
      "equal" -> delay/2 + uniform(0, delay/2)       keeps a guaranteed minimum wait
    """
    raw = base_delay * (factor ** (attempt - 1))
    delay = min(raw, max_delay)
    if jitter == "none":
        return delay
    if jitter == "full":
        return rng() * delay
    if jitter == "equal":
        return delay / 2 + rng() * (delay / 2)
    raise ValueError(f"unknown jitter strategy: {jitter!r}")


# ---------------------------------------------------------------- the decorator
def retry(max_attempts=3, base_delay=0.1, factor=2.0, max_delay=10.0, jitter="full",
          retry_on=(TransientError,), give_up_on=(), total_budget=None,
          on_retry=None, sleep=time.sleep, rng=random.random):
    """Retry `max_attempts` times total (i.e. 1 initial call + max_attempts-1 retries).

    Args:
        retry_on:     exception types that trigger a retry. Everything else propagates at once.
        give_up_on:   checked FIRST -- lets you retry OSError but not its FileNotFoundError child.
        total_budget: seconds; stop retrying once the elapsed total would exceed this, even if
                      attempts remain. A caller with a 2s SLA does not care that you had 5 tries.
        on_retry:     callback(attempt, exception, delay) -- for logging or a metric counter.
        sleep / rng:  injected for tests. Pass sleep=lambda s: None to make tests instant.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be >= 1")

    def decorator(fn):
        @functools.wraps(fn)                 # keeps __name__, __doc__, __wrapped__, signature
        def wrapper(*args, **kwargs):
            started = time.monotonic()
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except give_up_on:           # listed first, so it wins over a broader retry_on
                    raise
                except retry_on as exc:
                    if attempt == max_attempts:
                        raise                # bare raise: original traceback preserved
                    delay = backoff_delay(attempt, base_delay, factor, max_delay, jitter, rng)
                    if total_budget is not None:
                        elapsed = time.monotonic() - started
                        if elapsed + delay > total_budget:
                            raise            # out of time budget -- stop retrying now
                    if on_retry is not None:
                        on_retry(attempt, exc, delay)
                    sleep(delay)
            raise AssertionError("unreachable")   # the loop always returns or raises
        return wrapper
    return decorator


# ---------------------------------------------------------------- the async variant
def retry_async(max_attempts=3, base_delay=0.1, factor=2.0, max_delay=10.0, jitter="full",
                retry_on=(TransientError,), on_retry=None, sleep=None, rng=random.random):
    """Same logic, `await`-ing the call and using asyncio.sleep so the event loop stays free.
    A blocking time.sleep() inside an async retry would stall every other coroutine -- this is
    the trap interviewers look for once you mention asyncio."""
    sleeper = sleep or asyncio.sleep

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return await fn(*args, **kwargs)
                except retry_on as exc:
                    if attempt == max_attempts:
                        raise
                    delay = backoff_delay(attempt, base_delay, factor, max_delay, jitter, rng)
                    if on_retry is not None:
                        on_retry(attempt, exc, delay)
                    await sleeper(delay)
            raise AssertionError("unreachable")
        return wrapper
    return decorator


# ---------------------------------------------------------------- a class-based alternative
class Retry:
    """The same thing as a class, for when the interviewer asks "now do it without a closure".
    Holding state on the instance (here: a retry counter shared by every decorated call) is the
    one real reason to prefer this form."""

    def __init__(self, max_attempts=3, base_delay=0.1, retry_on=(TransientError,),
                 sleep=time.sleep, rng=random.random):
        self.max_attempts, self.base_delay = max_attempts, base_delay
        self.retry_on, self.sleep, self.rng = retry_on, sleep, rng
        self.total_retries = 0               # observable state across every decorated call

    def __call__(self, fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            for attempt in range(1, self.max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except self.retry_on:
                    if attempt == self.max_attempts:
                        raise
                    self.total_retries += 1
                    self.sleep(backoff_delay(attempt, self.base_delay, rng=self.rng))
        return wrapper


if __name__ == "__main__":
    def section(title):
        print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")

    # ------------------------------------------------------------ succeeds on the 3rd attempt
    section("succeeds within the limit")
    attempts = []

    @retry(max_attempts=4, base_delay=0.01, on_retry=lambda n, e, d:
           print(f"  attempt {n} failed ({e}); sleeping {d:.4f}s"))
    def flaky():
        """Fails twice, then works."""
        attempts.append(1)
        if len(attempts) < 3:
            raise TransientError(f"timeout #{len(attempts)}")
        return "success"

    print(f"  result: {flaky()} after {len(attempts)} attempts")
    print(f"  functools.wraps kept the identity: {flaky.__name__!r} / {flaky.__doc__!r}")

    # ------------------------------------------------------------ exhausts the limit
    section("exhausts the limit and re-raises the LAST error")

    @retry(max_attempts=3, base_delay=0.01)
    def always_fails():
        raise TransientError("downstream is down")

    try:
        always_fails()
    except TransientError as e:
        print(f"  caller correctly saw the failure after 3 attempts: {e}")

    # ------------------------------------------------------------ permanent errors
    section("a PermanentError is never retried -- zero wasted attempts")
    calls = []

    @retry(max_attempts=5, base_delay=0.01, retry_on=(TransientError,))
    def bad_input():
        calls.append(1)
        raise PermanentError("field 'amount' must be positive")

    try:
        bad_input()
    except PermanentError as e:
        print(f"  propagated immediately after {len(calls)} call: {e}")

    # ------------------------------------------------------------ give_up_on beats retry_on
    section("give_up_on carves an exception OUT of a broader retry_on")
    os_calls = []

    @retry(max_attempts=4, base_delay=0.01, retry_on=(OSError,),
           give_up_on=(FileNotFoundError,))
    def read_remote(path):
        os_calls.append(path)
        raise FileNotFoundError(path)        # a subclass of OSError -- but hopeless to retry

    try:
        read_remote("/nope")
    except FileNotFoundError:
        print(f"  retried OSError in general, but gave up on FileNotFoundError after "
              f"{len(os_calls)} call")

    # ------------------------------------------------------------ the shape of the backoff
    section("the delays: with and without jitter")
    print("  attempt |  no jitter |  full jitter (5 samples)")
    for n in range(1, 6):
        plain = backoff_delay(n, base_delay=0.1, max_delay=2.0, jitter="none")
        samples = [f"{backoff_delay(n, 0.1, max_delay=2.0):.3f}" for _ in range(5)]
        print(f"     {n}    |   {plain:6.3f}s  |  {', '.join(samples)}")
    print("  without jitter, 100 clients that failed together retry together -- a synchronised")
    print("  spike at 0.1s, 0.2s, 0.4s... exactly when the service is trying to recover.")
    print("  max_delay caps the growth so a long outage doesn't mean 17-minute waits.")

    # ------------------------------------------------------------ the time budget
    section("total_budget stops retrying when the caller's SLA is spent")
    budget_attempts = []

    @retry(max_attempts=10, base_delay=0.05, jitter="none", total_budget=0.2)
    def slow_failure():
        budget_attempts.append(time.monotonic())
        raise TransientError("still down")

    t0 = time.monotonic()
    try:
        slow_failure()
    except TransientError:
        print(f"  stopped after {len(budget_attempts)} attempts / "
              f"{time.monotonic() - t0:.2f}s, not the full 10 -- the 0.2s budget ran out")

    # ------------------------------------------------------------ async
    section("the async variant keeps the event loop free")

    async def demo_async():
        tries = []

        @retry_async(max_attempts=3, base_delay=0.01)
        async def flaky_io():
            tries.append(1)
            if len(tries) < 2:
                raise TransientError("async timeout")
            return "async success"

        return await flaky_io(), len(tries)

    print(f"  result: {asyncio.run(demo_async())}")

    # ------------------------------------------------------------ class-based
    section("class-based form, with state shared across decorated calls")
    policy = Retry(max_attempts=3, base_delay=0.01)

    @policy
    def a():
        if policy.total_retries < 2:
            raise TransientError("warming up")
        return "a ok"

    print(f"  {a()}  (total_retries observed by the policy object: {policy.total_retries})")
    print("\n  See also: 08_scaling_production_resilience/01_retry_backoff.py (the function form,")
    print("  with the thundering-herd explanation) and 02_circuit_breaker.py -- retries alone")
    print("  will hammer a dead dependency; a breaker is what stops that.")


# ---------------------------------------------------------------- tests
# (no `import pytest` on purpose -- keeps `python 05_retry_decorator.py` dependency-free while
# pytest still discovers plain `test_*` functions. A fake sleep makes every test instant and
# deterministic: this is the whole reason `sleep` and `rng` are injectable.)

class FakeSleep:
    """Records what it was asked to wait, and waits for nothing."""

    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


def test_succeeds_without_retrying_when_the_call_works():
    sleeper = FakeSleep()

    @retry(max_attempts=4, sleep=sleeper)
    def ok():
        return "fine"

    assert ok() == "fine"
    assert sleeper.calls == []          # no sleep at all on the happy path


def test_retries_until_success_and_returns_the_value():
    sleeper = FakeSleep()
    calls = []

    @retry(max_attempts=4, sleep=sleeper)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientError("boom")
        return "recovered"

    assert flaky() == "recovered"
    assert len(calls) == 3
    assert len(sleeper.calls) == 2       # slept between attempts 1-2 and 2-3, never after success


def test_stops_at_max_attempts_and_reraises_the_last_error():
    sleeper = FakeSleep()
    calls = []

    @retry(max_attempts=3, sleep=sleeper)
    def always_fails():
        calls.append(1)
        raise TransientError(f"failure #{len(calls)}")

    try:
        always_fails()
        raise AssertionError("should have raised")
    except TransientError as e:
        assert str(e) == "failure #3"    # the LAST error, not the first
    assert len(calls) == 3               # exactly max_attempts -- not one more
    assert len(sleeper.calls) == 2       # n attempts means n-1 sleeps


def test_does_not_retry_an_exception_outside_retry_on():
    sleeper = FakeSleep()
    calls = []

    @retry(max_attempts=5, retry_on=(TransientError,), sleep=sleeper)
    def permanent():
        calls.append(1)
        raise PermanentError("invalid input")

    try:
        permanent()
        raise AssertionError("should have raised")
    except PermanentError:
        pass
    assert len(calls) == 1               # zero retries wasted
    assert sleeper.calls == []


def test_give_up_on_takes_precedence_over_retry_on():
    sleeper = FakeSleep()
    calls = []

    @retry(max_attempts=4, retry_on=(OSError,), give_up_on=(FileNotFoundError,), sleep=sleeper)
    def missing():
        calls.append(1)
        raise FileNotFoundError("/nope")

    try:
        missing()
        raise AssertionError("should have raised")
    except FileNotFoundError:
        pass
    assert len(calls) == 1


def test_delays_grow_exponentially_and_are_capped():
    # rng fixed at 1.0 removes the jitter randomness, so the arithmetic is assertable
    delays = [backoff_delay(n, base_delay=1.0, factor=2.0, max_delay=8.0, jitter="none")
              for n in range(1, 7)]
    assert delays == [1.0, 2.0, 4.0, 8.0, 8.0, 8.0]      # doubles, then flattens at max_delay


def test_full_jitter_stays_within_the_exponential_bound():
    for n in range(1, 6):
        upper = min(1.0 * (2 ** (n - 1)), 8.0)
        for r in (0.0, 0.5, 1.0):
            d = backoff_delay(n, base_delay=1.0, max_delay=8.0, jitter="full", rng=lambda: r)
            assert 0.0 <= d <= upper


def test_equal_jitter_keeps_a_guaranteed_minimum_wait():
    d_min = backoff_delay(3, base_delay=1.0, max_delay=8.0, jitter="equal", rng=lambda: 0.0)
    d_max = backoff_delay(3, base_delay=1.0, max_delay=8.0, jitter="equal", rng=lambda: 1.0)
    assert d_min == 2.0 and d_max == 4.0       # never less than half the nominal 4.0s delay


def test_the_wrapper_sleeps_with_the_backoff_sequence():
    sleeper = FakeSleep()

    @retry(max_attempts=4, base_delay=1.0, factor=2.0, jitter="none", sleep=sleeper)
    def always_fails():
        raise TransientError("x")

    try:
        always_fails()
    except TransientError:
        pass
    assert sleeper.calls == [1.0, 2.0, 4.0]


def test_total_budget_cuts_the_retries_short():
    sleeper = FakeSleep()
    calls = []

    @retry(max_attempts=10, base_delay=1.0, factor=2.0, jitter="none", total_budget=2.5,
           sleep=sleeper)
    def always_fails():
        calls.append(1)
        raise TransientError("x")

    try:
        always_fails()
    except TransientError:
        pass
    # delays would be 1, 2, 4...; elapsed is ~0 with a fake sleep, so 1.0 and 2.0 fit under 2.5
    # but 4.0 does not -> 3 calls, 2 sleeps, well short of the 10 allowed attempts
    assert len(calls) == 3
    assert sleeper.calls == [1.0, 2.0]


def test_on_retry_callback_sees_every_retry():
    seen = []

    @retry(max_attempts=3, jitter="none", base_delay=0.5, sleep=FakeSleep(),
           on_retry=lambda n, e, d: seen.append((n, type(e).__name__, d)))
    def always_fails():
        raise TransientError("x")

    try:
        always_fails()
    except TransientError:
        pass
    assert seen == [(1, "TransientError", 0.5), (2, "TransientError", 1.0)]


def test_functools_wraps_preserves_identity():
    @retry(max_attempts=2, sleep=FakeSleep())
    def documented(a, b=2):
        """The original docstring."""
        return a + b

    assert documented.__name__ == "documented"
    assert documented.__doc__ == "The original docstring."
    assert documented(1) == 3
    assert documented.__wrapped__ is not None      # the undecorated function is still reachable


def test_max_attempts_must_be_at_least_one():
    try:
        retry(max_attempts=0)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_async_variant_retries_and_returns():
    calls = []

    async def scenario():
        @retry_async(max_attempts=4, sleep=lambda _: asyncio.sleep(0))
        async def flaky():
            calls.append(1)
            if len(calls) < 3:
                raise TransientError("boom")
            return "async ok"

        return await flaky()

    assert asyncio.run(scenario()) == "async ok"
    assert len(calls) == 3


def test_class_based_form_accumulates_state():
    policy = Retry(max_attempts=4, sleep=FakeSleep())
    calls = []

    @policy
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise TransientError("boom")
        return "ok"

    assert flaky() == "ok"
    assert policy.total_retries == 2
