# Coding interview round: Java 8 programs, data structures, DI, JWT and idempotency

> **Runnable (all self-checking, exit 0):**
> [`01_strings_and_arrays.java`](../examples/21_coding_interview/01_strings_and_arrays.java) ·
> [`02_java8_stream_coding_questions.java`](../examples/21_coding_interview/02_java8_stream_coding_questions.java) ·
> [`03_linked_list_tree_graph.java`](../examples/21_coding_interview/03_linked_list_tree_graph.java) ·
> [`04_design_coding_lru_idempotency_concurrency.java`](../examples/21_coding_interview/04_design_coding_lru_idempotency_concurrency.java) ·
> [`05_dependency_injection_and_token_auth.java`](../examples/21_coding_interview/05_dependency_injection_and_token_auth.java) ·
> [`06_java_output_trap_questions.java`](../examples/21_coding_interview/06_java_output_trap_questions.java)
> **Related:** [01 Java 8](01_java8_core.md) · [02 Collections](02_collections.md) · [04 Concurrency](04_concurrency.md) · [06 Spring core](06_spring_core.md) · [08 REST](08_rest_api.md) · [10 Security](10_spring_security.md)

## What interviewers are actually probing

A coding round for an experienced Java developer is not a puzzle contest. After the first two minutes
the interviewer already knows whether you can solve "reverse a linked list". What they are scoring:

1. **Do you clarify before typing?** Input size, nulls, duplicates, sorted or not, memory limit.
2. **Do you pick the right structure and say the complexity?** "HashMap, O(n) time, O(n) space; the
   brute force is O(n^2)" is the sentence they wait for.
3. **Is the code production-shaped?** Null handling, no int overflow, no mutation of the caller's
   input, names that read, and a way to test it.
4. **Do you find your own bugs?** Walk an edge case through the code out loud before they do.
5. **For 5-10+ years: can you write the *component*,** not only the algorithm: an LRU cache, a
   thread-safe singleton, an idempotent POST handler, a rate limiter. This is where most
   experienced candidates lose marks.

The reference list you gave (52 problems in three bands: freshers, 2-3 years, 5-10+ years) is mapped
below. The 5-10+ band is almost entirely data structures, concurrency and design-coding, which is why
files 03 and 04 exist.

## Must-know points

- **Say the complexity every time.** Time *and* space, and what the input-size assumption is.
- **The five patterns cover most problems:** hash map for lookup / frequency, two pointers,
  sliding window, stack/queue (BFS = queue, DFS = stack or recursion), sort-then-scan.
- **`HashMap` is the default tool**, `LinkedHashMap` when order matters, `TreeMap` when sorted keys matter,
  `ArrayDeque` for stack and queue (not `Stack`, not `LinkedList`).
- **Java 8 stream answers should end in a terminal operation you can explain**; know `groupingBy`,
  `partitioningBy`, `toMap` (and its duplicate-key exception), `flatMap`, `joining`, `reduce`.
- **Java is pass-by-value**, always. For objects the *value* is the reference.
- **`equals` and `hashCode` go together**; `Integer` caches -128..127; strings are immutable and pooled.
- **Concurrency answers need a happens-before story:** `volatile` for visibility, `synchronized` /
  `Lock` for atomicity, `Atomic*` / `ConcurrentHashMap` for lock-free building blocks.

## How to run the round (the 6-step script)

| Step | Say / do | Example for "first non-repeating character" |
|---|---|---|
| 1 Clarify | input, edge cases, constraints | "ASCII or Unicode? Case-sensitive? What do I return if none?" |
| 2 Brute force | name it and its cost | "Nested loops, O(n^2). Works, but not what I would ship." |
| 3 Improve | the structure that removes the cost | "Count in a `LinkedHashMap`, then scan: O(n) time, O(k) space." |
| 4 Code | small named methods, no clever tricks | |
| 5 Test aloud | empty, one element, all same, all different, null | `"aabb"` returns null, handled as `Character` not `char` |
| 6 Extend | the likely follow-up | "For a stream I would keep counts and an insertion-ordered set of candidates." |

## Pattern table: recognise the problem, name the technique

| The problem says... | Reach for | Cost | Example in the files |
|---|---|---|---|
| "find pair / complement / seen before" | `HashMap` / `HashSet` | O(n) | `twoSum`, duplicates |
| "longest / shortest substring or subarray with a property" | sliding window | O(n) | `longestUniqueSubstring` |
| "sorted array, find / merge / dedupe" | two pointers, binary search | O(n) / O(log n) | `mergeSorted`, `binarySearch` |
| "best contiguous sum" | Kadane (running best) | O(n) | `maxSubarray` |
| "group by X" | `groupingBy` / map of lists, canonical key | O(n) | `groupAnagrams` |
| "cycle / middle / kth from end" | slow-fast pointers, gap pointers | O(n), O(1) | `hasCycle`, `removeNthFromEnd` |
| "level by level / shortest path unweighted" | BFS with a queue | O(V+E) | `levelOrder` |
| "all combinations / permutations" | backtracking | exponential | `permutations` |
| "connected regions / flood" | DFS on a grid | O(R*C) | `numIslands` |
| "ordering with dependencies / is there a cycle" | topological sort or 3-colour DFS | O(V+E) | `topoOrder` |
| "most recent / least recent N items" | `LinkedHashMap` access order or map + doubly linked list | O(1) | `LruManual` |
| "exactly once under concurrency" | atomic reservation (`putIfAbsent`), not check-then-act | | `IdempotentHandler` |

## Interview questions and full answers

### Q1. (V. IMP.) What is Dependency Injection and how do you implement it?

**Dependency Injection is a design technique where an object receives the collaborators it needs from
the outside instead of creating them itself.** Inversion of Control is the principle (the framework, not
your code, controls object creation and wiring); DI is the mechanism that implements it.

Why it exists:

