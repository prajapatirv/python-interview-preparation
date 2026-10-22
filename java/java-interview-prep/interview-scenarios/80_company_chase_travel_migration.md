---
id: company-chase-travel-migration
title: Company pack, Chase Travel (1/2): Java rewrite, upgrade and migration (15 questions)
stack: java
skill: architecture
---
Company-level pack for a **Chase Travel / Java rewrite** engagement (see `../company-chase-travel/README.md`).

**Read this first.** Chase Travel's internal architecture and the details of any "Java rewrite" programme are **not
public**. Public facts: JPMorgan Chase acquired cxLoyalty's travel platform (closed early 2021) and moved its card-rewards
travel portal back onto it; Chase Travel engineering job posts list Java or .NET, React and Spring Boot; JPMorgan Chase
is publicly cited as a large-scale OpenRewrite user for keeping Java applications on supported versions. Everything
else below is an **illustrative scenario** built from common travel-industry and enterprise-migration patterns. In the
interview, say "in a platform like yours..." and never claim inside knowledge.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [architect] How would you approach rewriting a legacy travel platform (older J2EE or .NET services) into Java and Spring Boot?
tags: rewrite, modernization, strangler-fig, replatform, legacy-migration, chase-travel, company-chase-travel

**Start here: the concepts**
- **Modernisation options (the "Rs"):** retain, rehost (lift and shift), replatform (same code, new runtime), refactor (improve in place), **rearchitect/rewrite**, replace (buy), retire.
- **Big-bang rewrite:** build everything new, switch in one go. High risk: years without value, and the old system keeps changing.
- **Incremental rewrite (strangler fig):** replace one capability at a time behind a routing layer.

**The live scenario (functional requirement)**
*FR (illustrative): "A card-rewards travel platform built over many years (part J2EE, part .NET) must move to a single Java/Spring Boot microservices stack on the cloud, without interrupting bookings, points redemptions or customer service, while new features keep shipping."*

**What the interviewer is really checking**
That you de-risk a rewrite with incremental delivery, measurable parity, and business continuity.

**How I answer it**
1. **Why are we rewriting?** Agree measurable goals: one stack and skill set, faster releases, cloud scalability for peaks, end-of-support runtimes, security/compliance. Goals decide priorities.
2. **Assess:** inventory services, dependencies, data stores, supplier integrations, batch jobs, traffic and pain points; find seams (bounded contexts: search, pricing, booking, payments/points, fulfilment, servicing, notifications).
3. **Choose per component:** not everything needs a rewrite: stable low-change parts can be replatformed or retained for now; high-change or high-pain parts are rewritten first.
4. **Strangler fig:** a gateway/facade routes traffic per capability; build the new Java service, run it in **shadow mode** (receive mirrored traffic, compare outputs), then switch traffic gradually (by percentage, brand, or customer segment).
5. **Data:** each new service owns its data; legacy and new are synced through CDC during transition; one writer per data item at a time.
6. **Safety net:** characterisation tests, contract tests, replayed production traffic, performance baselines.
7. **Platform first:** CI/CD, Kubernetes, observability, security baselines, a company Spring Boot starter, so each migrated service is cheap.
8. **Deliver value along the way:** each migrated slice must ship something (faster search, a new channel), or funding dries up.

**Trade-offs and what can go wrong**
- Rewriting "as-is" faithfully copies 15 years of accidental complexity; rewriting "to-be" without parity tests breaks hidden business rules. Do both consciously: document rules, keep the valuable ones.
- Two systems in parallel cost more for a while; plan for it.
- Freezing legacy features for long periods frustrates the business; keep a thin change path.

**How I'd monitor it**
Percentage of traffic on new services per capability, parity mismatch rates in shadow mode, booking success rate and latency old vs new, legacy decommission milestones.

**Follow-ups to expect**
- *Why not big-bang?* -> No value until the end, huge cutover risk, and the target moves.
- *How do you find hidden business rules?* -> Code reading with domain experts, production logs, characterisation tests, and shadow-mode diffs.
- *Which slice first?* -> High value, low coupling, easy to verify (e.g. read-only content or search), not payments.

**60-second answer**
"I'd avoid a big-bang rewrite. First agree why we're rewriting and how we measure it, then map the platform into bounded contexts like search, pricing, booking, points, fulfilment and servicing, and decide per component: rewrite, replatform or retain. New Java services go behind a strangler facade, run in shadow mode against mirrored traffic until outputs match, then take traffic gradually. Data syncs through CDC during the transition, a shared platform makes each migration cheap, and every slice ships some business value."

### Q2 [architect] Run legacy and new services side by side: shadow traffic, parallel run and output comparison.
tags: shadow-traffic, parallel-run, dark-launch, diffing, verification, migration, company-chase-travel

**Start here: the concepts**
- **Shadow (mirrored) traffic:** a copy of real requests goes to the new service; its responses are recorded and compared, but never returned to users.
- **Parallel run:** both systems process the same work (e.g. batch) and outputs are reconciled.
- **Diffing:** structured comparison that ignores expected differences (timestamps, ids, ordering).

**The live scenario (functional requirement)**
*FR (illustrative): "The new Java pricing service must calculate points-and-cash prices identically to the legacy engine for every hotel offer before it can serve customers."*

**What the interviewer is really checking**
A rigorous way to prove behavioural parity at production scale without customer risk.

