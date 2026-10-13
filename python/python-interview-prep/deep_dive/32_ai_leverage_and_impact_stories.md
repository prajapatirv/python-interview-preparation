# Deep Dive 32 — Leveraging AI on a Project, and Telling the Customer-Impact Story

> Runnable companion: [`13_system_design_scenarios/04_ai_leverage_and_impact.py`](../13_system_design_scenarios/04_ai_leverage_and_impact.py)
> Related deep dives: [20 — AI-first technologies](20_ai_first_technologies.md) ·
> [28 — Observability](28_observability_distributed_systems.md) ·
> [29 — Capacity scaling](29_capacity_scaling_tps.md) ·
> [27 — Zero-downtime changes](27_zero_downtime_production_changes.md)

## What interviewers are actually probing

Two questions that look behavioural and are actually engineering judgement:

> **A.** *"If you had an AI licence or tool, how would you use it to improve and manage a project?"*
> **B.** *"What have you developed that significantly improved the customer experience?"*

**For (A)** they are *not* looking for enthusiasm or a list of tool names. They're checking whether you'd
pick use cases by **value × feasibility discounted by blast radius**, whether you know the **guardrails**
(data boundaries, review gates, evals, cost, a kill switch), and whether you'd **measure a baseline before
the pilot**. The anti-signal is someone who answers "I'd use Copilot and ChatGPT" and stops, or who claims
a 40% productivity gain with no baseline.

**For (B)** the Result is the only part being graded. "Customers were much happier" is worth nothing;
"p95 checkout latency 4.2s → 0.9s and cart abandonment 23% → 14%, measured over 30 days against a control
cohort" is the answer. The second anti-signal is a story told entirely in "we" — the interviewer is hiring
*you*.

Both questions reward the same underlying habit: **state the number, say how you measured it, and name
what it cost.**

---

## Must-know points

**Question A:**

- Start from **where the team loses hours**, not from where AI is fashionable. Mine it from data you
  already have: PR cycle time, time-to-first-review, escaped defects, MTTR, onboarding time.
- Score candidates on **value × feasibility, discounted by blast radius**. Feasibility usually kills
  things, not value.
- **Start internal and advisory** (a human still approves). A wrong answer should cost 30 seconds of
  reading, not a customer.
- **Guardrails, five categories**: data boundary (PII redaction, no-training contracts), human in the
  loop, **verifiability** (an offline eval suite gating prompt changes in CI), cost/latency, operations
  (kill switch, versioned prompts, traced calls).
- **Treat a prompt as code**: versioned, reviewed, and gated by an eval suite in CI.
- **Measure a baseline BEFORE the pilot**, and kill it loudly if the number didn't move. That credibility
  buys the next pilot.
- The **customer-facing chatbot** is the highest value and the worst risk profile. It needs RAG with
  citations, a scoped refusal policy, an eval gate and a kill switch *before* shipping.

**Question B:**

- **STAR**, with a **number** in the Result, the **measurement window**, and **how** you measured it.
- Use **I** for what you decided and built; credit the team for the rest.
- Name a **decision you made and a thing you deliberately did NOT do** — that's what shows judgement.
- Name **what got worse** (cost, complexity, a new dependency, eventual consistency).
- Have **two stories ready**: one scaling/performance problem you diagnosed, one failure you debugged.

---

## Part A — "How would you use AI on this project?"

### A1. The method (answer with this, not with tool names)

Four beats, about ninety seconds:

1. **Find where the team actually loses time.** Not where AI is exciting — where the hours go. And mine
   it from data you already have: PR cycle time, time-to-first-review, escaped defect count, MTTR,
   onboarding time-to-first-PR, release duration. If you can't name the metric you'd improve, you don't
   have a use case yet.
2. **Score candidates** on value × feasibility, discounted by the blast radius of a wrong answer.
3. **Pilot ONE for a sprint**, with the baseline measured *before* you start.
4. **Keep it only if the number moved.** Kill it loudly if it didn't — that honesty is what buys you the
   next pilot.

The scoring axes, and why these three:

- **VALUE** — hours saved per week, defects prevented, or latency removed. **If you can't state the unit,
  it's not a use case, it's a hope.**
- **FEASIBILITY** — can it ship this quarter, with data you're *allowed* to use, and **can you tell
  whether the output was right?** Feasibility is what kills most ideas, not value.
- **RISK / blast radius** — does a wrong answer annoy an engineer (low), ship a bug (medium), or reach a
  customer unreviewed (high)?

### A2. The ranked list (and what its shape tells you)

