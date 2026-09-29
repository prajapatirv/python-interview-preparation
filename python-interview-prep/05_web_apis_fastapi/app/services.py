"""Business logic layer. Takes plain values/DTOs and a repo -- no HTTP concepts leak in here,
which is exactly what makes it trivially unit-testable (see 04_testing_tdd for the pattern)."""
from app.repositories import OrderRepository
from app.schemas import OrderIn, OrderOut


class ValidationError(Exception):
    pass


class OrderService:
    def __init__(self, repo: OrderRepository):
        self.repo = repo

    def place_order(self, order: OrderIn) -> OrderOut:
        if not order.items:
            raise ValidationError("order must contain at least one item")

        total = sum(item.qty * item.price for item in order.items)
        return self.repo.save(order.customer_id, round(total, 2), status="CREATED")

    def get_order(self, order_id: str) -> OrderOut:
        return self.repo.get(order_id)  # raises NotFoundError -- let the router translate it
