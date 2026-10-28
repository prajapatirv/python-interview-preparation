---
id: target-persistent-java-spring
title: Target company, Persistent Systems: core Java, Spring Boot and microservices technical rounds
stack: java
skill: spring-boot
---
Part of the **target-company section** (hub: `../target-companies/README.md`, section "Persistent Systems").
Candidates describe two or three technical rounds: **core Java and Java 8** (wrapper classes, HashMap internals,
functional interfaces, default/static methods, streams, a singleton, a multithreading question), then **Spring Boot
and microservices** (annotations, error handling, JPA, scheduler, connecting to two databases, circuit breaker,
service communication, OAuth), often with a coding problem where the interviewer pushes for a more efficient solution.

HashMap internals is answered in depth in bank 83 Q1 and SQL joins in bank 29; this file covers the rest.
Every answer has a **120-second** point-by-point version (*How I answer it*) and a **60-second answer**.

### Q1 [fresher] What are wrapper classes and autoboxing, and why does Integer == sometimes fail?
tags: wrapper-classes, autoboxing, unboxing, integer-cache, equals, nullpointerexception, core-java, persistent

**Start here: the concepts**
- Each primitive has a **wrapper** object: `int -> Integer`, `long -> Long`, `boolean -> Boolean`, and so on. Collections and generics need objects, so they use wrappers.
- **Autoboxing** converts `int` to `Integer` automatically; **unboxing** does the reverse.
- `==` on objects compares **references**, not values.

**The live scenario (functional requirement)**
*FR: "Flag orders whose quantity equals the reserved quantity."* The check `order.getQty() == reservation.getQty()`
(both `Integer`) worked in tests with small numbers and failed in production for quantities above 127.

**What the interviewer is really checking**
That you know the Integer cache, the unboxing NPE, and the performance cost of boxing in hot loops.

**How I answer it** (120-second answer, point by point)
1. **Why wrappers exist:** generics and collections (`List<Integer>`), nullability (`null` = "not provided"), and utility methods (`Integer.parseInt`, `compare`).
2. **The cache:** `Integer.valueOf` (used by autoboxing) caches **-128 to 127**. Two boxed 100s are the same object, so `==` is true; two boxed 1000s are different objects, so `==` is false. That was the production bug.
3. **Fix:** compare with `equals()` or `Objects.equals(a, b)` (null-safe), or unbox deliberately when both are known non-null.
4. **Unboxing NPE:** `int total = map.get(key);` throws `NullPointerException` if the key is missing. Use `getOrDefault`, or keep it as `Integer` and check.
5. **Performance:** `Long sum = 0L; for (...) sum += x;` creates millions of objects. Use primitives, or `IntStream`/`LongStream` instead of `Stream<Integer>`.
6. **Immutability:** wrappers are immutable and final, so they are safe as map keys.

**Trade-offs and what can go wrong**
- `Boolean`, `Byte`, `Short`, `Character` (0-127) and `Long` also cache small values, which makes `==` bugs even harder to spot.
- `new Integer(5)` is deprecated (for removal); always use `valueOf` or autoboxing.

**Follow-ups to expect**
- *Can you change the cache range?* -> Only the upper bound for Integer, with `-XX:AutoBoxCacheMax`; never rely on it.
- *Is `int` or `Integer` better in an entity?* -> `Integer`/`Long` for nullable columns and ids before persist; `int` for required values.

**60-second answer**
"Wrapper classes like Integer and Long let primitives be used in collections and generics, and they can be null.
Autoboxing converts automatically using valueOf, which caches values from -128 to 127. So comparing two boxed Integers
with == works for small numbers and silently fails above 127, because == compares references. I had exactly that bug in
production, and the fix is equals or Objects.equals. The other traps are an NPE when unboxing a null, like a missing map
value, and the cost of boxing in hot loops, where I use primitives or IntStream instead."

### Q2 [mid] What is a functional interface, and why did Java 8 add default and static methods to interfaces?
tags: functional-interface, lambda, default-method, static-method, diamond-problem, java8, core-java, persistent

**Start here: the concepts**
- A **functional interface** has exactly **one abstract method**, so a lambda or method reference can implement it (`Runnable`, `Comparator`, `Function`, `Predicate`, `Supplier`, `Consumer`).
- A **default method** has a body in the interface; implementing classes inherit it.
- A **static method** in an interface is a helper called on the interface itself (`Comparator.comparing(...)`).

