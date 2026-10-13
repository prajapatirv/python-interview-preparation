# Deep Dive 10 — Web Frameworks: Django / Flask / FastAPI (FastAPI in depth)

> Runnable companion: [`05_web_apis_fastapi/`](../05_web_apis_fastapi/) — a layered FastAPI app with
> routers → services → repositories, DI, central exception handlers and tests.
> Related deep dives: [Framework development](11_python_framework_development.md) ·
> [Concurrency](07_concurrency.md) · [Error handling](08_error_handling.md) · [Java bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

Two things. First, **can you choose**: given a problem, do you pick Django, Flask or FastAPI for
defensible reasons rather than familiarity? Second, **do you know one of them deeply** — architecture,
DI, async semantics, testing, production deployment.

For a Python backend + Kafka + GenAI profile, **FastAPI is the right one to go deep on**: it's
async-native, validation is built in, and it's what most new Python microservices use. Expect a
direct Spring Boot comparison if Java is on your CV, so have that mapping ready.

---

## Must-know points

- **Django**: batteries-included — ORM, admin, auth, migrations, templating. Sync-first, WSGI with
  ASGI support.
- **Flask**: micro-framework, WSGI, you choose every extension.
- **FastAPI**: ASGI on Starlette, Pydantic v2 validation, type-hint driven, async-first, automatic
  OpenAPI.
- **WSGI = sync, ASGI = async.** Flask is WSGI; FastAPI/Starlette are ASGI; Django supports both.
- **Key FastAPI concepts**: path/query/body params, `Depends()`, `response_model`, middleware,
  `BackgroundTasks`, `lifespan`.
- **`async def` endpoints run on the event loop; `def` endpoints run in a thread pool.** Getting this
  backwards is the single most damaging FastAPI mistake.

---

## Part A — Choosing a framework

### Q1. Compare Django, Flask and FastAPI. When would you pick each?

| Aspect | Flask | FastAPI | Django / DRF |
|---|---|---|---|
| **Best fit** | Small services, prototypes, full control | High-throughput async APIs | Complex domain with admin |
| **Async** | No (WSGI; 2.x has limited async) | **Yes** (ASGI, native) | Partial (ASGI views, sync ORM) |
| **Auto OpenAPI docs** | No (extension) | **Yes, built in** | Via drf-spectacular |
| **Request validation** | Manual / marshmallow | **Pydantic, automatic** | DRF serializers |
| **ORM bundled** | No | No | **Yes** (Django ORM) |
| **Admin UI** | No | No | **Yes** — often the deciding factor |
| **Auth** | Extension | You build / extension | **Built in** (users, perms, sessions) |
| **Migrations** | Alembic | Alembic | **Built in** |
| **Setup overhead** | Minimal | Minimal | High (many conventions) |
| **Learning curve** | Lowest | Low–medium | Highest |

**How to choose, stated as decisions rather than preferences:**

- **Django** when the app is **data-model-centric with humans administering it** — a CMS, an internal
  portal, a back-office. The admin alone can save months. Also when you want one opinionated stack
  and a large team that benefits from convention over configuration.
- **Flask** when the service is **small and you want no opinions** — a webhook receiver, a sidecar, a
  legacy integration. Or when the team already knows it well.
- **FastAPI** when it's an **API-first microservice**: high I/O concurrency, strong request/response
  contracts, auto-generated docs for consumers. ML/GenAI inference endpoints, event-driven services,
  anything talking to Kafka or an LLM.

**For a microservice ecosystem with Kafka and LLM calls, FastAPI is usually the answer** — those
workloads are I/O-bound and benefit directly from async, and Pydantic gives you a validated contract
at the boundary for free.

**The honest caveats** (mentioning them raises your credibility):

- FastAPI has **no ORM, no admin, no auth** — you assemble SQLAlchemy + Alembic + your own auth. For
  a CRUD-heavy internal app that's weeks of work Django gives you free.
- **Async is not automatically faster.** For a CPU-bound or low-concurrency service, Flask under
  Gunicorn is simpler and just as fast.
- Django's async story has improved a lot (async views, async ORM in 4.1+), so "Django can't do
  async" is out of date.

---

### Q2. What are WSGI and ASGI?

**WSGI** (PEP 3333) is the synchronous interface between Python web applications and servers. The
contract is a single callable:

```python
def application(environ, start_response):
    start_response("200 OK", [("Content-Type", "text/plain")])
    return [b"Hello"]
```

One request occupies one worker **thread or process** for its entire duration. If the handler waits
2 s on a database, that worker is unavailable for 2 s. Concurrency = worker count. Servers: Gunicorn,
uWSGI, mod_wsgi.

**ASGI** is the async successor. The contract is an async callable with `receive`/`send` channels,
which supports **long-lived connections and streaming**:

```python
async def application(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"Hello"})
```

What ASGI adds beyond `async`/`await`:

- **WebSockets** — impossible in WSGI.
- **Server-Sent Events / streaming responses** — essential for streaming LLM tokens.
- **Long-lived connections** at high concurrency, since a waiting request costs a coroutine (~KB),
  not a thread (~MB).
- **Lifespan protocol** — startup/shutdown events, which is how FastAPI's `lifespan` works.

Servers: Uvicorn, Hypercorn, Daphne. Flask is WSGI; FastAPI/Starlette are ASGI; Django supports both.

> **Java contrast.** WSGI ≈ the Servlet API (thread-per-request, Tomcat). ASGI ≈ Servlet 3.1 async /
> Netty / WebFlux. The same trade-off exists in both ecosystems: thread-per-request is simpler to
> reason about and debug; the event-loop model scales to far more concurrent connections.

---

## Part B — FastAPI in depth

### Q3. How does FastAPI use type hints and Pydantic?

FastAPI **reads your function signature** and derives everything from it — where each parameter comes
from, how to validate it, and what the OpenAPI schema should say.

The rules FastAPI applies to each parameter:

1. Name appears in the **path template** → it's a **path parameter**.
2. Type is a **Pydantic model** → it's the **request body**.
3. Otherwise (a scalar: `int`, `str`, `bool`, `float`) → it's a **query parameter**.
4. Explicit markers override: `Query(...)`, `Path(...)`, `Body(...)`, `Header(...)`, `Cookie(...)`,
   `Form(...)`, `File(...)`, `Depends(...)`.

```python
from fastapi import FastAPI, Query, Path
from pydantic import BaseModel, Field, field_validator

class OrderIn(BaseModel):
    customer_id: int
    amount: float = Field(gt=0, description="Order total, must be positive")
    currency: str = Field(default="INR", pattern="^[A-Z]{3}$")

    @field_validator("currency")
    @classmethod
    def known_currency(cls, v):
        if v not in {"INR", "USD", "EUR"}:
            raise ValueError(f"unsupported currency {v}")
        return v

class OrderOut(BaseModel):
    id: int
    status: str
    # internal_notes is deliberately absent -> never serialised to clients

app = FastAPI()

@app.post("/orders", response_model=OrderOut, status_code=201, tags=["Orders"])
async def create_order(
    order: OrderIn,                                           # body (Pydantic model)
    notify: bool = False,                                     # query param, optional
    idempotency_key: str = Query(..., min_length=8),          # query, required + validated
):
    return OrderOut(id=1, status="CREATED")
```

**What you get from those hints, with no extra code:**

- **Parsing and coercion** — `"5"` from a query string becomes `int` 5.
- **Validation** — a failure returns **422** with a precise, structured error body naming the field.
- **`response_model` filters the output** — this is a **security feature**, not just documentation.
  Return an ORM object with a `password_hash` and `response_model` strips it. Relying on "I won't
  return that field" is how data leaks.
- **OpenAPI schema** at `/openapi.json`, Swagger UI at `/docs`, ReDoc at `/redoc`.
- **Editor autocomplete and mypy checking** on the same declarations.

**Pydantic v2 note:** the core is written in Rust (`pydantic-core`) and is roughly 5–50× faster than
v1. Migration gotchas: `@validator` → `@field_validator`, `class Config` → `model_config =
ConfigDict(...)`, `.dict()` → `.model_dump()`, `.json()` → `.model_dump_json()`, `orm_mode` →
`from_attributes`.

---

### Q4. Explain dependency injection in FastAPI with `Depends()`.

`Depends(callable)` tells FastAPI to **call that dependency for each request and inject the result**.
It's FastAPI's DI container.

The properties that make it more than a decorator:

- **Dependencies can depend on other dependencies** — FastAPI builds and resolves the whole graph.
- **Results are cached per request** — a dependency used by three others runs once. (`use_cache=False`
  to opt out.)
- **`yield` dependencies** provide setup/teardown, with the teardown running *after* the response.
- **They're overridable in tests** via `app.dependency_overrides`, with zero changes to source code.
- **They appear in the OpenAPI schema** — security schemes, required headers and query params show up
  in `/docs`.

```python
from fastapi import Depends, Header, HTTPException, FastAPI

# 1. A yield dependency — setup before, teardown after the response is sent
async def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()                       # always runs, even if the endpoint raised

# 2. A dependency that raises — auth
async def current_user(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "invalid token")
    return {"id": 7, "roles": ["admin"]}

# 3. A dependency depending on dependencies — the service layer
def get_order_service(db=Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db))

# 4. A parameterised dependency (a class or a factory)
class RoleChecker:
    def __init__(self, *roles): self.roles = set(roles)
    def __call__(self, user=Depends(current_user)):
        if not self.roles & set(user["roles"]):
            raise HTTPException(403, "forbidden")
        return user

app = FastAPI()

@app.get("/me")
async def me(user=Depends(current_user), svc=Depends(get_order_service)):
    return user

@app.delete("/orders/{oid}", dependencies=[Depends(RoleChecker("admin"))])
async def delete_order(oid: int, svc=Depends(get_order_service)):
    return svc.delete(oid)               # `dependencies=[...]` runs it but injects nothing
```

**Overriding in tests** — this is the payoff, and the reason DI beats module-level globals:

```python
def fake_user(): return {"id": 1, "roles": ["admin"]}

app.dependency_overrides[current_user] = fake_user
app.dependency_overrides[get_db] = lambda: in_memory_session
# ... run tests ...
app.dependency_overrides.clear()          # ALWAYS clear, or overrides leak across tests
```

No mocking library, no patching, no changes to route code. That's why the
[app in this repo](../05_web_apis_fastapi/app/dependencies.py) puts **every** provider in one
`dependencies.py`.

> **Java contrast.** `Depends()` ≈ Spring's `@Autowired`/constructor injection, but **per request and
> explicit in the signature** rather than resolved from a container by type. There's no component
> scanning and no magic — the dependency is visibly right there in the function signature, which
> makes the graph easier to follow.

---

### Q5. When should an endpoint be `async def` vs plain `def`?

**This is the highest-stakes FastAPI question**, because getting it wrong destroys throughput in a
way that looks like a mysterious latency problem.

| Endpoint | Runs on | Safe to block? |
|---|---|---|
| `async def` | **The event loop** (single thread) | **NO** — blocking freezes every concurrent request on that worker |
| `def` | **A thread pool** (`anyio`, ~40 threads) | **Yes** — FastAPI offloads it for you |

**The rules:**

1. **`async def` when everything inside is awaitable** — `asyncpg`, `httpx.AsyncClient`, `aiokafka`,
   `redis.asyncio`, async SQLAlchemy.
2. **plain `def` when you call blocking libraries** — `requests`, sync SQLAlchemy/`psycopg2`, `boto3`,
   heavy CPU work. FastAPI runs it in a thread pool, so blocking is fine.
3. **The catastrophic case: `async def` calling blocking code.** It freezes the whole loop.

```python
# WORST — async def with a blocking call. One slow call stalls EVERY concurrent
# request on this worker, including /health.
@app.get("/bad")
async def bad():
    return requests.get("https://slow-api.com").json()      # blocks the event loop

# FINE — sync endpoint, FastAPI runs it in a thread pool
@app.get("/ok-sync")
def ok_sync():
    return requests.get("https://slow-api.com").json()

# BEST — async all the way down
@app.get("/ok-async")
async def ok_async():
    async with httpx.AsyncClient() as client:
        r = await client.get("https://slow-api.com")
    return r.json()

# ESCAPE HATCH — async endpoint that must call one blocking thing
@app.get("/mixed")
async def mixed():
    return await asyncio.to_thread(blocking_legacy_call)
```

**A subtle, common version of the bug:** an `async def` endpoint that calls a *synchronous*
dependency which itself does I/O. The dependency's blocking call is still on the loop.

**How to detect it:** run with `PYTHONASYNCIODEBUG=1` or `asyncio.run(..., debug=True)` and watch for
"Executing <Task…> took 2.001 seconds" warnings. See
[Concurrency Q10](07_concurrency.md#q10-what-happens-if-you-call-timesleep-inside-async-code).

**If unsure, use plain `def`** — the thread pool is a safe default. The failure mode of a sync
endpoint is bounded (it consumes one of ~40 threads); the failure mode of a blocking async endpoint
is total.

---

### Q6. How do you structure a larger FastAPI application?

Layered, with strictly one-directional dependencies:

```
app/
├── main.py            # app factory, lifespan, middleware, exception handlers, router includes
├── config.py          # pydantic-settings — env-driven, cached
├── dependencies.py    # every Depends() provider in ONE place (so tests can override)
├── routers/           # HTTP layer ONLY — thin, no business logic
│   ├── orders.py
│   └── users.py
├── services.py        # business rules; raises DOMAIN exceptions, knows nothing about HTTP
├── repositories.py    # data access; raises NotFoundError; swappable
├── models.py          # ORM models
├── schemas.py         # Pydantic request/response DTOs — NOT the ORM models
├── events/            # Kafka producers/consumers
└── middleware/        # auth, tracing, rate limiting
```

**The rules that make this work**, each of which an interviewer may probe:

1. **Routers contain no business logic.** Parse, call the service, return. If a router has an `if`
   about business state, it's in the wrong layer.
2. **Services raise domain exceptions** (`ValidationError`, `NotFoundError`) and **never import
   FastAPI**. They must be unit-testable with no HTTP involved.
3. **Domain exceptions are NOT caught in routers.** They propagate to
   `@app.exception_handler(...)` registrations in `main.py`, which is the **single place HTTP status
   codes are decided**. See [Error handling Q13](08_error_handling.md#q13-how-should-a-rest-api-map-exceptions-to-responses).
4. **Separate Pydantic schemas from ORM models.** They change for different reasons; coupling them
   means a DB column rename becomes an API breaking change, and it's how internal fields leak.
5. **Every `Depends()` provider lives in `dependencies.py`**, so tests override in one place.
6. **The repository pattern** lets you swap PostgreSQL for Couchbase, or add a cache layer, without
   touching service code — the highest-value structural decision in the whole layout.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter

router = APIRouter(prefix="/orders", tags=["orders"])

@router.get("/{oid}")
async def get(oid: int, svc=Depends(get_order_service)):
    return await svc.get(oid)            # NotFoundError propagates to the handler in main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.producer = await start_kafka_producer()      # startup
    app.state.db = await create_pool()
    yield
    await app.state.producer.stop()                        # shutdown — flush!
    await app.state.db.close()

app = FastAPI(lifespan=lifespan)
app.include_router(router)
```

**`lifespan` replaced `@app.on_event("startup"/"shutdown")`**, which is deprecated. The context-manager
form guarantees teardown and makes the pairing obvious — it's
[`@asynccontextmanager`](05_context_managers_descriptors_metaclasses.md#q5-what-other-contextlib-utilities-are-useful)
doing exactly what it was designed for.

---

### Q7. How do you add middleware in FastAPI? Give a use case.

Middleware wraps **every** request/response. Two forms:

```python
import time, uuid

# 1. Decorator form — simplest
@app.middleware("http")
async def add_timing(request, call_next):
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = cid                # available to every handler
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.4f}"
    return response

# 2. Class form — Starlette's BaseHTTPMiddleware, for reusable/configurable middleware
from starlette.middleware.base import BaseHTTPMiddleware

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex)
        request.state.trace_id = trace_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception("[%s] unhandled", trace_id)
            raise
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Trace-Id"] = trace_id
        metrics.histogram("http_duration_ms", duration_ms,
                          tags=[f"path:{request.url.path}",
                                f"status:{response.status_code}"])
        return response

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["https://app.co"])
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

