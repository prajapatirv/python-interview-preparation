---
id: reported-api-design-patterns
title: Reported rounds, API design: the 12 patterns as one design answer, consistent errors, preventing lost updates
stack: java
skill: rest-api
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`). It turns a popular
"12 API design patterns" reference card into interview answers. Each pattern has a deep answer elsewhere in the repo,
and Q1 links them, so this bank adds what was missing: how they fit together, and the two topics with gaps.

### Q1 [senior] Your API works on the happy path. Walk through the patterns you add to make it production-ready.
tags: api-design, idempotency, pagination, versioning, rate-limiting, circuit-breaker, webhooks, async-request-reply, api-gateway, reported-rounds

**Start here: the concepts**
- A pattern is a known answer to a known failure. Start from the failure, not the name.

**The live scenario (functional requirement)**
*FR: "A payments API for partners: 3,000 merchants, mobile retries on bad networks, long-running settlement reports, and event notifications back to merchants."*

**What the interviewer is really checking**
Whether you can select patterns from requirements, in a sensible order, rather than recite a list.

**How I answer it** (120-second answer, point by point)
I group them by the question they answer:

| Question | Pattern | The failure it prevents | Mechanism | Deep answer |
|---|---|---|---|---|
| Can clients predict it? | **1. RESTful resources** | Inconsistent endpoints | Nouns for resources, HTTP methods for verbs: `PATCH /users/42` | Bank 23 Q2 |
| Can it change safely? | **2. Versioning** | Sudden client breakage | `/v1` and `/v2` coexist, with a sunset date | Bank 76 Q4, 72 Q11 |
| Can it handle big data? | **3. Pagination** | Huge responses and slow queries | Next-cursor over offset for large or changing data | Bank 76 Q5 |
| Can clients handle failures? | **4. Consistent errors** | Five error shapes to parse | One format: `type`, `title`, `status`, `detail` | Q2 below |
| Is a retry safe? | **5. Idempotency keys** | Paying twice on a retry | Same key, same stored result | Bank 23 Q4, 91 Q4 |
| Can it avoid wasted work? | **6. Conditional requests** | Re-sending unchanged data; lost updates | `ETag` with `If-None-Match` gives `304`; `If-Match` gives `412` | Q3 below, bank 76 Q9 |
| Is capacity protected? | **7. Rate limiting** | One client starving the rest | `429` with `Retry-After` | Bank 98 Q13, 76 Q8 |
| What about slow work? | **8. Async request-reply** | Timeouts on long jobs | `202` with a job URL, then poll | Bank 76 Q10 |
| Is there one front door? | **9. API gateway** | Auth and routing copied everywhere | Central auth, routing, limits | Bank 91 Q8 |
| Can we notify clients? | **10. Webhooks** | Clients polling forever | Signed POST; verify, deduplicate, retry failures | Bank 23 Q17 |
| What if a dependency is sick? | **11. Circuit breaker** | Cascading failure | `OPEN` rejects immediately | Bank 61 Q1, 05 Q5 |
| Do clients need many calls? | **12. API aggregation** | Chatty mobile clients | One call fans out; partial results allowed | Bank 05 Q13, 81 Q2 |

For this FR, the order I'd build in is:
1. **Resources, errors, versioning first.** These are expensive to change later, because clients depend on them.
2. **Idempotency keys on every money-moving POST.** Mobile retries make this non-negotiable.
3. **Auth and rate limits at the gateway**, per merchant.
4. **Cursor pagination** on transactions.
5. **Async request-reply** for settlement reports, and **webhooks** to tell merchants when they're ready.
6. **Timeouts and a breaker** on the bank connection.
7. **ETags** only where the read volume or lost-update risk justifies them.

**Trade-offs and what can go wrong**
- Don't add all twelve to an internal CRUD service. Each has a cost in code and in operations.
- Webhooks and retries mean **at-least-once** delivery, so consumers must deduplicate.
- A gateway is a shared dependency, so keep business logic out of it.

**How I'd monitor it**
Error rate by code and client, p99 per endpoint, 429 count per client, idempotency-replay count, webhook failure and retry counts, breaker state changes.

**Follow-ups to expect**
- *Which one matters most for payments?* -> Idempotency. Everything else degrades service; this one loses money.
- *Which is hardest to retrofit?* -> Versioning and the error format, since clients already rely on them.

**60-second answer**
"I start from failures. Clients need predictability, so resources, a single error format and versioning come first, because they're expensive to change later. Retries are the next risk, so every money-moving POST takes an idempotency key. Capacity comes next: rate limits per client at a gateway, and cursor pagination on large lists. Slow work becomes 202 with a job URL, with signed webhooks for completion. Unhealthy dependencies get timeouts and a circuit breaker. Then I add ETags and aggregation only where the numbers justify them, not all twelve on every service."

### Q2 [mid] How do you give clients one consistent error format?
tags: error-handling, problem-details, rfc9457, problemdetail, correlation-id, status-codes, api-design, reported-rounds

**Start here: the concepts**
- **RFC 9457** (Problem Details, which replaced RFC 7807) is the standard JSON error format, with the media type `application/problem+json`.
- Its fields: `type`, `title`, `status`, `detail`, `instance`, plus your own extensions.

**The live scenario (functional requirement)**
*FR: "Partners must decide automatically whether to retry, fix the input or call support."* If they have to match on English error messages, every reworded message breaks them.

**What the interviewer is really checking**
That the format is designed for **code to act on**, including a stable error code and a clear retry signal.

**How I answer it** (120-second answer, point by point)

```json
{
  "type": "https://api.acme.com/errors/insufficient-funds",
  "title": "Insufficient funds",
  "status": 422,
  "detail": "Account balance is lower than the payment amount.",
  "instance": "/payments/8841",
  "code": "PAYMENT_INSUFFICIENT_FUNDS",
  "traceId": "4bf92f3577b34da6"
}
```

1. **Correct status class:** 4xx means the client should change something and not blindly retry. 5xx means retrying may help.
2. **Stable `code` or `type`:** clients branch on it, and `detail` may be reworded for humans.
3. **Validation:** return every field error at once in an `errors` array, so a client doesn't fix one per round trip.
4. **`traceId`:** support finds the exact request in logs. Include this in errors from the gateway too.
5. **Spring:** `ProblemDetail` from `@RestControllerAdvice`, and `spring.mvc.problemdetails.enabled=true` covers Spring's own exceptions (bank 98 Q12).
6. **Filters too:** Spring Security errors occur before controllers, so give the `AuthenticationEntryPoint` and `AccessDeniedHandler` the same format.

**Trade-offs and what can go wrong**
- Never put stack traces, SQL or internal hostnames in `detail`.
- A `200 OK` with an error in the body breaks monitoring, retries and caching.
- `401` vs `403`: not authenticated vs not allowed. `404` may deliberately hide existence from an unauthorised caller.

**Follow-ups to expect**
- *400 vs 422?* -> 400 is malformed, and 422 is well-formed but violates a rule. Whichever you pick, stay consistent.
- *How does the client know when to retry?* -> `Retry-After` on 429 and 503.

**60-second answer**
"I use RFC 9457 Problem Details everywhere: type, title, status, detail, plus my own stable error code and a trace id. Clients branch on the code, not the text, so wording can change freely. The status class tells them whether to retry. Validation returns all field errors at once. In Spring, that's ProblemDetail from one RestControllerAdvice, and I also make sure the security filters return the same shape, because they run before the controller. I never leak stack traces."

### Q3 [senior] Explain optimistic locking, ETags and conditional HTTP requests. How do they prevent lost updates?
tags: optimistic-locking, etag, if-match, 412, 428, version, lost-update, conditional-requests, deloitte, reported-rounds

**Start here: the concepts**
- **Lost update:** two users read version 5, both edit, and the second save overwrites the first with no warning.
- **Optimistic locking:** keep a version number and fail the write if it has changed.
- **ETag:** an HTTP validator for a representation of a resource.
- The two connect: the ETag carries the database version out to the client, and back.

**The live scenario (functional requirement)**
*FR: "Two support agents edit the same customer."* Agent A changes the phone, and agent B changes the address from the same old copy. Without protection, B's save erases A's phone change.

**What the interviewer is really checking**
That you see the *whole* flow, across HTTP and the database. A database lock alone can't cover a user who holds a form for two minutes.

**How I answer it** (120-second answer, point by point)
1. **Why not a database lock?** A pessimistic lock can't be held while a person edits, or across two separate HTTP requests.
2. **Database side:** JPA `@Version` adds `WHERE id = ? AND version = ?` to the update and increments it. Zero rows updated throws `OptimisticLockException`.
3. **End to end:**

| Step | Request | Response |
|---|---|---|
| Read | `GET /customers/7` | `200`, `ETag: "5"`, body |
| Update | `PUT /customers/7`, `If-Match: "5"` | `200`, `ETag: "6"` |
| Stale update | `PUT /customers/7`, `If-Match: "5"` | `412 Precondition Failed` |
| No header sent | `PUT /customers/7` | `428 Precondition Required` |

4. **Server logic:** compare `If-Match` with the current version. Keep the `@Version` check too, as a safety net for two requests arriving together, since the header check and the save aren't atomic.
5. **Client on 412:** re-read, show the conflict or merge, and retry.
6. **Caching is the other half:** `GET` with `If-None-Match: "5"` returns `304 Not Modified` with no body, saving bandwidth.

**Trade-offs and what can go wrong**
- Spring's `ShallowEtagHeaderFilter` hashes the response, which saves bandwidth, but it doesn't save server work and it doesn't prevent lost updates by itself.
- Optimistic locking is poor under heavy contention, since many writers retry. A hot row like a seat counter suits an atomic `UPDATE ... SET x = x - 1 WHERE x > 0`.
- With a `PATCH` that touches separate fields, you may choose to merge rather than reject.
- `@Version` is checked at flush. Copying a stale version from a DTO onto a freshly loaded entity silently loses the check, so compare explicitly.

**Follow-ups to expect**
- *Weak ETags?* -> `W/"5"` means semantically equal, and is fine for caching. `If-Match` needs strong comparison.
- *How do you test it?* -> Two concurrent updates in an integration test, asserting that one succeeds and one gets 412 or 409.

**60-second answer**
"A lost update is when two people read the same version and the second save silently overwrites the first. A database lock can't help while someone holds a form open, so I use optimistic locking: a @Version column, and the update only applies if the version matches. ETags carry that version over HTTP. GET returns ETag 5, and PUT sends If-Match 5. If it changed, the server returns 412, and the client re-reads. No header gets 428. I keep the @Version check as well, since it covers two requests arriving at once. And the same ETag gives 304 on reads, saving bandwidth."