**How I answer it**
1. **Mirror at the edge:** the gateway or service mesh mirrors a percentage of read-only pricing requests to the new service (writes are never mirrored blindly).
2. **Compare asynchronously:** both responses are published to a comparison topic; a diff service normalises (rounding rules, ordering, timestamps) and classifies mismatches (field, magnitude, supplier, currency).
3. **Triage:** each mismatch category is a bug in new code, a bug found in legacy code (decide with business whether to replicate), or an accepted difference.
4. **Exit criteria:** e.g. 99.99% exact match over 2 weeks including a peak weekend; zero mismatches above 1 point/1 cent.
5. **Then switch** traffic gradually, keeping comparison running in reverse (legacy as shadow) for a while for rollback confidence.
6. For **side-effecting operations** (bookings), use a sandbox supplier or "dry-run" mode, or compare at the decision level (what would be booked) rather than executing twice.

**Trade-offs and what can go wrong**
- Mirroring doubles load on shared downstreams (suppliers!); mirror only when responses can be served from cache, or stub supplier calls in the shadow path.
- PII in comparison stores; mask and limit retention.
- Non-deterministic outputs (live availability) need comparing on the same supplier response snapshot.

**How I'd monitor it**
Match rate over time per category, mismatch backlog, shadow latency vs legacy, extra load on dependencies.

**Follow-ups to expect**
- *Tools?* -> Istio/Envoy mirroring, gateway mirroring filters, or a custom tee in the facade; GitHub's Scientist pattern for in-code experiments.
- *What if legacy is wrong?* -> Product decides; document the intentional difference.
- *How long to shadow?* -> Until exit criteria hold over representative traffic, including peaks and edge cases.

**60-second answer**
"I'd prove parity with production traffic before customers see the new service. The gateway mirrors a share of read-only pricing requests to the new Java service, both responses go to a comparison topic, and a diff service normalises rounding, ordering and timestamps and classifies mismatches. Each category is a new-code bug, a legacy bug the business decides on, or an accepted difference. When we hit exit criteria, like 99.99% match over two weeks including a peak, traffic switches gradually with legacy kept as the shadow for rollback."

### Q3 [senior] Integrate the new Java services with legacy systems and suppliers: Adapter, Facade and Anti-Corruption Layer.
tags: anti-corruption-layer, adapter-pattern, facade-pattern, integration, ddd, design-patterns, company-chase-travel

**Start here: the concepts**
- **Adapter:** converts one interface into another the client expects.
- **Facade:** a simple interface in front of a complex subsystem.
- **Anti-corruption layer (ACL, DDD):** a translation boundary (adapters + translators + facades) so a legacy or external model doesn't leak into your domain.

**The live scenario (functional requirement)**
*FR (illustrative): "New booking services must work with a legacy loyalty system (SOAP, cryptic status codes, a points model in 'units') and several hotel and air suppliers, each with different APIs (REST, SOAP/XML, industry message standards), without that complexity spreading into the new domain."*

**What the interviewer is really checking**
Pattern knowledge applied to keep a clean domain during migration.

**How I answer it**
1. **Domain model first:** our own `PointsBalance`, `Offer`, `Reservation`, `BookingStatus` with clear meanings.
2. **ACL per legacy/external system:** a `LegacyLoyaltyAdapter` implementing our `PointsLedgerPort`; translators map `STATUS=07` -> `BookingStatus.ON_HOLD`, "units" -> points; it hides SOAP behind a facade.
3. **Supplier adapters:** `SupplierClient` port with one adapter per supplier (Strategy + Adapter); a registry selects by supplier code. New suppliers are new adapters, no domain change.
4. **Error translation:** supplier-specific errors -> domain errors (`InventoryUnavailable`, `PriceChanged`, `SupplierTimeout`).
5. **Resilience inside the ACL:** timeouts, circuit breakers, retries per supplier.
6. When legacy is retired, the adapter is replaced by a direct implementation; the domain is untouched.

**Trade-offs and what can go wrong**
- Leaky adapters (passing legacy codes through "just for now") spread legacy semantics everywhere.
- Over-generic supplier abstractions lose important supplier capabilities; allow capability flags.
- Translation tables must be owned and versioned; legacy codes change too.

**How I'd monitor it**
Per-adapter error rates by translated error type, unknown-code counters (unmapped legacy codes), latency per supplier.

**Follow-ups to expect**
- *Adapter vs Facade?* -> Adapter changes an interface to match an expected one; Facade simplifies a subsystem.
- *Where does the ACL live?* -> In the integration/adapter layer of the service (hexagonal), or as a dedicated integration service when shared.
- *SOAP in Spring?* -> Spring Web Services or Jakarta XML Web Services clients, wrapped in the adapter.

**60-second answer**
"The new domain gets its own clean model, points, offers, reservations, statuses, and every legacy or external system sits behind an anti-corruption layer. The legacy loyalty SOAP service becomes an adapter implementing our points ledger port, with translators mapping cryptic codes and units into domain terms. Each supplier gets its own adapter behind one supplier port, chosen by a registry, so a new supplier is a new class. Errors are translated into domain errors and resilience lives in the adapters. When legacy retires, only the adapter changes."

### Q4 [senior] Migrate inside a running codebase with branch by abstraction and feature toggles.
tags: branch-by-abstraction, feature-toggles, trunk-based-development, refactoring, migration, company-chase-travel

**Start here: the concepts**
- **Branch by abstraction:** introduce an abstraction over the old implementation, build the new implementation behind it, switch callers by configuration, then delete the old one, all on trunk.
- **Feature toggles:** release, experiment, ops (kill switch) and permission toggles; need lifecycle management.

**The live scenario (functional requirement)**
*FR (illustrative): "Inside the booking service, replace the legacy in-process fare-rules component with a call to the new Java rules service, with instant fallback if problems appear during peak season."*

**What the interviewer is really checking**
Safe incremental change without long-lived branches.