**Typical uses:** correlation IDs, request/response logging, timing and metrics, CORS, GZip,
authentication for whole route groups, rate limiting.

**Three things to get right:**

- **Order matters and is counter-intuitive**: middleware added **last** runs **first** (it's the
  outermost layer). So add CORS last if you want it outermost.
- **Middleware runs for *every* request** including `/health` and `/metrics` — keep it cheap. Never
  do I/O in middleware unless you must.
- **Prefer `Depends()` over middleware when it applies to only some routes.** Dependencies are
  scoped, testable via overrides, and documented in OpenAPI; middleware is none of those.

---

### Q8. How do you implement authentication (JWT/OAuth2) in FastAPI?

Use `OAuth2PasswordBearer` to extract the bearer token, verify the JWT in a **dependency**, and raise
401 on failure. Role checks become further dependencies.

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt                                      # PyJWT

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")   # also documents the scheme in /docs

async def current_user(token: str = Depends(oauth2_scheme)):
    creds_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},   # required by the spec for 401
    )
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=["HS256"],                 # NEVER accept the token's own `alg`
            audience=settings.jwt_audience,
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "token expired", headers={"WWW-Authenticate": "Bearer"})
    except jwt.PyJWTError:
        raise creds_error
    return {"id": payload["sub"], "roles": payload.get("roles", [])}

