/*
 * 04 - Behavioural patterns, one runnable demo each: Strategy, Observer, Command, State, Template Method, Chain of
 *      Responsibility, Iterator, Mediator, Memento, Visitor, Interpreter, Null Object
 *
 * Run:  java 04_behavioral_patterns.java
 *
 * Interview angle: "strategy vs state", "observer vs pub/sub", "command and undo", "chain of responsibility in
 * filters", "iterator and fail-fast", "when is visitor worth it".
 */
import java.util.*;
import java.util.function.*;

class BehavioralPatterns {

    // ---- Strategy
    interface Shipping { int cost(int kg); }

    // ---- Observer
    static class Topic {
        private final List<Consumer<String>> subs = new ArrayList<>();
        void subscribe(Consumer<String> s) { subs.add(s); }
        void publish(String m) { subs.forEach(s -> s.accept(m)); }
    }

    // ---- Command (with undo)
    interface Command { void run(); void undo(); }
    static class Editor {
        final StringBuilder text = new StringBuilder();
        final Deque<Command> history = new ArrayDeque<>();
        void exec(Command c) { c.run(); history.push(c); }
        void undo() { if (!history.isEmpty()) history.pop().undo(); }
        Command append(String s) {
            return new Command() {
                public void run() { text.append(s); }
                public void undo() { text.setLength(text.length() - s.length()); }
            };
        }
    }

    // ---- State: behaviour depends on the object's own state
    enum OrderState {
        NEW { OrderState next() { return PAID; } },
        PAID { OrderState next() { return SHIPPED; } },
        SHIPPED { OrderState next() { throw new IllegalStateException("already shipped"); } };
        abstract OrderState next();
    }

    // ---- Template Method
    static abstract class Report {
        final String generate() { return header() + "|" + body() + "|" + footer(); }
        protected String header() { return "HEADER"; }
        protected abstract String body();
        protected String footer() { return "END"; }
    }

    // ---- Chain of Responsibility
    interface Handler { String handle(int amount); }
    static Handler link(int limit, String who, Handler next) {
        return amount -> amount <= limit ? who + " approves " + amount : (next == null ? "nobody can approve " + amount : next.handle(amount));
    }

    // ---- Iterator
    static class Countdown implements Iterable<Integer> {
        final int from; Countdown(int f) { from = f; }
        public Iterator<Integer> iterator() {
            return new Iterator<Integer>() {
                int n = from;
                public boolean hasNext() { return n > 0; }
                public Integer next() { return n--; }
            };
        }
    }

    // ---- Mediator: peers talk only to the hub
    static class ChatRoom {
        final Map<String, List<String>> inbox = new LinkedHashMap<>();
        void join(String user) { inbox.put(user, new ArrayList<>()); }
        void say(String from, String msg) { inbox.forEach((u, box) -> { if (!u.equals(from)) box.add(from + ": " + msg); }); }
    }

    // ---- Memento: snapshot and restore
    static class Doc {
        String text = "";
        String save() { return text; }                                               // memento (a String is immutable, so safe)
        void restore(String m) { text = m; }
    }

    // ---- Visitor: add operations without touching the element classes
    interface Node { <R> R accept(Visitor<R> v); }
    interface Visitor<R> { R num(int n); R add(Node l, Node r); }
    static class Num implements Node { final int n; Num(int n) { this.n = n; } public <R> R accept(Visitor<R> v) { return v.num(n); } }
    static class Add implements Node { final Node l, r; Add(Node l, Node r) { this.l = l; this.r = r; } public <R> R accept(Visitor<R> v) { return v.add(l, r); } }

    // ---- Interpreter: a tiny grammar  expr := term ('+' term)*
    static int interpret(String s) { int t = 0; for (String p : s.split("\\+")) t += Integer.parseInt(p.trim()); return t; }

    // ---- Null Object
    interface Audit { void record(String e); int count(); }
    static class RealAudit implements Audit { int n; public void record(String e) { n++; } public int count() { return n; } }
    static class NoAudit implements Audit { public void record(String e) { } public int count() { return 0; } }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        section("1. Strategy: swap the algorithm, the client chooses");
        Map<String, Shipping> s = new LinkedHashMap<>();
        s.put("ground", kg -> 100 + 20 * kg); s.put("air", kg -> 500 + 90 * kg);
        s.forEach((k, v) -> System.out.println("  " + k + " 3kg = " + v.cost(3) + " cents"));
        System.out.println("  JDK: Comparator. Spring: AuthenticationProvider, HandlerMapping.");

