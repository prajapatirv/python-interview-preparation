---
id: cpu-memory
title: Using CPU and memory efficiently
stack: java
skill: performance
---
Interview feedback focus: **using CPU and memory efficiently.** The answers move from symptom to evidence to
fix, with the JVM tools named where they help. JVM facts are for Java 17/21 unless stated.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What lives on the heap and what lives on the stack, and what kinds of OutOfMemoryError are there?
tags: heap, stack, memory-model, outofmemoryerror, basics

**The live scenario**
A service crashed with `java.lang.OutOfMemoryError: Metaspace` after weeks of hot-redeploys, and the team kept raising `-Xmx`, which didn't help.

**What the interviewer is really checking**
That you know the JVM's memory areas and read the OOM message before reacting.

**How I answer it**
1. **Stack (per thread):** method frames, local primitives and references. Too deep recursion gives `StackOverflowError`.
2. **Heap (shared):** all objects and arrays, managed by the garbage collector, sized by `-Xms`/`-Xmx` (or `-XX:MaxRAMPercentage` in containers).
3. **Outside the heap:** Metaspace (class metadata), thread stacks, direct ByteBuffers, the code cache, GC structures. A container's memory limit must cover heap **plus** all of these.
4. **Read the message:**
   - `Java heap space`: too many live objects (a leak or an undersized heap);
   - `GC overhead limit exceeded`: the JVM spends almost all its time collecting;
   - `Metaspace`: class-loader leak (our hot-redeploy case);
   - `unable to create native thread`: too many threads;
   - `Direct buffer memory`: off-heap buffers.
5. In our case raising `-Xmx` couldn't help: Metaspace is separate. Fixing the class-loader leak (a static reference holding the old deployment) did.

**Trade-offs and what can go wrong**
A huge heap means longer GC work and less memory for everything else in the container.

**How I'd monitor it**
Heap used after GC, Metaspace usage, thread count and direct-buffer usage (Micrometer JVM metrics).

**60-second answer**
The stack is per thread and holds method frames and local variables; the heap is shared and holds objects, managed by the GC. Outside the heap there's Metaspace, thread stacks, direct buffers and the code cache, and a container limit must cover all of them. I always read which OutOfMemoryError it is — heap space, GC overhead, Metaspace, native threads or direct memory — because each has a different cause; I've seen a team raise -Xmx for a Metaspace leak, which can't help.

### Q2 [mid] Production CPU is at 100% on one service. How do you find the cause?
tags: high-cpu, jstack, async-profiler, jfr, thread-dump, troubleshooting

**The live scenario**
After a release, a search service's pods went to 100% CPU, latency tripled, and autoscaling added pods that also went to 100%.

**What the interviewer is really checking**
A repeatable method from "CPU high" to "this line of code", using the right tools.

**How I answer it**
1. **Is it our code or the GC?** GC logs or the JVM's GC CPU metric. If GC is burning the CPU, it's really a memory problem (Q3, Q4).
2. **Which threads?** `top -H -p <pid>` shows the hottest OS threads. Convert the thread id to hex and find it in a thread dump (`jcmd <pid> Thread.print`). Take 3–4 dumps a few seconds apart; the same stack each time is your hot spot.
3. **Better: profile.** async-profiler (CPU mode) or a JFR recording for 60 s gives a **flame graph**: the widest frames are where CPU goes. Both are safe to run in production with low overhead.
4. **Common causes we've found:**
   - a regex with catastrophic backtracking on certain inputs (our case: a new validation pattern);
   - an infinite or very long loop on bad data;
   - serialisation of large objects, or excessive logging;
   - busy-spin waits;
   - a CPU-heavy algorithm (O(n²) on a list that grew).
5. **Mitigate first** (roll back the release), then fix: we rewrote the regex without nested quantifiers and added an input length limit.

**Trade-offs and what can go wrong**
Scaling out a CPU bug just multiplies the cost. A single thread dump can mislead — sample several.

**How I'd monitor it**
CPU per pod and **CPU-ms per request**, GC CPU share, and Kubernetes CPU-throttling metrics.

