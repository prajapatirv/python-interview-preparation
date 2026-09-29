"""
Cache-aside pattern: check cache -> miss -> load from "DB" -> populate cache -> TTL expiry ->
invalidate on write. Uses a FakeRedis (plain dict + expiry) so it runs with zero dependencies.

To use REAL Redis instead: `pip install redis`, start a local server, and replace
FakeRedis() with `redis.Redis(decode_responses=True)` -- every method below (get/setex/delete)
has the same name and signature as the real redis-py client, on purpose.

Run me: python 01_cache_aside_pattern.py
"""
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


class FakeRedis:
    """Minimal stand-in for redis-py's synchronous client -- just enough to demo cache-aside."""

    def __init__(self):
        self._store: dict[str, tuple[str, float | None]] = {}  # key -> (value, expires_at)

    def get(self, key):
        if key not in self._store:
            return None
        value, expires_at = self._store[key]
        if expires_at is not None and time.time() > expires_at:
            del self._store[key]  # lazy expiry, same as real Redis
            return None
        return value

    def setex(self, key, ttl_seconds, value):
        self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key):
        self._store.pop(key, None)


# ---------------------------------------------------------------- the "database"
FAKE_DB = {
    "order:1": '{"id": 1, "total": 100}',
    "order:2": '{"id": 2, "total": 250}',
}
db_calls = {"count": 0}


def load_from_db(order_id):
    db_calls["count"] += 1
    time.sleep(0.05)  # simulate real DB latency
    return FAKE_DB.get(f"order:{order_id}")


metrics = {"hit": 0, "miss": 0}
cache = FakeRedis()


def get_order(order_id, ttl=5):
    cache_key = f"order:{order_id}"

    cached = cache.get(cache_key)
    if cached is not None:
        metrics["hit"] += 1
        return cached

    metrics["miss"] += 1
    value = load_from_db(order_id)
    if value is not None:
        cache.setex(cache_key, ttl, value)
    return value


def update_order(order_id, new_value):
    FAKE_DB[f"order:{order_id}"] = new_value
    cache.delete(f"order:{order_id}")  # invalidate on write -- next read repopulates the cache


# ---------------------------------------------------------------- demo
section("cache-aside: first read misses, subsequent reads hit")
for _ in range(5):
    get_order(1)
print(f"order:1 read 5 times -> {metrics['hit']} hits, {metrics['miss']} miss, "
      f"{db_calls['count']} real DB call(s)")

section("write invalidates the cache -- next read is a guaranteed fresh miss")
update_order(1, '{"id": 1, "total": 999}')
result = get_order(1)
print(f"after update: {result}  ({db_calls['count']} DB calls total now)")

section("TTL expiry: wait past the TTL, then read again -> miss")
metrics_before = dict(metrics)
cache.setex("order:2", ttl_seconds=1, value=FAKE_DB["order:2"])
time.sleep(1.2)
get_order(2)
print(f"a read after TTL expiry counted as: "
      f"{'a HIT (bug!)' if metrics['hit'] == metrics_before['hit'] + 1 else 'a MISS (correct)'}")

# EXPERIMENT: change ttl=5 to ttl=0.1 in get_order and rerun the first block -- watch db_calls
# climb back up as entries expire mid-loop instead of staying cached for all 5 reads.
