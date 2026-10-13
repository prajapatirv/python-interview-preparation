"""
Two behavioural questions that are really engineering questions, and the structure for answering
both well:

  A. "If you had an AI licence/tool, how would you use it to improve and manage a project?"
  B. "What have you built that measurably improved the customer experience?"

Interviewers are not looking for enthusiasm. For (A) they want to hear that you'd pick use cases
by VALUE x FEASIBILITY, that you know the guardrails (data boundaries, review gates, evals, cost),
and that you'd measure the before/after rather than assert it. For (B) they want STAR with a
NUMBER in the Result -- and the number is the whole answer.

So this file is a thinking tool, not a lecture:
  - a use-case scorecard that ranks AI opportunities and tells you what to pilot first
  - the guardrail checklist as code (what must be true before each one ships)
  - a before/after metrics model so the claim is arithmetic, not opinion
  - a STAR story builder that refuses to accept a story with no measured result
  - two worked STAR stories: one that passes validation, one that deliberately doesn't

Pure stdlib. Run me: python 04_ai_leverage_and_impact.py
"""
from dataclasses import dataclass, field


def section(title):
    print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


# ================================================================ A. the use-case scorecard
@dataclass
class UseCase:
    """One candidate way to apply an AI tool to a project.

    The two axes that matter, and why:
      VALUE       -- hours saved per week, or defects prevented, or latency removed. If you cannot
                     state the unit, it is not a use case, it is a hope.
      FEASIBILITY -- can it ship this quarter, with the data you are allowed to use, and can you
                     TELL whether its output was right? Feasibility is usually what kills things,
                     not value.
    RISK is the tiebreaker, and it is mostly about blast radius: does a wrong answer annoy an
    engineer (low), ship a bug (medium), or reach a customer unreviewed (high)?
    """
    name: str
    description: str
    value: int           # 1-5: hours/week saved or quality gained
    feasibility: int     # 1-5: can we ship it this quarter, with data we're allowed to use
    risk: int            # 1-5: blast radius of a wrong output (5 = reaches customers unreviewed)
    unit_of_value: str
    guardrails: list = field(default_factory=list)

    @property
    def score(self):
        """value x feasibility, discounted by risk. Deliberately simple -- the point of a score is
        to force the conversation, not to be precise."""
        return round(self.value * self.feasibility * (1 - 0.1 * (self.risk - 1)), 1)

    @property
    def verdict(self):
        if self.risk >= 4 and self.feasibility < 4:
            return "NOT YET -- high blast radius, not yet verifiable"
        if self.score >= 16:
            return "PILOT NOW"
        if self.score >= 9:
            return "NEXT QUARTER"
        return "PARK IT"


