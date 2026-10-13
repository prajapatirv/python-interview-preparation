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

Don't stop at "it uses hashing". The whole flow in one line:
**key → `hashCode()` → spread → bucket index → compare `hash` then `equals` → store / return value.**

**1. The structure.** A `Node<K,V>[] table` (always a power-of-two length). Each `Node` holds `int hash`, `K key`, `V value`, `Node next`.
Bucket = one slot in that array; a bucket holds a chain (linked list) or, since Java 8, a red-black tree.

```text
table[16]
 [0]  -> null
 [1]  -> (hash,"Ravi",100) -> (hash,"John",200)      <- collision: same bucket, linked by `next`
 [2]  -> null
 [3]  -> (hash,"Mike",300)
 ...
```

The table is **allocated lazily** on the first `put` (a `new HashMap<>()` costs almost nothing), default capacity 16, load factor 0.75.

**2. `put(k, v)` step by step.**

1. `h = k.hashCode()`, then **spread**: `h ^ (h >>> 16)`. A `null` key hashes to 0, so it lives in bucket 0 (that's how `HashMap` allows one null key).
2. `index = (n - 1) & h`. Because `n` is a power of two this equals `h mod n` without a division, but it only looks at the **low bits**, which is exactly why step 1 mixes the high bits down: otherwise hashes that differ only in the upper bits (floats, `Long`s, sequential-ish ids) would all collide.
3. Bucket empty -> drop a new node in. Otherwise walk the bin: for each node compare **`hash` first (cheap int compare), then `==`, then `equals`**. Found -> replace the value and return the *old* value (`put` returns it). Not found -> append at the tail.
4. Chain length reaches 8: if the table has **>= 64** slots the bin becomes a red-black tree, otherwise the map **resizes instead** (a small table with a long chain is fixed by more buckets, not a tree).
5. `++size > threshold` (`capacity * 0.75`) -> resize to **2x** and redistribute.

`get(k)` repeats steps 1-3 and returns the value (or `null`). `containsKey`, `remove`, `getOrDefault` all share that lookup.

**3. Why compare `hash` before `equals`?** `equals` can be expensive (long strings, deep objects). Two different hashes can never be equal keys, so a stored `int hash` rejects almost every non-match for free. That is also why **same `hashCode` does not mean same key**: `"Aa"` and `"BB"` both hash to 2112 and are still different keys, so both live in the same bucket.

**4. Resize and rehash.** Triggered when `size` crosses `capacity * loadFactor` (16 -> threshold 12, 32 -> 24, ...). A new array of double the size is allocated and every node moves. It is **not** a full recompute: because the new length is `oldCap * 2`, one extra bit of the hash decides the node's fate:

```text
(hash & oldCap) == 0  -> stays at index i
(hash & oldCap) != 0  -> moves to index i + oldCap       (relative order of the chain is preserved)
```

Resize is O(n) and stop-the-world for that map, so for a known size pre-size it: `new HashMap<>((int)(n / 0.75f) + 1)`, or `HashMap.newHashMap(n)` on Java 19+.

**5. Treeification (Java 8+).** Bin >= 8 nodes **and** table >= 64 -> `TreeNode`s (red-black tree ordered by hash, then `Comparable.compareTo` if the keys are the same `Comparable` class, then a tie-break on identity hash). Lookup in that bin drops from O(n) to O(log n). It shrinks back to a list at <= 6 nodes (the gap between 8 and 6 stops flip-flopping). It exists to defuse **hash-flooding DoS**: an attacker choosing colliding keys can no longer turn a map into an O(n) list. Normal operation never builds trees: with a good hash, bins stay at 0-2 nodes (Poisson distribution, the reason the threshold is 8).

**6. Complexity - say it precisely.**

| Operation | Average | Worst case |
|---|---|---|
| `get` / `put` / `remove` | O(1) | O(log n) with tree bins (keys `Comparable`); O(n) if not `Comparable` and badly hashed |
| Resize | O(n), amortised O(1) per `put` | - |
| Iteration | O(capacity + size) | - |

Don't claim "O(log n) after Java 8". It is O(1) on average; the tree only bounds the pathological bucket. Iteration cost depends on **capacity**, so a huge map you emptied is still slow to iterate. Iteration order is unspecified (use `LinkedHashMap` / `TreeMap` if order matters).

**7. The traps interviewers use to probe depth.**

- **Override `equals` without `hashCode`** -> equal keys hash to different buckets, `get` returns `null` (Q4).
- **Mutable key** mutated after insert -> entry stranded in the old bucket (Q5). Use immutable keys (`String`, `Integer`, `UUID`, a `record`).
- **Not thread-safe.** Java 7: concurrent resize could build a cyclic chain -> `get` spins at 100% CPU forever. Java 8 fixed the loop (tail insertion, order preserved) but still **loses updates and can corrupt state**. Use `ConcurrentHashMap` (Q6/Q7).
- **Modifying while iterating** -> `ConcurrentModificationException` (fail-fast `modCount`, Q9). Also never mutate the map from inside `computeIfAbsent`'s function (Java 9+ throws `CME`).
- **Boxing/memory**: each entry is a ~32-byte `Node` plus boxed key and value; a map of 10M `Integer -> Integer` is far heavier than two primitive arrays. Mention primitive-specialised collections (fastutil, Eclipse Collections) for hot paths.
- **`capacity` vs `size`**: `size` = entries, `capacity` = table length. `new HashMap<>(100)` -> capacity 128, not 100.

**8. How a Lead answers this (about 90 seconds, spoken).**

> "`HashMap` is an array of buckets, where each bucket holds a linked list that Java 8 upgrades to a red-black tree under heavy collision. On `put` it takes the key's `hashCode`, XORs the high 16 bits into the low 16 so they influence the index, and masks with `n - 1` - which works because capacity is always a power of two. If the bucket is empty it stores a node; otherwise it walks the bin comparing the stored hash first, then `equals`, replacing the value on a match or appending on a miss. When a bin reaches 8 entries and the table is at least 64 wide it treeifies; otherwise it resizes. When size passes capacity times load factor, 0.75 by default, the table doubles, and each node either stays or moves by exactly `oldCap`, decided by a single hash bit. That's why `get` and `put` are O(1) on average, and why the tree only guards the worst case. The things I watch for in production are keys that are mutable or missing `hashCode`, pre-sizing when I know the cardinality to avoid rehashing, and never sharing a plain `HashMap` across threads - I'd use `ConcurrentHashMap` and its atomic `merge` / `computeIfAbsent`."

**Follow-up ladder (what they ask next, in the order they usually ask):**

1. Why power-of-two capacity? -> Q2. 2. Same hash, different keys? / constant `hashCode`? -> Q3. 3. `equals` without `hashCode`? -> Q4. 4. Mutable key? -> Q5. 5. Thread-safety, `ConcurrentHashMap`? -> Q6, Q7. 6. How would you design a good key class? -> immutable, `equals`+`hashCode` over the same fields, cache an expensive hash like `String` does, or use a `record`.
One-line memory trick: **hashCode -> spread -> `(n-1) &` -> equals -> value; resize at 0.75; tree at 8 (and table >= 64).**

### Q2. Why is the capacity a power of two?

Three reasons, in the order to say them:
1. **Cheap index.** `(n-1) & h` is one AND instead of an integer modulo (division). For `n = 16`, `n-1 = 1111b`, so the AND keeps the low 4 bits of the hash. For a non-power-of-two such as 12, `n-1 = 1011b` has a zero bit, so bucket indexes with that bit set could never be produced: slots would sit permanently empty and collisions go up.
2. **Uniform use of every bucket.** A power-of-two mask is all ones, so every bucket is reachable. That is also why the hash is *spread* (`h ^ (h >>> 16)`): the mask only sees low bits.
3. **Cheap resize.** Doubling adds exactly one more mask bit, so each node either stays at `i` or moves to `i + oldCap`, decided by `(hash & oldCap)`. No hash is recomputed.

`new HashMap<>(10)` is rounded up to 16 (`tableSizeFor`); `new HashMap<>(100)` -> 128. If you will hold N entries, size it as `N / 0.75 + 1` (or `HashMap.newHashMap(N)` in Java 19+) so it never resizes.
**Contrast** (good follow-up): `Hashtable` uses prime sizes and `%`, which spreads poorly-hashed keys better but is slower, which is why `HashMap` chose bit-masking plus a spreading step instead.

### Q3. What happens if two different keys have the same hash code? What if `hashCode` always returns 42?

Same hash is a **collision, not a duplicate**: `"Aa".hashCode() == "BB".hashCode() == 2112`, yet they are different keys. They land in the same bucket and `HashMap` tells them apart by `equals`; both are kept.

If `hashCode` always returns 42 (legal, just terrible), every key goes to one bucket:
- Java 7: one linked list -> every `get`/`put` is O(n), the whole map is a list.
- Java 8+: the bin is treeified once there are 8+ nodes and the table is >= 64. If `BadKey implements Comparable`, ordering uses `compareTo` and lookups are O(log n). If it is **not** `Comparable`, the tree falls back to identity-hash tie-breaks and a lookup must search **both** subtrees, so it is still effectively O(n).

Example 01 section 4 measures it: ~10x slower for 20,000 entries even with tree bins. The same weakness is the **hash-flooding DoS**: an attacker posts form fields/JSON keys that all collide (Java's `String.hashCode` is easy to forge), CPU spikes. Tree bins are the mitigation; also cap parameter counts and prefer well-distributed keys for untrusted input.
Say this in the interview: *"same hash is allowed and handled by equals; the cost is performance, never correctness."*

### Q4. What breaks if you override `equals` but not `hashCode`?

Without an override, `hashCode` is the **identity** hash, so two logically equal objects (`new Employee(101)` twice) hash to different buckets. `get` goes to the wrong bucket and returns `null`; `HashSet.add` stores both, so you get "duplicates" (example 01 section 2). It only *sometimes* works (same bucket by luck), which makes it a nasty intermittent bug.

```java
Employee a = new Employee(101), b = new Employee(101);   // equals() overridden, hashCode() not
map.put(a, "Ravi");
map.get(b);            // null - b hashed to a different bucket than a
set.add(a); set.add(b);// size 2, although a.equals(b)
```

The contract (say all of it):
- `equals`: reflexive, symmetric, transitive, consistent, `x.equals(null)` is false.
- If `a.equals(b)` then `a.hashCode() == b.hashCode()`. The reverse need **not** hold (collisions are legal).
- `hashCode` must be stable between calls while the fields used by `equals` are unchanged.

Rules of thumb: derive both from the **same** fields; use `Objects.equals/hash`, a `record` (generates both correctly), or Lombok `@EqualsAndHashCode`. For JPA entities, base them on a business key or id carefully (a generated id is `null` before persist, so the hash changes after save).

### Q5. Why are `String` and `Integer` good keys? What is wrong with a mutable key?

**Good keys** (`String`, `Integer`, `Long`, `UUID`, enums, `record`s of immutable fields) are immutable, so the hash never changes; `String` even caches its hash after the first call, so repeated lookups are free.

**The mutable-key trap:**

```text
1. key.id = 1  -> hashCode 100 -> stored in bucket 4
2. key.id = 2  -> hashCode 200 (same object, field mutated)
3. map.get(key) -> looks in bucket 9 -> null   (the entry is still physically in bucket 4)
```

The entry is **in** the map (`size()`, iteration, `containsValue` all see it) but unreachable by key: you cannot `get` or `remove` it, so it is a silent memory leak (example 01 section 3). Same story for `HashSet` and for `TreeMap` keys whose compare fields change.
Fixes: immutable keys (final fields, defensive copies), or remove the entry, mutate, re-insert. Don't use JPA entities with generated ids as keys across `persist`.

### Q6. `HashMap` vs `Hashtable` vs `Collections.synchronizedMap` vs `ConcurrentHashMap`?

| | Thread-safe | Null key/value | Locking | Notes |
|---|---|---|---|---|
| `HashMap` | no | 1 null key, null values | – | default choice, single thread |
| `Hashtable` | yes | no | one lock on every method | legacy |
| `synchronizedMap` | yes | as wrapped | one mutex; iteration needs manual `synchronized` | simple wrapper |
| `ConcurrentHashMap` | yes | no nulls | per-bin CAS/`synchronized` (Java 8+), lock-free reads | atomic `merge/compute/putIfAbsent`, weakly consistent iterators |

`ConcurrentHashMap` is thread-safe **per operation**, not per sequence: `if (!m.containsKey(k)) m.put(k, v)` is still a race. Use `putIfAbsent`, `computeIfAbsent`, `merge` (example 02 section 5 shows lost updates with `get`+`put`).

### Q7. How does `ConcurrentHashMap` achieve concurrency in Java 8+?

**Evolution (say this first):** Java 7 split the map into 16 `Segment`s, each a `ReentrantLock`: concurrency was capped at the segment count and fixed at construction. Java 8 removed segments and locks **per bucket**, so concurrency scales with table size.

How Java 8+ works:
- **Reads take no lock.** Table cells and node `val`/`next` are `volatile`; a `get` just reads (so readers never block writers or each other).
- **Empty bin on `put`** -> fill it with a single **CAS**, no lock at all. This is the common fast path.
- **Non-empty bin** -> `synchronized` on the **first node** of that bin only. Writers to different buckets never contend; only same-bucket writers serialize.
- **Treeification** works per bin under that same lock; very long bins become `TreeBin`s with their own read/write lock.
- **`size()`** is a striped counter (`baseCount` + `CounterCell[]`, same idea as `LongAdder`), so counting doesn't make every writer fight over one field; `size()` is an estimate under concurrent change. Use `mappingCount()` for a `long`.
- **Resize is cooperative:** threads that hit a table being resized help transfer bin ranges (`ForwardingNode` marks moved bins), so resize doesn't stall everyone behind one thread.

**Why no nulls?** `get` returning `null` must unambiguously mean "absent"; a concurrent map can't use `containsKey` afterwards to disambiguate because the state may have changed in between.

**What it does not give you:** atomicity across calls. `check-then-put` is still a race: use `putIfAbsent`, `computeIfAbsent`, `merge`, `compute` (atomic per key; keep the function short and non-blocking because it runs under the bin lock). Iterators are weakly consistent: no `ConcurrentModificationException`, may or may not reflect concurrent updates.

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
