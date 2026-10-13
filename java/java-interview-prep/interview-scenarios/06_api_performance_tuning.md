---
id: api-performance
title: Tuning backend APIs for response time and throughput
stack: java
skill: performance
---
Interview feedback focus: **tuning backend APIs for response time and throughput.** Every answer starts from a
production situation, works out where the time goes, and only then names the fix — the order a strong
candidate uses in the room. Defaults quoted are Spring Boot 3.x / Java 21 unless stated.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What do response time and throughput mean, and how are they related?
tags: latency, throughput, percentiles, littles-law, basics

**The live scenario**
An order API handles 300 requests/second with an average response time of 120 ms. The business asks: "Can it handle Black Friday at 1,500 rps, and will customers notice?"

**What the interviewer is really checking**
That you can talk in percentiles, not averages, and that you know latency and throughput are linked through concurrency.

**How I answer it**
1. **Response time (latency)** is how long one request takes, end to end as the client sees it. I quote it as percentiles: p50 is the typical user, p95/p99 are the unlucky ones — and at scale, "1% of users" is thousands of people.
2. **Throughput** is how many requests per second the system completes successfully.
3. They are linked by **Little's Law**: concurrency = throughput × latency. 300 rps × 0.12 s = 36 requests in flight at any moment. At 1,500 rps with the same latency, that is 180 in flight — which must fit inside our thread pool, connection pool and the database.
4. As utilisation rises, latency stays flat and then **bends sharply** (queueing). Past roughly 70–80% utilisation of the bottleneck, p99 explodes long before throughput stops growing.
5. So "can we handle 1,500 rps" means: will p99 stay inside the SLO at that load? We answer it with a load test, not arithmetic alone.

**Trade-offs and what can go wrong**
Averages hide tail latency; a 120 ms average can sit on a 2 s p99. Optimising throughput (big batches, queues) can hurt latency, and vice versa.

**How I'd monitor it**
Latency histograms per endpoint (p50/p95/p99), request rate, error rate, and saturation of the bottleneck resource (CPU, pool usage) on one dashboard.

**Follow-ups to expect**
- *Why not use the average?* -> It hides the tail; users and SLAs feel the p99.
- *What happens past the knee of the curve?* -> Queues grow, latency climbs exponentially, then timeouts and retries add more load.

**60-second answer**
Response time is how long one request takes, which I always quote as p50/p95/p99, never just the average. Throughput is completed requests per second. They're linked by Little's Law — concurrency equals throughput times latency — so 300 rps at 120 ms means about 36 requests in flight, and that number has to fit our thread and connection pools. As the bottleneck passes about 75% utilisation, latency bends sharply upward, so I answer "can we take 5x" with a load test against a p99 target.

### Q2 [mid] Average latency is 200 ms but p99 is 3 seconds. How do you find where the time goes?
tags: tail-latency, tracing, p99, diagnosis, apm

**The live scenario**
The `GET /accounts/{id}/summary` endpoint looks healthy on average, but 1% of calls take about 3 s, and the mobile team reports timeouts.

**What the interviewer is really checking**
A method — measure, break down, then fix — rather than guessing ("add a cache").

**How I answer it**
1. **Break the request into spans.** Distributed tracing (OpenTelemetry, or the APM agent) shows the waterfall for slow requests: our code, each DB query, each downstream call, serialisation.
2. **Compare slow traces with fast ones.** What's different? Common findings:
   - one downstream call with its own slow tail;
   - a DB query that is fast for most accounts but slow for big accounts (data skew — a customer with 50,000 transactions);
   - **waiting** rather than working: time waiting for a pooled DB connection or a thread;
   - GC pauses lining up with the slow requests.
3. **Correlate with resources:** connection-pool pending count, GC pause logs, CPU throttling in Kubernetes at the same timestamps.
4. In our case it was big accounts: the summary loaded every transaction and summed in Java. We moved the aggregation into SQL with an index, and p99 dropped from 3 s to 250 ms.
5. Then guard it: a p99 alert per endpoint and a perf test with a realistic large account.

**Trade-offs and what can go wrong**
Sampling may miss rare slow requests — use tail-based sampling or always keep traces above a latency threshold.

**How I'd monitor it**
Latency histograms by endpoint *and* by a size dimension (account tier), pool wait time, GC pause time, all on the same time axis.

