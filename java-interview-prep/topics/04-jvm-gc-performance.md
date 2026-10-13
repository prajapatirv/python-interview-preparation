---
id: 04-jvm-performance
title: JVM Internals, GC & Performance Tuning
focus: Memory model, garbage collectors, profiling, containers - what Leads use in RCA
---

### Q1 [basic] Describe JVM memory areas.
Heap (young: eden + survivor; old), Metaspace (class metadata, native memory), thread stacks, code cache (JIT output), direct buffers. `OutOfMemoryError: Java heap space` vs `Metaspace` vs `unable to create native thread` point to different areas.

### Q2 [basic] What is garbage collection and what are GC roots?
GC reclaims objects that cannot be reached from **roots**: thread stacks/locals, static fields, JNI references, active threads. Reachable objects live even if the code never uses them again (that is how leaks happen).

### Q3 [basic] Stack vs heap?
Stack: per-thread, holds frames, locals and references; fast; `StackOverflowError` on deep recursion. Heap: shared objects, managed by GC.

### Q4 [intermediate] How does generational GC work?
Most objects die young. New objects go to eden; a minor GC copies survivors to a survivor space and ages them; after a threshold they are promoted to old gen. Old gen is collected less often (mixed/major GC). Premature promotion (survivors too small) fills old gen and causes long pauses.

### Q5 [intermediate] G1 vs ZGC vs Parallel vs Shenandoah - which when?
| GC | Strength | Use when |
|---|---|---|
| Parallel | max throughput, longer pauses | batch jobs |
| G1 (default) | balanced, tunable pause goal | most services, heaps up to ~tens of GB |
| ZGC | pauses ~ms, large heaps, generational since 21 | low-latency, big heaps |
| Shenandoah | low pause, concurrent compaction | similar to ZGC (OpenJDK builds) |

### Q6 [intermediate] Which JVM flags do you set for a containerised service?
`-XX:MaxRAMPercentage=70` (not a fixed `-Xmx` that ignores pod limits), `-XX:+ExitOnOutOfMemoryError` (let Kubernetes restart), `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps`, GC logging `-Xlog:gc*:file=gc.log`, and size the pod request/limit to heap + metaspace + threads + direct memory (heap is only ~60-70% of RSS).

### Q7 [intermediate] A pod gets OOMKilled but heap looks fine. Why?
OOMKilled = the **container** exceeded its memory limit, not a Java `OutOfMemoryError`. Non-heap memory counts: metaspace, thread stacks (1MB each x thousands of threads), direct buffers (Netty), JIT, native libraries. Check with Native Memory Tracking (`-XX:NativeMemoryTracking=summary`, `jcmd VM.native_memory`) and lower `MaxRAMPercentage`.

### Q8 [intermediate] How do you read a GC log to see if GC is the problem?
Look at pause time and frequency, "Pause Young/Full", heap after GC, and the % of time in GC. Red flags: repeated Full GCs, heap-after-GC trending up (leak), pauses above your SLO, "to-space exhausted", humongous allocations in G1. Tools: GCeasy, JDK Mission Control.

### Q9 [advanced] How do you do a heap dump analysis step by step?
1. Capture: `jcmd <pid> GC.heap_dump /tmp/h.hprof` (or auto on OOM).
2. Open in Eclipse MAT -> Leak Suspects report.
3. Check Dominator Tree for the biggest retained sizes; use "Path to GC Roots (exclude weak refs)".
4. Typical findings: huge `HashMap` cache, session objects, a list in a singleton, `ThreadLocal` values.
5. Fix + add a bound/eviction + a metric/alert on old-gen usage after GC.

### Q10 [advanced] What is JIT compilation and warm-up?
HotSpot interprets first, then compiles hot methods with C1 (quick) and C2 (optimizing, with inlining and escape analysis). Cold JVMs are slow for the first seconds -> use readiness probes, warm-up requests, CDS/AppCDS, or native image for serverless. Benchmark with JMH, never with `System.currentTimeMillis()` loops.

