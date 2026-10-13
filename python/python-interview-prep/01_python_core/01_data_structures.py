"""
Data structures: list, tuple, dict, set/frozenset + collections module.
Run me: python 01_data_structures.py
"""
from collections import Counter, defaultdict, deque, namedtuple, OrderedDict, ChainMap
import os
import sys


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- list vs tuple
section("list vs tuple")
a_list = [1, 2, 3]
a_tuple = (1, 2, 3)
print("list size:", sys.getsizeof(a_list), "| tuple size:", sys.getsizeof(a_tuple))
# tuples are smaller/faster and hashable *if every element is hashable*
d = {(10, 20): "point"}
print("tuple as dict key works:", d[(10, 20)])
try:
    {[10, 20]: "x"}  # lists are never hashable
except TypeError as e:
    print("list as dict key fails:", e)

# EXPERIMENT: a tuple containing a list is NOT hashable either. Prove it:
mixed = (1, [2, 3])
try:
    hash(mixed)
except TypeError as e:
    print("tuple-with-list not hashable:", e)


# ---------------------------------------------------------------- the mutable default bug
section("classic mutable-default-argument bug")


def bad_append(item, bucket=[]):  # DANGER: same list object reused every call
    bucket.append(item)
    return bucket


def good_append(item, bucket=None):
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket


print("bad_append(1):", bad_append(1))
print("bad_append(2):", bad_append(2))  # [1, 2] <- surprise, same list as before
print("good_append(1):", good_append(1))
print("good_append(2):", good_append(2))  # [2] <- fresh list each time


# ---------------------------------------------------------------- dict essentials
section("dict: insertion order + O(1) average lookup")
scores = {}
scores["ravi"] = 90
scores["asha"] = 85
scores["ravi"] = 95  # overwrite keeps original position
print(list(scores.items()))  # ravi stays first even though its value changed


# ---------------------------------------------------------------- collections.Counter
section("collections.Counter")
words = "a b a c b a d".split()
counts = Counter(words)
print("most_common(2):", counts.most_common(2))
print("anagram check via Counter:", Counter("listen") == Counter("silent"))


# ---------------------------------------------------------------- collections.defaultdict
section("collections.defaultdict")
orders = [("alice", 10), ("bob", 5), ("alice", 7)]
by_user = defaultdict(list)
for user, amt in orders:
    by_user[user].append(amt)
print(dict(by_user))


# ---------------------------------------------------------------- collections.deque
section("collections.deque — O(1) at both ends, fixed-size ring buffer")
last5 = deque(maxlen=5)
for i in range(8):
    last5.append(i)
print("sliding window of last 5:", last5)

q = deque([1, 2])
q.appendleft(0)
q.popleft()
print("deque as a queue:", q)


# ---------------------------------------------------------------- namedtuple
section("collections.namedtuple")
Point = namedtuple("Point", "x y")
p = Point(1, 2)
x, y = p  # unpackable
print("namedtuple:", p, "unpacked:", x, y)


# ---------------------------------------------------------------- OrderedDict for LRU
section("collections.OrderedDict as an LRU cache")


class LRU:
    def __init__(self, capacity):
        self.capacity = capacity
        self.store = OrderedDict()

    def get(self, key):
        if key not in self.store:
            return -1
        self.store.move_to_end(key)
        return self.store[key]

    def put(self, key, value):
        self.store[key] = value
        self.store.move_to_end(key)
        if len(self.store) > self.capacity:
            self.store.popitem(last=False)  # evict least-recently-used


cache = LRU(2)
cache.put("a", 1)
cache.put("b", 2)
cache.get("a")       # "a" is now most-recently-used
cache.put("c", 3)    # evicts "b" (least recently used)
print("LRU after evicting b:", list(cache.store.items()))


# ---------------------------------------------------------------- ChainMap for layered config
section("collections.ChainMap — layered config (CLI > env > defaults)")
defaults = {"env": "dev", "debug": False}
cli_args = {"debug": True}
config = ChainMap(cli_args, os.environ, defaults)
print("debug =", config["debug"], "| env =", config["env"])


# ---------------------------------------------------------------- dedupe preserving order
section("remove duplicates while keeping order")
items = [3, 1, 3, 2, 1]
deduped = list(dict.fromkeys(items))
print("deduped:", deduped)

# EXPERIMENT: try `list(set(items))` instead — order is no longer guaranteed to match input.
