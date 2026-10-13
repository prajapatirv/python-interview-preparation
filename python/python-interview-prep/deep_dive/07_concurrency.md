# Deep Dive 07 — Concurrency (threading / multiprocessing / asyncio)

> Runnable companions: [`02_concurrency/`](../02_concurrency/) — threading, multiprocessing, asyncio,
> sync primitives, and [`benchmark_concurrency_models.py`](../02_concurrency/benchmark_concurrency_models.py)
> Related deep dives: [Generators](04_generators_iterators.md) · [Scaling](12_scaling_applications.md) ·
> [Java bridge](21_java_to_python_bridge.md)

## What interviewers are actually probing

One central idea: **match the tool to the workload**. Threads for blocking I/O, processes for CPU
work, asyncio for high-concurrency I/O. Everything else — the GIL, race conditions, locks, executors,
event loops — is scaffolding around that decision.

Coming from Java, this is the area where the mental model genuinely differs. Java threads are real OS
threads that run Python's equivalent of bytecode **in parallel**; CPython's do not, because of the
GIL. If you answer "use threads for CPU-bound work" you've failed the round. Conversely, if you say
"Python can't do parallelism" you've also failed — `multiprocessing` and C extensions both can.

---

## Must-know points

- **GIL**: in CPython only **one thread executes Python bytecode at a time, per process**. It exists
  to make reference counting safe without per-object locks.
- **I/O-bound → `threading` or `asyncio`. CPU-bound → `multiprocessing` / `ProcessPoolExecutor`.**
- The GIL **is released** during blocking I/O and inside many C extensions (NumPy, `hashlib`,
  compression, `re` on large inputs), which is exactly why threads help I/O.
- **`concurrent.futures`** gives one API (`Executor`, `Future`, `map`, `submit`, `as_completed`) over
  both thread and process pools.
- **asyncio** is single-threaded cooperative multitasking. **Never block the event loop.**
- Python 3.13 ships an experimental **free-threaded (no-GIL) build** (PEP 703); 3.12 added
  **per-interpreter GIL** (PEP 684).

---

## Interview questions and full answers

### Q1. What is the GIL and how does it affect concurrency?

The **Global Interpreter Lock** is a mutex in CPython that guarantees only one thread executes Python
bytecode at a time within a process.

**Why it exists:** CPython manages memory with **reference counting**. Every `Py_INCREF`/`Py_DECREF`
would need to be atomic or individually locked in a free-threaded interpreter, which is both slow
and error-prone. One big lock made the interpreter simple and made single-threaded code — the
overwhelming majority — fast. It also let C extension authors write non-thread-safe code safely,
which is a large part of why the ecosystem grew so fast.

**The consequences, precisely:**

- **CPU-bound multithreading gives no speedup** — often a *slowdown*, because threads now contend for
  the GIL and pay context-switch costs on top of doing the same total work.
- **I/O-bound multithreading works well**, because a thread **releases the GIL** before a blocking
  syscall (socket read, file read, `time.sleep`) and reacquires it after. While thread A waits on the
  network, thread B runs.
- **C extensions can release the GIL** around long computations. NumPy, `hashlib`, `zlib`, `lxml` and
  parts of `re` all do, so a "CPU-bound" NumPy workload *can* parallelise across threads.

```python
import time, threading
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def cpu_bound(n):
    return sum(i * i for i in range(n))

N, TASKS = 5_000_000, 4

t = time.perf_counter()
[cpu_bound(N) for _ in range(TASKS)]
print(f"sequential:      {time.perf_counter() - t:.2f}s")

t = time.perf_counter()
with ThreadPoolExecutor(TASKS) as ex: list(ex.map(cpu_bound, [N] * TASKS))
print(f"threads:         {time.perf_counter() - t:.2f}s")   # same or WORSE

if __name__ == "__main__":
    t = time.perf_counter()
    with ProcessPoolExecutor(TASKS) as ex: list(ex.map(cpu_bound, [N] * TASKS))
    print(f"processes:       {time.perf_counter() - t:.2f}s")  # ~TASKS× faster
```

**GIL switching detail** worth knowing: since 3.2 the GIL uses a time-based switch interval
(`sys.getswitchinterval()`, default **5 ms**) rather than counting bytecodes. A CPU-bound thread is
asked to drop the GIL every 5 ms.

