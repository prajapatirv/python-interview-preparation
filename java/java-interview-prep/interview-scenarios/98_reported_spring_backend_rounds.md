---
id: reported-spring-backend-rounds
title: Reported rounds, Spring backend (Virtusa, Capgemini): coding, JUnit, JPA keys, security, rate limiting, WebSocket, code quality
stack: java
skill: spring-boot
---
Part of the **reported interview questions** pack (hub: `../reported-interviews/README.md`, which maps every reported
question to its answer). This bank holds only the gaps; questions the repo already answers are linked from the hub.

Code in Q1-Q3, Q9 and Q11 ran and passed in `examples/21_coding_interview/08_reported_rounds_coding_and_internals.java`.

### Q1 [mid] Find the least number of coins to reach a target, where each coin can be used many times.
tags: coin-change, dynamic-programming, greedy, bottom-up, coding, virtusa, reported-rounds, topic-coding

**Start here: the concepts**
- **Greedy** always takes the largest coin that fits. It is fast, and it is wrong for some coin sets.
- **Dynamic programming** solves each smaller amount once and reuses the answer.

**The live scenario (functional requirement)**
*FR: "A vending machine must dispense change using the fewest coins."* With coins 1, 3 and 4 and a target of 6, greedy gives 4+1+1 (3 coins). The best is 3+3 (2 coins).

**What the interviewer is really checking**
Whether you know greedy fails, and can build the recurrence out loud.

**How I answer it** (120-second answer, point by point)
1. **Say why greedy fails**, with the counter-example above. I ran both.
2. **Recurrence:** the best answer for an amount is 1 + the best for `amount - coin`, over every coin that fits. Base case: `best[0] = 0`.
3. **Build upward:**

```java
int unreachable = target + 1;
int[] best = new int[target + 1];
Arrays.fill(best, unreachable);
best[0] = 0;
for (int amount = 1; amount <= target; amount++)
    for (int coin : coins)
        if (coin <= amount) best[amount] = Math.min(best[amount], best[amount - coin] + 1);
return best[target] == unreachable ? -1 : best[target];
```

4. **Why `target + 1` and not `Integer.MAX_VALUE`:** adding 1 to `MAX_VALUE` overflows to a negative number, which `min` then picks. That's a real bug.
5. **Complexity:** O(target x coins) time and O(target) space.
6. **Test cases:** coins 1,2,5 target 11 gives 3. Target 0 gives 0. Coin 2 target 3 gives -1.

**Trade-offs and what can go wrong**
- Greedy is correct for standard currency systems like 1, 2, 5, 10, but you'd have to prove that for your coin set.
- A huge target makes the table big. That's the limit of this approach.

**Follow-ups to expect**
- *Which coins were used?* -> Keep a `lastCoin[amount]` array and walk back.
- *Number of ways instead?* -> A different DP: loop coins on the outside and add counts.
- *Top-down?* -> Recursion with a memo table gives the same complexity, but recursion depth grows with the target.

**60-second answer**
"Greedy doesn't work: for coins 1, 3, 4 and target 6, it uses three coins when two is possible. So I use dynamic programming. best[amount] is one plus the minimum of best[amount minus coin] for every coin that fits, starting from best[0] equals 0. I fill it upward, using target plus one as 'unreachable', since MAX_VALUE would overflow, and return minus one if it's still unreachable. That's O(target times coins) time and O(target) space."

### Q2 [mid] Find a pair of numbers in an array whose sum is nearest to a given target.
tags: two-pointers, closest-sum, sorting, overflow, coding, virtusa, reported-rounds, topic-coding

**Start here: the concepts**
- After sorting, two pointers can move inward: the sum tells you which pointer to move.

**The live scenario (functional requirement)**
*FR: "Pick two items whose total is as close to the gift budget as possible."* For `[10, 22, 28, 29, 30, 40]` and budget 54, the answer is 22 + 30 = 52 (gap 2).

**What the interviewer is really checking**
Going from O(n squared) to O(n log n), and clarifying what "nearest" means.

**How I answer it** (120-second answer, point by point)
1. **Clarify:** can the same element be used twice? What if two pairs tie? I assume no, and any is acceptable.
2. **Brute force** checks all pairs: O(n squared).
3. **Better:** sort, then use two pointers:

```java
int[] a = input.clone(); Arrays.sort(a);
int lo = 0, hi = a.length - 1, bestLo = 0, bestHi = hi;
long bestGap = Long.MAX_VALUE;
while (lo < hi) {
    long sum = (long) a[lo] + a[hi];
    long gap = Math.abs(sum - target);
    if (gap < bestGap) { bestGap = gap; bestLo = lo; bestHi = hi; }
    if (sum == target) break;
    if (sum < target) lo++; else hi--;
}
```

4. **Why it's correct:** if the sum is too small, pairing `a[lo]` with anything smaller than `a[hi]` is even further below target, so `lo` can be dropped. The same holds in reverse for `hi`.
5. **Details:** `long` because two large ints overflow. `clone()` so that we don't reorder the caller's array. Fewer than two elements throws.
6. **Complexity:** O(n log n) for the sort and O(n) for the scan.

**Trade-offs and what can go wrong**
- A `HashSet` solves exact two-sum in O(n), but it can't find the *nearest* sum.
- If indices are needed, sort pairs of value and original index.

**Follow-ups to expect**
- *Three numbers?* -> Fix one, and run two pointers on the rest: O(n squared).
- *Already sorted?* -> Skip the sort, so O(n).

**60-second answer**
"I'd sort a copy and use two pointers from both ends. At each step I compute the sum and record it if its distance to the target is the best so far. If the sum is too small, I move the left pointer up; too big, the right pointer down; exact, I stop. Moving a pointer is safe because the discarded element can't do better. That's O(n log n) overall. I use long for the sum to avoid overflow, and a HashSet wouldn't help because it only finds exact matches."

### Q3 [mid] Write a Stream to count employees who joined in each month, and to list them in monthly order. How do you extract the month from a date?
tags: streams, groupingby, yearmonth, localdate, month, treemap, coding, virtusa, reported-rounds, topic-coding

**Start here: the concepts**
- `LocalDate.getMonth()` returns the `Month` enum, whose natural order is calendar order. `getMonthValue()` returns 1-12.
- `YearMonth.from(date)` keeps the year, which you usually need.

**The live scenario (functional requirement)**
*FR: "Joiners report by month."* Hires from March 2024 and January 2023 must not be merged under the wrong month.

**What the interviewer is really checking**
Spotting that grouping by month name merges different years, and getting a sorted result.

**How I answer it** (120-second answer, point by point)
1. **Extract the month:** `date.getMonth()` gives `MARCH`; `date.getMonthValue()` gives 3. With the old `Date` class, convert to `LocalDate` first. `SimpleDateFormat` isn't thread-safe.
2. **Count per month:**