**Follow-ups to expect**
- *What if tracing isn't available?* -> Timing logs per step with a correlation id, then Splunk `perc99` by step.
- *Could hedged requests help?* -> For idempotent reads with an independent tail, yes — at the cost of extra load.

**60-second answer**
I don't guess; I break slow requests into spans with tracing and compare slow traces against fast ones. The usual culprits are a downstream call with its own tail, a query that's slow only for big customers, time spent waiting for a pooled connection, or GC pauses. In my case big accounts were loading every transaction into Java; pushing the aggregation into indexed SQL took p99 from 3 seconds to 250 ms, and a per-endpoint p99 alert now guards it.

### Q3 [mid] The database is the bottleneck for your API. What do you look for and fix first?
tags: database, n+1, indexes, pagination, jpa, query-tuning

**The live scenario**
`GET /orders?customerId=…` took 1.8 s. Hibernate statistics showed 201 SQL statements for one request.

**What the interviewer is really checking**
That you know the classic ORM and query problems and fix them with evidence.

**How I answer it**
1. **Count queries per request** (Hibernate statistics, p6spy or APM). 201 statements = 1 for orders + 200 lazy loads for order lines: the **N+1 problem**. Fix with a fetch join, `@EntityGraph`, or batch fetching.
2. **Read the execution plan** (`EXPLAIN`) for the slow statements. A full table scan on `customer_id` means a missing index; a composite index matching the filter *and* sort order fixes both.
3. **Fetch less:**
   - DTO projections instead of whole entities;
   - only the needed columns;
   - **keyset pagination** (`WHERE id > :lastId ORDER BY id LIMIT 50`) instead of large `OFFSET`, which scans and throws away rows.
4. **Avoid round-trips:** batch inserts/updates (`hibernate.jdbc.batch_size`), bulk queries instead of a loop.
5. **Keep transactions short:** no remote calls inside a transaction — they hold connections and locks.
6. Result: 201 queries became 2, and the response went from 1.8 s to 90 ms.

**Trade-offs and what can go wrong**
Eager fetching everywhere fixes N+1 but loads huge graphs elsewhere — fetch per use case. Every index slows writes and uses memory.

**How I'd monitor it**
Queries per request, slow query log, DB CPU and wait events, connection-pool usage and wait time.

**Follow-ups to expect**
- *Why is OFFSET pagination slow on page 5,000?* -> The DB still reads and discards all the skipped rows.
- *Cache instead?* -> Only after the query is efficient; caching a bad query hides it until the cache misses.

**60-second answer**
I measure queries per request first — the N+1 problem from lazy loading is the most common killer, fixed with a fetch join or entity graph. Then I read the execution plans and add composite indexes that match the filter and sort. I fetch less with DTO projections and keyset pagination, batch writes, and keep transactions free of remote calls. On one orders API that took 201 queries down to 2 and the response from 1.8 s to 90 ms.

### Q4 [senior] How do you size the thread pool and the database connection pool for an API?
tags: thread-pool, hikaricp, tomcat, littles-law, pool-exhaustion

**The live scenario**
A payments API ran on Tomcat's default 200 threads and HikariCP's default pool of 10 connections. Under a traffic spike, requests piled up waiting for connections, the 30 s `connectionTimeout` let them queue silently, and p99 went from 150 ms to 30 s. Someone raised the pool to 200, and the database fell over.

**What the interviewer is really checking**
That pools are **queues with limits**, sized from measured numbers, and that "bigger" is often worse.

**How I answer it**
1. **Little's Law per resource.** Connections needed ≈ DB-call rate × time a connection is held. 400 queries/s × 20 ms = 8 connections busy on average; size for the peak plus headroom — say 15–20 — not 200.
2. **The database has the real limit.** A database runs best with a modest number of active connections (around a couple of times its CPU cores). 30 pods × 20 connections = 600 connections can overwhelm it. Pool size is a **fleet-wide** budget, divided across pods.
3. **Threads:** request threads should not vastly exceed what downstream resources can serve. With 200 threads and 10 connections, 190 threads just wait. Match them, or use a bulkhead.
4. **Fail fast:** set Hikari `connectionTimeout` to a few hundred milliseconds to 2 s, not 30 s, so an overloaded service sheds load quickly instead of building a hidden queue.
5. **Hold connections briefly:** no remote calls or heavy computation inside transactions — that one change usually frees more capacity than any pool change.
6. **Java 21 virtual threads** remove the request-thread limit, which makes the connection pool the *only* limit, so this sizing matters even more.