**The future:** PEP 703 added an optional **free-threaded build** in 3.13 (`python3.13t`), removing
the GIL at the cost of ~5–10% single-thread performance and requiring extensions to be rebuilt. PEP
684 gave each sub-interpreter its own GIL in 3.12. Mentioning these shows you're current — but state
clearly that the default CPython build you'll deploy still has the GIL.

> **Java contrast.** Java threads are OS threads with true parallelism and a memory model
> (`happens-before`, `volatile`, `synchronized`). Python's GIL means you get *concurrency* from
> threads but not *parallelism*. Java's virtual threads (21+) are the closest analogue to asyncio —
> cheap, many, I/O-focused — except they're preemptive at blocking points whereas Python's are
> cooperative at `await`.

---

### Q2. Concurrency vs parallelism?

**Concurrency** is *dealing with* many tasks by interleaving them — structure. One cook switching
between four dishes. **Parallelism** is *doing* many tasks literally simultaneously on multiple
cores — execution. Four cooks.

In Python: `threading` and `asyncio` give concurrency; `multiprocessing` gives parallelism. You can
have concurrency on a single core (and usually do); parallelism requires multiple cores.

The practical implication: concurrency helps when tasks **wait** (I/O), because waiting overlaps.
Parallelism helps when tasks **compute**, because computation is genuinely split.

---

### Q3. How do you choose between threading, multiprocessing and asyncio?

The decision tree that should come out automatically:

| Workload | Tool | Why |
|---|---|---|
| **CPU-bound** (parsing, image processing, crypto, heavy maths) | `multiprocessing` / `ProcessPoolExecutor` | Each process has its own GIL → true parallelism |
| **I/O-bound, blocking libraries** (`requests`, `psycopg2`, `boto3`, sync SQLAlchemy) | `threading` / `ThreadPoolExecutor` | GIL released during I/O; no rewrite needed |
| **I/O-bound, thousands of concurrent ops, async libraries available** (`httpx`, `asyncpg`, `aiokafka`) | `asyncio` | One thread, tiny per-task cost, scales to 10k+ |
| **CPU-bound but the hot loop is in C** (NumPy, Pandas) | threads *may* work | The C extension releases the GIL |
| **Mixed** | asyncio + `run_in_executor` / `to_thread` | Offload blocking or CPU work off the loop |

**Cost comparison, which is the other half of the answer:**

| | Memory per unit | Startup cost | Max practical count |
|---|---|---|---|
| Process | ~10–50 MB | ~50–100 ms (spawn) | ~#cores |
| Thread | ~8 MB stack (virtual) | ~50–100 µs | hundreds |
| Coroutine | ~1–3 KB | ~1 µs | 10,000s |

That table is why asyncio wins for 10,000 concurrent connections: 10,000 threads is 80 GB of stack
reservation and brutal context switching; 10,000 coroutines is a few tens of MB.

---

### Q4. Show `ThreadPoolExecutor` for concurrent HTTP calls.

`concurrent.futures` gives a uniform API. `map` preserves input order and re-raises on iteration;
`submit` + `as_completed` processes results **as they finish**, which is what you usually want.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch(url):
    time.sleep(1)                       # stands in for a blocking HTTP call
    return url, 200

urls = [f"https://api/{i}" for i in range(10)]

start = time.perf_counter()
with ThreadPoolExecutor(max_workers=10) as ex:
    future_to_url = {ex.submit(fetch, u): u for u in urls}
    for fut in as_completed(future_to_url):
        url = future_to_url[fut]
        try:
            print(fut.result())         # re-raises anything the worker raised
        except Exception as e:
            print(f"{url} failed: {e}")
print(f"{time.perf_counter() - start:.1f}s")    # ~1s, not 10s
```

**Points to volunteer:**

- **`fut.result()` re-raises worker exceptions.** If you never call `result()`, failures vanish
  silently — the single most common bug with executors (see Q11 of
  [Error handling](08_error_handling.md)).
- **The `with` block calls `shutdown(wait=True)`**, so it blocks until every task finishes.
- **Sizing:** for I/O-bound work, workers can far exceed core count — bounded by the downstream's
  tolerance and your connection pool, not your CPU. A common starting point is
  `min(32, os.cpu_count() + 4)`, which is the `ThreadPoolExecutor` default.
- **`ex.map` is lazy and ordered**; it re-raises the *first* exception when you reach that item,
  which can mask later ones.

---

### Q5. Show multiprocessing for CPU-bound work. Why the `__main__` guard?

```python
from concurrent.futures import ProcessPoolExecutor

