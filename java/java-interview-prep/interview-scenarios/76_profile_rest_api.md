---
id: profile-java-genai-rest-api
title: Java + GenAI profile (7/9): REST API design, 15 functional-requirement questions
stack: java
skill: rest-api
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Design the REST resource model for a travel booking API.
tags: rest, resource-design, http-methods, status-codes, uri-design, api-design, profile-java-genai

**Start here: the concepts**
- **Resources are nouns** (`/bookings`), HTTP methods are verbs: GET read, POST create, PUT replace, PATCH partial update, DELETE remove.
- **Status codes:** 200 OK, 201 Created, 202 Accepted, 204 No Content, 400, 401, 403, 404, 409 Conflict, 412, 422, 429, 500, 503.
- **Safe** (GET, HEAD) and **idempotent** (GET, PUT, DELETE) methods.

**The live scenario (functional requirement)**
*FR: "Customers search trips, create a booking, add travellers, cancel; agents look up any booking; partners get notifications."*

**What the interviewer is really checking**
Clean URIs, correct methods and status codes, and modelling actions that aren't CRUD.

**How I answer it**
1. Collections and items: `GET /bookings?status=CONFIRMED`, `POST /bookings` -> **201** + `Location: /bookings/B123`, `GET /bookings/B123`.
2. Sub-resources for ownership: `POST /bookings/B123/travellers`, `DELETE /bookings/B123/travellers/T1`.
3. **Actions that aren't CRUD** (cancel has rules, refunds, fees): model as a resource or state change: `POST /bookings/B123/cancellation` -> 201/202, rather than `DELETE /bookings/B123` (we never truly delete a booking).
4. Search with many parameters: `GET /trips?from=BOM&to=LHR&date=2026-12-01`; for very complex criteria, `POST /trip-searches` creating a search resource.
5. Status codes: validation 400 (or 422), not found 404, business rule violation (already cancelled) **409**, concurrent edit 412.
6. Consistent naming: plural nouns, kebab-case paths, camelCase JSON, ISO-8601 dates, money as amount + currency.

**Trade-offs and what can go wrong**
- Verbs in URLs (`/cancelBooking`) make RPC-style APIs that are hard to cache and reason about.
- Deep nesting (`/customers/1/bookings/2/travellers/3/documents`) couples clients to hierarchy; keep 2 levels.
- 200 with an error body breaks clients and monitoring.

**How I'd monitor it**
Status code distribution per endpoint, 4xx spikes after releases (contract breaks).

**Follow-ups to expect**
- *400 vs 422?* -> 400 malformed/invalid input; 422 well-formed but semantically invalid. Pick one convention.
- *401 vs 403?* -> 401 not authenticated; 403 authenticated but not allowed.
- *Is PATCH idempotent?* -> Not guaranteed; depends on the patch format.

**60-second answer**
"Resources are nouns and methods are verbs: POST /bookings returns 201 with a Location header, GET reads, travellers are a sub-resource. Business actions like cancel become a resource, POST /bookings/{id}/cancellation, because a cancellation has rules and fees and we never really delete a booking. Status codes carry meaning: 409 for an already-cancelled booking, 412 for a concurrent edit, never 200 with an error body. Plus consistent conventions: plural nouns, ISO dates, money as amount and currency."

### Q2 [senior] Make POST /payments safe to retry with idempotency keys.
tags: idempotency, idempotency-key, retries, payments, duplicate-prevention, api-design, profile-java-genai

**Start here: the concepts**
- **Idempotent:** doing it twice has the same effect as once. POST is not idempotent by default.
- **Idempotency-Key header:** the client sends a unique key per logical operation; the server stores the outcome and returns it for repeats (an IETF draft standardises the header).

**The live scenario (functional requirement)**
*FR: "Mobile apps on flaky networks retry payment requests; a customer must never be charged twice."* A timeout after the server charged the card made the app retry, and 0.3% of customers were double-charged.

**What the interviewer is really checking**
A correct implementation including concurrency and storage, not just "use a key".

**How I answer it**
1. Client generates a UUID per payment attempt and sends `Idempotency-Key`; it reuses the key on retries.
2. Server: `INSERT INTO idempotency (key, client_id, request_hash, status=IN_PROGRESS)` with a **unique constraint** on (client_id, key). Insert succeeds -> process. Conflict -> look at the stored row.
3. Stored row **COMPLETED** -> return the stored response (same status and body). **IN_PROGRESS** -> 409 (or wait briefly) so concurrent duplicates don't both charge.
4. **Same key, different body** (hash mismatch) -> 422: misuse.
5. Call the payment provider with **its** idempotency key too, so our retries to them are safe.
6. Expire keys after 24–48 hours.

**Trade-offs and what can go wrong**
- Storing the key in a cache only (no durable store) can lose it in a failover -> duplicates.
- Key scoped globally instead of per client lets clients collide.
- Crash after charging but before saving the response: reconcile with the provider by key.

