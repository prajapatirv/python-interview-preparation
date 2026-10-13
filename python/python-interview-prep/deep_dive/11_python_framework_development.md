# Deep Dive 11 — Python Framework Development

> Runnable companion: [`12_framework_internals/`](../12_framework_internals/) — repository pattern,
> plugin registry, DI container, middleware chain, config management.
> Related deep dives: [Web frameworks](10_web_frameworks.md) · [Decorators](03_decorators.md) ·
> [Descriptors & metaclasses](05_context_managers_descriptors_metaclasses.md) · [Scaling](12_scaling_applications.md)

## What interviewers are actually probing

"Framework development" doesn't usually mean *writing a web framework*. It means: **can you design
the skeleton other engineers build inside?** Layering, extension points, configuration, dependency
wiring, versioning, and the discipline that stops a service becoming a 4,000-line `main.py`.

This is the section where a 6–10 year candidate is separated from a 3-year one. A junior answers
"I'd use FastAPI." A senior answers with **layer boundaries, what each layer may import, where
exceptions are translated, and how it stays testable without infrastructure**.

---

## Must-know points

- **Layered, domain-driven structure**: routers (HTTP only) → services (business logic) →
  repositories (data access). **Each layer depends only on the one below.**
- **The repository pattern is the highest-value structural decision** — it lets you swap PostgreSQL
  for Couchbase, or add caching, without touching service code.
- **Domain exceptions propagate**; HTTP status codes are decided in **one** place.
- **Dependency injection** decouples construction from use and makes services testable without a DB
  or broker.
- **Configuration is env-driven and validated at startup** (`pydantic-settings`), never hardcoded.
- **Extension points** — plugins via a registry or entry points; middleware for cross-cutting
  concerns.

---

## Interview questions and full answers

### Q1. How do you structure a large-scale Python REST API project?

A **layered, domain-driven structure** where each layer has one responsibility and depends only on
the layer below. Never skip layers.

```
src/
├── main.py               # app factory, lifespan, middleware, exception handlers
├── config.py             # pydantic-settings — env-driven, validated, cached
├── dependencies.py       # every shared Depends() provider
├── routers/              # HTTP layer ONLY — thin
│   ├── __init__.py
│   ├── orders.py
│   └── users.py
├── services/             # business rules, orchestration — NO framework imports
│   ├── order_service.py
│   └── user_service.py
├── repositories/         # data access — SQLAlchemy / Couchbase / HTTP clients
│   ├── base_repo.py      # generic CRUD base
│   └── order_repo.py
├── models/               # ORM models
├── schemas/              # Pydantic request/response DTOs
├── events/               # Kafka producers/consumers
├── middleware/           # auth, tracing, rate limiting
└── tests/
    ├── unit/             # services with fake repos — fast, no infra
    └── integration/      # real DB via testcontainers
```

**The rules that make the structure real rather than decorative** — state these, because the folder
names alone prove nothing:

1. **Routers parse, delegate, return.** No business logic, no `if` statements about domain state. If
   a router asks "is this order already paid?", that belongs in the service.
2. **Services never import the web framework.** No `HTTPException`, no `Request`. They raise
   **domain** exceptions (`OrderAlreadyPaid`, `InsufficientStock`). This is what lets you call the
   same service from a Kafka consumer, a CLI command, or a Lambda without dragging HTTP along.
3. **Repositories hide the storage technology.** Services receive an interface, not a `Session`.
4. **Schemas are separate from models.** ORM models change when the database changes; DTOs change
   when the API contract changes. Coupling them turns a column rename into a breaking API change and
   is how `password_hash` leaks into a response.
5. **Dependencies point inward/downward only.** Repositories must not import services. If you need
   that, you have a layering error — usually a service that should be split.

**The repository pattern is the most important decision here.** With it, "we're moving from
PostgreSQL to Couchbase" or "add a Redis cache in front of reads" touches one file. Without it,
`session.query(...)` is scattered through business logic and the migration is a rewrite.

**The honest caveat to raise:** don't apply all of this to a 200-line service. Layering has a cost;
for a small, single-purpose Lambda a flat module is correct. Knowing when *not* to layer is as much a
signal as knowing how.

---

### Q2. How do you build a generic repository base class?

Use `typing.Generic` + `TypeVar` so the base provides typed CRUD and each concrete repository adds
only its domain-specific queries.

