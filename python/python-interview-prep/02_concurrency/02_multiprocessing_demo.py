"""
multiprocessing: true CPU parallelism via ProcessPoolExecutor, and why the __main__ guard matters.
Run me: python 02_multiprocessing_demo.py
"""
import time
from concurrent.futures import ProcessPoolExecutor


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


def cpu_heavy(n):
    """A genuinely CPU-bound task -- no I/O, pure computation."""
    return sum(i * i for i in range(n))


def run_sequential(tasks):
    start = time.perf_counter()
    results = [cpu_heavy(n) for n in tasks]
    return results, time.perf_counter() - start


def run_parallel(tasks):
    start = time.perf_counter()
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(cpu_heavy, tasks))
    return results, time.perf_counter() - start


# The `if __name__ == "__main__":` guard below is NOT optional on Windows/macOS.
# ProcessPoolExecutor uses the "spawn" start method there, which re-imports this module in
# each child process. Without the guard, importing this file would recursively spawn more
# pools inside each child -- a fork bomb. Arguments/results are also pickled across the
# process boundary, so the target function must be defined at module level (not a lambda
# or a nested function).
if __name__ == "__main__":
    section("CPU-bound work: sequential vs multiprocessing")
    tasks = [8_000_000] * 4

    _, seq_time = run_sequential(tasks)
    print(f"sequential: {seq_time:.2f}s")

    _, par_time = run_parallel(tasks)
    print(f"parallel (ProcessPoolExecutor): {par_time:.2f}s")

    print(f"speedup: {seq_time / par_time:.2f}x")
    # EXPERIMENT: swap cpu_heavy's body for `time.sleep(1); return n` (an I/O-bound stand-in).
    # You'll see multiprocessing still helps (processes truly run in parallel), but it's massive
    # overkill for I/O work -- asyncio or threads would do the same job with far less overhead
    # (no process spawn, no pickling). That contrast is the whole point of this file.