**How I answer it**
1. Introduce `FareRulesPort`; the old component is wrapped as `LegacyFareRulesAdapter`. Callers switch to the port (no behaviour change; release it).
2. Build `RulesServiceFareRulesAdapter` calling the new service, with timeouts and a circuit breaker.
3. A **toggle-driven router** implementation: by percentage, market or brand; optionally "both" mode comparing results (Q2) and returning the legacy result.
4. Ramp up: 1% -> 10% -> 50% -> 100%, watching error rate, latency and mismatch metrics; toggle back instantly if needed (ops kill switch).
5. Remove the legacy adapter and the toggle once stable (toggle debt is real; give each toggle an owner and expiry date).

**Trade-offs and what can go wrong**
- Toggle combinations explode testing; keep few, short-lived toggles.
- Toggle evaluation must be fast and available; cache flag state locally (Unleash/LaunchDarkly/OpenFeature SDKs do).
- Forgetting to clean up leaves dead code paths.

**How I'd monitor it**
Traffic share per implementation, error/latency per implementation, toggle age report.

**Follow-ups to expect**
- *OpenFeature?* -> A vendor-neutral feature flag API with a Java SDK.
- *Long-lived branches instead?* -> Painful merges and late integration; trunk + abstraction is safer.
- *Toggle in config or code?* -> Runtime flag service for ops toggles; config for static ones.

**60-second answer**
"I put an interface over the legacy fare-rules component and switch callers to it with no behaviour change. Then I build the new adapter calling the rules service, and a toggle-driven router sends traffic by percentage or market, optionally comparing both and still returning legacy. We ramp 1, 10, 50, 100 percent watching errors, latency and mismatches, with a kill switch for instant fallback in peak season. Then the legacy code and the toggle are deleted, because toggles are debt with an expiry date."

### Q5 [senior] Migrate booking and points data with zero loss: CDC, backfill, reconciliation and cutover.
tags: data-migration, cdc, debezium, backfill, reconciliation, cutover, company-chase-travel

**Start here: the concepts**
- **Backfill:** bulk copy of historical data. **CDC:** stream ongoing changes from the source's log.
- **Reconciliation:** prove source and target match (counts, checksums, business totals).
- **Single writer principle:** at any moment one system is authoritative for each record.

**The live scenario (functional requirement)**
*FR (illustrative): "Move 10 years of bookings and every member's points history from the legacy database to the new services' databases; balances must match to the point; downtime for the switch must be under 5 minutes or zero."*

**What the interviewer is really checking**
A disciplined migration with verification and rollback.

**How I answer it**
1. **Map and transform:** document the field mapping, code translations, data-quality rules; decide what to archive rather than migrate.
2. **Start CDC first** (Debezium on the legacy DB) capturing changes from a known log position, buffering into Kafka.
3. **Backfill** historical data in batches (idempotent upserts keyed by business ids), throttled to protect legacy.
4. **Apply CDC** from the recorded position: target catches up and stays near real time.
5. **Reconcile continuously:** row counts per day/partition, checksums per record set, and **business invariants** (sum of points ledger = balance per member; booking totals per day); mismatches go to a queue and are fixed.
6. **Cutover:** switch writes for the capability to the new service (brief write-freeze or a toggle), let CDC drain, verify, then optionally **reverse CDC** (new -> legacy) for a period so rollback is possible.
7. Decommission legacy tables only after a stable period and audit sign-off.

**Trade-offs and what can go wrong**
- Dual writes from the application (writing both DBs) are unreliable; prefer CDC.
- Schema/code mapping gaps surface late; profile data early.
- Huge backfills compete with production load; run off-peak and throttle.

**How I'd monitor it**
CDC lag, backfill progress, reconciliation mismatch counts by type, invariant check results, error queue size.

**Follow-ups to expect**
- *Why reverse CDC?* -> Allows rolling back to legacy without losing writes made after cutover.
- *PII during migration?* -> Encrypt in transit and at rest, restrict access, mask in non-prod copies.
- *How do you verify points to the point?* -> Recompute balances from migrated ledger entries and compare with legacy balances per member.

**60-second answer**
"I start CDC on the legacy database first, from a recorded log position, then backfill history in idempotent, throttled batches, then apply the buffered changes so the new store stays near real time. Reconciliation runs continuously: counts, checksums, and business invariants like ledger sums equal balances per member, with mismatches queued and fixed. Cutover switches writes behind a toggle with a brief freeze, and reverse CDC keeps legacy in sync for a while so rollback loses nothing. Legacy tables go only after audit sign-off."

### Q6 [senior] Upgrade a large estate from Java 8 or 11 to Java 21/25: what breaks and how do you do it?
tags: java-upgrade, java-25, java-21, jdeps, removed-apis, strong-encapsulation, company-chase-travel

**Start here: the concepts**
- **Removed from the JDK since 8:** Java EE modules (JAXB, JAX-WS, `javax.activation`: removed in 11), Nashorn JavaScript engine (removed in 15), CORBA, the Applet API; the **Security Manager** was permanently disabled in Java 24.
- **Strong encapsulation** of JDK internals (Java 16/17): `--illegal-access` gone; libraries using `sun.misc`/internal reflection need upgrades or `--add-opens`.
- **Tools:** `jdeps --jdk-internals`, `jdeprscan`, OpenRewrite migration recipes.

**The live scenario (functional requirement)**
*FR (illustrative): "300 Java services on Java 8/11 must reach a supported LTS (21 or 25) within two quarters because of security policy, with no customer-facing incidents."*

**What the interviewer is really checking**
Practical knowledge of the breaking changes and a scalable rollout process.

