# Java / J2EE Resource Request --- Interview Questions & Answers

## Java 8, Java 11, Spring Boot, Microservices, REST APIs, Apache Kafka, NoSQL, and Splunk

**Prepared for:** Resource-request / technical interview preparation\
**Level:** Basic → Intermediate → Advanced\
**Purpose:** A reusable Markdown study guide. Save it in any Markdown
editor, Git repository, wiki, or documentation tool.

> **How to use this guide:** First answer each question aloud without
> reading the answer. Then review the explanation and code. For scenario
> questions, explain the trade-offs and operational consequences---not
> only the definition.

------------------------------------------------------------------------

# Contents

1.  Core Java fundamentals
2.  Java 8 features
3.  Java 11 features
4.  Collections, concurrency, and JVM
5.  Spring and Spring Boot
6.  REST APIs and API design
7.  Microservices
8.  Apache Kafka
9.  NoSQL databases
10. Splunk and production troubleshooting
11. End-to-end design and scenario questions
12. Quick revision checklist

------------------------------------------------------------------------

# 1. Core Java Fundamentals

## Q1. What is Java, and why is it platform-independent?

**Answer:** Java is a statically typed, object-oriented programming
language. Java source code is compiled into **bytecode** (`.class`
files). A compatible Java Virtual Machine (JVM) executes that bytecode
on the target operating system.

The usual flow is:

``` text
Hello.java --javac--> Hello.class --JVM--> machine-specific execution
```

Example:

``` java
public class Hello {
    public static void main(String[] args) {
        System.out.println("Hello, Java");
    }
}
```

Compile and run:

``` bash
javac Hello.java
java Hello
```

**Interview point:** Java is platform-independent at the bytecode/JVM
level, but the JVM implementation and some native integrations are
platform-specific. "Write once, run anywhere" assumes a compatible
runtime and dependencies.

## Q2. What is the difference between JDK, JRE, and JVM?

-   **JVM:** Executes Java bytecode and manages runtime activities such
    as memory and garbage collection.
-   **JRE:** Conceptually includes the JVM and runtime libraries needed
    to run Java applications.
-   **JDK:** Includes development tools such as the compiler (`javac`),
    launcher, debugger, and runtime components.

Modern Java distributions may package these differently; since Java 9,
the old separate JRE download model is no longer the standard Oracle
distribution approach.

## Q3. Explain the four pillars of object-oriented programming.

1.  **Encapsulation:** Keep state and implementation details inside a
    class; expose controlled methods.
2.  **Abstraction:** Expose essential behavior while hiding
    implementation details.
3.  **Inheritance:** Derive a class from another class to reuse or
    specialize behavior.
4.  **Polymorphism:** Use a common type while the runtime selects the
    implementation of an overridden method.

Example:

``` java
interface PaymentService {
    void pay(double amount);
}

class CardPaymentService implements PaymentService {
    @Override
    public void pay(double amount) {
        System.out.println("Paying by card: " + amount);
    }
}

class UpiPaymentService implements PaymentService {
    @Override
    public void pay(double amount) {
        System.out.println("Paying by UPI: " + amount);
    }
}
```

Code can depend on `PaymentService` rather than a specific
implementation. This improves testability and makes adding another
payment method easier.

## Q4. What is the difference between an interface and an abstract class?

  -----------------------------------------------------------------------
  Interface                           Abstract class
  ----------------------------------- -----------------------------------
  Defines a contract; a class can     Provides a shared base
  implement multiple interfaces       implementation; a class can extend
                                      only one class

  Can contain abstract, default,      Can contain instance state,
  static, and private methods         constructors, and concrete/abstract
  (private methods from Java 9)       methods

  No ordinary per-instance fields;    Can hold instance fields
  fields are implicitly               
  `public static final`               

  Useful for capabilities and loose   Useful when related classes share
  coupling                            state or implementation
  -----------------------------------------------------------------------

**Example:** `Runnable` is a capability contract. An abstract
`BaseReportGenerator` could hold shared report configuration and helper
methods.

Choose based on the relationship and design---not merely on whether a
method has a body.

## Q5. What is the difference between `==` and `equals()`?

-   For primitives, `==` compares values.
-   For references, `==` checks whether both references point to the
    same object.
-   `equals()` checks logical equality if the class overrides it;
    otherwise, `Object.equals()` behaves like reference equality.

``` java
String a = new String("Kafka");
String b = new String("Kafka");

System.out.println(a == b);      // false: different objects
System.out.println(a.equals(b)); // true: same text
```

When creating a value object, implement `equals()` and `hashCode()`
consistently. Equal objects must have equal hash codes, especially when
used as keys in `HashMap` or elements in `HashSet`.

## Q6. Explain checked exceptions, unchecked exceptions, and errors.

-   **Checked exceptions:** Must be caught or declared,
    e.g. `IOException`.
-   **Unchecked exceptions:** Subclasses of `RuntimeException`,
    e.g. `IllegalArgumentException`, `NullPointerException`.
-   **Errors:** Serious JVM or environment problems,
    e.g. `OutOfMemoryError`; application code generally should not try
    to recover from all errors.

Use exceptions for exceptional conditions, not ordinary control flow.
Preserve the original cause when wrapping an exception:

``` java
try {
    loadFile();
} catch (IOException e) {
    throw new ReportLoadException("Unable to load report", e);
}
```

At service boundaries, translate internal exceptions into safe API
errors; do not expose stack traces to clients.

## Q7. What is immutability, and why is `String` immutable?

An immutable object cannot change its observable state after
construction. Benefits include safer sharing across threads, predictable
hash keys, and simpler reasoning.

`String` is immutable, which supports string pooling, safe reuse, and
security-sensitive use cases such as class names and paths. For repeated
concatenation in a loop, use `StringBuilder`:

``` java
StringBuilder result = new StringBuilder();
for (String item : items) {
    result.append(item).append(',');
}
String csv = result.toString();
```

For concurrent mutation, `StringBuilder` is not synchronized; choose
thread-confined use or an appropriate alternative.

## Q8. What is the difference between `final`, `finally`, and `finalize()`?

-   `final` can restrict reassignment, overriding, or inheritance
    depending on where it is used.
-   `finally` is a cleanup block used with `try`/`catch`; it usually
    runs whether or not an exception occurs.
-   `finalize()` was a legacy garbage-collection hook and is deprecated
    for removal. Do not use it for resource cleanup.

Prefer **try-with-resources** for `AutoCloseable` resources:

``` java
try (var input = new java.io.FileInputStream("input.txt")) {
    System.out.println(input.read());
}
```

## Q9. What is the difference between `ArrayList` and `LinkedList`?

`ArrayList` uses a resizable array and usually offers fast indexed reads
and good cache locality. Appending is amortized O(1); inserting/removing
in the middle usually shifts elements.

`LinkedList` is a doubly linked list. Indexed access is O(n), and
insertion/removal is O(1) only when the relevant node/iterator position
is already known. It also has greater per-element memory overhead.

**Practical default:** Prefer `ArrayList` unless measurements and access
patterns justify another structure.

## Q10. How does `HashMap` work?

