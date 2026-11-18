"""
Coding round: linked lists, binary trees and graphs - the problems that come up again and again.

The Python twin of java/java-interview-prep/examples/21_coding_interview/03_linked_list_tree_graph.java
(see shared/cross-stack-pairs.md). For each problem, say the invariant out loud before coding it:
that is what senior rounds score, more than the code itself.

  linked list : reverse (iterative and recursive), detect a cycle, find the middle, merge two sorted lists
  tree / BST  : height, level-order, validate a BST, lowest common ancestor, kth smallest, serialize
  graphs      : number of islands, cycle in a directed graph, topological order, shortest path in a grid

Run me: python 07_linked_list_tree_graph.py
Run the tests: pytest 07_linked_list_tree_graph.py -v
"""
from collections import deque


# ---------------------------------------------------------------- linked list
class Node:
    def __init__(self, val, next_=None):
        self.val, self.next = val, next_


def from_list(values):
    head = None
    for v in reversed(values):
        head = Node(v, head)
    return head


def to_list(head, limit=1_000):
    out = []
    while head and len(out) < limit:
        out.append(head.val)
        head = head.next
    return out


def reverse(head):
    """Invariant: `prev` is the reversed part, `head` the part still to reverse. O(n) time, O(1) space."""
    prev = None
    while head:
        head.next, prev, head = prev, head, head.next
    return prev


def reverse_recursive(head):
    """O(n) stack depth: Python's default recursion limit (~1,000) makes this fail on long lists."""
    if head is None or head.next is None:
        return head
    new_head = reverse_recursive(head.next)
    head.next.next, head.next = head, None
    return new_head


def has_cycle(head):
    """Floyd: the fast pointer gains one step per move, so inside a cycle it must land on the slow one."""
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
        if slow is fast:
            return True
    return False


def middle(head):
    """When fast reaches the end, slow is halfway. For an even length this returns the second middle."""
    slow = fast = head
    while fast and fast.next:
        slow, fast = slow.next, fast.next.next
    return slow


def merge_sorted(a, b):
    dummy = tail = Node(None)                 # the dummy node removes the "which list starts?" special case
    while a and b:
        if a.val <= b.val:
            tail.next, a = a, a.next
        else:
            tail.next, b = b, b.next
        tail = tail.next
    tail.next = a or b
    return dummy.next


# ---------------------------------------------------------------- binary tree and BST
class Tree:
    def __init__(self, val, left=None, right=None):
        self.val, self.left, self.right = val, left, right


def bst_from(values):
    root = None
    for v in values:
        root = _insert(root, v)
    return root


def _insert(node, v):
    if node is None:
        return Tree(v)
    if v < node.val:
        node.left = _insert(node.left, v)
    else:
        node.right = _insert(node.right, v)
    return node


def height(node):
    return 0 if node is None else 1 + max(height(node.left), height(node.right))


def level_order(root):
    """BFS with a queue; one inner loop per level gives the levels as separate lists."""
    if root is None:
        return []
    levels, queue = [], deque([root])
    while queue:
        level = []
        for _ in range(len(queue)):
            n = queue.popleft()
            level.append(n.val)
            queue.extend(c for c in (n.left, n.right) if c)
        levels.append(level)
    return levels


def is_bst(node, low=float("-inf"), high=float("inf")):
    """Pass the allowed RANGE down. Checking only parent vs child is the classic wrong answer."""
    if node is None:
        return True
    if not low < node.val < high:
        return False
    return is_bst(node.left, low, node.val) and is_bst(node.right, node.val, high)


def lca_bst(node, p, q):
    """In a BST the split point is the first node with p and q on different sides. O(height)."""
    while node:
        if p < node.val and q < node.val:
            node = node.left
        elif p > node.val and q > node.val:
            node = node.right
        else:
            return node.val
    return None


def kth_smallest(root, k):
    """In-order traversal of a BST visits values in sorted order; stop at the kth. Iterative: no recursion limit."""
    stack, node = [], root
    while stack or node:
        while node:
            stack.append(node)
            node = node.left
        node = stack.pop()
        k -= 1
        if k == 0:
            return node.val
        node = node.right
    raise ValueError("k is larger than the tree")


def serialize(node):
    """Pre-order with '#' for empty children: unambiguous, so it round-trips."""
    out = []

    def walk(n):
        if n is None:
            out.append("#")
            return
        out.append(str(n.val))
        walk(n.left)
        walk(n.right)
    walk(node)
    return ",".join(out)


def deserialize(text):
    tokens = iter(text.split(","))

    def build():
        t = next(tokens)
        if t == "#":
            return None
        return Tree(int(t), build(), build())
    return build()


# ---------------------------------------------------------------- graphs and grids
def count_islands(grid):
    """Flood-fill each unvisited land cell with BFS. O(rows*cols). Iterative, so big grids are safe."""
    rows, cols, seen, islands = len(grid), len(grid[0]), set(), 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and (r, c) not in seen:
                islands += 1
                queue = deque([(r, c)])
                seen.add((r, c))
                while queue:
                    y, x = queue.popleft()
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == "1" and (ny, nx) not in seen:
                            seen.add((ny, nx))
                            queue.append((ny, nx))
    return islands


def topological_order(graph):
    """Kahn's algorithm. If not every node comes out, the leftovers sit on a cycle: return None."""
    indegree = {n: 0 for n in graph}
    for targets in graph.values():
        for t in targets:
            indegree[t] = indegree.get(t, 0) + 1
    queue = deque(sorted(n for n, d in indegree.items() if d == 0))
    order = []
    while queue:
        n = queue.popleft()
        order.append(n)
        for t in graph.get(n, ()):
            indegree[t] -= 1
            if indegree[t] == 0:
                queue.append(t)
    return order if len(order) == len(indegree) else None