```java
hires.stream().collect(groupingBy(h -> YearMonth.from(h.joined()), TreeMap::new, counting()));
// {2023-01=1, 2024-01=1, 2024-03=2}
```

3. **Employees per month, in order:**

```java
hires.stream().collect(groupingBy(h -> YearMonth.from(h.joined()), TreeMap::new,
                       mapping(Hire::name, toList())));
// {2023-01=[B], 2024-01=[D], 2024-03=[A, C]}
```

4. **Why `TreeMap::new`:** the plain form returns a `HashMap` with no useful order. `Month` and `YearMonth` are both `Comparable`, so a `TreeMap` sorts them correctly, and strings like "February" would sort alphabetically, which is wrong.
5. **Trap:** grouping by `getMonth()` alone merges January 2023 with January 2024. I ran both. Ask which they want.

**Trade-offs and what can go wrong**
- A month with no hires won't appear. If the report needs zeros, iterate over the range of `YearMonth`s and use `getOrDefault`.
- Time zones: an instant near midnight may fall in another month, so convert to the business zone before taking the date.

**Follow-ups to expect**
- *In SQL?* -> `GROUP BY date_trunc('month', joined)`, in Postgres.

**60-second answer**
"LocalDate's getMonth gives the Month enum, and getMonthValue gives one to twelve. I group with groupingBy on YearMonth.from the date, with a TreeMap factory so the result is in calendar order, and counting for a count or mapping to a list for names. I use YearMonth because grouping by month alone merges the same month from different years. Month names as strings would sort alphabetically, so I avoid those. If the report needs zero rows, I fill in the empty months."

### Q4 [fresher] Write a Controller to register an employee.
tags: rest-controller, validation, requestbody, responseentity, dto, 201-created, spring-mvc, virtusa, reported-rounds

**Start here: the concepts**
- A controller does HTTP only: it takes a validated DTO, calls a service, and returns a status. Business rules live in the service.

**The live scenario (functional requirement)**
*FR: "POST /employees registers an employee. Duplicate emails are rejected."*

**What the interviewer is really checking**
Layering, validation, the correct status code, and not exposing the entity.

**How I answer it** (120-second answer, point by point)

```java
public record RegisterEmployeeRequest(
        @NotBlank String name, @Email @NotBlank String email, @NotNull Long departmentId) {}

@RestController
@RequestMapping("/employees")
class EmployeeController {
    private final EmployeeService service;
    EmployeeController(EmployeeService service) { this.service = service; }

    @PostMapping
    ResponseEntity<EmployeeResponse> register(@Valid @RequestBody RegisterEmployeeRequest request) {
        EmployeeResponse created = service.register(request);
        return ResponseEntity.created(URI.create("/employees/" + created.id())).body(created);
    }
}
```

1. **DTO, not entity:** a request DTO stops mass assignment, such as a client setting `salary`. The response DTO hides internal fields.
2. **`@Valid`:** a bad body gets `MethodArgumentNotValidException`, mapped to 400 in one `@RestControllerAdvice` (Q12).
3. **201 with `Location`:** correct for creation, rather than 200.
4. **Constructor injection:** makes the dependency explicit and testable.
5. **Duplicate email:** `service.register` throws a domain exception mapped to 409. Back it with a **unique constraint**, because a check-then-insert races between two requests. Catch the violation.

**Trade-offs and what can go wrong**
- `@Transactional` belongs on the service, not the controller.
- Passwords, if any, are hashed in the service and never logged or returned.

**Follow-ups to expect**
- *How do you test it?* -> `@WebMvcTest` with a mocked service for HTTP behaviour: 201, 400, 409.
- *Client retries a timed-out POST?* -> An idempotency key, or the unique email makes it safe.

**60-second answer**
"A RestController with PostMapping taking a validated request DTO with @Valid and @RequestBody. It calls the service and returns 201 Created with a Location header and a response DTO. I never expose the entity, to avoid mass assignment. Validation errors become 400 in a RestControllerAdvice, and a duplicate email becomes 409, backed by a database unique constraint because a check-then-insert would race. Business logic and @Transactional live in the service."

### Q5 [mid] How do you write JUnit tests for void methods?
tags: junit, mockito, void-methods, verify, argumentcaptor, dothrow, testing, virtusa, reported-rounds, topic-testing

**Start here: the concepts**
- A void method returns nothing, so you test its **effects**: a changed state, a collaborator call, or an exception.

**The live scenario (functional requirement)**
*FR: "`notify(order)` sends an email if the order is paid, and does nothing otherwise."*

**What the interviewer is really checking**
That you know the three kinds of effect, and Mockito's void syntax.

**How I answer it** (120-second answer, point by point)

```java
@ExtendWith(MockitoExtension.class)
class NotificationServiceTest {
    @Mock EmailClient email;
    @InjectMocks NotificationService service;

    @Test void sendsEmailForPaidOrder() {
        service.notify(paidOrder("a@x.com"));
        ArgumentCaptor<Email> sent = ArgumentCaptor.forClass(Email.class);
        verify(email).send(sent.capture());
        assertEquals("a@x.com", sent.getValue().to());
    }
    @Test void doesNothingForUnpaidOrder() {
        service.notify(unpaidOrder());
        verifyNoInteractions(email);
    }
    @Test void wrapsSendFailure() {
        doThrow(new SmtpException()).when(email).send(any());
        assertThrows(NotificationFailed.class, () -> service.notify(paidOrder("a@x.com")));
    }
}
```

1. **State change:** assert on the object or repository afterwards.
2. **Interaction:** `verify(mock).method(args)`, and `ArgumentCaptor` to inspect what was passed.
3. **Exception:** `assertThrows`.
4. **Stubbing a void method:** `when(...)` doesn't compile on void, so use `doThrow(...).when(mock).send(any())`, and `doNothing()`, `doAnswer()`.
5. **The negative case matters:** `verifyNoInteractions`, or `verify(mock, never())`.

**Trade-offs and what can go wrong**
- Over-verifying internals makes tests break on refactors. Verify the external effect, such as an email sent, not every internal call.
- If a void method is hard to test, that often signals hidden dependencies. Injecting them fixes both.

**Follow-ups to expect**
- *A void method with a real side effect?* -> Testcontainers or an embedded server for an integration test.

**60-second answer**
"A void method returns nothing, so I test its effects. For state, I assert on the object afterwards. For a collaborator, I use Mockito verify, with an ArgumentCaptor to check what was passed. For failure, assertThrows. Since when doesn't compile on a void method, I stub with doThrow().when(mock).send(any()). I also test the negative case using verifyNoInteractions. And I verify external effects rather than every internal call, or the tests break on each refactor."

### Q6 [mid] How do you write JUnit tests for static methods?
tags: junit, mockito, mockstatic, static-methods, clock, testability, powermock, testing, virtusa, reported-rounds, topic-testing