def require_role(*roles):
    def checker(user=Depends(current_user)):
        if not set(roles) & set(user["roles"]):
            raise HTTPException(403, "insufficient permissions")
        return user
    return checker

@app.delete("/orders/{oid}")
async def delete_order(oid: int, user=Depends(require_role("admin"))):
    ...
```

**The security points worth raising unprompted:**

- **Always pin `algorithms=[...]`.** Accepting the token's own `alg` header enables the classic
  `alg: none` and HS/RS confusion attacks.
- **401 vs 403**: 401 = *who are you?* (not authenticated); 403 = *I know who you are and no*
  (authenticated, not permitted).
- **For enterprise SSO** (Cognito, Keycloak, Azure AD, Auth0) you don't hold a shared secret — fetch
  the IdP's **JWKS**, cache it, and verify with the matching public key by `kid`.
- **Validate `exp`, `aud` and `iss`**, not just the signature.

**The `Header(...)` gotcha this repo documents** — and it catches people in interviews: a required
`Header(...)` with no default fails **FastAPI's own validation with 422** if the header is *missing
entirely*, **before your function body runs**. Only a *present-but-wrong* value reaches your code to
raise a deliberate 401. Get it backwards and your auth test asserts the wrong status code. See
[`05_web_apis_fastapi/README.md`](../05_web_apis_fastapi/README.md).

---

### Q9. What are `BackgroundTasks` and when are they not enough?

`BackgroundTasks` runs a function **after the response is sent**, in the same process.

```python
from fastapi import BackgroundTasks

