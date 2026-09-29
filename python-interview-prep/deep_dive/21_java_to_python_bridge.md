# Deep Dive 21 — Java → Python Bridge (syntax, idioms, and the traps)

> Runnable companion: [`01_python_core/11_java_to_python_bridge.py`](../01_python_core/11_java_to_python_bridge.py)
> Related deep dives: [OOP](06_oop_inheritance_mro.md) · [Concurrency](07_concurrency.md) ·
> [Web frameworks](10_web_frameworks.md) · [Comprehensions & map/filter/reduce](02_comprehensions_map_filter_reduce.md)

## Why this page exists

You already know the **concepts** — inheritance, interfaces, threads, streams, DI, generics. What
differs is the **syntax**, the **idiom**, and a handful of places where Python's semantics are
genuinely not what a Java developer expects.

This page is organised around that: a translation table for the things that map cleanly, then the
traps where a Java habit produces working-but-wrong Python, then the code smells that mark someone
as "writing Java in Python" in a code review.

---

## Part 1 — The translation table

### Types and collections

| Java | Python | Notes |
|---|---|---|
| `int`, `long` | `int` | **Arbitrary precision** — no overflow, ever |
| `double`, `float` | `float` | Always 64-bit |
| `BigDecimal` | `decimal.Decimal` | Same reason: never use `float` for money |
| `boolean` | `bool` | `True`/`False`, capitalised |
| `String` | `str` | Immutable in both; Python has no `StringBuilder` — use `"".join(parts)` |
| `char` | `str` of length 1 | No separate character type |
| `null` | `None` | Compare with `is None`, never `== None` |
| `Object` | `object` | |
| `ArrayList<T>` | `list` | Dynamic array in both |
| `LinkedList<T>`, `ArrayDeque<T>` | `collections.deque` | O(1) both ends |
| `HashMap<K,V>` | `dict` | **Insertion-ordered since 3.7** — it's already a `LinkedHashMap` |
| `HashSet<T>` | `set` | |
| `Set.of(...)` / immutable set | `frozenset` | Hashable, so usable as a dict key |
| `T[]` array | `list`, or `array.array` / `numpy.ndarray` for numerics | |
| `Optional<T>` | `T \| None` (type hint) | No wrapper object; just return `None` |
| `record Point(int x, int y)` | `@dataclass(frozen=True)` or `NamedTuple` | |
| `enum Color { RED }` | `class Color(enum.Enum): RED = 1` | |
| `Map.Entry<K,V>` | a 2-tuple from `d.items()` | |

**The one that surprises everyone:** Python's `int` is **arbitrary precision**. `2 ** 1000` is an
exact integer. There is no `long`, no overflow, and no `Math.addExact`. Integer overflow bugs simply
do not exist.

### Declarations and control flow

| Java | Python |
|---|---|
| `final int x = 5;` | `x = 5` (or `x: Final[int] = 5` — a hint only, not enforced) |
| `int[] a = {1,2,3};` | `a = [1, 2, 3]` |
| `for (int i = 0; i < n; i++)` | `for i in range(n):` |
| `for (String s : list)` | `for s in items:` |
| `while (cond) { }` | `while cond:` |
| `switch (x) { case 1: … }` | `match x:` / `case 1:` (3.10+), or a dict dispatch |
| `x ? a : b` | `a if x else b` |
| `x != null ? x : y` | `x if x is not None else y`, or `x or y` (careful — `0` and `""` are falsy) |
| `try { } catch (E e) { } finally { }` | `try: / except E as e: / else: / finally:` |
| `throw new E("m")` | `raise E("m")` |
| `throws IOException` | Nothing — **Python has no checked exceptions** |
| `assert x > 0 : "msg";` | `assert x > 0, "msg"` (**disabled under `-O`** — never for validation) |

### Classes and methods

```java
// JAVA
public class Order {
    private final String id;
    private double amount;

    public Order(String id, double amount) {
        this.id = id;
        this.amount = amount;
    }

    public String getId() { return id; }
    public double getAmount() { return amount; }
    public void setAmount(double amount) {
        if (amount < 0) throw new IllegalArgumentException("negative");
        this.amount = amount;
    }

    @Override
    public String toString() { return "Order{" + id + ", " + amount + "}"; }

    public static Order fromString(String s) { ... }
}
```

