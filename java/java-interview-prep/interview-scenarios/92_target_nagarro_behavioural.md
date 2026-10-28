---
id: target-nagarro-behavioural
title: Target company, Nagarro (3/3): behavioural, HR and culture-fit round (STAR)
stack: java
skill: leadership
---
Part of the **target-company section** (hub: `../target-companies/README.md`, section "Nagarro").
Nagarro is a client-facing digital engineering services company, so its behavioural round listens for
**ownership, client communication, learning speed, teamwork across distributed teams, and measurable impact**.

How to use these answers:
- Each answer is a **model story** in STAR form (Situation, Task, Action, Result), placed in the coach's sections:
  *The live scenario* = Situation + Task, *How I answer it* = Actions + Result, *60-second answer* = what you say.
- **Replace every illustrative detail with your own real project, numbers and names of technologies.** An interviewer
  can tell a borrowed story in two follow-up questions.
- Keep each story under two minutes, say "I" (not "we") for your actions, and end with a number and a lesson.

### Q1 [mid] Tell me about a challenging client delivery you owned
tags: behavioural, star, client-delivery, ownership, deadline, scope, stakeholder, nagarro

**The live scenario (functional requirement)**
*Situation:* a client in retail needed an order-tracking API live before a festival sale, 6 weeks away. Two weeks in, the
client's legacy inventory system turned out to have no API, only a nightly batch file. *Task:* I was the backend lead
responsible for delivering the integration on time without risking the sale.

**What the interviewer is really checking**
Ownership when things go wrong, honest client communication, a concrete trade-off you drove, and a measurable result.

**How I answer it** (120-second answer, point by point)
1. **Made the risk visible early:** the same day, I wrote a one-page note for the client: the problem, three options with effort and risk, and my recommendation.
2. **Proposed a pragmatic design:** ingest the nightly file into our database plus a small change-data feed from their order DB, instead of waiting for a new API from their team.
3. **Re-planned the scope with the client's product owner:** real-time stock moved to phase 2; order tracking (the sale-critical part) stayed in phase 1.
4. **Protected the delivery:** daily 15-minute sync with the client team, a contract test against sample files, and a load test at 3x the expected sale traffic.
5. **Result:** live 4 days before the sale; it handled 2.5x normal traffic with p99 under 300 ms and zero sev-1 incidents. The client extended the engagement for phase 2.
6. **Lesson:** surface integration risks in week one with a spike, not in week three.

**Trade-offs and what can go wrong**
- I accepted data that was up to a few hours stale for stock; I made that explicit in writing so it was a shared decision, not a surprise.
- Pitfall to avoid in the telling: blaming the client. Describe the constraint, not the people.

**Follow-ups to expect**
- *What would you do differently?* -> Run an integration spike in the first sprint for every external system.
- *How did you handle pushback?* -> I brought data (effort, risk, dates) and let the product owner choose between clear options.

**60-second answer**
"For a retail client we had six weeks to launch an order-tracking API before a festival sale, and two weeks in I found
their inventory system had no API, only a nightly batch file. I flagged it the same day with a one-page note: three
options, their risk and my recommendation. We ingested the batch file plus a change feed from their order database, and
agreed with the product owner to move real-time stock to phase two. I set up daily syncs, contract tests on sample files
and a load test at three times expected traffic. We went live four days early, handled two and a half times normal
traffic with p99 under 300 milliseconds, and the client extended us for phase two. My lesson: spike every external
integration in the first sprint."

### Q2 [mid] Describe a conflict with a teammate and how you resolved it
tags: behavioural, star, conflict, teamwork, collaboration, code-review, disagreement, nagarro

**The live scenario (functional requirement)**
*Situation:* a senior colleague wanted every service call to be synchronous REST "to keep it simple"; I believed order
events should go through Kafka because three downstream teams needed them. Code reviews became tense and the sprint was
slipping. *Task:* reach a decision without damaging the working relationship.

**What the interviewer is really checking**
That you disagree with respect, use data instead of opinion, can accept being partly wrong, and keep the team moving.

**How I answer it** (120-second answer, point by point)
1. **Moved it out of the PR comments:** I asked for a 30-minute call; text threads were escalating.
2. **Understood their concern first:** their real worry was operational: nobody on the team had run Kafka in production.
3. **Agreed on criteria, not solutions:** latency, coupling between teams, and operational risk.
4. **Ran a small spike together:** one event flow on the client's managed Kafka, with monitoring dashboards and a runbook.
5. **Decision:** Kafka for the order-events fan-out, synchronous REST for queries that need an immediate answer. Both of our concerns were met.
6. **Result:** delivered the sprint goal one day late instead of a full sprint; the colleague later led the Kafka runbook work.
7. **Lesson:** most technical conflicts are about different unstated risks; name the criteria first.