def cpu_heavy(n):                       # MUST be top-level: it gets pickled
    return sum(i * i for i in range(n))

if __name__ == "__main__":              # MUST be guarded
    with ProcessPoolExecutor() as ex:
        print(list(ex.map(cpu_heavy, [10 ** 7] * 4)))
```

**Why the guard is mandatory on Windows and macOS:** the default start method there is **`spawn`**,
which starts a fresh interpreter and **re-imports your module** to rebuild the child's namespace.
Without `if __name__ == "__main__":`, that re-import re-executes the pool creation, which spawns more
children, which re-import again — an infinite fork bomb. (On Linux the default was `fork`, which
copies the parent's memory and doesn't re-import; **Python 3.14 changes the Linux default to
`forkserver`**, so the guard is now genuinely cross-platform necessary.)

**Consequences of process isolation, all of which come up as follow-ups:**

1. **Everything crossing the boundary is pickled.** Arguments, return values, exceptions. So worker
   functions must be **top-level** (lambdas and closures can't be pickled), and large arguments cost
   real serialisation time.
2. **No shared memory by default.** A global mutated in a child is invisible to the parent.
3. **Startup is expensive** (~50–100 ms per process). Pointless for short tasks — the overhead
   dominates. Chunk work so each task is substantial.
4. **`fork` and threads don't mix.** Forking a process that holds locks in other threads can deadlock
   the child. This is why `forkserver`/`spawn` are safer defaults.

```python
import multiprocessing as mp
mp.set_start_method("spawn")            # explicit and portable; call once, at startup
```

---

### Q6. What is a race condition? Show one and fix it.

A race condition is when the result depends on the **interleaving** of threads accessing shared
mutable state.

`counter += 1` looks atomic but is **read–modify–write**: `LOAD`, `ADD`, `STORE`. The GIL can be
released between those bytecodes, so two threads can both read `5`, both compute `6`, and both store
`6` — one increment lost.

```python
import threading, time

counter = 0
lock = threading.Lock()

def bare():
    global counter
    for _ in range(20_000):
        counter += 1                    # LOAD, ADD, STORE — three bytecodes

def racy():
    global counter
    for _ in range(20_000):
        tmp = counter                   # read
        time.sleep(0)                   # any function call is a possible GIL handoff
        counter = tmp + 1               # write — another thread may have written between

def safe():
    global counter
    for _ in range(20_000):
        with lock:                      # atomic section
            tmp = counter
            time.sleep(0)
            counter = tmp + 1
```

Running these with 4 threads (expected 80,000):

```
bare  counter += 1         : 80,000    lost 0
read / sleep(0) / write    : 20,067    lost 59,933      <- the race
read / sleep(0) / write + lock : 80,000  lost 0
```

**The subtlety worth knowing, and worth raising in an interview**: on **CPython 3.13+** a *bare*
`counter += 1` in a tight loop often loses **nothing**, because the interpreter only checks for a GIL
handoff at the **loop back-edge** — i.e. *after* the `STORE`. Many textbook demos of this race no
longer reproduce.

**That does not make it atomic or thread-safe.** It means the bug **hides** until the critical
section contains a function call — which all real code does. The moment there's a call between the
read and the write, the updates vanish. A race that only appears under production load is strictly
worse than one you can demonstrate.

**Say this explicitly:** the GIL does **not** make your code thread-safe. It protects the
*interpreter's* internal state, not *your* application invariants.

Three fixes, in order of preference:

1. **Don't share mutable state.** Give each thread its own accumulator and combine at the end, or
   pass work through a `queue.Queue`. This is always the best answer.
2. **`threading.Lock`** around the critical section. Keep it short — never hold a lock across I/O.
3. **Use an already-atomic structure** — `queue.Queue`, or operations that complete in a single
   bytecode (`list.append` is atomic; `list[i] += 1` is not).

---

### Q7. Name the threading synchronisation primitives.

| Primitive | What it does | When |
|---|---|---|
| `Lock` | Mutual exclusion; one holder | Protect a critical section |
| `RLock` | Re-entrant — the *same thread* can acquire repeatedly | Recursive code, or a locked method calling another locked method |
| `Semaphore(n)` | Allow up to n concurrent holders | Cap concurrent DB connections / API calls |
| `BoundedSemaphore(n)` | As above, but raises on over-release | Catches release bugs |
| `Event` | One-shot broadcast flag; `wait()` / `set()` | Shutdown signal, "ready" notification |
| `Condition` | Wait for a state change with a predicate | Producer/consumer without a queue |
| `Barrier(n)` | Block until n threads arrive | Phased/lock-step computation |
| `queue.Queue` | Thread-safe FIFO with blocking + `task_done()` | **The default choice** for producer/consumer |
| `threading.local()` | Per-thread storage | Per-thread DB connection or request context |

```python
import threading

