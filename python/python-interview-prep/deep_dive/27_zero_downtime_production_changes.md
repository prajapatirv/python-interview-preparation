# Deep Dive 27 — Zero-Downtime Changes in a Distributed Production System

> Runnable companion: [`13_system_design_scenarios/01_zero_downtime_change.py`](../13_system_design_scenarios/01_zero_downtime_change.py)
> Related deep dives: [12 — Scaling applications](12_scaling_applications.md) ·
> [19 — Production stability & monitoring](19_production_stability_monitoring.md) ·
> [28 — Observability](28_observability_distributed_systems.md) ·
> [29 — Capacity scaling](29_capacity_scaling_tps.md) ·
> [15 — Kafka failure handling](15_kafka_failure_handling.md)

## What interviewers are actually probing

The question is usually asked as *"there's a bug in production affecting customers — walk me through
fixing it with zero downtime."* It's an experience test. They can tell in thirty seconds whether
you've been on call, because of **what you reach for first**.

- A junior answer starts writing the fix.
- A mid answer describes a rolling deploy.
- A **senior answer mitigates before it fixes** — flag off, traffic shifted, bleeding stopped —
  *then* fixes calmly, and separately names what it costs.

The three things they're specifically listening for:

1. **MITIGATE ≠ FIX.** The first move takes seconds and involves no deploy. Shipping code under
   pressure is how you turn one incident into two.
2. **Schema changes are the hard part.** Anyone can roll pods. Knowing that a column rename needs
   **three deploys** (expand → migrate → contract) is the differentiator.
3. **Zero downtime is bought, not free.** Blue/green costs 2× infrastructure; a canary needs enough
   traffic to be statistically meaningful; expand/migrate/contract means a week of dual writes. Name
   the price.

---

## Must-know points

- **The order is: declare → mitigate → stabilise → diagnose → fix → verify → postmortem.** Mitigation
  comes before diagnosis, and the clock stops at *stabilise*, not at *fix*.
- **Mitigations that need no deploy**, fastest first: feature flag / kill switch, traffic shift
  (previous version, another AZ/region/cell), load shedding or rate limiting the abusive caller,
  horizontal scale-out, cache the expensive path.
- **~80% of incidents are caused by a change.** Look at the last hour of deploys and flag flips
  *before* you read code.
- **Liveness ≠ readiness.** Liveness failing → *restart me*. Readiness failing → *remove me from the
  load balancer*. Conflating them causes restart loops.
- **A rolling deploy is only zero-downtime if you drain first and gate on readiness.** Skip either
  and you get the "every deploy has a 2-minute error spike" that teams wrongly accept as normal.
- **Blue/green**: deploy to the idle environment, verify with zero customer traffic, flip atomically.
  Rollback is the same flip — instant, no rebuild. Cost: 2× infrastructure during the switch.
- **Canary**: route a small % of real traffic to the new version, measure the **canary's own** error
  rate, abort automatically on SLO breach. Needs volume to mean anything.
- **Schema: expand → migrate → contract.** Add nullable columns and dual-write; backfill in batches;
  switch reads; drop the old column *days* later.
- **Graceful shutdown**: SIGTERM → fail readiness → drain in-flight → flush producers / commit
  offsets / close pools → exit 0, all inside `terminationGracePeriodSeconds`.
- **Every change must be reversible**, and the rollback must have been rehearsed. An untested
  rollback is not a rollback.

---

## Interview questions and full answers

### Q1. Walk me through it. Production is broken; what do you do?

**Step 0 — Declare the incident.** One channel, one commander, one scribe. This sounds like process
theatre and isn't: without it you get four engineers independently restarting things, and nobody can
reconstruct afterwards what changed. State explicitly: *what is the customer impact*, *what is the
SLI*, *who owns the mitigation*.

**Step 1 — MITIGATE, without a deploy.** Fastest first:

| Mitigation | Time to effect | When it applies |
|---|---|---|
| **Feature flag off** | ~30s | the bad behaviour is behind a flag (so: put every risky change behind one) |
| **Traffic shift** | 1–2 min | roll back to the previous version, or shift away from a bad AZ/region/cell |
| **Load shed / rate limit** | ~1 min | one caller or one endpoint is the problem; protect everyone else |
| **Scale out** | 2–5 min | it's saturation, not a bug — more capacity genuinely helps |
| **Degrade deliberately** | ~1 min | turn off the expensive non-critical path (recommendations, analytics) and keep checkout alive |

