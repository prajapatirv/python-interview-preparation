"""
threading: race conditions, Lock, and ThreadPoolExecutor for concurrent I/O.
Run me: python 01_threading_demo.py
"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- race condition
section("race condition: counter += 1 is NOT atomic")


def racy_increment(n_threads=4, n_iters=100_000):
    counter = 0

    def work():
        nonlocal counter
        for _ in range(n_iters):
            counter += 1  # read, modify, write -- another thread can interleave here
    threads = [threading.Thread(target=work) for _ in range(n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return counter


result = racy_increment()
expected = 4 * 100_000
print(f"expected {expected}, got {result} (mismatch means the race actually happened)")
# EXPERIMENT: rerun this file a few times -- the result varies and is often < expected.
# On some fast machines/short loops it may occasionally get lucky; increase n_iters to
# make the race more reliably visible.


# ---------------------------------------------------------------- fixed with a Lock
section("fixed with threading.Lock — always exactly correct")


def safe_increment(n_threads=4, n_iters=100_000):
    counter = 0
    lock = threading.Lock()

    def work():
        nonlocal counter
        for _ in range(n_iters):
            with lock:  # only one thread inside this block at a time
                counter += 1
    threads = [threading.Thread(target=work) for _ in range(n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return counter


print("safe_increment() ->", safe_increment(), "(always exactly 400000)")


# ---------------------------------------------------------------- ThreadPoolExecutor for I/O
section("ThreadPoolExecutor: 10 'network calls' of 0.3s run in ~0.3s total, not 3s")


def fetch(url):
    time.sleep(0.3)  # simulate blocking I/O (a real HTTP call, DB query, etc.)
    return url, 200


urls = [f"https://api.example/{i}" for i in range(10)]

start = time.perf_counter()
with ThreadPoolExecutor(max_workers=10) as pool:
    futures = [pool.submit(fetch, u) for u in urls]
    for f in as_completed(futures):
        pass  # in real code you'd use f.result() here
elapsed = time.perf_counter() - start
print(f"10 x 0.3s blocking calls via thread pool took {elapsed:.2f}s (not ~3.0s)")

# EXPERIMENT: change max_workers=10 to max_workers=2 and watch elapsed jump towards ~1.5s --
# only 2 requests can be "in flight" at a time now.
