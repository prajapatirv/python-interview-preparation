---
id: foundations-java-core
title: Core Java from the basics: concepts, a real story, then the answer
stack: java
skill: java-core
---
These entries are written **from the ground up**: *Start here: the concepts* in simple words, then a
real story, then the answer an interviewer expects. Every term is defined before it is used.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What is an immutable class, and how do you create one?
tags: immutable, final, thread-safety, defensive-copy, record, string, basics

**Start here: the concepts**
- **Object:** a thing in memory with data (fields) and behaviour (methods).
- **Mutable:** its data *can be changed* after it is created. A `List` you can `add()` to is mutable.
- **Immutable:** its data *can never be changed* after it is created. To "change" it you build a *new* object. `String` is the everyday example: `"abc".toUpperCase()` does not alter `"abc"`, it returns a different string.
- **Reference:** a variable holds an *address* of an object, not the object. Two variables can point at the same object, so a change through one is visible through the other. This is why mutability is dangerous.
- **Thread:** a separate line of execution. Several threads running at once can touch the same object at the same time.

**The live scenario**
A payment service has a `Money` object shared by the pricing code and the audit logger. Pricing applies a discount by changing the amount *inside* that same object. A moment later the audit logger writes the receipt, and it records the discounted amount as if it were the original price. Nobody copied anything; both pieces of code held the same reference. Worse, two threads were calculating tax on the same object, and one saw a half-updated value. If `Money` could never change, none of this could happen: each calculation would create a new `Money` and the old one would stay intact.

**What the interviewer is really checking**
That you understand *why* immutability matters (safety when sharing, especially across threads), not only the checklist of how to build one.

**How I answer it**
1. **Say what it is first:** an immutable class is one whose objects cannot change after construction; any "modification" returns a new object.
2. **Why we want it:**
   - safe to share between threads without locks, because nobody can change it;
   - safe as a `HashMap` key or `Set` element, because its hash code never changes;
   - easy to reason about and to cache.
3. **The recipe, with the reason for each step:**
   - make the class `final`, so a subclass cannot add mutable behaviour;
   - make every field `private final`, so it can only be set once;
   - set values only in the constructor and provide no setters;
   - if a field holds a mutable object (a `List`, a `Date`), **copy it on the way in and copy it on the way out**, otherwise the caller still holds a reference they can change.
4. **Show it briefly:**

```java
public final class Money {
    private final BigDecimal amount;
    private final String currency;
    public Money(BigDecimal amount, String currency) { this.amount = amount; this.currency = currency; }
    public Money add(Money other) { return new Money(amount.add(other.amount), currency); } // new object
}
// Java 16+: record Money(BigDecimal amount, String currency) { }
```

5. **Modern shortcut:** a `record` gives you a shallow-immutable class with constructor, getters, `equals`, `hashCode` and `toString`; remember it is only *shallowly* immutable, so a `List` component still needs a copy (`List.copyOf`).

**Trade-offs and what can go wrong**
Every change creates a new object, which costs allocation; for large structures updated in a hot loop use a builder or a mutable local and freeze at the end. `final` fields do not make the *objects they point to* immutable: a `final List` can still be added to. Forgetting the defensive copy is the classic bug.

**Follow-ups to expect**
- *Is a `final` variable the same as an immutable object?* -> no: `final` stops the *variable* being reassigned, not the object being modified.
- *Why is `String` immutable?* -> so it can be safely shared, cached in the string pool, used as a map key, and trusted in security checks.
- *How do you make a class with a `List` field immutable?* -> copy in the constructor with `List.copyOf`, and return an unmodifiable view or a copy.

**60-second answer**
An immutable class is one whose objects never change after construction, so any change produces a new object. I make the class final, fields private final, set them only in the constructor, and defensively copy any mutable field in and out. It is thread-safe without locks and safe as a map key, and a record is the short form.

### Q2 [mid] What is the `equals()` and `hashCode()` contract, and what breaks if you get it wrong?
tags: equals, hashcode, hashmap, contract, collections, basics

