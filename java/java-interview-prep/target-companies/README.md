# Target companies: Nagarro, Persistent Systems, EPAM Systems

One place to prepare for a **specific company's** Java backend interview. Each company has its own section:
how candidates describe the rounds, what the interviewers score, the questions candidates report, and **where
each one is answered** in this repo, either in a new company bank (90-94) or an existing bank.

**Read this first.** Everything here comes from **public candidate reports** (Glassdoor, AmbitionBox, LeetCode
Discuss, GeeksforGeeks, Naukri Code360) and job postings, checked on 2026-10-28. These are anecdotes, not an official
process: rounds differ by team, level, city and year. **Confirm the stages with your recruiter**, and treat the lists
below as likely topics, not a syllabus. Don't memorise answers; practise the approach and explain your trade-offs.

## At a glance

| | Nagarro | Persistent Systems | EPAM Systems |
|---|---|---|---|
| Typical flow | Online coding test -> 1-2 technical rounds -> (design for senior) -> HR / culture fit | 2-3 technical rounds (core Java, then Spring/microservices, sometimes coding) -> HR | HR contact -> 1-2 technical interviews with an EPAM engineer (sometimes a partner firm first) -> manager / HR |
| Heaviest weight | Coding/DSA + Spring Boot + **system design** + client-facing behaviour | **Core Java + Java 8** depth, Spring Boot annotations and practical scenarios | **Engineering craft**: OOP/SOLID, collections, multithreading, testing/TDD, **live coding in your IDE** |
| Coding style | Timed online test (one report: 3 problems in 75 min), plus short Java 8 streams tasks | One problem, then "make it more efficient" | Screen-share in your own IDE; reasoning and tests matter more than speed |
| Design round | Yes for mid-senior: URL shortener, chat, checkout, notifications, pipelines, CAP | Light: microservice components, communication, resilience | "Architecture of a large system you built", coupling/cohesion |
| New bank(s) here | [90](../interview-scenarios/90_target_nagarro_system_design.md), [91](../interview-scenarios/91_target_nagarro_backend_spring.md), [92](../interview-scenarios/92_target_nagarro_behavioural.md) | [93](../interview-scenarios/93_target_persistent_java_spring.md) | [94](../interview-scenarios/94_target_epam_java_engineering.md) |

Every new answer uses the coach's scenario format: *Start here: the concepts* -> *The live scenario* -> *What the
interviewer is really checking* -> **How I answer it (120-second, point by point)** -> *Trade-offs* -> *Follow-ups* ->
**60-second answer**. In a rapid-fire round, give the 60-second answer and stop. When they say "go deeper", expand into
the 120-second points.

---

## Nagarro

A global digital engineering services company. Most work is **client-facing product delivery**, so interviewers
listen for ownership, clear communication of assumptions, and practical fluency across the stack (Spring Boot, Docker,
Kubernetes, Kafka), not only correct answers.

### Rounds candidates describe

| Round | What happens | Prepare with |
|---|---|---|
| Online assessment | Timed DSA problems on an online platform with hidden test cases: arrays, strings, linked lists, heaps, trees | Bank [50](../interview-scenarios/50_coding_round_problems.md) (31 problems) + the gaps listed below |
| Technical 1 | OOP, Java 8 features, collections, HashMap/ConcurrentHashMap, basic SQL, Spring annotations | Bank [91](../interview-scenarios/91_target_nagarro_backend_spring.md) Q6, Q10 · bank [83](../interview-scenarios/83_company_jpmc_java_core_mid_senior.md) Q1 |
| Technical 2 / quick checks | Spring Boot depth, microservices patterns, "do you know Kafka / Docker?", project deep dive | Bank 91 (all), bank [24](../interview-scenarios/24_microservices_foundations.md) |
| System design (mid-senior, 45-60 min) | One of the 8 classic prompts below, with trade-offs | Bank [90](../interview-scenarios/90_target_nagarro_system_design.md) |
| HR / culture fit | Challenging project, deadlines, conflict, client experience, "Why Nagarro?" | Bank [92](../interview-scenarios/92_target_nagarro_behavioural.md), bank [40](../interview-scenarios/40_leadership_foundations.md) |

