---
id: company-jpmc-java-11-to-27
title: JPMorgan Chase pack (5/5): Java 11 to Java 27, major features and differences
stack: java
skill: java-core
---
Part of the **JPMorgan Chase Java mid/senior pack** (hub: `../company-chase-travel/README.md`). A JPMC SDE-3 candidate
reported being asked about the **advantages of Java 21's new features** and to **compare Java with other languages**, and
JPMorgan is publicly known to run OpenRewrite at scale to keep applications on supported Java versions. So expect
"what changed between versions, and why would we upgrade?"

**Facts checked on 2026-10-23** against the OpenJDK project pages: JDK 26 shipped 17 March 2026 (10 JEPs); JDK 27 shipped
15 September 2026 (9 JEPs). **LTS versions: 11, 17, 21, 25.** The next LTS is expected to be **Java 29 (September 2027)**.
Java 26 and 27 are **non-LTS** (six months of updates each).

## The version map at a glance

Read the bold rows (the LTS versions) first. "Preview" means usable only with `--enable-preview` and may still change.

| Version | Date | Headline changes you should be able to name |
|---|---|---|
| **11 (LTS)** | Sep 2018 | Standard `HttpClient` (HTTP/2, async); `var` in lambda params; run a single file with `java Main.java`; `String.isBlank/lines/strip/repeat`; `Files.readString/writeString`; `Optional.isEmpty`; TLS 1.3; Flight Recorder open-sourced; ZGC and Epsilon (experimental); **Java EE and CORBA modules removed** (JAXB, JAX-WS: now separate dependencies) |
| 12 | Mar 2019 | Switch expressions (preview); `Collectors.teeing`; `String.indent/transform`; Shenandoah (experimental); default CDS archive |
| 13 | Sep 2019 | Text blocks (preview); dynamic CDS archives; ZGC returns unused memory |
| 14 | Mar 2020 | **Switch expressions final**; **helpful NullPointerException messages**; records and `instanceof` patterns (preview); JFR event streaming; CMS GC removed |
| 15 | Sep 2020 | **Text blocks final**; ZGC and Shenandoah production-ready; hidden classes; Nashorn JavaScript engine removed; biased locking disabled |
| 16 | Mar 2021 | **Records final**; **pattern matching for `instanceof` final**; `Stream.toList()`; `jpackage`; JDK internals strongly encapsulated by default |
| **17 (LTS)** | Sep 2021 | **Sealed classes final**; internals encapsulated with no opt-out flag; new random-number generator API; Security Manager deprecated; **baseline for Spring Boot 3 / Spring 6** |
| 18 | Mar 2022 | **UTF-8 by default**; `jwebserver` simple web server; `@snippet` in Javadoc; finalization deprecated for removal |
| 19 | Sep 2022 | Virtual threads, record patterns, structured concurrency (preview/incubator) |
| 20 | Mar 2023 | Preview rounds only (scoped values incubator) |
| **21 (LTS)** | Sep 2023 | **Virtual threads final**; **pattern matching for `switch` final**; **record patterns final**; **sequenced collections** (`getFirst/getLast/reversed`); **generational ZGC**; key encapsulation (KEM) API |
| 22 | Mar 2024 | **Foreign Function & Memory API final** (replaces JNI); **unnamed variables `_`**; launch multi-file source programs; G1 region pinning |
| 23 | Sep 2024 | Markdown in Javadoc comments; ZGC generational by default; `sun.misc.Unsafe` memory methods deprecated; string templates withdrawn |
| 24 | Mar 2025 | **Stream gatherers final**; Class-File API final; **virtual threads no longer pinned by `synchronized`**; AOT class loading and linking (faster startup); quantum-resistant ML-KEM and ML-DSA; Security Manager permanently disabled; non-generational ZGC removed |
| **25 (LTS)** | Sep 2025 | **Scoped values final**; **module import declarations**; **compact source files and instance `main` methods** (`void main()`); **flexible constructor bodies** (code before `super(...)`); **compact object headers** supported; generational Shenandoah; AOT method profiling; Key Derivation Function API; 32-bit x86 port removed |
| 26 | Mar 2026 | **HTTP/3 for `HttpClient`**; AOT object caching with any GC; G1 throughput improvement; warnings when reflection mutates `final` fields ("final means final"); Applet API removed; previews: structured concurrency (6th), lazy constants, primitive patterns, PEM encodings |
| 27 | Sep 2026 | **G1 the default GC in all environments**; **compact object headers on by default**; **post-quantum hybrid key exchange for TLS 1.3**; JFR in-process data redaction; previews: lazy constants (3rd), primitive types in patterns (5th), structured concurrency (7th), PEM (3rd); Vector API (12th incubator) |

**One-line story to remember:** 11 modernised the APIs, 17 modernised the *language* (records, sealed, switch), 21 modernised
*concurrency* (virtual threads, pattern matching), 25 made Java simpler and leaner (scoped values, `void main`, compact
headers, AOT startup), and 26-27 keep improving runtime efficiency and security (HTTP/3, G1 everywhere, post-quantum TLS).