**Start here: the concepts**
- **`equals()`:** answers "do these two objects represent the same thing?". By default it only says yes if they are literally the same object in memory.
- **`hashCode()`:** turns an object into a number. Hash-based collections use this number as a quick first guess of where to look.
- **Hash collection (`HashMap`, `HashSet`):** stores items in buckets chosen by `hashCode()`, then confirms with `equals()`.
- **Contract:** the rules the two methods must obey together.

**The live scenario**
A `Customer` class overrides `equals()` to compare by `customerId` but not `hashCode()`. The team stores customers in a `HashSet` to de-duplicate. Two objects for customer 42 are "equal", yet both appear in the set and the report double counts. Because the default `hashCode()` gives them different numbers, they landed in different buckets and `equals()` was never even asked.

**What the interviewer is really checking**
That you know the rule "equal objects must have equal hash codes" and its practical consequence.

**How I answer it**
1. **Rules:**
   - if `a.equals(b)` then `a.hashCode() == b.hashCode()`;
   - equal hash codes do *not* require equal objects (collisions are allowed);
   - `equals` must be reflexive, symmetric, transitive and consistent.
2. **Always override both together,** using the same fields.
3. **How a lookup works:** compute the hash, go to the bucket, compare with `equals()`; with the wrong hash you look in the wrong bucket and miss.
4. **Keys must not change:** a mutable field used in `hashCode()` that changes after insertion makes the entry unfindable, so use immutable keys.
5. **Modern help:** records generate both correctly; otherwise use `Objects.equals` and `Objects.hash`.

**Trade-offs and what can go wrong**
A constant `hashCode()` is legal but turns the map into a list. Including mutable or lazy-loaded JPA fields causes subtle bugs.

**60-second answer**
`equals` defines logical equality and `hashCode` picks the bucket; equal objects must return equal hash codes. If I override one without the other, hash collections look in the wrong bucket and duplicates appear or lookups fail. I override both using the same, preferably immutable, fields.

### Q3 [mid] How does a `HashMap` work internally, and what happens on a collision?
tags: hashmap, buckets, collision, treeify, resize, load-factor, basics

**Start here: the concepts**
- **Array:** a fixed list of slots you can reach instantly by position.
- **Bucket:** one slot of that array, which can hold several entries.
- **Hash function:** turns a key into a number; the array position is that number reduced to the array size.
- **Collision:** two different keys that map to the same bucket.
- **Load factor:** how full the map may get before it grows (default 0.75).

**The live scenario**
A cache keyed by user id works well at 1,000 entries. At millions of entries with a poor `hashCode()`, many keys land in a few buckets, each bucket becomes a long chain, and `get()` slows from "instant" to "scan a list". Latency drifts upward with data size even though the code did not change.

**What the interviewer is really checking**
That you can describe the put/get steps and collision handling, and why good hash codes matter.

**How I answer it**
1. **Structure:** an array of buckets; each bucket is a linked list, converted to a balanced tree when it grows long (Java 8+, at 8 entries and a large enough table).
2. **`put`:** compute the hash, find the bucket, walk it comparing keys with `equals()`, replace if found, otherwise append.
3. **`get`:** same path; average O(1), worst case O(log n) with treeified buckets.
4. **Resize:** when entries exceed capacity x load factor, the table doubles and entries are redistributed, which is expensive, so pre-size when the count is known.
5. **Not thread-safe:** concurrent writes can corrupt it; use `ConcurrentHashMap`.

**Trade-offs and what can go wrong**
Poor hash codes and mutable keys hurt performance and correctness. A resize during a hot path causes a latency spike.

**60-second answer**
A `HashMap` is an array of buckets chosen by the key's hash; collisions chain entries in a list that becomes a tree when long. `get` and `put` are O(1) on average, it doubles when 75% full, and it is not thread-safe, so concurrent code uses `ConcurrentHashMap`.

### Q4 [mid] What is the difference between `volatile` and `synchronized`?
tags: volatile, synchronized, visibility, atomicity, memory-model, concurrency, basics

**Start here: the concepts**
- **Visibility:** when one thread changes a value, can other threads *see* the new value? Without help, a thread may keep reading a stale copy cached in its CPU.
- **Atomicity:** an operation happens completely or not at all, with no other thread interleaving.
- **Race condition:** the result depends on which thread happens to run first.
- **Lock (monitor):** only one thread at a time may hold it; others wait.