**Trade-offs and what can go wrong**
Too small: requests queue for connections. Too big: the database thrashes on context switches and locks, and everyone gets slower.

**How I'd monitor it**
Hikari active/idle/pending connections and acquire time, Tomcat busy threads, DB active sessions and CPU.

**Follow-ups to expect**
- *Formula?* -> HikariCP's guidance starts from about (cores × 2) + effective spindles on the DB side, then measure.
- *Why did raising the pool to 200 make it worse?* -> More concurrent queries than the DB can run means contention, so each query slows and total throughput drops.

**60-second answer**
Pools are bounded queues, so I size them from Little's Law — call rate times hold time, plus headroom — and treat database connections as a fleet-wide budget, because 30 pods times a big pool can drown the database. I fail fast on pool acquisition instead of the 30-second default, keep remote calls out of transactions so connections are held briefly, and keep request threads in line with what the pool can serve. Bigger pools often make it slower, and I've seen a pool of 200 take a database down.

**Minimal config**
```yaml
spring.datasource.hikari: { maximum-pool-size: 20, connection-timeout: 1500 }
server.tomcat.threads.max: 100
```

### Q5 [senior] Where and how do you add caching to cut response time — and what goes wrong?
tags: caching, caffeine, redis, cache-stampede, invalidation

**The live scenario**
A product-detail API at 2,000 rps hit the database for data that changed a few times a day. p99 was 400 ms. Adding a Redis cache cut it to 25 ms — until a cache flush at noon sent all traffic to the DB at once and the site went down for 4 minutes.

**What the interviewer is really checking**
Cache placement, invalidation, and the failure modes caching introduces.

**How I answer it**
1. **Cache what's read-heavy and tolerates staleness**, agreed with the business (prices for display: minutes; stock at checkout: never).
2. **Choose the layer:**
   - local in-process (Caffeine): fastest, no network hop, but per-pod copies;
   - distributed (Redis): shared, survives deploys, one network hop;
   - HTTP/CDN with `Cache-Control`/ETag for public data;
   - often a two-level combination.
3. **Invalidation:** a TTL as the safety net plus event-driven eviction (a Kafka "product-changed" event evicts the key).
4. **Protect against a stampede:**
   - single-flight / request coalescing (one loader per key);
   - **jittered TTLs** so keys don't expire together;
   - stale-while-revalidate;
   - warm the cache before switching traffic.

   The noon incident was a mass expiry: jittered TTLs plus refresh-ahead fixed it.
5. **Bound memory:** a maximum size and eviction policy; an unbounded cache is a memory leak with a nice name.

**Trade-offs and what can go wrong**
Stale data, cache-key mistakes that serve one user's data to another, and hiding a slow query that resurfaces on every miss.

**How I'd monitor it**
Hit ratio, load time, eviction count, Redis latency and memory, and DB QPS (should drop and stay flat).

**Follow-ups to expect**
- *Cache-aside vs read-through?* -> Cache-aside: the app loads on miss. Read-through: the cache library loads. Same stampede risk.
- *How do you cache per-user data safely?* -> Include the user/tenant in the key, and never cache permission-filtered results under a shared key.

**60-second answer**
I cache read-heavy data whose staleness the business accepts, choosing local Caffeine, Redis or HTTP caching by how shared and how fast it must be. Invalidation is TTL plus event-driven eviction. The failure I design for is the stampede — I once saw a mass expiry take a site down — so I use jittered TTLs, single-flight loading and refresh-ahead, and bound the cache's memory. Then I watch the hit ratio and DB load.

### Q6 [senior] Your API calls three downstream services. How do you make that fast?
tags: parallel-calls, completablefuture, http-client, connection-reuse, timeouts

**The live scenario**
A checkout API called pricing (120 ms), inventory (90 ms) and promotions (150 ms) one after another: 360 ms before our own work. It also created a new HTTP client per request, so every call paid TCP and TLS setup again.

**What the interviewer is really checking**
Parallelism, connection reuse and latency budgets — the cheap, big wins.