| Use case | Value | Feas | Risk | Score | Verdict |
|---|---|---|---|---|---|
| Test generation for untested legacy modules | 5 | 5 | 2 | 22.5 | **PILOT NOW** |
| Code review assistant (first pass) | 4 | 5 | 2 | 18.0 | **PILOT NOW** |
| Incident triage copilot | 5 | 4 | 3 | 16.0 | **PILOT NOW** |
| Documentation / runbook generation | 3 | 5 | 1 | 15.0 | next quarter |
| Semantic log search / NL→query | 4 | 4 | 2 | 14.4 | next quarter |
| Legacy migration assistant (Java→Python) | 5 | 3 | 3 | 12.0 | next quarter |
| Sprint planning / estimate generation | 2 | 4 | 2 | 7.2 | park it |
| **Customer-facing support chatbot** | **5** | 2 | **5** | 6.0 | **NOT YET** |

**The shape is the insight, and this is what to say out loud:**

- **Everything at the top is internal, advisory and easy to verify.** A human still approves, so a wrong
  answer costs thirty seconds of reading. That's not timidity; it's how you get value in the first quarter
  instead of spending it on a governance review.
- **The chatbot scores highest on value and worst overall**, because a confidently wrong answer reaches a
  customer unreviewed. It's not "never" — it's "not first", and it needs real machinery before it ships.
- **"AI writes the sprint plan" scoring badly is the correct answer.** Estimates don't become accurate
  because a model wrote them. Being willing to say an AI use case is *bad* is a strong signal.

### A3. What I'd pilot first, concretely

**Test generation for the untested modules that cause the most incidents.** Why this one:

- **The value is measurable** — coverage on those specific modules, and then escaped defects, which is the
  metric that actually matters.
- **The output is trivially verifiable** — the test either passes or fails, and you can check it's testing
  something real by running it against a deliberately broken version.
- **The blast radius is tiny** — a bad generated test is caught in review or by CI.
- **It attacks real pain** — nobody enjoys writing tests for legacy code, which is exactly why that code
  is untested.

The guardrails for this one specifically:

```
1. A generated test must FAIL against a deliberately broken version of the code.
   Otherwise you've generated a test that asserts nothing, and coverage goes up while
   quality doesn't. This is the single most important rule here.
2. Never commit a test the author cannot explain. If you can't say what it protects,
   it's a future flaky test somebody will delete.
3. Coverage is the PROXY. Escaped defects are the metric. Report both, and expect
   coverage to move first.
```

**The runner-up is the incident triage copilot**, and it's worth mentioning because the metric is MTTR —
a number leadership already cares about. Its guardrail is that it's **read-only** and **every claim must
cite the log line or span it came from**, so an engineer can verify in seconds rather than trusting it.

### A4. The guardrails (the part that separates "used AI" from "shipped AI")

**Data boundary**

- What leaves our network, to which provider, under which contract?
- Is PII redacted **before** the call, not after? **Test the redactor** — one forgotten
  `log.debug(request.json())` equivalent is a compliance incident.
- Is the provider contractually barred from training on our data? Get it in writing.
- **Is source code allowed to leave at all?** Many banks and insurers say no. Check *first* — that single
  constraint eliminates most of the table above, and knowing to ask shows you've worked somewhere real.

**Human in the loop**

- What's the blast radius of a confidently wrong answer?
- Who approves before it reaches a customer, a production branch, or a database?
- Is the step **advisory** (suggests) or **authoritative** (acts)? **Start advisory, always.** Earning the
  right to be authoritative requires the eval suite below.

**Verifiability** — the one people skip, and the one that decides whether this survives contact with
production

- How do I know the output was right? **If I can't tell, I can't ship it.**
- Is there an **offline eval set with a pass threshold**, versioned like code?
- **Does a prompt change run that eval in CI before merge?** A prompt is code: it changes behaviour, so it
  needs review and a regression gate. Teams that edit prompts in a web console have no idea whether
  yesterday's fix broke last week's fix.
- Are outputs **grounded in retrieved sources with citations**, so a human can check cheaply?

**Cost and latency**

- Cost per call × calls per day — is that a line item someone approved?
- Is there a **cache** for repeated or semantically similar prompts? (See
  [`10_genai_llm_patterns/`](../10_genai_llm_patterns/).)
- Is the **smallest model that passes the eval** the one in production? Model choice is a cost decision
  gated by the eval, not a preference.
- What's the p99 added latency, and is there a **timeout plus a fallback** when it's exceeded?

**Operations**

