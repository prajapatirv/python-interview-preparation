# Collections: HashMap internals, choosing the right structure, concurrent collections

> **Runnable:** [`01_hashmap_internals.java`](../examples/02_collections/01_hashmap_internals.java) ·
> [`02_collections_pitfalls.java`](../examples/02_collections/02_collections_pitfalls.java)
> **Crib sheet:** [`topics/01-java-core-collections-java8.md`](../topics/01-java-core-collections-java8.md) · **Guide:** Q5, Q9, Q10

## What interviewers are actually probing

"How does HashMap work?" is the most common Java question in existence, so it is a *depth filter*: they
keep asking "and then?" until you run out. The follow-ups are always the same family: what if `hashCode` is bad,
what if the key is mutable, what changed in Java 8, how does resize work, is it thread-safe, what do you use instead.

## Must-know points

- `HashMap` = array of buckets; index = `(n-1) & (h ^ (h >>> 16))`; default capacity 16, load factor 0.75, **resize ×2** when `size > capacity × 0.75`.
- Bucket collisions are a linked list; since Java 8 a bucket with ≥ 8 nodes (and table ≥ 64) becomes a **red-black tree** (O(log n)) and untreeifies at ≤ 6.
- `equals` and `hashCode` must agree: **equal objects ⇒ equal hash codes**. Break it and `get` returns `null` for a key you "just put".
- Keys should be **immutable**. Mutating a key after insertion strands the entry.
- `HashMap` is not thread-safe; use `ConcurrentHashMap` (and its atomic methods), not `Hashtable`/`synchronizedMap`.
- `ArrayList` for almost everything; `LinkedList` almost never; `ArrayDeque` for stacks/queues.
- Iterators are **fail-fast** (best-effort `ConcurrentModificationException`).

## Interview questions and full answers

### Q1. How does `HashMap` work internally?

`put(k, v)`:
1. compute `h = k.hashCode()`, spread it (`h ^ (h >>> 16)`) so high bits influence the low bits;
2. `index = (n - 1) & h` (works because `n` is a power of two);
3. if the bucket is empty, store a node; otherwise walk it comparing `hash` then `equals` — replace the value if found, else append;
4. if a chain reaches 8 and the table has ≥ 64 slots, treeify (otherwise resize);
5. if `++size > threshold` resize to double and redistribute (each node stays or moves by `oldCap`).

`get(k)` repeats steps 1–3. Average O(1); worst case O(log n) with trees (O(n) if keys are neither well hashed nor `Comparable`).

### Q2. Why is the capacity a power of two?

So the bucket index is a cheap bit-mask (`(n-1) & h`) rather than a modulo, and so resizing can split each bucket into "stays" and "moves by +oldCap" with a single bit test.
`new HashMap<>(10)` is rounded up to 16. If you know you'll hold N entries, size it as `N / 0.75 + 1` (or `HashMap.newHashMap(N)` in Java 19+) to avoid rehashing.

### Q3. What happens if two different keys have the same hash code? What if `hashCode` always returns 42?

They land in the same bucket and are distinguished by `equals`. A constant `hashCode` turns the map into one bucket: O(n) lookups (Java 7) or O(log n) if the key is `Comparable` (Java 8 tree bins).
Example 01 section 4 measures it: ~10× slower for 20,000 entries even with tree bins. The same weakness is the "hash flooding" denial-of-service vector, which is why untrusted keys must be well distributed.

### Q4. What breaks if you override `equals` but not `hashCode`?

`HashMap.get`/`HashSet.contains` look in the bucket from the **identity** hash, so a logically equal object usually isn't found, and `HashSet` stores "duplicates" (example 01 section 2).
Contract: reflexive, symmetric, transitive, consistent for `equals`; and equal objects must have equal `hashCode`. Use `Objects.equals/hash`, or a `record`, which generates both correctly.

### Q5. Why are `String` and `Integer` good keys? What is wrong with a mutable key?

They are immutable, so their hash is stable (`String` even caches it). If you mutate a field that participates in `hashCode` after insertion, the entry sits in the old bucket and `get` computes a new index: it is **in** the map (`size()`, iteration, `containsValue`) but unreachable — a silent leak (example 01 section 3).

### Q6. `HashMap` vs `Hashtable` vs `Collections.synchronizedMap` vs `ConcurrentHashMap`?

| | Thread-safe | Null key/value | Locking | Notes |
|---|---|---|---|---|
| `HashMap` | no | 1 null key, null values | – | default choice, single thread |
| `Hashtable` | yes | no | one lock on every method | legacy |
| `synchronizedMap` | yes | as wrapped | one mutex; iteration needs manual `synchronized` | simple wrapper |
| `ConcurrentHashMap` | yes | no nulls | per-bin CAS/`synchronized` (Java 8+), lock-free reads | atomic `merge/compute/putIfAbsent`, weakly consistent iterators |

`ConcurrentHashMap` is thread-safe **per operation**, not per sequence: `if (!m.containsKey(k)) m.put(k, v)` is still a race. Use `putIfAbsent`, `computeIfAbsent`, `merge` (example 02 section 5 shows lost updates with `get`+`put`).

