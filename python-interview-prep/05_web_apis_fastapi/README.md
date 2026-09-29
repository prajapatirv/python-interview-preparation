# 05 — Web APIs: FastAPI + REST semantics

A small but real layered FastAPI app (routers → services → repositories) plus REST notes covering
status codes, versioning, and auth vs authz. Needs `fastapi`, `uvicorn`, `pydantic`, `httpx`.

## Crib sheet

- **Layering**: routers handle HTTP only (thin); services hold business logic; repositories
  abstract data access. Each layer depends only on the one below it — this is what lets you swap
  the in-memory repo here for a real database without touching `services/`.
- **Dependency injection**: `Depends(callable)` is called per-request and its result injected.
  A `yield`-based dependency (see `app/dependencies.py::get_db`) does setup before `yield` and
  teardown after — the FastAPI equivalent of a context manager.
- **`async def` vs `def` endpoints**: use `async def` only when everything inside is non-blocking
  (async DB driver, `httpx.AsyncClient`). A blocking call inside `async def` freezes the whole
  worker's event loop for every other request; FastAPI runs plain `def` endpoints in a thread pool
  automatically, so blocking code there is safe.
- **`response_model`** filters AND validates what goes out, independent of what the internal
  object looks like — a real security boundary (it won't leak a field you forgot to hide).
- **Testing**: `TestClient` (built on `httpx`) drives the app in-process with no real server;
  `app.dependency_overrides` swaps a real dependency for a fake one per test.
- **REST status codes**: 200 read success, 201 created, 204 no body, 400 malformed, 401 no/bad
  credentials, 403 authenticated but not allowed, 404 missing, 409 conflict, 422 fails validation,
  429 rate limited, 500 unhandled bug, 503 overloaded/circuit open.
- **Auth vs authz**: authentication proves identity (→ 401 on failure); authorization checks
  permission once identity is known (→ 403 on failure). Keep them as separate dependencies.
- **Gotcha**: a *missing* required header/param (e.g. `Authorization: str = Header(...)` with no
  default) fails FastAPI's own request validation and returns **422**, before your function body
  ever runs. Only a *present-but-wrong* value reaches your code to raise the **401** yourself.
  `tests/test_orders_api.py::test_auth_rejects_wrong_token` exercises this deliberately.

## Run it

```bash
cd 05_web_apis_fastapi
uvicorn app.main:app --reload
# then open http://127.0.0.1:8000/docs for interactive Swagger UI
```

## Files

| Path | Role |
|---|---|
| `app/main.py` | app factory, router registration, global exception handler |
| `app/config.py` | `pydantic-settings`-based configuration |
| `app/schemas.py` | Pydantic request/response models |
| `app/repositories.py` | in-memory "database" behind a repo interface |
| `app/services.py` | business logic (validation, total calculation) |
| `app/dependencies.py` | `Depends()` providers: DB session, current user, rate limiter |
| `app/routers/orders.py` | thin HTTP layer: parses request, calls service, returns response |
| `tests/test_orders_api.py` | `TestClient` + `dependency_overrides` |
| `rest_api_notes.md` | status codes / versioning / headers reference (no runnable code) |

## Try it against a running server

```bash
curl -X POST http://127.0.0.1:8000/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer demo-token" \
  -d '{"customer_id": 1, "items": [{"sku": "A", "qty": 2, "price": 9.99}]}'
```

## Exercise

`app/dependencies.py::require_admin` already demonstrates chaining one `Depends()` on another
(authz depends on authn). Wire it onto a new `DELETE /orders/{order_id}` endpoint, add a
`respository.delete()` method, and write two `TestClient` tests: one asserting a non-admin gets
403, and one asserting an overridden admin user gets 204. This exercises the
`app.dependency_overrides` pattern from `tests/test_orders_api.py` for a case the shipped tests
don't already cover.
