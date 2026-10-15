---
id: foundations-rest-api
title: REST APIs & third-party integration: from the basics (drafted)
stack: java
skill: rest-api
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What makes an API RESTful?
tags: rest, http, api-design, statelessness, status-codes, hypermedia, basics

**Start here: the concepts**
- **API**: a set of rules that lets one program ask another program to do something or return data over a network.
- **REST**: a style for designing web APIs on top of HTTP. It is a set of design rules, not a product or a library. It exists so many different clients can use a service in a predictable way.
- **Resource**: a "thing" the API exposes, such as an order or a customer. Each has its own address, a **URL**, like `/orders/42`.
- **HTTP verbs (methods)**: the standard actions. GET reads, POST creates or triggers, PUT replaces, PATCH changes part of a resource, DELETE removes. Everyone already knows what they mean, so clients need no special instructions.
- **Representation**: the form in which a resource travels over the wire, usually JSON. The server's database row is not the resource itself, only its JSON description.
- **Stateless**: every request carries everything the server needs (who you are, what you want). The server keeps no memory of you between requests. This is why any server can handle any request.
- **Status code**: a number in the response that says what happened: 200 OK, 201 Created, 404 Not Found, 500 Server Error.
- **Cacheable**: a response can be marked as reusable, so a browser or CDN can serve it again without bothering the server.
- **Hypermedia (HATEOAS)**: responses include links to what you can do next, such as a "cancel" link inside an order.

**The live scenario**
A team built `POST /getOrder`, `POST /deleteOrderById` and so on. Errors came back as `200 OK` with `{"error": "not found"}` in the body. The dashboard showed 100% success while about 4% of calls actually failed. A CDN could not cache anything, because every call was a POST. Scaling from 2 to 6 servers broke logins, because the server remembered sessions in memory. After redesigning to `GET /orders/42`, honest status codes and stateless tokens, failures became visible and any server could take any request.

**What the interviewer is really checking**
Whether you know REST is a set of constraints with reasons behind them, not just "JSON over HTTP", and whether you can name the practical rules and what each one buys you.

**How I answer it**
1. **Model things as resources with noun URLs**: `/orders/42`, not `/getOrder`. The URL names the thing, so it stays stable and easy to guess.
2. **Let HTTP verbs be the actions**: GET reads, POST creates, PUT/PATCH update, DELETE removes. Tools, proxies and developers already understand these. GET must not change data, and PUT and DELETE are safe to repeat.
3. **Keep requests stateless**: send a token with every call. Then any server can answer, so you scale by adding servers.
4. **Return representations, usually JSON**: the client asks for a format and the server sends a description of the resource.
5. **Use correct status codes**: 2xx success, 4xx the client's mistake, 5xx the server's fault. Clients and monitoring tools rely on them.
6. **Allow caching**: mark safe GET responses cacheable, which reduces load and latency.
7. **Add hypermedia ideally**: links in responses let clients discover actions. Strictly, hypermedia is part of REST's uniform interface, but most real APIs skip it. That is why people call them "REST-like".

```
GET /orders/42      -> 200 OK
POST /orders        -> 201 Created, Location: /orders/43
DELETE /orders/42   -> 204 No Content
```

**Trade-offs and what can go wrong**
- Verbs in URLs (`/createOrder`) or always returning 200 are the most common mistakes.
- Statelessness makes each request slightly larger, because the token travels every time.
- Caching can serve stale data if you set it carelessly.
- Not every action fits a noun, such as "cancel order". Use a sub-resource like `POST /orders/42/cancellation`.
- Full hypermedia adds effort that many teams skip.

**How I'd monitor it**
- Track 2xx, 4xx and 5xx rates per endpoint. Honest codes make these numbers meaningful.
- Watch p95 latency and cache hit ratio.
- In Splunk, search by status code and correlation id to follow one failing request.
- Check that no server affinity ("sticky sessions") is needed, which would show hidden state.

**Follow-ups to expect**
- *PUT vs PATCH vs POST?* -> POST creates or triggers an action. PUT replaces the whole resource and is safe to repeat. PATCH changes only some fields.
- *Is returning 200 with an error body acceptable?* -> No. Clients, caches and monitoring read the status code, so use 4xx or 5xx, ideally with an RFC 9457 problem details body.
- *Does stateless mean no database?* -> No. The server keeps no per-client session memory between requests. Data still lives in a database.

**60-second answer**
REST is a way of designing web APIs on HTTP. You model things as resources with noun URLs, like `/orders/42`, and use the standard verbs for actions: GET to read, POST to create, PUT or PATCH to update, DELETE to remove. Each request is stateless, so it carries everything the server needs and any server can answer it. Data travels as representations, usually JSON, with correct status codes such as 201 for created and 404 for not found. GET responses can be cached to reduce load. Ideally responses also include hypermedia links, though many APIs skip that. These rules make an API predictable, scalable and easy to monitor.

### Q2 [fresher] GET vs POST vs PUT vs PATCH vs DELETE - which are safe and idempotent?
tags: rest, http-methods, idempotency, safe-methods, api-design, retries, basics

**Start here: the concepts**
- **HTTP method:** the verb in a request (GET, POST, PUT, PATCH, DELETE). It tells the server what kind of action the client wants. Proxies, caches, browsers and retry libraries all rely on these meanings.
- **Resource:** a thing the API exposes, such as an order at `/orders/42`.
- **Safe method:** one that is meant only to read and must not change anything on the server. GET, HEAD and OPTIONS are safe. Safe methods can be called freely by caches, crawlers and prefetchers.
- **Idempotent method:** one where calling it once or ten times leaves the server in the same final state. It is about the effect on the server, not about getting the same response each time. Every safe method is idempotent, but not every idempotent method is safe.
- **Why this exists:** networks fail. If a request times out, the client cannot know if the server processed it. Idempotency tells the client whether it is safe to simply try again.

**The live scenario**
A mobile checkout app sends `POST /payments` over weak 4G. About 1% of the 10,000 daily payments time out at 10 seconds. The app retries automatically. In many of those cases the first request had already succeeded, so about 60 customers a week are charged twice. Support tickets pile up. The cause is that POST is not idempotent, and nothing told the server that the retry was the same payment.

**What the interviewer is really checking**
Do you know the difference between "safe" and "idempotent", and can you connect it to a real decision, namely which requests a client may retry without causing duplicates?

**How I answer it**
1. **GET (and HEAD, OPTIONS) is safe and idempotent.** It only reads. HEAD is GET without the body, and OPTIONS asks what is allowed. Because they change nothing, caches and retry code can repeat them freely.
2. **PUT is idempotent but not safe.** It replaces the whole resource with what you send. Sending the same body five times gives the same final state as sending it once.
3. **DELETE is idempotent but not safe.** After the first call the resource is gone, and later calls leave it gone. The response may differ (200/204 first, then 404), but the server state is the same. That is still idempotent.
4. **POST is neither safe nor idempotent.** It usually means "create something" or "do an action", so repeating it can create duplicates. Retrying it needs extra protection (step 6).
5. **PATCH is not guaranteed idempotent.** It changes only part of a resource. "Set status to SHIPPED" is idempotent, but "add 10 to the balance" is not. The result depends on how the patch is written.
6. **To retry POST safely, use an idempotency key.** The client generates a unique ID per logical operation and sends it each time. The server stores the key with the result and returns the stored result instead of repeating the work:
```
POST /payments
Idempotency-Key: 7f3c-...-91ab
```
7. **Remember the PUT vs PATCH difference:** PUT sends the complete new version, PATCH sends only the changes.

**Trade-offs and what can go wrong**
- The method names are only a contract. A GET that deletes data is a real bug. Link prefetchers or crawlers can trigger it, and caches can serve stale results.
- "Idempotent" does not mean "no side effects at all". Logging or audit entries may still be written.
- A PUT that omits fields can wipe them, because PUT means full replacement.
- Idempotency keys need storage, an expiry time, and a check that the same key is not reused with a different body.
- A timeout means the outcome is unknown, not that the call failed.

**How I'd monitor it**
- Track timeouts, retries and 5xx rates per endpoint and method.
- In Splunk, search for the same `Idempotency-Key` appearing more than once. Count how many are replayed (served from the stored result) versus processed twice.
- Alert on duplicate business records, such as two payments with the same order ID.
- Scan access logs for GET requests that change data, and review them in code review.

**Follow-ups to expect**
- *DELETE returns 404 on the second call. Is it still idempotent?* -> Yes. Idempotency is about server state, which is the same either way. The status code may differ.
- *Can PATCH be idempotent?* -> Yes, if it sets absolute values (`status=SHIPPED`). No, if it applies relative changes (`balance += 10`).
- *Why not just never retry POST?* -> Then transient failures would reach users. With an idempotency key, retries become safe.

**60-second answer**
Safe means the method only reads and changes nothing: GET, HEAD and OPTIONS. Idempotent means repeating the call leaves the server in the same state: GET, HEAD, PUT and DELETE, plus OPTIONS. PUT and DELETE are idempotent but not safe, because they change data. POST is neither safe nor idempotent, since repeating it can create duplicates. PATCH is not guaranteed idempotent; it depends on whether it sets a value or adds to one. PUT replaces the whole resource, while PATCH changes only part of it. In practice this tells me what a client can retry after a timeout. For POST I would add an idempotency key so a retry does not charge a customer twice.

### Q3 [fresher] Which status codes do you use and when?
tags: rest, http-status-codes, api-design, error-contract, problem-details, idempotency, basics

**Start here: the concepts**
- **HTTP status code:** a 3-digit number in every response that tells the caller the outcome in a machine-readable way. Client code, load balancers, retry logic and dashboards all read it before they read the body.
- **The five families:** 2xx means success, 3xx means redirect, 4xx means the caller made a mistake, 5xx means the server failed. The 4xx/5xx split matters because a caller should fix a 4xx request but may retry a 5xx.
- **Authentication vs authorization:** authentication asks "who are you?" and authorization asks "are you allowed to do this?". 401 and 403 map to these. 401 is named "Unauthorized" but really means "not authenticated".
- **Idempotent:** doing the same request twice has the same effect as doing it once. Status codes help callers decide whether a retry is safe.
- **Gateway/upstream:** when our service calls another system (a payment vendor, say), that system is the upstream, and our service acts as a gateway to it. 502/503/504 describe upstream trouble.
- **Problem details (RFC 9457):** a standard JSON error body (`type`, `title`, `status`, `detail`) that accompanies the status code. Spring supports it through `ProblemDetail`.

**The live scenario**
A payments API handled 2,000 requests/min. A vendor outage made our service return `200 OK` with `{"error":"vendor down"}`. Monitoring saw 100% success, so no alert fired. Mobile clients treated the 200 as success and showed "Payment done" for about 40 minutes. About 1,200 customers were affected. Returning `502`/`504` would have tripped the error-rate alert within minutes and triggered the app's retry and error handling.

**What the interviewer is really checking**
Whether you treat the status code as a contract that clients, monitors and retry logic rely on, and whether you can tell "client's fault" from "our fault" from "upstream's fault".

**How I answer it**
1. **Success codes.**
   - `200 OK` for a successful read or update that returns a body.
   - `201 Created` after creating a resource, with a `Location` header pointing to the new resource, so the client knows where to fetch it.
   - `202 Accepted` when work is queued and not finished yet. Return a status URL so the client can poll.
   - `204 No Content` when it succeeded and there is nothing to return, such as a DELETE.
2. **Caller mistakes (4xx).** Each code tells the client what to fix.
   - `400` means the request is malformed or has bad input, such as broken JSON or a missing field.
   - `401` means not authenticated: no token or an invalid one.
   - `403` means authenticated but not allowed.
   - `404` means the resource doesn't exist.
   - `409` means conflict with current state, such as a duplicate or a stale version in optimistic locking.
   - `422` means the request is well-formed but breaks business rules, such as an end date before the start date. Some teams use 400 for both. Pick one convention and document it.
   - `429` means too many requests. Add a `Retry-After` header so the client knows when to come back.
3. **Our failures (5xx).**
   - `500` means a bug or unexpected error on our side.
   - `502` means the upstream sent an invalid response.
   - `503` means we're unavailable or overloaded, for example when a circuit breaker is open. Add `Retry-After`.
   - `504` means the upstream timed out.
   - Never pass vendor error codes or messages through. Map them to our own codes.
4. **Never return 200 with an error inside.** Monitors, caches, proxies and client libraries all trust the status line. A hidden error defeats all of them.
5. **Add a body.** Pair every error with a `ProblemDetail`, a stable error code and a correlation id (an ID that links one request across all logs).

```java
return ResponseEntity.created(URI.create("/orders/" + id)).body(order);
```

**Trade-offs and what can go wrong**
- Too many custom codes confuse clients. Stick to the common set.
- Using 500 for everything hides whether the caller or the server is at fault.
- Returning 404 instead of 403 can be deliberate, to avoid revealing that a resource exists. Document the choice.
- Clients may retry a 5xx. For POSTs with side effects that can cause duplicates, so use idempotency keys. A timeout (504) means the outcome is unknown, not that it failed.

**How I'd monitor it**
- Splunk: count by status, e.g. `index=api | stats count by status, endpoint`.
- Alert when the 5xx rate exceeds a threshold, such as 2% over 5 minutes.
- Watch 4xx spikes: 401 may mean a broken token rollout, and 429 may mean a misbehaving client.
- Track 502/504 separately per upstream, and log the correlation id on every error.

**Follow-ups to expect**
- *401 vs 403?* -> 401 means we don't know who you are. 403 means we know you and you're not allowed.
- *400 vs 422?* -> 400 means the request is malformed. 422 means it is well-formed but fails business validation. Be consistent within the API.
- *Should a retry on 504 be safe?* -> Only for idempotent calls or when an idempotency key is sent, because the first attempt may have succeeded.

**60-second answer**
I choose the status code by who is responsible. For success I use 200, 201 with a Location header, 202 for async work, and 204 when there's no body. For caller mistakes I use 400 for bad input, 401 when not authenticated, 403 when not allowed, 404 when missing, 409 for conflicts such as duplicates, 422 for business-rule failures, and 429 with Retry-After when they're too fast. For our own failures I use 500 for bugs, 502 or 504 when an upstream is bad or slow, and 503 when we're unavailable. I never return 200 with an error inside, because monitoring and clients trust the status line. I add a problem-details body with a stable error code and a correlation id, and I alert on the 5xx rate.

### Q4 [mid] How do you make a POST idempotent (e.g. payment/order creation)?
tags: rest, idempotency, post, payments, retries, database, http, basics

**Start here: the concepts**
- **Idempotent:** doing the same operation once or ten times leaves the system in the same state. GET, PUT and DELETE are idempotent by definition in HTTP. POST (create an order, charge a card) is not, so we must add this property ourselves.
- **Retry:** the client sends the same request again because it got no answer. Retries exist because networks drop packets and servers time out.
- **Timeout means unknown:** if the client times out, it cannot tell whether the server never got the request, failed, or succeeded and the reply was lost. A blind retry may charge the customer twice.
- **Idempotency key:** a unique value (usually a UUID) the client generates once per business action and sends in an `Idempotency-Key` header. Every retry of that action reuses the same key. It tells the server "this is the same request, not a new one."
- **Request hash:** a fingerprint (for example SHA-256) of the request body. It lets the server detect a key reused for a different request.
- **Unique constraint:** a database rule that rejects a second row with the same value. It is the safety net that works even when two requests arrive at the same instant.
- **Transaction:** a group of database writes that either all happen or none do.

