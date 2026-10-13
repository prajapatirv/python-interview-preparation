/*
 * 02 - Collections pitfalls interviewers love
 *
 * Run:  java 02_collections_pitfalls.java
 *
 * Fail-fast iterators, Arrays.asList / List.of, LRU with LinkedHashMap, Comparable consistency,
 * ConcurrentHashMap atomic ops, CopyOnWriteArrayList.
 */
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.*;

class CollectionsPitfalls {

    static void section(String t) { System.out.println("\n=== " + t + " ==="); }

    /** LRU cache in ~6 lines: LinkedHashMap in access-order mode + removeEldestEntry. */
    static class LruCache<K, V> extends LinkedHashMap<K, V> {
        private final int capacity;
        LruCache(int capacity) { super(16, 0.75f, true); this.capacity = capacity; }   // true = access order
        @Override protected boolean removeEldestEntry(Map.Entry<K, V> eldest) { return size() > capacity; }
    }

    static final class Version implements Comparable<Version> {
        final String label; final int major;
        Version(String label, int major) { this.label = label; this.major = major; }
        @Override public int compareTo(Version o) { return Integer.compare(major, o.major); }  // ignores label!
        @Override public boolean equals(Object o) { return o instanceof Version && ((Version) o).label.equals(label); }
        @Override public int hashCode() { return label.hashCode(); }
        @Override public String toString() { return label; }
    }

    public static void main(String[] args) throws Exception {

        section("1. Fail-fast iterators: ConcurrentModificationException");
        List<Integer> nums = new ArrayList<>(Arrays.asList(1, 2, 3, 4, 5));
        try { for (Integer x : nums) if (x == 2) nums.remove(x); }
        catch (ConcurrentModificationException e) { System.out.println("  remove inside for-each -> CME"); }
        nums.removeIf(x -> x % 2 == 0);                                  // the right way
        System.out.println("  removeIf(even) -> " + nums);
        Iterator<Integer> it = nums.iterator();
        while (it.hasNext()) if (it.next() == 3) it.remove();             // the other right way
        System.out.println("  Iterator.remove -> " + nums);
        // Why 'remove 4 of 5' sometimes does NOT throw: hasNext() returns false before next() checks modCount.

        section("2. Arrays.asList is fixed-size; List.of is immutable (and null-hostile)");
        List<String> view = Arrays.asList("a", "b", "c");
        view.set(0, "A");                                                // allowed: it writes through
        try { view.add("d"); } catch (UnsupportedOperationException e) { System.out.println("  Arrays.asList().add -> UnsupportedOperationException"); }
        try { List.of("a").set(0, "x"); } catch (UnsupportedOperationException e) { System.out.println("  List.of().set       -> UnsupportedOperationException"); }
        try { List.of("a", null); } catch (NullPointerException e) { System.out.println("  List.of(.., null)   -> NullPointerException"); }
        String[] backing = {"x", "y"};
        List<String> live = Arrays.asList(backing);
        backing[0] = "CHANGED";
        System.out.println("  Arrays.asList is a VIEW of the array: " + live);
        List<String> copy = List.copyOf(Arrays.asList(backing));
        System.out.println("  List.copyOf makes an immutable snapshot: " + copy);

        section("3. LRU cache via LinkedHashMap (access order)");
        LruCache<String, Integer> lru = new LruCache<>(3);
        lru.put("a", 1); lru.put("b", 2); lru.put("c", 3);
        lru.get("a");                      // a becomes most recently used
        lru.put("d", 4);                   // evicts b (least recently used)
        System.out.println("  keys (LRU -> MRU) = " + lru.keySet() + "  (b was evicted)");
        System.out.println("  not thread-safe: wrap with Collections.synchronizedMap or use Caffeine in production.");

        section("4. TreeSet uses compareTo, HashSet uses equals: keep them consistent");
        Set<Version> tree = new TreeSet<>();
        tree.add(new Version("1.0-alpha", 1));
        tree.add(new Version("1.0-final", 1));            // compareTo==0 -> treated as duplicate!
        Set<Version> hash = new HashSet<>(Arrays.asList(new Version("1.0-alpha", 1), new Version("1.0-final", 1)));
        System.out.println("  TreeSet size=" + tree.size() + "  HashSet size=" + hash.size() + "   <- inconsistent with equals");

        section("5. ConcurrentHashMap: use the atomic methods, not check-then-act");
        ConcurrentHashMap<String, Integer> chm = new ConcurrentHashMap<>();
        ExecutorService pool = Executors.newFixedThreadPool(8);
        CountDownLatch done = new CountDownLatch(8);
        Map<String, Integer> racy = new ConcurrentHashMap<>();
        for (int t = 0; t < 8; t++) {
            pool.submit(() -> {
                for (int i = 0; i < 5_000; i++) {
                    chm.merge("hits", 1, Integer::sum);                         // atomic
                    Integer cur = racy.get("hits");                              // check-then-act: lost updates
                    racy.put("hits", cur == null ? 1 : cur + 1);
                }
                done.countDown();
            });
        }
        done.await(); pool.shutdown();
        System.out.println("  merge()          = " + chm.get("hits") + " (expected 40000)");
        System.out.println("  get()+put()      = " + racy.get("hits") + " (thread-safe map, still a race)");

        section("6. CopyOnWriteArrayList: cheap reads, expensive writes");
        CopyOnWriteArrayList<String> listeners = new CopyOnWriteArrayList<>(Arrays.asList("l1", "l2"));
        for (String l : listeners) listeners.add(l + "-copy");           // no CME: iterates a snapshot
        System.out.println("  after adding during iteration: " + listeners + "  (good for listener lists, bad for write-heavy data)");

        section("7. Choosing a collection");
        System.out.println("  ArrayList  : default list; O(1) index, O(n) middle insert");
        System.out.println("  LinkedList : almost never; poor cache locality (use ArrayDeque for queues/stacks)");
        System.out.println("  HashSet/HashMap: O(1) average; TreeMap O(log n) sorted; LinkedHashMap ordered/LRU");
        System.out.println("  PriorityQueue: heap, O(log n) offer/poll, iteration order is NOT sorted");
        PriorityQueue<Integer> pq = new PriorityQueue<>(Arrays.asList(5, 1, 4, 2, 3));
        System.out.println("  PriorityQueue toString (heap array) = " + pq + " ; poll order = " + drain(pq));
    }

    static List<Integer> drain(PriorityQueue<Integer> pq) {
        List<Integer> out = new ArrayList<>();
        while (!pq.isEmpty()) out.add(pq.poll());
        return out;
    }
}

// EXERCISE: make LruCache thread-safe without synchronizing every read. Compare with Caffeine.
