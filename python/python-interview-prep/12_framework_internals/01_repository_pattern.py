"""
The repository pattern: the single highest-value structural decision in a service.

Swap PostgreSQL for Couchbase, or add a cache layer, WITHOUT touching business logic —
and unit-test the service with no database at all.

Run me: python 01_repository_pattern.py
Deep dive: ../deep_dive/11_python_framework_development.md
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generic, Optional, Protocol, TypeVar


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================== domain
@dataclass
class Order:
    id: int
    user_id: int
    total: float
    status: str = "PENDING"


class NotFoundError(Exception):
    """A DOMAIN exception. Note it knows nothing about HTTP."""


class ValidationError(Exception):
    """Ditto — the service layer never imports a web framework."""


# ================================================================== contract
T = TypeVar("T")


class Repository(Protocol, Generic[T]):
    """Structural contract. Implementations need NOT inherit from this."""

    def get_by_id(self, id: int) -> Optional[T]: ...
    def save(self, obj: T) -> T: ...
    def delete(self, id: int) -> bool: ...


class BaseRepository(ABC, Generic[T]):
    """Generic CRUD shared by concrete repositories."""

    def __init__(self, store):
        self._store = store

    @abstractmethod
    def _table(self) -> str: ...

    def get_by_id(self, id):
        return self._store.get(self._table(), id)

    def get_all(self, limit=100, offset=0):
        return self._store.scan(self._table())[offset:offset + limit]

    def save(self, obj):
        self._store.put(self._table(), obj.id, obj)
        return obj

    def delete(self, id):
        return self._store.remove(self._table(), id)


# ================================================================== backend 1
class FakeSQLStore:
    """Stands in for SQLAlchemy + PostgreSQL."""

    def __init__(self):
        self.tables = {}
        self.queries = []                       # so we can SEE the access pattern

    def get(self, table, key):
        self.queries.append(f"SELECT * FROM {table} WHERE id = {key}")
        return self.tables.get(table, {}).get(key)

    def put(self, table, key, value):
        self.queries.append(f"UPSERT INTO {table} (id) VALUES ({key})")
        self.tables.setdefault(table, {})[key] = value

    def scan(self, table):
        self.queries.append(f"SELECT * FROM {table}")
        return list(self.tables.get(table, {}).values())

    def remove(self, table, key):
        self.queries.append(f"DELETE FROM {table} WHERE id = {key}")
        return self.tables.get(table, {}).pop(key, None) is not None


class SqlOrderRepository(BaseRepository[Order]):
    def _table(self):
        return "orders"

    def get_by_user(self, user_id):             # domain-specific query
        self._store.queries.append(
            f"SELECT * FROM orders WHERE user_id = {user_id}")
        return [o for o in self._store.scan("orders") if o.user_id == user_id]


# ================================================================== backend 2
class InMemoryOrderRepository:
    """Satisfies the SAME Protocol without inheriting anything. This is the test double."""

    def __init__(self):
        self._data: dict[int, Order] = {}

    def get_by_id(self, id):
        return self._data.get(id)

    def get_all(self, limit=100, offset=0):
        return list(self._data.values())[offset:offset + limit]

    def save(self, obj):
        self._data[obj.id] = obj
        return obj

    def delete(self, id):
        return self._data.pop(id, None) is not None

    def get_by_user(self, user_id):
        return [o for o in self._data.values() if o.user_id == user_id]


# ================================================================== backend 3
class CachingOrderRepository:
    """DECORATES any repository with a read cache. The service is unaware."""

    def __init__(self, inner, ttl=300):
        self._inner = inner
        self._cache: dict[int, Order] = {}
        self.hits = self.misses = 0

    def get_by_id(self, id):
        if id in self._cache:
            self.hits += 1
            return self._cache[id]
        self.misses += 1
        obj = self._inner.get_by_id(id)
        if obj is not None:
            self._cache[id] = obj
        return obj

    def save(self, obj):
        self._cache.pop(obj.id, None)          # INVALIDATE on write, don't update
        return self._inner.save(obj)

    def delete(self, id):
        self._cache.pop(id, None)
        return self._inner.delete(id)

    def get_by_user(self, user_id):
        return self._inner.get_by_user(user_id)


# ================================================================== service
class OrderService:
    """Business logic. Knows NOTHING about SQL, Couchbase, HTTP or caching."""

    def __init__(self, repo):
        self.repo = repo                        # injected — this is the whole point

    def place(self, order: Order) -> Order:
        if order.total <= 0:
            raise ValidationError("total must be positive")
        return self.repo.save(order)

    def get(self, order_id: int) -> Order:
        order = self.repo.get_by_id(order_id)
        if order is None:
            raise NotFoundError(f"order {order_id} not found")
        return order

    def cancel(self, order_id: int) -> Order:
        order = self.get(order_id)
        if order.status == "SHIPPED":
            raise ValidationError("cannot cancel a shipped order")
        order.status = "CANCELLED"
        return self.repo.save(order)


# ================================================================== demo
section("1. the same service, three different repositories — zero code changes")

for label, repo in [
    ("SQL-backed     ", SqlOrderRepository(FakeSQLStore())),
    ("in-memory (test)", InMemoryOrderRepository()),
    ("cached SQL      ", CachingOrderRepository(SqlOrderRepository(FakeSQLStore()))),
]:
    svc = OrderService(repo)                    # IDENTICAL construction
    svc.place(Order(id=1, user_id=42, total=250.0))
    got = svc.get(1)
    cancelled = svc.cancel(1)
    print(f"  {label}  ->  get={got.total}  after cancel: {cancelled.status}")


section("2. the caching repository is invisible to the service")

inner = SqlOrderRepository(FakeSQLStore())
cached = CachingOrderRepository(inner)
svc = OrderService(cached)
svc.place(Order(id=7, user_id=1, total=99.0))

for _ in range(5):
    svc.get(7)
print(f"  5 reads -> cache hits={cached.hits} misses={cached.misses}")
print(f"  SQL statements actually issued: {len(inner._store.queries)}")
for q in inner._store.queries:
    print(f"     {q}")
print("\n  Adding caching touched ZERO lines of OrderService.")


section("3. domain exceptions carry no HTTP knowledge — the router maps them")

svc = OrderService(InMemoryOrderRepository())

# This is the ONLY place HTTP status codes are decided (normally in main.py)
EXCEPTION_STATUS = {NotFoundError: 404, ValidationError: 422}


def handle(fn, *args):
    try:
        return 200, fn(*args)
    except tuple(EXCEPTION_STATUS) as e:
        return EXCEPTION_STATUS[type(e)], str(e)


print("  place(total=-5) ->", handle(svc.place, Order(id=2, user_id=1, total=-5.0)))
print("  get(999)        ->", handle(svc.get, 999))
svc.place(Order(id=2, user_id=1, total=10.0))
print("  get(2)          ->", handle(svc.get, 2))
print("\n  OrderService never imported fastapi. It is callable from a Kafka consumer,")
print("  a CLI command or a Lambda handler with no changes.")


section("4. why this matters for TESTS")

import time

t = time.perf_counter()
for i in range(10_000):
    OrderService(InMemoryOrderRepository()).place(Order(id=i, user_id=1, total=10.0))
elapsed = time.perf_counter() - t
print(f"  10,000 service operations against a fake repo: {elapsed:.3f}s")
print("  No database, no container, no fixtures. That is why the suite gets RUN.")


# EXERCISE 1: add a CouchbaseOrderRepository satisfying the same Protocol. Confirm
#             OrderService works against it without a single edit.
# EXERCISE 2: the caching repo invalidates on write. Change it to UPDATE the cache
#             instead, then write a test with two interleaved writers that proves
#             the cache can end up holding the OLDER value.
# EXERCISE 3: move the transaction boundary into the SERVICE (a context manager that
#             spans two repositories) and explain why the repository must not commit.
# EXERCISE 4: install mypy and delete a method from InMemoryOrderRepository. Confirm
#             mypy catches the Protocol violation even though nothing inherits it.