- **Replaceable:** swap a real payment gateway for a fake in a test, or one implementation for another in
  production, without editing the consumer.
- **Explicit:** the constructor signature documents what the class needs.
- **Lifecycle managed by one owner:** the container decides singleton vs per-request scope, creation
  order and shutdown.

Without DI (`OrderServiceHardWired` in file 05) the class does `new RealGateway()` itself, so no test
can ever substitute the gateway. With DI the same class takes `PaymentGateway` in its constructor and a
test passes a lambda.

**How you implement it** is three layers, and you should be able to describe all three:

1. **Plain Java, no framework (manual DI):** write constructors that take interfaces and wire them in a
   `main` or a configuration class ("composition root"). This is perfectly valid and is how you explain DI
   without Spring.
2. **A container:** register how to build each type, resolve the graph, cache singletons, detect cycles.
   `MiniContainer` in file 05 is 12 lines and does exactly that.
3. **Spring:** the container scans `@Component` / `@Service` / `@Repository` classes and `@Bean`
   methods, builds a bean definition graph, instantiates singletons at startup, injects through the
   constructor (or setter / field), then applies `BeanPostProcessor`s (this is where AOP proxies for
   `@Transactional` appear).

```java
@Service
class OrderService {
    private final PaymentGateway gateway;     // final: cannot be reassigned
    private final Notifier notifier;

    OrderService(PaymentGateway gateway, Notifier notifier) {   // single constructor: @Autowired is optional since Spring 4.3
        this.gateway = gateway;
        this.notifier = notifier;
    }
}
```

> Follow-up they may ask: "Is DI the same as a Factory?" No. A factory is *called* by the consumer, which
> still knows the factory. With DI the consumer does not look anything up; the dependency arrives.

### Q2. (V. IMP.) When do you use which type of dependency injection?

| Type | How | Use it when | Do not use it when |
|---|---|---|---|
| **Constructor** | dependencies are constructor parameters | **default**: every *mandatory* dependency | the class has 6+ parameters (that is a design smell: split the class, do not switch injection type) |
| **Setter** | `setX(...)` called after construction | the dependency is genuinely **optional**, has a sensible default, or must be re-assignable (rare) | you rely on it being present; a half-built object is legal to construct |
| **Field** | `@Autowired` directly on a field | essentially **never in production code**; tolerable in throw-away tests and demos | anywhere you want a unit test with plain `new`, immutability, or visible dependencies |
| **Method / interface** | `@Bean` parameters, `ObjectProvider<T>`, `Provider<T>` | lazy or per-call lookup, e.g. a prototype bean needed inside a singleton | the dependency is always needed |

What file 05 proves, so you can say it with evidence:

- **Constructor:** `new OrderServiceCtor(null, spy)` fails *at construction* with a clear message.
  The object can never exist half-built. Fields are `final`, so the class is effectively immutable and
  thread-safe to share.
- **Setter:** `new OrderServiceSetter().checkout(1)` throws `NullPointerException` *at first use*,
  possibly in production, long after startup.
- **Field:** the test cannot supply the dependency without `setAccessible(true)` reflection or a
  Spring test context. That is the practical reason teams ban it.
- **Cycles:** constructor injection turns a circular dependency into a *startup* failure
  (`A -> B -> A`). Setter/field injection used to hide the cycle with early references; Spring Boot 2.6+
  forbids that by default. A cycle is a design problem: extract the shared part or use an event.

The 20-second spoken answer: "Constructor injection for everything required, because it is explicit,
final and testable without Spring. Setter injection only for truly optional collaborators with a default.
Field injection I avoid: it hides dependencies and forces reflection in tests. If a constructor gets long,
I split the class, not change the injection style."

Related traps: two beans of one type -> `@Primary` or `@Qualifier`; a **prototype bean injected into a
singleton** is created once (use `ObjectProvider` or `@Lookup`); `@Autowired` on a `List<Handler>` injects
*all* implementations, which is how you build strategy registries without an `if` chain.

### Q3. (V. IMP.) What is token-based authentication, and what is JWT?

**Token-based authentication means that after login the server hands the client a signed, time-limited
token, and the client presents it on every request; the server verifies the token instead of looking up
a server-side session.** JWT (JSON Web Token) is the most common token format.

Session vs token:

| | Server session (cookie + session id) | Token (JWT in `Authorization: Bearer`) |
|---|---|---|
| State | **server remembers** (memory / Redis) | **stateless**: all claims are inside the token |
| Scaling | needs sticky sessions or a shared store | any instance verifies with the key, no lookup |
| Revocation | trivial: delete the entry | hard: valid until `exp` unless you add a deny-list |
| Cross-service / mobile / SPA | awkward (cookies, CORS) | natural: one token, many services |
| Main risk | CSRF (cookie sent automatically) | XSS if stored in `localStorage`; token theft = replay until expiry |

**A JWT is three base64url parts separated by dots: `header.payload.signature`.**

- **Header:** `{"alg":"HS256","typ":"JWT"}` which algorithm signed it.
- **Payload (claims):** `sub` (subject), `iat`/`exp` (issued-at/expiry), `iss`, `aud`, plus roles.
- **Signature:** `HMAC-SHA256(base64(header) + "." + base64(payload), secret)` (or an RSA/ECDSA signature
  with a private key).

Three things people get wrong, all demonstrated in file 05:

1. **Signed is not encrypted.** The payload is only base64: anyone holding the token can read it. Never
   put secrets or PII in it. (Use JWE if you truly need encryption.)
2. **The signature gives integrity, not revocation.** Change `role` from `ADMIN` to `SUPERUSER` and
   verification fails (`bad signature`), but a *legitimately issued* token stays valid until `exp`.
3. **Verify in the right order:** allow-list the algorithm first (the `alg=none` attack sends an unsigned
   token and hopes the library accepts it; also the HS256-vs-RS256 key-confusion attack), then verify
   the signature in constant time (`MessageDigest.isEqual`), then check `exp` / `iss` / `aud`, and only
   then trust the claims.

