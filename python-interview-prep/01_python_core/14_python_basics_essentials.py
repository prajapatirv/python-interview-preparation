"""
Python basics that still get asked at senior level, because the wrong answer causes real bugs:
`is` vs `==`, how argument passing actually works, truthiness, shallow vs deep copy, `*args`/
`**kwargs`, unpacking, f-strings, sorting with a key, string immutability, and type hints.

None of this is "beginner" trivia in an interview -- every item below has a production failure
attached to it, and the failure is what you should be able to name.

Run me: python 14_python_basics_essentials.py
"""
import copy
import sys
from dataclasses import dataclass, field


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- is vs ==
section("`is` vs `==`: identity vs equality -- and why `is` sometimes LOOKS right")

a = [1, 2, 3]
b = [1, 2, 3]
c = a
print(f"  a == b -> {a == b}   (same contents: __eq__)")
print(f"  a is b -> {a is b}   (different objects: different id())")
print(f"  a is c -> {a is c}   (c is just another name for the same list)")

small_x, small_y = 256, 256
big_x, big_y = 1000, 1000
print(f"  256 is 256   -> {small_x is small_y}   (CPython caches -5..256 -- an implementation detail)")
print(f"  1000 is 1000 -> {big_x is big_y}  (two separate objects here; do NOT depend on either result)")
print("  use `is` ONLY for None, True, False and sentinels. Everything else: `==`.")

MISSING = object()          # the standard sentinel idiom: unique, falsy-free, cheap


def fetch(value=MISSING):
    """Distinguishes 'not supplied' from 'supplied as None' -- impossible with None as default."""
    return "nothing was passed" if value is MISSING else f"got {value!r}"


print(f"  fetch()      -> {fetch()}")
print(f"  fetch(None)  -> {fetch(None)}")


# ---------------------------------------------------------------- argument passing
section("Python is neither pass-by-value nor pass-by-reference: it's pass-by-OBJECT-REFERENCE")


def try_to_rebind(items, number):
    items = ["rebound"]     # rebinds the LOCAL name only -- caller sees nothing
    number = 999
    return items, number


def mutate_in_place(items):
    items.append("appended")   # mutates the SAME object the caller holds


orig_list, orig_num = ["a"], 1
try_to_rebind(orig_list, orig_num)
print(f"  after try_to_rebind: {orig_list}, {orig_num}   <- unchanged (names were rebound locally)")
mutate_in_place(orig_list)
print(f"  after mutate_in_place: {orig_list}             <- CHANGED (the object was mutated)")
print("  the rule: you can always MUTATE the caller's object; you can never REBIND the caller's name.")
print("  so: never mutate a list/dict argument unless the function name says so (sort_in_place).")


# ---------------------------------------------------------------- the mutable default argument
section("the mutable default argument -- evaluated ONCE, at `def` time")


def broken_append(item, bucket=[]):      # the SAME list on every call, forever
    bucket.append(item)
    return bucket


def correct_append(item, bucket=None):
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket


print(f"  broken_append('a') -> {broken_append('a')}")
print(f"  broken_append('b') -> {broken_append('b')}   <- 'a' leaked in from the previous call")
print(f"  correct_append('a') -> {correct_append('a')}")
print(f"  correct_append('b') -> {correct_append('b')}   <- fresh list each time")
print(f"  the shared default is visible on the function object: {broken_append.__defaults__}")


# ---------------------------------------------------------------- truthiness
section("truthiness: what counts as False, and the bug it causes")

falsy = [None, False, 0, 0.0, "", [], {}, set(), ()]
print(f"  falsy values: {[repr(v) for v in falsy]}")
print(f"  all falsy?    {not any(bool(v) for v in falsy)}")


def apply_discount_buggy(discount=None):
    if not discount:                   # 0 is falsy -> a deliberate 0% discount is silently ignored
        return "no discount applied"
    return f"{discount}% off"


def apply_discount_correct(discount=None):
    if discount is None:               # test for ABSENCE, not for falsiness
        return "no discount applied"
    return f"{discount}% off"


print(f"  buggy  with discount=0 -> {apply_discount_buggy(0)}")
print(f"  correct with discount=0 -> {apply_discount_correct(0)}")
print("  the same bug hits empty strings, empty lists and 0.0. `if x is None` when you mean absent.")


