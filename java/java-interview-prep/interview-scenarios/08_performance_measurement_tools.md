---
id: performance-tools
title: Tools and techniques to measure application performance
stack: java
skill: performance
---
Interview feedback focus: **tools and techniques to measure application performance.** Interviewers want to
hear which tool you reach for *for which question*, and what you actually read in its output.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] How do you measure the performance of an application?
tags: metrics, red-method, use-method, golden-signals, basics

**The live scenario**
A new team member is asked "Is the order service performing well?" and replies "CPU is at 40%". The lead asks: "But are users happy?"

**What the interviewer is really checking**
That you start from what users experience, then move to resources, and know the standard frameworks.

**How I answer it**
1. **User-facing first, with the RED method per endpoint:**
   - **R**ate: requests per second;
   - **E**rrors: failed requests per second or percentage;
   - **D**uration: latency percentiles (p50/p95/p99).
2. **Resources second, with the USE method per resource** (CPU, memory, pools, disks, the database):
   - **U**tilisation: how busy;
   - **S**aturation: how much work is queued (pool pending, run queue, Kafka lag);
   - **E**rrors.
3. Google's **four golden signals** (latency, traffic, errors, saturation) are the same idea in one list.
4. **Compare against targets:** an SLO such as "99% of requests under 300 ms" turns numbers into a yes/no answer.
5. **Tools by layer:**
   - metrics: Micrometer → Prometheus/Grafana, or an APM;
   - traces: OpenTelemetry;
   - logs: Splunk;
   - JVM: JFR, GC logs;
   - load: Gatling/JMeter/k6.

**Trade-offs and what can go wrong**
Measuring only averages and CPU misses tail latency and queueing — the things users feel.

**How I'd monitor it**
One dashboard per service: RED for each endpoint on top, USE for its resources below, SLO status at the very top.

**60-second answer**
I start from what users feel: rate, errors and duration percentiles per endpoint — the RED method — and judge them against an SLO. Then I look at resources with the USE method: utilisation, saturation and errors for CPU, memory, pools and the database. The tools follow the layers: Micrometer and Prometheus or an APM for metrics, OpenTelemetry for traces, Splunk for logs, JFR and GC logs for the JVM, and Gatling or JMeter for load.

### Q2 [mid] What do APM and distributed tracing give you that metrics and logs don't?
tags: apm, opentelemetry, tracing, micrometer, dynatrace, spans

**The live scenario**
A checkout request crosses API gateway → order service → pricing → inventory → Kafka → payment. Metrics said "checkout p99 is 2 s" but nobody could say which hop was slow.

**What the interviewer is really checking**
That you know what a trace is, how context propagates, and how to use it to locate latency.

**How I answer it**
1. **Metrics** say *that* something is slow (aggregates). **Logs** say *what happened* in one service. A **trace** says *where the time went* across services, for one request.
2. **How it works:** each hop creates a **span** (start, duration, attributes); a trace id and parent span id travel in headers (W3C `traceparent`) and in **Kafka headers**, linking all spans into a waterfall.
3. **In Spring Boot 3:** Micrometer Tracing with an OpenTelemetry bridge auto-instruments HTTP clients/servers, JDBC and Kafka. Export via OTLP to Jaeger, Tempo, Zipkin or a vendor (Dynatrace, New Relic, AppDynamics, Datadog — commercial APMs add auto-instrumentation and code-level hotspots).
4. **Put the trace id in every log line** (MDC), so you jump from a slow trace to its logs in Splunk.
5. In our case the waterfall showed 1.4 s waiting for a pricing call that retried twice on a timeout — invisible in averaged metrics.

**Trade-offs and what can go wrong**
Tracing every request is expensive at scale; sample (with tail-based sampling to keep slow and failed traces). Missing propagation on one hop breaks the chain.

**How I'd monitor it**
Trace-derived latency per service and dependency, plus exemplars linking metric spikes to example traces.