Each answer below has a **120-second point-by-point version** (*How I answer it*) and a **60-second answer**.

Levels: **mid** (3-6 yrs) · **senior** (6-10) · **architect** (10+, "expert").

### Q1 [mid] What changed from Java 8 to Java 11 that you use in daily work?
tags: java-11, httpclient, var, string-api, files-api, removed-modules, jpmc

**Start here: the concepts**
- Java 9 introduced the **module system** and a six-month release cadence; Java 11 was the first LTS after Java 8.
- Most teams jumped 8 -> 11 directly, so interviewers group 9, 10 and 11 together.

**The live scenario (functional requirement)**
*FR: "Move the statements service from Java 8 to 11 without breaking the build."* The build failed on `javax.xml.bind` (JAXB): it had been part of the JDK in 8 and was removed in 11.

**What the interviewer is really checking**
Practical knowledge of the APIs you gained, and the breaking changes you hit during the upgrade.

**How I answer it** (120-second answer, point by point)
1. **`var` (Java 10):** local type inference: `var trades = new ArrayList<Trade>();`. Java 11 also allows it in lambda parameters, so you can add annotations.
2. **`HttpClient` (Java 11):** a standard client with HTTP/2, async calls with `CompletableFuture`, and timeouts. It replaces `HttpURLConnection`.
3. **String helpers:** `isBlank()`, `strip()` (Unicode-aware `trim`), `lines()`, `repeat(n)`.
4. **Files:** `Files.readString(path)` and `Files.writeString(path, text)`.
5. **Collections (Java 9-10):** immutable factories `List.of`, `Set.of`, `Map.of`, and `List.copyOf`. `Collectors.toUnmodifiableList()`.
6. **Optional and streams:** `Optional.isEmpty`, `ifPresentOrElse`, `or`, `stream()`; `Stream.takeWhile`, `dropWhile`, `ofNullable`.
7. **Running a single file:** `java Hello.java` with no separate compile step.
8. **Runtime:** better container awareness (CPU and memory limits), G1 the default GC (since 9), Flight Recorder free to use.
9. **What broke:** JAXB, JAX-WS, `javax.annotation` and CORBA were removed (add them as dependencies, or move to Jakarta), and libraries using JDK internals printed illegal-access warnings.

**Trade-offs and what can go wrong**
- `var` with a vague right-hand side (`var x = service.get()`) hurts readability; use it when the type is obvious.
- `List.of` rejects nulls and is immutable; code that later calls `add` throws.

**Follow-ups to expect**
- *What is the module system for?* -> Strong encapsulation and reliable configuration of the JDK itself; most applications still run on the classpath.
- *Why is G1 the default?* -> It balances throughput and pause times for typical server heaps.

**60-second answer**
"From 8 to 11 the daily wins are var for local variables, the standard HttpClient with HTTP/2 and async support, String helpers like isBlank, strip, lines and repeat, Files.readString and writeString, immutable collection factories like List.of, and better Optional and Stream methods. Running a single file with java Hello.java is handy for scripts. The runtime became container-aware, G1 became the default, and Flight Recorder is free. The upgrade pain was the removed Java EE modules: JAXB and JAX-WS had to become explicit dependencies, plus warnings from libraries using JDK internals."

### Q2 [mid] Which Java 17 features do you use, and why does Java 17 matter for Spring?
tags: java-17, records, sealed-classes, text-blocks, switch-expressions, pattern-matching-instanceof, helpful-npe, jpmc

**Start here: the concepts**
- Java 17 is an LTS that collected everything final from 12-17.
- Spring Boot 3 and Spring Framework 6 require **Java 17 as the minimum**, so 17 is the floor for modern Spring.

**The live scenario (functional requirement)**
*FR: "Model API responses and domain events cleanly, and cut boilerplate in the payments service."* The team replaced 40-line DTO classes with one-line records, and `if-instanceof-cast` chains with pattern matching.

**What the interviewer is really checking**
That you know each feature's purpose and use it correctly (records are not entities; sealed types pair with switch).

**How I answer it** (120-second answer, point by point)
1. **Records (16):** `record Money(BigDecimal amount, Currency ccy) {}`. Final, with constructor, accessors, `equals/hashCode/toString` generated. Great for DTOs, events and value objects. **Not** for JPA entities, which need a no-args constructor and mutability.
2. **Sealed classes (17):** `sealed interface PaymentResult permits Approved, Declined, Pending`. Only the listed types can implement it, so the compiler knows every case.
3. **Switch expressions (14):** `case APPROVED -> "ok";`. They return a value, there is no fall-through, and with enums or sealed types the compiler checks that all cases are covered.
4. **Pattern matching for `instanceof` (16):** `if (obj instanceof Card c) { use(c); }`, with no cast.
5. **Text blocks (15):** multi-line SQL, JSON or test fixtures with `"""`, which is much more readable.
6. **Helpful NPEs (14):** messages like `Cannot invoke "Account.getId()" because "trade.account" is null`. This shortens production debugging a lot.
7. **Also:** `Stream.toList()` (16) and strong encapsulation of JDK internals.
8. **Why it matters:** Spring Boot 3 needs 17 (and moves `javax.*` to `jakarta.*`), so 17 is the gateway to modern Spring, and its free public updates are long over, so 21 or 25 is the better target today.