**Start here: the concepts**
- A **pure** static method has no outside dependency, so just call it and assert.
- A static method that touches the outside world, like `LocalDate.now()`, is the real problem.

**The live scenario (functional requirement)**
*FR: "An offer expires at midnight."* The code calls `LocalDate.now()` directly, so the test passes today and fails tomorrow.

**What the interviewer is really checking**
That you know `mockStatic`, and that you'd prefer a design that doesn't need it.

**How I answer it** (120-second answer, point by point)
1. **Pure static:** `assertEquals(5, MathUtils.add(2, 3));` no mocking at all.
2. **Mockito's `mockStatic`** (standard since Mockito 5, using the inline mock maker), with try-with-resources so the mock is thread-scoped and removed at the end:

```java
try (MockedStatic<LegacyIds> ids = mockStatic(LegacyIds.class)) {
    ids.when(LegacyIds::next).thenReturn("id-1");
    assertEquals("id-1", service.create().id());
}
```

3. **Better, inject the dependency:** for time, take a `java.time.Clock`:

```java
class OfferService {
    private final Clock clock;
    OfferService(Clock clock) { this.clock = clock; }
    boolean expired(Offer o) { return LocalDate.now(clock).isAfter(o.expiry()); }
}
// Test: new OfferService(Clock.fixed(Instant.parse("2026-01-01T00:00:00Z"), ZoneOffset.UTC))
```

4. **My rule:** `mockStatic` is for legacy or third-party code I can't change. For my own code, a need to mock statics means a missing dependency.
5. **PowerMock:** old, and doesn't keep up with modern Java and JUnit 5. Mention it only as what `mockStatic` replaced.

**Trade-offs and what can go wrong**
- Without try-with-resources, a static mock leaks into other tests on the thread.
- A static mock only applies on the thread that created it, so it doesn't reach async code.

**Follow-ups to expect**
- *Mock a private or final method?* -> Final works with the inline mock maker. Private: test through the public method.

**60-second answer**
"If the static method is pure, I just call it and assert. If it touches the outside world, Mockito's mockStatic works, inside try-with-resources so it's removed afterwards. But I treat that as a last resort for legacy code. For my own code I'd inject the dependency, so for time, I pass a java.time.Clock and use Clock.fixed in tests. That's simpler and gives a better design. PowerMock is what people used before, and I wouldn't start with it today."

### Q7 [mid] What is a composite key in JPA? What are @Embedded and @Embeddable?
tags: jpa, composite-key, embeddedid, embeddable, embedded, idclass, equals-hashcode, virtusa, reported-rounds

**Start here: the concepts**
- A **composite key** is a primary key made of more than one column.
- `@Embeddable` marks a class whose fields are stored in the owner's table.
- `@Embedded` uses such a class as a field. `@EmbeddedId` uses it as the primary key.

**The live scenario (functional requirement)**
*FR: "A student can enrol in a course once."* The natural key of `enrollment` is `(student_id, course_id)`. Separately, `Address` fields are reused on several entities without needing their own table.

**What the interviewer is really checking**
The two uses of embedding, and the rules for key classes.

**How I answer it** (120-second answer, point by point)

```java
@Embeddable
public record EnrollmentId(Long studentId, Long courseId) implements Serializable {}

@Entity
class Enrollment {
    @EmbeddedId EnrollmentId id;
    @MapsId("studentId") @ManyToOne(fetch = FetchType.LAZY) Student student;
    @MapsId("courseId")  @ManyToOne(fetch = FetchType.LAZY) Course course;
    LocalDate enrolledOn;
}

@Embeddable record Address(String city, String pincode) {}
@Entity class Customer { @Id Long id; @Embedded Address address; }
```

1. **`@Embedded` for a value object:** `Address` has no identity and no table of its own. Its columns sit in `customer`. It groups related fields and reuses them.
2. **Rules for a key class:** it must be `Serializable`, with correct `equals` and `hashCode`, because Hibernate's persistence context uses the id to find objects. A record provides those. Support for records as embeddables came with Hibernate 6.
3. **`@EmbeddedId` vs `@IdClass`:** `@EmbeddedId` groups the key in one object, and `@IdClass` repeats the fields on the entity. I prefer `@EmbeddedId`.
4. **`@MapsId`:** ties the relationship to the key column, so it isn't mapped twice.
5. **Same column names twice?** Use `@AttributeOverride`, such as a home and a work address.

**Trade-offs and what can go wrong**
- Composite keys are awkward in URLs and for child foreign keys. Many teams use a surrogate `id` and add a **unique constraint** on the natural pair. Both are valid, so say which you'd use and why.
- With a client-assigned id, `save()` does a `merge` with an extra `SELECT`, because Spring Data can't tell if it's new. Implement `Persistable` to avoid that.

**Follow-ups to expect**
- *Can `@Embedded` be null?* -> If all its columns are null, Hibernate gives you null by default.

**60-second answer**
"A composite key is a primary key of several columns, like student and course on an enrollment. @Embeddable marks a class stored inside its owner's table. Used with @Embedded it's a value object like Address, with no table of its own. Used with @EmbeddedId it's the primary key, and it must be Serializable with correct equals and hashCode, since Hibernate uses those to identify entities. I add @MapsId for the relationships. In practice, I often use a surrogate key plus a unique constraint, since composite keys make URLs and child tables awkward."

### Q8 [fresher] What is @ComponentScan, and how does it relate to @SpringBootApplication?
tags: componentscan, springbootapplication, stereotype, base-package, beans, capgemini, reported-rounds

**Start here: the concepts**
- `@ComponentScan` tells Spring where to look for classes marked `@Component`, `@Service`, `@Repository`, `@Controller` and `@Configuration`.
- `@SpringBootApplication` combines `@Configuration`, `@EnableAutoConfiguration` and `@ComponentScan`.

**The live scenario (functional requirement)**
A new `PaymentService` in `com.acme.payments` fails with `NoSuchBeanDefinitionException`. The main class is in `com.acme.app`, so the new package is never scanned.

**What the interviewer is really checking**
The default scan root, because that causes the real-world bug.

**How I answer it** (120-second answer, point by point)
1. **Default:** scans the package of the annotated class, **and everything below it**.
2. **So put the main class at the root package**, such as `com.acme`, above all the others.
3. **Options:** `@ComponentScan(basePackages = "com.acme.payments")`, or the type-safe `basePackageClasses = PaymentMarker.class`, plus `includeFilters` and `excludeFilters`.
4. **Careful:** declaring your own `@ComponentScan` *replaces* the default base package, unless you include it. Also, a broad scan on `com.acme` in a shared library pulls in everything.
5. **Auto-configuration isn't scanned:** those classes come from `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`. A library should use that, instead of relying on the consumer's scan.
6. **Performance:** broad scanning adds startup time on a large classpath.