**How I'd monitor it**
Replayed-request count, 409 in-progress rate, reconciliation mismatches with the provider (should be 0).

**Follow-ups to expect**
- *Why not dedupe by amount + card + time?* -> Legitimate identical purchases exist.
- *Which methods need keys?* -> Non-idempotent POSTs with side effects.
- *Natural idempotency?* -> PUT to a client-chosen id (`PUT /payments/{clientGeneratedId}`) achieves the same.

**60-second answer**
"The client sends an Idempotency-Key per logical payment and reuses it on retries. The server inserts the key with a unique constraint before doing anything: if the insert wins, we process; if the key exists and is completed, we return the stored response; if it's in progress, 409, so concurrent duplicates can't both charge; a different body with the same key is a 422. We also pass an idempotency key to the payment provider, keep keys 24 to 48 hours, and reconcile with the provider daily."

### Q3 [mid] PUT vs PATCH: how do you implement partial updates correctly?
tags: put, patch, json-merge-patch, json-patch, partial-update, rest, profile-java-genai

**Start here: the concepts**
- **PUT:** replace the whole resource with the given representation (idempotent).
- **PATCH:** partial modification. Formats: **JSON Merge Patch** (RFC 7396, `application/merge-patch+json`: send only changed fields, `null` deletes) and **JSON Patch** (RFC 6902: a list of operations).

**The live scenario (functional requirement)**
*FR: "Customers update their profile from different screens: one screen changes only the phone number, another only meal preference; neither should wipe the other's fields."* Using PUT with partial bodies set unspecified fields to null.

**What the interviewer is really checking**
Semantics, the null-vs-absent problem in Java, and concurrency.

**How I answer it**
1. PUT = full replacement; clients must send everything (fine for small resources edited as a whole).
2. For screens that edit pieces: **PATCH with JSON Merge Patch**.
3. **Absent vs null in Java:** a DTO can't distinguish "not sent" from "sent as null". Options: apply the patch on a `JsonNode`/`JsonMergePatch` (Jakarta JSON-P) to the current representation, then map back and **validate the result**; or use `Optional`-like wrapper fields (`JsonNullable` from openapi-generator).
4. Restrict patchable fields (no changing `customerId` or `tier`).
5. **Concurrency:** require `If-Match: <ETag>`; mismatch -> 412, so two screens don't overwrite each other blindly.

**Trade-offs and what can go wrong**
- JSON Patch is precise (array operations) but harder for clients.
- Binding PATCH to the same DTO as POST validation (`@NotNull` everywhere) rejects valid partial requests; validate the merged result.

**How I'd monitor it**
412 rates (contention), 400 on PATCH by field.

**Follow-ups to expect**
- *Is PATCH idempotent?* -> Merge patch setting values usually is; JSON Patch `add` to an array isn't.
- *Can PUT create?* -> Yes, when the client chooses the id (upsert).
- *Arrays in merge patch?* -> Replaced as a whole.

**60-second answer**
"PUT replaces the whole resource, which is why partial bodies wiped fields. For screens that edit one field I use PATCH with JSON Merge Patch: send only what changes, null means remove. In Java the trick is absent versus null, so I apply the patch to the current JSON representation, map it back and validate the merged result, allowing only patchable fields. And I require If-Match with an ETag, so two screens editing at once get a 412 instead of silently overwriting each other."

### Q4 [senior] What versioning strategy would you choose for a public API, and why?
tags: api-versioning, backward-compatibility, deprecation, sunset, evolution, rest, profile-java-genai

**Start here: the concepts**
- **Strategies:** URI (`/v1`), header (`API-Version`), media type, query param.
- **Compatible changes:** new optional fields, new endpoints, new optional params. **Breaking:** removing/renaming fields, changing types/semantics, new required inputs.
- **Deprecation signals:** `Deprecation` header (RFC 9745) and `Sunset` header (RFC 8594).

**The live scenario (functional requirement)**
*FR: "Partner travel agencies integrate with our booking API; some upgrade yearly; we must evolve weekly."*

**What the interviewer is really checking**
That versioning is a last resort and evolution is designed in.

**How I answer it**
1. **Design for evolution:** additive changes only; clients are told to ignore unknown fields (tolerant reader); enums documented as extensible.
2. **Major versions in the URI** (`/v1`, `/v2`) for public partner APIs: visible, easy to route at the gateway, easy to see in logs. (Spring Framework 7 supports path, header or media-type strategies natively.)
3. A new major only for real breaking changes, maybe once every year or two.
4. **Run versions side by side**, both mapped onto the same domain services; differences live in DTO mappers.
5. **Deprecation:** announce, add `Deprecation` + `Sunset` headers, contact partners using v1 (from gateway analytics), keep v1 for 12 months.

**Trade-offs and what can go wrong**
- Header versioning keeps URLs clean but is invisible in browser/curl testing and caches need `Vary`.
- Versioning per endpoint creates a matrix nobody can test.
- Silent semantic changes without a version are the worst breaking change.

