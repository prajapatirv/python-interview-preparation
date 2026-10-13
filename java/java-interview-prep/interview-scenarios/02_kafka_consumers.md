---
id: kafka-consumers
title: Kafka consumers — groups, offsets, rebalancing, lag
stack: java
skill: kafka
---
How to read these answers: every question is answered the way a senior engineer speaks in the room —
**a real situation first**, then the reasoning, then what goes wrong and how you would see it in
production. Code is deliberately minimal; where a config line helps, it is at the end.

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [fresher] What is a consumer group, and what happens if I run more consumers than partitions?
tags: consumer-groups, partitions, scaling, basics

**The live scenario**
An order-events topic has 6 partitions. The team scaled the `order-processor` service from 6 to 10 pods
expecting more throughput. Throughput did not move, and 4 pods showed zero messages processed.

**What the interviewer is really checking**
That you know the partition is the unit of parallelism, and that a group shares the work rather than copying it.

**How I answer it**
1. A consumer group is a set of consumers with the same `group.id` that **share** a topic: every partition is
   owned by exactly one consumer in the group at a time. That is how Kafka gives you parallelism *and* per-partition ordering.
2. A different group (say `analytics`) gets its own full copy of every message — that is how Kafka does pub/sub.
3. So with 6 partitions, at most 6 consumers in one group can be busy. Pods 7–10 sit idle as hot standbys —
   useful for failover, useless for throughput.
4. The fix in the scenario is to plan partition count for peak parallelism up front (we would have created the topic with
   12 or 24), or make each consumer faster.

**Trade-offs and what can go wrong**
- Adding partitions later is allowed, but it changes which partition a key hashes to, so ordering for existing keys breaks during the switch.
- Too many partitions has its own cost: more open files, longer leader elections, slower rebalances.

**How I'd monitor it**
Per-consumer assigned-partition count and records-consumed rate. A pod with zero assigned partitions is the giveaway.

