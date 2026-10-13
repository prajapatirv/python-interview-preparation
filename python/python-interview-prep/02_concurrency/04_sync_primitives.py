"""
Synchronization primitives: Event, Semaphore, and reproducing + fixing a deadlock.
Run me: python 04_sync_primitives.py
"""
import threading
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- Event: one-shot signal
section("threading.Event — one thread signals, others wait for it")
ready = threading.Event()
results = []


def consumer():
    ready.wait()  # blocks here until .set() is called
    results.append("consumer saw the signal")


def producer():
    time.sleep(0.2)
    results.append("producer about to signal")
    ready.set()


t1, t2 = threading.Thread(target=consumer), threading.Thread(target=producer)
t1.start(); t2.start()
t1.join(); t2.join()
print(results)


# ---------------------------------------------------------------- Semaphore: cap concurrent access
section("threading.Semaphore — limit concurrent access to a resource (e.g. max 3 DB connections)")
db_semaphore = threading.Semaphore(3)
active = {"now": 0, "max_seen": 0}
lock = threading.Lock()


def db_query(i):
    with db_semaphore:
        with lock:
            active["now"] += 1
            active["max_seen"] = max(active["max_seen"], active["now"])
        time.sleep(0.05)
        with lock:
            active["now"] -= 1


threads = [threading.Thread(target=db_query, args=(i,)) for i in range(10)]
[t.start() for t in threads]
[t.join() for t in threads]
print(f"max concurrent 'connections' observed: {active['max_seen']} (should be <= 3)")


# ---------------------------------------------------------------- deadlock: reproduce it
section("deadlock: two threads acquire two locks in OPPOSITE order")
lock_a = threading.Lock()
lock_b = threading.Lock()


def worker_1():
    with lock_a:
        time.sleep(0.1)  # widen the window so the deadlock reliably happens
        acquired = lock_b.acquire(timeout=1)  # use a timeout so the demo doesn't hang forever
        if acquired:
            lock_b.release()
        return acquired


def worker_2():
    with lock_b:
        time.sleep(0.1)
        acquired = lock_a.acquire(timeout=1)
        if acquired:
            lock_a.release()
        return acquired


outcome = {}


def run_worker(name, fn):
    outcome[name] = fn()


t1 = threading.Thread(target=run_worker, args=("w1", worker_1))
t2 = threading.Thread(target=run_worker, args=("w2", worker_2))
t1.start(); t2.start()
t1.join(); t2.join()
print("acquire succeeded? ->", outcome, "(a False means that thread timed out -- classic deadlock)")


# ---------------------------------------------------------------- deadlock: fixed
section("fixed: BOTH workers acquire locks in the SAME global order (lock_a then lock_b)")


def worker_1_fixed():
    with lock_a, lock_b:
        time.sleep(0.05)
        return True


def worker_2_fixed():
    with lock_a, lock_b:  # same order as worker_1_fixed -- no cycle possible
        time.sleep(0.05)
        return True


outcome2 = {}
t1 = threading.Thread(target=lambda: outcome2.update(w1=worker_1_fixed()))
t2 = threading.Thread(target=lambda: outcome2.update(w2=worker_2_fixed()))
t1.start(); t2.start()
t1.join(); t2.join()
print("with consistent lock ordering:", outcome2, "(both True, no deadlock)")

# EXERCISE: remove the timeout=1 from the deadlock reproduction and run it (be ready to Ctrl+C) --
# that's the actual hang a real deadlock causes in production.