- A **kill switch** (a feature flag) to turn it off in seconds without a deploy — the same requirement as
  any risky change ([27](27_zero_downtime_production_changes.md)).
- Prompts, model versions and eval results **versioned and auditable**.
- Every AI call **traced and metered** like any other dependency ([28](28_observability_distributed_systems.md)).
- What happens during a provider outage — degrade, or fail? An LLM is a third-party dependency with a rate
  limit, so it needs a timeout, a circuit breaker and a fallback, exactly like the payment gateway in
  [29](29_capacity_scaling_tps.md).

### A5. The measurement (because "it felt faster" is not a result)

One quarter, one pilot, measured before and after:

| Metric | Before | After | Change | How measured |
|---|---|---|---|---|
| PR review wait time | 9h | 2.5h | −72% | median PR open → first review, 8 weeks |
| Defects escaping to QA | 14/sprint | 8/sprint | −43% | Jira bugs tagged *escaped*, 6 sprints |
| Coverage on the 5 worst modules | 22% | 71% | +223% | `pytest --cov`, same 5 modules |
| MTTR for P2 incidents | 48min | 31min | −35% | PagerDuty ack → resolve, 20 incidents |
| Onboarding to first merged PR | 9 days | 4 days | −56% | last 6 joiners vs previous 6 |
| **AI spend** | **$0** | **$340/mo** | new | provider billing; approved budget $500 |

Stated as a business case: roughly 78 engineer-hours a month recovered for $340, **and** the two numbers
that matter to the customer — escaped defects and MTTR — both improved.

**Three things about this table that matter more than the numbers:**

1. **The cost row is included.** A productivity claim with no cost line is a sales pitch.
2. **Each row names its measurement method and window.** That's what makes it checkable.
3. **The trap to avoid is claiming a number with no baseline.** If you didn't measure before, say *"I
   didn't measure that, and that's what I'd do differently."* That answer scores **higher** than an
   invented 40%, because the interviewer has heard the invented 40% many times.

### A6. "How would you manage the project with AI?" — the second half of the question

Often the question is about *managing*, not just coding. The honest answer is narrower than people expect:

**What AI genuinely helps with:**

- **Summarising for the right audience** — turning a technical incident into a stakeholder update, or a
  long thread into a decision record. Low risk, real time saved.
- **Keeping documentation current** as a scheduled job that opens a PR (never pushes).
- **Triage and routing** — classifying incoming bugs, finding duplicate tickets, surfacing the three
  similar past incidents.
- **Reviewing for consistency** — "does this PR follow our error-handling conventions?" is a question a
  model answers well against a written convention.
- **Drafting** — a design-doc skeleton, a postmortem template filled from the incident timeline, a release
  note from the merged PRs.

**What it does not help with, and saying so is the credibility move:**

- **Estimates don't get more accurate.** The uncertainty is in the work, not in the writing-down.
- **Prioritisation is a judgement about value and risk** that needs context no model has.
- **Architecture decisions** need the constraints that live in people's heads and in last year's incidents.
- **Anything requiring accountability.** A model cannot be accountable for a decision, so a human owns
  every output that matters.

The framing to offer: **AI compresses the time spent on the artefacts around the work** — summaries,
docs, first-pass reviews, triage — **not the judgement inside it.** That's a smaller claim than the hype,
and it's the one that survives a sceptical follow-up.

---

## Part B — "What did you build that improved the customer experience?"

### B1. The format, and the two fatal failure modes

**STAR**: Situation, Task, Action, Result. But the Result is the only part being graded, and there are two
ways to fail fatally:

**1. No number in the Result.** "Customers were much happier" tells the interviewer nothing and signals
you never measured. Compare:

```
WEAK:   "We made checkout much faster and customers were happier."
STRONG: "p95 checkout latency went from 4.2s to 0.9s and cart abandonment from 23% to 14%,
         measured over 30 days against a control cohort."
```

**2. All "we", no "I".** The interviewer is hiring *you*. Say what **you** decided, built and owned, then
credit the team for the rest. "I did the tracing and wrote the cache layer; a teammate built the consumer
against the contract I specified" is both honest and specific.

The companion file encodes this as a `validate()` method that **refuses** a story with no measured result
— which is a useful forcing function when you're preparing.

### B2. A complete worked story