**Follow-ups to expect**
- *Can two consumers in the same group read the same partition?* → Not in a normal consumer group. (Kafka 4's preview *share groups* relax this for queue-style work, at the cost of ordering.)
- *What if I need 20x parallelism on 6 partitions?* → Parallelise inside the consumer by key (see Q15) or repartition.

**60-second answer**
A consumer group is a team of consumers sharing a topic; each partition goes to exactly one member, so the partition count
caps the group's parallelism. Separate groups each get every message, which is how Kafka does pub/sub. If I run more consumers than partitions, the extras
are idle standbys — they help failover but not throughput. So I size partitions for the peak parallelism I expect, because adding partitions later reshuffles keys.

### Q2 [fresher] What is an offset, and where does Kafka remember how far my consumer has read?
tags: offsets, basics, __consumer_offsets

**The live scenario**
A developer restarted a consumer and was surprised it did not re-read the whole topic from the beginning — and another
time was surprised it *did* re-read the last few hundred messages.

**What the interviewer is really checking**
The difference between the consumer's in-memory position and the committed offset, and why replays happen.

**How I answer it**
1. Every record in a partition has an offset — its sequence number in that append-only log.
2. The consumer keeps a **position** in memory: the next offset it will fetch.
3. It periodically **commits** an offset to the internal topic `__consumer_offsets`, keyed by group + topic + partition.
   The committed value means "the next record I have not yet processed".
4. On restart, or when a partition moves to another consumer, reading resumes from the last **committed** offset, not the in-memory position.
5. So anything processed after the last commit gets processed again. That explains the "re-read a few hundred" case,
   and it is why at-least-once delivery is the normal case in Kafka.

**Trade-offs and what can go wrong**
Commit too early and a crash loses messages; commit too late and a crash replays more. Consumers must therefore tolerate duplicates.

**How I'd monitor it**
Committed offset vs log-end offset per partition — that difference is **lag** (Q11).

**Follow-ups to expect**
- *Is the message deleted after it is read?* → No. Retention is by time or size, independent of consumers. That is what makes replay possible.
- *What if no committed offset exists?* → `auto.offset.reset` decides (Q5).

**60-second answer**
An offset is a record's position in a partition. The consumer tracks where it is in memory and periodically commits "next offset to read" into the
internal `__consumer_offsets` topic for its group. After a restart or rebalance it resumes from the committed offset, so anything processed but not yet committed is replayed.
That is why Kafka is at-least-once by default, and why every consumer I build is idempotent.

### Q3 [mid] Auto-commit or manual commit? Tell me about losing messages with auto-commit.
tags: offsets, auto-commit, delivery-semantics, data-loss

**The live scenario**
A notifications service used the plain Kafka client with defaults (`enable.auto.commit=true`, every 5 s). It handed records to an
in-memory executor and returned to `poll()` immediately. During a deploy, pods were killed with work still queued. The offsets had
already been auto-committed, so about 2,000 customers never got their SMS. There was no error in any log.

**What the interviewer is really checking**
That auto-commit commits what was *polled*, not what was *processed* — and that you know where the loss window is.

**How I answer it**
1. Auto-commit runs inside `poll()`. It commits the offsets returned by the *previous* poll, on a timer.
   If processing is synchronous inside the loop, that is roughly at-least-once. The moment processing becomes asynchronous, the commit can run ahead of the work, and you get **silent loss**.
2. Our fix: disable auto-commit and commit **after** processing succeeds.
   - In Spring Kafka this is the default: the container commits after the listener returns (`AckMode.BATCH`), or per record or manually if you choose.
   - With async processing, commit only up to the highest offset that is *contiguously* complete.
3. Combine with graceful shutdown: stop polling, finish in-flight work, commit, then leave the group.

**Trade-offs and what can go wrong**
- Manual commit gives at-least-once, so you accept duplicates and make the handler idempotent (Q10).
- Committing after every record is safe but slow; committing per batch is the usual balance.

**How I'd monitor it**
Compare "events produced" with "notifications sent" per hour in Splunk. A gap with no errors is the classic signature of offset-before-work loss.

**Follow-ups to expect**
- *Is auto-commit ever fine?* → For lossy telemetry where a few lost records do not matter, yes.
- *What does Spring Kafka do by default?* → It sets `enable.auto.commit=false` and commits from the container after the listener returns.

**60-second answer**
Auto-commit commits on a timer whatever the last poll returned, not what I finished processing. If processing is async or the pod dies mid-batch,
those messages are marked done and silently lost — I have seen exactly that during a deploy. So I disable auto-commit, commit after successful processing
(Spring Kafka's container does this by default), shut down gracefully, and make the handler idempotent because at-least-once means duplicates.

**Minimal config**
```properties
enable.auto.commit=false
spring.kafka.listener.ack-mode=batch   # or record / manual_immediate
```

### Q4 [mid] commitSync or commitAsync — which do you use, and when?
tags: offsets, commitSync, commitAsync, performance

**The live scenario**
A high-volume clickstream consumer was committing synchronously after every batch. Under load, the commit round-trips took
a visible slice of each loop, and p99 processing time crept up.

**What the interviewer is really checking**
That you know the latency/safety trade-off, and the standard pattern that combines the two.

**How I answer it**
1. `commitSync` blocks until the broker confirms, and it retries on retriable errors. It is safe but adds a round-trip per commit.
2. `commitAsync` does not block and does **not** retry. A retry could commit an older offset after a newer one has succeeded, moving you backwards.
   You get a callback to log failures.
3. The standard pattern:
   - `commitAsync` in the hot loop for throughput;
   - `commitSync` once on shutdown, and in `onPartitionsRevoked` during a rebalance, so the final position is definitely stored before you lose the partition.
4. In Spring Kafka you rarely call either yourself. The container does it, and `syncCommits=true` is the default.

**Trade-offs and what can go wrong**
An async commit that silently fails means a slightly larger replay after the next rebalance. That is acceptable if handlers are idempotent.

**How I'd monitor it**
The `commit-latency-avg` and commit-rate metrics, plus a WARN log from the async callback, counted in Splunk.

**Follow-ups to expect**
- *Why doesn't commitAsync retry?* → Ordering. A retried old commit could overwrite a newer one.

**60-second answer**
commitSync is safe but blocking; commitAsync is fast but fire-and-forget without retries, because a retried stale commit could move the offset backwards.
In a hand-written consumer I use async in the loop and a final sync on shutdown and on partition revoke. In Spring Kafka the container handles it, and I just choose the ack mode.

### Q5 [mid] What does auto.offset.reset do? We started a new consumer group and it processed nothing.
tags: offsets, auto.offset.reset, new-consumer-group, replay

**The live scenario**
A new `fraud-scoring` service went live with a fresh `group.id`. The business expected it to score the last 3 days of transactions
still in the topic. It scored nothing historical, because `auto.offset.reset` defaults to `latest`.
On a different team the opposite happened: a renamed group id with `earliest` re-processed 7 days of payments and sent duplicate emails.

**What the interviewer is really checking**
That the setting only applies when there is **no valid committed offset**, and that changing a group id is a data decision, not a cosmetic one.

**How I answer it**
1. It applies only when the group has no committed offset for a partition (new group), or the committed offset is no longer valid (the data aged out of retention).
2. The options:
   - `latest` (default): start from new messages only.
   - `earliest`: start from the oldest retained record.
   - `none`: throw, so a human decides.
3. For important pipelines I prefer an explicit decision. Either `earliest` with idempotent processing, or start at a chosen point in time using
   `kafka-consumer-groups --reset-offsets --to-datetime` before the first start.
4. I treat a group-id rename like a schema change: it goes through review, because it silently resets the position.

**Trade-offs and what can go wrong**
If a consumer is down longer than retention, its offset falls off the log, the reset policy fires, and with `latest` you **skip** data without an error.

**How I'd monitor it**
Alert when a group's committed offset is older than the log-start offset (that means it fell out of retention). Log the resolved start offset on boot.

**Follow-ups to expect**
- *How do you start a group from a timestamp?* → `--reset-offsets --to-datetime`, or `offsetsForTimes()` plus `seek()` in code.

**60-second answer**
auto.offset.reset only kicks in when a group has no valid committed offset — a new group, or an offset that fell out of retention. `latest` skips history, `earliest` replays everything retained,
and `none` fails fast. I have seen both failure modes: a new service that skipped data, and a renamed group that replayed a week of emails. So I set it deliberately, and I review group-id changes.

### Q6 [mid] What is a rebalance, what triggers it, and what actually happens during one?
tags: rebalancing, consumer-groups, group-coordinator, basics

**The live scenario**
Every time the payments consumer was deployed, the dashboard showed consumption drop to zero for about two minutes, and lag jumped. The team assumed Kafka was slow.
In reality it was a rebalance.

**What the interviewer is really checking**
That you can name the triggers and explain why the classic protocol is "stop-the-world" for the group.

**How I answer it**
1. A rebalance is the group redistributing partitions among its members. One broker acts as the **group coordinator**, and one consumer acts as the leader that computes the assignment (in the classic protocol).
2. Triggers:
   - a member joins (scale-out, a pod starting during a deploy);
   - a member leaves cleanly (shutdown);
   - a member is considered dead: no heartbeat within `session.timeout.ms`, or no `poll()` within `max.poll.interval.ms`;
   - subscription changes, such as new partitions or a regex matching a new topic.
3. With the classic **eager** protocol, every member revokes *all* its partitions, rejoins, waits for the new assignment, and then resumes.
   The whole group stops consuming for the duration — that was the two-minute gap.
4. A rolling deploy of 6 pods can trigger 12 rebalances (one for each leave and each join).

**Trade-offs and what can go wrong**
Rebalances also cause duplicates: anything processed but not committed before revocation is processed again by the new owner.

**How I'd monitor it**
Rebalance count and rebalance latency metrics per group, and Splunk on the "partitions revoked/assigned" log lines, correlated with deploy times.

**Follow-ups to expect**
- *How do you make it hurt less?* → Q7.

**60-second answer**
A rebalance is the group coordinator reassigning partitions when membership changes — a consumer joins, leaves, misses heartbeats, or stops polling for too long.
With the classic eager protocol everyone gives up every partition and waits, so the group stops consuming, and uncommitted work gets replayed. A rolling deploy can trigger a dozen of them,
which is why deploys show up as lag spikes.

### Q7 [senior] How do you handle consumer-group rebalancing in production?
tags: rebalancing, cooperative-sticky, static-membership, deployments, kip-848, lag

**The live scenario**
Payments consumer group: 12 partitions, 6 pods on Kubernetes. Every rolling deploy caused 2–3 minutes of near-zero consumption and a lag spike of about 400k messages.
An alert fired on every release. On top of that, during traffic peaks, a slow downstream call made pods exceed `max.poll.interval.ms`. They were kicked out, which caused more rebalances —
a **rebalance storm**.

**What the interviewer is really checking**
That you treat rebalancing as something you **engineer around**, with a diagnosis-first approach, not a single config tweak.

**How I answer it**
1. **Diagnose the trigger first.** In Splunk, line up the "revoked/assigned" logs against three things:
   - deploy events (membership change);
   - "consumer poll timeout has expired" warnings (slow processing);
   - heartbeat or session expiries (GC pauses, network).

   Each cause has a different fix.
2. **Make each rebalance incremental.** Switch to the `CooperativeStickyAssignor`.
   Only the partitions that actually move are paused; everyone else keeps consuming. That cut the impact from "whole group stops" to "two partitions pause".
3. **Make deploy rebalances disappear.** Use **static membership**: `group.instance.id` set to the stable pod name (a StatefulSet makes this easy).
   A pod that restarts within `session.timeout.ms` gets its *same* partitions back with **no rebalance at all**.
   We set the session timeout above the pod restart time.
4. **Remove the slow-processing trigger.** Lower `max.poll.records` so a batch always finishes inside `max.poll.interval.ms`.
   Put a timeout on the downstream call. Never `sleep` in the poll loop. Move long work to a pause/resume or retry-topic pattern (Q17).
5. **Make rebalances safe.** Commit offsets in `onPartitionsRevoked` (Spring Kafka does this for you). Make handlers idempotent, so the replayed tail does no harm (Q10).
6. **Graceful shutdown.** On SIGTERM: stop polling, finish in-flight records, commit, then leave. Give the Kubernetes `terminationGracePeriodSeconds` enough room for this.
7. **Strategic fix.** On Kafka 4.x, the new consumer rebalance protocol (KIP-848, `group.protocol=consumer`) moves assignment to the broker and is incremental by design.
   It is the long-term answer.

**Trade-offs and what can go wrong**
- Static membership delays failover of a pod that is **truly** dead until `session.timeout.ms` expires — 60 seconds of no consumption on its partitions instead of an immediate move. You are trading fast failover for calm deploys.
- Cooperative rebalancing takes two rounds, so a full rebalance takes slightly longer in total, but almost nobody is stopped during it.
- Moving from eager to cooperative needs a two-step rolling upgrade (both assignors listed, then remove the old one). Flipping it in one deploy fails.

**How I'd monitor it**
Rebalance rate and latency per group, lag per partition during deploys, and the count of poll-timeout warnings. The alert is "more than N rebalances in 10 minutes", not "one rebalance happened".

**Numbers I quote**
Deploy-time lag peak went from about 400k to under 5k. Rebalance-related consumption gaps went from roughly 150 s to about 3 s. Deploy alerts went to zero.

**Follow-ups to expect**
- *Why not just raise `max.poll.interval.ms` to 30 minutes?* → It hides the slow consumer. A genuinely hung consumer then holds its partitions for 30 minutes before anyone notices. Fix the processing time instead.
- *What happens to in-flight messages during revoke?* → Finish or abandon them, commit what is complete, and let the new owner replay the rest — which is safe because the handler is idempotent.
- *Does the new protocol remove the need for static membership?* → It greatly reduces the pain, but static membership still avoids the move entirely for a quick restart.

**60-second answer**
I start by finding what triggers the rebalances — deploys, slow processing that breaches max.poll.interval, or missed heartbeats — because each has a different fix.
Then I make rebalances incremental with the cooperative-sticky assignor, and make deploy restarts invisible with static membership. I remove slow-processing triggers with smaller poll batches and timeouts,
and I make rebalances harmless with commit-on-revoke plus idempotent handlers. On Kafka 4 I move to the broker-side KIP-848 protocol.
In my last system that took deploy lag spikes from 400k to under 5k.

**Minimal config**
```properties
partition.assignment.strategy=org.apache.kafka.clients.consumer.CooperativeStickyAssignor
group.instance.id=${POD_NAME}
session.timeout.ms=60000
max.poll.records=200
```

### Q8 [senior] A consumer keeps getting kicked out of the group and the same messages are processed again and again. Diagnose it.
tags: rebalancing, max.poll.interval.ms, slow-consumer, duplicates, troubleshooting

**The live scenario**
An invoice-generation consumer fetched 500 records per poll. Each record called a PDF service that sometimes took 2 seconds.
500 × 2 s = 1,000 s, far beyond the 300 s `max.poll.interval.ms`. The consumer was evicted mid-batch, and its partitions moved.
The new owner re-processed the uncommitted batch, also got slow, and also got evicted. Customers received the same invoice four times.

**What the interviewer is really checking**
That you understand the **two** liveness checks (heartbeat vs poll interval), and can do the arithmetic.

**How I answer it**
1. Kafka checks liveness twice:
   - a background **heartbeat** thread (`session.timeout.ms`), which proves the process is alive;
   - `max.poll.interval.ms`, which proves the poll *loop* is making progress.

   A consumer can be alive but stuck. The second check catches that.
2. The log line to look for is "consumer poll timeout has expired… the poll loop is spending too much time processing messages".
3. Fix the arithmetic: worst-case batch time = `max.poll.records` × worst per-record time. That must be comfortably below `max.poll.interval.ms`.
   We cut `max.poll.records` to 50 and put a 3 s timeout on the PDF call.
4. Stop the duplicate damage: an idempotency key per invoice, so a replay is a no-op.
5. If work is inherently long, decouple it: hand off to a job queue or retry topic, or pause the partition while the work runs, so the poll loop keeps going.

**Trade-offs and what can go wrong**
Smaller batches mean more poll round-trips and a little less throughput. That is a price worth paying for stability.

**How I'd monitor it**
Count of poll-timeout warnings, `time-between-poll-max` per consumer, and rebalance rate. Duplicate invoices are tracked by a unique-constraint violation counter.

**Follow-ups to expect**
- *Why didn't heartbeats keep it in the group?* → Heartbeats were fine. Since KIP-62 they run on a separate thread, and the poll-interval check is exactly what evicts a live-but-stuck consumer.

**60-second answer**
Kafka has two liveness checks: heartbeats for "the process is alive" and max.poll.interval for "the loop is making progress". If records-per-poll times worst-case processing time exceeds the poll interval,
the consumer is evicted mid-batch, its partitions move, and the uncommitted batch is replayed — often in a loop. I fix the arithmetic with smaller batches and timeouts on downstream calls,
add idempotency so replays are harmless, and decouple genuinely long work from the poll loop.

### Q9 [senior] Range, round-robin, sticky, cooperative-sticky, and the new KIP-848 protocol — which assignment strategy do you choose and why?
tags: rebalancing, assignors, cooperative-sticky, kip-848

**The live scenario**
A team consumed two co-partitioned topics (`orders` and `payments`, both keyed by orderId) and needed partition 3 of both on the same consumer, to join them in memory.
Another team just wanted the smoothest possible deploys.

**What the interviewer is really checking**
That you pick an assignor for a reason, and know which ones are eager vs incremental.

**How I answer it**
1. **Range:** assigns per topic, by contiguous ranges. It keeps the same partition numbers of co-partitioned topics together, which is the right choice for the join team.
   Its downside is uneven load across many topics.
2. **RoundRobin:** spreads evenly across all partitions, but it is eager and does not preserve previous assignments.
3. **Sticky:** spreads evenly and keeps assignments stable across rebalances, but it is still eager (stop-the-world).
4. **CooperativeSticky:** sticky *and* incremental — only moved partitions are revoked. This is my default for most services.
   Kafka 3.x clients list `[Range, CooperativeSticky]` by default precisely to allow the upgrade.
5. **KIP-848 (`group.protocol=consumer`, generally available in Kafka 4.0):** the broker computes assignments with server-side assignors.
   There is no group-wide sync barrier, and each member reconciles on its own. Where the cluster and clients support it, this is the strategic direction.

**Trade-offs and what can go wrong**
Moving from eager to cooperative needs a two-phase rolling deploy. Custom client-side assignors do not carry over directly to the broker-side protocol.

**How I'd monitor it**
Assignment skew (partitions per consumer) and rebalance duration before and after the change.

**60-second answer**
Range keeps the same partition numbers of co-partitioned topics together, so I use it for in-memory joins. RoundRobin and Sticky balance load but are eager. Cooperative-sticky
is sticky and incremental, so only moved partitions pause, and it is my default. On Kafka 4 I prefer the new broker-side KIP-848 protocol, which removes the group-wide barrier entirely.
Switching from eager to cooperative is a two-step rolling change.

### Q10 [senior] After a rebalance we processed some messages twice. How do you make a consumer idempotent?
tags: idempotency, duplicates, at-least-once, rebalancing, exactly-once

**The live scenario**
A loyalty-points service credited points on `OrderCompleted` events. After a rebalance, about 300 customers received double points.
The cause was the normal at-least-once replay of the uncommitted tail of a batch.

**What the interviewer is really checking**
That you accept duplicates as **normal** and design for them, instead of promising exactly-once you cannot deliver to an external database.

**How I answer it**
1. Duplicates come from rebalances, retries, producer retries without idempotence, and manual replays. You cannot eliminate them at the consumer, so you make processing idempotent.
2. Patterns, from simplest:
   - **Natural upsert:** "set status = SHIPPED for order 42" is naturally idempotent.
   - **Processed-event table:** insert the event id into a table with a unique key **in the same transaction** as the side effect. A duplicate fails the insert and is skipped.
     This is what we did for loyalty points.
   - **Version/conditional update:** only apply an event if its version is newer than the stored one, which also handles out-of-order events.
   - In NoSQL, use a document id equal to the event id with insert-if-absent, or a conditional write (CAS in Couchbase, `IF NOT EXISTS` in Cassandra).
3. Kafka's exactly-once (transactions plus `read_committed`) covers Kafka-to-Kafka processing. For an external database, idempotent writes *are* your exactly-once.

**Trade-offs and what can go wrong**
- The dedupe table grows, so purge it after the replay window, for example retention plus a margin.
- The event id must come from the producer, not be generated by the consumer.

**How I'd monitor it**
Count of "duplicate skipped" events. A sudden jump correlates with rebalances or a replay and is a useful signal in its own right.

**60-second answer**
At-least-once means duplicates are normal — from rebalances, retries and replays — so I make the side effect idempotent rather than trying to prevent redelivery. I use a natural upsert if possible.
Otherwise I store the event id with a unique key in the same transaction as the write, so a duplicate becomes a no-op, plus version checks for ordering. Kafka transactions give exactly-once only within Kafka;
for a database, the idempotent write is the exactly-once.

### Q11 [mid] What is consumer lag, and how do you monitor it?
tags: lag, monitoring, metrics, burrow, splunk

**The live scenario**
The business reported "order confirmation emails arrive 20 minutes late". No service was erroring. Lag on the email consumer group was 1.2 million messages and climbing.

**What the interviewer is really checking**
That you know the definition, that lag is the primary health metric for a consumer, and that you alert on its *trend*, not on a spike.

**How I answer it**
1. Lag per partition = log-end offset (latest written) − committed offset of the group. Total lag is the sum across partitions.
2. Lag in messages matters less than **lag in time**: "how stale is the data we act on?" 1M lag at 50k msg/s is 20 seconds; at 1k msg/s it is 17 minutes.
   I convert to time, or measure end-to-end latency from the record timestamp.
3. Where to get it:
   - the CLI, `kafka-consumer-groups --describe --group X`;
   - client metrics such as `records-lag-max`;
   - exported to Prometheus or Datadog via JMX or Burrow;
   - managed consoles (Confluent, MSK).
4. Alert on lag that **keeps growing for N minutes**, or on time-lag above the SLA, not on a momentary spike after a deploy.

**Trade-offs and what can go wrong**
Lag reported by the consumer itself disappears when the consumer is dead. That is why we also measure from outside, with Burrow or broker-side metrics.

**How I'd monitor it**
A dashboard per group with lag per partition (to spot a single stuck partition), consume rate vs produce rate, and the time-lag SLA line.

**60-second answer**
Lag is how far a group is behind the end of the log: log-end offset minus committed offset, per partition. I translate it into time, because that is what the business feels, and I watch it per partition
to catch a single stuck one. I alert on sustained growth or SLA breach rather than spikes, and I measure it from outside the consumer so a dead consumer still shows up.

### Q12 [senior] It's 2 a.m. and lag on a critical consumer group is growing fast. Walk me through what you do.
tags: lag, incident, troubleshooting, runbook, scaling

**The live scenario**
At 2:05 a.m. an alert fires: lag on `payment-settlement` has grown from 0 to 300k in 15 minutes. Settlement files are due to the bank at 6 a.m.

**What the interviewer is really checking**
A calm, ordered runbook: mitigate first, diagnose by elimination, and do not make it worse (for example by scaling into a rebalance storm).

**How I answer it**
1. **Scope it (2 minutes).** Is lag growing on all partitions or one?
   - All partitions → either a throughput problem (consumers are slower, or producers are faster) or a shared dependency problem.
   - One partition → a stuck or poison record, or a hot key (Q16, Q20).
2. **Producer side.** Did the produce rate jump (a batch job, a retry storm upstream)? If so, the consumers are fine and simply outnumbered.
3. **Consumer side.** Are consumers running and assigned? Look at rebalance count, restarts, and OOM kills. Is processing time per record up?
   Usually that is a **downstream** dependency — the database, a REST call, a lock. Check its latency and error rate in Splunk or APM.
4. **Mitigate.**
   - Downstream slow → fix or fail over the dependency. Scaling consumers just hammers it harder.
   - Consumers CPU-bound and partitions > consumers → scale out, but carefully: each new pod triggers a rebalance. Add them in one step, not one by one.
   - Poison record → let the error handler route it to the DLT, then resume.
5. **Protect the deadline.** Estimate catch-up time = lag ÷ (consume rate − produce rate). If it misses 6 a.m., escalate early, with numbers.
6. **Afterwards:** a blameless RCA, an alert threshold tuned to time-lag, and capacity headroom.

**Trade-offs and what can go wrong**
Restarting consumers "to see if it helps" triggers rebalances and adds a duplicate replay window. Do it deliberately, not reflexively.

**How I'd monitor it**
The same dashboard that alerted: per-partition lag, consume vs produce rate, and processing time. Then downstream latency, joined by correlation id in Splunk.

**60-second answer**
First I scope it: all partitions or one? All points to throughput or a shared dependency; one points to a poison record or hot key. Then I check whether producers spiked or consumers slowed —
usually a slow downstream such as the database. I mitigate accordingly: fix the dependency rather than scaling into it, scale out in one step if consumers are CPU-bound,
and DLT a poison record. I calculate the catch-up time against the business deadline and escalate early with numbers.

### Q13 [architect] Lag only appears under production load, never in performance testing. How do you find out why?
tags: lag, performance, production-only, capacity, troubleshooting

**The live scenario**
In the perf environment, the enrichment consumer handled 20k msg/s easily. In production it fell behind at 8k msg/s, every weekday from 9 to 11 a.m.

**What the interviewer is really checking**
That you know the usual reasons a test environment lies, and that you reason from data rather than tuning blindly.

**How I answer it**
1. List what is **different** in production:
   - **Key distribution:** the test used random keys, but production has a few huge merchants. Hot keys mean hot partitions, so one consumer is saturated while the others idle.
   - **Downstream contention:** the shared production database is busy with other workloads at 9 a.m., so per-record latency triples.
   - **Data shape:** real payloads are bigger, and deserialisation or compression cost scales with them.
   - **Co-tenancy:** noisy neighbours on the nodes, CPU throttling from Kubernetes limits, GC pauses on bigger heaps.
   - **Rebalances:** autoscaling in production adds and removes pods, and each change rebalances.
2. Prove it with production data: per-partition lag (skew → keys), processing-time histograms (downstream), CPU throttling metrics, GC logs, rebalance counts — all aligned on the 9–11 a.m. window.
3. Fix the actual cause:
   - salting or re-keying for hot keys (if ordering allows);
   - caching, batching writes, or a dedicated read replica for downstream contention;
   - raising CPU limits;
   - static membership to stop autoscaling from causing rebalances.
4. Close the loop: replay a **sample of production traffic** (keys and payloads) in perf, so the test stops lying.

**Trade-offs and what can go wrong**
Re-keying changes ordering guarantees, so check with the domain owner before salting a key.

**How I'd monitor it**
Per-partition lag and per-key throughput (top-N keys in Splunk), plus downstream p99 latency on the same time axis.

**60-second answer**
When lag only appears in production, I list what production has that perf did not: skewed real keys creating hot partitions, a contended shared database at peak, bigger payloads, CPU throttling or GC,
and autoscaling rebalances. I prove which one with per-partition lag, processing-time histograms and throttling metrics, all aligned on the bad window, then fix that cause specifically.
Finally I make perf replay real production key and payload distributions.

### Q14 [senior] A sale will bring 10x traffic. How do you scale your Kafka consumers?
tags: scaling, partitions, capacity, autoscaling, performance

**The live scenario**
Black Friday: order events go from 2k/s to 20k/s for 6 hours. The `order-processor` group runs 6 pods on a 12-partition topic, and each pod handles about 600 msg/s.

**What the interviewer is really checking**
Capacity arithmetic, the partition ceiling, and knowing the bottleneck is usually not Kafka itself.

**How I answer it**
1. **Do the maths.** 20k/s ÷ 600 msg/s per consumer ≈ 34 consumers. But only 12 partitions means at most 12 active consumers, so 12 × 600 = 7.2k/s. We cannot get there by adding pods alone.
2. **Options, in order:**
   - **Make each consumer faster:** batch the database writes (one multi-row insert per poll instead of 500 single inserts), async I/O, caching lookups. This often gives 3–5x.
   - **Add partitions ahead of time**, for example to 48, in a quiet window weeks before. Accept the key-remapping effect, or create a new topic and migrate.
   - **Parallelism inside a consumer by key** (Q15), when partitions are fixed.
3. **Check the downstream.** 20k writes/s must be absorbable by the database. Otherwise faster consumers just move the fire. Load-test the whole path.
4. **Autoscale on lag**, not on CPU (for example KEDA's Kafka scaler), with a cap of max = partition count, and pre-scale before the event to avoid rebalance churn at the peak.
5. **Let lag absorb the peak** if the business allows it. Kafka is a buffer, and a 10-minute lag that drains after the peak may be cheaper than provisioning for the peak.

**Trade-offs and what can go wrong**
More partitions mean longer rebalances and more broker overhead. Autoscaling causes rebalances at exactly the busiest moment, so I prefer to pre-scale for known events.

**How I'd monitor it**
Consume vs produce rate, time-lag against the SLA, downstream database latency, and the rebalance count during the event.

**60-second answer**
I start with arithmetic: target rate divided by per-consumer rate, compared with the partition count, which caps active consumers. Then I make each consumer faster with batched writes and async I/O,
add partitions well ahead of the event, or parallelise by key inside the consumer. I verify the downstream can take the load, autoscale on lag capped at the partition count
(or simply pre-scale for a known event), and agree with the business how much lag is acceptable to absorb the peak.

### Q15 [senior] We need more throughput, but events for the same customer must stay in order. How do you parallelise inside a consumer?
tags: ordering, parallelism, keys, throughput, parallel-consumer

**The live scenario**
An account-ledger consumer must apply events per account in order, but each event costs 50 ms of I/O. With 12 partitions, we were stuck at about 240 events/s.

**What the interviewer is really checking**
That you know ordering is per key, not per partition, and that you can exploit that without breaking correctness.

**How I answer it**
1. Kafka orders per partition. The business only needs order **per key** (per account), and one partition holds thousands of keys.
2. Inside each consumer, dispatch records to N worker lanes by `hash(key) % N`. The same key always goes to the same lane, in order; different keys run in parallel.
3. Commit carefully: only commit up to the **lowest offset not yet completed** across the lanes, so a crash never skips unfinished work.
4. Rather than hand-roll this, use a library that does key-ordered parallel processing with offset tracking, such as the Confluent Parallel Consumer.
5. Back-pressure: bound each lane's queue, and pause the partition when queues are full.

**Trade-offs and what can go wrong**
- Hand-rolled offset tracking is where bugs live: commit ahead of the work and you lose data.
- The rebalance handling becomes harder, because you must drain the lanes on revoke.

**How I'd monitor it**
Per-lane queue depth, the oldest in-flight offset age, and end-to-end time-lag.

**60-second answer**
Kafka guarantees order per partition, but the business only needs order per key, so inside a consumer I fan out to worker lanes by key hash — the same key stays on one lane in order,
and different keys run in parallel. The hard part is committing only up to the lowest unfinished offset and draining the lanes on rebalance, so I prefer a proven library like the Confluent Parallel Consumer.
That took us from 240 to about 4,000 events/s without adding partitions.

### Q16 [senior] One bad message is blocking a whole partition. How do you handle poison messages?
tags: poison-message, dlt, retries, error-handling, spring-kafka

**The live scenario**
A producer released a version that wrote `amount: "N/A"`. The consumer threw a deserialisation exception, and the default error handling kept retrying the same record forever.
Partition 7 stopped, its lag grew, and every order behind that record waited.

**What the interviewer is really checking**
Error classification, bounded retries, a Dead Letter Topic, and keeping ordering in mind.

**How I answer it**
1. **Classify the failure.**
   - Non-retryable (bad schema, validation, deserialisation) → retrying will never help, so send it to the **DLT immediately**.
   - Retryable (database timeout, 503 from a dependency) → retry with backoff, a bounded number of times.
2. **Spring Kafka.** Use `DefaultErrorHandler` with an exponential backoff and a `DeadLetterPublishingRecoverer`, mark exceptions like `DeserializationException` as not retryable,
   and wrap the deserializer in an `ErrorHandlingDeserializer` so bad bytes reach the error handler instead of crash-looping the poll.
3. **Non-blocking retries.** `@RetryableTopic` moves failing records to retry topics with delays, so the main partition keeps flowing.
   The trade-off is that ordering for that key is lost.
4. **The DLT is a process, not a bin.** Store the original topic, partition, offset, exception and headers. Alert on DLT growth. Have an owner and a re-drive tool once the bug is fixed.

**Trade-offs and what can go wrong**
For strictly ordered domains (a ledger), skipping a record can be worse than stopping. There we park the *key* (later events for the same account also go to a parking topic) or halt and page someone.

**How I'd monitor it**
DLT message rate (should be near zero), retry counts, and per-partition lag. A single partition with flat consumption is the poison-pill signature.

**60-second answer**
I classify failures. Non-retryable ones like bad schema go straight to a Dead Letter Topic with full context; retryable ones get bounded exponential backoff. In Spring Kafka that is DefaultErrorHandler plus DeadLetterPublishingRecoverer and
an ErrorHandlingDeserializer, or @RetryableTopic for non-blocking retries, at the cost of per-key ordering. The DLT has an owner, an alert and a re-drive tool. For strictly ordered data I park the whole key rather than skip one event.

### Q17 [senior] The downstream database is down for 20 minutes. What should your Kafka consumer do?
tags: back-pressure, pause-resume, retries, outage, circuit-breaker

**The live scenario**
The Cassandra cluster behind the `profile-updater` consumer was unavailable for 20 minutes during maintenance. The consumer retried every record a few times, sent thousands of valid events to the DLT,
and then needed a painful manual re-drive.

**What the interviewer is really checking**
The difference between a **bad message** and a **bad dependency**, and using Kafka itself as the buffer.

**How I answer it**
1. When the dependency is down, every message fails, and that tells you it is not the messages' fault. They must **not** go to the DLT.
2. Stop consuming instead:
   - a circuit breaker around the database call opens after a failure threshold;
   - the consumer **pauses** its partitions (`consumer.pause()`, or pausing the listener container in Spring Kafka);
   - it keeps calling `poll()` (which returns nothing while paused), so it stays in the group;
   - it probes the dependency, and **resumes** when the breaker half-opens successfully.
3. Kafka holds the backlog durably; lag grows, and then drains after recovery. That is exactly the buffer we want.
4. Make sure retention comfortably exceeds the longest outage you plan for.

**Trade-offs and what can go wrong**
- Blocking retries with `sleep` inside the listener breach `max.poll.interval.ms` and add rebalances to the outage.
- After resume, catch-up traffic can overload the recovering database, so rate-limit the catch-up.

**How I'd monitor it**
Breaker state, paused-partition count, lag growth and the drain rate after recovery, plus an alert if paused for longer than X minutes.

**60-second answer**
If every message is failing, the problem is the dependency, not the messages, so dead-lettering them is wrong. I open a circuit breaker, pause the partitions while still polling so the consumer stays in the group,
probe the dependency, and resume when it recovers — Kafka is the durable buffer and lag just drains afterwards. I make sure retention exceeds the longest outage and throttle the catch-up so we do not knock the database over again.

### Q18 [architect] A bug processed two hours of events wrongly. How do you replay or reset offsets safely?
tags: replay, reset-offsets, recovery, incident, idempotency

**The live scenario**
A pricing consumer applied the wrong currency conversion between 10:00 and 12:00. The fix was deployed at 12:30. Business asked: "Can we just re-run those two hours?"

**What the interviewer is really checking**
That you know replay is possible because Kafka retains data, and that you plan for side effects, idempotency and coordination.

**How I answer it**
1. **Confirm the data is still there:** is retention longer than the window? It almost always is for hours; check it for days.
2. **Decide how to replay:**
   - **Same group, rewind:** stop all members (offsets can only be reset on an inactive group), then run `kafka-consumer-groups --reset-offsets --to-datetime 2025-…T10:00 --execute`, and restart with the fix.
     This also re-processes 12:00–12:30, so the handlers must be idempotent.
   - **A separate replay group or job:** a one-off consumer with its own group id that `seek`s to the 10:00 offsets (`offsetsForTimes`) and stops at the 12:00 offsets.
     Live traffic is not disturbed. This is my preferred option.
3. **Side effects:** a replay re-triggers *everything* the handler does. Disable non-idempotent effects — emails, payments, downstream events — or route them through dedupe.
   This is the most important question to ask before any replay.
4. **Correctness:** write corrected values as upserts, and publish corrections as new events, so downstream systems also get the fix.
5. **Communicate:** agree the window, the dry-run counts and the sign-off with the data owner.

**Trade-offs and what can go wrong**
Resetting a live group while members are running silently fails or gets overwritten. Replays also add load, so throttle them.

**How I'd monitor it**
The replay job's processed count against the expected record count for the window (from offsets), plus a reconciliation query afterwards.

**60-second answer**
Kafka retains the events, so replay is possible. I prefer a separate one-off replay consumer that seeks to the start time and stops at the end offset, so live traffic is not touched.
Alternatively I stop the group and reset offsets to a datetime. The key questions are side effects — emails and payments must not fire again — and idempotent upserts for corrections,
with a dry-run count and owner sign-off before the run.

### Q19 [architect] A consumer group has stopped processing entirely, but there are no errors anywhere. What is your runbook?
tags: stuck-consumer, runbook, troubleshooting, deadlock, incident

**The live scenario**
Lag on `shipment-events` was rising linearly. All pods were Running, health checks were green, and the logs were silent.

**What the interviewer is really checking**
Systematic thinking about *silent* failures — the kind that liveness probes do not catch.

**How I answer it**
1. **Does the group exist, and is it stable?** Run `kafka-consumer-groups --describe`.
   - No active members → the consumers are not connected (auth, network, wrong bootstrap after a cert rotation).
   - "Rebalancing" forever → a rebalance storm.
2. **Are partitions assigned and are offsets moving?** Assigned but frozen means the consumer thread is stuck.
3. **Thread dump** (`jstack` or the Actuator `threaddump` endpoint) of a pod. The usual culprits:
   - a blocking call without a timeout (an HTTP client with an infinite read timeout, a database connection-pool wait);
   - a deadlock;
   - a paused container that never resumed.
4. **Is it consuming but silently dropping?** For example, a filter or a deserialiser swallowing errors, or a `@KafkaListener` on the wrong topic after a rename.
   Compare the consumed rate with the processed rate.
5. **Mitigate:** restart one pod to confirm the hypothesis (expect a rebalance and a replay window), then fix the root cause — timeouts everywhere, resume logic, alerts.
6. **Prevent:** a liveness signal based on **progress** (time since the last committed offset) instead of "the JVM answers HTTP".

**Trade-offs and what can go wrong**
Restarting everything first destroys the evidence. Take a thread dump before you restart.

**How I'd monitor it**
Alerts on "offset not advancing for N minutes while lag > 0", plus timeouts metered on every outbound call.

**60-second answer**
I check the group state first: no members means a connectivity or auth problem, and endless rebalancing means a storm. If partitions are assigned but offsets are frozen, I take a thread dump before restarting —
it is usually a call without a timeout, a connection-pool wait or a never-resumed pause. I also check for silent drops by comparing consumed vs processed counts.
Then I add timeouts everywhere and a liveness signal based on offset progress, not just "the JVM is up".

### Q20 [architect] One consumer pod is at 100% CPU while the others are idle. What's going on, and how do you fix it?
tags: hot-partition, keys, skew, scaling, partitioning

**The live scenario**
Marketplace orders keyed by `sellerId`. One mega-seller generated 40% of all events, so the consumer that owned that seller's partition was pegged at 100%, and its lag grew,
while 11 other pods sat at 10% CPU.

**What the interviewer is really checking**
That you recognise **key skew**, and know the remedies and their ordering trade-offs.

**How I answer it**
1. **Confirm the skew:** per-partition produce rate and lag, and the top-N keys by volume (from Splunk or a sampling consumer).
2. **Remedies, by impact on ordering:**
   - **A better key:** does the business need ordering per *seller*, or per *order*? Keying by `orderId` spreads the load and keeps the ordering that actually matters.
     This was the fix in our case.
   - **Compound or salted key** for the hot key only (`sellerId#n` across n sub-keys): this spreads load, but you lose cross-sub-key ordering, so downstream must tolerate that or re-merge.
   - **Parallelise inside the consumer** by a finer key (Q15).
   - **A separate topic** for the whale tenant, with its own consumers.
   - **Producer back-pressure or rate limits** for the noisy tenant, when fairness matters.
3. Adding partitions **does not help**: the same key still hashes to one partition.

**Trade-offs and what can go wrong**
Changing the key changes ordering semantics, and changes the partition for all in-flight data — coordinate the cut-over.

**How I'd monitor it**
Partition skew ratio (max vs average produce rate) and top keys by volume, with an alert when one partition carries more than X% of traffic.

**60-second answer**
One busy consumer with idle peers is key skew: a hot key maps to one partition, and adding partitions will not help. I confirm it with per-partition rates and top keys, then pick a remedy based on ordering needs:
re-key to the real ordering unit (often orderId, not sellerId), salt only the hot key, parallelise by a finer key inside the consumer, or isolate the whale tenant on its own topic.
