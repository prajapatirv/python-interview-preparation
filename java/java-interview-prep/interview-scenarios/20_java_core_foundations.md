---
id: foundations-java-core
title: Java 8, Java 11 & modern Java: from the basics (drafted)
stack: java
skill: java-core
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is the difference between JDK, JRE and JVM?
tags: jdk, jre, jvm, bytecode, jlink, java-runtime, basics

**Start here: the concepts**
- **Source code and bytecode:** You write `.java` files, which humans can read. The compiler turns them into `.class` files containing *bytecode*, an instruction set for an imaginary machine rather than for a real CPU. This lets the same `.class` file run on Windows, Linux or Mac.
- **JVM (Java Virtual Machine):** A program that runs bytecode. It loads classes, checks them for safety, executes them (interpreting, and compiling hot code to native machine code with the JIT compiler) and manages memory through garbage collection. There is a different JVM build for each operating system and CPU, which is what makes bytecode portable.
- **Core class libraries:** Ready-made classes such as `String`, `List`, `HashMap`, file I/O and networking. Every Java program needs them, and they ship with Java itself.
- **JRE (Java Runtime Environment):** The JVM plus the core class libraries. It is everything needed to *run* a Java program, and nothing to *build* one.
- **JDK (Java Development Kit):** The JRE plus developer tools: `javac` (compiler), `jar` (packages classes into a JAR file), `jcmd` (inspects a running JVM) and `jshell` (interactive console for trying code).
- **`jlink`:** A tool (Java 9 onward) that builds a small custom runtime containing only the modules your app uses.

**The live scenario**
A developer builds a service on a laptop with JDK 17 and hands the JAR to operations. The test server has an old runtime, Java 8. The service fails at startup with `UnsupportedClassVersionError ... class file version 61.0, ... only recognizes class file versions up to 52.0`. Nothing is wrong with the code. JDK 17's compiler wrote bytecode (version 61) that the Java 8 JVM (up to version 52) cannot read. The team lost half a day because nobody could say which piece, the compiler or the runtime, was out of date. A second, related case: a team shipped a full JDK in every container image, roughly hundreds of MB each, when a `jlink` runtime would have been much smaller. The exact sizes depend on the setup.

**What the interviewer is really checking**
Whether you understand the layering (JDK contains JRE contains JVM) and can tell *build time* from *run time*. They also want to see that you know the modern situation, where JRE is no longer a separate download for most people.

**How I answer it**
1. **Start with the JVM.** It runs bytecode, not Java source. This is why Java is "write once, run anywhere": the compiled output is portable and each platform supplies its own JVM.
2. **Add the JRE.** A JVM alone is not enough, because programs call `String`, collections and I/O classes. JRE = JVM + core libraries, so it is the "run" package.
3. **Add the JDK.** Developers also need to compile and diagnose. JDK = JRE + `javac` and tools like `jar`, `jcmd` and `jshell`. Remember it as nested boxes: JDK ⊃ JRE ⊃ JVM.
4. **Show the flow.** `javac` turns `.java` into `.class`, and the JVM runs the `.class` files:
```
javac Hello.java   # JDK tool, compile time
java Hello         # JVM, run time
```
5. **Mention the modern change.** Since Java 11, Oracle no longer offers a separate JRE download, and you install the JDK. Some vendors, such as Eclipse Temurin, still publish JRE packages for some versions. For small deployments you can use `jlink` to build a trimmed runtime with only the modules you need.

**Trade-offs and what can go wrong**
- **Version mismatch:** Compiling with a newer JDK and running on an older runtime gives `UnsupportedClassVersionError`. Compile with `--release 11`, or whichever version you target, to avoid it.
- **Full JDK in production:** It is bigger, and it includes tools you do not need at run time. Some teams keep it anyway because `jcmd` is handy for diagnosis.
- **`jlink` runtimes:** They are smaller but need extra build work. If you forget a module, the app fails at run time with missing-class errors.
- **A common mistake:** Saying "the JVM compiles Java". `javac` compiles to bytecode, and the JVM executes it.

**How I'd monitor it**
- Run `java -version` and `javac -version` on build and server machines to confirm they match.
- Run `jcmd <pid> VM.version` to see the JVM of a running process.
- Run `javap -v SomeClass.class` and read the "major version" (52 = Java 8, 55 = Java 11, 61 = Java 17).
- Add a CI check that the build JDK matches the deployment runtime.
- Search Splunk logs for `UnsupportedClassVersionError` after deployments.

**Follow-ups to expect**
- *Is the JVM platform independent?* -> No. Bytecode is portable, but each OS and CPU needs its own JVM build.
- *What does the JIT compiler do?* -> It turns frequently used bytecode into native machine code while the program runs, so hot code runs faster.
- *Can I run Java with only a JRE today?* -> Yes, if your vendor provides one, but Oracle stopped a separate JRE from Java 11. Most teams use the JDK or a `jlink` runtime.

**60-second answer**
The JVM is the engine that runs compiled Java bytecode. It loads classes, runs them, compiles hot code to native code and cleans up memory. The JRE is the JVM plus the core class libraries like `String` and collections, so it is enough to run a program. The JDK is the JRE plus developer tools such as the `javac` compiler, `jar`, `jcmd` and `jshell`, so it is what you need to build programs. I think of them as nested boxes: JDK contains JRE, which contains JVM. Since Java 11, Oracle no longer provides a separate JRE download, so you normally install the JDK, or you use `jlink` to build a smaller custom runtime. One practical point: bytecode compiled by a newer JDK will not run on an older JVM, so I match build and runtime versions.

### Q2 [fresher] Why is String immutable and what is the String pool?
tags: java, string, immutability, string-pool, stringbuilder, equals, basics

**Start here: the concepts**
- **Immutable:** an object whose contents cannot change after it is created. A `String` never changes. Methods like `toUpperCase()` or `concat()` return a new String and leave the old one untouched. Reassigning a variable (`s = s + "x"`) only points the variable at a new object.
- **Heap:** the memory area where Java objects live.
- **String pool:** a special cache inside the heap (since Java 7) that holds one shared copy of each distinct string literal. It exists to save memory and avoid creating duplicates.
- **String literal:** text written directly in code, like `"a"`. The compiler and JVM put literals in the pool and reuse them.
- **`==` vs `equals()`:** `==` asks "are these the same object in memory?". `equals()` asks "do these have the same characters?".
- **Thread-safe:** safe to use from several threads at once without locks. Immutable objects are automatically thread-safe, because nobody can change them.
- **Hash code:** a number computed from the content, used by `HashMap` to decide where to store a key.
- **`StringBuilder`:** a mutable text buffer you append to without creating a new object each time. `StringBuffer` is the older version whose methods are synchronized (locked), which makes it slower.

**The live scenario**
A nightly report job built a 100,000-line CSV with `result = result + line` inside a loop. It took about 40 seconds and GC (garbage collection) was busy. Each `+` created a new String and copied all the previous text, so the work grew roughly with the square of the size. After switching to `StringBuilder`, it ran in well under a second (illustrative numbers). In the same release, a role check `if (role == "ADMIN")` passed in unit tests, where the value was a literal. It failed in production, where the value came from JSON and was a different object.

**What the interviewer is really checking**
Whether you can explain *why* Java designed String this way (safety, caching, sharing) and whether you know the practical consequences: `equals()` vs `==`, and `StringBuilder` in loops.

**How I answer it**
1. **A String cannot be changed after creation.** Every "modification" creates a new object. This is the core rule.
2. **Because it never changes, it is thread-safe.** Many threads can share one String with no locks, since no one can alter it.
3. **Because it never changes, the pool is possible.** Many variables can safely point to the same object. If one could modify it, everyone sharing it would see the change.
4. **Because it never changes, the hash code can be cached.** `String` computes its hash once and reuses it, which makes it a fast and reliable `HashMap` key. A mutable key would change its hash after insertion, and the map could never find it again.
5. **It is safe for security-sensitive values.** Things like file paths, URLs, and class names can't be altered after validation.
6. **Literals share one pooled object, `new` makes another.**
```java
"a" == "a"               // true  (same pooled object)
new String("a") == "a"   // false (new heap object)
new String("a").equals("a") // true
```
   So always compare content with `equals()`.
7. **Use `StringBuilder` for repeated concatenation in loops** to avoid creating many throwaway Strings. Use `StringBuffer` only for old code that needs its synchronization.

**Trade-offs and what can go wrong**
- Immutability costs extra objects and copying when you build text piecemeal.
- Comparing with `==` works by accident for literals and breaks for runtime values (input, JSON, database). This is a classic bug.
- Don't call `intern()` (which puts a string into the pool) on lots of unique values. It adds pool overhead for little benefit.
- Passwords in a `String` stay in memory until GC, so security guidance often prefers `char[]` that you can wipe.
- A single `+` outside a loop is fine. The problem is concatenation inside loops.

**How I'd monitor it**
- Profile with JFR or a profiler to see high allocation rates from `String` and `char[]`/`byte[]`.
- Check GC logs for frequent young collections during string-heavy jobs.
- Track job duration, for example in Splunk, before and after the change.
- Use static analysis (such as SonarQube) and code review to flag `==` on strings and concatenation in loops.

**Follow-ups to expect**
- *Is `new String("a")` one object or two?* -> The literal `"a"` is in the pool (created once), and `new` creates a separate heap object, so up to two.
- *What does `intern()` do?* -> It returns the pooled copy of a string, adding it to the pool if it isn't there.
- *`StringBuilder` vs `StringBuffer`?* -> Same API. `StringBuffer` is synchronized and slower, while `StringBuilder` isn't synchronized and is the default choice.

**60-second answer**
A String is immutable, meaning its content can't change after creation. Methods like `toUpperCase()` return a new object. This makes strings thread-safe without locks, safe to share, and safe as `HashMap` keys, because their hash is computed once and cached. It also makes the String pool possible. The pool is a heap cache where identical literals share one object, so `"a" == "a"` is true while `new String("a") == "a"` is false. That's why I always compare strings with `equals()`, not `==`. Since every change creates a new object, I use `StringBuilder` for concatenation in loops. `StringBuffer` is the older, synchronized, slower version.

### Q3 [fresher] Abstract class vs interface - which one when?
tags: java8, oop, interface, abstract-class, default-methods, basics

**Start here: the concepts**
- **Interface:** a list of methods a class promises to provide, without saying how. It exists so callers can depend on the promise instead of on one specific class.
- **Abstract class:** a half-finished class. It can hold fields and finished methods, and it can declare methods with no body (abstract methods) that subclasses must complete. You cannot create an object of it directly.
- **Instance state:** data stored per object, such as a `retryCount` field. Interfaces cannot have it. They can only hold constants (`public static final`).
- **`default` method (Java 8):** an interface method with a body. Implementing classes inherit it and may override it. It lets you add a method to an old interface without breaking existing implementers.
- **`static` method (Java 8) and `private` method (Java 9):** `static` is a helper that belongs to the interface itself. `private` is a helper shared by the interface's own default methods.
- **Inheritance limits:** a class can `implement` many interfaces but `extend` only one class. Java has this rule to avoid the confusion of inheriting state from several parents.
- **Template method:** a pattern where the parent class fixes the order of steps and subclasses fill in some of them.

**The live scenario**
A payments team had a `PaymentProcessor` abstract class with 3 implementations. A partner integration needed a 4th implementation that already had to extend a vendor's `HttpClientBase` class. Java allows only one parent class, so the team spent about 2 days refactoring 12 classes to an interface. In a second case, someone added a method to a widely used interface and 15 implementations stopped compiling until the method was made `default`. Both problems came from choosing the wrong tool early.

**What the interviewer is really checking**
Whether you understand the real difference (state and single inheritance versus a contract) and can give a decision rule, not just recite syntax.

**How I answer it**
1. **Start with the contract.** Define what callers need as an interface, because a class can implement many interfaces and callers stay independent of any one implementation.
2. **Ask whether subclasses share fields or common code.** If they do (for example a `retryCount` and a common `validate()`), use an abstract class, because only classes can hold per-object state.
3. **Use an abstract class for a template-method skeleton.** The parent fixes the order of steps (validate, process, audit) and subclasses supply only `process()`.
4. **Use `default` methods to evolve interfaces.** Adding a method with a body does not break existing implementers.
5. **Combine them when needed.** Expose an interface, and offer an optional abstract base class that implements it. Callers use the interface, and implementers who want the shortcut extend the base.

```java
interface PaymentProcessor { Receipt pay(Order o); }
abstract class BaseProcessor implements PaymentProcessor { /* shared fields, template steps */ }
```

**Trade-offs and what can go wrong**
- An abstract class uses up your only `extends`, which makes later reuse hard.
- Abstract class constructors can run shared setup. Interfaces have no constructors.
- Too many `default` methods turn an interface into a hidden abstract class with logic that is hard to find.
- If two interfaces give the same `default` method, the class must override it to resolve the conflict, or it will not compile.
- Changing an interface without recompiling its implementers can cause `AbstractMethodError` at runtime.
- Since Java 17, sealed interfaces can restrict who may implement them. That is useful when the set of implementations should be closed.

**How I'd monitor it**
- Code review rule: "interface first, abstract class only for shared state."
- Build checks such as Sonar or ArchUnit rules against deep class hierarchies.
- Unit tests for each `default` method.
- In Splunk, search for `AbstractMethodError` or `IncompatibleClassChangeError` after a deployment. These point to mismatched library versions.

**Follow-ups to expect**
- *Can an abstract class have a constructor?* -> Yes. It runs when a subclass is created, to set up shared fields. Interfaces cannot have constructors.
- *Why were default methods added?* -> So Java 8 could add methods like `stream()` and `forEach()` to existing interfaces such as `Collection` and `Iterable` without breaking old code.
- *Can an interface have fields?* -> Only constants, which are implicitly `public static final`. It has no per-object state.

**60-second answer**
An interface is a contract: it says what a class can do, and a class can implement many of them. An abstract class is a partly built class: it can hold fields and shared code, but a class can extend only one. I start with an interface for the public API so callers stay flexible. I add an abstract class only when subclasses really share state or a step-by-step skeleton, called the template method. Since Java 8, interfaces can have `default` and `static` methods, and since Java 9 `private` ones. They still cannot hold per-object state. A good design is often both: an interface for callers and an optional abstract base class for convenience.

### Q4 [fresher] Checked vs unchecked exceptions? What is try-with-resources?
tags: java, exceptions, checked-exceptions, try-with-resources, autocloseable, spring, basics

**Start here: the concepts**
- **Exception:** an object Java creates when something goes wrong at runtime, such as a missing file or a failed database call. It travels up the call stack until some code catches it. If nothing catches it, the thread's work fails.
- **Checked exception:** a subclass of `Exception` that is not a `RuntimeException`, for example `IOException`. The compiler forces you to either catch it or declare it with `throws`. It exists to make you think about failures that are expected and possibly recoverable, like a missing file.
- **Unchecked exception:** a `RuntimeException` or its subclasses, for example `NullPointerException` or `IllegalArgumentException`. The compiler does not force you to handle them. They usually signal a bug or a failure the caller cannot fix. `Error` (for example `OutOfMemoryError`) is also unchecked, and you should not normally catch it.
- **Resource:** something that must be released after use, such as a file, a socket or a database connection. If you do not release it, it leaks, and the system eventually runs out.
- **AutoCloseable:** an interface with one method, `close()`. Any class that implements it can be used in try-with-resources.
- **Try-with-resources:** a `try` that opens resources in parentheses. Java calls `close()` on each one automatically when the block ends, whether it ends normally or with an exception.
- **Suppressed exception:** if the block throws an exception and `close()` then throws another one, Java keeps the first (the real cause) and attaches the second to it. You can read it with `getSuppressed()`.

**The live scenario**
An order service handles about 200 requests per second. It uses a pool of 20 database connections. A developer closed a connection in the normal path but forgot to close it when a `SQLException` was caught. Each failed query leaked one connection. A short database slowdown caused a few dozen failures, and within minutes all 20 connections were stuck. Every new request waited, then failed with HTTP 500, and the service was effectively down even though the database was healthy. The fix was to open the connection in try-with-resources so it is always returned to the pool.

**What the interviewer is really checking**
Whether you know the compiler rule and when to use each kind of exception. Also whether you understand why try-with-resources is safer than a hand-written `finally` for avoiding leaks.

**How I answer it**
1. **Define the split:** checked exceptions must be caught or declared, and unchecked ones need not be. The compiler enforces this, which is how it forces callers to think about expected failures.
2. **Say when to use each:** use checked for recoverable, expected problems that the caller can reasonably act on. Use unchecked for programming errors and for failures the caller cannot fix.
3. **Mention modern practice:** in Spring code, teams usually throw unchecked domain exceptions such as `OrderNotFoundException`. They handle them in one place, for example with `@ControllerAdvice`. Checked exceptions would otherwise force `throws` clauses through every layer.
4. **Explain try-with-resources:** it closes any `AutoCloseable` automatically, even when an exception is thrown. Resources are closed in reverse order of opening.
5. **Explain suppressed exceptions:** the original exception is kept as the main one, and failures from `close()` are attached as suppressed. In a hand-written `finally`, an exception from `close()` can replace the real cause, so you lose the root cause.

```java
try (var conn = dataSource.getConnection();
     var ps = conn.prepareStatement(sql)) {
    // use ps; both are closed automatically
}
```

**Trade-offs and what can go wrong**
- Checked exceptions make APIs noisy and tempt people to write empty `catch` blocks. That hides real failures.
- Unchecked exceptions are easy to forget to handle, so you need a central handler and good logging.
- Wrapping a checked exception in a runtime one without passing the original as the cause loses the stack trace.
- Only objects that implement `AutoCloseable` work in try-with-resources.
- If `close()` fails and nothing else failed, that exception is thrown as normal.

**How I'd monitor it**
- Watch connection pool metrics (active and pending connections, for example HikariCP through Micrometer). A pool that stays full points to a leak.
- Search logs in Splunk for "Connection is not available" and "Too many open files", and for stack traces containing "Suppressed:".
- Alert on a rising 5xx rate.
- Use static analysis or IDE warnings to flag resources that are opened but not closed.

**Follow-ups to expect**
- *Is `Error` checked?* -> No. It is unchecked, and it signals serious JVM problems such as `OutOfMemoryError`, so you normally do not catch it.
- *Does Spring `@Transactional` roll back on checked exceptions?* -> By default it rolls back on `RuntimeException` and `Error`, not on checked exceptions, unless you configure `rollbackFor`.
- *Why not just use `finally`?* -> It works, but it is verbose, and an exception from `close()` can hide the original one. Try-with-resources handles both cases.

**60-second answer**
Checked exceptions, like `IOException`, must be caught or declared with `throws`, and the compiler enforces that. Unchecked exceptions, which are `RuntimeException` and its subclasses, need no such handling and usually mean a bug or something the caller cannot fix. In modern Spring code I throw unchecked domain exceptions and handle them in one place, so I do not have to pass `throws` through every layer. Try-with-resources, written as `try (var in = ...)`, automatically closes any `AutoCloseable`, even when an exception is thrown. It closes resources in reverse order. If `close()` also fails, the original exception stays as the main one and the close failure is attached as suppressed. This prevents leaks such as exhausted connection pools.

### Q5 [fresher] `final` vs `finally` vs `finalize`?
tags: java, final, finally, finalize, exception-handling, resource-cleanup, basics

**Start here: the concepts**
- **Keyword:** a reserved word in Java, like `final` or `finally`. The three names look alike, but they are unrelated.
- **Variable, method, class:** the three things `final` can be put on. It means "this cannot be changed after it is set".
- **Reference vs object:** a variable holding an object stores a pointer to it. `final` on that variable freezes the pointer, not the object's contents.
- **Override / subclass:** a subclass can replace a parent's method (override) or extend a class. `final` forbids both.
- **Exception:** an error event that interrupts normal flow. `try` wraps risky code, and `catch` handles the error.
- **Resource:** something that must be released after use, such as a file, socket, or database connection. If you don't release it, the operating system eventually runs out of them.
- **Garbage collector (GC):** the JVM part that frees memory of unused objects at a time *it* chooses, not you.
- **Finalizer:** the `finalize()` method, which the GC may call before freeing an object. It was meant for cleanup but is unreliable, because nobody knows when, or whether, it runs.

**The live scenario**
A report service opened a file per request and relied on `finalize()` to close it. At about 200 requests/second, objects piled up waiting for the GC. The process hit its limit of 1,024 open files (illustrative number), and requests began failing with "Too many open files". Restarting fixed it for an hour. The fix was `try-with-resources`, which closes the file the moment the block ends.

**What the interviewer is really checking**
Whether you know these are three unrelated things (a modifier, a block, a method). Also whether you know `finalize()` should not be used and what to use instead.

**How I answer it**
1. **`final` means "cannot change".**
   - On a variable, it can be assigned once. For an object, the reference is fixed but the object's fields can still change.
   - On a method, it cannot be overridden, so a subclass cannot alter critical behaviour.
   - On a class, it cannot be subclassed. `String` is final, so nobody can create a mutable fake `String`.
2. **`finally` is a block after `try`/`catch` that runs whether or not an exception happened.** This is why it is used for cleanup. It does not run if the JVM exits first (`System.exit()`, a crash) or the thread is killed or stuck in an infinite loop. Never `return` inside `finally`, because it silently overrides the earlier return or hides an exception.
3. **`finalize()` is a method the GC may call before reclaiming an object.** It is deprecated since Java 9 and deprecated for removal since Java 18. It is unreliable because the GC decides the timing, it may never run, and it slows GC.
4. **Replace `finalize()` with `try-with-resources` for normal cleanup.** The class must implement `AutoCloseable`, and Java calls `close()` automatically, even on exceptions:
```java
try (var in = Files.newInputStream(path)) { /* use in */ }
```
5. **Use `Cleaner` (Java 9+) only as a safety net** for native resources, not as the main mechanism.

**Trade-offs and what can go wrong**
- Believing `final` makes an object immutable. A `final List` can still have items added.
- Writing `finally` with a `return`, which swallows exceptions.
- Forgetting that `finally` is skipped on `System.exit()`.
- Still overriding `finalize()` in old code. It delays memory release and hides leaks until production load.
- `Cleaner` is still not guaranteed to run on time, so it cannot replace explicit closing.

**How I'd monitor it**
- Open file descriptor count per process (for example `lsof -p <pid> | wc -l`, or your metrics agent).
- Splunk search for `"Too many open files"` or `"Connection pool exhausted"`.
- GC logs and heap dumps, to see objects stuck in the finalizer queue.
- Compile with `-Xlint:removal` and static analysis to flag `finalize()` usage.

**Follow-ups to expect**
- *Does `finally` run if `try` has a `return`?* -> Yes, `finally` runs just before the method returns. A `return` inside `finally` overrides the original one.
- *Is a `final` object immutable?* -> No. Only the reference can't be reassigned. Immutability needs final fields and no mutating methods.
- *Why is `finalize()` bad?* -> Its timing is unpredictable, it may never run, it hurts GC performance, and it can resurrect objects.

**60-second answer**
These three are unrelated words that only look alike. `final` means "can't change": a final variable is assigned once, a final method can't be overridden, and a final class can't be extended. Note that a final reference can still point to an object whose contents change. `finally` is a block after `try`/`catch` that runs whether or not an exception occurs, so it's used for cleanup, except when the JVM exits or the thread dies. `finalize()` is an old method the garbage collector might call before freeing an object. It's unreliable and deprecated for removal since Java 18. For cleanup I use `try-with-resources`, and `Cleaner` only as a backup.

### Q6 [mid] HashMap vs Hashtable vs ConcurrentHashMap vs Collections.synchronizedMap?
tags: java8, hashmap, concurrenthashmap, thread-safety, collections, basics

**Start here: the concepts**
- **Thread-safe:** a class is thread-safe if several threads can use it at the same time without corrupting its data or losing updates.
- **Lock (`synchronized`):** only one thread at a time may run the protected code. The others wait. This is safe but slow if many threads queue on one lock.
- **Bucket:** a map stores entries in an array of slots. The key's hash code picks the slot, and each slot is called a bucket.
- **CAS (compare-and-set):** a CPU instruction that says "set this value only if it is still what I expect". It needs no lock, and the caller retries if another thread changed the value first.
- **Atomic operation:** one step that no other thread can see half-done. `merge` and `computeIfAbsent` are atomic. A separate `get` followed by `put` is two steps, so it is not atomic.
- **Weakly consistent iterator:** an iterator that tolerates concurrent changes. It never throws `ConcurrentModificationException`, but it may or may not show changes made while you iterate.

**The live scenario**
A service counts API calls per customer in a `Collections.synchronizedMap(new HashMap<>())`. It runs 400 request threads on 16 cores at about 5,000 requests per second. Two things went wrong. Thread dumps showed most threads `BLOCKED` on the same lock, and p99 latency rose from 30 ms to roughly 180 ms (illustrative numbers). Worse, the code did `get`, then `+1`, then `put`. Two threads could read the same value, and one increment was lost, so billing counts were too low. Switching to `ConcurrentHashMap` with `counts.merge(id, 1L, Long::sum)` fixed both the contention and the lost updates.

**What the interviewer is really checking**
Whether you know that "thread-safe" does not mean "safe for compound operations", and whether you can explain why `ConcurrentHashMap` scales better than a single lock.

**How I answer it**
1. **`HashMap`:** not thread-safe, but fastest. It allows one null key and null values. Use it when only one thread touches the map. Shared across threads, it can lose updates or corrupt its structure during resize.
2. **`Hashtable`:** a legacy class (Java 1.0) where every method is `synchronized`. One lock covers the whole map, so threads queue even when touching different keys. It forbids null keys and values. I would not use it in new code.
3. **`Collections.synchronizedMap(map)`:** a wrapper that puts one lock around every call to a normal map. It has the same bottleneck as `Hashtable`, but it keeps the wrapped map's null rules. You must also lock manually while iterating, or you risk `ConcurrentModificationException`.
4. **`ConcurrentHashMap` (Java 8+):** reads usually take no lock. Adding to an empty bucket uses CAS. Otherwise a write locks only that bucket's first entry. Threads working on different buckets do not block each other. (Before Java 8 it used coarser "segments".)
5. **Rules of `ConcurrentHashMap`:** null keys and values are forbidden, because `get` returning null would not tell you "absent" from "stored null" when other threads are changing the map. Use the atomic methods (`computeIfAbsent`, `merge`, `putIfAbsent`) for check-then-act logic. Iterators are weakly consistent.
6. **My default:** `ConcurrentHashMap` for shared caches and counters, and plain `HashMap` for data owned by one thread.

**Trade-offs and what can go wrong**
- Individual calls are atomic, but a `get` followed by `put` is still a race, even on `ConcurrentHashMap`.
- `size()` and iteration are approximate under concurrent writes.
- Keep `computeIfAbsent` functions short. They hold a bucket lock, so slow I/O inside them blocks other threads, and modifying the same map from inside can deadlock or throw an exception.
- Mutating a key's fields after insert breaks lookups in any map.
- For very low contention, the gain over `synchronizedMap` is small.

**How I'd monitor it**
- Take repeated thread dumps (`jstack`) and look for many threads `BLOCKED` on the same monitor.
- Use Java Flight Recorder's lock-contention events.
- Track p99 latency and throughput against thread count. Flat throughput as threads grow suggests a lock bottleneck.
- Compare counters with an independent source (for example, billing totals) to catch lost updates.
- In Splunk, correlate latency spikes with traffic peaks.

**Follow-ups to expect**
- *Why does `ConcurrentHashMap` reject nulls?* -> A null from `get` would be ambiguous (absent or stored null), and you cannot safely resolve it with `containsKey` while others modify the map.
- *Is `ConcurrentHashMap` safe for `if (!map.containsKey(k)) map.put(k, v)`?* -> No, it is two steps. Use `putIfAbsent` or `computeIfAbsent`.
- *Does iterating throw `ConcurrentModificationException`?* -> Not for `ConcurrentHashMap` (weakly consistent). `HashMap` does, and so does a `synchronizedMap` iterated without manual locking.

**60-second answer**
`HashMap` is fast but not thread-safe, so I use it only within one thread. `Hashtable` and `Collections.synchronizedMap` make a map safe by putting one lock around every call, so threads queue even on different keys. `ConcurrentHashMap` in Java 8 and later uses CAS for empty buckets and locks only one bucket for writes, and reads are mostly lock-free. It forbids null keys and values and gives atomic methods like `merge` and `computeIfAbsent`. For shared caches and counters I use it with those atomic methods, because a separate `get` then `put` can still lose updates. I would watch for blocked threads in thread dumps and for latency that does not improve with more threads.

### Q7 [mid] ArrayList vs LinkedList? Fail-fast vs fail-safe iterators?
tags: java, collections, arraylist, linkedlist, iterator, concurrency, basics

**Start here: the concepts**
- **Array**: one continuous block of memory holding items side by side. Jumping to item number 5,000 is one calculation, so it is instant.
- **Linked list**: each item (a "node") sits separately in memory and holds pointers to the previous and next node. To reach item 5,000 you must walk from an end, one node at a time.
- **O(1) / O(n)**: shorthand for how work grows with size. O(1) means the cost stays the same. O(n) means it grows in step with the number of items.
- **Cache friendly**: CPUs read memory in chunks, so neighbouring items arrive almost free. Arrays benefit from this. Scattered linked nodes do not.
- **Iterator**: the object behind a `for-each` loop. It walks a collection one item at a time.
- **Fail-fast iterator**: the collection keeps a change counter (`modCount`). If the list is structurally changed (add or remove) while an iterator is walking it, the iterator notices and throws `ConcurrentModificationException`. It is a best-effort bug detector, not a guarantee. It can happen in a single thread.
- **Fail-safe (weakly consistent) iterator**: an iterator that never throws that exception. "Fail-safe" is an informal name. The Java docs say "snapshot" or "weakly consistent". A snapshot iterator walks a frozen copy. A weakly consistent iterator may or may not show changes made during the walk.
- **Copy-on-write**: `CopyOnWriteArrayList` copies its whole internal array on every write. Readers keep walking the old copy safely.

**The live scenario**
A reporting service loaded 200,000 rows into a `LinkedList` and looped with `for (int i...) list.get(i)`. In staging with 1,000 rows it looked fine. In production the job took about 40 seconds instead of well under a second, because every `get(i)` walked the chain, so the total work was roughly n². Switching to `ArrayList` fixed it. The same week, a cleanup job removed expired items inside a `for-each` loop and the logs filled with `ConcurrentModificationException`. The numbers are illustrative, but the pattern is very common.

**What the interviewer is really checking**
Whether you can explain the memory layout behind the Big-O numbers and know that `LinkedList` rarely wins in practice. Also whether you understand that fail-fast is a bug detector, and how to pick the right collection for concurrent use.

**How I answer it**
1. **Default to `ArrayList`.** It is backed by an array, so `get(i)` is O(1). Appending is amortized O(1): it occasionally grows the array by copying, about 1.5x larger in OpenJDK. Contiguous memory also suits CPU caches.
2. **Know its weak spot.** Inserting or removing in the middle shifts the later items, which is O(n). The shift is a fast bulk memory copy, so it is usually still fast.
3. **`LinkedList` is O(1) only at the ends**, or when you already hold an iterator positioned at the spot. Finding position `i` is O(n), and each node costs extra memory for two pointers and an object header. It implements `Deque`, but `ArrayDeque` is usually the better queue or stack.
4. **Explain fail-fast.** `ArrayList` and `HashMap` iterators compare the `modCount` they saw at the start with the current one. If it differs, they throw. Fix it with `iterator.remove()` or:
   ```java
   list.removeIf(item -> item.isExpired());
   ```
5. **Explain the concurrent alternatives.** `CopyOnWriteArrayList` iterates over a snapshot, so it is safe for many reads and rare writes. `ConcurrentHashMap` iterators are weakly consistent. They never throw, and they may or may not show concurrent updates.

**Trade-offs and what can go wrong**
- `CopyOnWriteArrayList` copies the whole array on each write. With frequent writes it burns CPU and creates garbage.
- Snapshot and weakly consistent iterators can show stale data. Do not use them where you need an exact view.
- Fail-fast is not guaranteed. Never build logic that relies on catching the exception.
- `Collections.synchronizedList` is still fail-fast, and you must synchronize manually while iterating.
- Choosing `LinkedList` because "insertion is O(1)" is the classic mistake. It ignores the cost of finding the position.

**How I'd monitor it**
- Search Splunk for `ConcurrentModificationException` and group by stack trace to find the offending loop.
- Take thread dumps or a profiler or JFR sample. Frames stuck in `LinkedList.node(int)` point to index-based access on a linked list.
- Check a heap histogram for large counts of `LinkedList$Node`.
- Watch GC frequency and pause time after adopting `CopyOnWriteArrayList` on a write-heavy path.

**Follow-ups to expect**
- *Both are O(n) for middle insert, so why is ArrayList often faster?* -> ArrayList shifts memory with one fast bulk copy. LinkedList must first walk node by node through scattered memory.
- *Does fail-fast guarantee the exception is thrown?* -> No. It is best effort, meant for detecting bugs, not for program logic.
- *When would you use CopyOnWriteArrayList?* -> For a small list that is read constantly and changed rarely, such as a listener list.

**60-second answer**
"`ArrayList` is backed by an array, so index access is O(1) and it is cache friendly. Appends are amortized O(1), and middle inserts are O(n) because items shift. `LinkedList` is only O(1) at the ends, or when you already hold the iterator position. Finding an index is O(n) and each node costs extra memory, so I default to `ArrayList` and use `ArrayDeque` for queues. Fail-fast iterators, as in `ArrayList` and `HashMap`, throw `ConcurrentModificationException` when the structure changes mid-iteration. That can happen even in one thread, and the fix is `iterator.remove()` or `removeIf`. The concurrent collections, `CopyOnWriteArrayList` and `ConcurrentHashMap`, never throw. One iterates over a snapshot and the other over a weakly consistent view, so both can be slightly stale."