A `HashMap` uses a key's hash code to help select a bucket, then uses
equality to identify the key. Collisions are possible. In modern Java
implementations, heavily collided buckets may become balanced trees
under certain conditions.

Important rules: - Implement `equals()` and `hashCode()` consistently. -
Avoid mutating key fields that affect equality/hash code while a key is
stored. - `HashMap` is not thread-safe for concurrent mutation. - It
permits one `null` key and `null` values; `ConcurrentHashMap` does not
permit `null` keys or values.

Expected lookup is approximately O(1) under a good hash distribution,
not a guaranteed constant-time promise in every case.

------------------------------------------------------------------------

# 2. Java 8 Features

## Q11. What major features arrived in Java 8?

Important features include: - Lambda expressions - Functional
interfaces - Method references - Stream API - Default and static
interface methods - `Optional` - New Date/Time API (`java.time`) -
`CompletableFuture`

These features support more expressive collection processing, APIs, and
asynchronous workflows.

## Q12. What is a functional interface?

An interface with exactly one abstract method is a functional interface.
It can be implemented with a lambda expression. Default and static
methods do not count as abstract methods.

``` java
@FunctionalInterface
interface PriceRule {
    double apply(double originalPrice);
}

PriceRule discount = price -> price * 0.90;
System.out.println(discount.apply(1000)); // 900.0
```

Common built-ins: - `Predicate<T>`: takes a value and returns
`boolean` - `Function<T, R>`: transforms `T` into `R` - `Consumer<T>`:
accepts a value and returns nothing - `Supplier<T>`: supplies a value

## Q13. What is a lambda expression?

A lambda is a concise implementation of a functional interface.

``` java
List<String> names = Arrays.asList("Asha", "Ravi", "Meera");
names.forEach(name -> System.out.println(name));
```

A lambda can capture local variables only when they are final or
effectively final. Lambdas are not simply anonymous inner classes with
different syntax; their runtime implementation and `this` behavior
differ.

## Q14. Explain the Stream API with an example.

Streams describe a pipeline of operations over data. Intermediate
operations such as `filter()` and `map()` are generally lazy; a terminal
operation such as `collect()` or `forEach()` triggers processing.

``` java
List<String> result = employees.stream()
    .filter(e -> e.getSalary() >= 80000)
    .map(Employee::getName)
    .sorted()
    .collect(Collectors.toList());
```

The pipeline filters employees, maps them to names, sorts the names, and
collects the result.

**Common mistakes:** - A stream is not a collection and is normally
consumed once. - Avoid side effects inside stream operations. - Parallel
streams are not automatically faster; consider data size, splitting
cost, thread-pool use, ordering, and thread safety.

## Q15. What is the difference between `map()` and `flatMap()`?

`map()` transforms each element into one result. `flatMap()` transforms
each element into a stream or container and flattens the nested results.

``` java
List<List<String>> teams = List.of(
    List.of("Ravi", "Asha"),
    List.of("Meera", "Dev")
);

List<String> people = teams.stream()
    .flatMap(List::stream)
    .collect(Collectors.toList());
// [Ravi, Asha, Meera, Dev]
```

Use `flatMap()` when each input can produce zero, one, or many outputs.

## Q16. What is `Optional`, and when should it be used?

`Optional<T>` represents a value that may be absent. It can make absence
explicit in return types.

``` java
Optional<User> user = repository.findById(id);

String displayName = user
    .map(User::getName)
    .filter(name -> !name.isBlank())
    .orElse("Guest");
```

Avoid blindly calling `get()`. `Optional` is generally most useful as a
return type; using it for every field, method parameter, or
serialization model is often unnecessary. Do not use
`orElse(expensiveCall())` when you need lazy fallback evaluation---use
`orElseGet()`.

## Q17. What is the Java 8 Date/Time API advantage?

`java.time` provides clearer immutable types such as `LocalDate`,
`LocalTime`, `LocalDateTime`, `Instant`, and `ZonedDateTime`. Unlike
legacy `Date`/`Calendar` APIs, most types are immutable and thread-safe.

``` java
LocalDate today = LocalDate.now(ZoneId.of("Asia/Kolkata"));
ZonedDateTime meeting = ZonedDateTime.of(
    2026, 10, 20, 10, 30, 0, 0,
    ZoneId.of("Asia/Kolkata")
);
```

Use `Instant` for a point on the UTC timeline; use `ZonedDateTime` when
the time zone's rules matter. Do not assume a server's default time zone
is the business time zone.

## Q18. What is `CompletableFuture`?

`CompletableFuture` represents a result that may become available later
and supports composing asynchronous tasks.

``` java
CompletableFuture<String> profileFuture =
    CompletableFuture.supplyAsync(() -> loadProfile(userId));

CompletableFuture<Integer> scoreFuture =
    CompletableFuture.supplyAsync(() -> loadScore(userId));

CompletableFuture<String> summary =
    profileFuture.thenCombine(scoreFuture,
        (profile, score) -> profile + " | score=" + score);
```

Production considerations: - Choose an executor appropriate to the
workload. - Set timeouts and handle exceptions. - Do not block request
threads waiting on many futures without understanding resource usage. -
Async does not automatically mean non-blocking I/O.

------------------------------------------------------------------------

# 3. Java 11 Features

## Q19. What are useful Java 11 features?

Java 11 is an LTS release. Useful features include: - Standard HTTP
Client API (`java.net.http`) - `String.isBlank()`, `strip()`, `lines()`,
`repeat()` - `Files.readString()` and `Files.writeString()` -
`Optional.isEmpty()` - Local-variable syntax for lambda parameters
(`var`, with restrictions) - Single-file source-code launching
(`java Hello.java`)

Java 11 also removed some modules/tools that existed in older JDK
distributions, so migration testing is important.

## Q20. How do `trim()` and `strip()` differ?

`trim()` removes characters at or below the traditional ASCII space
boundary. `strip()` uses Unicode-aware whitespace rules.

``` java
String input = "\u2003Hello\u2003";
System.out.println(input.trim());  // May retain these Unicode spaces
System.out.println(input.strip()); // "Hello"
```

Use `strip()` when Unicode whitespace is relevant.

## Q21. Show an HTTP request using Java 11's HTTP Client.

``` java
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;

public class ApiClient {
    public static void main(String[] args) throws Exception {
        HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(3))
            .build();

        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create("https://api.example.com/health"))
            .timeout(Duration.ofSeconds(5))
            .header("Accept", "application/json")
            .GET()
            .build();

        HttpResponse<String> response = client.send(
            request, HttpResponse.BodyHandlers.ofString());

        System.out.println(response.statusCode());
        System.out.println(response.body());
    }
}
```

In production, handle non-2xx responses, timeouts, retries,
authentication, logging, and response-body size. Retry only when safe
and appropriate.

## Q22. What should you check when migrating an application from Java 8 to Java 11?

1.  Compile and test against the intended JDK.
2.  Review removed Java EE/CORBA modules and tools from the JDK
    distribution.
3.  Check dependency compatibility and unsupported internal JDK APIs.
4.  Verify TLS, certificates, database drivers, agents, and monitoring
    tools.
