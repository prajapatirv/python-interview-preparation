"""
Circuit breaker built from scratch: CLOSED -> OPEN -> HALF-OPEN -> CLOSED/OPEN.
Protects a struggling downstream from being hammered by retries while it's unhealthy.

Run me: python 02_circuit_breaker.py
"""
import time


def section(title):
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


class CircuitOpenError(Exception):
    """Raised immediately, without even attempting the call, while the circuit is OPEN."""


class CircuitBreaker:
    CLOSED, OPEN, HALF_OPEN = "CLOSED", "OPEN", "HALF_OPEN"

    def __init__(self, failure_threshold=3, recovery_timeout=1.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = self.CLOSED
        self.failure_count = 0
        self.opened_at = None

    def call(self, fn):
        if self.state == self.OPEN:
            if time.time() - self.opened_at >= self.recovery_timeout:
                # enough time has passed -- allow exactly one trial call through
                self.state = self.HALF_OPEN
                print("  [breaker] recovery timeout elapsed -> HALF_OPEN, letting one trial call through")
            else:
                raise CircuitOpenError("circuit is OPEN -- failing fast, not calling downstream")

        try:
            result = fn()
        except Exception:
            self._record_failure()
            raise
        else:
            self._record_success()
            return result

    def _record_failure(self):
        self.failure_count += 1
        if self.state == self.HALF_OPEN:
            # the trial call failed -- back to OPEN, restart the recovery clock
            self.state = self.OPEN
            self.opened_at = time.time()
            print("  [breaker] trial call failed -> back to OPEN")
        elif self.failure_count >= self.failure_threshold:
            self.state = self.OPEN
            self.opened_at = time.time()
            print(f"  [breaker] {self.failure_count} failures reached threshold -> OPEN")

    def _record_success(self):
        if self.state == self.HALF_OPEN:
            print("  [breaker] trial call succeeded -> CLOSED, service is healthy again")
        self.state = self.CLOSED
        self.failure_count = 0


# ---------------------------------------------------------------- a downstream that fails, then recovers
class FlakyDownstream:
    def __init__(self, fail_for_n_calls):
        self.calls = 0
        self.fail_for_n_calls = fail_for_n_calls

    def call(self):
        self.calls += 1
        if self.calls <= self.fail_for_n_calls:
            raise ConnectionError(f"downstream unavailable (call {self.calls})")
        return "ok"


def charge_with_fallback(breaker, downstream):
    try:
        return breaker.call(downstream.call)
    except CircuitOpenError:
        return "FALLBACK: queued for later retry"
    except ConnectionError:
        return "FALLBACK: downstream call failed"


section("a downstream that fails 4 times, recovers on the 5th call")
downstream = FlakyDownstream(fail_for_n_calls=4)
breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=0.3)

for i in range(1, 9):
    result = charge_with_fallback(breaker, downstream)
    print(f"call {i}: state={breaker.state:9s} -> {result}")
    if breaker.state == breaker.OPEN:
        # sleep past recovery_timeout so the NEXT call is allowed to probe HALF_OPEN again --
        # a real system wouldn't sleep in the caller like this; it would simply be whatever time
        # naturally elapses between real incoming requests.
        time.sleep(breaker.recovery_timeout + 0.05)

# EXPERIMENT: set failure_threshold=1 -- the breaker opens after a single failure. Compare how
# quickly it "protects" the downstream vs. how much legitimate traffic it might reject if that
# one failure was just a blip. This threshold tuning is a real production trade-off.