```python
# PYTHON — the direct translation
class Order:
    def __init__(self, id: str, amount: float):
        self._id = id            # _ is a convention, not enforcement
        self._amount = amount

    @property
    def id(self) -> str:         # read-only: no setter defined
        return self._id

    @property
    def amount(self) -> float:
        return self._amount

    @amount.setter
    def amount(self, value: float):
        if value < 0:
            raise ValueError("negative")
        self._amount = value

    def __repr__(self) -> str:   # ~ toString(), but for developers
        return f"Order({self._id!r}, {self._amount})"

    @classmethod
    def from_string(cls, s: str) -> "Order":   # ~ static factory; cls respects subclassing
        ...
```

```python
# PYTHON — what you'd actually write, if there's no validation
from dataclasses import dataclass

@dataclass
class Order:
    id: str
    amount: float
# __init__, __repr__ and __eq__ generated. Attributes are public.
```

**The key differences:**

- **`self` is explicit** and is the first parameter of every instance method. It is *not* a keyword;
  the name is convention (but never deviate).
- **No `public`/`private`/`protected`.** `_x` means "internal, by convention"; `__x` triggers name
  mangling to avoid subclass collisions — **neither is access control**.
- **No pre-emptive getters/setters.** Start with a public attribute. You can convert it to a
  `@property` **later without breaking any caller**, which is precisely why Java's defensive
  accessor habit is unnecessary here. Writing `get_name()` in Python is the loudest Java accent
  there is.
- **`@classmethod` replaces static factories** — and `cls` means a subclass calling
  `USDate.from_string(...)` gets a `USDate` back, not a `Date`.
- **`__repr__` before `__str__`.** `__repr__` is what you see in tracebacks and debuggers, and it's
  the fallback for `__str__`. Always define it.

### Interfaces and abstract classes

| Java | Python |
|---|---|
| `interface Payable { void pay(); }` | `class Payable(ABC): @abstractmethod def pay(self): ...` |
| `interface` (structural use) | `typing.Protocol` — **no inheritance required** |
| `abstract class` | `class X(ABC)` with a mix of abstract and concrete methods |
| `implements A, B` | `class C(A, B)` — Python has real multiple inheritance |
| `@Override` | Nothing (no compiler check; `@typing.override` in 3.12 for type checkers) |
| `default` method in an interface | A concrete method on an `ABC`, or a **mixin** |

```python
from abc import ABC, abstractmethod
from typing import Protocol

# Nominal — like a Java interface: the implementer must inherit
class PaymentGateway(ABC):
    @abstractmethod
    def charge(self, amount: float) -> str: ...

# Structural — no equivalent in Java before... anything. Duck typing, statically checked.
class SupportsCharge(Protocol):
    def charge(self, amount: float) -> str: ...

def process(gw: SupportsCharge, amt):   # accepts ANY object with a matching charge()
    return gw.charge(amt)
```

**`Protocol` is the one with no Java analogue** and it's worth understanding: the implementing class
never imports or mentions the protocol. You can retrofit a type contract onto a **third-party class
you don't control** — impossible with a Java interface.

### Streams → comprehensions

| Java Stream | Python |
|---|---|
| `list.stream().map(f).collect(toList())` | `[f(x) for x in items]` |
| `.filter(p)` | `[x for x in items if p(x)]` |
| `.map(f).filter(p)` | `[f(x) for x in items if p(x)]` |
| `.mapToInt(...).sum()` | `sum(f(x) for x in items)` |
| `.anyMatch(p)` / `.allMatch(p)` | `any(p(x) for x in items)` / `all(...)` |
| `.count()` | `len(items)` or `sum(1 for x in items if p(x))` |
| `.max(cmp)` | `max(items, key=...)` |
| `.sorted(comparing(X::getY))` | `sorted(items, key=lambda x: x.y)` or `operator.attrgetter("y")` |
| `.distinct()` | `set(items)`, or `list(dict.fromkeys(items))` to keep order |
| `.limit(n)` | `items[:n]` or `itertools.islice(gen, n)` |
| `.flatMap(...)` | `[y for x in items for y in x]` |
| `.reduce(id, f)` | `functools.reduce(f, items, id)` — **but prefer `sum`/`max`/`math.prod`** |
| `Collectors.groupingBy(f)` | `defaultdict(list)` loop, or `itertools.groupby` (sort first!) |
| `Collectors.toMap(k, v)` | `{k(x): v(x) for x in items}` |
| `Collectors.joining(", ")` | `", ".join(strings)` |
| `.parallelStream()` | `concurrent.futures` — **no free parallelism; the GIL is real** |
| Lazy stream | **Generator expression** `(f(x) for x in items)` |

