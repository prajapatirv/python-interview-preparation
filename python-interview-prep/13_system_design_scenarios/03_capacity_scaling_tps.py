"""
"Traffic is going from 100 TPS to 600 TPS. How do you scale the system?"

The wrong answer is "add more pods". The right answer is a method:

  1. MEASURE first -- what is the current per-request cost in CPU, DB time and connections?
  2. DO THE ARITHMETIC -- Little's Law gives you the concurrency you need; that tells you the
     worker count, the pool sizes and the partition count. Capacity planning is multiplication.
  3. FIND THE REAL BOTTLENECK -- it is almost never the app tier. It is the database, a lock,
     a third-party API's rate limit, or a single-threaded component.
  4. REMOVE WORK before adding capacity -- caching, batching, async offload and an N+1 fix are
     all cheaper than 6x the infrastructure, and they improve latency instead of just surviving.
  5. SCALE WHAT'S LEFT, horizontally, and protect it with backpressure so overload degrades
     instead of collapsing.
  6. PROVE IT with a load test to 2x the target, then watch the saturation signals.

This file computes all of it: Little's Law, Amdahl's Law, queueing-theory latency under
utilization, a bottleneck analyser over a realistic request profile, the cache-hit-ratio
effect, connection-pool and Kafka-partition sizing, a cost comparison, and a simulated
load test that shows a queue collapsing at >100% utilization.

Pure stdlib. Run me: python 03_capacity_scaling_tps.py
"""
import math
import random
from collections import deque


def section(title):
    print(f"\n{'=' * 76}\n{title}\n{'=' * 76}")


CURRENT_TPS = 100
TARGET_TPS = 600


# ================================================================ Little's Law
def littles_law(tps, latency_seconds):
    """Little's Law:  L = arrival_rate x time_in_system.

    This single equation is the backbone of every capacity answer:
      600 TPS x 200ms  = 120 requests in flight at any instant.
      600 TPS x 50ms   =  30 requests in flight.

    Read it twice, because the second reading is the insight: HALVING LATENCY HALVES THE
    CONCURRENCY YOU MUST PROVISION. Making the request faster is the same as buying servers,
    except it also makes customers happier and costs nothing to run.
    """
    return tps * latency_seconds


def workers_needed(tps, service_time_seconds, target_utilization=0.7, per_worker_concurrency=1):
    """How many workers/threads/pods. Two things people get wrong:

      1. Never size for 100% utilization. Queueing delay goes to infinity as utilization -> 1
         (see utilization_latency_multiplier below). 60-75% is the planning target; that
         headroom is what absorbs a traffic spike, a GC pause, or losing an AZ.
      2. A sync Python worker handles ONE request at a time (per_worker_concurrency=1).
         An asyncio worker handles many concurrent I/O-bound requests on one thread -- which is
         exactly why async matters for an I/O-heavy service at 600 TPS.
    """
    concurrency = littles_law(tps, service_time_seconds)
    return math.ceil(concurrency / (target_utilization * per_worker_concurrency))


def utilization_latency_multiplier(utilization):
    """From M/M/1 queueing: response time multiplies by 1/(1-rho) as utilization rho rises.

      50% busy -> 2x the service time
      80% busy -> 5x
      90% busy -> 10x
      95% busy -> 20x
      99% busy -> 100x

    This is THE number to quote when someone says "CPU is only at 85%, we're fine". At 85%
    utilization your p99 is already ~7x your service time, and the next 5% of traffic doubles it.
    """
    if utilization >= 1:
        return float("inf")
    return 1 / (1 - utilization)


def amdahl_speedup(parallel_fraction, n_workers):
    """Amdahl's Law: the serial part caps your scaling. If 10% of the request is serialised --
    one shared lock, one single-threaded leader, one global sequence -- then no number of workers
    gets you past 10x, and you are at 5.3x by 10 workers.

    In a 100 -> 600 TPS conversation this is the answer to "we'll just add pods": find the serial
    component FIRST, because that is your real ceiling."""
    if parallel_fraction >= 1:
        return n_workers
    return 1 / ((1 - parallel_fraction) + parallel_fraction / n_workers)