**The live scenario**
A worker loop runs `while (running) { ... }`, and another thread sets `running = false` to stop it. In production the worker never stops, because it keeps reading its cached `true`. Declaring the flag `volatile` fixes it. In another class, two threads do `count++` on a `volatile int` and the total is wrong, because `count++` is read, add, write and `volatile` does not make those three steps one.

**What the interviewer is really checking**
That you separate visibility from atomicity and choose the right tool for each.

**How I answer it**
1. **`volatile`:** guarantees visibility and ordering of a single variable; no locking, no atomicity of compound actions.
2. **`synchronized`:** gives mutual exclusion *and* visibility; only one thread runs the block at a time.
3. **Use `volatile` for** a simple flag or a safely published reference written by one thread and read by others.
4. **Use `synchronized` or `Lock` for** compound actions like check-then-act and read-modify-write.
5. **Often better:** `AtomicInteger` and friends for counters, and concurrent collections.

**Trade-offs and what can go wrong**
`synchronized` can block and cause contention or deadlock; `volatile` is cheap but easy to misuse. On Java 21 virtual threads, long blocking inside `synchronized` can pin the carrier thread.

**60-second answer**
`volatile` makes a single variable's writes visible to other threads but does not make compound operations atomic; `synchronized` provides mutual exclusion plus visibility. I use `volatile` for flags, `synchronized` or atomics for read-modify-write, and prefer concurrent utilities where possible.

### Q5 [fresher] What is the difference between checked and unchecked exceptions, and when do you use each?
tags: exceptions, checked, unchecked, runtimeexception, error-handling, basics

**Start here: the concepts**
- **Exception:** an object that represents something going wrong and interrupts normal flow.
- **Checked exception:** the compiler *forces* you to handle or declare it (`IOException`, `SQLException`).
- **Unchecked exception:** a `RuntimeException` or `Error`; the compiler does not force handling (`NullPointerException`, `IllegalArgumentException`).
- **Stack trace:** the list of calls that led to the error, used for diagnosis.

**The live scenario**
A repository method declares `throws SQLException`. Every service above it must catch or re-declare it, so business code fills with try/catch that only logs and swallows, and a failed save quietly returns success. Switching to an unchecked `DataAccessException` (as Spring does) lets the failure travel up to one place that maps it to a 500 response and rolls back the transaction.

**What the interviewer is really checking**
Judgement: when a failure is recoverable by the caller vs a programming or infrastructure error, and awareness of the Spring transaction rollback default.

**How I answer it**
1. **Checked:** the caller can reasonably recover or must make a decision (file missing, a validation outcome).
2. **Unchecked:** programming bugs or failures the caller cannot fix (null, bad argument, database down).
3. **Modern practice:** prefer unchecked exceptions with a clear domain type, and handle them centrally (`@ControllerAdvice`).
4. **Never swallow:** log with context or rethrow; do not catch `Exception` and ignore it.
5. **Spring detail:** `@Transactional` rolls back on unchecked exceptions by default but commits on checked ones unless `rollbackFor` is set.

**Trade-offs and what can go wrong**
Too many checked exceptions leak implementation details through every layer. Catching generic `Exception` hides bugs and breaks rollback.

**60-second answer**
Checked exceptions are enforced by the compiler for recoverable situations; unchecked ones signal bugs or unrecoverable failures. I prefer unchecked domain exceptions handled in one place, never swallow them, and remember that Spring transactions roll back only on unchecked exceptions by default.

### Q6 [fresher] Cohesion vs coupling
tags: cohesion, coupling, design, solid, dependency-injection, interfaces, basics

**Start here: the concepts**
- **Class / module:** a unit of code with one place in the design.
- **Cohesion:** how closely the things *inside* one class belong together. High cohesion means the class does one job well; low cohesion means it is a grab-bag of unrelated duties.
- **Coupling:** how much one class *depends on* another. Tight (high) coupling means a change in one forces changes in many others; loose (low) coupling means they can change independently.
- **Interface:** a promise of what something can do, without saying how. Depending on an interface instead of a concrete class lowers coupling.
- **Dependency injection (DI):** handing a class the things it needs from outside, instead of the class creating them itself.