```python
from abc import ABC
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class BaseRepository(ABC, Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: int) -> Optional[T]:
        return await self.session.get(self.model, id)

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        q = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def save(self, obj: T) -> T:
        self.session.add(obj)
        await self.session.flush()      # assigns the generated PK without committing
        await self.session.refresh(obj) # load DB-side defaults back onto the object
        return obj

    async def delete(self, id: int) -> bool:
        obj = await self.get_by_id(id)
        if not obj:
            return False
        await self.session.delete(obj)
        return True

class OrderRepository(BaseRepository["Order"]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Order)

    async def get_by_user(self, user_id: int) -> List["Order"]:
        q = select(Order).where(Order.user_id == user_id)
        return list((await self.session.execute(q)).scalars().all())

    async def get_pending_older_than(self, cutoff) -> List["Order"]:
        q = select(Order).where(Order.status == "PENDING", Order.created_at < cutoff)
        return list((await self.session.execute(q)).scalars().all())
```

**Design points worth narrating:**

- **`flush()` not `commit()`.** The repository must **not own the transaction boundary** — the
  service does, because one business operation may span several repositories and must commit
  atomically. A repository that commits makes multi-repository transactions impossible.
- **`Generic[T]`** gives real type checking: `OrderRepository.get_by_id` is typed as returning
  `Optional[Order]`, not `Any`.
- **Return domain objects, not `Row`s or `Session`s.** The abstraction leaks the moment a service
  sees SQLAlchemy types.
- **Be careful not to over-genericise.** A `BaseRepository` with 30 methods nobody uses is worse than
  none. Keep it to genuinely universal CRUD and let concrete repos own their queries.
- **Define the interface with `Protocol` or `ABC`** so the service depends on the abstraction and
  tests can pass a dict-backed fake:

```python
from typing import Protocol

class OrderRepo(Protocol):
    async def get_by_id(self, id: int) -> Optional["Order"]: ...
    async def save(self, obj: "Order") -> "Order": ...

class InMemoryOrderRepo:                     # structurally satisfies OrderRepo — no inheritance
    def __init__(self): self._data = {}
    async def get_by_id(self, id): return self._data.get(id)
    async def save(self, obj): self._data[obj.id] = obj; return obj
```

That fake is what makes service unit tests run in milliseconds with no database — see
[`05_web_apis_fastapi/app/repositories.py`](../05_web_apis_fastapi/app/repositories.py).

---

### Q3. How do you build custom middleware in FastAPI?

Middleware wraps every request/response — the place for **cross-cutting concerns** that apply
uniformly: correlation IDs, timing, metrics, logging, CORS, compression.

```python
import time, uuid, logging
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        trace_id = request.headers.get("X-Trace-Id", uuid.uuid4().hex)
        request.state.trace_id = trace_id           # every handler can read this
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception("[%s] unhandled on %s", trace_id, request.url.path)
            raise                                    # let the exception handler produce the 500
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Duration-Ms"] = f"{duration_ms:.1f}"
        metrics.histogram(
            "http_duration_ms", duration_ms,
            tags=[f"path:{request.url.path}", f"status:{response.status_code}"],
        )
        return response

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["https://app.co"])
```

**Four things to get right:**

1. **Order is inverted**: the middleware added **last** is the **outermost** and runs **first**.
2. **Use the route template, not the raw path, as a metric tag.** `f"path:{request.url.path}"` with
   `/orders/12345` creates a new time series per order ID — that's a **cardinality explosion** that
   will take down your Prometheus. Use `request.scope.get("route").path` (`/orders/{id}`) instead.
   This is a real production incident, and mentioning it is a strong signal.
3. **Keep it cheap** — it runs on `/health` and `/metrics` too.
4. **Prefer `Depends()` when it applies to only some routes.** Dependencies are scoped, overridable
   in tests, and documented in OpenAPI. Middleware is none of those.

**Propagating the trace ID into logs** is the other half — use a `ContextVar` so every log line in
that request carries it automatically without threading it through every function:

```python
import contextvars
trace_id_var = contextvars.ContextVar("trace_id", default="-")

# in middleware:
trace_id_var.set(trace_id)

# in a logging filter:
class TraceFilter(logging.Filter):
    def filter(self, record):
        record.trace_id = trace_id_var.get()
        return True
```

`ContextVar` (not `threading.local`) is essential here — it's async-aware and follows the task, not
the thread. See [Production stability](19_production_stability_monitoring.md).

---

### Q4. How do you implement a plugin / extension architecture?

Two approaches, chosen by whether plugins live inside your codebase or are installed separately.

**Approach 1 — a registry decorator (in-process, simple):**

