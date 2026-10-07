# 01 — Python Core

The foundation every interview round touches. Run each file directly (`python 01_data_structures.py`)
and read the `# EXPERIMENT:` prompts — change the marked line, predict the output, then run it.

## Crib sheet

- **Mutable vs immutable**: `int/float/str/tuple/frozenset` are immutable (hashable, safe as dict
  keys); `list/dict/set` are mutable (watch aliasing bugs, especially in default arguments).
- **dict** is a hash table, O(1) average get/set/delete, insertion-ordered since 3.7.
- **`is` vs `==`**: identity vs equality. Never rely on small-int/string interning.
- **Comprehensions** have their own scope (loop var doesn't leak); prefer a generator expression
  when you only iterate once or feed `sum`/`any`/`max` — it's O(1) memory instead of O(n).
- **Decorators**: `@deco` above `def f` is sugar for `f = deco(f)`. Always `functools.wraps`.
  A decorator that takes arguments needs three nested levels (factory → decorator → wrapper).
- **The built-in decorators**: the *only* difference between an instance method, `@classmethod` and
  `@staticmethod` is what is prepended as the first argument (the object / the class / nothing) —
  all three are descriptors. `@classmethod`'s `cls` is the **actual** class, which is why a factory
  works for subclasses. `@property` makes a method read as an attribute, so you never write
  `get_x()`/`set_x()` in Python. `@cached_property` caches per instance (and needs a `__dict__`);
  `@lru_cache` caches by arguments and must **never** go on a method — it keeps `self` alive.
- **Generators**: lazy, single-pass, keep local state between `yield`s. `yield from` delegates to
  a sub-iterator and forwards `send`/`throw`.
- **Context managers**: `__enter__`/`__exit__`; `@contextlib.contextmanager` turns a generator into
  one (code before `yield` = enter, code in `finally` = exit).
- **Descriptors**: any object with `__get__`/`__set__`/`__delete__` stored as a class attribute.
  `property` is a data descriptor — that's why it beats instance `__dict__`.
- **MRO**: C3 linearization; `super()` goes to the *next* class in the instance's MRO, not
  necessarily the literal parent — this is what makes cooperative multiple inheritance work.
- **Exceptions**: catch the narrowest type; never bare `except:`; `raise X from err` preserves the
  chain; `finally`'s `return` silently discards everything else (never `return` from `finally`).
- **Memory**: CPython uses reference counting + a generational cyclic GC. `__slots__` removes the
  per-instance `__dict__` (~40% memory saving) at the cost of dynamic attributes.
- **Scope (LEGB)**: Local → Enclosing *function* → Global (= module-level) → Built-in. Assignment
  anywhere in a function makes the name local **for the whole function**, decided at compile time —
  that one rule causes `UnboundLocalError`, the late-binding closure bug, and the class-body
  `NameError`. `global`/`nonlocal` rebind a *name*; mutating an object needs neither.
- **ABCs**: `class X(ABC)` + `@abstractmethod` → `TypeError` at **instantiation**, naming what's
  missing. An ABC can hold concrete code (template method) — that's why it beats a `Protocol` when
  you own the hierarchy. It checks **names only**, never signatures: a type checker does that.
  `typing.Protocol` is structural (no inheritance); `__init_subclass__` validates at **import** time.
- **Multi-level `except`**: clauses are tried top-down, so a parent above a child makes the child's
  handler **dead code** — with no warning. `raise X from e` preserves the cause; `return`/`raise` in
  `finally` destroys the in-flight exception; `__exit__` returning `True` **swallows** it.
  `ExceptionGroup`/`except*` (3.11+) for several failures at once.

## Files

| File | Topic |
|---|---|
| `01_data_structures.py` | list/tuple/dict/set/frozenset, `collections` (Counter, defaultdict, deque, namedtuple, OrderedDict, ChainMap) |
| `02_comprehensions.py` | list/set/dict/generator comprehensions, nesting, walrus, closure trap |
| `03_decorators.py` | function/class decorators, decorators with args, retry/timer/rate-limit |
| `04_generators_iterators.py` | iterator protocol, `yield`, `yield from`, `send`/`throw`, `itertools` |
| `05_context_managers.py` | class-based & `@contextmanager`, `ExitStack`, async context manager |
| `06_descriptors_metaclasses.py` | validation descriptor, `property` internals, metaclass singleton, `__init_subclass__` |
| `07_oop_inheritance_mro.py` | multiple/multilevel inheritance, diamond problem, `super()`, mixins, ABCs, dunders |
| `08_exception_handling.py` | try/except/else/finally, custom hierarchy, chaining, EAFP vs LBYL, `ExceptionGroup` |
| `09_memory_management.py` | refcounting, `gc`, `weakref`, `__slots__`, `tracemalloc` |
| `exercises.md` | practice prompts — solve before checking the corresponding file above |
| `10_map_filter_reduce.py` | `map`/`filter` laziness, `reduce` and why it left builtins, `operator`, Java Streams mapping |
| `11_java_to_python_bridge.py` | the 7 traps a Java developer hits, bean → dataclass, ABC vs Protocol, MRO, the GIL race |
| `12_variable_scope_namespaces.py` | LEGB, `global`/`nonlocal`, `UnboundLocalError`, the class-body scope hole, late binding, shadowing built-ins |
| `13_abstract_base_classes.py` | `ABC`/`@abstractmethod`, template method, abstract property, `Protocol`, `register()`, `collections.abc` mixins, `__init_subclass__` |
| `14_python_basics_essentials.py` | `is` vs `==`, pass-by-object-reference, mutable defaults, truthiness, shallow/deep copy, `*args`/`**kwargs`, sorting, type hints |
| `15_nested_exception_handling.py` | multi-level `except`, nested `try`, layer translation, `with` + exceptions, `ExceptionGroup`/`except*`, `add_note()` |
| `16_methods_and_builtin_decorators.py` | `@classmethod`/`@staticmethod`/`@property` (+setter/deleter), the descriptor mechanism, `cached_property`, `lru_cache` traps, `singledispatchmethod`, `total_ordering`, `@dataclass`, `__new__` vs `__init__` |

## Deep dives

The crib sheet above is for revision. For long-form Q&A with full answers, trade-offs and
hands-on drills, see [`../deep_dive/`](../deep_dive/):

- [01 — Data structures + `collections`](../deep_dive/01_data_structures_collections.md)
- [02 — Comprehensions, `map`/`filter`/`reduce`](../deep_dive/02_comprehensions_map_filter_reduce.md)
- [03 — Custom decorators](../deep_dive/03_decorators.md)
- [04 — Generators, iterators, iterables](../deep_dive/04_generators_iterators.md)
- [05 — Context managers, descriptors, metaclasses](../deep_dive/05_context_managers_descriptors_metaclasses.md)
- [06 — OOP in depth: inheritance and MRO](../deep_dive/06_oop_inheritance_mro.md)
- [08 — Error handling](../deep_dive/08_error_handling.md)
- [22 — Variable scope, declaration and namespaces](../deep_dive/22_variable_scope_namespaces.md)
- [23 — Abstract base classes, interfaces and `Protocol`](../deep_dive/23_abstract_classes_interfaces.md)
- [24 — Python basics that still get asked at senior level](../deep_dive/24_python_basics_essentials.md)
- [25 — Multi-level exception handling and `with`](../deep_dive/25_nested_exception_handling.md)
- [33 — `@classmethod`, `@staticmethod`, `@property` and the built-in decorators](../deep_dive/33_methods_and_builtin_decorators.md)
- [21 — Java → Python bridge](../deep_dive/21_java_to_python_bridge.md)