@app.post("/orders", status_code=201)
async def create(order: OrderIn, bg: BackgroundTasks, svc=Depends(get_order_service)):
    saved = await svc.create(order)
    bg.add_task(send_confirmation_email, saved.id)    # runs after the 201 is returned
    return saved
```

Good for genuinely fire-and-forget, non-critical work: an email, an audit log line, a cache warm.

**When it is NOT enough — and this is the real question:**

- **Not durable.** If the process crashes or the pod is rescheduled between response and task, the
  work is **silently lost**. No record that it should have happened.
- **No retries.** An exception is logged and the task is gone.
- **No visibility.** No queue depth, no DLQ, no way to know how far behind you are.
- **Competes for the same resources.** A heavy background task starves your request handling —
  if it's a sync function it consumes one of the ~40 thread-pool threads.
- **Doesn't survive a graceful shutdown** unless you explicitly drain.

**For anything that must happen, use durable infrastructure:**

| Need | Tool |
|---|---|
| Durable task queue with retries and scheduling | **Celery** (Redis/RabbitMQ), **Arq**, **RQ**, **Dramatiq** |
| Event-driven fan-out, replay, multiple consumers | **Kafka** — see [Kafka pipelines](14_kafka_pipelines_delivery_semantics.md) |
| Guaranteed publish alongside a DB write | **Transactional outbox** — see [Queue architectures](18_queue_architectures.md) |

```python
from celery import Celery

