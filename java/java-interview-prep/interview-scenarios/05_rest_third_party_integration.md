---
id: rest-third-party
title: Calling third-party REST APIs — and still giving a proper response
stack: java
skill: rest-api
---
Every answer follows the same shape: **the live scenario**, what the interviewer is checking, how I answer,
trade-offs, monitoring, follow-ups, and a 60-second version you can say out loud. Code is kept to a few config lines.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] How do you call a third-party REST API from Spring Boot, and what matters beyond just making the call?
tags: rest-client, webclient, resttemplate, basics, timeouts

**The live scenario**
A new developer added an address-validation call using `new RestTemplate()` inside a service method. It worked in dev.
In production, the vendor had a slow minute, every request thread waited on it, and the whole service stopped responding.

**What the interviewer is really checking**
That you know the client options, and — more importantly — that a remote call is a **failure point**, not a method call.

**How I answer it**
1. **Clients.**
   - `RestClient` (Spring 6.1+): the modern synchronous fluent client.
   - `WebClient`: reactive, non-blocking, good for many parallel calls.
   - `RestTemplate`: still works, in maintenance mode.
   - Declarative HTTP interfaces (`@HttpExchange`) or OpenFeign: an interface instead of hand-written calls.
2. **Build the client once**, as a configured bean, with a pooled connection manager. Never create one per request.
3. **What matters beyond the call:**
   - **timeouts** (connect, read, overall) — the defaults are often infinite;
   - **error handling** — map their errors to ours;
   - **retries** only for safe cases;
   - **logging with a correlation id**;
   - **secrets** for API keys in a vault, not in code;
   - **metrics** per partner.
4. Wrap the vendor in an **adapter/gateway class** (an anti-corruption layer), so their model and quirks never leak into our domain.

**Trade-offs and what can go wrong**
WebClient in a blocking MVC app gives little benefit unless you actually call several services in parallel.

**How I'd monitor it**
Latency, error rate and timeout count per vendor endpoint (Micrometer `http.client.requests`), visible on one dashboard.

**Follow-ups to expect**
- *Why an adapter class?* → So a vendor change or switch touches one class, and tests can stub it.

**60-second answer**
In Spring Boot I'd use RestClient or a declarative HTTP interface (WebClient if I need non-blocking parallel calls), built once as a bean with a connection pool. What matters more than the call itself is treating it as a failure point:
explicit timeouts, error mapping, careful retries, correlation-id logging, secrets from a vault, and per-vendor metrics — all inside an adapter class so the vendor's quirks don't leak into our domain.

### Q2 [mid] The third-party API is slow. Why are timeouts the first thing you set, and how do you choose them?
tags: timeouts, latency, thread-pool, connection-pool, slo

**The live scenario**
A credit-score vendor normally answered in 200 ms. One afternoon it took 60+ seconds. Our default read timeout was infinite, so all 200 Tomcat threads ended up waiting on the vendor,
and even our `/health` endpoint stopped answering. Kubernetes restarted the pods, and the outage became ours.

**What the interviewer is really checking**
That you understand **resource exhaustion**: one slow dependency can consume every thread. And that you derive timeouts from an SLA rather than guessing.

**How I answer it**
1. **Three timeouts:**
   - connect (TCP/TLS establishment, short — about 1 s);
   - read/response (time to first byte or the full response);
   - **connection-pool acquire** — often forgotten, and it is exactly where threads pile up.
2. **Derive them from the budget.** If our API's SLA is p99 of 1 s and the vendor call is one step, the vendor gets maybe 400 ms. Look at the vendor's real p99 (say 250 ms) and set the timeout just above it.
   A timeout is a statement about how long the *business* is willing to wait.
3. **Overall deadline.** With retries, the *total* time must still fit the budget: 2 attempts × 400 ms + backoff must stay under 1 s. Otherwise retries break the SLA they were meant to protect.
4. **Propagate deadlines** downstream where possible, so work is not done for a caller who has already given up.

**Trade-offs and what can go wrong**
Too tight a timeout causes false failures during normal jitter; too loose and threads pile up. Revisit it with real percentile data.

**How I'd monitor it**
Vendor p50/p95/p99 latency, timeout count, connection-pool pending/active counts, and Tomcat busy threads — the early warning before an outage.

