"""
Same I/O-bound task, three ways: sequential, ThreadPoolExecutor, asyncio.
This is the benchmark every "why is asyncio fast" interview answer should be backed by.
Run me: python benchmark_concurrency_models.py
"""
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

N = 20
DELAY = 0.2  # each "request" takes 200ms


def io_task(_):
    time.sleep(DELAY)


async def aio_task(_):
    await asyncio.sleep(DELAY)


def run_sequential():
    start = time.perf_counter()
    for i in range(N):
        io_task(i)
    return time.perf_counter() - start


def run_threads():
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=N) as pool:
        list(pool.map(io_task, range(N)))
    return time.perf_counter() - start


async def run_asyncio_async():
    start = time.perf_counter()
    await asyncio.gather(*(aio_task(i) for i in range(N)))
    return time.perf_counter() - start


def run_asyncio():
    return asyncio.run(run_asyncio_async())


if __name__ == "__main__":
    print(f"{N} tasks x {DELAY}s blocking I/O each\n")

    seq = run_sequential()
    print(f"sequential : {seq:5.2f}s  (expected ~{N * DELAY:.1f}s)")

    thr = run_threads()
    print(f"threads    : {thr:5.2f}s  (expected ~{DELAY:.1f}s)")

    aio = run_asyncio()
    print(f"asyncio    : {aio:5.2f}s  (expected ~{DELAY:.1f}s)")

    print(f"\nthreads speedup over sequential : {seq / thr:5.1f}x")
    print(f"asyncio speedup over sequential : {seq / aio:5.1f}x")
    print(
        "\nThreads and asyncio land at roughly the same wall-clock time here because this "
        "workload is pure I/O wait. The real-world difference shows up at scale: asyncio's "
        "~1KB-per-coroutine footprint lets you run tens of thousands of concurrent operations "
        "on one thread, where a thread pool that size would exhaust OS resources "
        "(threads cost ~8MB of stack each)."
    )

# EXPERIMENT: bump N to 500. Threads still work but creating 500 OS threads is expensive and
# resource-heavy; asyncio handles it without breaking a sweat. That gap is the answer to
# "why choose asyncio over threading for I/O-bound work at scale."
