"""
Retry with exponential backoff + jitter -- retry only transient errors, cap attempts and total
time, and see why jitter matters (avoiding a synchronized "retry storm").

Run me: python 01_retry_backoff.py
"""
import random
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


class TransientError(Exception):
    """Worth retrying: a timeout, a 503, a connection reset."""


class PermanentError(Exception):
    """Never worth retrying: a 400, a validation failure."""


def retry_with_backoff(fn, max_attempts=4, base_delay=0.05, max_delay=2.0,
                        retry_on=(TransientError,), sleep=time.sleep):
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except retry_on as e:
            if attempt == max_attempts:
                print(f"  giving up after {max_attempts} attempts: {e}")
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay)  # spreads out simultaneous retriers
            wait = delay + jitter
            print(f"  attempt {attempt} failed ({e}); waiting {wait:.3f}s before retry")
            sleep(wait)


# ---------------------------------------------------------------- succeeds on the 3rd try
section("retry succeeds within max_attempts")
calls = {"n": 0}


def flaky():
    calls["n"] += 1
    if calls["n"] < 3:
        raise TransientError(f"timeout on attempt {calls['n']}")
    return "success"


print("result:", retry_with_backoff(flaky))


# ---------------------------------------------------------------- exhausts retries and re-raises
section("retry exhausts max_attempts and re-raises the last error")
try:
    retry_with_backoff(lambda: (_ for _ in ()).throw(TransientError("always fails")), max_attempts=3)
except TransientError as e:
    print(f"  caller correctly saw the failure: {e}")


# ---------------------------------------------------------------- permanent errors are NOT retried
section("a PermanentError is never retried, even though retry_on lists TransientError")


def always_invalid():
    raise PermanentError("this input will never become valid, no matter how many times we try")


try:
    retry_with_backoff(always_invalid, retry_on=(TransientError,))
except PermanentError as e:
    print(f"  propagated immediately, zero retries wasted: {e}")


# ---------------------------------------------------------------- why jitter matters
section("without jitter, every failing client retries at EXACTLY the same offsets -- a thundering herd")
no_jitter_delays = [min(0.05 * (2 ** a), 2.0) for a in range(4)]
print("without jitter, 100 clients would all wait exactly:", no_jitter_delays)
print("...then ALL retry in the same instant, potentially overwhelming a service that's just recovering.")
print("adding `+ random.uniform(0, delay)` spreads those 100 retries across a window instead of a spike.")

# EXPERIMENT: set max_delay=0.2 in the first retry_with_backoff call and observe the exponential
# growth get capped -- this prevents a long-failing dependency from making you wait minutes
# between retries.
