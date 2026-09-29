# Exercises — 01 Python Core

Solve each of these in a scratch file before looking at the referenced example file. That's the
point: struggling for 5-10 minutes first is what makes the concept stick.

1. **Data structures.** Write `group_anagrams(words: list[str]) -> list[list[str]]` using a
   `defaultdict` keyed by `tuple(sorted(word))`. Then explain why that key works but
   `sorted(word)` alone (a list) would not. → check `11_coding_challenges/01_anagram_grouping.py`.

2. **Comprehensions.** Given `orders = [{"id": 1, "items": [...]}, ...]` (nested dicts/lists),
   write a single nested comprehension that flattens every line item with qty > 0 into
   `(order_id, sku, qty)` tuples. → check `02_comprehensions.py`.

3. **Decorators.** Write `@memoize` from scratch (no `functools.lru_cache`) that caches results
   in a dict keyed by `(args, tuple(sorted(kwargs.items())))`. Then explain one caveat: what
   breaks if an argument is unhashable? → check `03_decorators.py`.

4. **Generators.** Write a generator `paginate(fetch_page, page_size)` that lazily yields items
   across pages, stopping when a page comes back empty, without loading everything into memory
   at once. → check `04_generators_iterators.py`.

5. **Context managers.** Write a `@contextmanager`-based `suppress_and_log(*exc_types)` that logs
   a warning and swallows only the given exception types, re-raising everything else.
   → check `05_context_managers.py`.

6. **Descriptors.** Write a `TypedField` descriptor that validates a value's type on `__set__`
   and raises `TypeError` with a clear message otherwise. Use it on two attributes of one class.
   → check `06_descriptors_metaclasses.py`.

7. **OOP/MRO.** Build a 4-class diamond (`D(B, C)`, `B(A)`, `C(A)`) where each `hello()` prints
   its own name then calls `super().hello()`. Predict the print order on paper *before* running
   it. → check `07_oop_inheritance_mro.py`.

8. **Exceptions.** Design a 3-level exception hierarchy for a payments service
   (`PaymentError` → `InsufficientFundsError`, `PaymentError` → `GatewayTimeoutError`), then write
   a handler that retries only `GatewayTimeoutError` up to 3 times and immediately surfaces
   everything else. → check `08_exception_handling.py`.

9. **Memory.** Create two classes identical except one uses `__slots__`. Instantiate 200,000 of
   each and compare total memory with `tracemalloc`. Report the percentage saved.
   → check `09_memory_management.py`.

10. **Integration exercise.** Combine #3 (memoize) and #6 (TypedField): build a small
    `Config` class whose fields are validated descriptors, with a `@classmethod` factory
    `from_dict` that's decorated with your own `@memoize` so repeated calls with the same dict
    don't rebuild the object. This mirrors the `get_settings()` pattern used in
    `05_web_apis_fastapi/app/config.py`.