        section("2. Observer: one-to-many notification");
        Topic t = new Topic();
        t.subscribe(m -> System.out.println("  inventory got " + m));
        t.subscribe(m -> System.out.println("  email got " + m));
        t.publish("OrderPlaced#7");
        System.out.println("  Spring: @EventListener. Observer is in-process; pub/sub (Kafka) adds a broker, durability and decoupling in time.");

        section("3. Command: request as an object, so it can be queued and undone");
        Editor e = new Editor();
        e.exec(e.append("Hello ")); e.exec(e.append("World"));
        System.out.print("  text = '" + e.text + "'"); e.undo(); System.out.println(" -> after undo '" + e.text + "'");
        System.out.println("  Runnable/Callable, job queues, Kafka commands, transactional undo (saga compensation).");

        section("4. State: the object changes behaviour as its own state changes");
        OrderState st = OrderState.NEW;
        st = st.next(); st = st.next();
        System.out.println("  NEW -> PAID -> " + st);
        try { st.next(); } catch (IllegalStateException ex) { System.out.println("  illegal transition rejected: " + ex.getMessage()); }
        System.out.println("  Strategy: client picks it. State: it moves itself. Spring Statemachine, order/payment lifecycles.");

        section("5. Template Method: fixed skeleton, overridable steps");
        System.out.println("  " + new Report() { protected String body() { return "sales=42"; } }.generate());
        System.out.println("  Spring: JdbcTemplate, AbstractRoutingDataSource. Functional form: pass a callback.");

        section("6. Chain of Responsibility: pass along until someone handles it");
        Handler chain = link(1_000, "teamlead", link(10_000, "manager", link(100_000, "director", null)));
        System.out.println("  " + chain.handle(500) + " | " + chain.handle(50_000) + " | " + chain.handle(500_000));
        System.out.println("  Servlet filters, Spring Security filter chain, HandlerInterceptor. A decorator always delegates; a handler may stop.");

        section("7. Iterator: traverse without exposing structure");
        StringBuilder sb = new StringBuilder();
        for (int n : new Countdown(3)) sb.append(n).append(' ');
        System.out.println("  " + sb + " (Iterable + for-each). Fail-fast iterators throw ConcurrentModificationException on structural change.");

        section("8. Mediator: peers talk through a hub");
        ChatRoom room = new ChatRoom(); room.join("ann"); room.join("bob"); room.join("cy");
        room.say("ann", "standup?");
        System.out.println("  inboxes = " + room.inbox + "   (event bus, DispatcherServlet-style coordination)");

        section("9. Memento: capture and restore state");
        Doc d = new Doc(); d.text = "v1"; String snap = d.save(); d.text = "v2 (oops)"; d.restore(snap);
        System.out.println("  restored to '" + d.text + "'   (undo history, editor snapshots)");

        section("10. Visitor: new operation, element classes untouched");
        Node expr = new Add(new Num(2), new Add(new Num(3), new Num(4)));
        Visitor<Integer> eval = new Visitor<Integer>() {
            public Integer num(int n) { return n; }
            public Integer add(Node l, Node r) { return l.accept(this) + r.accept(this); }
        };
        Visitor<String> print = new Visitor<String>() {
            public String num(int n) { return String.valueOf(n); }
            public String add(Node l, Node r) { return "(" + l.accept(this) + " + " + r.accept(this) + ")"; }
        };
        System.out.println("  " + expr.accept(print) + " = " + expr.accept(eval) + "   (worth it only when the element set is stable and operations keep growing)");

        section("11. Interpreter: evaluate a small grammar");
        System.out.println("  '1 + 2 + 39' = " + interpret("1 + 2 + 39") + "   (SpEL, regex, SQL parsers: rarely hand-written; use a library)");

        section("12. Null Object: a do-nothing implementation instead of null checks");
        Audit on = new RealAudit(), off = new NoAudit();
        on.record("x"); off.record("x");
        System.out.println("  real count = " + on.count() + ", null-object count = " + off.count() + "  (no if (audit != null) anywhere). JDK: Collections.emptyList().");
    }
}

// EXERCISE: add a 'cancelled' state to OrderState that is reachable from NEW and PAID but not SHIPPED, then show why an if/else on a status string is harder to extend.
