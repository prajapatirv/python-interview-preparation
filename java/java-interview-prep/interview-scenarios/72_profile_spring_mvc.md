---
id: profile-java-genai-spring-mvc
title: Java + GenAI profile (3/9): Spring MVC, 15 functional-requirement questions
stack: java
skill: spring-boot
---
Part of the **Java/J2EE + Gen AI** profile pack (see `../profile-java-genai/README.md`).
MVC here means **Spring Web MVC** (servlet stack): DispatcherServlet, controllers, views, validation, error handling.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] Walk through what happens inside Spring MVC when a request arrives.
tags: dispatcherservlet, handlermapping, handleradapter, viewresolver, request-lifecycle, spring-mvc, profile-java-genai

**Start here: the concepts**
- **Front controller:** one `DispatcherServlet` receives every request and delegates.
- **HandlerMapping:** finds the controller method for the URL and HTTP method.
- **HandlerAdapter:** invokes it, resolving arguments (`@PathVariable`, `@RequestBody`) and handling return values.
- **HttpMessageConverter:** JSON <-> objects (Jackson). **ViewResolver:** view name -> template, for server-rendered pages.

**The live scenario (functional requirement)**
*FR: "GET /api/bookings/{id} returns booking JSON; GET /bookings/{id} shows a booking HTML page."* A junior asks why a filter sees the request but the interceptor doesn't fire for a 404.

**What the interviewer is really checking**
That you can trace the pipeline and know where filters, interceptors, advice and converters sit.

**How I answer it**
1. **Servlet filters** run first (security, correlation id, CORS), outside Spring MVC.
2. `DispatcherServlet` asks the **HandlerMappings** (`RequestMappingHandlerMapping` for `@RequestMapping`) for a handler plus its **interceptor chain**.
3. Interceptors' `preHandle` run; then the **HandlerAdapter** resolves arguments via `HandlerMethodArgumentResolver`s, runs validation, and invokes the method.
4. Return value: `@ResponseBody`/`@RestController` -> an `HttpMessageConverter` picked by content negotiation writes JSON. A view name -> `ViewResolver` -> Thymeleaf renders HTML with the `Model`.
5. Exceptions go to `HandlerExceptionResolver`s, which include `@ExceptionHandler`/`@ControllerAdvice`.
6. `postHandle`/`afterCompletion` run; filters unwind.
7. A 404 with no matching handler never reaches handler interceptors, which answers the junior's question.

**Trade-offs and what can go wrong**
- Business logic in filters/interceptors is hard to test and see; keep them for cross-cutting concerns.
- Heavy work in `preHandle` adds latency to every request.

**How I'd monitor it**
`http_server_requests_seconds` by URI template, status and exception tag.

**Follow-ups to expect**
- *Who creates DispatcherServlet in Boot?* -> `DispatcherServletAutoConfiguration`, mapped to `/`.
- *Where does `@Valid` run?* -> During argument resolution, before your method.
- *How is JSON vs XML chosen?* -> Content negotiation on the `Accept` header against available converters.

**60-second answer**
"Filters run first, outside MVC. Then the DispatcherServlet, the front controller, asks the handler mappings which controller method matches, along with its interceptors. Interceptors' preHandle run, the handler adapter resolves arguments, runs validation and calls the method. A `@RestController` return goes through a message converter chosen by content negotiation, usually Jackson; a view name goes to a view resolver like Thymeleaf. Exceptions route to `@ControllerAdvice`. A request with no handler never reaches the interceptors, only the filters."

### Q2 [mid] @Controller vs @RestController, and how content negotiation picks the format.
tags: restcontroller, controller, responsebody, content-negotiation, message-converters, responseentity, profile-java-genai

**Start here: the concepts**
- **`@Controller`:** methods return view names by default.
- **`@RestController`** = `@Controller` + `@ResponseBody`: return values are written to the body.
- **`ResponseEntity`:** full control of status, headers and body.
- **Content negotiation:** `Accept` header -> matching `HttpMessageConverter`.

**The live scenario (functional requirement)**
*FR: "The reports endpoint must return JSON for the web app, CSV for finance downloads, and 201 with a Location header when a report is requested."*

**What the interviewer is really checking**
Practical control over responses, not just annotation definitions.

**How I answer it**
1. `@RestController` for the API; `@Controller` only for server-rendered pages.
2. Creation returns `ResponseEntity.created(URI.create("/reports/" + id)).body(dto)`: 201 + Location.
3. Multiple formats: `@GetMapping(value = "/reports/{id}", produces = {APPLICATION_JSON_VALUE, "text/csv"})` and register a custom `HttpMessageConverter` for CSV, so the method returns one DTO and the client's `Accept` decides.
4. Large CSV exports stream with `StreamingResponseBody` instead of building a big string.
5. Unsupported `Accept` -> 406; unsupported request `Content-Type` -> 415, handled by Spring.

**Trade-offs and what can go wrong**
- Returning JPA entities directly leaks fields and triggers lazy loading; return DTOs.
- Format via URL suffix (`.csv`) is disabled by default for security; prefer `Accept`.