5.  Run integration and performance tests.
6.  Confirm container images and build pipelines use the intended
    runtime.
7.  Check JVM flags; some options may have changed or become obsolete.

Java 11 does not include every Java EE API formerly bundled with some
Java 8 distributions. Add supported dependencies where needed.

------------------------------------------------------------------------

# 4. Collections, Concurrency, and JVM

## Q23. What is the difference between `synchronized`, `volatile`, and atomic classes?

-   `synchronized` provides mutual exclusion and memory-visibility
    guarantees around a monitor.
-   `volatile` provides visibility and ordering guarantees for
    reads/writes of a variable, but does **not** make compound
    operations such as `count++` atomic.
-   `AtomicInteger` and related classes support atomic operations such
    as increment and compare-and-set.

``` java
private final AtomicInteger count = new AtomicInteger();

public int nextCount() {
    return count.incrementAndGet();
}
```

Use the simplest mechanism that correctly protects the shared state. For
multiple related variables that must change together, a lock or another
coordinated design may be needed.

## Q24. What is the difference between `Runnable` and `Callable`?

`Runnable.run()` returns no result and cannot declare checked
exceptions. `Callable<V>.call()` returns a result and may throw checked
exceptions. Both can be submitted to executor services; a `Callable`
commonly produces a `Future<V>`.

Prefer managing work through `ExecutorService` instead of manually
creating many threads. Define pool sizing, queue capacity, shutdown
behavior, and rejection handling.

## Q25. What is a deadlock, and how can you prevent it?

A deadlock occurs when threads wait indefinitely for locks held by one
another.

Example: Thread A locks account 1 then waits for account 2; Thread B
locks account 2 then waits for account 1.

Prevention: - Acquire locks in a consistent global order. - Minimize
nested locking. - Consider timed lock attempts with `tryLock()`. -
Capture thread dumps when investigating. - Prefer higher-level
concurrency utilities where appropriate.

## Q26. Explain heap, stack, and garbage collection.

-   **Heap:** Stores objects and arrays; managed by the garbage
    collector.
-   **Thread stack:** Stores stack frames, local variables, and call
    state for each thread.
-   **Metaspace:** Stores class metadata in native memory.
-   **Garbage collection:** Reclaims heap memory occupied by objects
    that are no longer reachable.

An object is not necessarily collectible just because the application no
longer uses it intentionally; a lingering reference can keep it
reachable. Common memory issues include unbounded caches, static
collections, listener leaks, large queues, and retaining request data.

## Q27. How would you investigate high CPU or memory usage in a Java service?

1.  Check recent deployment/configuration changes and traffic.
2.  Inspect CPU, heap, GC pauses, allocation rate, thread count, and
    container limits.
3.  Capture thread dumps for high CPU or blocked threads.
4.  Capture a heap dump when appropriate and analyze retained
    objects/dominator trees.
5.  Check GC logs and metrics.
6.  Correlate findings with request rates, Kafka lag, database latency,
    and error rates.
7.  Reproduce and validate the fix with load tests.

Do not immediately increase heap size without identifying the cause. A
larger heap can delay failure but may increase pause duration or conceal
a leak.

------------------------------------------------------------------------

# 5. Spring and Spring Boot

## Q28. What is dependency injection (DI), and why is it useful?

Dependency injection means an object receives its dependencies from an
external container or caller rather than constructing them internally.
Spring's IoC container manages beans and their dependencies.

``` java
@Service
public class OrderService {
    private final OrderRepository repository;

    public OrderService(OrderRepository repository) {
        this.repository = repository;
    }
}
```

Constructor injection makes dependencies explicit, supports immutable
fields, and simplifies unit testing. Prefer it for required
dependencies.

## Q29. What is the difference between Spring and Spring Boot?

**Spring Framework** provides core features such as DI, AOP,
transactions, web MVC, and integration abstractions.

**Spring Boot** builds on Spring to simplify application setup with
auto-configuration, starter dependencies, externalized configuration,
embedded-server support, and operational features such as Actuator.

Spring Boot does not replace Spring; it makes Spring applications easier
to configure and run.

## Q30. What happens when a Spring Boot application starts?

At a high level: 1. `SpringApplication.run()` starts the application. 2.
Spring prepares the environment and application context. 3. Component
scanning and auto-configuration contribute bean definitions. 4. Beans
are created and dependencies injected. 5. Embedded web-server
infrastructure starts for a web application. 6. Application runners
execute after startup.

Exact details vary by application type and Boot version. Use startup
logs and Actuator to understand the actual runtime.

## Q31. What are `@Component`, `@Service`, `@Repository`, and `@RestController`?

-   `@Component`: General Spring-managed component.
-   `@Service`: Service-layer semantic marker.
-   `@Repository`: Persistence-layer marker; can participate in
    persistence exception translation.
-   `@RestController`: Combines controller behavior with response-body
    serialization by default.

The first three are component-scan candidates. Choose annotations that
communicate the component's role clearly.

## Q32. Explain the controller-service-repository layering.

A typical request flow is:

``` text
HTTP request
   ↓
Controller: HTTP mapping, validation, status codes
   ↓
Service: business rules and transaction boundary
   ↓
Repository: persistence operations
   ↓
Database
```

Keep controllers thin. Keep business rules in services, and database
access in repositories. Avoid returning persistence entities directly
from public APIs when DTOs provide a safer, more stable contract.

## Q33. How do you validate request data in Spring Boot?

Use Bean Validation annotations on request DTOs and `@Valid` at the
controller boundary.

``` java
public record CreateCustomerRequest(
    @NotBlank String name,
    @Email String email
) {}

@RestController
@RequestMapping("/customers")
class CustomerController {
    @PostMapping
    ResponseEntity<Void> create(
            @Valid @RequestBody CreateCustomerRequest request) {
        // Delegate to service
        return ResponseEntity.status(HttpStatus.CREATED).build();
    }
}
```

The exact support for records and validation dependencies depends on the
Java and Spring Boot versions. Return a consistent error format and
avoid leaking internal details.

## Q34. How do you handle exceptions globally in Spring Boot?

Use `@RestControllerAdvice` and `@ExceptionHandler` to translate
exceptions into consistent HTTP responses.

``` java
@RestControllerAdvice
class ApiExceptionHandler {
    @ExceptionHandler(CustomerNotFoundException.class)
    ResponseEntity<Map<String, String>> notFound(
            CustomerNotFoundException ex) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
            .body(Map.of("error", "CUSTOMER_NOT_FOUND"));
    }
}
```

A production response may include a stable error code, safe message,
timestamp, and correlation/trace ID. Log diagnostic details server-side,
but do not return stack traces or secrets.

## Q35. What is Spring Boot Actuator?

Actuator exposes operational endpoints for health, metrics, environment,
and other management functions depending on configuration and
dependencies.

Common examples include `/actuator/health` and `/actuator/metrics`. Do
not expose every management endpoint publicly. Apply authentication,
network restrictions, and endpoint-specific access controls. Liveness
and readiness probes should reflect different questions: "Should this
process be restarted?" versus "Can it accept traffic?"

## Q36. How do Spring profiles and externalized configuration work?

