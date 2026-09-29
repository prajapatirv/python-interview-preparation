"""
Production monitoring, simulated: RED metrics, histogram quantiles, the cardinality
trap, SLOs and error budgets, and multi-window burn-rate alerting.

Pure stdlib — no Prometheus, no Grafana. The point is to see WHY each rule exists,
because "alert on CPU > 80%" is the answer that fails the interview.

Run me: python 05_metrics_alerting_simulation.py
Deep dive: ../deep_dive/19_production_stability_monitoring.md
"""
import bisect
import random
import time
from collections import Counter, defaultdict


def section(title):
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


random.seed(7)   # deterministic output so the numbers below are reproducible


# ================================================================== metrics
class Registry:
    """A toy Prometheus: counters and histograms with labels."""

    def __init__(self):
        self.counters = defaultdict(float)     # (name, labels) -> value
        self.histograms = defaultdict(list)    # (name, labels) -> [observations]

    def inc(self, name, amount=1.0, **labels):
        self.counters[(name, tuple(sorted(labels.items())))] += amount

    def observe(self, name, value, **labels):
        self.histograms[(name, tuple(sorted(labels.items())))].append(value)

    def series_count(self):
        return len(self.counters) + len(self.histograms)


def quantile(values, q):
    if not values:
        return 0.0
    s = sorted(values)
    idx = min(int(q * len(s)), len(s) - 1)
    return s[idx]


# ================================================================== 1. RED
section("1. RED metrics — Rate, Errors, Duration — the three that matter")

reg = Registry()
ROUTES = ["/orders/{id}", "/orders", "/health"]

for _ in range(5_000):
    route = random.choices(ROUTES, weights=[6, 3, 1])[0]
    # /orders is slower and fails more often
    slow = route == "/orders"
    latency = random.lognormvariate(-3.2 if not slow else -2.1, 0.6)
    failed = random.random() < (0.02 if slow else 0.002)
    status = 500 if failed else 200

    reg.inc("http_requests_total", route=route, status=status)
    reg.observe("http_request_duration_seconds", latency, route=route)

for route in ROUTES:
    total = sum(v for (n, lbl), v in reg.counters.items()
                if n == "http_requests_total" and ("route", route) in lbl)
    errors = sum(v for (n, lbl), v in reg.counters.items()
                 if n == "http_requests_total" and ("route", route) in lbl
                 and ("status", 500) in lbl)
    lat = reg.histograms[("http_request_duration_seconds", (("route", route),))]
    print(f"  {route:<16} rate={total:>6.0f}  errors={errors / total:>6.2%}  "
          f"p50={quantile(lat, .50) * 1000:>6.1f}ms  p99={quantile(lat, .99) * 1000:>7.1f}ms")

print("\n  Note p50 vs p99 — an AVERAGE would hide the tail entirely.")


# ================================================================== 2. cardinality
section("2. THE CARDINALITY TRAP — the incident that takes down your monitoring")

good = Registry()
bad = Registry()

for i in range(5_000):
    order_id = random.randint(1, 100_000)
    good.inc("http_requests_total", route="/orders/{id}", status=200)    # TEMPLATE
    bad.inc("http_requests_total", route=f"/orders/{order_id}", status=200)  # RAW PATH

print(f"  labelled by route TEMPLATE : {good.series_count():>7,} time series")
print(f"  labelled by RAW path       : {bad.series_count():>7,} time series")
print(f"\n  5,000 requests produced {bad.series_count():,} series. At production volume that is")
print("  millions — Prometheus runs out of memory and your monitoring dies during")
print("  the incident you needed it for.")
print("\n  NEVER label with: user id, order id, email, session id, raw path, raw error text.")
print("  SAFE labels     : route template, method, status code, env, error CLASS.")
print("  Per-entity detail belongs in LOGS and TRACES, never in metric labels.")


# ================================================================== 3. histogram
section("3. why Histogram beats Summary: quantiles are NOT averageable")

# A REALISTIC fleet: instances are not identical. Two healthy pods take most of
# the traffic; one straggler (bad node, cold cache, noisy neighbour) is far slower
# and — because it is slow — serves far FEWER requests.
profiles = [
    ("pod-a (healthy)",  4_000, -3.2, 0.5),
    ("pod-b (healthy)",  4_000, -3.2, 0.5),
    ("pod-c (straggler)",  200, -0.8, 0.9),
]
instances = []
for name, n, mu, sigma in profiles:
    instances.append((name, [random.lognormvariate(mu, sigma) for _ in range(n)]))

