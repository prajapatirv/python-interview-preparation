"""
Abstract base classes (ABC): enforcing a contract at instantiation time, the template-method
pattern, abstract properties and class methods, `Protocol` (structural typing) as the alternative,
`register()` for third-party classes, and the `collections.abc` mixins you get for free.

The mental model: an **ABC is a promise checked by Python**; a **Protocol is a promise checked by
your type checker**; **duck typing is a promise checked by production**.

Run me: python 13_abstract_base_classes.py
"""
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- the basic contract
section("an ABC with an abstract method cannot be instantiated -- the error is at CONSTRUCTION")


class PaymentGateway(ABC):
    """Every gateway must be able to charge and to refund."""

    @abstractmethod
    def charge(self, amount_cents: int, token: str) -> str:
        """Return a provider transaction id. Must raise on failure."""

    @abstractmethod
    def refund(self, transaction_id: str) -> bool:
        ...


class StripeGateway(PaymentGateway):
    def charge(self, amount_cents, token):
        return f"stripe_txn_{amount_cents}"

    def refund(self, transaction_id):
        return True


class HalfFinishedGateway(PaymentGateway):
    def charge(self, amount_cents, token):       # refund() never implemented
        return "oops"


print(f"  StripeGateway works: {StripeGateway().charge(500, 'tok_x')}")
try:
    HalfFinishedGateway()
except TypeError as e:
    print(f"  TypeError at construction: {e}")
print("  note WHEN you find out: at instantiation, not when refund() is first called in prod.")
print(f"  the unimplemented set is tracked on the class: "
      f"{sorted(HalfFinishedGateway.__abstractmethods__)}")


# ---------------------------------------------------------------- ABCs may hold real code
section("an ABC is not an interface -- it can carry concrete code (the template-method pattern)")


class ReportJob(ABC):
    """Defines the ALGORITHM once; subclasses fill in only the steps that differ.
    This is the single biggest reason to pick an ABC over a Protocol."""

    def run(self):                      # <- the template: concrete, inherited, never overridden
        rows = self.fetch()
        cleaned = [r for r in rows if self.is_valid(r)]
        return self.render(cleaned)

    @abstractmethod
    def fetch(self) -> list:
        """Subclass must provide the data source."""

    @abstractmethod
    def render(self, rows: list) -> str:
        """Subclass must provide the output format."""

    def is_valid(self, row) -> bool:     # <- a HOOK: sensible default, override only if needed
        return row is not None


class CsvOrderReport(ReportJob):
    def fetch(self):
        return [{"id": 1, "total": 10}, None, {"id": 2, "total": 20}]

    def render(self, rows):
        return "id,total\n" + "\n".join(f"{r['id']},{r['total']}" for r in rows)


print("  CsvOrderReport().run() ->")
for line in CsvOrderReport().run().splitlines():
    print(f"    {line}")
print("  the None row was dropped by the inherited is_valid() hook, not by subclass code.")


# ---------------------------------------------------------------- abstract property / classmethod
section("abstract property, classmethod and staticmethod -- order the decorators correctly")


class Connector(ABC):
    @property
    @abstractmethod                     # @abstractmethod must be the INNERMOST decorator
    def dsn(self) -> str:
        """Subclasses expose this as an attribute or a property -- their choice."""

    @classmethod
    @abstractmethod
    def from_env(cls) -> "Connector":
        ...

    @staticmethod
    @abstractmethod
    def driver_name() -> str:
        ...


class PostgresConnector(Connector):
    dsn = "postgresql://localhost:5432/app"   # a plain class attribute satisfies the property

    @classmethod
    def from_env(cls):
        return cls()

    @staticmethod
    def driver_name():
        return "psycopg"


c = PostgresConnector.from_env()
print(f"  dsn={c.dsn}  driver={PostgresConnector.driver_name()}")
print("  a plain attribute satisfies an abstract property -- Python checks the NAME, not the kind.")
print("  get the decorator order backwards (@abstractmethod above @property) and the check is lost.")


# ---------------------------------------------------------------- what an ABC does NOT check
section("the limits: an ABC checks that names EXIST, never that signatures or types match")


class WrongSignature(PaymentGateway):
    def charge(self):                    # takes no amount, no token -- Python is fine with it
        return "nope"

    def refund(self, transaction_id, extra_required_arg):
        return False


w = WrongSignature()                     # instantiates happily
print(f"  WrongSignature() constructed fine: {w!r}")
try:
    w.charge(500, "tok_x")
except TypeError as e:
    print(f"  ...and blows up only at CALL time: {e}")
print("  mypy/pyright catch this statically; the ABC machinery does not. Run a type checker too.")


# ---------------------------------------------------------------- Protocol: structural typing
section("Protocol -- same contract, checked structurally, with no inheritance required")


@runtime_checkable
class SupportsCharge(Protocol):
    """Anything with a matching charge() satisfies this. The class need not know we exist --
    which is the whole point for third-party or legacy objects you cannot edit."""

    def charge(self, amount_cents: int, token: str) -> str:
        ...


class LegacyVendorClient:            # written years ago, imports nothing of ours
    def charge(self, amount_cents, token):
        return f"legacy_{amount_cents}"


def take_payment(gateway: SupportsCharge, amount: int) -> str:
    return gateway.charge(amount, "tok_demo")


print(f"  a legacy class satisfies the Protocol: {take_payment(LegacyVendorClient(), 250)}")
print(f"  isinstance works because of @runtime_checkable: "
      f"{isinstance(LegacyVendorClient(), SupportsCharge)}")