**60-second answer**
A remote call without a timeout lets one slow vendor eat every request thread — I have seen a vendor slowdown take down our health checks. I set connect, read and pool-acquire timeouts explicitly,
derived from our SLA budget and the vendor's real p99, and I make sure retries plus backoff still fit inside the overall deadline. Then I watch vendor percentiles and pool saturation as the early warning.

### Q3 [senior] A third-party API is slow and flaky. How do you still give your own clients a proper, predictable response?
tags: resilience, circuit-breaker, retry, fallback, bulkhead, timeouts, resilience4j

**The live scenario**
Our checkout calls a shipping-rates vendor to show delivery options. The vendor is slow (p99 of 3 s) and returns 502/503 about 2% of the time, worse during their deploys.
Checkout conversion dropped whenever they had a bad hour, because our page hung or showed a generic 500.

**What the interviewer is really checking**
A **layered** resilience design — not "add a retry" — plus the product thinking of what a *proper response* means when the vendor fails.

**How I answer it**
1. **Define a proper response with the business first.** For shipping rates, a degraded but useful answer is fine: cached rates, or a standard flat rate with an "estimate" flag.
   For a payment authorisation, the answer must be truthful ("pending"), never a guess. The fallback is a product decision.
2. **Layer the protections** (Resilience4j in Spring Boot), from the inside out:
   - **Timeout:** a hard 800 ms budget for this call (Q2).
   - **Retry:** at most 1–2 retries, only on transient failures (connect errors, 502/503/504, 429 honouring Retry-After), with exponential backoff and jitter, and only for idempotent requests (Q4).
   - **Circuit breaker:** when the failure or slow-call rate crosses about 50% over a window, stop calling for 30 s and go straight to the fallback. This protects us *and* lets the vendor recover (Q5).
   - **Bulkhead:** a dedicated, bounded thread pool or semaphore for this vendor, so its slowness cannot exhaust shared threads (Q6).
   - **Fallback:** cached last-known-good rates (with a TTL), or a flat-rate default, marked `"source":"estimated"`.
3. **Return a contract-stable response.** Our API returns 200 with the degraded data and a flag, or a well-defined error (503 with `Retry-After`, in RFC 9457 problem-details format) when no safe fallback exists.
   It never returns a raw vendor 500 or a hang.
4. **Make it async where possible.** If the answer is not needed in real time (for example, a label printed later), accept with 202 and fetch it in the background (Q11).
5. **Observe and tune** with per-vendor dashboards, plus breaker state-change alerts, so we can tell the vendor before they tell us.

**Trade-offs and what can go wrong**
- Retries multiply load on a struggling vendor; a breaker without a retry budget can still create a retry storm.
- Stale-cache fallbacks need a clear maximum age and a visible flag; silently wrong prices are worse than a clear error.
- Annotation ordering in Resilience4j matters (by default Retry wraps CircuitBreaker, which wraps TimeLimiter and Bulkhead). Know it before you rely on it.

**How I'd monitor it**
Per-vendor latency and error percentiles, retry count, breaker state transitions (an alert on OPEN), bulkhead rejections, fallback-served ratio, and checkout conversion next to all of them.

**Numbers I quote**
After this, checkout p99 stayed under 1.2 s during vendor incidents (it used to hang for 30 s or more). About 4% of requests were served from fallback on bad days. The conversion dip disappeared.

**Follow-ups to expect**
- *Why not just retry 5 times?* → It adds load exactly when the vendor is weakest, and blows our latency budget. Bounded retries plus a breaker is the right combination.
- *How do you test it?* → WireMock fault injection (delays, 503s, connection resets) in integration tests, plus a chaos test in staging (Q12).
- *What do you tell the client app?* → A stable contract: degraded data with a flag, or a 503 with Retry-After and a problem-details body.

**60-second answer**
First I agree with the business what a proper response is when the vendor fails — cached or estimated data with a flag, or an honest "pending". Then I layer the protections: a strict timeout from our SLA budget, at most a couple of retries with jittered backoff
on transient errors for idempotent calls, a circuit breaker that fails fast to the fallback, and a bulkhead so the vendor can't exhaust our threads. Our API always returns a stable contract — degraded 200 or a 503 problem-details with Retry-After — never a hang or a raw vendor 500.
Every layer is monitored, and the result in my last project was stable checkout latency during vendor incidents.