USE_CASES = [
    UseCase(
        "Code review assistant (first pass)",
        "AI reviews every PR before a human does: naming, missing tests, obvious bugs, "
        "unhandled errors. A human still approves.",
        value=4, feasibility=5, risk=2,
        unit_of_value="reviewer-hours/week + defects caught earlier",
        guardrails=["advisory only -- it can never approve a PR",
                    "runs on the diff, not the whole repo",
                    "a human is still the required approver"],
    ),
    UseCase(
        "Test generation for untested legacy modules",
        "Point it at a module with 20% coverage and have it draft the table-driven cases; "
        "an engineer reviews, fixes and keeps what's real.",
        value=5, feasibility=5, risk=2,
        unit_of_value="coverage % on the modules that cause the most incidents",
        guardrails=["generated tests must FAIL first against a deliberately broken version",
                    "never commit a test the author cannot explain",
                    "coverage is the proxy; escaped defects are the actual metric"],
    ),
    UseCase(
        "Incident triage copilot",
        "On a page, it summarises the last hour of logs/traces/deploys and proposes the 3 most "
        "likely causes with the evidence for each.",
        value=5, feasibility=4, risk=3,
        unit_of_value="MTTR (mean time to resolve), minutes",
        guardrails=["read-only access -- it proposes, the engineer acts",
                    "every claim must cite the log line or span it came from",
                    "no customer PII in the prompt; redact before sending"],
    ),
    UseCase(
        "Documentation and runbook generation",
        "Keep service READMEs, API docs and runbooks current from the code and the last 10 "
        "incidents, as a scheduled job that opens a PR.",
        value=3, feasibility=5, risk=1,
        unit_of_value="onboarding days-to-first-PR; stale-runbook incidents",
        guardrails=["opens a PR, never pushes", "an owner reviews before merge"],
    ),
    UseCase(
        "Legacy migration assistant (Java -> Python)",
        "Translate a module, generate the equivalence tests, and diff behaviour against the "
        "original on recorded production inputs.",
        value=5, feasibility=3, risk=3,
        unit_of_value="migration weeks saved per service",
        guardrails=["differential testing against the old system on real recorded inputs",
                    "shadow traffic before any cutover",
                    "no cutover without a rollback that was actually rehearsed"],
    ),
    UseCase(
        "Customer-facing support chatbot",
        "Answers billing and order questions directly to customers, in the product.",
        value=5, feasibility=2, risk=5,
        unit_of_value="support ticket deflection %",
        guardrails=["RAG grounded ONLY in approved policy docs, with citations",
                    "hard refusal + human handoff outside the approved scope",
                    "no account data in the prompt without an authenticated, scoped lookup",
                    "offline eval suite with a regression gate before every prompt change",
                    "a kill switch, and logging of every answer for audit"],
    ),
    UseCase(
        "Sprint planning / estimate generation",
        "Generates story breakdowns and estimates from a ticket description.",
        value=2, feasibility=4, risk=2,
        unit_of_value="planning hours (and nothing else -- estimates don't get more accurate)",
        guardrails=["a draft for the team to edit, never the committed plan"],
    ),
    UseCase(
        "Semantic log search / NL to query",
        "Ask 'why did checkout fail for customer X at 14:30' and get the query, the trace and "
        "the matching log lines.",
        value=4, feasibility=4, risk=2,
        unit_of_value="minutes to first hypothesis during an incident",
        guardrails=["read-only query generation; the engineer runs it",
                    "scoped to the services the asker already has access to"],
    ),
]


# ================================================================ the guardrails
GUARDRAIL_CHECKLIST = {
    "Data boundary": [
        "What leaves our network, and to which provider under which contract?",
        "Is customer PII redacted BEFORE the call, not after? (Test the redactor.)",
        "Is the provider contractually barred from training on our data? Get it in writing.",
        "Is source code allowed to leave at all? Many enterprises say no -- check first.",
    ],
    "Human in the loop": [
        "What is the blast radius of a confidently wrong answer?",
        "Who approves before it reaches a customer, a production branch or a database?",
        "Is the AI step ADVISORY (suggests) or AUTHORITATIVE (acts)? Start advisory, always.",
    ],
    "Verifiability": [
        "How do I know the output was right? If I cannot tell, I cannot ship it.",
        "Is there an offline eval set with a pass threshold, versioned like code?",
        "Does a prompt change run that eval in CI before merge? (It is a code change.)",
        "Are outputs grounded in retrieved sources WITH citations, so a human can check?",
    ],
    "Cost and latency": [
        "Cost per call x calls per day -- is that a line item someone approved?",
        "Is there a cache for repeated/similar prompts? (Semantic caching, see 10_genai_llm_patterns/)",
        "Is the smallest model that passes the eval the one in production?",
        "What is the p99 added latency, and is there a timeout + fallback when it is exceeded?",
    ],
    "Operations": [
        "Is there a kill switch (a feature flag) to turn it off in seconds without a deploy?",
        "Are prompts, model versions and eval results versioned and auditable?",
        "Is every AI call traced and metered like any other dependency?",
        "What happens when the provider has an outage -- degrade, or fail?",
    ],
}


# ================================================================ before/after measurement
@dataclass
class Improvement:
    """A claimed improvement, stated as arithmetic. If you cannot fill in `before` and `after`,
    you do not have a result -- you have an anecdote."""
    metric: str
    before: float
    after: float
    unit: str
    how_measured: str

    @property
    def delta_pct(self):
        if self.before == 0:
            return float("inf")
        return (self.after - self.before) / self.before * 100

    def line(self):
        if self.before == 0:
            change = "new"
        else:
            direction = "down" if self.after < self.before else "up"
            change = f"{direction} {abs(self.delta_pct):.0f}%"
        return (f"{self.metric}: {self.before:g}{self.unit} -> {self.after:g}{self.unit} "
                f"({change})  [{self.how_measured}]")