### Q8 [mid] Comparable vs Comparator? HashSet vs LinkedHashSet vs TreeSet?
tags: java, collections, comparable, comparator, hashset, linkedhashset, treeset, basics

**Start here: the concepts**
- **Set:** a collection that holds no duplicates. Each implementation decides what "duplicate" means and how it orders items.
- **Comparable:** an interface a class implements to define its one built-in ("natural") order through `compareTo(other)`. It returns a negative number, zero or a positive number. Examples are `String` (alphabetical) and `Integer` (numeric).
- **Comparator:** a separate object that defines an order from outside the class, through `compare(a, b)`. It exists because you often need several orders (by salary today, by name tomorrow), or the class is not yours to change.
- **Hash-based lookup:** `HashSet` runs `hashCode()` to pick a bucket and then `equals()` to confirm a match. This gives O(1) lookups on average, but no meaningful order.
- **Insertion order:** the order in which items were added.
- **Red-black tree:** a self-balancing sorted tree. `TreeSet` uses one, so every operation costs O(log n).
- **Consistent with equals:** `compare(a, b) == 0` should happen exactly when `a.equals(b)` is true.

**The live scenario**
A payroll report held about 10,000 employees in a `TreeSet<Emp>` sorted by salary. Finance noticed the report listed only about 8,200 people. Nobody had been dropped by a query. `compareTo` compared salary only, and `TreeSet` treats "compares as 0" as "same element". Everyone who shared a salary with an earlier employee was silently discarded. Adding a tie-breaker on employee id fixed it.

**What the interviewer is really checking**
Whether you know that each type of set decides duplicates in a different way (`equals`/`hashCode` versus comparison). They also want to see that you can choose a sensible order and a sensible structure for the job.

**How I answer it**
1. **Comparable is the natural order, inside the class.** I implement it once, via `compareTo`, when the class has one obvious order. The reason is that sorted collections and `Collections.sort` then work with no extra input.
2. **Comparator is an external order that can be composed.** I use it for alternative orders or classes I can't edit. Java 8 added builders, so I can chain sorts:
   `Comparator.comparing(Emp::dept).thenComparing(Emp::salary)`
   Calling `.reversed()` at the end flips the whole chain. To flip only one key, I use `thenComparing(Emp::salary, Comparator.reverseOrder())`.
3. **HashSet:** O(1) on average, no order guaranteed. It needs correct `equals` and `hashCode`. I pick it when I only need "is it in there?".
4. **LinkedHashSet:** it behaves like `HashSet` (still O(1)) but also keeps a linked list through its entries, so iteration follows insertion order. It costs a little more memory. I pick it for stable output, such as API responses or reports.
5. **TreeSet:** always sorted, O(log n). It also gives range queries like `first()`, `headSet` and `ceiling`. It needs either `Comparable` elements or a `Comparator` passed to the constructor, otherwise you get a `ClassCastException`.
6. **TreeSet decides duplicates by comparison, not `equals`.** So the ordering should be consistent with `equals`. If it isn't, the set breaks the general `Set` contract (as in the scenario).

**Trade-offs and what can go wrong**
- A `TreeSet` comparator that ignores a field drops elements silently.
- A mutable key changed after insertion breaks all three sets. A `HashSet` looks in the wrong bucket, and a `TreeSet` sits in the wrong place in the tree.
- `HashSet` allows one `null`. `TreeSet` with natural ordering throws on `null`, unless you use `Comparator.nullsFirst`.
- Subtracting ints inside `compare` can overflow. Use `Integer.compare`.
- Sorting a whole list once is often cheaper than keeping a `TreeSet` sorted on every insert.

**How I'd monitor it**
- Unit tests that assert set size equals the source list size when duplicates are not expected.
- Logging "records in / records out" counts for batch jobs, and alerting in Splunk when they differ.
- A heap profiler if a huge `LinkedHashSet` or `TreeSet` shows up as a memory hog.

**Follow-ups to expect**
- *What happens if you put an object without `Comparable` into a `TreeSet`?* -> `ClassCastException` at runtime, unless you supplied a `Comparator`.
- *Why must you override `hashCode` with `equals`?* -> Equal objects must land in the same bucket, or `HashSet` can't find them.
- *Which one for a sorted leaderboard with range queries?* -> `TreeSet`, or `TreeMap` if scores need values, with a tie-breaker in the comparator.

**60-second answer**
`Comparable` is the one natural order a class defines for itself with `compareTo`. `Comparator` is an outside, composable order, like `comparing(dept).thenComparing(salary)`, so I can have many orders without changing the class. `HashSet` is O(1) on average with no order. `LinkedHashSet` is also O(1) but remembers insertion order. `TreeSet` keeps things sorted at O(log n). The catch is that `TreeSet` treats "compares as zero" as a duplicate, so the ordering should be consistent with `equals`, or elements silently vanish. I've seen a report lose 1,800 of 10,000 employees that way.

### Q9 [mid] What is a functional interface? Name the common ones.
tags: java8, functional-interface, lambda, method-reference, predicate, streams, basics

**Start here: the concepts**
- **Interface:** a contract that lists methods a class must provide. Callers depend on the contract, not on the concrete class.
- **Abstract method:** a method declared without a body. Any class implementing the interface must supply it.
- **Functional interface:** an interface with exactly one abstract method (a "single abstract method", or SAM). Because there is only one method to fill in, Java can treat a small piece of code as that method. It may also have `default` and `static` methods, and methods that match `Object` ones (like `equals` in `Comparator`), without breaking the rule.
- **Lambda:** a short inline function, such as `x -> x > 10`. The compiler turns it into an object of whichever functional interface is expected.
- **Method reference:** shorthand for a lambda that only calls an existing method, such as `String::length`.
- **`@FunctionalInterface`:** an optional annotation. It makes the compiler fail if someone later adds a second abstract method.
- **Effectively final:** a local variable that is never reassigned after it is first set. Lambdas may only capture local variables of this kind.
- **Why it exists:** before Java 8, passing behaviour meant writing a whole anonymous class. Functional interfaces let streams, `Optional` and `CompletableFuture` accept behaviour as a short lambda.

**The common ones (java.util.function and friends)**
- `Function<T,R>`: takes T, returns R.
- `Predicate<T>`: takes T, returns boolean.
- `Consumer<T>`: takes T, returns nothing.
- `Supplier<T>`: takes nothing, returns T.
- `BiFunction<T,U,R>`: the two-argument version of `Function`. `BiConsumer` and `BiPredicate` follow the same pattern.
- `UnaryOperator<T>`: a `Function<T,T>`.
- `BinaryOperator<T>`: a `BiFunction<T,T,T>`.
- `Runnable`: no input, no result.
- `Callable<V>`: no input, returns a value and may throw checked exceptions.
- `Comparator<T>`: also a functional interface.
- Primitive versions such as `IntPredicate` avoid boxing.

**The live scenario**
An order service had 12 validation rules, each written as an anonymous class, about 400 lines in total. Adding a rule took a day because of the boilerplate. A developer refactored them into a `List<Predicate<Order>>` of one-line lambdas, and the file shrank to about 60 lines. During the same change, another developer tried to count rejections with a local `int count` inside a lambda. It would not compile, because lambdas cannot capture a local variable that changes. He worked around it with a shared array in a parallel stream and got wrong totals under load. The fix was to use `Collectors.counting()`, or an `AtomicInteger` if a side effect was really needed.

**What the interviewer is really checking**
Whether you know the "one abstract method" rule and the main built-in types by their shape (input and output). Also whether you know the lambda rules around captured variables and `this`.

**How I answer it**
1. **Define it:** a functional interface has exactly one abstract method. That is what lets a lambda or method reference stand in for it, since the compiler knows which method the lambda implements.
2. **Name the core four by shape:** `Function` (T to R), `Predicate` (T to boolean), `Consumer` (T to nothing), `Supplier` (nothing to T). Then add `BiFunction`, `UnaryOperator`, `Runnable` and `Callable`. Naming them by shape shows you understand them rather than having memorised a list.
3. **Mention `@FunctionalInterface`:** it is optional but good practice, because the compiler then protects the contract.
4. **Explain capture:** a lambda can use local variables only if they are effectively final. The lambda may run later, possibly on another thread, so a changing local copy would be confusing and unsafe. Fields (instance or static) can be modified, but then thread safety is your job.
5. **Explain `this`:** inside a lambda, `this` is the enclosing object, because a lambda does not create a new scope of its own. Inside an anonymous class, `this` is the anonymous object itself.

```java
Predicate<Order> big = o -> o.total() > 1000;
```

**Trade-offs and what can go wrong**
- Lambdas that mutate outside state are a common source of bugs, especially in parallel streams.
- `Callable` can throw checked exceptions but `Function` cannot, so lambdas that call such code need a try/catch inside.
- Long multi-line lambdas hurt readability. Extract a named method and use a method reference instead.
- Stack traces from lambdas are harder to read than those from named classes.
- Do not claim `Runnable` is new in Java 8. It is old, and it simply qualifies as a functional interface.

**How I'd monitor it**
This is mostly a compile-time and review concern. Code review and static analysis such as Sonar can flag side effects inside stream lambdas. At runtime, I log the rule name that rejected an order and track rejection counts per rule as a metric. A Splunk search on those counts shows when a rule suddenly rejects far more than usual.

**Follow-ups to expect**
- *Can a functional interface have more than one method?* -> Yes, if only one is abstract. `default`, `static` and `Object`-matching methods do not count.
- *Can a lambda change a local variable?* -> No, locals must be effectively final. It can change fields, or the contents of a mutable object like an `AtomicInteger`.
- *Lambda vs anonymous class?* -> A lambda is shorter and works only for functional interfaces, and `this` refers to the enclosing object. An anonymous class can implement any interface or class, and `this` is the anonymous object.

**60-second answer**
A functional interface is an interface with exactly one abstract method, so a lambda or method reference can implement it. The common ones are `Function` (T to R), `Predicate` (T to boolean), `Consumer` (T to nothing) and `Supplier` (nothing to T). There are also `BiFunction`, `UnaryOperator`, `Runnable` and `Callable`, which returns a value and can throw checked exceptions. `@FunctionalInterface` is optional, but it makes the compiler guard the single-method rule. Lambdas can capture only effectively-final local variables, so I avoid mutating outside state, especially in parallel streams. Also, `this` inside a lambda is the enclosing object, unlike in an anonymous class where it is the anonymous object itself.

### Q10 [mid] Intermediate vs terminal stream operations? map vs flatMap?
tags: java8, streams, lazy-evaluation, intermediate-operations, terminal-operations, flatmap, basics

**Start here: the concepts**
- **Stream:** a pipeline that describes how to process a sequence of data (a list, for example). It does not store the data. It is a recipe applied to a source.
- **Intermediate operation:** a step that transforms the stream and returns another stream, such as `filter`, `map`, `sorted` or `distinct`. It only adds a step to the recipe.
- **Terminal operation:** the step that ends the pipeline and produces a result or side effect, such as `collect`, `forEach`, `reduce` or `findFirst`. It starts the actual work.
- **Lazy:** intermediate operations do no work when you call them. Work starts only when a terminal operation is called. This lets Java skip needless work, for example stopping early once `findFirst` has its answer.
- **Stateless vs stateful:** `filter` and `map` look at one element at a time (stateless). `sorted` and `distinct` must see many or all elements before they can pass results on (stateful).
- **map:** turns each element into exactly one new element (1 to 1).
- **flatMap:** turns each element into a stream of zero or more elements, then merges (flattens) all those streams into one stream (1 to many).

**The live scenario**
An order-export service processes 50,000 orders per run, and each order has about 4 items. A developer wrote `orders.stream().map(this::enrich)` to enrich the orders but forgot a terminal operation. The job finished in milliseconds and reported success, yet nothing was enriched, because nothing had run. A second bug appeared in the same code. To list all items, they used `map(o -> o.items())` and got a stream of lists (50,000 lists) instead of a stream of 200,000 items. A third developer stored a stream in a field and reused it, which threw `IllegalStateException`.

**What the interviewer is really checking**
Whether you understand that streams are lazy and single-use, and whether you can choose between `map` and `flatMap` by looking at the shape of the data.

**How I answer it**
1. **Split operations into two kinds.** Intermediate operations return a stream and only describe the work. Terminal operations return a result (or nothing) and trigger the work. Without a terminal operation, nothing executes.
2. **Explain laziness.** Elements flow through the whole pipeline one at a time, not step by step over the whole list. So `filter` then `map` then `findFirst` can stop after the first match without touching the rest. Stateful operations like `sorted` are an exception, because they must collect all elements first.
3. **State the single-use rule.** After a terminal operation, the stream is closed. Using it again throws `IllegalStateException`. To process the data again, create a new stream from the source.
4. **Explain `map`.** Use it when each input gives exactly one output, such as `order -> order.id()`. The stream length stays the same.
5. **Explain `flatMap`.** Use it when each input gives a collection or stream of outputs and you want one combined stream. With `map`, you would get `Stream<Stream<Item>>` or `Stream<List<Item>>`. `flatMap` removes that extra layer.

```java
orders.stream().flatMap(o -> o.items().stream()).collect(toList());
```

**Trade-offs and what can go wrong**
- Forgetting the terminal operation means silent no-op code, with no error.
- Reusing a stream throws `IllegalStateException`.
- Side effects inside `map` or `filter` (database calls, mutating shared state) are risky. Because of laziness and possible short-circuiting, they may run fewer times than you expect, or in an unexpected order.
- `sorted` and `distinct` hold elements in memory, which is costly on large data.
- `flatMap` on a null stream returned by the mapper can cause a `NullPointerException`. Return an empty stream instead.

**How I'd monitor it**
- Unit tests that assert the result, so a missing terminal operation fails the test.
- IDE and static-analysis warnings for unused stream results.
- Splunk search for `IllegalStateException` with the text "stream has already been operated upon or closed" after deployments.
- Temporary `peek` logging at debug level to see which elements actually flow through.

**Follow-ups to expect**
- *Is `findFirst` terminal or intermediate?* -> Terminal, and short-circuiting: it can finish without reading the whole source.
- *Difference between `map` and `forEach`?* -> `map` is intermediate and returns a stream; `forEach` is terminal and returns nothing.
- *How do you turn `Optional<Stream>` or nested lists into one list?* -> Use `flatMap` to flatten one level, then `collect`.

**60-second answer**
A stream has intermediate and terminal operations. Intermediate ones like `filter`, `map`, `sorted` and `distinct` are lazy: they return a stream and just add a step to the pipeline. Nothing runs until a terminal operation such as `collect`, `forEach`, `reduce` or `findFirst` is called. After that the stream is used up, and reusing it throws an exception. `map` turns each element into exactly one element. `flatMap` turns each element into a stream and flattens all of them into one, for example `orders.stream().flatMap(o -> o.items().stream())` gives a stream of items instead of a stream of lists. A common bug is a pipeline with no terminal operation, which silently does nothing.

### Q11 [mid] Write a stream that groups employees by department and gets the average salary.
tags: java8, streams, collectors, groupingby, averagingdouble, tomap, basics

**Start here: the concepts**
- **Stream**: a pipeline that reads elements from a source (like a list) and processes them step by step without changing the source. It exists so you can say *what* you want instead of writing loops.
- **Collector**: the final step of a stream that gathers the elements into a result, such as a list, a map or a number. `collect(...)` takes one.
- **`groupingBy`**: a collector that sorts elements into buckets by a key. Here the key is the department, so you get a `Map<String, ...>` with one entry per department.
- **Downstream collector**: the second argument to `groupingBy`. It says what to do with the elements in each bucket. `averagingDouble` means "average this number over the bucket", so each department maps to its average salary.
- **Method reference (`Employee::dept`)**: a short form of a lambda that calls the method on each element. It is the "how to get the key" function.
- **`partitioningBy`**: like `groupingBy`, but the key is true/false from a condition, so there are always exactly two buckets.
- **`toMap`**: builds a map from a key function and a value function. Two elements giving the same key are a conflict.
- **Other collectors**: `counting` counts elements, `joining` glues strings together, and `teeing` (Java 12) runs two collectors on the same stream and combines their results.

**The live scenario**
A nightly payroll report covered 50,000 employees across 40 departments. A developer wrote `toMap(Employee::dept, Employee::salary)` to "get salary per department". It worked on the 20-row test file. In production it failed at 2 a.m. with `IllegalStateException: Duplicate key`, because many employees share a department. The report was late and finance noticed. The fix was `groupingBy` with `averagingDouble`, which handles many employees per key by design.

**What the interviewer is really checking**
Whether you know `groupingBy` with a downstream collector, and whether you understand the difference between grouping many elements per key and `toMap`, which expects one per key.

**How I answer it**
1. Start the stream with `emps.stream()`. The source list is not modified.
2. Call `collect(Collectors.groupingBy(Employee::dept, downstream))`. The first argument picks the bucket for each employee, so all employees with the same department land together.
3. Use `Collectors.averagingDouble(Employee::salary)` as the downstream collector. It turns each bucket into one average, so the result is `Map<String, Double>`. Without a downstream collector you would get lists of employees instead.
4. The finished code:
```java
Map<String, Double> avg = emps.stream()
    .collect(Collectors.groupingBy(Employee::dept,
             Collectors.averagingDouble(Employee::salary)));
```
5. Mention the neighbours. `partitioningBy` for a yes/no split. `counting` for headcount per department. `joining` for strings. `teeing` for two results in one pass, for example sum and count. `teeing` needs Java 12 or later, so it is not available on Java 11.
6. For `toMap`, say that duplicate keys throw `IllegalStateException` unless you pass a merge function, such as `toMap(k, v, Double::sum)`. The merge function tells Java how to combine two values with the same key.

**Trade-offs and what can go wrong**
- A `null` department makes `groupingBy` throw `NullPointerException`, because the key function must not return null. Clean the data or map nulls to "UNKNOWN".
- The default result is a `HashMap`, so iteration order is not guaranteed. Pass `TreeMap::new` as the second argument if you need sorted output.
- `averagingDouble` uses `double`, so it is not exact for money. Use `BigDecimal` with a custom reduction when pennies matter.
- `partitioningBy` always contains both `true` and `false` keys, even if one is empty. `groupingBy` only creates keys that actually appear.
- A department with no employees will not appear in the result.

**How I'd monitor it**
- Unit tests with duplicate departments, a null department and an empty list.
- Splunk search for `"Duplicate key"` or `"element cannot be mapped to a null key"` in the report job's logs, with an alert on any hit.
- Track report job duration and input row count, so a sudden change shows up.

**Follow-ups to expect**
- *Why did `toMap` fail here?* -> It expects one value per key and throws `IllegalStateException` on duplicates. Add a merge function, or use `groupingBy`.
- *What happens with a null department?* -> `groupingBy` throws `NullPointerException`. Filter those employees out or substitute a default key.
- *How would you get average and count together?* -> Use `teeing` (Java 12+), or `summarizingDouble`, which gives count, sum, min, max and average in one go.

**60-second answer**
I stream the employee list and call `collect` with `Collectors.groupingBy`. The first argument is `Employee::dept`, which puts employees with the same department in one bucket. The second argument is the downstream collector `averagingDouble(Employee::salary)`, which turns each bucket into its average, so I get a `Map<String, Double>`. I would not use `toMap` here, because it throws `IllegalStateException` on duplicate keys unless I give it a merge function. I also watch for null departments, which cause a `NullPointerException`. Related collectors are `partitioningBy` for true/false splits, `counting`, `joining`, and `teeing`, which arrived in Java 12.

### Q12 [mid] How should Optional be used - and abused?
tags: optional, java8, null-safety, return-types, lazy-evaluation, functional-style, basics

**Start here: the concepts**
- **null**: a reference that points to nothing. Calling a method on it throws `NullPointerException` (NPE). The compiler never warns you, so a method that might return null is a hidden trap for its callers.
- **Optional<T>** (added in Java 8): a small container that holds either one value or nothing. It exists so a method signature can say "this result may be missing", and the caller is pushed to handle that case.
- **Return type**: what a method hands back. This is the place Optional was designed for.
- **Eager vs lazy evaluation**: eager means the work is done immediately, whether or not it is needed. Lazy means it is done only when needed.
- **Supplier**: a tiny piece of code (a lambda) that produces a value only when it is called. It is how you ask for lazy work.
- **Serialization**: turning an object into bytes to send or store it. `Optional` does not implement `Serializable`.

**The live scenario**
An order service handles about 2,000 requests per second. A developer wrote `cache.find(id).orElse(loadFromDatabase(id))`. The cache hit rate was 95%, yet database load matched the full request rate. Java evaluates method arguments before the call, so `loadFromDatabase(id)` ran every time, even when the cache had a value. Changing it to `orElseGet(() -> loadFromDatabase(id))` cut database calls to roughly 5% of requests. In the same codebase a bare `.get()` on an empty Optional caused intermittent 500 errors (`NoSuchElementException`). That is just an NPE in a different form.

**What the interviewer is really checking**
Whether you know Optional's narrow purpose (a return type that makes absence explicit) and can name the common misuses, including the subtle `orElse` vs `orElseGet` cost.

**How I answer it**
1. **Use it as a return type** where "no result" is a normal outcome, such as `findById`. The signature then forces the caller to deal with absence instead of forgetting a null check.
2. **Chain instead of unwrapping.** Use `map`, `filter` and `orElseThrow` so the code reads as one flow:
   ```java
   repo.findById(id).map(Order::toDto).orElseThrow(NotFound::new);
   ```
3. **Don't use it for fields or method parameters.** It was not designed for them. It is not serializable, it adds an extra object, and a caller can still pass `null` instead of an Optional. For an optional parameter, use method overloads.
4. **Don't wrap collections.** Return an empty list. "Empty" already means "nothing", so `Optional<List<T>>` has two ways to say "none" and callers must check both.
5. **Avoid `get()`.** If the Optional is empty it throws. The stored advice, `isPresent()` then `get()`, is just a null check with extra steps. Prefer `orElseThrow()` (no-argument version since Java 10), `orElse`, `map` or `ifPresent`.
6. **Prefer `orElseGet` for anything costly.** `orElse(x)` always evaluates `x`. `orElseGet(supplier)` runs only when the Optional is empty. `orElse` is fine for cheap constants such as `orElse("N/A")`.
7. **Never return null from a method that returns Optional**, and use `ofNullable` (not `of`) when the value may be null, because `Optional.of(null)` throws an NPE.

**Trade-offs and what can go wrong**
- Optional adds an object allocation. This is negligible for normal business code but matters in hot loops. For primitives use `OptionalInt`, `OptionalLong` and `OptionalDouble`.
- Overuse hurts readability, for example `Optional.ofNullable(x).isPresent()` instead of `x != null`.
- Using it as a JSON/DTO field or JPA entity field leads to serialization and mapping problems.
- Do not use Optional as a map key or as a collection element.
- `orElseGet` is only lazy if the supplier is the expensive part. A side effect hidden inside `orElse` is a real bug.

**How I'd monitor it**
- **Splunk:** search for `NoSuchElementException "No value present"`. It points to a stray `get()`, so group by stack trace to find the class.
- **Static analysis:** turn on the IDE and SonarQube rules for `Optional.get()` without a check and for Optional used as a field or parameter.
- **Performance:** compare database or remote-call counts per request against expected cache hit rates. A mismatch suggests an eager `orElse`.
- **Code review:** grep for `.get()` on Optionals and `orElse(` followed by a method call.

**Follow-ups to expect**
- *Why is Optional a bad parameter type?* -> It makes call sites clumsy, the caller can still pass null, and overloads express "optional" more clearly.
- *`Optional.of` vs `ofNullable`?* -> `of` throws an NPE on null. `ofNullable` returns an empty Optional.
- *`map` vs `flatMap` on Optional?* -> Use `map` when the function returns a plain value. Use `flatMap` when it already returns an Optional, to avoid `Optional<Optional<T>>`.

**60-second answer**
Optional is meant to be a return type that says "this result may be missing", for example a `findById` method. I chain `map` and `orElseThrow` rather than unwrapping manually. I don't use Optional for fields, method parameters or collections: it isn't serializable, callers can still pass null, and for collections an empty list already means "nothing". I avoid bare `get()` because it throws when the Optional is empty, and I prefer `orElseThrow()`. And I use `orElseGet` instead of `orElse` for expensive defaults, because `orElse` evaluates its argument every time. In one service, that mistake caused a database call on every request even when the cache had the value.

### Q13 [mid] How do you make a class truly immutable?
tags: java, immutability, records, defensive-copy, thread-safety, collections, basics

**Start here: the concepts**
- **Immutable object:** an object whose state cannot change after the constructor finishes. Every read gives the same answer for the object's whole life. It exists so you can share an object freely without worrying that someone changes it.
- **`final` field:** a field that can be assigned only once. It stops you re-pointing the field, but it does not stop changes inside the object it points to. A `final List` can still have items added.
- **Mutable input/output:** an object such as `List`, `Date` or an array that others can modify. If your class stores the caller's reference, the caller can change your internals later.
- **Defensive copy:** making your own private copy of a mutable object when you receive it, and again when you hand it out. Nobody else then holds a reference to your internals.
- **`this` escape:** leaking the half-built object (`this`) from inside the constructor, for example registering it as a listener. Other threads can then see it before its fields are set.
- **Unmodifiable vs immutable:** `Collections.unmodifiableList(x)` is only a read-only view, and changes to `x` still show through it. `List.copyOf(x)` (Java 10+) makes a separate immutable copy and rejects nulls.
- **Record (Java 16+):** a short syntax for a data class. Its fields are `private final` and the class is `final`. It is only *shallow* immutable: the fields cannot be re-pointed, but the objects they point to may still be mutable.
- **Thread-safe:** safe when many threads use it at once. Immutable objects need no locks because nobody can write.

**The live scenario**
A pricing service caches a `PricingRule` object with a `Date validFrom` field and a getter returning that field directly. About 200 request threads share it. One code path called `rule.getValidFrom().setTime(...)` to compute a "grace period". For roughly 40 minutes, about 3% of requests (illustrative) saw wrong validity windows and quoted wrong prices. There were no exceptions, and the bug could not be reproduced locally. The cause was that the object was "final-ish" but not immutable.

**What the interviewer is really checking**
Whether you know that `final` alone is not enough. They want to hear about mutable fields, defensive copies, and why immutability gives thread safety.

**How I answer it**
1. **Make the class `final`** (or give it private constructors). A subclass could otherwise override methods and add mutable state.
2. **Make all fields `private final`.** Nobody outside can touch them, and they are assigned once. The Java memory model also guarantees that other threads see `final` fields fully set once construction finishes, as long as `this` did not escape.
3. **Provide no setters** and no method that changes state. Operations return a new object instead (like `String.toUpperCase()`).
4. **Copy mutable inputs in the constructor.** Otherwise the caller keeps a reference and can change your state later.
5. **Copy mutable outputs in getters**, or return immutable types. Otherwise a caller can change your state through the returned reference.
6. **Don't let `this` escape the constructor.** Another thread could see the object before its fields are assigned.
7. **Today, use a `record`** and copy collections in the compact constructor:
```java
record Order(String id, List<String> items) {
  Order { items = List.copyOf(items); }
}
```
8. **Conclusion:** because nothing can change, there is nothing to race on, so the object is thread-safe without locks. It must still be published safely, which rules 2 and 6 cover.

**Trade-offs and what can go wrong**
- Every "change" creates a new object. This is cheap for small objects but costly for large ones that change often. `StringBuilder` or builders help.
- `List.copyOf` is shallow. If the elements are mutable, the list is still effectively mutable, so the elements must be immutable too.
- A record holding an array or `Date` is not immutable unless you copy it in the constructor and in the accessor.
- `unmodifiableList` is not a defensive copy.
- Frameworks that need setters or no-arg constructors (some ORM or JSON setups) can conflict with this design.

**How I'd monitor it**
- Unit tests that mutate the source list or date after construction and assert the object did not change.
- Static analysis: SpotBugs flags exposed internal representation (EI_EXPOSE_REP), and Error Prone has an `@Immutable` check.
- Code review checklist for shared or cached objects.
- In Splunk, log the object's id and key values at read time. Searching for the same id with different values reveals hidden mutation.

**Follow-ups to expect**
- *Why is `String` immutable?* -> It is used as a HashMap key, for security (file paths, class names), and for string pooling and thread safety. A mutable key would break lookups.
- *Is `Collections.unmodifiableList` the same as `List.copyOf`?* -> No. The first is a live read-only view of the original list, and the second is an independent immutable copy.
- *Is a record deeply immutable?* -> No, only shallow. Mutable components need defensive copies.

**60-second answer**
To make a class truly immutable, I make it `final`, mark all fields `private final`, and provide no setters. If a field is mutable, like a list or a date, I copy it on the way in and on the way out, or I use `List.copyOf`. I also don't let `this` escape the constructor. `final` alone is not enough, because a final list can still be changed from outside. Today I'd use a record, but it is only shallow immutable, so I copy collections in the compact constructor. Immutable objects are thread-safe because nothing can change after construction, so I need no locks.

### Q14 [senior] When does `parallelStream()` hurt?
tags: java8, streams, parallel-stream, forkjoinpool, concurrency, basics

**Start here: the concepts**
- **Stream:** a pipeline that processes a collection step by step (filter, map, sum). `stream()` runs on one thread. `parallelStream()` splits the data and runs the pieces on several threads.
- **Common ForkJoinPool:** one JVM-wide pool of worker threads, shared by all parallel streams. It is also used by `CompletableFuture.supplyAsync` when you pass no executor. By default it has about (CPU cores - 1) threads, and the calling thread helps too. It exists so CPU-heavy work can use all cores without every caller creating its own threads.
- **CPU-bound vs blocking (I/O) work:** CPU-bound work keeps a core busy computing. Blocking work (a DB query, an HTTP call) holds a thread while it waits and does no computing.
- **Splitting:** the stream cuts the source into halves recursively. Arrays and `ArrayList` split cheaply by index. `LinkedList` or `Stream.iterate` split badly.
- **Stateless lambda:** it uses only its input, with no shared variables to modify. Shared mutable state in parallel code causes races.

**The live scenario**
An 8-core order service has a common pool of 7 threads. For each order it calls `items.parallelStream().map(pricingClient::fetch)`, and each REST call takes about 200 ms. Under light load it looks faster. At peak, 50 requests each submit 20 blocking calls, so all 7 workers sit waiting on sockets. Everything else on the common pool queues behind them, including a nightly report's parallel streams and a few `supplyAsync` calls. p99 latency goes from 300 ms to 6 s while CPU stays at 15%. Nothing is computing, yet everything is slow.

**What the interviewer is really checking**
Whether you know that parallel streams share one hidden pool, and that "parallel" does not mean "faster". A senior should explain when the split overhead and blocking outweigh the gain, and what to use instead.

**How I answer it**
1. **Name the shared pool.** All parallel streams use the one common pool. One blocking pipeline can therefore stall unrelated code across the JVM, which is a bug that is hard to trace.
2. **Say when it helps.** It helps only for CPU-bound work on a large, cheaply splittable source (arrays, `ArrayList`, ranges) with stateless, non-blocking lambdas. Each element's work must be big enough to pay for splitting, scheduling and merging.
3. **Say when it hurts.**
   - Blocking calls starve the pool, as in the scenario.
   - Small data costs more in overhead than it saves.
   - Poor splitting sources like `LinkedList` or `iterate` lose the gain.
   - Order-dependent or stateful operations (`sorted`, `distinct`, `limit`, `findFirst` on ordered streams) need coordination.
   - Shared mutable state gives wrong results. Non-associative reductions give wrong results too.
4. **Give the alternative for I/O.** Use an explicit, bounded executor with `CompletableFuture`, so a slow dependency only exhausts your own pool. On Java 21, use virtual threads, which are cheap threads that release the carrier thread while blocked:
```java
try (var ex = Executors.newVirtualThreadPerTaskExecutor()) { /* submit calls */ }
```
Note that this replaces the parallel stream. A parallel stream always runs on ForkJoin threads, not virtual threads.
5. **Measure.** Benchmark with realistic data and concurrent load (JMH or a load test). A single-user test hides the starvation.

**Trade-offs and what can go wrong**
- Custom executors need sizing and shutdown, and their queues must be bounded, but they give isolation.
- Running a parallel stream inside your own `ForkJoinPool` is a widely used trick, but it is not a documented guarantee. I would not rely on it.
- Parallel stream exceptions and debugging are harder, and the results can differ from sequential runs if the lambdas are not pure.
- Changing the common pool size with `-Djava.util.concurrent.ForkJoinPool.common.parallelism` is a global change that affects all users of the pool.

**How I'd monitor it**
- Thread dumps or JFR: many `ForkJoinPool.commonPool-worker-N` threads in socket read or JDBC calls.
- `ForkJoinPool.commonPool()` getters (`getActiveThreadCount`, `getQueuedSubmissionCount`), exposed as metrics.
- p99 latency up while CPU stays low is the typical signature of starvation.
- Splunk: search logs by thread name `commonPool-worker` and compare durations of calls running there.
- Alert on the dependency's latency and on executor queue depth for any custom pool.

**Follow-ups to expect**
- *How many threads does the common pool have?* -> By default cores - 1, and the calling thread also does work. It is configurable through a system property, but that is global.
- *Why can `parallelStream().forEach(list::add)` fail?* -> `ArrayList` is not thread-safe, so you can lose elements or get exceptions. Use `collect`, which handles combining safely.
- *Do virtual threads make parallel streams good for I/O?* -> No. Parallel streams still run on the common pool. Submit the I/O tasks to a virtual-thread executor (Java 21) instead.

**60-second answer**
"`parallelStream()` runs on the common ForkJoinPool, which is shared by the whole JVM and has roughly cores-minus-one threads. It pays off only for CPU-heavy work on big, easy-to-split data like arrays or ArrayList, with stateless lambdas. It hurts when the lambda blocks on a DB or HTTP call, because those few threads get stuck waiting and everything else on the pool queues behind them. In production that shows up as high latency with low CPU. It also hurts on small data, bad-splitting sources like LinkedList, ordered or stateful operations, and shared mutable state. For I/O I use my own bounded executor with CompletableFuture, or virtual threads on Java 21. And I always measure under concurrent load, not just a single-user test."

