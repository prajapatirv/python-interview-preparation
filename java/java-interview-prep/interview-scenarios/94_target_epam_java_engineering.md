---
id: target-epam-java-engineering
title: Target company, EPAM Systems: core Java, live coding, engineering practices and Kafka
stack: java
skill: java-core
---
Part of the **target-company section** (hub: `../target-companies/README.md`, section "EPAM Systems").
EPAM candidates describe an HR contact, then one or more **technical interviews with an EPAM engineer** (sometimes the
first is run by a partner firm), then a manager/HR round. Two things stand out in reports:

- **Engineering craft, not just facts:** coupling vs cohesion, SOLID, design patterns, JUnit + Mockito, sometimes a
  take-home **TDD** exercise, and "walk me through the architecture of a large system you built".
- **Live coding in your own IDE while sharing the screen** (longest substring without repeating characters, a tree
  path problem, grouping numbers into ranges with Java 8). One candidate felt they were marked down for rushing:
  **talk through your reasoning, test edge cases, and use the time.**

Every answer has a **120-second** point-by-point version (*How I answer it*) and a **60-second answer**.

### Q1 [mid] Iterator vs ListIterator, and what does fail-fast mean?
tags: iterator, listiterator, fail-fast, fail-safe, concurrentmodificationexception, modcount, collections, epam

**Start here: the concepts**
- An **Iterator** walks any `Collection` forward: `hasNext()`, `next()`, `remove()`.
- A **ListIterator** works only on `List`, and can go **both directions** and modify in place: `previous()`, `add()`, `set()`, `nextIndex()`.
- **Fail-fast** iterators throw `ConcurrentModificationException` if the collection is structurally changed during iteration other than through the iterator itself.

**The live scenario (functional requirement)**
*FR: "Remove cancelled items from a cart before pricing."* A `for (Item i : items) if (i.cancelled()) items.remove(i);`
threw `ConcurrentModificationException` in production for carts with several cancelled items.

**What the interviewer is really checking**
The `modCount` mechanism, the correct ways to remove during iteration, and fail-fast vs fail-safe collections.

**How I answer it** (120-second answer, point by point)
1. **Iterator:** forward only, works on `List`, `Set`, `Queue`; `remove()` deletes the last returned element safely.
2. **ListIterator:** bidirectional, `add`/`set` at the cursor, index-aware; obtained with `list.listIterator()` (optionally from an index).
3. **Fail-fast mechanism:** `ArrayList`/`HashMap` keep a `modCount`; the iterator stores the expected value and checks it on each `next()`. A structural change from outside makes them differ, so it throws. It is **best effort**, not a guarantee, and exists to expose bugs.
4. **Correct removal:** `items.removeIf(Item::cancelled)` (Java 8, cleanest), or explicit `Iterator.remove()`, or collect into a new list with a stream.
5. **Fail-safe / weakly consistent:** `CopyOnWriteArrayList` iterates over a snapshot (never throws, sees no later changes); `ConcurrentHashMap` iterators are weakly consistent (never throw, may or may not see concurrent updates).
6. **Threading note:** CME happens in a single thread too; it is not a concurrency-control tool. Use concurrent collections or locks for real concurrent access.

**Trade-offs and what can go wrong**
- `CopyOnWriteArrayList` copies the array on every write: great for many reads and rare writes (listeners), terrible for frequent writes.
- Removing by index in a forward `for (int i...)` loop skips elements; iterate backwards or use `removeIf`.

**Follow-ups to expect**
- *Enumeration vs Iterator?* -> Enumeration is the legacy (Vector/Hashtable) read-only version with no `remove`.
- *Why doesn't the last-but-one removal throw?* -> Removing the second-to-last element makes `hasNext()` return false before the check runs; a classic quirk showing fail-fast is best effort.

**60-second answer**
"An Iterator goes forward over any collection and can remove the last element it returned. A ListIterator works only on
lists, goes both ways, and can add and set at the cursor. Fail-fast means collections like ArrayList and HashMap keep a
modification count, and the iterator throws ConcurrentModificationException if the collection changes outside the
iterator. That's what happens when you call list.remove inside a for-each loop, even in one thread. The fix is removeIf,
or Iterator.remove. Concurrent collections are different: CopyOnWriteArrayList iterates over a snapshot, and
ConcurrentHashMap is weakly consistent, so neither throws."

### Q2 [mid] How does Java compute a hash code, and how does HashMap use it?
tags: hashcode, string-hashcode, hash-spreading, objects-hash, records, hashmap, equals, epam