**Trade-offs and what can go wrong**
- Escalating to the manager first would have been faster but would have cost trust.
- Avoid stories where you "won" and the other person was simply wrong; interviewers look for mutual respect.

**Follow-ups to expect**
- *What if you could not agree?* -> I'd write both options with the criteria and ask the architect or tech lead to decide, and then commit fully to the decision.
- *Have you ever been the one who was wrong?* -> Have one short example ready where you changed your mind on data.

**60-second answer**
"A senior colleague wanted every interaction as synchronous REST, and I wanted order events on Kafka because three teams
consumed them. Review comments were getting tense, so I asked for a call. I listened first, and their real concern was
that nobody on the team had operated Kafka. We agreed on criteria: latency, coupling and operational risk. Then we ran a
small spike together with dashboards and a runbook. We ended up with Kafka for event fan-out and REST for queries that
need an immediate answer. We lost one day, not a sprint, and that colleague later owned the Kafka runbook. I learned that
technical conflicts are usually about unstated risks, so I name the criteria first."

### Q3 [fresher] Why Nagarro?
tags: hr, why-company, motivation, culture-fit, client-facing, nagarro

**The live scenario (functional requirement)**
The HR or managerial round asks "Why Nagarro?" and often "Why are you leaving your current company?" in the same
breath. They want to know whether you understand the company and will stay.

**What the interviewer is really checking**
Research (not flattery), a link between what Nagarro does and what you have done, and a forward-looking reason for the
move.

**How I answer it** (120-second answer, point by point)
1. **What I know about them:** a global digital engineering company that builds products for clients in many industries (retail, travel, banking, automotive, and more), known for an entrepreneurial, flat culture with a lot of autonomy. *Check their current site and pick one or two industries or case studies that match your background.*
2. **Link to my experience:** "I have spent N years building Java/Spring Boot microservices with Kafka for client-facing products; I enjoy working directly with client stakeholders and turning vague requirements into a working system."
3. **What I want next:** variety of domains and modern stacks (cloud, event-driven, GenAI), and more ownership of design decisions.
4. **Reason for the move (positive):** "My current project is stable and in maintenance; I want to be closer to design and client delivery." Never criticise the current employer.
5. **Close with value:** "I can contribute from week one on backend design, performance tuning and production support."

**Trade-offs and what can go wrong**
- Generic answers ("good brand, good growth") score poorly.
- Salary as the first reason is a red flag even if it is true; mention it only in the compensation discussion.

**Follow-ups to expect**
- *Are you open to relocation, travel or client-site work?* -> Decide your honest answer before the interview.
- *Where do you see yourself in 3 years?* -> Leading the design of a product area and mentoring engineers; tie it to a role path they actually have.

**60-second answer**
"Nagarro builds digital products for clients across many industries, and that's the work I enjoy most. For the last few
years I've built Java and Spring Boot microservices with Kafka for client-facing systems, and I work directly with
stakeholders to turn loose requirements into working software. What attracts me is the variety of domains and modern
stacks, and the autonomy people describe in your culture. That fits my next step, which is owning design decisions end
to end. My current project has moved into maintenance, so I'm looking for that challenge. I can contribute quickly on
backend design, performance and production support."

### Q4 [mid] How do you handle tight deadlines and changing priorities?
tags: behavioural, star, deadlines, prioritisation, scope, agile, communication, nagarro

**The live scenario (functional requirement)**
*Situation:* three days before a release, the client added a regulatory change (masking card numbers in all logs and
exports). *Task:* include it without dropping the release or quality.

**What the interviewer is really checking**
That you prioritise openly, negotiate scope instead of quietly working overtime, and protect quality under pressure.

**How I answer it** (120-second answer, point by point)
1. **Clarified the real deadline:** the regulation applied from the release date, so it was truly mandatory.
2. **Estimated quickly and visibly:** 1.5 days for a central log-masking filter plus export changes.
3. **Traded scope:** with the product owner, moved two low-value UI enhancements to the next sprint.
4. **Reduced risk:** one central Logback masking converter instead of edits in 40 places; unit tests with sample card numbers; a log scan in the test environment for any 16-digit pattern.
5. **Result:** released on time; the audit found no unmasked PAN; the masking was later reused by two other teams.
6. **Lesson:** deadlines are fixed, scope is negotiable; always make the trade explicit.

**Trade-offs and what can go wrong**
- Agreeing to everything and working nights hides the problem and usually lowers quality.
- Skipping tests "to save time" under pressure is how the worst incidents ship.

**Follow-ups to expect**
- *What if the client refuses to drop scope?* -> Show the risk in writing and propose a phased delivery or more people for a short period; let them choose.
- *How do you estimate?* -> Break into tasks under one day, add risk buffer for unknowns, and re-estimate daily.

