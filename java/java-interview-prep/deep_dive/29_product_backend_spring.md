# Spring Boot, HTTP and persistence

Questions 115–144 from the [Product Java Backend Expanded Question Bank](../../InterviewTopic/Product_Java_Backend_Expanded_Question_Bank.pdf), documented by @lowkey.unhandled. Question numbers follow the source PDF.

### Trace a checkout conflict

Two transactions read inventory with version 8. The first decrements stock and updates the version to 9. The second update includes WHERE version = 8 and changes zero rows. Translate the optimistic conflict into a domain decision after rollback. A retry needs a fresh transaction and a fresh stock check. Test the race with separate connections against the production database engine. A single test transaction cannot reproduce this interleaving.

## Interview questions and answers

### Q115. What problem does Spring solve? Explain IoC and Dependency Injection.

Spring's container constructs application objects, assembles their dependencies and manages lifecycle and cross-cutting behavior. With constructor injection, CheckoutService receives a PaymentGateway supplied by configuration. This makes dependencies visible and allows a unit test to pass a fake gateway without starting the container.

### Q116. BeanFactory vs ApplicationContext; bean lifecycle and lifecycle callbacks.

BeanFactory provides bean definitions and dependency resolution. ApplicationContext adds facilities such as events, resource loading and application-wide post-processors. A typical singleton is instantiated, injected, processed before initialization, initialized through callbacks such as PostConstruct and then possibly wrapped in a proxy. On context shutdown destruction callbacks release resources.

### Q117. @Component vs @Service vs @Repository vs @Controller.

Component is the general scan marker. Service names an application or domain service. Repository identifies persistence components and supports exception translation when configured. Controller participates in MVC request handling. Pick stereotypes by responsibility so readers can follow an order request from controller to service to database.

### Q118. @Bean vs @Component; @Configuration and proxyBeanMethods.

Component scanning discovers annotated classes. A Bean method registers the object it returns, useful for a third-party client. In full Configuration mode, proxied calls between bean methods return the container-managed instance for that scope. With proxyBeanMethods=false a direct call is ordinary Java. Inject dependencies as method parameters to avoid depending on interception.

### Q119. Constructor vs setter vs field injection; why is constructor injection preferred?

Constructor injection requires collaborators up front, supports final fields and works in plain unit tests. Setter injection suits genuinely optional dependencies with defaults. Field injection hides requirements from constructors and complicates tests. A long constructor often indicates a service owns too many responsibilities.

### Q120. Singleton, prototype, request and session bean scopes.

Singleton normally gives one instance per bean definition per container. Prototype creates a fresh instance on each lookup, with cleanup left to the caller. Request and session scopes bind instances to web lifetimes. Injecting a prototype directly into a singleton resolves it only once; use a provider or scoped proxy for repeated lookup.

### Q121. @Primary vs @Qualifier; @Lazy; circular dependency resolution.

Primary chooses a default among matching beans, while Qualifier narrows the eligible candidates, for example selecting the refund gateway. Lazy defers creation or injects a lazy proxy. A constructor cycle prevents eager construction from finding a starting point. Move shared work into a separate collaborator or revise ownership before considering deferred resolution.

### Q122. How does Spring Boot auto-configuration work? @Conditional annotations.

Boot imports candidate auto-configurations and evaluates conditions on classes, properties, application type and existing beans. A datasource configuration can back off when the user supplies a DataSource. Inspect the condition evaluation report when a component is unexpectedly present or absent, then verify the classpath and effective properties.

### Q123. Spring Boot starters; embedded server; application startup lifecycle.

A starter bundles related dependencies. Auto-configuration reacts to what is on the classpath. SpringApplication prepares the environment and context, loads definitions and refreshes it, creating beans and the embedded web server in a web application. Runners execute before application-ready signaling. Tie traffic admission to readiness when startup includes warm-up.

### Q124. How do profiles and externalized configuration work?

