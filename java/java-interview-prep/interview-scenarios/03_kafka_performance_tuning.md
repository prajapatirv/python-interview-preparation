---
id: kafka-performance
title: Tuning Kafka configuration for large-scale traffic
stack: java
skill: kafka
---
Interview feedback focus: **tuning Kafka configuration for handling large scale of traffic.** Each answer names
the real settings, says what they trade, and shows how you would prove the result. Defaults are for Apache
Kafka 3.x/4.x clients unless stated; Kafka 4.0 changed some (noted where it matters).

Levels: **fresher** (0–2 yrs) · **mid** (3–6) · **senior** (6–10) · **architect** (10+).

### Q1 [mid] How do you tune a Kafka producer for high throughput?
tags: producer, batch.size, linger.ms, compression, throughput, tuning

**The live scenario**
A clickstream producer sent 40k small events/s (about 500 bytes each). Producer CPU was high, broker request rate was enormous, and throughput plateaued well below target.

**What the interviewer is really checking**
That you know batching is the main throughput lever and can explain each setting's trade-off.

**How I answer it**
1. **Batching is everything.** The producer groups records per partition into batches; bigger batches mean fewer requests, better compression and less broker CPU.
   - `batch.size` (default 16 KB): raise to 64–256 KB for high volume.
   - `linger.ms`: how long to wait for a batch to fill. Default 0 before Kafka 4.0 and 5 ms from 4.0; 5–20 ms is typical for throughput.
2. **Compression:** `compression.type=lz4` (fast) or `zstd` (best ratio). Compression works on whole batches, so it multiplies with batching. JSON often compresses 4–8x, cutting network and disk too.
3. **Memory and in-flight requests:**
   - `buffer.memory` (default 32 MB) must hold the batches waiting to be sent; if it fills, `send()` blocks up to `max.block.ms`;
   - `max.in.flight.requests.per.connection` up to 5 keeps ordering with idempotence on.
