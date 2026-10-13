# Deep Dive 06 — OOP in Depth (Multiple / Multilevel Inheritance, MRO)

> Runnable companion: [`01_python_core/07_oop_inheritance_mro.py`](../01_python_core/07_oop_inheritance_mro.py)
> Related deep dives: [Descriptors & metaclasses](05_context_managers_descriptors_metaclasses.md) ·
> [Java bridge](21_java_to_python_bridge.md) · [Framework development](11_python_framework_development.md)

## What interviewers are actually probing

With a Java background on your CV, this section is where the interviewer checks whether you
**translated** or merely **transliterated**. Java has single inheritance plus interfaces; Python has
real multiple inheritance, which means it needs the **MRO** — and the MRO is the single highest-value
thing to be fluent in here.

Expect: the four pillars (briefly), instance/class/static methods, abstract classes, and then a hard
pivot into **C3 linearisation, the diamond problem, what `super()` really does, and cooperative
multiple inheritance**. Being able to *write out an MRO by hand* and explain `super()` as "next in
the MRO, not the parent" is the differentiator.

---

## Must-know points

- **Pillars**: encapsulation, abstraction, inheritance, polymorphism — Python does all four, but by
  convention and duck typing rather than by compiler enforcement.
- **MRO** = the order Python searches classes for an attribute. Inspect with `Cls.__mro__` or
  `Cls.mro()`.
- **`super()` goes to the NEXT class in the MRO of `type(self)`** — *not* necessarily the literal
  parent. This is the crux.
- **Cooperative multiple inheritance**: every class calls `super()` and accepts `**kwargs`.
- **Python has no method overloading.** The last definition wins. Emulate with defaults, `*args`, or
  `functools.singledispatch`.
- **Prefer composition and thin mixins** over deep hierarchies.

---

## Interview questions and full answers

### Q1. Explain the four pillars of OOP with Python examples.

**Encapsulation** — bundle data with the behaviour that operates on it, and hide internals. Python
enforces nothing; it uses convention:
- `_x` — "internal, don't touch" (honoured by convention and by `from x import *`).
- `__x` — **name mangling** to `_ClassName__x`, which prevents *accidental* clashes in subclasses.
  It is not access control (see Q10).
- `@property` — the real tool, for controlled access with validation.

**Abstraction** — expose a simple interface, hide the detail. `abc.ABC` + `@abstractmethod` for
nominal typing, `typing.Protocol` for structural.

**Inheritance** — reuse and specialise. Python supports both multilevel and multiple.

**Polymorphism** — Python leans on **duck typing**: any object with the right methods works, no
common base class required. Plus method overriding and operator overloading via dunders.

```python
class Duck:
    def speak(self): return "quack"

class Robot:
    def speak(self): return "beep"

for thing in (Duck(), Robot()):          # no shared base class needed
    print(thing.speak())
```

> **Java contrast.** Java polymorphism requires a shared type (`interface Speaker`). Python requires
> only a shared *shape*. `typing.Protocol` gives you the static-checking benefit without the runtime
> coupling — it's Python's structural answer to Java's nominal interfaces.

---

### Q2. What is the difference between multilevel and multiple inheritance?

- **Multilevel** — a *chain*: `C(B)`, `B(A)`. A grandparent relationship. Java has this.
- **Multiple** — one class inherits from **two or more bases at once**: `class C(A, B)`. Java does
  *not* have this for classes (only multiple interfaces), which is why the MRO has no Java analogue.

```python
# Multilevel: Animal -> Mammal -> Dog
class Animal:
    def breathe(self): return "breathing"
class Mammal(Animal): pass
class Dog(Mammal): pass

# Multiple: Duck inherits from both
class Flyer:
    def move(self): return "fly"
class Swimmer:
    def move(self): return "swim"
class Duck(Flyer, Swimmer): pass

print(Dog().breathe())     # 'breathing' — found two levels up
print(Duck().move())       # 'fly' — Flyer is first in the MRO
```

Multiple inheritance introduces the **diamond problem**, which Python resolves deterministically with
the MRO (Q3–Q4).