### Q15 [senior] Explain generics, type erasure and PECS.
tags: java, generics, type-erasure, pecs, wildcards, collections, java8, basics

**Start here: the concepts**
- **Generics**: type parameters such as `List<String>`. They let the compiler check what goes into and comes out of a container, so you don't cast by hand. They exist to turn runtime `ClassCastException`s into compile errors.
- **Type erasure**: after checking your code, the compiler removes the type arguments and inserts casts where needed. At runtime `List<String>` and `List<Integer>` are the same class, `List`. Java did this so code compiled before Java 5 would keep working.
- **Consequences of erasure**: the JVM doesn't know `T`, so `new T()`, `new T[10]` and `instanceof List<String>` are illegal. `instanceof List<?>` is allowed because it makes no claim about the type argument.
- **Invariance**: `List<Integer>` is *not* a `List<Number>`, even though `Integer` is a `Number`. If it were, you could add a `Double` to a list that is really a `List<Integer>`.
- **Wildcard `?`**: "some unknown type". `? extends Number` means "Number or any subtype". `? super Integer` means "Integer or any supertype".
- **PECS**: **P**roducer **E**xtends, **C**onsumer **S**uper. If a collection *gives you* values, use `extends`. If it *takes in* values, use `super`.

**The live scenario**
A shared pricing library had `double total(List<Number> items)`. About 40 callers passed `List<BigDecimal>` or `List<Integer>`, which doesn't compile. Someone "fixed" it with raw `List` and casts. At 3 a.m. roughly 2% of requests failed with `ClassCastException`, thrown far from the code that put a `String` into the list. The fix was `total(List<? extends Number>)`, which restored compile-time safety.

**What the interviewer is really checking**
Whether you understand that generics are a compile-time feature only, and can use wildcards correctly in an API signature rather than reciting the acronym.

**How I answer it**
1. **State that generics are compile-time checking.** The reason is that the compiler checks the types and then erases them, so no runtime cost or class change is needed.
2. **Name the limits of erasure.** There is no `new T()`, no generic array creation, and no `instanceof List<String>`, because the type argument doesn't exist at runtime. The workaround is to pass a `Class<T>` token.
3. **Explain invariance.** `List<Integer>` is not a `List<Number>`, because otherwise the compiler couldn't stop you from adding a `Double` to it.
4. **Introduce wildcards as the fix, then give PECS.**
   - `List<? extends Number>` is a *producer*. You can safely read items as `Number`, but you can't add anything (except `null`), because the real element type is unknown.
   - `List<? super Integer>` is a *consumer*. You can safely add `Integer`s, but what you read back is only `Object`.
5. **Give the classic example.** `Collections.copy` reads from the source and writes to the destination:
```java
static <T> void copy(List<? super T> dest, List<? extends T> src)
```
6. **Say when to skip wildcards.** If a method both reads and writes the same list, use a plain type parameter `<T>`. Wildcards are for parameters, not return types.

**Trade-offs and what can go wrong**
- Raw types (`List` with no argument) switch checking off. Mixed types can enter the list, which is called *heap pollution*, and the failure appears later at a compiler-inserted cast.
- Unchecked warnings are real warnings. Suppressing them hides the problem.
- Wildcard-heavy signatures are harder to read. Use them in public APIs, not everywhere.
- Erasure can make two overloads clash, for example `f(List<String>)` and `f(List<Integer>)` have the same signature after erasure.

**How I'd monitor it**
- Compile with `-Xlint:unchecked` and fail the build on new warnings.
- Use static analysis, such as SonarQube or Error Prone, to flag raw types.
- In Splunk, search for `ClassCastException` and group by the top stack frame. A cluster pointing at generic code suggests heap pollution.

**Follow-ups to expect**
- *Why can't I create `new T[10]`?* -> Arrays check their element type at runtime, but `T` is erased, so the check is impossible. Use `List<T>` or `Array.newInstance` with a `Class<T>`.
- *What is a bridge method?* -> A synthetic method the compiler generates so an overriding method with specific types still matches the erased signature of the generic parent.
- *`List<?>` vs `List<Object>`?* -> `List<Object>` accepts only lists declared as `List<Object>`, but you can add anything to it. `List<?>` accepts any list, but you can't add anything (except `null`).

**60-second answer**
Generics let the compiler check types, and then it erases them. At runtime `List<String>` and `List<Integer>` are both just `List`. That is why you can't write `new T()` or `instanceof List<String>`. Generics are also invariant, so a `List<Integer>` is not a `List<Number>`. Wildcards fix that, and PECS tells you which one to use. If the collection produces values you read, use `? extends`. If it consumes values you write, use `? super`. `Collections.copy(dest, src)` is the example: `dest` is `super`, `src` is `extends`. I also avoid raw types, because they bypass the checks and the failure shows up later as a `ClassCastException`.

### Q16 [senior] How can a Java application leak memory despite the GC?
tags: java, memory-leak, garbage-collection, heap-dump, threadlocal, eclipse-mat, basics

**Start here: the concepts**
- **Heap**: the memory area where Java objects live. It has a fixed maximum size (`-Xmx`).
- **Garbage collector (GC)**: a background process that frees objects the program can no longer reach, so you don't call `free()` yourself.
- **GC root**: a starting point the GC always trusts. Examples are static fields, local variables on a running thread's stack, and live threads. An object is *reachable* if you can follow references from a root to it. The GC frees only unreachable objects.
- **Memory leak in Java**: objects you will never use again but that are still reachable, so the GC must keep them. The heap grows until `OutOfMemoryError`.
- **ThreadLocal**: a variable with one separate value per thread. Pooled threads (such as Tomcat workers) live for the whole application, so a value left in a ThreadLocal lives just as long.
- **Classloader**: the object that loads classes. A class and its static fields stay alive while its classloader is reachable. Application servers create a new classloader on each redeploy, and class metadata lives in **Metaspace** (Java 8+; older versions used PermGen).
- **Heap dump**: a snapshot file of every object on the heap. **Eclipse MAT** opens it. The **dominator tree** shows which objects keep the most memory alive. **Path to GC roots** shows the reference chain that stops an object from being freed.

**The live scenario**
An order service has a 4 GB heap. After about three days, old-generation usage climbs from 1.5 GB to nearly 4 GB. Full GCs run every few seconds, p99 latency goes from 200 ms to 6 s, and then pods die with `OutOfMemoryError`. A restart "fixes" it for another three days. The heap dump shows a `static HashMap<String, UserSession>` with 2 million entries and no eviction. Nothing was wrongly freed. The map simply kept everything reachable.

**What the interviewer is really checking**
Whether you understand that GC works on *reachability, not usefulness*, and whether you can name realistic leak patterns and the tools to find them. A senior should also mention heap versus off-heap/Metaspace.

**How I answer it**
1. **Define the leak.** The GC frees unreachable objects only. A leak is an object that is reachable but unused. This reframes the question to "who still holds a reference?"
2. **Name the common causes.**
   - Static maps or caches with no eviction. A static field is a GC root, so everything in it lives forever.
   - Listeners or callbacks registered but never removed. The event source holds them.
   - `ThreadLocal` not cleared on pooled threads. Call `remove()` in a `finally` block, because the thread never dies.
   - Unclosed resources (streams, connections, JDBC statements). They hold native memory or handles, which can run out even when the heap looks fine.
   - Classloader leaks on redeploy. One lingering reference, such as a thread or driver registration, keeps the whole old classloader alive, and Metaspace grows with each redeploy.
   - A mutable `HashMap` key. If a field used by `hashCode()` changes after insertion, the entry sits in the wrong bucket. You can't find it or remove it, but the map still references it.
3. **Confirm it is a leak.** Look at heap *after* full GCs. If that floor keeps rising, it is a leak. A high but stable floor means the heap is simply too small.
4. **Capture a heap dump** (or set `-XX:+HeapDumpOnOutOfMemoryError`):
   `jcmd <pid> GC.heap_dump /tmp/heap.hprof`
5. **Analyse it in MAT.** Open the dominator tree, find the biggest retainer, then use "path to GC roots" to see the exact field or thread holding it. Fix that reference, not the symptom.

**Trade-offs and what can go wrong**
- A heap dump pauses the JVM, and by default `GC.heap_dump` runs a full GC first. The file is roughly heap-sized and may contain sensitive data, so protect it.
- Raising `-Xmx` only delays the crash.
- Bounded caches (such as Caffeine, with size and TTL) fix the unbounded-map case, but a bad size limit causes churn.
- `WeakReference` helps in some cases but can hide the real design problem.
- Off-heap leaks (direct ByteBuffers, native code) do not show up in a heap dump.

**How I'd monitor it**
- Heap used after each full GC (a rising floor), GC pause time and frequency, and Metaspace usage.
- Alert on old-gen usage above about 80% after GC.
- Compare two heap dumps taken hours apart to see which class counts grow.
- Use Native Memory Tracking (`-XX:NativeMemoryTracking`) if the process RSS grows but the heap is flat.
- In Splunk, search for `OutOfMemoryError` and GC-log pause spikes.

**Follow-ups to expect**
- *Does `WeakHashMap` solve cache leaks?* -> Only partly. Keys are weakly held and entries vanish when the key is unreachable. Values that strongly reference their key still leak, and it gives no size or TTL control.
- *Why are ThreadLocals dangerous in thread pools?* -> Pool threads never die, so each thread's stored value (and its classloader) stays reachable unless `remove()` is called.
- *How do you tell a leak from a too-small heap?* -> A leak shows a steadily rising post-GC floor. A too-small heap shows a flat but high floor with frequent GCs.

**60-second answer**
The GC only frees objects nobody can reach, so a Java leak means objects that are still reachable but never used again. Typical causes are static caches with no eviction, listeners never removed, ThreadLocals not cleared on pooled threads, unclosed resources, old classloaders kept alive after redeploys, and mutable keys in a HashMap. I first check whether heap after full GC keeps rising. Then I take a heap dump with `jcmd <pid> GC.heap_dump <file>`, open it in Eclipse MAT, and read the dominator tree and path to GC roots to see who holds the objects. I fix the reference, for example by bounding the cache or calling `remove()` in a `finally`. I don't just raise the heap, and I alert on a rising post-GC heap floor.

### Q17 [senior] Why is Java serialization discouraged and what is serialVersionUID for?
tags: java serialization, serialVersionUID, objectinputfilter, deserialization security, gadget chains, schema evolution, basics

**Start here: the concepts**
- **Serialization**: turning a live object into bytes so it can be saved or sent. **Deserialization** is the reverse: bytes back into an object. It exists so objects can cross a network, a cache or a disk.
- **Java native serialization**: the built-in form, used when a class implements `Serializable` and is written with `ObjectOutputStream`. The byte stream contains class names and field values, not just data.
- **Gadget chain**: existing classes on the classpath (your code, libraries) that do something dangerous in methods run during deserialization, such as `readObject` or `hashCode`. An attacker crafts bytes that name these classes and chain them together to run code. The attacker writes no code of their own, only bytes.
- **serialVersionUID**: a `long` version stamp written into the stream and compared with the receiving class. If they differ, Java throws `InvalidClassException`. If you don't declare it, Java computes it from the class's structure, so small edits change it.
- **Schema**: an explicit, written contract of fields and types (JSON Schema, Avro, Protobuf). It is separate from your Java classes.
- **ObjectInputFilter**: an allow/deny list for which classes may be deserialized (Java 9+, backported to 8u121+).

**The live scenario**
An order service caches `OrderSession` objects in a shared cache as Java-serialized bytes, across 12 pods. A release adds one field, and nobody declared `serialVersionUID`. During the rolling deploy, new pods fail to read old entries and old pods fail to read new ones. About 30% of requests hit `InvalidClassException` for 20 minutes, and the cache is flushed to recover. Months later, a security scan finds an HTTP endpoint that calls `ObjectInputStream.readObject` on request bodies, with a vulnerable library on the classpath. That is a remote code execution risk.

**What the interviewer is really checking**
Whether you know that serialization is both a security and an evolution problem, not just "a marker interface". They also want to see that you can pick a safer format and defend an existing system when you can't remove serialization yet.

**How I answer it**
1. **Security first.** Deserialization creates objects named by the incoming bytes, and it does not call the constructors of the `Serializable` classes. So the input decides which code runs. Gadget chains turn that into code execution. Never deserialize untrusted bytes.
2. **Then evolution.** The byte format is tied to your class's fields, so renaming or reshaping a class is a breaking change to every stored or in-flight object. The layout is effectively frozen.
3. **Explain serialVersionUID.** It is the compatibility check. Declare it explicitly (`private static final long serialVersionUID = 1L;`) so harmless changes like adding a field don't break reads. Missing fields get defaults. Bump it only for a truly incompatible change. Without it, the computed value shifts with trivial edits.
4. **Be precise about its limits.** It is a version check, not a security control. An attacker can simply supply the matching value.
5. **Recommend alternatives.** Use JSON, Avro or Protobuf with an explicit schema. They carry data only, not arbitrary class names, and they support backward and forward compatibility rules.
6. **If you must keep it,** add an allow-list filter, e.g. `-Djdk.serialFilter=com.acme.dto.*;!*`. This allows only your DTO package and rejects everything else.

**Trade-offs and what can go wrong**
- Binary formats like Avro and Protobuf are less human-readable and need schema management. JSON is easy to read but larger and looser.
- A filter that is too wide gives false safety. Libraries add new gadgets over time, so allow-lists beat deny-lists.
- Hard-coding `serialVersionUID = 1L` and then making an incompatible change causes silent corruption or odd runtime errors instead of a clear exception.
- Teams often forget the hidden uses: HTTP sessions, caches, JMX, RMI, message queues.

**How I'd monitor it**
- In Splunk, search for `InvalidClassException`, `StreamCorruptedException` and filter rejections, and alert on spikes after deploys.
- Scan the code and dependencies for `ObjectInputStream`, `readObject` and known-vulnerable library versions.
- Enable filter logging and check for rejected classes. On JDK 17+, JFR can also record deserialization events.
- During rolling deploys, watch cache error rates per pod version.

**Follow-ups to expect**
- *Does `transient` help?* -> It excludes a field from the stream, so it is restored to its default value. It protects secrets from being written but does not fix the security problem.
- *What if I don't declare serialVersionUID?* -> Java computes one from the class structure, so many harmless changes break compatibility.
- *Are records safer?* -> Records deserialize through their canonical constructor, so validation runs. Native deserialization of untrusted input is still unsafe.

**60-second answer**
Java serialization turns objects into bytes, but on the way back the bytes decide which classes get created. Attackers use that with gadget chains in libraries on the classpath to run code, so deserializing untrusted data is dangerous. It also ties the byte format to your class layout, so changing a class can break stored or in-flight data. `serialVersionUID` is the version stamp, and a mismatch throws `InvalidClassException`. I always declare it explicitly, because the computed default changes with small edits, and it is not a security feature. For new work I use JSON, Avro or Protobuf with an explicit schema. If legacy code must keep serialization, I add an `ObjectInputFilter` allow-list and watch for related errors in the logs.

### Q18 [senior] What is the difference between `Comparable` consistency with equals, and why does `BigDecimal` surprise people?
tags: java, bigdecimal, comparable, equals-hashcode, treeset, hashset, basics

**Start here: the concepts**
- **`equals` and `hashCode`**: `equals` says whether two objects are "the same thing". `HashMap` and `HashSet` use `hashCode` to pick a bucket and then `equals` to confirm a match. Equal objects must have equal hash codes.
- **`Comparable` / `compareTo`**: gives a type a natural ordering. It returns negative, zero or positive. `TreeSet` and `TreeMap` use only `compareTo`. They never call `equals` or `hashCode`.
- **Consistent with equals**: a class is consistent when `a.compareTo(b) == 0` exactly when `a.equals(b)` is true. The Javadoc strongly recommends this, because sorted and hash collections should agree about duplicates.
- **`BigDecimal`**: an exact decimal number made of an unscaled integer plus a **scale** (the number of digits after the point). So `2.0` is 20 with scale 1, and `2.00` is 200 with scale 2.
- **`RoundingMode`**: the rule for dropping extra digits (for example `HALF_UP` or `HALF_EVEN`). It is needed because decimals cannot always be represented exactly.

**The live scenario**
A payments service receives about 1 million transactions a day from two upstream systems. One sends amounts like `10.5`, the other `10.50`. A de-duplication step used `Set<BigDecimal>` on amounts. The `HashSet` version counted both as different, so about 3,000 duplicates slipped through. A report using a `TreeSet` counted them as one, so the two totals never reconciled. Nobody had changed any logic. The two collections simply disagree about what "equal" means for `BigDecimal`.

**What the interviewer is really checking**
Whether you know that `equals`/`hashCode` and `compareTo` can disagree, which collections use which, and whether you handle money safely.

**How I answer it**
1. **State the surprise.** `new BigDecimal("2.0").equals(new BigDecimal("2.00"))` is `false`, because `equals` compares value and scale. `compareTo` returns `0`, because it compares only numeric value. So `BigDecimal` is *not* consistent with equals.
2. **Explain the collection effect.** `hashCode` also depends on scale, so `HashSet` stores both values as separate entries. `TreeSet` uses only `compareTo`, so it keeps one. The same applies to map keys: `HashMap.get` with `2.00` will miss a key stored as `2.0`.
3. **Fix it deliberately.** Normalise the scale before using values as keys, for example `setScale(2, RoundingMode.HALF_UP)`. Alternatively use `stripTrailingZeros()`, which makes `2.0` and `2.00` both `2`. Pick one rule and apply it at the system boundary. Compare values with `compareTo`, never `equals`.
4. **Use the right type for money.** Use `BigDecimal` with an explicit scale and `RoundingMode`. Never use `double`, which is binary and cannot represent most decimals exactly.
5. **Construct from `String`.** `new BigDecimal("0.1")` is exact. `new BigDecimal(0.1)` captures the binary error and gives 0.1000000000000000055511523... If you only have a `double`, use `BigDecimal.valueOf(double)`, which goes through the double's string form.

```java
new BigDecimal("2.0").equals(new BigDecimal("2.00"));    // false
new BigDecimal("2.0").compareTo(new BigDecimal("2.00")); // 0
```

**Trade-offs and what can go wrong**
- Normalising costs a little CPU and must be applied everywhere. One missed path brings the bug back.
- `divide` without a scale or `MathContext` throws `ArithmeticException` when the result does not terminate (for example 1/3).
- `stripTrailingZeros` can turn `100` into `1E+2`, which looks odd when printed. Use `toPlainString()` for display.
- A custom `Comparator` on a `TreeSet` that is inconsistent with equals can silently drop elements. The `Set` contract is then not followed.

**How I'd monitor it**
- Unit tests asserting that `2.0` and `2.00` behave the same in your keys and sets.
- Static analysis (SpotBugs, Sonar) flagging `new BigDecimal(double)`.
- A Splunk search comparing daily record counts and totals between the hash-based and sorted paths, with an alert on any non-zero difference.
- Log amounts with their scale so mismatches are visible.

**Follow-ups to expect**
- *Does `equals` on `BigDecimal` ignore scale?* -> No. It compares value and scale. Use `compareTo` for numeric equality.
- *Why is `new BigDecimal(0.1)` not 0.1?* -> The `double` is already slightly off in binary, and the constructor copies that exact value.
- *Which classes in the JDK have this inconsistency?* -> `BigDecimal` is the best-known one. Any class whose `compareTo` ignores something `equals` checks has the same problem.

**60-second answer**
`Comparable` is consistent with equals when `compareTo` returns 0 exactly when `equals` is true. `BigDecimal` breaks that rule. `2.0` and `2.00` have different scales, so `equals` and `hashCode` treat them as different, while `compareTo` returns 0. A `HashSet` therefore keeps both, and a `TreeSet`, which uses only `compareTo`, keeps one. I would normalise scale before using values as keys and compare with `compareTo`. For money I use `BigDecimal` with an explicit scale and `RoundingMode`, never `double`, and I build it from a `String` so no binary error gets in.

### Q19 [fresher] Which Java versions are LTS and which one should a new project use in 2026?
tags: java, lts, java-versions, java-21, java-25, release-cadence, basics

**Start here: the concepts**
- **Java release:** Since Java 9, a new Java version ships every six months (March and September). Each one adds features and fixes.
- **Support:** The vendor (Oracle, or others such as Eclipse Temurin and Amazon Corretto) publishes security and bug-fix updates for a version only for a limited time. After that, you run known-vulnerable software unless you upgrade.
- **LTS (Long-Term Support):** A release the vendors promise to patch for years. It exists so companies can stay on one stable version without upgrading every six months.
- **Non-LTS release:** A release patched only until the next release arrives, roughly six months. It is good for trying new features, not for long-lived systems.
- **Current LTS list:** Java 8, 11, 17, 21 and 25. Since 17, a new LTS comes every two years (17 in 2021, 21 in 2023, 25 in September 2025). Java 9, 10, 12-16, 18-20 and 22-24 are non-LTS.
- **Baseline version:** The minimum Java a framework needs. For example, Spring Boot 3 requires Java 17 or newer.

**The live scenario**
A team (illustrative numbers) starts a payments service on a non-LTS release because it has a feature they like. Six months later the vendor stops patching it. A security fix lands only in the newer release, so the team must upgrade that service. They now own 40 services, so a "quick" bump turns into weeks of testing and rollouts. Teams on an LTS plan the same upgrade once every two years, on their own schedule.

**What the interviewer is really checking**
Whether you know what "LTS" means and why companies care. They also want to see that you can choose a version based on support, framework compatibility and features, not just "the newest."

**How I answer it**
1. **Name the LTS versions: 8, 11, 17, 21, 25.** Then explain that LTS means years of patches, while non-LTS means about six months. This shows you understand the idea, not just a list.
2. **Say the new project should start on Java 21 or 25.** Java 25, released September 2025, is the newest LTS, so it has the longest support runway. Java 21 is a very safe choice because it has been in production since 2023 and most libraries and tools are well tested on it.
3. **Check what your framework and platform support before deciding.** Your Spring Boot version, build tools, container base images and company standards may limit you. Choose the newest LTS that all of them support.
4. **Avoid non-LTS releases for production.** They save nothing and force frequent upgrades. Use them only to experiment.
5. **Mention the features that justify moving off old LTS versions.** Java 17 gave records and sealed classes. Java 21 made virtual threads final. Java 8 and 11 are still common in older systems, but new code gains little by starting there.

```
java -version   # confirm which JDK your build and runtime actually use
```

**Trade-offs and what can go wrong**
- Newest LTS (25): the longest support, but some libraries or tools may lag. Test your dependencies.
- 21: very mature, but its support window ends earlier than 25's.
- Staying on 8 or 11: libraries are dropping support, and you often depend on paid or extended vendor support.
- Common mistake: "LTS" is mostly a vendor support promise, not a language feature. Support length and dates differ by vendor, so check yours.
- Another mistake: developing on one JDK and running another in production.

**How I'd monitor it**
- Keep an inventory of the Java version for every service, from CI configs and container images.
- Alert or report on versions approaching their vendor end-of-support date.
- Run dependency and vulnerability scans (e.g. OWASP Dependency-Check) in CI.
- Log the JVM version at startup (`java.version`) so you can search for it in Splunk and spot stragglers.

**Follow-ups to expect**
- *Is Java 8 still supported?* -> Yes, by vendors, but often only under extended or paid support. New code should not start there.
- *Why not use the latest non-LTS release?* -> It gets about six months of support, so you would face constant upgrades.
- *Does LTS mean new features stop?* -> No. An LTS is just a regular release that vendors choose to patch for longer.

**60-second answer**
The LTS versions are Java 8, 11, 17, 21 and 25. LTS means the vendor patches that version for years, while non-LTS releases are supported for only about six months. Companies prefer LTS so they are not forced to upgrade constantly. For a new project in 2026, I would start on Java 21 or 25. Java 25, released in September 2025, is the newest LTS and gives the longest support. Before deciding, I would check that my framework, build tools and base images support it.

### Q20 [fresher] What are `var`, text blocks and `String` helper methods?
tags: java11, java10, java15, var, text-blocks, string-api, basics

**Start here: the concepts**
- **Type inference:** the compiler works out a type from the code instead of you writing it. `var` asks it to do this for local variables.
- **Static typing:** every variable has one fixed type, checked at compile time. `var` keeps this. The compiler writes the type in for you, and it can never change later. It is not like JavaScript.
- **Local variable:** a variable declared inside a method or block. `var` works only there. It is not allowed for fields, method parameters or return types. It also needs an initializer on the same line, because the compiler infers the type from the right-hand side.
- **Text block:** a string literal that starts and ends with `"""` and can span many lines. It exists so SQL, JSON and HTML can be pasted in without `\n`, `+` and `\"` everywhere. It is still an ordinary `String`.
- **Incidental indentation:** the spaces you add only to line the text up with your code. A text block strips them, so only the relative indentation stays.
- **Whitespace:** characters such as space, tab and newline that print as "nothing".
- **Helper methods:** small methods on `String` for common jobs.
  - `isBlank()`: true if the string is empty or only whitespace.
  - `strip()`: removes leading and trailing whitespace, using the Unicode definition. `stripLeading()` and `stripTrailing()` do one side.
  - `lines()`: splits the text into a `Stream<String>`, one element per line.
  - `repeat(n)`: the string repeated n times.
  - `formatted(args)`: the same as `String.format(this, args)`, but called on the string itself.

**The live scenario**
A sign-up service handles about 40,000 registrations a day. Support noticed roughly 120 accounts with names that looked empty. The validation was `name.trim().isEmpty()`. Users on East-Asian keyboards had typed a full-width space (U+3000). `trim()` only removes characters up to U+0020, so it let that space through. Switching to `name.isBlank()` fixed it. In the same release a developer rewrote a 15-line SQL query as a text block. This removed a bug class where `"FROM orders" + "WHERE ..."` glued words together because a trailing space was missing.

**What the interviewer is really checking**
Whether you know which Java version added each feature. Also whether you understand that `var` is still static typing, and whether you can name practical differences such as `strip()` vs `trim()`.

