"""Shared Depends() providers: a singleton-ish repo/service, current-user auth, and a simple
in-process rate limiter dependency. Each is designed to be overridden in tests via
app.dependency_overrides (see tests/test_orders_api.py)."""
import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from app.config import get_settings
from app.repositories import OrderRepository
from app.services import OrderService

# A single in-memory repo shared across requests for this demo process. In a real app this would
# be `Depends(get_db_session)` yielding a per-request DB session instead.
_repo = OrderRepository()


def get_order_service() -> OrderService:
    return OrderService(_repo)


def get_current_user(authorization: str = Header(...)) -> dict:
    """Authentication: proves WHO is calling. Failure -> 401."""
    settings = get_settings()
    if authorization != f"Bearer {settings.demo_token}":
        raise HTTPException(status_code=401, detail="invalid or missing token")
    return {"id": 1, "roles": ["customer"]}


def require_admin(user: Annotated[dict, Depends(get_current_user)]) -> dict:
    """Authorization: checks WHAT an already-identified caller may do. Failure -> 403.
    Depends on get_current_user (authentication) first -- authorization is always the SECOND
    question, asked only once identity is known. This demo user is never an admin, so calling
    an endpoint that depends on this always 403s; wire in real roles for the README exercise."""
    if "admin" not in user["roles"]:
        raise HTTPException(status_code=403, detail="admin role required")
    return user


# --- simple in-process rate limiter dependency (sliding window) -----------------------------
_windows: dict[str, list[float]] = defaultdict(list)


def rate_limit(request: Request) -> None:
    settings = get_settings()
    key = request.client.host if request.client else "unknown"
    now = time.time()
    window = _windows[key] = [t for t in _windows[key] if now - t < 60]
    if len(window) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    window.append(now)