### What Nagarro evaluates in a design answer

1. **Clarity of assumptions:** state scope and constraints before drawing anything.
2. **Scalability and performance:** show how the system grows, with numbers (QPS, storage, partitions).
3. **Trade-offs explained:** consistency vs availability, latency vs throughput, sync vs async.
4. **Practical fluency:** connect the design to Spring Boot, Docker, Kubernetes, Kafka, Redis you have actually used.

### Reported questions and where they are answered

| Area | Reported question / topic | Answer |
|---|---|---|
| **System design** | URL shortener: hashing, collisions, analytics, scale | [90 Q1](../interview-scenarios/90_target_nagarro_system_design.md) |
| | Real-time chat: delivery guarantees, offline storage, millions of users | 90 Q2 |
| | E-commerce checkout: inventory, payments, order tracking, fault tolerance | 90 Q3 |
| | Distributed database trade-offs: CAP, replication, partitioning | 90 Q4 |
| | Load balancing and failover for high availability | 90 Q5 |
| | Notification service: push/email/SMS, retries, rate limiting, personalisation | 90 Q6 |
| | Data pipeline: clickstream / IoT ingestion, near-real-time analytics | 90 Q7 |
| | Security in application design: authn, authz, encryption, secure APIs | 90 Q8 |
| | Logging / monitoring pipeline | Bank [09](../interview-scenarios/09_production_monitoring.md), bank [28](../interview-scenarios/28_splunk_observability_foundations.md) |
| | Design a scalable system in Spring Boot; API gateway, load balancer | [91 Q8](../interview-scenarios/91_target_nagarro_backend_spring.md), 90 Q5 |
| **Backend** | REST vs gRPC | 91 Q1 |
| | Database indexing | 91 Q2 |
| | Transactions (ACID, isolation, `@Transactional`) | 91 Q3 |
| | Payment API receiving duplicate requests: idempotency | 91 Q4 |
| | Money deducted but order creation failed: data consistency | 91 Q5 |
| | Auto-configuration, `@SpringBootApplication`, starters, DI | 91 Q6 |
| | Caching in Spring Boot | 91 Q7 |
| | Kafka partitions, ordering, "do you know Kafka?" | 91 Q9 · bank [62](../interview-scenarios/62_round_kafka.md) |
| | CAP theorem, microservices patterns | 90 Q4 · bank 24 · bank [86](../interview-scenarios/86_company_jpmc_microservices_kafka_design.md) Q5 |
| | Spring bean lifecycle, GC incl. ZGC | Bank [21](../interview-scenarios/21_spring_boot_foundations.md) · bank [84](../interview-scenarios/84_company_jpmc_concurrency_jvm.md) Q9 |
| **Java 8 coding** | Second non-repeating character with streams; group employees by department and role | 91 Q10 · bank 50 Q5, Q18 |
| **DSA** | Two-sum; longest substring without repeating characters; sliding window | 50 Q8, Q6 · [94 Q3](../interview-scenarios/94_target_epam_java_engineering.md) |
| | Linked lists: detect cycle, reverse | 50 Q23, Q22 |
| | Trees/graphs: traversals, BFS | 50 Q26, Q25 |
| | **Not covered here yet:** merge k sorted lists (heap), lowest common ancestor, shortest path (BFS / Dijkstra), dynamic programming | Practise on LeetCode / GeeksforGeeks, medium level |
| **Behavioural** | Challenging client delivery | [92 Q1](../interview-scenarios/92_target_nagarro_behavioural.md) |
| | Conflict with a teammate | 92 Q2 |
| | Why Nagarro? | 92 Q3 |
| | Handling deadlines | 92 Q4 |
| | Learning a new technology fast | 92 Q5 |
| | A production issue you owned | 92 Q6 |

**Frontend and data/ML roles** are also reported (component lifecycle, state management, accessibility; ETL,
feature engineering, model metrics, analytics SQL). They are outside this Java backend pack. For analytics SQL use
bank [29](../interview-scenarios/29_sql_foundations.md), and for pipelines use 90 Q7.

### Nagarro prep plan (5 days)

