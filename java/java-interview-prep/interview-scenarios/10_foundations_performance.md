---
id: foundations-performance
title: Performance from the basics: concepts, a real story, then the answer
stack: java
skill: performance
---
These entries are written **from the ground up**. Each starts with *Start here: the concepts* (plain
words, every term defined), then a real production story, then the answer an interviewer expects. Read
them in order; the short crib-sheet answers for the same questions make sense once you have done this.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] How can a Java application leak memory despite the garbage collector?
tags: memory-leak, garbage-collection, heap, heap-dump, static-cache, threadlocal, basics

**Start here: the concepts**
- **Heap:** the area of memory where every object you create with `new` lives.
- **Garbage collector (GC):** a background process that deletes objects *nothing can reach any more*. It cannot know whether you still *need* an object, only whether something still *points to* it.
- **GC root:** a starting point the GC always trusts, such as a static field, a running thread's stack, or a loaded class. Everything reachable from a root is kept.
- **Memory leak in Java:** objects you will never use again, but that are still reachable from a root, so the GC is not allowed to delete them. The heap fills slowly until `OutOfMemoryError`.
- So "despite the GC" is the point: the GC is doing its job correctly. The code is accidentally keeping a reference.

**The live scenario**
An order service keeps a "recent customers" cache so it does not hit the database every time. It is a `static Map` that only ever has `put()` called on it.
- Day 1: 10,000 customers, 50 MB. Fine.
- Day 3: 800,000 customers, 1.4 GB. GC runs constantly but frees almost nothing.
- Day 4: `OutOfMemoryError`, the pod restarts, memory is fine again, and the cycle repeats.
The restart "fixes" it, which is the classic sign of a leak.

**What the interviewer is really checking**
That you can separate "the GC is broken" (almost never) from "we are holding references" (almost always), and that you know how to prove it with a heap dump.

**How I answer it**
1. **Define it:** a leak is reachable-but-unused objects, so the GC cannot free them.
2. **Name the usual sources and what each means:**
   - static map or cache with no eviction: the scenario above;
   - listeners or callbacks never removed: the event source keeps them alive;
   - `ThreadLocal` not cleared on pooled threads: pool threads live forever, so the value does too;
   - unclosed resources: connections and streams hold memory outside normal GC control;
   - classloader leak on redeploy: old application classes stay in memory;
   - mutable key in a `HashMap`: the hash changes after insert, so the entry can never be found or removed.
3. **Prove it, do not guess:** watch heap *after* GC over hours (a rising floor means a leak), take `jcmd <pid> GC.heap_dump`, open it in Eclipse MAT.
4. **Read MAT:** the dominator tree shows the biggest retained object; "path to GC roots" shows *who* holds it, for example `static cache -> HashMap -> Customer[]`.
5. **Fix and verify:** bound the cache (Caffeine with a max size and TTL), then run a soak test and confirm the floor is flat.

**Trade-offs and what can go wrong**
Heap dumps are large and pause the JVM, so take them deliberately. A bounded cache lowers the hit ratio, so size it from a measured hit rate. Restarting on a schedule hides the leak but is not a fix.

**How I'd monitor it**
Alert on the slope of heap-after-GC rather than raw heap use, and add a multi-hour soak test to the release checklist.

**Follow-ups to expect**
- *Heap dump vs thread dump?* -> a heap dump is what objects exist and who holds them; a thread dump is what each thread is doing right now.
- *How do you tell a leak from a big but healthy heap?* -> a healthy heap sawtooths with a flat floor after full GC; a leak's floor keeps climbing.

**60-second answer**
The GC only frees objects nothing references, so a Java leak is a reference we forgot to drop, such as a static cache that only grows. I confirm with a rising heap-after-GC, take a heap dump, find the biggest retainer and its GC-root path in MAT, then bound or remove it and verify with a soak test.

### Q2 [fresher] What are p50, p95 and p99 latency, and why not just use the average?
tags: percentiles, latency, p99, average, tail-latency, basics

**Start here: the concepts**
- **Latency:** how long one request takes from sent to answered.
- **Percentile:** sort all request times from fastest to slowest. **p50** is the time that 50% of requests beat (the median); **p95** is the time that 95% beat; **p99** is the time that 99% beat.
- **Tail latency:** the slow end of that sorted list: p95, p99 and beyond.
- **Average (mean):** the sum divided by the count. A few very slow requests barely move it.

**The live scenario**
A checkout API serves 1,000 requests per second. The dashboard says "average 120 ms, healthy". Meanwhile 1% of requests take 4 seconds and customers on those requests abandon the cart. That is 10 slow requests every second, and a single page load may call the API five times, so far more than 1% of *users* hit one.

**What the interviewer is really checking**
That you know averages hide the experience of the unluckiest users, and that you can reason about SLOs in percentiles.

