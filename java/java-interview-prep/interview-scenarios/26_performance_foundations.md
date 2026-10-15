---
id: foundations-performance
title: Performance engineering: from the basics (drafted)
stack: java
skill: performance
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] Describe JVM memory areas.
tags: jvm, memory, heap, metaspace, thread-stack, outofmemoryerror, basics

**Start here: the concepts**
- **JVM**: the program that runs your Java code. It asks the operating system (OS) for memory and divides it into areas, each with a different job.
- **Heap**: the area where every object you create with `new` lives. The garbage collector (GC) frees objects nothing refers to any more. Its size is capped by `-Xmx`.
- **Young generation**: the part of the heap for new objects. Most objects die quickly, so cleaning this part is cheap and frequent.
  - **Eden**: where new objects are first placed.
  - **Survivor spaces**: where objects that survived a cleanup wait before being promoted.
- **Old generation**: where long-lived objects end up. Cleaning it is rarer and more expensive.
- **Metaspace**: holds class metadata (what the JVM knows about each loaded class: methods, fields). It lives in native memory, meaning memory outside the heap that the OS gives the process. It replaced PermGen in Java 8 and grows as needed unless `-XX:MaxMetaspaceSize` caps it.
- **Thread stack**: private memory per thread. It holds method calls and local variables. Its size is set by `-Xss`, and it is also native memory.
- **Code cache**: native memory where the JIT compiler stores the machine code it generates for hot methods. JIT means just-in-time compilation: the JVM translates frequently used bytecode into faster machine code while the program runs.
- **Direct buffers**: memory allocated outside the heap (for example by `ByteBuffer.allocateDirect`, and used by libraries such as Netty) so that network and file I/O can avoid an extra copy. Capped by `-XX:MaxDirectMemorySize`.

**The live scenario**
A Spring Boot service runs in a Kubernetes pod with a 2 GB limit and `-Xmx1536m`. At peak (about 800 requests/s) the pod is killed every few hours with status `OOMKilled`. The Java logs show no `OutOfMemoryError`, and the heap graph peaks at only 1.2 GB. The cause: the heap is not the whole process. Roughly 1.2 GB heap + 150 MB metaspace + 300 threads × 1 MB stacks + 100 MB code cache + 200 MB direct buffers is about 1.95 GB, plus the JVM's own overhead. That exceeds 2 GB, so the OS killed the process. Setting the heap to about 60% of the container memory (`-XX:MaxRAMPercentage=60`) left room for the other areas, and the restarts stopped.

**What the interviewer is really checking**
Whether you know the JVM uses more memory than the heap, and whether you can match an error message to the right area.

**How I answer it**
1. **Split memory into heap and non-heap.** The heap holds objects and is managed by the GC. Non-heap (metaspace, stacks, code cache, direct buffers) is native memory. This split matters because the process's real size is the sum of both.
2. **Describe the heap.** New objects start in eden. Survivors of a young cleanup move through survivor spaces and eventually to old. This works because most objects die young, so cleaning a small young area is cheap.
3. **Describe each non-heap area.** Metaspace stores class metadata, stacks store each thread's calls, the code cache stores JIT output, and direct buffers speed up I/O.
4. **Match errors to areas.** The message after `OutOfMemoryError` names the area:
   - `Java heap space`: too many live objects, or a leak.
   - `Metaspace`: too many classes loaded, often a classloader leak or repeated redeploys.
   - `unable to create native thread`: the OS or container could not give another thread stack, so there are too many threads or too little native memory.
   - `Direct buffer memory`: the direct buffer limit was reached.
5. **Mention the container case.** If the pod shows `OOMKilled` with no Java error, the OS killed the whole process because total memory (heap plus native) was too high.

**Trade-offs and what can go wrong**
- A bigger heap does not fix native-memory problems. It can make them worse, because it leaves less room for the rest.
- Capping metaspace or direct memory gives a clear error early. Leaving them uncapped lets the OS kill the pod instead.
- More threads means more stack memory. Setting `-Xss` too small risks `StackOverflowError` in deep recursion.
- A full code cache makes the JVM stop compiling, so the app becomes slower (the log says "CodeCache is full").

**How I'd monitor it**
- Micrometer metrics `jvm.memory.used` and `jvm.memory.max`, split by area (heap, metaspace, code cache), plus `jvm.threads.live`.
- GC logs and `jstat -gc <pid>` for young and old usage.
- Native memory: start with `-XX:NativeMemoryTracking=summary`, then run `jcmd <pid> VM.native_memory summary`.
- Alert on container memory (working set) close to the limit, and search logs for `OutOfMemoryError` to see which message appears.

**Follow-ups to expect**
- *What replaced PermGen?* -> Metaspace in Java 8. It uses native memory, so it can grow until the OS limit unless capped.
- *Are thread stacks part of the heap?* -> No. They are native memory, one per thread, sized by `-Xss`.
- *Why can a pod be OOMKilled without a Java OutOfMemoryError?* -> The OS counts heap plus native memory. When the total passes the container limit, the process is killed before Java can report anything.

**60-second answer**
The JVM splits memory into the heap and non-heap areas. The heap holds all objects. It has a young part (eden and survivor spaces) for new objects and an old part for long-lived ones, and the garbage collector cleans it. Outside the heap there is metaspace for class metadata, a stack for each thread, the code cache for JIT-compiled code, and direct buffers for fast I/O. The error message tells you where the problem is: "Java heap space" is the heap, "Metaspace" is class metadata, "unable to create native thread" is thread or native memory limits, and "Direct buffer memory" is the direct buffers. In containers, the heap is only part of the total, so I size it at about 60% of the memory limit to leave room for the rest.

### Q2 [fresher] What is garbage collection and what are GC roots?
tags: garbage-collection, gc-roots, heap, reachability, memory-leak, jvm, basics

**Start here: the concepts**
- **Heap:** the area of memory where Java stores objects created with `new`. It is finite, so unused objects must be removed or the program runs out of space.
- **Garbage collection (GC):** the JVM automatically finds objects the program can no longer use and frees their memory. You don't call `free()` yourself, which prevents a whole class of bugs.
- **Reference:** a variable that points to an object. If nothing points to an object, nobody can ever use it again.
- **Reachable:** an object is reachable if you can get to it by starting at a known starting point and following references. GC keeps reachable objects and reclaims the rest. This is not reference counting, so two dead objects pointing at each other are still collected.
- **GC roots:** the fixed starting points of that search. They are things the JVM knows are alive:
  - local variables and method parameters on **thread stacks**
  - **active threads** themselves
  - **static fields** of loaded classes (classes are kept alive by their class loader)
  - **JNI references**, which are objects held by native (C/C++) code
  - objects held by the JVM internally, such as monitors used by `synchronized`
- **Memory leak (in Java):** objects that are still reachable but will never be used again. GC cannot tell they are useless, because it only checks reachability, not future use.

**The live scenario**
An order service runs with a 2 GB heap. A developer added a `static Map<String, Customer>` as a quick cache with no eviction. Over 6 hours, heap use after each GC climbed from 800 MB to 1.9 GB. Full GCs started running every few minutes, and p99 latency rose from 120 ms to about 3 s. Then the service threw `OutOfMemoryError: Java heap space` and restarted. The map is reachable from a static field, a GC root, so every entry stayed alive forever. The fix was a size-bounded cache with expiry. After the fix, heap after GC stayed flat near 900 MB and p99 stayed near 120 ms.

**What the interviewer is really checking**
Whether you know that GC works on reachability, not on "will this be used again", and whether you can link that to how leaks happen in a garbage-collected language.

**How I answer it**
1. **Define GC simply:** it frees objects the program can no longer reach. The reason is that manual memory management causes crashes and leaks.
2. **Explain reachability:** GC starts at the roots and follows every reference. Everything it touches is alive, and everything else is garbage. This is why cycles of dead objects are still collected.
3. **List the roots:** thread stacks and locals, active threads, static fields, JNI references, and loaded classes. The reason is that these are the things the JVM must assume are in use.
4. **Connect to leaks:** GC cannot read your intent. An object that is reachable stays alive even if your code will never touch it again. Typical causes are static collections that only grow, listeners never unregistered, and `ThreadLocal` values on pooled threads.
5. **Say how to find the cause:** take a heap dump, open it in Eclipse MAT, and use "path to GC roots" on the biggest objects. That shows which root is holding them.
```
jcmd <pid> GC.heap_dump /tmp/heap.hprof
```

**Trade-offs and what can go wrong**
- GC is not free. Most collectors briefly pause application threads ("stop-the-world") while they work, and a heap filling with live objects makes the pauses longer and more frequent.
- Setting a reference to `null` or "calling System.gc()" is not a fix for a leak. The real fix is removing the path from the root.
- `OutOfMemoryError` inside the JVM is different from a container being killed by the OS (OOMKilled). The first means the Java heap is full. The second means total process memory, including non-heap, exceeded the container limit.
- Weak references let an object be collected even when referenced, which is useful for caches, but they are easy to misuse.

**How I'd monitor it**
- Watch **heap used after GC**. A line that keeps rising over hours means a leak; a saw-tooth that returns to the same floor is healthy.
- Watch GC pause time and frequency (Micrometer/Prometheus `jvm_gc_pause_seconds`, or `jstat -gcutil <pid> 5s`).
- Enable GC logs with `-Xlog:gc*` and search them in Splunk for long pauses.
- Alert when after-GC heap exceeds about 80% of max, and take a heap dump before the crash.

**Follow-ups to expect**
- *Can a Java program have a memory leak even with GC?* -> Yes. If objects are still reachable from a root, such as a static map, GC keeps them even though they are never used.
- *What is a weak reference?* -> A reference that does not keep its object alive. If only weak references remain, GC may reclaim the object.
- *How do you find what is keeping an object alive?* -> Take a heap dump and use MAT's "path to GC roots" to see the chain from a root to the object.