```python
from abc import ABC, abstractmethod

_PLUGINS: dict[str, type] = {}

def register(name):
    """Register a plugin implementation under a name."""
    def deco(cls):
        if name in _PLUGINS:
            raise ValueError(f"duplicate plugin name: {name}")
        _PLUGINS[name] = cls
        return cls                      # MUST return the class
    return deco

class StorageBackend(ABC):
    @abstractmethod
    async def put(self, key, value): ...
    @abstractmethod
    async def get(self, key): ...

@register("redis")
class RedisBackend(StorageBackend):
    async def put(self, k, v): await redis.set(k, v)
    async def get(self, k):    return await redis.get(k)

@register("couchbase")
class CouchbaseBackend(StorageBackend):
    async def put(self, k, v): coll.upsert(k, v)
    async def get(self, k):    return coll.get(k).content_as[dict]

def get_backend(name: str) -> StorageBackend:
    try:
        return _PLUGINS[name]()
    except KeyError:
        raise ValueError(f"unknown backend {name!r}; available: {sorted(_PLUGINS)}")

backend = get_backend(settings.storage_backend)     # driven by config
```

**The catch with decorator registries: the module must be imported for the decorator to run.** If
`couchbase_backend.py` is never imported, it's never registered. Solutions: import them explicitly in
a package `__init__.py`, or auto-discover with `pkgutil.iter_modules`.

**`__init_subclass__` avoids that problem for subclass-based plugins** — registration happens
automatically when the class is defined, with no decorator:

```python
class StorageBackend(ABC):
    registry: dict[str, type] = {}

    def __init_subclass__(cls, key=None, **kw):
        super().__init_subclass__(**kw)
        if key:
            StorageBackend.registry[key] = cls

class RedisBackend(StorageBackend, key="redis"): ...
```

**Approach 2 — setuptools entry points (out-of-process, real extensibility):** lets a *separate pip
package* extend your application without you knowing it exists. This is how pytest plugins, Airflow
providers and Flask extensions work.

```toml
# in the PLUGIN package's pyproject.toml
[project.entry-points."myapp.storage_backends"]
s3 = "myapp_s3_plugin:S3Backend"
```

```python
# in YOUR application — discovers anything installed in the environment
from importlib.metadata import entry_points

def load_plugins():
    for ep in entry_points(group="myapp.storage_backends"):
        _PLUGINS[ep.name] = ep.load()
```

**Choosing:** registry for internal strategies you control; entry points when third parties (or other
teams shipping their own packages) must extend you without a PR to your repo.

**Design rules for either:** define the contract as an `ABC` or `Protocol`; **validate plugins at
startup**, not on first use, so a misconfiguration fails the deploy rather than a request; and make
the active plugin visible in `/health` and in your startup logs.

---

### Q5. What is dependency injection in Python frameworks and why does it matter?

DI **decouples construction from use**: an object receives its collaborators instead of creating
them. The practical payoff is that the collaborator becomes **substitutable**.

```python
# WITHOUT DI — untestable. You cannot run this without a real database.
class OrderService:
    def __init__(self):
        self.repo = OrderRepository(create_engine(os.environ["DB_URL"]))
        self.kafka = KafkaProducer(bootstrap_servers=os.environ["KAFKA"])

# WITH DI — the dependencies are explicit and swappable
class OrderService:
    def __init__(self, repo: OrderRepo, publisher: Publisher):
        self.repo = repo
        self.publisher = publisher

svc = OrderService(InMemoryOrderRepo(), FakePublisher())   # a unit test, no infra
```

In FastAPI, `Depends()` is the DI mechanism and the graph is resolved per request:

```python
# production wiring
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

def get_order_service(db=Depends(get_db)) -> OrderService:
    return OrderService(OrderRepository(db), KafkaPublisher())

# test wiring — no source changes at all
app.dependency_overrides[get_order_service] = lambda: OrderService(
    InMemoryOrderRepo(), FakePublisher()
)
```

**Why it matters, beyond "testing":**

- **Unit tests run in milliseconds** with no DB, no broker, no network. That changes how often people
  run them, which changes whether the suite is useful.
- **Swapping implementations** — in-memory for tests, Redis for dev, Couchbase for prod — becomes a
  config change.
- **Dependencies are visible in the signature.** You can read what a class needs without reading its
  body.
- **Lifecycle is managed once** — a `yield` dependency's teardown always runs.

**Do you need a DI container library?** Usually **no**. Python's `Depends()`, plain constructor
injection, and module-level factories cover almost everything. Reach for `dependency-injector` or
`punq` only in a large app with deep object graphs and multiple runtime profiles — and say that,
because reflexively adding a container is a Java-accent tell.

> **Java contrast.** Spring resolves by type from a container, with component scanning and
> `@Autowired`. FastAPI resolves per request from the explicit signature. Spring's is more powerful
> and more implicit; FastAPI's is more traceable. The `app.dependency_overrides` mechanism is the
> direct equivalent of `@MockBean`, but without the reflection.

---

