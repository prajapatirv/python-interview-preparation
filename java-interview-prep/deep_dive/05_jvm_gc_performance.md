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

One-liner: **stack = per-thread method execution; heap = shared objects managed by the GC.** Then add the depth:

```text
JVM process
 |- Heap (shared)            objects + arrays, GC-managed        -Xms / -Xmx     -> OutOfMemoryError: Java heap space
 |- Thread stack (1 / thread) frames, locals, operand stack       -Xss (~1 MB)    -> StackOverflowError
 |- Metaspace (native)       class metadata, method bytecode     MaxMetaspaceSize-> OOM: Metaspace
 |- Code cache, direct buffers, GC structures, thread native memory   (all count toward container RSS)
```

**Worked example**

```java
void calculate() {
    int x = 10;                         // primitive local: lives in this frame
    Employee e = new Employee("Ravi");  // 'e' (the reference) is in the frame; the object is on the heap
    process(e);                         // callee gets a COPY of the reference (pass-by-value)
}
```

```text
Stack (this thread)                Heap (shared)
calculate() frame                  Employee { name -> "Ravi" }
   x = 10                             ^
   e  ------------------------------- +
```

**Stack facts to state**
- One stack per thread, so locals are **thread-confined** and need no synchronisation; only objects reachable from shared state do. That is the root of "thread safety = shared mutable state".
- A **frame** is pushed per call (locals, operand stack, return address) and popped on return, so reclamation is free and deterministic.
- `StackOverflowError`: runaway/deep recursion (or a huge `-Xss` multiplied by thousands of threads exhausting native memory -> `unable to create native thread`). Fix by an iterative version, bounding depth, or raising `-Xss` only as a last resort.
- Java is **pass-by-value**: a reference is copied into the callee's frame, so the callee can mutate the object but not rebind your variable.

**Heap facts to state**
- Allocation is fast (thread-local allocation buffers, TLABs: bump a pointer, no lock). Reclamation is by **reachability** from GC roots, never by scope; `x = null` only makes an object *eligible*, it does not trigger GC.
- Young (eden + survivors) -> promoted to old after surviving N collections (tenuring), which is why most objects die cheap.
- An OOM means "too many **reachable** objects" (leak, unbounded cache, oversized result set), not "too many objects created".

**The precision a senior adds (the oversimplification trap)**
- "References live on the stack" is only true of **locals and parameters**. A reference that is a *field* (`Department.employee`) lives inside its object, **on the heap**; array elements and `static` fields are also heap/metaspace-side.
- "Objects are always on the heap" is the spec's model, not the physical truth: **escape analysis** + **scalar replacement** let C2 eliminate the allocation of an object that never escapes a method, keeping its fields in registers or on the stack (see Q11). So "stack fast, heap slow" is an incomplete statement; allocation is cheap, the real heap cost is GC work and cache misses.
- Metaspace is *not* heap and is not covered by `-Xmx`: heap + metaspace + thread stacks + direct buffers must all fit the container limit, or Kubernetes OOM-kills the pod (exit 137) with no Java error.

**Production mapping**

| Symptom | Think | First tool |
|---|---|---|
| `StackOverflowError` | recursion / cyclic call (e.g. bidirectional JPA `toString`, Jackson cycle) | stack trace, repeated frames |
| `OutOfMemoryError: Java heap space` | leak or oversized working set | heap dump (`-XX:+HeapDumpOnOutOfMemoryError`), MAT dominator tree |
| `OutOfMemoryError: Metaspace` | classloader leak / runaway proxies | `jcmd VM.metaspace`, class histogram |
| `unable to create native thread` | too many threads x `-Xss`, ulimit | thread dump, `jcmd Thread.print` |
| Pod OOMKilled, no Java error | non-heap memory | NMT, lower `MaxRAMPercentage` |

**Spoken answer (about 45 seconds):**
> "Each thread has its own stack made of frames, one per method call, holding locals, primitives and the references to objects. Frames are popped when the method returns, so that memory is reclaimed automatically; too much of it gives `StackOverflowError`. The heap is one shared area holding all objects and arrays, reclaimed by the garbage collector when they become unreachable; exhausting it gives `OutOfMemoryError`. So in `Employee e = new Employee()`, the reference is in the frame and the object is on the heap, but I'd be careful with the blanket statement that references live on the stack: fields are part of heap objects, and with escape analysis the JIT can even avoid allocating the object at all. Because locals are thread-confined while heap objects are shared, thread-safety is about shared mutable heap state. Metaspace holds class metadata outside the heap, which matters when sizing containers."

### Q2. How does garbage collection decide what to free?

Tracing from **GC roots**. Reachable objects are live; everything else is reclaimed. Strong references keep objects alive; `SoftReference` is cleared under memory pressure; `WeakReference` at the next GC; `PhantomReference` for cleanup hooks.
Because reachability, not "last use", decides, a static `Map` that is never cleared is a leak (example 01 section 3).

### Q3. Describe minor, major and full GC, and "stop-the-world".

A **minor** (young) GC copies live objects from eden/survivor to survivor or promotes them to old; it is a short stop-the-world pause.
In G1 a **mixed** collection also reclaims some old regions; a **full** GC is the fallback that compacts everything and is the long pause you want to avoid (usually a sign of mis-sizing, humongous allocations, or a leak).
Concurrent collectors (G1 marking, ZGC, Shenandoah) do most work alongside the application and pause only briefly.
How G1 actually selects and moves regions (RSets, SATB marking, mixed GCs, humongous objects): see **Q12**.

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

### Q12. How does the G1 garbage collector work internally?

**Correction to say first:** G1 appeared in Java 7 (7u4) but became the **default in Java 9** (JEP 248); Java 8's default was **Parallel GC**. It is still the default today.