How you make it production-safe: short access token (5-15 minutes); a **refresh token** that is rotated on
use and stored server-side so it *can* be revoked; HTTPS only; `HttpOnly; Secure; SameSite` cookie
rather than `localStorage` for browser apps; RS256/ES256 with a published JWKS for multi-service
setups so downstream services hold only the public key; a small deny-list (by `jti`) for emergency
revocation; clock-skew leeway of a few seconds.

In Spring: `spring-boot-starter-oauth2-resource-server` with `.oauth2ResourceServer(o -> o.jwt(...))`
validates the signature, `exp`, `iss` and maps claims to authorities. See
[10 Spring Security, Q3-Q6](10_spring_security.md).

> Follow-up they may ask: "How do you log a user out with JWT?" Delete the client copy, revoke the
> refresh token server-side, and let the short-lived access token expire; add the `jti` to a deny-list
> only when you must cut access immediately.

### Q4. (V. IMP.) How do you make a REST POST idempotent? (the `Idempotency-Key` pattern)

**An operation is idempotent if repeating it has the same effect as doing it once.** `GET`, `PUT`,
`DELETE` are idempotent *by definition*; `POST` is not, which is exactly the payment/order case where a
client times out and retries and the customer is charged twice.

The pattern: the client generates a unique key per *logical* operation and sends it in an
`Idempotency-Key` header; the server stores the key with the response and replays it for duplicates.

Rules the implementation in file 04 enforces (and what to say in an interview):

1. **Reserve the key atomically.** `putIfAbsent` / `computeIfAbsent` (or a unique constraint in the DB).
   `if (!map.containsKey(k)) map.put(k, ...)` is a race: two threads both pass the check and both charge.
2. **Same key + same body -> replay the stored response** (same status and body) and do **not** run the
   business logic again.
3. **Same key + different body -> `422`**. It is a client bug; silently accepting it hides data corruption.
4. **Concurrent duplicates wait for the first** (the entry holds a `CompletableFuture`), they do not
   all run and they do not fail. File 04 fires 50 simultaneous requests: 1 execution, 50 identical
   responses.
5. **A failed first attempt must not poison the key**: release it so the retry can run.
6. **Expire keys** (24 h is typical) so the store does not grow forever.
7. **Missing key -> `400`** for endpoints that require it.

Production variants: store in a table with `UNIQUE(key)` and do the insert in the *same transaction* as
the business write (so "charged but key not saved" cannot happen), or `SET key value NX EX 86400` in Redis
for the reservation. Downstream, also make the consumer idempotent (Kafka at-least-once delivery means
duplicates are normal): a natural business key + unique index, or a processed-message-id table.

`PUT` for create-with-client-id is the other answer: `PUT /orders/{uuid}` is idempotent without any
header.

> Follow-up they may ask: "Idempotent vs safe?" Safe = no state change (GET, HEAD). Idempotent = same
> final state when repeated (PUT, DELETE, and safe methods). Idempotent methods may still change state once.

### Q5. Reverse a string / check palindrome / check anagram without library shortcuts.

Reverse: swap `chars[i]` and `chars[j]` while `i < j`, O(n) time and O(n) space (a `String` is immutable,
so you need a `char[]`). Palindrome: two pointers from both ends, skip non-alphanumerics, compare
case-insensitively, O(n) time and O(1) extra space. Anagram: a 26-slot frequency array (increment for one
string, decrement for the other, all zeros means anagram), O(n) vs O(n log n) for sorting.

Traps: `null` and empty input; Unicode (`char` is a UTF-16 unit, use code points for emoji);
`StringBuilder.reverse()` is the one-liner but the interviewer banned it for a reason.

### Q6. First non-repeating character; longest substring without repeating characters.

First non-repeating: `LinkedHashMap<Character,Integer>` (insertion-ordered) counted in one pass, then
the first entry with count 1. Return type is `Character`, not `char`, so "none" is `null`.

Longest unique substring: **sliding window** with `Map<Character,Integer>` of last-seen index; when a
repeat is inside the window move `start` to `lastIndex + 1`. The famous bug is on `"abba"`: when you see
the second `a`, its old index is *outside* the window and must be ignored, so the condition is
`prev >= start`. O(n) time. Both are in file 01.

### Q7. Two sum, missing number, maximum subarray, sort 0/1/2.

- **Two sum:** one pass, `HashMap<value, index>`, look up `target - x`. O(n). Brute force is O(n^2).
- **Missing number 1..n:** `n(n+1)/2 - sum`. Use `long`: for n above about 65,000 the product overflows
  `int`. XOR of all indices and values is the overflow-free alternative.
- **Kadane:** `cur = max(a[i], cur + a[i])`, `best = max(best, cur)`. Initialise from `a[0]`, not `0`, or an
  all-negative array returns the wrong answer.
- **Dutch national flag:** three pointers, one pass, O(1) space. After swapping with `hi` do **not**
  advance `mid`: the swapped-in value has not been examined.

### Q8. Merge two sorted arrays / binary search / rotate an array / remove duplicates in place.

Two pointers each. Binary search: `mid = lo + (hi - lo) / 2` (the `(lo + hi) / 2` form overflows for large
arrays; this bug lived in the JDK for years). Rotate right by k: reverse all, reverse first k, reverse the
rest, in O(1) space; remember `k %= n`. In-place dedupe of a *sorted* array: a write pointer that only
advances when the value changes.

### Q9. Java 8: group employees by department, highest paid per department, second highest salary.

```java
Map<String, Long> count = emps.stream()
        .collect(groupingBy(Emp::dept, counting()));

Map<String, Optional<Emp>> top = emps.stream()
        .collect(groupingBy(Emp::dept, maxBy(comparingDouble(Emp::salary))));

Optional<Double> second = emps.stream().map(Emp::salary).distinct()
        .sorted(reverseOrder()).skip(1).findFirst();
```