The feature-flag path is the one to emphasise, because it has a prerequisite you build *in advance*:

```python
if flags.enabled("new-pricing-engine", default=False):
    price = new_pricing(order)
else:
    price = legacy_pricing(order)          # the fallback must stay working until the flag is deleted
```

Flags are read from a store the app re-reads every few seconds (LaunchDarkly, Unleash, a DynamoDB or
Redis key) so flipping one needs no restart. The discipline: **default off, and delete the flag once
the change is proven** — a permanent flag is a permanent untested code path.

**Step 2 — STABILISE and say so in metrics.** "Error rate back to 0.02%, p99 back to 180ms, queue
depth draining." The clock stops here, not when the fix ships. If you can't state recovery in numbers,
you don't have observability ([28](28_observability_distributed_systems.md)).

**Step 3 — DIAGNOSE with the pressure off.** Correlation ID → trace → logs. And look at the **diff**
first: deploys, flag flips, config changes, infrastructure changes in the last hour. Most incidents
are caused by a change, so "what changed?" beats "what's broken?" as an opening question.

**Step 4 — FIX and ship it safely.** Rolling or blue/green, behind a canary, with automated abort and
a tested rollback. Schema changes get expand → migrate → contract (Q5).

**Step 5 — VERIFY on the canary metrics**, not on the pipeline's green tick. A successful deploy and a
working system are different claims.

**Step 6 — BLAMELESS POSTMORTEM.** Three questions, each generating one action item with an owner and
a date: *what made it possible?* (the code or design gap), *what made it slow to detect?* (the missing
alert), *what made it slow to mitigate?* (the missing flag or runbook). The second and third usually
matter more than the first, because they generalise to the next incident.

---

### Q2. What's the difference between liveness and readiness, and why does it matter?

They answer different questions and have different consequences:

| Probe | Question | Failing means | Typical check |
|---|---|---|---|
| **Liveness** | "Am I alive?" | **restart me** | the process responds at all |
| **Readiness** | "Can I take traffic?" | **remove me from the LB** | DB pool connected, cache warm, migrations done, not shutting down |
| **Startup** | "Am I still booting?" | **wait, don't judge me yet** | used to give slow starters a long grace period |

**The two failure modes from conflating them:**

1. **Liveness that checks dependencies** → the database has a blip, every pod's liveness fails, the
   orchestrator restarts the *whole fleet*, and now you have a cold-cache thundering herd on a database
   that was already struggling. **Liveness must never check a dependency.** It checks "is this process
   wedged?" — nothing more.
2. **No readiness gate** → a pod joins the load balancer before its connection pool is up and serves
   503s for 30 seconds. This is the real cause of "deploys always cause a brief error spike".

```python
@app.get("/health/live")          # liveness: cheap, local, no dependencies
async def live():
    return {"status": "ok"}

@app.get("/health/ready")         # readiness: the things that must work to serve a request
async def ready():
    if shutting_down:             # set by the SIGTERM handler — this is what drains traffic
        raise HTTPException(503, "draining")
    if not await db.ping():
        raise HTTPException(503, "db unavailable")
    return {"status": "ready"}
```

See [`08_scaling_production_resilience/04_health_checks_graceful_shutdown.py`](../08_scaling_production_resilience/04_health_checks_graceful_shutdown.py).

---

### Q3. Rolling vs blue/green vs canary — when do you use each?

| | Rolling | Blue/green | Canary |
|---|---|---|---|
| How | replace instances in batches | two full environments, flip the pointer | route x% of traffic to the new version |
| Extra infra | ~1 batch | **2× during the switch** | ~1 extra instance |
| Rollback | redeploy the old version (minutes) | **flip back (seconds)** | shift traffic back (seconds) |
| Both versions live at once? | **yes** | briefly (during the flip) | **yes, deliberately** |
| Verifies with real traffic? | not before customers see it | smoke test with zero traffic | **yes, on a small %** |
| Best for | routine, low-risk changes | risky changes, big-bang cutovers, a fast escape hatch | changes whose effect you can only measure in production |