**How I answer it**
1. **Average hides the tail:** 990 requests at 100 ms and 10 at 4 s average out to about 140 ms, which looks fine.
2. **Use percentiles:** p50 for the typical user, p95 and p99 for the tail, and compare against an SLO such as "p95 under 300 ms".
3. **Why the tail matters more than it looks:** one page makes many calls, and the user waits for the slowest, so the chance of hitting a slow call is much higher than 1%.
4. **Aggregate correctly:** publish histogram buckets and compute quantiles on the server; never average per-instance p99 values.
5. **Look at the gap:** p50 flat but p99 rising usually points to GC pauses, a slow dependency, pool waits or one bad instance.

**Trade-offs and what can go wrong**
p99 needs enough samples to be stable, and it costs more to store (histograms). Chasing p99.9 can be wasted effort when users feel p95.

**How I'd monitor it**
Per-endpoint p50/p95/p99 plus error rate on one dashboard, with an SLO line, and alerts on burn rate rather than on a single spike.

**60-second answer**
Percentiles sort requests by speed: p50 is the typical user, p99 is the slowest 1%. Averages hide the tail, and a page that makes several calls feels the tail often, so I track p50, p95 and p99 per endpoint against an SLO and aggregate them with histograms.

### Q3 [mid] What is the difference between a thread pool and a connection pool, and what happens when each runs out?
tags: thread-pool, connection-pool, hikari, tomcat, littles-law, pool-exhaustion, basics