Say these three things: (1) `distinct()` before `skip(1)` or a tie for first makes "second" equal the
highest; (2) `maxBy` returns `Optional` because a group can theoretically be empty, unwrap it deliberately
(`collectingAndThen`); (3) the answer is `Optional`, not a magic `-1`, because there may be no second
salary. See file 02, sections 1-2.

### Q10. `toMap` throws; how do you handle duplicate keys? Sort by two fields? Partition?

`Collectors.toMap(k, v)` throws `IllegalStateException: Duplicate key` on a collision. Provide a merge
function `(a, b) -> a + "+" + b`, and a map supplier (`TreeMap::new`) if you need ordering. Sorting:
`comparing(A).thenComparing(B, reverseOrder())`; use `nullsLast` when fields can be null.
`partitioningBy` always returns both `true` and `false` keys (even when empty), unlike `groupingBy`.
Streams are single-use (second terminal op throws) and `sorted()` is a barrier that defeats
short-circuiting. All demonstrated in file 02.

### Q11. Reverse a linked list (iterative and recursive); detect a cycle; find the middle.

Iterative: `prev`, `curr`, `next`, O(n) time, O(1) space. Recursive: elegant but O(n) *stack*, so a
million-node list throws `StackOverflowError`; say that, then offer the iterative version. Cycle:
Floyd's slow/fast pointers, O(1) space (a `HashSet` of nodes works but is O(n) space). Middle: when
`fast` reaches the end `slow` is at the middle (second middle for even length). A `dummy` head node
removes the "empty result" special case in merge and remove problems.

### Q12. Validate a BST; kth smallest; lowest common ancestor; level-order traversal.

- **Validate BST:** pass `(min, max)` down. Comparing a node only with its parent is the classic wrong
  answer (a grandchild can violate the ordering; file 03 builds exactly that tree). Use `long` bounds so
  `Integer.MIN_VALUE` as a node value works.
- **Kth smallest:** iterative in-order with an explicit stack; stop at the kth pop, O(h + k).
- **LCA:** recurse; the node whose left and right subtrees each return non-null is the ancestor. For a
  BST you can instead walk down comparing values, O(h), no recursion.
- **Level order:** BFS with a queue and `size = q.size()` at the start of each level.

Always mention the skewed-tree case: recursion depth equals n, so for adversarial input use an
iterative traversal.

### Q13. Number of islands; detect a cycle in a directed graph; build order.

Islands: DFS flood-fill each unvisited `'1'`, count starts, O(R*C) (copy the grid first if the caller
needs it intact). Directed-graph cycle: DFS with three states (unvisited, on the current path, finished);
reaching a node that is *on the current path* is a cycle. A diamond (two paths to one node) is **not** a
cycle, which is why a plain "visited" set is wrong. Build order: Kahn's algorithm with in-degrees; if the
result has fewer than n nodes there is a cycle.

### Q14. Implement an LRU cache.

Fast answer: `LinkedHashMap(capacity, 0.75f, true)` (access order) and override `removeEldestEntry` to
`size() > capacity`. It is not thread-safe: wrap with `Collections.synchronizedMap` or guard with a lock.

"Without LinkedHashMap" answer: `HashMap<K, Node>` plus a doubly linked list with sentinel head/tail;
`get` and `put` move the node to the front, eviction removes `tail.prev`; both are O(1). Production
answer: use **Caffeine** (Window-TinyLFU, better hit rate, async loading, TTL) and discuss invalidation and
stampede protection. See file 04, section 1.

### Q15. Implement a thread-safe singleton. Which is best?

1. **Enum** `INSTANCE`: serialization- and reflection-proof, the Effective Java recommendation.
2. **Initialization-on-demand holder**: lazy, no locking, relies on the class-loading guarantee.
3. **Double-checked locking**: needs `volatile`, otherwise another thread can see a non-null reference
   to a partially constructed object (instruction reordering). File 04 races 200 threads and shows one
   construction.

Plus the real-world answer: in a Spring app you almost never write a singleton by hand; the container
gives you singleton *scope* and you keep the class stateless. Hand-rolled singletons are global state and
hard to test.

### Q16. Producer-consumer; rate limiter; retry with backoff; combining async calls.

- **Producer-consumer:** `BlockingQueue` in real code. With `wait/notify`: guard the condition with
  `while`, never `if` (spurious wakeups), and `notifyAll` when producers and consumers share one monitor.
- **Rate limiter:** token bucket (burst up to capacity, sustained refill rate) vs `Semaphore` (limits
  *concurrency*, a different thing) vs fixed window (allows 2x burst at the boundary). Inject the clock so
  it is testable. Distributed version: Redis + Lua script for an atomic check-and-decrement.
- **Retry:** exponential backoff **with jitter**, a cap on attempts, only for idempotent operations and
  transient errors; pair with a circuit breaker so retries do not amplify an outage.
- **`CompletableFuture`:** `thenCombine` for independent calls (wall time = slowest, not the sum),
  `completeOnTimeout` / `orTimeout` for a deadline, `exceptionally` or `handle` for fallback; pass your own
  executor, because the common pool is shared and sized for CPU work.

### Q17. "What is the output?" Integer cache, string pool, finally, overloads, CME, pass-by-value.

Memorise the verdicts (all proven in file 06):