**How I answer it**
1. **Parallelise independent calls:** `CompletableFuture` on a dedicated bounded executor, `WebClient` with `Mono.zip`, or virtual threads with structured concurrency. Latency becomes the slowest call (150 ms), not the sum (360 ms).
2. **Reuse connections:** one shared, pooled HTTP client bean with keep-alive. Creating a client per request cost us 30–60 ms per call in TCP and TLS handshakes, and leaked sockets.
3. **Timeouts per call** inside an overall budget, so one slow dependency can't hold the whole request.
4. **Fetch less, less often:** batch endpoints (one call for 20 items instead of 20 calls), and cache slow-changing responses.
5. **Avoid the call entirely:** keep a local read model fed by events for data you query on every request.
6. The checkout went from about 420 ms to 190 ms with parallel calls and a shared client alone.

**Trade-offs and what can go wrong**
Parallel fan-out multiplies instantaneous load on downstream services; bound the executor. Never use the common ForkJoin pool for blocking I/O.

**How I'd monitor it**
Per-dependency latency spans, outbound connection-pool usage, and new-connection rate (should be near zero with keep-alive).

**Follow-ups to expect**
- *Why not `parallelStream()` for the calls?* -> It uses the shared common pool, which is sized for CPU work, so blocking I/O starves everything else using it.

**60-second answer**
I run independent downstream calls in parallel, so latency becomes the slowest call rather than the sum, on a bounded executor or with WebClient or virtual threads. I reuse one pooled keep-alive HTTP client, because building a client per request pays TCP and TLS setup every time. I give each call its own timeout inside the overall budget, use batch endpoints, cache, or keep an event-fed read model to avoid calls altogether. That took one checkout from 420 to 190 ms.

### Q7 [senior] How do you increase an API's throughput by moving work off the request path?
tags: async, kafka, outbox, 202-accepted, throughput

**The live scenario**
`POST /orders` synchronously wrote the order, generated a PDF invoice (400 ms), sent an email (300 ms) and called the loyalty service. Throughput topped out at about 80 rps per pod, and an email-provider slowdown made order placement fail.

**What the interviewer is really checking**
Separating what the user must wait for from what can happen afterwards.

**How I answer it**
1. **Ask what the caller actually needs before we answer:** the order saved and validated. The invoice, email and loyalty points can follow seconds later.
2. **Do the essential part synchronously**, then publish an `OrderPlaced` event — reliably, with the **transactional outbox** (event row written in the same DB transaction, relayed to Kafka), so we never save an order without its event.
3. **Consumers do the rest** at their own pace, scaled independently, with retries and a DLT.
4. **For genuinely long operations** the client must track, return **202 Accepted** with a status URL.
5. Result: p99 for placing an order went from 1.1 s to 140 ms, throughput per pod rose about 5x, and email outages no longer affected orders.

**Trade-offs and what can go wrong**
Eventual consistency: the UI must handle "invoice not ready yet". Consumers must be idempotent, and the outbox adds a table and a relay to operate.

**How I'd monitor it**
Request latency, outbox backlog age, consumer lag per downstream task, and DLT rate.

**Follow-ups to expect**
- *Why not just `@Async`?* -> In-memory work is lost on a crash or deploy; an outbox plus Kafka is durable.

**60-second answer**
I separate what the caller must wait for from what can happen later. The request does only the essential write, then publishes an event through the transactional outbox so it's never lost, and consumers handle invoices, emails and loyalty independently with retries. Long operations get 202 with a status URL. On one order API that cut p99 from 1.1 s to 140 ms, multiplied throughput per pod about five times, and decoupled us from the email provider's outages.

### Q8 [mid] The response payload is large and slow. What do you do?
tags: payload, serialization, compression, pagination, jackson

**The live scenario**
A reporting endpoint returned 8 MB of JSON. Serialisation alone took 300 ms of CPU, and mobile users on slow networks waited 6 s for the download.

**What the interviewer is really checking**
That bytes and serialisation are part of latency, not just database time.

**How I answer it**
1. **Send less:**
   - paginate (cursor/keyset);
   - return only the fields the client uses (a summary DTO, sparse fieldsets, or a separate detail endpoint);
   - omit nulls and defaults.
