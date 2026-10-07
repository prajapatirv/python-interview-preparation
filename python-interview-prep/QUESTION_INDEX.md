# Python Interview — Question Index

A single reference mapping interview questions to where they're demonstrated in this repo.
**Click any `→ file.py:LX` link** to jump straight to that line in the editor.

- **Part 1 — Hands-On Topics**: every question here has a runnable example in one of the 13
  numbered folders. Read the Q&A, then click through and run the file yourself.
- **Part 2 — Reference Topics**: covered in the source interview-prep material but with no
  runnable example in this repo (Apache Camel, Couchbase, Airflow, Terraform/Databricks, Java
  migration, and more). No links — concept-only.

Use your editor's outline/symbol view (VS Code: `Ctrl+Shift+O`) to jump between the sections
below, or `Ctrl+F` for a specific keyword.

> **The answers here are deliberately short** — one or two lines, enough to jog your memory.
> For the full treatment of any topic below (multi-paragraph answers, trade-offs, failure modes,
> Java contrasts, hands-on drills and a "60-second spoken answer"), go to the matching document
> in **[`deep_dive/`](deep_dive/)**. The map:

| This index's section | Deep dive |
|---|---|
| 01 Python Core — data structures | [01 — Data structures + `collections`](deep_dive/01_data_structures_collections.md) |
| 01 Python Core — comprehensions, map/filter/reduce | [02 — Comprehensions, `map`/`filter`/`reduce`](deep_dive/02_comprehensions_map_filter_reduce.md) |
| 01 Python Core — decorators | [03 — Custom decorators](deep_dive/03_decorators.md) |
| 01 Python Core — generators/iterators | [04 — Generators, iterators, iterables](deep_dive/04_generators_iterators.md) |
| 01 Python Core — context managers, descriptors, metaclasses | [05 — Context managers, descriptors, metaclasses](deep_dive/05_context_managers_descriptors_metaclasses.md) |
| 01 Python Core — OOP / MRO | [06 — OOP in depth: inheritance and MRO](deep_dive/06_oop_inheritance_mro.md) |
| 01 Python Core — exceptions | [08 — Error handling](deep_dive/08_error_handling.md) |
| 01 Python Core — variable scope / namespaces | [22 — Variable scope, declaration and namespaces](deep_dive/22_variable_scope_namespaces.md) |
| 01 Python Core — abstract classes / `Protocol` | [23 — Abstract base classes, interfaces and `Protocol`](deep_dive/23_abstract_classes_interfaces.md) |
| 01 Python Core — language basics | [24 — Python basics that still get asked at senior level](deep_dive/24_python_basics_essentials.md) |
| 01 Python Core — multi-level `except`, `with` | [25 — Multi-level exception handling and `with`](deep_dive/25_nested_exception_handling.md) |
| 01 Python Core — `@classmethod`/`@staticmethod`/`@property` | [33 — Methods and the built-in decorators](deep_dive/33_methods_and_builtin_decorators.md) |
| 02 Concurrency | [07 — Concurrency](deep_dive/07_concurrency.md) |
| 03 Pandas | [09 — Pandas for data handling](deep_dive/09_pandas.md) |
| 05 FastAPI / REST | [10 — Django / Flask / FastAPI](deep_dive/10_web_frameworks.md) |
| 06 Kafka — core concepts | [13 — Kafka core](deep_dive/13_kafka_core.md) |
| 06 Kafka — delivery semantics | [14 — Pipelines & delivery semantics](deep_dive/14_kafka_pipelines_delivery_semantics.md) |
| 06 Kafka — retry/DLQ | [15 — Failure handling](deep_dive/15_kafka_failure_handling.md) |
| 06 Kafka — schema registry | [16 — Schema management](deep_dive/16_kafka_schema_management.md) |
| 06 Kafka — client config & Aurora sink | [31 — Kafka config & integration from Python](deep_dive/31_kafka_python_integration.md) |
| 07 Caching | [17 — Caching mechanisms](deep_dive/17_caching.md) |
| 07 Queues | [18 — Queue-based architectures](deep_dive/18_queue_architectures.md) |
| 08 Scaling & resilience | [12 — Scaling applications](deep_dive/12_scaling_applications.md) |
| Part 2 — monitoring/alerting | [19 — Production stability, alerting & monitoring](deep_dive/19_production_stability_monitoring.md) |
| 10 GenAI / LLM | [20 — AI-first technologies](deep_dive/20_ai_first_technologies.md) |
| 09 Large files / streaming | [30 — Handling a 100GB file](deep_dive/30_large_file_processing.md) |
| 11 Coding challenges | [26 — Three design-coding problems](deep_dive/26_coding_design_problems.md) |
| 12 Framework internals | [11 — Python framework development](deep_dive/11_python_framework_development.md) |
| 13 Zero-downtime changes | [27 — Zero-downtime production changes](deep_dive/27_zero_downtime_production_changes.md) |
| 13 Observability | [28 — Observability in a distributed system](deep_dive/28_observability_distributed_systems.md) |
| 13 Capacity planning / scaling TPS | [29 — Scaling 100 to 600 TPS](deep_dive/29_capacity_scaling_tps.md) |
| 13 AI leverage & impact stories | [32 — Leveraging AI, and the customer-impact story](deep_dive/32_ai_leverage_and_impact_stories.md) |
| Part 2 — Java migration | [21 — Java → Python bridge](deep_dive/21_java_to_python_bridge.md) |

---

## Part 1 — Hands-On Topics (click through to the example)

### 01 — Python Core

**`01_data_structures.py`**