**Rolling is the default**, and it's only zero-downtime if you do both of these:

```
1. DRAIN  — fail readiness so the LB deregisters the instance, then WAIT for in-flight
            requests to finish (the LB's deregistration delay, typically 30s) before
            stopping the process.
2. GATE   — don't return the new instance to the pool until its readiness probe passes,
            so cold-start 503s are absorbed by the probe instead of by customers.
```

The companion simulation shows the same deploy with and without those two: **0 failed requests vs
~22%**, with every pod reporting "Running" in both cases. *"The pods were all healthy"* and *"zero
requests failed"* are different claims.

**Blue/green's real value is the rollback**, not the deploy. Flipping a target group back is seconds
and needs no build — during an incident that speed is worth the doubled cost. Its two gotchas:
**database compatibility** (both environments share one database, so the schema must satisfy both —
Q5), and **stateful connections** (long-lived WebSockets or Kafka consumers don't "flip"; they need
draining).

**Canary's value is bounding the blast radius** — and the detail most people get wrong:

> **Measure the canary's OWN error rate, not the fleet average.**

If 1% of traffic goes to a version failing 20% of calls, the fleet-wide error rate is 0.2% — under a
1% SLO threshold, so a naive check passes and you promote a broken build. Comparing the canary cohort
against a control cohort is what makes it work.

The other caveat is **statistical significance**: at 1% of 100 requests/minute, a canary step sees one
request. You need either volume or time. A canary at low traffic is theatre — say so, and use
blue/green with a thorough smoke test instead.

**Cell-based / shuffle-sharded deployment** is worth naming as the next step up: partition customers
into N independent cells, deploy cell by cell, and a bad deploy affects 1/N of users with *no* traffic
splitting needed. It's how large AWS services bound blast radius, and it composes with everything
above.

---

### Q4. How do you deploy when the two versions must coexist?

**During any rolling deploy, version N and N+1 run simultaneously** — and they share a database, a
cache, and Kafka topics. Every change must therefore be **backward compatible for one version**.
Four surfaces, four rules:

**1. API contracts — only ever add.**

```
SAFE:    add an optional field; add a new endpoint; add an enum value CONSUMERS IGNORE
UNSAFE:  remove a field; rename a field; make an optional field required;
         narrow a type; change a status code; change the meaning of a value
```

For a breaking change, **version the endpoint** (`/v2/orders`) and run both until the old one's
traffic is zero — which you know because you *measured* it per version.

**2. Events / Kafka — schema compatibility is enforceable, so enforce it.** Set the Schema Registry to
`BACKWARD` so a new producer's messages are readable by old consumers: add fields **with defaults**,
remove optional fields, never change a type. And deploy **consumers before producers**, so the
reader understands the new shape before anything writes it. See
[16 — Schema management](16_kafka_schema_management.md).

**3. Caches — version the key, don't hope.** If the cached value's shape changes, old pods will
deserialise new entries and crash. Put the version in the key (`order:v2:{id}`), so the two versions
use disjoint keyspaces and the old entries expire on their own.

**4. Database — expand/migrate/contract.** That's Q5.

---

### Q5. How do you change a database schema with zero downtime?

**Never in one step.** The question to ask about any migration is: *"if the old code is still running
when this lands, does it break?"* A rename always does:

```sql
ALTER TABLE orders RENAME COLUMN customer_name TO full_name;   -- every v1 pod breaks instantly
```

**Expand → migrate → contract**, as three independent, individually reversible deploys:

```
DEPLOY 1  — EXPAND
    ALTER TABLE orders ADD COLUMN first_name text NULL;     -- nullable, no default on a big table
    ALTER TABLE orders ADD COLUMN last_name  text NULL;
    Application: DUAL-WRITE. Every write fills customer_name AND first/last.
    Reads still use customer_name. Old pods are unaffected — they ignore the new columns.

DEPLOY 2  — MIGRATE
    Backfill in BATCHES (never one UPDATE over 50M rows):
        UPDATE orders SET first_name = split_part(customer_name,' ',1), ...
        WHERE id BETWEEN :lo AND :hi;          -- 1k-10k rows, committed, throttled
    Then switch READS to first/last. Still dual-writing, so a rollback to deploy 1 is safe.

DEPLOY 3  — CONTRACT  (days later, not minutes)
    Stop dual-writing. Verify nothing reads customer_name (grep + query logs + a metric
    counting reads of that column). Then:
        ALTER TABLE orders DROP COLUMN customer_name;
```