---

### Q3. What is the MRO and how does C3 linearisation work?

The **Method Resolution Order** is the flat, ordered list of classes Python searches when looking up
an attribute. It's computed **once at class creation** and cached on `__mro__`.

Python uses **C3 linearisation**, which guarantees three properties:

1. **A class precedes its parents.**
2. **Parents keep the order you listed them in** (`class D(B, C)` → B before C).
3. **Monotonicity**: the ordering is consistent across the whole hierarchy — a class's MRO is
   compatible with the MRO of every one of its subclasses.

If no order satisfying all three exists, Python raises `TypeError: Cannot create a consistent method
resolution order (MRO)` — **at class creation time**, not at call time.

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print([k.__name__ for k in D.__mro__])    # ['D', 'B', 'C', 'A', 'object']
```

**How to compute it by hand** — the merge algorithm. `L[D]` = D + merge of the parents' linearisations
plus the list of parents. Take the head of the first list; if it doesn't appear in the *tail* of any
other list, accept it and remove it everywhere; otherwise try the next list's head.

```
L[A] = A, object
L[B] = B, A, object
L[C] = C, A, object
L[D] = D + merge(L[B], L[C], [B, C])
     = D + merge([B,A,object], [C,A,object], [B,C])
       take B  -> not in any tail          -> accept
     = D, B + merge([A,object], [C,A,object], [C])
       take A  -> IS in the tail of [C,A,object] -> skip
       take C  -> not in any tail          -> accept
     = D, B, C + merge([A,object], [A,object])
       take A  -> accept
     = D, B, C, A, object
```

The "A is in a tail, skip it" step is exactly what stops `A` running before `C`, which is what makes
the diamond work.

An MRO that **cannot** be built:

```python
class X: pass
class Y: pass
class P(X, Y): pass
class Q(Y, X): pass
# class Z(P, Q): pass
# -> TypeError: Cannot create a consistent MRO for bases P, Q
```

P requires X-before-Y, Q requires Y-before-X. No consistent order exists, so Python refuses.

---

### Q4. Explain the diamond problem and how Python solves it.

The diamond: `D` inherits `B` and `C`, both of which inherit `A`. A naive depth-first search would
reach `A` twice (once through B, once through C), calling `A`'s method **twice** — which corrupts
state in any `__init__` that increments a counter, opens a connection, or appends to a list.

Python's MRO lists **`A` exactly once, after both `B` and `C`**, and `super()` walks that flat list —
so every class's method runs exactly once, in a well-defined order.

```python
class A:
    def hello(self): print("A")

class B(A):
    def hello(self): print("B"); super().hello()

class C(A):
    def hello(self): print("C"); super().hello()

class D(B, C):
    def hello(self): print("D"); super().hello()

