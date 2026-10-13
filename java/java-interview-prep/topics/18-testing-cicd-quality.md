---
id: 18-testing-cicd
title: Testing, CI/CD, Code Quality & Security Hygiene
focus: JUnit 5, Mockito, Testcontainers, pipelines, quality gates, supply-chain security
deep_dive: 15
examples: 15_testing
---

### Q1 [basic] What is the test pyramid?
Many fast unit tests, fewer integration tests (real DB/broker), very few end-to-end UI tests. Fast feedback and low flakiness at the bottom; confidence in real wiring in the middle; a thin top for critical user journeys.

### Q2 [basic] JUnit 5 essentials?
`@Test`, `@BeforeEach/@AfterEach`, `@ParameterizedTest` with `@CsvSource/@MethodSource`, `@Nested`, `assertThrows`, `assertAll`, extensions (`@ExtendWith`), `@Tag` for grouping, `@DisplayName`. Combine with AssertJ for readable assertions.

### Q3 [intermediate] Mock vs Stub vs Spy vs Fake?
Stub returns canned answers; mock verifies interactions; spy wraps a real object; fake is a working lightweight implementation (in-memory repo). Prefer fakes/state assertions; over-mocking couples tests to implementation.

### Q4 [intermediate] Mockito: common patterns and pitfalls?
`when(repo.find(1)).thenReturn(x)`, `verify(repo).save(captor.capture())`, `ArgumentCaptor`, `doThrow` for void methods, `@InjectMocks`. Pitfalls: mocking value objects, verifying too much, mocking static/final unless necessary, tests that pass with no assertion.

### Q5 [intermediate] Spring Boot test slices?
`@WebMvcTest` (controller + MVC only, mock services), `@DataJpaTest` (JPA + embedded/Testcontainers DB), `@JsonTest`, `@RestClientTest`, and `@SpringBootTest` (full context, use sparingly - slow). Boot 4 modularises test starters. `@MockBean` is replaced by `@MockitoBean` in Spring Framework 6.2+.

### Q6 [intermediate] What is Testcontainers and why use it over H2?
Runs real dependencies (PostgreSQL, Oracle XE, Kafka, Redis, Couchbase) in Docker for tests, so SQL dialect, constraints, and broker behaviour match production. H2 hides dialect differences and passes tests that fail in prod. Reuse containers (singleton) to keep the suite fast.

### Q7 [intermediate] How do you test asynchronous code?
Use Awaitility (`await().atMost(5, SECONDS).untilAsserted(...)`) instead of `Thread.sleep`; inject a controllable clock/executor; for Kafka, produce and await a result in the sink; for `CompletableFuture`, join with timeouts.

### Q8 [intermediate] What is TDD and when is it worth it?
Red-Green-Refactor: write a failing test, make it pass minimally, refactor. Best for business logic with clear rules and bug fixes (write a failing test that reproduces the bug first). Less value for exploratory spikes or thin glue code.

### Q9 [intermediate] Consumer-driven contract testing?
The consumer defines expectations (Pact / Spring Cloud Contract); the provider verifies them in CI. Prevents breaking changes between services without a full environment. Publish contracts to a broker, gate provider builds.

### Q10 [intermediate] What code coverage target do you set?
Coverage is a signal, not a goal: ~70-80% on new code with meaningful assertions, 100% on critical business rules, and **mutation testing** (PIT) to check that tests really fail when code changes. Use SonarQube quality gates on new code, not only the total.

### Q11 [intermediate] Describe a good CI/CD pipeline for a Java service.
Commit -> build & unit tests -> static analysis (Sonar, SpotBugs) + dependency/license scan (OWASP Dependency-Check/Snyk) -> integration tests (Testcontainers) -> build image + SBOM + image scan -> push to registry -> deploy to dev automatically -> contract/smoke tests -> staging -> approval -> production canary with automated rollback. Pipeline-as-code (Jenkinsfile/GitHub Actions).