**60-second answer**
Metrics tell me something is slow, logs tell me what one service did, and a trace tells me where one request's time went across all services. Each hop records a span, and the trace context travels in HTTP and Kafka headers. In Spring Boot 3 I use Micrometer Tracing with OpenTelemetry, export to Jaeger, Tempo or an APM, and put the trace id in every log line. That's how we found a hidden retry adding 1.4 seconds to checkout.

### Q3 [mid] Which JVM command-line tools do you use, and for what?
tags: jcmd, jstat, jstack, jmap, jvm-tools, diagnostics

**The live scenario**
On a production incident bridge, an engineer has shell access to one pod and five minutes before it is restarted.

**What the interviewer is really checking**
Practical fluency with the JDK's built-in tools and their production safety.

**How I answer it**
1. **`jcmd <pid>`** — the Swiss-army knife:
   - `Thread.print` (thread dump);
   - `GC.class_histogram` (object counts by class — quick, light);
   - `GC.heap_dump` (full dump — pauses the app, large file);
   - `JFR.start` / `JFR.dump` (flight recording);
   - `VM.native_memory summary` (with NMT enabled);
   - `VM.flags` and `VM.system_properties` (what is actually configured).
2. **`jstat -gcutil <pid> 1000`** — live GC behaviour every second: generation occupancy, GC counts and times. Cheap and safe.
3. **`jstack`/`jmap`** — the older equivalents of jcmd's thread dump and heap dump.
4. **On that five-minute bridge,** my order is:
   - three thread dumps 5 s apart (cheap, shows stuck or hot threads);
   - a class histogram;
   - start a 60 s JFR recording;
   - a heap dump only if memory is the suspect, and only from a pod taken out of traffic.
5. **In Kubernetes:** `kubectl exec` into the pod, or ephemeral debug containers if the image lacks the JDK tools; copy files out with `kubectl cp`.

**Trade-offs and what can go wrong**
Heap dumps pause the JVM for seconds on big heaps and contain sensitive data. Minimal (JRE-only) images may lack the tools — ship `jcmd` or plan for debug containers.

**How I'd monitor it**
These are diagnostics, not monitoring; the evidence they produce goes into the incident record.

**60-second answer**
jcmd is my main tool: thread dumps, class histograms, heap dumps, starting JFR recordings, native memory and the real JVM flags. jstat -gcutil gives cheap live GC behaviour. On an incident I take several thread dumps, a class histogram and a short JFR recording first, because they're cheap, and a heap dump only when memory is the suspect and only from a pod out of traffic, since it pauses the JVM and holds customer data.

### Q4 [senior] How do you profile an application in production, and how do you read a flame graph?
tags: profiling, async-profiler, jfr, flame-graph, production

**The live scenario**
CPU per request had crept up 35% over three releases. No single change looked guilty. We needed to see where the CPU goes, in production, without hurting customers.

**What the interviewer is really checking**
Low-overhead production profiling, and turning a flame graph into a decision.

**How I answer it**
1. **Tools:**
   - **JFR** (built into the JDK): continuous recording with about 1% overhead using the default profile; CPU samples, allocation, locks, GC, I/O. Open it in JDK Mission Control.
   - **async-profiler**: accurate CPU, allocation, lock and wall-clock profiles without safepoint bias; outputs flame graphs directly.
   - Continuous profiling platforms (e.g. Pyroscope, vendor APMs) keep profiles over time for comparison.
2. **Reading a flame graph:**
   - each box is a method; the y-axis is the call stack;
   - **width = share of samples** (time), not order;
   - look for wide plateaus at the top — methods that themselves burn CPU;
   - compare two graphs (before/after) to see what grew.
3. **Choose the right mode:**
   - CPU mode: what burns CPU;
   - **wall-clock** mode: where requests *wait* (I/O, locks);
   - allocation mode: what creates garbage;
   - lock mode: contention.
4. Our differential flame graph showed a new date-parsing utility creating a formatter per call and a debug log building strings — together 30% of request CPU. Fixed in a day.

