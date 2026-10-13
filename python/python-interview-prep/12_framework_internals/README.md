# 12 — Framework Internals (Python Framework Development)

Pure stdlib — every file runs with `py <file>.py`, no dependencies.

"Framework development" in an interview rarely means *writing a web framework*. It means:
**can you design the skeleton other engineers build inside?** Layering, extension points,
dependency wiring, configuration, and the discipline that stops a service becoming a
4,000-line `main.py`.

These files rebuild the machinery FastAPI gives you, so you can **explain what `Depends()`
actually does** rather than just using it.

> **Full Q&A**: [`deep_dive/11_python_framework_development.md`](../deep_dive/11_python_framework_development.md)
> **See it applied**: [`05_web_apis_fastapi/`](../05_web_apis_fastapi/) is a real layered app
> using exactly these patterns.

## Crib sheet

- **Layered, domain-driven structure**: routers (HTTP only) → services (business logic) →
  repositories (data access). **Each layer depends only on the one below.** Never skip layers.
- **Routers parse, delegate, return.** No business logic. If a router asks "is this order
  already paid?", that belongs in the service.
- **Services never import the web framework.** No `HTTPException`, no `Request`. They raise
  *domain* exceptions, which is what lets the same service be called from a Kafka consumer,
  a CLI command or a Lambda without dragging HTTP along.
- **The repository pattern is the highest-value structural decision** — it lets you swap
  PostgreSQL for Couchbase, or add a cache layer, without touching service code, and it lets
  you unit-test services against an in-memory fake with no infrastructure.
- **The repository must NOT own the transaction boundary.** It calls `flush()`, not
  `commit()` — the service commits, because one business operation may span several
  repositories and must be atomic.
- **Domain exceptions are not caught in routers.** They propagate to central
  `exception_handler` registrations, so HTTP status codes are decided in exactly **one place**.
- **Dependency injection** decouples construction from use. In FastAPI, `Depends()` resolves a
  graph per request, caches each dependency once per request, and supports `yield` for
  setup/teardown. `app.dependency_overrides` is what makes tests fast.
- **Middleware order is inverted**: the middleware added **last** is the **outermost** and
  runs **first**. Get this wrong and a cache hit short-circuits your auth check.
- **Never label metrics with a raw path.** `/orders/12345` creates one time series per order
  ID — a cardinality explosion that will take down Prometheus. Use the route *template*.
- **Configuration is env-driven and validated at startup.** A missing `DB_URL` should crash
  the process at boot, not surface as a mystery at 3am. `extra="forbid"` catches typo'd
  variable names instead of silently using a default.
- **Inject settings, don't import them** — a module-level `settings` global is a singleton
  with all the usual testability problems.

## Files

| File | Topic |
|---|---|
| `01_repository_pattern.py` | generic `BaseRepository[T]`, `Protocol` contracts, swapping SQL → in-memory → cached with zero service changes, domain exceptions |
| `02_dependency_injection.py` | `Depends()` built from scratch: graph resolution, per-request caching, `yield` teardown via `ExitStack`, `dependency_overrides` |
| `03_plugin_architecture.py` | decorator registry vs `__init_subclass__` vs setuptools entry points; startup validation; when *not* to build a plugin system |
| `04_middleware_and_config.py` | the middleware chain and why order is inverted; the metrics cardinality trap; layered config with `ChainMap`; fail-fast validation |

## Suggested order

`01` → `02` → `04` → `03`

Do the repository pattern first — it's the one that changes how you structure everything else.

## The questions these answer

- How do you structure a large-scale Python REST API project?
- How do you build a generic repository base class?
- What is dependency injection and why does it matter? What does `Depends()` actually do?
- How do you implement a plugin / extension architecture?
- How do you build custom middleware, and when should it be a dependency instead?
- How do you handle configuration across environments?
- How do you implement API versioning, pagination, rate limiting, health checks?