```java
// JAVA
Map<String, List<Order>> byStatus = orders.stream()
    .filter(o -> o.getAmount() > 100)
    .collect(Collectors.groupingBy(Order::getStatus));
```

```python
# PYTHON
from collections import defaultdict

by_status = defaultdict(list)
for o in orders:
    if o.amount > 100:
        by_status[o.status].append(o)
```

**`.parallelStream()` has no equivalent.** The GIL means threads don't parallelise CPU-bound Python.
For real parallelism you need `ProcessPoolExecutor` — with pickling overhead and no shared memory.
See [Concurrency](07_concurrency.md).

### Concurrency

| Java | Python |
|---|---|
| `new Thread(r).start()` | `threading.Thread(target=f).start()` |
| `ExecutorService` / `ThreadPoolExecutor` | `concurrent.futures.ThreadPoolExecutor` |
| `Future<T>` / `CompletableFuture<T>` | `concurrent.futures.Future` / `asyncio.Future` |
| `synchronized` block/method | `with threading.Lock():` |
| `ReentrantLock` | `threading.RLock` |
| `Semaphore` | `threading.Semaphore` / `asyncio.Semaphore` |
| `CountDownLatch` | `threading.Event` or `Barrier` |
| `BlockingQueue` | `queue.Queue` / `asyncio.Queue` |
| `AtomicInteger` | **No direct equivalent** — use a `Lock`, or `queue` |
| `volatile` | No equivalent needed (the GIL provides the barrier) |
| `@Async` / `CompletableFuture` chains | `async def` + `await` |
| Virtual threads (21+) | `asyncio` coroutines — but **cooperative**, not preemptive |
| `ThreadLocal<T>` | `threading.local()` — or **`contextvars.ContextVar`** for async |

**Two genuinely different semantics, and both cause bugs:**

1. **The GIL.** Java threads run bytecode in parallel; CPython's do not. Threads help **I/O**, not
   CPU. Answer "use threads for CPU-bound work" and you've failed the round.
2. **Cooperative vs preemptive.** A Java virtual thread yields automatically at any blocking call. A
   Python coroutine yields **only at `await`**. One `time.sleep()` or `requests.get()` inside
   `async def` **freezes the entire event loop** — every concurrent request on that worker. There is
   no Java equivalent of this failure mode.

**For async code use `contextvars.ContextVar`, not `threading.local`** — `ContextVar` follows the
asyncio task, so concurrent requests sharing a thread keep separate values. Using `threading.local`
in async code leaks state between requests.

### Frameworks: Spring Boot → FastAPI

| Spring Boot | FastAPI |
|---|---|
| `@RestController` + `@RequestMapping` | `APIRouter` + `@router.get/post` |
| `@RequestBody` DTO + `@Valid` | A Pydantic model parameter (validated automatically) |
| `@PathVariable` / `@RequestParam` | Path template params / typed function params |
| `@Autowired`, constructor injection | `Depends()` — **per request, explicit in the signature** |
| `@Service`, `@Repository`, `@Component` | Plain classes + a `Depends()` provider |
| `@ControllerAdvice` / `@ExceptionHandler` | `@app.exception_handler(...)` |
| `Filter` / `HandlerInterceptor` | Middleware (`@app.middleware("http")`) |
| `application.yml` + `@ConfigurationProperties` | `pydantic-settings` `BaseSettings` |
| Spring Data JPA / Hibernate | SQLAlchemy (+ Alembic for migrations) |
| `@Transactional` | An explicit `async with session.begin():` block |
| Spring Actuator | A hand-rolled `/health` + `prometheus-fastapi-instrumentator` |
| Springdoc / Swagger annotations | OpenAPI generated **automatically** from type hints |
| Spring Kafka `@KafkaListener` | A `confluent-kafka` / `aiokafka` consumer in a lifespan task |
| JUnit + Mockito + `@MockBean` | pytest + `TestClient` + **`app.dependency_overrides`** |
| Maven / Gradle | pip + `pyproject.toml` (Poetry / uv) |
| Lombok `@Data` | `@dataclass` (built in — no annotation processor) |

**The two structural differences:**

