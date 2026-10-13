# Supplement — gaps found while reviewing `Java_Kafka_SpringBoot_Microservices_Interview_QA.docx`

The docx has **44 questions**. Each was checked against
[`Java_SpringBoot_Kafka_Interview_QA_Guide.md`](Java_SpringBoot_Kafka_Interview_QA_Guide.md) (96 Q), `topics/` and `deep_dive/`.
Most are covered. This file adds the ones that were **missing or only a one-line mention**, each with a
**small example** (kept deliberately simple). Numbering continues from the guide (Q97-Q119).

**Long-form version of every answer below** (mechanisms, failure modes, trade-offs, 60-second answers) is
[`deep_dive/19_docx_gap_topics.md`](deep_dive/19_docx_gap_topics.md); the question index is in
[`deep_dive/README.md`](deep_dive/README.md#question-index-the-44-question-docx-and-the-supplement).

Answer shape to use out loud: **Definition -> why -> how it works -> small example -> failure mode -> trade-off.**

---

## 1. Coverage map (docx question -> where it lives)

| Docx # | Question | Status | Where |
|---|---|---|---|
| 1 | Java 8 features | covered | Guide Q11 |
| 2 | map vs flatMap | covered | Guide Q15 |
| 3 | Optional | covered | Guide Q16 |
| 4 | HashMap vs ConcurrentHashMap | **thin** | Guide Q10 (one line) -> **Q98** |
| 5 | synchronized vs Lock | **thin** | Guide Q23, no ReentrantLock -> **Q99** |
| 6 | CompletableFuture | covered | Guide Q18 |
| 7 | Process vs Thread | **missing** | **Q97** |
| 8 | Java 8 vs Java 11 | covered | Guide Q19, Q22 |
| 9 | IoC and DI | covered | Guide Q28 |
| 10 | What is Spring Boot | covered | Guide Q29, Q30 |
| 11 | @SpringBootApplication | **missing** | **Q100** |
| 12 | @Component/@Service/@Repository/@RestController | covered | Guide Q31 |
| 13 | What is REST | covered | Guide Q39 |
| 14 | PUT vs PATCH | **thin** | Guide Q40 (table row) -> **Q102** |
| 15 | Idempotency | covered | Guide Q40, Q80, Q92 |
| 16 | What is a microservice | covered | Guide Q47 |
| 17 | How microservices communicate | covered | Guide Q48 |
| 18 | Circuit breaker | covered | Guide Q50 |
| 19 | Retry vs circuit breaker | **thin** | -> **Q103** |
| 20-22 | Kafka, topic, partition | covered | Guide Q55-Q57 |
| 23 | How Kafka scales | covered | Guide Q57, Q72 |
| 24 | Consumer group | covered | Guide Q59 |
| 25 | Consumer dies | **thin** | Guide Q64 -> **Q106** |
| 26-27 | Offset, lag | covered | Guide Q60, Q63 |
| 28 | Troubleshoot high lag | covered | Guide Q63, Q91 |
| 29 | Rebalancing | covered | Guide Q64, Q65 |
| 30 | Ordering | covered | Guide Q58, Q67 |
| 31 | At-most / at-least / exactly-once | covered | Guide Q61 |
| 32 | Dead letter topic | covered | Guide Q68 |
| 33 | Retry topic | **thin** | one mention -> **Q105** |
| 34 | Sudden TPS increase | **thin** | -> **Q107** |
| 35 | Aggregate 3-5 APIs in < 10 s | **missing** | -> **Q108** |
| 36-38 | NoSQL, Mongo vs Cassandra, eventual consistency | covered | Guide Q74-Q76 |
| 39-40 | Splunk, troubleshoot with Splunk | covered | Guide Q82-Q87 |
| 41 | Distributed tracing | **thin** | -> **Q110** |
| 42 | Zero-downtime deployment | **missing** (Q95 is partial) | -> **Q109** |
| 43 | Order processing system | covered | Guide Q94 |
| 44 | Payment slow, Kafka lag rising | **thin** | Guide Q91 -> **Q111** |

Also listed in the docx's priority section but absent from the guide: **Timeout + Bulkhead** (Q104),
**bean lifecycle** (Q101), **API Gateway** (Q112), **CAP theorem** (Q113), **ExecutorService** (Q114).

---

## Q97. Process vs thread?

- **Process:** an independent program with its **own memory space** and OS resources. Crashing one does not
  crash another. Communication needs IPC (sockets, pipes).
- **Thread:** a unit of execution **inside** a process. Threads **share the heap**, so they are cheap to create
  and talk to each other easily, but shared mutable state needs synchronization.

```java
// One JVM = one process. These two threads share `counter` (same heap).
int[] counter = {0};
Thread t1 = new Thread(() -> { for (int i = 0; i < 1000; i++) counter[0]++; });
Thread t2 = new Thread(() -> { for (int i = 0; i < 1000; i++) counter[0]++; });
t1.start(); t2.start(); t1.join(); t2.join();
System.out.println(counter[0]);   // often < 2000: a race, because the heap is shared
```

**Say:** a Spring Boot app is one process; each HTTP request runs on a thread from Tomcat's pool; singleton
beans are shared by all those threads, so they must be stateless or thread-safe.

---

## Q98. HashMap vs ConcurrentHashMap?

| | `HashMap` | `ConcurrentHashMap` |
|---|---|---|
| Thread-safe | No | Yes |
| `null` key/value | allowed | **not allowed** |
| Locking | none | fine-grained (per bin / CAS), reads mostly lock-free |
| Iteration | fail-fast (`ConcurrentModificationException`) | weakly consistent, never throws CME |

Thread-safe **methods** do not make a **compound action** atomic:

```java
Map<String, Integer> hits = new ConcurrentHashMap<>();

// WRONG: check-then-act, two threads can both read 5 and both write 6
Integer c = hits.get("home");
hits.put("home", c == null ? 1 : c + 1);

// RIGHT: one atomic operation
hits.merge("home", 1, Integer::sum);
```

**Trade-off:** it is per-JVM. With 3 service instances, each has its own map - use Redis or a DB for shared
state. `Collections.synchronizedMap` locks the whole map on every call and scales worse.

---

## Q99. synchronized vs ReentrantLock?

| | `synchronized` | `ReentrantLock` |
|---|---|---|
| Release | automatic at block end | **you** must `unlock()` in `finally` |
| Try without waiting | no | `tryLock()` / `tryLock(timeout)` |
| Interruptible wait | no | `lockInterruptibly()` |
| Fairness option | no | `new ReentrantLock(true)` |

```java
private final ReentrantLock lock = new ReentrantLock();

boolean transfer() throws InterruptedException {
    if (!lock.tryLock(200, TimeUnit.MILLISECONDS)) {
        return false;                 // give up instead of hanging (avoids deadlock pile-up)
    }
    try {
        // critical section
        return true;
    } finally {
        lock.unlock();                // ALWAYS in finally
    }
}
```

**Say:** default to `synchronized` for simplicity; reach for `ReentrantLock` when you need a timeout,
interruption, or fairness. Prefer atomics / `ConcurrentHashMap` over either when they fit.

---

## Q100. What does `@SpringBootApplication` do?

It is a shortcut for **three** annotations:

| Annotation | Job |
|---|---|
| `@SpringBootConfiguration` | marks the class as a configuration class (`@Configuration`) |
| `@EnableAutoConfiguration` | turns on auto-configuration from classpath + properties |
| `@ComponentScan` | scans the **package of this class and below** for `@Component` beans |

```java
@SpringBootApplication            // put this in the ROOT package: com.shop
public class ShopApplication {
    public static void main(String[] args) {
        SpringApplication.run(ShopApplication.class, args);
    }
}
// com.shop.order.OrderService      -> found (sub-package)
// com.other.AuditService           -> NOT found (outside the scan root)
```

**Common bug:** a bean "is not found" because it lives outside the root package. Fix by moving it, or
`@SpringBootApplication(scanBasePackages = {...})`.

---

## Q101. Explain the Spring bean lifecycle.

Order for a singleton bean:

1. Instantiate (constructor)
2. Inject dependencies
3. Aware callbacks (`BeanNameAware`, ...)
4. `BeanPostProcessor.postProcessBefore...`
5. **`@PostConstruct`** / `afterPropertiesSet()` - init logic
6. `BeanPostProcessor.postProcessAfter...` (**AOP proxies are created here**)
7. Bean ready, in use
8. **`@PreDestroy`** on context shutdown

```java
@Component
class PriceCache {
    private final Map<String, Double> prices = new HashMap<>();

    @PostConstruct void warmUp()  { prices.put("A", 10.0); }  // runs once, after injection
    @PreDestroy   void shutdown() { prices.clear(); }          // runs on graceful shutdown
}
```

**Say:** do not call overridable or DB-heavy code in the constructor - dependencies are not ready yet. Use
`@PostConstruct` (or `ApplicationRunner`) for start-up work.

---

## Q102. PUT vs PATCH?

- **PUT** = **replace** the whole resource. Idempotent. Missing fields are reset/cleared.
- **PATCH** = **partial** update of only the fields sent. Idempotent only if the patch is (e.g. "set status =
  SHIPPED" yes, "add 1 to quantity" no).

```http
GET /users/7        ->  {"name":"Asha","city":"Pune","phone":"111"}

PUT /users/7        {"name":"Asha","city":"Mumbai"}
                    ->  {"name":"Asha","city":"Mumbai"}            (phone is GONE)

PATCH /users/7      {"city":"Mumbai"}
                    ->  {"name":"Asha","city":"Mumbai","phone":"111"}  (phone kept)
```

**Say:** PUT also works as create-or-replace when the client chooses the id. Return `200` with the body or
`204` with none; `404` if the resource does not exist and you do not upsert.

---

## Q103. Retry vs circuit breaker?

They solve **different** problems and are used together.

| | Retry | Circuit breaker |
|---|---|---|
| Assumes | the failure is **transient** | the dependency is **down / degraded** |
| Does | tries the same call again | **stops calling** for a while |
| Protects | the caller's success rate | the dependency **and** the caller's threads |
| Risk if alone | **retry storm** hammers a sick service | needs a sensible fallback |

States: **CLOSED** (normal) -> failures cross threshold -> **OPEN** (fail fast, no calls) -> after wait ->
**HALF-OPEN** (let a few probes through) -> success => CLOSED, failure => OPEN.

```java
// Resilience4j-style: retry sits INSIDE the breaker
@CircuitBreaker(name = "payment", fallbackMethod = "pending")
@Retry(name = "payment")                      // 3 attempts, 200ms backoff
public Receipt pay(Order o) { return paymentClient.charge(o); }

Receipt pending(Order o, Throwable t) {       // fallback: degrade, do not crash
    return Receipt.pending(o.id());
}
```

**Rules:** retry only idempotent calls, with **exponential backoff + jitter + max attempts**; never retry
`4xx`; always pair with a **timeout**.

---

## Q104. Timeout and bulkhead - why do they matter?

- **Timeout:** without one, a slow dependency holds your threads forever -> thread pool exhaustion -> your
  service looks "down" though only a dependency is slow. Set connect + read timeouts on every outbound call.
- **Bulkhead:** give each dependency its **own small pool/semaphore** so one slow dependency cannot consume all
  threads (like ship compartments).

```java
// Payments may use at most 10 concurrent calls; the rest fail fast
@Bulkhead(name = "payment", type = Bulkhead.Type.SEMAPHORE)
public Receipt pay(Order o) { ... }
```

Example: pool = 200 threads. Reports API hangs for 30 s. Without a bulkhead all 200 threads end up stuck on
Reports and **Orders stops working too**. With a 20-call bulkhead on Reports, 180 threads stay free.

---

## Q105. What is a Kafka retry topic and how does it work?

Retrying inside the consumer **blocks the partition** (head-of-line blocking) and risks `max.poll.interval.ms`
timeouts. A retry topic moves the failed record **aside** so the main flow keeps moving.

```
orders  --fail-->  orders.retry.1 (wait 1 min)  --fail-->  orders.retry.2 (wait 10 min)
                                                              --fail-->  orders.DLT  (human / replay)
```

```java
try {
    process(record);
} catch (TransientException e) {
    producer.send(new ProducerRecord<>("orders.retry.1", record.key(), record.value()));
    // then commit the offset of the ORIGINAL record: it is safely parked
} catch (PoisonMessageException e) {
    producer.send(new ProducerRecord<>("orders.DLT", record.key(), record.value()));
}
```

Spring Kafka offers this out of the box: `@RetryableTopic(attempts = "4", backoff = @Backoff(delay = 1000, multiplier = 2))`.

**Trade-offs:** ordering for that key is lost once a record is parked; consumers must be **idempotent**;
keep original headers (attempt count, original topic, error); alert on DLT depth.

---

## Q106. What happens when a Kafka consumer dies?

Timeline (consumer group `billing`, 3 consumers, 6 partitions, 2 each):

1. Consumer C2 crashes (or is OOM-killed / loses network).
2. It stops sending heartbeats. Broker waits `session.timeout.ms` (e.g. 10 s), **or** if it is alive but not
   calling `poll()` within `max.poll.interval.ms`, it is kicked out.
3. Group coordinator triggers a **rebalance**; C2's partitions go to C1 and C3 (now 3 each).
4. New owners resume from the **last committed offset** of each partition.

```
Before: C1[P0,P1]  C2[P2,P3]  C3[P4,P5]
After : C1[P0,P1,P2]  C3[P3,P4,P5]        (C2 dead)
```

**Consequences to mention:** messages processed but not yet committed are **re-delivered** -> duplicates ->
idempotent processing needed; lag rises briefly during the rebalance; with `CooperativeStickyAssignor` only
the moved partitions pause. Fix a crash loop by finding the poison message, not by adding consumers.

---

## Q107. Traffic jumps from 100 TPS to 600 TPS. What do you do?

**Step 1 - measure, do not guess:** find the bottleneck (CPU, DB connections, a slow downstream, thread pool,
partition count). **Step 2 - do the math:**

```
Little's Law:  concurrency = TPS x latency
100 TPS x 0.2 s =  20 in-flight requests     (current)
600 TPS x 0.2 s = 120 in-flight requests     (needed)
Each instance handles ~40 concurrently  ->  120 / 40 = 3 instances (+ headroom => 4-5)
```

**Step 3 - apply the smallest safe levers, in order:**

1. **Scale out** stateless instances (HPA) behind the load balancer.
2. **Cache** read-heavy data (Redis / Caffeine) to cut DB hits.
3. **Make non-urgent work async** - accept, put on Kafka, process in the background.
4. **Protect dependencies** - connection pool sizing, timeouts, circuit breakers, rate limiting / load
   shedding (`429`) rather than falling over.
5. **DB** - indexes, read replicas, batching; the DB is usually the real limit, not the app.
6. **Kafka** - partitions >= consumers needed; scale consumers; tune `max.poll.records`.

**Validate:** load test to 600 (and 1,200 for headroom), watch p95/p99 latency, error rate, CPU, pool wait.

---

## Q108. Aggregate 3-5 downstream APIs and answer in under 10 seconds?

Call them **in parallel**, give each its **own timeout**, and return a **partial result** if one is slow.
Total time ~ the slowest call, not the sum.

```java
ExecutorService pool = Executors.newFixedThreadPool(10);   // bounded, not the common pool

CompletableFuture<Customer> c = CompletableFuture.supplyAsync(() -> customerApi.get(id), pool)
        .completeOnTimeout(Customer.unknown(), 3, TimeUnit.SECONDS);       // fallback value
CompletableFuture<List<Offer>> o = CompletableFuture.supplyAsync(() -> offerApi.get(id), pool)
        .completeOnTimeout(List.of(), 3, TimeUnit.SECONDS);
CompletableFuture<Payment> p = CompletableFuture.supplyAsync(() -> paymentApi.get(id), pool)
        .orTimeout(5, TimeUnit.SECONDS);                                    // this one is mandatory

CompletableFuture.allOf(c, o, p).join();
return new Dashboard(c.join(), o.join(), p.join());
```

```
Sequential: 2s + 2s + 3s = 7s     Parallel: max(2,2,3) = 3s
```

**Say:** mark which calls are **mandatory** (fail the request) vs **optional** (degrade with a default);
add circuit breakers per downstream; if the total still risks the 10 s SLA, return `202 Accepted` + poll,
or precompute/cache the aggregate.

---

## Q109. How do you achieve zero-downtime deployment?

Goal: users never see errors while the new version replaces the old.

| Technique | How |
|---|---|
| **Rolling update** | replace instances a few at a time (`maxUnavailable: 0`) |
| **Readiness probe** | do not send traffic until the new pod is truly ready |
| **Graceful shutdown** | old pod finishes in-flight requests before exit |
| **Blue/green** | two full environments, flip the router, instant rollback |
| **Canary** | send 5% to the new version, watch errors, then widen |
| **Backward-compatible changes** | old and new versions run **side by side** |

```yaml
# Spring Boot: stop accepting, finish in-flight work
server.shutdown: graceful
spring.lifecycle.timeout-per-shutdown-phase: 30s
```

```yaml
# Kubernetes
strategy: { type: RollingUpdate, rollingUpdate: { maxUnavailable: 0, maxSurge: 1 } }
readinessProbe: { httpGet: { path: /actuator/health/readiness, port: 8080 } }
```

**The hard part is the database:** use **expand -> migrate -> contract**. Add the new column (nullable),
deploy code that writes both, backfill, switch reads, and only later drop the old column. Never rename or
drop a column in the same release the code stops using it. Kafka consumers must tolerate old/new event
schemas (add optional fields only).

---

## Q110. What is distributed tracing and how does it work?

A request crosses many services; tracing **links all its logs and timings** with one **trace ID**; each
service hop is a **span**.

```
Client -> Gateway -> Order -> Payment -> Kafka -> Notification
          traceId=abc123 is propagated through every hop
          Order span 40ms | Payment span 900ms  <- slow hop is visible immediately
```

- HTTP: the ID travels in a header (`traceparent` / `X-B3-TraceId`). Kafka: in **record headers**.
- Each service puts the ID into **MDC** so every log line carries it.

```java
// log pattern includes %X{traceId};  Micrometer Tracing / OpenTelemetry does the propagation
log.info("Charging order {}", orderId);
// 2026-01-05 10:00:01 INFO [order-svc,abc123,9f2c] Charging order 42
```

**Splunk:** `index=prod traceId=abc123 | sort _time` shows the entire journey across services.
**Say:** logs = what happened, metrics = how much, traces = where the time went.

---

## Q111. Payment service is slow and Kafka lag is increasing. What do you do?

**1. Confirm the symptom** - which consumer group/topic; is lag growing or just a spike; since when (what
changed - deploy, traffic, dependency)?

**2. Find the bottleneck** - check Payment's p95/p99 latency, error rate, thread/connection pool, DB or
downstream calls; check consumer `poll` time vs processing time.

```
Lag grows when:  arrival rate  >  processing rate
Processing rate per consumer = 1 / time_per_message   e.g. 1 / 0.5 s = 2 msg/s
Arrival 100 msg/s  ->  need >= 50 consumers (or make each message faster)
```

**3. Stabilize first (smallest safe change)**

- Add a **timeout** + **circuit breaker** on the payment call so threads stop piling up.
- If Payment is down/slow: **pause the consumer** (`consumer.pause()`) or let it fail fast to a retry topic -
  do not burn retries on a dependency that is down.
- Scale consumers **only up to the partition count**; beyond that they sit idle.
- Batch / parallelize processing inside a consumer if work is I/O-bound (keep per-key ordering).

**4. Fix root cause** - payment DB slow query, pool too small, N+1 calls, missing index.

**5. Recover** - once healthy, scale consumers temporarily to drain the backlog; confirm lag -> 0.

**6. Prevent** - alert on lag trend (not just value), SLO for payment latency, load test, runbook.

Mention idempotency: retries and rebalances will re-deliver, so a payment must be keyed by an
**idempotency key** (e.g. `orderId`) to avoid charging twice.

---

## Q112. What is an API Gateway and why use one?

A single entry point in front of microservices. It handles **cross-cutting concerns** so each service does not
re-implement them.

| Concern | Example |
|---|---|
| Routing | `/orders/**` -> order-service |
| AuthN/AuthZ | validate JWT once |
| Rate limiting | 100 req/min per client, else `429` |
| TLS, CORS, logging | at the edge |
| Aggregation / BFF | combine 3 calls into 1 for a mobile app |

```yaml
# Spring Cloud Gateway
spring.cloud.gateway.routes:
  - id: orders
    uri: lb://order-service
    predicates: [ Path=/orders/** ]
    filters:    [ StripPrefix=0 ]
```

**Trade-off:** it is a **single point of failure** and a possible bottleneck - run it highly available,
keep business logic **out** of it, and still secure the services behind it (do not trust the network).

---

## Q113. Explain the CAP theorem.

During a **network Partition**, a distributed store must choose between **Consistency** (every read sees
the latest write) and **Availability** (every request gets a response). Partition tolerance is not optional in
a real network, so the real choice is **CP vs AP**.

| Choice | Behaviour during a partition | Typical |
|---|---|---|
| **CP** | refuses/blocks some requests to stay correct | MongoDB (primary), HBase, ZooKeeper |
| **AP** | answers always, may return stale data, reconciles later | Cassandra, DynamoDB (default) |

```
Bank balance      -> choose C  (better to reject than show a wrong balance)
Product "likes"   -> choose A  (a slightly stale count is fine)
```

**Say:** Cassandra is "tunable": `QUORUM` reads+writes (R + W > N) give strong consistency, `ONE` gives speed
and availability. Mention **eventual consistency** is the price of AP, and design for it (idempotency,
conflict resolution).

---

## Q114. Why use `ExecutorService` instead of `new Thread()`, and how do you size it?

`new Thread()` per task is unbounded (memory + context switching) and has no reuse, queueing or shutdown
control. A **thread pool** reuses threads and gives back-pressure.

```java
ExecutorService pool = new ThreadPoolExecutor(
        4, 8,                                   // core, max threads
        60, TimeUnit.SECONDS,
        new ArrayBlockingQueue<>(100),          // BOUNDED queue
        new ThreadPoolExecutor.CallerRunsPolicy());   // back-pressure when full

Future<String> f = pool.submit(() -> callApi());
// ... on shutdown:
pool.shutdown();
```

**Sizing:**

```
CPU-bound : threads ~ cores (+1)
I/O-bound : threads ~ cores x (1 + wait_time / compute_time)    e.g. 8 x (1 + 9) = 80
```

**Pitfalls:** `Executors.newFixedThreadPool` uses an **unbounded** queue (can OOM);
`newCachedThreadPool` can create unbounded threads; always `shutdown()`; name your threads for debugging.
On Java 21, virtual threads (`Executors.newVirtualThreadPerTaskExecutor()`) suit blocking I/O.

---

---

## Q115. Producer `acks=0 / 1 / all`?

`acks` = how many brokers must confirm a write.

| acks | Confirmed by | Risk | Use for |
|---|---|---|---|
| `0` | nobody | lost silently, even on a network blip | logs/metrics you can drop |
| `1` | leader only | lost if leader dies before followers copy | speed over safety |
| `all` | leader + all in-sync replicas | almost none (needs ISR to fail) | orders, payments |

```properties
acks=all
enable.idempotence=true
# topic: replication.factor=3, min.insync.replicas=2
```

**Say:** `acks=all` is only as strong as `min.insync.replicas`; with 3 replicas and min ISR 2 you survive one
broker loss without losing an acknowledged message.

---

## Q116. A Kafka consumer is slow. What do you do?

Slow consumer -> lag grows -> if one poll takes longer than `max.poll.interval.ms` the consumer is kicked out and
the group rebalances (it gets worse).

1. **Measure where time goes:** your processing code (DB / HTTP call) vs poll vs commit vs rebalances.
2. **Fix the slow part:** timeout + batch DB writes + cache; lower `max.poll.records` so a batch fits in the time budget.
3. **Parallelise:** more consumers up to the **partition count**; or `concurrency=N` in `@KafkaListener`.
4. **Poison message?** send to retry topic / DLT instead of retrying forever.

```java
@KafkaListener(topics = "orders", concurrency = "3")   // needs >= 3 partitions
void handle(Order o) { service.process(o); }           // keep it fast and idempotent
```

---

## Q117. How do you tune Kafka performance?

| Where | Setting | Effect |
|---|---|---|
| Producer | `batch.size` + `linger.ms` | bigger batches, more throughput |
| Producer | `compression.type=lz4` | less network, a bit of CPU |
| Consumer | `max.poll.records`, `fetch.min.bytes` | per-poll work and fetch size |
| Consumer | commit per **batch**, not per record | fewer round-trips |
| Topic | partitions | parallelism ceiling |
| App | batch DB writes, fast serializer | usually the biggest win |

**Rules:** measure first, change one thing at a time, never trade durability for speed without agreeing the loss
tolerance.

---

## Q118. Exactly-once semantics - what is it really?

- **Idempotent producer** (`enable.idempotence=true`): retries do not create duplicates.
- **Transactions** (`transactional.id`): write to several topics + commit consumer offsets **atomically**;
  consumers use `isolation.level=read_committed`.
- Works **inside Kafka** (read-process-write). It does **not** make an HTTP call or DB update exactly once.

```java
producer.beginTransaction();
producer.send(new ProducerRecord<>("out", key, value));
producer.sendOffsetsToTransaction(offsets, consumer.groupMetadata());
producer.commitTransaction();
```

**Say:** for external side effects use at-least-once + an idempotent handler (unique key / upsert).

---

## Q119. Distributed transactions - why not 2PC?

2PC (two-phase commit) = coordinator asks all to *prepare*, then *commit*. It holds locks, has a single point of
failure, is as slow as the slowest participant, and Kafka / most NoSQL / REST do not support it.

Use instead: **Saga** (local transactions + compensations) + **outbox** (event published atomically) +
**idempotent consumers**.

```
Order PENDING -> reserve stock -> charge payment -> Order CONFIRMED
payment fails -> release stock (compensation) -> Order REJECTED
```

---

## Priority-list check (all five groups)

Every item of the priority list is now answered somewhere. The item-by-item table is at the end of
[`deep_dive/19_docx_gap_topics.md`](deep_dive/19_docx_gap_topics.md#priority-checklist-coverage-the-five-priority-groups).

---

## 2. Quick self-check (answer aloud in 30 s each)

1. Why is `ConcurrentHashMap.get` + `put` still a race? What replaces it?
2. Which annotation would you change if a bean in `com.other` is not found?
3. Retry + circuit breaker: which wraps which, and why does retry need backoff and jitter?
4. A consumer dies mid-batch: what is re-delivered and what protects you?
5. 100 -> 600 TPS: write the Little's Law line before you say "add pods".
6. Why can a slow Reports API break Orders, and which pattern prevents it?
7. What is the expand -> migrate -> contract sequence for dropping a DB column?
8. Where does the trace ID travel for HTTP and for Kafka?