**Trade-offs and what can go wrong**
- A record is only shallowly immutable: copy lists in the compact constructor.
- Sealed hierarchies across modules or packages have placement rules; keep them together.

**Follow-ups to expect**
- *Records with Jackson?* -> Supported since Jackson 2.12; no annotations needed.
- *Can a record have methods and validation?* -> Yes: static factories, instance methods, and a compact constructor for validation.

**60-second answer**
"Java 17 is the floor for Spring Boot 3, and it brought in records, sealed classes, switch expressions, pattern matching for instanceof, text blocks and helpful NullPointerException messages. I use records for DTOs, events and value objects, not JPA entities. Sealed interfaces list every allowed subtype, so a switch over them is checked for completeness by the compiler. Pattern matching removes casts, text blocks make SQL and JSON readable, and the helpful NPE messages save real time in production. Today I'd target 21 or 25 rather than 17."

### Q3 [senior] What are the advantages of Java 21's new features?
tags: java-21, virtual-threads, pattern-matching-switch, record-patterns, sequenced-collections, generational-zgc, jpmc

**Start here: the concepts**
- Java 21 (September 2023) is the LTS that finished Project Loom's virtual threads and Project Amber's pattern matching.
- A JPMC SDE-3 candidate reports being asked this question directly.

**The live scenario (functional requirement)**
*FR: "The notifications service must handle 10x more concurrent slow calls, and the payment-result handling code must be safer to change."* Moving to 21 gave both: virtual threads for concurrency, and sealed types with switch patterns for safer branching.

**What the interviewer is really checking**
Not a list, but *why* each feature matters in a real service, with honest limits.

**How I answer it** (120-second answer, point by point)
1. **Virtual threads:** millions of cheap threads. Blocking-style code (JDBC, `RestClient`) scales like asynchronous code for I/O-heavy services. In Spring Boot 3.2+ it is one property: `spring.threads.virtual.enabled=true`. The limit: they don't speed up CPU work, and on 21 `synchronized` can pin (fixed in 24).
2. **Pattern matching for `switch`:**

```java
String text = switch (result) {
    case Approved a           -> "Approved " + a.authCode();
    case Declined(var reason) -> "Declined: " + reason;
    case Pending p            -> "Pending";
};
```

   With a **sealed** type there is no `default`, so adding a new result type becomes a **compile error** wherever it isn't handled. That is safer than if/else chains.
3. **Record patterns:** take records apart inside `instanceof`/`switch` (`Declined(var reason)`), even nested.
4. **Sequenced collections:** `getFirst()`, `getLast()`, `reversed()`, `addFirst()` on lists, deques, `LinkedHashSet` and `LinkedHashMap`. No more `list.get(list.size() - 1)`.
5. **Generational ZGC:** sub-millisecond pauses with much better throughput than the old single-generation ZGC.
6. **Other:** `String.indexOf` with ranges, `StringBuilder.repeat`, `Character` emoji methods, the KEM crypto API, a warning for dynamically loaded agents.
7. **Why it matters overall:** simpler scalable code, safer domain modelling, lower GC pauses, and an LTS with long support.

**Trade-offs and what can go wrong**
- Virtual threads move the bottleneck to DB pools and downstream limits; add concurrency limits.
- Some libraries and agents needed updates for 21; check your APM agent and build plugins first.

**Follow-ups to expect**
- *Virtual threads or WebFlux?* -> Virtual threads for request/response services with blocking libraries; reactive where streaming and backpressure matter.
- *What was still in preview in 21?* -> Structured concurrency, scoped values, string templates (later withdrawn), unnamed classes.

**60-second answer**
"Java 21's biggest advantage is virtual threads: plain blocking code scales to massive concurrency for I/O-bound services, enabled in Spring Boot with one property, though they don't help CPU-bound work. Second, pattern matching for switch with record patterns and sealed types: the compiler checks that every case is handled, so adding a new payment result breaks the build instead of production. Sequenced collections give getFirst, getLast and reversed. And generational ZGC gives sub-millisecond pauses with good throughput. Together that's simpler scalable code, safer domain logic and better latency, on an LTS."

### Q4 [senior] What changed in Java 22 to 25, and why is Java 25 an important LTS?
tags: java-25, java-24, java-22, scoped-values, stream-gatherers, compact-object-headers, aot-cache, ffm-api, flexible-constructors, jpmc

**Start here: the concepts**
- Java 25 (September 2025) is the LTS after 21, collecting the final features of 22, 23, 24 and 25.
- **Project Leyden** improves startup time; **Project Lilliput** shrinks object headers; **Project Panama** connects to native code.

