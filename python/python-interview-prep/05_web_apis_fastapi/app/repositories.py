"""In-memory 'database' behind a repository interface. Swap this for a real SQLAlchemy/Couchbase
repo later without touching app/services.py -- that's the whole point of the repository pattern."""
import itertools

from app.schemas import OrderOut


class NotFoundError(Exception):
    def __init__(self, resource: str):
        super().__init__(f"{resource} not found")


class OrderRepository:
    def __init__(self):
        self._store: dict[str, OrderOut] = {}
        self._ids = itertools.count(1)

    def save(self, customer_id: int, total: float, status: str) -> OrderOut:
        order_id = f"ORD-{next(self._ids)}"
        order = OrderOut(id=order_id, customer_id=customer_id, total=total, status=status)
        self._store[order_id] = order
        return order

    def get(self, order_id: str) -> OrderOut:
        if order_id not in self._store:
            raise NotFoundError(f"order {order_id}")
        return self._store[order_id]

    def list_for_customer(self, customer_id: int) -> list[OrderOut]:
        return [o for o in self._store.values() if o.customer_id == customer_id]