**60-second answer**
Garbage collection is the JVM automatically freeing heap objects that the program can no longer reach. It starts from GC roots, which are always-alive references: local variables on thread stacks, active threads, static fields, JNI references, and loaded classes. It follows every reference from those roots, keeps what it finds, and reclaims the rest. The important point is that GC checks reachability, not whether the code will use an object again. So a static map that only grows is a leak: its entries stay reachable, heap after GC keeps rising, and eventually you get OutOfMemoryError. I'd diagnose it by watching heap after GC, taking a heap dump, and using MAT's path to GC roots to find what holds the objects.

### Q3 [fresher] Stack vs heap?
tags: jvm, memory, stack, heap, garbage-collection, stackoverflowerror, outofmemoryerror, basics

**Start here: the concepts**
- **Memory area:** The JVM splits the memory it uses into regions with different jobs. Stack and heap are the two you meet most often.
- **Thread:** One independent path of execution in your program. A web server runs many threads at once, each handling a different request.
- **Method call and stack frame:** When a method is called, the JVM creates a *frame*, a small block holding that call's parameters, local variables and a few bookkeeping items. When the method returns, the frame is thrown away.
- **Stack:** Each thread has its own stack, a pile of frames. A call pushes a frame on top and a return pops it off. Because it works in this strict last-in, first-out way, it is very fast and needs no cleanup. Since no other thread can touch your stack, locals are naturally thread-safe.
- **Heap:** One big memory area shared by all threads. Every object created with `new` lives here, including arrays, Strings and collections. Objects can outlive the method that created them, which is why they can't live in a frame.
- **Reference:** An "address" pointing to an object. A local variable such as `User u` is only a reference. The reference sits in the stack frame and the `User` object sits on the heap. Primitives like `int` and `double` declared as locals sit directly in the frame.
- **Garbage collection (GC):** The JVM automatically finds heap objects that nothing refers to any more and frees them. The stack needs no GC because frames vanish when methods return.
- **StackOverflowError:** The stack has a fixed size per thread. If calls nest too deeply, usually runaway recursion, it runs out of room.
- **OutOfMemoryError: Java heap space:** The heap is full and GC cannot free enough space.

**The live scenario**
A reporting API loaded 2 million rows into a `List` for each export request. Normally p99 was 200 ms. At month-end, 20 users exported at once, heap use hit the 2 GB limit and GC ran almost continuously. p99 climbed to 6 s and then the pods threw `OutOfMemoryError: Java heap space`. The bug was a heap problem: too many live objects. A week later a different endpoint that walked a deeply nested category tree recursively threw `StackOverflowError` for one customer whose data was about 12,000 levels deep. That was a stack problem: too many nested calls. The two errors have different causes and different fixes.

**What the interviewer is really checking**
Whether you know *what* lives where (locals and references on the stack, objects on the heap), who shares what (stack per thread, heap shared), and whether you can link each area to its typical failure.

**How I answer it**
1. **Say what each one stores.** The stack holds frames with locals, primitives and references. The heap holds the objects those references point to. This matters because `String s = new String("a")` puts only the reference on the stack.
2. **Say who owns it.** Each thread has its own stack, so locals are safe from other threads. The heap is shared, so shared objects need care (synchronisation, immutability).
3. **Say how memory is freed.** Stack memory is freed automatically when a method returns, which is why it is fast. Heap memory is freed later by GC, which costs CPU and can pause work.
4. **Say how each fails.** Deep or infinite recursion gives `StackOverflowError`. Fix it with a base case, a loop, or an explicit stack structure. Too many live objects, or a leak, gives `OutOfMemoryError`. Fix it by streaming or paging data and removing leaked references. Raising the limit only buys time.
5. **Say how you size them.**
```
-Xmx2g     # max heap
-Xss512k   # stack size per thread
```

**Trade-offs and what can go wrong**
- Stack is fast but small and fixed. Heap is large and flexible but needs GC and can pause.
- A larger `-Xss` multiplies across threads. For example, 500 threads at 1 MB each is about 500 MB, and that memory is outside the heap.
- Common mistake: saying "objects are on the heap, so primitives are always on the stack". Primitive *fields* inside an object live inside that object on the heap.
- The JIT compiler can sometimes avoid heap allocation for short-lived objects (escape analysis). Treat that as an optimisation, not a rule to rely on.
- Stack and heap are not the only areas. Class metadata (Metaspace) is separate and also lives outside the heap.

**How I'd monitor it**
- GC logs (`-Xlog:gc`) and `jstat -gcutil <pid>` to see heap fullness and GC frequency.
- Micrometer metrics to Prometheus: `jvm.memory.used`, `jvm.gc.pause`, `jvm.threads.live`.
- `-XX:+HeapDumpOnOutOfMemoryError`, then open the dump in Eclipse MAT to find what holds the memory.
- `jcmd <pid> Thread.print` for stack traces.
- Splunk: search for `StackOverflowError` or `OutOfMemoryError` and chart the count over time.

**Follow-ups to expect**
- *Where do static variables and class metadata live?* -> Class metadata is in Metaspace, outside the heap. Static fields are part of the class's data, and the objects they point to are on the heap.
- *Is a local object always on the heap?* -> Conceptually yes, since the local variable only holds a reference. The JIT may optimise short-lived objects away, but you cannot depend on it.
- *Can stack and heap both be tuned?* -> Yes, with `-Xmx` for heap and `-Xss` for stack size per thread.

**60-second answer**
"The stack is memory owned by a single thread. Every method call adds a frame holding its local variables and references, and the frame disappears when the method returns, so it is fast and needs no GC. The heap is shared by all threads and holds every object created with `new`. A local variable of object type is only a reference on the stack pointing to an object on the heap. The garbage collector frees heap objects that nothing refers to any more. The failures differ. Too-deep recursion gives `StackOverflowError`, and too many live objects or a leak gives `OutOfMemoryError: Java heap space`. I would watch GC logs and heap usage to catch the second, and fix the first with a base case or a loop."

### Q4 [mid] How does generational GC work?
tags: gc, generational-gc, jvm, heap, eden, promotion, basics

**Start here: the concepts**
- **Garbage collection (GC):** the JVM automatically finds objects nothing refers to any more and frees their memory, so you don't call `free()` yourself.
- **Heap:** the memory area where Java objects live. GC works on the heap.
- **Generational hypothesis:** in real programs most objects die very young (a request DTO, a temporary string), and a few live a long time (caches, connection pools). This is why generational GC exists. Scanning only the young objects is cheap and frees most of the garbage.
- **Young generation:** the area for new objects. It has **eden** (where objects are first allocated) and two **survivor spaces**.
- **Minor GC:** a collection of the young generation only. It is stop-the-world, meaning application threads pause. It is usually short because it only copies the few live objects and ignores the dead ones.
- **Aging:** each time an object survives a minor GC it is copied to a survivor space and its age goes up by one.
- **Promotion and old generation:** once an object's age passes a threshold (the JVM adjusts it dynamically), it is moved to the **old generation**. Old gen holds long-lived objects and is collected less often because it is large and expensive to scan.
- **Mixed GC (G1) and full GC:** G1 is the default collector. Its mixed collections clean the young generation plus some old regions. "Mixed" is G1 terminology, and other collectors use different names. A **full GC** collects the whole heap and is the long pause you want to avoid.
- **Premature promotion:** objects that are still short-lived get promoted early, usually because a survivor space is too small to hold them. They then die in old gen, which fills it with garbage.

**The live scenario**
An order service runs a 4 GB heap at about 1,500 rps. Every request allocates roughly 200 KB of temporary objects, so about 300 MB/s. With about 1.5 GB of eden, a minor GC runs every ~5 s and pauses ~15 ms, and p99 is ~180 ms. A release then holds a large per-request payload for ~3 s across async calls. At each minor GC the survivor space overflows and those objects are promoted early. Old gen fills, G1 falls back to a full GC of ~1.8 s, and p99 jumps to ~2.4 s. After the payload is trimmed and the young generation sized properly, pauses drop back to ~20 ms and p99 to ~190 ms.

**What the interviewer is really checking**
Whether you understand why the heap is split by object age. They also want to see that you can connect this to a real symptom, such as premature promotion causing long pauses, and name how you would prove it.

**How I answer it**
1. **Start with the observation:** most objects die young. This is the reason for splitting the heap, since cleaning a small young area often is cheaper than scanning everything.
2. **Allocation:** new objects go into eden, which is fast because the JVM just bumps a pointer.
3. **Minor GC:** when eden is full, the JVM copies the live objects to a survivor space and discards everything else. Copying only live objects is cheap when most are dead.
4. **Aging:** survivors move between the two survivor spaces and their age rises each time. This gives short-lived objects a chance to die in the young generation.
5. **Promotion:** objects past the age threshold, or those that don't fit in the survivor space, go to old gen.
6. **Old gen collection:** it runs less often and is more expensive. In G1 this is mixed collection of selected regions, and full GC is the fallback.
7. **Premature promotion:** survivors that are too small push short-lived objects into old gen. Old gen then fills with garbage and triggers long pauses.

```
-Xlog:gc*:file=gc.log   # first evidence, before touching any sizing flag
```

**Trade-offs and what can go wrong**
- A bigger young generation means fewer minor GCs, but each one may take longer and old gen gets less room.
- Raising the age threshold keeps objects young longer, but copying them repeatedly costs CPU.
- Old objects that point to young ones need extra bookkeeping (card tables) so the young GC stays fast.
- Common mistake: tuning flags before measuring. The usual real fix is to allocate less or shorten object lifetimes.
- Large objects can go straight to old gen (called humongous objects in G1), which also fills it quickly.