print("  careful: runtime_checkable isinstance() checks METHOD NAMES ONLY, not signatures.")
print("  pick: ABC when you own the hierarchy and want shared code; Protocol for adapting "
      "code you don't own.")


# ---------------------------------------------------------------- register(): a virtual subclass
section("ABCMeta.register() -- declare an existing class a subclass without touching it")


class Serializer(ABC):
    @abstractmethod
    def dumps(self, obj) -> str:
        ...


class ThirdPartyJson:                 # pretend this lives in site-packages
    def dumps(self, obj):
        return "{...}"


Serializer.register(ThirdPartyJson)
print(f"  issubclass(ThirdPartyJson, Serializer) -> {issubclass(ThirdPartyJson, Serializer)}")
print(f"  isinstance works too -> {isinstance(ThirdPartyJson(), Serializer)}")
print("  BUT: a registered class inherits NO code and is NOT abstract-method-checked. "
      "It's a label for isinstance(), nothing more.")


# ---------------------------------------------------------------- collections.abc for free mixins
section("collections.abc -- implement 2 methods, inherit ~8 for free")


class ReadOnlyConfig(Mapping):
    """Implementing __getitem__, __iter__ and __len__ earns .get(), .keys(), .items(),
    .values(), __contains__, __eq__ and __ne__ from the Mapping mixin."""

    def __init__(self, data):
        self._data = dict(data)

    def __getitem__(self, key):
        return self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


cfg = ReadOnlyConfig({"env": "prod", "retries": 3})
print(f"  len={len(cfg)}  'env' in cfg={'env' in cfg}  cfg.get('missing', '-')={cfg.get('missing', '-')}")
inherited = sorted(n for n in set(dir(cfg)) - set(dir(object))
                   if not n.startswith("_") or (n.startswith("__") and n.endswith("__")))
print(f"  inherited for free: {[n for n in inherited if not n.startswith('__')]}")
print(f"  plus the dunders:   {[n for n in inherited if n.startswith('__')][:6]} ...")
try:
    cfg["env"] = "dev"
except TypeError as e:
    print(f"  immutable by construction (Mapping has no __setitem__): {e}")
print(f"  and isinstance checks pass against the stdlib ABCs: "
      f"Mapping={isinstance(cfg, Mapping)}, Sequence={isinstance(cfg, Sequence)}")


# ---------------------------------------------------------------- __init_subclass__: the lighter tool
section("__init_subclass__ -- validate subclasses without ABCMeta, at CLASS-CREATION time")


class Plugin:
    registry: dict = {}

    def __init_subclass__(cls, /, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name is None:
            raise TypeError(f"{cls.__name__} must declare `class {cls.__name__}(Plugin, name=...)`")
        if not hasattr(cls, "execute"):
            raise TypeError(f"{cls.__name__} must define execute()")
        Plugin.registry[name] = cls


class CsvPlugin(Plugin, name="csv"):
    def execute(self):
        return "csv!"


try:
    class BrokenPlugin(Plugin, name="broken"):   # no execute()
        pass
except TypeError as e:
    print(f"  rejected at class-definition time (import time!): {e}")

print(f"  registry: {Plugin.registry}")
print("  __init_subclass__ fires EARLIER than an ABC does -- at import, not at instantiation.")
print("  see 12_framework_internals/03_plugin_architecture.py for this as a real plugin loader.")


# ---------------------------------------------------------------- Java contrast
section("Java contrast")
print("""  Java                              Python
  --------------------------------  --------------------------------------------------
  interface Gateway { ... }         class Gateway(ABC) with @abstractmethod
  abstract class with some code     the SAME ABC -- Python has one construct for both
  implements Gateway  (required)    subclass an ABC, OR match a Protocol, OR just duck-type
  compile-time error                TypeError at instantiation (runtime, but before any use)
  default methods on interfaces     plain concrete methods on the ABC
  no structural typing              typing.Protocol = structural, no inheritance needed
  @FunctionalInterface + lambda     any callable; pass the function itself""")
print("  the big one: in Java the contract is enforced by the compiler before you ship;")
print("  in Python it is enforced the first time someone constructs the class, so your TESTS")
print("  (and a type checker in CI) are what move that check back to build time.")


# EXPERIMENT 1: delete `refund` from StripeGateway and run again -- note that the TypeError names
# exactly which methods are missing.
# EXPERIMENT 2: swap @property and @abstractmethod in Connector.dsn, then remove `dsn` from
# PostgresConnector. It now instantiates with no complaint -- the abstractness was silently lost.
# EXPERIMENT 3: delete `charge` from LegacyVendorClient and re-run the isinstance() check against
# SupportsCharge. Then add a `charge` that takes zero arguments -- isinstance STILL passes.
# EXPERIMENT 4: add `__setitem__` to ReadOnlyConfig and inherit from MutableMapping instead; count
# how many extra methods (pop, popitem, clear, update, setdefault) you get for free.

# EXERCISE: design a `NotificationChannel` ABC with abstract `send(message, recipient)` and a
# concrete `send_with_retry()` template that retries transient failures 3 times. Implement
# EmailChannel and SmsChannel. Then write a `SlackClient` you pretend you cannot edit, and make it
# usable through a Protocol instead. Finally, say in one sentence which of the three mechanisms
# (ABC / Protocol / register) you'd use for each of the three classes, and why.
