"""
Liveness vs readiness health checks, and a signal-driven graceful shutdown sequence.
Run me: python 04_health_checks_graceful_shutdown.py
(then, in a real deployment, `kill -TERM <pid>` -- here we simulate the signal directly so the
demo is self-contained and doesn't require a second terminal)
"""
import threading
import time

# Real graceful shutdown wires this up with:
#   import signal
#   signal.signal(signal.SIGTERM, lambda *_: shutdown_event.set())
# SIGTERM handling is POSIX-specific and awkward to demo reliably cross-platform in one script,
# so below we trigger the same shutdown_event directly to keep the demo self-contained.


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


# ---------------------------------------------------------------- liveness vs readiness
section("liveness ('is the process alive?') vs readiness ('can it serve traffic RIGHT NOW?')")


class FakeDependencies:
    """Stands in for a DB pool / cache client whose reachability can flip at runtime."""
    def __init__(self):
        self.db_ok = True
        self.cache_ok = True


deps = FakeDependencies()


def liveness_check():
    # A process can be "alive" (not deadlocked, event loop still spinning) even while its
    # dependencies are down. Kubernetes RESTARTS the pod if this fails.
    return {"status": "alive"}


def readiness_check():
    # A process can be alive but NOT ready to serve traffic (DB unreachable, still warming up
    # a cache). Kubernetes only STOPS ROUTING TRAFFIC if this fails -- it does NOT restart.
    checks = {"db": "ok" if deps.db_ok else "fail", "cache": "ok" if deps.cache_ok else "fail"}
    ready = all(v == "ok" for v in checks.values())
    return {"ready": ready, "checks": checks}


print("liveness :", liveness_check())
print("readiness:", readiness_check())

deps.db_ok = False  # simulate the database going unreachable
print("\n-- DB goes down --")
print("liveness :", liveness_check(), " <- still alive! the process itself is fine")
print("readiness:", readiness_check(), " <- NOT ready -- traffic should stop routing here")
print("this distinction matters: restarting a healthy process because a DOWNSTREAM is briefly")
print("unreachable just causes a thundering herd of reconnects when it comes back.")
deps.db_ok = True  # restore for the rest of the demo


# ---------------------------------------------------------------- graceful shutdown
section("graceful shutdown: stop accepting new work, drain in-flight work, THEN exit")

shutdown_event = threading.Event()
in_flight = {"count": 0}
in_flight_lock = threading.Lock()


def handle_request(i):
    with in_flight_lock:
        if shutdown_event.is_set():
            print(f"  request {i}: REJECTED -- shutting down, not accepting new work")
            return
        in_flight["count"] += 1
    try:
        time.sleep(0.15)  # simulate work in progress
        print(f"  request {i}: completed")
    finally:
        with in_flight_lock:
            in_flight["count"] -= 1


def graceful_shutdown():
    print("  SIGTERM received -- entering graceful shutdown")
    shutdown_event.set()  # stop accepting new requests immediately
    while True:
        with in_flight_lock:
            remaining = in_flight["count"]
        if remaining == 0:
            break
        print(f"  draining... {remaining} request(s) still in flight")
        time.sleep(0.05)
    print("  all in-flight requests drained -- safe to exit now")
    # a real service would also: flush a buffered Kafka producer, close DB connections, etc.


# simulate several concurrent requests, with a SIGTERM arriving mid-flight
threads = [threading.Thread(target=handle_request, args=(i,)) for i in range(5)]
[t.start() for t in threads]
time.sleep(0.05)  # let a couple requests get in-flight before the "signal" arrives

shutdown_thread = threading.Thread(target=graceful_shutdown)
shutdown_thread.start()

# a couple more requests attempt to start AFTER shutdown began -- they should be rejected
late_requests = [threading.Thread(target=handle_request, args=(i,)) for i in (5, 6)]
[t.start() for t in late_requests]

[t.join() for t in threads + late_requests + [shutdown_thread]]
print("\nprocess exits cleanly -- no request was killed mid-flight")

# EXPERIMENT: remove the `if shutdown_event.is_set(): return` guard in handle_request and rerun
# -- late requests now start AFTER shutdown began, and graceful_shutdown's drain loop has to
# wait for them too, or (worse, in a real system) the process could exit while still serving them.