**How I'd monitor it**
- GC logs (`-Xlog:gc*`): pause times, and how much heap is freed per collection.
- `jstat -gcutil <pid> 1000`: watch survivor and old gen occupancy.
- Micrometer metrics `jvm.gc.pause` and `jvm.gc.memory.promoted`, with an alert on p99 pause and promotion rate.
- Old gen usage *after* GC: a steady upward trend means a leak or premature promotion.
- JFR allocation profiling to find which code allocates the most.

**Follow-ups to expect**
- *How is G1 different from the classic young/old layout?* -> G1 splits the heap into equal regions and assigns them roles as eden, survivor or old, so it can collect the most garbage-heavy regions first.
- *What does generational ZGC change?* -> Java 21 adds a generational mode (`-XX:+ZGenerational`) that mostly collects concurrently, which keeps pauses very short while still using the young/old idea.
- *How do you fix premature promotion?* -> Confirm it in the GC log, reduce allocation or object lifetime first, and only then resize the young generation or survivor spaces.

**60-second answer**
Generational GC is built on the observation that most objects die young. New objects go into eden. When eden fills, a minor GC copies the few live objects to a survivor space and ages them. After enough survivals they are promoted to old gen, which is collected less often because it is costly to scan. In G1 that old collection is mixed GC, with full GC as the slow fallback. The danger is premature promotion: if survivor space is too small, short-lived objects reach old gen, fill it up, and cause long pauses. I would confirm that from GC logs and promotion metrics, and I would fix it by allocating less first and tuning sizes second.

### Q5 [mid] Which JVM flags do you set for a containerised service?
tags: jvm, containers, kubernetes, memory, gc, heap-dump, observability, basics

**Start here: the concepts**
- **Container memory limit:** Kubernetes gives each pod a memory cap. If the whole process goes over it, the Linux kernel kills the process (status `OOMKilled`, exit code 137). No Java error appears, because the JVM never gets a chance to react.
- **Heap:** the memory area where Java objects live. The JVM sizes it with `-Xmx` (maximum) or as a percentage of available RAM.
- **Non-heap memory:** everything else the process uses. This includes metaspace (class metadata), thread stacks (about 1 MB per thread by default), direct buffers (used by Netty and NIO), the JIT code cache and GC bookkeeping. The pod limit must cover heap plus all of this.
- **`MaxRAMPercentage`:** sets the max heap as a percentage of the container's memory limit. Modern JVMs (Java 10+, and 8u191+) read the cgroup limit, so the heap scales with the pod. The default is only 25%.
- **`OutOfMemoryError` (OOME):** a Java exception thrown when the heap is full. It is different from `OOMKilled`, which is the kernel killing the pod.
- **Heap dump:** a file snapshot of all live objects, used to find leaks (for example in Eclipse MAT).
- **GC log:** a text record of every garbage-collection pause and heap size. It is the evidence for tuning.

**The live scenario**
A service ran in a 2 GiB pod with a hard-coded `-Xmx2g`. Every 4-6 hours the pod restarted with `OOMKilled`. There was no Java stack trace and no heap dump, because the kernel killed it first. The heap alone could grow to the full 2 GiB, leaving nothing for metaspace, about 200 threads (~200 MB) or direct buffers. We switched to `MaxRAMPercentage=70`, which gives a ~1.4 GiB heap and ~600 MB headroom. Restarts stopped. When a real leak later appeared, we got an OOME with a heap dump rather than a silent kill. (Numbers are illustrative.)

**What the interviewer is really checking**
Do you understand that the JVM and the container have separate memory accounting? Can you set flags so failures are visible and self-healing rather than silent?

**How I answer it**
1. **Use `-XX:MaxRAMPercentage=70` instead of a fixed `-Xmx`.** The heap follows the pod limit, so resizing the pod needs no image change. A fixed `-Xmx` can silently exceed the pod limit.
2. **Leave room for non-heap memory.** Heap is roughly 60-70% of total process memory (RSS). Size the pod's request and limit to heap + metaspace + thread stacks + direct memory. Set the memory request equal to the limit so the pod is not evicted under node pressure. On small pods (under ~1 GiB) 70% is too aggressive, so start nearer 50-60%.
3. **Add `-XX:+ExitOnOutOfMemoryError`.** After an OOME the JVM state is unreliable and the service may limp along half-broken. Exiting lets Kubernetes restart it cleanly.
4. **Add `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dumps`.** The dump is written before the exit, which gives you evidence for MAT. Mount `/dumps` as a volume with space at least the heap size, otherwise the file disappears with the container.
5. **Turn on GC logging with rotation**, so logs cannot fill the disk:
```
-Xlog:gc*:file=/logs/gc.log:time,uptime:filecount=5,filesize=20m
```
6. **Check CPU too.** If the JVM sees fewer than 2 CPUs or less than about 1.8 GB, it picks SerialGC rather than G1. Choose the collector deliberately and set CPU requests to match.

**Trade-offs and what can go wrong**
- A percentage that is too high (80%+) brings back `OOMKilled` once threads or direct buffers grow. Too low wastes paid-for RAM.
- A heap dump pauses the JVM and can be several GB. Dumps may also contain sensitive data, so restrict access.
- `ExitOnOutOfMemoryError` with no memory headroom can cause a crash loop. Fix the leak instead of just raising limits.
- CPU limits cause CFS throttling, which shows up as latency spikes that look like GC pauses.

**How I'd monitor it**
- Kubernetes: `OOMKilled` events and restart count, plus container working set vs limit (`container_memory_working_set_bytes`).
- Micrometer/Prometheus: `jvm_memory_used_bytes` by area (heap vs non-heap), `jvm_gc_pause_seconds`, live thread count.
- Native Memory Tracking (`-XX:NativeMemoryTracking=summary`, then `jcmd <pid> VM.native_memory`) to see where non-heap memory goes.
- Splunk: search for `OutOfMemoryError` and GC pauses over 500 ms. Alert when the working set stays above ~85% of the limit.

**Follow-ups to expect**
- *OOMKilled vs OutOfMemoryError?* -> OOMKilled is the kernel killing the whole process for exceeding the pod limit, and Java sees nothing. OOME is the JVM reporting that its own heap is full.
- *Why not just set `-Xmx` equal to the pod limit?* -> The heap is only part of the process memory. Metaspace, stacks and direct buffers push total usage past the limit, and the kernel kills the pod.
- *How would you find a leak from the dump?* -> Open it in MAT, check the dominator tree and "Leak Suspects", and follow the path to GC roots to see what holds the objects.

**60-second answer**
I never hard-code `-Xmx` in containers. I use `-XX:MaxRAMPercentage=70` so the heap follows the pod limit, and I go lower on small pods. Heap is only about 60-70% of what the process uses, because metaspace, thread stacks and direct buffers also count. So I size the pod limit for all of that and set the request equal to the limit. I add `ExitOnOutOfMemoryError` so Kubernetes restarts a broken JVM, plus `HeapDumpOnOutOfMemoryError` to a mounted volume so I have evidence. I also enable rotated GC logging. I watch for `OOMKilled` events, working set vs limit, and GC pause metrics.

### Q6 [mid] A pod gets OOMKilled but heap looks fine. Why?
tags: jvm, memory, oomkilled, kubernetes, native-memory, containers, basics

**Start here: the concepts**
- **Container memory limit:** the maximum RAM Kubernetes lets a pod use (for example 2 GiB). It exists so one pod cannot starve the others on the node. If the pod goes over, the Linux kernel kills the process.
- **OOMKilled:** the status Kubernetes shows when the kernel killed the container for passing that limit. The exit code is 137. The JVM gets no warning, so there is no Java stack trace.
- **`OutOfMemoryError`:** a Java exception thrown by the JVM when it cannot allocate on its own heap. It is a different failure with a different cause, and you will see it in logs.
- **Heap:** the memory area where Java objects live. It is limited by `-Xmx` or `MaxRAMPercentage`, and it is only one part of what the process uses.
- **Non-heap (native) memory:** everything else the JVM process needs.
  - **Metaspace:** class metadata.
  - **Thread stacks:** each thread gets its own, 1 MB by default on 64-bit Linux. Stacks are reserved up front and fill as threads use them.
  - **Direct buffers:** memory allocated outside the heap, used by Netty and NIO for fast I/O.
  - **JIT code cache:** compiled machine code.
  - **Native libraries:** C code that allocates its own memory.
- **`MaxRAMPercentage`:** the share of the container limit the JVM may use for heap. The default is 25%.
- **Native Memory Tracking (NMT):** a JVM feature that reports the JVM's own native memory by category.

**The live scenario**
An order service runs in a pod with a 2 GiB limit and `MaxRAMPercentage=75`, so the heap cap is about 1.5 GiB. Grafana shows heap used at about 900 MB, yet the pod restarts every 6 hours or so. `kubectl describe pod` shows `OOMKilled`, exit code 137. NMT shows about 800 threads, a Netty direct-buffer pool of about 300 MB, metaspace of about 150 MB and a code cache of about 100 MB. Added to a fully grown heap, that is over 2 GiB. (These numbers are illustrative.) After lowering the heap to 60%, capping direct memory and trimming thread pools, the pod's memory stayed near 1.6 GiB with no restarts for two weeks.

**What the interviewer is really checking**
Do you know that the container limit covers the whole process, not just the heap? And can you diagnose native memory with a tool rather than guess?

**How I answer it**
1. **Confirm the failure type.** I look for `OOMKilled` or exit code 137 in `kubectl describe pod`. That means the kernel killed the container, not the JVM throwing `OutOfMemoryError`. The two have different fixes.
2. **Explain the arithmetic.** Container memory is heap plus non-heap. A heap that looks fine can still sit next to hundreds of MB of stacks, buffers, metaspace and code cache. The sum passes the limit.
3. **Measure the non-heap part.** I start the JVM with NMT and ask it for a summary. It adds a small overhead, so I use it for diagnosis rather than leaving it on blindly.
   ```
   -XX:NativeMemoryTracking=summary
   jcmd <pid> VM.native_memory summary
   ```
