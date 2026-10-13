# Testing: unit, slice, integration, contract tests and test doubles

> **Runnable:** [`01_test_doubles_and_mockito_by_hand.java`](../examples/15_testing/01_test_doubles_and_mockito_by_hand.java)
> **Crib sheet:** [`topics/18-testing-cicd-quality.md`](../topics/18-testing-cicd-quality.md) · **Guide:** Q38

## What interviewers are actually probing

How you get *confidence* cheaply: the shape of your test suite, what you mock and what you refuse to mock, and how you test the
parts that fail in production (database behaviour, messaging, timeouts, concurrency). "We have 80% coverage" is a weak answer; "we have a few fast, meaningful tests per behaviour and Testcontainers for the infrastructure edges" is a strong one.

## Must-know points

- Pyramid: many fast unit tests → fewer slice/integration tests → very few end-to-end. Add **contract tests** between services.
- **State** vs **interaction** testing: assert on results first; verify calls only where the call *is* the behaviour (e.g. "email sent").
- Test doubles: **dummy** (placeholder), **stub** (canned answers), **fake** (working lightweight impl), **spy** (records calls), **mock** (verifies interactions).
- Prefer real infrastructure via **Testcontainers** over H2/embedded fakes when engine behaviour matters.
- Deterministic tests: inject `Clock`, random seeds, and wait with Awaitility, never `Thread.sleep`.
- Flaky tests are production bugs in the test suite; quarantine and fix.

## Interview questions and full answers

### Q1. How do you structure tests for a Spring Boot service?

Unit tests for domain/service logic with plain JUnit 5 and constructor-injected fakes (no Spring context, milliseconds).
`@WebMvcTest` for controllers (routing, validation, JSON, error mapping, security rules with `MockMvc`); `@DataJpaTest` + Testcontainers for repositories and queries; `@SpringBootTest` with a random port for a handful of full-stack flows;
Kafka via `@EmbeddedKafka`/Testcontainers; contract tests for APIs and events. Keep the heavy tests few and the context cached (same configuration → same Spring context).

### Q2. Mock vs stub vs fake vs spy?

(See example 15 sections 1–2.) A **stub** returns canned data so the unit under test can proceed. A **fake** is a simplified working implementation (in-memory repository) — great for state-based tests.
A **spy** wraps/records real calls. A **mock** is a pre-programmed object that **verifies expectations**. Over-mocking couples tests to implementation: every refactor breaks them.

### Q3. What should you not mock?

The class under test, value objects/records, JDK types, and the database/ORM when you're testing queries, transactions or mapping — use a real engine in a container. Mock *ports* (HTTP clients, clocks, publishers) at your own boundary, ideally behind an interface you own.

### Q4. How do you test a REST controller?

```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
    @Autowired MockMvc mvc;
    @MockBean OrderService service;

    @Test void createsOrder() throws Exception {
        when(service.create(any())).thenReturn(new OrderDto(7L, "PAID"));
        mvc.perform(post("/orders").contentType(APPLICATION_JSON).content("{\"customer\":\"a\",\"amount\":10}"))
           .andExpect(status().isCreated())
           .andExpect(header().string("Location", "/orders/7"))
           .andExpect(jsonPath("$.status").value("PAID"));
    }
    @Test void rejectsInvalidAmount() throws Exception {
        mvc.perform(post("/orders").contentType(APPLICATION_JSON).content("{\"customer\":\"a\",\"amount\":-1}"))
           .andExpect(status().isBadRequest());
    }
}
```

Also test: 404 mapping through the `@ControllerAdvice`, 401/403 with `@WithMockUser`/JWT post-processors, and the `ProblemDetail` shape.

### Q5. How do you test code that talks to Kafka?

Unit-test the handler logic as a plain method (idempotency, mapping, failure classification). Integration-test the wiring with **Testcontainers `KafkaContainer`** (or `@EmbeddedKafka`): publish, assert the DB effect with Awaitility, publish a duplicate and assert no second effect, publish a poison message and assert it lands in the DLT.
Test **redelivery** explicitly — it is the bug you'll actually have.

### Q6. What is Testcontainers and why prefer it to H2?

It starts real dependencies (PostgreSQL, Kafka, Couchbase, Redis) in Docker per test run, so SQL dialect, locking, JSON columns, collation and transaction behaviour match production. H2's compatibility mode hides differences (and passes tests that fail on prod).
Costs: Docker in CI and slower startup — mitigate with singleton containers reused across test classes and the Spring context cache.

### Q7. How do you test time- and concurrency-dependent code?

Inject `java.time.Clock` (fixed/mutable in tests); expose schedulers/executors so tests can use a direct executor; use **Awaitility** (`await().atMost(...).untilAsserted(...)`) instead of sleeps; for concurrency, run N threads with a `CountDownLatch` start gate and assert invariants, and run repeatedly; consider jcstress for memory-model-level tests.

### Q8. How do you test resilience (timeouts, retries, circuit breakers)?

Use WireMock/MockServer to inject latency and 5xx; assert the client times out within the budget, retries only idempotent calls the expected number of times, opens the breaker, and returns the fallback. Add a Toxiproxy-based test against a real broker/DB for connection drops. Verify the metrics/log lines too.

### Q9. What is TDD, and when do you actually use it?

Red → green → refactor: write a failing test for the next behaviour, make it pass simply, then clean up. It shines for **domain logic, algorithms and bug fixes** (write the failing regression test first). It is less valuable for glue code, UI wiring and exploratory spikes. Say what you do in practice, not the textbook.

### Q10. What makes a unit test good?

Fast, isolated, deterministic, readable (Arrange/Act/Assert, one behaviour), named for behaviour (`rejectsOrderWhenStockIsZero`), failing for one reason, and independent of order. Test through the public API; avoid asserting private details. Use test data builders/object mothers to keep setup short.

### Q11. Code coverage and mutation testing?

Coverage shows what **isn't** executed, not what is verified. 70–80% on critical logic is a healthy signal; chasing 100% produces assertion-free tests. **Mutation testing** (PIT) changes the code and checks tests fail — a better measure of test strength for core domain code. Add static analysis (SonarQube, SpotBugs, ArchUnit for architecture rules) and dependency scanning to the pipeline.

### Q12. How do you test database migrations?

Run Flyway/Liquibase against a Testcontainers database in CI from an **empty** schema and from the **previous release** schema with representative data; run the old application version against the new schema to prove expand-and-contract compatibility.

## A worked example

Run [`01_test_doubles_and_mockito_by_hand.java`](../examples/15_testing/01_test_doubles_and_mockito_by_hand.java). Notice the three styles testing the *same* service:
a state test with stub+fake+spy, an interaction test with a `Proxy`-based mock (this is essentially how Mockito works), and the last, deliberately failing assertion that shows the failure message format.

## Hands-on drills

1. Write `@WebMvcTest` tests for create/validation/404/403 of one controller.
2. Replace H2 with a PostgreSQL Testcontainer in one `@DataJpaTest` and find a difference.
3. Add Awaitility to assert an async Kafka consumer's DB effect, then publish a duplicate.
4. Add an ArchUnit rule: "controllers must not access repositories".
5. Make a time-based job testable by injecting a `Clock`.

## The 60-second spoken answer

"I keep a pyramid: fast unit tests on domain logic with fakes, controller and repository slices, and a few full-stack tests, with Testcontainers for the real
database and Kafka instead of H2. I assert on outcomes first and mock only at my boundaries, never the class under test. I test the failure paths
that actually bite: redelivery and duplicates, timeouts and retries with WireMock, and migrations against the previous schema. Coverage is a floor, not a goal."