**The one idea:** G1 does not ask "collect young or old?". It asks **"which regions give the most reclaimed memory for the pause budget?"** (hence *Garbage-First*).

**1. Region-based heap.** The heap is cut into ~2048 equal **regions** (1-32 MB, power of two, `-XX:G1HeapRegionSize`). Each region is *logically* Eden, Survivor, Old or Humongous, and the roles are not contiguous and can change as regions are freed and reused.

```text
 E  E  S  O  O  E  O  H
 O  E  S  O  E  O  O  H      E=Eden  S=Survivor  O=Old  H=Humongous
 E  O  O  S  E  O  O  E
```

**2. Allocation.** Threads bump-allocate inside a TLAB carved from an Eden region. When Eden regions are used up (sized adaptively to meet the pause goal) a **young GC** runs.

**3. Young GC = stop-the-world evacuation.**
- The **collection set (CSet)** = all Eden + Survivor regions.
- Roots (thread stacks, statics, JNI, plus the **remembered sets** of the CSet regions) are scanned; live objects are **copied** into new Survivor regions or promoted to Old once old enough (`MaxTenuringThreshold`, adaptive, not a fixed count).
- References to moved objects are updated; the evacuated source regions go back to the free list. Done in parallel by `ParallelGCThreads` workers.
- Copying compacts as it goes, so G1 has little fragmentation without a separate compaction pass.

```text
before: [Live|Garb|Live]  [Garb|Live| ]      after: Survivor [Live|Live|Live]   source regions: free
object @1000 -> copied to @5000, every reference to it rewritten
```

**4. Remembered sets and cards (why it needn't scan the whole heap).** To collect region B you must know who points *into* B from outside. Each region keeps an **RSet** of incoming references, recorded in units of **cards** (512 bytes). A **post-write barrier** on every reference store marks the card dirty and queues it; **concurrent refinement threads** update RSets. Cost: extra write-barrier overhead and RSet memory (typically 5-20% of heap), the main reason G1 is a bit slower on raw throughput than Parallel.

**5. Concurrent marking cycle (for old regions).** When heap occupancy passes the **IHOP** (`InitiatingHeapOccupancyPercent`, 45% default, adaptive in 9+):
1. *Initial mark* (STW, piggybacks on a young GC) - mark roots.
2. *Root region scan* + *concurrent mark* - trace the object graph with the app running, using **SATB** (snapshot-at-the-beginning) so objects dropped during marking are still accounted for.
3. *Remark* (short STW) - finish SATB buffers, process references.
4. *Cleanup* - count live bytes per region, free fully empty ones, rank the rest by **reclaimable garbage**.

**6. Mixed GCs.** After marking, G1 runs several **mixed** collections: CSet = young regions **plus a slice of the most garbage-rich old regions**, chosen so the predicted pause fits `-XX:MaxGCPauseMillis` (default **200 ms**, a goal not a guarantee). Old regions above `G1MixedGCLiveThresholdPercent` (85% live) are skipped as not worth the copy cost; the phase ends when reclaimable garbage falls under `G1HeapWastePercent` (5%). Then back to **young-only**.

```text
young-only (young GCs, old fills)  ->  concurrent mark  ->  space-reclamation (mixed GCs)  ->  repeat
```

**7. Humongous objects.** Size **>= half a region** -> allocated directly in contiguous Old-type regions, never copied during evacuation; reclaimed at the end of marking, or *eagerly* during a young GC if nothing references them. A stream of large `byte[]`/big JSON/`ArrayList` growth causes fragmentation, early marking cycles and even Full GC: fix by raising `G1HeapRegionSize`, streaming instead of buffering, or pre-sizing.

**8. When G1 falls over.**
- **To-space exhausted / evacuation failure**: no free region to copy into (allocation faster than reclamation, or heap too small) -> expensive recovery and then a **Full GC** (parallel since JDK 10, but still a long pause).
- **Full GC** triggers: allocation failure without free regions, humongous allocation failure, explicit `System.gc()`, metaspace threshold. Red flag in logs: repeated `Pause Full`.
- Likely causes: heap undersized, leak (old gen after GC rising), IHOP too high so marking starts too late, humongous churn. Fix the cause before tuning flags.

**9. Tuning order.** Right-size the heap (and `MaxRAMPercentage` in containers) -> set a realistic `MaxGCPauseMillis` -> fix humongous allocation -> only then touch IHOP / region size. Don't set `-Xmn`/`NewSize`: it disables G1's adaptive young sizing and its pause-goal logic.

**Terms to recite:** Region, Eden/Survivor/Old/Humongous, Collection Set, Remembered Set + cards, Evacuation, SATB concurrent marking, Mixed GC, IHOP, Full GC.
**Memory trick:** *Regions -> Roots -> RSets -> Marking -> Evacuation.*

**Spoken answer (about 60 seconds):**
> "G1 splits the heap into equal-sized regions that are logically Eden, Survivor, Old or Humongous, instead of two contiguous generations. Allocation goes to Eden; when it fills, a young GC evacuates the live objects from the chosen regions into survivor or old regions in parallel, updating references, and uses remembered sets so it never has to scan the whole heap to find pointers into those regions. When heap occupancy crosses a threshold, it runs a mostly concurrent marking cycle to measure how much live data each old region holds, and then runs mixed collections that add the most garbage-heavy old regions to the young ones, as many as fit the pause target, 200 ms by default. So it's a pause-time-goal collector that picks regions by payoff. It became the default in Java 9, replacing Parallel. It can still hit evacuation failure and a Full GC when the heap is undersized or humongous allocations churn, so in production I watch GC logs for those rather than tuning flags blindly, and I reach for ZGC only when I need sub-10 ms pauses on large heaps."

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
