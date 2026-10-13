"""
Dependency injection, built from scratch — so you can explain what FastAPI's
Depends() actually does rather than just using it.

Covers: the DI graph, per-request caching, yield dependencies (setup/teardown),
and the override mechanism that makes tests fast.

Run me: python 02_dependency_injection.py
Deep dive: ../deep_dive/11_python_framework_development.md
"""
import inspect
from contextlib import ExitStack
from typing import Any, Callable


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================== the marker
class Depends:
    """Exactly FastAPI's marker: 'resolve this parameter by calling `dependency`'."""

    def __init__(self, dependency: Callable):
        self.dependency = dependency

    def __repr__(self):
        return f"Depends({self.dependency.__name__})"


# ================================================================== the resolver
class Injector:
    """A miniature DI container: resolves the graph, caches per request, runs teardown."""

    def __init__(self):
        self.overrides: dict[Callable, Callable] = {}     # app.dependency_overrides
        self.call_log: list[str] = []

    def solve(self, func: Callable, stack: ExitStack, cache: dict) -> Any:
        """Recursively resolve `func`'s Depends() parameters, then call it."""
        target = self.overrides.get(func, func)           # <- the test seam

        if target in cache:                               # PER-REQUEST CACHE
            self.call_log.append(f"  (cached) {target.__name__}")
            return cache[target]

        kwargs = {}
        for name, param in inspect.signature(target).parameters.items():
            if isinstance(param.default, Depends):
                kwargs[name] = self.solve(param.default.dependency, stack, cache)

        self.call_log.append(f"  calling  {target.__name__}")
        result = target(**kwargs)

        # A generator dependency = setup / yield / teardown, like FastAPI's yield deps
        if inspect.isgenerator(result):
            gen = result
            value = next(gen)
            stack.callback(lambda g=gen: _finish(g))
            result = value

        cache[target] = result
        return result

    def handle_request(self, endpoint: Callable, **path_params):
        """One 'request': build the graph, run the endpoint, then tear everything down."""
        self.call_log = []
        cache: dict = {}
        with ExitStack() as stack:                        # teardown AFTER the response
            kwargs = dict(path_params)
            for name, param in inspect.signature(endpoint).parameters.items():
                if isinstance(param.default, Depends):
                    kwargs[name] = self.solve(param.default.dependency, stack, cache)
            response = endpoint(**kwargs)
        return response


def _finish(gen):
    try:
        next(gen)                                         # run the code after `yield`
    except StopIteration:
        pass


# ================================================================== dependencies
TEARDOWN_LOG: list[str] = []


class Settings:
    db_url = "postgres://prod/orders"
    env = "prod"


def get_settings():
    return Settings()


def get_db(settings=Depends(get_settings)):
    """A YIELD dependency: the code after `yield` runs after the response is sent."""
    db = f"<connection to {settings.db_url}>"
    yield db
    TEARDOWN_LOG.append("db connection closed")


def get_repo(db=Depends(get_db)):
    return f"OrderRepository({db})"


def get_audit_log(db=Depends(get_db)):
    """ALSO depends on get_db — proving the per-request cache gives us the SAME db."""
    return f"AuditLog({db})"


def get_service(repo=Depends(get_repo), audit=Depends(get_audit_log)):
    return f"OrderService({repo}, {audit})"


def current_user(settings=Depends(get_settings)):
    return {"id": 7, "roles": ["admin"], "env": settings.env}


# ================================================================== endpoint
def get_order(order_id: int, svc=Depends(get_service), user=Depends(current_user)):
    return f"order {order_id} for user {user['id']} via {svc}"


# ================================================================== demo
section("1. resolving the dependency graph")

injector = Injector()
response = injector.handle_request(get_order, order_id=42)
print("\n".join(injector.call_log))
print(f"\n  response: {response}")
print(f"  teardown: {TEARDOWN_LOG}")

print("""
  The graph is:
      get_order
        +- get_service
        |    +- get_repo  -> get_db -> get_settings
        |    +- get_audit_log -> get_db (CACHED)
        +- current_user   -> get_settings (CACHED)
""")


section("2. per-request caching: get_db and get_settings are each called ONCE")

TEARDOWN_LOG.clear()
injector.handle_request(get_order, order_id=1)
calls = [line for line in injector.call_log if "calling" in line]
cached = [line for line in injector.call_log if "cached" in line]
print(f"  actual calls : {len(calls)}")
for c in calls:
    print(f"    {c.strip()}")
print(f"  cache hits   : {len(cached)}")
for c in cached:
    print(f"    {c.strip()}")
print("\n  get_db is depended on TWICE but opens ONE connection. Without per-request")
print("  caching you would open a second connection for the audit log — and in a real")
print("  service, run your queries in two different transactions.")


section("3. the cache is PER REQUEST, not global")

TEARDOWN_LOG.clear()
injector.handle_request(get_order, order_id=1)
first = TEARDOWN_LOG.copy()
injector.handle_request(get_order, order_id=2)
print(f"  teardowns after 2 requests: {TEARDOWN_LOG}")
print("  Each request got a fresh connection and closed it. State never leaks between")
print("  requests — which is what makes the service horizontally scalable.")


section("4. dependency_overrides: the reason DI beats module-level globals")


class TestSettings:
    db_url = "sqlite://memory"
    env = "test"


def fake_settings():
    return TestSettings()


def fake_user():
    return {"id": 1, "roles": ["tester"], "env": "test"}


injector.overrides[get_settings] = fake_settings
injector.overrides[current_user] = fake_user

TEARDOWN_LOG.clear()
response = injector.handle_request(get_order, order_id=99)
print(f"  {response}")
print("\n  No mocking library, no monkeypatching, no changes to get_order or any")
print("  dependency. The whole graph below get_settings rebuilt against sqlite.")

injector.overrides.clear()          # ALWAYS clear, or overrides leak across tests
response = injector.handle_request(get_order, order_id=99)
print(f"\n  after overrides.clear(): {response}")


section("5. what this buys you, stated plainly")

print("""  * Unit tests run in milliseconds with no DB, no broker, no network.
  * Swapping an implementation (in-memory / Redis / Couchbase) is a config change.
  * Dependencies are VISIBLE in the signature — you can read what a function needs
    without reading its body.
  * Lifecycle is managed once: a yield dependency's teardown always runs, even if
    the endpoint raised.

  And note what is NOT here: no container library, no decorators, no component
  scanning, no reflection over types. Python's `inspect` plus default values is
  enough. Reaching for `dependency-injector` in a normal service is usually a
  Java habit rather than a requirement.""")


# EXERCISE 1: make a dependency raise, and confirm the yield teardowns STILL run.
#             (Hint: ExitStack already guarantees it — prove it.)
# EXERCISE 2: add `use_cache=False` support to Depends so one dependency is rebuilt
#             per use. When would you want that?
# EXERCISE 3: add a `dependencies=[...]` list to the endpoint that runs a dependency
#             for its side effect (auth check) without injecting the result.
# EXERCISE 4: detect a CIRCULAR dependency (A depends on B depends on A) and raise a
#             clear error instead of hitting RecursionError.