AI_PILOT_RESULTS = [
    Improvement("PR review wait time", 9.0, 2.5, "h", "median PR open -> first review, 8 weeks"),
    Improvement("Defects escaping to QA", 14, 8, "/sprint", "Jira bugs labelled escaped, 6 sprints"),
    Improvement("Coverage on the 5 worst modules", 22, 71, "%", "pytest --cov, same 5 modules"),
    Improvement("MTTR for P2 incidents", 48, 31, "min", "PagerDuty ack -> resolve, 20 incidents"),
    Improvement("Onboarding to first merged PR", 9, 4, "days", "last 6 joiners vs previous 6"),
    Improvement("AI spend", 0, 340, "$/mo", "provider billing; approved budget $500"),
]


# ================================================================ B. the STAR story builder
@dataclass
class STARStory:
    """The answer format for "what did you build that made customers happy?".

    The two failure modes, both fatal:
      1. NO NUMBER in the Result. "Customers were much happier" is worth nothing. "p95 checkout
         latency 4.2s -> 0.9s, cart abandonment 23% -> 14%, measured over 30 days" is the answer.
      2. ALL "WE". Interviewers are hiring YOU. Say what you personally decided, built and owned,
         then credit the team for the rest.
    """
    situation: str
    task: str
    action: list
    result: list              # list[Improvement] -- enforced, not optional
    your_specific_role: str
    what_you_learned: str

    def validate(self):
        problems = []
        if not self.result:
            problems.append("NO MEASURED RESULT -- this is not yet an answer, it is an anecdote")
        if not self.your_specific_role:
            problems.append("no first-person ownership -- 'we' stories don't get offers")
        if len(self.action) < 2:
            problems.append("the Action should show a decision and a trade-off, not just a task")
        if not self.what_you_learned:
            problems.append("no reflection -- the follow-up question is always 'what would you "
                            "do differently?'")
        return problems

    def tell(self):
        out = [f"  SITUATION: {self.situation}", f"  TASK:      {self.task}", "  ACTION:"]
        out += [f"    - {a}" for a in self.action]
        out.append("  RESULT:")
        out += [f"    - {r.line()}" for r in self.result]
        out.append(f"  MY PART:   {self.your_specific_role}")
        out.append(f"  LEARNED:   {self.what_you_learned}")
        return "\n".join(out)


STORY_CHECKOUT = STARStory(
    situation="Checkout p95 was 4.2s and cart abandonment sat at 23%. Support's top complaint "
              "was 'the order page spins'. Nobody had profiled it in a year.",
    task="Own the latency problem end to end and get p95 under 1s without a rewrite, in one "
         "quarter, with no extra infrastructure budget.",
    action=[
        "Traced one real checkout request first instead of guessing, and found 5 of the 7 "
        "database calls were an N+1 over order items -- 30ms of the 4.2s was our code, the rest "
        "was waiting",
        "Replaced the N+1 with a single JOIN, and cached the customer/pricing lookup in Redis "
        "with a 60s TTL plus stampede protection, measuring the hit ratio before trusting it",
        "Moved the confirmation email and the analytics event out of the request path onto a "
        "Kafka topic with an idempotent consumer, so the customer stops waiting for work they "
        "don't need to see",
        "Chose NOT to introduce a read replica, because the trace showed the writes were the "
        "constraint -- a replica would have added cost and operational surface for nothing",
        "Shipped behind a feature flag at 5% traffic, compared p95 against the control group "
        "for 48h, then ramped",
    ],
    result=[
        Improvement("checkout p95", 4.2, 0.9, "s", "APM, 30-day window, same traffic mix"),
        Improvement("cart abandonment", 23, 14, "%", "analytics funnel, 30 days, flagged cohort "
                                                     "vs control"),
        Improvement("DB read QPS", 1800, 240, "qps", "RDS Performance Insights (87% cache hit)"),
        Improvement("support tickets about slow checkout", 40, 3, "/week", "Zendesk tag count"),
        Improvement("infrastructure cost", 100, 96, "% of baseline", "the queue cost less than "
                                                                    "the pods it removed"),
    ],
    your_specific_role="I did the tracing and the diagnosis, wrote the JOIN and the cache layer "
                       "including the stampede lock, and designed the async offload. A teammate "
                       "built the Kafka consumer against the contract I specified; our SRE "
                       "reviewed the rollout plan.",
    what_you_learned="I spent the first week optimising the wrong thing -- the Python code -- "
                     "because I trusted a hunch over a trace. Now I will not touch performance "
                     "work without a profile or a trace in front of me, and I write the "
                     "before-number down before I change anything, because otherwise you cannot "
                     "prove the after-number.",
)

