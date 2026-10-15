---
id: foundations-testing
title: Testing & quality: from the basics (drafted)
stack: java
skill: testing
---
Drafted concepts-first answers for questions whose stored answer was too short. Each starts with the concepts in plain words, then a real scenario, then the answer. Review before relying on them.

Levels: **fresher** (0-2 yrs) · **mid** (3-6) · **senior** (6-10) · **architect** (10+).

### Q1 [fresher] What is the test pyramid?
tags: testing, test-pyramid, unit-tests, integration-tests, end-to-end-tests, junit5, testcontainers, basics

**Start here: the concepts**
- **Automated test:** code that runs your code and checks the result, so a machine can tell you "still works" in seconds instead of a person clicking around.
- **Unit test:** tests one small piece (a method or class) in isolation, with no database, network or Spring context. Tools: JUnit 5 to run it, Mockito to fake collaborators. It runs in milliseconds.
- **Mock/fake:** a stand-in for a dependency (say, a payment client) so you test only your own logic.
- **Integration test:** tests that several parts work together for real, such as your repository with a real database or your consumer with a real Kafka broker. Spring Boot test slices (e.g. `@DataJpaTest`) load only part of the app. Testcontainers starts throwaway Docker containers with the real database or broker. It runs in seconds.
- **End-to-end (E2E) test:** drives the whole deployed system the way a user would, often through a browser (UI) or a full API flow. It runs in minutes and breaks easily.
- **Flaky test:** one that sometimes fails with no code change (timing, shared data, network). Teams stop trusting flaky suites.
- **Contract test:** checks that two services agree on the shape of their API messages, without deploying both.
- **Test pyramid:** a picture of how many tests to write at each level. Wide base of unit tests, a middle layer of integration tests, a thin top of E2E tests.

**The live scenario**
A team of 8 had 40 E2E browser tests that took 55 minutes and failed randomly about 1 run in 4. Developers re-ran the pipeline until it went green and stopped trusting it. They had almost no unit tests. One Friday, a change to discount rounding (a wrong `<` instead of `<=`) shipped. About 3% of orders were overcharged by a few cents until Monday, and finance noticed. No E2E test covered that exact edge case, because covering every number combination through a browser was too slow. Afterwards they added about 200 unit tests for pricing rules, 30 Testcontainers integration tests for the repositories, and cut E2E to 6 critical journeys. The pipeline dropped to 9 minutes and the flakiness largely disappeared.

**What the interviewer is really checking**
Do you know what each test level protects against and what it costs, and can you explain why the shape is a pyramid (cost and speed), not just recite it?

**How I answer it**
1. **Define the three layers.** Many unit tests, fewer integration tests, very few E2E tests. This is the shape the pyramid describes.
2. **Explain the base.** Unit tests are fast and precise: a failure points at one method. So you can cover many edge cases cheaply and run them on every save.
3. **Explain the middle.** Unit tests with mocks cannot prove your SQL, JSON mapping or Kafka config work. Integration tests with real dependencies (Testcontainers, WireMock for HTTP) catch wiring bugs. Mocks only prove what you assumed.
4. **Explain the top.** E2E tests give the most realistic confidence but are slow, expensive and flaky, and a failure doesn't say where the problem is. So keep only critical journeys, such as login and checkout.
5. **Give the principle.** Test at the lowest level that can catch the bug. Test behaviour (inputs and outputs), not internal details, so refactoring doesn't break tests.
6. **Mention contract tests.** In microservices they sit between integration and E2E, catching API mismatches without a full environment.

**Trade-offs and what can go wrong**
- The pyramid is a guideline, not a law. Some services are mostly glue code, and integration tests may give more value than unit tests there.
- The "ice-cream cone" is the opposite and common: many E2E tests, few unit tests. It is slow, flaky and costly to maintain.
- Over-mocking makes unit tests pass while the real system is broken. Testing private methods or call order makes tests break on every refactor.
- Integration tests cost more: Docker in CI, slower startup. Reuse containers to keep them fast.
- Chasing a coverage percentage can lead to meaningless tests. Coverage shows what is not tested, not that the tests are good.

**How I'd monitor it**
- CI pipeline duration, split by test level. Fast feedback is the point.
- Flaky-test rate (failures that pass on re-run). Quarantine and fix them.
- Test counts per layer, to see whether the shape is drifting toward a cone.
- A CI quality gate: the build fails on failing tests, and on coverage dropping for new code.
- Escaped defects: production bugs per release. For each one, ask "which level should have caught this?" and add that test.

**Follow-ups to expect**
- *Why not just write E2E tests, since they're most realistic?* -> They are slow, flaky and hard to debug, so they give feedback too late. Use a few for key journeys and cover the rest lower down.
- *Should you mock the database in a unit test?* -> For business logic, yes. To check queries and mappings, use a real database with Testcontainers instead, because a mock cannot catch SQL mistakes.
- *Where do contract tests fit?* -> Between integration and E2E. They verify that a consumer and a provider agree on the API without running both in one environment.

**60-second answer**
The test pyramid says to have many fast unit tests, fewer integration tests and very few end-to-end tests. Unit tests are cheap and pinpoint bugs, so I use them for business rules and edge cases. Integration tests use real things like a database through Testcontainers, so they prove the wiring that mocks can't. End-to-end tests are realistic but slow and flaky, so I keep them for a few critical journeys such as checkout. The rule is to test at the lowest level that can catch the bug. Otherwise you end up with slow, untrusted pipelines, and bugs like a small rounding error can still reach production.

### Q2 [fresher] JUnit 5 essentials?
tags: junit5, unit-testing, assertions, parameterized-tests, extensions, assertj, basics

**Start here: the concepts**
- **Unit test**: a small automated check that runs one piece of code (usually one class or method) and confirms the result. It exists so you find bugs in seconds on your machine, not days later in production.
- **JUnit 5**: the standard Java testing framework. It finds your test methods, runs them, and reports pass or fail.
- **`@Test`**: marks a method as a test. If it finishes without an exception, it passes.
- **`@BeforeEach` / `@AfterEach`**: methods that run before and after every test. Use them for setup and cleanup so each test starts fresh and tests don't affect each other.
- **`@DisplayName`**: a readable name shown in reports, such as "rejects negative amount", instead of a method name.
- **Assertion**: a statement of what you expect. If it is false, the test fails.
- **`assertThrows`**: checks that the code throws a particular exception. It tests the failure path.
- **`assertAll`**: runs several assertions and reports every failure, instead of stopping at the first.
- **`@ParameterizedTest`**: runs one test many times with different inputs. `@CsvSource` puts the values inline as text rows. `@MethodSource` takes them from a method, which suits complex objects. It needs the `junit-jupiter-params` module, which `spring-boot-starter-test` already includes.
- **`@Nested`**: an inner (non-static) class that groups tests for one situation, such as "when the cart is empty".
- **Extension (`@ExtendWith`)**: a plug-in that hooks into the test lifecycle. Mockito's `MockitoExtension` and Spring's `SpringExtension` are examples. It replaces JUnit 4's runners and rules.
- **`@Tag`**: a label such as "slow" or "integration". The build can then run only some groups.
- **AssertJ**: a separate library (not part of JUnit) with fluent assertions like `assertThat(list).hasSize(2).contains("A")`. Its failure messages are clearer than the built-in ones.

**The live scenario**
An order service gave a 10% discount "for orders of 100 or more". The code used `> 100`, so an order of exactly 100 got no discount. The only test used 50 and 500, so it passed. For three days, about 1,200 customers with orders of exactly 100 were overcharged, and support received roughly 90 complaints. Afterwards the team added a `@ParameterizedTest` with rows for 99, 100 and 101. The test would have failed on day one.

**What the interviewer is really checking**
Whether you have actually written JUnit 5 tests and know which feature solves which problem. They also want to see that you test behaviour and edge cases, not just that you can list annotations.

**How I answer it**
1. **Start with `@Test` and a clear name.** Each test checks one behaviour, so a failure points straight at the problem. `@DisplayName` makes reports readable.
2. **Use `@BeforeEach` / `@AfterEach` for setup and cleanup.** They run around every test, so tests stay independent. `@BeforeAll` / `@AfterAll` run once per class, and they must be static unless you use `@TestInstance(PER_CLASS)`.
3. **Use `@ParameterizedTest` for the same logic with many inputs.** This is how you cover boundaries without copy-pasting:
   ```java
   @ParameterizedTest
   @CsvSource({"99,0", "100,10", "101,10"})
   void discount(int total, int expected) { assertEquals(expected, calc(total)); }
   ```
4. **Assert the failure path with `assertThrows`**, and use `assertAll` when one object has several fields to check. You see every wrong field in one run.
5. **Group with `@Nested`** so related tests read like a specification, and **label with `@Tag`** so the CI pipeline can run fast tests on every commit and slow ones nightly.
6. **Use `@ExtendWith` for reusable setup.** `MockitoExtension` creates mocks automatically. Writing your own extension avoids repeating the same setup code in every test class.
7. **Add AssertJ for readable assertions.** It is optional, but the code reads like a sentence and failure messages are more useful.

**Trade-offs and what can go wrong**
- Tests that depend on each other or on execution order become flaky. Keep each test independent.
- Testing private details (which method was called) instead of results makes tests break on every refactor.
- Too many parameterized rows or `@Nested` levels can hide what is being tested.
- Overusing mocks can leave you testing the mocks, not the real code.
- Mixing JUnit 4 imports (`org.junit.Test`) with JUnit 5 (`org.junit.jupiter.api.Test`) silently skips tests. This is a common beginner mistake.

**How I'd monitor it**
- Check the CI test report for pass, fail and skipped counts. A sudden rise in skipped tests is a warning.
- Track coverage (for example with JaCoCo) as a hint, not a goal. Check that boundaries are covered.
- Track flaky tests (those that fail and then pass on rerun) and fix or quarantine them.
- Watch build time. If it grows, use `@Tag` to split fast and slow suites.

**Follow-ups to expect**
- *Difference between `@BeforeEach` and `@BeforeAll`?* -> `@BeforeEach` runs before every test. `@BeforeAll` runs once before all tests in the class, and the method must be static by default.
- *How is JUnit 5 different from JUnit 4?* -> It is split into Platform, Jupiter and Vintage. It uses extensions instead of runners and rules, and has `@Nested`, `@ParameterizedTest` and `@DisplayName` built in.
- *Why AssertJ if JUnit has assertions?* -> Its fluent style reads better, it has richer checks for collections and strings, and its error messages are clearer.

**60-second answer**
In JUnit 5 I mark tests with `@Test`, give them readable names with `@DisplayName`, and use `@BeforeEach` and `@AfterEach` so every test starts clean. For the same logic with many inputs I use `@ParameterizedTest` with `@CsvSource` or `@MethodSource`, mainly for boundary values like 99, 100 and 101. I check errors with `assertThrows` and several fields at once with `assertAll`. `@Nested` groups tests by situation, and `@Tag` lets the pipeline run fast and slow tests separately. `@ExtendWith` plugs in things like Mockito or Spring support, and I use AssertJ for readable assertions. I keep tests independent and check behaviour, not implementation details.

### Q3 [mid] Mock vs Stub vs Spy vs Fake?
tags: mockito, test-doubles, unit-testing, mocking, fakes, junit5, testing, basics

