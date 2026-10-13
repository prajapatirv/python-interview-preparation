"""
"How would you fix an issue in a distributed production system with ZERO downtime?"

The answer is never one technique -- it's a sequence, and the order is the point:

  STOP THE BLEEDING FIRST (seconds-to-minutes, no deploy):
     feature flag / kill switch -> traffic shift -> rate limit or shed load -> scale out
  THEN SHIP THE FIX SAFELY (minutes-to-hours):
     rolling or blue/green deploy, behind a canary, with health gating and instant rollback
  AND IF THE SCHEMA MUST CHANGE:
     expand -> migrate -> contract, across THREE separate deploys, never one

This file simulates each one against a fake fleet so the failure modes are observable:
a rolling deploy with no readiness gate serving 500s, connections killed because nothing drained,
a canary that correctly aborts on error rate, and a destructive migration breaking the old
version mid-deploy.

Pure stdlib, no sleeps longer than a few ms. Run me: python 01_zero_downtime_change.py
"""
import random
from collections import Counter


def section(title):
    print(f"\n{'=' * 74}\n{title}\n{'=' * 74}")


# ================================================================ the fake fleet
class Instance:
    """One pod / container / EC2 instance behind a load balancer."""

    def __init__(self, name, version="v1"):
        self.name, self.version = name, version
        self.state = "serving"            # serving | starting | draining | stopped
        self.warmup_requests_left = 0     # requests served badly before caches/JIT are warm
        self.in_flight = 0

    def __repr__(self):
        return f"{self.name}:{self.version}:{self.state}"

    @property
    def ready(self):
        """What a readiness probe answers. The distinction that matters:
             LIVENESS  = 'am I alive?'        -> failing means RESTART me
             READINESS = 'can I take traffic?' -> failing means REMOVE me from the LB
        Conflating them is how a slow-starting pod gets killed in a restart loop."""
        return self.state == "serving" and self.warmup_requests_left == 0

    def handle(self, request_id, broken_version=None):
        self.in_flight += 1
        try:
            if self.state != "serving":
                return 503                             # not serving but still in the LB pool
            if self.warmup_requests_left > 0:          # accepted traffic before being warm
                self.warmup_requests_left -= 1
                return 503
            if self.version == broken_version:
                return 500                             # the bug we are trying to fix
            return 200
        finally:
            self.in_flight -= 1


class LoadBalancer:
    def __init__(self, instances):
        self.instances = list(instances)
        self.counter = 0

    def pool(self, respect_readiness=True):
        if respect_readiness:
            return [i for i in self.instances if i.ready]
        return [i for i in self.instances if i.state != "stopped"]

    def send(self, n, broken_version=None, respect_readiness=True):
        """Round-robins n requests and returns a status-code histogram."""
        codes = Counter()
        for _ in range(n):
            pool = self.pool(respect_readiness)
            if not pool:
                codes[503] += 1                        # nothing to serve: a full outage
                continue
            instance = pool[self.counter % len(pool)]
            self.counter += 1
            codes[instance.handle(self.counter, broken_version)] += 1
        return codes


def report(label, codes, total):
    ok = codes.get(200, 0)
    errors = total - ok
    pct = 100 * errors / total if total else 0
    verdict = "ZERO downtime" if errors == 0 else f"{errors} failed requests ({pct:.1f}%)"
    print(f"    {label:52s} {dict(sorted(codes.items()))}  -> {verdict}")
    return errors


# ================================================================ 1. the kill switch
class FeatureFlag:
    """The fastest possible mitigation: no deploy, no restart, seconds to take effect.

    In production this is LaunchDarkly / Unleash / a DynamoDB or Redis key the app re-reads every
    few seconds. The rule that makes it work: every risky change ships behind a flag, DEFAULT OFF,
    and the flag is removed once the change is proven. A flag you never delete becomes tech debt.
    """

    def __init__(self, name, enabled=True):
        self.name, self.enabled = name, enabled

    def guarded_call(self):
        if not self.enabled:
            return "fallback path (old behaviour, or a cached/degraded response)"
        raise RuntimeError("new code path throws on 12% of inputs")


