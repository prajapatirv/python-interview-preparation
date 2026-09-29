# 02 — Concurrency (threading / multiprocessing / asyncio)

Run each file with `py <file>.py` (Windows) or `python3 <file>.py`. Concurrency bugs are timing-
dependent — run the race-condition demo several times, not once, to actually see it fail.

## Crib sheet

- **GIL**: CPython allows only one thread to execute Python bytecode at a time. Threads still help
  I/O-bound work (the GIL is released during blocking I/O); they do **not** speed up CPU-bound work.
- **Concurrency vs parallelism**: concurrency = interleaving tasks (one cook switching dishes);
  parallelism = literally simultaneous (many cooks). Threads/asyncio give concurrency;
  multiprocessing gives parallelism.
- **Choosing a tool**:
  - CPU-bound (image processing, heavy computation) → `multiprocessing` / `ProcessPoolExecutor`
  - I/O-bound, moderate task count, blocking libraries → `threading` / `ThreadPoolExecutor`
  - I/O-bound, thousands of connections, async-capable libraries → `asyncio`
- **Race condition**: `counter += 1` is read-modify-write, not atomic. Fix with `threading.Lock`.
- **Deadlock**: two threads each hold a lock the other needs. Fix: consistent lock ordering, lock
  timeouts, or avoid shared locks entirely (message passing via `queue.Queue`).
- **asyncio**: single-threaded, cooperative. `await` is the only place control can switch to
  another coroutine. Calling a blocking function (`time.sleep`, `requests.get`) inside `async def`
  freezes the *entire* event loop — use `asyncio.to_thread(...)` to offload it.
- **Never mutate shared state across processes** — each process has its own memory; use
  `multiprocessing.Queue`, `Pipe`, `shared_memory`, or an external store instead.

## Files

| File | Topic |
|---|---|
| `01_threading_demo.py` | race condition without/with a `Lock`, `ThreadPoolExecutor` for concurrent I/O |
| `02_multiprocessing_demo.py` | `ProcessPoolExecutor` for CPU-bound work, the `__main__` guard |
| `03_asyncio_demo.py` | coroutines, `gather`, `Semaphore`, timeout/cancellation, producer/consumer `asyncio.Queue` |
| `04_sync_primitives.py` | `Event`, `Semaphore`, deadlock reproduced then fixed |
| `benchmark_concurrency_models.py` | same I/O-bound task timed sequentially vs threads vs asyncio |

> **Deep dive**: [07 — Concurrency](../deep_dive/07_concurrency.md) — GIL internals, the cost table
> (process vs thread vs coroutine), `TaskGroup` vs `gather`, cancellation rules, and why a bare
> `counter += 1` no longer reproduces the race on CPython 3.13+ (but is still unsafe).
