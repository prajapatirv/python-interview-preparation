"""
Problem: design an LRU (Least Recently Used) cache with O(1) get and put.
On overflow, evict the LEAST RECENTLY USED key (not the oldest inserted -- a key that was just
read counts as "recently used" even if it was inserted long ago).

Two implementations:
  1. OrderedDict -- the pragmatic interview answer, leans on stdlib doing the hard part.
  2. dict + hand-rolled doubly linked list -- what OrderedDict does internally; interviewers
     sometimes explicitly ask you to NOT use OrderedDict to see if you understand why it's O(1).

Run me: python 03_lru_cache.py
Run the tests: pytest 03_lru_cache.py -v
"""
from collections import OrderedDict


# ---------------------------------------------------------------- approach 1: OrderedDict
class LRUCacheOrderedDict:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self._store: OrderedDict = OrderedDict()

    def get(self, key):
        if key not in self._store:
            return -1
        self._store.move_to_end(key)  # mark as most-recently-used
        return self._store[key]

    def put(self, key, value):
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        if len(self._store) > self.capacity:
            self._store.popitem(last=False)  # evict least-recently-used (the front)


# ---------------------------------------------------------------- approach 2: from scratch
class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key=None, value=None):
        self.key, self.value = key, value
        self.prev: "_Node | None" = None
        self.next: "_Node | None" = None


class LRUCacheFromScratch:
    """A dict for O(1) key lookup + a doubly linked list for O(1) reordering on access.
    head.next is always the MOST recently used node; tail.prev is always the LEAST."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self._map: dict = {}
        self.head, self.tail = _Node(), _Node()  # sentinels -- avoids null checks at the edges
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: _Node):
        node.prev.next = node.next
        node.next.prev = node.prev

    def _insert_at_front(self, node: _Node):
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key):
        if key not in self._map:
            return -1
        node = self._map[key]
        self._remove(node)
        self._insert_at_front(node)
        return node.value

    def put(self, key, value):
        if key in self._map:
            self._remove(self._map[key])

        node = _Node(key, value)
        self._map[key] = node
        self._insert_at_front(node)

        if len(self._map) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self._map[lru.key]


if __name__ == "__main__":
    for name, Cls in [("OrderedDict", LRUCacheOrderedDict), ("from-scratch", LRUCacheFromScratch)]:
        cache = Cls(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")       # "a" is now most-recently-used
        cache.put("c", 3)    # capacity=2 -> evicts "b" (the least recently used)
        print(f"{name:14s}: get('a')={cache.get('a')} get('b')={cache.get('b')} get('c')={cache.get('c')}")


# ---------------------------------------------------------------- tests, run against BOTH implementations
# (no `import pytest` here on purpose -- keeps `python 03_lru_cache.py` runnable with zero
# dependencies; pytest can still discover and run plain `test_*` functions with no special import)
IMPLEMENTATIONS = [LRUCacheOrderedDict, LRUCacheFromScratch]


def test_basic_get_put():
    for Cls in IMPLEMENTATIONS:
        cache = Cls(2)
        cache.put(1, "one")
        cache.put(2, "two")
        assert cache.get(1) == "one", f"{Cls.__name__} failed"
        assert cache.get(3) == -1, f"{Cls.__name__} failed"


def test_eviction_order():
    for Cls in IMPLEMENTATIONS:
        cache = Cls(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.get("a")          # touching "a" makes "b" the least-recently-used
        cache.put("c", 3)       # should evict "b", not "a"
        assert cache.get("a") == 1, f"{Cls.__name__} failed"
        assert cache.get("b") == -1, f"{Cls.__name__} failed"
        assert cache.get("c") == 3, f"{Cls.__name__} failed"


def test_put_existing_key_updates_value_and_recency():
    for Cls in IMPLEMENTATIONS:
        cache = Cls(2)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("a", 100)     # update, and "a" becomes most-recently-used again
        cache.put("c", 3)       # should evict "b"
        assert cache.get("a") == 100, f"{Cls.__name__} failed"
        assert cache.get("b") == -1, f"{Cls.__name__} failed"