**Start here: the concepts**
- `hashCode()` returns an `int` used to pick a bucket in hash-based collections.
- `Object.hashCode()` by default is an identity-based number (not the memory address in modern JVMs); classes that define `equals` must override it consistently.
- `String.hashCode()` is computed from the characters with a polynomial: `s[0]*31^(n-1) + ... + s[n-1]`, and cached.

**The live scenario (functional requirement)**
*FR: "Deduplicate customer records by (country, taxId)."* A key class built `hashCode` as `country.length() + taxId.length()`,
so almost every key collided and the dedupe job took 40 minutes instead of 2.

**What the interviewer is really checking**
How hashes are actually built (31 multiplier, `Objects.hash`, records), how HashMap spreads them, and why a weak hash
hurts performance even when it is "correct".

**How I answer it** (120-second answer, point by point)
1. **String:** `h = 31 * h + c` over the characters. 31 is an odd prime and `31 * h == (h << 5) - h`, cheap to compute. The result is cached in the `String` object (strings are immutable).
2. **Your own classes:** combine fields the same way: `Objects.hash(country, taxId)` (convenient, allocates an array) or `31 * country.hashCode() + taxId.hashCode()` (fast). Records and IDE/Lombok generators do this for you.
3. **Contract:** equal objects -> equal hash codes; use the **same fields** as `equals`, and only immutable ones.
4. **HashMap spreading:** `hash = h ^ (h >>> 16)` mixes the high bits into the low bits, then `index = hash & (n - 1)`. Without that, keys that differ only in high bits would collide in small tables.
5. **Collisions:** stored in the same bucket as a list, turned into a red-black tree beyond 8 entries (table at least 64), so worst case O(log n).
6. **The bug in the scenario:** the length-based hash was legal but terrible: few distinct values -> huge buckets -> slow. Switching to `Objects.hash` restored O(1) lookups.

**Trade-offs and what can go wrong**
- Mutable fields in `hashCode` lose entries after a change.
- JPA entities: hashing a generated id that is null before persist changes the hash after save; use a business key or a constant hash with id-based equals.
- `Objects.hash` boxes primitives and creates an array on each call; fine usually, not in a hot path.

**Follow-ups to expect**
- *Can two different strings have the same hash?* -> Yes, for example "Aa" and "BB" both give 2112; `equals` resolves it.
- *Why is the HashMap capacity a power of two?* -> So `hash & (n - 1)` is a fast modulo and resizing splits buckets cleanly.

**60-second answer**
"For a String, Java computes 31 times the running hash plus each character, and caches the result because strings are
immutable. For my own classes I combine the same fields used in equals, with Objects.hash or 31 times one field plus the
next, and records do it automatically. HashMap then spreads the hash by XOR-ing in the high 16 bits and picks a bucket
with hash AND table size minus one. Collisions share a bucket, and large buckets become trees. A legal but weak hash
still hurts: I once saw a key hashed by field lengths, which made a dedupe job take 40 minutes instead of 2."

### Q3 [mid] Live coding: longest substring without repeating characters
tags: coding-round, sliding-window, hashmap, strings, live-coding, two-pointers, epam

**Start here: the concepts**
- A **sliding window** keeps a range `[left, right]` that always satisfies the rule (no repeats) and moves both ends forward.
- Store the **last index** of each character, so when a repeat appears, `left` can **jump** past it in one step.
- Target: O(n) time, O(k) space where k is the alphabet size.

**The live scenario (functional requirement)**
Reported by EPAM candidates as a live task in their own IDE with screen sharing: *"Given `abcabcbb`, return 3 (`abc`).
Given `pwwkew`, return 3 (`wke`)."*

**What the interviewer is really checking**
Communication while coding: brute force first, then the optimisation, clean code, edge cases and tests. Not speed.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** ASCII or Unicode? case-sensitive? return the length or the substring? empty input?
2. **Brute force out loud:** every substring and a set check, O(n^3) or O(n^2): too slow for long input.
3. **Sliding window:**
   ```java
   static int longestUnique(String s) {
       Map<Character, Integer> last = new HashMap<>();
       int best = 0, left = 0;
       for (int right = 0; right < s.length(); right++) {
           char c = s.charAt(right);
           Integer seen = last.get(c);
           if (seen != null && seen >= left) left = seen + 1;   // jump past the repeat
           last.put(c, right);
           best = Math.max(best, right - left + 1);
       }
       return best;
   }
   ```