**The live scenario (functional requirement)**
*FR: "Cut container memory and startup time for 300 microservices, and remove `ThreadLocal`-based request context that breaks with virtual threads."*

**What the interviewer is really checking**
Awareness of current Java, and which changes matter to a large enterprise estate.

**How I answer it** (120-second answer, point by point)
1. **Language, easier to read and write:**
   - Unnamed variables `_` (22): `catch (Exception _)`, `case Pending _ ->`.
   - Flexible constructor bodies (25): validate arguments **before** calling `super(...)`.
   - Module import declarations (25): `import module java.base;`.
   - Compact source files and instance `main` (25): `void main() { IO.println("hi"); }` for scripts and teaching.
2. **APIs:**
   - **Stream gatherers** (24): custom intermediate operations, for example `stream.gather(Gatherers.windowFixed(100))` to batch records.
   - **Scoped values** (25): pass request context (user, trace id) safely and cheaply to called code; immutable, and suited to virtual threads, unlike `ThreadLocal`.
   - Foreign Function & Memory API (22): call native libraries without JNI.
   - Class-File API (24) for tools; Key Derivation Function API (25).
3. **Concurrency:** virtual threads are no longer pinned by `synchronized` (24), which removed the biggest reason to avoid them on 21.
4. **Performance and memory:**
   - **Compact object headers** (25, opt-in with `-XX:+UseCompactObjectHeaders`): headers from 12 to 8 bytes, often 10-20% less heap.
   - **AOT cache** (24-25): train once, then start faster with pre-loaded and pre-linked classes and method profiles (`-XX:AOTCacheOutput`, then `-XX:AOTCache`).
   - Generational Shenandoah (25); ZGC generational only (24).
5. **Security:** quantum-resistant ML-KEM and ML-DSA (24); the Security Manager permanently disabled (24).
6. **Why 25 matters:** it is the LTS with all of the above. Spring Boot 4 (November 2025) keeps a Java 17 baseline but is built to take advantage of 25.

**Trade-offs and what can go wrong**
- Tools and agents that relied on the Security Manager or `sun.misc.Unsafe` need updates.
- AOT caches must be regenerated when the application or JDK changes; build them in the CI pipeline.

**Follow-ups to expect**
- *Is structured concurrency final in 25?* -> No, it was in its fifth preview in 25 and still in preview in 27.
- *What is a stable value / lazy constant?* -> A value set once, lazily, then treated as a constant by the JIT; preview since 25 (renamed "lazy constants" in 26).

**60-second answer**
"Java 22 to 25 made Java simpler and leaner. Language: unnamed variables with underscore, code before super in constructors, module imports, and a plain void main for small programs. APIs: stream gatherers for things like batching and windows, scoped values as a safe, virtual-thread-friendly replacement for ThreadLocal context, and the Foreign Function and Memory API instead of JNI. Java 24 stopped synchronized from pinning virtual threads. For efficiency, compact object headers cut heap by around 10-20%, and the AOT cache speeds up startup. Java 25 is the LTS that has all of this, so it's the natural upgrade target from 17 or 21."

### Q5 [senior] What is new in Java 26 and 27, and would you run them in production?
tags: java-26, java-27, http3, g1-default, compact-object-headers, post-quantum-tls, lazy-constants, non-lts, jpmc

**Start here: the concepts**
- **Java 26** (17 March 2026) and **Java 27** (15 September 2026) are **non-LTS** releases. Each gets about six months of updates until the next release.
- Their final features mostly improve the **runtime** (GC, memory, networking, security); the language changes are still previews.

**The live scenario (functional requirement)**
*FR: "Our architecture board asks: should the platform adopt 27, stay on 25, or wait for 29?"*

**What the interviewer is really checking**
Up-to-date knowledge and a sensible adoption policy, not chasing every release.

**How I answer it** (120-second answer, point by point)
1. **Java 26 final features:**
   - **HTTP/3 support in `HttpClient`** (opt-in per client or request).
   - **AOT object caching with any GC,** including ZGC, extending the Leyden startup work.
   - **G1 throughput improvement** from reduced synchronisation.
   - **"Prepare to make final mean final":** warnings when deep reflection changes `final` fields. Some serialisation or mocking libraries will need updates before it becomes an error.
   - Applet API removed.
2. **Java 27 final features:**
   - **G1 is the default GC everywhere.** Before, on small machines or containers (under 2 CPUs or about 1.8 GB), the JVM silently chose Serial GC. This matters for small Kubernetes pods.
   - **Compact object headers on by default:** less heap for the same data, with no flag needed.
   - **Post-quantum hybrid key exchange for TLS 1.3** (X25519MLKEM768 preferred), which protects against "harvest now, decrypt later". Relevant for a bank.
   - **JFR in-process data redaction:** sensitive values such as passwords are masked in recordings.
