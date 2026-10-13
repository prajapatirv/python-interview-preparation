# REST API design with Spring MVC: methods, status codes, idempotency, caching, versioning

> **Runnable:** [`01_rest_api_status_codes_etag_idempotency.java`](../examples/08_rest_api/01_rest_api_status_codes_etag_idempotency.java)
> **Crib sheet:** [`topics/07-rest-api-design.md`](../topics/07-rest-api-design.md) · **Guide:** Q39–Q46, Q32

## What interviewers are actually probing

REST questions reveal whether you design APIs or merely write controllers. They ask for **status code precision** (400 vs 404 vs 409 vs 422),
**idempotency** (what happens when the client retries a POST?), **pagination**, **versioning**, **concurrency control** (ETag/If-Match), and
**error format**. A senior answer is always about *failure and retries*, not the happy path.

## Must-know points

- Resources are nouns; the method carries the verb. Plural collections: `/orders`, `/orders/{id}`.
- **Safe**: GET, HEAD, OPTIONS. **Idempotent**: GET, PUT, DELETE (+ safe ones). **POST** and **PATCH** are not idempotent by definition.
- Status classes: 2xx success, 3xx redirect/not modified, 4xx the client is wrong (don't retry unchanged), 5xx the server is wrong (retry may help).
- Use `Location` on 201; `ETag`/`If-None-Match` for conditional GET (304); `If-Match` for optimistic concurrency (412); `Idempotency-Key` for safe POST retries.
- Errors as **`application/problem+json`** (RFC 7807, `ProblemDetail` in Spring 6).
- Paginate every collection; cap page size; prefer **keyset (cursor)** pagination for large/changing data.

## Interview questions and full answers

### Q1. What is REST, and what makes an API "RESTful" in practice?

An architectural style: **client–server, stateless, cacheable, uniform interface, layered**. In practice: resource-oriented URLs, standard HTTP semantics (methods, status codes, headers), representations (JSON), no server-side session state,
and cacheability through headers. HATEOAS (hypermedia links) is the part most teams skip; say that honestly and explain what you do instead (documented contracts, OpenAPI).

### Q2. Which methods are safe and idempotent, and why does it matter?

| Method | Safe | Idempotent | Typical use |
|---|---|---|---|
| GET / HEAD | yes | yes | read |
| PUT | no | **yes** | replace a resource entirely |
| DELETE | no | **yes** | remove (second call still ends in "gone") |
| POST | no | **no** | create / actions |
| PATCH | no | not guaranteed | partial update |

Idempotency matters because networks fail and clients/gateways **retry**; only idempotent operations may be retried blindly.

### Q3. How do you make a POST safe to retry?

Client sends an **`Idempotency-Key`** header (UUID). The server stores `key → (request hash, response)` in a table with a unique constraint **in the same transaction** as the side effect; a repeat returns the stored response (example 08 section 5 returns the same `Location` and an `Idempotent-Replay` header).
Return `409`/`422` if the same key arrives with a different payload. Expire keys (24–48 h). The alternative is a natural idempotent design: client-generated resource id and `PUT /orders/{id}`.

### Q4. 400 vs 401 vs 403 vs 404 vs 409 vs 412 vs 422 vs 429: which and when?

- **400** malformed request (unparseable JSON, wrong type). 
- **422** syntactically fine but fails business/validation rules (many teams also use 400; be consistent and document it).
- **401** not authenticated / bad credentials. **403** authenticated but not allowed (don't leak existence: sometimes 404).
- **404** no such resource. **405** method not allowed (+ `Allow` header). **406/415** media type problems.
- **409** conflict with current state (duplicate, state-machine violation). **412** precondition failed (`If-Match` mismatch). **428** precondition required.
- **429** rate limited (+ `Retry-After`). **5xx**: 500 unexpected, 502/504 upstream, 503 overloaded/unavailable.

### Q5. How would you design `POST /orders`?

Request: `Content-Type: application/json`, body validated (`@Valid`), `Idempotency-Key`. Response: **201 Created**, `Location: /orders/{id}`, body = created representation (or minimal), `ETag`.
If processing is asynchronous: **202 Accepted** with a status resource (`/orders/{id}/status`). Errors: 400/422 with `ProblemDetail`, 409 on duplicates, 401/403, 429. Document in OpenAPI with examples.
Don't do work in the controller: validate → call an application service → map to DTO.

### Q6. PUT vs PATCH?

`PUT` replaces the **entire** representation and is idempotent. `PATCH` applies a partial change; use JSON Merge Patch (RFC 7396) for simple cases or JSON Patch (RFC 6902) for operations. PATCH is only idempotent if designed so (`set status = SHIPPED` yes; `increment` no).
Avoid "PUT with missing fields means keep" — that is a PATCH.

### Q7. How do you prevent lost updates in a REST API?

**Optimistic concurrency with ETags**: GET returns `ETag: "v7"`; the client sends `If-Match: "v7"` on PUT; the server compares to the current version (`@Version` column) and returns **412** if it changed, **428** if the header is missing (example 08 section 4).
This maps one-to-one onto JPA `@Version`. Pessimistic locking over HTTP is almost never right.

### Q8. Pagination, sorting and filtering — what is your approach?

`GET /orders?status=PAID&sort=createdAt,desc&page=0&size=20`. Spring Data gives `Pageable`/`Page<T>`. Cap `size`, whitelist sortable fields, return total/next links.
**Offset** pagination (`LIMIT 20 OFFSET 100000`) gets slower with depth and skips/duplicates rows when data changes. **Keyset/cursor** (`WHERE (created_at, id) < (?, ?) ORDER BY ... LIMIT 20` and an opaque `next` token) is stable and index-friendly. Prefer cursor for feeds and exports.

### Q9. How do you version an API without breaking clients?

Prefer **additive, backward-compatible** change (new optional fields, new endpoints; clients ignore unknown fields — Jackson `FAIL_ON_UNKNOWN_PROPERTIES=false`). When you must break: URI (`/v2/orders`), header (`Accept: application/vnd.company.v2+json`) or Spring 7's built-in API versioning.
Run old and new versions side by side, publish a **deprecation policy** (`Deprecation`/`Sunset` headers), monitor who still calls v1, and use **consumer-driven contract tests** to know what breaks.

### Q10. How do you secure a REST API?

TLS everywhere; authenticate with OAuth2/OIDC bearer tokens (JWT validated by the resource server: signature, `iss`, `aud`, `exp`); authorise per endpoint/method/resource (`@PreAuthorize`);
validate input; rate limit and throttle; avoid exposing internal ids and stack traces; CORS only for known origins; secrets out of code; audit sensitive actions; protect against mass assignment (use DTOs, not entities). OWASP API Top 10 is the checklist.

### Q11. How do you make REST calls between services reliable?

Timeouts (connect + read) on every client; retries only for idempotent calls with exponential backoff + jitter; circuit breaker and bulkhead; propagate correlation/trace headers; idempotency keys for POST; bounded connection pools; deadlines that shrink down the call chain.
In Spring: `RestClient`/`WebClient` with Resilience4j, or Spring Cloud OpenFeign with a resilience wrapper (chapter 11).

### Q12. REST vs gRPC vs GraphQL vs messaging?

REST/JSON: universal, cacheable, human friendly — public and partner APIs. gRPC: binary, schema-first, streaming, low latency — internal service-to-service. GraphQL: client-driven shape, aggregation for UIs, but caching/authorisation/N+1 need care.
Messaging (Kafka): asynchronous, decoupled in time, replayable — events and workflows. Choose per interaction, not per company.

### Q13. How do you document and contract-test an API?

OpenAPI 3 (springdoc-openapi generates from code, or design-first and generate stubs). Contract tests (Spring Cloud Contract/Pact) verify provider and consumer against a shared contract in CI; combine with schema-compatibility checks so a PR cannot silently break a field.

## A worked example

Run [`01_rest_api_status_codes_etag_idempotency.java`](../examples/08_rest_api/01_rest_api_status_codes_etag_idempotency.java). It starts a real HTTP server and drives it like `curl`:
read sections 2–5 in order and be able to say, for each line, *why that status code and header*. Then map each behaviour to Spring MVC: `ResponseEntity.created(uri)`, `@RestControllerAdvice` + `ProblemDetail`,
`ResponseEntity.ok().eTag(...)`/`WebRequest.checkNotModified`, `@Version`, and a `OncePerRequestFilter` for idempotency keys.

## Hands-on drills

1. Add `PATCH /orders/{id}` with JSON Merge Patch and decide its idempotency story.
2. Implement cursor pagination (`?after=<id>`) and show the problem with offset pagination under concurrent inserts.
3. Add rate limiting with a token bucket and return `429` + `Retry-After`.
4. Write the OpenAPI snippet for the create-order endpoint with error responses.
5. Convert the plain handler into a Spring `@RestController` + `@RestControllerAdvice` and list which lines disappear.

## The 60-second spoken answer

"I design resources as nouns with correct HTTP semantics: GET, PUT and DELETE are idempotent, POST isn't, so I add an idempotency key for
anything a client might retry. I use precise status codes with `application/problem+json`, `Location` on 201, ETags with `If-Match` to stop lost
updates, cursor pagination for large collections, and backward-compatible additive changes with explicit deprecation when I must break
a contract. Every outbound call has timeouts, bounded retries and a circuit breaker."