D().hello()
# D
# B
# C        <- super() inside B went to C, NOT to A
# A        <- A runs exactly ONCE
```

Trace it against `D.__mro__ == [D, B, C, A, object]`: each `super()` advances one step along that
list. **`super()` in `B` resolves to `C`**, even though `C` is not `B`'s parent and `B` knows nothing
about `C`. That is the whole point of the word *cooperative* — the chain is assembled by the MRO of
the *instance's* type, not by the static class hierarchy.

> **Java contrast.** Java avoids this by banning multiple class inheritance. Default methods in
> interfaces reintroduce a limited version, which Java resolves by forcing you to disambiguate
> explicitly (`Interface.super.method()`). Python resolves it automatically via C3.

---

### Q5. What exactly does `super()` do?

`super()` returns a **proxy object** that delegates attribute lookup to the class **after the current
one in the MRO of `type(self)`**.

The no-argument form `super()` is sugar (PEP 3135) for `super(__class__, self)`, where `__class__` is
filled in by the compiler as a closure cell — which is why it only works lexically inside a class
body.

```python
super()                    # modern: super(CurrentClass, self)
super(B, self)             # explicit: start searching AFTER B in type(self).__mro__
super(B, SomeSubclass)     # unbound: for classmethods
```

**The three things people get wrong:**

1. **"`super()` calls the parent."** No — it calls the *next class in the MRO*, which depends on the
   **instance's** type, not on where the call is written. In the diamond above, `B.hello`'s `super()`
   is `C` for a `D` instance and `A` for a plain `B` instance. The *same line of code* resolves
   differently.

```python
B().hello()      # B, A     <- super() in B went to A
D().hello()      # D, B, C, A  <- the same super() in B went to C
```

2. **Mixing `super()` with explicit `Parent.method(self)`** breaks the chain. Explicit calls jump
   directly to that class and skip everything between, so a cooperative chain can double-call or
   skip classes.

3. **Forgetting `super().__init__()`** means the rest of the chain never initialises. In a diamond,
   the class you *didn't* think about silently never runs.

---

### Q6. How do you design cooperative `__init__` methods for multiple inheritance?

The contract that makes multiple inheritance work in practice:

- Every class in the hierarchy **accepts `**kwargs`**.
- Each **pops (or declares) only the arguments it owns**.
- Each **passes the rest up with `super().__init__(**kwargs)`**.
- The chain terminates at `object`, which accepts **no** extra arguments — so if anything is left
  over, you get a loud `TypeError` instead of silently-dropped configuration.

```python
class Base:
    def __init__(self, **kw):
        super().__init__(**kw)           # terminates at object

class Timestamped(Base):
    def __init__(self, created=None, **kw):
        self.created = created
        super().__init__(**kw)           # pass the rest along

class Named(Base):
    def __init__(self, name="", **kw):
        self.name = name
        super().__init__(**kw)

class Product(Timestamped, Named):
    pass

p = Product(name="pen", created="2026-10-01")
print(p.name, p.created)                 # pen 2026-10-01
print([c.__name__ for c in Product.__mro__])
# ['Product', 'Timestamped', 'Named', 'Base', 'object']
```

`Timestamped.__init__` consumes `created` and forwards `name` onward without knowing what it is;
`Named` picks it up. Neither class imports or references the other.

**What breaks without the contract** — a class that takes positional args and doesn't forward:

```python
class Bad(Base):
    def __init__(self, x):               # no **kw, no super() forwarding
        self.x = x

class Broken(Bad, Named): pass
# Broken(x=1, name="pen") -> TypeError: __init__() got an unexpected keyword argument 'name'
```

This is why libraries designed for mixin use (Django's class-based views, DRF) are religious about
`**kwargs` + `super()`.

---

### Q7. What is a mixin? Give an example.

A **mixin** is a small class that adds **one focused capability**, is not meant to be instantiated on
its own, usually holds no state of its own, and is combined via multiple inheritance.

**Place mixins to the LEFT of the main base class**, so their methods come earlier in the MRO and
therefore take precedence — that's the whole point of mixing them in.

```python
import json

class JsonMixin:
    def to_json(self):
        return json.dumps(self.__dict__)

class ReprMixin:
    def __repr__(self):
        return f"{type(self).__name__}({self.__dict__})"

class User(JsonMixin, ReprMixin):        # mixins first
    def __init__(self, name):
        self.name = name

u = User("ravi")
print(u.to_json())    # {"name": "ravi"}
print(repr(u))        # User({'name': 'ravi'})
```

Real examples: Django's `LoginRequiredMixin`, `PermissionRequiredMixin`; DRF's `ListModelMixin`,
`CreateModelMixin`.

**Where mixins go wrong:** when they carry state, depend on attributes they don't define, or stack
five deep. At that point the MRO becomes the only documentation of behaviour, and nobody reads it.
Three mixins is plenty; past that, prefer composition.

> **Java contrast.** A mixin ≈ an interface with `default` methods. The key difference is that a
> Python mixin can also hold and mutate state, which is more powerful and more dangerous.

---

### Q8. Instance method vs `@classmethod` vs `@staticmethod`?

| | Receives | Sees | Typical use |
|---|---|---|---|
| Instance method | `self` | Instance + class state | Normal behaviour |
| `@classmethod` | `cls` | Class state; **respects subclassing** | Alternative constructors, factories, registries |
| `@staticmethod` | nothing | Neither | A pure helper that belongs namespaced in the class |

```python
class Date:
    def __init__(self, y, m, d):
        self.y, self.m, self.d = y, m, d

    @classmethod
    def from_str(cls, s):
        return cls(*map(int, s.split("-")))     # cls, not Date — see below

    @staticmethod
    def is_leap(y):
        return y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)

