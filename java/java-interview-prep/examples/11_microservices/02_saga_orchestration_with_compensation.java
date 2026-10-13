/*
 * 02 - Saga (orchestration): distributed transaction without 2PC, using compensating actions
 *
 * Run:  java 02_saga_orchestration_with_compensation.java
 *
 * Order -> reserve inventory -> charge payment -> create shipment. If a step fails, previously
 * completed steps are undone in reverse order. Also shows why the compensation itself must be
 * idempotent and retried until it succeeds.
 */
import java.util.*;
import java.util.function.*;

class SagaOrchestrationWithCompensation {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    interface Step {
        String name();
        void execute(Map<String, Object> ctx);        // may throw
        void compensate(Map<String, Object> ctx);     // must be idempotent
    }

    static class Action implements Step {
        final String name; final Consumer<Map<String, Object>> exec, comp;
        Action(String name, Consumer<Map<String, Object>> exec, Consumer<Map<String, Object>> comp) { this.name = name; this.exec = exec; this.comp = comp; }
        public String name() { return name; }
        public void execute(Map<String, Object> ctx) { exec.accept(ctx); }
        public void compensate(Map<String, Object> ctx) { comp.accept(ctx); }
    }

    static class Saga {
        final List<Step> steps = new ArrayList<>();
        final List<String> journal = new ArrayList<>();       // in production: persisted saga log / state table
        Saga add(Step s) { steps.add(s); return this; }

        boolean run(Map<String, Object> ctx) {
            Deque<Step> done = new ArrayDeque<>();
            for (Step s : steps) {
                try {
                    s.execute(ctx);
                    done.push(s);
                    journal.add("DONE        " + s.name());
                } catch (RuntimeException e) {
                    journal.add("FAILED      " + s.name() + " (" + e.getMessage() + ")");
                    while (!done.isEmpty()) {                  // compensate in REVERSE order
                        Step d = done.pop();
                        compensateWithRetry(d, ctx);
                    }
                    return false;
                }
            }
            return true;
        }

        private void compensateWithRetry(Step s, Map<String, Object> ctx) {
            for (int attempt = 1; ; attempt++) {
                try { s.compensate(ctx); journal.add("COMPENSATED " + s.name() + (attempt > 1 ? " (attempt " + attempt + ")" : "")); return; }
                catch (RuntimeException e) {
                    journal.add("comp-retry   " + s.name() + " attempt " + attempt + " failed (" + e.getMessage() + ")");
                    if (attempt >= 5) { journal.add("ESCALATE    " + s.name() + " -> manual intervention / alert"); return; }
                }
            }
        }
    }

    // ---- fake services with state, so compensation is observable
    static int stock = 5, reservedHolds = 0;
    static int charges = 0;
    static boolean paymentDeclines = false, refundFlaky = false;
    static int refundAttempts = 0;
    static Set<String> refunded = new HashSet<>();            // idempotency: refund once per orderId

    static Saga buildSaga() {
        return new Saga()
            .add(new Action("ReserveInventory",
                    ctx -> { if (stock < 1) throw new IllegalStateException("out of stock"); stock--; reservedHolds++; },
                    ctx -> { if (reservedHolds > 0) { reservedHolds--; stock++; } }))
            .add(new Action("ChargePayment",
                    ctx -> { if (paymentDeclines) throw new IllegalStateException("card declined"); charges++; },
                    ctx -> {
                        if (refundFlaky && ++refundAttempts < 3) throw new IllegalStateException("payment API timeout");
                        if (refunded.add((String) ctx.get("orderId"))) charges--;   // idempotent refund
                    }))
            .add(new Action("CreateShipment",
                    ctx -> { if (ctx.containsKey("noCourier")) throw new IllegalStateException("no courier available"); },
                    ctx -> { }));
    }

    static void report(String title, boolean ok, Saga saga) {
        System.out.println("  " + title + " -> " + (ok ? "ORDER CONFIRMED" : "ORDER REJECTED"));
        saga.journal.forEach(j -> System.out.println("    " + j));
        System.out.println("    state: stock=" + stock + " holds=" + reservedHolds + " charges=" + charges);
    }

    public static void main(String[] args) {
        section("1. Happy path");
        Saga s1 = buildSaga();
        Map<String, Object> c1 = new HashMap<>(); c1.put("orderId", "o-1");
        report("order o-1", s1.run(c1), s1);

        section("2. Third step fails: earlier steps are compensated in reverse");
        Saga s2 = buildSaga();
        Map<String, Object> c2 = new HashMap<>(); c2.put("orderId", "o-2"); c2.put("noCourier", true);
        report("order o-2", s2.run(c2), s2);

        section("3. Payment declines: only inventory needs undoing");
        stock = 5; reservedHolds = 0; charges = 0; paymentDeclines = true;
        Saga s3 = buildSaga();
        Map<String, Object> c3 = new HashMap<>(); c3.put("orderId", "o-3");
        report("order o-3", s3.run(c3), s3);
        paymentDeclines = false;

        section("4. Compensation fails transiently: retry until it succeeds (idempotently)");
        stock = 5; reservedHolds = 0; charges = 0; refundFlaky = true; refundAttempts = 0;
        Saga s4 = buildSaga();
        Map<String, Object> c4 = new HashMap<>(); c4.put("orderId", "o-4"); c4.put("noCourier", true);
        report("order o-4", s4.run(c4), s4);
        System.out.println("  Compensation is not a rollback: the customer may have SEEN the intermediate state (semantic undo).");

        section("5. Orchestration vs choreography");
        System.out.println("  Orchestration : a coordinator (this class, or Temporal/Camunda/Step Functions) tells each service what to do.");
        System.out.println("                  + clear flow, easy timeouts and monitoring   - coordinator is a component to own and keep available");
        System.out.println("  Choreography  : services react to each other's events (Kafka). + loose coupling");
        System.out.println("                  - flow is implicit, cyclic dependencies and hard-to-trace failure paths as it grows");
        System.out.println("  Requirements for either: idempotent steps and compensations, durable saga state, per-step timeouts, observability.");
        System.out.println("  Sagas give ACD without the I: design for intermediate states (PENDING orders) and use semantic locks.");
    }
}

// EXERCISE: persist the journal to a file after every step and make the saga resumable after a crash.
