"""
The built-in decorators every Python interview touches: `@classmethod`, `@staticmethod`,
`@property`, plus `functools`' `cached_property`, `lru_cache`, `singledispatchmethod`,
`total_ordering` and `@dataclass`.

03_decorators.py is about WRITING decorators. This file is about the ones Python already gives
you -- what each actually does to the attribute lookup, when to pick which, and the five traps:

  1. a `@classmethod` factory that hardcodes its class name breaks every subclass
  2. `@lru_cache` on a method keeps `self` alive forever -- a real memory leak
  3. `@cached_property` needs a `__dict__`, so it cannot coexist with `__slots__`
  4. `@classmethod` stacked on `@property` worked on 3.9-3.12 and now FAILS SILENTLY
  5. a `@property` that does expensive work or raises turns `obj.x` into a landmine

Run me: python 16_methods_and_builtin_decorators.py
"""
import functools
import gc
import sys
import weakref
from dataclasses import dataclass, field


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------- the three method types
section("instance vs class vs static: what the FIRST ARGUMENT is, and nothing else")


class Order:
    tax_rate = 0.20                      # a CLASS attribute -- shared by every instance

    def __init__(self, amount):
        self.amount = amount             # an INSTANCE attribute -- one per object

    def with_tax(self):
        """INSTANCE method. First arg `self` = the object. Needs instance data."""
        return self.amount * (1 + self.tax_rate)

    @classmethod
    def set_tax_rate(cls, rate):
        """CLASS method. First arg `cls` = the class. Reads/writes CLASS state,
        or builds an instance (a factory -- see the next section)."""
        cls.tax_rate = rate
        return cls.tax_rate

    @staticmethod
    def is_valid_amount(amount):
        """STATIC method. NO implicit first arg. A plain function that lives in the class's
        namespace because it belongs to the concept, not to any instance or the class."""
        return isinstance(amount, (int, float)) and amount > 0


o = Order(100)
print(f"  instance method : o.with_tax()                  -> {o.with_tax()}")
print(f"  class method    : Order.set_tax_rate(0.05)      -> {Order.set_tax_rate(0.05)}")
print(f"  ...and it changed CLASS state, so o sees it too -> {o.with_tax()}")
print(f"  static method   : Order.is_valid_amount(-5)     -> {Order.is_valid_amount(-5)}")
print(f"  all three are callable on an INSTANCE too       -> {o.is_valid_amount(10)}")
print("""
  Decision rule -- ask "what does it need?":
    needs the instance (self.amount)     -> instance method
    needs the class    (cls, subclasses) -> @classmethod
    needs NEITHER                        -> @staticmethod  (or a module-level function)""")
Order.set_tax_rate(0.20)   # put it back


# ---------------------------------------------------------------- classmethod as a factory
section("the #1 use of @classmethod: an alternative constructor that SUBCLASSES INHERIT")


class Event:
    def __init__(self, name, payload):
        self.name, self.payload = name, payload

    @classmethod
    def from_json(cls, raw):
        """`cls` is the ACTUAL class the call was made on -- so a subclass gets a subclass back.
        This is the entire reason to use @classmethod instead of @staticmethod here."""
        import json
        data = json.loads(raw)
        return cls(data["name"], data.get("payload", {}))

    @staticmethod
    def from_json_broken(raw):
        """The same factory as a @staticmethod. It has no `cls`, so it must name the class --
        and now every subclass silently gets the WRONG type back."""
        import json
        data = json.loads(raw)
        return Event(data["name"], data.get("payload", {}))   # <-- hardcoded. The bug.

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"


class AuditEvent(Event):
    """Adds behaviour the parent doesn't have."""

    def redact(self):
        return "<redacted>"


raw = '{"name": "order.created", "payload": {"id": 1}}'
good = AuditEvent.from_json(raw)
bad = AuditEvent.from_json_broken(raw)
print(f"  @classmethod  -> {good!r}   (an AuditEvent, as asked)")
print(f"  @staticmethod -> {bad!r}        (an Event! the subclass was ignored)")
print(f"  so the subclass method exists on one and not the other: "
      f"{hasattr(good, 'redact')} vs {hasattr(bad, 'redact')}")
try:
    bad.redact()
except AttributeError as e:
    print(f"  calling it: AttributeError: {e}")
print("  the same `cls` trick is why `dict.fromkeys()` works on a dict SUBCLASS.")

# Named constructors you already use that are exactly this pattern:
print(f"\n  stdlib examples of the same pattern:")
print(f"    dict.fromkeys('abc', 0)        -> {dict.fromkeys('abc', 0)}")
print(f"    int.from_bytes(b'\\x01\\x00', 'big') -> {int.from_bytes(b'\x01\x00', 'big')}")
print("    datetime.now() / .fromisoformat() / .fromtimestamp()  -- all classmethods")


