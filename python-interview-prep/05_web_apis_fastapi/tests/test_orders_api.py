"""
Integration tests against the real router stack via TestClient, with auth/rate-limit
dependencies overridden so tests don't depend on the demo token or timing.
Run me: pytest -v   (from 05_web_apis_fastapi/)
"""
from fastapi.testclient import TestClient

from app.dependencies import get_current_user, get_order_service, rate_limit
from app.main import app
from app.repositories import OrderRepository
from app.services import OrderService


def fake_user():
    return {"id": 99, "roles": ["customer"]}


def no_rate_limit():
    return None


# a fresh, isolated repo/service per test module so tests don't see each other's orders
_test_repo = OrderRepository()


def fake_order_service():
    return OrderService(_test_repo)


app.dependency_overrides[get_current_user] = fake_user
app.dependency_overrides[rate_limit] = no_rate_limit
app.dependency_overrides[get_order_service] = fake_order_service

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_create_order_success():
    resp = client.post(
        "/orders",
        json={"customer_id": 1, "items": [{"sku": "A", "qty": 2, "price": 9.99}]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "CREATED"
    assert body["total"] == 19.98
    assert body["id"].startswith("ORD-")


def test_create_order_rejects_empty_items():
    resp = client.post("/orders", json={"customer_id": 1, "items": []})
    assert resp.status_code == 422
    assert "item" in resp.json()["error"]


def test_create_order_rejects_invalid_qty():
    # Pydantic-level validation (qty must be > 0) -- FastAPI returns its own 422 shape here,
    # distinct from our ValidationError handler which fires only past Pydantic parsing.
    resp = client.post(
        "/orders",
        json={"customer_id": 1, "items": [{"sku": "A", "qty": 0, "price": 9.99}]},
    )
    assert resp.status_code == 422


def test_get_order_not_found_returns_404():
    resp = client.get("/orders/ORD-does-not-exist")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]


def test_get_order_round_trip():
    created = client.post(
        "/orders",
        json={"customer_id": 2, "items": [{"sku": "B", "qty": 1, "price": 50}]},
    ).json()

    fetched = client.get(f"/orders/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_auth_rejects_wrong_token():
    # Temporarily remove the override to prove the real auth dependency works.
    # Note: an OMITTED Authorization header fails FastAPI's own request validation (422),
    # before our code ever runs -- Header(...) marks it as a required request parameter.
    # A PRESENT-but-wrong header is what actually reaches get_current_user's 401 check.
    del app.dependency_overrides[get_current_user]
    try:
        resp = client.post(
            "/orders",
            json={"customer_id": 1, "items": [{"sku": "A", "qty": 1, "price": 10}]},
            headers={"Authorization": "Bearer wrong-token"},
        )
        assert resp.status_code == 401
    finally:
        app.dependency_overrides[get_current_user] = fake_user  # restore for other tests