- **No component scanning.** Python has no classpath scanning; you `import` and wire explicitly.
  Less magic, more visible.
- **`@Transactional` doesn't exist.** SQLAlchemy transaction boundaries are explicit blocks. That's
  arguably better — the boundary is visible in the code rather than inferred from an annotation and a
  proxy.

---

## Part 2 — The traps

These are the places where a Java habit produces Python that **runs** but is **wrong**.

### Trap 1 — Mutable default arguments

```java
// Java: a new list every call. Obviously.
void add(String item, List<String> bucket) { ... }
```

```python
def add(item, bucket=[]):        # BAD — evaluated ONCE, at definition time
    bucket.append(item)
    return bucket

print(add(1))    # [1]
print(add(2))    # [1, 2]   <- the SAME list, shared across calls

def add(item, bucket=None):      # GOOD
    bucket = [] if bucket is None else bucket
    bucket.append(item)
    return bucket
```

**Default values are evaluated once, at `def` time**, and stored on the function object. Nothing in
Java prepares you for this. It is the most-cited Python gotcha for a reason.

### Trap 2 — `==` vs `is`

```python
a = 256; b = 256
print(a is b)     # True — small ints are cached

a = 257; b = 257
print(a is b)     # often False
```

Same trap as Java's `Integer` cache for −128..127, but easier to hit because `is` reads so naturally.
**Use `is` only for `None`, `True`, `False` and sentinels.** Everything else uses `==`.

### Trap 3 — No checked exceptions

Java's compiler forces you to handle or declare. Python's does not — **any function can raise
anything**, and nothing tells you. Consequences:

- **Read the docs and the source** to know what a call can raise.
- **Be explicit about what you catch.** A bare `except:` also catches `KeyboardInterrupt`,
  `SystemExit` and `asyncio.CancelledError`, making your process unkillable.
- **Build your own exception hierarchy** rooted in one application base class, because the compiler
  won't organise it for you. See [Error handling](08_error_handling.md).

### Trap 4 — Truthiness

```java
if (list != null && !list.isEmpty()) { }
```

```python
if items:                        # empty list, dict, set, str, 0, None are ALL falsy
    ...

# The trap:
count = 0
if count:                        # False! But 0 might be a perfectly valid value
    ...
if count is not None:            # what you actually meant
    ...

# The `or` default trap:
timeout = user_timeout or 30     # if user_timeout is 0, you silently get 30
timeout = 30 if user_timeout is None else user_timeout   # correct
```

Empty collections being falsy is convenient. `0` and `""` being falsy is where Java developers get
caught, particularly with `or` defaults.

### Trap 5 — Shallow copies and aliasing

```python
a = [[1, 2], [3, 4]]
b = a.copy()          # shallow — inner lists are SHARED
a[0].append(99)
print(b)              # [[1, 2, 99], [3, 4]]

import copy
c = copy.deepcopy(a)  # fully independent
```

Same as Java's `clone()` semantics, but Python's `=` binds a **name to an object** — there is no
value copying anywhere, ever. `b = a` gives two names for one list.

### Trap 6 — No method overloading

```java
void process(int x) { }
void process(String x) { }     // fine in Java
```

```python
def process(x: int): ...
def process(x: str): ...       # the second SILENTLY REPLACES the first
```