**Start here: the concepts**
- **Test double:** a stand-in object used in a test in place of a real dependency (a database, payment gateway, email sender). It exists because real dependencies are slow, costly, or unpredictable. Stub, mock, spy and fake are all kinds of test double.
- **Stub:** a double that returns canned answers. "When someone asks for customer 7, return this customer." You then check the *result* of the code under test. It does not care how it was called.
- **Mock:** a double that records how it was called, and the test *verifies* those interactions. "Was `emailSender.send()` called exactly once with this address?" Use it when the behaviour you care about is a side effect with no visible return value.
- **Spy:** a double that records calls too, but in Mockito it wraps a *real* object. Real methods run unless you override them (a "partial mock"). The textbook spy only records calls without wrapping, so this is Mockito's meaning.
- **Fake:** a genuinely working but lightweight implementation, such as an in-memory `Map`-backed repository. It has real behaviour (save, then find returns it), just without a real database.
- **State assertion vs interaction verification:** state assertion checks the outcome ("the order is now PAID"). Interaction verification checks the calls made ("`save` was called once").
- **Implementation detail:** how the code does its work internally. Tests tied to it break on harmless refactors.

**The live scenario**
An order service had about 1,200 unit tests, many built on mocked repositories. A developer refactored to load orders in one batched query instead of three single calls. Behaviour was identical, yet 85 tests failed because they verified the old calls, and a day was spent fixing tests. Worse, a mocked `findByEmail` returned the customer in every test, but the real SQL was case-sensitive. After release, roughly 3% of customers (illustrative) could not see their orders. The mocks proved nothing about the real query. Afterwards the team used an in-memory fake for business-logic tests and added a Testcontainers database test for the repository itself.

**What the interviewer is really checking**
Whether you know the vocabulary and, more importantly, can judge when each double is appropriate. Over-mocking couples tests to implementation and gives false confidence.

**How I answer it**
1. **Define the four in one line each.** Stub gives canned answers, mock verifies calls, spy wraps a real object, fake is a working simple implementation. A shared vocabulary makes the rest of the answer clear.
2. **Say that Mockito blurs the lines.** A Mockito `mock()` can act as a stub (`when(...).thenReturn`) or a mock (`verify`). The role depends on how you use it, not on the class.
   ```java
   when(repo.findById(7)).thenReturn(order);   // stub role
   verify(mailer).send(any());                 // mock role
   ```
3. **Default to state assertions with stubs or fakes.** Checking outcomes survives refactoring, because the test cares *what* happened, not *how*.
4. **Use a fake when the dependency has behaviour.** A repository that stores and retrieves is easier and more honest as an in-memory fake than as ten `when(...)` lines per test.
5. **Use a mock only for outgoing side effects** with no observable result (email sent, event published). Verifying the call is then the only way to check it.
6. **Use a spy sparingly,** for example to test legacy code you cannot restructure yet. Spying on the class under test is a smell, because it suggests the class does too much.
7. **Back doubles with higher-level tests.** A double only proves your code works against *your assumption* of the dependency. Real behaviour (SQL, serialization) needs integration tests such as Testcontainers or contract tests.

**Trade-offs and what can go wrong**
- Over-mocking: tests break on refactors and still miss real bugs.
- Fakes cost effort to write and can drift from the real system, so back them with a shared test that runs against both the fake and the real one.
- Spies can hide the fact that a class is doing too much.
- Strict stubbing (Mockito reports unused stubs) helps keep tests honest, but needs team agreement.

**How I'd monitor it**
- Track the number of tests broken by refactors that changed no behaviour. A high count signals over-mocking.
- Run mutation testing (e.g. PIT) to check whether tests actually fail when logic changes. Line coverage alone does not show this.
- Watch CI flakiness and test duration.
- After releases, search Splunk for new error patterns (e.g. "not found" exceptions) to catch gaps unit tests missed.

**Follow-ups to expect**
- *When is a mock the right choice?* -> When the behaviour is an outgoing side effect with no return value, such as publishing an event or sending an email.
- *Why not mock everything?* -> It couples tests to internals, breaks them on refactors, and does not prove real dependencies behave as assumed.
- *How do you keep a fake honest?* -> Run one shared contract test against both the fake and the real implementation (e.g. via Testcontainers).

**60-second answer**
These are all test doubles, stand-ins for real dependencies. A stub returns canned answers, a mock lets me verify that specific calls happened, a spy wraps a real object and records calls, and a fake is a simple working version, like an in-memory repository. In Mockito, one mock object can play stub or mock depending on how I use it. I prefer state assertions with stubs or fakes, because they check outcomes and survive refactoring. I use mocks only for side effects like sending an email. Over-mocking makes tests brittle and can hide real bugs, such as a SQL query that behaves differently from my assumption. So I back the doubles with a few Testcontainers integration tests against the real database.

### Q4 [mid] Mockito: common patterns and pitfalls?
tags: mockito, junit5, unit-testing, mocking, argumentcaptor, test-quality, basics

**Start here: the concepts**
- **Mock:** a fake object that stands in for a real dependency (a repository, an HTTP client) so you can test one class alone. It exists so unit tests are fast and don't need a database.
- **Stubbing:** telling a mock what to return. `when(repo.find(1)).thenReturn(x)` means "when `find(1)` is called, return `x`".
- **Verification:** asking a mock afterwards whether it was called, e.g. `verify(repo).save(...)`. It checks an interaction, not a result.
- **ArgumentCaptor:** a tool that grabs the actual argument passed to a mock so you can assert on its contents. A plain `verify` only proves a call happened, not what was passed.
- **`doThrow`:** makes a mock throw an exception. For `void` methods you must use `doThrow(...).when(mock).method()`, because `when(...)` needs a return value to wrap.
- **`@InjectMocks`:** Mockito creates the class under test and pushes your `@Mock` objects into it. It tries the constructor first, then setters or fields.
- **Value object:** a simple immutable data holder (`Money`, `Address`) with no external dependencies. It's cheap to create for real.

**The live scenario**
A payment service had 1,200 unit tests and 92% line coverage. A test named `shouldApplyDiscount` mocked the pricing helper and the `Money` class, then only ran `verify(repo).save(any())`. It had no assertion on the amount. A refactor made the discount apply twice. All tests stayed green. For about three hours, roughly 4% of orders (illustrative) were undercharged, and finance had to reconcile them manually. Afterwards the team used real `Money` objects, captured the saved order and asserted its total, and added mutation testing to CI.

**What the interviewer is really checking**
Whether you use Mockito to isolate behaviour and assert outcomes, or just to make coverage numbers green. They also want to see that you know its common traps.

**How I answer it**
1. **Stub inputs with `when(...).thenReturn(...)`.** This controls what the class under test sees, so the test is deterministic.
2. **Assert outcomes first, interactions second.** Check the return value or saved state. Verify calls only when the call is the behaviour, such as "an email was sent".
3. **Use `ArgumentCaptor` to inspect what was passed:**
```java
verify(repo).save(captor.capture());
assertEquals(90, captor.getValue().getTotal());
```
This proves the content is right, not just that a call occurred.
4. **Use `doThrow` for void methods** to test failure paths, such as "what if `notifier.send()` fails?".
5. **Use `@InjectMocks` carefully.** I prefer constructor injection and plain `new Service(mockRepo)`. If injection can't match a dependency, you may get a null field and a confusing `NullPointerException`.
6. **Don't mock value objects.** Build real ones. Mocking them hides bugs and makes tests describe the mock, not the code.
7. **Don't verify too much.** Verifying every internal call ties the test to the implementation, so harmless refactors break it.
8. **Avoid mocking static or final code unless you have no choice.** It is a sign of a design that is hard to test. Since Mockito 5, the inline mock maker is the default, so final classes and `mockStatic` work, but wrapping the static call behind an interface is usually cleaner.
9. **Every test needs an assertion.** A test that only runs code passes even when the result is wrong.

**Trade-offs and what can go wrong**
- Over-mocking gives fast tests that prove little, because real wiring, SQL and JSON mapping are never exercised. Add integration tests (Spring slices, Testcontainers) for those.
- Over-verifying makes refactoring painful and teaches the team to ignore red tests.
- Unnecessary stubs hide dead setup. With `MockitoExtension` (strict stubs), Mockito fails the test with `UnnecessaryStubbingException`. Keep that on.
- Mixing matchers and raw values in one call (`eq(1)` with `"abc"`) throws an error. Use matchers for all arguments or for none.

**How I'd monitor it**
- CI test reports: watch for flaky or skipped tests.
- Mutation testing (for example PIT), which catches tests that pass even when the code is changed.
- A code review checklist: "Is there an assertion? Are the mocks necessary?"
- In production, Splunk searches for order-total mismatches or refund spikes. They show what slipped past the tests.

**Follow-ups to expect**
- *When do you use a spy instead of a mock?* -> A spy wraps a real object so real methods run unless stubbed. I use it rarely, for partial behaviour, and stub with `doReturn(...).when(spy)`.
- *Why use an ArgumentCaptor instead of `eq(obj)`?* -> `eq` needs a correct `equals` and a full expected object. A captor lets me assert only the fields that matter.
- *Mock or real object?* -> Mock slow or external collaborators. Use real objects for simple in-memory ones.

**60-second answer**
Mockito replaces dependencies with fakes so I can test one class in isolation. I stub with `when/thenReturn`, use `doThrow` for void methods, and use an `ArgumentCaptor` to check what was actually passed to a mock. `@InjectMocks` wires mocks in, but I prefer constructor injection because failed injection can leave nulls. My main rule is to assert outcomes first and verify interactions only when the call itself is the behaviour. I don't mock value objects, I don't verify every internal call, and I avoid mocking static or final code unless there's no other way. Above all, a test without an assertion proves nothing. Once, a test that only verified `save()` let a double-discount bug reach production. That is why I assert the captured content and add integration tests for what mocks cannot cover.

### Q5 [mid] Spring Boot test slices?
tags: spring-boot, testing, test-slices, webmvctest, datajpatest, mockito, basics

**Start here: the concepts**
- **Application context:** the container Spring builds at startup. It creates all your beans (controllers, services, repositories) and wires them together. Building it is the slow part of Spring tests.
- **Test slice:** a test annotation that starts only the part of the context one layer needs, such as the web layer or the database layer. It exists because starting everything for every test is slow and tests more than you meant to.
- **`@WebMvcTest`:** loads the controllers, JSON conversion, validation and request mapping. It does not load services or repositories, so you supply fake ones. You call it through `MockMvc`, which simulates HTTP without a real server.
- **`@DataJpaTest`:** loads entities, repositories and JPA only. By default it swaps your database for an embedded one if one is on the classpath, and rolls back each test's changes. For realism, run it against a real database in Testcontainers (throwaway Docker containers) with `@AutoConfigureTestDatabase(replace = NONE)` or `@ServiceConnection`.
- **`@JsonTest`:** checks only that your objects serialise to and from the JSON you expect.
- **`@RestClientTest`:** tests a class that calls another service over HTTP, with the remote server faked.
- **`@SpringBootTest`:** loads the full context. It is the closest to production but the slowest.
- **Mock:** a fake collaborator you control. `@MockitoBean` (Spring Framework 6.2+) puts a Mockito mock into the test's context. It replaces `@MockBean`, which was deprecated in Boot 3.4 and removed in Boot 4.

**The live scenario**
A team had 400 tests, nearly all `@SpringBootTest`. CI took about 22 minutes, so developers stopped running tests locally. A refactor removed `@Valid` from one controller method. No test noticed, because the full-context tests only checked happy paths. In production, requests with a missing field reached the database and returned HTTP 500 instead of 400, and a client retried them thousands of times. Afterwards the team added `@WebMvcTest` tests for every controller's bad-input cases and moved repository tests to `@DataJpaTest`. CI dropped to roughly 8 minutes (illustrative), and the bug class was covered.

**What the interviewer is really checking**
Whether you pick the cheapest test that protects a given risk, and whether you know what each slice loads and what it leaves out.