Profiles select environment-specific beans or property documents. Boot combines packaged defaults with external files, environment variables and command-line settings according to property-source precedence. Bind related settings to validated ConfigurationProperties. During incident diagnosis inspect the effective value and its origin while redacting credentials.

### Q125. Explain request flow from DispatcherServlet to controller and response.

A servlet filter chain receives the HTTP request, then DispatcherServlet locates a handler via HandlerMapping. A HandlerAdapter resolves arguments, converts the body, applies validation and invokes the controller. A return-value handler selects view rendering or an HTTP message converter for JSON. Exception resolvers can translate failures into responses.

### Q126. Filter vs HandlerInterceptor vs AOP; execution order and use cases.

Filters wrap the servlet chain, so they can handle headers and security before MVC dispatch. Interceptors wrap mapped handler execution with preHandle and completion hooks. AOP surrounds proxied bean method calls, useful for service timings beyond HTTP. Unwinding occurs in reverse nesting order. A filter can short-circuit before a controller or interceptor runs.

### Q127. @Controller vs @RestController; @RequestParam vs @PathVariable vs @RequestBody.

Controller typically resolves view names unless a handler uses ResponseBody. RestController applies response-body semantics across its handlers. PathVariable identifies a resource such as /orders/{id}, RequestParam binds query values such as page size, and RequestBody deserializes a representation. Validate external values before domain updates.

### Q128. POST vs PUT vs PATCH; idempotency; safe and idempotent HTTP methods.

POST submits work or creates a subordinate resource. PUT replaces the target representation and is idempotent. PATCH applies partial changes; setting quantity to three is idempotent whereas incrementing it is not. Safe methods such as GET request no state change. Idempotence concerns the intended effect of repeats, so a repeated DELETE may return a different status.

### Q129. How do you design pagination, sorting, filtering and API versioning?

Offset pagination is convenient but becomes expensive at depth and shifts under inserts. A cursor encoding a stable order such as (createdAt,id) supports keyset pagination through indexed comparisons. Bound page size, allowlist sortable fields and parameterize filters. Introduce a new API version for incompatible contracts and preserve older clients during migration.

### Q130. Global exception handling using @ControllerAdvice and @ExceptionHandler.

Centralize exception mappings with RestControllerAdvice and ExceptionHandler. Translate missing orders to 404, invalid input to 400 and conflicting updates to 409 when appropriate. Return a stable error code, safe detail and correlation ID. Log unexpected exceptions once with their stack internally so clients can report a traceable failure.

### Q131. Bean Validation: @Valid vs @Validated; custom validators.

Valid cascades into nested objects and triggers validation on supported MVC arguments. Spring's Validated supports groups and method-validation integration. Define a custom constraint annotation with a ConstraintValidator for rules such as start preceding end. Keep uniqueness enforced by a database constraint because concurrent requests can pass the same application check.

### Q132. How do you secure REST APIs? JWT, OAuth2, authentication and authorization.

OAuth 2.0 defines delegated access. A resource server can receive a JWT access token, verify its signature with trusted keys, restrict algorithms and validate issuer, audience and expiry. Map trusted claims to authorities, then check resource ownership on each order access. Authentication identifies the caller and authorization decides which operation that caller may perform.

### Q133. CORS vs CSRF; Spring Security filter chain.

CORS governs whether browser scripts from another origin can read responses, including preflight handling. CSRF concerns involuntary authenticated state changes with ambient credentials such as session cookies. Use CSRF protection for cookie-authenticated writes. Configure the Spring Security filter chain to handle preflight, extract credentials, authenticate and enforce access rules before dispatch.

### Q134. How do you implement API rate limiting and request correlation IDs?

A token bucket per tenant or API key permits bounded bursts and refills at the allowed rate. Use an atomic shared counter or gateway enforcement when limits span replicas, and return 429 with retry guidance. Validate or generate a correlation ID at ingress, propagate it through logs and messages, and use trace context for causal spans.

