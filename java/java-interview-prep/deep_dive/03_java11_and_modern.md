# Java 11 and beyond: what changed after Java 8, and how to migrate

> **Runnable:** [`01_java9_to_21_language_features.java`](../examples/03_java11_and_modern/01_java9_to_21_language_features.java) ·
> [`02_http_client_java11.java`](../examples/03_java11_and_modern/02_http_client_java11.java) ·
> [`03_virtual_threads_java21.java`](../examples/03_java11_and_modern/03_virtual_threads_java21.java)
> **Crib sheet:** [`topics/02-modern-java-11-to-25.md`](../topics/02-modern-java-11-to-25.md) · **Guide:** Q19–Q22

## What interviewers are actually probing

The requirement lists "Java 8" and "Java 11" separately, which usually means: *the codebase is on 8, there is a migration to 11 (or beyond)*.
So expect "what is new in 11", "what breaks when moving 8 → 11", and "would you go to 17/21?". Showing that you know the **module system fallout**,
the **removed Java EE modules**, and the **GC/container changes** is what separates a migration owner from a feature-list reciter.

## Must-know points

- Java 11 is an **LTS** (2018). Between 8 and 11: `var` (10), `List.of/Map.of` (9), `HttpClient` (11), new `String`/`Files`/`Optional` methods, G1 default (9), JPMS (9), container awareness (10).
- **Removed in 11**: Java EE & CORBA modules (`javax.xml.bind`/JAXB, `javax.annotation`, `javax.activation`, JAX-WS). Add them back as dependencies.
- **Strong encapsulation** of JDK internals (`sun.misc.Unsafe`, `--illegal-access` warnings in 9–15, denied by default in 16/17). Reflection hacks and old libraries break here.
- JDK 17 (LTS): records, sealed classes, text blocks, switch expressions, pattern `instanceof`. JDK 21 (LTS): virtual threads, pattern `switch`, sequenced collections.
- Spring Boot 3 requires **Java 17** and `jakarta.*` namespaces; Boot 2.7 is the last line that runs on 8.

## Interview questions and full answers

### Q1. What are the most useful Java 9–11 features?

| Feature | Version | Why it matters |
|---|---|---|
| `List.of/Set.of/Map.of` | 9 | immutable literals; reject `null` |
| `var` for locals | 10 | less noise; still statically typed; `var` allowed in lambda params (11) |
| `String`: `isBlank`, `strip`, `lines`, `repeat` | 11 | `strip` is Unicode-aware, `trim` only strips ≤ U+0020 |
| `Optional`: `isEmpty`, `ifPresentOrElse`, `or`, `orElseThrow()` | 9–11 | cleaner branches |
| `Files.readString/writeString` | 11 | one-liners |
| `java.net.http.HttpClient` | 11 | HTTP/2, async, built-in |
| `Collectors.toUnmodifiableList` / `Stream.takeWhile` | 9–10 | |
| Local-variable syntax for lambdas, `Predicate.not` | 11 | `filter(Predicate.not(String::isBlank))` |
| Single-file launch `java Hello.java` | 11 | scripts and **this lab** |
| Flight Recorder + ZGC (experimental) | 11 | production profiling without a tool licence |

### Q2. `trim()` versus `strip()`?

`trim()` removes characters ≤ `U+0020` (ASCII whitespace/control). `strip()` uses `Character.isWhitespace`, so it handles Unicode spaces such as `U+2003` (em space).
`stripLeading`/`stripTrailing` exist too. For "is this field empty after cleaning?" use `isBlank()` rather than `trim().isEmpty()`.

### Q3. Show the Java 11 HTTP client and say how it differs from `HttpURLConnection`/RestTemplate.

```java
HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(2)).build();   // reuse: it pools connections
HttpRequest req = HttpRequest.newBuilder(URI.create(url))
        .timeout(Duration.ofSeconds(3)).header("Accept", "application/json").GET().build();

HttpResponse<String> sync = client.send(req, BodyHandlers.ofString());
CompletableFuture<String> async = client.sendAsync(req, BodyHandlers.ofString()).thenApply(HttpResponse::body);
```

It is immutable and thread-safe, supports HTTP/2 and WebSocket, and is async by design. There is **no default timeout**: set both connect and request timeouts.
It has no interceptors or retry (use a wrapper or a library); in Spring you'd normally use `RestClient`/`WebClient`, which can sit on top of it.
Example 02 runs it against an embedded server.

### Q4. What do you check when migrating from Java 8 to 11?

1. **Build**: compiler `release 11`, Maven/Gradle plugins and Lombok/ByteBuddy/Mockito/ASM versions that read newer class files.
2. **Removed modules**: add `jakarta.xml.bind-api` + runtime (JAXB), `javax.annotation-api`, `javax.activation`, JAX-WS if used.
3. **Illegal reflective access**: run on 11 with `--illegal-access=warn` (9–15) and fix libraries that emit warnings; upgrade Spring, Hibernate, Jackson, cglib users.
4. **JVM flags**: removed/changed options (`-XX:+UseConcMarkSweepGC` deprecated, `-XX:MaxPermSize` already gone); GC logging switched to unified `-Xlog:gc*`.
5. **Default GC** is now G1 (parallel in 8); re-baseline pause times and memory.
6. **Containers**: 10+ honours cgroup limits (`-XX:MaxRAMPercentage`); 8u191+ also has it, but check your exact build.
7. **Behavioural**: `Thread.stop`, `Runtime.exec` and class-loader assumptions (`ClassLoader.getSystemClassLoader()` is no longer a `URLClassLoader`) can break.
8. **Test**: run the full suite, soak test, then roll out gradually behind a canary.

