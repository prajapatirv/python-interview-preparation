"""
OOP in depth: multiple/multilevel inheritance, the diamond problem, MRO, cooperative super(),
mixins, ABCs, and dunder methods. Run me: python 07_oop_inheritance_mro.py
"""
from abc import ABC, abstractmethod


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- multilevel vs multiple inheritance
section("multilevel (a chain) vs multiple (several bases at once)")


class Animal:
    def breathe(self):
        return "breathing"


class Mammal(Animal):  # multilevel: Animal -> Mammal -> Dog
    pass


class Dog(Mammal):
    pass


class Flyer:
    def move(self):
        return "fly"


class Swimmer:
    def move(self):
        return "swim"


class Duck(Flyer, Swimmer):  # multiple: Duck(Flyer, Swimmer)
    pass


print("Dog().breathe() ->", Dog().breathe())
print("Duck().move() ->", Duck().move(), "(leftmost base wins by MRO)")


# ---------------------------------------------------------------- the diamond problem + MRO
section("the diamond problem — Python's C3 MRO ensures A runs exactly once")


class A:
    def hello(self):
        print("  A")


class B(A):
    def hello(self):
        print("  B")
        super().hello()


class C(A):
    def hello(self):
        print("  C")
        super().hello()


class D(B, C):
    def hello(self):
        print("  D")
        super().hello()


print("MRO of D:", [k.__name__ for k in D.__mro__])
print("D().hello() call sequence:")
D().hello()  # D B C A -- A runs once, not twice


# ---------------------------------------------------------------- cooperative __init__
section("cooperative multiple inheritance: every __init__ accepts **kwargs and calls super()")


class Base:
    def __init__(self, **kw):
        super().__init__(**kw)  # chain terminates at object, which accepts no extra args


class Timestamped(Base):
    def __init__(self, created=None, **kw):
        self.created = created
        super().__init__(**kw)


class Named(Base):
    def __init__(self, name="", **kw):
        self.name = name
        super().__init__(**kw)


class Product(Timestamped, Named):
    pass


p = Product(name="pen", created="2026-10-01")
print("Product:", p.name, p.created)


# ---------------------------------------------------------------- mixins
section("mixins: small, focused, not meant to stand alone")


class JsonMixin:
    def to_json(self):
        import json
        return json.dumps(self.__dict__)


class User(JsonMixin):
    def __init__(self, name):
        self.name = name


print("User(...).to_json():", User("ravi").to_json())


# ---------------------------------------------------------------- abstract base classes
section("ABC — cannot instantiate until every abstractmethod is implemented")


class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount):
        ...


class StripeLike(PaymentGateway):
    def charge(self, amount):
        return f"charged {amount}"


print("StripeLike().charge(100) ->", StripeLike().charge(100))
try:
    PaymentGateway()
except TypeError as e:
    print("can't instantiate the ABC directly:", e)


# ---------------------------------------------------------------- dunder methods / operator overloading
section("dunder methods power +, ==, <, repr(), len(), and `with`")


class Money:
    def __init__(self, amount):
        self.amount = amount

    def __add__(self, other):
        return Money(self.amount + other.amount)

    def __eq__(self, other):
        return isinstance(other, Money) and self.amount == other.amount

    def __lt__(self, other):
        return self.amount < other.amount

    def __repr__(self):
        return f"Money({self.amount})"


print(Money(5) + Money(7), "| Money(5) < Money(7) ->", Money(5) < Money(7))


# ---------------------------------------------------------------- classmethod / staticmethod
section("classmethod (factory pattern) vs staticmethod (namespaced function)")


class Date:
    def __init__(self, y, m, d):
        self.y, self.m, self.d = y, m, d

    @classmethod
    def from_iso(cls, s):
        return cls(*map(int, s.split("-")))

    @staticmethod
    def is_leap(year):
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    def __repr__(self):
        return f"{self.y:04d}-{self.m:02d}-{self.d:02d}"


print("Date.from_iso('2026-09-30') ->", Date.from_iso("2026-09-30"))
print("Date.is_leap(2028) ->", Date.is_leap(2028))

# EXERCISE: build LoggingMixin + RetryMixin + an ABC Handler(process), then combine them into
# class OrderHandler(LoggingMixin, RetryMixin, Handler) and print OrderHandler.__mro__ to see
# exactly how the pieces stack.
