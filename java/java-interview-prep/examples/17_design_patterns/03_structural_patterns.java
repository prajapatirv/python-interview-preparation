/*
 * 03 - Structural patterns, one runnable demo each: Adapter, Bridge, Composite, Decorator, Facade, Flyweight, Proxy
 *
 * Run:  java 03_structural_patterns.java
 *
 * Interview angle: "adapter vs facade vs proxy vs decorator", "bridge vs adapter", "where do you see composite",
 * "what is flyweight (Integer cache)", "types of proxy and how Spring AOP uses it".
 */
import java.util.*;
import java.util.function.Supplier;

class StructuralPatterns {

    // ---- Adapter: make an incompatible interface fit
    interface Logger { void log(String msg); }
    static class LegacyAuditSdk { String write(int level, String text, long ts) { return "audit[" + level + "] " + text; } }
    static class AuditAdapter implements Logger {                                    // adapts the SDK to OUR port
        private final LegacyAuditSdk sdk; final List<String> out = new ArrayList<>();
        AuditAdapter(LegacyAuditSdk s) { sdk = s; }
        public void log(String msg) { out.add(sdk.write(1, msg, 0L)); }
    }

    // ---- Bridge: abstraction and implementation vary independently
    interface Renderer { String drawCircle(int r); }
    static class VectorRenderer implements Renderer { public String drawCircle(int r) { return "vector circle r=" + r; } }
    static class RasterRenderer implements Renderer { public String drawCircle(int r) { return "pixels for circle r=" + r; } }
    static abstract class Shape { protected final Renderer renderer; Shape(Renderer r) { renderer = r; } abstract String draw(); }
    static class Circle extends Shape { final int r; Circle(Renderer rd, int r) { super(rd); this.r = r; } String draw() { return renderer.drawCircle(r); } }

    // ---- Composite: leaf and group behind one interface
    interface FsNode { long size(); }
    static class FileNode implements FsNode { final long bytes; FileNode(long b) { bytes = b; } public long size() { return bytes; } }
    static class Folder implements FsNode {
        final List<FsNode> children = new ArrayList<>();
        Folder add(FsNode n) { children.add(n); return this; }
        public long size() { long t = 0; for (FsNode c : children) t += c.size(); return t; }
    }

    // ---- Decorator: stack behaviour on the same interface
    interface Text { String render(); }
    static class Plain implements Text { final String s; Plain(String s) { this.s = s; } public String render() { return s; } }
    static class Upper implements Text { final Text in; Upper(Text t) { in = t; } public String render() { return in.render().toUpperCase(); } }
    static class Bracketed implements Text { final Text in; Bracketed(Text t) { in = t; } public String render() { return "[" + in.render() + "]"; } }

    // ---- Facade: one simple call over a subsystem
    static class Inventory { boolean reserve(String sku) { return true; } }
    static class Payment { boolean charge(int cents) { return cents < 100_000; } }
    static class Shipping { String ship(String sku) { return "shipped " + sku; } }
    static class CheckoutFacade {
        private final Inventory inv = new Inventory(); private final Payment pay = new Payment(); private final Shipping ship = new Shipping();
        String placeOrder(String sku, int cents) {
            if (!inv.reserve(sku)) return "out of stock";
            if (!pay.charge(cents)) return "payment declined";
            return ship.ship(sku);
        }
    }

    // ---- Flyweight: share immutable intrinsic state
    static final class Glyph {                                                       // intrinsic: the character shape
        final char c; Glyph(char c) { this.c = c; }
        static final Map<Character, Glyph> POOL = new HashMap<>();
        static int created;
        static Glyph of(char c) { return POOL.computeIfAbsent(c, k -> { created++; return new Glyph(k); }); }
    }

    // ---- Proxy: protection + virtual (lazy) in one
    interface Report { String body(); }
    static class HeavyReport implements Report {
        static int loads;
        HeavyReport() { loads++; }                                                   // pretend this is expensive
        public String body() { return "quarterly numbers"; }
    }
    static class ReportProxy implements Report {
        private final Supplier<Report> factory; private final boolean allowed; private Report real;
        ReportProxy(Supplier<Report> f, boolean allowed) { factory = f; this.allowed = allowed; }
        public String body() {
            if (!allowed) throw new SecurityException("access denied");              // protection proxy
            if (real == null) real = factory.get();                                  // virtual proxy: create on first use
            return real.body();
        }
    }

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    public static void main(String[] args) {
        section("1. Adapter: fit a legacy/third-party API to your own interface");
        AuditAdapter a = new AuditAdapter(new LegacyAuditSdk());
        a.log("user created");
        System.out.println("  " + a.out + "   JDK: Arrays.asList, InputStreamReader. Spring: HandlerAdapter.");

        section("2. Bridge: shape x renderer without a class per combination");
        System.out.println("  " + new Circle(new VectorRenderer(), 5).draw() + " | " + new Circle(new RasterRenderer(), 5).draw());
        System.out.println("  2 shapes x 2 renderers needs 4 classes without Bridge, 2 + 2 with it. JDBC: DriverManager/Driver.");

        section("3. Composite: treat one file and a whole tree the same");
        Folder root = new Folder().add(new FileNode(100)).add(new Folder().add(new FileNode(50)).add(new FileNode(25)));
        System.out.println("  total size = " + root.size() + " bytes   (UI trees, menus, org charts, JSF/Swing components)");

        section("4. Decorator: wrap to add behaviour, same interface, stackable");
        System.out.println("  " + new Bracketed(new Upper(new Plain("hello"))).render() + "   JDK: BufferedReader, Collections.unmodifiableList.");

        section("5. Facade: hide a subsystem behind one method");
        CheckoutFacade f = new CheckoutFacade();
        System.out.println("  " + f.placeOrder("sku-1", 2_500) + " | " + f.placeOrder("sku-2", 500_000));

        section("6. Flyweight: share immutable objects");
        for (char c : "mississippi".toCharArray()) Glyph.of(c);
        System.out.println("  11 characters rendered, " + Glyph.created + " Glyph objects created   JDK: Integer.valueOf cache, String pool.");

        section("7. Proxy: control access to the real object");
        Report ok = new ReportProxy(HeavyReport::new, true);
        System.out.println("  loads before first use = " + HeavyReport.loads + ", body = " + ok.body() + ", loads after = " + HeavyReport.loads);
        try { new ReportProxy(HeavyReport::new, false).body(); } catch (SecurityException e) { System.out.println("  protection proxy: " + e.getMessage()); }
        System.out.println("  Types: virtual, protection, remote, caching, smart. Spring AOP: @Transactional, @Cacheable. Hibernate: lazy proxies.");

        section("8. Which one? (same shape, different intent)");
        System.out.println("  Adapter = change the interface | Decorator = same interface + behaviour | Proxy = same interface + access control");
        System.out.println("  Facade = new simpler interface over many | Bridge = designed-in split | Composite = tree | Flyweight = share state");
    }
}

// EXERCISE: add a caching decorator and a logging proxy around the same interface, then explain in one sentence why the first is a Decorator and the second a Proxy.