# ================================================================ the request profile
# What 1 request actually costs today, measured (from a trace/profile, not guessed).
REQUEST_PROFILE = [
    # component,            ms,   calls/request, max_capacity_tps, scaling
    ("app CPU (python)",    25.0, 1, 100 * 4,  "horizontal: more pods"),
    ("auth cache (redis)",   2.0, 1, 100000,   "horizontal: already trivial"),
    ("db: SELECT order",     8.0, 1, 1200,     "read replica / cache"),
    ("db: SELECT items",     6.0, 5, 1200,     "N+1! -> one JOIN or an IN query"),
    ("db: INSERT event",    12.0, 1, 400,      "WRITE -- single primary, the real limit"),
    ("payment-gateway API", 85.0, 1, 150,      "third-party rate limit: 150 TPS, hard"),
    ("email send",         120.0, 1, 50,       "does NOT need to be in the request path"),
]


def analyse_profile(profile, target_tps):
    """For each component: required TPS at the target, headroom, and whether it is the bottleneck.
    This table IS the capacity plan -- everything else is a reaction to it."""
    rows = []
    for name, ms, calls, max_tps, strategy in profile:
        required = target_tps * calls
        ratio = required / max_tps
        rows.append({
            "component": name,
            "ms_per_request": ms * calls,
            "required_tps": required,
            "max_tps": max_tps,
            "utilization": ratio,
            "status": "BOTTLENECK" if ratio > 1 else ("AT RISK" if ratio > 0.7 else "ok"),
            "strategy": strategy,
        })
    return rows


def total_latency(profile):
    return sum(ms * calls for _, ms, calls, _, _ in profile)


# ================================================================ removing work
def with_optimisations(profile):
    """The four changes that remove work instead of buying capacity, in the order of payoff:

      1. FIX THE N+1      -- 5 queries become 1 JOIN. -24ms, -2400 required DB TPS.
      2. CACHE READS      -- 90% hit ratio on the order lookup. -7.2ms, DB read load / 10.
      3. OFFLOAD TO ASYNC -- the email leaves the request path entirely and goes on a queue.
                             -120ms of USER-FACING latency for zero infrastructure.
      4. BATCH WRITES     -- 10 event inserts per transaction. Same rows, 1/10th the write TPS.

    Together they cut latency from 282ms to 120ms -- 2.4x. By Little's Law that alone cuts the
    concurrency you must provision by 2.4x, i.e. it absorbs 40% of the 6x traffic increase before
    you buy a single server. (What's left is dominated by the payment gateway's 85ms, which is
    someone else's latency -- the only lever there is to stop waiting for it synchronously.)
    """
    return [
        ("app CPU (python)",    25.0, 1, 100 * 4,  "horizontal: more pods"),
        ("auth cache (redis)",   2.0, 1, 100000,   "unchanged"),
        ("db: SELECT order",     0.8, 1, 12000,    "90% cache hit -> effective 0.8ms, 10x capacity"),
        ("db: SELECT items",     6.0, 1, 1200,     "N+1 fixed: 5 queries -> 1 JOIN"),
        ("db: INSERT event",     1.2, 1, 4000,     "batched 10 per transaction"),
        ("payment-gateway API", 85.0, 1, 150,      "STILL the hard limit -- needs negotiation"),
        # email removed from the request path entirely -> SQS/Kafka + a worker
    ]


# ================================================================ cache maths
def effective_backend_tps(tps, hit_ratio):
    """A cache's whole value in one line: backend load = tps x (1 - hit_ratio).

      600 TPS at 0% hit   -> 600 TPS on the DB
      600 TPS at 80% hit  -> 120 TPS
      600 TPS at 95% hit  -> 30 TPS
      600 TPS at 99% hit  ->  6 TPS

    Note the shape: going 0->80% removes 480 TPS; going 95->99% removes only 24. Most of the win
    arrives early, which is why "add a cache" is nearly always the cheapest first move -- and why
    chasing the last few percent of hit ratio rarely is.
    """
    return tps * (1 - hit_ratio)


