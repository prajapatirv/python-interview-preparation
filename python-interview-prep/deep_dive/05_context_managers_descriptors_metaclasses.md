# Deep Dive 05 — Context Managers, Descriptors and Metaclasses

> Runnable companions: [`01_python_core/05_context_managers.py`](../01_python_core/05_context_managers.py) ·
> [`01_python_core/06_descriptors_metaclasses.py`](../01_python_core/06_descriptors_metaclasses.py)
> Related deep dives: [Decorators](03_decorators.md) · [OOP](06_oop_inheritance_mro.md) ·
> [Framework development](11_python_framework_development.md)

## What interviewers are actually probing

These three are the "advanced Python" signals, and they are probed for different reasons:

- **Context managers** are *practical*. You will be asked because resource leaks are real: unclosed
  DB connections, un-rolled-back transactions, un-flushed Kafka producers. The expected answer
  includes both the class form and `@contextmanager`, plus what `__exit__`'s return value does.
- **Descriptors** are *explanatory*. They're how `property`, `classmethod`, `staticmethod` and every
  bound method actually work. Being able to explain the data/non-data lookup precedence proves you
  understand attribute access rather than just using it.
- **Metaclasses** are a *judgement* test. The interviewer wants to know you can explain them **and**
  that you know you almost never need them. Quoting Tim Peters — "if you wonder whether you need a
  metaclass, you don't" — and naming the lighter alternatives is the winning answer.

---

## Must-know points

- `with` calls `__enter__`, and **always** calls `__exit__(exc_type, exc, tb)` — on success, on
  exception, on `return`, on `break`.
- **`__exit__` returning a truthy value suppresses the exception.** Returning `None`/`False` lets it
  propagate. This is the single most-asked context-manager detail.
- `@contextlib.contextmanager` turns a generator into a context manager: before `yield` = enter, the
  yielded value = the `as` target, after `yield` (in a `finally`) = exit.
- **Descriptor** = an object defining `__get__`, `__set__` or `__delete__`, stored **on the class**.
- **Data descriptor** (defines `__set__` or `__delete__`) **beats** the instance `__dict__`;
  a **non-data descriptor** (only `__get__`) loses to it.
- **Metaclass** = the class *of* a class. `type` is the default. Prefer `__init_subclass__`,
  `__set_name__`, class decorators or `abc.ABC`.

---

## Part A — Context Managers

### Q1. What is a context manager and what problem does it solve?

An object defining **setup and teardown** around a block, via `__enter__` and `__exit__`. It
guarantees the teardown runs **even if the block raises, returns, or breaks**, replacing verbose and
easily-forgotten `try/finally` scaffolding.

```python
# Without — correct but noisy, and one early `return` away from a leak
f = open("data.txt")
try:
    process(f)
finally:
    f.close()

# With — the guarantee is structural
with open("data.txt") as f:
    process(f)
```

The real-world cases that matter in a backend role: **file handles**, **DB transactions**
(commit/rollback), **locks** (always released), **Kafka producers** (always flushed), **temporary
directories**, **timers/spans**, and **patching in tests**.

The `with` statement supports multiple managers, and they nest left-to-right:

```python
with open("in.txt") as src, open("out.txt", "w") as dst:
    dst.write(src.read())
# equivalent to nesting: dst's __exit__ runs first, then src's
```

---

### Q2. Write a class-based context manager for a database transaction.

`__exit__` receives the exception triple `(exc_type, exc_value, traceback)`, all `None` on success.
Commit when there was no exception, roll back when there was, always release the cursor.

```python
class Transaction:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        self.cur = self.conn.cursor()
        return self.cur                 # this is what `as cur` binds

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
        finally:
            self.cur.close()            # released even if commit/rollback throws
        return False                    # do NOT swallow the exception

with Transaction(conn) as cur:
    cur.execute("UPDATE accounts SET bal = bal - 100 WHERE id = 1")
    cur.execute("UPDATE accounts SET bal = bal + 100 WHERE id = 2")
# commits on success; rolls back and re-raises on failure
```

Two details worth narrating:

- **`return False`** (or simply falling off the end, which returns `None`) is deliberate: the caller
  must still see the failure. Returning `True` would silently swallow it.