**Minimal config**
```yaml
resilience4j:
  circuitbreaker.instances.shipping: { failureRateThreshold: 50, slowCallDurationThreshold: 800ms, waitDurationInOpenState: 30s }
  retry.instances.shipping: { maxAttempts: 2, waitDuration: 100ms, enableExponentialBackoff: true }
  bulkhead.instances.shipping: { maxConcurrentCalls: 40 }
```

### Q4 [mid] Which failures do you retry, which do you never retry, and how do you avoid making things worse?
tags: retry, backoff, jitter, idempotency, retry-storm

**The live scenario**
A team retried every failure 5 times with no delay. When the vendor had a hiccup, our traffic to them went up 6x in seconds — a **retry storm** that turned a 30-second blip into a 15-minute outage.
They also retried a `POST /payments` that had timed out, and charged two customers twice.

**What the interviewer is really checking**
Error classification, idempotency awareness, and storm prevention.

**How I answer it**
1. **Retry:**
   - connection failures before the request was sent;
   - 502, 503, 504;
   - 429 (only after honouring `Retry-After`);
   - read timeouts — **only** on idempotent operations.
2. **Never retry:**
   - 400, 401, 403, 404, 409, 422 — the request itself is wrong, so it will fail again;
   - non-idempotent calls (POST that creates or charges) **unless** the vendor supports an **idempotency key** (Q8).
3. **How to retry:**
   - exponential backoff **with jitter**, so clients don't retry in lock-step;
   - a small maximum (1–3 attempts);
   - a total deadline;
   - retry at **one layer only** — if the gateway, the service and the client library all retry 3 times, that is 27 calls.
4. **Retry budget:** cap retries at around 10% of traffic. Combined with a circuit breaker, retries stop when the vendor is clearly down.

**Trade-offs and what can go wrong**
A retried timeout may have succeeded on the vendor side. For anything with side effects, retries require an idempotency key or a status check first.

**How I'd monitor it**
Retry rate as a share of requests, attempts per request histogram, and outbound request rate vs inbound — a gap is a retry storm.

**60-second answer**
I retry only transient failures — connection errors, 502/503/504, and 429 after Retry-After — and timeouts only for idempotent calls. I never retry 4xx validation or auth errors, or a non-idempotent POST unless the vendor supports idempotency keys.
I use exponential backoff with jitter, a small attempt limit and an overall deadline, retry at one layer only, and add a circuit breaker so retries can't turn a vendor blip into a storm.

### Q5 [senior] Explain the circuit breaker — its states, how you tuned it, and what your client sees when it's open.
tags: circuit-breaker, resilience4j, fail-fast, fallback

**The live scenario**
A fraud-check vendor went fully down for 10 minutes. Without a breaker, every checkout waited out the 2 s timeout before failing, so checkout latency went from 300 ms to 2.3 s,
and our thread pools stayed saturated the whole time.

**What the interviewer is really checking**
That you understand **fail-fast** as protection for *both* sides, and can talk about tuning with real numbers.

**How I answer it**
1. **CLOSED:** calls flow normally, and failures and slow calls are counted over a sliding window (for example the last 100 calls, or the last 60 s).
2. **OPEN:** when the failure or slow-call rate exceeds a threshold (say 50%, with at least 20 calls), the breaker trips. Calls fail **immediately** to the fallback, with no timeout wait.
   That gave checkout back its 300 ms latency and freed threads, and it stopped hammering the vendor.
