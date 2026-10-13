/*
 * 03 - Coding round: linked lists, trees, recursion and graphs
 *
 * Run:  java 03_linked_list_tree_graph.java
 *
 * Interview angle: "reverse a linked list (iterative and recursive)", "detect a cycle", "find the
 * middle", "merge two sorted lists", "validate a BST", "lowest common ancestor", "kth smallest in
 * a BST", "level-order traversal", "height", "number of islands", "cycle in a directed graph",
 * "serialize a tree". Senior rounds care about the recursion invariant and about what happens on
 * a null, a single node, a skewed tree and a very deep tree (stack overflow).
 */
import java.util.*;

class LinkedListTreeGraph {

    static int checks = 0;
    static void section(String t) { System.out.println("\n=== " + t + " ==="); }
    static void check(String label, Object expected, Object actual) {
        checks++;
        if (!Objects.equals(expected, actual))
            throw new AssertionError(label + ": expected " + expected + " but got " + actual);
        System.out.println("  ok  " + label + " -> " + actual);
    }

    // ---- Linked list --------------------------------------------------------------------
    static class Node {
        int val; Node next;
        Node(int v) { val = v; }
    }
    static Node list(int... v) {
        Node dummy = new Node(0), t = dummy;
        for (int x : v) { t.next = new Node(x); t = t.next; }
        return dummy.next;
    }
    static String str(Node n) {
        StringBuilder sb = new StringBuilder("[");
        for (int guard = 0; n != null && guard < 50; n = n.next, guard++) sb.append(sb.length() > 1 ? "," : "").append(n.val);
        return sb.append("]").toString();
    }