def demo_kill_switch():
    flag = FeatureFlag("new-pricing-engine", enabled=True)
    failures = 0
    for _ in range(100):
        try:
            flag.guarded_call()
        except RuntimeError:
            failures += 1
    print(f"    flag ON : {failures}/100 requests failing -- customers are seeing it now")
    flag.enabled = False                 # <-- a config change, not a deploy. Seconds.
    print(f"    flag OFF: {flag.guarded_call()}")
    print("    time to mitigate: ~30 seconds, zero restarts, zero risk of a bad rollback build.")
    print("    THEN you fix the code calmly, with the pressure off. This is step one, always.")


# ================================================================ 2. rolling deploy
def rolling_deploy(n_instances=6, batch_size=2, wait_for_ready=True, warmup=3,
                   requests_per_step=60):
    """Replace instances in batches. Two things decide whether this is actually zero-downtime:

      1. DRAIN first -- fail readiness so the LB removes the instance, and let in-flight
         requests finish, BEFORE stopping the process.
      2. Do not return the new instance to the pool until its READINESS probe passes, so
         cold-start 503s are absorbed by the probe instead of by customers.

    Skip either and the deploy serves errors even though every pod reports "Running".
    """
    fleet = [Instance(f"pod-{i}") for i in range(n_instances)]
    lb = LoadBalancer(fleet)
    codes = Counter()
    total = 0

    def traffic(n):
        nonlocal total
        total += n
        codes.update(lb.send(n, respect_readiness=wait_for_ready))

    for start in range(0, n_instances, batch_size):
        batch = fleet[start:start + batch_size]
        for inst in batch:
            inst.state = "draining"
        traffic(requests_per_step)                     # traffic during the drain
        for inst in batch:
            inst.state = "starting"
            inst.version = "v2"
            inst.warmup_requests_left = warmup
        if wait_for_ready:
            for inst in batch:
                inst.state = "serving"            # process up, but `ready` is still False...
                while inst.warmup_requests_left:  # ...so the PROBE absorbs the cold-start 503s
                    inst.handle("warmup-probe")
        else:
            for inst in batch:
                inst.state = "serving"            # straight back into rotation, still cold
        traffic(requests_per_step)                     # traffic right after the swap
    return total, codes, fleet


# ================================================================ 3. blue/green
def blue_green(requests_per_phase=100, green_is_broken=False):
    """Two full environments. You deploy to the idle one, verify it with real probes while it
    serves NO customer traffic, then flip the LB/DNS/target group in one atomic step.

    Cost: 2x infrastructure during the switch. Benefit: rollback is the same one-step flip, and
    it is instant -- no re-deploy, no image pull, no warm-up. For a severe production bug that
    speed is worth the money.
    """
    blue = LoadBalancer([Instance(f"blue-{i}", "v1") for i in range(3)])
    green = LoadBalancer([Instance(f"green-{i}", "v2") for i in range(3)])
    active, standby = blue, green
    log = []

    codes = active.send(requests_per_phase)
    log.append(("serving from BLUE (v1)", codes, requests_per_phase))

    smoke = standby.send(20, broken_version="v2" if green_is_broken else None)
    smoke_ok = smoke.get(200, 0) == 20
    log.append(("smoke-testing GREEN with zero customer traffic", smoke, 20))

    if smoke_ok:
        active, standby = green, blue                 # the atomic flip
        codes = active.send(requests_per_phase, broken_version="v2" if green_is_broken else None)
        log.append(("flipped: serving from GREEN (v2)", codes, requests_per_phase))
    else:
        log.append(("flip ABORTED, blue still serving -- customers saw nothing", Counter(), 0))
        codes = active.send(requests_per_phase)
        log.append(("still serving from BLUE (v1)", codes, requests_per_phase))
    return log