print(Date.from_str("2026-09-30").y)   # 2026
print(Date.is_leap(2028))              # True
```

**Why `cls` and not `Date` inside `from_str`** — this is the point of the question:

```python
class USDate(Date):
    def __str__(self): return f"{self.m}/{self.d}/{self.y}"

d = USDate.from_str("2026-09-30")
print(type(d))     # <class 'USDate'>  — because we used cls
                   # hardcoding Date would have returned a Date, losing the subclass
```

`classmethod` is also the idiomatic **alternative constructor**, since Python has no constructor
overloading: `Date(y, m, d)`, `Date.from_str(...)`, `Date.today()`.

A `staticmethod` that never touches `cls` or `self` is often better as a module-level function —
keep it in the class only when it's conceptually part of the class's API.

---

### Q9. How do you create an abstract class in Python?

Inherit from `abc.ABC` and decorate methods with `@abstractmethod`. The class **cannot be
instantiated** until a subclass implements every abstract method — and the error is raised at
instantiation.

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount: float) -> str: ...

    @abstractmethod
    def refund(self, txn_id: str) -> bool: ...

    def charge_with_log(self, amount):        # concrete methods are allowed
        result = self.charge(amount)
        print(f"charged {amount}: {result}")
        return result

class Razorpay(PaymentGateway):
    def charge(self, amount): return f"rzp_{amount}"
    def refund(self, txn_id): return True

# PaymentGateway()  -> TypeError: Can't instantiate abstract class PaymentGateway
#                      with abstract methods charge, refund
Razorpay().charge_with_log(100)
```

You can stack `@abstractmethod` with `@property`, `@classmethod` and `@staticmethod` —
`@abstractmethod` must be **innermost**:

```python
class Repo(ABC):
    @property
    @abstractmethod
    def table_name(self) -> str: ...
```

**The structural alternative — `typing.Protocol`** — needs no inheritance at all. The implementer
never imports your protocol; a static checker verifies the shape:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsCharge(Protocol):
    def charge(self, amount: float) -> str: ...

def process(gateway: SupportsCharge, amt):    # mypy checks any argument structurally
    return gateway.charge(amt)
```

**Choosing:** `ABC` when you want to *share implementation* and enforce the contract at runtime;
`Protocol` when you want to accept third-party classes you can't modify, or to type a duck-typed API.
`Protocol` is the closer match to how Python actually works.

---

### Q10. How does Python implement encapsulation? What is name mangling?

**Python has no private members.** It has conventions and one mechanical trick.

- **`_single_underscore`** — pure convention meaning "internal API, may change". Tooling honours it
  (`from module import *` skips it, IDEs de-emphasise it), nothing enforces it.
- **`__double_underscore`** (no trailing underscores) — triggers **name mangling**: inside the class
  body the compiler rewrites `self.__x` to `self._ClassName__x`.

**Mangling exists to prevent accidental collisions in subclasses, not to provide security:**

```python
class Base:
    def __init__(self):
        self.__id = 1          # stored as _Base__id
    def show(self): return self.__id

class Child(Base):
    def __init__(self):
        super().__init__()
        self.__id = 2          # stored as _Child__id — does NOT clobber Base's