**How I answer it**
1. **Inventory:** JDK version, build tool, framework versions, risky libraries per repo (scripted from build files).
2. **Scan:** `jdeps --jdk-internals` and `jdeprscan` for internal/removed APIs.
3. **Upgrade the build first:** Maven/Gradle plugins, compiler `--release`, Lombok, Mockito, ByteBuddy, ASM, Jacoco: old versions fail on new bytecode.
4. **Replace removed modules:** add Jakarta XML Binding/JAX-WS dependencies (or the old `javax` artifacts for pre-Boot-3 code), replace Nashorn (GraalJS) or remove scripting, remove Security Manager usage.
5. **Automate with OpenRewrite** (`UpgradeToJava21`/`UpgradeToJava25` recipes: build files, deprecated APIs, plugin versions), reviewed as PRs.
6. **Runtime flags:** remove obsolete GC flags (CMS removed in 14; `PermSize` long gone), switch to G1/ZGC, re-tune container memory settings; test JVM behaviour changes (default charset UTF-8 since 18, TLS defaults).
7. **Roll out in waves:** shared libraries and parent POM first; canary deploys per service; compare error rates, GC and latency.
8. **Then modernise** opportunistically: records, switch patterns, virtual threads where they help.

**Trade-offs and what can go wrong**
- Abandoned libraries with no Java 17+ support: replace them early, they're the long poles.
- Default charset change (UTF-8) can alter file/byte handling in legacy code: test file and socket I/O.
- Jumping frameworks and JDK in one step makes failures hard to isolate.

**How I'd monitor it**
Version dashboard across services, CI pass rates per wave, production error/GC/latency comparison after each canary.

**Follow-ups to expect**
- *Why 21 or 25?* -> Both LTS; 25 is the newest LTS (Sept 2025); Spring Boot 4 supports 17-25.
- *Compile with `--release 8` on JDK 21?* -> JDK 21 can still target 8 (with deprecation warnings), useful during transition for libraries consumed by old services.
- *Multi-release JARs?* -> Let a library ship version-specific classes.

**60-second answer**
"I script an inventory first, then scan with jdeps for JDK internals and removed APIs. The typical breaks are the Java EE modules removed in 11, like JAXB and JAX-WS, Nashorn, Security Manager use, strong encapsulation hitting old reflection-heavy libraries, and old build plugins, Lombok or Mockito versions. OpenRewrite's Java upgrade recipes do the mechanical changes as PRs; I upgrade shared libraries and the parent POM first, clean up obsolete JVM flags, and roll out in canary waves comparing errors, GC and latency."

### Q7 [senior] Use OpenRewrite to upgrade hundreds of repositories safely.
tags: openrewrite, automated-refactoring, recipes, lst, large-scale-change, moderne, company-chase-travel

**Start here: the concepts**
- **OpenRewrite:** an open-source auto-refactoring engine; **recipes** transform code using a **Lossless Semantic Tree** (type-aware, preserves formatting).
- Recipes for Java version upgrades, Spring Boot migrations, javax->jakarta, JUnit 4->5, logging frameworks, security fixes; custom recipes for internal APIs.
- Runs via the Maven/Gradle plugin (`rewrite:dryRun`, `rewrite:run`); **Moderne** (commercial) runs recipes across thousands of repos at once.

**The live scenario (functional requirement)**
*FR (illustrative): "Move 300 repositories from Spring Boot 2.7/Java 11 to Spring Boot 3.5/Java 21, and later Boot 4, with a small platform team, in a regulated environment requiring code review for every change."*

**What the interviewer is really checking**
How large-scale automated change works in practice, with governance.

**How I answer it**
1. **Pick or compose recipes:** e.g. `UpgradeToJava21`, Spring Boot 3.5 migration, `JavaxMigrationToJakarta`, JUnit 5 migration; plus **custom recipes** for our internal libraries (renamed packages, deprecated company APIs).
2. **Pilot** on 5 representative repos: `dryRun` produces a patch, engineers review, fix gaps, refine recipes.
3. **Scale:** CI job (or Moderne) runs the recipe across repos and opens PRs automatically; each PR runs the full pipeline.
4. **Owners review and merge** (regulatory requirement satisfied; the change is generated but reviewed).
5. **Manual remainder:** a checklist for what recipes can't do (security config semantics, behaviour changes); track per repo.
6. **Measure:** percentage of repos on target versions; recipe success rate; time to merge.

**Trade-offs and what can go wrong**
- Recipes cover the mechanical 70–90%; behaviour changes still need humans and tests.
- Weak test coverage means automated changes ship untested: add characterisation tests for critical paths first.
- Some recipes live under source-available licences; check licence terms for commercial use.

**How I'd monitor it**
Version compliance dashboard, PR merge rate and age, post-merge incident rate.

**Follow-ups to expect**
- *Why not sed/regex?* -> No type information; OpenRewrite understands types, imports and formatting.
- *Writing a custom recipe?* -> Declarative YAML composing existing recipes, or Java recipes using visitors.
- *Enterprise usage?* -> Large banks publicly report running OpenRewrite at scale to keep apps on supported versions.

**60-second answer**
"OpenRewrite applies type-aware recipes on a lossless semantic tree, so it can upgrade Java, migrate Spring Boot, move javax to jakarta and JUnit 4 to 5 while keeping formatting. I'd compose the standard recipes with custom ones for our internal libraries, pilot on a handful of repos with dry runs, then let CI or Moderne open PRs across all 300, each going through the full pipeline and reviewed by owners, which satisfies the regulated review requirement. The leftover manual work goes on a tracked checklist, and a dashboard shows version compliance."

### Q8 [senior] What breaks when moving from Spring Boot 2 to 3 and then to 4?
tags: spring-boot-3, spring-boot-4, jakarta, spring-security-6, jackson-3, migration, company-chase-travel