### Q135. How does @Transactional work internally? Proxy-based behavior and self-invocation.

A call through the Spring proxy reaches transaction advice, which resolves propagation and asks the transaction manager to begin or join work. It commits or rolls back on exit. Calling this.otherMethod() inside the target bypasses that proxy, so the inner annotation cannot start its requested transaction. Put the boundary on an externally invoked service or use TransactionTemplate. [Spring transaction reference](https://docs.spring.io/spring-framework/reference/data-access/transaction/declarative/annotations.html)

### Q136. Propagation: REQUIRED, REQUIRES_NEW, SUPPORTS, MANDATORY, NOT_SUPPORTED.

REQUIRED joins or creates a transaction. REQUIRES_NEW suspends the outer one and commits independently, often needing another pooled connection. SUPPORTS joins if present. MANDATORY rejects calls without an existing transaction. NOT_SUPPORTED suspends an existing transaction for the duration. An independent audit write can survive a business rollback, so label its semantics carefully.

### Q137. Isolation levels; dirty read, non-repeatable read and phantom read.

Dirty reads expose uncommitted writes. Non-repeatable reads see changed values for the same row and phantom reads see a changed matching set. Read committed prevents dirty reads. Repeatable read protects reread rows, with phantom behavior depending on the engine. Serializable aims for a serial-equivalent history and may abort conflicting work. Retry the entire aborted transaction.

### Q138. Rollback rules; checked vs unchecked exception behavior.

Spring's usual declarative default rolls back on RuntimeException and Error. A checked exception ordinarily allows commit unless rollbackFor or a configured policy changes that. Catching and suppressing an exception may hide it from the interceptor. A joined transaction already marked rollback-only can still fail at outer commit. Verify by checking persisted state after the call.

### Q139. Optimistic vs pessimistic locking; @Version and lost updates.

Optimistic locking includes a version in the update predicate and increments it. If another writer wins, the stale update affects zero rows and JPA reports a conflict. Reload and retry only if the business decision still holds. Pessimistic locking acquires a database lock early, trading fewer conflicts for waiting and deadlock risks. Keep lock duration short.

### Q140. Entity lifecycle; persistence context; dirty checking and flush vs commit.

A new entity becomes managed via persist. Detached objects no longer receive automatic dirty tracking, and merge returns a managed copy. Remove schedules deletion. The persistence context tracks managed changes and flush sends SQL to the database, possibly before a query. Commit finalizes the transaction. A flushed update can still be rolled back.

### Q141. Lazy vs eager loading; N+1 problem; fetch join and entity graphs.

Lazy associations load on access within a usable persistence context. Eager specifies availability but need not produce one join. Listing orders then reading each customer can issue 1+n queries. Fetch the needed association with a fetch join, entity graph or DTO projection. Avoid collection fetch joins with offset pagination; page root IDs first and fetch details in a second query.

### Q142. Cascade types vs orphanRemoval; owning side of relationships.

Cascade propagates selected entity operations, for example persist from order to lines. orphanRemoval deletes a privately owned child removed from its relationship. The owning side controls the database link, usually the child with the foreign key. Maintain both sides in helper methods and avoid cascading removal into shared reference data.

### Q143. JPQL vs native SQL vs derived queries vs JPA Specification.

Derived query names suit short fixed predicates. JPQL queries entities and associations portably. Native SQL exposes database-specific operators and tuned plans. Specifications compose optional criteria such as status and date range. Inspect generated SQL and execution plans for important queries regardless of which interface produced them.

### Q144. How do you test controllers, services and repositories? JUnit, Mockito, MockMvc, Testcontainers.

Exercise controllers with MockMvc for routing, serialization, validation and security responses. Instantiate services with JUnit and Mockito or fakes to verify business decisions and failure paths. Use repository integration tests against the real engine in Testcontainers for constraints, locking and dialect behavior. Include a test crossing a real commit boundary for deferred constraint failures.