**The live scenario (functional requirement)**
*FR: "Apply different discount rules (festival, loyalty, first order) to a cart."* Each rule became a
`DiscountRule` functional interface implemented by lambdas, and the chain was built with a default method `andThen`.

**What the interviewer is really checking**
That you know why default methods exist (evolving interfaces without breaking implementers), the diamond conflict rule,
and the common built-in functional interfaces.

**How I answer it** (120-second answer, point by point)
1. **Functional interface:** one abstract method; `@FunctionalInterface` makes the compiler enforce it. Default, static and `Object` methods don't count.
2. **Built-ins I use daily:** `Function<T,R>`, `Predicate<T>`, `Supplier<T>`, `Consumer<T>`, `BiFunction`, `UnaryOperator`, plus primitive variants (`IntPredicate`) to avoid boxing.
3. **Why default methods:** Java 8 needed to add `stream()`, `forEach`, `removeIf` to `Collection` without breaking every existing implementation. Default methods made that **backward compatible**.
4. **Why static methods:** factory/helper methods live with the interface (`Comparator.comparing`, `List.of`) instead of a separate utility class.
5. **Diamond conflict:** if a class implements two interfaces with the same default method, it **must override** it and can call one explicitly: `A.super.hello()`. Class methods always win over interface defaults.
6. **Example:**
   ```java
   @FunctionalInterface
   interface DiscountRule {
       BigDecimal apply(Cart cart, BigDecimal price);
       default DiscountRule andThen(DiscountRule next) { return (c, p) -> next.apply(c, apply(c, p)); }
       static DiscountRule none() { return (c, p) -> p; }
   }
   ```

**Trade-offs and what can go wrong**
- Interfaces still cannot hold instance state; default methods can only use other interface methods.
- Overusing default methods turns interfaces into abstract classes in disguise; keep them small and generic.

**Follow-ups to expect**
- *Interface vs abstract class now?* -> Abstract class when you need state, constructors or protected members; interface for capabilities and multiple inheritance of type.
- *Private methods in interfaces?* -> Since Java 9, to share code between default methods.

**60-second answer**
"A functional interface has exactly one abstract method, so a lambda can implement it: Function, Predicate, Supplier,
Consumer and Comparator are the common ones, and @FunctionalInterface makes the compiler check it. Java 8 added default
methods so interfaces could evolve. That's how Collection got stream and forEach without breaking every implementation.
Static methods keep helpers with the interface, like Comparator.comparing. If two interfaces give the same default
method, the class must override it and can call A.super.method(). In a project I modelled discount rules as a functional
interface with a default andThen to chain them."

### Q3 [mid] What is the difference between map and flatMap in streams? Give a real example
tags: streams, map, flatmap, optional, collectors, java8, persistent

**Start here: the concepts**
- `map` turns **each element into one** new element: `Stream<Order> -> Stream<BigDecimal>`.
- `flatMap` turns **each element into a stream of elements** and **flattens** them into one stream: `Stream<Order> -> Stream<OrderLine>`.
- The same idea exists on `Optional`: `map` vs `flatMap` when the function already returns an `Optional`.

**The live scenario (functional requirement)**
*FR: "List every distinct SKU across today's orders."* Each order holds a list of lines.

**What the interviewer is really checking**
Whether you can explain flattening with a real nested structure and avoid `Stream<List<...>>` mistakes.

**How I answer it** (120-second answer, point by point)
1. **map, one to one:** `orders.stream().map(Order::total)` gives a `Stream<BigDecimal>`.
2. **The wrong attempt:** `orders.stream().map(Order::lines)` gives `Stream<List<OrderLine>>`: a stream of lists, not lines.
3. **flatMap, one to many, flattened:**
   ```java
   Set<String> skus = orders.stream()
       .flatMap(o -> o.lines().stream())
       .map(OrderLine::sku)
       .collect(Collectors.toSet());
   ```
4. **Optional:** `user.flatMap(User::address)` when `address()` returns `Optional<Address>`; `map` there would give `Optional<Optional<Address>>`.
5. **Java 16+ alternative:** `mapMulti` for cases where you push 0..n elements imperatively without creating small streams.
6. **Other classic uses:** words from lines (`lines.flatMap(l -> Arrays.stream(l.split(" ")))`), and flattening a `Map<K, List<V>>` into all values.