**Start here: the concepts**
- **Boot 3 / Framework 6:** Java 17 baseline, **`javax.*` -> `jakarta.*`** (Servlet, JPA, Validation), Spring Security 6, Hibernate 6, observability via Micrometer Observation/Tracing (Sleuth removed), trailing-slash matching off by default.
- **Boot 4 / Framework 7:** Jakarta EE 11, **Jackson 3** (new package `tools.jackson`), modular auto-configuration jars, JSpecify null-safety, built-in API versioning and resilience annotations, renamed/removed properties; upgrade from 3.5.

**The live scenario (functional requirement)**
*FR (illustrative): "The booking service runs Spring Boot 2.7 with Spring Cloud Sleuth, Springfox, a custom WebSecurityConfigurerAdapter and Hibernate 5 queries; bring it to Boot 4 with no API contract changes."*

**What the interviewer is really checking**
Concrete knowledge of the breaking points and the order of fixes.

**How I answer it**
1. **Boot 2.7 -> 3.5:**
   - OpenRewrite: jakarta migration + Boot 3 recipes.
   - Security: `WebSecurityConfigurerAdapter` (removed) -> `SecurityFilterChain` beans with lambda DSL; `authorizeRequests` -> `authorizeHttpRequests`.
   - Sleuth -> Micrometer Tracing / OpenTelemetry; Springfox (dead) -> springdoc-openapi.
   - Hibernate 6: HQL/criteria and type changes; test every custom query.
   - URL matching: trailing slash no longer matches; contract tests reveal client impact.
   - `spring-boot-properties-migrator` on the classpath temporarily reports renamed properties.
2. **Boot 3.5 -> 4.x:**
   - Jackson 3 package/API changes (custom serialisers, `ObjectMapper` customisers); Boot 4 offers deprecated Jackson 2 support as a bridge.
   - Modular starters: add specific starters where you relied on transitive auto-configs.
   - Property renames; deprecated APIs from 3.x removed.
   - Optionally adopt built-in API versioning and `@Retryable`.
3. Keep **API contracts frozen** with contract tests and OpenAPI diff throughout.

**Trade-offs and what can go wrong**
- Third-party libraries lagging on Jakarta or Jackson 3 block the upgrade; check compatibility early.
- Spring Cloud versions must match the Boot generation (release train compatibility).

**How I'd monitor it**
Contract test results, error rates after canary, startup warnings about deprecated properties.

**Follow-ups to expect**
- *Can you skip 3.x?* -> No; go via 3.5, which is the documented starting point for 4.0.
- *Spring Cloud compatibility?* -> Each Spring Cloud release train targets a specific Boot generation.
- *Biggest silent change in Boot 3?* -> Trailing-slash matching and Hibernate 6 query semantics.

**60-second answer**
"From 2.7 to 3.5 the big items are javax to jakarta, Spring Security 6, where WebSecurityConfigurerAdapter is gone so it's SecurityFilterChain beans, Sleuth replaced by Micrometer Tracing, Springfox by springdoc, Hibernate 6 query changes and no more trailing-slash matching. OpenRewrite and the properties migrator handle much of it. From 3.5 to 4 it's Jackson 3, modular starters, removed deprecations and renamed properties. Contract tests and an OpenAPI diff keep the API identical throughout, and Spring Cloud must match the Boot generation."

### Q9 [senior] Build a test safety net for a legacy migration when the old code has few tests.
tags: characterization-tests, golden-master, contract-testing, record-replay, regression, migration, company-chase-travel

**Start here: the concepts**
- **Characterisation (golden master) tests:** capture what the system *currently* does for many inputs, then assert the new system produces the same.
- **Record and replay:** capture real request/response pairs (including supplier responses) and replay them against the new code with stubs.
- **Consumer-driven contracts:** consumers' expectations verified against providers.

**The live scenario (functional requirement)**
*FR (illustrative): "The legacy cancellation-fee calculation has no unit tests and hundreds of rules accumulated over years; the Java rewrite must produce identical fees."*

**What the interviewer is really checking**
How to create confidence without pre-existing tests.

**How I answer it**
1. **Capture real cases:** sample production cancellations (anonymised): inputs (booking, fare rules, dates, supplier policy, member tier) and legacy outputs (fee, refund split points/cash).
2. **Golden master suite:** thousands of cases replayed in CI against the new service; any diff fails the build.
3. **Add synthetic edge cases:** boundary dates (time zones, daylight saving), currencies, partial cancellations, multi-room bookings.
4. **Record supplier interactions** and replay them with WireMock so tests are deterministic.
5. **Contract tests** for every consumer of the new APIs (web, mobile, servicing tools).
6. **Shadow traffic** in production (Q2) for cases the sample missed.
7. As rules are understood, convert golden cases into **readable unit tests** named after business rules, documented with the business.

**Trade-offs and what can go wrong**
- Golden masters freeze bugs too; triage diffs with the business.
- Sampled data may miss rare rules; combine with shadow traffic and rule extraction from code.
- Test data with PII must be anonymised.

**How I'd monitor it**
Golden-master pass rate, number of unexplained diffs, shadow mismatch rate, rule documentation coverage.

**Follow-ups to expect**
- *Approval testing tools?* -> ApprovalTests for Java helps manage golden files.
- *Mutation testing?* -> PIT checks that tests actually catch changes.
- *How many cases?* -> Enough to cover rule combinations seen in production; driven by distinct paths, not just volume.

**60-second answer**
"When legacy code has no tests, I capture its behaviour. I sample anonymised production cancellations with their inputs and legacy fee outputs, and replay thousands of them in CI against the new service, golden-master style, with supplier responses recorded and replayed through WireMock. I add synthetic edge cases like time zones and partial cancellations, contract tests for every consumer, and shadow traffic for anything the sample missed. As rules become clear, golden cases turn into readable, rule-named unit tests agreed with the business."

