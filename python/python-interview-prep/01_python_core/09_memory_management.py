"""
Memory management: reference counting, the cyclic GC, weakref, __slots__, and tracemalloc.
Run me: python 09_memory_management.py
"""
import gc
import sys
import tracemalloc
import weakref


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- reference counting
section("reference counting — objects are freed the instant refcount hits 0")
a = []
print("refcount right after creation (includes the getrefcount arg itself):", sys.getrefcount(a))
b = a
print("refcount after `b = a`:", sys.getrefcount(a))
del b
print("refcount after `del b`:", sys.getrefcount(a))


# ---------------------------------------------------------------- reference cycles need the GC
section("reference cycles — refcounting alone can't free these; the cyclic GC can")


class Node:
    def __init__(self, name):
        self.name = name
        self.other = None

    def __repr__(self):
        return f"Node({self.name})"


n1, n2 = Node("n1"), Node("n2")
n1.other = n2
n2.other = n1  # cycle: n1 -> n2 -> n1
del n1, n2  # refcount never hits 0 because they still reference each other
collected = gc.collect()  # the generational cyclic collector finds and frees the cycle
print(f"gc.collect() freed {collected} unreachable objects")


# ---------------------------------------------------------------- weakref avoids cache leaks
section("weakref.WeakValueDictionary — cache entries that don't keep values alive")


class Cache:
    def __init__(self):
        self._store = weakref.WeakValueDictionary()

    def put(self, key, value):
        self._store[key] = value

    def get(self, key):
        return self._store.get(key)


class BigObject:
    def __init__(self, name):
        self.name = name


cache = Cache()
obj = BigObject("payload")
cache.put("k1", obj)
print("cached before del:", cache.get("k1"))
del obj  # no other strong reference exists -> weakref-backed cache entry disappears too
print("cached after del (GC'd, not a leak):", cache.get("k1"))


# ---------------------------------------------------------------- __slots__ memory saving
section("__slots__ — trade dynamic attributes for ~40% less memory per instance")


class WithDict:
    def __init__(self, x, y):
        self.x, self.y = x, y


class WithSlots:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y


wd, ws = WithDict(1, 2), WithSlots(1, 2)
print("WithDict instance dict:", wd.__dict__)
try:
    ws.z = 3  # no __dict__ to fall back on
except AttributeError as e:
    print("WithSlots rejects new attributes:", e)

# EXPERIMENT: create 1,000,000 of each with a list comprehension and compare with
# tracemalloc (see below) or `sys.getsizeof` on a sample instance.


# ---------------------------------------------------------------- tracemalloc: find what's allocating memory
section("tracemalloc — find the top memory-allocating lines")
tracemalloc.start()

_ = [str(i) * 50 for i in range(50_000)]  # deliberately wasteful allocation

snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics("lineno")
print("top 3 allocations by line:")
for stat in top_stats[:3]:
    print(" ", stat)

tracemalloc.stop()

# EXERCISE: wrap the WithDict/WithSlots comparison above in tracemalloc.start()/stop() and
# report the actual byte difference for 100,000 instances of each.
