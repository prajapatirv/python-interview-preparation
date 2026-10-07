# Deep Dive 33 — `@classmethod`, `@staticmethod`, `@property` and the Built-in Decorators

> Runnable companion: [`01_python_core/16_methods_and_builtin_decorators.py`](../01_python_core/16_methods_and_builtin_decorators.py)
> Related deep dives: [03 — Writing custom decorators](03_decorators.md) ·
> [05 — Descriptors and metaclasses](05_context_managers_descriptors_metaclasses.md) ·
> [06 — OOP and MRO](06_oop_inheritance_mro.md) ·
> [23 — Abstract base classes](23_abstract_classes_interfaces.md) ·
> [24 — Python basics](24_python_basics_essentials.md) · [17 — Caching](17_caching.md)

## What interviewers are actually probing

[Deep dive 03](03_decorators.md) is about **writing** decorators. This one is about the ones Python
already gives you — and it gets asked at every level, for different reasons:

- **At 2 years**: can you state the difference between an instance, class and static method?
- **At 6+ years**: do you know *why* they differ (the descriptor protocol), when a `@property` is the
  wrong tool, and the four traps that cause production bugs?

The four traps, because these are what separate a recited answer from a lived one:

1. A **`@classmethod` factory that hardcodes its class name** silently returns the wrong type for
   every subclass.
2. **`@lru_cache` on a method keeps `self` alive forever** — a genuine, measurable memory leak.
3. **`@cached_property` cannot coexist with `__slots__`**, and since 3.12 it has no lock.
4. **`@classmethod` stacked on `@property`** worked on 3.9–3.12 and now **fails silently** on 3.13+.

And the framing question they're often really asking: *"do you write Java in Python?"* A candidate who
writes `get_amount()`/`set_amount()` instead of a plain attribute promoted to a `@property` when
needed has answered that without being asked.

---

## Must-know points

- The **only** difference between the three method types is **what gets prepended as the first
  argument**: the instance, the class, or nothing.
- All three are **descriptors**. `function.__get__` returns a bound method, `classmethod.__get__`
  binds the class, `staticmethod.__get__` returns the plain function. That is the whole mechanism.
- **`@classmethod`'s `cls` is the *actual* class**, so a factory inherited by a subclass returns the
  subclass. This is why `dict.fromkeys()` works on a dict subclass.
- **`@staticmethod` is inherited and overridable** — the thing most people get wrong when comparing it
  to a module-level function.
- **`@property`** turns a method into attribute access, with optional `@x.setter` / `@x.deleter`.
  No setter = read-only.
- **Never write `get_x()`/`set_x()` in Python.** Expose a plain attribute; promote it to a `@property`
  when you need logic. Callers never change.
- A `@property` must be **cheap and non-raising** — `obj.x` looks free, so an expensive property turns
  an innocent loop into N queries.
- **`@functools.cached_property`** computes once per instance and then *becomes* an instance attribute.
  Invalidate with `del obj.attr`. Needs a `__dict__`. Not thread-safe (3.12+ removed the lock).
- **`@functools.lru_cache`** memoises a **pure function** by its arguments. Arguments must be hashable.
  **Not on methods** — the cache lives on the class and keys on `self`.
- **`@functools.singledispatchmethod`** is Python's method overloading: dispatch on the first
  argument's runtime type.
- **`@functools.total_ordering`** fills in the other three comparisons from `__eq__` + one of them.
- **`@dataclass`** generates `__init__`/`__repr__`/`__eq__` from annotations; `frozen=True` adds
  `__hash__` — but a mutable field still makes instances unhashable at use time.
- **`__new__` creates, `__init__` initialises.** `__new__` is an implicit `staticmethod`,
  `__init_subclass__` an implicit `classmethod`.

---

## Interview questions and full answers

### Q1. Explain instance vs class vs static methods.

**The only difference is the implicit first argument.**

```python
class Order:
    tax_rate = 0.20                       # CLASS attribute — shared

    def __init__(self, amount):
        self.amount = amount              # INSTANCE attribute — one per object

    def with_tax(self):                   # INSTANCE: self = the object
        return self.amount * (1 + self.tax_rate)

    @classmethod
    def set_tax_rate(cls, rate):          # CLASS: cls = the class
        cls.tax_rate = rate

    @staticmethod
    def is_valid_amount(amount):          # STATIC: nothing is prepended
        return isinstance(amount, (int, float)) and amount > 0
```