def average_latency_with_cache(hit_ratio, cache_ms=2.0, backend_ms=20.0):
    """And the latency side of the same coin."""
    return hit_ratio * cache_ms + (1 - hit_ratio) * backend_ms


# ================================================================ sizing the dependencies
def pool_size(tps, db_time_seconds, safety=1.3):
    """Connection pool sizing. The pool must cover the CONCURRENT db work (Little's Law again),
    not the request rate.

      600 TPS x 15ms of DB time = 9 concurrent queries -> a pool of ~12 with headroom.

    Two traps:
      - Too SMALL: requests queue for a connection. That wait is invisible in DB metrics and
        looks like "the database is slow" when the database is idle.
      - Too BIG: Postgres has a hard max_connections (~500 on a mid-size instance) and each
        connection costs memory. pods x pool_size must stay under it -- and with 40 pods x 20
        connections you are at 800 and the deploy that adds 5 pods takes the database down.
        Use pgbouncer/RDS Proxy when that multiplication gets uncomfortable.
    """
    concurrency = littles_law(tps, db_time_seconds)
    return max(2, math.ceil(concurrency * safety))


def kafka_partitions(target_tps, per_consumer_tps, replication_overhead=1.0):
    """Partition count = the parallelism ceiling of a consumer group: you can never have more
    usefully-consuming instances than partitions.

    Size for 2-3x the target so you can scale out later WITHOUT repartitioning (which breaks
    per-key ordering and is operationally painful). More partitions is not free either: each one
    costs file handles, memory and rebalance time, and tens of thousands cluster-wide hurts.
    """
    minimum = math.ceil(target_tps / per_consumer_tps)
    return minimum, minimum * 3


def instance_cost(pods, pod_cost_per_month=70):
    return pods * pod_cost_per_month


# ================================================================ the load-test simulation
def simulate(arrival_tps, service_time_ms, workers, duration_seconds=60, seed=3,
             queue_limit=None):
    """A discrete-event-ish simulation of a bounded worker pool, to make the utilization cliff
    visible rather than theoretical.

    Returns throughput, latency percentiles, max queue depth and rejections. Watch what happens
    between rho=0.9 and rho=1.05: throughput flattens (it cannot exceed capacity) while LATENCY and
    QUEUE DEPTH explode. That is what "the site is down" actually looks like in metrics.
    """
    rng = random.Random(seed)
    service_time = service_time_ms / 1000
    capacity_tps = workers / service_time

    queue = deque()
    free_at = [0.0] * workers
    latencies = []
    rejected = 0
    max_queue = 0

    t = 0.0
    n_arrivals = int(arrival_tps * duration_seconds)
    for _ in range(n_arrivals):
        t += rng.expovariate(arrival_tps)            # Poisson arrivals, like real traffic

        # 1. workers that are free by now pick up queued work (this must happen even on an
        #    arrival we go on to reject -- otherwise rejections would starve the workers)
        for i in range(workers):
            if queue and free_at[i] <= t:
                arrived = queue.popleft()
                start = max(arrived, free_at[i])
                free_at[i] = start + service_time
                latencies.append(free_at[i] - arrived)

        # 2. admission control: a FULL queue means shed now rather than accept work we can't finish
        if queue_limit is not None and len(queue) >= queue_limit:
            rejected += 1
            continue

        # 3. admit
        queue.append(t)
        max_queue = max(max_queue, len(queue))

    latencies.sort()

    def pct(p):
        if not latencies:
            return 0.0
        return latencies[min(int(p / 100 * len(latencies)), len(latencies) - 1)] * 1000

    return {
        "offered_tps": arrival_tps,
        "capacity_tps": round(capacity_tps, 1),
        "utilization": round(arrival_tps / capacity_tps, 3),
        "completed": len(latencies),
        "rejected": rejected,
        "p50_ms": round(pct(50), 1),
        "p99_ms": round(pct(99), 1),
        "max_queue": max_queue,
    }