2. **Compress:** enable gzip (or Brotli at the gateway) for text responses above about 1 KB. JSON typically shrinks 5–10x.
3. **Serialise efficiently:** reuse one Jackson `ObjectMapper` (it is thread-safe and expensive to create), avoid reflection-heavy custom serializers in hot paths, and stream very large responses instead of building them in memory.
4. **Cache-friendly responses:** ETags so unchanged data returns `304 Not Modified`.
5. **Big exports** become async jobs that produce a file in object storage with a download link.
6. Our report went from 8 MB to 600 KB compressed and paginated; mobile load time went from 6 s to under 1 s.

**Trade-offs and what can go wrong**
Compression costs CPU; for tiny or already-compressed payloads it's not worth it. Removing fields is a contract change — version it.

**How I'd monitor it**
Response size histograms per endpoint, serialisation time in traces, and CPU per request.

**60-second answer**
Payload size is latency too — serialisation CPU and network time. I send less with pagination and summary DTOs, compress JSON with gzip, reuse a single ObjectMapper and stream large responses, add ETags so unchanged data costs a 304, and turn big exports into async file jobs. One report went from 8 MB to 600 KB and from 6 seconds to under one on mobile.

### Q9 [senior] Throughput must go from 100 to 1,000 requests per second. How do you plan and prove it?
tags: capacity-planning, scaling, load-testing, bottleneck, horizontal-scaling

**The live scenario**
A partner integration will send 10x our current traffic in six weeks. Today: 100 rps, 4 pods, p99 of 300 ms.

**What the interviewer is really checking**
A structured capacity plan: measure, find the bottleneck, remove bottlenecks in order, prove it with a test.

**How I answer it**
1. **Baseline:** per-pod throughput at our p99 target, from a load test. Say one pod sustains 60 rps before p99 crosses 300 ms.
2. **Naive arithmetic:** 1,000 ÷ 60 ≈ 17 pods, plus headroom for a zone failure and deploys → about 24. But scaling pods only works if **everything behind them** scales too.
3. **Walk the chain** and compute each component's load at 10x:
   - database: queries/s and connections (30 pods × pool size must stay under the DB limit);
   - cache: hit ratio and Redis throughput;
   - downstream services and their rate limits;
   - Kafka partitions for any events we publish.
4. **Remove bottlenecks in order:** usually the database first (read replicas, caching, query fixes), then dependency limits, then our own CPU.
5. **Make the service horizontally scalable:** stateless, no in-memory sessions, idempotent operations, HPA on a meaningful signal.
6. **Prove it:** a load test at 1,200 rps (20% above target) with production-like data, then a soak test for hours to catch leaks.

**Trade-offs and what can go wrong**
The bottleneck moves: fixing the DB exposes the next limit. Partner traffic is often bursty, so plan for peak, not average.

**How I'd monitor it**
Per-component utilisation versus the plan, p99 against the SLO, and saturation alerts (pool usage, CPU throttling, DB CPU).

**60-second answer**
I baseline per-pod throughput at our p99 target, do the arithmetic for pods with headroom, then walk the whole chain — database, cache, dependencies, Kafka — computing each one's load at 10x, because scaling pods only moves the problem. I remove bottlenecks in order, usually the database first, keep the service stateless so it scales horizontally, and prove it with a load test 20% above target plus a soak test.

### Q10 [senior] Would Java 21 virtual threads improve your API's throughput? When, and what are the traps?
tags: virtual-threads, java21, loom, throughput, pinning

**The live scenario**
An API spends 90% of each request waiting on two downstream HTTP calls. It needs 400 platform threads at peak; memory and context switching become a problem.

**What the interviewer is really checking**
That you know virtual threads help **blocking I/O-bound** workloads, not CPU-bound ones, and know the traps.

**How I answer it**
1. **What they solve:** thread-per-request code where threads mostly wait. Virtual threads are cheap (thousands of them), so waiting no longer ties up a scarce OS thread. Throughput rises without rewriting to reactive.
2. **Enabling it:** Spring Boot 3.2+ on Java 21 with `spring.threads.virtual.enabled=true`.
3. **Traps:**
   - they don't make CPU-bound work faster;
   - **downstream limits still exist**: unlimited concurrency now hits the DB pool and partner rate limits, so keep semaphores/bulkheads;
   - **pinning**: before Java 24, blocking inside `synchronized` pinned the carrier thread (fixed by JEP 491 in Java 24); native calls still pin;
   - `ThreadLocal`-heavy code multiplies memory with millions of threads;
   - don't pool virtual threads.