**How I answer it**
1. **Start from the risk, not the annotation.** Ask what could break: request mapping and validation, queries, JSON shape, or wiring. Each slice protects one of these cheaply.
2. **Controller rules go in `@WebMvcTest`.** It starts only the web layer, so it runs fast and fails with a clear cause. Mock the service so you are not testing business logic here:
```java
@WebMvcTest(OrderController.class)
class OrderControllerTest {
  @Autowired MockMvc mvc;
  @MockitoBean OrderService service;
}
```
3. **Queries go in `@DataJpaTest` against the real database type.** An embedded database can behave differently from PostgreSQL or Oracle (SQL dialect, locking, JSON columns). Testcontainers removes that gap.
4. **Use `@JsonTest` and `@RestClientTest` for narrow contracts.** They catch field renames and date-format changes without starting anything else.
5. **Keep a few `@SpringBootTest` tests.** Use them for end-to-end wiring, security configuration and startup failures, because slices deliberately skip those.
6. **Mock only boundaries.** Assert on behaviour (status, body, saved data), not on which internal methods were called.

**Trade-offs and what can go wrong**
- Each distinct slice or mock configuration creates a new cached context, so many variations erode the speed gain.
- Slices miss wiring problems, such as a bean that no slice loads. Without a few full tests, those appear only at startup.
- Over-mocking makes tests pass while the real integration fails.
- Boot 4 splits test support into per-technology modules, so dependencies and imports change when migrating. Check the migration guide.
- Embedded-database tests can pass while production SQL fails.

**How I'd monitor it**
- CI test duration, per module and per test class, to catch creeping slowness.
- The count of distinct Spring contexts created in a test run (context cache logs).
- The flaky-test rate and failures by test type.
- Coverage together with mutation testing (e.g., PIT), to show whether tests really assert something.
- In production, a Splunk search for HTTP 500s on endpoints that should return 400. It shows what the tests missed.

**Follow-ups to expect**
- *Why not use `@SpringBootTest` everywhere?* -> It is slow and tests too much at once, so failures are hard to locate and developers stop running the suite.
- *`@Mock` vs `@MockitoBean`?* -> `@Mock` is plain Mockito with no Spring. `@MockitoBean` replaces a bean inside the Spring context.
- *Does `@DataJpaTest` use my real database?* -> Not by default. It uses an embedded one, so use Testcontainers for production fidelity.

**60-second answer**
A test slice loads only one layer of a Spring Boot app, so tests are fast and focused. `@WebMvcTest` tests controllers, validation and JSON through MockMvc, with services mocked using `@MockitoBean`, which replaced `@MockBean` after 3.4. `@DataJpaTest` tests repositories and rolls back each test. I run it against a real database in Testcontainers, because embedded databases behave differently. `@JsonTest` and `@RestClientTest` cover JSON shape and outgoing HTTP calls. I keep a few `@SpringBootTest` tests for full wiring and security, since they are slow. I choose the cheapest test that guards each risk, and I watch CI time and the number of contexts created.

### Q6 [mid] What is Testcontainers and why use it over H2?
tags: testcontainers, h2, integration-testing, docker, postgresql, basics

**Start here: the concepts**
- **Integration test:** a test that runs your code together with a real dependency, such as a database or message broker, instead of a fake. It exists because many bugs only appear where your code meets that dependency.
- **H2:** a small database written in Java that runs inside your test JVM (the Java process running the tests). It is fast and needs no setup, but it is not PostgreSQL or Oracle. It only imitates them.
- **SQL dialect:** each database has its own SQL features, data types and rules, such as `jsonb` and `ON CONFLICT` in PostgreSQL. A query valid in one database can fail or behave differently in another.
- **Docker container:** a packaged, isolated process that runs a piece of software (for example PostgreSQL) the same way on any machine with Docker.
- **Testcontainers:** a Java library that starts Docker containers from inside your tests (JUnit 5 etc.) and removes them afterwards. Your test talks to the real PostgreSQL, Kafka, Redis, Oracle XE or Couchbase, not an imitation.
- **Constraint:** a database rule, such as unique, not null or foreign key, that rejects bad data.

**The live scenario**
A team's order service had 1,200 tests, all green in about 4 minutes, running on H2. A new feature used a PostgreSQL `ON CONFLICT` upsert and a `jsonb` column. H2 was in a compatibility mode and accepted a simplified version, so the tests passed. In production, the migration and query failed on a different constraint. Roughly 40 minutes of order writes failed before rollback (illustrative numbers). Afterwards the team moved repository tests to Testcontainers with PostgreSQL. The same bug now fails on a developer's laptop.

**What the interviewer is really checking**
Whether you understand that a test is only as trustworthy as the similarity between the test environment and production. They also want to know whether you can name the cost (speed, Docker) and how you manage it.

**How I answer it**
1. **Define it plainly.** Testcontainers starts real dependencies in Docker for the test run. The reason is that you test against the same engine you ship on.
2. **Explain the problem with H2.** It hides dialect differences, such as SQL syntax, data types, locking and constraint behaviour. Tests can pass that would fail in production. It can also fail tests that would work in production, which wastes time.
3. **Name what it covers.** Databases (PostgreSQL, Oracle XE), Kafka (real broker behaviour such as partitions and offsets), Redis and Couchbase. H2 cannot imitate Kafka or NoSQL stores at all.
4. **Show how little code it takes.** In Spring Boot 3.1+, `@ServiceConnection` wires the container's URL into the app automatically:
```java
@Testcontainers @SpringBootTest
class OrderRepoIT {
  @Container @ServiceConnection
  static PostgreSQLContainer<?> pg = new PostgreSQLContainer<>("postgres:16");
}
```
5. **Pin the image version to production's.** Otherwise you test a different engine again.
6. **Keep the suite fast.** Start one container per test run and share it (the singleton pattern), instead of one per test class. Clean data between tests, for example with transaction rollback or truncation. Testcontainers also has an opt-in "reuse" feature that keeps containers alive between runs for local development.
7. **Keep the right test mix.** Use plain unit tests for logic, and Testcontainers only where the dependency's real behaviour matters (repositories, migrations, messaging).

**Trade-offs and what can go wrong**
- Slower than H2: container startup takes seconds, not milliseconds.
- Needs Docker (or a compatible runtime) on laptops and CI agents. Some locked-down CI setups make this hard.
- Per-test containers make the suite very slow, and shared containers risk leaked data between tests.
- A floating image tag like `latest` can make tests unpredictable.
- Oracle images are large and can have licensing or startup-time concerns.
- A passing test still does not prove production-level performance or data volume.

**How I'd monitor it**
- CI build duration and the slowest test classes, to spot containers starting too often.
- Flaky-test rate in CI, since shared state or startup timeouts show up here.
- Test image tags compared with production versions, checked in code review or by a script.
- Count of production incidents caused by SQL or dialect issues; this should drop towards zero.

**Follow-ups to expect**
- *Can't H2 run in PostgreSQL mode?* -> It approximates the syntax but not the planner, locking, extensions or all types, so gaps remain. It is fine for pure logic, not for trusting database behaviour.
- *How do you keep Testcontainers fast?* -> Share one container per run, pin lightweight images, clean data between tests, and run only the needed tests against it.
- *How is it different from a shared test database?* -> Each run gets a fresh, isolated, disposable instance, so there is no drift or interference between teams.

**60-second answer**
Testcontainers is a Java library that starts real dependencies, like PostgreSQL, Kafka or Redis, in Docker for the length of a test run. I prefer it to H2 because H2 only imitates a database. It hides differences in SQL dialect, types and constraints, so tests can pass and then fail in production. With Testcontainers I test against the same engine and version I deploy, and I pin the image tag to match production. The cost is slower startup and a Docker requirement, so I share one container across the suite and clean data between tests. I keep unit tests plain and use Testcontainers for repositories, migrations and messaging, where real behaviour matters.

### Q7 [mid] How do you test asynchronous code?
tags: async testing, awaitility, completablefuture, kafka, testcontainers, basics

**Start here: the concepts**
- **Asynchronous code:** work that continues after the method returns, on another thread or in another process. A test that calls it and asserts straight away checks too early.
- **Flaky test:** a test that sometimes passes and sometimes fails on the same code. Timing guesses are the most common cause.
- **`Thread.sleep`:** pauses for a fixed time. If the work finishes in 50 ms you still wait the full time. If it takes longer than you guessed, the test fails randomly.
- **Awaitility:** a Java library that polls a condition until it is true or a deadline passes. `untilAsserted` retries your assertions until they stop failing.
- **Executor:** the object that decides which thread runs a task. If the test supplies it, the test controls when tasks run.
- **Clock:** `java.time.Clock` is the source of "now". Inject a fake one and a test can jump forward an hour instantly.
- **Sink:** wherever the async work finally leaves its result, such as a database row, an output topic or a stub HTTP endpoint.
- **`CompletableFuture`:** a Java object representing a result that will arrive later.

**The live scenario**
An order service publishes `OrderPlaced` to Kafka. A consumer then writes a row to a `shipments` table, usually within 200 ms. The test used `Thread.sleep(500)`. On the shared CI server, which was busy at peak, it took 700 ms, so the build failed about one run in ten. The team re-ran builds until they stopped trusting red ones. Someone then merged a real bug, a missing null check, because "it's probably the flaky test again". After the fix they replaced the sleeps with Awaitility and the build became trustworthy.

**What the interviewer is really checking**
Whether you can make timing-dependent tests fast and deterministic, and whether you know the pitfalls: sleeps, missing timeouts and tests that hang forever.

**How I answer it**
1. **Never use `Thread.sleep`.** It is either too slow or too short. Poll for the outcome instead, so the test finishes as soon as the work does:
   ```java
   await().atMost(5, SECONDS)
          .untilAsserted(() -> assertThat(repo.findByOrderId(id)).isPresent());
   ```
   The 5 seconds is a safety limit, not a delay. A failure then means "it did not happen in time", not "I guessed wrong".
2. **Make time and threads controllable where you can.** Inject a `Clock` and an `Executor`. In unit tests, use a fake clock or a same-thread executor, so retries and timeouts run instantly and in a fixed order. Don't wait for real time.
3. **For Kafka, test through the real boundary and watch the sink.** Produce a message, then await the observable result, such as the DB row or the output topic. Run against a real broker with Testcontainers (a throwaway Docker container started by the test) or Spring's embedded Kafka. Avoid asserting on internal method calls, because they break whenever you refactor.
4. **For `CompletableFuture`, always bound the wait.** Plain `join()` has no timeout and can hang the build forever. The stored answer's "join with timeouts" needs a correction here. Use `future.get(2, SECONDS)`, or add `orTimeout(...)` (Java 9+) to the future first. Then a stuck future fails the test quickly.
5. **Keep unit tests synchronous where possible.** Test the business logic directly, and use a few async integration tests only for the wiring.

**Trade-offs and what can go wrong**
- Too-short `atMost` values still flake on slow CI. Allow generous limits, because a passing test returns early anyway.
- Awaitility polls from another thread, so the state it reads must be thread-safe or visible (for example, use `AtomicReference` or read from the DB).
- Fake executors make tests deterministic but can hide real concurrency bugs. Keep a few real-thread integration tests.
- Kafka delivers at least once, so a test may see duplicates. Assert on the end state, not on message counts.
- Reusing the same topic or table across tests lets one test's data leak into another. Use unique IDs.

**How I'd monitor it**
- Track CI flaky-test rate and re-run counts. Quarantine and fix tests that fail intermittently.
- Check test duration trends. A test that creeps toward its `atMost` limit signals a real slowdown.
- Log the Awaitility timeout message and, in production, search Splunk for consumer lag and processing time to confirm the timings tests assume.

**Follow-ups to expect**
- *Why not just a bigger sleep?* -> It slows every run and still fails on a slower day. Polling stops as soon as the condition holds.
- *How do you test a retry with a 30-second backoff?* -> Inject a `Clock` or scheduler and advance it, so the test doesn't wait 30 real seconds.
- *How do you test that something does not happen?* -> Use Awaitility's `during(...)` or `failFast`, or wait for a known later event, because absence can't be polled for.

