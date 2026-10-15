---
id: round-spring-boot
title: Real interview round: Spring Boot, circuit breaker and conditional beans
stack: java
skill: spring-boot
---
Questions asked in a real interview round, answered from the basics.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [senior] What is a circuit breaker and how do you implement it in Spring Boot? Provide one example.
tags: circuit-breaker, resilience4j, fallback, fault-tolerance, spring-boot, microservices, basics

**Start here: the concepts**
- **Cascading failure:** one slow or failing dependency makes callers wait, their threads pile up, and the failure spreads to the whole system.
- **Circuit breaker:** a guard around a remote call that **stops calling** a dependency that keeps failing, and fails fast instead. The name comes from an electrical breaker.
- **States:**
  - **Closed:** normal, calls go through and the breaker counts successes and failures.
  - **Open:** the failure rate crossed a threshold; calls are rejected immediately (or sent to a fallback) without touching the dependency.
  - **Half-open:** after a wait time, a few trial calls are allowed; if they succeed the breaker closes, if they fail it opens again.
- **Failure rate threshold:** the percentage of failed calls in the sliding window that opens the breaker.
- **Fallback:** the alternative response when the call cannot be made: cached data, a default, or a clear error.
- **Resilience4j:** the standard library for this in Spring Boot today. Netflix Hystrix is in maintenance mode and no longer recommended.

**The live scenario**
An order service calls a pricing service. One afternoon pricing starts taking 20 seconds and failing. Without protection every order request waits, Tomcat's 200 threads fill up, and the order service stops answering even for requests that do not need pricing. With a circuit breaker, after 10 failing calls the breaker opens; for the next 30 seconds order requests fail in a few milliseconds with a "prices temporarily unavailable" fallback, threads stay free, and pricing gets room to recover. Then a few trial calls close the breaker automatically.

**What the interviewer is really checking**
That you understand the three states and why failing fast protects the caller, and that you can wire it with Resilience4j, including the fallback and the key settings.

**How I answer it**
1. **Define the problem:** a slow dependency consumes threads and spreads the outage; the breaker cuts that off.
2. **Add the dependencies:** `resilience4j-spring-boot3`, plus `spring-boot-starter-aop` (the annotations are applied through proxies) and Actuator for visibility.
3. **Configure it:**

```yaml
resilience4j:
  circuitbreaker:
    instances:
      pricing:
        sliding-window-size: 20
        minimum-number-of-calls: 10
        failure-rate-threshold: 50
        wait-duration-in-open-state: 30s
        permitted-number-of-calls-in-half-open-state: 3
        slow-call-duration-threshold: 2s
        slow-call-rate-threshold: 50
```

4. **Annotate the call and give a fallback:**

```java
@Service
class PricingClient {
    @CircuitBreaker(name = "pricing", fallbackMethod = "cachedPrice")
    public Price getPrice(String sku) {
        return restClient.get().uri("/prices/{sku}", sku).retrieve().body(Price.class);
    }

    Price cachedPrice(String sku, Throwable t) {          // same params + exception
        return priceCache.getOrDefault(sku, Price.unavailable(sku));
    }
}
```

5. **Pair it with a timeout** on the HTTP client (and optionally Resilience4j `TimeLimiter`); a breaker cannot open if calls hang forever.
6. **Observe it:** `/actuator/health` shows breaker state, `/actuator/circuitbreakers` and Micrometer metrics (`resilience4j_circuitbreaker_state`, failure rate, not-permitted calls).
7. **Decide what the fallback is:** stale cache for reads; a clear error or queued retry for writes; never silently pretend a payment succeeded.

**Trade-offs and what can go wrong**
- Thresholds that are too sensitive open the breaker on harmless blips; too lax and it protects nothing. Tune from real latency and error data.
- The annotation works only on calls that go through the Spring proxy: a method calling another method in the same class bypasses it.
- Fallbacks hide failures; always count and alert on them.
- A breaker per dependency, not one global breaker, so one bad vendor does not block healthy ones.
- Combine with retries carefully: retry inside the breaker's view and with backoff, not in a tight loop.

**How I'd monitor it**
Breaker state per instance, failure rate, slow-call rate, number of not-permitted calls, fallback invocations, and the downstream latency percentiles, with an alert when a breaker stays open.

**Follow-ups to expect**
- *Circuit breaker vs retry vs timeout vs bulkhead?* -> timeout bounds one call, retry repeats transient failures, bulkhead limits concurrency per dependency, breaker stops calling a failing dependency.
- *What happens in the half-open state?* -> a limited number of trial calls decide whether to close or reopen.
- *Hystrix?* -> deprecated; use Resilience4j or Spring Cloud CircuitBreaker, which wraps it.
- *How do you test it?* -> force the dependency to fail in an integration test and assert the fallback and state transitions.