```
SITUATION
  Checkout p95 was 4.2s and cart abandonment sat at 23%. Support's top complaint was
  "the order page spins". Nobody had profiled it in a year.

TASK
  Own the latency problem end to end: p95 under 1s, no rewrite, one quarter, no extra
  infrastructure budget.

ACTION
  - Traced one real checkout request instead of guessing, and found 5 of the 7 database
    calls were an N+1 over order items. Only ~30ms of the 4.2s was our own CPU; the rest
    was waiting.
  - Replaced the N+1 with a single JOIN, and cached the customer/pricing lookup in Redis
    with a 60s TTL plus stampede protection, measuring the hit ratio before trusting it.
  - Moved the confirmation email and the analytics event out of the request path onto a
    Kafka topic with an idempotent consumer, so the customer stops waiting for work they
    never see.
  - Chose NOT to add a read replica, because the trace showed writes were the constraint —
    a replica would have added cost and operational surface for nothing.
  - Shipped behind a feature flag at 5% traffic, compared p95 against a control group for
    48 hours, then ramped.

RESULT
  - checkout p95:            4.2s  -> 0.9s   (-79%)   APM, 30-day window, same traffic mix
  - cart abandonment:        23%   -> 14%    (-39%)   analytics funnel, flagged cohort vs control
  - DB read QPS:             1800  -> 240    (-87%)   RDS Performance Insights (87% cache hit)
  - support tickets, "slow": 40/wk -> 3/wk   (-92%)   Zendesk tag count
  - infrastructure cost:     100%  -> 96%             the queue cost less than the pods it removed

MY PART
  I did the tracing and the diagnosis, wrote the JOIN and the cache layer including the
  stampede lock, and designed the async offload. A teammate built the Kafka consumer against
  the contract I specified; our SRE reviewed the rollout plan.

LEARNED
  I spent the first week optimising the wrong thing — the Python code — because I trusted a
  hunch over a trace. Now I won't touch performance work without a profile in front of me,
  and I write the before-number down before I change anything, because otherwise you can't
  prove the after-number.
```

### B3. Why that story works — the five things to copy

1. **The Result has five metrics across three categories**: technical (p95, QPS), business (abandonment),
   and operational (support tickets, cost). The business number is what a non-engineer remembers; the
   technical number is what an engineer believes.
2. **Every metric names its measurement method and window.** "Measured against a control cohort" is the
   phrase that makes the abandonment number credible rather than coincidental — otherwise a sceptic
   rightly asks whether a marketing campaign changed the traffic mix.
3. **There's a decision you did NOT make.** "I chose not to add a read replica, because the trace showed
   writes were the constraint" demonstrates judgement far better than a list of things you built. Every
   strong story has one of these.
4. **The cost is named**, and in this case it improved — but if it had gone up, say so. A story where
   nothing got worse reads as incomplete, because something always does.
5. **The lesson is a real mistake with a changed behaviour.** "I optimised on a hunch for a week" is
   specific and slightly uncomfortable, which is exactly why it's believable. "I learned the importance of
   teamwork" is not a lesson.

### B4. The metrics that make a customer-impact story land

Pick the two or three you actually moved, and know how each was measured:

| Metric | What it is | Why it lands |
|---|---|---|
| **Latency** | p50/p95/p99 of the flow the customer **waits on** | name the flow ("checkout"), not the service |
| **Reliability** | error rate, successful-checkout rate, SLO attainment | the customer-visible version of "it works" |
| **Abandonment / conversion** | funnel drop-off at the step you fixed | the closest thing to money |
| **Support load** | tickets per week on that complaint | nothing is more concrete than "the complaint stopped arriving" |
| **Time-to-value** | time until the customer gets what they came for | first report generated, first order shipped, onboarding done |

**Two sentences that improve any of them:**

- *"I wrote the before-number down first."* → proves you measured rather than remembered.
- *"I also checked what got worse."* → cost, complexity, a p99 tail, a new dependency, eventual
  consistency. Senior engineers name the price.

### B5. If you don't have a dramatic story

Most work isn't a 5× latency win, and pretending otherwise is transparent. Three honest alternatives that
score well:

- **A small fix with a sharp number.** "A validation error said *'invalid input'* with no field name. I
  made it name the field and the constraint. Support tickets on that endpoint went from 12 a week to 1."
  Small scope, real measurement, visible care about the user.
- **A reliability story.** "We were losing roughly 0.3% of webhook deliveries to transient failures. I
  added a retry topic with exponential backoff and a DLQ with replay. Delivery went to 99.98% and we
  stopped getting 'we never received your callback' tickets." Nobody notices reliability until it's
  missing — which is the point.
- **An internal-customer story.** If your users are other engineers, say so and measure it: "our
  deployment took 40 minutes and blocked the team; I parallelised the test suite and got it to 8, so we
  went from one release a week to daily." Internal customers count, as long as you measure the same way.

