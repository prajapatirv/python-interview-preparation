"""
Java -> Python, part 2: the language features a Java developer looks for and cannot find.

11_java_to_python_bridge.py covers the seven traps and the bean -> dataclass translation.
This file answers the "where did X go?" questions:

  final / final class / final method    -> section 1-2  (Python has NO runtime enforcement)
  sealed interfaces                     -> section 3    (union types + exhaustive match)
  abstract classes vs interfaces        -> section 4
  public static void main(String[])     -> section 5    (if __name__ == "__main__")
  Stream API                            -> section 6    (comprehensions, and the laziness story)
  virtual threads (Java 21)             -> section 7    (THREE different Python answers)
  generics / type erasure               -> section 8
  static + instance initialiser blocks  -> section 9
  equals / hashCode / toString          -> section 10
  enum                                  -> section 11
  checked exceptions                    -> section 12

The theme running through all of it: **Java enforces at compile time what Python enforces by
convention, a type checker, or not at all.** Knowing which of the three applies to each feature is
the actual skill.

TWO THINGS ABOUT THIS FILE'S OWN STRUCTURE, both of which are section 5's lesson:

  1. Every class and function is at MODULE level, but all the printing lives in `main()` under an
     `if __name__ == "__main__":` guard. That is not style -- section 7 uses ProcessPoolExecutor,
     which on Windows/macOS re-imports this module in every child process. Narration at module
     level would print once per child (six times, when I first wrote it); spawning at module level
     raises RuntimeError outright.
  2. `cpu_bound` MUST stay at module level, because arguments and functions are PICKLED across the
     process boundary -- a nested function or lambda cannot be.

NOTE: section 7 runs a ~8s CPU benchmark (4 x 6M-iteration loops, four ways). The numbers are the
point, and they make this one of the slower files in the repo.

Run me: python 17_java_to_python_advanced.py
"""
import concurrent.futures as cf
import enum
import functools
import itertools
import sys
import sysconfig
import time
import typing
from collections import Counter, defaultdict
from dataclasses import FrozenInstanceError, dataclass


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ 1. final: the immutable object
@dataclass(frozen=True, slots=True)
class Money:
    """The closest thing to a Java `record` (or a class of `private final` fields):
    frozen=True generates a __setattr__ that raises, so the instance really is read-only."""
    amount_cents: int
    currency: str = "USD"


# ================================================================ 2. final method / final class
@typing.final                               # checker-only: "do not subclass this"
class CheckerFinal:
    @typing.final                           # checker-only: "do not override this"
    def critical(self):
        return "must not change"


class IgnoredIt(CheckerFinal):              # mypy: error. CPython: allowed.
    def critical(self):
        return "overridden anyway"


class SealedMeta(type):
    """Runtime enforcement, option A: a metaclass that inspects the bases."""

    def __new__(mcls, name, bases, namespace, **kwargs):
        for base in bases:
            if base.__dict__.get("__is_final__", False):
                raise TypeError(f"{base.__name__} is final and cannot be subclassed")
        return super().__new__(mcls, name, bases, namespace, **kwargs)


class ReallyFinal(metaclass=SealedMeta):
    __is_final__ = True


class FinalViaHook:
    """Runtime enforcement, option B: __init_subclass__. Lighter and far easier to read than a
    metaclass -- and it fires at CLASS DEFINITION, i.e. at import, like Java's compile error."""

    def __init_subclass__(cls, **kwargs):
        raise TypeError("FinalViaHook is final; compose instead of inheriting")


class Visibility:
    def __init__(self):
        self.public = 1
        self._internal = 2          # "don't touch" -- convention only
        self.__mangled = 3          # becomes _Visibility__mangled; NOT private


# ================================================================ 3. sealed -> union + match
@dataclass(frozen=True)
class Circle:
    radius: float


@dataclass(frozen=True)
class Square:
    side: float


@dataclass(frozen=True)
class Rectangle:
    w: float
    h: float


Shape = Circle | Square | Rectangle        # the "sealed" set, as a type alias


