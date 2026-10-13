"""
map / filter / reduce — the functional trio, and why Python usually prefers comprehensions.

If you're coming from Java Streams, this is the file that retrains the reflex:
    stream().map(f).filter(p).collect(toList())   ->   [f(x) for x in xs if p(x)]

Run me: python 10_map_filter_reduce.py
Deep dive: ../deep_dive/02_comprehensions_map_filter_reduce.md
"""
import operator
import sys
import timeit
from functools import reduce


def section(title):
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


# ---------------------------------------------------------------- laziness
section("map/filter are LAZY ITERATORS in Python 3 (they were lists in Python 2)")
nums = [1, 2, 3, 4, 5]

squares = map(lambda x: x * x, nums)
evens = filter(lambda x: x % 2 == 0, nums)

print("map object:", squares)                  # <map object ...> — nothing computed yet
print("filter object:", evens)
print("materialised:", list(squares), list(evens))

# THE CLASSIC BUG: an iterator is single-pass
squares = map(lambda x: x * x, nums)
print("first  list():", list(squares))
print("second list():", list(squares), "  <- EXHAUSTED, silently empty")
# EXPERIMENT: wrap the map in list() immediately and confirm the second call works.


# ---------------------------------------------------------------- equivalences
section("map/filter vs comprehension — the exact equivalences")
print("map(f, xs)            ==", list(map(str.upper, ["a", "b"])),
      "==", [s.upper() for s in ["a", "b"]])
print("filter(p, xs)         ==", list(filter(lambda n: n > 2, nums)),
      "==", [n for n in nums if n > 2])
print("map(f, filter(p, xs)) ==", list(map(lambda n: n * 10, filter(lambda n: n > 2, nums))),
      "==", [n * 10 for n in nums if n > 2])

# filter(None, xs) is a special form: drops FALSY values
mixed = [1, 0, "a", "", None, 3, [], [0]]
print("filter(None, mixed):", list(filter(None, mixed)))
# EXPERIMENT: note that [0] survives (a non-empty list is truthy) but [] does not.

# map over MULTIPLE iterables zips them
print("map with 2 iterables:", list(map(operator.add, [1, 2, 3], [10, 20, 30])))


# ---------------------------------------------------------------- when map actually wins
section("when map beats a comprehension: an existing named function (no lambda)")
raw = ["1", "2", "3"]

# map wins here — int is a C-level builtin, no Python-level call per item
print("map(int, raw)      :", list(map(int, raw)))
print("comprehension      :", [int(s) for s in raw])

t_map = timeit.timeit("list(map(int, raw))", globals={"raw": raw}, number=200_000)
t_comp = timeit.timeit("[int(s) for s in raw]", globals={"raw": raw}, number=200_000)
print(f"map with a builtin  : {t_map:.4f}s")
print(f"comprehension       : {t_comp:.4f}s   (map usually wins here)")

# ...but with a lambda, map LOSES — the lambda adds a Python call per item
t_map_l = timeit.timeit("list(map(lambda x: x * 2, nums))", globals={"nums": nums}, number=200_000)
t_comp_l = timeit.timeit("[x * 2 for x in nums]", globals={"nums": nums}, number=200_000)
print(f"map with a lambda   : {t_map_l:.4f}s")
print(f"comprehension       : {t_comp_l:.4f}s   (comprehension wins here)")
# RULE OF THUMB: named function -> map is fine and fast.
#                needs a lambda -> use a comprehension.


# ---------------------------------------------------------------- reduce
section("reduce — in functools, NOT a builtin, and usually the wrong tool")
values = [1, 2, 3, 4]

print("reduce(add)       :", reduce(operator.add, values))
print("reduce(mul)       :", reduce(operator.mul, values))
print("reduce with init  :", reduce(operator.add, values, 100))

# ALWAYS pass `initial` if the input can be empty
try:
    reduce(operator.add, [])
except TypeError as e:
    print("reduce([]) with no initial ->", e)
print("reduce([], 0)     :", reduce(operator.add, [], 0), " <- safe")

# Guido moved reduce out of builtins in Python 3 because nearly every real use
# is already a builtin, and the rest are unreadable.
import math
print("\nreduce(add)  -> use sum()      :", sum(values))
print("reduce(mul)  -> use math.prod():", math.prod(values))
print("reduce(max)  -> use max()      :", max(values))
print("reduce(and_) -> use all()      :", all(values))


# ---------------------------------------------------------------- the reduce TRAP
section("the reduce trap: reduce(+) on lists is QUADRATIC")
nested = [[i] for i in range(200)]

flat_reduce = reduce(operator.add, nested, [])      # allocates a NEW list every step -> O(n^2)
flat_comp = [x for sub in nested for x in sub]      # O(n)
print("same result:", flat_reduce == flat_comp)

t_red = timeit.timeit("reduce(operator.add, nested, [])",
                      globals={"reduce": reduce, "operator": operator, "nested": nested},
                      number=300)