celery = Celery("app", broker="redis://localhost/0")

@celery.task(bind=True, max_retries=3, default_retry_delay=30, acks_late=True)
def process_report(self, order_id):
    try:
        build_and_email_report(order_id)
    except TransientError as e:
        raise self.retry(exc=e)              # exponential backoff retry

# from the API:
process_report.delay(order_id)               # returns immediately, work is durable
```

**The decision rule to state:** if losing the task would be noticed by a customer or an auditor, it
doesn't belong in `BackgroundTasks`.

---

### Q10. How do you test a FastAPI application?

`TestClient` (sync, built on httpx) for most tests, `httpx.AsyncClient` with `ASGITransport` when you
need real async. **Override dependencies rather than patching.**

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import current_user, get_order_service

def fake_user(): return {"id": 1, "roles": ["admin"]}

@pytest.fixture
def client():
    app.dependency_overrides[current_user] = fake_user
    app.dependency_overrides[get_order_service] = lambda: FakeOrderService()
    yield TestClient(app)
    app.dependency_overrides.clear()          # ESSENTIAL — otherwise overrides leak

def test_me(client):
    r = client.get("/me")
    assert r.status_code == 200
    assert r.json()["id"] == 1

def test_missing_header_is_422_not_401(client):
    # The repo's documented gotcha: a missing required Header fails FastAPI validation first
    app.dependency_overrides.clear()
    r = TestClient(app).get("/me")
    assert r.status_code == 422               # NOT 401
```

Async version:

```python
import httpx, pytest

@pytest.mark.asyncio
async def test_async():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/me")
    assert r.status_code == 200
```