# ================================================================ 4. canary
def canary_deploy(steps=(1, 5, 25, 50, 100), requests_per_step=2000, new_version_error_rate=0.0,
                  slo_error_rate=0.01, seed=11):
    """Send a small % of real traffic to the new version, measure the error rate OF THE CANARY
    (not of the fleet average -- diluting the signal is how a bad canary gets promoted), and
    abort on the first step that breaches the SLO.

    The whole value is bounding the blast radius: a bad deploy hurts 1% of users for two minutes
    instead of 100% of users for twenty. Automate the abort -- a human watching a dashboard is
    not a rollback strategy.

    Yields (pct, canary_requests, errors, rate, breached). Note how few samples 1% of traffic
    gives you: at low volume a canary step needs minutes, not seconds, to mean anything.
    """
    rng = random.Random(seed)
    history = []
    for pct in steps:
        canary_requests = max(1, round(requests_per_step * pct / 100))
        errors = sum(1 for _ in range(canary_requests) if rng.random() < new_version_error_rate)
        rate = errors / canary_requests
        breached = rate > slo_error_rate
        history.append((pct, canary_requests, errors, rate, breached))
        if breached:
            break
    return history


# ================================================================ 5. expand / migrate / contract
class FakeTable:
    """A table the OLD and NEW application versions both talk to DURING the deploy. That overlap
    is the entire reason a one-step migration causes downtime."""

    def __init__(self):
        self.columns = {"id", "customer_name"}
        self.rows = [{"id": 1, "customer_name": "Ravi Bhalsod"}]

    def read(self, version):
        """v1 reads customer_name; v2 reads first_name/last_name."""
        needed = {"customer_name"} if version == "v1" else {"first_name", "last_name"}
        missing = needed - self.columns
        if missing:
            raise KeyError(f"{version} needs column(s) {sorted(missing)} which do not exist")
        return "ok"

    def write(self, version):
        return self.read(version)


def destructive_migration():
    """The one-step version: rename customer_name -> first_name/last_name in a single migration,
    deployed with the code. Every v1 instance still running breaks instantly."""
    t = FakeTable()
    t.columns = {"id", "first_name", "last_name"}      # the rename, as one irreversible step
    results = {}
    for version in ("v1", "v2"):
        try:
            t.read(version)
            results[version] = "ok"
        except KeyError as e:
            results[version] = f"BROKEN: {e}"
    return results


def expand_migrate_contract():
    """The safe version: THREE deploys, each independently reversible.

      DEPLOY 1 (expand):  add the new columns, nullable. Old code ignores them. Nothing breaks.
                          Application DUAL-WRITES: every write fills old AND new columns.
      DEPLOY 2 (migrate): backfill old rows in batches (never one giant UPDATE -- that locks the
                          table and blows your replication lag). Then switch READS to the new
                          columns, still dual-writing.
      DEPLOY 3 (contract): once no running code reads the old column, drop it. Days later, not
                          minutes -- you need a rollback window.

    At no point do both the old and new application versions disagree about what exists.
    """
    t = FakeTable()
    timeline = []

    # DEPLOY 1 -- expand
    t.columns |= {"first_name", "last_name"}
    timeline.append(("after expand (add nullable columns)",
                     {v: safe(t, v) for v in ("v1", "v2")}))

    # backfill, in batches
    for row in t.rows:
        first, _, last = row["customer_name"].partition(" ")
        row["first_name"], row["last_name"] = first, last
    timeline.append(("after backfill (batched, throttled)",
                     {v: safe(t, v) for v in ("v1", "v2")}))

    # DEPLOY 2 -- all instances now on v2, reading the new columns
    timeline.append(("after deploy 2 (v2 everywhere, still dual-writing)",
                     {"v2": safe(t, "v2")}))

    # DEPLOY 3 -- contract, days later
    t.columns -= {"customer_name"}
    timeline.append(("after contract (drop the old column, days later)",
                     {"v2": safe(t, "v2"), "v1 (no longer running)": safe(t, "v1")}))
    return timeline