**Follow-ups to expect**
- *CPU is high but no thread looks busy?* -> Check GC threads, and Kubernetes CFS throttling, which shows as latency, not CPU.

**60-second answer**
First I check whether it's GC or our code. Then I find the hot threads with top -H, match them in several thread dumps, or better, take a short async-profiler or JFR recording and read the flame graph — the widest frames are the CPU. Typical causes are catastrophic regex backtracking, loops on bad data, heavy serialisation or logging, or an O(n²) algorithm on data that grew. I roll back first, then fix the code, because autoscaling a CPU bug only multiplies the bill.

### Q3 [mid] Memory keeps growing until the pod is killed. How do you find a memory leak?
tags: memory-leak, heap-dump, eclipse-mat, jcmd, threadlocal

**The live scenario**
A pricing service's heap-after-GC grew from 600 MB to 3.5 GB over four days, then it hit OutOfMemoryError. Restarting "fixed" it every few days.

**What the interviewer is really checking**
Distinguishing a leak from normal usage, and the tooling to find the retaining reference.

**How I answer it**
1. **Confirm it's a leak:** the floor of the heap **after GC** keeps rising over hours or days. A sawtooth that returns to the same floor is healthy.
2. **Capture evidence:**
   - `-XX:+HeapDumpOnOutOfMemoryError` permanently configured to a volume;
   - or `jcmd <pid> GC.heap_dump` on a live pod (it pauses the app — take it from one pod out of rotation);
   - `jcmd <pid> GC.class_histogram` twice, an hour apart, as a cheap first look: the class whose count keeps growing is the suspect.
3. **Analyse** with Eclipse MAT: the *dominator tree* and *leak suspects* show what holds the memory, and *path to GC roots* shows **why** it can't be collected.
4. **Usual causes:**
   - an unbounded static `Map` used as a cache (our case: price lookups keyed by request id, never evicted);
   - `ThreadLocal` values on pooled threads never removed;
   - listeners or callbacks registered and never unregistered;
   - unclosed resources; a growing in-memory queue when consumers fall behind.
5. **Fix and prove:** we replaced the map with a bounded Caffeine cache; a soak test showed a flat floor after 24 h.

**Trade-offs and what can go wrong**
Heap dumps are as big as the heap and contain customer data — treat them as sensitive and store them securely.

**How I'd monitor it**
Heap used after GC (trend), old-gen occupancy, GC frequency, and an alert on a rising floor over 24 h.

**60-second answer**
A leak shows as the heap's post-GC floor rising over time, not a high sawtooth. I capture a heap dump — always on OOM, or with jcmd from a pod out of rotation — and compare class histograms over time. In Eclipse MAT, the dominator tree and path to GC roots show what's holding the memory and why. It's usually an unbounded static cache, ThreadLocals on pooled threads, unremoved listeners or a growing queue. We replaced an unbounded map with a bounded Caffeine cache and proved it with a 24-hour soak.

### Q4 [senior] How do you choose and tune the garbage collector?
tags: gc, g1, zgc, parallel-gc, gc-tuning, pause-time

**The live scenario**
A trading-quote API on G1 with a 16 GB heap had p99.9 spikes of 400 ms that matched GC pauses. A nightly batch job on the same settings ran slower than it needed to.

**What the interviewer is really checking**
That you pick a collector for the workload's goal — pause time vs throughput — and tune by measurement, starting with allocation.

**How I answer it**
1. **Start with the goal:**
   - **G1** (default): balanced; good for most services, with a pause target (`-XX:MaxGCPauseMillis`, default 200 ms);
   - **ZGC**: sub-millisecond pauses even with big heaps — generational ZGC since Java 21, and the default ZGC mode since Java 23 — for latency-critical services, at some throughput and memory cost;
   - **Parallel GC**: maximum throughput, long pauses acceptable — batch jobs.

   For the quote API we moved to generational ZGC; the 400 ms spikes disappeared. The batch job moved to Parallel GC and ran 15% faster.