| | First argument | Called as | Can read instance state? | Can read class state? |
|---|---|---|---|---|
| instance method | `self` (the object) | `obj.m()` | **yes** | yes, via `self.x` |
| `@classmethod` | `cls` (the class) | `Cls.m()` **or** `obj.m()` | no | **yes** |
| `@staticmethod` | — | `Cls.m()` **or** `obj.m()` | no | no |

**The decision rule, which is what they want to hear — ask "what does it need?":**

- Needs the instance (`self.amount`) → **instance method**.
- Needs the class — to read/write class state, or to construct one — → **`@classmethod`**.
- Needs **neither** → **`@staticmethod`**, or honestly a module-level function.

Two details worth adding:

- **All three are callable on an instance.** `obj.is_valid_amount(5)` works; Python just doesn't pass
  `obj`. So "static methods are called on the class" is not quite right.
- **A `@classmethod` that writes `cls.tax_rate = rate` writes to the class it was called on.**
  `SubOrder.set_tax_rate(0.1)` creates `SubOrder.tax_rate` and *shadows* the parent's, leaving
  `Order.tax_rate` untouched. That asymmetry (reads fall back to the parent, writes land locally)
  surprises people and is a real source of "why didn't my config change apply everywhere?".

---

### Q2. Why use `@classmethod` instead of `@staticmethod` for a factory?

**Because `cls` is the actual class the call was made on, so subclasses inherit the factory
correctly.** This is the single most important thing to say about `@classmethod`.

```python
class Event:
    def __init__(self, name, payload):
        self.name, self.payload = name, payload

    @classmethod
    def from_json(cls, raw):              # cls = AuditEvent when called on AuditEvent
        data = json.loads(raw)
        return cls(data["name"], data.get("payload", {}))

    @staticmethod
    def from_json_broken(raw):            # no cls, so it must name the class — the bug
        data = json.loads(raw)
        return Event(data["name"], data.get("payload", {}))

class AuditEvent(Event):
    def redact(self): return "<redacted>"
```

```python
AuditEvent.from_json(raw)          # AuditEvent('order.created')  ✅
AuditEvent.from_json_broken(raw)   # Event('order.created')       ❌ — the subclass was ignored
AuditEvent.from_json_broken(raw).redact()
# AttributeError: 'Event' object has no attribute 'redact'
```

The failure is nasty because it's **silent at the call site** and only blows up later, somewhere that
assumed it had an `AuditEvent`. And because the base class is usually written before any subclass
exists, the bug is introduced by code that was correct when written.

**The stdlib is full of this pattern**, which is a good thing to cite:

```python
dict.fromkeys("abc", 0)              # works on a dict SUBCLASS, returning the subclass
int.from_bytes(b"\x01\x00", "big")
datetime.now() / .fromisoformat() / .fromtimestamp()
pathlib.Path.cwd() / .home()
```

**The named-constructor pattern generally.** Python has no constructor overloading, so where Java
would write three constructors you write one `__init__` plus named classmethods:

```python
Money(cents=1234)                 # the canonical, boring constructor
Money.from_string("12.34")        # named, documented, discoverable alternatives
Money.from_decimal(Decimal("12.34"))
Money.zero()
```

That's strictly better than a single `__init__` with five mutually-exclusive optional arguments and
a pile of `if` statements — each factory validates exactly its own input and the name documents the
intent.

---

### Q3. How do they actually work? (The descriptor answer.)

A function stored on a class is a **descriptor** — it defines `__get__`. Attribute access invokes it,
and *that* is where the binding happens:

```
function.__get__(obj, cls)     -> bound method   (prepends obj as self)
classmethod.__get__(obj, cls)  -> bound method   (prepends cls as cls)
staticmethod.__get__(obj, cls) -> the plain function (prepends nothing)
```

Everything observable follows from those three lines:

```python
d = Demo()
type(d.instance_m)          # method    — bound to the instance
d.instance_m.__self__ is d  # True
d.instance_m.__func__       # the underlying plain function

type(Demo.instance_m)       # function  — NOT bound; Demo.instance_m(d) is how you call it
type(d.class_m)             # method    — bound to the CLASS
d.class_m.__self__ is Demo  # True
type(d.static_m)            # function  — nothing bound at all
```

**Why this is worth knowing rather than trivia:**

- It explains why `Demo.instance_m(d)` works and is exactly what `d.instance_m()` does. Unbound-method
  calls are what `super()` and most mixin plumbing rely on.
- It explains why a `@staticmethod` has **zero** call overhead relative to a module function — there's
  nothing to bind.