**Why each part is shaped that way:**

- **Nullable, no default.** On MySQL and older Postgres, adding a column *with a default* rewrites the
  whole table while holding a lock. (Postgres 11+ optimises constant defaults, but nullable-then-backfill
  is the portable habit.)
- **Batched backfill.** One giant `UPDATE` holds locks, bloats the WAL, blows out replication lag, and
  can't be paused. Batch it, commit each batch, throttle on replication lag, and make it **resumable**
  from a checkpoint — the same pattern as [30 — Large file processing](30_large_file_processing.md).
- **Days between deploy 2 and 3.** That gap *is* the rollback window. Dropping the column on Tuesday
  means you cannot roll back to Monday's build.
- **The lock matters more than the migration.** `ALTER TABLE` needing an `ACCESS EXCLUSIVE` lock will
  queue behind a long-running read and then block every subsequent query — a 10ms migration becomes a
  5-minute outage. Always set `lock_timeout` so the migration fails fast instead of queueing:

```sql
SET lock_timeout = '3s';          -- fail fast; retry later rather than blocking the world
CREATE INDEX CONCURRENTLY idx_orders_customer ON orders(customer_id);   -- no write lock
```

`CREATE INDEX CONCURRENTLY` (Postgres) / online DDL (MySQL 8) are the other half: a plain
`CREATE INDEX` locks writes for the duration.

**The same rule applies to adding a NOT NULL constraint** (add nullable → backfill → add a `CHECK NOT
VALID` → `VALIDATE CONSTRAINT`), and to **removing** a field from an API or event: stop writing it,
confirm nothing reads it, *then* remove it.

---

### Q6. What does graceful shutdown actually involve?

Kubernetes sends `SIGTERM`, waits `terminationGracePeriodSeconds` (default 30), then `SIGKILL`. What
you do in that window decides whether a deploy costs zero requests or hundreds:

```python
shutting_down = False

def handle_sigterm(signum, frame):
    global shutting_down
    shutting_down = True          # readiness now fails → the LB stops sending new requests

signal.signal(signal.SIGTERM, handle_sigterm)

# the ordered shutdown sequence
# 1. fail readiness (above) and SLEEP a few seconds — the LB needs time to notice
# 2. stop accepting new work; let in-flight requests finish (with a timeout)
# 3. flush: producer.flush(), commit Kafka offsets, close the DB pool, close the HTTP client
# 4. exit 0
```

The step people miss is **step 1's sleep**. Failing readiness is not instantaneous for the load
balancer — it polls every few seconds. Exiting immediately after failing readiness means the LB is
still routing to you. A `preStop` hook sleeping 5–10 seconds is the standard fix, and it must fit
inside the grace period alongside everything else.

**What you lose without draining:** in-flight requests become client-side 502s; uncommitted Kafka
offsets cause redelivery (survivable if your consumer is idempotent, which is why idempotency matters
here too); and an **unflushed producer buffer loses events entirely** — those are gone, not retried.

For a **Kafka consumer** specifically, graceful shutdown means: stop polling, finish the current
batch, commit, then `consumer.close()`. `close()` leaves the group cleanly so the rebalance happens in
milliseconds rather than after a 45-second session timeout — during which those partitions are
unconsumed. See [`06_kafka/08_kafka_to_aurora_sink.py`](../06_kafka/08_kafka_to_aurora_sink.py).

---

### Q7. What capabilities make zero-downtime possible? (Build these before the incident.)

This is the question behind the question, and volunteering it is what makes the answer senior. You
cannot *decide* to have zero downtime during an incident; you can only *spend* capabilities you already
built:

