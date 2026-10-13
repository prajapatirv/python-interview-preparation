/*
 * 06 - "What is the output?" trap questions (core Java gotchas that keep appearing)
 *
 * Run:  java 06_java_output_trap_questions.java
 *
 * Interview angle: Integer cache and ==, String pool and intern, return inside finally,
 * overload resolution with null / boxing / varargs, char arithmetic, integer overflow and
 * Math.abs(MIN_VALUE), List.remove(int) vs remove(Object), Arrays.asList, ternary unboxing NPE,
 * ConcurrentModificationException, floating point, HashSet without hashCode/equals, static init
 * order, and string immutability. Each trap is asserted, so the claimed output is verified.
 */
import java.math.BigDecimal;
import java.util.*;

class JavaOutputTrapQuestions {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    @SuppressWarnings("finally")
    static int finallyWins() { try { return 1; } finally { return 2; } }
    static int finallyDoesNotChangeReturnedPrimitive() { int x = 1; try { return x; } finally { x = 99; } }

    static String over(Object o) { return "Object"; }
    static String over(String s) { return "String"; }
    static String over(Integer i) { return "Integer"; }
    static String prim(long l) { return "long"; }
    static String prim(Integer i) { return "Integer"; }
    static String prim(int... v) { return "varargs"; }

    static class Point {
        final int x, y;
        Point(int x, int y) { this.x = x; this.y = y; }
        // equals WITHOUT hashCode: the classic broken contract
        @Override public boolean equals(Object o) { return o instanceof Point p && p.x == x && p.y == y; }
    }
    static class GoodPoint extends Point {
        GoodPoint(int x, int y) { super(x, y); }
        @Override public int hashCode() { return Objects.hash(x, y); }
    }

    static final List<String> INIT = new ArrayList<>();
    static class Parent {
        static { INIT.add("Parent.static"); }
        { INIT.add("Parent.instance"); }
        Parent() { INIT.add("Parent.ctor"); }
    }
    static class Child extends Parent {
        static { INIT.add("Child.static"); }
        { INIT.add("Child.instance"); }
        Child() { INIT.add("Child.ctor"); }
    }