**Trade-offs and what can go wrong**
- `flatMap` creates a small stream per element; on very hot paths a loop or `mapMulti` is cheaper.
- Streams are lazy: nothing runs until a terminal operation like `collect`.

**Follow-ups to expect**
- *Intermediate vs terminal operations?* -> Intermediate (map, filter, flatMap, sorted) are lazy and return a stream; terminal (collect, forEach, reduce, findFirst) trigger execution.
- *Can you reuse a stream?* -> No; a consumed stream throws `IllegalStateException`.

**60-second answer**
"map is one to one: each element becomes exactly one new element, for example order to order total. flatMap is one to
many and flattens: each element becomes a stream, and all of them merge into one stream. To get every distinct SKU
across orders, map gives a stream of lists, which is wrong. flatMap over each order's lines, then map to SKU and collect
to a set, gives the answer. The same applies to Optional, where flatMap avoids an Optional of an Optional. On hot paths,
mapMulti or a loop avoids creating many tiny streams."

### Q4 [mid] How do you write a thread-safe singleton, and how can a singleton be broken?
tags: singleton, thread-safety, double-checked-locking, volatile, holder-idiom, enum-singleton, reflection, serialization, design-patterns, persistent

**Start here: the concepts**
- A **singleton** guarantees one instance of a class per JVM (per class loader) with a global access point.
- In a multi-threaded app, two threads can create two instances at the same time unless creation is synchronised.
- In Spring, beans are singletons **per application context** by default, so hand-written singletons are rarely needed.

**The live scenario (functional requirement)**
*FR: "One shared configuration loader reads a large rules file once."* A lazy singleton without synchronisation loaded
the file twice under startup load and two threads saw different rule versions.

**What the interviewer is really checking**
The correct idioms (holder, enum, double-checked locking with `volatile`), why `volatile` is needed, and how reflection,
serialization and cloning can break it.

**How I answer it** (120-second answer, point by point)
1. **Eager:** `private static final Config INSTANCE = new Config();` thread-safe by class initialisation; fine if creation is cheap.
2. **Holder idiom (my default for lazy):**
   ```java
   final class Config {
       private Config() { }
       private static class Holder { static final Config INSTANCE = new Config(); }
       static Config getInstance() { return Holder.INSTANCE; }
   }
   ```
   The JVM loads `Holder` on first call; class initialisation is thread-safe without locks.