3. **Still in preview in 27:** structured concurrency (7th), lazy constants (3rd), primitive types in patterns (5th), PEM encodings (3rd); Vector API (12th incubator). Don't build production code on these.
4. **Would I run them in production?** For a bank-scale estate: **stay on the LTS (25)** for production, and run the latest release (27) in **CI as an early-warning build** to catch upcoming breakages. Teams that can upgrade every six months reliably may run non-LTS versions, but most enterprises don't.
5. **Next LTS:** Java 29, expected in September 2027.

**Trade-offs and what can go wrong**
- Non-LTS releases stop getting free updates after six months; falling behind means running without security fixes.
- Default changes (G1 everywhere, compact headers) change memory and CPU profiles; load-test before adopting.

**Follow-ups to expect**
- *How do I try compact headers on 25?* -> `-XX:+UseCompactObjectHeaders` (a product flag since 25); measure heap and GC before and after.
- *Does HTTP/3 change my Spring code?* -> Not by itself; it's at the JDK `HttpClient` level, and needs servers that speak HTTP/3 (over QUIC/UDP).

**60-second answer**
"Java 26 added HTTP/3 to the HttpClient, AOT object caching with any garbage collector, a G1 throughput improvement, and warnings when reflection modifies final fields. Java 27 made G1 the default everywhere, so small containers no longer silently get Serial GC, turned compact object headers on by default for less heap, added post-quantum hybrid key exchange for TLS 1.3, and redacts secrets in JFR recordings. Structured concurrency and lazy constants are still previews. Both are non-LTS, so for production I'd stay on 25 and run 27 in CI as an early warning, then move to 29, the next LTS, in 2027."

### Q6 [mid] What are LTS, non-LTS, preview and incubator features? Which version would you run in production?
tags: lts, release-cadence, preview-features, incubator, enable-preview, support-policy, jpmc

**Start here: the concepts**
- Java ships a new version **every six months** (March and September).
- **LTS** (long-term support) versions get years of updates: 11, 17, 21, 25, and next 29. A new LTS comes every two years.
- **Preview:** a finished design that may still change; it needs `--enable-preview` at compile and run time.
- **Incubator:** an experimental API in a `jdk.incubator.*` module (for example the Vector API).

**The live scenario (functional requirement)**
*FR: "Set the JDK policy for 300 services so they stay secure without constant upgrade projects."*

**What the interviewer is really checking**
That you understand support and risk, not only features.

**How I answer it** (120-second answer, point by point)
1. **Production runs an LTS** from a supported vendor (Oracle, Eclipse Temurin, Amazon Corretto, Azul, Red Hat, Microsoft). It is the same OpenJDK code with different support terms.
2. **Apply quarterly updates** (January, April, July, October): they contain security fixes. Staying on the version but not patching it is the real risk.
3. **Move to the next LTS within about a year** of its release, once frameworks and agents support it.
4. **Never use preview features in production code:** they can change or be withdrawn (string templates were previewed in 21 and 22, then removed).
5. **Test ahead:** run the build on the latest non-LTS JDK in CI to catch deprecations and removals early.
6. **Automate upgrades:** OpenRewrite recipes (`UpgradeToJava21`, `UpgradeToJava25`) plus `jdeps --jdk-internals` to find internal API use.

**Trade-offs and what can go wrong**
- Waiting too long turns a small upgrade into a big multi-version jump (8 -> 21 at once is much harder than step by step).
- Oracle JDK licensing terms differ by version; check before choosing a vendor.

**Follow-ups to expect**
- *How long is LTS support?* -> Depends on the vendor; typically at least 8 years for paid support, with free updates for several years from most OpenJDK vendors.

**60-second answer**
"Java releases every six months, and every two years one is an LTS: 11, 17, 21, 25, then 29 in 2027. In production I run an LTS from a supported OpenJDK vendor and apply the quarterly security updates, because an unpatched JDK is the real risk. I move to the next LTS within about a year once Spring and our agents support it. Preview features need --enable-preview and can change or disappear, like string templates did, so they stay out of production code. I run the latest release in CI as an early warning and automate upgrades with OpenRewrite."

### Q7 [senior] How do records, sealed types and pattern matching change the way you model a domain?
tags: data-oriented-programming, records, sealed-interfaces, pattern-matching, exhaustive-switch, algebraic-data-types, jpmc

**Start here: the concepts**
- **Data-oriented programming:** model data as simple immutable values (records), list all the possible shapes (sealed types), and handle each shape with an exhaustive `switch`.
- This is the Java version of what Scala and Kotlin call algebraic data types.

**The live scenario (functional requirement)**
*FR: "A payment can end as Approved, Declined (with a reason), Pending review or Failed (technical). Every channel (API, email, push) must handle all four, and adding a fifth must be impossible to forget."*

**What the interviewer is really checking**
Whether you use modern features to make illegal states impossible and changes safe, and know when classic OOP polymorphism is still better.

**How I answer it** (120-second answer, point by point)
1. **List the shapes:**