# ---------------------------------------------------------------- shallow vs deep copy
section("shallow vs deep copy: `copy()` copies the container, not what's inside it")

original = {"user": "ravi", "roles": ["admin", "dev"]}
assigned = original                       # not a copy at all -- another name
shallow = original.copy()                 # new dict, SAME inner list object
deep = copy.deepcopy(original)            # new dict, new inner list

shallow["roles"].append("leaked")
print(f"  after mutating shallow['roles']:")
print(f"    original: {original}        <- affected! the list was shared")
print(f"    deep:     {deep}  <- untouched")
print(f"  identity: shallow['roles'] is original['roles'] -> {shallow['roles'] is original['roles']}")
print(f"            deep['roles'] is original['roles']    -> {deep['roles'] is original['roles']}")
print(f"  assigned is original -> {assigned is original}  (`=` never copies anything)")
print("  deepcopy is correct but slow and cycle-aware; for a flat config, {**d} is enough.")


# ---------------------------------------------------------------- *args / **kwargs
section("*args and **kwargs: collecting, forwarding, and keyword-only parameters")


def describe(required, *args, mode="fast", **kwargs):
    return (f"required={required!r} args={args} mode={mode!r} kwargs={kwargs}")


print(f"  {describe(1)}")
print(f"  {describe(1, 2, 3, mode='slow', retries=5, debug=True)}")


def forward_everything(*args, **kwargs):
    """The decorator/wrapper signature: accept anything, pass it straight through unchanged."""
    return describe(*args, **kwargs)      # * and ** UNPACK here (the mirror image of collecting)


print(f"  forwarded: {forward_everything(1, 2, mode='slow')}")


def strict(a, b, /, c, *, d):
    """`/` ends positional-ONLY params; `*` starts keyword-ONLY ones. c can be given either way."""
    return a + b + c + d


print(f"  strict(1, 2, 3, d=4) -> {strict(1, 2, 3, d=4)}")
for call, kwargs in [("strict(a=1, b=2, c=3, d=4)", {"a": 1, "b": 2, "c": 3, "d": 4}),
                     ("strict(1, 2, 3, 4)", None)]:
    try:
        strict(**kwargs) if kwargs else strict(1, 2, 3, 4)
    except TypeError as e:
        print(f"  {call} -> TypeError: {e}")
print("  keyword-only params are how you keep a public API changeable without breaking callers.")


# ---------------------------------------------------------------- unpacking
section("unpacking: tuple, starred, nested, dict merge, and swapping")

first, *middle, last = [1, 2, 3, 4, 5]
print(f"  first={first} middle={middle} last={last}")

(name, (host, port)) = ("db", ("localhost", 5432))
print(f"  nested: name={name} host={host} port={port}")

x, y = 1, 2
x, y = y, x                               # no temp variable; the right side is a tuple first
print(f"  swapped: x={x} y={y}")

defaults = {"retries": 3, "timeout": 5}
override = {"timeout": 30}
merged = {**defaults, **override}         # later keys win
print(f"  merged with ** (later wins): {merged}")
print(f"  3.9+ operator form:  defaults | override       -> {defaults | override}")

head, *tail = "abcdef"
print(f"  works on any iterable: head={head!r} tail={tail}")


# ---------------------------------------------------------------- strings
section("strings are immutable -- which is why += in a loop is the classic performance bug")

s = "hello"
try:
    s[0] = "H"
except TypeError as e:
    print(f"  s[0] = 'H' -> TypeError: {e}")
print(f"  every 'change' makes a NEW string: {s.replace('h', 'H')} (s is still {s!r})")

parts = [f"row-{i}" for i in range(5)]
slow = ""
for p in parts:
    slow += p + ","                       # O(n^2): a fresh string object per iteration
fast = ",".join(parts) + ","              # O(n): one allocation
print(f"  += in a loop and ''.join() give the same result: {slow == fast}")
print("  on 100k rows, join() is the difference between milliseconds and tens of seconds.")

amount, label, rate = 1234.5678, "total", 0.0825
print(f"  f-string formatting: {amount:,.2f} | {label:>10} | {label!r} | {rate:.2%} | {255:#x}")
print(f"  the f-string `=` debug form: {amount=}")


# ---------------------------------------------------------------- sorting
section("sorting: key functions, stability, and sorted() vs list.sort()")