**60-second answer**
A circuit breaker wraps a remote call and, once failures cross a threshold, opens and fails fast instead of piling up threads on a broken dependency. It has closed, open and half-open states; after a wait it lets a few trial calls through to see if the dependency recovered. In Spring Boot I use Resilience4j: add the starter, configure the window size, failure-rate threshold and wait duration, annotate the method with `@CircuitBreaker` and provide a fallback method. I add a timeout and monitor the state through Actuator and Micrometer.

### Q2 [mid] What is the use of a conditional bean, and in what scenario do we use it?
tags: conditional, conditionalonproperty, conditionalonmissingbean, auto-configuration, profiles, feature-flag, spring-boot, basics

**Start here: the concepts**
- **Bean:** an object created and managed by the Spring container.
- **Condition:** a rule evaluated when Spring is deciding whether to register a bean definition; if it is false the bean is simply not created.
- **`@Conditional`:** the base annotation; Spring Boot provides ready-made variants such as `@ConditionalOnProperty`, `@ConditionalOnClass`, `@ConditionalOnMissingBean`, `@ConditionalOnBean`, `@ConditionalOnWebApplication` and `@ConditionalOnExpression`.
- **Auto-configuration:** Spring Boot's own configuration classes use these conditions heavily to decide what to create from the classpath and properties.

**The live scenario**
A payments service must use a real gateway in production but a fake gateway in tests and local runs, and a new "express checkout" feature must be switchable per environment without a redeploy of code. Rather than `if` statements scattered through the code, the team defines two beans and marks the fake with `@ConditionalOnProperty("payments.mode=fake")`. Production configuration sets nothing, so the real gateway is created; developers set the property and get the fake. Another time a library provides a default `ObjectMapper` with `@ConditionalOnMissingBean`, so the team's own bean silently replaces it.

**What the interviewer is really checking**
That you can name the common conditions and describe real uses: feature toggles, environment-specific implementations, optional libraries, and "back off if the user defined their own".

**How I answer it**
1. **Purpose:** decide *at startup* whether a bean should exist, based on properties, classpath, other beans or the environment, without changing code.
2. **Typical scenarios:**
   - **Feature flag:** `@ConditionalOnProperty(name = "feature.express", havingValue = "true")`.
   - **Environment-specific implementation:** a fake or stub in dev, real in prod (or use `@Profile`).
   - **Optional dependency:** `@ConditionalOnClass(KafkaTemplate.class)` creates Kafka beans only if Kafka is on the classpath.
   - **Default that users can override:** `@ConditionalOnMissingBean` creates a default only if the application has not defined one; this is how Boot auto-configuration lets you replace its beans.
   - **Web or non-web context:** `@ConditionalOnWebApplication`.
3. **Example:**

```java
@Configuration
class PaymentConfig {
    @Bean @ConditionalOnProperty(name = "payments.mode", havingValue = "fake")
    PaymentGateway fakeGateway() { return new FakeGateway(); }

    @Bean @ConditionalOnMissingBean(PaymentGateway.class)
    PaymentGateway realGateway() { return new BankGateway(); }
}
```

4. **Custom conditions:** implement `Condition` and use `@Conditional(MyCondition.class)` when none of the built-ins fit.
5. **Debug it:** run with `--debug` or open the `conditions` Actuator endpoint to see which conditions matched and why.

**Trade-offs and what can go wrong**
- Conditions are evaluated at startup; they do not switch at runtime (use feature-flag services for that).
- `@ConditionalOnBean` and `@ConditionalOnMissingBean` depend on bean registration order; they are reliable inside auto-configuration classes but can surprise in ordinary configuration.
- Too many conditions make the real wiring hard to understand; document them and test each combination that matters.
- Prefer `@Profile` for simple environment switches and conditions for property or classpath logic.

**Follow-ups to expect**
- *`@Profile` vs `@ConditionalOnProperty`?* -> `@Profile` switches on the active profile name; `@ConditionalOnProperty` on any property value.
- *How does Spring Boot back off when I define my own bean?* -> `@ConditionalOnMissingBean` on its default.
- *How do you see what was applied?* -> the condition evaluation report (`--debug`) or `/actuator/conditions`.

**60-second answer**
A conditional bean is a bean that Spring registers only if a rule is true at startup, such as a property value, a class on the classpath, or the absence of another bean. I use it for feature toggles with `@ConditionalOnProperty`, environment-specific implementations like a fake gateway in tests, optional integrations with `@ConditionalOnClass`, and defaults the application can override with `@ConditionalOnMissingBean`. Spring Boot's auto-configuration is built on the same mechanism, and I debug it with the condition evaluation report.