> Tip: do 8 → 11 → 17 as separate steps if the dependency tree is old; each hop has different breakage.

### Q5. What is the module system (JPMS) and do you need it?

Modules (`module-info.java`) add strong encapsulation and explicit dependencies above packages. Most Spring Boot applications stay on the classpath ("unnamed module") and never write a `module-info`.
You **do** feel it indirectly: JDK internals are sealed, so libraries needing `--add-opens` flags must declare them (`--add-opens java.base/java.lang=ALL-UNNAMED`).

### Q6. What is `var` and when is it wrong?

Compile-time type inference for locals: `var users = new ArrayList<User>();`. The static type is still fixed.
Good: long generic types, loops, try-with-resources. Wrong: when the right-hand side hides the type (`var x = service.process();`),
with `null`, with literals where you want a specific numeric type (`var n = 1;` is `int`), and never for fields or method signatures.

### Q7. What are records, and how do they differ from Lombok `@Value`?

`record Point(int x, int y) {}` declares an immutable carrier with canonical constructor, accessors, `equals`, `hashCode`, `toString`; you can add a *compact constructor* for validation.
They cannot extend classes, fields are final, and they are language-level so frameworks (Jackson 2.12+, Spring MVC/Data projections, JPA — *not* as entities) understand them natively.
Use records for DTOs, events, value objects and map keys; keep classes for JPA entities.

### Q8. Sealed classes and pattern matching — why do they matter?

`sealed interface Shape permits Circle, Square, Rect` tells the compiler the full set of subtypes, so a `switch` over them is **exhaustive without `default`**; adding a subtype produces a compile error at every `switch` that needs updating.
Pattern matching (`instanceof` 16, `switch` 21, record patterns 21) removes casts. This is "algebraic data types" for Java, ideal for results (`Approved | Declined | Pending`) and events.

### Q9. What are virtual threads and when would you not use them?

Virtual threads (Java 21) are cheap, JVM-scheduled threads multiplexed onto a small pool of carrier threads. When one blocks on I/O it is unmounted, so you can write plain blocking code and still serve ~100k concurrent requests.
They help **I/O-bound, high-concurrency** workloads; they do **not** speed up CPU-bound work and are **not** meant to be pooled.
Gotchas: pinning while inside `synchronized` (Java 21) or native frames, `ThreadLocal`-heavy code, and resource limits (DB pool, rate limits) still apply — bound with a `Semaphore`.
Spring Boot 3.2+: `spring.threads.virtual.enabled=true`. Example 03 shows 5,000 blocking tasks in ~0.3 s vs ~5 s on a 200-thread pool.

### Q10. Should we upgrade to 17 or 21? How do you justify it?

Frame it as **risk and value**: Java 8 still receives patches from vendors such as Temurin and Corretto, but the ecosystem has moved on (Spring Boot 3 / Spring Framework 6 require 17; Hibernate 6 and newer cloud SDKs and clients increasingly drop 8), so staying means freezing your dependency versions.
Value: better GC (G1/ZGC), startup/CDS, container support, language features that reduce code, security fixes, and being able to upgrade Spring Boot.
Risk: reflection-heavy libraries, build tooling, and a `javax→jakarta` rename if Boot 3 is also in scope. Propose: 8 → 11 now with a measured canary, 17 on the Boot 3 upgrade, 21 when virtual threads or the LTS cadence justify it.

### Q11. What changed for GC and memory between 8 and 11+?

G1 became the default (9); ZGC (11 experimental, 15 production, 21 generational) and Shenandoah offer sub-10 ms pauses; unified logging (`-Xlog`); Metaspace replaced PermGen already in 8;
`-XX:+UseContainerSupport` is on by default; compact strings (9) reduce heap for Latin-1 text; CDS archives speed startup.
Practical advice: leave G1 at defaults, set `-XX:MaxRAMPercentage`, enable `-XX:+HeapDumpOnOutOfMemoryError`, and only tune when GC logs show a problem.

## A worked example

Run [`01_java9_to_21_language_features.java`](../examples/03_java11_and_modern/01_java9_to_21_language_features.java). Each section header is tagged
with the version that introduced the feature (`[16] Records`, `[21] pattern switch`), which gives you a ready cheat sheet for the
"what's new since 8" question. Then run the HTTP client example; note the timeout section.

## Hands-on drills

1. Take any Java 8 class with getters/equals/hashCode and convert it to a record; list what you lose.
2. Replace an `instanceof` chain with a sealed hierarchy and a pattern `switch`.
3. Write a migration checklist for a 100-module Maven build moving 8 → 11 (what do you change first?).
4. Time 10,000 blocking tasks on a fixed pool vs virtual threads and explain the numbers.
5. Use `jdeps --jdk-internals app.jar` to find internal API usage, and explain each finding.

## The 60-second spoken answer

"Between 8 and 11 the practical changes are `var`, immutable collection factories, the new `String` and `Optional` methods, the built-in HTTP client,
G1 as default and container-aware memory. The migration risks are the removed Java EE modules like JAXB, strong encapsulation of JDK internals that breaks
old reflection-heavy libraries, and changed GC and logging flags. I'd upgrade build tooling and dependencies first, run on 11 with illegal-access warnings
on, fix what they show, and canary it. After that 17 gives records, sealed types and Spring Boot 3, and 21 adds virtual threads for I/O-heavy services."