def area(shape: Shape) -> float:
    """Java 21 checks this `switch` for exhaustiveness at COMPILE time. Python's `match` has no
    runtime exhaustiveness check -- but mypy/pyright DO flag a missing case when the subject is a
    closed union, which is the whole reason to declare the alias."""
    match shape:
        case Circle(radius=r):
            return 3.14159 * r * r
        case Square(side=s):
            return s * s
        case Rectangle(w=w, h=h):
            return w * h
        case _:
            raise TypeError(f"unhandled shape {type(shape).__name__}")   # the safety net


# ================================================================ 7. the CPU benchmark
def cpu_bound(n):
    """Pure Python arithmetic -- holds the GIL the whole time.
    MUST be module level: ProcessPoolExecutor pickles it to reach the child."""
    total = 0
    for i in range(n):
        total += i * i
    return total


N, WORKERS = 6_000_000, 4


def run_cpu_benchmark():
    print(f"\n  benchmark: {WORKERS} x cpu_bound({N:,}), four ways (a few seconds)")

    t0 = time.perf_counter()
    for _ in range(WORKERS):
        cpu_bound(N)
    serial = time.perf_counter() - t0
    print(f"    serial                     {serial:5.2f}s          (the baseline)")

    t0 = time.perf_counter()
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(cpu_bound, [N] * WORKERS))
    threaded = time.perf_counter() - t0
    print(f"    ThreadPoolExecutor         {threaded:5.2f}s  {serial / threaded:4.2f}x  "
          f"<- NO speedup: the GIL serialises them")

    if hasattr(cf, "InterpreterPoolExecutor"):              # new in 3.14 (PEP 734)
        t0 = time.perf_counter()
        with cf.InterpreterPoolExecutor(WORKERS) as ex:
            list(ex.map(cpu_bound, [N] * WORKERS))
        interp = time.perf_counter() - t0
        print(f"    InterpreterPoolExecutor    {interp:5.2f}s  {serial / interp:4.2f}x  "
              f"<- real parallelism, one GIL PER INTERPRETER")
    else:
        print(f"    InterpreterPoolExecutor    n/a             -- needs Python 3.14+ "
              f"(you are on {sys.version_info.major}.{sys.version_info.minor})")

    t0 = time.perf_counter()
    with cf.ProcessPoolExecutor(WORKERS) as ex:
        list(ex.map(cpu_bound, [N] * WORKERS))
    procs = time.perf_counter() - t0
    print(f"    ProcessPoolExecutor        {procs:5.2f}s  {serial / procs:4.2f}x  "
          f"<- real parallelism, separate memory")


