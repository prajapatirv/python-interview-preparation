---
id: rest-api
title: REST APIs & third-party integration
order: 2
summary: API design, error contracts, idempotency, and calling flaky third-party APIs safely.
crib: java/java-interview-prep/topics/07-rest-api-design.md
docs: java/java-interview-prep/deep_dive/08_rest_api.md, java/java-interview-prep/company-chase-travel/brush-up/01-spring-boot-rest-api.md
examples: java/java-interview-prep/examples/08_rest_api
keywords: rest, api, http, endpoint, status code, put, patch, post, get, idempotent, idempotency, versioning, pagination, third-party, third party, resttemplate, webclient, restclient, feign, timeout, circuit breaker, bulkhead, fallback, retry, rate limit, 429, problem details, openapi, swagger, webhook, cors, cross-origin
---
Skill focus for REST APIs & third-party integration answers:
- Treat every remote call as a failure point: timeouts (connect/read/pool-acquire), bounded retries with jittered backoff, circuit breaker, bulkhead, fallback.
- "A proper response" is a contract decision: stable status codes, RFC 9457 problem details, stable error codes, correlation id; never leak vendor errors.
- Idempotency: retries of POSTs with side effects need idempotency keys; a timeout means UNKNOWN, not failed.
- Spring specifics: RestClient / WebClient / @HttpExchange, Resilience4j, @RestControllerAdvice, ProblemDetail.
- Async request-reply (202 + status URL, webhooks verified with HMAC) for slow operations.