# Semaphore: at most 5 concurrent calls to a fragile downstream
sem = threading.Semaphore(5)
def call_api(x):
    with sem:
        return requests.get(f"/api/{x}")

# Event: cooperative shutdown
shutdown = threading.Event()
def worker():
    while not shutdown.is_set():
        do_work()
        shutdown.wait(timeout=1)        # sleeps, but wakes instantly on set()
shutdown.set()
```

`shutdown.wait(timeout=1)` instead of `time.sleep(1)` is the detail that marks experience — the
thread reacts to shutdown immediately instead of after a full second.

**`RLock` vs `Lock`** is a favourite follow-up: a plain `Lock` re-acquired by the same thread
**deadlocks instantly**. `RLock` keeps an owner and a recursion count.

---

### Q8. What is a deadlock and how do you avoid it?

Two or more threads each hold a lock the other needs, and both wait forever.

```python
lock_a, lock_b = threading.Lock(), threading.Lock()

def t1():
    with lock_a:
        time.sleep(0.1)
        with lock_b: ...        # waits for t2's lock_b

def t2():
    with lock_b:
        time.sleep(0.1)
        with lock_a: ...        # waits for t1's lock_a  -> deadlock
```

The four Coffman conditions must all hold: mutual exclusion, hold-and-wait, no preemption, circular
wait. Break any one:

1. **Consistent global lock ordering** — always acquire in the same order (e.g. sorted by `id()` or
   by account number). This breaks *circular wait* and is the most practical fix.
2. **Timeouts** — `lock.acquire(timeout=5)`; on failure, release everything and retry. Turns a
   deadlock into a recoverable error.
3. **Hold locks briefly.** Never across I/O or a network call.
4. **`RLock`** for genuinely re-entrant code paths.
5. **Avoid shared locks entirely** — message passing with `queue.Queue` has no locks to deadlock on.

```python
def transfer(a, b, amount):
    first, second = sorted((a, b), key=id)      # consistent order, always
    with first.lock, second.lock:
        a.balance -= amount
        b.balance += amount
```

---

### Q9. How does asyncio work? Explain event loop, coroutine, task.

- A **coroutine** is what `async def` produces. Calling it runs nothing — it returns a coroutine
  object that must be awaited or scheduled. It can **suspend at `await`**.
- The **event loop** runs in a single thread. It keeps a ready queue of callbacks and a selector
  (`epoll`/`kqueue`/IOCP) of pending I/O. When a coroutine `await`s something not yet ready, it
  yields control; the loop runs the next ready coroutine; when the OS signals the I/O is done, the
  loop resumes the original.
- A **Task** wraps a coroutine and schedules it on the loop so it runs **concurrently** with others.
  `asyncio.gather(...)` or `TaskGroup` (3.11+) runs many at once.

```python
import asyncio

async def fetch(i):
    await asyncio.sleep(1)            # non-blocking: yields to the loop
    return i

async def main():
    # Sequential — 100 seconds. Each await completes before the next starts.
    # results = [await fetch(i) for i in range(100)]

    # Concurrent — ~1 second.
    async with asyncio.TaskGroup() as tg:              # 3.11+
        tasks = [tg.create_task(fetch(i)) for i in range(100)]
    print(sum(t.result() for t in tasks))