**60-second answer**
Async code returns before the work is done, so asserting immediately fails, and `Thread.sleep` only guesses at timing, which causes slow or flaky tests. I poll with Awaitility, for example `await().atMost(5, SECONDS).untilAsserted(...)`, so the test ends as soon as the result appears. In unit tests I inject a clock and an executor so time and threads are under my control. For Kafka I produce a message to a Testcontainers broker and wait for the visible result in the sink, such as a DB row. For `CompletableFuture` I never use a bare `join()`, since it has no timeout. I use `get` with a timeout or `orTimeout` so a stuck future fails fast. Flaky tests make people ignore red builds, and that is how real bugs get through.

### Q8 [mid] What is TDD and when is it worth it?
tags: tdd, unit-testing, junit5, refactoring, regression-testing, mockito, basics

**Start here: the concepts**
- **Test-Driven Development (TDD):** a way of working where you write the test before the code it checks. The test acts as a small, runnable specification of what you want. It exists so you find mistakes in minutes, not weeks later in production.
- **Red-Green-Refactor:** the three-step loop of TDD.
  - **Red:** write a test for behaviour that does not exist yet, and watch it fail. A test that has never failed might not be testing anything.
  - **Green:** write the simplest code that makes the test pass, even if it is ugly.
  - **Refactor:** clean up the code and the test while all tests stay green. The tests are your safety net.
- **Unit test:** a fast, small test of one piece of logic (a method or class), usually with no database or network. JUnit 5 is the standard Java framework for these.
- **Business logic:** code that encodes the rules of the domain, such as "orders over 100 get 10% off, but not on already discounted items".
- **Regression:** a bug that comes back, or something that used to work and breaks after a change. A test that stays in the suite prevents it.
- **Glue code:** thin code that only passes data between layers or libraries and has almost no rules of its own.
- **Spike:** a short, throwaway experiment to learn whether something is possible. You do not yet know what the design should be.

**The live scenario**
A pricing service applies discount rules for about 50,000 orders a day. A developer changes the "loyalty discount" rule and, by accident, stacks it with a promo code. For six hours some customers get 30% off instead of 15%. Finance finds about 400 affected orders the next morning. The rule had no tests, and nobody dared to clean up the code. Afterwards the team wrote a failing test that reproduced the bug, fixed it, and added one test for each discount rule. They now write new rules test-first.

**What the interviewer is really checking**
Whether you see TDD as a design and safety practice with clear places where it pays off, not a religion or a coverage number. They also want to know whether you can say when you would not use it.

**How I answer it**
1. **Define the loop.** Red-Green-Refactor: write a failing test, make it pass with minimal code, then refactor. Minimal matters because it stops you building things nobody asked for.
2. **Say what it gives you.** Tests written first force you to think about inputs, outputs and edge cases before coding. The code ends up easier to test because it has fewer hidden dependencies. You also get a regression suite as a by-product.
3. **Use it for business logic with clear rules.** The expected results are easy to state (price, discount, tax, eligibility), so tests are cheap and valuable. Example in JUnit 5: `@Test void loyaltyDiscountDoesNotStackWithPromo()`.
4. **Use it for every bug fix.** First write a failing test that reproduces the bug. This proves you understood it, and once the test is green the bug cannot return unnoticed.
5. **Skip or relax it for spikes and thin glue code.** In a spike the design will change or be thrown away, so tests are wasted effort. Glue code has little logic, so a test would mostly repeat the code. Cover it with a few integration tests instead.
6. **Test behaviour, not implementation.** Assert on results, not on which private methods were called. Use Mockito only at real boundaries such as an external service. Otherwise refactoring breaks tests that should still pass.

**Trade-offs and what can go wrong**
- It is slower at the start, and it needs practice to feel natural.
- Over-mocking produces brittle tests that fail on every refactor and prove little.
- Bad tests written first lock in a bad design.
- Chasing 100% coverage encourages tests with no real assertions.
- TDD does not replace integration or contract tests. Unit tests do not show that the database, Kafka or another service works with your code.

**How I'd monitor it**
- Check that the CI build runs the unit tests on every pull request, and track its pass rate.
- Look at coverage trends in JaCoCo, mainly on changed code, not as a target number.
- Run mutation testing (for example PIT) on critical rules to see whether tests really catch changes.
- Track flaky tests and the time the suite takes.
- Count production defects in TDD-covered modules versus untested ones. Search Splunk for errors from the rule code after each release.

**Follow-ups to expect**
- *Does TDD mean 100% coverage?* -> No. Coverage shows what code ran, not whether the assertions are meaningful. Aim for the important rules and edge cases.
- *How is TDD different from just writing tests afterwards?* -> Tests-after tend to confirm what the code already does. Tests-first shape the design and prove they can fail.
- *How do you handle dependencies in TDD?* -> Keep the core logic free of I/O so it needs no mocks. Mock or fake only the boundaries, and use Testcontainers or WireMock in integration tests.

**60-second answer**
TDD is a loop called Red-Green-Refactor. I write a failing test, write the simplest code that makes it pass, then clean up while the tests stay green. It is worth it for business logic with clear rules, such as pricing or eligibility, because tests are cheap and mistakes are expensive. It is also worth it for bug fixes. I first write a test that reproduces the bug, so I know I understand it and it cannot quietly come back. I would not use it for spikes, where the design is still unknown, or for thin glue code with no real logic. I keep tests focused on behaviour, not implementation details, so refactoring does not break them. And I still add integration and contract tests, because unit tests alone do not prove the system works together.

### Q9 [mid] Consumer-driven contract testing?
tags: contract-testing, consumer-driven-contracts, pact, spring-cloud-contract, microservices, basics

**Start here: the concepts**
- **Provider and consumer:** The provider is the service that offers an API (for example, Customer service). The consumer is the service that calls it (for example, Order service). One service is often both.
- **Contract:** A written record of one interaction, such as "when I send GET /customers/42, I expect status 200 and a body with `id` and `email`." It lists only what the consumer actually uses, not the whole API.
- **Consumer-driven:** The consumer writes down what it needs, and the provider must prove it still delivers that. This is useful because providers often don't know which fields their callers rely on.
- **Pact and Spring Cloud Contract:** Two real tools. In Pact, the consumer's test generates the contract file (a "pact"). The provider replays it against its real code. Spring Cloud Contract usually starts from contracts written on the provider side, but it can generate stubs for consumers too. Check how your team uses it before calling it consumer-driven.
- **Broker:** A shared server (Pact Broker or PactFlow) that stores contracts and verification results, so both teams see them.
- **Why it exists:** Unit tests with mocks cannot notice when the real provider changes. A full end-to-end environment can, but it is slow and flaky. Contract tests sit in between: fast, and they run without a full environment.

**The live scenario**
Order service calls Customer service about 2,000 times a minute. A Customer team developer renames `phoneNumber` to `phone` and all their tests pass. After deploy, Order service fails to read the field and 12% of checkouts fail for 40 minutes before rollback. Order's unit tests passed because their mock still returned the old shape. Nobody had a test that connected the two. Afterwards the teams added contract tests, and the rename would have failed Customer's build before release.

**What the interviewer is really checking**
Whether you understand what this test level protects against (the gap between services), how the workflow runs in CI, and that it complements other tests rather than replacing them.

**How I answer it**
1. **Consumer writes a test against a mock provider.** The test states the request it sends and the response it needs. The reason is that the contract is then generated from real consumer code, not a hand-written guess.
2. **Publish the contract to the broker from CI.** This gives the provider team a single source of truth and removes manual file sharing.
3. **Provider verifies in its own CI.** The tool replays each contract against the real provider (usually a Spring Boot test slice with data stubbed). A mismatch fails the provider build, so the breaking change is caught before deploy.
4. **Gate deployments, not just builds.** Before releasing either side, ask the broker whether this version is compatible with what is in production:
```
pact-broker can-i-deploy --pacticipant order-service --version $GIT_SHA --to-environment production
```
5. **Keep contracts small.** Assert only the fields and status codes the consumer uses, so the provider stays free to change everything else. This avoids testing implementation details.

**Trade-offs and what can go wrong**
- Contracts check shape and basic behaviour, not business logic or performance. You still need unit tests and a few end-to-end checks.
- A consumer that over-specifies (exact values, every field) makes provider changes painful.
- Stale or unverified contracts give false confidence. Someone has to own the broker process.
- Without a gate such as `can-i-deploy`, a contract is only documentation.
- It only covers the consumers that have published contracts. An unknown caller is not protected.

**How I'd monitor it**
- Broker dashboard: verification status per consumer/provider version, and contracts that are failing or unverified.
- CI: failure rate of provider verification builds and `can-i-deploy` rejections, which show that the gate works.
- Production: a Splunk search for deserialization errors and 4xx/5xx on calls between the two services after each deploy. A rise means a gap in the contracts.

**Follow-ups to expect**
- *How is this different from an integration test?* -> An integration test runs both real services together and is slow. A contract test checks each side separately against a shared, recorded agreement.
- *Can the provider add a new field safely?* -> Yes, if consumers ignore unknown fields. Removing or renaming a field a consumer uses fails verification.
- *Does it work for Kafka messages?* -> Yes. Pact has message contracts and Spring Cloud Contract supports messaging, so the event shape is checked the same way.

**60-second answer**
Consumer-driven contract testing stops services breaking each other without needing a full environment. The consumer's tests record exactly what it expects from the provider, such as fields and status codes, using Pact or Spring Cloud Contract. That contract goes to a broker. The provider's CI replays it against the real code and fails the build if a change would break a consumer. Before deploying either side, I use a check like `can-i-deploy` so only compatible versions reach production. It does not replace unit tests or a few end-to-end checks, and consumers should keep contracts minimal. I once saw a renamed field cause 12% checkout failures because both sides' tests passed alone, and a contract test would have caught it.

### Q10 [mid] What code coverage target do you set?
tags: code coverage, jacoco, mutation testing, pitest, sonarqube, quality gates, basics

**Start here: the concepts**
- **Code coverage**: the percentage of lines (or branches) of your code that run while the tests run. It exists to show which code no test ever touches. It does not show whether the code is correct.
- **Meaningful assertion**: a check in a test that fails when behaviour is wrong, such as `assertEquals(90.00, price)`. A test that calls a method and checks nothing still raises coverage but protects nothing.
- **Branch coverage**: counts whether both the `if` and the `else` paths ran, not just the line. It is stricter than line coverage.
- **Critical business rule**: logic where a bug costs money or breaks trust, such as pricing, payments, eligibility and tax.
- **Mutation testing (PIT)**: the tool makes small deliberate bugs in your code (a `>` becomes `>=`, a `+` becomes `-`) and re-runs the tests. If the tests still pass, the bug "survived", which means your tests are weak. It exists because coverage cannot detect weak tests.
- **Quality gate**: an automatic pass/fail rule in CI (the build pipeline). If the rule is not met, the change cannot merge.
- **SonarQube / JaCoCo**: JaCoCo measures coverage in Java. SonarQube reads that report and enforces the gate.
- **New code**: only the lines changed in the current branch or period, as opposed to the whole legacy codebase.

**The live scenario**
A pricing service showed 85% coverage and a green dashboard. One release changed a discount check from `>= 100` to `> 100`. Orders of exactly 100 lost their discount, and about 2,000 orders a day were overcharged for three days before support noticed. The tests had run that line but only asserted that "a price is returned". Afterwards the team added boundary tests, ran PIT on the pricing package, and found 12 surviving mutants. They also switched the Sonar gate to measure new code.

**What the interviewer is really checking**
Whether you treat coverage as a tool to find gaps rather than a number to hit, and whether you know how to test the quality of the tests themselves.