1. **Day 1, coding:** 10 problems from bank 50 (Q5, Q6, Q8, Q10, Q18, Q22, Q23, Q25, Q26, Q27) under a timer, plus 2 from the gap list.
2. **Day 2, backend:** bank 91 Q1-Q10. Say each 60-second answer aloud.
3. **Day 3, design:** bank 90 Q1-Q4. Draw each on paper using the 5-step skeleton at the top of the bank, and time it at 45 minutes.
4. **Day 4, design:** bank 90 Q5-Q8. Then rehearse a **5-minute summary** of one design: interviewers push for concise trade-offs.
5. **Day 5, behavioural:** rewrite bank 92's six stories with your own projects and numbers. Do one mock interview (Pramp, Interviewing.io, or the coach's *Mock interview*).

**Risk to avoid:** over-fitting to these exact prompts. Interviewers change one constraint ("now offline-first",
"now 10x traffic"), so practise *reasoning*: clarify, numbers, design, hard parts, trade-offs.

### Questions to ask Nagarro

1. Is this role on a specific client account already? Which domain and stack?
2. How much client-facing communication does the role involve (demos, requirement workshops)?
3. What does the delivery model look like: a distributed team across countries, on-site visits?
4. How are engineers grown here: certifications, internal mobility between accounts?

---

## Persistent Systems

An Indian-headquartered digital engineering and IT services company. Its Java job postings ask for **Java 8/11/17,
Spring Boot, Spring MVC, Spring Data JPA, REST, Kafka, Docker/Kubernetes, CI/CD**, and for senior roles AWS or GCP.

### Rounds candidates describe

| Round | What happens | Prepare with |
|---|---|---|
| Technical 1, core Java | Wrapper classes, HashMap internals, functional interfaces, default/static interface methods, Java 8 streams, collections, singleton, design patterns, SQL joins | [93](../interview-scenarios/93_target_persistent_java_spring.md) Q1-Q5 · 83 Q1 · bank 29 |
| Technical 2, Spring + microservices | `@SpringBootApplication`/`@ComponentScan`/`@RestController`, error handling, JPA, scheduler, **two databases**, circuit breaker, service communication, OAuth | 93 Q6-Q11 · 91 Q6 |
| Coding (often inside a technical round) | One problem; the interviewer asks for a **more efficient** solution | Bank 50: practise "brute force -> optimised" out loud |
| HR | Notice period, location, compensation, motivation | Bank 40 |

### Reported questions and where they are answered

| Reported question / topic | Answer |
|---|---|
| Wrapper classes, autoboxing, Integer cache | [93 Q1](../interview-scenarios/93_target_persistent_java_spring.md) |
| How HashMap works internally | [83 Q1](../interview-scenarios/83_company_jpmc_java_core_mid_senior.md) · 94 Q2 |
| Functional interfaces; static and default methods in interfaces | 93 Q2 |
| Stream API, map vs flatMap, collections | 93 Q3 · 50 Q18-Q21 |
| Write a singleton class (thread-safe, how it breaks) | 93 Q4 · 50 Q28 |
| Core Java + multithreading question | 93 Q5 · 50 Q29 · 84 |
| Spring Boot error handling | 93 Q6 |
| Spring Boot annotations: `@SpringBootApplication`, `@ComponentScan`, `@RestController` | 91 Q6 · bank 21 |
| Connect Spring Boot to two databases | 93 Q7 |
| Spring Scheduler (and running it on several pods) | 93 Q8 |
| Circuit breakers | 93 Q9 · bank [61](../interview-scenarios/61_round_spring_boot.md) |
| Components of a microservice architecture; REST vs Kafka/RabbitMQ communication | 93 Q10 |
| What OAuth is for | 93 Q11 · 90 Q8 |
| Spring Data JPA, SQL joins | Bank 29 · brush-up [02](../company-chase-travel/brush-up/02-database-connection-spring-boot.md) |
| Kafka topics, partitions, offsets | 91 Q9 · bank [22](../interview-scenarios/22_kafka_foundations.md) |
| Basic distributed-systems questions | 90 Q4 · bank 30 |

### Persistent prep plan (3 days)