**The live scenario**
A checkout service handles about 200 orders per minute. A load balancer hiccup makes about 1% of calls time out at 5 seconds. The mobile app retries automatically. Many of the original requests had actually succeeded, so on one bad evening 140 customers were charged twice and support was flooded. The fix was not "stop retrying". It was to make retries safe.

**What the interviewer is really checking**
Whether you understand that a timeout is an unknown outcome, and that safe retries need a server-side record, enforced atomically, rather than a "check if it exists" query that races.

**How I answer it**
1. **The client generates one key per business action and reuses it on every retry.** A new key per attempt would defeat the purpose. The client, not the server, knows which attempts are "the same".
   ```
   POST /orders
   Idempotency-Key: 7c9e6679-7425-40de-944b-e07fc1f90ae7
   ```
2. **The server stores `key -> request hash -> response` in a table with a unique constraint on the key.** Scope it per client or user so two customers can't collide. The constraint makes the database, not application code, decide who wins a race.
3. **Write the key row in the same transaction as the business write.** Either both exist or neither does. Otherwise a crash between them leaves an order with no key (a retry duplicates it) or a key with no order (a retry returns a lie).
4. **On a repeat with the same key and same hash, return the stored response**, with the same status and body. The client sees the original result and nothing is executed again.
5. **On the same key with a different body, return 409 or 422.** This is a client bug. The IETF Idempotency-Key header draft uses 422 for this case. Pick one, document it, and keep it stable.
6. **Handle "still in progress".** If a duplicate arrives while the first request is running, the insert hits the unique constraint. Return 409 (or make it wait briefly) rather than running the work twice.
7. **Expire keys after about 24 hours** with a cleanup job. That window covers realistic retries and keeps the table small.

**Trade-offs and what can go wrong**
- Extra write and storage on every POST, and you need a cleanup job.
- The transaction only covers your own database. If you call an external payment provider, pass your key (or a derived one) to it too, otherwise the provider can still double-charge.
- Don't hash only part of the body, or the "different body" check becomes unreliable.
- Decide whether failed responses (such as 500) are stored. Usually you don't store transient failures, so the client may retry them.
- A key past its expiry is treated as new, so clients must not retry after the window.

**How I'd monitor it**
- Count of idempotent replays (key hits) per hour. A spike signals network or client trouble.
- Count of 409/422 key conflicts. A rise often means a client bug.
- Splunk search on the correlation id and idempotency key to trace all attempts for one order.
- A reconciliation query for duplicate orders per customer, item and minute. It should return zero.
- Idempotency table size and cleanup job success.

**Follow-ups to expect**
- *Why not just check whether the order exists first?* -> Two simultaneous requests both see "not found" and both insert. Only a unique constraint closes that race.
- *Who generates the key?* -> The client, once per user action, so it survives retries. The server cannot know which requests are the same.
- *Which HTTP methods need this?* -> POST, and PATCH when it is not naturally idempotent. PUT and DELETE are already idempotent by definition.

**60-second answer**
A timeout doesn't tell the client whether the request worked, so a blind retry of a POST can create a duplicate payment. I have the client send an Idempotency-Key header, a UUID reused on every retry of the same action. On the server I store the key, a hash of the request and the response in a table with a unique constraint, written in the same transaction as the business change. If the same key comes again with the same body, I return the stored response without redoing the work. If the body differs, I return 409 or 422. If a duplicate arrives while the first is still running, the unique constraint stops it. I expire keys after about 24 hours and pass the key to the payment provider too.

### Q5 [mid] How do you version an API?
tags: api-versioning, rest, backward-compatibility, breaking-changes, deprecation, spring-framework-7, basics

**Start here: the concepts**
- **API version:** A label on a contract (URLs, fields, status codes, error format) that clients depend on. It exists because you can't update every client at the moment you change the server.
- **Breaking change:** A change that makes an existing, correctly written client fail. Examples are removing or renaming a field, changing a field's type, making an optional input required, or changing a status code's meaning.
- **Compatible (additive) change:** A change old clients survive, such as adding an optional response field or a new endpoint. This only works if clients ignore fields they don't know (the "tolerant reader" habit).
- **URL versioning:** The version is in the path, e.g. `/v2/orders`. It's easy to see, test in a browser, log and route.
- **Header / media-type versioning:** The client asks for a version in a header, e.g. `Accept: application/vnd.app.v2+json`. The URL stays the same, but the version is hidden and harder to test and cache.
- **Query-parameter versioning:** e.g. `/orders?version=2`. It's simple but easy to forget, and it clutters URLs.
- **Deprecation and sunset:** Deprecation means "still works, please move off". Sunset is the date it stops working.
- **N-1 support:** You run the current version and the previous one at the same time, so clients get a migration window.

**The live scenario**
A payments team renamed `amount` to `totalAmount` in `GET /orders` and shipped on a Tuesday. About 40 partner integrations ran on that endpoint, and 12 of them broke within the hour. Their checkout pages showed "NaN", and support tickets rose from 5 to 300 a day. The team rolled back and then introduced `/v2/orders` with the new name. `/v1` stayed live for 6 months with a published end date. The real problem wasn't the rename. It was that nobody had a rule for when and how a change is allowed.

**What the interviewer is really checking**
Whether you know versioning is a policy about not breaking clients, not just a place to put "v2". They also want to see that you can name the options with their trade-offs and know how to retire old versions.

**How I answer it**
1. **First, avoid versioning when I can.** I add fields and endpoints in a compatible way and never remove or repurpose anything. Most changes then need no new version, so there is less to maintain.
2. **Only create a new version for a breaking change.** Every version is code you must test, secure and support, so I keep the number small.
3. **Pick one mechanism and use it consistently.** I usually choose URL versioning (`/v2/orders`). It's the most visible and simplest for consumers, easy to route at a gateway, and easy to spot in logs. Header or media-type versioning keeps URLs "pure" but is harder to debug and cache. Query parameters are workable but easy to forget.
4. **Use the framework.** Spring Framework 7 has built-in API versioning, so a controller method can declare which version it serves instead of duplicating path strings by hand:
   ```java
   @GetMapping(path = "/orders", version = "2")
   ```
5. **Publish a deprecation policy.** I announce the sunset date, support N-1, and tell clients through docs, changelog and response headers (`Deprecation`, `Sunset`). Clients can only migrate if they know the deadline.
6. **Retire on evidence.** I watch who still calls the old version, contact them, and only then switch it off.

**Trade-offs and what can go wrong**
- Every live version multiplies testing, security patching and documentation work.
- Copy-pasting whole controllers per version causes drift and bugs. I share the domain logic and keep only the thin mapping layer per version.
- Versioning too eagerly ("v7" in a year) tells clients the API is unstable.
- Silent breaking changes inside a version defeat the whole idea.
- URL versioning changes the resource's address, which purists dislike, but in practice the simplicity usually wins.
- Never sunset without a measured traffic check.

**How I'd monitor it**
- Request count per version, tagged as a metric label and charted per day, so I can see v1 traffic fall.
- Splunk search grouping calls on the old version by client id or API key, to find who still needs outreach.
- An alert if traffic to a deprecated version rises instead of falling.
- Contract tests in CI that fail the build if a field is removed or retyped.
- A 4xx and 5xx spike check right after a release.

**Follow-ups to expect**
- *Which is best: URL, header or query param?* -> No universally best. URL is simplest and most visible. Header keeps URLs stable but is harder to test. What matters is picking one and being consistent.
- *Is adding a field a breaking change?* -> Normally no, if clients ignore unknown fields. It's breaking if a client strictly validates the schema, so state the tolerant-reader rule in your API guidelines.
- *How do you shut down v1 safely?* -> Announce a date, send `Deprecation` and `Sunset` headers, track per-client usage, contact remaining callers, optionally brown-out (short planned outages) before the final removal.

**60-second answer**
"I try not to version at all: I add fields compatibly and only create a new version for a real breaking change, like removing or renaming a field. When I do, I usually use URL versioning, like `/v2/orders`, because it's the simplest and most visible for consumers. Header or media-type versioning also works but is harder to test, and Spring Framework 7 now has built-in support for these styles. The mechanism matters less than the policy: publish a deprecation date, support the current and previous version, and tell clients through docs and headers. I track traffic per version in metrics and Splunk, and I only turn off the old version once usage is gone or the clients have been warned."

### Q6 [mid] How do you design pagination, filtering and sorting?
tags: rest, api-design, pagination, keyset, cursor, sorting, basics

**Start here: the concepts**
- **Pagination**: returning a big list in small pages instead of all at once. Without it, one request can pull millions of rows and exhaust memory, the database and the network.
- **Filtering**: letting the client narrow the list with query parameters, such as `status=PAID`, so it only gets rows it needs.
- **Sorting**: letting the client choose the order, such as `sort=-createdAt`. The leading `-` is a common convention for descending. Paging only makes sense if the order is well defined.
- **Offset/limit**: "skip N rows, then give me M" (`OFFSET 10000 LIMIT 50`). It is simple, but the database still walks past and discards the skipped rows.
- **Cursor (keyset) pagination**: the client sends a bookmark, the cursor, which marks the last row it saw. The server returns the rows after that bookmark. The query jumps straight to that position using an index instead of counting rows.
- **Cursor is opaque**: the server encodes values such as the last `createdAt` and `id`, usually as Base64. Clients treat it as a meaningless token, so the internals can change later.
- **Whitelist**: an explicit list of allowed values. Only fields on the list can be sorted or filtered.

**The live scenario**
An orders API has 20 million rows. The mobile app pages with `?page=4000&size=50`. At that depth the query skips 200,000 rows each time, and p99 latency rises from 40 ms to about 3 s. Meanwhile, new orders keep arriving. A user scrolling to page 2 sees the last item of page 1 again, because everything shifted by one. One day a client also sends `limit=1000000`, and a pod runs out of memory. The team moves to cursor pagination, caps `limit` and whitelists sort fields.

**What the interviewer is really checking**
Whether you know why offset pagination breaks at scale and on changing data, and whether you protect the API and database with limits and whitelists. A mid-level answer should also name the costs of cursors.

**How I answer it**
1. **Define the contract**: `GET /orders?status=PAID&sort=-createdAt&limit=50&cursor=abc`. Filtering, sorting and paging are all query parameters on a collection resource. This is predictable and easy to cache and log.
2. **Prefer cursor (keyset) pagination for large or changing data.** It stays fast on deep pages because the database seeks through an index instead of discarding rows. It is also stable, because the bookmark points at a row, not a position, so inserts don't cause duplicates or skips.
3. **Make the sort total.** Always add a unique tie-breaker such as `id` to the sort. If many rows share a `createdAt`, the cursor would otherwise be ambiguous and you would lose or repeat rows.
   ```sql
   WHERE (created_at, id) < (:lastCreatedAt, :lastId)
   ORDER BY created_at DESC, id DESC LIMIT 51
   ```
   Fetching `limit + 1` rows tells you whether another page exists.
4. **Return `nextCursor`** (absent or null on the last page). Add a total count only if it is cheap, because `COUNT(*)` on a filtered table of millions of rows is expensive.
5. **Cap `limit`** with a default (for example 50) and a hard maximum (for example 100). This stops one client from asking for everything.
6. **Whitelist sortable and filterable fields.** Allow only fields that have a supporting index. This prevents slow full scans and stops internal column names from leaking or being injected into the query.
7. **Reject bad input clearly.** Return 400 with an RFC 9457 problem detail and a stable error code for an unknown sort field, an oversized limit or a tampered cursor. Don't silently ignore them.
8. **Use offset only for small, stable data**, such as an admin screen with a few hundred rows where users need "jump to page 7".

**Trade-offs and what can go wrong**
- Cursors cannot jump to an arbitrary page and make "page 5 of 80" hard to show.
- A cursor is tied to its filter and sort. Changing either means starting over, so validate that they match.
- Every sort and filter combination needs a matching index, or keyset is no faster.
- Sorting on a nullable or non-unique column without a tie-breaker gives wrong pages.
- A huge `OFFSET` or an uncapped `limit` is a denial-of-service risk.
- An exact total count can cost more than the page itself.
- Encoding a cursor is not a security measure. Don't put secrets in it, and sign it if tampering matters.

**How I'd monitor it**
- Latency histograms (p50/p99) per endpoint, split by whether a cursor was present.
- Slow-query logs and the database's `EXPLAIN` output for the paging query, to confirm it uses the index.
- The distribution of requested `limit` values, and the count of 400s for invalid sort or cursor. A spike suggests a client bug or abuse.
- A Splunk search on the endpoint grouped by `limit` and response time, plus an alert on p99 breaches.

**Follow-ups to expect**
- *Why is offset slow?* -> The database must read and throw away all skipped rows, so cost grows with page depth.
- *What if the sort field has duplicates?* -> Add a unique tie-breaker like `id` to the sort and the cursor.
- *How do you handle a total count?* -> Return it only if cheap, or give an approximate count, or just a `hasNext` flag.

**60-second answer**
I expose pagination, filtering and sorting as query parameters, like `status=PAID&sort=-createdAt&limit=50&cursor=abc`. Offset/limit is simple, but on large tables it gets slower with every page because the database discards skipped rows, and results shift when data changes. So for big or fast-changing data I use cursor, or keyset, pagination. The cursor marks the last row seen, the query seeks through an index, and I include a unique tie-breaker like `id` in the sort. I return a `nextCursor` and a total only if it is cheap. I cap `limit`, whitelist the sortable and filterable fields, and return a 400 problem detail for bad input. I watch p99 latency, slow queries and the `limit` distribution.

### Q7 [mid] How do you design the error response?
tags: rest, error-handling, problem-details, rfc-9457, spring-boot, api-design, basics

**Start here: the concepts**
- **Error contract:** the agreed format and meaning of failures, so clients can handle them in code. It exists because clients write `if` statements against your errors, and changing them later breaks those clients.
- **HTTP status code:** the number (400, 404, 500...) that tells any client, proxy or monitor the broad class of outcome. 4xx means the caller's request was wrong. 5xx means our side or a dependency failed.
- **Problem Details (RFC 7807, now replaced by RFC 9457):** a standard JSON shape for errors, sent as `application/problem+json`. Its standard members are:
  - `type`: a URI naming the kind of problem.
  - `title`: a short summary of that kind of problem.
  - `status`: the HTTP status, repeated in the body.
  - `detail`: an explanation of this specific occurrence.
  - `instance`: an identifier for this occurrence.
- **Extension members:** the standard allows extra fields. `code`, `errors[]` and `traceId` are extensions, not part of the standard itself.
- **Stable machine code:** a fixed string like `CARD_DECLINED` that programs match on. Human text may change or be translated, so code must never parse it.
- **Trace/correlation id:** a unique id per request, also written to our logs. It lets support find the exact request from one error.
- **Leaking:** exposing internals such as stack traces, SQL errors or a vendor's raw error. This helps attackers and ties clients to things we may change.

**The live scenario**
A checkout API served about 200 requests per second. Three teams had written three error shapes: `{"error":"..."}`, `{"message":"..."}` and an HTML 500 page. The mobile app showed "Something went wrong" for all of them. About 4% of requests failed, and support got 150 tickets a day that said only "payment failed". Worse, one payment-vendor error passed straight through to the client and revealed the vendor name and an internal hostname. After we standardised on one problem-details shape with a `traceId`, support could find the failing request in seconds, and the app could show "card declined" separately from "try again later".

**What the interviewer is really checking**
Whether you treat errors as a stable public contract (right status, stable codes, safe content) rather than just throwing exception messages at the client.

