"""Who is calling, and may they review?

- **Local mode** (no ``SUPABASE_URL``): one user, ``local``, who is also the reviewer.
- **Supabase mode**: the browser sends the Supabase Auth access token as ``Authorization: Bearer``; it is
  verified by asking Supabase (``GET /auth/v1/user``), so it works with any JWT signing scheme and needs no
  secret on our side. Results are cached for 60 s. A user is a reviewer when ``app_metadata.role ==
  "reviewer"`` or their id / email is in ``COACH_REVIEWERS``.
"""
import time
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, Request

from .. import config
from .store import LOCAL_USER

_cache: dict[str, tuple[float, "User"]] = {}
TTL = 60.0


@dataclass(frozen=True)
class User:
    id: str
    role: str = "learner"          # learner | reviewer

    @property
    def is_reviewer(self) -> bool:
        return self.role == "reviewer"


def _verify(token: str) -> User | None:
    hit = _cache.get(token)
    if hit and hit[0] > time.time():
        return hit[1]
    try:
        r = httpx.get(config.SUPABASE_URL.rstrip("/") + "/auth/v1/user", timeout=10,
                      headers={"apikey": config.SUPABASE_ANON_KEY or config.SUPABASE_SERVICE_KEY,
                               "Authorization": f"Bearer {token}"})
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    d = r.json()
    reviewer = (d.get("app_metadata") or {}).get("role") == "reviewer" or \
        d.get("id") in config.REVIEWERS or (d.get("email") or "").lower() in config.REVIEWERS
    user = User(d["id"], "reviewer" if reviewer else "learner")
    _cache[token] = (time.time() + TTL, user)
    return user


def current_user(request: Request) -> User:
    """FastAPI dependency."""
    if not config.SUPABASE_URL:
        return User(LOCAL_USER, "reviewer")
    header = request.headers.get("authorization", "")
    user = _verify(header[7:]) if header.lower().startswith("bearer ") else None
    if user is None:
        raise HTTPException(401, "sign in required")
    return user
