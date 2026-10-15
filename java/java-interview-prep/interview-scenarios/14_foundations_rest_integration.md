---
id: foundations-rest-integration
title: Calling several third-party APIs for one response: from the basics
stack: java
skill: rest-api
---
Concepts first, then a real story, then the answer. This file answers one very common senior question in
full: one request that must call several slow third-party APIs and return a single combined response.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] One request must call 5 third-party APIs that take about 2 seconds each, and we must respond within 5 seconds. How do you design it, and do you use CompletableFuture or a Spring feature?
tags: aggregation, parallel-calls, completablefuture, async, webclient, mono-zip, virtual-threads, timeouts, partial-response, resilience4j, basics

**Start here: the concepts**
- **Third-party API:** a service run by someone else. You do not control its speed, availability or limits.
- **Synchronous (blocking) call:** your thread sends the request and then *waits* doing nothing until the reply arrives. If you make five of these one after another, the waits add up.
- **Parallel (concurrent) calls:** you start all five requests at about the same time and wait for them together. The total time is roughly the *slowest* call, not the sum.
- **Aggregation:** combining the replies of several calls into one response for your client.
- **Latency budget:** the total time you are allowed (5 seconds). You split it: network and your own work, each call's timeout, and a safety margin.
- **Timeout:** the longest you are willing to wait for one call. Without it a stuck vendor holds your thread forever.
- **Thread pool / executor:** a fixed set of worker threads. Parallel work needs threads; if the pool is unbounded or shared carelessly it can exhaust the server.
- **Partial response:** returning what you have, clearly marked, when one non-critical call failed or timed out, instead of failing the whole request.
- **Circuit breaker and bulkhead:** the breaker stops calling a vendor that keeps failing; the bulkhead limits how many threads one vendor can use so it cannot starve the rest.

**The live scenario**
A travel site shows a trip summary page. One request needs five vendors: flights, hotels, car hire, weather and insurance quotes. Each vendor takes about 2 seconds. The first version calls them one after another: 5 x 2 s = 10 seconds, so the page times out at the 5-second SLA and users leave. A second problem shows up in testing: when the weather vendor slows to 8 seconds, every request waits for it, request threads pile up, and the whole site stalls even for pages that do not need weather. The team redesigns it: all five calls run in parallel with a 3-second timeout each, so the common case finishes in about 2.2 seconds, and weather and insurance are optional, so a slow one just shows "unavailable".

**What the interviewer is really checking**
That you do the arithmetic (sum vs max), that you know the Java and Spring options and when each fits, and that you design for failure: timeouts, partial responses, bounded concurrency, not just "use CompletableFuture".