**How I'd monitor it**
Status-code distribution, 406/415 counts (client misuse), export duration.

**Follow-ups to expect**
- *How do you set a header only sometimes?* -> `ResponseEntity` or `HttpServletResponse`.
- *Default JSON library?* -> Jackson (Jackson 3 in Boot 4).
- *XML support?* -> Add `jackson-dataformat-xml`; the converter registers automatically.

**60-second answer**
"`@RestController` is `@Controller` plus `@ResponseBody`, so return values become the body; plain `@Controller` returns view names for server-side pages. When I need status or headers, like 201 with Location after creating a report, I return a ResponseEntity. For JSON and CSV from one endpoint, I declare both in `produces`, register a CSV message converter and let the Accept header choose; Spring answers 406 or 415 when it can't. Big exports stream with StreamingResponseBody."

### Q3 [mid] Validate a complex form or request body: Bean Validation, groups and custom constraints.
tags: validation, bean-validation, valid, validated, custom-constraint, jakarta-validation, profile-java-genai

**Start here: the concepts**
- **Jakarta Bean Validation:** `@NotBlank`, `@Size`, `@Email`, `@Past`, `@Positive` on fields.
- **`@Valid`** cascades to nested objects; **`@Validated`** supports **groups** and method validation.
- **Custom constraint:** annotation + `ConstraintValidator`.

**The live scenario (functional requirement)**
*FR: "A loan application: name and income required, age at least 18, end date after start date, PAN in the right format, and for 'self-employed' a GST number is mandatory. Show all errors at once."*

**What the interviewer is really checking**
Declarative validation, cross-field rules, and a clean error response.

**How I answer it**
1. Field rules on the DTO record: `@NotBlank String name`, `@Positive BigDecimal income`, `@Pattern(regexp = "[A-Z]{5}[0-9]{4}[A-Z]") String pan`.
2. `@Valid @RequestBody LoanRequest req` in the controller; failures throw `MethodArgumentNotValidException` with **all** field errors.
3. **Cross-field:** a class-level custom constraint `@ValidDateRange` with a `ConstraintValidator<ValidDateRange, LoanRequest>`.
4. **Conditional (self-employed needs GST):** a class-level validator, or groups with `@Validated(SelfEmployed.class)`; I prefer one class-level validator because it reads clearly.
5. Path and query params: `@Validated` on the controller enables `@Min` on `@RequestParam`; Spring 6.1+ also validates method parameters natively.
6. Map errors to one Problem Details response with a list of `{field, message}`.
7. **Business rules** that need the DB (duplicate application) live in the service, not in annotations.

**Trade-offs and what can go wrong**
- Validators that call databases slow every request and are hard to test.
- Client-side validation is UX only; the server validates again.
- Error messages should be stable codes for the UI, with i18n via `messages.properties`.

**How I'd monitor it**
400 counts by field/code: a spike in one field often means a frontend bug.

**Follow-ups to expect**
- *`@Valid` vs `@Validated`?* -> `@Valid` is standard and cascades; `@Validated` is Spring's and supports groups.
- *Validating a List body?* -> Annotate the elements (`List<@Valid Item>`).
- *Where's the validator from?* -> Hibernate Validator via `spring-boot-starter-validation`.

**60-second answer**
"Field rules go on the DTO with Bean Validation annotations, and `@Valid` on the request body collects every error at once into a MethodArgumentNotValidException. Cross-field rules, like end date after start date or GST required for self-employed applicants, become class-level custom constraints. Rules that need the database live in the service. A `@ControllerAdvice` turns the errors into one Problem Details response listing field and message codes, and I watch 400s per field to catch frontend bugs."

### Q4 [senior] Design global error handling with @RestControllerAdvice and Problem Details.
tags: error-handling, controlleradvice, problemdetail, rfc-9457, exception-handler, api-design, profile-java-genai

**Start here: the concepts**
- **`@RestControllerAdvice` + `@ExceptionHandler`:** one place mapping exceptions to responses.
- **Problem Details (RFC 9457, replacing RFC 7807):** a standard JSON error with `type`, `title`, `status`, `detail`, `instance`, plus extensions. Spring's `ProblemDetail` and `ErrorResponse` implement it.
- `spring.mvc.problemdetails.enabled=true` makes Spring's own errors use it.

**The live scenario (functional requirement)**
*FR: "Every API in the platform must return errors in one format, with an error code the mobile app can switch on and a trace id support can search."* Today, five services return five shapes, some with stack traces.

**What the interviewer is really checking**
Consistency, security (no leaks) and debuggability.

**How I answer it**
1. Domain exceptions carry an error code (`BOOKING_NOT_FOUND`, `FARE_EXPIRED`).
2. One advice class, shipped in the company starter:

```java
@ExceptionHandler(DomainException.class)
ProblemDetail handle(DomainException ex) {
    var pd = ProblemDetail.forStatusAndDetail(ex.status(), ex.getMessage());
    pd.setProperty("code", ex.code()); pd.setProperty("traceId", currentTraceId());
    return pd;
}
```