**How I answer it**
1. **I say coverage is a signal, not a goal.** Once a number becomes a target, people write assertion-free tests to reach it. The number is still useful because low coverage reliably shows untested code.
2. **I set about 70-80% on new code, with meaningful assertions.** Getters, DTOs and config are not worth testing for their own sake, so chasing 100% everywhere gives low return and brittle tests tied to implementation details.
3. **I aim for near 100% on critical business rules, including branch coverage.** A bug here is expensive, so the extra effort pays off. Even 100% only proves the code ran, so I add boundary cases (like exactly 100) as well.
4. **I run mutation testing (PIT) on those critical packages.** It checks that tests fail when the code is changed. I run it on the core domain, not everywhere, because it is slow.
5. **I put the gate on new code, not only the total.** A legacy total of 45% would block every team, and a high total hides untested new code. Gating new code stops things getting worse without forcing a big rewrite.

```
mvn org.pitest:pitest-maven:mutationCoverage
```

**Trade-offs and what can go wrong**
- Chasing the number leads to assertion-free tests and mocking everything, so tests break on every refactor and catch nothing.
- PIT is slow on big codebases. Run it on selected packages or nightly, not on every commit.
- Some mutants are "equivalent" (the change does not alter behaviour), so a 100% mutation score is unrealistic.
- Coverage ignores missing tests for scenarios you never thought of. Integration and contract tests cover different risks.
- A strict gate can block urgent hotfixes, so agree on a documented override process.

**How I'd monitor it**
- Track JaCoCo coverage on new code per pull request, plus the Sonar trend over time.
- Track the PIT mutation score for core packages, and the number of surviving mutants.
- Count production defects in areas that had high coverage. If they recur, the tests are weak.
- Review the gate failures: frequent overrides mean the rule is wrong or ignored.

**Follow-ups to expect**
- *Line vs branch coverage?* -> Line says a line ran. Branch says both outcomes of each decision ran. Branch is stricter and better for business rules.
- *Is 100% coverage enough?* -> No. It proves code executed, not that results were checked. Mutation testing and good assertions close that gap.
- *How do you handle legacy code with low coverage?* -> Gate only new and changed code, and add tests when you touch an area, so coverage rises gradually.

**60-second answer**
"Coverage is a signal, not a goal. It tells me which code no test runs, but not whether the tests actually check anything. I aim for roughly 70-80% on new code with real assertions, and close to 100% on critical business rules like pricing or payments. To check the tests are good, I use mutation testing with PIT, which changes the code slightly and confirms the tests fail. In SonarQube I put the quality gate on new code, not just the total, so legacy code doesn't block teams and new code can't slip through untested. I once saw 85% coverage miss a boundary bug that overcharged customers, so I trust meaningful assertions over the percentage."

### Q11 [mid] Describe a good CI/CD pipeline for a Java service.
tags: ci-cd, testing, testcontainers, quality-gates, canary-deployment, devsecops, basics

**Start here: the concepts**
- **CI/CD pipeline**: an automated chain of steps that takes a code commit to production. It exists so every change gets the same checks and nobody deploys by hand from a laptop.
- **Pipeline-as-code**: the pipeline is defined in a file in the repo (Jenkinsfile, GitHub Actions YAML). It is reviewed, versioned and reproducible like any other code.
- **Unit test**: tests one class in memory, with collaborators mocked (JUnit 5, Mockito). It is fast and cheap, and it catches logic bugs.
- **Static analysis**: tools that read the code without running it. SonarQube and SpotBugs look for bugs, code smells and vulnerable patterns. A **quality gate** is a pass/fail rule, such as "no new critical issues", that stops the pipeline.
- **Dependency/license scan**: OWASP Dependency-Check or Snyk compare your libraries with known-vulnerability lists and flag forbidden licenses.
- **Integration test**: runs your code against real infrastructure. **Testcontainers** starts throwaway Docker containers (Postgres, Kafka) for the test, so the test does not rely on a fake.
- **Container image**: your app plus its runtime, packaged once. An **SBOM** (software bill of materials) is the list of everything inside it. An **image scan** checks that list for vulnerabilities. The **registry** stores images.
- **Contract test**: checks that a provider and its consumers agree on the API shape (Pact, Spring Cloud Contract), without deploying both. A **smoke test** is a few quick calls against a deployed environment to prove it is alive.
- **Canary**: send a small share of real traffic to the new version first. **Automated rollback** reverts if health metrics worsen.

**The live scenario**
An orders service handles about 800 requests/second. A release renamed a JSON field. Unit tests passed, because they mocked the client. The mobile consumer broke and checkout errors rose to 12% within minutes. The team rolled back by hand 25 minutes later. Afterwards they added contract tests, a canary stage and automatic rollback. The next bad release hit 5% of traffic for 2 minutes and reverted itself.

**What the interviewer is really checking**
Whether you know what each stage protects against and what it costs. They also want to see that you order stages cheap-to-expensive and that you treat safe release as part of the pipeline, not an afterthought.

**How I answer it**
1. **Commit triggers build and unit tests.** Fast checks run first, so a broken commit fails in minutes and costs little.
2. **Static analysis plus dependency/license scan** (Sonar, SpotBugs, OWASP Dependency-Check/Snyk) with a quality gate. This finds bugs and known-vulnerable libraries before anything is packaged.
3. **Integration tests with Testcontainers.** They prove the SQL, Kafka config and serialization work against real systems. They are slower, so they run after the cheap steps.
4. **Contract tests at build time.** I would move them here rather than after deploy. They need no environment and catch the API break from the scenario early.
5. **Build the image once**, generate the SBOM, scan the image, and push to the registry. The same immutable image is promoted through every environment, so what was tested is what ships.
6. **Deploy to dev automatically, then run smoke tests.** This proves the deployment and configuration work, which unit tests cannot show.
7. **Promote to staging, then a manual approval** if the business wants a gate. Teams with strong automation may skip it (continuous deployment).
8. **Production canary with automated rollback.** Release to a small share of traffic, compare error rate and latency with the old version, and revert automatically if they worsen.
9. **Everything is pipeline-as-code**, so the process is reviewable and repeatable.

**Trade-offs and what can go wrong**
- A slow pipeline (over about 15 minutes) makes developers bypass it. Parallelise stages and keep the unit-test base large.
- Flaky integration tests teach people to ignore red builds. Fix or quarantine them.
- Overly strict scanners block releases over false positives. Use triaged suppressions with expiry dates.
- Rebuilding per environment breaks "tested = shipped".
- Rollback is hard when a database migration is not backward compatible. Use expand/contract migrations.
- Canary decisions are only as good as the metrics behind them.

**How I'd monitor it**
Track pipeline duration, failure rate by stage, flaky-test rate, and deployment frequency. Also track change-failure rate and time to restore (the DORA metrics). In production, watch canary error rate, p95 latency and Kafka consumer lag, and alert on them. In Splunk, search for errors filtered by version tag to compare the canary with the baseline.

**Follow-ups to expect**
- *Where do contract tests belong?* -> At build time, before deploy. They need no running environment, and they catch API breaks early.
- *Why build the image only once?* -> Rebuilding per environment can produce a different artifact, so what you tested might not be what ships.
- *How do you roll back safely with a database change?* -> Make migrations backward compatible (add first, remove later), so the old version still works with the new schema.

**60-second answer**
A good pipeline runs cheap checks first and expensive ones later. On commit I build and run unit tests, then Sonar and SpotBugs with a quality gate, plus a dependency and license scan. Next come integration tests with Testcontainers and contract tests, so API breaks fail before anything deploys. I build the container image once, generate an SBOM, scan it and push it to the registry. That same image goes to dev, where smoke tests run, then to staging, and after an approval to production as a canary. The canary compares error rate and latency with the old version and rolls back automatically if they worsen. All of it is pipeline-as-code, and I track pipeline time, flaky tests and change-failure rate.

### Q12 [mid] Branching strategy: GitFlow vs trunk-based?
tags: gitflow, trunk-based-development, branching, continuous-integration, feature-flags, ci-quality-gates, basics

**Start here: the concepts**
- **Branch:** a separate line of commits in Git. Developers use branches so unfinished work does not break the shared code.
- **Merge:** combining one branch's changes into another. The longer two branches drift apart, the more they conflict, and the harder and riskier the merge.
- **GitFlow:** a model with long-lived branches. `main` holds released code, `develop` collects the next release, `feature/*` branches come off `develop`, `release/*` branches stabilise a version, and `hotfix/*` branches patch production. It exists for teams that ship versioned releases on a schedule.
- **Trunk-based development:** everyone merges small changes into one main branch (the "trunk") at least daily. Any other branches live hours or a day or two, not weeks. It exists to keep integration pain small.
- **Continuous integration (CI):** every merge automatically builds the code and runs tests, so breakage is found in minutes.
- **Feature flag:** a configuration switch that turns a feature on or off at runtime. Unfinished code can be merged but stay hidden.
- **CI quality gate:** a rule the pipeline enforces, for example "tests pass and coverage on new code is at least X%, or the merge is blocked".

**The live scenario**
A 12-developer team ships a payments service using GitFlow. A release branch stays open for three weeks while QA tests. Meanwhile 40 feature branches pile up on `develop`. On release day, merging produces conflicts in 25 files and takes a day. Then a production bug needs a hotfix. The fix goes to `main` but is forgotten on `develop`, and there is no regression test. Two weeks later the next release brings the same bug back, and about 3% of payments fail for an hour. The team then moves to trunk-based development: PRs under 300 lines, merged daily, unfinished work behind flags, and every bug fix must include a test that fails without the fix.

**What the interviewer is really checking**
Whether you understand that a branching strategy is about integration risk and release cadence, not preference. They also want to see that you link it to testing: trunk-based development only works if automated tests are trusted.

**How I answer it**
1. **Define both models briefly.** GitFlow uses long-lived `develop` and `release` branches. Trunk-based uses short-lived branches merged continuously. This shows you know what is being compared.
2. **Start from release cadence.** If the product ships versioned releases on a schedule and must maintain several versions at once (for example installed or mobile software), GitFlow's structure fits. If you deploy a web service or API many times a week, long branches only delay feedback.
3. **Explain the cost of long-lived branches.** Merge conflicts grow with branch age, and bugs from interactions between features appear late, at merge time rather than while the code is fresh.
4. **Explain what trunk-based needs.** It needs small PRs, fast CI, and feature flags so incomplete work can be merged safely. Without reliable tests, merging daily to trunk is dangerous. This is where unit tests, integration tests (Testcontainers) and contract tests act as the safety net.
5. **Add CI quality gates.** Block merges on failing tests, and require a regression test with every bug fix. This closes the gap in the scenario's hotfix story.
6. **Conclude.** I choose per cadence and test maturity, and for most modern services I prefer trunk-based. Whichever model you use, avoid branches that live for weeks.

**Trade-offs and what can go wrong**
- Trunk-based without strong tests means a broken trunk, so it needs fast, trusted CI and a rule to fix or revert a red build immediately.
- Feature flags add complexity: stale flags become dead code, and both flag states need testing. Remove flags once the feature is fully released.
- GitFlow gives control and clear release points, but late merges, forgotten hotfix merge-backs, and slow feedback are common failures.
- Calling it "trunk-based" while keeping week-old branches gives you the worst of both.
- Trunk-based does not mean no code review. Small PRs make reviews faster and better.

**How I'd monitor it**
- Branch and PR age (alert on branches older than a few days) and PR size.
- Merge-conflict frequency and time spent on release merges.
- CI duration (target: minutes) and the percentage of failed builds on trunk.
- Delivery metrics: deployment frequency, lead time from commit to production, change failure rate, and time to restore service.
- The number of active feature flags, and the age of each one.
- Escaped defects: production bugs with no matching test.

**Follow-ups to expect**
- *How do you release unfinished work on trunk?* -> Merge it behind a feature flag that is off by default, then turn it on gradually once it is ready.
- *What about hotfixes in trunk-based development?* -> Fix on trunk and deploy, or cherry-pick to a short-lived release branch if you must patch an old version. Add a regression test.
- *Can you do trunk-based with a weak test suite?* -> Not safely. First improve test coverage and CI speed, then shorten branch lifetimes step by step.