### Q6. How do you handle configuration management across environments?

**Environment-driven, validated at startup, never hardcoded.** `pydantic-settings` gives you typed,
validated config with clear precedence.

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        secrets_dir="/run/secrets",         # Docker/K8s secrets mounted as files
        extra="forbid",                     # unknown env vars are an ERROR, not ignored
    )

    environment: str = "dev"
    db_url: str                             # no default -> REQUIRED; startup fails without it
    redis_url: str
    kafka_brokers: str
    jwt_secret: str
    log_level: str = "INFO"
    max_workers: int = Field(default=4, ge=1, le=64)
    request_timeout_s: float = 5.0

    @field_validator("environment")
    @classmethod
    def known_env(cls, v):
        if v not in {"dev", "staging", "prod"}:
            raise ValueError(f"unknown environment: {v}")
        return v

@lru_cache
def get_settings() -> Settings:
    return Settings()                       # parsed once, cached for the process lifetime
```

**Precedence (highest wins):** actual environment variables → Docker/K8s secrets files → `.env`
file → defaults in the class.

**The principles that matter:**

1. **Fail fast at startup.** A field with no default is required; a missing `DB_URL` crashes the
   process on boot rather than on the first request at 2 a.m. `extra="forbid"` catches a typo'd env
   var name instead of silently using the default.
2. **Never commit secrets.** `.env` is for local development and is gitignored. In production use
   **AWS Secrets Manager / Parameter Store**, **Kubernetes Secrets**, or **Vault**.
3. **Config is environment, not code.** The same image runs in dev, staging and prod with different
   env vars — that's the Twelve-Factor rule, and it's what makes promoting a tested artefact
   meaningful.
4. **Cache it.** `@lru_cache` parses once. Without it, every `Settings()` re-reads and re-validates.
5. **Inject it, don't import it.** `settings = Depends(get_settings)` lets tests override with
   `TestSettings`. A module-level `settings` global is a singleton with all the usual problems.
6. **Rotate secrets without redeployment** — read them from Secrets Manager with a short TTL cache
   rather than baking them into env vars at pod start.

**Loading secrets from AWS at startup:**

```python
import boto3, json
from functools import lru_cache

@lru_cache(maxsize=1)
def _aws_secrets() -> dict:
    client = boto3.client("secretsmanager")
    raw = client.get_secret_value(SecretId="prod/myapp")["SecretString"]
    return json.loads(raw)

class Settings(BaseSettings):
    @classmethod
    def load(cls):
        return cls(**_aws_secrets()) if os.getenv("ENV") == "prod" else cls()
```

---

### Q7. How do you build a rate limiter as a FastAPI dependency?

As a **dependency**, so it's per-route, testable and documented — not as middleware, which would
apply globally.

```python
import time
from collections import defaultdict
from fastapi import Request, HTTPException, Depends

_windows: dict[str, list[float]] = defaultdict(list)

def rate_limit(max_calls: int, window_secs: int = 60):
    def dependency(request: Request):
        key = request.client.host                       # or user ID from the token
        now = time.monotonic()
        bucket = _windows[key]
        bucket[:] = [t for t in bucket if now - t < window_secs]   # drop expired
        if len(bucket) >= max_calls:
            raise HTTPException(
                429, "Rate limit exceeded",
                headers={"Retry-After": str(window_secs)},         # tell the client when
            )
        bucket.append(now)
    return dependency

@app.get("/api/data", dependencies=[Depends(rate_limit(100, 60))])
async def get_data(): ...
```

**Now say what's wrong with it**, because the interviewer is waiting for this:

1. **It is per-process.** With 4 Gunicorn workers × 3 pods you get **12× the intended limit**. For a
   real multi-instance limit you need shared state — Redis.
2. **`_windows` grows without bound** — every unique IP leaks an entry forever. Needs TTL eviction.
3. **Keying on `request.client.host` is wrong behind a proxy** — every request appears to come from
   the load balancer. Use `X-Forwarded-For` (carefully — it's spoofable unless your proxy overwrites
   it).
4. **A sliding-window *log* stores every timestamp.** Fine at 100/min; memory-hungry at 10,000/min.

**The production version — Redis, atomic, with TTL:**

```python
import redis.asyncio as aioredis

redis_client = aioredis.from_url(settings.redis_url)

def rate_limit(max_calls: int, window_secs: int = 60):
    async def dependency(request: Request, user=Depends(current_user)):
        key = f"ratelimit:{user['id']}:{int(time.time() // window_secs)}"  # fixed window
        pipe = redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_secs)          # self-cleaning: no unbounded growth
        count, _ = await pipe.execute()        # atomic round-trip
        if count > max_calls:
            raise HTTPException(429, "Rate limit exceeded",
                                headers={"Retry-After": str(window_secs)})
    return dependency