4. **Lower the heap share.** I reduce `MaxRAMPercentage`, for example from 75 to 60. This leaves more of the limit for native memory.
5. **Cap the other consumers.** I limit thread pools, set `-XX:MaxDirectMemorySize` and set `-Xss` if needed. I check for unbounded class loading.
6. **Re-test under load.** I confirm that the working set stays below the limit with headroom.

**Trade-offs and what can go wrong**
- A smaller heap means more garbage collection (GC) work and possibly a real `OutOfMemoryError`. Check GC pause time and allocation rate after the change.
- Raising the limit only hides a leak or an unbounded pool.
- NMT does not see everything. Memory that native libraries allocate through malloc is invisible to it, and glibc arenas can fragment (`MALLOC_ARENA_MAX` is a common mitigation).
- A heap that looks fine on a "used" graph may be fully committed. Compare committed memory, not just used.

**How I'd monitor it**
- Compare `container_memory_working_set_bytes` against the pod limit, and alert at about 85%.
- Break JVM memory down by area with `jvm_memory_used_bytes` (heap, non-heap).
- Watch `jvm_buffer_memory_used_bytes` (direct buffers) and `jvm_threads_live`.
- Track `kube_pod_container_status_last_terminated_reason{reason="OOMKilled"}` and restart counts.
- In Splunk, search Kubernetes events for `OOMKilled` or exit code 137, grouped by pod over time.

**Follow-ups to expect**
- *How is OOMKilled different from `OutOfMemoryError`?* -> OOMKilled comes from the kernel when the whole container passes its limit, with no Java trace. `OutOfMemoryError` is thrown by the JVM when it cannot allocate on its own heap or metaspace, and it appears in logs.
- *Why not just raise the memory limit?* -> That costs money on every pod and does not fix a growing thread count or buffer pool, so it only delays the next kill.
- *How do you find which native area is growing?* -> Take an NMT baseline with `jcmd VM.native_memory baseline`, then run `summary.diff` later to see which category grew.

**60-second answer**
OOMKilled means the Linux kernel killed the container because the whole process passed its memory limit. It is not a Java `OutOfMemoryError`. The heap is only one part of that memory. Metaspace, thread stacks at about 1 MB each, direct buffers from Netty, the JIT code cache and native libraries all count too. So a healthy-looking heap can still push the pod over the limit. I would enable Native Memory Tracking and run `jcmd VM.native_memory` to see which area is large. Then I would lower `MaxRAMPercentage` to leave room, cap thread pools and direct memory, and re-test under load. I would alert when container memory reaches about 85% of the limit.

### Q7 [mid] How do you read a GC log to see if GC is the problem?
tags: gc, gc-logs, jvm, g1, latency, heap, basics

**Start here: the concepts**
- **Garbage collection (GC):** The JVM automatically frees objects the program no longer uses. It exists so developers don't free memory by hand.
- **Stop-the-world pause:** For some GC phases, all application threads freeze. Requests that arrive during a pause just wait, so pauses show up directly as latency spikes.
- **Young vs Full collection:** Most objects die young, so the JVM cleans the small "young" area often and cheaply (`Pause Young`). A `Pause Full` cleans the whole heap. It is slow and usually means the JVM is in trouble.
- **Heap after GC:** The memory still in use right after a collection, which approximates your live data. It is the most honest measure of memory pressure.
- **G1 terms:** G1 is the default collector in modern JDKs. It splits the heap into regions. A *humongous allocation* is an object at least half a region in size, and it is handled awkwardly. *To-space exhausted* means G1 ran out of free space to copy surviving objects into, and it usually falls back to a Full GC.
- **GC log:** A text file where the JVM records every collection. On Java 9+ you enable it with unified logging. Java 8 uses `-XX:+PrintGCDetails`.

**The live scenario**
A checkout API on a 4 GB heap with G1 normally runs at p99 250 ms. Every 20 minutes or so, p99 jumps to 1.8 s and the SLO alert fires. The GC log shows a `Pause Full` of about 3 s, and heap-after-GC has crept from 1.5 GB to 3.6 GB over six hours. About 12% of wall-clock time is spent in GC. A heap dump shows an unbounded in-memory cache. After adding a size limit and expiry, heap-after-GC stays flat near 1.6 GB, GC time drops to about 1.5%, and p99 returns to 280 ms. (Numbers are illustrative.)

**What the interviewer is really checking**
Whether you prove GC is the cause by lining up GC evidence with latency, rather than guessing, and whether you can tell "GC is slow" from "GC is a symptom of a leak or bad sizing".

**How I answer it**
1. **Make sure the log exists.** Without it you are guessing. Example: `-Xlog:gc*:file=gc.log:time,uptime` (Java 9+).
2. **Check pause time against the SLO.** Find the longest and the p99 pause. If a 500 ms pause happens and your SLO is 300 ms, GC can explain the slow requests. Reason: the application is frozen for the whole pause.
3. **Check frequency and % of time in GC.** Add up pause time over a window. A few percent is healthy. Double digits means the app is spending real capacity on cleanup, not on requests.
4. **Count Full GCs.** Occasional ones are tolerable. Repeated `Pause Full` is a red flag because it means the normal incremental collection cannot keep up.
5. **Look at heap-after-GC over hours.** If the low points trend upward even after Full GCs, live data is growing, which suggests a leak. Compare like with like (after Full or mixed collections), because after-young numbers fluctuate normally.
6. **Search for G1-specific warnings.** `to-space exhausted` and many humongous allocations point to sizing problems or large arrays and buffers that need fixing.
7. **Correlate with request latency by timestamp.** Check whether p99 spikes coincide with the pauses. If they don't, GC is not your problem, so look at the database or downstream calls instead.
8. **Use a tool to see the trends.** GCeasy (a third-party web tool) or JDK Mission Control (JMC) charts the log so patterns are obvious.

**Trade-offs and what can go wrong**
- Don't blame GC from a single scary-looking line. Always check the timing against the latency graph.
- Raising the heap can delay a leak but never fixes it, and bigger heaps can mean longer pauses.
- In containers, an `OOMKilled` pod is a native-memory or limit problem, not necessarily a GC problem, and the GC log won't show it.
- Collector choice matters. Generational ZGC (Java 21) targets very short pauses but uses more CPU.

**How I'd monitor it**
- Micrometer/Prometheus metrics: `jvm_gc_pause_seconds` (count and max) and `jvm_memory_used_bytes` after GC.
- Alerts on GC time ratio and on Full GC count.
- JFR/JMC for allocation hot spots, and a heap dump with MAT if heap-after-GC keeps rising.
- A dashboard overlaying p99 latency and GC pauses.

**Follow-ups to expect**
- *What GC time percentage is acceptable?* -> Aim for a few percent at most. Sustained double digits is a clear problem, and your own SLO decides the exact limit.
- *Heap-after-GC keeps rising. What next?* -> Take a heap dump and open it in MAT to find the largest retained objects, then fix the leak rather than adding memory.
- *Pauses are long but heap is healthy. What then?* -> Tune pause goals, check for humongous objects, or consider generational ZGC if the SLO needs very short pauses.

**60-second answer**
First I make sure GC logging is on. Then I look at three things: how long the pauses are compared to my SLO, how often they happen and what percent of time the JVM spends in GC, and whether the heap after each GC is trending upward. Red flags are repeated Full GCs, to-space exhausted, and humongous allocations in G1. Rising heap-after-GC points to a leak. I then line up the pause timestamps with my p99 latency graph to prove GC is really the cause. I use GCeasy or JDK Mission Control to view the trends, and if it is a leak, I take a heap dump and analyse it in MAT.

### Q8 [senior] What is JIT compilation and warm-up?
tags: jit, warm-up, hotspot, c1-c2, jvm, performance, basics

**Start here: the concepts**
- **Bytecode:** `javac` compiles Java to portable bytecode, not machine code. The JVM must run that bytecode on a real CPU.
- **Interpreter:** It reads bytecode one instruction at a time. It starts instantly but is slow, often many times slower than compiled code.
- **JIT (just-in-time) compiler:** It turns bytecode into native machine code while the program is running. It only does this for code that proves it is used a lot, because compiling costs CPU and time.
- **Hot method:** A method or loop the JVM has seen run many times. HotSpot counts invocations and loop iterations to decide.
- **C1 and C2:** C1 compiles quickly and produces decent code. C2 compiles slowly but produces much faster code, because it uses runtime knowledge. HotSpot uses both in sequence (tiered compilation): interpreter, then C1, then C2 for the hottest code.
- **Inlining:** The compiler copies a small method's body into its caller. This removes call overhead and opens up further optimisations.
- **Escape analysis:** The compiler checks whether an object ever leaves a method. If not, it can avoid allocating it on the heap, which means less garbage.
- **Warm-up:** The period after JVM start when code is still interpreted or only C1-compiled. Latency is high and CPU is busy compiling until the hot paths reach C2.
- **CDS / AppCDS (class data sharing):** An archive of pre-parsed classes that the JVM maps at startup. It reduces class-loading time.
- **Native image (GraalVM):** Ahead-of-time compilation to a standalone executable. It starts fast but has no runtime JIT.

**The live scenario**
An order service normally runs at p99 = 120 ms. During a rolling deploy, Kubernetes marks each new pod ready as soon as the HTTP port opens, about 8 s after start. The pod immediately gets its share of about 400 rps. For roughly the first 60-90 s, that pod's p99 is about 1.8 s and its CPU is near 100% (illustrative numbers). Most of that CPU is the compiler threads. Users see timeouts on every deploy, and autoscaling makes it worse, because each new pod is cold when it joins. Nothing is wrong with the code. The pods were given traffic before they were warm.

**What the interviewer is really checking**
Whether you know the JVM is slow at first by design, and whether you can handle it operationally (readiness, warm-up, startup options) and measure it honestly (JMH).

