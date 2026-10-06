# 13 — System Design & Scenario Questions

The questions that aren't about syntax: *"how do you fix it with zero downtime?"*, *"how do you
scale 100 → 600 TPS?"*, *"how does observability work?"*, *"how would you use an AI tool on this
project?"*, *"what did you build that made customers happy?"*

These rounds are lost by **arm-waving** — "we'd add caching and more pods". They're won by a
**method plus arithmetic**: Little's Law, a bottleneck table, a burn-rate threshold, a before/after
number. Every file here is runnable so the arithmetic is real and you can change the inputs.

Pure stdlib, no infrastructure.

## Crib sheet

- **Zero downtime is a SEQUENCE, not a technique.** Mitigate without a deploy first (feature flag →
  traffic shift → shed load → scale out), *then* ship the fix (rolling/blue-green behind a canary
  with automated abort), and never change a schema in one step — **expand → migrate → contract**
  across three deploys.
- **Liveness ≠ readiness.** Liveness failing means *restart me*; readiness failing means *take me
  out of the load balancer*. Conflating them causes restart loops; skipping readiness causes the
  "every deploy has a 2-minute error spike" that teams learn to accept.
- **Observability = metrics (is it broken?) + logs (what happened to this request?) + traces (where
  did the time go?) + a correlation ID joining all three.** Low-cardinality labels in metrics;
  high-cardinality fields (order_id, user_id) in logs and spans. `SLI → SLO → error budget`, and
  alert on **burn rate** against the budget, on **symptoms** not causes.
- **Capacity planning is multiplication.** `Little's Law: concurrency = TPS × latency`. Halving
  latency halves the fleet you must provision, so **remove work before buying capacity** (fix the
  N+1, cache, batch, offload to a queue). Size pools and partitions from the same equation.
- **Never plan past ~70% utilization.** Queueing delay goes as `1/(1−ρ)`: at 90% busy your p99 is
  already 10× your service time, and the next 5% of traffic doubles it again.
- **Amdahl's Law is the ceiling.** 10% of the request behind one shared lock means 50 pods buy you
  8.5×, not 50×. Find the serial component before you add instances.
- **Overload must degrade, not collapse.** A bounded queue + load shedding (429 + `Retry-After`)
  keeps p99 bounded for everyone else. An unbounded queue just relocates the outage.
- **AI on a project: score use cases on value × feasibility, discounted by blast radius.** Start
  internal and advisory (a human still approves), measure a baseline *before* the pilot, and keep
  it only if the number moved. The guardrails — PII redaction, eval gates in CI, versioned prompts,
  a kill switch — are the part that separates "used AI" from "shipped AI".
- **A customer-impact story without a number is an anecdote.** STAR, with the Result as
  before → after, the measurement window, and how you measured it. Also name what got *worse*.

## Files

| File | Question it answers |
|---|---|
| `01_zero_downtime_change.py` | fixing production with zero downtime — kill switch, rolling vs blue/green, canary with automated abort, expand/migrate/contract, connection draining |
| `02_observability_pillars.py` | the three pillars built from scratch — correlation IDs in `ContextVar`, structured JSON logs, a metrics registry with percentiles, a tracer with a span waterfall, RED/USE, SLO burn-rate alerting, log sampling |
| `03_capacity_scaling_tps.py` | 100 → 600 TPS — Little's Law, Amdahl's Law, the utilization cliff, a bottleneck analyser, cache/pool/partition sizing, a load test that collapses, and the cost comparison |
| `04_ai_leverage_and_impact.py` | the two behavioural-but-technical questions — an AI use-case scorecard with guardrails and measured pilot results, plus a STAR story builder that rejects a story with no measured result |

## How to use this folder

1. Run each file and read the output alongside the code — the output *is* the answer you'd give.
2. Change the inputs. `TARGET_TPS = 6000` in `03_` changes which component is the bottleneck, and
   therefore changes the architecture, not just the config. That's the exercise.
3. Do the `# EXERCISE` block at the bottom of `04_` **before** your next interview: two STAR
   stories of your own, with real before/after numbers, that pass `validate()`. Those two stories
   matter more than any other answer in this repo.

> **Deep dives**: [27 — Zero-downtime production changes](../deep_dive/27_zero_downtime_production_changes.md) ·
> [28 — Observability in distributed systems](../deep_dive/28_observability_distributed_systems.md) ·
> [29 — Capacity planning & scaling to 600 TPS](../deep_dive/29_capacity_scaling_tps.md) ·
> [32 — AI leverage & customer-impact stories](../deep_dive/32_ai_leverage_and_impact_stories.md)
>
> Closely related: [12 — Scaling applications](../deep_dive/12_scaling_applications.md) ·
> [19 — Production stability, alerting & monitoring](../deep_dive/19_production_stability_monitoring.md) ·
> and the runnable patterns in [`../08_scaling_production_resilience/`](../08_scaling_production_resilience/)
> (retry, circuit breaker, rate limiter, health checks) that these scenarios assume you have.