**How I answer it**
1. **Use one shape everywhere.** Clients then write one error handler. In Spring I use `ProblemDetail` with a single `@RestControllerAdvice`, so no controller invents its own format.
2. **Pick the right HTTP status first.** Examples are 400 or 422 for validation, 401/403 for auth, 404 and 409 for missing or conflicting resources, 429 for rate limits, and 502/503/504 when a dependency fails. Proxies, retries and dashboards rely on the status, so it must be honest.
3. **Add a stable `code` and a `type` URI.** The code is for programs and the text is for humans. We can reword `detail` freely, but we never rename a code without versioning.
4. **Put field problems in `errors[]`.** Return every invalid field in one response, so the user fixes everything in one go instead of one error per attempt.
5. **Always include `traceId`,** the same id we log, so a customer can quote it to support.
6. **Never leak internals or vendor errors.** Log the full detail server-side and translate vendor failures into our own codes, for example `PAYMENT_PROVIDER_UNAVAILABLE` with status 503. A stack trace in a response helps attackers and exposes our design.

```json
{"type":"https://api.example.com/problems/validation","title":"Invalid request","status":422,
 "detail":"2 fields are invalid","instance":"/orders/8841","code":"VALIDATION_FAILED",
 "errors":[{"field":"email","code":"INVALID_FORMAT"}],"traceId":"4bf92f35"}
```

**Trade-offs and what can go wrong**
- Too many fine-grained codes become a maintenance burden. Start small and document them.
- Returning 200 with an error in the body hides failures from monitoring and retries.
- Over-helpful `detail` can leak data, for example saying "email already registered" enables account enumeration.
- Mixing a vendor's status into ours (passing their 500 straight through) confuses clients about whose fault it is.
- Without the same `traceId` in logs, the field is useless.

**How I'd monitor it**
- Dashboards of responses by status and by `code`, to spot a spike in one error type.
- Splunk search on `traceId` to follow one request across services.
- Alerts when 5xx rate or `*_UNAVAILABLE` codes cross a threshold.
- A contract test that fails if any response doesn't match the problem-details shape, and a log scan for stack traces in response bodies.

**Follow-ups to expect**
- *Why not just use the HTTP status?* -> Status is too coarse. Many different failures share 400 or 422, and clients need a specific `code` to react correctly.
- *400 or 422 for validation?* -> Both are used. 400 means malformed input, and 422 means well-formed but semantically invalid. What matters is picking one and applying it consistently.
- *How do you handle a third-party failure?* -> Catch it, log the vendor detail with the `traceId`, and return our own code with 502, 503 or 504, never the vendor's raw message.

**60-second answer**
I design errors as a public contract. I use one shape everywhere, the standard Problem Details format (RFC 9457, which replaced 7807), with `type`, `title`, `status`, `detail` and `instance`. I add extensions: a stable machine `code`, an `errors[]` list for field problems, and a `traceId` that matches our logs. I choose the HTTP status honestly, because proxies and monitoring depend on it. Clients match on the code, not the text. I never return stack traces or raw vendor errors; I log them server-side and translate them into our own codes. In Spring, I do this in one `@RestControllerAdvice` returning `ProblemDetail`.

### Q8 [mid] PUT vs PATCH and optimistic concurrency over HTTP?
tags: rest, http, put-vs-patch, etag, if-match, optimistic-concurrency, basics

**Start here: the concepts**
- **PUT**: the client sends the full new representation and the server replaces the resource with it. Sending the same PUT twice leaves the same end state, so it is idempotent.
- **PATCH**: the client sends only the changes, such as "set phone to X". It is not guaranteed to be idempotent. "Add 1 to the counter" is a valid PATCH, and repeating it changes the result. Common formats are JSON Merge Patch (RFC 7396) and JSON Patch (RFC 6902).
- **Lost update**: two users read the same record, both edit it, and the second save silently overwrites the first.
- **Optimistic concurrency**: instead of locking the record while someone edits, assume conflicts are rare. At save time, check that nobody changed the record since you read it. If someone did, reject the save.
- **ETag**: a response header holding an opaque version label for the resource, such as `ETag: "v7"`. It can be a hash or a version number. The value includes the quotes.
- **If-Match**: a request header that says "only do this write if the current ETag equals this value."
- **412 Precondition Failed**: the standard status when an `If-Match` check fails.
- **Version field**: the same idea inside the JSON body (`"version": 7`), usually backed by a database version column, e.g. JPA `@Version`.

**The live scenario**
A support tool lets agents edit customer profiles. About 40 agents work all day, and two of them open the same customer at 10:02. Agent A changes the address and saves at 10:03. Agent B changes the phone number and saves at 10:04 with a PUT of the whole profile. B's copy still has the old address, so A's change disappears. Three weeks later, 15 customers complain that their address "reverted". No error was logged, because every request returned 200.

**What the interviewer is really checking**
Whether you know PUT and PATCH semantics, and whether you can stop silent overwrites with a standard HTTP mechanism and a clear error contract, rather than by hoping conflicts won't happen.

**How I answer it**
1. **Choose the method.** Use PUT when the client owns the whole representation. Use PATCH for small partial edits. Reason: PUT is simple and idempotent, but it sends stale fields back, which makes lost updates more likely. PATCH sends less data, so fewer fields can be overwritten.
2. **Return a version on every read.** `GET /customers/42` returns `ETag: "7"`. Reason: the client needs proof of which state it saw.
3. **Require the version on every write.** The client sends `If-Match: "7"` with its PUT or PATCH. Reason: this tells the server what the edit was based on.
4. **Compare atomically.** The server must check and update in one step, for example `UPDATE ... SET ..., version = 8 WHERE id = 42 AND version = 7`. If zero rows are updated, there is a conflict. Reason: a separate read-then-write check still has a race window.
5. **Reject stale writes.** Return `412 Precondition Failed` for a header-based check. If you use a body `version` field, 409 Conflict is also common. Pick one and keep it consistent. Return an RFC 9457 problem body with a stable error code and tell the client to re-read.
6. **Force the check.** If `If-Match` is missing, return `428 Precondition Required`. Reason: otherwise clients can skip the protection.
7. **Return the new ETag** on success, so the client can edit again without another GET.

```http
PATCH /customers/42
If-Match: "7"
```

**Trade-offs and what can go wrong**
- The client must handle 412 by re-reading and re-applying the edit, or by asking the user. Many teams forget this part.
- Under heavy contention on the same record, many writes fail and retries multiply. Consider a different design for hot records.
- A PATCH that changes different fields than a concurrent edit might be safe to merge, but a version check will still reject it. That is the safe default.
- Don't blindly retry a 412 with the same version. It will never succeed.
- `If-Match` uses strong comparison, so weak ETags (`W/"..."`) are not suitable for it.
- A hash-based ETag must change whenever any writable part of the resource changes.

**How I'd monitor it**
- Count 412 and 428 responses per endpoint. A rising 412 rate points to contention or a client bug.
- Track the share of write requests that arrive without `If-Match`.
- In Splunk, search for `status=412` grouped by endpoint and correlation id.
- Alert on a sudden spike in conflicts.

**Follow-ups to expect**
- *Is PATCH idempotent?* -> Not by definition. It depends on the patch content. "Set X" is idempotent, "increment X" is not. With `If-Match`, a replayed PATCH fails safely because the version has changed.
- *412 or 409?* -> 412 when a precondition header like `If-Match` fails. 409 fits a general state conflict, such as a version number in the body.
- *Why not pessimistic locks?* -> They hold database locks while a human edits, which blocks other users and leaks locks if the client disappears. Optimistic checks hold nothing between requests.

**60-second answer**
PUT replaces the whole resource and is idempotent. PATCH changes only some fields and is not automatically idempotent. Both can cause lost updates when two users edit the same record. To prevent that, I use optimistic concurrency. Every GET returns an ETag, which is a version label, and the client sends it back in an `If-Match` header on its PUT or PATCH. The server compares the version and updates in one atomic step, for example `WHERE id = ? AND version = ?`. If the version has changed, it returns 412 Precondition Failed (or 409 if the version is in the body) with a problem-details error. It returns 428 if the header is missing. The client then re-reads and retries. I monitor the rate of 412s to spot contention.

### Q9 [mid] How do you handle long-running operations?
tags: rest, async, 202-accepted, polling, webhooks, idempotency, basics

**Start here: the concepts**
- **Long-running operation:** work that takes longer than a client or gateway will wait, usually more than a few seconds. Examples are processing a large file, generating a report, or calling a slow vendor. HTTP requests are meant to be short, and proxies and load balancers often cut connections after 30-60 seconds.
- **`202 Accepted`:** a status code meaning "I received your request and will process it later, but it is not done." It differs from `200 OK` or `201 Created`, which say the work is finished.
- **Job resource:** a record in your database representing the work, with an id, a status (`QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`), progress and a result. The client gets something to ask about later.
- **`Location` header:** an HTTP response header that tells the client where to look. Here it is the job's status URL, e.g. `/jobs/123`.
- **Polling:** the client repeatedly calls `GET /jobs/123` until the status is final. It is simple and works everywhere. The server can add `Retry-After` to say how long to wait between calls.
- **Webhook:** the opposite of polling. The server calls a URL the client registered when the job finishes. Because anyone could fake that call, the sender signs the body with a shared secret (HMAC) and the receiver verifies it.
- **Idempotent:** doing the same operation twice has the same effect as doing it once. This matters because queues redeliver messages and clients retry.
- **Expiry (TTL):** results are deleted after a set time so storage doesn't grow forever.

**The live scenario**
A finance app lets users upload 500 MB CSV files for validation and import. The first version did everything inside one `POST`. At about 90 seconds the gateway timed out and returned 504, but the server kept working. Users retried, so the same file was imported 2-3 times, and roughly 4% of uploads produced duplicates. The team switched to accept-and-poll. The `POST` now answers in under 200 ms, a worker does the import, and duplicates stopped.

**What the interviewer is really checking**
Whether you know not to hold an HTTP connection open for slow work, and whether you design the whole lifecycle: status, completion notification, retries without duplicates, and cleanup.

**How I answer it**
1. **Accept, don't block.** The `POST` validates input, saves a job row as `QUEUED`, puts a message on a queue, and returns `202` with a `Location` header. This keeps the request under every timeout, and the work survives even if the client disconnects.
   ```
   HTTP/1.1 202 Accepted
   Location: /jobs/123
   Retry-After: 5
   ```
2. **Persist the job.** Storing it in a database, not in memory, means a restart or a second server instance can still answer status questions.
3. **Expose status.** `GET /jobs/123` returns state, progress and, when done, a link to the result. A common pattern is `303 See Other` or a `result` link to the finished resource. Return a stable error object for `FAILED` jobs (RFC 9457 problem details), not raw internal errors.
4. **Offer a webhook or event too.** Polling is the default. Webhooks save traffic for clients that can receive calls. Sign them with HMAC and keep polling as a fallback, since webhooks can be lost.
5. **Make the worker idempotent.** Queues deliver at least once, so a message can arrive twice. Use the job id or a client-supplied `Idempotency-Key` on the `POST` so a retry returns the existing job, not a new one. In the worker, use upserts or "already processed" checks.
6. **Expire results.** Delete or archive jobs and files after a retention period (say 7 days) and return `404` or `410 Gone` afterwards.
7. **Handle cancel and failure.** Support `DELETE /jobs/123` where sensible, retry transient errors with backoff, and move poison messages to a dead-letter queue.

**Trade-offs and what can go wrong**
- More moving parts: a queue, workers, a job table and cleanup.
- Clients that poll every second create load. Use `Retry-After` and rate limits.
- Webhook receivers may be down, so retry delivery and allow polling.
- Jobs stuck in `RUNNING` after a worker crash need a heartbeat or lease timeout.
- Without idempotency, redelivery causes duplicates.
- Very short operations don't need this. Use plain synchronous `200`.

**How I'd monitor it**
- Queue depth and age of the oldest message (a growing age means workers are behind).
- Job duration percentiles (p50/p95/p99), success vs. failure rate, and count of jobs stuck in `RUNNING`.
- Dead-letter queue size, with an alert on any growth.
- Webhook delivery failure rate.
- Splunk: search by `jobId` and correlation id to follow one job from `POST` to completion.

**Follow-ups to expect**
- *Polling or webhook?* -> Polling is simpler and robust. Webhooks reduce load but need signature checks and retries. Offer both.
- *What if the client retries the POST?* -> An idempotency key makes the server return the same job instead of creating a second one.
- *What does a failed job return?* -> `GET /jobs/123` still returns `200` with status `FAILED` and an error object with a stable code. The job resource exists, so the lookup itself is not an error.

**60-second answer**
For long-running work I don't hold the HTTP request open. The `POST` saves a job record and queues the work. It returns `202 Accepted` with a `Location` header such as `/jobs/123`. The client polls that URL for status, progress and a result link, or receives a signed webhook when it's done. Because queues can deliver a message twice and clients can retry, I use an idempotency key and an idempotent worker so nothing runs twice. I expire old results, monitor queue age, job duration and stuck jobs, and send failed messages to a dead-letter queue.

### Q10 [mid] How do you handle large file upload/download?
tags: file-upload, presigned-url, multipart-upload, object-storage, range-requests, rest-api, basics

**Start here: the concepts**
- **Object storage (S3, Azure Blob):** a service that stores files as "objects" in buckets and is built to handle huge volumes and many parallel transfers. It exists so your application servers don't have to be file servers.
- **Streaming through the service:** the client sends the file to your app, and your app forwards it to storage. Every byte then uses your app's threads, memory, bandwidth and timeouts.
- **Pre-signed URL:** a temporary link the service creates using its own storage credentials. It allows one specific action (for example, upload this key) for a short time (for example, 15 minutes). The client talks to storage directly and never gets real credentials.
- **Multipart upload:** the file is split into parts that are uploaded separately, in parallel, and then stitched together. If one part fails, only that part is retried. On S3, each part except the last must be at least 5 MiB, and one upload can have up to 10,000 parts. A single PUT is limited to 5 GB.
- **Event notification:** storage tells your system "object X arrived", so your service reacts without polling.
- **Malware scan:** a scanner inspects the file's bytes for known threats before anyone can use the file.
- **`Range` request:** the client asks for only some bytes (`Range: bytes=0-1048575`). The server replies `206 Partial Content`. This allows resuming a broken download and seeking within a video.

**The live scenario**
A document portal accepted 200 MB scans through a Spring Boot API. At month-end, 300 users uploaded at once. Each upload held a request thread for minutes, pods ran out of memory, and the load balancer's 60-second timeout cut off slow connections. About 18% of uploads failed, and users restarted them from zero. The team moved to pre-signed multipart uploads. The API now handles only small JSON calls, and failures dropped to a few percent because only individual parts are retried.

**What the interviewer is really checking**
Whether you see that large files shouldn't pass through your business service, and whether you also cover resumability, validation, security and an honest "upload finished" signal.