**Trade-offs and what can go wrong**
Safepoint-biased profilers point at the wrong methods; sampling too briefly misses intermittent issues.

**How I'd monitor it**
Continuous JFR or profiling in production, so a "before" profile always exists when a regression appears.

**60-second answer**
In production I use JFR, which runs continuously at about 1% overhead, and async-profiler for precise CPU, allocation, lock or wall-clock flame graphs. In a flame graph, width is the share of time, and the wide plateaus at the top are where CPU really goes; comparing before and after graphs shows what grew. I pick the mode for the question — CPU for burning, wall-clock for waiting, allocation for garbage. A differential flame graph once found 30% of our request CPU in a formatter created per call.

### Q5 [mid] Which load-testing tool would you use, and how do you read the results?
tags: load-testing, jmeter, gatling, k6, locust, results

**The live scenario**
Before a product launch the team must prove the API holds 800 rps at p99 under 400 ms.

**What the interviewer is really checking**
Tool awareness, test design, and reading results beyond "it didn't crash".

**How I answer it**
1. **Tools:**
   - **JMeter**: GUI and huge plugin ecosystem; good for mixed protocols; heavier per virtual user;
   - **Gatling**: code-based scenarios (Java, Kotlin, Scala DSL), efficient, open arrival-rate models, great HTML reports;
   - **k6**: JavaScript scenarios, CLI-first, easy in CI;
   - **Locust**: Python.

   I prefer Gatling or k6 so tests live in the repo and run in CI.
2. **Design:** realistic user journeys and data, think time, an **arrival-rate** model, ramp → steady → spike → soak.
3. **Reading results:**
   - throughput achieved versus target (did the generator actually deliver 800 rps?);
   - latency percentiles over time, not just the summary (a rising line means queueing or a leak);
   - error rate and error types;
   - the **knee**, where latency bends;
   - server-side saturation at that point — **which resource ran out first** is the actual finding.
4. **Check the load generator** isn't the bottleneck (its CPU, network); distribute it if needed.

**Trade-offs and what can go wrong**
Testing through a shared gateway or against stubs that are too fast gives optimistic numbers.

**How I'd monitor it**
Production-grade dashboards during the test, with the test's start and stop marked.

**60-second answer**
I use Gatling or k6 so scenarios are code in the repo and run in CI; JMeter when its protocol support is needed. I design with realistic journeys and data, an arrival-rate model, and ramp, steady, spike and soak phases. Reading results, I check the generator really delivered the target rate, look at percentiles over time rather than a summary, find the knee, and most importantly identify which server-side resource saturated first — that's the real finding.

### Q6 [senior] When do you write a JMH microbenchmark, and why do naive timing loops lie?
tags: jmh, microbenchmark, jit, warmup, dead-code-elimination

**The live scenario**
A developer "proved" with a `System.nanoTime()` loop that their new parser was 10x faster. In production it was 20% slower.

**What the interviewer is really checking**
Understanding of the JIT and of measurement pitfalls on the JVM.

**How I answer it**
1. **Why naive loops lie:**
   - **warm-up**: early iterations run interpreted, later ones JIT-compiled;
   - **dead-code elimination**: if the result isn't used, the JIT may remove the work entirely (the "10x" case);
   - constant folding, loop unrolling, on-stack replacement;
   - GC kicking in during one run but not the other;
   - unrealistic inputs.
2. **JMH** (the OpenJDK benchmark harness) handles these: forks a fresh JVM per run, warm-up iterations, `Blackhole` to consume results, statistical error margins, and modes for throughput or average/sample time.
3. **When to use it:** comparing implementations of a **hot, isolated** piece of code that the profiler already flagged — a parser, a serialiser, a data structure. Not for whole endpoints (use a load test).
4. **Run it on realistic data** and production-like JVM flags; confirm the win with a load test or a production profile afterwards.

**Trade-offs and what can go wrong**
A microbenchmark win can disappear in the real system (different inlining, cache behaviour, allocation context).