asyncio.run(main())
```

**The `await` vs task distinction is the most common misunderstanding.** `await coro()` runs it *to
completion right now* — it's sequential. Concurrency requires `gather`, `TaskGroup` or
`create_task`.

```python
await a(); await b()                       # sequential: 2s
await asyncio.gather(a(), b())             # concurrent: 1s
```

**`TaskGroup` vs `gather`** (3.11+): `TaskGroup` is **structured concurrency** — if one task fails,
the rest are cancelled and errors surface as an `ExceptionGroup`; no task can outlive the block.
`gather(..., return_exceptions=True)` instead collects exceptions as results. Prefer `TaskGroup` for
new code; it makes orphaned tasks impossible.

> **Java contrast.** The event loop is Netty's; coroutines are closest to virtual threads (21+) or
> Project Reactor's `Mono`/`Flux`. The crucial difference is **cooperative vs preemptive**: a Java
> virtual thread yields automatically at any blocking call, whereas a Python coroutine yields *only*
> at `await`. One blocking call in Python freezes everything.

---

### Q10. What happens if you call `time.sleep()` inside async code?

**It blocks the entire event loop thread**, so every other coroutine freezes — including health
checks, other requests, and background heartbeats. In a FastAPI service, one such call in one
endpoint stalls every concurrent request on that worker.

```python
import asyncio, time

async def bad():
    time.sleep(2)                  # BLOCKS the loop for 2 full seconds
async def good():
    await asyncio.sleep(2)         # yields; the loop runs other coroutines
```

**The fixes, in order:**

1. **Use the async equivalent**: `asyncio.sleep`, `httpx.AsyncClient`, `asyncpg`, `aiokafka`,
   `aiobotocore`, `redis.asyncio`.
2. **Offload to a thread** when no async library exists:

```python
import asyncio, time

def legacy_blocking():
    time.sleep(2)
    return "done"

async def main():
    result = await asyncio.to_thread(legacy_blocking)    # 3.9+, runs in the default executor
    print(result)

asyncio.run(main())
```

3. **Offload CPU work to a process pool**, since a thread wouldn't help:

```python
loop = asyncio.get_running_loop()
with ProcessPoolExecutor() as pool:
    result = await loop.run_in_executor(pool, cpu_heavy, 10_000_000)
```

**How to catch this in practice:** run with `asyncio.run(main(), debug=True)` or set
`PYTHONASYNCIODEBUG=1`. The loop then logs any callback taking longer than 100 ms
("Executing <Task ...> took 2.001 seconds"). That's the answer to "how would you find it?" — it's
the single most useful asyncio debugging switch.

**FastAPI-specific consequence:** if your endpoint is `def` (not `async def`), FastAPI runs it in a
thread pool and blocking is safe. If it's `async def`, *you* own the loop and blocking is fatal. The
worst case is `async def` calling `requests.get()`. See
[Web frameworks Q5](10_web_frameworks.md#q5-when-should-an-endpoint-be-async-def-vs-plain-def).

---

### Q11. How do you limit concurrency in asyncio?

With `asyncio.Semaphore`. Launching 10,000 tasks against an API that tolerates 10 concurrent requests
will get you rate-limited or will exhaust file descriptors.

```python
import asyncio

sem = asyncio.Semaphore(10)

async def call(i):
    async with sem:                  # at most 10 inside this block at once
        await asyncio.sleep(0.5)
        return i

async def main():
    return await asyncio.gather(*(call(i) for i in range(100)))

asyncio.run(main())                  # ~5s: 100 tasks, 10 at a time
```

Note **all 100 tasks are created immediately** — they just queue on the semaphore. If creating the
tasks itself is expensive (each holds a large payload), use a **bounded queue with a fixed worker
pool** instead, which also gives you backpressure:

```python
async def worker(q):
    while (item := await q.get()) is not None:
        await handle(item)
        q.task_done()

async def main():
    q = asyncio.Queue(maxsize=100)                    # backpressure: put() blocks when full
    workers = [asyncio.create_task(worker(q)) for _ in range(10)]
    async for item in source():
        await q.put(item)
    for _ in workers: await q.put(None)
    await asyncio.gather(*workers)