orders = [
    {"id": 3, "customer": "bea", "total": 50},
    {"id": 1, "customer": "al", "total": 50},
    {"id": 2, "customer": "cy", "total": 120},
]
by_total_then_id = sorted(orders, key=lambda o: (-o["total"], o["id"]))
print(f"  total DESC then id ASC: {[o['id'] for o in by_total_then_id]}")
print("  a tuple key sorts by each element in turn; negate a number to flip just that one field.")
print(f"  sorted() returns a NEW list ({type(sorted([2, 1])).__name__}); "
      f"list.sort() returns {[2, 1].sort()} and mutates in place.")
print("  Python's sort is STABLE: equal keys keep their original relative order, which is what "
      "lets you sort by secondary key first and then by primary.")


# ---------------------------------------------------------------- loop idioms
section("loop idioms: enumerate, zip, dict.items(), and the for/else clause")

names = ["alice", "bob", "carol"]
scores = [90, 85]
for i, n in enumerate(names, start=1):
    print(f"  {i}. {n}")
print(f"  zip stops at the SHORTEST input: {list(zip(names, scores))}")
print(f"  zip(strict=True) catches the length mismatch instead of hiding it:")
try:
    list(zip(names, scores, strict=True))
except ValueError as e:
    print(f"    ValueError: {e}")

for n in names:
    if n == "zoe":
        break
else:
    print("  for/else: the `else` runs because the loop finished WITHOUT break (a search miss)")


# ---------------------------------------------------------------- type hints
section("type hints: ignored at runtime, invaluable in review and in CI")


@dataclass
class Order:
    id: int
    customer: str
    items: list[str] = field(default_factory=list)   # field(default_factory=...) = the None idiom
    discount: float | None = None                    # 3.10+ union syntax, replaces Optional[float]

    def total_items(self) -> int:
        return len(self.items)


o = Order(id=1, customer="ravi", items=["widget"])
print(f"  {o}")
print(f"  dataclass gives __init__, __repr__ and __eq__: {o == Order(1, 'ravi', ['widget'])}")

bad = Order(id="not-an-int", customer=42)            # NO runtime error -- hints are not checks
print(f"  wrong types accepted at runtime: id={bad.id!r} customer={bad.customer!r}")
print("  hints are enforced by mypy/pyright in CI, or at the edges by Pydantic (see "
      "05_web_apis_fastapi/). Inside your own code they are documentation a tool can verify.")
print(f"  and they're introspectable: {Order.__annotations__ if hasattr(Order, '__annotations__') else {}}")


# ---------------------------------------------------------------- odds and ends
section("three more that come up")

print(f"  chained comparison reads like maths: {0 <= 5 < 10} (and 5 is evaluated once)")
print(f"  integer division vs float: 7 // 2 = {7 // 2}, 7 / 2 = {7 / 2}, 7 % 2 = {7 % 2}")
print(f"  -7 // 2 = {-7 // 2} (floors toward -inf, unlike Java's -3) and -7 % 2 = {-7 % 2} "
      "(sign follows the divisor)")
print(f"  0.1 + 0.2 == 0.3 -> {0.1 + 0.2 == 0.3} (binary floats; use decimal.Decimal for money)")
print(f"  sys.getsizeof([]) = {sys.getsizeof([])} bytes empty; "
      f"{sys.getsizeof([0] * 1000)} with 1000 ints")


# EXPERIMENT 1: change `MISSING = object()` to `MISSING = None` and watch fetch() lose the ability
# to tell "not passed" from "passed None".
# EXPERIMENT 2: in the shallow-copy section, swap `copy.deepcopy` for `dict(original)` and confirm
# the inner list is shared again.
# EXPERIMENT 3: time the += loop vs join() with 200_000 parts using time.perf_counter(). Report the
# ratio -- that number is the answer to "why does string concatenation matter?".
# EXPERIMENT 4: add `index: int` with no default AFTER `discount: float | None = None` in the Order
# dataclass. Read the TypeError: non-default fields can never follow default ones.

# EXERCISE: write `deep_merge(base: dict, override: dict) -> dict` that recursively merges nested
# dicts (override wins on conflicts) and NEVER mutates either input. Prove it with a test that
# mutates the result and asserts both inputs are unchanged -- that's the shallow-copy trap above,
# as an actual bug you have to avoid.
