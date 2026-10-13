"""
Cache stampede (thundering herd): many concurrent requests miss at the same instant and all
hammer the "DB" at once. Reproduce it, then fix it with a SET-NX-style distributed lock so only
ONE requester rebuilds the cache while the rest wait briefly and retry.

Run me: python 02_cache_stampede_lock.py
"""
import threading
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


class FakeRedis:
    def __init__(self):
        self._store = {}
        self._lock = threading.Lock()  # protects the dict itself, not the app-level cache lock

    def get(self, key):
        with self._lock:
            return self._store.get(key)

    def setex(self, key, ttl_seconds, value):
        with self._lock:
            self._store[key] = value  # ttl omitted for brevity in this demo

    def set_nx(self, key, value, ttl_seconds):
        """Atomic 'set only if not exists' -- the real primitive behind a Redis-based lock."""
        with self._lock:
            if key in self._store:
                return False
            self._store[key] = value
            return True

    def delete(self, key):
        with self._lock:
            self._store.pop(key, None)


db_calls = {"count": 0}
db_call_lock = threading.Lock()


def expensive_db_load(key):
    with db_call_lock:
        db_calls["count"] += 1
    time.sleep(0.2)  # a genuinely slow query
    return f"value-for-{key}"


# ---------------------------------------------------------------- BROKEN: naive cache-aside
def get_naive(cache, key):
    value = cache.get(key)
    if value is not None:
        return value
    value = expensive_db_load(key)
    cache.setex(key, 10, value)
    return value


section("stampede: 20 threads all miss the SAME key at the same instant")
cache = FakeRedis()
db_calls["count"] = 0
threads = [threading.Thread(target=get_naive, args=(cache, "hot_key")) for _ in range(20)]
[t.start() for t in threads]
[t.join() for t in threads]
print(f"naive cache-aside under a stampede: {db_calls['count']} DB calls "
      f"(should be 1, is actually ~20 -- every thread missed before any of them wrote the cache)")


# ---------------------------------------------------------------- FIXED: SET-NX lock
def get_with_lock(cache, key, max_wait=1.0):
    value = cache.get(key)
    if value is not None:
        return value

    lock_key = f"lock:{key}"
    acquired = cache.set_nx(lock_key, "1", ttl_seconds=10)

    if acquired:
        try:
            value = expensive_db_load(key)
            cache.setex(key, 10, value)
            return value
        finally:
            cache.delete(lock_key)
    else:
        # another thread is already rebuilding this key -- wait briefly and retry the read
        deadline = time.time() + max_wait
        while time.time() < deadline:
            value = cache.get(key)
            if value is not None:
                return value
            time.sleep(0.01)
        return expensive_db_load(key)  # fallback: rebuilder took too long, do it ourselves


section("fixed: 20 threads, same key, but only ONE actually hits the DB")
cache2 = FakeRedis()
db_calls["count"] = 0
threads = [threading.Thread(target=get_with_lock, args=(cache2, "hot_key")) for _ in range(20)]
[t.start() for t in threads]
[t.join() for t in threads]
print(f"lock-protected cache-aside under a stampede: {db_calls['count']} DB call(s) (should be 1)")

# EXPERIMENT: lower max_wait to 0.01 in get_with_lock and rerun -- some threads will time out
# waiting for the rebuilder and fall back to their own DB call, creeping db_calls back up above 1.
# That's the real trade-off between "wait longer" and "risk a second DB hit."