STORY_WEAK = STARStory(
    situation="The API was slow.",
    task="Make it faster.",
    action=["We added caching."],
    result=[],
    your_specific_role="",
    what_you_learned="",
)


if __name__ == "__main__":
    section("A. 'You have an AI licence -- how would you use it on this project?'")
    print("""  Do not answer with a list of tools. Answer with a METHOD, then the ranked list that
  method produces, then the guardrails, then how you'd measure it. Four beats, 90 seconds.

  THE METHOD
    1. Find where the team actually loses time. Not where AI is fashionable -- where the hours go.
       Mine it from data you already have: PR cycle time, time-to-first-review, escaped defect
       count, MTTR, onboarding time, how long a release takes.
    2. Score each candidate on VALUE x FEASIBILITY, discounted by the blast radius of a wrong
       answer. Start where value is high, verification is easy and risk is low.
    3. Pilot ONE for a sprint, with a baseline measured BEFORE you start.
    4. Keep it only if the number moved. Kill it loudly if it didn't -- that credibility is what
       buys you the next pilot.""")

    print("\n  THE RANKED LIST (scored above):\n")
    print(f"    {'use case':44s} {'val':>4s} {'feas':>5s} {'risk':>5s} {'score':>6s}  verdict")
    for uc in sorted(USE_CASES, key=lambda u: -u.score):
        print(f"    {uc.name:44s} {uc.value:4d} {uc.feasibility:5d} {uc.risk:5d} "
              f"{uc.score:6.1f}  {uc.verdict}")

    print("\n  the shape of that table is the insight worth stating out loud:")
    print("    - the top entries are all INTERNAL, ADVISORY and EASY TO VERIFY. A human still")
    print("      approves, so a wrong answer costs 30 seconds of reading.")
    print("    - the customer-facing chatbot scores highest on VALUE and lowest overall, because")
    print("      a confidently wrong answer reaches a customer unreviewed. That one needs RAG")
    print("      with citations, a scoped refusal policy, an eval gate and a kill switch BEFORE")
    print("      it ships -- not after.")
    print("    - 'AI writes the sprint plan' scores badly and that is the correct answer. Estimates")
    print("      don't become accurate because a model wrote them.")

    print("\n  WHAT I'D PILOT FIRST, and why:")
    top = max(USE_CASES, key=lambda u: u.score)
    print(f"    {top.name} -- {top.description}")
    print(f"    measured in: {top.unit_of_value}")
    for g in top.guardrails:
        print(f"      guardrail: {g}")

    section("the guardrails -- the part that separates 'used AI' from 'shipped AI'")
    for area, questions in GUARDRAIL_CHECKLIST.items():
        print(f"\n  {area}")
        for q in questions:
            print(f"    - {q}")

    section("and the measurement, because 'it felt faster' is not a result")
    print("  one quarter, one pilot, measured before and after:\n")
    for imp in AI_PILOT_RESULTS:
        print(f"    {imp.line()}")
    saved_hours = 6.5 * 12          # reviewer-hours saved/week x engineers, illustrative
    print(f"\n    stated as a business case: ~{saved_hours:.0f} engineer-hours/month recovered "
          f"for $340/month,")
    print("    and the two numbers that actually matter to the customer -- escaped defects and")
    print("    MTTR -- both improved. If they hadn't, the honest answer is to kill the pilot.")
    print("\n    the trap to avoid in this answer: claiming a productivity number with no")
    print("    baseline. If you did not measure before, say 'I did not measure that, and that")
    print("    is what I'd do differently' -- that answer scores higher than an invented 40%.")

    section("B. 'What have you built that made customers measurably happier?'")
    print("  the format is STAR, but the Result is the only part being graded. A number, a")
    print("  measurement window, and how you measured it.\n")
    print(STORY_CHECKOUT.tell())
    print(f"\n  validation: {STORY_CHECKOUT.validate() or 'complete -- ready to tell'}")

    print("\n  the same story told badly, and what the validator says about it:\n")
    print(STORY_WEAK.tell())
    print("\n  validation:")
    for problem in STORY_WEAK.validate():
        print(f"    - {problem}")

    section("the five metrics that make a customer-impact story land")
    print("""  Pick whichever two or three you actually moved, and know how they were measured:

    LATENCY        p50/p95/p99 of the flow the customer waits on. Name the flow, not the service.
    RELIABILITY    error rate, or successful-checkout rate, or SLO attainment.
    ABANDONMENT    funnel drop-off at the step you fixed. The closest thing to money.
    SUPPORT LOAD   tickets per week on that complaint. Nothing is more concrete than "the
                   complaint stopped arriving".
    TIME-TO-VALUE  how long until the customer gets the thing they came for (first report
                   generated, first order shipped, onboarding completed).

  And two sentences that make any of them better:
    "I wrote the before-number down first."   -> proves you measured rather than remembered.
    "I also checked what got WORSE."          -> cost, complexity, a p99 tail, an extra
                                                 dependency. Senior engineers name the price.""")

    section("the 60-second answers")
    print("""  A -- the AI question:
  "I'd start from where the team loses hours, not from the tool. In my case that's review
  latency, flaky legacy coverage and incident triage. So I'd score candidates on value times
  feasibility, discounted by the blast radius of a wrong answer, and I'd deliberately start with
  internal, advisory use cases where a human still approves: an AI first-pass PR reviewer, test
  generation for the untested modules that cause the most incidents, and an incident-triage
  copilot that summarises the last hour of logs, traces and deploys and cites its evidence.

  The guardrails are the real work: nothing leaves the network without PII redaction I've tested,
  no AI step is authoritative -- it proposes, a human acts -- prompts and model versions are
  versioned like code with an offline eval suite gating changes in CI, every call is traced and
  cost-metered, and there's a feature flag to kill it in seconds.

  Then I'd pilot ONE for a sprint with the baseline measured first. On our pilot, median time to
  first review went from 9 hours to 2.5, escaped defects from 14 to 8 a sprint, and MTTR from 48
  to 31 minutes, for $340 a month. If those numbers hadn't moved I'd have said so and killed it --
  that's what buys credibility for the next one.

  The one I would NOT start with is a customer-facing chatbot. Highest value, worst risk profile:
  a confidently wrong answer reaches a customer unreviewed. That needs retrieval grounded in
  approved docs with citations, a hard refusal policy with human handoff, and a regression eval
  gate -- before it ships, not after."

  B -- the customer-impact question:
  "Checkout p95 was 4.2 seconds and cart abandonment was 23%. I traced a real request instead of
  guessing and found an N+1 -- five queries per order where one JOIN would do -- plus a
  confirmation email and an analytics write sitting in the request path. I replaced the N+1,
  cached the pricing lookup with stampede protection, and moved the email and the analytics event
  onto Kafka with an idempotent consumer. I deliberately did NOT add a read replica, because the
  trace showed writes were the constraint. We shipped behind a flag at 5% and compared against a
  control for 48 hours before ramping.

  p95 went from 4.2s to 0.9s, abandonment from 23% to 14% over 30 days against the control
  cohort, DB read QPS from 1800 to 240, and support tickets about slow checkout from about 40 a
  week to 3. Cost went slightly DOWN, because the queue was cheaper than the pods it let us
  remove.

  What I'd do differently: I spent the first week optimising Python code on a hunch. I don't touch
  performance work now without a trace in front of me, and I write the before-number down before I
  change anything."
""")

# EXPERIMENT 1: re-score USE_CASES for a company that forbids source code leaving the network
# (set feasibility=1 on everything that reads the repo). Notice which use cases survive -- that
# constraint is real at most banks and insurers, and it should change your answer.
# EXPERIMENT 2: add a UseCase for your own current project, honestly scored, and see where it
# lands. If you cannot fill in unit_of_value, you have found the weakness in the idea.
# EXPERIMENT 3: run STORY_WEAK.validate() after adding ONE Improvement to its result list. Watch
# which complaints disappear and which remain -- the remaining ones are what interviewers probe.

# EXERCISE: write your OWN two STARStory instances -- one scaling/performance problem you
# diagnosed, one failure you debugged under pressure -- and make validate() return an empty list
# for both. The constraint is deliberate: it will not pass until you have found a real
# before-number and a real after-number, which is exactly the work you should do before the
# interview, not during it. (deep_dive/README.md's checklist asks for these two stories; this is
# the tool for building them.)