# ================================================================ 9. initialiser blocks
class Registry:
    _registered: dict = {}                        # a "static field"
    LOADED_AT = "import time"                     # "static final", computed at class creation

    def __init_subclass__(cls, /, key=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if key is None:
            raise TypeError(f"{cls.__name__} must pass key=...")
        Registry._registered[key] = cls           # what a `static {}` block would do


class CsvHandler(Registry, key="csv"):
    pass


class JsonHandler(Registry, key="json"):
    pass


# ================================================================ 10. Object's methods
@functools.total_ordering
@dataclass(frozen=True)        # frozen -> __hash__ generated for us
class Version:
    major: int
    minor: int

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented          # NOT False -- lets Python try the other side
        return (self.major, self.minor) < (other.major, other.minor)


class BrokenEquality:
    """Defines __eq__ only -- so Python sets __hash__ = None and it stops being hashable."""

    def __init__(self, v):
        self.v = v

    def __eq__(self, other):
        return isinstance(other, BrokenEquality) and self.v == other.v


# ================================================================ 11. enum
class Status(enum.StrEnum):              # StrEnum (3.11+): members ARE strings
    PENDING = "pending"
    SHIPPED = "shipped"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:       # methods on an enum: same as Java
        return self in (Status.SHIPPED, Status.CANCELLED)


class Priority(enum.Enum):
    LOW = enum.auto()                    # auto() -> 1, 2, 3
    MEDIUM = enum.auto()
    HIGH = enum.auto()


# ================================================================ 8. generics (PEP 695)
class Box[T]:
    def __init__(self, value: T):
        self.value = value

    def get(self) -> T:
        return self.value


def first[T](items: list[T]) -> T:
    return items[0]


ORDERS = [
    {"id": 1, "status": "SHIPPED", "amount": 250, "region": "EMEA"},
    {"id": 2, "status": "PAID", "amount": 80, "region": "APAC"},
    {"id": 3, "status": "SHIPPED", "amount": 420, "region": "EMEA"},
    {"id": 4, "status": "CANCELLED", "amount": 15, "region": "AMER"},
    {"id": 5, "status": "SHIPPED", "amount": 120, "region": "APAC"},
]


def main():
    # ============================================================ 1. final
    section("1. `final` -- Java has one keyword, Python has four different answers")
    print("""  Java's `final` means four unrelated things depending on where it appears:
      final int x = 5;            a variable that cannot be REBOUND
      private final String id;    a field assigned once (shallow immutability)
      public final void m() {}    a method that cannot be OVERRIDDEN
      public final class C {}     a class that cannot be SUBCLASSED
  Python has no `final` keyword. Each maps to something different -- and in three of the four
  cases there is NO RUNTIME ENFORCEMENT at all.""")

    max_retries: typing.Final[int] = 3          # a hint for mypy/pyright, nothing more
    print(f"\n  typing.Final[int] = {max_retries}")
    max_retries = 99                            # mypy: error. CPython: completely fine.
    print(f"  ...rebound at runtime to {max_retries}  <- NO error. `Final` is checker-only.")
    print("  so: UPPER_CASE tells a human; `Final` tells the tool; neither stops anyone.")
    print("  If it MUST be immutable, make the OBJECT immutable:")

    m = Money(1250)
    print(f"\n  @dataclass(frozen=True, slots=True): {m}")
    try:
        m.amount_cents = 1
    except FrozenInstanceError as e:
        print(f"  assignment -> {type(e).__name__}: {e}   <- ENFORCED, at runtime")
    print("  frozen is the one case where Python is as strict as Java: a real __setattr__ guard.")
    print("  But it is SHALLOW, exactly like Java's final -- a frozen dataclass holding a list")
    print("  still lets you mutate that list (and that also breaks hashability; see deep dive 33).")

    # ============================================================ 2. final method / class
    section("2. a `final` method and a `final` class -- and how to actually enforce them")
    print(f"  @typing.final class, subclassed anyway -> {IgnoredIt().critical()!r}")
    print("  NO exception. `@final` is a declaration for the type checker, not a runtime guard.\n")

    try:
        class _TryIt(ReallyFinal):
            pass
    except TypeError as e:
        print(f"  metaclass guard         -> TypeError: {e}")
    try:
        class _TryIt2(FinalViaHook):
            pass
    except TypeError as e:
        print(f"  __init_subclass__ guard -> TypeError: {e}")

    print("""
  Which to use:
      @typing.final            the normal answer. Declare the intent, let CI enforce it.
      __init_subclass__ raise  when you must stop it at runtime (a public library boundary, a
                               security-relevant class). Fires at import, like a compile error.
      metaclass                only if you already have one.
  And the cultural note: Python's answer to "stop people touching this" is a leading underscore
  and a code review, not the compiler.""")

    v = Visibility()
    print(f"\n  attributes actually stored: {sorted(vars(v))}")
    print(f"  the 'private' one is still reachable: v._Visibility__mangled = "
          f"{v._Visibility__mangled}")
    print("  `_name` is a convention; `__name` only NAME-MANGLES, to stop accidental collisions")
    print("  in subclasses. Neither is Java's `private`. There is no access control in Python.")

    # ============================================================ 3. sealed
    section("3. `sealed interface` (Java 17) -- union types plus an exhaustive `match`")
    for sh in (Circle(1), Square(2), Rectangle(2, 3)):
        print(f"  area({sh}) = {area(sh):.3f}")
    print("""
  The mapping:
      sealed interface Shape permits Circle, Square  ->  Shape = Circle | Square   (a type alias)
      switch with exhaustiveness checking            ->  match/case + `case _: raise`
      pattern matching with deconstruction           ->  case Circle(radius=r)     (same idea)
  Python's `match` genuinely is structural pattern matching, not a switch: it destructures, binds
  names, and matches sequences, mappings and classes. The one thing it lacks is the COMPILER
  telling you a case is missing -- so keep the `case _` that raises, and a type checker in CI.""")

    # ============================================================ 4. abstraction
    section("4. abstract class vs interface -- Python collapses the distinction")
    print("""  Java separates them, and the separation is forced by single inheritance:
      interface       contract only (plus `default` methods since 8); implement MANY
      abstract class  contract PLUS state and code; extend ONE
  Python has ONE construct that does both, because it has multiple inheritance:
      class Base(ABC) with @abstractmethod  -- holds state, concrete code AND abstract methods
  ...plus a second mechanism Java has no analogue for:
      typing.Protocol -- STRUCTURAL. A class satisfies it by SHAPE, with no inheritance and no
                         import. This is what you reach for to describe a third-party type.

  What an ABC gives you that a Java interface cannot: the TEMPLATE METHOD pattern in one class --
  the algorithm concrete, the varying steps abstract, the optional ones hooks with defaults.
  What a Java interface gives you that an ABC does not: enforcement before you ship. Python's
  check fires at INSTANTIATION, so a test that CONSTRUCTS every implementation is what buys the
  compile-time guarantee back.

  The limit to volunteer: an ABC checks that NAMES exist. Not signatures, not types.
  Full treatment in deep dive 23 and 13_abstract_base_classes.py.""")

    # ============================================================ 5. main
    section('5. `public static void main(String[] args)` -> `if __name__ == "__main__":`')
    print(f"""  There is no main METHOD, because a Python file is a SCRIPT: importing it executes
  every top-level statement. So the question is not "where does execution start" but "how do I
  tell being RUN from being IMPORTED".

      if __name__ == "__main__":
          main()

  `__name__` is the module's name, and it is the string "__main__" only when the file is the entry
  point. In this file, right now, __name__ == {__name__!r}.

  Why it matters -- and this is the real lesson, not the syntax. Without the guard, top-level code
  runs on IMPORT: it breaks your test suite, breaks `--help`, double-starts servers, and under
  multiprocessing on Windows (which RE-IMPORTS the module in every child) it either prints
  everything once per child or raises outright. THIS FILE hit both while being written -- see the
  module docstring. It is the same anti-pattern as expensive top-level code in an Airflow DAG file
  (14_airflow_orchestration).

  The four ways a Python program actually starts:
      python app.py        runs the file;            __name__ == "__main__"
      python -m mypkg      runs mypkg/__main__.py;   __name__ == "__main__"
      mycli                a console_scripts entry point in pyproject.toml:
                           [project.scripts]  mycli = "mypkg.cli:main"
      import mypkg         runs mypkg/__init__.py;   __name__ == "mypkg"   <- no main() runs

  Arguments: `String[] args` -> `sys.argv` (argv[0] is the script name), but use `argparse` for
  anything real -- it gives you --help, types and defaults:
      p = argparse.ArgumentParser(); p.add_argument("--date", required=True)
      args = p.parse_args()                    # exits(2) on bad input, by design

  Exit codes: `System.exit(1)` -> `sys.exit(1)` (which raises SystemExit). RETURNING a value from
  main() does nothing -- `sys.exit(main())` is the idiom that turns a return value into the code.""")
    print(f"  sys.argv for this run: {sys.argv}")

    # ============================================================ 6. Stream API
    section("6. Stream API -> comprehensions, generators and itertools")
    print("  the direct translations (full table in deep dive 21):")
    print(f"    .filter(p).map(f).collect(toList()) -> "
          f"{[o['id'] for o in ORDERS if o['amount'] > 100]}")
    print(f"    .mapToInt(..).sum()                 -> {sum(o['amount'] for o in ORDERS)}")
    print(f"    .anyMatch(p) / .allMatch(p)         -> "
          f"{any(o['status'] == 'PAID' for o in ORDERS)} / "
          f"{all(o['amount'] > 0 for o in ORDERS)}")
    print(f"    .max(comparing(Order::getAmount))   -> "
          f"id={max(ORDERS, key=lambda o: o['amount'])['id']}")
    print(f"    .sorted(comparing(..).reversed())   -> "
          f"{[o['id'] for o in sorted(ORDERS, key=lambda o: -o['amount'])]}")

    by_status = defaultdict(list)
    for o in ORDERS:
        by_status[o["status"]].append(o["id"])
    sums = {s: sum(o["amount"] for o in ORDERS if o["status"] == s) for s in by_status}
    print(f"    Collectors.groupingBy(getStatus)    -> {dict(by_status)}")
    print(f"    groupingBy(.., counting())          -> {dict(Counter(o['status'] for o in ORDERS))}")
    print(f"    groupingBy(.., summingInt(..))      -> {sums}")
    print(f"    Collectors.toMap(getId, getAmount)  -> {{o['id']: o['amount'] for o in ORDERS}}")
    print(f"    Collectors.joining(\", \")            -> "
          f"{', '.join(str(o['id']) for o in ORDERS)}")
    print(f"    .flatMap(..)                        -> "
          f"{[c for o in ORDERS for c in o['region']][:6]}...")

    print("""
  Three things that are the SAME and surprise people, and one that is different.

  SAME 1 -- laziness. A Java Stream is lazy; so is a GENERATOR EXPRESSION. The difference is
            visible in the brackets:
                [f(x) for x in items]   list comprehension -- EAGER, builds the whole list
                (f(x) for x in items)   generator expression -- LAZY, one item at a time
            A list comprehension is `.collect(toList())` already applied.""")
    gen = (o["amount"] for o in ORDERS if o["amount"] > 100)
    print(f"  SAME 2 -- single use. {type(gen).__name__} first pass: {list(gen)}")
    print(f"            second pass: {list(gen)}  <- exhausted, exactly like reusing a consumed")
    print("            Stream (which throws IllegalStateException).")
    print("""
  SAME 3 -- short-circuiting. any()/all()/next() stop at the first decisive element, like
            .anyMatch/.findFirst, so `any(expensive(x) for x in items)` does not evaluate them all.

  DIFFERENT -- .parallelStream() has NO equivalent. Threads do not parallelise CPU-bound Python
            (section 7). You need ProcessPoolExecutor or, on 3.14, InterpreterPoolExecutor -- both
            with real data-transfer costs, not a free one-word change. This is the single biggest
            performance expectation to reset when moving from Java.""")

    print("\n  itertools covers the rest of the Stream vocabulary:")
    print(f"    .limit(3)   -> islice:       "
          f"{list(itertools.islice((o['id'] for o in ORDERS), 3))}")
    print(f"    .skip(2)    -> islice(2,..): "
          f"{list(itertools.islice((o['id'] for o in ORDERS), 2, None))}")
    print(f"    .distinct() -> dict.fromkeys (keeps order): "
          f"{list(dict.fromkeys(o['region'] for o in ORDERS))}")
    print(f"    Stream.iterate -> count:     "
          f"{list(itertools.islice(itertools.count(10, 5), 4))}")
    print(f"    .takeWhile(p)  -> takewhile: "
          f"{list(itertools.takewhile(lambda n: n < 300, (o['amount'] for o in ORDERS)))}")
    print(f"    .reduce(0, Integer::sum)     -> prefer sum(); reduce is for custom folds: "
          f"{functools.reduce(lambda acc, o: acc | {o['region']}, ORDERS, set())}")

    print("""
  And Optional -> there is no Optional. Python returns None and you handle it:
      Optional<Order> o = find(id);   o.map(Order::getAmount).orElse(0)
      order = find(id);               order.amount if order else 0
      value = d.get(key, default)                      # the dict idiom
      if (order := find(id)) is not None: ...           # walrus: need the value AND a test
  `x or default` is the tempting one-liner and it is the truthiness trap -- it also replaces 0
  and "". Use `x if x is not None else default` when zero is a legitimate value.""")

    # ============================================================ 7. virtual threads
    section("7. virtual threads (Java 21) -- Python has THREE answers, none a drop-in")
    gil = sys._is_gil_enabled() if hasattr(sys, "_is_gil_enabled") else "n/a (<3.13)"
    free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
    print(f"""  A Java virtual thread is a cheap, JVM-scheduled thread: you can have a million,
  each written in ordinary BLOCKING style, and the JVM parks one automatically at any blocking
  call. `Thread.ofVirtual().start(..)` or `Executors.newVirtualThreadPerTaskExecutor()`.

  Python has no equivalent, because the constraint is different: `threading.Thread` is a REAL OS
  thread, and the GIL means only one of them executes Python bytecode at a time.
  This interpreter: GIL enabled = {gil}, free-threaded build = {free_threaded}

  So the answer depends on what you wanted virtual threads FOR:

  (a) MANY CONCURRENT I/O WAITS -> asyncio. The closest analogue by purpose: 10k+ concurrent
      tasks on ONE thread, a few KB each.
          async with asyncio.TaskGroup() as tg:  tg.create_task(fetch())
      The difference that matters: asyncio is COOPERATIVE. A virtual thread yields at ANY blocking
      call; a coroutine yields only at `await`. One synchronous `requests.get()` or a CPU-heavy
      loop inside a coroutine BLOCKS THE WHOLE EVENT LOOP -- every other task stops. That failure
      mode does not exist with virtual threads, and it is the #1 asyncio bug. The cost is "async
      all the way down": one sync DB driver poisons the benefit.

  (b) PARALLEL CPU WORK -> processes, a free-threaded build, or subinterpreters. Benchmark below.

  (c) BLOCKING CALLS YOU CANNOT MAKE ASYNC -> a ThreadPoolExecutor is still right, because the GIL
      IS RELEASED during I/O. `await asyncio.to_thread(blocking_call)` bridges the two worlds.""")

    run_cpu_benchmark()

    print("""
  Read the threaded row: four threads, no faster than one. In Java that same code scales with
  cores, virtual or platform threads alike. THAT is the expectation to reset.

  The three routes to real parallelism, with their costs:
      processes        separate memory -> arguments and results are PICKLED. Best for coarse,
                       independent chunks (see 09_aws_lambda_streaming/03_large_file_processing.py).
      subinterpreters  3.12 added them (PEP 684: one GIL PER interpreter); 3.14 exposes
                       InterpreterPoolExecutor and `concurrent.interpreters` (PEP 734). Cheaper
                       than a process, still isolated memory -- data crosses by copy or buffer.
      free-threaded    PEP 703 builds CPython with NO GIL (3.13 experimental; officially supported
                       from 3.14 -- a SEPARATE build, e.g. `python3.14t`). Threads then behave
                       like Java's. Costs: some single-threaded slowdown, and C extensions must
                       opt in. The honest answer to "will Python ever have real threads" is
                       "it now can, if you choose that build".""")

    # ============================================================ 8. generics
    section("8. generics -- both languages erase them; Python never had them at runtime")
    print(f"  class Box[T] / def first[T](..)  ->  {Box(42).get()!r}, {first(['a', 'b'])!r}")
    print(f"  Box[int] is a valid expression   ->  {Box[int]}")
    print(f"  ...but nothing is checked at runtime: {Box[int]('not an int').get()!r}")
    print("""
  Java erases generics at compile time (so `new T[]` is illegal and you need `Class<T>` tokens).
  Python never had them at runtime at all -- annotations are data, and a type checker is the only
  thing that reads them. So:
      List<String>              ->  list[str]
      <T> T first(List<T> xs)   ->  def first[T](xs: list[T]) -> T      (3.12+, PEP 695)
                                    TypeVar("T") + Generic[T]            (the older spelling)
      ? extends Number          ->  a bound: def f[T: float](x: T) -> T
      Class<T> token            ->  pass the type itself: def load(cls: type[T]) -> T
  Practical consequence, identical in both: you cannot ask at runtime what T was.""")

    # ============================================================ 9. initialiser blocks
    section("9. static and instance initialiser blocks")
    print("""  Java                           Python
  -----------------------------  ------------------------------------------------------
  static { ... }                 plain statements in the CLASS BODY (run once, at class
                                 creation -- i.e. at import)
  { ... } instance initialiser   code in __init__
  static final X = compute()     a class attribute: X = compute()   (runs at import)
  @PostConstruct (Spring)        __post_init__ on a dataclass, or a factory classmethod
  class-level validation         __init_subclass__ (fires per subclass, at import)

  The thing to internalise: a Python class body is EXECUTABLE CODE that runs once, top to bottom,
  when the module is imported -- and its local namespace becomes the class __dict__. So an
  expensive call in a class body is an expensive call at IMPORT time.""")
    print(f"\n  registry populated at import, with no explicit static block: {Registry._registered}")
    print(f"  Registry.LOADED_AT = {Registry.LOADED_AT!r}")

    # ============================================================ 10. Object's methods
    section("10. equals / hashCode / toString / Comparable / clone")
    print("""  Java                   Python                Notes
  ---------------------  --------------------  --------------------------------------------
  equals(Object o)       __eq__(self, other)   return NotImplemented (not False) for an
                                               unknown type -- it lets Python try the other
                                               side's __eq__
  hashCode()             __hash__(self)        **defining __eq__ sets __hash__ to None**, so
                                               the object stops working as a dict key unless
                                               you define __hash__ too (or use frozen=True)
  toString()             __repr__ / __str__    __repr__ is for DEVELOPERS (unambiguous,
                                               ideally eval-able); __str__ is for users.
                                               Define __repr__; __str__ falls back to it
  Comparable.compareTo   __lt__ + @total_ordering    see deep dive 33
  clone() / Cloneable    copy.copy / deepcopy  no Cloneable ceremony; see deep dive 24
  finalize()             __del__               unreliable in both; use a context manager
  getClass()             type(obj)             and type(obj).__name__ for the name""")

    a, b = Version(1, 2), Version(1, 10)
    print(f"\n  {a!r} < {b!r} -> {a < b}   (total_ordering filled in >, <=, >=)")
    print(f"  sorted: {sorted([Version(2, 0), a, b])}")
    print(f"  usable as a dict key because frozen=True generated __hash__: "
          f"{({a: 'ok'})[Version(1, 2)]!r}")
    print(f"\n  a class defining only __eq__: __hash__ is {BrokenEquality.__hash__}")
    try:
        {BrokenEquality(1): "x"}
    except TypeError as e:
        print(f"  using it as a dict key -> TypeError: {e}")
    print("  Java never does this to you -- hashCode() just stays inherited from Object.")
    print("  In Python the pairing is opt-in, and forgetting it is a real bug.")

    # ============================================================ 11. enum
    section("11. enum -- Java's is a full class; Python's is close, with two extras")
    print(f"  Status.SHIPPED = {Status.SHIPPED!r}, .value = {Status.SHIPPED.value!r}, "
          f".is_terminal = {Status.SHIPPED.is_terminal}")
    print(f"  StrEnum members ARE str: Status.SHIPPED == 'shipped' -> "
          f"{Status.SHIPPED == 'shipped'}")
    print(f"  iteration (Java's values()): {[s.name for s in Status]}")
    print(f"  lookup by value / by name:   {Status('pending')!r} / {Status['SHIPPED']!r}")
    print(f"  auto() numbering:            {[(p.name, p.value) for p in Priority]}")
    print("""
  Java                      Python
  ------------------------  --------------------------------------------------
  enum Status { A, B }      class Status(Enum): A = auto(); B = auto()
  Status.values()           list(Status) / iteration
  Status.valueOf("A")       Status["A"]  (by NAME)   |   Status(value)  (by VALUE)
  .ordinal()                .value with auto(), or list(Status).index(x)
  .name()                   .name
  methods + fields on enum  the same -- methods, properties, even __init__
  EnumSet / EnumMap         a set/dict of members; or enum.Flag for bit flags
  switch on enum            match/case on the member
  -- Python extras Java lacks: StrEnum / IntEnum, whose members ARE str/int (so they serialise
     and compare like the primitive), plus @enum.unique and Flag for bitwise combinations.""")

    # ============================================================ 12. checked exceptions
    section("12. checked exceptions -- Python has none, and what replaces them")
    print("""  Java forces `throws IOException` and the compiler makes callers handle it.
  Python has NO checked exceptions: nothing in a signature tells you what a call can raise.

  What that costs: you cannot know from the signature. You read the docs, or the code.
  What replaces it -- and this is the answer to give:
      1. A DOCUMENTED custom exception hierarchy with ONE app base class, so a caller chooses its
         granularity (`except AppError` vs `except OrderNotFound`). The TYPE is the contract.
      2. Docstrings that state what is raised (a `Raises:` section).
      3. Splitting exceptions by the DECISION the caller must make -- transient vs permanent --
         rather than by where they came from. That is what lets a consumer choose retry vs DLQ
         without an isinstance ladder.
      4. A boundary handler that logs and converts: central FastAPI exception_handlers, or a Kafka
         consumer's retry/DLQ router.
  Deep dives 08 and 25 have the full pattern. One-line version: in Java the compiler is the
  contract; in Python the exception HIERARCHY is the contract, so design it deliberately.

  Related: try-with-resources -> `with` (deep dive 25). Both guarantee cleanup; only Python's
  lets __exit__ SWALLOW the exception by returning True.""")

    # ============================================================ summary
    section("the one-screen summary")
    print("""  Java feature              Python equivalent              Enforced by
  ------------------------  -----------------------------  ---------------------------------
  final variable            UPPER_CASE / Final[int]        nobody / a type checker
  final field               @dataclass(frozen=True)        RUNTIME (__setattr__ raises)
  final method              @typing.final                  a type checker only
  final class               @typing.final                  a type checker only
                            __init_subclass__: raise       RUNTIME, at import
  private                   _name (convention)             nobody
                            __name                         name mangling, not privacy
  sealed interface          A | B | C  +  match/case       a type checker (keep `case _`)
  interface                 ABC, or typing.Protocol        instantiation / a type checker
  abstract class            the SAME ABC                   instantiation
  public static void main   if __name__ == "__main__"      -
  String[] args             sys.argv, argparse             -
  Stream (lazy)             generator expression           -
  Stream (collected)        list comprehension             -
  parallelStream            ProcessPool / InterpreterPool  -- NOT a one-word change
  Optional<T>               T | None, d.get(k, default)    a type checker
  virtual threads           asyncio (I/O)  |  processes /  -
                            subinterpreters / free-threaded build (CPU)
  generics <T>              def f[T](..) / TypeVar         a type checker (erased at runtime)
  static { }                class-body statements          runs at import
  equals / hashCode         __eq__ + __hash__              define BOTH or lose dict-key use
  toString                  __repr__                       -
  enum                      enum.Enum / StrEnum / IntEnum  -
  checked exceptions        a documented hierarchy         code review and tests

  The pattern: Java pushes correctness to COMPILE time; Python pushes it to a TYPE CHECKER IN CI
  plus TESTS. Neither is free -- but a Python codebase with no mypy and no tests has genuinely
  given up guarantees that Java handed you for nothing.""")


# The __main__ guard is NOT optional here, and this file is its own best example.
# ProcessPoolExecutor (section 7) uses the "spawn" start method on Windows and macOS, which
# RE-IMPORTS this module in every child process. With the narration at module level it printed
# once per child; with the pool created at module level it raised "An attempt has been made to
# start a new process before the current process has finished its bootstrapping phase".
# Hence: definitions at module level (they must be importable AND picklable), output in main().
if __name__ == "__main__":
    main()

# EXPERIMENT 1: run `py -m mypy 17_java_to_python_advanced.py` (pip install mypy). Every
# "checker only" claim above becomes a real error -- the Final rebind, the @final subclass, the
# override. That is the point: the enforcement exists, it just is not the interpreter.
# EXPERIMENT 2: in cpu_bound, add `time.sleep(0.5)` and re-run. The threaded row now beats serial,
# because sleep RELEASES the GIL. That one change explains exactly when threads help.
# EXPERIMENT 3: give Money a `tags: list` field and mutate it on a frozen instance. Frozen is
# shallow -- exactly like Java's final.
# EXPERIMENT 4: delete the `case _: raise` from area() and pass it an int. Decide whether you
# prefer the silent None or the raise.
# EXPERIMENT 5: move one print() from main() back to module level and re-run. It appears several
# times -- once per spawned child. That is section 5, demonstrated by your own edit.

# EXERCISE: translate this Java class to idiomatic Python, and for each `final`, `private` and
# `@Override` say which of the three Python answers applies (runtime / type checker / nobody):
#
#     public final class OrderId implements Comparable<OrderId> {
#         private final String value;
#         public OrderId(String value) {
#             if (value == null || value.isBlank()) throw new IllegalArgumentException("blank");
#             this.value = value;
#         }
#         public static OrderId of(String raw) { return new OrderId(raw.trim()); }
#         @Override public boolean equals(Object o) { ... }
#         @Override public int hashCode() { return value.hashCode(); }
#         @Override public String toString() { return "OrderId[" + value + "]"; }
#         @Override public int compareTo(OrderId o) { return value.compareTo(o.value); }
#     }
#
# Make it immutable at RUNTIME, usable as a dict key, and sortable -- then write the one test that
# proves all three. (Compare your answer with the Money class in deep dive 33's worked example.)