**How I'd monitor it**
Traffic by version and partner, deprecated-endpoint calls trend, contract test results per version.

**Follow-ups to expect**
- *How do you detect breaking changes?* -> OpenAPI diff in CI (e.g. openapi-diff, oasdiff) fails the build on breaking changes.
- *Internal APIs?* -> Consumer-driven contracts instead of versions.
- *GraphQL versioning?* -> Evolve the schema, deprecate fields.

**60-second answer**
"I design so versioning is rare: additive changes, tolerant readers, an OpenAPI diff in CI that fails on breaking changes. For a public partner API, major versions go in the URI because it's visible and easy to route and monitor, and a new major appears only for genuine breaks. Versions run side by side on the same domain services with different mappers. Deprecation means Deprecation and Sunset headers, direct outreach to partners we see still calling v1, and a 12-month window."

### Q5 [mid] Offset or cursor pagination: which, and how do you implement it?
tags: pagination, cursor, keyset, offset, link-header, performance, profile-java-genai

**Start here: the concepts**
- **Offset:** `?page=10&size=50` -> `OFFSET 500 LIMIT 50`. Simple, supports jumping to a page; slow on deep pages, unstable when data changes.
- **Cursor/keyset:** `?after=<opaque cursor>&limit=50` -> `WHERE (created_at, id) < (:c, :id) ORDER BY ... LIMIT 50`. Fast and stable; no random page jumps.

**The live scenario (functional requirement)**
*FR: "Partners sync all bookings changed since their last sync (millions of rows) and the agent UI shows a paged table with page numbers."*

**What the interviewer is really checking**
Picking per use case and the details of keyset pagination.

