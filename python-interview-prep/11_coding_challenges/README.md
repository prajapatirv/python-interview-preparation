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

## How to use this folder

Each file has the problem statement in its docstring, up to 3 alternative implementations, and a
`pytest`-discoverable test at the bottom (`test_*` functions) so you can verify correctness with:

```bash
pytest 11_coding_challenges -v
```

Try solving each problem yourself first — cover the reference implementation, write your own in
a scratch file, run it against the tests below, *then* compare approaches.