Profiles allow environment-specific beans/configuration, while
externalized configuration allows properties to be supplied through
files, environment variables, command-line arguments, or configuration
systems.

Example:

``` yaml
spring:
  profiles:
    active: dev
```

A deployment environment can override settings without rebuilding the
artifact. Keep secrets in a secret manager or protected
environment---not in source control. Be careful not to log credentials
or sensitive configuration.

## Q37. Explain transaction management with `@Transactional`.

`@Transactional` typically lets Spring manage a transaction around a
method through a proxy or another configured mechanism.

``` java
@Service
class TransferService {
    @Transactional
    public void transfer(long from, long to, BigDecimal amount) {
        debit(from, amount);
        credit(to, amount);
    }
}
```

Important considerations: - Default rollback behavior commonly rolls
back on unchecked exceptions and `Error`, not every checked exception. -
Proxy-based transaction interception can be bypassed by
self-invocation. - Keep transactions short; do not hold database locks
while calling slow external APIs. - Transaction boundaries should match
business consistency requirements.

## Q38. How do you test a Spring Boot application?

-   **Unit tests:** Test business logic with collaborators mocked where
    useful.
-   **Web slice tests:** Test MVC/controller behavior with a focused
    application slice.
-   **Repository tests:** Test persistence mappings and queries.
-   **Integration tests:** Start more of the application and verify
    component interaction.
-   **Contract tests:** Verify API expectations between services.
-   **End-to-end tests:** Validate critical user flows across
    components.

Use a real compatible database or containerized dependency for important
database integration behavior. Mocks alone cannot validate SQL, indexes,
transactions, or driver behavior.

------------------------------------------------------------------------

# 6. REST APIs and API Design

## Q39. What is REST?

REST is an architectural style for networked systems. In typical RESTful
HTTP APIs, resources are identified by URLs and manipulated using
standard HTTP methods. Good designs use stateless requests, consistent
representations, caching where appropriate, and standard status codes.

Example resource: `/api/v1/orders/123`

REST is not synonymous with JSON, and an API is not automatically
RESTful just because it uses HTTP.

## Q40. Explain common HTTP methods and their idempotency.

  Method   Typical use                         Idempotent?
  -------- ----------------------------------- --------------------------------
  GET      Retrieve a resource                 Yes
  POST     Create or trigger processing        Not inherently
  PUT      Replace a resource at a known URI   Intended to be
  PATCH    Partially modify a resource         Depends on the patch semantics
  DELETE   Delete a resource                   Intended to be

**Idempotent** means repeating the same request has the same intended
effect as doing it once. The response code may differ between
attempts---for example, the first DELETE may return 204 and a later one
404---while the intended end state remains unchanged.

## Q41. Explain important HTTP status codes.

-   `200 OK`: Successful request with a response.
-   `201 Created`: Resource created; often include a `Location` header.
-   `202 Accepted`: Accepted for asynchronous processing, not
    necessarily completed.
-   `204 No Content`: Success without a response body.
-   `400 Bad Request`: Invalid request syntax or input.
-   `401 Unauthorized`: Authentication is missing or invalid.
-   `403 Forbidden`: Caller is authenticated but not permitted.
-   `404 Not Found`: Resource does not exist or is intentionally
    concealed.
-   `409 Conflict`: Conflicts with current resource state.
-   `422 Unprocessable Content`: Syntactically valid but semantically
    invalid content, where adopted by the API.
-   `429 Too Many Requests`: Rate limit exceeded.
-   `500 Internal Server Error`: Unexpected server failure.
-   `502/503/504`: Gateway/upstream failure, service unavailable, or
    gateway timeout.

Use status codes consistently and document the error contract.

## Q42. How would you design a REST endpoint to create an order?

Example:

``` http
POST /api/v1/orders
Content-Type: application/json
Idempotency-Key: 8b2c... 
```

``` json
{
  "customerId": "C123",
  "items": [
    {"productId": "P10", "quantity": 2}
  ]
}
```

A robust implementation validates the payload, authenticates the caller,
checks authorization, calculates prices on the server, persists the
order in a transaction, and returns `201 Created` with an order ID or
`Location`.

For payment/order workflows, idempotency keys can help prevent duplicate
creation when clients retry after timeouts. Store the key and result
with suitable uniqueness and retention rules.

## Q43. How do you implement pagination, sorting, and filtering?

A simple contract:

``` http
GET /api/v1/orders?page=0&size=20&sort=createdAt,desc&status=PAID
```

Validate page size and permitted sort fields. Offset pagination is
simple but can become inefficient or unstable for deep pages and
frequently changing datasets. Cursor/keyset pagination can be more
efficient for large ordered datasets, provided the cursor uses a stable
ordering.

Never concatenate untrusted sort/filter input into SQL. Map allowed API
fields to known query expressions.

## Q44. How should an API be secured?

Use layered controls: - TLS for transport security. - Authentication
using an appropriate mechanism, such as OAuth 2.0/OIDC where
applicable. - Authorization checks at resource and operation level. -
Input validation and output minimization. - Rate limiting and abuse
detection. - Secure secret handling and key rotation. - Audit logging
without sensitive payload leakage. - Dependency patching and security
testing.

CORS is a browser policy, not a substitute for authentication or
authorization.

## Q45. What is the difference between authentication and authorization?

**Authentication** answers "Who are you?"\
**Authorization** answers "What are you allowed to do?"

A valid token does not automatically mean the caller may access every
customer or order. Enforce object-level authorization, such as verifying
that the authenticated user is entitled to access order `123`.

## Q46. How do you make API changes without breaking clients?

Prefer additive changes where possible: new optional fields, new
endpoints, and tolerant readers. Avoid silently changing the meaning or
type of existing fields. Use versioning when a breaking contract change
is unavoidable, publish a deprecation plan, measure client usage, and
provide migration documentation.

Also consider enum evolution, nullability, date/time formats, pagination
semantics, and error response compatibility.

------------------------------------------------------------------------

# 7. Microservices

## Q47. What is a microservice?

A microservice is a small, independently deployable service organized
around a business capability. It typically owns a clear API and data
responsibilities and can be deployed and scaled independently.

Microservices add distributed-systems costs: network failure, latency,
data consistency challenges, observability needs, deployment
coordination, and operational overhead. A modular monolith can be a
better choice when independent deployment or scaling is not needed.

## Q48. How should services communicate?

-   **Synchronous:** HTTP/REST or gRPC; useful when the caller needs an
    immediate response.
-   **Asynchronous:** Kafka or another message broker; useful for
    event-driven workflows, buffering, and decoupling.

Do not use asynchronous messaging merely to avoid designing APIs. Choose
based on latency, coupling, failure handling, throughput, ordering, and
consistency requirements.

## Q49. What is service discovery?

Service discovery lets services locate healthy instances dynamically
rather than hardcoding addresses. It may be provided by Kubernetes
DNS/services, a platform load balancer, or a dedicated registry.

In a container platform, service names and platform routing may be
enough. Avoid adding a separate discovery system without a concrete
need.

## Q50. How do you handle failures between microservices?

Use timeouts, bounded retries, circuit breakers where appropriate,
bulkheads, rate limits, and fallbacks only when semantically safe.