**Trade-offs and what can go wrong**
- For JPA, `@EntityScan` and `@EnableJpaRepositories` have similar package rules, and a package outside the root needs them too.

**Follow-ups to expect**
- *Two beans with the same name from different packages?* -> `ConflictingBeanDefinitionException`. Name them explicitly.
- *How do you test a slice?* -> `@WebMvcTest` limits what gets scanned.

**60-second answer**
"@ComponentScan tells Spring which packages to search for stereotype-annotated classes. @SpringBootApplication includes it, and by default scans the main class's package and everything below. So the main class goes in the root package, and a class in a sibling package gives NoSuchBeanDefinition, which is the most common bug. You can set basePackages, but declaring it replaces the default. Auto-configuration isn't found by scanning, but through the AutoConfiguration.imports file."

### Q9 [mid] Implement an immutable class.
tags: immutable, final, defensive-copy, record, list-copyof, thread-safety, virtusa, reported-rounds, topic-java-core

**Start here: the concepts**
- **Immutable** means the object's observable state can't change after construction, so it's safe to share between threads with no locks.

**The live scenario (functional requirement)**
*FR: "A `Money` object is shared by pricing threads."* If someone changes it, or a list inside it, a price changes under another thread.

**What the interviewer is really checking**
Defensive copying. Most candidates miss the mutable field.

**How I answer it** (120-second answer, point by point)

```java
final class Money {                                  // 1. can't be subclassed
    private final long paise;                         // 2. private final fields
    private final List<String> tags;
    Money(long paise, List<String> tags) {
        this.paise = paise;
        this.tags = List.copyOf(tags);                // 3. defensive copy going in
    }
    long paise() { return paise; }                    // 4. no setters
    List<String> tags() { return tags; }              // 5. already unmodifiable going out
    Money plus(long more) { return new Money(paise + more, tags); }  // 6. change means a new object
}
```

I tested the two important cases: changing the caller's list afterwards doesn't affect the object, and `tags().add(...)` throws `UnsupportedOperationException`.

Further points:
1. `List.copyOf` is itself immutable, so the getter can return it. With a `Date` or an array, copy in **both** directions.
2. **Records** give you final fields and no setters, but **not** deep immutability. A `record R(List<String> xs)` still exposes a mutable list unless the compact constructor copies it.
3. **Why bother:** thread safety with no locks, safe as map keys, and final fields get safe publication guarantees from the Java Memory Model.

**Trade-offs and what can go wrong**
- `Collections.unmodifiableList(list)` is a *view*: changes to the original still show through. `List.copyOf` isn't.
- Many changes in a loop create many objects. The JVM handles short-lived objects well, and if not, use a builder.

**Follow-ups to expect**
- *Why final class?* -> A subclass could add mutable state or override a getter.
- *Bank 13 Q1, bank 70 Q2* go further on this.

**60-second answer**
"Final class, private final fields, no setters, and any change returns a new object. The part people miss is mutable fields: I copy a list on the way in with List.copyOf, so later changes to the caller's list can't reach inside, and what I return can't be modified. For a Date or array I copy in both directions. Records make this shorter, but they aren't deeply immutable, so their list fields still need copying. The benefit is thread safety with no locks."

### Q10 [mid] Explain OAuth and JWT. Who creates the JWT?
tags: oauth2, jwt, authorization-server, resource-server, access-token, jwks, security, virtusa, reported-rounds

**Start here: the concepts**
- **OAuth 2.0** is a protocol for delegated **authorization**: an app gets limited access without seeing the password. **OIDC** adds login on top.
- **JWT** is a **token format**: signed JSON with three parts, `header.payload.signature`. Base64-encoded, and **not encrypted**.
- They are separate things. OAuth doesn't require JWT, and JWT doesn't require OAuth.

**The live scenario (functional requirement)**
*FR: "A partner app reads a customer's statements with their consent, and each microservice verifies the caller without calling a central service on every request."*

**What the interviewer is really checking**
"Who creates the JWT?" is the trap. The answer is the **authorization server**, not your API.

**How I answer it** (120-second answer, point by point)
1. **Roles:** resource owner (user), client (app), authorization server (issues tokens, like Keycloak, Okta, Cognito), resource server (your API).
2. **Flow for a web or mobile app:** Authorization Code with PKCE. The user logs in at the auth server, the client gets a code, and swaps it for tokens.
3. **Service to service:** Client Credentials.
4. **Who creates the JWT:** the **authorization server** signs it with its **private key**. Your API never creates it. It only **verifies** it using the public key from the JWKS endpoint.
5. **What the API checks:** signature, `exp`, `iss`, `aud`, and then scopes. In Spring: `spring.security.oauth2.resourceserver.jwt.issuer-uri` with `spring-boot-starter-oauth2-resource-server`.
6. **Why JWT suits microservices:** verified locally, with no call to a central store per request.

**Trade-offs and what can go wrong**
- **Revocation:** a JWT stays valid until `exp`. So keep access tokens short (5 to 15 minutes), with refresh tokens, and a deny-list when it must be immediate.
- Never put secrets or personal data in the payload, because anyone can read it.
- Pin the allowed algorithms. Accepting `alg: none`, or confusing HS256 with RS256, are classic attacks.
- In a simple monolith with a homegrown login, your own service may sign tokens itself. Say that it's possible, and that it then holds the key.

**Follow-ups to expect**
- *Authentication vs authorization?* -> Who you are, and what you may do.
- *Where does a browser store it?* -> Prefer an HttpOnly cookie or a BFF, rather than `localStorage`, due to XSS.

**60-second answer**
"OAuth 2 is a protocol for delegated authorization, and JWT is a token format: signed JSON that's encoded rather than encrypted. They're independent. The JWT is created by the authorization server, like Keycloak or Okta, which signs it with its private key. My API never creates it; it only verifies the signature with the public key from the JWKS endpoint, then checks expiry, issuer, audience and scopes. That local verification is why JWT suits microservices. The catch is revocation, so I keep access tokens short-lived, with refresh tokens."

### Q11 [mid] Explain the Strategy and Factory patterns, with a real use.
tags: strategy-pattern, factory-pattern, open-closed, enum, spring-injection, design-patterns, virtusa, reported-rounds, topic-architecture

**Start here: the concepts**
- **Strategy:** the algorithm varies, so put each behind one interface and choose at run time.
- **Factory:** object creation or selection varies, so put that decision in one place.
- They usually appear together: a factory **selects** the strategy.

**The live scenario (functional requirement)**
*FR: "Fees differ for UPI, card and wire, and new channels will be added."* A growing `switch` in the payment service is touched for each new channel, and bugs creep in.

**What the interviewer is really checking**
That you can use them, including how Spring does it for you.