4. **Walk through `abba`:** the `seen >= left` check stops `left` moving backwards when the old `a` is outside the window. This is the bug most people write.
5. **Tests I type before saying "done":** `""` -> 0, `"a"` -> 1, `"bbbb"` -> 1, `"abcabcbb"` -> 3, `"pwwkew"` -> 3, `"abba"` -> 2.
6. **Complexity:** O(n) time, O(min(n, alphabet)) space. For ASCII, an `int[128]` array instead of the map is faster.

**Trade-offs and what can go wrong**
- Forgetting the `seen >= left` guard gives wrong answers on `abba`.
- Rushing to a solution without tests; EPAM interviewers watch the process, so narrate and test.

**Follow-ups to expect**
- *Return the substring, not the length?* -> Track `bestStart` when updating `best`, return `s.substring(bestStart, bestStart + best)`.
- *At most k distinct characters?* -> Same window with a count map; shrink from the left while distinct > k.

**60-second answer**
"I'd clarify the character set and the output, mention brute force at O(n squared) or worse, then use a sliding window. I
keep a map from each character to its last index and a left pointer. For each right index, if the character was seen
inside the current window, I jump left to one past its last position. Then I record the index and update the best
length. The guard 'seen at or after left' matters, and abba is the test that proves it. It's O(n) time, and I'd use an
int array for ASCII. Before I say done I run empty, single character, all same, and the two examples."

### Q4 [mid] Java 8 coding: group a list of numbers into consecutive ranges
tags: coding-round, java8, streams, ranges, sorting, collectors, live-coding, epam

**Start here: the concepts**
- Input `[1, 2, 3, 7, 8, 10]` -> output `["1-3", "7-8", "10"]`.
- Ranges are about **neighbours**, so the data must be **sorted** and each element compared with the previous one. That is stateful, which streams are not designed for.
- A clean answer often mixes a simple loop with streams for the parts that are naturally declarative.

**The live scenario (functional requirement)**
An EPAM candidate reported "group numbers into ranges using Java 8". In a real system: *"Show seat numbers booked by a
group as compact ranges: 12-15, 18, 21-22."*

**What the interviewer is really checking**
That you know where streams fit and where they don't, handle duplicates and unsorted input, and keep the code readable.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** sorted? duplicates? negative numbers? output as strings or pairs?
2. **Normalise with streams:** `List<Integer> xs = input.stream().distinct().sorted().toList();`
3. **Group with a loop** (readable, O(n)):
   ```java
   List<String> ranges = new ArrayList<>();
   for (int i = 0; i < xs.size(); ) {
       int start = xs.get(i), j = i;
       while (j + 1 < xs.size() && xs.get(j + 1) == xs.get(j) + 1) j++;
       ranges.add(start == xs.get(j) ? "" + start : start + "-" + xs.get(j));
       i = j + 1;
   }
   ```
4. **Pure-stream variant if they insist:** group by `value - index` (consecutive numbers share the same difference):
   `IntStream.range(0, xs.size()).boxed().collect(groupingBy(i -> xs.get(i) - i, TreeMap::new, mapping(xs::get, toList())))`
   then map each group to `first-last`. Clever; I would explain the `value - index` trick.
5. **Complexity:** O(n log n) for the sort, O(n) for grouping.
6. **Tests:** empty list, a single number, all consecutive, none consecutive, unsorted with duplicates.

**Trade-offs and what can go wrong**
- Comparing `Integer` objects with `==` (`xs.get(j + 1) == xs.get(j) + 1`) is safe here only because the right side unboxes to `int`; comparing two `Integer`s directly would break above 127.
- Overly clever streams reduce readability; interviewers prefer clear code with a short explanation.

**Follow-ups to expect**
- *Streaming input that doesn't fit in memory?* -> Process a sorted stream once, keeping only the current start and previous value.
- *Return objects instead of strings?* -> A `record Range(int from, int to)` with a `toString`.

**60-second answer**
"I'd clarify sorting and duplicates, then use a stream to make the list distinct and sorted. For the grouping itself I'd
use a simple loop: start a range, extend it while the next number is the previous plus one, then emit 'start-end', or
just the number if the range has one element. That's O(n log n) because of the sort. If they want pure streams, the trick
is that consecutive numbers share the same value minus index, so you can groupingBy that difference into a TreeMap. I'd
test empty, single, all-consecutive and unsorted-with-duplicates input."

### Q5 [senior] Live coding: find the maximum path sum (optimal path) in a binary tree
tags: coding-round, binary-tree, recursion, dfs, max-path-sum, live-coding, epam