2. **Before flags, reduce allocation.** Less garbage means less GC work with any collector (Q6).
3. **Size the heap from the live set:** enough headroom that the old generation isn't constantly near full; set `-Xms` = `-Xmx` in containers to avoid resizing.
4. **Measure with GC logs** (`-Xlog:gc*`) analysed in a tool like GCeasy, or JFR: pause percentiles, frequency, allocation rate, promotion rate.
5. **Change one thing at a time** and compare under the same load.

**Trade-offs and what can go wrong**
Copying flags from blog posts; tuning pause targets so low that G1 runs constantly; a heap so large that the container is OOM-killed by native memory.

**How I'd monitor it**
GC pause p99/max, GC CPU share, allocation rate, and heap-after-GC trend.

**Follow-ups to expect**
- *Minor vs major vs full GC?* -> Minor collects the young generation; major/mixed includes old regions; a full GC is a whole-heap, usually stop-the-world fallback you want to never see.

**60-second answer**
I choose the collector by goal: G1 by default, generational ZGC when tail latency matters — it removed 400 ms pauses on one API — and Parallel GC for throughput-only batch work. Before touching flags I reduce allocation, size the heap from the live set, and set -Xms equal to -Xmx in containers. I measure with GC logs or JFR — pause percentiles, allocation and promotion rates — and change one thing at a time under the same load.

**Minimal config**
```text
-XX:+UseZGC -Xms8g -Xmx8g -Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m
```

### Q5 [senior] The JVM runs in Kubernetes. How do you get CPU and memory right in containers?
tags: kubernetes, containers, maxrampercentage, cpu-throttling, oomkilled, native-memory

**The live scenario**
Pods were OOMKilled by Kubernetes with no Java OutOfMemoryError in the logs. Separately, a service with a 1-CPU limit had good average CPU but p99 spikes every few seconds.

**What the interviewer is really checking**
The JVM-container interaction: memory beyond the heap, and CPU throttling.

**How I answer it**
1. **OOMKilled vs OutOfMemoryError:** OOMKilled means the *container* exceeded its memory limit — the kernel killed the process. The JVM never saw it. Heap plus Metaspace, thread stacks, direct buffers and code cache exceeded the limit.
2. **Memory sizing:**
   - set the heap as a share of the container: `-XX:MaxRAMPercentage=70–75`, not the 25% default, and not 100%;
   - leave room for native memory;
   - measure it with **Native Memory Tracking** (`-XX:NativeMemoryTracking=summary`, then `jcmd <pid> VM.native_memory summary`).
3. **CPU limits and throttling:** with a CPU limit, the kernel's CFS quota throttles the pod for the rest of each 100 ms period once it's used up. GC threads and JIT bursts burn the quota, and requests stall — our p99 spikes. Options:
   - raise or remove the CPU *limit* while keeping a sensible *request*;
   - make the JVM see the right CPU count (`-XX:ActiveProcessorCount`) so GC and pool sizes fit;
   - avoid a single CPU for latency-sensitive JVMs.
4. **Right-size from data:** requests set to the observed p95 usage, limits with headroom, and verify throttling metrics after changes.

**Trade-offs and what can go wrong**
Removing CPU limits risks noisy neighbours; keep accurate requests so scheduling stays fair. Too-small pods spend a big share on JVM overhead.

**How I'd monitor it**
`container_cpu_cfs_throttled_periods_total`, container memory working set vs limit, OOMKilled restarts, heap and native memory.

**60-second answer**
OOMKilled means the container limit was exceeded, usually by native memory on top of the heap, so I size the heap at about 70–75% of the container with MaxRAMPercentage and measure the rest with Native Memory Tracking. For CPU, a limit causes CFS throttling — GC and JIT bursts use the quota and requests stall — which shows as p99 spikes, not high CPU. I keep accurate requests, relax limits for latency-sensitive services, align the JVM's processor count, and watch throttling metrics.

**Minimal config**
```text
-XX:MaxRAMPercentage=75 -XX:+ExitOnOutOfMemoryError -XX:+HeapDumpOnOutOfMemoryError
```

