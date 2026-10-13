"""
Descriptors (what actually powers @property), and metaclasses (what actually creates classes).
Run me: python 06_descriptors_metaclasses.py
"""


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- a validating descriptor
section("descriptor: reusable validation logic, shared across attributes/classes")


class Positive:
    """A data descriptor: defines __set__, so it beats the instance __dict__."""

    def __set_name__(self, owner, name):
        self.name = "_" + name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.name)

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{self.name[1:]} must be > 0, got {value}")
        setattr(obj, self.name, value)


class Order:
    qty = Positive()
    price = Positive()

    def __init__(self, qty, price):
        self.qty = qty
        self.price = price


o = Order(2, 9.5)
print("valid order:", o.qty, o.price)
try:
    Order(0, 1)
except ValueError as e:
    print("rejected:", e)


# ---------------------------------------------------------------- how @property is "just" a descriptor
section("@property is a built-in data descriptor — this is what it desugars to")


class Temperature:
    def __init__(self, celsius):
        self._c = celsius

    @property
    def celsius(self):
        return self._c

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._c = value

    @property
    def fahrenheit(self):
        return self._c * 9 / 5 + 32


t = Temperature(100)
print("100C in F:", t.fahrenheit)
try:
    t.celsius = -300
except ValueError as e:
    print("rejected:", e)


# ---------------------------------------------------------------- metaclass basics
section("a metaclass is the class OF a class — `type` is the default one")
Dog = type("Dog", (), {"speak": lambda self: "woof"})
print(Dog().speak(), "| type(Dog) ==", type(Dog))


# ---------------------------------------------------------------- metaclass enforcing a rule
section("metaclass that enforces subclasses implement run()")


class RequireRun(type):
    def __new__(mcs, name, bases, namespace):
        if bases and "run" not in namespace:
            raise TypeError(f"{name} must define run()")
        return super().__new__(mcs, name, bases, namespace)


class Job(metaclass=RequireRun):
    pass


class EmailJob(Job):
    def run(self):
        return "sending email"


print("EmailJob().run() ->", EmailJob().run())
try:
    class BadJob(Job):
        pass
except TypeError as e:
    print("rejected at class-definition time:", e)


# ---------------------------------------------------------------- the usually-better alternative
section("prefer __init_subclass__ over a metaclass when you just need a hook")


class Plugin:
    registry = {}

    def __init_subclass__(cls, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry[key or cls.__name__] = cls


class Csv(Plugin, key="csv"):
    pass


class Json(Plugin, key="json"):
    pass


print("plugin registry built with zero metaclass code:", Plugin.registry)

# EXERCISE: implement a Singleton using a metaclass (override __call__ on the metaclass so
# repeated instantiation returns the cached instance), then argue in one sentence why dependency
# injection is usually a better answer in an interview than "just use a singleton."