### Q7. How does `ConcurrentHashMap` achieve concurrency in Java 8+?

The Java 7 segment locks were replaced by: lock-free reads via `volatile` reads of table cells; an empty bin is filled with a **CAS**; a non-empty bin is updated while holding `synchronized` on the **first node** of that bin (so contention is per bucket); `size()` is a striped counter (`CounterCell`s, like `LongAdder`). Resizing is cooperative: threads that touch the table help transfer bins.

### Q8. `ArrayList` vs `LinkedList`?

`ArrayList`: contiguous array, O(1) index, amortised O(1) append, O(n) middle insert but with excellent cache locality, so it usually beats `LinkedList` even for middle inserts at realistic sizes.
`LinkedList`: O(1) insert/remove *given an iterator position*, but O(n) to find that position, 24+ bytes per node and poor locality.
Use `ArrayDeque` for queue/stack semantics. Pre-size `ArrayList` when you know the size.

### Q9. What is fail-fast iteration, and how do you remove while iterating?

`ArrayList`/`HashMap` iterators check a `modCount`; structural modification from outside the iterator throws `ConcurrentModificationException` (best effort, not a guarantee).
Safe ways: `Iterator.remove()`, `Collection.removeIf(predicate)`, collecting into a second list, or a concurrent/copy-on-write collection (weakly consistent: no exception, may not see recent changes).

### Q10. `Arrays.asList` vs `List.of` vs `new ArrayList<>(...)`?

- `Arrays.asList(a)`: fixed-size **view** over the array; `set` writes through to the array; `add/remove` throw `UnsupportedOperationException`; allows `null`.
- `List.of(...)` (9+): truly immutable, rejects `null`, throws on any mutation; `contains(null)` also throws.
- `new ArrayList<>(coll)`: independent, mutable copy.
- `List.copyOf` (10+): immutable snapshot.

### Q11. `Comparable` vs `Comparator`, and what does "consistent with equals" mean?

`Comparable` is the natural order, implemented by the class; `Comparator` is an external order (compose with `comparing(...).thenComparing(...).reversed()`).
`TreeSet`/`TreeMap` use `compareTo`/`compare` for identity, **not** `equals`. If `compareTo == 0` for two objects that are not `equals`, a `TreeSet` drops one while a `HashSet` keeps both (example 02 section 4). Keep them consistent or document the difference.

### Q12. When do you use `CopyOnWriteArrayList`, `LinkedHashMap`, `PriorityQueue`, `EnumMap`?

- `CopyOnWriteArrayList`: read-mostly lists such as listener registries; every write copies the array.
- `LinkedHashMap(accessOrder=true)` + `removeEldestEntry`: a six-line LRU cache (example 02 section 3). Not thread-safe by itself.
- `PriorityQueue`: heap; `poll()` returns the min; **iteration order is not sorted**.
- `EnumMap`/`EnumSet`: array/bit-vector backed, fastest for enum keys.

### Q13. Design question: implement an LRU cache. What are the trade-offs?

**Option 1** — `LinkedHashMap` in access-order mode (above): shortest, O(1), single-threaded.
**Option 2** — `HashMap<K, Node>` + doubly linked list (the classic interview whiteboard): `get` moves the node to the head, `put` inserts at head and evicts the tail.
**Concurrency**: a single lock is fine to start; for high contention use a sharded map, or just use **Caffeine** (W-TinyLFU, size/time-based eviction, async refresh, stats). Say which you'd ship and why: *don't hand-roll caches in production*.

## A worked example

Run [`01_hashmap_internals.java`](../examples/02_collections/01_hashmap_internals.java):

1. Section 1 prints the bucket index for a few strings so you can explain `(n-1) & spread(h)` with real numbers.
2. Section 2 and 3 are the two classic bugs (missing `hashCode`, mutated key).
3. Section 4 times a constant `hashCode`. Then **EXPERIMENT**: remove `implements Comparable` from `BadKey` and re-run.

## Hands-on drills

1. Implement a minimal `HashMap<K,V>` with chaining and resize; add tree bins only if time permits.
2. Write a `record Money(BigDecimal amount, String currency)` and show it works as a map key; why is `double` a bad field for `equals`?
3. Count word frequencies with `HashMap.merge`, then with a stream `groupingBy(counting())`, then concurrently with `ConcurrentHashMap` + parallel stream.
4. Find the first non-repeating character using `LinkedHashMap`.
5. Explain why `Collections.sort` on a `LinkedList` copies to an array first.

## The 60-second spoken answer

"A HashMap is an array of buckets. The key's hash is spread and masked to pick a bucket, collisions form a linked list that
becomes a red-black tree at eight entries, and the table doubles at 75% load. It relies on `equals` and `hashCode` agreeing and on keys
being immutable. It isn't thread-safe; I use `ConcurrentHashMap` with its atomic `merge`/`computeIfAbsent`, not check-then-act.
For lists I default to `ArrayList`, and for a cache I'd use Caffeine rather than hand-rolling an LRU, though I can write
one with `LinkedHashMap` in access-order mode."