### Q10 [architect] Which design patterns would you apply in the rewritten travel platform, and where?
tags: design-patterns, strategy, state-pattern, chain-of-responsibility, builder, saga, company-chase-travel

**Start here: the concepts**
- **GoF patterns** solve object-design problems (Strategy, Adapter, Facade, State, Chain of Responsibility, Builder, Template Method, Observer, Decorator, Specification).
- **Enterprise/microservice patterns** solve distribution problems (Saga, Outbox, CQRS, Circuit Breaker, API Gateway, BFF, Strangler Fig, Anti-Corruption Layer, Idempotent Consumer).

**The live scenario (functional requirement)**
*FR (illustrative): "Design the core of a rewards travel booking platform: search across suppliers, price in points and cash with member-tier rules, book with split payment, manage booking lifecycle and cancellations."*

**What the interviewer is really checking**
That patterns are chosen for real problems, not listed.

**How I answer it**
1. **Adapter + Strategy:** one adapter per supplier behind a `SupplierClient` port; strategy selection by supplier and product (hotel, air, car).
2. **Facade:** a `TripSearchFacade` hiding fan-out, caching and merging from the API layer.
3. **Chain of Responsibility / Specification:** pricing pipeline: base price -> supplier markup -> member-tier redemption rules -> promotions -> rounding; each rule a link, configurable and testable. Eligibility rules as composable Specifications.
4. **Builder:** constructing complex itineraries/booking requests immutably.
5. **State pattern / state machine:** booking lifecycle (QUOTED -> HELD -> PAYMENT_PENDING -> CONFIRMED -> TICKETED -> CANCELLED/REFUNDED) with allowed transitions enforced in one place.
6. **Template Method:** common booking flow with supplier-specific steps.
7. **Saga + Outbox + Idempotent consumer:** split payment (points hold + card charge + supplier booking) with compensations; reliable events.
8. **Circuit Breaker + Bulkhead:** per supplier. **CQRS:** trip-history and servicing views. **BFF:** web vs mobile. **Strangler Fig + ACL:** for the migration itself.
9. **Observer/domain events:** notifications, loyalty accrual, analytics react to booking events.

**Trade-offs and what can go wrong**
- Pattern overuse (factories of factories) hurts readability; apply where variation or complexity exists.
- State machines scattered across services drift; one owner per aggregate.

**How I'd monitor it**
Pattern-related metrics surface naturally: per-supplier breaker states, saga states, pricing rule execution timings.

**Follow-ups to expect**
- *Strategy vs State?* -> Strategy chooses an algorithm from outside; State changes behaviour as the object's state changes.
- *Decorator example?* -> Wrapping a supplier client with caching, metrics and retry decorators.
- *Spring support for state machines?* -> Spring Statemachine exists; a simple enum-based transition table is often enough.

**60-second answer**
"I'd apply patterns where the domain has real variation. Suppliers sit behind one port with an adapter each, chosen as strategies. A facade hides search fan-out and merging. Pricing is a chain of responsibility, base price, markup, tier redemption rules, promotions, rounding, each rule testable, with eligibility as composable specifications. The booking lifecycle is an explicit state machine, itineraries use builders, and split payment is a saga with outbox and idempotent consumers. Circuit breakers per supplier, CQRS for trip history, and strangler fig plus an anti-corruption layer for the migration."

### Q11 [senior] Turn a stateful, session-based legacy web app into stateless Spring Boot services.
tags: stateless, session-management, redis, spring-session, sso, oauth2, company-chase-travel

**Start here: the concepts**
- **Stateful legacy:** server-side `HttpSession` holding the search results, basket and user, needing sticky sessions.
- **Stateless services:** any instance can serve any request; state lives in tokens, client, or shared stores.
- **Spring Session:** externalises `HttpSession` to Redis/JDBC transparently.

**The live scenario (functional requirement)**
*FR (illustrative): "The legacy booking flow keeps search results, the selected room and traveller details in the server session across 5 steps; the new platform must autoscale across zones and survive pod restarts mid-booking."*

**What the interviewer is really checking**
Practical techniques and security implications.

**How I answer it**
1. **Identity:** move to OIDC/OAuth2: customer signs in once (enterprise identity), the web tier uses a BFF with an HttpOnly session cookie, APIs receive tokens; no server session needed for identity.
2. **Flow state:** model the booking flow as resources: `POST /quotes` returns a **quote id** (price locked with TTL); `POST /carts/{id}/travellers`; state stored in a database/Redis keyed by id and owned by the user.
3. **Search results:** cache in Redis with a short TTL keyed by search id; re-query if expired.
4. **Transition option:** Spring Session with Redis to externalise existing sessions quickly while refactoring towards resource-based state.
5. **Security:** every id validated against the authenticated user (no IDOR); quote tokens signed/opaque; TTLs enforced.
6. Remove sticky sessions at the load balancer once stateless.

**Trade-offs and what can go wrong**
- Big sessions in Redis cost memory and latency; keep state small and structured.
- Client-side state (JWT with booking data) can be tampered or grow; keep authoritative state server-side.

**How I'd monitor it**
Flow abandonment by step, quote expiry rate, Redis memory/latency, errors after pod restarts (should be none).

**Follow-ups to expect**
- *Why not sticky sessions?* -> Uneven load, lost state on pod failure, blocks autoscaling.
- *Price lock?* -> Quote with TTL and re-validation at booking time.
- *Multi-tab behaviour?* -> Resource ids per flow allow parallel carts.