**60-second answer**
"Three days before a release, the client added a regulatory requirement to mask card numbers in logs and exports. I
confirmed it was mandatory for that date, estimated a day and a half, and agreed with the product owner to move two
low-value UI items to the next sprint. To reduce risk I built one central masking converter in Logback instead of
editing forty places, with unit tests and a scan of test logs for card-number patterns. We released on time, the audit
found no unmasked card numbers, and two other teams reused the component. My rule: the deadline is fixed, scope is
negotiable, and the trade-off is always made explicit."

### Q5 [mid] Tell me about a time you learned a new technology quickly to deliver
tags: behavioural, star, learning, new-technology, upskilling, ownership, nagarro

**The live scenario (functional requirement)**
*Situation:* our project moved from VMs to Kubernetes on AWS, and I had never written a Helm chart or configured HPA.
*Task:* migrate our three services in one sprint with no downtime.

**What the interviewer is really checking**
How you learn (structured, hands-on), how fast you become useful, and whether you share knowledge.

**How I answer it** (120-second answer, point by point)
1. **Learned the minimum first:** two evenings on official docs and a sample app on a local kind cluster; deployments, services, probes, config maps, HPA.
2. **Built one service end to end** before touching the others, with readiness/liveness probes and graceful shutdown.
3. **Asked for an expert review early:** the platform team reviewed my first chart and caught missing resource limits.
4. **Migrated with blue/green:** both environments live, traffic switched at the load balancer, rollback in one step.
5. **Result:** all three services migrated in 8 days; deployment time fell from 40 minutes to 6; zero downtime.
6. **Shared it:** a one-hour session and a chart template the team still uses.

**Trade-offs and what can go wrong**
- Learning everything before starting delays delivery; learning nothing before starting causes incidents. Aim for "enough to build one slice safely".

**Follow-ups to expect**
- *What are you learning now?* -> Have a current answer (for example GenAI integration with Spring AI, or Java 21 virtual threads) and one thing you built with it.

**60-second answer**
"When our project moved to Kubernetes I'd never written a Helm chart. I spent two evenings on the official docs and a
local cluster to learn deployments, probes, config maps and autoscaling. Then I migrated one service end to end and
asked the platform team to review it early, which caught missing resource limits. We migrated with blue-green, so
rollback was one switch. All three services moved in eight days, deployments went from forty minutes to six, with zero
downtime. Afterwards I ran a session for the team and shared the chart template. I learn enough to build one safe slice,
then I get an expert review."

### Q6 [senior] Tell me about a production issue you handled and what you changed afterwards
tags: behavioural, star, production-incident, rca, ownership, postmortem, client-facing, nagarro

**The live scenario (functional requirement)**
*Situation:* on a Monday morning the client's checkout API p99 went from 300 ms to 8 s and orders dropped by 30%.
*Task:* I was on call and the client's operations manager was on the bridge call.

**What the interviewer is really checking**
Calm, structured incident handling, clear client communication, a real root cause, and lasting prevention.

**How I answer it** (120-second answer, point by point)
1. **Stabilise first:** dashboards showed DB connection pool exhaustion; I rolled back the weekend release (the most recent change) within 15 minutes. Latency recovered.
2. **Communicate:** updates to the client every 15 minutes: impact, action taken, next update time. No guessing in public.
3. **Root cause:** the release added a call to a pricing service inside a `@Transactional` method, so each request held a DB connection while waiting on a slow network call.
4. **Fix:** moved the remote call outside the transaction, added a timeout and a circuit breaker, and a test that fails if a transactional method makes HTTP calls (ArchUnit rule).
5. **Prevention:** alert on pool usage above 80% and pending connections, plus canary releases with automatic rollback on p99.
6. **Result:** no repeat in the following 9 months; the blameless postmortem was shared with the client, which increased their trust.

**Trade-offs and what can go wrong**
- Debugging live for an hour before rolling back costs the client money; restore service first, investigate second.
- A postmortem that names a person instead of a process gap discourages honest reporting.

**Follow-ups to expect**
- *How did you know to roll back?* -> The incident started right after the release, and rollback was safe and fast; that's always the first option to consider.
- *What metrics showed the cause?* -> Hikari active connections at max, pending threads rising, pricing-service latency spike.

**60-second answer**
"One Monday the client's checkout p99 jumped from 300 milliseconds to 8 seconds and orders fell 30 percent. I was on
call. Dashboards showed connection-pool exhaustion right after a weekend release, so I rolled back within 15 minutes and
latency recovered. I updated the client every 15 minutes with impact, action and the next update time. The root cause
was a pricing call added inside a transactional method, so connections were held during a slow network call. We moved
the call outside the transaction, added a timeout and a circuit breaker, an ArchUnit rule to catch it in tests, a pool
usage alert and canary releases. It didn't recur, and the client valued the blameless postmortem."