### Q11 [advanced] What is escape analysis?
If the JIT proves an object never escapes a method, it may allocate it on the stack or remove it (scalar replacement) - which is why tiny temporary objects are cheap and why micro-optimising allocation by hand is usually pointless.

### Q12 [intermediate] How do you profile a slow endpoint?
Start with the trace (which span is slow: DB, remote call, or CPU?). Then JFR / async-profiler for CPU and allocation flame graphs, `jcmd Thread.print` for blocked threads, DB slow-query log/`EXPLAIN`. Fix the biggest bar in the flame graph first, then re-measure.

### Q13 [intermediate] What are common performance anti-patterns in Spring apps?
N+1 queries, `findAll()` without paging, fetching entities when a projection is enough, synchronous calls in a chain, huge JSON payloads, logging at DEBUG in hot paths, unbounded caches, creating `ObjectMapper`/`SimpleDateFormat` per request, connection pool too small/large, missing indexes.

### Q14 [advanced] How do you size the DB connection pool (HikariCP)?
A small pool is usually faster. A good start: `pool = (cores * 2) + effective_spindles`, then tune with load tests; **total across all pods must stay below DB max connections**. Set `connectionTimeout`, `maxLifetime` below the DB/firewall idle timeout, and watch `hikaricp.connections.pending`. With virtual threads, cap concurrency with a semaphore.

### Q15 [advanced] What is the difference between latency, throughput and why p99 matters?
Latency = time per request; throughput = requests per second. Averages hide slow tails; one user request often fans out into many calls, so the p99 of each call dominates the user-visible time. Track p50/p95/p99, not the mean. Use Little's Law: `concurrency = throughput x latency`.

### Q16 [design] Design a performance test and capacity plan for a service that must handle 5x traffic next quarter.
Define SLOs (p95 < 300 ms, error < 0.1%) -> build a realistic workload from production traces -> test with Gatling/k6 in a prod-like environment, ramp until SLO breaks -> find the bottleneck (CPU, DB, pool, downstream) -> fix and repeat -> compute pods needed with 30-40% headroom -> verify autoscaling (HPA on CPU/RPS) and run a soak test for memory leaks -> document limits and alerts.

### Q17 [intermediate] What are JFR and JMC?
Java Flight Recorder is a low-overhead (~1-2%) built-in recorder of GC, allocations, locks, I/O and method samples; start with `jcmd <pid> JFR.start duration=60s filename=rec.jfr` and analyse in JDK Mission Control. Safe to run in production, which is why it is the first tool before external profilers.

### Q18 [advanced] Explain class loading and a ClassLoader leak.
Bootstrap -> Platform -> Application loaders (parent-first delegation). On hot redeploy in an app server, if any static reference/thread/`ThreadLocal` holds a class from the old loader, the whole old loader and its classes stay in Metaspace -> `OutOfMemoryError: Metaspace` after N redeploys. Fix by cleaning threads/drivers on shutdown or restart the process instead of redeploying.

### Q19 [design] Design the JVM and container settings for a service that runs as 20 pods with 2 GB memory limits on Kubernetes.
Set `-XX:MaxRAMPercentage=70` (leave room for metaspace, thread stacks, direct buffers), pick G1 (default) or ZGC if pauses matter, cap `-XX:MaxMetaspaceSize`, enable GC logging and `-XX:+HeapDumpOnOutOfMemoryError` to a mounted volume, and set CPU requests so `availableProcessors` is correct. Verify with a load test: container RSS must stay below the limit or the pod is OOMKilled. Trade-off: a bigger heap means fewer GCs but longer worst-case pauses and less native headroom.

### Q20 [design] Design an always-on, low-overhead production profiling setup for a fleet of JVMs.
Run **JFR** continuously with the default profile (about 1% overhead) into a rolling disk buffer, export GC and JVM metrics through Micrometer to Prometheus, and attach async-profiler on demand via a guarded actuator/ops endpoint. Dump JFR automatically on alert (high p99, GC pause threshold). Keep recordings short-lived and access-controlled because they can contain sensitive data. Failure mode: profiling that itself causes the incident - always rate-limit and time-box on-demand profiles.