And if you genuinely didn't measure: **say that, and say what you'd measure now.** It's a far better
answer than an invented percentage, and it's the same principle as A5.

---

## Hands-on drills

1. Run the companion. Re-score `USE_CASES` for a company that forbids source code leaving the network
   (`feasibility=1` on everything that reads the repo). Notice which survive — that constraint is real at
   most banks.
2. Add a `UseCase` for your own current project, honestly scored. If you can't fill in `unit_of_value`,
   you've found the weakness in the idea.
3. Write the guardrail answers for that use case. The one to labour over is **"how do I know the output
   was right?"**
4. Write your **two** STAR stories — one performance problem you diagnosed, one failure you debugged — and
   make `validate()` return an empty list for both. It won't pass until you've found real before and after
   numbers, which is the work you should do *before* the interview.
5. For each story, find the **decision you did NOT make** and write it as one sentence.
6. For each story, find **what got worse** and write it as one sentence.
7. Go and find a real before-number you never recorded: dig through an old dashboard, a Jira ticket, a
   support queue, a git log. If it genuinely isn't there, write the sentence you'd say instead.
8. Practise the Result paragraph out loud, timed. If the numbers aren't in the first fifteen seconds,
   restructure it.

---

## The 60-second spoken answers

**A — the AI question:**

> "I'd start from where the team loses hours, not from the tool. In our case that's review latency, flaky
> legacy coverage and incident triage. So I'd score candidates on value times feasibility, discounted by
> the blast radius of a wrong answer, and I'd deliberately start with internal, advisory use cases where a
> human still approves: an AI first-pass PR reviewer, test generation for the untested modules that cause
> the most incidents, and an incident-triage copilot that summarises the last hour of logs, traces and
> deploys and cites its evidence.
>
> The guardrails are the real work. Nothing leaves the network without PII redaction I've actually tested
> — and I'd check first whether source code is allowed to leave at all, because at a lot of firms it
> isn't. No AI step is authoritative: it proposes, a human acts. Prompts and model versions are versioned
> like code, with an offline eval suite gating changes in CI, because a prompt change is a behaviour
> change. Every call is traced and cost-metered like any other dependency, with a timeout and a fallback,
> and there's a feature flag to kill it in seconds.
>
> Then I'd pilot ONE for a sprint with the baseline measured first. On ours, median time to first review
> went from 9 hours to 2.5, escaped defects from 14 to 8 a sprint and MTTR from 48 to 31 minutes, for
> $340 a month. If those numbers hadn't moved I'd have said so and killed it — that honesty is what buys
> credibility for the next pilot. And the thing I'd avoid is claiming a productivity number with no
> baseline; if I didn't measure it, I'd say so.
>
> The one I would *not* start with is a customer-facing chatbot. Highest value, worst risk profile: a
> confidently wrong answer reaches a customer unreviewed. That needs retrieval grounded in approved docs
> with citations, a hard refusal policy with human handoff, and a regression eval gate — before it ships,
> not after.
>
> And on managing the project with it: AI compresses the artefacts around the work — summaries,
> documentation, first-pass review, ticket triage — not the judgement inside it. Estimates don't get more
> accurate because a model wrote them."

**B — the customer-impact question:**

> "Checkout p95 was 4.2 seconds and cart abandonment was 23%; support's top complaint was that the order
> page spins. I traced a real request instead of guessing and found an N+1 — five queries per order where
> one JOIN would do — plus a confirmation email and an analytics write sitting in the request path. Only
> about 30 milliseconds of the 4.2 seconds was our own CPU; the rest was waiting.
>
> I replaced the N+1, cached the pricing lookup with stampede protection, and moved the email and the
> analytics event onto Kafka with an idempotent consumer. I deliberately did *not* add a read replica,
> because the trace showed writes were the constraint — it would have added cost and operational surface
> for nothing. We shipped behind a flag at 5% and compared p95 against a control cohort for 48 hours
> before ramping.
>
> p95 went from 4.2s to 0.9s; abandonment from 23% to 14% over 30 days against the control; DB read QPS
> from 1,800 to 240; and support tickets about slow checkout from about 40 a week to 3. Cost went slightly
> *down*, because the queue was cheaper than the pods it let us remove.
>
> My part specifically was the tracing, the JOIN and the cache layer including the stampede lock, and the
> design of the async offload; a teammate built the Kafka consumer against the contract I specified.
>
> What I'd do differently: I spent the first week optimising Python code on a hunch. I don't touch
> performance work now without a trace in front of me, and I write the before-number down before I change
> anything — because otherwise you can't prove the after-number."