4. **Keyless records** use the sticky partitioner (fills one partition's batch, then moves on), which already maximises batch size.
5. **Prove it:** `kafka-producer-perf-test` and producer metrics. In our case `batch.size=128KB`, `linger.ms=10`, `lz4` went from 18 MB/s to 70 MB/s with 60% less broker CPU, adding about 10 ms of latency.

**Trade-offs and what can go wrong**
Higher `linger.ms` adds latency; larger batches use more buffer memory; `zstd` costs more CPU than `lz4`.

**How I'd monitor it**
Producer `batch-size-avg`, `records-per-request-avg`, `compression-rate-avg`, `record-send-rate`, `request-latency-avg`, `buffer-available-bytes`, and broker request rate.

**Follow-ups to expect**
- *Will this lose ordering?* -> No: with idempotence on and in-flight requests ≤ 5, ordering per partition is preserved.
- *Why did broker CPU drop?* -> Fewer, larger, compressed requests mean less request handling per byte.

**60-second answer**
Producer throughput is mostly batching: I raise batch.size to 64–256 KB, set linger.ms to 5–20 ms so batches fill, and turn on lz4 or zstd compression, which works per batch and multiplies the effect. I make sure buffer.memory holds the in-flight batches and keep idempotence with up to 5 in-flight requests so ordering holds. On one clickstream producer that took us from 18 to 70 MB/s and cut broker CPU by 60%, for about 10 ms of added latency.

**Minimal config**
```properties
batch.size=131072
linger.ms=10
compression.type=lz4
```

### Q2 [mid] How do acks, idempotence and min.insync.replicas trade durability against latency?
tags: acks, idempotence, min.insync.replicas, durability, latency

**The live scenario**
A team set `acks=1` "for performance" on a payments topic. A broker crashed right after acknowledging; the follower hadn't copied the data yet, and 1,200 payment events were lost.

**What the interviewer is really checking**
That you never tune durability away without a business decision, and know what the settings actually cost.

**How I answer it**
1. **acks:**
   - `acks=0`: fire and forget — fastest, can lose anything;
   - `acks=1`: the leader wrote it — loses data if the leader dies before followers copy;
   - `acks=all`: all in-sync replicas have it — the default since Kafka 3.0, together with `enable.idempotence=true`.
2. **min.insync.replicas** (topic/broker): with replication factor 3 and `min.insync.replicas=2`, a write needs 2 copies. One broker can fail without loss or unavailability.
3. **Idempotence:** the broker deduplicates producer retries by sequence number, so retries can't create duplicates or reorder — essentially free, keep it on.
4. **The latency cost of acks=all** is roughly one extra replication round-trip within the cluster — often a few milliseconds. Get throughput from batching and compression instead of weakening acks.
5. **Use acks=1 only for data the business agrees can be lost** (debug telemetry), on separate topics.

**Trade-offs and what can go wrong**
`min.insync.replicas=3` with RF=3 makes the topic unwritable when any broker is down. `unclean.leader.election.enable=true` trades loss for availability — keep it off for important data.

**How I'd monitor it**
Under-replicated partitions, ISR shrink/expand rates, producer error rate (`NotEnoughReplicas`), and produce latency p99.

**60-second answer**
acks=all with idempotence is the default since Kafka 3.0 and should stay for anything important; with replication factor 3 and min.insync.replicas 2 we survive a broker loss without losing data. acks=1 can lose data when a leader dies — I've seen 1,200 payments lost that way. The cost of acks=all is a few milliseconds, so I get throughput from batching and compression, and keep weaker acks for separate topics whose loss the business accepts.

### Q3 [senior] How do you tune Kafka consumers for high throughput?
tags: consumer, fetch.min.bytes, max.poll.records, batch-listener, concurrency, spring-kafka

**The live scenario**
An audit consumer writing to a database processed 3k msg/s while producers sent 12k msg/s. Lag grew all day and drained only overnight.

**What the interviewer is really checking**
That consumer throughput is usually limited by **processing**, and which settings and patterns move it.

**How I answer it**
1. **Find the limit:** is it fetching (network, broker) or processing (our code, the database)? Almost always processing. Measure time per record versus time per poll.
2. **Process in batches:** a batch listener in Spring Kafka (`batchListener=true`) receiving `max.poll.records` records (default 500), with **one multi-row insert or upsert per batch** instead of 500 single inserts. This alone gave us 3x.
3. **Fetch efficiently:**
   - `fetch.min.bytes` (e.g. 64 KB–1 MB) with `fetch.max.wait.ms` (default 500 ms) for fewer, fuller fetches;
   - `max.partition.fetch.bytes` (default 1 MB) larger if messages are large.
4. **Parallelism:**
   - more consumers up to the partition count (Spring Kafka `concurrency` = threads per instance);
   - or key-ordered parallel processing inside a consumer (Confluent Parallel Consumer).
5. **Keep it safe:** batch size × per-record time must stay well under `max.poll.interval.ms`; commit after the batch succeeds; idempotent writes.
6. Result: 3k → 15k msg/s with batch upserts, `concurrency=4` on 3 pods (12 partitions), and `fetch.min.bytes=256KB`.

**Trade-offs and what can go wrong**
Bigger batches mean bigger replays after a failure or rebalance, and one poison record can fail a whole batch — handle per-record errors inside batches.

**How I'd monitor it**
Consumer lag, `records-consumed-rate`, `fetch-latency-avg`, `records-per-request-avg`, and processing time per batch.

**60-second answer**
Consumer throughput is almost always limited by processing, so the big lever is batching the work — a batch listener with one multi-row upsert per poll instead of hundreds of single inserts. Then I fetch efficiently with fetch.min.bytes and fetch.max.wait.ms, and add parallelism up to the partition count with listener concurrency. I keep batch time under max.poll.interval and writes idempotent. That took one consumer from 3k to 15k msg/s.

**Minimal config**
```properties
max.poll.records=500
fetch.min.bytes=262144
fetch.max.wait.ms=200
spring.kafka.listener.type=batch
spring.kafka.listener.concurrency=4
```

### Q4 [senior] How many partitions does a high-traffic topic need?
tags: partitions, capacity, scaling, partition-count, throughput

**The live scenario**
A new events topic must handle 200 MB/s at peak, with consumers that each process about 10 MB/s. The team proposed 1,000 partitions "to be safe".

**What the interviewer is really checking**
Partition sizing from both producer and consumer sides, and the cost of too many partitions.

**How I answer it**
1. **Consumer side usually decides:** partitions ≥ target throughput ÷ per-consumer throughput = 200 ÷ 10 = 20 active consumers needed, so at least 20 partitions.
2. **Producer and broker side:** a single partition handles roughly tens of MB/s, depending on hardware and settings — measure it with the perf tools; rarely the binding limit.
3. **Add growth headroom:** you can add partitions later, but that remaps keys (breaking per-key ordering during the change), and you can't reduce them. We chose 48 (2.4x headroom; divisible by common consumer counts like 6, 12, 24).
4. **Why not 1,000:**
   - more open files and memory per broker;
   - longer leader elections and recovery after a broker failure;
   - slower rebalances;
   - smaller batches per partition (worse compression and throughput);
   - more end-to-end latency from replication of many small partitions.

   KRaft supports far more partitions per cluster than ZooKeeper did, but the per-partition costs remain.
5. **Check key distribution:** partitions don't help a hot key (see the consumer bank, Q20).

**Trade-offs and what can go wrong**
Too few partitions caps consumer parallelism permanently; too many costs latency and stability.

**How I'd monitor it**
Per-partition bytes in (skew), consumer lag per partition, and broker partition counts and leader balance.

**60-second answer**
I size partitions from the consumer side first — peak throughput divided by what one consumer can process, 200 over 10 means at least 20 — check per-partition broker throughput with the perf tools, then add headroom because adding partitions later remaps keys and you can't remove them; we chose 48. A thousand partitions would cost broker memory, recovery time, rebalance time and batching efficiency. And partitions never fix a hot key.

### Q5 [senior] How do you handle large messages in Kafka?
tags: large-messages, message.max.bytes, claim-check, compression, s3

**The live scenario**
A document service started publishing events with embedded PDFs of up to 8 MB. Producers got `RecordTooLargeException`; someone raised every size limit, and broker memory and replication lag spiked.

**What the interviewer is really checking**
Knowing the size limits and why the claim-check pattern is usually the right answer.

**How I answer it**
1. **Limits that must agree:**
   - producer `max.request.size` (default 1 MB);
   - broker `message.max.bytes` or topic `max.message.bytes` (about 1 MB by default);
   - replica `replica.fetch.max.bytes`;
   - consumer `max.partition.fetch.bytes` and `fetch.max.bytes`.

   Raise one without the others and something fails later.
2. **Why big messages hurt:** they occupy broker memory and network in big chunks, slow replication and fetches for everyone on that broker, and reduce batching efficiency.
3. **Better: the claim-check pattern.** Store the payload in object storage (S3, Blob) and send a small event with the reference, size and checksum. Kafka stays fast; consumers fetch the blob only if needed.
4. **For moderately large payloads (1–5 MB):** compression first (`zstd`), and raise the limits consistently on a dedicated topic.
5. We moved PDFs to S3 with pointer events of about 1 KB; replication lag returned to normal and consumer throughput rose 10x.

**Trade-offs and what can go wrong**
Claim-check adds a second system: lifecycle rules so blobs aren't deleted before consumers read them, and access control on the store.

**How I'd monitor it**
Record size percentiles (`record-size-avg` / `-max`), replication lag, broker network throughput, and `RecordTooLargeException` counts.

**60-second answer**
Kafka's limits default to about 1 MB across producer, broker, replication and consumer settings, and they must be raised together or something fails downstream. But large messages slow replication and fetches for everyone, so my default is the claim-check pattern: payload in S3, a small event with the reference and checksum in Kafka. For payloads of a few MB I compress with zstd on a dedicated topic with consistent limits. Moving PDFs to S3 gave us a 10x consumer throughput gain.

### Q6 [senior] Which broker-side settings matter for high traffic?
tags: broker, num.io.threads, num.network.threads, page-cache, replication, rack-awareness

**The live scenario**
At peak, produce latency p99 on a 6-broker cluster rose from 15 ms to 400 ms. Broker CPU was moderate, but request queues were growing.

**What the interviewer is really checking**
How a broker spends its resources, and which metrics point to which setting.

**How I answer it**
1. **Read the request path metrics first:** `RequestQueueTimeMs`, `LocalTimeMs`, `RemoteTimeMs` (waiting for followers with acks=all) and `ResponseQueueTimeMs` show where requests wait.
2. **Thread pools:**
   - `num.network.threads` (default 3) handle sockets — raise when `NetworkProcessorAvgIdlePercent` is low;
   - `num.io.threads` (default 8) handle requests and disk — raise when `RequestHandlerAvgIdlePercent` is low (our case: below 20%).
3. **Replication:** `num.replica.fetchers` to speed follower catch-up; a large `RemoteTimeMs` means followers are slow (disk, network, or too many partitions per broker).
4. **Memory:** Kafka relies on the **OS page cache**. Keep the JVM heap modest (around 6 GB is common) and leave the rest of RAM to the page cache, so consumers read recent data from memory.
5. **Disks and layout:** fast disks or multiple log dirs, enough network bandwidth for replication traffic (bytes in × replication factor), `broker.rack` for rack-aware replica placement across zones.
6. **Balance:** spread partition leaders evenly (`auto.leader.rebalance.enable` or tools like Cruise Control).
7. We raised `num.io.threads` and `num.network.threads`, rebalanced leaders, and p99 went back to 20 ms.

**Trade-offs and what can go wrong**
More threads than cores just adds contention; a huge broker heap starves the page cache.

**How I'd monitor it**
Request queue times, handler and network idle percentages, under-replicated partitions, `BytesInPerSec`/`BytesOutPerSec` per broker, disk and page-cache hit behaviour.

**60-second answer**
I start from the request-path metrics to see where produce requests wait: request queue, local disk time, waiting for followers or the response queue. Then I tune the matching resource — num.network.threads and num.io.threads when their idle percentages drop, replica fetchers when followers lag. I keep the heap modest so the OS page cache serves reads, size network for replication traffic, use rack awareness, and balance leaders. That took a cluster's produce p99 from 400 ms back to 20.

### Q7 [senior] You need low end-to-end latency rather than maximum throughput. What changes?
tags: latency, linger.ms, fetch.min.bytes, end-to-end-latency, tuning

**The live scenario**
A fraud-scoring pipeline needed card events scored within 50 ms end to end. It used settings copied from a bulk analytics pipeline (`linger.ms=50`, `fetch.min.bytes=1MB`), and p99 was 600 ms.

**What the interviewer is really checking**
That you understand throughput settings *add* latency, and can tune in the opposite direction.

**How I answer it**
1. **Map the latency path:** producer wait (linger) → send → leader write → replication (acks=all) → consumer fetch wait → processing.
2. **Producer:** `linger.ms` at 0–5 ms; a moderate `batch.size`; `lz4` (or no compression) for small messages.
3. **Consumer:** `fetch.min.bytes=1` (return as soon as any data exists) and a low `fetch.max.wait.ms`; keep processing per record fast; avoid big batches.
4. **Durability stays:** keep acks=all; it costs only a few milliseconds within a zone.
5. **Cluster health matters more than flags:** no under-replicated partitions, no GC pauses on brokers or consumers, consumers in the same region as brokers.
6. **Separate pipelines** when one topic serves both latency- and throughput-sensitive use cases — they want opposite settings.
7. Result: p99 from 600 ms to 35 ms.

**Trade-offs and what can go wrong**
More, smaller requests raise broker CPU and reduce throughput per broker; budget capacity for it.

**How I'd monitor it**
End-to-end latency from record timestamp to processing time (p99), plus produce and fetch latency.

**60-second answer**
Throughput settings add latency, so for a latency-critical pipeline I tune the other way: linger.ms near zero, moderate batches, light compression, fetch.min.bytes of 1 and a short fetch wait, with fast per-record processing — but I keep acks=all, which costs only a few milliseconds. Healthy replicas, no GC pauses and co-located consumers matter as much as flags, and I separate pipelines with opposite needs. One fraud pipeline went from 600 to 35 ms p99.

### Q8 [architect] Traffic must grow from 10,000 to 1 million messages per second. How do you plan the Kafka side?
tags: capacity-planning, scaling, brokers, partitions, throughput, architecture

**The live scenario**
An IoT platform onboarding a large customer expected events to grow 100x within a year: about 1M msg/s at 1 KB each — roughly 1 GB/s in.

**What the interviewer is really checking**
Capacity arithmetic across network, disk and partitions, and the scaling levers in the right order.

**How I answer it**
1. **Do the arithmetic:**
   - ingress 1 GB/s; with replication factor 3, the cluster writes 3 GB/s to disk and moves 2 GB/s between brokers;
   - egress = ingress × number of consumer groups (3 groups → 3 GB/s out);
   - retention 3 days ≈ 1 GB/s × 259,200 s × 3 replicas ≈ 780 TB, before compression (zstd might bring that to roughly 200–250 TB).
2. **Size brokers from the binding resource,** usually network or disk: if one broker sustains about 250 MB/s of combined in/out traffic safely at 60% utilisation, the cluster needs on the order of 30+ brokers. Validate per-broker numbers with a perf test on our hardware.
3. **Partitions** from consumer parallelism (Q4), spread evenly across brokers.
4. **Reduce bytes first:** compact serialisation (Avro/Protobuf instead of JSON), compression, dropping unused fields — a 3x byte reduction is a 3x cheaper cluster.
5. **Producers:** batching and compression (Q1), many producer instances.
6. **Isolation:** separate clusters or quotas for this customer, so one tenant can't hurt others (Q11).
7. **Tiered storage** (Kafka 3.6+, production-ready in later releases) keeps long retention cheap in object storage.
8. **Prove it in stages:** 10x, then 30x, then 100x, with perf tests and production canaries.

**Trade-offs and what can go wrong**
A managed service (MSK, Confluent Cloud) shifts operations but has its own throughput units and costs; a self-managed cluster needs strong ops automation.

**How I'd monitor it**
Per-broker bytes in/out against planned capacity, disk usage growth, replication lag, and partition skew.

**60-second answer**
I start with arithmetic: 1 million 1 KB messages is about 1 GB/s in, which becomes 3 GB/s on disk with replication factor 3 and more out per consumer group, plus hundreds of terabytes for retention. From the binding resource — usually network or disk per broker — I size the broker count, then partitions from consumer parallelism. I reduce bytes first with Avro and zstd, isolate the big tenant with quotas or its own cluster, use tiered storage for retention, and scale in proven stages.

### Q9 [senior] Under heavy traffic some partitions are overloaded while others are idle. How do you fix the distribution?
tags: partitioner, hot-partition, sticky-partitioner, key-distribution, skew

**The live scenario**
A metrics topic with 24 partitions showed 3 partitions receiving 60% of traffic, because producers keyed by `tenantId` and three tenants dominated.

**What the interviewer is really checking**
How the partitioner works and how to balance load without breaking required ordering.

**How I answer it**
1. **How records land on partitions:**
   - with a key: `murmur2(key) % partitions` — same key, same partition, always;
   - without a key: the **sticky partitioner** fills a batch for one partition before switching (Kafka 2.4+, improved uniform sticky behaviour in 3.3), which balances well and keeps batches large.
2. **Ask whether ordering per tenant is really required.** For metrics it wasn't: ordering per `tenantId + metricName` was enough. A finer key spread the load evenly.
3. **If ordering per tenant must stay:** split only the hot tenants (`tenantId#n`) and re-order downstream; or give whales their own topic.
4. **A custom `Partitioner`** for special rules (e.g. hot tenants spread across a reserved set of partitions) — keep it deterministic and documented.
5. **Don't just add partitions:** a hot key still maps to one partition.

**Trade-offs and what can go wrong**
Changing the key changes ordering semantics and remaps in-flight data; coordinate with consumers.

**How I'd monitor it**
Bytes in per partition (max vs average), lag per partition, and top keys by volume.

**60-second answer**
Keyed records go to the hash of the key modulo the partition count, so skewed keys mean hot partitions; keyless records use the sticky partitioner, which balances well. I first question whether ordering is really needed at that key's granularity — for us, tenant plus metric was enough and spread the load evenly. Otherwise I split only the hot keys, give whales their own topic, or use a custom partitioner. Adding partitions never fixes a hot key.

### Q10 [mid] Which metrics tell you whether Kafka is keeping up with traffic?
tags: monitoring, metrics, lag, under-replicated-partitions, jmx

**The live scenario**
A cluster "looked fine" — brokers up, no errors — while a critical consumer was 40 minutes behind and two brokers had under-replicated partitions.

**What the interviewer is really checking**
The short list of metrics that actually matter at each layer.

**How I answer it**
1. **Consumers:**
   - **lag** per group and partition, in messages and in time — the single most important metric;
   - `records-consumed-rate`, processing time, rebalance rate.
2. **Producers:**
   - `record-send-rate`, `record-error-rate`, `request-latency-avg`;
   - `batch-size-avg`, `compression-rate-avg`;
   - `buffer-available-bytes` (near zero means the producer is blocking).
3. **Brokers:**
   - `UnderReplicatedPartitions` (must be 0) and `OfflinePartitionsCount`;
   - ISR shrink/expand rate;
   - `BytesInPerSec`/`BytesOutPerSec` against capacity;
   - request queue time and handler idle percentage;
   - disk usage and growth;
   - controller health (KRaft quorum).
4. **Collect** via JMX → Prometheus/Grafana or Datadog, Burrow or a Kafka UI for lag, and alert on: lag growing for N minutes, any under-replicated partitions, offline partitions, disk above 75%.

**Trade-offs and what can go wrong**
Thousands of per-partition metrics overwhelm dashboards; aggregate for alerting, drill down per partition when investigating.

**How I'd monitor it**
That list *is* the monitoring — one dashboard per layer and four or five alerts that page.

**60-second answer**
For consumers I watch lag per partition, in messages and in time — the most important Kafka metric — plus consume rate and rebalances. For producers, send and error rates, request latency, batch size and buffer availability. For brokers, under-replicated and offline partitions must be zero, plus ISR churn, bytes in and out against capacity, request queue time, handler idle and disk. I alert on growing lag, any under-replicated partitions and disk, and drill into per-partition detail only when investigating.

### Q11 [senior] How do you load-test Kafka and prove a configuration change?
tags: perf-test, kafka-producer-perf-test, benchmarking, load-testing

**The live scenario**
The team wanted to switch from `snappy` to `zstd` and raise `batch.size` before a peak season, and needed evidence, not opinions.

**What the interviewer is really checking**
A disciplined benchmark: one change at a time, realistic data, both sides measured.

**How I answer it**
1. **Built-in tools:**
   - `kafka-producer-perf-test.sh --topic t --num-records 5000000 --record-size 1000 --throughput -1 --producer-props acks=all batch.size=131072 linger.ms=10 compression.type=zstd`, which reports records/s, MB/s and latency percentiles;
   - `kafka-consumer-perf-test.sh` for the consuming side;
   - for bigger studies, the OpenMessaging Benchmark.
2. **Realistic payloads:** use real (anonymised) message samples — random bytes don't compress, so they make compression look useless.
3. **One variable at a time,** several runs each, same topic layout and cluster state.
4. **Measure both sides:** client throughput and latency **and** broker CPU, network and disk, because a change can move cost from client to broker.
5. **Test end to end:** produce plus consume, with the real consumer logic for at least one run.
6. Our result: `zstd` with 128 KB batches cut network and disk 35% versus `snappy`, with 8% more producer CPU and the same p99 — approved.

**Trade-offs and what can go wrong**
Benchmarks on an idle cluster overstate capacity; leave production-like background load running.

**How I'd monitor it**
Benchmark results stored per run, and the same production metrics observed after rollout.

**60-second answer**
I benchmark with kafka-producer-perf-test and consumer-perf-test, or the OpenMessaging Benchmark for bigger studies, using real anonymised payloads because random bytes don't compress. I change one variable at a time over several runs, measure both client numbers and broker CPU, network and disk, and run end to end at least once. That's how we proved zstd with larger batches cut network and disk 35% for 8% more producer CPU.

### Q12 [architect] Many teams share one Kafka cluster and one team's traffic spike hurts everyone. What do you do?
tags: quotas, multi-tenancy, noisy-neighbour, governance, isolation

**The live scenario**
A data-science team backfilled a year of events at full speed. Broker network saturated, produce latency for the payments team jumped to seconds, and consumer lag grew everywhere.

**What the interviewer is really checking**
Platform thinking: quotas, isolation tiers and guardrails for shared infrastructure.

**How I answer it**
1. **Client quotas** per user or client id:
   - `producer_byte_rate` and `consumer_byte_rate` cap bandwidth;
   - `request_percentage` caps broker thread time.

   Kafka throttles over-quota clients by delaying responses, instead of failing them. We put the backfill on a quota of 50 MB/s.
2. **Isolation tiers:** critical workloads (payments) on a dedicated cluster or dedicated brokers; batch and analytics on a shared cluster; replays and backfills scheduled off-peak or on a replica cluster.
3. **Guardrails:**
   - topic creation through a self-service pipeline with sensible defaults (partitions, RF=3, min ISR 2, retention);
   - naming conventions and ownership tags;
   - capacity requests for big workloads.
4. **Visibility per tenant:** bytes in/out and request time per client id, so you can see who is causing the load.
5. **Chargeback or showback** so teams see the cost of their traffic.

**Trade-offs and what can go wrong**
Quotas set too low throttle legitimate peaks; review them with the teams. Too many dedicated clusters raise operational cost.

**How I'd monitor it**
Per-client throughput and throttle time (`throttle-time-avg`), broker network saturation, and an alert when a client exceeds its expected rate.

**60-second answer**
On a shared cluster I protect tenants with client quotas — producer and consumer byte rates and request percentage — which throttle the noisy client rather than failing it; a backfill that hurt payments now runs at a 50 MB/s quota. I put critical workloads on dedicated clusters or brokers, schedule backfills off-peak, give teams self-service topics with safe defaults and ownership tags, and show per-client traffic and cost so everyone can see who is using what.
