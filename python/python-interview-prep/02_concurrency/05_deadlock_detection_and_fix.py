"""
Deadlock: create it, find it the way you would in production, then fix it two ways.

The Python twin of java/java-interview-prep/examples/04_concurrency/03_deadlock_detection_and_fix.java
(see shared/cross-stack-pairs.md). 04_sync_primitives.py shows the basic reproduce-and-reorder demo;
this file answers the follow-ups: "how do you FIND one?", "the four conditions", "what if you can't
order the locks?", plus the two deadlocks that are specific to Python (a re-acquired Lock, and asyncio).

Python has no ThreadMXBean, so detection is built from what the runtime does give you: a thread dump
from sys._current_frames() (what py-spy dump and faulthandler print) and a wait-for graph.

Run me: python 05_deadlock_detection_and_fix.py
Deep dive: ../deep_dive/07_concurrency.md
"""
import asyncio
import random
import sys
import threading
import time
import traceback


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ================================================================ a lock that records who holds and who waits
class TrackedLock:
    """A threading.Lock that remembers its owner and its waiters, so a wait-for graph can be built.
    Real code would not wrap every lock; the point is to see what a detector needs to know."""
    registry: list["TrackedLock"] = []

    def __init__(self, name):
        self.name, self._lock, self.owner, self.waiters = name, threading.Lock(), None, set()
        TrackedLock.registry.append(self)

    def acquire(self, timeout=-1):
        me = threading.current_thread().name
        self.waiters.add(me)
        try:
            got = self._lock.acquire(timeout=timeout)
        finally:
            self.waiters.discard(me)
        if got:
            self.owner = me
        return got

    def release(self):
        self.owner = None
        self._lock.release()


def find_deadlock():
    """Edges thread -> thread ('waits for a lock held by'); a cycle is a deadlock."""
    waits_for = {w: lock.owner for lock in TrackedLock.registry if lock.owner for w in lock.waiters}
    for start in waits_for:
        path, node = [start], waits_for.get(start)
        while node is not None and node not in path:
            path.append(node)
            node = waits_for.get(node)
        if node == start:
            return path
    return None


def thread_dump(names):
    """The jstack equivalent: where is each thread stuck right now?"""
    frames = sys._current_frames()
    for t in threading.enumerate():
        if t.name in names and t.ident in frames:
            last = traceback.extract_stack(frames[t.ident])[-2]       # [-1] is inside TrackedLock.acquire
            print(f"  {t.name:<20} stuck at line {last.lineno} in {last.name}(): {last.line.split('#')[0].strip()}")


lock_a, lock_b = TrackedLock("A"), TrackedLock("B")


def holds_a_wants_b():
    lock_a.acquire()
    time.sleep(0.1)                     # widen the window so both threads take their first lock
    lock_b.acquire()                    # blocks forever: T2 holds B and wants A


def holds_b_wants_a():
    lock_b.acquire()
    time.sleep(0.1)
    lock_a.acquire()                    # blocks forever: T1 holds A and wants B


# ================================================================ bank transfers for the two fixes
HOLD = 0.0005      # time spent holding the first lock, so the two threads really collide (Java: sleep(20))


class Account:
    def __init__(self, id_, balance):
        self.id, self.balance, self.lock = id_, balance, threading.Lock()


def transfer_ordered(src, dst, amount):
    """FIX 1: every thread takes the locks in one global order (by id), so no cycle can form."""
    first, second = (src, dst) if src.id < dst.id else (dst, src)
    with first.lock:
        time.sleep(HOLD)
        with second.lock:
            src.balance -= amount
            dst.balance += amount


def transfer_with_timeout(src, dst, amount, retries):
    """FIX 2: when an order is impossible, give up the first lock on timeout and retry with jitter."""
    while True:
        with src.lock:
            time.sleep(HOLD)
            if dst.lock.acquire(timeout=0.005):
                try:
                    src.balance -= amount
                    dst.balance += amount
                    return
                finally:
                    dst.lock.release()
        retries.append(1)                                   # backed off: nobody waits forever
        time.sleep(random.uniform(0, 0.002))                # jitter, or both retry in lock-step (livelock)


def run_opposite_transfers(fn, *extra):
    x, y = Account(1, 1_000), Account(2, 1_000)

    def move(src, dst, amount):
        for _ in range(200):
            fn(src, dst, amount, *extra)

    # daemon, so a broken transfer function reports stuck=True instead of hanging the whole program
    threads = [threading.Thread(target=move, args=(x, y, 3), daemon=True),
               threading.Thread(target=move, args=(y, x, 2), daemon=True)]
    start = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    stuck = any(t.is_alive() for t in threads)
    return x, y, stuck, time.perf_counter() - start