3. Validation errors -> 400 with a list of field errors; extend `ResponseEntityExceptionHandler` so Spring's built-in exceptions (405, 415, missing params) get the same format.
4. A catch-all `Exception` handler -> 500 with a generic message and the trace id; the stack trace goes only to logs.
5. Document the error schema in OpenAPI so clients code against it.

**Trade-offs and what can go wrong**
- Leaking exception messages from libraries (SQL, class names) is an information-disclosure risk.
- Using 200 with `{"error": ...}` breaks HTTP semantics and monitoring.
- Too many fine-grained codes become unmaintainable; group them.

**How I'd monitor it**
Error codes as a metric tag (bounded set), 5xx alerts, trace id linking client reports to logs.

**Follow-ups to expect**
- *Advice ordering with several advices?* -> `@Order` on the advice classes.
- *Errors thrown in filters?* -> They bypass controller advice; handle in the filter or via the error controller.
- *404 for missing vs 403 for forbidden?* -> Sometimes return 404 for forbidden resources to avoid revealing existence.

**60-second answer**
"One `@RestControllerAdvice`, shipped in a shared starter, maps domain exceptions to RFC 9457 Problem Details with a stable error code and the trace id. I extend ResponseEntityExceptionHandler so Spring's own 405s and 415s use the same format, validation errors become a 400 with field details, and a catch-all returns a generic 500 while the stack trace only goes to logs. The error schema is in OpenAPI, so the mobile app switches on codes, and support searches by trace id."

### Q5 [mid] Filters vs interceptors vs AOP: where do you put correlation ids, auth and audit?
tags: filter, handlerinterceptor, aop, cross-cutting, correlation-id, mdc, profile-java-genai

**Start here: the concepts**
- **Servlet Filter:** around the whole request, before Spring MVC; sees raw request/response.
- **HandlerInterceptor:** around controller handling; knows which handler method was chosen.
- **AOP aspect:** around Spring bean method calls anywhere (services too).

**The live scenario (functional requirement)**
*FR: "Every request gets a correlation id in logs and responses; requests are authenticated; every call to an AI-powered endpoint is audited with user, endpoint and token usage."*

**What the interviewer is really checking**
Choosing the right layer for each cross-cutting concern.

**How I answer it**
1. **Correlation id -> Filter** (`OncePerRequestFilter`): read `X-Correlation-Id` or create one, put in MDC, add to the response, clear MDC in `finally`. It must cover everything, including 404s and security failures. (With OpenTelemetry the trace id plays this role.)
2. **Authentication -> Spring Security filter chain**, which is filters by design.
3. **"Which handler" logic -> Interceptor:** e.g. a custom `@AiFeature` annotation read via `HandlerMethod` to enforce a feature flag per endpoint.
4. **Audit of AI usage -> AOP** around the service method `@Audited`, since token usage is known in the service, and the same service may be called from Kafka listeners too.
5. Keep each one small and ordered (`@Order`, `FilterRegistrationBean`).

**Trade-offs and what can go wrong**
- MDC not cleared leaks ids between requests on pooled threads.
- AOP doesn't intercept self-invocation or private methods.
- Reading the request body in a filter consumes the stream; wrap with `ContentCachingRequestWrapper`.

**How I'd monitor it**
Percentage of log lines with a correlation id; audit-event counts vs request counts.

**Follow-ups to expect**
- *Async requests and MDC?* -> Propagate context to other threads with context-propagation or a `TaskDecorator`.
- *Interceptor for timing?* -> Use Micrometer's built-in HTTP metrics instead.
- *Filter in Boot?* -> Any `Filter` bean is registered automatically.

**60-second answer**
"I choose by scope. The correlation id is a filter, because it must cover every request, even 404s and auth failures. It goes into MDC and the response header and is cleared in finally. Authentication is Spring Security's filter chain. Anything that depends on which controller method matched, like a per-endpoint AI feature flag, is an interceptor. Auditing AI usage is an aspect on the service method, because token counts live there and Kafka listeners call it too."

### Q6 [senior] Accept large file uploads (PDFs for a RAG system) without running out of memory.
tags: multipart, file-upload, streaming, requestpart, large-files, spring-mvc, profile-java-genai

**Start here: the concepts**
- **Multipart:** `multipart/form-data`, bound with `@RequestParam MultipartFile` or `@RequestPart`.
- **Limits:** `spring.servlet.multipart.max-file-size`, `max-request-size`, `file-size-threshold` (above it, parts go to disk temp files).
- **Direct-to-storage uploads:** the client uploads to S3/Blob storage with a pre-signed URL.

**The live scenario (functional requirement)**
*FR: "Users upload policy PDFs up to 200 MB for the knowledge base; upload must return quickly while indexing happens in the background."*

**What the interviewer is really checking**
Memory-safe handling, security checks, and async processing.

**How I answer it**
1. Best: **pre-signed URL** flow. `POST /documents` returns an upload URL; the browser uploads straight to object storage; storage emits an event; the API never streams 200 MB.
2. If uploads must go through the API: set limits (`max-file-size=200MB`), keep `file-size-threshold` low so parts spill to disk, and stream `file.getInputStream()` to storage, never `getBytes()`.
3. **Validate:** content type by magic bytes, not just extension; virus scan; size; allowed tenants.
4. Return **202 Accepted** with `Location: /documents/{id}/status`; publish `DocumentUploaded` to Kafka; ingestion workers parse, chunk and embed.
5. Idempotency: hash the content; a duplicate upload maps to the existing document.