**The testing pyramid for this architecture:**

1. **Unit-test services** directly with fake repositories — no HTTP, no DB, milliseconds.
2. **Integration-test routes** with `TestClient` and overridden dependencies — checks wiring,
   status codes, serialisation.
3. **A few end-to-end tests** against a real DB (testcontainers) — checks migrations and SQL.

`TestClient` **does trigger `lifespan`** when used as a context manager (`with TestClient(app) as
c:`), which matters if your startup connects to Kafka — either mock it or use the non-context form.
See [`05_web_apis_fastapi/tests/test_orders_api.py`](../05_web_apis_fastapi/tests/test_orders_api.py).

---

### Q11. How do you run FastAPI in production?

```bash
# Gunicorn as the process manager, Uvicorn workers doing the async work
gunicorn app.main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --bind 0.0.0.0:8000 \
  --timeout 30 \
  --keep-alive 5 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --access-logfile -
```

```python
# gunicorn.conf.py — the same, version-controlled
workers = 4                          # CPU cores for async; 2-4x cores if mostly sync
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 30
keepalive = 5
max_requests = 1000                  # recycle workers to bound any memory leak
max_requests_jitter = 100            # de-synchronise restarts (avoid a thundering herd)
accesslog = "-"                      # stdout, for container log collection
```

**The full production checklist:**

- **Worker count**: roughly `#cores` for async workloads (each worker has its own event loop, so more
  workers ≠ more concurrency for I/O). `2–4 × cores` if endpoints are mostly sync/thread-pool. In
  Kubernetes, often **1 worker per pod** and scale with replicas — simpler resource accounting.
