"""
Exception handling: try/except/else/finally, custom hierarchies, chaining, EAFP vs LBYL,
and the return-in-finally footgun. Run me: python 08_exception_handling.py
"""
import logging

logging.basicConfig(level=logging.INFO, format="  [%(levelname)s] %(message)s")
log = logging.getLogger("demo")


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- try/except/else/finally
section("try / except / else / finally — else runs only on success, finally always runs")


def read_config(should_fail):
    try:
        if should_fail:
            raise FileNotFoundError("config.yaml missing")
        data = {"env": "dev"}
    except FileNotFoundError as e:
        log.error("config missing: %s", e)
        return {}
    else:
        return data  # only reached if no exception happened
    finally:
        print("  read_config finished (always runs)")


print("result:", read_config(should_fail=True))
print("result:", read_config(should_fail=False))


# ---------------------------------------------------------------- custom exception hierarchy
section("custom exception hierarchy rooted in one app base class")


class AppError(Exception):
    """Base for all application errors."""


class ValidationError(AppError):
    def __init__(self, field, msg):
        super().__init__(f"{field}: {msg}")
        self.field = field


class NotFoundError(AppError):
    def __init__(self, resource):
        super().__init__(f"{resource} not found")


def get_order(order_id):
    if order_id <= 0:
        raise ValidationError("order_id", "must be positive")
    if order_id > 1000:
        raise NotFoundError(f"order {order_id}")
    return {"id": order_id}


for oid in (-1, 9999, 42):
    try:
        print("get_order ->", get_order(oid))
    except AppError as e:  # one handler catches the whole family
        print(f"  AppError ({type(e).__name__}): {e}")


# ---------------------------------------------------------------- exception chaining
section("raise ... from ... — keep the root cause visible")


class ConfigError(Exception):
    pass


def load(raw_json):
    import json
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ConfigError("invalid config file") from e


try:
    load("{not valid json")
except ConfigError as e:
    print(f"ConfigError: {e}")
    print(f"  __cause__ (the original error): {e.__cause__!r}")


# ---------------------------------------------------------------- EAFP vs LBYL
section("EAFP (ask forgiveness) is the Pythonic default — avoids race conditions / double lookups")
d = {"key": "value"}

# LBYL — Look Before You Leap
if "key" in d:
    v_lbyl = d["key"]

# EAFP — Easier to Ask Forgiveness than Permission
try:
    v_eafp = d["key"]
except KeyError:
    v_eafp = None

print("both give:", v_lbyl, v_eafp)


# ---------------------------------------------------------------- the return-in-finally footgun
section("NEVER return from finally — it silently discards the try's return AND any exception")


def footgun():
    try:
        return "from try"
    finally:
        return "from finally"  # this one wins, silently


print("footgun() ->", footgun(), "  (the 'from try' value vanished with no warning)")


# ---------------------------------------------------------------- re-raising while preserving traceback
section("bare `raise` inside except re-raises with the original traceback intact")


def process(x):
    try:
        return 1 / x
    except ZeroDivisionError:
        log.exception("bad input %s", x)  # logs full traceback
        raise  # bare raise, not `raise e`


try:
    process(0)
except ZeroDivisionError:
    print("  caller saw it too, traceback preserved")

# EXERCISE: add a RetryableError(AppError) subclass, then write a retry loop that retries only
# RetryableError and lets every other AppError propagate immediately. Cross-check against
# 08_scaling_production_resilience/01_retry_backoff.py once you're done.