# ---------------------------------------------------------------- what the lookup ACTUALLY does
section("the mechanism: all three are DESCRIPTORS, and that's the whole explanation")


class Demo:
    def instance_m(self):
        return "instance"

    @classmethod
    def class_m(cls):
        return "class"

    @staticmethod
    def static_m():
        return "static"


d = Demo()
print(f"  d.instance_m   -> {type(d.instance_m).__name__:9s}  bound to the INSTANCE")
print(f"    .__self__ is d: {d.instance_m.__self__ is d}   .__func__ is the plain function: "
      f"{d.instance_m.__func__ is Demo.instance_m}")
print(f"  Demo.instance_m-> {type(Demo.instance_m).__name__:9s}  NOT bound -- you must pass self "
      f"yourself: {Demo.instance_m(d)!r}")
print(f"  d.class_m      -> {type(d.class_m).__name__:9s}  bound to the CLASS "
      f"(.__self__ is Demo: {d.class_m.__self__ is Demo})")
print(f"  d.static_m     -> {type(d.static_m).__name__:9s}  nothing is bound at all")
print("""
  Why: a function stored on a class is a DESCRIPTOR (it has __get__). Attribute access runs it:
    function.__get__(obj, cls)    -> a bound method   (prepends obj  as self)
    classmethod.__get__(obj, cls) -> a bound method   (prepends cls  as cls)
    staticmethod.__get__(obj,cls) -> the plain function (prepends nothing)
  That is the ENTIRE difference between the three. See 06_descriptors_metaclasses.py.""")

print(f"  reaching the raw function through the descriptor: "
      f"{Demo.__dict__['class_m'].__func__.__name__!r}")
print(f"  and since 3.10 a staticmethod object is directly callable: "
      f"{Demo.__dict__['static_m']()!r}")


# ---------------------------------------------------------------- staticmethod vs module function
section("@staticmethod vs a plain module-level function: a real choice, not a style one")
print("""  Use @staticmethod when:
    - it is conceptually part of the class (Order.is_valid_amount), so the name reads better
    - subclasses may want to OVERRIDE it (a module function cannot be overridden)
    - it is called polymorphically through self/cls (self.is_valid_amount(x) hits the override)

  Use a module-level function when:
    - it is genuinely independent -- then a class is just a namespace you don't need
    - it needs to be imported and used on its own

  The thing most people miss: a @staticmethod IS inherited and CAN be overridden.""")


class Validator:
    @staticmethod
    def normalise(value):
        return value.strip()

    def clean(self, value):
        return self.normalise(value)        # goes through `self`, so it picks up the override


class StrictValidator(Validator):
    @staticmethod
    def normalise(value):                   # overriding a staticmethod -- perfectly normal
        return value.strip().lower()


print(f"  Validator().clean('  AbC ')       -> {Validator().clean('  AbC ')!r}")
print(f"  StrictValidator().clean('  AbC ') -> {StrictValidator().clean('  AbC ')!r}  "
      f"<- the override won, via self")


# ---------------------------------------------------------------- @property
section("@property: a method that looks like an attribute (getter / setter / deleter)")


class Temperature:
    def __init__(self, celsius=0.0):
        self._celsius = celsius            # the single source of truth

    @property
    def celsius(self):
        """The GETTER. `t.celsius` calls this -- no parentheses."""
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        """The SETTER. `t.celsius = 5` calls this, so validation can't be bypassed."""
        if value < -273.15:
            raise ValueError(f"{value} is below absolute zero")
        self._celsius = value

    @celsius.deleter
    def celsius(self):
        """The DELETER. `del t.celsius` calls this. Rare, but it exists."""
        print("    (resetting to 0)")
        self._celsius = 0.0

    @property
    def fahrenheit(self):
        """A COMPUTED, read-only attribute -- derived, never stored, so it cannot go stale."""
        return self._celsius * 9 / 5 + 32


t = Temperature(25)
print(f"  t.celsius    -> {t.celsius}   (a method call that reads like an attribute)")
print(f"  t.fahrenheit -> {t.fahrenheit}  (computed; there is no _fahrenheit to drift)")
t.celsius = 100
print(f"  after t.celsius = 100, t.fahrenheit -> {t.fahrenheit}")
try:
    t.celsius = -300
except ValueError as e:
    print(f"  t.celsius = -300 -> ValueError: {e}")
try:
    t.fahrenheit = 100