4. **Prove it with a load test.** In our case, throughput per pod rose about 2.5x at the same p99, and the limit moved to the connection pool, which we then sized deliberately.

**Trade-offs and what can go wrong**
Profiling and thread dumps look different (many threads); some libraries still assume small thread counts.

**How I'd monitor it**
Pinning events in JFR (`jdk.VirtualThreadPinned`), pool wait times, and throughput against p99.

**60-second answer**
Virtual threads help when requests spend most of their time blocked on I/O: waiting becomes cheap, so throughput rises without a reactive rewrite. They don't help CPU-bound work, and they move the limit to downstream resources, so I keep bulkheads and size the connection pool deliberately. I watch for pinning — synchronized blocks before Java 24 — and ThreadLocal-heavy code. On one I/O-bound API, throughput per pod rose about 2.5x at the same p99.

### Q11 [architect] How do you run a load test that tells the truth?
tags: load-testing, gatling, jmeter, k6, coordinated-omission, soak-test

**The live scenario**
A load test reported p99 of 200 ms at 1,000 rps. In production at 600 rps, p99 was 1.5 s. The test had lied.

**What the interviewer is really checking**
That you know the common ways load tests mislead, and how to design one that predicts production.

**How I answer it**
1. **Realistic workload:** the production mix of endpoints, real payload sizes, and realistic data volumes and skew (big customers). Empty databases and identical requests hit caches and lie.
2. **Open vs closed model:** real users keep arriving whether or not we're slow. A closed-loop tool that waits for responses before sending more requests slows down with the server, hiding queueing — the **coordinated omission** problem. Use an arrival-rate (open) model (Gatling's `constantUsersPerSec`, k6's arrival-rate executors).
3. **Production-like environment:** same instance sizes, limits, and dependency latencies (or realistic stubs), same JVM flags.
4. **Test shapes:**
   - ramp to find the knee;
   - steady at target;
   - spike;
   - **soak** for hours to catch leaks and slow drifts.
5. **Measure server-side too:** compare client latency with server metrics and resource saturation.
6. **Pass/fail against SLOs**, automated, so the result is a decision, not a chart.

**Trade-offs and what can go wrong**
A full prod-like environment is expensive; a scaled-down one needs per-pod numbers extrapolated carefully. Shared test environments add noise.

**How I'd monitor it**
The same dashboards as production during the test, so you also test your observability.

**60-second answer**
A load test tells the truth only with a realistic workload — production mix, real data sizes and skew — and an open arrival-rate model, because closed-loop tools slow down with the server and hide queueing, the coordinated-omission trap. I run it on a production-like environment, use ramp, steady, spike and soak shapes, check server-side saturation, and pass or fail against the SLO automatically.

### Q12 [architect] After a release, latency went up 30%. How do you catch and prevent performance regressions?
tags: performance-regression, canary, ci-performance-test, slo, release

**The live scenario**
A release added a JSON-logging library and a new validation step. p99 rose from 180 ms to 240 ms. Nobody noticed for two weeks, until the cloud bill and a customer complaint arrived.

**What the interviewer is really checking**
Making performance a guarded property of every release, not an occasional project.

**How I answer it**
1. **Detect in the release:** canary deployments compared automatically against the baseline (p99, error rate, CPU per request), with automatic rollback on breach.
2. **Detect before the release:**
   - a performance test in CI for critical endpoints, with a tolerance band;
   - JMH microbenchmarks for hot code paths.
3. **Diagnose quickly:** compare flame graphs from before and after (async-profiler or JFR) — the diff showed 40% of the new CPU in the logging library's serialiser.
4. **Track efficiency, not just latency:** CPU-ms per request and memory per pod reveal regressions that autoscaling hides by adding pods.
5. **Own it:** performance budgets per service, reviewed like error budgets.

**Trade-offs and what can go wrong**
Noisy performance tests produce false alarms and get ignored; use stable environments, repeated runs and statistical comparison.

**How I'd monitor it**
Release markers on latency and CPU-per-request dashboards, plus SLO burn-rate alerts.

**60-second answer**
I make performance a release gate: canaries compared automatically against the baseline with rollback, a CI performance test with a tolerance band for critical endpoints, and JMH benchmarks for hot paths. When something slips I diff before-and-after flame graphs — that's how we found a logging library eating 40% of the new CPU. And I track CPU per request, because autoscaling quietly hides regressions as extra pods.