**How I'd monitor it**
JMH results tracked in CI for hot-path libraries, with regressions flagged.

**60-second answer**
Naive nanoTime loops lie on the JVM: early iterations aren't JIT-compiled, unused results get eliminated as dead code, and GC lands randomly. JMH fixes that with forks, warm-up, Blackholes and error margins. I use it only for hot, isolated code the profiler has already flagged — parsers, serialisers, data structures — on realistic data, and I confirm any win with a load test, because microbenchmark gains don't always survive in the full system.

### Q7 [mid] How do you measure database performance from the application side?
tags: database, explain-plan, slow-query-log, hibernate-statistics, hikari-metrics

**The live scenario**
An API's latency doubled when the orders table passed 50 million rows. The DBA said the DB was healthy; the developers said the code hadn't changed.

**What the interviewer is really checking**
Bridging app and database evidence with concrete tools.

**How I answer it**
1. **From the app:**
   - per-query timing in traces (JDBC spans);
   - **Hibernate statistics** or p6spy/datasource-proxy for statement counts and slow statements;
   - **HikariCP metrics**: active, pending, acquire time and usage time (long usage = slow queries or work inside transactions).
2. **From the database:**
   - `EXPLAIN` / `EXPLAIN ANALYZE` for the actual plan and row estimates;
   - the slow query log; PostgreSQL `pg_stat_statements`; Oracle AWR/ASH reports and SQL Monitor;
   - wait events (I/O, locks), and lock contention.
3. **Join them:** the slow statement from the trace, its plan from EXPLAIN, and its frequency from `pg_stat_statements`.
4. In our case the plan flipped from an index range scan to a full scan once statistics went stale after the table grew; refreshing statistics and adding a better composite index fixed it.

**Trade-offs and what can go wrong**
Logging every SQL statement in production is expensive and leaks data; sample, and mask parameters.

**How I'd monitor it**
Query latency percentiles by statement, statements per request, pool acquire time, and DB CPU, I/O and wait events.

**60-second answer**
From the application I measure query timing in traces, statement counts with Hibernate statistics or p6spy, and Hikari pool acquire and usage times. From the database I read EXPLAIN ANALYZE plans, the slow query log, pg_stat_statements or Oracle AWR, and wait events. Joining the two finds the real problem — in one case a plan flipped to a full scan after the table grew and statistics went stale.

### Q8 [senior] How do you use Splunk to analyse application performance?
tags: splunk, spl, percentiles, timechart, release-comparison

**The live scenario**
After a release, the business said "the app feels slower" but dashboards were averaged and inconclusive.

**What the interviewer is really checking**
That you can turn structured logs into performance evidence with real SPL.

**How I answer it**
1. **Log the right fields:** structured JSON per request — endpoint, status, `duration_ms`, trace id, version, pod, and the customer tier if skew matters.
2. **Percentiles by endpoint:**
   `index=app sourcetype=access | stats count perc95(duration_ms) perc99(duration_ms) by uri`
3. **Over time, split by release:**
   `index=app | timechart span=5m perc99(duration_ms) by version`
   A line that steps up exactly at the deploy is the answer.
4. **Find the slow segment:** add `by customer_tier` or `by pod` — one bad pod (noisy node) or one big customer shows immediately.
5. **Drill into examples:** pick the slowest trace ids and open their full log trail or trace.
6. **Make it permanent:** a saved search for the p99 per endpoint feeding an alert, and a dashboard panel with release markers.

**Trade-offs and what can go wrong**
Logs are sampled or dropped under load and are costly at volume; use metrics for alerting and Splunk for investigation and correlation.

**How I'd monitor it**
Saved searches for p99 per endpoint, error rate by version, and a per-release comparison panel.

**60-second answer**
I make sure every request logs structured fields — endpoint, status, duration, trace id, version, pod. Then SPL like stats perc95 and perc99 of duration by uri, and timechart perc99 by version, shows exactly whether a release stepped latency up. Splitting by pod or customer tier finds the slow segment, and slow trace ids lead to examples. Metrics drive alerts; Splunk is for investigation and correlation.