```java
sealed interface PaymentOutcome permits Approved, Declined, PendingReview, Failed {}
record Approved(String authCode) implements PaymentOutcome {}
record Declined(DeclineReason reason) implements PaymentOutcome {}
```

2. **Handle each shape with an exhaustive switch** in each channel. No `default` branch, so when someone adds `Refunded`, every switch that misses it **fails to compile**.
3. **Each record holds only the data that makes sense** for its case: `Approved` has an auth code, `Declined` has a reason. No nullable fields shared by all cases.
4. **Records give immutability and value equality** for free, so these objects are safe to cache and share.
5. **When I still use classic polymorphism** (a method on the interface): when the **behaviour** belongs to the type and new types are added often, but new operations are rare. Pattern matching is better when **operations** (channels, reports) are added often and the set of types is stable.
6. **Java 21+ for the full version** (pattern matching for switch, record patterns); unnamed patterns `_` (22) for cases you don't need.

**Trade-offs and what can go wrong**
- Sealed hierarchies must be closed; use them for real business alternatives, not for open plug-in points.
- A `default` branch in a switch over a sealed type removes the compiler's completeness check; avoid it.

**Follow-ups to expect**
- *How does Jackson serialise a sealed hierarchy?* -> `@JsonTypeInfo` with `@JsonSubTypes` (or automatic detection of permitted subtypes in recent Jackson versions).
- *What's the expression problem?* -> The trade-off in point 5: easy to add types vs easy to add operations.

**60-second answer**
"I model the possible outcomes as a sealed interface with one record per case, like Approved with an auth code and Declined with a reason. Each case only has the fields that make sense, so there are no shared nullable fields. Each channel handles the outcome with a switch over the sealed type with no default, so when someone adds a new outcome, every unhandled switch fails to compile instead of failing in production. Records give immutability and equality for free. I still use classic polymorphism when behaviour belongs to the type and new types are added often; pattern matching wins when new operations are added often."

### Q8 [senior] What problems do structured concurrency and scoped values solve, and what is their status?
tags: structured-concurrency, scoped-values, threadlocal, virtual-threads, preview, java-25, java-27, jpmc

**Start here: the concepts**
- **Structured concurrency:** treat subtasks started together as **one unit**. If one fails, the others are cancelled; the parent waits for all of them. Like a `try` block for threads.
- **Scoped values:** pass read-only context (user, trace id) to everything called inside a scope, without method parameters and without `ThreadLocal`'s problems.

**The live scenario (functional requirement)**
*FR: "Fetch a customer's profile, accounts and limits in parallel; if profile fails, stop the other two calls immediately and return an error; every call must log the request's trace id."* With raw `ExecutorService` futures, a failure in one left the other calls running ("thread leaks"), and the trace id was lost on worker threads.

**What the interviewer is really checking**
Awareness of where Java concurrency is heading, and honesty about the preview status.

**How I answer it** (120-second answer, point by point)
1. **The problem with plain futures:** subtasks are not tied to their parent. If one fails, the others keep running, and if the parent is cancelled, the children don't know.
2. **Structured concurrency:** open a `StructuredTaskScope`, `fork` the three calls, `join`. A failure cancels the siblings and the scope closes only when all are finished. Stack traces and thread dumps show the parent-child relationship.
3. **Status:** still in **preview** in Java 27 (seventh round). In 25 the API changed to `StructuredTaskScope.open()` with "joiners"; 27 adds an exception type parameter. **Use it for learning, not production code yet.**
4. **Scoped values:** **final in Java 25.** `ScopedValue.where(TRACE_ID, id).run(() -> handle())`. Everything inside can read `TRACE_ID.get()`. Values are immutable and automatically gone when the scope ends, and forked subtasks inherit them cheaply.
5. **Why not `ThreadLocal`:** it is mutable, can leak between pooled tasks if not removed, and copying inheritable thread-locals to millions of virtual threads is expensive.
6. **What I do today on 21/25:** virtual threads plus `CompletableFuture`/`ExecutorService` with explicit cancellation and timeouts, and scoped values (on 25) or MDC with context propagation for trace ids.

**Trade-offs and what can go wrong**
- Preview APIs change between releases (this one changed shape in 25); code written against an old preview will not compile later.
- Frameworks such as Spring and logging MDC still mainly rely on `ThreadLocal`; adopting scoped values is gradual.

**Follow-ups to expect**
- *Does structured concurrency need virtual threads?* -> It works best with them (each fork is a virtual thread by default), but it's a separate feature.

**60-second answer**
"With plain futures, subtasks aren't tied to their parent: if the profile call fails, the accounts and limits calls keep running. Structured concurrency treats the forked subtasks as one unit: a failure cancels the siblings and the scope waits for all of them, like a try block for threads. But it's still a preview in Java 27, so not for production code yet. Scoped values became final in 25: immutable context like a trace id, visible to everything inside a scope, cheap to inherit and impossible to leak, unlike ThreadLocal. Today I use virtual threads with timeouts and explicit cancellation, and scoped values where we're on 25."