**Start here: the concepts**
- **Thread:** one unit of work the JVM can run at a time. Creating threads is expensive, and each holds memory for its stack.
- **Thread pool:** a fixed set of ready threads that take requests from a queue (Tomcat's request threads are one).
- **Connection:** an open, authenticated link to the database. Opening one is slow.
- **Connection pool (HikariCP):** a fixed set of open connections that requests borrow and return.
- **Exhausted:** every item is in use, so new work waits in a queue or is rejected.
- **Little's Law:** items in use = arrival rate x time each is held.

**The live scenario**
An API at 200 requests per second, each holding a connection for 50 ms, needs 200 x 0.05 = 10 connections. A pool of 20 is comfortable. One day a query slows to 1 second. Now the same traffic needs 200 connections, the pool of 20 is empty, requests queue for a connection, Tomcat threads pile up waiting, and the whole service stalls even though CPU is at 15%.

**What the interviewer is really checking**
That you reason with Little's Law, understand that waiting (not computing) is the failure, and do not answer "increase the pool".

**How I answer it**
1. **Two different resources:** threads accept and run requests; connections talk to the database. A request holds a thread, and usually a connection inside it.
2. **Compute the need:** concurrency = rate x hold time; that tells me whether the pool is sized sensibly.
3. **What exhaustion looks like:** Hikari `pending` above zero and "connection not available, request timed out"; Tomcat threads all busy; latency rising with low CPU.
4. **Why bigger is not the fix:** more connections push more concurrent queries into a database that has a limited useful concurrency, which makes it slower and can take it down.
5. **Fix the hold time first:** index or rewrite the slow query, shorten transactions, move remote calls out of them, add timeouts.
6. **Then size from data:** a small pool (10–20 per instance) is usually right; pods x pool size must stay under the database `max_connections`.

**Trade-offs and what can go wrong**
Too small a pool queues work; too large overloads the database. A long timeout on connection acquire turns a fast failure into a slow outage.

**How I'd monitor it**
Hikari active, pending and acquire time; Tomcat busy threads; database active sessions and slow queries.

**60-second answer**
A thread pool runs requests and a connection pool lends database connections. By Little's Law the number in use is rate times hold time, so a query that goes from 50 ms to 1 second needs twenty times the connections and the pool empties. I fix the slow query and transaction length first and size the pool from measured concurrency, not by making it bigger.

### Q4 [mid] My service freezes for a second every few minutes. Could it be garbage collection?
tags: gc-pause, stop-the-world, g1, gc-logs, latency-spikes, basics

**Start here: the concepts**
- **Stop-the-world (STW) pause:** the JVM briefly freezes *every* application thread so the GC can safely move or inspect objects.
- **Young generation:** where new objects start; collecting it is frequent and usually very fast.
- **Old generation:** where long-lived objects end up; collecting it takes longer.
- **Allocation rate:** how many megabytes per second your code creates. The higher it is, the more often GC runs.
- **GC log:** a file the JVM writes with every collection, its type, duration and heap size.

**The live scenario**
A pricing API has p50 of 20 ms but p99 of 1.4 seconds, and the slow requests arrive in bursts every few minutes across all endpoints at once. That "everything slow at the same moment" shape is the signature of a pause rather than a slow query.

**What the interviewer is really checking**
That you can recognise a pause from its shape, confirm it with GC logs, and fix allocation before touching GC flags.

**How I answer it**
1. **Recognise the shape:** slow requests cluster in time and hit unrelated endpoints together.
2. **Confirm with evidence:** enable `-Xlog:gc*`, and compare pause timestamps with the latency spikes; Micrometer's `jvm.gc.pause` shows the same.
3. **Read the cause:** frequent young GC means a high allocation rate; long old or mixed GC means a large live set or fragmentation; Full GC means pressure or a leak.
4. **Reduce allocation first:** fewer temporary objects on hot paths, no boxing in loops, avoid copying big structures.
5. **Then the collector:** G1 is the sensible default; generational ZGC for very large heaps or strict pause goals. Change one setting, re-measure.

**Trade-offs and what can go wrong**
Bigger heap means fewer but longer collections for some collectors. Low-pause collectors cost throughput and CPU. Tuning flags without logs is guessing.

**How I'd monitor it**
Alert on GC pause p99 and the share of time spent in GC, and track allocation rate and heap-after-GC on the dashboard.

**60-second answer**
Everything slow at once, in bursts, suggests a stop-the-world GC pause. I enable GC logging and line the pauses up with the latency spikes, then reduce allocation on hot paths, and only afterwards consider G1 settings or ZGC. I verify with the pause p99 before and after.

### Q5 [mid] CPU is at 90% but latency is fine; in another service CPU is at 20% and latency is terrible. How can both happen?
tags: cpu, saturation, waiting, io-wait, blocked-threads, basics

**Start here: the concepts**
- **CPU utilisation:** the share of time the processor is busy running code.
- **Computing vs waiting:** a request can spend time *using* CPU or *waiting* for something (database, network, a lock). Waiting uses no CPU.
- **Thread states:** RUNNABLE (running or ready), BLOCKED (waiting for a lock), WAITING (waiting to be notified or for IO).
- **Saturation:** the point where a resource is so busy that new work queues.

**The live scenario**
Service A transcodes images: CPU 90%, latency steady, and that is healthy because it is doing its job. Service B calls a slow partner API: CPU 20%, but every request waits 3 seconds for the reply, threads pile up, and users see timeouts. CPU said "fine" while the service was effectively down.

**What the interviewer is really checking**
That you do not treat CPU as the only health number and that you can tell computing from waiting.

**How I answer it**
1. **CPU alone is not health;** it is one resource among threads, pools, memory, network and the database.
2. **Computing problems:** high CPU with rising latency, found with a flame graph (JFR or async-profiler).
3. **Waiting problems:** low CPU with rising latency, found with thread dumps (many BLOCKED or WAITING), pool pending counts and downstream latency.
4. **Use the golden signals:** latency, traffic, errors, saturation, and look at all four together.
5. **Fix by cause:** hot path -> optimise; lock -> shrink the critical section; slow dependency -> timeout, circuit breaker, cache, async.

**Trade-offs and what can go wrong**
Adding CPU to a waiting problem does nothing; adding threads can make contention worse.

**How I'd monitor it**
Dashboards showing CPU next to thread states, pool pending and downstream latency, with alerts on latency and saturation instead of CPU alone.

**60-second answer**
High CPU with good latency can be healthy work; low CPU with bad latency is usually waiting on a database, a downstream service or a lock. I separate them with a flame graph for computing and thread dumps and pool metrics for waiting, and I judge health by latency, errors and saturation, not CPU alone.

### Q6 [senior] Why does latency shoot up sharply when a service gets near its limit, and how do you find that limit?
tags: capacity, queueing, utilisation, load-testing, knee, saturation, basics

**Start here: the concepts**
- **Utilisation:** how busy a resource is, as a percentage of capacity.
- **Queueing:** when work arrives faster than it can be served, the excess waits in line, and waiting time is added to latency.
- **The knee:** the load level where latency stops growing gently and climbs steeply.
- **Load test:** replaying controlled traffic at increasing rates to find that point before users do.

**The live scenario**
A service handles 500, 800 and 1,000 requests per second with p95 of 120, 140 and 190 ms. Everyone relaxes. At 1,200 requests per second p95 is 900 ms and at 1,300 it is 6 seconds with errors. The last 20% of traffic cost 30 times the latency.

**What the interviewer is really checking**
That you understand non-linear behaviour near saturation and plan headroom instead of running at the edge.

**How I answer it**
1. **Why it is non-linear:** at low utilisation requests rarely wait; near 100% even small bursts create queues, and queues grow faster than they drain.
2. **Rule of thumb:** latency starts climbing noticeably around 70–80% utilisation of the bottleneck resource.
3. **Find the limit with a stress test:** ramp the arrival rate step by step and record p95, p99, errors and resource use at each step.
4. **Use an open load model:** a fixed arrival rate so slow responses cannot hide themselves (avoid coordinated omission).
5. **Identify the bottleneck at the knee:** CPU, a pool, the database or a downstream service.
6. **Plan headroom:** run production comfortably below the knee, autoscale on a leading signal, and add load-shedding or rate limits for spikes.

**Trade-offs and what can go wrong**
Test data and traffic mix that differ from production give a false knee. Running with lots of headroom costs money; running with none costs outages.

**How I'd monitor it**
Utilisation of the bottleneck resource and queue depth, with alerts well before the knee, and capacity reviews before known peak events.

**60-second answer**
Near saturation, small bursts create queues and waiting time dominates, so latency climbs steeply once the bottleneck passes about 70–80% utilisation. I find the knee with a stress test at a fixed arrival rate, identify which resource saturates there, keep production below it, and use autoscaling and load-shedding for spikes.