**60-second answer**
GitFlow uses long-lived `develop` and `release` branches, and it suits scheduled, versioned releases. The cost is heavy merging and late feedback. Trunk-based development means small PRs merged into one main branch at least daily, with unfinished work hidden behind feature flags. It suits fast, continuous delivery, but only with strong automated tests and quick CI, because every merge must be safe. I decide based on release cadence. In one team, a three-week release branch and a hotfix with no regression test caused the same bug to return. I would move that team to trunk-based with quality gates that require tests on every fix. Either way, avoid long-running branches.

### Q13 [mid] How do you handle dependency and vulnerability management?
tags: dependency-management, vulnerability-scanning, sbom, renovate, dependabot, ci-quality-gates, basics

**Start here: the concepts**
- **Dependency**: a library your code uses. A **transitive dependency** is one pulled in by another library. Most of your code's third-party content is transitive, and you never chose it directly.
- **CVE**: a public ID for a known security flaw in a specific version of a library. Scanners compare your dependency versions against lists of CVEs.
- **Severity (critical/high/medium/low)**: a rating of how dangerous the flaw is. It is the basis for deciding how fast to fix.
- **Renovate / Dependabot**: bots that watch your build file and open a pull request when a newer version exists. Small, frequent upgrades are easier than one huge upgrade every two years.
- **BOM (Bill of Materials)**: a file that declares a tested, matching set of versions. Spring Boot's dependency management is one. Importing it stops you mixing incompatible library versions.
- **Scanner in CI**: a build step (OWASP Dependency-Check, Snyk, Trivy or Grype) that checks dependencies against CVE lists. A **policy** says what fails the build.
- **SBOM (Software Bill of Materials)**: a machine-readable inventory of everything inside a build. **CycloneDX** is a common format. It lets you answer "which services use library X?" quickly.
- **End-of-life (EOL)**: the point when a version stops getting security fixes. Running EOL software means new flaws never get patched.
- **Patch SLA**: a promised deadline to fix, based on severity.

**The live scenario**
On a Friday, a critical remote-code-execution CVE appears in a logging library. We run about 40 services. Without an inventory, three people grep repositories for two days, because the library is mostly transitive. After we add CycloneDX SBOMs to every build, the same question takes a ten-minute search. Separately, a bot upgrade of a JSON library was merged with no contract test. It changed date formatting and broke a downstream consumer for an hour. Now upgrades are automated and tested.

**What the interviewer is really checking**
Whether you treat dependencies as a continuous, automated process with ownership and deadlines, not an occasional clean-up. They also want to hear that tests are what make frequent upgrades safe.