c = Child()
print(c.show())                 # 1 — Base still sees its own
print(c.__dict__)               # {'_Base__id': 1, '_Child__id': 2}
print(c._Base__id)              # 1 — trivially accessible; nothing is hidden
```

Without mangling, `Child.__id = 2` would silently break `Base.show()`. That is the entire purpose.

**The real encapsulation tool is `@property`**, which lets you start with a plain public attribute
and add validation later *without breaking any caller* — which is exactly why Python programmers
don't write pre-emptive getters and setters.

> **Java contrast.** `private` is compiler-enforced (though reflection defeats it). Python's stance
> is "we're all consenting adults" — mark intent, trust the caller, and rely on tests rather than
> access modifiers. Writing `getName()`/`setName()` in Python is the most common Java-accent tell.

---

### Q11. What are dunder (magic) methods? Implement a few.

Special methods Python calls for built-in operations. They're how you make your class behave like a
built-in type — and Python's polymorphism is largely *protocol*-based, so implementing the right
dunder is how you opt into `len()`, `in`, `for`, `+`, `with`, `[]` and so on.

| Group | Methods |
|---|---|
| Construction | `__new__`, `__init__`, `__del__` |
| Representation | `__repr__` (unambiguous, for devs), `__str__` (readable, for users), `__format__` |
| Comparison | `__eq__`, `__lt__`, `__le__`, `__gt__`, `__ge__`, `__ne__`, `__hash__` |
| Container | `__len__`, `__getitem__`, `__setitem__`, `__contains__`, `__iter__` |
| Numeric | `__add__`, `__sub__`, `__mul__`, `__radd__`, `__iadd__` |
| Callable / context | `__call__`, `__enter__`, `__exit__` |
| Attributes | `__getattr__`, `__getattribute__`, `__setattr__`, `__dir__` |

```python
from functools import total_ordering

@total_ordering                       # generates <=, >, >= from __eq__ and __lt__
class Money:
    def __init__(self, amt): self.amt = amt

    def __repr__(self):  return f"Money({self.amt})"      # for developers
    def __str__(self):   return f"₹{self.amt:.2f}"        # for users
    def __add__(self, other):  return Money(self.amt + other.amt)
    def __radd__(self, other):                            # enables sum([...])
        return self if other == 0 else Money(self.amt + other.amt)
    def __eq__(self, other):
        return isinstance(other, Money) and self.amt == other.amt
    def __lt__(self, other): return self.amt < other.amt
    def __hash__(self):      return hash(self.amt)        # required: we defined __eq__
    def __bool__(self):      return self.amt != 0

print(Money(5) + Money(7))            # Money(12)
print(str(Money(5)))                  # ₹5.00
print(sum([Money(1), Money(2)]))      # Money(3)  — thanks to __radd__
print(sorted([Money(3), Money(1)]))   # [Money(1), Money(3)]
```

**Two rules to state:** always define `__repr__` (it's the fallback for `__str__` and what you see in
tracebacks and debuggers), and if you define `__eq__` you **must** define `__hash__` or your class
becomes unhashable — see
[Deep Dive 01 Q4](01_data_structures_collections.md#q4-what-makes-an-object-usable-as-a-dict-key-or-set-element).

---

### Q12. Composition vs inheritance — which do you prefer and why?

**Composition, by default.** The reasoning:

**Inheritance** models *is-a* and couples the child to the parent's **implementation**, not just its
interface. Change the parent and every subclass can break — the "fragile base class" problem. Deep
hierarchies are hard to test in isolation because you inherit the whole chain's behaviour whether you
want it or not.

**Composition** models *has-a*: the object holds collaborators and delegates. That gives you:

- **Testability** — inject a fake collaborator; no need to subclass anything.
- **Runtime flexibility** — swap the collaborator without changing the type.
- **Explicit dependencies** — they're in `__init__`, visible in the signature.

```python
# Inheritance — OrderService IS-A KafkaProducer? No. And you can't test without Kafka.
class OrderService(KafkaProducer):
    def place(self, order):
        self.send("orders", order)

# Composition — OrderService HAS-A publisher. Inject a fake in tests.
class OrderService:
    def __init__(self, publisher, repo):
        self.publisher = publisher
        self.repo = repo

    def place(self, order):
        self.repo.save(order)
        self.publisher.send("orders", order)

