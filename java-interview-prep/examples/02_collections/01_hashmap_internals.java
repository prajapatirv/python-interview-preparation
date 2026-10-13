/*
 * 01 - HashMap internals: buckets, collisions, the equals/hashCode contract (Java 8+)
 *
 * Run:  java 01_hashmap_internals.java
 *
 * Interview angle: "How does HashMap work?", "what if hashCode is bad?",
 * "what if you mutate a key?", "why is the capacity a power of two?", "load factor".
 */
import java.util.*;

class HashMapInternals {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    /** Every instance lands in the same bucket: HashMap degrades to a tree (Java 8) / list (Java 7). */
    static final class BadKey implements Comparable<BadKey> {
        final int id;
        BadKey(int id) { this.id = id; }
        @Override public int hashCode() { return 42; }
        @Override public boolean equals(Object o) { return o instanceof BadKey && ((BadKey) o).id == id; }
        @Override public int compareTo(BadKey o) { return Integer.compare(id, o.id); }
    }

    static final class GoodKey {
        final int id;
        GoodKey(int id) { this.id = id; }
        @Override public int hashCode() { return Integer.hashCode(id); }
        @Override public boolean equals(Object o) { return o instanceof GoodKey && ((GoodKey) o).id == id; }
    }

    /** Equal objects, DIFFERENT hash codes: breaks the contract. */
    static final class BrokenContract {
        final String v;
        BrokenContract(String v) { this.v = v; }
        @Override public boolean equals(Object o) { return o instanceof BrokenContract && ((BrokenContract) o).v.equals(v); }
        // hashCode() NOT overridden -> identity hash
    }

    static final class MutableKey {
        String name;
        MutableKey(String n) { name = n; }
        @Override public int hashCode() { return name.hashCode(); }
        @Override public boolean equals(Object o) { return o instanceof MutableKey && ((MutableKey) o).name.equals(name); }
    }

    public static void main(String[] args) {

        section("1. How a key finds its bucket");
        int tableSize = 16;
        for (String k : new String[]{"alpha", "beta", "gamma", "delta"}) {
            int h = k.hashCode();
            int spread = h ^ (h >>> 16);                  // HashMap.hash(): mixes the high bits into the low bits
            int index = (tableSize - 1) & spread;         // power-of-two table => AND instead of %
            System.out.printf("  %-6s hashCode=%11d spread=%11d bucket=%2d%n", k, h, spread, index);
        }
        System.out.println("  default: capacity 16, load factor 0.75 -> resize (x2) when size > 12");

        section("2. Equal keys must have equal hash codes");
        Map<BrokenContract, String> broken = new HashMap<>();
        broken.put(new BrokenContract("k"), "first");
        System.out.println("  get(new equal key) = " + broken.get(new BrokenContract("k")) + "   <- null: lookup went to the wrong bucket");
        Set<BrokenContract> set = new HashSet<>(Arrays.asList(new BrokenContract("a"), new BrokenContract("a")));
        System.out.println("  HashSet of two 'equal' objects has size " + set.size() + " (should be 1)");

        section("3. Mutating a key after insertion loses the entry");
        Map<MutableKey, String> m = new HashMap<>();
        MutableKey key = new MutableKey("before");
        m.put(key, "value");
        key.name = "after";
        System.out.println("  size=" + m.size() + ", get(key)=" + m.get(key) + ", containsValue=" + m.containsValue("value")
                + "   <- still in the map but unreachable (a memory leak)");
        // Rule: use immutable keys (String, Integer, records, enums).

        section("4. Collisions: bad hashCode vs good hashCode");
        int n = 20_000;
        Map<BadKey, Integer> bad = new HashMap<>();
        long t0 = System.nanoTime();
        for (int i = 0; i < n; i++) bad.put(new BadKey(i), i);
        for (int i = 0; i < n; i++) bad.get(new BadKey(i));
        long badMs = (System.nanoTime() - t0) / 1_000_000;
        Map<GoodKey, Integer> good = new HashMap<>();
        t0 = System.nanoTime();
        for (int i = 0; i < n; i++) good.put(new GoodKey(i), i);
        for (int i = 0; i < n; i++) good.get(new GoodKey(i));
        long goodMs = (System.nanoTime() - t0) / 1_000_000;
        System.out.println("  " + n + " puts+gets: good hashCode ~" + goodMs + " ms, constant hashCode ~" + badMs + " ms");
        System.out.println("  BadKey is Comparable, so Java 8 turns the long bucket into a red-black tree (O(log n)).");
        System.out.println("  A non-Comparable bad key would be O(n) per lookup - that is also the hash-flooding DoS vector.");
        // EXPERIMENT: remove 'implements Comparable' from BadKey and re-run: watch the time explode.

        section("5. null handling and iteration order");
        Map<String, Integer> hm = new HashMap<>();
        hm.put(null, 1);
        System.out.println("  HashMap allows one null key: " + hm);
        try { new Hashtable<String, Integer>().put(null, 1); }
        catch (NullPointerException e) { System.out.println("  Hashtable / ConcurrentHashMap reject null keys: NPE"); }
        Map<String, Integer> lhm = new LinkedHashMap<>(); lhm.put("z", 1); lhm.put("a", 2); lhm.put("m", 3);
        Map<String, Integer> tm = new TreeMap<>(lhm);
        System.out.println("  LinkedHashMap keeps insertion order: " + lhm.keySet() + " | TreeMap sorts: " + tm.keySet());
        System.out.println("  HashMap order is unspecified and can change after a resize - never depend on it.");

        section("6. Pre-size when you know the count (avoid repeated resizes)");
        int expected = 1_000;
        int capacity = (int) (expected / 0.75f) + 1;
        System.out.println("  for " + expected + " entries use new HashMap<>(" + capacity + ") (Java 19+: HashMap.newHashMap(" + expected + "))");
    }
}

// EXERCISE: implement a minimal HashMap<K,V> with separate chaining and resize at 0.75 load.