**How I answer it**
1. **Do the arithmetic first.** Sequential is 5 x 2 s = 10 s, which breaks the 5-second SLA. In parallel the time is about the slowest call, around 2 s plus overhead, so there is room. If they were truly dependent (call B needs A's result) those must stay in order; only independent calls run in parallel.
2. **Set a budget.** Total 5 s: about 0.5 s for your own work and network, a 3 s timeout per vendor call, and the remaining margin for building the response and a fallback. Never let one call's timeout equal the whole SLA.
3. **Pick the tool that fits your stack.** Spring does not give a single "aggregate" annotation; it gives you building blocks:

| Option | When it fits | Note |
|---|---|---|
| `CompletableFuture` on a dedicated bounded executor | Spring MVC (blocking) app, `RestClient`/`RestTemplate`; the most common and simplest | you control the pool and the timeouts |
| `@Async` methods returning `CompletableFuture` | you like Spring-managed executors and annotations | proxy rules apply: a call within the same class bypasses it; configure the executor explicitly |
| `WebClient` with `Mono.zip(...)` | reactive or non-blocking app, many parallel calls | an MVC app must still `block()` at the end, which loses much of the benefit |
| Java 21 virtual threads (`spring.threads.virtual.enabled=true`) | simple blocking code that is cheap per thread | still cap concurrency per vendor; `StructuredTaskScope` is a preview API |

4. **A typical blocking version (MVC):**

```java
var f1 = CompletableFuture.supplyAsync(() -> flights.search(q), pool).orTimeout(3, SECONDS).exceptionally(e -> null);
var f2 = CompletableFuture.supplyAsync(() -> hotels.search(q),  pool).orTimeout(3, SECONDS).exceptionally(e -> null);
// ... one per vendor
CompletableFuture.allOf(f1, f2).join();           // total time is about the slowest call
return new TripSummary(f1.join(), f2.join());     // null means "unavailable", marked in the response
```

5. **Mark critical and optional calls.** Flights and hotels are required: if they fail return a clear error. Weather and insurance are optional: return the page with those sections marked unavailable. State the rule in the API contract.
6. **Bound concurrency.** Use a dedicated executor sized from `requests per second x vendors x call time` (Little's Law), a bulkhead per vendor, and a queue limit. Parallel calls multiply load on vendors, so also respect their rate limits.
7. **Add resilience.** Resilience4j (with the Spring Boot starter) gives `TimeLimiter`, `CircuitBreaker`, `Bulkhead` and `Retry` as annotations or decorators. Retry only idempotent calls, with backoff and jitter, and inside the time budget.
8. **Cut the work, not just the time.** Cache vendor data that changes slowly (weather for ten minutes), reuse HTTP connections, and consider an asynchronous design (return `202 Accepted` and let the client poll) if the work cannot fit the SLA.
9. **Prove it.** Load-test with a vendor artificially slowed to 8 seconds and confirm: p99 stays under the SLA, threads do not pile up, and the partial response appears.

**Trade-offs and what can go wrong**
- Parallel calls use more threads and put more instantaneous load on vendors. Without a bounded pool you trade latency for outages.
- `CompletableFuture.supplyAsync` without an executor uses the shared common pool, which is meant for CPU work; blocking calls there starve other tasks.
- `@Async` on a private method or a call within the same class silently runs synchronously.
- `orTimeout` completes the future but does not always cancel the underlying HTTP request; set the client's own connect and read timeouts as well.
- Partial responses require clients to handle missing sections; document them.
- Retrying inside parallel calls can blow the budget; budget retries or skip them for slow calls.

**How I'd monitor it**
- Per-vendor latency histograms (p50/p95/p99), error rate and timeout count.
- Executor queue depth, active threads and rejected tasks; circuit-breaker state and bulkhead usage.
- End-to-end p95/p99 and the percentage of partial responses, with traces showing the five spans side by side.

**Follow-ups to expect**
- *Why not just increase the server timeout?* -> the user still waits 10 seconds, and threads stay blocked longer, so capacity falls.
- *CompletableFuture or reactive?* -> in an MVC app with blocking clients, `CompletableFuture` with a bounded executor is simpler; use `WebClient` and `Mono.zip` when the whole stack is reactive; on Java 21 virtual threads make plain blocking code cheap.
- *What if one vendor is down all day?* -> the circuit breaker opens, calls fail fast with a fallback, and the optional section is marked unavailable.
- *What if the vendors have rate limits?* -> a per-vendor limiter or bulkhead, caching and request coalescing.
- *Where does aggregation belong?* -> often a backend-for-frontend or an aggregator service, so each client does not make five calls itself.

**60-second answer**
Sequential calls would take 5 x 2 s = 10 s, so I run the independent calls in parallel, which makes the time about the slowest call. I give the whole request a budget, put a timeout on every call, and run them on a dedicated bounded executor, using `CompletableFuture` in an MVC app, `WebClient` with `Mono.zip` in a reactive one, or virtual threads on Java 21. Spring does not have a single feature for this; I combine those with Resilience4j for timeouts, circuit breaker and bulkhead. I classify calls as required or optional and return a partial response when an optional vendor fails, cache slow-changing data, and prove the design with a load test where one vendor is made slow.