**How I answer it**
1. **Explain the mechanism.** HotSpot interprets first because compiling everything up front would delay startup. It counts how often code runs and compiles hot methods with C1, then C2. This is why the first seconds or minutes are slow.
2. **Say what C2 adds.** C2 uses runtime profiles to inline and run escape analysis. If an assumption later turns out wrong, the JVM can deoptimise (throw away the compiled code) and recompile. This is why steady-state speed can beat ahead-of-time code.
3. **Protect users with the readiness probe.** Do not report "ready" when the port opens. Report ready after a warm-up phase.
4. **Send warm-up requests.** Replay realistic calls at startup, covering the main endpoints, JSON serialisation and DB paths, so the hot code is compiled before real traffic arrives. Warm-up with unrealistic calls trains the wrong profile.
5. **Cut startup cost with CDS/AppCDS.** This speeds up class loading and startup. It does not skip JIT warm-up, so use it alongside warm-up requests, not instead of them.
6. **Consider native image for serverless or scale-to-zero.** It removes warm-up, but the usual trade-off is lower peak throughput and a harder build. Use it where cold starts dominate, not for long-running services.
7. **Benchmark with JMH.** A `System.currentTimeMillis()` loop mostly measures the interpreter, compilation and dead-code elimination. JMH forks fresh JVMs, runs warm-up iterations, then measures.
```java
@Warmup(iterations = 5) @Measurement(iterations = 5) @Fork(2)
```

**Trade-offs and what can go wrong**
- Longer warm-up delays readiness, so scale-out is slower. Set the probe timeout accordingly.
- Warm-up requests with side effects (writes, emails) are dangerous. Use read-only or test-flagged calls.
- Giving a pod too little CPU (a low container limit) makes compilation compete with requests and prolongs warm-up.
- Benchmarking a cold JVM, or one run that is too short, gives wrong conclusions.
- Native image loses runtime JIT optimisation and some dynamic features, such as reflection without configuration.

**How I'd monitor it**
- Compare p95/p99 by pod uptime (first 2 minutes vs steady state) in Splunk, e.g. `perc99(duration) by pod, uptime_bucket`.
- Alert on error rate or p99 spikes during deploys.
- Run `-XX:+PrintCompilation`, or use JFR compilation events.
- Watch JIT compiler thread CPU, and check the code cache with `jcmd <pid> Compiler.codecache`.
- Track time-to-ready per pod and CPU throttling.

**Follow-ups to expect**
- *Why not compile everything at startup?* -> It would slow startup and waste CPU on code that runs once, and C2 needs runtime profiles to optimise well.
- *Does AppCDS remove warm-up?* -> No. It speeds up class loading and startup. JIT warm-up still happens.
- *What is deoptimisation?* -> The JVM discards compiled code when an assumption fails (e.g. a new subclass appears) and falls back to the interpreter before recompiling.

**60-second answer**
The JVM first interprets bytecode because that starts instantly. It counts how often methods run, then compiles the hot ones with C1, which is quick, and finally C2, which is slower to produce but much faster, using inlining and escape analysis. So a cold JVM is slow for the first seconds or minutes while compilation uses CPU. In production I keep a pod out of rotation with a readiness probe until it has served warm-up requests that cover the real hot paths. I use CDS/AppCDS to speed up startup, and native image only for serverless, accepting lower peak performance. To measure, I use JMH, never a `currentTimeMillis()` loop, and in production I compare p99 by pod uptime.

### Q9 [senior] What is escape analysis?
tags: escape-analysis, jit, scalar-replacement, allocation, gc, basics

**Start here: the concepts**
- **Heap allocation**: `new` normally puts the object on the heap. The garbage collector (GC) later reclaims it. Allocation is fast, but it still costs memory bandwidth and creates GC work.
- **JIT compiler (C2)**: the JVM first interprets your bytecode. For hot methods it compiles optimized machine code at runtime. HotSpot's optimizing compiler is called C2.
- **Escape**: an object "escapes" if code outside the current method, or another thread, can reach it. That happens if you return it, store it in a field or collection, or pass it to code the compiler can't see into.
- **Escape analysis (EA)**: a C2 compile-time check of whether each object escapes. It exists because an object that nobody else can see doesn't need to be a real heap object.
- **Scalar replacement**: the compiler drops the object and keeps its fields as plain local values in registers or stack slots. No heap allocation happens, so there is nothing for GC to clean.
- **Lock elision**: if a lock object never escapes, no other thread can contend for it, so the compiler removes the synchronization.
- **Inlining**: the compiler copies a small called method into its caller. This is what lets EA see that an object never leaves.

**The live scenario**
A pricing API handles 4,000 rps. Each request creates about 50 tiny temporary `Money` and `Point`-style objects. A developer wants to add an object pool "to cut GC". A JMH run with `-prof gc` shows the hot path already allocating about 0 B/op, because C2 scalar-replaced those objects. The pool would only add contention. Later, a refactor made one method too big to inline. The allocation rate rose from roughly 300 MB/s to 1.2 GB/s (illustrative), and young GCs became four times as frequent. EA had silently switched off for that path.

**What the interviewer is really checking**
Whether you know that cheap short-lived objects are a JIT feature with conditions, and whether you measure before optimizing. A senior should also know the common myth: HotSpot does not really put objects on the stack.

**How I answer it**
1. **Define it.** EA proves that an object stays inside one method (or inlined unit) and one thread. The proof is needed because only then is it safe to change how the object lives.
2. **Correct the "stack allocation" wording.** In HotSpot the main result is scalar replacement: the object disappears and its fields become locals. It is not a real object placed on the stack. Lock elision is the other benefit.
3. **Say when it works.** The code must be hot enough for C2 to compile it, and the allocation and its uses must be inlined together. The object must not be returned, stored in a field or collection, or passed to a non-inlined call.
4. **Draw the practical conclusion.** Small temporary objects, such as iterators, builders, records and boxed values in a local loop, are often free. Hand-tuning allocation, with pools or reused mutable objects, is usually pointless and makes code worse.
5. **Prove it, don't assume.** Run a JMH benchmark with `-prof gc` and read `gc.alloc.rate.norm`. Compare against `-XX:-DoEscapeAnalysis` (EA is on by default in C2) to see its effect.

**Trade-offs and what can go wrong**
- EA is best-effort. Big methods, megamorphic calls (many possible targets), or branches that let the object escape on some path can defeat it. HotSpot's C2 has limited partial escape analysis, so one escaping path can keep the allocation.
- It only applies after warm-up. Cold code and the interpreter allocate normally.
- Large objects and arrays are often not eligible.
- Objects that live across requests, such as caches and sessions, always escape. EA does not fix a real allocation problem there.
- Common mistake: reading a microbenchmark that shows 0 allocation and assuming production behaves the same. Real call sites may have different inlining.

**How I'd monitor it**
- JMH `-prof gc` for B/op on the hot path.
- A JFR allocation profile (allocation-sample events) and an async-profiler allocation flame graph, to see which `new` sites really hit the heap.
- Production: allocation rate (MB/s), young GC frequency and pause time from GC logs or Micrometer JVM metrics. Alert on a step change after a release.
- Compare with and without `-XX:-DoEscapeAnalysis` in a test environment.

**Follow-ups to expect**
- *Does Java allocate objects on the stack?* -> Not as real objects in HotSpot. It does scalar replacement, so the fields live in registers or stack slots and the object is never created.
- *Why can a bigger method make an app slower?* -> Inlining limits can stop the callee from being inlined, so objects escape and allocation returns.
- *When would you still reduce allocation?* -> When a profile shows a high allocation rate and GC pressure on a hot path, and the objects truly escape, for example per-request DTOs or large buffers.

**60-second answer**
Escape analysis is a JIT optimization in C2. It checks whether an object can be seen outside the method that created it, or by another thread. If it can't, the JIT can skip the heap allocation through scalar replacement, keeping the fields as plain locals. It can also remove locks on such objects. People often say "allocated on the stack", but in HotSpot the object is really eliminated. This is why small temporary objects are usually cheap, and why hand-optimizing allocation or pooling them is normally pointless. It only works on hot, inlined code where the object never escapes, so a refactor can silently break it. I'd check it with JMH `-prof gc` and with allocation rate and GC logs in production.

### Q10 [mid] How do you profile a slow endpoint?
tags: performance, profiling, jfr, async-profiler, flame-graph, distributed-tracing, basics

**Start here: the concepts**
- **Latency and percentiles:** Latency is how long one request takes. p50 is the time half of requests beat, and p99 is the time 99% beat. Averages hide the slow tail, so we judge an endpoint by p95/p99.
- **Trace and span:** A trace is the timeline of one request across services. Each step (DB call, HTTP call, method) is a span with a start and duration. It tells you *where* the time went, but not *why*.
- **Profiler:** A tool that samples the running program many times per second and records what each thread is doing. Many samples in one method means the time goes there.
- **Flame graph:** A picture of those samples. Each bar is a method, and its width is the share of samples. The widest bars are your suspects.
- **CPU profile vs wall-clock profile:** A CPU profile only counts threads that are running on a core. A wall-clock profile also counts threads that are waiting (on a DB, lock or socket). A slow endpoint with low CPU needs wall-clock.
- **JFR (Java Flight Recorder):** A profiler built into the JVM that records CPU, allocation, locks and GC with low overhead. You open the file in JDK Mission Control. **async-profiler** is a separate sampling profiler that produces flame graphs.
- **Thread dump:** A snapshot of every thread's stack and state, taken with `jcmd <pid> Thread.print`. It shows threads BLOCKED on a lock or waiting for a connection.
- **Slow-query log and `EXPLAIN`:** The database logs queries over a time threshold. `EXPLAIN` shows how the DB runs a query, for example a full table scan instead of using an index.