### Q6 [senior] How do you reduce object allocation and churn in a hot path?
tags: allocation, gc-pressure, boxing, strings, jfr, hot-path

**The live scenario**
An event-enrichment service allocated about 2 GB/s. GC took 25% of CPU. A JFR allocation profile pointed at a few lines in the per-event loop.

**What the interviewer is really checking**
That you know where Java code allocates without it being obvious, and that you measure before optimising.

**How I answer it**
1. **Measure allocation first:** JFR (`jdk.ObjectAllocationSample`) or async-profiler in allocation mode shows which stack traces allocate the most bytes.
2. **Typical hidden allocations we fixed:**
   - **boxing:** `Map<Long, Integer>` counters and `List<Integer>` in hot loops; switched to primitive arrays or a primitive-collection library;
   - **string building:** `+` in loops and `String.format` per event; replaced with a reused `StringBuilder` or pre-built keys;
   - **logging:** `log.debug("x=" + obj)` builds the string even when debug is off; use parameterised logging;
   - **streams in tiny hot loops:** a stream pipeline per event allocates lambdas, spliterators and boxes; a plain loop is cheaper there;
   - re-parsing the same JSON or date formats; creating `ObjectMapper`/`Pattern` per call instead of once.
3. **Don't over-correct:** object pooling is rarely worth it on modern GCs (short-lived objects are cheap); fix the big allocators the profile shows, not every `new`.
4. **Result:** allocation fell from 2 GB/s to 400 MB/s, GC CPU from 25% to 5%, and we cut two pods.

**Trade-offs and what can go wrong**
Micro-optimisations make code harder to read; apply them only where the profile proves a hot path.

**How I'd monitor it**
Allocation rate, GC CPU share and young-GC frequency, before and after.

**60-second answer**
I measure allocation with JFR or async-profiler before changing anything. The usual hidden allocators in hot paths are boxing in collections, string concatenation and String.format, eagerly-built log messages, stream pipelines per event, and creating ObjectMappers or regex Patterns per call. I fix only what the profile shows — pooling is rarely worth it now. In one service that cut allocation from 2 GB/s to 400 MB/s and GC CPU from 25% to 5%.

### Q7 [senior] How do data-structure choices affect memory and CPU?
tags: collections, memory-footprint, hashmap, arraylist, data-structures

**The live scenario**
An in-memory reference-data service held 20 million small objects in `HashMap<String, Product>` and needed a 12 GB heap. Lookups were fine, but GC pauses and pod cost were not.

**What the interviewer is really checking**
Awareness of per-object overhead and choosing structures by access pattern.

**How I answer it**
1. **Every object has overhead:** an object header (about 12–16 bytes on 64-bit with compressed pointers), padding, and a reference for each field. A `HashMap` entry is its own object, and a boxed `Long` key is another — so a tiny value can cost 50–80 bytes.
2. **Choose by access pattern:**
   - `ArrayList` over `LinkedList` almost always (contiguous memory, cache-friendly; `LinkedList` nodes cost a lot and are slow to traverse);
   - `ArrayDeque` for queues and stacks;
   - `EnumMap`/`EnumSet` for enum keys;
   - **presize** `HashMap`/`ArrayList` when the size is known, to avoid repeated resizing.
3. **Compact the data:** we replaced 20 million objects with column-style primitive arrays plus an index, and interned repeated strings (country codes). Heap went from 12 GB to 3.5 GB. Java 9's compact strings already store Latin-1 text in one byte per character.
4. **Ask if it must be in memory at all:** a Redis or embedded store, or memory-mapped files, for large reference data.

**Trade-offs and what can go wrong**
Compact representations are less readable; encapsulate them behind a clean API. Interning everything can backfire.

**How I'd monitor it**
Heap after GC, GC pause time, and object counts from class histograms.

**60-second answer**
Every Java object carries header and padding, and a HashMap entry with boxed keys can cost 50–80 bytes for a small value, so structure choice matters at scale. I pick by access pattern — ArrayList over LinkedList, ArrayDeque, EnumMap, presized maps — and for huge datasets I compact into primitive arrays with an index and deduplicate repeated strings. That took one service from a 12 GB heap to 3.5 GB. And sometimes the right answer is not keeping it in heap at all.