- **The inner `try/finally`** ensures the cursor closes even if `commit()` itself raises — a real
  scenario on a broken connection.

---

### Q3. How do you write a context manager using `contextlib`?

Decorate a generator with `@contextmanager`. Code before `yield` is the enter phase, the yielded
value is bound by `as`, and code after `yield` is the exit phase. **Put the exit code in a
`finally`**, or it won't run when the block raises.

```python
from contextlib import contextmanager
import time

@contextmanager
def timer(label):
    start = time.perf_counter()
    try:
        yield                                      # control passes to the with-block
    finally:
        print(f"{label}: {time.perf_counter() - start:.3f}s")

with timer("load"):
    sum(range(10 ** 6))
```

**How it works** is worth being able to explain: the decorator wraps your generator in a helper whose
`__enter__` calls `next(gen)` (running up to the `yield`) and whose `__exit__` either calls
`next(gen)` again on success, or `gen.throw(exc)` on failure — which raises the exception *at the
`yield`*, so your `try/finally` (or `except`) sees it. This is the `throw()` machinery from
[Deep Dive 04 Q7](04_generators_iterators.md#q7-explain-generatorsend-throw-and-close).

The transaction manager becomes noticeably shorter:

```python
@contextmanager
def transaction(conn):
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()            # only reached if the block didn't raise
    except Exception:
        conn.rollback()
        raise                    # re-raise: don't swallow
    finally:
        cur.close()
```

**Class form vs generator form:** use the generator form for simple, one-off, linear setup/teardown
(most cases). Use the class form when the manager needs **state or methods** accessible during the
block, needs to be **reusable/reentrant**, or when the logic is complex enough that a class reads
better. Note that a `@contextmanager` generator is **single-use** — entering the same object twice
raises, because the generator is exhausted.

---

### Q4. How can a context manager suppress an exception?

**By returning a truthy value from `__exit__`.** That tells Python "I handled it, don't propagate."

```python
class Ignore:
    def __init__(self, *exc_types):
        self.exc_types = exc_types

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return exc_type is not None and issubclass(exc_type, self.exc_types)

with Ignore(ZeroDivisionError):
    1 / 0
print("still running")          # the exception was swallowed
```

The stdlib gives you this as **`contextlib.suppress`**:

```python
from contextlib import suppress
import os

with suppress(FileNotFoundError):
    os.remove("temp.txt")        # no-op if it doesn't exist
```

Use it **sparingly and narrowly**. `with suppress(Exception):` is a bare `except: pass` with better
marketing — silent failures are the hardest bugs to find. Suppress one specific, genuinely-expected
exception type, and nothing broader.

A subtlety worth knowing: execution does **not** resume inside the `with` block after a suppressed
exception. It resumes *after* the whole block. So `suppress` around a loop body swallows the rest of
the body too.

---

### Q5. What other `contextlib` utilities are useful?

| Utility | Purpose |
|---|---|
| `ExitStack()` | Manage a **dynamic/variable number** of context managers |
| `suppress(*excs)` | Swallow specific exceptions |
| `closing(thing)` | Call `.close()` on exit — for objects with `close()` but no `__enter__` |
| `nullcontext(value)` | A no-op manager; for conditional `with` without duplicating code |
| `redirect_stdout(f)` / `redirect_stderr(f)` | Capture output from code you can't change |
| `asynccontextmanager` | The `async with` version of `@contextmanager` |
| `AsyncExitStack` | `ExitStack` for async managers |
| `chdir(path)` (3.11+) | Temporarily change working directory |
| `ContextDecorator` | Make a context manager usable as a `@decorator` too |

**`ExitStack`** is the one that solves a problem you can't solve otherwise — opening N files where N
is known only at runtime:

```python
from contextlib import ExitStack

def merge(paths, out_path):
    with ExitStack() as stack:
        handles = [stack.enter_context(open(p)) for p in paths]   # N managers
        out = stack.enter_context(open(out_path, "w"))
        for h in handles:
            out.write(h.read())
    # every handle closed, in reverse order, even if one raised
```

`ExitStack` also supports `stack.callback(fn, *args)` to register arbitrary cleanup, and
`stack.pop_all()` to *transfer* ownership of the cleanups elsewhere — that's how you write a
"construct several resources, and roll them all back if any step fails" factory.

**`nullcontext`** removes an annoying duplication:

```python
from contextlib import nullcontext

cm = open(path) if path else nullcontext(sys.stdin)
with cm as f:
    process(f)          # one code path instead of an if/else around the whole block
```

An `async` example — the shape you'd use for a Kafka producer in a FastAPI `lifespan`:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def producer():
    p = KafkaProducer(...)
    await p.start()
    try:
        yield p
    finally:
        await p.stop()          # flush + close, always

async def main():
    async with producer() as p:
        await p.send("orders", b"hello")
```

---

## Part B — Descriptors

### Q6. What is a descriptor?

**Any object that defines `__get__`, `__set__` or `__delete__` and is stored as a class attribute.**
When you access that attribute on an instance, Python doesn't return the descriptor object — it
calls the descriptor's method.

The protocol:

```python
__get__(self, obj, objtype=None)   # obj is None when accessed on the CLASS
__set__(self, obj, value)
__delete__(self, obj)
__set_name__(self, owner, name)    # 3.6+: called at class creation with the attribute's name
```

Descriptors are not exotic — **they are the mechanism behind almost everything**:

- `property` is a data descriptor.
- `classmethod` and `staticmethod` are non-data descriptors.
- **Plain functions are non-data descriptors**: `func.__get__(obj, cls)` is what produces a *bound
  method*. That's why `obj.method` gets `self` passed automatically.
- Django model `Field`s, SQLAlchemy `Column`s and Pydantic fields are all descriptor-driven.

```python
class Demo:
    def method(self): ...

print(Demo.method)          # <function Demo.method>  — __get__ with obj=None
print(Demo().method)        # <bound method ...>      — __get__ with an instance
print(Demo.method.__get__(Demo(), Demo))   # the same bound method, manually
```

---

### Q7. Data descriptor vs non-data descriptor — how does lookup precedence work?

A **data descriptor** defines `__set__` **or** `__delete__`. A **non-data descriptor** defines only
`__get__`.

Attribute lookup for `obj.x` proceeds in this order:

1. **Data descriptor** found on `type(obj)` (or its MRO) → call its `__get__`.
2. **`obj.__dict__['x']`** → return it.
3. **Non-data descriptor or plain class attribute** on `type(obj)` → call `__get__` or return it.
4. **`__getattr__`** on the type, if defined → call it.
5. `AttributeError`.

*(Steps 1–3 are `object.__getattribute__`; step 4 only fires if 1–3 raised `AttributeError`.)*

**The consequence you're being tested on:** you *can* shadow a method on an instance (methods are
non-data descriptors, step 2 beats step 3), but you *cannot* shadow a `property` (data descriptor,
step 1 beats step 2).

```python
class C:
    def method(self): return "class method"

    @property
    def prop(self): return "class property"

c = C()
c.__dict__["method"] = lambda: "instance override"
print(c.method())                     # 'instance override' — non-data descriptor loses

# c.prop = "x"                        -> AttributeError: property has no setter
c.__dict__["prop"] = "instance value" # we can force it into __dict__...
print(c.prop)                         # ...'class property' — data descriptor still wins
```

This is also why `@cached_property` works the way it does: it's a **non-data** descriptor, so after
it computes the value and writes it into `obj.__dict__`, every later access short-circuits at step 2
and never calls the descriptor again. That's the whole caching mechanism — and it's also why
`cached_property` needs the instance to *have* a `__dict__` (it fails on `__slots__` classes).

---

### Q8. Write a reusable validation descriptor.

Use `__set_name__` (3.6+) to learn the attribute name automatically, store the real value in the
instance `__dict__` under a private name, and validate in `__set__`.

```python
class Positive:
    def __set_name__(self, owner, name):
        self.public = name
        self.private = "_" + name        # where the value actually lives

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self                  # accessed on the class -> return descriptor
        return getattr(obj, self.private)

    def __set__(self, obj, value):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{self.public} must be numeric")
        if value <= 0:
            raise ValueError(f"{self.public} must be > 0, got {value}")
        setattr(obj, self.private, value)

class Order:
    qty = Positive()
    price = Positive()

    def __init__(self, qty, price):
        self.qty = qty                   # goes through Positive.__set__
        self.price = price

o = Order(2, 9.5)
print(o.qty, o.price)                    # 2 9.5
# Order(0, 1)     -> ValueError: qty must be > 0
# Order(True, 1)  -> TypeError (bool is an int subclass — worth guarding)
```

**Why this beats writing two `@property` pairs:** the validation logic is written **once** and reused
for every field. That's the whole reason ORMs and form libraries are descriptor-based — one `Column`
class serves a thousand model fields.

Before `__set_name__` existed you had to pass the name in manually (`qty = Positive("qty")`), which
was error-prone. Mentioning that history shows you know why `__set_name__` was added.

---

### Q9. How is `@property` related to descriptors?

`property` **is** a built-in data descriptor class. `@property` creates a `property` object whose
`__get__` calls your getter function; `.setter` returns a *new* `property` with `__set__` wired to
the setter, and `.deleter` likewise for `__delete__`.

Because it defines `__set__` (even when you haven't supplied a setter — in which case `__set__`
raises `AttributeError`), it is a **data descriptor** and therefore always beats the instance
`__dict__`.

```python
class Temp:
    def __init__(self, celsius):
        self._celsius = celsius

    @property
    def celsius(self):
        return self._celsius

    @celsius.setter
    def celsius(self, value):
        if value < -273.15:
            raise ValueError("below absolute zero")
        self._celsius = value

    @property
    def fahrenheit(self):                # computed, read-only
        return self._celsius * 9 / 5 + 32

t = Temp(25)
print(t.fahrenheit)      # 77.0
t.celsius = 30           # goes through the setter's validation
# t.fahrenheit = 100     -> AttributeError: can't set attribute
```

You can build it from scratch to prove you understand the mechanism:

```python
class MyProperty:
    def __init__(self, fget=None, fset=None):
        self.fget, self.fset = fget, fset

    def __get__(self, obj, objtype=None):
        if obj is None: return self
        if self.fget is None: raise AttributeError("unreadable")
        return self.fget(obj)

    def __set__(self, obj, value):       # defining __set__ makes it a DATA descriptor
        if self.fset is None: raise AttributeError("can't set attribute")
        self.fset(obj, value)

    def setter(self, fset):
        return MyProperty(self.fget, fset)
```

**Design advice to volunteer:** don't write a `property` that just returns `self._x` with no logic —
that's Java `getX()` habit, and in Python a plain public attribute is correct. Add a `property` only
when you need validation, computation, lazy loading, or to preserve a public API while changing
internals. That last point is the key Python argument: **you can turn a plain attribute into a
property later without breaking any caller**, which is why pre-emptive getters are unnecessary.

---

## Part C — Metaclasses

### Q10. What is a metaclass?

A metaclass is **the class of a class** — it controls how class objects are created. Since classes
are themselves objects in Python, they have a type, and that type is their metaclass. The default is
`type`.

```python
class A: pass

print(type(A))            # <class 'type'>      — A's metaclass
print(type(A()))          # <class '__main__.A'> — an instance's type
print(type(type))         # <class 'type'>      — type is its own metaclass
```

A `class` statement is roughly sugar for a call to `type`:

```python
class Dog:
    def speak(self): return "woof"

# is approximately:
Dog = type("Dog", (), {"speak": lambda self: "woof"})
#          name   bases  namespace

d = Dog()
print(d.speak(), type(Dog))     # woof <class 'type'>
```

A custom metaclass subclasses `type` and overrides:

- **`__new__(mcs, name, bases, namespace)`** — create/modify the class object. Use this to *validate
  or rewrite* the class.
- **`__init__(cls, name, bases, namespace)`** — initialise an already-created class. Use this for
  side effects like registration.
- **`__call__(cls, *args)`** — intercept **instantiation** of the class (i.e. `MyClass(...)`). Use
  this for singletons or instance caching.

---

### Q11. Write a metaclass that enforces a rule on subclasses.

Override `__new__` to inspect the namespace before the class exists.

```python
class RequireRun(type):
    def __new__(mcs, name, bases, ns):
        if bases and "run" not in ns:              # `bases` is empty for the root class
            raise TypeError(f"{name} must define run()")
        return super().__new__(mcs, name, bases, ns)

class Job(metaclass=RequireRun):
    pass                                           # root: exempt

class EmailJob(Job):
    def run(self): return "sent"

# class BadJob(Job): pass
# -> TypeError: BadJob must define run()   ... raised at IMPORT time, not call time
```

**The value proposition:** the error surfaces at *import* time, the instant the module loads, rather
than at 3 a.m. when someone calls `.run()`. That's the legitimate case for a metaclass — enforcing an
invariant across an entire class hierarchy.

`if bases and ...` is the standard guard so the abstract root itself isn't rejected.

---

### Q12. Implement a Singleton with a metaclass. Is it a good idea?

Override `__call__` on the metaclass so that instantiating the class returns a cached instance.

```python
class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class Config(metaclass=Singleton):
    def __init__(self):
        self.loaded_at = "startup"

print(Config() is Config())      # True
```

**It works, and you should say it's usually the wrong choice.** Singletons are global mutable state:
they make tests order-dependent (one test's mutation leaks into the next), they hide dependencies
(a function's real inputs aren't in its signature), and they're awkward to substitute.

The Pythonic alternatives, in order:

```python
# 1. A module-level instance. Modules are already singletons — imported once, cached in sys.modules.
settings = Settings()          # in config.py; `from config import settings` everywhere

# 2. functools.lru_cache on a factory — lazy, and clearable in tests
from functools import lru_cache

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
# get_settings.cache_clear() in a fixture

# 3. Dependency injection — the actual right answer for a service
@app.get("/x")
async def endpoint(settings: Settings = Depends(get_settings)):
    ...
# app.dependency_overrides[get_settings] = lambda: TestSettings()
```

Option 3 is what the [FastAPI app in this repo](../05_web_apis_fastapi/app/dependencies.py) uses, and
it's the answer that shows you think about testability.

Also note the metaclass singleton above is **not thread-safe** — two threads can both pass the `if`
before either writes. A `threading.Lock` with double-checked locking is needed for real use, which is
one more reason to prefer the alternatives.

---

### Q13. What are the alternatives to metaclasses?

This is the question that actually matters, because the answer is "almost always, use one of these":

**1. `__init_subclass__`** (3.6+) — a hook on the *parent* called whenever a subclass is created.
Covers registration and validation, which is 90% of metaclass use, with none of the complexity or
MRO conflicts.

```python
class Plugin:
    registry = {}

    def __init_subclass__(cls, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        Plugin.registry[key or cls.__name__] = cls

class CsvPlugin(Plugin, key="csv"): pass
class JsonPlugin(Plugin, key="json"): pass

print(Plugin.registry)     # {'csv': <class 'CsvPlugin'>, 'json': <class 'JsonPlugin'>}
```

Note the class-keyword argument (`key="csv"`) — that's how you pass configuration without a
metaclass.

**2. Class decorators** — simpler, explicit, and composable. Use when you want to opt in per class
rather than infect a hierarchy:

```python
def register(cls):
    REGISTRY[cls.__name__] = cls
    return cls

@register
class CsvParser: ...
```

**3. `__set_name__` on descriptors** — for the specific job of "a field needs to know its own name",
which used to require a metaclass.

**4. `abc.ABC` / `@abstractmethod`** — for enforcing that subclasses implement an interface. Note
this *is* metaclass-powered (`ABCMeta`), but you get it declaratively.

**5. `typing.Protocol`** — structural typing with no inheritance at all, checked statically.

**The decision rule:** you need a real metaclass only when you must **modify the class namespace
itself** at creation time — rewriting attributes, collecting declarative fields into metadata,
controlling instantiation for every class in a hierarchy. If you're only reacting to subclass
creation, `__init_subclass__` is strictly better.

> **Java contrast.** There is no metaclass. The nearest equivalents are annotation processors
> (compile-time code generation, like Lombok) and reflection-driven frameworks (Spring scanning for
> `@Component`). Python does at *class-definition time* what Java does at *compile time* or via
> *runtime reflection*.

---

### Q14. Where are metaclasses used in real frameworks?

Knowing concrete examples proves you've read library source, not just tutorials:

- **Django** — `ModelBase` scans the class namespace for `Field` descriptors, builds the `_meta`
  options object, wires up the manager, registers the model in the app registry, and creates the
  table mapping. `class User(models.Model): name = CharField()` becomes an ORM mapping because
  `ModelBase.__new__` walked the namespace.
- **SQLAlchemy** — `DeclarativeMeta` does the equivalent for `Column` attributes.
- **Pydantic** — `ModelMetaclass` collects annotated fields, builds the validators, and (in v2)
  compiles the validation core. This runs **once at import**, which is why Pydantic validation is
  fast at request time.
- **`abc.ABCMeta`** — tracks abstract methods and blocks instantiation of incomplete subclasses.
- **`enum.EnumMeta`** — turns class attributes into singleton members, makes the class iterable, and
  prevents reassignment.

The unifying pattern: **run code once, at class-definition time, to build metadata that makes runtime
fast.** That's the legitimate reason metaclasses exist.

---

## Worked example — async context manager for a Kafka-style client

The exact shape you'd use in a FastAPI `lifespan` to guarantee the producer is flushed on shutdown.

```python
from contextlib import asynccontextmanager
import asyncio

class FakeProducer:
    async def start(self):           print("connected")
    async def stop(self):            print("flushed & closed")
    async def send(self, topic, v):  print("sent", topic, v)

@asynccontextmanager
async def producer():
    p = FakeProducer()
    await p.start()
    try:
        yield p
    finally:
        await p.stop()               # runs on success, on exception, on cancellation

async def main():
    async with producer() as p:
        await p.send("orders", b"hello")
        # raise RuntimeError("boom")  <- uncomment: "flushed & closed" still prints

asyncio.run(main())
```

**Why `finally` and not just code after the `yield`:** if the body raises, `@asynccontextmanager`
throws that exception *into* the generator at the `yield` point. Without `finally`, the `stop()` line
is skipped and you lose every buffered message. That's a data-loss bug, not a tidiness issue — see
[Kafka delivery semantics](14_kafka_pipelines_delivery_semantics.md).

---

## Hands-on drills

1. Write a context manager whose `__exit__` returns `True`, and one that returns `False`. Raise
   inside both and observe the difference. Then explain when suppressing is defensible.
2. Convert the class-based `Transaction` to `@contextmanager`. Remove the `finally` and prove the
   cursor leaks on exception.
3. Use `ExitStack` to open a list of N files where N comes from `sys.argv`. Make one of them a
   nonexistent path and confirm the already-opened handles still close.
4. Write the `Positive` descriptor. Then add a `__delete__` and observe how the class changes from
   non-data to data descriptor and what that does to instance shadowing.
5. Put a plain method, a `property` and a `cached_property` on one class. Try to shadow each via
   `obj.__dict__` and explain the three different outcomes using the precedence rules.
6. Write `RequireRun` and define a non-compliant subclass. Note the error appears at **import**.
   Rewrite it using `__init_subclass__` and compare the code length.
7. Implement the metaclass singleton, then break it with two threads racing in `__call__`. Fix it
   with a lock, then throw it away and use `lru_cache(maxsize=1)` instead.

---

## The 60-second spoken answer

> "A context manager guarantees teardown through `__enter__`/`__exit__` — `__exit__` always runs, and
> if it returns truthy it suppresses the exception, which I avoid except via a narrow
> `contextlib.suppress`. For simple cases I use `@contextmanager` with the cleanup in a `finally`,
> because the decorator throws the exception in at the `yield`; `ExitStack` handles a dynamic number
> of resources. A descriptor is any object with `__get__`/`__set__`/`__delete__` stored on a class —
> it's the machinery behind `property`, `classmethod`, and bound methods, since a plain function is a
> non-data descriptor whose `__get__` binds `self`. Data descriptors beat the instance `__dict__`,
> non-data ones lose to it, which is why you can shadow a method on an instance but not a property,
> and why `cached_property` works by writing into `__dict__` once. A metaclass is the class of a
> class; `type` is the default, and you override `__new__` to validate or `__call__` to control
> instantiation. Django, SQLAlchemy and Pydantic all use one to collect declarative fields at import
> time. But for registries and subclass validation I reach for `__init_subclass__` or a class
> decorator — if you're wondering whether you need a metaclass, you don't."