| Snippet | Result | Why |
|---|---|---|
| `Integer a=127,b=127; a==b` / `128,128` | `true` / `false` | cache is -128..127; compare with `equals` |
| `"hel"+"lo" == "hello"` / runtime concat | `true` / `false` | compile-time constants are pooled |
| `0.1+0.2 == 0.3` | `false` | binary floating point; use `BigDecimal(String)` |
| `Integer.MAX_VALUE + 1`, `Math.abs(MIN_VALUE)` | negative | two's-complement wrap |
| `100_000 * 100_000` assigned to `long` | `1410065408` | `int * int` overflows before widening |
| `try { return 1; } finally { return 2; }` | `2` | `finally` return overrides (never do this) |
| `list.remove(1)` on `List<Integer>` | removes **index** 1 | overload `remove(int)` beats `remove(Object)` |
| remove inside for-each | `ConcurrentModificationException` | use `removeIf` or an `Iterator` |
| `Arrays.asList(..).add(x)` / `List.of(..).set` | `UnsupportedOperationException` | fixed-size / immutable |
| `equals` without `hashCode`, in a `HashSet` | `contains` is `false` | different bucket |
| `true ? nullInteger : 0` | NPE | ternary with a primitive operand unboxes |
| static / instance init order | parent static, child static, parent instance + ctor, child instance + ctor | JLS 12.4/12.5 |
| `s.toUpperCase();` result ignored | unchanged | strings are immutable |

### Q18. (V. IMP.) When do you use Singleton scope? What are its pros and cons?

**Singleton scope means the container creates exactly one instance of the bean per `ApplicationContext`
and hands that same instance to every consumer.** It is Spring's *default* scope. (Do not confuse it with
the GoF Singleton pattern: that one is "one instance per classloader enforced by the class itself";
Spring's is "one per container, enforced by the container", and you can still create a second instance
with `new` or a second context.)

**Use it when the bean is stateless, or its state is immutable / safely shared:**

- services, controllers, repositories, mappers, validators, clients (`RestClient`, `KafkaTemplate`);
- expensive-to-build, thread-safe resources: `DataSource` / connection pool, `ObjectMapper`,
  `ExecutorService`, caches, configuration holders;
- anything where "one shared instance" is the intent.