### Q9 [architect] How would you upgrade a large estate from Java 8/11/17 to 21 or 25?
tags: java-upgrade, openrewrite, jdeps, jakarta-migration, spring-boot-3, migration-strategy, jpmc

**Start here: the concepts**
- An upgrade has three layers: the **JDK** (runtime and language), the **framework** (Spring Boot 2 -> 3 -> 4, `javax` -> `jakarta`), and the **libraries and tools** (build plugins, agents, mocking libraries).
- **OpenRewrite** applies automated, reviewable code changes ("recipes"). JPMorgan Chase is publicly cited as using it at large scale.

**The live scenario (functional requirement)**
*FR: "Move 300 services from mixed Java 8/11/17 to Java 25 within a year, with no production incidents."*

**What the interviewer is really checking**
A safe, automated, wave-based programme, and knowledge of the real breaking points.

**How I answer it** (120-second answer, point by point)
1. **Inventory:** JDK version, Spring Boot version, build tool, risky libraries and agents per service. Run `jdeps --jdk-internals` to find internal API use.
2. **Platform first:** base images for 21/25, CI build images, APM agents and build plugins upgraded and certified.
3. **Automate code changes with OpenRewrite:** `UpgradeToJava21`/`UpgradeToJava25`, `UpgradeSpringBoot_3_x`, `JavaxMigrationToJakarta`. Generate pull requests per service so teams review rather than rewrite by hand.
4. **Known breaking points:**
   - 8 -> 11: removed Java EE modules (JAXB, JAX-WS), illegal-access warnings.
   - 11 -> 17: strong encapsulation of internals (old Lombok, Mockito, ByteBuddy, Groovy versions break); upgrade those libraries.
   - Spring Boot 3: `javax.*` -> `jakarta.*`, Spring Security configuration changes, Hibernate 6 query differences.
   - 21 -> 25: Security Manager gone, `Unsafe` memory methods warning, 32-bit x86 gone, and agent updates.
5. **Waves:** pilot on 2-3 representative services, then waves by risk. Leaf services first, critical payment flows last, with the most testing.
6. **Verify:** full test suites, a performance comparison (GC behaviour, memory, startup), canary releases with metric comparison, and an instant rollback (keep the old image).
7. **Keep current afterwards:** run the next JDK in CI, automate dependency updates (Renovate or Dependabot), and own a regular upgrade cadence.

**Trade-offs and what can go wrong**
- Jumping straight from 8 to 25 without intermediate testing hides which change caused a failure; step through LTS versions in CI even if you release once.
- GC and memory defaults change between versions; capacity can shift, so load-test.

**Follow-ups to expect**
- *How do you handle a library with no Java 17+ version?* -> Replace it, isolate it in its own service, or fork as a last resort.
- *Multi-release jars?* -> Libraries can ship version-specific classes; mostly a library-author concern.

**60-second answer**
"I'd start with an inventory: JDK, Spring Boot version, risky libraries and agents, and jdeps to find internal API use. Then the platform: base images, CI images and APM agents certified on 25. Code changes are automated with OpenRewrite recipes for the Java version, Spring Boot 3 and javax to jakarta, delivered as pull requests teams review. The usual breakages are the removed Java EE modules, strong encapsulation breaking old Lombok or Mockito, and the jakarta move. I'd roll out in waves, from low-risk leaf services to payments last, with performance comparison, canaries and the old image ready for rollback, then keep the next JDK in CI."

### Q10 [senior] How have GC, memory and startup changed from Java 11 to 27, especially in containers?
tags: gc-evolution, container-awareness, g1, zgc, compact-object-headers, cds, aot-cache, project-leyden, jpmc

**Start here: the concepts**
- **Container awareness:** the JVM reads the container's CPU and memory limits (since 8u191/10) instead of the host's.
- **CDS / AOT cache:** save loaded classes (and, since 24-25, linked classes and method profiles) to a file, so later starts are faster.
- **Object header:** the hidden bytes at the start of every object (class pointer, hash, lock bits).

**The live scenario (functional requirement)**
*FR: "Reduce cost of 300 small pods (1 CPU, 1 GB) and cut cold-start time for autoscaling."*

**What the interviewer is really checking**
Practical runtime knowledge that saves money and latency, version by version.

**How I answer it** (120-second answer, point by point)
1. **Java 11:** G1 the default GC; ZGC and Epsilon experimental; container limits respected; default CDS archive (12).
2. **Java 15:** ZGC and Shenandoah production-ready. **Java 14:** CMS removed.
3. **Java 21:** **Generational ZGC**; **Java 23** makes it the ZGC default and **24** removes the non-generational mode.
4. **Java 24-25 (Project Leyden):** the **AOT cache**: do a training run, then start with classes pre-loaded and pre-linked, plus method profiles, so the JIT warms up faster. Real-world startup gains are often reported in the 30-40% range for Spring apps; **measure your own**.
5. **Java 25:** **compact object headers** (12 -> 8 bytes per object, opt-in); generational Shenandoah.
6. **Java 26:** AOT object caching works with any GC (including ZGC); G1 throughput improvement.
7. **Java 27:** **G1 is the default everywhere.** Before, a pod with under 2 CPUs or about 1.8 GB silently got **Serial GC**, which surprises many teams. Compact headers are **on by default**.
8. **What I do for small pods today:** set `-XX:MaxRAMPercentage=75`, choose the GC explicitly on older JDKs, consider at least 2 CPUs for latency-sensitive services, build an AOT cache in CI, and turn on compact headers on 25 after testing.