```

Use `asyncio.Semaphore`, not `threading.Semaphore`, inside async code — the threading one blocks the
loop.

---

### Q12. How do you share data between processes?

Processes don't share memory. The options, cheapest to most expensive:

| Mechanism | Notes |
|---|---|
| `multiprocessing.Queue` / `Pipe` | Message passing; everything pickled. The default choice. |
| `Value` / `Array` | Shared **ctypes** memory with an optional lock. Only primitives. |
| `multiprocessing.shared_memory` (3.8+) | Raw zero-copy buffer. Excellent with NumPy — share a 1 GB array with no copy. |
| `Manager()` | Proxy objects (`dict`, `list`) — convenient but **slow**: every access is an IPC round-trip. |
| External store | Redis, a DB, Kafka. The right answer once you have more than one machine. |

```python
from multiprocessing import Process, Value, Queue
from multiprocessing import shared_memory
import numpy as np

# 1. Shared primitive with a lock
counter = Value("i", 0)
def inc(c):
    with c.get_lock():              # required — Value is not atomic by itself
        c.value += 1

# 2. Zero-copy NumPy array across processes
arr = np.arange(1_000_000, dtype=np.int64)
shm = shared_memory.SharedMemory(create=True, size=arr.nbytes)
shared = np.ndarray(arr.shape, dtype=arr.dtype, buffer=shm.buf)
shared[:] = arr[:]                  # copied ONCE; children attach by shm.name
# child: shared_memory.SharedMemory(name=shm.name)
shm.close(); shm.unlink()           # always unlink, or you leak /dev/shm
```

**The trap to mention:** `Value` is not atomic. `c.value += 1` is read-modify-write across processes
too — you need `get_lock()`.

---

### Q13. How do you handle timeouts and cancellation in asyncio?

Use `asyncio.timeout(seconds)` (3.11+) or `asyncio.wait_for`. On timeout, the inner task is
**cancelled** by raising `CancelledError` at its current `await` point.

```python
import asyncio

async def slow():
    await asyncio.sleep(5)

async def main():
    try:
        async with asyncio.timeout(1):     # 3.11+; a context manager
            await slow()
    except TimeoutError:
        print("timed out")

    try:
        await asyncio.wait_for(slow(), timeout=1)   # older equivalent
    except asyncio.TimeoutError:
        print("timed out")

asyncio.run(main())
```

**The cancellation rules that matter:**

1. **Let `CancelledError` propagate.** Do cleanup in `finally`, don't swallow it. Swallowing breaks
   shutdown and timeout — the task refuses to die.

```python
async def worker():
    try:
        await long_operation()
    except asyncio.CancelledError:
        await rollback()            # cleanup
        raise                       # ALWAYS re-raise
    finally:
        await release_resources()   # runs on cancel too
```

2. **`CancelledError` inherits from `BaseException`** (since 3.8), *not* `Exception` — so a blanket
   `except Exception:` won't accidentally eat it. That change was made for exactly this reason.
3. **Cancellation is cooperative**: it only takes effect at an `await`. A coroutine in a tight CPU
   loop with no awaits cannot be cancelled.
4. **Shield critical sections** with `asyncio.shield(coro)` when a piece must complete even if the
   caller times out (e.g. committing a Kafka offset).

---

### Q14. What is the producer-consumer pattern? Implement it with `asyncio.Queue`.

Producers put work on a queue, consumers take it off. This **decouples their rates** and — with
`maxsize` — gives **backpressure**: when consumers fall behind, `put()` blocks and the producer
naturally slows down instead of exhausting memory.

```python
import asyncio

async def producer(q, n):
    for i in range(n):
        await q.put(i)              # blocks when the queue is full -> backpressure
    await q.put(None)               # poison pill: signals end-of-stream

async def consumer(q):
    while (item := await q.get()) is not None:
        print("processed", item)
        q.task_done()

async def main():
    q = asyncio.Queue(maxsize=2)    # small on purpose, to demonstrate backpressure
    await asyncio.gather(producer(q, 5), consumer(q))

asyncio.run(main())
```

**With multiple consumers**, send one poison pill per consumer, or use `q.join()` + cancellation:

```python
async def main():
    q = asyncio.Queue(maxsize=100)
    consumers = [asyncio.create_task(consumer(q)) for _ in range(5)]
    await producer(q, 1000)
    await q.join()                            # wait until every task_done() has fired
    for c in consumers: c.cancel()            # then shut the workers down
    await asyncio.gather(*consumers, return_exceptions=True)