local_p99s = [(name, quantile(lat, 0.99)) for name, lat in instances]
avg_of_p99 = sum(p for _, p in local_p99s) / len(local_p99s)        # WRONG
all_obs = [x for _, lat in instances for x in lat]
true_p99 = quantile(all_obs, 0.99)                                   # RIGHT

for (name, lat), (_, p) in zip(instances, local_p99s):
    print(f"  {name:<20} n={len(lat):>5}  local p99 = {p * 1000:>7.1f}ms")
print(f"\n  average of those p99s : {avg_of_p99 * 1000:>7.1f}ms   <- a Summary gives you this")
print(f"  TRUE fleet-wide p99   : {true_p99 * 1000:>7.1f}ms   <- a Histogram gives you this")
print(f"  error                 : {abs(avg_of_p99 - true_p99) / true_p99:>7.1%}")
print("""
  Averaging quantiles is doubly wrong: it ignores that the pods served very
  different REQUEST COUNTS, and the straggler's p99 gets a full one-third vote
  despite handling 2% of the traffic. There is no weighting that fixes it either —
  a quantile of quantiles is simply not a quantile.

  A Summary computes quantiles per instance, so it CANNOT be aggregated.
  A Histogram exports bucket COUNTS, which ARE additive — so histogram_quantile()
  across the fleet is correct. Use Histogram.""")


# ================================================================== 4. buckets
section("4. histogram buckets — what Prometheus actually stores")

BUCKETS = [.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10]
observations = all_obs           # reuse the fleet-wide sample from section 3
cumulative = Counter()
for v in observations:
    idx = bisect.bisect_left(BUCKETS, v)
    for b in BUCKETS[idx:]:
        cumulative[b] += 1                       # "le" buckets are CUMULATIVE

print("  le (seconds)   count  (cumulative)")
for b in BUCKETS:
    bar = "#" * int(40 * cumulative[b] / len(observations))
    print(f"  {b:>8}   {cumulative[b]:>6}  {bar}")
print(f"  {'+Inf':>8}   {len(observations):>6}")
print("\n  Bucket choice matters: with no bucket near your SLO threshold you cannot")
print("  measure compliance. Add a bucket AT your SLO (e.g. 0.2 for a 200ms target).")


# ================================================================== 5. SLO
section("5. SLI / SLO / error budget")

SLO = 0.995                       # 99.5% of requests succeed
WINDOW_DAYS = 30
budget_fraction = 1 - SLO
budget_minutes = budget_fraction * WINDOW_DAYS * 24 * 60

total_reqs = sum(v for (n, _), v in reg.counters.items() if n == "http_requests_total")
error_reqs = sum(v for (n, lbl), v in reg.counters.items()
                 if n == "http_requests_total" and ("status", 500) in lbl)
sli = 1 - error_reqs / total_reqs
consumed = (error_reqs / total_reqs) / budget_fraction

print(f"  SLI  (availability)   : {sli:.4%}")
print(f"  SLO  (target)         : {SLO:.2%}")
print(f"  error budget          : {budget_fraction:.2%}  = {budget_minutes:.0f} min / {WINDOW_DAYS}d")
print(f"  budget consumed       : {consumed:.1%}")
print(f"  verdict               : "
      f"{'SHIP FREELY' if consumed < 0.5 else 'SLOW DOWN' if consumed < 1 else 'FREEZE FEATURES'}")
print("""
  The error budget turns reliability from an argument into arithmetic. Budget left
  means ship; budget spent means stop shipping features and fix reliability. It
  aligns the velocity people and the stability people on one number.

  Never set the SLO to 100% — it removes the budget, so every incident is a crisis
  and there is no framework for deciding what is acceptable.""")


# ================================================================== 6. burn rate
section("6. multi-window burn-rate alerting — why a flat threshold is wrong")


# Use a 99.9% SLO here — the usual target for a customer-facing API. The tighter the
# SLO, the more clearly a flat percentage threshold diverges from budget burn.
SLO_BURN = 0.999
BUDGET = 1 - SLO_BURN                       # 0.1%
FLAT_THRESHOLD = 0.01                       # the naive "error rate > 1%" rule


def burn_rate(error_ratio):
    """How many times faster than sustainable are we burning the error budget?"""
    return error_ratio / BUDGET


def evaluate(long_ratio, short_ratio, factor, label, severity):
    """BOTH windows must breach: long confirms it is sustained, short that it is CURRENT."""
    fired = burn_rate(long_ratio) > factor and burn_rate(short_ratio) > factor
    print(f"    {label:<30} long={burn_rate(long_ratio):>6.1f}x  "
          f"short={burn_rate(short_ratio):>6.1f}x  -> {severity if fired else '-'}")
    return fired