**Trade-offs and what can go wrong**
- Very small CPU limits plus a concurrent collector (ZGC, Shenandoah) can starve the application threads.
- The AOT cache must match the exact JDK and classpath; regenerate it in every build.

**Follow-ups to expect**
- *GraalVM native image vs AOT cache?* -> Native image gives near-instant startup and small memory, but with closed-world limits and longer builds; the AOT cache keeps the normal JVM with no code restrictions.
- *How do you check which GC a pod runs?* -> `java -Xlog:gc -version`, or `jcmd <pid> VM.flags`.

**60-second answer**
"Since 11 the JVM respects container limits and G1 is the default. ZGC became production-ready in 15, generational in 21, and generational-only in 24. Java 24 and 25 added the Leyden AOT cache: a training run saves loaded and linked classes and profiles, so startup and warm-up are faster. 25 added compact object headers, shrinking every object header from 12 to 8 bytes, and 27 turns them on by default. 27 also makes G1 the default everywhere; before that, small pods with under 2 CPUs or about 1.8 GB silently got Serial GC. For small pods I set MaxRAMPercentage, pick the GC explicitly on older JDKs, and build the AOT cache in CI."

### Q11 [senior] How does Java compare with Kotlin, Scala and Go for backend services?
tags: java-vs-kotlin, java-vs-scala, java-vs-go, language-comparison, jvm-languages, jpmc

**Start here: the concepts**
- **Kotlin** and **Scala** run on the JVM and can use Java libraries. **Go** compiles to native binaries with its own runtime.
- A JPMC SDE-3 candidate reported being asked to compare Java with other languages such as Scala.

**The live scenario (functional requirement)**
*FR: "A new team proposes writing the next pricing service in Kotlin (or Scala, or Go). The architecture board asks for your view."*

**What the interviewer is really checking**
Balanced judgement: technical facts plus team, hiring and ecosystem factors, without language fanboyism.

**How I answer it** (120-second answer, point by point)
1. **Java today:** much less verbose than it was (records, `var`, pattern matching, text blocks), virtual threads for scalability, the largest ecosystem (Spring, Kafka clients), the largest hiring pool, and long-term stability. In a large bank it is usually the default for good reasons.
2. **Kotlin:** null-safety in the type system, concise syntax, data classes, coroutines, excellent Spring support, and 100% Java interop. Good when a team wants more expressiveness with little risk. The costs: two languages in the estate, and coroutines vs virtual threads overlap.
3. **Scala:** powerful functional programming and a strong type system; great for data pipelines (Spark), stream processing and complex domain logic. The costs: a steeper learning curve, slower compilation, smaller hiring pool, and past binary-compatibility pain between versions.
4. **Go:** simple language, fast startup, small memory footprint, single static binary, goroutines. Good for infrastructure tools, proxies and small high-concurrency services. The costs: a smaller enterprise library ecosystem (no Spring equivalent), and less expressive domain modelling.
5. **My decision factors:** team skills and hiring, ecosystem fit (security, observability, internal libraries), operational consistency across 300 services, performance needs, and long-term maintenance.
6. **My usual recommendation:** Java as the default for business services; Kotlin is acceptable where a team is committed to it; Scala for data and streaming where Spark or Akka/Pekko fit; Go for infrastructure and small tools.

**Trade-offs and what can go wrong**
- Mixing many languages increases the cost of shared libraries, security patching and on-call knowledge.
- Choosing based on syntax alone ignores the 10-year cost of ownership.

**Follow-ups to expect**
- *Did modern Java close the gap with Kotlin?* -> Mostly on data classes (records) and pattern matching; Kotlin still has null-safety in the type system and more concise syntax.
- *Virtual threads vs Kotlin coroutines?* -> Similar goals; virtual threads keep ordinary blocking code, coroutines need `suspend` functions.

**60-second answer**
"Modern Java is much more concise than its reputation, with records, pattern matching and virtual threads, and it has the biggest ecosystem and hiring pool, so in a large bank it's the sensible default. Kotlin adds null-safety in the type system and concise syntax with full Java interop, so it's low-risk if a team is committed to it. Scala is strong for functional and data-heavy work like Spark, but harder to learn and hire for. Go is great for small, fast-starting infrastructure services, but has no Spring-level ecosystem. I decide on team skills, ecosystem fit and long-term operations across the estate, not syntax."