**How I answer it**
1. **`var` (Java 10):** I use it for local variables when the type is obvious from the right side, e.g. `var list = new ArrayList<String>();`. The reason is less repetition. The type is fixed at compile time, so `list` can never become an `int` later.
2. **I avoid `var` when the type is unclear.** For example, `var result = service.process();` hides the type from the reader. Readability is the whole point, so I only use it where it helps.
3. **Text blocks (Java 15):** I use `"""` for SQL, JSON and HTML. After the opening `"""` the content starts on the next line. Indentation common to all lines is removed. Trailing spaces on each line are stripped. Newlines are normalised to `\n`. A `\` at the end of a line joins it with the next one. They were preview features in Java 13 and 14.
4. **String helpers (Java 11):** `isBlank`, `strip`, `stripLeading`, `stripTrailing`, `lines` and `repeat` arrived together in Java 11. I prefer `strip()` over `trim()` because it understands Unicode whitespace.
5. **`formatted()` came later, in Java 15:** it arrived together with text blocks. This is the one detail the short version blurs. It lets me write `"""Hello %s""".formatted(name)`.

**Trade-offs and what can go wrong**
- `var` with the diamond: `var list = new ArrayList<>();` infers `ArrayList<Object>`, not what you meant. Also, `var x = 1;` is an `int`, so intent can drift.
- `var` is not a keyword. It is a reserved type name, so you can still name a variable `var`, but you should not.
- Text blocks keep the whitespace you type. Mixing tabs and spaces makes the indentation stripping hard to predict. SQL in text blocks is still plain text, so never concatenate user input into it. Use `PreparedStatement`.
- `isBlank()` follows Java's `Character.isWhitespace`, which does not count non-breaking spaces. Test with your real input.
- Using these features on a build targeting an older Java fails to compile. Check the compiler `release` setting.

**How I'd monitor it**
- Unit tests with awkward input: empty string, tabs, full-width spaces.
- A Splunk search counting validation rejections per day, and a search for accounts with empty-looking names, to confirm the fix.
- Log the final SQL once in a test environment to check the text block output.
- CI fails if the project's Java version is lower than the language features in use.

**Follow-ups to expect**
- *Is `var` dynamic typing?* -> No. The compiler fixes the type at compile time, and the bytecode is the same as if you had written the type.
- *Difference between `trim()` and `strip()`?* -> `trim()` removes characters up to U+0020 only. `strip()` removes Unicode whitespace, so it is the safer choice.
- *Can I use `var` for a field or method parameter?* -> No. It works only for local variables with an initializer, and for loop variables and lambda parameters.

**60-second answer**
`var` came in Java 10. It lets the compiler infer a local variable's type, but the type is still fixed at compile time, so it is not dynamic typing. I use it when the type is obvious and avoid it when it would hide meaning. Text blocks became standard in Java 15. They use `"""` for multi-line strings such as SQL or JSON and remove the shared indentation. The `String` helpers `isBlank`, `strip`, `lines` and `repeat` came in Java 11. `formatted()` came in Java 15. I prefer `strip()` over `trim()` because it handles Unicode whitespace, which once let blank-looking names into a sign-up system.

### Q21 [fresher] What are List.of, Set.of, Map.of?
tags: java9, immutable-collections, factory-methods, list-of, set-of, map-of, basics

**Start here: the concepts**
- **Collection**: an object that holds a group of other objects. `List` keeps order and allows repeats, `Set` holds no duplicates, and `Map` stores key-value pairs.
- **Immutable**: it cannot change after creation. You cannot add, remove or replace elements. This makes it safe to share, because nobody can alter it behind your back.
- **Factory method**: a static method that builds an object for you (`List.of(...)`) instead of you writing `new`. It is short, and the JDK can choose an efficient implementation internally.
- **`UnsupportedOperationException`**: the runtime error you get when you call a change method (`add`, `remove`, `put`, `set`) on an immutable collection.
- **Null**: "no object". These collections reject it, so a null element, key or value throws `NullPointerException`.

**The live scenario**
A pricing service exposes a shared list of 12 supported currencies through a getter. It handles about 5,000 requests a minute. One developer called `getCurrencies().add("XYZ")` for a quick test feature. The list was a plain `ArrayList`, so the change leaked into every request and wrong prices appeared for hours. If the list had been created with `List.of(...)`, that call would have thrown `UnsupportedOperationException` in the developer's first test run, and the bug would never have reached production.

**What the interviewer is really checking**
Whether you know these are immutable, what they reject (nulls, duplicates), and where they differ from `Arrays.asList` and `Collections.unmodifiableList`. A fresher who also mentions *why* immutability is useful stands out.

**How I answer it**
1. **Say what they are.** `List.of`, `Set.of` and `Map.of` are factory methods added in **Java 9**. They create small, fixed collections in one line: `List.of("a","b")`. This removes the old `new ArrayList` plus several `add` calls.
2. **Say they are immutable.** Any change throws `UnsupportedOperationException`. That is deliberate: a shared constant list stays the same for everyone.
3. **No nulls.** A null element, key or value throws `NullPointerException`. Even `list.contains(null)` throws on these lists. The JDK designers chose to expose null mistakes early.
4. **No duplicates in `Set.of` or `Map.of`.** A repeated element or key throws `IllegalArgumentException`. This catches copy-paste mistakes at startup.
5. **Mention `copyOf`.** `List.copyOf`, `Set.copyOf` and `Map.copyOf` make an immutable copy of an existing collection. These arrived in **Java 10**, not 9.
6. **Mention limits.** `Map.of` takes at most 10 key-value pairs. For more, use `Map.ofEntries(Map.entry(k, v), ...)`.

```java
List<String> codes = List.of("USD", "EUR");
codes.add("INR"); // UnsupportedOperationException
```

**Trade-offs and what can go wrong**
- Immutability is **shallow**. You cannot add or remove elements, but if an element is a mutable object, its fields can still change.
- The iteration order of `Set.of` and `Map.of` is unspecified and can differ between JVM runs. Never depend on it. Use `LinkedHashSet` or `TreeMap` if order matters.
- Passing a null (for example, a value read from a database) throws `NullPointerException`, so `List.of(a, b)` is risky with unchecked data.
- If you need to build a list gradually, use `ArrayList` and then `List.copyOf` it at the end.

**How I'd monitor it**
- Search Splunk logs for `UnsupportedOperationException` and for `NullPointerException` with stack frames in `ImmutableCollections`, to find code that tries to modify these lists or passes nulls.
- Watch for startup failures with `IllegalArgumentException: duplicate element/key`.
- Write unit tests that try to modify shared constants and expect the exception.
- Static analysis tools such as SonarQube can flag mutable shared collections.

**Follow-ups to expect**
- *How is `List.of` different from `Arrays.asList`?* -> `Arrays.asList` is fixed-size, but `set` works and writes through to the backing array. `List.of` is fully immutable and rejects nulls.
- *How is `List.copyOf` different from `Collections.unmodifiableList`?* -> `unmodifiableList` is a read-only **view**, so changes to the original list show through. `copyOf` takes an independent snapshot.
- *Can I rely on the order of `Set.of`?* -> No. The order is unspecified and may change between runs.

**60-second answer**
`List.of`, `Set.of` and `Map.of` are Java 9 factory methods that create small immutable collections in one line. Immutable means that add, remove or put throws `UnsupportedOperationException`. They also reject nulls with `NullPointerException`, and `Set.of` and `Map.of` reject duplicates with `IllegalArgumentException`. `copyOf` makes an immutable copy of an existing collection, and it arrived in Java 10. I use them for constants and shared data so nobody can change them by accident. I remember that the immutability is shallow, that `Set.of` and `Map.of` have no guaranteed order, and that `Map.of` supports only 10 pairs, so I use `Map.ofEntries` beyond that.

### Q22 [mid] What is a record? What can't it do?
tags: java16, records, immutability, equals-hashcode, dto, compact-constructor, basics

**Start here: the concepts**
- **Record**: a special kind of class, final in Java 16 (preview in 14 and 15), for holding data. You list the fields once, in the header, and the compiler writes the boilerplate. It exists because plain data classes needed dozens of lines of constructor, getters, `equals`, `hashCode` and `toString`, and people got them wrong.
- **Component**: one item in the record header, such as `amount` in `Money(BigDecimal amount, String ccy)`. Each one becomes a private final field and an accessor method. The accessor is `amount()`, not `getAmount()`.
- **Canonical constructor**: the constructor that takes every component. The compiler generates it unless you write it.
- **Compact constructor**: a constructor without a parameter list, where you validate or normalise values. The fields are assigned automatically at the end.
- **Shallow immutability**: the fields can't be reassigned, but the objects they point to can still change. A `List` component can still be modified.
- **`equals`/`hashCode`**: the generated versions compare all components, so two records with equal values are equal.

**The live scenario**
A payments service used `Money` as a map key to group about 50,000 transactions per minute by amount and currency. Roughly 3% of lookups missed. The cause was that `BigDecimal("10.0")` and `BigDecimal("10.00")` are not `equals`, because they have different scales. The old hand-written class also had `equals` covering `amount` but not `ccy`, after someone added a field and forgot to update it. Switching to a record fixed the forgotten-field problem, since the compiler regenerates `equals` from the header. A compact constructor that called `setScale(2)` fixed the scale problem.

**What the interviewer is really checking**
Whether you know what the compiler generates, and the limits: no inheritance, only shallow immutability, and no JPA entities. A good candidate also knows that "immutable" does not mean "safe".

**How I answer it**
1. **Define it.** A record is a compact, immutable data carrier. `record Money(BigDecimal amount, String ccy) {}` generates the constructor, accessors, `equals`, `hashCode` and `toString`. This removes boilerplate and makes errors like a forgotten field impossible.
2. **State what it can't do.** It is implicitly final and already extends `java.lang.Record`, so it cannot extend a class. It can implement interfaces. It cannot be abstract. It cannot declare extra instance fields beyond the components, though it can have static fields, methods and nested types. Its fields cannot be reassigned.
3. **Explain shallow immutability.** A `List` component can still be mutated by whoever holds the original list. Make a defensive copy in the compact constructor.
4. **Add validation in the compact constructor.** It runs on every construction, so no invalid instance can exist:
```java
record Money(BigDecimal amount, String ccy) {
  Money { Objects.requireNonNull(ccy); amount = amount.setScale(2); }
}
```
5. **Say where it fits.** Records suit DTOs, Kafka events, API responses and map keys. The key use works only if the components have sensible `equals`, which is the `BigDecimal` trap above.
6. **Say where it doesn't fit.** Classic JPA entities need a no-arg constructor, non-final classes and mutable fields for proxies and dirty tracking, so a record can't be one. Records still work well as query projections. Recent Hibernate versions (6.2+) also allow them as embeddables.

**Trade-offs and what can go wrong**
- Shallow immutability is the most common mistake. A `List` or `Date` component can be changed from outside.
- Array components compare by reference in `equals`, so two records holding equal arrays are not equal.
- Generated `toString` prints every component, which can leak sensitive data such as card numbers into logs. Override it.
- Adding or reordering components changes the constructor signature and can break callers and serialisation. Treat a public record as an API.

**How I'd monitor it**
- Unit-test `equals`/`hashCode` with edge values, such as `10.0` against `10.00`.
- Watch cache hit rate and map-lookup miss counters, which would have exposed the 3% misses.
- Search Splunk for exceptions thrown from compact constructors (for example `IllegalArgumentException` with the record name) to find bad upstream data.
- Check that logs do not print sensitive record contents.

**Follow-ups to expect**
- *Can a record implement an interface?* -> Yes. It just can't extend a class.
- *Can a record have its own methods and static members?* -> Yes. It can have methods, static fields and static factory methods, but no extra instance fields.
- *Is a record deeply immutable?* -> No. Only the references are final, so copy mutable components in the constructor, for example with `List.copyOf`.

**60-second answer**
A record is a compact, immutable data carrier. From a one-line header the compiler generates the constructor, accessors, `equals`, `hashCode` and `toString`. It is implicitly final, so it can't extend a class, though it can implement interfaces, and it can't have extra instance fields. Its fields are only shallow-immutable, so I copy mutable components such as lists in a compact constructor, where I also validate input. Records are great for DTOs, events and map keys, but I watch for traps like `BigDecimal` scale in `equals`. They are not suitable as JPA entities, which need a no-arg constructor and mutability.

### Q23 [mid] Virtual threads vs reactive (WebFlux) - how do you choose?
tags: java21, virtual-threads, webflux, reactive, concurrency, basics

**Start here: the concepts**
- **Platform thread:** a normal Java thread, backed one-to-one by an operating system thread. It is expensive (roughly a megabyte of stack reserved), so a server can only run a few thousand.
- **Blocking I/O:** code that waits for a database or HTTP reply while holding its thread. The thread does nothing useful during the wait, but nobody else can use it.
- **Virtual thread (Java 21, JEP 444; preview in 19 and 20):** a very cheap thread managed by the JVM, not the OS. When it blocks on I/O, the JVM parks it and frees the underlying OS thread (the "carrier") for other work. You can run hundreds of thousands. You still write plain, sequential code.
- **Reactive programming (WebFlux, Project Reactor):** code written as a pipeline of callbacks (`Mono`/`Flux`). A few threads serve many requests because nothing ever blocks. It exists to avoid the cost of blocked threads.
- **Backpressure:** a slow consumer tells a fast producer "slow down", so memory doesn't fill with unprocessed data. Reactive streams build this in. Plain threads do not.
- **Pinning:** a virtual thread stuck to its carrier. In Java 21 this happens inside `synchronized` blocks and native calls. JEP 491 removes the `synchronized` case in Java 24.

**The live scenario**
An order service runs on Tomcat with 200 platform threads. Each request makes 3 downstream calls totalling about 300 ms of waiting. At 1,000 requests/s, about 300 requests are in flight at once (rate × latency), which is more than 200 threads. Requests queue and p99 latency jumps from 400 ms to 3 s, while CPU sits at 20%. The team could rewrite everything in WebFlux, which takes months, or upgrade to Java 21 and turn on virtual threads. They chose virtual threads. Latency recovered, but the 20-connection database pool became the next bottleneck.

**What the interviewer is really checking**
Whether you understand that both tools solve the same problem (threads wasted waiting) in different ways. They also want to see that you choose on workload and team cost, not fashion.

**How I answer it**
1. **Name the problem first.** Blocked platform threads limit throughput while the CPU is idle. Both options fix that.
2. **Default to virtual threads for request/response services.** The code stays sequential, stack traces are readable, debuggers and profilers work normally, and you keep most of the scalability. In Spring Boot 3.2+ it is one line:
   `spring.threads.virtual.enabled=true`
3. **Choose WebFlux when the workload is a stream.** Examples are server-sent events, WebSockets, or pipelines where backpressure and operators like `window` or `buffer` matter. Also choose it when you already have a working reactive codebase. Rewriting that gains little.
4. **Count the learning cost.** Reactive has a steep learning curve and hard debugging, because stack traces show framework internals instead of your logic. For a mid-size team that is a real cost.
5. **Check the limits.** Neither helps CPU-bound work. Virtual threads solve waiting, not computing.

**Trade-offs and what can go wrong**
- Virtual threads give no backpressure. Ten thousand cheap threads can overwhelm a database or partner API. Limit concurrency explicitly, for example with a `Semaphore` or bounded connection pools.
- Do not pool virtual threads. Create one per task.
- On Java 21, long blocking calls inside `synchronized` pin the carrier. Prefer `ReentrantLock` there.
- `ThreadLocal` values multiply with the thread count, so memory can grow.
- Mixing blocking calls into a reactive pipeline stalls its few event-loop threads, which is a common WebFlux mistake.

**How I'd monitor it**
- Compare p99 latency, throughput and CPU before and after the change.
- Watch connection-pool wait time, because the pool often becomes the new limit.
- Run with `-Djdk.tracePinnedThreads=full` (Java 21) to log pinning, and check the JFR event `jdk.VirtualThreadPinned`.
- In Splunk, alert on timeouts to downstream services and on rising request queue time.

**Follow-ups to expect**
- *Do virtual threads make code faster?* -> No. They raise throughput under many concurrent waits, but a single request is not faster.
- *Why not just increase the Tomcat thread pool?* -> Platform threads are costly in memory and context switching, so a pool of tens of thousands does not scale.
- *Can you mix both?* -> Yes. Use virtual threads for ordinary endpoints and WebFlux for the streaming ones, but keep them in separate services or clearly separated modules.

**60-second answer**
Both approaches solve the same problem: threads sitting idle while they wait for I/O. Virtual threads, final in Java 21, let me keep simple blocking code with normal stack traces and debugging, and still scale to many concurrent requests. Reactive with WebFlux gives built-in backpressure and streaming operators, but it has a steep learning curve and is hard to debug. So for typical request/response services I default to virtual threads. I keep WebFlux for streaming, backpressure-heavy pipelines or an existing reactive codebase. With virtual threads I still limit concurrency to downstream systems, because they have no backpressure, and I watch for pinning in `synchronized` blocks on Java 21.

### Q24 [senior] What are Structured Concurrency and Scoped Values?
tags: java25, structured-concurrency, scoped-values, virtual-threads, threadlocal, concurrency, basics

**Start here: the concepts**
- **Thread:** a path of execution inside a program. A **virtual thread** (final in Java 21) is a very cheap thread managed by the JVM, so one service can run hundreds of thousands at once.
- **ThreadLocal:** a variable where each thread has its own private copy. It is often used to carry per-request data such as the user ID or trace ID without passing it through every method. It is mutable, and it must be cleaned up manually.
- **Scoped Value:** a value bound for a limited block of code. Code inside the block, and the threads it starts in a structured scope, can read it. When the block ends, the binding disappears automatically. It cannot be changed from inside, only rebound for an inner block. Final in Java 25 (JEP 506).
- **Structured concurrency:** a rule that a task which splits into subtasks must not finish until all subtasks are done or cancelled. Subtasks live and die inside the parent's block, like a `try` block. It is still a **preview** feature in Java 25 (JEP 505), so it needs `--enable-preview` and its API has changed between previews.
- **Leaked thread:** a subtask that keeps running after the request that needed it has already failed or finished. It wastes CPU, connections and memory.

**The live scenario**
An order service handles about 3,000 requests per second. Each request calls inventory, pricing and fraud services in parallel on virtual threads. Fraud starts timing out at 2 seconds. The parent request fails, but the inventory and pricing calls keep running, and nobody reads their results. The wasted calls pile up and the downstream services slow down. The same service also keeps the user ID and trace ID in `ThreadLocal`s. Child threads have to copy them, and one missed `remove()` leaks data between requests. Both problems are about unclear lifetimes: who owns the subtasks, and how long the context lives.

**What the interviewer is really checking**
Whether you know these two features solve lifetime problems (of tasks and of context), and whether you are honest about their status: Scoped Values final, Structured Concurrency preview.

**How I answer it**
1. **Define the problem first.** Plain `ExecutorService` code lets subtasks outlive the method that started them. Failures and cancellation do not travel between them. Structured concurrency fixes this by tying subtasks to a block.
2. **Describe structured concurrency.** The parent opens a scope, forks subtasks, then joins. A policy (in Java 25 called a *Joiner*) decides the outcome. With an "all succeed or throw" policy, the first failure cancels the sibling subtasks and the parent sees the error. When the block exits, no subtask is still running. Thread dumps and stack traces then show the parent-child relationship.
3. **Describe scoped values.** Bind the value once at the entry point (for example a request filter), and everything beneath it reads it. It is immutable, so no code can silently change it. It is released automatically at the end of the block, so there is nothing to clean up. Subtasks forked in a structured scope inherit it cheaply, without copying.
4. **Say how they fit together.** Scoped values carry context *into* the scope, and structured concurrency controls the threads *inside* it.
5. **State the status and version.** Scoped Values: final in Java 25. Structured Concurrency: preview in Java 25. Do not call it production-final.

```java
static final ScopedValue<User> USER = ScopedValue.newInstance();
ScopedValue.where(USER, user).run(() -> handle()); // USER.get() works inside
```

**Trade-offs and what can go wrong**
- Scoped values are read-only. If code needs a mutable per-thread holder, it needs a different design.
- `ThreadLocal` is not removed and still works with virtual threads. Scoped values are a better fit for many uses, not a drop-in replacement. Libraries that use `ThreadLocal` (such as logging MDC) need migration time.
- Preview APIs can change between releases. Isolate them behind your own wrapper and avoid them in shared libraries.
- Cancellation relies on interruption. Subtasks that ignore interrupts, or that block in uninterruptible code, will not stop promptly.

**How I'd monitor it**
- Thread dumps (`jcmd <pid> Thread.dump_to_file`) to confirm no subtasks outlive their request.
- Metrics for in-flight downstream calls compared with in-flight requests. A gap means leaks.
- JFR virtual-thread events, such as pinning.
- Splunk searches on trace ID for requests where the parent failed but sibling calls kept logging afterwards.
- Alerts on downstream latency and on error rates after cancellation.

**Follow-ups to expect**
- *Why not just use `CompletableFuture`?* -> Its tasks are not tied to a parent. Failures do not cancel siblings automatically, and they run on the common pool unless you supply an executor.
- *Is `ThreadLocal` deprecated?* -> No. It still works, but it is mutable and needs manual cleanup. Scoped values suit read-only context better.
- *Can I use Structured Concurrency in production today?* -> Only by accepting preview status: `--enable-preview`, a possible API change, and no guarantee for library consumers.

**60-second answer**
Both features tie lifetimes to a block of code. Structured concurrency treats a parent and its subtasks as one unit. If one subtask fails, the others are cancelled, the parent sees the error, and nothing is left running afterwards. Scoped values give read-only per-request context, such as the user or trace ID, that exists only inside a block and is shared with the subtasks forked in that scope. This avoids the cleanup problems and copying cost of `ThreadLocal`. Scoped Values are final in Java 25. Structured Concurrency is still a preview feature in Java 25, so I would call it promising but not production-final.

### Q25 [mid] What improved in the JVM/GC since 8?
tags: jvm, garbage-collection, g1, zgc, containers, java-21, basics

**Start here: the concepts**
- **Garbage collector (GC):** the JVM part that finds objects nobody uses any more and frees their memory, so developers don't call `free()` themselves.
- **Pause (stop-the-world):** a moment when the GC freezes all application threads to do part of its work. Users see it as a latency spike.
- **Throughput vs pause time:** throughput is the share of time spent on real work rather than GC. Pause time is how long the longest freeze lasts. Collectors trade one against the other.
- **G1 (Garbage-First):** splits the heap into many small regions and collects the most garbage-filled ones first, aiming for a pause target (default 200 ms). It is the default since Java 9. Java 8 defaulted to the Parallel collector, which is fast overall but can pause for seconds on large heaps.
- **ZGC and Shenandoah:** concurrent collectors that do most work while the app runs, so pauses stay very short (ZGC aims for under a millisecond) and don't grow with heap size. ZGC became production-ready in Java 15. Shenandoah ships in OpenJDK builds, but not in every vendor's JDK.
- **Generational ZGC (Java 21):** most objects die young, so it collects young objects often and old ones rarely. This cuts CPU and memory overhead. In 21 you enable it with `-XX:+UseZGC -XX:+ZGenerational`.
- **cgroup limits:** Linux containers (Docker, Kubernetes) cap CPU and memory through cgroups. An old JVM ignored the cap and sized itself from the whole machine.
- **Class Data Sharing (CDS/AppCDS):** stores pre-parsed class data in a file so the JVM starts faster. **Project Leyden** extends this idea to startup and warm-up.
- **Object header:** the bookkeeping bytes in front of every object. Compact object headers shrink them, so the heap holds more objects.

**The live scenario**
A team ran 20 pods of an order service on Java 8, Parallel GC, 4 GB container limit. Two things hurt. On an old 8u build, the JVM read the node's 64 GB RAM and sized its heap as a quarter of that, so pods were OOM-killed. After a manual `-Xmx` fix, full GCs on a 3 GB heap froze requests for about 1.5 s, which broke a 300 ms SLA. They moved to Java 17 with G1 and `-XX:MaxRAMPercentage=70`. The kills stopped and p99 pauses fell to roughly 100–200 ms. For a 30 GB cache service, they tried ZGC to get pauses of a few milliseconds.

**What the interviewer is really checking**
Whether you know *why* each change exists (long pauses, containers, startup cost), can name the Java version, and can pick a collector for a workload instead of reciting names.

**How I answer it**
1. **Start with the default.** G1 has been the default since Java 9. It collects by region against a pause target, which avoids Java 8's long full-GC freezes. Reason: most services want predictable latency without tuning.
2. **Name the low-pause collectors.** ZGC and Shenandoah keep pauses very short even on big heaps because they work concurrently. Reason: for latency-critical or large-heap services, G1 pauses can still be too long.
3. **Mention Java 21's generational ZGC.** It collects young objects separately, which improves throughput and memory use. Reason: the first ZGC spent effort re-scanning the whole heap.
4. **Cover containers.** Modern JVMs honour cgroup limits. Java 10 added this and it was backported to 8u191. Size the heap by percentage:
   ```
   -XX:MaxRAMPercentage=70
   ```
   Reason: a percentage adapts when the pod limit changes, and the rest of the memory is left for metaspace, thread stacks and native memory.
5. **Finish with footprint and startup.** AppCDS (Java 10+) speeds startup. Project Leyden work, such as the ahead-of-time cache in Java 24, goes further. Compact object headers arrived as experimental in Java 24, and I'd check the exact status before relying on them. Reason: they matter for serverless and dense Kubernetes deployments.

**Trade-offs and what can go wrong**
- Low-pause collectors cost extra CPU and memory. On a small heap or one-CPU container, G1 or even Serial may be better.
- Setting the heap to 100% of the container limit leaves no room for non-heap memory, so the pod is OOM-killed.
- Don't carry over old Java 8 tuning flags. CMS was removed in Java 14, and many flags are obsolete.
- Switching collector without load testing is a gamble. Measure first.

**How I'd monitor it**
- Enable GC logs: `-Xlog:gc*:file=gc.log`. Ship them to Splunk and search for long pauses and "Pause Full".
- Watch Micrometer's `jvm.gc.pause`, heap used after GC, and allocation rate.
- Compare the container's working-set memory with its limit, and alert on OOMKilled restarts.
- Use JFR or `jcmd` to confirm the active collector and flags.

**Follow-ups to expect**
- *Which collector for a latency-sensitive 32 GB service?* -> ZGC (generational on 21+), because its pauses stay short as the heap grows. I'd confirm with a load test.
- *Why did Java 8 pods get OOM-killed?* -> Early 8 builds ignored cgroup limits and sized the heap from host memory. 8u191+ and Java 10+ respect them.
- *What replaced PermGen?* -> Metaspace, in Java 8, in native memory. It is not part of the heap, so cap it if classes leak.

**60-second answer**
Since Java 8, G1 became the default in Java 9, so most services get predictable pauses without tuning. For very low latency or large heaps, ZGC and Shenandoah keep pauses very short because they work concurrently. Java 21 added generational ZGC, which cuts overhead by treating young objects separately. The JVM is now container-aware, honouring cgroup limits, so I set `-XX:MaxRAMPercentage` rather than guessing `-Xmx`. Startup and footprint are improving too, with AppCDS, Project Leyden work and compact object headers. I always check GC logs and pause metrics before and after changing collectors.

### Q26 [mid] What is the HTTP Client and what replaced `HttpURLConnection`?
tags: java11, httpclient, httpurlconnection, http2, completablefuture, spring-restclient, basics

**Start here: the concepts**
- **HTTP client:** code that sends an HTTP request (GET, POST...) to another service and reads the response. Almost every microservice needs one to call other services.
- **`HttpURLConnection`:** the original JDK class for this, from the late 1990s. It is clunky: one object per request, awkward streams, hard to set timeouts correctly, no async, and no HTTP/2. It still exists, but it is the legacy option.
- **`java.net.http.HttpClient`:** the modern JDK replacement. It was an incubator (preview) API in Java 9 and 10 and became standard in **Java 11**. It uses a builder, immutable request and response objects, and a clean API.
- **HTTP/2:** a newer version of the protocol that sends many requests over one connection at the same time (multiplexing). That means fewer connections and less waiting. `HttpClient` supports it and falls back to HTTP/1.1 if the server does not.
- **`sendAsync` and `CompletableFuture`:** `send` blocks the calling thread until the response arrives. `sendAsync` returns immediately with a `CompletableFuture`, which is a placeholder for a result that arrives later. You attach steps to it, such as `thenApply`.
- **WebSocket:** a long-lived two-way channel between client and server, used for live updates. `HttpClient` can open one.
- **`RestClient` and declarative HTTP interfaces (Spring):** Spring's own wrappers for calling REST APIs. `RestClient` came in Spring Framework 6.1 (Boot 3.2). Declarative interfaces (`@HttpExchange`, Spring 6.0) let you write a Java interface and have Spring generate the calling code.

**The live scenario**
A payments service called a fraud-check API about 300 times per second. It used `HttpURLConnection` with hand-written code. During a slow period on the fraud API, threads hung for minutes because no read timeout had been set. The thread pool filled up and the checkout API went from 80 ms to timeouts. The team moved to one shared `HttpClient` with explicit connect and request timeouts, and made the independent calls with `sendAsync`. The result was fewer stuck threads and clear failures instead of hangs. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you know the JDK's modern client and its main features (Java 11, HTTP/2, async). Whether you know when to use plain `HttpClient` and when to use Spring's `RestClient`. Whether you know the practical rules, such as timeouts and reusing the client.

**How I answer it**
1. **Name the replacement and its version.** `java.net.http.HttpClient`, standard since Java 11. `HttpURLConnection` is not removed, but it is legacy. This shows you know it is a replacement, not a deletion.
2. **List what it adds.** HTTP/2, async calls through `CompletableFuture`, WebSocket, and a readable builder API.
3. **Show the shape in a few lines.** Build the client once and reuse it:
```java
HttpClient c = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();
HttpRequest r = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(3)).build();
c.sendAsync(r, BodyHandlers.ofString()).thenApply(HttpResponse::body);
```
   The client is immutable and thread-safe, and it manages its own connections, so one shared instance is cheaper than creating one per call.
4. **Say which to pick.** In a plain Java service, use `HttpClient`. In a Spring app, use `RestClient` (6.1+) or declarative HTTP interfaces, because they fit Spring's JSON conversion, error handling and testing.

**Trade-offs and what can go wrong**
- No timeout is set by default, so a slow server can hang your calls. Always set connect and request timeouts.
- Creating a new client for every request wastes resources. Share one.
- Async is not free. Long `thenApply` work runs on the client's executor threads, so keep those steps short or pass your own executor.
- `HttpClient` has no built-in retry, circuit breaker or JSON mapping. You add those yourself or through a library.
- In Spring, `RestTemplate` is older and in maintenance mode. `WebClient` is the reactive option, and `RestClient` is the modern blocking choice.

**How I'd monitor it**
- Client-side latency and error rate per downstream service (for example Micrometer timers).
- Timeout counts, and thread pool usage on the calling service.
- In Splunk, search for `HttpTimeoutException` or `ConnectException` grouped by target host.
- Alert when p99 latency or timeout rate for one downstream rises.

**Follow-ups to expect**
- *Is `HttpClient` blocking or non-blocking?* -> Both. `send` blocks the calling thread, and `sendAsync` returns a `CompletableFuture`.
- *Why not make a new client per request?* -> It is immutable and thread-safe and holds its own connection management, so one shared instance is cheaper.
- *RestClient vs WebClient?* -> `RestClient` is a fluent blocking client. `WebClient` is for reactive, non-blocking flows.

**60-second answer**
`HttpURLConnection` is the old JDK way to call HTTP, and it is clunky and has no HTTP/2. The modern replacement is `java.net.http.HttpClient`, standard since Java 11. It supports HTTP/2, async calls with `sendAsync` that return a `CompletableFuture`, and WebSocket. I build one client, share it, and always set connect and request timeouts, because there are none by default. In a plain Java service I use `HttpClient`. In a Spring app I prefer `RestClient` from Spring 6.1, or declarative HTTP interfaces. I watch downstream latency, timeouts and thread usage to catch slow dependencies early.

### Q27 [mid] What does Stream API add after Java 8?
tags: java, streams, java-9, java-16, collectors, gatherers, basics

**Start here: the concepts**
- **Stream**: a pipeline that processes a sequence of elements step by step (filter, map, collect) without writing loops by hand. Java 8 introduced it.
- **Intermediate vs terminal operation**: intermediate steps (`filter`, `map`) describe the work and run lazily. A terminal step (`collect`, `count`) starts the run.
- **Short-circuiting**: stopping early once the answer is known, instead of reading every element.
- **Collector**: a recipe that tells `collect` how to gather elements, for example into a list or a map.
- **Unmodifiable list**: a list that throws `UnsupportedOperationException` on `add` or `remove`.
- **Stateful operation**: a step that must remember earlier elements, such as a sliding window of the last 3 items. Java 8 had no clean way to build your own.
- **Why these additions exist**: after Java 8, developers kept hitting the same gaps (stop at a condition, avoid double passes, expand one element into many, custom steps). Each release filled one.

**The live scenario**
An audit service held 50 million event records sorted by timestamp. A report needed "all events before 09:00". The code used `filter(e -> e.time().isBefore(cutoff))`, which scanned all 50 million records and took about 40 seconds. Because the data was sorted, the team switched to `takeWhile`, which stops at the first record at or after the cutoff, and the report dropped to under a second. The same report also ran two passes to compute total and count, so they merged them with `teeing`.

**What the interviewer is really checking**
Whether you know Java did not stop at 8 and can name the additions with their versions and one practical use each. They also want to see that you know the pitfalls, such as `takeWhile` on unsorted data.

**How I answer it**
1. **Java 9: `takeWhile` and `dropWhile`.** `takeWhile` keeps elements until the condition first fails, then stops. `dropWhile` skips elements until the condition first fails, then keeps the rest. Use them on ordered, sorted data. Unlike `filter`, they stop at the first failure and do not look further.
2. **Java 12: `Collectors.teeing`.** It sends each element to two collectors and merges their results, so you get two answers in one pass:
   ```java
   stream.collect(Collectors.teeing(
       Collectors.counting(), Collectors.summingInt(Order::qty),
       (count, total) -> new Stats(count, total)));
   ```
   A stream can only be consumed once, so this avoids loading the data into a list just to traverse it twice.
3. **Java 16: `Stream.toList()`.** It replaces `collect(Collectors.toList())` with shorter code. The result is unmodifiable, so mutating it throws an exception. It allows null elements, unlike `Collectors.toUnmodifiableList()`.
4. **Java 16: `mapMulti`.** For each input element you push zero, one or many outputs to a consumer. It is an alternative to `flatMap` that avoids creating a small temporary stream per element. It helps when most elements produce few or no results.
5. **Java 24 (final): Stream Gatherers.** A gatherer is a custom intermediate operation, used with `.gather(...)`. Built-ins include `windowFixed` and `windowSliding` (batches and sliding windows). Before this, such steps needed awkward hacks or a manual loop. It was preview in Java 22 and 23, so say "Java 24 final" and not "Java 21".

**Trade-offs and what can go wrong**
- `takeWhile` on unsorted data silently returns a partial result. It stops at the first non-match, which is not the same as `filter`.
- On unordered or parallel streams, `takeWhile` and `dropWhile` behave nondeterministically.
- `toList()` returning an unmodifiable list breaks code that later calls `add`. Use `Collectors.toList()` if you need a mutable list, although the returned type is not guaranteed.
- `mapMulti` is harder to read, so use `flatMap` unless you have a reason not to.
- Gatherers need Java 24, so check the production runtime first.

**How I'd monitor it**
- Compare latency and elements processed before and after the change, in a benchmark and in production timers.
- Add a test on a sorted dataset that compares the `takeWhile` result with the `filter` result, to catch ordering assumptions.
- Search the logs for `UnsupportedOperationException` after moving to `toList()`.

**Follow-ups to expect**
- *How is `takeWhile` different from `filter`?* -> `filter` tests every element. `takeWhile` stops at the first failure, so it is only correct for ordered data.
- *Why use `teeing`?* -> It computes two results in one pass over a stream that can be consumed only once.
- *Is `toList()` the same as `Collectors.toList()`?* -> No. `toList()` is unmodifiable (Java 16), while `Collectors.toList()` returns a list with no guarantee about mutability, in practice an `ArrayList`.

**60-second answer**
After Java 8, the Stream API grew in several steps. Java 9 added `takeWhile` and `dropWhile`, which stop or start at the first failing element, so they suit sorted data. Java 12 added `Collectors.teeing`, which gives two results from one pass. Java 16 added `toList()`, a shorter way to collect into an unmodifiable list, and `mapMulti`, which emits zero or more outputs per element without temporary streams. Java 24 finalised Stream Gatherers, which let you write custom intermediate operations such as sliding windows. The main pitfall is using `takeWhile` on unsorted data, which gives wrong results without any error.

### Q28 [mid] What is the module system (JPMS) and do you use it?
tags: jpms, java9, modules, jlink, encapsulation, classpath, basics

**Start here: the concepts**
- **JPMS (Java Platform Module System):** a Java 9 feature (Project Jigsaw) that lets you group packages into a named **module** and declare which ones other modules may use. It exists because, on the plain classpath, every public class in every JAR is visible to everything else, including the JDK's own internals.
- **Classpath:** the traditional flat list of JARs. Anything public is reachable by anything. Most Spring Boot apps still run this way.
- **`module-info.java`:** a file at the root of a module. `requires` lists the modules you depend on. `exports` lists the packages others may call. `opens` lists the packages others may access through reflection.
- **Strong encapsulation:** the module boundary is enforced by the JVM. A package that is not exported cannot be used, even if the class is `public`.
- **Reflection:** code that inspects or changes classes at runtime, for example to set private fields. Spring, Hibernate and Jackson rely on it.
- **Unnamed module:** where all classpath code lands. It can read everything but is blocked from non-opened JDK internals.
- **`jlink`:** a tool that builds a custom, smaller Java runtime containing only the modules your app needs.
- **`InaccessibleObjectException`:** thrown when reflection tries to open something its module has not opened. The message looks like "module java.base does not open java.lang to unnamed module".

**The live scenario**
A team upgrades 40 services from Java 11 to Java 17. Under Java 11 an old serialization library was reflecting into `java.lang` and only printing a warning. Java 17 enforces the module boundary, so the library now throws `InaccessibleObjectException`. During the canary rollout the pods crash-loop within about two minutes. The team does not need to rewrite anything for JPMS. They need to understand the error. They add `--add-opens java.base/java.lang=ALL-UNNAMED` as a short-term fix, then upgrade the library.

**What the interviewer is really checking**
Whether you know what JPMS is and can say honestly where it matters in real work. They also want to see that you can diagnose the module errors that appear when you upgrade the JDK, without claiming to use it everywhere.

**How I answer it**
1. **Define it simply.** JPMS lets a module hide its internals and expose only chosen packages. The reason is that the classpath cannot enforce boundaries, so internal classes become accidental public APIs.
2. **Show the shape.**
   ```java
   module orders.api { requires java.sql; exports com.shop.orders.api; }
   ```
3. **Say whether you use it.** In Spring Boot services I stay on the classpath. Frameworks depend heavily on reflection and many third-party JARs are not modular, so the migration cost is high and the benefit is small for an application.
4. **Say where it does matter.** It helps library and SDK authors who want a clean public API. It also enables `jlink` for small runtimes, for example in containers.
5. **Explain the upgrade issue.** From Java 9 to 15 the JDK defaulted to permissive illegal access, with warnings. Java 16 denied it by default and Java 17 removed the switch, so reflection into JDK internals fails. The proper fix is to upgrade the library. `--add-opens` is a temporary workaround.

**Trade-offs and what can go wrong**
- Modularizing an app means non-modular dependencies become "automatic modules" with unstable names, and split packages across JARs are not allowed.
- `--add-opens` flags hide the problem but must be tracked, or they stay forever.
- `exports` does not allow reflection on private members. You need `opens` for that, and people often confuse the two.
- A `jlink` image has no automatic security patching. You must rebuild it when the JDK is patched.

**How I'd monitor it**
- Before upgrading, run `jdeps --jdk-internals` on the JARs to find use of JDK internals.
- In staging, search logs (for example in Splunk) for `InaccessibleObjectException` and `does not open`.
- Alert on crash loops and restart counts during canary rollouts.
- Use `java --list-modules` to check what a runtime contains, and compare `jlink` image size against the full JDK.

**Follow-ups to expect**
- *What is the difference between `exports` and `opens`?* -> `exports` allows compile-time and runtime use of public types. `opens` allows deep reflection, including private members.
- *Is `--add-opens` a good fix?* -> It is a stopgap. Prefer upgrading the library, and document every flag you keep.
- *What is an automatic module?* -> A plain JAR placed on the module path. Java derives a module name from the file name, which is fragile and can break when the file name changes.

**60-second answer**
JPMS, from Java 9, lets you package code as modules with a `module-info.java`. You declare what you require and which packages you export, so internal classes stay hidden. That is stronger than the classpath, where every public class is visible. In my Spring Boot work I stay on the classpath because frameworks use a lot of reflection and many libraries are not modular. JPMS matters most to library authors and to `jlink`, which builds small runtimes. The practical impact for me is on JDK upgrades. From Java 17, reflection into JDK internals fails with `InaccessibleObjectException`. I fix that by upgrading the library, and use `--add-opens` only as a temporary workaround.

### Q29 [mid] What is GraalVM Native Image and its trade-offs?
tags: graalvm, native-image, aot-compilation, spring-boot, startup-time, serverless, basics

**Start here: the concepts**
- **JVM and bytecode:** Normally `javac` turns Java into bytecode. The JVM loads that bytecode at startup and runs it. This is flexible but costs time and memory before the app does useful work.
- **JIT (Just-In-Time) compiler:** While the app runs, the JVM watches which methods are "hot" and compiles them to fast machine code. It gets very fast after a warm-up period, but warm-up takes seconds to minutes.
- **AOT (Ahead-Of-Time) compilation:** Compiling to machine code at build time instead of at runtime.
- **GraalVM Native Image:** A tool that AOT-compiles your app, the libraries it uses and a small runtime into one native executable. No JVM installation is needed to run it. It exists because many workloads (functions, CLIs, scale-to-zero services) care more about start time and memory than about peak speed.
- **Closed-world assumption:** At build time the tool analyses which code is reachable and keeps only that. Anything it cannot see, such as a class loaded by name at runtime, may be missing from the binary.
- **Reflection and proxies:** Reflection means finding and calling classes or methods by name at runtime. Proxies are classes generated on the fly (Spring, Hibernate and others use them). Both break the closed-world view, so you must declare them as **hints** (config files telling the build what to keep).
- **Spring AOT:** Spring Boot 3 / Spring Framework 6 can run a build step that works out the beans and proxies and generates these hints for you.
- **Scale-to-zero / serverless:** The platform stops your app when idle and starts it on demand. Startup time becomes user-visible latency (a "cold start").

**The live scenario**
A team ran a Spring Boot function on AWS Lambda behind an API. Traffic was bursty: idle at night, then 0 to 200 concurrent requests at 9 am. On the JVM, each cold start took about 6 seconds (illustrative) and the first users saw timeouts. They moved the function to a native image. Cold start dropped to well under a second and the memory setting could be lowered, which cut cost. The same team tried native on a pricing service that runs for weeks at high load. The warmed-up JVM was slightly faster there and the long builds slowed CI, so it stayed on the JVM.

**What the interviewer is really checking**
Whether you know native image is a trade, not an upgrade: you swap build time, flexibility and peak speed for startup and footprint. They also want to hear when you would and would not use it.

**How I answer it**
1. **Define it:** Native Image compiles the app ahead of time into a native executable. That removes JVM startup and warm-up, so it starts in tens of milliseconds and uses little memory.
2. **Name the fit:** Lambda, scale-to-zero services, CLIs and other short-lived processes, where startup and memory dominate cost and latency.
3. **List the costs:**
   - **Long builds:** Whole-program analysis takes minutes and a lot of RAM, so CI gets slower.
   - **No runtime class generation:** Bytecode that is created or loaded at runtime is not supported, because everything must be known at build time.
   - **Reflection and proxies need hints:** Spring AOT generates most of them. Libraries it does not cover need manual hints.
   - **Lower peak throughput:** There is no runtime JIT optimising from live data, so a long-running JVM is usually faster at steady state. Profile-guided optimisation in some GraalVM editions narrows the gap.
4. **Give the rule:** Use it where start time and footprint matter, not by default. Measure on your own workload first.
5. **Show the build step (Spring Boot 3 with Maven):**
```
mvn -Pnative native:compile
```

**Trade-offs and what can go wrong**
- The app works on the JVM but fails natively at runtime with missing class or method errors, because a hint was missing. Tests must run against the native binary, not only the JVM.
- Some libraries do not support native image yet.
- Debugging and profiling tools differ from the usual JVM ones.
- Build machines need more memory and time, and the binary is built per OS and CPU architecture.
- Choosing native because it is trendy, then losing throughput on a service that never scales to zero.

**How I'd monitor it**
- Cold start: Lambda's `Init Duration` in the REPORT log line, or time-to-ready for containers.
- Memory (RSS) and cost per request, JVM versus native.
- p99 latency and throughput under steady load, to see the peak-performance gap.
- Splunk search after each deploy for `ClassNotFoundException`, `NoSuchMethodError` or "missing reflection registration" errors.
- CI build duration and build memory.

**Follow-ups to expect**
- *How do you fix a missing-reflection error?* -> Add a hint (a hints file or Spring's `RuntimeHints`), or run the app with the tracing agent to collect them, then re-test the native binary.
- *Why is peak throughput lower?* -> The JIT optimises using live profiling data, and a native binary has no JIT. Its default GC options are also simpler.
- *Alternatives for faster JVM startup?* -> Tune the JVM, use class data sharing, or use checkpoint/restore approaches. These keep the JVM's flexibility but give smaller gains.

**60-second answer**
GraalVM Native Image compiles your Java app ahead of time into a native executable, so there is no JVM warm-up. It starts in tens of milliseconds and uses much less memory. That suits Lambda, scale-to-zero services and CLIs. The costs are long builds and no runtime class generation. Reflection and proxies must be declared as hints, and Spring AOT generates most of those. Peak throughput is usually lower than a warmed-up JIT. So I use it for short-lived, startup-sensitive workloads, I test the native binary itself, and I keep long-running high-throughput services on the JVM.

### Q30 [mid] What are `Stream.toList()`, `Optional.orElseThrow()` and `switch` expressions worth in code reviews?
tags: java-16, java-17, streams, optional, switch-expressions, code-review, basics

**Start here: the concepts**
- **Code review**: teammates read a change before it merges. Small language features matter here because they make intent obvious to the reader and remove whole classes of mistakes.
- **`Stream.toList()` (Java 16)**: ends a stream pipeline and gives back a `List`. It replaces the longer `collect(Collectors.toList())`. The returned list is **unmodifiable**: `add` or `remove` throws `UnsupportedOperationException`. `Collectors.toList()` makes no promise about the list type, but in practice it returns a mutable `ArrayList`. `toList()` does allow `null` elements.
- **`Optional`**: a box that holds either a value or nothing, so "might be missing" is visible in the type.
- **`Optional.get()`**: returns the value, or throws `NoSuchElementException` if the box is empty. The name hides the risk, so people call it without checking.
- **`Optional.orElseThrow()` (no-arg, Java 10)**: does the same as `get()`, but the name says "this throws if empty". There is also a version that takes a supplier, so you can throw your own exception.
- **Switch expression (standard in Java 14)**: a `switch` that produces a value, for example `var x = switch (day) { case SAT, SUN -> "weekend"; default -> "weekday"; };`. The arrow form (`->`) does not fall through into the next case, and the compiler requires all cases to be covered. The old colon form (`case X:`) can still fall through.
- **Fall-through**: in the old `switch`, forgetting `break` made execution continue into the next case, which caused silent bugs.
- **Checkstyle, Sonar, OpenRewrite**: Checkstyle and Sonar are tools that flag code-style and bug patterns automatically. OpenRewrite can rewrite code automatically across many repositories.

**The live scenario**
A team owns 40 services, and reviewers keep leaving the same comments: "use `toList()`", "don't call `get()`", "this switch is missing a `break`". Last quarter, a pricing service had a `switch` on a status string where one case lacked `break`. About 1% of 200,000 daily orders got the wrong discount. Separately, a log line `NoSuchElementException: No value present` appeared with no context, and it took an hour to find which `get()` caused it. The team then migrated to `toList()` in bulk. One service later added an element to that list and failed with `UnsupportedOperationException` on roughly 2% of requests.

**What the interviewer is really checking**
Whether you know what each feature really does (including the unmodifiable-list catch), and whether you can turn review comments into automated team standards instead of repeating them by hand.

**How I answer it**
1. **Call them small readability wins, not big features.** They make code shorter and intent clearer, but they do not change architecture.
2. **`toList()`: use it when the list is only read.** It is shorter and signals "read-only". Before swapping it in, check that nobody modifies the result, because the list is unmodifiable. If someone needs a mutable list, use `new ArrayList<>(...)` or `Collectors.toCollection(ArrayList::new)` explicitly.
3. **`orElseThrow()` instead of `get()`.** The behaviour is identical, but the name tells the reader and the reviewer that an exception is possible. Better still, use the supplier version so the error says what was missing:
   ```java
   repo.find(id).orElseThrow(() -> new OrderNotFoundException(id));
   ```
4. **Switch expressions.** The arrow form removes fall-through, and the compiler rejects missing cases. For enums, adding a new constant then breaks the build where it is unhandled, instead of failing silently in production.
5. **Make it a team rule, not a reviewer habit.** Write it in the style guide, enforce what you can with Checkstyle and Sonar, and use OpenRewrite for bulk migration. Automation avoids repeating the same comment and avoids debates in every pull request.

**Trade-offs and what can go wrong**
- `toList()` is not a drop-in replacement if code mutates the list. Tests that only cover the happy path may miss this.
- Bulk rewrites can cause behaviour changes, so review the diff and run tests.
- Arrow switch is not a cure-all. The colon form with `yield` still falls through if you forget `yield` or `break`.
- Over-enforcing style can annoy the team, so start with warnings and enforce once the codebase is clean.
- These features need the right Java version (16+ for `toList()`, 14+ for switch expressions), so check what your build targets.

**How I'd monitor it**
- A Sonar quality gate and Checkstyle in CI that fail the build on banned patterns, plus a trend of `Optional.get()` count per repository.
- After a migration, search the logs (for example in Splunk) for `UnsupportedOperationException` and `NoSuchElementException`, and compare error rates before and after the release.
- Count recurring review comments. If the same one keeps appearing, automate it.

**Follow-ups to expect**
- *Is `Stream.toList()` the same as `Collectors.toUnmodifiableList()`?* -> No. `toList()` allows `null` elements, while `toUnmodifiableList()` throws a `NullPointerException` on them.
- *When would you still use `Collectors.toList()`?* -> When the caller needs a list it can modify, or when the code must run on Java versions before 16.
- *Does a switch expression need a `default`?* -> It must be exhaustive. For enums, covering every constant is enough. For other types, such as strings or ints, you need `default`.

**60-second answer**
These are small readability wins, and I would not oversell them. `Stream.toList()` is shorter than `collect(Collectors.toList())`, but the list is unmodifiable, so I check that nobody mutates it. `orElseThrow()` replaces `get()`: same behaviour, but the name says it throws, and I prefer the version that takes a clear exception. Switch expressions return a value and, in the arrow form, avoid fall-through and force every case to be handled. The real value comes from making this team policy: put it in the style guide, enforce it with Checkstyle and Sonar, and use OpenRewrite for bulk migration. Then reviewers can spend their time on design instead of repeating style comments.

### Q31 [senior] What is Project Valhalla / Leyden / Panama in one line each?
tags: java, project-valhalla, project-leyden, project-panama, jvm, jdk-roadmap, basics

**Start here: the concepts**
- **OpenJDK project:** a long-running effort to change the Java platform in one area. Features arrive in stages: incubator or preview first, then final in a numbered release.
- **Object header and identity:** every Java object carries a hidden header (typically 12-16 bytes on HotSpot) for its type, locking and GC state. It exists because every object has a unique identity, which is what `==` compares. An array of objects is really an array of pointers to objects scattered on the heap.
- **Value types (Valhalla):** the "value class" idea is a class that gives up identity, so the JVM can drop the header and store the data inline, like an `int[]` does. It exists because small data holders (points, money, ticks) waste memory and cause cache misses today.
- **Warmup:** a JVM starts by loading classes and interpreting bytecode, then the JIT compiler gradually optimises hot code. Until then, the app is slow.
- **AOT (ahead-of-time) cache (Leyden):** the JVM saves work from a training run (class loading, linking, later profiling data) and reuses it at the next start. It exists to cut startup time and time-to-peak. Unlike GraalVM native image, it stays a normal JVM with dynamic features.
- **JNI (Java Native Interface):** the old way to call C code or use memory outside the heap. It needs C glue code and is error-prone.
- **FFM API (Panama):** Foreign Function & Memory API. It calls native libraries and manages off-heap memory from pure Java, with bounds-checked memory segments and scoped lifetimes. It is safer than JNI or `Unsafe`.

**The live scenario**
A pricing service holds 20 million tiny `Tick(price, qty)` objects. Each costs a header plus a pointer, so memory is roughly double the real data, and scanning them misses the CPU cache (illustrative: 1.5 GB heap, long GC pauses). Separately, the pods take 45 seconds to reach full speed, so autoscaling reacts too late during a traffic spike. Finally, the team wraps a C risk library with fragile JNI code that crashed a pod with a segfault. Each pain maps to one project: Valhalla, Leyden and Panama.

**What the interviewer is really checking**
Whether you know what problem each project solves and where it stands today, not just the names. A senior candidate should also say what they would use now and what they would only watch.

**How I answer it**
1. **Valhalla: remove identity to remove overhead.** Value classes would be stored flat, with no header or pointer. Reason: less memory and better cache locality, with the safety of classes. Status: still in preview or early access, so I do not design around it yet.
2. **Leyden: shift work from runtime to earlier.** Cache class loading, linking and (later) profile data so startup and warmup shrink. Reason: faster scale-out and cheaper short-lived processes. Delivery is incremental, and the first pieces arrived in JDK 24 (AOT class loading and linking). I would test it on my own build before relying on it.
3. **Panama: replace JNI.** The FFM API calls native code and handles off-heap memory in Java. It was preview in 19-21 and final in Java 22, so it is usable now. Its Vector API is still incubating. Reason: less glue code and fewer crashes. It is safer than JNI but not risk-free, because some calls are "restricted" and need explicit enabling.
4. **Close with a position.** Use Panama where it is final, pilot Leyden on a non-critical service, and follow Valhalla. Reason: this shows judgment, not just awareness.

**Trade-offs and what can go wrong**
- Valhalla value classes will have limits: no identity, so no synchronisation on them, and usually no `null` by default. Old code that depends on identity may behave differently.
- Leyden caches depend on the exact JDK and application build. A stale cache is useless, and the training run must be representative.
- Panama still allows native crashes if you pass wrong memory layouts. Off-heap memory is not garbage-collected like heap memory, so leaks are possible.
- Do not adopt preview features in production. Do not confuse Leyden with GraalVM native image.

**How I'd monitor it**
- Measure before and after: time to ready, time to peak throughput, and request latency in the first minutes after deploy.
- Use JFR or GC logs for heap size and allocation rate, and for object counts (relevant to Valhalla).
- For Panama, track off-heap usage (native memory tracking, container RSS vs heap) and alert on RSS growth.
- Search the logs in Splunk for JVM crash markers (`hs_err`, exit code 134) to check native stability.

**Follow-ups to expect**
- *How does Leyden differ from GraalVM native image?* -> Leyden keeps a standard JVM with dynamic loading and JIT, and caches work. Native image compiles a closed world into a binary and restricts dynamic features.
- *Why is Panama better than JNI?* -> It needs no C glue, has bounds-checked memory and scoped lifetimes, and is easier to maintain, but is still unsafe if misused.
- *Would you use Valhalla today?* -> No. I would use records and compact data structures now and design types that can later become value classes.

**60-second answer**
These are three OpenJDK projects that fix long-standing Java costs. Valhalla introduces value classes that have no object identity, so the JVM can store them flat without headers and pointers, saving memory and improving cache use. Leyden improves startup and warmup by caching work like class loading and linking from earlier runs, and it keeps the normal JVM, unlike native image. Panama's Foreign Function & Memory API replaces JNI for calling native code and managing off-heap memory, and it is final since Java 22. Today I would use Panama, trial Leyden, and only follow Valhalla. Knowing that status is what shows I track the platform.

### Q32 [fresher] Process vs thread? How do you create a thread?
tags: java, threads, process, concurrency, executorservice, runnable, callable, basics

**Start here: the concepts**
- **Process:** a running program. The operating system gives it its own private memory, so one process cannot normally read another's data. This isolation exists so one crashing program does not corrupt others. Starting a process is relatively heavy.
- **Thread:** a path of execution inside a process. A thread lets one program do several things at once, such as serving many users.
- **Heap:** the memory area where Java objects live. All threads in a process share it, which makes sharing data easy.
- **Stack:** each thread's private memory for method calls and local variables. Because it is private, local variables are safe from other threads.
- **Race condition:** a bug where two threads change the same shared object at the same time and produce wrong results. It is the price of sharing the heap.
- **Runnable / Callable:** a task is a piece of work, separate from the thread that runs it. `Runnable` returns nothing. `Callable` returns a result and may throw a checked exception.
- **ExecutorService (thread pool):** a manager that keeps a fixed set of reusable threads and feeds them tasks. Creating a thread is costly, so reusing threads is cheaper.

**The live scenario**
A report service created `new Thread(...)` for every request. At about 500 requests per second, each request took about 4 seconds. That meant roughly 2,000 threads alive at once. Each thread reserves stack memory (often around 1 MB, depending on the platform and settings). The service slowed down as the CPU switched between thousands of threads. Eventually it failed with `OutOfMemoryError: unable to create native thread`. The team switched to a pool of 20 threads with a bounded queue. Memory became stable and excess load was handled in a controlled way.

**What the interviewer is really checking**
Whether you know what is shared and what is private between threads. Also whether you know that real code submits tasks to a pool instead of creating threads by hand.

**How I answer it**
1. **Define the difference.** A process has its own memory. Threads inside one process share the heap and each has its own stack. This explains why threads are cheap to start and share data easily, but can suffer race conditions.
2. **Name the ways to create a thread.** You can implement `Runnable` and pass it to `new Thread(r).start()`. You can also extend `Thread` and override `run()`.
3. **Call `start()`, not `run()`.** `start()` asks the JVM to create a new thread, which then calls `run()`. Calling `run()` directly just executes the method on your current thread.
4. **Prefer an executor.** A pool reuses threads and limits how many exist, so load cannot crash the JVM. `Callable` plus `Future` gives you a result back, which a raw `Thread` cannot do.
5. **Extend `Thread` only for special cases.** Java allows only one parent class, so extending `Thread` wastes it. It also mixes the task with the mechanism that runs it.

```java
ExecutorService pool = Executors.newFixedThreadPool(4);
Future<Integer> f = pool.submit(() -> 42); // Callable
pool.shutdown();                           // always stop the pool
```

**Trade-offs and what can go wrong**
- Forgetting `shutdown()` can keep the application from exiting.
- `newFixedThreadPool` uses an unbounded queue. Under heavy load the queue can grow until memory runs out. A `ThreadPoolExecutor` with a bounded queue is safer.
- Shared mutable objects need synchronization or thread-safe classes.
- Exceptions inside a pool task can be hidden inside the `Future` if you never call `get()`.
- In Java 21, virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`) are very cheap threads, useful for many blocking tasks. This is an advanced follow-up, not the basic answer.

**How I'd monitor it**
- Track live thread count (for example the `jvm.threads.live` metric from Micrometer, or `ThreadMXBean`).
- Track pool queue size and active threads.
- Take a thread dump with `jstack` when the service is slow.
- Give threads meaningful names through a thread factory, so they are identifiable in logs and dumps.
- Search Splunk for `unable to create native thread` and set an alert on it.

**Follow-ups to expect**
- *Runnable vs Callable?* -> `Runnable.run()` returns nothing and cannot throw checked exceptions. `Callable.call()` returns a value and can throw.
- *What is the difference between `start()` and `run()`?* -> `start()` creates a new thread. `run()` is an ordinary method call on the current thread.
- *Why not create a thread per request?* -> Each thread costs memory and CPU switching time, and unlimited threads can crash the JVM. A pool caps this cost.

**60-second answer**
A process is a running program with its own private memory. Threads live inside a process, share its heap, and each has its own stack. That makes threads cheap and good for sharing data, but shared data can cause race conditions. To create a thread, you can implement `Runnable` and call `start()`, or extend `Thread`. In real code I submit a `Runnable` or `Callable` to an `ExecutorService`, because a pool reuses threads and limits how many exist. `Callable` can return a result and throw exceptions. I extend `Thread` only for special cases, and I always shut the pool down when I am done.

### Q33 [fresher] What is the difference between `synchronized` and `volatile`?
tags: java, concurrency, synchronized, volatile, java-memory-model, atomic, basics

**Start here: the concepts**
- **Thread**: one path of execution inside a program. A web server runs many threads at once, and they can all touch the same variables.
- **Shared variable**: a variable that more than one thread can read and write, such as a counter or a flag.
- **Visibility**: whether a change made by one thread can be seen by another. Each CPU core may keep its own cached copy of a variable, so without a rule a thread can keep reading a stale value.
- **Ordering (reordering)**: the compiler and CPU may rearrange instructions for speed if one thread can't tell the difference. Another thread can, so Java needs rules to limit this.
- **Atomicity**: an operation that happens completely or not at all, with nothing able to slip in the middle. `count++` is not atomic. It is three steps: read, add 1, write back.
- **Race condition**: a bug where the result depends on how threads happen to interleave, for example two threads both read 5 and both write 6, so one update is lost.
- **Mutual exclusion (lock)**: only one thread at a time may run a protected block. In Java, `synchronized` uses a lock attached to an object. A thread must get that lock to enter, and others wait.

**The live scenario**
A payments service handles about 2,000 requests per second. A developer adds `private volatile int processed;` and runs `processed++` in every request thread, thinking volatile makes it thread-safe. After an hour the dashboard shows about 7.1 million, but the access logs show 7.2 million requests. Updates were silently lost. The same team also had a worker loop `while (running) {...}` with a plain boolean `running`. On shutdown, the worker kept going because it never saw the change to `false`. The first bug needs atomicity and the second needs only visibility. That is the whole difference between the two keywords.

**What the interviewer is really checking**
Whether you know that visibility and atomicity are separate problems, and that `volatile` solves only the first. They also want to see that you can pick the right tool for each case.

**How I answer it**
1. **Name the two problems.** Threads can see stale values (visibility), and compound operations can interleave (atomicity). I start here because every keyword is a fix for one or both.
2. **`synchronized` fixes both.** Only one thread at a time holds the lock, so the block runs as one unit. When a thread releases the lock, its changes become visible to the next thread that acquires the same lock. The reason is that both threads must use the same lock object, otherwise there is no protection.
3. **`volatile` fixes visibility and ordering for one variable.** A write goes straight to main memory and a read always sees the latest write. The compiler and CPU also may not reorder around it. It takes no lock, so threads never wait.
4. **`volatile` gives no atomicity.** `count++` is read, add, write, so two threads can still interleave. Single reads and writes of a volatile variable are fine, but compound actions are not.
5. **Pick by use case.** For a simple flag one thread writes and others read, such as `running`, use `volatile`. For several related fields that must change together, use `synchronized`. For a simple counter, use `AtomicInteger`, or `LongAdder` when many threads update it heavily.
```java
private final AtomicInteger processed = new AtomicInteger();
processed.incrementAndGet(); // atomic, no lock
```

**Trade-offs and what can go wrong**
- `synchronized` is safe but threads wait, so a lock held too long, or too many threads contending for it, hurts throughput. Two locks taken in opposite orders can cause a deadlock.
- `volatile` is cheap but easy to misuse. A volatile `List` does not make the list's contents thread-safe, only the reference to it.
- Common mistake: synchronizing on different objects in different places, or on something that changes. The code looks protected but isn't.
- `LongAdder` is faster under heavy contention, but reading its total is not an instant exact snapshot while updates continue.

**How I'd monitor it**
- Compare application counters with an independent source, such as load balancer or access-log counts. A steady gap points to lost updates.
- Take thread dumps (`jstack`) and look for many threads in `BLOCKED` state waiting on the same lock.
- Use Java Flight Recorder to see lock contention and time spent waiting.
- Search logs (for example in Splunk) for requests that time out at the same moment, which suggests lock waits.

**Follow-ups to expect**
- *Can `volatile` replace `synchronized`?* -> Only when one thread writes a single variable and others just read it, and no compound action is involved. Otherwise no.
- *What does a `synchronized` instance method lock on?* -> The current object (`this`). A static synchronized method locks on the `Class` object.
- *How does `AtomicInteger` avoid locks?* -> It uses compare-and-set, a CPU instruction that updates the value only if it still equals what the thread last read. If it fails, the thread retries.

**60-second answer**
Both deal with threads sharing data, but they solve different problems. `synchronized` gives mutual exclusion: only one thread runs the block at a time. It also gives visibility, so changes made before releasing the lock are seen by the next thread that takes it. `volatile` gives only visibility and ordering for a single variable: every read sees the latest write. It does not give atomicity, so `count++` on a volatile variable is still a race, because it is read, add, write. I use `volatile` for simple flags like a `running` boolean. I use `synchronized` when several steps must happen together. For counters I use `AtomicInteger`, or `LongAdder` under heavy contention.

### Q34 [fresher] What are the thread states and what does `wait/notify` do?
tags: threads, thread-states, wait-notify, synchronization, monitor, concurrency, basics

**Start here: the concepts**
- **Thread:** one independent path of execution inside a program. A server runs many threads at once, each handling a different request.
- **Thread state:** the label the JVM gives a thread to say what it is doing right now. You see these labels in thread dumps (a snapshot listing every thread and its state).
- **Monitor (intrinsic lock):** every Java object has a hidden lock. `synchronized` takes that lock so only one thread at a time runs the protected code. This stops threads from corrupting shared data.
- **NEW:** the thread object exists, but `start()` has not been called.
- **RUNNABLE:** the thread is running, or is ready and waiting for CPU time. A thread blocked on network or file I/O usually also shows as RUNNABLE.
- **BLOCKED:** the thread wants to enter a `synchronized` block, but another thread holds the monitor. It waits for the lock.
- **WAITING:** the thread waits with no time limit for another thread's action (`wait()`, `join()`, `LockSupport.park()`).
- **TIMED_WAITING:** the same, but with a time limit (`sleep(ms)`, `wait(ms)`, `join(ms)`).
- **TERMINATED:** the thread has finished `run()`.
- **`wait()` / `notify()` / `notifyAll()`:** a way for threads to coordinate. A thread that finds its condition false (for example "queue is empty") calls `wait()` to sleep. Another thread changes the state and calls `notify()` to wake one waiter, or `notifyAll()` to wake all. All three must be called inside `synchronized` on the same object, otherwise you get `IllegalMonitorStateException`.
- **Spurious wakeup:** a waiting thread can wake up even though nobody notified it. This is allowed by the JVM and the OS.

**The live scenario**
An order service has 200 worker threads. At peak, about 3,000 requests per minute arrive and latency rises from 80 ms to 12 s. A thread dump shows 150 threads BLOCKED on one `synchronized` method of a shared object, and 30 threads WAITING. A custom hand-made queue also sometimes returns `null` to a consumer. The consumer used `if (queue.isEmpty()) wait();`, woke up spuriously or after another consumer took the item, and carried on with an empty queue. Reading the states told the team where to look.

**What the interviewer is really checking**
Whether you know the states as a lifecycle, can tell BLOCKED from WAITING, and understand that `wait()` releases the lock and must be used in a loop. Bonus: knowing modern code avoids raw `wait/notify`.

**How I answer it**
1. **Name the six states in lifecycle order:** NEW, RUNNABLE, BLOCKED, WAITING, TIMED_WAITING, TERMINATED. This shows you see a thread's life as a flow, not a list to memorise.
2. **Separate BLOCKED from WAITING.** BLOCKED means "I want a lock someone else holds". WAITING means "I chose to pause until someone signals me". The fix differs: BLOCKED points to lock contention, WAITING points to a missing signal.
3. **Explain `wait()`.** The thread must own the monitor. `wait()` releases it, so other threads can enter and change the state, then the thread sleeps. It wakes on `notify`, `notifyAll`, a timeout (if given) or an interrupt.
4. **Mention the wake-up path.** A notified thread does not run immediately. It becomes BLOCKED until it re-acquires the monitor, and `notify()` itself does not release the lock; that happens only when the notifier leaves its `synchronized` block.
5. **Always wait in a loop**, because of spurious wakeups and because another thread may have consumed the condition first:
```java
synchronized (lock) {
    while (queue.isEmpty()) lock.wait();
    item = queue.poll();
}
```
6. **Say what you would use today:** `BlockingQueue` (producer-consumer), `CountDownLatch` (wait for N events), `Condition` (several wait conditions per `Lock`). They handle the loop and locking for you, so there is less room for error.

**Trade-offs and what can go wrong**
- `if` instead of `while` causes bugs that appear rarely and are hard to reproduce.
- `notify()` wakes only one arbitrary waiter. If waiters wait for different conditions, the wrong one wakes and the signal is lost; `notifyAll()` is safer but wakes more threads.
- Calling `wait/notify` without holding the monitor throws an exception.
- Notifying before the waiter starts waiting means the signal is lost, so always check a state variable.
- Heavy `synchronized` use makes many threads BLOCKED and hurts throughput.

**How I'd monitor it**
- Take 3 thread dumps about 10 seconds apart (`jstack <pid>` or `jcmd <pid> Thread.print`). Threads stuck in the same state and stack across dumps are the problem.
- Count threads by state; a growing BLOCKED count means lock contention.
- Use JFR or a profiler's lock-contention view.
- Track request latency and thread pool queue size, and alert when they rise.
- Search Splunk for timeout and `InterruptedException` messages.

**Follow-ups to expect**
- *What is the difference between `sleep()` and `wait()`?* -> `sleep()` pauses the thread and keeps any locks it holds. `wait()` releases the monitor and needs `notify` or a timeout.
- *Why does `wait()` live in `Object` and not `Thread`?* -> The lock belongs to the object, so you wait on the object whose condition you are watching.
- *How do you find a deadlock?* -> A thread dump shows threads BLOCKED on each other's locks, and `jstack` reports "Found one Java-level deadlock".

**60-second answer**
A Java thread is in one of six states: NEW before `start()`, RUNNABLE when running or ready, BLOCKED when it waits for a `synchronized` lock, WAITING or TIMED_WAITING when it pauses for a signal or a time, and TERMINATED when done. `wait()` must be called while holding an object's monitor. It releases that monitor, sleeps until `notify`, `notifyAll`, a timeout or an interrupt, and then must re-acquire the lock before continuing. I always call it inside a `while(!condition)` loop, because threads can wake spuriously or another thread may have taken the condition first. In real code I prefer `BlockingQueue`, `CountDownLatch` or `Condition`, because they are safer and easier to read. In production I read thread dumps: many BLOCKED threads mean lock contention.

### Q35 [mid] What is a race condition vs a deadlock vs a livelock vs starvation?
tags: concurrency, race-condition, deadlock, livelock, starvation, threads, locks, basics

**Start here: the concepts**
- **Thread:** a path of execution inside a program. Several threads run at the same time and share the same memory, so they can interfere with each other.
- **Shared mutable state:** data that more than one thread can change. If nothing is shared or nothing changes, none of these problems exist.
- **Lock (monitor):** a "one at a time" token. A thread that holds it makes others wait. It exists to protect shared data from being changed by two threads at once.
- **Race condition:** the result depends on the timing of threads. Two classic shapes:
  - *Check-then-act:* "if stock > 0, then reduce stock". Another thread can change the stock between the check and the act.
  - *Read-modify-write:* `i++` is really three steps (read, add, write). Two threads can both read 5 and both write 6, so one update is lost.
- **Deadlock:** thread A holds lock 1 and waits for lock 2, while thread B holds lock 2 and waits for lock 1. Both are blocked forever and use no CPU.
- **Livelock:** threads are not blocked. They keep reacting to each other (for example both politely step aside, again and again) and use CPU but make no progress.
- **Starvation:** one thread never gets the lock or CPU time because others always go first. Causes include unfair locks and thread priorities.

**The live scenario**
A flash-sale service handles about 300 requests per second. Two bugs appear in one week:
- The stock check is `if (stock > 0) stock--;` on a shared field. Under load, 37 items are oversold. That is a race condition.
- Later, a money-transfer endpoint locks the "from" account and then the "to" account. Two opposite transfers (A to B and B to A) arrive together. Both threads hang, and after a few minutes the 200-thread pool is full of stuck requests and the service stops answering. That is a deadlock.

**What the interviewer is really checking**
Whether you can tell apart four problems that sound alike (wrong result, blocked forever, busy but stuck, unfairly ignored) and give a concrete fix for each.

**How I answer it**
1. **Race condition = wrong result from bad timing.** The program keeps running but the answer is wrong. Fix it by making the check and the act one atomic step: `synchronized`, `AtomicInteger`, or `ConcurrentHashMap.merge()`. Better still, avoid sharing mutable data.
2. **Deadlock = threads wait for each other in a circle.** Nobody can move, and CPU stays low. Fix it in one of three ways:
   - Use a **global lock ordering**, for example always lock the lower account id first. A circle cannot form if everyone takes locks in the same order.
   - Use `tryLock(timeout)` and back off if you cannot get the second lock.
   - Use fewer locks, so there is nothing to wait in a circle for.
3. **Livelock = busy but no progress.** Threads are running, not blocked. A common cause is a `tryLock` retry loop where both sides give up and retry at the same instant. Fix it with a random delay (jitter) before retrying.
4. **Starvation = one thread is always passed over.** The system as a whole makes progress, but one thread does not. Fix it with fair locks (`new ReentrantLock(true)`), avoiding priority tricks, and keeping lock-holding sections short.
5. **Quick way to tell them apart:** wrong value means race. Frozen with low CPU means deadlock. Frozen with high CPU means livelock. One task is slow while others are fine means starvation.

```java
Account first = a.id < b.id ? a : b, second = first == a ? b : a;
synchronized (first) { synchronized (second) { transfer(); } }
```

**Trade-offs and what can go wrong**
- Locking everything fixes races but raises the deadlock risk and lowers throughput.
- Fair locks prevent starvation but are slower than unfair ones.
- `tryLock` can turn a deadlock into a livelock if you retry without a delay.
- Races are hard to reproduce, because tests pass until the timing is unlucky.
- A common mistake is thinking `volatile` makes `i++` safe. It does not.

**How I'd monitor it**
- Take a thread dump with `jstack <pid>` or `jcmd <pid> Thread.print`. The JVM prints "Found one Java-level deadlock" and lists the threads and locks involved.
- In code, `ThreadMXBean.findDeadlockedThreads()` can feed a health check.
- Watch for a blocked-thread count that keeps rising and a thread pool whose queue is full. In Splunk, search for request timeouts that cluster after a deploy or a load spike.
- Livelock shows as high CPU with flat throughput.
- Starvation shows as high p99 latency for some requests while the average looks fine.
- Races show as business-rule breaks, for example reconciliation finding stock below zero.

**Follow-ups to expect**
- *What are the four conditions for deadlock?* -> Mutual exclusion, hold-and-wait, no preemption, and circular wait. Break any one and deadlock cannot happen. Lock ordering breaks circular wait.
- *Is a race condition the same as a data race?* -> No. A data race is unsynchronised access to the same memory where at least one access is a write. A race condition is any timing-dependent wrong behaviour. You can have a race condition even with fully synchronised individual operations (check-then-act across two calls).
- *Does `synchronized` stop starvation?* -> No. It gives no fairness guarantee, so use a fair `ReentrantLock` if that matters.

**60-second answer**
A race condition means the result depends on thread timing, like `i++` or check-then-act on shared data, and it gives wrong answers. I fix it with atomic operations or locks, or by not sharing mutable state. A deadlock is when two threads each hold a lock the other needs, so both wait forever with no CPU use. I prevent it with a global lock order, `tryLock` with a timeout, or fewer locks. A livelock is when threads keep reacting to each other and burn CPU without progress, and random backoff fixes it. Starvation is when one thread never gets the lock or CPU, for example from unfair locks, and fair locks or shorter critical sections help. In production I take a thread dump, which names deadlocks directly, and watch CPU, blocked threads and latency.

### Q36 [mid] How do you detect a deadlock in production?
tags: deadlock, thread-dump, jstack, jcmd, threadmxbean, concurrency, basics

**Start here: the concepts**
- **Thread**: one independent path of execution inside the JVM. A server runs many threads at once, for example one per request.
- **Lock (monitor)**: a "only one thread at a time" guard. `synchronized` and `ReentrantLock` both create one. It exists so two threads don't corrupt shared data.
- **Deadlock**: Thread A holds lock 1 and waits for lock 2, while Thread B holds lock 2 and waits for lock 1. Neither can move, and neither will ever release its lock. It never fixes itself.
- **Thread dump**: a snapshot of every thread, showing its state, its stack trace, which locks it holds and which lock it waits for. It is the main tool for seeing what a stuck JVM is doing.
- **jstack / jcmd**: JDK command-line tools that ask a running JVM for a thread dump. You pass the process id (`<pid>`).
- **ThreadMXBean**: a built-in Java management object (JMX) that lets the program inspect its own threads, including deadlock detection.

**The live scenario**
An order service normally answers in 200 ms. At 2:10 pm, requests start timing out. After 15 minutes the 200-thread pool is exhausted and the load balancer marks pods unhealthy. CPU is near 2%, which is odd for a "busy" service. Threads are not working, they are waiting. Two code paths update the `Account` and `Ledger` objects, but in opposite lock order. Under load they collided and froze. Restarting would clear it, but the evidence would be lost and the bug would return.

**What the interviewer is really checking**
Whether you can diagnose a hung system methodically without restarting it first, and whether you know a deadlock (a permanent cycle) is different from slowness (threads waiting on something external).

**How I answer it**
1. **Notice the symptom.** Requests hang, thread pool is full, CPU is low. Low CPU with stuck requests suggests threads are blocked, not computing.
2. **Take a thread dump before restarting.** Run `jcmd <pid> Thread.print` or `jstack <pid>`. A restart destroys the evidence. (`kill -3 <pid>` also prints a dump to the JVM's stdout.)
3. **Read the deadlock section.** If a Java-level deadlock exists, the dump says **"Found one Java-level deadlock"** and lists the cycle: each thread, the lock it holds and the lock it waits for. The stack traces show the exact lines of code.
4. **Take 3 dumps about 10 seconds apart.** A real deadlock shows the same threads on the same lines every time. A slow system, such as a database wait or heavy lock contention, shows threads changing between dumps. So the repeated dumps separate "permanently stuck" from "just slow". For a true deadlock one dump is enough to name the cycle.
5. **Detect it automatically.** `ThreadMXBean` can find deadlocks from inside the app, and you can publish the result as a health metric:
```java
ThreadMXBean t = ManagementFactory.getThreadMXBean();
long[] ids = t.findDeadlockedThreads(); // null means none
```
6. **Fix the cause.** Make every code path take locks in the same order, or use `tryLock` with a timeout, or reduce the locks needed.

**Trade-offs and what can go wrong**
- The dump only detects deadlocks among Java locks. `findDeadlockedThreads()` covers both `synchronized` and `ReentrantLock`, while `findMonitorDeadlockedThreads()` covers `synchronized` only.
- It does not detect "logical" deadlocks, such as threads waiting on each other through a queue, a database lock or a remote call. There you read the stack traces yourself.
- Taking a dump briefly pauses the JVM (a safepoint), which is usually fine but not free on very large heaps or thread counts.
- Polling `findDeadlockedThreads()` too often adds overhead. Once every 30-60 seconds is usually plenty.
- In Java 21, `Thread.print` does not list virtual threads. Use `jcmd <pid> Thread.dump_to_file -format=json <file>` for those.

**How I'd monitor it**
- Export a gauge, "deadlocked thread count", from `ThreadMXBean`, and alert when it is above 0.
- Alert on thread pool saturation, request latency and low CPU combined with rising active threads.
- Automate a thread dump to a file when the health check fails, and search the logs or Splunk for "Found one Java-level deadlock".

**Follow-ups to expect**
- *How do you prevent deadlocks?* -> Always acquire locks in one global order, hold them for as short a time as possible, and prefer `tryLock(timeout)` so a thread gives up instead of waiting forever.
- *Deadlock vs livelock vs starvation?* -> Deadlock: threads wait forever. Livelock: threads keep reacting to each other but make no progress. Starvation: a thread never gets a turn because others always win.
- *Can the JVM resolve a deadlock itself?* -> No. It can only report it, so you must restart or fix the code.

**60-second answer**
When requests hang, CPU is low and the thread pool is full, I suspect a deadlock. I take a thread dump before restarting, using `jcmd <pid> Thread.print` or `jstack`. If there is a Java-level deadlock, the dump prints "Found one Java-level deadlock" with the cycle of threads and locks. I take three dumps about ten seconds apart. If the same threads stay on the same lines, they are truly stuck and not just slow. For early warning I expose `ThreadMXBean.findDeadlockedThreads()` as a health metric and alert when it is non-zero. The fix is to take locks in a consistent order or use timeouts.

### Q37 [mid] ExecutorService - how do you size a thread pool?
tags: java, executorservice, thread-pool, concurrency, backpressure, threadpoolexecutor, basics

**Start here: the concepts**
- **Thread**: a worker that runs code. Creating one is costly (memory for its stack, scheduling work for the OS), so we reuse them.
- **Thread pool / ExecutorService**: a fixed set of reusable threads that take tasks from a queue. You submit work and the pool decides which thread runs it.
- **CPU-bound task**: a task that spends its time calculating (parsing, hashing, sorting). It keeps a CPU core busy the whole time.
- **I/O-bound task**: a task that spends most of its time waiting for a database, a REST call or a disk. The core is idle while it waits.
- **Core**: one unit of hardware that runs one thread at a time. Check `Runtime.getRuntime().availableProcessors()`.
- **Queue**: the waiting line for tasks when all threads are busy. *Bounded* means it has a maximum size. *Unbounded* means it can grow until memory runs out.
- **Rejection policy**: what the pool does when both the threads and the queue are full. The options are throw an error, drop the task, or make the caller run it.
- **Back-pressure**: slowing down the producer when the consumer cannot keep up, instead of piling up work.
- **OOM (OutOfMemoryError)**: the JVM has run out of heap and the process fails.

**The live scenario**
An 8-core order service calls a payment API. Each task takes about 200 ms, of which 20 ms is computing and 180 ms is waiting. Someone used `Executors.newFixedThreadPool(8)`, which seems sensible for 8 cores. Throughput was poor, because the 8 threads spent 90% of their time idle while waiting. Later the payment API slowed down. Tasks kept arriving, the hidden unbounded queue grew to millions of objects, and the service died with an OOM. The right fix was a larger pool, a bounded queue and a clear rejection policy.

**What the interviewer is really checking**
Whether you size a pool from the workload type (CPU-bound or I/O-bound) rather than guessing, and whether you know the dangerous defaults: the unbounded queue and the lack of back-pressure.

**How I answer it**
1. **Classify the work first.** CPU-bound and I/O-bound tasks need very different pool sizes. Extra threads on CPU-bound work only add context switching.
2. **CPU-bound: about the number of cores, or cores + 1.** More threads than cores cannot run in parallel. The "+1" covers the occasional thread that pauses, for example on a page fault.
3. **I/O-bound: `cores * (1 + wait/compute)`.** While one thread waits, others can use the core. With 8 cores and 90% waiting, wait/compute is 9, so 8 × (1 + 9) = **80 threads**.
4. **Treat the formula as a starting point.** Load-test and adjust. Also check the downstream limits: 80 threads are useless if the database connection pool has only 20 connections.
5. **Use a bounded queue and an explicit rejection policy.** This is the part that keeps the service alive under overload.
   ```java
   new ThreadPoolExecutor(80, 80, 0L, TimeUnit.SECONDS,
       new ArrayBlockingQueue<>(200), namedThreadFactory,
       new ThreadPoolExecutor.CallerRunsPolicy());
   ```
6. **`CallerRunsPolicy` gives back-pressure.** When the pool is full, the submitting thread runs the task itself. It is then busy and cannot submit more, so the producer slows down.
7. **Avoid `Executors.newFixedThreadPool` in production.** It uses an unbounded queue, so tasks pile up silently until OOM.
8. **Name your threads** (for example `order-io-1`) so thread dumps and logs show which pool a thread belongs to.

**Trade-offs and what can go wrong**
- Too few threads means idle CPUs and low throughput. Too many means memory use, context switching and overload on downstream systems.
- A small queue rejects tasks sooner. A large one hides overload and adds latency.
- `CallerRunsPolicy` can block an important caller, such as a Kafka consumer's poll loop or a web request thread. That can cause timeouts or a consumer-group rebalance. Sometimes failing fast with `AbortPolicy` and returning an error is better.
- With an unbounded queue, `ThreadPoolExecutor` never grows past its core size, because it only adds threads when the queue is full. A large max size is then meaningless.
- Mixing slow I/O tasks and fast CPU tasks in one pool lets the slow ones starve the fast ones. Use separate pools.

**How I'd monitor it**
- Export the pool's active thread count, queue size, completed tasks and rejected count (for example via Micrometer or a custom rejection handler).
- Alert when queue depth stays near its limit or rejections rise.
- Search Splunk for `RejectedExecutionException` and for task latency by thread name.
- Watch heap usage and GC time. A steadily growing heap alongside a growing queue is the OOM warning.
- Take a thread dump if throughput stalls, to see whether threads are waiting or blocked.

**Follow-ups to expect**
- *Why does a larger max pool size not help with an unbounded queue?* -> Extra threads are created only when the queue is full, and an unbounded queue never fills.
- *What changes with Java 21 virtual threads?* -> For I/O-bound work you can use one cheap virtual thread per task instead of tuning a pool size. You still need limits on downstream resources, for example with a semaphore.
- *Why is `newCachedThreadPool` risky?* -> It has no cap on thread count, so a burst can create thousands of threads and exhaust memory.

**60-second answer**
First I decide whether the work is CPU-bound or I/O-bound. For CPU-bound work I use about the number of cores, or cores plus one. For I/O-bound work I use cores × (1 + wait/compute). With 8 cores and 90% waiting, that is about 80 threads. That is only a starting point, so I load-test it and check downstream limits such as database connections. I never use `Executors.newFixedThreadPool` in production, because its unbounded queue can fill the heap and cause an OOM. I build a `ThreadPoolExecutor` with a bounded queue and a rejection policy. `CallerRunsPolicy` gives back-pressure by making the caller do the work. I name the threads and monitor active threads, queue size and rejections.

### Q38 [mid] Runnable vs Callable vs Future vs CompletableFuture?
tags: java8, concurrency, completablefuture, callable, future, executor, basics

**Start here: the concepts**
- **Thread / task:** a thread is a worker that runs code. A task is a unit of work you hand to a worker. Java separates "what to run" (the task) from "who runs it" (the thread).
- **Executor / thread pool:** a fixed team of reusable threads that picks up tasks from a queue. It exists because creating a thread per request is slow and can exhaust memory.
- **Runnable:** a task with `void run()`. It returns nothing and cannot throw checked exceptions.
- **Callable<V>:** like Runnable, but `V call() throws Exception` returns a result and may throw checked exceptions.
- **Future<V>:** a receipt for work submitted to an executor. `get()` waits until the result is ready, and that wait **blocks** the calling thread. You can't say "when done, do X", and you can't combine several Futures without blocking.
- **CompletableFuture<V>** (Java 8): a Future you can chain. You describe the next steps ("then do this with the result") and they run when the result arrives, without a thread sitting idle waiting.
- **Common pool:** the shared default thread pool (`ForkJoinPool.commonPool()`) that async methods use if you pass no executor. It is small, roughly the CPU core count, and shared by the whole JVM, including parallel streams.

**The live scenario**
A profile page called a user service (about 120 ms) and an order service (about 180 ms) one after the other, so each page took about 300 ms. The team moved to `CompletableFuture` to run both calls in parallel, which cut the time to about 180 ms. They forgot to pass an executor, so the blocking HTTP calls ran on the common pool of 7 threads. At peak, all 7 threads sat waiting on a slow order service. Unrelated parallel streams in the same JVM stalled, and latency rose to seconds. Giving the calls a dedicated, sized pool and adding a timeout fixed it.

**What the interviewer is really checking**
Whether you know the evolution (Runnable, Callable, Future, CompletableFuture) and why each step exists. They also want to know whether you know the production traps: blocking `get()`, the default common pool, and missing timeouts and fallbacks.

**How I answer it**
1. **Runnable:** use it for fire-and-forget work, because it has no result and no checked exception. Reason: it is the oldest, simplest task type.
2. **Callable:** use it when you need a result or a checked exception. Reason: `call()` returns a value and may throw, which Runnable can't do.
3. **Future:** `executor.submit(callable)` returns one. Calling `get()` blocks the thread until the result is ready. Reason: it gives a result but no chaining, so combining three calls means three blocking waits.
4. **CompletableFuture:** use it to build a pipeline of steps that fires when data arrives. Reason: it avoids tying up threads and lets you combine independent calls.
5. **Always pass your own executor** to `supplyAsync`. Reason: the default is the small, shared common pool, and blocking calls there starve everything else.
6. **Know the combinators:**
   - `thenApply` is map (transform the value).
   - `thenCompose` is flatMap (the next step itself returns a CompletableFuture).
   - `thenCombine` merges two independent futures.
   - `allOf` waits for all of them and returns `CompletableFuture<Void>`.
   - `anyOf` returns the first one to finish.
7. **Add a timeout and a fallback.**

```java
CompletableFuture.supplyAsync(() -> userSvc.get(id), pool)
  .thenCombine(CompletableFuture.supplyAsync(() -> orderSvc.get(id), pool), Profile::new)
  .orTimeout(2, TimeUnit.SECONDS)      // Java 9+, not in Java 8
  .exceptionally(ex -> Profile.fallback());
```

**Trade-offs and what can go wrong**
- `orTimeout` needs Java 9 or later. On Java 8 you must build the timeout yourself.
- A timeout completes the future exceptionally, but it does **not** stop the work already running in the pool.
- `exceptionally` hides errors, so log the exception inside it.
- Calling `join()` or `get()` inside a chain brings back the blocking you were trying to avoid.
- Chains with no async suffix may run on whichever thread completed the previous step.
- Pools that are too small cause queueing, and pools that are too large overload downstream services.
- Debugging is harder because stack traces are split across async steps.

**How I'd monitor it**
- Pool metrics: active threads, queue size, and rejected tasks.
- Timeout and fallback counts, logged with a clear message and searchable in Splunk.
- p95 and p99 latency of the endpoint.
- Thread dumps showing threads parked in `get()` or in `ForkJoinPool.commonPool-worker` threads.

**Follow-ups to expect**
- *thenApply vs thenCompose?* -> `thenApply` maps a value to a value. `thenCompose` is for when your function returns another CompletableFuture and you want it flattened, not nested.
- *What happens if one future in `allOf` fails?* -> The combined future completes exceptionally, but the others keep running, and you must inspect each one for its result.
- *Does `get()` vs `join()` differ?* -> Both block. `get()` throws checked exceptions, while `join()` throws an unchecked `CompletionException`.

**60-second answer**
Runnable is a task with no result. Callable returns a result and can throw checked exceptions. Future is the receipt you get when you submit a Callable to an executor, but `get()` blocks and you can't chain it. CompletableFuture, added in Java 8, lets you chain steps such as `thenApply` and `thenCompose`, combine calls with `thenCombine` or `allOf`, and handle errors with `exceptionally`, all without waiting on a thread. I always pass my own executor, because the default common pool is small and shared, and blocking calls on it can starve the whole JVM. I also add a timeout (`orTimeout`, Java 9+) and a fallback, and I monitor pool queue size and p99 latency.

### Q39 [mid] ReentrantLock vs synchronized? ReadWriteLock vs StampedLock?
tags: java, concurrency, locks, reentrantlock, synchronized, readwritelock, stampedlock, basics

**Start here: the concepts**
- **Lock (mutual exclusion):** a rule that lets only one thread at a time run a piece of code that touches shared data. Without it, two threads can corrupt the data by interleaving their steps.
- **`synchronized`:** Java's built-in lock, using the `synchronized` keyword on a method or block. The JVM acquires and releases it for you, even if an exception is thrown.
- **`ReentrantLock`:** a lock object from `java.util.concurrent.locks`. You call `lock()` and `unlock()` yourself, which gives extra controls.
- **Reentrant:** a thread that already holds the lock can take it again without blocking itself. Both `synchronized` and `ReentrantLock` are reentrant.
- **`tryLock` / timeout / interruptible:** "try to get the lock, but don't wait forever", "wait at most N ms", and "stop waiting if another thread interrupts me". Plain `synchronized` can only wait indefinitely.
- **Fairness:** a fair lock serves waiting threads in arrival order. An unfair one lets newcomers jump ahead, which is usually faster but can starve a thread.
- **`Condition`:** a "wait until X is true" signal tied to a lock, like `wait/notify` but with several separate wait queues per lock.
- **`ReadWriteLock`:** two locks in one. Many threads may hold the read lock together, but the write lock is exclusive. Its main implementation is `ReentrantReadWriteLock`.
- **`StampedLock` (Java 8):** like a read-write lock, but it returns a "stamp" (a version number). An optimistic read takes no lock: you read, then check the stamp to see whether a writer interfered.

**The live scenario**
A pricing service keeps an in-memory rate table. It gets about 5,000 reads per second and about 20 updates per minute. The first version put `synchronized` on every method, so readers queued behind each other even though they never change anything. Under load, p99 latency rose from about 20 ms to about 300 ms (illustrative numbers). Switching to a read-write lock let readers run in parallel and brought latency back down.

**What the interviewer is really checking**
Do you pick a lock by access pattern (read-heavy or write-heavy, need for timeouts) rather than by habit? Do you know the pitfalls: forgetting `unlock`, lock upgrades, and the non-reentrant `StampedLock`?

**How I answer it**
1. **Start with `synchronized`.** It is simple, and the JVM releases it automatically, so it cannot leak a lock. It is enough for most code.
2. **Move to `ReentrantLock` only when I need its extras:** `tryLock`, timeouts, interruptible waiting, fairness, or several `Condition`s. Each one lets a thread avoid hanging forever. The price is that I must release it myself:
   ```java
   lock.lock();
   try { /* critical section */ } finally { lock.unlock(); }
   ```
   If `unlock` is skipped after an exception, the lock stays held and other threads block forever.
3. **Use `ReadWriteLock` for read-heavy data.** Readers don't conflict with each other, so allowing them in parallel removes needless waiting. A writer still waits for readers and then blocks everyone.
4. **Use `StampedLock` for very read-heavy, short reads.** An optimistic read takes no lock, which is cheap. After reading, I call `validate(stamp)`. If a writer got in, I retry with a real read lock. It is not reentrant, so locking twice in one thread deadlocks. It also has no `Condition` support.
5. **Measure before switching.** A fancier lock helps only if contention is the real bottleneck.

**Trade-offs and what can go wrong**
- Forgetting `finally` on `unlock()` is the classic `ReentrantLock` bug.
- `ReentrantReadWriteLock` allows downgrading (write to read) but not upgrading (read to write). Trying to upgrade deadlocks.
- If writes are frequent or the critical section is tiny, a read-write lock costs more than a plain lock. Heavy readers can also delay writers.
- `StampedLock` is easy to misuse. You must re-read the data after a failed validation, and you must not call code that re-enters the lock.
- Fair locks reduce starvation but lower throughput.
- In Java 21, a virtual thread blocked inside `synchronized` can pin its carrier thread. `ReentrantLock` does not have this problem.

**How I'd monitor it**
- Take thread dumps (`jstack`) and look for many threads in `BLOCKED` or `WAITING` on the same lock.
- Use Java Flight Recorder monitor-contention events.
- Call `getQueueLength()` on a `ReentrantLock` and expose it as a metric.
- Log and count failed `tryLock` attempts, then alert on spikes in Splunk.
- Track p99 latency before and after a lock change.

**Follow-ups to expect**
- *Is `synchronized` slower than `ReentrantLock`?* -> Not meaningfully in modern JVMs. Choose by features, and measure if it matters.
- *Why must `unlock` be in `finally`?* -> An exception would otherwise skip it and leave the lock held forever.
- *What does optimistic read mean?* -> Read without locking, then validate the stamp. If a writer intervened, retry with a real lock.

**60-second answer**
`synchronized` is the simple built-in lock that the JVM releases automatically. `ReentrantLock` adds `tryLock`, timeouts, interruptible waiting, optional fairness and multiple `Condition`s. In return, I must call `unlock` in a `finally` block. A `ReadWriteLock` lets many readers run together while a writer is exclusive, so it suits read-heavy data. I can downgrade from write to read, but upgrading deadlocks. `StampedLock` adds optimistic reads: I read without a lock and validate a stamp, retrying if a writer interfered. It is fast for read-heavy code, but it is not reentrant and is easy to misuse. I default to `synchronized` and move to the others only when measurements show contention or I need their features.

### Q40 [mid] What are CountDownLatch, CyclicBarrier, Semaphore, Phaser?
tags: countdownlatch, cyclicbarrier, semaphore, phaser, synchronizers, concurrency, basics

**Start here: the concepts**
- **Thread:** a path of execution inside a program. Many threads run at once, and sometimes they must coordinate: wait for each other, or limit how many run a section at the same time.
- **Synchronizer:** a `java.util.concurrent` helper class that coordinates threads. All four classes here are synchronizers. Each is a counter plus a rule for when waiting threads are released.
- **CountDownLatch:** starts at N. Threads call `countDown()` as events finish, and other threads call `await()` and block until the count reaches 0. It is one-shot: the count never resets.
- **CyclicBarrier:** a meeting point for a fixed number of threads. Each calls `await()` and blocks until all N have arrived, then all are released together. It resets itself, so it can be reused ("cyclic"). It can also run an optional action when the last thread arrives.
- **Semaphore:** holds a number of permits. A thread calls `acquire()` to take one (blocking if none are left) and `release()` to return it. It caps how many threads are inside a section at once.
- **Phaser:** a barrier for work done in phases (step 1, then step 2, and so on). Unlike CyclicBarrier, threads can register and deregister while it runs. It also tracks the current phase number.

**The live scenario**
A payments service calls a partner API that allows at most 10 simultaneous connections. At peak, 200 request threads hit it and the partner returned HTTP 429 (too many requests) on about 30% of calls. A `Semaphore(10)` around the call fixed it: only 10 calls were in flight and the rest waited briefly. The same service also loads 4 reference-data caches in parallel at startup. A `CountDownLatch(4)` kept it from accepting traffic until all four finished.

**What the interviewer is really checking**
Whether you can pick the right tool for the situation and know the key differences: one-shot vs reusable, waiting for events vs waiting for each other, and limiting concurrency.

**How I answer it**
1. **Latch: "wait until N things happen."** Workers call `countDown()` and do not wait. One or more other threads `await()`. The count can't be reset, so it is used once, for example startup or test coordination.
2. **Barrier: "everyone waits for everyone."** All N threads are both the waiters and the arrivers. Once the last one arrives, all continue and the barrier resets for the next round. Use it for iterative work where every thread must finish round 1 before round 2 starts.
3. **Semaphore: "limit concurrent access."** Set the permits to the limit, and always release in a `finally` block so a failure doesn't leak permits:
```java
if (sem.tryAcquire(2, TimeUnit.SECONDS)) { try { call(); } finally { sem.release(); } }
```
4. **Phaser: "a barrier whose membership changes."** Use it when the number of participants varies or there are many phases. Threads call `register()`, `arriveAndAwaitAdvance()` and `arriveAndDeregister()`.
5. **State the correction:** a Semaphore limits how many calls are in flight at once, not calls per second. A true rate limit (for example 100 per second) needs a rate limiter such as a token bucket.

**Trade-offs and what can go wrong**
- A forgotten `countDown()`, for example after an exception, makes `await()` hang forever. Put it in `finally` and use `await(timeout)`.
- If one thread of a CyclicBarrier times out, is interrupted or dies, the barrier breaks and the others get `BrokenBarrierException`.
- Forgetting to release a Semaphore permit slowly starves the service.
- Plain `acquire()` can block forever. Prefer `tryAcquire` with a timeout and a fallback.
- A Semaphore has no owner, so any thread can release it. That is flexible but easy to misuse, unlike a lock.
- Don't reuse a CountDownLatch expecting a reset.

**How I'd monitor it**
- Take thread dumps (`jstack`) and look for threads stuck `WAITING` in `CountDownLatch.await` or `Semaphore.acquire`.
- Export `availablePermits()` and `getQueueLength()` as gauges. Alert when permits stay at 0 or the queue keeps growing.
- Count `tryAcquire` timeouts and log them, then search for them in Splunk and alert on a spike.
- Track partner 429 rates and call latency before and after the limit.

**Follow-ups to expect**
- *CountDownLatch vs CyclicBarrier?* -> A latch is one-shot, and the waiters are usually different threads from the ones counting down. A barrier is reusable, and the same N threads wait for each other.
- *Semaphore vs lock?* -> A lock has one owner at a time. A Semaphore allows N holders and isn't tied to a thread, so any thread may release.
- *What if a thread fails at a barrier?* -> The barrier breaks and the other waiting threads get `BrokenBarrierException`.

**60-second answer**
These are four tools for coordinating threads. A CountDownLatch makes threads wait until N events have happened. It is one-shot, so I use it for things like startup. A CyclicBarrier makes N threads wait for each other, then releases them together and resets, so it suits repeated rounds. A Semaphore holds permits and limits how many threads are in a section at once, for example 10 concurrent calls to a partner API. It caps concurrency, not calls per second. A Phaser is a flexible multi-phase barrier where threads can join and leave. I always release in `finally`, use timeouts, and watch permit counts and thread dumps in production.

### Q41 [mid] What is the Java Memory Model "happens-before"?
tags: java, concurrency, memory-model, happens-before, volatile, synchronized, basics

**Start here: the concepts**
- **Thread:** an independent path of execution inside one program. Several threads can read and write the same objects.
- **Visibility:** whether a value written by one thread can be seen by another. It is not automatic, because each CPU core has its own caches and registers.
- **Reordering:** the compiler, the JIT and the CPU may change the order of instructions, or keep a value in a register, as long as a single thread cannot tell the difference. Another thread can tell.
- **Java Memory Model (JMM):** the part of the Java language specification that says which values a thread may see when it reads a variable that other threads write.
- **Happens-before:** a guarantee between two actions, A and B. If A happens-before B, everything A did (including writes made before A) is visible to B, and A is ordered before B. It describes visibility and ordering, not wall-clock time.
- **Monitor:** the lock behind `synchronized`.
- **Volatile:** a field modifier. Reads and writes of that field go straight to shared memory with ordering guarantees.

**The live scenario**
A batch worker loops on `while (running) { process(); }`, and `running` is a plain `boolean`. A shutdown hook sets it to `false`. In tests it stops. In production, after the JIT compiles the hot loop, the worker may read `running` once and never re-read it. In this example, 3 of 12 pods ignored the stop signal, rolling deployments hung for 30 minutes until Kubernetes killed the pods, and in-flight records were lost. Declaring the field `volatile` fixed it.

**What the interviewer is really checking**
Whether you understand that "thread B sees thread A's write" is not guaranteed by default. They also want you to name the specific rules that create the guarantee, and not just say "use volatile".

**How I answer it**
1. **Say the problem first.** Without a happens-before edge, a reader may see stale values or an unexpected order of writes, because caches and reordering are allowed.
2. **Define the guarantee.** If A happens-before B, B sees A's effects. Within one thread, program order gives this automatically.
3. **List the rules.**
   - Unlock of a monitor happens-before every later lock of the *same* monitor. This is why `synchronized` publishes data.
   - A volatile write happens-before every later read of the *same* variable.
   - `Thread.start()` happens-before every action in the started thread.
   - Every action in a thread happens-before another thread returns from `join()` on it (thread end).
   - Final fields are visible correctly after safe construction. This means `this` must not escape from the constructor, and other threads then see the final fields as set at the end of the constructor.
4. **Add transitivity.** If A happens-before B and B happens-before C, then A happens-before C. That is why writing ordinary fields and then a volatile flag lets a reader who sees the flag also see those fields.
5. **Show a tiny example.**
```java
volatile boolean ready; int data;      // writer: data = 42; ready = true;
// reader: if (ready) use(data);       // sees 42
```
6. **Close with the limit.** Happens-before gives visibility and ordering, not atomicity. `count++` on a volatile is still a race.

**Trade-offs and what can go wrong**
- Volatile and locks cost something: they limit optimisation, and locks can block threads. Use them where sharing actually happens.
- The rule applies to the *same* monitor or variable. Locking two different objects creates no edge.
- Reading a shared field without synchronisation "works on my laptop", then fails under JIT or on a different CPU architecture.
- Unsafe publication, such as storing `this` in a static field inside a constructor, breaks the final-field guarantee.
- Volatile does not make compound actions (check-then-act, increment) safe. Use `synchronized` or `AtomicInteger`.

**How I'd monitor it**
Visibility bugs rarely throw exceptions, so I look for symptoms: threads stuck in loops (repeated thread dumps showing the same RUNNABLE frame), shutdowns that time out, and counters that drift. I test with jcstress (the OpenJDK concurrency stress tool) and review code for shared mutable fields that lack volatile or a lock. In Splunk I search for shutdown-timeout or "forced kill" log lines by pod.

**Follow-ups to expect**
- *Does volatile make `i++` thread-safe?* -> No. It is a read, an add and a write, and two threads can interleave. Use `AtomicInteger` or a lock.
- *Why does `ConcurrentHashMap` not need extra synchronisation for visibility?* -> Its operations establish happens-before: a put happens-before a later get of that key, so the reader sees the stored object's state.
- *Does `synchronized` give more than volatile?* -> Yes. It gives mutual exclusion as well as visibility, and it covers several variables at once.

**60-second answer**
Happens-before is the Java Memory Model's guarantee that if action A happens-before action B, then B sees everything A did. I need it because CPUs cache values and compilers reorder instructions, so one thread's write is not automatically visible to another. The main rules are: unlocking a monitor before a later lock of the same monitor, a volatile write before a later read of that variable, `Thread.start()` before the new thread's actions, a thread's end before `join()` returns, and safely published final fields. The edges chain together through transitivity. I once saw a plain boolean stop flag ignored in production after JIT compilation; making it volatile fixed it. Happens-before gives visibility and ordering, not atomicity, so `count++` still needs a lock or an atomic class.

### Q42 [senior] Why is double-checked locking broken without `volatile`?
tags: java, concurrency, java-memory-model, volatile, singleton, double-checked-locking, basics

**Start here: the concepts**
- **Singleton:** a class that should have exactly one instance in the whole application. *Lazy* initialization means creating it on first use, not at startup.
- **Double-checked locking (DCL):** a trick to create a lazy singleton while avoiding a lock on every call. You check `if (instance == null)` without a lock. Only if it is null do you enter `synchronized` and check again.
- **Object creation is several steps:** `instance = new Singleton()` means (1) allocate memory, (2) run the constructor to fill in fields, (3) write the reference into `instance`.
- **Reordering:** the compiler, the JIT and the CPU may change the order of operations that look independent, as long as a *single* thread can't tell. Other threads can tell. Steps 2 and 3 can swap.
- **Java Memory Model (JMM) and happens-before:** the JMM is the rulebook for what one thread is guaranteed to see of another thread's writes. Without a happens-before relationship, there is no guarantee, even if the write happened earlier in wall-clock time.
- **`volatile`:** a write to a volatile field happens-before every later read of it. It also forbids moving earlier writes (like the constructor's) after the volatile write. This is the guarantee since Java 5 (JSR-133); before that, DCL could not be fixed.

**The live scenario**
A pricing service lazily creates a `RateTable` singleton. It handles about 5,000 requests per second across 200 threads. After the team moved to new hardware, roughly one request in several million failed with a `NullPointerException` inside `RateTable` methods. Right after a restart, when many threads race to initialize it, the failure was most likely. It could not be reproduced in tests. The cause was a non-volatile DCL field: a thread saw a non-null `instance` whose fields were not yet visible.

**What the interviewer is really checking**
Whether you understand visibility and ordering in the Java Memory Model, not just "use volatile". A senior should explain *why* the unsynchronized first read is the problem and offer safer alternatives.

**How I answer it**
1. **Show the pattern.** The first `if` is outside the lock to keep the fast path cheap. The second is inside the lock so only one thread creates the object.
2. **Explain the race.** The lock protects the writer, but the reader on the fast path takes no lock. So it has no happens-before link to the writer.
3. **Name the reordering.** The reference can be published (step 3) before the constructor's writes (step 2) are visible. A reader sees a non-null reference to a half-built object, with default values (null, 0) in its fields.
4. **Fix it with `volatile`.** The volatile write publishes the reference only after the construction writes. The volatile read then guarantees the reader sees them.
   ```java
   private static volatile Singleton instance;
   ```
5. **Prefer simpler designs.** The holder idiom (a private static nested class holding the instance) is lazy and thread-safe, because the JVM guards class initialization with its own lock. An `enum` singleton is also thread-safe, and it additionally resists serialization and reflection attacks. Or just create it eagerly in a `static final` field.

**Trade-offs and what can go wrong**
- The bug is rare, hardware-dependent and timing-dependent. x86 hides it more often than ARM, so passing tests prove nothing.
- `volatile` adds a small cost on every read. That is usually negligible, but it is why DCL exists at all.
- Making only the *fields* of the singleton non-final while leaving `instance` non-volatile is the exact trap.
- In a Spring app, a plain `@Component` is already a managed singleton, so hand-written DCL is rarely needed.

**How I'd monitor it**
- Search Splunk for `NullPointerException` with a top stack frame in the singleton's methods, grouped by host and time since JVM start. Clustering right after deploys is the signature.
- Run static analysis (SpotBugs flags unsafe DCL) and review any hand-written lazy init.
- Test with a concurrency harness like OpenJDK's jcstress, not ordinary unit tests.

**Follow-ups to expect**
- *Why not just synchronize the whole getter?* -> It is correct, but every call takes the lock. That is a contention cost on a hot path, which is why people reach for DCL.
- *Why does the holder idiom work without `volatile`?* -> The JVM runs class initialization once, under a lock, and publishes its result safely to all threads. The nested class only loads on first use, so it stays lazy.
- *Does `final` on the fields help?* -> Yes, the JMM gives special safe-publication guarantees for final fields. But relying on that is fragile compared with `volatile`, the holder idiom or an enum.

**60-second answer**
Creating an object is three steps: allocate memory, run the constructor, then store the reference. The compiler or CPU may reorder the last two. In double-checked locking, the first null check has no lock, so a reader has no happens-before link to the writer. It can see a non-null reference to a half-built object. Declaring the field `volatile` forbids that reordering and guarantees visibility, which works since Java 5. In practice I would avoid hand-written DCL and use the holder idiom, an `enum` singleton or a Spring-managed bean. The bug is rare and timing-dependent, so I would catch it with code review, static analysis and concurrency tests, not by waiting for a test to fail.

### Q43 [senior] ConcurrentHashMap: what is atomic and what is not?
tags: java, concurrenthashmap, concurrency, atomic-operations, collections, computeifabsent, basics

**Start here: the concepts**
- **Thread-safe collection:** a collection that several threads can use at once without corrupting its internal structure. `ConcurrentHashMap` (CHM) is a thread-safe hash map built for heavy concurrent use.
- **Atomic operation:** one that other threads see as either not started or fully finished, never half-done. Each CHM method call on a single key is atomic.
- **Race condition:** the result depends on which thread runs first. It usually appears when you chain two separate calls, such as "check, then act", and another thread slips in between them.
- **Check-then-act:** code like "if the key is absent, put it". Each call is safe on its own, but the pair is not atomic.
- **Bucket (bin) lock:** CHM stores entries in buckets. A write locks only the bucket it touches, so writes to different buckets run in parallel. Reads like `get` normally take no lock.
- **Compound atomic methods:** `putIfAbsent`, `computeIfAbsent`, `compute` and `merge` do the check and the write as one atomic step per key.
- **Weakly consistent / estimate:** `size()` and iterators reflect the map at roughly the time you asked. Under concurrent updates the answer can be slightly stale, but nothing crashes. Iterators do not throw `ConcurrentModificationException`.

**The live scenario**
A pricing service cached exchange rates in a CHM, about 3,000 requests per second. The code was `if (!map.containsKey(ccy)) map.put(ccy, fetchRate(ccy))`. On a cold start, many threads missed the same currency and each called the rate provider, so the provider saw about 200 duplicate calls in one second and began throttling.

The team switched to `computeIfAbsent(ccy, this::fetchRate)`. Duplicates disappeared, but p99 latency rose from 40 ms to 900 ms. `fetchRate` took roughly 800 ms and held the bucket lock the whole time, so other writers to that bucket waited.

**What the interviewer is really checking**
Whether you know that atomicity covers one call, not a sequence of calls. Also whether you can name the traps: slow work inside `compute*`, modifying the map from inside the function, and treating `size()` as exact.

**How I answer it**
1. **Single-key operations are atomic.** `put`, `putIfAbsent`, `computeIfAbsent`, `compute` and `merge` run as one step per key. The map uses bucket-level locking plus memory-visibility guarantees, so a value you write is visible to threads that read it afterwards.
2. **A sequence of calls is not atomic.** `containsKey` followed by `put`, or `get` followed by `put`, lets another thread interleave. Two threads can both see "absent", or both read 5 and write 6, losing an update. Replace the pair with one atomic call:
   `map.merge(key, 1, Integer::sum);`
3. **Keep the function inside `computeIfAbsent`, `compute` and `merge` short.** It runs while the bucket is locked, so slow work (a remote call, a DB query) blocks other writers to that bucket. In the scenario, load the value outside the lock, or cache a `CompletableFuture` as the value. Be aware that in Java 8 `computeIfAbsent` could lock even when the key already existed. Java 9 improved that, so name the version if asked.
4. **Never modify the same map from inside that function.** It can deadlock, loop forever, or throw `IllegalStateException` ("Recursive update", Java 9+).
5. **Treat `size()` as an estimate** while writers are active. Use `mappingCount()` for a `long`, and never base logic on the exact count.
6. **Remember what CHM does not protect.** Bulk operations like `putAll` are not one atomic unit. The objects stored as values are not made thread-safe, so a mutable value still needs its own protection. Null keys and values are not allowed.

**Trade-offs and what can go wrong**
- Using `computeIfAbsent` fixes duplicates but can create lock contention if the loader is slow.
- A cached future avoids blocking, but you must remove failed futures so errors are not cached forever.
- Using a synchronized block around CHM calls throws away its concurrency benefit.
- Code that relies on `size()` or iteration being a snapshot will behave unpredictably.
- Mutating a value object after storing it is a data race that CHM cannot prevent.

**How I'd monitor it**
- Compare p99 latency of the cache-using endpoint before and after a change.
- Take thread dumps and look for many threads BLOCKED in `ConcurrentHashMap.computeIfAbsent`.
- Count loader calls per key (for example, a log line "loading rate for X"). In Splunk, search it and chart `count by key`. More than one load per key per TTL means a race.
- Track cache hit and miss counters, and use JFR (Java Flight Recorder) lock-contention events.

**Follow-ups to expect**
- *Why not `Collections.synchronizedMap`?* -> It uses one lock for the whole map, so readers and writers queue up, and iteration still needs manual locking.
- *Is `get` blocking?* -> No, reads normally take no lock. A value written before is visible due to happens-before ordering.
- *How do you count safely?* -> `merge(key, 1, Integer::sum)`, or `LongAdder` values for very hot keys.

**60-second answer**
Each single-key call on ConcurrentHashMap, like `put`, `putIfAbsent`, `computeIfAbsent` or `merge`, is atomic. A sequence of calls is not. `containsKey` then `put` is a race, so I use `putIfAbsent` or `merge`, which do the check and write as one step. The function passed to `computeIfAbsent` runs while the bucket is locked, so I keep it fast, never call a remote service in it, and never modify the same map from inside it. `size()` is only an estimate while other threads are writing, and iterators are weakly consistent. The values stored in the map are not made thread-safe either. To verify, I watch p99 latency, look for BLOCKED threads in thread dumps, and check logs for duplicate loads per key.

### Q44 [senior] What is ForkJoinPool and work stealing?
tags: forkjoinpool, work-stealing, recursivetask, parallel-streams, common-pool, concurrency, basics

**Start here: the concepts**
- **Thread pool:** a fixed set of reusable worker threads that run submitted tasks. It exists because creating a thread per task is slow and uncontrolled.
- **Divide and conquer:** split a big job into smaller independent pieces, solve them, then combine the results. Summing a million numbers is an example: split the array in half repeatedly, then add the partial sums.
- **ForkJoinPool:** a thread pool (Java 7+) built for divide and conquer. A task *forks* (submits) its subtasks, then *joins* (waits for) their results. `RecursiveTask<V>` returns a value and `RecursiveAction` does not.
- **Deque:** a double-ended queue, which can be added to or removed from at both ends. Each worker has its own deque of tasks, so workers rarely compete for one shared queue.
- **Work stealing:** a worker that runs out of tasks takes one from the *other end* of a busy worker's deque. The owner takes its newest task from its own end. A thief takes the oldest task, which is usually the biggest piece, so one steal gives it a lot of work. Splits are uneven in practice, so without stealing some cores would sit idle while others are overloaded.
- **Common pool:** a shared `ForkJoinPool` for the whole JVM (Java 8+). Parallel streams use it, and so do `CompletableFuture.supplyAsync` calls without an executor. Its default size is about CPU cores minus one.

**The live scenario**
An order service runs on 8 cores. A developer wrote `list.parallelStream().map(this::callPricingApi)` to "speed up" a 50-item loop. The common pool has about 7 workers, and each call blocks for roughly 300 ms on the network. Under 40 requests per second, all 7 workers were stuck waiting on HTTP. Other code using `CompletableFuture.supplyAsync` queued behind them. p99 latency went from 120 ms to about 6 s, while CPU stayed near 10%. The cause was blocking inside a pool built for CPU-bound work.

**What the interviewer is really checking**
Whether you understand the mechanism (per-worker deques, stealing from the opposite end) and its consequence: the pool is shared and sized for CPU work, so blocking in it harms unrelated code.

**How I answer it**
1. **Say what it is.** It is a pool for divide-and-conquer work. I describe fork and join, since that is the model it is designed around.
2. **Explain the structure.** Each worker has its own deque, which avoids contention on a single shared queue. Owners work LIFO on their own end, which is cache-friendly and runs the freshest subtasks first.
3. **Explain stealing.** An idle worker takes from the opposite (oldest) end. Old tasks are the largest, so one steal buys a lot of work, and owner and thief rarely touch the same spot.
4. **Connect it to real code.** Parallel streams and default async `CompletableFuture` calls run on the common pool, which is shared by the whole JVM.
5. **State the rule.** Don't block in it, because there are only about cores−1 workers and blocked ones can't steal or run anything. Use a dedicated executor for I/O instead, or virtual threads on Java 21.
6. **Keep subtasks meaningful.** Split until a piece is small enough to compute directly, not down to single elements.

```java
protected Long compute() { if (small) return direct(); left.fork(); return right.compute() + left.join(); }
```

**Trade-offs and what can go wrong**
- Splitting and forking have overhead, so small or cheap jobs run slower in parallel than sequentially.
- Blocking calls (I/O, locks, `Thread.sleep`) starve the shared common pool. `ManagedBlocker` can add compensating threads, but it is not a fix for ordinary blocking code.
- Tasks must be independent. Shared mutable state in a parallel stream causes bugs.
- A slow parallel stream in one feature slows every other user of the common pool.
- Stealing balances load only if there are enough tasks. Too few big chunks leaves cores idle.

**How I'd monitor it**
- Poll `ForkJoinPool.commonPool()` for `getActiveThreadCount()`, `getQueuedTaskCount()`, `getStealCount()` and `getPoolSize()`, and export them through Micrometer.
- Alert when active threads equal parallelism and the queue keeps growing, while CPU stays low.
- Take thread dumps and look for many `ForkJoinPool.commonPool-worker-N` threads in `WAITING` or `TIMED_WAITING` states.
- Search Splunk for logs by thread name containing `commonPool-worker` and compare their durations.

**Follow-ups to expect**
- *How is it different from ThreadPoolExecutor?* -> A ThreadPoolExecutor usually has one shared queue and suits independent tasks. A ForkJoinPool has a deque per worker plus stealing, and suits tasks that spawn subtasks.
- *How do I stop a parallel stream using the common pool?* -> Prefer a dedicated executor with `CompletableFuture`. Running the stream inside your own `ForkJoinPool.submit(...)` works in practice but is not a documented guarantee.
- *How do I change the common pool size?* -> Set `-Djava.util.concurrent.ForkJoinPool.common.parallelism=N`. The default is cores minus one.

**60-second answer**
ForkJoinPool is a thread pool made for divide-and-conquer work, where a task splits itself into subtasks, forks them, and joins the results. Each worker has its own deque of tasks. When a worker runs out, it steals the oldest, usually largest, task from another worker's deque. That keeps all cores busy even when the splits are uneven. Parallel streams and default `CompletableFuture` async calls run on the shared common pool, which has only about cores minus one threads. So I never block in it. I once saw a parallel stream making HTTP calls freeze a service for seconds with CPU nearly idle. I would use a dedicated executor for I/O and watch the common pool's active threads and queue size.

### Q45 [senior] ThreadLocal: use, danger and the alternative?
tags: threadlocal, concurrency, virtual-threads, scopedvalue, mdc, thread-pools, basics

**Start here: the concepts**
- **Thread:** one independent line of execution in your program. A web server handles many requests at once by running each on a thread.
- **ThreadLocal:** a variable where each thread sees its own private value. `set()` stores a value for the current thread, and `get()` reads it back. It exists so you can carry per-request data (logged-in user, trace id) through many method calls without adding a parameter to each one.
- **Thread pool:** a fixed set of threads that are reused for many tasks, because creating threads is expensive. Reuse is what makes ThreadLocal risky, since the thread outlives the request.
- **MDC (Mapped Diagnostic Context):** a logging feature (SLF4J/Logback) that adds fields such as `traceId` to every log line. It is built on ThreadLocal.
- **Virtual thread (Java 21):** a very cheap thread managed by the JVM, not the operating system. You can run millions of them, and the intent is one per task, never pooled.
- **ScopedValue:** a replacement for ThreadLocal where a value is bound only for a bounded block of code and is read-only inside it. It was a preview feature in Java 21 to 24 and became final in Java 25.

**The live scenario**
An order API runs on a pool of 200 threads at about 2,000 requests per second. A filter stores the tenant id in a ThreadLocal and clears it only on the success path. Under load, an exception skips the cleanup. The next request on that pooled thread starts with the previous request's tenant id, and one customer briefly sees another customer's data. Logs show the wrong `tenantId` in MDC too. Later the team moves to virtual threads. They now see 500,000 concurrent threads, each holding a 20 KB cached object in a ThreadLocal, so memory grows by about 10 GB.

**What the interviewer is really checking**
Whether you know that ThreadLocal state lives as long as the thread, not as long as the request, and whether you know the modern alternatives and their limits.

**How I answer it**
1. **Say what it is for.** ThreadLocal gives each thread its own copy, so per-request context (user, tenant, MDC) can travel through the call stack without being passed as a parameter.
2. **Name the main danger: leaks in pooled threads.** The value is tied to the thread. A pool reuses threads, so a value you forget to clear is seen by the next request. This is both a correctness bug (wrong user's data) and a memory leak.
3. **Always clean up in `finally`.** The `finally` block runs even when an exception is thrown, so cleanup is guaranteed:
```java
try { CTX.set(user); chain.doFilter(req, res); }
finally { CTX.remove(); }
```
4. **Mention the other danger: context is lost across async hops.** A new thread does not see the parent's values (`CompletableFuture`, executors, `@Async`). `InheritableThreadLocal` copies values only when a thread is created, which does not help with reused pool threads. You must copy the context explicitly, for example with MDC-aware task wrappers.
5. **Explain virtual threads accurately.** ThreadLocal still works. Virtual threads are not pooled, so cross-request leakage is mostly gone. But with millions of threads, each holding its own copy, memory multiplies. Per-thread caches of expensive objects (such as a `SimpleDateFormat`) stop making sense.
6. **Offer the alternatives.** The simplest is to pass context explicitly as a method parameter or a request object. It is verbose but clear and testable. The newer option is `ScopedValue` (final in Java 25; preview in 21 to 24). You bind a value for a block with `ScopedValue.where(USER, u).run(...)`. It is immutable, it disappears automatically when the block ends, so there is nothing to clean up, and it is designed to be inherited by child tasks in structured concurrency.

**Trade-offs and what can go wrong**
- ThreadLocal is hidden state. It makes code harder to test and reason about.
- Forgetting `remove()` causes leaks and cross-request data exposure. In app servers it can also leak classloaders on redeploy.
- `ScopedValue` cannot be changed after binding, so code that mutates the context needs a redesign. Before Java 25 it needs `--enable-preview`, and you cannot use it on older LTS versions.
- Explicit parameters add boilerplate, but they are the safest choice.

**How I'd monitor it**
- Heap growth and GC pressure, plus a heap dump to look for `ThreadLocalMap` entries retaining large objects.
- Splunk searches for log lines where `tenantId` or `userId` in MDC differs from the request's own value, or is present on a thread that should have none.
- A test that runs two requests back to back on a one-thread pool and asserts the context is empty.
- Thread counts and memory per thread when you adopt virtual threads.

**Follow-ups to expect**
- *Why does MDC lose the trace id in `CompletableFuture`?* -> MDC is a ThreadLocal, and the async task runs on another pool thread. Capture the context map before submitting and restore it inside the task, then clear it.
- *Does InheritableThreadLocal fix this?* -> No. It copies only when a thread is created, so reused pool threads keep stale or missing values.
- *Why prefer ScopedValue over ThreadLocal?* -> It has a bounded lifetime, is immutable, needs no manual cleanup, and is cheaper with many virtual threads.

**60-second answer**
ThreadLocal gives each thread its own copy of a variable. We use it for per-request context such as the user, the tenant, or logging MDC. The danger is that the value lives as long as the thread, and pooled threads are reused. A value that is not cleared leaks into the next request, which can show one customer another customer's data. So I always call `remove()` in a `finally` block. Values also do not follow work onto other threads in async code, so I copy context explicitly. With virtual threads, leakage is less of a problem because they are not pooled, but millions of threads each holding a copy can use a lot of memory. The alternatives are passing context explicitly, or `ScopedValue`, which is final in Java 25. It binds an immutable value for one block of code and cleans up automatically.

### Q46 [senior] Explain `@Async` and `@Scheduled` pitfalls in Spring.
tags: java, spring, async, scheduled, thread-pool, shedlock, basics

**Start here: the concepts**
- **Proxy**: Spring wraps your bean in a stand-in object. Callers get the stand-in, which adds behaviour (run in another thread, start a transaction) and then calls your real method. `@Async` is implemented this way.
- **Self-invocation**: a method calling another method in the same class uses `this`, the real object, and skips the proxy. The annotation is then silently ignored.
- **`@Async`**: a method annotated with it is handed to a thread pool (an *executor*) instead of running on the caller's thread. It needs `@EnableAsync`.
- **Executor / thread pool**: a set of reusable worker threads with a queue of waiting tasks. *Bounded* means limits on thread count and queue size, so a flood of work cannot use unlimited memory or threads.
- **`SimpleAsyncTaskExecutor`**: starts a brand-new thread for every task and never reuses it. It is fine for a demo and dangerous under load.
- **`@Scheduled`**: runs a method on a timer (`fixedRate`, `fixedDelay`, `cron`). It needs `@EnableScheduling`. The method takes no arguments.
- **Scheduler thread pool**: by default it has one thread, so scheduled jobs run one after another.
- **Distributed lock (ShedLock)**: a shared record, usually in a DB row or Redis key, that lets only one instance run a job at a time. **Quartz cluster** and **leader election** achieve the same goal.

**The live scenario**
An order service runs 6 pods. A `@Scheduled` job emails invoices every hour. After the move from 1 pod to 6, customers got 6 emails each. Separately, a `@Async` notification method was called from another method in the same class, so it ran on the request thread and added about 800 ms to each call. After that was "fixed", a traffic spike queued 200,000 tasks and the pods ran out of memory. Three pitfalls, one incident week.

**What the interviewer is really checking**
Whether you understand how Spring really executes these annotations (proxy, thread pool, one process per pod) and not just that they exist. Seniors are expected to think about failure and scale-out.

**How I answer it**
1. **`@Async` works only through the proxy.** Calling it from the same class, or on a `private` or `final` method, does nothing. Move the method to another bean, or inject the bean. The reason is that self-invocation never touches the proxy.
2. **Define the executor yourself.** In plain Spring with no executor bean, `@Async` falls back to `SimpleAsyncTaskExecutor`, a new thread per call. Spring Boot (2.1 onward) auto-configures a `ThreadPoolTaskExecutor` instead, but with a default queue that is effectively unbounded, so memory still grows under a flood. Define a `ThreadPoolTaskExecutor` with explicit core size, max size and queue capacity, and name it with `@Async("name")`.
3. **Choose a rejection policy.** When a bounded pool is full, the default throws `TaskRejectedException`. `CallerRunsPolicy` makes the caller do the work, which slows producers down (back-pressure).
4. **Handle errors and context.** A `void` `@Async` method loses its exceptions unless you register an `AsyncUncaughtExceptionHandler`. Return `CompletableFuture` if the caller needs the result or error. Security context, MDC log fields and transactions do not follow the task to the new thread, so copy them (for example with a `TaskDecorator`).
5. **`@Scheduled` is single-threaded by default.** One slow job delays every other job. Raise `spring.task.scheduling.pool.size`, or give long jobs their own scheduler.
6. **Every pod runs the job.** Spring has no idea other instances exist. Use ShedLock, a Quartz JDBC cluster, or leader election so it runs once:

```java
@Scheduled(cron = "0 0 * * * *")
@SchedulerLock(name = "invoiceJob", lockAtMostFor = "PT10M", lockAtLeastFor = "PT1M")
```

`lockAtMostFor` frees the lock if a pod dies mid-job. `lockAtLeastFor` protects against small clock differences between pods.

**Trade-offs and what can go wrong**
- Small pool plus small queue means tasks are rejected. Large pool means CPU and DB connection pressure.
- `@Async` tasks are lost if the pod stops, since they live only in memory. For critical work use a durable queue such as Kafka.
- `lockAtMostFor` set shorter than the job's runtime lets a second pod start the job while the first is still running.
- `fixedRate` on a single thread piles up late runs. `fixedDelay` waits for the previous run to finish.
- ShedLock adds a dependency on its store. Jobs should be idempotent anyway.

**How I'd monitor it**
- Micrometer executor metrics: `executor.active`, `executor.queued`, `executor.pool.size`, `executor.completed`. Alert when the queue stays near capacity.
- Count `TaskRejectedException` in Splunk, and log each job's start and end with pod name and duration. Search for the same job name starting from two pods within the same minute.
- Thread dumps showing hundreds of `SimpleAsyncTaskExecutor-*` threads.
- JVM heap and thread count graphs.

**Follow-ups to expect**
- *Why did my `@Async` method still run synchronously?* -> Most likely self-invocation, or a missing `@EnableAsync`, or a non-public method. The proxy was bypassed.
- *`fixedRate` vs `fixedDelay`?* -> `fixedRate` measures start to start; `fixedDelay` measures end of one run to start of the next.
- *Is there an alternative to ShedLock?* -> Quartz in JDBC cluster mode, a Kubernetes CronJob (one run per schedule), or leader election.

**60-second answer**
`@Async` works through a Spring proxy, so calling it from the same class does nothing and it must be called from another bean. Without a configured executor, plain Spring spawns a new thread per call, and Boot's default pool has an unbounded queue, so I define a bounded `ThreadPoolTaskExecutor` with a rejection policy. I also handle exceptions from `void` methods and copy security and logging context across threads. `@Scheduled` uses one thread by default, so a slow job blocks the others and I size the scheduler pool. In a multi-pod deployment every pod runs the job, so I use ShedLock, Quartz cluster or leader election to run it once, and I make the job idempotent. I watch queue size, rejections and duplicate job starts in the logs.

### Q47 [senior] How do you make a check-then-act operation safe across multiple pods?
tags: java, concurrency, distributed-systems, optimistic-locking, idempotency, kafka, basics

**Start here: the concepts**
- **Check-then-act:** you read a state ("is this coupon unused?") and then act on it ("mark it used"). Between the two steps another request can change the state, so both requests may pass the check. This is a *race condition*.
- **JVM lock (`synchronized`, `ReentrantLock`):** it only coordinates threads inside one process. Each pod is a separate JVM with its own memory, so these locks cannot stop two pods from acting together.
- **Database constraint:** a rule the database enforces itself (for example, `UNIQUE`). The database is the one shared referee all pods already talk to.
- **Optimistic lock (`@Version`):** assume conflicts are rare. Each row has a version number, and an update says "change this row only if the version is still 5". If another pod changed it first, zero rows match and you retry or fail.
- **Pessimistic lock (`SELECT ... FOR UPDATE`):** lock the row when you read it, so others wait until your transaction ends.
- **Redis lease (`SET key value NX PX ttl`):** `NX` means "set only if absent", so only one pod gets it. `PX` is an expiry in milliseconds, so a crashed pod cannot hold it forever.
- **Fencing token:** an increasing number issued with each lock. The protected resource rejects any request carrying an older number.
- **Kafka partition key:** messages with the same key go to the same partition. Within a consumer group, one consumer reads a partition at a time, so work for one key is processed one message at a time.
- **Idempotency key:** a unique ID sent with a request. If the same ID arrives twice, the second call returns the first result without repeating the work.

**The live scenario**
A flash sale runs on 6 pods at about 300 requests/s. Each coupon may be redeemed once. The code did `if (!coupon.isUsed()) { coupon.markUsed(); applyDiscount(); }` inside a `synchronized` method. It passed all tests on one pod. In production, 40 coupons were redeemed twice in 10 minutes, because two pods each saw "unused" at the same moment. Finance noticed the loss.

**What the interviewer is really checking**
Do you know that in-process locks stop at the JVM boundary? Can you pick the right shared coordination point (DB, Redis, Kafka) for the situation, and do you know that retries make idempotency necessary?

**How I answer it**
1. **Name the problem.** `synchronized` protects one JVM only, so I need a coordinator all pods share.
2. **Prefer the database first.** It already holds the data, so make the check and the act one atomic statement:
   ```sql
   UPDATE coupon SET used = true WHERE id = ? AND used = false
   ```
   If rows affected is 1, I won. If 0, someone else did. A `UNIQUE` constraint works the same way, because the second insert fails.
3. **Use `@Version` when conflicts are rare.** There are no held locks and it scales well. On `OptimisticLockException` I retry or reject.
4. **Use `SELECT ... FOR UPDATE` when conflicts are frequent.** Waiting is cheaper than retry storms. I keep the transaction short so locks are held briefly.
5. **Use a Redis lease only when the DB can't decide,** for example when guarding an external call. I store a unique value and release only if it still matches. The lease can expire during a long GC pause while the old holder keeps working, so I add a fencing token or a DB check as a backstop.
6. **Serialize by key in Kafka when the work is event-driven.** Use the coupon ID as the message key. Rebalancing can briefly overlap two consumers, so I still keep a DB guard.
7. **Always add idempotency keys.** Clients, gateways and Kafka redeliver messages. With a stored key, a retry returns the earlier result instead of redeeming twice.

**Trade-offs and what can go wrong**
- Optimistic locking under heavy contention causes retry storms.
- Pessimistic locking can cause lock waits and deadlocks, and long transactions make both worse.
- A Redis lease without fencing is not safe. TTL too short means the lock expires mid-work. TTL too long means slow recovery after a crash.
- Kafka key ordering limits parallelism, and a hot key creates a hot partition.
- Idempotency records need a retention period, and the key check must itself be atomic (unique index).

**How I'd monitor it**
- Count unique-constraint violations and optimistic-lock failures per minute. A sudden rise means contention.
- Track DB lock wait time and deadlock count.
- In Splunk, search for repeated idempotency keys ("duplicate request ignored") and for retries per request ID.
- Watch Kafka consumer lag and rebalance counts.
- Run a reconciliation query for duplicates (`GROUP BY coupon_id HAVING COUNT(*) > 1`) and alert if it returns anything.

**Follow-ups to expect**
- *Why not sticky sessions plus `synchronized`?* -> Pods restart, scale and rebalance, so two pods can still touch the same data. It only hides the bug.
- *Optimistic or pessimistic?* -> Optimistic when conflicts are rare, pessimistic when they are common and retries would be costly.
- *Is a Redis lock enough for correctness?* -> Not alone. Leases expire, so protect the final write with a fencing token or a DB condition.

**60-second answer**
A JVM lock only works inside one pod, so across pods I need a shared coordinator. My first choice is the database. I make the check and the update one atomic statement, or rely on a unique constraint or `@Version`, because the DB already holds the truth. If conflicts are frequent I use `SELECT ... FOR UPDATE` with short transactions. For event flows I key Kafka messages so one key is handled by one consumer at a time. A Redis `SET NX PX` lease is a last resort, and I add a fencing token because leases can expire mid-work. On top of all of this I use idempotency keys, so a retry never repeats the action. I watch constraint violations, lock waits and duplicate-request logs to prove it works.

### Q48 [mid] A service's CPU is at 100%. How do you find the busy thread?
tags: java, performance, cpu, jstack, thread-dump, profiling, basics

**Start here: the concepts**
- **Thread**: a worker inside your Java process. One process runs many threads, and each can use a CPU core at the same time.
- **Native thread id (TID)**: the number the operating system gives each thread. Linux tools such as `top` show it in decimal. A Java thread is a thin wrapper over one OS thread.
- **Thread dump**: a text snapshot of every JVM thread, with its name, state and stack trace (the chain of method calls it is in). `jstack <pid>` or `jcmd <pid> Thread.print` produces one.
- **`nid`**: the OS thread id as it appears in a thread dump, written in hexadecimal (e.g. `nid=0x1f4b`). It links what the OS sees to what Java sees.
- **Profiler / JFR / flame graph**: a profiler samples stacks many times per second and counts where time goes. JFR (Java Flight Recorder) is built into the JVM. async-profiler is a separate open-source tool. A flame graph draws the result, with wider boxes meaning more CPU.
- **GC thrash**: the garbage collector (which frees unused memory) runs almost continuously because the heap is nearly full, so it eats the CPU.
- **Regex backtracking**: some regex patterns try an exponential number of ways to match certain input and spin for seconds or minutes.

**The live scenario**
An order service normally runs at 25% CPU. After a release, an alert fires: 8 cores at about 100%, p99 latency up from 120 ms to 6 s, and the load balancer is timing out about 15% of requests. Restarting helps for 20 minutes, then it returns. The team needs to find which code is burning CPU, not just add more pods.

**What the interviewer is really checking**
Whether you have a repeatable method for going from "the process is hot" to "this line of code is hot", and whether you know that the cause is not always application code.

**How I answer it**
1. **Confirm which process.** Run `top` and note the PID. *Reason:* you must be sure it is the JVM and not something else on the box.
2. **Find the hot thread.** Run `top -H -p <pid>`. The `-H` flag lists threads instead of the process total. *Reason:* the process figure hides which worker is responsible. Note the TID of the top one or two threads.
3. **Convert the TID to hex.** `printf '%x\n' <tid>`. *Reason:* `top` shows decimal, but thread dumps show hex.
4. **Take thread dumps.** Run `jcmd <pid> Thread.print > t1.txt`, wait a few seconds, and repeat 2-3 times. Search for `nid=0x<hex>`. *Reason:* one dump is a single instant. If the same thread is in the same method across dumps, that is your hot spot.
5. **Read the stack and name the cause.** Typical causes:
   - an infinite or very long loop;
   - regex backtracking;
   - threads spinning on a lock or retry loop (a blocked thread uses no CPU, but a thread that keeps retrying does);
   - GC thrash.
6. **Check GC if the thread name is a GC worker.** If the busy thread is named like "GC Thread#3", the problem is memory pressure. Look at the GC logs, not at application code.
7. **If dumps are not conclusive, profile.** Use async-profiler or JFR for 30-60 seconds and read the flame graph. *Reason:* sampling many times shows where CPU goes over time, which is better than guessing from a few snapshots.

```bash
top -H -p 4321          # hot TID, e.g. 4455
printf '%x\n' 4455      # 1167
jcmd 4321 Thread.print | grep -A 20 'nid=0x1167'
```

**Trade-offs and what can go wrong**
- A thread dump pauses the JVM briefly. This is usually fine but not free on very large heaps.
- A single dump can mislead, so take several.
- A thread id can be reused or a thread can end before you look it up, so convert and search quickly.
- JIT compiler threads (the JVM compiling hot code) can be briefly hot after a deploy. That is normal, not a bug.
- Some profilers only sample at safepoints (points where the JVM can pause threads), which can skew results. async-profiler avoids much of that bias.
- In containers, check that you are inspecting the right PID and that CPU limits are not simply throttling you.

**How I'd monitor it**
- CPU per process and per thread, with alerts on sustained CPU above a threshold.
- GC logs and GC pause or time-percentage metrics.
- Thread count and thread states from JMX or Micrometer.
- Splunk searches for slow-request logs or timeouts that start at the same time as the CPU rise.
- Regular JFR recordings, so you can compare a "good" baseline with the incident.

**Follow-ups to expect**
- *Why convert the thread id to hex?* -> `top` prints decimal, but jstack's `nid` is hexadecimal, so they only match after conversion.
- *What if the busy thread is a GC thread?* -> The cause is memory pressure. Check GC logs, heap size, allocation rate and possible leaks.
- *Why prefer async-profiler or JFR over thread dumps?* -> They sample continuously and show where time accumulates, and they have lower overhead and less bias than a few snapshots.

**60-second answer**
First I run `top -H -p <pid>` to see which individual thread is using the CPU, because the process total hides that. I convert that thread's decimal id to hex and search for `nid=0x...` in a thread dump from `jstack` or `jcmd Thread.print`. I take a few dumps a few seconds apart to confirm it is stuck in the same method. If that is not enough, I run async-profiler or JFR and read the flame graph. The usual causes are infinite loops, regex backtracking, spinning on locks or retries, and GC thrash. If the busy thread is a GC thread, I move to the GC logs and look at memory instead of code.

### Q49 [senior] Explain false sharing and `LongAdder`.
tags: java, concurrency, false-sharing, longadder, atomiclong, cpu-cache, performance, basics

**Start here: the concepts**
- **CPU cache:** Reading main memory is slow, so each core keeps a small, fast copy of recently used data close by.
- **Cache line:** The cache does not copy single variables. It copies fixed blocks, typically 64 bytes on common x86 CPUs. Variables that sit next to each other in memory share a line.
- **Cache coherence:** If one core writes to a line, other cores' copies of that line become invalid. They must reload it before using it. This keeps the cores consistent but costs time.
- **False sharing:** Thread A writes variable X and thread B writes variable Y. The two are logically independent, but they sit on the same cache line. Each write invalidates the other core's copy, so the line bounces between cores. The code is correct but slow, and nothing in it looks wrong.
- **CAS (compare-and-set):** `AtomicLong` increments by reading the value and trying to swap in value+1 only if nobody changed it meanwhile. If someone did, it retries.
- **Contention:** Many threads fighting over one variable. Under heavy contention, many CAS attempts fail and retry, which wastes CPU. This is true sharing, a different problem from false sharing.
- **`LongAdder` (Java 8, `java.util.concurrent.atomic`):** A counter made of a base value plus an array of cells. When threads collide, they spread out and update different cells. `sum()` adds the base and all cells.

**The live scenario**
A metrics service on a 32-core machine counts requests with one shared `AtomicLong`. At about 200k requests/sec, CPU sits near 90% but throughput stops growing. Profiling shows the time goes into the counter's increment. Every core is fighting over one memory location. The team swaps in `LongAdder` (illustrative result: p99 latency falls from 40 ms to 12 ms). Earlier, the same team had a `long[]` of per-thread counters that was also slow. Neighbouring array slots shared a cache line, which was false sharing.

**What the interviewer is really checking**
Whether you understand the hardware cause (cache lines) and can separate false sharing from true contention. They also want to know whether you know what `LongAdder` gives up in exchange for speed.

**How I answer it**
1. **Define false sharing first.** Two threads write different variables on the same cache line. Each write invalidates the other core's copy, so the line ping-pongs. The reason it is hard to spot is that no lock or shared variable shows up in the code.
2. **Separate it from contention.** A single hot `AtomicLong` is true sharing. Every thread really wants the same variable, and CAS retries pile up. Padding cannot fix this. You must reduce how many threads touch the same location.
3. **Explain `LongAdder`.** Under low contention it updates its base value like an `AtomicLong`. When CAS fails, threads are directed to different cells. Each thread mostly updates its own cell, so the retries disappear.
4. **Mention the false-sharing guard inside it.** The cells are padded (the JDK uses an internal `@Contended` annotation) so that two cells do not share a cache line. Otherwise splitting the counter would just move the problem.
5. **State the read behaviour.** `sum()` adds up the base and all cells while updates may still be running. It is not an atomic snapshot. It can miss increments that land during the read, and `sumThenReset()` is also not atomic.
6. **Say when to use it.** Use it for statistics: counters, metrics, hit counts, where writes are frequent and reads are rare. Do not use it for sequence numbers or limits, where you need an exact value now or compare-and-set.

```java
LongAdder hits = new LongAdder();
hits.increment();            // hot path, many threads
long approx = hits.sum();    // read, not a snapshot
```

**Trade-offs and what can go wrong**
- Uses more memory than `AtomicLong` because of the cells and padding.
- `sum()` may be slightly stale under concurrent writes. This is fine for dashboards but wrong for "stop at exactly 1000".
- At low contention there is no gain. Do not replace every `AtomicLong` blindly.
- Hand-padding fields to avoid false sharing is fragile. Object layout depends on the JVM, and the user-level `@Contended` needs `-XX:-RestrictContended`.
- Common mistake: blaming false sharing for what is actually single-variable contention, and the reverse.

**How I'd monitor it**
- Benchmark with JMH at realistic thread counts before and after the change.
- Use async-profiler or a similar profiler to look for time in the atomic increment. A high CPU with flat throughput is the symptom.
- On Linux, `perf` cache-miss counters can show cache-line bouncing.
- Compare throughput and CPU in your metrics before and after rollout.

**Follow-ups to expect**
- *Why is `LongAdder` faster than `AtomicLong`?* -> It spreads updates over several cells, so threads rarely fight over one location, and fewer CAS retries happen.
- *Why is `sum()` not a snapshot?* -> It reads the cells one by one while other threads keep updating, so the result is a close value, not a single moment in time.
- *How do you fix false sharing in your own code?* -> Keep hot fields written by different threads on separate cache lines, using padding or `@Contended`, or restructure the data so each thread owns its own object. Measure first.

**60-second answer**
Memory is cached in cache lines, typically 64 bytes. False sharing happens when two threads write different variables that sit on the same line. The cores keep invalidating each other's copy, so the code is correct but slow. That is different from contention on one shared variable, which is what a hot `AtomicLong` suffers from, with CAS retries piling up. `LongAdder` fixes that by splitting the counter into a base plus padded cells, so threads update different cells, and `sum()` adds them up. It is much faster under heavy write contention, but `sum()` is not an atomic snapshot. So I use it for metrics and counters, not for exact limits or sequence numbers, and I confirm the gain with a JMH benchmark.

### Q50 [mid] What major features arrived in Java 8?
tags: java8, lambdas, streams, optional, completablefuture, basics

**Start here: the concepts**
- **Lambda expression**: a short, unnamed block of code you can pass around like a value, e.g. `x -> x * 2`. It exists to remove the bulky anonymous inner classes Java needed to pass behaviour before.
- **Functional interface**: an interface with exactly one abstract method (e.g. `Runnable`, `Comparator`, `Function`). A lambda is the implementation of that one method. `java.util.function` ships ready-made ones such as `Predicate`, `Function`, `Consumer` and `Supplier`.
- **Method reference**: a shorthand for a lambda that only calls an existing method, e.g. `String::toUpperCase`. It is easier to read when no extra logic is needed.
- **Stream API**: a pipeline for processing a collection step by step (filter, map, collect) without writing the loop yourself. It is lazy: nothing runs until a final operation such as `collect` is called. It does not modify the source collection.
- **Default and static interface methods**: interfaces can now contain method bodies. Default methods let library authors add methods (like `Collection.stream()`) without breaking every existing implementer. Static methods hold helpers next to the interface.
- **Optional**: a container that holds a value or nothing. It makes "might be absent" visible in a method's return type instead of hiding it behind `null`.
- **java.time**: a new date/time API (`LocalDate`, `Instant`, `Duration`, `ZonedDateTime`). Its objects are immutable, so they are safe to share between threads.
- **CompletableFuture**: a handle to a result that will arrive later. You can chain steps ("when done, then do this") and combine several async calls without blocking.

**The live scenario**
An order service handled about 300 requests/sec. A shared `SimpleDateFormat` was used to parse dates. It is not thread-safe, so under load roughly 1 in 2,000 orders got a wrong date. The team replaced it with `java.time.DateTimeFormatter`, which is immutable, and the bug disappeared. In the same refactor, 40-line loops that filtered and grouped orders became 5-line stream pipelines, and three sequential REST calls (about 300 ms each) became parallel `CompletableFuture`s, cutting the wait to about 300 ms in total.

**What the interviewer is really checking**
Whether you know what each feature is for and when it goes wrong, not just the list. At mid level they expect you to mention the pitfalls (Optional misuse, parallel streams, the default thread pool).

**How I answer it**
1. **Say the theme first**: Java 8 (released 2014) made Java more functional and less verbose. The reason is that the language needed a way to pass behaviour around and process data declaratively.
2. **Lambdas, functional interfaces, method references**: lambdas work because the target type is a one-method interface. Method references are the shorter form when the lambda only calls a method.
3. **Streams**: they describe what to do, not how to loop. Intermediate steps are lazy and only run when a final operation is called.
4. **Default/static interface methods**: these let the JDK add `stream()` and `forEach` to old interfaces without breaking existing code.
5. **Optional**: use it as a return type to signal "may be empty". Don't use it for fields or method parameters, and don't call `get()` without checking.
6. **java.time**: it replaces `Date`/`Calendar`/`SimpleDateFormat`, which are mutable and error-prone.
7. **CompletableFuture**: it runs async tasks and chains them. By default it uses the shared `ForkJoinPool.commonPool()`.

```java
orders.stream().filter(o -> o.total() > 100).map(Order::id).collect(Collectors.toList());
```

**Trade-offs and what can go wrong**
- Streams can be harder to debug than loops, and a long pipeline is not automatically faster.
- `parallelStream()` and default `CompletableFuture` both use the common pool. Blocking I/O there can starve other work. Pass your own `Executor` for I/O.
- Lambdas should not change shared state. It is unsafe in parallel code.
- `Optional.get()` on an empty value throws an exception, so it only moves the null problem.
- Streams cannot be reused after a final operation.

**How I'd monitor it**
- Thread dumps and metrics on the common pool, such as active threads and queue size.
- Latency percentiles (p95/p99) before and after introducing async or parallel code.
- Splunk search for `NoSuchElementException` or `NullPointerException` near Optional or stream code.
- Code review checks for blocking calls inside parallel streams.

**Follow-ups to expect**
- *Why can a lambda only target a functional interface?* -> The compiler needs exactly one abstract method to know which method the lambda implements.
- *What is the difference between an intermediate and a terminal operation?* -> Intermediate ones (`filter`, `map`) are lazy and return a stream. A terminal one (`collect`, `count`) triggers the work.
- *Why is `SimpleDateFormat` risky?* -> It keeps internal mutable state, so sharing it between threads corrupts results. `java.time` classes are immutable.

**60-second answer**
Java 8 was about making code more functional and concise. The main features are lambdas, which are short inline code blocks, and functional interfaces, which are the one-method interfaces they implement. Method references are a shorthand for lambdas that just call a method. The Stream API processes collections in lazy pipelines, and default and static interface methods let the JDK extend old interfaces without breaking them. `Optional` makes "no value" explicit in return types, `java.time` gives a thread-safe date/time API, and `CompletableFuture` chains async work. The main watch-outs are that parallel streams and default `CompletableFuture` share the common pool, and that `Optional` is best used only as a return type.

### Q51 [mid] What is a lambda expression?
tags: java8, lambda, functional-interface, invokedynamic, effectively-final, basics

**Start here: the concepts**
- **Interface:** a contract listing method names that a class promises to provide.
- **Functional interface:** an interface with exactly one abstract method, for example `Runnable` (`run()`), `Comparator` (`compare()`) or `Consumer` (`accept()`). It exists so Java can treat "one piece of behaviour" as something you can pass around.
- **Lambda expression:** a short way to write that single method's body without creating a named class. `name -> System.out.println(name)` means "given a `name`, print it". Java 8 added lambdas so code like sorting, filtering and looping over collections (streams) needs far less boilerplate.
- **Target type:** the compiler works out which functional interface the lambda implements from the context. In `forEach`, it expects a `Consumer<String>`.
- **Capture:** a lambda using a local variable from the surrounding method.
- **Effectively final:** a local variable that is never reassigned after it gets its value, even without the `final` keyword.
- **Anonymous inner class:** an unnamed class written inline with `new Interface() { ... }`. It was the pre-Java 8 way to pass behaviour.
- **`this`:** the current object. Its meaning inside a lambda differs from inside an anonymous class.

**The live scenario**
A team of 12 modernised a 200,000-line order service by mechanically converting anonymous inner classes into lambdas. One event-listener class registered itself with a message bus about 2,000 times an hour and unregistered with `bus.remove(this)`. After conversion, `this` no longer meant "the listener". It meant the enclosing service object, so `remove` found nothing and listeners were never removed. Heap usage climbed by a few hundred MB a day until the pods were restarted every night. The compiler gave no warning, because the code was valid. The lesson: lambdas are not just shorter anonymous classes.

**What the interviewer is really checking**
Whether you know a lambda is tied to a functional interface, and whether you understand its rules and differences (capture, `this`, runtime implementation) rather than just the arrow syntax.

**How I answer it**
1. **Define it:** a lambda is a concise implementation of a functional interface, meaning an interface with one abstract method. The compiler matches the lambda to that single method, so no class name or method name is needed.
2. **Show a small example:**
   ```java
   List<String> names = Arrays.asList("Asha", "Ravi", "Meera");
   names.forEach(name -> System.out.println(name));
   ```
   Here `forEach` expects a `Consumer<String>`, and the lambda supplies its `accept` method.
3. **State the capture rule:** a lambda can use a local variable from the enclosing method only if it is final or effectively final. The lambda may run later or on another thread, so it works with a copy of the value. Allowing reassignment would make the copy and the original disagree. Fields (instance and static) are not restricted this way, but changing them from lambdas, especially in parallel code, is risky.
4. **Explain the difference from anonymous classes:** an anonymous class is a real new class with its own `this`. In a lambda, `this` is the enclosing object, because a lambda does not introduce a new scope for `this`. At runtime the compiler does not generate a separate class file per lambda. It uses a mechanism called `invokedynamic` (Java 8), and the JVM creates the implementation when the lambda is first used. That is why they are not just different syntax.

**Trade-offs and what can go wrong**
- Mechanical conversion from anonymous classes can silently change the meaning of `this`, as in the scenario.
- Trying to modify a captured local variable (`count++`) gives a compile error. The workaround of an `AtomicInteger` or a one-element array is often a sign you should use a stream operation such as `count()` or `reduce` instead.
- Long, multi-line lambdas are hard to read and debug. Extract a named method and use a method reference instead.
- A lambda can only target an interface with one abstract method. It cannot replace an abstract class.

**How I'd monitor it**
- Compile errors and code review catch the capture rule.
- For `this` bugs, watch heap usage and GC logs for steady growth, then take a heap dump and look for objects that should have been removed, such as listeners.
- Search application logs in Splunk for "registered" versus "unregistered" counts to spot imbalance.
- Add tests that assert unregistering actually works before and after a refactor.

**Follow-ups to expect**
- *What is a functional interface?* -> An interface with exactly one abstract method. `@FunctionalInterface` makes the compiler enforce that, and default and static methods are still allowed.
- *What does effectively final mean?* -> A local variable that is never reassigned after initialisation, so the compiler treats it as if it were declared `final`.
- *What is a method reference?* -> A shorter form of a lambda that just calls an existing method, for example `System.out::println` instead of `name -> System.out.println(name)`.

**60-second answer**
A lambda is a short way to write the single method of a functional interface, which is an interface with one abstract method, like `Consumer` or `Comparator`. The compiler works out which interface it implements from the context, so I can write `names.forEach(name -> System.out.println(name))`. A lambda can only use local variables that are final or effectively final, meaning never reassigned, because it may run later with a copy of the value. It is not just an anonymous inner class with nicer syntax. Inside a lambda, `this` means the enclosing object, while in an anonymous class it means the anonymous object itself. Lambdas are also implemented differently at runtime, using `invokedynamic` instead of a separate class file. I have seen a refactor break listener removal because of that `this` change, so I convert carefully and test.

### Q52 [mid] What is the difference between `map()` and `flatMap()`?
tags: java8, streams, map, flatmap, optional, lambdas, basics

**Start here: the concepts**
- **Stream:** a pipeline that processes a sequence of elements step by step (filter, transform, collect) without changing the source collection.
- **Intermediate operation:** a step like `map` or `filter` that returns another stream. It does nothing until a terminal operation such as `collect` runs.
- **Mapping function:** the small function (a lambda) you pass in, which says what to do with each element.
- **`map()`:** applies the function to each element and puts exactly one result per element in the output. 10 elements in, 10 elements out.
- **Nested structure:** a collection inside a collection, such as `List<List<String>>`. A stream of lists is awkward because you usually want the items inside.
- **Flattening:** taking the nested groups and joining them into one level.
- **`flatMap()`:** your function must return a **Stream** for each element. `flatMap` then merges all those streams into one stream. Because each stream can be empty, have one item or have many, the output can be smaller or larger than the input.

**The live scenario**
An order service handles about 50,000 orders an hour. Each `Order` has a `List<Item>`. A developer wrote `orders.stream().map(Order::getItems).count()` to count items sold. The report said 50,000, which is the number of orders, not items. With about 3 items per order (illustrative), the real figure was around 150,000. `map` produced one list per order, so there was one element per order. Switching to `flatMap(o -> o.getItems().stream())` gave one element per item, and the count was correct.

**What the interviewer is really checking**
Whether you understand the one-to-one versus one-to-many difference and can say when each applies. They also want to see that you know the function passed to `flatMap` must return a stream, not any container.

**How I answer it**
1. **Start with the contract.** `map` is one in, one out. `flatMap` is one in, zero or more out, then flattened. This gives the interviewer the core idea straight away.
2. **Show the shape of the types.** `map(List::stream)` on a `Stream<List<String>>` gives `Stream<Stream<String>>`, which is still nested. `flatMap(List::stream)` gives `Stream<String>`. The type shows what flattening did.
3. **Give a concrete example.**
```java
List<String> people = teams.stream()
    .flatMap(List::stream)
    .collect(Collectors.toList());
// [Ravi, Asha, Meera, Dev]
```
   Each inner list becomes a stream and all four names end up in one stream. (On Java 16+ you can end with `.toList()`.)
4. **Say when to use it.** Use it when each input can produce zero, one or many outputs. Zero matters: returning an empty stream drops that element, so `flatMap` can also act as a filter.
5. **Mention Optional.** `Optional.flatMap` does the same job. It stops you ending up with `Optional<Optional<T>>` when the mapping function itself returns an Optional.

**Trade-offs and what can go wrong**
- The function must return a `Stream`. Returning a `List` will not compile, so call `.stream()` on it.
- A `null` returned by the function is treated as an empty stream, which can silently hide missing data. Return `Stream.empty()` on purpose.
- Using `flatMap` where `map` is enough only adds noise. Use `map` for a plain one-to-one change.
- For primitives, `flatMapToInt` avoids boxing overhead.
- Building a huge inner stream per element has a cost. Keep the mapping function cheap.

**How I'd monitor it**
This is a language-level choice, so the proof is mostly in tests and logs. Unit-test the output count against known input, such as 2 orders with 3 items each giving 6. While debugging, `peek()` can show elements flowing through, but remove it afterwards. In production, log the number of orders and the number of items processed, then search them in Splunk. A ratio of exactly 1:1 across many orders suggests a `map` where a `flatMap` was needed.

**Follow-ups to expect**
- *What does `Optional.flatMap` do differently from `Optional.map`?* -> `map` wraps the function's result in an Optional. `flatMap` expects the function to already return an Optional and avoids double wrapping.
- *Can `flatMap` produce fewer elements than the input?* -> Yes. If the function returns an empty stream for an element, that element contributes nothing.
- *Is `flatMap` lazy?* -> Yes, like other intermediate operations it runs only when a terminal operation runs. In early Java 8, `flatMap` was not fully lazy with short-circuiting operations such as `findFirst`. This was fixed in Java 10.

**60-second answer**
`map` transforms each element into exactly one result, so the number of elements stays the same. `flatMap` takes a function that returns a stream for each element, then merges all those streams into one flat stream. That means one input can give zero, one or many outputs. For example, with a list of teams, `flatMap(List::stream)` gives a single stream of all the people, while `map(List::stream)` would leave me with a stream of streams. I use `flatMap` when each element holds a collection, or when I want to drop some elements by returning an empty stream. `Optional` has the same pair of methods, where `flatMap` avoids an `Optional` inside an `Optional`. The usual mistake is counting with `map` and getting the number of parents instead of the number of children.

### Q53 [mid] What are useful Java 11 features?
tags: java11, lts, httpclient, string-api, files-api, migration, basics

**Start here: the concepts**
- **LTS (Long-Term Support):** Java releases every six months, but only some get years of security patches. Java 8, 11, 17 and 21 are LTS. Companies standardise on these because upgrading constantly is costly.
- **HTTP Client (`java.net.http`):** A built-in way to call REST APIs. It replaces the old, clumsy `HttpURLConnection`. It supports HTTP/1.1, HTTP/2 and WebSocket. It can block (`send`) or return a `CompletableFuture` (`sendAsync`). It was incubating in Java 9/10 and became standard in 11.
- **New String methods:** `isBlank()` is true for empty or whitespace-only text. `strip()` trims whitespace, and it understands Unicode, unlike `trim()`. `lines()` splits text into a stream of lines. `repeat(n)` repeats the text n times.
- **`Files.readString` / `writeString`:** Read or write a whole small file as one `String` in one call, with no reader or stream boilerplate.
- **`Optional.isEmpty()`:** The readable opposite of `isPresent()`. It replaces `!opt.isPresent()`.
- **`var` in lambda parameters:** `var` for local variables arrived in Java 10. Java 11 allows it in lambda parameters too, e.g. `(var a, var b) -> a + b`. The reason is that you can put annotations such as `@NonNull` on the parameters without writing the full type. The restriction is all-or-nothing: you cannot mix `var` with explicit types or with unnamed parameters in one lambda.
- **Single-file launch:** `java Hello.java` compiles in memory and runs the file, with no separate `javac` step. It suits small scripts and quick experiments.
- **Removed modules:** Java 11 dropped the Java EE and CORBA modules from the JDK (JAXB, JAX-WS and similar). It also removed Java Web Start. Code that silently relied on these now fails.

**The live scenario**
A team upgraded 40 Spring services from Java 8 to 11. The build was green, but in staging 6 services crashed at startup with `ClassNotFoundException: javax.xml.bind.JAXBException`. Java 8 shipped JAXB inside the JDK, and Java 11 does not. Adding the JAXB dependency to each pom fixed it. The same upgrade let them replace Apache HttpClient in a small internal tool with the built-in client, which removed one dependency to patch.

**What the interviewer is really checking**
Whether you have actually used Java 11 or only memorised a list. They want to see that you know which features are new APIs and which are language changes. They also want to hear that you know migration is not free.

**How I answer it**
1. **Say it is an LTS release.** That explains why teams move from 8 to 11 at all: they get a supported baseline.
2. **Start with the HTTP Client.** It is the biggest practical change, because it gives async calls and HTTP/2 without a third-party library.
```java
var client = HttpClient.newHttpClient();
var req = HttpRequest.newBuilder(URI.create("https://example.com")).build();
var res = client.send(req, HttpResponse.BodyHandlers.ofString());
```
3. **Cover the small API wins.** These are the String methods, `Files.readString` and `writeString`, and `Optional.isEmpty()`. Each one removes boilerplate or a common bug, such as `trim()` missing Unicode spaces.
4. **Explain `var` in lambdas accurately.** Say that `var` itself is Java 10 and that Java 11 extends it to lambda parameters so annotations can be added.
5. **Mention single-file launch** for quick scripts.
6. **Finish with migration.** Name the removed Java EE/CORBA modules and say you test on JDK 11 before cutting over.

**Trade-offs and what can go wrong**
- Removed modules cause runtime failures, not compile warnings, when code or libraries depended on them. Older libraries and application servers may not run on 11 at all.
- `readString` loads the whole file into memory, so it is wrong for large files. Use streaming instead.
- Single-file launch is not a replacement for a build tool.
- Reflection-based frameworks may print "illegal reflective access" warnings, because Java 9 and later enforce module encapsulation more strongly.

**How I'd monitor it**
- Run `jdeps` over the jars before migrating, to find uses of removed modules and JDK-internal APIs.
- Run the full CI pipeline and integration tests on JDK 11.
- After a canary deploy, search Splunk for `ClassNotFoundException OR NoClassDefFoundError` and for "illegal reflective access".
- Compare GC pauses, heap use and latency before and after the upgrade.
- Track HTTP Client timeouts and error rates.

**Follow-ups to expect**
- *Is `var` a Java 11 feature?* -> The `var` keyword for local variables is Java 10. Java 11 only adds it to lambda parameters.
- *Why use HttpClient over `HttpURLConnection`?* -> It has a fluent API, HTTP/2, async calls through `CompletableFuture`, and WebSocket support.
- *What breaks most often moving from 8 to 11?* -> The removed Java EE/CORBA modules, such as JAXB. After that come internal-API reflection and old library versions.

**60-second answer**
Java 11 is an LTS release, so it is a common upgrade target from Java 8. The headline feature is the standard HTTP Client in `java.net.http`. It supports HTTP/2 and async calls, and it replaces `HttpURLConnection`. There are also handy small APIs: `isBlank`, `strip`, `lines` and `repeat` on String, `Files.readString` and `writeString`, and `Optional.isEmpty`. `var` in lambda parameters is new in 11, mainly so you can annotate them, while plain `var` came in Java 10. You can also run a single source file directly with `java Hello.java`. The catch is that Java 11 removed the Java EE and CORBA modules, such as JAXB. So I always test the migration, and I add those libraries as dependencies where needed.

### Q54 [mid] How do `trim()` and `strip()` differ?
tags: string, trim, strip, unicode, whitespace, java11, basics

**Start here: the concepts**
- **Whitespace:** characters that show as blank space, such as space, tab and newline. Programs often need to remove them from the edges of user input.
- **Unicode:** the standard that gives every character from every language a number (a *code point*). Besides the ASCII space (U+0020), it defines many other spaces, such as the em space (U+2003) and the ideographic space (U+3000), which is common in Asian text.
- **ASCII:** the old 128-character set. It is the first part of Unicode, so code points 0-127 are the same.
- **Control character:** an invisible, non-printing character with a code point at or below U+001F, such as NUL or tab.
- **Immutable:** a `String` never changes. `trim()` and `strip()` return a string, either a new one or the same object if nothing needed removing.
- **`strip()` family:** added in **Java 11**. `trim()` has existed since Java 1.0, which is why it follows the old, simple rule.

**The live scenario**
A partner sends a 50,000-row customer file every night. Our import job looked up each customer by name after calling `trim()`. One night 1,200 rows (about 2.4%) failed with "customer not found". The names had been copied from Word documents, and some had an em space (U+2003) or an ideographic space (U+3000) at the edge. `trim()` ignored them, so "Hello\u2003" never matched "Hello". Switching to `strip()` fixed most of the rows. A few rows with non-breaking spaces (U+00A0) were still rejected, which taught us that `strip()` is not magic either.

**What the interviewer is really checking**
Whether you know that `trim()` has a narrow, old rule, that `strip()` follows Unicode and arrived in Java 11, and whether you can name the edge cases instead of just saying "strip is better".

**How I answer it**
1. **`trim()` removes every leading and trailing character with a code point at or below U+0020.** That covers the space plus all control characters. The reason is its age: it was written when ASCII was the only mental model.
2. **`strip()` removes characters for which `Character.isWhitespace(int)` is true.** That includes the Unicode space separators such as U+2003 and U+3000, as well as tab, newline and carriage return. The reason is that real text now comes from many languages and from copy-paste.
3. **So the stored example is not a "may": `trim()` always keeps U+2003.**
   ```java
   String s = "\u2003Hello\u2003";
   s.trim();  // unchanged, em spaces stay
   s.strip(); // "Hello"
   ```
4. **The two rules overlap but neither contains the other.** `trim()` removes control characters like NUL (U+0000) that `strip()` keeps. `strip()` removes Unicode spaces that `trim()` keeps.
5. **Neither removes the non-breaking space (U+00A0, also U+2007 and U+202F).** `Character.isWhitespace` deliberately excludes them. If you need those gone, use an explicit regex or replace step.
6. **Java 11 also adds `stripLeading()`, `stripTrailing()` and `isBlank()`.** `isBlank()` uses the same Unicode rule. For new code I default to `strip()` and say why.

**Trade-offs and what can go wrong**
- Changing `trim()` to `strip()` in old code can change behaviour for existing data, because NUL and other control characters are no longer removed. Check before a mass replace.
- `strip()` needs Java 11 or later, so it is not available on a Java 8 runtime.
- Whitespace is only cleaned at the edges. Spaces inside the text are untouched.
- Normalising input at the API boundary is better than fixing it at every call site.

**How I'd monitor it**
- Track the validation or lookup rejection rate per import and alert when it jumps (for example above 1%).
- In Splunk, search the rejected values for non-ASCII characters, e.g. a regex on `[^\x00-\x7F]`, and log the code points of the offending characters.
- Add unit tests with U+2003, U+3000, U+00A0, tab and NUL so behaviour is pinned down.

**Follow-ups to expect**
- *Does `strip()` remove the non-breaking space?* -> No. `Character.isWhitespace` excludes U+00A0, U+2007 and U+202F, so replace them explicitly.
- *What is the difference between `isEmpty()` and `isBlank()`?* -> `isEmpty()` is true only for length 0. `isBlank()` (Java 11) is also true for a string made only of whitespace by the Unicode rule.
- *Which should I use on Java 8?* -> Only `trim()` exists, so add a regex or `Character.isWhitespace` loop if Unicode spaces matter.

**60-second answer**
Both methods remove blanks from the start and end of a string. `trim()` is the old one and removes anything with a code point at or below the space, U+0020, which includes control characters but not Unicode spaces like the em space. `strip()`, added in Java 11, removes whatever `Character.isWhitespace` accepts, so it handles those Unicode spaces. They are not strict supersets: `trim()` removes NUL, which `strip()` keeps. Neither removes a non-breaking space, so that needs an explicit replace. In a real import job, `trim()` left em spaces in names copy-pasted from Word and caused lookup failures. For new code on Java 11 or later I use `strip()` and test with real Unicode examples.

### Q55 [mid] What is the difference between `Runnable` and `Callable`?
tags: runnable, callable, future, executorservice, threads, checked-exceptions, basics

**Start here: the concepts**
- **Thread**: a path of execution inside a program. Several threads let a program do several things at once, for example serving many users.
- **Task**: a piece of work you want run, separate from the thread that runs it. `Runnable` and `Callable` both describe a task.
- **Checked exception**: an error type (such as `IOException`) that the compiler forces you to catch or declare with `throws`. It exists so callers cannot ignore predictable failures.
- **`Runnable`**: an interface with `void run()`. It returns nothing and cannot declare checked exceptions. It dates from Java 1.0.
- **`Callable<V>`**: an interface with `V call() throws Exception` (Java 5). It returns a result of type `V` and may throw checked exceptions.
- **`Future<V>`**: a receipt for work that may not be finished. `get()` waits for the result. If the task threw, `get()` throws `ExecutionException` with the original error as its cause.
- **`ExecutorService`**: a managed pool of worker threads fed from a queue of tasks. It exists because creating a thread per task is expensive and unbounded.
- **Rejection handling**: the rule for what happens when the pool and its queue are both full.

**The live scenario**
A report service handled about 2,000 requests a minute. Each request ran `new Thread(runnable).start()`. During a sales peak the JVM held thousands of threads, memory climbed, and latency went from 300 ms to 8 s. Separately, a failing database call inside a `Runnable` could only be logged or lost, because `run()` cannot throw a checked exception and nobody received the error. The team moved to a bounded `ExecutorService` with 16 threads and a queue of 200. They used `Callable` for tasks that return data, so failures reach the caller through `Future.get()`. Latency stabilised and failures became visible.

**What the interviewer is really checking**
Whether you know the two differences, which are return value and checked exceptions. They also want to see that you connect them to `ExecutorService` and `Future`, and that you don't create raw threads in production.

**How I answer it**
1. **State the two differences.** `Runnable.run()` is `void` and cannot declare checked exceptions. `Callable<V>.call()` returns `V` and may throw `Exception`. Use `Runnable` for fire-and-forget work. Use `Callable` when you need a result or a checked error.
2. **Show how each is submitted.** `execute(Runnable)` returns nothing. `submit(...)` accepts either type and returns a `Future`. With `submit(Callable)`, `get()` returns the result. With `submit(Runnable)`, `get()` returns `null` and only tells you whether the task finished or failed. A `Callable` cannot be passed to `new Thread(...)`, only to executors or `FutureTask`.
3. **Explain why the Future matters.** A task's exception is stored in the `Future` and surfaces as `ExecutionException` on `get()`. If you never call `get()`, a failure inside `submit()` is silent. With `execute()`, an uncaught exception goes to the thread's uncaught-exception handler.
4. **Prefer an executor over many raw threads.** Threads are costly, and unlimited threads exhaust memory and CPU. A pool reuses a fixed number of threads.
5. **Define the pool's rules explicitly:**
   - **Pool size:** how many tasks run at once.
   - **Queue capacity:** how many wait. Use a bounded queue, because an unbounded one hides overload as growing memory.
   - **Shutdown:** call `shutdown()` and then `awaitTermination()`, so work finishes and the JVM can exit.
   - **Rejection policy:** decide whether to throw, run in the caller, or drop.

```java
Future<Integer> f = pool.submit(() -> repo.countOrders()); // Callable
```

**Trade-offs and what can go wrong**
- `Future.get()` without a timeout can block a thread forever. Use `get(timeout, unit)`.
- `submit(Runnable)` hides exceptions if you drop the `Future`.
- Executors created without shutdown keep non-daemon threads alive and stop the JVM from exiting.
- `Executors.newFixedThreadPool` uses an unbounded queue, which can lead to `OutOfMemoryError`. A hand-built `ThreadPoolExecutor` gives you control.
- A pool that is too small queues work and adds latency. One that is too large wastes memory and causes contention.

**How I'd monitor it**
- Pool metrics: active threads, queue size, completed tasks, and rejected tasks. Export them with `ThreadPoolExecutor` getters or Micrometer's executor metrics.
- Alert when queue depth stays near capacity or rejections are above zero.
- Search Splunk for `ExecutionException`, `RejectedExecutionException` and task-duration logs.
- Take thread dumps to find threads stuck in `Future.get()`.

**Follow-ups to expect**
- *Can you pass a lambda to `submit` without ambiguity?* -> Yes. The compiler picks `Callable` if the lambda returns a value and `Runnable` if it doesn't.
- *What does `Future.get()` do when the task failed?* -> It throws `ExecutionException` wrapping the original exception.
- *What is the difference between `execute` and `submit`?* -> `execute` takes only a `Runnable` and returns nothing. `submit` takes either type and returns a `Future`.

**60-second answer**
Both `Runnable` and `Callable` describe a task. `Runnable.run()` returns nothing and cannot declare checked exceptions. `Callable<V>.call()` returns a result and may throw checked exceptions. I submit either to an `ExecutorService`, and `submit` gives me a `Future`. For a `Callable`, `get()` returns the result or throws `ExecutionException` wrapping the real error. I avoid creating many raw threads, because that is unbounded and expensive. Instead I configure a pool with a size, a bounded queue, a rejection policy and a clean shutdown, and I watch queue depth and rejections.