**How I answer it** (120-second answer, point by point)
1. **Compact form, as I ran it:**

```java
interface Fee { long on(long amount); }
enum Channel {
    UPI(a -> 0), CARD(a -> a * 2 / 100), WIRE(a -> 2_500);
    final Fee fee;
    Channel(Fee fee) { this.fee = fee; }
}
static Fee feeFor(String channel) { return Channel.valueOf(channel.toUpperCase()).fee; }
```

2. **The Spring way,** when a strategy needs dependencies. Make each a bean, and Spring injects them all:

```java
@Service class FeeFactory {
    private final Map<String, FeeStrategy> byType;
    FeeFactory(List<FeeStrategy> all) {
        byType = all.stream().collect(toMap(FeeStrategy::type, identity()));
    }
    FeeStrategy of(String type) {
        return Optional.ofNullable(byType.get(type))
                       .orElseThrow(() -> new UnsupportedChannel(type));
    }
}
```

3. **Why it's better:** adding a channel means adding one class, and no existing code changes (open/closed principle). Each strategy is unit-tested alone.
4. **Which one is which?** Strategy is about *behaviour*, Factory about *choosing or creating*.

**Trade-offs and what can go wrong**
- Don't apply this to a two-branch `if` that will never grow. That's over-engineering.
- `valueOf` throws `IllegalArgumentException` on unknown input, so map that to a 400, not a 500.

**Follow-ups to expect**
- *Where's Strategy in the JDK?* -> `Comparator`. Factory: `List.of`, `Calendar.getInstance`.

**60-second answer**
"Strategy puts varying behaviour behind one interface, and Factory puts the choosing in one place, so they usually work together. For fees by payment channel, each channel is a strategy, and a factory picks one by type. In Spring, I inject a List of all strategies and build a map in the factory's constructor, so a new channel is just one new bean with no change to existing code. I wouldn't use it for a simple if that'll never grow."

### Q12 [fresher] @RestControllerAdvice vs @ExceptionHandler.
tags: restcontrolleradvice, exceptionhandler, error-handling, problemdetail, spring-mvc, virtusa, reported-rounds

**Start here: the concepts**
- `@ExceptionHandler` marks a **method** that handles an exception type.
- `@RestControllerAdvice` marks a **class** whose handlers apply **globally** across controllers.
- So they are not alternatives: you normally use them together.

**The live scenario (functional requirement)**
*FR: "All 40 APIs must return the same error format."* Handlers copied into each controller have drifted, and clients must parse five shapes.

**What the interviewer is really checking**
That they aren't alternatives, plus scope and precedence.

**How I answer it** (120-second answer, point by point)

```java
@RestControllerAdvice
class ApiErrors {
    @ExceptionHandler(EmployeeNotFound.class)
    ProblemDetail notFound(EmployeeNotFound e) {
        return ProblemDetail.forStatusAndDetail(HttpStatus.NOT_FOUND, e.getMessage());
    }
}
```

1. **`@ExceptionHandler` in a controller:** applies to that controller only, and wins over a global handler.
2. **In a `@RestControllerAdvice` class:** applies to all, or a subset with `basePackages` or `assignableTypes`.
3. **`@RestControllerAdvice` = `@ControllerAdvice` + `@ResponseBody`.**
4. **Most specific exception type wins.** Keep a catch-all for `Exception` that returns 500 with a generic message.
5. **`ProblemDetail`** implements RFC 9457 and is built into Spring 6+.

**Trade-offs and what can go wrong**
- It doesn't catch errors from **filters** (such as Spring Security), because those happen before the controller layer.
- Don't return stack traces or SQL errors to clients. Log them with a correlation id.

**Follow-ups to expect**
- *Full design of error handling?* -> Bank 72 Q4 and bank 99 Q2.

**60-second answer**
"They aren't alternatives. @ExceptionHandler marks a method that handles an exception, and @RestControllerAdvice marks a class that makes those handlers global. A handler in a controller applies only there and takes priority. So I use one advice class for a consistent ProblemDetail format, with specific handlers and a generic 500 catch-all. It doesn't catch filter errors like Spring Security's. And I never leak stack traces to the client."

### Q13 [senior] Explain a rate limiter. What parameters matter? If there is no user id, what can be the key?
tags: rate-limiter, token-bucket, sliding-window, redis, key-design, api-key, ip-address, 429, virtusa, reported-rounds, topic-architecture

**Start here: the concepts**
- A **rate limiter** caps how many requests a client may make per time window, protecting capacity and fairness.
- **Token bucket** allows controlled bursts. **Sliding window** is smoother. **Fixed window** is simplest, and it allows a double burst at the window edge.

**The live scenario (functional requirement)**
*FR: "A public, unauthenticated search API is being hammered by scrapers."* There's no user id to use. Limiting by IP alone blocks a whole office behind one NAT.

**What the interviewer is really checking**
The key question. It shows whether you've thought beyond the textbook algorithm.

**How I answer it** (120-second answer, point by point)

Parameters to decide:

| Parameter | Decision |
|---|---|
| Key | Who is being limited (table below) |
| Limit and window | e.g. 100 per minute, from real traffic percentiles |
| Burst | Bucket capacity vs refill rate |
| Algorithm | Token bucket by default |
| Scope | Per endpoint and global; expensive endpoints get tighter limits |
| Where | Gateway for coarse limits, service for business ones |
| Storage | Redis, for a limit shared across pods |
| When the limiter fails | Fail open (availability) or closed (protection): decide per API |
| Response | `429`, `Retry-After`, and `RateLimit-*` headers |

Keys when there's no user id:

| Key | Good for | Weakness |
|---|---|---|
| API key or client id | Partners and apps | Must exist; can be shared |
| JWT `client_id` | Service to service | Needs a token |
| IP address | Anonymous traffic | NAT shares IPs; attackers rotate them. Use the real client IP from a trusted proxy, not a raw `X-Forwarded-For` |
| IPv6 /64 prefix | IPv6 clients | A client controls a whole range, so limit the prefix |
| Session or device cookie | Browsers | Can be cleared |
| TLS or browser fingerprint | Bot defence | Approximate and can have false positives |
| Tenant or organisation | B2B | Needs tenant identification |
| Business key (phone, email for OTP) | Login and OTP abuse | The most effective for that flow |

I layer them: IP with a generous limit, and a tighter limit on an API key or business key.

**Trade-offs and what can go wrong**
- A Redis check adds about a millisecond to each request, and makes Redis a dependency.
- Check-and-increment must be **atomic**, using a Lua script, or concurrent requests slip through.
- `X-Forwarded-For` is client-controlled unless your proxy overwrites it, so spoofed IPs can bypass limits.

**Follow-ups to expect**
- *Implementation?* -> Bank 86 Q6 (distributed design), bank 70 Q15 (in Java), and bank 50 Q30.
- *Distributed in Redis?* -> A Lua script storing tokens and last-refill time per key.

