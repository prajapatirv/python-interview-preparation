---
id: 02-modern-java
title: Modern Java (11 -> 25 LTS)
focus: What changed since Java 8 and which LTS to target - a favourite opener for Lead profiles
deep_dive: 03
examples: 03_java11_and_modern
---
LTS releases: 8, 11, 17, 21, **25 (Sept 2025)**. Spring Boot 4 requires Java 17 as a minimum and supports Java 25 first-class. Be ready to say "I moved/would move from 8 to 17 to 21/25 in these steps".

### Q1 [basic] Which Java versions are LTS and which one should a new project use in 2026?
LTS: 8, 11, 17, 21, 25. A new project should start on **Java 21 or 25**; Java 25 is the newest LTS (released Sept 2025) and the natural upgrade for teams on 21. Non-LTS releases get only six months of support, so enterprises skip them.

### Q2 [basic] What are `var`, text blocks and `String` helper methods?
`var` (Java 10) = local type inference (the type is still static): `var list = new ArrayList<String>();`. Text blocks (Java 15) are multi-line strings with `"""` - great for SQL/JSON. Helpers: `isBlank`, `strip`, `lines`, `repeat`, `formatted`.

### Q3 [basic] What are List.of, Set.of, Map.of?
Java 9 factory methods that return **immutable** collections (no nulls, `Map.of` rejects duplicate keys). `List.copyOf` makes an immutable copy. Modifying them throws `UnsupportedOperationException`.

### Q4 [intermediate] What is a record? What can't it do?
A compact immutable data carrier: `record Money(BigDecimal amount, String ccy) {}` generates the constructor, accessors, `equals`, `hashCode`, `toString`. It is implicitly final, cannot extend a class, and fields are shallow-immutable. Add validation in a compact constructor. Great for DTOs, events and map keys; not for JPA entities (needs a no-arg constructor and mutability).

### Q5 [intermediate] What are sealed classes and pattern matching for switch?
`sealed interface Payment permits Card, Upi, Wallet {}` limits who can implement it, so the compiler knows all cases. With pattern matching (final in Java 21):
```java
String label = switch (payment) {
  case Card c   -> "card " + c.last4();
  case Upi u    -> "upi " + u.vpa();
  case Wallet w -> "wallet";
};  // no default needed: compiler checks exhaustiveness
```
Also `instanceof` patterns (`if (o instanceof String s)`) and record patterns for destructuring.

### Q6 [intermediate] What are virtual threads (Java 21) and when do they help?
Lightweight threads scheduled by the JVM onto a small pool of carrier (OS) threads. A blocking call parks the virtual thread and frees the carrier, so you can run hundreds of thousands of blocking tasks with the simple thread-per-request style. They help **I/O-bound** workloads (HTTP, JDBC); they do nothing for CPU-bound work.
```java
try (var ex = Executors.newVirtualThreadPerTaskExecutor()) {
  ex.submit(() -> callSlowService());
}
```
Spring Boot 3.2+: `spring.threads.virtual.enabled=true`.

### Q7 [intermediate] Virtual threads vs reactive (WebFlux) - how do you choose?
Virtual threads keep imperative code, normal stack traces and debuggability, with most of the scalability. Reactive gives backpressure and streaming operators but costs a steep learning curve and hard debugging. Default to virtual threads for typical request/response services; keep WebFlux for streaming, backpressure-heavy pipelines or an existing reactive codebase.

### Q8 [advanced] What are the virtual thread pitfalls (pinning, pools, ThreadLocal)?
- **Pinning:** blocking inside `synchronized` (before Java 24) pinned the carrier thread; Java 24 (JEP 491) removed most of this. Native calls can still pin.
- Don't pool virtual threads; create one per task and limit concurrency with a `Semaphore`.
- Millions of `ThreadLocal` copies are costly -> use **ScopedValue** (final in Java 25).
- The DB connection pool is now the real bottleneck; a pool of 20 still limits you to 20 concurrent queries.

### Q9 [advanced] What are Structured Concurrency and Scoped Values?
**Scoped Values** (final in Java 25): immutable, inheritable per-request context that replaces `ThreadLocal` for virtual threads. **Structured Concurrency** (still preview in Java 25): treat related subtasks as one unit - if one fails, siblings are cancelled and the parent sees the error, so no leaked threads. Say "preview" - don't claim it is production-final.

### Q10 [intermediate] What improved in the JVM/GC since 8?
G1 is the default since 9. ZGC and Shenandoah give pause times in the low milliseconds on big heaps; **generational ZGC** (Java 21) improved throughput. Containers: the JVM respects cgroup CPU/memory limits (use `-XX:MaxRAMPercentage`). Compact object headers and faster startup (AppCDS, Project Leyden) keep arriving.