- It explains the whole of [`06_descriptors_metaclasses.py`](../01_python_core/06_descriptors_metaclasses.py):
  `property` is a **data descriptor** (it defines `__set__` too), which is why it wins over an entry in
  the instance `__dict__`, while a method is a non-data descriptor, which is why an instance attribute
  can shadow a method.
- It's the mechanism behind `functools.wraps`, `cached_property`, and every validation descriptor.

A small extra you can drop in: since **3.10** a `staticmethod` object is **directly callable**
(`Demo.__dict__["static_m"]()`), where before it was only usable via attribute access. And
`classmethod.__func__` reaches the underlying function.

---

### Q4. `@staticmethod` or just a module-level function?

A real design question, not style. The honest answer is that **a module-level function is the default**
and `@staticmethod` needs a justification — and there are three good ones:

**Use `@staticmethod` when:**

1. **It's conceptually part of the class.** `Order.is_valid_amount(x)` reads better than
   `order_utils.is_valid_amount(x)`, and it's discoverable from the class.
2. **Subclasses may override it.** This is the one people miss — **a `@staticmethod` is inherited and
   can be overridden; a module function cannot.**
3. **It's called polymorphically through `self`/`cls`.** That's what makes the override take effect:

```python
class Validator:
    @staticmethod
    def normalise(value):
        return value.strip()

    def clean(self, value):
        return self.normalise(value)          # via self -> picks up the override

class StrictValidator(Validator):
    @staticmethod
    def normalise(value):                     # overriding a staticmethod — perfectly normal
        return value.strip().lower()

Validator().clean("  AbC ")        # 'AbC'
StrictValidator().clean("  AbC ")  # 'abc'   <- the override won
```

**Use a module-level function when:** it's genuinely independent of the class, or callers want to
import it on its own. If a class contains nothing but `@staticmethod`s, it isn't a class — it's a
module with extra syntax, and you should delete it.

**The honest caveat:** if a `@staticmethod` grows to need `cls`, make it a `@classmethod`; if it grows
to need `self`, make it an instance method. The conversion is one line and no caller changes, so don't
agonise over the initial choice.

---

### Q5. What is `@property` for, and when is it wrong?

It turns a method into **attribute access**, with an optional setter and deleter:

```python
class Temperature:
    def __init__(self, celsius=0.0):
        self._celsius = celsius               # the single source of truth

    @property
    def celsius(self):                        # GETTER: t.celsius
        return self._celsius

    @celsius.setter
    def celsius(self, value):                 # SETTER: t.celsius = 5 — validation can't be bypassed
        if value < -273.15:
            raise ValueError(f"{value} is below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self):                     # COMPUTED, read-only — derived, so it can't go stale
        return self._celsius * 9 / 5 + 32
```

```python
t.celsius = -300     # ValueError — the invariant is enforced on assignment
t.fahrenheit = 100   # AttributeError: property 'fahrenheit' has no setter
```

**The three legitimate reasons to add one:**

1. **Validation on assignment** — the invariant can't be bypassed by `obj.x = junk`.
2. **A computed value** — `fahrenheit` is derived from `celsius`, so there's no second field to drift
   out of sync. This is the best reason, and it's about correctness, not encapsulation.
3. **Backward compatibility** — turning an existing plain attribute into logic without changing a
   single caller.

**The Java contrast, which is the point of the question.** In Java you write `getFoo()`/`setFoo()` from
day one, because promoting a public field to a method later is a breaking API change. In Python,
`obj.x` and a `@property` are the *same syntax*, so you start with a plain attribute and add the
property the day you need it. **Writing `get_amount()`/`set_amount()` in Python is the clearest
possible signal that someone is writing Java in Python.**

**When a `@property` is the WRONG tool:**

- **When it's expensive.** `obj.x` looks free, so a property that hits the database or recomputes a
  large aggregate turns `for o in orders: print(o.total)` into N queries. Worse, `repr()` on a
  collection, a debugger stepping over the line, or a logging call will trigger it. If it's expensive,
  make it an explicit method — `obj.compute_total()` — so the cost is visible at the call site. (Or
  `@cached_property`, Q6.)
- **When it can raise for normal input.** Nobody expects attribute access to throw a
  `ConnectionError`.
- **When it has side effects.** A property that mutates state or writes a log is a trap.
- **When it takes arguments** — it can't; that's a method.
- **When there's no logic at all.** A property that just returns `self._x` with a setter that just
  assigns is pure ceremony. Use a plain attribute and add the property later.
