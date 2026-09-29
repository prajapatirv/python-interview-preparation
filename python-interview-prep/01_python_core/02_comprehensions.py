"""
Comprehensions: list/set/dict/generator forms, nesting, scope, and the lambda-in-loop trap.
Run me: python 02_comprehensions.py
"""
import sys


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- the four forms
section("the four comprehension forms")
nums = range(6)
print("list:", [n * n for n in nums])
print("set:", {n % 3 for n in nums})
print("dict:", {n: n * n for n in nums if n % 2})
print("generator (lazy, no list built):", sum(n * n for n in nums))


# ---------------------------------------------------------------- memory: list vs generator
section("list comprehension vs generator expression — memory")
lst = [i for i in range(1_000_000)]
gen = (i for i in range(1_000_000))
print(f"list size ~{sys.getsizeof(lst):,} bytes | generator size ~{sys.getsizeof(gen)} bytes")
# EXPERIMENT: bump range to 10_000_000 and watch the list size grow linearly while the
# generator's stays flat.


# ---------------------------------------------------------------- nested comprehensions
section("nested comprehensions — read left-to-right like nested for-loops")
matrix = [[1, 2, 3], [4, 5, 6]]
flat = [x for row in matrix for x in row]
transposed = [[row[i] for row in matrix] for i in range(3)]
print("flat:", flat)
print("transposed:", transposed)


# ---------------------------------------------------------------- filter vs transform
section("filtering `if` (after for) vs transforming `if/else` (before for)")
values = [1, 2, 3, 4, 5]
evens = [n for n in values if n % 2 == 0]                       # filter
labels = ["even" if n % 2 == 0 else "odd" for n in values]      # transform
print("evens:", evens)
print("labels:", labels)


# ---------------------------------------------------------------- scope: loop var doesn't leak
section("comprehension scope — the loop variable does NOT leak (Python 3)")
x = "outer"
squares = [x * x for x in range(3)]
print("x after comprehension:", x)  # still "outer"

# but the walrus operator := is a DELIBERATE exception — it binds in the enclosing scope
data = [3, 8, 1]
if any((big := n) > 5 for n in data):
    print("walrus leaks on purpose, big =", big)


# ---------------------------------------------------------------- the late-binding closure trap
section("classic bug: lambdas in a loop all capture the FINAL loop value")
broken = [lambda: i for i in range(3)]
print("broken (all see final i):", [f() for f in broken])

fixed = [lambda i=i: i for i in range(3)]  # default arg captures the value NOW
print("fixed (captures value at creation):", [f() for f in fixed])


# ---------------------------------------------------------------- comprehension + error handling
section("comprehensions can't hold try/except — wrap the risky call in a helper")


def to_int(s):
    try:
        return int(s)
    except ValueError:
        return None


raw = ["1", "x", "3"]
parsed = [n for s in raw if (n := to_int(s)) is not None]
print("safely parsed ints, bad ones dropped:", parsed)


# EXERCISE: write a comprehension that inverts {"a": 1, "b": 2, "c": 1} and explain out loud
# why the result has only 2 keys, and which original key "wins" for the duplicate value 1.
