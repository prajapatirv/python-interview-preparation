# REST API — reference notes (no runnable code here; concepts backing `app/`)

## HTTP method semantics

| Method | Meaning | Idempotent? | Safe (no side effects)? |
|---|---|---|---|
| GET | read | yes | yes |
| PUT | full replace | yes | no |
| PATCH | partial update | no (usually) | no |
| DELETE | remove | yes | no |
| POST | create / action | no | no |

## Status codes worth memorizing cold

| Code | Meaning | When |
|---|---|---|
| 200 | OK | successful GET/PUT/PATCH |
| 201 | Created | POST that created a resource (see `create_order`) |
| 204 | No Content | DELETE success, nothing to return |
| 400 | Bad Request | malformed syntax |
| 401 | Unauthorized | missing/invalid credentials (see `get_current_user`) |
| 403 | Forbidden | authenticated but not permitted (see `require_admin`) |
| 404 | Not Found | resource missing (see `NotFoundError` handler) |
| 409 | Conflict | duplicate resource |
| 422 | Unprocessable Entity | valid syntax, fails validation (Pydantic, or our `ValidationError` handler) |
| 429 | Too Many Requests | rate limited (see `rate_limit` dependency) |
| 500 | Internal Server Error | unhandled bug — never leak internals here |
| 503 | Service Unavailable | overloaded, or a circuit breaker is open (see `08_scaling_production_resilience`) |

## Critical headers

| Header | Use |
|---|---|
| `Content-Type: application/json` | body format being sent |
| `Accept: application/json` | desired response format |
| `Authorization: Bearer <token>` | auth credential |
| `X-Request-ID` / `X-Correlation-ID` | distributed tracing, idempotency keys |
| `If-None-Match: <etag>` | conditional GET → 304 Not Modified |
| `Retry-After` | tells the client how long to back off (pair with 429/503) |

## API versioning strategies

1. **URI versioning** (most common): `/v1/orders/{id}`, `/v2/orders/{id}` — side by side, easy to
   deprecate one with a `Deprecation: true` header + sunset date.
2. **Header versioning**: `Accept: application/vnd.company.v2+json`.
3. **Query param**: `GET /orders/1?version=2` — simplest, least discoverable.

## Auth vs authz, concretely

- **Authentication** (`get_current_user`): "who are you?" — verifies a token/credential.
  Failure → **401**.
- **Authorization** (`require_admin`): "are you allowed to do this?" — checked *after* identity
  is known, usually role/scope based. Failure → **403**.
- Keep them as two separate `Depends()` — chaining `require_admin` on `get_current_user` (as this
  project does) makes the order of checks explicit and each one independently testable.

## Pagination: offset vs keyset

- **Offset** (`?page=2&size=20`) is simple but `OFFSET n` becomes O(n) at large `n` — the DB still
  scans and discards the skipped rows.
- **Keyset/cursor** (`?after_id=145&size=20`, i.e. `WHERE id > :after_id ORDER BY id LIMIT :size`)
  uses the index directly — O(log n) — and stays stable even as rows are inserted concurrently.
  Prefer keyset for any endpoint that returns a large or frequently-changing collection.