if __name__ == "__main__":
    section("STEP 1 -- measure: what does ONE request cost today?")
    base_latency = total_latency(REQUEST_PROFILE)
    print(f"    components: {len(REQUEST_PROFILE)}, total latency {base_latency:.0f}ms")
    for name, ms, calls, max_tps, _ in REQUEST_PROFILE:
        print(f"      {name:22s} {ms:6.1f}ms x{calls}  = {ms * calls:6.1f}ms")
    print(f"    at {CURRENT_TPS} TPS, concurrency in flight = "
          f"{littles_law(CURRENT_TPS, base_latency / 1000):.0f} requests (Little's Law)")

    section("STEP 2 -- the arithmetic: Little's Law decides every number that follows")
    opt_latency = total_latency(with_optimisations(REQUEST_PROFILE))
    for tps in (CURRENT_TPS, TARGET_TPS):
        for latency_ms in (base_latency, opt_latency):
            concurrency = littles_law(tps, latency_ms / 1000)
            print(f"    {tps:3d} TPS x {latency_ms:5.0f}ms = {concurrency:6.1f} concurrent "
                  f"requests -> {workers_needed(tps, latency_ms / 1000)} sync workers "
                  f"at 70% target utilization")
    print(f"    read the 2nd and 4th rows together: cutting latency "
          f"{base_latency / opt_latency:.1f}x cuts the fleet {base_latency / opt_latency:.1f}x.")
    print("    LATENCY REDUCTION AND CAPACITY ARE THE SAME LEVER. Pull it first -- it's free to run.")

    print("\n    and why you never plan for 100% utilization:")
    for u in (0.5, 0.7, 0.8, 0.9, 0.95, 0.99):
        print(f"      {u:4.0%} utilized -> response time x{utilization_latency_multiplier(u):5.1f}")
    print("      'CPU is only at 90%' means your p99 is already 10x your service time.")

    section("STEP 3 -- find the real bottleneck (it is never the app tier)")
    print(f"    required capacity at {TARGET_TPS} TPS:\n")
    print(f"      {'component':22s} {'needs':>8s} {'max':>8s} {'util':>7s}  status")
    for row in analyse_profile(REQUEST_PROFILE, TARGET_TPS):
        print(f"      {row['component']:22s} {row['required_tps']:7.0f}  {row['max_tps']:7.0f} "
              f"{row['utilization']:7.1%}  {row['status']}")
    print("\n    the fix for each:")
    for row in analyse_profile(REQUEST_PROFILE, TARGET_TPS):
        if row["status"] != "ok":
            print(f"      {row['component']:22s} -> {row['strategy']}")
    print("\n    note the two that cannot be solved by scaling YOUR code: the payment gateway's")
    print("    150 TPS limit (a commercial conversation, plus queueing + backpressure on your")
    print("    side) and the single DB primary for writes (batch, shard, or move the write off")
    print("    the request path).")

    print("\n    and Amdahl's Law on the serialised fraction:")
    for serial in (0.0, 0.05, 0.10, 0.25):
        speedups = [f"{amdahl_speedup(1 - serial, n):.1f}x" for n in (2, 6, 12, 50)]
        ceiling = f"{1 / serial:.0f}x" if serial else "unbounded"
        print(f"      {serial:4.0%} serial -> 2/6/12/50 workers give {', '.join(speedups)} "
              f"(ceiling {ceiling})")
    print(f"      with 10% of the request behind one shared lock, 50 pods buy you "
          f"{amdahl_speedup(0.9, 50):.1f}x, not 50x.")

    section("STEP 4 -- remove work before buying capacity")
    optimised = with_optimisations(REQUEST_PROFILE)
    new_latency = total_latency(optimised)
    print(f"    latency {base_latency:.0f}ms -> {new_latency:.0f}ms "
          f"({base_latency / new_latency:.1f}x faster)")
    print(f"    concurrency at {TARGET_TPS} TPS: "
          f"{littles_law(TARGET_TPS, base_latency / 1000):.0f} -> "
          f"{littles_law(TARGET_TPS, new_latency / 1000):.0f} requests in flight")
    print(f"    sync workers needed: {workers_needed(TARGET_TPS, base_latency / 1000)} -> "
          f"{workers_needed(TARGET_TPS, new_latency / 1000)}")
    print("\n    what changed, in payoff order:")
    print(with_optimisations.__doc__.split("\n", 2)[2].rstrip())

    print("\n    the cache maths, which is why caching is always the first move:")
    for hit in (0.0, 0.5, 0.8, 0.9, 0.95, 0.99):
        print(f"      hit ratio {hit:4.0%} -> backend sees "
              f"{effective_backend_tps(TARGET_TPS, hit):6.1f} TPS, "
              f"avg latency {average_latency_with_cache(hit):5.1f}ms")
    print("      0->80% removes 480 TPS of load; 95->99% removes 24. Most of the win is early.")

    section("STEP 5 -- size what's left, then protect it")
    print(f"    app tier (asyncio, I/O-bound, ~50 concurrent per worker):")
    print(f"      {workers_needed(TARGET_TPS, new_latency / 1000, per_worker_concurrency=50)} pods "
          f"+ HPA on p95 latency or queue depth, min 3 across 3 AZs")
    print(f"    DB connection pool per pod: "
          f"{pool_size(TARGET_TPS, 0.008)} (600 TPS x 8ms of DB time, +30% headroom)")
    pods = workers_needed(TARGET_TPS, new_latency / 1000, per_worker_concurrency=50)
    print(f"      total connections = {pods} pods x {pool_size(TARGET_TPS, 0.008)} = "
          f"{pods * pool_size(TARGET_TPS, 0.008)} -- check this against max_connections!")
    min_p, recommended_p = kafka_partitions(TARGET_TPS, per_consumer_tps=100)
    print(f"    Kafka partitions for the async work: minimum {min_p}, "
          f"provision {recommended_p} (room to scale out without repartitioning)")
    print(f"    read replicas: 600 TPS of reads at 90% cache hit = 60 TPS -> 1 replica is plenty;")
    print(f"      the replica exists for FAILOVER and for analytics, not for this load")
    print("\n    and the protection, because capacity is never exact:")
    print("      - rate limit per API key (see 08_scaling_production_resilience/03_rate_limiter.py)")
    print("      - circuit breaker on the payment gateway (02_circuit_breaker.py)")
    print("      - a BOUNDED queue + load shedding: reject with 429 and Retry-After rather than")
    print("        accepting work you cannot finish (an unbounded queue just moves the failure)")
    print("      - timeouts everywhere, shorter than the caller's, so slow != infinite")

    section("STEP 6 -- prove it: the load test, and the utilization cliff")
    print("    one worker pool, 12 workers, 20ms service time (capacity = 600 TPS):\n")
    print(f"      {'offered':>8s} {'util':>7s} {'done':>7s} {'p50':>8s} {'p99':>9s} {'maxq':>6s}")
    for tps in (100, 300, 480, 540, 570, 600, 660):
        r = simulate(tps, service_time_ms=20, workers=12, duration_seconds=30)
        print(f"      {r['offered_tps']:7d}  {r['utilization']:6.0%} {r['completed']:7d} "
              f"{r['p50_ms']:7.1f}ms {r['p99_ms']:8.1f}ms {r['max_queue']:6d}")
    print("\n    the cliff is the whole point: between 90% and 110% of capacity, throughput stops")
    print("    improving while p99 and queue depth run away. 'It was fine at 540 TPS' is not")
    print("    evidence that 600 is safe -- which is why you load-test to 2x the target.")

    print("\n    the same pool with load shedding (queue_limit=50):\n")
    print(f"      {'offered':>8s} {'done':>7s} {'rejected':>9s} {'p99':>9s} {'maxq':>6s}")
    for tps in (600, 900, 1200):
        r = simulate(tps, 20, 12, duration_seconds=30, queue_limit=50)
        print(f"      {r['offered_tps']:7d} {r['completed']:7d} {r['rejected']:9d} "
              f"{r['p99_ms']:8.1f}ms {r['max_queue']:6d}")
    print("    overload now costs some 429s and KEEPS p99 bounded for everyone else.")
    print("    without shedding, every request is slow and eventually all of them time out --")
    print("    a worse outcome for 100% of users than a fast failure for 20% of them.")

    section("the cost conversation (have it before someone else does)")
    naive_pods = workers_needed(TARGET_TPS, base_latency / 1000)
    tuned_pods = workers_needed(TARGET_TPS, new_latency / 1000, per_worker_concurrency=50)
    print(f"    brute force  : {naive_pods:4d} pods = ${instance_cost(naive_pods):,}/month")
    print(f"    after tuning : {tuned_pods:4d} pods = ${instance_cost(tuned_pods):,}/month "
          f"+ a cache + a queue (~$200)")
    print(f"    saving       : ~${instance_cost(naive_pods) - instance_cost(tuned_pods) - 200:,}"
          f"/month, AND p99 latency improved {base_latency / new_latency:.0f}x")
    print("    this is the version of the answer that gets remembered: scaling well is cheaper")
    print("    than scaling hard, and the engineering that gets you there also makes it faster.")

    section("the 60-second spoken answer")
    print("""  "First I'd refuse to answer until I had numbers -- current p50/p99, the per-request
  cost in CPU and DB time, and which component saturates first. 6x traffic is only scary if you
  don't know where it lands.

  Then the arithmetic. Little's Law: concurrency equals arrival rate times latency. At 600 TPS and
  282ms that's 169 requests in flight; at 120ms it's 72. So my FIRST move is always to cut
  per-request work rather than buy 6x the fleet -- fix the N+1, cache the hot reads, batch the
  writes, and push anything the user doesn't wait for -- emails, webhooks, reporting -- onto a
  queue. On this profile that's a 2.4x latency cut, which absorbs a large slice of the traffic
  increase on its own and improves latency instead of merely surviving it.

  Then I scale what's left, horizontally, because the app tier is stateless. I size pools with
  Little's Law too -- 600 TPS times 8ms of DB time is 9 concurrent queries, so a pool of 12 per
  pod, and I multiply that by pod count and check it against max_connections, because the classic
  way to take a database down is to scale the app tier. Kafka partitions get provisioned at 2-3x
  the target so I can scale consumers later without repartitioning.

  The bottleneck usually isn't mine to scale. Here it's the payment gateway at 150 TPS -- that's a
  commercial conversation plus queueing and backpressure on my side -- and the single write
  primary, which I handle by batching and by moving writes off the request path.

  I never plan past about 70% utilization, because queueing delay goes as 1/(1-rho): at 90% your p99
  is already 10x your service time. And I protect the system with timeouts, circuit breakers, rate
  limits and a BOUNDED queue that sheds load with 429s -- a fast failure for 20% of traffic beats
  a slow failure for 100%.

  Finally I prove it: load-test to 1200 TPS, not 600, watch saturation signals -- queue depth,
  pool waits, replication lag -- and set autoscaling on p95 latency rather than CPU, because CPU
  is a lagging indicator for an I/O-bound service.\"""")

# EXPERIMENT 1: change TARGET_TPS to 6000 and re-run. Which component becomes the bottleneck that
# cannot be fixed by caching or batching? That is the point where the architecture, not the config,
# has to change (sharding, CQRS, or cell-based isolation).
# EXPERIMENT 2: in simulate(), set workers=12 and service_time_ms=40 (capacity 300 TPS) and offer
# 600 TPS. Watch max_queue grow without bound -- that is an unbounded queue hiding an outage.
# EXPERIMENT 3: add a `per_worker_concurrency` of 1 for the app tier (sync WSGI) and recompute the
# pod count. The gap between that and the async number is the business case for asyncio.
# EXPERIMENT 4: plot (print) utilization_latency_multiplier from 0.5 to 0.99 in steps of 0.01 and
# find where it crosses 10x. Memorise that number -- it is your autoscaling trigger.

# EXERCISE: extend analyse_profile() to also report the COST of each scaling strategy (a read
# replica, a Redis cluster, 6x pods, an extra Kafka broker) and output a ranked plan: cheapest
# change that removes the current bottleneck, then re-run the analysis to find the NEXT one. That
# iteration -- fix the bottleneck, re-measure, find the new bottleneck -- is the actual job.
