"""
Java -> Python bridge: the same concepts, the different syntax, and the traps.

You already know inheritance, interfaces, threads and streams. This file is about
the places where a Java HABIT produces Python that runs but is wrong.

Run me: python 11_java_to_python_bridge.py
Deep dive: ../deep_dive/21_java_to_python_bridge.md
"""
import copy
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import singledispatch
from typing import Protocol


def section(title):
    print(f"\n{'=' * 68}\n{title}\n{'=' * 68}")


# ================================================================= TRAP 1
section("TRAP 1: mutable default arguments are evaluated ONCE, at def time")


def add_bad(item, bucket=[]):          # BAD — one list shared by every call
    bucket.append(item)
    return bucket


def add_good(item, bucket=None):       # GOOD — None sentinel
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket


print("add_bad(1) ->", add_bad(1))
print("add_bad(2) ->", add_bad(2), "  <- the SAME list; Java would give a fresh one")
print("you can see it on the function object:", add_bad.__defaults__)
print("add_good(1) ->", add_good(1))
print("add_good(2) ->", add_good(2), "  <- correct")
# EXPERIMENT: add a third call to add_bad and watch the list keep growing.


# ================================================================= TRAP 2
section("TRAP 2: `is` vs `==` — same trap as Java's Integer cache")
# Build the values at RUNTIME so the compiler can't constant-fold them into one object.
# (Writing `a, b = 257, 257` on one line folds to a single object and hides the effect.)
a, b = int("256"), int("256")
print(f"256 is 256 -> {str(a is b):<5}  (CPython pre-caches -5..256, so these are one object)")
a, b = int("257"), int("257")
print(f"257 is 257 -> {str(a is b):<5}  (outside the cache: two distinct objects)")
print(f"257 == 257 -> {str(a == b):<5}  <- this is what you meant")
print("use `is` ONLY for None / True / False / sentinels; `==` for everything else")


# ================================================================= TRAP 3
section("TRAP 3: truthiness — 0 and '' are falsy, which breaks the `or` default idiom")
user_timeout = 0                        # a perfectly valid value!
print("user_timeout or 30 ->", user_timeout or 30, "  <- WRONG, silently became 30")
print("explicit None check ->", 30 if user_timeout is None else user_timeout, "  <- correct")

for value in ([], {}, "", 0, 0.0, None, [0], "0"):
    print(f"  bool({value!r:>6}) = {bool(value)}")
# EXPERIMENT: note [0] and "0" are TRUTHY — non-empty containers always are.


# ================================================================= TRAP 4
section("TRAP 4: assignment binds a NAME to an object; there is no value copying")
original = [[1, 2], [3, 4]]
alias = original                        # two names, ONE object
shallow = original.copy()               # new outer list, SHARED inner lists
deep = copy.deepcopy(original)          # fully independent

original[0].append(99)
print("original:", original)
print("alias   :", alias, "   <- same object")
print("shallow :", shallow, "   <- inner list was shared")
print("deep    :", deep, "        <- independent")


# ================================================================= TRAP 5
section("TRAP 5: no method overloading — the last definition silently WINS")


class Calculator:
    def area(self, w):
        return w * w

    def area(self, w, h):               # noqa: F811 — silently replaces the one above
        return w * h


try:
    Calculator().area(5)
except TypeError as e:
    print("Calculator().area(5) ->", e)
print("Calculator().area(5, 3) ->", Calculator().area(5, 3))

# The Python answers: default args, *args, or singledispatch


@singledispatch
def describe(value):
    return f"unknown: {value!r}"


@describe.register
def _(value: int):
    return f"int {value}"


@describe.register
def _(value: list):
    return f"list of {len(value)}"


print("singledispatch:", describe(5), "|", describe([1, 2]), "|", describe(3.3))


# ================================================================= TRAP 6
section("TRAP 6: late-binding closures — Java forbids this; Python allows it")
fns = [lambda: i for i in range(3)]
print("lambda: i        ->", [f() for f in fns], "  <- all see the FINAL i")
fns = [lambda i=i: i for i in range(3)]
print("lambda i=i: i    ->", [f() for f in fns], "  <- bound at definition time")


# ================================================================= TRAP 7
section("TRAP 7: type hints are NOT enforced at runtime")


def charge(amount: float) -> bool:
    return True


print("charge('not a number') ->", charge("not a number"), "  <- no error!")
print("hints are for mypy and for readers. Run mypy in CI, or they rot into lies.")


# ================================================================= OOP
section("OOP: Java bean -> Pythonic class")


class OrderJavaStyle:
    """The literal translation. Works, but nobody writes this."""

    def __init__(self, id, amount):
        self._id = id
        self._amount = amount

    def get_id(self):
        return self._id

    def get_amount(self):
        return self._amount

    def set_amount(self, amount):
        self._amount = amount


@dataclass
class OrderPythonic:
    """What you'd actually write: public attributes, generated __init__/__repr__/__eq__."""
    id: str
    amount: float
    tags: list = field(default_factory=list)   # NOT tags: list = []


class OrderWithValidation:
    """Add a @property ONLY when you need logic. Callers never have to change."""

    def __init__(self, id, amount):
        self._id = id
        self.amount = amount               # goes through the setter

    @property
    def id(self):                          # read-only: no setter defined
        return self._id

    @property
    def amount(self):
        return self._amount

    @amount.setter
    def amount(self, value):
        if value < 0:
            raise ValueError("amount must be >= 0")
        self._amount = value

    def __repr__(self):                    # ~ toString(), but for developers
        return f"OrderWithValidation({self._id!r}, {self._amount})"


