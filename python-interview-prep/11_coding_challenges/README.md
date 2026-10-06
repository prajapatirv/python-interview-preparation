# 11 — Coding Challenges

The classic live-coding-round problems, each with multiple solutions and a complexity discussion
(interviewers want you to name the trade-off, not just produce a working answer). Pure stdlib.

## Files

| File | Problem |
|---|---|
| `01_anagram_grouping.py` | group words that are anagrams of each other — 3 approaches compared |
| `02_sliding_window_max.py` | max of every size-k window in an array, using a monotonic deque |
| `03_lru_cache.py` | O(1) get/put LRU cache — `OrderedDict` version and a from-scratch dict+doubly-linked-list version |
| `04_reverse_string.py` | in-place two-pointer string reversal, plus the immutable-string subtlety in Python |
| `05_retry_decorator.py` | a retry decorator with a retry limit, exponential backoff, jitter, a time budget, an async variant — and an **injectable `sleep`** so the tests are instant |
| `06_nested_dict_search.py` | search a keyword in a nested dict and return the key **and the path** — recursive, generator, substring, iterative (no `RecursionError`), and a prebuilt index |

## How to use this folder

Each file has the problem statement in its docstring, up to 3 alternative implementations, and a
`pytest`-discoverable test at the bottom (`test_*` functions) so you can verify correctness with:

```bash
pytest 11_coding_challenges -v
```

Try solving each problem yourself first — cover the reference implementation, write your own in
a scratch file, run it against the tests below, *then* compare approaches.

> **If you add a 7th file, add its filename to `python_files` in [`../pytest.ini`](../pytest.ini)**
> — these files are named by topic rather than `test_*.py`, so pytest only discovers the ones
> listed there.

## Deep dive

[26 — Three design-coding problems](../deep_dive/26_coding_design_problems.md) covers the retry
decorator, the nested-dict search and the LRU cache in full: the clarifying questions to ask first,
why each design decision is made, the complexity discussion, and the follow-ups (thread safety,
TTL, distributed invalidation, circuit breakers) that the interview actually turns on.