-   Set timeouts for every network call.
-   Retry transient failures only; use exponential backoff and jitter.
-   Avoid retrying non-idempotent operations unless they are protected
    by idempotency.
-   Prevent retry storms and cascading failures.
-   Propagate correlation/trace IDs.
-   Define graceful degradation and clear error behavior.

A circuit breaker can stop repeatedly calling an unhealthy dependency,
but it does not fix the underlying failure.

## Q51. What is a saga pattern?

A saga coordinates a business transaction across multiple services using
a sequence of local transactions. If a later step fails, compensating
actions may undo the business effect of earlier steps.

Example: Order created → inventory reserved → payment authorized. If
payment fails, the workflow may release the inventory reservation and
mark the order as failed.

Compensation is not always a literal rollback. A refund, cancellation,
or notification may be a new business action with its own failure cases.
Make each step observable and preferably idempotent.

## Q52. How do you manage data consistency across microservices?

Each service should generally own its data and expose it through
APIs/events rather than sharing one database schema as an unrestricted
integration point.

Patterns include: - Transactional outbox to publish events reliably with
local database changes. - Idempotent consumers. - Sagas for
multi-service workflows. - Eventual consistency and read models. -
Reconciliation jobs for detecting and repairing discrepancies.

Distributed two-phase commit is often avoided because it increases
coupling and operational complexity. Choose consistency guarantees
according to business requirements.

## Q53. What is the transactional outbox pattern?

The application writes its business change and an event record in the
same local database transaction. A separate publisher reads unsent
outbox rows and publishes them to Kafka. After successful publication,
it records progress.

This avoids the dual-write failure where a database transaction succeeds
but event publication fails---or the reverse.

The publisher can publish duplicates if it crashes after publishing but
before recording success. Therefore, consumers should be idempotent.
CDC-based outbox publishing is another common implementation.

## Q54. How do you observe a microservices system?

Use: - **Logs:** Detailed event records with correlation/trace IDs. -
**Metrics:** Rates, errors, latency, saturation, queue depth, and
business counters. - **Distributed traces:** End-to-end request paths
across services. - **Health signals:** Readiness and liveness. -
**Alerts:** Actionable conditions tied to user impact or service-level
objectives.

Monitor both technical health and business outcomes. A service can be
"up" while processing orders incorrectly or falling behind on events.

------------------------------------------------------------------------

# 8. Apache Kafka --- Basic to Advanced

## Q55. What is Apache Kafka?

Kafka is a distributed event-streaming platform. Producers write records
to topics; brokers store and serve them; consumers read records. Kafka
supports durable event pipelines, stream processing, and decoupled
services.

Typical flow:

``` text
Order Service (producer)
        |
        v
Kafka topic: orders
        |
        v
Inventory Service (consumer group)
        |
        v
Inventory database
```

Kafka is not simply a traditional task queue. Records are retained
according to topic configuration, and multiple consumer groups can
independently read the same topic.

## Q56. Explain brokers, topics, partitions, and records.

-   **Broker:** A Kafka server.
-   **Topic:** A named stream of records.
-   **Partition:** An ordered, append-only log within a topic.
-   **Record:** A key, value, timestamp, and optional headers.
-   **Offset:** The record's position within a partition.
-   **Replication factor:** Number of replicas maintained for each
    partition.

Ordering is guaranteed within a partition, not across all partitions of
a topic.

## Q57. Why does Kafka use partitions?

Partitions enable parallel reads/writes and distribute storage and
traffic across brokers. A topic with more partitions can support more
consumer parallelism, subject to key distribution, broker resources, and
processing capacity.

Trade-offs: - More partitions increase metadata and operational
overhead. - Partition count can affect key-to-partition mapping and
ordering assumptions. - A hot key can overload one partition even when
the topic has many partitions.

Choose partition count using expected throughput, message size, consumer
parallelism, retention, and growth---not an arbitrary large number.

## Q58. How does Kafka key-based partitioning work?

A producer typically selects a partition based on the record key when a
key is present, subject to the configured partitioner. Records with the
same key are normally routed to the same partition under a stable
partitioning setup.

Example: use `orderId` as the key when all events for an order must be
ordered. Using a random key can spread load but loses per-order
ordering. A key with highly skewed traffic can create a hot partition.

Increasing a topic's partition count may change the partition selected
for a given key, so assess ordering and stateful-consumer implications
before changing it.

## Q59. What is a consumer group?

Consumers with the same `group.id` share partition assignments. Each
partition is assigned to at most one active consumer in a group at a
time, while different groups can read the same topic independently.

Example: a topic has 6 partitions. - One consumer in a group can own all
6 partitions. - Three consumers may own roughly 2 each. - Six consumers
may each own one. - More than six consumers in that group means some are
idle for that topic.

The exact assignment depends on the assignor and subscription pattern.

## Q60. What is a Kafka offset?

An offset identifies a record's position within one partition. Consumers
track progress by committing offsets.

-   **Auto-commit:** Kafka client periodically commits offsets, which is
    simple but may commit progress before processing is safely complete.
-   **Manual commit:** The application commits when its processing logic
    considers the records complete.

If a consumer commits before durable processing finishes, a crash can
lose work from the application's perspective. If it processes
successfully but crashes before committing, records may be processed
again.

## Q61. Explain at-most-once, at-least-once, and exactly-once processing.

-   **At-most-once:** A record is not processed more than once, but some
    work may be lost.
-   **At-least-once:** Work is retried until acknowledged/committed, so
    duplicates are possible.
-   **Exactly-once:** A carefully defined processing result is committed
    once within supported transactional boundaries.

Kafka transactions can provide exactly-once semantics for Kafka-to-Kafka
processing when configured correctly. They do not automatically make
arbitrary external database updates exactly once. For database sinks,
use idempotency, deduplication, transactional integration patterns, or
connector features appropriate to the system.

## Q62. How do you implement reliable Kafka consumer processing?

A common manual-commit approach: 1. Poll records. 2. Process each record
safely. 3. Persist the result or perform an idempotent operation. 4.
Commit offsets only after successful processing of the corresponding
records.

Be careful with batches and multiple partitions: committing a high
offset for a partition implies earlier records in that partition are
considered complete. If records complete out of order, coordinate
commits carefully.

Do not perform slow work on a consumer thread indefinitely; poll timing
and rebalance behavior must be considered. Use bounded worker pools and
a safe partition/offset completion strategy if processing concurrently.

## Q63. What causes consumer lag, and how do you troubleshoot it?

Consumer lag is a measure of how far consumer progress trails the latest
available offsets, commonly computed per partition and aggregated. The
exact metric definition depends on the monitoring system.

Possible causes: - Consumer processing is slower than production. - A
downstream database/API is slow. - Consumer count is too low relative to
partitions. - Uneven key distribution creates hot partitions. - Frequent
rebalances or long garbage-collection pauses. - Large records,
inefficient deserialization, or excessive logging. - Producer traffic
spikes.

Troubleshooting sequence: 1. Check lag trend by partition and consumer
group. 2. Compare production rate and consumption rate. 3. Check
processing latency, errors, retries, and downstream latency. 4. Inspect
partition skew and consumer assignments. 5. Check rebalance frequency,
GC, CPU, memory, and network. 6. Scale consumers only if partition
parallelism and downstream capacity permit it.