svc = OrderService(publisher=FakePublisher(), repo=InMemoryRepo())   # trivially testable
```

**Use inheritance when:** there's a genuine subtype relationship, you're implementing an
`ABC`/framework contract, or you're adding a small focused mixin. **Use composition otherwise** —
which is most of the time. This is the architecture the [FastAPI app in this
repo](../05_web_apis_fastapi/app/services.py) uses: services receive repositories, they don't inherit
from them.

---

### Q13. What is `__slots__` and when would you use it?

Declaring `__slots__ = ("x", "y")` replaces the per-instance `__dict__` with a fixed array of
descriptor-backed slots. Two benefits:

- **Memory**: typically **40–50% less per instance**, because you drop the dict (which is at least
  ~104 bytes even when small).
- **Speed**: attribute access is marginally faster (array index rather than hash lookup).

```python
import sys

class WithDict:
    def __init__(self, x, y): self.x, self.y = x, y

class WithSlots:
    __slots__ = ("x", "y")
    def __init__(self, x, y): self.x, self.y = x, y

a, b = WithDict(1, 2), WithSlots(1, 2)
print(sys.getsizeof(a) + sys.getsizeof(a.__dict__))   # ~152 bytes
print(sys.getsizeof(b))                               # ~56 bytes
# b.z = 3   -> AttributeError: 'WithSlots' object has no attribute 'z'
```

**Use it when you create millions of small objects** — parsed records, graph nodes, simulation
particles, market ticks. At 10 million instances the difference is gigabytes.

**Trade-offs to state:**

- No dynamic attributes (that's the point, but it surprises people).
- **No `__weakref__`** unless you add it to the slots explicitly.
- **Multiple inheritance is restricted** — two bases with non-empty `__slots__` raise
  `TypeError: multiple bases have instance lay-out conflict`.
- **`cached_property` and anything writing to `__dict__` stops working** (see
  [descriptor precedence](05_context_managers_descriptors_metaclasses.md#q7-data-descriptor-vs-non-data-descriptor--how-does-lookup-precedence-work)).
- A subclass without its own `__slots__` silently regains a `__dict__`, undoing the saving.

The modern shortcut: `@dataclass(slots=True)` (3.10+) gives you slots plus generated methods.

---

### Q14. Method overriding vs overloading in Python?

**Overriding** — a subclass redefines a parent method. Fully supported; it's runtime polymorphism
driven by the MRO.

**Overloading** (several methods with the same name, different signatures) — **does not exist**.
Python resolves names in a single namespace, so the last definition simply replaces the earlier ones:

```python
class C:
    def f(self, a): return "one arg"
    def f(self, a, b): return "two args"    # silently replaces the first

# C().f(1) -> TypeError: f() missing 1 required positional argument: 'b'
```

Four idiomatic emulations:

```python
# 1. Default and variadic arguments — covers most real cases
def area(w, h=None):
    return w * w if h is None else w * h

# 2. functools.singledispatch — dispatch on the FIRST argument's type
from functools import singledispatch

@singledispatch
def describe(value):
    return f"unknown: {value!r}"

@describe.register
def _(value: int):  return f"int {value}"

@describe.register
def _(value: list): return f"list of {len(value)}"

# 3. singledispatchmethod — the same, for methods (dispatches on the 2nd arg, after self)
from functools import singledispatchmethod

class Formatter:
    @singledispatchmethod
    def fmt(self, value): raise NotImplementedError

    @fmt.register
    def _(self, value: int): return f"{value:d}"

    @fmt.register
    def _(self, value: float): return f"{value:.2f}"

# 4. typing.overload — declarations for the TYPE CHECKER only; zero runtime effect
from typing import overload

@overload
def get(key: str) -> str: ...
@overload
def get(key: int) -> bytes: ...
def get(key):                      # the single real implementation
    ...