**The live scenario**
After a release, `GET /orders/{id}/summary` went from p99 300 ms to 2.4 s at about 200 rps. p50 was still 120 ms, so only some requests were slow, and an average chart would have hidden it. CPU was 35%, so the service was waiting, not computing. The trace showed 1.9 s in the DB, split into about 40 tiny SELECT spans, one per order line (the N+1 pattern). The slow-query log showed no single slow query, so the log alone would have missed it. We replaced the per-line lookups with one batched query and re-measured. DB calls per request dropped from 40 to 3, and p99 went from 2.4 s to 380 ms.

**What the interviewer is really checking**
Whether you follow a method (symptom, then evidence, then fix, then re-measure) instead of guessing, and whether you know which tool answers which question.

**How I answer it**
1. **Confirm with percentiles and reproduce.** Look at p95/p99 for that endpoint and at which requests are slow. Profile under realistic load, because a profile on an idle laptop shows different problems.
2. **Open a trace first.** It narrows the problem to a DB span, a remote call span, or time inside our own code. This stops you from profiling CPU when the time is spent waiting.
3. **If the time is in our code, take a CPU flame graph.** Start JFR or async-profiler on the live process for about 60 seconds, e.g. `jcmd <pid> JFR.start duration=60s filename=/tmp/ep.jfr`. Read the widest bars first, because they hold the most samples.
4. **If CPU is low but latency is high, the threads are waiting.** Use async-profiler in wall-clock mode, and take 3 thread dumps a few seconds apart. Threads stuck in the same place each time are blocked there, for example on a lock or a connection pool.
5. **For allocation or GC pressure, use the allocation profile.** It shows which code creates the most objects, which causes frequent GC pauses.
6. **If the DB is the culprit, count queries per request and check the slow-query log.** Run `EXPLAIN` on the suspects. Many small queries means N+1, and a scan means a missing index.
7. **Fix the single biggest cost, then re-measure with the same load.** Fixing the widest bar gives the largest gain. Re-measuring proves it worked and that no new bottleneck appeared.

**Trade-offs and what can go wrong**
- A CPU-only profile of a waiting endpoint looks "fine" and misleads you.
- A single thread dump is noise. Compare several.
- Profilers add overhead and sampling is statistical, so use short windows in production and check the impact.
- Flame graphs can show inlined or JIT-compiled frames that differ from your source, so warm up the app first.
- Optimising a narrow bar is wasted effort, and fixing one bottleneck often exposes the next.

**How I'd monitor it**
- Per-endpoint RED metrics (rate, errors, duration) as Micrometer histograms in Prometheus, with p99 alerts.
- Trace sampling in OpenTelemetry, plus DB queries per request.
- Connection pool metrics such as pending connections, and GC pause time.
- Splunk: `... | stats perc95(duration_ms) perc99(duration_ms) by uri`, to catch regressions right after a release.

**Follow-ups to expect**
- *CPU is low but the endpoint is slow. What now?* -> The threads are waiting. Use wall-clock profiling, thread dumps and the trace to find the DB, lock or pool they wait on.
- *Is it safe to profile production?* -> JFR is designed for low overhead, and async-profiler is generally lightweight, but use short windows and watch the overhead.
- *How do you read a flame graph?* -> Width is the share of samples, and the vertical axis is the call stack. Look for wide bars near the top, since the code that is actually running sits there.

**60-second answer**
I start with percentiles to confirm the endpoint is slow, then open a trace to see which span holds the time: the database, a remote call, or our own code. If it's our code, I take a JFR or async-profiler flame graph and read the widest bars. If CPU is low, I use wall-clock profiling and a few thread dumps with `jcmd <pid> Thread.print` to find blocked threads. If it's the DB, I count queries per request, check the slow-query log and run `EXPLAIN`. I fix the biggest cost first and re-measure under the same load. In one case this took p99 from 2.4 s to 380 ms by removing an N+1 query pattern.

### Q11 [mid] What are common performance anti-patterns in Spring apps?
tags: performance, spring-boot, jpa, hibernate, caching, connection-pool, basics