- **For validation of complex, multi-field invariants** — use `__post_init__`, a dedicated
  `validate()`, or Pydantic at the boundary. A property only sees one field at a time.

---

### Q6. `@property` vs `@cached_property` vs `@lru_cache` — which, when?

| | Recomputes | Scope of the cache | Takes arguments | Invalidate with |
|---|---|---|---|---|
| `@property` | every access | — | no | n/a |
| `@functools.cached_property` | **once per instance** | the instance `__dict__` | no | `del obj.attr` |
| `@functools.lru_cache` | once per argument tuple | **the function/class** | **yes** | `fn.cache_clear()` |

**`cached_property` computes once, then overwrites itself as a real instance attribute**, so later
reads are a plain dict lookup and the descriptor is never consulted again:

```python
class Report:
    def __init__(self, rows): self.rows = rows

    @functools.cached_property
    def total(self):
        return expensive_sum(self.rows)

r.total                      # computes
r.total                      # a dict lookup — the descriptor isn't involved
"total" in r.__dict__        # True
del r.total                  # the invalidation idiom (or r.__dict__.pop("total", None))
```

**Its two gotchas, both of which get asked:**

1. **It needs a `__dict__`.** With `__slots__` you get
   `TypeError: No '__dict__' attribute on 'Slotted' instance to cache 'total' property.` So
   `__slots__` and `cached_property` are mutually exclusive — you pick memory efficiency *or* lazy
   caching, not both. (Workaround: add `"__dict__"` to `__slots__`, which defeats most of the point.)
2. **It is not thread-safe.** Before 3.12 it held a **class-wide** lock, which was itself a scalability
   bug (every instance serialised on one lock). 3.12 **removed** the lock, so two threads can now both
   compute the value. That's harmless for a pure computation and a problem if it has side effects — in
   which case you need your own lock.

Also: it's **mutable by assignment** (`r.total = 5` just sets the attribute, no validation), and it
never expires. For time-based expiry you need a TTL cache, which is
[17 — Caching](17_caching.md).

**`lru_cache`** is for a **pure function keyed by its arguments**:

```python
@functools.lru_cache(maxsize=256)
def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)

fib.cache_info()   # CacheInfo(hits=78, misses=81, maxsize=256, currsize=81)
fib.cache_clear()
```

Requirements: arguments must be **hashable** (no dict/list args), and the function must be **pure**.
`@functools.cache` is `lru_cache(maxsize=None)` — unbounded, so it's a memory leak on unbounded input;
only use it where the input domain is genuinely small.

---

### Q7. Why is `@lru_cache` on a method a memory leak?

**Because the cache lives on the class and the cache key includes `self`, so the cache holds a strong
reference to every instance it has ever seen.**

```python
class Heavy:
    def __init__(self, n):
        self.n = n
        self.payload = bytes(1_000_000)

    @functools.lru_cache(maxsize=None)    # cache is on Heavy.work, keyed by (self, x)
    def work(self, x):
        return self.n * x

h = Heavy(10)
ref = weakref.ref(h)
h.work(5)
del h; gc.collect()
ref() is not None          # True  <- the instance is STILL ALIVE
Heavy.work.cache_info()    # CacheInfo(..., currsize=1)  — holding it
```

Three consequences, all bad:

1. **The instance is never collected** — with `maxsize=None` it's unbounded, so this is a textbook
   leak in a long-running service. One megabyte per request-scoped object adds up fast.
2. **It requires `self` to be hashable**, so it breaks on classes defining `__eq__` without
   `__hash__`.
3. **The cache is shared across instances**, so two objects with equal-but-distinct state can collide
   or, more often, pointlessly multiply the cache.

**The fixes, in order of preference:**

```python
# 1. BEST — no arguments beyond self? Use cached_property. Cache lives on the INSTANCE,
#    so it dies with the instance.
@functools.cached_property
def work(self): ...

# 2. A per-instance cache
def __init__(self): self._cache = {}
def work(self, x):
    if x not in self._cache: self._cache[x] = self.n * x
    return self._cache[x]

# 3. Hoist the pure part out — cache only the values that matter, not self
@staticmethod
@functools.lru_cache(maxsize=256)
def _work(n, x): return n * x
def work(self, x): return self._work(self.n, x)

# 4. A module-level cached function taking plain arguments
```

The general principle worth stating: **`lru_cache` is for pure functions. A method is, by definition,
not pure — it depends on `self`.** If you reach for `lru_cache` on a method, that's the signal to
extract the pure computation.