### Q8 [mid] How many threads should a service use, and how do threads waste CPU?
tags: threads, thread-pools, context-switching, cpu-bound, io-bound, forkjoin

**The live scenario**
A report service created a new 50-thread pool per request. Under load it had 4,000 threads on an 8-core pod; CPU was high but throughput was low.

**What the interviewer is really checking**
Sizing pools by workload type and knowing the cost of too many threads.

**How I answer it**
1. **CPU-bound work:** about one thread per core (`Runtime.availableProcessors()`); more threads just take turns, adding context switches and cache misses.
2. **I/O-bound work:** threads ≈ cores × (1 + wait time / compute time). If a task waits 90 ms and computes 10 ms, about 10 threads per core keep the CPU busy. Or use virtual threads for blocking I/O.
3. **Pools are shared, long-lived and bounded:** create them once (beans), with bounded queues and a rejection policy. A pool per request is a thread leak waiting to happen; that was our case.
4. **Don't put blocking I/O on the common ForkJoin pool**, which `parallelStream()` and default `CompletableFuture.supplyAsync` use; it's sized for CPU work and shared by the whole JVM.
5. **Parallel streams** only help CPU-heavy work on large collections; for small collections or I/O, they make things slower.
6. Fixing the pool-per-request bug: 4,000 threads became 64, CPU dropped by 40%, and throughput doubled.

**Trade-offs and what can go wrong**
Unbounded queues hide overload until memory runs out; unbounded pools exhaust native memory.

**How I'd monitor it**
Live thread count, pool active/queue size, rejected tasks, and context-switch rate.

**60-second answer**
For CPU-bound work, about one thread per core; for I/O-bound work, scale by the wait-to-compute ratio, or use virtual threads. Pools must be created once, bounded, and have a rejection policy. Blocking calls must stay off the common ForkJoin pool that parallel streams and supplyAsync use. I've seen a pool-per-request bug create 4,000 threads on 8 cores; fixing it cut CPU 40% and doubled throughput.

### Q9 [senior] Your in-memory cache is eating the heap. How do you cache without hurting memory?
tags: caching, caffeine, bounded-cache, soft-references, off-heap

**The live scenario**
A local cache of customer profiles grew to 5 GB because entries never expired. GC pauses grew, and a deploy with a cold cache caused a database spike.

**What the interviewer is really checking**
Bounded caching, eviction policy choice, and when to move the cache out of the heap.

**How I answer it**
1. **Always bound it:** Caffeine with `maximumSize` or `maximumWeight` (by approximate bytes) plus `expireAfterWrite`. Caffeine's W-TinyLFU eviction keeps a high hit ratio for its size.
2. **Size it from the hit-ratio curve:** often the top 5% of keys give 80–90% of hits. A cache 10x smaller with a 2% lower hit ratio is usually the better trade.
3. **Avoid soft references as a cache strategy:** the GC clears them under pressure, all at once, causing unpredictable latency.
4. **Move big or shared caches out of the heap:** Redis, or an off-heap cache, when the cache is large, shared across pods, or must survive deploys.
5. **Warm-up:** pre-load the hottest keys at startup or keep a distributed tier, so deploys don't stampede the database.
6. Result: a 300 MB bounded cache kept a 94% hit ratio (versus 97% at 5 GB), and GC pauses returned to normal.

**Trade-offs and what can go wrong**
A weight-based bound needs an honest weigher; an underestimated weigher still exhausts the heap.

**How I'd monitor it**
Hit ratio, eviction count, estimated cache size, heap after GC, and DB load after deploys.

**60-second answer**
A cache must be bounded — I use Caffeine with a size or weight limit plus expiry — and sized from the hit-ratio curve, because a small cache usually captures most of the hits. I avoid soft references, which the GC clears all at once, and move large or shared caches to Redis or off-heap. In one service a 300 MB bounded cache kept 94% of hits that previously took 5 GB of heap.