**How I answer it**
1. **Automate updates with Renovate or Dependabot.** Group minor and patch updates and run the full test suite on each PR. Small steps keep upgrades cheap, and tests catch behaviour changes.
2. **Align versions with a BOM** (for example Spring Boot's). One tested set of versions avoids conflicts and "works on my machine" surprises.
3. **Scan in CI with a policy.** Fail the build on critical CVEs, and on high ones where a fix exists. Keep an exceptions file where each suppression has an owner and an expiry date. Otherwise the gate gets ignored or disabled.
4. **Generate an SBOM (CycloneDX) per build and store it.** When a new CVE is announced, you can find affected services quickly.
5. **Remove unused dependencies.** Code you don't ship can't be exploited, and the build gets smaller and faster.
6. **Track end-of-life.** Spring Boot 2.x no longer gets open-source fixes, so move to a supported 3.x line. Spring Boot 3 needs Java 17 or later. Java 8 is very old, and free updates now depend on your vendor's support policy.
7. **Set a patch SLA by severity.** For example, critical in days, high in weeks and the rest in the normal cycle. A deadline turns "we should patch" into a commitment.

```xml
<!-- import the BOM, then declare libraries without versions -->
```

**Trade-offs and what can go wrong**
- **Alert fatigue**: many findings are not reachable in your code. If everything blocks the build, people suppress everything. Prioritise by severity, exploitability and whether a fix exists.
- **Auto-merge without tests**: weak coverage turns bots into a risk. Rely on unit, integration and contract tests, not on the version number.
- **Transitive pinning**: overriding a version by hand can break the BOM's guarantees. Document it and remove it when the BOM catches up.
- **Scanners miss unknown flaws**, so they are not a guarantee.
- **Upgrade debt**: skipping versions for years makes the eventual upgrade a risky project.

**How I'd monitor it**
- Count open vulnerabilities by severity and by service.
- Track time-to-patch against the SLA.
- Track the age of the oldest dependency and the number of services on EOL runtimes.
- Track open bot PRs and the CI failure rate on the scan gate.
- Alert when the scanner database finds a new critical CVE in a stored SBOM.
- Review scan failures and exception expiries on a dashboard (for example in Splunk).

**Follow-ups to expect**
- *Why not upgrade everything immediately?* -> Upgrades can change behaviour. Automate them, but let tests and a staged rollout decide what ships.
- *How do you handle a CVE with no fix yet?* -> Check whether the vulnerable code path is reachable, then add a mitigation such as config changes or a WAF rule. Record a time-limited exception and track the upstream fix.
- *Why is an SBOM useful if you already scan?* -> Scanning finds flaws in what you build today. An SBOM tells you which deployed services contain a library when a new CVE is announced tomorrow.

**60-second answer**
I treat dependencies as a continuous process. Renovate or Dependabot opens small upgrade PRs, and my tests run on each one. I use a BOM such as Spring Boot's so versions stay compatible. CI scans dependencies and fails on critical CVEs, and on high ones that have a fix, with time-limited exceptions. Every build produces a CycloneDX SBOM, so when a new CVE appears I can see which services are affected. I remove unused dependencies and track end-of-life, such as old Spring Boot 2.x and Java 8, and I follow a patch SLA by severity. I watch time-to-patch and open vulnerabilities per service to prove it works.

### Q14 [senior] Zero-downtime release with database migration - how does the pipeline support it?
tags: zero-downtime, database-migration, flyway, liquibase, expand-contract, canary, basics

**Start here: the concepts**
- **Zero-downtime release:** users keep getting correct responses while new code goes live. No maintenance window and no error spike.
- **Rolling deployment:** pods are replaced a few at a time. For several minutes, old and new versions of the app run together against the same database. This overlap is the root of the whole problem.
- **Canary release:** the new version first gets a small slice of traffic (say 5%). If its metrics look healthy, the slice grows. This limits the damage from a bad release.
- **Readiness probe:** a check the platform runs on a pod. The pod receives traffic only after it passes, so a half-started pod never serves users.
- **Schema migration (Flyway/Liquibase):** versioned scripts that change the database structure. The tool records which scripts have run, so each runs exactly once per environment.
- **Backward-compatible migration:** the schema works for both the old and the new app version. Adding a nullable column is compatible. Renaming or dropping one is not.
- **Expand/contract:** change the schema in two separate releases. *Expand* adds the new structure. *Contract* removes the old structure once nothing uses it.
- **Smoke test:** a few fast checks against the live deployment, such as health, one read and one write. They confirm the release basically works.

**The live scenario**
An orders service handles about 2,000 requests/s on 12 pods. A release renamed `customer.phone` to `mobile` in one migration, and the pipeline ran it before the rolling update. For the roughly 6 minutes the update took, old pods still queried `phone` and failed. About 40% of requests returned 500 errors (illustrative numbers). Rolling back the app did not help, because the column was already renamed. Afterwards the team adopted expand/contract and added a migration test.

**What the interviewer is really checking**
Whether you know that old and new code overlap during a release, so the database must be compatible with both. They also want to see that you can turn that rule into pipeline stages and safe rollback.

**How I answer it**
1. **Treat every schema change as two releases (expand, then contract).** The database can't be rolled back as easily as code, and two versions run at once. So release N only adds things, for example `ALTER TABLE customer ADD COLUMN mobile VARCHAR(20) NULL;`.
2. **Run the migration as its own pipeline step before the app rollout.** The new code needs the new column to exist. Running it once as a job, rather than inside every starting pod, avoids many pods racing. Flyway and Liquibase do lock, but a single job is simpler to reason about and to time.
3. **Keep it backward compatible.** Old pods ignore the new column and keep working. New code writes both columns and reads the new one with a fallback. A later backfill, in small batches, copies old data across.
4. **Roll out gradually with readiness probes.** Pods get traffic only when ready. A canary or rolling update exposes only a small share of users to a faulty version.
5. **Gate promotion on smoke tests and live metrics.** If the error rate or latency worsens, stop and roll back the app. This is safe because the schema still supports the old version.
6. **Ship the cleanup migration in a later release.** Drop the old column only after no old version can run and rollback is no longer needed. This is the contract step.

**Trade-offs and what can go wrong**
- It takes more releases and temporary duplicate columns, which is slower than one rename.
- Some DDL locks big tables. Adding an index or a default can block writes, so check your database's online-DDL behaviour and test with production-sized data.
- A migration that "works" on an empty test database can still break the old app. Add a Testcontainers test that applies migrations to a real database of the same type and then runs the previous app version's key queries.
- Dropping a column too early removes your rollback path.
- Batch backfills that are too large can overload the database.

**How I'd monitor it**
- Error rate and p99 latency split by app version, during the canary window.
- Splunk searches for `ERROR` with SQL exceptions (for example "column not found") grouped by pod version.
- Readiness failures and restarts.
- The Flyway history table, migration duration and database lock waits.
- Alerts that block promotion automatically.

**Follow-ups to expect**
- *How do you roll back?* -> Roll back the app only. The expand-only schema still supports the old version. Fix forward for data issues.
- *How do you rename a column safely?* -> Add the new column, dual-write, backfill, switch reads, then drop the old column in a later release.
- *Why not run migrations at app startup?* -> Many pods start together and long migrations fail readiness. A separate job gives control and clear failure handling.

**60-second answer**
A rolling release means old and new app versions run together against one database. So every migration must work for both. I split changes into expand and contract. The pipeline first runs an additive Flyway or Liquibase migration as a separate step. It then rolls out the app gradually with readiness probes, and smoke tests plus error and latency metrics decide whether to promote it. If something fails, I roll back only the app, which is safe because the old schema is untouched. The cleanup migration, such as dropping the old column, ships in a later release once no old version is running. I also test migrations against a real database with Testcontainers, using the previous app version's queries.

### Q15 [senior] What is a flaky test and how do you fix them?
tags: flaky-test, testing, ci, junit5, testcontainers, awaitility, test-isolation, basics

**Start here: the concepts**
- **Flaky test:** a test that sometimes passes and sometimes fails on the same code, with no change in between. It gives no reliable signal.
- **Deterministic:** the same input always gives the same result. A good test is deterministic. A flaky one depends on something the test does not control.
- **Common causes:** time (the clock, timeouts, time zones), concurrency (threads finishing in a different order), shared state (a database row or static variable left by another test), test ordering (test B only passes if test A ran first), and external services (a network call that is slow or down).
- **Fake clock:** the code asks an injected clock object for the time instead of calling the system clock directly. The test can then freeze or move time itself.
- **Isolated data:** each test creates its own data and cleans up, or runs in its own throwaway database, so tests cannot affect each other.
- **Proper wait:** wait until a condition is true, with a time limit, instead of sleeping a fixed time and hoping.
- **Quarantine:** move a known-flaky test out of the blocking build so it stops stopping everyone, but keep running and tracking it.
- **Flake rate:** the share of runs where a test fails without a real code change.
- **Why this matters:** CI (continuous integration) exists to tell you whether a change is safe. Flaky tests destroy that signal.

**The live scenario**
A team of 40 engineers merges about 60 pull requests a day. About 8% of builds go red from random failures. People start clicking "re-run" without reading the failure. One Friday a red build is re-run and merged. This time the failure was real: a payment-rounding bug that a correct test had caught. About 1,200 orders were charged the wrong amount before the fix. Afterwards the team measured flake rate per test, quarantined the worst 15, and fixed the root causes within two weeks. Random red builds fell below 1%.

**What the interviewer is really checking**
Whether you treat flakiness as a trust and engineering problem, not just "re-run it." They want root-cause thinking and a process that protects the team's trust in a red build.

**How I answer it**
1. **Define it and name the cause categories.** A flaky test is non-deterministic, and the cause is usually time, concurrency, shared state, ordering, or an external service. Naming the category tells you where to look.
2. **Reproduce it before touching it.** Run the test in a loop, in random order, and in parallel. Flakes depend on timing, so a single green run proves nothing.
3. **Quarantine quickly, with an owner and a deadline.** A flaky test blocking the main build teaches people to ignore red. Quarantine removes the noise but must not become a graveyard, so give each one a ticket and a date.
4. **Fix the root cause, not the symptom.**
   - Time: inject a fake clock.
   - Shared state: give each test its own data, or its own database via Testcontainers (real dependencies in throwaway containers).
   - Concurrency: wait for a condition, never `Thread.sleep`.
   - External services: stub them with WireMock, or use a real container.
   - Ordering: remove hidden dependencies between tests.
5. **Track flake rate and protect trust.** Report it per test and per suite. The goal is that a red build always means something real.

```java
await().atMost(5, SECONDS).until(() -> repo.findOrder(id).isPaid()); // Awaitility
```

**Trade-offs and what can go wrong**
- Automatic retries hide flakes and can mask real race conditions in production code. Use them only as a short-term bridge, with the retry count reported.
- Quarantine without ownership means coverage quietly disappears.
- Longer timeouts make tests slower and only hide the problem.
- Real containers are more faithful but slower than mocks. Mocking everything can make tests stable but meaningless.
- Sometimes the flake is a real bug in the application, such as a race condition. Do not assume the test is at fault.

**How I'd monitor it**
- Flake rate per test, from CI history: failed-then-passed on the same commit.
- Share of builds that go red and then green on re-run, with an alert if it passes about 2%.
- Size and age of the quarantine list.
- Time to merge, and the number of manual re-runs per day.
- Searchable CI logs (for example in Splunk) grouped by test name, to find the worst offenders.

**Follow-ups to expect**
- *Should you auto-retry failed tests?* -> Only as a temporary measure, and always report retried passes as flakes. Otherwise real race conditions get hidden.
- *Why not just use `Thread.sleep`?* -> It is either too short, so the test fails on a slow machine, or too long, so the suite is slow. Waiting on a condition with a timeout is both faster and safer.
- *How do you stop new flaky tests from entering?* -> Run new or changed tests many times in CI, randomize order, run in parallel, and review tests for clock, shared data, and sleep usage.

**60-second answer**
A flaky test passes or fails on the same code. It is usually caused by time, concurrency, shared state, test ordering, or an external service. The real damage is that people stop trusting red builds, and then a real failure gets ignored. First I reproduce it by running it in a loop and in random order. Then I quarantine it with an owner and a deadline so the main build stays trustworthy. I fix the root cause: a fake clock for time, isolated data or Testcontainers for state, condition-based waits instead of sleeps, and WireMock for outside services. Finally I track flake rate so a red build always means something real.

### Q16 [senior] Performance and load testing tools and approach?
tags: performance-testing, load-testing, gatling, k6, jmeter, ci-quality-gates, basics

**Start here: the concepts**
- **Load test**: sends many simulated users' requests to a system to see how it behaves under expected traffic. It exists because code that is correct for one user can still be slow or broken for 5,000.
- **Gatling, k6, JMeter**: tools that generate this traffic. JMeter is GUI/XML-driven and widely known. Gatling (tests as code, JVM-based) and k6 (tests in JavaScript) fit version control and pipelines well.
- **Realistic data**: test inputs that look like production (varied users, IDs, payload sizes). One repeated ID hits the cache every time and hides real database cost.
- **Think-time**: the pause a real user takes between actions. Without it, each virtual user acts like a machine and the load is unrealistic.
- **Ramp-up**: raising load gradually, so you see where things start to degrade instead of slamming the system cold.
- **Steady state**: holding the target load for a while. The numbers you report come from this phase.
- **Spike test**: a sudden jump (e.g. a flash sale) to check how the system copes and recovers.
- **Soak test**: moderate load for hours, to expose slow problems such as memory leaks, connection leaks and disk filling.
- **p95/p99**: the latency under which 95% or 99% of requests finish. Averages hide the slow tail that users actually feel.
- **Error rate**: the percentage of failed requests (5xx, timeouts).
- **Saturation metrics**: how full a resource is (CPU, heap/GC, thread pool, DB connection pool, queue depth). They show *why* latency rises.
- **Production-like environment**: same instance sizes, configuration and data volume as production. Otherwise results don't transfer.

**The live scenario**
A checkout API handled 200 requests/s in QA with a 120 ms average. After a marketing email, production hit 1,500 requests/s. p99 jumped from 400 ms to 9 s and 6% of requests timed out. The cause was a DB connection pool of 20, which a single QA user flow never exhausted. A load test with realistic data and a ramp-up would have shown the pool saturating, with the knee in the latency curve, well before launch.

**What the interviewer is really checking**
Whether you treat load testing as a method (goals, realistic workload, right metrics, finding bottlenecks) rather than "run JMeter and look at the average". Seniors are expected to link results to saturation and to automate it.

**How I answer it**
1. **Define goals first.** For example "1,500 req/s, p95 < 300 ms, errors < 1%". Without a target, a result means nothing.
2. **Model the workload from real traffic.** Take the request mix and user behaviour from production logs, and use realistic data plus think-time, so the load resembles reality.
3. **Run in a production-like environment.** Match sizing, config and data volume. A small database with 1,000 rows will not show the slow query that appears at 50 million.
4. **Run in phases.** Ramp up to find where it bends, hold steady state to measure, then run a spike test for sudden surges and a soak test for slow leaks. Each phase finds a different class of bug.
5. **Measure p95/p99 and error rate, not averages.** Averages hide the tail.
6. **Watch saturation alongside.** The first resource to hit its limit is the bottleneck. Fix that one, then rerun.
7. **Automate a small smoke load test in CI/CD with thresholds.** Run a short, light test on each build and fail it on regressions. The full tests run on a schedule or before releases.
```js
thresholds: { http_req_duration: ['p(95)<300'], http_req_failed: ['rate<0.01'] }
```

**Trade-offs and what can go wrong**
- Prod-like environments cost money, and a shared environment makes results noisy.
- Pipeline tests are short and noisy, so they catch only large regressions, not subtle ones.
- Closed-model tools (fixed users, each waiting for its response) slow down when the server slows, which understates the problem. For arrival-rate traffic, use an open model (fixed requests per second).
- The load generator itself can be the bottleneck. Monitor its CPU too.
- Mocked downstream services that answer instantly make results too optimistic.
- Unrealistic or too-small datasets give false confidence.

**How I'd monitor it**
Track p50/p95/p99, throughput and error rate per endpoint, alongside CPU, GC pauses, heap, thread-pool and connection-pool usage, DB slow queries, and Kafka consumer lag where relevant. Use Grafana/Prometheus or APM during the run, and Splunk searches on errors and timeouts for the test window. Alert and fail the build when thresholds are breached.

**Follow-ups to expect**
- *Why p99 and not average?* -> A few very slow requests barely move the average, but they hit real users, and in microservice chains they multiply.
- *How do you find the bottleneck?* -> Raise load until latency bends, then see which saturation metric hits its limit first (pool, CPU, DB). Fix it and retest.
- *Can you load test in production?* -> Sometimes, with synthetic traffic, feature flags and a limited blast radius. Usually a prod-like environment is safer.

**60-second answer**
I start with goals, such as a target request rate, p95 latency and error budget. Then I build a workload from real production traffic using Gatling, k6 or JMeter, with realistic data and think-time. I run it in a production-like environment: ramp up to find where it degrades, hold steady state to measure, then run spike and soak tests for sudden surges and slow leaks. I report p95/p99 and error rate rather than averages, and watch saturation metrics like CPU, heap, thread pools and DB connections to find the real bottleneck. Finally, I put a short smoke load test in the pipeline with thresholds, so regressions fail the build before release.

### Q17 [architect] Design the quality strategy for a team of 8 working on 5 microservices.
tags: testing, quality-strategy, microservices, testcontainers, contract-testing, ci-quality-gates, basics

**Start here: the concepts**
- **Unit test:** checks one class or function in memory, with no network or database. It is fast (milliseconds) and catches logic bugs. JUnit 5 runs it and Mockito fakes the collaborators.
- **Integration test:** checks that our code works with a real dependency such as a database or Kafka. **Testcontainers** starts that dependency in a throwaway Docker container, so the test hits real behaviour instead of a mock. It needs Docker on the CI agents.
- **Contract test:** checks that two services agree on the shape of their messages or API. In *consumer-driven* contracts (Pact, Spring Cloud Contract), the caller writes down what it needs and the provider's build must satisfy it. This replaces running every service together.
- **E2E smoke test:** a few tests that run through the deployed system, for example "place an order". They are slow and brittle, so keep them few.
- **Definition of Done (DoD):** a shared checklist a change must satisfy before it counts as finished.
- **Quality gate:** an automatic pipeline check that fails the build. SonarQube can apply it to *new code* only, so legacy debt does not block everyone.
- **ArchUnit:** a library that turns architecture rules into tests, such as "controllers must not call repositories".
- **Trunk-based development:** everyone merges small changes to one main branch daily. **Feature flags** hide unfinished work behind a switch.
- **Flaky test:** a test that sometimes fails with no code change. It trains people to ignore red builds.

**The live scenario**
(Illustrative numbers.) The orders team renamed a JSON field from `customerId` to `customerRef`. Their unit tests passed, because the payment client was mocked. After deploy, about 15% of checkouts failed for 40 minutes, until a rollback. Each team had good coverage, but nothing tested the agreement between services. Afterwards the team added consumer-driven contract tests to both pipelines, and this class of break now fails the provider's build.

**What the interviewer is really checking**
Whether you can design a system of checks: which level protects against which risk, what each costs, and how the habits and automation keep it working. Listing tools is not enough.

**How I answer it**
1. **Agree a Definition of Done:** tests, peer review, docs and observability (logs, metrics, alerts). Reason: with 8 people, quality depends on shared habits, not individual heroics.
2. **Per service, many unit tests and a focused set of Testcontainers integration tests.** Unit tests are cheap and cover logic. Integration tests cover SQL, serialization and Kafka config, where mocks lie.
3. **Contract tests between services.** They catch the scenario's failure in minutes, without a shared test environment.
4. **Only a few E2E smoke tests** on critical journeys. Reason: they are costly and flaky, so they confirm wiring and do not hunt bugs.
5. **Quality gates in the pipeline:** Sonar on new code (no new bugs or vulnerabilities, a sensible coverage floor on changed lines) plus ArchUnit rules. Reason: the build enforces standards, so reviewers can focus on design.
6. **A PR template and checklist** mirroring the DoD, so review is consistent.
7. **Trunk-based development with feature flags.** Reason: small merges keep integration pain low, and flags separate deploy from release. This only works with a fast, trusted pipeline.
8. **Shared pipeline templates** across all five services, so a fix to the build or scan steps is made once.
9. **A weekly review of flaky tests and vulnerabilities.** Fix or delete flaky tests, and triage dependency alerts on a schedule.

**Trade-offs and what can go wrong**
- Coverage targets get gamed. Test behaviour, not implementation details, or refactors break tests and block progress.
- Testcontainers slows the build and needs Docker. Reuse containers and keep integration tests focused.
- Contract tests need ownership. Stale contracts give false confidence.
- Strict gates on old code stall the team, so gate only new code.
- Skipping the flaky-test review leads people to rerun until green and ignore failures.

**How I'd monitor it**
- Track pipeline duration, flaky-test rate, and the change failure rate and rollbacks (DORA metrics).
- Track escaped defects: production bugs per release, each tagged with the test level that should have caught it.
- Watch the Sonar new-code trend and the open vulnerability count.
- In Splunk, search error spikes right after deploys and correlate them with the release version.

**Follow-ups to expect**
- *Why not just more E2E tests?* -> They are slow, flaky and hard to debug. Contract and integration tests give faster, more precise feedback.
- *How do you handle a breaking API change?* -> Make it backward compatible (add the new field, keep the old), migrate consumers while contract tests prove they work, then remove the old field.
- *What coverage number would you set?* -> A floor on new code, such as the Sonar default, and never a global target. Mutation testing or review of risky areas says more than the percentage.

**60-second answer**
I start with a shared Definition of Done: tests, review, docs and observability. In each service I write many fast unit tests and focused Testcontainers integration tests against real databases and Kafka. Between services I use consumer-driven contract tests, because most outages come from mismatched agreements, not from logic bugs. I keep only a few end-to-end smoke tests for critical journeys. The pipeline enforces Sonar gates on new code and ArchUnit rules, and shared templates keep all five services consistent. We work trunk-based with feature flags, and each week we review flaky tests and vulnerabilities. I judge the strategy by escaped defects and change failure rate, not by coverage.

### Q18 [mid] Static analysis and code style tooling?
tags: static-analysis, code-style, checkstyle, sonarqube, archunit, ci-quality-gates, basics

**Start here: the concepts**
- **Static analysis**: a tool reads your code (source or compiled bytecode) without running it and flags suspicious patterns. It exists because many bugs follow known shapes that a machine can spot faster than a tired reviewer.
- **Code style/formatting**: rules for layout and naming (indentation, import order, naming). Consistency keeps code reviews and diffs free of noise.
- **Checkstyle**: checks style rules and reports violations. It reports, it does not fix.
- **Spotless**: automatically reformats code to an agreed format, so nobody argues about it.
- **SpotBugs**: scans compiled bytecode for likely bugs (null dereferences, resource leaks).
- **Error Prone**: a compiler plugin that flags common mistakes while `javac` compiles, so the build fails right away.
- **PMD**: scans source for bad practices (unused code, empty catch blocks, overly complex methods).
- **SonarQube**: a server that gathers results, tracks them over time and applies a **quality gate**, a pass/fail rule (for example, no new bugs and coverage on new code above a set level). It also lists **security hotspots**: code that is security-sensitive and needs a human decision, not a confirmed vulnerability.
- **ArchUnit**: a library that turns architecture rules into ordinary JUnit tests (for example, "controllers must not call repositories directly").
- **OpenRewrite**: applies automated code changes ("recipes") across a codebase, for example a Java or Spring Boot upgrade.

**The live scenario**
A payments service handles about 200 requests per second. A developer adds a JDBC query but forgets to close the connection on an error path. Under normal load nothing shows. During a partner outage, errors spike, the pool of 20 connections drains in minutes, and the API times out for 25 minutes. A reviewer had missed it in a 600-line pull request. SpotBugs flags this exact pattern. Afterwards the team added SpotBugs and Error Prone to CI and a Sonar quality gate on new code, so the pattern fails the build before a human has to spot it.

**What the interviewer is really checking**
Whether you know which tool catches which class of problem, and that you wire them into the workflow (CI, IDE, quality gate) instead of just naming them. Also whether you understand that tools handle mechanical issues so people can review design.

**How I answer it**
1. **Group tools by the problem they solve.** Format and style (Spotless, Checkstyle), bug patterns (SpotBugs, Error Prone, PMD), overall quality and security (SonarQube), architecture (ArchUnit), migrations (OpenRewrite). Different tools see different things, so naming the problem shows understanding.
2. **Auto-fix what can be fixed.** Spotless reformats on build or commit, so style is never a review comment.
3. **Fail the build on real bugs.** Error Prone fails at compile time and SpotBugs runs in CI. Early failure is cheap, while a production failure is not.
4. **Gate on new code.** A SonarQube quality gate applies to code changed in the pull request. Gating the whole legacy codebase would block everyone, while gating new code stops things getting worse.
5. **Encode architecture as tests.** For example:
   `noClasses().that().resideInAPackage("..controller..").should().dependOnClassesThat().resideInAPackage("..repository..")`
   The rule then runs on every build and cannot be forgotten.
6. **Use OpenRewrite for mass changes.** A recipe upgrades thousands of lines consistently and the result is reviewable as a diff.
7. **Run in both IDE and CI.** The IDE gives instant feedback, and CI is the enforced source of truth. The result is that reviewers spend their time on design, naming and edge cases.

**Trade-offs and what can go wrong**
- **False positives**: too many noisy warnings teach people to ignore all of them. Tune the rules and suppress with a written reason.
- **Slow builds**: run heavy scans in CI, not on every local compile.
- **Legacy noise**: turning everything on at once produces thousands of findings. Gate only new code and pay down old issues gradually.
- **Metric gaming**: a green gate does not mean good design. Tools do not replace tests or review.
- **Security hotspots** need a human decision, so someone must own triaging them.
- **Rule overload**: too many style rules waste effort. Keep only the ones that prevent real problems.

**How I'd monitor it**
- Quality gate pass/fail rate and the number of builds it blocks.
- Count of new bugs, vulnerabilities and unreviewed hotspots per release in SonarQube.
- Trend of technical debt and duplicated code over time.
- Suppression count (for example, `@SuppressWarnings` and `NOSONAR`), which shows whether the rules are being bypassed.
- ArchUnit test failures in CI, and CI scan duration.

**Follow-ups to expect**
- *Checkstyle vs Spotless?* -> Checkstyle reports violations, Spotless rewrites the code to fix formatting. I use Spotless for layout and Checkstyle only for rules it can't auto-fix.
- *How do you introduce Sonar on a legacy project?* -> Apply the quality gate to new code only, fix old issues gradually, and never block the team on historical debt.
- *Does static analysis replace tests?* -> No. It finds known bad patterns without running the code, while tests verify behaviour and business rules.

**60-second answer**
I split static tooling by the problem it solves. Spotless auto-formats and Checkstyle enforces style, so formatting never comes up in review. SpotBugs, Error Prone and PMD catch bug patterns such as leaks and null mistakes. SonarQube collects the results, applies a quality gate to new code and lists security hotspots for humans to review. ArchUnit turns architecture rules into JUnit tests, and OpenRewrite automates large migrations. I run them in the IDE for fast feedback and in CI for enforcement, tune rules to avoid noise, and watch the suppression count. That way reviewers can focus on design instead of mechanical issues.

### Q19 [mid] How do you secure the build pipeline (supply chain)?
tags: supply-chain-security, ci-cd, dependency-pinning, cosign, slsa, oidc, basics

**Start here: the concepts**
- **Supply chain:** everything that goes into your software besides your own code: libraries, build tools, base images, the CI server and its credentials. An attacker who tampers with any of these ships malicious code without touching your repo.
- **Pinned dependency:** a dependency locked to an exact version instead of a range like "latest 1.x". Builds are then repeatable, and a new malicious release cannot slip in unnoticed.
- **Verified dependency:** its checksum (a fingerprint of the file) is compared with a recorded value, so a swapped file is rejected.
- **Private artifact repository:** your own internal store (for example Nexus or Artifactory) that proxies public registries. Builds pull only from it, so you control and scan what enters.
- **Image signing (cosign):** cosign is a tool that adds a digital signature to a container image. The cluster can then check "was this built by our pipeline?" before running it.
- **Provenance and SLSA:** provenance is a signed record of how an artifact was built (source commit, builder, steps). SLSA ("salsa") is a framework of levels that describes how trustworthy that record is.
- **OIDC for pipeline credentials:** instead of storing a cloud password in CI, the pipeline proves its identity with a short-lived token, and the cloud exchanges it for temporary access. Nothing long-lived exists to steal.
- **Least privilege:** each job gets only the permissions it needs.
- **Protected branches:** rules that block direct pushes to main and require reviews and passing checks.
- **Secret scanning:** automated search for passwords and keys in commits.
- **Isolated build runners:** fresh, separate machines per build, so one build cannot read another's data or leave malware behind.

**The live scenario**
A team of 40 developers runs about 200 builds a day. A library used the version range `1.+`. One morning a compromised patch release was published and the next build pulled it in. It also ran with a long-lived deploy key stored in CI variables. Within hours, 12 services were built with the bad library. The key was exposed in build logs, and the team spent two days rotating secrets and rebuilding. Afterwards they pinned versions, moved to OIDC and signed their images.

**What the interviewer is really checking**
Do you see the pipeline itself as an attack target, and can you name layered controls (inputs, credentials, outputs, people) with the reason for each, rather than just listing tools?

**How I answer it**
1. **Control inputs: pin and verify dependencies.** Use exact versions plus lockfiles or checksum verification. Reason: repeatable builds and no surprise code.
2. **Pull through a private artifact repository.** Reason: one controlled gate where you can scan, block bad packages and keep copies if the public registry disappears. It also reduces the risk of dependency confusion, where a public package imitates an internal name.
3. **Remove long-lived secrets: OIDC with least privilege.** Reason: a stolen short-lived token expires quickly, and a narrow scope limits the damage. For example, in GitHub Actions:
   ```yaml
   permissions: { id-token: write, contents: read }
   ```
4. **Protect the source: protected branches with required reviews.** Reason: no single person, or a stolen account, can push code straight to production. Add secret scanning to catch leaked keys before they spread.
5. **Isolate builds: ephemeral, separate runners.** Reason: a compromised build cannot persist or reach other projects' secrets.
6. **Secure the output: sign images with cosign and publish SLSA provenance.** Reason: the deploy step verifies the signature and refuses anything not built by your pipeline.
7. **Keep tests and gates in the pipeline.** Dependency vulnerability scans and the usual unit and integration tests run as required checks, so a bad change fails the build.

**Trade-offs and what can go wrong**
- Pinning means you must update deliberately. Use an automated update bot with PRs, or you will run old, vulnerable versions.
- Signing proves who built the artifact, not that it is safe. A signed image can still contain a vulnerable library, so keep scanning.
- Required reviews slow delivery and become rubber-stamping if reviewers are overloaded.
- Ephemeral runners cost more and slow builds if caches are lost.
- A common mistake is a signature that nobody verifies at deploy time. It then gives no protection.

**How I'd monitor it**
- Admission control (such as a policy engine in Kubernetes) rejects unsigned images, and you alert on rejections.
- Dependency and secret scanner findings are tracked, with time-to-fix.
- Audit logs of pipeline changes, branch protection changes and token use; for example, a Splunk search for pipeline runs from unexpected branches or users.
- A report of how many builds still use long-lived secrets (target: zero).

**Follow-ups to expect**
- *What is dependency confusion?* -> An attacker publishes a public package with the same name as your internal one at a higher version. A private repository with proper source rules prevents it.
- *Why OIDC rather than a secret in a CI variable?* -> The token is short-lived and tied to a specific repo and branch, so there is nothing permanent to leak.
- *What is an SBOM?* -> A list of every component in the artifact, so you can quickly find affected services when a new vulnerability is announced.

**60-second answer**
I protect the pipeline in layers. First, inputs: I pin and verify dependencies and pull them only through a private artifact repository. Second, credentials: the pipeline uses OIDC to get short-lived, least-privilege access, so no long-lived secrets are stored, and secret scanning catches leaks. Third, people and code: protected branches with required reviews, and isolated, throwaway build runners. Fourth, outputs: I sign images with cosign and publish SLSA provenance, and the cluster verifies the signature before running anything. Signing does not prove the code is safe, so I keep vulnerability scans and tests as required gates, and I monitor rejections and audit logs.