3. **HALF_OPEN:** after a wait (30 s), let a few trial calls through. If they succeed, close; if not, open again.
4. **Tuning:**
   - minimum number of calls (so 2 failures out of 3 calls at 3 a.m. don't trip it);
   - a **slow-call threshold** — slow is often worse than failed;
   - which exceptions count (a 404 is not a vendor failure);
   - one breaker per vendor, sometimes per endpoint.
5. **The client sees** a fast, defined response. For fraud checks we chose a business rule: allow low-value orders, hold high-value ones as "pending review". Clear, fast and safe.

**Trade-offs and what can go wrong**
- A breaker shared across very different endpoints trips everything because of one bad endpoint.
- Thresholds that are too sensitive cause flapping.

**How I'd monitor it**
State-transition events (alert on OPEN), the not-permitted call count, and the fallback share. A breaker that opens often is a vendor-relationship conversation.

**60-second answer**
A circuit breaker counts failures and slow calls in a sliding window. Past a threshold it opens and fails fast to a fallback, so we stop wasting threads and the vendor gets room to recover. After a wait, half-open lets a few trial calls decide whether to close.
I tune the minimum calls, the slow-call threshold and which errors count, one breaker per vendor. The client sees a fast, defined business answer — in our case "approved if low value, pending review if high" — instead of a 2-second hang.

### Q6 [senior] One partner API's slowness took down all our endpoints, even ones that never call that partner. Why, and how do you prevent it?
tags: bulkhead, thread-pool, isolation, resource-exhaustion

**The live scenario**
Our service exposed 12 endpoints. Only `/quotes` called Partner A. When Partner A slowed down, all 200 Tomcat threads were stuck in `/quotes`, so `/orders`, `/profile` and even `/health` stopped answering.

**What the interviewer is really checking**
That you understand shared resource pools as a blast-radius problem, and know the **bulkhead** pattern.

**How I answer it**
1. The shared resources were the Tomcat thread pool and the outbound HTTP connection pool. One slow dependency consumed them all — the failure spread sideways.
2. A **bulkhead** isolates resources per dependency, like watertight compartments in a ship:
   - a semaphore bulkhead: at most 30 concurrent calls to Partner A; beyond that, reject immediately to the fallback;
   - or a thread-pool bulkhead: a dedicated, bounded executor for Partner A calls.
3. Use **separate HTTP connection pools per vendor**, with their own max-connections and pool-acquire timeout.
4. Combine with timeouts and a breaker. The bulkhead limits *how many* threads can be stuck, and the timeout limits *how long*.
5. On Java 21 with virtual threads, thread exhaustion is less likely, but you still need a concurrency limit — the vendor and the connection pool are still finite.

**Trade-offs and what can go wrong**
A bulkhead that is too small rejects legitimate traffic at peak. Size it from Little's Law: concurrency ≈ throughput × latency (for example 100 rps × 0.3 s = 30).

**How I'd monitor it**
Bulkhead available permits and rejections, per-vendor pool usage, and Tomcat busy threads per endpoint.

**60-second answer**
All endpoints shared the same Tomcat threads and connection pool, so one slow partner held every thread — the failure spread sideways. I isolate each dependency with a bulkhead (a semaphore or dedicated pool) and a per-vendor connection pool sized with Little's Law,
plus timeouts and a breaker. A slow partner can then only degrade its own feature. Virtual threads reduce thread exhaustion, but I still cap concurrency per vendor.

### Q7 [mid] The vendor returns errors in their own format. What does your API return to its clients?
tags: error-handling, problem-details, rfc9457, error-mapping, api-contract

**The live scenario**
Our mobile app showed raw messages like `"ERR_UPSTREAM_4471: SOAP fault at gw-node-3"`. We were leaking the vendor's stack details and internal hostnames, and every vendor change broke the app's error handling.

**What the interviewer is really checking**
Contract ownership: **your** API has **your** error model. Plus correct status-code semantics.

**How I answer it**
1. **Translate at the adapter boundary.** The vendor's errors become our domain exceptions (`AddressInvalidException`, `PartnerUnavailableException`), and a `@RestControllerAdvice` maps those to HTTP.
2. **Status-code semantics from *our* client's point of view:**
   - the vendor rejects the user's input → **422** or **400**, with a field-level message;
   - vendor down or timed out → **503** (with `Retry-After`) or **504**, and never pretend it was the client's fault;
   - the vendor says "not found" → it depends on meaning; often a 404 of *our* resource, or a business outcome inside a 200.
3. **Body format:** RFC 9457 problem details (`type`, `title`, `status`, `detail`, `instance`, plus a `correlationId`). Spring Boot supports it natively (`ProblemDetail`).
4. **Never leak** vendor hostnames, stack traces or raw messages. Log them server-side with the correlation id, and return a safe message.
5. **Stable error codes** (`"code":"ADDRESS_UNVERIFIABLE"`) so clients can branch on them; messages are for humans.

**Trade-offs and what can go wrong**
Over-generic errors ("something went wrong") make support impossible. The correlation id is the bridge between the safe message and the detailed log.

**How I'd monitor it**
Count by our error code and the vendor's original code, in Splunk, keyed by correlation id.

**60-second answer**
My API owns its error contract. The adapter translates vendor errors into domain exceptions, and a controller advice maps them to correct statuses — 4xx when the user's input is wrong, 503 or 504 when the vendor fails.
I return RFC 9457 problem details with a stable error code and a correlation id. Vendor details and hostnames stay in our logs, never in the response.

### Q8 [senior] We called a payment provider, the call timed out, and we don't know if the customer was charged. What do you do?
tags: idempotency-key, payments, timeouts, reconciliation, exactly-once

**The live scenario**
A `POST /charges` to the payment provider timed out after 5 s. The provider had in fact processed it. Our code retried, and the customer was charged twice; support got 40 complaints in one day.

**What the interviewer is really checking**
That you know a timeout means **unknown**, not **failed**, and the patterns for safe retries with side effects.

**How I answer it**
1. **A timeout is an unknown outcome.** Never treat it as a failure for a call with side effects.
2. **Idempotency key:** generate a unique key per *business intent* (for example the order id plus the attempt purpose) and send it on every attempt (`Idempotency-Key` header — Stripe, Adyen and most providers support it).
   The provider returns the original result for a repeated key instead of charging again. Persist the key **before** the first call.
3. **No key support?** Before retrying, **query the status** by our reference ("did charge for order 42 happen?"), then decide.
4. **State machine on our side:**
   - `PENDING` → `SUCCEEDED` or `FAILED`;
   - a timeout leaves it `PENDING`;
   - the customer sees "payment processing", not "failed";
   - a background reconciler (status poll, or the provider's webhook) resolves it.
5. **Daily reconciliation** against the provider's settlement report as the safety net.
6. **Expose idempotency on our own API too**, so *our* clients can safely retry `POST /orders`.

**Trade-offs and what can go wrong**
The idempotency key must be stable across retries and different across genuinely new intents. Getting that scope wrong either blocks legitimate payments or allows duplicates.

**How I'd monitor it**
Count of payments stuck in PENDING beyond N minutes, reconciliation mismatches (alert on any), and duplicate-key hits.

**60-second answer**
A timeout means "unknown", not "failed". For payments I send an idempotency key that is persisted before the first attempt and reused on every retry, so the provider deduplicates. If the provider has no key support, I query the status before retrying.
Our side keeps a PENDING state, so the customer sees "processing", and a reconciler resolves it by status poll or webhook, backed by daily settlement reconciliation. And our own POST APIs accept idempotency keys for the same reason.

### Q9 [senior] The vendor started returning 429 Too Many Requests during our peak. How do you handle their rate limit?
tags: rate-limiting, 429, retry-after, throttling, queueing

**The live scenario**
An SMS vendor allowed 100 requests/s per account. A marketing campaign pushed 400/s. They returned 429s, our naive retries made it worse, and 30% of OTP messages were delayed past their 5-minute validity.

**What the interviewer is really checking**
Client-side throttling, prioritisation, and using queues to smooth bursts.

**How I answer it**
1. **Honour `Retry-After`** on a 429, and never retry immediately.
2. **Throttle client-side** so we never exceed their limit: a token-bucket rate limiter (Resilience4j `RateLimiter`, or a shared Redis-based limiter when many pods share one vendor quota). Each pod's share is the quota ÷ pod count, or a central limiter.
3. **Decouple with a queue:** requests go onto a queue (Kafka or SQS), and workers drain it at exactly the vendor's rate. Bursts become a backlog instead of errors.
4. **Prioritise:** OTP/transactional traffic in a separate high-priority lane with reserved quota, and marketing in a bulk lane that can wait.
5. **Commercial fix:** negotiate a higher limit or a second account for bulk traffic, or a secondary vendor for failover.

**Trade-offs and what can go wrong**
Queueing adds latency. For time-bound messages like OTPs, set a TTL and drop expired items rather than sending a useless message late.

**How I'd monitor it**
429 rate per vendor, limiter wait time, queue depth and age per priority lane, and OTP delivery-latency percentiles.

**60-second answer**
I treat a vendor's rate limit as a capacity limit we must respect. I honour Retry-After, throttle client-side with a token bucket (shared across pods if the quota is shared), and put a queue in front so bursts become backlog rather than errors.
Critical traffic like OTPs gets its own priority lane with reserved quota, expired items are dropped, and the long-term fix is commercial — a higher quota or a secondary vendor.

### Q10 [senior] When is it acceptable to serve cached or stale data from a third-party API, and how do you design that?
tags: caching, fallback, stale-while-revalidate, ttl, data-freshness

**The live scenario**
A product page called a currency-rates API on every request: 3 million calls a day, mostly returning the same value, and when the vendor was down, pages failed.

**What the interviewer is really checking**
Data-freshness judgement per use case, and caching mechanics that double as resilience.

**How I answer it**
1. **Classify the data by acceptable staleness, with the business:**
   - FX rates for *display*: minutes are fine;
   - FX rates for *settlement*: must be the exact rate, and must be stored with the transaction;
   - stock levels: seconds, and the final check happens at checkout;
   - credit decisions: never cached.
2. **Cache design:**
   - `@Cacheable` with Caffeine locally, or Redis for sharing across pods;
   - a TTL matching the agreed staleness;
   - **stale-while-revalidate:** serve the cached value and refresh asynchronously, with a single in-flight refresh to avoid a stampede;
   - **stale-if-error:** when the vendor fails, serve the last-known-good value up to a maximum age, flagged as such.
3. **Pre-fetch** for small, hot datasets (rates refreshed every 60 s by a scheduler), so requests never call the vendor at all.
4. **Expose freshness** in our response (`asOf` timestamp), so clients can decide.

**Trade-offs and what can go wrong**
Caching per-user or permission-filtered data shared across users is a security bug. Cache keys must include everything that changes the answer.

**How I'd monitor it**
Hit ratio, age of served values, stale-served count during vendor errors, and vendor call volume (which should drop sharply).

**Numbers I quote**
Vendor calls went from 3M/day to about 1,500/day (one refresh per minute). The vendor outage that week caused zero page errors.

**60-second answer**
It depends on how stale the data can be for that use case, so I agree that with the business — display FX rates can be minutes old, settlement rates never. Then I cache with a matching TTL, use stale-while-revalidate to hide latency and stale-if-error up to a maximum age as a fallback,
pre-fetch small hot datasets, and expose an `asOf` timestamp. It cut vendor calls by over 99% and turned a vendor outage into a non-event.

### Q11 [architect] The vendor takes 30 seconds to respond. How do you design the API so your clients aren't left waiting?
tags: async, 202-accepted, webhooks, polling, long-running-operations

**The live scenario**
A KYC (identity verification) vendor takes 10–60 seconds per check. Our onboarding API held the HTTP request open, and mobile clients on bad networks timed out, retried, and started a second check.

**What the interviewer is really checking**
The asynchronous request-reply pattern, webhook handling, and idempotency across the whole flow.

**How I answer it**
1. **Accept, don't wait:** `POST /verifications` validates, stores a `PENDING` record, enqueues the work, and returns **202 Accepted** with `Location: /verifications/{id}`.
   Make it idempotent with a client-supplied key, so a mobile retry returns the same id.
2. **A worker calls the vendor** with the resilience stack (timeouts, retries, breaker), and updates the status.
3. **Tell the client:**
   - polling `GET /verifications/{id}` (simple; return `Retry-After` hints);
   - or push — a webhook to a B2B client, or a mobile push/WebSocket/SSE for our app.
4. **If the vendor calls us back** with a webhook:
   - verify the signature (HMAC) and timestamp to stop replays;
   - respond 2xx fast and process async;
   - treat delivery as at-least-once, so the handler is idempotent;
   - still poll as a safety net in case a webhook is lost.
5. **Timeouts at the business level:** a check stuck PENDING for over 10 minutes escalates to manual review.

**Trade-offs and what can go wrong**
More moving parts (queue, worker, state) and an eventually consistent UX. Worth it when the operation is genuinely slow or unreliable.

**How I'd monitor it**
Time-in-PENDING percentiles, stuck-job count, webhook signature failures, and the duplicate-webhook rate.

**60-second answer**
For a slow vendor I switch to async request-reply: the POST stores a pending record and returns 202 with a status URL, idempotent on a client key so retries don't start a second job. A worker calls the vendor with the full resilience stack, and the client polls or gets a push.
Vendor webhooks are signature-verified, acknowledged fast, processed idempotently, and backed by polling in case one is lost. Anything stuck pending escalates to a human.

### Q12 [mid] How do you test and observe third-party integrations so you're not surprised in production?
tags: testing, wiremock, contract-testing, observability, splunk, correlation-id

**The live scenario**
Our integration tests used a mock that always returned a perfect 200 in 5 ms. The first time the real vendor returned a 503 with an HTML body, our JSON parser threw and the service returned 500s.
We discovered it from customer complaints, not from monitoring.

**What the interviewer is really checking**
Testing the **unhappy paths**, contract safety, and the observability you build before go-live.

**How I answer it**
1. **Unit-test the adapter** with WireMock (or MockRestServiceServer). Script the failures:
   - delays beyond the timeout;
   - 429 with Retry-After;
   - 500 with an HTML body;
   - malformed JSON;
   - connection reset.

   Assert *our* behaviour each time: fallback served, breaker opens, correct problem-details response.
2. **Contract tests:** record or verify the vendor's schema (an OpenAPI spec, or Pact/Spring Cloud Contract where both sides cooperate), and run them in CI so a vendor-side change is caught early.
3. **Sandbox tests** against the vendor's test environment in a nightly job, not on every build (sandboxes are flaky).
4. **Chaos in staging:** inject latency and errors (for example with Toxiproxy) and confirm alerts fire and dashboards show the right thing.
5. **Observability before go-live:**
   - a correlation id propagated to the vendor (as a header, if they accept one) and in every log line;
   - structured logs with vendor, endpoint, status, latency and attempt;
   - Micrometer metrics per vendor;
   - a Splunk dashboard: latency percentiles, error rate by code, breaker state, fallback share;
   - alerts on the SLO, not on single errors.

**Trade-offs and what can go wrong**
Logging full request/response bodies can leak personal data. Mask fields, and log bodies only at debug level, behind a flag.

**How I'd monitor it**
The dashboard above, plus a synthetic probe that calls the vendor's health or test endpoint every minute, so we see their outage before our users do.

**60-second answer**
I test the unhappy paths deliberately: WireMock scripts timeouts, 429s, HTML error pages, malformed JSON and resets, and the tests assert our fallback and error contract. Contract tests catch vendor schema changes in CI, sandbox runs happen nightly, and chaos tests in staging prove the alerts work.
Before go-live I add correlation ids, structured per-vendor logs and metrics, a Splunk dashboard, SLO-based alerts and a synthetic probe — so we see a vendor problem before customers do.

### Q13 [architect] One request needs data from four downstream APIs, under an 800 ms SLA. How do you design it?
tags: aggregation, parallel-calls, completablefuture, partial-response, latency-budget

**The live scenario**
A "customer 360" screen needs profile, orders, loyalty points and recommendations, each from a different service (two of them external).
Called sequentially, p99 was 2.4 s, and if recommendations failed, the whole screen failed.

**What the interviewer is really checking**
Latency budgeting, parallel composition, and **partial responses** — essential vs optional data.

**How I answer it**
1. **Classify the dependencies:** profile is **essential** (no profile, no screen); orders are important; loyalty and recommendations are **optional**.
2. **Call in parallel:** `CompletableFuture` with a dedicated bounded executor, WebClient with `Mono.zip`, or virtual threads with structured concurrency on newer Java.
   Latency becomes max(calls), not sum(calls).
3. **Budget each call:** an overall 800 ms deadline, and each call gets its own timeout within it. Optional calls get a *shorter* timeout (300 ms). If they are late, we drop them rather than wait.
4. **Partial responses:**
   - an essential failure → an error (503 problem details);
   - an optional failure → return the rest, with that section `null` or empty and a `"degraded": ["recommendations"]` list, so the UI hides the widget gracefully.
5. **Reduce calls:** cache slow-changing parts (loyalty tier), or pre-compute a read model from events (Kafka → a materialised customer view) if this screen is hot. Often that is the real architectural answer.
6. Optionally use a **BFF** (backend for frontend) that owns this aggregation, so mobile and web aren't each doing four calls.

**Trade-offs and what can go wrong**
Unbounded parallel fan-out under load multiplies downstream traffic, so bound the executor and keep a bulkhead per dependency. A materialised view adds eventual consistency.

**How I'd monitor it**
Per-dependency latency within the request (tracing spans), the degraded-section rate, and end-to-end p99 against the 800 ms SLA.

**60-second answer**
I classify the dependencies as essential or optional, call them in parallel so latency is the max rather than the sum, and give each call its own timeout inside the 800 ms budget — shorter for optional ones. An essential failure returns a clean 503; an optional one returns a partial response with a degraded flag, so the UI hides that widget.
For a hot screen I go further and cache or pre-compute a read model from events, often behind a BFF. Tracing spans show which dependency is eating the budget.