| Capability | Without it… |
|---|---|
| **Stateless services** | you can't replace an instance freely — sessions/state live in it |
| **Liveness + readiness that mean different things** | restart loops, or cold pods serving 503s |
| **Feature flags on every risky path** | your only mitigation is a deploy, under pressure |
| **Backward-compatible APIs, events and schemas** | the two versions can't coexist, so there's no rolling anything |
| **Idempotent operations** | a retry or a redelivery double-charges someone, so you daren't retry |
| **Observability you can query in minutes** | you can't tell whether you've mitigated, or what to fix |
| **A rehearsed rollback** | your rollback is a plan, not a capability |
| **Automated canary analysis** | a human watching a dashboard is not a rollback strategy |
| **Batched, resumable migrations** | every schema change is an outage risk |
| **Load shedding / rate limits** | overload collapses instead of degrading |

The sentence that lands: **"zero downtime is a property of the system's design, not of the deploy
procedure."** A stateful service with a destructive migration cannot be deployed with zero downtime no
matter how careful the pipeline is.

---

### Q8. What does it cost? (Name the trade-offs.)

Every technique above has a price, and naming them unprompted is the strongest signal in this whole
topic:

- **Blue/green: 2× infrastructure** during the switch, and you still share one database — so the
  schema must satisfy both versions anyway. Blue/green does *not* exempt you from Q5.
- **Canary: needs traffic volume.** At 10 requests/minute a 1% canary is meaningless. It also needs
  automated analysis, which is real engineering to build.
- **Expand/migrate/contract: three deploys and a week of dual writes**, during which the data model is
  duplicated and both paths need tests. Teams skip the contract step and accumulate dead columns
  forever — so it needs a tracked ticket, not good intentions.
- **Feature flags: every flag is a branch**, so N flags are 2^N code paths. Untested combinations are
  where bugs hide. Flags need an owner and a deletion date.
- **Idempotency: a storage cost** (the dedup table/index) and a design cost (every operation needs a
  natural or supplied key).
- **Draining: slower deploys.** A 30-second deregistration delay × 20 batches is 10 minutes of rollout.
- **Cell-based architecture: operational multiplication.** N cells to monitor, deploy and debug.

And the honest closer: **sometimes the right answer is planned downtime.** A 2-minute maintenance
window at 3am on a Sunday, announced in advance, can be cheaper and *safer* than a three-week
expand/migrate/contract for an internal tool with 50 users. Knowing when zero downtime isn't worth
buying is part of the skill.

---

## A worked example

**Incident: a pricing change ships; 12% of checkouts start returning 500.**

```
14:02  Error rate alert fires: checkout 5xx 0.1% -> 12%. Burn rate 120x. PAGE.
14:03  DECLARE. Incident channel open, commander named. Customer impact stated:
       "roughly 1 in 8 checkouts failing since 13:58."
14:04  "What changed?" -> deploy at 13:57 enabled flag `new-pricing-engine` at 100%.
       Correlation is enough to act on. Diagnosis can wait.
14:05  MITIGATE: flag -> off. No deploy, no restart.
14:06  STABILISE confirmed: 5xx back to 0.1%, p99 back to 180ms. Clock stops.
       Customer impact window: 8 minutes.
--- pressure off ---
14:20  DIAGNOSE: one trace from a failed request (correlation id from the alert) shows
       new_pricing() raising KeyError('tax_rate') for orders with no shipping address.
       Logs confirm: 100% of failures have shipping_address = null.
14:40  FIX: default the tax rate for addressless orders; add the missing test case;
       add a Pydantic validator so the field can't be absent silently.
15:10  SHIP: rolling deploy, drain + readiness gate. Flag stays OFF.
15:25  CANARY: flag on at 1% -> error rate matches the control cohort for 15 min.
       5% -> 25% -> 100% over 90 minutes, automated abort armed at a 1% error rate.
17:00  VERIFY: 100%, error rate 0.1%, p99 unchanged. Flag scheduled for deletion.
Next day  POSTMORTEM:
   What made it possible?  No test for an order without a shipping address; the field
                           was optional in the model but required by the new code path.
                           -> ACTION: contract test over all optional-field combinations.
   Slow to detect?         8 minutes. Acceptable, and the alert was on the right signal
                           (customer-facing error rate, not CPU).
                           -> ACTION: none.
   Slow to mitigate?       3 minutes, because the flag already existed.
                           -> ACTION: make "risky change behind a flag" a PR checklist item,
                              since this only worked because someone had already done it.
```