**60-second answer**
"Identity moves to OIDC with a BFF and HttpOnly cookie, so services just validate tokens. The multi-step booking flow becomes resources: a quote with a price-lock TTL, then a cart with travellers, stored in Redis or a database by id and checked against the logged-in user. Search results are cached briefly by search id. As a bridge, Spring Session with Redis externalises existing sessions while we refactor. Then sticky sessions go, any pod can serve any step, and a restart mid-booking loses nothing."

### Q12 [senior] Migrate legacy batch jobs (points accrual, settlement, supplier reconciliation) to Java.
tags: batch-processing, spring-batch, scheduling, reconciliation, idempotency, migration, company-chase-travel

**Start here: the concepts**
- **Spring Batch:** jobs -> steps -> chunk-oriented processing (read, process, write) with restartability, skip/retry policies and job metadata.
- **Schedulers:** Kubernetes CronJobs, enterprise schedulers (Control-M, Autosys), Quartz.
- **Event-driven alternative:** replace some nightly batches with continuous streaming.

**The live scenario (functional requirement)**
*FR (illustrative): "Nightly legacy jobs award points for completed stays, produce supplier settlement files, and reconcile supplier invoices with bookings; they must move to the new stack without missed or double payments."*

**What the interviewer is really checking**
Correctness (idempotency, restart) and whether to keep batch at all.

**How I answer it**
1. **Re-think each job:** points accrual on stay completion can become **event-driven** (react to `StayCompleted`), giving faster points and no nightly window. Settlement files and invoice reconciliation stay batch (partners expect files on schedule).
2. **Spring Batch** for batch jobs: chunked readers (paging/cursor JDBC), processors, writers; restart from the last committed chunk after failure; skip policies send bad records to an error table.
3. **Idempotency:** each output keyed (settlement id per supplier per period); re-running a job doesn't duplicate payments.
4. **Parallel run:** new jobs run alongside legacy for several cycles producing outputs into a comparison area; reconcile totals and line items before switching.
5. **Scheduling:** Kubernetes CronJob or the enterprise scheduler, with dependencies and SLAs; alerts on missed or late runs.
6. **Controls:** totals and record counts in file trailers, checksums, audit logs; four-eyes approval for payment files.

**Trade-offs and what can go wrong**
- Time zones and cut-off times (which day does a stay belong to?) cause subtle mismatches.
- Long jobs on shared DBs hurt online traffic; use replicas or throttle.

**How I'd monitor it**
Job success/duration vs SLA, records processed/skipped, reconciliation differences, late-file alerts.

**Follow-ups to expect**
- *Partitioning in Spring Batch?* -> Split by key ranges and process in parallel workers.
- *Exactly-once payments?* -> Idempotency keys + reconciliation with the payment system.
- *Why not keep everything batch?* -> Customers expect points quickly; events give near real time.

**60-second answer**
"First I ask which jobs should stay batch. Points accrual can become event-driven on stay completion, which is faster for members, while settlement files and invoice reconciliation stay scheduled because partners expect them. Batch jobs move to Spring Batch: chunked, restartable from the last commit, with skip policies and an error table. Every output is idempotent per supplier and period, so reruns can't double-pay. New and legacy run in parallel for several cycles with totals reconciled before switching, and late or missed runs alert."

### Q13 [architect] Plan the cutover and rollback for a migrated booking capability.
tags: cutover, rollback, canary, kill-switch, runbook, hypercare, company-chase-travel

**Start here: the concepts**
- **Cutover:** the moment authority moves from old to new.
- **Rollback plan:** a tested way back, including data written after cutover.
- **Hypercare:** a period of heightened monitoring and support after go-live.

**The live scenario (functional requirement)**
*FR (illustrative): "Move hotel booking from the legacy engine to the new Java services before the holiday season with zero lost bookings and a rollback possible within minutes."*

**What the interviewer is really checking**
Operational maturity: rehearsal, criteria, communication.

**How I answer it**
1. **Timing:** not right before peak; leave weeks of stable operation before the holiday surge, and a change freeze during it.
2. **Progressive cutover:** internal users -> 1% customers -> specific markets/brands -> 100%, using routing toggles at the gateway.
3. **Go/no-go criteria:** booking success rate, supplier error rates, latency, reconciliation results, support ticket volume, all compared with legacy baselines.
4. **Rollback:** a kill switch routes back to legacy; **reverse data sync** keeps legacy aware of bookings made in the new system (or a defined procedure to import them); rehearsed in staging and once in production at low traffic.
5. **Runbook:** step owners, timings, verification queries, communication plan (customer service, partners, leadership).
6. **Hypercare:** war room, dashboards, on-call from both legacy and new teams for 2–4 weeks.
7. **Decommission** legacy after a defined stable period.

**Trade-offs and what can go wrong**
- Rollback that has never been tested doesn't exist.
- In-flight bookings during the switch (started in legacy, completed in new) need explicit handling: drain or route by booking id.

**How I'd monitor it**
Real-time business dashboard: bookings per minute per system, failures by reason, supplier responses, reconciliation status.

**Follow-ups to expect**
- *What triggers a rollback?* -> Pre-agreed thresholds, not debate during an incident.
- *Customer communication?* -> Usually unnecessary if progressive; prepare templates anyway.
- *In-flight sessions?* -> Route by session/booking origin until completion.

**60-second answer**
"I'd schedule it well before the holiday peak and cut over progressively: internal users, 1% of customers, then markets, then everyone, by gateway routing. Go/no-go criteria are agreed in advance against legacy baselines: booking success, supplier errors, latency, reconciliation, support tickets. Rollback is a rehearsed kill switch plus reverse data sync so bookings made in the new system aren't lost. A runbook with owners and a communication plan, two to four weeks of hypercare, and legacy decommissioned only after a stable period."