No error, no warning — the name simply rebinds. Use default arguments, `*args`, or
`functools.singledispatch`. See [OOP Q14](06_oop_inheritance_mro.md#q14-method-overriding-vs-overloading-in-python).

### Trap 7 — `super()` is not "the parent"

With real multiple inheritance, `super()` goes to the **next class in the MRO of the instance's
type** — which may be a class the current class has never heard of.

```python
class D(B, C): ...
# super() inside B reaches C when the instance is a D, NOT A.
```

Java has no analogue because it has no multiple class inheritance. This is the
[single most important OOP difference](06_oop_inheritance_mro.md#q5-what-exactly-does-super-do).

### Trap 8 — Type hints are not enforced

```python
def charge(amount: float) -> bool:
    ...
charge("not a number")      # runs happily; no error at runtime
```

Hints are **documentation and a static-analysis input**. Nothing checks them at runtime unless you
use Pydantic or a runtime validator. **Run `mypy` in CI** or the hints slowly rot into lies.

Pydantic is the exception — it validates and **coerces** at runtime, which is exactly why FastAPI
uses it at the system boundary.

### Trap 9 — Late-binding closures

```python
fns = [lambda: i for i in range(3)]
print([f() for f in fns])          # [2, 2, 2] — not [0, 1, 2]

fns = [lambda i=i: i for i in range(3)]
print([f() for f in fns])          # [0, 1, 2]
```

Java forbids this by requiring captured locals to be effectively final. Python allows it and gives
the surprising answer.

### Trap 10 — Import-time side effects

Module-level code runs **on import**, once, and the module is then cached in `sys.modules`. Decorators
run at import time. A slow module-level operation slows every startup, and **circular imports** are a
runtime `ImportError`, not a compile error. Keep module level to definitions and constants.

---

## Part 3 — Code smells that say "Java developer"

A reviewer spots these instantly. Worth auditing your own code for them.

| Smell | Instead |
|---|---|
| `get_name()` / `set_name()` for a plain field | A public attribute; add `@property` **only** when you need logic |
| `if type(x) == Order:` | `isinstance(x, Order)` — or better, duck typing / `Protocol` |
| `for i in range(len(items)):` then `items[i]` | `for item in items:` or `for i, item in enumerate(items):` |
| `while i < len(x): ... i += 1` | `for x in items:` |
| A class with one method and no state | A plain function |
| `AbstractOrderProcessorFactoryImpl` | `process_order()` |
| Deep inheritance hierarchies | Composition, or two or three thin mixins |
| A DI container library | `Depends()`, or constructor injection |
| `try: ... except Exception: pass` | Catch the narrowest type; log and re-raise |
| Interfaces for everything | `Protocol` where useful; duck typing otherwise |
| Manual `str` concatenation in a loop | `"".join(parts)` |
| `list.append` in a loop building a new list | A list comprehension |
| `map(lambda x: x*2, xs)` | `[x * 2 for x in xs]` |
| `x == None` | `x is None` |
| `if len(items) > 0:` | `if items:` |
| `Thread` per unit of work | `ThreadPoolExecutor`, or `asyncio` |
| Singleton via a metaclass | A module-level instance, `lru_cache`, or DI |
| Checking types at every boundary | Type hints + `mypy`; Pydantic at the **edges only** |

**The umbrella principle:** Python trusts the caller. It has no `private`, no checked exceptions and
no compiler-enforced interfaces — and the idiom is to lean on **tests, type checkers and
conventions** rather than trying to reconstruct compile-time guarantees at runtime.

---

## Part 4 — Migrating a Java/Scala service to Python

A likely interview question with Java on your CV. Structure the answer in phases.

**Phase 1 — Discovery.** Inventory modules, dependencies, integrations and SLAs. Classify each
component:
- **Pure business logic** → easy to port.
- **Framework-heavy** (Spring) → FastAPI, with rewiring.
- **Spark/Scala jobs** → PySpark, often a near 1:1 transformation translation.
- **CPU-bound hot paths** → the risk area. Python may be 10–50× slower. Keep as a service, or
  rewrite the hot path in Rust/C (PyO3, Cython) — or don't migrate it.

**Phase 2 — Architecture mapping.**

| Java/Scala | Python |
|---|---|
| Spring Boot REST | FastAPI |
| Hibernate / JPA | SQLAlchemy (async) + Alembic |
| Spring Security JWT | PyJWT + FastAPI dependencies |
| Spring Kafka | `confluent-kafka-python` / `aiokafka` |
| Scala Spark | PySpark |
| JUnit + Mockito | pytest + `unittest.mock` |
| Maven/Gradle | `pyproject.toml` + Poetry/uv |
| Jackson | Pydantic |

**Phase 3 — Incremental migration via the strangler fig.** Replace one service or endpoint at a time
behind the **same API contract**. Run both in parallel, **shadow traffic** to the new one and compare
outputs, then ramp 1% → 5% → 25% → 100%. **Never a big-bang rewrite.** See
[Scaling Q8](12_scaling_applications.md#q8-what-is-the-strangler-fig-pattern-for-zero-downtime-migration).

**Phase 4 — The watch-outs to raise unprompted:**

1. **Static typing is gone.** Add type hints and enforce `mypy` in CI from day one, or you lose the
   safety net that made the Java code maintainable.
2. **Concurrency must be redesigned, not translated.** Java threads map 1:1 to OS threads with true
   parallelism. A direct port of a thread-per-request design will underperform badly. Rethink it as
   asyncio or multiprocessing.
3. **Performance benchmark every migrated component** against the original. "It's fast enough" must
   be measured, not assumed.
4. **No compile-time errors.** A typo that Java caught at build time is now a runtime `AttributeError`
   in production. Compensate with type checking, higher test coverage and linting.
5. **Packaging and deployment differ** — virtualenvs, wheels, a very different dependency-resolution
   story from Maven.
6. **Team skills.** Idiomatic Python is not Java-with-different-syntax; budget for review and
   pairing, or you'll end up with a Java codebase written in Python, which has the disadvantages of
   both.

---

## The things Python has that Java doesn't

Worth knowing so you actually *use* the language rather than emulating Java in it:

| Feature | Why it matters |
|---|---|
| **Comprehensions** | Streams without the ceremony, and they read left-to-right |
| **Generators (`yield`)** | Lazy sequences in three lines; O(1) memory over infinite streams |
| **Decorators** | Cross-cutting concerns without AOP, proxies or bytecode weaving |
| **Context managers (`with`)** | try-with-resources, but for **any** setup/teardown pair |
| **Multiple inheritance + MRO** | Real mixins with state |
| **Duck typing + `Protocol`** | Structural contracts without inheritance; retrofit onto third-party types |
| **First-class functions everywhere** | No `@FunctionalInterface`, no boxing |
| **Tuple unpacking** | `a, b = b, a`; `x, *rest = items` |
| **f-strings** | `f"{x=}"` prints `x=5` — superb for debugging |
| **Keyword arguments** | Self-documenting calls; no builder pattern needed |
| **`*args` / `**kwargs`** | Genuinely generic wrappers |
| **REPL** | Interactive exploration of live objects |
| **Slicing** | `items[::-1]`, `items[2:5]`, `items[::2]` |
| **Arbitrary-precision ints** | No overflow, ever |
| **The walrus operator** | Assign and test in one expression |
| **`match` statements** | Structural pattern matching, not just value switching |

---

## Hands-on drills

1. Take a Java class you know well with getters, setters and a static factory. Write the literal
   translation, then rewrite it as a `@dataclass` with one `@property`. Compare the line counts.
2. Translate five Java Stream chains into comprehensions. Then translate the `groupingBy` one and
   notice there's no direct equivalent — use `defaultdict(list)`.
3. Write `def f(x, items=[])`, call it three times, and explain the output.
4. Build a diamond inheritance hierarchy and print `__mro__`. Explain why `super()` in `B` reaches
   `C`. There is no Java code that does this.
5. Write an `async def` endpoint that calls `requests.get`. Fire 10 concurrent requests and measure.
   Change it to `def` and measure again.
6. Take a `synchronized` counter from Java, write the naive Python version, run it with 4 threads,
   and show the lost updates. Fix it with a `Lock`.
7. Write the same interface twice — once as `abc.ABC`, once as `typing.Protocol`. Implement the
   Protocol version **without importing it** and confirm `mypy` still checks it.
8. Write a `@retry` decorator. Compare it to how you'd do the same in Spring (`@Retryable` + AOP) and
   note that Python needs no proxying or bytecode manipulation.

---

## The 60-second spoken answer

> "The concepts transfer — inheritance, interfaces, DI, streams — but three things are genuinely
> different rather than just syntactically different. First, the GIL: Java threads give real
> parallelism, CPython's don't, so threads are for I/O and processes are for CPU, and asyncio is
> cooperative rather than preemptive — one blocking call inside `async def` freezes every concurrent
> request, which has no Java equivalent. Second, Python has real multiple inheritance, so `super()`
> means 'the next class in the MRO of the instance's type', not 'the parent' — inside `B` it can
> reach a class `B` has never heard of. Third, nothing is enforced: no private, no checked
> exceptions, and type hints aren't checked at runtime, so I lean on `mypy` in CI, a deliberate
> exception hierarchy, and Pydantic at the system boundary to get back what the compiler used to give
> me. Idiomatically I've had to unlearn some habits — no pre-emptive getters and setters, because a
> public attribute can become a property later without breaking callers; comprehensions instead of
> Streams; `isinstance` and duck typing instead of type checks; and functions where Java would want a
> class. The traps that actually bit me were mutable default arguments, which are evaluated once at
> definition time, and `0` and empty string being falsy, which breaks the `x or default` idiom."