1. **Day 1:** bank 93 Q1-Q5 and bank 83 Q1. Code the odd/even printer and the holder singleton from memory.
2. **Day 2:** bank 93 Q6-Q11. Write the two-datasource configuration once by hand; it is a favourite "explain how" question.
3. **Day 3:** four bank-50 problems, each solved twice (brute force, then optimised) while talking. Revise the 60-second answers.

### Questions to ask Persistent

1. Which client or product will this role support, and which Java / Spring Boot versions?
2. Is the work greenfield microservices or modernisation of an existing system?
3. Which cloud (AWS, Azure, GCP) and how are services deployed?

---

## EPAM Systems

A global software engineering and consulting company. Its interviewers are practising engineers, and reports
consistently mention **craft**: clean code, OOP and SOLID, testing, and how you think while coding.

### Rounds candidates describe

| Round | What happens | Prepare with |
|---|---|---|
| HR contact | Role, location, English, expectations | Bank 40 (motivation, a 2-minute project story) |
| Technical interview(s) | Core Java (collections, iterators, hashing, multithreading), Java 8 streams, OOP, design patterns, coupling vs cohesion, Spring Boot, Spring Security, JUnit/Mockito, basic SQL, microservices, Kafka groups/DLQ/keys | [94](../interview-scenarios/94_target_epam_java_engineering.md) |
| Live coding | **In your own IDE, sharing the screen**: longest substring without repeats, a tree path problem, grouping numbers into ranges with Java 8 | 94 Q3-Q5 · bank 50 |
| Take-home (some reports) | A small TDD exercise with JUnit | 94 Q7 |
| Manager / HR | Project architecture, teamwork, offer | 94 Q11 · bank 40 |

**EPAM-specific advice from candidates:** set up your IDE before the call (a blank Maven/Gradle project with JUnit 5,
font size large enough to share). Narrate as you code, write tests for edge cases, and **don't rush**: one candidate
felt that finishing too fast without explanation counted against them. Strong DSA practice is repeatedly recommended.

### Reported questions and where they are answered

| Reported question / topic | Answer |
|---|---|
| Iterator vs ListIterator (and fail-fast) | [94 Q1](../interview-scenarios/94_target_epam_java_engineering.md) |
| How Java computes a hash | 94 Q2 · 83 Q1-Q2 |
| Longest substring without repeating characters (live) | 94 Q3 · 50 Q6 |
| Group numbers into ranges using Java 8 (live) | 94 Q4 |
| Optimal path in a tree (live) | 94 Q5 · 50 Q25-Q26 |
| Coupling vs cohesion, SOLID, design patterns | 94 Q6 · bank 30 |
| JUnit, Mockito, TDD exercise | 94 Q7 · bank [31](../interview-scenarios/31_testing_foundations.md) |
| Multithreading concepts | 94 Q8 · bank 84 |
| Kafka: consumers in a group, multiple groups, message keys, DLQ | 94 Q9 · bank 02 |
| Spring Security | 94 Q10 · 93 Q11 |
| Architecture of a large system you worked on | 94 Q11 |
| Java streams, collections, maps, microservices concepts | 93 Q3 · 50 Q18-Q21 · bank 24 |
| Basic SQL queries | Bank 29 |

### EPAM prep plan (3 days)

1. **Day 1:** bank 94 Q1, Q2, Q6, Q7, Q8. Write one TDD kata end to end (red-green-refactor) in your IDE.
2. **Day 2:** live-coding practice, sharing your own screen to a friend or recording yourself: 94 Q3, Q4, Q5 plus three bank-50 problems. Explain first, then code, then test.
3. **Day 3:** 94 Q9, Q10, and rehearse **94 Q11 with your own system** until it fits in 2 minutes with numbers.

### Questions to ask EPAM

1. Which client and domain is this role for, and how big is the team?
2. What does a typical engineering workflow look like: code review, testing standards, CI/CD?
3. How do engineers grow at EPAM: levels, internal learning, moving between projects?

---

## Where these questions are used in the coach