### Q14 [senior] Prove the rewritten Java services perform at least as well as legacy at peak.
tags: performance-testing, capacity-planning, load-testing, jfr, baseline, peak-traffic, company-chase-travel

**Start here: the concepts**
- **Baseline:** legacy's real throughput and latency at peak (from production metrics).
- **Load test types:** load (expected peak), stress (beyond), soak (hours), spike (sudden surge).
- **Profiling:** JFR, async-profiler; **capacity model:** throughput per pod, scaling limits, downstream limits.

**The live scenario (functional requirement)**
*FR (illustrative): "Hotel search must handle a card-member promotion spike of 5× normal traffic with p95 under 2 s, at least as good as the legacy system today."*

**What the interviewer is really checking**
Rigorous, realistic performance validation.

**How I answer it**
1. **Baseline legacy** from production: peak RPS, p50/p95/p99, error rate, supplier call volumes, cache hit rate.
2. **Realistic workload model:** traffic mix (search vs details vs book), destinations distribution, cache-hit realism, think times; supplier latency simulated from recorded distributions (never load-test real suppliers without agreement).
3. **Tests:** load at normal peak, stress to 5× and beyond to find the knee, spike test (0 -> 5× in a minute: autoscaling reaction), soak for 8 hours (leaks).
4. **Profile under load:** JFR/async-profiler for CPU hotspots, allocation rates, lock contention; fix and re-test.
5. **Capacity model:** RPS per pod at target latency, pods needed for 5×, node and supplier quota limits; pre-scale for known promotions.
6. **Protection:** rate limiting, load shedding, cached fallbacks for supplier saturation.
7. Performance tests run in the pipeline for critical paths (smaller scale) to catch regressions.

**Trade-offs and what can go wrong**
- Test environments smaller than prod give misleading results; scale models carefully or test in prod-like environments.
- Load tools with coordinated omission under-report latency.
- Downstream (suppliers, DB) is often the real limit, not the Java service.

**How I'd monitor it**
Same dashboards in tests and prod: RPS, latency percentiles, errors, GC, pod count, supplier latency.

**Follow-ups to expect**
- *Tools?* -> Gatling, k6, JMeter; JFR for profiling.
- *Pre-scaling?* -> Scheduled scale-up before promotions; autoscaling alone may react too late.
- *What's a knee?* -> The load where latency rises sharply as utilisation nears saturation.

**60-second answer**
"I baseline legacy from production metrics, then build a realistic workload: the real traffic mix, realistic cache hits, and supplier latency simulated from recorded distributions, because we don't hammer real suppliers. Load, stress to 5x and past the knee, a spike test for autoscaling reaction, and an 8-hour soak for leaks, with JFR profiling under load. The result is a capacity model, RPS per pod and pods needed for 5x within supplier quotas, so we pre-scale before promotions, with load shedding and cached fallbacks as protection."

### Q15 [architect] Where can GenAI help the migration itself, and with what guardrails?
tags: genai-for-migration, code-understanding, test-generation, documentation, openrewrite, guardrails, company-chase-travel

**Start here: the concepts**
- **AI-assisted modernisation:** LLMs help read legacy code, document business rules, translate code (e.g. C# or old Java to modern Java), generate tests, and draft migration PRs.
- **Deterministic tools** (OpenRewrite, compilers, tests) remain the source of correctness.

**The live scenario (functional requirement)**
*FR (illustrative): "Speed up the rewrite of legacy services whose original authors have left; regulators and security require that code and customer data never go to unapproved AI services."*

**What the interviewer is really checking**
Pragmatic, safe use of GenAI in engineering, a natural bridge between the Java and Gen AI parts of this profile.

**How I answer it**
1. **Approved tooling only:** enterprise-approved coding assistants or **internally hosted models**; no customer data or secrets in prompts; repository access controls respected.
2. **Code comprehension:** RAG over the legacy codebase (code chunked by class/method, plus docs, tickets, runbooks) so engineers can ask "where is the cancellation fee calculated and which rules apply?", answers citing files and lines.
3. **Business-rule extraction:** LLM drafts rule descriptions from code; domain experts validate; validated rules become characterisation tests (Q9).
4. **Test generation:** LLM proposes unit tests for legacy code before migration; engineers review; mutation testing checks their value.
5. **Translation assistance:** for .NET -> Java or old Java idioms, AI drafts code, but compilers, tests, golden masters and shadow traffic decide correctness.
6. **Combine with OpenRewrite:** deterministic recipes for mechanical upgrades; AI for the long tail, then turned into new recipes when patterns repeat.
7. **Measure:** cycle time per migrated service, defect rate of AI-assisted vs manual changes.

**Trade-offs and what can go wrong**
- Plausible but wrong code or rule descriptions; human review and tests are mandatory.
- IP and data leakage through unapproved tools.
- Over-reliance erodes understanding; engineers must still own the domain.

**How I'd monitor it**
AI-assisted PR share, review rejection rate, post-merge defects, time saved per migration.

**Follow-ups to expect**
- *Can AI do the whole rewrite?* -> It accelerates comprehension and drafting; correctness comes from tests and parity checks.
- *How to protect code?* -> Approved, contractually covered tools or self-hosted models; audit usage.
- *Agents for upgrades?* -> Agentic tools can run builds and tests in loops, still gated by review.

**60-second answer**
"GenAI accelerates comprehension and drafting, while correctness still comes from tests. Using only approved or internally hosted models, I'd index the legacy codebase, docs and tickets for RAG so engineers can ask where a rule lives and get answers citing files. The model drafts business-rule descriptions and unit tests that experts and engineers validate, and drafts translations from old code. OpenRewrite handles the mechanical upgrades, and compilers, golden masters and shadow traffic decide what's correct. No customer data or secrets go into prompts."
