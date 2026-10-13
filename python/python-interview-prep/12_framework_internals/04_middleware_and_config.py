"""
Two more framework internals:
  A. the middleware chain — how one request passes through N wrappers, and why
     order is inverted (and the cardinality trap in metrics middleware)
  B. configuration — layered precedence, fail-fast validation at startup

Run me: python 04_middleware_and_config.py
Deep dive: ../deep_dive/11_python_framework_development.md
"""
import os
import re
import time
import uuid
from collections import ChainMap, defaultdict


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ============================================================================
# PART A — the middleware chain
# ============================================================================
section("A1. how a middleware chain is actually built")


class Request:
    def __init__(self, method, path, headers=None):
        self.method, self.path = method, path
        self.headers = headers or {}
        self.state = {}                        # request.state, as in Starlette
        self.route = None                      # the matched TEMPLATE, e.g. /orders/{id}


class Response:
    def __init__(self, status, body, headers=None):
        self.status, self.body = status, body
        self.headers = headers or {}


def build_chain(app, middlewares):
    """Wrap `app` in each middleware. The LAST one added ends up OUTERMOST."""
    handler = app
    for mw in middlewares:                     # note: applied in order...
        handler = mw(handler)                  # ...so each wraps the previous
    return handler


TRACE = []


def logging_mw(next_handler):
    def handler(request):
        TRACE.append("  -> logging (enter)")
        response = next_handler(request)
        TRACE.append("  <- logging (exit)")
        return response
    return handler


def timing_mw(next_handler):
    def handler(request):
        TRACE.append("  -> timing (enter)")
        start = time.perf_counter()
        response = next_handler(request)
        response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.5f}"
        TRACE.append("  <- timing (exit)")
        return response
    return handler


def correlation_mw(next_handler):
    def handler(request):
        TRACE.append("  -> correlation (enter)")
        cid = request.headers.get("X-Correlation-ID", uuid.uuid4().hex[:8])
        request.state["correlation_id"] = cid
        response = next_handler(request)
        response.headers["X-Correlation-ID"] = cid
        TRACE.append("  <- correlation (exit)")
        return response
    return handler


def endpoint(request):
    TRACE.append(f"     [endpoint] cid={request.state.get('correlation_id')}")
    return Response(200, {"ok": True})


# Order of the list = order of application. The LAST applied runs FIRST.
app = build_chain(endpoint, [logging_mw, timing_mw, correlation_mw])

TRACE.clear()
resp = app(Request("GET", "/orders/42"))
print("\n".join(TRACE))
print(f"\n  response headers: {resp.headers}")
print("""
  Applied: logging, timing, correlation.
  Executed: correlation -> timing -> logging -> endpoint, then back out.

  The LAST middleware added is the OUTERMOST and runs FIRST. This is counter-
  intuitive and it matters: add CORS last if you want it outermost, and make sure
  auth wraps caching rather than the other way round — otherwise a cache hit
  short-circuits BEFORE the auth check and you serve data to anonymous callers.""")


# ---------------------------------------------------------------------------
section("A2. THE CARDINALITY TRAP in metrics middleware")

METRICS_RAW = defaultdict(int)
METRICS_TEMPLATED = defaultdict(int)

ROUTE_PATTERNS = [(re.compile(r"^/orders/\d+$"), "/orders/{id}"),
                  (re.compile(r"^/users/\d+$"), "/users/{id}")]


def match_route(path):
    for pattern, template in ROUTE_PATTERNS:
        if pattern.match(path):
            return template
    return path


import random
random.seed(3)
for _ in range(3_000):
    path = f"/orders/{random.randint(1, 50_000)}"
    METRICS_RAW[("http_requests_total", path, 200)] += 1               # WRONG
    METRICS_TEMPLATED[("http_requests_total", match_route(path), 200)] += 1   # RIGHT

print(f"  labelled by RAW path      : {len(METRICS_RAW):>6,} time series")
print(f"  labelled by route TEMPLATE: {len(METRICS_TEMPLATED):>6,} time series")
print("""
  3,000 requests -> ~2,900 series with the raw path. At production volume that is
  millions of series and your Prometheus dies — during the incident you needed it
  for. Use request.scope['route'].path (the TEMPLATE), never request.url.path.

  Never label with: user id, order id, email, session id, raw path, raw error text.
  Per-entity detail belongs in logs and traces.""")


# ---------------------------------------------------------------------------
section("A3. middleware vs Depends() — when to use which")

print("""  MIDDLEWARE                          DEPENDS()
  ---------------------------------   ------------------------------------------
  runs for EVERY request              scoped to the routes that declare it
  incl. /health and /metrics          skipped where not needed
  not in the OpenAPI schema           documented in /docs automatically
  hard to override in tests           app.dependency_overrides — trivial
  good for: correlation IDs, CORS,    good for: auth, rate limits, DB sessions,
    gzip, global timing/logging         anything route-specific

  Rule: if it applies to SOME routes, it is a dependency, not middleware.
  And keep middleware cheap — it runs on your health checks too.""")


# ============================================================================
# PART B — configuration
# ============================================================================
section("B1. layered configuration with ChainMap — precedence made visible")

