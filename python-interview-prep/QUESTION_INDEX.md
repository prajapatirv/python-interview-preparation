# Python Interview — Question Index

A single reference mapping interview questions to where they're demonstrated in this repo.
**Click any `→ file.py:LX` link** to jump straight to that line in the editor.

- **Part 1 — Hands-On Topics**: every question here has a runnable example in one of the 11
  numbered folders. Read the Q&A, then click through and run the file yourself.
- **Part 2 — Reference Topics**: covered in the source interview-prep material but with no
  runnable example in this repo (Apache Camel, Couchbase, Airflow, Terraform/Databricks, Java
  migration, monitoring/alerting, and more). No links — concept-only.

Use your editor's outline/symbol view (VS Code: `Ctrl+Shift+O`) to jump between the 21 sections
below, or `Ctrl+F` for a specific keyword.

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

### Production monitoring & release-safety (not covered by `08_scaling_production_resilience`)

*(08 covers retry/backoff, circuit breakers, rate limiting, and liveness/readiness hands-on —*
*these are the adjacent topics with no runnable example.)*

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