**Start here: the concepts**
- A **path** goes from any node to any node along parent-child links, each node used at most once; it can turn at most once (at its highest node).
- **Post-order DFS:** compute an answer for the children before the parent.
- Each call returns the best **downward** path from this node (one side only), while updating a global best that may use **both** sides.

**The live scenario (functional requirement)**
EPAM candidates mention "find the optimal path in a tree". The common version: *"Return the maximum path sum in a binary
tree whose node values may be negative."*

**What the interviewer is really checking**
Recursive thinking (what each call returns vs what it records), handling negatives, and complexity.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** any-node-to-any-node or root-to-leaf? negative values? empty tree?
2. **Key idea:** at each node, `gain(node) = node.val + max(0, gain(left), gain(right))` is what it can offer its parent (one branch). A path that **peaks** here is `node.val + max(0, gain(left)) + max(0, gain(right))`: update the global best with it.
3. **Code:**
   ```java
   private int best = Integer.MIN_VALUE;
   int maxPathSum(Node root) { gain(root); return best; }
   private int gain(Node n) {
       if (n == null) return 0;
       int l = Math.max(0, gain(n.left)), r = Math.max(0, gain(n.right));
       best = Math.max(best, n.val + l + r);
       return n.val + Math.max(l, r);
   }
   ```
4. **Negatives:** `max(0, ...)` drops a branch that would reduce the sum; `best` starts at `MIN_VALUE` so an all-negative tree returns its largest single node.
5. **Complexity:** O(n) time, O(h) stack space; a degenerate tree with 100k nodes could overflow the stack, so mention an iterative post-order for production.
6. **Root-to-leaf variant:** just return `val + max(gain(left), gain(right))` without the both-sides update, treating missing children carefully.

**Trade-offs and what can go wrong**
- Returning `l + r` to the parent is the classic bug: a parent cannot use both branches of a child.
- A mutable field for `best` is fine in an interview; in production return a small result object to stay thread-safe.

**Follow-ups to expect**
- *Return the path itself?* -> Track the nodes for the best peak, then rebuild left-down and right-down chains.
- *Weighted graph instead of tree?* -> Shortest path becomes Dijkstra (non-negative weights) or Bellman-Ford.

**60-second answer**
"I'd confirm it's any node to any node with possible negatives. Then a post-order DFS: each call returns the best
downward gain from that node, its value plus the better child gain, floored at zero so a negative branch is dropped. At
each node I also update a global best with value plus both child gains, because a path can peak there and use both
sides. The parent only ever receives one branch, which is the usual bug. Best starts at Integer.MIN_VALUE so an
all-negative tree works. It's O(n) time and O(height) stack, and I'd mention an iterative version for very deep trees."

### Q6 [senior] Explain coupling and cohesion, and how SOLID helps you get them right
tags: coupling, cohesion, solid, single-responsibility, dependency-inversion, design-principles, clean-code, epam

**Start here: the concepts**
- **Cohesion** = how closely the things inside one module belong together. Aim **high**: one reason to change.
- **Coupling** = how much one module depends on the internals of another. Aim **low**: change one without breaking the other.
- **SOLID** is a set of five principles that push code towards high cohesion and low coupling.

**The live scenario (functional requirement)**
*FR: "Generate monthly invoices."* An `InvoiceService` of 2,000 lines calculated taxes, built PDFs, sent emails and called
the payment provider's SDK directly. A change to the email template broke tax tests, and switching PDF libraries took a
sprint.

**What the interviewer is really checking**
That you can recognise bad coupling/cohesion in real code and fix it with concrete refactorings, not recite acronyms.

**How I answer it** (120-second answer, point by point)
1. **Diagnose:** low cohesion (four unrelated jobs in one class) and high coupling (direct dependency on SDK and PDF library classes).
2. **S, single responsibility:** split into `TaxCalculator`, `InvoicePdfRenderer`, `InvoiceMailer`, `PaymentGateway`; `InvoiceService` only orchestrates.
3. **O, open/closed:** tax rules per country as `TaxRule` strategies registered in a map; adding a country adds a class, no edits to existing ones.
4. **L, Liskov:** any `PaymentGateway` implementation must honour the same contract (no throwing "unsupported" for refunds).
5. **I, interface segregation:** reporting code depends on a small `InvoiceReader`, not on the whole service.
6. **D, dependency inversion:** the domain depends on its own `PaymentGateway` interface; an adapter wraps the vendor SDK. Swapping vendors touches one class. Spring injects the implementations.
7. **Result:** the PDF library swap took two days, tests per component run in milliseconds with simple fakes, and template changes no longer break tax tests.
8. **Package level:** organise by feature (`invoice`, `tax`), keep classes package-private where possible, and enforce dependency rules with ArchUnit.