```

**Why this matters beyond the exercise:** it is the shape of a Kafka consumer feeding a worker pool
(see [Kafka pipelines](14_kafka_pipelines_delivery_semantics.md)), and the bounded queue is exactly
the **load-shedding/backpressure** mechanism described in
[Scaling](12_scaling_applications.md#q10-what-is-load-shedding-and-backpressure). An unbounded queue
is a memory leak with a scheduling problem attached.

---

## Worked example — benchmark: sequential vs threads vs asyncio

Run this. The numbers make the theory concrete, and the *shape* of the result is the answer to
"which should I use?"

```python
import asyncio, time
from concurrent.futures import ThreadPoolExecutor

def io_task(_):        time.sleep(0.2)          # blocking I/O
async def aio_task(_): await asyncio.sleep(0.2) # non-blocking I/O

N = 20

t = time.perf_counter()
[io_task(i) for i in range(N)]
print("sequential", round(time.perf_counter() - t, 2))     # ~4.0s

t = time.perf_counter()
with ThreadPoolExecutor(N) as ex:
    list(ex.map(io_task, range(N)))
print("threads   ", round(time.perf_counter() - t, 2))     # ~0.2s

async def main():
    await asyncio.gather(*(aio_task(i) for i in range(N)))

t = time.perf_counter()
asyncio.run(main())
print("asyncio   ", round(time.perf_counter() - t, 2))     # ~0.2s
```

**Threads and asyncio tie at N=20** — so why choose asyncio? Re-run at **N=5,000**. Threads will
struggle or fail (memory, context switching, OS limits); asyncio stays flat at ~0.2 s. That scaling
difference, not the small-N result, is the reason.

Then swap `io_task` for a CPU-bound function and re-run: threads become *slower* than sequential, and
only `ProcessPoolExecutor` helps. Running that comparison yourself is worth more than memorising this
page — see
[`02_concurrency/benchmark_concurrency_models.py`](../02_concurrency/benchmark_concurrency_models.py).

---

## Hands-on drills

1. Run the Q1 benchmark with `cpu_bound`. Confirm threads are no faster (probably slower) and
   processes scale with cores. Then replace the body with a NumPy operation and re-run — explain why
   threads suddenly help.
2. Run the race-condition demo **ten times**. Note a different wrong answer each run. Then set
   `sys.setswitchinterval(0.000001)` and watch it get dramatically worse.
3. Build the two-lock deadlock, watch it hang, then fix it with consistent ordering. Then fix it
   again with `acquire(timeout=...)` and compare the failure modes.
4. Write an asyncio program with `time.sleep(2)` inside a coroutine. Run it with
   `asyncio.run(main(), debug=True)` and find the "took 2.001 seconds" warning.
5. Write 100 tasks hitting a fake API. Add an `asyncio.Semaphore(10)` and measure the wall-clock
   change. Then remove it and cap concurrency with a bounded queue + 10 workers instead.
6. Use `TaskGroup` with one task that raises. Observe that siblings are cancelled and you get an
   `ExceptionGroup`. Compare against `gather(..., return_exceptions=True)`.
7. Write a coroutine that swallows `CancelledError`. Try to `wait_for` it with a 1 s timeout and see
   that it won't die. Fix it by re-raising.
8. Share a 100 MB NumPy array with a child process via `shared_memory` and via a `Queue`. Time both.

---

## The 60-second spoken answer

> "CPython's GIL means one thread executes bytecode at a time per process — it's there to make
> reference counting safe. So threads don't speed up CPU-bound Python, but they do help I/O because
> the GIL is released around blocking syscalls and inside C extensions like NumPy. My rule is:
> CPU-bound goes to `ProcessPoolExecutor`, blocking I/O with sync libraries goes to
> `ThreadPoolExecutor`, and high-concurrency I/O with async libraries goes to asyncio — a coroutine
> is a couple of KB against roughly 8 MB of stack for a thread, so asyncio is what scales to ten
> thousand connections. asyncio is single-threaded and cooperative, which means one blocking call
> freezes everything; I use `asyncio.to_thread` for legacy blocking code and `run_in_executor` with a
> process pool for CPU work, and I turn on debug mode to catch slow callbacks. The GIL doesn't make
> my code thread-safe — `counter += 1` is still read-modify-write — so I prefer passing work through
> a queue over sharing state with locks, and when I must lock I acquire in a consistent order and
> never hold one across I/O. For structured concurrency I use `TaskGroup` over `gather`, and I always
> let `CancelledError` propagate after cleaning up in `finally`."