except AttributeError as e:
    print(f"  t.fahrenheit = 100 -> AttributeError: {e}  (no setter = read-only)")
del t.celsius
print(f"  after `del t.celsius` -> {t.celsius}")

print("""
  Why this matters (the Java contrast): in Java you write getFoo()/setFoo() from day one, because
  turning a public field into a method later is a breaking API change. In Python you expose a
  PLAIN ATTRIBUTE and promote it to a @property the day you need logic -- and no caller changes.
  So: never write get_x()/set_x() in Python. Start plain; add @property when there's a reason.

  The trap: `obj.x` now LOOKS free but may do anything. A property must be cheap and must not
  raise for normal input -- a property that hits the database turns an innocent-looking loop into
  N queries, and `repr()` or a debugger stepping over it triggers the work.""")


# ---------------------------------------------------------------- cached_property
section("@functools.cached_property: compute once per instance, then it IS an attribute")


class Report:
    def __init__(self, rows):
        self.rows = rows
        self.compute_count = 0

    @property
    def total_every_time(self):
        self.compute_count += 1
        return sum(self.rows)

    @functools.cached_property
    def total_cached(self):
        """Runs ONCE, then overwrites itself in the instance __dict__, so later reads are a plain
        dict lookup -- the descriptor is never consulted again."""
        self.compute_count += 1
        return sum(self.rows)


r = Report([1, 2, 3])
r.total_every_time, r.total_every_time, r.total_every_time
print(f"  @property      : 3 reads -> computed {r.compute_count} times")
r.compute_count = 0
r.total_cached, r.total_cached, r.total_cached
print(f"  @cached_property: 3 reads -> computed {r.compute_count} time")
print(f"  because the value now lives in the instance dict: {'total_cached' in r.__dict__}")
print(f"  so you INVALIDATE it with: del r.total_cached  (or r.__dict__.pop('total_cached', None))")
del r.total_cached
print(f"  after del, 'total_cached' in r.__dict__ -> {'total_cached' in r.__dict__}")

print("\n  the two gotchas:")


class Slotted:
    __slots__ = ("rows",)

    def __init__(self, rows):
        self.rows = rows

    @functools.cached_property
    def total(self):
        return sum(self.rows)


try:
    Slotted([1, 2]).total
except TypeError as e:
    print(f"    1. needs a __dict__ to cache into, so __slots__ breaks it: TypeError: {e}")
print(f"    2. not thread-safe: since 3.12 there is no lock, so two threads can both compute it")
print(f"       (before 3.12 there WAS a class-wide lock, which was itself a bottleneck).")
print(f"       Harmless for a pure function; a problem if the computation has side effects.")
print(f"  and it is per-INSTANCE. For a pure function keyed by arguments, use @lru_cache.")


# ---------------------------------------------------------------- lru_cache
section("@functools.lru_cache / @cache: memoise a PURE function -- and the method trap")


@functools.lru_cache(maxsize=256)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)


print(f"  fib(80) = {fib(80)}  (instant, and would be astronomically slow uncached)")
print(f"  introspection is built in: {fib.cache_info()}")
fib.cache_clear()
print(f"  after cache_clear(): {fib.cache_info()}")
print("  requirements: arguments must be HASHABLE (so no dict/list args) and the function must")
print("  be PURE -- same args, same result, no side effects. `@functools.cache` is")
print("  `lru_cache(maxsize=None)`: unbounded, so it is a memory leak on unbounded input.")

print("\n  THE TRAP -- @lru_cache on a method keeps every instance alive forever:")


class Heavy:
    def __init__(self, n):
        self.n = n
        self.payload = bytes(1_000_000)        # pretend this is expensive to hold

    @functools.lru_cache(maxsize=None)         # the cache lives on the CLASS, keyed by (self, x)
    def work(self, x):
        return self.n * x


h = Heavy(10)
ref = weakref.ref(h)
h.work(5)
del h
gc.collect()
print(f"    instance still alive after `del h`: {ref() is not None}  <- a genuine memory leak")
print(f"    because the cache key is (self, x), the cache holds a strong ref to self: "
      f"{Heavy.work.cache_info()}")
Heavy.work.cache_clear()
gc.collect()
print(f"    after cache_clear(): still alive? {ref() is not None}")
print("""    The fixes, in order of preference:
      - @cached_property        if the value depends only on the instance (no arguments)
      - a per-instance cache    self._cache = {} in __init__
      - @staticmethod + lru_cache, passing only the values that matter (not self)
      - functools.lru_cache on a module-level function taking plain arguments""")


# ---------------------------------------------------------------- stacking order
section("stacking: @abstractmethod goes INNERMOST, and one old chain now fails SILENTLY")