### Q11 [intermediate] What is the HTTP Client and what replaced `HttpURLConnection`?
`java.net.http.HttpClient` (Java 11): HTTP/2, async `sendAsync` returning `CompletableFuture`, WebSocket. In Spring use `RestClient` (6.1+) or declarative HTTP interfaces; keep `HttpClient` for plain Java services.

### Q12 [intermediate] What does Stream API add after Java 8?
`takeWhile`/`dropWhile` (9), `toList()` (16, returns unmodifiable list), `mapMulti` (16), `Collectors.teeing` (12) and **Stream Gatherers** (Java 24 final) for custom intermediate operations such as windowing.

### Q13 [advanced] How would you migrate a large Java 8 app to Java 21/25?
1. Upgrade build tools (Maven/Gradle, plugins) and run on 11 first; fix `--add-opens`, removed `javax.xml.bind`, `sun.misc.Unsafe` usage.
2. Move 11 -> 17: strong encapsulation of JDK internals; update Lombok, Mockito, ByteBuddy, Jackson.
3. Move frameworks: Spring Boot 2 -> 3 means `javax.*` -> `jakarta.*` (use OpenRewrite recipes).
4. Move to 21/25, run load tests, compare GC logs, then switch to virtual threads where the profile says so.
5. Roll out with canary and the old JVM flags removed.
> Follow-up: what blocks the jump? Old libraries and reflection-heavy code.

### Q14 [intermediate] What is the module system (JPMS) and do you use it?
Java 9 modules (`module-info.java`) give strong encapsulation and `jlink` small runtimes. Most Spring apps stay on the classpath; JPMS matters mostly for libraries and for understanding errors like `InaccessibleObjectException` ("module java.base does not open ...").

### Q15 [intermediate] What is GraalVM Native Image and its trade-offs?
Ahead-of-time compiles the app into a native executable: startup in tens of milliseconds and low memory (great for serverless/scale-to-zero). Costs: long build, no runtime class generation, reflection/proxies need hints (Spring AOT generates them), peak throughput is usually lower than a warmed-up JIT. Use it for Lambda/CLI/short-lived services, not by default.

### Q16 [intermediate] What are `Stream.toList()`, `Optional.orElseThrow()` and `switch` expressions worth in code reviews?
Small readability wins: `toList()` replaces `collect(Collectors.toList())`; no-arg `orElseThrow()` replaces `get()`; switch expressions return values and avoid fall-through bugs. Lead point: set these in your team's style guide, enforce with Checkstyle/Sonar and OpenRewrite.

### Q17 [advanced] What is Project Valhalla / Leyden / Panama in one line each?
Valhalla: value types to remove object-header overhead. Leyden: faster startup/warmup via AOT cache. Panama: safe, fast native-memory and foreign function API (replacing JNI). None needs to be used today; knowing the direction signals that you track the platform.

### Q18 [design] Your team is on Java 8 with Spring Boot 2.x. Make the case and plan for upgrading.
- **Why:** Spring Boot 2 and Java 8 are out of free support (security fixes, CVE exposure), better GC/containers, virtual threads, records/sealed types reduce code.
- **Plan:** inventory dependencies -> automated recipes (OpenRewrite) -> upgrade in small steps with green CI at each step -> performance baseline before/after -> feature-flag/canary rollout -> remove old runtime.
- **Risks:** `javax` -> `jakarta`, old libraries, reflection, Hibernate 6 query changes.
- **Measure:** startup time, p95 latency, memory, GC pause, build time.

### Q19 [design] Design how you would introduce virtual threads into a latency-sensitive Spring Boot service safely.
- **Requirements:** more concurrent blocking I/O without more platform threads, no regression in p99.
- **Approach:** enable virtual-thread executors (`spring.threads.virtual.enabled=true`) on a canary, keep CPU-bound work on a bounded pool, replace `synchronized` around I/O with `ReentrantLock` where pinning shows up (JFR `jdk.VirtualThreadPinned`).
- **Guard rails:** a semaphore per downstream (virtual threads remove the natural pool limit, so you can now overwhelm the DB or a partner API), connection-pool sizing, and `ThreadLocal` audit.
- **Measure:** p95/p99, throughput, DB pool wait time, carrier-thread pinning; roll back via the property flag.

### Q20 [design] Design a migration of a shared internal library used by 40 services from Java 8 to a multi-release, LTS-friendly artifact.
Publish a **multi-release JAR** (or two classifiers) built on the oldest supported baseline, with a deprecation window and semantic versioning. Add a compatibility test matrix (Java 17 / 21 / 25) in CI, an OpenRewrite recipe for consumers, and a dashboard of which service uses which version. Trade-off: supporting too many baselines slows the library; set an explicit policy (for example the last two LTS releases). Failure mode: a transitive dependency drags a consumer back to `javax.*` - use a BOM and enforcer rules.