**Trade-offs and what can go wrong**
- Proxies and ingress have their own body limits (nginx `client_max_body_size`) and timeouts.
- `getBytes()` on 200 MB × 20 concurrent uploads = 4 GB heap.
- Malicious PDFs (zip bombs, embedded scripts) hit the parser; sandbox it.

**How I'd monitor it**
Upload sizes and duration, failures by reason, ingestion queue lag, document status counts.

**Follow-ups to expect**
- *Resumable uploads?* -> Multipart upload in S3 or tus protocol.
- *How does the client know indexing finished?* -> Poll the status resource, SSE, or a webhook.
- *Where are temp files?* -> `spring.servlet.multipart.location`; mount a volume with enough space.

**60-second answer**
"For 200 MB PDFs I'd keep the bytes out of the API: it hands out a pre-signed URL, the browser uploads straight to object storage, and a storage event starts ingestion. If it must pass through the API, I set multipart limits, let parts spill to disk and stream to storage, never `getBytes()`. I validate by magic bytes and virus scan, return 202 with a status URL, and Kafka-driven workers parse, chunk and embed in the background."

### Q7 [mid] Build a server-rendered page with Spring MVC and Thymeleaf correctly.
tags: thymeleaf, model, viewresolver, post-redirect-get, csrf, server-side-rendering, profile-java-genai

**Start here: the concepts**
- **Model:** data for the view. **View name** -> template via the ViewResolver.
- **Post/Redirect/Get (PRG):** after a form POST, redirect so a browser refresh doesn't resubmit.
- **CSRF:** session-based forms need a CSRF token; Thymeleaf with Spring Security adds it automatically.

**The live scenario (functional requirement)**
*FR: "An internal admin screen lets ops edit prompt templates: list, edit form with validation errors, save, then show a success message."*

**What the interviewer is really checking**
That you know classic MVC: model binding, validation errors in views, PRG and flash attributes.

**How I answer it**
1. `@GetMapping("/prompts/{id}/edit")` adds `model.addAttribute("form", ...)` and returns `"prompts/edit"`.
2. `@PostMapping` with `@Valid @ModelAttribute("form") PromptForm form, BindingResult result`: if errors, return the same view (fields show `th:errors`).
3. On success save, `redirectAttributes.addFlashAttribute("msg", "Saved")`, and `return "redirect:/prompts"`: PRG.
4. Spring Security enables CSRF; `th:action` injects the hidden token.
5. Escape output (Thymeleaf `th:text` escapes by default; `th:utext` only for trusted HTML) to prevent XSS, especially since prompts contain user text.

**Trade-offs and what can go wrong**
- `BindingResult` must directly follow the validated parameter, or Spring throws instead of populating it.
- Returning a view after POST causes duplicate submissions on refresh.
- Server-side MVC suits internal tools; customer-facing SPAs usually use REST + React.

**How I'd monitor it**
Form error rates, admin audit log of template changes (who/when/what diff).

**Follow-ups to expect**
- *Model vs ModelAndView?* -> Same data; ModelAndView bundles view name and model.
- *Flash attributes?* -> Stored in the session for exactly one redirect.
- *Session scope for wizards?* -> `@SessionAttributes`, cleared with `SessionStatus.setComplete()`.

**60-second answer**
"GET puts a form object in the model and returns the view name; POST binds with `@Valid @ModelAttribute` plus a BindingResult right after it. On errors I return the same view and Thymeleaf shows field errors; on success I save, add a flash message and redirect, the Post/Redirect/Get pattern, so a refresh doesn't resubmit. Spring Security's CSRF token is injected by `th:action`, and `th:text` escaping prevents XSS in prompt text."

### Q8 [senior] Spring MVC or Spring WebFlux, now that virtual threads exist?
tags: webflux, spring-mvc, reactive, virtual-threads, backpressure, architecture-decision, profile-java-genai

**Start here: the concepts**
- **Spring MVC:** servlet stack, thread per request, blocking style.
- **WebFlux:** reactive stack on Netty, non-blocking, `Mono`/`Flux`, backpressure.
- **Virtual threads:** make blocking threads cheap, so MVC scales for I/O-bound concurrency.

**The live scenario (functional requirement)**
*FR: "A new AI gateway service fans out to LLM providers, streams tokens to 5,000 concurrent clients, and enforces quotas."* The team is split between MVC and WebFlux.

**What the interviewer is really checking**
A decision based on workload and team skill, not fashion.

**How I answer it**
1. **Default to MVC + virtual threads** for typical CRUD and integration services: simple blocking code, JDBC/JPA, easy debugging, now scales to thousands of concurrent waits.
2. **Choose WebFlux** when the core job is **streaming and composition with backpressure**: long-lived SSE or WebSocket connections, fan-out/fan-in of streams, a gateway (Spring Cloud Gateway is reactive). This AI gateway is that case.
3. Note MVC can stream too (`SseEmitter`, `StreamingResponseBody`), so for a modest number of streaming clients MVC is fine.
4. Don't mix: blocking calls (JDBC, legacy SDKs) inside WebFlux event-loop threads freeze it; wrap with `Schedulers.boundedElastic()` or avoid.
5. Consider team skill: reactive stack traces and operators have a learning curve.