### Q12 [intermediate] Branching strategy: GitFlow vs trunk-based?
GitFlow: long-lived develop/release branches, heavier merging, suits scheduled releases. Trunk-based: short-lived branches, small PRs, feature flags, continuous integration - best for fast delivery with strong tests. Choose per release cadence; avoid long-running branches.

### Q13 [intermediate] How do you handle dependency and vulnerability management?
Automated updates (Renovate/Dependabot), BOMs to align versions, scanning in CI with a policy (fail on critical CVEs), SBOM generation (CycloneDX), removing unused dependencies, tracking end-of-life versions (Spring Boot 3.x, Java 8), and a patch SLA by severity.

### Q14 [advanced] Zero-downtime release with database migration - how does the pipeline support it?
Migration step runs before the app rollout (Flyway/Liquibase) and must be backward compatible; app rollout is rolling/canary with readiness; smoke tests gate promotion; the cleanup migration (drop column) ships in a later release.

### Q15 [advanced] What is a flaky test and how do you fix them?
Passes/fails non-deterministically: time, concurrency, shared state, ordering, external services. Quarantine quickly, fix the root cause (fake clock, isolated data, proper waits), track flake rate; never let a flaky suite train people to ignore red builds.

### Q16 [advanced] Performance and load testing tools and approach?
Gatling/k6/JMeter, realistic data and think-time, ramp-up, steady state, spike and soak tests, measure p95/p99 and errors, watch saturation metrics, run in a production-like environment, automate a smoke load test in the pipeline with thresholds.

### Q17 [design] Design the quality strategy for a team of 8 working on 5 microservices.
Definition of Done (tests, review, docs, observability), unit + Testcontainers integration per service, contract tests across services, a few E2E smoke tests, Sonar gates on new code, ArchUnit rules, PR template and checklist, trunk-based dev with feature flags, shared pipeline templates, a weekly flaky-test and vulnerability review.

### Q18 [intermediate] Static analysis and code style tooling?
Checkstyle/Spotless (format), SpotBugs/Error Prone/PMD (bugs), SonarQube (quality gate, security hotspots), ArchUnit (architecture rules), OpenRewrite (automated refactors/migrations). Automate in CI and IDE; reviews then focus on design.

### Q19 [intermediate] How do you secure the build pipeline (supply chain)?
Pinned and verified dependencies, private artifact repository, signed images (cosign) and provenance (SLSA), least-privilege pipeline credentials via OIDC (no long-lived secrets), protected branches with required reviews, secret scanning, and isolated build runners.

### Q20 [intermediate] How are you using AI assistants (Copilot / Claude Code / Amazon Q) in engineering - and what are the guardrails?
Use them for boilerplate, tests, refactors, code review hints and documentation, and for exploring unfamiliar code. Guardrails: humans own the code (review everything), never paste secrets/customer data, run the full test and security pipeline, keep prompts/context scoped (e.g. via Amazon Bedrock inside the company boundary), measure impact (cycle time, defect rate), and teach the team good prompting. Relevant to your Claude-via-Bedrock and Amazon Q rollout.

### Q21 [design] Design a CI/CD pipeline for a microservice with security and quality gates and fast feedback.
Stages: build + unit tests (minutes) -> static analysis, dependency and secret scanning -> build image and scan it -> deploy to ephemeral/test environment -> contract and integration tests (Testcontainers) -> smoke test -> progressive prod rollout with automated rollback. Fail fast, cache dependencies, run slow suites in parallel or nightly, keep pipelines as code, and sign artifacts. Trade-off: every gate adds time - measure lead time and prune low-value checks.

### Q22 [design] Design a strategy for eliminating flaky tests in a large suite.
Measure first: track failure rate per test over many runs and quarantine anything above a threshold into a non-blocking job with an owner and a deadline. Fix root causes: shared state, time and randomness (inject a `Clock`), async waits (use `Awaitility` not `sleep`), test-order dependence, and shared external environments (Testcontainers per run). Fail the build on new flaky tests. Failure mode: a retry-everything policy that hides real race conditions.