```

`@overload` is the one people misuse — it does **nothing** at runtime. The bodies must be `...` and a
single concrete implementation must follow.

> **Java contrast.** Java picks an overload at **compile time** from static argument types.
> `singledispatch` picks at **runtime** from the actual type — closer to double dispatch / the
> visitor pattern than to Java overloading.

---

## Worked example — abstract base + mixins + cooperative `super()`

Everything above in one piece: an ABC defining the contract, two mixins adding orthogonal
capabilities, and an MRO you should be able to predict before running it.

```python
from abc import ABC, abstractmethod
import logging

logging.basicConfig(level=logging.INFO)

class LoggingMixin:
    def log(self, msg):
        logging.getLogger(type(self).__name__).info(msg)

class RetryMixin:
    max_retries = 3

    def run_with_retry(self, *args):
        for i in range(self.max_retries):
            try:
                return self.process(*args)          # provided by the concrete class
            except Exception as e:
                self.log(f"retry {i + 1}/{self.max_retries}: {e}")
        raise RuntimeError("gave up after retries")

class Handler(ABC):
    @abstractmethod
    def process(self, event): ...

class OrderHandler(LoggingMixin, RetryMixin, Handler):
    def process(self, event):
        self.log(f"processing {event}")
        return event["id"]

print([c.__name__ for c in OrderHandler.__mro__])
# ['OrderHandler', 'LoggingMixin', 'RetryMixin', 'Handler', 'ABC', 'object']

print(OrderHandler().run_with_retry({"id": 42}))    # 42
```

**Things to notice, and to say out loud:**

- `RetryMixin` calls `self.process()` and `self.log()` — **neither of which it defines**. It relies on
  the MRO supplying them. That's powerful and it's the danger: the mixin has an *implicit contract*
  that nothing enforces. A stricter design would make `RetryMixin` inherit the ABC too, or use a
  `Protocol` to document the requirement.
- Mixin order matters: `LoggingMixin` first means its `log` wins if `RetryMixin` also defined one.
- `Handler` being an ABC means forgetting `process` fails at instantiation, not in production.

---

## Hands-on drills

1. Build the diamond from Q4 and print `D.__mro__`. Then derive the same MRO **by hand** with the C3
   merge algorithm and check your work.
2. Construct an impossible MRO (`P(X,Y)`, `Q(Y,X)`, `Z(P,Q)`) and read the `TypeError` carefully.
3. Call `B().hello()` and `D().hello()` with the Q4 classes. Explain why the identical `super()` line
   inside `B` reaches two different classes.
4. Write a four-class cooperative `__init__` chain with `**kwargs`. Then remove `**kw` from one class
   and observe exactly which argument gets lost and where the `TypeError` surfaces.
5. Put a mixin to the *right* of the main base instead of the left and explain why its method stops
   winning.
6. Write a `Money` class with `__eq__` but **no** `__hash__`. Put it in a set and read the error.
   Add `__hash__` and confirm.
7. Measure `__slots__` savings: create 1,000,000 instances with and without, using `tracemalloc`.
   Then try to give one a new attribute.
8. Implement a shape hierarchy twice — once with an ABC, once with `typing.Protocol` — and argue
   which you'd ship.

---

## The 60-second spoken answer

> "Python has real multiple inheritance, so it needs an MRO — a C3 linearisation guaranteeing a class
> precedes its parents, parent order is preserved, and the ordering is monotonic; if no consistent
> order exists you get a `TypeError` at class creation. That's how the diamond problem is solved: the
> shared ancestor appears once, at the end, so it runs once. `super()` goes to the *next class in the
> MRO of the instance's type*, not the literal parent — inside `B`, `super()` reaches `C` when the
> instance is a `D`, which is what makes cooperative inheritance work. For that to hold, every class
> takes `**kwargs`, consumes what it owns, and forwards the rest, terminating at `object`. I use
> mixins for small orthogonal capabilities, placed left of the main base so they win in the MRO, but
> I default to composition — injecting collaborators keeps things testable, whereas inheritance
> couples me to the parent's implementation. Python has no overloading; I use defaults or
> `singledispatch`. And encapsulation is convention: `_x` is a hint, `__x` only name-mangles to avoid
> subclass collisions, and `@property` is the real tool since I can convert a public attribute to one
> later without breaking callers."