async def async_deadlock_and_fix():
    a, b = asyncio.Lock(), asyncio.Lock()

    async def take(first, second):
        async with first:
            await asyncio.sleep(0.05)               # yield, so the other task takes its first lock
            async with second:
                return "done"

    try:
        await asyncio.wait_for(asyncio.gather(take(a, b), take(b, a)), timeout=0.5)
        print("  opposite order : finished (unexpected)")
    except TimeoutError:
        print("  opposite order : TimeoutError after 0.5 s - two tasks on ONE thread deadlocked;")
        print("                   the loop itself stays responsive, only those tasks are stuck")
    results = await asyncio.wait_for(asyncio.gather(take(a, b), take(a, b)), timeout=0.5)
    print(f"  same order     : {results} - the same lock-ordering fix works for asyncio.Lock")


def main():
    section("1. Create a classic lock-ordering deadlock")
    t1 = threading.Thread(target=holds_a_wants_b, name="T1-holds-A-wants-B", daemon=True)
    t2 = threading.Thread(target=holds_b_wants_a, name="T2-holds-B-wants-A", daemon=True)
    t1.start()
    t2.start()
    time.sleep(0.4)
    print(f"  after 0.4 s both threads are alive and stuck: {t1.is_alive() and t2.is_alive()}")
    print("  (daemon=True so the interpreter can still exit; a real service just hangs)")

    section("2. Find it: a thread dump plus a wait-for graph")
    thread_dump({t1.name, t2.name})
    cycle = find_deadlock()
    print(f"  wait-for cycle : {' -> '.join(cycle + cycle[:1]) if cycle else 'none'}")
    print("  In production:  py-spy dump --pid <pid>   (no restart, no code change)")
    print("                  faulthandler.dump_traceback_later(60) as a watchdog, or")
    print("                  faulthandler.register(signal.SIGUSR1) to dump on demand (not on Windows).")
    print("  Take 3 dumps about 10 s apart: threads parked on the same line every time are the culprits.")
    print("  Java contrast: ThreadMXBean.findDeadlockedThreads() / jstack find the cycle for you.")

    section("3. The four Coffman conditions - break any one and deadlock is impossible")
    print("  mutual exclusion | hold and wait | no preemption | circular wait")
    print("  lock ordering breaks circular wait; acquire(timeout=...) breaks hold-and-wait and no-preemption.")
    print("  The GIL does not help: a thread blocked in acquire() releases it, and the others carry on.")

    section("4. Fix 1: one global lock order (400 opposite transfers)")
    x, y, stuck, secs = run_opposite_transfers(transfer_ordered)
    print(f"  stuck: {stuck}   x={x.balance} y={y.balance}   sum preserved: {x.balance + y.balance == 2_000}"
          f"   ({secs * 1000:.0f} ms)")
    # EXPERIMENT: change transfer_ordered to `first, second = src, dst` (no ordering) and rerun:
    #             'stuck' turns True once the two 5 s join timeouts run out, and nothing moves.

    section("5. Fix 2: acquire with a timeout, back off, retry with jitter")
    retries = []
    x, y, stuck, secs = run_opposite_transfers(transfer_with_timeout, retries)
    print(f"  stuck: {stuck}   x={x.balance} y={y.balance}   sum preserved: {x.balance + y.balance == 2_000}"
          f"   back-offs: {len(retries)}")
    print("  Use it when one order is impossible (locks discovered at runtime, plugins, callbacks).")
    print("  Java contrast: ReentrantLock.tryLock(timeout) - Python's threading.Lock.acquire(timeout=) is the same idea.")

    section("6. Two deadlocks that are specific to Python")
    plain = threading.Lock()
    with plain:
        again = plain.acquire(timeout=0.2)
    print(f"  threading.Lock re-acquired by the SAME thread: {again}  (it deadlocks itself; Java locks are reentrant)")
    reentrant = threading.RLock()
    with reentrant:
        with reentrant:
            print("  threading.RLock re-acquired by the same thread: True  (reentrant, like synchronized)")
    asyncio.run(async_deadlock_and_fix())
    print("  Others worth naming: queue.join() with a missing task_done(); joining a multiprocessing")
    print("  Process before draining the Queue it writes to; calling back into user code while holding a lock.")

    section("7. Related liveness problems")
    print("  livelock  : threads keep backing off in step and never progress (fix: the random jitter above)")
    print("  starvation: a thread never wins the lock; threading.Lock makes no FIFO promise")
    print("  Keep critical sections short, and never hold a lock across I/O or a network call.")


if __name__ == "__main__":
    main()


# EXERCISE 1: dining philosophers with 5 TrackedLocks - make it deadlock, show find_deadlock()
#             printing the 5-thread cycle, then fix it two different ways.
# EXERCISE 2: write a watchdog thread that runs find_deadlock() every second and, on a cycle,
#             prints thread_dump() and exits non-zero (what a health check would do).