def has_directed_cycle(graph):
    return topological_order(graph) is None


def shortest_path(grid, start, goal):
    """BFS finds the fewest steps in an unweighted grid ('#' is a wall). Weighted edges need Dijkstra."""
    rows, cols = len(grid), len(grid[0])
    queue, dist = deque([start]), {start: 0}
    while queue:
        cell = queue.popleft()
        if cell == goal:
            return dist[cell]
        y, x = cell
        for nxt in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
            ny, nx = nxt
            if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] != "#" and nxt not in dist:
                dist[nxt] = dist[cell] + 1
                queue.append(nxt)
    return -1


GRID = ["11000",
        "11010",
        "00100",
        "00011"]
MAZE = ["..#.",
        ".##.",
        "....",
        "#..."]
COURSES = {"python": ["fastapi", "pandas"], "fastapi": ["deploy"], "pandas": ["deploy"], "deploy": []}


if __name__ == "__main__":
    print("== linked list")
    print("  reverse 1..5            :", to_list(reverse(from_list([1, 2, 3, 4, 5]))))
    print("  reverse (recursive)     :", to_list(reverse_recursive(from_list([1, 2, 3]))))
    loop = from_list([1, 2, 3, 4])
    loop.next.next.next.next = loop.next                           # 4 -> 2 makes a cycle
    print("  cycle detected          :", has_cycle(loop), "| no cycle:", has_cycle(from_list([1, 2, 3])))
    print("  middle of 1..5          :", middle(from_list([1, 2, 3, 4, 5])).val)
    print("  merge [1,4,9] + [2,3,10]:", to_list(merge_sorted(from_list([1, 4, 9]), from_list([2, 3, 10]))))
    try:
        reverse_recursive(from_list(list(range(5_000))))
    except RecursionError:
        print("  recursive reverse of 5,000 nodes -> RecursionError: say this before the interviewer does")

    print("\n== binary tree / BST")
    root = bst_from([50, 30, 70, 20, 40, 60, 80])
    print("  level order             :", level_order(root))
    print("  height                  :", height(root))
    print("  is a BST                :", is_bst(root))
    trap = Tree(10, Tree(5, None, Tree(15)), Tree(20))             # 15 is right of 5 but left of 10
    print("  'parent vs child only' would accept this tree; the range check says:", is_bst(trap))
    print("  LCA(20, 40)             :", lca_bst(root, 20, 40), "| LCA(20, 80):", lca_bst(root, 20, 80))
    print("  3rd smallest            :", kth_smallest(root, 3))
    text = serialize(root)
    print("  serialize               :", text)
    print("  round trip equal        :", serialize(deserialize(text)) == text)

    print("\n== graphs and grids")
    print("  islands in GRID         :", count_islands(GRID))
    print("  course order            :", topological_order(COURSES))
    print("  cycle in a->b->c->a     :", has_directed_cycle({"a": ["b"], "b": ["c"], "c": ["a"]}))
    print("  shortest path in MAZE   :", shortest_path(MAZE, (0, 0), (0, 3)), "steps")

# EXPERIMENT: replace deque.popleft() with list.pop(0) in level_order and time a tree of 100,000
#             nodes - list.pop(0) is O(n), so BFS quietly becomes O(n^2).


# ---------------------------------------------------------------- tests (plain asserts: no pytest import needed)
def test_reverse_both_ways():
    assert to_list(reverse(from_list([1, 2, 3]))) == [3, 2, 1]
    assert to_list(reverse_recursive(from_list([1, 2, 3]))) == [3, 2, 1]
    assert reverse(None) is None and to_list(reverse(from_list([7]))) == [7]


def test_cycle_middle_and_merge():
    loop = from_list([1, 2, 3])
    loop.next.next.next = loop
    assert has_cycle(loop) and not has_cycle(from_list([1, 2])) and not has_cycle(None)
    assert middle(from_list([1, 2, 3, 4])).val == 3
    assert to_list(merge_sorted(from_list([1, 3]), from_list([2, 4, 5]))) == [1, 2, 3, 4, 5]
    assert to_list(merge_sorted(None, from_list([1]))) == [1]


def test_tree_problems():
    root = bst_from([50, 30, 70, 20, 40, 60, 80])
    assert level_order(root) == [[50], [30, 70], [20, 40, 60, 80]] and height(root) == 3
    assert is_bst(root) and not is_bst(Tree(10, Tree(5, None, Tree(15)), Tree(20)))
    assert lca_bst(root, 20, 40) == 30 and lca_bst(root, 60, 80) == 70 and lca_bst(root, 20, 80) == 50
    assert [kth_smallest(root, k) for k in (1, 4, 7)] == [20, 50, 80]
    assert serialize(deserialize(serialize(root))) == serialize(root) and level_order(None) == []


def test_kth_smallest_rejects_too_large_k():
    try:
        kth_smallest(bst_from([2, 1]), 3)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_graph_problems():
    assert count_islands(GRID) == 4 and count_islands(["0"]) == 0
    order = topological_order(COURSES)
    assert order.index("python") < order.index("fastapi") < order.index("deploy")
    assert has_directed_cycle({"a": ["b"], "b": ["a"]}) and not has_directed_cycle(COURSES)
    assert shortest_path(MAZE, (0, 0), (0, 3)) == 7 and shortest_path([".#."], (0, 0), (0, 2)) == -1