- **Reverse proxy / load balancer** in front (nginx, ALB, Ingress) for TLS and connection handling.
- **Connection pooling** to the DB, sized so `pods × workers × pool_size` doesn't exceed the DB's
  limit — see [Scaling Q5](12_scaling_applications.md#q5-how-do-you-implement-database-connection-pooling-in-python).
- **Health endpoints**: `/health/live` (process alive) and `/health/ready` (dependencies reachable).
- **Structured JSON logs** to stdout, with the correlation ID on every line.
- **Prometheus metrics** at `/metrics`; **OpenTelemetry** tracing.
- **Graceful shutdown** via `lifespan` — drain in-flight requests, flush the Kafka producer, close
  the pool. Kubernetes `terminationGracePeriodSeconds` must exceed it.
- **`--max-requests` with jitter** to bound leaks without synchronised restarts.
- **Never `--reload` in production**; never `uvicorn` alone without a process manager.

All of this is covered in [Production stability](19_production_stability_monitoring.md).

---

### Q12. Explain the Django request lifecycle and its ORM basics.

**Lifecycle:** request → WSGI/ASGI handler → **middleware chain (request phase, top-down)** → URL
resolver (`urls.py`) → **view** (function or class-based) → ORM / templates → response → **middleware
chain (response phase, bottom-up)** → client.

**ORM essentials:**

- **Models map to tables**; `makemigrations`/`migrate` track schema changes.
- **QuerySets are lazy and chainable** — no SQL runs until you iterate, slice, or call
  `len()`/`list()`/`exists()`. That laziness is why you can build a query across several functions.
- **The N+1 problem is the interview question here:**

```python
# N+1: 1 query for books + 1 query per book for its author = 101 queries
for book in Book.objects.all():
    print(book.author.name)

# select_related — SQL JOIN, for ForeignKey / OneToOne (forward, single-valued)
for book in Book.objects.select_related("author"):
    print(book.author.name)                     # 1 query total

# prefetch_related — a SECOND query + Python-side join, for M2M / reverse FK (multi-valued)
for author in Author.objects.prefetch_related("books"):
    print([b.title for b in author.books.all()])   # 2 queries total
```

The distinction to state crisply: **`select_related` = JOIN, for single-valued forward relations;
`prefetch_related` = separate query, for multi-valued relations** (you can't JOIN a to-many relation
without row multiplication).

Other essentials: `only()`/`defer()` to limit columns, `annotate()`/`aggregate()` for
window/aggregate functions, `F()` expressions for atomic DB-side updates
(`F("count") + 1` avoids a read-modify-write race), `Q()` for complex OR/AND filters, and
`select_for_update()` for row locks inside `transaction.atomic()`.

---

### Q13. Flask: explain application and request context, and blueprints.

Flask uses **context locals** — thread-local (really, context-local) proxies that make
`current_app`, `g`, `request` and `session` available anywhere during a request without passing them
as arguments.

- **Application context** — `current_app` (the app instance) and `g` (a per-request scratchpad for
  things like a DB connection).
- **Request context** — `request` (incoming data) and `session` (the signed cookie).

```python
from flask import Flask, g, current_app, request

app = Flask(__name__)

@app.before_request
def open_db():
    g.db = connect()                 # one connection per request, on `g`

@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()

@app.route("/orders")
def orders():
    return {"host": request.host, "env": current_app.config["ENV"]}
```

**The classic error** — `RuntimeError: Working outside of application context` — happens when you
touch `current_app` or `g` from a background thread, a CLI command, or a test without pushing a
context. The fix is `with app.app_context():` or `with app.test_request_context():`.

**Blueprints** group routes, templates and static files into modular components registered on the
app — the direct analogue of FastAPI's `APIRouter` and Django's app/`include()`:

```python
from flask import Blueprint

orders_bp = Blueprint("orders", __name__, url_prefix="/orders")

@orders_bp.route("/<int:oid>")
def get_order(oid): ...

app.register_blueprint(orders_bp)
```

**The contrast worth drawing:** Flask's implicit context locals are convenient but hide dependencies
and make testing require context pushing. FastAPI's explicit `Depends()` puts the same information
in the function signature — more typing, less magic, and it's why FastAPI code is easier to unit test.

---

### Q14. How does FastAPI compare with Spring Boot for a Java developer?

| Spring Boot | FastAPI |
|---|---|
| `@RestController` / `@RequestMapping` | `APIRouter` + `@app.get/post` path operations |
| `@RequestBody` DTO + Bean Validation (`@Valid`) | Pydantic model parameter (validation is automatic) |
| `@PathVariable` / `@RequestParam` | Path params from the template / typed function params |
| `@Autowired`, constructor injection | `Depends()` — **per request**, explicit in the signature |
| `@Service` / `@Repository` stereotypes | Plain classes + a `Depends()` provider |
| `@ControllerAdvice` / `@ExceptionHandler` | `@app.exception_handler(...)` |
| Filters / `HandlerInterceptor` | Middleware (`@app.middleware("http")`) |
| Spring Actuator (`/health`, `/metrics`) | Hand-rolled `/health` + `prometheus-fastapi-instrumentator` |
| Springdoc / Swagger annotations | OpenAPI generated automatically from type hints |
| `application.yml` + `@ConfigurationProperties` | `pydantic-settings` `BaseSettings` |
| Spring Data JPA / Hibernate | SQLAlchemy (+ Alembic for migrations) |
| `@Transactional` | An explicit `async with session.begin():` block |
| Spring Kafka `@KafkaListener` | `confluent-kafka` / `aiokafka` consumer in a lifespan-managed task |
| `@Async` / `CompletableFuture` | `async def` + `asyncio` |
| JUnit + Mockito + `@SpringBootTest` | pytest + `TestClient` + `dependency_overrides` |

**The honest summary to give:**

- **FastAPI is lighter and async-native.** Less ceremony, far less configuration, faster startup.
- **Spring Boot has more built-in enterprise machinery** — Actuator, declarative transactions,
  security, batch, an enormous integration catalogue. In FastAPI you assemble those.
- **DI differs meaningfully**: Spring resolves by type from a container at startup, with component
  scanning; FastAPI resolves per request from the explicit signature. Spring's is more powerful and
  more magical; FastAPI's is more traceable and trivially overridable in tests.
- **The biggest mental shift is concurrency.** Spring's thread-per-request model tolerates blocking
  calls anywhere. FastAPI's event loop does not — `async def` + a blocking call is a production
  outage. See [Q5](#q5-when-should-an-endpoint-be-async-def-vs-plain-def).

---

## Worked example — FastAPI service that validates an order and publishes it to Kafka

This is the shape interviewers like, because it exercises `lifespan`, validation, async/sync bridging
and graceful shutdown all at once. The subtle part is that `confluent-kafka` is a **synchronous C
library** whose delivery callbacks fire inside `poll()` — so you need a bridge back to the event loop.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from confluent_kafka import Producer, KafkaException
import asyncio, threading

class Order(BaseModel):
    order_id: str
    customer_id: int
    amount: float = Field(gt=0)

@asynccontextmanager
async def lifespan(app: FastAPI):
    p = Producer({
        "bootstrap.servers": "localhost:9092",
        "enable.idempotence": True,          # implies acks=all — no duplicates from retries
        "linger.ms": 10,
        "compression.type": "zstd",
    })
    stop = threading.Event()

    def poll_loop():                          # delivery callbacks only fire inside poll()
        while not stop.is_set():
            p.poll(0.1)

    t = threading.Thread(target=poll_loop, daemon=True)
    t.start()
    app.state.producer = p
    yield
    stop.set()
    t.join()
    p.flush(10)                               # GRACEFUL SHUTDOWN: never lose buffered messages

app = FastAPI(lifespan=lifespan)

@app.post("/orders", status_code=202)
async def create(order: Order):
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def on_delivery(err, msg):                # runs on the POLL THREAD, not the loop
        if err:
            loop.call_soon_threadsafe(fut.set_exception, KafkaException(err))
        else:
            loop.call_soon_threadsafe(fut.set_result, msg.offset())

    app.state.producer.produce(
        "orders",
        key=order.order_id,                   # key -> partition -> per-order ordering
        value=order.model_dump_json(),
        on_delivery=on_delivery,
    )
    try:
        offset = await asyncio.wait_for(fut, timeout=10)
    except Exception as e:
        raise HTTPException(503, f"publish failed: {e}")
    return {"status": "ACCEPTED", "offset": offset}
```

**The five points to narrate:**

1. **`loop.call_soon_threadsafe`** is mandatory — the delivery callback runs on the poll thread, and
   touching an asyncio Future from another thread without it is a data race.
2. **`p.flush(10)` in the lifespan teardown** is the difference between graceful shutdown and losing
   every buffered message on deploy. `produce()` is asynchronous and buffers locally.
3. **`enable.idempotence=True`** stops producer retries creating duplicates.
4. **`key=order_id`** routes all events for an order to one partition, preserving per-order ordering.
5. **202 Accepted, not 201** — you've accepted it for processing, not completed it. Honest semantics.

For an asyncio-native alternative, `aiokafka` removes the thread bridge entirely — worth mentioning
as the cleaner option when the whole service is async. See
[Kafka pipelines](14_kafka_pipelines_delivery_semantics.md).

---

## Hands-on drills

1. Write an `async def` endpoint calling `requests.get` against a 2-second endpoint. Fire 10
   concurrent requests and measure total time. Change it to `def` and measure again. Explain both.
2. Return an ORM object containing `password_hash` from an endpoint with no `response_model`. Confirm
   the leak. Add `response_model` and confirm it's stripped.
3. Write a dependency chain three deep and log inside each. Confirm the shared one is called **once**
   per request, then set `use_cache=False` and watch it change.
4. Override `get_db` and `current_user` in a pytest fixture. Forget `clear()` and watch the override
   leak into an unrelated test.
5. Make a required `Header(...)` and call the endpoint (a) with no header and (b) with a wrong value.
   Confirm 422 and 401 respectively.
6. Add three middlewares that each log their name on entry and exit. Predict the order, then verify.
7. Build the Kafka publisher above, then kill the process mid-request **without** `p.flush()` in
   teardown. Confirm the message is lost. Add the flush and confirm it isn't.
8. Run under Gunicorn with `--workers 4` and hit `/metrics`. Explain why an in-process counter shows
   only a quarter of the traffic.

---

## The 60-second spoken answer

> "Django when the app is model-centric and I want the admin, ORM, auth and migrations for free;
> Flask for something small where I want no opinions; FastAPI for API-first microservices — which is
> what I'd pick for a Kafka and LLM-facing service, because it's ASGI so it handles high I/O
> concurrency, and Pydantic gives me a validated contract and OpenAPI docs straight from type hints.
> The thing I'd stress about FastAPI is the async rule: `async def` runs on the event loop and a
> single blocking call there stalls every concurrent request on that worker, whereas a plain `def`
> endpoint is offloaded to a thread pool, so if I'm using `requests` or `boto3` I use `def`. I
> structure apps as routers → services → repositories, with routers holding no business logic,
> services raising domain exceptions that propagate to central `exception_handler` registrations so
> status codes are decided in one place, and every `Depends()` provider in one module so tests can
> swap them with `dependency_overrides` instead of patching. Startup and shutdown go in `lifespan` —
> that's where I flush the Kafka producer, and skipping it loses buffered messages on every deploy.
> In production it's Gunicorn with Uvicorn workers behind a proxy, `max_requests` with jitter,
> structured JSON logs, `/health/live` and `/health/ready`, and Prometheus metrics. Coming from
> Spring: routers are controllers, Pydantic is Bean Validation, `Depends()` is `@Autowired` but per
> request and explicit, and `exception_handler` is `@ControllerAdvice`."