**What this timeline demonstrates:** mitigation at 14:05 before any diagnosis; the clock stopping at
*stabilise*, not at *fix*; "what changed?" as the first diagnostic question; the fix shipped slowly
and verified on a canary with the pressure off; and a postmortem whose actions address the *detection
and mitigation* path, not just the bug. The 8-minute impact window exists because the flag was already
there — which is the whole argument for building the capability in advance.

---

## Hands-on drills

1. Run the companion with `wait_for_ready=True` and `False`. Record the 503 count for each. That
   difference is the entire readiness argument in one number.
2. Set `warmup=10` with no readiness gate and watch the error count climb. Map that onto a real
   service: what takes 10 requests to warm up? (JIT, connection pools, a local cache.)
3. Write liveness and readiness endpoints for a service you know. Then deliberately make liveness
   check the database and describe, in two sentences, what happens during a 30-second DB blip.
4. Run `canary_deploy(new_version_error_rate=0.02, requests_per_step=200)`, then with
   `requests_per_step=20000`. Explain why the first one passes.
5. Write the three migrations for renaming `customer_name` → `first_name`/`last_name`, including the
   batched backfill with a resumable checkpoint. Then write the rollback for each of the three.
6. Add `SET lock_timeout` to a migration, hold a long transaction on the table in another session, and
   observe the migration failing fast instead of blocking every query behind it.
7. Implement a SIGTERM handler that fails readiness, sleeps 5s, drains, flushes and exits. Measure the
   total shutdown time against `terminationGracePeriodSeconds=30`.
8. Take a feature flag you've shipped and write its deletion ticket: what must be true before the old
   branch can be removed?
9. For a service you own, list which of the ten capabilities in Q7 you actually have. The gaps are
   your next three tickets.

---

## The 60-second spoken answer

> "I separate mitigating from fixing, because shipping code under pressure is how one incident becomes
> two. First I declare the incident — one channel, one commander — and state the customer impact in
> terms of an SLI. Then I mitigate *without a deploy*: flip the feature flag off, shift traffic back to
> the previous version or away from a bad AZ, rate-limit an abusive caller, or scale out if it's
> genuinely saturation. That's thirty seconds to a couple of minutes, and it works because every risky
> change ships behind a flag that's default-off. Once the SLI has recovered — and I say that in
> numbers, not in vibes — the clock stops. Only then do I diagnose, and my first question is 'what
> changed in the last hour?', because most incidents are caused by a change.
>
> Then I ship the fix properly. Rolling deploy, which is only zero-downtime if I drain first — fail
> readiness so the load balancer deregisters, wait for in-flight requests — and gate the new instance
> on its readiness probe so cold-start 503s hit the probe instead of customers. Liveness and readiness
> mean different things: liveness failing restarts me, readiness failing takes me out of the pool, and
> liveness must never check a dependency or one database blip restarts the whole fleet. For a risky
> change I'd use blue/green, because the rollback is a pointer flip in seconds with no rebuild —
> at the cost of 2× infrastructure. And I'd put a canary in front with *automated* abort on SLO breach,
> measuring the canary cohort's own error rate against a control, because averaging it over the fleet
> hides a 20% failure rate under a 1% threshold.
>
> The genuinely hard part is the schema, because during any rollout both versions share one database.
> So never a one-step rename: expand by adding nullable columns and dual-writing, migrate by
> backfilling in throttled resumable batches and switching reads, then contract by dropping the old
> column days later — and that gap is the rollback window. `lock_timeout` on every migration so an
> `ALTER TABLE` fails fast rather than queueing behind a long read and blocking the world, and
> `CREATE INDEX CONCURRENTLY`.
>
> And I'd say what it costs: blue/green doubles infrastructure, canaries need traffic volume to mean
> anything, expand/migrate/contract is three deploys and a week of dual writes, and every feature flag
> is an extra code path somebody has to delete. Zero downtime is a property of the system's design —
> stateless services, backward-compatible contracts, idempotent operations, a rehearsed rollback — not
> of the deploy procedure. And for a low-traffic internal tool, an announced two-minute window at 3am
> is sometimes the cheaper and safer answer."
