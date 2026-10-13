---
id: 20-lead-behavioral
title: Lead / Technical Leadership & Behavioral Questions
focus: Team lead (4+ yrs) - delivery, mentoring, estimation, stakeholder management, conflict
---
Use STAR with numbers. Keep each story to ~2 minutes and prepare 6-8 stories you can bend to many questions: a production incident, a conflict, a mentoring win, a failed decision, a delivery under pressure, a technical migration, an improvement you drove, a disagreement with a client.

### Q1 [basic] Tell me about yourself (90-second version).
Structure: current role and scale -> core strengths -> 2 proof points -> why this role. Example frame: "12+ years in Java, last 4+ leading teams at Cybage; I design and deliver Spring Boot/Quarkus services, event-driven pipelines on Kafka and AWS, and I lead code reviews, mentoring and client communication. Recently I built [X] and cut [Y]. I'm looking for a Lead role where I own architecture and delivery for [Z]."

### Q2 [basic] What does a Lead Java developer do beyond coding?
Owns technical design and quality, breaks down work, estimates, unblocks the team, reviews code, mentors, interfaces with product/clients, manages risk and tech debt, ensures operability (monitoring, runbooks) and keeps delivery predictable. Still codes, but multiplies the team's output.

### Q3 [intermediate] How do you estimate and plan a feature?
Clarify requirements and acceptance criteria -> split into small slices -> identify risks/unknowns (spike) -> estimate with the team (relative points or ranges, not single numbers) -> add buffer for review, testing and deployment -> track via burn-down and revise early. Be explicit about assumptions and communicate changes quickly.

### Q4 [intermediate] How do you handle a team member who is underperforming?
Understand the cause first (skill gap, unclear expectations, personal issues, motivation) in a private 1:1, set clear specific goals and a short feedback loop, pair programming/mentoring, adjust task difficulty, document progress, involve the manager if there is no improvement. Be fair, concrete, and supportive.

### Q5 [intermediate] How do you mentor juniors?
Pair on real tasks, give small scoped stories with growing difficulty, code reviews that explain why, guided design discussions, learning goals each quarter, brown-bag sessions, and let them present their work. Measure growth by independence and quality of PRs.

### Q6 [intermediate] How do you run effective code reviews in a team?
Small PRs, a checklist (correctness, tests, security, performance, readability), review within 24 hours, comment on code not people, distinguish blocking vs optional comments, automate style, rotate reviewers to share knowledge, and track review turnaround time.

### Q7 [intermediate] Tell me about a conflict with a teammate/stakeholder and how you resolved it.
Frame: facts -> perspectives -> shared goal -> options with trade-offs -> decision criteria (data) -> agreement and follow-up. Show empathy, keep it professional, and end with the outcome and what you learned.

### Q8 [intermediate] How do you handle unclear or changing requirements?
Clarify with questions and examples, write down assumptions, deliver in increments with frequent demos (you ran weekly demos), prefer reversible decisions, use feature flags, keep the backlog visible, and escalate impact on scope/timeline early.

### Q9 [intermediate] How do you handle tight deadlines without sacrificing quality?
Negotiate scope (MVP vs nice-to-have), cut work not quality (tests and monitoring stay), prioritise by risk, parallelise with clear interfaces, add temporary capacity only if it helps, and record deliberate shortcuts as tracked tech debt with a payback plan.

### Q10 [intermediate] How do you communicate with clients and stakeholders?
Daily/weekly updates in plain language: progress, risks, decisions needed. Weekly demos, a shared status doc, early bad news with options, written follow-up after calls, and translating technical constraints into business impact.

### Q11 [intermediate] Describe a technical decision you made with trade-offs.
Pick a real case (e.g. choosing Quarkus + Picocli for parsers, Kafka vs RabbitMQ, expand/contract migration). Present options, criteria (performance, team skills, cost, risk), the decision, the outcome and what you would change.

### Q12 [intermediate] How do you drive engineering best practices in the team?
Lightweight standards (definition of done, coding guidelines, ADRs), automate with CI quality gates and templates, lead by example, run retros to improve one thing per sprint, share learnings (tech talks), and measure outcomes (defects, cycle time, incident count).

### Q13 [intermediate] How do you manage on-call and production support in the team?
Rotation with clear escalation, runbooks, alert quality reviews, blameless post-incident reviews, a support-vs-feature capacity split, and fixing top recurring causes so on-call load shrinks over time.

### Q14 [intermediate] How do you keep up with technology and bring it into the team?
Follow release notes (Java 25, Spring Boot 4, Kafka 4), try small spikes, evaluate against real problems, run a short proof of concept with success criteria, document findings, and adopt gradually. Mention structured learning (Claude Code certifications, Copilot, Bedrock).

### Q15 [intermediate] How do you handle disagreement with your manager or architect?
Seek to understand their constraints, bring data and options, propose a small experiment, disagree and commit once the decision is made, and document the rationale. Escalate only for risks to safety, security or compliance.

### Q16 [intermediate] What is your biggest weakness / area to improve?
Pick a real, non-fatal one with a concrete plan: e.g. "Observability stack breadth (Prometheus/Grafana/Splunk) - I know the concepts from Datadog/CloudWatch and I'm building hands-on labs", or "NoSQL depth - I'm modelling a service on Couchbase". Show progress, not excuses.

### Q17 [intermediate] Why are you leaving your current company / why this role?
Positive framing: growth in scope (architecture ownership), new domain/scale, modern stack, learning. Never criticise the employer. Tie to what the new company needs and what you bring.

### Q18 [intermediate] What are your achievements you are proudest of?
Prepare 3 with numbers: automation that saved hours/week, a migration delivered with zero downtime, the Ops Master Agent hackathon win delivered to leadership, mentoring that produced promotions, reduced incident count after logging/alerting improvements.

### Q19 [design] How would you set up a new team of 6 for a new product?
Define the mission and boundaries, split ownership by components/domains, agree working agreements (branching, reviews, DoD), set up the golden-path repo (CI/CD, observability, security), pick the first thin vertical slice to prove the pipeline, ADRs for key decisions, onboarding guide, and a metrics dashboard (lead time, deploy frequency, change failure rate, MTTR).

### Q20 [design] How do you balance feature delivery with technical debt and platform work?
Reserve capacity (e.g. 20%), link debt items to measurable pain (incidents, slow builds), bundle debt work into related features, keep a visible roadmap, and report the effect (e.g. build time down 40%, incidents halved) to justify continued investment.

### Q21 [intermediate] Which metrics do you track as a Lead?
DORA: deployment frequency, lead time for changes, change failure rate, time to restore. Plus: PR turnaround, defect escape rate, test flakiness, on-call load, sprint predictability, team health (survey). Use them to improve the system, not to rank people.

### Q22 [intermediate] Questions you should ask the interviewer.
How is the team structured and what does the Lead own? What is the deployment frequency and incident process? What does the tech roadmap look like (Java/Spring upgrades, cloud)? How is technical debt handled? What does success look like in the first 6 months?

### Q23 [design] Design an onboarding and growth plan for a new junior engineer and a new senior engineer joining your team.
Junior: a buddy, a small first PR in week one, a curated reading path, pairing, and a 30/60/90 plan with clear expectations. Senior: context on domain and architecture, ownership of one bounded area, early involvement in design reviews, and a goal to improve a team practice. For both, set a feedback rhythm (weekly 1:1), measure time to first deploy, and document what was unclear so onboarding improves. Failure mode: leaving people to 'figure it out' and finding problems at the 3-month review.