def safe(table, version):
    try:
        table.read(version)
        return "ok"
    except KeyError as e:
        return f"BROKEN: {e}"


# ================================================================ 6. connection draining
def draining(in_flight_requests=5, drain=True):
    """SIGTERM arrives. The difference between a clean shutdown and 5 angry customers:

        signal.signal(signal.SIGTERM, handler)   # set a flag
        -> stop accepting new work (fail readiness so the LB removes you)
        -> wait for in-flight requests, with a timeout (K8s terminationGracePeriodSeconds)
        -> close DB pools / flush the Kafka producer / commit offsets
        -> exit 0

    Kubernetes sends SIGTERM, waits terminationGracePeriodSeconds (default 30), then SIGKILL.
    If your shutdown takes longer than that, your pod is killed mid-request every single deploy.
    """
    inst = Instance("pod-x")
    inst.in_flight = in_flight_requests
    events = []
    if drain:
        events.append("SIGTERM received, readiness set to false")
        events.append("LB removed this instance from the pool (new traffic -> other pods)")
        while inst.in_flight:
            inst.in_flight -= 1
            events.append(f"finished an in-flight request ({inst.in_flight} left)")
        events.append("flushed Kafka producer, committed offsets, closed the DB pool")
        events.append("exit 0 -- zero failed requests")
    else:
        events.append("SIGKILL / os._exit() -- process gone immediately")
        events.append(f"{inst.in_flight} in-flight requests became client-side 502s")
        events.append("uncommitted Kafka offsets -> those messages get redelivered")
        events.append("unflushed producer buffer -> those events are LOST")
    return events