**Trade-offs and what can go wrong**
- WebFlux with a blocking database loses most benefits (R2DBC exists but JPA doesn't).
- Virtual threads don't give backpressure; you still need explicit limits.

**How I'd monitor it**
Event-loop latency/blocked-thread detection (BlockHound in tests), concurrent connections, memory per connection.

**Follow-ups to expect**
- *Can MVC use WebClient?* -> Yes, though RestClient is the natural blocking client now.
- *What is backpressure?* -> The consumer signals how much it can take; the producer slows down.
- *Spring AI streaming?* -> `ChatClient...stream().content()` returns a `Flux<String>`, usable from both stacks.

**60-second answer**
"My default is Spring MVC with virtual threads: simple blocking code, JPA, easy debugging, and it now handles thousands of concurrent waits. I choose WebFlux when the core job is streaming with backpressure, like an AI gateway holding 5,000 token streams and fanning out to providers, the same reason Spring Cloud Gateway is reactive. The rule is never block the event loop, and I weigh the team's reactive skills, because the operators and stack traces have a real learning curve."

### Q9 [senior] Stream LLM tokens to the browser from a Spring MVC endpoint.
tags: sse, sseemitter, streaming, llm, spring-ai, server-sent-events, profile-java-genai

**Start here: the concepts**
- **Server-Sent Events (SSE):** one long HTTP response with `text/event-stream`; the server pushes events, the browser's `EventSource` (or fetch streaming) reads them.
- **SseEmitter** (MVC) or returning `Flux<ServerSentEvent<String>>` (supported in MVC too, with Reactor on the classpath).
- **Time to first token** matters more to perceived speed than total time.

**The live scenario (functional requirement)**
*FR: "The support copilot must start showing the answer within 1 second, even though a full answer takes 8 seconds; the user can press Stop."*

**What the interviewer is really checking**
Streaming mechanics end to end, plus cancellation, timeouts and proxies.

**How I answer it**
1. Spring AI gives a stream: `chatClient.prompt().user(q).stream().content()` -> `Flux<String>`.
2. Expose it as SSE:

```java
@GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
Flux<String> stream(@RequestParam String q) { return chatClient.prompt().user(q).stream().content(); }
```

   With plain MVC and no Reactor, an `SseEmitter` fed from the provider's callback works the same.
3. **Stop button:** the browser closes the connection; the Flux is cancelled, which cancels the upstream provider request, so we stop paying for tokens.
4. **Timeouts:** set an emitter/async timeout (`spring.mvc.async.request-timeout`) longer than the max generation time; send periodic comment heartbeats so proxies don't cut idle streams.
5. **Proxies:** disable buffering for the route (nginx `X-Accel-Buffering: no`), or tokens arrive in one lump at the end.
6. After completion, save the full answer and token usage for audit and feedback.

**Trade-offs and what can go wrong**
- Each open stream holds a connection; with platform threads and `SseEmitter`, use an async executor or virtual threads.
- Errors mid-stream can't change the HTTP status (already 200); send an `event: error` message.
- Guardrails on output are harder when streaming; check per chunk or buffer sentences.

**How I'd monitor it**
Time to first token, tokens/s, stream completion vs cancellation rate, concurrent streams.

**Follow-ups to expect**
- *SSE vs WebSocket?* -> SSE is one-way, simple, works over plain HTTP; WebSocket for two-way, low-latency messaging.
- *Does SSE work through load balancers?* -> Yes, with idle timeouts raised and buffering off.
- *How to stream structured output?* -> Stream text for display; parse structured JSON only after completion.

**60-second answer**
"The model streams tokens, so I stream them on: Spring AI's `stream().content()` gives a Flux, and returning it with `text/event-stream` makes it SSE, or I use SseEmitter on plain MVC. The user sees text in under a second. When they press Stop the connection closes, the Flux cancels and the provider call stops, so we stop paying. I set async timeouts, send heartbeats, disable proxy buffering, send errors as an SSE event because the status is already 200, and track time to first token."

### Q10 [senior] Tune the embedded Tomcat for throughput and protect it under overload.
tags: tomcat, thread-pool, max-connections, accept-count, timeouts, capacity, profile-java-genai

**Start here: the concepts**
- **`server.tomcat.threads.max`** (default 200): worker threads. **`max-connections`** (default 8192 for NIO): open connections. **`accept-count`** (default 100): OS backlog when all connections are taken.
- **Timeouts:** connection timeout, keep-alive; plus client timeouts on downstream calls.

**The live scenario (functional requirement)**
*FR: "The fare-search API must sustain 1,500 requests/s at p99 under 800 ms; during a flash sale it must degrade gracefully, not collapse."* Each request waits ~300 ms on supplier APIs.

**What the interviewer is really checking**
Capacity reasoning (Little's Law) and overload protection, not random property tweaking.

**How I answer it**
1. Little's Law: 1,500 × 0.3 s = 450 concurrent requests in progress. With 200 threads I'm thread-bound.
2. Options: **virtual threads** (`spring.threads.virtual.enabled=true`) so waiting is cheap; or raise `threads.max` to ~500 and verify memory and CPU; or scale out pods.
3. **Downstream limits:** HTTP client connection pool sized for 450 concurrent calls per pod; timeouts (connect 1 s, read 1.5 s).
4. **Overload:** a bulkhead/concurrency limit per supplier; load shedding returning **503 + Retry-After** fast instead of queueing until everyone times out; rate limiting at the gateway.
5. Graceful shutdown (default since Boot 3.4) so deploys don't drop in-flight requests.
6. Load-test with realistic think times and supplier latency (Gatling/k6), find the knee, set HPA targets below it.

**Trade-offs and what can go wrong**
- Huge thread pools increase memory and context switching and just move the queue.
- A big `accept-count` hides overload as latency; failing fast is kinder.
- Keep-alive must be consistent with the load balancer: the server's keep-alive timeout should be **longer** than the LB's idle timeout, so the LB closes idle connections first; otherwise the LB reuses a connection the server just closed and returns 502s.

**How I'd monitor it**
`tomcat_threads_busy`, connection counts, p99, 503 rate, supplier latency, HPA replica count.

**Follow-ups to expect**
- *Why not just increase to 2,000 threads?* -> ~1 MB stack each, scheduling overhead; virtual threads solve it better.
- *Switch to Undertow/Jetty?* -> Rarely the bottleneck; measure first.
- *What does graceful shutdown do?* -> Stops accepting new requests and waits for in-flight ones up to a timeout.

**60-second answer**
"I start from Little's Law: 1,500 requests a second at 300 ms of waiting is about 450 in flight, and Tomcat's default 200 threads can't hold that. I'd enable virtual threads, or raise the pool after checking memory, and size the HTTP client pool and timeouts to match. Then overload protection: per-supplier bulkheads and fast 503s with Retry-After instead of an ever-growing queue. Load tests find the knee, autoscaling triggers below it, and graceful shutdown protects deploys."

### Q11 [mid] Version an API with Spring Framework 7's built-in API versioning.
tags: api-versioning, spring-framework-7, spring-boot-4, deprecation, rfc-9745, profile-java-genai

**Start here: the concepts**
- **Versioning strategies:** URI path (`/v2/...`), header (`API-Version: 2`), query parameter, media type (`application/vnd.app.v2+json`).
- **Spring Framework 7** adds first-class versioning: configure a strategy once, then `@GetMapping(version = "2")`.
- Deprecation can be signalled with standard headers (RFC 9745 `Deprecation`, plus `Sunset`).

**The live scenario (functional requirement)**
*FR: "The booking response changes `price` from a number to an object with amount and currency. Mobile apps in the field can't update for 6 months."*

**What the interviewer is really checking**
Non-breaking evolution first, a clean versioning mechanism, and a deprecation plan.

**How I answer it**
1. First ask: can it be **additive**? Add `priceDetail` alongside `price`; no new version needed. Only true breaking changes get a version.
2. Configure once (Boot 4 also has `spring.mvc.apiversion.*` properties):

```java
public void configureApiVersioning(ApiVersionConfigurer c) { c.useRequestHeader("API-Version"); }
```

3. Controllers: `@GetMapping(path = "/bookings/{id}", version = "1")` and `version = "2"` on separate methods (or `"1.1+"` style baselines), both delegating to the same service with different mappers.
4. Mark v1 deprecated: Spring can add `Deprecation`/`Sunset` headers via a deprecation handler; publish the sunset date.
5. Track v1 usage per client; remove when it's near zero after the sunset date.

**Trade-offs and what can go wrong**
- Path versioning is the most visible and cache-friendly; header versioning keeps URLs stable but is less obvious. Pick one per platform.
- Versioning every small change leads to version sprawl; additive changes and tolerant readers avoid it.
- Duplicated controller code between versions; keep versions in the mapping layer.

**How I'd monitor it**
Requests per version per client app; alert on unknown version values.

**Follow-ups to expect**
- *Before Spring 7?* -> Separate `/v1` and `/v2` mappings or custom request conditions.
- *What counts as breaking?* -> Removing/renaming fields, changing types or meaning, new required inputs.
- *Client side?* -> RestClient/WebClient can insert the version via an `ApiVersionInserter`.

**60-second answer**
"First I try to avoid a version: adding a `priceDetail` field next to `price` breaks nobody. If the change truly breaks clients, Spring Framework 7 has built-in versioning: I configure the strategy once, a header or the path, and annotate handler methods with `version = "1"` or `"2"`, both calling the same service through different mappers. v1 gets Deprecation and Sunset headers, and I track usage per mobile app version so it can be removed once traffic is gone."

### Q12 [mid] Test Spring MVC controllers with MockMvc, MockMvcTester and RestTestClient.
tags: mockmvc, webmvctest, mockmvctester, resttestclient, controller-testing, testing, profile-java-genai

**Start here: the concepts**
- **`@WebMvcTest`:** loads only the web layer (controllers, advice, converters, filters, security), no services or DB.
- **MockMvc:** simulates requests without a server. **MockMvcTester** (Spring 6.2) adds AssertJ-style fluent assertions. **RestTestClient** (Spring 7) is a unified test client for MockMvc or a live server.
- **`@MockitoBean`:** replaces a bean with a mock in the test context.

**The live scenario (functional requirement)**
*FR: "Prove the booking API returns 201 with Location on success, 400 with field errors on bad input, 404 Problem Details for unknown ids, and 403 for the wrong role."*

**What the interviewer is really checking**
That you test the HTTP contract (status, headers, JSON, security) fast and in isolation.

**How I answer it**
1. `@WebMvcTest(BookingController.class)` and `@MockitoBean BookingService service`.
2. Happy path: given the mock returns a booking, POST JSON and assert 201, `Location` header, and JSON fields with JsonPath.
3. Validation: POST an invalid body, assert 400 and the field error list. This also tests the advice and Problem Details format.
4. 404: mock throws `BookingNotFoundException`, assert status and `code`.
5. Security: with `jwt().authorities(...)` or `@WithMockUser(roles = "AGENT")`, assert 403 for the admin-only endpoint.
6. A couple of full `@SpringBootTest(webEnvironment = RANDOM_PORT)` tests with RestTestClient verify the real stack end to end.

**Trade-offs and what can go wrong**
- Mocking the service means the test doesn't prove the service works; that's what service unit tests are for.
- Forgetting security in `@WebMvcTest` means it applies by default; import your security config to test real rules.

**How I'd monitor it**
Test duration and flakiness in CI; contract coverage of documented status codes.

**Follow-ups to expect**
- *MockMvc vs TestRestTemplate?* -> MockMvc has no network and is fast; a real server tests the servlet container too.
- *How do you test a streaming endpoint?* -> `asyncDispatch` in MockMvc, or WebTestClient against the Flux.
- *Testing JSON serialisation alone?* -> `@JsonTest`.

**60-second answer**
"I use `@WebMvcTest` for the controller with the service mocked via `@MockitoBean`, and MockMvc or the newer MockMvcTester to assert the HTTP contract: 201 with Location, 400 with field errors, 404 as Problem Details, and 403 for the wrong role with a mocked JWT. That tests controllers, validation, advice and security together in milliseconds. Then a few full-server tests with RestTestClient cover the real stack."

### Q13 [mid] Configure CORS and CSRF for a React SPA calling a Spring MVC backend.
tags: cors, csrf, spring-security, spa, cookies, bff, profile-java-genai

**Start here: the concepts**
- **CORS:** the browser blocks cross-origin calls unless the server sends `Access-Control-Allow-Origin` etc.; preflight `OPTIONS` for non-simple requests.
- **CSRF:** an attack that rides on cookies the browser sends automatically; needed when auth is cookie-based, not for pure bearer-token APIs.

**The live scenario (functional requirement)**
*FR: "The React app on app.example.com calls api.example.com; login uses the corporate SSO."* Browser shows "blocked by CORS policy" on every POST.

**What the interviewer is really checking**
That you understand what each protection is for, and don't "fix" CORS with `*`.

**How I answer it**
1. CORS in Spring Security (`http.cors(...)` with a `CorsConfigurationSource`), so preflight requests aren't rejected by security first.
2. Allow exactly `https://app.example.com`, the methods and headers you use, `allowCredentials(true)` only if cookies are used (and never with `*`).
3. **Auth design decides CSRF:** with a **BFF** (backend-for-frontend) holding tokens server-side and an HttpOnly, SameSite session cookie, keep CSRF on, using `CookieCsrfTokenRepository` so React reads the token and sends `X-XSRF-TOKEN`.
4. With bearer tokens in the `Authorization` header (no cookies), CSRF can be disabled for that API.
5. Same-site deployment (one domain via a gateway path `/api`) avoids CORS altogether.

**Trade-offs and what can go wrong**
- `allowedOrigins("*")` with credentials is rejected by browsers and dangerous.
- Tokens in localStorage are exposed to XSS; the BFF + HttpOnly cookie pattern is safer.
- CORS is a browser rule; it does not protect the API from curl.

**How I'd monitor it**
Preflight failures, 403 CSRF rejections after releases.

**Follow-ups to expect**
- *Why preflight?* -> For non-simple methods or headers, the browser asks permission first.
- *`@CrossOrigin`?* -> Fine per controller, but central config in security is easier to audit.
- *SameSite cookies?* -> `Lax`/`Strict` block most cross-site cookie sending, reducing CSRF risk.

**60-second answer**
"CORS is the browser asking whether app.example.com may call the API, so I configure it in Spring Security, so preflights pass, with the exact origin, methods and headers, never `*` with credentials. CSRF depends on auth: with a BFF and HttpOnly session cookies, which I prefer for SPAs, CSRF stays on with a cookie token React echoes in a header. With pure bearer tokens and no cookies, it can be off. Serving the SPA and API under one domain removes CORS entirely."

### Q14 [mid] Implement pagination, sorting and filtering in a Spring MVC + Spring Data API.
tags: pagination, pageable, sorting, filtering, specification, spring-data, profile-java-genai

**Start here: the concepts**
- **`Pageable`** binds `?page=0&size=20&sort=createdAt,desc` automatically.
- **`Page<T>`** includes a count query; **`Slice<T>`** skips it (just "has next").
- **Specifications / Querydsl** build dynamic filters.

**The live scenario (functional requirement)**
*FR: "Agents search tickets by status, priority and date range, sort by any column, 25 per page; the table holds 40 million rows."*

**What the interviewer is really checking**
That pagination is safe at scale: max page size, sort whitelist, count cost, deep pages.

**How I answer it**
1. Controller takes `TicketFilter` (a validated record) + `Pageable`; cap size with `spring.data.web.pageable.max-page-size=100`.
2. **Whitelist sort fields**; arbitrary sort on unindexed columns means full scans and lets clients probe internal fields.
3. Dynamic filters with `Specification<Ticket>` combining only the provided criteria.
4. **Return a DTO page**, not `PageImpl` serialised directly: Boot 3.3+ warns and offers `@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)` for a stable JSON shape.
5. **40 million rows:** the count query is expensive, so use `Slice` (no total) or an approximate count; deep `OFFSET 400000` is slow, so offer keyset/cursor pagination (`createdAt < :lastSeen`) for scrolling.
6. Composite indexes matching the common filter + sort.

**Trade-offs and what can go wrong**
- Offset pagination skips/duplicates rows when data changes between pages; cursors are stable.
- Total counts on huge tables can dominate latency.

**How I'd monitor it**
Query time by filter combination, slow-query log, page-size distribution.

**Follow-ups to expect**
- *Keyset with ties?* -> Order by `(createdAt, id)` and compare both.
- *Search across text?* -> Move to Elasticsearch/OpenSearch, not `LIKE '%x%'`.
- *Why Slice?* -> Infinite scroll doesn't need the total.

**60-second answer**
"Spring binds `Pageable` from query params, and filters go into a validated record that builds a Specification from only the criteria given. On 40 million rows I cap page size, whitelist sortable columns that are indexed, return a stable DTO page, and avoid the expensive count by using Slice or approximate totals. Deep pages and live data call for keyset pagination with a cursor on created-at plus id, which stays fast and doesn't skip rows."

### Q15 [architect] Organise the MVC layers: thin controllers, DTO mapping, and open-session-in-view.
tags: layered-architecture, dto, mapstruct, open-in-view, controller-design, clean-code, profile-java-genai

**Start here: the concepts**
- **Controller:** HTTP only: binding, validation, status codes. **Service:** use cases, transactions. **Repository:** persistence.
- **DTO:** the API shape, separate from entities. Mapping by hand or MapStruct (compile-time generated).
- **Open-session-in-view (OSIV):** keeps the Hibernate session open until the view renders. Boot enables it by default and logs a warning.

**The live scenario (functional requirement)**
*FR: "A travel itinerary API used by web, mobile and partner channels; each channel needs a slightly different shape."* The old code returned entities, had business rules in controllers, and 30 lazy queries fired during JSON serialisation.

**What the interviewer is really checking**
Clean responsibilities, API stability, and awareness of OSIV's hidden cost.

**How I answer it**
1. **Thin controllers:** map request -> command, call one service method, map result -> response. No `if` business rules.
2. **Services** own transactions and return domain objects or DTOs, fully loaded.
3. **DTOs per API**, mapped with MapStruct; entities never cross the controller. Changing a column no longer breaks partners.
4. **Channel differences** in mappers (or a BFF per channel), not in the domain.
5. **Turn off OSIV** (`spring.jpa.open-in-view=false`): lazy loading outside transactions now fails loudly in tests, forcing explicit fetch plans instead of 30 hidden queries.
6. Enforce layering with ArchUnit (controllers may not use repositories).

**Trade-offs and what can go wrong**
- Mapping boilerplate; MapStruct removes most of it.
- Overly layered "pass-through" services add nothing; keep them thin when logic is thin, but keep the boundary.
- Turning OSIV off in a legacy app surfaces `LazyInitializationException`s; fix them before production.

**How I'd monitor it**
Queries per request, payload sizes per channel, architecture tests in CI.

**Follow-ups to expect**
- *Why not return entities?* -> Leaks internals, lazy-loading surprises, circular references, couples API to schema.
- *Records as DTOs?* -> Yes, ideal: immutable and concise.
- *Where does validation live?* -> Shape validation on DTOs; business invariants in the domain/service.

**60-second answer**
"Controllers only translate HTTP: bind, validate, call one service method, choose the status. Services own the use case and the transaction and return fully loaded data. The API uses DTO records mapped with MapStruct, so entities never leak and each channel's shape lives in its mapper or a BFF. I switch off open-session-in-view, which Boot enables by default, so lazy loading during JSON serialisation fails in tests instead of firing 30 hidden queries in prod, and ArchUnit keeps the layers honest."