**60-second answer**
"A rate limiter caps requests per client over time. I decide the key, the limit and burst, the algorithm (usually token bucket), where it runs, what happens if the store fails, and the response: 429 with Retry-After. With no user id, I'd use an API key or client id if one exists. Otherwise the IP from a trusted proxy, knowing NAT shares it and attackers rotate it, so a /64 prefix for IPv6, plus a session cookie or fingerprint. For OTP abuse, the phone number is the best key. I usually layer a generous IP limit with tighter limits on stronger keys."

### Q14 [mid] Redis cache vs in-memory cache: how do you choose?
tags: redis, caffeine, in-memory-cache, two-level-cache, invalidation, consistency, virtusa, reported-rounds, topic-architecture

**Start here: the concepts**
- **In-memory (Caffeine):** inside the JVM, one copy per pod. Nanoseconds to microseconds.
- **Redis:** a separate server, one copy shared by all pods. About a millisecond over the network.

**The live scenario (functional requirement)**
*FR: "Product details: read 20,000 times a second across 30 pods. An admin price update must show within seconds."*

**What the interviewer is really checking**
Consistency across pods, and whether you know the option of using both.

**How I answer it** (120-second answer, point by point)

| | In-memory (Caffeine) | Redis |
|---|---|---|
| Latency | Nanoseconds to microseconds | About 1 ms, plus serialisation |
| Shared across pods | No, each pod differs | Yes |
| Survives restart | No | Yes, if persistence is on |
| Size limit | JVM heap, and affects GC | Separate memory, scales out |
| Failure mode | Dies with the app | A network dependency that can fail |
| Invalidation | Hard across pods | One place to delete |
| Cost | No extra infrastructure | A cluster to run |

1. **Choose in-memory** for small, rarely changing data where short staleness is fine: config, currency codes.
2. **Choose Redis** when pods must agree (sessions, rate limits, locks), data is large, or a cold start would stampede the database.
3. **Use both:** Caffeine with a short TTL in front of Redis, and Redis pub/sub to clear local entries on update. This handles the price update while cutting Redis load.
4. **In all cases:** set a TTL with jitter, and have a stampede guard. Caffeine's `get(key, loader)` loads once per key in one JVM.

**Trade-offs and what can go wrong**
- A large heap cache increases GC pause times.
- Treat Redis as optional in the read path: use a short timeout and a circuit breaker, then fall back to the database.
- Caching is a consistency decision. Be able to state "how stale is acceptable".

**Follow-ups to expect**
- *Spring?* -> `@Cacheable` over a `CacheManager`, for Caffeine or Redis. It goes through a proxy, so self-invocation skips it.
- *Bank 07 Q9* covers an in-memory cache eating the heap.

**60-second answer**
"An in-memory cache like Caffeine lives inside each JVM, so it's extremely fast, but every pod has its own copy and it's lost on restart. Redis is shared by all pods and survives restarts, at around a millisecond per call, plus an operational dependency. I use in-memory for small, rarely changing data, and Redis when pods must agree, like sessions and rate limits. For high read traffic, I use both: a short-TTL local cache in front of Redis, with pub/sub to invalidate. The real question is how stale the data can be."

### Q15 [mid] What is WebSocket, and when would you use it instead of REST?
tags: websocket, sse, polling, stomp, sticky-sessions, redis-pubsub, spring-websocket, capgemini, reported-rounds, topic-rest-api

**Start here: the concepts**
- **HTTP** is request-response: the server speaks only when asked.
- **WebSocket** starts as HTTP, upgrades, and stays open as a **two-way** connection on which either side can send anytime.
- **SSE** (Server-Sent Events) is a one-way server push over ordinary HTTP.

**The live scenario (functional requirement)**
*FR: "Live delivery-tracking updates, and chat between the driver and customer."* Polling every 2 seconds across 100,000 users wastes capacity and still lags.

**What the interviewer is really checking**
When to use it (and when not), and how it scales.

**How I answer it** (120-second answer, point by point)
1. **Handshake:** the client sends `Upgrade: websocket`, and the server replies `101 Switching Protocols`. The same TCP connection then carries frames.
2. **Choose by need:**

| Need | Use |
|---|---|
| Normal request-response | REST |
| Server to client only, like notifications or LLM token streams | SSE |
| Two-way and low latency, like chat, collaboration or trading | WebSocket |
| Occasional checks | Polling is fine and simplest |

3. **Spring:** `spring-boot-starter-websocket`, usually with STOMP over WebSocket (`@MessageMapping`), and clients subscribing to topics.
4. **Scaling is the hard part:** connections are stateful and tied to one pod. To reach a user on another pod, broadcast with Redis pub/sub or Kafka, or use an external STOMP broker (`enableStompBrokerRelay`).
5. **Load balancer:** must support the upgrade, and idle timeouts must exceed your heartbeat interval.
6. **Security:** authenticate during the handshake, check the `Origin` header, and use `wss://`.

**Trade-offs and what can go wrong**
- Each open connection holds memory, and rolling deploys drop connections, so clients need reconnect with backoff.
- Delivery isn't guaranteed. For anything important, keep a message id and let the client catch up.
- Corporate proxies can block it, which is one reason libraries offered fallbacks.

**Follow-ups to expect**
- *WebClient vs WebSocket?* -> WebClient is an HTTP client, unrelated. See bank 21 Q14.
- *HTTP/2 or HTTP/3?* -> SSE gets multiplexing, so its old connection limit fades.

**60-second answer**
"WebSocket upgrades an HTTP connection to a long-lived two-way channel where either side can send anytime. I use it for chat or live collaboration. For server-to-client only, like notifications or streaming LLM tokens, SSE is simpler. For plain request-response, REST. The hard part is scale: connections are stateful and tied to a pod, so I broadcast through Redis pub/sub or a broker, make sure the load balancer supports upgrades, authenticate during the handshake, and have clients reconnect with backoff."

### Q16 [mid] Why use SonarQube, and how do you implement code coverage? What is coverage for?
tags: sonarqube, jacoco, code-coverage, quality-gate, mutation-testing, ci, capgemini, reported-rounds, topic-testing

**Start here: the concepts**
- **Code coverage** measures which lines and branches your tests executed. It shows what is **not tested**, and can't show that tested code is correct.
- **JaCoCo** measures coverage. **SonarQube** analyses code quality and applies a pass/fail **quality gate**.

**The live scenario (functional requirement)**
*FR: "Stop new bugs reaching production without slowing every PR."* A team has 85% coverage, and the tests contain no assertions.

**What the interviewer is really checking**
That you know what the tools do, and that coverage doesn't equal quality.

**How I answer it** (120-second answer, point by point)
1. **Implementing coverage:** add the JaCoCo Maven plugin. It attaches an agent during tests and writes a report.

