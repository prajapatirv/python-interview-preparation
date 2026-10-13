# JVM internals, garbage collection and performance troubleshooting

> **Runnable:** [`01_memory_leaks_gc_and_strings.java`](../examples/05_jvm_gc_performance/01_memory_leaks_gc_and_strings.java)
> **Crib sheet:** [`topics/04-jvm-gc-performance.md`](../topics/04-jvm-gc-performance.md) · **Guide:** Q26–Q27

## What interviewers are actually probing

"A service is slow / out of memory / burning CPU: what do you do?" They want a **method** (which tool, in what order, what evidence ends the investigation),
not a list of flags. They also test that you know heap vs stack vs metaspace, what makes an object collectable, and that GC tuning is the *last* step.

## Must-know points

- **Heap** (objects; young = eden + survivors, old) · **Stack** (per thread, frames, locals) · **Metaspace** (class metadata, native memory) · **direct memory** (NIO buffers) · code cache.
- An object is garbage when **unreachable from GC roots** (thread stacks, static fields, JNI, class loaders). A "leak" in Java = still reachable but no longer needed.
- Generational hypothesis: most objects die young → cheap minor GCs; promoted objects need major/mixed collections.
- **G1** is default since 9 (region-based, pause-time target); **ZGC/Shenandoah** target sub-10 ms pauses; **Parallel** maximises throughput; **Serial** is for tiny heaps.
- `OutOfMemoryError` has flavours: *Java heap space*, *GC overhead limit exceeded*, *Metaspace*, *unable to create native thread*, *Direct buffer memory*.
- `StackOverflowError` is per thread (deep/infinite recursion, `-Xss`); it is not an OOM.

## Interview questions and full answers

### Q1. Explain heap, stack and metaspace.

The **stack** is per thread: one frame per method call holding locals and operand stack; reclaimed on return; size via `-Xss`.
The **heap** is shared: all objects and arrays, divided into young (eden + two survivor spaces) and old generation, managed by the GC (`-Xms/-Xmx`).
**Metaspace** holds class metadata in native memory (replaced PermGen in 8); grows until `-XX:MaxMetaspaceSize`; classloader leaks on redeploy fill it.
Remember: references live on the stack, the objects they point to on the heap.

### Q2. How does garbage collection decide what to free?

Tracing from **GC roots**. Reachable objects are live; everything else is reclaimed. Strong references keep objects alive; `SoftReference` is cleared under memory pressure; `WeakReference` at the next GC; `PhantomReference` for cleanup hooks.
Because reachability, not "last use", decides, a static `Map` that is never cleared is a leak (example 01 section 3).

### Q3. Describe minor, major and full GC, and "stop-the-world".

A **minor** (young) GC copies live objects from eden/survivor to survivor or promotes them to old; it is a short stop-the-world pause.
In G1 a **mixed** collection also reclaims some old regions; a **full** GC is the fallback that compacts everything and is the long pause you want to avoid (usually a sign of mis-sizing, humongous allocations, or a leak).
Concurrent collectors (G1 marking, ZGC, Shenandoah) do most work alongside the application and pause only briefly.

### Q4. Which collector should I choose?

| Goal | Collector | Notes |
|---|---|---|
| Sensible default, balanced | **G1** | `-XX:MaxGCPauseMillis`, don't over-tune |
| Lowest latency, big heaps | **ZGC** (generational in 21) / Shenandoah | pauses ~sub-ms to few ms; slightly more CPU/memory |
| Max throughput batch jobs | **Parallel** | longer pauses acceptable |
| Tiny containers/CLIs | **Serial** | single thread |

Pick by measuring **pause time, throughput and footprint** under real load, not by folklore.

### Q5. What is a memory leak in Java and how do you find one?

Objects that remain reachable but are never used again: static collections, unbounded caches, listeners never deregistered, `ThreadLocal` in pooled threads, un-closed resources, classloaders retained on redeploy.
Find it: confirm a **sawtooth that trends upward** (old gen after full GC keeps rising) in GC logs/metrics → heap dump (`jcmd <pid> GC.heap_dump` or `-XX:+HeapDumpOnOutOfMemoryError`) → open in **Eclipse MAT**, check the **dominator tree** and "path to GC roots" for the biggest retainer → fix → verify the trend flattens.

### Q6. High CPU: what is your process?

