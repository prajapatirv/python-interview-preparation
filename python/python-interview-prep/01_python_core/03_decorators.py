"""
Decorators: plain, with functools.wraps, with arguments, class-based, and real-world patterns
(retry, timer, rate limiter). Run me: python 03_decorators.py
"""
import functools
import threading
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- the simplest decorator
section("simplest decorator + why functools.wraps matters")


def log_calls(func):
    @functools.wraps(func)  # remove this line and watch add.__name__ break below
    def wrapper(*args, **kwargs):
        print(f"calling {func.__name__}{args}")
        return func(*args, **kwargs)
    return wrapper


@log_calls
def add(a, b):
    """Add two numbers."""
    return a + b


add(2, 3)
print("add.__name__ ==", add.__name__, "| add.__doc__ ==", add.__doc__)
# EXPERIMENT: comment out @functools.wraps(func) above and rerun — __name__ becomes "wrapper".


# ---------------------------------------------------------------- decorator with arguments
section("decorator that takes arguments: @retry(times=3) needs 3 nesting levels")


def retry(times=3, delay=0.05, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == times:
                        raise
                    print(f"  attempt {attempt} failed ({e}); retrying...")
                    time.sleep(delay * attempt)  # linear backoff for the demo
        return wrapper
    return decorator


calls = {"n": 0}


@retry(times=3, exceptions=(ValueError,))
def flaky():
    calls["n"] += 1
    if calls["n"] < 3:
        raise ValueError(f"not ready yet (call {calls['n']})")
    return "success"


print("flaky() ->", flaky())


# ---------------------------------------------------------------- stacking order
section("stacked decorators apply bottom-up, run outer-first")


def bold(func):
    @functools.wraps(func)
    def wrapper(*a, **k):
        return f"<b>{func(*a, **k)}</b>"
    return wrapper


def italic(func):
    @functools.wraps(func)
    def wrapper(*a, **k):
        return f"<i>{func(*a, **k)}</i>"
    return wrapper


@bold      # applied second -> runs first (outermost)
@italic    # applied first -> runs second
def text():
    return "hi"


print("text() ->", text())  # <b><i>hi</i></b>


# ---------------------------------------------------------------- class-based decorator with state
section("class-based decorator — needed when the decorator itself needs state")


class CountCalls:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.func(*args, **kwargs)


@CountCalls
def ping():
    return "pong"


ping()
ping()
print("ping.calls ==", ping.calls)


# ---------------------------------------------------------------- production pattern: timer
section("real-world pattern: @timer")


def timer(func):
    @functools.wraps(func)
    def wrapper(*a, **k):
        start = time.perf_counter()
        try:
            return func(*a, **k)
        finally:
            print(f"  {func.__name__} took {(time.perf_counter() - start) * 1000:.2f}ms")
    return wrapper


@timer
def slow_sum(n):
    return sum(range(n))


slow_sum(5_000_000)


# ---------------------------------------------------------------- production pattern: rate limiter
section("real-world pattern: thread-safe token-bucket @rate_limit")


def rate_limit(calls: int, per: float):
    lock = threading.Lock()
    tokens, last = [calls], [time.monotonic()]

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*a, **k):
            with lock:
                now = time.monotonic()
                tokens[0] = min(calls, tokens[0] + (now - last[0]) * calls / per)
                last[0] = now
                if tokens[0] < 1:
                    raise RuntimeError("rate limit exceeded")
                tokens[0] -= 1
            return func(*a, **k)
        return wrapper
    return decorator


@rate_limit(calls=3, per=1.0)
def send_sms(to):
    return f"sent to {to}"


for i in range(3):
    print(send_sms(f"user{i}"))
try:
    send_sms("user4")  # 4th call within the same second -> blocked
except RuntimeError as e:
    print("4th call blocked:", e)

# EXPERIMENT: change `calls=3` to `calls=5` and see how many succeed before the RuntimeError.