---

### Q8. What's the trap with stacking these decorators?

**Two separate ordering rules, and both fail quietly.**

**1. `@abstractmethod` must be the INNERMOST decorator:**

```python
@property            @classmethod         @staticmethod
@abstractmethod      @abstractmethod      @abstractmethod
def dsn(self): ...   def make(cls): ...   def helper(): ...
```

Reverse any of them and the abstractness is **silently lost** — `__abstractmethods__` comes out empty
and the subclass instantiates with the method missing. No warning. Covered in
[23 — Abstract base classes](23_abstract_classes_interfaces.md).

**2. `@classmethod` stacked on `@property` is gone, and its removal is silent:**

```python
class Config:
    _registry = {"env": "prod"}

    @classmethod
    @property
    def env(cls):
        return cls._registry["env"]
```

| Python | Behaviour |
|---|---|
| ≤ 3.8 | never worked |
| 3.9–3.10 | worked (chaining was added for this) |
| 3.11 | works, **deprecated** |
| **3.13+** | **removed — and it does not raise** |

On 3.13+, `Config.env` returns `<bound method env of <class 'Config'>>` — a method object, not
`"prod"`. **No exception, no warning, just the wrong object**, which then fails somewhere far away
(`"prod" in Config.env` → `TypeError`, or worse, a truthy check that silently passes). That's harder
to debug than an error would have been, which is exactly why it's worth knowing.

**What to write instead for a class-level computed value:**

```python
@classmethod
def env(cls): return cls._registry["env"]      # and CALL it: Config.env()
# or a module-level constant
# or a descriptor on the METACLASS, if it genuinely must look like an attribute
```

(`@staticmethod` + `@property` has the same story. And note `@property` + `@classmethod` in the other
order never worked at all.)

---

### Q9. How do you "overload" a method in Python?

**You don't — a second `def` with the same name just replaces the first.** There are three real
answers, and naming the trade-offs is the point:

**1. Default and keyword arguments** — covers most cases:

```python
def fetch(self, *, limit=100, offset=0, since=None): ...
```

**2. `@functools.singledispatchmethod`** — dispatch on the first argument's runtime type:

```python
class Serialiser:
    @functools.singledispatchmethod
    def fmt(self, value):
        return f"other: {value!r}"             # the fallback

    @fmt.register
    def _(self, value: int):  return f"int: {value:,}"
    @fmt.register
    def _(self, value: list): return f"list of {len(value)}"
    @fmt.register
    def _(self, value: dict): return f"dict with keys {sorted(value)}"
```