scenarios = [
    # (name,                             long-window ratio, short-window ratio)
    ("steady healthy",                    0.0005,  0.0005),
    ("2-min blip, already recovered",     0.0120,  0.0001),
    ("major outage, ongoing",             0.0500,  0.0800),
    ("slow persistent burn",              0.0040,  0.0045),
]

print(f"  SLO {SLO_BURN:.1%}  ->  error budget {BUDGET:.2%}")
print("  FAST burn rule: 14.4x over BOTH 1h and 5m  -> P1 page")
print("  SLOW burn rule:  3.0x over BOTH 6h and 30m -> P2 ticket")
print(f"  NAIVE flat rule: error rate > {FLAT_THRESHOLD:.0%} on the long window\n")

for name, long_r, short_r in scenarios:
    print(f"  scenario: {name}   (long={long_r:.2%}  short={short_r:.2%})")
    evaluate(long_r, short_r, 14.4, "fast burn (1h + 5m)", "P1 PAGE")
    evaluate(long_r, short_r, 3.0, "slow burn (6h + 30m)", "P2 ticket")
    flat = long_r > FLAT_THRESHOLD
    note = "  <-- FALSE POSITIVE" if flat and short_r < BUDGET * 3 else ""
    print(f"    {'NAIVE flat rule':<30} {'':>11}  {'':>13}  -> "
          f"{'FIRES' if flat else '-'}{note}")
    print()

print("""  Read the two middle scenarios — they are the whole argument:

  'blip, already recovered'  the flat rule FIRES (1.2% > 1%) and keeps firing on the
                             1h average long after the problem ended. The burn-rate
                             rules do not, because the SHORT window is clean. That
                             short window is what makes an alert resolve promptly.

  'slow persistent burn'     the flat rule stays SILENT (0.4% < 1%) while the service
                             quietly burns its budget at 4x — it will miss the SLO in
                             days. The slow-burn rule catches it as a P2 ticket.

  A single flat threshold is simultaneously too noisy and too blind. Alert fatigue is
  the real failure mode: every alert that fires without needing action trains people
  to ignore alerts.""")


# ================================================================== 7. symptoms
section("7. alert on SYMPTOMS, not CAUSES")

rows = [
    ("CPU > 80%",                     "CAUSE",   "dashboard",  "users may be fine"),
    ("memory > 85%",                  "CAUSE",   "ticket",     "investigate a leak"),
    ("pod restarted",                 "CAUSE",   "ticket",     "unless it is looping"),
    ("5xx rate > 1% for 2 min",       "SYMPTOM", "P1 PAGE",    "users are harmed NOW"),
    ("p99 latency > 2s for 5 min",    "SYMPTOM", "P2 slack",   "users feel it"),
    ("RPS < 10% of baseline",         "SYMPTOM", "P1 PAGE",    "likely a total outage"),
    ("Kafka lag > 10k for 10 min",    "SYMPTOM", "P2 slack",   "falling behind; data at risk"),
    ("DLQ depth > 0",                 "SYMPTOM", "P2 ticket",  "ALWAYS — messages are stuck"),
    ("error budget burn > 14.4x",     "SYMPTOM", "P1 PAGE",    "SLO will be missed"),
]
print(f"  {'condition':<32}{'kind':<10}{'action':<12}why")
print("  " + "-" * 82)
for cond, kind, action, why in rows:
    print(f"  {cond:<32}{kind:<10}{action:<12}{why}")

print("""
  High CPU with happy users is not worth waking anyone for. The three tests for any
  proposed alert: (1) is a human needed RIGHT NOW? (2) is it actionable — is there a
  runbook step? (3) does it reflect user impact? If not, it is a dashboard or a ticket.""")


# EXERCISE 1: add a `tenant` label to http_requests_total and compute how many series
#             1,000 tenants x 3 routes x 4 status codes produces. Is that acceptable?
# EXERCISE 2: change SLO to 0.999 and re-run section 5. How many minutes of budget
#             per month do you have now? Is that operationally realistic for your team?
# EXERCISE 3: implement a 5th scenario — a 10-minute outage — and show it fires the fast
#             burn rule but NOT the slow one, and explain why that is correct.
# EXERCISE 4: add buckets at 0.2 and 2.0 to BUCKETS and recompute the share of requests
#             under a 200ms SLO threshold.