**Trade-offs and what can go wrong**
- Over-applying SOLID creates many tiny interfaces with a single implementation; introduce an abstraction when there is a second implementation or a test seam you need.
- Splitting classes without changing dependencies only moves the coupling around.

**Follow-ups to expect**
- *Which principle matters most in practice?* -> Single responsibility and dependency inversion: they give testability and replaceable integrations.
- *How do you measure coupling?* -> Imports/dependency graphs, change coupling in git history (files that always change together), ArchUnit rules.

**60-second answer**
"Cohesion is how much a module's contents belong together, and I want it high. Coupling is how much a module depends on
another's internals, and I want it low. I once refactored a 2,000-line invoice service that calculated tax, built PDFs,
sent emails and called a payment SDK directly. Single responsibility split it into a calculator, a renderer, a mailer
and a gateway, with the service only orchestrating. Open/closed made tax rules pluggable strategies. Dependency
inversion put the payment SDK behind our own interface with an adapter. After that a PDF library swap took two days
instead of a sprint. I add abstractions when a second implementation or a test needs them, not by default."

### Q7 [mid] How do you test a Spring service with JUnit 5 and Mockito, and how do you work test-first?
tags: junit5, mockito, tdd, unit-testing, test-slices, testcontainers, assertj, spring-boot-test, epam

**Start here: the concepts**
- **Unit test:** one class, dependencies replaced by **mocks/fakes**, runs in milliseconds.
- **TDD:** red (write a failing test) -> green (simplest code that passes) -> refactor (clean up with tests protecting you).
- **Integration test:** real Spring context or real database (Testcontainers), slower, fewer of them.

**The live scenario (functional requirement)**
A reported EPAM take-home: *"Using TDD, implement a discount service: 10% off orders above 100, an extra 5% for loyalty
members, never more than 20%."*

**What the interviewer is really checking**
Test design (behaviour names, arrange-act-assert, edge cases), correct Mockito use, the test pyramid in Spring, and
whether you really drive design from tests.

**How I answer it** (120-second answer, point by point)
1. **First test (red):** `noDiscountAtOrBelow100()`: `assertThat(service.discount(order(100))).isEqualByComparingTo("0")`. Fails because the class doesn't exist.
2. **Green, then the next behaviour:** above 100 -> 10%; loyalty -> +5%; cap at 20%; boundary values 100, 100.01; null or negative totals rejected. Each test adds one rule; I refactor to a rule list when the `if`s get ugly.
3. **Mockito where there is a dependency:** `LoyaltyClient` is mocked: `when(loyalty.isMember("c1")).thenReturn(true)`; `verify(audit).record(any())` only when the interaction **is** the behaviour. Constructor injection makes this trivial: `new DiscountService(loyalty, audit)`, no Spring context.
4. **Readable tests:** `@DisplayName` or descriptive names, `@ParameterizedTest` with `@CsvSource` for the boundary table, AssertJ assertions, `BigDecimal` compared with `isEqualByComparingTo`.
5. **Spring layers:** `@WebMvcTest` + MockMvc for the controller (status, JSON, validation), with the service mocked via `@MockitoBean` (Boot 3.4+; `@MockBean` is deprecated and removed in Boot 4); `@DataJpaTest` + Testcontainers for repositories; one `@SpringBootTest` smoke test.
6. **Coverage as a signal:** JaCoCo in CI with branch coverage; mutation testing (PIT) on core rules if quality matters.

**Trade-offs and what can go wrong**
- Over-mocking (mocking value objects, verifying every call) gives tests that break on every refactor.
- `@SpringBootTest` everywhere makes the suite slow; most tests should not start a context.
- TDD with too-large steps stops being TDD; keep each cycle a few minutes.

**Follow-ups to expect**
- *Mock vs stub vs spy?* -> A stub returns canned answers; a mock also verifies interactions; a spy wraps a real object and overrides some methods (use sparingly).
- *How do you test time-dependent code?* -> Inject a `Clock` and use `Clock.fixed` in tests.

**60-second answer**
"I start with a failing test for the simplest rule, no discount at 100, make it pass, then add one behaviour at a time:
10 percent above 100, plus 5 for loyalty, a 20 percent cap, and the boundary values, refactoring into a rule list when
the ifs pile up. The loyalty client is a Mockito mock passed through the constructor, so no Spring context is needed, and
I only verify interactions that are the behaviour. I use parameterized tests for boundary tables and AssertJ. In Spring
I use WebMvcTest for controllers, DataJpaTest with Testcontainers for repositories, and one SpringBootTest smoke test."