1. `top -H -p <pid>` (or `jcmd Thread.print` + a few dumps) to find hot threads; convert the thread id to hex and match `nid=0x...` in the dump.
2. Take **3 thread dumps ~10 s apart**; threads that repeat the same frame are the hot path.
3. If GC threads are hot, it's actually memory pressure: check GC logs.
4. For a precise answer use a profiler: **async-profiler / JFR** flame graph.
5. Typical culprits: infinite/busy loops, regex backtracking, serialization of huge payloads, excessive logging, lock spinning, N+1 calls, JIT compilation after a deploy.

### Q7. High memory / OOM: what is your process?

Look at which pool: heap (`jstat -gcutil`, GC logs), metaspace, direct buffers, native threads (`unable to create native thread` → too many threads / ulimit).
Take a heap dump, histogram (`jcmd <pid> GC.class_histogram`), compare two dumps for growth. In containers verify `-XX:MaxRAMPercentage` against the cgroup limit — the JVM total (heap + metaspace + threads + direct) must fit, or the kernel OOM-kills the pod (exit 137) *without* a Java OOM.

### Q8. `String` pool, `==` versus `equals`, and why `+=` in a loop is bad.

Literals are interned in the pool, so `"a" == "a"` is true while `new String("a") == "a"` is false; always `equals`. `String` is immutable (thread-safe, cacheable hash, safe as a map key, security-sensitive).
`s += x` in a loop allocates a new string each time (O(n²)); use `StringBuilder` (single-thread) — the compiler already optimises simple single expressions (`invokedynamic` string concat since 9). `StringBuffer` is the legacy synchronised version.

### Q9. How does the JIT work, and why are Java benchmarks tricky?

The interpreter profiles code; hot methods are compiled by C1 (quick) then C2 (heavily optimised: inlining, escape analysis, loop unrolling). Consequences: **warm-up** (first requests are slow; autoscaling needs it), de-optimisation after a changed assumption, and microbenchmarks lying (dead-code elimination). Use **JMH**, not `System.nanoTime` around a loop.

### Q10. What are the JVM flags you set in a container?

```text
-XX:MaxRAMPercentage=75.0          # heap relative to the container limit, not the host RAM
-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps
-Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=10M
-XX:+ExitOnOutOfMemoryError        # let the orchestrator restart a poisoned process
-Djava.security.egd=file:/dev/./urandom   # older images: avoid entropy blocking
```

Leave `-Xms = -Xmx` for predictable behaviour on a dedicated service, and avoid tuning G1 internals without GC-log evidence.

### Q11. What is escape analysis, and why do small objects not always cost?

C2 can prove an object never escapes a method and then **scalar-replace** it (no heap allocation) or elide locks. That's why "allocation is expensive" is context-dependent and why you should measure before "optimising" allocations away.

## A worked example

Run [`01_memory_leaks_gc_and_strings.java`](../examples/05_jvm_gc_performance/01_memory_leaks_gc_and_strings.java). Then re-run with
`java -Xmx64m -Xlog:gc 01_memory_leaks_gc_and_strings.java` and read the GC events. Finally comment out `LEAKY_CACHE.clear()`
and lower `-Xmx` until you trigger `OutOfMemoryError`; add `-XX:+HeapDumpOnOutOfMemoryError` and inspect `java_pid*.hprof` in MAT.

## Hands-on drills

1. Write a loop that leaks via a `ThreadLocal` in a fixed thread pool and show growth with `jcmd`.
2. Compare G1 vs Parallel vs ZGC pause times for the same allocation-heavy program (`-Xlog:gc`).
3. Explain what `Full GC (Allocation Failure)` followed by `OutOfMemoryError: Java heap space` implies.
4. Use `jcmd <pid> VM.native_memory summary` (with `-XX:NativeMemoryTracking=summary`) to account for non-heap memory.
5. Convert a hot-thread id from `top -H` into the matching `nid` in a thread dump.

## The 60-second spoken answer

"Objects live on the heap, split into young and old generations, and are collected when they're unreachable from GC roots, so Java leaks are
reachable-but-unwanted objects like unbounded static caches. G1 is my default; I reach for ZGC only for latency-critical large heaps.
For production problems I start from metrics and GC logs, take thread dumps for CPU, a heap dump with MAT for leaks, and I make sure the
heap is sized as a percentage of the container limit so Kubernetes doesn't OOM-kill us. I tune GC last, with evidence."