```xml
<plugin>
  <groupId>org.jacoco</groupId><artifactId>jacoco-maven-plugin</artifactId>
  <executions>
    <execution><goals><goal>prepare-agent</goal></goals></execution>
    <execution><id>report</id><phase>verify</phase><goals><goal>report</goal></goals></execution>
  </executions>
</plugin>
```

2. **Line vs branch:** `if (a && b)` with one test may get all lines but miss branches. Branch coverage is the more useful number.
3. **SonarQube finds:** bugs, vulnerabilities, security hotspots, code smells, duplication, and takes coverage from JaCoCo's XML report.
4. **Quality gate on new code:** the valuable setting, such as 80% coverage on **new code** and no new critical issues. It doesn't punish old code, and CI fails if the gate fails.
5. **Purpose:** to find untested risk, and to stop quality from sliding, not to hit a target for its own sake.
6. **Stronger check:** **mutation testing** with PIT changes your code, and sees whether tests fail. That catches assertion-free tests.

**Trade-offs and what can go wrong**
- A 100% target leads to worthless tests on getters.
- Exclude generated code and DTOs, or numbers are misleading.
- Static analysis has false positives: triage them, don't turn off the rule set.

**Follow-ups to expect**
- *What target?* -> See bank 31 Q10. Around 70-80% on business logic, set by risk.
- *Have you worked with them?* -> Answer honestly, with what you've done, then show this reasoning.

**60-second answer**
"Coverage shows which code tests actually ran, so it tells me what's untested. It can't tell me the tests are good. I add the JaCoCo plugin, which measures during tests and produces a report. SonarQube reads that plus its own static analysis: bugs, vulnerabilities, duplication. Its key feature is a quality gate on new code that fails CI, so old code doesn't block anyone. I care more about branch coverage than line coverage, and mutation testing with PIT is the check that catches tests with no real assertions."

### Q17 [mid] If Service A calls Service B, how does the complete service-discovery flow work? How do you register a service?
tags: service-discovery, eureka, kubernetes-dns, loadbalancer, heartbeat, registration, capgemini, reported-rounds, topic-microservices

**Start here: the concepts**
- Pods get new IPs on every deploy, so hardcoded addresses break. A **registry** maps a service name to its current live instances.

**The live scenario (functional requirement)**
*FR: "`orders` calls `payments` by name. `payments` scales from 2 to 10 pods and deploys twice a day."*

**What the interviewer is really checking**
The full flow in order, and that you know how it differs on Kubernetes.

**How I answer it** (120-second answer, point by point)

Registering, with Eureka:
1. Add `spring-cloud-starter-netflix-eureka-client`.
2. Set `spring.application.name=payments` and `eureka.client.service-url.defaultZone=http://eureka:8761/eureka`.
3. At startup the client registers its name, host, port and health URL.

The flow, A calling B:
1. B starts, registers, and sends a **heartbeat** every 30 seconds by default.
2. A's client **fetches the registry** and caches it locally, refreshing about every 30 seconds.
3. A calls `http://payments/charge`, via a `@LoadBalanced` `RestClient`/`WebClient` or a Feign client.
4. **Spring Cloud LoadBalancer** replaces `payments` with a real instance, round-robin by default.
5. The call goes straight to that instance. **Eureka isn't in the request path**.
6. If B dies, heartbeats stop, and Eureka removes it after 90 seconds by default. Until then, A may hit a dead instance, so retries and a breaker are still needed.

On Kubernetes, usually no Eureka is needed:
- A `Service` object gets a stable DNS name: `payments.default.svc.cluster.local`. kube-proxy or the CNI routes to ready pods.
- Registration is automatic, using pod labels, and readiness probes decide who gets traffic.

**Trade-offs and what can go wrong**
- **Client-side** discovery (Eureka) gives smarter routing, but needs a client library per language. **Server-side** discovery (K8s, ALB) has no library.
- Eureka favours availability over consistency, so stale entries can happen. Self-preservation mode keeps entries during a network partition.
- On graceful shutdown, deregister first and drain, or calls fail during every deploy.

**Follow-ups to expect**
- *What if Eureka goes down?* -> Clients keep using their cached registry, so existing calls continue. New instances aren't discovered.
- *Gateway vs discovery?* -> Bank 91 Q8. The gateway is for north-south traffic, and discovery is for east-west.

**60-second answer**
"With Eureka, B registers its name and address at startup and sends heartbeats. A fetches and caches the registry. When A calls http://payments, Spring Cloud LoadBalancer picks an instance from that cache, and the call goes directly there, so Eureka isn't in the request path. If B dies, Eureka removes it after missed heartbeats, so A still needs retries and a breaker. To register, I add the Eureka client, set the application name and the server URL. On Kubernetes, you usually don't need Eureka: a Service gives a stable DNS name, and readiness probes decide who gets traffic."

### Q18 [mid] From a performance and security perspective, why move from Java 8 to Java 17, even without using records or sealed classes?
tags: java8, java17, upgrade, g1, zgc, tls13, strong-encapsulation, containers, lts, capgemini, reported-rounds, topic-java-core

**Start here: the concepts**
- A new JDK improves the **runtime** (GC, JIT, security, container support), which you get without changing a line of code.

**The live scenario (functional requirement)**
*FR: "Justify an upgrade to a manager who says 'we don't need any new language features'."*

**What the interviewer is really checking**
That your answer isn't about syntax. It's about the JVM and the support lifecycle.

**How I answer it** (120-second answer, point by point)

Performance, no code changes:
| Area | Change |
|---|---|
| G1 GC | Parallel full GC (10), returns unused memory to the OS (12), abortable mixed collections, and years of tuning |
| Low-pause GC | ZGC and Shenandoah are production-ready from 15 |
| Strings | Compact strings (9) reduce heap for Latin-1 text |
| Startup | Application class-data sharing, with default CDS |
| Containers | The JVM respects cgroup CPU and memory limits properly |
| Diagnostics | Flight Recorder became free and open in 11, and helpful NPE messages arrived in 14-15 |

Security:
| Area | Change |
|---|---|
| TLS | TLS 1.3 (11) |
| Algorithms | Older and weak ones are disabled by default |
| Encapsulation | Strong by default in 16-17: reflection into JDK internals is blocked, which reduces attack surface |
| Removal | CORBA and Java EE modules removed (11); Applet API and Security Manager deprecated for removal (17) |
| Patches | Current LTS receives security fixes from free vendors |

**Business reason:** free public updates for Java 8 have been limited for years, and modern frameworks need newer JDKs. **Spring Boot 3 requires Java 17**, and Boot 2.x open-source support has ended, so staying on 8 means frameworks without fixes.

