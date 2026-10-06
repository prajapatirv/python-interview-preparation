# Deep Dive 23 — Abstract Base Classes, Interfaces and Protocols

> Runnable companion: [`01_python_core/13_abstract_base_classes.py`](../01_python_core/13_abstract_base_classes.py)
> Related deep dives: [06 — OOP and MRO](06_oop_inheritance_mro.md) ·
> [05 — Context managers, descriptors, metaclasses](05_context_managers_descriptors_metaclasses.md) ·
> [11 — Python framework development](11_python_framework_development.md) ·
> [21 — Java → Python bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

Everyone can recite "ABC means abstract base class, use `@abstractmethod`". What distinguishes a
senior answer is knowing **when a contract should be enforced at all**, and by which of the four
mechanisms Python gives you:

| Mechanism | Checked by | Checked when |
|---|---|---|
| **Duck typing** | production | when the method is first called |
| **`typing.Protocol`** | mypy / pyright | in CI, before merge |
| **ABC + `@abstractmethod`** | Python itself | at **instantiation** |
| **`__init_subclass__`** | your own code | at **class definition** (import time) |

The one-liner worth memorising: **an ABC is a promise checked by Python, a Protocol is a promise
checked by your type checker, and duck typing is a promise checked by production.**

The follow-up they're usually driving at is the honest limit: **an ABC only checks that NAMES
exist.** It never checks signatures or types. If you don't volunteer that, you look like you've only
read the docs.

---

## Must-know points

- `class X(ABC)` with an `@abstractmethod` **cannot be instantiated** — `TypeError` at construction,
  naming exactly which methods are missing. The class itself is importable and subclassable.
- An ABC is **not** an interface: it can hold concrete methods, state, and `__init__`. That is its
  main advantage over a Protocol (shared code → the **template-method** pattern).
- `__abstractmethods__` is a frozenset on the class listing what's still unimplemented.
- **Decorator order matters**: `@abstractmethod` must be the **innermost** decorator
  (`@property` above `@abstractmethod`). Reverse them and the abstractness is silently lost.
- An ABC checks **names only** — not signatures, not return types. A subclass with a wrong signature
  instantiates fine and fails at call time. A type checker catches it; `abc` does not.
- **`typing.Protocol`** = structural typing. Any class with matching members satisfies it, with no
  inheritance. Use it for code you don't own, and for narrow one-method contracts.
- `@runtime_checkable` enables `isinstance()` against a Protocol — but it checks **member names
  only**, so treat it as a smoke test, not a guarantee.
- `ABC.register(Cls)` makes `Cls` a **virtual subclass**: `isinstance`/`issubclass` pass, but it
  inherits **no code** and gets **no abstract-method check**.
- `collections.abc` gives you mixins: implement `__getitem__`/`__iter__`/`__len__` and inherit
  `get`, `keys`, `items`, `values`, `__contains__`, `__eq__` from `Mapping`.
- **`__init_subclass__`** validates subclasses at **class-creation** (import) time — earlier than an
  ABC, and much lighter than a metaclass.
- `ABC` is just `class ABC(metaclass=ABCMeta)`. Know that, and you know why
  `class X(ABC, SomeOtherMeta)` can produce a metaclass conflict.

---

## Interview questions and full answers

### Q1. What is an abstract base class and what problem does it solve?

An ABC defines a **contract that Python enforces at instantiation**. Any subclass that hasn't
implemented every `@abstractmethod` cannot be constructed:

```python
from abc import ABC, abstractmethod

class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount_cents: int, token: str) -> str:
        """Return a provider transaction id. Must raise on failure."""

    @abstractmethod
    def refund(self, transaction_id: str) -> bool: ...

class StripeGateway(PaymentGateway):
    def charge(self, amount_cents, token): return f"stripe_{amount_cents}"
    def refund(self, transaction_id): return True

class HalfFinished(PaymentGateway):
    def charge(self, amount_cents, token): return "oops"      # no refund()

StripeGateway()      # fine
HalfFinished()       # TypeError: Can't instantiate abstract class HalfFinished
                     # without an implementation for abstract method 'refund'
HalfFinished.__abstractmethods__       # frozenset({'refund'})
```

**The problem it solves is WHEN you find out.** Without the ABC, `HalfFinished` imports fine,
constructs fine, passes a smoke test that only calls `charge`, deploys — and throws
`AttributeError` the first time a customer requests a refund. With the ABC, the failure moves to
construction, which means your app fails at startup or your test suite fails on `Cls()` — both
*before* a customer is involved.

The second thing it solves is **documentation that cannot rot**. The abstract methods *are* the
contract, with the docstring explaining the invariants (`"must raise on failure"`, `"must be
idempotent"`). A plain base class with `raise NotImplementedError` bodies documents the same thing
but only fires when called.

**Why not `NotImplementedError`?** It's the weaker alternative:

```python
class PaymentGateway:
    def charge(self, amount, token): raise NotImplementedError
```

This class is instantiable, so the error surfaces at call time rather than construction time, and
nothing tells you *all* the methods you forgot — you discover them one production incident at a
time. Use it only when you genuinely want an optional hook. (It also has one legitimate niche: a
method that *most* subclasses needn't implement.)

---

### Q2. Is an ABC an interface?

**No, and this is the most useful thing to say about ABCs.** Java separates `interface` (contract
only) from `abstract class` (contract + shared code). Python has **one construct that does both** —
which is why an ABC is usually the right answer when you own the hierarchy.

The payoff is the **template-method pattern**: define the algorithm once in the ABC, let subclasses
fill in only the steps that vary.

```python
class ReportJob(ABC):
    def run(self):                        # the TEMPLATE — concrete, inherited, never overridden
        rows = self.fetch()
        cleaned = [r for r in rows if self.is_valid(r)]
        return self.render(cleaned)

    @abstractmethod
    def fetch(self) -> list: ...          # subclass MUST provide the source

    @abstractmethod
    def render(self, rows) -> str: ...    # subclass MUST provide the format

    def is_valid(self, row) -> bool:      # a HOOK: sane default, override only if needed
        return row is not None

class CsvOrderReport(ReportJob):
    def fetch(self):  return [{"id": 1}, None, {"id": 2}]
    def render(self, rows): return ",".join(str(r["id"]) for r in rows)
```

Three categories of member, and naming them is what shows design maturity:

- **template** (`run`) — the invariant algorithm. Concrete; subclasses don't touch it.
- **abstract** (`fetch`, `render`) — the required variation points.
- **hook** (`is_valid`) — optional variation with a working default.

This is exactly the shape of `unittest.TestCase` (`run` orchestrates `setUp`/`test`/`tearDown`),
of a Kafka consumer base class (`poll` → `handle` → `commit`), and of the repository base in
[`12_framework_internals/01_repository_pattern.py`](../12_framework_internals/01_repository_pattern.py).

A Protocol **cannot** do this — it carries no implementation. So the rule is: **need to share code →
ABC. Only need a shape → Protocol.**

---

### Q3. How do you make a property, classmethod or staticmethod abstract?

Stack the decorators with `@abstractmethod` **innermost**:

```python
class Connector(ABC):
    @property
    @abstractmethod                   # innermost — the ORDER IS LOAD-BEARING
    def dsn(self) -> str: ...

    @classmethod
    @abstractmethod
    def from_env(cls) -> "Connector": ...

    @staticmethod
    @abstractmethod
    def driver_name() -> str: ...
```

Get it backwards (`@abstractmethod` on top of `@property`) and **the abstractness is silently
lost** — `property` wraps the already-marked function and the resulting descriptor no longer carries
`__isabstractmethod__`, so `__abstractmethods__` is empty and any subclass instantiates. No warning.
That silence is why interviewers ask.

Second point worth making: **Python checks the NAME, not the kind.** A plain class attribute
satisfies an abstract property:

```python
class PostgresConnector(Connector):
    dsn = "postgresql://localhost/app"       # a plain attribute, not a property — accepted
    @classmethod
    def from_env(cls): return cls()
    @staticmethod
    def driver_name(): return "psycopg"
```

That's a feature: the base declares *"instances must expose a `dsn`"* and leaves the subclass free
to make it a constant, a computed property, or a `functools.cached_property`. It's also why
`abstractproperty`/`abstractclassmethod`/`abstractstaticmethod` were deprecated in 3.3 — the stacked
form subsumes them.

---

### Q4. What does an ABC *not* check? (The limits.)

**It checks that the names exist on the class at instantiation. That's all.** Specifically it does
not check:

```python
class WrongSignature(PaymentGateway):
    def charge(self):                                  # no amount, no token
        return "nope"
    def refund(self, transaction_id, extra_required):   # extra required arg
        return False

w = WrongSignature()          # ✅ instantiates happily
w.charge(500, "tok")          # ❌ TypeError, only now:
                              # charge() takes 1 positional argument but 3 were given
```

The full list of what `abc` will not catch:

- **Signatures** — arity, parameter names, keyword-only-ness.
- **Types** — a `charge` returning `None` instead of `str`.
- **Semantics** — a `refund` that doesn't actually refund, or isn't idempotent.
- **Timing** — nothing is checked until something calls `Cls()`. A class that's imported but never
  instantiated in your tests is never verified.
- **Liskov violations** — narrowing an accepted type, or raising where the base promised not to.

So the complete answer to "how do you enforce a contract" is **three layers, not one**:

1. **ABC** — the names exist (runtime, at construction).
2. **mypy/pyright in CI** — the signatures and types match, *and* overrides are LSP-compatible.
   `mypy` flags an incompatible override as `Signature of "charge" incompatible with supertype`.
3. **Tests** — the semantics hold. The strong version is a **shared contract test suite** that
   every implementation must pass:

```python
# tests/contract/test_payment_gateway.py — parametrised over EVERY implementation
@pytest.mark.parametrize("gateway_cls", [StripeGateway, AdyenGateway, FakeGateway])
class TestGatewayContract:
    def test_charge_returns_a_transaction_id(self, gateway_cls):
        assert isinstance(gateway_cls().charge(100, "tok"), str)

    def test_refunding_twice_is_idempotent(self, gateway_cls):
        g = gateway_cls(); txn = g.charge(100, "tok")
        assert g.refund(txn) and g.refund(txn) is not None   # the SEMANTIC the ABC can't state
```

Mentioning that suite is the strongest thing you can say here: it's how you enforce the parts of a
contract that no type system expresses, and it's how you keep a `FakeGateway` used in tests honest
about the real one's behaviour. See [`04_testing_tdd/`](../04_testing_tdd/).

---

### Q5. ABC vs `typing.Protocol` — when do you use each?

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class SupportsCharge(Protocol):
    def charge(self, amount_cents: int, token: str) -> str: ...

class LegacyVendorClient:              # imports nothing of ours, written years ago
    def charge(self, amount_cents, token): return f"legacy_{amount_cents}"

def take_payment(gateway: SupportsCharge, amount: int) -> str:
    return gateway.charge(amount, "tok")

take_payment(LegacyVendorClient(), 250)          # ✅ type-checks, no inheritance anywhere
```

**Nominal vs structural** is the distinction. An ABC is *nominal*: you satisfy it by **declaring**
you do (subclassing or `register()`). A Protocol is *structural*: you satisfy it by **having the
right shape**. It's static duck typing — "if it quacks, mypy agrees it's a duck".

| | ABC | Protocol |
|---|---|---|
| Satisfied by | explicit subclassing (or `register`) | having matching members |
| Can carry implementation | **yes** — the main reason to choose it | no (default bodies exist but are rarely useful) |
| Enforced at | runtime, at instantiation | **static check only**, unless `@runtime_checkable` |
| Works on code you don't own | only via `register()` | **yes, natively** |
| Best for | your own hierarchy, shared behaviour, plugins you define | adapting third-party/legacy types, narrow 1-method contracts, dependency boundaries |
| Costs | coupling: implementers must import your base | nothing at runtime — which also means no runtime guarantee |

**How I choose, stated as rules:**

- **I own the hierarchy and want shared code** → ABC. (`ReportJob`, `BaseRepository`, a plugin base.)
- **I'm describing what my function NEEDS from its argument** → Protocol. This is the better default
  for dependency boundaries, because it inverts the dependency: the *consumer* defines the interface
  it needs, so neither side imports the other. That's the Python spelling of the Dependency
  Inversion Principle.
- **The contract is one method** → Protocol, or honestly just pass the function.
- **I need `isinstance` to dispatch at runtime** → ABC (`register()` if the class isn't mine).

**The `@runtime_checkable` caveat you must state:** `isinstance()` against a Protocol checks **member
names only** — not signatures, and (for non-data protocols) not even that they're callable with the
right arity:

```python
class Fake:
    def charge(self): pass             # wrong signature entirely
isinstance(Fake(), SupportsCharge)     # True. Useless as a guarantee.
```

It's a smoke test. For real safety, rely on the static check.

---

### Q6. What does `ABC.register()` do, and what are its limits?

It declares an existing class a **virtual subclass** without touching it:

```python
class Serializer(ABC):
    @abstractmethod
    def dumps(self, obj) -> str: ...

class ThirdPartyJson:                 # lives in site-packages; we cannot edit it
    def dumps(self, obj): return "{...}"

Serializer.register(ThirdPartyJson)
issubclass(ThirdPartyJson, Serializer)      # True
isinstance(ThirdPartyJson(), Serializer)    # True
```

**What you get:** `isinstance`/`issubclass` pass, so the class works with `functools.singledispatch`
and with any `isinstance`-based routing you already have.

**What you do NOT get — say all three:**

1. **No inherited code.** A registered class gets nothing from the ABC — no template method, no
   `__init__`, nothing.
2. **No abstract-method check.** `Serializer.register(SomethingWithNoDumps)` succeeds happily and
   `isinstance` lies to you. It is a *label*, not a verification.
3. **It doesn't appear in the MRO.** `ThirdPartyJson.__mro__` has no `Serializer` in it, so `super()`
   cannot reach it and attribute lookup is unaffected.

This is how `collections.abc` claims the built-ins: `list` doesn't subclass `MutableSequence`, it's
registered as a virtual subclass, which is why `isinstance([], Sequence)` is `True`. You can also
hook it from the ABC side with `__subclasshook__` for duck-typed `isinstance`.

**In practice:** reach for `register()` only when you need `isinstance` to succeed for a class you
can't edit. If you just need type-checker agreement, a Protocol is cleaner and honest about the
lack of a runtime guarantee.

---

### Q7. What does `collections.abc` give you for free?

Implement the two or three required methods and inherit the rest of the interface:

```python
from collections.abc import Mapping

class ReadOnlyConfig(Mapping):
    def __init__(self, data): self._data = dict(data)
    def __getitem__(self, key): return self._data[key]      # required
    def __iter__(self):         return iter(self._data)     # required
    def __len__(self):          return len(self._data)      # required

cfg = ReadOnlyConfig({"env": "prod", "retries": 3})
len(cfg), "env" in cfg, cfg.get("missing", "-"), list(cfg.items()), cfg == {"env": "prod", "retries": 3}
cfg["env"] = "dev"      # TypeError — Mapping has no __setitem__, so it's immutable BY CONSTRUCTION
```

Those three methods earn you `get`, `keys`, `items`, `values`, `__contains__`, `__eq__` and `__ne__`,
plus `isinstance(cfg, Mapping)` so every library that duck-types on mappings accepts it.

The ones to know and what each requires:

| ABC | You implement | You inherit |
|---|---|---|
| `Iterable` | `__iter__` | — |
| `Iterator` | `__iter__`, `__next__` | — |
| `Sequence` | `__getitem__`, `__len__` | `__contains__`, `__iter__`, `__reversed__`, `index`, `count` |
| `MutableSequence` | + `__setitem__`, `__delitem__`, `insert` | `append`, `extend`, `pop`, `remove`, `__iadd__`, `reverse` |
| `Mapping` | `__getitem__`, `__iter__`, `__len__` | `get`, `keys`, `items`, `values`, `__contains__`, `__eq__` |
| `MutableMapping` | + `__setitem__`, `__delitem__` | `pop`, `popitem`, `clear`, `update`, `setdefault` |
| `Set` | `__contains__`, `__iter__`, `__len__` | all the operators: `&`, `\|`, `-`, `^`, `<=`, … |

**The design lesson** — worth stating because it generalises: this is exactly the template-method
pattern from Q2. The mixin implements the broad interface *in terms of* a tiny required core. When
you design your own base class, ask "what is the smallest set of methods a subclass must write?" and
build everything else on top. It's also why `Mapping` vs `MutableMapping` is a real API decision:
subclassing the immutable one makes immutability structural rather than a convention nobody follows.

---

### Q8. `__init_subclass__` vs ABC vs metaclass — which and why?

Three tools, three different moments:

```python
class Plugin:
    registry: dict = {}

    def __init_subclass__(cls, /, name=None, **kwargs):
        super().__init_subclass__(**kwargs)              # ALWAYS cooperate
        if name is None:
            raise TypeError(f"{cls.__name__} must pass name=...")
        if not hasattr(cls, "execute"):
            raise TypeError(f"{cls.__name__} must define execute()")
        Plugin.registry[name] = cls                      # auto-registration, for free

class CsvPlugin(Plugin, name="csv"):
    def execute(self): return "csv!"

class Broken(Plugin, name="broken"):      # TypeError at CLASS DEFINITION — i.e. at IMPORT
    pass
```

| | Fires when | Use it for |
|---|---|---|
| `__init_subclass__` | the subclass is **defined** (import time) | auto-registration, validating class-level config, rejecting bad subclasses before anything runs |
| ABC `@abstractmethod` | the subclass is **instantiated** | "every implementation must provide these methods" |
| metaclass (`ABCMeta`, custom) | the class **object** is created | rewriting the class, controlling `isinstance`, DSLs — rarely needed |

**`__init_subclass__` is the one people under-use**, and it has two real advantages over an ABC:
it fires **earlier** (a broken plugin breaks the import, not the first request), and it can enforce
things an ABC can't — "you must declare a `name`", "you must set `table_name`", "your `timeout` must
be an int". It's also a plain classmethod, so it's far easier to read and debug than a metaclass.

**The rule for metaclasses:** if `__init_subclass__`, a class decorator, or an ABC can do it, use
those. Reach for a metaclass only when you must control class *creation* itself (as `ABCMeta` and
Django's model metaclass do). See
[05 — Context managers, descriptors, metaclasses](05_context_managers_descriptors_metaclasses.md)
and [`12_framework_internals/03_plugin_architecture.py`](../12_framework_internals/03_plugin_architecture.py).

---

### Q9. When should you NOT use an ABC?

Volunteering this is what makes the answer senior — ABCs get over-applied by people arriving from
Java.

**Don't, when:**

- **There's exactly one implementation.** A one-implementation "interface" is ceremony. Add the
  abstraction when the second implementation appears; you'll also design it better then, because
  you'll have seen two real shapes.
- **The contract is a single method.** Pass the function. `def process(rows, transform: Callable[[Row], Row])`
  beats a `Transformer` ABC with one method and five subclasses.
- **You don't own the implementers.** They'd have to import your base class. Use a Protocol.
- **It's a mixin, not a contract.** `LoggingMixin` with no abstract methods is just a class — call
  it a mixin and don't dress it as an ABC.
- **You want duck typing.** `json.dumps` accepts anything with the right shape; forcing a base class
  on third-party objects is how you end up with adapter sprawl.

**The cost of over-abstracting** is real and worth naming: an extra file to open to understand any
flow, a base class whose shape was guessed from one example and then fits nothing, and `isinstance`
checks that make adding an implementation a change in three places. The rule of thumb: **the second
implementation justifies the abstraction; the first one doesn't.**

One honest exception: when the abstraction exists specifically to make testing possible — a
`Clock` ABC so you can inject a fake time, or a `Repository` ABC so the service layer can be tested
without a database — a single production implementation is fine, because the test double is the
second implementation.

---

### Q10. How do ABCs interact with multiple inheritance and the MRO?

`ABC` is just `class ABC(metaclass=ABCMeta)`, so ABCs follow the normal C3 linearization
([06 — OOP and MRO](06_oop_inheritance_mro.md)). Two practical consequences:

**1. Abstract methods are satisfied by ANY class in the MRO.** This is how mixins compose:

```python
class Readable(ABC):
    @abstractmethod
    def read(self): ...

class FileReadMixin:
    def read(self): return "from file"       # not a subclass of Readable at all

class FileSource(FileReadMixin, Readable):   # mixin FIRST, so its read() is found first
    pass

FileSource().read()        # "from file" — instantiable: the MRO supplies `read`
```

If you reverse the bases (`Readable, FileReadMixin`), `Readable.read` — the abstract one — comes
first in the MRO and the class **remains abstract**. `ABCMeta` collects `__abstractmethods__` by
walking the MRO, so **order matters**. The rule: *mixins before the ABC.*

**2. Metaclass conflicts.** Combining an ABC with a class that has a *different* custom metaclass
raises:

```
TypeError: metaclass conflict: the metaclass of a derived class must be a
(non-strict) subclass of the metaclasses of all its bases
```

You hit this mixing an ABC with some ORM or Pydantic-style bases. The fix is a metaclass that
inherits both (`class Meta(ABCMeta, OtherMeta): pass`), or — usually better — stop inheriting and
use a Protocol or composition instead.

---

## Java contrast

| Java | Python |
|---|---|
| `interface Gateway { String charge(...); }` | `class Gateway(ABC)` with `@abstractmethod` |
| `abstract class` — contract **plus** code | **the same ABC** — Python has one construct for both |
| `implements Gateway` is **required** | subclass the ABC, match a `Protocol`, or just duck-type |
| Missing method = **compile error** | `TypeError` at **instantiation** (runtime, but before any use) |
| `default` methods on interfaces (Java 8+) | plain concrete methods on the ABC |
| No structural typing | `typing.Protocol` — structural, no inheritance needed |
| `@FunctionalInterface` + lambda | any callable; pass the function itself |
| Multiple interfaces, single class inheritance | multiple inheritance with C3 MRO and cooperative `super()` |
| Signatures enforced by the compiler | signatures enforced only by mypy/pyright — **run one in CI** |

**The difference that actually matters:** in Java the compiler refuses to ship a class that doesn't
satisfy its interface. In Python the check happens the first time someone constructs the class — so
**your tests and your type checker are what move that check back to build time.** A test that merely
imports every module catches nothing; a test that *instantiates* every implementation catches
everything `abc` can catch. That sentence is the whole Java→Python translation of this topic.

---

## A worked example

A notification system that uses each mechanism for the job it's actually right for:

```python
"""ABC for our own hierarchy (shared retry logic), Protocol for a vendor SDK we can't edit,
__init_subclass__ for registration, and a contract test for the semantics none of them check."""
from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable
import time


# ---- 1. ABC: we own this hierarchy AND we want to share the retry algorithm.
class NotificationChannel(ABC):
    registry: dict[str, type] = {}

    def __init_subclass__(cls, /, channel_name=None, **kwargs):
        """Fires at IMPORT time — earlier than the ABC's own check, and it enforces something
        the ABC cannot: that every channel declares a name."""
        super().__init_subclass__(**kwargs)
        if channel_name is None:
            raise TypeError(f"{cls.__name__} must declare channel_name=...")
        NotificationChannel.registry[channel_name] = cls

    # --- the TEMPLATE: the algorithm, written once, inherited by every channel
    def send_with_retry(self, message: str, recipient: str, attempts: int = 3) -> bool:
        for attempt in range(1, attempts + 1):
            try:
                self.send(message, recipient)
                return True
            except self.transient_errors() as exc:
                if attempt == attempts:
                    raise
                time.sleep(0.05 * 2 ** (attempt - 1))      # see deep_dive/26 for the real version
        return False

    # --- ABSTRACT: every channel must provide this
    @abstractmethod
    def send(self, message: str, recipient: str) -> None:
        """Deliver, or raise. MUST be idempotent for the same (message, recipient)."""

    @property
    @abstractmethod                                        # innermost — order is load-bearing
    def max_length(self) -> int: ...

    # --- HOOK: a working default, overridden only when a channel needs to
    def transient_errors(self) -> tuple[type[Exception], ...]:
        return (TimeoutError, ConnectionError)

    def truncate(self, message: str) -> str:               # shared concrete helper
        return message if len(message) <= self.max_length else message[: self.max_length - 1] + "…"


class EmailChannel(NotificationChannel, channel_name="email"):
    max_length = 10_000                                    # a plain attribute satisfies the property
    def send(self, message, recipient):
        print(f"  email -> {recipient}: {self.truncate(message)}")


class SmsChannel(NotificationChannel, channel_name="sms"):
    max_length = 160
    def send(self, message, recipient):
        print(f"  sms -> {recipient}: {self.truncate(message)}")
    def transient_errors(self):                            # this provider also throws OSError
        return (TimeoutError, ConnectionError, OSError)


# ---- 2. Protocol: a vendor SDK we cannot edit and must not force to import our base class.
@runtime_checkable
class SupportsPost(Protocol):
    def post(self, text: str, target: str) -> dict: ...


class VendorSlackClient:                     # from site-packages; knows nothing about us
    def post(self, text, target): return {"ok": True, "channel": target}


class SlackChannelAdapter(NotificationChannel, channel_name="slack"):
    """The ADAPTER is where the two worlds meet: it satisfies our ABC and consumes the Protocol.
    No inheritance is imposed on the vendor, and the retry logic is still inherited."""
    max_length = 4_000

    def __init__(self, client: SupportsPost):
        self.client = client

    def send(self, message, recipient):
        self.client.post(self.truncate(message), recipient)


def notify_everywhere(message: str, recipient: str) -> dict[str, bool]:
    """Dispatch via the registry that __init_subclass__ built for us."""
    results = {}
    for name, cls in NotificationChannel.registry.items():
        channel = cls(VendorSlackClient()) if cls is SlackChannelAdapter else cls()
        results[name] = channel.send_with_retry(message, recipient)
    return results


# ---- 3. The contract test: the SEMANTICS none of the above can express.
def test_every_channel_truncates_and_is_idempotent():
    for name, cls in NotificationChannel.registry.items():
        channel = cls(VendorSlackClient()) if cls is SlackChannelAdapter else cls()
        long_message = "x" * 50_000
        assert len(channel.truncate(long_message)) <= channel.max_length
        assert channel.send_with_retry("hello", "a@b.com") is True
        assert channel.send_with_retry("hello", "a@b.com") is True    # twice == once
```

**Why each choice:**

- **`NotificationChannel` is an ABC, not a Protocol**, because `send_with_retry` and `truncate` are
  real shared code. A Protocol would force every channel to reimplement them.
- **`__init_subclass__` enforces `channel_name`** — something `@abstractmethod` cannot express — and
  it does so at import time, so a misconfigured channel breaks the build, not the first page.
- **`SupportsPost` is a Protocol** because `VendorSlackClient` is not ours. Using an ABC here would
  mean either monkey-patching the vendor class or calling `register()` — both worse than describing
  the shape we need.
- **`SlackChannelAdapter` is the seam**: our contract on the outside, the vendor's Protocol on the
  inside. Swapping vendors changes one class.
- **`max_length` is an abstract property satisfied by a plain int**, so each channel states its
  limit as data rather than boilerplate.
- **The contract test** asserts the two things nothing else checks: truncation respects
  `max_length`, and `send` is idempotent. The ABC can't say "idempotent"; a test can.

---

## Hands-on drills

1. Build a 3-method ABC, implement 2 of them, and read the `TypeError` carefully. Print
   `__abstractmethods__`. Then implement the third and watch it empty out.
2. Swap `@property` and `@abstractmethod` on an abstract property, then omit the attribute in the
   subclass. Confirm it instantiates — you've just reproduced the silent failure.
3. Write a subclass with a deliberately wrong signature. Instantiate it (works), call it (fails).
   Then run `mypy` on the file and read the override error. That's the three-layer argument in
   practice.
4. Convert that ABC to a Protocol and make an unrelated class satisfy it. Add `@runtime_checkable`
   and prove `isinstance` passes even with a wrong signature.
5. Implement `Mapping` with three methods, then `set(dir(cfg)) - set(dir(object))` to count what you
   got free. Switch to `MutableMapping`, add `__setitem__`/`__delitem__`, and count again.
6. Use `register()` on a class missing the abstract method. Confirm `isinstance` returns `True` —
   and write down in one sentence why that's dangerous.
7. Write `__init_subclass__` that rejects a subclass without a `table_name`, and confirm the error
   fires on `import`, not on instantiation.
8. Build the mixin/ABC MRO puzzle from Q10 both ways round. Print `__mro__` and
   `__abstractmethods__` for each and explain the difference.
9. Create a metaclass conflict on purpose (an ABC plus a class with its own metaclass), read the
   error, then resolve it with a combined metaclass.
10. Write a parametrised contract test over three implementations of one ABC, including a fake used
    in unit tests. Make the fake fail it, then fix the fake.

---

## The 60-second spoken answer

> "An ABC is a contract Python enforces at instantiation: subclass it, miss an `@abstractmethod`,
> and you get a `TypeError` naming exactly what's missing. The value is *when* you find out — at
> construction, so a startup or a test catches it, rather than `AttributeError` the first time a
> customer hits that path.
>
> The thing people get wrong is thinking an ABC is an interface. It isn't — it can carry concrete
> code, and that's usually why I pick it: I define the algorithm once in the base as a template
> method, mark the varying steps abstract, and give the optional ones working defaults as hooks.
> That's exactly what `collections.abc` does — implement `__getitem__`, `__iter__` and `__len__` and
> you inherit `get`, `keys`, `items` and `__eq__` from `Mapping`.
>
> The limit I'd volunteer: an ABC checks that NAMES exist, nothing more. A subclass with a wrong
> signature instantiates fine and blows up at call time. So I use three layers — the ABC for
> existence at runtime, mypy in CI for signatures and Liskov compatibility, and a shared
> parametrised contract test suite for the semantics neither can express, like 'refund must be
> idempotent'. That same suite keeps my test fakes honest about the real implementation.
>
> `typing.Protocol` is the alternative: structural rather than nominal, so a third-party class
> satisfies it without importing anything of mine. I use an ABC when I own the hierarchy and want
> shared code, and a Protocol to describe what a function needs from its argument — which inverts
> the dependency, since the consumer defines the interface. `@runtime_checkable` makes `isinstance`
> work but only checks member names, so I treat it as a smoke test. `register()` makes an existing
> class a virtual subclass for `isinstance` purposes, but it inherits no code and gets no
> abstract-method check — it's a label, not a verification.
>
> And `__init_subclass__` is the one people under-use: it fires at class definition, so it's
> *earlier* than an ABC and can enforce things an ABC can't, like 'every plugin must declare a
> name'. I reach for a metaclass only when none of those will do. Coming from Java, the thing to
> internalise is that Python's check happens at runtime — so a test that actually instantiates every
> implementation is what gives you back the compiler."