    public static void main(String[] args) {
        section("1. Equality: == versus equals");
        Integer a = 127, b = 127, c = 128, d = 128;
        check("Integer cache: 127 == 127", true, a == b);
        check("Integer cache: 128 == 128 (outside -128..127)", false, c == d);
        check("Integer equals", true, c.equals(d));
        String s1 = "hello", s2 = "hello", s3 = new String("hello");
        check("literals share the pool", true, s1 == s2);
        check("new String is a distinct object", false, s1 == s3);
        check("intern() returns the pooled instance", true, s1 == s3.intern());
        check("equals compares content", true, s1.equals(s3));
        check("compile-time constant concatenation is pooled", true, s1 == "hel" + "lo");
        String part = "hel";
        check("runtime concatenation is NOT pooled", false, s1 == part + "lo");
        check("0.1 + 0.2 == 0.3", false, 0.1 + 0.2 == 0.3);
        check("BigDecimal from String is exact", "0.3", new BigDecimal("0.1").add(new BigDecimal("0.2")).toString());
        check("NaN != NaN", false, Double.NaN == Double.NaN);

        section("2. Arithmetic");
        check("Integer.MAX_VALUE + 1 wraps", Integer.MIN_VALUE, Integer.MAX_VALUE + 1);
        check("Math.abs(Integer.MIN_VALUE) is still negative", Integer.MIN_VALUE, Math.abs(Integer.MIN_VALUE));
        check("Math.floorMod(-7, 3) vs -7 % 3", "2/-1", Math.floorMod(-7, 3) + "/" + (-7 % 3));
        check("1 / 2 is integer division", 0, 1 / 2);
        check("char + int is int", 98, 'a' + 1);
        check("(char) cast restores the letter", 'b', (char) ('a' + 1));
        check("'a' + 'b' + \"c\" vs \"c\" + 'a' + 'b'", "195c/cab", ('a' + 'b' + "c") + "/" + ("c" + 'a' + 'b'));
        long wrong = 100_000 * 100_000;                  // int * int overflows BEFORE the widening to long
        long right = 100_000L * 100_000;
        check("int multiplication overflows before widening to long", "1410065408/10000000000", wrong + "/" + right);
        byte by = (byte) 200;
        check("(byte) 200 wraps to -56", (byte) -56, by);
        int i = 5;
        i = i++ + ++i;                       // 5 + 7
        check("i = i++ + ++i", 12, i);

        section("3. try / finally");
        check("return in finally overrides the try's return", 2, finallyWins());
        check("finally cannot change an already-evaluated primitive return", 1, finallyDoesNotChangeReturnedPrimitive());

        section("4. Overloading and autoboxing");
        check("over(\"s\")", "String", over("s"));
        check("over((Object) \"s\") chooses by STATIC type", "Object", over((Object) "s"));
        check("prim(5): widening beats boxing beats varargs", "long", prim(5));
        check("prim() with no args falls to varargs", "varargs", prim());

        section("5. Collections");
        List<Integer> nums = new ArrayList<>(List.of(10, 20, 30, 1));
        nums.remove(1);                                  // remove(int index)
        check("remove(int) removes by INDEX", "[10, 30, 1]", nums.toString());
        nums.remove(Integer.valueOf(1));                 // remove(Object)
        check("remove(Object) removes by VALUE", "[10, 30]", nums.toString());
        List<String> fixed = Arrays.asList("a", "b");
        try { fixed.add("c"); check("must throw", "threw", "did not"); }
        catch (UnsupportedOperationException e) { check("Arrays.asList is fixed-size", true, true); }
        try { List.of(1).set(0, 2); check("must throw", "threw", "did not"); }
        catch (UnsupportedOperationException e) { check("List.of is immutable", true, true); }
        List<Integer> cme = new ArrayList<>(List.of(1, 2, 3, 4));
        try { for (Integer n : cme) if (n == 2) cme.remove(n); check("must throw", "threw", "did not"); }
        catch (ConcurrentModificationException e) { check("remove inside for-each throws CME", true, true); }
        cme.removeIf(n -> n % 2 == 0);
        check("removeIf is the safe way (list was [1,3,4] after the failed loop)", "[1, 3]", cme.toString());
        Set<Point> bad = new HashSet<>(List.of(new Point(1, 2)));
        Set<Point> good = new HashSet<>(List.of(new GoodPoint(1, 2)));
        check("equals without hashCode: HashSet.contains(equal object)", false, bad.contains(new Point(1, 2)));
        check("equals + hashCode: HashSet.contains", true, good.contains(new GoodPoint(1, 2)));
        Map<Object, String> m = new HashMap<>();
        m.put(null, "null-key");
        check("HashMap allows one null key (Hashtable/ConcurrentHashMap do not)", "null-key", m.get(null));

        section("6. Unboxing, immutability, init order");
        Integer maybe = null;
        try { int boom = true ? maybe : 0; check("must throw", "threw", "did not " + boom); }
        catch (NullPointerException e) { check("ternary with a primitive operand unboxes null -> NPE", true, true); }
        String str = "abc";
        str.toUpperCase();                                // result discarded
        check("String methods return a NEW string", "abc", str);
        check("String.valueOf((Object) null) is the text \"null\", not an NPE", "null", String.valueOf((Object) null));
        INIT.clear();
        new Child();
        check("init order: statics, then parent instance+ctor, then child instance+ctor",
                "[Parent.static, Child.static, Parent.instance, Parent.ctor, Child.instance, Child.ctor]", INIT.toString());
        StringBuilder sb = new StringBuilder("x");
        mutate(sb);
        check("Java is pass-by-value; the reference is copied, the object is shared", "x!", sb.toString());
        StringBuilder sb2 = new StringBuilder("x");
        reassign(sb2);
        check("reassigning the parameter does not touch the caller's variable", "x", sb2.toString());

        System.out.println("\nAll " + checks + " checks passed.");
    }
    static void mutate(StringBuilder s) { s.append("!"); }
    static void reassign(StringBuilder s) { s = new StringBuilder("other"); }
}