```

This is a **fixed window**, which allows a 2× burst at a window boundary. The refinements to name:
**sliding window log** (exact, memory-heavy), **sliding window counter** (weighted blend of two
windows — the usual production compromise), and **token bucket** (allows controlled bursts; what API
gateways use). See
[`08_scaling_production_resilience/03_rate_limiter.py`](../08_scaling_production_resilience/03_rate_limiter.py).

Also mention: rate limiting often belongs at the **API gateway / ingress** (Kong, Envoy, AWS API
Gateway, nginx) rather than in application code — cheaper, and it protects the app from the load
rather than absorbing it.

---

### Q8. How do you implement API versioning without breaking clients?

**URL path versioning** is the most common and the easiest to reason about:

```python
from fastapi import FastAPI, APIRouter

app = FastAPI()
v1 = APIRouter(prefix="/v1", tags=["v1"])
v2 = APIRouter(prefix="/v2", tags=["v2"])

@v1.get("/orders/{id}", response_model=OrderV1)
async def get_order_v1(id: int, svc=Depends(get_order_service)):
    return OrderV1.from_domain(await svc.get(id))

@v2.get("/orders/{id}", response_model=OrderV2)
async def get_order_v2(id: int, svc=Depends(get_order_service)):
    return OrderV2.from_domain(await svc.get(id))

app.include_router(v1)
app.include_router(v2)
```

**The critical design point:** version the **schemas and routers**, not the service layer. One
`OrderService` serves both; only the DTO mapping differs. Forking the business logic per version is
how you end up maintaining two divergent applications.

**The strategies, with trade-offs:**

| Strategy | Example | Pros | Cons |
|---|---|---|---|
| **URL path** | `/v1/orders` | Obvious, cacheable, easy to route | URL isn't a pure resource identifier |
| **Header** | `Accept: application/vnd.api.v2+json` | Clean URLs, RESTful purist | Invisible in a browser; harder to test/debug |
| **Query param** | `/orders?version=2` | Simple | Easy to forget; messes with caching |
| **No versioning** | Additive-only changes | Simplest of all | Only works if you *never* break |

**Deprecation process — the part people forget, and where the senior signal is:**

```python
@v1.get("/orders/{id}", deprecated=True)     # marks it in the OpenAPI docs
async def get_order_v1(id: int, response: Response):
    response.headers["Deprecation"] = "true"                          # RFC 8594
    response.headers["Sunset"] = "Wed, 01 Apr 2026 00:00:00 GMT"
    response.headers["Link"] = '</v2/orders>; rel="successor-version"'
    ...
```

Then: **measure v1 usage per client** (metrics tagged by API key), **contact the remaining
consumers**, agree a date, and only then remove it. "We announced it in the changelog" is not a
migration plan.

**Prefer additive, non-breaking changes** and you often avoid versioning entirely. Adding an optional
field is safe; removing or renaming one, changing a type, or tightening validation is not. This is
exactly the compatibility discipline of
[Kafka schema management](16_kafka_schema_management.md) — same problem, different transport.

---

### Q9. How do you implement health checks and readiness probes for Kubernetes?

**Two distinct endpoints with genuinely different semantics** — conflating them causes outages.

- **Liveness** — "is the process wedged?" Failing it makes Kubernetes **kill and restart** the pod.
  It must be **trivial** and check **nothing external**.
- **Readiness** — "can I serve traffic right now?" Failing it **removes the pod from the load
  balancer** without restarting it. It *should* check dependencies.

```python
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
import asyncio

@app.get("/health/live")
async def liveness():
    return {"status": "alive"}          # deliberately checks nothing

@app.get("/health/ready")
async def readiness():
    async def check(name, coro):
        try:
            await asyncio.wait_for(coro, timeout=2)     # ALWAYS bound the check
            return name, "ok"
        except Exception as e:
            return name, f"fail: {type(e).__name__}"

    results = await asyncio.gather(
        check("db", db.execute(text("SELECT 1"))),
        check("redis", redis_client.ping()),
        check("kafka", kafka_admin.list_topics(timeout=2)),
    )
    checks = dict(results)
    healthy = all(v == "ok" for v in checks.values())
    return JSONResponse(checks, status_code=200 if healthy else 503)