Lag is a symptom, not a root cause.

## Q64. What is a Kafka rebalance?

A rebalance changes partition ownership among consumers in a group when
members join/leave, subscriptions change, or failures/timeouts occur.

Rebalances temporarily affect consumption and can contribute to lag.
Frequent rebalances may be caused by crashes, unstable deployments, long
processing, missed heartbeats, or inappropriate poll settings.

Mitigation: - Keep polling within the configured maximum interval. - Use
graceful shutdown. - Configure session and heartbeat settings based on
client/version behavior. - Avoid long blocking work on the poll
thread. - Consider cooperative-sticky assignment where supported and
suitable. - Monitor rebalance rate and duration.

Do not tune timeouts blindly; larger values can slow failure detection.

## Q65. Explain `session.timeout.ms`, `heartbeat.interval.ms`, and `max.poll.interval.ms`.

-   `session.timeout.ms`: How long the group coordinator may wait
    without heartbeats before considering a consumer failed, subject to
    broker/client configuration.
-   `heartbeat.interval.ms`: How often the consumer sends heartbeats in
    applicable group protocols; typically lower than the session
    timeout.
-   `max.poll.interval.ms`: Maximum interval between calls to `poll()`
    before the consumer can be considered unable to make progress and
    trigger reassignment.

Exact behavior depends on Kafka client and group protocol version. The
key distinction: heartbeats show liveness; `poll()` cadence shows the
application is making progress through the consumer loop.

## Q66. What is the difference between Kafka retention and compaction?

-   **Time/size retention:** Old log segments can be deleted based on
    configured age or size.
-   **Log compaction:** Kafka retains the latest known value for each
    key over time, subject to compaction rules; tombstones represent
    deletes.

Compaction is useful for changelog/state topics and latest-state
snapshots. It does not mean a topic instantly contains only one record
per key; compaction runs asynchronously and old records may remain until
processed.

## Q67. How do you choose a partition key?

Choose a key that: - Preserves the ordering required by the business. -
Distributes traffic reasonably evenly. - Matches the state or entity
being processed. - Avoids a single extremely hot key.

Examples: - `orderId` for per-order event order. - `customerId` for
per-customer sequence, if customer traffic is balanced enough. - No key
or a custom strategy when ordering by entity is not required and load
distribution matters more.

There is no universally best key. The choice is a business-ordering and
load-distribution decision.

## Q68. What is a dead-letter topic (DLT/DLQ)?

A dead-letter topic stores records that cannot be processed after the
configured retry strategy. It should preserve useful metadata, such as
original topic, partition, offset, exception category, and processing
timestamp, while avoiding sensitive data leakage.

Define: - Which errors are retryable. - Retry count and backoff. - Who
monitors the DLT. - How records are inspected and replayed. - How
duplicate side effects are prevented during replay.

A DLT is not a substitute for fixing a persistent bug or invalid schema.

## Q69. How do you handle schema evolution in Kafka?

Use a documented event contract and a schema strategy such as Avro,
Protobuf, or JSON Schema with a compatible registry/tooling setup. Apply
compatibility rules deliberately: - Add optional/defaulted fields when
compatible with old consumers. - Avoid changing a field's meaning or
type without a migration plan. - Test old producer/new consumer and new
producer/old consumer combinations as required. - Keep event names and
versions meaningful.

Schema compatibility depends on the format, registry policy, and
reader/writer configuration; "adding a field is always safe" is not
universally true.

## Q70. How do you improve Kafka producer performance and reliability?

Consider: - `acks=all` and appropriate replication/minimum in-sync
replica settings for durability requirements. - Idempotent producer
support to reduce duplicates caused by retries. - Batching
(`batch.size`) and linger (`linger.ms`) to improve throughput where
latency permits. - Compression such as LZ4 or Zstandard when supported
and beneficial. - Correct delivery timeout and retry settings. -
Monitoring request latency, error rate, batch size, and broker health.

Do not trade durability for speed without understanding the loss risk.
Defaults and exact property behavior vary by Kafka client version.

## Q71. What does replication factor mean, and what is ISR?

The **replication factor** is the number of replicas of a partition. One
replica is leader for client traffic; followers replicate the log.

**ISR (in-sync replicas)** is the set of replicas considered caught up
enough to be in sync under Kafka's rules. With `acks=all`, the leader
waits for acknowledgement from the current ISR, subject to
configuration. `min.insync.replicas` can require a minimum ISR size for
writes.

Example: replication factor 3 with minimum ISR 2 may continue accepting
durable writes when one replica is unavailable, but reject writes if the
ISR falls below the required minimum. This is a durability/availability
trade-off.

## Q72. How do you scale Kafka consumers?

1.  Determine partitions per topic and consumer-group assignment.
2.  Add consumers up to useful partition parallelism.
3.  Verify the downstream system can handle more concurrent work.
4.  Identify hot partitions and key skew.
5.  Tune batch sizes and processing time.
6.  Consider adding partitions only after evaluating ordering and key
    mapping.
7.  Track lag, throughput, latency, errors, and rebalances.

More consumers do not always mean more throughput: consumers beyond the
available partitions may sit idle, and downstream capacity may be the
bottleneck.

## Q73. How would you design an order-event flow with Kafka?

Example flow: 1. Order service validates and saves the order plus an
outbox event in one database transaction. 2. An outbox publisher sends
`OrderCreated` keyed by `orderId`. 3. Inventory service consumes the
event, reserves inventory idempotently, and records processed event IDs.
4. Inventory emits `InventoryReserved` or `InventoryRejected`. 5. Order
workflow reacts to the result and progresses or compensates. 6. Retries,
DLT handling, event IDs, tracing, and reconciliation support operations.

Define event contracts, ownership, timeout policy, duplicate behavior,
and recovery procedures before coding.

------------------------------------------------------------------------

# 9. NoSQL Databases

## Q74. What is NoSQL, and when should you use it?

NoSQL covers several database models beyond traditional relational
tables, including document, key-value, wide-column, and graph databases.
They are not all interchangeable.

Use a NoSQL database when its data model, access patterns, scaling
characteristics, or availability model fits the application. A
relational database may still be the better choice when relational
constraints, joins, and multi-row transactions dominate.

## Q75. Compare MongoDB, Couchbase, and Cassandra.

  -------------------------------------------------------------------------
  Database          Common model      Strengths /       Important
                                      common fit        considerations
  ----------------- ----------------- ----------------- -------------------
  MongoDB           Document          Flexible          Model documents
                                      JSON-like         around access
                                      documents,        patterns; watch
                                      indexes, rich     document growth and
                                      document queries  transaction/query
                                                        cost

  Couchbase         Key-value +       Low-latency       Design keys and
                    document          key-value access, indexes carefully;
                                      JSON documents,   understand cluster
                                      SQL++ query       and bucket
                                      capability        configuration

  Cassandra         Wide-column       Distributed       Data modeling is
                                      writes, high      query-driven;
                                      availability,     partition-key
                                      large-scale       design and
                                      partitioned       tombstones matter
                                      workloads         
  -------------------------------------------------------------------------