Dispatch is on the first argument **after `self`**, registration is by type annotation, and it
respects inheritance (a `bool` matches an `int` handler). Its limits: **single** dispatch only (not on
two arguments), no dispatch on value, and it's slower than an `if`. The rule of thumb: an
`isinstance` ladder is fine at two types and unreadable at six — switch when the ladder starts
growing, or when third-party code needs to register its own types (which `singledispatch` allows and a
ladder doesn't).

**3. `typing.overload`** — for the *type checker* only. It documents multiple signatures; the runtime
implementation is still one function. Useful for a public API whose return type depends on its
arguments.

---

### Q10. Which decorators write code for you?

**`@functools.total_ordering`** — define `__eq__` plus one of `<`, `<=`, `>`, `>=` and get the rest:

```python
@functools.total_ordering
class Version:
    def __eq__(self, o): return (self.major, self.minor) == (o.major, o.minor)
    def __lt__(self, o): return (self.major, self.minor) <  (o.major, o.minor)
# >=, >, <=, and max()/min()/sorted() all now work
```

The caveat: the generated methods are slower than hand-written ones (each is a small wrapper), so for
a hot comparison in a tight sort, write all four.

**`@dataclass`** — reads the annotations and generates `__init__`, `__repr__` and `__eq__`:

```python
@dataclass(frozen=True, order=True)
class Point:
    x: int
    y: int
    tags: list = field(default_factory=list)   # the mutable-default fix, dataclass style
```

The nuance worth knowing, because it bites: **`frozen=True` generates `__hash__`, but hashing walks
the fields**, so one mutable field makes the instance unhashable *at use time*:

```python
{Point(1, 2): "ok"}
# TypeError: cannot use 'Point' as a dict key (unhashable type: 'list')
```

Frozen means "you can't rebind the fields", not "every field is immutable" — the same distinction as
`tuple` being hashable only if its contents are. Fix with a `tuple`/`frozenset` field, or
`field(hash=False)`.

Also: a field without a default can never follow one with a default (`TypeError` at class creation),
`eq=True` sets `__hash__ = None` unless `frozen=True` too, and `__post_init__` is the hook for
cross-field validation.

Related, for completeness: **`@functools.wraps`** (keep a wrapper's identity — always, see
[03](03_decorators.md)), **`@functools.partial`/`partialmethod`** (pre-bind arguments),
**`@contextlib.contextmanager`** ([05](05_context_managers_descriptors_metaclasses.md)), and
**`@typing.final`** / **`@override`** (3.12+), which are checker-only.

---

### Q11. `__new__` vs `__init__`?

- **`__new__` CREATES and returns the object.** An implicit `staticmethod`; first arg is `cls`.
- **`__init__` INITIALISES the already-created object.** First arg is `self`; must return `None`.

**You almost never need `__new__`. The two times you do:**

**1. Subclassing an immutable type.** By the time `__init__` runs, the `str`/`int`/`tuple` already
exists with its value fixed, so the only place to influence it is `__new__`:

```python
class UpperStr(str):
    def __new__(cls, value):
        return super().__new__(cls, value.upper())

UpperStr("hello")      # 'HELLO'
```

**2. Controlling instance creation** — returning an existing object instead of a new one:

```python
class Singleton:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

**The gotcha to volunteer: `__init__` still runs on every call**, even when `__new__` returned the
existing object. So a singleton that initialises state in `__init__` **resets that state** on every
`Singleton()` call — a classic bug. (And in Python a module-level instance, or a function with
`@lru_cache`, is usually the more idiomatic singleton anyway.)

Two more facts: if `__new__` returns an object that **isn't** an instance of `cls`, `__init__` is
**not** called at all. And `__init_subclass__` is an implicit `classmethod`, just as `__new__` is an
implicit `staticmethod` — writing the decorator on either is redundant, not wrong.

---

## Java contrast

| Java | Python |
|---|---|
| `static` method | `@staticmethod` — but **inherited and overridable**, unlike a Java `static` |
| `static` factory method | `@classmethod`, and `cls` makes it work for subclasses |
| constructor overloading | **one `__init__`** + named `@classmethod` factories |
| `getFoo()` / `setFoo()` from day one | a **plain attribute**, promoted to `@property` only when needed |
| `private` fields | a `_name` convention; `__name` only name-mangles |
| method overloading by signature | `@singledispatchmethod`, default args, or `typing.overload` |
| `Comparable.compareTo` | `__lt__` + `@functools.total_ordering` |
| Lombok `@Data` / records | `@dataclass` |
| `static` is resolved at compile time | everything is an attribute lookup at runtime, via descriptors |
| `final` | nothing enforces it; `@typing.final` is checker-only |

**The two that matter most:** a Java `static` method is *hidden*, not overridden, by a subclass —
Python's `@staticmethod` is genuinely overridden and dispatched through `self`. And the getter/setter
difference is the single biggest source of un-Pythonic Python: `@property` exists so you *don't* need
accessors up front.

---

## A worked example

A `Money` class using each decorator for the job it's actually right for:

```python
import functools
from decimal import Decimal

@functools.total_ordering
class Money:
    """Stores integer minor units (cents) — never a float. See deep dive 24 on why."""

    CURRENCIES = frozenset({"USD", "EUR", "INR", "GBP"})

    def __init__(self, amount_cents: int, currency: str = "USD"):
        if not self.is_valid_currency(currency):          # the staticmethod, used as validation
            raise ValueError(f"unknown currency {currency!r}")
        self._amount_cents = int(amount_cents)
        self.currency = currency

    # ---- @staticmethod: belongs to the CONCEPT; needs neither instance nor class state.
    #      Kept on the class (not module-level) so a subclass can extend the currency set.
    @staticmethod
    def is_valid_currency(code: str) -> bool:
        return code in Money.CURRENCIES

    # ---- @classmethod: factories. `cls` means a SUBCLASS gets a subclass back.
    @classmethod
    def from_string(cls, text: str, currency: str = "USD") -> "Money":
        return cls(int(Decimal(text) * 100), currency)

    @classmethod
    def zero(cls, currency: str = "USD") -> "Money":
        return cls(0, currency)

    # ---- @property: a COMPUTED view. There is no _amount field to drift out of sync,
    #      and it is cheap, so attribute syntax is honest.
    @property
    def amount(self) -> Decimal:
        return Decimal(self._amount_cents) / 100

    # ---- @x.setter: the invariant cannot be bypassed by assignment.
    @amount.setter
    def amount(self, value: Decimal) -> None:
        if not isinstance(value, Decimal):
            raise TypeError("use Decimal, never float, for money")
        if value < 0:
            raise ValueError("amount cannot be negative")
        self._amount_cents = int(value * 100)
        self.__dict__.pop("formatted", None)      # INVALIDATE the cached_property below

    # ---- @cached_property: formatting is pure, derived from the instance, and takes no
    #      arguments — so cache it per instance. It MUST be invalidated by the setter above,
    #      which is the whole hazard of caching on a mutable object.
    @functools.cached_property
    def formatted(self) -> str:
        symbol = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹"}[self.currency]
        return f"{symbol}{self.amount:,.2f}"

    # ---- @total_ordering needs __eq__ plus ONE ordering operator.
    def __eq__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented                 # NotImplemented, not False — lets Python try
        return (self._amount_cents, self.currency) == (other._amount_cents, other.currency)

    def __lt__(self, other) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        if self.currency != other.currency:
            raise TypeError("cannot compare different currencies")
        return self._amount_cents < other._amount_cents

    def __hash__(self):
        return hash((self._amount_cents, self.currency))   # __eq__ kills __hash__ — restore it

    def __repr__(self):
        return f"{type(self).__name__}({self._amount_cents}, {self.currency!r})"


class TaxedMoney(Money):
    """Exists only to prove the factories inherit correctly."""
    TAX = Decimal("0.20")

    @property
    def with_tax(self) -> Decimal:
        return self.amount * (1 + self.TAX)
```

```python
m = Money.from_string("12.34")
m.amount                      # Decimal('12.34')
m.formatted                   # '$12.34'   (computed once)
m.amount = Decimal("99.99")   # validated, and invalidates `formatted`
m.formatted                   # '$99.99'   (recomputed because the setter cleared it)

t = TaxedMoney.from_string("100.00")
type(t)                       # <class 'TaxedMoney'>  — `cls` did its job
t.with_tax                    # Decimal('120.00')

sorted([Money(500), Money(100), Money(300)])        # total_ordering
Money.from_string("1.00") >= Money.from_string("1.00")   # True, from __eq__ + __lt__
{Money(100): "ok"}[Money(100)]                      # 'ok' — __hash__ was restored
```

**Why each choice, which is the part an interviewer grades:**

- **`is_valid_currency` is a `@staticmethod`** because it needs neither `self` nor `cls`, but it's kept
  on the class so it's discoverable and so a subclass can extend `CURRENCIES`.
- **`from_string`/`zero` are `@classmethod`s** because `cls(...)` means `TaxedMoney.from_string(...)`
  returns a `TaxedMoney`. As `@staticmethod`s hardcoding `Money(...)` they'd silently return the wrong
  type — Q2's bug.
- **`amount` is a `@property`, not a plain attribute**, because the stored representation (integer
  cents) deliberately differs from the public one (`Decimal`), and the setter enforces "no floats, no
  negatives" in the one place it can't be bypassed.
- **`formatted` is a `@cached_property`** because it's derived, argument-free and pure — and the setter
  **must** invalidate it. That coupling is the real cost of caching on a mutable object, and it's why
  `cached_property` is safest on effectively-immutable objects.
- **`total_ordering`** removes three near-identical methods; `__eq__` returning `NotImplemented`
  (rather than `False`) lets Python try the reflected operation.
- **`__hash__` is restored explicitly** because defining `__eq__` sets `__hash__ = None`. Forgetting
  this is how a class silently stops working as a dict key.
- **`lru_cache` appears nowhere**, deliberately: every candidate here either depends on `self`
  (→ `cached_property`) or is a factory. Putting `@lru_cache` on `formatted` would leak every `Money`
  object ever formatted — Q7.

---

## Hands-on drills

1. Write the `Event.from_json` / `from_json_broken` pair, subclass it, and watch the `@staticmethod`
   version return the wrong type. Then call a subclass-only method on the result.
2. Print `type(obj.m)`, `type(Cls.m)`, `obj.m.__self__` and `obj.m.__func__` for an instance, class and
   static method. Then call `Cls.m(obj)` directly.
3. Add a `@classmethod set_x` that writes `cls.x`, call it on a subclass, and confirm the parent's
   value is untouched. Explain the read/write asymmetry in one sentence.
4. Give a class a `@property` that prints `"QUERY"`. Put three instances in a list and call `repr()` on
   the list. Count the lines — that's the hidden-cost argument.
5. Convert that property to `@cached_property`, then add `__slots__` and read the `TypeError`. Decide
   which you'd give up.
6. Add a setter to a class with a `@cached_property` derived from the same field. Change the field and
   observe the stale cached value. Then add the `__dict__.pop(...)` invalidation.
7. Reproduce the `lru_cache`-on-a-method leak with `weakref.ref` and `gc.collect()`. Then fix it four
   ways and compare.
8. Stack `@classmethod` over `@property` and print the result on your Python version. If it returns a
   bound method, write the one-sentence review comment that rejects it.
9. Swap `@property` and `@abstractmethod` on an abstract property, omit it in the subclass, and confirm
   it instantiates anyway.
10. Replace a five-branch `isinstance` ladder with `@singledispatchmethod`. Then register a handler for
    a type you don't own, which is the thing the ladder can't do.
11. Build a `@dataclass(frozen=True)` with a `list` field and try to use it as a dict key. Then fix it
    three ways (tuple, `field(hash=False)`, `frozenset`).
12. Write a singleton via `__new__` that sets `self.count = 0` in `__init__`. Call it twice,
    incrementing in between, and watch the state reset.
13. Do the `Money` exercise at the bottom of
    [`16_methods_and_builtin_decorators.py`](../01_python_core/16_methods_and_builtin_decorators.py)
    without looking at the worked example above.

---

## The 60-second spoken answer

> "The only difference between the three method types is what gets prepended as the first argument: an
> instance method gets the object, a `@classmethod` gets the class, a `@staticmethod` gets nothing. All
> three are descriptors — `function.__get__` returns a method bound to the instance,
> `classmethod.__get__` binds the class, `staticmethod.__get__` hands back the plain function — and
> that's the entire mechanism. My decision rule is to ask what the method needs: instance data, the
> class, or neither.
>
> The important thing about `@classmethod` is that `cls` is the *actual* class, so a factory like
> `from_json` returns the subclass when it's called on a subclass. That's why I use it for named
> constructors instead of a `@staticmethod` — a static factory has to hardcode its class name, so every
> subclass silently gets the wrong type back, and it fails far away from the call. It's the same `cls`
> trick that makes `dict.fromkeys()` work on a dict subclass.
>
> `@staticmethod` I use when something belongs to the class conceptually, or when a subclass might
> override it — and that's the part people miss: a `@staticmethod` is inherited and genuinely
> overridden, unlike a Java `static`. Otherwise a module-level function is simpler.
>
> `@property` turns a method into attribute access, with an optional setter for validation. The key
> point versus Java is that I never write `get_x`/`set_x` — I expose a plain attribute and promote it to
> a property the day I need logic, and no caller changes. But a property must be cheap and must not
> raise, because `obj.x` looks free: an expensive property turns a loop into N queries, and even a
> `repr()` or a debugger triggers it. If it's expensive, I make it an explicit method or a
> `@cached_property`.
>
> `@cached_property` computes once per instance and then overwrites itself in the instance `__dict__`,
> so you invalidate it with `del obj.attr` — and if the underlying field has a setter, that setter
> *must* clear it. It needs a `__dict__`, so it can't coexist with `__slots__`, and since 3.12 it has no
> lock, so two threads can both compute it. `@lru_cache` is for pure functions keyed by hashable
> arguments — and never on a method, because the cache lives on the class and keys on `self`, so it
> keeps every instance alive forever. That's a real leak I'd flag in review; the fix is
> `cached_property`, or hoisting the pure part into a static function.
>
> Two ordering traps: `@abstractmethod` must be the innermost decorator or the abstractness is silently
> lost, and `@classmethod` stacked on `@property` worked on 3.9 to 3.12 but was removed in 3.13 — and it
> doesn't raise, it just returns a bound method instead of the value, which is harder to debug than an
> error. For a class-level computed value I'd use a plain classmethod and call it.
>
> Beyond those: `@singledispatchmethod` for type-based dispatch since Python has no overloading,
> `@total_ordering` to fill in comparisons from `__eq__` and `__lt__`, and `@dataclass` to generate
> `__init__`, `__repr__` and `__eq__` — remembering that `frozen=True` gives you `__hash__` but a
> mutable field still makes instances unhashable, and that defining `__eq__` sets `__hash__` to `None`
> unless you restore it."