**How I answer it**
1. **Client asks the API for permission to upload.** It sends filename, size and content type. The API checks auth and limits, then creates a storage key it chooses itself (never trust the client's filename). *Reason: the API stays in control without carrying the bytes.*
2. **Start a multipart upload and return one pre-signed URL per part.** The client uploads parts in parallel and retries only failed ones. *Reason: speed, and a dropped connection doesn't mean starting over.* Small files can use a single pre-signed PUT.
3. **Client completes the upload** by sending the list of part IDs. Storage assembles the object.
4. **Storage emits an event** (to a queue or topic). A worker picks it up. *Reason: the API doesn't have to trust the client's "I'm done".*
5. **Validate and scan before use.** Check the real size and sniff the actual file type from its bytes, not just the client-sent `Content-Type`. Scan for malware while the file sits in a quarantine location or has a "pending" status. Only then mark it "available". The user sees status `PENDING` and then `READY`, for example via a status URL.
6. **Downloads:** return a short-lived pre-signed GET URL, or serve through a CDN. Storage supports `Range` natively, so download managers and video players can resume or seek.

```
Range: bytes=1048576-2097151   ->   206 Partial Content
```

**Trade-offs and what can go wrong**
- Abandoned multipart uploads keep costing storage. Add a lifecycle rule to abort incomplete uploads after a few days.
- Pre-signed URLs are bearer links: anyone who has one can use it. Keep expiry short, never log full URLs, and scope each to one key and method.
- Size limits on a plain pre-signed PUT are weak. Use a presigned POST policy with a size range, or re-check size after upload and delete violations.
- The client-side flow is more complex (part splitting, retries). Browser CORS settings on the bucket are a common setup mistake.
- Scanning adds delay, so the product must handle a "not ready yet" state.

**How I'd monitor it**
- API: the rate of "create upload" vs "complete upload" calls (a widening gap means abandoned uploads), and p95 latency, which should stay small.
- Storage: incomplete multipart upload count and size, 4xx/5xx rates, and bytes transferred.
- Pipeline: event-to-READY time, scan failures, quarantined file count, and queue lag on the event consumer.
- Logs: search by correlation/upload ID to follow one upload from request to READY. Alert when many uploads stay in PENDING.

**Follow-ups to expect**
- *How do you resume an interrupted upload?* -> Keep the upload ID and list the parts already stored (S3 `ListParts`), then upload only the missing ones.
- *Why not just raise the server's max request size?* -> It ties up threads and memory per slow client and doesn't scale. Timeouts and retries still restart the whole file.
- *How do you stop users from uploading something dangerous?* -> Restrict by size and type up front, but verify after upload by inspecting the file's bytes and scanning for malware. Keep the file unavailable until it is clean.

**60-second answer**
I avoid streaming big files through my service because it ties up threads, memory and timeouts. The client asks my API for permission, and I return pre-signed URLs so it uploads straight to S3 or Blob storage. For large files I use multipart upload, so parts go in parallel and a failure only retries that part. When the upload completes, storage fires an event, and a worker validates the size and real file type and scans for malware before the file is marked ready. For downloads I hand out short-lived pre-signed links and rely on `Range` requests, so downloads can resume and seek. I also add a lifecycle rule to clean up abandoned multipart uploads and monitor the gap between started and completed uploads.

### Q11 [mid] REST vs GraphQL vs gRPC?
tags: rest, graphql, grpc, api-design, protobuf, http2, basics

**Start here: the concepts**
- **API style**: the agreed way one program asks another for data or actions over a network. REST, GraphQL and gRPC are three such styles.
- **REST**: you expose *resources* (e.g. `/orders/42`) and use standard HTTP verbs (GET, POST, PUT, DELETE) and status codes. It exists because it reuses how the web already works, so every tool, browser and proxy understands it.
- **Caching**: storing a response so the next identical request is answered without hitting your server. HTTP caches (browsers, CDNs) do this automatically for GET requests, which is why REST is "cacheable".
- **GraphQL**: one endpoint where the client sends a query naming exactly the fields it wants. It exists to fix *over-fetching* (getting 40 fields when you need 3) and *under-fetching* (needing several calls to assemble one screen).
- **Query cost limit**: GraphQL lets clients write deep, expensive queries, so the server must cap depth or estimated cost to stop one query from overloading it.
- **gRPC**: a framework for calling remote functions. It uses **Protobuf** (a compact binary format, defined in a `.proto` schema file) over **HTTP/2** (a faster version of HTTP that multiplexes many calls on one connection).
- **Strongly typed**: the schema generates client and server code, so a wrong field type fails at compile time, not in production.
- **Streaming**: sending a continuous flow of messages in one call, not a single request and response.
- **BFF (Backend For Frontend)**: a small service built for one client (e.g. the mobile app) that gathers data from many backends.

**The live scenario**
A retail app's mobile home screen made 6 REST calls (user, orders, offers, and so on) and used about 10% of each payload. On a slow 4G network, load time was 4 seconds. The team put a GraphQL BFF in front, and the screen needed 1 call of about 15 KB. Meanwhile, the 12 internal services behind it talked REST/JSON at 8,000 calls per second, and serialization CPU was noticeable. Moving the hottest internal path to gRPC cut its latency and payload size. Public partners still used plain REST with documented endpoints.

**What the interviewer is really checking**
Whether you pick by *who the caller is and what the pain is*, not by fashion, and whether you know each style's weak spot (GraphQL caching and cost, gRPC browser support and debuggability).

**How I answer it**
1. **Start with the caller.** Public or partner callers need something universal and easy to debug, so REST. Its verbs, status codes and caching work everywhere, and anyone can try it with curl.
2. **Choose GraphQL when the client's data shape varies.** Many screens, each needing different fields from many backends, is where it pays off. The client asks for exactly what it needs, which removes over- and under-fetching. Put it as a BFF over the backends.
3. **Choose gRPC for internal service-to-service calls.** Binary Protobuf is smaller and faster than JSON, HTTP/2 reuses connections, the schema gives generated typed clients, and streaming is built in. You control both ends, so the tooling cost is acceptable.
4. **State the typical mix**: REST public, gRPC internal, GraphQL BFF over many backends.
5. **Apply the same safety rules to all three.** Set timeouts (gRPC calls: a deadline), bounded retries only for idempotent calls, and a stable error contract. In REST that means RFC 9457 problem details with a correlation id.

**Trade-offs and what can go wrong**
- **REST**: fixed response shapes cause over-fetching and many round trips.
- **GraphQL**: usually sends everything as POST to one URL, so HTTP/CDN caching doesn't work by default. It often returns HTTP 200 even when part of the query failed, which hides errors from monitoring. Deep queries need cost or depth limits. Resolvers can trigger the "N+1" problem (one query per list item).
- **gRPC**: browsers can't call it directly (they need gRPC-Web or a gateway). Binary payloads are harder to inspect. A schema change needs care (never reuse field numbers).
- **Common mistake**: adopting all three everywhere, which multiplies tooling and on-call burden.

**How I'd monitor it**
- Per-endpoint or per-operation latency (p95/p99), error rate and request rate.
- For GraphQL, log the *operation name* and track errors inside 200 responses, query depth and cost rejections.
- For gRPC, track status codes (e.g. `DEADLINE_EXCEEDED`, `UNAVAILABLE`) and payload sizes.
- In Splunk, search by correlation id across all three styles to follow one request end to end.
- Alert on cache hit ratio for REST and on slow-resolver spikes for GraphQL.

**Follow-ups to expect**
- *Why is GraphQL harder to cache?* -> Requests are mostly POSTs to one URL with varying bodies, so HTTP caches can't key on the URL. You need persisted queries or caching at the resolver level.
- *Why is gRPC faster than REST/JSON?* -> Protobuf is compact binary and cheap to parse, and HTTP/2 multiplexes many calls over one connection.
- *Can you use gRPC for a public API?* -> Possible, but browser support needs gRPC-Web or a gateway, so most teams keep public APIs on REST.

**60-second answer**
"I choose by who is calling. For public and partner APIs I use REST: it is simple, universal, and GET responses cache well over plain HTTP. For internal service-to-service calls I prefer gRPC, which sends compact binary Protobuf over HTTP/2, gives typed generated clients and supports streaming. GraphQL fits when many screens need different fields from many backends, because the client picks its fields and avoids over- and under-fetching. I would usually place it as a BFF, with query cost limits, and accept that HTTP caching is harder. So the typical mix is REST public, gRPC internal, GraphQL BFF. Whatever the style, I set timeouts, retry only safe calls, and keep a stable error contract with a correlation id."

### Q12 [mid] How do you secure a REST API?
tags: rest-api, security, oauth2, jwt, authorization, rate-limiting, basics

**Start here: the concepts**
- **TLS (HTTPS):** encrypts traffic between client and server so nobody on the network can read or change it. Without it, tokens and data travel as plain text.
- **Authentication vs authorization:** authentication asks "who are you?". Authorization asks "what may you do?". A missing or invalid login gives 401. A valid login without permission gives 403.
- **OAuth2:** a standard where a client gets a short-lived access token from an authorization server instead of handling the user's password. It is about delegated authorization. OpenID Connect adds the "who" part.
- **JWT:** a signed token carrying claims (user id, issuer, audience, expiry, scopes). The API checks the signature without calling anyone.
- **Scope / least privilege:** a scope is a named permission such as `orders:read`. Least privilege means each token gets only what it needs, so a leak does limited damage.
- **IDOR (object-level authorization):** the caller is logged in but asks for someone else's object by changing an id in the URL. The server must check that this caller owns this object.
- **Input validation:** treat all incoming data as untrusted, and check type, length, format and allowed values.
- **Rate limiting / request size limits:** caps on how many requests, and how large, a caller may send. They stop abuse, scraping and overload.
- **CORS:** a browser rule that decides which websites' JavaScript may call your API. An allow-list names the permitted origins.
- **API gateway / WAF:** a gateway is a single front door for routing, authentication and limits. A WAF (web application firewall) blocks known attack patterns.
- **Audit log:** a record of who did what, and when.

**The live scenario**
An orders API serves about 200k requests a day. A customer changed `/orders/1041` to `/orders/1042` and saw a stranger's order. A script then walked ids for an hour and pulled roughly 3,000 orders. TLS was on and every token was valid, with correct scopes. The service only checked "is the token valid?", never "does this order belong to this user?". The fix was an ownership check, a rate limit and an alert.

**What the interviewer is really checking**
Whether you see security as layers and know that a valid token is not enough. The most common real breach is broken object-level authorization, not weak encryption.

**How I answer it**
1. **TLS everywhere**, including internal service-to-service calls. Otherwise tokens and data can be sniffed or altered.
2. **Authenticate with OAuth2 access tokens (JWT).** Validate the signature, issuer, audience and expiry on every request. A signed token that is not checked for audience can be replayed against the wrong API.
3. **Least-privilege scopes.** Each client gets only the scopes it needs, so a stolen token has limited reach.
4. **Check object-level authorization in the service**, using the user id from the token, not from the request:
   ```java
   orderRepo.findByIdAndOwnerId(id, jwt.getSubject()) // empty -> 404
   ```
5. **Choose 404 or 403 deliberately.** For resources the caller must not know exist, return 404 so you don't confirm the id is real. Use 403 when knowing it exists is harmless.
6. **Validate input** and set **request size limits**, so malformed or huge payloads are rejected before they reach logic or memory.
7. **Rate limit** per client or token to slow brute force and id-walking.
8. **CORS allow-list** with specific origins, never `*` with credentials.
9. **No secrets in URLs.** URLs end up in logs, browser history and proxies. Put tokens in the `Authorization` header.
10. **Audit logs** for sensitive actions, with a correlation id and the user id, but never tokens or passwords.
11. **Gateway/WAF in front** for central authentication, limits and attack filtering. It is an extra layer, not a replacement for steps 2–4.

**Trade-offs and what can go wrong**
- Gateway-only security fails once a service is reached some other way. Each service must still check authorization.
- CORS is enforced by browsers only. It does not stop curl or scripts, so it is not authentication.
- Long-lived JWTs can't be revoked easily. Use short expiry plus refresh tokens.
- 404-for-403 hides data but makes debugging harder. Log the real reason internally.
- Error bodies that leak stack traces or vendor messages help attackers. Return RFC 9457 problem details with stable codes.
- Over-tight rate limits block legitimate bursts.

**How I'd monitor it**
- Splunk searches and alerts on spikes in 401/403/404 per client or IP, and on sequential id access by one user.
- Rate-limit rejection counts (429s), and the gateway or WAF block rate.
- Token validation failures by reason (expired, bad audience).
- Audit-log review for sensitive actions.
- Dependency and secret scanning in CI, and regular penetration tests.

**Follow-ups to expect**
- *Why isn't a valid JWT enough?* -> It proves identity and scopes, not ownership of a specific object. The service must still check it.
- *401 vs 403?* -> 401 means not authenticated (missing or invalid token). 403 means authenticated but not allowed.
- *Where do you store tokens in a browser app?* -> Prefer short-lived tokens, and an HttpOnly, Secure cookie or a backend-for-frontend pattern, to reduce XSS theft.

**60-second answer**
I secure an API in layers. First TLS everywhere, then OAuth2 access tokens, usually JWTs, where I validate signature, issuer, audience and expiry on every call. Scopes are least-privilege, so each client gets only what it needs. The key step is object-level authorization: I check in the service that the caller owns the resource, which prevents IDOR, and I return 404 instead of 403 when the caller shouldn't know it exists. On top of that come input validation, request size limits, rate limiting, a CORS allow-list (which only protects browsers), no secrets in URLs, and audit logs. A gateway and WAF add a front layer, but each service still enforces its own rules. I monitor 401/403/404 spikes, 429s and sequential id access in Splunk.

### Q13 [mid] What is HATEOAS and do you use it?
tags: rest, hateoas, hypermedia, api-design, richardson-maturity-model, spring-hateoas, basics

**Start here: the concepts**
- **REST**: an architectural style for web APIs. Resources (orders, users) have URLs, and you act on them with HTTP methods (GET, POST, PUT, DELETE).
- **Hypermedia**: a response that carries links, not just data. A web page works this way: you don't memorise URLs, you click the links on the page.
- **HATEOAS** ("Hypermedia As The Engine Of Application State"): the API response tells the client which actions are possible *right now*, as links. The client follows those links instead of building URLs from hard-coded rules.
- **Richardson Maturity Model**: a 0-3 scale for how "RESTful" an API is. Level 0 is one endpoint, level 1 is resources, level 2 is proper HTTP verbs and status codes, and level 3 is hypermedia (HATEOAS). That is why HATEOAS is called "full REST".
- **Link formats**: HAL is a common JSON convention, with `_links` in the body. The HTTP `Link` header (RFC 8288) is another option. In Spring, the Spring HATEOAS library builds these.

**The live scenario**
An order API serves a web app and a mobile app with about 200k installed users. Each client hard-codes the rule "show Cancel if status is PENDING or PAID" and builds `/orders/{id}/cancel` itself. The business then adds a rule: paid orders already handed to the courier can't be cancelled. The web app is fixed in a day. Old mobile versions stay in the wild for weeks and keep showing Cancel. In our illustrative numbers, about 3% of cancel calls return 409 and support tickets spike. With hypermedia, the server would return a `cancel` link only when cancelling is allowed. The business rule would live in one place, and old clients would simply stop showing the button.

**What the interviewer is really checking**
Whether you know the idea and where it sits on the maturity model, and whether you give an honest, pragmatic view of when it pays off. They don't want buzzwords or dogma.

**How I answer it**
1. **Define it simply.** Responses include links to the next possible actions, so the client discovers what it can do instead of hard-coding it. This is level 3 of the Richardson model, "full REST".
2. **Show a tiny example**, because it makes the idea concrete:
```json
{"id":42,"status":"PAID","_links":{"self":{"href":"/orders/42"},"cancel":{"href":"/orders/42/cancel"}}}
```
If the order can't be cancelled, the `cancel` link is absent. The client shows the button only if the link exists.
3. **Say what it buys you.** Business rules about "what is allowed now" stay on the server, and URLs can change without breaking clients that follow links.
4. **Say what it costs.** Responses get bigger, and the server needs code to decide which links to emit. Most clients (a mobile app, a front-end team next door) already know the workflow, so they ignore the links.
5. **Give the honest position.** In practice few teams use it. Clear documentation (OpenAPI) and stable URLs matter more. I know it, and I use it only where clients really are generic: public or partner APIs with many unknown consumers, or workflow-heavy APIs where allowed actions change by state.
6. **Mention the cheap middle ground.** Even without full HATEOAS, I return `self` and pagination links (`next`, `prev`). I may also return an `allowedActions` field. These give most of the benefit with little effort.

**Trade-offs and what can go wrong**
- Teams add `_links` but clients still build URLs by hand, so you pay the cost and get no benefit.
- There is no single universal standard (HAL, JSON:API, Siren and others), so tooling and client support vary.
- Links hide authorisation and state rules in server code. Those rules must still be enforced on the endpoint itself: a missing link is a hint, not security.
- Link generation can be a hidden performance cost if it triggers extra permission or database checks per item in a list.

**How I'd monitor it**
- Rate of 405/409/422 on action endpoints (for example cancel) by client version. A spike means clients and server rules have drifted apart. In Splunk, search by status, endpoint and client-version header.
- Response size and p95 latency before and after adding links.
- Whether clients actually follow links, by comparing hits on `/cancel` from clients that used the link with hits from clients that built the URL.

**Follow-ups to expect**
- *Is HATEOAS required for a REST API?* -> By Roy Fielding's definition, yes. Most real APIs stop at level 2 and are still called REST. The choice is a pragmatic trade-off.
- *Does a missing link mean the action is forbidden?* -> No. The server must still check permissions and state on the endpoint. Links only guide the UI.
- *How would you do it in Spring?* -> Use Spring HATEOAS: model classes carry links (for example `EntityModel`), and HAL is the usual format.

**60-second answer**
HATEOAS means the API response includes links to the actions you can take next, like clicking links on a web page. The client follows the links instead of hard-coding URLs and business rules. It is level 3 of the Richardson maturity model, often called "full REST". Its benefit is that rules such as "can this order be cancelled?" live on the server, so changes don't break old clients. The cost is bigger payloads, extra server logic, and little real use, because most clients already know the workflow. So in practice I rely on clear OpenAPI documentation and stable URLs. I always include self and pagination links. I use full HATEOAS only where clients really are generic, such as public APIs with many unknown consumers.

### Q14 [senior] How do you document and test the contract?
tags: rest, openapi, contract-testing, pact, breaking-changes, basics

**Start here: the concepts**
- **API contract:** the written promise between the team that offers an API (provider) and the teams that call it (consumers). It covers URLs, fields, types, status codes and error shapes. It exists so both sides can work without reading each other's code.
- **OpenAPI spec:** a machine-readable YAML/JSON file describing that contract. Tools turn it into docs, client code, mocks and automated checks.
- **Design-first vs generated:** design-first means you write and agree the spec before coding. Generated means a library such as springdoc reads your Spring controllers and produces the spec. Design-first is better for agreement; generated is cheaper but only describes what the code already does.
- **API portal:** a shared website where specs are published so consumers can find and read them.
- **Consumer-driven contract test:** each consumer records exactly what it sends and what it needs back. The provider's build replays those expectations, and fails if it can no longer satisfy them. Pact and Spring Cloud Contract are the common tools.
- **Breaking change:** a change that makes an existing caller fail, such as removing a field, renaming it, or making an optional field required. openapi-diff compares two spec versions and flags these in CI (the automated build).
- **Mock server:** a fake API generated from the spec that returns sample responses, so consumers can build before the real service exists.

**The live scenario**
A payments team renamed `customerRef` to `customerId` in a response. Their own tests passed, and so did the generated docs, since the docs followed the code. Three consumer services, including a mobile backend doing about 400 requests/s, started failing at deploy. Rollback took 25 minutes. After this, the team added a spec diff check and consumer contract tests to the pipeline. The same rename was then blocked in the pull request.

**What the interviewer is really checking**
Whether you see the contract as something verified automatically on every build, not just documentation. A senior should also cover both sides: APIs you own, and third-party APIs you don't control.

**How I answer it**
1. **Make the spec the source of truth.** I prefer design-first: consumers and provider review the OpenAPI file before coding. Where we generate it with springdoc, I treat the output as a reviewed artefact, because generated specs record accidents as well as intent.
2. **Put the error contract in the spec.** Document the failure responses too: status codes, RFC 9457 problem-detail body, stable error codes and the correlation id. Callers write error handling against these.
3. **Publish it** to a portal, with versions and a changelog, so consumers do not depend on emails or tribal knowledge.
4. **Run a breaking-change check in CI.** Compare the new spec with the last released one using openapi-diff. A removed field or tightened rule fails the build unless the team deliberately versions the API. It is cheap and catches the obvious breaks.
5. **Add consumer-driven contract tests.** The spec check only knows what the API offers. Contract tests know what consumers actually use, so a provider can remove a field nobody reads without a fight, and cannot remove one someone depends on. Consumers publish contracts (to a Pact Broker, for example) and the provider verifies them on every build.
6. **Use mock servers for parallel work.** Frontend and consumer teams build against a mock generated from the agreed spec, and swap in the real service later.
7. **Third-party APIs.** I can't make a vendor run my contract tests. So I write consumer-side tests against recorded or stubbed vendor responses, run a small scheduled check against the vendor's sandbox to detect drift, and map vendor errors into my own error contract so vendor details never leak.

**Trade-offs and what can go wrong**
- Contract tests need upkeep. Stale contracts block provider releases, so each contract needs an owning team.
- Contract tests cover shape, not business behaviour. They do not replace integration tests.
- Over-strict contracts, such as matching exact values instead of types, make tests brittle.
- Generated specs can silently drift from intent. Mocks can drift from the real service, which is why provider verification is still needed.
- A diff tool cannot detect meaning changes, such as the same field now holding a different unit.

**How I'd monitor it**
- CI metrics: breaking-change check failures per month, and contract-verification pass rate per provider.
- The Pact Broker's "can-i-deploy" check as a deploy gate.
- In production, Splunk searches for 4xx/5xx spikes by endpoint and consumer after each release, and for unknown-field or deserialization errors.
- For vendors, an alert when the scheduled sandbox check fails.

**Follow-ups to expect**
- *Why not just integration tests?* -> They are slow, need every service running, and fail for unrelated reasons. Contract tests are fast and isolated, and they point to the exact broken expectation.
- *How do you evolve an API without breaking callers?* -> Make additive changes only, such as new optional fields. Deprecate before removal, and version when a break is unavoidable.
- *Who owns the contract in consumer-driven testing?* -> Consumers state their needs, but the provider team owns verification and decides how to evolve the API.

**60-second answer**
I treat the contract as something the build verifies, not just a document. I write the OpenAPI spec design-first, or review the springdoc-generated one, and include the error format in it. I publish it to a portal. In CI, openapi-diff blocks breaking changes such as removed fields. On top of that I use consumer-driven contract tests with Pact or Spring Cloud Contract, so the provider's build fails if it breaks something a real consumer uses. Teams build in parallel against mock servers generated from the spec. For third-party APIs I test my side against recorded responses, check their sandbox on a schedule, and wrap vendor errors in my own error contract.

### Q15 [senior] How do you make API calls to other services resilient?
tags: rest-api, resilience, timeouts, retry, circuit-breaker, bulkhead, basics

**Start here: the concepts**
- **Timeout**: the longest we wait before giving up. Without one, a thread can wait forever on a stuck service. There are three kinds: *connect* (opening the connection), *read* (waiting for the response bytes), and *pool-acquire* (waiting for a free connection from our own pool).
- **Retry**: trying a failed call again, because many failures (a network blip, a restarting server) are short-lived.
- **Idempotent**: doing it twice has the same effect as doing it once. GET and PUT usually are. A plain POST "create payment" is not, so a retry could charge twice. A POST becomes safe to retry if it carries an **idempotency key** the server uses to spot duplicates.
- **Exponential backoff**: wait longer after each failure (200ms, 400ms, 800ms), so we don't pound a struggling server. **Jitter** adds randomness so thousands of clients don't all retry at the same instant. A **cap** limits the number of attempts and the maximum wait.
- **Circuit breaker**: like a fuse. After too many failures it "opens" and fails calls immediately without contacting the dependency. After a pause it lets a few trial calls through and closes again if they succeed.
- **Bulkhead**: separate compartments in a ship. We give each dependency its own limited thread or connection pool, so one slow service can't use up everything.
- **Fallback**: a degraded but acceptable answer (cached data, a default) when the call fails.
- **Deadline propagation**: passing "the caller gives up at time T" downstream, so services stop work nobody is waiting for.

**The live scenario**
A checkout service calls a shipping-rates vendor at about 300 requests/second. The vendor degrades and responses go from 100ms to 30s. There are no timeouts, so all 200 request threads block within seconds. Checkout, which doesn't even need live rates to take an order, stops responding, and the outage lasts 25 minutes. A naive "retry 3 times" fix would have tripled the load on the already struggling vendor.

**What the interviewer is really checking**
Whether you treat every remote call as a failure point and know that these tools work *together*. They also want to see that you know retries can make an outage worse.

**How I answer it**
1. **Set timeouts on every call**: connect, read, and pool-acquire. A slow dependency would otherwise consume our threads, so the timeout caps how much we lose per call.
2. **Retry only when it is safe and useful.** Retry idempotent calls (or POSTs with an idempotency key) on transient errors: timeouts, connection failures, 503, 429 (respecting `Retry-After`). Don't retry other 4xx, because the same bad request fails again. Use exponential backoff with jitter and a cap, so retries don't create a synchronized flood. A timeout means the outcome is *unknown*, not failed, which is why idempotency matters.
3. **Add a circuit breaker.** If the failure or slow-call rate crosses a threshold, fail fast. This protects the vendor from our traffic and our threads from waiting.
4. **Add a bulkhead.** Give each dependency a bounded pool or concurrency limit, so shipping rates can use at most, say, 20 threads and the rest of checkout keeps working.
5. **Define a fallback** where the business accepts it, such as cached or flat-rate shipping. For payments, return a clear error or pending state instead.
6. **Propagate a deadline.** If the caller has 2s left, downstream calls get less than that and retries stop once it's spent. This avoids wasted work.
7. **Tooling:** Resilience4j provides retry, circuit breaker, bulkhead, and time limiter. Spring Framework 7 adds core `@Retryable` and `@ConcurrencyLimit` (retry and bulkhead-style limiting), but it has no circuit breaker, so you'd still use Resilience4j for that.

**Trade-offs and what can go wrong**
- Retries multiply load: 3 layers each retrying 3 times means 27 calls per request (a retry storm). Retry at one layer only.
- Timeouts that are too short cause false failures. Too long and they don't protect you. Base them on the dependency's observed p99.
- Retrying non-idempotent calls causes duplicates, such as double charges.
- A breaker with poor thresholds flaps or never opens. Fallbacks can serve stale data silently.
- Deadline headers aren't standardized in HTTP (gRPC has deadlines built in), so agree on a convention across teams.

**How I'd monitor it**
- Resilience4j metrics through Micrometer: breaker state, failure and slow-call rate, retry counts, bulkhead rejections.
- Outbound latency p95/p99 and timeout counts per dependency, plus connection-pool wait time.
- Alerts when a breaker opens or fallback rate rises. In Splunk, search for breaker-open and retry-exhausted logs by correlation id.

**Follow-ups to expect**
- *Why not just retry more?* -> It adds load to a failing service and can turn a slowdown into an outage. Cap attempts and let the breaker stop retries.
- *Circuit breaker vs bulkhead?* -> The breaker stops calling a failing dependency. The bulkhead limits how many resources one dependency can use, even while it's healthy but slow.
- *How do you safely retry a POST?* -> Send an idempotency key so the server returns the original result for duplicates.

**60-second answer**
Every remote call is a failure point, so I start with timeouts on connect, read, and pool-acquire. I retry only idempotent calls, or POSTs with an idempotency key, on transient errors, using exponential backoff, jitter, and a cap, and I retry at one layer only. A circuit breaker fails fast when the dependency is unhealthy, and a bulkhead limits the threads and connections each dependency can use. Where the business allows it, I add a fallback such as cached data, and I pass a deadline downstream so nobody works for a caller who has already gone. I'd use Resilience4j, or Spring Framework 7's `@Retryable` and `@ConcurrencyLimit` for retry and concurrency limits. I'd watch breaker state, timeouts, retries, and latency percentiles per dependency.

### Q16 [senior] Compression, caching and performance tips?
tags: rest, performance, http-caching, compression, pagination, http2, latency, basics

**Start here: the concepts**
- **Compression (gzip/br):** the server shrinks the response body before sending it, and the client expands it. JSON is repetitive text, so it often shrinks a lot. This saves network time, at the cost of some CPU. gzip is universal; br (Brotli) usually compresses better.
- **Cache-Control:** a response header that tells browsers, gateways and CDNs whether they may reuse a response and for how long. For example, `max-age=60` means "reuse for 60 seconds without asking me". `private` means "only the end user's cache, not shared ones". It exists so repeated requests never reach your servers.
- **ETag and 304:** an ETag is a fingerprint (version label) of a response. The client sends it back in `If-None-Match`. If nothing changed, the server replies **304 Not Modified** with no body, so you save bandwidth and serialisation, though the request still travels.
- **Pagination:** return big lists in pages. Offset paging (`page=500`) gets slower on deep pages because the database skips rows. Cursor/keyset paging ("after id X") stays fast.
- **Field selection:** the client asks only for the fields it needs, for example `?fields=id,name`, so payloads are smaller.
- **Chatty API:** a client needs many small calls to do one job. Each call pays a network round trip, so a **batch endpoint** replaces N calls with one.
- **Connection reuse:** opening a TCP/TLS connection is slow. HTTP keep-alive reuses one connection for many requests. HTTP/2 also multiplexes many requests over one connection.
- **Async processing:** for slow work, return `202 Accepted` plus a status URL instead of holding the request open.
- **p95/p99:** the latency that 95% or 99% of requests beat. Averages hide the slow tail that users feel.

**The live scenario**
An orders API serves 2,000 requests/s. The mobile list endpoint returns 500 KB of JSON (all fields, 200 items). The average latency looks fine at 120 ms, but p99 is 3 s on poor mobile networks. A screen also makes 6 calls to build one view. After gzip, a `fields` parameter, cursor paging at 20 items, a batch endpoint and ETags on rarely-changing reference data, the payload drops to about 15 KB. The call count drops from 6 to 2 and p99 falls to about 600 ms (illustrative numbers).

**What the interviewer is really checking**
Whether you treat performance as measured, per-endpoint engineering with a known cost for each technique, not a list of buzzwords. They also want to see that you know when each tip is wrong.

**How I answer it**
1. **Measure first (p95/p99 per endpoint).** Averages hide the slow tail, and different endpoints have different problems. Otherwise you optimise the wrong thing.
2. **Shrink what you send.** Use pagination (cursor for deep lists), field selection and compression. Fewer bytes means less time on slow networks. In Spring Boot: `server.compression.enabled=true`, plus a minimum response size so tiny bodies are skipped.
3. **Send fewer requests.** Replace chatty call sequences with batch or composite endpoints. Round trips cost more than bytes.
4. **Reuse work.** Set `Cache-Control` for data that can be stale briefly. Add `ETag` so unchanged data returns 304. Use `private` for user-specific data and add `Vary: Accept-Encoding` so caches store compressed and plain versions separately.
5. **Reuse connections.** Keep-alive or HTTP/2 avoids repeated TCP/TLS handshakes. The same applies to your outgoing calls to third parties: use a pooled client with connect, read and pool-acquire timeouts.
6. **Move slow work off the request.** Return 202 with a status URL (or a webhook) so threads and clients are not blocked.

**Trade-offs and what can go wrong**
- Compression costs CPU. Skip tiny bodies and already-compressed content (images, PDFs). Be careful compressing HTTPS responses that reflect secrets next to attacker-controlled input (the BREACH attack).
- Caching the wrong thing serves stale or, worse, another user's data. Never cache personalised responses in a shared cache.
- ETags save bandwidth, but you still compute the response unless you check a cheap version first.
- Offset paging gets slower on deep pages and can skip or duplicate rows when data changes. Prefer cursors.
- Batch endpoints need limits and a partial-failure contract.
- Fields chosen by the client make caching and testing harder.

**How I'd monitor it**
- p50/p95/p99 latency per endpoint (for example Micrometer `http.server.requests`).
- Response size distribution.
- Cache hit ratio at the CDN/gateway, and the share of 304s.
- Calls per user action.
- Connection-pool wait time.
- CPU after enabling compression.
- Splunk searches on slow-request logs, grouped by endpoint and correlation id.

**Follow-ups to expect**
- *Does a 304 save the server work?* -> It saves bandwidth and serialisation. It only saves real work if you can cheaply check the version (a timestamp or version column) before building the response.
- *Why cursor over offset paging?* -> Offset makes the database skip N rows, which is slow on deep pages and unstable when data changes. A cursor seeks directly to "after this key".
- *Does HTTP/2 remove the need for batching?* -> It cuts connection overhead, but each call still has latency and server work, so batching remains worthwhile for dependent or many calls.

**60-second answer**
I start by measuring p95 and p99 per endpoint, because averages hide the slow tail. Then I reduce bytes with pagination, field selection and gzip or Brotli. I reduce round trips with batch endpoints and by reusing connections through keep-alive or HTTP/2. For data that rarely changes I add `Cache-Control` and ETags, so clients get a cheap 304 instead of the full body. Slow work returns 202 with a status URL. I watch the trade-offs: compression costs CPU, personalised data must never sit in shared caches, and deep offset paging gets slow, so I prefer cursors. Finally I confirm the gains in latency percentiles, cache hit ratio and response size.

### Q17 [mid] What is a webhook and how do you make it reliable?
tags: webhook, rest-api, hmac, idempotency, retries, dead-letter-queue, basics

**Start here: the concepts**
- **Webhook:** an HTTP callback. You give the provider a URL, and when an event happens (payment succeeded) the provider sends a POST to that URL. It exists so you don't have to poll ("anything new yet?") every few seconds.
- **Sender and receiver:** the sender is the system where the event happens. The receiver is the system that owns the URL and reacts to the event.
- **HMAC signature:** the sender computes a hash of the request body using a secret shared with the receiver and sends it in a header. The receiver recomputes it. If the values match, the body is genuine and unchanged. Anyone can POST to a public URL, so this proves who sent it.
- **Retry with backoff and jitter:** if delivery fails, the sender tries again after growing delays (1 min, 5 min, 30 min...). Jitter adds randomness so thousands of retries don't hit at the same instant.
- **Idempotent / event id:** processing the same event twice has the same effect as once. Each event carries a unique id so the receiver can recognise a duplicate.
- **Delivery log and replay:** a record of every attempt (time, status, response), plus a way to re-send an event on demand.
- **Dead-letter list:** the parking place for events that failed all retries, so they are visible and not silently lost.

**The live scenario**
A payments provider sends `payment.succeeded` webhooks to an order service, about 50 per second. During a deploy the receiver was down for 6 minutes, so roughly 18,000 events got errors. The sender retried with backoff, and the events arrived later, many twice because the first attempt had been processed but the reply timed out. Without event-id de-duplication, customers would have been shipped two orders. Without a delivery log and replay, the 40 events that exhausted their retries would have been lost for good.

**What the interviewer is really checking**
Whether you know a webhook is at-least-once delivery over an unreliable network, and whether you design for duplicates, forgery, slowness and loss on both the sender and receiver side.

**How I answer it**
1. **Define it:** the server POSTs to a client-registered URL when an event occurs. This avoids polling and gives near-real-time updates.
2. **Sign payloads (HMAC):** the sender signs the raw body with a shared secret, and the receiver verifies it using constant-time comparison on the raw bytes. I also include a timestamp in the signed data and reject old ones, so a captured request can't be replayed later.
3. **Sender: timeouts and retries:** the sender sets short connect and read timeouts (a few seconds) so one slow receiver can't block its workers. It treats any non-2xx or timeout as "unknown" and retries with exponential backoff plus jitter, for a bounded number of attempts.
4. **Idempotent event ids:** retries mean the same event can arrive twice, so every event has a unique id. The receiver stores processed ids (unique constraint) and skips duplicates. Order is not guaranteed either, so I use event timestamps or versions to ignore stale updates.
5. **Receiver: respond fast:** verify the signature, save the event, return 200, then process asynchronously via a queue. Slow processing inside the HTTP call causes timeouts, and timeouts cause more retries.
6. **Delivery log and replay endpoint:** the sender records each attempt and response, and offers an API or UI to re-send any event. This also covers the case where the receiver was down longer than the retry window.
7. **Dead-letter list:** after the last retry, the event moves to a dead-letter list that triggers an alert and can be replayed after the fix.
8. **Mindset:** treat the receiver as unreliable, since it can be down, slow or buggy, and design the sender so that never loses events or hurts itself.

```
X-Signature: t=1700000000,v1=<hex HMAC-SHA256 of "t.body">
```

**Trade-offs and what can go wrong**
- Delivery is at-least-once, not exactly-once. Duplicates are the price, so idempotency is mandatory.
- Verifying a parsed-and-reserialised body breaks the signature. Use the raw body.
- Endless retries to a dead endpoint waste resources. Cap attempts and disable endpoints that keep failing.
- Acknowledging before saving the event can lose it. Persist first, then return 200.
- Secrets leak or never rotate. Support rotation with two valid secrets for a period.

**How I'd monitor it**
- Sender: delivery success rate, attempts per event, retry-queue depth, age of the oldest undelivered event, dead-letter count (alert above 0).
- Receiver: signature-failure count, duplicate-event count, response-time p95, processing lag behind the queue.
- Logs (for example in Splunk): search by event id and correlation id to trace one event across all attempts.

**Follow-ups to expect**
- *Why not just poll instead?* -> Polling wastes calls and adds delay. Webhooks are real-time, but they need the reliability work above, and many systems add a periodic reconciliation poll as a safety net.
- *How does the receiver handle duplicates?* -> It keeps a table of processed event ids with a unique constraint and returns 200 for ones it has already seen.
- *Which status codes should the receiver return?* -> 2xx means accepted and stops retries. 4xx for a bad signature (retrying won't help). 5xx or timeout makes the sender retry.

**60-second answer**
A webhook is an HTTP callback: when something happens, the provider POSTs to a URL I registered, so I don't have to poll. Because networks fail, delivery is at-least-once, so I design for duplicates and loss. The sender signs each payload with HMAC and a timestamp, uses short timeouts, and retries with exponential backoff and jitter. Every event has a unique id, and the receiver stores the ids it has processed so duplicates do nothing. The receiver verifies the signature, saves the event, returns 200 quickly, and processes it asynchronously. The sender keeps a delivery log with a replay endpoint, and events that exhaust their retries go to a dead-letter list with an alert. I treat the receiver as unreliable and monitor success rate, retry age and dead-letter count.

### Q18 [architect] Design a public "Orders" API for 3rd-party partners.
tags: rest-api, api-design, idempotency, oauth2, webhooks, rate-limiting, basics

**Start here: the concepts**
- **Idempotency key:** a unique value the client sends with a POST. If the same key arrives again, the server returns the first result instead of creating a second order. It exists because a timeout leaves the client not knowing whether the call worked.
- **Optimistic version (ETag + If-Match):** every order carries a version tag (ETag). An update sends it back in `If-Match`. If someone else changed the order meanwhile, the server answers 412 instead of silently overwriting.
- **Cursor pagination:** the client gets a page plus an opaque "next" token. It stays correct when rows are added, unlike page numbers, and it is fast on large tables.
- **ETag caching:** the client sends `If-None-Match` and the server answers 304 (no body) if nothing changed. This saves bandwidth and load.
- **Problem Details (RFC 9457):** a standard JSON error shape (`type`, `title`, `status`, `detail`). Add a stable error code and a correlation id.
- **OAuth2 client credentials:** a partner's server exchanges its id and secret for a short-lived token. No human is involved.
- **Gateway rate limit:** a front door that caps each partner's requests, so one partner cannot starve the others.
- **Webhook signing:** we call the partner's URL with events. We attach an HMAC signature (a hash made with a shared secret) so they can verify the sender.
- **Additive change:** adding optional fields or endpoints, which never breaks existing clients.

**The live scenario**
A partner sends about 40,000 `POST /orders` a day. During a 30-second database slowdown, their client times out and retries. The retries create 600 duplicate orders and 600 double shipments. Support spends two days fixing them. Separately, a field rename in "just a small release" breaks three partners' parsers. Both problems come from API design, not code bugs.

**What the interviewer is really checking**
Whether you treat the API as a long-lived contract with strangers: safe retries, predictable errors, tenant isolation, evolution without breakage, and operability.

**How I answer it**
1. **Model resources:** `/orders`, `/orders/{id}`, `/orders/{id}/payments`. Nouns and standard verbs keep it predictable. For slow work, return `202 Accepted` with a status URL.
2. **Authenticate and isolate:** OAuth2 client credentials with scopes. Always check that the order belongs to the calling partner, or one partner can read another's orders by guessing ids.
3. **Protect capacity:** the gateway enforces per-partner limits and returns `429` with `Retry-After`, so one noisy partner cannot hurt the rest.
4. **Make writes safe:** require an idempotency key on POST. Store it with a hash of the request body. Same key and same body returns the original response. Same key and a different body returns an error (422 or 409). Use ETag + `If-Match` for updates.
```
POST /orders
Idempotency-Key: 7c1e-...-a9
```
5. **Make reads cheap:** cursor pagination, documented filters, and ETag with 304 responses.
6. **Make errors a contract:** use RFC 9457 with stable codes and a request id in every response. Never pass through internal or vendor errors.
7. **Evolve safely:** URL major version (`/v1`), additive changes only, a changelog, a sandbox for testing, and a deprecation notice period with a `Sunset` header.
8. **Push events:** signed webhooks. Include a timestamp in the signed data to block replays. Delivery is at-least-once with backoff retries, so partners dedupe by event id.

**Trade-offs and what can go wrong**
- Idempotency storage costs space. Expire keys after a documented window, for example 24 hours.
- URL versions are simple but multiply the versions you must support. Header versioning is cleaner but harder for partners to use.
- Strict rate limits protect you but hurt legitimate bursts. Offer per-partner tiers.
- Webhook consumers that are slow or down cause retry storms. Cap retries and offer an event replay endpoint.
- Common mistakes: changing a field's meaning, leaking stack traces, using offset pagination on huge sets.

**How I'd monitor it**
Per-partner dashboards cover request rate, p95/p99 latency, 4xx/5xx split, 429 count and webhook failure rate. Set SLOs, such as 99.9% availability, and alert on error-budget burn. Search logs by request id, for example in Splunk. Track idempotency-key replays (a spike means partners are timing out). Meter usage per partner for billing and capacity planning.

**Follow-ups to expect**
- *Why not just retry POST safely without a key?* -> A timeout means the outcome is unknown. Without a key, the retry may create a duplicate.
- *How do you remove a field?* -> Don't within a version. Deprecate it, announce a `Sunset` date, then remove it in `/v2`.
- *How do partners trust webhooks?* -> Verify the HMAC over the raw body plus timestamp, reject old timestamps, and dedupe by event id.

**60-second answer**
I'd model orders, order details and payments as resources, secured with OAuth2 client credentials. The gateway rate-limits each partner, and every query is scoped to the calling partner. Writes use idempotency keys, so a retry after a timeout can't create a duplicate. Updates use ETag with `If-Match` to avoid lost updates. Reads use cursor pagination and ETag caching. Errors follow RFC 9457 with stable codes and a request id. I version by URL, allow only additive changes, announce deprecations, and give partners a sandbox. For events I send signed webhooks with at-least-once delivery. I watch per-partner latency, errors and 429s against SLOs.

### Q19 [architect] Design an API gateway layer. What belongs there and what does not?
tags: api-gateway, rest, rate-limiting, authentication, bff, resilience, observability, basics

**Start here: the concepts**
- **API gateway:** a single front door that all outside clients call. It forwards each request to the right internal service. It exists so cross-cutting rules live in one place instead of being copied into 40 services.
- **TLS termination:** the gateway decrypts HTTPS traffic and manages certificates centrally. Internal hops may be re-encrypted (mTLS) if your security policy requires it.
- **Authentication vs authorization:** authentication asks "who are you?" (for example, validating a JWT or API key). Authorization asks "what may you do?". *Coarse* authorization is a broad check such as "does this token have the orders scope?". *Fine-grained* authorization is "may this user see this order?", which needs business data.
- **Rate limiting:** capping requests per client in a time window (returning 429) so one noisy client cannot starve the others.
- **Routing:** mapping a path or host (such as `/orders/**`) to a backend service.
- **CORS:** browser rules about which web origins may call your API. The gateway answers these headers once.
- **Canary routing:** sending a small share of traffic (say 5%) to a new version to test it before a full rollout.
- **BFF / aggregator:** a "backend for frontend" is a separate service that calls several domain services and shapes one response for a specific client. It is a normal service with its own owners and tests.

**The live scenario**
A retailer has 40 microservices and one gateway handling 3,000 requests/second. To "save a call", a team added discount calculation and a three-service order-summary merge inside the gateway. A bug in that code caused a gateway deploy rollback at peak. Because every API sat behind the gateway, the whole platform was down for 12 minutes. Gateway releases also became weekly, coordinated events. The fix was to move that logic into a BFF and return the gateway to thin, boring, rarely changed duties.

**What the interviewer is really checking**
Whether you see the gateway as a shared, critical-path piece of infrastructure that must stay thin, and whether you can explain where the boundary lies and why.

**How I answer it**
1. **Put cross-cutting, business-agnostic concerns in the gateway.** These are TLS termination, authentication, coarse authorization, rate limiting, routing, CORS, request/response logging and canary routing. They are the same for every service, so one enforcement point is cheaper and safer than 40 copies.
2. **Cache only public GETs.** Cache responses that are identical for every caller. Caching personalised data risks leaking one user's data to another.
3. **Log metadata, not payloads.** Record method, path, status, latency, client id and a correlation id, which the gateway creates if it is missing and passes downstream. Do not log bodies or tokens, because they contain personal data and secrets.
4. **Keep business logic out.** Pricing, eligibility and workflow rules change often and belong to domain teams. In the gateway they couple every team to one release pipeline.
5. **Keep cross-domain orchestration out.** Calling several services and merging results needs timeouts, fallbacks and partial-failure decisions. Put that in a BFF/aggregator that a team owns.
6. **Keep heavy transformations out.** Large payload rewriting burns gateway CPU and memory on the shared path. Simple header edits are fine.
7. **Still validate in the services.** Services should verify tokens or identity too, and do fine-grained authorization themselves. Do not trust "it came through the gateway" alone.
8. **Make it highly available and config-driven.** Run at least three stateless instances across zones behind a load balancer. Keep routes, limits and policies in Git and deploy them through review and CI, so changes are auditable and reversible.
9. **Set upstream timeouts.** Without them, a slow backend ties up gateway threads and the failure spreads to every route.

**Trade-offs and what can go wrong**
- The gateway is a single point of failure and an extra network hop (typically a few ms). Redundancy and a thin design reduce the risk.
- Rate-limit counters kept in each instance's memory give inconsistent limits. A shared store such as Redis fixes that but adds a dependency, so decide whether to fail open or closed if it is down.
- Gateway logic creeps in "just this once". Enforce the boundary through design review.
- A gateway team that becomes a bottleneck for every change. Let teams own their route config through pull requests.

**How I'd monitor it**
- Per-route request rate, p95/p99 latency, and 4xx/5xx rate, plus the 429 rate per client.
- Gateway latency compared with upstream latency, to show who is slow.
- CPU, memory and open connections per instance.
- Splunk: search by correlation id across gateway and service logs, and alert on a 5xx spike per route or a sudden rise in 401/403.
- Canary comparison of error rate and latency against the stable version.

**Follow-ups to expect**
- *Gateway vs BFF?* -> The gateway is generic, shared infrastructure. A BFF is a service tailored to one client type that aggregates and shapes data.
- *Where does fine-grained authorization go?* -> In the owning service, which has the data to decide. The gateway only checks things like token validity and scope.
- *Gateway vs service mesh?* -> The gateway handles north-south traffic (outside to inside). A mesh handles east-west traffic between services, such as mTLS and retries.

**60-second answer**
An API gateway is the single front door to my services, so I keep only business-agnostic, cross-cutting work in it. That means TLS termination, authentication, coarse authorization, rate limiting, routing, CORS, request/response logging without bodies, caching of public GETs, and canary routing. I keep business logic, cross-domain orchestration and heavy transformations out, because they change often and would tie every team to one risky release. Orchestration goes in a BFF or aggregator service. Services still check identity and do fine-grained authorization themselves. I run the gateway stateless on several instances, set upstream timeouts, and keep config in Git. I monitor per-route latency, error rates and 429s, and trace requests by correlation id in Splunk.

### Q20 [mid] How do you deprecate an endpoint without breaking clients?
tags: rest, api-versioning, deprecation, sunset-header, backward-compatibility, api-governance, basics

**Start here: the concepts**
- **Breaking change**: a change that makes existing client code fail, such as removing a field, renaming a URL, or changing a type. Adding an optional field is usually not breaking. Only breaking changes need deprecation.
- **Deprecation**: officially saying "this still works, but stop using it, a replacement exists". It is a warning, not a removal.
- **Sunset**: the date after which the endpoint stops working.
- **`Deprecation` and `Sunset` headers**: HTTP response headers that carry these messages to client code. `Sunset` is defined in RFC 8594 and `Deprecation` in RFC 9745. A `Link` header can point to the migration guide.
- **Client identifier**: something that tells you who is calling, such as an API key, OAuth client id or `User-Agent`. Without one you cannot tell who still uses the old endpoint.
- **Running both versions**: the old and new endpoints live side by side so clients can migrate at their own pace.

**The live scenario**
Our `/v1/orders` returns `price` as a string. The new `/v2/orders` returns a structured `money` object. About 40 clients call v1, 3.2 million calls a day. We announced a sunset 6 months out. At 2 months, 31 clients had moved. Usage logs showed 9 clients still calling, and one partner alone made 80% of the traffic. Without logs by client, we would have switched v1 off and broken that partner's checkout.

**What the interviewer is really checking**
Whether you treat removal as a managed process with communication and data, not a code change, and whether you know consumers you cannot see will break.

**How I answer it**
1. **Check the change is really breaking.** Additive changes need no deprecation. This avoids needless versions to maintain.
2. **Ship the replacement first and run both.** Clients cannot migrate to something that does not exist yet. Publish a migration guide with old-to-new field mapping.
3. **Announce with a firm date.** Use the changelog, email and developer portal. A date gives clients a deadline their managers can plan around.
4. **Signal in every response.** Machine-readable warnings reach developers who never read emails:
```
Deprecation: true
Sunset: Wed, 31 Dec 2025 23:59:59 GMT
Link: <https://docs.example.com/v2-migration>; rel="deprecation"
```
5. **Log who still calls it, by client id.** This tells you who to contact and how big the risk is.
6. **Contact heavy users directly.** Emails get ignored, so call the owners of the biggest traffic. Offer help.
7. **Use brownouts (optional).** Briefly return errors on the old endpoint, for example 30 minutes, so hidden dependencies surface while the cost is small.
8. **Remove on the date, with data guiding exceptions.** The stored answer said to wait for usage near zero. That can mean waiting forever, because someone always forgets. The date is the commitment. Metrics tell you whether to hold for a named client with a plan. After removal, return `410 Gone` with a problem-details body pointing to v2, not a bare 404.

**Trade-offs and what can go wrong**
- Running two versions doubles testing and bug-fixing, so keep the window bounded.
- Dates that keep slipping teach clients to ignore every notice.
- Clients behind shared or missing API keys cannot be traced, so require identification before you need it.
- Internal or mobile clients may not update quickly because old app versions stay installed. Allow longer windows for them.
- Clients may ignore the headers, which is why you need direct contact.

**How I'd monitor it**
- A Splunk search counting calls to the deprecated path per day, split by client id, plotted on a dashboard.
- Alert if a new client id starts calling the old endpoint after the announcement.
- Track "clients remaining" and "calls per day" against the sunset date.
- After removal, watch the count of `410` responses by client to find who was missed.

**Follow-ups to expect**
- *Why not just version in the URL forever?* -> Every version has a maintenance cost, so you need a retirement process.
- *What if a key partner will not migrate by the date?* -> Agree a written extension with a final date, or keep a narrow compatibility shim for them.
- *What status code after removal?* -> `410 Gone`, with an RFC 9457 problem body linking to the new endpoint.

**60-second answer**
First I check the change is really breaking, because additive changes need no deprecation. Then I ship the replacement and run both versions, with a migration guide. I announce a firm sunset date and add `Deprecation`, `Sunset` and `Link` headers to every old response. I log calls by client id so I know who still uses it, and I contact the heavy users personally. I may run short brownouts to flush out hidden callers. On the date I remove it and return `410 Gone` with a pointer to the new endpoint. Usage metrics tell me whether a specific client needs a short extension, but I don't wait for zero traffic.

### Q21 [mid] What is REST?
tags: rest, http, api-design, stateless, resources, status-codes, basics

**Start here: the concepts**
- **Architectural style:** A set of design constraints, not a product, library or protocol. Roy Fielding described REST in his 2000 doctoral dissertation. A system is "RESTful" to the degree it follows those constraints.
- **Resource:** A "thing" the API exposes, such as an order or a customer. It is a noun, not an action.
- **URL (URI):** The address that identifies one resource. Example: `/api/v1/orders/123` is order 123, and `v1` is the API version.
- **Standard HTTP methods:** GET reads, POST creates or triggers, PUT replaces, PATCH changes part of a resource, DELETE removes. Everyone already knows what they mean, so clients, proxies and caches can act without custom documentation. GET, PUT and DELETE are defined as idempotent, meaning repeating them has the same effect as doing them once. POST is not.
- **Stateless:** Each request carries everything the server needs (credentials, ids, parameters). The server keeps no per-client conversation between requests. This is why you can add servers behind a load balancer and any server can answer any request.
- **Representation:** The format in which a resource is sent, such as JSON or XML. The resource and its representation are different things. "Consistent representations" means the same kind of resource always has the same shape.
- **Caching:** Reusing a previous response instead of asking again. Headers like `Cache-Control` and `ETag` tell clients and proxies when this is safe.
- **Status codes:** Numbers that say what happened: 200 OK, 201 Created, 400 bad request, 404 not found, 409 conflict, 500 server error. Clients branch on them.
- **Other constraints:** Client-server separation, layered system (proxies and gateways in between), and hypermedia (responses contain links to next actions). Many "REST" APIs skip hypermedia.

**The live scenario**
A mobile app calls an "order API" that is really one endpoint, `POST /doEverything`, with an `action` field in the body. It always returns 200, even for errors, with the error text inside the JSON. Traffic is 2,000 requests per second at peak. The CDN cannot cache anything because everything is a POST. Dashboards show 99.9% success while customers see failures, because the failures are hidden inside 200 responses. A redesign to `GET /api/v1/orders/123`, `POST /api/v1/orders` and honest status codes lets the CDN cache reads, and alerts on 5xx finally work.

**What the interviewer is really checking**
Whether you can explain REST as a set of design constraints and show how they matter in practice (scaling, caching, error handling), instead of reciting "it uses HTTP and JSON".

**How I answer it**
1. **Define it:** REST is an architectural style for networked systems, not a protocol. This stops the common confusion that REST equals HTTP.
2. **Resources and URLs:** Model nouns, not verbs: `/orders/123`, not `/getOrder`. A stable address per thing makes the API predictable.
3. **Standard methods:** Let the HTTP method express the action. Tools and caches understand GET as safe and cacheable, and PUT/DELETE as idempotent.
4. **Stateless requests:** Send everything needed on every call. This makes horizontal scaling simple and failures easy to recover from, because a retry can hit any server.
5. **Consistent representations:** Keep the same shape and naming for the same resource. Clients then need less special-case code.
6. **Caching where appropriate:** Mark safe reads as cacheable. It cuts load and latency, but only where slightly stale data is acceptable.
7. **Standard status codes:** Use codes honestly, and return errors in a stable format such as RFC 9457 problem details with a correlation id. Clients, retries and monitoring all depend on this.
8. **Close with the caveats:** REST is not synonymous with JSON, and an API is not automatically RESTful just because it uses HTTP. A single POST endpoint tunnelling actions is HTTP, but not REST.

**Trade-offs and what can go wrong**
- Real APIs are often "REST-ish": they skip hypermedia, which is fine if you say so honestly.
- Statelessness moves state to the client or a database, so requests get larger or need extra lookups.
- Caching wrongly can serve stale prices or stock levels.
- Not everything fits CRUD. Actions like "cancel order" need a sensible design, such as `POST /orders/123/cancellation`.
- Do not assume POST is safe to retry. After a timeout the outcome is unknown, so POSTs with side effects need idempotency keys.

**How I'd monitor it**
- Request rate, latency percentiles and error rate per endpoint, split by status class (2xx, 4xx, 5xx).
- Cache hit ratio at the CDN or gateway.
- In Splunk, search by correlation id and group by endpoint and status. A 200 that carries an error body is a design smell.
- Alerts on rising 5xx and on 4xx spikes after a release, which often means a broken contract.

**Follow-ups to expect**
- *What is the difference between PUT and PATCH?* -> PUT replaces the whole resource and is idempotent. PATCH changes only the fields sent.
- *Why is statelessness important?* -> Any server can handle any request, so you can scale out and recover from failures easily.
- *Is POST idempotent?* -> No. Repeating it can create duplicates, so use an idempotency key for retries.

**60-second answer**
REST is an architectural style for networked systems, not a protocol or a data format. In a typical RESTful HTTP API, resources like `/api/v1/orders/123` are identified by URLs and handled with standard methods: GET, POST, PUT, PATCH and DELETE. Requests are stateless, so each one carries everything the server needs and any server can answer it. Representations are consistent, caching is used where it is safe, and standard status codes tell clients what happened. REST is not the same as JSON, and using HTTP does not make an API RESTful. A single POST endpoint that always returns 200 is HTTP, but not REST.

### Q22 [mid] What is the difference between authentication and authorization?
tags: authentication, authorization, rest-api, spring-security, access-token, idor, basics

**Start here: the concepts**
- **Authentication (authn):** proving who the caller is, for example with a password, a login through an identity provider, or a signed token. It exists because a server cannot trust a name the caller just claims.
- **Authorization (authz):** deciding what an already-identified caller may do. It exists because "we know who you are" does not mean "you may do everything."
- **Access token (for example a JWT):** a small signed piece of data the caller sends with each request, usually in the `Authorization` header. It carries the caller's identity and sometimes roles or scopes. A "valid" token means the signature is genuine and it has not expired. It says nothing about which specific records the caller may touch.
- **Role/scope:** a coarse permission label such as `ORDER_READ`. It answers "may this kind of user call this kind of endpoint?"
- **Object-level authorization:** a finer check that the caller is entitled to this particular record, for example order `123`. Skipping it is a well-known flaw called IDOR or BOLA (broken object-level authorization).
- **401 vs 403:** `401` means "I don't know who you are" (authentication failed). `403` means "I know who you are, and the answer is no" (authorization failed).

**The live scenario**
A B2B order API handles about 40,000 requests an hour. A customer reports that changing `/orders/123` to `/orders/124` in the URL showed another company's order. The gateway validated the token on every call, and the token was genuine. But `GET /orders/{id}` only checked "is the user logged in?" and never "does this order belong to this user's account?" Over three days, roughly 200 orders (illustrative) were readable by the wrong customers. This was an authorization failure, not an authentication one.

**What the interviewer is really checking**
Whether you separate "who" from "what allowed," and whether you know that a valid token alone is not enough. A mid-level candidate should bring up object-level checks and the 401/403 distinction without being asked.

**How I answer it**
1. **Define the two terms in one line each.** Authentication is "who are you?" and authorization is "what are you allowed to do?" This shows the order: you must know who someone is before deciding what they may do.
2. **Authenticate first, at the edge.** The gateway or security filter verifies the token's signature and expiry. Reject failures with `401`. Doing this once, centrally, means no controller can forget it.
3. **Apply coarse authorization next.** Check roles or scopes for the endpoint. Reject failures with `403`. This is cheap and needs no database lookup.
4. **Then enforce object-level authorization.** Load the order and verify it belongs to the caller's customer or account, or that the caller has a rule granting access. The reason is that a valid token proves identity, not entitlement to order `123`.
5. **Put the check close to the data.** Do it in the service layer or in the query itself, not only at the gateway, because only the service knows who owns the record. In Spring Security, for example:
```java
@PreAuthorize("@orderAccess.canRead(#id, authentication)")
```
6. **Return a stable error contract.** Use an RFC 9457 problem-details body with a stable error code and a correlation id. Never reveal internal reasons.

**Trade-offs and what can go wrong**
- Trusting a customer id sent in the request body or URL instead of taking it from the token lets callers pose as others.
- Checking only at the gateway leaves internal paths unprotected.
- Returning `403` for someone else's order confirms the order exists. Many teams return `404` instead, which hides existence but makes debugging harder.
- Putting permissions in the token makes them stale until it expires, so keep tokens short-lived.
- Object-level checks add a lookup. Accept this cost, since the alternative is a data leak.

**How I'd monitor it**
- Track `401` and `403` rates per endpoint, and alert on spikes (possible probing).
- In Splunk, search for one user id requesting many distinct order ids in a short window (enumeration).
- Log user id, resource id, decision and correlation id for every denial.
- Add automated tests: user A requests user B's order and must get `403` or `404`.

**Follow-ups to expect**
- *Why is 401 named "Unauthorized" if it means unauthenticated?* -> It is a historical naming quirk. In practice, `401` is for missing or invalid credentials, and `403` is for a known caller who lacks permission.
- *Is checking roles enough?* -> No. Roles are coarse. You also need object-level checks so a `CUSTOMER` role cannot read other customers' data.
- *Where should authorization live in a microservice system?* -> Authenticate at the gateway, but enforce authorization in each service that owns the data, because the gateway does not know record ownership.

**60-second answer**
Authentication answers "who are you?" and authorization answers "what are you allowed to do?" I authenticate first, usually by validating a signed token at the gateway, and return `401` if that fails. Then I check coarse permissions like roles or scopes and return `403` if they fail. A valid token does not mean the caller may access everything, so I also enforce object-level authorization: I confirm the authenticated user is entitled to order `123` before returning it. I do that in the service that owns the data and take the user's identity from the token, never from the request. I monitor `401`/`403` spikes and look for one user requesting many different ids.

### Q23 [mid] How do you make API changes without breaking clients?
tags: rest, api-versioning, backward-compatibility, tolerant-reader, deprecation, contract-testing, basics

**Start here: the concepts**
- **Breaking change**: a change that makes an existing client fail or misbehave without the client changing. Clients are code we don't control, and they were written against the old behaviour.
- **Contract**: everything a client may rely on, not only field names. It includes types, nullability, formats, ordering, status codes and error bodies.
- **Additive change**: adding something new and optional (a response field, an optional request field, a new endpoint) while leaving everything old untouched.
- **Tolerant reader**: a client that ignores fields it doesn't know and doesn't crash on surprises. It makes additive changes safe. In Jackson this means not failing on unknown properties.
- **Versioning**: running old and new contracts side by side (`/v1/`, `/v2/`, or a header) so clients move when they are ready.
- **Deprecation**: announcing that something will be removed, with a date. Not the same as removing it.
- **Enum evolution**: adding a new value to a fixed list (e.g. status `REFUNDED`). Clients with a strict switch may crash on a value they have never seen.
- **Pagination semantics**: how paging behaves (page size, cursor vs page number, ordering). Changing it quietly changes what clients receive.

**The live scenario**
An orders API serves 40 client apps, about 2,000 requests per second. A developer adds a new order status, `PARTIALLY_SHIPPED`, and changes `createdAt` from `2024-05-01T10:00:00Z` to epoch milliseconds. After the release, the mobile app's strict enum parser throws on the new status, and a partner's report job fails to parse dates. The error rate for those clients jumps from 0.1% to 18%, and rollback takes 40 minutes. Nobody knew who was using what.

**What the interviewer is really checking**
Whether you know that "compatible" covers more than field names (enums, nulls, formats, paging, errors). They also want to see a managed process: measure, deprecate, migrate, remove.

**How I answer it**
1. **Prefer additive changes.** Add optional fields and new endpoints instead of editing existing ones. Old clients ignore what they don't know, so nothing breaks.
2. **Never silently change the meaning or type of an existing field.** A client written against the old meaning can't detect the change. If `amount` was in dollars, it must not become cents. Add `amountCents` instead.
3. **Make new request fields optional with safe defaults.** A newly required request field breaks every existing caller.
4. **Treat these as breaking, even though they look small:**
   - New enum values. Document up front that clients must handle unknown values, and for new APIs include an `UNKNOWN` fallback.
   - A field changing from non-null to nullable.
   - Date/time format changes. Stick to ISO 8601 with a timezone.
   - Pagination changes such as page size, ordering or cursor format.
   - Error response changes. Keep the error shape and error codes stable; RFC 9457 problem details is a good base.
5. **Version only when a breaking change is unavoidable.** Each version is more code to run and test, so versioning is a last resort. Put it in the URL or a header and run old and new in parallel.
6. **Measure client usage first.** Log the version, the client id and the endpoint on every call. You can't retire `v1` until you know who still calls it.
7. **Publish a deprecation plan.** Announce a removal date, add a `Sunset` response header (RFC 8594), contact the heavy users directly, and write migration docs with before/after examples.
8. **Catch breaks before release.** Run contract tests or schema-diff checks in CI so a breaking change fails the build.

**Trade-offs and what can go wrong**
- Additive-only grows messy over time (old fields linger forever), but this is cheaper than breaking clients.
- Many live versions multiply the testing and support cost. Set a limit, for example two versions.
- "Additive" is not always safe: new enum values and strict clients are the classic trap.
- Deprecating without removing teaches clients to ignore warnings. Follow through with brownouts (short planned outages) and a firm date.
- Changing the error format is often forgotten, yet clients parse it for retry decisions.

**How I'd monitor it**
- Requests per version and per client id, in a Splunk dashboard. The goal is to see `v1` traffic decline toward zero.
- 4xx and 5xx rates per client after every release, with an alert on a jump.
- Counts of calls to deprecated endpoints, plus a list of clients still using them.
- Contract-test results in CI.
- Client parse errors reported by partners or in app crash logs.

**Follow-ups to expect**
- *URL versioning or header versioning?* -> URL is simple, visible and easy to route and cache. Headers keep URLs clean but are easier to miss and harder to test by hand. Pick one and stay consistent.
- *Is adding a response field always safe?* -> Only if clients are tolerant readers. Strict schema validators will reject unknown fields, so state the tolerance rule in your API guidelines.
- *How do you know it's safe to switch off v1?* -> Usage metrics show near-zero traffic. The remaining callers have been contacted, and a brownout caused no complaints.

**60-second answer**
I first try to make only additive changes: new optional fields and new endpoints. I never change the type or meaning of an existing field, because clients can't detect that. I also remember that enum values, nullability, date formats, pagination and error bodies are all part of the contract. If a breaking change can't be avoided, I add a new version and run both side by side. Before retiring the old one, I measure who still calls it, announce a sunset date, and give migration docs. I back all this with contract tests in CI and per-client usage dashboards, so breakage is caught before clients see it.

### Q24 [mid] How do you find the slowest API endpoints?
tags: splunk, latency, percentiles, observability, rest-api, slow-endpoints, basics

**Start here: the concepts**
- **Endpoint**: one URL path plus an HTTP method, such as `GET /orders/{id}`. "Slowest API" really means "slowest endpoint".
- **Latency / duration**: the time from when the server receives a request to when it finishes the response. We log it as `duration_ms`.
- **Splunk and SPL**: Splunk stores and searches logs. SPL is its query language, where steps are chained with `|`. `stats` groups events and computes numbers such as count and average.
- **Average (mean)**: the sum of all durations divided by the count. A few very slow requests barely move it, so it can hide pain.
- **Percentile (p95, p99)**: p95 is the value that 95% of requests are faster than. If p95 is 800 ms, 1 in 20 requests takes 800 ms or more. Percentiles show what your slowest users feel.
- **Route template**: the pattern `/orders/{id}`, as opposed to the raw URL `/orders/12345`. Grouping must use the template, or every ID becomes its own group.

**The live scenario**
A checkout service handles about 2,000 requests per minute. Users complain that "payment is sometimes slow", but the dashboard shows an average of 220 ms, which looks healthy. The team groups by endpoint and sorts by p95. `POST /payments` has a p95 of 4.8 s and a p99 of 9 s, because a third-party payment gateway occasionally stalls. About 3% of payments were crawling, and the average hid it completely.

**What the interviewer is really checking**
Whether you know that averages mislead and percentiles don't, and whether you question the data (is the field numeric, how is it measured, are the groups meaningful) before trusting a ranking.

**How I answer it**
1. **Make sure each request logs a numeric `duration_ms`, plus endpoint, method, status and a correlation id.** Without a number per request there is nothing to rank. The correlation id lets you follow one slow request across services later.
2. **Group by route template, not raw URL.** Otherwise `/orders/1` and `/orders/2` become separate groups, each too small to mean anything.
3. **Compute count, average, p95 and p99 per endpoint, then sort by p95.**
   ```spl
   index=application sourcetype=app:json
   | stats count avg(duration_ms) as avg_ms p95(duration_ms) as p95_ms p99(duration_ms) as p99_ms by endpoint
   | sort - p95_ms
   ```
   Renaming the results with `as` makes the later `sort` easier to write than using the raw `p95(duration_ms)` name.
4. **Use percentiles, not just averages.** A small number of slow requests is hidden by the mean but shows up clearly in p95 and p99.
5. **Validate the field.** Check that `duration_ms` is numeric (not a string like `"120ms"`) and measured the same way everywhere. For example, make sure every service times from the same start point, and that none logs seconds while another logs milliseconds. Otherwise the ranking is wrong.
6. **Read count next to the percentiles.** An endpoint with 3 calls and a huge p99 is noise. One with 50,000 calls and p95 of 2 s is a real problem.
7. **Then drill down.** Take the worst endpoint, filter by time window and status, and use the correlation id to see whether the time went to the database, a downstream call, or the app itself.

**Trade-offs and what can go wrong**
- Splunk's percentile functions are approximate. That is fine for ranking, but use `exactperc95` if you need exact values.
- Never average percentiles across time buckets or hosts. Recompute from the raw events instead.
- Server-side duration excludes network time and queueing before the request reaches the app, so users may see worse latency than your logs show.
- Slow endpoints are not always the most important ones. Weigh them by traffic and business value.
- Missing or non-numeric `duration_ms` values are silently skipped by `stats`, which can make results look better than they are.

**How I'd monitor it**
- Save the search as a dashboard panel with p50, p95 and p99 over time per endpoint, using `timechart`.
- Alert when p95 for a key endpoint exceeds its target (for example, 1 s) for several consecutive minutes.
- Run a data-quality check: `| where isnull(duration_ms) OR NOT isnum(duration_ms)` should return nothing.
- Track error rate and request count next to latency, so you can tell slow from failing.

**Follow-ups to expect**
- *Why not just use the average?* -> A few very slow requests barely move the mean, so users can be suffering while the average looks fine. Percentiles expose that tail.
- *What's the difference between p95 and p99?* -> p95 means 5% of requests are slower than that value, and p99 means 1% are. p99 is the more extreme tail and is often where downstream stalls appear.
- *Once you find a slow endpoint, how do you find the cause?* -> Follow a slow request's correlation id across services, and compare the time spent in the database, in downstream calls and in your own code.

**60-second answer**
I make sure every request logs a numeric `duration_ms`, along with the endpoint as a route template, the status and a correlation id. In Splunk I run `stats` grouped by endpoint to get count, average, p95 and p99, then sort by p95. I prefer percentiles because the average hides a small number of very slow requests, and those are what users complain about. I check that `duration_ms` is really numeric and measured the same way in every service, and I look at the count so I don't chase tiny samples. Then I take the worst endpoint and use correlation ids to find where the time goes. Finally I put it on a dashboard with an alert on p95.

### Q25 [mid] How do you secure your REST API?
tags: rest-api, security, oauth2, jwt, authorization, rate-limiting, basics

**Start here: the concepts**
- **HTTPS (TLS):** HTTP encrypted in transit. Without it, anyone on the network path can read or change passwords, tokens and data. It exists because the network is untrusted.
- **Authentication (authn):** proving who the caller is. **Authorization (authz):** deciding what that caller may do. They are different checks, and many breaches come from doing the first and skipping the second.
- **OAuth2:** a standard where a trusted *authorization server* logs the user in and issues a short-lived **access token**. Your API never sees the user's password. It exists so many apps can share one login system safely.
- **JWT (JSON Web Token):** a signed token format that carries claims such as user id, roles and expiry. The API verifies the signature and expiry without a database call. JWT is a *format*, and OAuth2 is a *process*. An OAuth2 server often issues JWTs.
- **Role check (RBAC):** access rules based on a role, such as CUSTOMER or ADMIN.
- **Object-level authorization:** checking that *this specific record* belongs to *this caller*. Without it, a logged-in user can change an id in the URL and read someone else's data. This is known as IDOR or BOLA.
- **Input validation:** rejecting malformed or oversized input at the edge. It exists because attackers send input you did not expect.
- **Rate limiting:** capping requests per client or time window. It exists to stop brute-force, scraping and overload.
- **CORS:** a *browser* rule that decides which websites' JavaScript may call your API. It is not protection against scripts or servers.
- **Safe error messages:** errors that tell the caller what to fix without exposing stack traces, SQL or internal names.

**The live scenario**
A banking API has `GET /accounts/{id}/transactions`. It had HTTPS, valid tokens and a CUSTOMER role check. A tester logged in as customer A and changed the id to customer B's account. They received 200 OK with B's transactions, because the role check only asked "is this a customer?". In a fuzz test, 50,000 sequential ids were enumerated in minutes. Fixing it meant adding an ownership check and rate limiting. Unknown ids and other people's ids now return the same 404.

**What the interviewer is really checking**
Whether you see security as layers and know that authentication plus role checks is not enough. You should name object-level authorization, and show you know CORS and JWT are not magic.

**How I answer it**
1. **Use HTTPS everywhere.** Terminate TLS at the gateway or load balancer and redirect or refuse plain HTTP. Otherwise tokens can be stolen in transit.
2. **Authenticate with tokens (OAuth2 / OIDC, usually JWT).** The client sends `Authorization: Bearer <token>`. The API validates the signature, issuer, audience and expiry. Keep tokens short-lived, because a stolen token is then useful only briefly.
3. **Authorize at two levels.** First roles and scopes, such as only ADMIN on `/admin/**`. Then ownership: load the record and verify it belongs to the caller's id from the token. Never trust an id sent by the client alone.
   ```java
   @PreAuthorize("@accountAccess.isOwner(#id, authentication)")
   ```
4. **Validate input.** Check types, lengths and ranges (Bean Validation), and use parameterized queries. Reject bad input with 400 before it reaches business logic.
5. **Rate limit** per client or token, ideally at the gateway, and return 429 with `Retry-After`. This slows credential stuffing and abuse.
6. **Restrict CORS** to the exact origins you own, never `*` together with credentials. This limits what other websites can do from a user's browser.
7. **Return safe errors.** Use a stable format (RFC 9457 problem details) with an error code and correlation id. Log the detail on the server and never expose stack traces. Return 401 for unauthenticated and 403 for forbidden. Use 404 where revealing that a record exists would itself leak information.

**Trade-offs and what can go wrong**
- JWTs cannot easily be revoked before expiry. Use short lifetimes plus refresh tokens, or a deny-list for high-risk cases.
- Skipping `aud`/`iss` or signature algorithm checks lets forged or foreign tokens through.
- Putting sensitive data in a JWT is risky, because it is only signed, not encrypted.
- Ownership checks add a lookup per request, and forgetting them on one endpoint is the common bug. Centralize them.
- Rate limits that are too tight block legitimate users behind one shared IP.
- CORS is not authentication. `curl` ignores it.

**How I'd monitor it**
- Alert on spikes in 401, 403 and 429 per client or IP.
- Search logs for one user requesting many different resource ids.
- Track token validation failures by reason (expired, bad signature, wrong audience).
- Use correlation ids to trace a single request across services.
- Run dependency scanning and periodic penetration tests that include IDOR cases.

**Follow-ups to expect**
- *JWT vs OAuth2: which do you pick?* -> They are not alternatives. OAuth2 is the flow for getting tokens and JWT is a common token format.
- *401 vs 403?* -> 401 means "I don't know who you are" (missing or invalid token). 403 means "I know who you are, but you may not do this."
- *Where do you store tokens in a browser app?* -> Prefer short-lived tokens, and use HttpOnly, Secure cookies or a backend-for-frontend, so JavaScript cannot read them and XSS cannot steal them.

**60-second answer**
I secure an API in layers. First, HTTPS everywhere so traffic cannot be read or altered. Second, authenticate with short-lived OAuth2 access tokens, often JWTs, validating signature, issuer, audience and expiry. Third, authorize twice: roles for what a user may do, and an ownership check so a customer can only touch their own accounts, because role checks alone allow ID-swapping attacks. I also validate all input, rate limit to stop brute force and scraping, and restrict CORS to our own origins, remembering CORS only protects browsers. Finally, errors are safe and consistent, with a correlation id and no stack traces. I monitor spikes in 401, 403 and 429 responses and unusual patterns of resource access.