print("""  The order that is load-bearing -- @abstractmethod must be the innermost decorator:
      @property          @classmethod        @staticmethod
      @abstractmethod    @abstractmethod     @abstractmethod
      def dsn(self):     def make(cls):      def helper():
  Reverse any of those and the abstractness is silently LOST (see 13_abstract_base_classes.py).""")


class Config:
    _registry = {"env": "prod"}

    @classmethod
    @property
    def env_chained(cls):
        """`@classmethod` stacked on `@property` was supported in 3.9-3.12, deprecated in 3.11,
        and REMOVED in 3.13. It no longer raises -- it just quietly does the wrong thing."""
        return cls._registry["env"]


result = Config.env_chained
print(f"\n  on Python {sys.version_info.major}.{sys.version_info.minor}, "
      f"Config.env_chained -> {result!r}")
if isinstance(result, str):
    print("    (this interpreter still supports the chain)")
else:
    print(f"    ...which is a {type(result).__name__}, NOT the string 'prod'. It FAILED SILENTLY.")
    print("    No exception, no warning -- just the wrong object, which then breaks far away.")
print("""  What to write instead for a class-level computed value:
      - a plain @classmethod and CALL it:  Config.env()
      - a module-level constant
      - a custom descriptor on a metaclass, if it genuinely must look like an attribute""")


# ---------------------------------------------------------------- singledispatch
section("@functools.singledispatchmethod: Python's answer to method overloading")


class Serialiser:
    """Python has no overloading by signature -- a second `def fmt` just replaces the first.
    singledispatch picks an implementation by the FIRST argument's runtime type instead."""

    @functools.singledispatchmethod
    def fmt(self, value):
        return f"other: {value!r}"               # the fallback

    @fmt.register
    def _(self, value: int):
        return f"int: {value:,}"

    @fmt.register
    def _(self, value: list):
        return f"list of {len(value)}"

    @fmt.register
    def _(self, value: dict):
        return f"dict with keys {sorted(value)}"


s = Serialiser()
for v in (1000, [1, 2, 3], {"b": 1, "a": 2}, "text"):
    print(f"  fmt({v!r:18s}) -> {s.fmt(v)}")
print("  dispatch is on the first arg AFTER self, and registration is by type annotation.")
print("  the alternative -- an if/elif isinstance ladder -- is fine for 2 types and unreadable at 6.")


# ---------------------------------------------------------------- total_ordering & dataclass
section("@functools.total_ordering and @dataclass: decorators that WRITE methods for you")


@functools.total_ordering
class Version:
    """Define __eq__ and ONE of <, <=, >, >= and get the other three for free."""

    def __init__(self, major, minor):
        self.major, self.minor = major, minor

    def __eq__(self, other):
        return (self.major, self.minor) == (other.major, other.minor)

    def __lt__(self, other):
        return (self.major, self.minor) < (other.major, other.minor)

    def __repr__(self):
        return f"v{self.major}.{self.minor}"


a, b = Version(1, 2), Version(1, 10)
print(f"  defined only __eq__ and __lt__, yet: {a} < {b} = {a < b}, "
      f"{a} >= {b} = {a >= b}, max = {max(a, b)}")


@dataclass(frozen=True, order=True)
class Point:
    """@dataclass reads the ANNOTATIONS and generates __init__, __repr__ and __eq__ --
    plus ordering with order=True, and hashability/immutability with frozen=True."""
    x: int
    y: int
    tags: list = field(default_factory=list)     # the mutable-default fix, dataclass style


p1, p2 = Point(1, 2), Point(1, 2)
print(f"  @dataclass gives __repr__: {p1}")
print(f"  ...__eq__ by VALUE: p1 == p2 -> {p1 == p2}   (plain classes compare by identity)")
print(f"  ...__lt__ from order=True:   p1 < Point(2, 0) -> {p1 < Point(2, 0)}")
try:
    p1.x = 5
except Exception as e:
    print(f"  ...and frozen=True blocks assignment: {type(e).__name__}: {e}")

# frozen=True generates __hash__ -- but hashing still walks the FIELDS, so one mutable field
# makes the whole instance unhashable at use time. A trap worth meeting once.
try:
    {p1: "ok"}
except TypeError as e:
    print(f"  BUT frozen != hashable: {{p1: 'ok'}} -> TypeError: {e}")
    print("    because `tags: list` is a mutable field, and hash() hashes the field TUPLE.")


@dataclass(frozen=True)
class Coord:
    x: int
    y: int                              # every field hashable -> the instance is hashable


print(f"  with only hashable fields it works: {{Coord(1, 2): 'ok'}}[Coord(1, 2)] -> "
      f"{ {Coord(1, 2): 'ok'}[Coord(1, 2)] }")