| Pros | Cons |
|---|---|
| **Cheap:** built once at startup, no per-request allocation or GC churn | **Shared mutable state is a bug factory:** every thread uses the same object, so a per-request field leaks between users (file 05, section 3b: request A reads request B's user) |
| **Fail-fast:** eager creation surfaces wiring errors and cycles at startup | **Must be thread-safe** by design: stateless, immutable, or properly synchronised / `Atomic*` / `ConcurrentHashMap` |
| **Good for expensive resources** (pools, parsers, SSL contexts) | **Lives as long as the context:** holds memory (a growing in-bean cache is a leak) and cannot be GC'd |
| **Easy to reason about** when stateless: no lifecycle surprises | **Prototype-into-singleton trap:** a prototype bean injected into a singleton is created *once*, at injection time, so it silently behaves like a singleton |
| One place for config and lifecycle callbacks (`@PostConstruct`, `@PreDestroy`) | **Test isolation:** state survives between tests that share a cached context; reset or use `@DirtiesContext` |

**When NOT to use it:** per-request or per-user data (use `request` / `session` scope, or better,
pass the data as method arguments or keep it in a request-scoped holder / `ThreadLocal` that you clear),
objects that are not thread-safe (`SimpleDateFormat`, a `StringBuilder` buffer, a JDBC `Connection`), and
objects that must be created fresh per use (use `prototype` and obtain it through `ObjectProvider<T>` or
`@Lookup`).

Rules of thumb you can say aloud:

1. Default to singleton and make the bean **stateless**: data in via arguments, results out via return values.
2. If it needs state, make it **immutable** (`final` fields set in the constructor).
3. If it needs *mutable* shared state, name the concurrency mechanism (`ConcurrentHashMap`, `LongAdder`,
   a lock) or move the state out into a database / cache.
4. Never store request data, the current user or a transaction in a singleton field.

Scope summary: `singleton` (one per container, default), `prototype` (new per lookup, Spring does not
manage its destruction), and web scopes `request`, `session`, `application`, `websocket`. Related:
`@Lazy` defers singleton creation, `spring.main.lazy-initialization=true` makes all of them lazy (faster
startup, but wiring errors surface at first use).

> Follow-up they may ask: "Is a Spring singleton thread-safe?" No. The container guarantees *one
> instance*; it does not synchronise your code. Thread-safety is the bean's own responsibility.

### Q19. (V. IMP.) What are circular dependencies? How does Spring handle them?

**A circular dependency is a cycle in the bean graph: A needs B and B needs A (or A -> B -> C -> A).**
Neither can be fully built before the other, so a container has to either refuse, or cheat by handing out
a half-built object.

How Spring behaves, by injection style (all shown in file 05, section 3c, and `3` before it):

| Style | Behaviour | Why |
|---|---|---|
| **Constructor <-> constructor** | **Fails at startup**: `BeanCurrentlyInCreationException` ("Requested bean is currently in creation: Is there an unresolvable circular reference?") | there is no object to hand out until a constructor returns |
| **Setter / field, singleton scope** | Historically **worked**: Spring creates the raw object, publishes an *early reference* in its three-level singleton cache (`singletonObjects` -> `earlySingletonObjects` -> `singletonFactories`), then populates properties; the other bean receives the half-built instance | the object exists before its properties are set |
| **Setter / field, since Spring Boot 2.6** | **Fails by default** (`spring.main.allow-circular-references=false`); you can switch it back on, but you should not | the framework chose to surface the design smell |
| **Prototype scope** | Always fails: prototypes are not cached, so there is nothing to publish early | |

Why it is a problem even when it "works":

- the injected reference may be **half-initialised**: a method called from a `@PostConstruct` sees null
  fields;
- an **AOP proxy can be bypassed**: the early reference can be the raw object while the container later
  wraps the bean in a proxy (`@Transactional`, `@Async`), so one consumer holds the proxy and another the
  unproxied target (Spring detects some cases with "has been injected into other beans in its raw version");
- it signals **tangled responsibilities** (A and B know each other, so neither is reusable or testable alone).

**How to fix, best first:**

1. **Redesign (the real answer):** extract the shared behaviour into a third bean `C` that both depend
   on, so the graph is a DAG: `A -> C <- B`. Often it is one class doing two jobs; split it.
2. **Invert with events or an interface:** B publishes an `ApplicationEvent` / calls a callback interface
   instead of calling A directly.
3. **Break one edge lazily:** `@Lazy` on one constructor parameter (Spring injects a lazy-resolution
   proxy) or inject `ObjectProvider<A>` / `Provider<A>` and call `getObject()` at use time. The cycle
   still exists in the design; you have only deferred it, so treat this as a tactical fix.
4. **Move one dependency to a setter** (`@Autowired` setter) - last resort and, from Boot 2.6, it also
   needs `allow-circular-references=true`.

How to find them: the startup failure prints the whole chain (`A -> B -> A`); `ArchUnit` can assert
"slices must be free of cycles" at the package level in CI.

> Follow-up they may ask: "Why does constructor injection catch this better?" Because it fails
> immediately and loudly at startup, in every environment, instead of producing a half-built object that
> misbehaves only on one code path in production.

### Q20. (V. IMP.) What is the difference between `BeanFactory` and `ApplicationContext`?

**`BeanFactory` is the basic IoC container: it creates beans and injects dependencies. `ApplicationContext`
extends it and adds the enterprise features you actually use.** In practice you always use an
`ApplicationContext` (Spring Boot builds one for you); `BeanFactory` is the root interface and what the
context delegates to internally.

| | `BeanFactory` | `ApplicationContext` |
|---|---|---|
| Bean creation | **lazy**: on the first `getBean()` | **eager** for singletons: pre-instantiated at `refresh()` |
| Failure timing | wiring errors appear at first use, possibly in production | wiring errors and cycles appear **at startup** |
| Post-processors | must be registered by hand | **auto-detects and applies** `BeanPostProcessor` / `BeanFactoryPostProcessor` (this is how `@Autowired`, AOP proxies and `@Transactional` get applied) |
| Events | none | `ApplicationEventPublisher`, `ContextRefreshedEvent`, `@EventListener` |
| Environment | none | `Environment`, **profiles**, `@Value`, property sources |
| i18n | none | `MessageSource` |
| Resources | basic | `ResourceLoader` (`classpath:`, `file:`, `http:`) |
| Annotation config | limited | `@Configuration`, component scanning, `@Bean`, `@Conditional` |
| Typical use | memory-constrained / embedded, tests of the container itself | **every real application** |

Implementations to name: `AnnotationConfigApplicationContext` (plain Java config),
`ClassPathXmlApplicationContext` (XML), `AnnotationConfigServletWebServerApplicationContext` (Spring Boot
web), and `DefaultListableBeanFactory` as the underlying `BeanFactory`.

What file 05, section 3d, proves:

- a `SimpleBeanFactory` has created **nothing** until `getBean("orderService")` is called;
- a `SimpleApplicationContext.refresh()` creates all singletons for the *active profile*, skips the `dev`
  data source, and publishes `ContextRefreshedEvent`;
- a broken bean makes the context fail **at refresh**, whereas the factory fails only when someone asks.

Consequences worth saying aloud:

- **Eager singleton creation is the reason a Spring app fails fast** when a bean is mis-wired or a
  cycle exists; `spring.main.lazy-initialization=true` trades that for faster startup.
- Prototype-scoped beans are *not* pre-created, even by an `ApplicationContext`.
- `BeanFactory` vs `FactoryBean`: a `FactoryBean<T>` is a *bean that produces other beans*
  (`&name` returns the factory itself); it is unrelated to `BeanFactory` and a common trick question.

> Follow-up they may ask: "When would you ever use a plain BeanFactory?" Almost never today: a tiny
> embedded or very memory-constrained runtime, or when building a container-like tool yourself. Spring
> docs recommend `ApplicationContext` unless you have a specific reason.

### Q21. (V. IMP.) How does Spring Boot provide auto-configuration?

**Spring Boot looks at what is on your classpath, what beans you already defined and what properties are
set, and registers sensible default beans for you; every default is conditional and backs off the moment
you define your own.** Add `spring-boot-starter-web` and you get an embedded Tomcat, `DispatcherServlet`
and Jackson `ObjectMapper` without writing any configuration.

The mechanism, step by step:

1. **`@SpringBootApplication`** is three annotations: `@SpringBootConfiguration` (a `@Configuration`),
   `@ComponentScan` (finds *your* beans) and **`@EnableAutoConfiguration`** (the switch for this answer).
2. **`@EnableAutoConfiguration`** imports `AutoConfigurationImportSelector`, which reads the list of
   candidate auto-configuration classes from
   `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` inside each jar
   (Boot 2.7+/3.x; older versions used `spring.factories`). `spring-boot-autoconfigure` alone ships
   well over a hundred candidates (`DataSourceAutoConfiguration`, `JacksonAutoConfiguration`,
   `KafkaAutoConfiguration`, ...).
3. **Each candidate is guarded by conditions**, evaluated while bean definitions are registered:

   | Condition | Meaning |
   |---|---|
   | `@ConditionalOnClass` / `OnMissingClass` | only if a class is (not) on the classpath: this is why a starter "turns on" a feature |
   | `@ConditionalOnMissingBean` | only if **you** have not defined one: this is how your bean overrides the default |
   | `@ConditionalOnBean` | only if another bean exists |
   | `@ConditionalOnProperty` | feature flag via `application.properties` |
   | `@ConditionalOnWebApplication`, `OnResource`, `OnExpression`, `OnCloudPlatform` | environment guards |

4. **Defaults are bound to properties** through `@ConfigurationProperties` classes
   (`ServerProperties`, `DataSourceProperties`, `JacksonProperties`), so `server.port=9090` or
   `spring.datasource.url=...` tunes the default without replacing it.
5. **Ordering** is controlled with `@AutoConfigureBefore` / `@AutoConfigureAfter`, so (for example) the
   `DataSource` exists before JPA wires itself to it.

```java
@AutoConfiguration
@ConditionalOnClass(ObjectMapper.class)                  // Jackson is on the classpath
public class JacksonLikeAutoConfiguration {
    @Bean
    @ConditionalOnMissingBean                            // backs off if the app defines its own
    ObjectMapper objectMapper() { return new ObjectMapper(); }
}
```

**How to see and control it:**

- `--debug` or `debug=true` prints the **conditions evaluation report**: "Positive matches", "Negative
  matches" (with the exact failed condition) and "Exclusions". `/actuator/conditions` gives the same at runtime.
- Exclude one: `@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)` or
  `spring.autoconfigure.exclude=...`.
- Override one: define your own bean of that type (the `OnMissingBean` guard does the rest).
- Write your own starter: an `@AutoConfiguration` class, an `.imports` file, a `@ConfigurationProperties`
  class and (by convention) a `*-spring-boot-starter` module that only carries dependencies.

**Common failure modes** worth naming: two default beans pulled in by two starters (an unexpected
embedded database appears because `h2` is on the test classpath); the app configures a bean *before* the
auto-configuration and `OnMissingBean` sees order differently than expected (use `@AutoConfigureAfter`);
slow startup from hundreds of conditions evaluated at boot (trim starters, use AOT / native image).

Run [`07_spring_boot/01_autoconfiguration_and_externalized_config.java`](../examples/07_spring_boot/01_autoconfiguration_and_externalized_config.java)
to see conditions and "your own bean makes the default back off" simulated; the long-form is
[07 Spring Boot, Q1-Q3](07_spring_boot.md).

> Follow-up they may ask: "What is the difference between `@ComponentScan` and auto-configuration?"
> Component scan finds the beans *you* wrote in your package tree. Auto-configuration loads candidate
> configuration classes *from libraries* by a fixed list, then keeps only those whose conditions pass.

### Q22. (V. IMP.) What is Spring Boot Actuator?

**Actuator is a Spring Boot module (`spring-boot-starter-actuator`) that adds production-ready
operational endpoints to your application: health, metrics, configuration, loggers, thread dumps and
more, exposed over HTTP and JMX.** It answers "is it up, is it healthy, what is it doing, how is it
configured?" without you writing any of that code.

Add the starter and, with no code, you get (under `/actuator`):

| Endpoint | What it gives you | Typical use |
|---|---|---|
| `health` | status `UP`/`DOWN` plus component details (DB, disk, Kafka, custom indicators) | load balancer and Kubernetes probes |
| `health/liveness`, `health/readiness` | probe groups | "restart me" vs "send me traffic" |
| `info` | build and git info, custom data | which version is running |
| `metrics` | JVM, HTTP server, datasource-pool, cache metrics via **Micrometer** | dashboards, alerts |
| `prometheus` | metrics in Prometheus scrape format | Prometheus / Grafana |
| `loggers` | read **and change log levels at runtime** | debug a live issue without redeploying |
| `env`, `configprops` | property sources and bound configuration | "which value won?" |
| `conditions`, `beans`, `mappings` | auto-configuration report, bean graph, URL map | startup debugging |
| `threaddump`, `heapdump` | JVM diagnostics | deadlocks, leaks |
| `httpexchanges`, `auditevents` | recent requests, security events | light tracing and audit |
| `shutdown` | graceful stop (disabled by default) | rarely; prefer the orchestrator |

How it works: each capability is an **endpoint** (`@Endpoint`, with `@ReadOperation` /
`@WriteOperation`) technology-neutral, then exposed as web (Spring MVC / WebFlux) and/or JMX adapters.
Health is aggregated from `HealthIndicator` beans; a failing indicator turns the whole status `DOWN`
(status order is configurable). Metrics are recorded through the **Micrometer** facade, which is to metrics
what SLF4J is to logging, and shipped to Prometheus, Datadog, CloudWatch, Splunk and others by a registry.

Custom health indicator:

```java
@Component
class PaymentGatewayHealth implements HealthIndicator {
    public Health health() {
        return gatewayReachable() ? Health.up().withDetail("latencyMs", 42).build()
                                  : Health.down().withDetail("reason", "timeout").build();
    }
}
```

**Production rules (this is where the marks are):**

1. **Expose the minimum.** By default only `health` is exposed over HTTP:
   `management.endpoints.web.exposure.include=health,info,prometheus`. Never `*` on an internet-facing port.
2. **Secure the sensitive ones.** `env` (may show secrets, though values are sanitised), `heapdump`
   (contains every object in memory, including passwords and tokens), `threaddump`, `loggers`
   (write access changes behaviour). Require a role via Spring Security.
3. **Separate management port** (`management.server.port=9001`) so it is not reachable through the public
   gateway or ingress.
4. **Liveness must not depend on downstream systems.** If the database is down and liveness fails,
   Kubernetes restarts every pod and turns an outage into a bigger one. Put DB / Kafka checks in
   **readiness** only (the example below proves the distinction).
5. **Keep health checks cheap** and time-bounded; an expensive indicator hit by every probe is its own
   incident. Use `show-details=when-authorized`.
6. **Tag metrics with low-cardinality labels** (service, endpoint template) never user ids, or you will
   flood the metrics backend.
7. **Pair with graceful shutdown** (`server.shutdown=graceful`): readiness flips first, in-flight
   requests drain, then the process stops.

Run [`07_spring_boot/02_actuator_health_and_graceful_shutdown.java`](../examples/07_spring_boot/02_actuator_health_and_graceful_shutdown.java)
for a real HTTP server showing liveness vs readiness and a graceful shutdown with a request in flight.
Long form: [07 Spring Boot, Q8](07_spring_boot.md); metrics and Splunk side: [14](14_observability_splunk.md).

> Follow-up they may ask: "How do you know which endpoint caused a latency spike?" `http.server.requests`
> metric tagged by `uri` and `status`, plus a trace id in the logs (Micrometer Tracing / OpenTelemetry).

## Coverage map: the 52 problems from the reference list

| Band | Problems | Where |
|---|---|---|
| Freshers 1-17 | prime, reverse, palindrome, factorial, swap, largest / second largest, sum of digits, Fibonacci, GCD, reverse words, vowels, anagram, dedupe chars, char frequency, permutations, quicksort | file 01 (all but quicksort, factorial; trivial, see drills) |
| 2-3 yrs 18-34 | stack, infix-postfix, first non-repeating, merge sorted, max difference, Kadane, matrix rotate, pair sum, missing number, 0/1/2, Pascal, selection sort, binary search, group anagrams, longest substring | file 01 (stack/infix, matrix, Pascal, selection sort are drills) |
| 5-10 yrs 35-52 | LRU, singleton, serialization, reverse list, producer-consumer, LCA, kth smallest, rotated search, cycle, max path sum, validate BST, serialize tree, islands, CompletableFuture, rate limiter | files 03 and 04 (serialization and rotated search are drills) |
| Marked *V. IMP.* | JWT / token auth, DI and its types, when to use which, singleton scope pros/cons, circular dependencies, BeanFactory vs ApplicationContext, Boot auto-configuration, Actuator | Q1-Q3, Q18-Q22 here, file 05 |
| Added here | idempotent POST, stream collectors, output traps, token bucket, retry | Q4, files 02, 04, 06 |

## A worked example

Run file 04 and read the **section 3** output:

```text
=== 3. Idempotent POST with an Idempotency-Key ===
  ok  50 concurrent duplicates -> every caller sees the SAME response -> [201:order-1]
  ok  business logic executed exactly once -> 1
  ok  different body, same key -> 422 -> 422
```

Then break it on purpose: replace `store.putIfAbsent(key, candidate)` with
`store.containsKey(key) ? store.get(key) : store.put(key, candidate)` and run again. `executions` becomes
greater than 1 and the check fails. That single edit is the check-then-act race interviewers want you to
name.

## Hands-on drills

1. Write `isBalanced(String)` for `()[]{}` with an `ArrayDeque`. State the complexity and the empty-string
   answer.
2. Implement `search(int[] rotated, int key)` in O(log n) (binary search deciding which half is sorted).
3. Add `Pascal's triangle`, `matrix rotate 90`, `selection sort` and `quicksort` to file 01 with checks.
4. Make `IdempotentHandler` persist to a `ConcurrentHashMap` replaced by a simulated table with a unique
   constraint, and run the business write and key insert in one "transaction".
5. Add a sliding-window-log rate limiter and show the boundary burst that the fixed window allows.
6. Extend `MiniContainer` with `@Qualifier`-like names and a prototype scope; make it detect a prototype
   injected into a singleton.
7. Re-implement the stream questions in file 02 with a plain `for` loop and compare readability, then
   with `parallelStream()` and explain why `toMap` into a `HashMap` would be wrong there.

## The 60-second spoken answers

**DI:** "Dependency injection means a class receives its collaborators instead of constructing them, so
I can swap implementations and test it with plain `new`. In Spring the container builds the graph and
injects through the constructor. I use constructor injection for required dependencies, setter only for
optional ones with a default, and avoid field injection because it hides dependencies and needs
reflection in tests."

**Singleton scope:** "One shared instance per container, the default. I use it for stateless or
immutable beans such as services, repositories and clients, which is cheap and fail-fast. The cost is
that it is shared across threads, so any mutable per-request field is a data leak and a race; the
container makes one instance, it does not make it thread-safe. Per-request state goes into arguments or
request scope, and a prototype needed inside a singleton comes through `ObjectProvider`."

**Circular dependencies:** "A needs B and B needs A. Constructor injection fails fast at startup
with a clear chain; setter or field injection used to work because Spring publishes an early reference
to the half-built singleton, but since Boot 2.6 that is off by default. It is a design smell, and
the fix is to extract the shared part into a third bean or use an event; `@Lazy` or `ObjectProvider` is
only a tactical way to defer one edge."

**BeanFactory vs ApplicationContext:** "`BeanFactory` is the basic container: lazy creation and
dependency injection only. `ApplicationContext` extends it with eager singleton creation at startup,
automatic post-processors (so `@Autowired` and AOP work), events, profiles and `Environment`, message
sources and resource loading. I always use `ApplicationContext`; the eager start is what makes a
mis-wired bean fail at boot instead of at the first request."

**Auto-configuration:** "`@SpringBootApplication` includes `@EnableAutoConfiguration`, which loads a list
of candidate configuration classes from each jar's `AutoConfiguration.imports` file. Each candidate is
guarded by conditions such as `@ConditionalOnClass` and `@ConditionalOnMissingBean`, so it only applies
when the library is on the classpath and backs off if I define my own bean. Defaults are tuned through
properties, and `--debug` prints the conditions report that shows what matched and why."

**Actuator:** "It is Spring Boot's production-ops module: endpoints for health, metrics through
Micrometer, loggers, env, thread and heap dumps, exposed over HTTP and JMX. In production I expose only
health, info and prometheus, on a separate secured management port, keep liveness independent of
downstream systems and put database and Kafka checks in readiness, so a dependency outage does not make
Kubernetes restart every pod."

**JWT:** "After login the server issues a signed, short-lived token: header, payload, signature. Each
request carries it and any service can verify the signature without a session lookup, which is why it
scales and works across microservices. The payload is readable, not encrypted, and the token cannot be
revoked before expiry, so I keep access tokens to minutes, rotate a server-side refresh token, pin the
algorithm and validate `exp`, `iss` and `aud`."

**Idempotency:** "The client sends an `Idempotency-Key`; the server reserves it atomically, runs the
business logic once, stores the response and replays it for duplicates. Same key with a different body
is a 422. A failed first attempt releases the key, and keys expire. In the database that is a unique
constraint written in the same transaction as the business change."