if __name__ == "__main__":
    section("STEP 1 -- mitigate before you fix: the kill switch (no deploy, ~30 seconds)")
    demo_kill_switch()

    section("STEP 2 -- a rolling deploy, with and without a readiness gate")
    total, codes, fleet = rolling_deploy(wait_for_ready=True)
    report("rolling, drain + readiness gate", codes, total)
    total, codes, fleet = rolling_deploy(wait_for_ready=False)
    report("rolling, NO drain and NO readiness gate", codes, total)
    print("    the 503s in the second run came from two distinct bugs:")
    print("      - draining pods still in the LB pool (no deregistration delay)")
    print("      - cold pods back in rotation before their caches/pools were warm")
    print("    'the pods were all Running' is not the same as 'zero requests failed'.")

    section("STEP 2b -- blue/green: verify with zero customer traffic, then flip atomically")
    print("    healthy green:")
    for label, codes, n in blue_green(green_is_broken=False):
        if n:
            report(label, codes, n)
        else:
            print(f"    {label}")
    print("\n    broken green (the smoke test catches it):")
    for label, codes, n in blue_green(green_is_broken=True):
        if n:
            report(label, codes, n)
        else:
            print(f"    {label}")
    print("    rollback = flip the pointer back. Instant, and it needs no new build.")

    section("STEP 2c -- canary: bound the blast radius, and automate the abort")
    for label, rate in [("a healthy new version", 0.0), ("a new version failing 20% of calls", 0.20)]:
        print(f"    {label}:")
        history = canary_deploy(new_version_error_rate=rate)
        for pct, n, errors, observed, breached in history:
            verdict = "BREACH -> ROLLBACK" if breached else "within SLO, promote"
            print(f"      {str(pct) + '% traffic':>12s}  canary_requests={n:>5d}  errors={errors:>4d}  "
                  f"rate={observed:6.2%}  {verdict}")
        last_pct = history[-1][0]
        if history[-1][4]:
            print(f"      -> aborted at {last_pct}% of traffic: "
                  f"{100 - last_pct}% of users never saw the bug")
        else:
            print("      -> promoted to 100%")
    print("    the canary's OWN error rate is the signal. Averaging it over the whole fleet")
    print("    (1% of traffic failing 20% = 0.2% overall) hides the bug under your SLO threshold.")

    section("STEP 3 -- the schema change: one destructive migration vs expand/migrate/contract")
    print("    destructive rename, deployed in one step:")
    for version, result in destructive_migration().items():
        print(f"      {version}: {result}")
    print("      ...and every v1 pod still running during the rollout is now throwing 500s.")
    print("\n    expand -> migrate -> contract:")
    for label, results in expand_migrate_contract():
        print(f"      {label}")
        for version, result in results.items():
            print(f"        {version:28s} {result}")
    print("      while BOTH versions are running, neither ever sees a missing column. v1 only")
    print("      breaks after it is fully retired -- which is the point of the 3-deploy sequence.")

    section("STEP 4 -- graceful shutdown: drain, or lose requests on every single deploy")
    print("    with draining:")
    for e in draining(drain=True):
        print(f"      {e}")
    print("    without draining:")
    for e in draining(drain=False):
        print(f"      {e}")

    section("the checklist to say out loud")
    print("""  Mitigate first, fix second. In order:

   0. DECLARE IT. One incident channel, one commander, one scribe. Stop the side conversations.
   1. MITIGATE without a deploy (seconds):
        - flip the feature flag / kill switch off
        - shift traffic: away from the bad AZ/region/cell, or back to the previous version
        - shed load: rate-limit the abusive caller, turn off the expensive non-critical path
        - scale out horizontally if it's saturation rather than a bug
   2. STABILISE: confirm the SLI recovered (error rate, p99, queue depth). Say it in metrics,
      not in vibes. Only now does the clock stop.
   3. DIAGNOSE with the system calm: correlation IDs, traces, the diff of what changed in the
      last hour. 80% of production incidents are caused by a change -- look there first.
   4. FIX with a rolling or blue/green deploy, behind a canary, with automated abort on SLO
      breach and a tested rollback. Schema changes get expand -> migrate -> contract.
   5. VERIFY: watch the canary metrics, not the deploy pipeline's green tick.
   6. BLAMELESS POSTMORTEM: what made it possible, what made it slow to detect, what made it
      slow to mitigate. One action item per answer, each with an owner and a date.

  The capabilities that make all of this possible -- build them BEFORE the incident:
    stateless services (so any instance can be replaced), health + readiness probes that mean
    different things, feature flags on every risky path, backward-compatible APIs and schemas,
    idempotent operations (so a retry is free), observability you can query in minutes
    (see 02_observability_pillars.py), and a rollback you have actually rehearsed.

  What makes an answer senior: naming what you give up. Blue/green costs 2x infrastructure.
  Canaries need enough traffic to be statistically meaningful -- at 10 requests/minute a 1%
  canary tells you nothing. Expand/migrate/contract means three deploys and a week of dual
  writes. Zero downtime is bought, not free, and you should know the price.""")

# EXPERIMENT 1: in rolling_deploy, set warmup=10 with wait_for_ready=False and watch the
# 503 count climb -- that is exactly the shape of "deploys always cause a 2-minute error spike".
# EXPERIMENT 2: run canary_deploy(new_version_error_rate=0.02, requests_per_step=200). At 1%
# traffic that is 2 canary requests -- a sample far too small to judge anything, so it passes by
# luck. Raise requests_per_step to 20000 and it fails honestly. That is the statistical-
# significance point an interviewer is waiting for: a canary needs VOLUME, or TIME, or both.
# EXPERIMENT 3: in expand_migrate_contract, move the contract step before deploy 2 and show which
# version breaks. Then write the one-sentence rule that prevents it.

# EXERCISE: add a `cell_based_routing(cells, bad_cell)` function that routes customers to N
# independent cells by hash of customer_id, then shows that taking one cell out of rotation caps
# the impact of a bad deploy at 1/N of users instead of all of them. Compare that blast radius
# with the canary above, and say which one you'd build first for a system at 600 TPS.