### Q10 [architect] Cloud costs for your Java services are too high. How do you make them more efficient?
tags: cost, right-sizing, efficiency, cpu-per-request, autoscaling

**The live scenario**
Finance asked us to cut compute cost for 40 Java services by 30% without hurting SLOs. Average CPU utilisation was 12%.

**What the interviewer is really checking**
Efficiency as a measurable engineering goal, and the order of the levers.

**How I answer it**
1. **Measure efficiency per unit of work:** CPU-ms and MB per request (or per message), per service. This finds the outliers worth fixing.
2. **Right-size first (cheap, big win):** CPU and memory requests set from actual p95 usage plus headroom, not guesses. 12% average utilisation means we pay for ~8x what we use.
3. **Autoscale on the right signal** (requests per pod, Kafka lag) with sensible minimums, and scale down out of hours where traffic allows.
4. **Fix the top offenders' code:** profile the five most expensive services — allocation churn, N+1 queries, chatty logging, serialisation. These often give 20–50% each.
5. **Platform levers:**
   - fewer, larger pods (less per-JVM overhead);
   - newer JDK versions (GC and JIT improvements are free gains);
   - ARM instances where libraries allow;
   - AppCDS or CRaC for faster startup, which makes scaling down safer.
6. **Guard it:** cost per request on dashboards and alerts on regressions, so savings don't erode.
7. We reached 34% savings: 20% from right-sizing, 10% from fixing two services' code, 4% from instance types.

**Trade-offs and what can go wrong**
Cutting headroom too far breaks SLOs during spikes and zone failures. Keep the SLO as the constraint.

**How I'd monitor it**
Cost per service, CPU-ms per request, utilisation vs requests, and SLO compliance after each change.

**60-second answer**
I measure efficiency per unit of work — CPU and memory per request — then take the levers in order: right-size requests from real usage, since 12% utilisation means paying for much more than we use; autoscale on meaningful signals; profile and fix the most expensive services; then platform wins like newer JDKs, fewer larger pods and ARM. We cut 34% while holding SLOs, and cost per request now has its own regression alert.

### Q11 [senior] You must process millions of database rows or a 50 GB file without running out of memory. How?
tags: streaming, batching, bounded-memory, jdbc-fetch-size, backpressure

**The live scenario**
A nightly export loaded 8 million rows with `findAll()` into a `List`, then built the CSV in memory. It needed a 24 GB heap and still crashed as data grew.

**What the interviewer is really checking**
Constant-memory processing: streaming, batching and back-pressure.

**How I answer it**
1. **Stream, don't collect:**
   - JDBC with a fetch size (`setFetchSize(1000)`) so rows arrive in chunks;
   - Spring Data's `Stream<T>` query methods inside a read-only transaction, or keyset-paginated batches;
   - write each row to an output stream (CSV or object-storage multipart upload) as you go.
2. **Detach as you go:** with JPA, clear the persistence context per batch, or use plain JDBC/projections for exports; otherwise the first-level cache holds every entity.
3. **For files:** read line by line or with a streaming parser (Jackson streaming, StAX), never `readAllBytes`.
4. **Batch writes** (e.g. 1,000 rows per insert) with periodic commits, so a failure restarts from the last checkpoint, not from zero.
5. **Back-pressure:** a bounded queue between reader and workers, so a fast reader can't fill the heap.
6. **Parallelise by partition** (ranges of ids or file chunks), each in constant memory.
7. The export now runs in a 1 GB heap regardless of row count, and takes 25 minutes instead of 2 hours.

**Trade-offs and what can go wrong**
Long-running read transactions can hold locks or snapshots; run exports from a read replica.

**How I'd monitor it**
Heap stays flat during the job, rows/s throughput, checkpoint progress, and job duration trend.

**60-second answer**
I process in constant memory: stream rows with a JDBC fetch size or keyset batches, write each row straight to the output, clear the persistence context per batch, and use streaming parsers for files. Writes are batched with checkpoints so failures resume, a bounded queue gives back-pressure, and I parallelise by id range. One export went from a 24 GB heap that kept crashing to a flat 1 GB, and from 2 hours to 25 minutes.