```

**The mistakes that cause real incidents:**

1. **Checking the database in the *liveness* probe.** The DB blips for 30 seconds → every pod fails
   liveness → Kubernetes restarts **every pod simultaneously** → you've turned a brief dependency
   blip into a full outage, and now you have a cold-start stampede too. **Liveness must never check
   external dependencies.**
2. **No timeout on the checks.** A hung DB connection makes the probe hang, which Kubernetes treats
   as a failure anyway — but slowly, and it ties up a worker.
3. **Not distinguishing hard from soft dependencies.** If the app can serve degraded traffic without
   Redis, a Redis failure should not mark it unready. Report it, don't fail on it.
4. **Forgetting `startupProbe`** for slow-starting apps (loading an ML model, warming a cache).
   Without it, liveness fires during startup and restarts the pod forever.

```yaml
livenessProbe:
  httpGet: { path: /health/live, port: 8000 }
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:
  httpGet: { path: /health/ready, port: 8000 }
  periodSeconds: 5
  failureThreshold: 2
startupProbe:                      # gives up to 150s to start before liveness kicks in
  httpGet: { path: /health/live, port: 8000 }
  failureThreshold: 30
  periodSeconds: 5
```

See [`08_scaling_production_resilience/04_health_checks_graceful_shutdown.py`](../08_scaling_production_resilience/04_health_checks_graceful_shutdown.py).

---

### Q10. How do you implement pagination — offset vs keyset?

```python
# OFFSET pagination — simple, but degrades badly and is unstable
@app.get("/orders")
async def list_orders(page: int = 1, size: int = 20, db=Depends(get_db)):
    q = select(Order).order_by(Order.id).offset((page - 1) * size).limit(size)
    return (await db.execute(q)).scalars().all()

# KEYSET (cursor) pagination — O(log n), stable under concurrent inserts
@app.get("/orders/cursor")
async def list_cursor(after_id: int = 0, size: int = 20, db=Depends(get_db)):
    q = select(Order).where(Order.id > after_id).order_by(Order.id).limit(size)
    rows = (await db.execute(q)).scalars().all()
    return {
        "data": rows,
        "next_cursor": rows[-1].id if len(rows) == size else None,
    }
```

**The two problems with OFFSET**, and you should name both:

1. **Performance.** `OFFSET 1000000` makes the database **scan and discard a million rows** before
   returning 20. It's O(n) in the offset, so page 50,000 is catastrophically slower than page 1.
   Every "why is our API slow?" investigation eventually finds a deep-offset query.
2. **Correctness — the drift problem.** If a row is inserted before page 1 while the client is
   reading, every subsequent page shifts by one: the client **sees one row twice and misses
   another**. For a paginating sync job, that's silent data loss.

**Keyset** uses `WHERE id > last_seen_id` which hits the index directly — O(log n) — and is immune to
inserts, because the cursor is anchored to a **value**, not a position.

**Keyset's limitations, which you should volunteer:**

- **No random access.** You cannot jump to "page 50" — only next/previous. For a UI with numbered
  pages, offset (or a hybrid) is required.
- **The sort key must be unique and stable.** Sorting by a non-unique column needs a **composite
  cursor** as a tiebreaker:

```python
# Sorting by created_at (not unique) — tie-break on id
q = (select(Order)
     .where(tuple_(Order.created_at, Order.id) > (last_created_at, last_id))
     .order_by(Order.created_at, Order.id)
     .limit(size))
```

- **Encode the cursor as an opaque token** (base64 of the composite key) so clients can't construct
  one and you can change the internals later.

**The rule:** offset for small, bounded, human-browsed datasets; **keyset for anything large or
machine-consumed** (sync jobs, exports, infinite scroll).

---

### Q11. How do you implement background tasks and job queues?

Matched to durability requirements — see
[Web frameworks Q9](10_web_frameworks.md#q9-what-are-backgroundtasks-and-when-are-they-not-enough)
for the full comparison.

```python
# TIER 1 — FastAPI BackgroundTasks: in-process, fire-and-forget, NOT durable
@app.post("/orders")
async def create(order: OrderIn, bg: BackgroundTasks):
    saved = await svc.create(order)
    bg.add_task(send_confirmation_email, saved.id)
    return saved

# TIER 2 — Celery: durable, retryable, distributed
from celery import Celery

celery = Celery("app", broker="redis://localhost/0", backend="redis://localhost/1")

@celery.task(bind=True, max_retries=3, default_retry_delay=30,
             acks_late=True, autoretry_for=(TransientError,), retry_backoff=True)
def process_report(self, order_id):
    build_and_email_report(order_id)

process_report.delay(order_id)          # returns immediately; work survives a crash