### Q8 [mid] Executors and CompletableFuture: how do you run independent calls in parallel safely?
tags: multithreading, executorservice, completablefuture, thread-pool, timeouts, virtual-threads, concurrency, epam

**Start here: the concepts**
- An **ExecutorService** is a managed thread pool; you submit tasks instead of creating threads.
- **CompletableFuture** composes asynchronous results: `supplyAsync`, `thenApply`, `thenCombine`, `allOf`, `exceptionally`.
- Always pass **your own executor** for blocking I/O; the default common pool is sized for CPU work.

**The live scenario (functional requirement)**
*FR: "The customer dashboard needs profile, orders and recommendations from three services, under 400 ms."* Called one
after another they took 150 + 200 + 180 = 530 ms.

**What the interviewer is really checking**
Correct composition, timeouts and error handling per call, pool choice, and awareness of virtual threads.

**How I answer it** (120-second answer, point by point)
1. **Run in parallel:**
   ```java
   var profile = CompletableFuture.supplyAsync(() -> profiles.get(id), ioPool).orTimeout(300, MILLISECONDS);
   var orders  = CompletableFuture.supplyAsync(() -> orderClient.recent(id), ioPool).orTimeout(300, MILLISECONDS);
   var recs    = CompletableFuture.supplyAsync(() -> recClient.forUser(id), ioPool)
                     .completeOnTimeout(List.of(), 250, MILLISECONDS);
   CompletableFuture.allOf(profile, orders, recs).join();
   ```
   Total is roughly the slowest call (about 200 ms), not the sum.
2. **Per-call failure policy:** recommendations are optional (empty list on timeout); profile is mandatory (fail the request); `exceptionally`/`handle` per future decides.
3. **Pool:** a bounded `ThreadPoolExecutor` for I/O with a named thread factory and a bounded queue; never the common pool for blocking calls. On Java 21+, `Executors.newVirtualThreadPerTaskExecutor()` makes blocking calls cheap.
4. **Context:** MDC/trace ids and security context do not cross threads automatically; wrap tasks (or use Micrometer context propagation).
5. **Shutdown:** executors are Spring beans with `shutdown()` on close, so tasks are not lost on redeploy.
6. **Result:** p99 from 530 ms to 230 ms.

**Trade-offs and what can go wrong**
- `get()` without a timeout can block forever; `join()` throws unchecked `CompletionException` wrapping the cause.
- An unbounded queue hides overload until memory runs out; a bounded queue with a rejection policy fails visibly.
- Parallel calls triple the instantaneous load on downstream services.

**Follow-ups to expect**
- *thenApply vs thenCompose?* -> `thenApply` maps a value; `thenCompose` chains another future (like flatMap).
- *Structured concurrency?* -> `StructuredTaskScope` (preview through Java 25) cancels sibling tasks when one fails and ties lifetimes to a scope.

**60-second answer**
"I'd start the three calls with supplyAsync on a dedicated, bounded I/O pool, never the common pool, and combine them
with allOf, so the latency is the slowest call, not the sum. Each future gets its own timeout and failure policy:
recommendations fall back to an empty list with completeOnTimeout, while a missing profile fails the request. I
propagate MDC and trace context into the tasks and shut the executor down cleanly. On Java 21 virtual threads make this
simpler. In one dashboard this took p99 from 530 to about 230 milliseconds."

### Q9 [mid] Kafka: how many consumers in a group receive a message, what happens with multiple groups, and how do keys and DLQs work?
tags: kafka, consumer-group, multiple-groups, message-key, partitioning, dlq, dead-letter-topic, spring-kafka, epam

**Start here: the concepts**
- Within one **consumer group**, each message is delivered to **exactly one** consumer (the one assigned that partition).
- **Different groups** are independent: **every group** receives every message, with its own offsets.
- The **key** decides the partition (`hash(key) % partitions`), so same key = same partition = ordered.
- A **DLQ / dead-letter topic** holds messages that keep failing, so they don't block the partition.

**The live scenario (functional requirement)**
*FR: "An `OrderPlaced` event must update inventory and also send a confirmation email."* Inventory and email are two
consumer groups on the same topic; each scales independently.

**What the interviewer is really checking**
Exact answers to the questions candidates reported (one consumer per group, all groups), plus practical key and DLQ
design in Spring Kafka.