**How I answer it**
1. **Agent UI (page numbers, shallow pages):** offset pagination with a max page size and an indexed sort.
2. **Partner sync (deep, changing data):** cursor pagination on `(updated_at, id)`:
   - Response: `{ "data": [...], "nextCursor": "eyJ1IjoiMjAyNi0..."}` (base64 of the last row's sort keys, opaque to clients).
   - Index on `(updated_at, id)`; each page is an index range scan, constant time at any depth.
3. Include `limit` with a max (e.g. 200); return `nextCursor: null` at the end.
4. Optionally `Link` headers (`rel="next"`) for HTTP-native clients.
5. Avoid total counts on huge sets (costly); offer `hasMore` instead.

**Trade-offs and what can go wrong**
- Offset with concurrent inserts duplicates or skips rows across pages.
- Cursors tied to a sort order: changing sort invalidates them.
- Non-unique sort keys without a tiebreaker (`id`) lose rows.

**How I'd monitor it**
Page latency vs depth, page-size distribution, partner sync durations.

**Follow-ups to expect**
- *Why opaque cursors?* -> Lets you change the implementation without breaking clients.
- *Changes during a sync?* -> Updated rows move to the end (newer `updated_at`) and will be seen in the next sync.
- *Spring Data support?* -> `ScrollPosition` / `Window` with keyset scrolling.

**60-second answer**
"I pick per use case. The agent table with page numbers uses offset pagination with capped page size and indexed sorting, since it's shallow. The partner sync over millions of changing rows uses keyset cursors on updated-at plus id: an opaque base64 cursor, an index range scan per page so it's constant time at any depth, no skipped or duplicated rows, and hasMore instead of an expensive total. Spring Data's keyset scrolling supports it directly."

### Q6 [mid] Define a consistent error contract for all APIs.
tags: error-handling, problem-details, rfc-9457, error-codes, api-contract, rest, profile-java-genai

**Start here: the concepts**
- **Problem Details (RFC 9457):** `type`, `title`, `status`, `detail`, `instance`, plus extension members.
- **Machine-readable codes** for clients; human-readable messages for developers; no internals.

**The live scenario (functional requirement)**
*FR: "Partners must handle errors programmatically (e.g. fare expired -> re-price automatically), and support must find the failing request from a partner's report."*

**What the interviewer is really checking**
Usability for clients, security, and operability.

**How I answer it**
1. `Content-Type: application/problem+json` for every error:

```json
{ "type": "https://api.example.com/errors/fare-expired", "title": "Fare expired",
  "status": 409, "detail": "Fare F12 expired at 10:42Z", "code": "FARE_EXPIRED",
  "traceId": "4bf92f...", "errors": [] }
```

2. `code` is stable and documented; `type` links to docs; `errors[]` for field validation details.
3. Correct HTTP status always; `Retry-After` on 429/503.
4. `traceId` lets support jump to logs/traces.
5. Implemented once in a shared Spring starter (`@RestControllerAdvice` + `ProblemDetail`).
6. Documented in OpenAPI as a reusable response component.

**Trade-offs and what can go wrong**
- Leaking SQL errors, stack traces, or internal hostnames.
- Different services inventing their own shapes.
- Codes that change meaning over time break partner automation.

**How I'd monitor it**
Error codes per partner and endpoint, unknown-error (500) rate.

**Follow-ups to expect**
- *Localisation?* -> Clients localise from the code; `detail` stays English for developers.
- *Validation errors format?* -> A list of `{field, code, message}`.
- *Should 404 reveal existence?* -> For sensitive resources return 404 instead of 403.

**60-second answer**
"Every error is RFC 9457 Problem Details: the right HTTP status, a stable documented code like FARE_EXPIRED that partners can automate on, a human-readable detail, field errors for validation, Retry-After when it's worth retrying, and the trace id so support finds the request in seconds. No stack traces or SQL. It's implemented once in a shared starter and documented as a reusable OpenAPI component, so all services look the same."

### Q7 [senior] Secure a REST API end to end: OAuth2, scopes and the OWASP API Top 10.
tags: api-security, oauth2, oidc, owasp-api-top-10, bola, rate-limiting, profile-java-genai

**Start here: the concepts**
- **OAuth2/OIDC:** tokens from an identity provider; APIs validate JWTs (issuer, audience, expiry, signature).
- **Scopes/roles** for what a client may do; **object-level checks** for which records.
- **OWASP API Top 10 (2023):** broken object-level authorization (BOLA), broken authentication, broken object property-level authorization, unrestricted resource consumption, broken function-level authorization, sensitive business flows, SSRF, misconfiguration, inventory management, unsafe consumption of third-party APIs.

**The live scenario (functional requirement)**
*FR: "Expose booking APIs to customers (mobile), agents (internal) and partners (B2B), each seeing only what they're allowed; pass a penetration test."*

**What the interviewer is really checking**
Practical controls mapped to real risks.

**How I answer it**
1. **AuthN:** customers via OIDC authorization code + PKCE (through a BFF for web), partners via client credentials or mTLS, agents via corporate SSO.
2. **AuthZ layers:** scopes at the gateway/route (`bookings:read`), roles for functions, **object-level ownership checks** in the service (customer X can read only their bookings): BOLA is #1.
3. **Property-level:** response DTOs per audience (partners don't see internal margin); request DTOs whitelist writable fields (no mass assignment of `status`).
4. **Resource consumption:** rate limits, max page size, payload size limits, timeouts.
5. **SSRF:** never fetch arbitrary user-supplied URLs (e.g. "import itinerary from URL") without an allow-list.
6. **Transport:** TLS 1.2+, HSTS; secrets in vaults; API inventory to avoid forgotten old endpoints.
7. Security tests: OWASP ZAP in CI, pen tests, authorisation tests per role.

**Trade-offs and what can go wrong**
- Relying only on the gateway; internal calls bypass it.
- Sequential ids make enumeration easy; UUIDs help but never replace authorisation checks.

**How I'd monitor it**
403 spikes per client (enumeration), rate-limit hits, auth failures, anomalous access patterns.

**Follow-ups to expect**
- *API keys?* -> Identify a client, not a user; fine for low-risk, combine with OAuth for sensitive data.
- *JWT in URL?* -> Never; it ends up in logs.
- *How to test BOLA?* -> Automated tests calling with user A's token for user B's resource.

**60-second answer**
"Authentication fits each audience: OIDC with PKCE through a BFF for customers, client credentials or mTLS for partners, SSO for agents. Authorisation is layered: scopes at the gateway, roles for functions, and object-level ownership checks in the service, because broken object-level authorisation is number one on the OWASP API list. Per-audience DTOs stop property leaks and mass assignment, and rate and size limits stop resource abuse. ZAP runs in CI, and tests try user A's token on user B's data."

### Q8 [senior] Implement rate limiting and throttling for a public API.
tags: rate-limiting, throttling, 429, retry-after, token-bucket, bucket4j, profile-java-genai

**Start here: the concepts**
- **Rate limiting:** cap requests per client per time window; respond **429 Too Many Requests** with `Retry-After`.
- **Algorithms:** token bucket (bursts allowed), sliding window, fixed window.
- **Where:** API gateway (preferred), service-level (Bucket4j/Resilience4j with Redis), or both.

**The live scenario (functional requirement)**
*FR: "Partners get 100 requests/s on the free tier and 1,000 on premium; the AI-powered itinerary endpoint is limited by LLM tokens per day, not request count."*

**What the interviewer is really checking**
Correct distributed implementation and good client experience.

**How I answer it**
1. **Gateway-level** request limits per API key/plan (Spring Cloud Gateway `RequestRateLimiter` with Redis, Kong, or managed gateway usage plans).
2. **Token bucket** per partner: capacity = burst (e.g. 2× rate), refill = plan rate; state in **Redis** so all gateway instances share it (Lua script for atomicity).
3. Response headers: `RateLimit-Limit`, `RateLimit-Remaining`, `RateLimit-Reset` (IETF draft) and `Retry-After` on 429.
4. **AI endpoint:** a **token budget** per partner per day, decremented by actual LLM usage after each call; reject with 429 and a clear code when exhausted; optionally degrade to a smaller model.
5. **Service-level protection** (load shedding) independent of per-client limits, protecting against total overload.
6. Exempt health checks; separate limits per endpoint cost (search is expensive, GET booking cheap).

**Trade-offs and what can go wrong**
- Local in-memory limits per instance multiply the effective limit by instance count.
- Redis outage: fail open (risk of overload) or fail closed (outage); usually fail open with service-level shedding as backstop.

**How I'd monitor it**
429s per partner and plan, Redis latency, partners near limits (upsell opportunities), token consumption per partner.

**Follow-ups to expect**
- *Rate limit vs quota?* -> Rate per second/minute; quota per day/month.
- *Throttling vs rejecting?* -> Throttling delays/queues; rejecting returns 429.
- *Client-side behaviour?* -> Exponential backoff honouring Retry-After.

**60-second answer**
"Per-plan limits live at the gateway as a token bucket per partner in Redis, so every gateway instance shares state, with burst capacity and RateLimit headers plus Retry-After on 429. The AI itinerary endpoint is limited by a daily LLM token budget per partner, charged with actual usage, with a clear error or a smaller-model fallback when it runs out. Separately, service-level load shedding protects us from total overload, and I watch 429s per partner and Redis health."

### Q9 [senior] Use HTTP caching and conditional requests: ETag, Cache-Control and If-Match.
tags: http-caching, etag, cache-control, conditional-requests, optimistic-concurrency, if-match, profile-java-genai

**Start here: the concepts**
- **Cache-Control:** `max-age`, `no-store`, `private`, `public`, `stale-while-revalidate`.
- **ETag:** a version identifier of a representation. `If-None-Match` -> **304 Not Modified** when unchanged. `If-Match` -> **412 Precondition Failed** when changed (optimistic locking).

**The live scenario (functional requirement)**
*FR: "The mobile app polls airport and airline reference data every launch (2 MB); booking edits from two agents must not overwrite each other."*

**What the interviewer is really checking**
Bandwidth/latency wins with caching, and concurrency control over HTTP.

**How I answer it**
1. **Reference data:** `Cache-Control: public, max-age=3600, stale-while-revalidate=86400` + `ETag`. CDN caches it; clients revalidate with `If-None-Match` and usually get a tiny **304**.
2. In Spring: `ResponseEntity.ok().eTag(version).cacheControl(CacheControl.maxAge(1, HOURS))`, or `ShallowEtagHeaderFilter` (saves bandwidth but still computes the body).
3. **Booking edits:** GET returns `ETag: "v17"` (from the JPA `@Version`); PUT/PATCH must send `If-Match: "v17"`; mismatch -> **412**, the agent reloads. Missing `If-Match` -> **428 Precondition Required**.
4. Personal data: `Cache-Control: private, no-store` where appropriate so shared caches never keep it.

**Trade-offs and what can go wrong**
- Caching authenticated responses at a CDN without `private`/`Vary` can leak data between users.
- Weak vs strong ETags: weak (`W/`) for semantic equivalence; byte-range needs strong.

**How I'd monitor it**
CDN hit ratio, 304 ratio, 412 rate (contention), bandwidth.

**Follow-ups to expect**
- *Last-Modified vs ETag?* -> Timestamps have one-second granularity; ETags are precise.
- *Cache invalidation at CDN?* -> Versioned URLs or purge APIs.
- *POST caching?* -> Generally not cached.

**60-second answer**
"For reference data I set Cache-Control with max-age and stale-while-revalidate plus an ETag, so the CDN serves most requests and app launches revalidate with If-None-Match and get a tiny 304 instead of 2 MB. For booking edits the ETag is the entity's version: updates must send If-Match, a stale version gets 412 so the second agent reloads instead of overwriting, and a missing header gets 428. Personal data is marked private or no-store so shared caches never hold it."

### Q10 [senior] Design an API for a long-running operation such as generating an AI trip report.
tags: long-running-operations, 202-accepted, polling, webhooks, async-api, sse, profile-java-genai

**Start here: the concepts**
- **202 Accepted:** request accepted, processing later.
- **Status resource:** `GET /operations/{id}` with state (PENDING/RUNNING/SUCCEEDED/FAILED) and a link to the result.
- **Notifications:** polling, webhooks, SSE/WebSocket.

**The live scenario (functional requirement)**
*FR: "A corporate travel manager requests an AI-generated quarterly travel spend report (30–90 s to build across 10,000 trips); the request must not time out and the UI shows progress."*

**What the interviewer is really checking**
The async request-reply pattern and its reliability details.

**How I answer it**
1. `POST /reports` (with an Idempotency-Key) -> **202 Accepted**, `Location: /reports/R9/status`, body `{id, status: "PENDING"}`.
2. A worker picks the job from a queue/topic, aggregates data, calls the LLM for the narrative summary, stores the PDF/JSON, updates progress.
3. `GET /reports/R9/status` -> `{status: "RUNNING", progress: 60}`; when done -> `SUCCEEDED` + `resultUrl` (`/reports/R9` or a pre-signed download link). Include `Retry-After` to pace polling.
4. **Push options:** SSE stream for the UI's progress bar; **webhooks** for partner systems (signed with HMAC, retried with backoff).
5. Failures: `FAILED` with a Problem Details error; jobs are idempotent and retried by the worker; timeouts cancel stuck jobs.
6. Results expire after N days.

**Trade-offs and what can go wrong**
- Holding an HTTP request open 90 s is fragile through proxies and mobile networks.
- Polling too often wastes resources; `Retry-After` guides clients.
- Webhooks need receivers to verify signatures and handle duplicates.

**How I'd monitor it**
Job queue depth and age, job duration, failure rate, webhook delivery success.

**Follow-ups to expect**
- *Cancel an operation?* -> `DELETE /reports/R9` or `POST /reports/R9/cancellation`.
- *Why not just stream?* -> Fine for chat; reports need a durable result and retries.
- *Webhook security?* -> HMAC signature + timestamp to prevent replay.

**60-second answer**
"I don't hold the request open. POST /reports, with an idempotency key, returns 202 with a Location to a status resource. A queue-driven worker builds the report, calls the LLM for the narrative and stores the result, updating progress. Clients poll the status, paced by Retry-After, the UI can get progress over SSE, and partner systems get a signed, retried webhook. Failures come back as a FAILED status with Problem Details, jobs are idempotent, and results expire after a set time."

### Q11 [mid] Contract-first or code-first with OpenAPI, and how do you keep the contract honest?
tags: openapi, contract-first, code-first, springdoc, contract-testing, api-governance, profile-java-genai

**Start here: the concepts**
- **OpenAPI:** a machine-readable API description; generates docs, clients, server stubs, mocks.
- **Contract-first:** write the spec, generate interfaces. **Code-first:** annotate code, generate the spec (springdoc-openapi).
- **Consumer-driven contracts:** consumers define expectations (Pact, Spring Cloud Contract).

**The live scenario (functional requirement)**
*FR: "Three teams (web, mobile, partners) start building against the new booking API before the backend is finished; the docs must never drift from reality."*

**What the interviewer is really checking**
Process: parallel development, governance and drift prevention.

**How I answer it**
1. **Contract-first** for this case: the spec is agreed in a PR review with consumers; frontend teams use a **mock server** (Prism/WireMock) generated from it immediately.
2. Backend generates Spring interfaces (openapi-generator `interfaceOnly`) and implements them; the compiler then flags mismatches.
3. **Lint** the spec (Spectral rules: naming, error format, pagination conventions).
4. **Breaking-change check** in CI (oasdiff) against the published version.
5. Contract tests verify the running service against the spec or against consumer contracts.
6. Code-first with springdoc is fine for internal services with one consumer, as long as the generated spec is published and diffed.

**Trade-offs and what can go wrong**
- Generated code can be awkward; generate interfaces/DTOs only, not whole controllers.
- Code-first specs drift into "whatever the code does" without review.

**How I'd monitor it**
Contract test results in CI, spec lint violations, breaking-change gate failures.

**Follow-ups to expect**
- *OpenAPI 3.1?* -> Aligns with JSON Schema 2020-12.
- *AsyncAPI?* -> The equivalent for event-driven APIs.
- *Generated clients?* -> Yes for partners (SDKs), versioned with the API.

**60-second answer**
"When several teams build in parallel I go contract-first: the OpenAPI spec is reviewed with consumers, frontends start against a generated mock server on day one, and the backend implements generated interfaces so the compiler catches drift. Spectral lints conventions, oasdiff blocks breaking changes in CI, and contract tests check the running service against the spec. For an internal service with one consumer, code-first with springdoc is fine, as long as the generated spec is published and diffed."

### Q12 [senior] Call an external REST API from Spring: RestClient, HTTP interfaces and timeouts.
tags: restclient, http-interface, webclient, timeouts, connection-pool, third-party-api, profile-java-genai

**Start here: the concepts**
- **RestClient (Spring 6.1+):** fluent synchronous client; **RestTemplate** is in maintenance mode. **WebClient:** reactive.
- **HTTP interfaces:** declarative clients (`@HttpExchange`, `@GetExchange`), backed by RestClient/WebClient; Boot 4 can auto-configure them as "HTTP service clients".
- **Timeouts:** connect, read/response, and connection-pool acquisition.

**The live scenario (functional requirement)**
*FR: "Integrate a hotel supplier API (p99 900 ms, occasionally hangs) for availability; our availability endpoint must answer within 2 s."*

**What the interviewer is really checking**
Modern client choice and production-grade configuration.

**How I answer it**
1. Declarative client:

```java
@HttpExchange("/v2") interface HotelSupplier {
    @GetExchange("/availability") Availability search(@RequestParam String city, @RequestParam LocalDate in);
}
```

   backed by a `RestClient` with the supplier's base URL and auth interceptor.
2. **Timeouts** on the underlying HTTP client (JDK HttpClient, Apache HttpClient 5 or Jetty): connect 500 ms, read 1.5 s; a pool with sensible max connections per route and an acquisition timeout.
3. **Resilience:** circuit breaker + bulkhead around the client (Resilience4j or Spring 7's `@ConcurrencyLimit`), at most one retry for idempotent GETs.
4. **Errors:** map 4xx/5xx with `defaultStatusHandler` to domain exceptions; log supplier correlation ids.
5. **Observability:** RestClient is instrumented by Micrometer (`http.client.requests`), with tracing headers propagated.
6. Contract with the supplier tested via WireMock stubs, including slow and malformed responses.

**Trade-offs and what can go wrong**
- Default timeouts can be infinite: a hanging supplier holds threads forever.
- Creating a new client per request loses connection pooling.
- Logging full responses may leak PII or blow up log volume.

**How I'd monitor it**
Supplier latency percentiles, error rates by status, breaker state, pool pending acquisitions.

**Follow-ups to expect**
- *RestTemplate still OK?* -> Works, but new code should use RestClient.
- *Feign?* -> OpenFeign is now feature-complete/maintenance; HTTP interfaces are the Spring-native replacement.
- *WebClient in MVC?* -> Only if you need reactive composition or streaming.

**60-second answer**
"I declare the supplier as an HTTP interface with `@GetExchange` methods, backed by a RestClient, since RestTemplate is in maintenance mode, with the base URL and auth interceptor configured once. The important part is the underlying HTTP client: connect and read timeouts that fit my 2-second budget and a bounded connection pool. Around it go a circuit breaker and bulkhead, at most one retry for GETs, and status handlers mapping errors to domain exceptions. Micrometer gives latency metrics and tracing for free."

### Q13 [senior] Your REST API's p99 is too high. How do you find and fix the cause?
tags: api-performance, latency, p99, profiling, payload, n-plus-one, profile-java-genai

**Start here: the concepts**
- **Percentiles:** p50 is typical, p99 is the tail users still feel; averages hide problems.
- **Where time goes:** network, serialisation, DB, downstream calls, GC, thread pool queueing, lock contention.
- **Tools:** distributed traces, JFR/async-profiler, DB slow-query logs, load tests.

**The live scenario (functional requirement)**
*FR: "The booking details API must have p99 under 300 ms."* p50 is 80 ms but p99 is 1.8 s.

**What the interviewer is really checking**
A measurement-driven method, not guesswork.

**How I answer it**
1. **Traces of slow requests** (tail-sampled): which span dominates? Here: a loyalty-service call (p99 1.2 s) and a 40-query N+1.
2. **Fix the biggest first:**
   - Loyalty call: parallelise with other calls, timeout 200 ms with a fallback, cache tier info.
   - N+1: entity graph/batch fetching (one or two queries).
3. **Payload:** response was 400 KB (whole booking history); add field selection or a summary representation, enable gzip/brotli compression.
4. **JVM:** check GC pauses and thread pool queueing (`tomcat_threads_busy` at max = queueing latency).
5. **Profile under load** with async-profiler/JFR for CPU hotspots (JSON serialisation, regex, logging).
6. **Verify** with a load test at production traffic patterns; track p99 per release.

**Trade-offs and what can go wrong**
- Optimising p50 does nothing for the tail.
- Caching everything adds staleness and invalidation bugs; cache what's read-heavy and tolerant.
- Load tests with unrealistic data (empty DB) mislead.

**How I'd monitor it**
p50/p95/p99 per endpoint with exemplars linked to traces, dependency latency breakdown, error budget burn.

**Follow-ups to expect**
- *Coordinated omission?* -> Load tools that wait for responses under-report latency; use open-model tools (wrk2, Gatling open injection, k6 arrival-rate).
- *HTTP/2?* -> Multiplexing helps clients with many parallel calls.
- *When to go async?* -> When work isn't needed for the response.

**60-second answer**
"I start from traces of the slow requests, not guesses. Here the tail came from a loyalty call with a 1.2-second p99 and a 40-query N+1. I parallelised the call with a 200 ms timeout and a cached fallback, fixed the N+1 with an entity graph, cut the 400 KB payload with a summary view and compression, and checked thread-pool queueing and GC. A profiler under load catches CPU hotspots, and a realistic open-model load test proves p99 is under 300 ms before release."

### Q14 [mid] HATEOAS and the Richardson maturity model: do you use them?
tags: hateoas, richardson-maturity-model, hypermedia, spring-hateoas, rest-constraints, api-design, profile-java-genai

**Start here: the concepts**
- **Richardson maturity model:** Level 0 (one endpoint, RPC), Level 1 (resources), Level 2 (HTTP verbs + status codes), Level 3 (hypermedia controls, HATEOAS).
- **HATEOAS:** responses include links to related resources and allowed actions; clients navigate by links.
- **Spring HATEOAS:** `EntityModel`, `CollectionModel`, `linkTo(methodOn(...))`, HAL format.

**The live scenario (functional requirement)**
*FR: "Whether a booking can be cancelled, modified or upgraded depends on fare rules; the mobile app keeps duplicating these rules and getting them wrong."*

**What the interviewer is really checking**
Pragmatism: where hypermedia adds real value.

**How I answer it**
1. Most production APIs are **Level 2**: resources, verbs, status codes; that's the pragmatic baseline.
2. Level 3 pays off where **available actions depend on server-side state**, exactly this case. The booking response includes:

```json
"_links": { "self": {...}, "cancel": {"href": "/bookings/B1/cancellation"}, "modify": {...} }
```

   The app shows "Cancel" only if the link exists, so fare rules live only in the backend.
3. Implement with Spring HATEOAS (`EntityModel.of(dto)` + conditional `add(link)`), HAL media type.
4. Don't force full hypermedia-driven clients; links as **affordances** for state-dependent actions give most of the benefit.

**Trade-offs and what can go wrong**
- Larger payloads and more complex serialisation.
- Few clients truly navigate by links; documentation remains essential.

**How I'd monitor it**
Action-attempt errors (e.g. 409 on cancel) should drop when clients follow links.

**Follow-ups to expect**
- *Is an API without HATEOAS RESTful?* -> Strictly by Fielding's definition, no; in industry "REST" usually means Level 2.
- *HAL vs JSON:API?* -> Different hypermedia formats; pick one platform-wide.
- *Pagination links?* -> A natural, widely used piece of hypermedia (`next`, `prev`).

**60-second answer**
"Most APIs I build are Level 2: resources, proper verbs and status codes. I add hypermedia where the allowed actions depend on server state, like whether a booking can be cancelled or modified under its fare rules. The response includes cancel or modify links only when they're allowed, and the app just shows buttons for the links it receives, so fare rules live in one place. Spring HATEOAS with HAL makes that easy. I don't push fully link-driven clients, just these affordances and pagination links."

### Q15 [architect] REST, GraphQL, gRPC or SSE: choose the right style for each consumer, including AI features.
tags: graphql, grpc, sse, websocket, api-styles, architecture-decision, profile-java-genai

**Start here: the concepts**
- **REST:** resource-oriented, cacheable, universal.
- **GraphQL:** clients ask for exactly the fields they need from one endpoint; great for varied UIs; caching and cost control are harder.
- **gRPC:** contract-first Protobuf over HTTP/2, fast, streaming; best for internal service-to-service.
- **SSE / WebSocket:** server push; SSE for one-way streams (LLM tokens), WebSocket for two-way.

**The live scenario (functional requirement)**
*FR: "A travel platform serves a web app, a mobile app, 200 B2B partners, 40 internal services, and an AI assistant that streams answers."*

**What the interviewer is really checking**
Matching API styles to consumers and constraints, not picking a favourite.

**How I answer it**
1. **Partners -> REST + OpenAPI:** universal, cacheable, easy to secure and version, SDKs generated.
2. **Web + mobile -> a GraphQL BFF** (Spring for GraphQL) when screens need varied combinations of trips, loyalty and offers in one round trip; or REST BFFs per channel if the team prefers simplicity. Protect GraphQL with query depth/complexity limits and persisted queries.
3. **Internal high-volume calls -> gRPC** (pricing engine called 50× per search) where latency and typed contracts matter; REST elsewhere for simplicity.
4. **AI assistant -> SSE** for token streaming (one-way, works over HTTP, easy with Spring), WebSocket only for true bidirectional features like voice.
5. **Events -> Kafka** with AsyncAPI, not polling APIs.

**Trade-offs and what can go wrong**
- GraphQL N+1 resolver problems (use DataLoader/batch mapping) and expensive arbitrary queries.
- gRPC needs HTTP/2-aware load balancing and isn't browser-native (gRPC-Web).
- Too many styles burden the platform team; standardise per consumer type.

**How I'd monitor it**
Per style: REST status/latency, GraphQL resolver timing and query cost, gRPC status codes, SSE concurrent streams and time to first token.

**Follow-ups to expect**
- *GraphQL for partners?* -> Possible, but cost control, caching and versioning are harder at partner scale.
- *gRPC streaming vs Kafka?* -> gRPC for live request-scoped streams; Kafka for durable, replayable events.
- *Can MCP replace REST for AI?* -> MCP exposes tools to AI agents; it typically wraps existing REST APIs, not replaces them.

**60-second answer**
"I choose per consumer. Partners get REST with OpenAPI: universal, cacheable and easy to version. Web and mobile get a BFF, GraphQL when screens need varied data in one round trip, with complexity limits and DataLoader. High-volume internal calls like pricing use gRPC; other internal calls stay REST. The AI assistant streams over SSE, and events go through Kafka. For AI agents, MCP servers wrap these existing APIs as tools rather than replacing them."
