"""The class under test. Kept dependency-free (repo/payment client are injected) so it's
trivially unit-testable with mocks -- see tests/test_order_service.py."""


class PaymentError(Exception):
    pass


class OrderService:
    def __init__(self, repo, payment_client):
        self.repo = repo
        self.payment = payment_client

    def place_order(self, user_id, items):
        if not items:
            raise ValueError("order must have items")

        total = sum(i["price"] * i["qty"] for i in items)

        result = self.payment.charge(user_id, total)
        if not result.success:
            raise PaymentError("payment failed")

        order = {"user_id": user_id, "items": items, "total": total}
        return self.repo.save(order)