print("java style   :", OrderJavaStyle("o1", 100).get_amount())
print("pythonic     :", OrderPythonic("o1", 100))
print("with property:", OrderWithValidation("o1", 100))
try:
    OrderWithValidation("o2", -5)
except ValueError as e:
    print("validation   :", e)
# KEY POINT: OrderPythonic.amount can become a @property LATER without breaking
# a single caller. That is why pre-emptive getters/setters are unnecessary.


# ================================================================= interfaces
section("interfaces: ABC (nominal, like Java) vs Protocol (structural, no Java analogue)")


class PaymentGateway(ABC):                 # ~ interface: implementers must inherit
    @abstractmethod
    def charge(self, amount: float) -> str: ...


class Razorpay(PaymentGateway):
    def charge(self, amount): return f"rzp_{amount}"


try:
    PaymentGateway()
except TypeError as e:
    print("abstract instantiation ->", e)
print("Razorpay().charge(100) ->", Razorpay().charge(100))


class SupportsCharge(Protocol):            # structural — implementer never imports this
    def charge(self, amount: float) -> str: ...


class ThirdPartyGateway:                   # a class you do NOT control
    def charge(self, amount): return f"tp_{amount}"


def process(gw: SupportsCharge, amt):      # mypy checks this structurally
    return gw.charge(amt)


print("Protocol accepts a class that never heard of it ->", process(ThirdPartyGateway(), 50))


# ================================================================= MRO
section("super() is NOT 'the parent' — it is the next class in the instance's MRO")


class A:
    def hello(self): print("    A")


class B(A):
    def hello(self): print("    B"); super().hello()


class C(A):
    def hello(self): print("    C"); super().hello()


class D(B, C):
    def hello(self): print("    D"); super().hello()


print("D.__mro__:", [k.__name__ for k in D.__mro__])
print("B().hello()  ->"); B().hello()
print("D().hello()  ->"); D().hello()
print("  NOTE: the SAME super() line inside B reached A for a B, and C for a D.")
print("  Java has no analogue — there is no multiple class inheritance.")


# ================================================================= concurrency
section("concurrency: the GIL means `counter += 1` is still a race")
counter = 0
lock = threading.Lock()
ITERATIONS, THREADS = 20_000, 4
EXPECTED = ITERATIONS * THREADS


def run(body, label):
    global counter
    counter = 0
    threads = [threading.Thread(target=body) for _ in range(THREADS)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    print(f"  {label:<34} {counter:>8,} / {EXPECTED:,}   lost {EXPECTED - counter:,}")


def bare():
    global counter
    for _ in range(ITERATIONS):
        counter += 1                       # LOAD, ADD, STORE — three separate bytecodes


def read_yield_write():
    global counter
    for _ in range(ITERATIONS):
        tmp = counter                      # read
        time.sleep(0)                      # any function call is a possible switch point
        counter = tmp + 1                  # write — another thread may have written between


def read_yield_write_locked():
    global counter
    for _ in range(ITERATIONS):
        with lock:                         # ~ synchronized
            tmp = counter
            time.sleep(0)
            counter = tmp + 1


run(bare, "bare counter += 1")
run(read_yield_write, "read / yield / write, NO lock")
run(read_yield_write_locked, "read / yield / write, WITH lock")

print("""
  Note the first line: on CPython 3.13+ a BARE `counter += 1` in a tight loop often
  loses nothing, because the interpreter only checks for a GIL handoff at the loop
  back-edge — i.e. AFTER the store. That does NOT make it atomic or safe; it means
  the bug HIDES until the critical section contains a function call, which all real
  code does. The second line adds exactly that and the updates vanish.

  The GIL protects the INTERPRETER's state, not YOUR invariants.""")
# EXPERIMENT: run this file several times — line 2 loses a different amount each run.
# EXPERIMENT: replace time.sleep(0) with a call to any helper function and see the
#             race persist. It is the call, not the sleep, that creates the window.


# ================================================================= misc
section("things Python has that Java doesn't")
items = [10, 20, 30, 40, 50]
a, b = 1, 2
a, b = b, a
first, *rest = items
print("tuple swap        : a, b =", a, b)
print("unpacking         : first =", first, "rest =", rest)
print("slicing           :", items[1:4], items[::-1], items[::2])
print("f-string debugging: ", end="")
x = 42
print(f"{x=}")
print("arbitrary ints    :", 2 ** 100)
print("chained comparison:", 1 < 5 < 10, " (Java needs 1 < 5 && 5 < 10)")
print("keyword args      : no builder pattern needed")


# EXERCISE 1: write the Java `for (int i = 0; i < items.size(); i++)` pattern in Python,
#             then rewrite it with enumerate(). Which reads better?
# EXERCISE 2: take OrderPythonic and add validation to `amount` WITHOUT changing any
#             calling code. Prove it by calling OrderPythonic("o1", 100).amount first.
# EXERCISE 3: build a class that implements SupportsCharge but does NOT inherit it.
#             Install mypy and confirm it type-checks. Then break the signature.
# EXERCISE 4: replace the `counter += 1` race with a queue.Queue and no lock at all.