# TIER 3 — Kafka: event-driven, replayable, multiple independent consumers
await producer.send("order.placed", OrderPlacedEvent.from_order(order))
```

**Choosing:**

| Need | Tool |
|---|---|
| Trivial, loss-tolerant, in-process | `BackgroundTasks` |
| Durable task with retries and scheduling | **Celery** (feature-rich, heavy), **Arq** (asyncio-native, light), **RQ**, **Dramatiq** |
| Event broadcast to several independent consumers, with replay | **Kafka** |
| Guaranteed publish atomic with a DB write | **Transactional outbox** ([Queue architectures](18_queue_architectures.md)) |

**Celery configuration points that matter in production:**

- **`acks_late=True`** — acknowledge *after* the task completes, so a worker crash redelivers the
  task instead of losing it. Requires the task to be **idempotent**.
- **`retry_backoff=True`** plus `retry_jitter` — exponential backoff with jitter.
- **A dedicated queue per workload class** so a slow report job doesn't starve fast notifications.
- **`task_time_limit`** so a hung task doesn't occupy a worker forever.
- **Monitor queue depth and task latency** and alert on both.

---

### Q12. How do you handle file uploads securely?

```python
from fastapi import UploadFile, File, HTTPException
import boto3, magic, hashlib

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_SIZE = 50 * 1024 * 1024                 # 50 MB

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    content = await file.read()

    if len(content) > MAX_SIZE:
        raise HTTPException(413, "File too large")

    # Validate by CONTENT, not by extension or the client-supplied Content-Type
    mime = magic.from_buffer(content[:2048], mime=True)
    if mime not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported type: {mime}")

    # NEVER use the client's filename — generate a safe key from the content hash
    sha256 = hashlib.sha256(content).hexdigest()
    key = f"uploads/{sha256[:2]}/{sha256}"

    s3 = boto3.client("s3")
    s3.put_object(Bucket="my-bucket", Key=key, Body=content,
                  ContentType=mime, ServerSideEncryption="AES256")
    return {"key": key, "size": len(content)}
```

**Every line here is defending against a specific attack:**

1. **Size limit** — prevents memory exhaustion / DoS. Also enforce it at the **proxy**
   (`client_max_body_size` in nginx) so you reject before buffering.
2. **Content-based MIME detection** (`python-magic` reads magic bytes) — the extension and the
   client's `Content-Type` header are **attacker-controlled**. `evil.php` renamed to `cat.jpg` is the
   oldest trick there is.
3. **Never use the original filename** — it enables **path traversal** (`../../etc/passwd`),
   overwrites, and encoding attacks. A content hash also gives free deduplication.
4. **Two-character prefix directory** (`uploads/ab/abcd...`) — avoids millions of objects under one
   prefix, which matters for S3 listing and for filesystem storage.
5. **Server-side encryption** at rest.

**Additional hardening to mention:**

- **Stream large files instead of `await file.read()`**, which loads the whole thing into memory:

```python
hasher = hashlib.sha256()
while chunk := await file.read(1024 * 1024):     # 1 MB at a time
    hasher.update(chunk)
    temp.write(chunk)
```

- **Presigned S3 URLs** — let the client upload **directly to S3**, bypassing your service entirely.
  No bandwidth, no memory, no timeout risk. This is the right answer for large files.
- **Antivirus scanning** (ClamAV, or an S3 event → Lambda) for user-facing uploads.
- **Serve from a separate domain** so a stored-XSS payload can't run against your app's origin.

---

### Q13. What is the OpenAPI spec and how does FastAPI generate it?

**OpenAPI** (formerly Swagger) is a standard JSON/YAML description of an API: endpoints, parameters,
request/response schemas, auth schemes, examples, error codes.

FastAPI **introspects your type hints and Pydantic models at startup** and generates it — served at
`/openapi.json`, with Swagger UI at `/docs` and ReDoc at `/redoc`.

```python
@app.post(
    "/orders",
    response_model=OrderOut,
    status_code=201,
    responses={
        409: {"description": "Duplicate order", "model": ErrorOut},
        422: {"description": "Validation error"},
    },
    tags=["Orders"],
    summary="Place a new order",
    description="Creates an order and publishes an `order.placed` event to Kafka.",
    response_description="The created order with its assigned ID",
)
async def create_order(order: OrderIn):
    """Longer documentation can live in the docstring — it's picked up too."""
```

**Why it's worth investing in:**

- **Client SDK generation** — `openapi-generator` produces typed clients in TypeScript, Java, Go.
  Your consumers stop hand-writing HTTP calls.
- **Contract testing** — Schemathesis or Dredd generate property-based tests straight from the spec
  and find edge cases you didn't write tests for.
- **API gateway import** — AWS API Gateway and Kong consume OpenAPI directly.
- **It's always current**, because it's derived from the code rather than maintained alongside it.
  Hand-written API docs are wrong within a month.

**Production notes:** disable `/docs` on public-facing production services
(`FastAPI(docs_url=None, redoc_url=None)`) or put them behind auth — the schema is a map of your
attack surface. And export the spec **in CI** to diff it against the previous version, so a breaking
change fails the build rather than a customer's integration.

---

### Q14. How do you implement circuit breakers?

A circuit breaker stops you hammering a downstream that's already failing. States:

**CLOSED** (normal) → too many failures → **OPEN** (fail fast, don't even try) → after a timeout →
**HALF-OPEN** (allow one trial call) → success → **CLOSED**, or failure → **OPEN** again.

```python
from circuitbreaker import circuit
import requests