**Trade-offs and what can go wrong**
- Migration cost: libraries using JDK internals break on strong encapsulation; `javax` to `jakarta` comes with the Boot 3 move; and removed modules (JAXB) need explicit dependencies.
- Measure the performance gains in your own workload. Published numbers vary.
- If upgrading today, target 21 or 25 rather than stopping at 17. See bank 87.

**Follow-ups to expect**
- *What did you actually need to change?* -> Bank 71 Q12 walks through an upgrade.

**60-second answer**
"Even with no new syntax, you get a much better runtime. G1 has improved a lot, ZGC is available, compact strings shrink the heap, startup is faster with class-data sharing, and the JVM handles container limits properly. For security, you get TLS 1.3, weak algorithms disabled, strong encapsulation of JDK internals and, most importantly, supported patches. And the framework reason is decisive: Spring Boot 3 requires 17, so staying on 8 means an unsupported stack. The cost is libraries that used internals and the javax to jakarta move. I'd measure gains on our workload, and today I'd target 21 or 25."

### Q19 [mid] How has Spring Boot evolved from 1.0 to 4.0? What should you know for each version?
tags: spring-boot, version-history, spring-boot-4, jakarta, java-baseline, framework-7, migration, reported-rounds

**Start here: the concepts**
- A major Boot version usually follows a major Spring Framework version and raises the Java baseline.

**The live scenario (functional requirement)**
*FR: "We are on Boot 2.7. Plan the path to a supported version."* A popular infographic says Boot 4 requires Java 21. The official docs say **Java 17**. Quoting the wrong baseline in an interview, or in a plan, costs credibility.

**What the interviewer is really checking**
Whether you know the breaking changes in each major version, not just the year.

**How I answer it** (120-second answer, point by point)

| Boot | Year | Framework | Minimum Java | Embedded Tomcat | Main idea |
|---|---|---|---|---|---|
| 1.0 | 2014 | 4 | 6 | 7 | Auto-configuration, starters, executable JAR |
| 2.0 | 2018 | 5 | 8 | 8.5 | WebFlux, Micrometer, Actuator rework, HikariCP default |
| 3.0 | 2022 | 6 | 17 | 10 | `javax` to `jakarta`, native image via AOT, observability API |
| 4.0 | 2025 | 7 | 17 (up to 25 tested) | 11 (Servlet 6.1) | Modular auto-configuration, API versioning, JSpecify null-safety |

1. **2 to 3 is the hard one:** the `jakarta` package rename touches a lot of code, and Java 17 is required. Go via 2.7 first, and use OpenRewrite to automate it.
2. **Virtual threads:** on Java 21+, `spring.threads.virtual.enabled=true` (from Boot 3.2).
3. **AI:** Boot 4 isn't "AI-ready" in itself. Spring AI is a separate project: 2.0 targets Boot 4.0 and 4.1, and 2.1 milestones target Boot 4.2.

Corrections to that infographic, checked against the docs:
- Boot 4 minimum Java is **17**, not 21. 25 is the highest listed as compatible for 4.0.
- Boot 2.0 shipped with **Tomcat 8.5**, not 9, which came with 2.1.
- Early Boot 1.x documented **Java 6** as the minimum, not Java 8 (the oldest docs still online, 1.2.x, say Java 6).
- "Fastest startup and lowest memory" is marketing unless measured on your app.

**Trade-offs and what can go wrong**
- Don't skip the deprecation warnings. Fix them on the last release of your current line, and only then jump.
- Third-party starters often lag behind a new major, so check them first.

**Follow-ups to expect**
- *What is the upgrade order?* -> Bank 71 Q12.
- *Is Boot 4's Jackson different?* -> Jackson 3 is the new default, so expect package changes. Check the 4.0 migration guide.

**60-second answer**
"Boot 1 introduced auto-configuration and starters on Framework 4. Boot 2 added WebFlux and Micrometer on Framework 5, with Java 8. Boot 3 was the hard one: Java 17, and javax moved to jakarta, on Framework 6. Boot 4 is on Framework 7 with Tomcat 11, modular auto-configuration and built-in API versioning, and its minimum is still Java 17, not 21 as some infographics claim. Spring AI is a separate project on top. For a move from 2.7, I'd clear deprecations first and use OpenRewrite for the jakarta rename."

### Q20 [fresher] Why do we use Spring Boot? How does it differ from Spring?
tags: spring-boot, spring-vs-spring-boot, starters, auto-configuration, embedded-server, actuator, capgemini, reported-rounds

**Start here: the concepts**
- **Spring Framework** gives you dependency injection, MVC, transactions and more, and you wire them together yourself.
- **Spring Boot** sits on top and removes that setup through conventions. It isn't a replacement for Spring.

**The live scenario (functional requirement)**
*FR: "Start a new order microservice this sprint."* With plain Spring, the team first chooses compatible library versions, configures a servlet container, a data source and JSON, and then starts on the actual feature.

**What the interviewer is really checking**
Whether you can name concrete benefits, and know that the magic can be inspected and overridden.

**How I answer it** (120-second answer, point by point)

| Feature | What it removes |
|---|---|
| **Starters** | Choosing compatible libraries: `spring-boot-starter-web` brings a tested set |
| **Auto-configuration** | Writing the beans you'd always write, based on the classpath and properties |
| **Embedded server** | Installing Tomcat and deploying a WAR: `java -jar app.jar` runs it |
| **Actuator** | Building health, metrics and info endpoints by hand |
| **Externalised config** | Rebuilding per environment: properties, YAML, env vars and profiles |
| **Dependency management** | Maintaining version numbers: the parent BOM manages them |

1. **It stays out of your way:** define your own bean, and the auto-configured one backs off because of `@ConditionalOnMissingBean`.
2. **It isn't magic:** `--debug` prints the conditions report, showing what was applied and why, and Actuator's `/actuator/conditions` shows the same at run time.
3. **Why it suits microservices:** a self-contained JAR is simple to containerise, and has health probes built in.

**Trade-offs and what can go wrong**
- Unused starters add startup time and memory, so remove what you don't need.
- It's easy to use without understanding what's underneath, which makes debugging harder. Knowing how auto-configuration works matters (bank 85 Q2).
- A framework version upgrade is larger than a library bump, so plan for it (bank 71 Q12).

**Follow-ups to expect**
- *Can you still deploy a WAR?* -> Yes, with `SpringBootServletInitializer`, though it's rarely needed now.
- *Alternatives?* -> Quarkus and Micronaut, which favour build-time processing for faster startup.

**60-second answer**
"Spring gives the core features, but you wire them together. Spring Boot sits on top and removes that setup. Starters bring a tested set of dependencies, auto-configuration creates the usual beans based on the classpath and properties, an embedded server means java -jar just runs it, and Actuator gives health and metrics. It backs off when you define your own bean, and the conditions report shows why anything was configured. That's why it suits microservices. The cost is some extra startup and memory, and you still need to understand what's underneath."