| Bank file | Questions | Interview Coach topic card (Java stack) | Coach `skill:` id |
|---|---|---|---|
| `90_target_nagarro_system_design.md` | 8 | System design & design patterns | `architecture` |
| `91_target_nagarro_backend_spring.md` | 10 | Microservices architecture | `microservices` |
| `92_target_nagarro_behavioural.md` | 6 | Leadership, behavioural & your projects | `leadership` |
| `93_target_persistent_java_spring.md` | 11 | Spring & Spring Boot | `spring-boot` |
| `94_target_epam_java_engineering.md` | 11 | Java 8, Java 11 & modern Java | `java-core` |
| **Total target-company section** | **46** | | |

In the coach, the banks appear inside their topic cards (Topics), and *Ask anything* and *Mock interview* use them for
grounding and scoring. Every question is tagged with the company name (`nagarro`, `persistent`, `epam`), so a tag
search finds one company's set.

## Adding another target company

1. Add a section to this README with the same parts: rounds, reported questions -> answer, prep plan, questions to ask, sources.
2. Put new answers in `../interview-scenarios/9N_target_<company>_<focus>.md` (next free number) with front matter
   `id`, `title`, `stack: java` and a `skill:` id from `interview-coach/skills/java/`, and tag every question with the company.
3. Add the bank to the table above and to `../interview-scenarios/README.md`. Run the coach's `tests/test_real_repo.py`.
4. Reuse existing banks wherever a question is already answered; add new answers only for real gaps.

## Sources (checked 2026-10-28)

Nagarro
- [Nagarro interview questions (AmbitionBox)](https://www.ambitionbox.com/interviews/nagarro-interview-questions)
- [Nagarro careers (nagarro.com)](https://www.nagarro.com/en/careers)
- [Recently appeared for Nagarro interview, sharing my experience (LeetCode Discuss)](https://leetcode.com/discuss/post/7891670/recently-appeared-for-nagarro-interview-k1zd4/)
- [Nagarro interview experience for SDE Java developer, 3 years (GeeksforGeeks)](https://www.geeksforgeeks.org/?p=562015)
- [Nagarro interview review (Glassdoor)](https://static.glassdoor.at/Interview/Nagarro-Interview-E240077-RVW84284725.htm)
- [Nagarro interview review (Glassdoor)](https://www.glassdoor.com.hk/Interview/Nagarro-Interview-E240077-RVW87369123.htm)
- [Staff Engineer, Java Full Stack (Nagarro posting via NodeFlair)](https://nodeflair.com/jobs/nagarro-staff-engineer-java-full-stack-509511)

Persistent Systems
- [Persistent Systems senior Java developer interview questions (AmbitionBox)](https://www.ambitionbox.com/interviews/persistent-systems-interview-questions/senior-java-developer)
- [Persistent Systems interview experience (Naukri Code360)](https://www.naukri.com/code360/interview-experiences/persistent-systems/persistent-systems-interview-experience-off-campus-jun-2021-1366)
- [Persistent Systems interview review (Glassdoor)](https://www.glassdoor.com/Interview/Persistent-Systems-Interview-E150639-RVW96709405.htm)
- [Persistent Systems interview review (Glassdoor)](https://www.glassdoor.com/Interview/Persistent-Systems-Interview-E150639-RVW97636436.htm)
- [Java Developer, Persistent Systems (posting via NodeFlair)](https://nodeflair.com/jobs/persistent-systems-java-developer-543349)

EPAM Systems
- [EPAM Systems interview review (Glassdoor)](https://www.glassdoor.com.au/Interview/EPAM-Systems-Interview-E15544-RVW43566116.htm)
- [EPAM Systems interview review (Glassdoor)](https://www.glassdoor.com.au/Interview/EPAM-Systems-Interview-E15544-RVW70649819.htm)
- [EPAM Systems interview review (Glassdoor)](https://www.glassdoor.ca/Interview/EPAM-Systems-Interview-E15544-RVW70946905.htm)
- [EPAM Systems interview review (Glassdoor)](https://www.glassdoor.ca/Interview/EPAM-Systems-Interview-E15544-RVW92109490.htm)
- [EPAM Systems interview review (Glassdoor)](https://www.glassdoor.com.au/Interview/EPAM-Systems-Interview-E15544-RVW61849640.htm)