print("    (use a tuple, or field(hash=False), or frozenset for a collection field)")


# ---------------------------------------------------------------- __new__ vs __init__
section("__new__ vs __init__: the one place you need the other constructor hook")

print("""  __new__  CREATES and returns the object (an implicit @staticmethod, first arg `cls`)
  __init__ INITIALISES the already-created object (first arg `self`, returns None)
  You almost never need __new__. The two times you do:""")


class UpperStr(str):
    """1. Subclassing an IMMUTABLE type. By the time __init__ runs the str already exists with
    its value fixed, so the only place to change it is __new__."""

    def __new__(cls, value):
        return super().__new__(cls, value.upper())


print(f"\n  1. immutable subclass: UpperStr('hello') -> {UpperStr('hello')!r}")


class Singleton:
    """2. Controlling INSTANCE CREATION itself -- returning an existing object instead of a new
    one. (A module-level instance is usually the more Pythonic answer.)"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


print(f"  2. singleton: Singleton() is Singleton() -> {Singleton() is Singleton()}")
print("     note __init__ still runs on EVERY call, even when __new__ returns the old object --")
print("     which is why a singleton that initialises state in __init__ resets it each time.")
class HasHook:
    def __init_subclass__(cls, **kwargs):     # no @classmethod written -- Python adds it
        super().__init_subclass__(**kwargs)


print(f"\n  and two implicit decorators worth knowing:")
print(f"    __init_subclass__ is made a classmethod for you -> "
      f"{type(HasHook.__dict__['__init_subclass__']).__name__}")
print(f"    __new__ is made a staticmethod for you          -> "
      f"{type(UpperStr.__dict__['__new__']).__name__}")
print("    so writing @classmethod / @staticmethod on them is redundant, not wrong.")


# ---------------------------------------------------------------- the summary table
section("the summary table")
print("""  decorator                what it does                           when
  -----------------------  -------------------------------------  ---------------------------------
  (none)                   instance method; self = the object     needs instance data
  @classmethod             cls = the actual class                 factories, class-level state
  @staticmethod            no implicit first argument             belongs to the concept only
  @property                method that reads as an attribute      validation, computed values
  @x.setter / @x.deleter   the write / delete half                enforce invariants on assignment
  @functools.cached_property  compute once PER INSTANCE           expensive, instance-derived, no args
  @functools.lru_cache     memoise by arguments (LRU-bounded)     pure functions; NOT on methods
  @functools.cache         lru_cache(maxsize=None)                pure + small, bounded input domain
  @functools.wraps         keep name/doc/signature in a wrapper   ALWAYS, when writing a decorator
  @functools.singledispatchmethod  dispatch on arg type           replaces an isinstance ladder
  @functools.total_ordering  fill in the other comparisons        value objects
  @dataclass               generate __init__/__repr__/__eq__      data holders
  @abstractmethod          must be implemented to instantiate     contracts (INNERMOST decorator)
  @staticmethod on __new__ (implicit)  creates the object         immutable subclasses, singletons""")


# EXPERIMENT 1: add `@classmethod def from_dict(cls, d)` to Event, call it on AuditEvent, and
# confirm you get an AuditEvent. Then rewrite it as a @staticmethod and watch the type change.
# EXPERIMENT 2: give Temperature a `@property def from_db(self)` that prints "QUERY" and returns 1.
# Then put a Temperature in a list and call repr() on the list. Count the QUERY lines.
# EXPERIMENT 3: add __slots__ = ("rows", "compute_count") to Report and run again. Read the
# TypeError and decide which of cached_property or __slots__ you would give up.
# EXPERIMENT 4: change Heavy.work to a @cached_property (drop the `x` argument) and re-run the
# weakref check. Confirm the instance is collected this time.
# EXPERIMENT 5: stack @property ABOVE @classmethod (the other order) in Config and see what
# Config.env_chained gives you. Neither order works on 3.13+ -- that's the point.

# EXERCISE: write a `Money` class with:
#   - `amount_cents` stored as an int, and a `@property amount` exposing it as a Decimal
#   - a setter that rejects negative values and non-Decimal input
#   - `@classmethod from_string("12.34")` that a `Money` SUBCLASS also inherits correctly
#   - `@staticmethod is_valid_currency(code)`
#   - `@cached_property formatted` returning "$12.34", and a note on when it must be invalidated
#   - `@functools.total_ordering` so two Money objects compare
# Then explain in one sentence why `amount` is a property rather than a plain attribute, and why
# `from_string` is a classmethod rather than a staticmethod.