t_cmp = timeit.timeit("[x for sub in nested for x in sub]",
                      globals={"nested": nested}, number=300)
print(f"reduce(+) flatten : {t_red:.4f}s   <- O(n^2), a new list each step")
print(f"comprehension     : {t_cmp:.4f}s   <- O(n)")
# EXPERIMENT: change range(200) to range(2000) and watch the gap widen ~100x, not ~10x.


# ---------------------------------------------------------------- when reduce is right
section("when reduce IS the right tool: a custom, non-builtin fold")

# Merge a list of config dicts, later ones winning
configs = [{"a": 1}, {"b": 2}, {"a": 9}]
merged = reduce(lambda acc, d: {**acc, **d}, configs, {})
print("merged configs:", merged)

# Walk a nested structure by a path
data = {"user": {"address": {"city": "Pune"}}}
dig = lambda obj, key: obj.get(key) if isinstance(obj, dict) else None
print("dig path:", reduce(dig, ["user", "address", "city"], data))
# ...even here, a 3-line for-loop is defensible. Know reduce; reach for it rarely.


# ---------------------------------------------------------------- operator module
section("operator — operators as C functions, so you can skip the lambda")
rows = [{"name": "bob", "age": 30}, {"name": "amy", "age": 25}, {"name": "cid", "age": 30}]

print("sort by age      :", sorted(rows, key=operator.itemgetter("age")))
# itemgetter with several keys returns a tuple -> multi-column sort for free
print("sort age,name    :", sorted(rows, key=operator.itemgetter("age", "name")))


class P:
    def __init__(self, n): self.n = n
    def __repr__(self): return f"P({self.n})"


print("sort by attribute:", sorted([P(3), P(1), P(2)], key=operator.attrgetter("n")))
print("methodcaller     :", list(map(operator.methodcaller("upper"), ["a", "b"])))


# ---------------------------------------------------------------- the pipeline comparison
section("a real pipeline, three ways — this is the interview answer")
orders = [
    {"id": 1, "amount": 250, "status": "PAID"},
    {"id": 2, "amount": 90, "status": "FAILED"},
    {"id": 3, "amount": 410, "status": "PAID"},
]

# 1. Functional — reads INSIDE-OUT, which is why it loses idiomatically
total_fn = reduce(
    operator.add,
    map(lambda o: o["amount"], filter(lambda o: o["status"] == "PAID", orders)),
    0,
)

# 2. Generator expression fed to a builtin — lazy, O(1) memory, reads LEFT-TO-RIGHT
total_gen = sum(o["amount"] for o in orders if o["status"] == "PAID")

# 3. Explicit loop — most readable when the logic grows
total_loop = 0
for o in orders:
    if o["status"] == "PAID":
        total_loop += o["amount"]

print(f"functional : {total_fn}")
print(f"generator  : {total_gen}   <- the idiomatic Python spelling")
print(f"loop       : {total_loop}")


# ---------------------------------------------------------------- memory
section("generator expression vs list comprehension — memory")
lst = [i * i for i in range(100_000)]
gen = (i * i for i in range(100_000))
print(f"list comprehension : {sys.getsizeof(lst):>9,} bytes")
print(f"generator expression: {sys.getsizeof(gen):>8,} bytes  <- O(1), regardless of size")
# EXPERIMENT: raise to 10_000_000. The list grows linearly; the generator stays flat.


# ---------------------------------------------------------------- Java Streams mapping
section("Java Streams -> Python cheat sheet")
table = [
    (".map(f)",                       "[f(x) for x in xs]"),
    (".filter(p)",                    "[x for x in xs if p(x)]"),
    (".mapToInt(f).sum()",            "sum(f(x) for x in xs)"),
    (".anyMatch(p) / .allMatch(p)",   "any(...) / all(...)"),
    (".sorted(comparing(X::getY))",   "sorted(xs, key=attrgetter('y'))"),
    (".distinct()",                   "set(xs)  /  list(dict.fromkeys(xs))"),
    (".limit(n)",                     "xs[:n]  /  islice(gen, n)"),
    (".flatMap(...)",                 "[y for x in xs for y in x]"),
    (".reduce(id, f)",                "reduce(f, xs, id)  -- prefer sum/max/prod"),
    ("Collectors.groupingBy(f)",      "defaultdict(list) loop"),
    ("Collectors.joining(', ')",      "', '.join(strings)"),
    (".parallelStream()",             "concurrent.futures -- NO free parallelism (GIL)"),
]
for java, python in table:
    print(f"  {java:<32} ->  {python}")


# EXERCISE 1: rewrite `reduce(lambda a, b: a if a['amount'] > b['amount'] else b, orders)`
#             using a builtin. (Hint: max with a key.)
# EXERCISE 2: `filter(None, xs)` drops falsy values. Write the comprehension equivalent,
#             then explain why `filter(bool, xs)` is the same thing.
# EXERCISE 3: implement Collectors.groupingBy(Order::getStatus) three ways — a plain loop,
#             defaultdict(list), and itertools.groupby — and say why groupby needs a sort first.
