"""
Unit tests for OrderService, showing fixtures, mocking, pytest.raises, and parametrize.
Run me: pytest -v  (from this folder or the project root)
"""
from unittest.mock import MagicMock

import pytest

from src.order_service import OrderService, PaymentError


@pytest.fixture
def svc():
    """A fresh OrderService with fully mocked dependencies for every test."""
    repo = MagicMock()
    payment = MagicMock()
    payment.charge.return_value = MagicMock(success=True)
    repo.save.return_value = {"id": "ORD-1"}
    return OrderService(repo, payment)


def test_place_order_success(svc):
    items = [{"price": 100, "qty": 2}]
    result = svc.place_order("u1", items)

    assert result["id"] == "ORD-1"
    svc.payment.charge.assert_called_once_with("u1", 200)


def test_empty_items_raises(svc):
    with pytest.raises(ValueError, match="items"):
        svc.place_order("u1", [])


def test_payment_failure_raises(svc):
    svc.payment.charge.return_value = MagicMock(success=False)

    with pytest.raises(PaymentError):
        svc.place_order("u1", [{"price": 50, "qty": 1}])

    # important: the repo should NEVER be touched if payment failed
    svc.repo.save.assert_not_called()


@pytest.mark.parametrize(
    "qty,price,expected_total",
    [
        (1, 50, 50),
        (3, 20, 60),
        (2, 100, 200),
    ],
)
def test_total_calculation(svc, qty, price, expected_total):
    items = [{"qty": qty, "price": price}]
    svc.place_order("u1", items)
    svc.payment.charge.assert_called_once_with("u1", expected_total)


def test_multiple_line_items_sum_correctly(svc):
    items = [{"price": 10, "qty": 3}, {"price": 5, "qty": 2}]
    svc.place_order("u1", items)
    svc.payment.charge.assert_called_once_with("u1", 40)  # 30 + 10