**How I answer it** (120-second answer, point by point)
1. **One group:** one consumer per message. With 6 partitions and 3 consumers, each gets 2 partitions; a 7th consumer on a 6-partition topic sits idle.
2. **Many groups:** `inventory-service` and `email-service` both read every event; their offsets are independent, so a slow email consumer never delays inventory.
3. **Keys:** key by `orderId` so all events of an order stay in order; a null key spreads messages across partitions (sticky partitioner), with no ordering between them.
4. **Failure handling in Spring Kafka:** `DefaultErrorHandler` with `FixedBackOff`/`ExponentialBackOff` for in-place retries, then `DeadLetterPublishingRecoverer` publishes to `orders.DLT` with headers (original topic, partition, offset, exception). Non-retryable exceptions (validation, deserialization via `ErrorHandlingDeserializer`) go straight to the DLT.
5. **Non-blocking retries:** `@RetryableTopic` creates retry topics with delays, so the main partition keeps flowing (at the cost of strict ordering for retried records).
6. **DLT handling:** monitored, alerted, a tool to inspect and replay after a fix; idempotent consumers make replay safe.

**Trade-offs and what can go wrong**
- Retry topics break ordering per key; for strictly ordered flows retry in place or park later events for that key.
- A DLT nobody watches is silent data loss.
- Too many partitions for a small topic increases rebalance time and broker overhead.

**Follow-ups to expect**
- *What triggers a rebalance?* -> A consumer joining/leaving, `max.poll.interval.ms` exceeded, or partition count changes.
- *How do you replay from the start for a new group?* -> `auto.offset.reset=earliest` for a new group id, within topic retention.

**60-second answer**
"Inside one consumer group each message goes to exactly one consumer, the one owning that partition, so consumers beyond
the partition count sit idle. Different groups are independent: each group gets every message with its own offsets, so
inventory and email can both consume OrderPlaced and scale separately. The key picks the partition, so keying by order
id keeps an order's events in sequence. For failures, Spring Kafka's DefaultErrorHandler retries with backoff and then
the DeadLetterPublishingRecoverer sends the record to a DLT with the original topic, offset and exception in headers.
Bad data goes straight there. The DLT is monitored and replayable, and consumers are idempotent."

### Q10 [mid] How does Spring Security work, and how do you secure a REST API with it?
tags: spring-security, filter-chain, securityfilterchain, authentication, authorization, jwt, method-security, csrf, epam

**Start here: the concepts**
- Spring Security is a **chain of servlet filters** that runs before your controllers.
- **Authentication** builds an `Authentication` object (who) stored in the `SecurityContext`; **authorisation** checks it against rules (what).
- Configuration today is a `SecurityFilterChain` bean (the old `WebSecurityConfigurerAdapter` was removed in Spring Security 6).

**The live scenario (functional requirement)**
*FR: "A REST API for internal admins and partner systems: admins manage products, partners only read their own
catalogue; tokens come from the company identity provider."*

**What the interviewer is really checking**
The filter-chain mental model, a correct stateless configuration for APIs, URL vs method security, and common mistakes.

**How I answer it** (120-second answer, point by point)
1. **Request flow:** `DelegatingFilterProxy` -> `FilterChainProxy` -> filters such as `BearerTokenAuthenticationFilter` -> `AuthorizationFilter` -> controller. Failures go to the `AuthenticationEntryPoint` (401) or `AccessDeniedHandler` (403).
2. **Configuration:**
   ```java
   @Bean SecurityFilterChain api(HttpSecurity http) throws Exception {
       return http.csrf(c -> c.disable())   // stateless token API, no browser session cookies
           .sessionManagement(s -> s.sessionCreationPolicy(STATELESS))
           .authorizeHttpRequests(a -> a.requestMatchers(HttpMethod.GET, "/catalogue/**").hasAuthority("SCOPE_catalogue.read")
                                        .requestMatchers("/admin/**").hasRole("ADMIN")
                                        .anyRequest().authenticated())
           .oauth2ResourceServer(o -> o.jwt(Customizer.withDefaults()))
           .build();
   }
   ```
3. **Method security:** `@EnableMethodSecurity` and `@PreAuthorize("@catalogueAccess.owns(authentication, #partnerId)")` for ownership rules that URLs cannot express.
4. **Mapping claims:** a `JwtAuthenticationConverter` maps a `roles` claim to `ROLE_` authorities.
5. **CSRF:** disable only for stateless bearer-token APIs; keep it for cookie-based browser sessions.
6. **Passwords (if local users exist):** `BCryptPasswordEncoder`/`DelegatingPasswordEncoder`, never plain text.
7. **Testing:** MockMvc with `.with(jwt().authorities(...))` to assert 401/403/200 per role.