- **Q:** Why choose a tuple over a list, and when can a tuple NOT be used as a dict key?
  **A:** Tuples are immutable and (if every element is hashable) hashable — safe as dict keys or
  set members. A tuple containing a mutable object like a list is still not hashable.
  → [01_data_structures.py:15](01_python_core/01_data_structures.py#L15)
- **Q:** What's the classic "mutable default argument" bug?
  **A:** Default values are evaluated once at function-definition time, so a mutable default
  (list/dict) is silently shared and accumulates state across calls. Use `None` as a sentinel.
  → [01_data_structures.py:36](01_python_core/01_data_structures.py#L36)
- **Q:** Does a dict preserve insertion order when you overwrite an existing key's value?
  **A:** Yes — the key keeps its original position; only a brand-new key is appended at the end.
  → [01_data_structures.py:57](01_python_core/01_data_structures.py#L57)
- **Q:** How do you find the top-k most frequent items, or check if two words are anagrams, cheaply?
  **A:** `collections.Counter` — `most_common(k)`, and two Counters compare equal iff the words
  are anagrams of each other.
  → [01_data_structures.py:66](01_python_core/01_data_structures.py#L66)
- **Q:** What's the cleanest way to group items into a dict of lists without `if key not in d` checks?
  **A:** `collections.defaultdict(list)`.
  → [01_data_structures.py:74](01_python_core/01_data_structures.py#L74)
- **Q:** Why is `deque` preferred over `list` for a queue or a sliding window?
  **A:** `list.pop(0)`/`insert(0, x)` are O(n) — every element shifts; `deque` gives O(1) at both
  ends, and `maxlen` gives a free fixed-size ring buffer.
  → [01_data_structures.py:83](01_python_core/01_data_structures.py#L83)
- **Q:** How do you build an O(1) get/put LRU cache using only stdlib?
  **A:** `collections.OrderedDict` + `move_to_end()` on every access + `popitem(last=False)` to
  evict the least-recently-used entry.
  → [01_data_structures.py:104](01_python_core/01_data_structures.py#L104)
- **Q:** What's `ChainMap` for?
  **A:** Layering multiple dicts into one read view without copying — e.g. CLI args override env
  vars override defaults.
  → [01_data_structures.py:134](01_python_core/01_data_structures.py#L134)
- **Q:** How do you remove duplicates from a list while preserving order?
  **A:** `list(dict.fromkeys(items))` — O(n); `list(set(items))` is also O(n) but loses order.
  → [01_data_structures.py:142](01_python_core/01_data_structures.py#L142)

**`02_comprehensions.py`**

- **Q:** List comprehension vs. generator expression — when does the memory difference matter?
  **A:** A list comprehension materializes everything (O(n) memory); a generator expression
  yields lazily (O(1) memory) — use it when you only iterate once or feed `sum`/`any`/`max`.
  → [02_comprehensions.py:22](01_python_core/02_comprehensions.py#L22)
- **Q:** Does the loop variable in a comprehension leak into the enclosing scope?
  **A:** No, in Python 3 each comprehension has its own scope — except the walrus operator `:=`,
  which deliberately binds in the enclosing scope.
  → [02_comprehensions.py:49](01_python_core/02_comprehensions.py#L49)
- **Q:** Why do lambdas created inside a loop all return the same (final) value?
  **A:** Closures capture variables, not values — fix by binding the current value as a default
  argument: `lambda i=i: i`.
  → [02_comprehensions.py:61](01_python_core/02_comprehensions.py#L61)
- **Q:** Can a comprehension handle per-item exceptions?
  **A:** No — wrap the risky call in a small helper that returns a sentinel on failure, then
  filter the sentinel out.
  → [02_comprehensions.py:70](01_python_core/02_comprehensions.py#L70)

**`03_decorators.py`**

- **Q:** What does `@functools.wraps` actually fix?
  **A:** Without it, the wrapper replaces the original function's `__name__`/`__doc__`, breaking
  introspection, logging, and any framework routing that depends on them.
  → [03_decorators.py:15](01_python_core/03_decorators.py#L15)
- **Q:** How do you write a decorator that itself takes arguments, like `@retry(times=3)`?
  **A:** Add a third nesting level — an outer factory function that receives the arguments and
  returns the actual decorator.
  → [03_decorators.py:38](01_python_core/03_decorators.py#L38)
- **Q:** In what order do stacked decorators run?
  **A:** Applied bottom-up at definition time (`@a @b def f` → `f = a(b(f))`), but the outermost
  one runs first at call time.
  → [03_decorators.py:72](01_python_core/03_decorators.py#L72)
- **Q:** When do you need a class-based decorator instead of a function-based one?
  **A:** When the decorator itself needs to hold state across calls (a call counter, a cache) —
  implement `__init__`/`__call__` and use `functools.update_wrapper`.
  → [03_decorators.py:99](01_python_core/03_decorators.py#L99)
- **Q:** How would you implement a thread-safe rate limiter as a decorator?
  **A:** A token-bucket counter protected by a `threading.Lock`, replenished based on elapsed
  time on each call.
  → [03_decorators.py:147](01_python_core/03_decorators.py#L147)

**`04_generators_iterators.py`**

- **Q:** What's the difference between an iterable and an iterator?
  **A:** An iterable implements `__iter__` and can be iterated many times; an iterator implements
  `__next__`, is single-pass, and returns itself from `__iter__`.
  → [04_generators_iterators.py:13](01_python_core/04_generators_iterators.py#L13)
- **Q:** What does `yield` actually do to a function's execution?
  **A:** Calling a generator function doesn't run its body — it returns a generator object; each
  `next()` runs until the next `yield`, returns that value, and freezes the frame's local state.
  → [04_generators_iterators.py:46](01_python_core/04_generators_iterators.py#L46)
- **Q:** What does `yield from` do?
  **A:** Delegates to a sub-iterator, yielding every item it produces and forwarding
  `send()`/`throw()` — the clean way to write a recursive generator (e.g. flattening nested lists).
  → [04_generators_iterators.py:83](01_python_core/04_generators_iterators.py#L83)
- **Q:** How does `generator.send()` work, and what must happen before you call it?
  **A:** It resumes the generator and makes the paused `yield` expression evaluate to the sent
  value — the generator must first be primed with a `next()` (or `send(None)`).
  → [04_generators_iterators.py:98](01_python_core/04_generators_iterators.py#L98)
- **Q:** Which `itertools` functions come up constantly in interviews?
  **A:** `islice` (lazy slicing), `groupby` (groups only *consecutive* equal keys — sort first),
  `accumulate` (running totals), and hand-building a `batched()` helper for chunked processing.
  → [04_generators_iterators.py:118](01_python_core/04_generators_iterators.py#L118)

**`05_context_managers.py`**

- **Q:** What's the contract between `with` and `__enter__`/`__exit__`?
  **A:** `__enter__`'s return value is bound by `as`; `__exit__(exc_type, exc, tb)` always runs,
  even on exception, and returning `True` from it suppresses the exception.
  → [05_context_managers.py:15](01_python_core/05_context_managers.py#L15)
- **Q:** How do you turn a generator function into a context manager?
  **A:** `@contextlib.contextmanager` — code before `yield` is `__enter__`; code in a `finally`
  after `yield` is `__exit__`.
  → [05_context_managers.py:45](01_python_core/05_context_managers.py#L45)
- **Q:** How do you manage an unknown-at-write-time number of context managers?
  **A:** `contextlib.ExitStack` — `stack.enter_context(...)` for each one; all close in reverse
  order automatically, even on error.
  → [05_context_managers.py:71](01_python_core/05_context_managers.py#L71)
- **Q:** What does an async context manager look like, and where does this project use one?
  **A:** `@contextlib.asynccontextmanager` — same enter/exit shape with `await`; this is exactly
  the pattern used for a Kafka producer's lifecycle and a FastAPI DB session.
  → [05_context_managers.py:91](01_python_core/05_context_managers.py#L91)

**`06_descriptors_metaclasses.py`**

- **Q:** What is a descriptor, and how is `@property` "just" one?
  **A:** Any object defining `__get__`/`__set__`/`__delete__` and stored as a class attribute;
  `property` is a built-in *data* descriptor, which is why it beats instance `__dict__`.
  → [06_descriptors_metaclasses.py:12](01_python_core/06_descriptors_metaclasses.py#L12) (`@property` desugaring: [line 50](01_python_core/06_descriptors_metaclasses.py#L50))
- **Q:** What is a metaclass, and when would you actually reach for one?
  **A:** The class of a class (`type` is the default) — controls how the class OBJECT itself is
  created; useful for enforcing a rule on every subclass at class-definition time.
  → [06_descriptors_metaclasses.py:87](01_python_core/06_descriptors_metaclasses.py#L87)
- **Q:** What's usually a better alternative to a custom metaclass?
  **A:** `__init_subclass__` — a hook on the parent that fires whenever a subclass is defined
  (e.g. building a plugin registry), with none of the metaclass machinery.
  → [06_descriptors_metaclasses.py:115](01_python_core/06_descriptors_metaclasses.py#L115)

**`07_oop_inheritance_mro.py`**

- **Q:** What's the difference between multilevel and multiple inheritance?
  **A:** Multilevel is a chain (`C(B)`, `B(A)`); multiple is several bases at once
  (`class C(A, B)`), which introduces the diamond problem.
  → [07_oop_inheritance_mro.py:13](01_python_core/07_oop_inheritance_mro.py#L13)
- **Q:** How does Python resolve the diamond problem, and what does `super()` actually call?
  **A:** C3 linearization (the MRO) lists each class exactly once; `super()` calls the NEXT class
  in the *instance's* MRO — not necessarily the literal parent — which is what makes cooperative
  multiple inheritance work.
  → [07_oop_inheritance_mro.py:48](01_python_core/07_oop_inheritance_mro.py#L48)
- **Q:** How do you write cooperative `__init__` methods across multiple inheritance?
  **A:** Every class accepts `**kwargs`, pops what it needs, and calls
  `super().__init__(**kwargs)` — the chain terminates at `object`.
  → [07_oop_inheritance_mro.py:80](01_python_core/07_oop_inheritance_mro.py#L80)
- **Q:** What's a mixin, and where should it sit in the base-class list?
  **A:** A small, focused class adding one capability, not meant to stand alone — place it to
  the LEFT of the main base so its methods win in the MRO.
  → [07_oop_inheritance_mro.py:109](01_python_core/07_oop_inheritance_mro.py#L109)
- **Q:** How do you enforce that a class can't be instantiated until it implements certain methods?
  **A:** `abc.ABC` + `@abstractmethod`.
  → [07_oop_inheritance_mro.py:127](01_python_core/07_oop_inheritance_mro.py#L127)

**`08_exception_handling.py`**

- **Q:** What's the exact role of `try`/`except`/`else`/`finally`?
  **A:** `else` runs ONLY if no exception occurred (keep the success path out of `try` so its own
  errors aren't accidentally caught); `finally` always runs, even after `return`.
  → [08_exception_handling.py:16](01_python_core/08_exception_handling.py#L16)
- **Q:** How do you design a custom exception hierarchy?
  **A:** One `AppError(Exception)` base per application so callers can catch the whole family,
  then specific subclasses carrying structured context (e.g. a `field` attribute).
  → [08_exception_handling.py:38](01_python_core/08_exception_handling.py#L38)
- **Q:** What does `raise NewError(...) from original_error` actually do?
  **A:** Chains the exceptions — the original is stored on `__cause__` and both tracebacks print,
  instead of losing the root cause.
  → [08_exception_handling.py:72](01_python_core/08_exception_handling.py#L72)
- **Q:** EAFP vs. LBYL — which is idiomatic Python, and why?
  **A:** EAFP (try it, catch the exception) is preferred — it avoids the race condition and
  double-lookup that LBYL (`if x in d: d[x]`) is prone to.
  → [08_exception_handling.py:95](01_python_core/08_exception_handling.py#L95)
- **Q:** What's the "return in finally" footgun?
  **A:** A `return` inside `finally` silently overrides and discards both the `try`'s return
  value AND any in-flight exception — never do it.
  → [08_exception_handling.py:112](01_python_core/08_exception_handling.py#L112)

**`10_map_filter_reduce.py`**

- **Q:** Are `map` and `filter` lists in Python 3?
  **A:** No — they are lazy, single-pass iterators. Calling `list()` on the same `map` object
  twice gives you the results and then an empty list, with no error.
  → [10_map_filter_reduce.py:1](01_python_core/10_map_filter_reduce.py#L1)
- **Q:** `map` or a comprehension?
  **A:** `map` when you pass an existing named function (`map(int, xs)`) — it is cleaner and
  faster. A comprehension when you would otherwise need a lambda, which `map` makes slower.
- **Q:** Why was `reduce` moved out of builtins in Python 3?
  **A:** Almost every real use is already `sum`, `max`, `min`, `any`, `all`, `math.prod` or
  `join`; the rest are hard to read. Note `reduce(operator.add, list_of_lists)` is **O(n²)**.
- **Q:** How do Java Streams map onto Python?
  **A:** `.map(f).filter(p).collect(toList())` → `[f(x) for x in xs if p(x)]`;
  `groupingBy` → `defaultdict(list)`; `.parallelStream()` has **no** equivalent (the GIL).

**`11_java_to_python_bridge.py`**

- **Q:** Coming from Java, what actually differs rather than just looking different?
  **A:** The GIL (threads give concurrency, not parallelism); real multiple inheritance, so
  `super()` means "next in the MRO", not "the parent"; and nothing is enforced — no `private`,
  no checked exceptions, and type hints are not checked at runtime.
  → [11_java_to_python_bridge.py:1](01_python_core/11_java_to_python_bridge.py#L1)
- **Q:** Why no pre-emptive getters and setters in Python?
  **A:** A public attribute can become a `@property` later **without breaking any caller**, so
  defensive accessors buy nothing. `get_name()` is the loudest Java accent there is.
- **Q:** What is `typing.Protocol` and why has Java no equivalent?
  **A:** A structural contract — the implementing class never imports it, so you can retrofit a
  type contract onto a third-party class you do not control.

**`09_memory_management.py`**

- **Q:** How does CPython actually free memory, and what does the GC add on top of refcounting?
  **A:** Reference counting frees an object the instant its count hits zero; a generational
  cyclic GC (`gc.collect()`) is needed on top for reference cycles, which refcounting alone can
  never resolve.
  → [09_memory_management.py:16](01_python_core/09_memory_management.py#L16) (cycle demo: [line 26](01_python_core/09_memory_management.py#L26))
- **Q:** How do you cache objects without keeping them alive forever?
  **A:** `weakref.WeakValueDictionary` — entries vanish automatically once no other strong
  reference to the value exists, avoiding a classic cache-based memory leak.
  → [09_memory_management.py:47](01_python_core/09_memory_management.py#L47)
- **Q:** What does `__slots__` actually trade off?
  **A:** Removes the per-instance `__dict__`, cutting memory (~40%+ for small objects), at the
  cost of losing the ability to add arbitrary new attributes.
  → [09_memory_management.py:75](01_python_core/09_memory_management.py#L75)
- **Q:** How do you find exactly which line is allocating the most memory?
  **A:** `tracemalloc.start()` → `take_snapshot()` → `.statistics("lineno")`.
  → [09_memory_management.py:102](01_python_core/09_memory_management.py#L102)

**`12_variable_scope_namespaces.py`**

- **Q:** Explain the LEGB rule.
  **A:** A bare name is resolved Local -> Enclosing *function* -> Global (= module-level) -> Built-in,
  and the classification is decided at **compile time** (`LOAD_FAST` vs `LOAD_GLOBAL`), not when the
  line runs.
  → [12_variable_scope_namespaces.py:21](01_python_core/12_variable_scope_namespaces.py#L21)
- **Q:** Why does reading a module-level `counter` inside a function that also assigns to it raise
  `UnboundLocalError`?
  **A:** Because the assignment anywhere in the body makes the name local for the **whole** function —
  including the line above it. Fix by passing it in and returning it out; `global` is the last resort.
  → [12_variable_scope_namespaces.py:63](01_python_core/12_variable_scope_namespaces.py#L63)
- **Q:** Does mutating a module-level dict need `global`?
  **A:** No. `global`/`nonlocal` are about **rebinding a name**; `config["k"] = v` mutates the object the
  name already points at. Only `config = {}` needs `global`.
  → [12_variable_scope_namespaces.py:101](01_python_core/12_variable_scope_namespaces.py#L101)
- **Q:** What does `nonlocal` do and when do you use it?
  **A:** Rebinds a name in the nearest **enclosing function** scope (it must already exist). Its real use
  is closure state — a tiny object with one method, which is how a stateful decorator keeps a counter.
  → [12_variable_scope_namespaces.py:119](01_python_core/12_variable_scope_namespaces.py#L119)
- **Q:** Why can a method not see a class attribute as a bare name?
  **A:** A class body executes in its own namespace and is **not** an enclosing scope for anything nested
  in it — so methods need `self.x`, and a comprehension in a class body cannot see the class's own
  attributes (it *can* see globals).
  → [12_variable_scope_namespaces.py:179](01_python_core/12_variable_scope_namespaces.py#L179)
- **Q:** Why do all the lambdas created in a loop return the same value?
  **A:** Closures capture the **variable**, not the value (late binding). Bind eagerly with a default
  argument (`lambda i=i: i`) or `functools.partial`.
  → [12_variable_scope_namespaces.py:204](01_python_core/12_variable_scope_namespaces.py#L204)
- **Q:** What is wrong with module-level mutable state in a service?
  **A:** It leaks between tests, `+= 1` is not thread-safe, and it does not survive scaling out — an
  in-process rate limiter becomes 4 limiters on 4 pods. Module level is for immutable constants; use a
  `ContextVar` for per-request state.
  → [12_variable_scope_namespaces.py:240](01_python_core/12_variable_scope_namespaces.py#L240)

**`13_abstract_base_classes.py`**

- **Q:** What does an ABC actually enforce, and when?
  **A:** A subclass missing an `@abstractmethod` raises `TypeError` **at instantiation**, naming what is
  missing (`__abstractmethods__` lists it). The value is *when* you find out — at construction, not on
  the first production call.
  → [13_abstract_base_classes.py:21](01_python_core/13_abstract_base_classes.py#L21)
- **Q:** Is an ABC the same as a Java interface?
  **A:** No — it can carry concrete code, which is the main reason to choose it: the **template-method**
  pattern (the algorithm once in the base, abstract steps, optional hooks with defaults).
  → [13_abstract_base_classes.py:60](01_python_core/13_abstract_base_classes.py#L60)
- **Q:** How do you make a property abstract, and what is the trap?
  **A:** `@property` above `@abstractmethod` — `@abstractmethod` must be **innermost**. Reverse them and
  the abstractness is silently lost, with no warning.
  → [13_abstract_base_classes.py:99](01_python_core/13_abstract_base_classes.py#L99)
- **Q:** What does an ABC *not* check?
  **A:** Signatures and types. A subclass with the wrong signature instantiates happily and fails at call
  time — so you need three layers: the ABC for names, mypy for signatures, and a shared contract test
  suite for the semantics.
  → [13_abstract_base_classes.py:138](01_python_core/13_abstract_base_classes.py#L138)
- **Q:** ABC vs `typing.Protocol` — when each?
  **A:** ABC (nominal) when you own the hierarchy and want shared code; `Protocol` (structural) to
  describe what a function needs, especially for third-party classes that cannot import your base.
  `@runtime_checkable` `isinstance` checks **member names only**.
  → [13_abstract_base_classes.py:159](01_python_core/13_abstract_base_classes.py#L159)
- **Q:** What does `ABC.register()` give you, and what does it not?
  **A:** `isinstance`/`issubclass` pass — but no inherited code, **no abstract-method check**, and it is
  not in the MRO. It is a label, not a verification. (It is how `isinstance([], Sequence)` works.)
  → [13_abstract_base_classes.py:189](01_python_core/13_abstract_base_classes.py#L189)
- **Q:** What do you get from `collections.abc`?
  **A:** Implement `__getitem__`/`__iter__`/`__len__` and `Mapping` gives you `get`, `keys`, `items`,
  `values`, `__contains__` and `__eq__` — plus immutability by construction, since `Mapping` has no
  `__setitem__`.
  → [13_abstract_base_classes.py:211](01_python_core/13_abstract_base_classes.py#L211)
- **Q:** When would you use `__init_subclass__` instead of an ABC?
  **A:** When the check should fire at **class definition** (import time) rather than instantiation, or
  when it is something an ABC cannot express — "every plugin must declare a name". Lighter and far more
  readable than a metaclass.
  → [13_abstract_base_classes.py:246](01_python_core/13_abstract_base_classes.py#L246)

**`14_python_basics_essentials.py`**

- **Q:** `is` vs `==`, and why does `is` sometimes appear to work?
  **A:** `is` is identity, `==` is value. CPython caches small ints (-5..256) and interns some strings —
  an implementation detail. Use `is` only for `None`/`True`/`False`/sentinels.
  → [14_python_basics_essentials.py:21](01_python_core/14_python_basics_essentials.py#L21)
- **Q:** Is Python pass-by-value or pass-by-reference?
  **A:** Neither — pass-by-**object-reference**. You can always *mutate* the caller's object; you can
  never *rebind* the caller's name.
  → [14_python_basics_essentials.py:49](01_python_core/14_python_basics_essentials.py#L49)
- **Q:** What is the mutable-default-argument bug?
  **A:** Defaults are evaluated once at `def` time, so the same list is shared across every call (visible
  in `fn.__defaults__`). Use `None` as a sentinel, or `field(default_factory=list)` in a dataclass.
  → [14_python_basics_essentials.py:72](01_python_core/14_python_basics_essentials.py#L72)
- **Q:** What bug does truthiness cause?
  **A:** `if not discount:` silently ignores a deliberate `0`; `if not items:` cannot tell "no filter
  supplied" from "filter matched nothing". `if x is None` asks a different question — use the one you
  mean.
  → [14_python_basics_essentials.py:94](01_python_core/14_python_basics_essentials.py#L94)
- **Q:** Shallow vs deep copy — when does it matter?
  **A:** `.copy()`/`{**d}` copy the container, not what is inside, so a nested config default mutated by
  one request changes every later request in that process. Prefer immutability or a factory function over
  `deepcopy`.
  → [14_python_basics_essentials.py:119](01_python_core/14_python_basics_essentials.py#L119)
- **Q:** What are `/` and `*` in a signature for?
  **A:** `/` ends positional-only parameters; `*` starts keyword-only ones. Keyword-only is how you keep
  a public API changeable and call sites readable — every boolean flag should be keyword-only.
  → [14_python_basics_essentials.py:137](01_python_core/14_python_basics_essentials.py#L137)
- **Q:** Why is `+=` on strings in a loop a performance bug?
  **A:** Strings are immutable, so each `+=` allocates and copies — O(n^2). Accumulate in a list and
  `"".join()` once, or use `io.StringIO`.
  → [14_python_basics_essentials.py:195](01_python_core/14_python_basics_essentials.py#L195)
- **Q:** `sorted()` vs `list.sort()`, and what does stability buy you?
  **A:** `sorted()` returns a new list; `.sort()` returns `None` and mutates. Sort is stable, so equal keys
  keep their order — which is what makes multi-pass sorting (and sortable table columns) work. A tuple
  key sorts by each element in turn.
  → [14_python_basics_essentials.py:218](01_python_core/14_python_basics_essentials.py#L218)
- **Q:** Are type hints enforced?
  **A:** Not at runtime. mypy/pyright enforce them in CI; Pydantic enforces them at the **boundary**
  (request bodies, config, events). Validate at the edges, trust inside.
  → [14_python_basics_essentials.py:252](01_python_core/14_python_basics_essentials.py#L252)
- **Q:** What does `-7 // 2` give, and why does it matter?
  **A:** `-4` — Python floors toward negative infinity (Java truncates to `-3`), and `%` takes the
  **divisor's** sign. It matters the moment you port a hash-based sharding or partitioning function.
  → [14_python_basics_essentials.py:276](01_python_core/14_python_basics_essentials.py#L276)

**`15_nested_exception_handling.py`**

- **Q:** How are multiple `except` clauses evaluated, and what is the classic bug?
  **A:** Top-down, first `isinstance` match wins — so a parent class above a child makes the child's
  handler **dead code**, with no warning from Python. Order specific to general, or by decision
  (retryable -> permanent -> unknown).
  → [15_nested_exception_handling.py:25](01_python_core/15_nested_exception_handling.py#L25)
- **Q:** When do you nest `try` blocks?
  **A:** When different parts of the body have different recovery strategies. Handle each error at the
  layer that can actually do something; let the rest propagate.
  → [15_nested_exception_handling.py:72](01_python_core/15_nested_exception_handling.py#L72)
- **Q:** How do errors cross layer boundaries?
  **A:** Each layer catches the layer below's type and raises its own with `raise ... from e`, so the
  storage type never leaks upward and the root cause survives. HTTP status codes are decided in one
  place, at the boundary.
  → [15_nested_exception_handling.py:108](01_python_core/15_nested_exception_handling.py#L108)
- **Q:** What is the exact order of `try`/`except`/`else`/`finally`?
  **A:** `try` -> (`except` | `else`) -> `finally`, always. On `return`, the value is computed, then
  `finally` runs, then the caller gets it. `else` exists to keep your `except` narrow.
  → [15_nested_exception_handling.py:166](01_python_core/15_nested_exception_handling.py#L166)
- **Q:** What are the three ways nested handling silently loses an error?
  **A:** Raising inside `except` without `from` (the cause only lands in `__context__`); raising **or
  returning** in `finally` (it destroys the in-flight exception); and an over-broad inner handler with a
  `continue` (rows vanish with no log and no metric).
  → [15_nested_exception_handling.py:232](01_python_core/15_nested_exception_handling.py#L232)
- **Q:** What does `__exit__` returning `True` do?
  **A:** It **swallows** the exception. Right for a best-effort audit write, catastrophic for a payment —
  so return `issubclass(exc_type, TheOneExpectedError)`, never a bare `True`. In `@contextmanager` form
  the exception surfaces at the `yield`.
  → [15_nested_exception_handling.py:290](01_python_core/15_nested_exception_handling.py#L290)
- **Q:** What is `ExceptionGroup`/`except*` for?
  **A:** Several independent failures at once (concurrency). **Multiple `except*` branches can all run**
  for one group — which is how you split a failed batch into "retry these" and "DLQ those".
  `asyncio.TaskGroup` raises these natively.
  → [15_nested_exception_handling.py:373](01_python_core/15_nested_exception_handling.py#L373)
- **Q:** What is `add_note()` for?
  **A:** Attaching context (a Kafka offset, an attempt number) **without** changing the exception's type
  or message — so handlers above still match and the traceback still carries the coordinates.
  → [15_nested_exception_handling.py:408](01_python_core/15_nested_exception_handling.py#L408)

**`16_methods_and_builtin_decorators.py`**

- **Q:** What is the difference between an instance method, a `@classmethod` and a `@staticmethod`?
  **A:** Only what gets prepended as the first argument — the instance, the class, or nothing. Ask what
  the method needs: instance data -> instance method, the class -> `@classmethod`, neither ->
  `@staticmethod`. All three are callable on an instance.
  → [16_methods_and_builtin_decorators.py:29](01_python_core/16_methods_and_builtin_decorators.py#L29)
- **Q:** Why use `@classmethod` rather than `@staticmethod` for a factory / alternative constructor?
  **A:** `cls` is the **actual** class, so a subclass gets a subclass back. A `@staticmethod` factory has
  to hardcode the class name, so every subclass silently receives the wrong type — the same `cls` trick
  is why `dict.fromkeys()` works on a dict subclass.
  → [16_methods_and_builtin_decorators.py:71](01_python_core/16_methods_and_builtin_decorators.py#L71)
- **Q:** How do they actually work?
  **A:** All three are **descriptors**: `function.__get__` returns a method bound to the instance,
  `classmethod.__get__` binds the class, `staticmethod.__get__` returns the plain function. That is the
  entire difference — and it explains `obj.m.__self__`, `obj.m.__func__`, and `Cls.m(obj)`.
  → [16_methods_and_builtin_decorators.py:126](01_python_core/16_methods_and_builtin_decorators.py#L126)
- **Q:** `@staticmethod` or a module-level function?
  **A:** A module function is the default. `@staticmethod` earns its place when the name belongs to the
  class, or when a subclass may **override** it — which it can, unlike a module function, and the
  override is picked up when called through `self`.
  → [16_methods_and_builtin_decorators.py:165](01_python_core/16_methods_and_builtin_decorators.py#L165)
- **Q:** What is `@property` for, and when is it the wrong tool?
  **A:** Validation on assignment, a computed value that cannot drift, and promoting a plain attribute
  to logic without changing any caller — which is why you never write `get_x()`/`set_x()` in Python.
  Wrong when it is expensive, can raise, or has side effects: `obj.x` looks free, so a property that
  queries a DB turns a loop into N queries and fires on `repr()` too.
  → [16_methods_and_builtin_decorators.py:199](01_python_core/16_methods_and_builtin_decorators.py#L199)
- **Q:** `@property` vs `@cached_property` vs `@lru_cache`?
  **A:** `property` recomputes every access; `cached_property` computes once per instance and then *is*
  an instance attribute (invalidate with `del obj.attr`); `lru_cache` caches by argument tuple on the
  function itself. `cached_property` needs a `__dict__` (so no `__slots__`) and has had no lock since
  3.12.
  → [16_methods_and_builtin_decorators.py:258](01_python_core/16_methods_and_builtin_decorators.py#L258)
- **Q:** Why is `@lru_cache` on a method a memory leak?
  **A:** The cache lives on the **class** and the key includes `self`, so it holds a strong reference to
  every instance it has seen — provably: the object survives `del` + `gc.collect()`. Fix with
  `@cached_property`, a per-instance dict, or by hoisting the pure part into a static function.
  → [16_methods_and_builtin_decorators.py:315](01_python_core/16_methods_and_builtin_decorators.py#L315)
- **Q:** What are the decorator-stacking traps?
  **A:** `@abstractmethod` must be **innermost** or the abstractness is silently lost; and
  `@classmethod` on top of `@property` worked on 3.9-3.12 but was removed in 3.13 — on 3.13+ it does
  not raise, it just returns a bound method instead of the value.
  → [16_methods_and_builtin_decorators.py:363](01_python_core/16_methods_and_builtin_decorators.py#L363)
- **Q:** How do you overload a method in Python?
  **A:** You cannot — a second `def` replaces the first. Use default/keyword arguments,
  `@functools.singledispatchmethod` to dispatch on the first argument's runtime type (and it lets
  third-party code register its own types), or `typing.overload` for the type checker only.
  → [16_methods_and_builtin_decorators.py:398](01_python_core/16_methods_and_builtin_decorators.py#L398)
- **Q:** Which decorators write methods for you?
  **A:** `@functools.total_ordering` (the other three comparisons from `__eq__` + one) and `@dataclass`
  (`__init__`/`__repr__`/`__eq__` from annotations). Note `frozen=True` adds `__hash__` but a **mutable
  field still makes instances unhashable**, and defining `__eq__` sets `__hash__ = None`.
  → [16_methods_and_builtin_decorators.py:430](01_python_core/16_methods_and_builtin_decorators.py#L430)
- **Q:** `__new__` vs `__init__`?
  **A:** `__new__` creates and returns the object (an implicit `staticmethod`); `__init__` initialises
  it. You need `__new__` only for subclassing an immutable type or controlling instance creation — and
  note `__init__` still runs even when `__new__` returns an existing object, which breaks naive
  singletons.
  → [16_methods_and_builtin_decorators.py:494](01_python_core/16_methods_and_builtin_decorators.py#L494)

### 02 — Concurrency

**`01_threading_demo.py`**

- **Q:** Why isn't `counter += 1` safe across threads, and how do you fix it?
  **A:** It's a read-modify-write, not atomic — another thread can interleave between the read
  and the write. Fix with `threading.Lock`.
  → [01_threading_demo.py:15](02_concurrency/01_threading_demo.py#L15) (fixed: [line 40](02_concurrency/01_threading_demo.py#L40))
- **Q:** How much does a `ThreadPoolExecutor` actually help with 10 blocking I/O calls?
  **A:** ~10x — the GIL is released during blocking I/O, so 10× 0.3s calls complete in ~0.3s
  total instead of 3s.
  → [01_threading_demo.py:62](02_concurrency/01_threading_demo.py#L62)

**`02_multiprocessing_demo.py`**

- **Q:** Why doesn't threading speed up CPU-bound work, and what does?
  **A:** The GIL lets only one thread run Python bytecode at a time — genuine parallelism for
  CPU-bound work needs separate processes (`ProcessPoolExecutor`), each with its own interpreter
  and GIL.
  → [02_multiprocessing_demo.py:13](02_concurrency/02_multiprocessing_demo.py#L13)
- **Q:** Why is the `if __name__ == "__main__":` guard mandatory with multiprocessing?
  **A:** The "spawn" start method (default on Windows/macOS) re-imports the module in each child
  process; without the guard, importing the file would recursively spawn more pools.
  → [02_multiprocessing_demo.py:37](02_concurrency/02_multiprocessing_demo.py#L37)

**`03_asyncio_demo.py`**

- **Q:** What actually lets `asyncio.gather` run 20 "requests" concurrently on ONE thread?
  **A:** Each `await` is the only point control can switch to another coroutine — the event loop
  interleaves them cooperatively.
  → [03_asyncio_demo.py:20](02_concurrency/03_asyncio_demo.py#L20)
- **Q:** How do you cap concurrency in asyncio (e.g. max 5 in-flight calls)?
  **A:** `asyncio.Semaphore(5)`, acquired via `async with` around the call.
  → [03_asyncio_demo.py:28](02_concurrency/03_asyncio_demo.py#L28)
- **Q:** What happens if you call a blocking function (`time.sleep`, `requests.get`) inside `async def`?
  **A:** It freezes the ENTIRE event loop — every other coroutine stalls. Offload it with
  `await asyncio.to_thread(fn)`.
  → [03_asyncio_demo.py:46](02_concurrency/03_asyncio_demo.py#L46)
- **Q:** How do you time out and cancel a coroutine that's taking too long?
  **A:** `async with asyncio.timeout(seconds): ...` — raises `TimeoutError` and cancels the inner
  task.
  → [03_asyncio_demo.py:61](02_concurrency/03_asyncio_demo.py#L61)
- **Q:** What's the producer/consumer shape with `asyncio.Queue`?
  **A:** A bounded queue with a sentinel (`None`) signaling "no more work" — mirrors how a Kafka
  consumer might feed a worker pool.
  → [03_asyncio_demo.py:75](02_concurrency/03_asyncio_demo.py#L75)

**`04_sync_primitives.py`**

- **Q:** How do you make one thread wait for a signal from another?
  **A:** `threading.Event` — `.wait()` blocks until another thread calls `.set()`.
  → [04_sync_primitives.py:14](02_concurrency/04_sync_primitives.py#L14)
- **Q:** How do you cap concurrent access to a limited resource (e.g. max 3 DB connections)?
  **A:** `threading.Semaphore(3)`.
  → [04_sync_primitives.py:37](02_concurrency/04_sync_primitives.py#L37)
- **Q:** How does a deadlock actually happen, and what's the simplest fix?
  **A:** Two threads acquire the same two locks in OPPOSITE order and each waits on what the
  other holds. Fix: always acquire locks in the SAME global order everywhere.
  → [04_sync_primitives.py:60](02_concurrency/04_sync_primitives.py#L60) (fixed: [line 98](02_concurrency/04_sync_primitives.py#L98))

**`benchmark_concurrency_models.py`**

- **Q:** For pure I/O-bound work, how do sequential, threaded, and asyncio approaches actually compare?
  **A:** Threads and asyncio land at roughly the same wall-clock time for I/O wait; the real gap
  shows up at scale — asyncio's ~1KB-per-coroutine footprint scales to tens of thousands of
  concurrent operations where an equally large thread pool would exhaust OS resources.
  → [benchmark_concurrency_models.py:10](02_concurrency/benchmark_concurrency_models.py#L10)

### 03 — Pandas for Data Handling

**`01_series_dataframe_basics.py`**

- **Q:** `loc` vs. `iloc` — what's the actual difference, and where does it bite people?
  **A:** `loc` is label-based and slice-INCLUSIVE; `iloc` is position-based and slice-EXCLUSIVE
  (like a normal Python list) — the inclusivity difference is the classic gotcha.
  → [01_series_dataframe_basics.py:23](03_pandas_data_handling/01_series_dataframe_basics.py#L23)

**`02_missing_data_groupby_merge.py`**

- **Q:** How do you decide between `dropna` and `fillna`, and what should you fill with?
  **A:** Base it on what the missingness MEANS in context — never blindly fill with 0; e.g. a
  missing amount on a FAILED order plausibly means "no charge happened."
  → [02_missing_data_groupby_merge.py:15](03_pandas_data_handling/02_missing_data_groupby_merge.py#L15)
- **Q:** `groupby().agg()` vs. `.transform()` — when do you need each?
  **A:** `agg` reduces each group to one row; `transform` returns a result the SAME shape as the
  input — use it for per-row features like "% of this row's group total."
  → [02_missing_data_groupby_merge.py:33](03_pandas_data_handling/02_missing_data_groupby_merge.py#L33)
- **Q:** How do you catch a silently-broken join before it drops data?
  **A:** `merge(..., indicator=True)` adds a `_merge` column showing exactly which rows matched
  from which side (`left_only`/`right_only`/`both`).
  → [02_missing_data_groupby_merge.py:51](03_pandas_data_handling/02_missing_data_groupby_merge.py#L51)

**`03_performance_large_data.py`**

- **Q:** How much faster is a vectorized operation than `.apply()`, concretely?
  **A:** Typically an order of magnitude or more — `np.where`/`.str`/`.dt` run in C; `.apply()`
  calls a Python function per row.
  → [03_performance_large_data.py:16](03_pandas_data_handling/03_performance_large_data.py#L16)
- **Q:** How do you aggregate a CSV that's bigger than RAM?
  **A:** `pd.read_csv(..., chunksize=N)` and accumulate into a running dict/aggregate per chunk.
  → [03_performance_large_data.py:38](03_pandas_data_handling/03_performance_large_data.py#L38)
- **Q:** What are the two biggest levers for reducing a DataFrame's memory footprint?
  **A:** Downcasting numeric dtypes (`pd.to_numeric(..., downcast=...)`) and converting
  low-cardinality string columns to `category` — this repo's demo measures an 87% reduction.
  → [03_performance_large_data.py:51](03_pandas_data_handling/03_performance_large_data.py#L51)

### 04 — TDD, Unit & Integration Testing

- **Q:** What's the Red-Green-Refactor loop, concretely, on a real class?
  **A:** Write a failing test → minimum code to pass it → refactor without breaking it — see the
  fixture/mock/parametrize pattern applied end to end to `OrderService`.
  → [test_order_service.py:13](04_testing_tdd/tests/test_order_service.py#L13)
- **Q:** How do you unit-test business logic without a real database or payment gateway?
  **A:** Inject `MagicMock()` for every dependency via a `@pytest.fixture`, and assert on how they
  were CALLED (`assert_called_once_with`), not just on the return value.
  → [test_order_service.py:13](04_testing_tdd/tests/test_order_service.py#L13)
- **Q:** How do you test "N inputs, same assertion shape" without copy-pasting test functions?
  **A:** `@pytest.mark.parametrize("qty,price,expected", [...])`.
  → [test_order_service.py:45](04_testing_tdd/tests/test_order_service.py#L45)
- **Q:** How do you assert that a specific exception type (and message) is raised?
  **A:** `with pytest.raises(ValueError, match="items"): ...`.
  → [test_order_service.py:30](04_testing_tdd/tests/test_order_service.py#L30)
- **Q:** How do you prove a failure path did NOT have a side effect (e.g. never touched the DB)?
  **A:** Assert on the mock after the exception: `mock_repo.save.assert_not_called()`.
  → [test_order_service.py:35](04_testing_tdd/tests/test_order_service.py#L35)

### 05 — Web APIs: FastAPI + REST

- **Q:** How does FastAPI's dependency injection work, and how do you override it in tests?
  **A:** `Depends(callable)` is resolved once per request; a `yield`-based dependency does setup
  before `yield`/teardown after (the context-manager shape). Tests swap a dependency via
  `app.dependency_overrides[dep] = fake`.
  → [dependencies.py:19](05_web_apis_fastapi/app/dependencies.py#L19) (override usage: [tests/test_orders_api.py](05_web_apis_fastapi/tests/test_orders_api.py))
- **Q:** Where should a domain exception (like "order not found") get turned into an HTTP status code?
  **A:** Centrally, via `@app.exception_handler(NotFoundError)` — NOT with an inline
  `try/except HTTPException` scattered across every route.
  → [main.py:16](05_web_apis_fastapi/app/main.py#L16)
- **Q:** Why does chaining `require_admin` on top of `get_current_user` matter?
  **A:** Authorization is always the SECOND question, checked only once identity is already
  known — two separate `Depends()` makes that order explicit and each half independently testable.
  → [dependencies.py:31](05_web_apis_fastapi/app/dependencies.py#L31)
- **Q:** A required `Header(...)` with no default is missing from the request — what status code comes back, and from where?
  **A:** 422, from FastAPI's OWN request validation, before your function body ever runs — only a
  present-but-WRONG value reaches your code to raise your own 401.
  → [test_orders_api.py:88](05_web_apis_fastapi/tests/test_orders_api.py#L88)
- **Q:** What does `response_model` on a route actually enforce?
  **A:** Filters AND validates the outbound shape independent of the internal object — a real
  security boundary against leaking a field you forgot to hide.
  → [routers/orders.py:16](05_web_apis_fastapi/app/routers/orders.py#L16)
- **Q:** Offset vs. keyset pagination — what's the actual complexity difference?
  **A:** `OFFSET n` is O(n) (the DB scans and discards the skipped rows); keyset
  (`WHERE id > :after_id`) uses the index directly, O(log n), and stays stable under concurrent
  inserts.
  → [rest_api_notes.md:57](05_web_apis_fastapi/rest_api_notes.md#L57)

### 06 — Kafka

- **Q:** How does Kafka decide which partition a keyed message goes to, and why does that matter for ordering?
  **A:** The key is hashed to a partition — Kafka only guarantees ordering WITHIN a partition, so
  same-key messages (e.g. one customer's orders) always land on the same partition and stay
  ordered relative to each other.
  → [01_producer_basics.py:35](06_kafka/01_producer_basics.py#L35)
- **Q:** Why must you disable `enable.auto.commit` for a reliable consumer?
  **A:** Auto-commit fires on a timer regardless of whether your handler finished — commit
  manually AFTER successful processing instead (the at-least-once shape).
  → [02_consumer_basics.py:30](06_kafka/02_consumer_basics.py#L30)
- **Q:** At-most-once vs. at-least-once — where exactly does the commit go, and what fails each way?
  **A:** Commit BEFORE processing = at-most-once (a crash mid-processing LOSES the message
  forever); commit AFTER processing = at-least-once (a crash before commit causes a
  harmless-if-idempotent DUPLICATE).
  → [03_delivery_semantics.py:70](06_kafka/03_delivery_semantics.py#L70) (loss) / [line 75](06_kafka/03_delivery_semantics.py#L75) (duplicate)
- **Q:** What does Kafka's exactly-once actually require, and what does it NOT cover?
  **A:** An idempotent producer (dedupes retried batches) + a transactional producer wrapping
  both the output `produce()` and the input offset commit + `read_committed` on downstream
  consumers. It only covers Kafka-to-Kafka; an external DB sink still needs its own idempotent
  writes.
  → [03_delivery_semantics.py:82](06_kafka/03_delivery_semantics.py#L82)
- **Q:** How do you handle a poison-pill message without blocking the whole partition?
  **A:** Classify the error first — permanent (bad schema/validation) goes straight to a DLQ;
  transient gets a few short inline retries, then routes to a delayed retry-tier TOPIC instead of
  sleeping in the consumer loop (which risks exceeding `max.poll.interval.ms` and triggering a
  rebalance).
  → [04_retry_topic_dlq.py:54](06_kafka/04_retry_topic_dlq.py#L54)
- **Q:** What's the trade-off of using retry-tier topics?
  **A:** You lose strict per-key ordering — a later event for the same key on the main topic can
  be processed before the retried one catches up.
  → [04_retry_topic_dlq.py:104](06_kafka/04_retry_topic_dlq.py#L104)
- **Q:** What's the Confluent wire format, and how much overhead does Schema Registry add per message?
  **A:** `[magic byte][4-byte schema ID][payload]` — 5 bytes; the schema itself is fetched once
  by ID and cached, never resent per message.
  → [05_schema_registry_avro_notes.md:7](06_kafka/05_schema_registry_avro_notes.md#L7)
- **Q:** Under `BACKWARD` compatibility, which Avro schema changes are safe vs. unsafe?
  **A:** Safe: add a field WITH a default, or remove a field. Unsafe: add a field without a
  default, or change/remove a type incompatibly.
  → [05_schema_registry_avro_notes.md:39](06_kafka/05_schema_registry_avro_notes.md#L39)

**`06_schema_registry_simulation.py`**

- **Q:** Describe the Confluent wire format.
  **A:** Magic byte `0`, then a 4-byte big-endian schema ID, then the payload — 5 bytes total,
  so the schema itself never travels. Dumping the first byte is the fastest way to debug a
  deserialisation failure: `0x7B` means someone produced plain JSON to an Avro topic.
  → [06_schema_registry_simulation.py:1](06_kafka/06_schema_registry_simulation.py#L1)
- **Q:** BACKWARD vs FORWARD — which side do you upgrade first?
  **A:** BACKWARD (the default) means a new consumer can read old data, so upgrade **consumers**
  first. FORWARD means old consumers can read new data, so upgrade **producers** first.
- **Q:** Why does `BACKWARD_TRANSITIVE` matter?
  **A:** Plain BACKWARD only checks against the *latest* version, so v1→v2→v3 can each pass while
  v3 cannot read v1 data — which a consumer replaying a 30-day topic will hit.
- **Q:** Should a production service auto-register schemas?
  **A:** No. `auto.register.schemas=false`; CI registers after a compatibility check that fails
  the build. Otherwise any deployment can silently change a shared contract.

**`07_kafka_python_config.py`**

- **Q:** Which Python Kafka client, and why?
  **A:** `confluent-kafka-python` (librdkafka, C) for production — fastest and most complete;
  `aiokafka` if the service is asyncio, because `confluent-kafka`'s `poll`/`flush` block and would
  stall the event loop. `kafka-python` is slower; avoid for new work.
  → [07_kafka_python_config.py:16](06_kafka/07_kafka_python_config.py#L16)
- **Q:** What is the minimum producer config for "do not lose messages"?
  **A:** `acks=all` + `enable.idempotence=True` + a bounded `delivery.timeout.ms` — and **act on the
  delivery callback's error**, because `produce()` is asynchronous and a permanent failure is otherwise
  invisible. `flush()` before exit, always.
  → [07_kafka_python_config.py:105](06_kafka/07_kafka_python_config.py#L105)
- **Q:** Which consumer default loses data?
  **A:** `enable.auto.commit=True`. A background thread commits offsets on a timer, so it can commit
  messages you have not finished — a crash then loses them silently. Set it `False` and commit after the
  work succeeds.
  → [07_kafka_python_config.py:145](06_kafka/07_kafka_python_config.py#L145)
- **Q:** What does `enable.idempotence=True` imply, and what does it NOT cover?
  **A:** It implies `acks=all`, `retries>0`, `max.in.flight<=5`, and it dedupes the broker's **own**
  retries. It does nothing about your application calling `produce()` twice.
  → [07_kafka_python_config.py:182](06_kafka/07_kafka_python_config.py#L182)
- **Q:** How do you catch a contradictory Kafka config before it ships?
  **A:** Validate at startup and fail the boot: idempotence with `acks=1`, `max.in.flight>5` with
  idempotence, `retries>0` with in-flight>1 and idempotence off (silent reordering), auto-commit with
  `read_committed`.
  → [07_kafka_python_config.py:182](06_kafka/07_kafka_python_config.py#L182)
- **Q:** Where should the config live?
  **A:** Environment variables mapped to librdkafka keys (strip prefix, lowercase, `_` -> `.`), secrets
  from a secret manager, one profile per environment. MSK uses SASL_SSL + OAUTHBEARER with an IAM token
  callback; Confluent Cloud uses SASL_SSL + PLAIN.
  → [07_kafka_python_config.py:239](06_kafka/07_kafka_python_config.py#L239)
- **Q:** My consumer keeps rebalancing. Why?
  **A:** Processing takes longer than `max.poll.interval.ms` between `poll()` calls. Fix the handler, or
  lower `max.poll.records` — never `sleep()` in the loop. Note `session.timeout.ms` (heartbeat) and
  `max.poll.interval.ms` (progress) are different clocks.
  → [07_kafka_python_config.py:64](06_kafka/07_kafka_python_config.py#L64)

**`08_kafka_to_aurora_sink.py`**

- **Q:** How do you consume from Kafka and write to Aurora without losing or duplicating rows?
  **A:** Poll a batch -> validate (poison straight to the DLQ) -> **one** transaction with **one**
  idempotent upsert -> **DB commit** -> *then* commit the Kafka offset. A crash in between means a
  redelivery that the upsert turns into a no-op.
  → [08_kafka_to_aurora_sink.py:208](06_kafka/08_kafka_to_aurora_sink.py#L208)
- **Q:** What happens if you commit the Kafka offset first?
  **A:** A crash between the commit and the write loses the row **forever, silently** — which is also
  exactly what `enable.auto.commit=True` does to you on a 5-second timer.
  → [08_kafka_to_aurora_sink.py:156](06_kafka/08_kafka_to_aurora_sink.py#L156)
- **Q:** Why is a plain `INSERT` wrong?
  **A:** At-least-once delivery means redelivery is normal (every rebalance). A plain INSERT either
  raises `IntegrityError` and kills the batch, or — with no unique index — **double-counts revenue**,
  which nothing errors on. `ON CONFLICT (event_id) DO NOTHING` is the fix.
  → [08_kafka_to_aurora_sink.py:174](06_kafka/08_kafka_to_aurora_sink.py#L174)
- **Q:** Why batch the writes?
  **A:** 200 rows row-at-a-time is 200 round trips; `execute_values` makes it one. Measured at 40x fewer
  round trips in the simulation — and it is the usual reason consumer lag never drains.
  → [08_kafka_to_aurora_sink.py:193](06_kafka/08_kafka_to_aurora_sink.py#L193)
- **Q:** Do Kafka transactions give you exactly-once into a database?
  **A:** No — they cover Kafka-to-Kafka only. There is no two-phase commit between Kafka and Aurora, so
  the **idempotent write** is what makes the replay harmless: at-least-once delivery, effectively-once
  effect.
  → [08_kafka_to_aurora_sink.py:208](06_kafka/08_kafka_to_aurora_sink.py#L208)
- **Q:** What is Aurora-specific about this?
  **A:** Writes go to the **writer** endpoint; a failover takes 30-60s and invalidates pooled sockets
  (`pool_pre_ping`, bounded lifetime, treat `OperationalError` as retryable); `pods x pool_size` must
  stay under `max_connections`; IAM auth tokens expire in 15 minutes.
  → [08_kafka_to_aurora_sink.py:299](06_kafka/08_kafka_to_aurora_sink.py#L299)
- **Q:** How do you update the database and publish an event atomically?
  **A:** You cannot — there is no transaction spanning both. Use the **transactional outbox**: write the
  event row in the same transaction as the business data, then relay it (or let Debezium tail it). Every
  clever ordering of two separate writes leaves a window.
  → [08_kafka_to_aurora_sink.py:380](06_kafka/08_kafka_to_aurora_sink.py#L380)

### 07 — Caching & Queues

- **Q:** What's the cache-aside pattern, and how do you keep it correct across writes?
  **A:** Check cache → miss → load from source → populate cache (with a TTL); on write, DELETE
  the cache key so the next read is a guaranteed fresh miss instead of serving stale data.
  → [01_cache_aside_pattern.py:79](07_caching_queues/01_cache_aside_pattern.py#L79)
- **Q:** What is a cache stampede, and how do you stop 20 concurrent misses from all hitting the DB?
  **A:** A `SET key val NX`-style lock — only the requester who wins the lock rebuilds the cache;
  everyone else waits briefly and retries the read. This repo's demo goes from ~20 DB calls down
  to exactly 1.
  → [02_cache_stampede_lock.py:63](07_caching_queues/02_cache_stampede_lock.py#L63) (broken) / [line 100](07_caching_queues/02_cache_stampede_lock.py#L100) (fixed)
- **Q:** How does a bounded queue give you backpressure for free?
  **A:** `queue.Queue(maxsize=N)` — `put()` blocks the producer once full, so a slow consumer
  naturally throttles a fast producer.
  → [03_queue_patterns.py:19](07_caching_queues/03_queue_patterns.py#L19)
- **Q:** How does an SQS-style visibility timeout + DLQ actually work end to end?
  **A:** A received-but-unacked message becomes invisible for `visibility_timeout`, then
  reappears for redelivery; after `maxReceiveCount` failed attempts it's moved to a DLQ
  automatically instead of blocking the queue forever.
  → [03_queue_patterns.py:46](07_caching_queues/03_queue_patterns.py#L46)

### 08 — Scaling & Production Resilience

- **Q:** Why does exponential backoff need jitter, specifically?
  **A:** Without jitter, every failing client waits the exact same delays and then ALL retry at
  the same instant — jitter spreads that spike across a window instead of hammering a
  just-recovering service.
  → [01_retry_backoff.py:77](08_scaling_production_resilience/01_retry_backoff.py#L77)
- **Q:** What are the exact state transitions of a circuit breaker?
  **A:** CLOSED (normal) → OPEN (fails fast, no calls reach the downstream) → HALF-OPEN (one
  trial call probes recovery) → back to CLOSED on success or OPEN again on failure.
  → [02_circuit_breaker.py:18](08_scaling_production_resilience/02_circuit_breaker.py#L18)
- **Q:** Circuit breaker vs. rate limiter — what is each one actually protecting?
  **A:** A rate limiter protects YOUR service from too many callers; a circuit breaker protects a
  DOWNSTREAM from your own retries once it's already unhealthy.
  → [03_rate_limiter.py:23](08_scaling_production_resilience/03_rate_limiter.py#L23)
- **Q:** Liveness vs. readiness — why does conflating them cause outages?
  **A:** Liveness = "is the process alive" (failure → Kubernetes RESTARTS it); readiness = "can
  it serve traffic right now" (failure → traffic STOPS routing, no restart). Restarting a healthy
  process because a downstream is briefly unreachable just causes a thundering herd of reconnects.
  → [04_health_checks_graceful_shutdown.py:22](08_scaling_production_resilience/04_health_checks_graceful_shutdown.py#L22)
- **Q:** What does a graceful shutdown sequence actually have to do, in order?
  **A:** Stop accepting NEW work → wait for in-flight work to drain → flush any buffered writes
  (a Kafka producer, a batched log) → exit. The container's grace period must exceed how long
  that drain takes.
  → [04_health_checks_graceful_shutdown.py:62](08_scaling_production_resilience/04_health_checks_graceful_shutdown.py#L62)

**`05_metrics_alerting_simulation.py`**

- **Q:** What is the cardinality trap?
  **A:** Labelling a metric with a raw path or a user/order ID creates one time series per value.
  Millions of series OOM your Prometheus — during the incident you needed it for. Use the route
  *template*; per-entity detail belongs in logs and traces.
  → [05_metrics_alerting_simulation.py:1](08_scaling_production_resilience/05_metrics_alerting_simulation.py#L1)
- **Q:** Histogram or Summary?
  **A:** Histogram. A Summary computes quantiles per instance, and quantiles **cannot** be
  averaged across instances — a Histogram exports bucket counts, which are additive.
- **Q:** What is an error budget and what is it *for*?
  **A:** `1 − SLO`. It is a deployment risk budget: budget left means ship freely, budget spent
  means freeze features and work on reliability.
- **Q:** Why multi-window burn-rate alerts instead of "error rate > 1%"?
  **A:** A flat threshold is both too noisy (keeps firing on a 1h average after a blip ended) and
  too blind (misses a slow 4x burn that sits under the threshold). Requiring a long **and** a
  short window to breach fixes both.

### 09 — AWS Lambda & Streaming Large Files

- **Q:** Why initialize clients OUTSIDE the Lambda handler function?
  **A:** Code outside the handler is reused across warm invocations — initializing inside pays
  connection-setup cost on every single call.
  → [01_lambda_handler_patterns.py:62](09_aws_lambda_streaming/01_lambda_handler_patterns.py#L62)
- **Q:** What must a Lambda handler do on failure for retries/DLQ to work at all?
  **A:** Re-raise the exception — returning a normal value (even a 500-shaped dict) tells Lambda
  the invocation SUCCEEDED, and it will never retry or route to a DLQ.
  → [01_lambda_handler_patterns.py:71](09_aws_lambda_streaming/01_lambda_handler_patterns.py#L71)
- **Q:** How do you process a file bigger than the function's memory without crashing?
  **A:** Stream it (row-by-row via the response body's streaming interface) with a bounded batch
  buffer, instead of `.read()`-ing the whole thing — this repo measures a 98.7% memory reduction
  doing exactly that.
  → [02_stream_large_file_s3_simulation.py:44](09_aws_lambda_streaming/02_stream_large_file_s3_simulation.py#L44)

**`03_large_file_processing.py`**

- **Q:** How would you process a 100GB file?
  **A:** Stream it — iterating a file object yields one line at a time, so peak memory is the longest
  *line*, identical at 10MB and 100GB (measured: 39MB vs 170KB on the same input). The S3 version wraps
  the `StreamingBody` instead of calling `.read()` on it.
  → [03_large_file_processing.py:80](09_aws_lambda_streaming/03_large_file_processing.py#L80)
- **Q:** What is a generator pipeline and why does it matter?
  **A:** Compose parse -> filter -> transform as generators; each record flows all the way through before
  the next is read, so peak memory is one record regardless of stage count. It reads like a query and
  each stage is unit-testable with three dicts.
  → [03_large_file_processing.py:121](09_aws_lambda_streaming/03_large_file_processing.py#L121)
- **Q:** Which operations can you do in one pass, and which cannot?
  **A:** One pass: sum/count/filter/map, and GROUP BY with few distinct keys. **Not** one pass: sort,
  exact dedupe, joins, exact percentiles. High-cardinality GROUP BY needs hash-partitioning into N files
  first — which is literally a shuffle.
  → [03_large_file_processing.py:155](09_aws_lambda_streaming/03_large_file_processing.py#L155)
- **Q:** How do you sort a file larger than RAM?
  **A:** External merge sort: read a chunk, sort it in memory, write a sorted run to disk; then
  `heapq.merge` across the runs, which holds one record per run. The same two phases as `sort -S`,
  Postgres and Spark.
  → [03_large_file_processing.py:182](09_aws_lambda_streaming/03_large_file_processing.py#L182)
- **Q:** How do you deduplicate 2 billion IDs?
  **A:** Exact: hash-partition so all copies of a key land in the same file, then a `set` per file.
  Approximate: a Bloom filter — fixed memory, **no false negatives**, but it can drop a genuinely new
  record, so use it as a pre-filter in front of a DB check.
  → [03_large_file_processing.py:239](09_aws_lambda_streaming/03_large_file_processing.py#L239)
- **Q:** How do you parallelise it, and what is the trap?
  **A:** Split into byte ranges that **start on record boundaries** — seek to the nominal offset, then
  advance to the next newline; `size // n` splits a row in half. Then processes, not threads (the GIL
  blocks CPU-bound parsing). The chunk descriptor is two integers, so it also works as a ranged S3 GET
  per Lambda.
  → [03_large_file_processing.py:299](09_aws_lambda_streaming/03_large_file_processing.py#L299)
- **Q:** How do you survive a crash 80GB in?
  **A:** Chunk the work and checkpoint after each chunk, writing to a temp file and `os.replace`-ing it
  so a crash mid-write leaves the previous checkpoint intact. The write must be idempotent, and the
  checkpoint goes *after* the side effect commits.
  → [03_large_file_processing.py:362](09_aws_lambda_streaming/03_large_file_processing.py#L362)
- **Q:** Why is a single `.gz` a problem?
  **A:** It is **not splittable** — it must be decompressed from byte 0, so byte-range parallelism is
  impossible. Use many smaller `.gz` objects, or Parquet (columnar + row groups + predicate pushdown).
  → [03_large_file_processing.py:402](09_aws_lambda_streaming/03_large_file_processing.py#L402)
- **Q:** Should this be Python at all?
  **A:** Often not. If it is in S3 and the work is SQL-shaped, convert to Parquet once and use Athena, or
  run DuckDB on one box. Write the Python streaming version when the per-record transform is genuinely
  custom or must run inside an existing service.
  → [03_large_file_processing.py:440](09_aws_lambda_streaming/03_large_file_processing.py#L440)

### 10 — GenAI / LLM Patterns

- **Q:** What's the actual pipeline shape of RAG, end to end?
  **A:** `embed(query)` → similarity search a vector DB for top-k chunks → inject them into the
  prompt → LLM generates grounded in that context, with citations back to the source chunks.
  → [02_rag_pipeline_concept.py:79](10_genai_llm_patterns/02_rag_pipeline_concept.py#L79)
- **Q:** What's the single most effective anti-hallucination prompt instruction?
  **A:** Explicitly telling the model it's ALLOWED to say "I don't have information about this" —
  removing the implicit pressure to always sound confident.
  → [01_prompt_engineering_examples.py:43](10_genai_llm_patterns/01_prompt_engineering_examples.py#L43)
- **Q:** RAG vs. fine-tuning — how do you decide?
  **A:** RAG for knowledge that changes often and needs citations; fine-tune only when the model
  needs to think/respond DIFFERENTLY (style, behavior), not just know new facts.
  → [10_genai_llm_patterns/README.md](10_genai_llm_patterns/README.md)
- **Q:** What's semantic caching, and why is a naive similarity threshold risky?
  **A:** Cache LLM responses by MEANING (embedding similarity), not exact string match, so
  paraphrased questions hit the cache too — but too low a threshold starts serving a wrong cached
  answer to unrelated questions.
  → [03_semantic_caching_concept.py:52](10_genai_llm_patterns/03_semantic_caching_concept.py#L52)

### 11 — Coding Challenges

- **Q:** Group anagrams — what's the key insight, and the complexity trade-off between approaches?
  **A:** Two words are anagrams iff sorting their characters gives the same key. A sort-based key
  is O(n·k log k); a character-frequency-array key is O(n·k) — faster for long words, at the cost
  of a fixed 26-slot allocation per word.
  → [01_anagram_grouping.py:17](11_coding_challenges/01_anagram_grouping.py#L17) (sort) / [line 27](11_coding_challenges/01_anagram_grouping.py#L27) (freq)
- **Q:** Max of every sliding window of size k — how do you get from O(n·k) to O(n)?
  **A:** A monotonic decreasing deque of INDICES — the front is always the current window's max;
  each index is pushed and popped at most once across the whole array.
  → [02_sliding_window_max.py:21](11_coding_challenges/02_sliding_window_max.py#L21)
- **Q:** How do you implement an O(1) get/put LRU cache from scratch, without `OrderedDict`?
  **A:** A dict for O(1) key lookup + a hand-rolled doubly linked list (with head/tail sentinels)
  for O(1) reordering on access — this is literally what `OrderedDict` does internally.
  → [03_lru_cache.py:47](11_coding_challenges/03_lru_cache.py#L47)
- **Q:** Why can't you reverse a string truly "in place" in Python?
  **A:** Strings are immutable — convert to a list of characters first, two-pointer swap in place
  on the list, then `"".join()`.
  → [04_reverse_string.py:14](11_coding_challenges/04_reverse_string.py#L14)
- **Q:** Design a retry decorator with a retry limit and exponential backoff. What makes it production
  code rather than a loop with a `sleep`?
  **A:** Three nesting levels (it takes arguments), `functools.wraps`, `delay = base * factor^(n-1)`
  capped by `max_delay`, **jitter** so N failing clients do not retry in the same instant, retry only
  transient errors, a bare `raise` on the last attempt so the traceback survives — and an **injectable
  `sleep`** so the tests assert the exact delay sequence in microseconds instead of waiting.
  → [05_retry_decorator.py:59](11_coding_challenges/05_retry_decorator.py#L59) (decorator) / [line 36](11_coding_challenges/05_retry_decorator.py#L36) (the delay maths)
- **Q:** Why is jitter not optional?
  **A:** Without it, 100 clients that failed together retry at exactly 0.1s, 0.2s, 0.4s... — a
  synchronised spike precisely while the service is recovering. Full jitter is `uniform(0, delay)`.
  → [05_retry_decorator.py:36](11_coding_challenges/05_retry_decorator.py#L36)
- **Q:** Why does a retry decorator need a *time* budget as well as an attempt limit?
  **A:** The decorator's limit is attempts; the caller's limit is time. A caller with a 2s SLA does not
  care that you had 5 attempts left — so check the budget **before** sleeping.
  → [05_retry_decorator.py:59](11_coding_challenges/05_retry_decorator.py#L59)
- **Q:** What is the trap in an async retry decorator?
  **A:** A blocking `time.sleep()` stalls the whole event loop — every other coroutine waits. Use
  `await asyncio.sleep()`. (And `CancelledError` is a `BaseException`, so `except Exception` correctly
  does not retry a cancelled task.)
  → [05_retry_decorator.py:101](11_coding_challenges/05_retry_decorator.py#L101)
- **Q:** What can retries alone not fix?
  **A:** A dependency that is already saturated — retrying triples your offered load at the worst moment.
  You need a **circuit breaker** alongside, and the operation must be **idempotent**, or a retry
  double-charges the customer.
  → [05_retry_decorator.py:59](11_coding_challenges/05_retry_decorator.py#L59)
- **Q:** Search for a keyword in a nested dictionary and return the matching key. What do you ask first?
  **A:** Four things: does it nest through lists too, first match or all matches, exact or substring, and
  do you want the key or the **path** — because "city" appearing twice is useless without
  `customer.address.city`.
  → [06_nested_dict_search.py:47](11_coding_challenges/06_nested_dict_search.py#L47)
- **Q:** What is the subtle bug in the obvious recursive solution?
  **A:** Guarding with `if found:` instead of `if found is not None:` — a falsy *key* like `0` or `""` is
  then skipped, and the search silently continues past a correct answer.
  → [06_nested_dict_search.py:47](11_coding_challenges/06_nested_dict_search.py#L47)
- **Q:** Why return a generator for the all-matches version?
  **A:** The caller chooses the cost: `next(gen, None)` stops at the first match, `list(gen)` walks
  everything, `islice(gen, 10)` takes ten. One function, three cost profiles.
  → [06_nested_dict_search.py:70](11_coding_challenges/06_nested_dict_search.py#L70)
- **Q:** When must the search be iterative rather than recursive?
  **A:** When the data is deep or **untrusted** — Python's ~1000-frame recursion limit makes the recursive
  version a DoS vector on adversarially nested JSON. An explicit stack is bounded only by heap, and
  `popleft` instead of `pop` gives breadth-first (the shallowest match, usually the one a human meant).
  → [06_nested_dict_search.py:121](11_coding_challenges/06_nested_dict_search.py#L121)
- **Q:** "Now do this 10,000 times a second."
  **A:** Flatten once into a `value -> [paths]` index: O(n) to build, O(1) per lookup. And if the data
  lives in Postgres, it is a `jsonb` containment query with a GIN index — do not walk JSON in Python when
  the database can index it.
  → [06_nested_dict_search.py:175](11_coding_challenges/06_nested_dict_search.py#L175)

---

### 12 — Framework Internals

**`01_repository_pattern.py`**

- **Q:** What is the single highest-value structural decision when laying out a service?
  **A:** The repository pattern — it lets you swap PostgreSQL for Couchbase, or add a cache
  layer, without touching business logic, and lets you unit-test services with no database.
  → [01_repository_pattern.py:1](12_framework_internals/01_repository_pattern.py#L1)
- **Q:** Should a repository call `commit()`?
  **A:** No — `flush()` only. The *service* owns the transaction boundary, because one business
  operation may span several repositories and must commit atomically.
- **Q:** Why must the service layer never import the web framework?
  **A:** So the same service is callable from a Kafka consumer, a CLI command or a Lambda. It
  raises *domain* exceptions; a central handler maps those to HTTP status codes in one place.

**`02_dependency_injection.py`**

- **Q:** What does FastAPI's `Depends()` actually do?
  **A:** Resolves a dependency graph per request, caches each dependency once per request, and
  supports `yield` for setup/teardown that runs after the response.
  → [02_dependency_injection.py:1](12_framework_internals/02_dependency_injection.py#L1)
- **Q:** Why does per-request caching matter?
  **A:** A `get_db` depended on by three other dependencies opens **one** connection, so all
  your queries run in one transaction. Without it you'd get three connections.
- **Q:** Why is DI better than a module-level `settings` global?
  **A:** `app.dependency_overrides` swaps any node of the graph in tests with no patching and no
  source changes — which is why the unit suite runs in milliseconds.

**`03_plugin_architecture.py`**

- **Q:** Three ways to build a plugin system, and their trade-offs?
  **A:** A decorator registry (simple, but the module must be *imported* to register);
  `__init_subclass__` (registers at class definition, subclasses only); setuptools entry points
  (a separate pip package can extend you, at packaging cost).
  → [03_plugin_architecture.py:1](12_framework_internals/03_plugin_architecture.py#L1)
- **Q:** When should you *not* build a plugin system?
  **A:** For two or three implementations you control — an `if`/`else` and a config value is the
  right amount of engineering until a third party actually needs to extend you.

**`04_middleware_and_config.py`**

- **Q:** In what order does middleware run?
  **A:** The middleware added **last** is the **outermost** and runs **first**. Get it wrong and
  a cache hit short-circuits before your auth check.
  → [04_middleware_and_config.py:1](12_framework_internals/04_middleware_and_config.py#L1)
- **Q:** What's the cardinality trap in metrics middleware?
  **A:** Labelling by `request.url.path` creates one time series per order ID. Use the route
  *template* (`/orders/{id}`), or you'll OOM Prometheus during the incident you needed it for.
- **Q:** Why should config validation happen at startup?
  **A:** A missing `DB_URL` or a typo'd `WORKER=8` should crash the process at boot, in staging,
  with a message naming the problem — not silently use a default and surface at 3am.

### 13 — System Design & Scenario Questions

**`01_zero_downtime_change.py`**

- **Q:** How would you fix an issue in a distributed production system with zero downtime?
  **A:** Mitigate before you fix. Declare the incident, then flip the feature flag off / shift traffic /
  shed load / scale out — seconds to minutes, no deploy. Stabilise and say so in metrics; the clock stops
  there. *Then* diagnose calmly and ship the fix behind a canary.
  → [01_zero_downtime_change.py:98](13_system_design_scenarios/01_zero_downtime_change.py#L98)
- **Q:** What is the difference between liveness and readiness?
  **A:** Liveness failing means **restart me**; readiness failing means **remove me from the load
  balancer**. Liveness must never check a dependency, or one DB blip restarts the whole fleet. No
  readiness gate is why "deploys always cause a brief error spike".
  → [01_zero_downtime_change.py:29](13_system_design_scenarios/01_zero_downtime_change.py#L29)
- **Q:** When is a rolling deploy actually zero-downtime?
  **A:** Only if you **drain** (fail readiness, let the LB deregister, wait for in-flight requests) and
  **gate** the new instance on its readiness probe. The simulation shows 0 failed requests with both, and
  ~22% without — while every pod reports "Running" in both cases.
  → [01_zero_downtime_change.py:131](13_system_design_scenarios/01_zero_downtime_change.py#L131)
- **Q:** Blue/green vs canary?
  **A:** Blue/green verifies with zero customer traffic and rolls back with an instant pointer flip, at 2x
  infrastructure. A canary bounds the blast radius with real traffic — and you must measure the canary's
  **own** error rate, because averaging it over the fleet hides a 20% failure under a 1% SLO.
  → [01_zero_downtime_change.py:174](13_system_design_scenarios/01_zero_downtime_change.py#L174) (blue/green) / [line 206](13_system_design_scenarios/01_zero_downtime_change.py#L206) (canary)
- **Q:** How do you change a database schema with zero downtime?
  **A:** **Expand -> migrate -> contract**, as three separate deploys: add nullable columns and
  dual-write; backfill in throttled resumable batches and switch reads; drop the old column *days* later
  (that gap is the rollback window). Plus `lock_timeout` so an `ALTER TABLE` fails fast instead of
  queueing behind a long read and blocking everything.
  → [01_zero_downtime_change.py:233](13_system_design_scenarios/01_zero_downtime_change.py#L233)
- **Q:** What does graceful shutdown involve?
  **A:** SIGTERM -> fail readiness (and sleep a few seconds so the LB notices) -> finish in-flight work ->
  flush the producer, commit offsets, close the pool -> exit 0, all inside
  `terminationGracePeriodSeconds`. Skip it and every deploy costs 502s and **lost** unflushed events.
  → [01_zero_downtime_change.py:233](13_system_design_scenarios/01_zero_downtime_change.py#L233)

**`02_observability_pillars.py`**

- **Q:** What is the difference between monitoring and observability?
  **A:** Monitoring checks known signals against known thresholds — it answers questions you wrote in
  advance. Observability lets you answer **new** questions from the data you already emit, without
  shipping code.
  → [02_observability_pillars.py:36](13_system_design_scenarios/02_observability_pillars.py#L36)
- **Q:** What are the three pillars, and why do you need all three?
  **A:** Metrics say *that* it is broken, logs say *what happened to this request*, traces say *where the
  time went*. And cardinality forces the split: a user ID cannot be a metric label, so high-cardinality
  data has to live in logs and span attributes.
  → [02_observability_pillars.py:63](13_system_design_scenarios/02_observability_pillars.py#L63)
- **Q:** Why does latency go in a histogram and never an average?
  **A:** An average hides the tail: 99% at 50ms and 1% at 10s averages to 150ms and looks fine while 1 in
  100 customers times out. Bucket boundaries must straddle your SLO threshold or you cannot measure
  compliance.
  → [02_observability_pillars.py:63](13_system_design_scenarios/02_observability_pillars.py#L63)
- **Q:** What is the cardinality rule?
  **A:** Series count is the product of all label cardinalities. `route`/`status`/`region` are fine;
  `user_id`/`order_id` create one series per value and take your monitoring system down during the
  incident you needed it for.
  → [02_observability_pillars.py:63](13_system_design_scenarios/02_observability_pillars.py#L63)
- **Q:** How does a trace survive a network hop?
  **A:** The W3C `traceparent` header on every outbound HTTP call **and in every Kafka message header**.
  Drop it on one hop and the trace splits into two unconnected halves — the usual reason a distributed
  trace looks broken.
  → [02_observability_pillars.py:174](13_system_design_scenarios/02_observability_pillars.py#L174)
- **Q:** Why a `ContextVar` for the correlation ID rather than a global or `threading.local`?
  **A:** A global is shared by every concurrent request; `threading.local` is wrong for asyncio because
  thousands of tasks share one thread. A `ContextVar` is isolated per task *and* per thread — and you must
  `reset(token)` in a `finally`, or the value leaks into the next request.
  → [02_observability_pillars.py:48](13_system_design_scenarios/02_observability_pillars.py#L48)
- **Q:** Explain SLI, SLO and error budget, and how you alert on them.
  **A:** SLI = the measurement, SLO = the target, error budget = `1 - SLO` (99.9% is ~40 min per 28 days).
  Alert on multi-window **burn rate** — 14.4x over an hour pages, ~1.5x over six hours tickets — and on
  **symptoms** the customer feels, never on causes like CPU.
  → [02_observability_pillars.py:259](13_system_design_scenarios/02_observability_pillars.py#L259)
- **Q:** RED vs USE, and which signal predicts an outage?
  **A:** RED (Rate, Errors, Duration) for services; USE (Utilization, Saturation, Errors) for resources.
  **Saturation** is the leading indicator: a pool at 100% utilization with 0 waiters is fine, with 50
  waiters you are already failing and the latency graph has not caught up.
  → [02_observability_pillars.py:259](13_system_design_scenarios/02_observability_pillars.py#L259)

**`03_capacity_scaling_tps.py`**

- **Q:** Traffic is going from 100 TPS to 600 TPS. How do you scale?
  **A:** Measure first (per-request cost from a trace, and the **peak-to-mean ratio** — 600 average with a
  2.4x peak is really 1440). Then Little's Law for the numbers, remove work before buying capacity, scale
  what is left, protect it with backpressure, and load-test to 2x.
  → [03_capacity_scaling_tps.py:109](13_system_design_scenarios/03_capacity_scaling_tps.py#L109)
- **Q:** What is Little's Law and why is it the whole answer?
  **A:** `concurrency = arrival rate x latency`. 600 TPS x 282ms = 169 in flight; at 120ms it is 72. So
  **halving latency halves the fleet you must provision** — latency reduction and capacity are the same
  lever, and the cheap one.
  → [03_capacity_scaling_tps.py:38](13_system_design_scenarios/03_capacity_scaling_tps.py#L38)
- **Q:** Why never plan past ~70% utilization?
  **A:** Queueing delay goes as `1/(1-rho)`: 80% busy is 5x the service time, 90% is 10x, 95% is 20x. "CPU
  is only at 90%" means your p99 is already 10x — and the next 5% of traffic doubles it.
  → [03_capacity_scaling_tps.py:66](13_system_design_scenarios/03_capacity_scaling_tps.py#L66)
- **Q:** What caps horizontal scaling?
  **A:** Amdahl's Law. With 10% of the request behind one shared lock, 50 pods buy 8.5x, not 50x. So "what
  is the serial component?" comes before "add instances".
  → [03_capacity_scaling_tps.py:83](13_system_design_scenarios/03_capacity_scaling_tps.py#L83)
- **Q:** What do you do before buying capacity?
  **A:** Remove work, in payoff order: fix the N+1, cache the hot reads, move anything the user does not
  wait for onto a queue, batch the writes. On a typical profile that is 282ms -> 120ms for zero extra
  infrastructure — and it makes the product faster, not just survivable.
  → [03_capacity_scaling_tps.py:133](13_system_design_scenarios/03_capacity_scaling_tps.py#L133)
- **Q:** How do you size a connection pool, and what is the classic outage?
  **A:** Little's Law again: 600 TPS x 8ms of DB time = ~5 concurrent queries -> a pool of 7-12 per pod.
  Then multiply by **max** pod count and compare with `max_connections` — autoscaling the app tier into
  the database's connection limit is a real and common outage.
  → [03_capacity_scaling_tps.py:180](13_system_design_scenarios/03_capacity_scaling_tps.py#L180)
- **Q:** Why does a bounded queue beat an unbounded one under overload?
  **A:** With shedding, throughput stays at capacity and p99 stays ~110ms whatever you offer. Unbounded,
  110% load gives a 2.6s p99 and a queue of 1800 — you did the work for requests whose clients had already
  timed out. A fast 429 for 20% beats a slow failure for 100%.
  → [03_capacity_scaling_tps.py:215](13_system_design_scenarios/03_capacity_scaling_tps.py#L215)
- **Q:** What do you autoscale on?
  **A:** p95 latency or queue depth — **not** CPU, which is a lagging indicator for an I/O-bound service
  (you will be timing out at 40% CPU because you are waiting on a dependency).
  → [03_capacity_scaling_tps.py:52](13_system_design_scenarios/03_capacity_scaling_tps.py#L52)

**`04_ai_leverage_and_impact.py`**

- **Q:** You have an AI licence. How would you use it to improve and manage a project?
  **A:** Start from where the team loses hours (PR cycle time, escaped defects, MTTR), score candidates on
  **value x feasibility discounted by blast radius**, pilot ONE for a sprint with the baseline measured
  first, and keep it only if the number moved.
  → [04_ai_leverage_and_impact.py:31](13_system_design_scenarios/04_ai_leverage_and_impact.py#L31)
- **Q:** Which use cases do you start with, and which do you explicitly not?
  **A:** Internal and advisory first — a PR first-pass reviewer, test generation for the untested modules
  that cause the most incidents, an incident-triage copilot that cites its evidence. **Not** a
  customer-facing chatbot: highest value, worst risk, because a confidently wrong answer reaches a
  customer unreviewed.
  → [04_ai_leverage_and_impact.py:68](13_system_design_scenarios/04_ai_leverage_and_impact.py#L68)
- **Q:** What are the guardrails?
  **A:** Five categories: data boundary (tested PII redaction, a no-training contract, and check whether
  source code may leave at all), human in the loop (advisory, not authoritative), **verifiability** (an
  offline eval suite gating prompt changes in CI — a prompt is code), cost/latency (cache, smallest model
  that passes, timeout + fallback), and operations (kill switch, versioned prompts, traced calls).
  → [04_ai_leverage_and_impact.py:147](13_system_design_scenarios/04_ai_leverage_and_impact.py#L147)
- **Q:** How do you prove the pilot worked?
  **A:** Before/after with the measurement method and window, **including the cost row**. And if you did
  not measure a baseline, say so — that answer scores higher than an invented 40%.
  → [04_ai_leverage_and_impact.py:183](13_system_design_scenarios/04_ai_leverage_and_impact.py#L183)
- **Q:** What functionality have you built that significantly improved the customer experience?
  **A:** STAR, and the **Result is the only part being graded**: a number, the measurement window, and how
  you measured it ("p95 4.2s -> 0.9s, abandonment 23% -> 14% over 30 days against a control cohort"). Use
  "I" for what you decided, name a decision you deliberately did **not** make, and name what got worse.
  → [04_ai_leverage_and_impact.py:220](13_system_design_scenarios/04_ai_leverage_and_impact.py#L220)
- **Q:** Which metrics make such a story land?
  **A:** Latency of the flow the customer waits on, reliability, funnel abandonment (closest to money),
  support tickets on that complaint, and time-to-value. Two or three, each with how it was measured.
  → [04_ai_leverage_and_impact.py:183](13_system_design_scenarios/04_ai_leverage_and_impact.py#L183)

---

## Part 2 — Reference Topics (no runnable example in this repo)

These are covered in the source interview-prep material but have no corresponding hands-on
folder — either the tooling doesn't fit a lightweight local demo (Camel, Couchbase, Airflow,
Terraform/Databricks) or they're more about judgment/process than code (migration approach, team
leadership).

### Apache Camel

- **Q:** What is Apache Camel and what problem does it solve?
  **A:** An integration framework implementing Enterprise Integration Patterns (EIPs) — a routing
  and mediation engine connecting heterogeneous systems (REST, Kafka, FTP, DB, S3) through a
  consistent DSL, instead of bespoke glue code per system pair.
- **Q:** What are the core Camel concepts?
  **A:** Route (message flow definition, `from(...).to(...)`), Exchange (the message container),
  Processor (a transform step), Component (a connector like `kafka`/`http`/`jdbc`), Endpoint (a
  specific address on a component).
- **Q:** Which Enterprise Integration Patterns does Camel implement out of the box?
  **A:** Splitter (one message → many), Aggregator (many → one), Content-Based Router,
  Dead Letter Channel, Idempotent Consumer, Filter, Enrich.
- **Q:** Where does Camel fit relative to Kafka?
  **A:** Kafka is an event streaming platform (durable pub/sub); Camel is an integration
  framework (routing/transformation/protocol bridging). They complement each other — a Camel
  route often consumes from Kafka, transforms, and produces to another system.

### Couchbase

- **Q:** What is Couchbase, and when would you reach for it over Redis or a relational DB?
  **A:** A distributed multi-model NoSQL database combining key-value storage with a JSON
  document store, full SQL++ (N1QL), and full-text search. Choose it over Redis when you need
  JSON documents + SQL-like queries at scale, not just a pure cache; choose a relational DB when
  you need complex joins/ACID/reporting.
- **Q:** What does a basic CRUD flow look like?
  **A:** `collection.insert/get/upsert/remove(doc_id, ...)`, plus `mutate_in()` for an efficient
  partial (sub-document) update instead of rewriting the whole document.
- **Q:** How do you run a SQL-like query against JSON documents?
  **A:** N1QL — `SELECT ... FROM bucket WHERE ... GROUP BY ...`, executed via
  `cluster.query(...)`.
- **Q:** Why is Couchbase a good fit for session storage specifically?
  **A:** Native per-document TTL/expiry (`InsertOptions(expiry=timedelta(minutes=30))`) plus
  sub-millisecond key-value reads.

### Airflow DAGs & Tasks

- **Q:** What is a DAG, and what does Airflow actually manage for you?
  **A:** A Directed Acyclic Graph of tasks and dependencies; Airflow schedules runs, tracks state,
  handles retries, and provides a UI for monitoring — it does not execute your business logic
  itself, just orchestrates when/in-what-order it runs.
- **Q:** Classic DAG definition (operators) vs. the TaskFlow API — what's the actual difference?
  **A:** Classic style wires `PythonOperator` tasks together with `>>` and passes data via
  explicit `xcom_pull`/`xcom_push`; the TaskFlow API (`@task` decorators) lets plain Python
  function calls define both the logic AND the dependency graph, with XComs handled
  automatically.
- **Q:** What are XComs for, and what should you NOT put in one?
  **A:** Passing small values between tasks via Airflow's metadata DB — never large datasets;
  write large data to S3 and pass just the S3 key through XCom instead.
- **Q:** How do S3 sensors avoid wasting a worker slot while waiting?
  **A:** `S3KeySensor(mode="reschedule")` frees the worker slot between checks instead of
  blocking it for the entire wait.

### AWS Lambda & Orchestration (Airflow integration)

*(Note: streaming a large file inside a single Lambda invocation IS covered hands-on — see*
*[09 — AWS Lambda & Streaming Large Files](#09--aws-lambda--streaming-large-files)*
*above. This section is specifically about Lambda↔Airflow orchestration, which isn't.)*

- **Q:** What are the two patterns for combining Airflow and Lambda?
  **A:** (a) Airflow triggers Lambda via `LambdaInvokeFunctionOperator` — Airflow owns the
  schedule/dependencies, Lambda executes a lightweight task. (b) Lambda triggers an Airflow DAG
  run via the Airflow REST API (e.g. an S3 event fires a Lambda that POSTs to MWAA's `/aws_mwaa/cli`
  endpoint) — useful for event-driven pipelines Airflow itself isn't watching for.
- **Q:** What's the Lambda handler best-practice checklist?
  **A:** Initialize clients (boto3, DB connections) at module scope, not inside the handler;
  log the `context.aws_request_id` for traceability; re-raise on failure so Lambda's retry/DLQ
  mechanism engages instead of swallowing the error.

### Java/Scala → Python Migration

- **Q:** What's the recommended phased approach to migrating a Java/Scala application to Python?
  **A:** (1) Discovery — inventory modules/dependencies/SLAs, classify each as easy-to-port pure
  logic vs. framework-heavy vs. Spark/Scala vs. C-extension-dependent. (2) Architecture mapping —
  pick Python equivalents per component. (3) Incremental migration via the Strangler Fig pattern
  — replace one service/module at a time behind the same API contract, running both versions in
  parallel behind a proxy and shifting traffic gradually. Never a big-bang rewrite. (4) Watch-outs
  — add mypy since Python loses compile-time type checking; redesign the concurrency model since
  Java threads map 1:1 to OS threads while Python needs asyncio/multiprocessing; benchmark before
  and after each migrated component.
- **Q:** What are the typical component-by-component replacements?
  **A:** Spring Boot REST → FastAPI; Hibernate → SQLAlchemy (async); Spring Security JWT →
  `python-jose` + FastAPI dependencies; Spring Kafka → `confluent-kafka-python`; Scala Spark jobs
  → PySpark (often a near 1:1 translation); JUnit/Mockito → pytest + `unittest.mock`; Maven/Gradle
  → `pip` + `pyproject.toml` (Poetry).

### Terraform & Databricks

- **Q:** What does Terraform actually manage, and what are the non-negotiable state-management practices?
  **A:** Infrastructure as Code via declarative HCL, with `terraform plan`/`apply` and a tracked
  state file. Non-negotiables: remote state in S3 with DynamoDB locking (never local in a team),
  workspaces for environment isolation, `terraform import` to bring existing resources under
  management.
- **Q:** What is Databricks, and what does it add on top of raw Spark?
  **A:** A managed analytics platform built on Spark, adding managed clusters, multi-language
  notebooks, Delta Lake (ACID transactions on a data lake), MLflow, Delta Live Tables for
  streaming ETL, and Unity Catalog for governance.
- **Q:** How is a Databricks job commonly triggered from an orchestrator?
  **A:** `DatabricksRunNowOperator` from an Airflow DAG, passing `notebook_params` (e.g. a date
  partition) into the job.

### Microservices & Team Leadership

- **Q:** How would you design a Python microservices system end to end?
  **A:** Each service owns its own FastAPI app and its own datastore, communicating via REST
  (sync) and Kafka (async events); an API gateway handles auth/routing/rate limiting at the edge;
  services are discoverable via Kubernetes DNS; observability is Prometheus+Grafana metrics, ELK
  logs, and Jaeger tracing tied together with a shared trace-ID header.
- **Q:** How would you lead and guide a Python team, concretely?
  **A:** Coding standards enforced in CI (PEP 8, type hints, mypy); TDD with a coverage floor;
  structured code review checklist (error handling, tests, types, security, performance);
  Architecture Decision Records for key decisions; pair programming for mentoring; a clear
  branching strategy; feature flags for safe releases; blameless post-mortems.
- **Q:** How do you introduce TDD into an existing codebase that has none?
  **A:** Require tests-first only for NEW code; add tests for existing code opportunistically when
  you touch it (Boy Scout Rule); set a coverage floor and raise it incrementally each sprint; use
  characterization tests to document legacy behavior before refactoring it.

### Production monitoring & release-safety — mostly NOW COVERED by `13_system_design_scenarios/`

*(08 covers retry/backoff, circuit breakers, rate limiting and liveness/readiness hands-on;*
*`13_system_design_scenarios/01_zero_downtime_change.py` and `02_observability_pillars.py` now cover*
*canaries, blue/green, expand-migrate-contract, the three pillars and SLO burn-rate alerting as*
*runnable code — see also deep dives [27](deep_dive/27_zero_downtime_production_changes.md) and*
*[28](deep_dive/28_observability_distributed_systems.md). The entries below remain as the*
*crib-sheet summary.)*

- **Q:** What is an SLO, and what's an error budget used for in practice?
  **A:** An SLO is a target value for a measured SLI (e.g. "99.5% of requests < 200ms"); the
  error budget (`1 - SLO`) is a deployment-risk budget — a depleted budget means freeze feature
  work and focus on reliability, a healthy one means ship freely.
- **Q:** What's the difference between a canary deployment and a feature flag, and when do you use each?
  **A:** A canary routes a small % of ALL traffic to a new deployed version and auto-rolls-back on
  metric regressions (infrastructure-level control); a feature flag toggles a specific behavior
  per-user/percentage within one running version (application-level control) — they're often
  combined.
- **Q:** What's the safe sequence for a schema migration that adds a NOT NULL column to a huge table?
  **A:** Add the column nullable with a default → backfill existing rows → only then alter it to
  NOT NULL; create any new index `CONCURRENTLY` so it doesn't lock the table; never drop an old
  column in the same deploy as the code that stops using it.

### AI-first / LLM production concerns (beyond `10_genai_llm_patterns`)

*(10 covers prompt engineering, a RAG pipeline, and semantic caching hands-on — these are the*
*adjacent production-maturity topics with no runnable example.)*

- **Q:** What is AWS Bedrock, and what does it provide beyond raw model access?
  **A:** A managed multi-model API (Claude, Titan, Llama, Mistral, Cohere) with pay-per-token
  billing, VPC endpoints, IAM integration, managed RAG (Knowledge Bases), managed agent workflows
  (Bedrock Agents), and Guardrails for content filtering/PII redaction.
- **Q:** LangChain vs. LangGraph — when do you reach for each?
  **A:** LangChain for linear chains — RAG pipelines, document Q&A, single-pass tool use.
  LangGraph for stateful, graph-based multi-step agent workflows with conditional branching and
  memory across steps.
- **Q:** How do you build an LLM agent that calls real functions/tools?
  **A:** Define a tool schema (name, description, JSON input schema), send it alongside the
  conversation; when the model responds with a tool-use request, execute the real function and
  feed the result back as a `toolResult` message, looping until the model returns a final answer.
- **Q:** How do you evaluate an LLM-powered feature before shipping, instead of eyeballing outputs?
  **A:** Build a golden test set of (question, ground truth, retrieved context, generated answer)
  and score it automatically on faithfulness, answer relevance, and context recall (e.g. via
  `ragas`) — run this in CI and fail the build below a threshold.