# Highest priority first. ChainMap returns the first hit, without copying.
DEFAULTS = {"env": "dev", "log_level": "INFO", "workers": "4",
            "db_url": "", "request_timeout_s": "5.0"}
FILE_CFG = {"workers": "8", "log_level": "DEBUG"}          # .env
SECRETS = {"db_url": "postgres://prod/orders"}             # /run/secrets
ENV_VARS = {"LOG_LEVEL": "WARNING"}                        # real env vars win

normalised_env = {k.lower(): v for k, v in ENV_VARS.items()}
config = ChainMap(normalised_env, SECRETS, FILE_CFG, DEFAULTS)

for key in ["log_level", "workers", "db_url", "env"]:
    source = next(name for name, layer in
                  [("env var", normalised_env), ("secret", SECRETS),
                   ("file", FILE_CFG), ("default", DEFAULTS)] if key in layer)
    print(f"  {key:<20} = {config[key]!r:<28} (from {source})")

print("\n  Precedence: env vars > secrets > .env file > defaults.")
print("  ChainMap is a VIEW — no copying, and changes to a layer are seen immediately.")


# ---------------------------------------------------------------------------
section("B2. fail-fast validation at STARTUP (what pydantic-settings does for you)")


class ConfigError(Exception):
    pass


class Settings:
    """A hand-rolled BaseSettings, to show what the validation is actually doing."""

    SPEC = {
        # name                type   required  validator
        "env":               (str,  True,  lambda v: v in {"dev", "staging", "prod"}),
        "db_url":            (str,  True,  lambda v: v.startswith(("postgres://", "sqlite://"))),
        "log_level":         (str,  False, lambda v: v in {"DEBUG", "INFO", "WARNING", "ERROR"}),
        "workers":           (int,  False, lambda v: 1 <= v <= 64),
        "request_timeout_s": (float, False, lambda v: 0 < v <= 60),
    }

    def __init__(self, raw: dict, forbid_extra=True):
        problems = []
        known = set(self.SPEC)

        if forbid_extra:
            for key in set(raw) - known:
                problems.append(f"unknown setting {key!r} (typo? extra='forbid')")

        for name, (typ, required, check) in self.SPEC.items():
            if name not in raw or raw[name] == "":
                if required:
                    problems.append(f"{name!r} is REQUIRED and was not provided")
                continue
            try:
                value = typ(raw[name])
            except (TypeError, ValueError):
                problems.append(f"{name!r}={raw[name]!r} is not a valid {typ.__name__}")
                continue
            if not check(value):
                problems.append(f"{name!r}={value!r} failed validation")
            else:
                setattr(self, name, value)

        if problems:
            raise ConfigError("invalid configuration:\n    - " + "\n    - ".join(problems))


print("  valid configuration:")
good = Settings(dict(config))
print(f"    env={good.env} workers={good.workers} log_level={good.log_level}")
print(f"    db_url={good.db_url}")

print("\n  missing a REQUIRED setting (no DB_URL in any layer):")
try:
    Settings(dict(ChainMap(FILE_CFG, DEFAULTS)))
except ConfigError as e:
    print("   ", str(e).replace("\n", "\n   "))

print("\n  a typo'd env var, caught by extra='forbid':")
try:
    Settings({**dict(config), "worker": "8", "loglevel": "INFO"})
except ConfigError as e:
    print("   ", str(e).replace("\n", "\n   "))

print("""
  This is the whole point of fail-fast config: a missing DB_URL or a typo'd
  WORKER=8 crashes the process at BOOT, in staging, with a message naming the
  problem — instead of silently using a default and surfacing as a mystery at 3am.
  In real code: pydantic-settings with extra='forbid' and no default on required
  fields gives you exactly this.""")


# ---------------------------------------------------------------------------
section("B3. inject settings, don't import them")

print("""  # BAD — a module-level global is a singleton with all the usual problems
  from app.config import settings          # imported everywhere, unpatchable

  # GOOD — a cached provider you can override
  @lru_cache
  def get_settings() -> Settings:
      return Settings()

  @app.get("/x")
  async def endpoint(settings: Settings = Depends(get_settings)): ...

  # in tests:
  app.dependency_overrides[get_settings] = lambda: Settings(env="test", ...)

  Also: never commit secrets. .env is for local dev and is gitignored; production
  reads AWS Secrets Manager / Kubernetes Secrets / Vault, ideally with a short TTL
  cache so secrets can ROTATE without a redeploy.""")


# EXERCISE 1: add a `caching_mw` and an `auth_mw`. Build the chain with auth
#             INSIDE caching and prove a cache hit serves data without auth running.
# EXERCISE 2: add a middleware that catches exceptions and returns a 500 with the
#             correlation ID. Confirm it must be OUTERMOST to catch everything.
# EXERCISE 3: add a `secrets_dir` layer that reads files from a directory, mimicking
#             a Kubernetes secret mount, and put it between env vars and the .env file.
# EXERCISE 4: make Settings support a `prod`-only rule: log_level must not be DEBUG
#             when env == 'prod'. This is a cross-field validator.