3. **Double-checked locking:** check, `synchronized`, check again, and the field **must be `volatile`**, otherwise another thread can see a reference to a half-constructed object (instruction reordering).
4. **Enum singleton:** `enum Config { INSTANCE; }` is safe against reflection and serialization by design (Joshua Bloch's recommendation).
5. **How it breaks:**
   - **Reflection:** `setAccessible(true)` on the private constructor; guard by throwing if an instance already exists (or use enum).
   - **Serialization:** deserialising creates a new object; add `readResolve()` returning the instance.
   - **Cloning:** don't implement `Cloneable`, or throw in `clone()`.
   - **Multiple class loaders** (app servers) can each have one.
6. **In Spring:** I make it a `@Component` (singleton scope) and inject it, which is also easier to test.

**Trade-offs and what can go wrong**
- Singletons are global state: hard to mock and they hide dependencies. Prefer DI.
- A singleton holding mutable state must itself be thread-safe (immutable fields or concurrent collections).

**Follow-ups to expect**
- *Why volatile in DCL?* -> It prevents reordering of "assign reference" before "finish constructor" and guarantees visibility across threads.
- *Is a Spring singleton the same as GoF singleton?* -> No; one per container, not per JVM, and you can still `new` the class.

**60-second answer**
"For a lazy, thread-safe singleton I use the holder idiom: a private constructor and a static nested class holding the
instance. The JVM initialises it on first use, and class initialisation is thread-safe without locks. If someone asks for
double-checked locking, the field must be volatile, or another thread can see a half-constructed object. The safest is an
enum singleton, which also resists reflection and serialization. Otherwise reflection can call the private constructor,
deserialisation creates a copy unless you add readResolve, and clone can copy it. In Spring apps I just use a singleton
bean and inject it, because global state is hard to test."

### Q5 [mid] Multithreading question: print odd and even numbers alternately with two threads
tags: multithreading, wait-notify, synchronized, reentrantlock, condition, semaphore, coding-round, core-java, persistent

**Start here: the concepts**
- Two threads must **take turns**, so they need a shared lock and a condition to wait on.
- `wait()` releases the monitor and sleeps; `notify()/notifyAll()` wakes waiting threads. Both must be called while holding the same lock.
- Always wait **in a loop** that re-checks the condition (spurious wake-ups).

**The live scenario (functional requirement)**
A classic Persistent core-Java prompt: *"Thread A prints odd numbers, thread B prints even numbers, output must be
1, 2, 3 ... 10 in order."* Interviewers then ask for a second, cleaner version.

**What the interviewer is really checking**
Correct use of a monitor or `Condition`, the while-loop rule, and knowing higher-level alternatives.

**How I answer it** (120-second answer, point by point)
1. **Shared state:** `int counter = 1; final int max = 10;` guarded by one lock object.
2. **wait/notify version:**
   ```java
   void print(boolean odd) throws InterruptedException {
       synchronized (lock) {
           while (counter <= max) {
               while (counter <= max && (counter % 2 == 1) != odd) lock.wait();
               if (counter <= max) { System.out.println(Thread.currentThread().getName() + " " + counter++); }
               lock.notifyAll();
           }
       }
   }
   ```
   Start two threads: one calls `print(true)`, the other `print(false)`.
3. **Why `while` not `if`:** a thread can wake up spuriously or when it is not its turn; it must re-check.
4. **Cleaner alternative:** two `Semaphore`s: `odd` starts with 1 permit, `even` with 0. The odd thread `acquire`s odd, prints, `release`s even, and vice versa. No shared condition logic.
5. **Lock + Condition alternative:** `ReentrantLock` with `oddTurn` and `evenTurn` conditions, signalling exactly the other thread.
6. **Termination:** both loops stop at `max`; the final `notifyAll` makes sure the other thread wakes and exits.

**Trade-offs and what can go wrong**
- Calling `wait()` outside `synchronized` throws `IllegalMonitorStateException`.
- `notify()` instead of `notifyAll()` is fine with exactly two threads but fragile with more.
- Real systems rarely do this; say so, and mention `ExecutorService`, `CompletableFuture` and concurrent queues for real work.

**Follow-ups to expect**
- *What about three threads printing 1, 2, 3 in rotation?* -> Same pattern with `counter % 3 == id`, or three semaphores in a ring.
- *sleep vs wait?* -> `sleep` keeps the lock; `wait` releases it and needs a notify.

**60-second answer**
"I'd share a counter and one lock. Each thread loops while the counter is under the max. It waits in a while loop until
it's its turn, by parity, then prints, increments, and calls notifyAll. The while loop matters because of spurious
wake-ups, and wait and notify must be inside synchronized on the same lock. A cleaner version uses two semaphores: odd
starts with one permit and even with zero, and each thread acquires its own and releases the other's. A ReentrantLock
with two conditions also works. In real code I'd use executors and concurrent queues, not raw wait and notify."

### Q6 [mid] How do you handle errors globally in a Spring Boot REST API?
tags: exception-handling, controlleradvice, exceptionhandler, problem-details, rfc9457, validation, rest-api, spring-boot, persistent

**Start here: the concepts**
- `@RestControllerAdvice` + `@ExceptionHandler` methods catch exceptions from all controllers in one place.
- **Problem Details** (RFC 9457, Spring 6 `ProblemDetail`) is the standard JSON error body: `type`, `title`, `status`, `detail`, `instance`.
- Services throw **domain exceptions**; only the advice decides HTTP status codes.

**The live scenario (functional requirement)**
*FR: "Partners integrate with our booking API and need consistent, machine-readable errors."* Before the change, some
endpoints returned 200 with `{"error": ...}`, others a stack trace with 500.

**What the interviewer is really checking**
A clean layering (no try/catch in every controller), correct status codes, validation errors, and not leaking internals.

**How I answer it** (120-second answer, point by point)
1. **Domain exceptions:** `BookingNotFoundException`, `InsufficientPointsException`, thrown by services.
2. **One advice:**
   ```java
   @RestControllerAdvice
   class ApiErrors {
       @ExceptionHandler(BookingNotFoundException.class)
       ProblemDetail notFound(BookingNotFoundException e) {
           return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
       }
   }
   ```
3. **Validation:** `@Valid` on the request body raises `MethodArgumentNotValidException`; map it to 400 with a list of field errors.
4. **Status codes:** 400 bad input, 401 not authenticated, 403 not allowed, 404 not found, 409 conflict (duplicate/version), 422 business rule, 500 unexpected (generic message only).
5. **Built-in support:** `spring.mvc.problemdetails.enabled=true` returns Problem Details for Spring's own exceptions; extending `ResponseEntityExceptionHandler` lets me customise them.
6. **Logging and correlation:** log the full stack trace once in the catch-all handler with the trace id, and return the trace id in the body so support can find it.

**Trade-offs and what can go wrong**
- A catch-all `Exception` handler that returns 400 hides real server bugs; unexpected errors must stay 500.
- Returning `e.getMessage()` for unexpected exceptions can leak SQL or internal class names.

**Follow-ups to expect**
- *Error in a filter (security) before the controller?* -> `@ControllerAdvice` does not see it; use an `AuthenticationEntryPoint`/`AccessDeniedHandler` or a filter-level handler.
- *Errors in WebClient calls?* -> Map downstream 4xx/5xx to your own domain exceptions with `onStatus`.

**60-second answer**
"Services throw domain exceptions like BookingNotFound, and one @RestControllerAdvice maps them to HTTP status codes, so
controllers stay free of try-catch. I return RFC 9457 Problem Details, which Spring supports with ProblemDetail, so
partners get a consistent body with type, title, status and detail. @Valid errors become 400 with field errors, business
rules 422, conflicts 409, and anything unexpected a generic 500 with the trace id while the stack trace goes to the logs.
Filter-level errors, like security, need their own handlers because the advice never sees them."

### Q7 [senior] How do you connect a Spring Boot application to two databases?
tags: multiple-datasources, datasource, jpa, entitymanagerfactory, transactionmanager, hikari, spring-data, spring-boot, persistent

**Start here: the concepts**
- Spring Boot auto-configures **one** `DataSource` from `spring.datasource.*`. With two, you define both yourself.
- Each JPA database needs its own `DataSource`, `EntityManagerFactory`, and `TransactionManager`, and its own set of repositories and entity packages.
- One of them is marked `@Primary`, so injection points without a qualifier still work.

**The live scenario (functional requirement)**
*FR: "The order service writes to its PostgreSQL database and reads customer data from a legacy Oracle reporting
database."*

**What the interviewer is really checking**
That you know the wiring (packages, qualifiers, transaction managers), and the trap that one transaction does not span
both databases.

**How I answer it** (120-second answer, point by point)
1. **Properties:** `app.datasource.orders.*` and `app.datasource.legacy.*` (URL, user, Hikari pool size per database).
2. **DataSources:** `@Bean @Primary @ConfigurationProperties("app.datasource.orders") DataSourceProperties ...` then `.initializeDataSourceBuilder().type(HikariDataSource.class).build()`; same for legacy without `@Primary`.
3. **JPA per database:** a `@Configuration` with `@EnableJpaRepositories(basePackages = "...orders.repo", entityManagerFactoryRef = "ordersEmf", transactionManagerRef = "ordersTx")`, and an `EntityManagerFactory` built with `EntityManagerFactoryBuilder` scanning `...orders.entity`. A second configuration for `legacy`.
4. **Transactions:** `@Transactional("legacyTx")` on legacy services; the primary manager is the default.
5. **Read-only legacy:** if I only run reports, `JdbcTemplate` on the legacy `DataSource` is simpler than a second JPA setup.
6. **Migrations:** Flyway configured for the orders DB only; never let the app migrate the legacy schema.
7. **Health:** both appear in `/actuator/health`; a down legacy DB should degrade the report feature, not fail readiness for the whole service.

**Trade-offs and what can go wrong**
- A `@Transactional` method writing to both databases is **not atomic** across them. Use XA (JTA with Atomikos/Narayana) only if truly needed; usually redesign with an outbox or idempotent retries.
- Forgetting `@Primary` gives "expected single matching bean but found 2".
- Entity packages overlapping between the two configurations causes confusing mapping errors.

**Follow-ups to expect**
- *Read/write splitting to a replica?* -> `AbstractRoutingDataSource` with a lookup key from `@Transactional(readOnly = true)`, wrapped in `LazyConnectionDataSourceProxy`.
- *Two databases in tests?* -> Testcontainers for both, with `@DynamicPropertySource`.

**60-second answer**
"Boot auto-configures only one DataSource, so for two I define both explicitly with their own properties and Hikari
pools, and mark the main one @Primary. For JPA, each database gets its own configuration class with
@EnableJpaRepositories pointing to its repository package, its own EntityManagerFactory scanning its entity package, and
its own transaction manager. Legacy services use @Transactional with that manager's name. If the second database is
read-only reporting, JdbcTemplate is simpler. The big trap is that one transaction doesn't span both databases. I avoid
XA and design with an outbox or idempotent retries instead."

### Q8 [senior] You use @Scheduled for a nightly job. What happens when the service runs on four pods?
tags: scheduler, scheduled, shedlock, distributed-lock, cron, batch, kubernetes, spring-boot, persistent

**Start here: the concepts**
- `@EnableScheduling` + `@Scheduled(cron = "...")` runs a method on a timer **inside every running instance**.
- With 4 pods, the job runs **4 times** unless you coordinate.
- A **distributed lock** (ShedLock, database row, Redis) lets only one instance run each execution.

**The live scenario (functional requirement)**
*FR: "Every night at 01:00, send expiry reminder emails for loyalty points."* After scaling to 4 pods, customers got 4
identical emails.

**What the interviewer is really checking**
That you recognise the multi-instance problem and know the standard fixes, plus idempotency, time zones and monitoring.

**How I answer it** (120-second answer, point by point)
1. **Root cause:** each pod has its own scheduler; nothing coordinated them.
2. **Fix 1, ShedLock:** `@SchedulerLock(name = "pointsExpiryReminder", lockAtMostFor = "30m", lockAtLeastFor = "1m")` with a `shedlock` table in the existing database. Only the instance that acquires the lock row runs.
3. **Fix 2, platform scheduler:** move the job to a **Kubernetes CronJob** (or AWS EventBridge) that runs one container; the service itself stays stateless. My preference for heavy batch jobs.
4. **Idempotency anyway:** mark each reminder as sent (`reminder_sent_at`) and select only unsent rows, so a retry or overlap never sends twice.
5. **Time zone:** `@Scheduled(cron = "0 0 1 * * *", zone = "Asia/Kolkata")`; servers usually run in UTC.
6. **Thread pool:** the default scheduler has **one thread**; a long job blocks all others. Set `spring.task.scheduling.pool.size` or use an executor.
7. **Large volumes:** process in pages/chunks (Spring Batch if it needs restartability), with metrics on rows processed.

**Trade-offs and what can go wrong**
- `lockAtMostFor` shorter than the job's duration lets a second pod start while the first is still running.
- A pod killed mid-job leaves partial work; chunked, idempotent processing makes a rerun safe.
- A CronJob adds deployment pieces but isolates batch load from API pods.

**How I'd monitor it**
Last successful run timestamp (alert if older than 25 hours), duration, rows processed, failures, and duplicate-send
count (should be zero).

**Follow-ups to expect**
- *fixedRate vs fixedDelay?* -> `fixedRate` starts every N ms regardless of duration; `fixedDelay` waits N ms after the previous run finishes.
- *How do you run it on demand?* -> Expose a secured admin endpoint or trigger the CronJob manually; both go through the same lock.

**60-second answer**
"@Scheduled runs in every instance, so on four pods the job runs four times. That's exactly how customers once got four
identical reminder emails. The quick fix is ShedLock: a lock table in our database, so only one pod runs each execution,
with lockAtMostFor longer than the job. For heavy batch work I prefer a Kubernetes CronJob that runs one container. Either
way, the job is idempotent: it marks each reminder as sent and selects only unsent rows. I also set the cron time zone,
raise the scheduler pool from its default single thread, process in chunks, and alert if the last success is more than a
day old."

### Q9 [mid] What is a circuit breaker, and how do you configure it in Spring Boot?
tags: circuit-breaker, resilience4j, fallback, timeout, retry, bulkhead, microservices, spring-boot, persistent

**Start here: the concepts**
- A **circuit breaker** stops calling a failing dependency for a while, so your service fails fast instead of waiting on timeouts and running out of threads.
- **States:** CLOSED (calls flow, failures counted) -> OPEN (calls rejected immediately, fallback used) -> HALF_OPEN (a few trial calls decide whether to close again).
- In Spring Boot it is usually **Resilience4j**.

**The live scenario (functional requirement)**
*FR: "Product pages show a delivery estimate from a logistics partner API."* When the partner slowed to 20-second
responses, all Tomcat threads waited and the whole product page went down.

**What the interviewer is really checking**
The state machine, sensible thresholds, the order of resilience decorators, and a useful fallback.

**How I answer it** (120-second answer, point by point)
1. **Timeout first:** `TimeLimiter` or the HTTP client's read timeout at 800 ms. Without timeouts, a breaker reacts too slowly.
2. **Breaker config:**
   ```yaml
   resilience4j.circuitbreaker.instances.logistics:
     sliding-window-size: 50
     failure-rate-threshold: 50
     slow-call-duration-threshold: 1s
     slow-call-rate-threshold: 60
     wait-duration-in-open-state: 30s
     permitted-number-of-calls-in-half-open-state: 5
   ```
3. **Annotate:** `@CircuitBreaker(name = "logistics", fallbackMethod = "estimateFallback")`; the fallback returns "Delivery in 3-5 days" from a cached or default value.
4. **Retry carefully:** at most 1-2 retries with backoff for idempotent GETs, and only for transient errors; retries count towards the breaker.
5. **Bulkhead:** limit concurrent calls to the partner (for example 20), so it can never take all threads.
6. **Observe:** breaker state and failure rate exported through Actuator/Micrometer; alert when it opens.
7. **Result in the scenario:** product pages stayed up with a default estimate while the partner was slow.

**Trade-offs and what can go wrong**
- Thresholds too sensitive open the breaker on normal blips; too lax and it never protects you. Tune from real traffic.
- Ignoring business errors: a 404 "no estimate" should not count as a failure (`ignore-exceptions`).
- A fallback that calls another slow service just moves the problem.

**Follow-ups to expect**
- *Circuit breaker vs retry?* -> Retry handles brief transient failures; the breaker handles sustained failure. They work together, breaker outside retry.
- *Where else can it live?* -> In a service mesh (Istio outlier detection) for language-agnostic protection.

**60-second answer**
"A circuit breaker counts failures and slow calls to a dependency. Past a threshold it opens and rejects calls
immediately with a fallback, so threads aren't stuck. After a wait, a few trial calls in half-open decide whether to
close again. In Spring Boot I use Resilience4j: a timeout of about 800 milliseconds, then a breaker with a 50-call window,
50 percent failure or 60 percent slow-call thresholds, 30 seconds open, and a fallback like a default delivery estimate.
I add at most one retry for idempotent calls and a bulkhead to cap concurrency, and I export the breaker state to
alerts."

### Q10 [mid] Explain the main components of a microservice architecture and how services communicate
tags: microservices, components, api-gateway, service-discovery, config-server, synchronous, asynchronous, kafka, rabbitmq, observability, persistent

**Start here: the concepts**
- A microservice owns **one business capability and its data**, and is deployed independently.
- **Synchronous** communication (REST/gRPC) waits for an answer; **asynchronous** (Kafka/RabbitMQ) sends an event or message and moves on.
- Supporting components (gateway, discovery, config, observability) make many small services manageable.

**The live scenario (functional requirement)**
*FR: "An insurance platform: quote, policy, payment and notification services, used by a web portal and agents' mobile
app."*

**What the interviewer is really checking**
A complete, organised list of components with a purpose for each, and a clear rule for when to use sync vs async.

**How I answer it** (120-second answer, point by point)
1. **Edge:** API gateway (routing, auth, rate limiting), optionally a BFF per client.
2. **Services:** quote, policy, payment, notification, each with **its own database** (database per service).
3. **Discovery and config:** Kubernetes Services (or Eureka) for discovery; config from ConfigMaps/Secrets or Spring Cloud Config, secrets from Vault.
4. **Communication rule:**
   - **Sync REST/gRPC** when the caller needs the answer now: "get quote price".
   - **Async events** when others should react: `PolicyIssued` on Kafka triggers notification, billing and analytics without the policy service knowing them.
   - **Kafka vs RabbitMQ:** Kafka for high-throughput event streams with replay and ordering per key; RabbitMQ for task queues with flexible routing and per-message acks.
5. **Resilience:** timeouts, retries, circuit breakers on sync calls; DLQs and idempotent consumers on async ones.
6. **Data consistency:** sagas + outbox for multi-service flows like "pay then issue policy".
7. **Observability:** centralised logs with correlation ids, metrics (Prometheus/Micrometer), distributed tracing (OpenTelemetry).
8. **Platform:** containers, Kubernetes, CI/CD per service, contract tests between services.

**Trade-offs and what can go wrong**
- Long chains of synchronous calls multiply latency and failure probability (availability of 5 services at 99.9% each is about 99.5%).
- Sharing one database between services creates hidden coupling; it is the most common "distributed monolith" smell.

**Follow-ups to expect**
- *How do you split a monolith?* -> By bounded context, strangler fig at the gateway, one capability at a time, data last.
- *Choreography or orchestration?* -> Orchestration for business-critical flows that need visibility; choreography for loose side effects.

**60-second answer**
"At the edge there's an API gateway, maybe a BFF per client. Behind it, services each own one business capability and
their own database. Kubernetes gives discovery, and config and secrets come from ConfigMaps or Vault. My communication
rule: synchronous REST or gRPC when the caller needs the answer now, like a quote price; events on Kafka when others
should react, like PolicyIssued triggering billing and notifications. I'd use RabbitMQ for classic task queues. Sync calls
get timeouts and circuit breakers, async consumers get DLQs and idempotency, sagas with outbox handle multi-service
flows, and logs, metrics and tracing tie it together."

### Q11 [mid] What is OAuth 2.0 used for, and how do you secure microservices with it?
tags: oauth2, openid-connect, jwt, resource-server, client-credentials, authorization-code, pkce, spring-security, microservices, persistent

**Start here: the concepts**
- **OAuth 2.0** is an **authorisation** framework: it lets a client get an **access token** to call an API on behalf of a user or itself, without sharing passwords.
- **OpenID Connect (OIDC)** adds **authentication** (an ID token saying who the user is).
- Roles: resource owner (user), client (app), authorization server (Keycloak, Okta, Entra ID, Cognito), resource server (your API).

**The live scenario (functional requirement)**
*FR: "Agents log in to the mobile app; the app calls the policy API; the billing batch job calls the payment API with no
user present."*

**What the interviewer is really checking**
That you know which grant fits which client, how a Spring Boot API validates tokens, and token lifetime trade-offs.

**How I answer it** (120-second answer, point by point)
1. **Grants:** user-facing web/mobile -> **Authorization Code + PKCE**; service-to-service with no user -> **Client Credentials**. Password and implicit grants are deprecated (OAuth 2.1).
2. **Tokens:** a short-lived access token (often a JWT, 5-15 min) and a refresh token held by the client.
3. **Spring Boot resource server:** `spring-boot-starter-oauth2-resource-server` and `spring.security.oauth2.resourceserver.jwt.issuer-uri=...`. Spring fetches the JWKS keys and validates signature, issuer, expiry and audience on every request.
4. **Authorisation rules:** scopes and roles mapped to authorities: `.requestMatchers(HttpMethod.POST, "/policies/**").hasAuthority("SCOPE_policy.write")`, plus ownership checks in the service.
5. **Gateway + services:** the gateway validates first, and services validate again (zero trust); propagate the user token, or use token exchange for downstream calls.
6. **Client side:** Spring's OAuth2 client (`OAuth2AuthorizedClientManager`) obtains and refreshes client-credential tokens for outbound calls automatically.

**Trade-offs and what can go wrong**
- JWTs cannot be revoked before expiry; keep them short or use introspection for sensitive operations.
- Not checking `aud` lets a token issued for another API be replayed against yours.
- Storing tokens in browser localStorage exposes them to XSS; prefer a BFF with HttpOnly cookies.

**Follow-ups to expect**
- *OAuth vs JWT?* -> OAuth is the protocol for getting tokens; JWT is one token format.
- *How do you test secured endpoints?* -> `@WithMockUser` or `jwt()` request post-processor in MockMvc tests.

**60-second answer**
"OAuth 2.0 lets clients get access tokens to call APIs without handling user passwords, and OpenID Connect adds
identity on top. For the agents' mobile app I'd use authorization code with PKCE, and for the billing batch job client
credentials, since no user is present. Each Spring Boot service is an OAuth2 resource server: it points to the issuer,
fetches the signing keys, and validates signature, expiry, issuer and audience on every request. Scopes map to
authorities for endpoint rules, and the service still checks ownership. Access tokens are short-lived, and the gateway
validates too, but services never trust the network alone."
