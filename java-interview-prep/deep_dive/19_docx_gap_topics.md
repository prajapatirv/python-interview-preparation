# Interview-guide gap topics: core Java, Spring, REST, resilience, Kafka recovery, scaling and design

> **Runnable:** reuses the existing examples where the behaviour is already simulated -
> [`04_concurrency/01`](../examples/04_concurrency/01_race_volatile_atomic_locks.java) ·
> [`04_concurrency/02`](../examples/04_concurrency/02_thread_pools_and_sizing.java) ·
> [`02_collections/02`](../examples/02_collections/02_collections_pitfalls.java) ·
> [`11_microservices/01`](../examples/11_microservices/01_circuit_breaker_retry_bulkhead.java) ·
> [`12_kafka/02`](../examples/12_kafka/02_consumer_groups_rebalancing_and_lag.java) ·
> [`12_kafka/03`](../examples/12_kafka/03_delivery_semantics_idempotency_dlt.java) ·
> [`16_system_design/01`](../examples/16_system_design/01_capacity_littles_law_100_to_600_tps.java) ·
> [`14_observability_splunk/01`](../examples/14_observability_splunk/01_structured_logging_mdc_and_splunk_queries.java) ·
> [`07_spring_boot/02`](../examples/07_spring_boot/02_actuator_health_and_graceful_shutdown.java)
> **Short answers:** [`../Docx_Gap_Supplement_QA.md`](../Docx_Gap_Supplement_QA.md) (Q97-Q114) ·
> **Source:** the 44-question `Java_Kafka_SpringBoot_Microservices_Interview_QA.docx`

This chapter is the long-form treatment of the questions in the interview-prep `.docx` that were **missing or only
a one-liner** in the 96-question guide. It has no `examples/19_*` folder of its own: every mechanism here is
already runnable in an earlier chapter (listed per question). The index at the end maps all 44 docx questions to
their answer.

## What interviewers are actually probing

- **Core Java:** do you know *why* a thread-safe collection still has races, and when a lock is the wrong tool?
- **Spring:** can you explain what the framework does for you, so you can debug it when it does not?
- **Resilience:** do you know that retry and circuit breaker are *complementary*, and that an unbounded wait is the
  most common cause of an outage?
- **Kafka:** what exactly happens to in-flight work when a consumer dies, and how a slow dependency becomes lag?
- **Scale and design:** do you start with measurement and arithmetic, then pick the smallest safe change?

## Must-know points