**The live scenario**
An e-commerce `OrderService` places orders, but it also builds PDF invoices, sends emails and calls one specific bank's API directly. The bank changes its API: you must edit `OrderService`, retest ordering, and risk breaking invoices. A new payment provider means copying the code. Each of those pain points is a symptom: too many jobs (low cohesion) and a hard dependency on one bank class (tight coupling).

**What the interviewer is really checking**
That you can define both terms in your own words, tie them to maintainability, and name the practical tools (interfaces, DI, single responsibility).

**How I answer it**
1. **Define each in one line:** cohesion is how focused a class is; coupling is how much it depends on others.
2. **Aim for the opposite of what you have:** high cohesion, low coupling, because the change cost stays small and local.
3. **Raise cohesion:** give each class one reason to change (Single Responsibility): `OrderService` handles orders, `InvoiceService` makes PDFs, `NotificationService` sends email.
4. **Lower coupling:** depend on an interface, `PaymentGateway`, with `BankAGateway` and `BankBGateway` implementations, and inject the one you want.
5. **Benefit you can state:** switching bank is a configuration change, and `OrderService` can be unit-tested with a fake gateway.

**Trade-offs and what can go wrong**
Over-splitting creates many tiny classes and indirection that is hard to follow. An interface with only one implementation, created "just in case", is noise. Zero coupling is impossible; the goal is coupling to *stable* abstractions.

**Follow-ups to expect**
- *How are cohesion and coupling related?* -> they usually move together: low cohesion tends to force tight coupling because one class needs many collaborators.
- *Which Spring feature helps?* -> dependency injection: the container supplies the implementation, so classes depend on interfaces.

**60-second answer**
Cohesion is how focused a class is on one job; coupling is how much it depends on other classes. I want high cohesion and low coupling so changes stay local. I give each class a single responsibility and depend on interfaces injected through DI, so a payment provider can be switched without touching the order logic.

### Q7 [mid] How to convert a normal class into a singleton
tags: singleton, design-pattern, thread-safety, enum, spring-scope, basics

**Start here: the concepts**
- **Singleton:** a class that has exactly **one instance** in the whole application, with one global way to get it.
- **Why it exists:** something expensive or shared, such as a configuration holder, a connection pool or a cache.
- **Lazy vs eager:** *eager* creates the instance at class load; *lazy* creates it on first use.
- **Thread-safe:** safe when several threads ask for the instance at the same time.
- **Spring singleton scope:** by default every Spring bean is one instance per container. That is "singleton" in a different sense: managed by the container, not by the class itself.

**The live scenario**
A hand-written lazy singleton checks `if (instance == null) instance = new Config();`. Under load, two threads both see `null` and each creates an instance, so two "singletons" hold different cached settings. Support sees a customer get the old tax rate on one request and the new one on the next.

**What the interviewer is really checking**
That you know the threading hazard, can list the safe implementations, and know that in Spring you rarely hand-write one.

**How I answer it**
1. **Basics:** private constructor, a static field holding the instance, a public static accessor.
2. **Safe options:**
   - **enum singleton:** one constant; thread-safe and also safe against reflection and serialisation;
   - **initialisation-on-demand holder:** a private static nested class holds the instance, so the JVM's class loading makes it lazy and thread-safe;
   - **double-checked locking** with a `volatile` field: works, but is easy to get wrong.
3. **Pitfalls:** hidden global state, hard to test (cannot swap it for a fake), tight coupling, and one instance per *classloader*, not per JVM.
4. **In Spring:** declare a bean and let the container manage a single instance, and inject it; this keeps the class testable.
5. **Remember:** a singleton must be stateless or safely synchronised, because every thread shares it.

**Trade-offs and what can go wrong**
Mutable state in a singleton is the number one concurrency bug source. Reflection or serialisation can create a second instance of a naive singleton.

**60-second answer**
A singleton has one instance with a global accessor. The safest hand-written forms are an enum or the holder idiom; lazy check-then-create is not thread-safe, and double-checked locking needs `volatile`. In Spring I let the container manage one bean and inject it, keeping the class testable, and I keep it stateless.