The right choice depends on consistency requirements, workload,
operational expertise, cloud/platform constraints, and cost.

## Q76. What is eventual consistency?

Eventual consistency means replicas may temporarily return different
values, but if updates stop and replication proceeds, they are expected
to converge. It can improve availability and scalability but may expose
stale reads.

Ask: - How stale can data be? - Which operations require
read-your-writes? - What conflict resolution is used? - Which
consistency level is required for critical operations?

Do not assume every NoSQL database or every operation uses the same
consistency model.

## Q77. Explain partition keys and hot partitions in Cassandra.

Cassandra uses a partition key to determine where data is stored. Rows
with the same partition key are colocated within a partition.

A good partition key distributes data and traffic while supporting the
queries. A poor key can create oversized partitions or concentrate
requests on a small subset of nodes.

For example, using a constant country code as the only partition key for
a high-volume global event table can create a hot partition. A composite
strategy may distribute load, but the exact design should follow
required query patterns and retention needs.

## Q78. Why is data modeling query-driven in Cassandra?

Cassandra is optimized for known query patterns rather than arbitrary
joins. Tables are often designed to serve particular queries, and
denormalization is common.

Before creating a table, define: - Required query and sort order. -
Partition key and clustering columns. - Expected rows per partition. -
Data volume and time range. - TTL/retention behavior. - Consistency and
write/read patterns.

Avoid treating Cassandra like a relational database and expecting
unrestricted joins or ad hoc filtering to perform well.

## Q79. What are indexes in document databases, and why do they matter?

An index lets the database find matching records without scanning every
document/row. Indexes improve reads for supported query patterns but
consume memory/storage and add write/update overhead.

Use query plans and workload metrics to verify index effectiveness.
Compound index field order matters; an index that looks similar to a
query may not efficiently support its filters and sort. Avoid creating
indexes without understanding their read benefit and write cost.

## Q80. How do you handle duplicate requests in a NoSQL-backed service?

Use a stable idempotency key or unique business identifier, enforce
uniqueness where the database supports it, and make updates conditional
or atomic when required. Record enough state to recognize a repeated
request and return the original outcome.

A check-then-insert sequence can race under concurrency. Prefer a
database-enforced unique constraint, compare-and-set/conditional write,
or atomic operation suited to the chosen database.

## Q81. How do you choose between a relational database and NoSQL?

Evaluate: - Transaction and consistency needs. - Query patterns and join
requirements. - Data shape and evolution. - Expected scale and traffic
distribution. - Read/write latency and availability goals. - Operational
skills, backup/recovery, and cost. - Reporting and analytics needs.

Avoid choosing NoSQL only because a system is called "microservices" or
because it is perceived as automatically faster.

------------------------------------------------------------------------

# 10. Splunk and Production Troubleshooting

## Q82. What is Splunk?

Splunk is a platform used to ingest, search, analyze, and visualize
machine-generated data such as application logs, infrastructure logs,
and security events. Teams use it for troubleshooting, monitoring,
dashboards, and alerting.

A common workflow is to search a time range, filter events, extract
fields, aggregate results, visualize patterns, and create an alert when
a meaningful condition occurs.

## Q83. What is SPL?

SPL (Search Processing Language) is Splunk's search language. A search
is typically a pipeline of commands separated by `|`.

Example:

``` spl
index=application sourcetype=app:json level=ERROR
| stats count by service, errorCode
| sort - count
```

This searches matching error events, counts them by service and error
code, and sorts the largest counts first. Index names and field names
depend on the environment's ingestion configuration.

## Q84. How would you find errors for a particular service?

``` spl
index=application service="order-service" level="ERROR"
| timechart span=5m count
```

This displays error counts over five-minute intervals. Narrow the time
range first, then add a correlation ID, endpoint, error code, or
deployment version to isolate the issue.

Use the fields that actually exist in your Splunk events; field
extraction varies by source and ingestion setup.

## Q85. How do you find the slowest API endpoints?

If logs include a numeric `duration_ms` field:

``` spl
index=application sourcetype=app:json
| stats count avg(duration_ms) p95(duration_ms) p99(duration_ms) by endpoint
| sort - p95(duration_ms)
```

Percentiles are often more useful than averages because a small number
of slow requests can be hidden by the mean. Validate that `duration_ms`
is numeric and consistently measured.

## Q86. How do you trace one request across microservices in Splunk?

Use a correlation ID or trace ID generated at the entry point and
propagated through service calls and message headers.

``` spl
index=application correlationId="abc-123"
| sort _time
| table _time service level message correlationId traceId
```

If a Kafka consumer processes the request asynchronously, propagate the
trace/correlation context in message headers or application metadata. Do
not use sensitive personal information as a correlation identifier.

## Q87. How would you investigate a sudden increase in errors?

1.  Set a time range around the incident and compare it with a baseline.
2.  Group errors by service, endpoint, exception, host/pod, and
    deployment version.
3.  Check whether latency and traffic changed at the same time.
4.  Correlate application logs with Kafka lag, database latency, CPU,
    memory, and upstream errors.
5.  Identify the first failing dependency or deployment change.
6.  Confirm whether the issue affects all traffic or a subset.
7.  Validate the fix and monitor recovery.

Example:

``` spl
index=application level=ERROR
| stats count by service, exception, version
| sort - count
```

A log count alone does not establish root cause. Correlate evidence
across metrics, traces, and changes.

## Q88. What makes a good production log?

Prefer structured logs with timestamp, severity, service name,
environment, version, request/trace ID, operation, duration, outcome,
and stable error code.

Avoid: - Passwords, tokens, secrets, or unnecessary personal data. -
Logging the same exception repeatedly at every layer. - Huge
request/response bodies by default. - Unbounded high-cardinality metric
labels. - Vague messages such as "Something went wrong."

Logs should help answer what failed, where, when, and which request was
affected.

## Q89. What is the difference between logs, metrics, and traces?

-   **Logs:** Individual event details.
-   **Metrics:** Numeric measurements over time, suitable for alerting
    and trend analysis.
-   **Traces:** A distributed request's path across services and
    operations.

Use metrics to detect the problem, traces to locate latency/failure
across service boundaries, and logs to inspect event details.
Correlation and trace IDs help connect them.

------------------------------------------------------------------------

# 11. End-to-End Design and Scenario Questions

## Q90. A Spring Boot API is slow. How would you troubleshoot it?

**Strong answer structure:** 1. Quantify the symptom: p50/p95/p99
latency, error rate, affected endpoints, start time, and customer
impact. 2. Check recent releases, configuration changes, and traffic
spikes. 3. Use tracing to split time among application code, database,
Kafka, and downstream APIs. 4. Check JVM CPU, GC pauses, thread pools,
connection pools, and saturation. 5. Inspect database query
plans/indexes and connection-pool waits. 6. Check Kafka lag or
synchronous message operations. 7. Reproduce under representative load
and change one variable at a time. 8. Validate with before/after
measurements and add regression coverage.

Do not start by increasing every timeout or resource limit. Identify the
bottleneck first.