    /** Three pointers, O(n)/O(1). */
    static Node reverseIterative(Node head) {
        Node prev = null;
        while (head != null) { Node next = head.next; head.next = prev; prev = head; head = next; }
        return prev;
    }
    /** O(n) time, O(n) STACK: a 1M-node list overflows the stack. Know that trade-off. */
    static Node reverseRecursive(Node head) {
        if (head == null || head.next == null) return head;
        Node newHead = reverseRecursive(head.next);
        head.next.next = head;
        head.next = null;
        return newHead;
    }
    /** Floyd's tortoise and hare: O(n)/O(1), no HashSet. */
    static boolean hasCycle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) {
            slow = slow.next; fast = fast.next.next;
            if (slow == fast) return true;
        }
        return false;
    }
    static Node middle(Node head) {
        Node slow = head, fast = head;
        while (fast != null && fast.next != null) { slow = slow.next; fast = fast.next.next; }
        return slow;                                   // second middle for even length
    }
    /** Dummy head removes the "is the result list empty yet?" special case. */
    static Node mergeSorted(Node a, Node b) {
        Node dummy = new Node(0), t = dummy;
        while (a != null && b != null) {
            if (a.val <= b.val) { t.next = a; a = a.next; } else { t.next = b; b = b.next; }
            t = t.next;
        }
        t.next = a != null ? a : b;
        return dummy.next;
    }
    /** Two-pointer gap of n: one pass. */
    static Node removeNthFromEnd(Node head, int n) {
        Node dummy = new Node(0); dummy.next = head;
        Node fast = dummy, slow = dummy;
        for (int i = 0; i < n; i++) fast = fast.next;
        while (fast.next != null) { fast = fast.next; slow = slow.next; }
        slow.next = slow.next.next;
        return dummy.next;
    }

    // ---- Binary tree --------------------------------------------------------------------
    static class T {
        int val; T left, right;
        T(int v) { val = v; }
        T(int v, T l, T r) { val = v; left = l; right = r; }
    }
    static T bstInsert(T root, int v) {
        if (root == null) return new T(v);
        if (v < root.val) root.left = bstInsert(root.left, v); else root.right = bstInsert(root.right, v);
        return root;
    }
    static int height(T n) { return n == null ? 0 : 1 + Math.max(height(n.left), height(n.right)); }

    /** BFS with a queue; the "size at the start of the level" trick separates levels. */
    static List<List<Integer>> levelOrder(T root) {
        List<List<Integer>> out = new ArrayList<>();
        if (root == null) return out;
        Deque<T> q = new ArrayDeque<>();
        q.add(root);
        while (!q.isEmpty()) {
            int size = q.size();
            List<Integer> level = new ArrayList<>();
            for (int i = 0; i < size; i++) {
                T n = q.poll();
                level.add(n.val);
                if (n.left != null) q.add(n.left);
                if (n.right != null) q.add(n.right);
            }
            out.add(level);
        }
        return out;
    }
    static void inorder(T n, List<Integer> out) {
        if (n == null) return;
        inorder(n.left, out); out.add(n.val); inorder(n.right, out);
    }
    /** Pass (min, max) bounds DOWN. Comparing only with the parent is the classic wrong answer. */
    static boolean isValidBst(T n, long lo, long hi) {
        if (n == null) return true;
        if (n.val <= lo || n.val >= hi) return false;
        return isValidBst(n.left, lo, n.val) && isValidBst(n.right, n.val, hi);
    }
    /** In-order of a BST is sorted, so the kth visited node is the kth smallest. Stops early. */
    static int kthSmallest(T root, int k) {
        Deque<T> st = new ArrayDeque<>();
        T cur = root;
        while (cur != null || !st.isEmpty()) {
            while (cur != null) { st.push(cur); cur = cur.left; }
            cur = st.pop();
            if (--k == 0) return cur.val;
            cur = cur.right;
        }
        throw new NoSuchElementException("k is larger than the tree");
    }
    /** General binary tree LCA: the node where p and q are found in different subtrees. */
    static T lca(T n, int p, int q) {
        if (n == null || n.val == p || n.val == q) return n;
        T l = lca(n.left, p, q), r = lca(n.right, p, q);
        return l != null && r != null ? n : (l != null ? l : r);
    }
    /** Post-order: each node returns its best downward path; the global max is the best bend. */
    static int best;
    static int maxPathSum(T root) { best = Integer.MIN_VALUE; down(root); return best; }
    private static int down(T n) {
        if (n == null) return 0;
        int l = Math.max(0, down(n.left)), r = Math.max(0, down(n.right));
        best = Math.max(best, n.val + l + r);
        return n.val + Math.max(l, r);
    }
    /** Pre-order with an explicit null marker round-trips any shape. */
    static String serialize(T n) { return n == null ? "#" : n.val + "," + serialize(n.left) + "," + serialize(n.right); }
    static T deserialize(String s) { return build(new ArrayDeque<>(Arrays.asList(s.split(",")))); }
    private static T build(Deque<String> q) {
        String t = q.poll();
        if (t.equals("#")) return null;
        T n = new T(Integer.parseInt(t));
        n.left = build(q); n.right = build(q);
        return n;
    }

    // ---- Graphs -------------------------------------------------------------------------
    /** Flood fill. Mutates the grid to mark visited (copy first if the caller needs it intact). */
    static int numIslands(char[][] g) {
        int count = 0;
        for (int r = 0; r < g.length; r++)
            for (int c = 0; c < g[0].length; c++)
                if (g[r][c] == '1') { count++; sink(g, r, c); }
        return count;
    }
    private static void sink(char[][] g, int r, int c) {
        if (r < 0 || c < 0 || r >= g.length || c >= g[0].length || g[r][c] != '1') return;
        g[r][c] = '0';
        sink(g, r + 1, c); sink(g, r - 1, c); sink(g, r, c + 1); sink(g, r, c - 1);
    }
    /** DFS with three colours: 0 unvisited, 1 on the current path, 2 done. Back edge to 1 = cycle. */
    static boolean hasDirectedCycle(Map<Integer, List<Integer>> g) {
        Map<Integer, Integer> color = new HashMap<>();
        for (Integer start : g.keySet()) if (dfsCycle(g, start, color)) return true;
        return false;
    }
    private static boolean dfsCycle(Map<Integer, List<Integer>> g, int u, Map<Integer, Integer> color) {
        int c = color.getOrDefault(u, 0);
        if (c == 1) return true;
        if (c == 2) return false;
        color.put(u, 1);
        for (int v : g.getOrDefault(u, List.of())) if (dfsCycle(g, v, color)) return true;
        color.put(u, 2);
        return false;
    }
    /** Kahn's algorithm: also answers "build order" and detects cycles (result shorter than n). */
    static List<Integer> topoOrder(int n, int[][] edges) {
        List<List<Integer>> adj = new ArrayList<>();
        int[] indeg = new int[n];
        for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        for (int[] e : edges) { adj.get(e[0]).add(e[1]); indeg[e[1]]++; }
        Deque<Integer> q = new ArrayDeque<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.add(i);
        List<Integer> order = new ArrayList<>();
        while (!q.isEmpty()) {
            int u = q.poll();
            order.add(u);
            for (int v : adj.get(u)) if (--indeg[v] == 0) q.add(v);
        }
        return order;
    }

    public static void main(String[] args) {
        section("1. Linked list");
        check("reverse iterative", "[5,4,3,2,1]", str(reverseIterative(list(1, 2, 3, 4, 5))));
        check("reverse recursive", "[3,2,1]", str(reverseRecursive(list(1, 2, 3))));
        check("reverse empty / single", "[]/[7]", str(reverseIterative(null)) + "/" + str(reverseIterative(list(7))));
        Node cyc = list(1, 2, 3, 4);
        Node tail = cyc; while (tail.next != null) tail = tail.next;
        tail.next = cyc.next;                           // 4 -> 2
        check("hasCycle true", true, hasCycle(cyc));
        check("hasCycle false", false, hasCycle(list(1, 2, 3)));
        check("middle of odd list", 3, middle(list(1, 2, 3, 4, 5)).val);
        check("middle of even list (second middle)", 3, middle(list(1, 2, 3, 4)).val);
        check("mergeSorted", "[1,1,2,3,4,4]", str(mergeSorted(list(1, 2, 4), list(1, 3, 4))));
        check("removeNthFromEnd(2)", "[1,2,3,5]", str(removeNthFromEnd(list(1, 2, 3, 4, 5), 2)));
        check("removeNthFromEnd removes the head", "[2]", str(removeNthFromEnd(list(1, 2), 2)));

        section("2. Binary tree / BST");
        T bst = null;
        for (int v : new int[]{8, 3, 10, 1, 6, 14, 4, 7, 13}) bst = bstInsert(bst, v);
        List<Integer> in = new ArrayList<>(); inorder(bst, in);
        check("inorder of a BST is sorted", "[1, 3, 4, 6, 7, 8, 10, 13, 14]", in.toString());
        check("height", 4, height(bst));
        check("levelOrder", "[[8], [3, 10], [1, 6, 14], [4, 7, 13]]", levelOrder(bst).toString());
        check("kthSmallest(3)", 4, kthSmallest(bst, 3));
        check("isValidBst", true, isValidBst(bst, Long.MIN_VALUE, Long.MAX_VALUE));
        T liar = new T(10, new T(5, new T(1), new T(12)), new T(15));   // 12 is right of 5 but left of 10
        check("isValidBst catches the grandchild violation", false, isValidBst(liar, Long.MIN_VALUE, Long.MAX_VALUE));
        check("lca(4, 7) in BST", 6, lca(bst, 4, 7).val);
        check("lca(1, 14)", 8, lca(bst, 1, 14).val);
        T pathTree = new T(-10, new T(9), new T(20, new T(15), new T(7)));
        check("maxPathSum", 42, maxPathSum(pathTree));
        String ser = serialize(bst);
        check("serialize/deserialize round trip", ser, serialize(deserialize(ser)));
        check("skewed tree height (n = 3000, recursion ok)", 3000, height(skewed(3000)));

        section("3. Graphs and grids");
        char[][] grid = {
                "11000".toCharArray(), "11000".toCharArray(), "00100".toCharArray(), "00011".toCharArray()};
        check("numIslands", 3, numIslands(grid));
        Map<Integer, List<Integer>> dag = Map.of(1, List.of(2, 3), 2, List.of(4), 3, List.of(4), 4, List.of());
        Map<Integer, List<Integer>> cyclic = Map.of(1, List.of(2), 2, List.of(3), 3, List.of(1));
        check("DAG has no cycle (diamond is NOT a cycle)", false, hasDirectedCycle(dag));
        check("cyclic graph", true, hasDirectedCycle(cyclic));
        check("topoOrder", "[0, 1, 2, 3]", topoOrder(4, new int[][]{{0, 1}, {1, 2}, {2, 3}}).toString());
        check("topoOrder shorter than n means a cycle", 0, topoOrder(2, new int[][]{{0, 1}, {1, 0}}).size());

        System.out.println("\nAll " + checks + " checks passed.");
    }

    static T skewed(int n) {
        T root = new T(0), cur = root;
        for (int i = 1; i < n; i++) { cur.right = new T(i); cur = cur.right; }
        return root;
    }
}