**Minimal config**
```text
index=app sourcetype=access earliest=-24h | timechart span=5m perc99(duration_ms) by version
```

### Q9 [senior] How do you set performance SLOs and alerts that people actually trust?
tags: slo, sli, error-budget, burn-rate, alerting, dashboards

**The live scenario**
The team had 120 alerts, most on CPU over 80%. On-call ignored them. A real latency incident went unnoticed for 40 minutes.

**What the interviewer is really checking**
Symptom-based alerting tied to user experience, and how SLOs drive decisions.

**How I answer it**
1. **Define SLIs that users feel:** the percentage of requests faster than a threshold, and the success rate, per critical journey (checkout, login).
2. **Set SLOs with the business:** e.g. 99% of checkout requests under 400 ms over 28 days. The remaining 1% is the **error budget**.
3. **Alert on burn rate, not raw thresholds:** page when the budget is being consumed fast (e.g. 14x the normal rate over 1 hour); open a ticket on slow burns. That pages for real user impact and ignores harmless CPU spikes.
4. **Resource metrics move to dashboards**, used to diagnose — not to page.
5. **Use the budget to decide:** budget nearly spent → freeze risky releases and prioritise performance work.
6. We went from 120 alerts to 14, and the next latency incident paged within 4 minutes.

**Trade-offs and what can go wrong**
SLOs that are too strict cause constant alerts; too loose and they hide pain. Revisit them quarterly with real data.

**How I'd monitor it**
SLO status and remaining error budget per journey on the top of each service dashboard.

**60-second answer**
I define SLIs users feel — the share of requests under a latency threshold and the success rate per journey — and agree SLOs with the business, which gives an error budget. I alert on how fast that budget burns, not on CPU thresholds, so pages mean real user pain; resource metrics stay on dashboards for diagnosis. The budget also drives decisions like freezing releases. One team went from 120 noisy alerts to 14 that people trusted.

### Q10 [architect] How would you build a performance-engineering practice in a team that has none?
tags: performance-engineering, baseline, ci, capacity-review, culture

**The live scenario**
A growing platform had performance incidents every few weeks, always discovered by customers, and performance testing happened once a year before peak season.

**What the interviewer is really checking**
Turning measurement into a sustainable process with ownership — an architect's answer.

**How I answer it**
1. **Make it visible:** an SLO per critical journey, and RED/USE dashboards per service with release markers.
2. **Establish baselines:** per-service throughput at the SLO, CPU-ms and memory per request, recorded and versioned.
3. **Shift left:**
   - performance tests for the top journeys in CI/CD with tolerance bands (a regression gate);
   - JMH for hot libraries;
   - profiling as a normal review step for performance-sensitive changes.
4. **Production as the truth:** continuous profiling (JFR) and canary analysis on latency and CPU per request.
5. **Capacity reviews:** quarterly, and before known peaks — forecast traffic, re-run load tests at peak plus headroom.
6. **Ownership and learning:** each team owns its SLOs; performance incidents get blameless reviews with action items; game days rehearse traffic spikes and dependency slowness.
7. Customer-found performance incidents went from about one a month to none over the next six months, and peak season ran without a war room.

**Trade-offs and what can go wrong**
Too heavy a process slows delivery; start with the top three journeys and expand.

**How I'd monitor it**
Count of performance incidents and who found them, SLO compliance trend, and CI performance-gate results.

**60-second answer**
I'd make performance visible with SLOs and RED/USE dashboards, record baselines like throughput at SLO and CPU per request, and shift left with CI performance gates and microbenchmarks for hot code. Production stays the source of truth through continuous profiling and canary analysis, with quarterly capacity reviews before peaks. Teams own their SLOs, and incidents get blameless reviews. Starting with the top three journeys, we got customer-found performance incidents down from monthly to none.
