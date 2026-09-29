"""
A sliding-window rate limiter, applied per caller key, as a reusable decorator.
Distinguishes rate limiting (protect MY service from too many callers) from a circuit breaker
(protect A DOWNSTREAM from my retries) -- see 02_circuit_breaker.py for the latter.

Run me: python 03_rate_limiter.py
"""
import functools
import time
from collections import defaultdict


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float):
        super().__init__(f"rate limit exceeded, retry after {retry_after:.2f}s")
        self.retry_after = retry_after


def rate_limit(max_calls: int, window_seconds: float):
    """A sliding-window limiter. In a multi-instance deployment this dict would live in Redis
    instead (INCR + EXPIRE, or a sorted set of timestamps) so every instance shares one view --
    an in-process dict only rate-limits calls hitting THIS process."""
    windows: dict[str, list[float]] = defaultdict(list)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(caller_key, *args, **kwargs):
            now = time.time()
            windows[caller_key] = [t for t in windows[caller_key] if now - t < window_seconds]

            if len(windows[caller_key]) >= max_calls:
                oldest = windows[caller_key][0]
                retry_after = window_seconds - (now - oldest)
                raise RateLimitExceeded(retry_after)

            windows[caller_key].append(now)
            return func(caller_key, *args, **kwargs)
        return wrapper
    return decorator


@rate_limit(max_calls=3, window_seconds=1.0)
def call_api(caller_key):
    return f"served {caller_key}"


# ---------------------------------------------------------------- demo: one caller exceeds the limit
section("caller 'user-A' makes 5 calls in a burst -- only 3 are allowed per second")
for i in range(5):
    try:
        print(f"  call {i + 1}:", call_api("user-A"))
    except RateLimitExceeded as e:
        print(f"  call {i + 1}: BLOCKED -- {e}")


# ---------------------------------------------------------------- demo: limits are per-key, not global
section("a DIFFERENT caller key is unaffected -- limits are per-caller, not global")
print(" ", call_api("user-B"))  # user-B has its own fresh window


# ---------------------------------------------------------------- demo: window slides, doesn't reset in lockstep
section("after waiting past the window, the SAME caller is allowed again")
time.sleep(1.05)
print(" ", call_api("user-A"))

# EXPERIMENT: change window_seconds=1.0 to window_seconds=0.1 and rerun the burst of 5 -- with
# such a short window, more of the 5 calls succeed because earlier ones "age out" mid-burst.
# That's the difference between a sliding window and a fixed one that resets all at once.
