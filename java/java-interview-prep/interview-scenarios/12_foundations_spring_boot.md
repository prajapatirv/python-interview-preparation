---
id: foundations-spring-boot
title: Spring Boot from the basics: concepts, a real story, then the answer
stack: java
skill: spring-boot
---
These entries are written **from the ground up**: *Start here: the concepts* in plain words, then a real
production story, then the answer an interviewer expects.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What are Actuator, Micrometer, Prometheus and Grafana, and how do they fit together?
tags: actuator, micrometer, prometheus, grafana, metrics, observability, basics

**Start here: the concepts**
- **Metric:** a number measured over time, such as requests per second, heap used or request duration.
- **Actuator:** a Spring Boot module that adds production endpoints (`/actuator/health`, `/actuator/metrics`) to your app.
- **Micrometer:** the instrumentation library inside Spring Boot that *records* metrics; it is vendor-neutral, like SLF4J is for logging.
- **Prometheus:** a server that *pulls* (scrapes) metrics from your app every few seconds and stores them as time series.
- **Grafana:** a dashboard and alerting tool that *draws* graphs from Prometheus.

**The live scenario**
At 2 a.m. the on-call engineer is paged: "checkout latency high". Without metrics they would be guessing. With them, a Grafana dashboard shows p95 rose at 01:47, the Hikari pending connections graph rose at the same moment, and the `payments` timer shows the database call tripled. The chain made that visible: Micrometer recorded it, Actuator exposed it, Prometheus stored it, Grafana drew it.

**What the interviewer is really checking**
That you know each tool's role in the chain, not just the names, and that you can name useful metrics.

**How I answer it**
1. **The chain:** app code -> Micrometer (records) -> Actuator `/actuator/prometheus` (exposes) -> Prometheus (scrapes and stores) -> Grafana (dashboards, alerts).
2. **Add the dependencies** `spring-boot-starter-actuator` and `micrometer-registry-prometheus`, and include the endpoint in `management.endpoints.web.exposure.include`.
3. **Built-in metrics:** `http.server.requests`, `jvm.memory.used`, `jvm.gc.pause`, `process.cpu.usage`, `hikaricp.connections.*`.
4. **Add business metrics:** a `Counter` or `Timer` through `MeterRegistry`, for example `orders.placed`.
5. **Production care:** expose only the endpoints you need, on an internal management port, and keep tags low-cardinality.

**Trade-offs and what can go wrong**
Metrics are not exposed by default, which is why the endpoint returns 404 until included. Tags such as user id explode series count and overload Prometheus.

**How I'd monitor it**
Alert on p95 against an SLO, error rate, and saturation, with Prometheus' own `up` metric to catch a service that stopped being scraped.

**60-second answer**
Micrometer records metrics in the app, Actuator exposes them over HTTP, Prometheus scrapes and stores them, and Grafana draws dashboards and alerts. I add business metrics through `MeterRegistry`, expose only the endpoints needed on an internal port, and keep tags bounded.

### Q2 [mid] Why does `@Transactional` sometimes not work, for example when one method calls another in the same class?
tags: transactional, proxy, aop, self-invocation, rollback, spring, basics

**Start here: the concepts**
- **Transaction:** a group of database operations that either all succeed (commit) or all undo (rollback).
- **Proxy:** Spring wraps your bean in a stand-in object. Calls from *outside* go through the proxy, which starts and ends the transaction around your method.
- **Self-invocation:** a method calling another method on `this`, inside the same object. It bypasses the proxy, so no transaction logic runs.
- **Default rollback rule:** rollback on `RuntimeException` and `Error`; a checked exception does **not** roll back unless configured.

**The live scenario**
A service has `placeOrder()` (no annotation) that calls `this.saveOrder()` marked `@Transactional`. Under load a failure after the insert leaves half-written data: the order row exists but its payment row does not. The annotation looked right, but because the call stayed inside the class it never went through the proxy, so there was no transaction at all.

**What the interviewer is really checking**
That you understand it is proxy-based and can list the common failure modes.

**How I answer it**
1. **Mechanism:** Spring AOP proxies the bean; the transaction exists only for calls that arrive through the proxy.
2. **Self-invocation:** call from another bean, or move the method into a separate service, or inject the proxy of the bean itself; avoid `this.`.
3. **Visibility:** `private` or `final` methods are not proxied; use public methods.
4. **Rollback rules:** a checked exception commits unless `rollbackFor = Exception.class`; a caught-and-swallowed exception means the proxy sees a normal return and commits.
5. **Scope and cost:** keep transactions short; do not hold one across a remote HTTP call because it pins a database connection.
6. **Prove it:** enable SQL and transaction logging and check whether a transaction actually started.

**Trade-offs and what can go wrong**
Moving code to another bean fixes the proxy issue but adds structure. Long transactions exhaust the connection pool.

**How I'd monitor it**
Hikari active and pending, transaction duration timers, and `idle in transaction` sessions in the database.

**60-second answer**
`@Transactional` works through a proxy, so it only applies to calls that arrive through that proxy. A method calling another on `this` bypasses it, and private methods, checked exceptions and swallowed exceptions also defeat it. I put transactional methods in a separate bean, keep them short and verify with transaction logging.

### Q3 [mid] How does Spring Boot auto-configuration work, and how do you find out why a bean was or was not created?
tags: auto-configuration, conditional, starters, spring-boot, debug, basics

**Start here: the concepts**
- **Starter:** a dependency such as `spring-boot-starter-web` that pulls in a set of libraries.
- **Auto-configuration:** Spring Boot classes that create beans for you based on what is on the classpath and in your properties.
- **Conditional:** a rule on an auto-configuration, such as `@ConditionalOnClass` ("only if this class exists") or `@ConditionalOnMissingBean` ("only if you did not define your own").
- **Condition evaluation report:** a printout of every auto-configuration and why it matched or not.

**The live scenario**
A team adds a Redis starter and a `RedisTemplate` appears with no configuration. Later they define their own `DataSource` bean and Boot's default silently backs off. Another day an expected `ObjectMapper` setting has no effect because a second mapper bean was defined and the auto-configured one was skipped. They solve all three by reading the condition report.

**What the interviewer is really checking**
That you know auto-configuration is conditional and overridable, and that you can debug it.

**How I answer it**
1. **Mechanism:** `@SpringBootApplication` enables auto-configuration, which loads candidate classes from the `AutoConfiguration.imports` file in each starter.
2. **Each candidate is conditional** on classes present, beans missing, properties set and similar.
3. **Your beans win:** `@ConditionalOnMissingBean` means defining your own bean replaces Boot's.
4. **Tuning:** use `application.properties` first, then your own bean, then exclude an auto-configuration if needed.
5. **Debugging:** run with `--debug` or `debug=true`, or use the `conditions` Actuator endpoint, to see matched and unmatched conditions with reasons.

**Trade-offs and what can go wrong**
Auto-configuration hides wiring, so surprises appear when two libraries both configure the same thing. Excluding too much loses defaults.

**How I'd monitor it**
Startup time and bean count, and a test that asserts critical beans exist.

**60-second answer**
Starters bring libraries; auto-configuration classes create beans conditionally on the classpath, properties and missing beans, and my own beans override Boot's. To debug I run with `--debug` or read the conditions endpoint to see why each auto-configuration matched or did not.