- A process owns memory; threads share the heap. Shared mutable state is the source of every race.
- `ConcurrentHashMap` makes each *method* atomic, not your *check-then-act*. Use `merge`/`compute`.
- `synchronized` is automatic and simple; `ReentrantLock` buys `tryLock`, interruption and fairness at the price of a mandatory `finally`.
- `@SpringBootApplication` = configuration + auto-configuration + component scan from its own package downward.
- PUT replaces, PATCH changes part. Idempotency depends on the *operation*, not the verb.
- Retry handles transient faults, a circuit breaker handles a sick dependency; every outbound call needs a timeout.
- Kafka consumer death = heartbeat/poll timeout -> rebalance -> resume from last committed offset -> duplicates.
- Lag grows when arrival rate exceeds processing rate; scaling consumers is capped by partition count.
- Capacity: concurrency = TPS x latency (Little's Law). Do the math before you say "add pods".
- Zero downtime is a *code and schema* property (backward compatibility), not only a deployment-tool property.

---

## Interview questions and full answers

### 1. Core Java

#### Q1. Process vs thread - and why does it matter in a Spring Boot service? (guide Q97)

A **process** is an isolated program instance: its own virtual address space, file handles and OS-level resources.
A crash or memory leak in one does not corrupt another, and they communicate through IPC (sockets, pipes, shared
files, message brokers). A **thread** is a schedulable path of execution *inside* a process. All threads of a process
share the **heap** and static data, but each has its own **stack** and program counter.

Consequences:

| | Process | Thread |
|---|---|---|
| Creation cost | high | low |
| Isolation | strong | none for heap data |
| Communication | IPC / network | shared memory (needs synchronization) |
| Failure blast radius | itself | whole process (an `OutOfMemoryError` affects every thread) |
| Context switch | expensive | cheaper |

In a Spring Boot service the JVM is **one process**; Tomcat hands each request to a thread from its pool (default
200). Singleton beans are shared by all those threads, which is why **controllers, services and repositories must be
stateless or thread-safe**. The classic bug is a field on a singleton `@Service` holding per-request data.

```java
@Service
class PriceService {
    private BigDecimal lastPrice;               // BUG: shared by all request threads

    BigDecimal quote(String sku) {
        lastPrice = lookup(sku);                // thread A writes
        return lastPrice;                       // thread B may have overwritten it by now
    }
}
// Fix: keep per-request data in local variables / method parameters.
```

*Failure mode:* intermittent wrong data under load that never reproduces in a single-user test.
*Trade-off:* more processes (containers) give isolation and independent scaling; more threads give cheap concurrency.
Virtual threads (Java 21) make threads cheap enough for blocking I/O, but they do **not** remove the shared-state problem.
*Run:* `04_concurrency/01` shows the lost-update race on a shared counter.

#### Q2. HashMap vs ConcurrentHashMap (guide Q98)

`HashMap` is fast and unsynchronized. Under concurrent writes it can lose entries, throw
`ConcurrentModificationException` during iteration, and (on old JDKs) loop forever while resizing.

`ConcurrentHashMap` (Java 8+) uses **CAS for empty bins and per-bin `synchronized` locking** for collisions; reads are
mostly lock-free. It does not allow `null` keys or values because `get()` returning `null` would be ambiguous (absent
vs mapped-to-null) when another thread may change the map between calls. Iterators are **weakly consistent**: they
reflect the map at some point and never throw CME. `size()` is an estimate under concurrent modification.

The deeper point is **compound operations**:

```java
Map<String, Integer> stock = new ConcurrentHashMap<>();

// BROKEN: each call is atomic, the sequence is not
if (!stock.containsKey("sku-1")) {        // thread A and B both see "absent"
    stock.put("sku-1", 10);               // both write
}

// CORRECT: a single atomic operation
stock.putIfAbsent("sku-1", 10);
stock.merge("sku-1", -1, Integer::sum);                 // atomic decrement
stock.compute("sku-1", (k, v) -> v == null ? 0 : v - 1);
stock.computeIfAbsent("sku-2", k -> loadFromDb(k));     // keep the lambda short and non-reentrant
```

*Failure modes:* (1) check-then-act races; (2) long-running work inside `compute` blocks that bin for others;
(3) treating a per-JVM map as shared state across 3 pods - each pod has its own copy; (4) unbounded growth as an
accidental cache (no eviction) -> memory leak. For a bounded cache use Caffeine; for cross-instance state use Redis
or the database.
*Compare:* `Collections.synchronizedMap` takes one lock for every call; `Hashtable` is the legacy equivalent.
*Run:* `02_collections/02` shows the failing patterns.

#### Q3. synchronized vs ReentrantLock (guide Q99)

Both are **reentrant** mutual-exclusion locks with the same memory-visibility guarantees (a release happens-before
the next acquire). The differences are about control:

| Need | `synchronized` | `ReentrantLock` |
|---|---|---|
| Simplicity, no leak possible | yes | no - forgetting `unlock()` leaks the lock |
| Give up after a time | no | `tryLock(timeout)` |
| Respond to interruption while waiting | no | `lockInterruptibly()` |
| Fair (FIFO) ordering | no | `new ReentrantLock(true)` (lower throughput) |
| Multiple wait conditions | one monitor `wait/notify` | several `Condition` objects |
| Read-mostly workload | - | `ReentrantReadWriteLock` / `StampedLock` |

```java
class Account {
    private final ReentrantLock lock = new ReentrantLock();
    private long balance;

    boolean withdraw(long amt) throws InterruptedException {
        if (!lock.tryLock(100, TimeUnit.MILLISECONDS)) return false;   // caller can retry or fail fast
        try {
            if (balance < amt) return false;
            balance -= amt;
            return true;
        } finally {
            lock.unlock();                                              // never skip this
        }
    }
}
```

Deadlock avoidance ties in directly: acquire locks in a **global order**, or use `tryLock` with a timeout and back
off. A senior answer also says the best lock is **no lock**: immutable objects, thread confinement, `AtomicLong`,
`LongAdder` under high contention, or a single-writer queue.
*Run:* `04_concurrency/03` demonstrates a deadlock and the ordered-lock fix.

#### Q4. Why ExecutorService, and how do you size and bound it? (guide Q114)

Creating a `Thread` per task is unbounded, wastes memory (each stack is ~1 MB) and gives no queueing, reuse,
result handling or shutdown. A pool decouples *task submission* from *thread management* and gives you
**back-pressure**: the one lever that stops a traffic spike from turning into an out-of-memory crash.

Anatomy of `ThreadPoolExecutor`: tasks go to a core thread; when core threads are busy they enter the **queue**; only
when the queue is full does it grow towards `maximumPoolSize`; when both are full the **rejection policy** runs
(`AbortPolicy`, `CallerRunsPolicy`, `DiscardPolicy`). This ordering surprises people: with an unbounded queue the
pool **never** grows beyond core size.

Sizing starting points (then measure):

```
CPU-bound : N_cores (+1)
I/O-bound : N_cores x (1 + wait / compute)       8 x (1 + 90ms/10ms) = 80
```

Pitfalls: `newFixedThreadPool` has an unbounded `LinkedBlockingQueue` (OOM under overload);
`newCachedThreadPool` has unbounded threads; sharing the `ForkJoinPool.commonPool()` for blocking calls starves
parallel streams; forgetting `shutdown()`; swallowed exceptions in `execute()` (use `submit` and read the
`Future`, or set an `UncaughtExceptionHandler`); unnamed threads that make thread dumps unreadable.
*Run:* `04_concurrency/02` compares pool sizes.

---

### 2. Spring and Spring Boot

#### Q5. What does `@SpringBootApplication` actually do? (guide Q100)

It is a **meta-annotation** combining:

1. `@SpringBootConfiguration` - a specialised `@Configuration`; the class can declare `@Bean` methods.
2. `@EnableAutoConfiguration` - imports auto-configuration classes listed in
   `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`, each guarded by
   `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnProperty` ...
3. `@ComponentScan` - registers `@Component`/`@Service`/`@Repository`/`@RestController`/`@Configuration`
   classes found in **the annotated class's package and all sub-packages**.

Two practical consequences: **where you put the class matters**, and **your own bean wins** over auto-configuration
because of `@ConditionalOnMissingBean`.

```java
package com.shop;                          // scan root
@SpringBootApplication
public class ShopApplication { ... }

// com.shop.order.OrderService       -> scanned
// com.shop.common.Clock             -> scanned
// com.thirdparty.Helper             -> NOT scanned; add @Import or scanBasePackages
```

Debug tip: run with `--debug` (or `debug=true`) to print the **conditions evaluation report**: which
auto-configurations matched and why others did not. Exclude one with
`@SpringBootApplication(exclude = DataSourceAutoConfiguration.class)`.
*Run:* `07_spring_boot/01` re-creates the conditional logic in miniature.

#### Q6. Walk through the bean lifecycle (guide Q101)

For a singleton: **instantiate -> populate properties/inject -> `*Aware` callbacks (`BeanNameAware`,
`ApplicationContextAware`) -> `BeanPostProcessor.postProcessBeforeInitialization` -> `@PostConstruct` ->
`InitializingBean.afterPropertiesSet` -> custom init-method -> `postProcessAfterInitialization` -> ready ->
`@PreDestroy` -> `DisposableBean.destroy` -> custom destroy-method.**

The step interviewers care about is `postProcessAfterInitialization`: that is where Spring wraps the bean in a
**proxy** for `@Transactional`, `@Async`, `@Cacheable` and AOP. It explains the famous self-invocation bug:
calling `this.save()` from inside the same class bypasses the proxy, so the transaction annotation silently does
nothing.

```java
@Service
class ReportService {
    @Transactional
    public void save() { ... }

    public void run() {
        save();            // BUG: direct call on `this`, not on the proxy - no transaction
    }
}
// Fix: move save() to another bean, or inject the proxy, or restructure.
```

Other lifecycle facts: scope matters (**prototype** beans are created per request and Spring does *not* call
destroy callbacks for them); constructor injection means dependencies exist when the constructor runs, but
`@Value` field values do not until after instantiation - another reason to prefer constructor injection;
start-up work belongs in `@PostConstruct`, `SmartLifecycle` or an `ApplicationRunner`, and long blocking work there
delays readiness.
*Run:* `06_spring_core/01` (mini container) and `06_spring_core/02` (proxy + self-invocation).

---

### 3. REST

#### Q7. PUT vs PATCH, and what idempotency means for each (guide Q102)

**PUT** sends the *complete* representation and the server replaces the stored one. Re-sending the same PUT yields
the same state: idempotent by definition. Fields omitted are treated as cleared/defaulted, which is the usual
source of accidental data loss.

**PATCH** sends a *delta*. Two formats: **JSON Merge Patch** (`application/merge-patch+json`: send the changed
fields, `null` deletes) and **JSON Patch** (`application/json-patch+json`: an ordered list of `add/remove/replace`
operations). A patch is idempotent only if its *semantics* are: "set status = SHIPPED" is, "increment quantity"
is not, and JSON Patch `add` to an array is not.

```http
PATCH /orders/42
Content-Type: application/merge-patch+json
{"status":"SHIPPED"}                      -> idempotent: safe to retry
```

```java
@PatchMapping(path = "/orders/{id}", consumes = "application/merge-patch+json")
ResponseEntity<Order> patch(@PathVariable long id, @RequestBody Map<String, Object> changes) {
    Order o = repo.findById(id).orElseThrow(NotFoundException::new);
    if (changes.containsKey("status")) o.setStatus(OrderStatus.valueOf((String) changes.get("status")));
    return ResponseEntity.ok(repo.save(o));
}
```

Senior details: protect against lost updates with **`If-Match` + ETag** (answer `412` on mismatch, `428` if the
header is required but missing); validate that a PATCH cannot touch read-only fields; make non-idempotent
operations safe with an **`Idempotency-Key`** header persisted with the result.
*Run:* `08_rest_api/01` covers ETag and idempotency against a real HTTP server.

---

### 4. Microservice resilience

#### Q8. Retry vs circuit breaker (guide Q103)

Think of **retry** as "try again, it was probably a blip" and the **circuit breaker** as "stop, it is not a blip".

*Retry* masks transient faults: network glitches, a pod being restarted, a `503` during a deploy. It is only safe
for **idempotent** operations and must be bounded: max attempts, **exponential backoff**, **jitter**, and an
overall time budget. Without jitter, thousands of clients retry at the same instants - a *thundering herd* that
keeps a recovering service down. Retrying at several layers multiplies load (3 layers x 3 attempts = 27 calls).
Do not retry `4xx` (the request is wrong, not the server), and honour `Retry-After` on `429`.

*Circuit breaker* tracks the failure/slow-call rate over a sliding window. **CLOSED** passes calls; above the
threshold it goes **OPEN** and fails immediately with a fallback (no threads wasted, the dependency gets room to
recover); after a wait it goes **HALF-OPEN** and lets a few probes through to decide.

Composition order matters: **circuit breaker outside, retry inside** - retries count as failures for the breaker, and
once open, there are no retries at all. With Resilience4j's aspect order, `Retry( CircuitBreaker( TimeLimiter( call )))`
is the documented default; know that and say why.

```java
@CircuitBreaker(name = "inventory", fallbackMethod = "unknownStock")
@Retry(name = "inventory")
public Stock stock(String sku) { return client.get(sku); }

Stock unknownStock(String sku, Throwable t) { return Stock.assumeAvailable(sku); }   // degrade, document it
```

*Fallback design* is a business decision: cached value, default, queue for later, or fail with a clear `503`.
*Monitor:* breaker state transitions, retry counts, and fallback rate as metrics with alerts.
*Run:* `11_microservices/01` prints every state transition and shows how a retry storm happens without jitter.

#### Q9. Timeouts and bulkheads (guide Q104)

A missing timeout is the single most common cause of cascading failure. Little's Law makes it concrete: if each
request holds a thread and the dependency takes 30 s instead of 100 ms, a 200-thread pool carries **6.7 req/s**
instead of 2,000. The service is "down" although nothing crashed.

Set, at minimum: **connect timeout**, **read/response timeout** (RestClient/WebClient/Feign/JDBC/Kafka producer
`delivery.timeout.ms`), and an **overall deadline** for the request that downstream budgets are carved from
(inbound 2 s -> gateway 1.8 s -> service 1.5 s -> DB 1 s). Prefer a deadline propagated in a header over fixed
numbers at every hop.

A **bulkhead** limits how much of your capacity one dependency can consume:

- *Semaphore bulkhead* - cap concurrent calls (cheap, same thread).
- *Thread-pool bulkhead* - dedicated pool per dependency (stronger isolation, extra context switch).

```java
// 3 dependencies, 200 request threads. Without isolation one slow dependency can take all 200.
@Bulkhead(name = "reports",  type = Bulkhead.Type.SEMAPHORE)   // max 20 concurrent
@Bulkhead(name = "payments", type = Bulkhead.Type.SEMAPHORE)   // max 60 concurrent
```

When the bulkhead is full the call is **rejected immediately** (`BulkheadFullException`) - that is the point:
fail fast, degrade the non-critical feature, keep the critical path alive. Size each bulkhead from
`peak TPS x p99 latency` of that dependency.

#### Q10. API Gateway (guide Q112)

A gateway is the **edge** of the system: clients talk to one address, and it routes to services, terminates TLS,
validates tokens, applies rate limits, and can aggregate calls. It also centralises CORS, request logging and
the injection of a **trace/correlation ID**.

Choices: Spring Cloud Gateway (reactive, code-configured), Kong/NGINX/Envoy, or a cloud-native gateway (AWS API
Gateway, Azure APIM). BFF ("backend for frontend") variants give each client type (web, mobile) its own
aggregation layer.

Anti-patterns: business logic in the gateway (it becomes a distributed monolith's god object); relying on it as
the only security layer (services should still verify tokens - zero trust); a single un-replicated instance; and
using it for service-to-service calls inside the cluster (use a mesh or direct discovery).
*Contrast:* gateway = north-south traffic (client to cluster); service mesh = east-west (service to service).

---

### 5. Kafka: failure handling and recovery

#### Q11. Retry topics (guide Q105)

Why not just loop and retry inside the listener? Because the consumer processes a partition **sequentially**: one
slow, retried message blocks every message behind it (**head-of-line blocking**) and, if the retry loop outlasts
`max.poll.interval.ms`, the consumer is declared dead and the group rebalances - making things worse.

A **non-blocking retry topic** design parks the failed record and moves on:

```
orders -> [fail] -> orders-retry-1 (delay 5s) -> [fail] -> orders-retry-2 (delay 1m)
       -> [fail] -> orders-retry-3 (delay 10m) -> [fail] -> orders-dlt
```

Implementation options: Spring Kafka `@RetryableTopic` (creates the topics, delays via pause/resume of the
partition and a timestamp header); or hand-rolled: produce to the next retry topic with headers
`attempt`, `original-topic`, `exception`, `next-retry-at`, then commit the original offset.

Classify errors first: **transient** (timeout, 503) -> retry topics; **non-retryable/poison**
(deserialisation error, validation failure) -> straight to the DLT; **business rejects** -> a separate
"rejected" topic or status, not an error.

Trade-offs and traps:

- **Ordering is broken** for that key once a record is parked - fine for independent events, not for state
  machines (use a single-key blocking retry, or sequence numbers and ignore stale events).
- Consumers must be **idempotent**; a record can be retried *and* duplicated by a rebalance.
- Beware amplification: every layer that retries multiplies traffic to the downstream.
- Operate it: alert on **DLT depth and age**, build a replay tool, and keep the original headers and stack trace.

*Run:* `12_kafka/03` simulates retry, DLT and idempotent consumption.

#### Q12. What happens when a consumer dies (guide Q106)

Sequence in a group of three consumers on six partitions:

1. The process is killed, OOMs, or the node loses the network. **Heartbeats stop.** (Heartbeats come from a
   background thread; `poll()` is the other liveness signal.)
2. After `session.timeout.ms` without a heartbeat - or `max.poll.interval.ms` without a `poll()` for a *live but
   stuck* consumer - the group coordinator removes the member.
3. The coordinator triggers a **rebalance**; partitions are redistributed by the assignor.
4. New owners start from each partition's **last committed offset** (or `auto.offset.reset` if none).
5. Records processed *after* the last commit but *before* the crash are **processed again**.

```
committed offset = 100     consumer processes 101..108, crashes before committing
new owner restarts at 101  -> records 101..108 are delivered twice
```

So the guarantees are **at-least-once**; correctness comes from **idempotent processing** (dedupe on a business
key, upsert, unique constraint, or Kafka transactions for Kafka-to-Kafka). Commit *after* processing, and batch
commits sensibly - too rare means large replays, too frequent costs throughput.

Reduce the pain: `CooperativeStickyAssignor` (only moved partitions pause), **static membership**
(`group.instance.id` lets a restarted pod reclaim its partitions within the session timeout without a
rebalance), `ConsumerRebalanceListener` to commit/cleanup on revoke, and sensible `max.poll.records` so one batch
fits in `max.poll.interval.ms`.
A *crash loop* (die, rebalance, die) usually means one poison record: find it, route it to the DLT, do not just
add consumers. *Run:* `12_kafka/02` shows the reassignment and the replayed records.

#### Q13. Payment is slow and lag is rising (guide Q111)

This is a scenario answer: **symptom -> bottleneck -> stabilise -> fix -> prevent**.

*Quantify.* `lag growth rate = arrival rate - processing rate`. If a consumer takes 500 ms per record it does 2
rec/s; 100 rec/s of arrivals need 50 consumer threads, which needs **at least 50 partitions**. If the topic has
12 partitions, adding consumers cannot help beyond 12; you must make each record faster, process records
concurrently inside the consumer (while preserving per-key order), or add partitions (which changes key
mapping - plan it).

*Find the cause.* Is the time in the payment call (p99 latency, pool wait, DB lock wait), or in your own code
(serialization, N+1 queries)? Is it all partitions or one (hot key / skew)? Did a deploy or a downstream change
precede it?

*Stabilise.*

1. Timeout + circuit breaker on the payment client so stuck calls release threads.
2. If payment is **down**, pause the listener container (`pause()`) rather than failing every record into the DLT -
   resume when healthy; lag is a cheaper failure than lost or duplicated payments.
3. Scale consumers only up to partitions; raise `max.poll.records` cautiously.
4. Keep ordering: concurrency per partition only across different keys.

*Correctness.* A charge is a side effect: pass an **idempotency key** (order ID) to the payment provider, and
record the outcome before committing the offset, so rebalances and retries never double-charge.

*Recover and prevent.* Drain the backlog with temporary extra capacity, then alert on **lag trend and time-lag**
(not only absolute lag), set an SLO for payment latency, add a bulkhead, and write the runbook.
*Run:* `12_kafka/02` and `12_kafka/04` (capacity math).

---

### 6. Scale, design and operations

#### Q14. 100 -> 600 TPS (guide Q107)

Never start with "add servers". Start with **arithmetic and a bottleneck hunt**.

Little's Law: `L = lambda x W` (in-flight requests = arrival rate x time in system). At 200 ms latency:
100 TPS -> 20 in flight, 600 TPS -> 120 in flight. If one instance sustains ~40 concurrent requests before
latency degrades (find this by load test), you need `120 / 40 = 3` instances at 100% utilisation - plan for
**60-70%** utilisation, so 5 - and remember latency *rises sharply* near saturation (queueing theory: waiting time
~ `rho / (1 - rho)`).

Then walk the stack from the user inward, naming the lever and the risk:

| Layer | Lever | Watch out for |
|---|---|---|
| Edge | CDN, rate limiting, `429` shedding | unfair limits per client |
| App | scale out, stateless, tune pools | thread pool vs DB pool mismatch |
| Cache | Redis/Caffeine, cache-aside | stampede, stale data, invalidation |
| Async | accept then queue (Kafka) | eventual consistency, idempotency |
| DB | indexes, replicas, batching, pool sizing | usually the real ceiling; connection limits |
| Downstream | bulkhead, circuit breaker, timeouts | their capacity is not yours |

Validate: load test above target (e.g. 1,000 TPS), track p95/p99 not averages, error rate, saturation, then
autoscale (HPA on CPU or a custom metric such as in-flight requests or consumer lag).
*Run:* `16_system_design/01` and `16_system_design/02`.

#### Q15. Aggregating 3-5 APIs within 10 seconds (guide Q108)

Sequential calls add (2 + 2 + 3 = 7 s and then one slow call breaks the budget). Parallel calls cost about the
**slowest** one. Design with a **time budget**:

1. Classify each downstream as **mandatory** or **optional**.
2. Run them in parallel on a **bounded** executor with a per-call timeout *smaller* than the total budget.
3. Combine with `allOf`; optional failures degrade to defaults, mandatory failures fail the request.
4. Put a circuit breaker on each so a dead dependency costs nothing.

```java
var customer = supplyAsync(() -> customerApi.get(id), io).orTimeout(4, SECONDS);                       // mandatory
var offers   = supplyAsync(() -> offerApi.get(id), io).completeOnTimeout(List.of(), 3, SECONDS)         // optional
                   .exceptionally(ex -> List.of());
var risk     = supplyAsync(() -> riskApi.score(id), io).orTimeout(5, SECONDS);                          // mandatory

allOf(customer, offers, risk).join();                       // elapsed ~ max(4, 3, 5), never > 5 s
return new Summary(customer.join(), offers.join(), risk.join());
```

Failure modes: using the common pool (blocking calls starve it); unbounded fan-out (3 calls x 500 req/s =
1,500 concurrent outbound calls - size the pool and the bulkhead); thread-context loss (MDC/trace ID/security
context do not cross threads by default - use a decorating executor); partial results presented as complete
(flag them: `"degraded": ["offers"]`).
If the total is still too slow: cache or pre-compute the aggregate, or switch to `202 Accepted` plus a status
endpoint/webhook. *Run:* `01_java8_core/04`.

#### Q16. Zero-downtime deployment (guide Q109)

Zero downtime is the product of four properties:

1. **Capacity during rollout** - never fewer healthy instances than needed (`maxUnavailable: 0`, `maxSurge: 1`).
2. **Correct traffic gating** - the load balancer sends traffic only to instances that are *ready*
   (readiness probe, warm-up of caches/JIT/connection pools), and **stops** sending before shutdown.
3. **Graceful shutdown** - on `SIGTERM`: fail readiness, stop taking new work, finish in-flight requests, drain
   Kafka consumers (commit, leave group), then exit - inside `terminationGracePeriodSeconds`.
4. **Backward compatibility** - old and new versions run *simultaneously* for minutes or hours, against the
   *same* database and topics.

Strategies: **rolling** (default), **blue/green** (instant switch and rollback; double the capacity, hard with
DB changes), **canary** (a small percentage, auto-rollback on SLO breach), **feature flags** (decouple deploy from
release).

```yaml
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
management.endpoint.health.probes.enabled: true
```

The database is where it goes wrong. **Expand -> migrate -> contract:**

1. *Expand:* add the new column/table (nullable, no lock-heavy default).
2. *Dual write:* new code writes both; old code keeps working.
3. *Backfill* in small batches; *switch reads*.
4. *Contract:* only after every old instance is gone, drop the old column (a later release).

Same discipline for events: add **optional** fields only, consumers ignore unknown fields (tolerant reader),
and remove fields in a later version. Also: connection-draining, idempotent consumers (a rebalance during rollout
causes redelivery), and a tested rollback.
*Run:* `07_spring_boot/02` shows the graceful-shutdown ordering.

#### Q17. Distributed tracing (guide Q110)

Logs from 8 services interleave and cannot answer "why was *this* request slow?". A **trace** is the tree of
**spans** for one request: each span has an ID, parent ID, start time, duration, and tags.
The **trace ID** is created at the edge and propagated on every call - HTTP header (W3C `traceparent`, or B3), Kafka
record headers, and across thread hand-offs.

In Spring Boot 3: **Micrometer Tracing** (bridge to OpenTelemetry or Brave) auto-instruments `RestClient`,
`WebClient`, `@Scheduled`, Kafka templates/listeners, JDBC (with datasource-micrometer). It also puts `traceId`
and `spanId` into the **MDC**, so the log pattern adds them to every line:

```
logging.pattern.level = %5p [${spring.application.name:},%X{traceId:-},%X{spanId:-}]
10:00:01 INFO [order-svc,4bf92f35,00f067aa] Charging order 42
10:00:02 WARN [payment-svc,4bf92f35,a3ce929d] Provider timeout after 900 ms
```

Use: take the trace ID from the alert or error response, query `index=prod traceId=4bf92f35 | sort _time` in Splunk,
or open the trace in Jaeger/Tempo/Zipkin and read the **critical path** (the longest chain of spans) to locate the
slow hop.

Production concerns: **sampling** (head-based 1-10 percent, or tail-based to keep errors and slow traces),
**cardinality** (never put user IDs into metric tags), PII in span attributes, and the three pillars being
complementary - **metrics tell you *that* it is slow, traces *where*, logs *why***.
*Run:* `14_observability_splunk/01`.

#### Q18. CAP theorem (guide Q113)

CAP says that in the presence of a **network partition** a replicated store cannot be both fully **consistent**
(linearizable: every read sees the latest write) and fully **available** (every non-failing node answers).
Because partitions *will* happen, the real decision is what to sacrifice **during** one. Outside a partition you
can have both; **PACELC** extends this: *else* (no partition) you still trade **latency vs consistency**.

| Style | During a partition | Examples |
|---|---|---|
| CP | rejects/blocks writes (or reads) it cannot guarantee | ZooKeeper, etcd, HBase, MongoDB with majority concern |
| AP | accepts requests, nodes diverge, reconcile later | Cassandra (default), DynamoDB (eventually consistent reads), Couchbase XDCR |

Cassandra is **tunable**: with replication factor `N`, read consistency `R` and write consistency `W`, `R + W > N`
gives strong consistency (e.g. `QUORUM`/`QUORUM`), `ONE`/`ONE` gives low latency and availability with eventual
consistency. Pick **per use case**: money movement and inventory decrement lean CP; timelines, counters, carts and
recommendations lean AP.

Designing for AP means accepting its consequences: idempotent writes, conflict resolution (last-write-wins,
vector clocks, CRDTs), read-repair/anti-entropy, and user-visible "your change may take a moment".
*Run:* `13_nosql/02` demonstrates quorum arithmetic.

---

## A worked example

Walk one request through the chapter, using the existing runnable files as evidence:

1. `16_system_design/01` - compute how many instances 600 TPS needs and watch latency explode near 100 percent utilisation.
2. `11_microservices/01` - slow the payment dependency; observe the breaker open and fallback rate rise.
3. `12_kafka/02` - kill a consumer; read the partitions it owned and the offsets the replacement resumes from.
4. `12_kafka/03` - note the duplicate delivery and how the idempotent consumer absorbs it.
5. `14_observability_splunk/01` - follow one trace ID across all log lines.

## Hands-on drills

1. Write a `ConcurrentHashMap<String, Integer>` word counter with 8 threads using (a) get/put and (b) `merge`;
   compare totals.
2. Make a `ThreadPoolExecutor(2, 4, ..., new ArrayBlockingQueue<>(2), CallerRunsPolicy)` and submit 10 slow tasks;
   predict which thread runs each before you print.
3. Add a `@PostConstruct` and a self-invoking `@Transactional` method; explain why the transaction does not start.
4. Write the PUT and PATCH for the same change and show which fields each preserves.
5. Compose `retry(circuitBreaker(call))` by hand with a fake clock; prove that retries stop once the breaker is open.
6. For a topic with 6 partitions and 500 ms processing, calculate the maximum throughput and what raises it.
7. Write the four-step expand/migrate/contract plan for renaming column `phone` to `mobile`.
8. Take a 4-hop call chain with a 2 s SLA and assign a timeout to each hop.

## The 60-second spoken answers

**Resilience:** "Every outbound call has a timeout, so one slow dependency cannot hold all my threads. Transient
faults get a bounded, jittered retry on idempotent operations only; a circuit breaker stops calls to an unhealthy
dependency and returns a deliberate fallback; and a bulkhead keeps one dependency from consuming the whole pool."

**Kafka consumer failure:** "A dead consumer stops heartbeating, the coordinator rebalances, and the new owner
resumes at the last committed offset, so anything processed-but-uncommitted is delivered again. I commit after
processing and make the handler idempotent. Persistent failures go to retry topics and then a DLT, and I alert on
DLT depth and lag trend."

**Scaling:** "I compute concurrency as TPS times latency, find the real bottleneck, usually the database or a
downstream, and then scale stateless instances, cache reads, move non-urgent work async, and protect dependencies.
I load-test beyond the target and watch p99 and saturation rather than averages."

**Zero downtime:** "Rolling or canary deploys with readiness gating and graceful shutdown, and, more importantly,
backward-compatible schema and event changes using expand, migrate, contract, so old and new versions can run
together and rollback is safe."

---

## Index: all 44 docx questions -> where the answer is

| Docx # | Question | Short answer (guide) | Long answer (deep dive) |
|---|---|---|---|
| 1 | Java 8 features | Guide Q11 | [01](01_java8_core.md) |
| 2 | map vs flatMap | Guide Q15 | [01](01_java8_core.md) |
| 3 | Optional | Guide Q16 | [01](01_java8_core.md) |
| 4 | HashMap vs ConcurrentHashMap | Guide Q10, **Q98** | [02](02_collections.md), **19 - Q2** |
| 5 | synchronized vs Lock | Guide Q23, **Q99** | [04](04_concurrency.md), **19 - Q3** |
| 6 | CompletableFuture | Guide Q18 | [01](01_java8_core.md) |
| 7 | Process vs Thread | **Q97** | **19 - Q1** |
| 8 | Java 8 vs Java 11 | Guide Q19, Q22 | [03](03_java11_and_modern.md) |
| 9 | IoC and DI | Guide Q28 | [06](06_spring_core.md) |
| 10 | What is Spring Boot | Guide Q29, Q30 | [07](07_spring_boot.md) |
| 11 | @SpringBootApplication | **Q100** | **19 - Q5** |
| 12 | Stereotype annotations | Guide Q31 | [06](06_spring_core.md) |
| 13 | What is REST | Guide Q39 | [08](08_rest_api.md) |
| 14 | PUT vs PATCH | Guide Q40, **Q102** | [08](08_rest_api.md), **19 - Q7** |
| 15 | Idempotency | Guide Q40, Q80, Q92 | [08](08_rest_api.md), [11](11_microservices.md) |
| 16 | What is a microservice | Guide Q47 | [11](11_microservices.md) |
| 17 | How microservices communicate | Guide Q48 | [11](11_microservices.md) |
| 18 | Circuit breaker | Guide Q50 | [11](11_microservices.md) |
| 19 | Retry vs circuit breaker | **Q103** | **19 - Q8** |
| 20 | What is Kafka | Guide Q55 | [12](12_kafka.md) |
| 21 | Topic | Guide Q56 | [12](12_kafka.md) |
| 22 | Partition | Guide Q56, Q57 | [12](12_kafka.md) |
| 23 | How Kafka scales | Guide Q57, Q72 | [12](12_kafka.md) |
| 24 | Consumer group | Guide Q59 | [12](12_kafka.md) |
| 25 | Consumer dies | Guide Q64, **Q106** | [12](12_kafka.md), **19 - Q12** |
| 26 | Offset | Guide Q60 | [12](12_kafka.md) |
| 27 | Consumer lag | Guide Q63 | [12](12_kafka.md) |
| 28 | Troubleshoot high lag | Guide Q63, Q91 | [12](12_kafka.md), **19 - Q13** |
| 29 | Rebalancing | Guide Q64, Q65 | [12](12_kafka.md) |
| 30 | Ordering | Guide Q58, Q67 | [12](12_kafka.md) |
| 31 | Delivery semantics | Guide Q61 | [12](12_kafka.md) |
| 32 | Dead letter topic | Guide Q68 | [12](12_kafka.md) |
| 33 | Retry topic | **Q105** | **19 - Q11** |
| 34 | Sudden TPS increase | **Q107** | [16](16_system_design.md), **19 - Q14** |
| 35 | Aggregate 3-5 APIs < 10 s | **Q108** | **19 - Q15** |
| 36 | What is NoSQL | Guide Q74 | [13](13_nosql.md) |
| 37 | MongoDB vs Cassandra | Guide Q75 | [13](13_nosql.md) |
| 38 | Eventual consistency | Guide Q76, **Q113** | [13](13_nosql.md), **19 - Q18** |
| 39 | What is Splunk | Guide Q82 | [14](14_observability_splunk.md) |
| 40 | Troubleshoot with Splunk | Guide Q87 | [14](14_observability_splunk.md) |
| 41 | Distributed tracing | Guide Q54, Q86, **Q110** | [14](14_observability_splunk.md), **19 - Q17** |
| 42 | Zero-downtime deployment | Guide Q95, **Q109** | [16](16_system_design.md), **19 - Q16** |
| 43 | Order processing system | Guide Q94 | [11](11_microservices.md), [16](16_system_design.md) |
| 44 | Payment slow, lag rising | Guide Q91, **Q111** | [12](12_kafka.md), **19 - Q13** |
| - | Timeout and bulkhead | **Q104** | **19 - Q9** |
| - | Bean lifecycle | **Q101** | **19 - Q6** |
| - | API Gateway | **Q112** | **19 - Q10** |
| - | ExecutorService | **Q114** | **19 - Q4** |