## Q91. A Kafka consumer's lag grows continuously. What do you do?

-   Verify production and consumption rates.
-   Break lag down by partition to find skew.
-   Check consumer processing latency, exceptions, retries, and
    downstream database/API latency.
-   Inspect rebalances, poll behavior, GC, CPU, and thread contention.
-   Determine whether adding consumers can help based on partition
    count.
-   Scale downstream dependencies if they are the limiting factor.
-   Tune batch and processing behavior only after measuring.
-   Define a safe replay or recovery plan if the backlog is very large.

If a single key causes a hot partition, simply adding consumers may not
solve the problem.

## Q92. An event is processed twice. How do you prevent duplicate business effects?

Assume at-least-once delivery unless the full processing boundary proves
otherwise. Include a stable event ID and make the consumer idempotent.

For example, a database table can record processed event IDs with a
unique constraint in the same transaction as the business update. If the
same event arrives again, the unique constraint or stored processing
state prevents the business effect from happening twice.

For external payments, use the provider's idempotency mechanism where
available. Kafka producer idempotence alone does not guarantee an
external database or API is updated exactly once.

## Q93. A downstream service is unavailable. How should your service behave?

-   Apply a short, explicit timeout.
-   Retry only transient failures, with bounded exponential backoff and
    jitter.
-   Avoid retrying non-idempotent requests without protection.
-   Use a circuit breaker or bulkhead where it improves isolation.
-   Return a clear error or accepted/asynchronous response according to
    the API contract.
-   Avoid holding database transactions or scarce threads while waiting.
-   Emit metrics, structured logs, and traces.
-   Recover queued work safely and monitor for a retry storm.

A fallback is appropriate only if the business can tolerate its
semantics---for example, showing cached data may be acceptable for a
product catalog but not for confirming a payment.

## Q94. How would you design a resilient order-processing service?

**One possible architecture:**

``` text
Client
  |
  v
API Gateway / Load Balancer
  |
  v
Spring Boot Order Service
  |  \ 
  |   \--> Database transaction: order + outbox event
  |
  v
Outbox Publisher --> Kafka: OrderCreated
                         |
             +-----------+-----------+
             |                       |
             v                       v
      Inventory Service        Notification Service
             |
             v
     Inventory database
             |
             v
 Kafka: InventoryReserved / InventoryRejected
             |
             v
       Order workflow
```

Key design decisions: - Validate and authorize the request. - Use
idempotency keys for client retries. - Write order and outbox row
atomically. - Partition events by `orderId` when per-order ordering is
needed. - Make consumers idempotent. - Use explicit retry and DLT
policies. - Model compensation for failures. - Add tracing, metrics,
structured logs, and alerts. - Define recovery, replay, and
reconciliation procedures.

This architecture favors eventual consistency across services; it should
not be presented as a single ACID transaction spanning all services.

## Q95. How would you deploy and operate a Spring Boot service?

A practical checklist: - Build a versioned artifact and run automated
tests. - Scan dependencies and container images. - Externalize
configuration and protect secrets. - Configure resource requests/limits
and connection pools. - Provide readiness and liveness probes. - Use
graceful shutdown so in-flight requests and Kafka processing can finish
safely. - Apply rolling/canary deployment where appropriate. - Monitor
error rate, latency, throughput, JVM, database pools, Kafka lag, and
restarts. - Keep rollback and database/event-schema compatibility
plans. - Verify backup and recovery requirements.

A successful deployment means more than a green build: verify runtime
health and business behavior.

## Q96. How do you explain a difficult production incident in an interview?

Use the STAR structure: - **Situation:** Describe the system and
customer/business impact. - **Task:** State your responsibility. -
**Action:** Explain evidence gathered, tools used, hypotheses tested,
communication, and mitigation. - **Result:** Quantify recovery or
improvement where possible. - **Learning:** Explain the permanent fix,
tests, alerting, or runbook added.

Be accurate about your personal contribution. Do not invent metrics. A
good incident answer shows disciplined diagnosis and prevention, not
only that you restarted a service.

------------------------------------------------------------------------

# 12. Quick Revision Checklist

## Java

-   [ ] `==` versus `equals()`
-   [ ] `equals()` / `hashCode()` contract
-   [ ] Collections complexity and thread safety
-   [ ] Java 8 lambdas, functional interfaces, streams, `Optional`,
    `CompletableFuture`
-   [ ] Java 11 HTTP Client, `String` methods, `Files` methods
-   [ ] `synchronized` versus `volatile` versus atomics
-   [ ] Heap, stack, GC, thread dumps, heap dumps
-   [ ] Java 8 → 11 migration issues

## Spring Boot and REST

-   [ ] Constructor injection and bean lifecycle basics
-   [ ] Controller/service/repository separation
-   [ ] Validation and global exception handling
-   [ ] Transactions and proxy/self-invocation caveat
-   [ ] Actuator health and metrics security
-   [ ] HTTP methods, status codes, idempotency
-   [ ] Authentication versus authorization
-   [ ] Pagination, API versioning, request validation

## Microservices

-   [ ] Synchronous versus asynchronous communication
-   [ ] Timeouts, retries, circuit breakers, bulkheads
-   [ ] Saga and compensating actions
-   [ ] Transactional outbox
-   [ ] Eventual consistency and idempotent consumers
-   [ ] Logs, metrics, traces, SLOs

## Kafka

-   [ ] Topic, partition, broker, offset, replication
-   [ ] Consumer groups and partition parallelism
-   [ ] Offset commits and delivery semantics
-   [ ] Rebalances and poll/heartbeat settings
-   [ ] Consumer lag diagnosis
-   [ ] Partition keys, ordering, hot partitions
-   [ ] Retry topics / DLT and replay safety
-   [ ] Schema evolution
-   [ ] Producer reliability, ISR, `acks`, idempotence

## NoSQL

-   [ ] MongoDB vs Couchbase vs Cassandra
-   [ ] Query-driven data modeling
-   [ ] Partition-key design and hot partitions
-   [ ] Index trade-offs
-   [ ] Consistency and atomic operations
-   [ ] Idempotency and duplicate prevention

## Splunk / Production

-   [ ] Search by index, service, time, level, trace ID
-   [ ] `stats`, `timechart`, `sort`, `table`
-   [ ] p95/p99 latency and error-rate analysis
-   [ ] Correlate logs with metrics and traces
-   [ ] Structured logging and sensitive-data protection

------------------------------------------------------------------------

# Suggested Interview Answer Framework

For most technical questions, answer in this order:

1.  **Definition:** Explain the concept in one or two sentences.
2.  **Mechanism:** Explain how it works.
3.  **Example:** Give a short code or production example.
4.  **Trade-off:** Explain when it helps and what it costs.
5.  **Production concern:** Mention failure modes, monitoring, security,
    or scaling when relevant.

For scenario questions, state assumptions, identify evidence, explain
the diagnostic sequence, describe the fix, and explain how you would
prevent recurrence.

**Version note:** Examples are intended as interview-preparation
material. APIs and configuration defaults can vary by Java, Spring Boot,
Kafka client/broker, and database version. Verify version-specific
details against the versions used by the target project.
