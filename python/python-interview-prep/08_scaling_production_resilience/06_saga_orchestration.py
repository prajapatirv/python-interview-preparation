"""
Saga (orchestration): a business transaction across services without 2PC, undone by compensations.

The Python twin of java/java-interview-prep/examples/11_microservices/02_saga_orchestration_with_compensation.java
(see shared/cross-stack-pairs.md). Order -> reserve inventory -> charge payment -> create shipment.
When a step fails, the steps that already ran are compensated in REVERSE order. A compensation can
itself fail, so it must be idempotent and retried until it succeeds.

Run me: python 06_saga_orchestration.py
Deep dive: ../deep_dive/12_scaling_applications.md
"""
from dataclasses import dataclass, field


def section(title):
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


class StepFailed(Exception):
    pass


# ================================================================ three fake services, each with its own database
class Inventory:
    def __init__(self, stock=10):
        self.stock, self.reservations = stock, {}

    def reserve(self, order_id, qty):
        if qty > self.stock:
            raise StepFailed("out of stock")
        self.stock -= qty
        self.reservations[order_id] = qty

    def release(self, order_id):                       # compensation; idempotent: a second call is a no-op
        self.stock += self.reservations.pop(order_id, 0)


class Payments:
    def __init__(self, decline_over=None, refund_failures=0):
        self.charges, self.decline_over, self.refund_failures = {}, decline_over, refund_failures
        self.refund_calls = 0

    def charge(self, order_id, amount):
        if self.decline_over is not None and amount > self.decline_over:
            raise StepFailed("card declined")
        self.charges[order_id] = amount

    def refund(self, order_id):
        self.refund_calls += 1
        if self.refund_failures > 0:                   # the payment provider times out a few times
            self.refund_failures -= 1
            raise TimeoutError("payment provider timed out")
        self.charges.pop(order_id, None)               # idempotent: refunding twice refunds once


class Shipping:
    def __init__(self, down=False):
        self.shipments, self.down = {}, down

    def create(self, order_id):
        if self.down:
            raise StepFailed("shipping service unavailable")
        self.shipments[order_id] = "label-printed"

    def cancel(self, order_id):
        self.shipments.pop(order_id, None)


# ================================================================ the orchestrator
@dataclass
class Step:
    name: str
    action: callable
    compensation: callable


@dataclass
class SagaLog:
    """What a real orchestrator persists after every step, so a crash mid-saga can resume or undo."""
    events: list = field(default_factory=list)

    def add(self, text):
        self.events.append(text)
        print(f"  {text}")


def run_saga(steps, log, max_compensation_attempts=5):
    done = []
    for step in steps:
        try:
            step.action()
            done.append(step)
            log.add(f"OK    {step.name}")
        except StepFailed as e:
            log.add(f"FAIL  {step.name}: {e} -> compensating {len(done)} completed step(s) in reverse")
            for prev in reversed(done):
                compensate(prev, log, max_compensation_attempts)
            return "COMPENSATED"
    return "COMPLETED"


def compensate(step, log, max_attempts):
    for attempt in range(1, max_attempts + 1):
        try:
            step.compensation()
            log.add(f"UNDO  {step.name}" + (f" (attempt {attempt})" if attempt > 1 else ""))
            return
        except TimeoutError as e:
            log.add(f"RETRY {step.name}: {e}")         # real code: backoff with jitter, then a DLQ + alert
    log.add(f"STUCK {step.name}: still failing after {max_attempts} attempts -> park for a human")


def order_saga(order_id, qty, amount, inventory, payments, shipping):
    return [
        Step("reserve inventory", lambda: inventory.reserve(order_id, qty), lambda: inventory.release(order_id)),
        Step("charge payment", lambda: payments.charge(order_id, amount), lambda: payments.refund(order_id)),
        Step("create shipment", lambda: shipping.create(order_id), lambda: shipping.cancel(order_id)),
    ]


def state(inv, pay, ship):
    return f"stock={inv.stock} reserved={inv.reservations} charges={pay.charges} shipments={ship.shipments}"


def main():
    section("1. Happy path")
    inv, pay, ship = Inventory(), Payments(), Shipping()
    print(f"  saga result: {run_saga(order_saga('o-1', 2, 50, inv, pay, ship), SagaLog())}")
    print(f"  {state(inv, pay, ship)}")

    section("2. The third step fails: earlier steps are compensated in reverse")
    inv, pay, ship = Inventory(), Payments(), Shipping(down=True)
    print(f"  saga result: {run_saga(order_saga('o-2', 2, 50, inv, pay, ship), SagaLog())}")
    print(f"  {state(inv, pay, ship)}   <- back where we started: no money taken, stock restored")

    section("3. Payment declines: only the inventory needs undoing")
    inv, pay, ship = Inventory(), Payments(decline_over=40), Shipping()
    print(f"  saga result: {run_saga(order_saga('o-3', 1, 99, inv, pay, ship), SagaLog())}")
    print(f"  {state(inv, pay, ship)}")

    section("4. A compensation fails transiently: retry it until it succeeds")
    inv, pay, ship = Inventory(), Payments(refund_failures=2), Shipping(down=True)
    print(f"  saga result: {run_saga(order_saga('o-4', 3, 70, inv, pay, ship), SagaLog())}")
    print(f"  refund was called {pay.refund_calls} times; {state(inv, pay, ship)}")
    pay.refund("o-4")
    print(f"  a duplicate refund (e.g. a redelivered message) changes nothing: charges={pay.charges}")
    print("  That is why every compensation must be idempotent: retries and redeliveries WILL happen.")
    # EXPERIMENT: set refund_failures=9 and rerun - the saga parks the refund as STUCK. What should
    #             happen next in production? (Alert, a dead-letter queue, a manual runbook.)

    section("5. Orchestration vs choreography, and what a saga does NOT give you")
    print("  orchestration : one coordinator calls each service and owns the state (this file; Temporal,")
    print("                  AWS Step Functions, Camunda). Easy to follow and to monitor.")
    print("  choreography  : each service reacts to the previous one's event (OrderPlaced -> PaymentCharged).")
    print("                  No central brain; harder to see the whole flow and to change the order.")
    print("  no isolation  : between steps other requests SEE the half-done state (stock reserved, no")
    print("                  payment yet). Use semantic locks (status=PENDING) and make reads tolerate it.")
    print("  the log       : persist each step (as SagaLog does) so a crashed orchestrator resumes or undoes.")
    print("  steps that cannot be undone (an email sent) go LAST, after every step that can fail.")


if __name__ == "__main__":
    main()


# EXERCISE 1: persist SagaLog to a JSON file after every event, kill the process in the middle of
#             step 2, and write the recovery code that reads the log and compensates.
# EXERCISE 2: rewrite the flow as choreography: three handlers subscribed to events on a queue.
#             Where does the "compensate in reverse" logic live now?