**Trade-offs and what can go wrong**
- Rule order matters: `anyRequest()` must be last, and a broad `permitAll()` early opens everything after it.
- `hasRole("ADMIN")` expects the authority `ROLE_ADMIN`; mixing roles and authorities causes silent 403s.
- Forgetting ownership checks gives every partner access to every catalogue (broken object-level authorisation).

**Follow-ups to expect**
- *Where is the SecurityContext stored?* -> In a `ThreadLocal` via `SecurityContextHolder` for the request thread; it doesn't propagate to async threads automatically.
- *Session vs token?* -> Sessions suit server-rendered web apps; stateless tokens suit APIs and horizontal scaling.

**60-second answer**
"Spring Security is a chain of filters in front of the controllers. One filter authenticates, for an API usually by
validating a bearer JWT, and puts an Authentication into the SecurityContext. Then the authorization filter checks the
rules. I configure a SecurityFilterChain bean: stateless sessions, CSRF off only because it's a token API, URL rules by
scope and role, anyRequest authenticated last, and oauth2ResourceServer with JWT. Ownership rules go into @PreAuthorize
with method security. 401 versus 403 comes from the entry point and the access-denied handler, and I test each role with
MockMvc and the jwt post-processor."

### Q11 [senior] Walk me through the architecture of a large system you worked on
tags: architecture-walkthrough, system-design, project-deep-dive, trade-offs, scalability, behavioural-technical, epam

**Start here: the concepts**
- This is a **project deep dive**: the interviewer uses your system to test design judgement, depth and honesty.
- Structure beats detail: **context -> numbers -> architecture -> your part -> hard problems -> what you'd change**.
- Expect them to drill into any box you draw; only draw what you can defend.

**The live scenario (functional requirement)**
EPAM candidates report "the architecture of a large system" questions. Prepare one system you know end to end, for
example: *"A loyalty and rewards platform: 8 million members, 1,500 requests/s at peak, points earned from card
transactions via Kafka, redeemed through REST APIs."* (Replace with your own.)

**What the interviewer is really checking**
Whether you understand **why** the system is shaped the way it is, what **you** owned, real numbers, and trade-offs you
would revisit.

**How I answer it** (120-second answer, point by point)
1. **Context in one sentence:** business purpose, users, and why it matters (revenue, regulation).
2. **Numbers:** users, peak RPS, events/day, data size, latency SLO, availability target.
3. **Architecture (draw it):** clients -> gateway -> 6-8 Spring Boot services on Kubernetes -> PostgreSQL per service + Redis -> Kafka for transaction events -> batch/analytics. Name the key data flows: earn (async) and redeem (sync with a saga).
4. **My part:** "I owned the earn pipeline and the redemption API: design, implementation, performance tuning and on-call."
5. **Two hard problems and how we solved them:** duplicate card events (idempotent consumer with a processed-event table); peak redemption during promotions (cache plus connection-pool tuning, autoscaling on Kafka lag via KEDA).
6. **Quality and operations:** contract tests, Testcontainers, canary releases, dashboards and alerts by SLO.
7. **What I would change:** for example, "we started with a shared database for two services, and splitting it later was painful; I'd separate data from day one."
8. **Close with impact:** "p99 down from 900 to 250 ms, zero duplicate credits since go-live."

**Trade-offs and what can go wrong**
- Drawing a textbook architecture you didn't build collapses under the second follow-up; describe the real one, including its flaws.
- Saying "we" for everything hides your contribution; say "I" for your decisions.
- Confidential details: describe patterns and numbers in rounded form, never client names or secrets you are not allowed to share.

**Follow-ups to expect**
- *Why Kafka there and not REST?* -> Have the real reason (fan-out to several consumers, buffering bank peaks, replay).
- *What breaks first at 10x load?* -> Name the real bottleneck (database writes, a partner API) and the plan.
- *What was the worst incident?* -> One short STAR story with the RCA and the prevention.

**60-second answer**
"I'll take the loyalty platform I worked on: around 8 million members and 1,500 requests a second at peak. Card
transactions arrive through Kafka and earn points asynchronously, and redemptions are synchronous REST calls coordinated
by a saga. It runs as about eight Spring Boot services on Kubernetes, with PostgreSQL per service and Redis for hot
reads. I owned the earn pipeline and the redemption API. The two hard problems were duplicate card events, solved with
idempotent consumers, and promotion peaks, solved with caching, pool tuning and KEDA autoscaling on lag. If I did it
again, I'd separate the databases from day one. The result was p99 from 900 to 250 milliseconds and no duplicate
credits."