**Start here: the concepts**
- **Anti-pattern:** a habit that looks fine in a demo but costs a lot of time, CPU or memory under real traffic.
- **N+1 queries:** you run 1 query to load a list (say 50 orders), then 1 more query per row to load a related thing (their items). That is 51 database round trips where 1 or 2 would do. JPA/Hibernate lazy loading causes this quietly.
- **Paging:** asking the database for a slice (for example 50 rows at a time) instead of the whole table. `findAll()` with no `Pageable` loads every row into memory.
- **Entity vs projection:** an entity is a full managed object with all columns, tracked by Hibernate. A projection (a DTO or interface) selects only the columns you need, so it is cheaper.
- **Connection pool:** a fixed set of reusable database connections (HikariCP is Spring Boot's default). Opening a connection is slow, so the pool reuses them.
- **Little's Law:** concurrency = throughput × latency. At 200 requests/s with 50 ms of database time each, about 10 connections are busy at once.
- **Index:** a lookup structure in the database. Without one, a filter scans the whole table.
- **Unbounded cache:** a cache with no size limit or expiry. It grows until the JVM runs out of memory.

**The live scenario**
This is an illustrative story. `GET /orders` returned 50 orders with their items. After launch at 150 requests/s, p99 went from 120 ms to 2.4 s and CPU hit 85%. The SQL log showed 51 queries per request. Hikari showed threads waiting for a connection, and the `orders.customer_id` filter had no index. The team fixed it with a fetch join and a DTO projection, paging and the index. After the fix there were 2 queries per request, p99 was 180 ms and CPU was 40%.

**What the interviewer is really checking**
Whether you can name the common mistakes, explain why each one hurts, and say how you would find it with evidence rather than guessing.

**How I answer it**
1. **Database access comes first, because it is the most common cause.** Fix N+1 with a fetch join or `@EntityGraph`, as in `select o from Order o join fetch o.items`. Never call `findAll()` without paging, and use a projection when the endpoint needs only a few columns. Add indexes on filter and join columns, and confirm them with `EXPLAIN`.
2. **Reduce the work per request.** Independent downstream calls made one after another add their latencies together, so run them in parallel. Huge JSON payloads cost serialisation CPU and network time, so page them, trim fields and enable compression.
3. **Remove waste in hot paths.**
   - Use parameterised logging, and avoid DEBUG in hot paths, because the work of building log strings and writing them costs time even if nobody reads the output.
   - Create `ObjectMapper` once and share it as a bean, because it is expensive to build but thread-safe once configured.
   - `SimpleDateFormat` is not thread-safe, so sharing it is a bug. Use `DateTimeFormatter`, which is immutable.
4. **Bound your resources.** Give every cache a maximum size and a TTL (for example Caffeine). Size the connection pool using Little's Law. Too small and requests queue. Too large and the database thrashes, so a pool of 10-30 is often enough per instance.
5. **Measure first.** Look at p95/p99, query counts per request and pool metrics before changing anything.

**Trade-offs and what can go wrong**
- Fetch joins on several collections multiply rows (a Cartesian product), and combining them with paging forces in-memory paging. Use batch fetching or two queries instead.
- Projections lose entity features such as dirty checking.
- Parallel calls add thread-pool pressure and make error handling harder.
- Caches add stale data and the risk of a stampede (many requests refreshing the same key at once).
- Indexes slow writes and use disk.
- A bigger pool can overload the database instead of helping.

**How I'd monitor it**
- Hibernate statistics or SQL logging in test, to count queries per request.
- Micrometer/Prometheus: `http.server.requests` percentiles, `hikaricp.connections.pending` and `hikaricp.connections.active`, and JVM heap and GC.
- OpenTelemetry traces, to see serial call chains.
- A JFR or async-profiler flame graph for CPU hot spots.
- Splunk: `... | stats perc95(duration) perc99(duration) by endpoint`.
- Alerts on p99 against the SLO, and on pool wait time.

**Follow-ups to expect**
- *How do you detect N+1?* -> Count SQL statements per request in tests or traces. If the count grows with the number of rows, it is N+1.
- *Why is a bigger pool not always better?* -> The database has a limited number of cores and I/O. Past that point more connections just add contention and context switching.
- *Is `ObjectMapper` thread-safe?* -> Yes, once configured. Reuse one instance and do not reconfigure it per request.

**60-second answer**
The most common Spring performance mistakes start with the database: N+1 queries, `findAll()` without paging, loading full entities when a projection would do, and missing indexes. Next are chains of synchronous calls that could run in parallel, huge JSON payloads, and DEBUG logging in hot paths. Then come resource mistakes such as unbounded caches, a connection pool that is too small or too large, and creating `ObjectMapper` or `SimpleDateFormat` per request. `ObjectMapper` should be shared, and `SimpleDateFormat` is not thread-safe, so I use `DateTimeFormatter`. I do not guess. I check p99, queries per request and Hikari pending connections, then fix the biggest cause. In one case, going from 51 queries to 2 cut p99 from 2.4 s to 180 ms.

### Q12 [senior] How do you size the DB connection pool (HikariCP)?
tags: hikaricp, connection-pool, jdbc, spring-boot, performance, virtual-threads, basics

**Start here: the concepts**
- **Database connection:** A live session between your app and the database. Opening one is slow (network handshake, login, session setup), and the database spends memory and a process or thread on each.
- **Connection pool (HikariCP):** A fixed set of already-open connections that threads borrow and return. It exists to avoid paying the open cost on every request. HikariCP is the default pool in Spring Boot.
- **Pool size (`maximumPoolSize`):** The maximum number of connections the pool holds. If all are in use, the next thread waits in a queue.
- **Pending threads:** Threads waiting for a free connection. A growing count means the pool is a bottleneck.
- **`max_connections`:** The database's own hard limit across all clients. Beyond it, new connections are refused.
- **Spindles:** Physical disk heads. The formula comes from spinning-disk days and matters little on SSDs.
- **Little's Law:** Average concurrency = throughput × time each request holds the resource. It tells you how many connections you really need.
- **Virtual threads (Java 21):** Very cheap threads. You can have tens of thousands, so many can queue for a small pool.

**The live scenario**
A service ran 10 pods, each with a pool of 30, against a PostgreSQL server with 8 cores and `max_connections` = 200 (illustrative numbers). At normal load it was fine. During a sale, autoscaling went to 15 pods, which meant 450 requested connections. The database refused connections ("too many connections"), and p99 latency went from 200 ms to 900 ms. The fix was a pool of 8 per pod: 15 × 8 = 120, under the limit. p99 dropped to about 180 ms, and database CPU fell because it was no longer juggling hundreds of sessions.

**What the interviewer is really checking**
Whether you know that more connections does not mean more speed, and whether you size the pool from the whole system (database capacity, pod count, hold time) rather than copying a number.

**How I answer it**
1. **Start small.** A small pool is usually faster. The database has a limited number of CPU cores and disks, and extra connections only add context switching and lock contention. A common starting point is `pool = (cores × 2) + effective_spindles`, where "cores" means the **database server's** cores, not the app's. This is a starting guess, not a rule.
2. **Cross-check with Little's Law.** At 200 rps per pod with each request holding a connection for 20 ms, you need about 200 × 0.02 = 4 connections on average. A pool of 8-10 gives headroom for bursts.
3. **Budget across all pods.** `pool × max pods (including autoscaling and rolling deploys) + admin and other clients` must stay **below the database `max_connections`**. Each pod sizes its own pool without knowing about the others, so the total is easy to overshoot.
4. **Set timeouts deliberately.** `connectionTimeout` is how long a thread waits for a connection before failing. The default is 30 s, which is too long for an API, so fail fast (2-3 s). Set `maxLifetime` a little **below** any database or firewall idle/lifetime limit, so Hikari retires connections before the network silently kills them.
5. **Load test and adjust.** Run at realistic arrival rates and change the pool size. Keep the smallest pool that holds p99 and keeps pending near zero.
6. **Cap concurrency with virtual threads.** Thousands of virtual threads can all block on a 10-connection pool and time out. Put a semaphore (permit count ≈ pool size) in front of the database work so excess requests wait cheaply or are rejected early.

```properties
spring.datasource.hikari.maximum-pool-size=10
spring.datasource.hikari.connection-timeout=3000
spring.datasource.hikari.max-lifetime=1740000
```
(Here the limit is assumed to be 30 minutes, so `max-lifetime` is 29.)

**Trade-offs and what can go wrong**
- **Too small:** requests queue and time out under bursts.
- **Too large:** the database overloads, and the pool-size-times-pods math breaks during scale-out.
- **Pool exhausted but database CPU low:** connections are being held too long, for example during a remote HTTP call inside a transaction. Fix that before enlarging the pool.
- **Long transactions and lazy loading** hold connections without doing work.
- **`maxLifetime` above the network limit** causes random "connection reset" errors.
- **Many services or pods:** consider an external pooler such as PgBouncer.

**How I'd monitor it**
- **`hikaricp.connections.pending`:** should be near 0. A sustained value above 0 means threads are waiting.
- **`hikaricp.connections.active`:** compare it with the maximum to see saturation.
- **`hikaricp.connections.acquire`:** how long threads wait for a connection.
- **`hikaricp.connections.usage`:** how long a connection is held.
- **`hikaricp.connections.timeout`:** a count of failed acquisitions.
- **Database side:** the current connection count against `max_connections`.
- **Alerts and logs:** alert on pending > 0 for several minutes, and search Splunk for "Connection is not available".

**Follow-ups to expect**
- *Why not a big pool "just in case"?* -> The database can only run about as many queries at once as it has cores and disks. Extra connections add queuing and context switching inside the database, so latency rises.
- *Pending is high but the database is idle. What is wrong?* -> Connections are held too long outside the database, such as remote calls inside transactions or leaks. Shorten the transaction scope.
- *Does the formula apply with SSDs or cloud databases?* -> Only as a starting point. Measure with load tests.

**60-second answer**
"I start with a small pool, because the database can only do so much work at once. A common starting point is database cores × 2 plus effective spindles, which I check with Little's Law: throughput × connection hold time. Then I make sure pool size × all pods, including autoscaling, stays below the database's max connections. I set a short connectionTimeout so requests fail fast, and a maxLifetime slightly below the database or firewall limit. I tune with load tests and watch hikaricp pending, acquire and usage metrics. With virtual threads, I add a semaphore so thousands of threads don't pile up on a small pool."

### Q13 [senior] What is the difference between latency, throughput and why p99 matters?
tags: latency, throughput, p99, percentiles, littles-law, tail-latency, basics

**Start here: the concepts**
- **Latency**: the time one request takes from sent to answered, measured in milliseconds. It is what a single user feels.
- **Throughput**: how many requests the system completes per second (rps). It is how much work the system gets done.
- **Percentile (p50, p95, p99)**: sort all request times from fastest to slowest. p99 is the time that 99% of requests beat, so 1 in 100 is slower. p50 is the typical request.
- **Mean (average)**: the sum of all times divided by the count. A few very slow requests barely move it, so it can look healthy while some users suffer.
- **Tail latency**: the slowest few percent of requests. It matters because real users hit it often (see the scenario).
- **Fan-out**: one user request triggers many internal calls, such as 30 service calls to build one page.
- **Concurrency**: how many requests are in progress at the same moment. It is limited by threads, connections and memory.
- **Little's Law**: in a steady system, `concurrency = throughput x latency`. It links the other three numbers.

**The live scenario**
A product-page API served 500 rps. The dashboard showed mean latency 110 ms, all green, yet support reported "the page hangs". The percentiles told a different story: p50 90 ms, p95 400 ms, p99 2.4 s. The page fans out to 30 backend calls, and each backend call had a p99 of about 800 ms. The chance that a page hits at least one slow call is 1 - 0.99^30, about 26%. So roughly 1 page in 4 was slow, even though each call was slow only 1% of the time. Traces showed the slow calls waited for a database connection during GC pauses. After fixing the pool size and GC settings, the call p99 dropped from 800 ms to 250 ms and the page p99 from 2.4 s to 700 ms. The mean barely changed (110 to 95 ms), which is why it was a useless signal.

**What the interviewer is really checking**
Whether you can explain why averages mislead, show with arithmetic how tails amplify under fan-out, and use Little's Law to reason about capacity instead of just quoting definitions.

**How I answer it**
1. **Define the two quantities separately.** Latency is time per request, and throughput is requests per second. They are related but not the same: you can raise throughput by adding parallelism while each request stays slow.
2. **Say that the mean hides the tail.** Averaging blends 99 fast requests with 1 very slow one into a "fine" number. Percentiles show the distribution, so I track p50, p95 and p99, not the mean.
3. **Show why p99 matters with fan-out.** A request touching N calls is slow if any call is slow: `P(slow) = 1 - 0.99^N`. With N = 30 that is 26%, and with N = 100 it is 63%. So the p99 of each call dominates what the user sees.
4. **Tie it together with Little's Law.** At 500 rps and 0.11 s mean latency, about 55 requests are in flight. If latency rises to 0.4 s, 200 are in flight. With a 200-thread pool, throughput is capped at 200 / 0.4 = 500 rps. Any further slowdown makes requests queue, and the tail explodes. Slower calls therefore reduce capacity, not just user happiness.
5. **Set targets as percentiles.** For example, "p99 < 500 ms at 500 rps" is an SLO (service level objective). It is better than "average under 200 ms".

**Trade-offs and what can go wrong**
- Never average percentiles across instances. Merge histograms, or compute the percentile over the raw data.
- p99 needs enough samples. With 50 requests a minute it is noise, so use longer windows.
- Chasing p99.9 costs money (spare capacity, hedged requests) and may not be worth it for every endpoint.
- Load tests that wait for each response before sending the next one hide stalls (coordinated omission). Use a fixed arrival rate.
- Little's Law uses steady-state averages. It is a sizing guide, not a guarantee during spikes.

**How I'd monitor it**
- Micrometer timers with published histograms, scraped by Prometheus. Query `histogram_quantile(0.99, ...)` per endpoint.
- Splunk: `... | stats perc50(duration) perc95(duration) perc99(duration) by endpoint`.
- OpenTelemetry traces to find which fan-out call is the slow one.
- Alerts on SLO burn rate (how fast the error budget is being used), not on the mean.
- In-flight request gauge and pool wait time, to check Little's Law against reality.

**Follow-ups to expect**
- *Why not just use the maximum?* -> The max is one outlier and is unstable. p99 or p99.9 is repeatable and still captures the tail.
- *If latency doubles, what happens to throughput?* -> With fixed concurrency, throughput halves (Little's Law). To keep throughput you need twice the concurrency, until a resource saturates.
- *How do you reduce the tail from fan-out?* -> Call downstream services in parallel, set timeouts, cache, and fix pauses such as GC and pool waits. Hedged requests are an option for idempotent reads.

**60-second answer**
Latency is how long one request takes, and throughput is how many requests per second the system completes. I track p50, p95 and p99 rather than the mean, because the mean hides slow requests. One user request often fans out into many calls. With 30 calls that each have a 1% chance of being slow, about 26% of pages hit at least one slow call. So the p99 of each call dominates what users feel. Little's Law ties it together: concurrency equals throughput times latency, so when latency rises, in-flight requests grow, thread and connection pools saturate, and the tail gets worse. I set SLOs on percentiles and watch them in Prometheus or Splunk, with traces to find the slow call.

### Q14 [mid] What are JFR and JMC?
tags: jfr, jmc, profiling, jvm, observability, production-diagnostics, basics

**Start here: the concepts**
- **Profiler:** a tool that shows where a program spends time and memory (which methods, which locks, which allocations). It exists because guessing the bottleneck is usually wrong.
- **Java Flight Recorder (JFR):** a recorder built into the JVM itself, like an aircraft black box. It writes events (GC pauses, object allocations, lock waits, file/socket I/O, periodic method samples) into a `.jfr` file.
- **Event:** one timestamped fact, such as "thread X waited 80 ms for a lock" or "a GC pause took 45 ms".
- **Method sampling:** every ~10-20 ms JFR looks at what the running threads are executing. Hot methods show up in many samples. It is cheap because it does not time every call.
- **Overhead:** the slowdown caused by measuring. The default JFR settings cost roughly 1-2%, which is why it is acceptable in production. The more detailed "profile" setting costs a bit more.
- **JDK Mission Control (JMC):** the desktop tool that opens `.jfr` files and shows them as graphs: hot methods, GC, memory, locks, I/O and threads. It is a separate download from the JDK (since Java 11). The command-line `jfr` tool can also summarise a file.
- **jcmd:** a command-line tool that sends commands to a running JVM by process ID (`pid`). No restart is needed.

**The live scenario**
An orders API normally runs at 600 rps with p99 around 300 ms. After a release, p99 climbs to 2.4 s, but CPU is only 45% and the heap looks fine. Nobody knows why. Instead of guessing or attaching a heavy profiler, the on-call engineer records 60 seconds of JFR on one pod. In JMC, the Lock Instances view shows about 70% of request threads blocked on one `synchronized` block around a pricing cache. They replace it with a `ConcurrentHashMap` lookup. p99 drops back to about 320 ms. The whole diagnosis took 15 minutes with no restart. These numbers are illustrative.

**What the interviewer is really checking**
Do you know a safe, built-in way to get evidence from a live JVM, and do you measure before you fix? Can you also say what it does not show?

**How I answer it**
1. **Define it:** JFR is a built-in, low-overhead (~1-2%) recorder of GC, allocations, locks, I/O and method samples. JMC is the viewer. The recorder and the viewer are two different things.
2. **Start it on the live process.** No restart or special agent is needed, which is the reason to choose it during an incident:
   `jcmd <pid> JFR.start duration=60s filename=rec.jfr`
3. **Record while the problem is happening.** Sixty seconds of the bad period is worth more than hours of a quiet one.
4. **Copy the file out and open it in JMC.** In containers, write to a writable path and copy it out, for example with `kubectl cp`.
5. **Read in a fixed order:** GC pauses first, then hot methods, then lock contention and I/O waits, then allocation hot spots. Each view answers a different symptom (CPU-bound, blocked, or memory-heavy).
6. **Fix one thing, then re-measure** with the same load, so you can prove the before/after.
7. **Use it before external profilers.** It is safe in production, so it is the first tool. If I need flame graphs or native-code detail, I move to async-profiler.

**Trade-offs and what can go wrong**
- It is low overhead, not zero. The detailed profile setting, or recording for hours with many events enabled, costs more.
- Sampling can miss very short spikes. It tells you where time goes statistically, not every call.
- It shows what the JVM sees. Problems in a downstream service or the network show up only as waiting, so you still need distributed tracing.
- Files can be large, and they may contain sensitive data such as class names and some strings. Treat them as internal.
- Common mistake: recording when the system is healthy, or changing code before looking at the evidence.

**How I'd monitor it**
- Keep a continuous low-overhead recording running (`-XX:StartFlightRecording` with a size or age limit), so after an incident I can run `jcmd <pid> JFR.dump` and get the minutes before it.
- Alert on p99 latency and GC pause time from Micrometer/Prometheus. Use the alert as the trigger to take a recording.
- Compare recordings before and after a release for lock wait time, allocation rate and GC pause.

**Follow-ups to expect**
- *How is JFR different from a flame graph tool like async-profiler?* -> JFR is built in and covers many event types (GC, locks, I/O). async-profiler gives detailed CPU and native flame graphs. I start with JFR and escalate if needed.
- *Can you use it without JMC?* -> Yes. The `jfr` CLI (`jfr summary`, `jfr print`) and some IDEs read the files.
- *Is it really safe in production?* -> The default settings are designed for it, about 1-2%. I still start with a short window and watch latency while it runs.

**60-second answer**
Java Flight Recorder is a recorder built into the JVM. It captures GC, allocations, locks, I/O and method samples with only about 1-2% overhead, so it is safe to use in production. JDK Mission Control is the tool I use to open and analyse the recording. When latency rises, I run `jcmd <pid> JFR.start duration=60s filename=rec.jfr` on a live pod while the problem is happening. Then I copy the file out and read it in order: GC, hot methods, lock contention, I/O waits. Once, this showed most threads blocked on one synchronized cache, and fixing it brought p99 from 2.4 s back to 0.3 s. I use JFR first because it needs no restart. If I need flame graphs, I move to async-profiler.

### Q15 [senior] Explain class loading and a ClassLoader leak.
tags: classloader, metaspace, jvm, memory-leak, tomcat, threadlocal, basics

**Start here: the concepts**
- **Class loading:** The JVM does not load every class at startup. When code first needs a class, a *ClassLoader* finds the `.class` bytes, checks them, and creates the class in memory. This keeps startup fast and lets you load code from places such as WAR files.
- **ClassLoader:** An object that loads classes. Each class remembers which loader defined it. Two copies of `Foo` loaded by different loaders are different classes to the JVM.
- **Built-in loaders (Java 9+):** *Bootstrap* loads core JDK classes. *Platform* loads other JDK modules. *Application* loads your classpath. (Java 8 had an "Extension" loader instead of Platform.)
- **Parent-first delegation:** A loader first asks its parent to load a class, and only loads it itself if the parent fails. This stops anyone from replacing `java.lang.String` with their own version. Servlet containers such as Tomcat deliberately load a web app's own classes *child-first*, so each app can bring its own library versions.
- **Metaspace:** The native memory (outside the Java heap) where the JVM stores class metadata. It replaced PermGen in Java 8. By default it is not capped, so it grows until the OS or container stops it, unless you set `MaxMetaspaceSize`.
- **Unloading:** Classes are freed only when their *whole loader* becomes unreachable and is garbage collected. Individual classes cannot be freed.
- **ClassLoader leak:** Something still reachable keeps the old loader alive, so all its classes stay in Metaspace.

**The live scenario**
A legacy WAR runs on Tomcat. Each hot redeploy during a release window adds roughly 100 MB of Metaspace (illustrative numbers). After the fourth redeploy, with `MaxMetaspaceSize=512m`, Tomcat throws `OutOfMemoryError: Metaspace` and the service is down for 15 minutes. After the fix, Metaspace stays near 130 MB across redeploys.

**What the interviewer is really checking**
Whether you understand that a loader and its classes are freed together, and whether you can name the typical anchors and how to prove them with a heap dump.

**How I answer it**
1. **Explain the hierarchy.** Bootstrap, then Platform, then Application, with parent-first delegation. The reason is safety: core classes cannot be hijacked. Mention that web containers give each app its own child loader.
2. **Explain why redeploy creates a new loader.** The container drops the old web-app loader and creates a fresh one, so the old classes should become garbage.
3. **Explain the leak.** A loader and its classes are freed only together. If anything long-lived still references one class or one object from the old loader, the loader stays reachable. Every class it loaded stays in Metaspace, and each redeploy adds another full copy.
4. **Name the usual anchors.**
   - A static field in a class from a *parent* loader that points at app objects.
   - A JDBC driver registered in `DriverManager`.
   - A non-daemon thread or executor started by the app and never stopped.
   - A `ThreadLocal` value set on a container pool thread and never removed. The thread outlives the app, so the value does too.
5. **Fix it.** Clean up in a shutdown hook, as in the snippet below. Where legacy code cannot be fixed, restart the process instead of redeploying, so the OS reclaims everything.
6. **Prove it.** Take a heap dump and open it in MAT. Look for several instances of the same `WebappClassLoader`, then use "path to GC roots" to find the anchor.

```java
public void contextDestroyed(ServletContextEvent e) { // ServletContextListener
  executor.shutdownNow(); DriverManager.deregisterDriver(driver); tl.remove();
}
```

**Trade-offs and what can go wrong**
- Not every Metaspace growth is a leak. Heavy use of proxies or generated classes also grows it.
- Restarting the process is the most reliable fix, but it costs downtime unless you use rolling deploys.
- Third-party libraries may leak and be hard to fix.
- With no `MaxMetaspaceSize`, a leak shows up as the container being OOMKilled instead of a clear Java error.

**How I'd monitor it**
- Track Metaspace used (Micrometer `jvm.memory.used` for Metaspace) and loaded class count after each deploy. Use `jstat -gc` (the MU column) for a quick check.
- Run `jcmd <pid> VM.classloader_stats` to count live loaders.
- Use `-Xlog:class+unload` to see whether classes ever unload.
- Alert if Metaspace after a full GC rises across deploys.
- Search Splunk for Tomcat warnings such as "appears to have started a thread named ... but has failed to stop it", and for `OutOfMemoryError: Metaspace`.

**Follow-ups to expect**
- *Why is Metaspace not on the heap?* -> It holds class metadata in native memory, which lets it grow dynamically. That is also why it needs its own cap.
- *Why does a ThreadLocal leak a loader?* -> The pool thread outlives the app, and its map holds the value, whose class points to the old loader.
- *Is raising MaxMetaspaceSize a fix?* -> No. It only delays the failure, because each redeploy still leaks a full copy.

**60-second answer**
A ClassLoader loads classes on demand. The JVM has Bootstrap, Platform and Application loaders, and each asks its parent first, so core classes stay safe. Web containers give each app its own loader, and on redeploy they discard it. A loader and its classes are freed only together, in Metaspace, which is native memory. If anything long-lived still points at one class or object from the old loader, such as a static in a parent-loader class, a registered JDBC driver, a running thread, or a `ThreadLocal` on a pool thread, the whole loader stays. Every redeploy then adds a copy until `OutOfMemoryError: Metaspace`. I would confirm it with a heap dump in MAT and fix it by cleaning up on shutdown, or by restarting the process instead of redeploying.