@circuit(failure_threshold=5, recovery_timeout=30,
         expected_exception=requests.Timeout)
def call_payment_service(order_id, amount):
    return requests.post(f"{PAYMENT_URL}/charge",
                         json={"order": order_id, "amount": amount}, timeout=3)

def charge_with_fallback(order_id, amount):
    try:
        return call_payment_service(order_id, amount)
    except CircuitBreakerError:
        # The circuit is open — the payment service is known-down. Don't wait 3s to find out.
        publish_to_retry_queue(order_id, amount)
        return {"status": "queued", "message": "Payment will be retried"}
```

**Why it matters, in one sentence:** without a breaker, a slow downstream consumes **all** your
worker threads/connections waiting on timeouts, and its outage becomes *your* outage — that's
**cascading failure**. The breaker converts a 3-second timeout into an instant failure, freeing
resources to serve everything else.

**Design points:**

- **`expected_exception` must be narrow.** Counting a 400 Bad Request as a circuit failure means bad
  client input opens your circuit.
- **Always have a fallback** — cached data, a queued retry, a degraded response. A breaker without a
  fallback just fails faster.
- **One breaker per downstream dependency**, not one global. A payment outage shouldn't stop you
  calling the inventory service.
- **Emit the state as a metric and alert on OPEN.** A silently open circuit is an invisible outage.
- **Combine with retries carefully:** retry *inside* the breaker, so repeated retries count toward
  opening it. Retrying an open circuit defeats the purpose.

See [`08_scaling_production_resilience/02_circuit_breaker.py`](../08_scaling_production_resilience/02_circuit_breaker.py)
and [Scaling](12_scaling_applications.md).

---

## Hands-on drills

1. Take a 500-line single-file FastAPI app and split it into routers/services/repositories. Then
   write a service unit test that runs with **no database**. Time the suite before and after.
2. Implement `BaseRepository[T]` with `Generic`. Write an `InMemoryOrderRepo` satisfying the same
   `Protocol` and run the service tests against both.
3. Build a plugin registry three ways: decorator, `__init_subclass__`, and entry points. Note which
   one requires the module to be imported first, and why.
4. Write `Settings` with a required field and no default. Run without the env var and confirm the
   process fails at startup, not at first request. Add `extra="forbid"` and introduce a typo.
5. Implement the in-process rate limiter, run it under `gunicorn -w 4`, and measure the actual
   effective limit. Then implement the Redis version and measure again.
6. Add a middleware tagging metrics with `request.url.path`, generate 10,000 requests to
   `/orders/{random_id}`, and count the resulting time series. Fix it with the route template.
7. Put a DB check in the liveness probe, kill the DB, and watch Kubernetes restart every pod. Move
   the check to readiness and repeat.
8. Create 1,000,000 rows and time `OFFSET 0 LIMIT 20` against `OFFSET 999980 LIMIT 20`. Then
   implement keyset pagination and time page 50,000.

---

## The 60-second spoken answer

> "I structure services in layers with one-directional dependencies: routers handle HTTP only,
> services hold business logic and raise domain exceptions without importing the web framework, and
> repositories hide the storage technology. The repository pattern is the decision that pays off
> most — swapping Postgres for Couchbase or adding a cache touches one file instead of the whole
> codebase — and because services take a repository interface, I can unit-test them against an
> in-memory fake with no infrastructure, so the suite runs in milliseconds. Domain exceptions aren't
> caught in routers; they propagate to central `exception_handler` registrations so status codes are
> decided in exactly one place. Every `Depends()` provider lives in one module so tests override with
> `dependency_overrides` rather than patching. Config is `pydantic-settings`: env-driven, validated
> at startup so a missing `DB_URL` fails the boot, with secrets from Secrets Manager rather than
> env vars. For extension points I use a registry or `__init_subclass__` internally and setuptools
> entry points when third parties need to extend without touching my repo. And I'm careful about
> the operational details — separate liveness and readiness probes, keyset pagination for anything
> large, metrics tagged by route template rather than raw path to avoid cardinality explosions, and
> a circuit breaker per downstream so their outage doesn't become mine."
