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


def bare_increment(n_threads=4, n_iters=20_000):
    """`counter += 1` with nothing else in the loop body."""
    counter = 0

    def work():
        nonlocal counter
        for _ in range(n_iters):
            counter += 1  # LOAD, ADD, STORE -- three separate bytecodes
    threads = [threading.Thread(target=work) for _ in range(n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return counter


def racy_increment(n_threads=4, n_iters=20_000):
    """The same read-modify-write, but with a call inside the critical section."""
    counter = 0

    def work():
        nonlocal counter
        for _ in range(n_iters):
            tmp = counter      # read
            time.sleep(0)      # ANY function call is a possible GIL handoff point
            counter = tmp + 1  # write -- another thread may have written in between
    threads = [threading.Thread(target=work) for _ in range(n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return counter


expected = 4 * 20_000
bare = bare_increment()
racy = racy_increment()
print(f"bare `counter += 1`          : {bare:>7,} / {expected:,}  lost {expected - bare:,}")
print(f"read / sleep(0) / write      : {racy:>7,} / {expected:,}  lost {expected - racy:,}")
print("""
Why the first line often loses NOTHING on CPython 3.13+: the interpreter only checks
for a GIL handoff at the loop back-edge -- i.e. AFTER the store -- so a bare += in a
tight loop tends not to interleave. That does NOT make it atomic or thread-safe; it
means the bug HIDES until the critical section contains a function call, which all
real code does. The second line adds exactly that, and the updates disappear.""")
# EXPERIMENT: rerun this file a few times -- the second number differs every run.
# EXPERIMENT: swap time.sleep(0) for a call to any trivial helper and the race persists.
#             It is the CALL that opens the window, not the sleep.


# ---------------------------------------------------------------- fixed with a Lock
section("fixed with threading.Lock — always exactly correct")


def safe_increment(n_threads=4, n_iters=20_000):
    counter = 0
    lock = threading.Lock()

    def work():
        nonlocal counter
        for _ in range(n_iters):
            with lock:             # only one thread inside this block at a time
                tmp = counter      # the SAME read/yield/write as racy_increment above
                time.sleep(0)      # the handoff can still happen -- but no one else
                counter = tmp + 1  # can be inside the lock, so nothing is lost
    threads = [threading.Thread(target=work) for _ in range(n_threads)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return counter


print("safe_increment() ->", f"{safe_increment():,}", "(always exactly 80,000)")
print("Same critical section as the racy version -- the Lock is the only difference.")


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
